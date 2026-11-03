# EconomIA 0.19.0: Mais › Integrações: Shopee (senha errada e certa, a assinatura conferida), Google Places, Brave e
# Instagram (salvar e testar, chave só como ••••, Apagar), a IA do Home Assistant (as tarefas e os assistentes do HA falso,
# escolher e testar sozinho) e o Uso da IA (quadros, gráfico dos 7 dias, tipos, últimas chamadas, painel do provedor).
import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, HAFalso, check, espera, pagina, resumo

HOJE = (datetime.now(timezone.utc) - timedelta(hours=3)).date()


def shopee(p):
    cred = dict(x.split("=", 1) for x in p.cabecalhos["Authorization"].replace("SHA256 ", "").split(", "))
    certo = hashlib.sha256((cred["Credential"] + cred["Timestamp"] + p.corpo + "segredo-shopee").encode()).hexdigest()
    if cred["Signature"] != certo:
        return {"errors": [{"message": "invalid signature", "extensions": {"code": 10020}}]}
    return {"data": {"productOfferV2": {"nodes": [{"productName": "Café Pilão Tradicional 500g", "priceMin": "17.90"}]}}}


def prepara(lojas):
    lojas.rotas["/shopee"] = shopee
    lojas.rotas["/google/nearby"] = lambda p: ({"places": [{"id": "1", "displayName": {"text": "Farmácia Bem Estar"}, "types": ["pharmacy"],
                                                            "location": {"latitude": -26.3045, "longitude": -48.85}}]}
                                               if p.cabecalhos.get("X-Goog-Api-Key") == "chave-google" else (403, {"error": {"message": "API key not valid"}}))
    lojas.rotas["/brave"] = lambda p: {"web": {"results": [{"url": "https://www.giassi.com.br", "title": "Giassi"}]}}
    lojas.rotas["/graph/me/accounts"] = lambda p: {"data": [{"instagram_business_account": {"id": "99", "username": "casa"}}]}
    lojas.rotas["/graph/99"] = lambda p: {"business_discovery": {"username": "instagram"}}
    lojas.rotas["/graph/debug_token"] = lambda p: {"data": {"expires_at": 0}}


def antes(S):
    ontem = (HOJE - timedelta(days=1)).isoformat()
    S.gravar_json(S.USO_FILE, {"dias": {ontem: {"chamadas": 2, "erros": 0, "cota": 1, "tokens": 3000, "imagens": 0, "segundos": 40, "tipos": {"busca": 2},
                                                "ias": {"ai_task.claude": 2}}},
                               "ultimas": [{"quando": f"{ontem}T15:00:00+00:00", "tipo": "busca", "ia": "ai_task.claude", "resultado": "cota", "segundos": 2.0,
                                            "tokens": 1500, "imagens": 0}]})


async def st(pg, el, txt, ms=15000):
    await espera(pg, f"() => document.getElementById('{el}').textContent.indexOf({json.dumps(txt)}) >= 0", ms)
    return await pg.text_content("#" + el)


