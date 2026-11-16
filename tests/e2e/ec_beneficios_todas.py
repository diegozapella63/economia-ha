# EconomIA 1.39.0: Mais › Lojas › Benefícios de todas: a IA procura os benefícios do clube das lojas que você acompanha,
# uma de cada vez (uma por rede, pelo nome), com o andamento e o Parar; as procuradas nos últimos 60 dias ficam de fora;
# os benefícios achados ficam recolhidos em cada loja.
import asyncio
import time
from datetime import datetime, timedelta, timezone

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, HAFalso, abrir_mais, check, espera, pagina, resumo

AGORA = datetime.now(timezone.utc)
OFERTAS = {"versao": 2, "gerado_em": "2026-11-02T10:00:00-03:00", "categorias": [
    {"id": "farmacias", "nome": "Farmácias", "singular": "Farmácia",
     "redes": [{"id": "farm-raia", "nome": "Droga Raia"}, {"id": "farm-nissei", "nome": "Farmácias Nissei"}, {"id": "farm-sol", "nome": "Farmácia Sol"}],
     "lojas": [{"rede": "farm-raia", "distancia_km": 0.8, "endereco": "Rua A, 1", "fontes": ["Mapa"]},
               {"rede": "farm-nissei", "distancia_km": 1.4, "endereco": "Rua B, 2", "fontes": ["Mapa"]},
               {"rede": "farm-sol", "distancia_km": 1.9, "endereco": "Rua F, 6", "fontes": ["Mapa"]}], "cupons": [], "ofertas": []},
    {"id": "mercados", "nome": "Mercados", "singular": "Mercado",
     "redes": [{"id": "merc-giassi", "nome": "Giassi"}, {"id": "merc-giassi2", "nome": "Giassi - Centro"}, {"id": "merc-fort", "nome": "Fort Atacadista"}],
     "lojas": [{"rede": "merc-giassi", "distancia_km": 1.1, "endereco": "Rua C, 3", "fontes": ["Mapa"]},
               {"rede": "merc-giassi2", "distancia_km": 2.5, "endereco": "Rua G, 7", "fontes": ["Mapa"]},
               {"rede": "merc-fort", "distancia_km": 4.2, "endereco": "Rua E, 5", "fontes": ["Mapa"]}], "cupons": [], "ofertas": []}],
    "lista": []}
CLUBES = {"Farmácias Nissei": "Club Nissei", "Giassi": "Clube Giassi", "Mercado Livre": "Meli+"}


def antes(S):
    S.gravar_json(S.OFERTAS, OFERTAS)
    S.gravar_json(S.CLUBES_FILE, {
        # procurada ontem: fica de fora
        S.chave_loja("Farmácias Nissei"): {"loja": "Farmácias Nissei", "clube": "Club Nissei", "beneficios": [{"titulo": "Desconto", "detalhe": "Até 40%."}],
                                           "em": (AGORA - timedelta(days=1)).isoformat()},
        # procurada há três meses: entra de novo
        S.chave_loja("Droga Raia"): {"loja": "Droga Raia", "clube": "", "beneficios": [], "em": (AGORA - timedelta(days=90)).isoformat()}})


def responde(corpo):
    time.sleep(0.6)  # dá tempo de tocar em Parar
    nome = corpo["task_name"].split("clube ", 1)[1]
    clube = CLUBES.get(nome)
    if not clube:
        return {"clube": "", "beneficios": []}
    return {"clube": clube, "custo": "Grátis", "beneficios": [{"titulo": "Preço de clube", "detalhe": "Ofertas para quem é do clube."}]}


def pedidos(ha):
    return [b["task_name"].split("clube ", 1)[1] for _, c, _, b in ha.pedidos_de("ai_task/generate_data") if "clube " in b.get("task_name", "")]


