# EconomIA 0.19.0: Mais › Aparência (tema e cor do app, guardados no aparelho), Mais › Opções (busca direta com as lojas do
# CEP, folhetos, itens sem preço, encartes), Usar IA (desligada some tudo o que gasta IA, para todos os aparelhos),
# Sensores no Home Assistant (o sensor aparece e some no HA falso) e a Lista do Home Assistant (escolher a lista, o item
# do HA entra na Minha lista).
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, HAFalso, check, espera, pagina, resumo


async def mais(pg, aba):
    await pg.click('.tabbar [data-view="mais"]')
    await pg.click("#aba-" + aba)
    await pg.wait_for_timeout(300)


async def fundo(pg):
    return await pg.evaluate("getComputedStyle(document.body).backgroundColor")


async def main():
    ha = HAFalso()
    ha.lista("todo.compras", "Compras")
    ha.lista("todo.casa", "Afazeres")
    ha.item("todo.compras", "Pão francês")
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados"], "lista": [{"produto": "Leite integral"}]}
    with App(cfg, buscar=False, ha=ha) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            # ----- Aparência -----
            await mais(pg, "aparencia")
            temas = [t.strip() for t in await pg.locator("#tema button").all_inner_texts()]
            check(temas == ["Automático", "Claro", "Escuro"] and await pg.get_attribute('#tema [data-v="escuro"]', "aria-checked") == "true", "temas, Escuro de começo")
            escuro = await fundo(pg)
            await pg.click('#tema [data-v="claro"]')
            check(await pg.get_attribute("html", "data-theme") == "light" and await fundo(pg) != escuro, f"Claro muda as cores ({escuro} → {await fundo(pg)})")
            check(len(await pg.locator("#cores button").all()) == 10 and await pg.get_attribute('#cores [data-v="verde"]', "aria-checked") == "true", "10 cores, verde de começo")
            acento = await pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent')")
            await pg.click('#cores [data-v="roxo"]')
            check(await pg.get_attribute("html", "data-cor") == "roxo" and await pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent')") != acento,
                  "Roxo troca a cor de destaque")
            await pg.locator("#mp-aparencia").screenshot(path=SHOTS + "/ecap-claro-roxo.png")
            await pg.reload()
            await pg.wait_for_timeout(1000)
            check(await pg.get_attribute("html", "data-theme") == "light" and await pg.get_attribute("html", "data-cor") == "roxo", "o tema e a cor ficam depois de recarregar")
            check("tema" not in app.config_salva() and "cor" not in app.config_salva(), "e ficam só neste aparelho")
            await pg.click('#tema [data-v="auto"]')
            check(await pg.get_attribute("html", "data-theme") is None, "Automático segue o aparelho")
            await pg.click('#tema [data-v="escuro"]')
            await pg.click('#cores [data-v="verde"]')
            check(await pg.get_attribute("html", "data-cor") is None, "verde é a cor padrão")
            # ----- Opções -----
            await mais(pg, "opcoes")
            await espera(pg, "() => /Giassi/.test(document.getElementById('opDiretasSt').textContent)")
            check(await pg.text_content("#opDiretasSt") == "Giassi: atende o seu CEP · Angeloni: atende o seu CEP.", f"as lojas diretas do CEP ({await pg.text_content('#opDiretasSt')})")
            for sw in ("#opDiretas", "#opFolhetos", "#opItens", "#opEncartes"):
                check(await pg.is_checked(sw), f"{sw} ligado de começo")
                await pg.click(sw)
                await pg.wait_for_timeout(500)
            op = app.config_salva()["opcoes"]
            check(op == {"itens_sem_preco": False, "encartes_auto": False, "lojas_diretas": False, "folhetos": False}, f"as opções desligadas ficam salvas ({op})")
            await pg.locator("#mp-opcoes").screenshot(path=SHOTS + "/ecap-opcoes.png")
            # ----- Usar IA -----
            await mais(pg, "integracoes")
            check(await pg.is_checked("#usarIA") and await pg.text_content("#usarIATxt") == "Ligado.", "IA ligada")
            await pg.click("#usarIA")
            await pg.wait_for_timeout(600)
            check(app.config_salva()["usar_ia"] is False, "desligar fica salvo")
            check(await pg.evaluate("document.documentElement.classList.contains('sem-ia')") and await pg.locator("#iaDet").is_hidden(), "sem IA: some a escolha da IA")
            check(await pg.text_content("#usarIATxt") == "Desligado: a busca usa só o que não gasta IA. Vale para todos os aparelhos.", "explica o que muda")
            check(await pg.locator('#v-mais section[aria-labelledby="h-uso"]').is_hidden(), "Uso da IA some")
            await mais(pg, "opcoes")
            check(await pg.locator("#opFolhetos").is_hidden() and await pg.locator("#opDiretas").is_visible(), "Opções: só a busca direta, que não gasta IA")
            await pg.click('.tabbar [data-view="lista"]')
            check(await pg.locator("#fotoBtn").is_hidden() and await pg.locator("#textoBtn").is_hidden(), "Minha lista: sem Ler com IA")
            await pg.locator("#v-lista").screenshot(path=SHOTS + "/ecap-sem-ia.png")
            await mais(pg, "integracoes")
            await pg.click("#usarIA")
            await pg.wait_for_timeout(600)
            check(app.config_salva()["usar_ia"] is True and not await pg.evaluate("document.documentElement.classList.contains('sem-ia')"), "ligar de novo")
            # ----- Sensores no Home Assistant -----
            await pg.click("#sensores")
            await espera(pg, "() => /Ligado/.test(document.getElementById('sensoresTxt').textContent)")
            check(await pg.text_content("#sensoresTxt") == "Ligado: sensor.economia_ia_hoje.", "sensores ligados")
            for _ in range(100):
                if "sensor.economia_ia_hoje" in ha.estados:
                    break
                await asyncio.sleep(0.05)
            check(ha.estados.get("sensor.economia_ia_hoje", {}).get("attributes", {}).get("friendly_name") == "EconomIA: chamadas de IA hoje", "o sensor aparece no Home Assistant")
            await pg.click("#sensores")
            for _ in range(100):
                if "sensor.economia_ia_hoje" not in ha.estados:
                    break
                await asyncio.sleep(0.05)
            check("sensor.economia_ia_hoje" not in ha.estados and app.config_salva()["sensores"] is False, "desligado: o sensor some do Home Assistant")
            # ----- Lista do Home Assistant -----
            opts = [t.strip() for t in await pg.locator("#syncEnt option").all_inner_texts()]
            check(opts == ["Não sincronizar", "Afazeres", "Compras"], f"as listas do Home Assistant ({opts})")
            check(await pg.is_disabled("#syncNovos"), "sem lista: as opções ficam desligadas")
            await pg.select_option("#syncEnt", "todo.compras")
            await espera(pg, "() => document.getElementById('toast').textContent === 'Sua lista foi atualizada pelo Home Assistant'", 15000)
            sync = app.config_salva()["sync"]
            check(sync["ativo"] and sync["entidade"] == "todo.compras", "sincronizando com Compras")
            check("Conferida" in await pg.text_content("#syncInfo"), "mostra quando conferiu")
            await pg.locator('#v-mais section[aria-labelledby="h-ha"]').screenshot(path=SHOTS + "/ecap-lista-ha.png")
            await pg.click("#syncNovos")
            await pg.wait_for_timeout(500)
            check(app.config_salva()["sync"]["enviar_novos"] is False, "Itens novos daqui vão para lá: desligado")
            await pg.click('.tabbar [data-view="lista"]')
            pao = pg.locator("#wish > li.item", has_text="Pão francês")
            check(await pao.count() == 1 and "VEIO DO HOME ASSISTANT" in (await pao.inner_text()).upper(), "o item da lista do HA entrou na Minha lista")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
