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
    # 1.32.0: o "sem lactose" vem com outras palavras no meio, e às vezes como "zero"
    + ["Leite UHT Integral Zero Lactose Pratinho 1L", "Leite Integral Sem Lactose Vale Verde 1L", "Leite Desnatado Zero Lactose Brilhux 1L",
       "Leite UHT Integral Pratinho 1L", "Leite UHT Desnatado Brilhux 1L"]
    # a marca no meio do nome (quem digita só a marca, como "Lysoform")
    + ["Tira Manchas Brilhux Oxi 450g", "Tira Manchas Brilhux Rosa 1L", "Alvejante Brilhux 1L", "Doce de Leite Vale Verde 400g",
       "Doce de Leite Pratinho 200g"]
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

    def test_palavras_no_meio_e_sem_igual_a_zero(self):
        self.assertEqual(self.S.sugestoes_nomes("leite sem lac"), ["Leite sem lactose"],
                         "1.32.0: as lojas escrevem Leite UHT Integral Zero Lactose; a sugestão fica com o que foi digitado")
        self.assertEqual(self.S.sugestoes_nomes("leite zero lac"), ["Leite zero lactose"])
        self.assertEqual(self.S.sugestoes_nomes("leite uht"), ["Leite uht integral"], "do começo (o desnatado foi visto uma vez só)")
        self.assertEqual(self.S.sugestoes_nomes("leite integral lac"), ["Leite integral lactose"], "com saltos também na ordem")
        self.assertEqual(self.S.sugestoes_nomes("leite sem lactose"), [], "a palavra já completa não vira sugestão")
        self.assertEqual(self.S.sugestoes_nomes("leite sem pra"), [], "completar com a marca, não")

    def test_a_palavra_no_meio_do_nome(self):
        """1.32.0: a marca (ou outra palavra) que as lojas escrevem no meio do nome."""
        self.assertIn("Tira manchas Brilhux", self.S.sugestoes_nomes("brilhux"), "a marca sozinha acha o produto dela")
        self.assertIn("Tira manchas Brilhux", self.S.sugestoes_nomes("brilh"), "e enquanto digita")
        self.assertIn("Doce de leite", self.S.sugestoes_nomes("leite"), "leite também acha o doce de leite (depois dos do começo)")
        self.assertEqual(self.S.sugestoes_nomes("leite")[0], "Leite uht", "os que começam pelo que foi digitado primeiro")
        self.assertNotIn("Alvejante Brilhux", self.S.sugestoes_nomes("brilhux"), "visto uma vez só")

    def test_o_nome_do_item_sem_marca_tamanho_e_embalagem(self):
        """1.32.0: Similares › Pôr na lista e Trocar por este levam só o item, para ainda comparar as lojas."""
        n = self.S.nome_do_item
        self.assertEqual(n("Sabão em Pó Brilhux 1,6kg"), "Sabão em pó")
        self.assertEqual(n("Arroz Integral Tio Zeca 1kg"), "Arroz integral", "a marca de duas palavras corta")
        self.assertEqual(n("Frango a Passarinho Congelado IQF Pratinho Pacote 1kg"), "Frango a passarinho congelado")
        self.assertEqual(n("Coxa e Sobrecoxa de Frango Resfriada Preço por quilo"), "Coxa e sobrecoxa de frango resfriada",
                         "sem marca: tira o preço por quilo (e o por que sobra no fim)")
        self.assertEqual(n("Acém Moído Bovino Kg"), "Acém moído bovino")
        self.assertEqual(n("Pratinho Pipoca Doce 100g"), "Pratinho pipoca doce", "a marca no começo fica (senão não sobra o item)")
        self.assertEqual(n("1kg"), "1kg", "sem nada que sobre, o nome de antes")

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
