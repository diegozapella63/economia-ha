# EconomIA 0.19.0: no computador (1280 px): a barra lateral (telas, itens acabando, Buscar ofertas com o andamento, as
# ofertas por tipo de loja), sem a barra de abas de baixo, as ações no alto (Ler com IA, Adicionar item) e as colunas
# lado a lado (Ofertas e cupons, Mais › Casa).
import asyncio
import threading
from datetime import datetime, timedelta, timezone

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, HAFalso, categoria, check, espera, pagina, resumo

HOJE = (datetime.now(timezone.utc) - timedelta(hours=3)).date()
D = lambda n: (HOJE + timedelta(days=n)).isoformat()  # noqa: E731
OF = lambda i, rede, prod, por, de: {"id": i, "rede": rede, "produto": prod, "preco_oferta": por, "preco_normal": de, "tipo": "promo", "tags": []}  # noqa: E731
OFERTAS = {"versao": 2, "gerado_em": "2026-11-02T10:00:00-03:00", "lista": [{"produto": "Leite integral", "precos": {"merc-giassi": 4.89, "merc-fort": 4.49}}],
           "categorias": [categoria("mercados", [("merc-giassi", "Giassi", 1.0), ("merc-fort", "Fort", 2.0)],
                                    ofertas=[OF("a", "merc-giassi", "Arroz 5 kg", 21.9, 27.9), OF("b", "merc-fort", "Feijão 1 kg", 6.9, 8.9)],
                                    cupons=[{"rede": "merc-giassi", "codigo": "GI10", "valor": 10, "beneficio": "R$ 10", "condicao": "", "valido_ate": D(5), "status": "confirmado"}]),
                          categoria("farmacias", [("farm-panvel", "Panvel", 1.0)], ofertas=[OF("c", "farm-panvel", "Dipirona 1 g", 8.9, 12.9)])]}


async def caixa(pg, sel):
    return await pg.locator(sel).bounding_box()


async def main():
    ha = HAFalso()
    solta = threading.Event()
    ha.responde_ia("EconomIA: mercados", lambda c: (solta.wait(30), {"lojas": []})[1])
    ha.responde_ia("EconomIA: farmacias", {"lojas": []})
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados", "farmacias"], "opcoes": {"itens_sem_preco": False},
           "lista": [{"produto": "Leite integral", "compras": [D(-14), D(-7)]}, {"produto": "Café"}]}
    with App(cfg, buscar=False, antes=lambda S: S.gravar_json(S.OFERTAS, OFERTAS), ha=ha) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p, largura=1280, altura=900, toque=False)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            check(await pg.locator("#lado").is_visible() and await pg.locator("#views").is_hidden(), "barra lateral no lugar da barra de abas")
            nav = [t.strip() for t in await pg.locator("#lado .side-link span:not(.sl-num):not(.side-badge)").all_inner_texts()]
            check(nav == ["Minha lista", "Roteiro", "Ofertas", "Mais"], f"as telas na barra lateral ({nav})")
            check(await pg.text_content('#lado [data-lado="lista"] .side-badge') == "1", "1 item acabando na Minha lista")
            cats = [(await x.locator(".sl-nome").inner_text(), await x.locator(".sl-num").inner_text()) for x in await pg.locator("#lado .side-item").all()]
            check(cats == [("Mercados", "2"), ("Farmácias", "1")] and await pg.text_content("#lado .side-h small") == "3", f"as ofertas por tipo de loja ({cats})")
            check(await pg.locator(".top-acts").is_visible() and await pg.locator(".cab-topo .mic-top.so-voz").is_hidden(), "as ações no alto")
            await pg.screenshot(path=SHOTS + "/ecdk-lista.png")
            # ofertas pela barra lateral, com as colunas lado a lado
            await pg.click('#lado [data-lado-cat="farmacias"]')
            check(await pg.locator("#v-ofertas").is_visible() and await pg.get_attribute('#cats [data-cat="farmacias"]', "aria-pressed") == "true", "a categoria abre em Ofertas")
            check(await pg.get_attribute('#lado [data-lado-cat="farmacias"]', "aria-current") == "page", "e fica marcada na barra")
            await pg.click('#lado [data-lado-cat="mercados"]')
            a, c = await caixa(pg, 'section[aria-labelledby="h-ofertas"]'), await caixa(pg, 'section[aria-labelledby="h-cupons"]')
            check(abs(a["y"] - c["y"]) < 2 and c["x"] > a["x"] + a["width"] - 1, "Ofertas e Cupons lado a lado")
            await pg.screenshot(path=SHOTS + "/ecdk-ofertas.png")
            await pg.click('#lado [data-lado="mais"]')
            await pg.click("#aba-casa")
            a, c = await caixa(pg, 'section[aria-labelledby="h-onde"]'), await caixa(pg, 'section[aria-labelledby="h-restr"]')
            check(abs(a["y"] - c["y"]) < 2 and c["x"] > a["x"], "Mais › Casa em duas colunas")
            # ações do alto
            await pg.click('.top-acts [data-acao="adicionar"]')
            check(await pg.locator("#v-lista").is_visible() and await pg.evaluate("document.activeElement.id") == "novoItem", "Adicionar item vai para o campo da lista")
            await pg.click('.top-acts [data-acao="ler"]')
            check(await pg.locator("#fotoTxt").is_visible() and await pg.evaluate("document.activeElement.id") == "fotoTxt", "Ler com IA abre o campo da mensagem")
            await pg.click("#fotoFechar")
            # Buscar ofertas pela barra lateral
            await pg.click('#lado [data-lado="buscar"]')
            await espera(pg, "() => /Buscando…/.test(document.querySelector('#lado .side-busca').textContent)")
            check(await pg.is_disabled("#lado .side-busca"), "Buscando… na barra lateral, desligado")
            await espera(pg, "() => /Buscando mercados \\(1 de 2\\)/.test(document.getElementById('buscaMsg').textContent)")
            check(True, "o andamento com a categoria e quantas faltam")
            await pg.screenshot(path=SHOTS + "/ecdk-buscando.png")
            solta.set()
            await espera(pg, "() => /Buscar ofertas/.test(document.querySelector('#lado .side-busca').textContent)", 20000)
            check(not await pg.is_disabled("#lado .side-busca"), "terminou: Buscar ofertas de novo")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
