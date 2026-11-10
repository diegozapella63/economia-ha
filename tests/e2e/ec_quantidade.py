# EconomIA 1.14.0: a quantidade de cada item (o − e o + no começo dos botões do cartão, de 1 a 99): o preço mostra o total
# e "2 × R$ …", a economia e o roteiro contam a quantidade, a lista resumida também, e fica guardada. Lojas e preços inventados.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, App, categoria, check, pagina, resumo, shot

OFERTAS = {"versao": 2, "gerado_em": "2026-11-01T10:00:00-03:00",
           "categorias": [categoria("mercados", [("merc-giassi", "Giassi", 1.0), ("merc-fort", "Fort", 2.0)])],
           "lista": [{"produto": "Café torrado em grãos", "precos": {"merc-giassi": 81.9, "merc-fort": 95.8}},
                     {"produto": "Arroz 5 kg", "precos": {"merc-giassi": 24.9, "merc-fort": 22.9}}]}


def limpo(s):
    return " ".join(s.replace("\xa0", " ").split())


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados"], "lista": [{"produto": "Café torrado em grãos"}, {"produto": "Arroz 5 kg"}]}
    with App(cfg, buscar=False, antes=lambda S: S.gravar_json(S.OFERTAS, OFERTAS)) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(300)
            cafe = pg.locator("#wish > li.item", has_text="Café torrado")
            check(limpo(await cafe.locator(".qtd").inner_text()) == "− 1 +" and await cafe.locator('.qtd [data-d="-1"]').is_disabled(), "começa em 1, sem o −")
            hs = await cafe.evaluate("li => [li.querySelector('.qtd').getBoundingClientRect(), li.querySelector('[data-comprei]').getBoundingClientRect()].map(r => [Math.round(r.top), Math.round(r.height)])")
            check(hs[0] == hs[1], f"o − e o + na linha do Comprei hoje, da mesma altura ({hs})")
            check(limpo(await cafe.locator(".i-save").inner_text()) == "economia de R$ 13,90", "economia de 1")
            await cafe.locator('.qtd [data-d="1"]').click()
            await pg.wait_for_timeout(400)
            cafe = pg.locator("#wish > li.item", has_text="Café torrado")
            check(limpo(await cafe.locator(".qtd b").inner_text()) == "2", "o + soma um")
            check([i.get("qtd") for i in app.config_salva()["lista"]] == [2, None], f"fica guardada ({app.config_salva()['lista']})")
            caixa = limpo(await cafe.locator(".i-best .por").inner_text())
            check(caixa == "R$ 163,80 2 × R$ 81,90", f"o preço: o total e 2 × o de um ({caixa})")
            check(limpo(await cafe.locator(".i-save").inner_text()) == "economia de R$ 27,80", "a economia de 2")
            await shot(pg, "quantidade")
            # o roteiro conta a quantidade: 2 cafés e 1 arroz no Giassi (a parada no Fort economizaria só R$ 2,00)
            await pg.click('.tabbar [data-view="roteiro"]')
            await pg.wait_for_timeout(400)
            await pg.click('#rotParadas [data-v="2"]')
            await pg.wait_for_timeout(400)
            total = limpo(await pg.locator("#rotRes .rot-total .por").inner_text())
            check(total == "R$ 188,70", f"o total do roteiro com 2 cafés: 2 × 81,90 + 24,90 ({total})")
            linhas = [limpo(x) for x in await pg.locator("#rotRes .parada li").all_inner_texts()]
            check("2 × Café torrado em grãos R$ 163,80" in linhas, f"a linha do café no roteiro ({linhas})")
            # a resumida: o total e onde
            await pg.click('.tabbar [data-view="lista"]')
            await pg.click('#visLista [data-vis="resumida"]')
            await pg.wait_for_timeout(300)
            mini = limpo(await pg.locator("#wish > li.mini", has_text="Café").inner_text())
            check(mini.endswith("R$ 163,80 2 × · Giassi"), f"a resumida: o total, a quantidade e onde ({mini})")
            await pg.click('#visLista [data-vis="completa"]')
            await pg.wait_for_timeout(300)
            # o − volta para 1 e tira a quantidade dos dados
            await pg.locator("#wish > li.item", has_text="Café torrado").locator('.qtd [data-d="-1"]').click()
            await pg.wait_for_timeout(400)
            check("qtd" not in app.config_salva()["lista"][0], "de volta a 1: sem a quantidade guardada")
            check(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "nada passa da largura")
            await b.close()
            b, pg = await pagina(p, 320, 700, escuro=False)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(300)
            check(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "320 px: nada passa da largura")
            await shot(pg, "quantidade-320")
            await b.close()
    resumo()


asyncio.run(main())
