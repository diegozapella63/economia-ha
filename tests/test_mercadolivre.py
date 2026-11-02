"""Previsor de categorias do Mercado Livre: autorização, renovação do acesso, erros, limites, cache e o filtro."""
import time
import unittest

from apoio import LojasFalsas, limpa, servidor


class Base(unittest.TestCase):
    def setUp(self):
        self.lojas = LojasFalsas().__enter__()
        self.lojas.categorias_ml_padrao()
        self.S, self.pasta, self.log = servidor(self.lojas.env())

    def tearDown(self):
        self.lojas.__exit__()
        limpa(self.pasta)

    def configura(self, **mais):
        seg = self.S.segredos()
        seg["ml"] = dict({"app_id": "123456", "secret": "segredo-ml", "url_retorno": "https://www.google.com"}, **mais)
        self.S.grava_segredos(seg)

    def conecta(self):
        self.configura()
        self.S.ml_conectar("https://www.google.com/?code=TG-abc123&state=x")


class Autorizacao(Base):
    def test_endereco_de_autorizar(self):
        self.configura()
        u = self.S.ml_autorizar_url()
        self.assertTrue(u.startswith(self.lojas.base + "/ml-auth?"))
        self.assertIn("response_type=code", u)
        self.assertIn("client_id=123456", u)
        self.assertIn("redirect_uri=https%3A%2F%2Fwww.google.com", u)
        self.assertIsNone(self.S.ml_autorizar_url({"app_id": "1"}), "sem URL de retorno não dá para autorizar")

    def test_conectar_pelo_endereco_ou_so_pelo_codigo(self):
        S = self.S
        self.configura()
        self.assertFalse(S.ml_ligado())
        S.ml_conectar("TG-abc123")
        self.assertTrue(S.ml_ligado())
        c = S.ml_conf()
        self.assertEqual((c["access_token"], c["refresh_token"]), ("tok-1", "r-1"))
        self.assertGreater(c["expira"], time.time() + 3600)

    def test_codigo_errado_ou_faltando_dados(self):
        S = self.S
        self.configura()
        with self.assertRaises(S.ErroBusca) as e:
            S.ml_conectar("https://www.google.com/?code=TG-errado")
        self.assertIn("Autorize de novo", str(e.exception))
        with self.assertRaises(S.ErroBusca):
            S.ml_conectar("lixo com espaço")
        self.configura(secret="")
        with self.assertRaises(S.ErroBusca) as e:
            S.ml_conectar("TG-abc123")
        self.assertIn("Salve antes", str(e.exception))

    def test_chave_secreta_errada(self):
        S = self.S
        self.configura(secret="outra")
        with self.assertRaises(S.ErroBusca) as e:
            S.ml_conectar("TG-abc123")
        self.assertIn("App ID ou a chave secreta", str(e.exception))


class Renovacao(Base):
    def test_renova_quando_vence_e_guarda_o_refresh_novo(self):
        S = self.S
        self.conecta()
        seg = S.segredos()
        seg["ml"]["expira"] = 0
        S.grava_segredos(seg)
        self.assertEqual(S.ml_token(), "tok-2")
        self.assertEqual(S.ml_conf()["refresh_token"], "r-2", "o Mercado Livre troca o refresh_token a cada uso")
        self.assertEqual(S.ml_token(), "tok-2", "ainda válido: não pede outro")
        self.assertEqual(len(self.lojas.pedidos_de("/ml/oauth/token")), 2)

    def test_autorizacao_revogada_apaga_o_acesso(self):
        S = self.S
        self.conecta()
        seg = S.segredos()
        seg["ml"].update(expira=0, refresh_token="r-revogado")
        S.grava_segredos(seg)
        with self.assertRaises(S.ErroBusca):
            S.ml_token()
        self.assertFalse(S.ml_ligado())
        self.assertNotIn("refresh_token", S.ml_conf())
        self.assertEqual(S.ml_conf()["app_id"], "123456", "o App ID continua")


