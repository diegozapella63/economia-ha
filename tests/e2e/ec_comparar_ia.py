# EconomIA 1.36.0: Comparar com IA. O botão Comparar (ao lado de Completa/Resumida) deixa marcar as opções dos cartões (a
# melhor compra, as outras lojas, os tamanhos, os similares, de itens diferentes); o toque marca em vez de abrir o link;
# Comparar leva as escolhidas à Conversa, e a IA diz o que vale mais a pena (marca, rendimento, preço do que se aproveita).
# O Voltar do celular e Cancelar saem do Comparar. Lojas e preços inventados.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, App, HAFalso, categoria, check, espera, pagina, resumo, shot

OFERTAS = {"versao": 2, "gerado_em": "2026-11-02T10:00:00-03:00", "categorias": [
    categoria("mercados", [("merc-azul", "Mercado Azul", 0.8), ("merc-sol", "Atacado Sol", 3.0)])],
    "lista": [
        {"produto": "Peito de frango", "precos": {"merc-azul": 18.0, "merc-sol": 19.0}, "base": {"quantidade": 0.4, "unidade": "kg"},
         "tamanhos": [{"rede": "merc-sol", "embalagem": "Peito de frango com osso 1,5 kg", "quantidade": 1.5, "preco": 14.4}]},
        {"produto": "Filé de peito de frango", "precos": {"merc-azul": 13.0}, "base": {"quantidade": 1, "unidade": "kg"}}]}
PEDIDOS = []


def responde(corpo):
    PEDIDOS.append(corpo["instructions"])
    return {"resposta": "Leve o filé: sem osso, o quilo aproveitado sai mais barato.", "acoes": []}


def limpo(s):
    return " ".join(s.replace("\xa0", " ").split())


async def main():
    ha = HAFalso()
    ha.tarefa_ia("ai_task.busca", "Busca")
    ha.responde_ia("conversa", responde)
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados"], "ia": {"busca": "ai_task.busca"},
           "lista": [{"produto": "Peito de frango"}, {"produto": "Filé de peito de frango"}]}
    with App(cfg, buscar=False, antes=lambda S: S.gravar_json(S.OFERTAS, OFERTAS), ha=ha) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="lista"]')
            await pg.wait_for_timeout(400)
            btn = pg.locator("#cmpBtn")
            check(await btn.is_visible() and limpo(await btn.inner_text()) == "Comparar", "o botão Comparar ao lado de Completa e Resumida")
            caixas = [await pg.locator(s).bounding_box() for s in ("#visLista", "#cmpBtn")]
            check(abs(caixas[0]["y"] - caixas[1]["y"]) < 1 and abs(caixas[0]["height"] - caixas[1]["height"]) < 2, f"na mesma linha, da mesma altura ({caixas})")
            # ----- Voltar do celular sai do Comparar -----
            await btn.click()
            await pg.wait_for_timeout(200)
            check(await pg.locator("#cmpBar").is_visible() and limpo(await pg.locator("#cmpN").inner_text()) == "Toque nas opções: de 2 a 6.", "a barra do Comparar")
            check(await pg.locator("#cmpGo").is_disabled(), "Comparar só com 2 ou mais")
            await pg.go_back()
            await pg.wait_for_timeout(400)
            check(not await pg.locator("#cmpBar").is_visible() and await btn.get_attribute("aria-pressed") == "false", "o Voltar do celular sai do Comparar")
            check(await pg.locator("#wish").is_visible(), "e fica na Minha lista")
            # ----- marcar de dois itens: a melhor compra do frango e o filé -----
            await btn.click()
            await pg.wait_for_timeout(200)
            frango = pg.locator("#wish > li.item", has_text="Peito de frango").filter(has_not_text="Filé").first
            file_ = pg.locator("#wish > li.item", has_text="Filé de peito de frango").first
            paginas = len(b.contexts[0].pages)
            await frango.locator(".i-best").click()
            await pg.wait_for_timeout(200)
            check(len(b.contexts[0].pages) == paginas and pg.url.startswith(app.url), "o toque marca, sem abrir a loja")
            check(await frango.locator(".i-best[data-cmp-sel]").count() == 1, "a melhor compra marcada")
            await file_.locator(".i-best").click()
            await frango.locator(".i-others li").first.click()
            await pg.wait_for_timeout(200)
            check(limpo(await pg.locator("#cmpN").inner_text()) == "3 escolhidas" and not await pg.locator("#cmpGo").is_disabled(), "3 escolhidas")
            await frango.locator(".i-others li").first.click()  # desmarca
            await pg.wait_for_timeout(200)
            check(limpo(await pg.locator("#cmpN").inner_text()) == "2 escolhidas", "o toque de novo desmarca")
            check(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "nada passa da largura")
            await shot(pg, "comparar-marcando")
            # ----- Comparar: a conversa abre com as opções e a resposta da IA -----
            await pg.click("#cmpGo")
            await espera(pg, "() => document.querySelectorAll('.cm.ia:not(.pensando)').length === 1")
            eu = limpo(await pg.locator(".cm.eu").last.text_content())
            check(eu.startswith("Compare e diga o que vale mais a pena comprar:")
                  and "1. Peito de frango com osso 1,5 kg: R$ 14,40 (R$ 9,60/kg), em Atacado Sol" in eu
                  and "2. Filé de peito de frango, 1 kg: R$ 13,00 (R$ 13,00/kg), em Mercado Azul" in eu, f"a pergunta com as opções ({eu})")
            check(await pg.locator(".cm.ia").last.text_content() == "Leve o filé: sem osso, o quilo aproveitado sai mais barato.", "a resposta da IA")
            check(PEDIDOS and "Para comparar opções" in PEDIDOS[-1] and "quanto custa o que se aproveita" in PEDIDOS[-1], "a IA recebe como comparar")
            check(app.config_salva().get("lista") and not await pg.locator("#cmpBar").is_visible(), "o Comparar fecha ao ir para a conversa")
            await shot(pg, "comparar-conversa")
            # o Voltar fecha a conversa e não volta ao Comparar
            await pg.go_back()
            await pg.wait_for_timeout(400)
            check(await pg.locator("#chat").is_hidden() and not await pg.locator("#cmpBar").is_visible(), "o Voltar fecha a conversa")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
