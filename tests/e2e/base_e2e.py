"""Base dos testes visuais do EconomIA: lojas falsas, dados preparados pela busca de verdade, o servidor do add-on
num processo e o Chromium do Playwright. Cada teste é um script: python3 tests/e2e/ec_lista.py

- check(cond, texto) imprime PASS ou FAIL (o run.sh falha com qualquer FAIL ou Traceback)
- as capturas vão para $E2E_TMP/shots (sem E2E_TMP, uma pasta temporária)
- png_codigo() desenha um código de barras EAN-13/EAN-8 num PNG, sem biblioteca de imagem
"""
import os
import random
import socket
import struct
import subprocess
import sys
import tempfile
import time
import zlib

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))  # tests/, para o apoio.py

from apoio import APP, CEP, LojasFalsas, categoria, ean13, porta_livre, prod, servidor  # noqa: E402,F401
from ha_falso import Erro, HAFalso, estado  # noqa: E402,F401

TMP = os.environ.get("E2E_TMP") or tempfile.mkdtemp(prefix="economia-e2e-")
SHOTS = os.path.join(TMP, "shots")
os.makedirs(SHOTS, exist_ok=True)

_passou, _falhou = 0, []


def check(cond, texto):
    global _passou
    print(("PASS " if cond else "FAIL ") + " ".join(str(texto).split()), flush=True)
    if cond:
        _passou += 1
    else:
        _falhou.append(texto)


def resumo():
    print(f"{_passou} checks passed" if not _falhou else f"{len(_falhou)} FAILED, {_passou} passed", flush=True)


def shot(pg, nome, **kw):
    return pg.screenshot(path=os.path.join(SHOTS, nome + ".png"), **kw)


class App:
    """Lojas falsas + dados + servidor do add-on. Use com `with App(...) as app:`; app.url é o endereço da página.
    ha=HAFalso() liga o Home Assistant falso (IA, listas, fala para texto); servicos=True aponta o mapa, o Brave, o
    Instagram, a Shopee e os sites de encartes para as lojas falsas; env: variáveis a mais para o servidor."""

    def __init__(self, config, buscar=True, preparar=None, antes=None, ha=None, servicos=False, env=None):
        self.config, self.buscar, self.preparar, self.antes = config, buscar, preparar, antes
        self.ha, self.servicos, self.env_extra = ha, servicos, env or {}

    def __enter__(self):
        self.lojas = LojasFalsas().__enter__()
        if self.ha:
            self.ha.__enter__()
        if self.preparar:
            self.preparar(self.lojas)
        S, self.pasta, self.log = servidor(self.lojas.env())
        self.S = S
        S.gravar_config(dict(self.config))
        if self.antes:  # o que o teste quer pronto antes da busca (vocabulário, segredos…)
            self.antes(S)
        if self.buscar:  # a busca de verdade, contra as lojas falsas, grava o ofertas.json que a página mostra
            S.mesclar_resultado(S.busca_direta(S.ler_config()), S.ler_config(), completa=True)
            S.grava_vocab()
        self.porta = porta_livre()
        env = dict(os.environ, OFERTAS_DATA=self.pasta, OFERTAS_PORT=str(self.porta), OFERTAS_ALLOW_ALL="1",
                   OFERTAS_MEDIA=os.path.join(self.pasta, "media"), OFERTAS_SHARE=os.path.join(self.pasta, "share"), OFERTAS_HA_API="http://127.0.0.1:9/api",
                   OFERTAS_HA_WS="ws://127.0.0.1:9/websocket", SUPERVISOR_TOKEN="", OFERTAS_ESPERA_COTA="0", OFERTAS_SYNC_SEG="3600")
        env.update(self.lojas.env_servicos() if self.servicos else self.lojas.env())
        if self.ha:
            env.update(self.ha.env())
        env.update(self.env_extra)
        self.saida = open(os.path.join(TMP, f"servidor-{self.porta}.log"), "w")
        self.proc = subprocess.Popen([sys.executable, os.path.join(APP, "server.py")], env=env, stdout=self.saida, stderr=subprocess.STDOUT)
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", self.porta), 0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        self.url = f"http://127.0.0.1:{self.porta}/"
        return self

    def __exit__(self, *a):
        self.proc.terminate()
        self.proc.wait(10)
        self.saida.close()
        if self.ha:
            self.ha.__exit__()
        self.lojas.__exit__()

    def config_salva(self):
        return self.S.ler_json(os.path.join(self.pasta, "config.json"), {})

    def ofertas_salvas(self):
        return self.S.ler_json(os.path.join(self.pasta, "ofertas.json"), {})

    def api(self, metodo, caminho, corpo=None):
        """Um pedido direto à API do servidor (para preparar o cenário ou conferir)."""
        import json
        import urllib.request
        req = urllib.request.Request(self.url + caminho.lstrip("/"), method=metodo, data=json.dumps(corpo).encode() if corpo is not None else None,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read() or b"null")