async def main():
    ha = HAFalso()
    ha.tarefa_ia("ai_task.claude", "Claude")
    ha.tarefa_ia("ai_task.openai", "OpenAI", anexos=False)
    ha.agente("conversation.gemini", "Gemini")
    ha.responde_ia("teste", {"busca": True, "exemplo": "Giassi, café por R$ 19,90", "fonte": "https://www.giassi.com.br/cafe"})
    with App({"cep": CEP, "categorias": ["mercados"], "lista": []}, buscar=False, preparar=prepara, antes=antes, ha=ha, servicos=True) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await pg.click('.tabbar [data-view="mais"]')
            await pg.click("#aba-integracoes")
            await st(pg, "shSt", "Desligada")
            check(await pg.text_content("#gSt") == "Desligada: as lojas vêm só do OpenStreetMap." and await pg.text_content("#bSt") == "Desligado.", "começa tudo desligado")
            # ----- Shopee -----
            await pg.fill("#shApp", "18300000001")
            await pg.fill("#shSenha", "senha-errada")
            await pg.click("#shSalvar")
            await st(pg, "shSt", "recusou o App ID")
            check("erro" in await pg.get_attribute("#shSt", "class"), "senha errada: a Shopee recusa (a assinatura não confere)")
            await pg.fill("#shSenha", "segredo-shopee")
            await pg.click("#shSalvar")
            t = await st(pg, "shSt", "Pronta")
            check(t == "Pronta. Exemplo: Café Pilão Tradicional 500g por R$ 17,90.", f"Shopee pronta ({t})")
            check(await pg.input_value("#shSenha") == "••••••••••••••••" and await pg.locator("#shSenhaOk").is_visible(), "a senha aparece só como ••••")
            check((app.S.ler_json(app.pasta + "/segredos.json") or {}).get("shopee") == {"app_id": "18300000001", "secret": "segredo-shopee"}, "a senha fica no Home Assistant")
            # ----- Google -----
            await pg.click("#gSalvar")
            check(await pg.text_content("#gSt") == "Cole a chave do Google.", "sem chave: pede a chave")
            await pg.fill("#gKey", "chave-errada")
            await pg.click("#gSalvar")
            t = await st(pg, "gSt", "recusou")
            check(t == "O Google recusou a chave (403: API key not valid).", f"chave errada ({t})")
            await pg.fill("#gKey", "chave-google")
            await pg.click("#gSalvar")
            t = await st(pg, "gSt", "Pronta")
            check(t == "Pronta: 1 farmácias a até 1 km, a mais perto é Farmácia Bem Estar (0,5 km).", f"Google pronto ({t})")
            # ----- Brave e Instagram -----
            await pg.fill("#bKey", "chave-brave")
            await pg.click("#bSalvar")
            check(await st(pg, "bSt", "Pronta") == "Pronta: o app procura o site das lojas que o mapa não traz.", "Brave pronto")
            await pg.fill("#iKey", "EAAG-chave-instagram")
            await pg.click("#iSalvar")
            t = await st(pg, "iSt", "Pronta")
            check(t == "Pronta: conta @casa. Consigo ler os posts das contas comerciais das lojas. A chave não vence.", f"Instagram pronto ({t})")
            await pg.locator('#v-mais section[aria-labelledby="h-shopee"]').screenshot(path=SHOTS + "/ecic-shopee.png")
            # recarregar: tudo ligado, nenhuma chave volta para a página
            await pg.reload()
            await pg.wait_for_timeout(1000)
            await pg.click('.tabbar [data-view="mais"]')
            await pg.click("#aba-integracoes")
            await st(pg, "iSt", "Ligado")
            check(await pg.text_content("#shSt") == "Ligada. Os preços da Shopee vêm direto da Shopee.", "Shopee ligada")
            check(await pg.text_content("#gSt") == "Ligada: as lojas vêm do OpenStreetMap e do Google Maps.", "Google ligado")
            check(await pg.text_content("#iSt") == "Ligado com a conta @casa: os encartes postados pelas lojas entram na busca.", "Instagram ligado, com a conta")
            html = await pg.content()
            check(all(x not in html for x in ("segredo-shopee", "chave-google", "chave-brave", "EAAG-chave")), "nenhuma chave está na página")
            await pg.click("#gApagar")
            await st(pg, "gSt", "Desligada")
            check("google" not in (app.S.ler_json(app.pasta + "/segredos.json") or {}), "Apagar tira a chave do Google")
            await pg.click("#shApagar")
            await st(pg, "shSt", "Desligada")
            # ----- IA do Home Assistant -----
            opts = [t.strip() for t in await pg.locator("#iaBusca option").all_inner_texts()]
            check(opts == ["Padrão do Home Assistant", "Tarefa de IA: Claude", "Tarefa de IA: OpenAI", "Assistente: Gemini"], f"IAs para buscar ({opts})")
            fotos = [t.strip() for t in await pg.locator("#iaFotos option").all_inner_texts()]
            check(fotos == ["Padrão do Home Assistant", "Claude", "(não lê imagens) OpenAI"], f"IAs para fotos ({fotos})")
            await pg.select_option("#iaBusca", "ai_task.claude")
            t = await st(pg, "iaBuscaSt", "Pronta")
            check(t == "Pronta para buscar ofertas. Exemplo: Giassi, café por R$ 19,90", f"testa sozinho ao escolher ({t})")
            check(app.config_salva()["ia"]["busca"] == "ai_task.claude" and ha.chamadas_ia[-1]["entity_id"] == "ai_task.claude", "escolhida e usada")
            await pg.select_option("#iaFotos", "ai_task.openai")
            t = await st(pg, "iaFotosSt", "não lê")
            check(t == "Essa IA não lê imagens." and "erro" in await pg.get_attribute("#iaFotosSt", "class"), "IA de fotos que não lê imagens")
            await pg.locator('#v-mais section[aria-labelledby="h-ia"]').screenshot(path=SHOTS + "/ecic-ia.png")
            # ----- Uso da IA -----
            await pg.click("#aba-dados")
            await pg.click("#aba-integracoes")
            await espera(pg, "() => document.querySelectorAll('#usoChart .uso-bar').length === 7")
            try:  # o gráfico já estava desenhado com o uso de antes: espera chegar a contagem nova (o Testar de agora há pouco)
                await espera(pg, "() => /^\\s*hoje\\s*1\\b/i.test(document.querySelector('#usoTiles .uso-tile').innerText)", 8000)
            except Exception:  # noqa: BLE001  (o check abaixo mostra o que ficou)
                pass
            tiles = [t.replace("\n", " ") for t in await pg.locator("#usoTiles .uso-tile").all_inner_texts()]
            check(tiles[0].upper().startswith("HOJE 1") and tiles[1].upper().startswith("7 DIAS 3") and "1 vez sem cota" in tiles[1], f"quadros de uso ({tiles})")
            check((await pg.text_content("#usoCap")).startswith("Hoje: 1 chamada"), "hoje no gráfico")
            await pg.locator("#usoChart .uso-bar").nth(5).click()
            cap = await pg.text_content("#usoCap")
            check(cap.endswith(f"{(HOJE - timedelta(days=1)):%d/%m}: 2 chamadas, 1 sem cota."), f"tocar na barra de ontem ({cap})")
            tipos = await pg.text_content("#usoTipos")
            check("Busca de ofertas 2" in tipos and "Testes 1" in tipos, f"por tipo ({tipos})")
            ult = await pg.text_content("#usoUlt")
            check("Testes" in ult and "cota excedida" in ult and "Claude" in ult, "últimas chamadas, com o resultado e o nome da IA")
            prov = await pg.text_content("#usoProv")
            check("Consumo exato e custo da OpenAI" in prov, f"o painel do provedor de uma das IAs escolhidas (fotos: OpenAI) ({prov[:90]})")
            await pg.locator('#v-mais section[aria-labelledby="h-uso"]').screenshot(path=SHOTS + "/ecic-uso.png")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
