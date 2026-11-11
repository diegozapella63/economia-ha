# EconomIA 0.18.0–0.19.0: Minha lista com os preços da busca de verdade (lojas falsas): ícones, mais barato, outras lojas,
# Similares (ligar, escolher um similar, Roteiro, desligar; 1.28.0: num grupo recolhido, Buscar similares no pé do cartão e os
# achados guardados para a próxima vez), Escolher esse e Desfazer, "ou" no item, adicionar,
# "Quis dizer…?" ao adicionar e no item sem preço, Comprei hoje, remover → Histórico → voltar, Limpar lista.
import asyncio
import copy
import json
import os

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, check, ean13, pagina, prod, resumo, shot
from apoio import NOMES_VOCAB

AVES, BOV = "Açougue/Aves", "Açougue/Bovinos"


def prepara(lojas):
    g = [prod("Coxinha da Asa de Frango Resfriada Kg", 21.90, AVES, "kg", 1, ean13("789000000001")),
         prod("Asa de Frango Congelada Kg", 15.90, AVES, "kg", 1), prod("Asinha de Frango Temperada Kg", 18.50, AVES, "kg", 1),
         prod("Sobrecoxa de Frango Resfriada Kg", 12.48, AVES, "kg", 1), prod("Frango Inteiro Congelado Kg", 10.99, AVES, "kg", 1),
         prod("Filé de Peito de Frango Kg", 26.90, AVES, "kg", 1),
         prod("Carne Moída Bovina de Primeira Kg", 39.90, BOV, "kg", 1), prod("Acém Moído Bovino Kg", 32.90, BOV, "kg", 1),
         prod("Almôndega de Carne Moída Bovina Congelada 500g", 15.90, "Congelados/Pratos Prontos")]
    lojas.catalogo["giassi"] = g
    lojas.catalogo["angeloni"] = [dict(copy.deepcopy(p), categories=[], link=p["link"].replace("/p", "-ang/p"))
                                  for p in g if "Moída Bovina de Primeira" in p["productName"]]
    lojas.catalogo["angeloni"][0]["items"][0]["sellers"][0]["commertialOffer"]["Price"] = 42.90


def antes(S):
    S.aprende_nomes(NOMES_VOCAB)


