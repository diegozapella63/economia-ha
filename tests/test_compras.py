"""Compras no EconomIA (1.47.0): o InventarIA mostra, na ficha de um consumível, as compras dele daqui. O arquivo
share/economia/integracao.json (só com Opções › Reposição › InventarIA ligado, permissão do dono, chave própria e nenhum
dado da casa), o que o app sabe de um nome (lista, histórico, Reposição), o Pôr na lista e o Repor com as regras das
ferramentas, e a rota /api/integracao/compras (chave, desligado, 400). Dados inventados."""
import json
import os
import stat
import urllib.error
import urllib.request

from apoio import Cenario
from test_api_fluxos import Servidor

HOJE = "2026-11-02"


def _ler(arq):
    with open(arq, encoding="utf-8") as f:
        return f.read()


def casa():
    return {"lista": [{"produto": "Sabão líquido 3 L", "compras": ["2026-09-01", "2026-10-05", "2026-10-28"]}, "Leite integral"],
            "historico": [{"produto": "Creme de mãos", "compras": ["2026-08-10"], "saiu": "2026-08-11"}],
            "reposicao": [{"id": "r1", "nome": "Sabão líquido 3 L", "cada": 1, "unidade": "mes", "desde": "2026-10-28"}],
            "repor": {"inventario": True}}


