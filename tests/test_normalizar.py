"""A resposta da IA (ou dos sites) antes de gravar (normalizar): lojas, cupons, ofertas, preços da lista, tamanhos,
similares, online com frete, clube; e a junção dos itens entre categorias (juntar_item, juntar_categorias, item_ofertas,
sem_repetir_tamanhos) e o item certo da lista (casar_item)."""
from apoio import Cenario


class Base(Cenario):
    def n(self, bruto, cat="mercados", lista=("Leite integral", "Café 500 g")):
        return self.S.normalizar(cat, bruto, {"lista": [{"produto": x} for x in lista]})

    def item(self, precos=None, base=None, tamanhos=None, links=None, similares=None):
        return {"precos": dict(precos or {}), "base": base, "tamanhos": list(tamanhos or []), "links": dict(links or {}), "vistos": {},
                **({"similares": similares} if similares else {})}


class Lojas(Base):
    def test_resposta_fora_do_formato(self):
        with self.assertRaisesRegex(self.S.ErroBusca, "fora do formato"):
            self.n(["lista"])

    def test_sem_busca_na_web(self):
        with self.assertRaisesRegex(self.S.ErroBusca, "não usou a busca na web"):
            self.n({"erro": "sem_busca"})

    def test_lojas_sem_nome_ficam_de_fora(self):
        cat, _ = self.n({"lojas": ["texto", {"rede": ""}, {"rede": None}, {"rede": "Bistek", "distancia_km": "1,5"}]})
        self.assertEqual([l["rede"] for l in cat["lojas"]], ["merc-bistek"])
        self.assertEqual(cat["lojas"][0]["distancia_km"], 1.5)

    def test_a_mesma_rede_fica_com_a_filial_mais_perto(self):
        cat, _ = self.n({"lojas": [{"rede": "Bistek", "distancia_km": 2.0, "endereco": "Longe"}, {"rede": "Bistek", "distancia_km": 1.0, "endereco": "Perto"},
                                   {"rede": "Bistek", "distancia_km": None}, {"rede": "Bistek", "distancia_km": 3}]})
        self.assertEqual([(l["distancia_km"], l["endereco"]) for l in cat["lojas"]], [(1.0, "Perto")])

    def test_fontes_e_site(self):
        cat, _ = self.n({"lojas": [{"rede": "A", "fontes": ["Site", "Inventada", "Encarte"], "site": "https://a.com.br/ofertas"},
                                   {"rede": "B", "site": "a.com.br"}]})
        a, b = cat["lojas"]
        self.assertEqual((a["fontes"], a["site"]), (["Site", "Encarte"], "https://a.com.br/ofertas"))
        self.assertEqual((b["fontes"], "site" in b), (["Site"], False), "sem fontes: Site; site sem https fica de fora")

    def test_nome_da_loja_com_busca_direta(self):
        cat, _ = self.n({"lojas": [{"rede": "Giassi Supermercados - Joinville"}]})
        self.assertEqual(cat["redes"], [{"id": "merc-giassi", "nome": "Giassi", "curto": "Giassi"}])

    def test_lojas_da_mais_perto_para_a_mais_longe(self):
        cat, _ = self.n({"lojas": [{"rede": "C"}, {"rede": "A", "distancia_km": 3}, {"rede": "B", "distancia_km": 1}]})
        self.assertEqual([l["rede"] for l in cat["lojas"]], ["merc-b", "merc-a", "merc-c"])

    def test_clube_nas_fontes_vira_conta(self):
        cat, _ = self.n({"lojas": [{"rede": "Bistek", "fontes": ["Clube"]}, {"rede": "Giassi"}]})
        self.assertEqual(cat["contas"], [{"rede": "merc-bistek", "libera": "Preços e cupons do clube da loja", "status": "pendente"}])

    def test_rede_so_de_oferta_ganha_uma_loja(self):
        cat, _ = self.n({"ofertas": [{"rede": "Mercado X", "produto": "Arroz", "preco_oferta": 20}]})
        self.assertEqual(cat["lojas"], [{"rede": "merc-mercado-x", "distancia_km": None, "horario": "", "endereco": None, "fontes": ["Site"]}])

    def test_online_regional_e_marketplace(self):
        cat, _ = self.n({"ofertas": [{"rede": "Amazon", "produto": "A", "preco_oferta": 5, "frete": 0}, {"rede": "Bistek", "produto": "B", "preco_oferta": 5, "frete": 0}]},
                        cat="online")
        lojas = {l["rede"]: l for l in cat["lojas"]}
        self.assertNotIn("regional", lojas["onli-amazon"])
        self.assertTrue(lojas["onli-bistek"]["regional"])
        self.assertEqual(lojas["onli-amazon"]["horario"], "Entrega no seu CEP")


