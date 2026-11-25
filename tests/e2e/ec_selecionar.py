# EconomIA 1.54.0: Selecionar na Minha lista, como nos outros apps da família. O botão Selecionar (ou segurar o dedo num
# item) troca a lista por uma linha por item, com a marca; Todos/Nenhum; o X e o Voltar do celular saem. A barra de baixo:
# Comprei hoje (todos de uma vez) e Alterar (onde comprar e, com as listas prontas, para qual lista; Manter de início) e,
# no Alterar, Remover (vão para o histórico) ou Tirar desta lista. Depois, o aviso com Desfazer. Itens e lojas inventados.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, App, categoria, check, espera, pagina, resumo, shot

OFERTAS = {"versao": 2, "gerado_em": "2026-11-01T10:00:00-03:00",
           "categorias": [categoria("mercados", [("merc-giassi", "Giassi", 1.0), ("merc-fort", "Fort", 2.0)]),
                          categoria("farmacias", [("farm-sc", "Farmácia Exemplo", 1.5)])],
           "lista": [{"produto": "Café torrado em grãos", "precos": {"merc-giassi": 81.9, "merc-fort": 95.8}},
                     {"produto": "Arroz 5 kg", "precos": {"merc-giassi": 24.9, "merc-fort": 22.9}},
                     {"produto": "Pão de forma", "precos": {"merc-giassi": 9.9, "merc-fort": 8.5}}]}

FORA = """() => { const W = innerWidth, ruins = [];
  for (const e of document.querySelectorAll('#wish *, #selBar *')) { const r = e.getBoundingClientRect();
    if (r.width && !e.closest('[hidden]') && (r.right > W + 1 || r.left < -1)) ruins.push(e.className || e.tagName); }
  if (document.documentElement.scrollWidth > W) ruins.push('página ' + document.documentElement.scrollWidth);
  return ruins.slice(0, 4); }"""


def limpo(s):
    return " ".join(s.replace("\xa0", " ").split())


def item(app, nome):
    return next((i for i in app.config_salva()["lista"] if i["produto"] == nome), None)


