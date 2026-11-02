"""Apoio dos testes do EconomIA: o servidor carregado do zero, numa pasta de dados só do teste, e lojas falsas.

- servidor(): importa economia/app/server.py de novo (sem o cache das buscas anteriores), com /data numa pasta
  temporária e os endereços das lojas, do Mercado Livre e do Open Food Facts apontando para o LojasFalsas.
- LojasFalsas: um servidor HTTP local que responde como a busca da VTEX (regiões, busca por texto, por código de
  barras e por seção), o OAuth e o previsor de categorias do Mercado Livre, o Open Food Facts e páginas soltas.
- prod(): um produto no formato da intelligent-search da VTEX.

Só biblioteca padrão do Python, como o próprio app.
"""
import importlib
import json
import os
import re
import shutil
import socket
import sys
import tempfile
import threading
import unicodedata
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, "economia", "app")
CEP = "89216120"


def norm(t):
    return re.sub(r"[^a-z0-9]+", " ", unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().lower()).strip()


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", norm(t)).strip("-")


def porta_livre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def prod(nome, preco, secao=None, un="un", mult=1, ean="", de=None, estoque=50, marca=None, link=None):
    """Produto da VTEX. secao: "Açougue/Aves" vira categories ["/Açougue/Aves/", "/Açougue/"]."""
    cats = []
    if secao:
        partes = [p for p in secao.strip("/").split("/") if p]
        cats = ["/" + "/".join(partes[:i]) + "/" for i in range(len(partes), 0, -1)]
    return {"categories": cats, "productName": nome, "brand": marca or nome.split()[0], "link": link or ("/" + slug(nome) + "/p"),
            "items": [{"itemId": "1", "ean": ean, "measurementUnit": un, "unitMultiplier": mult,
                       "sellers": [{"sellerId": "1", "commertialOffer": {"Price": preco, "ListPrice": de or preco, "AvailableQuantity": estoque}}]}]}


def ean13(base12):
    """Completa 12 dígitos com o dígito verificador."""
    s = sum(int(x) * (3 if i % 2 == 0 else 1) for i, x in enumerate(reversed(base12)))
    return base12 + str((10 - s % 10) % 10)


