# EconomIA 1.56.0 (o dono: "do mesmo jeito que criamos esse agrupar por… a gente precisa adicionar ele em outros locais"; o
# modelo é o dos Consumíveis do InventarIA): Minha lista › Agrupar por Nenhum (a ordem de sempre), Onde comprar (o setor de
# cada item, com mais de um setor ligado) e Loja (onde está o preço escolhido; sem preço no fim), numa barra só, do mesmo
# tamanho; cada grupo com o ícone, o nome e quantos, que fecha pelo nome; o título fecha o bloco; o aparelho lembra.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, App, categoria, check, pagina, resumo, shot

OFERTAS = {"versao": 2, "gerado_em": "2026-11-01T10:00:00-03:00",
           "categorias": [categoria("mercados", [("merc-giassi", "Giassi", 1.0), ("merc-fort", "Fort", 2.0)]),
                          categoria("farmacias", [("farm-sol", "Farmácia Sol", 1.5)])],
           "lista": [{"produto": "Arroz 5 kg", "precos": {"merc-giassi": 24.9, "merc-fort": 22.9}},
                     {"produto": "Café torrado em grãos", "precos": {"merc-giassi": 81.9, "merc-fort": 95.8}},
                     {"produto": "Feijão preto 1 kg", "precos": {"merc-fort": 8.9, "merc-giassi": 9.5}},
                     {"produto": "Protetor solar", "precos": {"farm-sol": 59.9}}]}

GRUPOS = "() => [...document.querySelectorAll('#wish > li.wish-grp')].map(g => { const n = []; let li = g.nextElementSibling; while (li && !li.classList.contains('wish-grp')) { n.push(li.querySelector('.i-prod').textContent); li = li.nextElementSibling; } return [g.querySelector('b').textContent, g.querySelector('.grp-n').textContent, n]; })"


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados", "farmacias"],
           "lista": [{"produto": "Arroz 5 kg"}, {"produto": "Café torrado em grãos", "escolha": {"rede": "merc-giassi", "q": None, "obs": ""}},
                     {"produto": "Feijão preto 1 kg"}, {"produto": "Protetor solar"}, {"produto": "Bolacha recheada"}]}
    with App(cfg, buscar=False, antes=lambda S: S.gravar_json(S.OFERTAS, OFERTAS)) as app:
        async with async_playwright() as p:
            for w, escuro in ((390, True), (320, False)):
                b, pg = await pagina(p, w, 844, escuro=escuro)
                await pg.goto(app.url)
                await pg.wait_for_timeout(1200)
                await pg.click('.tabbar [data-view="lista"]')
                await pg.wait_for_timeout(300)
                ops = [t.strip() for t in await pg.locator("#listaAgrupar .agrupar-seg button").all_inner_texts()]
                check(ops == ["Nenhum", "Onde comprar", "Loja"], f"{w}: Nenhum, Onde comprar e Loja ({ops})")
                check(await pg.get_attribute('#listaAgrupar [data-agrupar=""]', "aria-pressed") == "true" and await pg.locator("#wish > li.wish-grp").count() == 0, f"{w}: Nenhum: a lista de sempre")
                cx = await pg.evaluate("[...document.querySelectorAll('#listaAgrupar .agrupar-seg button')].map(b => { const r = b.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.top)]; })")
                check(len({c[0] for c in cx}) == 1 and len({c[1] for c in cx}) == 1, f"{w}: numa linha, do mesmo tamanho ({cx})")
                # Onde comprar
                await pg.click('#listaAgrupar [data-agrupar="setor"]')
                await pg.wait_for_timeout(300)
                gs = await pg.evaluate(GRUPOS)
                check([g[0] for g in gs] == ["Mercado", "Farmácia", "Qualquer lugar"] and gs[1][2] == ["Protetor solar"] and gs[2][2] == ["Bolacha recheada"],
                      f"{w}: Onde comprar: Mercado, Farmácia e, sem setor, Qualquer lugar ({gs})")
                check(gs[0][1] == "3 itens" and gs[1][1] == "1 item", f"{w}: quantos no título")
                # Loja: a sua escolha vale (o café no Giassi); o mais cheio primeiro; sem preço no fim
                await pg.click('#listaAgrupar [data-agrupar="loja"]')
                await pg.wait_for_timeout(300)
                gs = await pg.evaluate(GRUPOS)
                check([g[0] for g in gs] == ["Fort", "Farmácia Sol", "Giassi", "Sem preço ainda"] and sorted(gs[0][2]) == ["Arroz 5 kg", "Feijão preto 1 kg"] and gs[2][2] == ["Café torrado em grãos"],
                      f"{w}: Loja: a sua escolha vale, o mais cheio primeiro e sem preço no fim ({gs})")
                check(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"{w}: nada passa da largura")
                await shot(pg, f"agrupar-loja-{w}")
                # um grupo fecha pelo nome
                await pg.locator("#wish > li.wish-grp .grp-h").first.click()
                await pg.wait_for_timeout(300)
                gs = await pg.evaluate(GRUPOS)
                check(gs[0][2] == [] and await pg.get_attribute("#wish > li.wish-grp:first-child .grp-h", "aria-expanded") == "false", f"{w}: o grupo fecha pelo nome")
                # o bloco fecha pelo título, com o escolhido ao lado; o aparelho lembra
                await pg.click("#listaAgruparL")
                await pg.wait_for_timeout(200)
                check(await pg.locator("#listaAgrupar .agrupar-seg").count() == 0 and (await pg.locator("#listaAgrupar .agrupar-val").inner_text()).strip() == "· Loja", f"{w}: fechado, o escolhido ao lado")
                await pg.reload()
                await pg.wait_for_timeout(1200)
                await pg.click('.tabbar [data-view="lista"]')
                await pg.wait_for_timeout(300)
                check(await pg.locator("#listaAgrupar.fechado").count() == 1 and (await pg.evaluate(GRUPOS))[0][2] == [], f"{w}: o aparelho lembra a escolha, o bloco e o grupo fechados")
                await pg.click("#listaAgruparL")
                # selecionando, o bloco sai e a lista não se agrupa
                await pg.click("#selBtn")
                await pg.wait_for_timeout(300)
                check(await pg.locator("#listaAgrupar").is_hidden() and await pg.locator("#wish > li.wish-grp").count() == 0, f"{w}: selecionando, sem o Agrupar")
                await pg.go_back()
                await pg.wait_for_timeout(300)
                await pg.click('#listaAgrupar [data-agrupar=""]')
                await pg.wait_for_timeout(300)
                check(await pg.locator("#wish > li.wish-grp").count() == 0 and await pg.locator("#wish > li.item").count() == 5, f"{w}: de volta ao Nenhum")
                await b.close()
    resumo()


asyncio.run(main())
