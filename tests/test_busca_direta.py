"""Busca direta nas lojas VTEX (Giassi, Angeloni…) contra lojas falsas: preço por peso, seção da loja, similares,
"ou", código de barras, nome corrigido e o produto pelo código."""
import unittest

from apoio import CEP, NOMES_VOCAB, LojasFalsas, ean13, limpa, prod, servidor

AVES, BOV = "Açougue/Aves", "Açougue/Bovinos"
EAN_COXINHA = ean13("789000000001")


def catalogo_giassi():
    return [
        prod("Coxinha da Asa de Frango Resfriada Kg", 21.90, AVES, "kg", 1, EAN_COXINHA),
        prod("Coxinha da Asa Congelada Sadia 1kg", 24.90, AVES),
        prod("Asa de Frango Congelada Kg", 15.90, AVES, "kg", 1),
        prod("Asinha de Frango Temperada Kg", 18.50, AVES, "kg", 1),
        prod("Sobrecoxa de Frango Resfriada Kg", 12.48, AVES, "kg", 1),
        prod("Filé de Peito de Frango Kg", 26.90, AVES, "kg", 1),
        prod("Frango Inteiro Congelado Kg", 10.99, AVES, "kg", 1),
        prod("Linguiça Toscana Kg", 9.90, "Açougue", "kg", 1),
        prod("Carne Moída Bovina de Primeira Kg", 39.90, BOV, "kg", 1),
        prod("Acém Moído Bovino Kg", 32.90, BOV, "kg", 1),
        prod("Almôndega de Carne Moída Bovina Congelada 500g", 15.90, "Congelados/Pratos Prontos"),
        prod("Hambúrguer Texas Burger Carne Bovina 672g", 19.90, "Congelados/Hambúrguer"),
        prod("Sobrecoxa de Frango Member's Mark Congelada 2,3kg", 14.98, AVES, "kg", 2.3),
        prod("Kit Churrasco Picanha + Linguiça", 89.90, BOV),
        prod("Leite Integral Tirol 1L", 4.89, "Laticínios/Leites", de=5.49),
        prod("Leite Integral Itambé 1L", 4.59, "Laticínios/Leites", estoque=0),
    ]


class Base(unittest.TestCase):
    def setUp(self):
        self.lojas = LojasFalsas().__enter__()
        self.lojas.catalogo["giassi"] = catalogo_giassi()
        self.lojas.catalogo["angeloni"] = [dict(p, categories=[], link=p["link"].replace("/p", "-ang/p"))
                                           for p in catalogo_giassi() if "Moíd" in p["productName"]]
        self.S, self.pasta, self.log = servidor(self.lojas.env())

    def tearDown(self):
        self.lojas.__exit__()
        limpa(self.pasta)

    def busca(self, *itens, cfg=None):
        cfg = cfg or {"cep": CEP, "categorias": ["mercados"], "lista": [i if isinstance(i, dict) else {"produto": i} for i in itens]}
        out = {}
        for cat, parcial in self.S.busca_direta(cfg):
            for prod_nome, ent in parcial.items():
                out[prod_nome] = ent
        return out