async def marcar(pg, nome):
    await pg.locator("#wish > li.sel", has_text=nome).locator("button").click()
    await pg.wait_for_timeout(120)


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados", "farmacias"],
           "lista": [{"produto": "Café torrado em grãos"}, {"produto": "Arroz 5 kg"}, {"produto": "Pão de forma"}]}
    with App(cfg, buscar=False, antes=lambda S: S.gravar_json(S.OFERTAS, OFERTAS)) as app:
        async with async_playwright() as p:
            for largura, escuro in ((390, False), (320, True)):
                tag = f"{largura} px {'escuro' if escuro else 'claro'}"
                b, pg = await pagina(p, largura=largura, altura=844, escuro=escuro)
                await pg.goto(app.url)
                await espera(pg, "() => document.querySelectorAll('#wish > li.item').length >= 2")
                check(await pg.locator("#selBtn").is_visible(), f"{tag}: o Selecionar na barra da lista")
                await pg.click("#selBtn")
                await espera(pg, "() => document.documentElement.classList.contains('selecionando')")
                linhas = pg.locator("#wish > li.sel")
                check(await linhas.count() == len(app.config_salva()["lista"]), f"{tag}: uma linha por item")
                check(limpo(await pg.inner_text("#selN")) == "Toque nos itens", f"{tag}: nada marcado ainda")
                check(await pg.locator("#selComprei").is_disabled() and await pg.locator("#selAlterar").is_disabled(), f"{tag}: sem marcar, os botões ficam inativos")
                check(await pg.evaluate("history.state && history.state.sell") is True, f"{tag}: a seleção é uma entrada do histórico")
                # Todos e Nenhum
                await pg.click("#selTodos")
                n = await linhas.count()
                check(limpo(await pg.inner_text("#selN")) == f"{n} selecionados" and limpo(await pg.inner_text("#selTodos")) == "Nenhum", f"{tag}: Todos marca todos")
                await pg.click("#selTodos")
                check(await pg.locator("#wish > li.sel.on").count() == 0, f"{tag}: Nenhum desmarca")
                ruins = await pg.evaluate(FORA)
                check(not ruins, f"{tag}: nada para fora da tela {ruins}")
                if largura == 390:
                    await marcar(pg, "Café torrado")
                    await marcar(pg, "Arroz 5 kg")
                    check(limpo(await pg.inner_text("#selN")) == "2 selecionados", "dois marcados")
                    check(limpo(await pg.inner_text("#selAlterar")) == "Alterar 2 itens", "o Alterar diz quantos")
                    await shot(pg, "selecionar-390")
                    # Comprei hoje nos dois
                    await pg.click("#selComprei")
                    await espera(pg, "() => !document.documentElement.classList.contains('selecionando')")
                    await pg.wait_for_timeout(500)
                    check("comprados hoje" in limpo(await pg.inner_text("#toast")), "o aviso diz quantos foram comprados")
                    check(await pg.locator("#toast #selDesfazer").is_visible(), "com o Desfazer")
                    cafe, arroz, pao = item(app, "Café torrado em grãos"), item(app, "Arroz 5 kg"), item(app, "Pão de forma")
                    check(len(cafe.get("compras") or []) == 1 and len(arroz.get("compras") or []) == 1 and not pao.get("compras"), "a compra de hoje nos dois, não no terceiro")
                    check(await pg.evaluate("!(history.state && history.state.sell)"), "saiu da entrada da seleção")
                    # Desfazer
                    await pg.click("#toast #selDesfazer")
                    await pg.wait_for_timeout(500)
                    check(not (item(app, "Café torrado em grãos").get("compras") or []), "o Desfazer tira a compra")
                    # Alterar: onde comprar
                    await pg.click("#selBtn")
                    await marcar(pg, "Pão de forma")
                    await pg.click("#selAlterar")
                    chips = [limpo(x) for x in await pg.locator("#selAlt [data-selcampo='setor']").all_inner_texts()]
                    check(chips == ["Manter", "Automático", "Mercado", "Farmácia", "Pet shop"], f"onde comprar, com Manter {chips}")
                    check(await pg.locator("#selAlt [data-selcampo='lista']").count() == 0, "sem as listas prontas, nada de lista")
                    check(await pg.locator("#selAlt [data-v='']").first.get_attribute("aria-pressed") == "true", "começa em Manter")
                    await shot(pg, "selecionar-alterar-390")
                    await pg.click("#selAlt [data-selcampo='setor'][data-v='farmacias']")
                    await pg.click("#selSalvar")
                    await pg.wait_for_timeout(500)
                    check(item(app, "Pão de forma").get("setor") == "farmacias", "o Pão de forma vai para a farmácia")
                    check(item(app, "Arroz 5 kg").get("setor") is None, "o resto fica como estava")
                    check("1 item alterado" in limpo(await pg.inner_text("#toast")), "o aviso do alterado")
                    # Remover vai para o histórico, o Desfazer volta
                    await pg.click("#selBtn")
                    await marcar(pg, "Arroz 5 kg")
                    await pg.click("#selAlterar")
                    check(limpo(await pg.inner_text("#selRemover")) == "Remover", "no Alterar, o Remover")
                    await pg.click("#selRemover")
                    await pg.wait_for_timeout(500)
                    salvo = app.config_salva()
                    check(item(app, "Arroz 5 kg") is None and any(h["produto"] == "Arroz 5 kg" for h in salvo.get("historico") or []), "o Arroz sai e fica no histórico")
                    await pg.click("#toast #selDesfazer")
                    await pg.wait_for_timeout(500)
                    check(item(app, "Arroz 5 kg") is not None, "o Desfazer devolve o Arroz")
                    # segurar o dedo começa com o item marcado; o Voltar do celular sai
                    await pg.locator("#wish > li", has_text="Café torrado").first.dispatch_event("contextmenu")
                    await espera(pg, "() => document.documentElement.classList.contains('selecionando')")
                    check(limpo(await pg.inner_text("#selN")) == "1 selecionado", "segurar o dedo marca o item")
                    await pg.go_back()
                    await espera(pg, "() => !document.documentElement.classList.contains('selecionando')")
                    check(await pg.locator("#selBar").is_hidden(), "o Voltar do celular sai da seleção")
                    # o X também
                    await pg.click("#selBtn")
                    await pg.click("#selFim")
                    await espera(pg, "() => !document.documentElement.classList.contains('selecionando')")
                    check(await pg.evaluate("!(history.state && history.state.sell)"), "o X sai e tira a entrada")
                else:
                    await pg.click("#selFim")
                await b.close()

            # com as listas prontas: mover para outra lista
            c = app.config_salva()
            c.setdefault("opcoes", {})["listas"] = True
            c["listas"] = [{"id": "semanal", "nome": "Semanal"}, {"id": "mensal", "nome": "Mensal"}]
            for it in c["lista"]:
                it["listas"] = ["semanal"]
            app.api("PUT", "api/config", c)
            b, pg = await pagina(p, largura=390, altura=844)
            await pg.goto(app.url)
            await espera(pg, "() => document.querySelectorAll('#listasBar .pick').length >= 2")
            await pg.locator("#listasBar .pick", has_text="Semanal").click()
            await espera(pg, "() => document.querySelectorAll('#wish > li.item').length === 3")
            await pg.click("#selBtn")
            await marcar(pg, "Café torrado")
            await pg.click("#selAlterar")
            listas = [limpo(x) for x in await pg.locator("#selAlt [data-selcampo='lista']").all_inner_texts()]
            check(listas == ["Manter", "Mensal"], f"Mover para a lista: Manter e as outras {listas}")
            check(limpo(await pg.inner_text("#selRemover")) == "Tirar desta lista", "numa lista pronta, Tirar desta lista")
            await pg.click("#selAlt [data-selcampo='lista'][data-v='mensal']")
            await pg.click("#selSalvar")
            await pg.wait_for_timeout(500)
            check(item(app, "Café torrado em grãos").get("listas") == ["mensal"], "o Café vai para a Mensal")
            check(await pg.locator("#wish > li.item").count() == 2, "e sai da Semanal")
            # Comprei hoje numa lista pronta marca como comprado nela
            await pg.click("#selBtn")
            await marcar(pg, "Arroz 5 kg")
            await pg.click("#selComprei")
            await pg.wait_for_timeout(500)
            sem = next(l for l in app.config_salva()["listas"] if l["id"] == "semanal")
            check("arroz 5 kg" in (sem.get("comprados") or []), "o Arroz fica em Comprados da Semanal")
            await b.close()
    resumo()


asyncio.run(main())