async def espera(pg, js, ms=15000):
    """Espera uma condição na página (sem sleep fixo)."""
    await pg.wait_for_function(js, timeout=ms)


CONFIG_ABAS = ("integracoes", "dados", "aparencia", "opcoes")


async def abrir_mais(pg, onde, computador=False):
    """Mais é um menu (1.3.0): abre Mais pela barra de baixo (no computador, pela lateral) e a linha da tela (casa, lojas,
    config ou sobre). Uma aba de Configurações (integracoes, dados, aparencia, opcoes) abre Configurações nessa aba."""
    await pg.click('#lado [data-lado="mais"]' if computador else '.tabbar [data-view="mais"]')
    # vindo de outra tela de Mais, a entrada dela no histórico é desfeita (history.back): espera antes de abrir a nova
    await espera(pg, "() => !(history.state && history.state.tela) && !document.getElementById('maisMenu').hidden")
    tela = "config" if onde in CONFIG_ABAS else onde
    await pg.click(f'#maisMenu [data-mais="{tela}"]')
    if tela == "config":
        await pg.click("#aba-" + onde)


async def pagina(p, largura=412, altura=892, escuro=True, args=None, permissoes=None, toque=True):
    b = await p.chromium.launch(args=args or [])
    ctx = await b.new_context(viewport={"width": largura, "height": altura}, device_scale_factor=2,
                              color_scheme="dark" if escuro else "light", has_touch=toque, permissions=permissoes or [],
                              accept_downloads=True)
    pg = await ctx.new_page()
    pg.erros = []
    pg.on("pageerror", lambda e: pg.erros.append(str(e)))
    return b, pg


# ---------- código de barras em PNG (cinza, 8 bits), sem PIL ----------
_L = ["0001101", "0011001", "0010011", "0111101", "0100011", "0110001", "0101111", "0111011", "0110111", "0001011"]
_G = ["".join("1" if c == "0" else "0" for c in x)[::-1] for x in _L]
_R = ["".join("1" if c == "0" else "0" for c in x) for x in _L]
_P = ["LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG", "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL"]


def bits_ean(c):
    if len(c) == 8:
        return "101" + "".join(_L[int(x)] for x in c[:4]) + "01010" + "".join(_R[int(x)] for x in c[4:]) + "101"
    b = "101" + "".join((_L if _P[int(c[0])][i] == "L" else _G)[int(x)] for i, x in enumerate(c[1:7])) + "01010"
    return b + "".join(_R[int(x)] for x in c[7:]) + "101"


def png_codigo(codigo, modulo=4, altura=160, girar=0, borrar=0, ruido=0.0, luz=True, fundo=(900, 640), semente=1):
    """PNG com o código no meio de um fundo maior. girar: 0, 90 ou 180; borrar: raio da média; ruido: fração de pontos."""
    rnd = random.Random(semente)
    bits = bits_ean(codigo)
    w_cod = (len(bits) + 22) * modulo
    W, H = fundo
    img = [[150 + (60 * x // W if luz else 0) for x in range(W)] for _ in range(H)]
    x0, y0 = (W - w_cod) // 2, (H - altura - 20) // 2
    for y in range(y0 - 10, y0 + altura + 20):
        for x in range(x0, x0 + w_cod):
            img[y][x] = 250
    for i, b in enumerate(bits):
        if b == "1":
            for y in range(y0, y0 + altura):
                for x in range(x0 + (11 + i) * modulo, x0 + (12 + i) * modulo):
                    img[y][x] = 20
    if borrar:
        r = borrar
        for y in range(H):
            linha, acc = img[y], []
            s = sum(linha[:r])
            for x in range(W):
                if x + r < W:
                    s += linha[x + r]
                if x - r - 1 >= 0:
                    s -= linha[x - r - 1]
                n = min(W - 1, x + r) - max(0, x - r) + 1
                acc.append(s // n)
            img[y] = acc
    if ruido:
        for _ in range(int(W * H * ruido)):
            img[rnd.randrange(H)][rnd.randrange(W)] = rnd.randint(0, 255)
    if girar == 180:
        img = [linha[::-1] for linha in img[::-1]]
    elif girar == 90:
        img = [list(c) for c in zip(*img[::-1])]
    H, W = len(img), len(img[0])
    cru = b"".join(b"\x00" + bytes(linha) for linha in img)

    def bloco(tipo, dados):
        return struct.pack(">I", len(dados)) + tipo + dados + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 0, 0, 0, 0)) + bloco(b"IDAT", zlib.compress(cru, 6)) + bloco(b"IEND", b"")
