"""Os fluxos pela API HTTP, com o servidor de verdade num processo, o Home Assistant falso (ha_falso.py) e as lojas
falsas: Buscar e o andamento (/api/busca), buscar itens, ler lista e encarte (POST + GET pelo id), IAs e Testar a IA,
listas do HA e sincronizar (com a junção pela revisão), versões, exportar, mapa e teste das lojas, lojas diretas,
folhetos, uso da IA, Falar, PUT /api/ofertas, limites de tamanho, integrações (chaves nunca voltam) e o main()."""
import base64
import http.client
import io
import json
import os
import socket
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
import zipfile

from apoio import APP, CEP, LojasFalsas, categoria, limpa, porta_livre, prod, servidor
from ha_falso import Erro, HAFalso, estado

PNG = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\0" * 64).decode()


class Servidor(unittest.TestCase):
    """Lojas falsas + HA falso + o servidor do add-on num processo, uma vez por classe."""

    @classmethod
    def prepara(cls):
        pass

    @classmethod
    def setUpClass(cls):
        cls.lojas = LojasFalsas().__enter__()
        cls.ha = HAFalso().__enter__()
        cls.lojas.catalogo["giassi"] = [prod("Coxinha da Asa de Frango Resfriada Kg", 21.90, "Açougue/Aves", "kg", 1),
                                        prod("Café Pilão Tradicional 500g", 19.90, "Mercearia/Café")]
        S, cls.pasta, _ = servidor()
        cls.S = S
        cls.prepara()
        cls.porta = porta_livre()
        env = dict(os.environ, OFERTAS_DATA=cls.pasta, OFERTAS_PORT=str(cls.porta), OFERTAS_MEDIA=os.path.join(cls.pasta, "media"), OFERTAS_SHARE=os.path.join(cls.pasta, "share"),
                   OFERTAS_ALLOW_ALL="1", OFERTAS_ESPERA_COTA="0", OFERTAS_SYNC_SEG="3600", **cls.lojas.env_servicos(), **cls.ha.env())
        cls.saida = open(os.path.join(cls.pasta, "servidor.log"), "w")
        cls.proc = subprocess.Popen([sys.executable, os.path.join(APP, "server.py")], env=env, stdout=cls.saida, stderr=subprocess.STDOUT)
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", cls.porta), 0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("o servidor não subiu")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(10)
        cls.saida.close()
        cls.ha.__exit__()
        cls.lojas.__exit__()
        limpa(cls.pasta)

    def pede(self, metodo, caminho, corpo=None, bruto=None, cab=None):
        dados = bruto if bruto is not None else (json.dumps(corpo).encode() if corpo is not None else None)
        h = dict({"Content-Type": "application/json"} if dados is not None else {}, **(cab or {}))
        req = urllib.request.Request(f"http://127.0.0.1:{self.porta}{caminho}", data=dados, method=metodo, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                tipo, d = r.headers.get("Content-Type", ""), r.read()
                self.cab = r.headers
                return r.status, (json.loads(d) if tipo.startswith("application/json") else d)
        except urllib.error.HTTPError as e:
            self.cab = e.headers
            t = e.read()
            try:
                return e.code, json.loads(t)
            except ValueError:
                return e.code, t

    def config(self, **kw):
        st, d = self.pede("GET", "/api/estado")
        rev = int((d["config"] or {}).get("rev") or 0)
        cfg = dict({"cep": CEP, "raio_km": 2, "categorias": ["mercados"], "lista": []}, **kw)
        st, d = self.pede("PUT", "/api/config", dict(cfg, rev=rev))
        self.assertEqual(st, 200)
        return d["config"]

    def espera(self, caminho, cond, segundos=20):
        fim = time.time() + segundos
        while time.time() < fim:
            st, d = self.pede("GET", caminho)
            if cond(d):
                return d
            time.sleep(0.05)
        self.fail(f"{caminho} não chegou lá: {d}")

    def so_tamanho(self, metodo, caminho, tamanho):
        """Manda só o cabeçalho com o tamanho (sem o corpo): o servidor recusa antes de ler."""
        c = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=10)
        c.putrequest(metodo, caminho)
        c.putheader("Content-Type", "application/json")
        c.putheader("Content-Length", str(tamanho))
        c.endheaders()
        r = c.getresponse()
        d = json.loads(r.read() or b"{}")
        c.close()
        return r.status, d


