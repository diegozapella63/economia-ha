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

    def test_encontrar_lojas_procura_os_clubes(self):
        # 1.36.0: no Encontrar lojas, uma pergunta por rede acompanhada (farmácias, mercados e pet shops) ainda não procurada
        # ou procurada há mais de 60 dias; uma vez cada rede, até o máximo; online fica de fora
        S, ha = self.S, self.ha
        cfg = self.config()
        ha.responde_ia("clube", {"clube": "Clube Teste", "beneficios": [{"titulo": "Desconto", "detalhe": "10%"}]})
        velho = (S.datetime.now(S.timezone.utc) - S.timedelta(days=90)).isoformat(timespec="seconds")
        S.gravar_json(S.CLUBES_FILE, {S.chave_loja("Farmácia Lua"): {"clube": None, "beneficios": [], "em": S.agora()},
                                      S.chave_loja("Atacado Sol"): {"clube": "Velho", "beneficios": [], "em": velho}})
        alvos = [("farmacias", "farm-lua", "Farmácia Lua", {}), ("mercados", "merc-sol", "Atacado Sol", {}),
                 ("mercados", "merc-azul", "Mercado Azul", {}), ("mercados", "merc-azul2", "Mercado Azul", {}),
                 ("online", "onli-x", "Loja Online", {}), ("petshops", "pets-cao", "Pet Cão", {})]
        self.assertEqual(S.clubes_das_lojas(cfg, alvos), 3, "Atacado Sol (velho), Mercado Azul (uma vez) e Pet Cão")
        nomes = [p[3]["instructions"] for p in ha.pedidos_de("ai_task/generate_data")]
        self.assertEqual(sum("Mercado Azul" in t for t in nomes), 1)
        self.assertFalse(any("Farmácia Lua" in t or "Loja Online" in t for t in nomes))
        self.assertEqual(S.ler_json(S.CLUBES_FILE)[S.chave_loja("Atacado Sol")]["clube"], "Clube Teste")
        self.assertEqual(S.clubes_das_lojas(cfg, alvos), 0, "tudo procurado: nenhuma pergunta")
        self.assertEqual(S.clubes_das_lojas(cfg, [("mercados", "m1", "Rede Um", {}), ("mercados", "m2", "Rede Dois", {})], maximo=1), 1)
        self.assertEqual(S.clubes_das_lojas(dict(cfg, usar_ia=False), [("mercados", "m3", "Rede Tres", {})]), 0, "sem a IA, nada")

    def test_ia_desligada(self):
        self.config(usar_ia=False)
        with self.assertRaises(self.S.ErroBusca):
            self.S.beneficios_clube({"nome": "Fort"})


if __name__ == "__main__":
    unittest.main()
