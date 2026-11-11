# EconomIA 0.19.0: Ler com IA, com o Home Assistant falso: Colar mensagem (itens, "Já na lista", quantidade, ajustar o
# nome e desmarcar antes de adicionar), Escolher fotos (miniaturas, tirar uma, anexos para a IA de fotos), erro da IA,
# Falar com o microfone falso do Chromium (fala para texto do HA → a IA separa os itens), o encarte ou print de preços
# na tela Ofertas (as ofertas entram) e os prints da carteira de cupons do app em Mais › Lojas.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, Erro, HAFalso, abrir_mais, categoria, check, espera, estado, pagina, png_codigo, resumo

IMG = png_codigo("7891000100103", modulo=2, altura=80, fundo=(400, 300))
OFERTAS = {"versao": 2, "gerado_em": "2026-11-02T10:00:00-03:00", "lista": [], "categorias": [
    categoria("mercados", [("merc-giassi", "Giassi", 1.0)]), categoria("farmacias", [("farm-panvel", "Panvel", 1.2)])]}


def ler_lista(corpo):
    t = corpo["instructions"]
    if corpo.get("attachments"):
        return {"itens": [{"produto": "Arroz Tio João 5 kg", "quantidade": "2"}]}
    if "quebrar" in t:
        return Erro(500, "Internal Server Error")
    return {"itens": [{"produto": "leite integral", "quantidade": "2"}, {"produto": "Lysoform"}, {"produto": "Pão de forma"}]}