class Buscar(Servidor):
    def test_buscar_e_o_andamento(self):
        ha = self.ha
        st, d = self.pede("PUT", "/api/config", {"rev": 0, "categorias": ["mercados"], "lista": []})
        st, d = self.pede("POST", "/api/buscar")
        self.assertEqual((st, d), (400, {"erro": "Salve o CEP em Mais › Casa antes de buscar."}))
        self.config(lista=[{"produto": "Coxinha da asa"}, {"produto": "Abacaxi"}], opcoes={"itens_sem_preco": False})
        solta = threading.Event()

        def devagar(corpo):
            solta.wait(15)
            return {"lojas": [{"rede": "Bistek", "distancia_km": 1.5}], "lista": [{"item": 2, "precos": [{"rede": "Bistek", "preco": 8.9}]}]}
        ha.responde_ia("EconomIA: mercados", devagar)
        st, d = self.pede("POST", "/api/buscar")
        self.assertEqual((st, d), (202, {"ok": True}))
        b = self.espera("/api/busca", lambda b: b.get("etapa") == "mercados")
        self.assertEqual((b["rodando"], b["atual"], b["total"], b["erro"]), (True, 1, 1, None), "o andamento enquanto a IA pensa")
        st, d = self.pede("POST", "/api/buscar")
        self.assertEqual((st, d), (202, {"ok": True, "ja_rodando": True}), "uma busca de cada vez")
        st, d = self.pede("POST", "/api/lojas-mapa/atualizar", {})
        self.assertEqual(d, {"ok": False, "msg": "Espere a busca terminar."})
        st, e = self.pede("GET", "/api/estado")
        self.assertTrue(e["busca"]["rodando"])
        solta.set()
        b = self.espera("/api/busca", lambda b: not b["rodando"])
        self.assertEqual((b["erro"], b["etapa"], b["chamadas_ia"]), (None, None, 1))
        self.assertTrue(b["terminou_em"])
        st, e = self.pede("GET", "/api/estado")
        lista = {i["produto"]: i for i in e["ofertas"]["lista"]}
        self.assertEqual(lista["Abacaxi"]["precos"], {"merc-bistek": 8.9})
        self.assertEqual(self.S.valor_total(lista["Coxinha da asa"]["precos"]["merc-giassi"]), 21.9)
        self.assertEqual(e["uso_ia"]["hoje"]["chamadas"], 1)

    def test_buscar_itens(self):
        ha = self.ha
        self.config(lista=[{"produto": "Café Pilão 500 g"}, {"produto": "Leite"}])
        st, d = self.pede("POST", "/api/buscar-itens", {"itens": ["Não está na lista", 3]})
        self.assertEqual((st, d), (400, {"erro": "Esse item não está na lista."}))
        n = len(ha.chamadas_ia)
        ha.responde_ia("itens sem preço", {"lista": [{"item": 1, "precos": [{"rede": "Bistek", "categoria": "mercados", "preco": 18.5}]}]})
        st, d = self.pede("POST", "/api/buscar-itens", {"itens": ["café pilão 500 G", "Café Pilão 500 g"]})
        self.assertEqual(st, 202)
        b = self.espera("/api/busca", lambda b: not b["rodando"])
        self.assertIsNone(b["erro"])
        self.assertEqual(len(ha.chamadas_ia), n + 1)
        self.assertIn("1) Café Pilão 500 g", ha.chamadas_ia[-1]["instructions"], "o nome como está na lista, uma vez")
        self.assertNotIn("Leite", ha.chamadas_ia[-1]["instructions"])

    def test_ia_desligada_e_cota(self):
        self.config(lista=[{"produto": "Café Pilão 500 g"}], usar_ia=False)
        st, d = self.pede("POST", "/api/ler-lista", {"texto": "leite"})
        self.assertEqual((st, d["erro"]), (400, self.S.IA_DESLIGADA))
        st, d = self.pede("POST", "/api/ler-encarte", {"imagens": [PNG], "loja": "X"})
        self.assertEqual(st, 400)
        st, d = self.pede("POST", "/api/voz", bruto=b"\0" * 32000)
        self.assertEqual((st, d["erro"]), (400, self.S.IA_DESLIGADA))
        self.config(lista=[{"produto": "Abacaxi"}], opcoes={"itens_sem_preco": False})
        self.ha.regras_ia.insert(0, {"quando": "mercados", "resp": Erro(429, "quota"), "vezes": 2})
        self.pede("POST", "/api/buscar")
        b = self.espera("/api/busca", lambda b: not b["rodando"])
        self.assertIn("A cota da IA acabou", b["erro"])


