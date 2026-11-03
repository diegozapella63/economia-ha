# EconomIA 0.19.0: Mais › Dados: baixar a planilha, o JSON da lista e o das ofertas (nome do arquivo com a data e o
# conteúdo), Versões anteriores (cópia automática e antes de limpar; Restaurar pede confirmação e guarda a de antes),
# Importar lista (itens novos, datas juntadas, arquivo inválido, nada novo).
import asyncio
import io
import json
import re
import zipfile

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, categoria, check, espera, pagina, resumo

OFERTAS = {"versao": 2, "gerado_em": "2026-11-01T10:00:00-03:00", "categorias": [categoria("mercados", [("merc-giassi", "Giassi", 1.0), ("merc-fort", "Fort", 2.0)])],
           "lista": [{"produto": "Arroz 5 kg", "precos": {"merc-giassi": 24.9, "merc-fort": 22.9}}]}


async def baixa(pg, sel):
    async with pg.expect_download() as d:
        await pg.click(sel)
    dl = await d.value
    with open(await dl.path(), "rb") as f:
        return dl.suggested_filename, f.read()


async def abre_dados(pg):
    await pg.click('.tabbar [data-view="mais"]')
    await pg.click("#aba-dados")
    await pg.wait_for_timeout(300)


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados"], "lista": [{"produto": "Arroz 5 kg", "compras": ["2026-10-01", "2026-10-15"]}, {"produto": "Bolacha"}]}
    with App(cfg, buscar=False, antes=lambda S: S.gravar_json(S.OFERTAS, OFERTAS)) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            # ----- exportar -----
            await abre_dados(pg)
            nome, x = await baixa(pg, "#expXlsx")
            check(re.fullmatch(r"economia-minha-lista-\d{4}-\d\d-\d\d\.xlsx", nome), f"planilha com a data no nome ({nome})")
            folha = zipfile.ZipFile(io.BytesIO(x)).read("xl/worksheets/sheet1.xml").decode()
            check("Arroz 5 kg" in folha and "Fort" in folha and "Giassi R$ 24,90" in folha and "15/10/2026" in folha, "a planilha com o mais barato, as outras lojas e as compras")
            nome, j = await baixa(pg, "#expJson")
            d = json.loads(j)
            arroz = next(i for i in d["lista"] if i["produto"] == "Arroz 5 kg")
            check(nome.endswith(".json") and d["app"] == "EconomIA" and arroz["mais_barato"]["loja"] == "Fort" and arroz["compra_a_cada_dias"] == 14, "o JSON da lista")
            nome, o = await baixa(pg, "#expOf")
            check(nome.startswith("economia-ofertas-") and json.loads(o)["lista"][0]["precos"]["merc-fort"] == 22.9, "o JSON das ofertas")
            await pg.locator("#mp-dados").screenshot(path=SHOTS + "/ecd-dados.png")
            # ----- versões: a cópia automática ao salvar e a de antes de limpar -----
            await pg.click('.tabbar [data-view="lista"]')
            await pg.fill("#novoItem", "Café Pilão 500 g")
            await pg.click('#addForm button[type="submit"]')
            await pg.wait_for_timeout(800)
            await pg.click("#limpar")
            await pg.click("#limparSim")
            await pg.wait_for_timeout(900)
            check(app.config_salva()["lista"] == [], "lista limpa")
            await abre_dados(pg)
            await pg.click("#verBtn")
            await espera(pg, "() => document.querySelectorAll('#verLista li').length >= 2")
            vers = [t.replace("\xa0", " ") for t in await pg.locator("#verLista li").all_inner_texts()]
            check(len(vers) == 2 and "antes de limpar a lista · 3 itens · CEP " + CEP in vers[0] and "automática · 2 itens" in vers[1], f"as duas cópias, da mais nova para a mais velha ({vers})")
            await pg.locator("#verLista li").first.locator("[data-ver]").click()
            check("Voltar para esta versão?" in await pg.locator("#verLista li").first.inner_text(), "Restaurar pede confirmação")
            await pg.click("#verLista [data-ver-nao]")
            check(await pg.locator("#verLista [data-ver-sim]").count() == 0, "Cancelar desiste")
            await pg.locator("#verLista li").first.locator("[data-ver]").click()
            await pg.locator("#verLista li").first.locator("[data-ver-sim]").click()
            await espera(pg, "() => document.getElementById('toast').textContent === 'Versão restaurada'")
            check([i["produto"] for i in app.config_salva()["lista"]] == ["Arroz 5 kg", "Bolacha", "Café Pilão 500 g"], "a lista voltou")
            await espera(pg, "() => /antes de restaurar/.test(document.getElementById('verLista').textContent)")
            check(await pg.locator("#verLista li").count() == 3, "guarda a versão de antes de restaurar (ficam as 3 mais recentes)")
            await pg.locator("#mp-dados").screenshot(path=SHOTS + "/ecd-versoes.png")
            await pg.click('.tabbar [data-view="lista"]')
            check(await pg.locator("#wish > li.item").count() == 3, "a Minha lista mostra os itens de volta")
            # ----- importar -----
            await abre_dados(pg)
            await pg.set_input_files("#impArq", [{"name": "x.json", "mimeType": "application/json", "buffer": b"{quebrado"}])
            await espera(pg, "() => document.getElementById('impMsg').textContent !== ''")
            check(await pg.text_content("#impMsg") == "Esse arquivo não é um JSON válido.", "arquivo inválido")
            imp = {"lista": [{"produto": "Detergente Ypê", "compras": ["2026-10-20"]}, {"produto": "arroz 5 KG", "compras": ["2026-10-29", "2026-10-15"]}, "ab", {"x": 1}]}
            await pg.set_input_files("#impArq", [{"name": "lista.json", "mimeType": "application/json", "buffer": json.dumps(imp).encode()}])
            await espera(pg, "() => /novo/.test(document.getElementById('impMsg').textContent)")
            check(await pg.text_content("#impMsg") == "1 item novo entrou na lista, e 1 data de compra foi juntada.", f"importado ({await pg.text_content('#impMsg')})")
            lista = {i["produto"]: i for i in app.config_salva()["lista"]}
            check("Detergente Ypê" in lista and sorted(lista["Arroz 5 kg"]["compras"]) == ["2026-10-01", "2026-10-15", "2026-10-29"], "o novo entra e a data nova é juntada, sem repetir")
            await pg.set_input_files("#impArq", [{"name": "lista.json", "mimeType": "application/json", "buffer": json.dumps(imp).encode()}])
            await espera(pg, "() => /Não achei/.test(document.getElementById('impMsg').textContent)")
            check(await pg.text_content("#impMsg") == "Não achei itens novos nesse arquivo.", "importar de novo não duplica")
            vs = app.api("GET", "api/versoes")["versoes"]
            check(any(v["motivo"] == "antes de importar" for v in vs), "guarda uma cópia antes de importar")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
