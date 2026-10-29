"""Falar: o que você diz vai para a fala para texto do Home Assistant e volta como texto, que a IA lê
como uma mensagem colada (o mesmo módulo do GerencIA, do CronologIA e do ResolvIA).

O motor é o do assistente de voz preferido (Configurações › Assistentes de voz; com o Home Assistant
Cloud, stt.home_assistant_cloud), com o idioma dele; sem assistente, a primeira entidade stt.*.
O áudio chega do app como PCM cru, 16 kHz, 16 bits, mono (o mesmo que o Assist manda).
Só biblioteca padrão do Python: o WebSocket do Home Assistant é falado à mão, para uma única pergunta.
"""
import base64
import http.client
import json
import os
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


def _ws_comando(url, token, comando, timeout=10):
    """Uma pergunta à API WebSocket do Home Assistant: conecta, autentica, manda o comando e devolve o resultado."""
    u = urlparse(url)
    seguro = u.scheme == "wss"
    porta = u.port or (443 if seguro else 80)
    s = socket.create_connection((u.hostname, porta), timeout=timeout)
    if seguro:
        s = ssl.create_default_context().wrap_socket(s, server_hostname=u.hostname)
    buf = bytearray()

    def receber(n):
        while len(buf) < n:
            pedaco = s.recv(65536)
            if not pedaco:
                raise ErroVoz("O Home Assistant fechou a conexão.")
            buf.extend(pedaco)
        out = bytes(buf[:n])
        del buf[:n]
        return out

    def enviar(dados, op=1):
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
        s.sendall(cab + mascara + bytes(c ^ mascara[i % 4] for i, c in enumerate(dados)))

    def ler():
        texto = b""
        while True:
            b1, b2 = receber(2)
            op, n = b1 & 0x0F, b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", receber(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", receber(8))[0]
            mascara = receber(4) if b2 & 0x80 else None
            dados = receber(n)
            if mascara:
                dados = bytes(c ^ mascara[i % 4] for i, c in enumerate(dados))
            if op == 8:
                raise ErroVoz("O Home Assistant fechou a conexão.")
            if op == 9:
                enviar(dados, 10)  # ping: responde pong
                continue
            if op in (0, 1):
                texto += dados
                if b1 & 0x80:
                    return json.loads(texto.decode("utf-8"))

    try:
        chave = base64.b64encode(os.urandom(16)).decode()
        caminho = (u.path or "/") + (f"?{u.query}" if u.query else "")
        s.sendall((f"GET {caminho} HTTP/1.1\r\nHost: {u.hostname}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                   f"Sec-WebSocket-Key: {chave}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            pedaco = s.recv(4096)
            if not pedaco:
                raise ErroVoz("O Home Assistant não aceitou a conexão.")
            resp += pedaco
        cab, resto = resp.split(b"\r\n\r\n", 1)
        if b" 101" not in cab.split(b"\r\n", 1)[0]:
            raise ErroVoz("O Home Assistant não aceitou a conexão.")
        buf.extend(resto)
        ler()  # auth_required
        enviar({"type": "auth", "access_token": token})
        if ler().get("type") != "auth_ok":
            raise ErroVoz("O Home Assistant recusou o acesso do app.")
        enviar({"id": 1, **comando})
        while True:
            m = ler()
            if m.get("id") == 1 and m.get("type") == "result":
                if not m.get("success"):
                    raise ErroVoz((m.get("error") or {}).get("message") or "O Home Assistant recusou o pedido.")
                return m.get("result")
    finally:
        try:
            enviar(b"", 8)
        except Exception:  # noqa: BLE001
            pass
        s.close()


class Voz:
    def __init__(self, rest, ws, token, log, simulada=False):
        self.rest, self.ws, self.token, self.log, self.simulada = rest, ws, token, log, simulada
        self.cache = None

    def motor(self):
        """{engine, language, name} da fala para texto a usar, ou None. Guardado por um minuto."""
        if self.simulada:
            return {"engine": "stt.simulada", "language": "pt-BR", "name": "Fala simulada (teste)"}
        if self.cache and time.time() - self.cache[0] < 60:
            return self.cache[1]
        valor = None
        if self.token:
            try:
                r = _ws_comando(self.ws, self.token, {"type": "assist_pipeline/pipeline/list"}) or {}
                lista = r.get("pipelines") or []
                p = next((x for x in lista if x.get("id") == r.get("preferred_pipeline") and x.get("stt_engine")), None) \
                    or next((x for x in lista if x.get("stt_engine")), None)
                if p:
                    valor = {"engine": p["stt_engine"], "language": p.get("stt_language") or p.get("language") or "pt-BR", "name": p.get("name") or ""}
            except Exception as e:  # noqa: BLE001
                self.log("Assistentes de voz:", e)
            if not valor:
                try:
                    u = urlparse(self.rest)
                    c = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=15)
                    c.request("GET", u.path.rstrip("/") + "/states", headers={"Authorization": f"Bearer {self.token}"})
                    r = c.getresponse()
                    estados = json.loads(r.read() or b"[]") if r.status == 200 else []
                    st = next((x for x in estados if str(x.get("entity_id", "")).startswith("stt.")), None)
                    if st:
                        valor = {"engine": st["entity_id"], "language": "pt-BR", "name": (st.get("attributes") or {}).get("friendly_name") or st["entity_id"]}
                except Exception as e:  # noqa: BLE001
                    self.log("Fala para texto:", e)
        self.cache = (time.time(), valor)
        return valor

    def status(self):
        m = self.motor()
        if not m:
            return {"pronta": False, "motivo": "Para falar, o Home Assistant precisa de um assistente de voz com fala para texto "
                                               "(Configurações › Assistentes de voz; com o Home Assistant Cloud ele já vem pronto)."}
        return {"pronta": True, "motor": m["engine"], "idioma": m["language"], "nome": m["name"]}

    def texto(self, pcm):
        """PCM cru (16 kHz, 16 bits, mono) para texto."""
        if not pcm or len(pcm) < MIN_BYTES:
            raise ErroVoz("Não ouvi nada. Toque no microfone e fale.")
        if len(pcm) > MAX_BYTES:
            raise ErroVoz("Fale até 2 minutos de cada vez.")
        m = self.motor()
        if not m:
            raise ErroVoz(self.status()["motivo"])
        if self.simulada:
            time.sleep(0.8)
            return {"texto": "Compra leite integral, dois pacotes de café de 500 gramas e detergente", "nome": m["name"]}
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
