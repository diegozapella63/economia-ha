# EconomIA 1.15.0: as listas prontas (Compra semanal, Compra mensal…), ligadas em Mais › Configurações › Opções › Listas
# (desligadas de começo). Uma barra no alto da Minha lista: Todas, cada lista (com quantos itens) e + Nova. A tela toda (os
# itens, o cupom de economia) segue a lista aberta, que fica guardada no aparelho; em cada item, o nome de cada lista põe ou
# tira o item dela; o item novo entra na lista aberta; numa lista, "tirar desta lista" não apaga o item. Renomear e Apagar
# lista. No Roteiro, quais listas entram. Lojas, itens e preços inventados.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, App, abrir_mais, categoria, check, pagina, resumo, shot

OFERTAS = {"versao": 2, "gerado_em": "2026-11-01T10:00:00-03:00",
           "categorias": [categoria("mercados", [("merc-giassi", "Giassi", 1.0), ("merc-fort", "Fort", 2.0)])],
           "lista": [{"produto": "Café torrado em grãos", "precos": {"merc-giassi": 81.9, "merc-fort": 95.8}},
                     {"produto": "Arroz 5 kg", "precos": {"merc-giassi": 24.9, "merc-fort": 22.9}},
                     {"produto": "Pão de forma", "precos": {"merc-giassi": 9.9, "merc-fort": 8.5}}]}


def limpo(s):
    return " ".join(s.replace("\xa0", " ").split())


async def nomes(pg):
    return [limpo(x) for x in await pg.locator("#wish > li .i-prod").all_inner_texts()]


