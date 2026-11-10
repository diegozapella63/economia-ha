# EconomIA 0.20.0: a Conversa com a IA, com o Home Assistant falso. O balão ao lado do microfone abre a conversa (de baixo no
# celular, numa janela no canto de baixo à direita no computador); sugestões da tela; a resposta da IA com as ações para confirmar (pôr na lista,
# comprei hoje, tirar da lista, abrir uma tela); o que foi feito fica marcado e vai junto na próxima pergunta; a tela
# aberta vai para a IA; erro com Tentar de novo; a conversa continua depois de recarregar; Nova conversa; Enter envia e
# Shift+Enter quebra a linha; o microfone da conversa põe a fala na caixa; com a IA desligada, o balão some.
import asyncio
import json
from datetime import datetime, timedelta, timezone

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, Erro, HAFalso, categoria, check, espera, estado, pagina, resumo

HOJE = (datetime.now(timezone.utc) - timedelta(hours=3)).date().isoformat()
OFERTAS = {"versao": 2, "gerado_em": "2026-11-02T10:00:00-03:00", "categorias": [
    categoria("mercados", [("merc-giassi", "Giassi", 1.0), ("merc-angeloni", "Angeloni", 1.4)],
              ofertas=[{"id": "g1", "rede": "merc-giassi", "produto": "Picanha kg", "preco_normal": 89.9, "preco_oferta": 59.9, "tipo": "promo"}])],
    "lista": [{"produto": "Café Pilão 500 g", "precos": {"merc-giassi": 19.9, "merc-angeloni": 21.5}}]}
LISTA = [{"produto": "Café Pilão 500 g", "compras": []}, {"produto": "Leite integral", "compras": []}, {"produto": "Detergente Ypê 500 ml", "compras": []}]


def ultima_pergunta(corpo):
    t = corpo["instructions"]
    return t[t.rindex("\nPessoa: ") + 9:]


def responde(corpo):
    p = ultima_pergunta(corpo).lower()
    if "quebra" in p:
        return Erro(500, "Internal Server Error")
    if p.startswith("vale a pena?"):
        return {"resposta": "Vale a pena. Nota 4,7 de quem comprou, e R$ 59,90 está bem abaixo do preço de costume.", "acoes": []}
    if "churrasco" in p:
        return {"resposta": "Para o churrasco:\n• Picanha em oferta no Giassi por R$ 59,90\n**Dica**: compre o café junto.",
                "acoes": [{"tipo": "por_na_lista", "produto": "Picanha kg"}, {"tipo": "comprei", "produto": "café pilão"},
                          {"tipo": "tirar_da_lista", "produto": "Detergente Ypê 500 ml"}, {"tipo": "abrir", "tela": "ofertas"},
                          {"tipo": "buscar", "produto": "Não está na lista"}]}
    return "O café está mais barato no Giassi: R$ 19,90."


