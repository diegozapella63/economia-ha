# EconomIA 1.15.0: as listas prontas (Compra semanal, Compra mensal…), ligadas em Mais › Configurações › Opções › Listas
# (desligadas de começo). Uma barra no alto da Minha lista: cada lista (com quantos itens) e + Nova. A tela toda (os itens,
# o cupom de economia) segue a lista aberta, que fica guardada no aparelho; em cada item, o nome de cada lista põe ou tira o
# item dela; o item novo entra na lista aberta; numa lista, "tirar desta lista" não apaga o item. Renomear e Apagar lista.
# No Roteiro, quais listas entram.
# 1.17.0: sem "Todas": Nenhuma mostra só os itens que não estão em lista nenhuma; Mover itens passa os itens escolhidos de
# uma lista para outra (ou para Nenhuma); no Roteiro, cada lista e Nenhuma, ao menos uma. Lojas, itens e preços inventados.
# 1.26.0: a lista pronta é fixa: Comprei hoje marca o item (Comprados (n), no fim e recolhido, com Desmarcar) e o cupom e o
# Roteiro olham só para o que falta; Começar de novo desmarca tudo, sem tirar item nenhum. Cada lista pode ter um ícone (Editar).
# 1.27.0: todo item fica numa lista: Nenhuma só aparece enquanto tem item (para passar para uma lista com Mover itens), não é
# destino do Mover, e sem lista aberta nada entra (Crie uma lista / Abra uma lista); tirar da única lista leva ao histórico;
# os itens não têm mais os botões das listas.
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


async def abre(pg, nome):
    await pg.locator("#listasBar .pick", has_text=nome).click()
    await pg.wait_for_timeout(300)


def de(app, lid):
    return [i["produto"] for i in app.config_salva()["lista"] if lid in (i.get("listas") or [])]


