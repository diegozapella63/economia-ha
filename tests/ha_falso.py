"""Home Assistant de mentira para os testes do EconomIA: a API REST que o add-on usa (ha_api) e o WebSocket do Falar.

- REST em {base}/api: /states (todo.*, ai_task.*, conversation.*, stt.*, zone.home, sensores), POST/DELETE /states/<id>,
  /services/ai_task/generate_data, /services/conversation/process, /services/todo/get_items e add_item, /stt/<motor>.
- WebSocket em {ws}: auth_required → auth → auth_ok e o comando assist_pipeline/pipeline/list.
- Respostas da IA com roteiro: responde_ia(quando, resposta, vezes) — quando é um trecho do task_name (ou uma função
  que recebe o corpo do pedido); resposta é um dict (data estruturada), um texto (a IA respondeu em texto), Erro(código,
  corpo) ou uma função que recebe o corpo e devolve um desses.
- Guarda tudo o que chegou em pedidos (método, caminho, cabeçalhos, corpo) para os testes conferirem.

Só biblioteca padrão, num thread, como as LojasFalsas.
"""
import base64
import hashlib
import json
import struct
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = "token-do-supervisor-de-teste"


def cala_desistencia(srv):
    """handle_error do servidor falso: o app que desiste no meio (tempo esgotado, conexão fechada) não é erro do teste;
    o resto (um erro no roteiro do teste) continua aparecendo."""
    padrao = srv.handle_error

    def h(pedido, endereco):
        if isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError)):
            return
        padrao(pedido, endereco)
    return h


class Erro:
    """Resposta de erro do Home Assistant: o código HTTP e o corpo."""

    def __init__(self, codigo, corpo=""):
        self.codigo, self.corpo = codigo, corpo if isinstance(corpo, str) else json.dumps(corpo)


def estado(entidade, valor="on", **atributos):
    return {"entity_id": entidade, "state": valor, "attributes": atributos}


