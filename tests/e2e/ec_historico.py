# EconomIA 1.60.0 (o dono: "Histórico de preços na tela do EconomIA: hoje só a IA vê; um gráfico no item da lista. Pode
# seguir"): no item da Minha lista, o bloco Histórico de preços (fechado, o de hoje contra a média; aberto, o gráfico do
# menor preço de cada dia, com o menor, o maior e a média); só no item com dois dias ou mais de preço guardado.
import asyncio
from datetime import date, timedelta

from playwright.async_api import async_playwright

from base_e2e import CEP, App, categoria, check, pagina, resumo, shot

OFERTAS = {"versao": 2, "gerado_em": "2026-11-01T10:00:00-03:00",
           "categorias": [categoria("mercados", [("merc-giassi", "Giassi", 1.0), ("merc-fort", "Fort", 2.0)])],
           "lista": [{"produto": "Arroz 5 kg", "precos": {"merc-giassi": 24.9, "merc-fort": 22.9}},
                     {"produto": "Feijão preto 1 kg", "precos": {"merc-fort": 8.9}}]}


def antes(S):
    S.gravar_json(S.OFERTAS, OFERTAS)  # anota o preço de hoje (Fort, 22,90)
    h = S.ler_json(S.PRECOS_DIA, {})
    hoje = date.fromisoformat(S.hoje_br())
    h[S.norm("Arroz 5 kg")]["dias"].update({(hoje - timedelta(days=n)).isoformat(): [v, loja] for n, v, loja in
                                           ((30, 27.9, "Giassi"), (21, 26.9, "Giassi"), (14, 29.9, "Fort"), (7, 25.9, "Giassi"), (3, 26.5, "Fort"), (1, 24.9, "Giassi"))})
    S.gravar_json(S.PRECOS_DIA, h)


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados"], "lista": [{"produto": "Arroz 5 kg"}, {"produto": "Feijão preto 1 kg"}]}
    with App(cfg, buscar=False, antes=antes) as app:
        async with async_playwright() as p:
            for w, escuro in ((390, True), (320, False)):
                b, pg = await pagina(p, w, 844, escuro=escuro)
                await pg.goto(app.url)
                await pg.wait_for_timeout(1200)
                await pg.click('.tabbar [data-view="lista"]')
                await pg.wait_for_timeout(300)
                check(await pg.locator("#wish .i-hist").count() == 1, f"{w}: só o item com dois dias ou mais tem o histórico")
                arroz = pg.locator('#wish li.item[data-k="arroz 5 kg"] .i-hist')
                tit = (await arroz.locator("summary").inner_text()).strip()
                check(tit == "Histórico de preços · 13% abaixo da média", f"{w}: fechado, o de hoje contra a média ({tit})")
                check(not await arroz.locator(".hist-graf").is_visible(), f"{w}: começa fechado")
                await arroz.locator("summary").click()
                await pg.wait_for_timeout(250)
                check(await arroz.locator(".hist-graf .hist-linha").count() == 1 and await arroz.locator(".hist-graf").is_visible(), f"{w}: aberto, o gráfico")
                pts = (await arroz.locator(".hist-linha").get_attribute("points")).split()
                check(len(pts) == 7, f"{w}: um ponto por dia com preço ({len(pts)})")
                txt = " ".join((await arroz.locator(".i-tam").inner_text()).replace("\xa0", " ").split())
                check("Hoje R$ 22,90 (Fort) · média R$ 26,41 em 7 dias" in txt, f"{w}: o de hoje e a média ({txt})")
                check("Menor R$ 22,90" in txt and "maior R$ 29,90" in txt, f"{w}: o menor e o maior")
                check("poucos dias" not in txt, f"{w}: com 7 dias, sem o aviso de poucos dias")
                dx = await pg.evaluate("(() => { const s = document.querySelectorAll('.i-hist .hist-datas span'); return Math.round(s[1].getBoundingClientRect().left - s[0].getBoundingClientRect().right); })()")
                check(dx > 100, f"{w}: a primeira data na esquerda e a última na direita ({dx})")
                cabe = await pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                check(cabe, f"{w}: nada passa da largura")
                await shot(pg, f"historico-{w}")
                # continua aberto depois de a lista ser pintada de novo
                await pg.click('.tabbar [data-view="ofertas"]')
                await pg.click('.tabbar [data-view="lista"]')
                await pg.wait_for_timeout(300)
                check(await arroz.locator(".hist-graf").is_visible(), f"{w}: aberto, continua aberto ao voltar")
                await b.close()
    resumo()


asyncio.run(main())
