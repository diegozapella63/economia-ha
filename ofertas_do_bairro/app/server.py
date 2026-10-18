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

Só usa a biblioteca padrão do Python.
"""
import io
import json
import os
import re
import threading
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
HA_API = os.environ.get("OFERTAS_HA_API", "http://supervisor/core/api")
# O ingress do Supervisor chega sempre deste endereço.
INGRESS_IPS = {"172.30.32.2", "127.0.0.1", "::1"}
ALLOW_ALL = os.environ.get("OFERTAS_ALLOW_ALL") == "1"  # só para testes fora do HA
MAX_BODY = 2 * 1024 * 1024

CATEGORIAS = {
    "farmacias": {"nome": "Farmácias", "singular": "Farmácia", "o_que": "farmácias e drogarias, de rede ou independentes"},
    "mercados": {"nome": "Mercados", "singular": "Mercado", "o_que": "supermercados, hipermercados e atacarejos"},
    "petshops": {"nome": "Pet shops", "singular": "Pet shop", "o_que": "pet shops e lojas de produtos para animais"},
}
TAGS = {"bebe", "pet", "gato", "cachorro", "alcool", "medicamento", "maquiagem", "geriatrico", "skincare", "suplementos",
        "cafe", "bucal", "limpeza", "carnes", "alimentos", "higiene", "lactose", "gluten", "acucar"}
FONTES = {"Site", "App", "Encarte", "Clube", "Instagram", "WhatsApp", "Tiendeo"}

BUSCA = {"rodando": False, "etapa": None, "atual": 0, "total": 0, "erro": None, "avisos": [], "terminou_em": None}
_trava = threading.Lock()


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


def url_ok(u):
    return isinstance(u, str) and u.startswith(("https://", "http://")) and len(u) < 600


def texto(v, limite=120):
    return str(v).strip()[:limite] if v not in (None, "") else None


def data_ok(v):
    return v if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) else None


def norm(s):
    t = unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


# ---------- IA do Home Assistant ----------
def opcoes():
    return ler_json(OPTIONS, {}) or {}


def chamar_ai_task(nome, instrucoes):
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        raise ErroBusca("O add-on não tem acesso ao Home Assistant. Reinstale a versão mais nova do add-on.")
    corpo = {"task_name": nome, "instructions": instrucoes}
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


def instrucoes_para(cat_id, cfg):
    cat = CATEGORIAS[cat_id]
    casa, excluir, restr, interesses = descreve_casa(cfg)
    lojas = cfg.get("lojas") or {}
    lista = [i.get("produto") if isinstance(i, dict) else str(i) for i in (cfg.get("lista") or [])]
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
Lojas para ignorar: {', '.join(lojas.get('ignorar') or []) or 'nenhuma'}. Lojas para incluir mesmo mais longe: {', '.join(lojas.get('manter') or []) or 'nenhuma'}. Lojas indicadas pelo morador: {', '.join(adicionadas) or 'nenhuma'}.

Responda somente com um objeto JSON, sem texto antes ou depois, neste formato:
{{
  "lojas": [{{"rede": "nome da rede ou da loja", "endereco": "rua e número", "distancia_km": 1.2, "horario": "Aberta até 22h", "fontes": ["Site", "App", "Encarte", "Clube", "Instagram", "WhatsApp", "Tiendeo"]}}],
  "cupons": [{{"rede": "...", "codigo": "CODIGO", "valor": 20, "beneficio": "R$ 20 de desconto", "condicao": "Pedidos acima de R$ 200", "valido_ate": "AAAA-MM-DD ou null", "oficial": true, "fonte": "URL"}}],
  "ofertas": [{{"rede": "...", "produto": "Nome · tamanho", "preco_normal": 10.0, "preco_oferta": 8.0, "tipo": "promo", "unidade": null, "condicao": null, "tags": ["alimentos"], "fonte": "URL"}}],
  "lista": [{{"produto": "texto exato do item da lista", "precos": [{{"rede": "...", "preco": 9.9, "fonte": "URL"}}]}}]
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
        ofertas.append(item)

    nomes_lista = {norm(i.get("produto") if isinstance(i, dict) else i): (i.get("produto") if isinstance(i, dict) else i)
                   for i in (cfg.get("lista") or [])}
    lista = {}
    for it in bruto.get("lista") or []:
        if not isinstance(it, dict):
            continue
        original = nomes_lista.get(norm(it.get("produto") or ""))
        if not original:
            continue
        for p in it.get("precos") or []:
            if not isinstance(p, dict) or not url_ok(p.get("fonte")):
                continue
            rid, preco = rede_id(p.get("rede")), numero(p.get("preco"))
            if rid and preco:
                lista.setdefault(original, {})[rid] = preco

    # toda rede citada precisa de uma loja, para o painel saber se a acompanha
    for rid in redes:
        lojas.setdefault(rid, {"rede": rid, "distancia_km": None, "horario": "", "endereco": None, "fontes": ["Site"]})

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


def buscar():
    cfg = ler_json(CONFIG, {}) or {}
    cats = [c for c in (cfg.get("categorias") or list(CATEGORIAS)) if c in CATEGORIAS]
    BUSCA.update({"rodando": True, "erro": None, "avisos": [], "atual": 0, "total": len(cats), "etapa": None})
    try:
        if not cfg.get("cep"):
            raise ErroBusca("Salve o CEP em Mais antes de buscar.")
        anterior = ler_json(OFERTAS, {}) or {}
        antigas = {c.get("id"): c for c in (anterior.get("categorias") or []) if isinstance(c, dict)}
        novas, lista, falhas = [], {}, []
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
            for prod, precos in parcial.items():
                lista.setdefault(prod, {}).update(precos)
        if not novas or len(falhas) == len(cats):
            raise ErroBusca(falhas[0] if falhas else "A busca não trouxe resultados.")
        gravar_json(OFERTAS, {
            "versao": 2, "gerado_em": agora(), "origem": "ia_home_assistant",
            "lista": [{"produto": p, "precos": v} for p, v in lista.items()],
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
        ps = sorted(({"loja": info[r]["nome"], "tipo": info[r]["tipo"], "preco": numero(v)}
                     for r, v in precos.get(norm(prod), {}).items() if acompanha(r) and numero(v)),
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
    server_version = "EconomIA/0.5"

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
                "busca": BUSCA,
            })
        elif rota == "/api/busca":
            self._json(200, BUSCA)
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
            cfg["atualizado_em"] = agora()
            gravar_json(CONFIG, cfg)
            self._json(200, {"ok": True})
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
    servidor = ThreadingHTTPServer(("0.0.0.0", PORT), Painel)
    log(f"painel no ar na porta {PORT}; dados em {DATA}")
    servidor.serve_forever()


if __name__ == "__main__":
    main()
