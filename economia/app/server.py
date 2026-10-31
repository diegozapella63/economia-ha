#!/usr/bin/env python3
"""EconomIA: serve o painel pelo ingress do Home Assistant.

Tudo fica dentro do Home Assistant, na pasta /data do add-on:
- config.json   perfil, lista, lojas e rotina (gravado pelo painel)
- ofertas.json  ofertas das lojas perto de casa (gravado pela busca)

A busca usa a IA configurada no próprio Home Assistant (ação ai_task.generate_data,
por exemplo com a integração Anthropic e a busca na web ligada).

Rotas:
- GET  /             página do painel
- GET  /api/estado   configuração, ofertas e usuário do HA que abriu a página
- PUT  /api/config   grava a configuração
- PUT  /api/ofertas  grava um ofertas.json pronto
- POST /api/buscar   começa a busca agora
- POST /api/buscar-itens   {"itens": [...]} busca só esses itens e junta ao resultado
- GET  /api/uso-ia   chamadas de IA por dia, tipo e resultado (e sensor.economia_ia_hoje, se ligado)
- GET  /api/voz/status   se o Falar está pronto e com qual fala para texto
- POST /api/voz   áudio PCM 16 kHz, 16 bits, mono → {"texto"} pela fala para texto do Home Assistant
- GET  /api/versoes   cópias anteriores do config.json (as 3 mais recentes)
- GET  /api/lojas-diretas   lojas com busca direta no site (Giassi, Angeloni) e se atendem o CEP
- POST /api/versoes/guardar {"motivo"} | /api/versoes/restaurar {"nome"}
- GET  /api/busca    andamento da busca
- GET  /api/exportar/lista.xlsx | lista.json   exporta a lista
- GET  /api/todos    listas de tarefas do Home Assistant
- POST /api/sincronizar-lista   sincroniza agora com a lista do Home Assistant
- POST /api/ler-lista   lê fotos ou texto (do WhatsApp, por exemplo) e sugere itens
- GET  /api/ler-lista?id=...   resultado da leitura
- GET  /api/ias    tarefas de IA e assistentes de conversa do Home Assistant
- POST /api/testar-ia   testa a IA escolhida para buscar ofertas ou ler fotos

Só usa a biblioteca padrão do Python.
"""
import base64
import html as html_mod
import io
import json
import os
import re
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from xml.sax.saxutils import escape as xml_esc
import shutil
import zipfile

import voz

DATA = os.environ.get("OFERTAS_DATA", "/data")
WWW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "www")
PORT = int(os.environ.get("OFERTAS_PORT", "8099"))
CONFIG = os.path.join(DATA, "config.json")
OFERTAS = os.path.join(DATA, "ofertas.json")
OPTIONS = os.path.join(DATA, "options.json")
USO_FILE = os.path.join(DATA, "uso_ia.json")
VERSOES = os.path.join(DATA, "versoes")
MAX_VERSOES = 3
INTERVALO_VERSAO = 600  # uma cópia a cada 10 minutos de uso, no máximo
SYNC_FILE = os.path.join(DATA, "sync_ha.json")
SYNC_INTERVALO = int(os.environ.get("OFERTAS_SYNC_SEG", "60"))
ESPERA_COTA = int(os.environ.get("OFERTAS_ESPERA_COTA", "60"))
AUTO_ENCARTES = int(os.environ.get("OFERTAS_AUTO_ENCARTES", "2"))  # sites lidos sozinhos por busca
HA_API = os.environ.get("OFERTAS_HA_API", "http://supervisor/core/api")
HA_WS = os.environ.get("OFERTAS_HA_WS", "ws://supervisor/core/websocket")
VOZ_SIMULADA = os.environ.get("OFERTAS_VOZ_SIMULADA") == "1"  # só para testes fora do HA
# O ingress do Supervisor chega sempre deste endereço.
INGRESS_IPS = {"172.30.32.2", "127.0.0.1", "::1"}
ALLOW_ALL = os.environ.get("OFERTAS_ALLOW_ALL") == "1"  # só para testes fora do HA
MAX_BODY = 2 * 1024 * 1024
MAX_FOTOS_BODY = 16 * 1024 * 1024
# fotos ficam um instante na pasta de mídia do HA, para a IA ler, e são apagadas em seguida
MEDIA = os.environ.get("OFERTAS_MEDIA", "/media")
MEDIA_URI = os.environ.get("OFERTAS_MEDIA_URI", "media-source://media_source/local")
LEITURAS = {}

CATEGORIAS = {
    "farmacias": {"nome": "Farmácias", "singular": "Farmácia", "o_que": "farmácias e drogarias, de rede ou independentes"},
    "mercados": {"nome": "Mercados", "singular": "Mercado", "o_que": "supermercados, hipermercados e atacarejos"},
    "petshops": {"nome": "Pet shops", "singular": "Pet shop", "o_que": "pet shops e lojas de produtos para animais"},
    "online": {"nome": "Online", "singular": "Online", "o_que": "marketplaces com entrega no CEP"},
}
MARKETPLACES = {"ifood": "iFood", "rappi": "Rappi", "mercadolivre": "Mercado Livre", "amazon": "Amazon", "shopee": "Shopee", "magalu": "Magalu",
                "americanas": "Americanas", "casasbahia": "Casas Bahia"}
ASSINATURAS = {"prime": "Amazon Prime", "melimais": "Meli+", "clubeifood": "Clube iFood"}
TAGS = {"bebe", "pet", "gato", "cachorro", "alcool", "medicamento", "maquiagem", "geriatrico", "skincare", "suplementos",
        "cafe", "bucal", "limpeza", "carnes", "alimentos", "higiene", "lactose", "gluten", "acucar"}
FONTES = {"Site", "App", "Encarte", "Clube", "Instagram", "WhatsApp", "Tiendeo"}

BUSCA = {"rodando": False, "etapa": None, "atual": 0, "total": 0, "erro": None, "avisos": [], "terminou_em": None}
_trava = threading.Lock()
# configuração: cada gravação aumenta "rev"; o diário guarda o que veio do HA para juntar com o painel
_cfg_trava = threading.Lock()
DIARIO = []
SYNC = {"ultima": None, "erro": None, "chegaram": 0, "enviados": 0}


class ErroBusca(Exception):
    pass


class ErroCota(ErroBusca):
    """A IA recusou por limite de uso (erro 429 / cota)."""
    def __init__(self, provedor=""):
        super().__init__(("A cota da IA acabou" + (f" ({provedor})" if provedor else "") +
                          ": ela recusou por excesso de pedidos (erro 429). No plano gratuito há limite por minuto e por dia. "
                          "Espere alguns minutos e tente de novo, ou ative o faturamento da chave (no Google, em aistudio.google.com)."))


def e_cota(txt):
    t = str(txt or "").lower()
    return "429" in t or "quota" in t or "resource_exhausted" in t or "rate limit" in t


class ErroFormato(ErroBusca):
    """A IA respondeu texto em vez do JSON pedido; guarda um trecho para mostrar e registrar."""
    def __init__(self, trecho=""):
        self.trecho = " ".join(str(trecho or "").split())[:220]
        if "{" in self.trecho:
            msg = "A IA mandou a resposta num formato que o EconomIA não conseguiu ler. Toque em Buscar de novo; se repetir, veja o Registro do app."
        else:
            msg = "A IA respondeu fora do formato esperado." + (f" Ela disse: \"{self.trecho}\"" if self.trecho else "")
        super().__init__(msg)


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


def agora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hoje_br():
    return (datetime.now(timezone.utc) - timedelta(hours=3)).date().isoformat()


# ---------- utilidades de limpeza ----------
def slug(texto, limite=40):
    t = unicodedata.normalize("NFD", str(texto)).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:limite] or "item"


def numero(v):
    if isinstance(v, str):  # "R$ 12,90", "1.299,90"
        v = re.sub(r"[^\d,.]", "", v)
        if "," in v:
            v = v.replace(".", "").replace(",", ".")
    try:
        n = round(float(v), 2)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def frete_ok(v):
    try:
        n = round(float(v), 2)
    except (TypeError, ValueError):
        return None
    return n if n >= 0 else None


def inteiro(v):
    try:
        n = int(round(float(v)))
    except (TypeError, ValueError):
        return None
    return n if n >= 0 else None


def valor_total(v, socio=False):
    """Preço de um item da lista: número (loja), {preco, clube} (loja com clube) ou {preco, frete} (online)."""
    if isinstance(v, dict):
        preco = numero(v.get("preco"))
        clube = numero(v.get("clube"))
        if socio and clube and (not preco or clube < preco):
            preco = clube
        return round(preco + (frete_ok(v.get("frete")) or 0), 2) if preco else None
    return numero(v)


UNIDADES = {"l": ("L", 1), "lt": ("L", 1), "litro": ("L", 1), "litros": ("L", 1), "ml": ("L", 0.001),
            "kg": ("kg", 1), "g": ("kg", 0.001), "gr": ("kg", 0.001),
            "un": ("un", 1), "und": ("un", 1), "unid": ("un", 1), "unidade": ("un", 1), "unidades": ("un", 1),
            "m": ("m", 1), "metro": ("m", 1), "metros": ("m", 1)}


def medida(q, u):
    """Quantidade numa unidade comum: litro, quilo, unidade ou metro."""
    try:
        q = float(q)
    except (TypeError, ValueError):
        return None
    f = UNIDADES.get(str(u or "").strip().lower().rstrip("."))
    if not f or not (0 < q < 100000):
        return None
    return round(q * f[1], 4), f[0]


def mesmo_tamanho(qa, qb):
    return abs(qa - qb) <= qb * 0.01


def url_ok(u):
    return isinstance(u, str) and u.startswith(("https://", "http://")) and len(u) < 600


def fonte_ok(u):
    """Link da fonte; aceita "loja.com.br/x" sem https. Sem link válido, None."""
    if url_ok(u):
        return u
    u = str(u or "").strip()
    if u and " " not in u and re.match(r"^[\w-]+(\.[\w-]+)+(/.*)?$", u) and len(u) < 600:
        return "https://" + u
    return None


def casar_item(it, nomes):
    """Qual item da lista é este: pelo número, pelo nome exato ou por nome parecido."""
    try:
        k = int(it.get("item"))
        if 1 <= k <= len(nomes):
            return nomes[k - 1]
    except (TypeError, ValueError):
        pass
    alvo = norm(re.sub(r"\s*\(base:[^)]*\)\s*$", "", str(it.get("produto") or "")))
    exatos = {norm(n): n for n in nomes}
    if alvo in exatos:
        return exatos[alvo]
    raiz = lambda w: w[:-1] if len(w) > 3 and w.endswith("s") else w  # noqa: E731
    vazias = {"de", "da", "do", "das", "dos", "para", "com", "em", "e", "a", "o"}
    pa = {raiz(w) for w in alvo.split()} - vazias
    melhor, nota = None, 0.0
    for n in nomes:
        pn = {raiz(w) for w in norm(n).split()} - vazias
        if pn:
            comum = len(pn & pa) / len(pn)
            if comum > nota:
                melhor, nota = n, comum
    return melhor if nota >= 0.75 else None


def texto(v, limite=120):
    return str(v).strip()[:limite] if v not in (None, "") else None


def data_ok(v):
    return v if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) else None


def norm(s):
    t = unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


# ---------- configuração com revisão ----------
def ler_config():
    return ler_json(CONFIG, {}) or {}


def gravar_config(cfg):
    cfg["rev"] = int(cfg.get("rev") or 0) + 1
    cfg["atualizado_em"] = agora()
    gravar_json(CONFIG, cfg)
    return cfg


def nome_item(i):
    return (i.get("produto") if isinstance(i, dict) else str(i or "")).strip()


IA_DESLIGADA = "A IA está desligada. Para usar, ligue em Mais › Integrações › Usar IA."
OPCOES_PADRAO = {"itens_sem_preco": True, "encartes_auto": True, "lojas_diretas": True}


def ia_ligada(cfg=None):
    return (cfg if cfg is not None else ler_config()).get("usar_ia") is not False


def opcao(nome, cfg=None):
    v = ((cfg if cfg is not None else ler_config()).get("opcoes") or {}).get(nome)
    return OPCOES_PADRAO.get(nome, True) if v is None else v is True


def sensores_ligados(cfg=None):
    return (cfg if cfg is not None else ler_config()).get("sensores") is True


# ---------- versões anteriores do config.json ----------
_versao = {"ultima": 0.0}
MOTIVOS_VERSAO = {"auto": "automática", "importar": "antes de importar", "restaurar": "antes de restaurar", "limpar": "antes de limpar a lista"}


def guardar_versao(motivo="auto", forcar=False):
    if not os.path.exists(CONFIG) or (not forcar and time.time() - _versao["ultima"] < INTERVALO_VERSAO):
        return None
    motivo = motivo if motivo in MOTIVOS_VERSAO else "auto"
    os.makedirs(VERSOES, exist_ok=True)
    nome = f"config-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{motivo}.json"
    shutil.copy2(CONFIG, os.path.join(VERSOES, nome))
    _versao["ultima"] = time.time()
    for velho in sorted(f for f in os.listdir(VERSOES) if f.endswith(".json"))[:-MAX_VERSOES]:
        try:
            os.remove(os.path.join(VERSOES, velho))
        except OSError:
            pass
    return nome


def listar_versoes():
    if not os.path.isdir(VERSOES):
        return []
    out = []
    for nome in sorted((f for f in os.listdir(VERSOES) if re.match(r"^config-\d{8}-\d{6}-[a-z]+\.json$", f)), reverse=True):
        d = ler_json(os.path.join(VERSOES, nome), {}) or {}
        m = re.match(r"^config-(\d{8})-(\d{6})-([a-z]+)\.json$", nome)
        quando = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").isoformat()
        out.append({"nome": nome, "quando": quando, "motivo": MOTIVOS_VERSAO.get(m.group(3), m.group(3)),
                    "itens": len([i for i in (d.get("lista") or []) if nome_item(i)]), "cep": d.get("cep")})
    return out


def restaurar_versao(nome):
    if not re.match(r"^config-\d{8}-\d{6}-[a-z]+\.json$", str(nome or "")):
        raise ErroBusca("Versão não encontrada.")
    d = ler_json(os.path.join(VERSOES, nome))
    if not isinstance(d, dict):
        raise ErroBusca("Versão não encontrada.")
    with _cfg_trava:
        guardar_versao("restaurar", forcar=True)
        d["rev"] = int(ler_config().get("rev") or 0)
        novo = gravar_config(d)
    log(f"versão restaurada: {nome}")
    return novo