class HAFalso:
    def __init__(self, token=TOKEN):
        self.token = token
        self.estados = {}            # entity_id -> estado
        self.todos = {}              # todo.x -> [{"uid", "summary", "status"}]
        self.regras_ia = []          # [{"quando", "resp", "vezes"}]
        self.regras_conversa = []    # [{"quando", "resp", "vezes"}] resp: (texto, response_type)
        self.ia_padrao = Erro(500, "sem roteiro para este pedido de IA")
        self.stt = (200, {"result": "success", "text": "leite integral e café"})
        self.pipelines = {"pipelines": [], "preferred_pipeline": None}
        self.ws_aceita = True        # False: recusa o token no WebSocket
        self.pedidos = []            # (método, caminho, cabeçalhos, corpo)
        self.chamadas_ia = []        # corpos de ai_task/generate_data
        self.ws_comandos = []
        self._uid = 0
        self._trava = threading.Lock()
        self.estados["zone.home"] = estado("zone.home", "0", latitude=-26.30, longitude=-48.85, friendly_name="Casa")

    # ----- atalhos para montar o cenário -----
    def tarefa_ia(self, entidade, nome, anexos=True):
        self.estados[entidade] = estado(entidade, "unknown", friendly_name=nome, supported_features=3 if anexos else 1)

    def agente(self, entidade, nome):
        self.estados[entidade] = estado(entidade, "unknown", friendly_name=nome)

    def lista(self, entidade, nome, itens=()):
        self.estados[entidade] = estado(entidade, str(len(itens)), friendly_name=nome)
        self.todos[entidade] = [dict(it) for it in itens]

    def item(self, entidade, resumo, status="needs_action"):
        self._uid += 1
        it = {"uid": f"uid-{self._uid}", "summary": resumo, "status": status}
        self.todos.setdefault(entidade, []).append(it)
        return it

    def responde_ia(self, quando, resposta, vezes=None):
        self.regras_ia.append({"quando": quando, "resp": resposta, "vezes": vezes})

    def responde_conversa(self, quando, texto, tipo="action_done", vezes=None):
        self.regras_conversa.append({"quando": quando, "resp": (texto, tipo), "vezes": vezes})

    def pedidos_de(self, trecho, metodo=None):
        return [p for p in self.pedidos if trecho in p[1] and (metodo is None or p[0] == metodo)]

    def tudo_que_chegou(self):
        """Todo o texto que o add-on mandou para o Home Assistant (caminhos, cabeçalhos e corpos)."""
        return "\n".join(f"{m} {c} {json.dumps(h, ensure_ascii=False)} {b if isinstance(b, str) else json.dumps(b, ensure_ascii=False)}"
                         for m, c, h, b in self.pedidos)

    def env(self):
        return {"OFERTAS_HA_API": self.api, "OFERTAS_HA_WS": self.ws, "SUPERVISOR_TOKEN": self.token}

    # ----- servidor -----
    def __enter__(self):
        dono = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def _out(self, d, cod=200):
                b = d if isinstance(d, bytes) else (d.encode() if isinstance(d, str) else json.dumps(d).encode())
                self.send_response(cod)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def _corpo(self):
                n = int(self.headers.get("Content-Length") or 0)
                return self.rfile.read(n) if n else b""

            def _ok(self):
                if self.headers.get("Authorization") != "Bearer " + dono.token:
                    self._out({"message": "Invalid authentication"}, 401)
                    return False
                return True

            def do_GET(self):
                if self.headers.get("Upgrade", "").lower() == "websocket":
                    dono.pedidos.append(("WS", self.path, dict(self.headers), ""))
                    return dono._websocket(self)
                dono.pedidos.append(("GET", self.path, dict(self.headers), ""))
                if self._ok():
                    dono._get(self)

            def do_POST(self):
                bruto = self._corpo()
                try:
                    corpo = json.loads(bruto.decode("utf-8")) if bruto else None
                except (ValueError, UnicodeDecodeError):
                    corpo = bruto
                dono.pedidos.append(("POST", self.path, dict(self.headers), corpo))
                if self._ok():
                    dono._post(self, corpo)

            def do_DELETE(self):
                dono.pedidos.append(("DELETE", self.path, dict(self.headers), ""))
                if self._ok():
                    ent = urllib.parse.urlsplit(self.path).path.split("/api/states/", 1)[-1]
                    existia = dono.estados.pop(ent, None)
                    self._out({"message": "Entity removed."} if existia else {"message": "Entity not found."}, 200 if existia else 404)

        self._srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self._srv.handle_error = cala_desistencia(self._srv)
        self._srv.daemon_threads = True
        self.porta = self._srv.server_address[1]
        self.base = f"http://127.0.0.1:{self.porta}"
        self.api = self.base + "/api"
        self.ws = f"ws://127.0.0.1:{self.porta}/api/websocket"
        threading.Thread(target=self._srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        return self

    def __exit__(self, *a):
        self._srv.shutdown()
        self._srv.server_close()

    # ----- REST -----
    def _get(self, h):
        caminho = urllib.parse.urlsplit(h.path).path
        if caminho == "/api/states":
            return h._out(list(self.estados.values()))
        if caminho.startswith("/api/states/"):
            e = self.estados.get(caminho.split("/api/states/", 1)[1])
            return h._out(e) if e else h._out({"message": "Entity not found."}, 404)
        h._out({"message": "not found"}, 404)

    def _regra(self, regras, corpo, chave):
        with self._trava:
            for r in regras:
                q = r["quando"]
                bate = q(corpo) if callable(q) else q in str((corpo or {}).get(chave) or "")
                if bate and r["vezes"] != 0:
                    if r["vezes"]:
                        r["vezes"] -= 1
                    return r["resp"]
        return None

    def _post(self, h, corpo):
        u = urllib.parse.urlsplit(h.path)
        caminho = u.path
        if caminho == "/api/services/ai_task/generate_data":
            self.chamadas_ia.append(corpo)
            ent = (corpo or {}).get("entity_id")
            if ent and ent not in self.estados:
                return h._out(f"Entity {ent} not found", 400)
            resp = self._regra(self.regras_ia, corpo, "task_name")
            resp = self.ia_padrao if resp is None else resp
            if callable(resp):
                resp = resp(corpo)
            if isinstance(resp, Erro):
                return h._out(resp.corpo.encode(), resp.codigo)
            return h._out({"changed_states": [], "service_response": {"conversation_id": "c1", "data": resp}})
        if caminho == "/api/services/conversation/process":
            resp = self._regra(self.regras_conversa, corpo, "agent_id") or ("", "error")
            if callable(resp):
                resp = resp(corpo)
            if isinstance(resp, Erro):
                return h._out(resp.corpo.encode(), resp.codigo)
            texto, tipo = resp
            return h._out({"changed_states": [], "service_response": {
                "response": {"speech": {"plain": {"speech": texto, "extra_data": None}}, "card": {}, "language": "pt-BR",
                             "response_type": tipo, "data": {}}, "conversation_id": "c2", "continue_conversation": False}})
        if caminho == "/api/services/todo/get_items":
            ent = (corpo or {}).get("entity_id")
            status = set((corpo or {}).get("status") or ["needs_action", "completed"])
            itens = [dict(i) for i in self.todos.get(ent, []) if i["status"] in status]
            return h._out({"changed_states": [], "service_response": {ent: {"items": itens}}})
        if caminho == "/api/services/todo/add_item":
            ent, nome = (corpo or {}).get("entity_id"), (corpo or {}).get("item")
            self.item(ent, nome)
            return h._out([])
        if caminho.startswith("/api/states/"):
            ent = caminho.split("/api/states/", 1)[1]
            novo = ent not in self.estados
            self.estados[ent] = {"entity_id": ent, "state": str((corpo or {}).get("state")), "attributes": (corpo or {}).get("attributes") or {}}
            return h._out(self.estados[ent], 201 if novo else 200)
        if caminho.startswith("/api/stt/"):
            st, d = self.stt
            return h._out(d, st)
        h._out({"message": "not found"}, 404)

    # ----- WebSocket (só o que o Falar precisa) -----
    def _websocket(self, h):
        chave = h.headers.get("Sec-WebSocket-Key", "")
        aceite = base64.b64encode(hashlib.sha1((chave + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
        h.wfile.write(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                       f"Sec-WebSocket-Accept: {aceite}\r\n\r\n").encode())
        h.wfile.flush()
        h.close_connection = True

        def manda(d):
            b = json.dumps(d).encode()
            cab = bytes([0x81]) + (bytes([len(b)]) if len(b) < 126 else bytes([126]) + struct.pack(">H", len(b)) if len(b) < 65536
                                   else bytes([127]) + struct.pack(">Q", len(b)))
            h.wfile.write(cab + b)
            h.wfile.flush()

        def recebe():
            b1, b2 = h.rfile.read(2)
            op, n = b1 & 0x0F, b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", h.rfile.read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", h.rfile.read(8))[0]
            mascara = h.rfile.read(4) if b2 & 0x80 else b"\0\0\0\0"
            dados = bytes(c ^ mascara[i % 4] for i, c in enumerate(h.rfile.read(n)))
            return op, dados

        try:
            manda({"type": "auth_required", "ha_version": "2026.11.0"})
            op, dados = recebe()
            auth = json.loads(dados or b"{}")
            if not self.ws_aceita or auth.get("access_token") != self.token:
                manda({"type": "auth_invalid", "message": "Invalid access token"})
                return
            manda({"type": "auth_ok", "ha_version": "2026.11.0"})
            while True:
                op, dados = recebe()
                if op == 8:
                    return
                cmd = json.loads(dados)
                self.ws_comandos.append(cmd)
                if cmd.get("type") == "assist_pipeline/pipeline/list":
                    manda({"id": cmd["id"], "type": "result", "success": True, "result": self.pipelines})
                else:
                    manda({"id": cmd["id"], "type": "result", "success": False, "error": {"code": "unknown_command", "message": "Unknown command."}})
        except (OSError, ValueError):
            return