async def barra(pg):
    return [limpo(x) for x in await pg.locator("#listasBar .pick").all_inner_texts()]


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados"],
           "lista": [{"produto": "Café torrado em grãos"}, {"produto": "Arroz 5 kg"}, {"produto": "Pão de forma"}]}
    with App(cfg, buscar=False, antes=lambda S: S.gravar_json(S.OFERTAS, OFERTAS)) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(300)
            check(await pg.locator("#listasWrap").is_hidden() and await pg.locator("#wish .i-listas").count() == 0, "desligadas de começo: nada de listas")
            # ligar em Mais › Configurações › Opções
            await abrir_mais(pg, "opcoes")
            await pg.wait_for_timeout(300)
            check(not await pg.is_checked("#opListas"), "a opção começa desligada")
            await pg.locator('label[for="opListas"]').click()
            await pg.wait_for_timeout(400)
            check(app.config_salva().get("opcoes", {}).get("listas") is True, "ligada e guardada")
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(300)
            check(await barra(pg) == ["Todas 3", "+ Nova"], f"a barra: Todas e + Nova ({await barra(pg)})")
            # criar a Compra semanal: abre nela, vazia
            await pg.click('#listasBar [data-lnova]')
            await pg.fill("#listaNome", "Compra semanal")
            await pg.click('#listaForm button[type="submit"]')
            await pg.wait_for_timeout(400)
            check(await barra(pg) == ["Todas 3", "Compra semanal 0", "+ Nova"], f"criada e aberta ({await barra(pg)})")
            check(await pg.get_attribute('#listasBar [data-la]:not([data-la=""])', "aria-pressed") == "true", "a lista nova fica aberta")
            check("Nada em Compra semanal ainda" in await pg.inner_text("#wish"), "vazia: diz como pôr itens")
            check(await pg.locator("#limpar").is_hidden(), "numa lista pronta, sem Limpar lista")
            # o item novo entra na lista aberta; um que já está em Todas também entra
            await pg.fill("#novoItem", "Leite integral")
            await pg.click('#addForm button[type="submit"]')
            await pg.wait_for_timeout(300)
            await pg.fill("#novoItem", "Pão de forma")
            await pg.click('#addForm button[type="submit"]')
            await pg.wait_for_timeout(400)
            check(sorted(await nomes(pg)) == ["Leite integral", "Pão de forma"], f"a semanal com o novo e o de Todas ({await nomes(pg)})")
            sem = next(l for l in app.config_salva()["listas"])
            check(sem["nome"] == "Compra semanal" and [i["produto"] for i in app.config_salva()["lista"] if sem["id"] in (i.get("listas") or [])] == ["Pão de forma", "Leite integral"],
                  "guardado em cada item")
            # o cupom de economia segue a lista aberta: só o pão (8,50 contra 9,90)
            eco = limpo(await pg.inner_text("#heroValor"))
            check(eco == "R$ 1,40", f"o cupom só com a semanal ({eco})")
            await shot(pg, "listas-semanal")
            # Todas: tudo; em cada item, o nome da lista põe ou tira
            await pg.click('#listasBar [data-la=""]')
            await pg.wait_for_timeout(300)
            check(len(await nomes(pg)) == 4 and limpo(await pg.inner_text("#heroValor")) != "R$ 1,40", "Todas: os 4 itens e o cupom de todos")
            cafe = pg.locator("#wish > li.item", has_text="Café torrado")
            await cafe.locator(".lst-b", has_text="Compra semanal").click()
            await pg.wait_for_timeout(300)
            check(await barra(pg) == ["Todas 4", "Compra semanal 3", "+ Nova"], f"o café entrou na semanal ({await barra(pg)})")
            # numa lista, "tirar desta lista" não apaga o item
            await pg.click('#listasBar .pick:has-text("Compra semanal")')
            await pg.wait_for_timeout(300)
            leite = pg.locator("#wish > li.item", has_text="Leite integral")
            check(await leite.locator('[data-rm]').inner_text() == "tirar desta lista", "o remover vira tirar desta lista")
            await leite.locator('[data-rm]').click()
            await pg.wait_for_timeout(300)
            check("Leite integral" not in await nomes(pg) and "Leite integral" in [i["produto"] for i in app.config_salva()["lista"]], "saiu da semanal e continua em Todas")
            # a lista aberta fica guardada no aparelho
            await pg.reload()
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(300)
            check(sorted(await nomes(pg)) == ["Café torrado em grãos", "Pão de forma"], "depois de abrir de novo, continua na semanal")
            # o Roteiro escolhe as listas: Todas, ou uma ou mais
            await pg.click('.tabbar [data-view="roteiro"]')
            await pg.wait_for_timeout(300)
            check([limpo(x) for x in await pg.locator("#rotListas .pick").all_inner_texts()] == ["Todas", "Compra semanal"], "no Roteiro, as listas")
            await pg.click('#rotParadas [data-v="1"]')
            await pg.wait_for_timeout(300)
            todas = limpo(await pg.locator("#rotRes .rot-total .por").inner_text())
            await pg.click('#rotListas [data-rl]:not([data-rl=""])')
            await pg.wait_for_timeout(400)
            so = limpo(await pg.locator("#rotRes .rot-total .por").inner_text())
            check(todas != so and so == "R$ 91,80", f"só a semanal: o café e o pão no Giassi ({todas} → {so})")
            check(app.config_salva()["roteiro"]["listas"] == [sem["id"]], "guardado no roteiro")
            await shot(pg, "listas-roteiro")
            # renomear e apagar
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(300)
            await pg.click('#listasExtra [data-lren]')
            await pg.fill("#listaNome", "Semanal")
            await pg.click('#listaForm button[type="submit"]')
            await pg.wait_for_timeout(300)
            check(await barra(pg) == ["Todas 4", "Semanal 2", "+ Nova"], f"renomeada ({await barra(pg)})")
            await pg.click('#listasExtra [data-ldel]')
            check("Os itens continuam em Todas" in await pg.inner_text("#listasExtra"), "Apagar pergunta antes")
            await pg.click('#listasExtra [data-lapagar]')
            await pg.wait_for_timeout(400)
            c = app.config_salva()
            check(await barra(pg) == ["Todas 4", "+ Nova"] and len(await nomes(pg)) == 4 and c["listas"] == [] and not any(i.get("listas") for i in c["lista"])
                  and c["roteiro"]["listas"] == [], "apagada: volta para Todas, com os itens")
            check(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "nada passa da largura")
            await b.close()
            b, pg = await pagina(p, 320, 700, escuro=False)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.click('#listasBar [data-lnova]')
            await pg.fill("#listaNome", "Compra mensal do mercado")
            await pg.click('#listaForm button[type="submit"]')
            await pg.wait_for_timeout(300)
            check(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "320 px: a barra rola de lado, nada passa da largura")
            await shot(pg, "listas-320")
            # desligar esconde tudo, sem apagar
            await abrir_mais(pg, "opcoes")
            await pg.locator('label[for="opListas"]').click()
            await pg.wait_for_timeout(300)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(300)
            check(await pg.locator("#listasWrap").is_hidden() and len(await nomes(pg)) == 4 and len(app.config_salva()["listas"]) == 1,
                  "desligadas: a lista toda, e as listas continuam guardadas")
            await b.close()
    resumo()


asyncio.run(main())
