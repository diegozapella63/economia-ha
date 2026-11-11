# EconomIA 1.12.0: Minha lista › o nome do item sugere enquanto a pessoa digita, a partir de 2 letras, logo abaixo da linha
# com os botões: primeiro o que já esteve na lista (o histórico), depois os nomes genéricos dos produtos vistos nas lojas,
# sem marca e sem tamanho ("arroz" → Arroz branco, Arroz integral…). Tocar numa preenche o campo; Adicionar fecha a lista;
# o que já está na lista não aparece. Marcas e produtos inventados.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, App, check, espera, pagina, resumo, shot

MARCAS = ["Pratinho", "Brilhux", "Tio Zeca"]
NOMES = ([f"Arroz Branco {m} Tipo 1 5kg" for m in MARCAS] + [f"Arroz Integral {m} 1kg" for m in MARCAS[:2]]
         + ["Arroz Parboilizado Pratinho 5kg", "Arroz Parboilizado Brilhux 1kg", "Arroz Tio Zeca Tipo 1 5kg", "Arroz Tio Zeca Agulhinha 2kg"]
         + ["Sabão em Pó Brilhux 1,6kg", "Sabão em Pó Pratinho 800g"])


def vocab(S):
    S.aprende_nomes(NOMES, MARCAS)
    S.grava_vocab()


async def opcoes(pg):
    return await pg.locator(".sug-box .sug-op").all_inner_texts()


async def digita(pg, texto):
    await pg.fill("#novoItem", "")
    await pg.locator("#novoItem").press_sequentially(texto, delay=30)


async def main():
    cfg = {"cep": CEP, "categorias": ["mercados"], "lista": [{"produto": "Arroz integral", "compras": []}],
           "historico": [{"produto": "Arroz cateto", "compras": ["2026-10-01", "2026-10-20"], "saiu": "2026-10-25"},
                         {"produto": "Feijão preto", "compras": ["2026-10-02"], "saiu": "2026-10-25"}]}
    with App(cfg, buscar=False, antes=vocab) as app:
        async with async_playwright() as p:
            for largura in (390, 320):
                b, pg = await pagina(p, largura, 844 if largura == 390 else 700)
                await pg.goto(app.url)
                await pg.wait_for_timeout(1200)
                await pg.click('.tabbar [data-view="lista"]')
                await pg.wait_for_timeout(300)
                await pg.click("#novoItem")
                check(await pg.locator(".sug-box").count() == 0, f"[{largura}] sem nada digitado, nenhuma sugestão")
                await digita(pg, "a")
                await pg.wait_for_timeout(400)
                check(await pg.locator(".sug-box").count() == 0, f"[{largura}] com uma letra, nenhuma")
                await digita(pg, "arroz")
                await espera(pg, "() => document.querySelectorAll('.sug-box .sug-op').length >= 3")
                ops = await opcoes(pg)
                check(ops[:3] == ["Arroz cateto", "Arroz branco", "Arroz parboilizado"] and "Arroz integral" not in ops and "Arroz agulhinha" in ops,
                      f"[{largura}] o do histórico primeiro, depois os das lojas, sem marca, e os da lista pronta (1.33.0); o Arroz integral já está na lista ({ops})")
                caixa = await pg.evaluate("""() => { const f = document.getElementById('addForm').getBoundingClientRect(), s = document.querySelector('.sug-box');
                  return { abaixo: s.getBoundingClientRect().top >= f.bottom - 6, depois: s.previousElementSibling.id, largura: Math.round(s.getBoundingClientRect().width),
                           cabe: document.documentElement.scrollWidth <= innerWidth }; }""")
                check(caixa["abaixo"] and caixa["depois"] == "addForm" and caixa["cabe"], f"[{largura}] a lista logo abaixo da linha do campo, sem passar da tela ({caixa})")
                await pg.wait_for_timeout(600)  # a rolagem até a lista
                vis = await pg.evaluate("() => { const s = document.querySelector('.sug-box').getBoundingClientRect(), t = document.querySelector('.tabbar').getBoundingClientRect(); return [Math.round(s.bottom), Math.round(t.top)]; }")
                check(vis[0] <= vis[1], f"[{largura}] a lista aparece inteira, acima da barra de baixo (e do teclado) ({vis})")
                await shot(pg, f"sugestoes-{largura}")
                # tocar numa preenche o campo e fecha
                await pg.locator(".sug-op", has_text="Arroz parboilizado").click()
                await pg.wait_for_timeout(500)
                check(await pg.input_value("#novoItem") == "Arroz parboilizado" and await pg.locator(".sug-box").count() == 0,
                      f"[{largura}] tocar preenche o campo e fecha a lista")
                # a palavra que está sendo digitada completa, com o acento das lojas
                await digita(pg, "sab")
                await espera(pg, "() => document.querySelectorAll('.sug-box .sug-op').length >= 2")
                check((await opcoes(pg))[:2] == ["Sabão", "Sabão em pó"], f"[{largura}] sab → Sabão, Sabão em pó, depois a lista pronta ({await opcoes(pg)})")
                await pg.locator(".sug-op", has_text="Sabão em pó").click()
                item = f"Sabão em pó {1 if largura == 390 else 2} kg"  # o tamanho a pessoa escreve depois
                await pg.locator("#novoItem").press_sequentially(item[len("Sabão em pó"):], delay=30)
                await pg.wait_for_timeout(500)
                await pg.click('#addForm button[type="submit"]')
                await pg.wait_for_timeout(500)
                check(await pg.locator(".sug-box").count() == 0, f"[{largura}] Adicionar fecha a lista")
                lista = [i["produto"] for i in app.config_salva()["lista"]]
                check(item in lista, f"[{largura}] e o item entra ({lista})")
                # o que entrou na lista sai das sugestões; o que saiu da lista (o histórico) aparece
                await digita(pg, "sabão em")
                await espera(pg, "() => document.querySelectorAll('.sug-box .sug-op').length >= 1")
                check(item not in await opcoes(pg), f"[{largura}] o que já está na lista não é sugerido ({await opcoes(pg)})")
                await b.close()
    resumo()


asyncio.run(main())
