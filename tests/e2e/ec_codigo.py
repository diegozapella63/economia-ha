# EconomIA 0.19.0: Minha lista › código de barras: foto (leitor próprio, sem o do navegador) ou números,
# o produto pela loja ou pelo Open Food Facts, código de balança, número errado e o item na lista com o código.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, App, check, ean13, pagina, png_codigo, prod, resumo, shot

EAN_COXINHA = ean13("789000000001")
EAN_OFF = "7896004000855"


def prepara(lojas):
    lojas.catalogo["giassi"] = [prod("Coxinha da Asa de Frango Resfriada Kg", 21.90, "Açougue/Aves", "kg", 1, EAN_COXINHA)]
    lojas.off[EAN_OFF] = {"product_name_pt": "Biscoito Recheado Chocolate", "brands": "Bauducco", "quantity": "140 g"}


FOTOS = [  # (nome, png, código esperado)
    ("limpa", lambda: png_codigo(EAN_COXINHA), EAN_COXINHA),
    ("de-pe", lambda: png_codigo(EAN_COXINHA, girar=90, fundo=(640, 900)), EAN_COXINHA),
    ("de-ponta-cabeca", lambda: png_codigo(EAN_COXINHA, girar=180), EAN_COXINHA),
    ("borrada", lambda: png_codigo(EAN_COXINHA, borrar=2), EAN_COXINHA),
    ("com-ruido", lambda: png_codigo(EAN_COXINHA, ruido=0.02, semente=7), EAN_COXINHA),
    ("pequena", lambda: png_codigo(EAN_COXINHA, modulo=2, altura=80, fundo=(1600, 900)), EAN_COXINHA),
    ("ean8", lambda: png_codigo("78912342"), "78912342"),
    ("upc-a", lambda: png_codigo("0036000291452", borrar=1), "0036000291452"),
]


