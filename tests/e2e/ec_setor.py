# EconomIA 1.35.0: a comparação é sempre por quilo, litro ou unidade (nunca pelo tamanho de sempre do item, 400 g ou
# 30 ml) e nada se compara entre setores: cada item fica no setor escolhido (Onde comprar, ao adicionar ou no pé do
# cartão) ou no das lojas em que ele mais aparece. Lojas e preços inventados.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, App, categoria, check, pagina, resumo, shot

OFERTAS = {"versao": 2, "gerado_em": "2026-11-02T10:00:00-03:00", "categorias": [
    categoria("mercados", [("merc-azul", "Mercado Azul", 0.8), ("merc-sol", "Atacado Sol", 3.0)]),
    categoria("farmacias", [("farm-lua", "Farmácia Lua", 1.0), ("farm-mar", "Drogaria Mar", 1.5)])],
    "lista": [
        {"produto": "Peito de frango", "precos": {"merc-azul": 18.0, "merc-sol": 19.0}, "base": {"quantidade": 0.4, "unidade": "kg"},
         "tamanhos": [{"rede": "merc-sol", "embalagem": "Peito de frango 1,5 kg", "quantidade": 1.5, "preco": 14.4}]},
        {"produto": "Álcool 70", "precos": {"farm-lua": 6.26, "farm-mar": 6.28}, "base": {"quantidade": 0.03, "unidade": "L"},
         "tamanhos": [{"rede": "merc-sol", "embalagem": "Galão 5 L", "quantidade": 5, "preco": 42.98}]},
        {"produto": "Leite sem lactose", "precos": {"merc-azul": 4.98, "merc-sol": 5.59, "farm-lua": 23.88}, "base": {"quantidade": 1, "unidade": "L"}}]}


def limpo(s):
    return " ".join(s.replace("\xa0", " ").split())


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados", "farmacias"],
           "lista": [{"produto": "Peito de frango"}, {"produto": "Álcool 70"}, {"produto": "Leite sem lactose"}]}
    with App(cfg, buscar=False, antes=lambda S: S.gravar_json(S.OFERTAS, OFERTAS)) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(400)
            item = lambda nome: pg.locator("#wish > li.item", has_text=nome).first  # noqa: E731
            # ----- por quilo, não por 400 g -----
            frango = item("Peito de frango")
            best = limpo(await frango.locator(".i-best").inner_text())
            check("R$ 9,60 por quilo" in best and "Peito de frango 1,5 kg por R$ 14,40 · Atacado Sol" in best and "400 g" not in best, f"Melhor compra por quilo ({best})")
            av = limpo(await frango.locator(".i-avulso").first.inner_text())
            check(av == "Avulso, o mais barato: R$ 45,00 por quilo · 400 g por R$ 18,00 (Mercado Azul)", f"o avulso também por quilo ({av})")
            eco = limpo(await frango.locator(".i-save").inner_text())
            check(eco == "economia de R$ 35,40/kg", f"a economia por quilo ({eco})")
            await frango.screenshot(path=__import__("os").path.join(__import__("base_e2e").SHOTS, "setor-frango.png"))
            # ----- automático: o álcool fica nas farmácias (onde mais aparece); o galão do atacado não entra -----
            alc = item("Álcool 70")
            t = limpo(await alc.inner_text())
            check("MAIS BARATO" in t.upper() and "Farmácia Lua" in t and "Atacado Sol" not in t and "Galão" not in t, f"álcool: só as farmácias ({t[:200]})")
            check(await alc.locator("details.i-det").count() == 0, "sem Comparar tamanhos com o galão de outro setor")
            check("Em 2 farmácias" in t, "o pé conta só as farmácias")
            leite = item("Leite sem lactose")
            t = limpo(await leite.inner_text())
            check("Farmácia Lua" not in t and "Em 2 mercados" in t and "economia de R$ 0,61" in t, f"leite: só os mercados ({t[:200]})")
            sel = alc.locator("select[data-setor]")
            ops = [limpo(x) for x in await sel.locator("option").all_inner_texts()]
            check(ops == ["Setor automático", "Só mercado", "Só farmácia"], f"o setor no pé do cartão ({ops})")
            # ----- só mercado: o galão vira o preço do item -----
            await sel.select_option("mercados")
            await pg.wait_for_timeout(700)
            check(next(i for i in app.config_salva()["lista"] if i["produto"] == "Álcool 70").get("setor") == "mercados", "o setor fica guardado")
            alc = item("Álcool 70")
            t = limpo(await alc.inner_text())
            check("R$ 42,98" in t and "Atacado Sol" in t and "Farmácia Lua" not in t and "Em 1 mercado" in t, f"só mercado: o galão do atacado ({t[:200]})")
            check(await alc.locator("select[data-setor]").input_value() == "mercados", "o pé mostra Só mercado")
            await alc.locator("select[data-setor]").select_option("")
            await pg.wait_for_timeout(700)
            check("setor" not in next(i for i in app.config_salva()["lista"] if i["produto"] == "Álcool 70"), "de volta ao automático")
            # ----- Onde comprar, ao adicionar -----
            row = pg.locator("#novoSetorRow")
            check(await row.is_visible(), "Onde comprar aparece com mais de um setor ligado")
            await pg.select_option("#novoSetor", "farmacias")
            await pg.fill("#novoItem", "Dipirona 1 g")
            await pg.click('#addForm button[type="submit"]')
            await pg.wait_for_timeout(700)
            novo = next(i for i in app.config_salva()["lista"] if i["produto"] == "Dipirona 1 g")
            check(novo.get("setor") == "farmacias", f"o item novo entra com o setor ({novo})")
            check(await pg.input_value("#novoSetor") == "", "o campo volta ao automático")
            check(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "nada passa da largura")
            await shot(pg, "setor-lista")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
