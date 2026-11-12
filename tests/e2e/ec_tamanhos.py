# EconomIA 0.19.0: na Minha lista, a Melhor compra pelo tamanho (galão de 5 L contra 5 × 1 L), Comparar tamanhos (do mais
# barato por litro), escolher um tamanho, o espaço para estoque ("Compensa, mas dura muito"), a decisão online ou na loja
# (Compensa pedir, Confira o frete, Compra na loja, Só online, Compra na loja agora porque chega depois de acabar) e o
# preço de clube (a dica para quem não marcou e o preço de sócio depois de marcar em Mais › Lojas).
import asyncio
from datetime import datetime, timedelta, timezone

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, abrir_mais, categoria, check, pagina, resumo

HOJE = (datetime.now(timezone.utc) - timedelta(hours=3)).date()
D = lambda n: (HOJE + timedelta(days=n)).isoformat()  # noqa: E731
AMZ = lambda preco, frete=0, prazo=None: dict({"preco": preco, "frete": frete}, **({"prazo_dias": prazo} if prazo is not None else {}))  # noqa: E731

OFERTAS = {"versao": 2, "gerado_em": "2026-11-02T10:00:00-03:00", "categorias": [
    categoria("mercados", [("merc-giassi", "Giassi", 0.8), ("merc-fort", "Fort Atacadista", 3.0)]),
    categoria("farmacias", [("farm-panvel", "Panvel", 1.0), ("farm-nissei", "Farmácias Nissei", 1.5)]),
    categoria("online", [("onli-amazon", "Amazon", None), ("onli-mercado-livre", "Mercado Livre", None)])],
    "lista": [
        {"produto": "Lysoform", "precos": {"merc-giassi": 21.9, "merc-fort": 19.9}, "base": {"quantidade": 1, "unidade": "L"},
         "tamanhos": [{"rede": "merc-fort", "embalagem": "Galão 5 L", "quantidade": 5, "preco": 69.9}]},
        {"produto": "Café Pilão 500 g", "precos": {"merc-giassi": 19.9, "onli-amazon": AMZ(16.9, 0, 2)}},
        {"produto": "Arroz 5 kg", "precos": {"merc-giassi": 24.9, "onli-mercado-livre": {"preco": 22.9, "frete": None, "carrinho": True}}},
        {"produto": "Sabão em pó 1 kg", "precos": {"merc-giassi": 15.9, "onli-amazon": AMZ(14.9, 5.0)}},
        {"produto": "Ração Golden 10 kg", "precos": {"onli-amazon": AMZ(129.9)}},
        {"produto": "Leite em pó", "precos": {"merc-giassi": 25.9, "onli-amazon": AMZ(20.9, 0, 5)}},
        {"produto": "Dipirona", "precos": {"farm-panvel": {"preco": 8.9, "clube": 6.9}, "farm-nissei": 7.9}}]}


async def item(pg, nome):
    return pg.locator("#wish > li.item", has_text=nome).first


async def txt(loc):
    return (await loc.inner_text()).replace("\xa0", " ")


