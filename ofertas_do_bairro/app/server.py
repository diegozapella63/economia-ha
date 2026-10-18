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
- GET  /api/busca    andamento da busca
- GET  /api/exportar/lista.xlsx | lista.json   exporta a lista
- GET  /api/todos    listas de tarefas do Home Assistant
- POST /api/sincronizar-lista   sincroniza agora com a lista do Home Assistant
- POST /api/ler-lista   lê fotos ou texto (do WhatsApp, por exemplo) e sugere itens
- GET  /api/ler-lista?id=...   resultado da leitura

Só usa a biblioteca padrão do Python.
"""
import base64
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
import zipfile

DATA = os.environ.get("OFERTAS_DATA", "/data")
WWW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "www")
PORT = int(os.environ.get("OFERTAS_PORT", "8099"))
CONFIG = os.path.join(DATA, "config.json")
OFERTAS = os.path.join(DATA, "ofertas.json")
OPTIONS = os.path.join(DATA, "options.json")
SYNC_FILE = os.path.join(DATA, "sync_ha.json")
SYNC_INTERVALO = int(os.environ.get("OFERTAS_SYNC_SEG", "60"))
HA_API = os.environ.get("OFERTAS_HA_API", "http://supervisor/core/api")
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
MARKETPLACES = {"mercadolivre": "Mercado Livre", "amazon": "Amazon", "shopee": "Shopee", "magalu": "Magalu",
                "americanas": "Americanas", "casasbahia": "Casas Bahia"}
ASSINATURAS = {"prime": "Amazon Prime", "melimais": "Meli+"}
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


def valor_total(v):
    """Preço de um item da lista: número (loja) ou {preco, frete} (online)."""
    if isinstance(v, dict):
        preco = numero(v.get("preco"))
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
def ha_api(metodo, caminho, corpo=None, timeout=30):
    token = os.environ.get("SUPERVISOR_TOKEN")
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


def chamar_ai_task(nome, instrucoes, anexos=None):
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        raise ErroBusca("O add-on não tem acesso ao Home Assistant. Reinstale a versão mais nova do add-on.")
    corpo = {"task_name": nome, "instructions": instrucoes}
    if anexos:
        corpo["attachments"] = anexos
    entidade = str(opcoes().get("ai_task_entity") or "").strip()
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
            raise ErroBusca("Falta uma IA com tarefa de IA no Home Assistant. Configure a integração Anthropic "
                            "(ou outra com AI Task) em Configurações → Dispositivos e serviços.") from e
        if e.code == 401:
            raise ErroBusca("O add-on não tem permissão para usar o Home Assistant. Reinstale a versão mais nova.") from e
        if anexos and "attachment" in corpo_erro.lower():
            raise ErroBusca("A IA escolhida no Home Assistant não lê imagens. Use uma que leia, como a Anthropic, "
                            "ou cole o texto da mensagem.") from e
        raise ErroBusca(f"A IA do Home Assistant recusou o pedido ({e.code}): {corpo_erro}") from e
    except urllib.error.URLError as e:
        raise ErroBusca("Não consegui falar com o Home Assistant. Tente de novo em instantes.") from e
    dado = (resp.get("service_response") or {}).get("data") if isinstance(resp, dict) else None
    if isinstance(dado, dict):
        return dado
    if not isinstance(dado, str):
        raise ErroBusca("A IA não devolveu resposta.")
    ini, fim = dado.find("{"), dado.rfind("}")
    if ini < 0 or fim <= ini:
        raise ErroBusca("A IA respondeu fora do formato esperado.")
    try:
        return json.loads(dado[ini:fim + 1])
    except ValueError as e:
        raise ErroBusca("A IA respondeu fora do formato esperado.") from e


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
                "é contado, no singular (rolo, cápsula, fralda). Em \"ofertas\", informe \"tamanho\" quando souber.")


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
            out.append(f"{n} (base: {fmt_base(b)})" if b else n)
    return out


def instrucoes_online(cfg):
    casa, excluir, restr, interesses = descreve_casa(cfg)
    on = cfg.get("online") or {}
    mkts = [MARKETPLACES.get(m, m) for m in (on.get("marketplaces") or ["mercadolivre", "amazon"])]
    assin = [ASSINATURAS.get(a, a) for a in (on.get("assinaturas") or [])]
    lista = itens_prompt(cfg)
    return f"""Encontre preços válidos hoje ({hoje_br()}) em {', '.join(mkts)} para entrega no CEP {cfg.get('cep')}, no Brasil.