class LojasFalsas:
    """Lojas VTEX, Mercado Livre e Open Food Facts de mentira, num servidor local de verdade."""

    def __init__(self):
        self.catalogo = {}  # loja -> [produtos]
        self.regioes = {"giassi": "giassi08", "angeloni": "superangeloni21"}
        self.paginas = {}  # caminho -> (status, corpo, tipo)
        self.off = {}  # ean -> product
        self.ml_classes = []  # [(função(texto normalizado) -> bool, domínio, categoria, nome)]
        self.ml = {"acesso": None, "refresh": None, "n": 0, "app": "123456", "segredo": "segredo-ml",
                   "codigo": "TG-abc123", "volta": "https://www.google.com", "status_previsor": 200}
        self.pedidos = []  # (método, caminho, cabeçalhos)
        self._srv = None

    # ----- servidor -----
    def __enter__(self):
        dono = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _out(self, d, cod=200, tipo="application/json"):
                b = d if isinstance(d, bytes) else (d.encode() if isinstance(d, str) else json.dumps(d).encode())
                self.send_response(cod)
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def do_GET(self):
                dono.pedidos.append(("GET", self.path, dict(self.headers)))
                dono._get(self)

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                corpo = self.rfile.read(n).decode() if n else ""
                dono.pedidos.append(("POST", self.path, dict(self.headers), corpo))
                dono._post(self, corpo)

        self._srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.porta = self._srv.server_address[1]
        self.base = f"http://127.0.0.1:{self.porta}"
        threading.Thread(target=self._srv.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *a):
        self._srv.shutdown()
        self._srv.server_close()

    def env(self):
        return {"OFERTAS_VTEX_TESTE": self.base, "OFERTAS_ML_API": self.base + "/ml", "OFERTAS_ML_AUTH": self.base + "/ml-auth",
                "OFERTAS_OFF": self.base + "/off"}

    # ----- respostas -----
    def _get(self, h):
        u = urllib.parse.urlsplit(h.path)
        q = urllib.parse.parse_qs(u.query)
        caminho = u.path
        if caminho in self.paginas:
            st, corpo, tipo = self.paginas[caminho]
            return h._out(corpo, st, tipo)
        if caminho.startswith("/ml/sites/MLB/domain_discovery/search"):
            if h.headers.get("Authorization") != f"Bearer {self.ml['acesso']}":
                return h._out({"message": "invalid access token", "error": "unauthorized", "status": 401}, 401)
            if self.ml["status_previsor"] != 200:
                return h._out({"message": "too many requests"}, self.ml["status_previsor"])
            t = norm((q.get("q") or [""])[0])
            lim = int((q.get("limit") or ["4"])[0])
            out = [{"domain_id": d, "domain_name": n, "category_id": c, "category_name": n, "attributes": []}
                   for f, d, c, n in self.ml_classes if f(t)]
            return h._out(out[:lim])
        if caminho.startswith("/off/api/v2/product/"):
            ean = caminho.rsplit("/", 1)[-1].split(".")[0]
            p = self.off.get(ean)
            return h._out({"status": 1, "product": p} if p else {"status": 0, "status_verbose": "product not found"})
        partes = caminho.strip("/").split("/")
        loja = partes[0] if partes else ""
        if "regions" in caminho:
            sel = self.regioes.get(loja)
            return h._out([{"id": "v2." + loja, "sellers": [{"id": sel, "name": sel}]}] if sel else [])
        if "product_search" in caminho:
            prods = self.catalogo.get(loja, [])
            resto = caminho.split("product_search", 1)[1].strip("/")
            termo = (q.get("query") or [""])[0]
            cont = int((q.get("count") or ["12"])[0])
            if resto:  # facetas: category-1/acougue/category-2/aves
                p = resto.split("/")
                slugs = [p[i + 1] for i in range(0, len(p) - 1, 2) if p[i].startswith("category-")]
                prods = [x for x in prods if x["categories"]
                         and [slug(s) for s in max(x["categories"], key=len).strip("/").split("/")][:len(slugs)] == slugs]
            elif termo.isdigit():
                prods = [x for x in prods if any(it.get("ean") == termo for it in x["items"])]
            else:
                ws = [w for w in norm(termo).split() if len(w) >= 3 and w not in ("de", "da", "do", "ou")]
                prods = [x for x in prods if any(w in norm(x["productName"]) for w in ws)]
            return h._out({"products": prods[:cont]})
        h._out({"erro": "não achei"}, 404)

    def _post(self, h, corpo):
        if h.path == "/ml/oauth/token":
            f = {k: v[0] for k, v in urllib.parse.parse_qs(corpo).items()}
            if f.get("client_id") != self.ml["app"] or f.get("client_secret") != self.ml["segredo"]:
                return h._out({"error": "invalid_client", "message": "invalid client"}, 400)
            ok = (f.get("grant_type") == "authorization_code" and f.get("code") == self.ml["codigo"] and f.get("redirect_uri") == self.ml["volta"]) or \
                 (f.get("grant_type") == "refresh_token" and f.get("refresh_token") == self.ml["refresh"])
            if not ok:
                return h._out({"error": "invalid_grant", "message": "error validating grant"}, 400)
            self.ml["n"] += 1
            self.ml["acesso"], self.ml["refresh"] = f"tok-{self.ml['n']}", f"r-{self.ml['n']}"
            return h._out({"access_token": self.ml["acesso"], "token_type": "bearer", "expires_in": 21600, "scope": "offline_access read",
                           "user_id": 1, "refresh_token": self.ml["refresh"]})
        h._out({}, 404)

    # ----- atalhos -----
    def categorias_ml_padrao(self):
        """Um previsor simples: hambúrguer, almôndega, carne bovina, frango, álcool e limpador."""
        self.ml_classes = [
            (lambda t: "hamburg" in t or "burger" in t, "MLB-HAMBURGERS", "MLB1", "Hambúrgueres"),
            (lambda t: "almondega" in t, "MLB-MEATBALLS", "MLB2", "Almôndegas"),
            (lambda t: any(w in t for w in ("carne", "moid", "acem", "patinho", "bovin")) and "hamburg" not in t and "almondega" not in t,
             "MLB-BEEF", "MLB3", "Carnes Bovinas"),
            (lambda t: any(w in t for w in ("frango", "asa", "coxa")), "MLB-CHICKEN", "MLB4", "Frango"),
            (lambda t: "limpador" in t, "MLB-CLEANERS", "MLB5", "Limpadores"),
            (lambda t: "alcool" in t and "limpador" not in t, "MLB-ALCOHOL", "MLB6", "Álcool"),
        ]

    def pedidos_de(self, trecho):
        return [p for p in self.pedidos if trecho in p[1]]


def servidor(env=None):
    """O módulo server.py carregado do zero, com a pasta de dados própria. Devolve (módulo, pasta, mensagens do log)."""
    pasta = tempfile.mkdtemp(prefix="economia-teste-")
    os.environ.update({"OFERTAS_DATA": pasta, "OFERTAS_MEDIA": os.path.join(pasta, "media"), "OFERTAS_ALLOW_ALL": "1",
                       "OFERTAS_HA_API": "http://127.0.0.1:9/api", "OFERTAS_HA_WS": "ws://127.0.0.1:9/websocket"})
    for k in ("OFERTAS_VTEX_TESTE", "OFERTAS_ML_API", "OFERTAS_ML_AUTH", "OFERTAS_OFF"):
        os.environ.pop(k, None)
    os.environ.update(env or {})
    if APP not in sys.path:
        sys.path.insert(0, APP)
    sys.modules.pop("server", None)
    S = importlib.import_module("server")
    msgs = []
    S.log = msgs.append
    return S, pasta, msgs


def limpa(pasta):
    shutil.rmtree(pasta, ignore_errors=True)


NOMES_VOCAB = [t.format(m=m) for m in ("Ypê", "Veja", "Tirol", "Omo", "Comfort", "Neve", "Pilão", "Bauducco", "Qboa", "Scotch", "Araras",
                                        "Lysoform", "Itambé", "Melitta", "Santa", "Coamo", "Limpol", "Brilhante", "Downy", "Sadia")
               for t in ("Álcool Líquido 46 INPM Limpeza {m} 1L", "Desinfetante Pinho {m} 500ml", "Detergente Líquido Neutro {m} 500ml",
                         "Sabão em Pó Lavagem Perfeita {m} 1kg", "Amaciante Concentrado {m} 1L", "Limpador Multiuso Limpeza Pesada {m} 500ml",
                         "Papel Higiênico Folha Dupla {m} 12un", "Leite Integral {m} 1L", "Peito de Frango Congelado {m} 1kg")]
