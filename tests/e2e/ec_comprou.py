# EconomIA 1.49.0: o Comprei hoje de um item que está na Reposição (pelo nome igual ou parecido) recomeça a contagem de
# hoje e a tela pergunta "Dura quanto tempo?": a resposta vira o A cada da Reposição. Um item fora da Reposição não
# pergunta nada. Casa inventada; 390 px escuro e 320 px claro, sem nada passando da largura.
import asyncio
import datetime
import zoneinfo

from playwright.async_api import async_playwright

from base_e2e import CEP, App, check, espera, pagina, resumo, shot

HOJE = datetime.datetime.now(zoneinfo.ZoneInfo("America/Sao_Paulo")).date()
dia = lambda n: (HOJE + datetime.timedelta(days=n)).isoformat()


def config():
    return {"cep": CEP, "raio_km": 5, "categorias": ["mercados"],
            "lista": [{"produto": "Creme de mãos Nivea 50 g"}, {"produto": "Leite integral"}],
            "reposicao": [{"id": "aaaa1", "nome": "Creme de mãos", "cada": 1, "unidade": "mes", "desde": dia(-40)}]}


async def main():
    async with async_playwright() as p:
        for largura, escuro in ((390, True), (320, False)):
            tag = f"{largura} px {'escuro' if escuro else 'claro'}"
            with App(config(), buscar=False) as app:
                b, pg = await pagina(p, largura=largura, escuro=escuro)
                await pg.goto(app.url)
                await pg.wait_for_selector("[data-comprei]")
                check(await pg.locator("#repComprou").is_hidden(), f"{tag}: sem compra, sem a pergunta")
                check(await pg.locator("#repAgora").is_visible(), f"{tag}: o creme está na Hora de repor")
                # um item fora da Reposição: nada é perguntado
                await pg.locator(".item", has_text="Leite integral").locator("[data-comprei]").click()
                await pg.wait_for_timeout(400)
                check(await pg.locator("#repComprou").is_hidden(), f"{tag}: o leite não está na Reposição: sem a pergunta")
                # o item parecido com o da Reposição: recomeça de hoje e pergunta
                await pg.locator(".item", has_text="Creme de mãos Nivea 50 g").locator("[data-comprei]").click()
                await pg.wait_for_selector("#repComprou:not([hidden])")
                txt = " ".join((await pg.locator("#repComprouTxt").inner_text()).split())
                check(txt.startswith("Você comprou Creme de mãos Nivea 50 g."), f"{tag}: diz o que foi comprado ({txt})")
                ops = await pg.evaluate("[...document.querySelectorAll('#repComprouOp .pick')].map(b => [b.textContent.trim(), b.getAttribute('aria-pressed')])")
                check([o[0] for o in ops] == ["1 semana", "15 dias", "1 mês", "2 meses", "3 meses", "6 meses", "1 ano", "2 anos"], f"{tag}: os tempos ({ops})")
                check([o[0] for o in ops if o[1] == "true"] == ["1 mês"], f"{tag}: o de hoje vem marcado")
                check(await pg.locator("#repAgora").is_hidden(), f"{tag}: comprado, sai da Hora de repor")
                await espera(pg, "() => true")
                await pg.wait_for_timeout(600)
                rep = app.config_salva()["reposicao"][0]
                check(rep["desde"] == dia(0) and rep["cada"] == 1, f"{tag}: a Reposição recomeça de hoje, com o mesmo A cada ({rep})")
                check(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"{tag}: nada passa da largura")
                hs = await pg.evaluate("[...document.querySelectorAll('#repComprouOp .pick, #repComprouNao')].map(b => b.offsetHeight)")
                check(set(hs) == {50}, f"{tag}: tudo com 50 px ({hs})")
                await shot(pg, f"comprou-{largura}")
                await pg.locator("#repComprouOp .pick", has_text="3 meses").click()
                await pg.wait_for_timeout(700)
                check(await pg.locator("#repComprou").is_hidden(), f"{tag}: escolhido, a pergunta sai")
                rep = app.config_salva()["reposicao"][0]
                check((rep["cada"], rep["unidade"], rep["desde"]) == (3, "mes", dia(0)), f"{tag}: o A cada vira 3 meses ({rep})")
                check(len(app.config_salva()["reposicao"]) == 1, f"{tag}: o item parecido é o mesmo: não entra outro")
                # Agora não: fecha sem mudar o A cada
                await pg.reload()
                await pg.wait_for_selector("[data-comprei]")
                await pg.locator(".item", has_text="Creme de mãos Nivea 50 g").locator("[data-comprei]").click()
                await pg.wait_for_selector("#repComprou:not([hidden])")
                await pg.click("#repComprouNao")
                await pg.wait_for_timeout(300)
                check(await pg.locator("#repComprou").is_hidden() and app.config_salva()["reposicao"][0]["cada"] == 3, f"{tag}: Agora não deixa como está")
                check(not pg.erros, f"{tag}: sem erros na página {pg.erros}")
                await b.close()


asyncio.run(main())
resumo()
