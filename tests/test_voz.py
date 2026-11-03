"""Falar: as falas para texto do Home Assistant (os assistentes de voz pelo WebSocket e as entidades stt.*), a escolha
em Mais, a que sumiu, o áudio mandado para /api/stt/<motor> com o X-Speech-Content e os erros; IA desligada, fora do
Home Assistant e o modo simulado (OFERTAS_VOZ_SIMULADA)."""
import json
import os
import socket
import struct
import sys
import threading
import unittest
from pathlib import Path

from apoio import Cenario, limpa, servidor
from ha_falso import estado

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "economia" / "app"))


class _Voz:
    """O voz.py, importado só quando um teste usa: assim a medição de cobertura (que começa depois de carregar os
    testes) vê o módulo inteiro."""

    def __getattr__(self, nome):
        import voz as m
        return getattr(m, nome)


voz = _Voz()

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


class Voz(Cenario):
    """A classe Voz direto, com o Home Assistant falso: estados com erro, fala para texto que não responde ou não manda JSON."""

    def voz(self, rest=None):
        return voz.Voz(rest or self.ha.base + "/api", self.ha.base.replace("http", "ws") + "/api/websocket", self.ha.token,
                       lambda *a: self.log.append(" ".join(map(str, a))))

    def test_estados_com_erro_ou_sem_resposta(self):
        ha = self.ha
        ha.estados["stt.faster_whisper"] = estado("stt.faster_whisper", "unknown", friendly_name="Faster Whisper")
        ha.pipelines = {"pipelines": [{"id": "p1", "name": "", "stt_engine": "stt.faster_whisper", "language": "en-US"}], "preferred_pipeline": None}
        ops = self.voz().opcoes()
        self.assertEqual(ops, [{"id": "pipeline:p1", "nome": "Assistente: sem nome (Faster Whisper)", "engine": "stt.faster_whisper",
                                "language": "en-US", "preferido": False}], "sem stt_language: o idioma do assistente")
        v = self.voz()
        v.token = "outro"
        self.assertEqual(v.opcoes(), [], "token recusado: nada, sem quebrar")
        self.assertTrue(any("Assistentes de voz:" in str(m) for m in self.log))
        self.log.clear()
        v = voz.Voz("http://127.0.0.1:9/api", "ws://127.0.0.1:9/api/websocket", "t", lambda *a: self.log.append(" ".join(map(str, a))))
        self.assertEqual(v.opcoes(), [])
        self.assertTrue(any(m.startswith("Fala para texto:") for m in self.log), self.log)
        self.assertIsNone(v.motor())

    def test_guardado_por_um_minuto(self):
        ha = self.ha
        ha.estados["stt.a"] = estado("stt.a", "unknown")
        v = self.voz()
        self.assertEqual([o["nome"] for o in v.opcoes()], ["Fala para texto: stt.a"], "sem nome: o id")
        ha.estados.pop("stt.a")
        self.assertEqual(len(v.opcoes()), 1, "guardado")
        v.cache = (v.cache[0] - 61, v.cache[1])
        self.assertEqual(v.opcoes(), [])

    def test_fala_para_texto_sem_resposta_ou_sem_json(self):
        ha = self.ha
        ha.estados["stt.a"] = estado("stt.a", "unknown", friendly_name="A")
        v = self.voz()
        v.opcoes()
        ha.stt = (200, "isto não é JSON")
        with self.assertRaisesRegex(voz.ErroVoz, "Não entendi"):
            v.texto(UM_SEGUNDO)
        ha.stt = (200, {"result": "success", "text": "   "})
        with self.assertRaisesRegex(voz.ErroVoz, "Não entendi"):
            v.texto(UM_SEGUNDO)
        ha.stt = (400, "")
        with self.assertRaisesRegex(voz.ErroVoz, r"não aceitou o áudio \(400\)"):
            v.texto(UM_SEGUNDO)
        self.assertIsNone(v.cache, "erro: as opções são lidas de novo")
        v.cache = (9e18, [{"id": "stt.a", "nome": "A", "engine": "stt.a", "language": "pt-BR", "preferido": False}])
        v.rest = "http://127.0.0.1:9/api"
        with self.assertRaisesRegex(voz.ErroVoz, "Sem resposta da fala para texto do Home Assistant"):
            v.texto(UM_SEGUNDO)