class Cupons(Base):
    def test_status_validade_e_beneficio(self):
        cat, _ = self.n({"cupons": [{"rede": "A", "codigo": "X1", "fonte": "a.com.br/cupom", "oficial": True, "valido_ate": "2026-12-01", "valor": "R$ 10"},
                                    {"rede": "A", "codigo": "X2", "fonte": "https://a.com.br", "valido_ate": "01/12"}]})
        c1, c2 = cat["cupons"]
        self.assertEqual((c1["status"], c1["valido_ate"], c1["valor"], c1["fonte"], c1["beneficio"]), ("confirmado", "2026-12-01", 10.0, "https://a.com.br/cupom", "Cupom de desconto"))
        self.assertEqual((c2["status"], c2["valido_ate"]), ("testar", None))

    def test_cupom_sem_link_codigo_ou_loja(self):
        cat, _ = self.n({"cupons": [{"rede": "A", "codigo": "X"}, {"rede": "A", "fonte": "https://a.com"}, {"codigo": "X", "fonte": "https://a.com"}, "x"]})
        self.assertEqual(cat["cupons"], [])
        self.assertTrue(any("3 cupom sem link ou sem código" in str(m) for m in self.log), "o sem loja só fica de fora")


class Ofertas(Base):
    def test_repetida_e_preco_normal_menor(self):
        cat, _ = self.n({"ofertas": [{"rede": "A", "produto": "Arroz 5 kg", "preco_normal": 20, "preco_oferta": 25}, {"rede": "A", "produto": "Arroz 5 kg", "preco_oferta": 1}]})
        self.assertEqual(len(cat["ofertas"]), 1)
        self.assertEqual((cat["ofertas"][0]["preco_normal"], cat["ofertas"][0]["tipo"]), (None, "preco"), "de menor que por: vale só o preço")

    def test_encarte_com_validade_unidade_condicao_e_receita(self):
        cat, _ = self.n({"ofertas": [{"rede": "A", "produto": "Picanha", "preco": "59,90", "encarte": True, "valido_ate": "2026-11-09", "unidade": "kg",
                                      "condicao": "Leve 2", "receita": "tarja", "tipo": "inventado", "tamanho": {"quantidade": 1, "unidade": "kg"}}]})
        o = cat["ofertas"][0]
        self.assertEqual((o["tipo"], o["encarte"], o["valido_ate"], o["unidade"], o["condicao"], o["receita"], o["preco_oferta"]),
                         ("encarte", True, "2026-11-09", "kg", "Leve 2", "tarja", 59.9))
        self.assertNotIn("tamanho", o, "com unidade (preço por quilo), sem tamanho")

    def test_tamanho_e_etiquetas(self):
        cat, _ = self.n({"ofertas": [{"rede": "A", "produto": "Café", "preco_normal": 20, "preco_oferta": 15, "tipo": "clube", "tags": ["cafe", "x"],
                                      "tamanho": {"quantidade": 500, "unidade": "g"}}]})
        o = cat["ofertas"][0]
        self.assertEqual((o["tipo"], o["tags"], o["tamanho"]), ("clube", ["cafe"], {"quantidade": 0.5, "unidade": "kg"}))

    def test_sem_loja_produto_ou_preco(self):
        cat, _ = self.n({"ofertas": [{"produto": "A", "preco_oferta": 1}, {"rede": "A", "preco_oferta": 1}, {"rede": "A", "produto": "B"}, "x"]})
        self.assertEqual(cat["ofertas"], [])
        self.assertTrue(any("3 oferta sem loja, produto ou preço" in str(m) for m in self.log))

    def test_online_frete_prazo_vendedor(self):
        cat, _ = self.n({"ofertas": [
            {"rede": "Amazon", "produto": "Sem frete", "preco_oferta": 5},
            {"rede": "Amazon", "produto": "Remédio", "preco_oferta": 5, "frete": 0, "receita": "tarja"},
            {"rede": "Amazon", "produto": "Carrinho", "preco_oferta": 5, "frete": "no carrinho"},
            {"rede": "Amazon", "produto": "Kit", "preco_oferta": 30, "frete": 9.9, "prazo_dias": "2", "unidades": 3, "vendedor": "Loja X",
             "oficial": True, "importado": True},
            {"rede": "Amazon", "produto": "Um", "preco_oferta": 5, "frete": 0, "unidades": 1}]}, cat="online")
        of = {o["produto"]: o for o in cat["ofertas"]}
        self.assertEqual(sorted(of), ["Carrinho", "Kit", "Um"], "sem frete e remédio de tarja ficam de fora")
        self.assertEqual((of["Carrinho"]["frete"], of["Carrinho"]["frete_carrinho"]), (None, True))
        k = of["Kit"]
        self.assertEqual((k["frete"], k["prazo_dias"], k["unidades"], k["vendedor"], k["oficial"], k["importado"]), (9.9, 2, 3, "Loja X", True, True))
        self.assertNotIn("unidades", of["Um"])
        self.assertFalse(of["Um"]["oficial"])


