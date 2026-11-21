# EconomIA 1.46.0: o cartão Falar (Mais › Configurações › Integrações, depois do IA), com os textos dos outros apps.
# EconomIA 1.10.0: Mais › Integrações › Para falar com o voz.py igual ao do GerencIA: uma linha por motor de fala para
# texto (o nome do Home Assistant, sem "Assistente:" nem "Fala para texto:"); a escolha de antes (um assistente,
# "pipeline:<id>") aparece como o motor dele; escolher outro grava o id do motor.
import asyncio

from playwright.async_api import async_playwright

from base_e2e import CEP, SHOTS, App, HAFalso, abrir_mais, check, espera, estado, pagina, resumo


async def main():
    ha = HAFalso()
    ha.tarefa_ia("ai_task.claude", "Claude")
    ha.estados["stt.home_assistant_cloud"] = estado("stt.home_assistant_cloud", "unknown", friendly_name="Home Assistant Cloud")
    ha.estados["stt.faster_whisper"] = estado("stt.faster_whisper", "unknown", friendly_name="Faster Whisper")
    ha.pipelines = {"pipelines": [{"id": "p1", "name": "Casa", "stt_engine": "stt.home_assistant_cloud", "stt_language": "pt-BR"}], "preferred_pipeline": "p1"}
    cfg = {"cep": CEP, "categorias": ["mercados"], "lista": [], "ia": {"fotos": "ai_task.claude", "busca": "ai_task.claude", "voz": "pipeline:p1"}}
    with App(cfg, buscar=False, ha=ha) as app:
        async with async_playwright() as p:
            b, pg = await pagina(p)
            await pg.goto(app.url)
            await pg.wait_for_timeout(1200)
            await abrir_mais(pg, "integracoes")
            await espera(pg, "() => /Pronto para ouvir/.test(document.getElementById('vozSt').textContent)")
            # 1.46.0: o cartão Falar, depois do IA, com os textos dos outros apps
            sec = pg.locator('section[aria-labelledby="h-falar"]')
            ids = await pg.evaluate("() => [...document.querySelectorAll('#mp-integracoes > section > .set-head h2')].map((h) => h.id)")
            check(ids[:4] == ["h-correria", "h-ia", "h-falar", "h-uso"] and (await pg.locator("#h-falar").inner_text()).strip() == "Falar" and await pg.locator("#h-falar .h-ic svg").count() == 1,
                  f"1.46.0: o cartão Falar depois do IA, com o ícone ({ids[:4]})")
            check((await sec.locator(".set-head .sec-meta").inner_text()).strip() == "Quem transforma a fala em texto. Não muda o assistente de voz do Home Assistant.", "o texto de cima, o dos outros apps")
            check(await pg.locator('section[aria-labelledby="h-ia"] #iaVoz').count() == 0 and "Para falar" not in await pg.locator('section[aria-labelledby="h-ia"]').inner_text(), "o Para falar saiu do cartão IA")
            ops = await pg.eval_on_selector_all("#iaVoz option", "os => os.map(o => [o.value, o.textContent])")
            check(ops == [["", "Automático"], ["stt.home_assistant_cloud", "Home Assistant Cloud"], ["stt.faster_whisper", "Faster Whisper"]],
                  f"Fala para texto: Automático e uma linha por motor, com o nome do Home Assistant ({ops})")
            check((await sec.locator(".set-t").inner_text()).strip() == "Fala para texto" and await sec.locator(".set-t svg").count() == 1, "o campo Fala para texto, com o ícone")
            check(await pg.input_value("#iaVoz") == "stt.home_assistant_cloud", "a escolha de antes (o assistente Casa) aparece como o motor dele")
            check(" ".join((await pg.text_content("#vozSt")).split()) == "Pronto para ouvir · Transcreve com Home Assistant Cloud." and await pg.get_attribute("#vozSt", "class") == "ia-st ok", "Pronto para ouvir · Transcreve com…, sem aviso de que sumiu")
            check(await pg.locator("#vozComo").is_hidden(), "com fala para texto, sem o Como configurar")
            bt = sec.locator("#vozTestar")
            check((await bt.inner_text()).strip() == "Verificar de novo" and await bt.locator("svg").count() == 1 and round((await bt.bounding_box())["height"]) == 50, "o Verificar de novo, com o ícone e 50 px")
            await pg.select_option("#iaVoz", "stt.faster_whisper")
            await espera(pg, "() => /Transcreve com Faster Whisper/.test(document.getElementById('vozSt').textContent)")
            check((app.config_salva().get("ia") or {}).get("voz") == "stt.faster_whisper", "grava o id do motor")
            await pg.select_option("#iaVoz", "")
            await espera(pg, "() => document.querySelector('#iaVoz option').textContent === 'Automático: Home Assistant Cloud'")
            check((app.config_salva().get("ia") or {}).get("voz") == "", "Automático: diz qual é o motor (o preferido do Home Assistant)")
            # o motor escolhido some do Home Assistant: vale o automático, e a tela diz
            await pg.select_option("#iaVoz", "stt.faster_whisper")
            await espera(pg, "() => /Faster Whisper/.test(document.getElementById('vozSt').textContent)")
            del ha.estados["stt.faster_whisper"]
            await pg.click("#vozTestar")
            await espera(pg, "() => /não foi encontrado/.test(document.getElementById('vozSt').textContent)")
            check(" ".join((await pg.text_content("#vozSt")).split()) == "Pronto para ouvir · Transcreve com Home Assistant Cloud. O escolhido não foi encontrado: usando o automático."
                  and await pg.input_value("#iaVoz") == "", "o escolhido sumiu: usando o automático")
            check(await pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), "nada passa da largura")
            await sec.screenshot(path=SHOTS + "/ecf-falar.png")
            # sem nenhuma fala para texto: Sem fala para texto e o Como configurar
            del ha.estados["stt.home_assistant_cloud"]
            ha.pipelines = {"pipelines": [], "preferred_pipeline": None}
            await pg.click("#vozTestar")
            await espera(pg, "() => /Sem fala para texto/.test(document.getElementById('vozSt').textContent)")
            como = " ".join((await pg.locator("#vozComo").inner_text()).split())
            check(await pg.locator("#vozLinha").is_hidden() and await pg.get_attribute("#vozSt", "class") == "ia-st erro" and como.startswith("Como configurar")
                  and "Com o Home Assistant Cloud, a fala para texto já vem pronta." in como and "Whisper (local, de graça) com a integração Wyoming" in como
                  and "toque em Verificar de novo e escolha o motor na lista." in como, f"sem fala para texto: o Como configurar, com os três passos ({como[:80]})")
            await sec.screenshot(path=SHOTS + "/ecf-falar-sem.png")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
