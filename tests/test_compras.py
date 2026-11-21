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
        self.assertEqual(c["reposicao"], {"cada": 1, "unidade": "mes", "texto": self.S._repor_cada({"cada": 1, "unidade": "mes"}), "proxima": "2026-11-28", "na_hora": False})
        h = self.S.compras_de("Creme de Mãos")
        self.assertEqual((h["na_lista"], h["vezes"], h["ultima"], h["reposicao"]), (False, 1, "2026-08-10", None), "fora da lista: as compras do histórico")
        s = self.S.compras_de("Leite integral")
        self.assertEqual((s["na_lista"], s["vezes"], s["ultima"]), (True, 0, ""), "um item só com o nome")
        n = self.S.compras_de("Pasta térmica")
        self.assertEqual((n["na_lista"], n["vezes"], n["compras"], n["reposicao"]), (False, 0, [], None))

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
        arq = os.path.join(self.pasta, "share", "integracao.json")
        self.assertTrue(os.path.exists(arq) or os.path.exists(self.S.INTEGRACAO_ARQ), "o servidor grava o arquivo ao subir")
