# EconomIA 1.3.0: Mais é um menu, como no GerencIA e no InventarIA: Casa, Lojas, Configurações e, por último, Sobre,
# cada linha com o ícone no quadradinho, o título, uma linha do que tem e a seta, e cada uma abre a sua tela.
# Configurações tem as abas Integrações, Dados, Aparência e Opções (a aba fica guardada). O ‹ Mais, o Voltar do celular,
# arrastar para a direita e o Mais de baixo (ou da barra lateral) voltam ao menu; recarregar volta na mesma tela. Um
# atalho de fora (Preencher o perfil) abre Casa e o Voltar volta para a Minha lista. Quem vinha das abas da 1.2 volta no
# mesmo lugar, já no caminho novo. 390 px escuro, 320 px claro e o computador, sem nada passando da borda.
import asyncio
import json
import os
import re

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, check, espera, pagina, resumo

LINHAS = [("casa", "Casa", "CEP, quem mora, rotina e preferências."),
          ("lojas", "Lojas", "Perto de casa, clubes e cupons do app."),
          ("config", "Configurações", "Integrações, dados, aparência e opções."),
          ("sobre", "Sobre", "CorrerIA Code, os apps e o GitHub.")]
ABAS = [("integracoes", "Integrações"), ("dados", "Dados"), ("aparencia", "Aparência"), ("opcoes", "Opções")]
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VERSAO = re.search(r'^version:\s*"?([\d.]+)', open(os.path.join(RAIZ, "economia", "config.yaml"), encoding="utf-8").read(), re.M).group(1)

# o que está à vista e o que ficou guardado
TELA = """() => { const vis = (el) => !!el && el.getClientRects().length > 0, ui = JSON.parse(localStorage.getItem('ofertas-bairro:ui') || '{}');
  return {titulo: document.getElementById('screenTitle').textContent, volta: vis(document.getElementById('maisVolta')),
    menu: vis(document.getElementById('maisMenu')), abas: vis(document.getElementById('maisAbas')),
    paineis: [...document.querySelectorAll('#v-mais > .mais-painel')].filter(vis).map((p) => p.id),
    linha: vis(document.querySelector('.cab .sync')), pe: vis(document.getElementById('maisPe')),
    telas: [...document.querySelectorAll('.wrap > .view')].filter(vis).map((v) => v.id),
    hist: (history.state && history.state.tela) || '', tela: ui.maisTela || '', aba: ui.maisAba || '', y: Math.round(scrollY),
    fora: document.documentElement.scrollWidth - innerWidth}; }"""
LINHAS_JS = """() => { const lista = document.querySelector('#maisMenu .menu-list').getBoundingClientRect();
  return [...document.querySelectorAll('#maisMenu .menu-row')].map((r) => { const b = r.getBoundingClientRect(), t = r.querySelector('.mb b'), s = r.querySelector('.mb > span');
    return {k: r.dataset.mais, t: t.textContent, s: s.textContent, ic: !!r.querySelector('.h-ic svg'), chev: !!r.querySelector('svg.chev'),
      x: b.left - lista.left, w: b.width - lista.width, y: b.top, fim: b.bottom, h: b.height,
      cortado: [t, s].some((e) => e.scrollWidth > e.clientWidth + 1 || e.getBoundingClientRect().right > b.right + 1)}; }); }"""
ARRASTA = """(dx) => { const el = document.getElementById('screenTitle'), r = el.getBoundingClientRect();
  const x = innerWidth / 2 - dx / 2, y = r.top + r.height / 2, t0 = new Touch({identifier: 1, target: el, clientX: x, clientY: y});
  el.dispatchEvent(new TouchEvent('touchstart', {touches: [t0], changedTouches: [t0], bubbles: true}));
  const t1 = new Touch({identifier: 1, target: el, clientX: x + dx, clientY: y + 4});
  el.dispatchEvent(new TouchEvent('touchend', {touches: [], changedTouches: [t1], bubbles: true})); }"""


async def tela(pg):
    return await pg.evaluate(TELA)


async def no_menu(pg, txt):
    """O menu de Mais: título Mais, o menu e o rodapé; sem o ‹ Mais, as abas, os painéis, a linha da busca e a entrada no histórico."""
    await espera(pg, "() => !(history.state && history.state.tela) && !document.getElementById('maisMenu').hidden")
    t = await tela(pg)
    check(t["titulo"] == "Mais" and t["menu"] and not t["volta"] and not t["abas"] and t["paineis"] == [] and t["pe"] and not t["linha"]
          and t["tela"] == "" and t["telas"] == ["v-mais"] and t["fora"] == 0, f"{txt}: o menu de Mais ({t})")