class Previsor(Base):
    def test_previsao_guardada(self):
        S = self.S
        self.conecta()
        p = S.ml_prever("Carne moída bovina")
        self.assertEqual(p, [{"d": "MLB-BEEF", "c": "MLB3", "n": "Carnes Bovinas"}])
        S.ml_prever("CARNE MOÍDA   bovina")
        self.assertEqual(len(self.lojas.pedidos_de("domain_discovery")), 1, "o mesmo nome (normalizado) vem do cache")
        S.grava_ml()
        S2, _, _ = servidor(dict(self.lojas.env(), OFERTAS_DATA=self.pasta))
        self.assertEqual(S2.ml_prever("Carne moída bovina"), p, "o cache fica em categorias_ml.json")

    def test_sem_conexao_nao_pergunta(self):
        self.assertIsNone(self.S.ml_prever("Leite"))
        self.assertEqual(self.S.confere_ml("Leite", ["Leite Tirol"]), [None])

    def test_limite_por_hora(self):
        S = self.S
        self.conecta()
        S.ML_POR_HORA = 2
        self.assertIsNotNone(S.ml_prever("a1"))
        self.assertIsNotNone(S.ml_prever("a2"))
        self.assertIsNone(S.ml_prever("a3"), "passou do limite da hora: fica para depois")

    def test_429_pausa_dez_minutos(self):
        S = self.S
        self.conecta()
        self.lojas.ml["status_previsor"] = 429
        self.assertEqual(S.confere_ml("Carne moída", ["Hambúrguer"]), [None])
        self.assertIn("esperar", S._ml["erro"])
        self.lojas.ml["status_previsor"] = 200
        self.assertIsNone(S.ml_prever("outra coisa"), "pausado")
        self.assertGreater(S._ml["pausa"], time.time() + 500)

    def test_testar(self):
        S = self.S
        self.assertFalse(S.testar_ml()["ok"])
        self.configura()
        r = S.testar_ml()
        self.assertFalse(r["ok"])
        self.assertIn("Falta autorizar", r["msg"])
        S.ml_conectar("TG-abc123")
        r = S.testar_ml()
        self.assertTrue(r["ok"])
        self.assertIn("carne moída → Carnes Bovinas; hambúrguer → Hambúrgueres", r["msg"])


class Filtro(Base):
    def cands(self, *nomes):
        return [{"nome": n, "ean": ""} for n in nomes]

    def test_tira_outra_categoria_quando_confirma_uma(self):
        S = self.S
        self.conecta()
        c = self.cands("Carne Moída Bovina de Primeira Kg", "Almôndega de Carne Moída 500g", "Produto Desconhecido")
        self.assertEqual([x["nome"] for x in S.filtra_ml("Carne moída bovina de primeira", c)],
                         ["Carne Moída Bovina de Primeira Kg", "Produto Desconhecido"], "sem resposta do previsor, fica")
        self.assertTrue(any("outra categoria" in m for m in self.log))

    def test_nao_confirmando_nenhum_nada_sai(self):
        S = self.S
        self.conecta()
        c = self.cands("Almôndega de Carne Moída 500g", "Hambúrguer Bovino")
        self.assertEqual(S.filtra_ml("Carne moída bovina", c), c)

    def test_codigo_de_barras_conhecido_nunca_sai(self):
        S = self.S
        self.conecta()
        S.guarda_casados("Carne moída bovina", ["7891000100103"])
        c = [{"nome": "Carne Moída Bovina Kg", "ean": ""}, {"nome": "Hambúrguer da casa", "ean": "7891000100103"}]
        self.assertEqual(S.filtra_ml("Carne moída bovina", c), c)

    def test_ou_vale_a_categoria_de_qualquer_lado(self):
        S = self.S
        self.conecta()
        c = self.cands("Coxinha da Asa Kg", "Hambúrguer Bovino", "Carne Moída Kg")
        self.assertEqual([x["nome"] for x in S.filtra_ml("Coxinha da asa ou carne moída", c)], ["Coxinha da Asa Kg", "Carne Moída Kg"])

    def test_desligado_nao_filtra_nem_pergunta(self):
        S = self.S
        c = self.cands("Hambúrguer Bovino")
        self.assertEqual(S.filtra_ml("Carne moída", c), c)
        self.assertFalse(self.lojas.pedidos_de("domain_discovery"))

    def test_montar_item_passa_pelo_filtro(self):
        S = self.S
        self.conecta()
        ent, _ = S.montar_item("Carne moída bovina", {"Loja": [
            {"nome": "Carne Moída Bovina Kg", "preco": 39.9, "tam": (1, "kg"), "link": "a", "ean": ""},
            {"nome": "Almôndega de Carne Moída 1kg", "preco": 25.0, "tam": (1, "kg"), "link": "b", "ean": ""}]})
        self.assertEqual([p["preco"] for p in ent["precos"]], [39.9], "a almôndega mais barata não vira o preço da carne")


if __name__ == "__main__":
    unittest.main()
