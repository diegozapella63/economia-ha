# EconomIA 1.18.0: Mais › Configurações › Opções › Atalho no celular. O caminho do app no Home Assistant (/app/<slug>,
# pelo nome do contêiner: o slug ofertas_do_bairro com traços) com o Copiar embaixo, e os passos do app do Home
# Assistant (Gerenciar atalhos › Atalho fixado › Painel). Fora do Home Assistant, o cartão não aparece. 390 e 320 px.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, abrir_mais, check, pagina, resumo

CAMINHO = "/app/a1b2c3d4_ofertas_do_bairro"
CFG = {"cep": CEP, "raio_km": 5, "categorias": ["mercados"], "lista": [{"produto": "Leite integral"}]}


async def main():
    async with async_playwright() as p:
        with App(CFG, buscar=False) as app:  # fora do Home Assistant
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await abrir_mais(pg, "opcoes")
            await pg.wait_for_timeout(300)
            check(await pg.locator("#opAtalho").is_hidden(), "fora do Home Assistant: sem o Atalho no celular")
            await b.close()
        with App(CFG, buscar=False, env={"OFERTAS_HOST": "a1b2c3d4-ofertas-do-bairro"}) as app:
            for largura, escuro in ((390, True), (320, False)):
                tag = f"{largura} px {'escuro' if escuro else 'claro'}"
                b, pg = await pagina(p, largura=largura, escuro=escuro, permissoes=["clipboard-read", "clipboard-write"])
                await pg.goto(app.url)
                await pg.wait_for_timeout(1200)
                await abrir_mais(pg, "opcoes")
                await pg.wait_for_timeout(300)
                sec = pg.locator("#opAtalho")
                check(await sec.is_visible(), f"{tag}: Atalho no celular em Opções")
                ids = await pg.evaluate("[...document.querySelectorAll('#mp-opcoes > section')].map(s => s.id || s.getAttribute('aria-labelledby'))")
                check(ids[-1] == "opAtalho", f"{tag}: por último ({ids})")
                txt = " ".join((await sec.inner_text()).split())
                check("abre o EconomIA direto" in txt and "Configurações › Aplicativo complementar › Gerenciar atalhos" in txt and "Atalho fixado" in txt and "Painel" in txt,
                      f"{tag}: os passos do app do Home Assistant ({txt[:150]})")
                check(await pg.input_value("#opAtalhoC") == CAMINHO, f"{tag}: o caminho")
                await sec.scroll_into_view_if_needed()
                bi, bb = await pg.locator("#opAtalhoC").bounding_box(), await pg.locator("#opAtalhoCopiar").bounding_box()
                check(bb["y"] >= bi["y"] + bi["height"] - 1 and abs(bb["width"] - bi["width"]) < 2, f"{tag}: o Copiar embaixo, da mesma largura")
                check(round(bi["height"]) == 50 and round(bb["height"]) == 50, f"{tag}: os dois com 50 px ({bi['height']}, {bb['height']})")
                check(await pg.eval_on_selector("#opAtalhoC", "(e) => e.scrollWidth <= e.clientWidth"), f"{tag}: o caminho inteiro à vista, sem cortar")
                check(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"{tag}: nada passa da largura")
                await pg.click("#opAtalhoCopiar")
                await pg.wait_for_timeout(300)
                check(await pg.evaluate("navigator.clipboard.readText()") == CAMINHO, f"{tag}: o Copiar põe o caminho na área de transferência")
                await sec.screenshot(path=f"{SHOTS}/ec-atalho-{largura}.png")
                check(not pg.erros, f"{tag}: sem erros na página {pg.erros}")
                await b.close()


asyncio.run(main())
resumo()