class BuscaVtex(Base):
    def test_produto_por_peso_e_bandeja(self):
        res = {c["nome"]: c for c in self.S.busca_vtex("giassi", "sobrecoxa", "v2.giassi")}
        mm = res["Sobrecoxa de Frango Member's Mark Congelada 2,3kg"]
        self.assertEqual(mm["preco"], 34.45, "preço do kg × peso da bandeja")
        self.assertEqual(mm["tam"], (2.3, "kg"))
        self.assertEqual(res["Sobrecoxa de Frango Resfriada Kg"]["tam"], (1, "kg"), "vendido por kg: 1 kg")

    def test_kit_sem_estoque_e_promocao(self):
        res = {c["nome"]: c for c in self.S.busca_vtex("giassi", "leite", "v2.giassi")}
        self.assertNotIn("Leite Integral Itambé 1L", res, "sem estoque fica de fora")
        self.assertEqual(res["Leite Integral Tirol 1L"]["de"], 5.49)
        kit = self.S.busca_vtex("giassi", "picanha", "v2.giassi")
        self.assertEqual(kit, [], "kit com + não é o produto")

    def test_secao_ean_e_link(self):
        c = self.S.busca_vtex("giassi", "coxinha", "v2.giassi")[0]
        self.assertEqual(c["secao"], "acougue/aves")
        self.assertEqual(c["secao_nome"], "Aves")
        self.assertEqual(c["ean"], EAN_COXINHA)
        self.assertTrue(c["link"].startswith("https://www.giassi.com.br/"))
        self.assertIn("regionId=v2.giassi", self.lojas.pedidos_de("product_search")[-1][1])

    def test_aprende_os_nomes(self):
        self.S.busca_vtex("giassi", "frango", None)
        self.assertIn("frango inteiro congelado kg", self.S.vocab()["set"])

    def test_regiao_da_loja_do_cep(self):
        S = self.S
        self.assertEqual(S.regiao_direta("giassi", CEP), ("v2.giassi", ""), "código 'giassi08' não é nome de loja")
        self.lojas.regioes.pop("angeloni")
        self.assertEqual(S.regiao_direta("angeloni", CEP), (None, ""))
        n = len(self.lojas.pedidos_de("regions"))
        S.regiao_direta("giassi", CEP)
        self.assertEqual(len(self.lojas.pedidos_de("regions")), n, "guardada por 6 horas")

    def test_secao_vtex_e_mesma_secao(self):
        S = self.S
        self.assertEqual(S.secao_vtex({"categories": ["/Açougue/", "/Açougue/Aves/Frango/"]}), ("acougue/aves/frango", "Frango"))
        self.assertEqual(S.secao_vtex({"categories": []}), ("", ""))
        self.assertTrue(S.mesma_secao("acougue", "acougue/aves"))
        self.assertTrue(S.mesma_secao("acougue/aves", "acougue/aves"))
        self.assertFalse(S.mesma_secao("acougue/aves", "acougue/bovinos"))
        self.assertFalse(S.mesma_secao("acougue/ave", "acougue/aves"), "prefixo de texto não é seção de dentro")


class Secao(Base):
    def test_almondega_de_outra_secao_sai(self):
        r = self.busca("Carne moída bovina de primeira")["Carne moída bovina de primeira"]
        precos = {k: (v["preco"] if isinstance(v, dict) else v) for k, v in r["precos"].items()}
        self.assertEqual(precos["merc-giassi"], 39.90)
        self.assertTrue(any("outra seção" in m and "Almôndega" in m for m in self.log), self.log)
        self.assertEqual(self.S.casados()["carne moida bovina de primeira"]["secoes"], {"giassi": ["acougue/bovinos"]})

    def test_secao_aprendida_filtra_o_parecido(self):
        S = self.S
        S.guarda_casados("Coxinha da asa", [], "giassi", ["acougue/aves"])
        cand = [{"nome": "Coxinha da Asa de Frango", "secao": "acougue/aves", "ean": ""},
                {"nome": "Coxinha de Frango Salgadinho", "secao": "congelados/salgados", "ean": ""},
                {"nome": "Coxinha sem seção", "secao": "", "ean": ""}]
        fica, firmes = S.filtra_secao("Coxinha da asa", "giassi", cand, set())
        self.assertEqual([c["nome"] for c in fica], ["Coxinha da Asa de Frango", "Coxinha sem seção"])
        self.assertEqual([c["nome"] for c in firmes], ["Coxinha da Asa de Frango"])

    def test_sem_secao_conhecida_nao_filtra(self):
        cand = [{"nome": "Coxinha de Frango", "secao": "x/y", "ean": ""}]
        fica, _ = self.S.filtra_secao("Coxinha da asa", "giassi", cand, set())
        self.assertEqual(fica, cand)

    def test_secao_afim(self):
        S = self.S
        self.assertTrue(S.secao_afim("Carne moída bovina", "acougue/bovinos"))
        self.assertTrue(S.secao_afim("Carne moída", "acougue/carnes"))
        self.assertFalse(S.secao_afim("Carne moída", "congelados/pratos prontos"))
        self.assertTrue(S.secao_afim("Arroz ou feijão", "mercearia/feijao"), "vale para qualquer lado do 'ou'")


