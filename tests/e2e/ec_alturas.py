# EconomIA 1.11.0: uma altura só, a mesma em todos os apps da família (50 px): botões, campos, caixas de seleção, botões
# de escolha (as abas de Configurações, o Tema) e as escolhas em botões na Minha lista, em Casa, em Lojas e nas quatro
# abas de Configurações (e, desde a 1.16.0, na Compra rápida), no celular (390 e 320 px) e no computador. Ficam de fora os botões só com ícone, os quadrinhos
# da IA, os botões pequenos das linhas da lista (Comprei hoje, remover), os preços das lojas, os interruptores e as cores.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, App, abrir_mais, categoria, check, pagina, resumo, shot

H = 50
CONTROLES = ".btn, .ghost.big, input.field, select.field, .seg, .pick, .mais-abas, .side-busca"
MEDIR = """(sel) => [...document.querySelectorAll(sel)].filter(e => e.offsetParent && e.getBoundingClientRect().width > 4 && !e.closest('.ler-tiles, .tabbar, #lado'))
  .map(e => [e.offsetHeight, (e.className || e.tagName) + ' ' + (e.textContent || e.placeholder || '').replace(/\\s+/g, ' ').trim().slice(0, 30)])"""
OFERTAS = {"versao": 2, "gerado_em": "2026-11-01T10:00:00-03:00", "categorias": [categoria("mercados", [("merc-giassi", "Giassi", 1.0), ("merc-fort", "Fort", 2.0)])],
           "lista": [{"produto": "Arroz 5 kg", "precos": {"merc-giassi": 24.9, "merc-fort": 22.9}}]}


async def conferir(pg, onde):
    hs = await pg.evaluate(MEDIR, CONTROLES)
    fora = [x for x in hs if x[0] != H]
    check(hs and not fora, f"{onde}: {len(hs)} controles, todos com {H} px {fora[:4]}")


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados"], "lista": [{"produto": "Arroz 5 kg"}, {"produto": "Bolacha"}]}
    with App(cfg, buscar=False, antes=lambda S: S.gravar_json(S.OFERTAS, OFERTAS)) as app:
        async with async_playwright() as p:
            for largura, altura in ((390, 844), (320, 700), (1280, 860)):
                pc = largura >= 1000
                b, pg = await pagina(p, largura, altura, toque=not pc)
                await pg.goto(app.url)
                await pg.wait_for_timeout(1200)
                await pg.click('#lado [data-lado="lista"]' if pc else '.tabbar [data-view="lista"]')
                await pg.wait_for_timeout(400)
                await conferir(pg, f"{largura} px › Minha lista")
                if not pc:  # 1.16.0: a Compra rápida, com Como chegar e Buscar preços
                    await pg.click('.tabbar [data-view="roteiro"]')
                    await pg.click('#rotModo [data-modo="rapida"]')
                    for nome in ("Arroz 5 kg", "Pilha AA"):
                        await pg.fill("#rapItem", nome)
                        await pg.click('#rapForm button[type="submit"]')
                    await pg.wait_for_timeout(300)
                    await conferir(pg, f"{largura} px › Compra rápida")
                    # 1.25.2: os itens do mesmo tamanho na linha; nome comprido quebra a linha (nada cortado), com 50 px no mínimo
                    chips = await pg.evaluate("[...document.querySelectorAll('#rapItens .rap-t')].map(e => [e.offsetHeight, Math.round(e.getBoundingClientRect().top)])")
                    linhas = {}
                    for h, t in chips:
                        linhas.setdefault(t, set()).add(h)
                    check(chips and all(h >= H for h, _ in chips) and all(len(v) == 1 for v in linhas.values()), f"{largura} px › os itens da Compra rápida com {H} px ou mais, iguais na linha ({chips})")
                    await pg.click('#rotModo [data-modo="roteiro"]')
                # 1.21.1: Encarte ou print de preços, nas Ofertas: na largura do cartão no celular, 250 px no computador
                await pg.click('#lado [data-lado="ofertas"]' if pc else '.tabbar [data-view="ofertas"]')
                await pg.wait_for_timeout(400)
                w = await pg.evaluate("() => { const b = document.getElementById('encBtn'); return b && b.checkVisibility() ? [Math.round(b.getBoundingClientRect().width), Math.round(b.closest('.row-form').getBoundingClientRect().width), b.offsetHeight] : null; }")
                check(w and w[2] == H and (w[0] == 250 if pc else abs(w[0] - w[1]) <= 1), f"{largura} px › Encarte ou print de preços na largura do cartão ({w})")
                for onde in ("casa", "lojas", "integracoes", "dados", "aparencia", "opcoes"):
                    await abrir_mais(pg, onde, computador=pc)
                    await pg.wait_for_timeout(400)
                    await conferir(pg, f"{largura} px › {onde}")
                    if onde == "casa":  # 1.21.1: o Espaço para estoque na largura do cartão, como os outros campos
                        w = await pg.evaluate("() => { const e = document.getElementById('estoque'); return [Math.round(e.getBoundingClientRect().width), Math.round(e.parentElement.getBoundingClientRect().width)]; }")
                        check(abs(w[0] - w[1]) <= 1, f"{largura} px › Espaço para estoque na largura toda ({w})")
                await shot(pg, f"alturas-{largura}")
                await b.close()
    resumo()


asyncio.run(main())
