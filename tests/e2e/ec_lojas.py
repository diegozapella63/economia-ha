# EconomIA 0.16.6–0.17.7: Mais › Lojas: abas por tipo de loja, procurar loja pelo nome (em todas as abas), Só sem fonte
# de preço, desmarcar (Inativas) e marcar de novo, clube na linha da loja, loja sem localização em Online.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, check, pagina, resumo

OFERTAS = {"versao": 2, "gerado_em": "2026-11-02T10:00:00-03:00", "categorias": [
    {"id": "farmacias", "nome": "Farmácias", "singular": "Farmácia",
     "redes": [{"id": "farm-raia", "nome": "Droga Raia"}, {"id": "farm-nissei", "nome": "Farmácias Nissei"}],
     "lojas": [{"rede": "farm-raia", "distancia_km": 0.8, "endereco": "Rua A, 1", "fontes": ["Mapa"]},
               {"rede": "farm-nissei", "distancia_km": 1.4, "endereco": "Rua B, 2", "fontes": ["Mapa"],
                "preco_fonte": {"como": "site", "exemplo": "Dipirona 1g por R$ 9,90"}}], "cupons": [], "ofertas": []},
    {"id": "mercados", "nome": "Mercados", "singular": "Mercado",
     "redes": [{"id": "merc-giassi", "nome": "Giassi"}, {"id": "merc-angeloni", "nome": "Angeloni"}, {"id": "merc-fort", "nome": "Fort Atacadista"}],
     "lojas": [{"rede": "merc-giassi", "distancia_km": 1.1, "endereco": "Rua C, 3", "fontes": ["Mapa", "Site"]},
               {"rede": "merc-angeloni", "distancia_km": 2.0, "endereco": "Rua D, 4", "fontes": ["Mapa", "Site"]},
               {"rede": "merc-fort", "distancia_km": 4.2, "endereco": "Rua E, 5", "fontes": ["Mapa"]}], "cupons": [], "ofertas": []},
    {"id": "petshops", "nome": "Pet shops", "singular": "Pet shop",
     "redes": [{"id": "pets-cobasi", "nome": "Cobasi"}],
     "lojas": [{"rede": "pets-cobasi", "distancia_km": None, "fontes": ["Site"]}], "cupons": [], "ofertas": []},
    {"id": "online", "nome": "Online", "singular": "Online", "redes": [], "lojas": [], "cupons": [], "ofertas": []}],
    "lista": []}


def antes(S):
    S.gravar_json(S.OFERTAS, OFERTAS)


async def abre_lojas(pg):
    await pg.click('.tabbar [data-view="mais"]')
    await pg.wait_for_timeout(300)
    await pg.click("#aba-lojas")
    await pg.wait_for_timeout(500)


async def nomes(pg):
    return [n.strip() for n in await pg.locator("#mp-lojas .group > ul.rows .r-name").all_inner_texts()]


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["farmacias", "mercados", "petshops", "online"], "lista": []}
    with App(cfg, buscar=False, antes=antes) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1500)
            await abre_lojas(pg)
            abas = [t.strip() for t in await pg.locator("#lojasAbas button").all_inner_texts()]
            check(abas == ["Farmácias", "Mercados", "Pet shops", "Online"], f"abas por tipo de loja ({abas})")
            check(await nomes(pg) == ["Droga Raia", "Farmácias Nissei"], f"aba Farmácias ({await nomes(pg)})")
            await pg.click('#lojasAbas [data-loja-aba="mercados"]')
            await pg.wait_for_timeout(300)
            check(await nomes(pg) == ["Giassi", "Angeloni", "Fort Atacadista"], f"aba Mercados, da mais perto para a mais longe ({await nomes(pg)})")
            check(await pg.get_attribute('#lojasAbas [data-loja-aba="mercados"]', "aria-pressed") == "true", "aba marcada")
            await pg.locator("#mp-lojas").screenshot(path=SHOTS + "/ecj-mercados.png")
            # loja sem localização: em Online
            await pg.click('#lojasAbas [data-loja-aba="petshops"]')
            await pg.wait_for_timeout(300)
            check("Cobasi" not in await nomes(pg), "Cobasi (sem localização) sai de Pet shops")
            await pg.click('#lojasAbas [data-loja-aba="online"]')
            await pg.wait_for_timeout(300)
            txt = await pg.locator("#mp-lojas").inner_text()
            check("PET SHOPS SEM LOCALIZAÇÃO" in txt.upper() and "Cobasi" in txt, "e aparece em Online, no grupo sem localização")
            # procurar pelo nome: vale em todas as abas
            await pg.fill("#lojaBusca", "nis")
            await pg.wait_for_timeout(400)
            check(await nomes(pg) == ["Farmácias Nissei"], f"procurar 'nis' acha a Nissei em outra aba ({await nomes(pg)})")
            check(all(await pg.locator("#lojasAbas button").evaluate_all("bs => bs.map(b => b.getAttribute('aria-pressed') === 'false')")), "procurando, nenhuma aba fica marcada")
            await pg.fill("#lojaBusca", "")
            await pg.wait_for_timeout(300)
            # Só sem fonte de preço
            await pg.click('#lojasAbas [data-loja-aba="farmacias"]')
            await pg.check("#soSemFonte")
            await pg.wait_for_timeout(300)
            check(await nomes(pg) == ["Droga Raia"], f"só sem fonte: a Nissei (com site) sai ({await nomes(pg)})")
            await pg.uncheck("#soSemFonte")
            await pg.wait_for_timeout(300)
            # desmarcar: vai para Inativas e para a config
            await pg.locator('#mp-lojas input[data-rede="farm-raia"]').uncheck()
            await pg.wait_for_timeout(1000)
            inat = pg.locator("#mp-lojas details.inativas")
            check(await inat.count() == 1 and "Inativas (1)" in await inat.locator("summary").inner_text(), "Droga Raia em Inativas")
            check("farm-raia" in (app.config_salva().get("lojas") or {}).get("ignorar", []), "gravado em lojas.ignorar")
            await inat.locator("summary").click()
            await pg.locator('#mp-lojas input[data-rede="farm-raia"]').check()
            await pg.wait_for_timeout(1000)
            check("farm-raia" not in (app.config_salva().get("lojas") or {}).get("ignorar", []), "marcar de novo volta a acompanhar")
            # clube na linha da loja (Nissei: Club Nissei)
            clube = pg.locator('#mp-lojas [data-clube="farm-nissei"]')
            check(await clube.count() == 1 and "Club Nissei" in await clube.inner_text(), "clube da Nissei na linha da loja")
            await clube.click()
            await pg.wait_for_timeout(1000)
            check(await pg.get_attribute('#mp-lojas [data-clube="farm-nissei"]', "aria-pressed") == "true", "toque marca que é do clube")
            check("farm-nissei" in (app.config_salva().get("clubes") or []), "gravado em clubes")
            await pg.locator("#mp-lojas").screenshot(path=SHOTS + "/ecj-farmacias.png")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
