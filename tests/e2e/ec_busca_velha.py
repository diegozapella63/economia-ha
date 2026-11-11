# EconomIA 1.31.0: a última busca completa com mais de 3 dias fica em alerta no alto (Última busca há N dias, na cor de
# aviso, com Buscar agora); até 3 dias, como antes. Lojas e preços inventados.
import asyncio
from datetime import date, timedelta

from playwright.async_api import async_playwright

from base_e2e import CEP, App, categoria, check, pagina, resumo, shot


def ofertas(dias):
    d = (date.today() - timedelta(days=dias)).isoformat()
    return {"versao": 2, "gerado_em": f"{d}T16:38:00-03:00",
            "categorias": [categoria("mercados", [("merc-azul", "Mercado Azul", 1.0)])],
            "lista": [{"produto": "Café torrado em grãos", "precos": {"merc-azul": 81.9}}]}


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados"], "lista": [{"produto": "Café torrado em grãos"}]}
    with App(cfg, buscar=False, antes=lambda S: S.gravar_json(S.OFERTAS, ofertas(9))) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            dia = (date.today() - timedelta(days=9)).strftime("%d/%m")
            txt = await pg.inner_text("#syncText")
            check(txt.startswith(f"Última busca há 9 dias ({dia})"), f"9 dias: diz há quanto tempo ({txt})")
            check("velha" in (await pg.get_attribute("#sync", "class")) and await pg.locator("#syncBuscar").is_visible(), "em alerta, com o Buscar agora")
            cor = await pg.evaluate("[getComputedStyle(document.getElementById('sync')).color, getComputedStyle(document.documentElement).getPropertyValue('--warn')]")
            check(cor[1].strip() != "", f"na cor de aviso ({cor})")
            await shot(pg, "busca-velha")
            app.S.gravar_json(app.S.OFERTAS, ofertas(3))
            await pg.reload()
            await pg.wait_for_timeout(1200)
            check("velha" not in (await pg.get_attribute("#sync", "class") or "") and await pg.locator("#syncBuscar").is_hidden()
                  and (await pg.inner_text("#syncText")).startswith("Última busca "), "até 3 dias: como antes")
            app.S.gravar_json(app.S.OFERTAS, ofertas(4))
            await pg.reload()
            await pg.wait_for_timeout(1200)
            await pg.click("#syncBuscar")
            await pg.wait_for_timeout(600)
            check(await pg.locator("#syncBuscar").is_hidden() or await pg.locator("#buscaMsg").is_visible(), "Buscar agora começa a busca")
            await b.close()
            b, pg = await pagina(p, 1280, 800)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            lado = pg.locator(".side-sync")
            check(await lado.count() == 1 and "velha" in await lado.get_attribute("class"), "no computador, a barra lateral também avisa")
            await b.close()
    resumo()


asyncio.run(main())
