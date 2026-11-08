# EconomIA 0.19.0: Mais › Lojas, as ações: Encontrar lojas (o mapa falso, o andamento do teste de preço e o resumo),
# o resultado do teste em cada loja ("Preço pelo site", "Como foi testado"), Adicionar site de ofertas numa loja (site
# inválido, @ do Instagram), Testar agora, Adicionar loja que não apareceu (com e sem site, remover) e Buscar preços agora.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, HAFalso, abrir_mais, check, espera, pagina, prod, resumo


def prepara(lojas):
    b = lojas.base
    lojas.regioes["super-koch"] = "koch01"
    lojas.catalogo["super-koch"] = [prod("Leite Integral Tirol 1L", 4.59, "Laticínios/Leites")]
    lojas.rotas["/overpass"] = lambda p: {"elements": [
        {"type": "node", "lat": -26.3045, "lon": -48.85, "tags": {"name": "Farmácia Bem Estar", "amenity": "pharmacy", "addr:street": "Rua das Flores", "addr:housenumber": "100"}},
        {"type": "node", "lat": -26.309, "lon": -48.85, "tags": {"name": "Super Koch", "shop": "supermarket", "website": b + "/super-koch/"}}]}


async def linha(pg, nome):
    return pg.locator("#lojasCats li.row", has_text=nome).first


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["farmacias", "mercados", "online"], "usar_ia": False, "lista": [{"produto": "Leite integral"}]}
    with App(cfg, buscar=False, preparar=prepara, ha=HAFalso(), servicos=True) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await abrir_mais(pg, "lojas")
            # ----- Encontrar lojas -----
            await pg.click("#acharLojas2")
            await espera(pg, "() => /Testei 2 lojas/.test(document.getElementById('lojasAcharMsg').textContent)", 30000)
            msg = await pg.text_content("#lojasAcharMsg")
            check("até 5 km (OpenStreetMap)." in msg and "1 com preço direto do site, 1 sem fonte de preço sem IA." in msg, f"o resumo do mapa e do teste ({msg})")
            check(await pg.locator("#lojasAcharMsg [data-buscar-ja]").is_visible(), "oferece Buscar preços agora")
            check(not await pg.is_disabled("#acharLojas2"), "o botão volta")
            await pg.click('#lojasAbas [data-loja-aba="mercados"]')
            koch = (await (await linha(pg, "Super Koch")).inner_text()).replace("\xa0", " ")
            check("PREÇO PELO SITE" in koch.upper() and "ex.: Leite Integral Tirol 1L por R$ 4,59" in koch, f"Super Koch: preço pelo site ({koch[:140]})")
            await (await linha(pg, "Super Koch")).locator("details.fonte-det summary").click()
            passos = await (await linha(pg, "Super Koch")).locator("details.fonte-det ul").inner_text()
            check("✓ Site com busca direta" in passos and "✓ Achei \"leite\" no site" in passos, f"Como foi testado ({passos})")
            await pg.locator("#mp-lojas").screenshot(path=SHOTS + "/ecla-mercados.png")
            await pg.click('#lojasAbas [data-loja-aba="farmacias"]')
            bem = (await (await linha(pg, "Farmácia Bem Estar")).inner_text()).upper()
            check("SEM FONTE DE PREÇO" in bem and "ADICIONAR SITE DE OFERTAS" in bem and "RUA DAS FLORES, 100" in bem, "a farmácia sem site: sem fonte, com o botão do site")
            check("LIGUE A IA PARA TER O PREÇO" in bem, "sem IA: diz o que falta")
            # ----- site da loja: inválido e @ do Instagram -----
            await (await linha(pg, "Farmácia Bem Estar")).locator("[data-site]").click()
            form = pg.locator("#lojasCats form[data-site-form]")
            await form.locator("input").fill("abc")
            await form.locator("button[type=submit]").click()
            check(await pg.text_content("#toast") == "Esse endereço não parece um site.", "site inválido")
            await form.locator("input").fill("@bemestar_farma")
            await form.locator("button[type=submit]").click()
            await pg.wait_for_timeout(700)
            add = app.config_salva()["lojas"]["adicionar"]
            check(add == [{"categoria": "farmacias", "nome": "Farmácia Bem Estar", "site": "https://www.instagram.com/bemestar_farma/"}], f"o @ vira o endereço do Instagram ({add})")
            check("@bemestar_farma" in await (await linha(pg, "Farmácia Bem Estar")).inner_text(), "a loja mostra o Instagram")
            # ----- Testar agora -----
            await (await linha(pg, "Farmácia Bem Estar")).locator("[data-testar]").click()
            check("Testando…" in await (await linha(pg, "Farmácia Bem Estar")).inner_text(), "Testando…")
            await espera(pg, "() => /Farmácia Bem Estar:/.test(document.getElementById('toast').textContent)", 20000)
            check(await pg.text_content("#toast") == "Farmácia Bem Estar: veja em Como foi testado.", "o resumo do teste")
            await espera(pg, "() => /Tem Instagram/.test(document.getElementById('lojasCats').textContent)")
            det = (await linha(pg, "Farmácia Bem Estar")).locator("details.fonte-det")
            check(await det.get_attribute("open") is not None and "Tem Instagram (@bemestar_farma): ligue o Instagram em Mais › Configurações › Integrações" in await det.inner_text(),
                  "Como foi testado abre sozinho, com o passo do Instagram")
            await pg.locator("#mp-lojas").screenshot(path=SHOTS + "/ecla-testar.png")
            # ----- Adicionar loja que não apareceu -----
            await pg.fill("#novaLoja", "ab")
            await pg.click('#addLoja button[type="submit"]')
            check(await pg.text_content("#lojaMsg") == "Escreva o nome da loja e, se souber, a rua.", "nome curto")
            await pg.fill("#novaLoja", "Mercado da Esquina")
            await pg.select_option("#novaLojaCat", "mercados")
            await pg.fill("#novaLojaSite", "não é site")
            await pg.click('#addLoja button[type="submit"]')
            check(await pg.text_content("#lojaMsg") == "O site de ofertas não parece um endereço válido.", "site inválido")
            await pg.fill("#novaLojaSite", "mercadoesquina.com.br/ofertas")
            await pg.click('#addLoja button[type="submit"]')
            await pg.wait_for_timeout(700)
            check(await pg.text_content("#lojaMsg") == '"Mercado da Esquina" adicionada.', "adicionada (com a IA desligada, não promete o encarte)")
            add = app.config_salva()["lojas"]["adicionar"]
            check({"categoria": "mercados", "nome": "Mercado da Esquina", "site": "https://mercadoesquina.com.br/ofertas"} in add, "com https://")
            check(await pg.locator('#lojasAbas [data-loja-aba="online"]').count() == 0, "a busca ainda não trouxe nada online: sem a aba Online")
            await pg.click('#lojasAbas [data-loja-aba="mercados"]')
            esq = pg.locator("#lojasCats li.row", has_text="Mercado da Esquina")
            check(await esq.count() == 1 and "Adicionada por você" in await esq.inner_text() and "encarte" not in await esq.inner_text(),
                  "a loja adicionada, ainda sem localização, aparece na aba dela")
            check("MERCADOS SEM LOCALIZAÇÃO" in (await pg.text_content("#lojasCats")).upper(), "no grupo sem localização")
            await pg.locator("#mp-lojas").screenshot(path=SHOTS + "/ecla-adicionada.png")
            await esq.locator("button.rm").click()
            await pg.wait_for_timeout(700)
            check(not any(a["nome"] == "Mercado da Esquina" for a in app.config_salva()["lojas"]["adicionar"]), "remover")
            # ----- Buscar preços agora -----
            await pg.click("#lojasAcharMsg [data-buscar-ja]")
            await espera(pg, "() => /Busca concluída/.test(document.getElementById('buscaMsg').textContent)", 30000)
            await pg.click('.tabbar [data-view="lista"]')
            await espera(pg, "() => /4,59/.test(document.getElementById('wish').textContent)")
            leite = (await pg.locator("#wish > li.item", has_text="Leite integral").inner_text()).replace("\xa0", " ")
            check("Super Koch" in leite and "R$ 4,59" in leite, "a loja achada pelo mapa já traz o preço pelo site, sem IA")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
