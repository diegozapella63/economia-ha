# EconomIA 1.11.0: Minha lista › código de barras › Tirar foto abre a câmera do próprio app, em tela cheia (o seletor de
# arquivo do celular, no app do Home Assistant, abria a galeria): o leitor do navegador lê o código sozinho quando ele
# entra no quadro; o botão do meio tira a foto e lê pelo leitor próprio; o X, o Voltar do celular e o Esc fecham; sem a
# câmera (http), explica e abre a escolha da foto. A câmera de teste do Chromium (sem código nela).
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, App, check, ean13, espera, pagina, prod, resumo, shot

EAN = ean13("789000000001")
CAMERA = ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"]
# o leitor do navegador, de mentira: acha o código quando a página pede (window.__acha)
DETECTOR = """window.__acha = null; window.BarcodeDetector = class { constructor(o) { this.o = o; }
  detect() { return Promise.resolve(window.__acha ? [{ rawValue: window.__acha }] : []); } };"""
SEM_CAMERA = "Object.defineProperty(navigator, 'mediaDevices', { value: undefined });"


def prepara(lojas):
    lojas.catalogo["giassi"] = [prod("Coxinha da Asa de Frango Resfriada Kg", 21.90, "Açougue/Aves", "kg", 1, EAN)]


async def abre_codigo(pg, app):
    await pg.goto(app.url)
    await pg.wait_for_timeout(1200)
    await pg.click('.tabbar [data-view="lista"]')
    await pg.wait_for_timeout(300)
    await pg.click("#codBtn")
    await pg.wait_for_timeout(200)


async def main():
    cfg = {"cep": CEP, "categorias": ["mercados"], "lista": [{"produto": "Leite integral", "compras": []}]}
    with App(cfg, buscar=False, preparar=prepara) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p, args=CAMERA, permissoes=["camera"])
            await pg.add_init_script(DETECTOR)
            await abre_codigo(pg, app)
            check(await pg.locator("#codFoto").inner_text() == "Tirar foto" and await pg.locator('#codArq[capture]').count() == 0,
                  "Tirar foto é um botão (nada de seletor de arquivo com capture, que abre a galeria)")
            await pg.click("#codFoto")
            await espera(pg, "() => !document.getElementById('codCamUI').hidden && document.getElementById('codVideo').readyState >= 2")
            ui = await pg.locator("#codCamUI").bounding_box()
            check(ui["width"] == 390 and ui["height"] == 844, f"a câmera em tela cheia ({ui})")
            check(await pg.evaluate("history.state && history.state.cam") is True, "uma entrada no histórico, para o Voltar")
            await shot(pg, "camera-codigo")
            # o Voltar do celular fecha só a câmera
            await pg.go_back()
            await pg.wait_for_timeout(400)
            check(await pg.locator("#codCamUI").is_hidden() and await pg.evaluate("document.getElementById('codVideo').srcObject") is None,
                  "o Voltar fecha a câmera e desliga")
            check(await pg.locator("#codBox").is_visible(), "o painel do código continua aberto")
            # o X fecha
            await pg.click("#codFoto")
            await espera(pg, "() => !document.getElementById('codCamUI').hidden")
            await pg.click("#codCamX")
            await pg.wait_for_timeout(300)
            check(await pg.locator("#codCamUI").is_hidden() and not await pg.evaluate("history.state && history.state.cam"), "o X fecha e tira a entrada do histórico")
            # o botão do meio: a foto vai para o leitor próprio (a câmera de teste não tem código)
            await pg.click("#codFoto")
            await espera(pg, "() => !document.getElementById('codCamUI').hidden && document.getElementById('codVideo').readyState >= 2")
            await pg.click("#codCamFoto")
            await espera(pg, "() => /Não consegui ler o código/.test(document.getElementById('codMsg').textContent)")
            check(await pg.locator("#codCamUI").is_hidden(), "tirar a foto fecha a câmera e lê a foto")
            # o leitor do navegador acha o código sozinho, com a câmera aberta
            await pg.click("#codFoto")
            await espera(pg, "() => !document.getElementById('codCamUI').hidden")
            await pg.evaluate(f"window.__acha = '{EAN}'")
            await espera(pg, "() => document.getElementById('codCamUI').hidden")
            check(await pg.input_value("#codNum") == EAN, "achou o código: fecha e põe os números")
            await espera(pg, "() => !document.getElementById('codRes').hidden || /Procurando|Coxinha/.test(document.getElementById('codMsg').textContent)")
            check(True, "e procura o produto")
            await b.close()
            # sem câmera (http): explica e abre a escolha da foto
            b, pg = await pagina(p)
            await pg.add_init_script(SEM_CAMERA)
            await abre_codigo(pg, app)
            async with pg.expect_file_chooser() as fc:
                await pg.click("#codFoto")
            await (await fc.value).set_files([])
            msg = await pg.locator("#codMsg").inner_text()
            check("https" in msg and await pg.locator("#codGal").is_visible() and await pg.locator("#codCamUI").is_hidden(),
                  f"sem câmera: explica, oferece escolher a foto ({msg})")
            await b.close()
    resumo()


asyncio.run(main())
