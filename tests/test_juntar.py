"""Montar os preços de um item e juntar o que cada busca achou: tamanho de sempre, outros tamanhos, promoções,
similares, a resposta da IA normalizada, a junção das categorias e o ofertas.json gravado."""
import json
import os
import unittest

from apoio import limpa, servidor


def cand(nome, preco, tam=None, de=None, link=None, ean=""):
    return {"nome": nome, "curto": nome[:20], "preco": preco, "de": de, "tam": tam, "link": link or "https://loja/" + nome.replace(" ", "-"), "ean": ean}


class Base(unittest.TestCase):
    def setUp(self):
        self.S, self.pasta, self.log = servidor()
        self.cfg = {"cep": "89216120", "lista": [{"produto": "Leite integral"}, {"produto": "Café 500 g"}, {"produto": "Coxinha da asa"}]}

    def tearDown(self):
        limpa(self.pasta)


class MontarItem(Base):
    def test_tamanho_de_sempre_pelo_mais_comum(self):
        ent, ofs = self.S.montar_item("Leite integral", {
            "Giassi": [cand("Leite Tirol 1L", 4.89, (1, "L"), de=5.49), cand("Leite Tirol 1L cx 12", 54.0, (12, "L"))],
            "Angeloni": [cand("Leite Tirol 1L", 5.29, (1, "L"))]})
        self.assertEqual(ent["base"], {"quantidade": 1, "unidade": "L"})
        self.assertEqual({p["rede"]: p["preco"] for p in ent["precos"]}, {"Giassi": 4.89, "Angeloni": 5.29})
        self.assertEqual([(t["rede"], t["quantidade"], t["preco"]) for t in ent["tamanhos"]], [("Giassi", 12, 54.0)])
        self.assertEqual([(o["rede"], o["preco_normal"], o["preco_oferta"]) for o in ofs], [("Giassi", 5.49, 4.89)])

    def test_tamanho_do_nome_do_item_manda(self):
        ent, _ = self.S.montar_item("Café 500 g", {"Giassi": [cand("Café Pilão 500g", 15.9, (0.5, "kg")), cand("Café Pilão 1kg", 29.9, (1, "kg")),
                                                              cand("Café Pilão 1kg b", 30.9, (1, "kg"))]})
        self.assertEqual(ent["base"], {"quantidade": 0.5, "unidade": "kg"})
        self.assertEqual(ent["precos"][0]["preco"], 15.9)

    def test_mais_barato_do_mesmo_tamanho_e_frete(self):
        ent, _ = self.S.montar_item("Leite integral", {"Shopee": [cand("A 1L", 6, (1, "L")), cand("B 1L", 5, (1, "L"))]}, frete="carrinho")
        self.assertEqual(ent["precos"][0]["preco"], 5)
        self.assertEqual(ent["precos"][0]["frete"], "carrinho")

    def test_similares_vao_na_entrada(self):
        ent, _ = self.S.montar_item("Coxinha da asa", {"Giassi": [cand("Coxinha kg", 21.9, (1, "kg"))]},
                                    similares={"Giassi": [cand("Sobrecoxa kg", 12.48, (1, "kg")), cand("Sem tamanho", 3)]})
        self.assertEqual(ent["similares"], [{"rede": "Giassi", "nome": "Sobrecoxa kg", "preco": 12.48, "quantidade": 1, "unidade": "kg",
                                             "fonte": "https://loja/Sobrecoxa-kg"}])

    def test_unicos_pelo_link(self):
        a, b = cand("A", 1, link="x"), cand("B", 2, link="x")
        self.assertEqual(self.S.unicos([a, b, cand("C", 3, link="y")]), [a, cand("C", 3, link="y")])


