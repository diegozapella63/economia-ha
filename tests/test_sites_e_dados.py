"""Preços sem IA nas páginas das lojas (schema.org, meta tags, dados embutidos, texto), busca do site com robots.txt,
Shopee Afiliados (assinatura), versões da configuração, uso da IA, exportar e categoria das lojas."""
import hashlib
import io
import json
import os
import time
import unittest
import zipfile

from apoio import LojasFalsas, limpa, servidor

LD = """<html><head><script type="application/ld+json">{"@context":"https://schema.org","@graph":[
 {"@type":"Product","name":"Detergente Ypê Neutro 500ml","offers":{"@type":"Offer","price":"2.39","availability":"https://schema.org/InStock"}},
 {"@type":"Product","name":"Detergente Limpol 500ml","offers":{"@type":"Offer","price":"2.19","availability":"https://schema.org/InStock"}},
 {"@type":"Product","name":"Detergente Esgotado 500ml","offers":{"@type":"Offer","price":"1.99","availability":"https://schema.org/OutOfStock"}}]}
</script></head><body></body></html>"""

TEXTO = """<div class="card"><h3>Ração Golden Gatos Castrados 1kg</h3><s>R$ 39,90</s><span>R$ 34,90</span></div>
<div class="card"><h3>Areia Higiênica Pipicat 4kg</h3><span>R$ 21,50</span><small>3x de R$ 7,17</small></div>
<p>Frete grátis acima de R$ 99,00</p>"""


class Base(unittest.TestCase):
    def setUp(self):
        self.lojas = LojasFalsas().__enter__()
        self.S, self.pasta, self.log = servidor(self.lojas.env())

    def tearDown(self):
        self.lojas.__exit__()
        limpa(self.pasta)


class PaginasDaLoja(Base):
    def test_schema_org_em_grafo_sem_esgotado(self):
        ofs = self.S.ofertas_da_pagina(LD)
        self.assertEqual([(o["produto"], o["preco"]) for o in ofs], [("Detergente Ypê Neutro 500ml", 2.39), ("Detergente Limpol 500ml", 2.19)])

    def test_cartoes_de_texto_com_preco_riscado_e_sem_parcela(self):
        ofs = {o["produto"]: o for o in self.S.ofertas_da_pagina(TEXTO)}
        self.assertEqual(ofs["Ração Golden Gatos Castrados 1kg"]["preco"], 34.90)
        self.assertEqual(ofs["Ração Golden Gatos Castrados 1kg"]["preco_normal"], 39.90)
        self.assertEqual(ofs["Areia Higiênica Pipicat 4kg"]["preco"], 21.50, "a parcela 3x de R$ 7,17 não é o preço")
        self.assertFalse(any("Frete" in n for n in ofs))

    def test_pagina_de_produto_por_meta_tags(self):
        h = ('<meta property="og:title" content="Fralda Pampers Confort Sec G 46un">'
             '<meta content="89.90" property="product:price:amount"><meta property="product:sale_price:amount" content="79,90">'
             '<meta property="product:availability" content="in stock">')
        r = self.S.preco_da_pagina(h)
        self.assertEqual((r["nome"], r["preco"]), ("Fralda Pampers Confort Sec G 46un", 79.90), "vale o menor entre preço e promoção")

    def test_busca_do_site_respeita_robots_e_tenta_o_nucleo(self):
        S = self.S
        origem = self.lojas.base + "/loja"
        self.lojas.paginas["/loja/busca"] = (200, LD, "text/html")
        info = {"regras": S.robots_regras("User-agent: *\nDisallow: /busca\n"), "busca": "/busca?q={}"}
        self.assertEqual(S.busca_do_site(origem, info, "Detergente"), [], "o robots.txt proíbe a busca")
        self.assertFalse(self.lojas.pedidos_de("/loja/busca"))
        info = {"regras": [], "busca": "/busca?q={}"}
        ofs = S.busca_do_site(origem, info, "Detergente Ypê")
        self.assertEqual([o["produto"] for o in ofs], ["Detergente Ypê Neutro 500ml"])

    def test_sem_busca_que_funcione_espera_uma_semana(self):
        S = self.S
        origem = self.lojas.base + "/vazia"
        info = {"regras": []}
        self.assertEqual(S.busca_do_site(origem, info, "Leite"), [])
        self.assertIn("sem_busca", info)
        n = len(self.lojas.pedidos)
        self.assertEqual(S.busca_do_site(origem, info, "Leite"), [])
        self.assertEqual(len(self.lojas.pedidos), n, "não tenta de novo antes de uma semana")
        S.busca_do_site(origem, info, "Leite", forcar=True)
        self.assertGreater(len(self.lojas.pedidos), n)

    def test_procura_catalogo_pelo_endereco(self):
        S = self.S
        urls = ["https://loja.com/detergente-ype-neutro-500ml/p", "https://loja.com/detergente-limpol-500ml/p",
                "https://loja.com/amaciante-comfort-1l/p", "https://loja.com/detergente-ype-neutro-5l/p"]
        r = S.procura_catalogo(urls, "Detergente Ypê")
        self.assertEqual(r, ["https://loja.com/detergente-ype-neutro-5l/p", "https://loja.com/detergente-ype-neutro-500ml/p"],
                         "do endereço mais curto para o mais longo")
        self.assertEqual(S.procura_catalogo(urls, "Amaciante ou detergente Limpol"),
                         ["https://loja.com/amaciante-comfort-1l/p", "https://loja.com/detergente-limpol-500ml/p"])