class PrecosDaLista(Base):
    def test_clube_e_obs(self):
        _, p = self.n({"lista": [{"item": 1, "precos": [{"rede": "A", "preco": 10, "preco_clube": 8}, {"rede": "B", "preco": 10, "preco_clube": 12},
                                                         {"rede": "C", "preco": 9, "obs": "Tirol 1 L"}]}]})
        pr = p["Leite integral"]["precos"]
        self.assertEqual(pr, {"merc-a": {"preco": 10.0, "clube": 8.0}, "merc-b": 10.0, "merc-c": {"preco": 9.0, "obs": "Tirol 1 L"}})

    def test_preco_sem_loja_usa_a_do_item(self):
        _, p = self.n({"lista": [{"item": 1, "rede": "Bistek", "precos": [{"preco": 5}]}]})
        self.assertEqual(p["Leite integral"]["precos"], {"merc-bistek": 5.0})

    def test_preco_sem_valor_ou_loja(self):
        _, p = self.n({"lista": [{"item": 1, "precos": [{"rede": "A"}, {"preco": 2}, "x"]}]})
        self.assertEqual(p, {}, "item sem nenhum preço válido não entra")

    def test_online_precisa_de_frete(self):
        _, p = self.n({"lista": [{"item": 1, "precos": [{"rede": "Amazon", "preco": 5}, {"rede": "Shopee", "preco": 4, "frete": "carrinho", "obs": "x"},
                                                         {"rede": "Magalu", "preco": 6, "frete": 0, "prazo_dias": 3}]}]}, cat="online")
        self.assertEqual(p["Leite integral"]["precos"], {"onli-shopee": {"preco": 4.0, "frete": None, "carrinho": True, "obs": "x"},
                                                         "onli-magalu": {"preco": 6.0, "frete": 0.0, "prazo_dias": 3}})

    def test_item_fora_da_lista_ou_invalido(self):
        _, p = self.n({"lista": ["x", {"item": 9, "produto": "Abacaxi", "precos": [{"rede": "A", "preco": 1}]}]})
        self.assertEqual(p, {})
        self.assertTrue(any("item que não está na lista" in str(m) for m in self.log))

    def test_links_e_vistos(self):
        _, p = self.n({"_via": "encarte", "lista": [{"item": 1, "precos": [{"rede": "A", "preco": 5, "fonte": "a.com.br/leite"}]}]})
        e = p["Leite integral"]
        self.assertEqual(e["links"], {"merc-a": "https://a.com.br/leite"})
        self.assertEqual(e["vistos"]["merc-a"]["via"], "encarte")

    def test_via_site_marca_o_que_foi_procurado(self):
        cat, _ = self.n({"_via": "site", "lojas": [{"rede": "Giassi"}], "lista": []})
        self.assertEqual((cat["_buscados"], cat["_redes_buscadas"]), (["leite integral", "cafe 500 g"], ["merc-giassi"]))


