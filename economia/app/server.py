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
- GET  /api/integracoes   Shopee Afiliados: App ID e se a senha está guardada (a senha nunca sai daqui)
- PUT  /api/integracoes   {"shopee": {"app_id", "secret"}}, {"google": {"key"}}, {"instagram": {"token"}} guardam em segredos.json; null apaga
- POST /api/integracoes/testar   {"servico": "shopee" | "google" | "instagram" | "brave" | "ml"} faz uma consulta de teste
- POST /api/integracoes/ml/conectar   {"codigo"}: o endereço que abriu depois de autorizar no Mercado Livre (ou só o code=TG-…)
- GET  /api/folhetos   lojas com folheto lido no Kimbino ou no Seus Folhetos e como foi a última leitura
- GET  /api/lojas-mapa   lojas do raio pelo mapa (OpenStreetMap e, com chave, Google Places)
- POST /api/lojas-mapa/atualizar   {"raio_km", "categorias"}: lê o mapa agora, registra as lojas e começa o teste de preço de cada uma
- GET  /api/lojas-mapa/teste   andamento do teste de preço das lojas
- POST /api/ler-encarte   {"imagens": [...], "loja", "categoria"}: a IA lê o encarte ou o print de preços e junta ao resultado
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
import gzip
import hashlib
import html as html_mod
import http.cookiejar
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
SEGREDOS = os.path.join(DATA, "segredos.json")  # chaves das integrações: não vão para o painel, para o HA nem para as versões
FOLHETOS = os.path.join(DATA, "folhetos.json")  # folhetos já lidos, guardados até vencer
SHOPEE_API = os.environ.get("OFERTAS_SHOPEE_API", "https://open-api.affiliate.shopee.com.br/graphql")
FOLHETOS_TESTE = os.environ.get("OFERTAS_FOLHETOS_TESTE")  # só para testes: um servidor falso no lugar dos sites de encartes
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
MKT_SITES = {"ifood": "https://www.ifood.com.br", "rappi": "https://www.rappi.com.br", "mercadolivre": "https://www.mercadolivre.com.br",
             "amazon": "https://www.amazon.com.br", "shopee": "https://shopee.com.br", "magalu": "https://www.magazineluiza.com.br",
             "americanas": "https://www.americanas.com.br", "casasbahia": "https://www.casasbahia.com.br"}
ASSINATURAS = {"prime": "Amazon Prime", "melimais": "Meli+", "clubeifood": "Clube iFood"}
TAGS = {"bebe", "pet", "gato", "cachorro", "alcool", "medicamento", "maquiagem", "geriatrico", "skincare", "suplementos",
        "cafe", "bucal", "limpeza", "carnes", "alimentos", "higiene", "lactose", "gluten", "acucar"}
FONTES = {"Site", "App", "Encarte", "Clube", "Instagram", "WhatsApp", "Tiendeo", "Mapa"}

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


def frete_item(v):
    """Frete de um preço online: número, ou "carrinho" quando a loja só mostra a taxa no carrinho. None: sem frete."""
    if isinstance(v, str) and norm(v) in ("carrinho", "no carrinho", "a ver", "a confirmar", "frete no carrinho"):
        return "carrinho"
    return frete_ok(v)


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
OPCOES_PADRAO = {"itens_sem_preco": True, "encartes_auto": True, "lojas_diretas": True, "folhetos": True}


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


def entrega_ligada(cfg):
    return (cfg.get("online") or {}).get("mercados_entrega") is not False


def mkts_online(cfg):
    """Marketplaces que a IA procura (a Shopee sai quando vem pela API)."""
    ids = (cfg.get("online") or {}).get("marketplaces") or ["mercadolivre", "amazon"]
    if shopee_pronta():
        ids = [m for m in ids if m != "shopee"]
    return [MARKETPLACES.get(m, m) for m in ids]


def lojas_perto(cfg):
    """Lojas físicas do raio que a última busca achou, para a parte online não repetir."""
    of = ler_json(OFERTAS, {}) or {}
    try:
        raio = float(cfg.get("raio_km") or 2)
    except (TypeError, ValueError):
        raio = 2.0
    out = []
    for c in of.get("categorias") or []:
        if not isinstance(c, dict) or c.get("id") == "online":
            continue
        nomes = {r.get("id"): r.get("nome") for r in c.get("redes") or [] if isinstance(r, dict)}
        for l in c.get("lojas") or []:
            d = l.get("distancia_km") if isinstance(l, dict) else None
            if isinstance(d, (int, float)) and d <= raio and nomes.get(l.get("rede")):
                out.append(nomes[l["rede"]])
    return sorted(set(out))[:20]


def lojas_perto_cat(cfg):
    """{nome normalizado: categoria} de todas as lojas físicas do raio, com distância (sem o limite de 20 do texto para a IA)."""
    of = ler_json(OFERTAS, {}) or {}
    try:
        raio = float(cfg.get("raio_km") or 2)
    except (TypeError, ValueError):
        raio = 2.0
    out = {}
    for c in of.get("categorias") or []:
        if not isinstance(c, dict) or c.get("id") in (None, "online"):
            continue
        nomes = {r.get("id"): r.get("nome") for r in c.get("redes") or [] if isinstance(r, dict)}
        for l in c.get("lojas") or []:
            d = l.get("distancia_km") if isinstance(l, dict) else None
            if isinstance(d, (int, float)) and d <= raio and nomes.get(l.get("rede")):
                out.setdefault(norm(nomes[l["rede"]]), c["id"])
    return out  # loja sem localização (cadastrada à mão e não achada no mapa) conta como online


def categoria_da_loja(nome, perto):
    """Loja que está entre as do bairro fica na categoria dela (mesmo que antes tenha sido vista só como "mercado que
    entrega"); a que não está é online, porque entrega."""
    k = norm(nome)
    return perto.get(k) or next((c for n, c in perto.items() if mesma_loja(n, nome)), None) or "online"


def entrega_txt(cfg):
    if not entrega_ligada(cfg):
        return ""
    tipos = [CATEGORIAS[c]["o_que"].split(",")[0] for c in (cfg.get("categorias") or list(CATEGORIAS)) if c in CATEGORIAS and c != "online"]
    perto = lojas_perto(cfg)
    return (f"Mercados que entregam: procure também {', '.join(tipos) or 'supermercados'} da cidade e da região, inclusive fora do raio de "
            f"{cfg.get('raio_km') or 2} km, que vendem pelo site ou app próprio com entrega neste CEP (redes regionais com loja online). "
            "Em \"rede\", só o nome da loja, sem \"online\" ou \"delivery\". \"frete\" é a taxa de entrega para este CEP; se o site só mostra "
            "a taxa no carrinho, use \"frete\": \"carrinho\" e escreva em \"obs\" a regra que achar (por exemplo \"frete grátis acima de R$ 550\"). "
            "\"prazo_dias\" é 0 para entrega no mesmo dia."
            + (f" Não precisa trazer estas lojas, que ficam perto e já são buscadas: {', '.join(perto)}." if perto else ""))


def ja_tenho_txt(cfg, cat_id):
    ja = (cfg.get("_ja_tenho") or {}).get(cat_id) or []
    return (f"Os preços da lista destas lojas já vieram direto do site delas: {', '.join(ja)}. "
            "Não traga preços da lista dessas lojas; procure as outras.") if ja else ""


PAGINA_PRODUTO = ("Na Amazon, no Mercado Livre e nos outros marketplaces, use o preço da página do produto (o do botão de comprar), "
                  "não o do Google Shopping, que costuma estar desatualizado.")


def instrucoes_online(cfg):
    casa, excluir, restr, interesses = descreve_casa(cfg)
    on = cfg.get("online") or {}
    mkts = mkts_online(cfg)
    assin = [ASSINATURAS.get(a, a) for a in (on.get("assinaturas") or [])]
    lista = itens_prompt(cfg)
    return f"""Encontre preços válidos hoje ({hoje_br()}) {('em ' + ', '.join(mkts)) if mkts else 'em lojas online'} para entrega no CEP {cfg.get('cep')}, no Brasil.

Use a busca na web agora. Use só o que encontrar nas páginas: não invente produtos, preços, fretes nem prazos. Se não conseguir usar a busca na web, responda apenas {{"erro": "sem_busca"}}.

Assinaturas do morador: {', '.join(assin) or 'nenhuma'}. Quando a assinatura der frete grátis no item, use frete 0.
{APPS_TXT if any(m in (on.get("marketplaces") or []) for m in ("ifood", "rappi")) else ""}
{entrega_txt(cfg)}
{ja_tenho_txt(cfg, "online")}
Casa: {casa}.
Não traga: {', '.join(excluir) or 'nada a excluir'}.
Restrições: {', '.join(restr) or 'nenhuma'}. Interesses, que devem vir primeiro: {', '.join(interesses) or 'nenhum'}.
Lista de compras: {'; '.join(lista) or 'vazia'}.
{TAMANHOS_TXT} Em "tamanhos", informe também o frete e o prazo de cada opção.

Regras: em "fonte", use o link da página do produto. {PAGINA_PRODUTO} Só lojas oficiais ou vendedores bem avaliados. Marque "importado": true quando o envio for internacional. Não inclua remédios que exigem receita. Informe frete e prazo de entrega para este CEP. Em kits, informe "unidades". Até 15 ofertas, priorizando os itens da lista e os interesses.

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
    socios = set(cfg.get("clubes") or [])
    if socios:  # clube marcado em Mais › Lojas: a IA procura o preço de membro dessas lojas
        of = ler_json(OFERTAS, {}) or {}
        nomes_c = [r.get("nome") for c in of.get("categorias") or [] if isinstance(c, dict) and c.get("id") == cat_id
                   for r in c.get("redes") or [] if isinstance(r, dict) and r.get("id") in socios and r.get("nome")]
        if nomes_c:
            extra += f' O morador é do clube de {", ".join(nomes_c[:8])}: traga o "preco_clube" dessas lojas sempre que a loja mostrar.'
    return f"""Encontre ofertas e cupons válidos hoje ({hoje_br()}) de {cat['o_que']} perto do CEP {cfg.get('cep')}, num raio de {cfg.get('raio_km') or 2} km, no Brasil.

Use a busca na web agora. Use só o que encontrar nas páginas: não invente lojas, preços nem cupons. Se não conseguir usar a busca na web, responda apenas {{"erro": "sem_busca"}}.

Casa: {casa}.
Não traga: {', '.join(excluir) or 'nada a excluir'}.
Restrições: {', '.join(restr) or 'nenhuma'}. Interesses, que devem vir primeiro: {', '.join(interesses) or 'nenhum'}.
Lista de compras (procure o preço atual de cada item nestas lojas): {'; '.join(lista) or 'vazia'}.
{TAMANHOS_TXT}
Lojas para ignorar: {', '.join(lojas.get('ignorar') or []) or 'nenhuma'}. Lojas para incluir mesmo mais longe: {', '.join(lojas.get('manter') or []) or 'nenhuma'}. Lojas indicadas pelo morador: {', '.join(adicionadas) or 'nenhuma'}.
{ja_tenho_txt(cfg, cat_id)}
{mapa_txt(cfg, cat_id)}

Responda somente com um objeto JSON, sem texto antes ou depois, neste formato:
{{
  "lojas": [{{"rede": "nome da rede ou da loja", "endereco": "rua e número", "distancia_km": 1.2, "site": "URL da página de ofertas ou do site da loja, ou null", "horario": "Aberta até 22h", "fontes": ["Site", "App", "Encarte", "Clube", "Instagram", "WhatsApp", "Tiendeo"]}}],
  "cupons": [{{"rede": "...", "codigo": "CODIGO", "valor": 20, "beneficio": "R$ 20 de desconto", "condicao": "Pedidos acima de R$ 200", "valido_ate": "AAAA-MM-DD ou null", "oficial": true, "fonte": "URL"}}],
  "ofertas": [{{"rede": "...", "produto": "Nome · tamanho", "preco_normal": 10.0, "preco_oferta": 8.0, "tipo": "promo", "unidade": null, "tamanho": {{"quantidade": 500, "unidade": "g"}}, "condicao": null, "tags": ["alimentos"], "fonte": "URL"}}],
  "lista": [{{"item": 1, "produto": "texto exato do item da lista", "base": {{"quantidade": 1, "unidade": "L", "rotulo": null}}, "precos": [{{"rede": "...", "preco": 9.9, "preco_clube": 8.9, "fonte": "URL"}}], "tamanhos": [{{"rede": "...", "embalagem": "Galão 5 L", "quantidade": 5, "unidade": "L", "preco": 39.9, "fonte": "URL"}}]}}]
}}

Regras: em "lojas", inclua também mercadinhos e lojas independentes do raio, mesmo sem preços encontrados, com o site ou a página de ofertas quando houver. Até 15 ofertas, priorizando os interesses e os maiores descontos. Nos preços da lista, "preco" é o preço para todo mundo; se a loja tiver preço de clube (cadastro por CPF ou app), informe também "preco_clube", senão null. "tipo" é "promo", "clube" (preço para membros) ou "atacado" (preço por quantidade). "oficial" é true só se o cupom estiver no site ou app da própria loja. Etiquetas permitidas em "tags": {', '.join(sorted(TAGS))}.{extra}"""


def e_marketplace(nome):
    n = norm(nome)
    return any(norm(m) in n for m in list(MARKETPLACES.values()) + ["magazine luiza", "aliexpress", "temu", "shein", "submarino"])


def mkt_id(nome):
    """"Mercado Livre" → "mercadolivre"; "Magazine Luiza" → "magalu"; None se não for um dos marketplaces do app."""
    n = norm(nome)
    if "magazine luiza" in n:
        return "magalu"
    return next((k for k, v in MARKETPLACES.items() if norm(v) in n), None)


def normalizar(cat_id, bruto, cfg):
    if not isinstance(bruto, dict):
        raise ErroBusca("A IA respondeu fora do formato esperado.")
    if bruto.get("erro") == "sem_busca":
        raise ErroBusca(SEM_BUSCA)
    pre = cat_id[:4] + "-"
    redes = {}
    visto = {"em": agora(), "via": bruto.get("_via") if bruto.get("_via") in ("site", "api", "encarte") else "web"}

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
            frete = frete_item(o.get("frete"))
            if frete is None or item.get("receita") == "tarja":
                ids.discard(oid)
                continue
            item["frete"] = None if frete == "carrinho" else frete
            if frete == "carrinho":
                item["frete_carrinho"] = True
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
        frete = frete_item(p.get("frete"))
        if frete is None:
            descarta("preço online sem frete")
            return None, None
        valor = {"preco": preco, "frete": None, "carrinho": True} if frete == "carrinho" else {"preco": preco, "frete": frete}
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
        ent = lista.setdefault(original, {"precos": {}, "base": None, "tamanhos": [], "links": {}, "vistos": {}})
        for p in it.get("precos") or []:
            if isinstance(p, dict) and not p.get("rede") and it.get("rede"):
                p = dict(p, rede=it["rede"])
            rid, valor = valor_lista(p)
            if rid:
                ent["precos"][rid] = valor
                ent["vistos"][rid] = visto
                if fonte_ok(p.get("fonte")):
                    ent["links"][rid] = fonte_ok(p.get("fonte"))
        for x in it.get("similares") or []:  # mais em conta na mesma seção da loja (busca direta)
            m, preco, nome_s = (medida(x.get("quantidade"), x.get("unidade")), numero(x.get("preco")), texto(x.get("nome"), 80)) if isinstance(x, dict) else (None, None, None)
            rid = rede_id(x.get("rede")) if m and preco and nome_s else None
            if rid:
                ent.setdefault("similares", []).append(dict({"rede": rid, "nome": nome_s, "preco": preco, "quantidade": m[0], "unidade": m[1]},
                                                            **({"fonte": fonte_ok(x.get("fonte"))} if fonte_ok(x.get("fonte")) else {})))
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
                ent["vistos"].setdefault(rid, visto)
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
                tam.update({k: valor[k] for k in ("preco", "frete", "prazo_dias", "carrinho") if k in valor})
            else:
                tam["preco"] = valor
            if fonte_ok(t.get("fonte")):
                tam["fonte"] = fonte_ok(t.get("fonte"))
            ent["tamanhos"].append(tam)
    lista = {k: v for k, v in lista.items() if v["precos"] or v["tamanhos"]}

    # só as redes que ficaram com loja, cupom, oferta ou preço; cada uma precisa de uma loja
    usadas = set(lojas) | {c["rede"] for c in cupons} | {o["rede"] for o in ofertas}
    usadas |= {r for v in lista.values() for r in list(v["precos"]) + [t["rede"] for t in v["tamanhos"]] + [x["rede"] for x in v.get("similares") or []]}
    redes = {k: v for k, v in redes.items() if k in usadas}
    online = cat_id == "online"
    for rid in redes:
        lojas.setdefault(rid, {"rede": rid, "distancia_km": None, "horario": "Entrega no seu CEP" if online else "",
                               "endereco": None, "fontes": ["Site", "App"] if online else ["Site"]})
        if online and not e_marketplace(redes[rid]):
            lojas[rid]["regional"] = True  # mercado da região que entrega, separado dos marketplaces

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
        # busca pelo site: o que foi procurado em quais lojas (o preço antigo dessas lojas para esses itens é trocado pelo novo)
        **({"_buscados": [norm(nome_item(i)) for i in (cfg.get("lista") or []) if nome_item(i)], "_redes_buscadas": sorted(redes)}
           if bruto.get("_via") == "site" else {}),
    }, lista


# ---------- encarte do site da loja ----------
URL_ATTR_RE = re.compile(r"""(?:src|data-src|data-original|href|content|srcset)\s*=\s*["']([^"']+)["']""", re.I)
RUIDO_IMG = ("logo", "icon", "favicon", "sprite", "avatar", "whatsapp", "facebook", "instagram", "pixel", "loading")
NAVEGADOR = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36"


ACEITA = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"


def baixar(url, limite, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": NAVEGADOR, "Accept": ACEITA, "Accept-Language": "pt-BR,pt;q=0.9"})
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
    de_onde = f'do site da loja "{loja["nome"]}" ({loja["site"]})' if loja.get("site") else \
        f'da loja "{loja["nome"]}": fotos ou prints do encarte, do app ou da gôndola, mandados pelo morador'
    return f"""Você recebe {fonte} {de_onde}. Hoje é {hoje_br()}.
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
    log(f"encarte de {loja['nome']}: {len(dados)} arquivo(s)")
    val = data_ok((r or {}).get("validade")) if isinstance(r, dict) else None
    if val and val < hoje_br():
        raise ErroBusca(f"o encarte do site é antigo: venceu em {datetime.fromisoformat(val).strftime('%d/%m/%Y')}")
    return normalizar(loja["categoria"], bruto_encarte(loja, r), cfg)


def bruto_encarte(loja, r):
    """A resposta da IA sobre um encarte no formato da busca (lojas, ofertas e preços da lista)."""
    r = r if isinstance(r, dict) else {}
    nome, url, val = loja["nome"], loja.get("site"), data_ok(r.get("validade"))
    marca_rede = lambda x: dict(x, rede=nome, fonte=url)  # noqa: E731
    bruto = {
        "_via": "encarte",
        "lojas": [{"rede": nome, "endereco": None, "distancia_km": None, "fontes": ["Site", "Encarte"] if url else ["Encarte"]}],
        "cupons": [],
        "ofertas": [dict(o, rede=nome, preco_oferta=o.get("preco"), fonte=url, encarte=True, valido_ate=val)
                    for o in r.get("ofertas") or [] if isinstance(o, dict)],
        "lista": [dict(it, precos=[marca_rede(x) for x in it.get("precos") or [] if isinstance(x, dict)],
                       tamanhos=[marca_rede(x) for x in it.get("tamanhos") or [] if isinstance(x, dict)])
                  for it in r.get("lista") or [] if isinstance(it, dict)],
    }
    return bruto


def juntar_categoria(dest, cat):
    """Junta o resultado de um encarte à categoria que veio da busca."""
    ids_redes = {r["id"] for r in dest.get("redes") or []}
    dest.setdefault("redes", []).extend(r for r in cat["redes"] if r["id"] not in ids_redes)
    lojas = {l["rede"]: l for l in dest.get("lojas") or []}
    for l in cat["lojas"]:
        if l["rede"] in lojas:
            alvo = lojas[l["rede"]]
            alvo["fontes"] = sorted(set(alvo.get("fontes") or []) | set(l["fontes"]))
            for k in ("folheto", "folheto_ate", "instagram", "instagram_ate"):
                if l.get(k):
                    alvo[k] = l[k]
        else:
            dest.setdefault("lojas", []).append(l)
    ids = {o["id"] for o in dest.get("ofertas") or []}
    dest.setdefault("ofertas", []).extend(o for o in cat["ofertas"] if o["id"] not in ids)


def juntar_item(dest, ent):
    """Junta o que uma categoria achou para um item da lista ao que as outras já acharam."""
    if ent.get("similares"):
        dest.setdefault("similares", []).extend(ent["similares"])
    b, nb = dest.get("base"), ent.get("base")
    links, dlinks = ent.get("links") or {}, dest.setdefault("links", {})
    vistos, dvistos = ent.get("vistos") or {}, dest.setdefault("vistos", {})
    if not b and nb:
        dest["base"] = b = nb
    if not (b and nb) or (nb["unidade"] == b["unidade"] and mesmo_tamanho(nb["quantidade"], b["quantidade"])):
        dest["precos"].update(ent["precos"])
        dlinks.update(links)
        dvistos.update(vistos)
        if b and nb:
            dest["tamanhos"] += ent["tamanhos"]
        return
    if nb["unidade"] != b["unidade"]:  # medidas diferentes não dá para comparar
        dest["precos"].update(ent["precos"])
        dlinks.update(links)
        dvistos.update(vistos)
        return
    # esta categoria usou outro tamanho como base: os preços dela viram tamanhos
    for rid, v in ent["precos"].items():
        t = {"rede": rid, "quantidade": nb["quantidade"]}
        if isinstance(v, dict):
            t.update({k: v[k] for k in ("preco", "frete", "prazo_dias", "carrinho") if k in v})
        else:
            t["preco"] = v
        if links.get(rid):
            t["fonte"] = links[rid]
        dest["tamanhos"].append(t)
    for t in ent["tamanhos"]:
        if mesmo_tamanho(t["quantidade"], b["quantidade"]):
            v = {k: t[k] for k in ("preco", "frete", "prazo_dias", "carrinho") if k in t}
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
        dest = {"precos": {}, "base": None, "tamanhos": [], "links": {}, "vistos": {}}
        if votos:
            un, q = max(votos, key=votos.get)
            dest["base"] = next(e["base"] for e in ents if e.get("base") and (e["base"]["unidade"], e["base"]["quantidade"]) == (un, q))
        for e in ents:
            juntar_item(dest, e)
        lista[prod] = dest
    return lista


def sem_repetir_tamanhos(tams):
    """O mesmo produto da mesma loja vinha uma vez por busca: fica o mais recente (o último)."""
    unicos = {}
    for t in tams:
        if isinstance(t, dict) and numero(t.get("preco")) and numero(t.get("quantidade")):
            k = (t.get("rede"), round(float(t["quantidade"]), 4), norm(t.get("obs") or t.get("nome") or ""))
            unicos.pop(k, None)
            unicos[k] = t
    return list(unicos.values())


def item_ofertas(prod, ent):
    out = {"produto": prod, "precos": ent["precos"]}
    links = {r: u for r, u in (ent.get("links") or {}).items() if r in ent["precos"]}
    if links:
        out["links"] = links
    vistos = {r: v for r, v in (ent.get("vistos") or {}).items() if r in ent["precos"]}
    if vistos:
        out["vistos"] = vistos
    if ent.get("base"):
        out["base"] = ent["base"]
        if ent["tamanhos"]:
            por_un = lambda t: (t["preco"] + (t.get("frete") or 0)) / t["quantidade"]  # noqa: E731
            out["tamanhos"] = sorted(sem_repetir_tamanhos(ent["tamanhos"]), key=por_un)[:12]
    if ent.get("similares"):
        unicos_s = {}
        for x in ent["similares"]:  # o mesmo produto da mesma loja: fica o mais recente
            if isinstance(x, dict) and numero(x.get("preco")) and numero(x.get("quantidade")):
                unicos_s.pop((x.get("rede"), norm(x.get("nome") or "")), None)
                unicos_s[(x.get("rede"), norm(x.get("nome") or ""))] = x
        out["similares"] = sorted(unicos_s.values(), key=lambda x: x["preco"] / x["quantidade"])[:6]
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
VAZIAS_BUSCA = {"de", "da", "do", "das", "dos", "para", "com", "em", "e", "a", "o", "p", "c", "sem", "tipo", "ou"}
UNIDADE_NOME = re.compile(r"(\d+(?:[.,]\d+)?)\s*(ml|l|lt|litros?|kg|g|gr|un|und|unid|unidades?|m|metros?)\b", re.I)


VTEX_ACHADAS = {}  # lojas cadastradas ou achadas pela busca com site VTEX que permite consulta automática
LOJAS_SITE = os.path.join(DATA, "lojas_site.json")
CAMINHOS_VTEX = ("/api/checkout/pub/regions", "/api/io/_v/api/intelligent-search/product_search/")


def todas_diretas():
    out = {k: dict(v, fixa=True) for k, v in LOJAS_DIRETAS.items()}
    for k, v in VTEX_ACHADAS.items():
        out.setdefault(k, v)
    return out


def nome_direta(nome):
    """Nome de uma loja com busca direta escrito do jeito dela (Giassi Supermercados → Giassi)."""
    n = norm(nome).replace(" ", "")
    for k, loja in todas_diretas().items():
        if n.startswith(k.replace("-", "")):
            return loja["nome"]
    return nome


def site_direta(chave):
    return VTEX_TESTE.rstrip("/") + "/" + chave if VTEX_TESTE else (todas_diretas().get(chave) or {}).get("site")


def origem_de(u):
    if VTEX_TESTE and u.startswith(VTEX_TESTE):  # nos testes cada loja é uma pasta do servidor falso
        return VTEX_TESTE.rstrip("/") + "/" + u[len(VTEX_TESTE):].strip("/").split("/")[0]
    sp = urllib.parse.urlsplit(u)
    return f"{sp.scheme}://{sp.netloc}".lower()


def robots_regras(txt):
    """As regras do robots.txt que valem para qualquer programa (User-agent: *)."""
    grupos, atual, ua_antes = [], None, False
    for linha in str(txt or "").splitlines():
        lin = linha.split("#", 1)[0].strip()
        if ":" not in lin:
            continue
        k, v = (x.strip() for x in lin.split(":", 1))
        k = k.lower()
        if k == "user-agent":
            if not ua_antes:
                atual = {"ua": [], "regras": []}
                grupos.append(atual)
            atual["ua"].append(v.lower())
            ua_antes = True
            continue
        ua_antes = False
        if k in ("allow", "disallow") and atual is not None:
            atual["regras"].append((k, v))
    return [r for g in grupos if "*" in g["ua"] for r in g["regras"]]


def robots_permite(regras, caminho):
    melhor = None
    for k, v in regras:
        if not v:
            continue
        padrao = "^" + re.escape(v).replace(r"\*", ".*").replace(r"\$", "$")
        if re.match(padrao, caminho) and (melhor is None or len(v) > melhor[0] or (len(v) == melhor[0] and k == "allow")):
            melhor = (len(v), k)
    return melhor is None or melhor[1] == "allow"


def testa_site(origem, cep):
    """O site é uma loja VTEX que permite consulta automática? Primeiro lê o robots.txt; só consulta se ele deixar."""
    res = {"vtex": False, "permite": False, "em": agora()}
    try:
        txt = pagina_txt(origem + "/robots.txt")
    except urllib.error.HTTPError as e:
        txt = "" if e.code == 404 else None
        if txt is None:
            res["erro"] = (f"recusou o acesso de programas (erro {e.code})" if e.code in (401, 403, 429)
                           else f"respondeu com erro {e.code}")
    except Exception as e:  # noqa: BLE001
        txt = None
        r = getattr(e, "reason", None) or e
        bruto = f"{type(r).__name__}: {r}"[:140]
        t = bruto.lower()
        res["detalhe"] = bruto
        if "timed out" in t or "timeout" in t:
            res["erro"] = "demorou demais para responder"
        elif any(x in t for x in ("remotedisconnected", "closed connection", "connection reset", "connectionreset",
                                  "connection aborted", "eof occurred", "unexpected_eof", "incompleteread")):
            res["erro"] = "fechou a conexão sem responder ao EconomIA. No navegador ele abre: é a proteção do site contra acesso de programas"
        elif "ssl" in t or "certificate" in t:
            res["erro"] = "teve erro de conexão segura"
        elif "name or service" in t or "getaddrinfo" in t or "nodename" in t:
            res["erro"] = "não foi encontrado"
        else:
            res["erro"] = f"não respondeu ({bruto[:80]})"
    if txt is None:
        res["em"] = (datetime.now(timezone.utc) - timedelta(days=6)).isoformat(timespec="seconds")  # sem resposta: tenta amanhã
        res["sem_resposta"] = True
        return res
    regras = robots_regras(txt)
    res["regras"] = regras[:80]
    res["sitemaps"] = [u for u in re.findall(r"(?im)^\s*sitemap:\s*(\S+)", txt) if url_ok(u)][:6]
    res["paginas"] = robots_permite(regras, "/")
    res["permite"] = all(robots_permite(regras, c) for c in CAMINHOS_VTEX)
    if res["permite"]:
        try:
            res["vtex"] = isinstance(http_json(origem + "/api/checkout/pub/regions?country=BRA&postalCode=" + re.sub(r"\D", "", str(cep or "")), timeout=10), list)
        except Exception:  # noqa: BLE001
            pass
    return res


SITES_REDES = {
    "raia": "https://www.drogaraia.com.br", "drogasil": "https://www.drogasil.com.br", "pague menos": "https://www.paguemenos.com.br",
    "nissei": "https://www.farmaciasnissei.com.br", "panvel": "https://www.panvel.com", "catarinense": "https://www.drogariacatarinense.com.br",
    "sao joao": "https://www.saojoaofarmacias.com.br", "cobasi": "https://www.cobasi.com.br", "petz": "https://www.petz.com.br",
    "bistek": "https://www.bistek.com.br", "fort": "https://www.fortatacadista.com.br", "atacadao": "https://www.atacadao.com.br",
    "giassi": "https://www.giassi.com.br", "angeloni": "https://super.angeloni.com.br",
    "farmasesi": "https://www.farmasesi.com.br", "sesi": "https://www.farmasesi.com.br",
}
# redes de farmácia cujo nome no mapa costuma vir com a filial depois ("FarmaSesi - Itoupava Norte", "Drogaria Catarinense Floresta")
SITES_COM_FILIAL = {"raia", "drogasil", "pague menos", "nissei", "panvel", "catarinense", "sao joao", "farmasesi", "sesi"}


