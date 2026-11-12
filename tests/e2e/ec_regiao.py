# EconomIA 1.22.0: Mercados da região que entregam. Em Mais › Lojas › Compras online, a distância (só as maiores que a da
# casa, e só com o interruptor ligado); em Online, cada mercado da região com a distância e a entrega (pelo site, sem
# resposta ou não entrega), o Como foi testado e o Entrega no meu CEP, que confirma à mão (e desfaz).
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, abrir_mais, check, pagina, resumo

PASSOS_SEM = ["✗ O site comum.exemplo não tem a consulta de entrega por CEP.", "Confirme se entrega."]
OFERTAS = {"versao": 2, "gerado_em": "2026-11-02T10:00:00-03:00", "lista": [], "categorias": [
    {"id": "mercados", "nome": "Mercados", "singular": "Mercado", "redes": [{"id": "merc-giassi", "nome": "Giassi"}],
     "lojas": [{"rede": "merc-giassi", "distancia_km": 1.1, "endereco": "Rua C, 3", "fontes": ["Mapa"]}], "cupons": [], "ofertas": []},
    {"id": "online", "nome": "Online", "singular": "Online",
     "redes": [{"id": "onli-rede-entrega", "nome": "Rede Entrega"}, {"id": "onli-rede-comum", "nome": "Rede Comum"},
               {"id": "onli-rede-longe", "nome": "Rede Longe"}],
     "lojas": [{"rede": "onli-rede-entrega", "regional": True, "distancia_km": 8.0, "fontes": ["Mapa"], "lat": -26.37, "lon": -48.85,
                "entrega": {"atende": True, "passos": ["✓ O site entrega.exemplo tem a consulta de entrega por CEP.", "✓ Entrega no CEP 89216-120."]}},
               {"rede": "onli-rede-comum", "regional": True, "distancia_km": 6.0, "fontes": ["Mapa"], "entrega": {"atende": None, "passos": PASSOS_SEM}},
               {"rede": "onli-rede-longe", "regional": True, "distancia_km": 9.0, "fontes": ["Mapa"],
                "entrega": {"atende": False, "passos": ["✗ Não entrega no CEP 89216-120."]}}], "cupons": [], "ofertas": []}]}


def antes(S):
    S.gravar_json(S.OFERTAS, OFERTAS)


async def linha(pg, nome):
    return (await pg.locator("#mp-lojas li.row", has=pg.locator(".r-name", has_text=nome)).first.inner_text()).replace("\xa0", " ").lower()


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados", "online"], "lista": [], "online": {"mercados_entrega": True, "entrega_km": 10}}
    with App(cfg, buscar=False, antes=antes) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1500)
            await abrir_mais(pg, "lojas")
            await pg.wait_for_timeout(500)
            opts = [t.strip() for t in await pg.locator("#entregaKm option").all_inner_texts()]
            check(opts == ["até 10 km", "até 15 km", "até 20 km", "até 30 km", "até 50 km"], f"a distância: só maiores que os 5 km da casa ({opts})")
            check(await pg.locator("#entregaKm").input_value() == "10", "a escolhida")
            w = await pg.evaluate("() => { const e = document.getElementById('entregaKm'); return [Math.round(e.getBoundingClientRect().width), Math.round(e.parentElement.getBoundingClientRect().width), e.offsetHeight]; }")
            check(abs(w[0] - w[1]) <= 1 and w[2] == 50, f"na largura do cartão, com 50 px ({w})")
            await pg.locator("#onlineSec").screenshot(path=SHOTS + "/ecr-online.png")
            await pg.click('#onlineSec label.set-line:has(#onEntrega)')
            await pg.wait_for_timeout(600)
            check(await pg.locator("#entregaKmG").is_hidden(), "desligado: sem a distância")
            check((app.config_salva().get("online") or {}).get("mercados_entrega") is False, "desligado fica gravado")
            await pg.click('#onlineSec label.set-line:has(#onEntrega)')
            await pg.wait_for_timeout(600)
            await pg.select_option("#entregaKm", "15")
            await pg.wait_for_timeout(800)
            check((app.config_salva().get("online") or {}).get("entrega_km") == 15, "a distância fica gravada")
            # as lojas em Online
            await pg.click('#lojasAbas [data-loja-aba="online"]')
            await pg.wait_for_timeout(400)
            ent = await linha(pg, "Rede Entrega")
            check("entrega no seu cep" in ent and "8 km" in ent.replace(",0", "") and "entrega no meu cep" not in ent, f"pelo site: entrega ({ent[:120]})")
            com = await linha(pg, "Rede Comum")
            bt = pg.locator("#mp-lojas li.row", has=pg.locator(".r-name", has_text="Rede Comum")).first.locator("[data-entrega]")
            check("sem preços" in com and "não sei se entrega no seu cep" in com and (await bt.inner_text()).strip() == "Entrega aqui"
                  and await bt.get_attribute("aria-pressed") == "false", f"sem resposta: sem preço, para confirmar ({com[:160]})")
            check(await bt.evaluate("b => b.classList.contains('loja-btn') && !!b.querySelector('svg rect')"), "1.36.1: um botão com a caixinha, como o Sou do clube")
            det = pg.locator("#mp-lojas li.row", has=pg.locator(".r-name", has_text="Rede Comum")).first.locator("details.fonte-det")
            await det.locator("summary").click()
            check(PASSOS_SEM[0] in await det.inner_text(), "Como foi testado diz o porquê")
            inat = pg.locator("#mp-lojas details.inativas")
            check(await inat.count() == 1 and "Rede Longe" in await inat.text_content(), "não entrega: em Inativas")
            await pg.screenshot(path=SHOTS + "/ecr-lojas.png", full_page=True)
            # 1.24.1: Só sem fonte de preço mostra o que ainda não tem a entrega confirmada
            await pg.check("#soSemFonte")
            await pg.wait_for_timeout(400)
            nomes = [n.strip() for n in await pg.locator("#mp-lojas .group > ul.rows .r-name").all_inner_texts()]
            check("Rede Comum" in nomes and "Rede Entrega" not in nomes, f"Só sem fonte de preço: o mercado sem a entrega confirmada ({nomes})")
            await pg.uncheck("#soSemFonte")
            await pg.wait_for_timeout(400)
            # confirmar à mão
            await pg.locator("#mp-lojas li.row", has=pg.locator(".r-name", has_text="Rede Comum")).first.locator("[data-entrega]").click()
            await pg.wait_for_timeout(800)
            check("Rede Comum" in (app.config_salva().get("online") or {}).get("entrega_sim", []), "confirmada: gravado em online.entrega_sim")
            com = await linha(pg, "Rede Comum")
            check("entrega no seu cep" not in com and await bt.get_attribute("aria-pressed") == "true" and await bt.locator("svg path").count() == 1,
                  f"confirmada: a caixinha marcada, sem o selo repetido (1.36.3) ({com[:160]})")
            await pg.locator("#mp-lojas li.row", has=pg.locator(".r-name", has_text="Rede Comum")).first.locator("[data-entrega]").click()
            await pg.wait_for_timeout(800)
            check("Rede Comum" not in (app.config_salva().get("online") or {}).get("entrega_sim", []) and await bt.get_attribute("aria-pressed") == "false", "e desfaz")
            check(not pg.erros, f"sem erros na página {pg.erros[:2]}")
            await b.close()
    resumo()


asyncio.run(main())
