# EconomIA 1.1.0 (1.3.0: Mais é um menu): Mais › Sobre, a última linha do menu de Mais. CorrerIA Code (desenvolvimento
# de softwares) e por que o nome, os sete apps da família, cada um com a sua linha e o GitHub (este marcado com a versão),
# e Meu GitHub. A mesma página do CronologIA, nas cores e fontes daqui. O Voltar do celular, o ‹ Mais e arrastar para a
# direita voltam para o menu; de 320 px ao computador, claro e escuro, nada passando da borda.
import asyncio
import os
import re

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, check, espera, pagina, resumo

GH = "https://github.com/diegozapella63"
APPS = [("CronologIA", "cronologia-ha", "Agenda da família, remédios, rotinas e placar."),
        ("ResolvIA", "resolvia-ha", "Listas de tarefas com prazos, pontos e repetição."),
        ("GerencIA", "gerencia-ha", "Finanças da casa: caixa, cartões e investimentos."),
        ("InventarIA", "inventario-ha", "Inventário da casa: cômodos, itens e valores."),
        ("EconomIA", "economia-ha", "Lista de compras com o melhor preço perto de casa."),
        ("MemorIA", "memoria-ha", "Cadernos de anotação que abrem na hora certa."),
        ("CorrerIA", "correria-ha", "Pergunte e peça a qualquer app, no chat ou no WhatsApp.")]
POR_QUE = ("Porque eu sou um programador sem tempo: vivo na correria. Então eu uso a IA para rodar tudo isso aqui. "
           "Ela escreve, testa e publica; eu dou as ideias e reclamo dos botões tortos.")
INFO = '<circle cx="12" cy="12" r="10"></circle><path d="M12 16v-4"></path><path d="M12 8h.01"></path>'  # o ícone de informação (Lucide)
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ler = lambda *c: open(os.path.join(RAIZ, *c), encoding="utf-8").read()  # noqa: E731
VERSAO = re.search(r'^version:\s*"?([\d.]+)', ler("economia", "config.yaml"), re.M).group(1)

# o que está à vista: título, ‹ Mais, abas, painéis, linha do alto, aviso de exemplo, rodapé, Sobre e o menu de Mais
TELA = """() => { const vis = (el) => !!el && el.getClientRects().length > 0;
  return {titulo: document.getElementById('screenTitle').textContent, volta: vis(document.getElementById('maisVolta')),
    abas: vis(document.getElementById('maisAbas')), sobre: vis(document.getElementById('mp-sobre')),
    paineis: [...document.querySelectorAll('#v-mais > .mais-painel')].filter(vis).map((p) => p.id),
    linha: vis(document.querySelector('.cab .sync')), banner: vis(document.getElementById('banner')), pe: vis(document.getElementById('maisPe')),
    menu: vis(document.getElementById('maisMenu')), hist: (history.state && history.state.tela) || '',
    guardado: (JSON.parse(localStorage.getItem('ofertas-bairro:ui') || '{}').maisTela) || ''}; }"""
ARRASTA = """(dx) => { const el = document.querySelector('#por-que .sb-txt'), r = el.getBoundingClientRect();
  const x = innerWidth / 2 - dx / 2, y = r.top + r.height / 2, t0 = new Touch({identifier: 1, target: el, clientX: x, clientY: y});
  el.dispatchEvent(new TouchEvent('touchstart', {touches: [t0], changedTouches: [t0], bubbles: true}));
  const t1 = new Touch({identifier: 1, target: el, clientX: x + dx, clientY: y + 4});
  el.dispatchEvent(new TouchEvent('touchend', {touches: [], changedTouches: [t1], bubbles: true})); }"""


async def tela(pg):
    return await pg.evaluate(TELA)


async def ir_mais(pg, computador):
    await pg.click('#lado [data-lado="mais"]' if computador else '.tabbar [data-view="mais"]')
    await pg.wait_for_timeout(200)


