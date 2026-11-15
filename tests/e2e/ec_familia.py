# EconomIA 1.37.0, o padrão da família: o ícone antes do título de cada opção e campo de Mais e em cada botão; sem linha
# entre as opções; o que depende de uma chave num quadro embaixo dela (a IA embaixo de Usar IA, os sensores embaixo de
# Criar sensores); a seta nas abas que não cabem; toda seção fecha e abre pelo cabeçalho e o aparelho lembra. No celular,
# o nome do item novo fica na linha toda (com o ícone, o Adicionar deixava a caixa com 24 px em 320 px).
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, abrir_mais, check, pagina, resumo


async def main():
    with App({"cep": CEP, "categorias": ["mercados"], "lista": []}, buscar=False) as app:
        async with async_playwright() as p:
            for largura in (390, 320):
                b, pg = await pagina(p, largura=largura)
                await pg.goto(app.url)
                await pg.wait_for_timeout(1200)
                tag = f"{largura}px"
                # Minha lista: o nome do item na linha toda no celular, os botões (Adicionar com o ícone) embaixo
                await pg.click('.tabbar [data-view="lista"]')
                await pg.wait_for_timeout(300)
                cx = await pg.evaluate("() => { const i = document.getElementById('novoItem'), a = document.querySelector('#addForm button[type=submit]'), f = document.getElementById('addForm'); return [Math.round(i.getBoundingClientRect().width), Math.round(f.clientWidth), a.getBoundingClientRect().top > i.getBoundingClientRect().bottom - 1, Math.round(a.getBoundingClientRect().height)] }")
                check(cx[0] == cx[1] and cx[2] and cx[3] == 50, f"{tag}: Minha lista, o nome na linha toda e os botões embaixo ({cx})")
                await abrir_mais(pg, "integracoes")
                await pg.wait_for_timeout(500)
                sem = await pg.evaluate("() => [...document.querySelectorAll('#mp-integracoes .set-t, #mp-integracoes .sh-row > label')].filter(e => e.offsetParent && !e.querySelector('.t-ic')).map(e => e.textContent.trim())")
                check(not sem, f"{tag}: cada título de opção e de campo com o ícone {sem[:4]}")
                botoes = await pg.evaluate("() => [...document.querySelectorAll('#mp-integracoes button')].filter(b => b.offsetParent && b.textContent.trim().length > 1 && !b.querySelector('svg')).map(b => b.textContent.trim())")
                check(not botoes, f"{tag}: cada botão com o ícone {botoes[:4]}")
                linhas = await pg.evaluate("() => [...document.querySelectorAll('.panel.settings .set-row')].filter(r => r.offsetParent && parseFloat(getComputedStyle(r).borderTopWidth) > 0).length")
                check(linhas == 0, f"{tag}: sem linha entre as opções ({linhas})")
                check(await pg.locator("#iaDet.sub-op > .sub-box #iaBusca").count() == 1, f"{tag}: a IA num quadro embaixo de Usar IA")
                # Criar sensores: a lista num quadro embaixo da chave
                if not await pg.locator("#sensores").is_checked():
                    await pg.click("label[for=sensores]")
                    await pg.wait_for_timeout(500)
                cods = await pg.locator("#sensLista .sensor-row code").all_inner_texts()
                check(await pg.locator("#sensLista").is_visible() and cods == ["sensor.economia_ia_hoje", "sensor.economia_melhor_loja", "binary_sensor.economia_oferta"], f"{tag}: Criar sensores e a lista embaixo ({cods})")
                await pg.click("label[for=sensores]")
                await pg.wait_for_timeout(500)
                check(not await pg.locator("#sensLista").is_visible(), f"{tag}: desligado, sem a lista")
                cls = await pg.evaluate("() => document.getElementById('maisAbas').parentElement.className")
                cabe = await pg.evaluate("() => { const t = document.getElementById('maisAbas'); return t.scrollWidth <= t.clientWidth + 2 }")
                check("abas-wrap" in cls and (("tem-dir" in cls) == (not cabe)), f"{tag}: a seta só quando as abas não cabem ({cls}, cabe {cabe})")
                # contrair e expandir, guardado no aparelho
                h = pg.locator("#h-ia")
                check(await h.get_attribute("aria-expanded") == "true", f"{tag}: IA do Home Assistant fecha e abre, aberta de início")
                await h.click()
                await pg.wait_for_timeout(200)
                check(await h.get_attribute("aria-expanded") == "false" and not await pg.locator("#usarIA").is_visible(), f"{tag}: um toque fecha")
                await pg.reload()
                await pg.wait_for_timeout(1200)
                await abrir_mais(pg, "integracoes")
                await pg.wait_for_timeout(400)
                check(await pg.locator("#h-ia").get_attribute("aria-expanded") == "false", f"{tag}: continua fechada ao abrir de novo")
                await pg.locator("#h-ia").click()
                await pg.wait_for_timeout(200)
                check(await pg.locator("#usarIA").is_visible() or await pg.locator("label[for=usarIA]").is_visible(), f"{tag}: abre de novo")
                if largura == 390:
                    await pg.screenshot(path=SHOTS + "/ecf-integracoes.png")
                check(not pg.erros, f"{tag}: sem erros na página {pg.erros[:2]}")
                await b.close()
    return resumo()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