def site_da_rede(nome, cidade=""):
    """Site de rede conhecida pelo nome ("Atacadão Joinville" → atacadao.com.br; "Atacadão Dia a Dia" não é a mesma rede)."""
    tira = set(norm(cidade or "").split())
    k = " ".join(w for w in chave_loja(nome).split() if w not in tira)
    if k in SITES_REDES:
        return SITES_REDES[k]
    return next((SITES_REDES[r] for r in SITES_COM_FILIAL if k.startswith(r + " ")), None)


def candidatos_site(cfg):
    """Sites das lojas cadastradas e das achadas pela última busca: {origem: (nome, categoria)}."""
    out = {}
    for a in ((cfg.get("lojas") or {}).get("adicionar") or []):
        if isinstance(a, dict) and url_ok(a.get("site")) and a.get("categoria") in ("mercados", "farmacias", "petshops") and texto(a.get("nome"), 60):
            out[origem_de(a["site"])] = (texto(a["nome"], 60).split(",")[0].strip(), a["categoria"])
    cidade = ((ler_json(FOLHETOS, {}) or {}).get("_cep") or {}).get("cidade") or ""
    if not cidade and cfg.get("cep"):
        try:
            cidade = cidade_do_cep(cfg.get("cep"), {})[0] or ""
        except Exception:  # noqa: BLE001
            cidade = ""
    for c in (ler_json(OFERTAS, {}) or {}).get("categorias") or []:
        if not isinstance(c, dict) or c.get("id") not in ("mercados", "farmacias", "petshops"):
            continue
        nomes = {r.get("id"): r.get("nome") for r in c.get("redes") or [] if isinstance(r, dict)}
        for l in c.get("lojas") or []:
            if not isinstance(l, dict) or not nomes.get(l.get("rede")) or "folheto" in l:
                continue
            site = l.get("site") if url_ok(l.get("site")) else site_da_rede(nomes[l["rede"]], cidade)
            if site:
                out.setdefault(origem_de(site), (nomes[l["rede"]], c["id"]))
    of = ler_json(OFERTAS, {}) or {}
    links = {}
    for i in of.get("lista") or []:
        for rid, u in ((i.get("links") or {}).items() if isinstance(i, dict) else []):
            links.setdefault(rid, u)
    for c in of.get("categorias") or []:
        if not isinstance(c, dict) or c.get("id") != "online":
            continue
        for o in c.get("ofertas") or []:
            if isinstance(o, dict) and o.get("fonte"):
                links.setdefault(o.get("rede"), o["fonte"])
        nomes = {r.get("id"): r.get("nome") for r in c.get("redes") or [] if isinstance(r, dict)}
        for l in c.get("lojas") or []:
            rid = l.get("rede") if isinstance(l, dict) else None
            if l.get("regional") and nomes.get(rid) and url_ok(links.get(rid)):
                out.setdefault(origem_de(links[rid]), (nomes[rid], "online"))
    fixas = {origem_de(v["site"]) for v in LOJAS_DIRETAS.values()} | {"https://www.kimbino.com.br", "https://seusfolhetos.com.br"}
    return {o: v for o, v in out.items() if o not in fixas}


def atualiza_diretas(cfg, max_novas=6):
    """Testa o site das lojas (uma vez por semana cada) e liga a busca direta nas que são VTEX e permitem consulta."""
    memo = ler_json(LOJAS_SITE, {}) or {}
    semana = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(timespec="seconds")
    novas = 0
    for o, (nome, cat) in candidatos_site(cfg).items():
        m = memo.get(o)
        if m and m.get("em", "") >= semana:
            m.update({"nome": nome, "categoria": cat})
            continue
        if novas >= max_novas:
            continue
        novas += 1
        memo[o] = dict(testa_site(o, cfg.get("cep")), nome=nome, categoria=cat)
        log(f"site de {nome}: " + (f"sem resposta ({memo[o].get('detalhe') or memo[o].get('erro')}), tento de novo amanhã" if memo[o].get("sem_resposta") else "busca direta ligada" if memo[o]["vtex"] else
                                   "não deixa programas usarem a busca do site" + (", mas deixa abrir as páginas de produto" if memo[o].get("paginas") else "")
                                   if not memo[o]["permite"] else "sem busca direta"))
    if novas:
        gravar_json(LOJAS_SITE, memo)
    VTEX_ACHADAS.clear()
    for o, m in memo.items():
        if m.get("vtex") and m.get("permite") and m.get("nome"):
            VTEX_ACHADAS[slug(m["nome"], 30)] = {"nome": m["nome"], "site": o, "categoria": m.get("categoria") or "mercados"}
    return memo


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


def alternativas(item):
    """"Coxinha da asa ou asinha": cada lado é um item e vale o que achar (o mais em conta ganha na comparação)."""
    partes = [x.strip(" ,;") for x in re.split(r"\s+ou\s+", str(item or ""), flags=re.I)]
    partes = [x for x in partes if palavras_busca(x)]
    return partes if len(partes) > 1 else [str(item or "")]


# ---------- casamento do item com o produto, pelo padrão de nome do varejo ----------
# Nome de produto no varejo: tipo + marca + variante + tamanho ("Álcool Araras Bactericida Eucalipto 1L"). O item da lista
# segue o mesmo padrão ("álcool perfumado"): o tipo (a primeira palavra) e a marca precisam estar no nome; cada outra
# palavra vale se estiver no nome ou nas categorias, ou se o nome tiver uma palavra que, nos produtos que as lojas já
# mostraram (catálogos, buscas), anda junto com ela ("perfumado" anda com "lavanda", "eucalipto"…). O vocabulário é
# aprendido sozinho e fica em vocabulario.json; o produto achado com certeza guarda o EAN (código de barras), que acha o
# mesmo produto em outra loja mesmo com outro nome.
VOCAB = os.path.join(DATA, "vocabulario.json")
CASADOS = os.path.join(DATA, "casados.json")
MAX_NOMES_VOCAB = 80000
_vocab = {"nomes": None}
_vocab_trava = threading.Lock()


def vocab():
    if _vocab["nomes"] is None:
        d = ler_json(VOCAB, {}) or {}
        _vocab.update(nomes=list(dict.fromkeys(d.get("nomes") or [])), marcas=set(d.get("marcas") or []), mudou=False, assoc={}, stats=None)
        _vocab["set"] = set(_vocab["nomes"])
    return _vocab


def aprende_nomes(nomes, marcas=()):
    """Guarda nomes de produto que as lojas mostraram (sem o tamanho) e as marcas."""
    v = vocab()
    with _vocab_trava:
        for n in nomes:
            t = " ".join(w for w in norm(re.sub(UNIDADE_NOME, " ", str(n or ""))).split() if not w.isdigit())
            if len(t.split()) >= 2 and t not in v["set"]:
                v["set"].add(t)
                v["nomes"].append(t)
                v["mudou"] = True
        for m in marcas:
            m = norm(m)
            if len(m) >= 2 and len(m.split()) == 1 and m not in v["marcas"]:
                v["marcas"].add(m)
                v["mudou"] = True
        if len(v["nomes"]) > MAX_NOMES_VOCAB:
            corte = len(v["nomes"]) - MAX_NOMES_VOCAB
            for x in v["nomes"][:corte]:
                v["set"].discard(x)
            v["nomes"] = v["nomes"][corte:]


def grava_vocab():
    v = vocab()
    with _vocab_trava:
        if v["mudou"]:
            gravar_json(VOCAB, {"nomes": v["nomes"], "marcas": sorted(v["marcas"]), "em": agora()})
            v.update(mudou=False, assoc={}, stats=None)  # as associações são refeitas com o vocabulário novo
    grava_ml()


def stats_vocab():
    """Em quantos nomes cada palavra aparece (df) e quantas vezes abre o nome (primeira)."""
    v = vocab()
    if v["stats"] is None:
        df, primeira = {}, {}
        for n in v["nomes"]:
            ws = n.split()
            primeira[ws[0]] = primeira.get(ws[0], 0) + 1
            for t in set(ws):
                df[t] = df.get(t, 0) + 1
        v["stats"] = (df, primeira)
    return v["stats"]


def associadas(w):
    """Palavras que, nos nomes de produto vistos, aparecem bem mais junto de w do que no resto (variantes, não tipos nem marcas)."""
    v = vocab()
    if w in v["assoc"]:
        return v["assoc"][w]
    nomes, out = v["nomes"], set()
    if len(nomes) >= 200:
        df, primeira = stats_vocab()
        raiz, k, com = (w[:-1] if len(w) >= 5 else w), 0, {}
        for n in nomes:
            u = set(n.split())
            if w in u or (len(w) >= 5 and any(x.startswith(raiz) and len(x) <= len(w) + 1 for x in u)):
                k += 1
                for t in u:
                    com[t] = com.get(t, 0) + 1
        total = len(nomes)
        if k >= 3:
            for t, c in com.items():
                if (c < 3 or t.startswith(raiz) or t in VAZIAS_BUSCA or t in v["marcas"] or len(t) < 4
                        or primeira.get(t, 0) > 0.3 * df[t] or df[t] > 0.05 * total):
                    continue  # tipo de produto (limpador, papel), marca ou palavra comum demais
                if (c / k) / (df[t] / total) >= 4:
                    out.add(t)
    v["assoc"][w] = out
    return out


# vocabulário inicial do varejo (o aprendido soma a ele): "perfumado" é o nome da fragrância
FRAGRANCIAS = {"perfumado", "perfumada", "perfumados", "perfumadas", "aromatizado", "aromatizada", "fragrancia", "lavanda", "eucalipto",
               "eucaliptus", "floral", "flores", "citrus", "citrico", "citrica", "campestre", "talco", "pinho", "laranja", "limao", "alecrim",
               "menta", "hortela", "baunilha", "jasmim", "rosas", "lirio", "violeta", "frutas", "tropical", "coco", "algodao", "brisa",
               "marine", "primavera", "cereja", "bouquet", "citronela", "capim", "maca", "morango", "erva", "carinho", "aconchego"}
EQUIVALENTES = {w: FRAGRANCIAS for w in ("perfumado", "perfumada", "perfumados", "perfumadas", "aromatizado", "aromatizada",
                                         "cheiroso", "cheirosa")}


def palavra_bate(w, pp):
    if w in EQUIVALENTES:
        return any(x in EQUIVALENTES[w] for x in pp)
    return any(x == w or (len(w) >= 4 and (x.startswith(w) or (len(x) >= 4 and w.startswith(x)))) for x in pp)


def combina(item, produto):
    """O produto do site é o item da lista? O tipo (primeira palavra) precisa estar no nome ou nas categorias
    ("JIMO Secante..." está em Limpeza › Lava-Louças); das outras palavras, todas (até 3) ou 3 de cada 4."""
    return casa_lista(item, [produto], traduzir=False)[0]


# palavras que mudam o que a pessoa pode comer ou usar: nunca ficam de fora num casamento "parecido"
RESTRICOES = {"lactose", "gluten", "acucar", "diet", "light", "zero", "integral", "desnatado", "semidesnatado", "vegano", "vegana",
              "organico", "organica", "sodio", "sal", "infantil", "bebe", "kids", "adulto", "filhote", "senior", "castrado", "castrados",
              "gato", "gatos", "cachorro", "cachorros", "cao", "caes", "generico", "referencia"}


def eh_tipo(w):
    """A palavra costuma abrir o nome do produto (é um tipo: "pão", "limpador", "álcool")? Pelo vocabulário aprendido."""
    v = vocab()
    if not v["nomes"] or len(v["nomes"]) < 200:
        return False
    df, primeira = stats_vocab()
    return primeira.get(w, 0) >= 5 and primeira[w] >= 0.5 * df.get(w, 1)


def cabeca_bate(cab, pp, itens_do_tipo=None):
    """O tipo do item está entre as 3 primeiras palavras do nome do produto (a marca pode vir antes: "JIMO Secante"),
    sem outro tipo antes dele: "Limpador … Lavanda e Álcool" não é álcool e "Pão … Leite" não é leite."""
    ws = [w for w in pp if len(w) >= 2 and not any(ch.isdigit() for ch in w) and w not in VAZIAS_BUSCA]
    if not eh_tipo(cab):  # o item começa pela marca ou por outra coisa ("Churu atum"): basta estar no começo do nome
        if ws and eh_tipo(ws[0]) and not palavra_bate(cab, [ws[0]]) and cab not in vocab()["marcas"] and ws[0] not in (itens_do_tipo or ()):
            return False  # o produto é de outro tipo, que o item nem cita
        return any(palavra_bate(cab, [w]) for w in ws[:4])
    for w in ws[:3]:
        if palavra_bate(cab, [w]):
            return True
        if eh_tipo(w):
            return False
    return False


def casa_lista(item, textos, traduzir=True):
    """combina() para os produtos de uma busca de uma vez. Palavra do item que nenhum produto do mesmo tipo usa
    ("perfumado" entre os "álcool …") é escrita de outro jeito pela loja: vale uma palavra que anda junto com ela nos
    produtos vistos ("eucalipto", "lavanda"). Palavra que a loja usa ("integral" entre os "leite …") tem de estar no nome."""
    alts = alternativas(item)
    if len(alts) > 1:  # "coxinha da asa ou asinha": casa com qualquer um dos lados
        res = [casa_lista(a, textos, traduzir) for a in alts]
        out = [True if True in v else "parecido" if "parecido" in v else False for v in zip(*res)]
        return [o is True for o in out] if True in out else out
    pi = palavras_busca(item)
    if not pi:
        return [False] * len(textos)
    toks = [norm(t).split() for t in textos]
    cab = [cabeca_bate(pi[0], pp, set(pi)) for pp in toks]
    marcas = vocab()["marcas"]
    traduz = {w for w in pi[1:] if w not in marcas and not any(c and palavra_bate(w, pp) for c, pp in zip(cab, toks))} if traduzir else set()
    out = []
    for c, pp in zip(cab, toks):
        if not c:
            out.append(False)
            continue
        u, ok, faltam = set(pp) - set(pi), 1, []  # a palavra associada tem de ser outra, não uma do próprio item
        for w in pi[1:]:
            if palavra_bate(w, pp) or (w in traduz and associadas(w) & u):
                ok += 1
            else:
                faltam.append(w)
        # com 4 palavras ou mais, pode faltar 1 em 4, mas nunca a que vem logo depois do tipo ("carne moída", "papel higiênico")
        cheio = ok == len(pi) if len(pi) <= 3 else (ok >= 0.75 * len(pi) and pi[1] not in faltam)
        # parecido: só falta uma palavra, que nenhum produto do mesmo tipo usa nesta loja ("de cozinha" no álcool) e que
        # não é restrição ("sem lactose", "zero açúcar"). Vale só se nenhum produto casar inteiro.
        parecido = (not cheio and len(pi) >= 3 and len(faltam) == 1 and faltam[0] in traduz and faltam[0] not in RESTRICOES)
        out.append(True if cheio else "parecido" if parecido else False)
    if any(o is True for o in out):
        out = [o is True for o in out]
    return out


def termo_nucleo(item):
    """Tipo + marca do item, para buscar de novo quando o item inteiro não acha nada ("álcool perfumado" → "alcool"),
    ou None se já for só isso."""
    pi = palavras_busca(item)
    if len(pi) < 2:
        return None
    marcas = vocab()["marcas"]
    nucleo = [pi[0]] + [w for w in pi[1:] if w in marcas]
    if len(nucleo) == len(pi):
        return None
    originais = [w for w in re.split(r"[\s,;/]+", str(item)) if w]  # com acento, como a pessoa escreveu ("álcool")
    return " ".join(next((o for o in originais if norm(o) == w), w) for w in nucleo)


def casados():
    return ler_json(CASADOS, {}) or {}


def guarda_casados(item, eans, loja=None, secoes=()):
    """Guarda o código de barras dos produtos casados com certeza e, por loja, a seção onde eles ficam."""
    eans = [e for e in eans if re.fullmatch(r"\d{8,14}", str(e or ""))]
    secoes = [s for s in secoes if s]
    if not eans and not (loja and secoes):
        return
    c = casados()
    k = norm(item)
    atual = c.get(k) or {}
    novo = list(dict.fromkeys((atual.get("eans") or []) + eans))[-20:]
    secs = dict(atual.get("secoes") or {})
    if loja and secoes:
        secs[loja] = list(dict.fromkeys((secs.get(loja) or []) + secoes))[-4:]
    if novo != (atual.get("eans") or []) or secs != (atual.get("secoes") or {}):
        c[k] = dict({"eans": novo, "em": agora()}, **({"secoes": secs} if secs else {}))
        gravar_json(CASADOS, c)


def secoes_do_item(item, loja, firmes):
    """As seções da loja onde o item fica: as dos produtos casados com certeza agora e as aprendidas antes."""
    secs = {c["secao"] for c in firmes if c.get("secao")}
    return secs | set((((casados().get(norm(item)) or {}).get("secoes") or {}).get(loja)) or [])


def secao_afim(item, sec):
    """A seção fala do item? ("carne moída bovina" e "Açougue › Bovinos": "bovin…"). Compara o começo das palavras,
    porque a seção vem no plural ou no masculino ("Carnes", "Bovinos")."""
    ws = [w for parte in sec.split("/") for w in parte.split() if len(w) >= 4]
    for a in alternativas(item):
        for w in palavras_busca(a):
            if len(w) >= 4 and any(x.startswith(w[:max(4, len(w) - 2)]) for x in ws):
                return True
    return False


def filtra_secao(item, loja, cand, eans):
    """Produto de outra seção da loja não é o item, mesmo com nome parecido: "Carne moída" fica em Açougue › Bovinos e
    o hambúrguer em Congelados. É o mesmo sinal que o app da loja usa. Sem seção conhecida, não filtra."""
    firmes = [c for c in cand if combina(item, c["nome"])]
    afins = {c["secao"] for c in firmes if c.get("secao") and secao_afim(item, c["secao"])}
    if afins:  # entre os casados com certeza, fica quem está numa seção que fala do item: a almôndega de "carne moída" em Congelados › Pratos sai
        antes = set(secoes_do_item(item, loja, [])) | afins
        fora = [c for c in firmes if c.get("secao") and not any(mesma_secao(c["secao"], s) for s in antes) and c.get("ean") not in eans]
        firmes = [c for c in firmes if c not in fora]
        cand = [c for c in cand if c not in fora]
        if fora:
            log(f"seção da loja: fora de '{item}' por estar em outra seção: " + "; ".join(f"{c['nome'][:40]} ({c['secao']})" for c in fora[:3]))
    secs = secoes_do_item(item, loja, firmes)
    if not secs:
        return cand, firmes
    ok = [c for c in cand if c in firmes or c.get("ean") in eans or not c.get("secao") or any(mesma_secao(c["secao"], s) for s in secs)]
    if len(ok) < len(cand):
        log(f"seção da loja: {len(cand) - len(ok)} produto(s) de outra seção fora de '{item}' ({', '.join(sorted({c['secao'] for c in cand if c not in ok})[:3])})")
    return ok, firmes


def similares_vtex(chave, regiao, item, cand, n=3):
    """Mais em conta na mesma seção da loja ("sobrecoxa" e "asa" para quem pediu "coxinha da asa"), comparando pelo
    preço do quilo (ou litro). Só com seção de 2 níveis ou mais: "Açougue" sozinho junta boi, porco e frango."""
    conta = {}
    for c in cand:
        if c.get("secao") and "/" in c["secao"]:
            conta[c["secao"]] = conta.get(c["secao"], 0) + 1
    if not conta:
        return []
    sec = max(conta, key=conta.get)
    unid = {}
    for c in cand:
        if c.get("tam"):
            unid[c["tam"][1]] = unid.get(c["tam"][1], 0) + 1
    if not unid:
        return []
    un = max(unid, key=unid.get)
    melhor = min(c["preco"] / c["tam"][0] for c in cand if c.get("tam") and c["tam"][1] == un)
    rotulo = next((c["secao_nome"] for c in cand if c.get("secao") == sec and c.get("secao_nome")), "")
    facetas = "/".join(f"category-{i}/{re.sub(r'[^a-z0-9]+', '-', parte).strip('-')}" for i, parte in enumerate(sec.split("/"), 1))
    achados = busca_vtex(chave, "", regiao, 40, facetas=facetas)
    if not any(p.get("secao", "").startswith(sec) for p in achados) and rotulo:  # a loja não abriu a seção pelo caminho: busca pelo nome dela
        achados = busca_vtex(chave, rotulo, regiao, 40)
    vistos, out = {c["link"] for c in cand}, {}
    for p in achados:
        if p["link"] in vistos or not p.get("tam") or p["tam"][1] != un or not p.get("secao"):
            continue
        if not (p["secao"] == sec or p["secao"].startswith(sec + "/")):
            continue
        if p["preco"] / p["tam"][0] < melhor * 0.98:
            out.setdefault(p["link"], p)
    return sorted(out.values(), key=lambda p: p["preco"] / p["tam"][0])[:n]


def quer_similares(cfg):
    return {norm(nome_item(i)) for i in (cfg.get("lista") or []) if isinstance(i, dict) and i.get("similares") and nome_item(i)}


# "com 12", "c/ 6", "cx com 4": quantas embalagens. "com 10% de desconto" e "com 20 off" não são pacote.
PACOTE_NOME = re.compile(r"(?:\bc/\s*|\bcom\s+|\bcx\.?\s*(?:com\s*)?|\bpack\s*|\bx\s*)(\d{1,2})(?![\d,.])(?!\s*(?:%|por\s*cento|(?:ml|l|lt|g|gr|kg|m|un|und|unid|unidades?|reais|off|de\s+desc\w*)\b))", re.I)


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


def secao_vtex(prod):
    """A seção onde a loja cadastrou o produto, do nível mais fundo: ("acougue/aves/frango", "Frango"), ou ("", "")."""
    cats = [str(c) for c in (prod.get("categories") or []) if str(c).strip("/ ")]
    if not cats:
        return "", ""
    fundo = [x.strip() for x in max(cats, key=lambda c: c.strip("/").count("/")).strip("/").split("/") if x.strip()]
    return "/".join(norm(x) for x in fundo), fundo[-1]


def mesma_secao(a, b):
    """Uma seção dentro da outra (Açougue ⊃ Açougue › Aves) conta como a mesma; seções irmãs não."""
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def busca_vtex(chave, termo, regiao, count=12, facetas=None):
    params = {"query": termo, "count": count, "locale": "pt-BR"}
    if regiao:
        params["regionId"] = regiao
    caminho = (facetas.strip("/") + "/") if facetas else ""
    d = http_json(site_direta(chave) + "/api/io/_v/api/intelligent-search/product_search/" + caminho + "?" + urllib.parse.urlencode(params)) or {}
    out = []
    for prod in d.get("products") or []:
        nome = str(prod.get("productName") or "").strip()
        if not nome or "+" in nome or norm(nome).startswith("kit "):
            continue
        busca_em = " ".join([nome, str(prod.get("brand") or "")] + [str(c) for c in (prod.get("categories") or [])][:4])
        aprende_nomes([nome], [prod.get("brand") or ""])
        for it in (prod.get("items") or [])[:1]:
            ofs = [x.get("commertialOffer") or {} for x in it.get("sellers") or []]
            ofs = [o for o in ofs if numero(o.get("Price")) and (o.get("AvailableQuantity") or 0) > 0]
            if not ofs:
                continue
            o = min(ofs, key=lambda x: numero(x.get("Price")))
            preco, de = numero(o.get("Price")), numero(o.get("ListPrice"))
            tam = tamanho_nome(nome)
            # produto vendido por peso ou volume: a VTEX dá o preço por kg (ou litro) e o unitMultiplier diz quanto vem
            # na embalagem ("Sobrecoxa 2,3 kg": R$ 14,98/kg × 2,3 = R$ 34,45 a bandeja)
            un, mult = str(it.get("measurementUnit") or "").strip().lower(), numero(it.get("unitMultiplier")) or 1
            if un in UNIDADES and UNIDADES[un][0] in ("kg", "L") and mult and abs(mult - 1) > 0.001:
                preco = round(preco * mult, 2)
                de = round(de * mult, 2) if de else de
                tam = medida(mult, un) or tam
            elif not tam and un in UNIDADES and UNIDADES[un][0] in ("kg", "L"):
                tam = medida(1, un)
            marca = texto(prod.get("brand"), 30) or ""
            curto = (marca + " " + fmt_base({"quantidade": tam[0], "unidade": tam[1]})) if marca and tam else nome[:60]
            sec, sec_nome = secao_vtex(prod)
            out.append({"nome": nome, "curto": curto, "busca_em": busca_em, "preco": preco, "de": de if de and de > preco + 0.004 else None, "tam": tam,
                        "ean": str(it.get("ean") or ""), "secao": sec, "secao_nome": sec_nome,
                        "link": str((todas_diretas().get(chave) or {}).get("site") or "") + str(prod.get("link") or "")})
    return out


def lojas_diretas_status(cfg):
    out = []
    memo = atualiza_diretas(cfg, 0)
    for k, loja in todas_diretas().items():
        try:
            reg, nome = regiao_direta(k, cfg.get("cep"))
            out.append({"id": k, "nome": loja["nome"], "atende": bool(reg), "loja": nome, "fixa": bool(loja.get("fixa"))})
        except Exception as e:  # noqa: BLE001
            out.append({"id": k, "nome": loja["nome"], "atende": None, "erro": str(e)[:120]})
    pag = sorted(m["nome"] for m in memo.values() if m.get("nome") and m.get("paginas") and not (m.get("vtex") and m.get("permite")))
    return out + [{"id": slug(n, 30), "nome": n, "atende": None, "paginas": True} for n in pag[:8]]


def busca_direta(cfg, itens=None, cats=("mercados",)):
    """Pergunta a cada loja com busca direta o preço de cada item da lista. Devolve [(categoria, parcial)]."""
    nomes = itens or nomes_da_lista(cfg)
    if not nomes or not cfg.get("cep"):
        return []
    perto = lojas_perto_cat(cfg)
    todas = {k: v for k, v in todas_diretas().items() if (v.get("categoria") or "mercados") in cats or not v.get("fixa")}
    achados, lojas, sims = {}, {}, {}  # categoria -> item -> loja -> [candidatos]; categoria -> lojas; similares do mesmo jeito
    com_sim = quer_similares(cfg)
    pode = set(cats) | ({"online"} if entrega_ligada(cfg) and "online" in (cfg.get("categorias") or list(CATEGORIAS)) else set())
    for k, loja in todas.items():
        cat_id = (loja.get("categoria") or "mercados") if loja.get("fixa") else categoria_da_loja(loja["nome"], perto)
        if cat_id not in pode:
            continue
        try:
            reg, unidade = regiao_direta(k, cfg.get("cep"))
        except Exception as e:  # noqa: BLE001
            log(f"busca direta {loja['nome']}: não consegui saber a loja do CEP ({e})")
            continue
        if not reg:
            log(f"busca direta {loja['nome']}: não atende o CEP {cfg.get('cep')}")
            continue
        BUSCA["etapa"] = "preços no site · " + loja["nome"]
        n = 0
        for nome in nomes:
            try:
                alts = alternativas(nome)  # "coxinha da asa ou asinha": busca cada lado
                res = unicos([c for a in alts for c in busca_vtex(k, a, reg)])
                cand = [c for c, ok in zip(res, casa_lista(nome, [c["busca_em"] for c in res])) if ok]
                nucleos = [t for t in (termo_nucleo(a) for a in alts) if t]
                if not cand and nucleos:  # "álcool perfumado": busca "álcool" e fica com os que combinam
                    res = unicos(res + [c for t in nucleos for c in busca_vtex(k, t, reg, 40)])
                    cand = [c for c, ok in zip(res, casa_lista(nome, [c["busca_em"] for c in res])) if ok]
                eans = set((casados().get(norm(nome)) or {}).get("eans") or [])
                cand += [c for c in res if c.get("ean") in eans and c not in cand]  # o mesmo produto achado antes, por código de barras
                cand, firmes = filtra_secao(nome, k, cand, eans)
                # só o casamento firme (nome ou vocabulário inicial) ensina o código de barras e a seção
                guarda_casados(nome, [c.get("ean") for c in firmes], k, [c.get("secao") for c in firmes])
                if cand and norm(nome) in com_sim:
                    s = similares_vtex(k, reg, nome, cand)
                    if s:
                        sims.setdefault(cat_id, {}).setdefault(nome, {})[k] = s
            except Exception as e:  # noqa: BLE001
                log(f"busca direta {loja['nome']} '{nome}': {e}")
                continue
            if cand:
                achados.setdefault(cat_id, {}).setdefault(nome, {})[k] = cand
                n += 1
        lojas.setdefault(cat_id, []).append({"rede": loja["nome"], "endereco": unidade or None, "distancia_km": None, "site": loja["site"], "fontes": ["Site"]})
        log(f"busca direta {loja['nome']}{' (' + unidade + ')' if unidade else ''}: {n} de {len(nomes)} item(ns) com preço")
    out = []
    cfg_itens = dict(cfg, lista=[{"produto": n} for n in nomes])
    for cat_id, ls in lojas.items():
        lista_bruta, ofertas = [], []
        for nome, por_loja in (achados.get(cat_id) or {}).items():
            s = {todas[k]["nome"]: v for k, v in ((sims.get(cat_id) or {}).get(nome) or {}).items()}
            ent, ofs = montar_item(nome, {todas[k]["nome"]: cands for k, cands in por_loja.items()}, similares=s)
            lista_bruta.append(ent)
            ofertas += ofs
        out.append(normalizar(cat_id, {"lojas": ls, "cupons": [], "ofertas": ofertas, "lista": lista_bruta, "_via": "site"}, cfg_itens))
    return out


def unicos(cands):
    """Os mesmos produtos de duas buscas (um lado e o outro do "ou"): cada link uma vez."""
    vistos, out = set(), []
    for c in cands:
        if c.get("link") not in vistos:
            vistos.add(c.get("link"))
            out.append(c)
    return out


