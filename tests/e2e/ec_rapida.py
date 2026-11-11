# EconomIA 1.16.0: a Compra rápida, no Roteiro (Roteiro | Compra rápida, guardado no aparelho). Os itens de agora entram
# com as sugestões (os da lista com o nome de lá), não vão para a lista e ficam no aparelho; a resposta é uma loja física só:
# a mais perto com o máximo de itens, a não ser que outra com os mesmos itens saia bem mais barata. Nada online. Compare as
# outras lojas, o que falta lá, Como chegar, Buscar preços (só o que está sem preço, só nas lojas físicas) e Limpar.
# Lojas, itens e preços inventados.
import asyncio
import json

from playwright.async_api import async_playwright

from base_e2e import CEP, App, categoria, check, espera, pagina, prod, resumo, shot

OFERTAS = {"versao": 2, "gerado_em": "2026-11-01T10:00:00-03:00",
           "categorias": [categoria("mercados", [("merc-giassi", "Giassi", 1.0), ("merc-fort", "Fort", 2.0), ("merc-komprao", "Komprão", 4.5)]),
                          categoria("online", [("onli-amazon", "Amazon", None)])],
           "lista": [{"produto": "Café torrado em grãos", "precos": {"merc-giassi": 81.9, "merc-fort": 95.8, "onli-amazon": {"preco": 50.0, "frete": 0}}},
                     {"produto": "Arroz 5 kg", "precos": {"merc-giassi": 24.9, "merc-fort": 22.9}},
                     {"produto": "Pão de forma", "precos": {"merc-giassi": 9.9, "merc-fort": 8.5}},
                     # vistos numa compra rápida de antes: não estão na lista
                     {"produto": "Sabão em pó 1,6 kg", "precos": {"merc-giassi": 39.9, "merc-fort": 21.9}},
                     {"produto": "Leite integral", "precos": {"merc-fort": 5.2, "merc-komprao": 4.9}}]}


def limpo(s):
    return " ".join(s.replace("\xa0", " ").split())


async def chips(pg):
    return [limpo(x) for x in await pg.locator("#rapItens .rap-t").all_inner_texts()]


async def onde(pg):  # o nome da loja e o resumo (o rótulo Onde comprar fica em maiúsculas)
    lbl = await pg.inner_text("#rapRes .rap-onde .lbl")
    return limpo(lbl.capitalize() + " " + await pg.inner_text("#rapRes .rap-loja") + " " + await pg.inner_text("#rapRes .rap-onde .rot-sub"))


async def compare(pg):
    return [limpo(x) for x in await pg.locator("#rapRes .rot-op").all_inner_texts()]


