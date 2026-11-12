# EconomIA 1.36.9: sem o ritmo de compra do item (ainda não aprendido), quanto um tamanho dura vem do tamanho da casa
# (Mais › Casa › Quem mora): por semana, o de sempre por pessoa. Com o Espaço para estoque, uma caixa de 18 kg de frango
# não é sugerida a 2 pessoas que compram para o mês. O Espaço para estoque ganha "Só o do mês: até 1 mês". Lojas e preços
# inventados.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, App, abrir_mais, categoria, check, pagina, resumo, shot

OFERTAS = {"versao": 2, "gerado_em": "2026-11-02T10:00:00-03:00", "categorias": [
    categoria("mercados", [("merc-azul", "Mercado Azul", 0.8), ("merc-sol", "Atacado Sol", 3.0)])],
    "lista": [
        {"produto": "Peito de frango", "precos": {"merc-azul": 15.98, "merc-sol": 16.9}, "base": {"quantidade": 0.4, "unidade": "kg"},
         "tamanhos": [{"rede": "merc-sol", "embalagem": "Peito de frango caixa 18 kg", "quantidade": 18, "preco": 214.2},
                      {"rede": "merc-azul", "embalagem": "Peito de frango bandeja 1 kg", "quantidade": 1, "preco": 16.9},
                      {"rede": "merc-sol", "embalagem": "Peito de frango 2 kg", "quantidade": 2, "preco": 29.8}]}]}


def limpo(s):
    return " ".join(s.replace("\xa0", " ").split())


async def main():
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados"], "perfil": {"adultos": 2}, "cotidiano": {"estoque": "pouco"},
           "lista": [{"produto": "Peito de frango"}]}
    with App(cfg, buscar=False, antes=lambda S: S.gravar_json(S.OFERTAS, OFERTAS)) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(400)
            frango = pg.locator("#wish > li.item", has_text="Peito de frango").first
            best = limpo(await frango.locator(".i-best").inner_text())
            check("Peito de frango 2 kg por R$ 29,80 · Atacado Sol" in best and "18 kg" not in best, f"2 pessoas, 2 meses de estoque: sem a caixa de 18 kg ({best})")
            await frango.locator("details.i-det").first.evaluate("d => { d.open = true; }")
            nt = limpo(await frango.locator(".i-tam").first.inner_text())
            check("Sai R$ 14,90/kg, contra R$ 16,90/kg no próximo mais barato (Peito de frango bandeja 1 kg, Mercado Azul)." in nt, f"o próximo depois dele, não a caixa que ficou de fora ({nt})")
            check("Para 2 pessoas, dura uns 18 dias." in nt and "Peito de frango caixa 18 kg sai ainda mais barato, mas duraria uns 5 meses para 2 pessoas, mais do que você costuma guardar." in nt,
                  f"quanto dura, pelo tamanho da casa ({nt})")
            # 1.36.11: a caixa sai do Comparar tamanhos e fica em Desconsiderados (n), recolhido logo abaixo
            tam = frango.locator("details.i-det:not(.i-fora)").first
            check((await tam.locator("summary").inner_text()).strip().endswith("Comparar tamanhos (4)") and await tam.locator(".tam-list li", has_text="18 kg").count() == 0,
                  "o Comparar tamanhos sem a caixa de 18 kg")
            fora = frango.locator("details.i-fora")
            check(await fora.count() == 1 and limpo(await fora.locator("summary").inner_text()) == "Desconsiderados (1)" and not await fora.evaluate("d => d.open"),
                  "Desconsiderados (1), recolhido")
            check(await fora.evaluate("d => d.previousElementSibling && d.previousElementSibling.matches('details.i-det')"), "logo abaixo do Comparar tamanhos")
            await fora.locator("summary").click()
            await pg.wait_for_timeout(200)
            check(limpo(await fora.locator(".i-sub").inner_text()) == "Duram mais que o seu estoque (até 2 meses, para 2 pessoas)."
                  and await fora.locator(".tam-list li", has_text="caixa 18 kg").count() == 1, "dentro, a caixa e o porquê")
            await frango.screenshot(path=__import__("os").path.join(__import__("base_e2e").SHOTS, "estoque-frango.png"))
            # dá para escolher a caixa mesmo assim (deu vontade): vira Sua escolha e volta para o Comparar tamanhos
            await fora.locator(".tam-list li", has_text="caixa 18 kg").locator(".esc-btn").click()
            await pg.wait_for_timeout(800)
            e = next(i for i in app.config_salva()["lista"] if i["produto"] == "Peito de frango").get("escolha")
            check(e and e.get("q") == 18, f"escolher a caixa fica salvo ({e})")
            frango = pg.locator("#wish > li.item", has_text="Peito de frango").first
            check("SUA ESCOLHA" in limpo(await frango.locator(".i-best").inner_text()).upper() and await frango.locator("details.i-fora").count() == 0, "vira Sua escolha")
            await frango.locator("[data-desescolher]").click()
            await pg.wait_for_timeout(700)
            # ----- Só o do mês -----
            await abrir_mais(pg, "casa")
            ops = [limpo(x) for x in await pg.locator("#estoque option").all_inner_texts()]
            check(ops == ["Só o do mês: até 1 mês de estoque", "Pouco: até 2 meses", "Normal: até 6 meses", "Bastante: até 1 ano"], f"o espaço para estoque ({ops})")
            await pg.select_option("#estoque", "mes")
            await pg.wait_for_timeout(600)
            check(app.config_salva()["cotidiano"]["estoque"] == "mes", "Só o do mês fica guardado")
            await pg.fill("#pAdultos", "1")
            await pg.locator("#pAdultos").dispatch_event("change")
            await pg.wait_for_timeout(600)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(400)
            frango = pg.locator("#wish > li.item", has_text="Peito de frango").first
            best = limpo(await frango.locator(".i-best").inner_text())
            check("Peito de frango bandeja 1 kg por R$ 16,90" in best, f"1 pessoa, 1 mês: o de 2 kg duraria uns 35 dias, mais que o mês; fica a bandeja de 1 kg ({best})")
            await pg.reload()
            await pg.wait_for_timeout(1200)
            await shot(pg, "estoque-lista")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
