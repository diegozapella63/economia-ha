"""Falar: o que você diz vai para a fala para texto do Home Assistant e volta como texto, que a IA lê
como uma mensagem colada. O mesmo arquivo no GerencIA e no EconomIA (tools/iguais.py: ao mudar, copie para o outro);
no CronologIA, no ResolvIA e no MemorIA, o lib/voice.js faz o mesmo em Node.

O motor é o escolhido no app (uma lista, como a da IA: uma linha por motor de fala para texto) ou, sem escolha, o do
assistente de voz preferido (Configurações › Assistentes de voz; com o Home Assistant Cloud, stt.home_assistant_cloud),
com o idioma dele; sem assistente, a primeira entidade stt.*. Uma escolha de antes, de um assistente ("pipeline:<id>"),
vale como o motor dele.
O áudio chega do app como PCM cru, 16 kHz, 16 bits, mono (o mesmo que o Assist manda).
Só biblioteca padrão do Python: o WebSocket do Home Assistant é falado à mão (ConexaoWS, que o GerencIA também usa
para escutar os e-mails).
"""
import base64
import http.client
import json
import os
import select
import socket
import ssl
import struct
import time
from urllib.parse import quote, urlparse

TAXA = 16000
MIN_BYTES = int(TAXA * 2 * 0.4)    # menos de 0,4 s: não falou nada
MAX_BYTES = TAXA * 2 * 125         # pouco mais de 2 minutos


class ErroVoz(Exception):
    pass