class Shopee(Base):
    def test_assinatura_e_erros(self):
        S = self.S
        with self.assertRaises(S.ErroShopee):
            S.shopee_consulta("{x}")
        seg = S.segredos()
        seg["shopee"] = {"app_id": "18300000001", "secret": "segredo"}
        S.grava_segredos(seg)
        S.SHOPEE_API = self.lojas.base + "/shopee"
        self.lojas.paginas["/shopee"] = (200, "{}", "application/json")

        capturado = {}

        def post(h, corpo):
            capturado["auth"], capturado["corpo"] = h.headers.get("Authorization"), corpo
            h._out({"data": {"productOfferV2": {"nodes": [{"productName": "Ração Golden 10kg", "priceMin": "129.9"}]}}})
        self.lojas._post = post
        nodes = S.shopee_produtos("Ração Golden")
        self.assertEqual(nodes[0]["productName"], "Ração Golden 10kg")
        cred = dict(x.split("=", 1) for x in capturado["auth"].replace("SHA256 ", "").split(", "))
        esperado = hashlib.sha256((cred["Credential"] + cred["Timestamp"] + capturado["corpo"] + "segredo").encode()).hexdigest()
        self.assertEqual(cred["Signature"], esperado, "SHA256(app_id + timestamp + corpo + senha)")
        self.assertLess(abs(int(cred["Timestamp"]) - time.time()), 60)


class Versoes(Base):
    def test_guarda_lista_e_restaura(self):
        S = self.S
        S.gravar_config({"cep": "1", "lista": [{"produto": "A"}]})
        n1 = S.guardar_versao("auto", forcar=True)
        self.assertIsNone(S.guardar_versao("auto"), "menos de 10 minutos depois: não guarda de novo")
        S.gravar_config({"cep": "2", "lista": []})
        v = S.listar_versoes()
        self.assertEqual(v[0]["nome"], n1)
        self.assertEqual((v[0]["itens"], v[0]["cep"]), (1, "1"))
        novo = S.restaurar_versao(n1)
        self.assertEqual(novo["cep"], "1")
        self.assertTrue(any(x["nome"].endswith("-restaurar.json") for x in S.listar_versoes()), "guarda a de antes de restaurar")
        with self.assertRaises(S.ErroBusca):
            S.restaurar_versao("../segredos.json")

    def test_so_as_tres_mais_recentes(self):
        S = self.S
        S.gravar_config({"cep": "1"})
        os.makedirs(S.VERSOES, exist_ok=True)
        for i in range(5):
            with open(os.path.join(S.VERSOES, f"config-2026010{i}-120000-auto.json"), "w") as f:
                f.write("{}")
        S.guardar_versao("auto", forcar=True)
        self.assertEqual(len(S.listar_versoes()), S.MAX_VERSOES)