class Similares(Base):
    def test_mais_em_conta_da_mesma_secao(self):
        r = self.busca({"produto": "Coxinha da asa", "similares": True})["Coxinha da asa"]
        nomes = [s["nome"] for s in r["similares"]]
        # por kg: frango inteiro 10,99, sobrecoxa 12,48, a bandeja de 2,3 kg 14,98 (R$ 34,45); a asa, 15,90, fica de fora
        self.assertEqual(nomes, ["Frango Inteiro Congelado Kg", "Sobrecoxa de Frango Resfriada Kg", "Sobrecoxa de Frango Member's Mark Congelada 2,3kg"])
        self.assertEqual(r["similares"][2]["preco"], 34.45)
        self.assertTrue(all(s["rede"] == "merc-giassi" and s["unidade"] == "kg" for s in r["similares"]))
        self.assertNotIn("Linguiça Toscana Kg", nomes, "seção de um nível acima (Açougue) não entra")
        self.assertTrue(self.lojas.pedidos_de("category-1/acougue/category-2/aves"), "busca pela seção (facetas)")

    def test_sem_pedir_nao_busca_similares(self):
        r = self.busca("Coxinha da asa")["Coxinha da asa"]
        self.assertNotIn("similares", r)
        self.assertFalse(self.lojas.pedidos_de("category-1/"))

    def test_secao_de_um_nivel_nao_da_similar(self):
        S = self.S
        cand = [{"nome": "Linguiça", "secao": "acougue", "secao_nome": "Açougue", "tam": (1, "kg"), "preco": 9.9, "link": "x"}]
        self.assertEqual(S.similares_vtex("giassi", None, "Linguiça", cand), [])

    def test_sem_facetas_busca_pelo_nome_da_secao(self):
        S = self.S
        # a loja não abre a seção pelo caminho: tenta "Aves" como texto
        cand = [{"nome": "Coxinha", "secao": "acougue/aves", "secao_nome": "Aves", "tam": (1, "kg"), "preco": 30, "link": "c"}]
        self.lojas.catalogo["giassi"] = [prod("Peito de Aves Kg", 20, AVES, "kg", 1)]
        self.lojas.paginas["/giassi/api/io/_v/api/intelligent-search/product_search/category-1/acougue/category-2/aves/"] = (200, '{"products": []}', "application/json")
        r = S.similares_vtex("giassi", None, "Coxinha", cand)
        self.assertEqual([p["nome"] for p in r], ["Peito de Aves Kg"])


class Alternativas(Base):
    def test_ou_busca_os_dois_lados(self):
        r = self.busca("Coxinha da asa ou asinha")["Coxinha da asa ou asinha"]
        precos = {k: (v["preco"] if isinstance(v, dict) else v) for k, v in r["precos"].items()}
        self.assertEqual(precos["merc-giassi"], 18.50, "a asinha, mais em conta, ganha")
        termos = [p[1] for p in self.lojas.pedidos_de("product_search")]
        self.assertTrue(any("query=Coxinha+da+asa&" in t for t in termos) and any("query=asinha&" in t for t in termos), termos)