def montar_item(nome, por_rede, frete=None, similares=None):
    """Os produtos achados para um item da lista, de uma ou mais lojas, no formato da busca: o preço no tamanho de
    sempre, os outros tamanhos e as promoções. frete="carrinho" para loja online que só mostra o frete no carrinho."""
    por_rede = {r: cs for r, cs in ((r, filtra_ml(nome, cs)) for r, cs in por_rede.items()) if cs}
    # tamanho de sempre: o do nome do item ou o mais comum entre os produtos achados
    base = tamanho_nome(nome)
    if not base:
        conta = {}
        for cands in por_rede.values():
            for c in cands:
                if c["tam"]:
                    conta[c["tam"]] = conta.get(c["tam"], 0) + 1
        base = max(conta, key=lambda t: (conta[t], -t[0])) if conta else None
    extra = {"frete": frete} if frete is not None else {}
    precos, tamanhos, ofertas = [], [], []
    for rede, cands in por_rede.items():
        iguais = [c for c in cands if c["tam"] and c["tam"][1] == base[1] and mesmo_tamanho(c["tam"][0], base[0])] if base else cands
        if iguais:
            c = min(iguais, key=lambda x: x["preco"])
            precos.append(dict({"rede": rede, "preco": c["preco"], "obs": c.get("curto") or c["nome"], "fonte": c["link"]}, **extra))
        if base:
            outros = sorted((c for c in cands if c["tam"] and c["tam"][1] == base[1] and c not in iguais), key=lambda x: x["preco"] / x["tam"][0])
            for c in outros[:4]:
                tamanhos.append(dict({"rede": rede, "embalagem": (c.get("curto") or c["nome"])[:40], "quantidade": c["tam"][0], "unidade": c["tam"][1],
                                      "preco": c["preco"], "fonte": c["link"]}, **extra))
        for c in cands[:3]:
            if c.get("de"):
                ofertas.append(dict({"rede": rede, "produto": c["nome"], "preco_normal": c["de"], "preco_oferta": c["preco"], "tipo": "promo",
                                     "fonte": c["link"], "tamanho": {"quantidade": c["tam"][0], "unidade": c["tam"][1]} if c["tam"] else None}, **extra))
    ent = {"produto": nome, "precos": precos, "tamanhos": tamanhos}
    sim = [dict({"rede": rede, "nome": c["nome"][:80], "preco": c["preco"], "quantidade": c["tam"][0], "unidade": c["tam"][1], "fonte": c["link"]}, **extra)
           for rede, cs in (similares or {}).items() for c in cs if c.get("tam")]
    if sim:
        ent["similares"] = sim
    if base:
        ent["base"] = {"quantidade": base[0], "unidade": base[1]}
    return ent, ofertas


# ---------- Mercado Livre: o previsor de categorias diz de que tipo é cada produto, pelo nome ----------
# O mesmo modelo que o Mercado Livre usa para classificar os anúncios (português do Brasil). O item da lista e cada
# produto achado ganham uma categoria; produto de outra categoria (hambúrguer para "carne moída") sai. Precisa de um
# app de desenvolvedor do Mercado Livre, autorizado uma vez; o EconomIA renova o acesso sozinho. Tudo fica em
# segredos.json e as respostas em categorias_ml.json (90 dias).
ML_API = os.environ.get("OFERTAS_ML_API", "https://api.mercadolibre.com")
ML_AUTH = os.environ.get("OFERTAS_ML_AUTH", "https://auth.mercadolivre.com.br/authorization")
CATEGORIAS_ML = os.path.join(DATA, "categorias_ml.json")
ML_POR_HORA = 400  # consultas novas por hora, no máximo (o resto fica para a próxima busca)
_ml_trava = threading.Lock()
_ml = {"cache": None, "mudou": False, "horas": [], "pausa": 0.0, "erro": None}


def ml_conf():
    c = segredos().get("ml")
    return c if isinstance(c, dict) else {}


def ml_ligado():
    c = ml_conf()
    return bool(c.get("app_id") and c.get("secret") and c.get("refresh_token"))


def ml_autorizar_url(c=None):
    c = c or ml_conf()
    if not (c.get("app_id") and c.get("url_retorno")):
        return None
    return ML_AUTH + "?" + urllib.parse.urlencode({"response_type": "code", "client_id": c["app_id"], "redirect_uri": c["url_retorno"]})