Use a busca na web agora. Use só o que encontrar nas páginas: não invente produtos, preços, fretes nem prazos. Se não conseguir usar a busca na web, responda apenas {{"erro": "sem_busca"}}.

Assinaturas do morador: {', '.join(assin) or 'nenhuma'}. Quando a assinatura der frete grátis no item, use frete 0.
Casa: {casa}.
Não traga: {', '.join(excluir) or 'nada a excluir'}.
Restrições: {', '.join(restr) or 'nenhuma'}. Interesses, que devem vir primeiro: {', '.join(interesses) or 'nenhum'}.
Lista de compras: {'; '.join(lista) or 'vazia'}.
{TAMANHOS_TXT} Em "tamanhos", informe também o frete e o prazo de cada opção.

Regras: só lojas oficiais ou vendedores bem avaliados. Marque "importado": true quando o envio for internacional. Não inclua remédios que exigem receita. Informe frete e prazo de entrega para este CEP. Em kits, informe "unidades". Até 15 ofertas, priorizando os itens da lista e os interesses.

Responda somente com um objeto JSON, sem texto antes ou depois, neste formato:
{{
  "cupons": [{{"rede": "Mercado Livre", "codigo": "CODIGO", "valor": 20, "beneficio": "R$ 20 de desconto", "condicao": "Acima de R$ 200", "valido_ate": "AAAA-MM-DD ou null", "oficial": true, "fonte": "URL"}}],
  "ofertas": [{{"rede": "Amazon", "produto": "Nome · tamanho", "preco_normal": 10.0, "preco_oferta": 8.0, "frete": 0, "prazo_dias": 2, "vendedor": "nome do vendedor", "oficial": true, "importado": false, "unidades": 1, "tamanho": {{"quantidade": 1, "unidade": "L"}}, "tipo": "promo", "tags": ["alimentos"], "fonte": "URL"}}],
  "lista": [{{"produto": "texto exato do item da lista", "base": {{"quantidade": 1, "unidade": "L", "rotulo": null}}, "precos": [{{"rede": "Amazon", "preco": 9.9, "frete": 0, "prazo_dias": 2, "fonte": "URL"}}], "tamanhos": [{{"rede": "Mercado Livre", "embalagem": "Kit 6 × 1 L", "quantidade": 6, "unidade": "L", "preco": 49.9, "frete": 0, "prazo_dias": 3, "fonte": "URL"}}]}}]
}}

Etiquetas permitidas em "tags": {', '.join(sorted(TAGS))}."""


def instrucoes_para(cat_id, cfg):
    if cat_id == "online":
        return instrucoes_online(cfg)
    cat = CATEGORIAS[cat_id]
    casa, excluir, restr, interesses = descreve_casa(cfg)
    lojas = cfg.get("lojas") or {}
    lista = itens_prompt(cfg)
    adicionadas = [a.get("nome") for a in (lojas.get("adicionar") or []) if isinstance(a, dict) and a.get("categoria") == cat_id]
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
  "lojas": [{{"rede": "nome da rede ou da loja", "endereco": "rua e número", "distancia_km": 1.2, "horario": "Aberta até 22h", "fontes": ["Site", "App", "Encarte", "Clube", "Instagram", "WhatsApp", "Tiendeo"]}}],
  "cupons": [{{"rede": "...", "codigo": "CODIGO", "valor": 20, "beneficio": "R$ 20 de desconto", "condicao": "Pedidos acima de R$ 200", "valido_ate": "AAAA-MM-DD ou null", "oficial": true, "fonte": "URL"}}],
  "ofertas": [{{"rede": "...", "produto": "Nome · tamanho", "preco_normal": 10.0, "preco_oferta": 8.0, "tipo": "promo", "unidade": null, "tamanho": {{"quantidade": 500, "unidade": "g"}}, "condicao": null, "tags": ["alimentos"], "fonte": "URL"}}],
  "lista": [{{"produto": "texto exato do item da lista", "base": {{"quantidade": 1, "unidade": "L", "rotulo": null}}, "precos": [{{"rede": "...", "preco": 9.9, "fonte": "URL"}}], "tamanhos": [{{"rede": "...", "embalagem": "Galão 5 L", "quantidade": 5, "unidade": "L", "preco": 39.9, "fonte": "URL"}}]}}]
}}

Regras: até 15 ofertas, priorizando os interesses e os maiores descontos. "tipo" é "promo", "clube" (preço para membros) ou "atacado" (preço por quantidade). "oficial" é true só se o cupom estiver no site ou app da própria loja. Etiquetas permitidas em "tags": {', '.join(sorted(TAGS))}.{extra}"""