async def item(pg, nome):
    return pg.locator("#wish > li.item", has_text=nome).first


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados", "farmacias", "petshops", "online"], "lista": [
        {"produto": "Coxinha da asa", "similares": True, "compras": ["2026-10-05", "2026-10-19"]},
        {"produto": "Carne moída bovina de primeira", "compras": []},
        {"produto": "Coxinha da asa ou asinha", "compras": []},
        {"produto": "Detergemte Ypê", "compras": []}]}
    with App(cfg, preparar=prepara, antes=antes) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1500)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(500)
            check(await pg.locator("#wish > li.item").count() == 4, "4 itens na lista")
            cox = await item(pg, "Coxinha da asa")
            check((await cox.locator(".i-ic").inner_text()).strip() == "🍗", "ícone do frango")
            check((await (await item(pg, "Carne moída")).locator(".i-ic").inner_text()).strip() == "🥩", "ícone da carne")
            best = (await cox.locator(".i-best").inner_text()).replace("\xa0", " ")
            check("R$ 21,90" in best and "Giassi" in best, f"mais barato da coxinha ({best[:60]})")
            # a almôndega (outra seção) não virou o preço da carne; Angeloni aparece como outra opção
            carne = await item(pg, "Carne moída")
            txt = (await carne.inner_text()).replace("\xa0", " ")
            check("R$ 39,90" in txt and "R$ 15,90" not in txt, "carne moída: preço da carne, não da almôndega")
            check("R$ 42,90" in txt, "Angeloni nas outras lojas")
            check("economia de R$ 3,00" in txt, "economia em relação à segunda loja")
            # "ou": vale o mais em conta dos dois lados
            ou = (await (await item(pg, "ou asinha")).locator(".i-best").inner_text()).replace("\xa0", " ")
            check("R$ 18,50" in ou, f"coxinha ou asinha: a asinha ganha ({ou[:40]})")
            check('coxinha da asa ou asinha' in (await pg.text_content("#wishDica")).lower(), "a dica do 'ou' aparece em cima da lista")
            await shot(pg, "ecl-lista", full_page=True)

            # ----- Similares (1.28.0: tudo o que a busca achou na seção, num grupo recolhido como o Comparar tamanhos) -----
            sim = cox.locator("details.i-det", has_text="Similares (")
            check(await sim.count() == 1 and await sim.get_attribute("open") is None and (await sim.locator("summary").inner_text()).strip() == "Similares (5)",
                  f"similares ligados: grupo recolhido ({await sim.locator('summary').inner_text()})")
            await sim.locator("summary").click()
            await pg.wait_for_timeout(200)
            nomes = [t.split("\n")[0] for t in await sim.locator(".sim-list li b").all_inner_texts()]
            check(nomes == ["Frango Inteiro Congelado Kg", "Sobrecoxa de Frango Resfriada Kg", "Asa de Frango Congelada Kg", "Asinha de Frango Temperada Kg",
                            "Filé de Peito de Frango Kg"], f"todos os da seção, por kg ({nomes})")
            check("4 saem mais em conta que o item." in await sim.inner_text() and await sim.locator(".sim-list li.conta").count() == 4,
                  "os mais em conta marcados (o filé, mais caro, também aparece)")
            check(await cox.locator(".i-foot .i-sim").inner_text() == "Esconder similares" and await cox.locator(".sim-btn").count() == 0,
                  "no pé do cartão, ao lado do Buscar de novo")
            await cox.screenshot(path=SHOTS + "/ecl-similares.png")
            await sim.locator(".sim-list li").nth(1).locator(".esc-btn").click()
            await pg.wait_for_timeout(1200)
            cox = await item(pg, "Coxinha da asa")
            caixa = (await cox.locator(".i-best").first.inner_text()).replace("\xa0", " ")
            check("Sua escolha · similar".upper() in caixa.upper() and "R$ 12,48" in caixa and "Sobrecoxa" in caixa, f"similar escolhido ({caixa[:80]})")
            e = next(i for i in app.config_salva()["lista"] if i["produto"] == "Coxinha da asa").get("escolha") or {}
            check(e.get("sim") is True and e.get("obs") == "Sobrecoxa de Frango Resfriada Kg" and e.get("rede") == "merc-giassi", f"escolha gravada ({e})")
            await pg.click('.tabbar [data-view="roteiro"]')
            await pg.wait_for_timeout(600)
            rot = (await pg.locator(".parada").first.inner_text()).replace("\xa0", " ")
            check("Similar: Sobrecoxa de Frango Resfriada Kg" in rot and "R$ 12,48" in rot, "Roteiro usa o similar escolhido")
            await pg.locator(".parada").first.screenshot(path=SHOTS + "/ecl-roteiro.png")
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(400)
            # Esconder similares desfaz a escolha do similar
            await (await item(pg, "Coxinha da asa")).locator(".i-sim").click()
            await pg.wait_for_timeout(1200)
            cox = await item(pg, "Coxinha da asa")
            check(await cox.locator("details.i-det", has_text="Similares").count() == 0 and await cox.locator(".i-sim").inner_text() == "Buscar similares",
                  "escondidos: o grupo some e volta o Buscar similares")
            it = next(i for i in app.config_salva()["lista"] if i["produto"] == "Coxinha da asa")
            check("similares" not in it and "escolha" not in it, f"config sem similares e sem a escolha do similar ({it})")
            # Buscar similares num item sem eles: grava e já busca o item; o grupo abre com o que veio
            await (await item(pg, "Carne moída")).locator(".i-sim").click()
            await pg.wait_for_function("() => [...document.querySelectorAll('#wish > li.item')].some(li => /Carne moída/.test(li.textContent) && li.querySelector('details.i-det[data-det^=\"sim|\"]'))", timeout=30000)
            await pg.wait_for_timeout(500)
            carne = await item(pg, "Carne moída")
            sc = carne.locator("details.i-det", has_text="Similares (")
            check(await sc.get_attribute("open") is not None and "Acém Moído Bovino Kg" in await sc.inner_text() and "1 sai mais em conta que o item." in await sc.inner_text(),
                  "achou o acém, mais em conta, e o grupo abre")
            check(next(i for i in app.config_salva()["lista"] if i["produto"].startswith("Carne moída")).get("similares") is True, "ligado na config")
            with open(os.path.join(app.pasta, "similares.json"), encoding="utf-8") as f:
                reg = json.load(f)
            check("carne moida bovina de primeira" in reg and reg["carne moida bovina de primeira"]["itens"][0]["nome"] == "Acém Moído Bovino Kg",
                  "os achados ficam guardados para a próxima vez")
            # escondidos e pedidos de novo: os guardados aparecem na hora, sem outra busca
            await carne.locator(".i-sim").click()
            await pg.wait_for_timeout(800)
            pedidos = len(app.lojas.pedidos_de("intelligent-search"))
            await (await item(pg, "Carne moída")).locator(".i-sim").click()
            await pg.wait_for_timeout(800)
            carne = await item(pg, "Carne moída")
            check("Acém Moído Bovino Kg" in await carne.inner_text() and await carne.locator(".i-rebusca").inner_text() == "Buscar de novo",
                  "de volta na hora, sem buscar")
            check(len(app.lojas.pedidos_de("intelligent-search")) == pedidos, "nenhum pedido novo às lojas")
            await carne.screenshot(path=SHOTS + "/ecl-similares-carne.png")
            larg = await carne.evaluate("li => { const c = li.getBoundingClientRect(); return [...li.querySelectorAll('.sim-list li')].every(x => x.getBoundingClientRect().right <= c.right + 0.5); }")
            check(larg, "1.29.0: os similares dentro do cartão (a borda não passa)")
            # 1.29.0: Pôr na lista (um item novo) e Trocar por este (o item vira o similar)
            sc = carne.locator(".sim-list li", has_text="Acém Moído Bovino Kg")
            check(await sc.locator(".sim-acoes button").all_inner_texts() == ["Pôr na lista", "Trocar por este"], "as duas ações embaixo do similar")
            await sc.locator("[data-simpor]").click()
            await pg.wait_for_timeout(600)
            check(any(i["produto"] == "Acém moído bovino" for i in app.config_salva()["lista"]) and await pg.locator("#wish > li.item", has_text="Acém moído bovino").count() >= 1,
                  "Pôr na lista: o acém entrou como item novo, só o item (1.32.0: sem o Kg)")
            carne = await item(pg, "Carne moída")
            await carne.locator(".sim-list li", has_text="Acém Moído Bovino Kg").locator("[data-simtroca]").click()
            await pg.wait_for_timeout(500)
            check(any(i["produto"] == "Carne moída bovina de primeira" for i in app.config_salva()["lista"]), "já na lista: não troca")
            await pg.locator("#wish > li.item", has_text="Acém moído bovino").filter(has_not_text="Carne moída").locator("button.rm").click()
            await pg.wait_for_timeout(600)
            # Trocar por este: a coxinha (similares guardados, na hora) vira o frango inteiro, com as compras; a coxinha vai para o histórico
            await (await item(pg, "Coxinha da asa")).locator(".i-sim").click()
            await pg.wait_for_timeout(800)
            cox = await item(pg, "Coxinha da asa")
            await cox.locator(".sim-list li", has_text="Frango Inteiro Congelado Kg").locator("[data-simtroca]").click()
            await pg.wait_for_timeout(800)
            c = app.config_salva()
            novo = next((i for i in c["lista"] if i["produto"] == "Frango inteiro congelado"), {})
            check(not any(i["produto"] == "Coxinha da asa" for i in c["lista"]) and novo.get("compras") == ["2026-10-05", "2026-10-19"]
                  and "similares" not in novo and "escolha" not in novo, f"trocado, com as compras de antes ({novo})")
            check(any(h["produto"] == "Coxinha da asa" for h in c.get("historico") or []), "o nome de antes fica no histórico")

            # ----- Escolher esse (outra loja) e Desfazer -----
            carne = await item(pg, "Carne moída")
            await carne.locator(".i-others li", has_text="Angeloni").locator(".esc-btn").click()
            await pg.wait_for_timeout(1000)
            carne = await item(pg, "Carne moída")
            caixa = (await carne.locator(".i-best").first.inner_text()).replace("\xa0", " ")
            check("SUA ESCOLHA" in caixa.upper() and "Angeloni" in caixa and "R$ 42,90" in caixa, "escolheu o Angeloni, mais caro")
            check("O mais barato é R$ 39,90 no Giassi." in (await carne.inner_text()).replace("\xa0", " "), "avisa qual é o mais barato")
            await carne.locator("[data-desescolher]").click()
            await pg.wait_for_timeout(1000)
            carne = await item(pg, "Carne moída")
            check("MAIS BARATO" in (await carne.locator(".i-best").first.inner_text()).upper(), "Desfazer escolha volta ao mais barato")
            # 1.30.0: o remover fica no pé, ao lado do Buscar similares; no item sem preço (sem pé), nos botões
            # 1.35.0: com mais de um setor ligado, o setor do item (Setor automático) fica antes do remover
            pe = await carne.locator(".i-foot").evaluate("el => { const c = el.cloneNode(true); c.querySelectorAll('select').forEach((s) => s.replaceWith(s.selectedOptions[0].text)); return c.textContent; }")
            pe = " ".join(pe.replace("\xa0", " ").split())
            check(await carne.locator(".i-foot [data-rm]").count() == 1 and await carne.locator(".i-actions > [data-rm]").count() == 0
                  and pe.endswith("Buscar de novo · Esconder similares · Setor automático · remover"), f"remover no pé ({pe!r})")
            check(await (await item(pg, "Detergemte Ypê")).locator(".i-actions > [data-rm]").count() == 1, "sem preço: remover nos botões")
            # 1.30.0: o item com os similares ligados sai e volta do histórico com eles (os guardados, sem outra busca)
            pedidos = len(app.lojas.pedidos_de("intelligent-search"))
            await carne.locator(".i-foot [data-rm]").click()
            await pg.wait_for_timeout(800)
            check(any(h["produto"].startswith("Carne moída") and h.get("similares") is True for h in app.config_salva()["historico"]), "no histórico, com os similares ligados")
            await pg.click("#histBtn")
            await pg.wait_for_timeout(300)
            await pg.locator("#histLista .hist-row", has_text="Carne moída").locator(".hist-add").click()
            await pg.wait_for_timeout(900)
            await pg.click("#histBtn")
            carne = await item(pg, "Carne moída")
            check(await carne.locator(".i-sim").inner_text() == "Esconder similares" and "Acém Moído Bovino Kg" in await carne.inner_text()
                  and len(app.lojas.pedidos_de("intelligent-search")) == pedidos, "voltou com os similares, sem buscar")

            # ----- Quis dizer… no item sem preço -----
            det = await item(pg, "Detergemte Ypê")
            txt = await det.inner_text()
            check("SEM PREÇO AINDA" in txt.upper() and "Quis dizer" in txt, "item sem preço com a sugestão")
            await det.locator(".corr-btn").click()
            await pg.wait_for_timeout(1000)
            nomes = [i["produto"] for i in app.config_salva()["lista"]]
            check("Detergente Ypê" in nomes and "Detergemte Ypê" not in nomes, f"trocado para Detergente Ypê ({nomes})")

            # ----- Adicionar, repetido e Quis dizer… ao adicionar -----
            await pg.fill("#novoItem", "Arroz Tio João 5 kg")
            await pg.click('#addForm button[type="submit"]')
            await pg.wait_for_timeout(800)
            check('"Arroz Tio João 5 kg" entrou na lista.' in await pg.text_content("#addMsg"), "adicionado")
            await pg.fill("#novoItem", "arroz tio joão 5 KG")
            await pg.click('#addForm button[type="submit"]')
            check("já está na lista" in await pg.text_content("#addMsg"), "repetido (sem diferença de maiúsculas) não entra")
            await pg.fill("#novoItem", "ab")
            await pg.click('#addForm button[type="submit"]')
            check("Escreva o nome do produto" in await pg.text_content("#addMsg"), "nome curto demais")
            await pg.fill("#novoItem", "Álcool de lompeza")
            await pg.click('#addForm button[type="submit"]')
            await pg.wait_for_selector("#addMsg .corr-btn")
            check("Quis dizer" in await pg.text_content("#addMsg") and await pg.text_content("#addMsg .corr-btn") == "Álcool de limpeza", "Quis dizer ao adicionar")
            await pg.locator("#addMsg").screenshot(path=SHOTS + "/ecl-quis-dizer.png")
            await pg.click("#addMsg .corr-btn")
            await pg.wait_for_timeout(900)
            nomes = [i["produto"] for i in app.config_salva()["lista"]]
            check("Álcool de limpeza" in nomes and "Álcool de lompeza" not in nomes, "troca o nome com um toque")
            await pg.fill("#novoItem", "Café Pilão 500 g")
            await pg.click('#addForm button[type="submit"]')
            await pg.wait_for_timeout(900)
            check(await pg.locator("#addMsg .corr-btn").count() == 0, "nome certo: sem sugestão")

            # ----- Comprei hoje, remover → Histórico → voltar -----
            arroz = await item(pg, "Arroz Tio João")
            await arroz.locator("[data-comprei]").click()
            await pg.wait_for_timeout(800)
            arroz_cfg = next(i for i in app.config_salva()["lista"] if i["produto"] == "Arroz Tio João 5 kg")
            check(len(arroz_cfg.get("compras") or []) == 1, "Comprei hoje grava a compra")
            check("Última compra em" in await (await item(pg, "Arroz Tio João")).inner_text(), "mostra a última compra")
            await (await item(pg, "Arroz Tio João")).locator("button.rm").click()
            await pg.wait_for_timeout(900)
            check(await pg.locator("#wish > li.item", has_text="Arroz Tio João").count() == 0, "removido da lista")
            check(await pg.text_content("#histN") == "3", f"contador do histórico (o arroz, a coxinha trocada e o acém tirado) ({await pg.text_content('#histN')})")
            await pg.click("#histBtn")
            await pg.wait_for_timeout(300)
            linha = pg.locator("#histLista .hist-row", has_text="Arroz Tio João")
            check(await linha.count() == 1 and "Comprou 1 vez" in await linha.inner_text(), "no histórico, com a compra")
            await pg.locator("#histBox").screenshot(path=SHOTS + "/ecl-historico.png")
            await linha.locator(".hist-add").click()
            await pg.wait_for_timeout(900)
            arroz_cfg = next((i for i in app.config_salva()["lista"] if i["produto"] == "Arroz Tio João 5 kg"), {})
            check(len(arroz_cfg.get("compras") or []) == 1, "voltou para a lista com as compras de antes")
            check("voltou para a lista" in await pg.text_content("#addMsg"), "avisa que voltou")

            # ----- Limpar lista (com confirmação) -----
            n = await pg.locator("#wish > li.item").count()
            await pg.click("#limpar")
            check(await pg.locator("#limparConf").is_visible(), "Limpar pede confirmação")
            await pg.click("#limparNao")
            check(await pg.locator("#wish > li.item").count() == n, "Cancelar não tira nada")
            await pg.click("#limpar")
            await pg.click("#limparSim")
            await pg.wait_for_timeout(1000)
            check(await pg.locator("#wish > li.item").count() == 0, "Tirar tudo esvazia a lista")
            c = app.config_salva()
            check(len(c.get("lista") or []) == 0 and len(c.get("historico") or []) >= n, "os itens foram para o histórico")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
