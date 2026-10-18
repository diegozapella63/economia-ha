#!/usr/bin/env python3
"""Ofertas do Bairro: serve o painel pelo ingress do Home Assistant.

Tudo fica dentro do Home Assistant, na pasta /data do add-on:
- config.json   perfil, lista, lojas e rotina (gravado pelo painel)
- ofertas.json  ofertas das lojas perto de casa

Rotas:
- GET  /             página do painel
- GET  /api/estado   configuração, ofertas e usuário do HA que abriu a página
- PUT  /api/config   grava a configuração
- PUT  /api/ofertas  grava um novo ofertas.json

Só usa a biblioteca padrão do Python.
"""
import json
import os
import urllib.parse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DATA = os.environ.get("OFERTAS_DATA", "/data")
WWW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "www")
PORT = int(os.environ.get("OFERTAS_PORT", "8099"))
CONFIG = os.path.join(DATA, "config.json")
OFERTAS = os.path.join(DATA, "ofertas.json")
# O ingress do Supervisor chega sempre deste endereço.
INGRESS_IPS = {"172.30.32.2", "127.0.0.1", "::1"}
ALLOW_ALL = os.environ.get("OFERTAS_ALLOW_ALL") == "1"  # só para testes fora do HA
MAX_BODY = 2 * 1024 * 1024


def log(msg):
    print(f"[ofertas] {datetime.now().strftime('%H:%M:%S')} {msg}", flush=True)


def ler_json(path, padrao=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return padrao


def gravar_json(path, dado):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dado, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


class Painel(BaseHTTPRequestHandler):
    server_version = "OfertasDoBairro/0.2"

    def log_message(self, fmt, *args):
        pass

    def _permitido(self):
        if ALLOW_ALL or self.client_address[0] in INGRESS_IPS:
            return True
        self._json(403, {"erro": "Acesso só pelo Home Assistant."})
        return False

    def _json(self, codigo, dado):
        corpo = json.dumps(dado, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _corpo(self):
        tamanho = int(self.headers.get("Content-Length") or 0)
        if tamanho <= 0 or tamanho > MAX_BODY:
            self._json(413, {"erro": "Conteúdo vazio ou grande demais."})
            return None
        try:
            dado = json.loads(self.rfile.read(tamanho).decode("utf-8"))
        except ValueError:
            dado = None
        if not isinstance(dado, dict):
            self._json(400, {"erro": "Conteúdo inválido."})
            return None
        return dado

    def do_GET(self):
        if not self._permitido():
            return
        rota = urllib.parse.urlsplit(self.path).path
        if rota in ("/", "/index.html"):
            with open(os.path.join(WWW, "index.html"), "rb") as f:
                corpo = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
        elif rota == "/api/estado":
            self._json(200, {
                "config": ler_json(CONFIG),
                "ofertas": ler_json(OFERTAS),
                "usuario": self.headers.get("X-Remote-User-Display-Name") or self.headers.get("X-Remote-User-Name") or None,
            })
        elif rota == "/api/saude":
            self._json(200, {"ok": True})
        else:
            self._json(404, {"erro": "Não encontrado"})

    def do_PUT(self):
        if not self._permitido():
            return
        rota = urllib.parse.urlsplit(self.path).path
        if rota == "/api/config":
            cfg = self._corpo()
            if cfg is None:
                return
            cfg["atualizado_em"] = datetime.now(timezone.utc).isoformat()
            gravar_json(CONFIG, cfg)
            self._json(200, {"ok": True})
        elif rota == "/api/ofertas":
            dado = self._corpo()
            if dado is None:
                return
            if not isinstance(dado.get("categorias"), list):
                return self._json(400, {"erro": "Faltou a lista de categorias."})
            gravar_json(OFERTAS, dado)
            log("ofertas atualizadas")
            self._json(200, {"ok": True})
        else:
            self._json(404, {"erro": "Não encontrado"})


def main():
    os.makedirs(DATA, exist_ok=True)
    servidor = ThreadingHTTPServer(("0.0.0.0", PORT), Painel)
    log(f"painel no ar na porta {PORT}; dados em {DATA}")
    servidor.serve_forever()


if __name__ == "__main__":
    main()