def normalizar(cat_id, bruto, cfg):
    if not isinstance(bruto, dict):
        raise ErroBusca("A IA respondeu fora do formato esperado.")
    if bruto.get("erro") == "sem_busca":
        raise ErroBusca("A IA do Home Assistant está sem a busca na web. Ligue a busca na web nas opções da tarefa de IA "
                        "(Configurações → Dispositivos e serviços → Anthropic).")
    pre = cat_id[:4] + "-"
    redes = {}

    def rede_id(nome):
        nome = texto(nome, 60)
        if not nome:
            return None
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

    cupons = []
    for c in bruto.get("cupons") or []:
        if not isinstance(c, dict) or not url_ok(c.get("fonte")) or not texto(c.get("codigo"), 40):
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
        if not isinstance(o, dict) or not url_ok(o.get("fonte")):
            continue
        rid, prod = rede_id(o.get("rede")), texto(o.get("produto"), 100)
        normal, oferta = numero(o.get("preco_normal")), numero(o.get("preco_oferta"))
        if not (rid and prod and normal and oferta and oferta < normal):
            continue
        oid = rid + "-" + slug(prod)
        if oid in ids:
            continue
        ids.add(oid)
        item = {"id": oid, "rede": rid, "produto": prod, "preco_normal": normal, "preco_oferta": oferta,
                "tipo": o.get("tipo") if o.get("tipo") in ("promo", "clube", "atacado") else "promo",
                "tags": [t for t in (o.get("tags") or []) if t in TAGS], "fonte": o["fonte"]}
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

    nomes_lista = {norm(i.get("produto") if isinstance(i, dict) else i): (i.get("produto") if isinstance(i, dict) else i)
                   for i in (cfg.get("lista") or [])}
    def valor_lista(p):
        """(rede, valor) de um preço da lista; online precisa de frete."""
        if not isinstance(p, dict) or not url_ok(p.get("fonte")):
            return None, None
        rid, preco = rede_id(p.get("rede")), numero(p.get("preco"))
        if not (rid and preco):
            return None, None
        if cat_id != "online":
            return rid, preco
        frete = frete_ok(p.get("frete"))
        if frete is None:
            return None, None
        valor = {"preco": preco, "frete": frete}
        if inteiro(p.get("prazo_dias")) is not None:
            valor["prazo_dias"] = inteiro(p.get("prazo_dias"))
        if texto(p.get("obs"), 60):
            valor["obs"] = texto(p.get("obs"), 60)
        return rid, valor

    lista = {}
    for it in bruto.get("lista") or []:
        if not isinstance(it, dict):
            continue
        original = nomes_lista.get(norm(re.sub(r"\s*\(base:[^)]*\)\s*$", "", str(it.get("produto") or ""))))
        if not original:
            continue
        ent = lista.setdefault(original, {"precos": {}, "base": None, "tamanhos": []})
        for p in it.get("precos") or []:
            rid, valor = valor_lista(p)
            if rid:
                ent["precos"][rid] = valor
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
            tam["fonte"] = t["fonte"]
            ent["tamanhos"].append(tam)
    lista = {k: v for k, v in lista.items() if v["precos"] or v["tamanhos"]}

    # toda rede citada precisa de uma loja, para o painel saber se a acompanha
    online = cat_id == "online"
    for rid in redes:
        lojas.setdefault(rid, {"rede": rid, "distancia_km": None, "horario": "Entrega no seu CEP" if online else "",
                               "endereco": None, "fontes": ["Site", "App"] if online else ["Site"]})

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


def juntar_item(dest, ent):
    """Junta o que uma categoria achou para um item da lista ao que as outras já acharam."""
    b, nb = dest.get("base"), ent.get("base")
    if not b and nb:
        dest["base"] = b = nb
    if not (b and nb) or (nb["unidade"] == b["unidade"] and mesmo_tamanho(nb["quantidade"], b["quantidade"])):
        dest["precos"].update(ent["precos"])
        if b and nb:
            dest["tamanhos"] += ent["tamanhos"]
        return
    if nb["unidade"] != b["unidade"]:  # medidas diferentes não dá para comparar
        dest["precos"].update(ent["precos"])
        return
    # esta categoria usou outro tamanho como base: os preços dela viram tamanhos
    for rid, v in ent["precos"].items():
        t = {"rede": rid, "quantidade": nb["quantidade"]}
        if isinstance(v, dict):
            t.update({k: v[k] for k in ("preco", "frete", "prazo_dias") if k in v})
        else:
            t["preco"] = v
        dest["tamanhos"].append(t)
    for t in ent["tamanhos"]:
        if mesmo_tamanho(t["quantidade"], b["quantidade"]):
            v = {k: t[k] for k in ("preco", "frete", "prazo_dias") if k in t}
            dest["precos"].setdefault(t["rede"], v if "frete" in v else v["preco"])
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
        dest = {"precos": {}, "base": None, "tamanhos": []}
        if votos:
            un, q = max(votos, key=votos.get)
            dest["base"] = next(e["base"] for e in ents if e.get("base") and (e["base"]["unidade"], e["base"]["quantidade"]) == (un, q))
        for e in ents:
            juntar_item(dest, e)
        lista[prod] = dest
    return lista


