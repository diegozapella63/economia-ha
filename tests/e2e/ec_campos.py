# EconomIA 1.19.0, o padrão da família: os campos de texto aberto (o Colar mensagem) aumentam puxando o canto e guardam
# o tamanho no aparelho (textareas.js, o mesmo arquivo dos outros apps; no add-on, embutido na página); aberto de novo,
# o campo volta como ficou. A caixa da Conversa (que cresce sozinha) fica de fora. 390 px, escuro. E os botões das telas
# de Mais (fora de Dados, que já era assim) na largura do cartão no celular, dois lado a lado dividindo a linha; 250 px
# no computador; as linhas com um campo (o CEP, Nunca mostrar) ficam como estão. E a ação do meio da barra de baixo
# (Buscar) só com o ícone: o nome fica para o leitor de tela.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, HAFalso, abrir_mais, check, pagina, resumo

CFG = {"cep": CEP, "raio_km": 5, "categorias": ["mercados"], "ia": {"fotos": "ai_task.claude"}, "lista": [{"produto": "Leite integral"}]}


LARG = """(s) => [...document.querySelectorAll(s)].filter((b) => b.checkVisibility()).map((b) => { const p = b.closest('.panel, section'), cs = getComputedStyle(p);
  return [Math.round(b.getBoundingClientRect().width), Math.round(p.getBoundingClientRect().width - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight))]; })"""


async def colar(pg):
    await pg.click('.tabbar [data-view="lista"]')
    await pg.wait_for_timeout(300)
    await pg.click("#textoBtn")
    await pg.wait_for_timeout(300)


async def main():
    ha = HAFalso()
    ha.tarefa_ia("ai_task.claude", "Claude")
    with App(CFG, buscar=False, ha=ha) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await colar(pg)
            ta = pg.locator("#fotoTxt")
            check(await ta.is_visible(), "Colar mensagem aberto")
            check(await ta.evaluate("(e) => getComputedStyle(e).resize") == "vertical", "Colar mensagem: dá para aumentar")
            await ta.evaluate("(e) => { e.style.height = '240px'; }")  # como puxar o canto
            await pg.wait_for_timeout(700)
            await pg.reload()
            await pg.wait_for_timeout(1200)
            await colar(pg)
            h = await pg.locator("#fotoTxt").evaluate("(e) => Math.round(parseFloat(e.style.height))")
            check(h == 240, f"aberto de novo, do tamanho que ficou ({h})")
            chaves = await pg.evaluate("Object.keys(localStorage).filter((k) => k.startsWith('textareas:'))")
            check(chaves == ["textareas:EconomIA:fotoTxt"], f"guardado no aparelho, com o nome do app ({chaves})")
            check(await pg.locator("#chatTxt").evaluate("(e) => getComputedStyle(e).resize") != "vertical", "a caixa da Conversa fica de fora")
            await pg.locator("#fotoTxt").scroll_into_view_if_needed()
            await pg.screenshot(path=f"{SHOTS}/ec-campos-390.png")
            # a ação do meio só com o ícone, no meio da barra
            meio = await pg.evaluate("""() => { const b = document.getElementById('buscar'), t = document.getElementById('buscarTxt'), c = (e) => { const r = e.getBoundingClientRect(); return r.top + r.height / 2; };
              return [t.textContent, Math.round(t.getBoundingClientRect().width), Math.round(Math.abs(c(b.querySelector('.pill')) - c(document.querySelector('.tabbar [data-view="mais"]'))))]; }""")
            check(meio[0] == "Buscar" and meio[1] <= 1 and meio[2] <= 3, f"Buscar só com o ícone, no meio da barra ({meio})")
            # os botões de Mais › Configurações › Integrações
            await abrir_mais(pg, "integracoes")
            await pg.wait_for_timeout(500)
            w = await pg.evaluate(LARG, "#iaTestar")
            check(w and abs(w[0][0] - w[0][1]) <= 2, f"Verificar de novo na largura do cartão ({w})")
            par = await pg.evaluate(LARG, "#shSalvar, #shTestar")
            check(len(par) == 2 and par[0][0] == par[1][0] and abs(par[0][0] * 2 + 8 - par[0][1]) <= 3, f"Salvar e testar e Testar dividem a linha ({par})")
            await pg.locator("#iaTestar").scroll_into_view_if_needed()
            await pg.screenshot(path=f"{SHOTS}/ec-campos-integracoes-390.png")
            await abrir_mais(pg, "casa")
            await pg.wait_for_timeout(400)
            cep = await pg.evaluate(LARG, "#ondeForm .row-form .btn")
            check(cep and cep[0][0] < 120, f"a linha do CEP fica como está ({cep})")
            achar = await pg.evaluate(LARG, "#acharLojas")
            check(achar and abs(achar[0][0] - achar[0][1]) <= 2, f"Encontrar lojas na largura do cartão ({achar})")
            check(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "nada passa da largura")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()
            # no computador, 250 px
            b, pg = await pagina(p, largura=1280, altura=900, escuro=False, toque=False)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await abrir_mais(pg, "integracoes", computador=True)
            await pg.wait_for_timeout(500)
            w = await pg.evaluate(LARG, "#iaTestar, #shSalvar, #shTestar")
            check(w and all(x == 250 for x, _ in w), f"no computador, 250 px ({w})")
            await b.close()


asyncio.run(main())
resumo()