class LerComIA(Servidor):
    def test_ler_lista_pelo_id(self):
        ha = self.ha
        self.config(lista=[{"produto": "Leite integral"}])
        st, d = self.pede("POST", "/api/ler-lista", {"texto": "   "})
        self.assertEqual((st, d), (400, {"erro": "Escolha uma foto ou cole o texto da mensagem."}))
        ha.responde_ia("ler lista", {"itens": [{"produto": "leite integral"}, {"produto": "Pão francês", "quantidade": "6"}]})
        st, d = self.pede("POST", "/api/ler-lista", {"texto": "leite integral e 6 pães", "imagens": [PNG]})
        self.assertEqual(st, 202)
        job = d["id"]
        r = self.espera("/api/ler-lista?id=" + job, lambda r: r["status"] != "lendo")
        self.assertEqual(r, {"status": "pronto", "itens": [{"produto": "Leite integral", "ja_na_lista": True},
                                                           {"produto": "Pão francês", "ja_na_lista": False, "quantidade": "6"}], "erro": None})
        st, d = self.pede("GET", "/api/ler-lista?id=nao-existe")
        self.assertEqual((st, d), (404, {"erro": "Leitura não encontrada."}))
        self.assertEqual(os.listdir(os.path.join(self.pasta, "media", "economia")), [], "a foto sai da pasta de mídia")

    def test_ler_encarte(self):
        ha = self.ha
        self.config(lista=[{"produto": "Café Pilão 500 g"}])
        st, d = self.pede("POST", "/api/ler-encarte", {"imagens": [PNG]})
        self.assertEqual((st, d), (400, {"erro": "Escolha as fotos do encarte e diga de qual loja é."}))
        ha.responde_ia("encarte Mercado Kuntze", {"ofertas": [{"produto": "Café Pilão 500 g", "preco": 15.98}],
                                                  "lista": [{"item": 1, "precos": [{"preco": 15.98}]}]})
        st, d = self.pede("POST", "/api/ler-encarte", {"imagens": [PNG], "loja": "Mercado Kuntze", "categoria": "mercados"})
        self.assertEqual(st, 202)
        r = self.espera("/api/ler-lista?id=" + d["id"], lambda r: r["status"] != "lendo")
        self.assertEqual((r["status"], r["loja"], r["ofertas"], r["precos"]), ("pronto", "Mercado Kuntze", 1, ["Café Pilão 500 g"]))
        st, e = self.pede("GET", "/api/estado")
        cafe = next(i for i in e["ofertas"]["lista"] if i["produto"] == "Café Pilão 500 g")
        self.assertEqual(cafe["precos"]["merc-mercado-kuntze"], 15.98)


