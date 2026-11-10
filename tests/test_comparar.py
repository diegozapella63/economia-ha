"""Comparar preço (1.5.0): uma oferta procurada nas outras lojas, como o Buscar este item (primeiro os sites, a IA só
quando faltam preços), sem entrar na lista. A loja da própria oferta fica de fora; outro tamanho vale pelo preço por
quilo, litro ou unidade; o resultado fica em comparacoes.json e volta no api/estado."""
from apoio import Cenario, categoria, prod
from ha_falso import Erro

CAFE = "Mercearia/Café"


def oferta(i, rede, produto, por, de=None, **kw):
    return dict({"id": i, "rede": rede, "produto": produto, "preco_oferta": por, "preco_normal": de, "tipo": "promo" if de else "preco", "tags": []}, **kw)


OFERTAS = {"versao": 2, "lista": [{"produto": "Leite", "precos": {"merc-x": 5.0}}], "categorias": [
    categoria("mercados", [("merc-bistek", "Bistek", 2.4), ("merc-giassi", "Giassi", 1.1)], ofertas=[
        oferta("o-cafe", "merc-bistek", "Café Pilão Tradicional 500 g", 21.9, 26.9),
        oferta("o-cafe-giassi", "merc-giassi", "Café Pilão Tradicional 500 g", 19.9, 22.9),
        oferta("o-cafe-1kg", "merc-bistek", "Café Pilão Tradicional · 1 kg", 42.0, 49.9, tamanho={"quantidade": 1, "unidade": "kg"}),
        oferta("o-raro", "merc-bistek", "Geleia de jabuticaba artesanal 300 g", 25.0, 30.0)]),
    categoria("farmacias", [("farm-panvel", "Panvel", 0.8)], ofertas=[oferta("o-protetor", "farm-panvel", "Protetor solar Nivea FPS 50 · 200 ml", 59.9, 79.9)]),
    categoria("online", [("onli-amazon", "Amazon", None)], ofertas=[oferta("o-cafe-on", "onli-amazon", "Café Pilão Tradicional 500 g", 20.5, 24.0, frete=0)])]}