async def adiciona(pg, nome):
    await pg.fill("#rapItem", nome)
    await pg.click('#rapForm button[type="submit"]')
    await pg.wait_for_timeout(250)


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados", "online"],
           "lista": [{"produto": "Café torrado em grãos"}, {"produto": "Arroz 5 kg"}, {"produto": "Pão de forma"}]}
    pilha = prod("Pilha Alcalina AA Duracell com 4", 21.9, "Bazar/Pilhas")
    with App(cfg, buscar=False, preparar=lambda L: L.catalogo.update(giassi=[pilha]), antes=lambda S: S.gravar_json(S.OFERTAS, OFERTAS)) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="roteiro"]')
            await pg.wait_for_timeout(300)
            check(await pg.locator("#rotModo button").all_inner_texts() == ["Roteiro", "Compra rápida"], "a escolha: Roteiro ou Compra rápida")
            check(await pg.get_attribute('#rotModo [data-modo="roteiro"]', "aria-pressed") == "true" and await pg.locator("#rapida").is_hidden(), "começa no Roteiro")
            await pg.click('#rotModo [data-modo="rapida"]')
            await pg.wait_for_timeout(300)
            check(await pg.inner_text("#h-rot") == "Compra rápida" and await pg.locator("#rotPlano").is_hidden() and await pg.locator("#rapida").is_visible(),
                  "na Compra rápida: o título, o campo, sem as paradas")
            check(await pg.locator("#rapRes").inner_text() == "" and await chips(pg) == [], "vazia: só o campo")
            # a sugestão traz o nome da lista
            await pg.click("#rapItem")
            await pg.keyboard.type("pão")
            await pg.wait_for_timeout(300)
            check("Pão de forma" in await pg.locator(".sug-box").inner_text(), "a sugestão: o item da lista")
            await pg.locator(".sug-box .sug-op", has_text="Pão de forma").click()
            await pg.click('#rapForm button[type="submit"]')
            await pg.wait_for_timeout(250)
            await adiciona(pg, "arroz 5 KG")
            check(await chips(pg) == ["Pão de forma", "Arroz 5 kg"], f"os itens, com o nome da lista ({await chips(pg)})")
            # 1.23.0: o melhor preço, mesmo um pouco mais longe (antes, a mais perto quando a outra saía menos de R$ 5 mais barata)
            check(await onde(pg) == "Onde comprar Fort 2,0 km · os 2 itens por R$ 31,40", f"onde comprar: o melhor preço ({await onde(pg)})")
            check(await compare(pg) == ["Fort · 2,0 km · recomendado R$ 31,40", "Giassi · 1,0 km R$ 34,80"], f"compare ({await compare(pg)})")
            check(limpo(await pg.inner_text("#rapRes .i-nota")) == "Fica mais longe, mas sai R$ 3,40 mais barato que Giassi (1,0 km).", "diz por que mais longe")
            # Buscar de novo e Limpar logo embaixo dos itens, lado a lado, do mesmo tamanho
            acoes = [t.strip() for t in await pg.locator("#rapAcoes > *").all_inner_texts()]
            check(acoes == ["Buscar de novo", "Limpar"], f"embaixo dos itens: Buscar de novo e Limpar ({acoes})")
            # outra bem mais barata com os mesmos itens: vale ir mais longe
            await adiciona(pg, "Sabão em pó 1,6 kg")
            check(await onde(pg) == "Onde comprar Fort 2,0 km · os 3 itens por R$ 53,30", f"o Fort, R$ 21,40 mais barato ({await onde(pg)})")
            check(limpo(await pg.inner_text("#rapRes .i-nota")) == "Fica mais longe, mas sai R$ 21,40 mais barato que Giassi (1,0 km).", "diz por que mais longe")
            # o que só uma loja tem decide: a que tem tudo
            await adiciona(pg, "Leite integral")
            await adiciona(pg, "Café torrado em grãos")
            texto = await pg.inner_text("#rapRes")
            check(await onde(pg) == "Onde comprar Fort 2,0 km · os 5 itens por R$ 154,30", f"a única com os 5 ({await onde(pg)})")
            check("Amazon" not in texto and "50,00" not in texto, "nada online, nem o café mais barato da Amazon")
            linhas = [limpo(x) for x in await pg.locator("#rapRes .parada li").all_inner_texts()]
            check(linhas == ["Pão de forma R$ 8,50", "Arroz 5 kg R$ 22,90", "Sabão em pó 1,6 kg R$ 21,90", "Leite integral R$ 5,20", "Café torrado em grãos R$ 95,80"],
                  f"o preço de cada item lá ({linhas})")
            href = await pg.get_attribute("#rapRes .row-form a", "href")
            check(href.startswith("https://www.google.com/maps/dir/?api=1") and "destination=Fort" in href and "origin=" not in href,
                  "Como chegar: do lugar onde está até a loja")
            check(await compare(pg) == ["Fort · 2,0 km · recomendado R$ 154,30", "Giassi · 1,0 km R$ 156,60 · sem 1 item", "Komprão · 4,5 km R$ 4,90 · sem 4 itens"],
                  f"compare: o que falta em cada uma ({await compare(pg)})")
            await shot(pg, "rapida", full_page=True)
            # ver outra loja: o que não tem lá e onde tem
            await pg.locator("#rapRes .rot-op", has_text="Giassi").click()
            await pg.wait_for_timeout(250)
            check(await onde(pg) == "Onde comprar Giassi 1,0 km · 4 de 5 itens por R$ 156,60", f"o Giassi ({await onde(pg)})")
            check("Não tem lá: Leite integral (Komprão, R$ 4,90)." in limpo(await pg.inner_text("#rapRes")), "o que falta e onde tem")
            # sem preço ainda: procura só esse, só nas lojas físicas, e não põe na lista
            await adiciona(pg, "Pilha AA")
            check(await chips(pg) == ["Pão de forma", "Arroz 5 kg", "Sabão em pó 1,6 kg", "Leite integral", "Café torrado em grãos", "Pilha AA sem preço"], "o item sem preço")
            check("Sem preço ainda: Pilha AA." in limpo(await pg.inner_text("#rapRes")), "diz o que está sem preço")
            check(await pg.inner_text('#rapAcoes [data-rapbusca="sem"]') == "Buscar preços", "o botão de buscar, embaixo dos itens")
            check((await compare(pg))[0] == "Fort · 2,0 km · recomendado R$ 154,30", f"o item sem preço em loja nenhuma não conta como faltando ({await compare(pg)})")
            med = await pg.evaluate("[...document.querySelectorAll('#rapAcoes > *')].map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; })")
            check(len(med) == 2 and med[0] == med[1] and med[0][1] == 50, f"Buscar preços e Limpar lado a lado, do mesmo tamanho ({med})")
            cc = await pg.evaluate("() => { const a = document.querySelector('#rapRes .row-form a'); return [Math.round(a.getBoundingClientRect().width), Math.round(a.parentElement.getBoundingClientRect().width), a.offsetHeight]; }")
            check(abs(cc[0] - cc[1]) <= 1 and cc[2] == 50, f"Como chegar na largura do cartão ({cc})")
            async with pg.expect_request(lambda r: "api/buscar-itens" in r.url and r.method == "POST") as rq:
                await pg.click('#rapAcoes [data-rapbusca="sem"]')
            check(json.loads((await rq.value).post_data) == {"itens": ["Pilha AA"], "rapida": True}, "procura só o que está sem preço")
            await espera(pg, "() => !document.getElementById('buscar').disabled", 30000)
            await pg.wait_for_timeout(800)
            check(await chips(pg) == ["Pão de forma", "Arroz 5 kg", "Sabão em pó 1,6 kg", "Leite integral", "Café torrado em grãos", "Pilha AA"], f"achou a pilha ({await chips(pg)})")
            check("Pilha AA R$ 21,90" in [limpo(x) for x in await pg.locator("#rapRes .parada li").all_inner_texts()]
                  or "Pilha AA" in limpo(await pg.inner_text("#rapRes")), "a pilha entra na conta")
            check([i["produto"] for i in app.config_salva()["lista"]] == ["Café torrado em grãos", "Arroz 5 kg", "Pão de forma"], "a lista não muda")
            # repetido e o limite
            await adiciona(pg, "pilha aa")
            check(await pg.inner_text("#rapMsg") == "Já está aqui.", "não repete")
            # fica no aparelho: abre de novo na Compra rápida, com os itens
            await pg.reload()
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="roteiro"]')
            await pg.wait_for_timeout(300)
            check(await pg.locator("#rapida").is_visible() and len(await chips(pg)) == 6, "depois de abrir de novo, continua")
            # um toque tira; Limpar tira tudo
            await pg.locator("#rapItens .rap-t", has_text="Leite").click()
            await pg.wait_for_timeout(250)
            check("Leite integral" not in await chips(pg), "um toque tira o item")
            check(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "nada passa da largura")
            await pg.click("#rapAcoes [data-raplimpar]")
            await pg.wait_for_timeout(250)
            check(await chips(pg) == [] and await pg.locator("#rapRes").inner_text() == "" and await pg.locator("#rapAcoes > *").count() == 0, "Limpar: vazia")
            await pg.click('#rotModo [data-modo="roteiro"]')
            await pg.wait_for_timeout(250)
            check(await pg.locator("#rotPlano").is_visible() and await pg.inner_text("#h-rot") == "Roteiro de compras", "de volta ao Roteiro")
            await b.close()
            b, pg = await pagina(p, 320, 700, escuro=False)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="roteiro"]')
            await pg.click('#rotModo [data-modo="rapida"]')
            for nome in ("Pão de forma", "Sabão em pó 1,6 kg", "Leite integral", "Papel higiênico folha dupla com 12 rolos"):
                await adiciona(pg, nome)
            check(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "320 px: nada passa da largura")
            med = await pg.evaluate("[...document.querySelectorAll('#rapAcoes > *')].map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height), Math.round(r.top)]; })")
            check(len(med) == 2 and med[0][:2] == med[1][:2] and med[0][1] == 50, f"320 px: os dois botões do mesmo tamanho (sem caber lado a lado, um embaixo do outro) ({med})")
            caixa = await pg.evaluate("[document.getElementById('rapItem'), document.querySelector('#rapForm .btn')].map(e => Math.round(e.getBoundingClientRect().top))")
            check(caixa[0] == caixa[1], "320 px: o campo e o Adicionar na mesma linha")
            await shot(pg, "rapida-320", full_page=True)
            await b.close()
    resumo()


asyncio.run(main())
