# EconomIA 0.19.0: o botão Buscar com o Home Assistant falso: do exemplo para as ofertas do CEP, o andamento enquanto a IA
# pensa ("Buscando mercados…", botão girando), "Busca concluída, com 1 chamada de IA", os preços na lista (o do site vale
# mais), a cota da IA acabando (mensagem de erro, o resultado anterior fica), "Buscar este item" e Buscar sem CEP.
import asyncio
import threading

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, Erro, HAFalso, check, espera, pagina, prod, resumo


def prepara(lojas):
    lojas.catalogo["giassi"] = [prod("Coxinha da Asa de Frango Resfriada Kg", 21.90, "Açougue/Aves", "kg", 1)]


async def item(pg, nome):
    return (await pg.locator("#wish > li.item", has_text=nome).first.inner_text()).replace("\xa0", " ")


async def main():
    ha = HAFalso()
    solta = threading.Event()

    def mercados(corpo):
        solta.wait(30)
        return {"lojas": [{"rede": "Giassi", "distancia_km": 1.0}, {"rede": "Bistek", "distancia_km": 2.0}],
                "lista": [{"item": 1, "precos": [{"rede": "Giassi", "preco": 25.0}]}, {"item": 2, "precos": [{"rede": "Bistek", "preco": 8.9}]}]}
    ha.responde_ia("EconomIA: mercados", mercados, vezes=1)
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados"], "lista": [{"produto": "Coxinha da asa"}, {"produto": "Abacaxi pérola"}],
           "opcoes": {"itens_sem_preco": False}}
    with App(cfg, buscar=False, preparar=prepara, ha=ha, servicos=True) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            check("Salve o CEP em Mais › Casa e toque em Buscar" in await pg.text_content("#bannerTxt"), "sem busca ainda: o exemplo, com o aviso")
            check(await pg.text_content("#syncText") == "Nenhuma busca ainda", "nenhuma busca ainda")
            await pg.click('.tabbar [data-view="lista"]')
            await pg.click("#buscar")
            await espera(pg, "() => /Buscando mercados/.test(document.getElementById('buscaMsg').textContent)")
            msg = await pg.text_content("#buscaMsg")
            check(msg == "Buscando mercados. Leva alguns minutos; pode continuar usando o painel.", f"andamento enquanto a IA pensa ({msg})")
            check(await pg.is_disabled("#buscar") and await pg.text_content("#buscarTxt") == "Buscando", "o botão fica Buscando, desligado")
            check(await pg.locator("#buscar .ic-gira").is_visible() and await pg.locator("#buscar .ic-busca").is_hidden(), "o ícone gira")
            await pg.locator("#views").screenshot(path=SHOTS + "/ecb-botao-girando.png")
            await pg.screenshot(path=SHOTS + "/ecb-buscando.png")
            solta.set()
            await espera(pg, "() => /Busca concluída/.test(document.getElementById('buscaMsg').textContent)", 20000)
            check(await pg.text_content("#buscaMsg") == "Busca concluída, com 1 chamada de IA.", f"concluída ({await pg.text_content('#buscaMsg')})")
            check(not await pg.is_disabled("#buscar") and await pg.text_content("#buscarTxt") == "Buscar", "o botão volta")
            await espera(pg, "() => /Última busca/.test(document.getElementById('syncText').textContent)")
            check(await pg.locator("#banner").is_hidden(), "o exemplo sai")
            cox = await item(pg, "Coxinha da asa")
            check("R$ 21,90" in cox and "Giassi" in cox and "R$ 25,00" not in cox, "o preço do site vale mais que o da busca na web")
            check("R$ 8,90" in await item(pg, "Abacaxi") and "Bistek" in await item(pg, "Abacaxi"), "o abacaxi pela IA")
            await pg.locator("#wish").screenshot(path=SHOTS + "/ecb-lista.png")
            # cota da IA: a mensagem fica, o resultado anterior também
            ha.responde_ia("EconomIA: mercados", Erro(429, "Too Many Requests"))
            await pg.click("#buscar")
            await espera(pg, "() => document.getElementById('buscaMsg').classList.contains('err')", 20000)
            erro = await pg.text_content("#buscaMsg")
            check(erro.startswith("A cota da IA acabou: ela recusou por excesso de pedidos (erro 429)."), f"erro de cota ({erro[:80]})")
            check("R$ 8,90" in await item(pg, "Abacaxi"), "o resultado anterior continua")
            # Buscar este item
            ha.regras_ia.clear()
            ha.responde_ia("itens sem preço", {"lista": [{"item": 1, "precos": [{"rede": "Bistek", "categoria": "mercados", "preco": 2.49}]}]})
            await pg.fill("#novoItem", "Detergente Ypê neutro")
            await pg.click('#addForm button[type="submit"]')
            await pg.wait_for_timeout(800)
            det = pg.locator("#wish > li.item", has_text="Detergente Ypê neutro")
            check("SEM PREÇO AINDA" in (await det.inner_text()).upper(), "item novo sem preço")
            # cada texto do aviso fica anotado: a busca de um item é rápida e o aviso seguinte pode chegar logo
            await pg.evaluate("""() => { window._avisos = []; const t = document.getElementById('toast');
                new MutationObserver(() => window._avisos.push(t.textContent)).observe(t, {childList: true, characterData: true, subtree: true}); }""")
            await det.locator(".i-busca").click()
            try:
                await espera(pg, "() => window._avisos.some(a => a.includes('Procurando o preço de Detergente Ypê neutro'))", 5000)
                avisou = True
            except Exception:  # noqa: BLE001
                avisou = False
            check(avisou, f"avisa que está procurando ({await pg.evaluate('window._avisos')})")
            await espera(pg, "() => /R\\$\\s2,49/.test((document.querySelector('#wish') || {}).textContent || '')", 20000)
            check("Bistek" in await item(pg, "Detergente Ypê neutro"), "o item ganhou preço sem uma busca completa")
            pedido = ha.chamadas_ia[-1]["instructions"]
            check("1) Detergente Ypê neutro" in pedido and "Coxinha" not in pedido, "a IA só pergunta desse item")
            # sem CEP: vai para Mais › Casa
            st = app.api("GET", "api/estado")
            app.api("PUT", "api/config", dict(st["config"], cep=""))
            await pg.reload()
            await pg.wait_for_timeout(1200)
            await pg.click("#buscar")
            await pg.wait_for_timeout(300)
            check(await pg.text_content("#toast") == "Salve o CEP antes de buscar." and await pg.locator("#mp-casa").is_visible(), "sem CEP: pede para salvar, em Mais › Casa")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
