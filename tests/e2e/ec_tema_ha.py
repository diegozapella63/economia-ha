# EconomIA 1.42.0: o fundo e os cartões são os do tema do Home Assistant (hatema.js, o mesmo arquivo em todos os apps da
# família), para todos os apps terem o mesmo fundo. Dentro de um Home Assistant de mentira, com um tema dele (claro e
# depois escuro, trocado com o app aberto), o app pinta aquele fundo e aqueles cartões; aberto sozinho, as cores do tema
# padrão do Home Assistant (#fafafa e #111111). O Home Assistant e o app ficam na mesma origem, como no Ingress.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, check, pagina, resumo

# o Home Assistant em volta do app: o tema no <html>, como ele pinta, e o <home-assistant> com o hass.themes
HA = """<!doctype html><html style="--primary-background-color:#eef3fb;--card-background-color:#fcfdff"><body style="margin:0">
<home-assistant></home-assistant><iframe id="app" src="/app/" style="position:fixed;inset:0;width:100%;height:100%;border:0"></iframe>
<script>document.querySelector("home-assistant").hass = { themes: { darkMode: false } };
window.modo = (dark, bg, card) => { document.querySelector("home-assistant").hass = { themes: { darkMode: dark } };
  document.documentElement.style.setProperty("--primary-background-color", bg); document.documentElement.style.setProperty("--card-background-color", card); };</script></body></html>"""

FUNDO = "() => getComputedStyle(document.body).backgroundColor"
CORES = "() => ['--ha-bg-light', '--ha-card-light', '--ha-bg-dark', '--ha-card-dark'].map((v) => document.documentElement.style.getPropertyValue(v))"
# um cartão: o que usa o --surface (o valor que ele tem agora, já com o tema)
CARTAO = """() => { const d = document.createElement('div'); d.style.background = 'var(--surface)'; document.body.append(d);
  const c = getComputedStyle(d).backgroundColor; d.remove(); return c; }"""


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados"], "lista": [{"produto": "Leite integral"}]}
    with App(cfg, buscar=False) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p, escuro=False)
            base = app.url.split("?")[0].rstrip("/")

            async def servir(route):
                url = route.request.url
                if url.rstrip("/") == "http://ha.test":
                    await route.fulfill(body=HA, content_type="text/html")
                elif url.startswith("http://ha.test/app/"):
                    # pelo servidor do app, como o Ingress faz
                    r = await route.fetch(url=base + "/" + url[len("http://ha.test/app/"):])
                    await route.fulfill(response=r)
                else:
                    await route.fulfill(status=404, body="")

            await pg.context.route("http://ha.test/**", servir)
            await pg.goto("http://ha.test/")
            await pg.wait_for_timeout(1800)
            fr = pg.frames[1]
            check(await fr.evaluate("() => window.__haTema && window.__haTema.doHA") == "light", "dentro do Home Assistant: lê o tema dele (claro)")
            check(await fr.evaluate(CORES) == ["#eef3fb", "#fcfdff", "#111111", "#1c1c1c"], f"as cores claras do tema, as escuras do padrão ({await fr.evaluate(CORES)})")
            check(await fr.evaluate(FUNDO) == "rgb(238, 243, 251)", f"claro: o fundo do tema ({await fr.evaluate(FUNDO)})")
            check(await fr.evaluate(CARTAO) == "rgb(252, 253, 255)", f"claro: o cartão do tema ({await fr.evaluate(CARTAO)})")
            await pg.screenshot(path=SHOTS + "/ec-tema-ha-claro.png")
            # a pessoa deixa o Home Assistant escuro (um tema com o escuro dele): o app vai junto, sem abrir de novo
            await pg.emulate_media(color_scheme="dark")
            await pg.evaluate("() => window.modo(true, '#0d1a26', '#172636')")
            await pg.wait_for_timeout(900)
            check(await fr.evaluate("() => window.__haTema.doHA") == "dark", "Home Assistant escuro: lê de novo")
            check(await fr.evaluate(CORES) == ["#fafafa", "#ffffff", "#0d1a26", "#172636"], f"agora as cores escuras do tema ({await fr.evaluate(CORES)})")
            check(await fr.evaluate(FUNDO) == "rgb(13, 26, 38)", f"escuro: o fundo do tema ({await fr.evaluate(FUNDO)})")
            check(await fr.evaluate(CARTAO) == "rgb(23, 38, 54)", f"escuro: o cartão do tema ({await fr.evaluate(CARTAO)})")
            await pg.screenshot(path=SHOTS + "/ec-tema-ha-escuro.png")
            check(not pg.erros, f"sem erros {pg.erros}")
            await b.close()
            # sozinho (fora do Home Assistant): as cores do tema padrão do Home Assistant
            for escuro, fundo, cartao in ((False, "rgb(250, 250, 250)", "rgb(255, 255, 255)"), (True, "rgb(17, 17, 17)", "rgb(28, 28, 28)")):
                b, pg = await pagina(p, escuro=escuro)
                await pg.goto(app.url)
                await pg.wait_for_timeout(1200)
                nome = "escuro" if escuro else "claro"
                check(await pg.evaluate("() => window.__haTema.doHA") is None, f"{nome}, sozinho: sem o Home Assistant")
                check(await pg.evaluate(FUNDO) == fundo, f"{nome}, sozinho: o fundo do tema padrão ({await pg.evaluate(FUNDO)})")
                check(await pg.evaluate(CARTAO) == cartao, f"{nome}, sozinho: o cartão do tema padrão ({await pg.evaluate(CARTAO)})")
                await b.close()


asyncio.run(main())
resumo()