async def abre(pg, k):
    await pg.click(f'#maisMenu [data-mais="{k}"]')
    await espera(pg, f"() => history.state && history.state.tela === '{k}'")


async def na_tela(pg, k, titulo, paineis, txt):
    t = await tela(pg)
    check(t["titulo"] == titulo and t["volta"] and not t["menu"] and t["abas"] == (k == "config") and t["paineis"] == paineis
          and t["linha"] and t["pe"] and t["hist"] == k and t["tela"] == k and t["telas"] == ["v-mais"] and t["fora"] == 0,
          f"{txt}: a tela {titulo}, com o ‹ Mais no alto e só {paineis} ({t})")
    return t


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados"], "lista": [{"produto": "Leite integral"}]}
    with App(cfg, buscar=False) as app:
        async with async_playwright() as p:
            for escuro, w in ((True, 390), (False, 320), (True, 1280)):
                pc = w >= 1000
                b, pg = await pagina(p, largura=w, altura=900 if pc else 844, escuro=escuro, toque=not pc)
                tag = f"{'escuro' if escuro else 'claro'} {w}px"
                await pg.goto(app.url)
                await pg.wait_for_timeout(1200)
                aba_mais = '#lado [data-lado="mais"]' if pc else '.tabbar [data-view="mais"]'
                await pg.click(aba_mais)
                await no_menu(pg, f"{tag}: Mais abre")
                if not escuro:
                    await abre(pg, "config")
                    await pg.click("#aba-aparencia")
                    await pg.click('#tema [data-v="claro"]')
                    check(await pg.get_attribute("html", "data-theme") == "light", f"{tag}: tema claro")
                    await pg.click("#aba-integracoes")
                    await pg.click("#maisVolta")
                    await no_menu(pg, f"{tag}: depois do tema")
                check(await pg.get_attribute(aba_mais, "aria-current") == "page", f"{tag}: Mais marcado embaixo (ou na barra lateral)")
                # ----- o menu: uma linha por função, Configurações e Sobre por último -----
                linhas = await pg.evaluate(LINHAS_JS)
                check([(x["k"], x["t"], x["s"]) for x in linhas] == LINHAS, f"{tag}: Casa, Lojas, Configurações e Sobre, cada uma com a sua linha ({linhas})")
                check(all(x["ic"] and x["chev"] for x in linhas), f"{tag}: cada linha com o ícone no quadradinho e a seta")
                check(all(abs(x["x"]) <= 1 and abs(x["w"]) <= 1 and x["h"] >= 60 for x in linhas), f"{tag}: as linhas na largura do menu, todas alinhadas")
                check(all(a["fim"] <= c["y"] + 1 for a, c in zip(linhas, linhas[1:])), f"{tag}: uma embaixo da outra, sem encostar")
                check(not any(x["cortado"] for x in linhas), f"{tag}: nenhum texto cortado")
                cores = await pg.evaluate("[getComputedStyle(document.querySelector('#maisMenu .h-ic')).color, getComputedStyle(document.querySelector('#hello .brand > span')).color]")
                check(cores[0] == cores[1], f"{tag}: o ícone na cor do app ({cores})")
                check(" ".join((await pg.locator("#maisPe").inner_text()).split()) == f"EconomIA v{VERSAO}", f"{tag}: o rodapé com a versão")
                await pg.screenshot(path=f"{SHOTS}/ecmais-menu-{'escuro' if escuro else 'claro'}-{w}.png")
                # ----- cada tela e um jeito de voltar -----
                await abre(pg, "casa")
                await na_tela(pg, "casa", "Casa", ["mp-casa"], f"{tag}: Casa")
                check(await pg.evaluate("window.scrollY") == 0, f"{tag}: Casa abre no alto")
                if pc:
                    cab = await pg.evaluate("""() => ['maisVolta', 'screenTitle'].map((id) => document.getElementById(id).getBoundingClientRect())
                        .concat([document.querySelector('.cab .sync').getBoundingClientRect(), document.querySelector('.top-acts').getBoundingClientRect()])
                        .map((r) => ({x: r.left, y: r.top, fim: r.bottom, dir: r.right}))""")
                    volta, h1, sync, acts = cab
                    check(volta["fim"] <= h1["y"] + 1 and h1["fim"] <= sync["y"] + 1 and h1["dir"] <= acts["x"], f"{tag}: ‹ Mais, o título e a linha da busca um embaixo do outro, sem bater nas ações ({cab})")
                await pg.screenshot(path=f"{SHOTS}/ecmais-casa-{'escuro' if escuro else 'claro'}-{w}.png")
                await pg.click("#maisVolta")
                await no_menu(pg, f"{tag}: ‹ Mais em Casa")
                await abre(pg, "lojas")
                await na_tela(pg, "lojas", "Lojas", ["mp-lojas"], f"{tag}: Lojas")
                await pg.screenshot(path=f"{SHOTS}/ecmais-lojas-{'escuro' if escuro else 'claro'}-{w}.png")
                await pg.go_back()
                await no_menu(pg, f"{tag}: o Voltar em Lojas")
                # ----- Configurações: as abas -----
                await abre(pg, "config")
                await na_tela(pg, "config", "Configurações", ["mp-integracoes"], f"{tag}: Configurações abre em Integrações")
                nomes = [x.strip() for x in await pg.locator("#maisAbas [role=tab]").all_inner_texts()]
                check(nomes == [n for _, n in ABAS], f"{tag}: as abas Integrações, Dados, Aparência e Opções ({nomes})")
                cabe = await pg.evaluate("(s => [s.scrollWidth, s.clientWidth])(document.getElementById('maisAbas'))")
                check(cabe[0] <= cabe[1] + 1, f"{tag}: as quatro abas cabem, sem rolar para o lado ({cabe})")
                for k, n in ABAS:
                    await pg.click("#aba-" + k)
                    t = await tela(pg)
                    sel = await pg.evaluate("[...document.querySelectorAll('#maisAbas [role=tab]')].filter((b) => b.getAttribute('aria-selected') === 'true').map((b) => b.dataset.aba)")
                    dentro = await pg.evaluate(f"""(() => {{ const s = document.getElementById('maisAbas').getBoundingClientRect(), b = document.getElementById('aba-{k}').getBoundingClientRect();
                        return b.left >= s.left - 1 && b.right <= s.right + 1; }})()""")
                    check(t["paineis"] == ["mp-" + k] and sel == [k] and t["aba"] == k and t["titulo"] == "Configurações" and dentro and t["fora"] == 0,
                          f"{tag}: a aba {n} mostra só o painel dela, marcada e à vista ({t['paineis']}, {sel}, {dentro})")
                await pg.click("#aba-dados")
                await pg.keyboard.press("ArrowRight")
                check(await pg.get_attribute("#aba-aparencia", "aria-selected") == "true" and await pg.evaluate("document.activeElement.id") == "aba-aparencia",
                      f"{tag}: a seta para a direita vai para a próxima aba")
                await pg.screenshot(path=f"{SHOTS}/ecmais-config-{'escuro' if escuro else 'claro'}-{w}.png")
                if pc:
                    await pg.click(aba_mais)
                    await no_menu(pg, f"{tag}: o Mais da barra lateral em Configurações")
                else:
                    await pg.evaluate(ARRASTA, -120)
                    await pg.wait_for_timeout(300)
                    check((await tela(pg))["titulo"] == "Configurações", f"{tag}: arrastar para a esquerda fica em Configurações")
                    await pg.evaluate(ARRASTA, 120)
                    await no_menu(pg, f"{tag}: arrastar para a direita em Configurações")
                await abre(pg, "config")
                await na_tela(pg, "config", "Configurações", ["mp-aparencia"], f"{tag}: Configurações volta na aba de antes")
                # recarregar (ou abrir o app de novo) volta na mesma tela e aba, e o Voltar ainda leva ao menu
                await pg.reload()
                await espera(pg, "() => document.getElementById('screenTitle').textContent === 'Configurações' && history.state && history.state.tela === 'config'")
                await na_tela(pg, "config", "Configurações", ["mp-aparencia"], f"{tag}: recarregado")
                await pg.go_back()
                await no_menu(pg, f"{tag}: recarregado, o Voltar")
                # saindo por outra aba de baixo, a entrada da tela é desfeita e Mais volta no menu
                await abre(pg, "lojas")
                await pg.click('#lado [data-lado="ofertas"]' if pc else '.tabbar [data-view="ofertas"]')
                await espera(pg, "() => !(history.state && history.state.tela) && !document.getElementById('v-ofertas').hidden")
                check(await pg.locator("#maisVolta").is_hidden() and (await tela(pg))["titulo"] == "Ofertas", f"{tag}: Ofertas, sem o ‹ Mais")
                await pg.click(aba_mais)
                await no_menu(pg, f"{tag}: Mais de novo, depois de Ofertas")
                check(not pg.erros, f"{tag}: sem erros na página {pg.erros}")
                await b.close()

            # ----- quem vinha das abas da 1.2 volta no mesmo lugar, já no caminho novo -----
            b, pg = await pagina(p, largura=390, altura=844)
            await pg.goto(app.url)
            await pg.wait_for_timeout(800)
            for ui, titulo, paineis, txt in (({"view": "mais", "maisTela": "", "maisAba": "lojas"}, "Lojas", ["mp-lojas"], "estava em Mais › Lojas"),
                                             ({"view": "mais", "maisTela": "", "maisAba": "dados"}, "Configurações", ["mp-dados"], "estava em Mais › Dados"),
                                             ({"view": "mais", "maisTela": "sobre", "maisAba": "casa"}, "Sobre", ["mp-sobre"], "estava em Mais › Sobre"),
                                             ({"view": "lista", "maisAba": "casa"}, "Minha lista", [], "estava na Minha lista")):
                await pg.evaluate("(u) => localStorage.setItem('ofertas-bairro:ui', JSON.stringify(u))", ui)
                await pg.reload()
                await espera(pg, f"() => document.getElementById('screenTitle').textContent === {json.dumps(titulo)}")
                t = await tela(pg)
                guardado = await pg.evaluate("JSON.parse(localStorage.getItem('ofertas-bairro:ui'))")
                check(t["paineis"] == paineis and guardado.get("menuMais") == 1 and guardado.get("maisAba") == ("dados" if ui["maisAba"] == "dados" else "integracoes"),
                      f"1.2 → 1.3, {txt}: abre em {titulo} ({t['paineis']}, {guardado})")
                if paineis:
                    check(t["volta"] and t["hist"] == t["tela"], f"1.2 → 1.3, {txt}: com o ‹ Mais e a entrada no histórico")
                    await pg.go_back()
                    await no_menu(pg, f"1.2 → 1.3, {txt}: o Voltar")
                else:
                    await pg.click('.tabbar [data-view="mais"]')
                    await no_menu(pg, f"1.2 → 1.3, {txt}: Mais abre no menu")
                    await abre(pg, "config")
                    check((await tela(pg))["paineis"] == ["mp-integracoes"], f"1.2 → 1.3, {txt}: Configurações em Integrações")
                    await pg.go_back()
                    await no_menu(pg, f"1.2 → 1.3, {txt}: o Voltar em Configurações")
            # já no caminho novo, nada muda: em Mais, abre no menu
            await pg.evaluate("localStorage.setItem('ofertas-bairro:ui', JSON.stringify({view: 'mais', maisTela: '', maisAba: 'dados', menuMais: 1}))")
            await pg.reload()
            await pg.wait_for_timeout(1000)
            await no_menu(pg, "1.3: em Mais, o menu")
            # o endereço antigo #lojas abre Mais › Lojas
            await pg.goto(app.url + "#lojas")
            await pg.reload()
            await espera(pg, "() => document.getElementById('screenTitle').textContent === 'Lojas'")
            check((await tela(pg))["paineis"] == ["mp-lojas"], "o endereço antigo #lojas abre Mais › Lojas")
            check(not pg.erros, f"1.2 → 1.3: sem erros na página {pg.erros}")
            await b.close()

    # ----- um atalho de fora: Preencher o perfil abre Casa; o Voltar volta para a Minha lista, o ‹ Mais vai ao menu -----
    with App({"cep": CEP, "raio_km": 5, "categorias": ["mercados"], "lista": []}, buscar=False) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p, largura=390, altura=844)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.click('#comecar [data-ir="mais"]')
            await espera(pg, "() => history.state && history.state.tela === 'casa'")
            await na_tela(pg, "casa", "Casa", ["mp-casa"], "Preencher o perfil")
            await pg.go_back()
            await espera(pg, "() => !(history.state && history.state.tela) && !document.getElementById('v-lista').hidden")
            t = await tela(pg)
            check(t["titulo"] == "Minha lista" and t["telas"] == ["v-lista"] and not t["volta"], f"Preencher o perfil, o Voltar: volta para a Minha lista ({t})")
            await pg.click('#comecar [data-ir="mais"]')
            await espera(pg, "() => history.state && history.state.tela === 'casa'")
            await pg.click("#maisVolta")
            await no_menu(pg, "Preencher o perfil, o ‹ Mais")
            check(not pg.erros, f"atalho: sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
