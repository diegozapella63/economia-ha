# EconomIA 0.18.0: Mais › Integrações › Mercado Livre (categorias): salvar com URL errada, salvar, Autorizar (link com o
# App ID), colar o endereço errado e o certo, Conectado com o teste, Testar, Apagar; chave guardada aparece só como ••••.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, abrir_mais, check, pagina, resumo


async def abre_integracoes(pg):
    await abrir_mais(pg, "integracoes")
    await pg.wait_for_timeout(500)


async def main():
    def prepara(lojas):
        lojas.categorias_ml_padrao()
    with App({"cep": CEP, "categorias": ["mercados"], "lista": []}, buscar=False, preparar=prepara) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await abre_integracoes(pg)
            card = pg.locator('section[aria-labelledby="h-ml"]')
            check(await card.is_visible(), "card do Mercado Livre em Integrações")
            check("Desligado" in await pg.text_content("#mlSt"), "começa desligado")
            check(await pg.locator("#mlAutorizar").is_hidden() and await pg.locator("#mlPasso2").is_hidden(), "sem App ID: sem Autorizar")
            await card.locator("details.ml-como summary").click()
            check("developers.mercadolivre.com.br" in await card.locator("details.ml-como").inner_text(), "Como configurar: os passos")
            # URL de retorno sem https
            await pg.fill("#mlApp", "123456")
            await pg.fill("#mlSenha", "segredo-ml")
            await pg.fill("#mlUrl", "http://www.google.com")
            await pg.click("#mlSalvar")
            await pg.wait_for_timeout(300)
            check("começa com https://" in await pg.text_content("#mlSt"), "URL sem https: avisa")
            # salvar certo
            await pg.fill("#mlUrl", "https://www.google.com")
            await pg.fill("#mlSenha", "segredo-ml")
            await pg.click("#mlSalvar")
            await pg.wait_for_function("() => /Autorizar no Mercado Livre/.test(document.getElementById('mlSt').textContent)")
            href = await pg.get_attribute("#mlAutorizar", "href")
            check(await pg.locator("#mlAutorizar").is_visible() and "client_id=123456" in href and "redirect_uri=https%3A%2F%2Fwww.google.com" in href,
                  "Autorizar aponta para o app certo")
            check(await pg.locator("#mlSenhaOk").is_visible() and await pg.input_value("#mlSenha") == "••••••••••••••••", "a chave aparece só como ••••")
            seg = app.S.ler_json(app.pasta + "/segredos.json", {})
            check(seg.get("ml", {}).get("secret") == "segredo-ml", "a chave ficou no Home Assistant")
            # tocar em Autorizar mostra o passo 2 (o link abre outra aba; aqui só conferimos o passo)
            await pg.evaluate("document.getElementById('mlAutorizar').addEventListener('click', e => e.preventDefault(), {once: true})")
            await pg.click("#mlAutorizar")
            check(await pg.locator("#mlPasso2").is_visible(), "Autorizar mostra onde colar o endereço")
            await card.screenshot(path=SHOTS + "/eci-ml-autorizar.png")
            await pg.click("#mlConectar")
            check("Cole o endereço" in await pg.text_content("#mlSt"), "Conectar sem endereço: avisa")
            await pg.fill("#mlCodigo", "https://www.google.com/?code=TG-errado")
            await pg.click("#mlConectar")
            await pg.wait_for_function("() => /não aceitou/.test(document.getElementById('mlSt').textContent)")
            check(await pg.input_value("#mlCodigo") == "", "o campo do código é limpo depois de usar")
            await pg.fill("#mlCodigo", "https://www.google.com/?code=TG-abc123&state=x")
            await pg.click("#mlConectar")
            await pg.wait_for_function("() => /Conectado/.test(document.getElementById('mlSt').textContent)")
            st = await pg.text_content("#mlSt")
            check("carne moída → Carnes Bovinas; hambúrguer → Hambúrgueres" in st, f"conectado, com o teste ({st})")
            check(await pg.locator("#mlPasso2").is_hidden() and await pg.text_content("#mlAutorizar") == "Autorizar de novo", "passo 2 some; Autorizar de novo")
            await card.screenshot(path=SHOTS + "/eci-ml-conectado.png")
            # recarregar: continua conectado
            await pg.reload()
            await pg.wait_for_timeout(1200)
            await abre_integracoes(pg)
            check("Conectado: a categoria confere" in await pg.text_content("#mlSt"), "depois de recarregar: conectado")
            await pg.click("#mlTestar")
            await pg.wait_for_function("() => /Conectado. Teste/.test(document.getElementById('mlSt').textContent)")
            check(True, "Testar de novo")
            await pg.click("#mlApagar")
            await pg.wait_for_timeout(800)
            check("Desligado" in await pg.text_content("#mlSt") and await pg.input_value("#mlApp") == "", "Apagar desliga e limpa")
            check("ml" not in app.S.ler_json(app.pasta + "/segredos.json", {}), "e tira a chave do Home Assistant")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