def quadro(dados, op=1, fin=True, mascara=None):
    """Um quadro WebSocket do servidor (sem máscara, a não ser que peça)."""
    if isinstance(dados, (dict, list)):
        dados = json.dumps(dados).encode()
    n = len(dados)
    cab = bytes([(0x80 if fin else 0) | op])
    m = 0x80 if mascara else 0
    cab += bytes([m | n]) if n < 126 else bytes([m | 126]) + struct.pack(">H", n) if n < 65536 else bytes([m | 127]) + struct.pack(">Q", n)
    if mascara:
        cab += mascara
        dados = bytes(c ^ mascara[i % 4] for i, c in enumerate(dados))
    return cab + dados


class Conexao:
    def __init__(self, s):
        self.s, self.buf = s, b""

    def le(self, n):
        while len(self.buf) < n:
            p = self.s.recv(65536)
            if not p:
                raise OSError("fechou")
            self.buf += p
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def aperto(self, linha=b"HTTP/1.1 101 Switching Protocols"):
        while b"\r\n\r\n" not in self.buf:
            self.buf += self.s.recv(4096)
        self.pedido, self.buf = self.buf.split(b"\r\n\r\n", 1)
        self.s.sendall(linha + b"\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n")

    def recebe(self):
        b1, b2 = self.le(2)
        n = b2 & 0x7F
        if n == 126:
            n = struct.unpack(">H", self.le(2))[0]
        elif n == 127:
            n = struct.unpack(">Q", self.le(8))[0]
        m = self.le(4)
        return b1 & 0x0F, bytes(c ^ m[i % 4] for i, c in enumerate(self.le(n)))

    def manda(self, *quadros):
        self.s.sendall(b"".join(quadros))

    def entra(self):
        self.aperto()
        self.manda(quadro({"type": "auth_required"}))
        self.auth = json.loads(self.recebe()[1])
        self.manda(quadro({"type": "auth_ok"}))
        self.cmd = json.loads(self.recebe()[1])