class IasEListas(Servidor):
    @classmethod
    def prepara(cls):
        cls.ha.tarefa_ia("ai_task.claude", "Claude")
        cls.ha.agente("conversation.gemini", "Gemini")
        cls.ha.lista("todo.compras", "Compras")
        cls.ha.item("todo.compras", "Pão francês")

    def test_ias_e_testar(self):
        ha = self.ha
        self.config()
        st, d = self.pede("GET", "/api/ias")
        self.assertEqual(d, {"tarefas": [{"id": "ai_task.claude", "nome": "Claude", "anexos": True}], "agentes": [{"id": "conversation.gemini", "nome": "Gemini"}]})
        ha.responde_ia("teste", {"busca": True, "exemplo": "Giassi R$ 19,90", "fonte": "https://giassi.com.br/cafe"})
        st, d = self.pede("POST", "/api/testar-ia", {"uso": "busca"})
        self.assertEqual(d, {"ok": True, "msg": "Pronta para buscar ofertas. Exemplo: Giassi R$ 19,90"})
        self.config(ia={"fotos": "ai_task.claude"})
        st, d = self.pede("POST", "/api/testar-ia", {"uso": "fotos"})
        self.assertEqual(d, {"ok": True, "msg": "Pronta para ler fotos."})
        st, u = self.pede("GET", "/api/uso-ia")
        self.assertEqual((u["hoje"]["chamadas"], u["hoje"]["tipos"]), (1, {"teste": 1}))
        ha.token, antes = "outra", ha.token
        try:
            st, d = self.pede("GET", "/api/ias")
            self.assertEqual((st, d), (502, {"erro": "O Home Assistant recusou o pedido (401).", "tarefas": [], "agentes": []}))
            st, d = self.pede("GET", "/api/todos")
            self.assertEqual((st, d), (502, {"erro": "O Home Assistant recusou o pedido (401)."}))
        finally:
            ha.token = antes

    def test_listas_e_sincronizar_com_a_revisao(self):
        st, d = self.pede("GET", "/api/todos")
        self.assertEqual(d, {"listas": [{"id": "todo.compras", "nome": "Compras"}]})
        cfg = self.config(lista=[{"produto": "Leite", "compras": []}], sync={"ativo": True, "entidade": "todo.compras"})
        rev_painel = cfg["rev"]
        st, d = self.pede("POST", "/api/sincronizar-lista")
        self.assertEqual(d["sync"]["chegaram"], 1)
        self.assertEqual(d["rev"], rev_painel + 1, "o pão do HA entrou e a revisão subiu")
        # o painel salva com a revisão antiga (sem o pão): o servidor junta o que veio do HA
        st, d = self.pede("PUT", "/api/config", {"rev": rev_painel, "cep": CEP, "lista": [{"produto": "Leite", "compras": []}, {"produto": "Ovos"}],
                                                 "sync": {"ativo": True, "entidade": "todo.compras"}})
        self.assertTrue(d["mesclado"])
        self.assertEqual([i["produto"] for i in d["config"]["lista"]], ["Leite", "Ovos", "Pão francês"])
        st, d = self.pede("POST", "/api/sincronizar-lista")
        self.assertIn("Ovos", [i["summary"] for i in self.ha.todos["todo.compras"]], "o item novo do painel vai para o HA")
        self.ha.token, antes = "outra", self.ha.token
        try:
            st, d = self.pede("POST", "/api/sincronizar-lista")
            self.assertEqual(d["sync"]["erro"], "O Home Assistant recusou o pedido (401).")
        finally:
            self.ha.token = antes

    def test_usuario_do_ingress_nao_sai_do_add_on(self):
        st, e = self.pede("GET", "/api/estado", cab={"X-Remote-User-Display-Name": "Davi", "X-Remote-User-Name": "davi.souza@exemplo.com.br"})
        self.assertEqual(e["usuario"], "Davi")
        st, e = self.pede("GET", "/api/estado", cab={"X-Remote-User-Name": "davi"})
        self.assertEqual(e["usuario"], "davi")
        self.pede("POST", "/api/sincronizar-lista", cab={"X-Remote-User-Name": "davi.souza@exemplo.com.br"})
        self.assertNotIn("@exemplo.com.br", self.ha.tudo_que_chegou())


