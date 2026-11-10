# EconomIA 0.19.0: a tela Ofertas: categorias, resumo (melhor cupom e destaque), filtro por loja, ordem (o que
# está na lista primeiro), "Não mostrar" (só esta oferta ou o tipo inteiro) e "Mostrar de novo", escondidas pelo perfil
# (1.8.0: no fim, em Escondidas (N), recolhidas até um toque; os cupons vencidos também, em Vencidos (N)),
# receita, clube, cupons com a validade (vence em, não confirmado, vencido, até) e o Copiar, "Sem preços de", Online
# com frete, prazo e os mercados da região, pet shops só para o pet da casa e a categoria vazia.
import asyncio
from datetime import datetime, timedelta, timezone

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, categoria, check, espera, pagina, resumo

HOJE = (datetime.now(timezone.utc) - timedelta(hours=3)).date()
D = lambda n: (HOJE + timedelta(days=n)).isoformat()  # noqa: E731


def oferta(i, rede, produto, por, de=None, **kw):
    return dict({"id": i, "rede": rede, "produto": produto, "preco_oferta": por, "preco_normal": de, "tipo": "promo" if de else "preco", "tags": []}, **kw)


OFERTAS = {"versao": 2, "gerado_em": "2026-11-02T10:00:00-03:00", "lista": [], "categorias": [
    categoria("farmacias", [("farm-panvel", "Panvel", 0.8), ("farm-nissei", "Farmácias Nissei", 1.4), ("farm-vida", "Farmácia Vida", 1.0)], ofertas=[
        oferta("o-cerveja", "farm-panvel", "Cerveja Heineken 350 ml", 4.49, 5.99, tags=["alcool"]),
        oferta("o-protetor", "farm-panvel", "Protetor solar Nivea FPS 50 · 200 ml", 59.9, 79.9, tags=["skincare"], fonte="https://www.panvel.com/protetor"),
        oferta("o-dipirona", "farm-nissei", "Dipirona 1 g · 10 comprimidos", 8.9, 12.9, receita="mip"),
        oferta("o-fralda", "farm-nissei", "Fralda Pampers Confort Sec G", 79.9, 99.9, tags=["bebe"]),
        oferta("o-shampoo", "farm-panvel", "Shampoo Seda 325 ml", 11.9, 15.9, tipo="clube"),
        oferta("o-rivotril", "farm-nissei", "Rivotril 2 mg", 9.9, receita="tarja")],
        cupons=[{"rede": "farm-panvel", "codigo": "PANVEL20", "valor": 20, "beneficio": "R$ 20 de desconto", "condicao": "Acima de R$ 100", "valido_ate": D(2), "status": "confirmado"},
                {"rede": "farm-nissei", "codigo": "NISSEI10", "valor": 10, "beneficio": "10% em tudo", "condicao": "No app", "valido_ate": None, "status": "testar"},
                {"rede": "farm-panvel", "codigo": "VELHO", "valor": 5, "beneficio": "R$ 5", "condicao": "", "valido_ate": D(-1), "status": "confirmado"},
                {"rede": "farm-nissei", "codigo": "NATAL", "valor": 15, "beneficio": "15% no Natal", "condicao": "", "valido_ate": D(60), "status": "confirmado"}]),
    categoria("mercados", [("merc-giassi", "Giassi", 1.1)]),
    categoria("petshops", [("pets-cobasi", "Cobasi", 1.0)], ofertas=[
        oferta("o-golden", "pets-cobasi", "Ração Golden Gatos Castrados 10 kg", 159.9, 189.9, tags=["pet", "gato"]),
        oferta("o-pedigree", "pets-cobasi", "Ração Pedigree Cães Adultos 15 kg", 139.9, 169.9, tags=["pet", "cachorro"])]),
    categoria("online", [("onli-amazon", "Amazon", None, {"horario": "Entrega no seu CEP"}), ("onli-bistek", "Bistek", None, {"regional": True})], ofertas=[
        oferta("o-cafe", "onli-amazon", "Café Pilão 500 g", 18.9, 22.9, frete=0, prazo_dias=2, vendedor="Amazon", oficial=True, tags=["cafe"]),
        oferta("o-arroz", "onli-bistek", "Arroz Tio João 5 kg", 24.9, 29.9, frete=None, frete_carrinho=True)])]}


def antes(S):
    S.gravar_json(S.OFERTAS, OFERTAS)


async def deals(pg):
    return [t.strip() for t in await pg.locator("#deals .d-prod").all_inner_texts()]