class WebSocketCru(unittest.TestCase):
    """_ws_comando contra um servidor de soquete com roteiro: o que o Home Assistant pode mandar de diferente."""

    def roda(self, roteiro, comando=None, esquema="ws"):
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        srv.settimeout(10)
        self.recebidos = []

        def atende():
            try:
                c, _ = srv.accept()
                c.settimeout(10)
                cx = Conexao(c)
                try:
                    roteiro(cx)
                    while True:  # o que o app manda depois (o fechamento)
                        self.recebidos.append(cx.recebe())
                except OSError:
                    pass
                finally:
                    c.close()
            except OSError:
                pass
            finally:
                srv.close()

        t = threading.Thread(target=atende, daemon=True)
        t.start()
        try:
            return voz._ws_comando(f"{esquema}://127.0.0.1:{srv.getsockname()[1]}/api/websocket?x=1", "tok", comando or {"type": "x"}, timeout=5)
        finally:
            t.join(10)

    def test_resposta_normal_com_ping_eventos_e_pedacos(self):
        vistos = {}

        def roteiro(cx):
            cx.aperto()
            vistos["pedido"] = cx.pedido.split(b"\r\n")[0]
            cx.manda(quadro(b"oi", op=9), quadro({"type": "auth_required"}))
            vistos["pong"] = cx.recebe()
            vistos["auth"] = json.loads(cx.recebe()[1])
            cx.manda(quadro({"type": "auth_ok"}, mascara=b"\1\2\3\4"))
            vistos["cmd"] = json.loads(cx.recebe()[1])
            msg = json.dumps({"id": 1, "type": "result", "success": True, "result": {"ok": "sim"}}).encode()
            cx.manda(quadro({"id": 7, "type": "event"}), quadro(msg[:10], fin=False), quadro(msg[10:], op=0))

        self.assertEqual(self.roda(roteiro, {"type": "assist_pipeline/pipeline/list"}), {"ok": "sim"})
        self.assertEqual(vistos["pedido"], b"GET /api/websocket?x=1 HTTP/1.1")
        self.assertEqual(vistos["pong"], (10, b"oi"), "ping: responde pong com o mesmo conteúdo")
        self.assertEqual(vistos["auth"], {"type": "auth", "access_token": "tok"})
        self.assertEqual(vistos["cmd"], {"id": 1, "type": "assist_pipeline/pipeline/list"})
        self.assertEqual(self.recebidos[0][0], 8, "no fim, fecha a conexão")

    def test_mensagens_grandes_nos_dois_sentidos(self):
        grande = {"type": "x", "dados": "a" * 70000}
        medio = {"result": "b" * 300}
        vistos = {}

        def roteiro(cx):
            cx.entra()
            vistos["cmd"] = cx.cmd
            cx.manda(quadro({"id": 1, "type": "result", "success": True, "result": {"m": medio, "g": "c" * 70000}}))

        r = self.roda(roteiro, grande)
        self.assertEqual((r["m"], len(r["g"])), (medio, 70000))
        self.assertEqual(vistos["cmd"], {"id": 1, **grande})

        def roteiro2(cx):
            cx.entra()
            vistos["cmd"] = cx.cmd
            cx.manda(quadro({"id": 1, "type": "result", "success": True, "result": 1}))

        self.assertEqual(self.roda(roteiro2, {"type": "x", "dados": "d" * 500}), 1)
        self.assertEqual(len(vistos["cmd"]["dados"]), 500)

    def test_erros(self):
        def sem_101(cx):
            cx.aperto(b"HTTP/1.1 403 Forbidden")

        def fecha_no_aperto(cx):
            cx.s.recv(4096)
            cx.s.shutdown(socket.SHUT_RDWR)

        def auth_invalido(cx):
            cx.aperto()
            cx.manda(quadro({"type": "auth_required"}))
            cx.recebe()
            cx.manda(quadro({"type": "auth_invalid"}))

        def resultado(erro):
            def r(cx):
                cx.entra()
                cx.manda(quadro({"id": 1, "type": "result", "success": False, **erro}))
            return r

        def fecha_quadro(cx):
            cx.entra()
            cx.manda(quadro(b"", op=8))

        def corta(cx):
            cx.entra()
            cx.s.sendall(quadro({"id": 1, "type": "result", "success": True, "result": "longo" * 20})[:20])
            cx.s.shutdown(socket.SHUT_RDWR)

        for roteiro, msg in ((sem_101, "não aceitou a conexão"), (fecha_no_aperto, "não aceitou a conexão"),
                             (auth_invalido, "recusou o acesso do app"),
                             (resultado({"error": {"code": "x", "message": "Comando desconhecido."}}), "Comando desconhecido."),
                             (resultado({}), "O Home Assistant recusou o pedido."),
                             (fecha_quadro, "fechou a conexão"), (corta, "fechou a conexão")):
            with self.subTest(msg=msg):
                with self.assertRaisesRegex(voz.ErroVoz, msg):
                    self.roda(roteiro)

    def test_wss_usa_conexao_segura(self):
        visto = {}

        class Ctx:
            def wrap_socket(self, s, server_hostname=None):
                visto["host"] = server_hostname
                return s

        orig = voz.ssl.create_default_context
        voz.ssl.create_default_context = lambda: Ctx()
        try:
            def roteiro(cx):
                cx.entra()
                cx.manda(quadro({"id": 1, "type": "result", "success": True, "result": "ok"}))
            r = self.roda(roteiro, esquema="wss")
        finally:
            voz.ssl.create_default_context = orig
        self.assertEqual((r, visto["host"]), ("ok", "127.0.0.1"))


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