class Dados(Servidor):
    def test_versoes(self):
        self.config(lista=[{"produto": "A"}, {"produto": "B"}])
        st, d = self.pede("POST", "/api/versoes/guardar", {"motivo": "importar"})
        nome = d["nome"]
        self.assertRegex(nome, r"^config-\d{8}-\d{6}-importar\.json$")
        self.config(lista=[])
        st, d = self.pede("GET", "/api/versoes")
        v = next(x for x in d["versoes"] if x["nome"] == nome)
        self.assertEqual((v["motivo"], v["itens"], v["cep"]), ("antes de importar", 2, CEP))
        st, d = self.pede("POST", "/api/versoes/restaurar", {"nome": nome})
        self.assertEqual([i["produto"] for i in d["config"]["lista"]], ["A", "B"])
        st, d = self.pede("POST", "/api/versoes/restaurar", {"nome": "../segredos.json"})
        self.assertEqual((st, d), (400, {"erro": "Versão não encontrada."}))
        st, d = self.pede("POST", "/api/versoes/restaurar", {"nome": "config-20200101-000000-auto.json"})
        self.assertEqual(st, 400)

    def test_exportar(self):
        self.config(lista=[{"produto": "Leite", "compras": ["2026-10-01", "2026-10-11"]}])
        self.pede("PUT", "/api/ofertas", {"gerado_em": "2026-11-01T10:00:00", "categorias": [categoria("mercados", [("merc-giassi", "Giassi", 1.0)])],
                                          "lista": [{"produto": "Leite", "precos": {"merc-giassi": 4.89}}]})
        st, d = self.pede("GET", "/api/exportar/lista.json")
        self.assertRegex(self.cab["Content-Disposition"], r'attachment; filename="economia-minha-lista-\d{4}-\d\d-\d\d\.json"')
        self.assertEqual((d["app"], d["ultima_busca"], d["lista"][0]["compra_a_cada_dias"]), ("EconomIA", "2026-11-01T10:00:00", 10))
        st, x = self.pede("GET", "/api/exportar/lista.xlsx")
        self.assertIn("spreadsheetml", self.cab["Content-Type"])
        folha = zipfile.ZipFile(io.BytesIO(x)).read("xl/worksheets/sheet1.xml").decode()
        self.assertIn("Leite", folha)
        self.assertIn("11/10/2026", folha)
        st, o = self.pede("GET", "/api/exportar/ofertas.json")
        self.assertEqual(o["lista"][0]["precos"], {"merc-giassi": 4.89})
        self.assertIn("economia-ofertas-", self.cab["Content-Disposition"])

    def test_put_ofertas_e_limites(self):
        st, d = self.pede("PUT", "/api/ofertas", {"lista": []})
        self.assertEqual((st, d), (400, {"erro": "Faltou a lista de categorias."}))
        st, d = self.pede("PUT", "/api/nao-existe", {"x": 1})
        self.assertEqual(st, 404)
        st, d = self.pede("POST", "/api/nao-existe", {"x": 1})
        self.assertEqual(st, 404)
        self.assertEqual(self.so_tamanho("PUT", "/api/config", 2 * 1024 * 1024 + 1), (413, {"erro": "Conteúdo vazio ou grande demais."}))
        self.assertEqual(self.so_tamanho("POST", "/api/ler-lista", 16 * 1024 * 1024 + 1)[0], 413, "fotos: até 16 MB")
        self.assertEqual(self.so_tamanho("POST", "/api/voz", self.S.voz.MAX_BYTES + 4097), (413, {"erro": "Fale até 2 minutos de cada vez."}))
        st, d = self.pede("PUT", "/api/config", bruto=b"x" * 1000)
        self.assertEqual((st, d), (400, {"erro": "Conteúdo inválido."}))
        grande = {"rev": 0, "cep": CEP, "lista": [], "nota": "x" * (2 * 1024 * 1024 - 100)}
        st, d = self.pede("PUT", "/api/config", grande)
        self.assertEqual(st, 200, "abaixo de 2 MB passa")


