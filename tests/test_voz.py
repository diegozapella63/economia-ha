"""Falar: as falas para texto do Home Assistant (os assistentes de voz pelo WebSocket e as entidades stt.*), a escolha
em Mais, a que sumiu, o áudio mandado para /api/stt/<motor> com o X-Speech-Content e os erros; IA desligada, fora do
Home Assistant e o modo simulado (OFERTAS_VOZ_SIMULADA)."""
import os

from apoio import Cenario, limpa, servidor
from ha_falso import estado

UM_SEGUNDO = b"\0\1" * 16000


class Falar(Cenario):
    def setUp(self):
        super().setUp()
        ha = self.ha
        ha.estados["stt.home_assistant_cloud"] = estado("stt.home_assistant_cloud", "unknown", friendly_name="Home Assistant Cloud")
        ha.estados["stt.faster_whisper"] = estado("stt.faster_whisper", "unknown", friendly_name="Faster Whisper")
        ha.pipelines = {"pipelines": [{"id": "p1", "name": "Casa", "stt_engine": "stt.home_assistant_cloud", "stt_language": "pt-BR"},
                                      {"id": "p2", "name": "Só texto", "stt_engine": None}], "preferred_pipeline": "p1"}

    def test_opcoes_e_escolha(self):
        S, ha = self.S, self.ha
        self.config()
        st = S.voz_status()
        self.assertEqual(st["opcoes"], [{"id": "pipeline:p1", "nome": "Assistente: Casa (Home Assistant Cloud)", "preferido": True},
                                        {"id": "stt.faster_whisper", "nome": "Fala para texto: Faster Whisper", "preferido": False}],
                         "o assistente sem fala para texto fica de fora; a entidade que o assistente usa não repete")
        self.assertEqual({k: st[k] for k in ("pronta", "motor", "idioma", "usando", "escolha", "escolha_sumiu")},
                         {"pronta": True, "motor": "stt.home_assistant_cloud", "idioma": "pt-BR", "usando": "pipeline:p1", "escolha": "",
                          "escolha_sumiu": False})
        self.assertEqual(ha.ws_comandos, [{"id": 1, "type": "assist_pipeline/pipeline/list"}])
        self.assertTrue(ha.pedidos_de("/api/websocket", "WS"))
        self.config(ia={"voz": "stt.faster_whisper"})
        st = S.voz_status()
        self.assertEqual((st["usando"], st["motor"], st["escolha"]), ("stt.faster_whisper", "stt.faster_whisper", "stt.faster_whisper"))
        self.config(ia={"voz": "stt.sumiu"})
        st = S.voz_status()
        self.assertEqual((st["usando"], st["escolha_sumiu"]), ("pipeline:p1", True), "a escolhida sumiu: vale a preferida")

    def test_audio_para_texto(self):
        S, ha = self.S, self.ha
        self.config(ia={"voz": "stt.faster_whisper"})
        r = S.voz_texto(UM_SEGUNDO)
        self.assertEqual(r, {"texto": "leite integral e café", "nome": "Fala para texto: Faster Whisper"})
        p = ha.pedidos_de("/api/stt/")[-1]
        self.assertEqual(p[1], "/api/stt/stt.faster_whisper")
        self.assertEqual(p[2]["X-Speech-Content"], "format=wav; codec=pcm; sample_rate=16000; bit_rate=16; channel=1; language=pt-BR")
        self.assertEqual(p[2]["Authorization"], "Bearer " + ha.token)
        self.assertEqual(p[3], UM_SEGUNDO, "o áudio vai cru")
        for status, corpo, msg in ((415, {"message": "unsupported"}, "A fala para texto não aceitou o áudio"),
                                   (500, "", r"A fala para texto do Home Assistant falhou \(500"),
                                   (200, {"result": "error", "text": ""}, "Não entendi. Tente de novo")):
            ha.stt = (status, corpo)
            with self.assertRaisesRegex(S.ErroBusca, msg):
                S.voz_texto(UM_SEGUNDO)
        with self.assertRaisesRegex(S.ErroBusca, "Não ouvi nada"):
            S.voz_texto(b"\0" * 1000)
        with self.assertRaisesRegex(S.ErroBusca, "Fale até 2 minutos"):
            S.voz_texto(b"\0" * (S.voz.MAX_BYTES + 2))

    def test_sem_fala_para_texto(self):
        S, ha = self.S, self.ha
        self.config()
        for e in [e for e in ha.estados if e.startswith("stt.")]:
            ha.estados.pop(e)
        ha.pipelines = {"pipelines": [], "preferred_pipeline": None}
        st = S.voz_status()
        self.assertFalse(st["pronta"])
        self.assertIn("precisa de um assistente de voz com fala para texto", st["motivo"])
        with self.assertRaisesRegex(S.ErroBusca, "precisa de um assistente de voz"):
            S.voz_texto(UM_SEGUNDO)

    def test_websocket_recusado_ainda_usa_as_entidades(self):
        S, ha = self.S, self.ha
        self.config()
        ha.ws_aceita = False
        st = S.voz_status()
        self.assertEqual([o["id"] for o in st["opcoes"]], ["stt.faster_whisper", "stt.home_assistant_cloud"])
        self.assertTrue(any("Assistentes de voz" in str(m) for m in self.log))

    def test_ia_desligada_e_fora_do_home_assistant(self):
        S = self.S
        self.config(usar_ia=False)
        self.assertEqual(S.voz_status(), {"pronta": False, "motivo": "A IA está desligada em Mais › Integrações."})
        with self.assertRaisesRegex(S.ErroBusca, "A IA está desligada"):
            S.voz_texto(UM_SEGUNDO)
        self.config()
        os.environ.pop("SUPERVISOR_TOKEN")
        self.assertEqual(S.voz_status(), {"pronta": False, "motivo": "Fora do Home Assistant não dá para falar."})


class FalaSimulada(Cenario):
    def test_modo_simulado(self):
        S, pasta, _ = servidor({"OFERTAS_VOZ_SIMULADA": "1"})
        try:
            S.gravar_config({"cep": "1"})
            st = S.voz_status()
            self.assertTrue(st["pronta"])
            self.assertEqual([o["id"] for o in st["opcoes"]], ["pipeline:simulado", "stt.simulada_2"])
            self.assertIn("leite integral", S.voz_texto(UM_SEGUNDO)["texto"])
        finally:
            limpa(pasta)