async def main():
    cfg = {"cep": CEP, "categorias": ["mercados"], "lista": [{"produto": "Leite integral", "compras": []}]}
    with App(cfg, buscar=False, preparar=prepara) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(300)
            check(await pg.locator("#codBox").is_hidden(), "painel do código fechado no começo")
            await pg.click("#codBtn")
            check(await pg.locator("#codBox").is_visible() and await pg.get_attribute("#codBtn", "aria-expanded") == "true", "botão abre o painel")
            # o histórico e o código não ficam abertos juntos
            await pg.click("#histBtn")
            check(await pg.locator("#codBox").is_hidden(), "abrir o histórico fecha o código")
            await pg.click("#codBtn")
            check(await pg.locator("#histBox").is_hidden(), "abrir o código fecha o histórico")
            await shot(pg, "ecc-aberto")
            # leitor próprio (o Chromium de teste não tem o BarcodeDetector)
            check(not await pg.evaluate("'BarcodeDetector' in window"), "sem BarcodeDetector: testa o leitor próprio")
            for nome, gera, esperado in FOTOS:
                await pg.fill("#codNum", "")
                await pg.set_input_files("#codArq", files=[{"name": nome + ".png", "mimeType": "image/png", "buffer": gera()}])
                await pg.wait_for_function("() => /Achei|Não achei|Não consegui|balança|já está|Procurando/.test(document.getElementById('codMsg').textContent) && !/Lendo/.test(document.getElementById('codMsg').textContent)", timeout=15000)
                lido = await pg.input_value("#codNum")
                check(lido == esperado, f"foto {nome}: leu {lido or 'nada'}")
            # foto sem código
            await pg.fill("#codNum", "")
            await pg.set_input_files("#codArq", files=[{"name": "nada.png", "mimeType": "image/png", "buffer": png_codigo(EAN_COXINHA, altura=0)}])
            await pg.wait_for_function("() => /Não consegui|Achei|Não achei/.test(document.getElementById('codMsg').textContent)", timeout=15000)
            check("Não consegui ler" in await pg.text_content("#codMsg") and await pg.input_value("#codNum") == "", "foto sem código: avisa e não inventa número")
            # produto na loja
            await pg.fill("#codNum", EAN_COXINHA)
            await pg.click("#codProcura")
            await pg.wait_for_selector("#codRes:not([hidden])")
            msg = (await pg.text_content("#codMsg")).replace("\xa0", " ")
            check("Achei no Giassi, por R$ 21,90" in msg, f"achou na loja com o preço ({msg})")
            check(await pg.input_value("#codNome") == "Coxinha da Asa de Frango Resfriada Kg", "nome do produto preenchido")
            await shot(pg, "ecc-achou-loja")
            # Open Food Facts
            await pg.fill("#codNum", EAN_OFF)
            await pg.press("#codNum", "Enter")
            await pg.wait_for_function("() => /Open Food Facts/.test(document.getElementById('codMsg').textContent)")
            check(await pg.input_value("#codNome") == "Biscoito Recheado Chocolate Bauducco 140 g", "nome pelo Open Food Facts, com marca e tamanho")
            # código de balança e número errado
            await pg.fill("#codNum", ean13("200012300001"))
            await pg.click("#codProcura")
            await pg.wait_for_function("() => /balança/.test(document.getElementById('codMsg').textContent)")
            check(True, "código de balança: avisa que só vale na loja")
            await pg.fill("#codNum", "7891000100104")
            await pg.click("#codProcura")
            await pg.wait_for_timeout(300)
            check("não é um código de barras válido" in await pg.text_content("#codMsg") and await pg.locator("#codRes").is_hidden(), "dígito verificador errado")
            # não achado: escreve o nome e o código fica no item
            await pg.fill("#codNum", "7891000100103")
            await pg.click("#codProcura")
            await pg.wait_for_selector("#codRes:not([hidden])")
            check("Não achei" in await pg.text_content("#codMsg"), "código válido não achado: pede o nome")
            await pg.click("#codPor")
            check("Escreva o nome" in await pg.text_content("#codMsg"), "sem nome não põe na lista")
            await pg.fill("#codNome", "Leite em pó Ninho 380 g")
            await pg.click("#codPor")
            await pg.wait_for_timeout(1500)
            check("entrou na lista com o código de barras" in await pg.text_content("#addMsg"), "item entrou com o código")
            check(await pg.locator("#codBox").is_hidden(), "o painel fecha")
            lista = app.config_salva().get("lista") or []
            novo = next((i for i in lista if i.get("produto") == "Leite em pó Ninho 380 g"), {})
            check(novo.get("ean") == "7891000100103", f"código gravado na config ({novo})")
            # o mesmo código de novo: já está na lista
            await pg.click("#codBtn")
            await pg.fill("#codNum", "7891000100103")
            await pg.click("#codProcura")
            await pg.wait_for_timeout(300)
            check('Já está na lista: "Leite em pó Ninho 380 g"' in await pg.text_content("#codMsg"), "código repetido: aponta o item")
            # código para um item que já existe pelo nome: guarda no item
            await pg.fill("#codNum", EAN_COXINHA)
            await pg.click("#codProcura")
            await pg.wait_for_selector("#codRes:not([hidden])")
            await pg.fill("#codNome", "Leite integral")
            await pg.click("#codPor")
            await pg.wait_for_timeout(1200)
            leite = next((i for i in app.config_salva().get("lista") or [] if i.get("produto") == "Leite integral"), {})
            check(leite.get("ean") == EAN_COXINHA and "ficou guardado" in await pg.text_content("#addMsg"), "nome repetido: o código vai para o item que existe")
            await shot(pg, "ecc-na-lista")
            # o código vai junto para o histórico e volta
            await pg.locator("#wish li.item", has_text="Leite em pó Ninho").locator("button.rm").click()
            await pg.wait_for_timeout(1200)
            cfg2 = app.config_salva()
            h = next((x for x in cfg2.get("historico") or [] if x.get("produto") == "Leite em pó Ninho 380 g"), {})
            check(h.get("ean") == "7891000100103", "removido: o código fica no histórico")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