async def main():
    ha = HAFalso()
    ha.tarefa_ia("ai_task.claude", "Claude")
    ha.estados["stt.home_assistant_cloud"] = estado("stt.home_assistant_cloud", "unknown", friendly_name="Home Assistant Cloud")
    ha.pipelines = {"pipelines": [{"id": "p1", "name": "Casa", "stt_engine": "stt.home_assistant_cloud", "stt_language": "pt-BR"}], "preferred_pipeline": "p1"}
    ha.responde_ia("ler lista", ler_lista)
    ha.responde_ia("falar", {"itens": [{"produto": "Café 500 g", "quantidade": "2"}, {"produto": "Detergente"}]})
    ha.responde_ia("encarte Mercado Kuntze", {"validade": None, "ofertas": [{"produto": "Café Pilão 500 g", "preco": 15.98}, {"produto": "Picanha kg", "preco": 59.9, "unidade": "kg"}],
                                              "lista": [{"item": 2, "precos": [{"preco": 15.98}]}]})
    ha.responde_ia("ler cupons", {"cupons": [{"loja": "Panvel", "beneficio": "20% em Colgate", "condicao": "Ativado no app", "valido_ate": "2099-01-31"},
                                             {"loja": "Loja Desconhecida", "codigo": "X10", "beneficio": "R$ 10 acima de R$ 80"}]})
    cfg = {"cep": CEP, "raio_km": 5, "categorias": ["mercados", "farmacias"], "ia": {"fotos": "ai_task.claude"},
           "lista": [{"produto": "Leite integral"}, {"produto": "Café Pilão 500 g"}]}
    with App(cfg, buscar=False, antes=lambda S: S.gravar_json(S.OFERTAS, OFERTAS), ha=ha) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p, args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"], permissoes=["microphone"])
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="lista"]')
            # ----- Colar mensagem -----
            await pg.click("#textoBtn")
            check(await pg.locator("#fotoTxt").is_visible() and await pg.locator("#fotoLer").is_visible(), "Colar mensagem abre o campo")
            await pg.click("#fotoLer")
            check(await pg.text_content("#fotoMsg") == "Cole o texto da mensagem.", "sem texto: pede o texto")
            await pg.fill("#fotoTxt", "Amor, compra 2 leites, Lysoform e pão de forma. Bjs")
            await pg.click("#fotoLer")
            check(await pg.text_content("#fotoMsg") == "A IA está lendo…" and await pg.is_disabled("#fotoLer"), "lendo")
            await espera(pg, "() => document.querySelectorAll('#fotoItens li').length === 3")
            check(await pg.text_content("#fotoMsg") == "Achei 3 itens. Confira, ajuste o nome se precisar e adicione.", "achou 3 itens")
            leite = pg.locator("#fotoItens li").nth(0)
            check((await leite.inner_text()).upper().count("JÁ NA LISTA") == 1 and await leite.locator("input[type=checkbox]").is_disabled(), "o leite já está na lista")
            check("QTD. 2" in (await leite.inner_text()).upper(), "com a quantidade")
            check('"""Amor, compra 2 leites, Lysoform e pão de forma. Bjs"""' in ha.chamadas_ia[-1]["instructions"], "o texto colado vai para a IA")
            await pg.locator("#fotoBox").screenshot(path=SHOTS + "/ecia-mensagem.png")
            await pg.locator("#fotoItens li").nth(1).locator("textarea").fill("Lysoform Original 500 ml")
            ta = pg.locator("#fotoItens li").nth(0).locator("textarea")
            check(await ta.evaluate("(e) => e.scrollHeight <= e.clientHeight + 2"), "1.20.0: o nome do item à vista, inteiro (a caixa cresce com o texto)")
            await pg.locator("#fotoItens li").nth(2).locator("input[type=checkbox]").uncheck()
            await pg.click("#fotoAdd")
            await pg.wait_for_timeout(800)
            check(await pg.text_content("#addMsg") == "1 item entrou na lista. Os preços aparecem depois da próxima busca.", "adicionado")
            nomes = [i["produto"] for i in app.config_salva()["lista"]]
            check("Lysoform Original 500 ml" in nomes and "Pão de forma" not in nomes and nomes.count("Leite integral") == 1, f"o nome ajustado entra, o desmarcado não ({nomes})")
            check(await pg.locator("#fotoBox").is_hidden(), "a caixa fecha")
            # ----- Escolher fotos -----
            await pg.set_input_files("#fotoArq", [{"name": "a.png", "mimeType": "image/png", "buffer": IMG}, {"name": "b.png", "mimeType": "image/png", "buffer": IMG}])
            await espera(pg, "() => document.querySelectorAll('#fotoPrev .foto-th').length === 2")
            check(await pg.text_content("#fotoMsg") == "2 fotos. Tire ou escolha mais, ou toque em Digitalizar com IA.", "2 fotos escolhidas")
            await pg.click('#fotoPrev .foto-rm[data-i="1"]')
            check(await pg.locator("#fotoPrev .foto-th").count() == 1 and await pg.text_content("#fotoMsg") == "1 foto. Tire ou escolha mais, ou toque em Digitalizar com IA.", "tirar uma foto")
            await pg.locator("#fotoBox").screenshot(path=SHOTS + "/ecia-fotos.png")
            await pg.click("#fotoLer")
            await espera(pg, "() => /Arroz/.test(document.getElementById('fotoItens').innerHTML)")
            c = ha.chamadas_ia[-1]
            check(c["entity_id"] == "ai_task.claude" and len(c["attachments"]) == 1 and c["attachments"][0]["media_content_type"] == "image/jpeg",
                  "a foto vai reduzida, em JPEG, para a IA de fotos")
            check("1 imagem(ns) em anexo" in c["instructions"], "o pedido diz quantas fotos")
            await pg.click("#fotoAdd")
            await pg.wait_for_timeout(800)
            check("Arroz Tio João 5 kg" in [i["produto"] for i in app.config_salva()["lista"]], "o item da foto entrou")
            # ----- erro da IA -----
            await pg.click("#textoBtn")
            await pg.fill("#fotoTxt", "quebrar tudo")
            await pg.click("#fotoLer")
            await espera(pg, "() => document.getElementById('fotoMsg').classList.contains('err')")
            check(await pg.text_content("#fotoMsg") == "A IA do Home Assistant recusou o pedido (500): Internal Server Error", "erro da IA aparece")
            check(not await pg.is_disabled("#fotoLer"), "dá para tentar de novo")
            await pg.click("#fotoFechar")
            # ----- Falar -----
            await espera(pg, "() => !document.getElementById('falarBtn').hidden")
            check(await pg.locator(".cab-topo .mic-top.so-voz").is_visible(), "o microfone aparece no alto (o HA tem fala para texto)")
            await pg.click("#falarBtn")
            await espera(pg, "() => /Ouvindo/.test(document.getElementById('vozEstado').textContent)")
            check(await pg.locator("#vozBox .vz-ok").is_visible() and await pg.locator("#vozBox .vz-mic").is_hidden(), "gravando: o botão vira o de pronto")
            await pg.locator("#vozBox").screenshot(path=SHOTS + "/ecia-ouvindo.png")
            await pg.wait_for_timeout(1500)
            await pg.click("#vozMic")
            await espera(pg, "() => !document.getElementById('vozOuvido').hidden")
            check(await pg.text_content("#vozOuvido span") == "“leite integral e café”", "mostra o que ouviu")
            await espera(pg, "() => /Detergente/.test(document.getElementById('fotoItens').innerHTML)")
            stt = ha.pedidos_de("/api/stt/")[-1]
            check(stt[1] == "/api/stt/stt.home_assistant_cloud" and len(stt[3]) >= 16000 * 2 * 1 and "sample_rate=16000" in stt[2]["X-Speech-Content"],
                  f"o áudio PCM vai para a fala para texto do assistente preferido ({len(stt[3])} bytes)")
            check(ha.chamadas_ia[-1]["task_name"] == "EconomIA: falar" and "leite integral e café" in ha.chamadas_ia[-1]["instructions"], "a IA separa os itens da fala")
            await pg.locator("#fotoBox").screenshot(path=SHOTS + "/ecia-falar.png")
            await pg.click("#fotoFechar")
            # ----- encarte ou print de preços (Ofertas) -----
            await pg.click('.tabbar [data-view="ofertas"]')
            await pg.set_input_files("#encArq", [{"name": "enc.png", "mimeType": "image/png", "buffer": IMG}])
            await espera(pg, "() => !document.getElementById('encBox').hidden")
            check(await pg.text_content("#encMsg") == "1 foto. Diga de qual loja é e toque em Ler com IA.", "encarte escolhido")
            await pg.click("#encLer")
            check(await pg.text_content("#encMsg") == "Diga de qual loja é o encarte.", "pede a loja")
            # 1.8.0: as lojas sugeridas no visual do app, logo abaixo do campo (nada de <datalist>, a lista do celular)
            check(await pg.evaluate("() => document.querySelectorAll('datalist, input[list]').length") == 0, "sem <datalist> na página")
            await espera(pg, "() => document.querySelector('#encBox .sug-box')")
            sug = [t.strip() for t in await pg.locator("#encBox .sug-op").all_inner_texts()]
            check("Giassi" in sug and len(sug) <= 6, f"no campo, as lojas de mercado ({sug})")
            junto = await pg.evaluate("() => [document.getElementById('encLoja').getBoundingClientRect(), document.querySelector('#encBox .sug-box').getBoundingClientRect()].map((r) => [r.left, r.right, r.top, r.bottom])")
            check(0 <= junto[1][2] - junto[0][3] <= 12 and abs(junto[1][0] - junto[0][0]) < 2 and abs(junto[1][1] - junto[0][1]) < 2, f"embaixo do campo, da mesma largura ({junto})")
            await pg.fill("#encLoja", "xyz")
            check(await pg.locator("#encBox .sug-box").count() == 0, "nada combina: some")
            await pg.fill("#encLoja", "GIA")
            check([t.strip() for t in await pg.locator("#encBox .sug-op").all_inner_texts()] == ["Giassi"], "combina sem diferença de maiúsculas")
            await pg.locator("#encBox").screenshot(path=SHOTS + "/ecia-sugestoes.png")
            await pg.locator("#encBox .sug-op").first.tap()
            await pg.wait_for_timeout(400)
            check(await pg.input_value("#encLoja") == "Giassi" and await pg.locator("#encBox .sug-box").count() == 0, "tocar preenche o campo e fecha")
            check(await pg.text_content("#encMsg") == "Diga de qual loja é o encarte.", "o toque não cai no botão de baixo")
            await pg.fill("#encLoja", "Mercado Kuntze")
            await pg.click("#encLer")
            await espera(pg, "() => /Li 2 ofertas/.test(document.getElementById('encMsg').textContent)")
            check(await pg.text_content("#encMsg") == "Li 2 ofertas do Mercado Kuntze. 1 item da sua lista ganhou preço: Café Pilão 500 g.", f"resultado do encarte ({await pg.text_content('#encMsg')})")
            await espera(pg, "() => /Picanha/.test(document.getElementById('deals').textContent)")
            check("Mercado Kuntze" in await pg.text_content("#filters"), "a loja do encarte entra nos filtros")
            await pg.locator("#v-ofertas").screenshot(path=SHOTS + "/ecia-encarte.png")
            # ----- prints da carteira de cupons -----
            await abrir_mais(pg, "lojas")
            await pg.set_input_files("#cupArq", [{"name": "cup.png", "mimeType": "image/png", "buffer": IMG}])
            await espera(pg, "() => !document.getElementById('cupBox').hidden")
            await pg.click("#cupLer")
            await espera(pg, "() => document.querySelectorAll('#cupItens li').length === 2")
            check(await pg.text_content("#cupMsg") == "Achei 2 cupons. Confira a loja de cada um e guarde.", "achou os cupons")
            linhas = pg.locator("#cupItens li")
            check(await linhas.nth(0).locator("select").input_value() == "farm-panvel" and await linhas.nth(0).locator("input[type=checkbox]").is_checked(), "a loja conhecida já vem marcada")
            check(await linhas.nth(1).locator("select").input_value() == "" and not await linhas.nth(1).locator("input[type=checkbox]").is_checked(), "a desconhecida pede a loja")
            await linhas.nth(1).locator("select").select_option("merc-giassi")
            check(await linhas.nth(1).locator("input[type=checkbox]").is_checked(), "escolher a loja marca o cupom")
            await pg.locator("#cupMeus").screenshot(path=SHOTS + "/ecia-cupons.png")
            await pg.click("#cupAdd")
            await pg.wait_for_timeout(800)
            meus = app.config_salva().get("cupons_meus") or []
            check(sorted((c["rede"], c["beneficio"], c.get("codigo")) for c in meus) == [("farm-panvel", "20% em Colgate", None), ("merc-giassi", "R$ 10 acima de R$ 80", "X10")],
                  f"os cupons guardados ({meus})")
            check(await pg.locator("#cupLista li").count() == 2, "aparecem na lista de cupons")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