async def main():
    ha = HAFalso()
    ha.tarefa_ia("ai_task.claude", "Claude")
    ha.tarefa_ia("ai_task.busca", "Busca")
    ha.estados["stt.home_assistant_cloud"] = estado("stt.home_assistant_cloud", "unknown", friendly_name="Home Assistant Cloud")
    ha.pipelines = {"pipelines": [{"id": "p1", "name": "Casa", "stt_engine": "stt.home_assistant_cloud", "stt_language": "pt-BR"}], "preferred_pipeline": "p1"}
    ha.stt = (200, {"result": "success", "text": "tem cerveja em oferta"})
    ha.responde_ia("conversa", responde)
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados"], "ia": {"fotos": "ai_task.claude", "busca": "ai_task.busca"}, "lista": LISTA}
    with App(cfg, buscar=False, antes=lambda S: S.gravar_json(S.OFERTAS, OFERTAS), ha=ha) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p, args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"], permissoes=["microphone"])
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="lista"]')
            bolha = pg.locator('.cab-topo [data-acao="chat"]')
            check(await bolha.is_visible(), "o balão da conversa aparece no alto")
            await espera(pg, "() => !document.querySelector('.cab-topo .mic-top.so-voz').hidden")
            caixa_b, caixa_m = await bolha.bounding_box(), await pg.locator(".cab-topo .mic-top.so-voz").bounding_box()
            check(abs(caixa_b["y"] - caixa_m["y"]) < 1 and abs(caixa_b["width"] - caixa_m["width"]) < 1 and caixa_b["x"] < caixa_m["x"],
                  "ao lado do microfone, do mesmo tamanho e alinhado")
            await bolha.click()
            check(await pg.locator("#chat").is_visible() and await pg.locator("#chatFundo").is_visible(), "abre a conversa por cima")
            check(await bolha.get_attribute("aria-expanded") == "true", "o balão diz que a conversa está aberta")
            caixa = await pg.locator("#chat").bounding_box()
            check(caixa["x"] == 0 and caixa["width"] == 412 and abs(caixa["y"] + caixa["height"] - 892) < 1 and caixa["height"] < 892 * 0.9,
                  f"no celular, sobe de baixo ({caixa})")
            check(await pg.text_content(".chat-vazio") == "Pergunte sobre a lista, as ofertas ou o que quiser. A IA sugere; você confirma.", "o texto da conversa vazia")
            sug = await pg.locator("#chatSug button").all_text_contents()
            check(sug == ["Onde a compra fica mais barata?", "O que está acabando?", "Monte uma lista para um churrasco"], f"as sugestões da Minha lista ({sug})")
            check(await pg.is_disabled("#chatEnv") and await pg.is_disabled("#chatNova"), "sem texto: Enviar e Nova conversa inativos")
            check(await pg.locator("#chatMic").is_visible(), "o microfone também na conversa")
            await pg.locator("#chat").screenshot(path=SHOTS + "/ecchat-vazia.png")
            # ----- uma sugestão e a resposta em texto solto -----
            await pg.click("#chatSug button >> nth=0")
            check(await pg.locator(".cm.eu").last.text_content() == "Onde a compra fica mais barata?", "a sugestão vira a pergunta")
            check(await pg.locator(".cm.pensando").count() == 1 or await pg.locator(".cm.ia").count() == 1, "espera a IA")
            await espera(pg, "() => document.querySelectorAll('.cm.ia:not(.pensando)').length === 1")
            check(await pg.locator(".cm.ia").last.text_content() == "O café está mais barato no Giassi: R$ 19,90.", "a resposta da IA")
            check(await pg.locator("#chatSug").is_hidden(), "as sugestões saem depois da primeira pergunta")
            c = ha.chamadas_ia[-1]
            check(c["task_name"] == "EconomIA: conversa" and c["entity_id"] == "ai_task.claude", "vai para a tarefa de IA de fotos")
            t = c["instructions"]
            check("Tela aberta no app: Minha lista." in t and "- Café Pilão 500 g; mais barato no Giassi por R$ 19,90" in t and "Picanha kg, no Giassi" in t,
                  "a IA recebe a tela, a lista com os preços e as ofertas")
            check(ha.pedidos_de("/services/conversation/process") == [], "nunca um assistente de conversa")
            # ----- Enter envia, Shift+Enter quebra a linha -----
            await pg.click("#chatTxt")
            await pg.keyboard.type("Monte um")
            await pg.keyboard.press("Shift+Enter")
            await pg.keyboard.type("churrasco")
            check(await pg.input_value("#chatTxt") == "Monte um\nchurrasco" and not await pg.is_disabled("#chatEnv"), "Shift+Enter quebra a linha")
            await pg.keyboard.press("Enter")
            await espera(pg, "() => document.querySelectorAll('.cm-acao').length === 4")
            check(await pg.input_value("#chatTxt") == "", "a caixa esvazia")
            ia = pg.locator(".cm.ia").last
            check(await ia.locator("b").text_content() == "Dica" and await ia.locator("br").count() == 2 and "**" not in await ia.text_content(),
                  "negrito e linhas na resposta")
            acoes = await pg.locator(".cm-acao").all_text_contents()
            check(acoes == ["Pôr na lista: Picanha kg", "Comprei hoje: Café Pilão 500 g", "Tirar da lista: Detergente Ypê 500 ml", "Abrir Ofertas"],
                  f"as ações conferidas com a lista ({acoes})")
            check([i["produto"] for i in app.config_salva()["lista"]] == [i["produto"] for i in LISTA], "nada muda sem o toque")
            await pg.locator("#chat").screenshot(path=SHOTS + "/ecchat-acoes.png")
            # ----- confirmar -----
            await pg.click(".cm-acao >> nth=0")
            await espera(pg, "() => document.querySelectorAll('.cm-acao:disabled').length === 1")
            await pg.wait_for_timeout(600)
            nomes = [i["produto"] for i in app.config_salva()["lista"]]
            check("Picanha kg" in nomes, f"Pôr na lista: entrou ({nomes})")
            check(await pg.locator(".cm-acao >> nth=0").text_content() == "Na lista: Picanha kg", "o botão fica marcado")
            toast = await pg.locator("#toast").bounding_box()
            check(await pg.locator("#toast").is_visible() and toast["y"] < 100, f"o aviso aparece no alto, por cima da conversa ({toast})")
            await pg.click(".cm-acao >> nth=1")
            await pg.wait_for_timeout(600)
            cafe = [i for i in app.config_salva()["lista"] if i["produto"] == "Café Pilão 500 g"][0]
            check(cafe["compras"] == [HOJE], f"Comprei hoje: a compra de hoje ({cafe})")
            check(await pg.locator(".cm-acao >> nth=1").text_content() == "Compra registrada: Café Pilão 500 g", "marcado")
            await pg.click(".cm-acao >> nth=2")
            await pg.wait_for_timeout(600)
            salvo = app.config_salva()
            check("Detergente Ypê 500 ml" not in [i["produto"] for i in salvo["lista"]] and "Detergente Ypê 500 ml" in [h["produto"] for h in salvo["historico"]],
                  "Tirar da lista: vai para o histórico")
            check(await pg.locator(".cm-acao:disabled").count() == 3, "três feitas")
            await pg.click(".cm-acao:disabled >> nth=0", force=True)
            await pg.wait_for_timeout(300)
            check([i["produto"] for i in app.config_salva()["lista"]].count("Picanha kg") == 1, "tocar de novo não faz de novo")
            check(await pg.locator("#v-lista").is_visible() and "Picanha kg" in await pg.text_content("#v-lista"), "a lista atrás já mostra a picanha")
            # ----- Abrir Ofertas: fecha a conversa no celular -----
            await pg.click(".cm-acao >> nth=3")
            await pg.wait_for_timeout(400)
            check(await pg.locator("#chat").is_hidden() and await pg.text_content("#screenTitle") == "Ofertas", "Abrir Ofertas fecha a conversa e abre a tela")
            # 1.9.0: o Voltar do celular fecha só a Conversa, como nos outros apps (a tela de baixo continua)
            hist = await pg.evaluate("history.length")
            await bolha.click()
            check(await pg.evaluate("history.state && history.state.chat") is True, "aberta, a Conversa ocupa uma entrada no histórico")
            await pg.go_back()
            await pg.wait_for_timeout(400)
            check(await pg.locator("#chat").is_hidden() and await pg.text_content("#screenTitle") == "Ofertas", "o Voltar do celular fecha a Conversa e fica em Ofertas")
            await bolha.click()
            await pg.click("#chatFechar")
            await pg.wait_for_timeout(400)
            check(await pg.locator("#chat").is_hidden() and not await pg.evaluate("!!(history.state && history.state.chat)") and await pg.evaluate("history.length") <= hist + 2,
                  "o X fecha e desfaz a entrada")
            # ----- a próxima pergunta leva o que foi feito e a tela -----
            await bolha.click()
            check(await pg.locator(".cm-acao").count() == 4 and await pg.is_enabled(".cm-acao >> nth=3"), "a conversa continua; Abrir fica sempre ativo")
            await pg.fill("#chatTxt", "e o café?")
            await pg.click("#chatEnv")
            await espera(pg, "() => document.querySelectorAll('.cm.ia:not(.pensando)').length === 3")
            t = ha.chamadas_ia[-1]["instructions"]
            check("Tela aberta no app: Ofertas." in t, "a tela aberta vai para a IA")
            check("(Sugeri: Pôr na lista: Picanha kg, feito; Comprei hoje: Café Pilão 500 g, feito; Tirar da lista: Detergente Ypê 500 ml, feito; Abrir Ofertas, feito)" in t,
                  "o que a IA sugeriu e o que foi feito vão junto")
            check("Pessoa: Monte um\nchurrasco" in t, "a pergunta com a quebra de linha")
            # ----- erro e Tentar de novo -----
            await pg.fill("#chatTxt", "quebra tudo")
            await pg.click("#chatEnv")
            await espera(pg, "() => document.querySelector('.cm.erro')")
            check(await pg.locator(".cm.erro").text_content() == "A IA do Home Assistant recusou o pedido (500): Internal Server Error Tentar de novo", "o erro da IA aparece")
            await pg.locator("#chat").screenshot(path=SHOTS + "/ecchat-erro.png")
            ha.regras_ia.insert(0, {"quando": lambda corpo: "quebra" in ultima_pergunta(corpo), "resp": {"resposta": "Agora foi.", "acoes": []}, "vezes": 1})
            await pg.click(".cm.erro .link")
            await espera(pg, "() => !document.querySelector('.cm.erro') && /Agora foi/.test(document.getElementById('chatMsgs').textContent)")
            check(await pg.locator(".cm.eu").count() == 4, "Tentar de novo não repete a pergunta")
            # ----- recarregar: a conversa continua -----
            await pg.reload()
            await pg.wait_for_timeout(1200)
            await pg.locator('.cab-topo [data-acao="chat"]').click()
            check(await pg.locator(".cm.eu").count() == 4 and await pg.locator(".cm-acao:disabled").count() == 3, "depois de recarregar, a conversa e o que foi feito continuam")
            # ----- microfone da conversa -----
            await pg.click("#chatMic")
            await espera(pg, "() => /Ouvindo/.test(document.getElementById('chatOuvindo').textContent)")
            check(await pg.locator("#chatMic.on").count() == 1, "gravando: o microfone fica vermelho")
            await pg.locator(".chat-form").screenshot(path=SHOTS + "/ecchat-ouvindo.png")
            await pg.wait_for_timeout(1200)
            await pg.click("#chatMic")
            await espera(pg, "() => document.getElementById('chatTxt').value === 'tem cerveja em oferta'")
            check(await pg.locator("#chatOuvindo").is_hidden() and await pg.is_enabled("#chatEnv"), "a fala vira texto na caixa, para conferir e enviar")
            check(ha.chamadas_ia[-1]["instructions"].count("tem cerveja") == 0, "não envia sozinho")
            # ----- Nova conversa -----
            await pg.click("#chatNova")
            check(await pg.locator(".cm").count() == 0 and await pg.locator(".chat-vazio").is_visible(), "Nova conversa limpa")
            sug = await pg.locator("#chatSug button").all_text_contents()
            check(sug[0] == "Quais ofertas valem a pena para mim?", f"as sugestões da tela Ofertas ({sug})")
            await pg.click("#chatFundo", position={"x": 200, "y": 40})
            check(await pg.locator("#chat").is_hidden(), "tocar fora fecha")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()

            # ----- computador: janela no canto, a página continua usável -----
            b, pg = await pagina(p, largura=1280, altura=860, toque=False)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            check(await pg.locator('.cab-topo [data-acao="chat"]').is_hidden() and await pg.locator('.top-acts [data-acao="chat"]').is_visible(),
                  "no computador, o balão fica nas ações do alto")
            await pg.click('.top-acts [data-acao="chat"]')
            caixa = await pg.locator("#chat").bounding_box()
            check(caixa["x"] == 856 and caixa["width"] == 400 and caixa["y"] == 156 and caixa["height"] == 680, f"janela no canto de baixo, à direita ({caixa})")
            topo = await pg.locator('.top-acts [data-acao="chat"]').bounding_box()
            check(topo["y"] + topo["height"] < caixa["y"], "o balão do alto continua à vista para fechar")
            check(await pg.locator("#chatFundo").is_hidden(), "sem fundo escuro")
            check(await pg.evaluate("document.activeElement.id") == "chatTxt", "o cursor já fica na caixa")
            await pg.click('#lado [data-lado="lista"]')
            check(await pg.text_content("#screenTitle") == "Minha lista" and await pg.locator("#chat").is_visible(), "dá para usar a página com a conversa aberta")
            await pg.fill("#chatTxt", "churrasco de novo")
            await pg.keyboard.press("Enter")
            await espera(pg, "() => document.querySelectorAll('.cm-acao').length >= 2")
            await pg.screenshot(path=SHOTS + "/ecchat-computador.png")
            await pg.click('.cm-acao:has-text("Abrir Ofertas")')
            check(await pg.text_content("#screenTitle") == "Ofertas" and await pg.locator("#chat").is_visible(), "no computador, Abrir não fecha a conversa")
            await pg.keyboard.press("Escape")
            check(await pg.locator("#chat").is_hidden(), "Esc fecha")
            # ----- Vale a pena? numa oferta: a conversa abre e a IA de busca (com a busca na web) avalia -----
            await pg.click('#lado [data-lado="ofertas"]')
            await pg.locator('#deals .deal', has_text="Picanha kg").locator('[data-act="avaliar"]').click()
            check(await pg.locator("#chat").is_visible(), "Vale a pena? abre a conversa")
            pergunta = (await pg.locator(".cm.eu").last.text_content()).replace("\xa0", " ")
            check(pergunta == "Vale a pena? Picanha kg, R$ 59,90 (era R$ 89,90) no Giassi.", f"a pergunta com o produto, o preço e a loja ({pergunta})")
            await espera(pg, "() => /Nota 4,7/.test(document.getElementById('chatMsgs').textContent)")
            c = ha.chamadas_ia[-1]
            check(c["entity_id"] == "ai_task.busca" and "Para avaliar um produto" in c["instructions"], "vai para a IA de busca, com o pedido de avaliação")
            await pg.screenshot(path=SHOTS + "/ecchat-vale-a-pena.png")
            await pg.fill("#chatTxt", "e o café?")
            await pg.keyboard.press("Enter")
            await espera(pg, "() => /19,90/.test(document.querySelector('.cm.ia:last-child') ? document.querySelector('.cm.ia:last-child').textContent : '')")
            check(ha.chamadas_ia[-1]["entity_id"] == "ai_task.claude", "a pergunta seguinte, escrita, volta para a IA da conversa")
            await pg.keyboard.press("Escape")
            await pg.evaluate("localStorage.setItem('ofertas-bairro:ui', JSON.stringify(Object.assign(JSON.parse(localStorage.getItem('ofertas-bairro:ui') || '{}'), {tema: 'claro'})))")
            await pg.reload()
            await pg.wait_for_timeout(1200)
            await pg.click('.top-acts [data-acao="chat"]')
            await pg.screenshot(path=SHOTS + "/ecchat-computador-claro.png")
            # ----- IA desligada: o balão some -----
            st = app.api("GET", "/api/estado")
            app.api("PUT", "/api/config", dict(st["config"], usar_ia=False))
            await pg.reload()
            await pg.wait_for_timeout(1200)
            check(await pg.locator('[data-acao="chat"]:visible').count() == 0, "IA desligada: o balão some")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