def item_ofertas(prod, ent):
    out = {"produto": prod, "precos": ent["precos"]}
    if ent.get("base"):
        out["base"] = ent["base"]
        if ent["tamanhos"]:
            por_un = lambda t: (t["preco"] + (t.get("frete") or 0)) / t["quantidade"]  # noqa: E731
            out["tamanhos"] = sorted(ent["tamanhos"], key=por_un)[:12]
    return out


def buscar():
    cfg = ler_json(CONFIG, {}) or {}
    cats = [c for c in (cfg.get("categorias") or list(CATEGORIAS)) if c in CATEGORIAS]
    BUSCA.update({"rodando": True, "erro": None, "avisos": [], "atual": 0, "total": len(cats), "etapa": None})
    try:
        if not cfg.get("cep"):
            raise ErroBusca("Salve o CEP em Mais antes de buscar.")
        anterior = ler_json(OFERTAS, {}) or {}
        antigas = {c.get("id"): c for c in (anterior.get("categorias") or []) if isinstance(c, dict)}
        novas, parciais, falhas = [], [], []
        for i, cat_id in enumerate(cats, 1):
            BUSCA.update({"atual": i, "etapa": CATEGORIAS[cat_id]["nome"].lower()})
            log(f"buscando {cat_id}")
            try:
                cat, parcial = normalizar(cat_id, chamar_ai_task(f"EconomIA: {cat_id}", instrucoes_para(cat_id, cfg)), cfg)
            except ErroBusca as e:
                if any(t in str(e) for t in ("Falta uma IA", "sem a busca na web", "não tem acesso", "não tem permissão")):
                    raise
                falhas.append(f"{CATEGORIAS[cat_id]['nome']}: {e}")
                if cat_id in antigas:
                    novas.append(antigas[cat_id])
                continue
            novas.append(cat)
            parciais.append(parcial)
        lista = juntar_categorias(parciais)
        if not novas or len(falhas) == len(cats):
            raise ErroBusca(falhas[0] if falhas else "A busca não trouxe resultados.")
        gravar_json(OFERTAS, {
            "versao": 2, "gerado_em": agora(), "origem": "ia_home_assistant",
            "lista": [item_ofertas(p, v) for p, v in lista.items()],
            "categorias": novas,
        })
        if falhas:
            BUSCA["avisos"] = ["Algumas buscas falharam e mantive o resultado anterior: " + " | ".join(falhas)]
        log("busca concluída")
    except ErroBusca as e:
        BUSCA["erro"] = str(e)
        log(f"busca falhou: {e}")
    except Exception as e:  # noqa: BLE001
        BUSCA["erro"] = f"Erro inesperado na busca: {e}"
        log(BUSCA["erro"])
    finally:
        BUSCA.update({"rodando": False, "etapa": None, "terminou_em": agora()})


# ---------- ler a lista de fotos ou texto ----------
def instrucoes_leitura(texto_msg, n_fotos, cfg):
    atuais = [nome_item(i) for i in (cfg.get("lista") or []) if nome_item(i)]
    partes = []
    if n_fotos:
        partes.append(f"{n_fotos} imagem(ns) em anexo")
    if texto_msg:
        partes.append("o texto abaixo")
    return f"""Alguém mandou, provavelmente pelo WhatsApp, coisas para comprar. Você recebe {' e '.join(partes)}.
Pode ser print de conversa, lista escrita à mão, foto de produto ou de embalagem vazia, encarte ou receita.

Extraia só os itens a comprar, em português do Brasil, um por item, do jeito que se escreve numa lista de compras: o nome do produto e, se aparecer, a marca, o tamanho ou a dosagem (por exemplo "Lysoform", "Leite integral 1 L", "Dipirona 500 mg"). A quantidade (por exemplo "2" ou "3 pacotes") vai em "quantidade", não no nome. Junte itens repetidos. Ignore conversa que não seja item de compra, preços, horários e nomes de pessoas.
Itens que já estão na lista: {'; '.join(atuais) or 'nenhum'}. Se um item for o mesmo de um desses, use exatamente o nome que já está na lista.
{('Texto:' + chr(10) + chr(34) * 3 + texto_msg + chr(34) * 3) if texto_msg else ''}

Responda somente com um objeto JSON, sem texto antes ou depois:
{{"itens": [{{"produto": "Leite integral 1 L", "quantidade": "2", "obs": null}}]}}
Se não achar nenhum item, responda {{"itens": []}}."""


