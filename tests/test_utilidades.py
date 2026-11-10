"""Partes pequenas do servidor: números, tamanhos, links, datas, robots.txt, páginas de produto, nomes de loja."""
import json
import unittest

from apoio import limpa, servidor


class Base(unittest.TestCase):
    def setUp(self):
        self.S, self.pasta, self.log = servidor()

    def tearDown(self):
        limpa(self.pasta)


class Numeros(Base):
    def test_numero_em_reais(self):
        n = self.S.numero
        self.assertEqual(n("R$ 12,90"), 12.9)
        self.assertEqual(n("1.299,90"), 1299.9)
        self.assertEqual(n(7.456), 7.46)
        self.assertEqual(n("12.5"), 12.5)
        for v in (0, -3, "abc", None, ""):
            self.assertIsNone(n(v), v)

    def test_frete_e_total(self):
        S = self.S
        self.assertEqual(S.frete_ok(0), 0)
        self.assertIsNone(S.frete_ok(-1))
        self.assertEqual(S.frete_ok("R$ 9,90"), 9.9, "frete em texto, como as lojas mostram")
        self.assertEqual(S.frete_ok("9,90"), 9.9)
        self.assertEqual(S.frete_ok("1.234,50"), 1234.5)
        self.assertEqual(S.frete_ok("Grátis"), 0)
        self.assertIsNone(S.frete_ok("-5,00"))
        self.assertIsNone(S.frete_ok("a combinar"))
        self.assertEqual(S.valor_total({"preco": "R$ 20,00", "frete": "R$ 9,90"}), 29.9, "o preço online soma o frete em texto")
        self.assertEqual(S.frete_item("no carrinho"), "carrinho")
        self.assertEqual(S.frete_item("9,90".replace(",", ".")), 9.9)
        self.assertEqual(S.valor_total(10), 10)
        self.assertEqual(S.valor_total({"preco": 10, "frete": 5}), 15)
        self.assertEqual(S.valor_total({"preco": 10, "clube": 8}), 10, "sem ser sócio, vale o preço normal")
        self.assertEqual(S.valor_total({"preco": 10, "clube": 8}, socio=True), 8)
        self.assertIsNone(S.valor_total({"frete": 5}))

    def test_inteiro_texto_data(self):
        S = self.S
        self.assertEqual(S.inteiro("3.6"), 4)
        self.assertIsNone(S.inteiro(-2))
        self.assertEqual(S.texto("  oi  "), "oi")
        self.assertIsNone(S.texto(""))
        self.assertEqual(S.texto("x" * 200, 10), "x" * 10)
        self.assertEqual(S.data_ok("2026-11-02"), "2026-11-02")
        self.assertIsNone(S.data_ok("02/11/2026"))
        self.assertEqual(S.br_preco(1299.9), "R$ 1.299,90")
        self.assertEqual(S.br_data("2026-11-02"), "02/11/2026")

    def test_data_iso(self):
        S = self.S
        self.assertEqual(S.data_iso("válido até 29/10/2026"), "2026-10-29")
        self.assertEqual(S.data_iso("29/10/26"), "2026-10-29")
        self.assertEqual(S.data_iso("29/10")[5:], "10-29")
        self.assertIsNone(S.data_iso("31/02/2026"), "data que não existe")
        self.assertIsNone(S.data_iso("sem data"))


