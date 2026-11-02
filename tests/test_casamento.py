"""Casamento do item da lista com o produto da loja: tipo, palavras, parecido, restrições, "ou", vocabulário aprendido."""
import unittest

from apoio import NOMES_VOCAB, limpa, servidor

MARCAS = ["Ypê", "Veja", "Tirol", "Omo", "Comfort", "Neve", "Pilão", "Bauducco", "Qboa", "Scotch", "Araras", "Lysoform", "Itambé",
          "Melitta", "Santa", "Coamo", "Limpol", "Brilhante", "Downy", "Sadia"]


class Base(unittest.TestCase):
    vocabulario = True

    def setUp(self):
        self.S, self.pasta, self.log = servidor()
        if self.vocabulario:
            extra = [f"Leite Desnatado {m} 1L" for m in MARCAS] + [f"Café Torrado e Moído {m} 500g" for m in MARCAS]
            self.S.aprende_nomes(NOMES_VOCAB + extra, MARCAS)

    def tearDown(self):
        limpa(self.pasta)


class PalavrasDaBusca(Base):
    vocabulario = False

    def test_tira_tamanho_numeros_e_palavras_vazias(self):
        S = self.S
        self.assertEqual(S.palavras_busca("Detergente Ypê 500 ml"), ["detergente", "ype"])
        self.assertEqual(S.palavras_busca("Papel higiênico com 12"), ["papel", "higienico"])
        self.assertEqual(S.palavras_busca("Coxinha da asa ou asinha"), ["coxinha", "asa", "asinha"])
        self.assertEqual(S.palavras_busca(""), [])

    def test_alternativas_com_ou(self):
        S = self.S
        self.assertEqual(S.alternativas("Coxinha da asa ou asinha"), ["Coxinha da asa", "asinha"])
        self.assertEqual(S.alternativas("Arroz OU feijão"), ["Arroz", "feijão"])
        self.assertEqual(S.alternativas("Ovos"), ["Ovos"])
        self.assertEqual(S.alternativas("ou"), ["ou"], "sem palavra dos dois lados não divide")
        self.assertEqual(S.alternativas("Ouro branco"), ["Ouro branco"], "'ou' dentro de palavra não divide")

    def test_palavra_bate_igual_prefixo_e_fragrancia(self):
        S = self.S
        self.assertTrue(S.palavra_bate("leite", ["leite", "integral"]))
        self.assertTrue(S.palavra_bate("desinf", ["desinfetante"]), "prefixo de 4 letras ou mais")
        self.assertTrue(S.palavra_bate("desinfetantes", ["desinfetante"]), "plural")
        self.assertFalse(S.palavra_bate("sab", ["sabao"]), "prefixo de 3 letras não vale")
        self.assertTrue(S.palavra_bate("perfumado", ["alcool", "eucalipto"]), "perfumado vale pela fragrância")
        self.assertFalse(S.palavra_bate("perfumado", ["alcool", "tradicional"]))