def ler_lista(job, fotos, texto_msg):
    pasta = os.path.join(MEDIA, "economia")
    arquivos, anexos = [], []
    try:
        if fotos:
            try:
                os.makedirs(pasta, exist_ok=True)
            except OSError as e:
                raise ErroBusca("O add-on não consegue usar a pasta de mídia do Home Assistant. Reinstale a versão mais nova.") from e
            for n, (dado, tipo) in enumerate(fotos):
                ext = "png" if tipo == "image/png" else "webp" if tipo == "image/webp" else "jpg"
                nome = f"lista-{job}-{n}.{ext}"
                with open(os.path.join(pasta, nome), "wb") as f:
                    f.write(dado)
                arquivos.append(os.path.join(pasta, nome))
                anexos.append({"media_content_id": f"{MEDIA_URI}/economia/{nome}", "media_content_type": tipo})
        cfg = ler_config()
        bruto = chamar_ai_task("EconomIA: ler lista", instrucoes_leitura(texto_msg, len(anexos), cfg), anexos)
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
    texto_msg = str(dado.get("texto") or "").strip()[:4000]
    if not fotos and not texto_msg:
        return None
    job = datetime.now().strftime("%H%M%S") + "-" + os.urandom(3).hex()
    for antigo in sorted(LEITURAS)[:-20]:
        LEITURAS.pop(antigo, None)
    LEITURAS[job] = {"status": "lendo", "itens": [], "erro": None}
    threading.Thread(target=ler_lista, args=(job, fotos, texto_msg), daemon=True).start()
    return job


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
    itens = []
    for it in cfg.get("lista") or []:
        prod = it.get("produto") if isinstance(it, dict) else str(it)
        if not prod:
            continue
        compras = sorted(d for d in ((it.get("compras") or []) if isinstance(it, dict) else []) if data_ok(d))
        ps = sorted(({"loja": info[r]["nome"], "tipo": info[r]["tipo"], "preco": valor_total(v)}
                     for r, v in precos.get(norm(prod), {}).items() if acompanha(r) and valor_total(v)),
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
    server_version = "EconomIA/0.8.3"

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
        elif rota == "/api/estado":
            self._json(200, {
                "config": ler_json(CONFIG),
                "ofertas": ler_json(OFERTAS),
                "usuario": self.headers.get("X-Remote-User-Display-Name") or self.headers.get("X-Remote-User-Name") or None,
                "busca": BUSCA,
                "sync": SYNC,
            })
        elif rota == "/api/todos":
            try:
                self._json(200, {"listas": listas_ha()})
            except ErroBusca as e:
                self._json(502, {"erro": str(e)})
        elif rota == "/api/busca":
            self._json(200, BUSCA)
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
                novo = gravar_config(cfg)
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
        if urllib.parse.urlsplit(self.path).path == "/api/ler-lista":
            dado = self._corpo(MAX_FOTOS_BODY)
            if dado is None:
                return
            job = comeca_leitura(dado)
            if not job:
                return self._json(400, {"erro": "Escolha uma foto ou cole o texto da mensagem."})
            return self._json(202, {"id": job})
        if urllib.parse.urlsplit(self.path).path != "/api/buscar":
            return self._json(404, {"erro": "Não encontrado"})
        with _trava:
            if BUSCA["rodando"]:
                return self._json(202, {"ok": True, "ja_rodando": True})
            cfg = ler_json(CONFIG, {}) or {}
            if not cfg.get("cep"):
                return self._json(400, {"erro": "Salve o CEP em Mais antes de buscar."})
            BUSCA["rodando"] = True
        threading.Thread(target=buscar, daemon=True).start()
        self._json(202, {"ok": True})


def main():
    os.makedirs(DATA, exist_ok=True)
    threading.Thread(target=laco_sincronizacao, daemon=True).start()
    servidor = ThreadingHTTPServer(("0.0.0.0", PORT), Painel)
    log(f"painel no ar na porta {PORT}; dados em {DATA}")
    servidor.serve_forever()


if __name__ == "__main__":
    main()