class ConexaoWS:
    """Uma conexão com a API WebSocket do Home Assistant, falada à mão: aperto de mão, autenticação, mandar e ler
    mensagens JSON (o ping do Home Assistant é respondido sozinho). Serve para uma pergunta (_ws_comando) e para
    ficar escutando eventos (emails.py)."""

    def __init__(self, url, token, timeout=10):
        u = urlparse(url)
        seguro = u.scheme == "wss"
        porta = u.port or (443 if seguro else 80)
        self.s = socket.create_connection((u.hostname, porta), timeout=timeout)
        self.buf = bytearray()
        try:
            if seguro:
                self.s = ssl.create_default_context().wrap_socket(self.s, server_hostname=u.hostname)
            chave = base64.b64encode(os.urandom(16)).decode()
            caminho = (u.path or "/") + (f"?{u.query}" if u.query else "")
            self.s.sendall((f"GET {caminho} HTTP/1.1\r\nHost: {u.hostname}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                            f"Sec-WebSocket-Key: {chave}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
            resp = b""
            while b"\r\n\r\n" not in resp:
                pedaco = self.s.recv(4096)
                if not pedaco:
                    raise ErroVoz("O Home Assistant não aceitou a conexão.")
                resp += pedaco
            cab, resto = resp.split(b"\r\n\r\n", 1)
            if b" 101" not in cab.split(b"\r\n", 1)[0]:
                raise ErroVoz("O Home Assistant não aceitou a conexão.")
            self.buf.extend(resto)
            self.ler()  # auth_required
            self.enviar({"type": "auth", "access_token": token})
            if self.ler().get("type") != "auth_ok":
                raise ErroVoz("O Home Assistant recusou o acesso do app.")
        except BaseException:
            self.fechar()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.fechar()

    def _receber(self, n):
        while len(self.buf) < n:
            pedaco = self.s.recv(65536)
            if not pedaco:
                raise ErroVoz("O Home Assistant fechou a conexão.")
            self.buf.extend(pedaco)
        out = bytes(self.buf[:n])
        del self.buf[:n]
        return out

    def enviar(self, dados, op=1):
        if isinstance(dados, (dict, list)):
            dados = json.dumps(dados).encode()
        mascara = os.urandom(4)
        n = len(dados)
        cab = bytes([0x80 | op])
        if n < 126:
            cab += bytes([0x80 | n])
        elif n < 65536:
            cab += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            cab += bytes([0x80 | 127]) + struct.pack(">Q", n)
        self.s.sendall(cab + mascara + bytes(c ^ mascara[i % 4] for i, c in enumerate(dados)))

    def ler(self, espera=None):
        """A próxima mensagem (dict). Com espera (segundos), devolve None se nada começar a chegar nesse tempo."""
        texto = b""
        while True:
            if espera is not None and not texto and not self.buf and not (hasattr(self.s, "pending") and self.s.pending()):
                if not select.select([self.s], [], [], espera)[0]:
                    return None
            b1, b2 = self._receber(2)
            op, n = b1 & 0x0F, b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._receber(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._receber(8))[0]
            mascara = self._receber(4) if b2 & 0x80 else None
            dados = self._receber(n)
            if mascara:
                dados = bytes(c ^ mascara[i % 4] for i, c in enumerate(dados))
            if op == 8:
                raise ErroVoz("O Home Assistant fechou a conexão.")
            if op == 9:
                self.enviar(dados, 10)  # ping: responde pong
                continue
            if op in (0, 1):
                texto += dados
                if b1 & 0x80:
                    return json.loads(texto.decode("utf-8"))

    def fechar(self):
        try:
            self.enviar(b"", 8)
        except Exception:  # noqa: BLE001
            pass
        try:
            self.s.close()
        except Exception:  # noqa: BLE001
            pass


def _ws_comando(url, token, comando, timeout=10):
    """Uma pergunta à API WebSocket do Home Assistant: conecta, autentica, manda o comando e devolve o resultado."""
    with ConexaoWS(url, token, timeout) as c:
        c.enviar({"id": 1, **comando})
        while True:
            m = c.ler()
            if m.get("id") == 1 and m.get("type") == "result":
                if not m.get("success"):
                    raise ErroVoz((m.get("error") or {}).get("message") or "O Home Assistant recusou o pedido.")
                return m.get("result")


class Voz:
    def __init__(self, rest, ws, token, log, simulada=False, texto_simulado="Um texto de teste"):
        """simulada: sem o Home Assistant (testes e prévia), duas falas de mentira; texto_simulado é o que elas "ouvem"."""
        self.rest, self.ws, self.token, self.log, self.simulada = rest, ws, token, log, simulada
        self.texto_simulado = texto_simulado
        self.cache = None

    def _ler(self):
        """Assistentes de voz e entidades stt.* do Home Assistant. Guardado por um minuto."""
        if self.cache and time.time() - self.cache[0] < 60:
            return self.cache[1]
        pipes, pref, ents = [], None, []
        if self.token:
            try:
                r = _ws_comando(self.ws, self.token, {"type": "assist_pipeline/pipeline/list"}) or {}
                pipes = [x for x in (r.get("pipelines") or []) if x.get("stt_engine")]
                pref = r.get("preferred_pipeline")
            except Exception as e:  # noqa: BLE001
                self.log("Assistentes de voz:", e)
            try:
                u = urlparse(self.rest)
                c = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=15)
                c.request("GET", u.path.rstrip("/") + "/states", headers={"Authorization": f"Bearer {self.token}"})
                r = c.getresponse()
                estados = json.loads(r.read() or b"[]") if r.status == 200 else []
                ents = [x for x in estados if str(x.get("entity_id", "")).startswith("stt.")]
            except Exception as e:  # noqa: BLE001
                self.log("Fala para texto:", e)
        valor = (pipes, pref, ents)
        self.cache = (time.time(), valor)
        return valor

    def opcoes(self):
        """Lista para escolher, como a IA usada pelo app: [{id, nome, idioma, assistentes, preferido}].
        Uma por motor de fala para texto (entidade stt.* ou o motor de um assistente de voz)."""
        if self.simulada:
            return [{"id": "stt.simulada", "nome": "Fala simulada (teste)", "idioma": "pt-BR", "assistentes": ["Home Assistant"], "preferido": True},
                    {"id": "stt.outra_simulada", "nome": "Outra fala simulada (teste)", "idioma": "pt-BR", "assistentes": [], "preferido": False}]
        pipes, pref, ents = self._ler()
        lista = {}
        for p in pipes:
            o = lista.setdefault(p["stt_engine"], {"id": p["stt_engine"], "nome": "", "idioma": "", "assistentes": [], "preferido": False})
            o["assistentes"].append(p.get("name") or "")
            if p.get("id") == pref:
                o["preferido"] = True
                o["idioma"] = p.get("stt_language") or p.get("language") or o["idioma"]
            elif not o["idioma"]:
                o["idioma"] = p.get("stt_language") or p.get("language") or ""
        for e in ents:
            o = lista.setdefault(e["entity_id"], {"id": e["entity_id"], "nome": "", "idioma": "", "assistentes": [], "preferido": False})
            o["nome"] = (e.get("attributes") or {}).get("friendly_name") or ""
        for o in lista.values():
            o["nome"] = o["nome"] or (o["assistentes"][0] if o["assistentes"] else o["id"])
            o["idioma"] = o["idioma"] or "pt-BR"
            o["assistentes"] = [a for a in o["assistentes"] if a]
        return sorted(lista.values(), key=lambda o: (not o["preferido"], o["nome"].lower()))

    def _resolver(self, escolha):
        """A escolha guardada no app como o id de um motor: "pipeline:<id>" (um assistente, como se guardava antes)
        vira o motor dele; "" se não houver escolha."""
        escolha = str(escolha or "").strip()
        if escolha.startswith("pipeline:"):
            pid = escolha.split(":", 1)[1]
            pipes = [{"id": "simulado", "stt_engine": "stt.simulada"}] if self.simulada else self._ler()[0]
            return next((p["stt_engine"] for p in pipes if str(p.get("id")) == pid), escolha)
        return escolha

    def motor(self, escolha=""):
        """{engine, language, name} da fala para texto a usar, ou None: a escolhida no app ou, sem escolha
        (ou se ela sumiu do Home Assistant), a do assistente de voz preferido."""
        ops, escolha = self.opcoes(), self._resolver(escolha)
        o = next((x for x in ops if escolha and x["id"] == escolha), None) \
            or next((x for x in ops if x["preferido"]), None) or (ops[0] if ops else None)
        return {"engine": o["id"], "language": o["idioma"], "name": o["nome"]} if o else None

    def status(self, escolha=""):
        """Pronta ou o motivo; com o motor que vai ser usado, a lista para escolher, a escolhida (se ainda existe) e se
        a escolhida sumiu do Home Assistant (escolha_sumiu: o app avisa que está usando outra)."""
        ops = self.opcoes()
        m = self.motor(escolha)
        if not m:
            return {"pronta": False, "opcoes": [], "motivo": "Para falar, o Home Assistant precisa de um assistente de voz com fala para texto "
                                                             "(Configurações › Assistentes de voz; com o Home Assistant Cloud ele já vem pronto)."}
        resolvida = self._resolver(escolha)
        existe = any(o["id"] == resolvida for o in ops)
        return {"pronta": True, "motor": m["engine"], "idioma": m["language"], "nome": m["name"], "opcoes": ops, "usando": m["engine"],
                "selecionada": resolvida if existe else "", "escolha_sumiu": bool(resolvida) and not existe}

    def texto(self, pcm, escolha=""):
        """PCM cru (16 kHz, 16 bits, mono) para texto."""
        if not pcm or len(pcm) < MIN_BYTES:
            raise ErroVoz("Não ouvi nada. Toque no microfone e fale.")
        if len(pcm) > MAX_BYTES:
            raise ErroVoz("Fale até 2 minutos de cada vez.")
        m = self.motor(escolha)
        if not m:
            raise ErroVoz(self.status(escolha)["motivo"])
        if self.simulada:
            time.sleep(0.8)
            return {"texto": self.texto_simulado, "nome": m["name"]}
        u = urlparse(self.rest)
        # nomes dos cabeçalhos escritos exatamente assim: o proxy do Supervisor só repassa "X-Speech-Content" desse jeito
        c = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=90)
        try:
            c.putrequest("POST", u.path.rstrip("/") + "/stt/" + quote(m["engine"]), skip_accept_encoding=True)
            c.putheader("Authorization", f"Bearer {self.token}")
            c.putheader("Content-Type", "application/octet-stream")
            c.putheader("X-Speech-Content", f"format=wav; codec=pcm; sample_rate={TAXA}; bit_rate=16; channel=1; language={m['language']}")
            c.putheader("Content-Length", str(len(pcm)))
            c.endheaders()
            c.send(pcm)
            r = c.getresponse()
            corpo = r.read().decode("utf-8", "replace")
        except (OSError, http.client.HTTPException) as e:
            raise ErroVoz(f"Sem resposta da fala para texto do Home Assistant ({e}).")
        finally:
            c.close()
        if not 200 <= r.status < 300:
            self.cache = None
            det = corpo[:200]
            self.log(f"Fala para texto ({m['engine']}): {r.status} {det}")
            raise ErroVoz(f"A fala para texto não aceitou o áudio ({det or r.status})." if r.status in (400, 415)
                          else f"A fala para texto do Home Assistant falhou ({r.status}{': ' + det if det else ''}).")
        try:
            j = json.loads(corpo)
        except ValueError:
            j = {}
        txt = str(j.get("text") or "").strip()
        if j.get("result") != "success" or not txt:
            raise ErroVoz("Não entendi. Tente de novo, mais perto do microfone.")
        return {"texto": txt, "nome": m["name"]}