def ml_pede(caminho, dados=None, token=None):
    """Chamada à API do Mercado Livre: POST de formulário (dados) ou GET; devolve o JSON ou levanta ErroBusca."""
    h = {"Accept": "application/json", "User-Agent": "EconomIA (Home Assistant)"}
    if token:
        h["Authorization"] = "Bearer " + token
    corpo = urllib.parse.urlencode(dados).encode() if dados is not None else None
    if corpo is not None:
        h["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(ML_API + caminho, data=corpo, headers=h, method="POST" if corpo is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read(2_000_000).decode("utf-8") or "null")
    except urllib.error.HTTPError as e:
        try:
            j = json.loads(e.read(20000).decode("utf-8") or "{}")
        except Exception:  # noqa: BLE001
            j = {}
        motivo = str((j or {}).get("error") or "")
        msg = str((j or {}).get("message") or (j or {}).get("error_description") or motivo or "")[:160]
        if e.code == 429:
            _ml["pausa"] = time.time() + 600
            raise ErroBusca("O Mercado Livre pediu para esperar (consultas demais). Tento de novo em 10 minutos.") from e
        if motivo == "invalid_grant":
            raise ErroBusca("O Mercado Livre não aceitou a autorização (código usado, vencido ou revogado). Autorize de novo em Mais › Integrações.") from e
        if motivo == "invalid_client":
            raise ErroBusca("O Mercado Livre recusou o App ID ou a chave secreta. Confira em Mais › Integrações.") from e
        raise ErroBusca(f"O Mercado Livre respondeu com erro {e.code}" + (f": {msg}" if msg else "") + ".") from e


def ml_guarda_token(d):
    if not isinstance(d, dict) or not d.get("access_token"):
        raise ErroBusca("O Mercado Livre não devolveu o acesso.")
    seg = segredos()
    c = dict(seg.get("ml") or {})
    c.update({"access_token": str(d["access_token"]), "refresh_token": str(d.get("refresh_token") or c.get("refresh_token") or ""),
              "expira": time.time() + max(600, int(d.get("expires_in") or 10800)) - 300})
    seg["ml"] = c
    grava_segredos(seg)


def ml_conectar(texto_colado):
    """Troca o código da autorização (o endereço inteiro que abriu, ou só o código TG-...) pelo acesso."""
    c = ml_conf()
    if not (c.get("app_id") and c.get("secret") and c.get("url_retorno")):
        raise ErroBusca("Salve antes o App ID, a chave secreta e a URL de retorno.")
    t = str(texto_colado or "").strip()
    m = re.search(r"[?&#]code=([^&#\s]+)", t)
    cod = urllib.parse.unquote(m.group(1)) if m else t
    if not re.fullmatch(r"[\w.\-]{6,300}", cod):
        raise ErroBusca("Cole o endereço que abriu depois de autorizar (ele tem code=TG-…).")
    with _ml_trava:
        ml_guarda_token(ml_pede("/oauth/token", {"grant_type": "authorization_code", "client_id": c["app_id"], "client_secret": c["secret"],
                                                 "code": cod, "redirect_uri": c["url_retorno"]}))


def ml_token():
    """O acesso válido, renovado pelo refresh_token quando vence (o Mercado Livre troca o refresh_token a cada uso)."""
    with _ml_trava:
        c = ml_conf()
        if c.get("access_token") and float(c.get("expira") or 0) > time.time():
            return c["access_token"]
        if not (c.get("refresh_token") and c.get("app_id") and c.get("secret")):
            return None
        try:
            d = ml_pede("/oauth/token", {"grant_type": "refresh_token", "client_id": c["app_id"], "client_secret": c["secret"],
                                        "refresh_token": c["refresh_token"]})
        except ErroBusca as e:
            if "autorização" in str(e) or "recusou" in str(e):  # sem volta: precisa autorizar de novo
                seg = segredos()
                x = dict(seg.get("ml") or {})
                for k in ("access_token", "refresh_token", "expira"):
                    x.pop(k, None)
                seg["ml"] = x
                grava_segredos(seg)
            raise
        ml_guarda_token(d)
        return d["access_token"]


def cache_ml():
    if _ml["cache"] is None:
        d = ler_json(CATEGORIAS_ML, {}) or {}
        _ml["cache"] = d if isinstance(d, dict) else {}
    return _ml["cache"]


def grava_ml():
    with _ml_trava:
        if _ml["mudou"] and _ml["cache"] is not None:
            c = _ml["cache"]
            if len(c) > 8000:  # ficam os mais recentes
                for k in sorted(c, key=lambda k: c[k].get("em", ""))[:len(c) - 8000]:
                    c.pop(k, None)
            gravar_json(CATEGORIAS_ML, c)
            _ml["mudou"] = False


def ml_prever(titulo):
    """[{"d": domínio, "c": categoria, "n": nome da categoria}] para o nome, do mais provável para o menos;
    [] se o Mercado Livre não soube; None se não deu para perguntar agora (sem conexão, limite da hora)."""
    k = norm(titulo)[:120]
    if not k:
        return []
    cache = cache_ml()
    noventa = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat(timespec="seconds")
    if k in cache and cache[k].get("em", "") >= noventa:
        return cache[k].get("p") or []
    agora_s = time.time()
    _ml["horas"] = [t for t in _ml["horas"] if t > agora_s - 3600]
    if agora_s < _ml["pausa"] or len(_ml["horas"]) >= ML_POR_HORA:
        return None
    tok = ml_token()
    if not tok:
        return None
    _ml["horas"].append(agora_s)
    d = ml_pede("/sites/MLB/domain_discovery/search?" + urllib.parse.urlencode({"limit": 3, "q": str(titulo)[:150]}), token=tok)
    p = [{"d": str(x.get("domain_id") or ""), "c": str(x.get("category_id") or ""), "n": texto(x.get("category_name"), 60) or ""}
         for x in (d if isinstance(d, list) else []) if isinstance(x, dict) and (x.get("domain_id") or x.get("category_id"))]
    with _ml_trava:
        cache[k] = {"p": p, "em": agora()}
        _ml["mudou"] = True
    return p


def confere_ml(item, nomes):
    """Para cada nome de produto: True se o Mercado Livre põe o produto numa das categorias do item, False se põe em
    outra (hambúrguer para "carne moída"), None se não dá para saber (sem conexão, sem resposta)."""
    if not nomes or not ml_ligado():
        return [None] * len(nomes)
    try:
        alvo = set()
        for a in alternativas(item):
            for x in ml_prever(a) or []:
                alvo |= {x["d"], x["c"]} - {""}
        if not alvo:
            return [None] * len(nomes)
        out = []
        for n in nomes:
            p = ml_prever(n)
            out.append(None if not p else bool({p[0]["d"], p[0]["c"]} & alvo))
        _ml["erro"] = None
        return out
    except ErroBusca as e:
        _ml["erro"] = str(e)
        log(f"Mercado Livre (categorias): {e}")
    except Exception as e:  # noqa: BLE001
        log(f"Mercado Livre (categorias): {e}")
    return [None] * len(nomes)


def filtra_ml(item, cands):
    """Tira os produtos que o Mercado Livre põe em outra categoria, mas só quando ele confirma pelo menos um produto
    na categoria do item: se não confirma nenhum, quem pode estar errado é o palpite para o item, e nada sai.
    O produto achado antes pelo código de barras (o mesmo produto) nunca sai."""
    if not cands or not ml_ligado():
        return cands
    ok = confere_ml(item, [c.get("nome") or "" for c in cands])
    if True not in ok:
        return cands
    eans = set((casados().get(norm(item)) or {}).get("eans") or [])
    fica = [c for c, o in zip(cands, ok) if o is not False or (c.get("ean") and c.get("ean") in eans)]
    if len(fica) < len(cands):
        log(f"Mercado Livre (categorias): {len(cands) - len(fica)} produto(s) de outra categoria fora de '{item}' "
            f"({'; '.join(c.get('nome', '')[:40] for c in cands if c not in fica)[:200]})")
    return fica


def testar_ml():
    c = ml_conf()
    if not (c.get("app_id") and c.get("secret")):
        return {"ok": False, "msg": "Falta o App ID ou a chave secreta."}
    if not c.get("refresh_token"):
        return {"ok": False, "msg": "Falta autorizar: toque em Autorizar no Mercado Livre e cole aqui o endereço que abrir."}
    try:
        _ml["pausa"] = 0.0
        a = ml_pede("/sites/MLB/domain_discovery/search?" + urllib.parse.urlencode({"limit": 1, "q": "Carne moída bovina de primeira 500 g"}), token=ml_token())
        b = ml_pede("/sites/MLB/domain_discovery/search?" + urllib.parse.urlencode({"limit": 1, "q": "Hambúrguer bovino congelado 672 g"}), token=ml_token())
    except ErroBusca as e:
        return {"ok": False, "msg": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "msg": f"Não consegui testar ({e})."}
    na = (a[0].get("category_name") if isinstance(a, list) and a else None) or "?"
    nb = (b[0].get("category_name") if isinstance(b, list) and b else None) or "?"
    return {"ok": True, "msg": f"Conectado. Teste: carne moída → {na}; hambúrguer → {nb}."}


# ---------- Shopee Afiliados: a Open API devolve produto, preço e link, sem IA ----------
# App ID e senha ficam em /data/segredos.json, que não vai para o painel, para o HA nem para as versões.
SHOPEE_ERROS = {
    10020: "A Shopee recusou o App ID ou a senha. Confira em affiliate.shopee.com.br › Open API.",
    10030: "A Shopee pediu para esperar: consultas demais em pouco tempo.",
    10031: "A Shopee negou o acesso a essa consulta.",
    10032: "A Shopee não reconheceu a conta de afiliado.",
    10033: "A conta de afiliado está congelada na Shopee.",
    10035: "A conta de afiliado ainda não tem acesso à Open API. Peça o acesso em affiliate.shopee.com.br › Open API.",
}


class ErroShopee(Exception):
    pass


def segredos():
    d = ler_json(SEGREDOS, {}) or {}
    return d if isinstance(d, dict) else {}


def grava_segredos(d):
    gravar_json(SEGREDOS, d)
    try:
        os.chmod(SEGREDOS, 0o600)
    except OSError:
        pass


def shopee_chaves():
    sh = segredos().get("shopee") or {}
    app, senha = str(sh.get("app_id") or "").strip(), str(sh.get("secret") or "").strip()
    return (app, senha) if app and senha else None


def shopee_pronta():
    return shopee_chaves() is not None


def shopee_consulta(query):
    chaves = shopee_chaves()
    if not chaves:
        raise ErroShopee("Falta o App ID e a senha da Shopee em Mais › Integrações.")
    app, senha = chaves
    corpo = json.dumps({"query": query}, separators=(",", ":"), ensure_ascii=False)
    ts = str(int(time.time()))
    assinatura = hashlib.sha256((app + ts + corpo + senha).encode("utf-8")).hexdigest()
    req = urllib.request.Request(SHOPEE_API, data=corpo.encode("utf-8"), method="POST", headers={
        "Content-Type": "application/json", "User-Agent": "EconomIA",
        "Authorization": f"SHA256 Credential={app}, Timestamp={ts}, Signature={assinatura}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read(4_000_000).decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            d = json.loads(e.read(200_000).decode("utf-8") or "{}")
        except (ValueError, OSError):
            raise ErroShopee(f"A Shopee respondeu com erro {e.code}.") from e
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise ErroShopee(f"Não consegui falar com a Shopee ({e}).") from e
    erros = d.get("errors") if isinstance(d, dict) else None
    if erros:
        e0 = erros[0] if isinstance(erros[0], dict) else {}
        cod = (e0.get("extensions") or {}).get("code")
        try:
            cod = int(cod)
        except (TypeError, ValueError):
            pass
        raise ErroShopee(SHOPEE_ERROS.get(cod) or f"A Shopee recusou a consulta: {str(e0.get('message') or cod)[:160]}")
    return (d.get("data") if isinstance(d, dict) else None) or {}


def shopee_produtos(termo, limite=20):
    q = ("{productOfferV2(keyword: %s, sortType: 1, page: 1, limit: %d) {nodes {itemId productName priceMin priceMax "
         "productLink offerLink shopName shopType ratingStar sales priceDiscountRate} pageInfo {page limit hasNextPage}}}") % (
        json.dumps(str(termo)[:80], ensure_ascii=False), int(limite))
    return ((shopee_consulta(q).get("productOfferV2") or {}).get("nodes")) or []


def testar_shopee():
    try:
        nodes = shopee_produtos("café 500 g", 5)
    except ErroShopee as e:
        return {"ok": False, "msg": str(e)}
    if not nodes:
        return {"ok": True, "msg": "A Shopee aceitou o App ID e a senha, mas não devolveu produtos no teste."}
    x = nodes[0]
    return {"ok": True, "msg": f"Pronta. Exemplo: {str(x.get('productName') or '')[:60]} por {br_preco(numero(x.get('priceMin')) or 0)}."}


def busca_shopee(cfg, itens=None):
    """Preço de cada item da lista na Shopee, pela Open API do Shopee Afiliados. Devolve [(categoria, parcial)]."""
    nomes = itens or nomes_da_lista(cfg)
    if not nomes or not shopee_pronta():
        return []
    BUSCA["etapa"] = "preços na Shopee"
    lista_bruta, n = [], 0
    for nome in nomes:
        try:
            nodes = shopee_produtos(nome)
        except ErroShopee as e:
            log(f"shopee '{nome}': {e}")
            if not str(e).startswith("A Shopee recusou a consulta"):
                break  # chave errada, sem acesso ou limite: as outras consultas também vão falhar
            continue
        cands = []
        for x in nodes:
            pn = str(x.get("productName") or "").strip()
            preco, nota = numero(x.get("priceMin")), numero(x.get("ratingStar")) or 0
            if not pn or not preco or (nota and nota < 4.5) or not combina(nome, pn):
                continue
            cands.append({"nome": pn[:80], "preco": preco, "de": None, "tam": tamanho_nome(pn),
                          "link": fonte_ok(x.get("productLink")) or fonte_ok(x.get("offerLink"))})
        if cands:
            n += 1
            ent, _ = montar_item(nome, {"Shopee": cands}, frete="carrinho")
            lista_bruta.append(ent)
    log(f"shopee: {n} de {len(nomes)} item(ns) com preço")
    if not lista_bruta:
        return []
    cat, parcial = normalizar("online", {"lojas": [], "cupons": [], "ofertas": [], "lista": lista_bruta, "_via": "api"},
                              dict(cfg, lista=[{"produto": x} for x in nomes]))
    return [(cat, parcial)]


# ---------- folhetos dos sites de encartes (Kimbino, Seus Folhetos) ----------
# O folheto da semana de cada loja escolhida em Mais › Lojas é lido uma vez pela IA de fotos e guardado até vencer.
# Nas buscas seguintes os preços vêm do que foi guardado, e os itens novos da lista são casados com as ofertas
# do folheto pelo nome, sem IA.
AGREGADORES = [
    {"id": "kimbino", "nome": "Kimbino", "base": "https://www.kimbino.com.br", "loja": "/{}/",
     "variantes": ["{}", "{}-atacadista", "{}-supermercados", "supermercados-{}", "{}-supermercado"]},
    {"id": "seusfolhetos", "nome": "Seus Folhetos", "base": "https://seusfolhetos.com.br", "loja": "/{}-ofertas",
     "variantes": ["{}", "{}-atacadista", "supermercados-{}"]},
    # Portafolhetos: da mesma empresa do Kimbino, com o mesmo formato (imagens no leafletscdn)
    {"id": "portafolhetos", "tipo": "kimbino", "nome": "Portafolhetos", "base": "https://www.portafolhetos.com.br", "loja": "/{}/",
     "variantes": ["{}", "{}-atacadista", "{}-supermercados", "supermercados-{}"]},
    # Catálogos Ofertas: o robots.txt libera /lojas/ e /vista/ofertas/ (sem parâmetros) e não define sinal de IA
    {"id": "catalogosofertas", "nome": "Catálogos Ofertas", "base": "https://www.catalogosofertas.com.br", "loja": "/lojas/{}/ofertas-catalogos",
     "variantes": ["{}", "{}-atacadista", "supermercados-{}"]},
]
MESES = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6, "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}
PERIODO_MES = re.compile(r"(\d{1,2})\s+(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\w*\.?\s*(?:-|–|a|até)\s*(\d{1,2})\s+(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)", re.I)
PERIODO_TRACO = re.compile(r"(\d{2})-(\d{2})-(\d{4})\D{1,12}?(\d{2})-(\d{2})-(\d{4})")
CO_IMG = re.compile(r"(?:https?://[^\"'\s<>]*?)?/assets/uploads/flyers/(\d+)/([A-Za-z0-9_]+)/([a-z0-9-]+?)-(\d+)-(\d+)-([0-9a-f]+)\.(webp|jpe?g|png)", re.I)
# tamanhos que a página do folheto não mostra (ela traz só miniaturas de 260 px): o add-on testa e guarda o que existir
CO_TAMANHOS = ["1040x1080WebP", "780x810WebP", "1300x1350WebP", "1000x1000WebP", "1200x1200WebP", "1500x1500WebP", "800x800WebP",
               "normalWebP", "normal", "largeWebP", "large", "bigWebP", "big", "zoomWebP", "zoom", "original", "520x540WebP"]
CO_LARGURA_MIN = 700
CO_TAMANHO_ARQ = os.path.join(DATA, "catalogos_tamanho.json")
_robots_agreg = {}


def periodo_mes(t):
    """"30 out. até 10 nov." → ("2026-10-30", "2026-11-10")."""
    m = PERIODO_MES.search(str(t or ""))
    if not m:
        return None, None
    ano = int(hoje_br()[:4])
    m1, m2 = MESES[m.group(2).lower()[:3]], MESES[m.group(4).lower()[:3]]
    try:
        de = datetime(ano, m1, int(m.group(1))).date()
        ate = datetime(ano + (1 if m2 < m1 else 0), m2, int(m.group(3))).date()
    except ValueError:
        return None, None
    return de.isoformat(), ate.isoformat()


def tamanho_imagem(d):
    """(largura, altura) pelo cabeçalho de um WebP, JPEG ou PNG."""
    try:
        if d[:4] == b"RIFF" and d[8:12] == b"WEBP":
            c = d[12:16]
            if c == b"VP8X":
                return 1 + int.from_bytes(d[24:27], "little"), 1 + int.from_bytes(d[27:30], "little")
            if c == b"VP8 ":
                return int.from_bytes(d[26:28], "little") & 0x3FFF, int.from_bytes(d[28:30], "little") & 0x3FFF
            if c == b"VP8L":
                b = int.from_bytes(d[21:25], "little")
                return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
        if d[:8] == b"\x89PNG\r\n\x1a\n":
            return int.from_bytes(d[16:20], "big"), int.from_bytes(d[20:24], "big")
        if d[:2] == b"\xff\xd8":
            i = 2
            while i + 9 < len(d):
                if d[i] != 0xFF:
                    i += 1
                    continue
                mk = d[i + 1]
                if 0xC0 <= mk <= 0xCF and mk not in (0xC4, 0xC8, 0xCC):
                    return int.from_bytes(d[i + 7:i + 9], "big"), int.from_bytes(d[i + 5:i + 7], "big")
                i += 2 + int.from_bytes(d[i + 2:i + 4], "big")
    except (IndexError, ValueError):
        pass
    return None


def agreg_permite(url):
    """O robots.txt do site de encartes deixa programas abrirem este endereço? (lido uma vez por dia)"""
    sp = urllib.parse.urlsplit(url)
    if FOLHETOS_TESTE and url.startswith(FOLHETOS_TESTE):
        base, caminho = FOLHETOS_TESTE.rstrip("/") + "/" + sp.path.strip("/").split("/")[0], "/" + "/".join(sp.path.strip("/").split("/")[1:])
    else:
        base, caminho = f"{sp.scheme}://{sp.netloc}", sp.path or "/"
    g = _robots_agreg.get(base)
    if not g or g[0] < time.time() - 86400:
        motivo = "o robots.txt do site não deixa"
        try:
            txt = pagina_txt(base + "/robots.txt")
            regras = robots_regras(txt)
            # sinal de conteúdo (Cloudflare): "ai-input=no" proíbe mandar o conteúdo para uma IA, que é o que o folheto faz
            if re.search(r"(?im)^\s*content-signal\s*:.*\bai-input\s*=\s*no\b", txt):
                regras = [("disallow", "/")]
                motivo = "o site não deixa mandar o conteúdo para IA (ai-input=no)"
                log(f"{base}: {motivo}")
        except urllib.error.HTTPError as e:
            regras = [] if e.code == 404 else [("disallow", "/")]
            if e.code != 404:
                motivo = f"o site recusou o acesso de programas (erro {e.code})" if e.code in (401, 403, 429) else f"o site respondeu com erro {e.code}"
        except Exception as e:  # noqa: BLE001
            regras = [("disallow", "/")]  # sem resposta: não abre
            motivo = f"o site não respondeu ({str(getattr(e, 'reason', e))[:60]})"
        g = _robots_agreg[base] = (time.time(), regras, motivo)
    if robots_permite(g[1], caminho + (("?" + sp.query) if sp.query else "")):
        return True
    _robots_agreg["_ultimo"] = g[2] if len(g) > 2 else "o robots.txt do site não deixa"
    return False
MAX_FOLHETOS_LOJA = 2
MAX_PAGINAS = 12
DATA_BR = re.compile(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?")
PERIODO = re.compile(r"(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\s*(?:-|–|a|até)\s*(\d{1,2}/\d{1,2}/\d{2,4})", re.I)
KIMBI_IMG = re.compile(r"https?://[^\"'\s<>]*(?:kimbicdn|leafletscdn)\.com/[^\"'\s<>]*?/data/(\d+/\d+)/(\d+)\.(?:jpe?g|png|webp)[^\"'\s<>,]*", re.I)
SF_IMG = re.compile(r"(?:https?://[^\"'\s<>/]+)?/public/gimg/(?:\d+/)+(\d+)-(\d+)-(\d+)\.(?:jpe?g|png|webp)", re.I)
_folhetos_trava = threading.Lock()


def agreg_base(a):
    return FOLHETOS_TESTE.rstrip("/") + "/" + a["id"] if FOLHETOS_TESTE else a["base"]


# páginas guardam os cookies que o próprio site manda (como um navegador comum faz entre um redirecionamento e outro)
_abridor = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def pagina_resp(url, timeout=20):
    """(texto, código HTTP, endereço final depois dos redirecionamentos, cabeçalhos)."""
    req = urllib.request.Request(url, headers={"User-Agent": NAVEGADOR, "Accept": ACEITA, "Accept-Language": "pt-BR,pt;q=0.9"})
    with _abridor.open(req, timeout=timeout) as r:
        dado = r.read(4 * 1024 * 1024 + 1)
        return dado.decode("utf-8", "ignore"), getattr(r, "status", 200), r.geturl(), r.headers


def pagina_txt(url):
    return pagina_resp(url)[0]


ROBO_FORTE = re.compile(r"(?i)<title>\s*just a moment|cf_chl_opt|attention required! \| cloudflare|captcha-delivery\.com|px-captcha")
ROBO_FRACO = re.compile(r"(?i)cf-chl|challenge-platform|awswaf|_incapsula_resource|captcha|turnstile|document\.cookie\s*=|verify you are human"
                        r"|verifique se (?:você|voce) é humano|are you a robot")


def pede_robo(txt, cab=None):
    """A página é uma verificação de robô (Cloudflare, AWS WAF, Imperva, DataDome…)? O add-on não tenta passar por ela."""
    h = {k.lower(): str(v).lower() for k, v in (cab.items() if cab else [])}
    if h.get("x-amzn-waf-action") or h.get("cf-mitigated") == "challenge":
        return True
    return bool(ROBO_FORTE.search(txt[:60000])) or (len(txt) < 20000 and bool(ROBO_FRACO.search(txt)))


def redireciona_para(txt, base):
    """Página quase vazia que só manda para outro endereço (meta refresh ou location em JS): o endereço."""
    m = re.search(r"""(?i)<meta[^>]+http-equiv=["']?refresh["']?[^>]*content=["']?\s*\d*\s*;?\s*url\s*=\s*['"]?([^"'>\s]+)""", txt) \
        or re.search(r"""(?:window|document|top|self)\.location(?:\.href)?\s*=\s*["']([^"']+)["']|location\.(?:replace|assign)\(\s*["']([^"']+)["']""", txt)
    if not m:
        return None
    alvo = next(g for g in m.groups() if g)
    return urllib.parse.urljoin(base, html_mod.unescape(alvo))


def resumo_vazia(txt, cod, cab):
    """"código 202, 0 bytes, servidor CloudFront": o que dá para saber de uma página que veio vazia."""
    srv = str((cab.get("Server") if cab else "") or "").strip()[:20]
    return f"código {cod}, {len(txt.encode())} bytes" + (f", servidor {srv}" if srv else "")


def sem_tags(t):
    return " ".join(html_mod.unescape(re.sub(r"(?s)<[^>]+>", " ", t)).split())


def data_iso(txt):
    """"29/10/2026", "29/10/26" ou "29/10" (ano de hoje) → "2026-10-29"."""
    m = DATA_BR.search(str(txt or ""))
    if not m:
        return None
    ano = m.group(3)
    a = (int(ano) + (2000 if len(ano) == 2 else 0)) if ano else int(hoje_br()[:4])
    try:
        return datetime(a, int(m.group(2)), int(m.group(1))).date().isoformat()
    except ValueError:
        return None


def periodo_de(m):
    a, b = m.group(1), m.group(2)
    return data_iso(a if a.count("/") == 2 else a + "/" + b.split("/")[-1]), data_iso(b)


def folhetos_da_pagina(a, url_loja, html_txt):
    """Os folhetos listados na página da loja: [{url, id, de, ate}]."""
    caminho = urllib.parse.urlsplit(url_loja).path.rstrip("/")
    if a["id"] == "catalogosofertas":
        loja_slug = caminho.split("/lojas/", 1)[-1].split("/")[0]
        out, vistos = [], set()
        achados = list(re.finditer(r"((?:https?:)?(?:\\?/\\?/[^/\"'\s]+)?(?:\\?/[a-z0-9-]+)?\\?/vista\\?/ofertas\\?/([a-z0-9-]+)-(\d{5,}))(?![\d])", html_txt, re.I))
        for i, m in enumerate(achados):
            if loja_slug not in m.group(2) or m.group(3) in vistos:
                continue  # "encartes parecidos" de outras lojas ficam de fora
            vistos.add(m.group(3))
            fim = next((x.start() for x in achados[i + 1:] if x.group(3) != m.group(3)), min(len(html_txt), m.end() + 3000))
            de, ate = periodo_mes(sem_tags(html_txt[m.start():min(fim, m.end() + 3000)]))
            caminho_f = m.group(1).replace("\\/", "/")
            out.append({"url": urllib.parse.urljoin(url_loja, html_mod.unescape(caminho_f)), "id": a["id"] + ":" + m.group(3), "de": de, "ate": ate})
        return out
    if a.get("tipo", a["id"]) == "kimbino":
        padrao = re.compile(r"href=[\"']((?:https?://[^/\"']+)?" + re.escape(caminho) + r"/[a-z0-9-]+-(\d{6,})/?)[\"']", re.I)
    else:
        padrao = re.compile(r"href=[\"']((?:https?://[^/\"']+)?" + re.escape(caminho)
                            + r"/(?:folheto-(\d+)(?:-\d+)?|[a-z0-9-]*folheto[a-z0-9-]*))[\"']", re.I)
    achados = [(urllib.parse.urljoin(url_loja, html_mod.unescape(m.group(1))), m) for m in padrao.finditer(html_txt)]
    vistos, out = set(), []
    for i, (u, m) in enumerate(achados):
        if u in vistos:
            continue
        vistos.add(u)
        # o texto do folheto fica entre o link dele e o link do próximo folheto (ou, antes, desde o anterior)
        ultimo = max(k for k, (x, _) in enumerate(achados) if x == u)
        prox = next((mm.start() for x, mm in achados[ultimo + 1:] if x != u), len(html_txt))
        ant = max([mm.end() for x, mm in achados[:i] if x != u] or [0])
        ini = max(0, html_txt.rfind("<", 0, m.start()))
        de, ate = None, None
        for trecho in (html_txt[ini:min(prox, ini + 2500)], html_txt[max(ant, ini - 1500):ini]):
            mp = PERIODO.search(sem_tags(trecho))
            if mp:
                de, ate = periodo_de(mp)
                break
        if not de:
            d = re.search(r"-(\d{2})-(\d{2})-(\d{4})-\d{6,}/?$", u)
            if d:
                de = f"{d.group(3)}-{d.group(2)}-{d.group(1)}"
        out.append({"url": u, "id": a["id"] + ":" + (m.group(2) or slug(urllib.parse.urlsplit(u).path, 60)), "de": de, "ate": ate})
    return out


def paginas_folheto(a, f):
    """Endereços das páginas do folheto, na ordem (e a validade, se a página do folheto disser)."""
    if f.get("paginas") is not None:
        return f["paginas"]
    if not agreg_permite(f["url"]):
        f["paginas"] = []
        return []
    try:
        html_txt = pagina_txt(f["url"])
    except Exception as e:  # noqa: BLE001
        log(f"folheto {f['url']}: {e}")
        f["paginas"] = []
        return []
    if not f.get("ate"):
        desc = re.search(r"(?:name|property)=[\"'](?:og:)?description[\"'][^>]*content=[\"']([^\"']+)", html_txt, re.I)
        m = (PERIODO.search(html_mod.unescape(desc.group(1))) if desc else None) or PERIODO.search(sem_tags(html_txt)[:20000])
        if m:
            f["de"], f["ate"] = periodo_de(m)
    if not f.get("ate") and a["id"] == "catalogosofertas":
        m = PERIODO_TRACO.search(html_txt)
        if m:
            f["de"], f["ate"] = f"{m.group(3)}-{m.group(2)}-{m.group(1)}", f"{m.group(6)}-{m.group(5)}-{m.group(4)}"
        else:
            f["de"], f["ate"] = periodo_mes(sem_tags(html_txt)[:20000])
    paginas = {}
    if a["id"] == "catalogosofertas":
        fid = f["id"].split(":", 1)[-1]
        for m in CO_IMG.finditer(html_txt):
            n = int(m.group(4))
            # a mesma página pode vir em JPEG e em WebP: fica a WebP, que é o formato das pastas grandes
            if m.group(1) == fid and (n not in paginas or (m.group(7).lower() == "webp" and not paginas[n].lower().endswith(".webp"))):
                paginas[n] = urllib.parse.urljoin(f["url"], m.group(0))
        grandes = paginas_grandes([paginas[k] for k in sorted(paginas)][:MAX_PAGINAS])
        f["pequeno"] = bool(paginas) and not grandes
        f["paginas"] = grandes
        return grandes
    if a.get("tipo", a["id"]) == "kimbino":
        achados = [(m.group(1), int(m.group(2)), m.group(0).replace("&amp;", "&").rstrip(",")) for m in KIMBI_IMG.finditer(html_txt)]
        # o folheto é a pasta que mais aparece (as outras são capas de folhetos sugeridos)
        conta = {}
        for pasta, _, _ in achados:
            conta[pasta] = conta.get(pasta, 0) + 1
        if conta:
            pasta = max(conta, key=conta.get)
            for p_, n, u in achados:
                if p_ != pasta:
                    continue
                atual = paginas.get(n)
                if atual is None or ("/0x0/" in u and "/0x0/" not in atual):
                    paginas[n] = u
    else:
        achados = [(int(m.group(1)), int(m.group(2)), int(m.group(3)), urllib.parse.urljoin(f["url"], m.group(0))) for m in SF_IMG.finditer(html_txt)]
        # as páginas usam o mesmo tamanho, comprido; capas de outros folhetos e a imagem de compartilhar usam outros
        conta = {}
        for _, w, h, _ in achados:
            if h >= 2000:
                conta[(w, h)] = conta.get((w, h), 0) + 1
        if conta:
            tam = max(conta, key=lambda k: (conta[k], k[0]))
            for i, w, h, u in achados:
                if (w, h) == tam:
                    paginas.setdefault(i, u)
    f["paginas"] = [paginas[k] for k in sorted(paginas)][:MAX_PAGINAS]
    if f["paginas"] and not agreg_permite(f["paginas"][0]):  # o servidor de imagens também precisa deixar
        f["paginas"] = []
    return f["paginas"]


def paginas_grandes(miniaturas):
    """Troca a pasta de tamanho das miniaturas pela maior que o servidor de imagens tiver (o tamanho achado fica guardado)."""
    if not miniaturas:
        return []
    g = ler_json(CO_TAMANHO_ARQ, {}) or {}
    mes = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(timespec="seconds")
    semana = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(timespec="seconds")
    troca = lambda u, t: re.sub(r"(/assets/uploads/flyers/\d+/)[A-Za-z0-9_]+/", r"\g<1>" + t + "/", u)  # noqa: E731
    if g.get("pasta") and g.get("em", "") >= mes:
        return [troca(u, g["pasta"]) for u in miniaturas]
    if g.get("nenhum") and g.get("em", "") >= semana:
        return []
    melhor = None
    for t in CO_TAMANHOS:
        u = troca(miniaturas[0], t)
        if not agreg_permite(u):
            continue
        try:
            dado, _ = baixar(u, 6_000_000, timeout=15)
        except Exception:  # noqa: BLE001
            continue
        wh = tamanho_imagem(dado)
        if wh and wh[0] >= CO_LARGURA_MIN and (not melhor or wh[0] > melhor[1]):
            melhor = (t, wh[0])
            if wh[0] >= 1000:
                break
    gravar_json(CO_TAMANHO_ARQ, {"pasta": melhor[0], "largura": melhor[1], "em": agora()} if melhor else {"nenhum": True, "em": agora()})
    log("Catálogos Ofertas: " + (f"páginas em {melhor[0]} ({melhor[1]} px)" if melhor else "só miniaturas, pequenas demais para ler"))
    return [troca(u, melhor[0]) for u in miniaturas] if melhor else []


def cidade_do_cep(cep, cache):
    cep = re.sub(r"\D", "", str(cep or ""))
    c = cache.get("_cep") or {}
    if c.get("cep") == cep and c.get("cidade"):
        return c["cidade"], c.get("uf")
    try:
        d = {"localidade": "Joinville", "uf": "SC"} if FOLHETOS_TESTE else http_json(f"https://viacep.com.br/ws/{cep}/json/", timeout=10)
    except Exception:  # noqa: BLE001
        return None, None
    cidade, uf = (d or {}).get("localidade"), (d or {}).get("uf")
    if cidade:
        cache["_cep"] = {"cep": cep, "cidade": cidade, "uf": uf}
    return cidade, uf


def ia_com_arquivos(nome, instrucoes, dados, uso="fotos"):
    """Grava as imagens um instante na pasta de mídia, pede para a IA ler e apaga."""
    pasta = os.path.join(MEDIA, "economia")
    arquivos, anexos = [], []
    try:
        os.makedirs(pasta, exist_ok=True)
        marca = datetime.now().strftime("%H%M%S") + os.urandom(2).hex()
        for n, (dado, t) in enumerate(dados):
            t = t if t in ("image/jpeg", "image/png", "image/webp", "application/pdf") else "image/jpeg"
            ext = {"application/pdf": "pdf", "image/png": "png", "image/webp": "webp"}.get(t, "jpg")
            arq = f"folheto-{marca}-{n}.{ext}"
            with open(os.path.join(pasta, arq), "wb") as fh:
                fh.write(dado)
            arquivos.append(os.path.join(pasta, arq))
            anexos.append({"media_content_id": f"{MEDIA_URI}/economia/{arq}", "media_content_type": t})
        return chamar_ai_task(nome, instrucoes, anexos, uso=uso)
    finally:
        for a in arquivos:
            try:
                os.remove(a)
            except OSError:
                pass


def instrucoes_capas(loja, n, cidade, uf, cfg):
    onde = f"{cidade} ({uf})" if cidade else f"o CEP {cfg.get('cep')}"
    return f"""Você recebe a primeira página de {n} encartes de "{loja['nome']}", na ordem. O morador mora em {onde}. Hoje é {hoje_br()}.
Para cada encarte, diga se ele vale para as lojas de onde o morador mora: "sim" quando a página citar essa cidade, o estado ou a região dela, ou disser que vale para todas as lojas; "nao" quando citar só outras cidades, estados ou regiões; "nao_sei" quando a página não disser.
Responda somente com um objeto JSON, sem texto antes ou depois: {{"encartes": [{{"n": 1, "vale": "sim", "onde": "a região escrita no encarte, ou null"}}]}}"""


def escolhe_folhetos(loja, a, cands, cache, cfg):
    """Até 2 folhetos por loja. Com mais, a IA olha só a capa de cada um e diz quais valem para a cidade (fica guardado)."""
    cands = sorted(cands, key=lambda f: f.get("de") or "", reverse=True)
    if len(cands) <= MAX_FOLHETOS_LOJA:
        return cands
    vale = cache.setdefault("_vale", {})
    falta = [f for f in cands if f["id"] not in vale and f["id"] not in cache["itens"]]
    if falta and ia_ligada(cfg):
        cidade, uf = cidade_do_cep(cfg.get("cep"), cache)
        capas = []
        for f in falta[:16]:
            imgs = paginas_folheto(a, f)
            if not imgs:
                continue
            try:
                dado, t = baixar(imgs[0], 6_000_000)
            except Exception:  # noqa: BLE001
                continue
            capas.append((f, dado, t))
        for i in range(0, len(capas), 8):
            grupo = capas[i:i + 8]
            BUSCA["etapa"] = f"capas dos folhetos · {loja['nome']}"
            try:
                r = ia_com_arquivos(f"EconomIA: capas de {loja['nome']}", instrucoes_capas(loja, len(grupo), cidade, uf, cfg),
                                    [(d, t) for _, d, t in grupo])
            except ErroBusca as e:
                log(f"capas de {loja['nome']}: {e}")
                break
            resp = {}
            for x in (r.get("encartes") if isinstance(r, dict) else None) or []:
                if isinstance(x, dict) and str(x.get("n", "")).isdigit():
                    resp[int(x["n"])] = x.get("vale")
            for k, (f, _, _) in enumerate(grupo, 1):
                vale[f["id"]] = {"v": resp.get(k) if resp.get(k) in ("sim", "nao", "nao_sei") else "nao_sei", "ate": f.get("ate")}
    ordem = {"sim": 0, "nao_sei": 1}
    ok = [f for f in cands if f["id"] in cache["itens"] or (vale.get(f["id"]) or {}).get("v") in ordem]
    nota = lambda f: 0 if f["id"] in cache["itens"] else ordem[vale[f["id"]]["v"]]  # noqa: E731
    sims = [f for f in ok if nota(f) == 0]
    return (sims or sorted(ok, key=nota))[:MAX_FOLHETOS_LOJA]


def bases_loja(nome, cache):
    """Começos de endereço para procurar a loja: "Komprão Koch Atacadista" → komprao, komprao-koch."""
    cidade = norm((cache.get("_cep") or {}).get("cidade") or "")
    palavras = [w for w in norm(nome).split() if w not in GENERICAS and w not in cidade.split()]
    if not palavras:
        palavras = norm(nome).split()[:1]
    return list(dict.fromkeys(["-".join(palavras[:1]), "-".join(palavras[:2])]))


def achar_folhetos(loja, cache):
    """Acha a página da loja no Kimbino, no Seus Folhetos ou no Catálogos Ofertas e os folhetos válidos hoje: (agregador, url, folhetos)."""
    alvo = slug(loja["nome"], 40)
    bases = bases_loja(loja["nome"], cache)
    memo = cache.setdefault("_lojas", {})
    hoje = hoje_br()
    dias = lambda n: (datetime.now(timezone.utc) - timedelta(days=n)).isoformat(timespec="seconds")  # noqa: E731
    diag = loja.setdefault("_diag", {})
    for a in AGREGADORES:
        chave = a["id"] + ":" + alvo
        m = memo.get(chave) or {}
        if m.get("motivo") and not m.get("url") and m.get("em", "") >= dias(7):
            diag[a["nome"]] = m["motivo"]
        if m.get("url"):
            urls = [m["url"]] if m.get("em", "") >= dias(14) else []
        elif m and m.get("em", "") >= dias(7):
            continue  # não tem esta loja: só procura de novo daqui a uma semana
        else:
            urls = []
        # o nome inteiro primeiro ("droga-raia" antes de "droga"): o motivo mostrado é o da página certa
        urls = urls or list(dict.fromkeys(agreg_base(a) + a["loja"].format(v.format(b)) for b in reversed(bases) for v in a["variantes"]))
        achou, motivo = None, None
        for u in urls:
            if not agreg_permite(u):
                motivo = _robots_agreg.get("_ultimo")
                break
            try:
                html_txt, cod, final, cab = pagina_resp(u)
                ir = redireciona_para(html_txt, final) if len(html_txt) < 3000 and not pede_robo(html_txt, cab) else None
                if ir and ir != final and urllib.parse.urlsplit(ir).netloc == urllib.parse.urlsplit(final).netloc and agreg_permite(ir):
                    html_txt, cod, final, cab = pagina_resp(ir)
            except urllib.error.HTTPError as e:
                if e.code in (401, 403, 429):
                    motivo = f"o site recusou o acesso de programas (erro {e.code})"
                    break
                if e.code != 404:
                    motivo = f"o site respondeu com erro {e.code}"
                continue
            except Exception as e:  # noqa: BLE001
                motivo = f"o site não respondeu ({str(getattr(e, 'reason', e))[:60]})"
                continue
            if pede_robo(html_txt, cab):
                motivo = "o site pediu verificação de robô"
                break
            c_u, c_f = urllib.parse.urlsplit(u).path.rstrip("/"), urllib.parse.urlsplit(final).path.rstrip("/")
            if c_f != c_u and not any(b in c_f for b in bases):
                continue  # mandou para outra página (a do início, por exemplo): a loja não está neste site
            fs = folhetos_da_pagina(a, final, html_txt)
            if fs:
                achou = (final, fs)
                break
            if "/" + bases[-1] in u and not motivo:
                if len(html_txt.strip()) < 2048:
                    motivo = f"a página da loja veio vazia ({resumo_vazia(html_txt, cod, cab)})"
                    log(f"{a['nome']} {u}: página vazia, {resumo_vazia(html_txt, cod, cab)}: {html_txt[:300]!r}")
                else:
                    motivo = f"abri a página da loja ({len(html_txt) // 1024} KB), mas não achei folheto nela"
        memo[chave] = {"url": achou[0] if achou else None, "em": agora(), "motivo": motivo}
        if motivo and not achou:
            diag[a["nome"]] = motivo
            log(f"folheto de {loja['nome']} no {a['nome']}: {motivo}")
        if achou:
            validos = [f for f in achou[1] if (not f["ate"] or f["ate"] >= hoje) and (not f["de"] or f["de"] <= hoje)]
            if validos:
                return a, achou[0], validos
            diag[a["nome"]] = "só tem folheto vencido"
    return None, None, []


def precos_por_oferta(ofertas, nomes, ja):
    """Item da lista que bate com uma oferta do folheto vira preço da loja, sem perguntar à IA."""
    out = []
    for nome in nomes:
        if nome in ja:
            continue
        cands = []
        for o in ofertas:
            if not isinstance(o, dict) or not numero(o.get("preco")) or not combina(nome, str(o.get("produto") or "")):
                continue
            t = o.get("tamanho") if isinstance(o.get("tamanho"), dict) else {}
            tam = medida(t.get("quantidade"), t.get("unidade")) or tamanho_nome(o.get("produto") or "")
            if str(o.get("unidade") or "").lower() == "kg":
                tam = (1.0, "kg")
            cands.append({"nome": str(o.get("produto"))[:80], "preco": numero(o["preco"]), "de": None, "tam": tam, "link": None})
        if cands:
            ent, _ = montar_item(nome, {"_": cands})
            out.append({"produto": nome, "base": ent.get("base"), "precos": [{k: v for k, v in x.items() if k != "rede"} for x in ent["precos"]],
                        "tamanhos": [{k: v for k, v in x.items() if k != "rede"} for x in ent["tamanhos"]]})
    return out


def ler_folheto(loja, f, imgs, cfg):
    """Baixa as páginas do folheto e manda para a IA de fotos, até 8 por chamada. Devolve a resposta juntada."""
    dados = []
    for u in imgs[:MAX_PAGINAS]:
        try:
            dados.append(baixar(u, 6_000_000))
        except Exception:  # noqa: BLE001
            continue
    if not dados:
        raise ErroBusca("não consegui baixar as páginas do folheto")
    junto = {"validade": f.get("ate"), "ofertas": [], "lista": []}
    nomes = nomes_da_lista(cfg)
    for i in range(0, len(dados), 8):
        parte = dados[i:i + 8]
        BUSCA["etapa"] = f"folheto · {loja['nome']}" + (f" ({i // 8 + 1}ª parte)" if len(dados) > 8 else "")
        r = ia_com_arquivos(f"EconomIA: folheto {loja['nome']}", instrucoes_encarte(dict(loja, site=f["url"]), "", len(parte), cfg), parte)
        r = r if isinstance(r, dict) else {}
        junto["validade"] = junto["validade"] or data_ok(r.get("validade"))
        junto["ofertas"] += [o for o in r.get("ofertas") or [] if isinstance(o, dict)]
        for it in r.get("lista") or []:
            if isinstance(it, dict):
                original = casar_item(it, nomes)  # guarda pelo nome: a ordem da lista pode mudar
                if original:
                    junto["lista"].append(dict({k: v for k, v in it.items() if k != "item"}, produto=original))
    log(f"folheto de {loja['nome']}: {len(dados)} página(s), {len(junto['ofertas'])} oferta(s)")
    return junto


def resultado_folheto(loja, f, r, cfg):
    nomes = nomes_da_lista(cfg)
    r = dict(r)
    ja = {casar_item(it, nomes) for it in r.get("lista") or [] if isinstance(it, dict)}
    r["lista"] = list(r.get("lista") or []) + precos_por_oferta(r.get("ofertas") or [], nomes, ja)
    cat, parcial = normalizar(loja["categoria"], bruto_encarte({"nome": loja["nome"], "site": f["url"], "categoria": loja["categoria"]}, r), cfg)
    for l in cat["lojas"]:
        l["fontes"] = ["Encarte"]
        l["folheto"] = f["url"]
        if f.get("ate") or r.get("validade"):
            l["folheto_ate"] = f.get("ate") or r.get("validade")
    return cat, parcial


GENERICAS = {"supermercado", "supermercados", "mercado", "mercados", "hipermercado", "atacadista", "atacado", "atacarejo", "loja", "lojas",
             "unidade", "filial", "super", "comercial", "ltda", "de", "do", "da", "dos", "das", "e", "o", "a"}
MAX_FOLHETOS_NOVOS = 3  # lojas com folheto novo lido pela IA em cada busca (as outras ficam para a próxima)


def lojas_folheto(cfg, cats=None, categorias=None, ja=None):
    """As lojas físicas que o morador acompanha (e as que cadastrou) e que não têm preço pelo site: o folheto delas
    é procurado sozinho. Lojas com site de encarte próprio já têm o encarte lido por outro caminho."""
    lojas_cfg = cfg.get("lojas") or {}
    ignorar, manter = set(lojas_cfg.get("ignorar") or []), set(lojas_cfg.get("manter") or [])
    try:
        raio = float(cfg.get("raio_km") or 2)
    except (TypeError, ValueError):
        raio = 2.0
    adicionar = [a for a in lojas_cfg.get("adicionar") or [] if isinstance(a, dict) and texto(a.get("nome"), 60)]
    pular = {norm(n) for v in (ja or {}).values() for n in v}
    pular |= {norm(texto(a["nome"], 60).split(",")[0]) for a in adicionar if url_ok(a.get("site"))}
    out, vistos = [], set()

    def add(nome, cat):
        nome = (texto(nome, 60) or "").split(",")[0].strip()
        k = norm(nome)
        if k and k not in vistos and k not in pular and cat in ("mercados", "farmacias", "petshops") and (cats is None or cat in cats):
            vistos.add(k)
            out.append({"nome": nome, "categoria": cat})
    for l in lojas_cfg.get("folhetos") or []:  # versões antigas guardavam a lista à mão
        if isinstance(l, dict):
            add(l.get("nome"), l.get("categoria") or "mercados")
    for a in adicionar:
        add(a["nome"], a.get("categoria") or "mercados")
    if categorias is None:
        categorias = (ler_json(OFERTAS, {}) or {}).get("categorias") or []
    for c in categorias:
        if not isinstance(c, dict):
            continue
        nomes = {r.get("id"): r.get("nome") for r in c.get("redes") or [] if isinstance(r, dict)}
        for l in c.get("lojas") or []:
            if not isinstance(l, dict):
                continue
            rid, d = l.get("rede"), l.get("distancia_km")
            if rid in ignorar or (isinstance(d, (int, float)) and d > raio and rid not in manter):
                continue
            add(nomes.get(rid), c.get("id"))
    return out


def busca_folhetos(cfg, lojas, so_guardados=False, max_novas=MAX_FOLHETOS_NOVOS):
    """O folheto da semana das lojas. Devolve ([(categoria, parcial)], status por loja)."""
    if not lojas or not opcao("folhetos", cfg):
        return [], {}
    novas = 0
    resultado, status = [], {}
    with _folhetos_trava:
        cache = ler_json(FOLHETOS, {}) or {}
        itens = cache.setdefault("itens", {})
        hoje = hoje_br()
        velho = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(timespec="seconds")
        for k in [k for k, v in itens.items() if (v.get("ate") or "9999") < hoje or (not v.get("ate") and v.get("lido_em", "") < velho)]:
            itens.pop(k, None)
        vale = cache.setdefault("_vale", {})
        for k in [k for k, v in vale.items() if (v.get("ate") or "9999") < hoje]:
            vale.pop(k, None)
        descobertas = 0
        for loja in lojas:
            guardados = [dict(v, id=k) for k, v in itens.items() if norm(v.get("loja", "")) == norm(loja["nome"]) and v.get("r")]
            conhecida = any(k.endswith(":" + slug(loja["nome"], 40)) for k in cache.get("_lojas") or {})
            if not so_guardados and not conhecida:
                descobertas += 1
                if descobertas > 8:  # loja nova nos sites de encartes: até 8 por busca, as outras na próxima
                    continue
            if not so_guardados and novas >= max_novas and not guardados:
                continue  # folheto novo só para algumas lojas por busca: as outras ficam para a próxima
            if so_guardados or novas >= max_novas:  # só o que já foi lido, sem abrir os sites
                for f in guardados:
                    resultado.append(resultado_folheto(loja, f, f["r"], cfg))
                continue
            st = {"loja": loja["nome"], "fonte": None, "folhetos": 0, "lidos": 0, "guardados": 0, "ofertas": 0, "ate": None, "erro": None, "em": agora()}
            try:
                BUSCA["etapa"] = "folheto · " + loja["nome"]
                a, _, cands = achar_folhetos(loja, cache)
                if not cands:
                    st["erro"] = "Não achei folheto desta semana nos sites de encartes."
                else:
                    st["fonte"], st["folhetos"] = a["nome"], len(cands)
                    escolhidos = escolhe_folhetos(loja, a, cands, cache, cfg)
                    if not escolhidos:
                        st["erro"] = "Os folhetos desta semana não valem para a sua cidade."
                    for f in escolhidos:
                        guardado = itens.get(f["id"])
                        if guardado and guardado.get("r"):
                            r = guardado["r"]
                            st["guardados"] += 1
                        elif not ia_ligada(cfg):
                            continue
                        else:
                            imgs = paginas_folheto(a, f)
                            if not imgs:
                                st["erro"] = (f"Achei o folheto no {a['nome']}, mas só em miniatura, pequena demais para ler." if f.get("pequeno")
                                              else "Achei o folheto, mas não as páginas dele.")
                                continue
                            r = ler_folheto(loja, f, imgs, cfg)
                            novas += st["lidos"] == 0
                            itens[f["id"]] = {"loja": loja["nome"], "url": f["url"], "de": f.get("de"), "ate": f.get("ate") or r.get("validade"),
                                              "paginas": len(imgs), "lido_em": agora(), "r": r}
                            gravar_json(FOLHETOS, cache)
                            st["lidos"] += 1
                        cat, parcial = resultado_folheto(loja, f, r, cfg)
                        resultado.append((cat, parcial))
                        st["ofertas"] += len(cat["ofertas"])
                        st["ate"] = max(st["ate"] or "", f.get("ate") or (itens.get(f["id"]) or {}).get("ate") or "") or None
            except ErroBusca as e:
                st["erro"] = str(e)
            except Exception as e:  # noqa: BLE001
                st["erro"] = f"Erro inesperado: {e}"
                log(f"folheto de {loja['nome']}: {e}")
            if st["erro"] and not st["fonte"] and not st["ofertas"]:
                st["erro"] = None  # não está no Kimbino nem no Seus Folhetos: é o normal para muita loja
                st["sem_folheto"] = True
            status[norm(loja["nome"])] = st
            log(f"folheto de {loja['nome']}: " + ("não está nos sites de encartes" if st.get("sem_folheto") else st["erro"] or f"{st['fonte']}, {st['lidos']} lido(s) agora, {st['guardados']} guardado(s), {st['ofertas']} oferta(s)"))
        if status:
            cache["_status"] = dict(cache.get("_status") or {}, **status)
        gravar_json(FOLHETOS, cache)
    return resultado, status


def folhetos_painel(cfg):
    st = (ler_json(FOLHETOS, {}) or {}).get("_status") or {}
    return [dict(l, status=st.get(norm(l["nome"]))) for l in lojas_folheto(cfg)]


def juntar_folheto_status(rel, st):
    if st:
        atuais = {norm(x["loja"]): x for x in rel.get("folhetos") or []}
        atuais.update(st)
        rel["folhetos"] = list(atuais.values())


# ---------- Instagram: encartes que as lojas postam (API oficial, Business Discovery) ----------
# Com uma conta profissional do Instagram ligada a uma página do Facebook e uma chave da Meta, o add-on lê os posts
# públicos das contas comerciais das lojas. Post de oferta (pela legenda) dos últimos dias é lido uma vez pela IA de
# fotos e guardado até vencer, como o folheto. Raspar o Instagram sem a API não é permitido.
GRAPH = os.environ.get("OFERTAS_GRAPH", "https://graph.facebook.com/v26.0")
INSTAGRAM = os.path.join(DATA, "instagram.json")
INSTA_DIAS = 8
MAX_INSTA_NOVOS = 3
LEGENDA_OFERTA = re.compile(r"(?i)(oferta|promo|encarte|v[aá]lid|imbat|pre[cç]o|desconto|sald[aã]o|show de|feir[aã]o|"
                            r"ter[cç]a|quarta|quinta|sexta|fim de semana|semana|R\$|a[cç]ougue|hortifr|leve \d)")


def insta_chave():
    i = segredos().get("instagram") or {}
    return str(i.get("token") or "").strip() or None, str(i.get("ig_id") or "").strip() or None


def insta_pronto():
    t, ig = insta_chave()
    return bool(t and ig)


def insta_handle(u):
    """"https://www.instagram.com/mercado_boidourado/" ou "@mercado_boidourado" → "mercado_boidourado"."""
    t = str(u or "").strip()
    m = re.search(r"instagram\.com/([A-Za-z0-9._]{2,30})", t) or re.match(r"^@([A-Za-z0-9._]{2,30})$", t)
    if not m or m.group(1).lower() in ("p", "reel", "reels", "explore", "stories", "accounts", "tv"):
        return None
    return m.group(1).lower().rstrip(".")


def graph_get(caminho, params, token, timeout=25):
    q = urllib.parse.urlencode(dict(params, access_token=token))
    req = urllib.request.Request(f"{GRAPH}/{caminho.lstrip('/')}?{q}", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read(6_000_000).decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read(100_000).decode("utf-8") or "{}").get("error") or {}
        except (ValueError, OSError):
            err = {}
        c, msg = err.get("code"), str(err.get("message") or "")
        if c == 190:
            raise ErroBusca("A chave do Instagram venceu ou foi cancelada. Gere outra e cole em Mais › Integrações.") from e
        if c in (4, 17, 32, 613):
            raise ErroBusca("O Instagram pediu para esperar (limite de consultas). Tento de novo mais tarde.") from e
        if c == 110 or err.get("error_subcode") == 2207013 or "cannot find user" in msg.lower():
            raise ErroBusca("conta não encontrada ou não é comercial (a API só lê contas comerciais e de criador)") from e
        if c in (10, 200) or "permission" in msg.lower():
            raise ErroBusca("a chave não tem as permissões instagram_basic, instagram_manage_insights, pages_show_list e pages_read_engagement") from e
        raise ErroBusca(f"O Instagram recusou o pedido ({e.code}: {msg[:120]}).") from e


def insta_conta(token):
    """A conta profissional do Instagram ligada a uma página do Facebook da chave: (id, usuário)."""
    d = graph_get("me/accounts", {"fields": "name,instagram_business_account{id,username}", "limit": 50}, token)
    for pg in d.get("data") or []:
        ig = pg.get("instagram_business_account") or {}
        if ig.get("id"):
            return ig["id"], ig.get("username")
    return None, None


def insta_validade(token):
    try:
        d = (graph_get("debug_token", {"input_token": token}, token, timeout=15).get("data") or {})
    except ErroBusca:
        return ""
    exp = d.get("data_access_expires_at") if not d.get("expires_at") else d.get("expires_at")
    if d.get("expires_at") == 0:
        return " A chave não vence."
    if exp:
        dia = (datetime.fromtimestamp(int(exp), timezone.utc) - timedelta(hours=3)).strftime("%d/%m/%Y")
        return f" A chave vale até {dia}."
    return ""


def testar_instagram():
    token, ig = insta_chave()
    if not token:
        return {"ok": False, "msg": "Falta a chave do Instagram."}
    try:
        usuario = (segredos().get("instagram") or {}).get("usuario")
        if not ig:
            ig, usuario = insta_conta(token)
            if not ig:
                return {"ok": False, "msg": "A chave funciona, mas não achei conta profissional do Instagram ligada a uma página do Facebook. "
                                            "Ligue a conta à página (no app do Instagram: Configurações › Central de contas) e gere a chave de novo."}
            seg = segredos()
            seg["instagram"] = dict(seg.get("instagram") or {}, ig_id=ig, usuario=usuario)
            grava_segredos(seg)
        d = graph_get(ig, {"fields": "business_discovery.username(instagram){username,media_count}"}, token)
        if not (d.get("business_discovery") or {}).get("username"):
            return {"ok": False, "msg": "O Instagram não respondeu como esperado."}
    except ErroBusca as e:
        return {"ok": False, "msg": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "msg": f"Não consegui testar ({e})."}
    return {"ok": True, "msg": f"Pronta: conta @{usuario or '?'}. Consigo ler os posts das contas comerciais das lojas." + insta_validade(token)}


def insta_posts(handle, cache, forcar=False):
    """Posts recentes de uma conta comercial, guardados por 12 horas: (posts, erro)."""
    token, ig = insta_chave()
    contas = cache.setdefault("contas", {})
    c = contas.get(handle) or {}
    meio_dia = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(timespec="seconds")
    if c.get("em", "") >= meio_dia and not forcar:
        return c.get("posts") or [], c.get("erro")
    campos = ("business_discovery.username(" + handle + "){username,media.limit(12)"
              "{id,caption,media_type,media_url,permalink,timestamp,children{media_type,media_url}}}")
    try:
        d = graph_get(ig, {"fields": campos}, token)
        posts = (((d.get("business_discovery") or {}).get("media") or {}).get("data") or [])
        contas[handle] = {"em": agora(), "posts": posts}
        return posts, None
    except ErroBusca as e:
        contas[handle] = {"em": agora(), "posts": [], "erro": str(e)}
        return [], str(e)


def posts_encarte(posts):
    """Posts de oferta dos últimos dias, pela legenda: [{id, url, de, imgs, legenda}] (até 3)."""
    limite = (datetime.now(timezone.utc) - timedelta(days=INSTA_DIAS)).date().isoformat()
    out = []
    for p in posts:
        if not isinstance(p, dict) or p.get("media_type") not in ("IMAGE", "CAROUSEL_ALBUM"):
            continue
        ts = str(p.get("timestamp") or "")[:10]
        if not ts or ts < limite or not LEGENDA_OFERTA.search(str(p.get("caption") or "")):
            continue
        if p["media_type"] == "IMAGE":
            imgs = [p.get("media_url")]
        else:
            imgs = [c.get("media_url") for c in ((p.get("children") or {}).get("data") or []) if c.get("media_type") == "IMAGE"]
        imgs = [u for u in imgs if url_ok(u)][:6]
        if imgs:
            out.append({"id": str(p.get("id")), "url": p.get("permalink"), "de": ts, "imgs": imgs, "legenda": str(p.get("caption") or "")[:400]})
    return out[:3]


def lojas_instagram(cfg, cats=None, categorias=None):
    """As lojas que você acompanha e que têm Instagram (do mapa ou informado por você): [{nome, categoria, handle}]."""
    lojas_cfg = cfg.get("lojas") or {}
    ignorar, manter = set(lojas_cfg.get("ignorar") or []), set(lojas_cfg.get("manter") or [])
    try:
        raio = float(cfg.get("raio_km") or 2)
    except (TypeError, ValueError):
        raio = 2.0
    out, vistos = [], set()
    for a in lojas_cfg.get("adicionar") or []:
        h = insta_handle(a.get("site")) if isinstance(a, dict) else None
        if h and h not in vistos and (cats is None or a.get("categoria") in cats):
            vistos.add(h)
            out.append({"nome": texto(a.get("nome"), 60).split(",")[0].strip(), "categoria": a.get("categoria") or "mercados", "handle": h})
    if categorias is None:
        categorias = (ler_json(OFERTAS, {}) or {}).get("categorias") or []
    for c in categorias:
        if not isinstance(c, dict) or c.get("id") not in ("mercados", "farmacias", "petshops") or (cats and c["id"] not in cats):
            continue
        nomes = {r.get("id"): r.get("nome") for r in c.get("redes") or [] if isinstance(r, dict)}
        for l in c.get("lojas") or []:
            rid, d = l.get("rede"), l.get("distancia_km")
            h = insta_handle(l.get("social")) or insta_handle(l.get("instagram_perfil"))
            if not h or h in vistos or not nomes.get(rid) or rid in ignorar or (isinstance(d, (int, float)) and d > raio and rid not in manter):
                continue
            vistos.add(h)
            out.append({"nome": nomes[rid], "categoria": c["id"], "handle": h})
    return out


def resultado_instagram(loja, p, r, cfg):
    cat, parcial = resultado_folheto(loja, {"url": p["url"], "ate": p.get("ate")}, r, cfg)
    for l in cat["lojas"]:
        l["fontes"] = ["Instagram"]
        l["instagram"] = l.pop("folheto", None) or p["url"]
        l["instagram_ate"] = l.pop("folheto_ate", None)
    return cat, parcial


def busca_instagram(cfg, cats, ja, ler=True, max_novos=MAX_INSTA_NOVOS):
    """Encartes que as lojas postaram no Instagram. Devolve [(categoria, parcial)]."""
    if not insta_pronto() or not opcao("folhetos", cfg):
        return []
    lojas = lojas_instagram(cfg, cats)
    if not lojas:
        return []
    pular = {norm(n) for v in (ja or {}).values() for n in v}
    hoje = hoje_br()
    out, novos = [], 0
    cache = ler_json(INSTAGRAM, {}) or {}
    lidos = cache.setdefault("lidos", {})
    velho = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(timespec="seconds")
    for k in [k for k, v in lidos.items() if (v.get("ate") or "9999") < hoje or v.get("lido_em", "") < velho]:
        lidos.pop(k, None)
    for loja in lojas:
        if norm(loja["nome"]) in pular:
            continue  # já tem preço pelo site
        for k, v in lidos.items():
            if v.get("handle") == loja["handle"] and v.get("r") and (v.get("ate") or "9999") >= hoje:
                out.append(resultado_instagram(loja, {"url": v.get("url"), "ate": v.get("ate")}, v["r"], cfg))
        if not ler or not ia_ligada(cfg) or novos >= max_novos:
            continue
        BUSCA["etapa"] = "Instagram · " + loja["nome"]
        posts, erro = insta_posts(loja["handle"], cache)
        if erro:
            log(f"Instagram de {loja['nome']} (@{loja['handle']}): {erro}")
            continue
        for p in posts_encarte(posts):
            if p["id"] in lidos or novos >= max_novos:
                continue
            dados = []
            for u in p["imgs"]:
                try:
                    dados.append(baixar(u, 8_000_000))
                except Exception:  # noqa: BLE001
                    continue
            if not dados:
                continue
            BUSCA["etapa"] = "Instagram · " + loja["nome"] + " (lendo o encarte)"
            try:
                r = ia_com_arquivos(f"EconomIA: Instagram {loja['nome']}",
                                    instrucoes_encarte(dict(loja, site=p["url"]), "Legenda do post: " + p["legenda"], len(dados), cfg), dados)
            except ErroBusca as e:
                log(f"Instagram de {loja['nome']}: {e}")
                break
            novos += 1
            r = r if isinstance(r, dict) else {}
            nomes = nomes_da_lista(cfg)
            r["lista"] = [dict({k: v for k, v in it.items() if k != "item"}, produto=casar_item(it, nomes))
                          for it in r.get("lista") or [] if isinstance(it, dict) and casar_item(it, nomes)]
            ate = data_ok(r.get("validade"))
            vazio = not [o for o in r.get("ofertas") or [] if isinstance(o, dict)]
            vencido = bool(ate and ate < hoje)
            lidos[p["id"]] = {"handle": loja["handle"], "loja": loja["nome"], "url": p["url"], "de": p["de"],
                              "ate": ate or (datetime.fromisoformat(p["de"]) + timedelta(days=7)).date().isoformat(),
                              "lido_em": agora(), "r": None if (vazio or vencido) else r}
            gravar_json(INSTAGRAM, cache)
            log(f"Instagram de {loja['nome']}: post de {p['de']} " + ("sem ofertas" if vazio else "vencido" if vencido else f"{len(r.get('ofertas') or [])} oferta(s)"))
            if not vazio and not vencido:
                out.append(resultado_instagram(loja, dict(p, ate=lidos[p["id"]]["ate"]), r, cfg))
    gravar_json(INSTAGRAM, cache)
    return out


# ---------- primeiro o que não gasta IA ----------
def busca_scripts(cfg, cats, itens=None, ler_folhetos=True):
    """Busca direta nas lojas, Shopee pela API e folhetos (lidos uma vez por semana). Devolve (resultado, relatório)."""
    resultado, rel, ja = [], {}, {}
    locais = [c for c in cats if c in ("mercados", "farmacias", "petshops")]
    if locais and opcao("lojas_diretas", cfg):
        try:
            atualiza_diretas(cfg)
            d = busca_direta(cfg, itens, locais)
        except Exception as e:  # noqa: BLE001
            d = []
            log(f"busca direta: {e}")
        if d:
            resultado += d
            rel["diretas"] = sorted({r["nome"] for c, _ in d for r in c["redes"]})
            for c, _ in d:
                ja[c["id"]] = sorted(r["nome"] for r in c["redes"])
    if opcao("lojas_diretas", cfg):
        try:
            ca = busca_catalogos(cfg, itens, cats)
        except Exception as e:  # noqa: BLE001
            ca = []
            log(f"páginas de produto: {e}")
        if ca:
            resultado += ca
            rel["diretas"] = sorted(set(rel.get("diretas") or []) | {r["nome"] for c, _ in ca for r in c["redes"]})
            for c, _ in ca:
                ja[c["id"]] = sorted(set(ja.get(c["id"]) or []) | {r["nome"] for r in c["redes"]})
        try:
            bs = busca_sites(cfg, itens, cats)
        except Exception as e:  # noqa: BLE001
            bs = []
            log(f"busca do site: {e}")
        if bs:
            resultado += bs
            rel["diretas"] = sorted(set(rel.get("diretas") or []) | {r["nome"] for c, _ in bs for r in c["redes"]})
            for c, _ in bs:
                ja[c["id"]] = sorted(set(ja.get(c["id"]) or []) | {r["nome"] for r in c["redes"]})
        try:
            po = busca_paginas_ofertas(cfg, cats, ja, itens)
        except Exception as e:  # noqa: BLE001
            po = []
            log(f"ofertas do site: {e}")
        if po:
            resultado += po
            rel["diretas"] = sorted(set(rel.get("diretas") or []) | {r["nome"] for c, _ in po for r in c["redes"]})
            for c, _ in po:
                ja[c["id"]] = sorted(set(ja.get(c["id"]) or []) | {r["nome"] for r in c["redes"]})
    if "online" in cats and shopee_pronta():
        try:
            sh = busca_shopee(cfg, itens)
        except Exception as e:  # noqa: BLE001
            sh = []
            log(f"shopee: {e}")
        if sh:
            resultado += sh
            rel["shopee"] = sum(len(p) for _, p in sh)
            ja["online"] = sorted(set(ja.get("online") or []) | {"Shopee"})
    try:  # logo depois do site: o folheto das lojas que não têm preço por lá
        fo, st = busca_folhetos(cfg, lojas_folheto(cfg, cats, ja=ja), so_guardados=not ler_folhetos)
    except Exception as e:  # noqa: BLE001
        fo, st = [], {}
        log(f"folhetos: {e}")
    resultado += fo
    juntar_folheto_status(rel, st)
    try:
        ig = busca_instagram(cfg, cats, ja, ler=ler_folhetos)
    except Exception as e:  # noqa: BLE001
        ig = []
        log(f"Instagram: {e}")
    if ig:
        resultado += ig
        rel["instagram"] = sorted({r["nome"] for c, _ in ig for r in c["redes"]})
    return resultado, rel, ja


# ---------- lista de produtos do site (sitemap) e preço na página do produto ----------
# Para lojas cujo site não deixa programas usarem a busca (/api/), mas deixa abrir as páginas de produto: a lista de
# produtos que a própria loja publica no sitemap é baixada uma vez por dia, os itens da lista são achados pelo nome
# e o preço é lido na página de cada produto (dados schema.org). Sem IA. É o preço padrão do site.
CATALOGOS = os.path.join(DATA, "catalogos")
MAX_CATALOGOS = 6
PAGINAS_ITEM = 2
LD_JSON = re.compile(r"<script[^>]+application/ld\+json[^>]*>(.*?)</script>", re.S | re.I)


def arquivo_catalogo(origem):
    return os.path.join(CATALOGOS, slug(origem.split("://", 1)[-1], 60) + ".json")


def baixa_catalogo(origem, info):
    """Endereços das páginas de produto que a loja publica no sitemap. Baixa de novo uma vez por dia."""
    arq = arquivo_catalogo(origem)
    c = ler_json(arq, {}) or {}
    ontem = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(timespec="seconds")
    if c.get("em", "") >= ontem and "urls" in c:
        return c
    regras = info.get("regras") or []
    fila = list(info.get("sitemaps") or []) or [origem + "/sitemap.xml"]
    urls, vistos, total = [], set(), 0
    while fila and len(vistos) < 40 and total < 80 * 1024 * 1024:
        sm = fila.pop(0)
        if sm in vistos or not robots_permite(regras, urllib.parse.urlsplit(sm).path or "/"):
            continue
        vistos.add(sm)
        try:
            dado, _ = baixar(sm, 30 * 1024 * 1024, timeout=45)
        except Exception:  # noqa: BLE001
            continue
        if dado[:2] == b"\x1f\x8b":
            try:
                dado = gzip.decompress(dado)
            except OSError:
                continue
        total += len(dado)
        txt = dado.decode("utf-8", "ignore")
        locs = [html_mod.unescape(u) for u in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", txt)]
        if "<sitemapindex" in txt[:3000]:
            prod = [u for u in locs if re.search(r"product|produto", u, re.I)]
            fila += prod or [u for u in locs if not re.search(r"categor|brand|marca|institucional|blog|image", u, re.I)]
        else:
            outros = bool(re.search(r"categor|brand|marca|institucional|blog|image|bulario|receita|loja", sm, re.I))
            urls += [u for u in locs if re.search(r"/p/?$", u) or not outros]
    c = {"em": agora(), "urls": list(dict.fromkeys(urls))[:200_000], "precos": c.get("precos") or {}}
    aprende_nomes(texto_url(u) for u in c["urls"][:40_000])  # os nomes do catálogo ensinam como o varejo chama cada coisa
    os.makedirs(CATALOGOS, exist_ok=True)
    gravar_json(arq, c)
    log(f"lista de produtos de {origem}: {len(c['urls'])} produto(s)")
    return c


def texto_url(u):
    caminho = urllib.parse.unquote(urllib.parse.urlsplit(u).path).rstrip("/")
    if caminho.endswith("/p"):
        caminho = caminho[:-2]
    return re.sub(r"[-_]+", " ", caminho.rsplit("/", 1)[-1])


def procura_catalogo(urls, nome, n=PAGINAS_ITEM):
    """As páginas de produto cujo endereço tem as palavras do item, das mais justas para as mais longas."""
    cabs = [p[0] for p in (palavras_busca(a) for a in alternativas(nome)) if p]
    tipo = [(u, t) for u in urls for t in [texto_url(u)] if any(c[:4] in norm(t) for c in cabs)]  # só os do mesmo tipo passam pelo casamento
    achadas = [(len(t), u) for (u, t), ok in zip(tipo, casa_lista(nome, [t for _, t in tipo])) if ok]
    return [u for _, u in sorted(achadas)[:n]]


def produto_ld(x):
    """Um Product do schema.org: {nome, marca, preco, disponivel} ou None."""
    if not isinstance(x, dict) or "Product" not in str(x.get("@type")):
        return None
    of = x.get("offers") or {}
    ofs = of if isinstance(of, list) else [of]
    if isinstance(of, dict) and isinstance(of.get("offers"), list):
        ofs = of["offers"] or [of]
    precos, disp = [], False
    for o in ofs:
        if not isinstance(o, dict):
            continue
        v = numero(o.get("price")) or numero(o.get("lowPrice"))
        estoque = "outofstock" not in str(o.get("availability") or "").lower().replace(" ", "")
        if v and estoque:
            precos.append(v)
            disp = True
    if not precos and isinstance(of, dict) and not isinstance(of.get("offers"), list) and numero(of.get("lowPrice")) \
            and "outofstock" not in str(of.get("availability") or "").lower():
        precos, disp = [numero(of["lowPrice"])], True
    if not precos:
        return None
    marca = x.get("brand")
    marca = marca.get("name") if isinstance(marca, dict) else marca
    return {"nome": texto(x.get("name"), 100), "marca": texto(marca, 30), "preco": min(precos), "disponivel": disp}


def meta_tag(html_txt, nome):
    """O content de <meta property|name|itemprop="nome">, em qualquer ordem de atributos."""
    for m in re.finditer(r"<meta\b[^>]*>", html_txt, re.I):
        t = m.group(0)
        if re.search(r"""(?:property|name|itemprop)\s*=\s*["']""" + re.escape(nome) + r"""["']""", t, re.I):
            c = re.search(r"""content\s*=\s*(?:"([^"]*)"|'([^']*)')""", t, re.I)
            if c:
                return html_mod.unescape(c.group(1) if c.group(1) is not None else c.group(2)).strip()
    return None


def parece_produto(u):
    """Nota de quanto o endereço parece página de produto (e não categoria, marca ou página institucional)."""
    caminho, t = urllib.parse.urlsplit(u).path, texto_url(u)
    nota = 3 if re.search(r"/p/?$", caminho) else 0
    nota += 2 if re.search(r"(?i)\d+\s*(?:ml|g|kg|mg|mcg|l|un|unid|cps|caps|capsulas|comprimidos|cp)\b", t) else 0
    nota += 1 if len(t.split()) >= 4 else 0
    if re.search(r"(?i)categor|/marca|brand|institucional|blog|como-comprar|politica|contato|sobre|login|carrinho|minha-conta|busca", caminho):
        nota -= 5
    return nota


def preco_da_pagina(html_txt):
    """Nome, preço e se tem estoque, pelos dados schema.org da página do produto (ou pelas meta tags)."""
    for bloco in LD_JSON.findall(html_txt):
        try:
            d = json.loads(html_mod.unescape(bloco.strip()))
        except ValueError:
            continue
        itens = d if isinstance(d, list) else (d.get("@graph") or [d]) if isinstance(d, dict) else []
        for x in itens:
            r = produto_ld(x)
            if r:
                return r
    # meta tags de produto (Magazord e outras): o atributo content pode vir antes ou depois do property
    precos = [numero(meta_tag(html_txt, n)) for n in ("product:price:amount", "product:sale_price:amount", "og:price:amount", "og:price")]
    precos = [v for v in precos if v]
    if precos:
        disp = meta_tag(html_txt, "product:availability") or meta_tag(html_txt, "og:availability") or ""
        t = meta_tag(html_txt, "og:title") or (re.search(r"<h1[^>]*>(.*?)</h1>", html_txt, re.S | re.I) or [None, None])[1]
        return {"nome": texto(sem_tags(t), 100) if t else None, "marca": texto(meta_tag(html_txt, "product:brand"), 30),
                "preco": min(precos), "disponivel": not re.search(r"(?i)out ?of ?stock|oos|esgotado|indispon", disp)}
    # sem schema.org (lojas com página montada por JavaScript, como a da Cobasi): o produto de nome parecido com o título
    import difflib
    tit = re.search(r"""<meta[^>]+property=["']og:title["'][^>]*content=["']([^"']+)""", html_txt, re.I) \
        or re.search(r"<h1[^>]*>(.*?)</h1>", html_txt, re.S | re.I) or re.search(r"<title>(.*?)</title>", html_txt, re.S | re.I)
    titulo = texto(sem_tags(html_mod.unescape(tit.group(1))), 120) if tit else ""
    if not titulo or re.search(r"(?i)esgotado|indispon[ií]vel|avise-me quando chegar", sem_tags(html_txt)[:20000]):
        return None
    melhor = None
    for o in ofertas_json_embutido(html_txt) + ofertas_texto(html_txt):
        nota = difflib.SequenceMatcher(None, norm(titulo), norm(o["produto"])).ratio()
        if nota >= 0.6 and (not melhor or nota > melhor[0]):
            melhor = (nota, o)
    if melhor:
        return {"nome": titulo, "marca": None, "preco": melhor[1]["preco"], "disponivel": True}
    return None


def preco_produto(origem, cat, u):
    """Preço da página do produto, guardado por um dia."""
    ontem = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(timespec="seconds")
    g = (cat.get("precos") or {}).get(u)
    if g and g.get("em", "") >= ontem:
        return g.get("r")
    try:
        r = preco_da_pagina(pagina_txt(u))
        if r and not r.get("nome"):
            r["nome"] = texto_url(u).strip().capitalize()[:100]
    except Exception as e:  # noqa: BLE001
        log(f"página de produto {u}: {e}")
        r = None
    cat.setdefault("precos", {})[u] = {"em": agora(), "r": r}
    time.sleep(0.3)  # devagar, para não pesar no site da loja
    return r


def busca_catalogos(cfg, itens=None, cats=None):
    """Preço dos itens da lista nas lojas que só deixam abrir as páginas de produto. Devolve [(categoria, parcial)]."""
    nomes = (itens or nomes_da_lista(cfg))[:40]
    memo = ler_json(LOJAS_SITE, {}) or {}
    perto = lojas_perto_cat(cfg)
    lojas = [(o, m) for o, m in memo.items() if m.get("nome") and m.get("paginas") and not (m.get("vtex") and m.get("permite"))
             and not m.get("marketplace") and not e_marketplace(m["nome"])]  # o sitemap de marketplace tem milhões de páginas
    out = []
    for origem, m in lojas[:MAX_CATALOGOS]:
        cat_id = categoria_da_loja(m["nome"], perto)  # fora do raio: mercado que entrega
        if cats and cat_id not in cats:
            continue
        BUSCA["etapa"] = "lista de produtos · " + m["nome"]
        try:
            cat = baixa_catalogo(origem, m)
        except Exception as e:  # noqa: BLE001
            log(f"lista de produtos de {m['nome']}: {e}")
            continue
        if not cat.get("urls"):
            continue
        BUSCA["etapa"] = "preços no site · " + m["nome"]
        lista_bruta, n = [], 0
        for nome in nomes:
            cands = []
            for u in procura_catalogo(cat["urls"], nome):
                r = preco_produto(origem, cat, u)
                if not r or not r.get("disponivel") or not r.get("preco"):
                    continue
                pn = r.get("nome") or texto_url(u)
                tam = tamanho_nome(pn) or tamanho_nome(texto_url(u))
                curto = (r["marca"] + " " + fmt_base({"quantidade": tam[0], "unidade": tam[1]})) if r.get("marca") and tam else pn[:60]
                cands.append({"nome": pn, "curto": curto, "preco": r["preco"], "de": None, "tam": tam, "link": u})
            if cands:
                n += 1
                ent, _ = montar_item(nome, {m["nome"]: cands}, frete="carrinho" if cat_id == "online" else None)
                lista_bruta.append(ent)
        try:
            gravar_json(arquivo_catalogo(origem), cat)
        except OSError:
            pass
        log(f"site de {m['nome']}: {n} de {len(nomes)} item(ns) com preço pelas páginas de produto")
        if lista_bruta:
            lojas_b = [] if cat_id == "online" else [{"rede": m["nome"], "site": origem, "fontes": ["Site"]}]
            out.append(normalizar(cat_id, {"lojas": lojas_b, "cupons": [], "ofertas": [], "lista": lista_bruta, "_via": "site"},
                                  dict(cfg, lista=[{"produto": x} for x in nomes])))
    return out


# ---------- página de ofertas do site, lida sem IA ----------
# Muita farmácia pequena tem uma página com os produtos e os preços no próprio HTML ("Ofertas", "Comprar pelo WhatsApp"),
# sem sitemap nem busca. O texto da página é lido por regras: dados schema.org, dados da página (JSON) ou os cartões
# "nome do produto" + "R$ 0,00". Os itens da lista são achados pelo nome, como no folheto. Respeita o robots.txt.
PAGINAS_OF = os.path.join(DATA, "paginas_ofertas.json")
PRECO_BR = re.compile(r"R\$\s*(\d{1,3}(?:\.\d{3})+,\d{2}|\d+,\d{2})")
PARCELA = re.compile(r"(?i)(\b\d{1,2}\s*x\b|sem juros|parcela|/\s*m[eê]s)")
RUIDO_BLOCO = re.compile(r"(?i)(comprar|adicionar|carrinho|whatsapp|ver mais|ver todos|saiba mais|entrar|login|cadastr|cookie|aceitar|recusar|"
                         r"configurar|pol[ií]tica|termos|busque|buscar|frete|economize|desconto|cupom|esgotado|indispon[ií]vel|avise-me|"
                         r"copyright|direitos reservados|cnpj|telefone|hor[aá]rio|acima de)")
NOME_JSON = re.compile(r'"(?:name|nome|title|titulo|productName|produto|descricao)"\s*:\s*"((?:[^"\\]|\\.){6,140})"')
PRECO_JSON = re.compile(r'"(price|preco|valor|sellingPrice|salePrice|bestPrice|finalPrice|precoPor|preco_por|precoVenda|preco_venda|'
                        r'special_price|promotional_price|price_promotional)"\s*:\s*"?(\d+(?:[.,]\d{1,2})?)"?', re.I)


def parece_nome(b):
    if len(b) < 6 or len(b) > 140 or PRECO_BR.search(b) or RUIDO_BLOCO.search(b) or "~" in b:
        return False
    return len(re.findall(r"[A-Za-zÀ-ÿ]{2,}", b)) >= 2 and sum(ch.isdigit() for ch in b) <= len(b) / 3


def _ld_produtos(d, out, fundo=0):
    if fundo > 6:
        return
    if isinstance(d, list):
        for x in d:
            _ld_produtos(x, out, fundo + 1)
    elif isinstance(d, dict):
        r = produto_ld(d)
        if r and r.get("nome") and r.get("disponivel"):
            out.append({"produto": r["nome"], "preco": r["preco"]})
            return
        for k in ("@graph", "itemListElement", "item", "mainEntity"):
            if k in d:
                _ld_produtos(d[k], out, fundo + 1)


def ofertas_json_embutido(html_txt):
    """Produtos nos dados que a página traz em <script> (Next, Nuxt, lojas próprias): nome e preço vizinhos."""
    out = []
    for sc in re.findall(r"(?is)<script\b(?![^>]*ld\+json)[^>]*>(.*?)</script>", html_txt):
        if len(sc) < 50 or '"' not in sc:
            continue
        nomes = []
        for m in NOME_JSON.finditer(sc):
            try:
                n = json.loads('"' + m.group(1) + '"')
            except ValueError:
                n = m.group(1)
            n = texto(sem_tags(n), 120)
            if n and parece_nome(n):
                nomes.append((m.start(), m.end(), n))
        if not nomes:
            continue
        p1 = PRECO_JSON.search(sc)
        preco_antes = bool(p1 and p1.start() < nomes[0][0])  # {"price": 9.9, "name": "..."}: o preço vem antes do nome
        for i, (ini, fim, n) in enumerate(nomes):
            if preco_antes:
                janela = sc[max(nomes[i - 1][1] if i else 0, ini - 800):ini]
            else:
                janela = sc[fim:min(nomes[i + 1][0] if i + 1 < len(nomes) else len(sc), fim + 800)]
            precos = []
            for p in PRECO_JSON.finditer(janela):
                bruto = p.group(2)
                v = float(bruto.replace(",", "."))
                if not re.search(r"[.,]", bruto) and p.group(1).lower() in ("sellingprice", "bestprice"):
                    v /= 100  # VTEX: em centavos
                if 0.5 <= v <= 20000:
                    precos.append(round(v, 2))
            if precos:
                out.append({"produto": n, "preco": min(precos)})
    return out


def blocos_da_pagina(html_txt):
    t = re.sub(r"(?is)<(script|style|noscript|svg|head|template)\b[^>]*>.*?</\1>", " ", html_txt)
    t = re.sub(r"(?is)<(del|s|strike)\b[^>]*>(.*?)</\1>", lambda m: " ~" + re.sub(r"<[^>]+>", " ", m.group(2)) + "~ ", t)
    partes = [" ".join(html_mod.unescape(x).split()) for x in re.split(r"<[^>]+>", t)]
    s = "\n".join(x for x in partes if x)
    s = re.sub(r"R\$\s*\n\s*", "R$ ", s)  # <span>R$</span><span>159</span><span>,90</span>
    s = re.sub(r"(\d)\s*\n\s*(,\d{2})", r"\1\2", s)
    return s.split("\n")


def ofertas_texto(html_txt):
    """Cartões de produto no texto da página: um nome de produto e, logo depois, o preço (o riscado é o preço "de")."""
    out, nome, precos = [], None, []

    def fecha():
        if nome and precos:
            atuais = [v for v, r in precos if not r] or [v for v, r in precos]
            riscados = [v for v, r in precos if r]
            p = min(atuais)
            normal = max(riscados) if riscados and max(riscados) > p else max(atuais) if max(atuais) > p else None
            out.append({"produto": nome, "preco": p, "preco_normal": normal})
    for b in blocos_da_pagina(html_txt):
        m = PRECO_BR.search(b)
        if m:
            if PARCELA.search(b) or RUIDO_BLOCO.search(b):
                continue  # "3x de R$ 53,30", "frete grátis acima de R$ 99,00"
            antes = b[:m.start()].strip(" -–:|~")
            if parece_nome(antes) and not re.match(r"(?i)^(de|por|ou|apenas|a partir)\b", antes):
                fecha()
                nome, precos = antes, []
            if nome:
                riscado = "~" in b or bool(re.match(r"(?i)^\W*de\b", b))
                precos += [(numero(x.group(1)), riscado) for x in PRECO_BR.finditer(b) if numero(x.group(1))]
            continue
        if parece_nome(b):
            if precos:
                fecha()
                nome, precos = b, []
            elif nome and (b[:1].islower() or re.match(r"(?i)^(c/|com\b|cx|caixa|cont[eé]m|embalagem|\d)", b)) and len(nome) + len(b) < 140:
                nome = nome + " " + b  # "Dipirona 500 mg" + "caixa com 10 comprimidos"
            else:
                nome = b
    fecha()
    return out


def ofertas_da_pagina(html_txt):
    """Produtos e preços que a página mostra, sem IA."""
    out = []
    for bloco in LD_JSON.findall(html_txt):
        try:
            _ld_produtos(json.loads(html_mod.unescape(bloco.strip())), out)
        except ValueError:
            continue
    if len(out) < 3:
        out += ofertas_json_embutido(html_txt)
    if len(out) < 3:
        out += ofertas_texto(html_txt)
    vistos, final = set(), []
    for o in out:
        k = norm(o["produto"])
        if k and k not in vistos and o.get("preco") and 0.5 <= o["preco"] <= 20000:
            vistos.add(k)
            final.append({"produto": texto(o["produto"], 120), "preco": o["preco"], "preco_normal": o.get("preco_normal")})
    return final[:300]


def le_pagina_ofertas(url, regras, forcar=False):
    """(ofertas, links para páginas de ofertas do mesmo site). Guardado por 12 horas. None se o robots.txt não deixa."""
    sp = urllib.parse.urlsplit(url)
    if regras and not robots_permite(regras, (sp.path or "/") + (("?" + sp.query) if sp.query else "")):
        return None
    cache = ler_json(PAGINAS_OF, {}) or {}
    meio_dia = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(timespec="seconds")
    g = cache.get(url)
    if g and g.get("em", "") >= meio_dia and not forcar:
        return g.get("ofertas") or [], g.get("links") or []
    html_txt = pagina_txt(url)
    ofs = ofertas_da_pagina(html_txt)
    datas = [data_iso(m.group(1)) for m in re.finditer(r"(?i)v[aá]lid[oa]s?\b[^0-9<]{0,40}?(\d{1,2}/\d{1,2}/\d{2,4})", sem_tags(html_txt))]
    datas = [d for d in datas if d]
    if ofs and datas and max(datas) < hoje_br():
        log(f"ofertas de {url}: a página diz que valem até {max(datas)}, ficam de fora")
        ofs = []
    links = []
    for h in re.findall(r"""(?i)<a\b[^>]*href=["']([^"'#]+)""", html_txt):
        u = urllib.parse.urljoin(url, html_mod.unescape(h))
        su = urllib.parse.urlsplit(u)
        if su.netloc == sp.netloc and re.search(r"(?i)oferta|promo", su.path) and u.rstrip("/") != url.rstrip("/") and u not in links:
            links.append(u)
    velho = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(timespec="seconds")
    cache = {k: v for k, v in cache.items() if isinstance(v, dict) and v.get("em", "") >= velho}
    cache[url] = {"em": agora(), "ofertas": ofs, "links": links[:3]}
    gravar_json(PAGINAS_OF, cache)
    return ofs, links[:3]


def ofertas_do_site(site, info, forcar=False):
    """Ofertas da página do site (a que o morador informou, ou a inicial) e da página de ofertas ligada a ela."""
    regras = info.get("regras") or []
    r = le_pagina_ofertas(site, regras, forcar)
    if r is None:
        return None, []
    ofs, links = r
    lidas = [site]
    if links and len(ofs) < 60:
        r2 = le_pagina_ofertas(links[0], regras, forcar)
        if r2:
            vistos = {norm(o["produto"]) for o in ofs}
            ofs = ofs + [o for o in r2[0] if norm(o["produto"]) not in vistos]
            lidas.append(links[0])
    return ofs, lidas


BUSCAS_SITE = ["/pesquisa?terms={}", "/busca?q={}", "/search?q={}", "/busca?termo={}", "/pesquisa?q={}", "/busca/{}",
               "/catalogsearch/result/?q={}", "/search?type=product&q={}", "/{}?_q={}&map=ft"]
MAX_SITES_BUSCA = 6
ITENS_BUSCA_SITE = 15


def busca_do_site(origem, info, termo, forcar=False):
    """Usa a busca do próprio site, nos endereços que o robots.txt deixa, e lê os produtos com preço do resultado.
    O endereço que funcionou fica guardado (info["busca"]); sem nenhum, tenta de novo na semana seguinte."""
    regras = info.get("regras") or []
    tpl = info.get("busca")
    semana = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(timespec="seconds")
    if tpl:
        tentar = [tpl]
    elif info.get("sem_busca", "") >= semana and not forcar:
        return []
    else:
        tentar = BUSCAS_SITE
    q, q2 = urllib.parse.quote(termo), termo_nucleo(termo)
    for t in tentar:
        caminho = t.replace("{}", q)
        if not robots_permite(regras, caminho):
            continue
        try:
            html_txt = pagina_txt(origem + caminho)
        except Exception:  # noqa: BLE001
            continue
        todos = ofertas_da_pagina(html_txt)
        aprende_nomes([o["produto"] for o in todos])
        ofs = [o for o, ok in zip(todos, casa_lista(termo, [o["produto"] for o in todos])) if ok]
        if not ofs and q2 and robots_permite(regras, t.replace("{}", urllib.parse.quote(q2))):  # "álcool perfumado" → "álcool"
            try:
                html2 = pagina_txt(origem + t.replace("{}", urllib.parse.quote(q2)))
                todos2 = ofertas_da_pagina(html2)
                aprende_nomes([o["produto"] for o in todos2])
                ofs = [o for o, ok in zip(todos2, casa_lista(termo, [o["produto"] for o in todos2])) if ok]
            except Exception:  # noqa: BLE001
                ofs = []
        if ofs:
            info["busca"] = t
            info.pop("sem_busca", None)
            return ofs
    if not tpl:
        info["sem_busca"] = agora()
    return []


def busca_sites(cfg, itens=None, cats=None):
    """Itens da lista pela busca do próprio site das lojas onde ela funcionou no teste. Devolve [(categoria, parcial)]."""
    nomes = (itens or nomes_da_lista(cfg))[:ITENS_BUSCA_SITE]
    memo = ler_json(LOJAS_SITE, {}) or {}
    perto = lojas_perto_cat(cfg)
    out = []
    for origem, m in [(o, m) for o, m in memo.items() if m.get("busca") and m.get("nome")][:MAX_SITES_BUSCA]:
        cat_id = "online" if m.get("marketplace") else categoria_da_loja(m["nome"], perto)  # fora do raio: loja que entrega
        if cats and cat_id not in cats:
            continue
        BUSCA["etapa"] = "busca do site · " + m["nome"]
        lista_bruta = []
        for nome in nomes:
            try:
                ofs = [dict(o, _q=a) for a in alternativas(nome) for o in busca_do_site(origem, m, a)]  # "asa ou sobrecoxa": cada lado
            except Exception as e:  # noqa: BLE001
                log(f"busca do site de {m['nome']}: {e}")
                break
            time.sleep(0.4)  # devagar, para não pesar no site da loja
            cands = [{"nome": o["produto"], "preco": o["preco"], "de": o.get("preco_normal"), "tam": tamanho_nome(o["produto"]),
                      "link": origem + (m.get("busca") or "").replace("{}", urllib.parse.quote(o["_q"]))} for o in ofs[:8]]
            if cands:
                ent, _ = montar_item(nome, {m["nome"]: cands}, frete="carrinho" if cat_id == "online" else None)
                lista_bruta.append(ent)
        log(f"busca do site de {m['nome']}: {len(lista_bruta)} de {len(nomes)} item(ns) com preço")
        if lista_bruta:
            lojas_b = [] if cat_id == "online" else [{"rede": m["nome"], "site": origem, "fontes": ["Site"]}]
            out.append(normalizar(cat_id, {"lojas": lojas_b, "cupons": [], "ofertas": [], "lista": lista_bruta, "_via": "site"},
                                  dict(cfg, lista=[{"produto": x} for x in nomes])))
    return out


def busca_paginas_ofertas(cfg, cats, ja, itens=None):
    """Lojas cuja página do site mostra os preços (achadas no teste do Encontrar lojas): itens da lista e ofertas, sem IA."""
    fontes = ler_json(SONDA_FILE, {}) or {}
    memo = ler_json(LOJAS_SITE, {}) or {}
    nomes = (itens or nomes_da_lista(cfg))[:40]
    pular = {norm(n) for v in ja.values() for n in v}
    out, n = [], 0
    for cat_id, por in fontes.items():
        if cats and cat_id not in cats:
            continue
        for k, st in (por or {}).items():
            if not isinstance(st, dict) or st.get("como") != "ofertas_site" or not url_ok(st.get("url")) or k in pular or n >= 8:
                continue
            n += 1
            nome, url = st.get("nome") or k, st["url"]
            BUSCA["etapa"] = "ofertas do site · " + nome
            try:
                ofs, _ = ofertas_do_site(url, memo.get(origem_de(url)) or {})
            except Exception as e:  # noqa: BLE001
                log(f"ofertas do site de {nome}: {e}")
                continue
            if not ofs:
                continue
            lista = precos_por_oferta(ofs, nomes, set())
            marca = lambda x: dict(x, rede=nome, fonte=url)  # noqa: E731
            bruto = {"_via": "site", "cupons": [],
                     "lojas": [{"rede": nome, "endereco": None, "distancia_km": None, "fontes": ["Site"]}],
                     "ofertas": [dict(o, rede=nome, preco_oferta=o["preco"], fonte=url, encarte=True) for o in ofs[:20]],
                     "lista": [dict(it, precos=[marca(x) for x in it["precos"]], tamanhos=[marca(x) for x in it["tamanhos"]]) for it in lista]}
            out.append(normalizar(cat_id, bruto, dict(cfg, lista=[{"produto": x} for x in nomes])))
            log(f"ofertas do site de {nome}: {len(ofs)} produto(s) na página, {len(lista)} item(ns) da lista")
    return out


# ---------- lojas do raio pelo mapa: a casa do Home Assistant + OpenStreetMap (e Google Places, com chave) ----------
# A IA não tem mapa: ela acha as lojas que aparecem na busca e estima a distância. O mapa diz quais lojas existem
# no raio, com endereço e distância de verdade (para rede, a filial mais perto), e a IA só procura os preços.
LOJAS_MAPA = os.path.join(DATA, "lojas_mapa.json")
OVERPASS = os.environ.get("OFERTAS_OVERPASS", "https://overpass-api.de/api/interpreter")
GOOGLE_PLACES = os.environ.get("OFERTAS_GOOGLE_PLACES", "https://places.googleapis.com/v1/places:searchNearby")
GOOGLE_TEXTO = os.environ.get("OFERTAS_GOOGLE_TEXTO", "https://places.googleapis.com/v1/places:searchText")
CASA_TESTE = os.environ.get("OFERTAS_CASA")  # só para testes: "lat,lon" no lugar da zona Casa do HA
OSM_TIPOS = {
    "farmacias": ['nwr["amenity"="pharmacy"]', 'nwr["shop"="chemist"]'],
    "mercados": ['nwr["shop"~"^(supermarket|convenience|wholesale|greengrocer|butcher)$"]'],
    "petshops": ['nwr["shop"="pet"]', 'nwr["shop"="agrarian"]'],
}
GOOGLE_TIPOS = {"farmacias": ["pharmacy", "drugstore"], "mercados": ["supermarket", "grocery_store"], "petshops": ["pet_store"]}
# pet shop que vende remédio também é "pharmacy" no Google: o tipo principal e o nome dizem que não é farmácia
OUTRA_CATEGORIA = {"farmacias": {"pet_store", "veterinary_care"}, "mercados": {"pet_store", "veterinary_care", "pharmacy", "drugstore"}}
NOME_FORA = {"farmacias": re.compile(r"\b(pet|pets|petshop|vet|veterinari[ao]s?|animal|animais|agropecuari[ao]|agrovet\w*)\b"),
             "mercados": re.compile(r"\b(pet|pets|petshop|veterinari[ao]s?|agrovet\w*)\b")}
PALAVRAS_LOJA = {"farmacia", "farmacias", "drogaria", "drogarias", "droga", "supermercado", "supermercados", "mercado", "mercados",
                 "mercearia", "minimercado", "hipermercado", "atacadista", "atacado", "pet", "shop", "petshop", "loja", "lojas",
                 "super", "hiper", "de", "do", "da", "dos", "das", "e", "ltda", "me", "filial", "unidade"}


REDES_SOCIAIS = {"instagram.com": "o Instagram", "facebook.com": "o Facebook", "fb.com": "o Facebook", "wa.me": "o WhatsApp",
                 "whatsapp.com": "o WhatsApp", "linktr.ee": "um Linktree", "tiktok.com": "o TikTok", "youtube.com": "o YouTube",
                 "ifood.com.br": "o iFood", "rappi.com.br": "o Rappi", "business.site": "uma página do Google", "g.page": "uma página do Google"}


def rede_social(u):
    """"o Instagram" quando o "site" da loja no mapa é rede social, WhatsApp ou app de entrega (não tem preço para ler)."""
    if not url_ok(u):
        return None
    h = urllib.parse.urlsplit(u).netloc.lower().split(":")[0]
    return next((v for k, v in REDES_SOCIAIS.items() if h == k or h.endswith("." + k)), None)


def site_loja(u):
    return u if url_ok(u) and not rede_social(u) else None


def social_loja(u):
    return u if rede_social(u) else None


def da_categoria(cat, nome, primario=None):
    """A loja é mesmo desta categoria? ("Vanilla Pet Center" e "Farmácia Veterinária" não entram em farmácias.)"""
    if primario and primario in OUTRA_CATEGORIA.get(cat, ()):
        return False
    r = NOME_FORA.get(cat)
    return not (r and r.search(norm(nome)))


def casa(cfg=None):
    """(lat, lon) da zona Casa do Home Assistant."""
    if CASA_TESTE:
        a, b = CASA_TESTE.split(",")
        return float(a), float(b)
    z = ha_api("GET", "/states/zone.home") or {}
    at = z.get("attributes") or {}
    return float(at["latitude"]), float(at["longitude"])


def km_entre(a, b, c, d):
    import math
    r = 6371.0
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = math.radians(c - a), math.radians(d - b)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(h)), 1)


def chave_loja(nome):
    """"Droga Raia" e "Raia" viram "raia"; "Farmácia Preço Popular" vira "preco popular";
    "Supermercado Imperatriz - Joinville" vira "imperatriz" (o que vem depois do traço é filial, bairro ou cidade)."""
    base = re.split(r"\s+[-–|]\s+", str(nome or ""), maxsplit=1)[0]
    w = [x for x in norm(base).split() if x not in PALAVRAS_LOJA]
    if not w:
        w = [x for x in norm(nome).split() if x not in PALAVRAS_LOJA]
    return " ".join(w) or norm(nome)


def mesma_loja(a, b):
    ka, kb = chave_loja(a), chave_loja(b)
    return ka == kb or ka.startswith(kb + " ") or kb.startswith(ka + " ")


def mesmo_lugar(a, b, nome_a, nome_b):
    """Duas lojas no mesmo lugar (até 150 m) com nomes quase iguais são a mesma ("Impeatriz", erro de digitação no mapa)."""
    import difflib
    if a.get("lat") is None or b.get("lat") is None:
        return False
    if km_entre(a["lat"], a["lon"], b["lat"], b["lon"]) > 0.15:
        return False
    return difflib.SequenceMatcher(None, chave_loja(nome_a), chave_loja(nome_b)).ratio() >= 0.8


def google_chave():
    return str((segredos().get("google") or {}).get("key") or "").strip() or None


def osm_lojas(lat, lon, raio_m, cats):
    partes = "".join(f"{t}(around:{raio_m},{lat},{lon});" for c in cats for t in OSM_TIPOS.get(c, []))
    q = f"[out:json][timeout:25];({partes});out center tags;"
    req = urllib.request.Request(OVERPASS, data=urllib.parse.urlencode({"data": q}).encode(), method="POST",
                                 headers={"User-Agent": "EconomIA (add-on do Home Assistant)", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        d = json.loads(r.read(8_000_000).decode("utf-8") or "{}")
    out = []
    for e in d.get("elements") or []:
        t = e.get("tags") or {}
        nome = texto(t.get("name") or t.get("brand"), 60)
        la, lo = e.get("lat") or (e.get("center") or {}).get("lat"), e.get("lon") or (e.get("center") or {}).get("lon")
        if not nome or la is None or lo is None:
            continue
        cat = ("farmacias" if t.get("amenity") == "pharmacy" or t.get("shop") == "chemist"
               else "petshops" if t.get("shop") in ("pet", "agrarian") else "mercados")
        if not da_categoria(cat, nome):
            continue
        rua = ", ".join(x for x in [t.get("addr:street"), t.get("addr:housenumber")] if x)
        bairro = t.get("addr:suburb") or t.get("addr:neighbourhood")
        out.append({"nome": nome, "categoria": cat, "endereco": ", ".join(x for x in [rua, bairro] if x) or None,
                    "distancia_km": km_entre(lat, lon, float(la), float(lo)), "fonte": "OpenStreetMap",
                    "lat": round(float(la), 6), "lon": round(float(lo), 6),
                    "site": next((u for u in (t.get("website"), t.get("contact:website"), t.get("brand:website")) if site_loja(u)), None),
                    "social": next((u for u in (t.get("website"), t.get("contact:website"), t.get("contact:instagram")) if social_loja(u)), None)})
    return out


def google_lojas(lat, lon, raio_m, cats, chave):
    out = []
    for cat in cats:
        corpo = {"includedTypes": GOOGLE_TIPOS.get(cat, []), "maxResultCount": 20, "rankPreference": "DISTANCE", "languageCode": "pt-BR",
                 "locationRestriction": {"circle": {"center": {"latitude": lat, "longitude": lon}, "radius": float(raio_m)}}}
        if not corpo["includedTypes"]:
            continue
        req = urllib.request.Request(GOOGLE_PLACES, data=json.dumps(corpo).encode(), method="POST", headers={
            "Content-Type": "application/json", "X-Goog-Api-Key": chave,
            "X-Goog-FieldMask": "places.id,places.displayName,places.shortFormattedAddress,places.formattedAddress,places.location,places.businessStatus,places.websiteUri,places.primaryType"})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                d = json.loads(r.read(4_000_000).decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            try:
                msg = (json.loads(e.read(100_000).decode("utf-8") or "{}").get("error") or {}).get("message")
            except (ValueError, OSError):
                msg = None
            raise ErroBusca(f"O Google recusou a chave ({e.code}{': ' + str(msg)[:120] if msg else ''}).") from e
        for pl in d.get("places") or []:
            if pl.get("businessStatus") == "CLOSED_PERMANENTLY":
                continue
            nome = nome_bonito((pl.get("displayName") or {}).get("text"))
            loc = pl.get("location") or {}
            if not nome or loc.get("latitude") is None or not da_categoria(cat, nome, pl.get("primaryType")):
                continue
            out.append({"nome": nome, "categoria": cat, "endereco": texto(pl.get("shortFormattedAddress") or pl.get("formattedAddress"), 90),
                        "distancia_km": km_entre(lat, lon, loc["latitude"], loc["longitude"]), "fonte": "Google",
                        "lat": round(float(loc["latitude"]), 6), "lon": round(float(loc["longitude"]), 6), "place_id": texto(pl.get("id"), 200),
                        "site": site_loja(pl.get("websiteUri")), "social": social_loja(pl.get("websiteUri"))})
    return out


def nome_bonito(n):
    """"DROGARIA DROGÃO JOINVILLE" → "Drogaria Drogão Joinville" (nomes todos em maiúsculas no Google)."""
    n = texto(n, 60)
    if not n or n != n.upper() or not any(ch.isalpha() for ch in n):
        return n
    pequenas = {"de", "do", "da", "dos", "das", "e"}
    return " ".join(w.lower() if i and w.lower() in pequenas else w.capitalize() for i, w in enumerate(n.split()))


GOOGLE_BUSCA = {"farmacias": ["farmácia", "drogaria"], "mercados": ["supermercado", "mercado", "atacadista"], "petshops": ["pet shop", "agropecuária"]}
AGRO = re.compile(r"\bagro|\bra[cç](?:ao|ão|oes|ões)\b", re.I)
# atacarejo (Fort, Atacadão, Assaí, Komprão) às vezes é só "wholesaler"/"warehouse_store" no Google, sem "supermarket"
ATACAREJO = re.compile(r"\batacad\w*|\batacarejo|\bassai\b|\bmakro\b|\bkomprao\b")
ATACADO_FORA = re.compile(r"\b(materia\w*|constru\w*|tintas?|embalage\w*|pisos?|ferrage\w*|roupas?|confec\w*|moda|calcados?|autope\w*|pecas|eletro\w*|"
                          r"moveis|papelaria|bebidas|aviamentos|tecidos|brinquedos|cosmeticos|utilidades)\b")
TIPOS_ATACADO = {"wholesaler", "warehouse_store", "food_store", "discount_store"}


def google_post(url, corpo, chave, campos, timeout=25):
    req = urllib.request.Request(url, data=json.dumps(corpo).encode(), method="POST", headers={
        "Content-Type": "application/json", "X-Goog-Api-Key": chave, "X-Goog-FieldMask": campos})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read(4_000_000).decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            msg = (json.loads(e.read(100_000).decode("utf-8") or "{}").get("error") or {}).get("message")
        except (ValueError, OSError):
            msg = None
        raise ErroBusca(f"O Google recusou o pedido ({e.code}{': ' + str(msg)[:120] if msg else ''}).") from e


def google_varredura(lat, lon, raio_m, cats, chave, paginas=3):
    """Text Search por "farmácia", "supermercado"…: até 60 lugares por palavra, dentro do quadrado da casa.
    O Nearby para em 20; aqui a busca continua página a página enquanto vierem lojas dentro da distância."""
    import math
    dla = raio_m / 111_000.0
    dlo = raio_m / (111_000.0 * max(0.2, math.cos(math.radians(lat))))
    caixa = {"rectangle": {"low": {"latitude": lat - dla, "longitude": lon - dlo}, "high": {"latitude": lat + dla, "longitude": lon + dlo}}}
    campos = ("places.id,places.displayName,places.shortFormattedAddress,places.formattedAddress,places.location,"
              "places.businessStatus,places.websiteUri,places.types,places.primaryType,nextPageToken")
    out = []
    for cat in cats:
        tipos = set(GOOGLE_TIPOS.get(cat, []))
        for q in GOOGLE_BUSCA.get(cat, []):
            corpo = {"textQuery": q, "pageSize": 20, "languageCode": "pt-BR", "regionCode": "BR", "locationRestriction": caixa, "rankPreference": "DISTANCE"}
            for _ in range(paginas):
                d = google_post(GOOGLE_TEXTO, corpo, chave, campos)
                dentro = 0
                for pl in d.get("places") or []:
                    loc = pl.get("location") or {}
                    nome = nome_bonito((pl.get("displayName") or {}).get("text"))
                    if not nome or loc.get("latitude") is None or pl.get("businessStatus") == "CLOSED_PERMANENTLY":
                        continue
                    km = km_entre(lat, lon, loc["latitude"], loc["longitude"])
                    agro = cat == "petshops" and AGRO.search(norm(nome))
                    atac = (cat == "mercados" and ATACAREJO.search(norm(nome)) and not ATACADO_FORA.search(norm(nome))
                            and TIPOS_ATACADO & set(pl.get("types") or []))
                    if km * 1000 > raio_m or (tipos and not tipos & set(pl.get("types") or []) and not agro and not atac) or not da_categoria(cat, nome, pl.get("primaryType")):
                        continue
                    dentro += 1
                    out.append({"nome": nome, "categoria": cat, "endereco": texto(pl.get("shortFormattedAddress") or pl.get("formattedAddress"), 90),
                                "distancia_km": km, "fonte": "Google", "lat": round(float(loc["latitude"]), 6), "lon": round(float(loc["longitude"]), 6),
                                "place_id": texto(pl.get("id"), 200), "site": site_loja(pl.get("websiteUri")), "social": social_loja(pl.get("websiteUri"))})
                if not d.get("nextPageToken") or not dentro:
                    break
                corpo = dict(corpo, pageToken=d["nextPageToken"])
    return out


def google_site(nome, lat, lon, chave):
    """O site de uma loja pelo Google (Text Search), para as que o mapa trouxe sem site: {site, place_id} ou {}."""
    corpo = {"textQuery": nome, "maxResultCount": 3, "languageCode": "pt-BR",
             "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lon}, "radius": 500.0}}}
    req = urllib.request.Request(GOOGLE_TEXTO, data=json.dumps(corpo).encode(), method="POST", headers={
        "Content-Type": "application/json", "X-Goog-Api-Key": chave,
        "X-Goog-FieldMask": "places.id,places.displayName,places.location,places.websiteUri"})
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read(2_000_000).decode("utf-8") or "{}")
    for pl in d.get("places") or []:
        loc = pl.get("location") or {}
        if loc.get("latitude") is None or not mesma_loja(nome, (pl.get("displayName") or {}).get("text") or ""):
            continue
        if km_entre(lat, lon, loc["latitude"], loc["longitude"]) <= 0.4:
            return {"site": site_loja(pl.get("websiteUri")), "social": social_loja(pl.get("websiteUri")), "place_id": texto(pl.get("id"), 200)}
    return {}


def lojas_do_mapa(cfg, cats, forcar=False):
    """{categoria: [lojas]} do raio, da mais perto para a mais longe, uma por rede (a filial mais perto). Guardado por 7 dias."""
    cats = [c for c in cats if c in OSM_TIPOS]
    if not cats:
        return {}
    try:
        lat, lon = casa(cfg)
    except Exception as e:  # noqa: BLE001
        log(f"mapa: sem a localização da Casa no Home Assistant ({e})")
        return {}
    try:
        raio_m = int(float(cfg.get("raio_km") or 2) * 1000)
    except (TypeError, ValueError):
        raio_m = 2000
    g = google_chave()
    chave = f"v6,{lat:.4f},{lon:.4f},{raio_m},{','.join(sorted(cats))},{'g' if g else 'o'}"
    memo = ler_json(LOJAS_MAPA, {}) or {}
    semana = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(timespec="seconds")
    if not forcar and memo.get("chave") == chave and memo.get("em", "") >= semana:
        return memo.get("lojas") or {}
    todas, fontes = [], []
    try:
        todas += osm_lojas(lat, lon, raio_m, cats)
        fontes.append("OpenStreetMap")
    except Exception as e:  # noqa: BLE001
        log(f"mapa: OpenStreetMap sem resposta ({e})")
    if g:
        try:
            todas += google_lojas(lat, lon, raio_m, cats, g)
            fontes.append("Google")
        except Exception as e:  # noqa: BLE001
            log(f"mapa: {e}")
        try:
            todas += google_varredura(lat, lon, raio_m, cats, g)
            if "Google" not in fontes:
                fontes.append("Google")
        except Exception as e:  # noqa: BLE001
            log(f"mapa: busca por texto no Google: {e}")
    if not fontes:
        return memo.get("lojas") or {}
    lojas = {}
    for l in sorted(todas, key=lambda x: (x["fonte"] != "Google", x["distancia_km"])):
        lista = lojas.setdefault(l["categoria"], [])
        igual = next((x for x in lista if mesma_loja(x["nome"], l["nome"]) or mesmo_lugar(x, l, x["nome"], l["nome"])), None)
        if igual is None:
            lista.append(l)
        else:
            for k in ("site", "social"):
                if not igual.get(k) and l.get(k):
                    igual[k] = l[k]
        if igual is not None and l["distancia_km"] < igual["distancia_km"] - 0.05:  # a filial mais perto da mesma rede
            igual.update({k: l.get(k) for k in ("endereco", "distancia_km", "lat", "lon", "place_id")})
    for c in lojas:
        lojas[c] = sorted(lojas[c], key=lambda x: x["distancia_km"])[:30]
    mes = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(timespec="seconds")
    sites = {k: v for k, v in (memo.get("sites") or {}).items() if isinstance(v, dict) and v.get("em", "") >= mes}
    if g:  # lojas sem site (o OpenStreetMap quase nunca traz): pergunta ao Google, uma por uma, até 30; a resposta vale 30 dias
        n = 0
        for l in [x for c in lojas for x in lojas[c]]:
            if l.get("site") or site_da_rede(l["nome"]) or l.get("lat") is None:
                continue
            ks = f"{chave_loja(l['nome'])}@{l['lat']:.3f},{l['lon']:.3f}"
            if ks not in sites:
                if n >= 30:
                    continue
                n += 1
                try:
                    sites[ks] = dict(google_site(l["nome"], l["lat"], l["lon"], g), em=agora())
                except Exception as e:  # noqa: BLE001
                    log(f"mapa: site de {l['nome']} no Google: {e}")
                    break
            for k in ("site", "social", "place_id"):
                if sites[ks].get(k) and not l.get(k):
                    l[k] = sites[ks][k]
    gravar_json(LOJAS_MAPA, {"chave": chave, "em": agora(), "fontes": fontes, "lojas": lojas, "sites": sites})
    log("mapa: " + ", ".join(f"{len(v)} {CATEGORIAS[c]['nome'].lower()}" for c, v in lojas.items()) + f" no raio ({' e '.join(fontes)})")
    return lojas


def mapa_txt(cfg, cat_id):
    lojas = (cfg.get("_mapa") or {}).get(cat_id) or []
    if not lojas:
        return ""
    itens = [f"{l['nome']}" + (f" ({l['endereco']})" if l.get("endereco") else "") + f", {str(l['distancia_km']).replace('.', ',')} km" for l in lojas[:25]]
    return ("Lojas do raio, pelo mapa (são estas que existem perto da casa, com a distância certa): " + "; ".join(itens) + ". "
            "Procure o preço dos itens da lista nessas lojas e use esses nomes. Em \"lojas\", não repita as do mapa: traga só outras do raio que achar.")


def aplica_mapa(categorias, mapa, cfg, marcar_novas=False):
    """Endereço e distância de verdade nas lojas (filial mais perto) e as lojas do mapa que a busca não trouxe."""
    for cid in mapa:
        if mapa[cid] and cid in CATEGORIAS and not any(c.get("id") == cid for c in categorias):
            categorias.append({"id": cid, "nome": CATEGORIAS[cid]["nome"], "singular": CATEGORIAS[cid]["singular"],
                               "redes": [], "lojas": [], "cupons": [], "ofertas": [], "contas": []})
    for cat in categorias:
        lojas_m = mapa.get(cat.get("id")) or []
        for r in cat.get("redes") or []:  # "DROGARIA DROGÃO JOINVILLE", registrada antes assim, vira "Drogaria Drogão Joinville"
            if r.get("nome") and r["nome"] == r["nome"].upper():
                r["nome"] = nome_bonito(r["nome"])
                r["curto"] = r["nome"][:16]
        nomes = {r["id"]: r["nome"] for r in cat.get("redes") or []}
        if cat.get("lojas"):  # registradas antes pelo mapa, mas de outra categoria (pet shop nas farmácias): saem
            cat["lojas"] = [l for l in cat["lojas"] if not (set(l.get("fontes") or []) <= {"Mapa"}
                                                            and not da_categoria(cat.get("id"), nomes.get(l.get("rede"), "")))]
        if not lojas_m:
            continue
        usadas = set()
        for l in cat.get("lojas") or []:
            m = next((x for x in lojas_m if mesma_loja(x["nome"], nomes.get(l["rede"], ""))
                      or mesmo_lugar(x, l, x["nome"], nomes.get(l["rede"], ""))), None)
            if m:
                usadas.add(m["nome"])
                if m.get("fonte") == "Google" and not mesma_loja(m["nome"], nomes.get(l["rede"], "")):  # nome com erro de digitação no mapa
                    for r in cat.get("redes") or []:
                        if r.get("id") == l["rede"]:
                            r["nome"], r["curto"] = m["nome"], m["nome"][:16]
                    nomes[l["rede"]] = m["nome"]
                l["distancia_km"], l["endereco"] = m["distancia_km"], m.get("endereco") or l.get("endereco")
                l["fontes"] = sorted(set(l.get("fontes") or []) | {"Mapa"})
                l.update({k: m[k] for k in ("lat", "lon", "place_id", "social") if m.get(k)})
                if not site_loja(l.get("site")) and l.get("site"):
                    l["social"] = l.get("social") or social_loja(l["site"])
                    l.pop("site", None)
                if m.get("site") and not url_ok(l.get("site")):
                    l["site"] = m["site"]
        for m in lojas_m:
            if m["nome"] in usadas or any(mesma_loja(m["nome"], n) for n in nomes.values()):
                continue
            rid = cat["id"][:4] + "-" + slug(nome_direta(m["nome"]), 30)
            if rid in nomes:
                continue
            nomes[rid] = m["nome"]
            cat.setdefault("redes", []).append({"id": rid, "nome": m["nome"], "curto": m["nome"][:16]})
            nova = {"rede": rid, "distancia_km": m["distancia_km"], "horario": "", "endereco": m.get("endereco"), "fontes": ["Mapa"]}
            nova.update({k: m[k] for k in ("lat", "lon", "place_id", "site", "social") if m.get(k)})
            if marcar_novas:
                nova["nova"] = True  # registrada pelo Encontrar lojas: os preços vêm na próxima busca
            cat.setdefault("lojas", []).append(nova)
        # a mesma loja registrada duas vezes (nome com erro de digitação ou com " - Joinville"): fica a que tem mais fontes
        ficam = []
        for l in sorted(cat.get("lojas") or [], key=lambda x: (set(x.get("fontes") or []) <= {"Mapa"}, x.get("distancia_km") or 99)):
            dup = next((f for f in ficam if mesma_loja(nomes.get(f["rede"], ""), nomes.get(l["rede"], "")) and f["rede"] != l["rede"]
                        and set(l.get("fontes") or []) <= {"Mapa"}
                        or mesmo_lugar(f, l, nomes.get(f["rede"], ""), nomes.get(l["rede"], ""))), None)
            if dup is None:
                ficam.append(l)
            elif not dup.get("site") and l.get("site"):
                dup["site"] = l["site"]
        cat["lojas"] = sorted(ficam, key=lambda l: l["distancia_km"] if l.get("distancia_km") is not None else 99)


def atualizar_lojas_mapa(dado):
    """O botão Encontrar lojas: lê o mapa agora e registra as lojas do raio, sem buscar preços."""
    cfg = ler_config()
    try:
        if dado.get("raio_km"):
            cfg = dict(cfg, raio_km=float(dado["raio_km"]))
    except (TypeError, ValueError):
        pass
    cats = [c for c in (dado.get("categorias") or cfg.get("categorias") or list(CATEGORIAS)) if c in OSM_TIPOS]
    if not cats:
        return {"ok": False, "msg": "Marque farmácias, mercados ou pet shops."}
    try:
        casa(cfg)
    except Exception:  # noqa: BLE001
        return {"ok": False, "msg": "Não achei a localização da Casa no Home Assistant. Confira em Configurações › Sistema › Geral."}
    mapa = lojas_do_mapa(cfg, cats, forcar=True)
    if not any(mapa.values()):
        return {"ok": False, "msg": "O mapa não respondeu agora ou não achou lojas nessa distância. Tente de novo em alguns minutos ou aumente a distância."}
    mesclar_resultado([], cfg, mapa=mapa, novas_lojas=True)
    try:
        localiza_sem_local(cfg)
    except Exception as e:  # noqa: BLE001
        log(f"lojas sem localização: {e}")
    if not SONDA["rodando"]:
        threading.Thread(target=sonda_lojas, args=(cfg,), daemon=True).start()
    partes = [f"{len(v)} {CATEGORIAS[c]['nome'].lower()}" for c, v in mapa.items() if v]
    txt = partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " e " + partes[-1]
    fontes = (ler_json(LOJAS_MAPA, {}) or {}).get("fontes") or []
    raio = str(cfg.get("raio_km") or 2).replace(".0", "")
    return {"ok": True, "msg": f"Achei {txt} até {raio} km ({' e '.join(fontes)}).",
            "lojas": {c: len(v) for c, v in mapa.items()}, "teste": True}


LOCAIS = os.path.join(DATA, "locais.json")


def localiza_sem_local(cfg, maximo=10):
    """Loja física sem localização (cadastrada à mão, ou que veio de um site): o Google diz onde fica a filial mais perto
    (nome parecido, até 20 km). Achada, ganha endereço e distância; senão continua sem localização, e conta como online.
    A resposta fica guardada por 30 dias, também o "não achei"."""
    chave = google_chave()
    if not chave:
        return 0
    try:
        lat, lon = casa(cfg)
    except Exception:  # noqa: BLE001
        return 0
    cache = ler_json(LOCAIS, {}) or {}
    mes = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(timespec="seconds")
    cidade = ((ler_json(FOLHETOS, {}) or {}).get("_cep") or {}).get("cidade") or ""
    achadas, consultas = 0, 0
    with _mescla_trava:
        of = ler_json(OFERTAS, {}) or {}
        for c in of.get("categorias") or []:
            if not isinstance(c, dict) or c.get("id") not in ("mercados", "farmacias", "petshops"):
                continue
            nomes = {r.get("id"): r.get("nome") for r in c.get("redes") or [] if isinstance(r, dict)}
            for l in c.get("lojas") or []:
                if not isinstance(l, dict) or l.get("distancia_km") is not None or l.get("lat") is not None or l.get("place_id") or not nomes.get(l.get("rede")):
                    continue
                nome = nomes[l["rede"]]
                g = cache.get(norm(nome))
                if not g or g.get("em", "") < mes:
                    if consultas >= maximo:
                        continue
                    consultas += 1
                    g = {"em": agora()}
                    try:
                        corpo = {"textQuery": f"{nome} {cidade}".strip(), "maxResultCount": 5, "languageCode": "pt-BR", "regionCode": "BR",
                                 "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lon}, "radius": 20000.0}}}
                        d = google_post(GOOGLE_TEXTO, corpo, chave, "places.id,places.displayName,places.shortFormattedAddress,places.location,places.businessStatus")
                    except Exception as e:  # noqa: BLE001
                        log(f"onde fica {nome}: {e}")
                        continue
                    melhor = None
                    for pl in d.get("places") or []:
                        loc = pl.get("location") or {}
                        if loc.get("latitude") is None or pl.get("businessStatus") == "CLOSED_PERMANENTLY" \
                                or not mesma_loja(nome, (pl.get("displayName") or {}).get("text") or ""):
                            continue
                        km = km_entre(lat, lon, loc["latitude"], loc["longitude"])
                        if km <= 20 and (not melhor or km < melhor["distancia_km"]):
                            melhor = {"distancia_km": km, "lat": round(float(loc["latitude"]), 6), "lon": round(float(loc["longitude"]), 6),
                                      "endereco": texto(pl.get("shortFormattedAddress"), 90), "place_id": texto(pl.get("id"), 200)}
                    g.update(melhor or {"nada": True})
                    cache[norm(nome)] = g
                if g.get("nada") or g.get("lat") is None:
                    continue
                l.update({k: g[k] for k in ("distancia_km", "lat", "lon", "endereco", "place_id") if g.get(k) is not None})
                l["fontes"] = sorted(set(l.get("fontes") or []) | {"Mapa"})
                achadas += 1
        if achadas:
            gravar_json(OFERTAS, of)
    gravar_json(LOCAIS, cache)
    if consultas or achadas:
        log(f"lojas sem localização: {achadas} achada(s) no Google, {consultas} consulta(s)")
    return achadas


# ---------- teste de preço de cada loja (no Encontrar lojas): o que funciona sem IA e o que não ----------
SONDA_FILE = os.path.join(DATA, "fontes_preco.json")
SONDA = {"rodando": False, "atual": 0, "total": 0, "loja": None, "terminou_em": None, "resumo": None}
TERMO_TESTE = {"farmacias": "dipirona", "mercados": "leite", "petshops": "ração"}


def chave_direta(origem):
    for k, v in todas_diretas().items():
        if origem_de(v.get("site") or "") == origem:
            return k
    return None


def lojas_acompanhadas(cfg, categorias):
    lojas_cfg = cfg.get("lojas") or {}
    ignorar, manter = set(lojas_cfg.get("ignorar") or []), set(lojas_cfg.get("manter") or [])
    try:
        raio = float(cfg.get("raio_km") or 2)
    except (TypeError, ValueError):
        raio = 2.0
    out = []
    for c in categorias:
        if not isinstance(c, dict) or c.get("id") not in TERMO_TESTE:
            continue
        nomes = {r.get("id"): r.get("nome") for r in c.get("redes") or [] if isinstance(r, dict)}
        for l in c.get("lojas") or []:
            rid, d = l.get("rede"), l.get("distancia_km")
            if not nomes.get(rid) or rid in ignorar or (isinstance(d, (int, float)) and d > raio and rid not in manter):
                continue
            out.append((c["id"], rid, nomes[rid], l))
    return out


def testa_preco_loja(cat_id, nome, l, memo, cidade, cache_f, cfg, buscas_folheto, forcar=False):
    """Tenta um preço de exemplo sem IA e diz, passo a passo, o que funcionou e o que não."""
    termo = TERMO_TESTE.get(cat_id, "leite")
    st = {"como": None, "exemplo": None, "site": None, "passos": [], "em": agora(), "nome": nome}
    if l.get("_site_ia"):
        st["site_url"] = l["_site_ia"]
    manual = next((a["site"] for a in ((cfg.get("lojas") or {}).get("adicionar") or [])
                   if isinstance(a, dict) and url_ok(a.get("site")) and texto(a.get("nome"), 60)
                   and mesma_loja(texto(a["nome"], 60).split(",")[0], nome)), None)
    social_manual = manual if manual and rede_social(manual) else None
    if social_manual:
        manual = None
    site = manual or site_loja(l.get("site")) or site_da_rede(nome, cidade) or l.get("_site_ia")
    if site:
        o = origem_de(site)
        st["site"] = o.split("://", 1)[-1].replace("www.", "")
        k0 = chave_direta(o)
        m = {"vtex": True, "permite": True} if k0 and todas_diretas()[k0].get("fixa") else memo.get(o) or {}
        if forcar and not (k0 and todas_diretas()[k0].get("fixa")):
            m = {}
        if not m or m.get("sem_resposta"):  # no Encontrar lojas, site que falhou é testado de novo na hora
            m = memo[o] = dict(testa_site(o, cfg.get("cep")), nome=nome, categoria=cat_id)
        if m.get("sem_resposta"):
            st["passos"].append(f"✗ O site {st['site']} {m.get('erro') or 'não respondeu'}. Tento de novo amanhã.")
        elif m.get("vtex") and m.get("permite"):
            k = chave_direta(o)
            if not k:
                VTEX_ACHADAS[slug(nome, 30)] = {"nome": nome, "site": o, "categoria": cat_id}
                k = slug(nome, 30)
            try:
                reg, unidade = regiao_direta(k, cfg.get("cep"))
            except Exception as e:  # noqa: BLE001
                reg, unidade = None, None
                st["passos"].append(f"✗ O site {st['site']} não disse qual loja atende o seu CEP ({str(e)[:60]}).")
            if reg:
                st["passos"].append(f"✓ Site com busca direta, loja {unidade or 'do seu CEP'}.")
                try:
                    cands = [c for c in busca_vtex(k, termo, reg) if combina(termo, c["busca_em"])]
                except Exception:  # noqa: BLE001
                    cands = []
                if cands:
                    c = min(cands, key=lambda x: x["preco"])
                    st.update(como="site", exemplo=f"{c['nome'][:45]} por {br_preco(c['preco'])}")
                    st["passos"].append(f"✓ Achei \"{termo}\" no site: {st['exemplo']}.")
                else:
                    st["passos"].append(f"✗ A busca do site não trouxe \"{termo}\" com estoque.")
            elif reg is None and not st["passos"]:
                st["passos"].append(f"✗ O site {st['site']} não entrega no seu CEP.")
        elif not m.get("paginas"):
            st["passos"].append(f"✗ O site {st['site']} pede para programas não consultarem os preços.")
        else:
            try:
                ofs_b = busca_do_site(o, m, termo, forcar)
            except Exception:  # noqa: BLE001
                ofs_b = []
            if ofs_b:
                ex = min(ofs_b, key=lambda x: x["preco"])
                st.update(como="busca_site", exemplo=f"{ex['produto'][:45]} por {br_preco(ex['preco'])}")
                st["passos"].append(f"✓ A busca do site traz os preços (sem IA): \"{termo}\", {st['exemplo']}.")
            else:
                st["passos"].append("✗ Não achei uma busca do site que mostre os preços para programas.")
        if not st["como"] and m and not m.get("sem_resposta") and not (m.get("vtex") and m.get("permite")) and m.get("paginas"):
            try:
                cat = baixa_catalogo(o, m)
            except Exception:  # noqa: BLE001
                cat = {"urls": []}
            if not cat.get("urls"):
                st["passos"].append(f"✗ O site {st['site']} não publica a lista de produtos (sitemap).")
            else:
                st["passos"].append(f"✓ Lista de produtos do site: {len(cat['urls'])} páginas.")
                achou = None
                for u in procura_catalogo(cat["urls"], termo, 3):
                    r = preco_produto(o, cat, u)
                    if r and r.get("preco") and r.get("disponivel"):
                        achou = r
                        break
                try:
                    gravar_json(arquivo_catalogo(o), cat)
                except OSError:
                    pass
                if not achou:  # a loja pode não vender o item de exemplo (cama, roupa de pet): tenta outros produtos
                    tentadas = set(procura_catalogo(cat["urls"], termo, 3))
                    resto = [x for x in cat["urls"] if x not in tentadas]
                    # o sitemap pode começar pelas categorias: vão primeiro os endereços com cara de produto
                    for u in sorted(resto[:5000], key=parece_produto, reverse=True)[:4]:
                        r = preco_produto(o, cat, u)
                        if r and r.get("preco") and r.get("disponivel"):
                            achou = r
                            st["passos"].append(f"Não achei \"{termo}\" no site; testei outro produto.")
                            break
                    try:
                        gravar_json(arquivo_catalogo(o), cat)
                    except OSError:
                        pass
                if achou:
                    st.update(como="paginas", exemplo=f"{(achou.get('nome') or termo)[:40]} por {br_preco(achou['preco'])}")
                    st["passos"].append(f"✓ Preço lido na página do produto: {st['exemplo']}.")
                else:
                    st["passos"].append("✗ Não consegui ler o preço nas páginas de produto do site.")
            if not st["como"]:  # sem lista de produtos: os preços que a própria página do site mostra
                pag = manual or site
                try:
                    ofs, lidas = ofertas_do_site(pag if urllib.parse.urlsplit(pag).path not in ("", "/") else o + "/", m, forcar)
                except Exception as e:  # noqa: BLE001
                    ofs, lidas = [], []
                    st["passos"].append(f"✗ Não consegui abrir a página do site ({str(e)[:60]}).")
                if ofs is None:
                    st["passos"].append("✗ O site pede para programas não lerem essa página.")
                elif ofs:
                    alvo = next((x for x in ofs if combina(termo, x["produto"])), None)
                    ex = alvo or ofs[0]
                    st.update(como="ofertas_site", url=lidas[0], exemplo=f"{ex['produto'][:45]} por {br_preco(ex['preco'])}")
                    st["passos"].append(f"✓ A página do site mostra {len(ofs)} produto(s) com preço, lidos sem IA" + (f" ({len(lidas)} páginas)" if len(lidas) > 1 else "") + ".")
                    st["passos"].append(f"✓ Achei \"{termo}\": {st['exemplo']}." if alvo else
                                        f"Não tem \"{termo}\" nas ofertas de hoje. A cada busca, os itens da sua lista são procurados nelas.")
                elif lidas:
                    st["passos"].append(f"✗ Não achei preços no texto da página {lidas[0].split('://', 1)[-1][:50]} (o site monta os preços no navegador).")
    elif rede_social(social_manual or l.get("social") or l.get("site")):
        u = social_manual or l.get("social") or l.get("site")
        if not insta_handle(u):
            st["passos"].append(f"✗ O site desta loja no mapa é {rede_social(u)} ({u.split('://', 1)[-1][:40]}), sem preços para ler.")
    else:
        st["passos"].append("✗ O mapa não traz o site desta loja." + ("" if ia_ligada(cfg) or brave_chave() else
                                                                        " Com a chave do Brave em Integrações (ou a IA ligada), o app procura o site."))
    h = insta_handle(social_manual) or insta_handle(l.get("social"))
    if h and not st["como"]:
        st["instagram"] = h
        if insta_pronto():
            cache_i = ler_json(INSTAGRAM, {}) or {}
            posts, erro = insta_posts(h, cache_i, forcar)
            gravar_json(INSTAGRAM, cache_i)
            lido = [v for v in (cache_i.get("lidos") or {}).values()
                    if v.get("handle") == h and v.get("r") and (v.get("ate") or "9999") >= hoje_br()]
            if lido:
                st["como"] = "instagram"
                st["passos"].append(f"✓ Encarte do Instagram (@{h}) já lido, guardado até {datetime.fromisoformat(max(v['ate'] for v in lido)).strftime('%d/%m')}.")
            elif erro:
                st["passos"].append(f"✗ Instagram @{h}: {erro}.")
            else:
                enc = posts_encarte(posts)
                if enc:
                    st["como"] = "instagram_novo"
                    st["passos"].append(f"✓ Instagram @{h}: post de oferta de {datetime.fromisoformat(enc[0]['de']).strftime('%d/%m')}"
                                        + ("; a IA lê na próxima busca." if ia_ligada(cfg) else "; ler o post precisa da IA."))
                else:
                    st["passos"].append(f"✗ Instagram @{h}: nenhum post de oferta nos últimos {INSTA_DIAS} dias.")
        else:
            st["passos"].append(f"Tem Instagram (@{h}): ligue o Instagram em Mais › Integrações para ler os encartes.")
    if not st["como"]:
        guardados = [v for v in (cache_f.get("itens") or {}).values() if norm(v.get("loja", "")) == norm(nome) and v.get("r")]
        if guardados:
            st["como"] = "folheto"
            st["passos"].append("✓ Folheto da semana já lido, guardado até vencer.")
        elif buscas_folheto[0] < 8:
            buscas_folheto[0] += 1
            if forcar:  # procura a loja de novo nos sites de encartes, sem a memória de "não tem"
                for k in [k for k in (cache_f.get("_lojas") or {}) if k.endswith(":" + slug(nome, 40))]:
                    cache_f["_lojas"].pop(k, None)
            alvo_f = {"nome": nome, "categoria": cat_id}
            try:
                a, _, cands = achar_folhetos(alvo_f, cache_f)
            except Exception:  # noqa: BLE001
                a, cands = None, []
            diag_f = alvo_f.get("_diag") or {}
            if cands:
                st["como"] = "folheto_novo"
                st["passos"].append(f"✓ Tem folheto da semana no {a['nome']}" + ("; a IA lê na próxima busca." if ia_ligada(cfg) else "; ler o folheto precisa da IA."))
            else:
                sem = [x["nome"] for x in AGREGADORES if x["nome"] not in diag_f]
                txt = ("✗ Sem folheto no " + ", ".join(sem[:-1]) + (" e " if len(sem) > 1 else "") + sem[-1]) if sem else "✗ Sem folheto"
                txt += "".join(f"; {k}: {v}" for k, v in diag_f.items())
                st["passos"].append(txt + ".")
    if not st["como"]:
        st["como"] = "ia" if ia_ligada(cfg) else "nenhum"
        st["passos"].append("Preço só pela busca na web com IA." if ia_ligada(cfg) else "✗ Sem IA, não há de onde tirar o preço desta loja.")
    return st


SITES_IA = os.path.join(DATA, "sites_ia.json")


def instrucoes_sites(lojas, cidade, uf):
    itens = [f"{i}) {l['nome']}" + (f" ({l['endereco']})" if l.get("endereco") else "") for i, l in enumerate(lojas, 1)]
    onde = f"{cidade} ({uf})" if cidade else "a cidade do morador"
    return f"""Use a busca na web agora e ache o site oficial destas lojas de {onde}, no Brasil: {'; '.join(itens)}.
Para cada uma, o endereço do site da própria loja, de preferência a página de ofertas ou a loja online com preços. Não vale Instagram, Facebook, WhatsApp, iFood, Rappi, Google Maps, guias ou listas de empresas, nem marketplace. Se a loja não tiver site, null. Não invente.
Responda somente com um objeto JSON, sem texto antes ou depois: {{"lojas": [{{"n": 1, "site": "https://... ou null"}}]}}"""


BRAVE = os.environ.get("OFERTAS_BRAVE", "https://api.search.brave.com/res/v1/web/search")
# resultados que não são o site da própria loja
NAO_SITE = ("google.", "facebook.", "instagram.", "linkedin.", "youtube.", "tiktok.", "twitter.", "x.com", "wa.me", "whatsapp.",
            "ifood.", "rappi.", "mercadolivre.", "olx.", "shopee.", "amazon.", "magazineluiza.", "americanas.", "aliexpress.",
            "guiamais.", "apontador.", "telelistas.", "cnpj", "econodata.", "casadosdados.", "solutudo.", "cylex", "hotfrog.",
            "tiendeo.", "kimbino.", "seusfolhetos.", "portafolhetos.", "catalogosofertas.", "reclameaqui.", "yelp.", "tripadvisor.",
            "foursquare.", "wikipedia.", "indeed.", "glassdoor.", "infojobs.", "vagas.", "catho.", "jusbrasil.", "gov.br",
            "linktr.ee", "keepo.bio", "listamais.", "encontra", "brasilempresas", "empresasdobrasil", "consultasocio", "waze.")


def brave_chave():
    return str((segredos().get("brave") or {}).get("key") or "").strip() or None


def brave_busca(q, chave, n=10):
    req = urllib.request.Request(BRAVE + "?" + urllib.parse.urlencode({"q": q, "country": "BR", "search_lang": "pt-br", "count": n}),
                                 headers={"Accept": "application/json", "X-Subscription-Token": chave})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read(3_000_000).decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 422):
            raise ErroBusca(f"O Brave recusou a chave ({e.code}). Confira em Mais › Integrações.") from e
        if e.code == 429:
            raise ErroBusca("O Brave pediu para esperar (limite de buscas do plano).") from e
        raise ErroBusca(f"O Brave respondeu com erro {e.code}.") from e
    return [x for x in ((d.get("web") or {}).get("results") or []) if isinstance(x, dict) and url_ok(x.get("url"))]


def site_pelo_brave(nome, cidade, chave):
    """O site da própria loja nos resultados do Brave: o primeiro que não é rede social, guia, marketplace nem site de
    encartes e que tem no endereço ou no título uma palavra do nome da loja."""
    gen = {"agropecuaria", "agropet", "agro", "veterinaria", "acougue", "padaria", "hortifruti", "comercio", "produtos",
           "drogaria", "farmacia", "supermercado", "mercado", "petshop", "center", "store", "brasil"} | set(norm(cidade).split())
    palavras = [w for w in chave_loja(nome).split() if len(w) >= 4 and w not in gen]
    if not palavras:
        return None  # nome só com palavras genéricas: o resultado seria um chute
    for x in brave_busca(f"{nome} {cidade}".strip(), chave):
        u = x["url"]
        host = urllib.parse.urlsplit(u).netloc.lower()
        if any(k in host for k in NAO_SITE) or not site_loja(u):
            continue
        onde = norm(u.replace(".", " ").replace("/", " ").replace("-", " ") + " " + str(x.get("title") or ""))
        if any(w in onde.split() or w in norm(host).replace(" ", "") for w in palavras):
            return u
    return None


def testar_brave():
    ch = brave_chave()
    if not ch:
        return {"ok": False, "msg": "Falta a chave do Brave."}
    try:
        r = brave_busca("Giassi supermercados Joinville", ch, n=3)
    except ErroBusca as e:
        return {"ok": False, "msg": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "msg": f"Não consegui testar ({e})."}
    return {"ok": True, "msg": "Pronta: o app procura o site das lojas que o mapa não traz." if r else "O Brave aceitou a chave, mas não trouxe resultados."}


def sites_por_ia(cfg, lojas, forcar=False):
    """{nome normalizado: site} das lojas sem site no mapa. Primeiro a busca do Brave (sem IA, com chave em Integrações);
    o que faltar, pela busca na web da IA, numa pergunta só. Guardado 30 dias (também o "não tem")."""
    cache = ler_json(SITES_IA, {}) or {}
    mes = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(timespec="seconds")
    velho = lambda l: forcar or (cache.get(norm(l["nome"])) or {}).get("em", "") < mes  # noqa: E731
    mudou = False
    ch = brave_chave()
    if ch:
        cidade, _ = cidade_do_cep(cfg.get("cep"), ler_json(FOLHETOS, {}) or {})
        for l in [l for l in lojas if velho(l)][:15]:
            try:
                u = site_pelo_brave(l["nome"], cidade or "", ch)
            except ErroBusca as e:
                log(f"sites das lojas (Brave): {e}")
                break
            cache[norm(l["nome"])] = {"site": u, "em": agora(), "via": "brave"}
            mudou = True
            log(f"site de {l['nome']} pelo Brave: {u or 'não achei'}")
            time.sleep(1.1)  # plano grátis: uma busca por segundo
    # a IA tenta as que ninguém achou ainda (ou que só o Brave procurou)
    falta = [l for l in lojas if velho(l) or (not (cache.get(norm(l["nome"])) or {}).get("site")
                                             and (cache.get(norm(l["nome"])) or {}).get("via") != "ia")][:15]
    if falta and ia_ligada(cfg):
        cidade, uf = cidade_do_cep(cfg.get("cep"), ler_json(FOLHETOS, {}) or {})
        try:
            r = chamar_ai_task("EconomIA: sites das lojas", instrucoes_sites(falta, cidade or "", uf or ""), uso="busca")
        except ErroBusca as e:
            log(f"sites das lojas: {e}")
            r = None
        if isinstance(r, dict):
            resp = {int(x["n"]): x.get("site") for x in r.get("lojas") or [] if isinstance(x, dict) and str(x.get("n", "")).isdigit()}
            for i, l in enumerate(falta, 1):
                u = resp.get(i)
                cache[norm(l["nome"])] = {"site": u if url_ok(u) and site_loja(u) else None, "em": agora(), "via": "ia"}
            mudou = True
            log("sites das lojas pela IA: " + ", ".join(f"{l['nome']} → {cache[norm(l['nome'])]['site'] or 'sem site'}" for l in falta))
    if mudou:
        gravar_json(SITES_IA, cache)
    return {k: v["site"] for k, v in cache.items() if isinstance(v, dict) and v.get("site")}


def sem_site(l, nome, cidade, cfg):
    """A loja não tem site por nenhum caminho (informado, mapa, rede conhecida)?"""
    manual = next((a["site"] for a in ((cfg.get("lojas") or {}).get("adicionar") or [])
                   if isinstance(a, dict) and url_ok(a.get("site")) and mesma_loja(texto(a.get("nome"), 60).split(",")[0], nome)), None)
    return not (manual or site_loja(l.get("site")) or site_da_rede(nome, cidade))


def marca_fontes(categorias):
    """Põe em cada loja o resultado do último teste de preço (guardado à parte, sobrevive às buscas)."""
    fontes = ler_json(SONDA_FILE, {}) or {}
    for c in categorias:
        if not isinstance(c, dict):
            continue
        nomes = {r.get("id"): r.get("nome") for r in c.get("redes") or [] if isinstance(r, dict)}
        por_cat = fontes.get(c.get("id")) or {}
        if c.get("id") == "online":
            c["fontes_mkt"] = {k[4:]: v for k, v in por_cat.items() if k.startswith("mkt:") and isinstance(v, dict)}
        for l in c.get("lojas") or []:
            st = por_cat.get(norm(nomes.get(l.get("rede")) or ""))
            if st and st.get("como") == "instagram_novo" and l.get("instagram"):  # a busca já leu o post
                ate = l.get("instagram_ate")
                st = dict(st, como="instagram", passos=[f"✓ Encarte do Instagram lido pela IA" + (f", vale até {datetime.fromisoformat(ate).strftime('%d/%m')}." if ate else ".")])
            elif st and st.get("como") == "folheto_novo" and l.get("folheto"):
                ate = l.get("folheto_ate")
                st = dict(st, como="folheto", passos=[f"✓ Folheto da semana lido pela IA" + (f", vale até {datetime.fromisoformat(ate).strftime('%d/%m')}." if ate else ".")])
            if st:
                l["preco_fonte"] = st
                if st.get("site_url") and not site_loja(l.get("site")):  # site achado pela IA: a loja passa a mostrar
                    l["site"] = st["site_url"]


def sonda_lojas(cfg):
    SONDA.update({"rodando": True, "atual": 0, "total": 0, "loja": None, "resumo": None})
    try:
        atualiza_diretas(cfg, max_novas=30)
        of = ler_json(OFERTAS, {}) or {}
        alvos = lojas_acompanhadas(cfg, of.get("categorias") or [])
        SONDA["total"] = len(alvos)
        memo = ler_json(LOJAS_SITE, {}) or {}
        cache_f = ler_json(FOLHETOS, {}) or {}
        cidade, _ = cidade_do_cep(cfg.get("cep"), cache_f)
        faltam = [{"nome": nome, "endereco": l.get("endereco")} for _, _, nome, l in alvos if sem_site(l, nome, cidade or "", cfg)]
        if faltam:
            SONDA["loja"] = "procurando o site das lojas"
            achados = sites_por_ia(cfg, faltam)
            alvos = [(c, r, n, dict(l, _site_ia=achados[norm(n)]) if norm(n) in achados and sem_site(l, n, cidade or "", cfg) else l)
                     for c, r, n, l in alvos]
        fontes = ler_json(SONDA_FILE, {}) or {}
        buscas_folheto = [0]
        conta = {}
        for i, (cat_id, rid, nome, l) in enumerate(alvos, 1):
            SONDA.update({"atual": i, "loja": nome})
            try:
                st = testa_preco_loja(cat_id, nome, l, memo, cidade or "", cache_f, cfg, buscas_folheto)
            except Exception as e:  # noqa: BLE001
                st = {"como": "nenhum", "exemplo": None, "passos": [f"✗ Erro no teste: {str(e)[:80]}"], "em": agora()}
            fontes.setdefault(cat_id, {})[norm(nome)] = st
            conta[st["como"]] = conta.get(st["como"], 0) + 1
            log(f"teste de preço {nome}: {st['como']}" + (f" ({st['exemplo']})" if st.get("exemplo") else ""))
        gravar_json(LOJAS_SITE, memo)
        gravar_json(FOLHETOS, cache_f)
        gravar_json(SONDA_FILE, fontes)
        with _mescla_trava:
            of = ler_json(OFERTAS, {}) or {}
            marca_fontes(of.get("categorias") or [])
            gravar_json(OFERTAS, of)
        sem_ia = sum(conta.get(k, 0) for k in ("site", "paginas", "ofertas_site", "busca_site"))
        partes = [f"{sem_ia} com preço direto do site"] if sem_ia else []
        enc = sum(conta.get(k, 0) for k in ("folheto", "folheto_novo", "instagram", "instagram_novo"))
        if enc:
            partes.append(f"{enc} com folheto ou encarte no Instagram")
        if conta.get("ia"):
            partes.append(f"{conta['ia']} só pela busca com IA")
        if conta.get("nenhum"):
            partes.append(f"{conta['nenhum']} sem fonte de preço sem IA")
        SONDA["resumo"] = ("Testei " + str(len(alvos)) + (" loja: " if len(alvos) == 1 else " lojas: ") + ", ".join(partes) + ".") if alvos else "Nenhuma loja para testar."
    except Exception as e:  # noqa: BLE001
        SONDA["resumo"] = f"O teste parou: {e}"
        log(SONDA["resumo"])
    finally:
        SONDA.update({"rodando": False, "loja": None, "terminou_em": agora()})
        try:
            grava_vocab()
        except OSError:
            pass


TERMO_ONLINE = "café"


def testa_marketplace(cfg, mid, nome, memo):
    """Teste de preço de um marketplace (botão Testar agora em Online): API de afiliados, busca do site, senão só IA.
    A lista de produtos (sitemap) fica de fora: num marketplace ela tem milhões de páginas."""
    termo = TERMO_ONLINE
    st = {"como": None, "exemplo": None, "site": None, "passos": [], "em": agora(), "nome": nome}
    if mid == "shopee":
        if shopee_pronta():
            try:
                nodes = shopee_produtos(termo + " 500 g", 5)
            except ErroShopee as e:
                nodes = None
                st["passos"].append(f"✗ API de afiliados da Shopee: {e}")
            x = next((n for n in nodes or [] if numero(n.get("priceMin"))), None)
            if x:
                st.update(como="api", exemplo=f"{texto(x.get('productName'), 45)} por {br_preco(numero(x['priceMin']))}")
                st["passos"].append(f"✓ API de afiliados da Shopee: \"{termo}\", {st['exemplo']}.")
                return st
            if nodes is not None:
                st["passos"].append("✗ A API de afiliados da Shopee não trouxe produtos no teste.")
        else:
            st["passos"].append("A Shopee tem API de afiliados, que dá preço sem IA: ligue em Mais › Integrações.")
    o = MKT_SITES.get(mid)
    if o:
        st["site"] = o.split("://", 1)[-1].replace("www.", "")
        m = dict(testa_site(o, cfg.get("cep")), nome=nome, categoria="online", marketplace=True)
        if m.get("sem_resposta"):
            st["passos"].append(f"✗ O site {st['site']} {m.get('erro') or 'não respondeu'}.")
        elif not m.get("paginas"):
            st["passos"].append(f"✗ O site {st['site']} pede para programas não consultarem os preços.")
        else:
            try:
                ofs = busca_do_site(o, m, termo, True)
            except Exception:  # noqa: BLE001
                ofs = []
            if ofs:
                ex = min(ofs, key=lambda x: x["preco"])
                st.update(como="busca_site", exemplo=f"{ex['produto'][:45]} por {br_preco(ex['preco'])}")
                st["passos"].append(f"✓ A busca do site traz os preços (sem IA): \"{termo}\", {st['exemplo']}.")
                memo[o] = m  # a busca do site entra nas próximas buscas (só ela; a lista de produtos não)
            else:
                st["passos"].append(f"✗ A busca do site {st['site']} não mostra os preços para programas (ou o robots.txt não deixa).")
    if not st["como"]:
        st["como"] = "ia" if ia_ligada(cfg) else "nenhum"
        st["passos"].append("Preço só pela busca na web com IA." if ia_ligada(cfg) else "✗ Sem IA, não há de onde tirar o preço deste marketplace.")
    return st


def sonda_loja(cfg, cat_id, rid):
    """O teste de preço de uma loja só, de novo e sem o que ficou guardado (botão Testar agora)."""
    SONDA.update({"rodando": True, "atual": 1, "total": 1, "loja": None, "resumo": None})
    try:
        of = ler_json(OFERTAS, {}) or {}
        cat = next((c for c in of.get("categorias") or [] if isinstance(c, dict) and c.get("id") == cat_id), None)
        nomes = {r.get("id"): r.get("nome") for r in (cat or {}).get("redes") or [] if isinstance(r, dict)}
        l = next((x for x in (cat or {}).get("lojas") or [] if isinstance(x, dict) and x.get("rede") == rid), None)
        mid = rid[4:] if rid.startswith("mkt:") else (mkt_id(nomes.get(rid) or "") if cat_id == "online" else None)
        if mid and mid not in MARKETPLACES:
            mid = None
        if not mid and (not l or not nomes.get(rid)):
            SONDA["resumo"] = "Não achei essa loja."
            return
        nome = nomes.get(rid) or MARKETPLACES[mid]
        SONDA["loja"] = nome
        memo = ler_json(LOJAS_SITE, {}) or {}
        cache_f = ler_json(FOLHETOS, {}) or {}
        cidade, _ = cidade_do_cep(cfg.get("cep"), cache_f)
        if not mid and sem_site(l, nome, cidade or "", cfg):
            achados = sites_por_ia(cfg, [{"nome": nome, "endereco": l.get("endereco")}], forcar=True)
            if achados.get(norm(nome)):
                l = dict(l, _site_ia=achados[norm(nome)])
        try:
            st = testa_marketplace(cfg, mid, nome, memo) if mid else testa_preco_loja(cat_id, nome, l, memo, cidade or "", cache_f, cfg, [0], forcar=True)
        except Exception as e:  # noqa: BLE001
            st = {"como": "nenhum", "exemplo": None, "passos": [f"✗ Erro no teste: {str(e)[:80]}"], "em": agora(), "nome": nome}
        gravar_json(LOJAS_SITE, memo)
        gravar_json(FOLHETOS, cache_f)
        fontes = ler_json(SONDA_FILE, {}) or {}
        fontes.setdefault(cat_id, {})[norm(nome)] = st
        if mid:
            fontes[cat_id]["mkt:" + mid] = st  # para o marketplace que ainda não tem loja na última busca
        gravar_json(SONDA_FILE, fontes)
        with _mescla_trava:
            of = ler_json(OFERTAS, {}) or {}
            marca_fontes(of.get("categorias") or [])
            gravar_json(OFERTAS, of)
        log(f"teste de preço {nome} (só ela): {st['como']}" + (f" ({st['exemplo']})" if st.get("exemplo") else ""))
        SONDA["resumo"] = f"{nome}: " + (st["exemplo"] and f"achei {st['exemplo']}." or "veja em Como foi testado.")
    except Exception as e:  # noqa: BLE001
        SONDA["resumo"] = f"O teste parou: {e}"
        log(SONDA["resumo"])
    finally:
        SONDA.update({"rodando": False, "loja": None, "terminou_em": agora()})
        try:
            grava_vocab()
        except OSError:
            pass


def testar_google():
    g = google_chave()
    if not g:
        return {"ok": False, "msg": "Falta a chave do Google."}
    try:
        lat, lon = casa()
        r = google_lojas(lat, lon, 1000, ["farmacias"], g)
    except ErroBusca as e:
        return {"ok": False, "msg": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "msg": f"Não consegui testar ({e})."}
    if not r:
        return {"ok": True, "msg": "O Google aceitou a chave, mas não achou farmácias a 1 km da sua casa."}
    r.sort(key=lambda x: x["distancia_km"])
    return {"ok": True, "msg": f"Pronta: {len(r)} farmácias a até 1 km, a mais perto é {r[0]['nome']} ({str(r[0]['distancia_km']).replace('.', ',')} km)."}


MAX_FOCADA = 8


def instrucoes_focada(cfg, itens, cats):
    on = cfg.get("online") or {}
    locais = [CATEGORIAS[c]["o_que"] for c in cats if c != "online"]
    mkts = mkts_online(cfg) if "online" in cats else []
    entrega = "online" in cats and entrega_ligada(cfg)
    assin = [ASSINATURAS.get(a, a) for a in (on.get("assinaturas") or [])]
    numerados = [f"{k}) {n}" for k, n in enumerate(itens, 1)]
    return f"""Preciso do preço atual ({hoje_br()}) destes itens de uma lista de compras, para o CEP {cfg.get('cep')}, no Brasil: {'; '.join(numerados)}.

Use a busca na web agora e procure item por item: no site e no app das lojas, em encartes, no Google Shopping e em comparadores de preço. Use só o que encontrar: não invente preços. Se não conseguir usar a busca na web, responda apenas {{"erro": "sem_busca"}}.

Onde procurar: {', '.join(locais) or 'nenhuma loja física'}{f' num raio de {cfg.get("raio_km") or 2} km do CEP' if locais else ''}{('; e online em ' + ', '.join(mkts) + ' com entrega no CEP') if mkts else ''}{'; e em mercados que entregam no CEP, mesmo fora do raio (categoria "online")' if entrega else ''}.
Assinaturas do morador: {', '.join(assin) or 'nenhuma'}.
Se o item for genérico (por exemplo "pó lava louça"), procure as marcas mais vendidas e diga em "obs" qual produto e tamanho é cada preço. Traga até 4 preços por item, de lojas diferentes.
"categoria" é {', '.join(f'"{c}"' for c in cats)}. Online, informe "frete" (0 se grátis; "carrinho" se a loja só mostra no carrinho) e "prazo_dias". {PAGINA_PRODUTO}

Em "fonte", ponha o link da página do produto (o anúncio no Mercado Livre, a página na Amazon, o produto no site da loja), não a página inicial.

Responda somente com um objeto JSON, sem texto antes ou depois:
{{"lista": [{{"item": 1, "produto": "texto do item", "base": {{"quantidade": 1, "unidade": "kg", "rotulo": null}}, "precos": [{{"rede": "nome da loja", "categoria": "mercados", "preco": 12.9, "preco_clube": null, "frete": null, "prazo_dias": null, "obs": "Marca 1 kg", "fonte": "URL"}}]}}]}}"""


def categoria_do_preco(p, cats):
    """Em que categoria entra um preço da busca focada."""
    c = p.get("categoria")
    if c in cats:
        return c
    nome = norm(p.get("rede") or "")
    if "online" in cats and (frete_item(p.get("frete")) is not None
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
        cat.pop("_buscados", None)
        cat.pop("_redes_buscadas", None)
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
        ia = ia_ligada(cfg)
        # primeiro o que não gasta IA: site das lojas, Shopee e folhetos guardados
        BUSCA.update({"etapa": "sites das lojas", "total": 0})
        scripts, rel_s, ja = busca_scripts(cfg, cats, ler_folhetos=ia)
        relatorio.update(rel_s)
        BUSCA["etapa"] = "lojas no mapa"
        try:
            mapa = lojas_do_mapa(cfg, cats)
        except Exception as e:  # noqa: BLE001
            mapa = {}
            log(f"mapa: {e}")
        if not ia:  # sem IA: junta o que veio dos sites e o mapa ao resultado anterior
            mesclar_resultado(scripts, cfg, relatorio, mapa, completa=True)
            BUSCA["chamadas_ia"] = 0
            if not scripts:
                BUSCA["avisos"] = ["Com a IA desligada, nenhum site trouxe preço agora" + ("; as lojas foram atualizadas pelo mapa." if mapa else ".")]
            log("busca sem IA: " + (", ".join(rel_s) or "nenhum site trouxe preço") + (", mapa atualizado" if mapa else ""))
            return
        cfg_ia = dict(cfg, _ja_tenho=ja, _mapa=mapa)
        BUSCA["total"] = len(cats)
        for i, cat_id in enumerate(cats, 1):
            BUSCA.update({"atual": i, "etapa": CATEGORIAS[cat_id]["nome"].lower()})
            if cat_id == "online" and not mkts_online(cfg) and not entrega_ligada(cfg):
                continue  # só a Shopee, que já veio pela API
            log(f"buscando {cat_id}")
            try:
                try:
                    cat, parcial = normalizar(cat_id, chamar_ai_task(f"EconomIA: {cat_id}", instrucoes_para(cat_id, cfg_ia)), cfg)
                except ErroCota:
                    BUSCA["etapa"] = CATEGORIAS[cat_id]["nome"].lower() + " (a IA pediu uma pausa, tentando de novo em 1 minuto)"
                    log("cota da IA: esperando 60 s")
                    time.sleep(ESPERA_COTA)
                    BUSCA["etapa"] = CATEGORIAS[cat_id]["nome"].lower()
                    cat, parcial = normalizar(cat_id, chamar_ai_task(f"EconomIA: {cat_id}", instrucoes_para(cat_id, cfg_ia)), cfg)
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
        if scripts:  # por último: o preço do site da loja vale mais que o que a busca na web achou
            juntar_focada(novas, parciais, scripts)
            falhou_tudo = False
        if mapa:
            aplica_mapa(novas, mapa, cfg)
        # lojas que a busca acabou de achar (ainda não estavam no resultado anterior): o folheto delas também
        ja_vistas = {norm(x["loja"]) for x in relatorio.get("folhetos") or []}
        novas_lojas = [l for l in lojas_folheto(cfg, cats, novas, ja) if norm(l["nome"]) not in ja_vistas]
        if novas_lojas:
            try:
                fo2, st2 = busca_folhetos(cfg, novas_lojas)
            except Exception as e:  # noqa: BLE001
                fo2, st2 = [], {}
                log(f"folhetos: {e}")
            if fo2:
                juntar_focada(novas, parciais, fo2)
                falhou_tudo = False
            juntar_folheto_status(relatorio, st2)
        folheto = {norm(x["loja"]) for x in relatorio.get("folhetos") or [] if x.get("ofertas")} | {norm(n) for v in ja.values() for n in v}
        sites = [a for a in ((cfg.get("lojas") or {}).get("adicionar") or [])
                 if isinstance(a, dict) and url_ok(a.get("site")) and a.get("categoria") in cats and texto(a.get("nome"), 60)
                 and norm(texto(a["nome"], 60).split(",")[0]) not in folheto]
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
        manuais = {norm(l["nome"]) for l in sites} | folheto
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
        marca_fontes(novas)
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
        try:
            grava_vocab()
        except OSError:
            pass


_mescla_trava = threading.Lock()


def mesclar_resultado(resultado, cfg, extra=None, mapa=None, completa=False, novas_lojas=False):
    """Junta [(categoria, parcial)] ao ofertas.json atual, sem apagar o resto. Devolve a lista de preços juntada."""
    with _mescla_trava:
        anterior = ler_json(OFERTAS, {}) or {}
        novas = [c for c in (anterior.get("categorias") or []) if isinstance(c, dict)]
        base = {}
        for i in anterior.get("lista") or []:
            if isinstance(i, dict) and i.get("produto"):
                base[i["produto"]] = {"precos": dict(i.get("precos") or {}), "base": i.get("base"), "vistos": dict(i.get("vistos") or {}),
                                      "tamanhos": list(i.get("tamanhos") or []), "links": dict(i.get("links") or {}),
                                      "similares": list(i.get("similares") or [])}
        # a loja que acabou de ser consultada pelo site manda: o preço antigo dela para o item sai (mesmo se agora não achou nada).
        # Assim um produto casado errado numa busca antiga ("Limpador … e Álcool" no álcool perfumado) não fica para sempre.
        for cat, _ in resultado:
            buscados, redes_b = set(cat.get("_buscados") or []), set(cat.get("_redes_buscadas") or [])
            if not buscados or not redes_b:
                continue
            # a mesma loja em outra categoria também sai: o Fort que era "mercado que entrega" e agora é loja do bairro
            redes_b |= {pre + rid[5:] for rid in list(redes_b) for pre in ("merc-", "farm-", "pets-", "onli-") if len(rid) > 5}
            for prod, ent in base.items():
                if norm(prod) not in buscados:
                    continue
                for rid in redes_b:
                    ent["precos"].pop(rid, None)
                    ent["links"].pop(rid, None)
                    ent["vistos"].pop(rid, None)
                ent["tamanhos"] = [t for t in ent["tamanhos"] if not (isinstance(t, dict) and t.get("rede") in redes_b)]
                ent["similares"] = [x for x in ent.get("similares") or [] if not (isinstance(x, dict) and x.get("rede") in redes_b)]
        parciais = [base]
        juntar_focada(novas, parciais, resultado)
        if completa:  # busca feita: nenhuma loja está mais "esperando a próxima busca"
            for c in novas:
                for l in c.get("lojas") or []:
                    l.pop("nova", None)
        if mapa:
            aplica_mapa(novas, mapa, cfg, marcar_novas=novas_lojas)
        marca_fontes(novas)
        lista = juntar_categorias(parciais)
        relatorio = anterior.get("relatorio") if isinstance(anterior.get("relatorio"), dict) else {}
        relatorio["sem_preco"] = [n for n in nomes_da_lista(cfg) if n not in lista]
        for k, v in (extra or {}).items():
            if k in ("diretas", "shopee", "folhetos"):
                relatorio[k] = v
        gravar_json(OFERTAS, dict(anterior, versao=2, origem="ia_home_assistant", gerado_em=agora() if completa else anterior.get("gerado_em") or agora(),
                                  atualizado_em=agora(), lista=[item_ofertas(p, v) for p, v in lista.items()],
                                  categorias=novas, relatorio=relatorio))
        return lista


def buscar_itens(itens):
    cfg = ler_json(CONFIG, {}) or {}
    cats = [c for c in (cfg.get("categorias") or list(CATEGORIAS)) if c in CATEGORIAS]
    _uso_local.chamadas = 0
    BUSCA.update({"rodando": True, "erro": None, "avisos": [], "atual": 1, "total": 1, "chamadas_ia": None,
                  "etapa": (itens[0] if len(itens) == 1 else f"{len(itens)} itens").lower()})
    try:
        if not cfg.get("cep"):
            raise ErroBusca("Salve o CEP em Mais antes de buscar.")
        resultado, rel, _ = busca_scripts(cfg, cats, itens, ler_folhetos=False)
        conta = {n: sum(len(p[n]["precos"]) for _, p in resultado if n in p) for n in itens}
        faltam = [n for n in itens if conta[n] < 2]
        if faltam and ia_ligada(cfg):
            try:
                resultado = busca_focada(cfg, faltam, cats) + resultado  # o site da loja por último: vale mais
            except ErroBusca:
                if not resultado:
                    raise
        lista = mesclar_resultado(resultado, cfg, rel)
        achados = [n for n in itens if n in lista and any(n in p for _, p in resultado)]
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
        try:
            grava_vocab()
        except OSError:
            pass


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


# ---------- encarte ou print de preços mandado pelo morador ----------
def ler_encarte_fotos(job, fotos, loja):
    pasta = os.path.join(MEDIA, "economia")
    arquivos, anexos = [], []
    try:
        os.makedirs(pasta, exist_ok=True)
        for n, (dado, mime) in enumerate(fotos):
            ext = "png" if mime == "image/png" else "webp" if mime == "image/webp" else "jpg"
            nome = f"encarte-{job}-{n}.{ext}"
            with open(os.path.join(pasta, nome), "wb") as f:
                f.write(dado)
            arquivos.append(os.path.join(pasta, nome))
            anexos.append({"media_content_id": f"{MEDIA_URI}/economia/{nome}", "media_content_type": mime})
        cfg = ler_config()
        r = chamar_ai_task(f"EconomIA: encarte {loja['nome']}", instrucoes_encarte(loja, "", len(anexos), cfg), anexos, uso="fotos")
        cat, parcial = normalizar(loja["categoria"], bruto_encarte(loja, r), cfg)
        for l in cat["lojas"]:
            l["fontes"] = sorted(set(l.get("fontes") or []) | {"Encarte"})
        mesclar_resultado([(cat, parcial)], cfg)
        LEITURAS[job].update({"status": "pronto", "ofertas": len(cat["ofertas"]), "precos": sorted(parcial),
                              "loja": loja["nome"], "itens": [{"produto": o["produto"], "preco": o["preco_oferta"]} for o in cat["ofertas"][:40]]})
        log(f"encarte por foto {loja['nome']}: {len(cat['ofertas'])} oferta(s), {len(parcial)} item(ns) da lista")
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


def comeca_encarte(dado):
    fotos = []
    for img in (dado.get("imagens") or [])[:8]:
        m = re.match(r"^data:(image/(?:jpeg|png|webp));base64,(.+)$", str(img), re.S)
        if m:
            try:
                bruto = base64.b64decode(m.group(2), validate=False)
            except ValueError:
                continue
            if 0 < len(bruto) <= 6 * 1024 * 1024:
                fotos.append((bruto, m.group(1)))
    nome = texto(dado.get("loja"), 60)
    cat = dado.get("categoria") if dado.get("categoria") in CATEGORIAS and dado.get("categoria") != "online" else "mercados"
    if not fotos or not nome:
        return None
    job = datetime.now().strftime("%H%M%S") + "-" + os.urandom(3).hex()
    for antigo in sorted(LEITURAS)[:-20]:
        LEITURAS.pop(antigo, None)
    LEITURAS[job] = {"status": "lendo", "itens": [], "erro": None}
    threading.Thread(target=ler_encarte_fotos, args=(job, fotos, {"nome": nome, "site": None, "categoria": cat}), daemon=True).start()
    return job


# ---------- Falar: o áudio vai para a fala para texto do Home Assistant ----------
VOZ = voz.Voz(HA_API, HA_WS, None, lambda *a: log(" ".join(str(x) for x in a)), simulada=VOZ_SIMULADA)


def voz_status():
    if not ia_ligada():
        return {"pronta": False, "motivo": "A IA está desligada em Mais › Integrações."}
    VOZ.token = token_ha()
    if not VOZ.token and not VOZ_SIMULADA:
        return {"pronta": False, "motivo": "Fora do Home Assistant não dá para falar."}
    escolha = str((ler_config().get("ia") or {}).get("voz") or "").strip() or None
    st = VOZ.status(escolha)
    st["opcoes"] = [{"id": o["id"], "nome": o["nome"], "preferido": o["preferido"]} for o in VOZ.opcoes()]
    st["escolha"] = escolha or ""
    return st


def voz_texto(pcm):
    if not ia_ligada():
        raise ErroBusca(IA_DESLIGADA)
    VOZ.token = token_ha()
    inicio = time.time()
    try:
        r = VOZ.texto(pcm, str((ler_config().get("ia") or {}).get("voz") or "").strip() or None)
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
                                 "cat": c.get("id"), "dist": dist.get(r["id"]), "loja": r["id"] in dist}

    def acompanha(rid):
        i = info.get(rid)
        if not i or i["cat"] not in ativas or rid in ignorar:
            return False
        if not i["loja"] and i["cat"] != "online" and rid not in manter:
            return False  # rede que ficou sem loja (o mapa tirou: de outra categoria ou duplicada)
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
    server_version = "EconomIA/0.18.0"

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
        elif rota == "/api/integracoes":
            ch = segredos().get("shopee") or {}
            ig = segredos().get("instagram") or {}
            ml = ml_conf()
            self._json(200, {"shopee": {"app_id": str(ch.get("app_id") or ""), "tem_senha": bool(ch.get("secret"))}, "google": {"tem_chave": bool(google_chave())},
                             "instagram": {"tem_chave": bool(ig.get("token")), "usuario": ig.get("usuario")}, "brave": {"tem_chave": bool(brave_chave())},
                             "ml": {"app_id": str(ml.get("app_id") or ""), "tem_senha": bool(ml.get("secret")), "url_retorno": str(ml.get("url_retorno") or ""),
                                    "conectado": ml_ligado(), "autorizar": ml_autorizar_url(ml), "erro": _ml["erro"]}})
        elif rota == "/api/lojas-mapa/teste":
            self._json(200, SONDA)
        elif rota == "/api/lojas-mapa":
            m = ler_json(LOJAS_MAPA, {}) or {}
            self._json(200, {"fontes": m.get("fontes") or [], "em": m.get("em"), "lojas": m.get("lojas") or {}})
        elif rota == "/api/folhetos":
            self._json(200, {"lojas": folhetos_painel(ler_config())})
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
        elif rota == "/api/integracoes":
            dado = self._corpo()
            if dado is None:
                return
            seg = segredos()
            if "shopee" in dado:
                novo = dado.get("shopee")
                if not novo:
                    seg.pop("shopee", None)
                else:
                    atual = seg.get("shopee") or {}
                    app = re.sub(r"\s", "", str(novo.get("app_id") or ""))[:40]
                    senha = str(novo.get("secret") or "").strip()[:200]
                    if not app:
                        return self._json(400, {"erro": "Falta o App ID da Shopee."})
                    seg["shopee"] = {"app_id": app, "secret": senha or (atual.get("secret") if atual.get("app_id") == app else "")}
            if "google" in dado:
                novo = dado.get("google")
                chave = re.sub(r"\s", "", str((novo or {}).get("key") or ""))[:120]
                if chave:
                    seg["google"] = {"key": chave}
                elif not novo:
                    seg.pop("google", None)
                try:
                    os.remove(LOJAS_MAPA)  # a próxima busca já usa (ou deixa de usar) o Google
                except OSError:
                    pass
            if "brave" in dado:
                novo = dado.get("brave")
                chave = re.sub(r"\s", "", str((novo or {}).get("key") or ""))[:120]
                if chave:
                    seg["brave"] = {"key": chave}
                elif not novo:
                    seg.pop("brave", None)
            if "ml" in dado:
                novo = dado.get("ml")
                if not novo:
                    seg.pop("ml", None)
                else:
                    atual = seg.get("ml") or {}
                    app = re.sub(r"\D", "", str(novo.get("app_id") or ""))[:30]
                    senha = re.sub(r"\s", "", str(novo.get("secret") or ""))[:200]
                    volta = str(novo.get("url_retorno") or "").strip()[:300]
                    if not app:
                        return self._json(400, {"erro": "Falta o App ID do Mercado Livre."})
                    if not re.match(r"https://[^\s/]+\.[^\s]+", volta):
                        return self._json(400, {"erro": "A URL de retorno precisa ser a mesma do app no Mercado Livre e começar com https://."})
                    mesmo = atual.get("app_id") == app
                    x = {"app_id": app, "secret": senha or (atual.get("secret") if mesmo else ""), "url_retorno": volta}
                    if mesmo and atual.get("url_retorno") == volta and not senha:  # a autorização continua valendo
                        x.update({k: atual[k] for k in ("access_token", "refresh_token", "expira") if k in atual})
                    seg["ml"] = x
                grava_segredos(seg)
                ml = seg.get("ml") or {}
                return self._json(200, {"ok": True, "ml": {"app_id": str(ml.get("app_id") or ""), "tem_senha": bool(ml.get("secret")),
                                                           "url_retorno": str(ml.get("url_retorno") or ""), "conectado": ml_ligado(),
                                                           "autorizar": ml_autorizar_url(ml)}})
            if "instagram" in dado:
                novo = dado.get("instagram")
                chave = re.sub(r"\s", "", str((novo or {}).get("token") or ""))[:600]
                if chave:
                    seg["instagram"] = {"token": chave}  # a conta do Instagram é achada de novo no teste
                elif not novo:
                    seg.pop("instagram", None)
            grava_segredos(seg)
            ch = seg.get("shopee") or {}
            self._json(200, {"ok": True, "shopee": {"app_id": str(ch.get("app_id") or ""), "tem_senha": bool(ch.get("secret"))},
                             "google": {"tem_chave": bool((seg.get("google") or {}).get("key"))}})
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
        if urllib.parse.urlsplit(self.path).path == "/api/lojas-mapa/atualizar":
            if BUSCA["rodando"] or SONDA["rodando"]:
                return self._json(200, {"ok": False, "msg": "Espere a busca terminar." if BUSCA["rodando"] else "Ainda estou testando as lojas. Espere terminar."})
            try:
                n = int(self.headers.get("Content-Length") or 0)
                dado = json.loads(self.rfile.read(n) or b"{}") if 0 < n < 20000 else {}
            except (ValueError, OSError):
                dado = {}
            return self._json(200, atualizar_lojas_mapa(dado if isinstance(dado, dict) else {}))
        if urllib.parse.urlsplit(self.path).path == "/api/lojas-mapa/testar-loja":
            try:
                n = int(self.headers.get("Content-Length") or 0)
                dado = json.loads(self.rfile.read(n) or b"{}") if 0 < n < 10000 else {}
            except (ValueError, OSError):
                dado = {}
            if SONDA.get("rodando"):
                return self._json(409, {"ok": False, "msg": "Já tem um teste rodando. Espere ele terminar."})
            cat_id, rid = str((dado or {}).get("categoria") or ""), str((dado or {}).get("rede") or "")[:80]
            if (cat_id not in TERMO_TESTE and cat_id != "online") or not rid:
                return self._json(400, {"ok": False, "msg": "Loja inválida."})
            SONDA["rodando"] = True
            threading.Thread(target=sonda_loja, args=(ler_config(), cat_id, rid), daemon=True).start()
            return self._json(200, {"ok": True})
        if urllib.parse.urlsplit(self.path).path == "/api/integracoes/testar":
            try:
                n = int(self.headers.get("Content-Length") or 0)
                dado = json.loads(self.rfile.read(n) or b"{}") if 0 < n < 10000 else {}
            except (ValueError, OSError):
                dado = {}
            serv = dado.get("servico") if isinstance(dado, dict) else None
            return self._json(200, testar_google() if serv == "google" else testar_instagram() if serv == "instagram"
                              else testar_brave() if serv == "brave" else testar_ml() if serv == "ml" else testar_shopee())
        if urllib.parse.urlsplit(self.path).path == "/api/integracoes/ml/conectar":
            dado = self._corpo()
            if dado is None:
                return
            try:
                ml_conectar((dado or {}).get("codigo"))
            except ErroBusca as e:
                return self._json(400, {"ok": False, "msg": str(e)})
            except Exception as e:  # noqa: BLE001
                return self._json(400, {"ok": False, "msg": f"Não consegui conectar ({e})."})
            return self._json(200, testar_ml())
        if urllib.parse.urlsplit(self.path).path == "/api/ler-encarte":
            dado = self._corpo(MAX_FOTOS_BODY)
            if dado is None:
                return
            if not ia_ligada():
                return self._json(400, {"erro": IA_DESLIGADA})
            job = comeca_encarte(dado)
            if not job:
                return self._json(400, {"erro": "Escolha as fotos do encarte e diga de qual loja é."})
            return self._json(202, {"id": job})
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
