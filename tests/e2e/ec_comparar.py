# EconomIA 1.5.0: Comparar preço nas Ofertas. Cada oferta tem "Comparar preço" ao lado do "Não mostrar" (os dois na mesma
# linha); tocar procura o mesmo produto nas outras lojas (busca de verdade contra as lojas falsas, sem IA) e mostra ali
# mesmo: "Mais barato em outra loja" com as lojas do mais barato para o mais caro (a mais barata marcada, com o link),
# "Menor preço entre 3 lojas" quando a oferta ganha e "Não achei em outras lojas". Enquanto procura: "Comparando…" e o
# Buscar girando; no fim, o aviso. Fica depois de recarregar. 390 px escuro e 320 px claro, nada para fora da tela.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, categoria, check, espera, pagina, prod, resumo


def oferta(i, rede, produto, por, de=None, **kw):
    return dict({"id": i, "rede": rede, "produto": produto, "preco_oferta": por, "preco_normal": de, "tipo": "promo" if de else "preco", "tags": []}, **kw)


OFERTAS = {"versao": 2, "gerado_em": "2026-11-08T10:00:00-03:00", "lista": [], "categorias": [
    categoria("mercados", [("merc-bistek", "Bistek Supermercados", 2.4), ("merc-giassi", "Giassi", 1.1)], ofertas=[
        oferta("o-cafe", "merc-bistek", "Café Pilão Tradicional 500 g", 21.9, 42.9),
        oferta("o-nescau", "merc-bistek", "Achocolatado Nescau 400 g", 7.99, 9.99),
        oferta("o-geleia", "merc-bistek", "Geleia de jabuticaba artesanal 300 g", 25.0, 30.0)])]}


def prepara(lojas):
    lojas.catalogo["giassi"] = [prod("Café Pilão Tradicional 500g", 19.90, "Mercearia/Café"), prod("Achocolatado em Pó Nescau 400g", 9.49, "Mercearia/Achocolatado")]
    lojas.catalogo["angeloni"] = [prod("Café Pilão Tradicional 500g", 23.50, "Mercearia/Café", link="/cafe-ang/p"),
                                  prod("Achocolatado em Pó Nescau 400g", 8.99, "Mercearia/Achocolatado", link="/nescau-ang/p")]


def antes(S):
    S.gravar_json(S.OFERTAS, OFERTAS)


FORA = """() => { const W = innerWidth, ruins = [];
  for (const e of document.querySelectorAll('#deals *')) { const r = e.getBoundingClientRect();
    if (r.width && (r.right > W + 1 || r.left < -1)) ruins.push(e.className || e.tagName); }
  if (document.documentElement.scrollWidth > W) ruins.push('página ' + document.documentElement.scrollWidth);
  return ruins.slice(0, 4); }"""


async def txt(loc):
    return " ".join((await loc.inner_text()).replace("\xa0", " ").split())