class MapaEFontes(Servidor):
    @classmethod
    def prepara(cls):
        b = cls.lojas.base
        cls.lojas.rotas["/overpass"] = lambda p: {"elements": [
            {"type": "node", "lat": -26.3045, "lon": -48.85, "tags": {"name": "Farmácia Bem Estar", "amenity": "pharmacy", "website": b + "/lenta/"}},
            {"type": "node", "lat": -26.309, "lon": -48.85, "tags": {"name": "Mercado Kuntze", "shop": "supermarket"}}]}
        cls.solta = threading.Event()
        cls.lojas.rotas["/lenta/robots.txt"] = lambda p: (cls.solta.wait(20), (404, "", "text/plain"))[1]

    def test_encontrar_lojas_e_o_teste(self):
        self.config(categorias=["farmacias", "mercados"], usar_ia=False)
        st, d = self.pede("POST", "/api/lojas-mapa/atualizar", {"raio_km": 2})
        self.assertIn(d["msg"], ("Achei 1 farmácias e 1 mercados até 2 km (OpenStreetMap).", "Achei 1 mercados e 1 farmácias até 2 km (OpenStreetMap)."))
        self.assertEqual(d["lojas"], {"farmacias": 1, "mercados": 1})
        st, m = self.pede("GET", "/api/lojas-mapa")
        self.assertEqual(m["fontes"], ["OpenStreetMap"])
        self.assertEqual({c: [l["nome"] for l in v] for c, v in m["lojas"].items()}, {"farmacias": ["Farmácia Bem Estar"], "mercados": ["Mercado Kuntze"]})
        self.espera("/api/lojas-mapa/teste", lambda t: t["rodando"])  # parado no site da Farmácia Bem Estar, que demora
        st, d = self.pede("POST", "/api/lojas-mapa/atualizar", {})
        self.assertEqual(d["msg"], "Ainda estou testando as lojas. Espere terminar.")
        st, d = self.pede("POST", "/api/lojas-mapa/testar-loja", {"categoria": "mercados", "rede": "merc-mercado-kuntze"})
        self.assertEqual((st, d), (409, {"ok": False, "msg": "Já tem um teste rodando. Espere ele terminar."}))
        self.solta.set()
        t = self.espera("/api/lojas-mapa/teste", lambda t: not t["rodando"])
        self.assertEqual((t["total"], t["atual"]), (2, 2))
        self.assertTrue(t["resumo"].startswith("Testei 2 lojas"), t["resumo"])
        st, d = self.pede("POST", "/api/lojas-mapa/testar-loja", {"categoria": "brinquedos", "rede": "x"})
        self.assertEqual((st, d), (400, {"ok": False, "msg": "Loja inválida."}))
        st, d = self.pede("POST", "/api/lojas-mapa/testar-loja", {"categoria": "mercados", "rede": "merc-mercado-kuntze"})
        self.assertEqual((st, d), (200, {"ok": True}))
        t = self.espera("/api/lojas-mapa/teste", lambda t: not t["rodando"] and (t["resumo"] or "").startswith("Mercado Kuntze"))
        st, e = self.pede("GET", "/api/estado")
        kuntze = next(l for c in e["ofertas"]["categorias"] for l in c["lojas"] if l["rede"] == "merc-mercado-kuntze")
        self.assertEqual(kuntze["preco_fonte"]["como"], "nenhum")

    def test_lojas_diretas_e_folhetos(self):
        self.config(lojas={"adicionar": [{"nome": "Mercado Kuntze", "categoria": "mercados"}]})
        st, d = self.pede("GET", "/api/lojas-diretas")
        ids = {x["id"]: x for x in d["lojas"]}
        self.assertEqual((ids["giassi"]["atende"], ids["angeloni"]["atende"]), (True, True))
        st, d = self.pede("GET", "/api/folhetos")
        self.assertEqual(d["lojas"][0], {"nome": "Mercado Kuntze", "categoria": "mercados", "status": None}, "a cadastrada primeiro, ainda sem leitura")


