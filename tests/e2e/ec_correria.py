# EconomIA 1.7.0: Mais › Configurações › Integrações › CorrerIA. Começa desligado; ligar grava o arquivo que o CorrerIA lê
# (share/economia/correria.json) e diz "Ligado."; o CorrerIA (Claude) põe um item pela ferramenta e a página avisa "pela
# CorrerIA" e mostra o item; o último uso aparece no quadro; recarregar não desliga; desligar apaga o arquivo e fecha a rota.
# Não depende da IA: com Usar IA desligado, o quadro continua.
import asyncio
import json
import os
import urllib.error
import urllib.request

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, abrir_mais, check, espera, pagina, resumo


def ferramenta(app, nome, argumentos=None, chave=None):
    if chave is None:
        with open(os.path.join(app.pasta, "share", "correria.json"), encoding="utf-8") as f:
            chave = json.load(f)["chave"]
    corpo = json.dumps({"nome": nome, "argumentos": argumentos or {}, "pessoa": {"id": "p1", "nome": "Ana"}, "cliente": "Claude"}).encode()
    req = urllib.request.Request(app.url + "api/integracao/ferramentas", data=corpo, method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + chave, "X-App": "CorrerIA"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


async def main():
    cfg = {"cep": CEP, "categorias": ["mercados"], "usar_ia": False, "lista": [{"produto": "Café Pilão 500 g", "compras": []}]}
    with App(cfg, buscar=False) as app:
        arq = os.path.join(app.pasta, "share", "correria.json")
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await abrir_mais(pg, "integracoes")
            card = pg.locator('section[aria-labelledby="h-correria"]')
            check(await card.is_visible(), "o quadro da CorrerIA aparece, mesmo com a IA desligada")
            check(await pg.text_content("#correriaTxt") == "Desligado." and not await pg.is_checked("#correria"), "começa desligado")
            check(not os.path.exists(arq), "desligado: sem arquivo")
            await pg.click("#correria")
            await espera(pg, "() => document.getElementById('correriaTxt').textContent === 'Ligado.'")
            await pg.wait_for_timeout(500)
            check(app.config_salva().get("correria") is True, "ligado e salvo")
            check(os.path.exists(arq), "ligar grava o arquivo que o CorrerIA lê")
            await card.screenshot(path=SHOTS + "/eccor-ligado.png")
            # o CorrerIA põe um item: a página avisa e mostra
            st, d = ferramenta(app, "por_na_lista", {"produto": "Pão de forma"})
            check(st == 200 and d["texto"].startswith("Pus Pão de forma na lista"), f"a ferramenta grava ({st} {d})")
            check(ferramenta(app, "lista", chave="errada")[0] == 401, "chave errada: 401")
            await pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
            await espera(pg, "() => /pela CorrerIA/.test(document.getElementById('toast').textContent)")
            check(await pg.text_content("#toast") == "Sua lista foi atualizada pela CorrerIA", "o aviso diz quem mudou")
            t = await pg.text_content("#correriaTxt")
            check(t.startswith("Ligado. Último uso: Claude, hoje "), f"o último uso no quadro ({t})")
            await pg.click('.tabbar [data-view="lista"]')
            check("Pão de forma" in await pg.text_content("#v-lista"), "o item aparece na Minha lista")
            # a página grava depois: o item fica e a CorrerIA continua ligada
            await pg.reload()
            await pg.wait_for_timeout(1200)
            await abrir_mais(pg, "integracoes")
            check(await pg.is_checked("#correria"), "recarregar não desliga")
            await pg.click("#correria")
            await espera(pg, "() => document.getElementById('correriaTxt').textContent === 'Desligado.'")
            await pg.wait_for_timeout(500)
            salvo = app.config_salva()
            check(salvo.get("correria") is False and "Pão de forma" in [i["produto"] for i in salvo["lista"]], "desligado e o item continua")
            check(not os.path.exists(arq), "desligar apaga o arquivo")
            check(ferramenta(app, "lista", chave="qualquer")[0] == 401, "desligado: a rota fecha")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