async def comparar(pg, nome, tag):
    d = pg.locator("#deals .deal", has_text=nome)
    await d.locator('[data-act="comparar"]').click()
    await espera(pg, f"() => {{ const d = [...document.querySelectorAll('#deals .deal')].find(x => x.textContent.includes({nome!r})); return d && d.querySelector('.cmp'); }}", 20000)
    await espera(pg, "() => !document.getElementById('buscar').disabled")
    return d


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados"], "lista": [], "usar_ia": False}
    with App(cfg, buscar=False, preparar=prepara, antes=antes) as app:
        async with async_playwright() as p:
            for largura, escuro in ((390, True), (320, False)):
                tag = f"{largura} px {'escuro' if escuro else 'claro'}"
                if largura == 320:  # cada tamanho começa sem comparação
                    app.S.gravar_json(app.S.COMPARACOES, {})
                b, pg = await pagina(p, largura=largura, altura=844, escuro=escuro)
                await pg.goto(app.url)
                await espera(pg, "() => document.querySelector('.tabbar [data-view=\"ofertas\"]')")
                await pg.click('.tabbar [data-view="ofertas"]')
                await espera(pg, "() => document.querySelectorAll('#deals .deal').length === 3")
                cafe = pg.locator("#deals .deal", has_text="Café Pilão")
                bts = cafe.locator(".d-acts .hide-btn")
                check([x.strip() for x in await bts.all_inner_texts()] == ["Comparar preço", "Não mostrar"], f"{tag}: Comparar preço ao lado do Não mostrar")
                c0, c1 = await bts.nth(0).bounding_box(), await bts.nth(1).bounding_box()
                check(abs(c0["y"] - c1["y"]) < 2, f"{tag}: os dois na mesma linha ({c0['y']:.0f} e {c1['y']:.0f})")
                check(await cafe.locator(".cmp").count() == 0, f"{tag}: nada comparado ainda")

                # mais barato em outra loja
                await cafe.locator('[data-act="comparar"]').click()
                await espera(pg, "() => [...document.querySelectorAll('#deals [data-act=\"comparar\"]')].some(b => b.disabled && b.textContent === 'Comparando…')"
                                 " || document.querySelector('#deals .cmp')", 5000)
                await espera(pg, "() => document.querySelector('#deals .deal .cmp')", 20000)
                await espera(pg, "() => !document.getElementById('buscar').disabled")
                bloco = cafe.locator(".cmp")
                check(await txt(bloco.locator(".cmp-t")) == "Mais barato em outra loja", f"{tag}: Mais barato em outra loja ({await txt(bloco.locator('.cmp-t'))})")
                chips = [await txt(x) for x in await bloco.locator("li").all()]
                check(chips == ["Giassi R$ 19,90", "Angeloni R$ 23,50"], f"{tag}: as lojas, da mais barata para a mais cara ({chips})")
                check(await bloco.locator("li").nth(0).get_attribute("class") == "barato" and await bloco.locator("li").nth(1).get_attribute("class") is None,
                      f"{tag}: só a mais barata marcada")
                href = await bloco.locator("li a.i-chip").nth(0).get_attribute("href")
                check(href and href.startswith("http") and "giassi" in href and await bloco.locator("li a").nth(0).get_attribute("target") == "_blank",
                      f"{tag}: cada loja abre o produto ({href})")
                cor = await pg.evaluate("() => [getComputedStyle(document.querySelector('#deals .cmp-t')).color, getComputedStyle(document.querySelector('.off.num')).color]")
                check(cor[0] == cor[1], f"{tag}: o aviso na cor das ofertas ({cor})")
                check(await txt(cafe.locator('[data-act="comparar"]')) == "Comparar preço" and not await cafe.locator('[data-act="comparar"]').is_disabled(),
                      f"{tag}: o botão volta")
                await espera(pg, "() => /mais barato em Giassi/.test(document.getElementById('toast').textContent)", 5000)
                check(not await pg.locator("#toast").is_hidden(), f"{tag}: o aviso no fim ({await pg.text_content('#toast')})")
                check(await pg.evaluate(FORA) == [], f"{tag}: nada para fora da tela {await pg.evaluate(FORA)}")
                await cafe.screenshot(path=f"{SHOTS}/ecc-mais-barato-{largura}.png")

                # a oferta ganha
                nes = await comparar(pg, "Nescau", tag)
                check(await txt(nes.locator(".cmp-t")) == "Menor preço entre 3 lojas", f"{tag}: Menor preço entre 3 lojas")
                check([await txt(x) for x in await nes.locator(".cmp li").all()] == ["Angeloni R$ 8,99", "Giassi R$ 9,49"] and await nes.locator(".cmp li.barato").count() == 0,
                      f"{tag}: as outras lojas, sem marcar")
                # nada achado
                gel = await comparar(pg, "Geleia", tag)
                check(await txt(gel.locator(".cmp")) == "Não achei em outras lojas" and await gel.locator(".cmp ul").count() == 0, f"{tag}: Não achei em outras lojas")
                check([await txt(x) for x in await pg.locator("#deals .cmp-t").all()] == ["Mais barato em outra loja", "Menor preço entre 3 lojas", "Não achei em outras lojas"],
                      f"{tag}: cada oferta com a sua comparação")
                await pg.screenshot(path=f"{SHOTS}/ecc-ofertas-{largura}.png", full_page=True)

                # fica depois de recarregar; esconder a oferta esconde a comparação junto
                await pg.reload()
                await pg.click('.tabbar [data-view="ofertas"]')
                await espera(pg, "() => document.querySelectorAll('#deals .cmp').length === 3")
                check(True, f"{tag}: as três comparações ficam depois de recarregar")
                check(app.config_salva()["lista"] == [], f"{tag}: a lista não muda")
                check(not pg.erros, f"{tag}: sem erros na página {pg.erros}")
                await b.close()


asyncio.run(main())
resumo()
