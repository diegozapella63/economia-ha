# EconomIA 1.36.12: o link que a IA dá para um marketplace (Americanas, Amazon, Magalu, Casas Bahia, iFood…) muitas vezes não
# abre o produto ("nenhum resultado encontrado"). Nele, o Abrir vira Procurar, na busca do próprio marketplace; só o anúncio
# do Mercado Livre (MLB…) e da Shopee, e o link de um preço que veio da API ou do site da loja, continuam. Lojas e preços
# inventados.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, App, categoria, check, pagina, resumo, shot

WEB = {"em": "2026-11-12T20:00:00-03:00", "via": "web"}
OFERTAS = {"versao": 2, "gerado_em": "2026-11-12T20:00:00-03:00", "categorias": [
    categoria("mercados", [("merc-azul", "Mercado Azul", 0.8)]),
    categoria("online", [("onli-americanas", "Americanas", None), ("onli-amazon", "Amazon", None), ("onli-mercado-livre", "Mercado Livre", None),
                         ("onli-casas-bahia", "Casas Bahia", None)],
              ofertas=[{"id": "o-alc", "rede": "onli-americanas", "produto": "Álcool 70 Tupi 1 L", "preco_oferta": 9.9, "preco_normal": 14.9, "tipo": "promo", "tags": [],
                        "fonte": "https://www.americanas.com.br/produto/7788990011"},
                       {"id": "o-ml", "rede": "onli-mercado-livre", "produto": "Álcool gel 500 ml", "preco_oferta": 8.9, "preco_normal": 12.9, "tipo": "promo", "tags": [],
                        "fonte": "https://produto.mercadolivre.com.br/MLB-1234567890-alcool-gel-500ml"}])],
    "lista": [{"produto": "Álcool", "precos": {
        "onli-americanas": {"preco": 12.59, "frete": 0, "prazo_dias": 2},
        "onli-amazon": {"preco": 21.99, "frete": 0, "prazo_dias": 2},
        "onli-mercado-livre": {"preco": 22.97, "frete": 0, "prazo_dias": 3},
        "onli-casas-bahia": {"preco": 23.5, "frete": 0, "prazo_dias": 4},
        "merc-azul": 24.99},
        "links": {"onli-americanas": "https://www.americanas.com.br/produto/123456789", "onli-amazon": "https://www.amazon.com.br/dp/B0ABCDEFGH",
                  "onli-mercado-livre": "https://produto.mercadolivre.com.br/MLB-1234567890-alcool", "onli-casas-bahia": "https://www.casasbahia.com.br/alcool/p/55",
                  "merc-azul": "https://www.mercadoazul.exemplo/alcool-70/p"},
        "vistos": {"onli-americanas": WEB, "onli-amazon": WEB, "onli-casas-bahia": WEB, "merc-azul": dict(WEB, via="site"),
                   "onli-mercado-livre": dict(WEB, via="api")}}]}


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados", "online"], "online": {"marketplaces": ["americanas", "amazon", "mercadolivre", "casasbahia"]},
           "lista": [{"produto": "Álcool"}]}
    with App(cfg, buscar=False, antes=lambda S: S.gravar_json(S.OFERTAS, OFERTAS)) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(400)
            alc = pg.locator("#wish > li.item", has_text="Álcool").first
            best = alc.locator("a.i-best")
            check(await best.get_attribute("href") == "https://www.americanas.com.br/busca/alcool" and "Procurar" in await best.inner_text(),
                  f"Americanas pela IA: Procurar na busca da Americanas ({await best.get_attribute('href')})")
            hrefs = {(await a.inner_text()).split("R$")[0].strip(): await a.get_attribute("href") for a in await alc.locator(".i-others a").all()}
            check(hrefs.get("Amazon") == "https://www.amazon.com.br/s?k=%C3%81lcool", f"Amazon pela IA: a busca da Amazon ({hrefs})")
            check(hrefs.get("Casas Bahia") == "https://www.casasbahia.com.br/alcool/b", "Casas Bahia pela IA: a busca da Casas Bahia")
            check(hrefs.get("Mercado Livre") == "https://produto.mercadolivre.com.br/MLB-1234567890-alcool", "Mercado Livre pela API: o anúncio")
            check(hrefs.get("Mercado Azul") == "https://www.mercadoazul.exemplo/alcool-70/p", "o site da loja: o produto")
            await shot(pg, "links-lista")
            # ----- as ofertas -----
            await pg.click('.tabbar [data-view="ofertas"]')
            await pg.wait_for_timeout(500)
            await pg.click('#cats [data-cat="online"]')
            await pg.wait_for_timeout(400)
            h = await pg.locator("#deals .deal", has_text="Tupi").locator(".d-acts a").get_attribute("href")
            check(h == "https://www.americanas.com.br/busca/alcool-70-tupi-1-l", f"a oferta da Americanas: a busca dela ({h})")
            h = await pg.locator("#deals .deal", has_text="Álcool gel").locator(".d-acts a").get_attribute("href")
            check(h == "https://produto.mercadolivre.com.br/MLB-1234567890-alcool-gel-500ml", f"a do Mercado Livre, com o anúncio: o anúncio ({h})")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