class Tamanhos(Base):
    def test_medida_em_unidade_comum(self):
        m = self.S.medida
        self.assertEqual(m(500, "ml"), (0.5, "L"))
        self.assertEqual(m(500, "g"), (0.5, "kg"))
        self.assertEqual(m(2, "Litros"), (2, "L"))
        self.assertEqual(m(12, "un"), (12, "un"))
        self.assertEqual(m(30, "m"), (30, "m"))
        self.assertIsNone(m(0, "kg"))
        self.assertIsNone(m(1, "caixa"))
        self.assertIsNone(m("x", "kg"))

    def test_tamanho_pelo_nome(self):
        t = self.S.tamanho_nome
        self.assertEqual(t("Leite Integral Tirol 1L"), (1, "L"))
        self.assertEqual(t("Leite 1L Caixa com 12"), (12, "L"))
        self.assertEqual(t("Sabão em Pó Omo 1,6kg"), (1.6, "kg"))
        self.assertEqual(t("Café Pilão 500g"), (0.5, "kg"))
        self.assertEqual(t("Água Mineral 1,5 L c/ 6"), (9, "L"))
        self.assertEqual(t("Papel Higiênico 12un"), (12, "un"))
        self.assertIsNone(t("Pão francês"))

    def test_desconto_nao_e_pacote(self):
        t = self.S.tamanho_nome
        self.assertEqual(t("Detergente 500ml com 10% de desconto"), (0.5, "L"))
        self.assertEqual(t("Detergente 500ml com 20 off"), (0.5, "L"))
        self.assertEqual(t("Detergente 500ml com 2 reais de desconto"), (0.5, "L"))

    def test_fmt_base_e_mesmo_tamanho(self):
        S = self.S
        self.assertEqual(S.fmt_base({"quantidade": 0.5, "unidade": "L"}), "500 ml")
        self.assertEqual(S.fmt_base({"quantidade": 0.25, "unidade": "kg"}), "250 g")
        self.assertEqual(S.fmt_base({"quantidade": 2, "unidade": "kg"}), "2 kg")
        self.assertEqual(S.fmt_base({"quantidade": 30, "unidade": "un", "rotulo": "comprimidos"}), "30 comprimidos")
        self.assertTrue(S.mesmo_tamanho(1.005, 1))
        self.assertFalse(S.mesmo_tamanho(1.02, 1))


class Links(Base):
    def test_url_e_fonte(self):
        S = self.S
        self.assertTrue(S.url_ok("https://giassi.com.br/x"))
        self.assertFalse(S.url_ok("ftp://x"))
        self.assertFalse(S.url_ok("https://" + "x" * 700))
        self.assertEqual(S.fonte_ok("giassi.com.br/leite"), "https://giassi.com.br/leite")
        self.assertIsNone(S.fonte_ok("não é link"))
        self.assertIsNone(S.fonte_ok(None))

    def test_slug_e_norm(self):
        S = self.S
        self.assertEqual(S.slug("Açougue & Aves!"), "acougue-aves")
        self.assertEqual(S.slug(""), "item")
        self.assertEqual(S.norm("  Álcool 46°  "), "alcool 46")

    def test_texto_url_e_cara_de_produto(self):
        S = self.S
        self.assertEqual(S.texto_url("https://loja.com/detergente-ype-neutro-500ml/p"), "detergente ype neutro 500ml")
        self.assertGreater(S.parece_produto("https://loja.com/detergente-ype-neutro-500ml/p"), 3)
        self.assertLess(S.parece_produto("https://loja.com/categoria/limpeza"), 0)
        self.assertLess(S.parece_produto("https://loja.com/minha-conta"), 0)


class Robots(Base):
    TXT = """
User-agent: Googlebot
Disallow: /

User-agent: *
User-agent: bingbot
Disallow: /checkout
Disallow: /*?busca=
Allow: /checkout/ajuda
Disallow: /api/*$
"""

    def test_so_as_regras_de_todos(self):
        S = self.S
        r = S.robots_regras(self.TXT)
        self.assertIn(("disallow", "/checkout"), r)
        self.assertNotIn(("disallow", "/"), r, "regra do Googlebot não vale para nós")
        self.assertTrue(S.robots_permite(r, "/produto/leite"))
        self.assertFalse(S.robots_permite(r, "/checkout/pagar"))
        self.assertTrue(S.robots_permite(r, "/checkout/ajuda"), "Allow mais comprido vence")
        self.assertFalse(S.robots_permite(r, "/s?busca=leite"))
        self.assertFalse(S.robots_permite(r, "/api/x"))
        self.assertTrue(S.robots_permite([], "/qualquer"))
        self.assertEqual(S.robots_regras(""), [])