async def abre(pg, nome):
    it = await item(pg, nome)
    await it.locator("details.i-det").first.evaluate("d => { d.open = true; }")  # o aberto fica lembrado entre um desenho e outro
    await pg.wait_for_timeout(100)
    return it


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados", "farmacias", "online"], "cotidiano": {"estoque": "normal"},
           "lista": [{"produto": "Lysoform", "compras": [D(-60), D(-30)]}, {"produto": "Café Pilão 500 g"}, {"produto": "Arroz 5 kg"},
                     {"produto": "Sabão em pó 1 kg"}, {"produto": "Ração Golden 10 kg"}, {"produto": "Leite em pó", "compras": [D(-20), D(-10)]},
                     {"produto": "Dipirona"}]}
    with App(cfg, buscar=False, antes=lambda S: S.gravar_json(S.OFERTAS, OFERTAS)) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(400)
            # ----- Melhor tamanho -----
            lys = await item(pg, "Lysoform")
            best = await txt(lys.locator(".i-best"))
            check("MELHOR COMPRA" in best.upper() and "R$ 13,98 por litro" in " ".join(best.split()) and "Galão 5 L por R$ 69,90 · Fort Atacadista" in best,
                  f"Melhor compra: o galão, pelo preço do litro ({best})")
            check("O próximo mais barato: R$ 19,90 por litro · 1 L por R$ 19,90 (Fort Atacadista)" in await txt(lys), "1.36.8: e o próximo mais barato, por litro")
            check("economia de R$ 5,92/L" in await txt(lys.locator(".i-head")), "economia por litro em relação ao avulso")
            lys = await abre(pg, "Lysoform")
            det = await txt(lys.locator("details.i-det"))
            check(det.startswith("Comparar tamanhos (3)"), f"Comparar tamanhos ({det[:40]})")
            check("COMPENSA O MAIOR" in det.upper() and "Sai R$ 13,98/L, contra R$ 19,90/L no próximo mais barato (1 L, Fort Atacadista). No seu ritmo, dura uns 5 meses." in det, f"por que compensa ({det})")
            linhas = [await txt(li) for li in await lys.locator(".tam-list li").all()]
            check(len(linhas) == 3 and "Galão 5 L" in linhas[0] and "R$ 13,98/L" in linhas[0] and "R$ 21,90/L" in linhas[2], "do mais barato por litro para o mais caro")
            await lys.screenshot(path=SHOTS + "/ect-lysoform.png")
            # 1.25.0: no Roteiro, sem escolha sua, o que compensa mais já vale: o galão no Fort, pelo preço do galão
            await pg.click('.tabbar [data-view="roteiro"]')
            await pg.wait_for_timeout(400)
            fort = " ".join((await pg.locator("#rotRes .parada", has_text="Fort Atacadista").inner_text()).replace("\xa0", " ").split())
            check("Lysoform Galão 5 L, o que compensa mais R$ 69,90" in fort, f"o roteiro já leva o galão ({fort[:160]})")
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(400)
            lys = await abre(pg, "Lysoform")
            await lys.locator(".tam-list li").nth(0).locator(".esc-btn").click()
            await pg.wait_for_timeout(800)
            e = next(i for i in app.config_salva()["lista"] if i["produto"] == "Lysoform").get("escolha")
            check(e == {"rede": "merc-fort", "q": 5, "obs": "Galão 5 L"}, f"escolher o galão fica salvo ({e})")
            check("SUA ESCOLHA" in (await txt((await item(pg, "Lysoform")).locator(".i-best"))).upper(), "e vira Sua escolha")
            await (await item(pg, "Lysoform")).locator("[data-desescolher]").click()
            await pg.wait_for_timeout(600)
            # pouco espaço para estoque: o galão dura demais
            await abrir_mais(pg, "casa")
            await pg.select_option("#estoque", "pouco")
            await pg.wait_for_timeout(500)
            check(app.config_salva()["cotidiano"]["estoque"] == "pouco", "estoque: pouco")
            await pg.click('.tabbar [data-view="lista"]')
            lys = await item(pg, "Lysoform")
            check("MAIS BARATO" in (await txt(lys.locator(".i-best"))).upper(), "com pouco espaço, o de sempre volta a ser a compra")
            lys = await abre(pg, "Lysoform")
            det = await txt(lys.locator("details.i-det"))
            check("COMPENSA, MAS DURA MUITO" in det.upper() and "mais do que você costuma guardar. Fique no de 1 L ou mude o espaço para estoque em Mais › Casa." in det, f"avisa que dura demais ({det[-160:]})")
            # ----- online ou na loja -----
            casos = [("Café Pilão", "Online ou na loja", "COMPENSA PEDIR", "Economiza R$ 3,00 pedindo online."),
                     ("Arroz 5 kg", "Online ou na loja", "CONFIRA O FRETE", "Online sai R$ 2,00 mais barato antes do frete, que só aparece no carrinho."),
                     ("Sabão em pó", "Online ou na loja", "COMPRA NA LOJA", "Com o frete de R$ 5,00, o online sai R$ 4,00 mais caro."),
                     ("Leite em pó", "Online ou na loja", "COMPRA NA LOJA AGORA", "Online sai R$ 5,00 mais barato, mas chega depois de acabar. Na próxima, peça até ")]
            for nome, resumo_, chip, nota in casos:
                it = await abre(pg, nome)
                det = await txt(it.locator("details.i-det"))
                check(det.startswith(resumo_) and chip in det.upper() and nota in det, f"{nome}: {chip.lower()} ({det[:200]})")
            await (await item(pg, "Arroz 5 kg")).screenshot(path=SHOTS + "/ect-arroz.png")
            rac = await txt(await item(pg, "Ração Golden"))
            check("Amazon" in rac and "R$ 129,90" in rac, "só online: o preço da Amazon")
            it = await abre(pg, "Ração Golden")
            check("SÓ ONLINE" in (await txt(it.locator("details.i-det"))).upper(), "Só online")
            # ----- preço de clube -----
            dip = await item(pg, "Dipirona")
            check("Panvel tem preço de clube: R$ 6,90. Se você for do clube, marque em Mais › Lojas." in await txt(dip), "a dica do clube para quem não marcou")
            check("Farmácias Nissei" in await txt(dip.locator(".i-best")), "sem o clube, a Nissei é a mais barata")
            await abrir_mais(pg, "lojas")
            await pg.click('#lojasAbas [data-loja-aba="farmacias"]')
            await pg.click('#lojasCats [data-clube="farm-panvel"]')
            await pg.wait_for_timeout(700)
            check(app.config_salva()["clubes"] == ["farm-panvel"], "sócio do Bem Panvel")
            await pg.click('.tabbar [data-view="lista"]')
            dip = await item(pg, "Dipirona")
            best = (await txt(dip.locator(".i-best"))).upper()
            check("R$ 6,90" in best and "PANVEL" in best and "CLUBE" in best, f"sócio: o preço de clube vale ({best})")
            check("tem preço de clube" not in await txt(dip), "a dica some")
            await dip.screenshot(path=SHOTS + "/ect-clube.png")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
