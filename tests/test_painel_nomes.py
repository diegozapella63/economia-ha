"""A página (economia/pagina/painel.html) é um script só: duas funções com o mesmo nome no mesmo nível, a segunda vale para
as duas, sem erro nenhum. Foi o que a 1.17.0 fez com naLista (a das Ofertas, "Está na sua lista", virou a das listas
prontas, e as ofertas da lista saíram do alto). Aqui, nenhum nome repetido no nível de cima do script."""
import os
import re
import unittest
from collections import Counter

PAINEL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "economia", "pagina", "painel.html")


class NomesDaPagina(unittest.TestCase):
    def test_nenhuma_funcao_ou_variavel_repetida(self):
        with open(PAINEL, encoding="utf-8") as f:
            texto = f.read()
        nomes = re.findall(r"^  function ([A-Za-z0-9_$]+)\(", texto, re.M) + re.findall(r"^  var ([A-Za-z0-9_$]+)\s*=", texto, re.M)
        repetidos = sorted(n for n, k in Counter(nomes).items() if k > 1)
        self.assertGreater(len(nomes), 300, "achou as funções da página")
        self.assertEqual(repetidos, [], "nomes declarados duas vezes no nível de cima do script")


if __name__ == "__main__":
    unittest.main()
