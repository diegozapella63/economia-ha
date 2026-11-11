"""1.24.0: Benefícios do clube. A IA procura o que o clube de vantagens da loja dá, com a fonte; a resposta é conferida
(textos curtos, só benefícios com título, a fonte só se for endereço), guardada em clubes.json por loja e vai para a
página em /api/estado; com a IA desligada, a rota recusa."""
import unittest

from apoio import Cenario


class Beneficios(Cenario):
    def test_procura_confere_e_guarda(self):
        S, ha = self.S, self.ha
        self.config()
        ha.responde_ia("clube Fort Atacadista", {"clube": "Clube Mais", "custo": "Grátis", "como_entrar": "CPF no caixa ou o app",
                                                 "beneficios": [{"titulo": "Preço de clube", "detalhe": "Até 30% menos em produtos marcados."},
                                                                {"titulo": "", "detalhe": "sem título: sai"}, "lixo",
                                                                {"titulo": "Cupons no app", "detalhe": "x" * 400}],
                                                 "fonte": "https://www.fortatacadista.com.br/clube"})
        r = S.beneficios_clube({"nome": "Fort Atacadista", "clube": "Clube Mais"})
        self.assertEqual((r["clube"], r["custo"], r["como_entrar"], r["fonte"], r["loja"]),
                         ("Clube Mais", "Grátis", "CPF no caixa ou o app", "https://www.fortatacadista.com.br/clube", "Fort Atacadista"))
        self.assertEqual([b["titulo"] for b in r["beneficios"]], ["Preço de clube", "Cupons no app"])
        self.assertLessEqual(len(r["beneficios"][1]["detalhe"]), 220)
        guardado = S.ler_json(S.CLUBES_FILE)
        self.assertEqual(guardado[S.chave_loja("Fort Atacadista")]["clube"], "Clube Mais")
        pedido = ha.pedidos_de("ai_task/generate_data")[-1][3]
        self.assertIn("Fort Atacadista (Clube Mais)", pedido["instructions"])
        self.assertEqual(S.uso_resumo()["hoje"]["tipos"], {"clube": 1}, "conta no Uso da IA como Benefícios do clube")

    def test_sem_clube_e_respostas_estranhas(self):
        S, ha = self.S, self.ha
        self.config()
        ha.responde_ia("clube Mercadinho", {"clube": None})
        r = S.beneficios_clube({"nome": "Mercadinho"})
        self.assertEqual((r["clube"], r["beneficios"]), (None, []))
        ha.responde_ia("clube Outra", {"clube": "Vantagens", "beneficios": [], "fonte": "não é endereço"})
        self.assertIsNone(S.beneficios_clube({"nome": "Outra"})["fonte"])
        with self.assertRaises(S.ErroBusca):
            S.beneficios_clube({"nome": ""})
        with self.assertRaises(S.ErroBusca):
            S.limpa_clube(["lista"])

    def test_ia_desligada(self):
        self.config(usar_ia=False)
        with self.assertRaises(self.S.ErroBusca):
            self.S.beneficios_clube({"nome": "Fort"})


if __name__ == "__main__":
    unittest.main()