def aplicar_diario(cfg, d):
    lista = cfg.setdefault("lista", [])
    idx = {norm(nome_item(i)): i for i in lista if isinstance(i, dict)}
    item = idx.get(norm(d["produto"]))
    if not item:
        item = {"produto": d["produto"], "compras": [], "origem": "ha"}
        lista.append(item)
    if d["tipo"] == "compra" and d.get("data") and d["data"] not in item.setdefault("compras", []):
        item["compras"].append(d["data"])


def ritmo_info(item):
    compras = sorted(c for c in (item.get("compras") or []) if data_ok(c))
    if len(compras) < 2:
        return None, None
    ds = [datetime.strptime(c, "%Y-%m-%d") for c in compras]
    media = max(1, round(sum((ds[k] - ds[k - 1]).days for k in range(1, len(ds))) / (len(ds) - 1)))
    prevista = ds[-1] + timedelta(days=media)
    hoje = datetime.strptime(hoje_br(), "%Y-%m-%d")
    return (prevista - hoje).days, prevista.strftime("%Y-%m-%d")


# ---------- API do Home Assistant ----------
def token_ha():
    """Chave do Supervisor. O s6-overlay da imagem base limpa o ambiente, então também lê o arquivo dele."""
    for k in ("SUPERVISOR_TOKEN", "HASSIO_TOKEN"):
        if os.environ.get(k):
            return os.environ[k]
    for pasta in ("/run/s6/container_environment", "/var/run/s6/container_environment"):
        for k in ("SUPERVISOR_TOKEN", "HASSIO_TOKEN"):
            try:
                with open(os.path.join(pasta, k), encoding="utf-8") as f:
                    t = f.read().strip()
            except OSError:
                continue
            if t:
                return t
    return None


