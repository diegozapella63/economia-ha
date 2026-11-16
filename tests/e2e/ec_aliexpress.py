# EconomIA 1.40.0: Mais › Configurações › Integrações › AliExpress Afiliados: App Key e App Secret (o errado é recusado
# pela assinatura), Salvar e testar com o exemplo, o App Secret só como ••••, o AliExpress marcado sozinho em Mais › Lojas ›
# Online, o Preço pela API na linha dele, o status ao recarregar, Apagar; nada passa da largura no celular de 320 px.
import asyncio
import hashlib
import json

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, abrir_mais, check, espera, pagina, resumo

OFERTAS = {"versao": 2, "gerado_em": "2026-11-02T10:00:00-03:00", "relatorio": {"aliexpress": 1}, "categorias": [
    {"id": "online", "nome": "Online", "singular": "Online", "redes": [], "lojas": [], "cupons": [], "ofertas": []}], "lista": []}


def ali(p):
    tudo = dict({k: v[0] for k, v in p.query.items()}, **p.form())
    assina = tudo.pop("sign", "")
    certo = hashlib.md5(("segredo-ali" + "".join(k + tudo[k] for k in sorted(tudo)) + "segredo-ali").encode()).hexdigest().upper()
    if assina != certo:
        return {"error_response": {"type": "ISV", "code": "IncompleteSignature", "msg": "The request signature does not conform to platform standards"}}
    return {"aliexpress_affiliate_product_query_response": {"resp_result": {"resp_code": 200, "result": {"products": {"product": [
        {"product_title": "Garrafa Térmica Inox 1 L", "target_sale_price": "39.90", "target_sale_price_currency": "BRL", "evaluate_rate": "97%",
         "product_detail_url": "https://pt.aliexpress.com/item/1005009876543.html"}]}}}}}


async def st(pg, el, txt, ms=20000):
    try:
        await espera(pg, f"() => document.getElementById('{el}').textContent.indexOf({json.dumps(txt)}) >= 0", ms)
    except Exception as e:  # noqa: BLE001
        raise AssertionError(f"#{el} não mostrou {txt!r} (está: {await pg.text_content('#' + el)!r})") from e
    return await pg.text_content("#" + el)


async def main():
    cfg = {"cep": CEP, "categorias": ["mercados", "online"], "lista": [], "online": {"marketplaces": ["mercadolivre", "amazon"]}}
    with App(cfg, buscar=False, preparar=lambda lj: lj.rotas.__setitem__("/aliexpress", ali), antes=lambda S: S.gravar_json(S.OFERTAS, OFERTAS),
             servicos=True) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await abrir_mais(pg, "integracoes")
            await st(pg, "alSt", "Desligado")
            ints = await pg.eval_on_selector_all("#mp-integracoes section h2[id]", "els => els.map(e => e.id)")
            check(ints.index("h-ali") == ints.index("h-shopee") + 1, f"AliExpress logo depois da Shopee ({ints})")
            card = pg.locator('#v-mais section[aria-labelledby="h-ali"]')
            check(await card.locator("h2 .h-ic svg").count() == 1 and "AliExpress Afiliados" in await card.locator("h2").inner_text(), "o cartão, com o ícone")
            # App Secret errado: a assinatura não confere
            await pg.fill("#alApp", "512345")
            await pg.fill("#alSenha", "errado")
            await pg.click("#alSalvar")
            await st(pg, "alSt", "recusou a assinatura")
            check("erro" in await pg.get_attribute("#alSt", "class"), "App Secret errado: o AliExpress recusa (a assinatura não confere)")
            check("aliexpress" in app.config_salva()["online"]["marketplaces"], "salvar marca o AliExpress em Mais › Lojas › Online")
            # certo
            await pg.fill("#alSenha", "segredo-ali")
            await pg.click("#alSalvar")
            t = await st(pg, "alSt", "Pronto")
            check(t == "Pronto. Exemplo: Garrafa Térmica Inox 1 L por R$ 39,90.", f"o exemplo do teste ({t})")
            check(await pg.input_value("#alSenha") == "••••••••••••••••" and await pg.locator("#alSenhaOk").is_visible(), "o App Secret aparece só como ••••")
            check((app.S.ler_json(app.pasta + "/segredos.json") or {}).get("aliexpress") == {"app_key": "512345", "secret": "segredo-ali"}, "fica no Home Assistant")
            await card.screenshot(path=SHOTS + "/ecal-cartao.png")
            # recarregar: ligado, e o App Secret não volta para a página
            await pg.reload()
            await pg.wait_for_timeout(1000)
            await abrir_mais(pg, "integracoes")
            t = await st(pg, "alSt", "Ligado")
            check(t == "Ligado. Os preços do AliExpress vêm direto do AliExpress.", f"ligado ({t})")
            check(await pg.input_value("#alApp") == "512345", "o App Key aparece")
            check("segredo-ali" not in await pg.content(), "o App Secret não está na página")
            # Mais › Lojas › Online: marcado, com o Preço pela API
            await abrir_mais(pg, "lojas")
            if await pg.locator('#lojasAbas [data-loja-aba="online"]').is_visible():  # só Online com lojas: sem as abas
                await pg.click('#lojasAbas [data-loja-aba="online"]')
            await pg.wait_for_timeout(300)
            linha = pg.locator("#mp-lojas li.row", has=pg.locator('input[data-mkt="aliexpress"]')).first
            check(await linha.locator('input[data-mkt="aliexpress"]').is_checked(), "AliExpress marcado em Online")
            check(await linha.locator(".chip", has_text="Preço pela API").count() == 1, "com o Preço pela API")
            # desmarcado: o status diz
            await linha.locator('input[data-mkt="aliexpress"]').uncheck()
            await pg.wait_for_timeout(800)
            await abrir_mais(pg, "integracoes")
            t = await st(pg, "alSt", "desmarcado")
            check(t == "Ligado, mas o AliExpress está desmarcado em Mais › Lojas › Online.", f"desmarcado ({t})")
            # Apagar
            await pg.click("#alApagar")
            await st(pg, "alSt", "Desligado")
            check("aliexpress" not in (app.S.ler_json(app.pasta + "/segredos.json") or {}), "Apagar tira as chaves")
            check(await pg.input_value("#alApp") == "" and await pg.locator("#alApagar").is_hidden(), "os campos vazios, sem o Apagar")
            await b.close()
            # 320 px: nada passa da largura
            b, pg = await pagina(p, largura=320)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await abrir_mais(pg, "integracoes")
            await pg.locator('#v-mais section[aria-labelledby="h-ali"]').scroll_into_view_if_needed()
            largo = await pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(largo <= 0, f"320 px: nada passa da largura ({largo})")
            await pg.locator('#v-mais section[aria-labelledby="h-ali"]').screenshot(path=SHOTS + "/ecal-320.png")
            await b.close()
    resumo()


asyncio.run(main())