async def abrir_sobre(pg):
    await pg.click("#sobreBtn")
    await espera(pg, "() => history.state && history.state.tela === 'sobre' && !document.getElementById('mp-sobre').hidden")


async def em_mais(pg, txt):
    """Voltou para o menu de Mais, com o rodapé; sem o ‹ Mais, as abas, os painéis e a entrada de Sobre."""
    await espera(pg, "() => !(history.state && history.state.tela) && !document.getElementById('maisMenu').hidden")
    t = await tela(pg)
    check(t["titulo"] == "Mais" and t["menu"] and not t["abas"] and not t["volta"] and not t["sobre"] and t["paineis"] == []
          and t["pe"] and not t["linha"] and t["guardado"] == "", f"{txt}: volta para o menu de Mais ({t})")


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
                await ir_mais(pg, pc)
                if not escuro:
                    await pg.click('#maisMenu [data-mais="config"]')
                    await pg.click("#aba-aparencia")
                    await pg.click('#tema [data-v="claro"]')
                    check(await pg.get_attribute("html", "data-theme") == "light", f"{tag}: tema claro")
                    await pg.click("#maisVolta")
                    await em_mais(pg, f"{tag}: depois do tema")
                # ----- Sobre, a última linha do menu de Mais -----
                ult = await pg.evaluate("""() => [...document.querySelectorAll('#v-mais > *')].filter((x) => x.getClientRects().length).map((x) => x.id)""")
                check(ult == ["maisMenu", "maisPe"], f"{tag}: em Mais, só o menu e o rodapé ({ult})")
                linhas = [" ".join(x.split()) for x in await pg.locator("#maisMenu .menu-row").all_inner_texts()]
                check(len(linhas) == 4 and linhas[-1] == "Sobre CorrerIA Code, os apps e o GitHub.", f"{tag}: Sobre, CorrerIA Code, os apps e o GitHub., a última linha ({linhas})")
                check(await pg.evaluate("document.querySelector('#maisMenu li:last-child .menu-row').id") == "sobreBtn", f"{tag}: o Sobre é a última linha")
                check(await pg.evaluate("document.querySelector('#sobreBtn .h-ic svg').innerHTML") == INFO, f"{tag}: com o ícone de informação")
                rb, lb = await pg.evaluate("""() => [document.getElementById('sobreBtn'), document.querySelector('#maisMenu .menu-list')]
                    .map((x) => { const b = x.getBoundingClientRect(); return {x: b.left, w: b.width, y: b.top, fim: b.bottom}; })""")
                check(abs(rb["w"] - lb["w"]) <= 1 and abs(rb["x"] - lb["x"]) <= 1 and abs(rb["fim"] - lb["fim"]) <= 1, f"{tag}: a linha na largura do menu, embaixo de todas ({rb}, {lb})")
                check(await pg.locator("#maisVolta").is_hidden(), f"{tag}: em Mais, sem o ‹ Mais")
                await pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await pg.screenshot(path=f"{SHOTS}/ecsobre-mais-{'escuro' if escuro else 'claro'}-{w}.png")
                # ----- Sobre -----
                await abrir_sobre(pg)
                t = await tela(pg)
                check(t["titulo"] == "Sobre" and t["volta"] and t["sobre"] and not t["abas"] and t["paineis"] == ["mp-sobre"] and not t["menu"]
                      and t["guardado"] == "sobre", f"{tag}: a tela Sobre, com o ‹ Mais no alto e sem o menu ({t})")
                check(not t["linha"] and not t["banner"] and not t["pe"], f"{tag}: sem a linha do alto, o aviso de exemplo e o rodapé (a versão está em Este app)")
                check(" ".join((await pg.locator("#maisVolta").inner_text()).split()) == "Mais", f"{tag}: ‹ Mais")
                check(await pg.evaluate("window.scrollY") == 0, f"{tag}: abre no alto")
                check(await pg.evaluate("document.querySelector('.sb-nome').innerHTML") == "Correr<span>IA</span> Code", f"{tag}: CorrerIA Code")
                cores = await pg.evaluate("[getComputedStyle(document.querySelector('.sb-nome span')).color, getComputedStyle(document.querySelector('#hello .brand > span')).color]")
                check(cores[0] == cores[1], f"{tag}: o IA na cor do IA de EconomIA no alto ({cores})")
                oque = await pg.evaluate("(x => [x.textContent, getComputedStyle(x).textTransform, x.getBoundingClientRect().height, parseFloat(getComputedStyle(x).fontSize)])(document.querySelector('.sb-oque'))")
                check(oque[:2] == ["desenvolvimento de softwares", "uppercase"], f"{tag}: desenvolvimento de softwares, em maiúsculas ({oque[:2]})")
                check(oque[2] < oque[3] * 2, f"{tag}: numa linha só ({oque[2]:.0f} px, fonte {oque[3]:.0f} px)")
                lema = await pg.evaluate("(x => [x.textContent, getComputedStyle(x).fontStyle])(document.querySelector('.sb-lema'))")
                check(lema == ["Feito na correria, rodado pela IA.", "italic"], f"{tag}: o lema em itálico ({lema})")
                check(await pg.locator(".sobre-topo .sb-raio svg").count() == 1, f"{tag}: o raio")
                check((await pg.locator("#por-que h2").inner_text()).strip() == "Por que CorrerIA?" and await pg.text_content("#por-que .sb-txt") == POR_QUE,
                      f"{tag}: Por que CorrerIA?")
                check((await pg.locator("#os-apps h2").inner_text()).strip() == "Os apps", f"{tag}: Os apps")
                linhas = await pg.evaluate("[...document.querySelectorAll('#os-apps .sb-app')].map(a => [a.querySelector('.sb-wm').textContent, a.getAttribute('href'), a.querySelector('.mb > span').textContent])")
                check([tuple(x) for x in linhas] == [(n, f"{GH}/{r}", t) for n, r, t in APPS], f"{tag}: os sete apps, na ordem, cada um com a sua linha e o GitHub ({linhas})")
                wms = await pg.evaluate("[...document.querySelectorAll('#os-apps .sb-wm')].map(w => w.innerHTML)")
                check(wms == [f"{n[:-2]}<span>IA</span>" for n, _, _ in APPS], f"{tag}: o IA de cada nome na cor de destaque, sem espaço no meio")
                check(await pg.locator("#os-apps .sb-app .h-ic svg").count() == 7, f"{tag}: cada app com o seu ícone")
                aqui = pg.locator("#os-apps .sb-app.aqui")
                check(await aqui.count() == 1 and await aqui.get_attribute("href") == f"{GH}/economia-ha"
                      and [x.strip() for x in await pg.locator("#os-apps .sb-aqui").all_inner_texts()] == [f"Este app · v{VERSAO}"],
                      f"{tag}: o EconomIA marcado, Este app · v{VERSAO}")
                links = await pg.evaluate("[...document.querySelectorAll('#mp-sobre a')].map(a => [a.getAttribute('href'), a.target, a.rel])")
                check(links == [[f"{GH}/{r}", "_blank", "noopener"] for _, r, _ in APPS] + [[GH, "_blank", "noopener"]], f"{tag}: os 8 links abrem fora ({links})")
                gh = pg.locator("#mp-sobre a.sb-github")
                check((await gh.inner_text()).strip() == "Meu GitHub" and "btn" in await gh.get_attribute("class"), f"{tag}: Meu GitHub")
                gb, pb = await gh.bounding_box(), await pg.locator("#os-apps").bounding_box()
                check(abs(gb["width"] - pb["width"]) <= 1, f"{tag}: Meu GitHub na largura dos quadros ({gb['width']:.0f} / {pb['width']:.0f})")
                fora = await pg.evaluate("""() => { const pg = document.getElementById('mp-sobre').getBoundingClientRect();
                  return [document.documentElement.scrollWidth - innerWidth, [...document.querySelectorAll('#mp-sobre *')].filter((x) => { const b = x.getBoundingClientRect();
                    return b.width && (b.left < pg.left - 1 || b.right > pg.right + 1); }).length]; }""")
                check(fora == [0, 0], f"{tag}: nada passando da borda ({fora})")
                nome = f"{SHOTS}/ecsobre-{'escuro' if escuro else 'claro'}-{w}"
                await pg.screenshot(path=nome + ".png")
                await pg.screenshot(path=nome + "-inteira.png", full_page=True)
                # ----- voltar -----
                await pg.go_back()
                await em_mais(pg, f"{tag}: o Voltar")
                await abrir_sobre(pg)
                await pg.click("#maisVolta")
                await em_mais(pg, f"{tag}: o ‹ Mais")
                if not pc:
                    await abrir_sobre(pg)
                    await pg.evaluate(ARRASTA, -120)
                    await pg.wait_for_timeout(300)
                    check((await tela(pg))["sobre"], f"{tag}: arrastar para a esquerda fica em Sobre")
                    await pg.evaluate(ARRASTA, 120)
                    await em_mais(pg, f"{tag}: arrastar para a direita")
                # saindo por outra tela, a entrada de Sobre é desfeita e Mais volta no menu
                await abrir_sobre(pg)
                await pg.click('#lado [data-lado="ofertas"]' if pc else '.tabbar [data-view="ofertas"]')
                await espera(pg, "() => !(history.state && history.state.tela) && !document.getElementById('v-ofertas').hidden")
                check(not await pg.locator(".cab .sync").is_hidden() and await pg.locator("#maisVolta").is_hidden(), f"{tag}: Ofertas, sem o ‹ Mais")
                await ir_mais(pg, pc)
                await em_mais(pg, f"{tag}: Mais de novo, depois de Ofertas")
                if w == 390:
                    # um app abre o GitHub dele em outra aba; o EconomIA fica em Sobre
                    await abrir_sobre(pg)
                    await pg.context.route("https://github.com/**", lambda r: r.fulfill(body="<title>GitHub</title>ok", content_type="text/html"))
                    async with pg.context.expect_page() as nova:
                        await pg.locator("#os-apps .sb-app").nth(1).click()
                    nova = await nova.value
                    await nova.wait_for_load_state()
                    check(nova.url == f"{GH}/resolvia-ha", f"{tag}: um toque abre o GitHub do app noutra aba ({nova.url})")
                    await nova.close()
                    check((await tela(pg))["sobre"], f"{tag}: e o app fica em Sobre")
                    # recarregar (ou abrir o app de novo) volta em Sobre, e o Voltar ainda leva para Mais
                    await pg.reload()
                    await espera(pg, "() => document.getElementById('screenTitle').textContent === 'Sobre'")
                    check((await tela(pg))["hist"] == "sobre", f"{tag}: recarregado, abre em Sobre")
                    outra = await pg.context.new_page()
                    await outra.goto(app.url)
                    await espera(outra, "() => document.getElementById('screenTitle').textContent === 'Sobre' && history.state && history.state.tela === 'sobre'")
                    await outra.go_back()
                    await em_mais(outra, f"{tag}: aberto de novo em Sobre, o Voltar")
                    await outra.close()
                if pc:
                    side = (await pg.locator("#lado .side-foot").inner_text()).strip()
                    check(side.startswith(f"EconomIA {VERSAO}"), f"{tag}: a mesma versão na barra lateral ({side})")
                check(f'server_version = "EconomIA/{VERSAO}"' in ler("economia", "app", "server.py"), f"{tag}: a mesma versão no servidor")
                check(not pg.erros, f"{tag}: sem erros na página {pg.erros}")
                await b.close()


asyncio.run(main())
resumo()