class Compras(Cenario):
    def setUp(self):
        super().setUp()
        self.S.hoje_br = lambda: HOJE

    def test_o_arquivo_so_com_a_chave_ligada_e_sem_dados_da_casa(self):
        self.config(**casa())
        self.S.publicar_integracao()
        arq = self.S.INTEGRACAO_ARQ
        a = json.loads(_ler(arq))
        self.assertEqual(sorted(a), ["app", "chave", "compras", "gravado_em", "ip_url", "nome", "url", "versao"])
        self.assertEqual((a["app"], a["nome"], a["compras"], a["versao"]), ("economia", "EconomIA", "/api/integracao/compras", self.S.VERSAO))
        self.assertGreaterEqual(len(a["chave"]), 32)
        self.assertNotEqual(a["chave"], self.S.correria_chave(), "uma chave só dela")
        self.assertEqual(stat.S_IMODE(os.stat(arq).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(self.S.INTEGRACAO_CHAVE).st_mode), 0o600)
        self.assertNotIn("Sabão", _ler(arq), "nada da lista vai para a pasta share")
        self.S.publicar_integracao()
        self.assertEqual(json.loads(_ler(arq))["chave"], a["chave"], "a chave fica")
        self.config(**dict(casa(), repor={"inventario": False}))
        self.S.publicar_integracao()
        self.assertFalse(os.path.exists(arq), "desligado, o arquivo some")
        self.S.publicar_integracao()  # sem arquivo, nada quebra

    def test_o_que_o_app_sabe_de_um_nome(self):
        self.config(**casa())
        c = self.S.compras_de("sabao liquido 3 l")
        self.assertEqual((c["na_lista"], c["vezes"], c["ultima"], c["compras"]), (True, 3, "2026-10-28", ["2026-10-28", "2026-10-05", "2026-09-01"]))
        self.assertEqual(c["reposicao"], {"nome": "Sabão líquido 3 L", "cada": 1, "unidade": "mes", "texto": self.S._repor_cada({"cada": 1, "unidade": "mes"}), "proxima": "2026-11-28", "na_hora": False})
        h = self.S.compras_de("Creme de Mãos")
        self.assertEqual((h["na_lista"], h["vezes"], h["ultima"], h["reposicao"]), (False, 1, "2026-08-10", None), "fora da lista: as compras do histórico")
        s = self.S.compras_de("Leite integral")
        self.assertEqual((s["na_lista"], s["vezes"], s["ultima"]), (True, 0, ""), "um item só com o nome")
        n = self.S.compras_de("Pasta térmica")
        self.assertEqual((n["na_lista"], n["vezes"], n["compras"], n["reposicao"]), (False, 0, [], None))

    def test_o_nome_parecido_acha_o_item(self):
        """1.48.0: "Creme de Mãos" (o consumível) acha "Creme de mãos 50 g" (o item daqui); nunca outro tipo de coisa."""
        P = self.S.nome_parecido
        nomes = ["Creme de leite", "Creme de mãos Nivea 50 g", "Sabão líquido 3 L", "Sabão em pó", "Leite integral"]
        self.assertEqual(P("Creme de Mãos", nomes), "Creme de mãos Nivea 50 g")
        self.assertEqual(P("creme para a mão", nomes), "Creme de mãos Nivea 50 g", "sem o plural e sem as palavras vazias")
        self.assertEqual(P("Sabão líquido", nomes), "Sabão líquido 3 L")
        self.assertEqual(P("Sabão", nomes), "Sabão líquido 3 L", "dois igualmente perto: o primeiro da lista")
        self.assertEqual(P("Sabão líquido de coco", nomes + ["Sabão líquido de coco Ypê 1 L"]), "Sabão líquido de coco Ypê 1 L", "entre vários, o de nome mais perto")
        self.assertEqual(P("sabao liquido 3 l", nomes), "Sabão líquido 3 L", "o igual vem antes do parecido")
        self.assertIsNone(P("Creme dental", nomes), "uma palavra a mais dos dois lados: outro produto")
        self.assertIsNone(P("Leite de coco", nomes))
        self.assertIsNone(P("Mãos", nomes), "o tipo (a primeira palavra) tem de ser o mesmo")
        self.assertIsNone(P("500 g", nomes), "só o tamanho não é um nome")
        self.assertIsNone(P("Pasta térmica", []))
        self.config(**dict(casa(), lista=[{"produto": "Creme de mãos Nivea 50 g", "compras": ["2026-10-30"]}], historico=[],
                           reposicao=[{"id": "r2", "nome": "Creme de mãos Nivea 50 g", "cada": 2, "unidade": "mes", "desde": "2026-10-30"}]))
        c = self.S.compras_de("Creme de Mãos")
        self.assertEqual((c["item"], c["na_lista"], c["ultima"], c["reposicao"]["nome"]), ("Creme de mãos Nivea 50 g", True, "2026-10-30", "Creme de mãos Nivea 50 g"))
        r = self.S.compras_fazer({"nome": "Creme de Mãos", "acao": "lista"})
        self.assertIn("já está na lista", r["texto"])
        self.assertEqual(len(self.S.ler_config()["lista"]), 1, "não entra outro com o nome do InventarIA")
        r = self.S.compras_fazer({"nome": "Creme de Mãos", "acao": "repor", "dias": 180})
        reps = self.S.ler_config()["reposicao"]
        self.assertEqual([(x["nome"], x["cada"]) for x in reps], [("Creme de mãos Nivea 50 g", 6)], "muda a Reposição do item parecido")
        self.assertEqual(self.S.compras_de("Pasta térmica")["item"], "")

    def test_com_varias_listas_prontas_o_por_na_lista_pergunta_qual(self):
        self.config(**dict(casa(), opcoes={"listas": True}, listas=[{"id": "l1", "nome": "Mercado"}, {"id": "l2", "nome": "Farmácia"}]))
        self.assertEqual(self.S.compras_de("Pasta térmica")["listas"], ["Mercado", "Farmácia"])
        with self.assertRaises(self.S.ErroFerramenta) as e:
            self.S.compras_fazer({"nome": "Pasta térmica", "acao": "lista"})
        self.assertIn("Diga em qual lista", str(e.exception))
        r = self.S.compras_fazer({"nome": "Pasta térmica", "acao": "lista", "lista": "farmacia"})
        self.assertIn("Farmácia", r["texto"])
        item = next(i for i in self.S.ler_config()["lista"] if isinstance(i, dict) and i.get("produto") == "Pasta térmica")
        self.assertEqual(item["listas"], ["l2"])
        self.config(**dict(casa(), opcoes={"listas": True}, listas=[{"id": "l1", "nome": "Mercado"}]))
        self.assertEqual(self.S.compras_de("Pasta térmica")["listas"], [], "uma lista só: não há o que perguntar")
        self.config(**casa())
        self.assertEqual(self.S.compras_de("Pasta térmica")["listas"], [], "sem as listas prontas")

    def test_por_na_lista_traz_do_historico_e_repor_pela_duracao(self):
        self.config(**casa())
        r = self.S.compras_fazer({"nome": "Creme de mãos", "acao": "lista"})
        self.assertEqual((r["na_lista"], r["vezes"]), (True, 1))
        self.assertIn("Pus Creme de mãos na lista", r["texto"])
        cfg = self.S.ler_config()
        self.assertEqual([x for x in cfg["historico"] if x["produto"] == "Creme de mãos"], [], "saiu do histórico")
        self.assertIn("já está na lista", self.S.compras_fazer({"nome": "Creme de mãos", "acao": "lista"})["texto"])
        r = self.S.compras_fazer({"nome": "Creme de mãos", "acao": "repor", "dias": 180})
        self.assertEqual((r["reposicao"]["cada"], r["reposicao"]["unidade"], r["reposicao"]["proxima"]), (6, "mes", "2027-05-02"))
        rep = next(x for x in self.S.ler_config()["reposicao"] if x["nome"] == "Creme de mãos")
        self.assertEqual(rep["origem"], "inventario")
        self.assertEqual(self.S.DIARIO[-1]["tipo"], "repor")
        self.assertEqual([self.S._dias_em_cada(d) for d in (7, 14, 15, 30, 365, 730, 3650, 3651, 0, -3, "x", True, None)],
                         [(1, "semanas"), (2, "semanas"), (15, "dias"), (1, "meses"), (365, "dias"), (24, "meses"), (122, "meses"), None, None, None, None, None, None])
        for ruim, diz in (({"nome": "Creme", "acao": "apagar"}, "acao vale lista ou repor"), ({"nome": "Creme", "acao": "repor"}, "mande dias"),
                          ({"nome": "", "acao": "lista"}, "")):
            with self.assertRaises(self.S.ErroFerramenta) as e:
                self.S.compras_fazer(ruim)
            self.assertIn(diz, str(e.exception))


