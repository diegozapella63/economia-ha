# EconomIA 0.19.0: Mais › Aparência (1.9.0: o tema no aparelho, de começo Sistema, e a cor do app da casa toda, na paleta da família; 1.4.0: a Cor do dia, ligada de começo, e a
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


# a Cor do dia, a mesma em todos os apps da família: as 11 cores da paleta sem o Grafite, uma por dia pela data local
DIA_JS = """() => { const L = ['vermelho','coral','laranja','ouro','verde','menta','turquesa','azul','indigo','lilas','rosa'], d = new Date(),
  n = Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 864e5); return L[((n % 11) + 11) % 11]; }"""
PALETA = ["Vermelho", "Coral", "Laranja", "Ouro", "Verde", "Menta", "Turquesa", "Azul", "Índigo", "Lilás", "Rosa", "Grafite"]
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
            # este aparelho já tinha uma cor (de antes da 1.9.0, só nele): Magenta, sem a Cor do dia
            await pg.add_init_script("if (!sessionStorage.getItem('ec-t')) { localStorage.setItem('ofertas-bairro:ui', JSON.stringify({cor: 'magenta', corDia: false})); sessionStorage.setItem('ec-t', '1'); }")
            await pg.goto(app.url)
            await pg.wait_for_timeout(1500)
            # ----- Aparência (1.9.0: o tema no aparelho, começando em Sistema; a cor do app da casa toda; a paleta da família) -----
            check(app.config_salva().get("cor") == "rosa" and app.config_salva().get("cor_dia") is False,
                  f"na primeira vez, a casa adota a cor deste aparelho (Magenta de antes vira Rosa) ({app.config_salva().get('cor')}, {app.config_salva().get('cor_dia')})")
            check(await pg.get_attribute("html", "data-cor") == "rosa", "e pinta com ela")
            await mais(pg, "aparencia")
            temas = [t.strip() for t in await pg.locator("#tema button").all_inner_texts()]
            check(temas == ["Sistema", "Claro", "Escuro"] and await pg.get_attribute('#tema [data-v="auto"]', "aria-checked") == "true", "temas, Sistema de começo")
            check(await pg.get_attribute("html", "data-theme") is None, "Sistema segue o aparelho")
            nomes = [t.strip() for t in await pg.locator("#cores button").all_inner_texts()]
            check(nomes == PALETA, f"as 12 cores da família, na ordem ({nomes})")
            await pg.click("#corDia")
            await pg.wait_for_timeout(500)
            hoje = await pg.evaluate(DIA_JS)
            check(await pg.is_checked("#corDia") and app.config_salva().get("cor_dia") is True, "Cor do dia ligada, para a casa toda")
            check(await pg.evaluate(MARCADA) == [hoje] and await pg.get_attribute("html", "data-cor") == hoje, f"a cor do dia marcada e valendo ({hoje})")
            await pg.click('#tema [data-v="escuro"]')
            escuro = await fundo(pg)
            await pg.click('#tema [data-v="claro"]')
            check(await pg.get_attribute("html", "data-theme") == "light" and await fundo(pg) != escuro, f"Claro muda as cores ({escuro} → {await fundo(pg)})")
            outra = "lilas" if hoje != "lilas" else "azul"
            acento = await pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent')")
            await pg.click(f'#cores [data-v="{outra}"]')
            await pg.wait_for_timeout(500)
            check(await pg.get_attribute("html", "data-cor") == outra and await pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent')") != acento,
                  f"{outra} troca a cor de destaque")
            check(not await pg.is_checked("#corDia"), "escolher uma cor desliga a Cor do dia")
            check(app.config_salva().get("cor") == outra and app.config_salva().get("cor_dia") is False and "tema" not in app.config_salva(), "a cor vale para a casa toda; o tema, não")
            await pg.locator("#mp-aparencia").screenshot(path=SHOTS + "/ecap-claro-lilas.png")
            await pg.reload()
            await pg.wait_for_timeout(1000)
            check(await pg.get_attribute("html", "data-theme") == "light" and await pg.get_attribute("html", "data-cor") == outra, "o tema e a cor ficam depois de recarregar")
            check(not await pg.is_checked("#corDia") and await pg.evaluate(MARCADA) == [outra], "a Cor do dia continua desligada")
            # outro aparelho: a cor da casa, o tema dele (Sistema)
            b2, p3 = await pagina(p)
            await p3.goto(app.url)
            await p3.wait_for_timeout(1200)
            check(await p3.get_attribute("html", "data-cor") == outra and await p3.get_attribute("html", "data-theme") is None, "em outro aparelho, a cor da casa e o tema Sistema")
            await b2.close()
            # uma cor de antes no config.json vira a da paleta
            st = app.api("GET", "/api/estado")
            app.api("PUT", "/api/config", dict(st["config"], cor="roxo", cor_dia=False))
            await pg.reload()
            await pg.wait_for_timeout(1000)
            check(await pg.get_attribute("html", "data-cor") == "lilas", "Roxo, de antes, é Lilás")
            await pg.click(f'#cores [data-v="{outra}"]')
            await pg.wait_for_timeout(400)
            await pg.click("#corDia")
            check(await pg.get_attribute("html", "data-cor") == hoje and await pg.evaluate(MARCADA) == [hoje], "ligar a Cor do dia volta para a cor de hoje")
            await pg.wait_for_timeout(500)
            await pg.reload()
            await pg.wait_for_timeout(1000)
            check(await pg.is_checked("#corDia") and await pg.get_attribute("html", "data-cor") == hoje, "ligada fica depois de recarregar")
            await pg.click("#corDia")
            check(await pg.get_attribute("html", "data-cor") == outra and await pg.evaluate(MARCADA) == [outra], "desligar volta para a última cor escolhida")
            await pg.click('#tema [data-v="auto"]')
            check(await pg.get_attribute("html", "data-theme") is None, "Sistema segue o aparelho")
            await pg.click('#tema [data-v="escuro"]')
            await pg.click('#cores [data-v="verde"]')
            check(await pg.get_attribute("html", "data-cor") == "verde", "Verde")
            await pg.click("#corDia")  # de volta à Cor do dia, para a virada do dia, embaixo
            await pg.wait_for_timeout(500)
            # ----- Opções -----
            await mais(pg, "opcoes")
            await espera(pg, "() => /preço direto/.test(document.getElementById('opDiretasSt').textContent)")
            check(await pg.text_content("#opDiretasSt") == "Todas as 2 lojas com preço direto.", f"as lojas diretas do CEP ({await pg.text_content('#opDiretasSt')})")
            # 1.35.0: cada loja numa linha, recolhidas em Lojas (2)
            det = pg.locator("#opDiretasLojas")
            check(await det.is_visible() and not await det.evaluate("d => d.open") and (await det.locator("summary").inner_text()).strip() == "Lojas (2)",
                  "as lojas ficam recolhidas em Lojas (2)")
            await det.locator("summary").click()
            linhas = [x.strip() for x in await det.locator("li").all_inner_texts()]
            check(linhas == ["Giassi: atende o seu CEP", "Angeloni: atende o seu CEP"], f"abertas, uma por linha ({linhas})")
            for sw in ("#opDiretas", "#opFolhetos", "#opItens", "#opEncartes"):
                check(await pg.is_checked(sw), f"{sw} ligado de começo")
                await pg.click(sw)
                await pg.wait_for_timeout(500)
            op = app.config_salva()["opcoes"]
            check(op == {"itens_sem_preco": False, "encartes_auto": False, "lojas_diretas": False, "folhetos": False, "listas": False},
                  f"as opções desligadas ficam salvas; as Listas (1.15.0) já vêm desligadas ({op})")
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
            check(await pg.text_content("#sensoresTxt") == "Ligado: sensor.economia_ia_hoje, sensor.economia_melhor_loja e binary_sensor.economia_oferta.", "sensores ligados")
            for _ in range(100):
                if "sensor.economia_ia_hoje" in ha.estados:
                    break
                await asyncio.sleep(0.05)
            check(ha.estados.get("sensor.economia_ia_hoje", {}).get("attributes", {}).get("friendly_name") == "EconomIA: chamadas de IA hoje", "o sensor aparece no Home Assistant")
            for _ in range(100):
                if "binary_sensor.economia_oferta" in ha.estados:
                    break
                await asyncio.sleep(0.05)
            check("sensor.economia_melhor_loja" in ha.estados and "binary_sensor.economia_oferta" in ha.estados, "1.21.0: a melhor loja e a oferta da lista também")
            await pg.click("#sensores")
            for _ in range(100):
                if not any(e in ha.estados for e in ("sensor.economia_ia_hoje", "sensor.economia_melhor_loja", "binary_sensor.economia_oferta")):
                    break
                await asyncio.sleep(0.05)
            check(not any(e in ha.estados for e in ("sensor.economia_ia_hoje", "sensor.economia_melhor_loja", "binary_sensor.economia_oferta"))
                  and app.config_salva()["sensores"] is False, "desligado: os sensores somem do Home Assistant")
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
            # ----- Cor do dia na virada do dia, com o app aberto (relógio de mentira: 8/11 é índigo, 9/11 é lilás) -----
            ctx = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, color_scheme="dark", has_touch=True,
                                      timezone_id="America/Sao_Paulo")
            p2 = await ctx.new_page()
            p2.erros = []
            p2.on("pageerror", lambda e: p2.erros.append(str(e)))
            await p2.clock.install(time=datetime.datetime(2026, 11, 8, 23, 58, 30, tzinfo=datetime.timezone(datetime.timedelta(hours=-3))))
            await p2.goto(app.url)
            await p2.wait_for_timeout(1200)
            check(await p2.get_attribute("html", "data-cor") == "indigo", "8/11: índigo")
            await mais(p2, "aparencia")
            check(await p2.evaluate(MARCADA) == ["indigo"], "a índigo marcada")
            await p2.locator('#mp-aparencia section[aria-labelledby="h-cor"]').screenshot(path=SHOTS + "/ecap-cor-do-dia.png")
            await p2.clock.fast_forward("03:00")
            await espera(p2, "() => document.documentElement.getAttribute('data-cor') === 'lilas'", 5000)
            check(await p2.evaluate(MARCADA) == ["lilas"], "passou da meia-noite: lilás, sem recarregar")
            check(not p2.erros, f"sem erros na página {p2.erros}")
            await b.close()


asyncio.run(main())
resumo()
