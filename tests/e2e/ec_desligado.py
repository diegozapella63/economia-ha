# EconomIA 1.1.1: os textos só dizem o que vai acontecer. Com a opção ou a integração desligada, nada promete o que não
# acontece: Rotina de compras sem "Avisar no celular" (o aviso no celular ainda não existe), Compras online só com a aba
# Online, a ordem da busca sem as etapas desligadas em Opções, Similares e código de barras sem a busca direta, a Lista
# do Home Assistant sem sincronizar, o Instagram e a Shopee em Integrações e a loja adicionada à mão com a IA desligada.
import asyncio
import copy

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, HAFalso, check, espera, pagina, prod, resumo

BOV = "Açougue/Bovinos"
TODAS = ["Lojas perto de casa.", "Site das lojas sem site.", "Site da loja.", "Busca do site.", "Páginas de produto.",
         "Página de ofertas do site.", "Shopee.", "Folheto da semana.", "Instagram das lojas.", "Busca na web com IA.",
         "Encarte do site.", "Itens sem preço."]


def prepara(lojas):
    g = [prod("Carne Moída Bovina de Primeira Kg", 39.90, BOV, "kg", 1), prod("Acém Moído Bovino Kg", 32.90, BOV, "kg", 1)]
    lojas.catalogo["giassi"] = g
    lojas.catalogo["angeloni"] = [dict(copy.deepcopy(g[0]), categories=[], link=g[0]["link"].replace("/p", "-ang/p"))]
    lojas.catalogo["angeloni"][0]["items"][0]["sellers"][0]["commertialOffer"]["Price"] = 42.90


def antes(S):
    S.grava_segredos({"instagram": {"token": "t", "ig_id": "99", "usuario": "casa"}})


async def mais(pg, aba):
    await pg.click('.tabbar [data-view="mais"]')
    await pg.click("#aba-" + aba)
    await pg.wait_for_timeout(300)


async def etapas(pg):
    """As etapas visíveis da ordem da busca (fim de Mais › Lojas), pelo título de cada uma."""
    return [t.strip() for t in await pg.locator("#mp-lojas ol.passos li:visible b").all_inner_texts()]