class Tamanhos(Base):
    def resp(self, tamanhos, base=None, cat="mercados"):
        _, p = self.n({"lista": [{"item": 1, "base": base or {"quantidade": 1, "unidade": "L"}, "precos": [{"rede": "A", "preco": 5}], "tamanhos": tamanhos}]}, cat=cat)
        return p["Leite integral"]

    def test_outros_tamanhos(self):
        e = self.resp([{"rede": "B", "embalagem": "Caixa com 12", "quantidade": 12, "unidade": "L", "preco": 55, "fonte": "https://b.com/12"},
                       "x", {"rede": "B", "quantidade": 500, "unidade": "g", "preco": 3}, {"quantidade": 2, "unidade": "L", "preco": 9},
                       {"rede": "B", "quantidade": 12, "unidade": "L", "preco": 50}])
        self.assertEqual(e["tamanhos"], [{"rede": "merc-b", "quantidade": 12.0, "embalagem": "Caixa com 12", "preco": 55.0, "fonte": "https://b.com/12"}],
                         "outra unidade, sem loja e repetido ficam de fora")

    def test_tamanho_da_base_vale_como_preco(self):
        e = self.resp([{"rede": "C", "quantidade": 1000, "unidade": "ml", "preco": 4.5, "fonte": "https://c.com/1l"}])
        self.assertEqual((e["precos"]["merc-c"], e["links"]["merc-c"], e["tamanhos"]), (4.5, "https://c.com/1l", []))

    def test_online_com_frete_e_prazo(self):
        e = self.resp([{"rede": "Amazon", "quantidade": 6, "unidade": "L", "preco": 30, "frete": 0, "prazo_dias": 2}], cat="online")
        self.assertEqual(e["tamanhos"], [{"rede": "onli-amazon", "quantidade": 6.0, "preco": 30.0, "frete": 0.0, "prazo_dias": 2}])

    def test_base_por_unidade_com_rotulo(self):
        e = self.resp([], base={"quantidade": 12, "unidade": "un", "rotulo": "Rolo"})
        self.assertEqual(e["base"], {"quantidade": 12.0, "unidade": "un", "rotulo": "rolo"})

    def test_similares(self):
        _, p = self.n({"lista": [{"item": 1, "precos": [{"rede": "A", "preco": 5}], "similares": [
            {"rede": "A", "nome": "Leite Desnatado 1L", "preco": 4, "quantidade": 1, "unidade": "L", "fonte": "a.com/x"},
            {"rede": "A", "nome": "Sem medida", "preco": 4}, "x"]}]})
        self.assertEqual(p["Leite integral"]["similares"], [{"rede": "merc-a", "nome": "Leite Desnatado 1L", "preco": 4.0, "quantidade": 1.0, "unidade": "L",
                                                             "fonte": "https://a.com/x"}])


