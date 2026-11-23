# EconomIA 1.52.0: Mais › Configurações › Integrações › Memória da IA. Uma memória só, da casa, compartilhada por todos os
# apps (fica em share/familia/memoria_ia.json, fora do app): o quadro vem antes do Falar e diz isso; o que outro app escreveu
# aparece; escrever uma frase põe na lista e no arquivo; apagar tira; com Usar IA desligado, o quadro some.
import asyncio
import json
import os

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, abrir_mais, check, espera, pagina, resumo, shot


async def main():
    cfg = {"cep": CEP, "categorias": ["mercados"], "usar_ia": True, "lista": [{"produto": "Café Pilão 500 g", "compras": []}]}
    with App(cfg, buscar=False) as app:
        arq = os.path.join(app.pasta, "familia", "memoria_ia.json")
        os.makedirs(os.path.dirname(arq), exist_ok=True)
        with open(arq, "w", encoding="utf-8") as f:   # o que outro app da casa já escreveu
            json.dump({"versao": 1, "lista": [{"id": "r1", "texto": "A feira é no sábado", "em": "2026-11-02T09:30:00-0300", "app": "ResolvIA"}]}, f)
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await abrir_mais(pg, "integracoes")
            card = pg.locator("#memoriaIa")
            await espera(pg, "() => document.querySelectorAll('#memLista li').length === 1")
            check(await card.is_visible(), "o quadro Memória da IA aparece")
            check(" ".join((await card.locator("h2").text_content()).split()) == "Memória da IA", "com o título Memória da IA")
            check("Uma memória só, da casa, compartilhada por todos os apps" in await card.locator(".sec-meta").text_content(), "diz que é compartilhada")
            ordem = await pg.evaluate("[...document.querySelectorAll('section.panel.settings')].filter(s => s.offsetParent).map(s => s.getAttribute('aria-labelledby'))")
            check("h-memoria" in ordem and ordem.index("h-falar") == ordem.index("h-memoria") + 1, f"logo antes do Falar, depois do IA ({ordem})")
            linha = await pg.locator("#memLista li").first.text_content()
            check("A feira é no sábado" in linha and "ResolvIA" in linha, "o que outro app escreveu aparece, com o app")
            check(await card.locator("h2 svg").count() >= 1 and await card.locator("#memSalvar svg").count() == 1, "o título e o botão com ícone")
            alturas = await pg.evaluate("[document.getElementById('memTexto').getBoundingClientRect().height, document.getElementById('memSalvar').getBoundingClientRect().height].map(Math.round)")
            check(alturas == [50, 50], f"o campo e o botão com a altura da família ({alturas})")
            check(await pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "nada sai da tela")
            await card.scroll_into_view_if_needed()
            await shot(pg, "memoria-ia")
            await pg.fill("#memTexto", "O café é sempre o da marca azul")
            await pg.click("#memSalvar")
            await espera(pg, "() => document.querySelectorAll('#memLista li').length === 2")
            check(await pg.input_value("#memTexto") == "", "o campo fica vazio para a próxima")
            with open(arq, encoding="utf-8") as f:
                lista = json.load(f)["lista"]
            check([(x["texto"], x["app"]) for x in lista] == [("A feira é no sábado", "ResolvIA"), ("O café é sempre o da marca azul", "EconomIA")], "e fica na pasta share, para todos os apps")
            await pg.click("#memSalvar")
            await espera(pg, "() => /Escreva o que é para lembrar/.test(document.body.innerText)")
            await pg.locator("#memLista .mem-del").nth(1).click()
            await espera(pg, "() => document.querySelectorAll('#memLista li').length === 1")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