class CodigoDeBarras(Base):
    def test_item_achado_so_pelo_codigo(self):
        r = self.busca({"produto": "Meu frango favorito", "ean": EAN_COXINHA})
        precos = {k: (v["preco"] if isinstance(v, dict) else v) for k, v in r["Meu frango favorito"]["precos"].items()}
        self.assertEqual(precos, {"merc-giassi": 21.90})
        self.assertIn(EAN_COXINHA, self.S.casados()["meu frango favorito"]["eans"])

    def test_produto_pelo_codigo_na_loja(self):
        r = self.S.produto_por_ean(EAN_COXINHA, {"cep": CEP, "lista": [{"produto": "Coxinha", "ean": EAN_COXINHA}]})
        self.assertTrue(r["ok"])
        self.assertEqual((r["nome"], r["fonte"], r["preco"]), ("Coxinha da Asa de Frango Resfriada Kg", "Giassi", 21.90))
        self.assertEqual(r["na_lista"], ["Coxinha"])

    def test_produto_pelo_codigo_no_open_food_facts(self):
        self.lojas.off["7896004000855"] = {"product_name_pt": "Biscoito Recheado Chocolate", "brands": "Bauducco,Pandurata", "quantity": "140 g"}
        r = self.S.produto_por_ean("7896004000855", {"cep": CEP})
        self.assertEqual((r["ok"], r["nome"], r["fonte"]), (True, "Biscoito Recheado Chocolate Bauducco 140 g", "Open Food Facts"))
        ua = self.lojas.pedidos_de("/off/")[-1][2].get("User-Agent", "")
        self.assertIn("EconomIA", ua, "o Open Food Facts pede um User-Agent que identifique o app")
        self.assertNotIn("@", ua, "sem e-mail de ninguém")

    def test_upc_balanca_invalido_e_nao_achado(self):
        S = self.S
        self.assertEqual(S.produto_por_ean("036000291452", {})["ean"], "0036000291452", "UPC-A vira EAN-13")
        r = S.produto_por_ean(ean13("200012300001"), {})
        self.assertFalse(r["ok"])
        self.assertIn("balança", r["msg"])
        self.assertFalse(S.produto_por_ean("7891000100104", {})["ok"])
        r = S.produto_por_ean("7891000100103", {"cep": CEP})
        self.assertFalse(r["ok"])
        self.assertEqual(r["ean"], "7891000100103", "código válido não achado: a página guarda o código no item")


class NomeCorrigido(Base):
    def test_busca_pelo_nome_corrigido(self):
        self.S.aprende_nomes(NOMES_VOCAB + ["Peito de Frango Sadia", "Frango Inteiro Seara", "Asa de Frango Copacol"])
        r = self.busca("Sobrecoxa de frago")
        precos = {k: (v["preco"] if isinstance(v, dict) else v) for k, v in r["Sobrecoxa de frago"]["precos"].items()}
        self.assertEqual(precos["merc-giassi"], 12.48)


class Categoria(Base):
    def test_loja_que_nao_atende_o_cep(self):
        self.lojas.regioes = {"giassi": "giassi08"}
        r = self.busca("Carne moída bovina de primeira")
        self.assertEqual(set(r["Carne moída bovina de primeira"]["precos"]), {"merc-giassi"})
        self.assertTrue(any("não atende o CEP" in m for m in self.log))

    def test_sem_cep_nao_busca(self):
        self.assertEqual(self.S.busca_direta({"lista": [{"produto": "Leite"}]}), [])