class Integracoes(Servidor):
    @classmethod
    def prepara(cls):
        cls.lojas.rotas["/google/nearby"] = lambda p: {"places": [{"id": "1", "displayName": {"text": "Farmácia Bem Estar"}, "types": ["pharmacy"],
                                                                   "location": {"latitude": -26.3045, "longitude": -48.85}}]}
        cls.lojas.rotas["/brave"] = lambda p: {"web": {"results": [{"url": "https://www.giassi.com.br", "title": "Giassi"}]}}
        cls.lojas.rotas["/graph/me/accounts"] = lambda p: {"data": [{"instagram_business_account": {"id": "99", "username": "casa"}}]}
        cls.lojas.rotas["/graph/99"] = lambda p: {"business_discovery": {"username": "instagram"}}
        cls.lojas.rotas["/graph/debug_token"] = lambda p: {"data": {"expires_at": 0}}

    def test_chaves_testadas_e_nunca_devolvidas(self):
        for corpo in ({"google": {"key": " chave-google-secreta "}}, {"brave": {"key": "chave-brave-secreta"}},
                      {"instagram": {"token": "EAAG-token-secreto"}}):
            st, d = self.pede("PUT", "/api/integracoes", corpo)
            self.assertEqual(st, 200)
        st, d = self.pede("GET", "/api/integracoes")
        self.assertEqual((d["google"], d["brave"], d["instagram"]), ({"tem_chave": True}, {"tem_chave": True}, {"tem_chave": True, "usuario": None}))
        for serv, msg in (("google", "Pronta: 1 farmácias a até 1 km, a mais perto é Farmácia Bem Estar (0,5 km)."),
                          ("brave", "Pronta: o app procura o site das lojas que o mapa não traz."),
                          ("instagram", "Pronta: conta @casa. Consigo ler os posts das contas comerciais das lojas. A chave não vence.")):
            st, d = self.pede("POST", "/api/integracoes/testar", {"servico": serv})
            self.assertEqual(d, {"ok": True, "msg": msg}, serv)
        g = self.lojas.pedidos_de("/google/nearby")[-1]
        self.assertEqual(g[2]["X-Goog-Api-Key"], "chave-google-secreta", "sem os espaços colados")
        st, d = self.pede("GET", "/api/integracoes")
        self.assertEqual(d["instagram"]["usuario"], "casa")
        st, e = self.pede("GET", "/api/estado")
        tudo = json.dumps([d, e])
        for segredo in ("chave-google-secreta", "chave-brave-secreta", "EAAG-token-secreto"):
            self.assertNotIn(segredo, tudo)
            self.assertNotIn(segredo, self.ha.tudo_que_chegou(), "nem para o Home Assistant")
        st, d = self.pede("POST", "/api/integracoes/testar", bruto=b"[]")
        self.assertEqual(d, {"ok": False, "msg": "Falta o App ID e a senha da Shopee em Mais › Configurações › Integrações."}, "sem serviço: a Shopee")
        for corpo in ({"google": None}, {"brave": None}, {"instagram": None}):
            self.pede("PUT", "/api/integracoes", corpo)
        st, d = self.pede("GET", "/api/integracoes")
        self.assertEqual((d["google"], d["brave"], d["instagram"]["tem_chave"]), ({"tem_chave": False}, {"tem_chave": False}, False))


class Falar(Servidor):
    @classmethod
    def prepara(cls):
        cls.ha.estados["stt.home_assistant_cloud"] = estado("stt.home_assistant_cloud", "unknown", friendly_name="Home Assistant Cloud")
        cls.ha.pipelines = {"pipelines": [{"id": "p1", "name": "Casa", "stt_engine": "stt.home_assistant_cloud", "stt_language": "pt-BR"}],
                            "preferred_pipeline": "p1"}

    def test_status_e_audio(self):
        self.config()
        st, d = self.pede("GET", "/api/voz/status")
        self.assertEqual((d["pronta"], d["usando"], d["opcoes"]), (True, "pipeline:p1", [{"id": "pipeline:p1", "nome": "Assistente: Casa (Home Assistant Cloud)",
                                                                                        "preferido": True}]))
        st, d = self.pede("POST", "/api/voz", bruto=b"\0\1" * 16000, cab={"Content-Type": "application/octet-stream"})
        self.assertEqual((st, d), (200, {"texto": "leite integral e café", "nome": "Assistente: Casa (Home Assistant Cloud)"}))
        st, d = self.pede("POST", "/api/voz", bruto=b"\0" * 100)
        self.assertEqual((st, d), (400, {"erro": "Não ouvi nada. Toque no microfone e fale."}))
        st, d = self.pede("POST", "/api/voz", bruto=b"")
        self.assertEqual(st, 413)


class Principal(unittest.TestCase):
    def test_main_no_mesmo_processo(self):
        """main(): cria a pasta de dados, liga a sincronização e serve o painel na porta de OFERTAS_PORT."""
        porta = porta_livre()
        S, pasta, msgs = servidor({"OFERTAS_PORT": str(porta), "OFERTAS_SYNC_SEG": "3600"})
        try:
            S.DATA = os.path.join(pasta, "nova")
            threading.Thread(target=S.main, daemon=True).start()
            for _ in range(100):
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{porta}/api/saude", timeout=2) as r:
                        self.assertEqual(json.loads(r.read()), {"ok": True})
                    break
                except OSError:
                    time.sleep(0.05)
            else:
                self.fail("o painel não subiu")
            self.assertTrue(os.path.isdir(S.DATA))
            self.assertIn("chave do Home Assistant: AUSENTE (a busca e a lista do HA não vão funcionar)", msgs)
            self.assertIn(f"painel no ar na porta {porta}; dados em {S.DATA}", msgs)
        finally:
            limpa(pasta)


if __name__ == "__main__":
    unittest.main()
