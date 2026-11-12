# EconomIA 1.35.0: a comparação é sempre por quilo, litro ou unidade (nunca pelo tamanho de sempre do item, 400 g ou
# 30 ml) e nada se compara entre setores: cada item fica no setor escolhido (Onde comprar, ao adicionar ou no pé do
# cartão) ou no das lojas em que ele mais aparece. Lojas e preços inventados.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, App, categoria, check, pagina, resumo, shot

OFERTAS = {"versao": 2, "gerado_em": "2026-11-02T10:00:00-03:00", "categorias": [
    categoria("mercados", [("merc-azul", "Mercado Azul", 0.8), ("merc-sol", "Atacado Sol", 3.0)]),
    categoria("farmacias", [("farm-lua", "Farmácia Lua", 1.0), ("farm-mar", "Drogaria Mar", 1.5)])],
    "lista": [
        {"produto": "Peito de frango", "precos": {"merc-azul": 18.0, "merc-sol": 19.0}, "base": {"quantidade": 0.4, "unidade": "kg"},
         "tamanhos": [{"rede": "merc-sol", "embalagem": "Peito de frango 1,5 kg", "quantidade": 1.5, "preco": 14.4}]},
        {"produto": "Álcool 70", "precos": {"farm-lua": 6.26, "farm-mar": 6.28}, "base": {"quantidade": 0.03, "unidade": "L"},
         "tamanhos": [{"rede": "merc-sol", "embalagem": "Galão 5 L", "quantidade": 5, "preco": 42.98}]},
        {"produto": "Leite sem lactose", "precos": {"merc-azul": {"preco": 4.98, "obs": "Leite Vale Bom zero lactose 1 L"}, "merc-sol": 5.59, "farm-lua": 23.88}, "base": {"quantidade": 1, "unidade": "L"}},
        # 1.36.0: o tamanho de sempre achado pela busca (400 g) bem acima do comum: a referência é o preço comum do quilo
        {"produto": "Coxa de frango", "precos": {"merc-azul": 18.48, "merc-sol": 19.9}, "base": {"quantidade": 0.4, "unidade": "kg"},
         "tamanhos": [{"rede": "merc-azul", "embalagem": "Coxa 1 kg", "quantidade": 1, "preco": 15.9},
                      {"rede": "merc-sol", "embalagem": "Coxa bandeja 1 kg", "quantidade": 1, "preco": 17.98},
                      {"rede": "merc-sol", "embalagem": "Coxa congelada 1,5 kg", "quantidade": 1.5, "preco": 14.38}]}]}