class CasaLista(Base):
    def casa(self, item, *nomes):
        return self.S.casa_lista(item, list(nomes))

    def test_ate_tres_palavras_precisa_de_todas(self):
        self.assertEqual(self.casa("Leite integral", "Leite Integral Tirol 1L", "Leite Desnatado Tirol 1L"), [True, False])

    def test_tipo_tem_de_ser_o_tipo_do_produto(self):
        # "Limpador … e Álcool" não é álcool: outro tipo vem antes
        r = self.casa("Álcool", "Limpador Multiuso Limpeza Pesada Veja e Álcool 500ml", "Álcool Líquido 46 INPM Limpeza Araras 1L")
        self.assertEqual(r, [False, True])

    def test_marca_antes_do_tipo(self):
        self.assertEqual(self.casa("Detergente Ypê", "Ypê Detergente Líquido Neutro 500ml"), [True])

    def test_quatro_palavras_aceita_faltar_uma_mas_nao_a_segunda(self):
        r = self.casa("Carne moída bovina primeira", "Carne Moída Bovina Patinho kg", "Carne Bovina Primeira Acém kg")
        self.assertEqual(r, [True, False], "falta 'primeira' passa; falta 'moída' (logo depois do tipo) não")

    def test_restricao_nunca_fica_de_fora(self):
        self.assertEqual(self.casa("Leite sem lactose", "Leite Integral Tirol 1L"), [False])
        self.assertEqual(self.casa("Leite zero lactose", "Leite Zero Lactose Tirol 1L"), [True])

    def test_parecido_so_quando_ninguem_casa_inteiro(self):
        # nenhum álcool tem "cozinha" no nome: o mais parecido entra, marcado como "parecido"
        r = self.casa("Álcool limpeza cozinha", "Álcool Líquido 46 INPM Limpeza Araras 1L", "Desinfetante Pinho Veja 500ml")
        self.assertEqual(r, ["parecido", False])
        r = self.casa("Álcool limpeza cozinha", "Álcool Líquido 46 INPM Limpeza Araras 1L", "Álcool Limpeza Cozinha Qboa 1L")
        self.assertEqual(r, [False, True], "com casamento inteiro, o parecido sai")

    def test_perfumado_pela_fragrancia(self):
        r = self.casa("Álcool perfumado", "Álcool Líquido 46 INPM Limpeza Araras Lavanda 1L", "Álcool Líquido 46 INPM Limpeza Araras 1L")
        self.assertEqual(r, [True, False])

    def test_ou_casa_com_qualquer_lado(self):
        r = self.casa("Detergente Ypê ou Limpol", "Detergente Líquido Neutro Limpol 500ml", "Detergente Líquido Neutro Ypê 500ml",
                      "Detergente Líquido Neutro Brilhante 500ml")
        self.assertEqual(r, [True, True, False])

    def test_combina_sem_traducao(self):
        S = self.S
        self.assertTrue(S.combina("Leite integral", "Leite Integral Tirol 1L"))
        self.assertFalse(S.combina("Álcool limpeza cozinha", "Álcool Líquido 46 INPM Limpeza Araras 1L"), "sem parecido no casamento firme")

    def test_item_vazio_nao_casa_nada(self):
        self.assertEqual(self.casa("", "Leite Integral Tirol 1L"), [False])
        self.assertEqual(self.casa("500 ml", "Leite Integral Tirol 1L"), [False])


class TermoNucleo(Base):
    def test_tipo_e_marca_com_acento(self):
        S = self.S
        self.assertEqual(S.termo_nucleo("Álcool perfumado"), "Álcool")
        self.assertEqual(S.termo_nucleo("Detergente Ypê limão"), "Detergente Ypê")
        self.assertIsNone(S.termo_nucleo("Leite"), "uma palavra: não há o que tirar")
        self.assertIsNone(S.termo_nucleo("Leite Tirol"), "tipo + marca: já é o núcleo")


class TipoAprendido(Base):
    def test_eh_tipo_pelo_vocabulario(self):
        S = self.S
        for w in ("leite", "detergente", "alcool", "limpador"):
            self.assertTrue(S.eh_tipo(w), w)
        for w in ("integral", "limpeza", "ype"):
            self.assertFalse(S.eh_tipo(w), w)

    def test_sem_vocabulario_nada_e_tipo(self):
        S, pasta, _ = servidor()
        try:
            self.assertFalse(S.eh_tipo("leite"))
        finally:
            limpa(pasta)

    def test_vocabulario_gravado_e_lido_de_novo(self):
        S = self.S
        S.grava_vocab()
        S2, _, _ = servidor({"OFERTAS_DATA": self.pasta})
        self.assertEqual(len(S2.vocab()["nomes"]), len(S.vocab()["nomes"]))
        self.assertIn("ype", S2.vocab()["marcas"])
        self.assertEqual(S2.vocab()["formas"].get("alcool"), "álcool", "a forma com acento também é guardada")

    def test_nome_repetido_e_sem_tipo_nao_entram(self):
        S = self.S
        n = len(S.vocab()["nomes"])
        S.aprende_nomes(["Leite Integral Tirol 1L", "Leite", "12"])
        self.assertEqual(len(S.vocab()["nomes"]), n)