async def main():
    ha = HAFalso()
    ha.lista("todo.compras", "Compras")
    # sem a aba Online (a chave "online" na config faz o app não ligar a aba sozinho)
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados"], "online": {"marketplaces": ["mercadolivre", "amazon"]},
           "lista": [{"produto": "Carne moída bovina de primeira", "compras": []}]}
    with App(cfg, preparar=prepara, antes=antes, ha=ha) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1500)
            # ----- Rotina de compras: o aviso no celular ainda não existe, então nada fala dele -----
            await mais(pg, "casa")
            rotina = pg.locator('#v-mais section[aria-labelledby="h-rotina"]')
            txt = await rotina.inner_text()
            check(await pg.locator("#avisar").count() == 0 and await pg.locator("#proxAviso").count() == 0, "sem Avisar no celular")
            check("AVIS" not in txt.upper() and "ESPAÇO PARA ESTOQUE" in txt.upper() and "DIAS DE MERCADO" in txt.upper(), f"Rotina de compras não promete aviso ({txt!r})")
            await rotina.screenshot(path=SHOTS + "/ecdl-rotina.png")
            # ----- Compras online: só com a aba Online -----
            await mais(pg, "lojas")
            check(await pg.locator("#onlineSec").is_hidden(), "sem a aba Online: Compras online some (não manda para uma aba que não existe)")
            check(await etapas(pg) == TODAS, f"a ordem da busca com tudo ligado ({await etapas(pg)})")
            # ----- Integrações: Instagram e Shopee -----
            await mais(pg, "integracoes")
            await espera(pg, "() => /Ligado/.test(document.getElementById('iSt').textContent)")
            check(await pg.text_content("#iSt") == "Ligado com a conta @casa: os encartes postados pelas lojas entram na busca.", "Instagram com IA e Folhetos: entra na busca")
            check(await pg.text_content("#shSt") == "Desligada.", f"Shopee sem a API e sem a aba Online: só Desligada ({await pg.text_content('#shSt')})")
            # ----- Lista do Home Assistant: "aparece aqui" só sincronizando -----
            check(await pg.locator("#syncDesc").is_hidden() and await pg.is_disabled("#syncNovos"), "Não sincronizar: sem a explicação, opções inativas")
            await pg.select_option("#syncEnt", "todo.compras")
            await pg.wait_for_timeout(500)
            check(await pg.locator("#syncDesc").is_visible() and "aparece aqui" in await pg.text_content("#syncDesc"), "sincronizando: explica o que acontece")
            await pg.locator('#v-mais section[aria-labelledby="h-ha"]').screenshot(path=SHOTS + "/ecdl-lista-ha.png")
            # ----- Usar IA desligado: o Instagram não lê, a loja adicionada à mão não entra na busca -----
            await pg.click("#usarIA")
            await pg.wait_for_timeout(600)
            check(await pg.text_content("#iSt") == "Ligado com a conta @casa.", f"Instagram sem IA: não diz que entra na busca ({await pg.text_content('#iSt')})")
            await mais(pg, "lojas")
            await pg.fill("#novaLoja", "Mercado da Esquina")
            await pg.select_option("#novaLojaCat", "mercados")
            await pg.fill("#novaLojaSite", "mercadoesquina.com.br/ofertas")
            await pg.click('#addLoja button[type="submit"]')
            await pg.wait_for_timeout(700)
            check(await pg.text_content("#lojaMsg") == '"Mercado da Esquina" adicionada.', f"sem IA: só adicionada ({await pg.text_content('#lojaMsg')})")
            esq = pg.locator("#lojasCats li.row", has_text="Mercado da Esquina")
            t = (await esq.inner_text()) if await esq.count() == 1 else ""
            check("Adicionada por você" in t and "encarte" not in t and "próxima busca" not in t, f"sem IA: a loja não promete o encarte ({t!r})")
            check(await etapas(pg) == ["Lojas perto de casa.", "Site das lojas sem site.", "Site da loja.", "Busca do site.", "Páginas de produto.",
                                       "Página de ofertas do site.", "Shopee.", "Folhetos já lidos."], f"sem IA: só as etapas sem IA ({await etapas(pg)})")
            await mais(pg, "integracoes")
            await pg.click("#usarIA")
            await pg.wait_for_timeout(600)
            await mais(pg, "lojas")
            t = await pg.locator("#lojasCats li.row", has_text="Mercado da Esquina").inner_text()
            check("o encarte de mercadoesquina.com.br é lido a cada busca" in t, f"com IA: o encarte é lido ({t!r})")
            # ----- Opções desligadas: somem da ordem da busca -----
            await mais(pg, "opcoes")
            for sw in ("#opDiretas", "#opFolhetos", "#opItens"):
                await pg.click(sw)
                await pg.wait_for_timeout(400)
            await mais(pg, "lojas")
            check(await etapas(pg) == ["Lojas perto de casa.", "Site das lojas sem site.", "Shopee.", "Busca na web com IA.", "Encarte do site."],
                  f"sem busca direta, folhetos e itens sem preço: as etapas somem ({await etapas(pg)})")
            await pg.locator('#v-mais section[aria-labelledby="h-como"]').screenshot(path=SHOTS + "/ecdl-etapas.png")
            await mais(pg, "integracoes")
            await espera(pg, "() => /Ligado/.test(document.getElementById('iSt').textContent)")
            check(await pg.text_content("#iSt") == "Ligado com a conta @casa.", "Instagram com Folhetos desligados: não diz que entra na busca")
            # ----- Minha lista: Similares e código de barras sem a busca direta -----
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(400)
            carne = pg.locator("#wish > li.item", has_text="Carne moída").first
            await carne.locator(".sim-btn").click()
            await pg.wait_for_timeout(800)
            vazio = await pg.locator("#wish > li.item", has_text="Carne moída").first.locator(".sim-vazio").inner_text()
            check(vazio == "Similares ligados: vêm da busca direta nas lojas, desligada em Mais › Opções.", f"Similares sem busca direta: não promete a próxima busca ({vazio!r})")
            check(await pg.locator("#wish > li.item", has_text="Carne moída").first.locator(".sim-vazio button").count() == 0, "e sem o Buscar agora")
            await pg.evaluate("document.getElementById('toast').hidden = true")
            await pg.locator("#wish > li.item", has_text="Carne moída").first.screenshot(path=SHOTS + "/ecdl-similares.png")
            await pg.click("#codBtn")
            await pg.fill("#codNum", "7891234567895")
            await pg.click("#codProcura")
            await espera(pg, "() => !document.getElementById('codRes').hidden")
            await pg.fill("#codNome", "Detergente Teste 500 ml")
            await pg.click("#codPor")
            await pg.wait_for_timeout(500)
            check(await pg.text_content("#addMsg") == '"Detergente Teste 500 ml" entrou na lista com o código de barras.', f"código sem busca direta ({await pg.text_content('#addMsg')})")
            # ----- religar a busca direta: volta a explicação de antes -----
            await mais(pg, "opcoes")
            await pg.click("#opDiretas")
            await pg.wait_for_timeout(400)
            await pg.click('.tabbar [data-view="lista"]')
            vazio = await pg.locator("#wish > li.item", has_text="Carne moída").first.locator(".sim-vazio").inner_text()
            check("aparecem na próxima busca" in vazio and "Buscar agora" in vazio, f"com busca direta: avisa e oferece Buscar agora ({vazio!r})")
            # ----- aba Online ligada: Compras online volta, e a Shopee pela IA quando marcada -----
            c = app.config_salva()  # a busca ainda não trouxe nada online: liga a aba pela config, como o Salvar de Mais › Casa
            c["categorias"] = ["mercados", "online"]
            app.api("PUT", "api/config", c)
            await pg.reload()
            await pg.wait_for_timeout(1200)
            await mais(pg, "lojas")
            check(await pg.locator("#onlineSec").is_visible(), "com a aba Online: Compras online aparece")
            await pg.click('#pMkt [data-v="shopee"]')
            await pg.wait_for_timeout(500)
            await mais(pg, "integracoes")
            await espera(pg, "() => /Desligada:/.test(document.getElementById('shSt').textContent)")
            check(await pg.text_content("#shSt") == "Desligada: a Shopee entra pela busca com IA.", "Shopee marcada, com IA e a aba Online: entra pela busca com IA")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