def ha_api(metodo, caminho, corpo=None, timeout=30):
    token = token_ha()
    if not token:
        raise ErroBusca("O add-on não tem acesso ao Home Assistant. Reinstale a versão mais nova do add-on.")
    req = urllib.request.Request(HA_API + caminho, method=metodo,
                                 data=json.dumps(corpo).encode("utf-8") if corpo is not None else None,
                                 headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            texto = r.read().decode("utf-8")
            return json.loads(texto) if texto else None
    except urllib.error.HTTPError as e:
        raise ErroBusca(f"O Home Assistant recusou o pedido ({e.code}).") from e
    except urllib.error.URLError as e:
        raise ErroBusca("Não consegui falar com o Home Assistant.") from e


def listas_ha():
    estados = ha_api("GET", "/states") or []
    return sorted(({"id": e["entity_id"], "nome": (e.get("attributes") or {}).get("friendly_name") or e["entity_id"]}
                   for e in estados if isinstance(e, dict) and str(e.get("entity_id", "")).startswith("todo.")),
                  key=lambda x: x["nome"].lower())


def itens_ha(entidade):
    r = ha_api("POST", "/services/todo/get_items?return_response=true",
               {"entity_id": entidade, "status": ["needs_action", "completed"]}) or {}
    return ((r.get("service_response") or {}).get(entidade) or {}).get("items") or []


def sincronizar_lista():
    cfg = ler_config()
    conf = cfg.get("sync") or {}
    ent = str(conf.get("entidade") or "").strip()
    if not conf.get("ativo") or not ent.startswith("todo."):
        return
    estado = ler_json(SYNC_FILE, {}) or {}
    primeira = estado.get("entidade") != ent
    if primeira:
        estado = {"entidade": ent, "status": {}, "enviados": [norm(nome_item(i)) for i in cfg.get("lista") or []], "acabando": {}}
    itens = itens_ha(ent)
    hoje = hoje_br()
    mudancas = []
    enviados = set(estado.get("enviados") or [])
    with _cfg_trava:
        cfg = ler_config()
        lista = cfg.setdefault("lista", [])
        idx = {norm(nome_item(i)): i for i in lista if isinstance(i, dict)}
        for it in itens:
            nome = str(it.get("summary") or "").strip()[:120]
            if len(nome) < 2:
                continue
            uid, situacao, k = str(it.get("uid") or nome), it.get("status"), norm(nome)
            antes = estado["status"].get(uid)
            if situacao == "needs_action" and antes is None and k not in idx:
                idx[k] = {"produto": nome, "compras": [], "origem": "ha"}
                lista.append(idx[k])
                enviados.add(k)
                mudancas.append({"tipo": "novo", "produto": nome})
            if situacao == "completed" and antes is not None and antes != "completed":
                if k not in idx:
                    idx[k] = {"produto": nome, "compras": [], "origem": "ha"}
                    lista.append(idx[k])
                    enviados.add(k)
                if hoje not in idx[k].setdefault("compras", []):
                    idx[k]["compras"].append(hoje)
                    mudancas.append({"tipo": "compra", "produto": idx[k]["produto"], "data": hoje})
            estado["status"][uid] = situacao
        if mudancas:
            rev = gravar_config(cfg)["rev"]
            DIARIO.extend(dict(m, rev=rev) for m in mudancas)
            del DIARIO[:-300]
            log(f"lista do HA: {len(mudancas)} mudança(s)")
    # do EconomIA para a lista do HA
    pendentes = {norm(i.get("summary") or "") for i in itens if i.get("status") == "needs_action"}
    mandou = 0
    for item in cfg.get("lista") or []:
        if not isinstance(item, dict):
            continue
        nome, k = nome_item(item), norm(nome_item(item))
        if not nome or k in pendentes:
            continue
        if conf.get("enviar_novos", True) and k not in enviados:
            ha_api("POST", "/services/todo/add_item", {"entity_id": ent, "item": nome})
            pendentes.add(k)
            mandou += 1
        elif conf.get("enviar_acabando", True):
            dias, prevista = ritmo_info(item)
            if dias is not None and dias <= 1 and estado["acabando"].get(k) != prevista:
                ha_api("POST", "/services/todo/add_item", {"entity_id": ent, "item": nome})
                estado["acabando"][k] = prevista
                pendentes.add(k)
                mandou += 1
        enviados.add(k)
    atuais = {norm(nome_item(i)) for i in cfg.get("lista") or [] if isinstance(i, dict)}
    estado["enviados"] = sorted(k for k in enviados if k in atuais)
    gravar_json(SYNC_FILE, estado)
    SYNC.update({"ultima": agora(), "erro": None, "chegaram": SYNC["chegaram"] + len(mudancas), "enviados": SYNC["enviados"] + mandou})


def laco_sincronizacao():
    while True:
        if _sensor_dia["dia"] != hoje_br() and token_ha():
            publica_sensor_uso()
        try:
            sincronizar_lista()
        except ErroBusca as e:
            SYNC["erro"] = str(e)
        except Exception as e:  # noqa: BLE001
            SYNC["erro"] = f"Erro na sincronização: {e}"
            log(SYNC["erro"])
        time.sleep(SYNC_INTERVALO)


# ---------- IA do Home Assistant ----------
def opcoes():
    return ler_json(OPTIONS, {}) or {}


COMO_BUSCA = ("Na Anthropic, ligue a busca na web nas opções da tarefa de IA. "
              "No Google Gemini, a Pesquisa Google só funciona num assistente de conversa: ligue \"Enable Google Search tool\" "
              "nele e escolha esse assistente em Mais → IA do Home Assistant → Para buscar ofertas.")
SEM_BUSCA = "A IA escolhida não usou a busca na web. " + COMO_BUSCA


def ia_escolhida(uso):
    """Entidade escolhida em Mais (busca ou fotos); em branco, a opção antiga do add-on ou a preferida do HA."""
    ent = str(((ler_config().get("ia") or {}).get(uso)) or "").strip()
    return ent or str(opcoes().get("ai_task_entity") or "").strip()


def _json_ou_none(t):
    try:
        return json.loads(t)
    except ValueError:
        return None


def extrai_json(dado, nivel=0):
    """Acha o objeto JSON na resposta da IA: puro, em bloco de código, dentro de uma string ou com aspas escapadas."""
    if isinstance(dado, dict):
        return dado
    if not isinstance(dado, str):
        raise ErroBusca("A IA não devolveu resposta.")
    t = dado.strip()
    blocos = re.findall(r"```(?:json)?\s*(.*?)```", t, re.S)
    for c in blocos + [t]:
        c = c.strip()
        v = _json_ou_none(c)
        if isinstance(v, dict):
            return v
        if isinstance(v, str) and nivel < 2:  # JSON entregue como texto entre aspas
            try:
                return extrai_json(v, nivel + 1)
            except ErroBusca:
                pass
        ini, fim = c.find("{"), c.rfind("}")
        if ini < 0 or fim <= ini:
            continue
        trecho = c[ini:fim + 1]
        for tentativa in (trecho, re.sub(r",\s*([}\]])", r"\1", trecho)):
            v = _json_ou_none(tentativa)
            if isinstance(v, dict):
                return v
        if '\\"' in trecho:  # aspas e quebras de linha escapadas: \" e \n
            v = _json_ou_none('"' + trecho.replace("\n", "\\n") + '"')
            if isinstance(v, str):
                v = _json_ou_none(v)
                if isinstance(v, dict):
                    return v
    log("resposta da IA fora do formato: " + " ".join(dado.split())[:600])
    raise ErroFormato(dado)


def chamar_conversa(agente, instrucoes):
    r = ha_api("POST", "/services/conversation/process?return_response=true",
               {"text": instrucoes, "agent_id": agente}, timeout=900) or {}
    resp = ((r.get("service_response") or {}).get("response")) or {}
    fala = ((resp.get("speech") or {}).get("plain") or {}).get("speech") or ""
    if resp.get("response_type") == "error" or (e_cota(fala) and "{" not in fala[:1]):
        if e_cota(fala):
            raise ErroCota("Google Gemini" if "google" in fala.lower() else "")
        raise ErroBusca("O assistente de conversa respondeu com erro: " + " ".join(fala.split())[:160])
    return extrai_json(fala)


# ---------- uso da IA: o HA não devolve tokens nem custo, então o add-on conta as chamadas ----------
_uso_trava = threading.Lock()
_uso_local = threading.local()  # quantas chamadas a busca desta thread fez
SENSOR_USO = "sensor.economia_ia_hoje"
DIAS_USO = 120


def tipo_uso(nome):
    n = str(nome or "").replace("EconomIA: ", "")
    if n == "teste":
        return "teste"
    if n.startswith("encarte"):
        return "encarte"
    if n == "itens sem preço":
        return "itens"
    if n == "ler cupons":
        return "cupons"
    if n == "ler lista":
        return "fotos"
    if n == "falar":
        return "fala"
    return "busca"


def registra_uso(nome, entidade, entrada, saida, imagens, segundos, resultado):
    dia, tipo = hoje_br(), tipo_uso(nome)
    tokens = round((entrada + saida) / 4)  # estimativa: uns 4 caracteres por token
    with _uso_trava:
        u = ler_json(USO_FILE, {}) or {}
        dias = u.setdefault("dias", {})
        d = dias.setdefault(dia, {})
        for k, v in (("chamadas", 1), ("tokens", tokens), ("imagens", imagens), ("segundos", round(segundos, 1)),
                     ("erros", 1 if resultado not in ("ok", "cota") else 0), ("cota", 1 if resultado == "cota" else 0)):
            d[k] = round(d.get(k, 0) + v, 1)
        tipos, ia = d.setdefault("tipos", {}), entidade or "padrão do Home Assistant"
        tipos[tipo] = tipos.get(tipo, 0) + 1
        ias = d.setdefault("ias", {})
        ias[ia] = ias.get(ia, 0) + 1
        for k in sorted(dias)[:-DIAS_USO]:
            del dias[k]
        ultimas = u.setdefault("ultimas", [])
        ultimas.insert(0, {"quando": agora(), "tipo": tipo, "ia": ia, "resultado": resultado,
                           "segundos": round(segundos, 1), "tokens": tokens, "imagens": imagens})
        del ultimas[40:]
        gravar_json(USO_FILE, u)
    if hasattr(_uso_local, "chamadas"):
        _uso_local.chamadas += 1
    threading.Thread(target=publica_sensor_uso, daemon=True).start()


def uso_resumo():
    u = ler_json(USO_FILE, {}) or {}
    dias = u.get("dias") or {}
    hoje = hoje_br()
    d0 = datetime.strptime(hoje, "%Y-%m-%d")
    semana = [(d0 - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

    def soma(chaves):
        t = {"chamadas": 0, "erros": 0, "cota": 0, "tokens": 0, "imagens": 0, "segundos": 0, "tipos": {}, "ias": {}}
        for k in chaves:
            d = dias.get(k) or {}
            for c in ("chamadas", "erros", "cota", "tokens", "imagens", "segundos"):
                t[c] = round(t[c] + (d.get(c) or 0), 1)
            for grupo in ("tipos", "ias"):
                for nome, n in (d.get(grupo) or {}).items():
                    t[grupo][nome] = t[grupo].get(nome, 0) + n
        return t

    return {"hoje": soma([hoje]), "semana": soma(semana), "mes": soma([k for k in dias if k[:7] == hoje[:7]]),
            "dias": [dict(dia=k, **{c: (dias.get(k) or {}).get(c, 0) for c in ("chamadas", "erros", "cota")}) for k in semana],
            "ultimas": (u.get("ultimas") or [])[:12], "desde": min(dias) if dias else None, "sensor": SENSOR_USO}


_sensor_dia = {"dia": None, "ligado": None}


def remove_sensor_uso():
    """Sensores no Home Assistant desligado: o sensor que o app criou some do Home Assistant."""
    try:
        ha_api("DELETE", "/states/" + SENSOR_USO)
    except Exception:  # noqa: BLE001  (já não existia, ou o HA está fora: some no próximo reinício)
        pass


def publica_sensor_uso():
    """Sensor no HA com as chamadas de hoje, para gráfico e automação (só com a opção ligada)."""
    ligado, antes = sensores_ligados(), _sensor_dia["ligado"]
    _sensor_dia["ligado"] = ligado
    if not ligado:
        if antes is not False:
            remove_sensor_uso()
        _sensor_dia["dia"] = hoje_br()
        return
    try:
        r = uso_resumo()
        h = r["hoje"]
        ha_api("POST", "/states/" + SENSOR_USO, {"state": int(h["chamadas"]), "attributes": {
            "friendly_name": "EconomIA: chamadas de IA hoje", "icon": "mdi:robot-outline",
            "unit_of_measurement": "chamadas", "state_class": "total_increasing",
            "erros": int(h["erros"]), "cota_excedida": int(h["cota"]), "tokens_texto_estimados": int(h["tokens"]),
            "imagens": int(h["imagens"]), "por_tipo": h["tipos"], "ultimos_7_dias": int(r["semana"]["chamadas"]),
            "este_mes": int(r["mes"]["chamadas"]), "ultima_chamada": (r["ultimas"][0]["quando"] if r["ultimas"] else None)}})
        _sensor_dia["dia"] = hoje_br()
    except Exception as e:  # noqa: BLE001
        if _sensor_dia["dia"] != hoje_br():
            log(f"sensor de uso da IA: {e}")
        _sensor_dia["dia"] = hoje_br()


def chamar_ai_task(nome, instrucoes, anexos=None, uso="busca"):
    if not ia_ligada():
        raise ErroBusca(IA_DESLIGADA)
    inicio, resultado, saida = time.time(), "erro", 0
    try:
        r = _chamar_ai_task(nome, instrucoes, anexos, uso)
        resultado = "ok"
        try:
            saida = len(json.dumps(r, ensure_ascii=False))
        except (TypeError, ValueError):
            pass
        return r
    except ErroCota:
        resultado = "cota"
        raise
    except ErroFormato:
        resultado = "formato"
        raise
    finally:
        try:
            registra_uso(nome, ia_escolhida(uso), len(instrucoes or ""), saida, len(anexos or []), time.time() - inicio, resultado)
        except Exception as e:  # noqa: BLE001
            log(f"uso da IA: {e}")


def _chamar_ai_task(nome, instrucoes, anexos=None, uso="busca"):
    token = token_ha()
    if not token:
        raise ErroBusca("O add-on não tem acesso ao Home Assistant. Reinstale a versão mais nova do add-on.")
    entidade = ia_escolhida(uso)
    if entidade.startswith("conversation."):
        if anexos:
            raise ErroBusca("Um assistente de conversa não lê imagens. Em Mais → IA do Home Assistant, escolha uma tarefa de IA para ler fotos.")
        return chamar_conversa(entidade, instrucoes)
    corpo = {"task_name": nome, "instructions": instrucoes}
    if anexos:
        corpo["attachments"] = anexos
    if entidade:
        corpo["entity_id"] = entidade
    req = urllib.request.Request(
        HA_API + "/services/ai_task/generate_data?return_response=true",
        data=json.dumps(corpo).encode("utf-8"),
        method="POST",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            resp = json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        corpo_erro = e.read().decode("utf-8", "ignore")[:300]
        if e.code in (400, 404) and ("not found" in corpo_erro.lower() or "ai_task" in corpo_erro.lower()):
            raise ErroBusca("Falta uma IA no Home Assistant. Configure uma integração de IA (Anthropic, OpenAI, Google Gemini...) "
                            "em Configurações → Dispositivos e serviços e escolha-a em Mais → IA do Home Assistant.") from e
        if e.code == 401:
            raise ErroBusca("O add-on não tem permissão para usar o Home Assistant. Reinstale a versão mais nova.") from e
        if e.code == 429 or e_cota(corpo_erro):
            raise ErroCota() from e
        if anexos and "attachment" in corpo_erro.lower():
            raise ErroBusca("A IA escolhida no Home Assistant não lê imagens. Use uma que leia, como a Anthropic, "
                            "ou cole o texto da mensagem.") from e
        raise ErroBusca(f"A IA do Home Assistant recusou o pedido ({e.code}): {corpo_erro}") from e
    except urllib.error.URLError as e:
        raise ErroBusca("Não consegui falar com o Home Assistant. Tente de novo em instantes.") from e
    dado = (resp.get("service_response") or {}).get("data") if isinstance(resp, dict) else None
    return extrai_json(dado)


def ias_disponiveis():
    estados = ha_api("GET", "/states") or []
    tarefas, agentes = [], []
    for e in estados:
        if not isinstance(e, dict):
            continue
        ent, at = str(e.get("entity_id") or ""), e.get("attributes") or {}
        nome = at.get("friendly_name") or ent
        if ent.startswith("ai_task."):
            tarefas.append({"id": ent, "nome": nome, "anexos": bool(int(at.get("supported_features") or 0) & 2)})
        elif ent.startswith("conversation.") and ent != "conversation.home_assistant":
            agentes.append({"id": ent, "nome": nome})
    ordem = lambda x: x["nome"].lower()  # noqa: E731
    return {"tarefas": sorted(tarefas, key=ordem), "agentes": sorted(agentes, key=ordem)}


def testar_ia(uso):
    ent = ia_escolhida(uso)
    if uso == "fotos":
        if ent.startswith("conversation."):
            return {"ok": False, "msg": "Assistente de conversa não lê imagens. Escolha uma tarefa de IA."}
        tarefas = ias_disponiveis()["tarefas"]
        if not tarefas:
            return {"ok": False, "msg": "Nenhuma tarefa de IA no Home Assistant."}
        if not ent:
            return {"ok": True, "msg": "Usando a IA preferida do Home Assistant."}
        t = next((t for t in tarefas if t["id"] == ent), None)
        if not t:
            return {"ok": False, "msg": "Essa IA não existe mais no Home Assistant."}
        return {"ok": True, "msg": "Pronta para ler fotos."} if t["anexos"] else {"ok": False, "msg": "Essa IA não lê imagens."}
    try:
        r = chamar_ai_task("EconomIA: teste", f"""Teste rápido do EconomIA ({hoje_br()}). Use a busca na web agora para achar o preço atual de café torrado e moído 500 g em algum supermercado do Brasil.
Responda somente com um objeto JSON, sem texto antes ou depois: {{"busca": true, "exemplo": "loja e preço que você achou", "fonte": "URL"}}
Se não conseguir usar a busca na web, responda apenas {{"erro": "sem_busca"}}.""")
    except ErroFormato as e:
        if "{" in e.trecho:
            return {"ok": False, "msg": str(e)}
        return {"ok": False, "msg": "A IA respondeu sem usar a busca na web" + (f" (\"{e.trecho[:140]}\")" if e.trecho else "") + ". " + COMO_BUSCA}
    except ErroBusca as e:
        return {"ok": False, "msg": str(e)}
    if r.get("erro") == "sem_busca" or not url_ok(r.get("fonte")):
        return {"ok": False, "msg": SEM_BUSCA}
    return {"ok": True, "msg": "Pronta para buscar ofertas." + (" Exemplo: " + texto(r.get("exemplo"), 80) if texto(r.get("exemplo"), 80) else "")}


def descreve_casa(cfg):
    p = cfg.get("perfil") or {}
    pets = p.get("pets") or {}
    if isinstance(pets, list):
        pets = {k: 1 for k in pets}
    partes = [f"{int(p.get('adultos') or 1)} adulto(s)"]
    kids = int(p.get("criancas") or 0) + int(p.get("bebes") or 0)
    partes.append(f"{int(p.get('criancas') or 0)} criança(s) e {int(p.get('bebes') or 0)} bebê(s)" if kids else "sem crianças")
    bichos = [f"{int(n)} {k}" for k, n in pets.items() if int(n or 0) > 0]
    partes.append("pets: " + ", ".join(bichos) if bichos else "sem pets")
    excluir = []
    if not kids:
        excluir.append("produtos de bebê e infantis")
    if not bichos:
        excluir.append("produtos para animais")
    excluir += [f"etiqueta {t}" for t in (p.get("nunca") or [])]
    restr = p.get("restricoes") or []
    return "; ".join(partes), excluir, restr, p.get("interesses") or []


TAMANHOS_TXT = ("Para cada item da lista: \"base\" é o tamanho do item (se a lista indicar \"base\", use essa; se o item não diz "
                "o tamanho, use o mais vendido, por exemplo 1 L) e \"precos\" traz só embalagens desse tamanho. Em \"tamanhos\", traga as outras embalagens "
                "do mesmo produto que achar (maiores, menores, kits, fardos e leve X pague Y), cada uma com a quantidade total "
                "e o preço total do pacote, sem dividir. Unidades: L, ml, kg, g, un ou m; com \"un\", diga em \"rotulo\" o que "
                "é contado, no singular (rolo, cápsula, fralda). Em \"lista\", \"item\" é o número do item na lista de compras. "
                "Se o item for genérico (por exemplo \"pó lava louça\"), use o produto mais vendido desse tipo e diga qual em \"obs\". "
                "Em \"ofertas\", informe \"tamanho\" quando souber.")


def fmt_base(b):
    q, u = float(b.get("quantidade") or 0), b.get("unidade")
    if u == "L" and q < 1:
        return f"{q * 1000:g} ml"
    if u == "kg" and q < 1:
        return f"{q * 1000:g} g"
    if u == "un":
        return f"{q:g} {b.get('rotulo') or 'un'}"
    return f"{q:g} {u}"


def itens_prompt(cfg):
    of = ler_json(OFERTAS, {}) or {}
    bases = {norm(i.get("produto") or ""): i["base"] for i in of.get("lista") or []
             if isinstance(i, dict) and isinstance(i.get("base"), dict) and i["base"].get("quantidade")}
    out = []
    for i in cfg.get("lista") or []:
        n = nome_item(i)
        if n:
            b = bases.get(norm(n))
            out.append(f"{len(out) + 1}) " + (f"{n} (base: {fmt_base(b)})" if b else n))
    return out


APPS_TXT = ("No iFood e no Rappi, procure mercados, farmácias e pet shops que entregam neste CEP, inclusive lojas do bairro, "
            "e use \"rede\": \"iFood · nome da loja\" (ou \"Rappi · nome da loja\"). Nesses apps, \"frete\" é a taxa de entrega "
            "e \"prazo_dias\" é 0 para entrega no mesmo dia. Com Clube iFood, use frete 0 nas lojas participantes do Clube e diga "
            "o pedido mínimo do benefício em \"obs\". O preço no app pode ser diferente do preço no balcão: use o do app.")


def instrucoes_online(cfg):
    casa, excluir, restr, interesses = descreve_casa(cfg)
    on = cfg.get("online") or {}
    mkts = [MARKETPLACES.get(m, m) for m in (on.get("marketplaces") or ["mercadolivre", "amazon"])]
    assin = [ASSINATURAS.get(a, a) for a in (on.get("assinaturas") or [])]
    lista = itens_prompt(cfg)
    return f"""Encontre preços válidos hoje ({hoje_br()}) em {', '.join(mkts)} para entrega no CEP {cfg.get('cep')}, no Brasil.

Use a busca na web agora. Use só o que encontrar nas páginas: não invente produtos, preços, fretes nem prazos. Se não conseguir usar a busca na web, responda apenas {{"erro": "sem_busca"}}.

Assinaturas do morador: {', '.join(assin) or 'nenhuma'}. Quando a assinatura der frete grátis no item, use frete 0.
{APPS_TXT if any(m in (on.get("marketplaces") or []) for m in ("ifood", "rappi")) else ""}
Casa: {casa}.
Não traga: {', '.join(excluir) or 'nada a excluir'}.
Restrições: {', '.join(restr) or 'nenhuma'}. Interesses, que devem vir primeiro: {', '.join(interesses) or 'nenhum'}.
Lista de compras: {'; '.join(lista) or 'vazia'}.
{TAMANHOS_TXT} Em "tamanhos", informe também o frete e o prazo de cada opção.

Regras: em "fonte", use o link da página do produto. Só lojas oficiais ou vendedores bem avaliados. Marque "importado": true quando o envio for internacional. Não inclua remédios que exigem receita. Informe frete e prazo de entrega para este CEP. Em kits, informe "unidades". Até 15 ofertas, priorizando os itens da lista e os interesses.

Responda somente com um objeto JSON, sem texto antes ou depois, neste formato:
{{
  "cupons": [{{"rede": "Mercado Livre", "codigo": "CODIGO", "valor": 20, "beneficio": "R$ 20 de desconto", "condicao": "Acima de R$ 200", "valido_ate": "AAAA-MM-DD ou null", "oficial": true, "fonte": "URL"}}],
  "ofertas": [{{"rede": "Amazon", "produto": "Nome · tamanho", "preco_normal": 10.0, "preco_oferta": 8.0, "frete": 0, "prazo_dias": 2, "vendedor": "nome do vendedor", "oficial": true, "importado": false, "unidades": 1, "tamanho": {{"quantidade": 1, "unidade": "L"}}, "tipo": "promo", "tags": ["alimentos"], "fonte": "URL"}}],
  "lista": [{{"item": 1, "produto": "texto exato do item da lista", "base": {{"quantidade": 1, "unidade": "L", "rotulo": null}}, "precos": [{{"rede": "Amazon", "preco": 9.9, "frete": 0, "prazo_dias": 2, "fonte": "URL"}}], "tamanhos": [{{"rede": "Mercado Livre", "embalagem": "Kit 6 × 1 L", "quantidade": 6, "unidade": "L", "preco": 49.9, "frete": 0, "prazo_dias": 3, "fonte": "URL"}}]}}]
}}

Etiquetas permitidas em "tags": {', '.join(sorted(TAGS))}."""


def instrucoes_para(cat_id, cfg):
    if cat_id == "online":
        return instrucoes_online(cfg)
    cat = CATEGORIAS[cat_id]
    casa, excluir, restr, interesses = descreve_casa(cfg)
    lojas = cfg.get("lojas") or {}
    lista = itens_prompt(cfg)
    adicionadas = [a.get("nome") + (f" (site: {a['site']})" if url_ok(a.get("site")) else "")
                   for a in (lojas.get("adicionar") or []) if isinstance(a, dict) and a.get("categoria") == cat_id and a.get("nome")]
    extra = ""
    if cat_id == "farmacias":
        extra = ' Em remédios, inclua "receita": "tarja" (venda sob prescrição) ou "mip" (sem receita).'
    if cat_id == "petshops":
        extra = ' Em produtos para animais, use as etiquetas "pet" e "gato" ou "cachorro".'
    return f"""Encontre ofertas e cupons válidos hoje ({hoje_br()}) de {cat['o_que']} perto do CEP {cfg.get('cep')}, num raio de {cfg.get('raio_km') or 2} km, no Brasil.

Use a busca na web agora. Use só o que encontrar nas páginas: não invente lojas, preços nem cupons. Se não conseguir usar a busca na web, responda apenas {{"erro": "sem_busca"}}.

Casa: {casa}.
Não traga: {', '.join(excluir) or 'nada a excluir'}.
Restrições: {', '.join(restr) or 'nenhuma'}. Interesses, que devem vir primeiro: {', '.join(interesses) or 'nenhum'}.
Lista de compras (procure o preço atual de cada item nestas lojas): {'; '.join(lista) or 'vazia'}.
{TAMANHOS_TXT}
Lojas para ignorar: {', '.join(lojas.get('ignorar') or []) or 'nenhuma'}. Lojas para incluir mesmo mais longe: {', '.join(lojas.get('manter') or []) or 'nenhuma'}. Lojas indicadas pelo morador: {', '.join(adicionadas) or 'nenhuma'}.

Responda somente com um objeto JSON, sem texto antes ou depois, neste formato:
{{
  "lojas": [{{"rede": "nome da rede ou da loja", "endereco": "rua e número", "distancia_km": 1.2, "site": "URL da página de ofertas ou do site da loja, ou null", "horario": "Aberta até 22h", "fontes": ["Site", "App", "Encarte", "Clube", "Instagram", "WhatsApp", "Tiendeo"]}}],
  "cupons": [{{"rede": "...", "codigo": "CODIGO", "valor": 20, "beneficio": "R$ 20 de desconto", "condicao": "Pedidos acima de R$ 200", "valido_ate": "AAAA-MM-DD ou null", "oficial": true, "fonte": "URL"}}],
  "ofertas": [{{"rede": "...", "produto": "Nome · tamanho", "preco_normal": 10.0, "preco_oferta": 8.0, "tipo": "promo", "unidade": null, "tamanho": {{"quantidade": 500, "unidade": "g"}}, "condicao": null, "tags": ["alimentos"], "fonte": "URL"}}],
  "lista": [{{"item": 1, "produto": "texto exato do item da lista", "base": {{"quantidade": 1, "unidade": "L", "rotulo": null}}, "precos": [{{"rede": "...", "preco": 9.9, "preco_clube": 8.9, "fonte": "URL"}}], "tamanhos": [{{"rede": "...", "embalagem": "Galão 5 L", "quantidade": 5, "unidade": "L", "preco": 39.9, "fonte": "URL"}}]}}]
}}

Regras: em "lojas", inclua também mercadinhos e lojas independentes do raio, mesmo sem preços encontrados, com o site ou a página de ofertas quando houver. Até 15 ofertas, priorizando os interesses e os maiores descontos. Nos preços da lista, "preco" é o preço para todo mundo; se a loja tiver preço de clube (cadastro por CPF ou app), informe também "preco_clube", senão null. "tipo" é "promo", "clube" (preço para membros) ou "atacado" (preço por quantidade). "oficial" é true só se o cupom estiver no site ou app da própria loja. Etiquetas permitidas em "tags": {', '.join(sorted(TAGS))}.{extra}"""


def normalizar(cat_id, bruto, cfg):
    if not isinstance(bruto, dict):
        raise ErroBusca("A IA respondeu fora do formato esperado.")
    if bruto.get("erro") == "sem_busca":
        raise ErroBusca(SEM_BUSCA)
    pre = cat_id[:4] + "-"
    redes = {}

    def rede_id(nome):
        nome = texto(nome, 60)
        if not nome:
            return None
        nome = nome_direta(nome)
        rid = pre + slug(nome, 30)
        redes.setdefault(rid, nome)
        return rid

    lojas = {}
    for l in bruto.get("lojas") or []:
        if not isinstance(l, dict):
            continue
        rid = rede_id(l.get("rede"))
        if not rid:
            continue
        d = numero(l.get("distancia_km"))
        atual = lojas.get(rid)
        if atual and atual.get("distancia_km") is not None and (d is None or d >= atual["distancia_km"]):
            continue
        lojas[rid] = {"rede": rid, "distancia_km": d, "horario": texto(l.get("horario"), 60) or "",
                      "endereco": texto(l.get("endereco"), 90),
                      "fontes": [f for f in (l.get("fontes") or []) if f in FONTES][:5] or ["Site"]}
        if url_ok(l.get("site")):
            lojas[rid]["site"] = l["site"][:300]

    descartes = {}

    def descarta(motivo):
        descartes[motivo] = descartes.get(motivo, 0) + 1

    cupons = []
    for c in bruto.get("cupons") or []:
        if isinstance(c, dict):
            c = dict(c, fonte=fonte_ok(c.get("fonte")))
        if not isinstance(c, dict) or not c["fonte"] or not texto(c.get("codigo"), 40):
            descarta("cupom sem link ou sem código")
            continue
        rid = rede_id(c.get("rede"))
        if not rid:
            continue
        cupons.append({"rede": rid, "codigo": texto(c.get("codigo"), 40), "valor": numero(c.get("valor")),
                       "beneficio": texto(c.get("beneficio"), 60) or "Cupom de desconto",
                       "condicao": texto(c.get("condicao"), 120) or "", "valido_ate": data_ok(c.get("valido_ate")),
                       "status": "confirmado" if c.get("oficial") is True else "testar", "fonte": c["fonte"]})

    ofertas, ids = [], set()
    for o in bruto.get("ofertas") or []:
        if not isinstance(o, dict):
            continue
        rid, prod = rede_id(o.get("rede")), texto(o.get("produto"), 100)
        normal, oferta = numero(o.get("preco_normal")), numero(o.get("preco_oferta") or o.get("preco"))
        encarte = o.get("encarte") is True
        if not (rid and prod and oferta):
            descarta("oferta sem loja, produto ou preço")
            continue
        if not (normal and oferta < normal):
            normal = None  # encarte e site costumam mostrar só o preço da oferta
        oid = rid + "-" + slug(prod)
        if oid in ids:
            continue
        ids.add(oid)
        item = {"id": oid, "rede": rid, "produto": prod, "preco_normal": normal, "preco_oferta": oferta,
                "tipo": o.get("tipo") if o.get("tipo") in ("promo", "clube", "atacado") else "promo",
                "tags": [t for t in (o.get("tags") or []) if t in TAGS], "fonte": fonte_ok(o.get("fonte"))}
        if normal is None:
            item["tipo"] = "encarte" if encarte else "preco"
        if encarte:
            item["encarte"] = True
        if data_ok(o.get("valido_ate")):
            item["valido_ate"] = data_ok(o.get("valido_ate"))
        for campo, lim in (("unidade", 12), ("condicao", 80)):
            if texto(o.get(campo), lim):
                item[campo] = texto(o.get(campo), lim)
        if o.get("receita") in ("tarja", "mip"):
            item["receita"] = o["receita"]
        tam = o.get("tamanho") if isinstance(o.get("tamanho"), dict) else {}
        m = medida(tam.get("quantidade"), tam.get("unidade"))
        if m and not item.get("unidade"):
            item["tamanho"] = {"quantidade": m[0], "unidade": m[1]}
        if cat_id == "online":
            frete = frete_ok(o.get("frete"))
            if frete is None or item.get("receita") == "tarja":
                ids.discard(oid)
                continue
            item["frete"] = frete
            for campo in ("prazo_dias", "unidades"):
                n = inteiro(o.get(campo))
                if n is not None and (campo == "prazo_dias" or n > 1):
                    item[campo] = n
            if texto(o.get("vendedor"), 60):
                item["vendedor"] = texto(o.get("vendedor"), 60)
            item["oficial"] = o.get("oficial") is True
            if o.get("importado") is True:
                item["importado"] = True
        ofertas.append(item)

    def valor_lista(p):
        """(rede, valor) de um preço da lista; online precisa de frete."""
        if not isinstance(p, dict):
            return None, None
        rid, preco = rede_id(p.get("rede")), numero(p.get("preco"))
        if not (rid and preco):
            descarta("preço da lista sem loja ou valor")
            return None, None
        if cat_id != "online":
            clube, obs = numero(p.get("preco_clube")), texto(p.get("obs"), 60)
            if not (clube and clube < preco) and not obs:
                return rid, preco
            valor = {"preco": preco}
            if clube and clube < preco:
                valor["clube"] = clube
            if obs:
                valor["obs"] = obs
            return rid, valor
        frete = frete_ok(p.get("frete"))
        if frete is None:
            descarta("preço online sem frete")
            return None, None
        valor = {"preco": preco, "frete": frete}
        if inteiro(p.get("prazo_dias")) is not None:
            valor["prazo_dias"] = inteiro(p.get("prazo_dias"))
        if texto(p.get("obs"), 60):
            valor["obs"] = texto(p.get("obs"), 60)
        return rid, valor

    nomes = [nome_item(i) for i in (cfg.get("lista") or []) if nome_item(i)]
    lista = {}
    for it in bruto.get("lista") or []:
        if not isinstance(it, dict):
            continue
        original = casar_item(it, nomes)
        if not original:
            descarta("item que não está na lista")
            continue
        ent = lista.setdefault(original, {"precos": {}, "base": None, "tamanhos": [], "links": {}})
        for p in it.get("precos") or []:
            if isinstance(p, dict) and not p.get("rede") and it.get("rede"):
                p = dict(p, rede=it["rede"])
            rid, valor = valor_lista(p)
            if rid:
                ent["precos"][rid] = valor
                if fonte_ok(p.get("fonte")):
                    ent["links"][rid] = fonte_ok(p.get("fonte"))
        b = it.get("base") if isinstance(it.get("base"), dict) else {}
        base = medida(b.get("quantidade"), b.get("unidade"))
        if not base:
            continue
        if not ent["base"]:
            ent["base"] = {"quantidade": base[0], "unidade": base[1]}
            if base[1] == "un" and texto(b.get("rotulo"), 14):
                ent["base"]["rotulo"] = texto(b.get("rotulo"), 14).lower()
        bq, bu = ent["base"]["quantidade"], ent["base"]["unidade"]
        vistos = {(t["rede"], t["quantidade"]) for t in ent["tamanhos"]}
        for t in it.get("tamanhos") or []:
            if not isinstance(t, dict):
                continue
            m = medida(t.get("quantidade"), t.get("unidade") or bu)
            if not m or m[1] != bu:
                continue
            rid, valor = valor_lista(t)
            if not rid:
                continue
            if mesmo_tamanho(m[0], bq):  # é o tamanho da base: vale como preço da loja
                ent["precos"].setdefault(rid, valor)
                if fonte_ok(t.get("fonte")):
                    ent["links"].setdefault(rid, fonte_ok(t.get("fonte")))
                continue
            if (rid, m[0]) in vistos:
                continue
            vistos.add((rid, m[0]))
            tam = {"rede": rid, "quantidade": m[0]}
            if texto(t.get("embalagem"), 40):
                tam["embalagem"] = texto(t.get("embalagem"), 40)
            if isinstance(valor, dict):
                tam.update({k: valor[k] for k in ("preco", "frete", "prazo_dias") if k in valor})
            else:
                tam["preco"] = valor
            if fonte_ok(t.get("fonte")):
                tam["fonte"] = fonte_ok(t.get("fonte"))
            ent["tamanhos"].append(tam)
    lista = {k: v for k, v in lista.items() if v["precos"] or v["tamanhos"]}

    # só as redes que ficaram com loja, cupom, oferta ou preço; cada uma precisa de uma loja
    usadas = set(lojas) | {c["rede"] for c in cupons} | {o["rede"] for o in ofertas}
    usadas |= {r for v in lista.values() for r in list(v["precos"]) + [t["rede"] for t in v["tamanhos"]]}
    redes = {k: v for k, v in redes.items() if k in usadas}
    online = cat_id == "online"
    for rid in redes:
        lojas.setdefault(rid, {"rede": rid, "distancia_km": None, "horario": "Entrega no seu CEP" if online else "",
                               "endereco": None, "fontes": ["Site", "App"] if online else ["Site"]})

    n_precos = sum(len(v["precos"]) + len(v["tamanhos"]) for v in lista.values())
    log(f"{cat_id}: {len(lojas)} loja(s), {len(ofertas)} oferta(s), {len(cupons)} cupom(ns), {n_precos} preço(s) da lista"
        + (" | descartados: " + ", ".join(f"{n} {m}" for m, n in descartes.items()) if descartes else ""))
    cat = CATEGORIAS[cat_id]
    return {
        "id": cat_id, "nome": cat["nome"], "singular": cat["singular"],
        "redes": [{"id": rid, "nome": nome, "curto": nome[:16]} for rid, nome in redes.items()],
        "lojas": sorted(lojas.values(), key=lambda l: l["distancia_km"] if l["distancia_km"] is not None else 99),
        "cupons": cupons,
        "ofertas": ofertas,
        "contas": [{"rede": l["rede"], "libera": "Preços e cupons do clube da loja", "status": "pendente"}
                   for l in lojas.values() if "Clube" in l["fontes"]],
    }, lista


# ---------- encarte do site da loja ----------
URL_ATTR_RE = re.compile(r"""(?:src|data-src|data-original|href|content|srcset)\s*=\s*["']([^"']+)["']""", re.I)
RUIDO_IMG = ("logo", "icon", "favicon", "sprite", "avatar", "whatsapp", "facebook", "instagram", "pixel", "loading")
NAVEGADOR = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36"


def baixar(url, limite, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": NAVEGADOR, "Accept-Language": "pt-BR,pt;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        tipo = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        dado = r.read(limite + 1)
    if len(dado) > limite:
        raise ValueError("arquivo grande demais")
    return dado, tipo


def candidatos_encarte(pagina_html, base):
    """Imagens e PDFs da página, na ordem em que aparecem (Wix: pede uma versão de até 1600 px)."""
    vistos, out = set(), []
    for valor in URL_ATTR_RE.findall(pagina_html):
        for parte in valor.split(","):
            u = parte.strip().split(" ")[0].replace("&amp;", "&")
            if not u or u.startswith("data:"):
                continue
            u = urllib.parse.urljoin(base, u)
            low = u.lower()
            wix = re.match(r"(https?://static\.wixstatic\.com/media/[^/?#]+?\.(?:jpe?g|png|webp))", u, re.I)
            if wix:
                chave, u = wix.group(1).lower(), wix.group(1) + "/v1/fit/w_1600,h_3200,q_85/encarte.jpg"
            elif re.search(r"\.(jpe?g|png|webp|pdf)([?#].*)?$", low):
                chave = low.split("?")[0].split("#")[0]
            else:
                continue
            if chave in vistos or any(r in low.rsplit("/", 1)[-1] for r in RUIDO_IMG):
                continue
            vistos.add(chave)
            out.append(u)
    return out


def texto_da_pagina(pagina_html):
    t = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", pagina_html)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return " ".join(html_mod.unescape(t).split())[:5000]


def instrucoes_encarte(loja, texto_pag, n, cfg):
    aspas = chr(34) * 3
    fonte = f"{n} imagem(ns) ou PDF do encarte de ofertas" if n else "o texto da página de ofertas"
    return f"""Você recebe {fonte} do site da loja "{loja['nome']}" ({loja['site']}). Hoje é {hoje_br()}.
{('Texto da página: ' + aspas + texto_pag[:4000] + aspas) if texto_pag else ''}

Extraia as ofertas legíveis: "produto" com marca e tamanho (por exemplo "Café Pilão 500 g"), "preco" (o preço da oferta), "preco_normal" só se o encarte mostrar o preço "de", "unidade" ("kg" quando o preço for por quilo), "condicao" (por exemplo "leve 3 pague 2", "no cartão da loja", "clube"), "tipo" ("clube" quando for preço de clube, senão "promo") e "tamanho". Não invente nada que não esteja legível.
Lista de compras do morador: {'; '.join(itens_prompt(cfg)) or 'vazia'}. Para cada item da lista que aparecer no encarte, informe o preço em "lista".
{TAMANHOS_TXT}

Responda somente com um objeto JSON, sem texto antes ou depois:
{{"validade": "AAAA-MM-DD ou null", "ofertas": [{{"produto": "Café Pilão 500 g", "preco": 15.98, "preco_normal": null, "unidade": null, "condicao": null, "tipo": "promo", "tamanho": {{"quantidade": 500, "unidade": "g"}}, "tags": ["alimentos", "cafe"]}}], "lista": [{{"item": 1, "produto": "texto exato do item da lista", "base": {{"quantidade": 1, "unidade": "L", "rotulo": null}}, "precos": [{{"preco": 9.9}}], "tamanhos": []}}]}}
Etiquetas permitidas em "tags": {', '.join(sorted(TAGS))}. Até 40 ofertas, priorizando os itens da lista e os interesses."""


def ler_encarte(loja, cfg):
    """Abre o site de ofertas, baixa o encarte e pede para a IA de fotos ler. Devolve (categoria, lista)."""
    try:
        pagina, tipo = baixar(loja["site"], 3 * 1024 * 1024)
    except Exception as e:  # noqa: BLE001
        raise ErroBusca(f"não consegui abrir o site ({e})") from e
    dados, texto_pag = [], ""
    if tipo == "application/pdf" or pagina[:4] == b"%PDF":
        dados.append((pagina, "application/pdf"))
    elif tipo.startswith("image/"):
        dados.append((pagina, tipo))
    else:
        html_txt = pagina.decode("utf-8", "ignore")
        texto_pag = texto_da_pagina(html_txt)
        for u in candidatos_encarte(html_txt, loja["site"])[:16]:
            if len(dados) >= 6:
                break
            try:
                dado, t = baixar(u, 9 * 1024 * 1024 if u.lower().endswith(".pdf") else 4_500_000)
            except Exception:  # noqa: BLE001
                continue
            if t == "application/pdf" or dado[:4] == b"%PDF":
                if sum(1 for _, x in dados if x == "application/pdf") < 2:
                    dados.append((dado, "application/pdf"))
            elif t in ("image/jpeg", "image/png", "image/webp") and len(dado) >= 45_000:  # logos e ícones são pequenos
                dados.append((dado, t))
    if not dados and len(texto_pag) < 200:
        raise ErroBusca("não achei encarte nem ofertas no site")
    pasta = os.path.join(MEDIA, "economia")
    arquivos, anexos = [], []
    try:
        if dados:
            os.makedirs(pasta, exist_ok=True)
        marca = datetime.now().strftime("%H%M%S") + os.urandom(2).hex()
        for n, (dado, t) in enumerate(dados):
            ext = {"application/pdf": "pdf", "image/png": "png", "image/webp": "webp"}.get(t, "jpg")
            nome = f"encarte-{marca}-{n}.{ext}"
            with open(os.path.join(pasta, nome), "wb") as f:
                f.write(dado)
            arquivos.append(os.path.join(pasta, nome))
            anexos.append({"media_content_id": f"{MEDIA_URI}/economia/{nome}", "media_content_type": t})
        r = chamar_ai_task(f"EconomIA: encarte {loja['nome']}", instrucoes_encarte(loja, texto_pag, len(anexos), cfg), anexos or None, uso="fotos")
    finally:
        for a in arquivos:
            try:
                os.remove(a)
            except OSError:
                pass
    nome, url, val = loja["nome"], loja["site"], data_ok(r.get("validade"))
    marca_rede = lambda x: dict(x, rede=nome, fonte=url)  # noqa: E731
    bruto = {
        "lojas": [{"rede": nome, "endereco": None, "distancia_km": None, "fontes": ["Site", "Encarte"]}],
        "cupons": [],
        "ofertas": [dict(o, rede=nome, preco_oferta=o.get("preco"), fonte=url, encarte=True, valido_ate=val)
                    for o in r.get("ofertas") or [] if isinstance(o, dict)],
        "lista": [dict(it, precos=[marca_rede(x) for x in it.get("precos") or [] if isinstance(x, dict)],
                       tamanhos=[marca_rede(x) for x in it.get("tamanhos") or [] if isinstance(x, dict)])
                  for it in r.get("lista") or [] if isinstance(it, dict)],
    }
    log(f"encarte de {nome}: {len(dados)} arquivo(s), {len(bruto['ofertas'])} oferta(s)")
    return normalizar(loja["categoria"], bruto, cfg)


def juntar_categoria(dest, cat):
    """Junta o resultado de um encarte à categoria que veio da busca."""
    ids_redes = {r["id"] for r in dest.get("redes") or []}
    dest.setdefault("redes", []).extend(r for r in cat["redes"] if r["id"] not in ids_redes)
    lojas = {l["rede"]: l for l in dest.get("lojas") or []}
    for l in cat["lojas"]:
        if l["rede"] in lojas:
            lojas[l["rede"]]["fontes"] = sorted(set(lojas[l["rede"]].get("fontes") or []) | set(l["fontes"]))
        else:
            dest.setdefault("lojas", []).append(l)
    ids = {o["id"] for o in dest.get("ofertas") or []}
    dest.setdefault("ofertas", []).extend(o for o in cat["ofertas"] if o["id"] not in ids)


def juntar_item(dest, ent):
    """Junta o que uma categoria achou para um item da lista ao que as outras já acharam."""
    b, nb = dest.get("base"), ent.get("base")
    links, dlinks = ent.get("links") or {}, dest.setdefault("links", {})
    if not b and nb:
        dest["base"] = b = nb
    if not (b and nb) or (nb["unidade"] == b["unidade"] and mesmo_tamanho(nb["quantidade"], b["quantidade"])):
        dest["precos"].update(ent["precos"])
        dlinks.update(links)
        if b and nb:
            dest["tamanhos"] += ent["tamanhos"]
        return
    if nb["unidade"] != b["unidade"]:  # medidas diferentes não dá para comparar
        dest["precos"].update(ent["precos"])
        dlinks.update(links)
        return
    # esta categoria usou outro tamanho como base: os preços dela viram tamanhos
    for rid, v in ent["precos"].items():
        t = {"rede": rid, "quantidade": nb["quantidade"]}
        if isinstance(v, dict):
            t.update({k: v[k] for k in ("preco", "frete", "prazo_dias") if k in v})
        else:
            t["preco"] = v
        if links.get(rid):
            t["fonte"] = links[rid]
        dest["tamanhos"].append(t)
    for t in ent["tamanhos"]:
        if mesmo_tamanho(t["quantidade"], b["quantidade"]):
            v = {k: t[k] for k in ("preco", "frete", "prazo_dias") if k in t}
            dest["precos"].setdefault(t["rede"], v if "frete" in v else v["preco"])
            if t.get("fonte"):
                dlinks.setdefault(t["rede"], t["fonte"])
        else:
            dest["tamanhos"].append(t)


def juntar_categorias(parciais):
    """Junta os itens da lista de todas as categorias usando, para cada um, a base com mais preços."""
    lista = {}
    for prod in dict.fromkeys(p for parcial in parciais for p in parcial):
        ents = [parcial[prod] for parcial in parciais if prod in parcial]
        votos = {}
        for e in ents:
            if e.get("base"):
                k = (e["base"]["unidade"], e["base"]["quantidade"])
                votos[k] = votos.get(k, 0) + len(e["precos"]) + 0.5
        dest = {"precos": {}, "base": None, "tamanhos": [], "links": {}}
        if votos:
            un, q = max(votos, key=votos.get)
            dest["base"] = next(e["base"] for e in ents if e.get("base") and (e["base"]["unidade"], e["base"]["quantidade"]) == (un, q))
        for e in ents:
            juntar_item(dest, e)
        lista[prod] = dest
    return lista


def item_ofertas(prod, ent):
    out = {"produto": prod, "precos": ent["precos"]}
    links = {r: u for r, u in (ent.get("links") or {}).items() if r in ent["precos"]}
    if links:
        out["links"] = links
    if ent.get("base"):
        out["base"] = ent["base"]
        if ent["tamanhos"]:
            por_un = lambda t: (t["preco"] + (t.get("frete") or 0)) / t["quantidade"]  # noqa: E731
            out["tamanhos"] = sorted(ent["tamanhos"], key=por_un)[:12]
    return out


# ---------- busca direta nas lojas: o próprio site responde com o preço da loja do CEP ----------
# Giassi e Angeloni usam a VTEX: /api/checkout/pub/regions diz qual loja atende o CEP e a busca do site
# (intelligent-search) devolve produto, preço e estoque dessa loja. Não precisa de login nem de IA.
LOJAS_DIRETAS = {
    "giassi": {"nome": "Giassi", "site": "https://www.giassi.com.br", "categoria": "mercados"},
    "angeloni": {"nome": "Angeloni", "site": "https://super.angeloni.com.br", "categoria": "mercados"},
}
VTEX_TESTE = os.environ.get("OFERTAS_VTEX_TESTE")  # só para testes: um servidor falso no lugar dos sites
_regioes = {}
VAZIAS_BUSCA = {"de", "da", "do", "das", "dos", "para", "com", "em", "e", "a", "o", "p", "c", "sem", "tipo"}
UNIDADE_NOME = re.compile(r"(\d+(?:[.,]\d+)?)\s*(ml|l|lt|litros?|kg|g|gr|un|und|unid|unidades?|m|metros?)\b", re.I)


def nome_direta(nome):
    """Nome de uma loja com busca direta escrito do jeito dela (Giassi Supermercados → Giassi)."""
    n = norm(nome).replace(" ", "")
    for k, loja in LOJAS_DIRETAS.items():
        if n.startswith(k):
            return loja["nome"]
    return nome


def site_direta(chave):
    return VTEX_TESTE.rstrip("/") + "/" + chave if VTEX_TESTE else LOJAS_DIRETAS[chave]["site"]


def http_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": NAVEGADOR, "Accept": "application/json", "Accept-Language": "pt-BR,pt;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read(4_000_000).decode("utf-8") or "null")


def regiao_direta(chave, cep):
    """(id da região, nome da loja) que atende o CEP; (None, None) se a loja não entrega nele."""
    cep = re.sub(r"\D", "", str(cep or ""))
    k = (chave, cep)
    if k in _regioes and time.time() - _regioes[k][2] < 6 * 3600:
        return _regioes[k][:2]
    d = http_json(site_direta(chave) + "/api/checkout/pub/regions?country=BRA&postalCode=" + cep)
    r = d[0] if isinstance(d, list) and d else {}
    vend = (r.get("sellers") or [{}])[0] if r.get("sellers") else {}
    nome = str(vend.get("name") or "").strip()
    if re.fullmatch(r"[a-z]+\d*", nome):  # "giassi08": código, não nome de loja
        nome = ""
    val = (r.get("id") if vend else None, nome)
    _regioes[k] = (*val, time.time())
    return val


def palavras_busca(t):
    return [w for w in norm(re.sub(UNIDADE_NOME, " ", str(t))).split() if w not in VAZIAS_BUSCA and not w.isdigit()]


def combina(item, produto):
    """O produto do site é o item da lista? Todas as palavras do item (até 3) ou 3 de cada 4 precisam estar no nome
    ou nas categorias do produto ("JIMO Secante..." está em Limpeza › Lava-Louças)."""
    pi, pp = palavras_busca(item), norm(produto).split()
    if not pi:
        return False
    ok = sum(1 for w in pi if any(x == w or (len(w) >= 4 and (x.startswith(w) or (len(x) >= 4 and w.startswith(x)))) for x in pp))
    return ok == len(pi) if len(pi) <= 3 else ok >= 0.75 * len(pi)


PACOTE_NOME = re.compile(r"(?:\bc/\s*|\bcom\s+|\bcx\.?\s*(?:com\s*)?|\bpack\s*|\bx\s*)(\d{1,2})\b(?!\s*(?:ml|l|lt|g|gr|kg|m|un|und|unid|unidades?)\b)", re.I)


def tamanho_nome(nome):
    """Quantidade total do produto pelo nome: "Leite 1L" → 1 L; "Leite 1L Caixa com 12" → 12 L."""
    m = UNIDADE_NOME.findall(str(nome))
    if not m:
        return None
    q, u = m[-1]
    u = u.lower()
    u = "L" if u in ("l", "lt", "litro", "litros") else "un" if u.startswith("un") else "m" if u.startswith("metro") else u
    t = medida(q.replace(",", "."), u)
    pac = PACOTE_NOME.search(str(nome))
    if t and t[1] != "un" and pac and int(pac.group(1)) > 1:
        t = (round(t[0] * int(pac.group(1)), 4), t[1])
    return t


def busca_vtex(chave, termo, regiao):
    params = {"query": termo, "count": 12, "locale": "pt-BR"}
    if regiao:
        params["regionId"] = regiao
    d = http_json(site_direta(chave) + "/api/io/_v/api/intelligent-search/product_search/?" + urllib.parse.urlencode(params)) or {}
    out = []
    for prod in d.get("products") or []:
        nome = str(prod.get("productName") or "").strip()
        if not nome or "+" in nome or norm(nome).startswith("kit "):
            continue
        busca_em = " ".join([nome, str(prod.get("brand") or "")] + [str(c) for c in (prod.get("categories") or [])][:4])
        for it in (prod.get("items") or [])[:1]:
            ofs = [x.get("commertialOffer") or {} for x in it.get("sellers") or []]
            ofs = [o for o in ofs if numero(o.get("Price")) and (o.get("AvailableQuantity") or 0) > 0]
            if not ofs:
                continue
            o = min(ofs, key=lambda x: numero(x.get("Price")))
            preco, de = numero(o.get("Price")), numero(o.get("ListPrice"))
            tam = tamanho_nome(nome)
            if not tam and str(it.get("measurementUnit") or "").lower() == "kg":
                tam = medida(it.get("unitMultiplier") or 1, "kg")
            marca = texto(prod.get("brand"), 30) or ""
            curto = (marca + " " + fmt_base({"quantidade": tam[0], "unidade": tam[1]})) if marca and tam else nome[:60]
            out.append({"nome": nome, "curto": curto, "busca_em": busca_em, "preco": preco, "de": de if de and de > preco + 0.004 else None, "tam": tam,
                        "link": LOJAS_DIRETAS[chave]["site"] + str(prod.get("link") or "")})
    return out


def lojas_diretas_status(cfg):
    out = []
    for k, loja in LOJAS_DIRETAS.items():
        try:
            reg, nome = regiao_direta(k, cfg.get("cep"))
            out.append({"id": k, "nome": loja["nome"], "atende": bool(reg), "loja": nome})
        except Exception as e:  # noqa: BLE001
            out.append({"id": k, "nome": loja["nome"], "atende": None, "erro": str(e)[:120]})
    return out


def busca_direta(cfg, itens=None):
    """Pergunta a cada loja com busca direta o preço de cada item da lista. Devolve [(categoria, parcial)]."""
    nomes = itens or nomes_da_lista(cfg)
    if not nomes or not cfg.get("cep"):
        return []
    achados = {}  # item -> loja -> [candidatos]
    lojas = []
    for k, loja in LOJAS_DIRETAS.items():
        try:
            reg, unidade = regiao_direta(k, cfg.get("cep"))
        except Exception as e:  # noqa: BLE001
            log(f"busca direta {loja['nome']}: não consegui saber a loja do CEP ({e})")
            continue
        if not reg:
            log(f"busca direta {loja['nome']}: não atende o CEP {cfg.get('cep')}")
            continue
        BUSCA["etapa"] = "preços no site do " + loja["nome"]
        n = 0
        for nome in nomes:
            try:
                cand = [c for c in busca_vtex(k, nome, reg) if combina(nome, c["busca_em"])]
            except Exception as e:  # noqa: BLE001
                log(f"busca direta {loja['nome']} '{nome}': {e}")
                continue
            if cand:
                achados.setdefault(nome, {})[k] = cand
                n += 1
        lojas.append({"rede": loja["nome"], "endereco": unidade or None, "distancia_km": None, "site": LOJAS_DIRETAS[k]["site"], "fontes": ["Site"]})
        log(f"busca direta {loja['nome']}{' (' + unidade + ')' if unidade else ''}: {n} de {len(nomes)} item(ns) com preço")
    if not lojas:
        return []
    lista_bruta, ofertas = [], []
    for nome, por_loja in achados.items():
        # tamanho de sempre: o do nome do item ou o mais comum entre os produtos achados
        base = tamanho_nome(nome)
        if not base:
            conta = {}
            for cands in por_loja.values():
                for c in cands:
                    if c["tam"]:
                        conta[c["tam"]] = conta.get(c["tam"], 0) + 1
            base = max(conta, key=lambda t: (conta[t], -t[0])) if conta else None
        precos, tamanhos = [], []
        for k, cands in por_loja.items():
            rede = LOJAS_DIRETAS[k]["nome"]
            iguais = [c for c in cands if base and c["tam"] and c["tam"][1] == base[1] and mesmo_tamanho(c["tam"][0], base[0])] if base else cands
            if iguais:
                c = min(iguais, key=lambda x: x["preco"])
                precos.append({"rede": rede, "preco": c["preco"], "obs": c["curto"], "fonte": c["link"]})
            if base:
                outros = sorted((c for c in cands if c["tam"] and c["tam"][1] == base[1] and c not in iguais), key=lambda x: x["preco"] / x["tam"][0])
                for c in outros[:4]:
                    tamanhos.append({"rede": rede, "embalagem": c["curto"][:40], "quantidade": c["tam"][0], "unidade": c["tam"][1], "preco": c["preco"], "fonte": c["link"]})
            for c in cands[:3]:
                if c["de"]:
                    ofertas.append({"rede": rede, "produto": c["nome"], "preco_normal": c["de"], "preco_oferta": c["preco"], "tipo": "promo", "fonte": c["link"],
                                    "tamanho": {"quantidade": c["tam"][0], "unidade": c["tam"][1]} if c["tam"] else None})
        ent = {"produto": nome, "precos": precos, "tamanhos": tamanhos}
        if base:
            ent["base"] = {"quantidade": base[0], "unidade": base[1]}
        lista_bruta.append(ent)
    cfg_itens = dict(cfg, lista=[{"produto": n} for n in nomes])
    cat, parcial = normalizar("mercados", {"lojas": lojas, "cupons": [], "ofertas": ofertas, "lista": lista_bruta}, cfg_itens)
    return [(cat, parcial)]


MAX_FOCADA = 8


def instrucoes_focada(cfg, itens, cats):
    on = cfg.get("online") or {}
    locais = [CATEGORIAS[c]["o_que"] for c in cats if c != "online"]
    mkts = [MARKETPLACES.get(m, m) for m in (on.get("marketplaces") or ["mercadolivre", "amazon"])] if "online" in cats else []
    assin = [ASSINATURAS.get(a, a) for a in (on.get("assinaturas") or [])]
    numerados = [f"{k}) {n}" for k, n in enumerate(itens, 1)]
    return f"""Preciso do preço atual ({hoje_br()}) destes itens de uma lista de compras, para o CEP {cfg.get('cep')}, no Brasil: {'; '.join(numerados)}.

Use a busca na web agora e procure item por item: no site e no app das lojas, em encartes, no Google Shopping e em comparadores de preço. Use só o que encontrar: não invente preços. Se não conseguir usar a busca na web, responda apenas {{"erro": "sem_busca"}}.

Onde procurar: {', '.join(locais) or 'nenhuma loja física'}{f' num raio de {cfg.get("raio_km") or 2} km do CEP' if locais else ''}{('; e online em ' + ', '.join(mkts) + ' com entrega no CEP') if mkts else ''}.
Assinaturas do morador: {', '.join(assin) or 'nenhuma'}.
Se o item for genérico (por exemplo "pó lava louça"), procure as marcas mais vendidas e diga em "obs" qual produto e tamanho é cada preço. Traga até 4 preços por item, de lojas diferentes.
"categoria" é {', '.join(f'"{c}"' for c in cats)}. Online, informe "frete" (0 se grátis) e "prazo_dias".

Em "fonte", ponha o link da página do produto (o anúncio no Mercado Livre, a página na Amazon, o produto no site da loja), não a página inicial.

Responda somente com um objeto JSON, sem texto antes ou depois:
{{"lista": [{{"item": 1, "produto": "texto do item", "base": {{"quantidade": 1, "unidade": "kg", "rotulo": null}}, "precos": [{{"rede": "nome da loja", "categoria": "mercados", "preco": 12.9, "preco_clube": null, "frete": null, "prazo_dias": null, "obs": "Marca 1 kg", "fonte": "URL"}}]}}]}}"""


def categoria_do_preco(p, cats):
    """Em que categoria entra um preço da busca focada."""
    c = p.get("categoria")
    if c in cats:
        return c
    nome = norm(p.get("rede") or "")
    if "online" in cats and (frete_ok(p.get("frete")) is not None
                             or any(norm(m) in nome for m in list(MARKETPLACES.values()) + ["shopee", "magazine"])):
        return "online"
    pistas = {"farmacias": ("drog", "farm", "raia", "pacheco", "panvel", "pague menos"),
              "petshops": ("pet", "cobasi", "petz", "agro")}
    for cat, palavras in pistas.items():
        if cat in cats and any(w in nome for w in palavras):
            return cat
    locais = [c for c in cats if c != "online"]
    return "mercados" if "mercados" in locais else (locais[0] if locais else None)


def busca_focada(cfg, itens, cats):
    """Uma pergunta só sobre os itens que ficaram sem preço. Devolve [(categoria, parcial)]."""
    itens = itens[:MAX_FOCADA]
    if not itens or not cats:
        return []
    try:
        r = chamar_ai_task("EconomIA: itens sem preço", instrucoes_focada(cfg, itens, cats))
    except ErroCota:
        log("cota da IA na busca dos itens sem preço: esperando 60 s")
        time.sleep(ESPERA_COTA)
        r = chamar_ai_task("EconomIA: itens sem preço", instrucoes_focada(cfg, itens, cats))
    if not isinstance(r, dict):
        raise ErroBusca("A IA respondeu fora do formato esperado.")
    if r.get("erro") == "sem_busca":
        raise ErroBusca(SEM_BUSCA)
    por_cat = {}
    for it in r.get("lista") or []:
        if not isinstance(it, dict):
            continue
        for campo in ("precos", "tamanhos"):
            for p in it.get(campo) or []:
                if not isinstance(p, dict):
                    continue
                c = categoria_do_preco(p, cats)
                if not c:
                    continue
                alvo = por_cat.setdefault(c, {})
                k = it.get("item") or it.get("produto")
                ent = alvo.setdefault(str(k), dict(it, precos=[], tamanhos=[]))
                ent[campo].append(p)
    cfg_itens = dict(cfg, lista=[{"produto": n} for n in itens])
    out = []
    for c, ents in por_cat.items():
        cat, parcial = normalizar(c, {"lojas": [], "cupons": [], "ofertas": [], "lista": list(ents.values())}, cfg_itens)
        out.append((cat, parcial))
    achados = {p for _, parcial in out for p in parcial}
    log(f"itens sem preço: {len(achados)} de {len(itens)} encontrados")
    return out


def juntar_focada(novas, parciais, resultado):
    for cat, parcial in resultado:
        alvo = next((c for c in novas if c.get("id") == cat["id"]), None)
        if alvo is None:
            novas.append(cat)
        else:
            juntar_categoria(alvo, cat)
        parciais.append(parcial)


def nomes_da_lista(cfg):
    return [nome_item(i) for i in (cfg.get("lista") or []) if nome_item(i)]


def buscar():
    cfg = ler_json(CONFIG, {}) or {}
    cats = [c for c in (cfg.get("categorias") or list(CATEGORIAS)) if c in CATEGORIAS]
    BUSCA.update({"rodando": True, "erro": None, "avisos": [], "atual": 0, "total": len(cats), "etapa": None, "chamadas_ia": None})
    try:
        if not cfg.get("cep"):
            raise ErroBusca("Salve o CEP em Mais antes de buscar.")
        anterior = ler_json(OFERTAS, {}) or {}
        antigas = {c.get("id"): c for c in (anterior.get("categorias") or []) if isinstance(c, dict)}
        novas, parciais, falhas = [], [], []
        relatorio = {"categorias": {}, "sem_preco": [], "falhas": []}
        _uso_local.chamadas = 0
        for i, cat_id in enumerate(cats, 1):
            BUSCA.update({"atual": i, "etapa": CATEGORIAS[cat_id]["nome"].lower()})
            log(f"buscando {cat_id}")
            try:
                try:
                    cat, parcial = normalizar(cat_id, chamar_ai_task(f"EconomIA: {cat_id}", instrucoes_para(cat_id, cfg)), cfg)
                except ErroCota:
                    BUSCA["etapa"] = CATEGORIAS[cat_id]["nome"].lower() + " (a IA pediu uma pausa, tentando de novo em 1 minuto)"
                    log("cota da IA: esperando 60 s")
                    time.sleep(ESPERA_COTA)
                    BUSCA["etapa"] = CATEGORIAS[cat_id]["nome"].lower()
                    cat, parcial = normalizar(cat_id, chamar_ai_task(f"EconomIA: {cat_id}", instrucoes_para(cat_id, cfg)), cfg)
            except ErroBusca as e:
                if isinstance(e, ErroCota):
                    raise
                if any(t in str(e) for t in ("Falta uma IA", "não usou a busca na web", "não tem acesso", "não tem permissão", "assistente de conversa")):
                    raise
                falhas.append(f"{CATEGORIAS[cat_id]['nome']}: {e}")
                relatorio["categorias"][cat_id] = {"ok": False, "erro": str(e)[:200]}
                if cat_id in antigas:
                    novas.append(antigas[cat_id])
                continue
            novas.append(cat)
            parciais.append(parcial)
            relatorio["categorias"][cat_id] = {"ok": True, "ofertas": len(cat["ofertas"]), "lojas": len(cat["lojas"]),
                                               "precos": sum(len(v["precos"]) for v in parcial.values())}
        falhou_tudo = not novas or len(falhas) == len(cats)
        if "mercados" in cats and opcao("lojas_diretas", cfg):
            try:
                diretas = busca_direta(cfg)
            except Exception as e:  # noqa: BLE001
                diretas = []
                log(f"busca direta: {e}")
            if diretas:
                juntar_focada(novas, parciais, diretas)
                relatorio["diretas"] = sorted({r["nome"] for c, _ in diretas for r in c["redes"]})
                falhou_tudo = False
        sites = [a for a in ((cfg.get("lojas") or {}).get("adicionar") or [])
                 if isinstance(a, dict) and url_ok(a.get("site")) and a.get("categoria") in cats and texto(a.get("nome"), 60)]
        BUSCA["total"] = len(cats) + len(sites)
        for j, loja in enumerate(sites, 1):
            loja = {"nome": texto(loja["nome"], 60).split(",")[0].strip(), "site": loja["site"], "categoria": loja["categoria"]}
            BUSCA.update({"atual": len(cats) + j, "etapa": "encarte de " + loja["nome"]})
            try:
                cat_e, parcial_e = ler_encarte(loja, cfg)
            except ErroBusca as e:
                falhas.append(f"Encarte de {loja['nome']}: {e}")
                continue
            alvo = next((c for c in novas if c.get("id") == cat_e["id"]), None)
            if alvo is None:
                novas.append(cat_e)
            else:
                juntar_categoria(alvo, cat_e)
            parciais.append(parcial_e)
            falhou_tudo = False
        # lojas do raio que a busca achou com site, mas sem nenhum preço: tenta ler o encarte do site
        com_preco = {r for parcial in parciais for ent in parcial.values() for r in list(ent["precos"]) + [t["rede"] for t in ent["tamanhos"]]}
        manuais = {norm(l["nome"]) for l in sites}
        ignorar = set((cfg.get("lojas") or {}).get("ignorar") or [])
        try:
            raio = float(cfg.get("raio_km") or 2)
        except (TypeError, ValueError):
            raio = 2.0
        auto = []
        for c in novas:
            if c.get("id") not in cats or c.get("id") == "online":
                continue
            nomes = {r["id"]: r["nome"] for r in c.get("redes") or []}
            ofertou = {o["rede"] for o in c.get("ofertas") or []}
            for l in c.get("lojas") or []:
                rid = l.get("rede")
                d = l.get("distancia_km")
                if (url_ok(l.get("site")) and rid not in ofertou and rid not in com_preco and rid not in ignorar
                        and (d is None or d <= raio) and norm(nomes.get(rid, "")) not in manuais):
                    auto.append((c, l, nomes.get(rid, rid)))
        for c, l, nome in auto[:AUTO_ENCARTES if opcao("encartes_auto", cfg) else 0]:
            BUSCA.update({"etapa": "encarte de " + nome})
            try:
                cat_e, parcial_e = ler_encarte({"nome": nome, "site": l["site"], "categoria": c["id"]}, cfg)
            except ErroBusca as e:
                l["site_sem_encarte"] = True
                log(f"encarte automático de {nome}: {e}")
                continue
            if not cat_e["ofertas"] and not parcial_e:
                l["site_sem_encarte"] = True
                continue
            juntar_categoria(c, cat_e)
            parciais.append(parcial_e)
            l["encarte_auto"] = True
            l["fontes"] = sorted(set(l.get("fontes") or []) | {"Encarte"})
        lista = juntar_categorias(parciais)
        if falhou_tudo:
            raise ErroBusca(falhas[0] if falhas else "A busca não trouxe resultados.")
        # itens que ninguém achou: uma pergunta só sobre eles
        faltam = [n for n in nomes_da_lista(cfg) if n not in lista]
        if faltam and opcao("itens_sem_preco", cfg):
            BUSCA.update({"etapa": f"{len(faltam)} item(ns) sem preço"})
            try:
                juntar_focada(novas, parciais, busca_focada(cfg, faltam, cats))
                lista = juntar_categorias(parciais)
            except ErroBusca as e:
                log(f"busca dos itens sem preço: {e}")
        relatorio["sem_preco"] = [n for n in nomes_da_lista(cfg) if n not in lista]
        relatorio["falhas"] = falhas
        relatorio["chamadas_ia"] = _uso_local.chamadas
        BUSCA["chamadas_ia"] = _uso_local.chamadas
        gravar_json(OFERTAS, {
            "versao": 2, "gerado_em": agora(), "origem": "ia_home_assistant",
            "lista": [item_ofertas(p, v) for p, v in lista.items()],
            "categorias": novas,
            "relatorio": relatorio,
        })
        if falhas:
            BUSCA["avisos"] = ["Algumas buscas falharam e mantive o resultado anterior: " + " | ".join(falhas)]
        log(f"busca concluída com {_uso_local.chamadas} chamada(s) de IA" + (f"; sem preço: {', '.join(relatorio['sem_preco'])}" if relatorio["sem_preco"] else ""))
    except ErroBusca as e:
        BUSCA["erro"] = str(e)
        log(f"busca falhou: {e}")
    except Exception as e:  # noqa: BLE001
        BUSCA["erro"] = f"Erro inesperado na busca: {e}"
        log(BUSCA["erro"])
    finally:
        BUSCA.update({"rodando": False, "etapa": None, "terminou_em": agora()})


def buscar_itens(itens):
    cfg = ler_json(CONFIG, {}) or {}
    cats = [c for c in (cfg.get("categorias") or list(CATEGORIAS)) if c in CATEGORIAS]
    _uso_local.chamadas = 0
    BUSCA.update({"rodando": True, "erro": None, "avisos": [], "atual": 1, "total": 1, "chamadas_ia": None,
                  "etapa": (itens[0] if len(itens) == 1 else f"{len(itens)} itens").lower()})
    try:
        if not cfg.get("cep"):
            raise ErroBusca("Salve o CEP em Mais antes de buscar.")
        resultado = []
        if "mercados" in cats and opcao("lojas_diretas", cfg):
            try:
                resultado += busca_direta(cfg, itens)
            except Exception as e:  # noqa: BLE001
                log(f"busca direta: {e}")
        try:
            resultado = busca_focada(cfg, itens, cats) + resultado  # o site da loja por último: vale mais
        except ErroBusca:
            if not resultado:
                raise
        anterior = ler_json(OFERTAS, {}) or {}
        novas = [c for c in (anterior.get("categorias") or []) if isinstance(c, dict)]
        base = {}
        for i in anterior.get("lista") or []:
            if isinstance(i, dict) and i.get("produto"):
                base[i["produto"]] = {"precos": dict(i.get("precos") or {}), "base": i.get("base"),
                                      "tamanhos": list(i.get("tamanhos") or []), "links": dict(i.get("links") or {})}
        parciais = [base]
        juntar_focada(novas, parciais, resultado)
        lista = juntar_categorias(parciais)
        relatorio = anterior.get("relatorio") if isinstance(anterior.get("relatorio"), dict) else {}
        achados = [n for n in itens if n in lista and any(n in p for _, p in resultado)]
        relatorio["sem_preco"] = [n for n in nomes_da_lista(cfg) if n not in lista]
        gravar_json(OFERTAS, dict(anterior, versao=2, origem="ia_home_assistant", gerado_em=anterior.get("gerado_em") or agora(),
                                  atualizado_em=agora(), lista=[item_ofertas(p, v) for p, v in lista.items()],
                                  categorias=novas, relatorio=relatorio))
        if not achados:
            BUSCA["avisos"] = ["Não achei preço para " + ", ".join(itens) + ". Tente com marca e tamanho, por exemplo \"Detergente Ypê 500 ml\"."]
        BUSCA["chamadas_ia"] = _uso_local.chamadas
        log(f"busca de itens: {len(achados)} de {len(itens)} com preço, {_uso_local.chamadas} chamada(s) de IA")
    except ErroBusca as e:
        BUSCA["erro"] = str(e)
        log(f"busca de itens falhou: {e}")
    except Exception as e:  # noqa: BLE001
        BUSCA["erro"] = f"Erro inesperado na busca: {e}"
        log(BUSCA["erro"])
    finally:
        BUSCA.update({"rodando": False, "etapa": None, "terminou_em": agora()})


# ---------- ler a lista de fotos ou texto ----------
def instrucoes_leitura(texto_msg, n_fotos, cfg, origem="mensagem"):
    atuais = [nome_item(i) for i in (cfg.get("lista") or []) if nome_item(i)]
    partes = []
    if n_fotos:
        partes.append(f"{n_fotos} imagem(ns) em anexo")
    if texto_msg:
        partes.append("o texto abaixo")
    abertura = ("A pessoa falou o que precisa comprar, e a fala para texto do Home Assistant transcreveu. Você recebe a transcrição abaixo; "
                "números podem vir por extenso e pode haver erros de transcrição: corrija pelo sentido."
                if origem == "fala" else f"Alguém mandou, provavelmente pelo WhatsApp, coisas para comprar. Você recebe {' e '.join(partes)}.")
    return f"""{abertura}
Pode ser print de conversa, lista escrita à mão, foto de produto ou de embalagem vazia, encarte ou receita.

Extraia só os itens a comprar, em português do Brasil, um por item, do jeito que se escreve numa lista de compras: o nome do produto e, se aparecer, a marca, o tamanho ou a dosagem (por exemplo "Lysoform", "Leite integral 1 L", "Dipirona 500 mg"). A quantidade (por exemplo "2" ou "3 pacotes") vai em "quantidade", não no nome. Junte itens repetidos. Ignore conversa que não seja item de compra, preços, horários e nomes de pessoas.
Itens que já estão na lista: {'; '.join(atuais) or 'nenhum'}. Se um item for o mesmo de um desses, use exatamente o nome que já está na lista.
{('Texto:' + chr(10) + chr(34) * 3 + texto_msg + chr(34) * 3) if texto_msg else ''}

Responda somente com um objeto JSON, sem texto antes ou depois:
{{"itens": [{{"produto": "Leite integral 1 L", "quantidade": "2", "obs": null}}]}}
Se não achar nenhum item, responda {{"itens": []}}."""


def instrucoes_cupons(n_fotos, nomes):
    return f"""Você recebe {n_fotos} print(s) do app ou do site de lojas (farmácias, mercados, pet shops) com cupons ou ofertas da conta do cliente.

Extraia cada cupom ou oferta pessoal: a loja, o código (muitos são ativados com um toque e não têm código: use null), um benefício curto (por exemplo "20% em Colgate" ou "R$ 10 acima de R$ 80"), a condição, a validade e o produto, se for de um produto específico.
Ignore propaganda que não seja cupom ou oferta da conta. Não invente: se a validade não aparecer, use null.
Lojas que o morador acompanha: {'; '.join(nomes) or 'nenhuma'}. Quando for uma delas, use exatamente esse nome em "loja".

Responda somente com um objeto JSON, sem texto antes ou depois:
{{"cupons": [{{"loja": "Panvel", "codigo": null, "beneficio": "20% em Colgate", "condicao": "Ativado no app", "valido_ate": "AAAA-MM-DD ou null", "produto": "Colgate"}}]}}
Se não achar nenhum cupom, responda {{"cupons": []}}."""


def ler_cupons(bruto):
    of = ler_json(OFERTAS, {}) or {}
    redes = {norm(r.get("nome") or ""): r.get("id") for c in of.get("categorias") or [] if isinstance(c, dict)
             for r in c.get("redes") or [] if isinstance(r, dict) and r.get("id")}
    cupons, vistos = [], set()
    for c in (bruto.get("cupons") if isinstance(bruto, dict) else None) or []:
        if not isinstance(c, dict) or not texto(c.get("beneficio"), 60):
            continue
        cup = {"loja": texto(c.get("loja"), 60) or "", "beneficio": texto(c.get("beneficio"), 60)}
        cup["rede"] = redes.get(norm(cup["loja"]))
        for campo, lim in (("codigo", 40), ("condicao", 120), ("produto", 60)):
            if texto(c.get(campo), lim):
                cup[campo] = texto(c.get(campo), lim)
        if data_ok(c.get("valido_ate")):
            cup["valido_ate"] = data_ok(c.get("valido_ate"))
        k = (norm(cup["loja"]), norm(cup["beneficio"]), cup.get("codigo"))
        if k not in vistos:
            vistos.add(k)
            cupons.append(cup)
    return cupons[:30]


def ler_lista(job, fotos, texto_msg, tipo="lista", origem="mensagem"):
    pasta = os.path.join(MEDIA, "economia")
    arquivos, anexos = [], []
    try:
        if fotos:
            try:
                os.makedirs(pasta, exist_ok=True)
            except OSError as e:
                raise ErroBusca("O add-on não consegue usar a pasta de mídia do Home Assistant. Reinstale a versão mais nova.") from e
            for n, (dado, mime) in enumerate(fotos):
                ext = "png" if mime == "image/png" else "webp" if mime == "image/webp" else "jpg"
                nome = f"lista-{job}-{n}.{ext}"
                with open(os.path.join(pasta, nome), "wb") as f:
                    f.write(dado)
                arquivos.append(os.path.join(pasta, nome))
                anexos.append({"media_content_id": f"{MEDIA_URI}/economia/{nome}", "media_content_type": mime})
        cfg = ler_config()
        if tipo == "cupons":
            of = ler_json(OFERTAS, {}) or {}
            nomes = [r.get("nome") for c in of.get("categorias") or [] if isinstance(c, dict)
                     for r in c.get("redes") or [] if isinstance(r, dict) and r.get("nome")]
            cupons = ler_cupons(chamar_ai_task("EconomIA: ler cupons", instrucoes_cupons(len(anexos), nomes), anexos, uso="fotos"))
            LEITURAS[job].update({"status": "pronto", "cupons": cupons})
            log(f"leitura {job}: {len(cupons)} cupom(ns)")
            return
        bruto = chamar_ai_task("EconomIA: falar" if origem == "fala" else "EconomIA: ler lista",
                               instrucoes_leitura(texto_msg, len(anexos), cfg, origem), anexos, uso="fotos")
        atuais = {norm(nome_item(i)): nome_item(i) for i in (cfg.get("lista") or []) if nome_item(i)}
        itens, vistos = [], set()
        for it in (bruto.get("itens") if isinstance(bruto, dict) else None) or []:
            if not isinstance(it, dict):
                continue
            prod = texto(it.get("produto"), 80)
            if not prod or len(prod) < 2 or norm(prod) in vistos:
                continue
            vistos.add(norm(prod))
            item = {"produto": atuais.get(norm(prod), prod), "ja_na_lista": norm(prod) in atuais}
            if texto(it.get("quantidade"), 20):
                item["quantidade"] = texto(it.get("quantidade"), 20)
            if texto(it.get("obs"), 60):
                item["obs"] = texto(it.get("obs"), 60)
            itens.append(item)
        LEITURAS[job].update({"status": "pronto", "itens": itens[:40]})
        log(f"leitura {job}: {len(itens)} item(ns)")
    except ErroBusca as e:
        LEITURAS[job].update({"status": "erro", "erro": str(e)})
    except Exception as e:  # noqa: BLE001
        LEITURAS[job].update({"status": "erro", "erro": f"Erro inesperado ao ler: {e}"})
        log(LEITURAS[job]["erro"])
    finally:
        for a in arquivos:
            try:
                os.remove(a)
            except OSError:
                pass


def comeca_leitura(dado):
    fotos = []
    for img in (dado.get("imagens") or [])[:8]:
        m = re.match(r"^data:(image/(?:jpeg|png|webp));base64,(.+)$", str(img), re.S)
        if not m:
            continue
        try:
            bruto = base64.b64decode(m.group(2), validate=False)
        except ValueError:
            continue
        if 0 < len(bruto) <= 6 * 1024 * 1024:
            fotos.append((bruto, m.group(1)))
    tipo = "cupons" if dado.get("tipo") == "cupons" else "lista"
    texto_msg = "" if tipo == "cupons" else str(dado.get("texto") or "").strip()[:4000]
    if not fotos and not texto_msg:
        return None
    job = datetime.now().strftime("%H%M%S") + "-" + os.urandom(3).hex()
    for antigo in sorted(LEITURAS)[:-20]:
        LEITURAS.pop(antigo, None)
    LEITURAS[job] = {"status": "lendo", "itens": [], "erro": None}
    origem = "fala" if dado.get("origem") == "fala" and not fotos else "mensagem"
    threading.Thread(target=ler_lista, args=(job, fotos, texto_msg, tipo, origem), daemon=True).start()
    return job


# ---------- Falar: o áudio vai para a fala para texto do Home Assistant ----------
VOZ = voz.Voz(HA_API, HA_WS, None, lambda *a: log(" ".join(str(x) for x in a)), simulada=VOZ_SIMULADA)


def voz_status():
    if not ia_ligada():
        return {"pronta": False, "motivo": "A IA está desligada em Mais › Integrações."}
    VOZ.token = token_ha()
    if not VOZ.token and not VOZ_SIMULADA:
        return {"pronta": False, "motivo": "Fora do Home Assistant não dá para falar."}
    return VOZ.status()


def voz_texto(pcm):
    if not ia_ligada():
        raise ErroBusca(IA_DESLIGADA)
    VOZ.token = token_ha()
    inicio = time.time()
    try:
        r = VOZ.texto(pcm)
    except voz.ErroVoz as e:
        log(f"Falar: {e}")
        raise ErroBusca(str(e)) from e
    log(f"Falar: {len(pcm) / 32000:.1f} s de áudio, texto em {time.time() - inicio:.1f} s ({r.get('nome') or 'fala para texto'})")
    return r


# ---------- exportar a lista ----------
def dados_lista():
    cfg = ler_json(CONFIG, {}) or {}
    of = ler_json(OFERTAS, {}) or {}
    lojas_cfg = cfg.get("lojas") or {}
    ignorar, manter = set(lojas_cfg.get("ignorar") or []), set(lojas_cfg.get("manter") or [])
    try:
        raio = float(cfg.get("raio_km") or 2)
    except (TypeError, ValueError):
        raio = 2.0
    cats = of.get("categorias") or []
    ativas = set(cfg.get("categorias") or [c.get("id") for c in cats if isinstance(c, dict)])
    info = {}
    for c in cats:
        if not isinstance(c, dict):
            continue
        dist = {l.get("rede"): l.get("distancia_km") for l in c.get("lojas") or [] if isinstance(l, dict)}
        for r in c.get("redes") or []:
            if isinstance(r, dict) and r.get("id"):
                info[r["id"]] = {"nome": r.get("nome") or r["id"], "tipo": c.get("singular") or c.get("nome") or "",
                                 "cat": c.get("id"), "dist": dist.get(r["id"])}

    def acompanha(rid):
        i = info.get(rid)
        if not i or i["cat"] not in ativas or rid in ignorar:
            return False
        return rid in manter or i["dist"] is None or i["dist"] <= raio

    precos = {norm(i.get("produto")): i.get("precos") or {} for i in of.get("lista") or [] if isinstance(i, dict)}
    socios = set(cfg.get("clubes") or [])
    itens = []
    for it in cfg.get("lista") or []:
        prod = it.get("produto") if isinstance(it, dict) else str(it)
        if not prod:
            continue
        compras = sorted(d for d in ((it.get("compras") or []) if isinstance(it, dict) else []) if data_ok(d))
        ps = sorted(({"loja": info[r]["nome"], "tipo": info[r]["tipo"], "preco": valor_total(v, r in socios)}
                     for r, v in precos.get(norm(prod), {}).items() if acompanha(r) and valor_total(v, r in socios)),
                    key=lambda x: x["preco"])
        ritmo = None
        if len(compras) >= 2:
            ds = [datetime.strptime(d, "%Y-%m-%d") for d in compras]
            ritmo = max(1, round(sum((ds[k] - ds[k - 1]).days for k in range(1, len(ds))) / (len(ds) - 1)))
        itens.append({"produto": prod, "mais_barato": ps[0] if ps else None, "precos": ps,
                      "economia": (round(ps[-1]["preco"] - ps[0]["preco"], 2) or None) if len(ps) > 1 else None,
                      "compras": compras, "compra_a_cada_dias": ritmo})
    return itens, of.get("gerado_em")


def br_data(iso):
    return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"


def br_preco(v):
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def xlsx(linhas, larguras, moeda):
    """Planilha .xlsx mínima: uma aba, cabeçalho em negrito e congelado, colunas de dinheiro em R$."""
    def ref(c, r):
        letras = ""
        c += 1
        while c:
            c, resto = divmod(c - 1, 26)
            letras = chr(65 + resto) + letras
        return f"{letras}{r}"
    linhas_xml = []
    for r, linha in enumerate(linhas, 1):
        celulas = []
        for c, v in enumerate(linha):
            if v is None or v == "":
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                estilo = ' s="2"' if c in moeda else ""
                celulas.append(f'<c r="{ref(c, r)}"{estilo}><v>{v}</v></c>')
            else:
                estilo = ' s="1"' if r == 1 else ""
                celulas.append(f'<c r="{ref(c, r)}" t="inlineStr"{estilo}><is><t xml:space="preserve">{xml_esc(str(v))}</t></is></c>')
        linhas_xml.append(f'<row r="{r}">{"".join(celulas)}</row>')
    cols = "".join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>' for i, w in enumerate(larguras, 1))
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    partes = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook {ns} xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Minha lista" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>',
        "xl/styles.xml": f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet {ns}><numFmts count="1"><numFmt numFmtId="164" formatCode="&quot;R$&quot; #,##0.00"/></numFmts><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/><xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>',
        "xl/worksheets/sheet1.xml": f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet {ns}><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols>{cols}</cols><sheetData>{"".join(linhas_xml)}</sheetData></worksheet>',
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in partes.items():
            z.writestr(nome, conteudo)
    return buf.getvalue()


def exportar(formato):
    itens, ultima = dados_lista()
    if formato == "json":
        dado = {"app": "EconomIA", "exportado_em": agora(), "ultima_busca": ultima, "lista": itens}
        return json.dumps(dado, ensure_ascii=False, indent=2).encode("utf-8"), "application/json; charset=utf-8"
    cab = ["Produto", "Mais barato em", "Tipo de loja", "Preço", "Economia", "Outras lojas",
           "Compra a cada (dias)", "Última compra", "Datas de compra"]
    linhas = [cab]
    for i in itens:
        mb = i["mais_barato"] or {}
        linhas.append([
            i["produto"], mb.get("loja"), mb.get("tipo"), mb.get("preco"), i["economia"],
            "; ".join(f'{p["loja"]} {br_preco(p["preco"])}' for p in i["precos"][1:]),
            i["compra_a_cada_dias"], br_data(i["compras"][-1]) if i["compras"] else None,
            ", ".join(br_data(d) for d in i["compras"]),
        ])
    return xlsx(linhas, [42, 22, 14, 12, 12, 48, 12, 14, 36], {3, 4}), \
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ---------- HTTP ----------
class Painel(BaseHTTPRequestHandler):
    server_version = "EconomIA/0.12.0"

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

    def _corpo(self, limite=MAX_BODY):
        tamanho = int(self.headers.get("Content-Length") or 0)
        if tamanho <= 0 or tamanho > limite:
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
        elif re.fullmatch(r"/fonts/[a-z0-9-]+\.(woff2?|txt)", rota):
            caminho = os.path.join(WWW, rota.lstrip("/"))
            if not os.path.isfile(caminho):
                return self._json(404, {"erro": "Não encontrado"})
            with open(caminho, "rb") as f:
                corpo = f.read()
            ext = rota.rsplit(".", 1)[1]
            self.send_response(200)
            self.send_header("Content-Type", {"woff": "font/woff", "woff2": "font/woff2"}.get(ext, "text/plain; charset=utf-8"))
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
        elif rota == "/api/estado":
            self._json(200, {
                "config": ler_json(CONFIG),
                "ofertas": ler_json(OFERTAS),
                "usuario": self.headers.get("X-Remote-User-Display-Name") or self.headers.get("X-Remote-User-Name") or None,
                "busca": BUSCA,
                "sync": SYNC,
                "uso_ia": uso_resumo(),
            })
        elif rota == "/api/todos":
            try:
                self._json(200, {"listas": listas_ha()})
            except ErroBusca as e:
                self._json(502, {"erro": str(e)})
        elif rota == "/api/busca":
            self._json(200, BUSCA)
        elif rota == "/api/uso-ia":
            self._json(200, uso_resumo())
        elif rota == "/api/voz/status":
            self._json(200, voz_status())
        elif rota == "/api/lojas-diretas":
            self._json(200, {"lojas": lojas_diretas_status(ler_config())})
        elif rota == "/api/versoes":
            self._json(200, {"versoes": listar_versoes()})
        elif rota == "/api/exportar/ofertas.json":
            corpo = json.dumps(ler_json(OFERTAS, {}) or {}, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="economia-ofertas-{hoje_br()}.json"')
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
        elif rota == "/api/ias":
            try:
                self._json(200, ias_disponiveis())
            except ErroBusca as e:
                self._json(502, {"erro": str(e), "tarefas": [], "agentes": []})
        elif rota == "/api/ler-lista":
            job = (urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("id") or [""])[0]
            if job not in LEITURAS:
                return self._json(404, {"erro": "Leitura não encontrada."})
            self._json(200, LEITURAS[job])
        elif rota in ("/api/exportar/lista.xlsx", "/api/exportar/lista.json"):
            formato = "json" if rota.endswith(".json") else "xlsx"
            corpo, tipo = exportar(formato)
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Disposition", f'attachment; filename="economia-minha-lista-{hoje_br()}.{formato}"')
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
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
            with _cfg_trava:
                atual = ler_config()
                base, cur = int(cfg.get("rev") or 0), int(atual.get("rev") or 0)
                mesclado = False
                if cur > base:
                    for d in DIARIO:
                        if d["rev"] > base:
                            aplicar_diario(cfg, d)
                            mesclado = True
                cfg["rev"] = cur
                try:
                    guardar_versao("auto")
                except OSError as e:
                    log(f"versão anterior: {e}")
                ligados = sensores_ligados(atual), ia_ligada(atual)
                novo = gravar_config(cfg)
            if (sensores_ligados(novo), ia_ligada(novo)) != ligados:
                threading.Thread(target=publica_sensor_uso, daemon=True).start()
            self._json(200, {"ok": True, "config": novo, "mesclado": mesclado})
        elif rota == "/api/ofertas":
            dado = self._corpo()
            if dado is None:
                return
            if not isinstance(dado.get("categorias"), list):
                return self._json(400, {"erro": "Faltou a lista de categorias."})
            gravar_json(OFERTAS, dado)
            self._json(200, {"ok": True})
        else:
            self._json(404, {"erro": "Não encontrado"})

    def do_POST(self):
        if not self._permitido():
            return
        if urllib.parse.urlsplit(self.path).path == "/api/sincronizar-lista":
            try:
                sincronizar_lista()
            except ErroBusca as e:
                SYNC["erro"] = str(e)
            return self._json(200, {"sync": SYNC, "rev": int(ler_config().get("rev") or 0)})
        if urllib.parse.urlsplit(self.path).path == "/api/voz":
            tamanho = int(self.headers.get("Content-Length") or 0)
            if tamanho <= 0 or tamanho > voz.MAX_BYTES + 4096:
                return self._json(413, {"erro": "Fale até 2 minutos de cada vez."})
            try:
                return self._json(200, voz_texto(self.rfile.read(tamanho)))
            except ErroBusca as e:
                return self._json(400, {"erro": str(e)})
        if urllib.parse.urlsplit(self.path).path == "/api/versoes/guardar":
            dado = self._corpo() or {}
            try:
                return self._json(200, {"nome": guardar_versao(str(dado.get("motivo") or "auto"), forcar=True)})
            except OSError as e:
                return self._json(500, {"erro": f"Não consegui guardar a cópia ({e})."})
        if urllib.parse.urlsplit(self.path).path == "/api/versoes/restaurar":
            dado = self._corpo() or {}
            try:
                return self._json(200, {"ok": True, "config": restaurar_versao(dado.get("nome"))})
            except ErroBusca as e:
                return self._json(400, {"erro": str(e)})
        if urllib.parse.urlsplit(self.path).path == "/api/testar-ia":
            dado = self._corpo() or {}
            try:
                return self._json(200, testar_ia("fotos" if dado.get("uso") == "fotos" else "busca"))
            except ErroBusca as e:
                return self._json(200, {"ok": False, "msg": str(e)})
        if urllib.parse.urlsplit(self.path).path == "/api/ler-lista":
            dado = self._corpo(MAX_FOTOS_BODY)
            if dado is None:
                return
            if not ia_ligada():
                return self._json(400, {"erro": IA_DESLIGADA})
            job = comeca_leitura(dado)
            if not job:
                return self._json(400, {"erro": "Escolha uma foto ou cole o texto da mensagem."})
            return self._json(202, {"id": job})
        rota = urllib.parse.urlsplit(self.path).path
        if rota not in ("/api/buscar", "/api/buscar-itens"):
            return self._json(404, {"erro": "Não encontrado"})
        alvo, args = buscar, ()
        if rota == "/api/buscar-itens":
            dado = self._corpo() or {}
            nomes = {norm(n): n for n in nomes_da_lista(ler_json(CONFIG, {}) or {})}
            itens = list(dict.fromkeys(nomes[norm(i)] for i in (dado.get("itens") or []) if isinstance(i, str) and norm(i) in nomes))
            if not itens:
                return self._json(400, {"erro": "Esse item não está na lista."})
            alvo, args = buscar_itens, (itens[:MAX_FOCADA],)
        with _trava:
            if BUSCA["rodando"]:
                return self._json(202, {"ok": True, "ja_rodando": True})
            cfg = ler_json(CONFIG, {}) or {}
            if not ia_ligada(cfg):
                return self._json(400, {"erro": IA_DESLIGADA})
            if not cfg.get("cep"):
                return self._json(400, {"erro": "Salve o CEP em Mais antes de buscar."})
            BUSCA["rodando"] = True
        threading.Thread(target=alvo, args=args, daemon=True).start()
        self._json(202, {"ok": True})


def main():
    os.makedirs(DATA, exist_ok=True)
    log("chave do Home Assistant: " + ("encontrada" if token_ha() else "AUSENTE (a busca e a lista do HA não vão funcionar)"))
    threading.Thread(target=laco_sincronizacao, daemon=True).start()
    servidor = ThreadingHTTPServer(("0.0.0.0", PORT), Painel)
    log(f"painel no ar na porta {PORT}; dados em {DATA}")
    servidor.serve_forever()


if __name__ == "__main__":
    main()