class Normalizar(Base):
    def bruto(self, **extra):
        b = {"_via": "site", "lojas": [{"rede": "Giassi Supermercados", "endereco": "Rua X", "distancia_km": 1.2, "fontes": ["Site"]}], "cupons": [], "ofertas": [],
             "lista": [{"produto": "Leite integral", "base": {"quantidade": 1, "unidade": "L"},
                        "precos": [{"rede": "Giassi", "preco": 4.89, "fonte": "giassi.com.br/leite"}],
                        "tamanhos": [{"rede": "Giassi", "quantidade": 12, "unidade": "L", "preco": 54, "embalagem": "Caixa 12"},
                                     {"rede": "Giassi", "quantidade": 1000, "unidade": "ml", "preco": 4.79}],
                        "similares": [{"rede": "Giassi", "nome": "Leite Semidesnatado", "preco": 4.5, "quantidade": 1, "unidade": "L"},
                                      {"rede": "Giassi", "nome": "", "preco": 1, "quantidade": 1, "unidade": "L"}]},
                       {"produto": "Item que não está na lista", "precos": [{"rede": "Giassi", "preco": 1}]}]}
        b.update(extra)
        return b

    def test_lista_em_ids_de_loja(self):
        cat, parcial = self.S.normalizar("mercados", self.bruto(), self.cfg)
        ent = parcial["Leite integral"]
        self.assertIn("merc-giassi", ent["precos"])
        self.assertEqual(ent["links"]["merc-giassi"], "https://giassi.com.br/leite")
        self.assertEqual([(t["quantidade"], t["preco"]) for t in ent["tamanhos"]], [(12, 54)], "1000 ml é o tamanho de sempre: vira preço, não tamanho")
        self.assertEqual(ent["similares"], [{"rede": "merc-giassi", "nome": "Leite Semidesnatado", "preco": 4.5, "quantidade": 1, "unidade": "L"}])
        self.assertNotIn("Item que não está na lista", parcial)
        self.assertEqual(cat["id"], "mercados")
        self.assertEqual([r["nome"] for r in cat["redes"]], ["Giassi"], "nome da loja com busca direta escrito do jeito dela")

    def test_ia_fora_do_formato(self):
        S = self.S
        with self.assertRaises(S.ErroBusca):
            S.normalizar("mercados", "texto solto", self.cfg)


class Juntar(Base):
    def test_juntar_categorias_usa_a_base_com_mais_precos(self):
        S = self.S
        a = {"Leite integral": {"precos": {"merc-giassi": 4.89, "merc-fort": 4.49}, "base": {"quantidade": 1, "unidade": "L"}, "tamanhos": [],
                                "links": {}, "vistos": {}, "similares": [{"rede": "merc-giassi", "nome": "S", "preco": 4, "quantidade": 1, "unidade": "L"}]}}
        b = {"Leite integral": {"precos": {"onli-amazon": 50}, "base": {"quantidade": 12, "unidade": "L"}, "tamanhos": [], "links": {"onli-amazon": "u"}, "vistos": {}}}
        lista = S.juntar_categorias([a, b])
        ent = lista["Leite integral"]
        self.assertEqual(ent["base"]["quantidade"], 1)
        self.assertEqual(set(ent["precos"]), {"merc-giassi", "merc-fort"})
        self.assertEqual([(t["rede"], t["quantidade"], t["preco"]) for t in ent["tamanhos"]], [("onli-amazon", 12, 50)], "a base de 12 L vira tamanho")
        self.assertEqual(len(ent["similares"]), 1)

    def test_item_ofertas_ordena_e_tira_repetidos(self):
        S = self.S
        ent = {"precos": {"a": 1}, "links": {"a": "u", "b": "v"}, "vistos": {"a": {"em": "x"}}, "base": {"quantidade": 1, "unidade": "kg"},
               "tamanhos": [{"rede": "a", "quantidade": 2, "preco": 10}, {"rede": "a", "quantidade": 2, "preco": 9}, {"rede": "b", "quantidade": 5, "preco": 20}],
               "similares": [{"rede": "a", "nome": "X", "preco": 30, "quantidade": 1}, {"rede": "a", "nome": "x", "preco": 20, "quantidade": 1},
                             {"rede": "b", "nome": "Y", "preco": 10, "quantidade": 2}, {"rede": "c", "nome": "Z", "preco": None, "quantidade": 1}]}
        out = S.item_ofertas("P", ent)
        self.assertEqual(out["links"], {"a": "u"}, "só os links das lojas com preço")
        self.assertEqual([(t["rede"], t["quantidade"], t["preco"]) for t in out["tamanhos"]], [("b", 5, 20), ("a", 2, 9)])
        self.assertEqual([(s["rede"], s["preco"]) for s in out["similares"]], [("b", 10), ("a", 20)], "um por loja e nome, o mais recente; sem preço sai")