async def escondidas(pg):
    """Escondidas (N) no fim das ofertas: o título (ou None), se está aberta e os produtos dela."""
    d = pg.locator("#dealsInat details.inativas")
    if not await d.count():
        return None, False, []
    return ((await d.locator("summary").inner_text()).strip(), await d.evaluate("(e) => e.open"),
            [t.strip() for t in await d.evaluate("(e) => [...e.querySelectorAll('.d-prod')].map((x) => x.textContent)")])


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["farmacias", "mercados", "petshops", "online"],
           "lista": [{"produto": "Protetor solar Nivea FPS 50"}], "clubes": ["farm-panvel"],
           "perfil": {"adultos": 2, "criancas": 0, "bebes": 0, "pets": {"gato": 1, "cachorro": 0, "outros": 0}, "interesses": ["cafe"], "nunca": [], "restricoes": []},
           "cupons_meus": [{"id": "meu-1", "rede": "farm-panvel", "beneficio": "20% em protetor solar", "valido_ate": D(10), "produto": "Protetor solar"}]}
    with App(cfg, buscar=False, antes=antes) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p, permissoes=["clipboard-read", "clipboard-write"])
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="ofertas"]')
            await espera(pg, "() => document.querySelectorAll('#deals .deal').length > 0")
            cats = [t.strip() for t in await pg.locator("#cats button").all_inner_texts()]
            check(cats == ["Farmácias", "Mercados", "Pet shops", "Online"], f"categorias ({cats})")
            check(await pg.text_content("#screenTitle") == "Ofertas", "título da tela")
            # ordem: a da lista primeiro; a fralda (sem crianças no perfil) fica escondida
            d = await deals(pg)
            check(d[0] == "Protetor solar Nivea FPS 50 · 200 ml" and "Fralda Pampers Confort Sec G" not in d, f"o item da lista primeiro e a fralda escondida ({d})")
            check("Está na sua lista" in await pg.locator("#deals .deal").first.inner_text(), "diz por que está em primeiro")
            # resumo
            check(await pg.text_content("#sumCupom") == "PANVEL20", "melhor cupom: o confirmado de maior valor, dentro da validade")
            check("Panvel · R$ 20 de desconto · vence em 2 dias" in await pg.text_content("#sumCupomS"), f"cupom com loja e validade ({await pg.text_content('#sumCupomS')})")
            check(await pg.text_content("#sumTop") == "−25%", f"destaque: −25% ({await pg.text_content('#sumTop')})")
            tit, aberta, prods = await escondidas(pg)
            check(tit == "Escondidas (1)" and not aberta and prods == ["Fralda Pampers Confort Sec G"], f"a escondida pelo perfil no fim, recolhida, com o nome e a contagem ({tit}, {aberta}, {prods})")
            check(await pg.locator("#factHid, #sumHid").count() == 0, "sem a faixa das escondidas no alto")
            fim = await pg.evaluate("() => [document.querySelector('#deals').getBoundingClientRect().bottom, document.querySelector('#dealsInat').getBoundingClientRect().top]")
            check(fim[1] >= fim[0], f"depois das outras ofertas ({fim})")
            # receita, clube, preço atual
            dip = pg.locator("#deals .deal", has_text="Dipirona")
            check("Sem receita" in await dip.inner_text(), "remédio sem receita marcado")
            riv = (await pg.locator("#deals .deal", has_text="Rivotril").inner_text()).replace("\xa0", " ")
            check("Tarja vermelha · com receita" in riv and "Preço atual" in riv, "tarja vermelha e preço sem o 'de'")
            sh = (await pg.locator("#deals .deal", has_text="Shampoo").inner_text()).replace("\xa0", " ")
            check("SEU CLUBE" in sh.upper() and "Sem clube R$ 15,90" in sh, f"oferta de clube de quem é do clube ({sh[:80]})")
            check(await pg.locator('#deals .deal', has_text="Protetor").locator('a[href="https://www.panvel.com/protetor"]').count() == 1, "link da fonte")
            await pg.locator("#v-ofertas").screenshot(path=SHOTS + "/eco-farmacias.png")
            # sem preços: a loja do raio sem nada
            sp = await pg.text_content("#semPrecos")
            check("Sem preços de: Farmácia Vida." in sp and "Mandar encarte" in sp and "Adicionar site" in sp, f"loja sem preços ({sp})")
            # filtro por loja
            filtros = [t.strip() for t in await pg.locator("#filters button").all_inner_texts()]
            check(filtros == ["Todas", "Panvel", "Farmácias Nissei"], f"filtros: só as lojas com oferta, sem a Farmácia Vida ({filtros})")
            await pg.click('#filters [data-rede="farm-nissei"]')
            check(await deals(pg) == ["Dipirona 1 g · 10 comprimidos", "Rivotril 2 mg"], f"só a Nissei ({await deals(pg)})")
            # o Destaque leva à oferta: volta para Todas e a linha pisca no meio da tela
            await pg.click("#factTop")
            check(await pg.get_attribute('#filters [data-rede="todas"]', "aria-pressed") == "true", "o Destaque volta para Todas")
            linha = pg.locator('#deals .deal', has_text="Protetor solar")
            check("achada" in (await linha.get_attribute("class")), "a oferta do Destaque fica marcada")
            await pg.wait_for_timeout(900)
            caixa = await linha.bounding_box()
            check(0 < caixa["y"] < 844 - caixa["height"], f"e aparece na tela ({caixa})")
            check(await pg.locator('#deals [data-act="avaliar"]').count() == len(await deals(pg)), "cada oferta tem Vale a pena?")
            acts = [x.strip() for x in await linha.locator(".d-acts .hide-btn").all_inner_texts()]
            check(acts == ["Comparar preço", "Vale a pena?", "Não mostrar"], f"Comparar preço, Vale a pena? e Não mostrar ({acts})")
            ys = [(await linha.locator(".d-acts .hide-btn").nth(i).bounding_box())["y"] for i in range(3)]
            check(max(ys) - min(ys) < 2, f"os três na mesma linha ({ys})")
            await pg.evaluate("window.scrollTo(0, 0)")
            # Não mostrar: o tipo inteiro (bebidas alcoólicas), ver as escondidas e mostrar de novo
            cerveja = pg.locator("#deals .deal", has_text="Cerveja")
            await cerveja.locator('[data-act="menu"]').click()
            menu = await pg.locator("#deals .hide-menu").inner_text()
            check("Só esta oferta" in menu and "Nada de bebidas alcoólicas" in menu, f"menu de esconder ({menu})")
            await pg.click('#deals [data-act="nunca"]')
            await pg.wait_for_timeout(800)
            check("alcool" in app.config_salva()["perfil"]["nunca"], "gravado em Nunca mostrar")
            tit, aberta, prods = await escondidas(pg)
            check("Cerveja Heineken 350 ml" not in await deals(pg) and tit == "Escondidas (2)" and "Cerveja Heineken 350 ml" in prods, f"some e conta nas escondidas ({tit}, {prods})")
            await pg.click("#dealsInat summary")
            check((await escondidas(pg))[1], "um toque abre as escondidas")
            await pg.locator("#dealsInat").screenshot(path=SHOTS + "/eco-escondidas.png")
            muted = pg.locator("#dealsInat .deal.muted", has_text="Cerveja")
            check(await muted.count() == 1 and "Você pediu para não mostrar bebidas alcoólicas" in await muted.inner_text(), "escondida aparece apagada, com o motivo")
            fralda = pg.locator("#dealsInat .deal.muted", has_text="Fralda")
            check("Não há crianças no seu perfil" in await fralda.inner_text() and await fralda.locator('[data-act="perfil"]').count() == 1, "a do perfil: Ajustar no perfil")
            await muted.locator('[data-act="mostrar"]').click()
            await pg.wait_for_timeout(800)
            check("alcool" not in app.config_salva()["perfil"]["nunca"], "Mostrar de novo tira de Nunca mostrar")
            check("Cerveja Heineken 350 ml" in await deals(pg) and (await escondidas(pg))[:2] == ("Escondidas (1)", True), "volta para as ofertas; as escondidas continuam abertas")
            await pg.click("#dealsInat summary")
            check(not (await escondidas(pg))[1], "outro toque recolhe")
            # Só esta oferta
            await pg.locator("#deals .deal", has_text="Dipirona").locator('[data-act="menu"]').click()
            await pg.click('#deals [data-act="esconder"]')
            await pg.wait_for_timeout(800)
            check(app.config_salva().get("ocultas") == ["o-dipirona"], "Só esta oferta: o id fica em ocultas")
            check("Dipirona 1 g · 10 comprimidos" not in await deals(pg) and "Dipirona 1 g · 10 comprimidos" in (await escondidas(pg))[2], "e ela vai para as escondidas")
            # cupons e validade
            t = pg.locator("#tickets .ticket")
            textos = [x.replace("\xa0", " ").upper() for x in await t.all_inner_texts()]  # os selos são em maiúsculas
            check(len(textos) == 4 and "SEU CUPOM" in textos[0] and "JÁ ESTÁ NO APP DA LOJA" in textos[0], f"o seu cupom do app primeiro ({textos[:1]})")
            chip = lambda cod: next((x for x in textos if cod in x), "")  # noqa: E731
            check("VENCE EM 2 DIAS" in chip("PANVEL20"), "vence em 2 dias")
            check("NÃO CONFIRMADO" in chip("NISSEI10"), "cupom a testar: não confirmado")
            # 1.8.0: o vencido no fim, em Vencidos (1), recolhido até um toque
            venc = pg.locator("#ticketsInat details.inativas")
            check(chip("VELHO") == "" and await venc.count() == 1 and (await venc.locator("summary").inner_text()).strip() == "Vencidos (1)" and not await venc.evaluate("(e) => e.open"),
                  "o vencido fora dos outros, em Vencidos (1), recolhido")
            await venc.locator("summary").click()
            v = (await venc.locator(".ticket").inner_text()).replace("\xa0", " ").upper()
            check(await venc.evaluate("(e) => e.open") and "VELHO" in v and "VENCIDO" in v, f"um toque mostra o vencido ({v[:60]})")
            await venc.locator("summary").click()
            fim = (HOJE + timedelta(days=60))
            check(f"ATÉ {fim:%d/%m/%Y}" in chip("NATAL"), f"longe: a data ({chip('NATAL')[-30:]})")
            await pg.locator('#tickets .copy[data-code="PANVEL20"]').click()
            await espera(pg, "() => /Copiado|Selecionado/.test(document.querySelector('#tickets .copy[data-code=\"PANVEL20\"]').textContent)")
            check(True, "Copiar o código")
            forma = await pg.locator("#tickets .chip.deal").evaluate_all("es => es.map(e => [getComputedStyle(e).display, Math.round(e.getBoundingClientRect().height)])")
            check(len(forma) == 1 and all(d in ("flex", "inline-flex") and h < 30 for d, h in forma), f"o selo de validade urgente é um selo, não uma linha de oferta ({forma})")
            await pg.locator("#tickets").screenshot(path=SHOTS + "/eco-cupons.png")
            # Online: frete, prazo, loja oficial, mercado da região
            await pg.click('#cats [data-cat="online"]')
            await pg.wait_for_timeout(300)
            check(await pg.text_content("#ofertasMeta") == "Preço com frete para o seu CEP.", "online: preço com frete")
            filtros = (await pg.text_content("#filters")).replace("\xa0", " ")
            check("Mercados da região que entregam" in filtros and filtros.index("Amazon") < filtros.index("Mercados da região") < filtros.index("Bistek"), "os mercados da região separados")
            cafe = (await pg.locator("#deals .deal", has_text="Café").inner_text()).replace("\xa0", " ")
            check("Frete grátis" in cafe and "Chega em 2 dias" in cafe and "Loja oficial" in cafe and "Você se interessa por café" in cafe, f"café na Amazon ({cafe[:120]})")
            arroz = await pg.locator("#deals .deal", has_text="Arroz").inner_text()
            check("Frete no carrinho" in arroz and "Mercado da região" in arroz, "arroz no Bistek: frete no carrinho")
            await pg.locator("#v-ofertas").screenshot(path=SHOTS + "/eco-online.png")
            # Pet shops: só o do gato da casa; Mercados sem ofertas
            await pg.click('#cats [data-cat="petshops"]')
            check(await deals(pg) == ["Ração Golden Gatos Castrados 10 kg"], f"pet shop: só a ração de gato ({await deals(pg)})")
            check((await escondidas(pg))[::2] == ("Escondidas (1)", ["Ração Pedigree Cães Adultos 15 kg"]), f"a de cachorro escondida ({await escondidas(pg)})")
            await pg.click('#cats [data-cat="mercados"]')
            check("Nenhuma oferta encontrada ainda" in await pg.text_content("#deals"), "categoria sem ofertas")
            check(await pg.locator("#resumo").is_hidden(), "sem nada: o resumo some")
            # desligados em Online: o marketplace fora da busca e os mercados da região somem das ofertas e dos filtros
            st = app.api("GET", "/api/estado")
            app.api("PUT", "/api/config", dict(st["config"], online={"marketplaces": ["mercadolivre"], "mercados_entrega": False}))
            await pg.reload()
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="ofertas"]')
            await pg.click('#cats [data-cat="online"]')
            check("Nenhuma oferta encontrada" in await pg.text_content("#deals") and await pg.locator("#filters").is_hidden(),
                  "Amazon fora da busca e Bistek com os mercados da região desligados: sem ofertas nem filtros")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
