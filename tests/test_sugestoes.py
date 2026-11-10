"""1.12.0: as sugestões ao digitar o nome de um item (Minha lista › Itens da lista): os nomes genéricos, sem marca e sem
tamanho, que abrem os nomes de produto vistos nas lojas, do mais visto para o menos visto. Marcas e produtos inventados."""
import unittest

from apoio import limpa, servidor

# marcas inventadas: duas de uma palavra e duas de duas palavras (as lojas mandam a marca de cada produto)
MARCAS = ["Pratinho", "Brilhux", "Tio Zeca", "Vale Verde"]
NOMES = (
    [f"Arroz Branco {m} Tipo 1 5kg" for m in MARCAS] + ["Arroz Branco Agulhinha Pratinho 1kg"]
    + [f"Arroz Integral {m} 1kg" for m in MARCAS[:3]]
    + ["Arroz Parboilizado Pratinho 5kg", "Arroz Parboilizado Tio Zeca 1kg"]
    + ["Arroz Arbóreo Vale Verde 500g"]  # visto uma vez só: fica de fora
    + ["Arroz Tio Zeca Tipo 1 5kg", "Arroz Tio Zeca Parboilizado 2kg", "Arroz Pratinho Tipo 1 1kg"]  # a marca logo depois do tipo
    + ["Sabão em Pó Brilhux 1,6kg", "Sabão em Pó Vale Verde 800g", "Sabão em Pó Pratinho Lavanda 2kg", "Sabão Líquido Brilhux 3L",
       "Sabão Líquido Vale Verde 1L", "Sabão Barra Brilhux 5 Unidades", "Sabão Barra Pratinho Pacote 5un"]
    + [f"Sabonete Líquido {m} 250ml" for m in MARCAS] + ["Sabonete Barra Brilhux 90g", "Sabonete Barra Pratinho 85g"]
    + ["Sabonete Pacote Brilhux 6 unidades", "Sabonete Pacote Vale Verde 12"]  # embalagem: não é um tipo de sabonete
    + ["Café em Pó Pratinho 500g", "Café em Pó Tio Zeca 250g", "Café Solúvel Brilhux 100g", "Café Solúvel Pratinho 200g"]
    + ["Chá de Camomila Brilhux 10 sachês", "Chá de Camomila Vale Verde 15g"]
    + ["Pratinho Pipoca Doce 100g", "Pratinho Pipoca Salgada 100g"]  # nomes que começam pela marca
)


class Sugestoes(unittest.TestCase):
    def setUp(self):
        self.S, self.pasta, self.log = servidor()
        self.S.aprende_nomes(NOMES, MARCAS)

    def tearDown(self):
        limpa(self.pasta)

    def test_o_tipo_ganha_uma_palavra_sem_marca_do_mais_visto_para_o_menos_visto(self):
        self.assertEqual(self.S.sugestoes_nomes("arroz"), ["Arroz branco", "Arroz integral", "Arroz parboilizado"],
                         "o arbóreo foi visto uma vez só; Arroz Tio Zeca e Arroz Pratinho são marcas")
        self.assertEqual(self.S.sugestoes_nomes("ARROZ  "), self.S.sugestoes_nomes("arroz"), "maiúsculas e espaços não contam")

    def test_a_palavra_que_esta_sendo_digitada_completa(self):
        self.assertEqual(self.S.sugestoes_nomes("sab"),
                         ["Sabonete", "Sabão", "Sabonete líquido", "Sabão em pó", "Sabão barra", "Sabão líquido", "Sabonete barra"],
                         "as duas palavras primeiro (estão em mais nomes); o empate, em ordem alfabética")
        self.assertEqual(self.S.sugestoes_nomes("arroz int"), ["Arroz integral"])
        self.assertEqual(self.S.sugestoes_nomes("arroz branco"), [], "Arroz Branco Agulhinha foi visto uma vez só (e o resto é marca)")

    def test_palavra_de_ligacao_nao_fecha_o_nome_e_o_acento_volta(self):
        self.assertEqual(self.S.sugestoes_nomes("sabão"), ["Sabão em pó", "Sabão barra", "Sabão líquido"],
                         "sabão em pó, com o acento das lojas (pó vem da lista das palavras curtas)")
        self.assertEqual(self.S.sugestoes_nomes("cafe"), ["Café em pó", "Café solúvel"])
        self.assertEqual(self.S.sugestoes_nomes("cha"), ["Chá de camomila"], "o chá de camomila; o próprio chá já foi digitado")

    def test_marca_e_embalagem_cortam(self):
        self.assertEqual(self.S.sugestoes_nomes("sabonete"), ["Sabonete líquido", "Sabonete barra"], "o Sabonete Pacote fica de fora")
        self.assertEqual(self.S.sugestoes_nomes("prat"), [], "completar com uma marca, não")
        self.assertEqual(self.S.sugestoes_nomes("pratinho"), ["Pratinho pipoca"], "mas quem escreve a marca inteira vê o que ela tem")

    def test_texto_curto_numeros_e_tamanho(self):
        self.assertEqual(self.S.sugestoes_nomes("a"), [])
        self.assertEqual(self.S.sugestoes_nomes(""), [])
        self.assertEqual(self.S.sugestoes_nomes("5 kg"), [])
        self.assertEqual(self.S.sugestoes_nomes("arroz 5kg"), self.S.sugestoes_nomes("arroz"), "o tamanho não conta")
        self.assertEqual(self.S.sugestoes_nomes("feijao"), [], "nada visto")

    def test_no_maximo_o_limite(self):
        self.assertEqual(len(self.S.sugestoes_nomes("sab", limite=3)), 3)

    def test_as_marcas_de_mais_palavras_sao_aprendidas(self):
        m = self.S.vocab()["marcas"]
        self.assertTrue({"tio zeca", "vale verde", "pratinho", "brilhux"} <= m)
        self.S.aprende_nomes([], ["Uma Marca Comprida Demais", " "])
        self.assertNotIn("uma marca comprida demais", self.S.vocab()["marcas"], "até 3 palavras")

    def test_o_indice_e_refeito_quando_o_vocabulario_muda(self):
        self.assertEqual(self.S.sugestoes_nomes("feijao"), [])
        self.S.aprende_nomes(["Feijão Carioca Pratinho 1kg", "Feijão Carioca Brilhux 1kg", "Feijão Preto Pratinho 1kg"], [])
        self.S.grava_vocab()  # o vocabulário novo refaz as contas
        self.assertEqual(self.S.sugestoes_nomes("feijao"), ["Feijão carioca"])


if __name__ == "__main__":
    unittest.main()