class Mesclar(Base):
    def test_loja_consultada_de_novo_tira_o_preco_antigo(self):
        S = self.S
        S.gravar_json(S.OFERTAS, {"categorias": [], "lista": [
            {"produto": "Leite integral", "precos": {"merc-giassi": 9.99, "merc-fort": 4.49}, "base": {"quantidade": 1, "unidade": "L"},
             "tamanhos": [{"rede": "merc-giassi", "quantidade": 12, "preco": 99}], "links": {"merc-giassi": "velho"}, "vistos": {},
             "similares": [{"rede": "merc-giassi", "nome": "Velho", "preco": 1, "quantidade": 1, "unidade": "L"}]}]})
        cat = {"id": "mercados", "nome": "Mercados", "singular": "Mercado", "redes": [], "lojas": [], "cupons": [], "ofertas": [],
               "_buscados": ["leite integral"], "_redes_buscadas": ["merc-giassi"]}
        S.mesclar_resultado([(cat, {})], self.cfg)
        o = S.ler_json(S.OFERTAS)
        leite = next(i for i in o["lista"] if i["produto"] == "Leite integral")
        self.assertEqual(leite["precos"], {"merc-fort": 4.49})
        self.assertNotIn("similares", leite)
        self.assertNotIn("tamanhos", leite)
        self.assertNotIn("_buscados", o["categorias"][0])

    def test_relatorio_sem_preco_e_sugestoes(self):
        S = self.S
        S.mesclar_resultado([], dict(self.cfg, lista=[{"produto": "Leite integral"}]))
        o = S.ler_json(S.OFERTAS)
        self.assertEqual(o["relatorio"]["sem_preco"], ["Leite integral"])
        self.assertEqual(o["relatorio"]["sugestoes"], {})
        self.assertEqual(o["versao"], 2)

    def test_mantem_o_que_as_outras_buscas_acharam(self):
        S = self.S
        S.gravar_json(S.OFERTAS, {"categorias": [{"id": "farmacias", "lojas": [{"rede": "farm-raia"}], "redes": [{"id": "farm-raia", "nome": "Raia"}]}],
                                  "lista": [{"produto": "Café 500 g", "precos": {"farm-raia": 20}, "base": {"quantidade": 0.5, "unidade": "kg"}}]})
        S.mesclar_resultado([], self.cfg)
        o = S.ler_json(S.OFERTAS)
        self.assertEqual(o["categorias"][0]["id"], "farmacias")
        self.assertEqual(next(i for i in o["lista"] if i["produto"] == "Café 500 g")["precos"], {"farm-raia": 20})


class MesclarBordas(Base):
    """A mesma loja em outra categoria, a busca completa que tira o "esperando a próxima busca", o relatório que guarda
    só o que veio dos sites, e a data da busca que só muda na busca completa."""

    def test_a_mesma_loja_em_outra_categoria_tambem_sai(self):
        S = self.S
        S.gravar_json(S.OFERTAS, {"categorias": [], "lista": [{"produto": "Leite integral", "precos": {"onli-fort": 4.0, "merc-giassi": 5.0}},
                                                             {"produto": "Café 500 g", "precos": {"onli-fort": 15.0}}, "lixo", {"precos": {}}]})
        cat = {"id": "mercados", "nome": "Mercados", "singular": "Mercado", "redes": [], "lojas": [], "cupons": [], "ofertas": [],
               "_buscados": ["leite integral"], "_redes_buscadas": ["merc-fort"]}
        S.mesclar_resultado([(cat, {})], self.cfg)
        lista = {i["produto"]: i for i in S.ler_json(S.OFERTAS)["lista"]}
        self.assertEqual(lista["Leite integral"]["precos"], {"merc-giassi": 5.0}, "o Fort que era mercado que entrega")
        self.assertEqual(lista["Café 500 g"]["precos"], {"onli-fort": 15.0}, "item que não foi buscado agora fica")

    def test_busca_completa_e_relatorio(self):
        S = self.S
        S.gravar_json(S.OFERTAS, {"gerado_em": "2026-01-01T00:00:00", "relatorio": {"falhas": ["antiga"], "diretas": ["Velha"]},
                                  "categorias": [{"id": "mercados", "redes": [{"id": "merc-a", "nome": "A"}], "lojas": [{"rede": "merc-a", "nova": True}]}]})
        S.mesclar_resultado([], self.cfg, extra={"diretas": ["Giassi"], "shopee": 2, "instagram": ["x"]})
        o = S.ler_json(S.OFERTAS)
        self.assertEqual(o["gerado_em"], "2026-01-01T00:00:00", "só a busca completa muda a data da busca")
        self.assertTrue(o["categorias"][0]["lojas"][0]["nova"])
        self.assertEqual((o["relatorio"]["diretas"], o["relatorio"]["shopee"], o["relatorio"]["falhas"]), (["Giassi"], 2, ["antiga"]))
        self.assertNotIn("instagram", o["relatorio"], "só diretas, shopee e folhetos entram por aqui")
        S.mesclar_resultado([], self.cfg, completa=True)
        o = S.ler_json(S.OFERTAS)
        self.assertNotEqual(o["gerado_em"], "2026-01-01T00:00:00")
        self.assertNotIn("nova", o["categorias"][0]["lojas"][0], "busca feita: ninguém mais espera a próxima busca")