class Correcao(Base):
    def test_corrige_com_acento_e_maiuscula(self):
        S = self.S
        self.assertEqual(S.corrige_texto("Álcool de lompeza"), "Álcool de limpeza")
        self.assertEqual(S.corrige_texto("Detergemte Ypê"), "Detergente Ypê")
        self.assertEqual(S.corrige_texto("Papel higienco"), "Papel higiênico")
        self.assertEqual(S.corrige_texto("desinfetamte"), "desinfetante")

    def test_nao_mexe_no_que_esta_certo_ou_e_desconhecido(self):
        S = self.S
        for t in ("Leite integral", "Café Pilão 500 g", "Amaciante", "Xyzw", "Sabão em pó", ""):
            self.assertIsNone(S.corrige_texto(t), t)

    def test_marca_e_palavra_curta_nao_sao_corrigidas(self):
        S = self.S
        self.assertIsNone(S.corrige_palavra("tirol"))
        self.assertIsNone(S.corrige_palavra("lei"))
        self.assertIsNone(S.corrige_palavra("leite"))

    def test_precisa_de_vocabulario(self):
        S, pasta, _ = servidor()
        try:
            S.aprende_nomes(NOMES_VOCAB[:20])
            self.assertIsNone(S.corrige_texto("Álcool de lompeza"), "com menos de 150 nomes, não arrisca")
        finally:
            limpa(pasta)

    def test_sugestoes_dos_itens_sem_preco(self):
        S = self.S
        self.assertEqual(S.sugestoes_para(["Álcool de lompeza", "Leite integral"]), {"Álcool de lompeza": "Álcool de limpeza"})

    def test_distancia(self):
        S = self.S
        self.assertEqual(S._distancia("limpeza", "limpeza"), 0)
        self.assertEqual(S._distancia("lompeza", "limpeza"), 1)
        self.assertEqual(S._distancia("lmipeza", "limpeza"), 1, "troca de vizinhas conta 1")
        self.assertEqual(S._distancia("abc", "abcdef", 2), 3, "passou do limite")

    def test_indice_refeito_quando_o_vocabulario_muda(self):
        S = self.S
        self.assertIsNone(S.corrige_palavra("framboeza"))
        S.aprende_nomes(["Geleia de Framboesa Queensberry 320g", "Iogurte Framboesa Batavo 170g"])
        S.grava_vocab()
        self.assertEqual(S.corrige_palavra("framboeza"), "framboesa")


class CodigoDeBarras(Base):
    vocabulario = False

    def test_digito_verificador(self):
        S = self.S
        for e in ("7891000100103", "7896004000855", "78912342", "0036000291452", "17891000100100"):
            self.assertTrue(S.ean_valido(e), e)
        for e in ("7891000100104", "789100010010", "abc", "", "78912343"):
            self.assertFalse(S.ean_valido(e), e)

    def test_eans_da_lista(self):
        S = self.S
        cfg = {"lista": [{"produto": "Leite", "ean": "7891000100103"}, {"produto": "Café", "ean": "123"}, "Pão", {"produto": "Ovos"}]}
        self.assertEqual(S.eans_da_lista(cfg), {"leite": "7891000100103"})

    def test_casados_guarda_ean_e_secao_por_loja(self):
        S = self.S
        S.guarda_casados("Leite integral", ["7891000100103", "x", ""], "giassi", ["laticinios/leites", ""])
        S.guarda_casados("Leite integral", ["7891000100103"], "angeloni", ["frios/leite"])
        c = S.casados()["leite integral"]
        self.assertEqual(c["eans"], ["7891000100103"])
        self.assertEqual(c["secoes"], {"giassi": ["laticinios/leites"], "angeloni": ["frios/leite"]})
        S.guarda_casados("Leite integral", [])  # nada novo: não regrava
        self.assertEqual(S.casados()["leite integral"], c)


if __name__ == "__main__":
    unittest.main()