class Comparar(Cenario):
    def setUp(self):
        super().setUp()
        self.lojas.catalogo["giassi"] = [prod("Café Pilão Tradicional 500g", 19.90, CAFE)]
        self.lojas.catalogo["angeloni"] = [prod("Café Pilão Tradicional 500g", 23.50, CAFE, link="/cafe-ang/p")]
        self.ofertas(OFERTAS)

    def comparada(self, oid):
        return self.S.comparacoes()[oid]

    def test_mais_barato_em_outra_loja_pelos_sites(self):
        S, ha = self.S, self.ha
        self.config(categorias=["mercados"], lista=[{"produto": "Leite"}])
        S.comparar_oferta("o-cafe")
        self.assertIsNone(S.BUSCA["erro"])
        c = self.comparada("o-cafe")
        self.assertEqual((c["produto"], c["preco"]), ("Café Pilão Tradicional 500 g", 21.9))
        self.assertEqual([(p["loja"], p["preco"], p["equivale"]) for p in c["precos"]], [("Giassi", 19.9, 19.9), ("Angeloni", 23.5, 23.5)],
                         "do mais barato para o mais caro")
        self.assertTrue(c["precos"][0]["fonte"].startswith("http"), "com o link do produto")
        self.assertNotIn("quantidade", c["precos"][0], "o mesmo tamanho da oferta: sem o tamanho")
        self.assertEqual(ha.chamadas_ia, [], "2 preços pelos sites: sem IA")
        self.assertEqual((S.BUSCA["avisos"], S.BUSCA["rodando"], S.BUSCA["chamadas_ia"]),
                         (["Café Pilão Tradicional 500 g: mais barato em Giassi."], False, 0))
        self.assertEqual(S.nomes_da_lista(S.ler_config()), ["Leite"], "a lista não muda")
        self.assertEqual(S.ler_json(S.OFERTAS), OFERTAS, "as ofertas e os preços da lista não mudam")

    def test_a_loja_da_oferta_fica_de_fora(self):
        S = self.S
        self.config(categorias=["mercados"])
        S.comparar_oferta("o-cafe-giassi")
        c = self.comparada("o-cafe-giassi")
        self.assertEqual([p["loja"] for p in c["precos"]], ["Angeloni"], "o Giassi é a loja da oferta")
        self.assertEqual(S.BUSCA["avisos"], ["Café Pilão Tradicional 500 g: a oferta é o menor preço."])

    def test_outro_tamanho_pelo_preco_por_quilo(self):
        S = self.S
        self.config(categorias=["mercados"], usar_ia=False)
        S.comparar_oferta("o-cafe-1kg")  # 1 kg por R$ 42,00; o Giassi vende 500 g por R$ 19,90 (R$ 39,80 o quilo)
        c = self.comparada("o-cafe-1kg")
        self.assertEqual(c["produto"], "Café Pilão Tradicional", "procura sem o tamanho depois do ·")
        g = c["precos"][0]
        self.assertEqual((g["loja"], g["preco"], g["equivale"], g["quantidade"], g["unidade"]), ("Giassi", 19.9, 39.8, 0.5, "kg"))
        self.assertEqual(S.BUSCA["avisos"], ["Café Pilão Tradicional: mais barato em Giassi."])

    def test_tamanho_da_oferta(self):
        S = self.S
        self.assertEqual(S.tamanho_da_oferta({"produto": "Protetor solar Nivea FPS 50 · 200 ml"}), (0.2, "L"), "pelo nome")
        self.assertEqual(S.tamanho_da_oferta({"produto": "X", "tamanho": {"quantidade": 2, "unidade": "kg"}}), (2.0, "kg"))
        self.assertEqual(S.tamanho_da_oferta({"produto": "Picanha", "unidade": "kg"}), (1.0, "kg"), "preço por quilo")
        self.assertIsNone(S.tamanho_da_oferta({"produto": "Peitoral Tech Blue para Cães"}))
        self.assertEqual(S.termo_da_oferta("Protetor solar  Nivea FPS 50 · 200 ml"), "Protetor solar Nivea FPS 50")

    def test_medidas_diferentes_e_loja_repetida(self):
        S = self.S
        o = {"rede": "merc-bistek", "produto": "Café 500 g", "preco_oferta": 20}
        ent = {"base": {"quantidade": 1, "unidade": "L"}, "precos": {"merc-giassi": 10.0}, "tamanhos": []}
        self.assertEqual(S.comparar_precos(ent, {"merc-giassi": "Giassi"}, o, "Bistek"), [], "litro com quilo não dá para comparar")
        ent = {"base": {"quantidade": 0.5, "unidade": "kg"}, "links": {"merc-giassi": "giassi.com.br/x"},
               "precos": {"merc-giassi": 21.0, "onli-giassi": {"preco": 18.0, "frete": None, "carrinho": True, "obs": "Pilão 500 g"},
                          "onli-bistek": 15.0, "merc-angeloni": None},
               "tamanhos": [{"rede": "merc-giassi", "quantidade": 1, "preco": 30.0}, {"quantidade": 1, "preco": 1.0}]}
        r = S.comparar_precos(ent, {"merc-giassi": "Giassi", "onli-giassi": "Giassi", "merc-angeloni": "Angeloni"}, o, "Bistek")
        self.assertEqual(r, [{"loja": "Giassi", "preco": 30.0, "equivale": 15.0, "quantidade": 1, "unidade": "kg"}],
                         "um por loja, o mais em conta; o Bistek em outra categoria também é a loja da oferta; sem preço fica de fora")
        r = S.comparar_precos(dict(ent, tamanhos=[]), {"onli-giassi": "Giassi", "merc-giassi": "Giassi"}, o, "Bistek")
        self.assertEqual(r, [{"loja": "Giassi", "preco": 18.0, "equivale": 18.0, "carrinho": True, "obs": "Pilão 500 g"}],
                         "frete no carrinho e o que é cada preço")

    def test_outro_produto_fica_de_fora(self):
        """1.11.0: o Comparar só junta o mesmo produto. O "Creme Nivea Men 4 em 1" não é o "Creme de Barbear Nivea Men
        Sensitive" (que custava menos e aparecia como mais barato)."""
        S = self.S
        o = {"rede": "farm-floresta", "produto": "Creme Nivea Men 4 em 1, 30g", "preco_oferta": 19.99}
        ent = {"base": {"quantidade": 0.03, "unidade": "kg"}, "precos": {
            "farm-paguemenos": {"preco": 13.49, "obs": "Creme de Barbear Nivea Men Sensitive 65g"},
            "farm-popular": {"preco": 17.5, "obs": "Nivea Men Creme 4 em 1 Rosto Barba Mãos e Corpo 30g"},
            "farm-catarinense": {"preco": 15.3, "obs": "Creme Nivea Men 2 em 1 30g"}}, "tamanhos": []}
        r = S.comparar_precos(ent, {"farm-paguemenos": "Pague Menos", "farm-popular": "Preço Popular", "farm-catarinense": "Catarinense"}, o, "Floresta")
        self.assertEqual([p["loja"] for p in r], ["Preço Popular"], "o creme de barbear e o 2 em 1 são outros produtos")

    def test_regra_do_outro_produto(self):
        S = self.S
        mesmo = [("Creme Nivea Men 4 em 1, 30g", "Creme Nivea Men 4 em 1 30g"), ("Azeite Gallo Extra Virgem 500ml", "Azeite de Oliva Extra Virgem Gallo 500ml"),
                 ("Sabonete Dove Original 90g", "Sabonete em Barra Dove Cremoso Original 90g"), ("Shampoo Seda 325ml", "Shampoo Seda 2 em 1 325ml"),
                 ("Café 500 g", "Pilão 500 g"), ("Desodorante Rexona Men Active Dry Aerosol 150ml", "Desodorante Aerossol Rexona Men Active 150ml"), ("", "Qualquer")]
        for a, b in mesmo:
            self.assertFalse(S.outro_produto(a, b), f"{a} × {b}: o mesmo (ou não dá para dizer)")
        outros = [("Creme Nivea Men 4 em 1, 30g", "Creme de Barbear Nivea Men Sensitive 65g"), ("Creme Nivea Men 4 em 1", "Creme Nivea Men 2in1"),
                  ("Shampoo Seda Ceramidas 325ml", "Shampoo Seda Cachos Definidos 325ml"), ("Creme Nivea Men 4 em 1", "Nivea 30 g")]
        for a, b in outros:
            self.assertTrue(S.outro_produto(a, b), f"{a} × {b}: outro produto")
        self.assertEqual(S.palavras_produto("Creme Nivea Men 4 em 1, 30g"), ["creme", "nivea", "men", "4em1"])

    def test_a_ia_so_quando_faltam_precos(self):
        S, ha = self.S, self.ha
        self.config(categorias=["mercados", "online"])
        ha.responde_ia("itens sem preço", {"lista": [{"item": 1, "produto": "Geleia de jabuticaba artesanal 300 g", "precos": [
            {"rede": "Empório Bom", "categoria": "mercados", "preco": 19.0, "fonte": "https://emporio.com.br/geleia"},
            {"rede": "Amazon", "preco": 22.0, "frete": 5, "fonte": "https://amazon.com.br/geleia"}]}]})
        S.comparar_oferta("o-raro")
        self.assertEqual(len(ha.chamadas_ia), 1)
        self.assertIn("1) Geleia de jabuticaba artesanal 300 g", ha.chamadas_ia[0]["instructions"])
        self.assertIn('"categoria" é "mercados", "online"', ha.chamadas_ia[0]["instructions"], "a loja do bairro: o mesmo tipo e o online")
        c = self.comparada("o-raro")
        self.assertEqual([(p["loja"], p["equivale"]) for p in c["precos"]], [("Empório Bom", 19.0), ("Amazon", 27.0)], "online com o frete")
        self.assertEqual(S.BUSCA["chamadas_ia"], 1)

    def test_oferta_online_compara_com_todas(self):
        S = self.S
        self.config(categorias=["mercados", "farmacias", "online"])
        busca, pedidas = S.busca_scripts, []
        S.busca_scripts = lambda cfg, cats, itens, **k: pedidas.append((cats, itens, cfg["lista"])) or busca(cfg, cats, itens, **k)
        S.comparar_oferta("o-cafe-on")
        S.comparar_oferta("o-protetor")
        self.assertEqual(pedidas, [(["mercados", "farmacias", "online"], ["Café Pilão Tradicional 500 g"], [{"produto": "Café Pilão Tradicional 500 g"}]),
                                   (["farmacias", "online"], ["Protetor solar Nivea FPS 50"], [{"produto": "Protetor solar Nivea FPS 50"}])],
                         "a oferta online: todas as lojas; a da farmácia: farmácias e online")
        c = self.comparada("o-cafe-on")
        self.assertEqual(c["preco"], 20.5, "frete grátis")
        self.assertEqual([p["loja"] for p in c["precos"]], ["Giassi", "Angeloni"])

    def test_nada_achado_ia_desligada_ou_falhando(self):
        S, ha = self.S, self.ha
        self.config(categorias=["mercados"], usar_ia=False)
        S.comparar_oferta("o-raro")
        self.assertEqual((ha.chamadas_ia, self.comparada("o-raro")["precos"]), ([], []), "IA desligada: só os sites")
        self.assertEqual(S.BUSCA["avisos"], ["Geleia de jabuticaba artesanal 300 g: não achei em outras lojas."])
        self.config(categorias=["mercados"])
        ha.responde_ia("itens", Erro(500, "boom"))
        S.comparar_oferta("o-raro")
        self.assertIsNone(S.BUSCA["erro"], "a comparação fica com o que os sites acharam")
        self.assertEqual(S.BUSCA["avisos"], ["Geleia de jabuticaba artesanal 300 g: não achei em outras lojas, e a IA falhou: "
                                             "A IA do Home Assistant recusou o pedido (500): boom"])

    def test_erros(self):
        S = self.S
        self.config(categorias=["mercados"])
        S.comparar_oferta("o-nao-existe")
        self.assertEqual(S.BUSCA["erro"], S.OFERTA_SUMIU)
        self.assertFalse(S.BUSCA["rodando"])
        self.config(cep="")
        S.comparar_oferta("o-cafe")
        self.assertEqual(S.BUSCA["erro"], "Salve o CEP em Mais › Casa antes de buscar.")
        self.config(categorias=["mercados"])
        S.busca_scripts = lambda *a, **k: 1 / 0
        S.comparar_oferta("o-cafe")
        self.assertTrue(S.BUSCA["erro"].startswith("Erro inesperado na busca: "), S.BUSCA["erro"])
        self.ofertas(dict(OFERTAS, categorias=["lixo"] + OFERTAS["categorias"]))
        self.assertEqual(S.acha_oferta("o-protetor")[0::2], ("farmacias", "Panvel"))

    def test_guarda_as_mais_recentes(self):
        S = self.S
        S.MAX_COMPARACOES = 3
        for i in range(5):
            S.guarda_comparacao(f"o-{i}", {"em": f"2026-11-0{i + 1}T10:00:00-03:00", "precos": []})
        S.guarda_comparacao("o-2", {"em": "2026-11-09T10:00:00-03:00", "precos": []})
        self.assertEqual(list(S.comparacoes()), ["o-3", "o-4", "o-2"], "a mais recente fica, a mais antiga sai")
        S.gravar_json(S.COMPARACOES, ["lixo"])
        self.assertEqual(S.comparacoes(), {})