class InventarioFalso:
    """O InventarIA de mentira: /api/integracao/consumiveis e, 1.87.0 de lá, o POST .../comprado (guarda o que recebeu)."""

    def __init__(self, consumiveis):
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        dono = self
        self.pedidos, self.consumiveis, self.status = [], consumiveis, 200

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _manda(self, st, corpo):
                dado = json.dumps(corpo).encode()
                self.send_response(st)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(dado)))
                self.end_headers()
                self.wfile.write(dado)

            def do_GET(self):
                self._manda(200, {"versao": "1.87.0", "ligado": True, "consumiveis": dono.consumiveis})

            def do_POST(self):
                corpo = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                dono.pedidos.append({"caminho": self.path, "corpo": corpo, "chave": self.headers.get("Authorization")})
                if dono.status != 200:
                    return self._manda(dono.status, {"error": "x"})
                self._manda(200, {"id": "con-001", "dura_ate": "2027-05-02"})

        self.http = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.http.serve_forever, daemon=True).start()

    def liga(self, S):
        pasta = os.path.join(S.SHARE_CASA, "inventario")
        os.makedirs(pasta, exist_ok=True)
        with open(os.path.join(pasta, "integracao.json"), "w", encoding="utf-8") as f:
            json.dump({"url": f"http://127.0.0.1:{self.http.server_address[1]}", "chave": "chave-do-inventario"}, f)

    def fecha(self):
        self.http.shutdown()
        self.http.server_close()


