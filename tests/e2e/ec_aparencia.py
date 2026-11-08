# EconomIA 0.19.0: Mais › Aparência (tema e cor do app, guardados no aparelho; 1.4.0: a Cor do dia, ligada de começo, e a
# troca da cor na virada do dia com o app aberto), Mais › Opções (busca direta com as lojas do
# CEP, folhetos, itens sem preço, encartes), Usar IA (desligada some tudo o que gasta IA, para todos os aparelhos),
# Sensores no Home Assistant (o sensor aparece e some no HA falso) e a Lista do Home Assistant (escolher a lista, o item
# do HA entra na Minha lista).
import asyncio
import datetime

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, HAFalso, abrir_mais, check, espera, pagina, resumo


async def mais(pg, aba):
    await abrir_mais(pg, aba)
    await pg.wait_for_timeout(300)


# a Cor do dia, como na página: as cores sem o cinza, uma por dia pela data local
DIA_JS = """() => { const L = ['vermelho','coral','rosa','magenta','laranja','amarelo','roxo','azul','verde'], d = new Date(),
  n = Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 864e5); return L[((n % 9) + 9) % 9]; }"""
MARCADA = "() => [...document.querySelectorAll('#cores [aria-checked=\"true\"]')].map(b => b.dataset.v)"


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
            hoje = await pg.evaluate(DIA_JS)
            dia = None if hoje == "verde" else hoje
            check(await pg.is_checked("#corDia"), "Cor do dia ligada de começo")
            check(len(await pg.locator("#cores button").all()) == 10 and await pg.evaluate(MARCADA) == [hoje], f"10 cores, a do dia marcada ({hoje})")
            check(await pg.get_attribute("html", "data-cor") == dia, f"a cor do dia vale ({hoje})")
            outra = "roxo" if hoje != "roxo" else "azul"
            acento = await pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent')")
            await pg.click(f'#cores [data-v="{outra}"]')
            check(await pg.get_attribute("html", "data-cor") == outra and await pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent')") != acento,
                  f"{outra} troca a cor de destaque")
            check(not await pg.is_checked("#corDia"), "escolher uma cor desliga a Cor do dia")
            await pg.locator("#mp-aparencia").screenshot(path=SHOTS + "/ecap-claro-roxo.png")
            await pg.reload()
            await pg.wait_for_timeout(1000)
            check(await pg.get_attribute("html", "data-theme") == "light" and await pg.get_attribute("html", "data-cor") == outra, "o tema e a cor ficam depois de recarregar")
            check(not await pg.is_checked("#corDia") and await pg.evaluate(MARCADA) == [outra], "a Cor do dia continua desligada")
            check("tema" not in app.config_salva() and "cor" not in app.config_salva() and "corDia" not in app.config_salva(), "e ficam só neste aparelho")
            await pg.click("#corDia")
            check(await pg.get_attribute("html", "data-cor") == dia and await pg.evaluate(MARCADA) == [hoje], "ligar a Cor do dia volta para a cor de hoje")
            await pg.reload()
            await pg.wait_for_timeout(1000)
            check(await pg.is_checked("#corDia") and await pg.get_attribute("html", "data-cor") == dia, "ligada fica depois de recarregar")
            await pg.click("#corDia")
            check(await pg.get_attribute("html", "data-cor") == outra and await pg.evaluate(MARCADA) == [outra], "desligar volta para a última cor escolhida")
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
            # ----- Cor do dia na virada do dia, com o app aberto (relógio de mentira: 8/11 é rosa, 9/11 é magenta) -----
            ctx = await b.new_context(viewport={"width": 412, "height": 892}, device_scale_factor=2, color_scheme="dark", has_touch=True,
                                      timezone_id="America/Sao_Paulo")
            p2 = await ctx.new_page()
            p2.erros = []
            p2.on("pageerror", lambda e: p2.erros.append(str(e)))
            await p2.clock.install(time=datetime.datetime(2026, 11, 8, 23, 58, 30, tzinfo=datetime.timezone(datetime.timedelta(hours=-3))))
            await p2.goto(app.url)
            await p2.wait_for_timeout(1200)
            check(await p2.get_attribute("html", "data-cor") == "rosa", "8/11: rosa")
            await mais(p2, "aparencia")
            check(await p2.evaluate(MARCADA) == ["rosa"], "a rosa marcada")
            await p2.locator('#mp-aparencia section[aria-labelledby="h-cor"]').screenshot(path=SHOTS + "/ecap-cor-do-dia.png")
            await p2.clock.fast_forward("03:00")
            await espera(p2, "() => document.documentElement.getAttribute('data-cor') === 'magenta'", 5000)
            check(await p2.evaluate(MARCADA) == ["magenta"], "passou da meia-noite: magenta, sem recarregar")
            check(not p2.erros, f"sem erros na página {p2.erros}")
            await b.close()


asyncio.run(main())
resumo()