async def main():
    ha = HAFalso()
    ha.tarefa_ia("ai_task.busca", "Busca")
    ha.responde_ia("clube", responde)
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["farmacias", "mercados"], "ia": {"busca": "ai_task.busca"}, "lista": [],
           "lojas": {"ignorar": ["merc-fort"]}}
    with App(cfg, buscar=False, antes=antes, ha=ha) as app:
        async with async_playwright() as p:
            for largura in (390, 320):
                b, pg = await pagina(p, largura=largura)
                await pg.goto(app.url)
                await pg.wait_for_timeout(1200)
                await abrir_mais(pg, "lojas")
                await pg.wait_for_timeout(500)
                todas, achar = pg.locator("#benTodas"), pg.locator("#acharLojas2")
                bt, ba = await todas.bounding_box(), await achar.bounding_box()
                check(await todas.is_visible() and "Benefícios de todas" in await todas.inner_text() and await todas.locator("svg").count() >= 1,
                      f"{largura} px: Benefícios de todas, com o ícone")
                # no celular, um embaixo do outro, na largura do cartão
                check(abs(bt["x"] - ba["x"]) < 1 and bt["y"] > ba["y"] and abs(bt["height"] - ba["height"]) < 1 and abs(bt["width"] - ba["width"]) < 2,
                      f"{largura} px: embaixo do Encontrar lojas, do mesmo tamanho ({bt}, {ba})")
                largo = await pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                check(largo <= 0, f"{largura} px: nada passa da largura ({largo})")
                if largura == 320:
                    await pg.locator("#mp-lojas").screenshot(path=SHOTS + "/ecbt-320.png")
                    await b.close()
                    break

                # Parar: termina a loja que está sendo procurada e para
                await todas.click()
                await espera(pg, "() => /Procurando os benefícios: 1 de 5 · Droga Raia/.test(document.getElementById('benTodasMsg').textContent)")
                check((await todas.inner_text()).strip() == "Parar", "durante a procura, o botão vira Parar")
                check(await todas.bounding_box() == bt, "no mesmo lugar e do mesmo tamanho")
                check(await pg.locator('#mp-lojas [data-clube-ben]:not([disabled])').count() == 0, "os Benefícios de cada loja esperam")
                await pg.locator("#mp-lojas").screenshot(path=SHOTS + "/ecbt-andamento.png")
                await todas.click()
                check("Parando depois desta loja" in await pg.text_content("#benTodasMsg"), "Parar: avisa que para depois desta loja")
                await espera(pg, "() => /Benefícios procurados/.test(document.getElementById('benTodasMsg').textContent)")
                msg = await pg.text_content("#benTodasMsg")
                check(msg == "Benefícios procurados em 1 loja. Nenhuma com clube.", f"parou depois da primeira ({msg})")
                check(pedidos(ha) == ["Droga Raia"], f"só a Droga Raia foi perguntada ({pedidos(ha)})")
                check((await todas.inner_text()).strip() == "Benefícios de todas", "volta a Benefícios de todas")

                # de novo: as que faltam, uma por rede (o Giassi - Centro é o mesmo Giassi; a Nissei foi procurada ontem;
                # o Fort você não acompanha), e as lojas online que você acompanha (o Mercado Livre e a Amazon, de início)
                await todas.click()
                await espera(pg, "() => /Benefícios procurados/.test(document.getElementById('benTodasMsg').textContent)", 20000)
                msg = await pg.text_content("#benTodasMsg")
                check(msg == "Benefícios procurados em 4 lojas: 2 com clube.", f"as outras quatro ({msg})")
                check(pedidos(ha) == ["Droga Raia", "Farmácia Sol", "Giassi", "Mercado Livre", "Amazon"], f"uma vez cada, da mais perto para a mais longe ({pedidos(ha)})")
                salvos = app.api("GET", "/api/estado").get("clubes") or {}
                check(any(v.get("clube") == "Clube Giassi" for v in salvos.values()), "os benefícios do Giassi guardados")
                # recolhidos, como o Como foi testado
                await pg.click('#lojasAbas [data-loja-aba="mercados"]')
                await pg.wait_for_timeout(300)
                det = pg.locator('#mp-lojas details[data-clube-det="merc-giassi"]')
                check(await det.count() == 1 and "Benefícios do Clube Giassi" in await det.locator("summary").inner_text()
                      and await det.get_attribute("open") is None, "Giassi: os benefícios recolhidos")
                # tudo procurado há pouco: avisa e não pergunta de novo
                await todas.click()
                await pg.wait_for_timeout(400)
                check("já foram procurados nos últimos 60 dias" in await pg.text_content("#toast"), "tudo procurado: avisa")
                check(len(pedidos(ha)) == 5, "e não pergunta à IA de novo")
                await b.close()
    resumo()


asyncio.run(main())