class ComprouAvisaOInventario(Cenario):
    """1.49.0: o Comprei hoje (da tela e da CorrerIA) recomeça a Reposição do item e avisa o InventarIA."""

    def setUp(self):
        super().setUp()
        self.S.hoje_br = lambda: HOJE
        self.inv = InventarioFalso([{"id": "con-001", "nome": "Creme de mãos", "categoria": "Higiene", "duracao_dias": 180}])
        self.inv.liga(self.S)
        self.addCleanup(self.inv.fecha)

    def test_o_aviso_ao_inventario(self):
        self.config(**casa())
        r = self.S.inventario_comprado("Creme de mãos", 90)
        self.assertEqual(r, {"ok": True, "dura_ate": "2027-05-02"})
        p = self.inv.pedidos[-1]
        self.assertEqual((p["caminho"], p["corpo"], p["chave"]), ("/api/integracao/consumiveis/comprado", {"nome": "Creme de mãos", "dias": 90}, "Bearer chave-do-inventario"))
        self.S.inventario_comprado("Creme de mãos")
        self.assertEqual(self.inv.pedidos[-1]["corpo"], {"nome": "Creme de mãos"}, "sem os dias: só recomeça a contar")
        self.inv.status = 404
        self.assertEqual(self.S.inventario_comprado("Leite"), {"ok": False, "aviso": ""}, "não é um consumível de lá: nada a dizer")
        self.inv.status = 500
        self.assertEqual(self.S.inventario_comprado("Creme de mãos")["aviso"], "O InventarIA não respondeu.")
        n = len(self.inv.pedidos)
        self.config(**dict(casa(), repor={"inventario": False}))
        self.assertEqual(self.S.inventario_comprado("Creme de mãos"), {"ok": False, "aviso": ""})
        self.assertEqual(len(self.inv.pedidos), n, "com a chave desligada, nada é chamado")

    def test_a_compra_pela_correria_recomeca_a_reposicao_e_avisa(self):
        self.config(**dict(casa(), lista=[{"produto": "Creme de mãos Nivea 50 g", "compras": []}, {"produto": "Sabão líquido 3 L", "compras": []}], historico=[]))
        cfg = self.S.ler_config()
        texto, mud = self.S._ferr_comprei({"produto": "Creme de mãos Nivea 50 g", "dura_dias": 90}, cfg, {})
        rep = next(x for x in cfg["reposicao"] if x["nome"] == "Creme de mãos")
        self.assertEqual((rep["cada"], rep["unidade"], rep["desde"], rep["origem"]), (3, "mes", HOJE, "inventario"), "entra na Reposição com o nome do consumível")
        self.assertIn("volta em 02/02/2027", texto)
        self.assertIn("O InventarIA já sabe.", texto)
        self.assertEqual(self.inv.pedidos[-1]["corpo"], {"nome": "Creme de mãos", "dias": 90})
        self.assertEqual(mud["repor"]["nome"], "Creme de mãos", "a Reposição vai no diário, para a página aberta juntar")
        velho = {"reposicao": []}
        self.S.aplicar_diario(velho, dict(mud, rev=9))
        self.assertEqual(velho["reposicao"][0]["nome"], "Creme de mãos")
        n = len(self.inv.pedidos)
        texto, mud = self.S._ferr_comprei({"produto": "Sabão líquido 3 L"}, cfg, {})
        sab = next(x for x in cfg["reposicao"] if x["nome"] == "Sabão líquido 3 L")
        self.assertEqual((sab["desde"], sab["cada"]), (HOJE, 1), "sem a duração: a mesma, contando da compra")
        self.assertEqual(len(self.inv.pedidos), n, "não é um consumível: o InventarIA não é chamado")
        with self.assertRaises(self.S.ErroFerramenta):
            self.S._ferr_comprei({"produto": "Sabão líquido 3 L", "data": "2026-11-01", "dura_dias": 0}, cfg, {})


class ComprasPelaAPI(Servidor):
    @classmethod
    def prepara(cls):
        cls.S.gravar_config(dict({"cep": "88000-000", "raio_km": 2, "categorias": ["mercados"]}, **casa()))

    def pedir(self, metodo="GET", caminho="/api/integracao/compras?nome=Creme%20de%20m%C3%A3os", corpo=None, chave=None):
        chave = self.S.integracao_chave() if chave is None else chave
        req = urllib.request.Request(f"http://127.0.0.1:{self.porta}{caminho}", method=metodo,
                                     data=json.dumps(corpo).encode() if corpo is not None else None,
                                     headers={"Authorization": f"Bearer {chave}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def test_a_rota_com_a_chave(self):
        self.assertEqual(self.pedir(chave="errada")[0], 401)
        self.assertEqual(self.pedir(chave=self.S.correria_chave())[0], 401, "a chave do CorrerIA não vale aqui")
        st, c = self.pedir()
        self.assertEqual((st, c["na_lista"], c["ultima"]), (200, False, "2026-08-10"))
        self.assertEqual(self.pedir(caminho="/api/integracao/compras")[0], 400)
        st, r = self.pedir("POST", "/api/integracao/compras", {"nome": "Creme de mãos", "acao": "lista"})
        self.assertEqual((st, r["na_lista"]), (200, True))
        self.assertEqual(self.pedir("POST", "/api/integracao/compras", {"nome": "Creme de mãos", "acao": "x"})[0], 400)
        self.assertEqual(self.pedir("POST", "/api/integracao/compras", ["x"])[0], 400)
        # 1.49.0: a rota da página para o Comprei hoje (pelo ingress, sem chave): sem o InventarIA na casa, nada a fazer
        st, r = self.pedir("POST", "/api/reposicao/comprado", {"nome": "Creme de mãos", "dias": 90}, chave="")
        self.assertEqual((st, r["ok"]), (200, False))
        self.assertEqual(self.pedir("POST", "/api/reposicao/comprado", {"nome": "Creme de mãos", "dias": 0}, chave="")[0], 400)
        self.assertEqual(self.pedir("POST", "/api/reposicao/comprado", {"nome": ""}, chave="")[0], 400)
        arq = os.path.join(self.pasta, "share", "integracao.json")
        self.assertTrue(os.path.exists(arq) or os.path.exists(self.S.INTEGRACAO_ARQ), "o servidor grava o arquivo ao subir")
