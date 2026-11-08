# EconomIA 1.2.0: as caixas de seleção (economia/pagina/selectsheet.js, o mesmo arquivo dos outros apps; no add-on,
# embutido na página) não abrem a janela padrão do celular: abrem uma janela no visual do app, de baixo para cima, com
# as opções em linhas e a atual marcada na cor do app, no escuro e no claro. Escolher entra na própria caixa (o app
# ouve o change de sempre e grava); o Voltar do celular, o X e tocar fora fecham só ela, e o Voltar seguinte é o do
# app. No computador, no meio da tela; o teclado também.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, abrir_mais, check, pagina, resumo

HEX = "(h) => { h = h.trim().replace('#', ''); return `rgb(${parseInt(h.slice(0, 2), 16)}, ${parseInt(h.slice(2, 4), 16)}, ${parseInt(h.slice(4, 6), 16)})`; }"


async def tocar(pg, sel):
    loc = pg.locator(sel).first
    await loc.scroll_into_view_if_needed()
    bx = await loc.bounding_box()
    await pg.touchscreen.tap(bx["x"] + bx["width"] / 2, bx["y"] + bx["height"] / 2)
    await pg.wait_for_timeout(450)


async def abrir_casa(pg, computador=False):
    await abrir_mais(pg, "casa", computador)
    await pg.wait_for_timeout(200)


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados"], "lista": [{"produto": "Leite integral"}]}
    with App(cfg, buscar=False) as app:
        async with async_playwright() as p:
            for escuro in (True, False):
                tag = "escuro" if escuro else "claro"
                b, pg = await pagina(p, largura=390, altura=844, escuro=escuro)
                await pg.goto(app.url)
                await pg.wait_for_timeout(1200)
                if not escuro:
                    await abrir_mais(pg, "aparencia")
                    await pg.click('#tema [data-v="claro"]')
                await abrir_casa(pg)
                cx = "#estoque"
                check(await pg.locator(cx).evaluate("(s) => getComputedStyle(s).pointerEvents") == "none", f"{tag}: a caixa nunca recebe o toque (a janela do celular não abre)")
                opts = [o.strip() for o in await pg.locator(f"{cx} option").all_inner_texts()]
                atual = await pg.locator(cx).evaluate("(s) => s.selectedIndex")
                hist = await pg.evaluate("history.length")
                await tocar(pg, cx)
                folha = pg.locator(".ss-wrap.in .ss-sheet")
                check(await folha.count() == 1, f"{tag}: tocar abre a janela")
                check((await folha.locator(".ss-head b").inner_text()).strip() == "Espaço para estoque", f"{tag}: o título é o rótulo da caixa")
                check([t.strip() for t in await folha.locator(".ss-opt").all_inner_texts()] == opts, f"{tag}: as opções em linhas ({opts})")
                check([t.strip() for t in await folha.locator(".ss-opt.on").all_inner_texts()] == [opts[atual]], f"{tag}: a atual marcada")
                cores = await pg.evaluate(f"""(() => {{ const hex = {HEX}, c = getComputedStyle(document.documentElement), s = document.querySelector('.ss-sheet');
                  return [getComputedStyle(s).backgroundColor, hex(c.getPropertyValue('--surface')), getComputedStyle(s.querySelector('.ss-opt.on svg')).color,
                          hex(c.getPropertyValue('--accent')), getComputedStyle(s).color, hex(c.getPropertyValue('--ink'))]; }})()""")
                check(cores[0] == cores[1] and cores[2] == cores[3] and cores[4] == cores[5], f"{tag}: o fundo, a marca e o texto nas cores do app ({cores})")
                bx = await folha.bounding_box()
                check(abs(bx["y"] + bx["height"] - 844) < 2 and bx["width"] >= 389, f"{tag}: de baixo para cima, na largura do celular ({bx})")
                await pg.screenshot(path=f"{SHOTS}/ecselecao-{tag}.png")
                # escolher: entra na caixa e o app grava
                outra = (atual + 1) % len(opts)
                await tocar(pg, f".ss-opt >> nth={outra}")
                await pg.wait_for_timeout(600)
                check(await pg.locator(".ss-wrap").count() == 0, f"{tag}: escolher fecha")
                v = await pg.locator(f"{cx} option").nth(outra).get_attribute("value")
                check(await pg.input_value(cx) == v, f"{tag}: a escolha entra na caixa ({v})")
                # Voltar, X e tocar fora: só a janela
                for como in ("Voltar", "X", "fora"):
                    await tocar(pg, cx)
                    check(await pg.locator(".ss-wrap.in").count() == 1, f"{tag} {como}: abre de novo")
                    if como == "Voltar":
                        await pg.go_back()
                        await pg.wait_for_timeout(500)
                    elif como == "X":
                        await tocar(pg, ".ss-x")
                    else:
                        await pg.touchscreen.tap(195, 40)
                        await pg.wait_for_timeout(450)
                    check(await pg.locator(".ss-wrap").count() == 0 and await pg.input_value(cx) == v and not await pg.locator("#mp-casa").is_hidden(),
                          f"{tag} {como}: fecha só ela, nada muda")
                check(await pg.evaluate("history.length") >= hist, f"{tag}: o histórico do app intacto")
                # gravou: depois de recarregar, a escolha está lá
                await pg.wait_for_timeout(800)
                await pg.reload()
                await pg.wait_for_timeout(1200)
                await abrir_casa(pg)
                check(await pg.input_value(cx) == v, f"{tag}: a escolha ficou gravada")
                check(not pg.erros, f"{tag}: sem erros na página {pg.erros}")
                await b.close()
            # computador: no meio da tela, o teclado
            b, pg = await pagina(p, largura=1280, altura=900, escuro=True, toque=False)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await abrir_casa(pg, computador=True)
            cx = pg.locator("#estoque")
            await cx.scroll_into_view_if_needed()
            bx = await cx.bounding_box()
            await pg.mouse.click(bx["x"] + bx["width"] / 2, bx["y"] + bx["height"] / 2)
            await pg.wait_for_timeout(400)
            sb = await pg.locator(".ss-wrap.in .ss-sheet").bounding_box()
            wb = await pg.locator(".ss-wrap").bounding_box()
            check(sb and abs(sb["x"] + sb["width"] / 2 - (wb["x"] + wb["width"] / 2)) < 2 and abs(sb["y"] + sb["height"] / 2 - 450) < 2 and sb["width"] <= 440,
                  f"computador: no meio da tela ({sb})")
            await pg.keyboard.press("Escape")
            await pg.wait_for_timeout(400)
            check(await pg.locator(".ss-wrap").count() == 0 and await cx.evaluate("(s) => document.activeElement === s"), "computador: Esc fecha e o foco volta para a caixa")
            i0 = await cx.evaluate("(s) => s.selectedIndex")
            n = await cx.locator("option").count()
            await pg.keyboard.press("Enter")
            await pg.wait_for_timeout(300)
            await pg.keyboard.press("ArrowUp" if i0 == n - 1 else "ArrowDown")
            await pg.keyboard.press("Enter")
            await pg.wait_for_timeout(600)
            check(await cx.evaluate("(s) => s.selectedIndex") == (i0 - 1 if i0 == n - 1 else i0 + 1), "computador: Enter abre, as setas e o Enter escolhem")
            check(not pg.erros, f"computador: sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
