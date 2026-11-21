# EconomIA 1.46.0: Reposição. Mais › Reposição guarda o que se compra de tempos em tempos, cada item com o seu "A cada"
# (dias, semanas ou meses). Na hora, o item aparece no cartão Hora de repor, no alto da Minha lista, com Pôr na lista e
# Já tenho (os dois recomeçam a contagem). Em Opções › Reposição, as chaves Remédios do CronologIA e Consumíveis do
# InventarIA (desligadas de início) deixam escolher o item desses apps. Casa inventada; 390 px escuro, 320 px claro e o
# computador, sem nada passando da largura.
import asyncio
import datetime
import json
import os
import zoneinfo

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, abrir_mais, check, espera, pagina, resumo
from test_reposicao import InventarioFalso

HOJE = datetime.datetime.now(zoneinfo.ZoneInfo("America/Sao_Paulo")).date()
dia = lambda n: (HOJE + datetime.timedelta(days=n)).isoformat()


def mais_meses(d, n):
    """O mesmo dia, n meses depois (ou o último dia desse mês), como a página."""
    m = d.month - 1 + n
    ano, mes = d.year + m // 12, m % 12 + 1
    fim = (datetime.date(ano + mes // 12, mes % 12 + 1, 1) - datetime.timedelta(days=1)).day
    return datetime.date(ano, mes, min(d.day, fim))


def config():
    return {"cep": CEP, "raio_km": 5, "categorias": ["mercados"], "lista": [{"produto": "Leite integral"}],
            "reposicao": [{"id": "aaaa1", "nome": "Filtro de água", "cada": 6, "unidade": "mes", "desde": dia(-200)},
                          {"id": "bbbb2", "nome": "Leite integral", "cada": 1, "unidade": "semana", "desde": dia(-7)},
                          {"id": "cccc3", "nome": "Ração 15 kg", "cada": 30, "unidade": "dia", "desde": dia(-10)}]}


def casa(app, inv):
    """Os outros apps na pasta share da casa: o CronologIA com dois remédios e o InventarIA (de mentira) com dois consumíveis."""
    raiz = os.path.dirname(os.path.join(app.pasta, "share"))
    for nome, dado in (("cronologia", {"app": "CronologIA", "versao": "1.106.0", "remedios": [{"nome": "Vitamina D", "dose": "1 cápsula", "vezes": 1},
                                                                                           {"nome": "Antialérgico", "dose": "", "vezes": 2}]}),
                       ("inventario", {"url": inv.url, "chave": inv.chave})):
        os.makedirs(os.path.join(raiz, nome), exist_ok=True)
        with open(os.path.join(raiz, nome, "integracao.json"), "w", encoding="utf-8") as f:
            json.dump(dado, f)


async def tocar(pg, sel):
    loc = pg.locator(sel).first
    await loc.scroll_into_view_if_needed()
    bx = await loc.bounding_box()
    await pg.touchscreen.tap(bx["x"] + bx["width"] / 2, bx["y"] + bx["height"] / 2)
    await pg.wait_for_timeout(450)


LINHAS = "() => [...document.querySelectorAll('#repLista .hist-row')].map((l) => [l.querySelector('b').textContent, l.querySelector('small').textContent])"
VEZ = "() => [...document.querySelectorAll('#repAgoraLista .rep-vez')].map((l) => [l.querySelector('b').textContent, l.querySelector('small').textContent])"
FORA = "() => document.documentElement.scrollWidth - innerWidth"


async def aviso(pg):
    await pg.wait_for_timeout(250)
    return (await pg.locator("#toast").inner_text()).strip()


async def tudo(p, inv):
    """390 px, do começo ao fim."""
    with App(config(), buscar=False) as app:
        casa(app, inv)
        b, pg = await pagina(p)
        await pg.goto(app.url)
        await pg.wait_for_timeout(1200)
        # ---- a Minha lista: o cartão Hora de repor
        cartao = pg.locator("#repAgora")
        check(await cartao.is_visible() and (await pg.locator("#h-repagora").inner_text()).strip() == "Hora de repor"
              and await pg.locator("#h-repagora .h-ic svg").count() == 1, "o cartão Hora de repor na Minha lista, com o ícone")
        check((await pg.locator("#repAgoraN").inner_text()).strip().lower() == "2 itens", "a contagem: 2 itens")
        vez = await pg.evaluate(VEZ)
        check(vez == [["Filtro de água", "A cada 6 meses"], ["Leite integral", "A cada 1 semana · já está na lista"]], f"só o que está na hora, o mais atrasado primeiro ({vez})")
        ordem = await pg.evaluate("() => [...document.querySelectorAll('#v-lista > section')].filter((s) => s.getClientRects().length).map((s) => s.id || s.getAttribute('aria-labelledby') || s.className)")
        check(ordem.index("repAgora") < ordem.index("h-lista"), f"antes dos Itens da lista ({ordem})")
        bt = await pg.evaluate("() => [...document.querySelectorAll('#repAgoraLista .rep-vez:first-child button')].map((x) => { const r = x.getBoundingClientRect(); return [x.textContent.trim(), Math.round(r.width), Math.round(r.height), Math.round(r.top), !!x.querySelector('svg')]; })")
        check([x[0] for x in bt] == ["Pôr na lista", "Já tenho"] and abs(bt[0][1] - bt[1][1]) <= 1 and bt[0][2] == bt[1][2] == 50 and bt[0][3] == bt[1][3] and bt[0][4] and bt[1][4],
              f"Pôr na lista e Já tenho lado a lado, do mesmo tamanho, com 50 px e o ícone ({bt})")
        check(await pg.evaluate(FORA) <= 0, "nada passa da largura")
        await cartao.screenshot(path=f"{SHOTS}/ec-reposicao-agora-390.png")
        # Já tenho: sai do cartão e a contagem recomeça hoje
        await pg.click('[data-rep-tenho="bbbb2"]')
        check("Leite integral" in await aviso(pg) and "em 7 dias" in await aviso(pg), f"Já tenho: o aviso diz quando volta ({await aviso(pg)})")
        await espera(pg, "() => document.querySelectorAll('#repAgoraLista .rep-vez').length === 1")
        check((await pg.locator("#repAgoraN").inner_text()).strip().lower() == "1 item", "ficou 1 item")
        await espera(pg, "() => true")
        await pg.wait_for_timeout(400)
        salvo = {r["id"]: r for r in app.config_salva()["reposicao"]}
        check(salvo["bbbb2"]["desde"] == dia(0) and salvo["aaaa1"]["desde"] == dia(-200), f"guardado: o tempo do leite conta de hoje ({salvo['bbbb2']})")
        # Pôr na lista: entra na lista, o cartão some
        await pg.click('[data-rep-por="aaaa1"]')
        check("entrou na lista" in await aviso(pg), f"Pôr na lista: o aviso ({await aviso(pg)})")
        check(await cartao.is_hidden(), "nada mais na hora: o cartão some")
        await pg.wait_for_timeout(400)
        c = app.config_salva()
        check([i["produto"] for i in c["lista"]] == ["Leite integral", "Filtro de água"] and {r["id"]: r["desde"] for r in c["reposicao"]}["aaaa1"] == dia(0),
              f"o item entrou na lista e o tempo dele recomeçou ({[i['produto'] for i in c['lista']]})")
        check("Filtro de água" in await pg.locator("#wish").inner_text(), "e aparece nos Itens da lista")
        # ---- Mais › Reposição
        await pg.click('.tabbar [data-view="mais"]')
        linhas = await pg.evaluate("() => [...document.querySelectorAll('#maisMenu .menu-row')].map((r) => [r.dataset.mais, r.querySelector('.mb b').textContent, r.querySelector('.mb > span').textContent, !!r.querySelector('.h-ic svg')])")
        check(linhas[2] == ["reposicao", "Reposição", "O que comprar de novo de tempos em tempos.", True] and [x[0] for x in linhas] == ["casa", "lojas", "reposicao", "config", "sobre"],
              f"Reposição no menu de Mais, depois de Lojas ({linhas})")
        await pg.click('#maisMenu [data-mais="reposicao"]')
        await espera(pg, "() => history.state && history.state.tela === 'reposicao'")
        check((await pg.locator("#screenTitle").inner_text()).strip() == "Reposição" and await pg.locator("#mp-reposicao").is_visible()
              and await pg.locator("#maisAbas").is_hidden(), "a tela Reposição, sem as abas de Configurações")
        ls = await pg.evaluate(LINHAS)
        check(ls == [["Leite integral", "A cada 1 semana · em 7 dias"], ["Ração 15 kg", "A cada 30 dias · em 20 dias"], ["Filtro de água", "A cada 6 meses · em " + mais_meses(HOJE, 6).strftime("%d/%m")]],
              f"os itens, do que volta antes para o que volta depois ({ls})")
        check(await pg.locator("#repFonte").is_hidden(), "sem as chaves de Opções, nada de escolher de outro app")
        check(await pg.evaluate("() => { const b = [...document.querySelectorAll('#repForm button')].filter((x) => x.getClientRects().length); return b.length === 1 && b[0].textContent.trim() === 'Adicionar' && !!b[0].querySelector('svg') && Math.round(b[0].getBoundingClientRect().height) === 50; }"),
              "o Adicionar, com o ícone e 50 px")
        # o que não vale
        await pg.click("#repSalvar")
        check(await aviso(pg) == "Escreva o item.", "sem nome: pede o item")
        await pg.fill("#repNome", "ração 15 KG")
        await pg.click("#repSalvar")
        check("já está na reposição" in await aviso(pg), f"o mesmo item duas vezes: não ({await aviso(pg)})")
        await pg.fill("#repCada", "0")
        await pg.fill("#repNome", "Sabão em pó")
        await pg.click("#repSalvar")
        check(await aviso(pg) == "A cada quanto? De 1 a 365.", "A cada 0: não")
        # um item digitado, a cada 2 semanas
        await pg.fill("#repCada", "2")
        await tocar(pg, "#repUn")
        check([t.strip() for t in await pg.locator(".ss-wrap.in .ss-opt").all_inner_texts()] == ["dias", "semanas", "meses"], "dias, semanas ou meses, na janela do app")
        await tocar(pg, ".ss-opt >> nth=1")
        await pg.click("#repSalvar")
        check("Sabão em pó" in await aviso(pg) and "em 14 dias" in await aviso(pg), f"adicionado: o aviso diz quando volta ({await aviso(pg)})")
        ls = await pg.evaluate(LINHAS)
        check(["Sabão em pó", "A cada 2 semanas · em 14 dias"] in ls and len(ls) == 4 and await pg.input_value("#repNome") == "" and await pg.input_value("#repCada") == "30",
              f"entrou na lista da tela e o campo ficou limpo ({ls})")
        await pg.wait_for_timeout(400)
        novo = [r for r in app.config_salva()["reposicao"] if r["nome"] == "Sabão em pó"][0]
        check((novo["cada"], novo["unidade"], novo["desde"], "origem" in novo) == (2, "semana", dia(0), False), f"guardado ({novo})")
        # ---- Opções › Reposição: as chaves
        await abrir_mais(pg, "opcoes")
        await espera(pg, "() => document.getElementById('opRepCronSt').textContent !== ''")
        sec = pg.locator('section[aria-labelledby="h-oprep"]')
        await sec.scroll_into_view_if_needed()
        tit = await sec.evaluate("(s) => [...s.querySelectorAll('.set-t')].map((t) => [t.textContent.trim(), !!t.querySelector('svg')])")
        check(tit == [["Remédios do CronologIA", True], ["Consumíveis do InventarIA", True]] and (await pg.locator("#h-oprep").inner_text()).strip() == "Reposição",
              f"Opções › Reposição: as duas chaves, cada uma com o ícone ({tit})")
        check(not await pg.is_checked("#opRepCron") and not await pg.is_checked("#opRepInv")
              and [(await pg.locator(i).inner_text()).strip() for i in ("#opRepCronSt", "#opRepInvSt")] == ["Desligado.", "Desligado."], "desligadas de início")
        check(inv.pedidos == [], "desligado, o InventarIA nem é chamado")
        await pg.click("#opRepCron")
        await espera(pg, "() => document.getElementById('opRepCronSt').textContent === '2 remédios.'")
        check(await pg.get_attribute("#opRepCronSt", "class") == "ia-st ok" and await pg.get_attribute("#opRepInvSt", "class") == "ia-st", "Remédios do CronologIA ligado: 2 remédios., com o ponto aceso")
        await pg.click("#opRepInv")
        await espera(pg, "() => document.getElementById('opRepInvSt').textContent === '2 consumíveis.'")
        check(inv.pedidos and inv.pedidos[-1][1] == "Bearer " + inv.chave, "Consumíveis do InventarIA ligado: 2 consumíveis., pedidos com a chave")
        check(await pg.evaluate(FORA) <= 0, "Opções: nada passa da largura")
        await sec.screenshot(path=f"{SHOTS}/ec-reposicao-opcoes-390.png")
        check(app.config_salva()["repor"] == {"cronologia": True, "inventario": True}, "as chaves ficam guardadas")
        # ---- escolher de outro app
        await abrir_mais(pg, "reposicao")
        await espera(pg, "() => !document.getElementById('repFonte').hidden")
        await tocar(pg, "#repFonte")
        folha = pg.locator(".ss-wrap.in .ss-sheet")
        grupos = [(t or "").strip() for t in await folha.locator(".ss-group").all_text_contents()]
        ops = [t.strip() for t in await folha.locator(".ss-opt").all_inner_texts()]
        check(grupos == ["Remédios do CronologIA", "Consumíveis do InventarIA"]
              and ops == ["Escolher de outro app", "Vitamina D · 1 cápsula", "Antialérgico", "Pasta térmica · Informática", "Pilhas AA"], f"a janela do app, com os remédios e os consumíveis ({grupos} {ops})")
        await pg.screenshot(path=f"{SHOTS}/ec-reposicao-escolher-390.png")
        await tocar(pg, ".ss-opt >> nth=1")
        check(await pg.input_value("#repNome") == "Vitamina D" and await pg.input_value("#repFonte") == "", "escolher põe o nome no campo")
        await pg.fill("#repCada", "2")
        await tocar(pg, "#repUn")
        await tocar(pg, ".ss-opt >> nth=2")
        await pg.click("#repSalvar")
        await pg.wait_for_timeout(500)
        vit = [r for r in app.config_salva()["reposicao"] if r["nome"] == "Vitamina D"][0]
        check((vit["cada"], vit["unidade"], vit.get("origem")) == (2, "mes", "cronologia"), f"guardado com o app de onde veio ({vit})")
        check(await pg.evaluate("() => [...document.querySelectorAll('#repLista .hist-row')].filter((l) => l.querySelector('.rep-de')).map((l) => l.querySelector('.rep-de').textContent)") == ["CronologIA"],
              "a linha diz de qual app é")
        await tocar(pg, "#repFonte")
        ops = [t.strip() for t in await pg.locator(".ss-wrap.in .ss-opt").all_inner_texts()]
        check("Vitamina D · 1 cápsula" not in ops and len(ops) == 4, f"o que já está na reposição sai da escolha ({ops})")
        await tocar(pg, ".ss-opt >> nth=3")
        check(await pg.input_value("#repNome") == "Pilhas AA", "um consumível do InventarIA")
        check((await pg.input_value("#repCada"), await pg.input_value("#repUn")) == ("6", "mes"), "1.46.3: o A cada já vem com a duração estimada do InventarIA (180 dias = 6 meses)")
        await pg.fill("#repNome", "Pilhas AAA")
        await pg.click("#repSalvar")
        await pg.wait_for_timeout(500)
        pil = [r for r in app.config_salva()["reposicao"] if r["nome"] == "Pilhas AAA"][0]
        check("origem" not in pil, f"o nome mudado à mão deixa de ser o do outro app ({pil})")
        # ---- editar e apagar
        await pg.click(f'#repLista [data-rep="{vit["id"]}"]')
        check(await pg.input_value("#repNome") == "Vitamina D" and await pg.input_value("#repCada") == "2" and await pg.input_value("#repUn") == "mes"
              and (await pg.locator("#repSalvar").inner_text()).strip() == "Salvar" and await pg.locator("#repCancelar").is_visible(), "tocar no item abre para editar, com Salvar e Cancelar")
        bt = await pg.evaluate("() => ['repSalvar', 'repCancelar'].map((i) => { const r = document.getElementById(i).getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height), Math.round(r.top)]; })")
        check(abs(bt[0][0] - bt[1][0]) <= 1 and bt[0][1:] == bt[1][1:] and await pg.evaluate("() => !!document.querySelector('#repCancelar svg')"), f"Salvar e Cancelar lado a lado, iguais ({bt})")
        await pg.click("#repCancelar")
        check(await pg.input_value("#repNome") == "" and (await pg.locator("#repSalvar").inner_text()).strip() == "Adicionar", "Cancelar volta ao Adicionar")
        await pg.click(f'#repLista [data-rep="{vit["id"]}"]')
        await pg.fill("#repCada", "3")
        await pg.click("#repSalvar")
        await pg.wait_for_timeout(500)
        vit2 = [r for r in app.config_salva()["reposicao"] if r["nome"] == "Vitamina D"][0]
        check((vit2["id"], vit2["cada"], vit2["desde"], vit2.get("origem")) == (vit["id"], 3, vit["desde"], "cronologia"), f"editado: o mesmo item, a cada 3 meses, sem recomeçar o tempo ({vit2})")
        n = await pg.locator("#repLista .hist-row").count()
        await pg.click(f'#repLista [data-rep-rm="{pil["id"]}"]')
        check("saiu da reposição" in await aviso(pg) and await pg.locator("#repLista .hist-row").count() == n - 1, "Apagar tira da reposição")
        await pg.wait_for_timeout(400)
        check("Pilhas AAA" not in [r["nome"] for r in app.config_salva()["reposicao"]], "e do que está guardado")
        check(await pg.evaluate(FORA) <= 0, "Reposição: nada passa da largura")
        await pg.locator("#mp-reposicao").screenshot(path=f"{SHOTS}/ec-reposicao-390.png")
        # desligar a chave: a escolha some, os itens ficam
        await abrir_mais(pg, "opcoes")
        await pg.click("#opRepCron")
        await pg.click("#opRepInv")
        await espera(pg, "() => document.getElementById('opRepInvSt').textContent === 'Desligado.'")
        await abrir_mais(pg, "reposicao")
        await pg.wait_for_timeout(500)
        check(await pg.locator("#repFonte").is_hidden() and "Vitamina D" in [x[0][:10] for x in await pg.evaluate(LINHAS)], "chaves desligadas: sem a escolha, e o item que veio de lá continua")
        # o Voltar do celular volta ao menu
        await pg.go_back()
        await espera(pg, "() => !document.getElementById('maisMenu').hidden")
        check((await pg.locator("#screenTitle").inner_text()).strip() == "Mais", "o Voltar do celular volta ao menu de Mais")
        check(not pg.erros, f"sem erros na página {pg.erros}")
        await b.close()


async def outras(p, inv):
    """320 px claro e o computador: nada cortado nem fora da largura; sem os outros apps na casa, as chaves dizem."""
    for largura, escuro in ((320, False), (1280, True)):
        pc, tag = largura >= 1000, f"{largura} px"
        cfg = dict(config(), repor={"cronologia": True, "inventario": True})
        with App(cfg, buscar=False) as app:
            b, pg = await pagina(p, largura=largura, altura=900 if pc else 720, escuro=escuro, toque=not pc)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            check(await pg.locator("#repAgora").is_visible() and await pg.evaluate(FORA) <= 0, f"{tag}: o Hora de repor, sem passar da largura")
            cort = await pg.evaluate("() => [...document.querySelectorAll('#repAgora button')].filter((x) => x.scrollWidth > x.clientWidth + 1).map((x) => x.textContent)")
            bt = await pg.evaluate("() => [...document.querySelectorAll('#repAgoraLista .rep-vez:first-child button')].map((x) => { const r = x.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height), Math.round(r.top)]; })")
            check(cort == [] and abs(bt[0][0] - bt[1][0]) <= 1 and bt[0][1:] == bt[1][1:], f"{tag}: os botões inteiros, iguais e alinhados ({bt} {cort})")
            await pg.locator("#repAgora").screenshot(path=f"{SHOTS}/ec-reposicao-agora-{largura}.png")
            await abrir_mais(pg, "reposicao", pc)
            await pg.wait_for_timeout(500)
            check(len(await pg.evaluate(LINHAS)) == 3 and await pg.evaluate(FORA) <= 0 and await pg.locator("#repFonte").is_hidden(),
                  f"{tag}: a tela Reposição; sem os outros apps na casa, sem a escolha")
            cab = await pg.evaluate("() => { const a = document.getElementById('repCada').getBoundingClientRect(), u = document.getElementById('repUn').getBoundingClientRect(), n = document.getElementById('repNome').getBoundingClientRect(); return [Math.round(a.height), Math.round(u.height), Math.round(n.height), Math.round(a.top), Math.round(u.top), u.right <= n.right + 1]; }")
            check(cab[0] == cab[1] == cab[2] and cab[3] == cab[4] and cab[5], f"{tag}: A cada e a unidade na mesma linha, da altura do campo ({cab})")
            await pg.locator("#mp-reposicao").screenshot(path=f"{SHOTS}/ec-reposicao-{largura}.png")
            await abrir_mais(pg, "opcoes", pc)
            await espera(pg, "() => document.getElementById('opRepCronSt').textContent !== ''")
            st = [(await pg.locator(i).inner_text()).strip() for i in ("#opRepCronSt", "#opRepInvSt")]
            check(st == ["O CronologIA não está neste Home Assistant.", "O InventarIA não está neste Home Assistant."], f"{tag}: sem os apps na casa, as chaves dizem ({st})")
            # o CronologIA de antes da 1.106.0 e o InventarIA que não liga os consumíveis
            casa(app, inv)
            raiz = os.path.dirname(os.path.join(app.pasta, "share"))
            with open(os.path.join(raiz, "cronologia", "integracao.json"), "w", encoding="utf-8") as f:
                json.dump({"app": "CronologIA", "versao": "1.105.1"}, f)
            inv.resposta = (200, {"versao": "1.81.0", "ligado": False, "consumiveis": []})
            await abrir_mais(pg, "reposicao", pc)
            await abrir_mais(pg, "opcoes", pc)
            await espera(pg, "() => document.getElementById('opRepInvSt').textContent.indexOf('Ligue') === 0")
            st = [(await pg.locator(i).inner_text()).strip() for i in ("#opRepCronSt", "#opRepInvSt")]
            check(st == ["Atualize o CronologIA (1.106.0 ou mais novo).", "Ligue Usar consumíveis no InventarIA."], f"{tag}: o que falta no outro app ({st})")
            check(await pg.get_attribute("#opRepCronSt", "class") == "ia-st erro", f"{tag}: o que falta, em destaque")
            inv.resposta = None
            check(await pg.evaluate(FORA) <= 0, f"{tag}: Opções sem passar da largura")
            check(not pg.erros, f"{tag}: sem erros na página {pg.erros}")
            await b.close()


async def exemplo(p):
    """Fora do add-on (a página sozinha, com o exemplo): a Reposição funciona, com uma casa inventada para escolher."""
    b, pg = await pagina(p)
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    await pg.goto("file://" + os.path.join(raiz, "economia", "pagina", "painel.html"))
    await pg.wait_for_timeout(3500)
    await abrir_mais(pg, "opcoes")
    await pg.click("#opRepCron")
    await abrir_mais(pg, "reposicao")
    await espera(pg, "() => !document.getElementById('repFonte').hidden")
    await tocar(pg, "#repFonte")
    ops = [t.strip() for t in await pg.locator(".ss-wrap.in .ss-opt").all_inner_texts()]
    check(ops == ["Escolher de outro app", "Vitamina D · 1 cápsula", "Antialérgico · 1 comprimido"], f"no exemplo: os remédios de uma casa inventada ({ops})")
    await tocar(pg, ".ss-opt >> nth=2")
    await pg.click("#repSalvar")
    check([x[0] for x in await pg.evaluate(LINHAS)] == ["AntialérgicoCronologIA"], f"no exemplo: o item entra ({await pg.evaluate(LINHAS)})")
    check(not pg.erros, f"no exemplo: sem erros na página {pg.erros}")
    await b.close()


async def main():
    inv = InventarioFalso()
    try:
        async with async_playwright() as p:
            await tudo(p, inv)
            await outras(p, inv)
            await exemplo(p)
    finally:
        inv.fecha()


asyncio.run(main())
resumo()
