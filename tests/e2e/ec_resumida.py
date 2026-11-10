# EconomIA 1.13.0: Minha lista › Completa ou Resumida (fica guardada no aparelho). Na resumida, cada item é uma linha: o
# nome, o preço escolhido (a sua escolha, a melhor compra ou o mais barato) e onde comprar; um toque abre o cartão inteiro
# ali mesmo, e tocar no nome dele fecha. E, no pé de cada cartão com preço, Buscar de novo procura só aquele item.
import asyncio
import json

from playwright.async_api import async_playwright

from base_e2e import CEP, App, categoria, check, espera, pagina, resumo, shot

OFERTAS = {"versao": 2, "gerado_em": "2026-11-01T10:00:00-03:00",
           "categorias": [categoria("mercados", [("merc-giassi", "Giassi", 1.0), ("merc-fort", "Fort", 2.0)])],
           "lista": [{"produto": "Arroz 5 kg", "precos": {"merc-giassi": 24.9, "merc-fort": 22.9}},
                     {"produto": "Café torrado em grãos", "precos": {"merc-giassi": 81.9, "merc-fort": 95.8}}]}


async def linhas(pg):
    return await pg.evaluate("""() => [...document.querySelectorAll('#wish > li')].map(li => li.classList.contains('mini')
      ? ['mini', li.querySelector('.i-prod').textContent, (li.querySelector('.i-mini-v b') || {}).textContent || '', (li.querySelector('.i-mini-v small') || {}).textContent || '']
      : ['cartao', li.querySelector('.i-prod').textContent]).map(x => x.map(s => s.replace(/\\u00a0/g, ' ')))""")


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados"],
           "lista": [{"produto": "Arroz 5 kg"}, {"produto": "Café torrado em grãos", "escolha": {"rede": "merc-fort", "q": None, "obs": ""}},
                     {"produto": "Bolacha recheada"}]}
    with App(cfg, buscar=False, antes=lambda S: S.gravar_json(S.OFERTAS, OFERTAS)) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(300)
            check(await pg.locator("#visLista button").all_inner_texts() == ["Completa", "Resumida"], "a escolha: Completa ou Resumida")
            check(await pg.get_attribute('#visLista [data-vis="completa"]', "aria-pressed") == "true", "começa na completa")
            check([x[0] for x in await linhas(pg)] == ["cartao"] * 3, "completa: os cartões de sempre")
            # Buscar de novo, no pé do cartão com preço; o sem preço tem o Buscar este item
            arroz = pg.locator("#wish > li.item", has_text="Arroz 5 kg")
            check(await arroz.locator(".i-foot .i-rebusca").inner_text() == "Buscar de novo", "Buscar de novo no pé do cartão")
            check(await pg.locator("#wish > li.item", has_text="Bolacha").locator(".i-rebusca").count() == 0, "o item sem preço tem o Buscar este item")
            async with pg.expect_request(lambda r: "api/buscar-itens" in r.url and r.method == "POST") as rq:
                await arroz.locator(".i-rebusca").click()
            check(json.loads((await rq.value).post_data) == {"itens": ["Arroz 5 kg"]}, "procura só aquele item")
            await espera(pg, "() => !document.getElementById('buscar').disabled", 30000)
            await pg.wait_for_timeout(500)
            # a resumida
            await pg.click('#visLista [data-vis="resumida"]')
            await pg.wait_for_timeout(300)
            ls = await linhas(pg)
            check(ls == [["mini", "Arroz 5 kg", "R$ 22,90", "Fort"], ["mini", "Café torrado em grãos", "R$ 95,80", "Fort"], ["mini", "Bolacha recheada", "Sem preço ainda", ""]],
                  f"resumida: o item, o preço (a sua escolha, no café) e onde comprar ({ls})")
            alt = await pg.evaluate("[...document.querySelectorAll('#wish > li.mini')].map(li => li.getBoundingClientRect().height)")
            check(all(h <= 62 for h in alt), f"cada linha baixa ({alt})")
            check(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "nada passa da largura")
            await shot(pg, "lista-resumida")
            # um toque abre o cartão ali mesmo; tocar no nome fecha
            await pg.locator("#wish .i-mini", has_text="Café").click()
            await pg.wait_for_timeout(300)
            check([x[0] for x in await linhas(pg)] == ["mini", "cartao", "mini"], "o café abre, os outros ficam resumidos")
            cafe = pg.locator("#wish > li.item:not(.mini)")
            check("SUA ESCOLHA" in (await cafe.inner_text()).upper() and await cafe.locator(".i-rebusca").count() == 1, "o cartão inteiro, com o Buscar de novo")
            await shot(pg, "lista-resumida-aberta")
            await cafe.locator(".i-actions .sim-btn").click()  # um botão do cartão não fecha
            await pg.wait_for_timeout(300)
            check([x[0] for x in await linhas(pg)] == ["mini", "cartao", "mini"], "os botões do cartão não fecham")
            await cafe.locator(".i-head .i-prod").click()
            await pg.wait_for_timeout(300)
            check([x[0] for x in await linhas(pg)] == ["mini"] * 3, "tocar no nome fecha")
            # fica guardada no aparelho
            await pg.reload()
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(300)
            check(await pg.get_attribute('#visLista [data-vis="resumida"]', "aria-pressed") == "true" and [x[0] for x in await linhas(pg)] == ["mini"] * 3,
                  "depois de recarregar, continua resumida")
            await b.close()
            b, pg = await pagina(p, 320, 700, escuro=False)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.click('#visLista [data-vis="resumida"]')
            await pg.wait_for_timeout(300)
            check(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "320 px: nada passa da largura")
            corte = await pg.evaluate("[...document.querySelectorAll('#wish .i-mini-v b')].filter(e => e.scrollWidth > e.clientWidth + 1).length")
            check(corte == 0, "320 px: os preços inteiros")
            await shot(pg, "lista-resumida-320")
            await b.close()
    resumo()


asyncio.run(main())