class PaginasDeProduto(Base):
    def test_meta_tag_em_qualquer_ordem(self):
        S = self.S
        h = '<meta content="12,90" property="product:price:amount"><meta name=\'og:title\' content=\'Leite &amp; Cia\'>'
        self.assertEqual(S.meta_tag(h, "product:price:amount"), "12,90")
        self.assertEqual(S.meta_tag(h, "og:title"), "Leite & Cia")
        self.assertIsNone(S.meta_tag(h, "og:price:amount"))

    def test_produto_ld(self):
        S = self.S
        p = S.produto_ld({"@type": "Product", "name": "Leite Tirol 1L", "brand": {"name": "Tirol"},
                          "offers": {"@type": "Offer", "price": "4.99", "availability": "https://schema.org/InStock"}})
        self.assertEqual(p["preco"], 4.99)
        self.assertTrue(p["disponivel"])
        sem = S.produto_ld({"@type": "Product", "name": "X", "offers": {"price": "4.99", "availability": "http://schema.org/OutOfStock"}})
        self.assertFalse(sem and sem.get("disponivel"))
        agg = S.produto_ld({"@type": "Product", "name": "Y", "offers": {"@type": "AggregateOffer", "lowPrice": 3.5,
                                                                         "offers": [{"price": 3.5}, {"price": 4.2}]}})
        self.assertEqual(agg["preco"], 3.5)
        self.assertIsNone(S.produto_ld({"@type": "Organization"}))
        self.assertIsNone(S.produto_ld("x"))

    def test_sem_tags(self):
        self.assertEqual(self.S.sem_tags("<p>Leite <b>R$&nbsp;4,99</b></p>"), "Leite R$ 4,99")

    def test_extrai_json_da_resposta_da_ia(self):
        S = self.S
        self.assertEqual(S.extrai_json({"a": 1}), {"a": 1})
        self.assertEqual(S.extrai_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(S.extrai_json('Aqui está: {"a": [1, 2,]} pronto'), {"a": [1, 2]})
        self.assertEqual(S.extrai_json(json.dumps(json.dumps({"a": 2}))), {"a": 2})
        with self.assertRaises(S.ErroBusca):
            S.extrai_json(None)
        with self.assertRaises(S.ErroBusca):
            S.extrai_json("sem json nenhum")


class Lojas(Base):
    def test_chave_e_mesma_loja(self):
        S = self.S
        self.assertEqual(S.chave_loja("Droga Raia"), "raia")
        self.assertEqual(S.chave_loja("Supermercado Imperatriz - Joinville"), "imperatriz")
        self.assertTrue(S.mesma_loja("Droga Raia", "Raia"))
        self.assertTrue(S.mesma_loja("Giassi Supermercados", "Giassi"))
        self.assertFalse(S.mesma_loja("Giassi", "Angeloni"))

    def test_mesmo_lugar(self):
        S = self.S
        a, b = {"lat": -26.30, "lon": -48.85}, {"lat": -26.3005, "lon": -48.8502}
        self.assertTrue(S.mesmo_lugar(a, b, "Supermercado Imperatriz", "Supermercado Impeatriz"))
        self.assertFalse(S.mesmo_lugar(a, {"lat": -26.32, "lon": -48.85}, "Imperatriz", "Imperatriz"), "longe demais")
        self.assertFalse(S.mesmo_lugar(a, {"lat": None}, "x", "x"))

    def test_km_entre(self):
        self.assertAlmostEqual(self.S.km_entre(-26.30, -48.85, -26.31, -48.85), 1.1, places=1)

    def test_marketplace(self):
        S = self.S
        self.assertTrue(S.e_marketplace("Mercado Livre"))
        self.assertTrue(S.e_marketplace("Magazine Luiza"))
        self.assertFalse(S.e_marketplace("Giassi"))
        self.assertEqual(S.mkt_id("Magazine Luiza"), "magalu")
        self.assertEqual(S.mkt_id("Amazon.com.br"), "amazon")
        self.assertIsNone(S.mkt_id("Giassi"))

    def test_nome_bonito(self):
        S = self.S
        self.assertEqual(S.nome_bonito("DROGARIA DROGÃO JOINVILLE"), "Drogaria Drogão Joinville")
        self.assertEqual(S.nome_bonito("CASA DE CARNES DO ZÉ"), "Casa de Carnes do Zé")
        self.assertEqual(S.nome_bonito("Giassi"), "Giassi")

    def test_categoria_do_preco(self):
        S = self.S
        cats = ["mercados", "farmacias", "petshops", "online"]
        self.assertEqual(S.categoria_do_preco({"rede": "Droga Raia"}, cats), "farmacias")
        self.assertEqual(S.categoria_do_preco({"rede": "Cobasi"}, cats), "petshops")
        self.assertEqual(S.categoria_do_preco({"rede": "Amazon"}, cats), "online")
        self.assertEqual(S.categoria_do_preco({"rede": "Loja X", "frete": 10}, cats), "online")
        self.assertEqual(S.categoria_do_preco({"rede": "Giassi"}, cats), "mercados")
        self.assertEqual(S.categoria_do_preco({"rede": "Giassi", "categoria": "farmacias"}, cats), "farmacias")


class ItemDaLista(Base):
    def test_casar_item_pela_resposta_da_ia(self):
        S = self.S
        nomes = ["Leite integral", "Café Pilão 500 g", "Papel higiênico"]
        self.assertEqual(S.casar_item({"item": 2}, nomes), "Café Pilão 500 g")
        self.assertEqual(S.casar_item({"produto": "leite integral"}, nomes), "Leite integral")
        self.assertEqual(S.casar_item({"produto": "Papel higiênico (base: 12 rolos)"}, nomes), "Papel higiênico")
        self.assertEqual(S.casar_item({"produto": "Cafés Pilão 500 g"}, nomes), "Café Pilão 500 g", "plural e acento")
        self.assertIsNone(S.casar_item({"produto": "Cafés Pilão"}, nomes), "precisa de 3 de cada 4 palavras do item")
        self.assertIsNone(S.casar_item({"produto": "Detergente"}, nomes))

    def test_ritmo(self):
        S = self.S
        self.assertEqual(S.ritmo_info({"compras": ["2026-10-01"]}), (None, None))
        dias, prev = S.ritmo_info({"compras": ["2026-10-01", "2026-10-11", "2026-10-21"]})
        self.assertEqual(prev, "2026-10-31")


if __name__ == "__main__":
    unittest.main()


class Versao(Base):
    """1.9.1: a versão fica só no economia/config.yaml."""

    def test_le_do_config_yaml(self):
        import os
        import re
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(raiz, "economia", "config.yaml"), encoding="utf-8") as f:
            esperado = re.search(r'^version:\s*"?([\d.]+)', f.read(), re.M).group(1)
        self.assertEqual(self.S.VERSAO, esperado)
        self.assertEqual(self.S.Painel.server_version, "EconomIA/" + esperado)
        with open(os.path.join(raiz, "economia", "app", "www", "index.html"), encoding="utf-8") as f:
            self.assertIn("var VERSAO = '" + esperado + "';", f.read(), "a página montada tem a mesma versão")

    def test_no_conteiner_e_sem_arquivo(self):
        import os
        import tempfile
        from unittest import mock
        pasta = tempfile.mkdtemp()
        try:
            with open(os.path.join(pasta, "config.yaml"), "w", encoding="utf-8") as f:
                f.write('name: EconomIA\nversion: "7.8.9"\n')
            falso = os.path.join(pasta, "server.py")
            with mock.patch.object(self.S.os.path, "abspath", lambda p: falso if p == self.S.__file__ else os.path.realpath(p)):
                self.assertEqual(self.S.ler_versao(), "7.8.9", "no contêiner, o config.yaml ao lado do server.py")
                os.remove(os.path.join(pasta, "config.yaml"))
                self.assertEqual(self.S.ler_versao(), "0", "sem o arquivo, não quebra")
        finally:
            limpa(pasta)