def limpo(s):
    return " ".join(s.replace("\xa0", " ").split())


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados", "farmacias"],
           "lista": [{"produto": "Peito de frango"}, {"produto": "Álcool 70"}, {"produto": "Leite sem lactose"}, {"produto": "Coxa de frango"}]}
    with App(cfg, buscar=False, antes=lambda S: S.gravar_json(S.OFERTAS, OFERTAS)) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(400)
            item = lambda nome: pg.locator("#wish > li.item", has_text=nome).first  # noqa: E731
            # ----- por quilo, não por 400 g -----
            frango = item("Peito de frango")
            best = limpo(await frango.locator(".i-best").inner_text())
            check("R$ 9,60 por quilo" in best and "Peito de frango 1,5 kg por R$ 14,40 · Atacado Sol" in best and "400 g" not in best, f"Melhor compra por quilo ({best})")
            av = limpo(await frango.locator(".i-avulso").first.inner_text())
            check(av == "Avulso, o mais barato: R$ 45,00 por quilo · 400 g por R$ 18,00 (Mercado Azul)", f"o avulso também por quilo ({av})")
            eco = limpo(await frango.locator(".i-save").inner_text())
            check(eco == "economia de R$ 35,40/kg", f"a economia por quilo ({eco})")
            await frango.screenshot(path=__import__("os").path.join(__import__("base_e2e").SHOTS, "setor-frango.png"))
            # ----- 1.36.0: o pacote de 400 g a R$ 46/kg não é a referência: o comum das 5 opções (R$ 17,98/kg) -----
            coxa = item("Coxa de frango")
            best = limpo(await coxa.locator(".i-best").inner_text())
            check("R$ 9,59 por quilo" in best and "Coxa congelada 1,5 kg por R$ 14,38 · Atacado Sol" in best, f"a mais barata por quilo ({best})")
            av = limpo(await coxa.locator(".i-avulso").first.inner_text())
            check(av == "O comum é R$ 17,98 por quilo, em 5 opções.", f"comparada ao comum ({av})")
            check(limpo(await coxa.locator(".i-save").inner_text()) == "economia de R$ 8,39/kg" and await coxa.locator(".i-others").count() == 0,
                  "a economia contra o comum, sem os pacotes de 400 g soltos (estão no Comparar tamanhos)")
            await coxa.locator("details.i-det").first.evaluate("d => { d.open = true; }")
            det = limpo(await coxa.locator("details.i-det").first.inner_text())
            check("MAIS BARATO POR QUILO" in det.upper() and "Sai R$ 9,59/kg; o comum é R$ 17,98/kg." in det, f"o porquê ({det[:200]})")
            # ----- automático: o álcool fica nas farmácias (onde mais aparece); o galão do atacado não entra -----
            alc = item("Álcool 70")
            t = limpo(await alc.inner_text())
            check("MAIS BARATO" in t.upper() and "Farmácia Lua" in t and "Atacado Sol" not in t and "Galão" not in t, f"álcool: só as farmácias ({t[:200]})")
            check(await alc.locator("details.i-det").count() == 0, "sem Comparar tamanhos com o galão de outro setor")
            check("Em 2 farmácias" in t, "o pé conta só as farmácias")
            leite = item("Leite sem lactose")
            t = limpo(await leite.inner_text())
            check("Farmácia Lua" not in t and "Em 2 mercados" in t and "economia de R$ 0,61" in t, f"leite: só os mercados ({t[:200]})")
            # 1.36.7: o produto achado acima do cartão do preço; "Em 2 mercados · preços de…" no fim, embaixo dos botões;
            # o Comprei hoje é o botão cheio (a ação principal), como o Criar backup
            ordem = await leite.evaluate("""li => { const q = s => li.querySelector(s), segue = (a, b) => !!(a && b && (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING));
                return [q('.i-produto') && q('.i-produto').textContent, segue(q('.i-produto'), q('.i-best')), segue(q('.i-botoes'), q('.i-foot')), li.lastElementChild.classList.contains('i-foot')]; }""")
            check(ordem == ["Produto: Leite Vale Bom zero lactose 1 L", True, True, True], f"o produto antes do preço e o Em 2 mercados no fim ({ordem})")
            cor = await leite.evaluate("""li => { const b = li.querySelector('[data-comprei]'), c = getComputedStyle(b);
                return [b.classList.contains('btn'), c.backgroundColor === getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || c.backgroundColor !== 'rgba(0, 0, 0, 0)', Math.round(b.getBoundingClientRect().height)]; }""")
            check(cor == [True, True, 50], f"Comprei hoje: o botão cheio, com 50 px ({cor})")
            await leite.screenshot(path=__import__("os").path.join(__import__("base_e2e").SHOTS, "setor-leite.png"))
            sel = alc.locator("select[data-setor]")
            ops = [limpo(x) for x in await sel.locator("option").all_inner_texts()]
            check(ops == ["Qualquer", "Mercado", "Farmácia"], f"o setor no pé do cartão, como ao adicionar ({ops})")
            # ----- só mercado: o galão vira o preço do item -----
            await sel.select_option("mercados")
            await pg.wait_for_timeout(700)
            check(next(i for i in app.config_salva()["lista"] if i["produto"] == "Álcool 70").get("setor") == "mercados", "o setor fica guardado")
            alc = item("Álcool 70")
            t = limpo(await alc.inner_text())
            check("R$ 42,98" in t and "Atacado Sol" in t and "Farmácia Lua" not in t and "Em 1 mercado" in t, f"só mercado: o galão do atacado ({t[:200]})")
            check(await alc.locator("select[data-setor]").input_value() == "mercados", "o pé mostra Mercado")
            await alc.locator("select[data-setor]").select_option("")
            await pg.wait_for_timeout(700)
            check("setor" not in next(i for i in app.config_salva()["lista"] if i["produto"] == "Álcool 70"), "de volta ao automático")
            # ----- Onde comprar, ao adicionar -----
            sel = pg.locator("#novoSetor")
            check(await sel.is_visible(), "Onde comprar aparece com mais de um setor ligado")
            ops = [limpo(x) for x in await sel.locator("option").all_inner_texts()]
            check(ops == ["Qualquer", "Mercado", "Farmácia"], f"as opções de onde comprar ({ops})")
            # antes do Adicionar: o nome numa linha; embaixo, onde comprar e os botões, na mesma linha e da mesma altura
            cx = {k: await pg.locator(s_).bounding_box() for k, s_ in (("nome", "#novoItem"), ("onde", "#novoSetor"), ("add", '#addForm button[type="submit"]'))}
            check(cx["onde"]["y"] > cx["nome"]["y"] + cx["nome"]["height"] - 1 and abs(cx["onde"]["y"] - cx["add"]["y"]) < 1
                  and abs(cx["onde"]["height"] - cx["add"]["height"]) < 1 and cx["onde"]["x"] + cx["onde"]["width"] <= cx["add"]["x"],
                  f"onde comprar antes do Adicionar ({cx})")
            await pg.select_option("#novoSetor", "farmacias")
            await pg.fill("#novoItem", "Dipirona 1 g")
            await pg.click('#addForm button[type="submit"]')
            await pg.wait_for_timeout(700)
            novo = next(i for i in app.config_salva()["lista"] if i["produto"] == "Dipirona 1 g")
            check(novo.get("setor") == "farmacias", f"o item novo entra com o setor ({novo})")
            check(await pg.input_value("#novoSetor") == "", "o campo volta ao automático")
            check(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "nada passa da largura")
            await shot(pg, "setor-lista")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
