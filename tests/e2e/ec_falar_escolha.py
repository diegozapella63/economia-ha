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
            await espera(pg, "() => /Usando/.test(document.getElementById('vozSt').textContent)")
            ops = await pg.eval_on_selector_all("#iaVoz option", "os => os.map(o => [o.value, o.textContent])")
            check(ops == [["", "Padrão do Home Assistant"], ["stt.home_assistant_cloud", "Home Assistant Cloud · preferido"], ["stt.faster_whisper", "Faster Whisper"]],
                  f"uma linha por motor, com o nome do Home Assistant ({ops})")
            check(await pg.input_value("#iaVoz") == "stt.home_assistant_cloud", "a escolha de antes (o assistente Casa) aparece como o motor dele")
            check((await pg.text_content("#vozSt")).startswith("Usando Home Assistant Cloud."), "sem aviso de que sumiu")
            await pg.select_option("#iaVoz", "stt.faster_whisper")
            await espera(pg, "() => /Usando Faster Whisper/.test(document.getElementById('vozSt').textContent)")
            check((app.config_salva().get("ia") or {}).get("voz") == "stt.faster_whisper", "grava o id do motor")
            await pg.locator("#iaVoz").screenshot(path=SHOTS + "/ecf-voz.png")
            check(not pg.erros, f"sem erros na página {pg.erros}")
            await b.close()


asyncio.run(main())
resumo()