class UsoDaIA(Base):
    def test_conta_chamadas_tokens_e_erros(self):
        S = self.S
        S.registra_uso("buscar ofertas", "ai_task.claude", 4000, 400, 0, 12.3, "ok")
        S.registra_uso("ler encarte", None, 400, 0, 2, 3, "erro")
        S.registra_uso("buscar ofertas", "ai_task.claude", 0, 0, 0, 1, "cota")
        r = S.uso_resumo()
        h = r["hoje"]
        self.assertEqual((h["chamadas"], h["erros"], h["cota"], h["imagens"]), (3, 1, 1, 2))
        self.assertEqual(h["tokens"], 1100 + 100)
        self.assertEqual(h["ias"]["padrão do Home Assistant"], 1)
        self.assertEqual(len(r["dias"]), 7)
        self.assertEqual(r["ultimas"][0]["resultado"], "cota")


class Exportar(Base):
    def prepara(self):
        S = self.S
        S.gravar_config({"cep": "89216120", "raio_km": 5, "categorias": ["mercados"], "lista": [
            {"produto": "Leite integral", "compras": ["2026-10-01", "2026-10-11"]}, {"produto": "Café"}]})
        S.gravar_json(S.OFERTAS, {"gerado_em": "2026-11-02T10:00:00", "categorias": [
            {"id": "mercados", "nome": "Mercados", "singular": "Mercado", "redes": [{"id": "merc-giassi", "nome": "Giassi"}, {"id": "merc-fort", "nome": "Fort"}],
             "lojas": [{"rede": "merc-giassi", "distancia_km": 1.0}, {"rede": "merc-fort", "distancia_km": 2.0}]}],
            "lista": [{"produto": "Leite integral", "precos": {"merc-giassi": 4.89, "merc-fort": 4.49}}]})

    def test_json(self):
        self.prepara()
        corpo, tipo = self.S.exportar("json")
        d = json.loads(corpo)
        self.assertEqual(d["app"], "EconomIA")
        leite = next(i for i in d["lista"] if i["produto"] == "Leite integral")
        self.assertEqual(leite["mais_barato"]["loja"], "Fort")
        self.assertEqual(leite["economia"], 0.4)

    def test_planilha(self):
        self.prepara()
        corpo, tipo = self.S.exportar("xlsx")
        self.assertIn("spreadsheetml", tipo)
        z = zipfile.ZipFile(io.BytesIO(corpo))
        self.assertIn("xl/worksheets/sheet1.xml", z.namelist())
        folha = z.read("xl/worksheets/sheet1.xml").decode()
        self.assertIn("Leite integral", folha)
        self.assertIn("Giassi R$ 4,89", folha)


class CategoriaDaLoja(Base):
    def test_loja_do_bairro_e_online(self):
        S = self.S
        S.gravar_json(S.OFERTAS, {"categorias": [
            {"id": "mercados", "redes": [{"id": "merc-fort", "nome": "Fort Atacadista"}, {"id": "merc-longe", "nome": "Mercado Longe"},
                                         {"id": "merc-sem", "nome": "Sem Endereço"}],
             "lojas": [{"rede": "merc-fort", "distancia_km": 4.2}, {"rede": "merc-longe", "distancia_km": 12}, {"rede": "merc-sem", "distancia_km": None}]},
            {"id": "online", "redes": [{"id": "onli-amazon", "nome": "Amazon"}], "lojas": [{"rede": "onli-amazon", "distancia_km": 1}]}]})
        perto = S.lojas_perto_cat({"raio_km": 5})
        self.assertEqual(perto, {"fort atacadista": "mercados"})
        self.assertEqual(S.categoria_da_loja("Fort Atacadista", perto), "mercados")
        self.assertEqual(S.categoria_da_loja("Fort", perto), "mercados", "pelo nome da rede")
        self.assertEqual(S.categoria_da_loja("Sem Endereço", perto), "online", "sem localização = online")
        self.assertEqual(S.categoria_da_loja("Mercado Longe", perto), "online", "fora do raio entrega")


if __name__ == "__main__":
    unittest.main()