class Arquivos(Base):
    def test_gravar_e_ler_json(self):
        S = self.S
        p = os.path.join(self.pasta, "x.json")
        S.gravar_json(p, {"á": 1})
        with open(p, encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"á": 1})
        self.assertEqual(S.ler_json(os.path.join(self.pasta, "nao-existe.json"), {"padrao": True}), {"padrao": True})
        with open(p, "w") as f:
            f.write("{quebrado")
        self.assertEqual(S.ler_json(p, []), [])


class SimilaresGuardados(Base):
    """1.28.0: os similares achados ficam guardados por item, para o item que volta à lista não pedir outra busca."""

    def test_guardar_e_mandar_para_a_pagina(self):
        S = self.S
        S.hoje_br = lambda: "2026-11-02"
        sobre = {"rede": "merc-giassi", "nome": "Sobrecoxa kg", "preco": 12.48, "quantidade": 1, "unidade": "kg"}
        S.guardar_similares([{"produto": "Coxinha da asa", "precos": {}, "similares": [sobre] * 8}, {"produto": "Leite integral", "precos": {}}, None])
        reg = S.ler_json(S.SIMILARES_FILE, {})
        self.assertEqual(list(reg), ["coxinha da asa"], "só quem achou similar")
        self.assertEqual((reg["coxinha da asa"]["em"], len(reg["coxinha da asa"]["itens"])), ("2026-11-02", 6), "a data da busca e até 6")
        self.assertEqual(S.similares_salvos(self.cfg), {"Coxinha da asa": {"em": "2026-11-02", "itens": [sobre] * 6}})
        self.assertEqual(S.similares_salvos({"lista": [{"produto": "Leite integral"}, "Café"]}), {}, "só os itens da lista que têm")
        S.guardar_similares([{"produto": "Leite integral", "precos": {}}])
        self.assertEqual(list(S.ler_json(S.SIMILARES_FILE, {})), ["coxinha da asa"], "nada achado: não apaga o que estava guardado")
        S.gravar_json(S.SIMILARES_FILE, {"coxinha da asa": {"em": "ontem", "itens": [sobre]}})
        self.assertEqual(S.similares_salvos(self.cfg), {}, "data estranha: fica de fora")

    def test_ficam_os_mais_recentes(self):
        S = self.S
        S.MAX_SIMILARES_SALVOS = 3
        sim = [{"rede": "merc-giassi", "nome": "X", "preco": 1, "quantidade": 1, "unidade": "kg"}]
        for d, nome in (("2026-10-01", "A"), ("2026-10-02", "B"), ("2026-10-03", "C"), ("2026-10-04", "D")):
            S.hoje_br = lambda d=d: d
            S.guardar_similares([{"produto": nome, "precos": {}, "similares": sim}])
        self.assertEqual(sorted(S.ler_json(S.SIMILARES_FILE, {})), ["b", "c", "d"])

    def test_a_busca_guarda(self):
        S = self.S
        S.hoje_br = lambda: "2026-11-02"
        sim = {"rede": "merc-giassi", "nome": "Sobrecoxa kg", "preco": 12.48, "quantidade": 1, "unidade": "kg"}
        S.gravar_json(S.OFERTAS, {"categorias": [], "lista": [{"produto": "Coxinha da asa", "precos": {"merc-giassi": 21.9}, "similares": [sim]}]})
        S.mesclar_resultado([], self.cfg)
        self.assertEqual(S.ler_json(S.SIMILARES_FILE, {})["coxinha da asa"], {"produto": "Coxinha da asa", "em": "2026-11-02", "itens": [sim]})
        S.hoje_br = lambda: "2026-11-09"
        S.mesclar_resultado([], self.cfg)
        self.assertEqual(S.ler_json(S.SIMILARES_FILE, {})["coxinha da asa"]["em"], "2026-11-02", "os mesmos de antes: fica a data em que foram achados")

if __name__ == "__main__":
    unittest.main()
