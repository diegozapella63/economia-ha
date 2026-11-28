"""Preço dos combustíveis pela ANP (1.63.0): o levantamento semanal de preços dos postos, dos dados abertos da ANP
(as quatro últimas semanas, um CSV com o país todo). Só biblioteca padrão. Daqui só se guarda o que é da cidade da casa.

O arquivo: separado por ponto e vírgula, com «Estado - Sigla», «Municipio», «Revenda», «Bairro», «Produto»,
«Data da Coleta» (DD/MM/AAAA), «Valor de Venda» (vírgula decimal) e «Bandeira». A pesquisa é por amostra: nem todo posto
aparece toda semana.
"""
import re
import unicodedata
import urllib.request
from datetime import date, timedelta

BASE = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/qus/"
ARQUIVOS = ("ultimas-4-semanas-gasolina-etanol.csv", "ultimas-4-semanas-diesel-gnv.csv")
PAGINA = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis"
LIMITE = 40 * 1024 * 1024  # o arquivo tem uns 4 MB; bem mais que isso não é ele
MAX_LINHAS = 3000
# como a pessoa fala → o nome do produto no arquivo (sem acento, minúsculo)
PRODUTOS = (("gasolina", "Gasolina"), ("gasolina aditivada", "Gasolina aditivada"), ("etanol", "Etanol"), ("diesel", "Diesel"),
            ("diesel s10", "Diesel S10"), ("gnv", "GNV"))
APELIDOS = {"alcool": "etanol", "aditivada": "gasolina aditivada", "gasolina comum": "gasolina", "comum": "gasolina", "s10": "diesel s10",
            "diesel s-10": "diesel s10", "oleo diesel": "diesel", "gas": "gnv", "gas natural": "gnv"}


def chave(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 -]", " ", s)).strip()


def produto(v):
    """O produto como o arquivo chama (em chave), pelo jeito que a pessoa fala; "" se não é um deles."""
    k = chave(v)
    k = APELIDOS.get(k, k)
    return k if k in dict(PRODUTOS) else ""


def nome_produto(k):
    return dict(PRODUTOS).get(k, str(k).capitalize())


def _colunas(cab):
    nomes = [chave(c) for c in cab]
    achar = lambda *partes: next((i for i, n in enumerate(nomes) if all(p in n for p in partes)), None)  # noqa: E731
    return {"uf": achar("estado"), "cidade": achar("municipio"), "posto": achar("revenda"), "bairro": achar("bairro"),
            "rua": achar("nome", "rua"), "numero": achar("numero"), "produto": achar("produto"), "data": achar("data"),
            "preco": achar("valor", "venda"), "bandeira": achar("bandeira")}


def _data(v):
    m = re.match(r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*$", str(v or ""))
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat() if m else ""
    except ValueError:
        return ""


def _preco(v):
    try:
        n = float(str(v or "").strip().replace(".", "").replace(",", ".")) if "," in str(v) else float(str(v).strip())
    except ValueError:
        return 0.0
    return round(n, 3) if 0.5 <= n <= 50 else 0.0


def ler(linhas, cidade, uf):
    """As linhas do arquivo (um iterável de texto) que são da cidade: [{posto, bairro, rua, bandeira, produto, data, preco}]."""
    cid, est = chave(cidade), chave(uf)
    col, out = None, []
    for bruta in linhas:
        campos = [c.strip().strip('"').strip() for c in str(bruta).rstrip("\r\n").lstrip("﻿").split(";")]
        if col is None:
            c = _colunas(campos)
            if None not in (c["uf"], c["cidade"], c["produto"], c["data"], c["preco"]):
                col = c
            continue
        pega = lambda k: campos[col[k]] if col[k] is not None and col[k] < len(campos) else ""  # noqa: E731
        if chave(pega("cidade")) != cid or (est and chave(pega("uf")) != est):
            continue
        p, dt, pr = chave(pega("produto")), _data(pega("data")), _preco(pega("preco"))
        if not p or not dt or not pr:
            continue
        rua = " ".join(x for x in (pega("rua").title(), pega("numero")) if x)
        out.append({"posto": pega("posto").title()[:80], "bairro": pega("bairro").title()[:40], "rua": rua[:80], "bandeira": pega("bandeira").title()[:30],
                    "produto": p, "data": dt, "preco": pr})
        if len(out) >= MAX_LINHAS:
            break
    if col is None:
        raise ValueError("O arquivo da ANP veio num formato que eu não conheço.")
    return out


def baixar(url, cidade, uf, timeout=60):
    """Lê o arquivo da ANP linha a linha (sem guardar o país todo) e devolve só as linhas da cidade."""
    req = urllib.request.Request(url, headers={"User-Agent": "EconomIA (Home Assistant)", "Accept": "text/csv,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        lido = [0]

        def linhas():
            for b in r:
                lido[0] += len(b)
                if lido[0] > LIMITE:
                    raise ValueError("O arquivo da ANP veio grande demais.")
                try:
                    yield b.decode("utf-8")
                except UnicodeDecodeError:
                    yield b.decode("latin-1")
        return ler(linhas(), cidade, uf)


def resumo(linhas, hoje=None, dias=10):
    """Por produto, na coleta mais recente (e as de até `dias` antes dela): {produto: {data, media, postos: [do mais barato], n}}."""
    out = {}
    for p in dict.fromkeys(x["produto"] for x in linhas):
        do_p = [x for x in linhas if x["produto"] == p]
        ultima = max(x["data"] for x in do_p)
        corte = (date.fromisoformat(ultima) - timedelta(days=dias)).isoformat()
        vale = {}
        for x in sorted(do_p, key=lambda x: x["data"]):
            if x["data"] > corte:
                vale[(x["posto"], x["rua"])] = x  # de cada posto, a coleta mais nova
        postos = sorted(vale.values(), key=lambda x: (x["preco"], x["posto"]))
        out[p] = {"data": ultima, "media": round(sum(x["preco"] for x in postos) / len(postos), 3), "n": len(postos), "postos": postos}
    return out