async def nova(pg, nome):
    await pg.click('#listasBar [data-lnova]')
    await pg.fill("#listaNome", nome)
    await pg.click('#listaForm button[type="submit"]')
    await pg.wait_for_timeout(400)


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
            check(await barra(pg) == ["Nenhuma 3", "+ Nova"], f"a barra: Nenhuma (os de antes, sem Todas) e + Nova ({await barra(pg)})")
            check(await pg.locator("#listasExtra [data-lmover]").count() == 0, "sem outra lista, nada de Mover itens")
            check(await pg.locator("#addArea").is_hidden() and await pg.inner_text("#addBloq") == "Crie uma lista para pôr itens.",
                  "sem lista, nada entra: Crie uma lista")
            await shot(pg, "listas-sem-lista")
            # criar a Compra semanal: abre nela, vazia
            await nova(pg, "Compra semanal")
            check(await barra(pg) == ["Nenhuma 3", "Compra semanal 0", "+ Nova"], f"criada e aberta ({await barra(pg)})")
            check(await pg.get_attribute('#listasBar [data-la]:not([data-la=""])', "aria-pressed") == "true", "a lista nova fica aberta")
            check("Nada em Compra semanal ainda" in await pg.inner_text("#wish"), "vazia: diz como pôr itens")
            check(await pg.locator("#addArea").is_visible() and await pg.locator("#addBloq").is_hidden(), "com a lista aberta, o Adicionar volta")
            check(await pg.locator("#limpar").is_hidden(), "numa lista pronta, sem Limpar lista")
            # o item novo entra na lista aberta; um que está em Nenhuma também entra (e sai de Nenhuma)
            await pg.fill("#novoItem", "Leite integral")
            await pg.click('#addForm button[type="submit"]')
            await pg.wait_for_timeout(300)
            await pg.fill("#novoItem", "Pão de forma")
            await pg.click('#addForm button[type="submit"]')
            await pg.wait_for_timeout(400)
            check(sorted(await nomes(pg)) == ["Leite integral", "Pão de forma"], f"a semanal com o novo e o de Nenhuma ({await nomes(pg)})")
            sem = app.config_salva()["listas"][0]
            check(sem["nome"] == "Compra semanal" and de(app, sem["id"]) == ["Pão de forma", "Leite integral"], "guardado em cada item")
            check(await barra(pg) == ["Nenhuma 2", "Compra semanal 2", "+ Nova"], f"o pão saiu de Nenhuma ({await barra(pg)})")
            # o cupom de economia segue a lista aberta: só o pão (8,50 contra 9,90)
            eco = limpo(await pg.inner_text("#heroValor"))
            check(eco == "R$ 1,40", f"o cupom só com a semanal ({eco})")
            await shot(pg, "listas-semanal")
            # Nenhuma: só os que não estão em lista nenhuma; nada entra nela, e o Mover passa para uma lista
            await abre(pg, "Nenhuma")
            check(await nomes(pg) == ["Café torrado em grãos", "Arroz 5 kg"] and limpo(await pg.inner_text("#heroValor")) != "R$ 1,40", f"Nenhuma: os 2 sem lista ({await nomes(pg)})")
            check(await pg.locator("#addArea").is_hidden() and await pg.inner_text("#addBloq") == "Abra uma lista para pôr itens.", "em Nenhuma, nada entra")
            check(await pg.locator("#wish .i-listas, #wish .lst-b").count() == 0, "os itens sem os botões das listas")
            await pg.click("#listasExtra [data-lmover]")
            await pg.wait_for_timeout(200)
            await pg.locator("#listasExtra .lm-itens label", has_text="Café torrado").click()
            await pg.click("#listasExtra [data-lmok]")
            await pg.wait_for_timeout(400)
            check(await barra(pg) == ["Nenhuma 1", "Compra semanal 3", "+ Nova"] and await nomes(pg) == ["Arroz 5 kg"], f"o café foi para a semanal ({await barra(pg)})")
            # numa lista, "tirar desta lista": sem outra lista, o item sai da lista e fica no histórico (nada vai para Nenhuma)
            await abre(pg, "Compra semanal")
            leite = pg.locator("#wish > li.item", has_text="Leite integral")
            check((await leite.locator('[data-rm]').inner_text()).strip() == "Tirar desta lista", "o remover vira tirar desta lista")
            await leite.locator('[data-rm]').click()
            await pg.wait_for_timeout(300)
            c = app.config_salva()
            check("Leite integral" not in await nomes(pg) and await barra(pg) == ["Nenhuma 1", "Compra semanal 2", "+ Nova"]
                  and not any(i["produto"] == "Leite integral" for i in c["lista"]) and any(h["produto"] == "Leite integral" for h in c["historico"]),
                  f"saiu da lista e ficou no histórico ({await barra(pg)})")
            await pg.fill("#novoItem", "Leite integral")
            await pg.click('#addForm button[type="submit"]')
            await pg.wait_for_timeout(300)
            check(await barra(pg) == ["Nenhuma 1", "Compra semanal 3", "+ Nova"], "de volta do histórico, na semanal")
            # a lista aberta fica guardada no aparelho
            await pg.reload()
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(300)
            check(sorted(await nomes(pg)) == ["Café torrado em grãos", "Leite integral", "Pão de forma"], "depois de abrir de novo, continua na semanal")
            # o Roteiro escolhe a lista (1.23.0: uma só, como Paradas e O que comprar; 1.25.1: sem Todas): cada uma e Nenhuma
            await pg.click('.tabbar [data-view="roteiro"]')
            await pg.wait_for_timeout(300)
            rl = [limpo(x) for x in await pg.locator("#rotListas button").all_inner_texts()]
            check(rl == ["Compra semanal", "Nenhuma"], f"no Roteiro: as listas e Nenhuma, sem Todas ({rl})")
            check(await pg.locator('#rotListas [aria-pressed="true"]').all_inner_texts() == ["Compra semanal"], "de começo, a lista aberta na Minha lista")
            hs = await pg.evaluate("[...document.querySelectorAll('#rotListas button, #rotEscopo button')].map(b => b.offsetHeight)")
            check(len(set(hs)) == 1, f"do tamanho das outras escolhas ({hs})")
            await pg.click('#rotParadas [data-v="1"]')
            await pg.wait_for_timeout(300)
            so = limpo(await pg.locator("#rotRes .rot-total .por").inner_text())
            check(so == "R$ 91,80", f"só a semanal: o café e o pão no Giassi ({so})")
            await pg.click('#rotListas [data-rl="_nenhuma"]')
            await pg.wait_for_timeout(400)
            check(app.config_salva()["roteiro"]["listas"] == ["_nenhuma"], "Nenhuma: os itens sem lista, guardado no roteiro")
            check(await pg.locator('#rotListas [aria-pressed="true"]').all_inner_texts() == ["Nenhuma"], "uma escolha só")
            nenhuma = limpo(await pg.locator("#rotRes .rot-total .por").inner_text())
            check(nenhuma != so, f"Nenhuma: outro total ({nenhuma})")
            await pg.click(f'#rotListas [data-rl="{sem["id"]}"]')
            await pg.wait_for_timeout(300)
            check(app.config_salva()["roteiro"]["listas"] == [sem["id"]], "de volta à semanal")
            await shot(pg, "listas-roteiro")
            # Mover itens: da semanal para a mensal, só os marcados
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(300)
            await nova(pg, "Compra mensal")
            men = app.config_salva()["listas"][1]
            await abre(pg, "Compra semanal")
            await pg.click("#listasExtra [data-lmover]")
            await pg.wait_for_timeout(300)
            alvos = [limpo(x) for x in await pg.locator("#listasExtra .lista-mover .pick").all_inner_texts()]
            check(alvos == ["Compra mensal"], f"Mover para: as outras listas, sem Nenhuma ({alvos})")
            check(await pg.locator("#listasExtra [data-lmok]").is_disabled(), "sem item marcado, o Mover espera")
            await pg.locator("#listasExtra .lm-itens label", has_text="Pão de forma").click()
            await pg.locator("#listasExtra .lista-mover .pick", has_text="Compra mensal").click()
            await pg.wait_for_timeout(200)
            check(await pg.inner_text("#listasExtra [data-lmok]") == "Mover 1 item", "o botão diz quantos")
            med = await pg.evaluate("[...document.querySelectorAll('#listasExtra .lm-fim > *')].map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; })")
            check(len(med) == 2 and med[0] == med[1] and med[0][1] == 50, f"Mover e Cancelar lado a lado, do mesmo tamanho ({med})")
            await shot(pg, "listas-mover")
            await pg.click("#listasExtra [data-lmok]")
            await pg.wait_for_timeout(400)
            check(de(app, sem["id"]) == ["Café torrado em grãos", "Leite integral"] and de(app, men["id"]) == ["Pão de forma"], "o pão foi para a mensal e saiu da semanal")
            check(await barra(pg) == ["Nenhuma 1", "Compra semanal 2", "Compra mensal 1", "+ Nova"] and sorted(await nomes(pg)) == ["Café torrado em grãos", "Leite integral"],
                  f"a barra conta ({await barra(pg)})")
            # de Nenhuma, Marcar todos para a semanal: vazia, Nenhuma some e a semanal fica aberta
            await abre(pg, "Nenhuma")
            await pg.click("#listasExtra [data-lmover]")
            await pg.click("#listasExtra [data-lmtodos]")
            await pg.locator("#listasExtra .lista-mover .pick", has_text="Compra semanal").click()
            await pg.wait_for_timeout(200)
            check(await pg.inner_text("#listasExtra [data-lmok]") == "Mover 1 item", "Marcar todos")
            await pg.click("#listasExtra [data-lmok]")
            await pg.wait_for_timeout(400)
            check(sorted(de(app, sem["id"])) == ["Arroz 5 kg", "Café torrado em grãos", "Leite integral"] and await barra(pg) == ["Compra semanal 3", "Compra mensal 1", "+ Nova"],
                  f"Nenhuma ficou vazia e some ({await barra(pg)})")
            check(await pg.get_attribute('#listasBar [aria-pressed="true"]', "data-la") == sem["id"], "abre a primeira lista")
            await pg.click('.tabbar [data-view="roteiro"]')
            await pg.wait_for_timeout(300)
            rl = [limpo(x) for x in await pg.locator("#rotListas button").all_inner_texts()]
            check(rl == ["Compra semanal", "Compra mensal"], f"no Roteiro, sem Nenhuma vazia ({rl})")
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(300)
            # 1.26.0: comprar na lista fixa: o item vai para Comprados (no fim, recolhido) e a análise olha só para o resto
            await abre(pg, "Compra semanal")
            check(await pg.locator("#listasExtra [data-lrecomecar]").count() == 0 and await pg.locator("#wishComprados details").count() == 0,
                  "nada comprado: sem Comprados nem Começar de novo")
            check(limpo(await pg.inner_text("#heroValor")) == "R$ 15,90", f"o cupom com o arroz e o café ({await pg.inner_text('#heroValor')})")
            await pg.locator("#wish > li.item", has_text="Café torrado").locator("[data-comprei]").click()
            await pg.wait_for_timeout(400)
            semc = next(x for x in app.config_salva()["listas"] if x["id"] == sem["id"])
            check(len(semc.get("comprados") or []) == 1 and sorted(await nomes(pg)) == ["Arroz 5 kg", "Leite integral"], f"o café saiu do que falta ({await nomes(pg)})")
            check(await pg.inner_text("#wishComprados summary") == "Comprados (1)" and not await pg.locator("#wishComprados details").evaluate("d => d.open"),
                  "no fim, recolhido: Comprados (1)")
            check(any(i["produto"] == "Café torrado em grãos" and i.get("compras") for i in app.config_salva()["lista"]), "a data da compra fica no histórico")
            check(sorted(de(app, sem["id"])) == ["Arroz 5 kg", "Café torrado em grãos", "Leite integral"], "nenhum item sai da lista")
            check(limpo(await pg.inner_text("#heroValor")) == "R$ 2,00", f"o cupom sem o que já foi comprado ({await pg.inner_text('#heroValor')})")
            await pg.click('.tabbar [data-view="roteiro"]')
            await pg.wait_for_timeout(300)
            rt = await pg.inner_text("#rotRes")
            check("Arroz 5 kg" in rt and "Café torrado" not in rt, "o Roteiro sem o que já foi comprado")
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(300)
            # Desmarcar volta para o que falta
            await pg.click("#wishComprados summary")
            await pg.locator("#wishComprados [data-descomprar]").click()
            await pg.wait_for_timeout(400)
            check(len(await nomes(pg)) == 3 and await pg.locator("#wishComprados details").count() == 0, "Desmarcar: de volta ao que falta")
            # tudo comprado; Começar de novo desmarca tudo
            for nome in ("Café torrado", "Arroz 5 kg", "Leite integral"):
                await pg.locator("#wish > li.item", has_text=nome).locator("[data-comprei]").click()
                await pg.wait_for_timeout(300)
            check("Tudo comprado" in await pg.inner_text("#wish") and await pg.inner_text("#wishComprados summary") == "Comprados (3)", "tudo comprado")
            check(await barra(pg) == ["Compra semanal 3", "Compra mensal 1", "+ Nova"], f"a lista continua com os 3 ({await barra(pg)})")
            await shot(pg, "listas-comprados")
            await pg.click("#listasExtra [data-lrecomecar]")
            await pg.wait_for_timeout(400)
            semc = next(x for x in app.config_salva()["listas"] if x["id"] == sem["id"])
            check(not semc.get("comprados") and len(await nomes(pg)) == 3 and await pg.locator("#listasExtra [data-lrecomecar]").count() == 0,
                  "Começar de novo: tudo para comprar de novo")
            # Editar (o nome e o ícone) e apagar
            await abre(pg, "Compra semanal")
            check(await pg.inner_text('#listasExtra [data-lren]') == "Editar", "Editar")
            await pg.click('#listasExtra [data-lren]')
            await pg.fill("#listaNome", "Semanal")
            ics = await pg.evaluate("[...document.querySelectorAll('#listaForm .lista-icones .pick')].map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.top), Math.round(r.width), Math.round(r.height)]; })")
            check(len(ics) == 12 and len({t for t, _, _ in ics}) == 2 and len({(w, h) for _, w, h in ics}) == 1 and ics[0][2] == 50,
                  f"12 ícones, seis por linha, do mesmo tamanho ({ics})")
            await pg.click('#listaForm [data-lic="🥦"]')
            await pg.click('#listaForm [data-lic="🛒"]')
            check(await pg.input_value("#listaNome") == "Semanal" and await pg.locator('#listaForm [data-lic][aria-pressed="true"]').all_inner_texts() == ["🛒"],
                  "um ícone só, e o nome digitado fica")
            await pg.click('#listaForm [data-lic="🛒"]')
            check(await pg.locator('#listaForm [data-lic][aria-pressed="true"]').count() == 0, "tocar de novo tira o ícone")
            await pg.click('#listaForm [data-lic="🛒"]')
            med = await pg.evaluate("[...document.querySelectorAll('#listaForm .row-form > *')].map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.top), Math.round(r.width), Math.round(r.height)]; })")
            check(len(med) == 2 and med[0] == med[1] and med[0][2] == 50, f"Salvar e Cancelar lado a lado, do mesmo tamanho ({med})")
            await shot(pg, "listas-editar")
            await pg.click('#listaForm button[type="submit"]')
            await pg.wait_for_timeout(300)
            check(await barra(pg) == ["🛒 Semanal 3", "Compra mensal 1", "+ Nova"], f"com o nome e o ícone novos ({await barra(pg)})")
            check(app.config_salva()["listas"][0].get("icone") == "🛒", "o ícone fica guardado na lista")
            await pg.click('#listasExtra [data-ldel]')
            check("Os itens não são apagados" in await pg.inner_text("#listasExtra"), "Apagar pergunta antes")
            await pg.click('#listasExtra [data-lapagar]')
            await pg.wait_for_timeout(400)
            c = app.config_salva()
            check(await barra(pg) == ["Nenhuma 3", "Compra mensal 1", "+ Nova"] and len(await nomes(pg)) == 3 and [x["nome"] for x in c["listas"]] == ["Compra mensal"]
                  and c["roteiro"]["listas"] == [], f"apagada: os itens dela vão para Nenhuma, aberta, para passar a outra lista ({await barra(pg)})")
            check(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "nada passa da largura")
            await b.close()
            b, pg = await pagina(p, 320, 700, escuro=False)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.click('#listasBar [data-lnova]')
            await pg.fill("#listaNome", "Compra mensal do mercado")
            await pg.click('#listaForm [data-lic="🧴"]')
            check(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "320 px: os ícones cabem")
            await shot(pg, "listas-nova-320")
            await pg.click('#listaForm button[type="submit"]')
            await pg.wait_for_timeout(400)
            check("🧴 Compra mensal do mercado 0" in await barra(pg), f"criada com o ícone ({await barra(pg)})")
            await abre(pg, "Nenhuma")
            await pg.click("#listasExtra [data-lmover]")
            await pg.wait_for_timeout(300)
            check(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "320 px: a barra rola de lado, nada passa da largura")
            await shot(pg, "listas-320")
            # desligar esconde tudo, sem apagar
            await abrir_mais(pg, "opcoes")
            await pg.locator('label[for="opListas"]').click()
            await pg.wait_for_timeout(300)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(300)
            check(await pg.locator("#listasWrap").is_hidden() and len(await nomes(pg)) == 4 and len(app.config_salva()["listas"]) == 2,
                  "desligadas: a lista toda, e as listas continuam guardadas")
            await b.close()
    resumo()


asyncio.run(main())
