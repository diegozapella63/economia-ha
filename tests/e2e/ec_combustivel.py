# EconomIA 1.63.0 (o dono: "Preço do combustível (ANP) no EconomIA. Pode seguir também"): Mais › Casa › Combustível: os
# preços dos postos da cidade (a média e o mais barato de cada produto) pela pesquisa semanal da ANP, com o Atualizar.
# Postos e preços inventados; nada é baixado (o guardado está em dia).
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, App, check, pagina, resumo, shot

LINHAS = [{"posto": "Posto Da Ana Ltda", "bairro": "Centro", "rua": "Rua Das Flores 10", "bandeira": "Branca", "produto": "gasolina", "data": "2026-11-23", "preco": 5.99},
          {"posto": "Posto Do Beto Comércio De Combustíveis Ltda", "bairro": "Glória", "rua": "Rua Do Sol 20", "bandeira": "Branca", "produto": "gasolina", "data": "2026-11-23", "preco": 6.19},
          {"posto": "Posto Da Ana Ltda", "bairro": "Centro", "rua": "Rua Das Flores 10", "bandeira": "Branca", "produto": "etanol", "data": "2026-11-23", "preco": 4.19}]


def antes(S):
    S.gravar_json(S.FOLHETOS, {"_cep": {"cep": "89200000", "cidade": "Joinville", "uf": "SC"}})
    S.gravar_json(S.COMBUSTIVEL, {"cidade": "Joinville", "uf": "SC", "buscado_em": S.agora(), "linhas": LINHAS})


def vazio(S):
    S.gravar_json(S.FOLHETOS, {"_cep": {"cep": "89200000", "cidade": "Joinville", "uf": "SC"}})


async def abre(pg, app):
    await pg.goto(app.url + "#mais")
    await pg.wait_for_timeout(1000)
    await pg.evaluate("document.querySelector('[data-mais=\"casa\"]') && document.querySelector('[data-mais=\"casa\"]').click()")
    await pg.wait_for_selector("#combBuscar")


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados"], "lista": []}
    async with async_playwright() as p:
        with App(cfg, buscar=False, antes=antes) as app:
            for w, escuro in ((390, False), (320, True)):
                b, pg = await pagina(p, w, 844, escuro=escuro)
                await abre(pg, app)
                await pg.wait_for_selector("#combustivel .comb-item")
                check((await pg.locator("#h-comb").inner_text()).strip() == "Combustível", f"{w}: o título")
                itens = await pg.locator("#combustivel .comb-item").all_inner_texts()
                check(len(itens) == 2 and "Gasolina" in itens[0] and "média R$ 6,09" in itens[0] and "R$ 5,99 · Posto Da Ana Ltda (Centro)" in itens[0],
                      f"{w}: a gasolina com a média e o posto mais barato ({itens})")
                check("Etanol" in itens[1] and "R$ 4,19" in itens[1], f"{w}: o etanol")
                dica = (await pg.locator("#combHint").inner_text()).strip()
                check(dica == "Postos de Joinville na pesquisa semanal da ANP, coleta de 23/11.", f"{w}: de onde vem ({dica})")
                check(await pg.locator('#combHint a.site').get_attribute("href") == "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis", f"{w}: a ANP é um link")
                bt = pg.locator("#combBuscar")
                check((await bt.inner_text()).strip() == "Atualizar" and await bt.locator("svg").count() == 1, f"{w}: o Atualizar com ícone")
                caixa = await bt.bounding_box()
                check(round(caixa["height"]) == 50, f"{w}: o botão com 50 px ({caixa['height']})")
                check(not await pg.evaluate("document.documentElement.scrollWidth > innerWidth"), f"{w}: nada passa da largura")
                await pg.locator("#combustivel").scroll_into_view_if_needed()
                await shot(pg, f"combustivel-{w}")
                await bt.click()
                await pg.wait_for_timeout(600)
                check(await pg.locator("#combustivel .comb-item").count() == 2, f"{w}: em dia, o Atualizar não muda nada")
                await b.close()
        with App(cfg, buscar=False, antes=vazio) as app:
            b, pg = await pagina(p, 390, 844)
            await abre(pg, app)
            check((await pg.locator("#combBuscar").inner_text()).strip() == "Ver preços dos postos", "sem nada guardado: Ver preços dos postos")
            check((await pg.locator("#combHint").inner_text()).strip() == "Os preços dos postos da cidade, pela pesquisa semanal da ANP.", "o texto de antes de buscar")
            check(await pg.locator("#combustivel .comb-item").count() == 0, "nenhuma linha")
            await b.close()
    resumo()


asyncio.run(main())