class Bordas(Base):
    """A loja do CEP que não responde, o erro num item que não para os outros, o estado das lojas com busca direta,
    a correção que quebra, o Open Food Facts fora do ar e similares sem tamanho para comparar."""

    def test_loja_do_cep_que_nao_responde_e_item_com_erro(self):
        S = self.S
        S.regiao_direta = (lambda orig: (lambda k, cep: (_ for _ in ()).throw(OSError("tempo esgotado")) if k == "angeloni" else orig(k, cep)))(S.regiao_direta)
        S.alternativas = (lambda orig: (lambda n: (_ for _ in ()).throw(ValueError("nome estranho")) if n == "Item Quebrado" else orig(n)))(S.alternativas)
        r = self.busca("Item Quebrado", "Leite integral")
        self.assertEqual(set(r["Leite integral"]["precos"]), {"merc-giassi"}, "o erro num item não para os outros")
        self.assertIn("busca direta Angeloni: não consegui saber a loja do CEP (tempo esgotado)", self.log)
        self.assertIn("busca direta Giassi 'Item Quebrado': nome estranho", self.log)

    def test_estado_das_lojas_com_busca_direta(self):
        S = self.S
        b = self.lojas.base
        S.gravar_json(S.LOJAS_SITE, {b + "/farmavida": {"nome": "Farmácia Vida", "paginas": True, "vtex": False, "em": "2099-01-01T00:00:00+00:00"}})
        S.regiao_direta = (lambda orig: (lambda k, cep: (_ for _ in ()).throw(OSError("x" * 200)) if k == "angeloni" else orig(k, cep)))(S.regiao_direta)
        st = {x["id"]: x for x in S.lojas_diretas_status({"cep": CEP})}
        self.assertEqual((st["giassi"]["atende"], st["giassi"]["fixa"]), (True, True))
        self.assertEqual((st["angeloni"]["atende"], len(st["angeloni"]["erro"])), (None, 120), "o erro, curto")
        self.assertEqual(st["farmacia-vida"], {"id": "farmacia-vida", "nome": "Farmácia Vida", "atende": None, "paginas": True},
                         "site comum que deixa ler as páginas")

    def test_correcao_que_quebra(self):
        S = self.S
        S.corrige_texto = lambda n: (_ for _ in ()).throw(KeyError("vocab")) if n == "Ruim" else ("Leite" if n == "Leiet" else None)
        self.assertEqual(S.sugestoes_para(["Ruim", "Leiet", "Café"]), {"Leiet": "Leite"})

    def test_open_food_facts_fora_do_ar(self):
        S = self.S
        S.OFF_API = "http://127.0.0.1:9"
        r = S.produto_por_ean("7896004000855", {"cep": CEP})
        self.assertFalse(r["ok"])
        self.assertIn("Não achei esse código nas lojas nem no Open Food Facts", r["msg"])
        S.busca_vtex = lambda *a, **k: (_ for _ in ()).throw(OSError("loja fora"))
        self.assertFalse(S.produto_por_ean(EAN_COXINHA, {"cep": CEP})["ok"], "a loja que falha é pulada")

    def test_similares_sem_tamanho_ou_unidade_diferente(self):
        S = self.S
        cand = [{"nome": "Coxinha", "secao": "acougue/aves", "secao_nome": "Aves", "tam": None, "preco": 30, "link": "c"}]
        self.assertEqual(S.similares_vtex("giassi", None, "Coxinha", cand), [], "sem tamanho: não dá para comparar o quilo")
        cand = [{"nome": "Coxinha", "secao": "acougue/aves", "secao_nome": "Aves", "tam": (1.0, "kg"), "preco": 30, "link": "c"}]
        self.lojas.catalogo["giassi"] = [prod("Frango Inteiro Congelado Kg", 10.99, AVES, "kg", 1), prod("Caldo de Galinha 1L", 5.0, AVES),
                                         prod("Asa sem seção", 9.0, None, "kg", 1)]
        self.assertEqual([p["nome"] for p in S.similares_vtex("giassi", None, "Coxinha", cand)], ["Frango Inteiro Congelado Kg"],
                         "litro não se compara com quilo; sem seção fica de fora")

    def test_loja_achada_fora_do_bairro_so_como_mercado_que_entrega(self):
        S = self.S
        self.lojas.regioes["super-longe"] = "l1"
        self.lojas.catalogo["super-longe"] = [prod("Leite Integral Tirol 1L", 3.99, "Laticínios/Leites")]
        S.VTEX_ACHADAS["super-longe"] = {"nome": "Super Longe", "site": self.lojas.base + "/super-longe", "categoria": "mercados"}
        self.busca("Leite integral")
        self.assertFalse(self.lojas.pedidos_de("/super-longe/"), "não fica no bairro e Online não está marcado: nem pergunta")
        cfg = {"cep": CEP, "categorias": ["mercados", "online"], "lista": [{"produto": "Leite integral"}]}
        cats = {c["id"]: c for c, _ in S.busca_direta(cfg, cats=("mercados",))}
        self.assertIn("onli-super-longe", [r["id"] for r in cats["online"]["redes"]], "com Online marcado: entra como mercado que entrega")


if __name__ == "__main__":
    unittest.main()