class Juntar(Base):
    L1 = {"quantidade": 1.0, "unidade": "L"}

    def test_sem_base_herda_a_do_outro(self):
        dest = self.item({"merc-a": 5})
        self.S.juntar_item(dest, self.item({"merc-b": 4}, base=self.L1))
        self.assertEqual((dest["base"], dest["precos"]), (self.L1, {"merc-a": 5, "merc-b": 4}))

    def test_unidades_diferentes_nao_se_comparam(self):
        dest = self.item({"merc-a": 5}, base=self.L1)
        self.S.juntar_item(dest, self.item({"merc-b": 30}, base={"quantidade": 1.0, "unidade": "kg"}, tamanhos=[{"rede": "merc-b", "quantidade": 2, "preco": 50}]))
        self.assertEqual((dest["precos"], dest["tamanhos"]), ({"merc-a": 5, "merc-b": 30}, []))

    def test_outra_base_vira_tamanho(self):
        dest = self.item({"merc-a": 5}, base=self.L1)
        ent = self.item({"onli-x": {"preco": 20, "frete": 0, "prazo_dias": 1}, "merc-b": 22}, base={"quantidade": 5.0, "unidade": "L"}, links={"merc-b": "https://b/5l"},
                        tamanhos=[{"rede": "merc-c", "quantidade": 1.0, "preco": 4.8, "fonte": "https://c/1l"}, {"rede": "merc-c", "quantidade": 2.0, "preco": 9}])
        self.S.juntar_item(dest, ent)
        self.assertEqual(dest["precos"], {"merc-a": 5, "merc-c": 4.8}, "o tamanho igual à base vira preço")
        self.assertEqual(dest["links"], {"merc-c": "https://c/1l"})
        self.assertEqual(dest["tamanhos"], [{"rede": "onli-x", "quantidade": 5.0, "preco": 20, "frete": 0, "prazo_dias": 1},
                                            {"rede": "merc-b", "quantidade": 5.0, "preco": 22, "fonte": "https://b/5l"},
                                            {"rede": "merc-c", "quantidade": 2.0, "preco": 9}])

    def test_tamanho_online_da_outra_base_mantem_o_frete(self):
        dest = self.item({}, base=self.L1)
        self.S.juntar_item(dest, self.item({}, base={"quantidade": 5.0, "unidade": "L"}, tamanhos=[{"rede": "onli-x", "quantidade": 1.0, "preco": 4, "frete": 2}]))
        self.assertEqual(dest["precos"], {"onli-x": {"preco": 4, "frete": 2}})

    def test_mesma_base_junta_tamanhos_e_similares(self):
        dest = self.item({"merc-a": 5}, base=self.L1)
        self.S.juntar_item(dest, self.item({"merc-b": 4}, base=self.L1, tamanhos=[{"rede": "merc-b", "quantidade": 6, "preco": 20}], similares=[{"rede": "merc-b"}]))
        self.assertEqual((len(dest["tamanhos"]), dest["similares"]), (1, [{"rede": "merc-b"}]))

    def test_categorias_votam_a_base(self):
        S = self.S
        p1 = {"Leite": self.item({"merc-a": 5, "merc-b": 6}, base=self.L1)}
        p2 = {"Leite": self.item({"onli-x": 25}, base={"quantidade": 6.0, "unidade": "L"}), "Café": self.item({"onli-x": 10})}
        lista = S.juntar_categorias([p1, p2])
        self.assertEqual(lista["Leite"]["base"], self.L1, "a base com mais preços ganha")
        self.assertEqual(lista["Leite"]["tamanhos"][0]["quantidade"], 6.0)
        self.assertEqual(list(lista), ["Leite", "Café"])

    def test_item_ofertas(self):
        S = self.S
        tams = [{"rede": f"merc-{i}", "quantidade": 2.0, "preco": 10.0 + i} for i in range(15)] + [{"rede": "merc-0", "quantidade": 2.0, "preco": 1.0}]
        sims = [{"rede": "merc-a", "nome": "X", "preco": 9, "quantidade": 1}, {"rede": "merc-a", "nome": "x", "preco": 3, "quantidade": 1}] + \
               [{"rede": "merc-b", "nome": f"S{i}", "preco": 10 + i, "quantidade": 1} for i in range(8)]
        out = S.item_ofertas("Leite", self.item({"merc-a": 5}, base=self.L1, tamanhos=tams, links={"merc-a": "u", "merc-z": "v"}, similares=sims))
        self.assertEqual(out["links"], {"merc-a": "u"}, "só os links das lojas com preço")
        self.assertEqual(len(out["tamanhos"]), 12)
        self.assertEqual(out["tamanhos"][0], {"rede": "merc-0", "quantidade": 2.0, "preco": 1.0}, "a mesma loja e tamanho: fica o mais recente")
        self.assertEqual([x["nome"] for x in out["similares"]][:2], ["x", "S0"], "similares: o mais recente de cada nome, do mais barato por unidade")
        self.assertEqual(len(out["similares"]), 6)
        self.assertNotIn("tamanhos", S.item_ofertas("X", self.item({"merc-a": 1}, tamanhos=tams)), "sem base, sem tamanhos")

    def test_sem_repetir_tamanhos(self):
        S = self.S
        t = [{"rede": "a", "quantidade": 2, "preco": 9, "obs": "X"}, {"rede": "a", "quantidade": 2, "preco": 8, "obs": "x"}, {"rede": "a", "quantidade": 2, "preco": 7, "obs": "Y"},
             {"rede": "a", "quantidade": 0, "preco": 1}, "lixo"]
        self.assertEqual(S.sem_repetir_tamanhos(t), [{"rede": "a", "quantidade": 2, "preco": 8, "obs": "x"}, {"rede": "a", "quantidade": 2, "preco": 7, "obs": "Y"}])


class CasarItem(Base):
    NOMES = ["Leite integral", "Café Pilão 500 g", "Papel higiênico"]

    def test_pelo_numero_e_pelo_nome(self):
        S = self.S
        self.assertEqual(S.casar_item({"item": 2}, self.NOMES), "Café Pilão 500 g")
        self.assertEqual(S.casar_item({"item": "1"}, self.NOMES), "Leite integral")
        self.assertEqual(S.casar_item({"item": 9, "produto": "café pilão 500 g"}, self.NOMES), "Café Pilão 500 g")
        self.assertEqual(S.casar_item({"item": "x", "produto": "Leite integral (base: 1 L)"}, self.NOMES), "Leite integral")

    def test_parecido_e_plural(self):
        S = self.S
        self.assertEqual(S.casar_item({"produto": "Papel higiênico Neve"}, self.NOMES), "Papel higiênico")
        self.assertEqual(S.casar_item({"produto": "Cafés Pilão 500 g"}, self.NOMES), "Café Pilão 500 g", "o plural com s")
        self.assertIsNone(S.casar_item({"produto": "Leite"}, self.NOMES), "menos de 3/4 das palavras: não é o item")
        self.assertIsNone(S.casar_item({}, self.NOMES))
