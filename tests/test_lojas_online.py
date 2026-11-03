"""Preços sem IA nos sites das lojas e o teste de cada loja: o robots.txt (testa_site, com os erros de cada tipo), a busca
direta nas lojas VTEX achadas, a lista de produtos do sitemap e o preço na página do produto, a busca do site, a página
de ofertas, a Shopee pela Open API, o site das lojas pelo Brave e pela IA, o Testar agora (testa_preco_loja,
testa_marketplace, sonda_loja, sonda_lojas) e a ordem de busca_scripts."""
import gzip
import types

from apoio import FECHA, Cenario, categoria, prod

LD = """<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Product","name":"{n}","brand":{{"name":"{m}"}},
"offers":{{"@type":"Offer","price":"{p}","availability":"https://schema.org/{d}"}}}}</script>"""


def urlset(urls):
    return "<urlset>" + "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>"


class Base(Cenario):
    def setUp(self):
        super().setUp()
        self.S.time = types.SimpleNamespace(time=self.S.time.time, sleep=lambda s: None)  # sem as pausas educadas entre pedidos
        b, lj = self.lojas.base, self.lojas
        # Farmácia Vida: robots.txt proíbe /api/, publica o sitemap (índice → produtos em .gz) e as páginas de produto
        lj.paginas["/farmavida/robots.txt"] = (200, f"User-agent: *\nDisallow: /api/\nDisallow: /checkout\nSitemap: {b}/farmavida/sitemap.xml\n", "text/plain")
        lj.paginas["/farmavida/sitemap.xml"] = (200, f"<sitemapindex><sitemap><loc>{b}/farmavida/sitemap-categorias.xml</loc></sitemap>"
                                                     f"<sitemap><loc>{b}/farmavida/sitemap-produtos.xml.gz</loc></sitemap></sitemapindex>", "application/xml")
        prods = [f"{b}/farmavida/dipirona-monoidratada-500mg-10-comprimidos/p", f"{b}/farmavida/dipirona-gotas-20ml/p", f"{b}/farmavida/shampoo-seda-325ml/p"]
        lj.paginas["/farmavida/sitemap-produtos.xml.gz"] = (200, gzip.compress(urlset(prods).encode()), "application/gzip")
        lj.paginas["/farmavida/dipirona-monoidratada-500mg-10-comprimidos/p"] = (200, LD.format(n="Dipirona Monoidratada 500mg 10 Comprimidos", m="EMS", p="8.90", d="InStock"), "text/html")
        lj.paginas["/farmavida/dipirona-gotas-20ml/p"] = (200, LD.format(n="Dipirona Gotas 20ml", m="EMS", p="6.50", d="OutOfStock"), "text/html")
        lj.paginas["/farmavida/shampoo-seda-325ml/p"] = (200, LD.format(n="Shampoo Seda 325ml", m="Seda", p="12.90", d="InStock"), "text/html")
        # Mercado Site: só a busca do próprio site mostra os preços
        lj.paginas["/mercadosite/robots.txt"] = (200, "User-agent: *\nDisallow: /api/\nDisallow: /pesquisa\n", "text/plain")
        lj.paginas["/mercadosite/busca"] = (200, "<html>" + LD.format(n="Leite Integral Tirol 1L", m="Tirol", p="4.79", d="InStock")
                                            + LD.format(n="Leite Desnatado Tirol 1L", m="Tirol", p="4.99", d="InStock") + "</html>", "text/html")
        # Farmácia do Zé: a página inicial e a de ofertas mostram os produtos no texto
        lj.paginas["/farmaze/"] = (200, """<html><body><a href="/farmaze/ofertas-da-semana">Ofertas</a>
            <div><h3>Dipirona 500 mg caixa com 10 comprimidos</h3><s>R$ 9,90</s><b>R$ 7,49</b></div>
            <div><h3>Protetor Solar Nivea FPS 50</h3><b>R$ 39,90</b></div></body></html>""", "text/html")
        lj.paginas["/farmaze/ofertas-da-semana"] = (200, "<div><h3>Fralda Pampers Confort Sec G</h3><b>R$ 79,90</b></div>", "text/html")
        # Super Koch: loja VTEX que permite a consulta (nos testes, a pasta da loja é o slug do nome)
        lj.regioes["super-koch"] = "koch01"
        lj.catalogo["super-koch"] = [prod("Leite Integral Tirol 1L", 4.59, "Laticínios/Leites")]


class TestaSite(Base):
    def test_robots_e_vtex(self):
        S, b = self.S, self.lojas.base
        r = S.testa_site(b + "/farmavida", "89216-120")
        self.assertEqual((r["vtex"], r["permite"], r["paginas"]), (False, False, True), "proíbe /api/: só as páginas")
        self.assertEqual(r["sitemaps"], [b + "/farmavida/sitemap.xml"])
        self.assertFalse(self.lojas.pedidos_de("/farmavida/api/"), "o robots.txt proíbe: nem pergunta")
        r = S.testa_site(b + "/super-koch", "89216120")
        self.assertEqual((r["vtex"], r["permite"]), (True, True))
        self.assertTrue(self.lojas.pedidos_de("/super-koch/api/checkout/pub/regions?country=BRA&postalCode=89216120"))

    def test_erros(self):
        S, b, lj = self.S, self.lojas.base, self.lojas
        lj.paginas["/bloqueia/robots.txt"] = (403, "Forbidden", "text/html")
        lj.paginas["/fecha/robots.txt"] = FECHA
        lj.paginas["/quebrado/robots.txt"] = (500, "erro", "text/html")
        casos = [(b + "/bloqueia", "recusou o acesso de programas (erro 403)"), (b + "/quebrado", "respondeu com erro 500"),
                 (b + "/fecha", "fechou a conexão sem responder ao EconomIA. No navegador ele abre: é a proteção do site contra acesso de programas"),
                 ("http://127.0.0.1:9", "não respondeu (ConnectionRefusedError")]
        for origem, msg in casos:
            r = S.testa_site(origem, "1")
            self.assertTrue(r["erro"].startswith(msg), (origem, r))
            self.assertTrue(r["sem_resposta"])
            self.assertLess(r["em"], S.agora(), "sem resposta: tenta de novo no dia seguinte, não daqui a uma semana")

    def test_lojas_achadas_e_diretas(self):
        S, b = self.S, self.lojas.base
        cfg = self.config(lojas={"adicionar": [{"categoria": "mercados", "nome": "Super Koch, Centro", "site": b + "/super-koch/ofertas"},
                                               {"categoria": "farmacias", "nome": "Farmácia Vida", "site": b + "/farmavida/"},
                                               {"categoria": "online", "nome": "Não é física", "site": b + "/x"}]})
        self.ofertas({"categorias": [categoria("mercados", [("merc-giassi", "Giassi", 1.0, {"site": "https://www.giassi.com.br"})])],
                      "lista": [{"produto": "Leite", "links": {"onli-regional": b + "/regional/leite/p"}}]})
        self.ofertas({"categorias": [categoria("mercados", [("merc-giassi", "Giassi", 1.0, {"site": "https://www.giassi.com.br"})]),
                                     categoria("online", [("onli-regional", "Mercado Regional", None, {"regional": True})])],
                      "lista": [{"produto": "Leite", "links": {"onli-regional": b + "/regional/leite/p"}}]})
        self.lojas.paginas["/regional/robots.txt"] = (200, "User-agent: *\nDisallow: /api/\n", "text/plain")
        cand = S.candidatos_site(cfg)
        self.assertEqual(cand, {b + "/super-koch": ("Super Koch", "mercados"), b + "/farmavida": ("Farmácia Vida", "farmacias"),
                                b + "/regional": ("Mercado Regional", "online")}, "o site do Giassi (fixo) fica de fora")
        memo = S.atualiza_diretas(cfg)
        self.assertEqual(S.VTEX_ACHADAS, {"super-koch": {"nome": "Super Koch", "site": b + "/super-koch", "categoria": "mercados"}})
        self.assertTrue(memo[b + "/farmavida"]["paginas"])
        n = len(self.lojas.pedidos)
        S.atualiza_diretas(cfg)
        self.assertEqual(len(self.lojas.pedidos), n, "cada site é testado uma vez por semana")
        self.assertEqual(S.chave_direta(b + "/super-koch"), "super-koch")
        st = {x["id"]: x for x in S.lojas_diretas_status(cfg)}
        self.assertEqual((st["giassi"]["atende"], st["giassi"]["fixa"], st["giassi"]["loja"]), (True, True, ""), "giassi08 é código, não nome de loja")
        self.assertEqual((st["super-koch"]["atende"], st["super-koch"]["fixa"]), (True, False))
        self.assertTrue(st["farmacia-vida"]["paginas"])
        # a loja VTEX achada entra na busca direta
        self.ofertas({"categorias": [categoria("mercados", [("merc-super-koch", "Super Koch", 1.0)])]})
        res = S.busca_direta(self.config(lista=[{"produto": "Leite integral"}]), cats=("mercados",))
        nomes = {r["nome"] for c, _ in res for r in c["redes"]}
        self.assertIn("Super Koch", nomes)

    def test_site_das_redes(self):
        S = self.S
        self.assertEqual(S.site_da_rede("Atacadão Joinville", "Joinville"), "https://www.atacadao.com.br")
        self.assertIsNone(S.site_da_rede("Atacadão Dia a Dia"), "outra rede com o mesmo começo")
        self.assertEqual(S.site_da_rede("FarmaSesi - Itoupava Norte"), "https://www.farmasesi.com.br")
        self.assertEqual(S.site_da_rede("Drogaria Catarinense Floresta"), "https://www.drogariacatarinense.com.br")
        self.assertIsNone(S.site_da_rede("Farmácia do Zé"))
        self.assertEqual(S.origem_de("https://www.Loja.com.br/ofertas?x=1"), "https://www.loja.com.br")


class Catalogo(Base):
    def test_sitemap_e_pagina_do_produto(self):
        S, b = self.S, self.lojas.base
        info = S.testa_site(b + "/farmavida", "1")
        c = S.baixa_catalogo(b + "/farmavida", info)
        self.assertEqual(len(c["urls"]), 3, "do índice, só o sitemap de produtos (o .gz também)")
        self.assertFalse(self.lojas.pedidos_de("sitemap-categorias"))
        self.assertTrue(S.arquivo_catalogo(b + "/farmavida").endswith(".json"))
        n = len(self.lojas.pedidos)
        S.baixa_catalogo(b + "/farmavida", info)
        self.assertEqual(len(self.lojas.pedidos), n, "guardado por um dia")
        r = S.preco_produto(b + "/farmavida", c, b + "/farmavida/dipirona-monoidratada-500mg-10-comprimidos/p")
        self.assertEqual(r, {"nome": "Dipirona Monoidratada 500mg 10 Comprimidos", "marca": "EMS", "preco": 8.9, "disponivel": True})
        self.assertIsNone(S.preco_produto(b + "/farmavida", c, b + "/farmavida/dipirona-gotas-20ml/p"), "fora de estoque")
        n = len(self.lojas.pedidos)
        S.preco_produto(b + "/farmavida", c, b + "/farmavida/dipirona-monoidratada-500mg-10-comprimidos/p")
        self.assertEqual(len(self.lojas.pedidos), n, "o preço também fica guardado por um dia")
        proibido = dict(info, regras=S.robots_regras("User-agent: *\nDisallow: /farmavida/sitemap\n"))
        S.gravar_json(S.arquivo_catalogo(b + "/farmavida"), {})
        self.assertEqual(S.baixa_catalogo(b + "/farmavida", proibido)["urls"], [], "o robots.txt proíbe o sitemap")

    def test_busca_pelas_paginas_de_produto(self):
        S, b = self.S, self.lojas.base
        memo = {b + "/farmavida": dict(S.testa_site(b + "/farmavida", "1"), nome="Farmácia Vida", categoria="farmacias"),
                "https://www.amazon.com.br": {"nome": "Amazon", "paginas": True}}
        S.gravar_json(S.LOJAS_SITE, memo)
        self.ofertas({"categorias": [categoria("farmacias", [("farm-farmacia-vida", "Farmácia Vida", 1.0)])]})
        cfg = self.config(categorias=["farmacias"], lista=[{"produto": "Dipirona 500 mg"}, {"produto": "Shampoo Seda"}])
        res = S.busca_catalogos(cfg)
        self.assertEqual(len(res), 1, "marketplace fica de fora (o sitemap tem milhões de páginas)")
        cat, parcial = res[0]
        self.assertEqual(cat["id"], "farmacias")
        self.assertEqual(S.valor_total(parcial["Dipirona 500 mg"]["precos"]["farm-farmacia-vida"]), 8.9)
        self.assertEqual(S.valor_total(parcial["Shampoo Seda"]["precos"]["farm-farmacia-vida"]), 12.9)
        self.assertEqual(parcial["Shampoo Seda"]["vistos"]["farm-farmacia-vida"]["via"], "site")
        # fora do raio: vai para Online, com frete no carrinho
        self.ofertas({"categorias": []})
        cat, parcial = S.busca_catalogos(cfg, cats=["farmacias", "online"])[0]
        self.assertEqual(cat["id"], "online")
        self.assertEqual(parcial["Shampoo Seda"]["precos"]["onli-farmacia-vida"]["carrinho"], True)
        self.assertEqual(S.busca_catalogos(cfg, cats=["farmacias"]), [], "online não pedido: nada")


class BuscaDoSiteEOfertas(Base):
    def test_busca_do_site(self):
        S, b = self.S, self.lojas.base
        info = dict(S.testa_site(b + "/mercadosite", "1"), nome="Mercado Site", categoria="mercados")
        ofs = S.busca_do_site(b + "/mercadosite", info, "leite integral")
        self.assertEqual([o["produto"] for o in ofs], ["Leite Integral Tirol 1L"])
        self.assertEqual(info["busca"], "/busca?q={}", "/pesquisa é proibido no robots.txt; o modelo que funcionou fica")
        self.assertFalse(self.lojas.pedidos_de("/mercadosite/pesquisa"))
        S.gravar_json(S.LOJAS_SITE, {b + "/mercadosite": info})
        cfg = self.config(lista=[{"produto": "Leite integral ou desnatado"}, {"produto": "Leite integral"}])
        res = S.busca_sites(cfg, cats=["mercados", "online"])
        cat, parcial = res[0]
        self.assertEqual(cat["id"], "online", "fora do raio: loja que entrega")
        self.assertEqual(sorted(p for p in parcial), ["Leite integral", "Leite integral ou desnatado"])
        self.assertEqual(parcial["Leite integral"]["links"]["onli-mercado-site"], b + "/mercadosite/busca?q=Leite%20integral")
        self.assertEqual(S.busca_sites(cfg, cats=["mercados"]), [])

    def test_pagina_de_ofertas(self):
        S, b, lj = self.S, self.lojas.base, self.lojas
        ofs, lidas = S.ofertas_do_site(b + "/farmaze/", {"regras": []})
        self.assertEqual(lidas, [b + "/farmaze/", b + "/farmaze/ofertas-da-semana"], "segue o link de ofertas do mesmo site")
        self.assertEqual([(o["produto"], o["preco"], o["preco_normal"]) for o in ofs],
                         [("Dipirona 500 mg caixa com 10 comprimidos", 7.49, 9.9), ("Protetor Solar Nivea FPS 50", 39.9, None),
                          ("Fralda Pampers Confort Sec G", 79.9, None)])
        n = len(lj.pedidos)
        S.ofertas_do_site(b + "/farmaze/", {"regras": []})
        self.assertEqual(len(lj.pedidos), n, "guardado por 12 horas")
        S.ofertas_do_site(b + "/farmaze/", {"regras": []}, forcar=True)
        self.assertGreater(len(lj.pedidos), n)
        self.assertEqual(S.ofertas_do_site(b + "/farmaze/", {"regras": S.robots_regras("User-agent: *\nDisallow: /farmaze/\n")}), (None, []),
                         "o robots.txt não deixa: nem abre")
        lj.paginas["/velha/"] = (200, "<p>Ofertas válidas até 10/01/2020</p><div><h3>Arroz Tio João 5 kg</h3><b>R$ 24,90</b></div>", "text/html")
        self.assertEqual(S.le_pagina_ofertas(b + "/velha/", []), ([], []), "ofertas vencidas ficam de fora")
        # na busca: lojas que o teste achou com a página de ofertas
        S.gravar_json(S.SONDA_FILE, {"farmacias": {"farmacia do ze": {"como": "ofertas_site", "url": b + "/farmaze/", "nome": "Farmácia do Zé"},
                                                   "outra": {"como": "site"}}})
        cfg = self.config(lista=[{"produto": "Dipirona 500 mg"}, {"produto": "Protetor solar"}])
        res = S.busca_paginas_ofertas(cfg, ["farmacias"], {})
        cat, parcial = res[0]
        self.assertEqual(cat["redes"][0]["nome"], "Farmácia do Zé")
        self.assertEqual(len(cat["ofertas"]), 3)
        self.assertEqual(S.valor_total(parcial["Dipirona 500 mg"]["precos"]["farm-farmacia-do-ze"]), 7.49)
        self.assertEqual(S.busca_paginas_ofertas(cfg, ["farmacias"], {"farmacias": ["Farmácia do Zé"]}), [], "loja que já tem preço por outro caminho")


class Shopee(Base):
    def setUp(self):
        super().setUp()
        self.lojas.rotas["/shopee"] = self.shopee

    def shopee(self, p):
        self.assertTrue(p.cabecalhos["Authorization"].startswith("SHA256 Credential=18300000001, Timestamp="))
        q = p.json()["query"]
        if "Ração Golden" in q or "café 500 g" in q:
            return {"data": {"productOfferV2": {"nodes": [
                {"productName": "Ração Golden Adulto Frango 10kg", "priceMin": "129.90", "ratingStar": "4.8", "productLink": "https://shopee.com.br/racao-golden-i.1.2",
                 "offerLink": "https://s.shopee.com.br/afiliado"},
                {"productName": "Ração Golden Filhote 10kg", "priceMin": "99.90", "ratingStar": "4.2", "productLink": "https://shopee.com.br/x"},
                {"productName": "Brinquedo para cachorro", "priceMin": "9.90", "ratingStar": "5"}]}}}
        if "Recusado" in q:
            return {"errors": [{"message": "invalid keyword", "extensions": {"code": 11001}}]}
        if "Areia" in q:
            return {"errors": [{"message": "rate limit", "extensions": {"code": 10030}}]}
        return {"data": {"productOfferV2": {"nodes": []}}}

    def test_testar(self):
        S = self.S
        self.assertEqual(S.testar_shopee(), {"ok": False, "msg": "Falta o App ID e a senha da Shopee em Mais › Integrações."})
        S.grava_segredos({"shopee": {"app_id": "18300000001", "secret": "segredo"}})
        self.assertEqual(S.testar_shopee(), {"ok": True, "msg": "Pronta. Exemplo: Ração Golden Adulto Frango 10kg por R$ 129,90."})
        self.lojas.rotas["/shopee"] = lambda p: {"errors": [{"message": "x", "extensions": {"code": "10020"}}]}
        self.assertEqual(S.testar_shopee()["msg"], S.SHOPEE_ERROS[10020])
        self.lojas.rotas["/shopee"] = lambda p: {"data": {"productOfferV2": {"nodes": []}}}
        self.assertEqual(S.testar_shopee()["msg"], "A Shopee aceitou o App ID e a senha, mas não devolveu produtos no teste.")
        self.lojas.rotas["/shopee"] = lambda p: (500, "<html>erro</html>", "text/html")
        self.assertEqual(S.testar_shopee()["msg"], "A Shopee respondeu com erro 500.")

    def test_busca(self):
        S = self.S
        cfg = self.config(categorias=["online"], lista=[{"produto": "Ração Golden 10 kg"}])
        self.assertEqual(S.busca_shopee(cfg), [], "sem a chave: nada")
        S.grava_segredos({"shopee": {"app_id": "18300000001", "secret": "segredo"}})
        nomes = ["Ração Golden 10 kg", "Item Recusado", "Areia Pipicat 4 kg", "Depois do limite"]
        cat, parcial = S.busca_shopee(cfg, nomes)[0]
        self.assertEqual(cat["id"], "online")
        self.assertEqual(parcial["Ração Golden 10 kg"]["precos"], {"onli-shopee": {"preco": 129.9, "frete": None, "carrinho": True,
                                                                                   "obs": "Ração Golden Adulto Frango 10kg"}})
        self.assertEqual(parcial["Ração Golden 10 kg"]["links"]["onli-shopee"], "https://shopee.com.br/racao-golden-i.1.2", "o link do produto, não o de afiliado")
        self.assertEqual(parcial["Ração Golden 10 kg"]["vistos"]["onli-shopee"]["via"], "api")
        consultas = [p[3] for p in self.lojas.pedidos_de("/shopee")]
        self.assertTrue(any("Areia" in c for c in consultas))
        self.assertFalse(any("Depois do limite" in c for c in consultas), "limite (10030): para as consultas seguintes")

    def test_erros_de_conexao_e_codigo_desconhecido(self):
        S = self.S
        S.grava_segredos({"shopee": {"app_id": "18300000001", "secret": "segredo"}})
        S.SHOPEE_API = "http://127.0.0.1:9/graphql"
        with self.assertRaisesRegex(S.ErroShopee, r"^Não consegui falar com a Shopee \("):
            S.shopee_consulta("{x}")
        S.SHOPEE_API = self.lojas.base + "/shopee"
        self.lojas.rotas["/shopee"] = lambda p: (400, {"errors": [{"message": "Campo desconhecido", "extensions": {"code": "abc"}}]})
        with self.assertRaisesRegex(S.ErroShopee, "^A Shopee recusou a consulta: Campo desconhecido$"):
            S.shopee_consulta("{x}")
        self.lojas.rotas["/shopee"] = lambda p: {"errors": ["texto solto"]}
        with self.assertRaisesRegex(S.ErroShopee, "^A Shopee recusou a consulta: None$"):
            S.shopee_consulta("{x}")
        self.lojas.rotas["/shopee"] = lambda p: {"data": None}
        self.assertEqual(S.shopee_consulta("{x}"), {})

    def test_nada_achado_e_chaves_incompletas(self):
        S = self.S
        S.grava_segredos({"shopee": {"app_id": " 1 ", "secret": "  "}})
        self.assertFalse(S.shopee_pronta(), "senha em branco")
        S.grava_segredos({"shopee": {"app_id": "18300000001", "secret": "segredo"}})
        cfg = self.config(categorias=["online"], lista=[{"produto": "Vela aromática"}])
        self.assertEqual(S.busca_shopee(cfg), [])
        self.assertTrue(any("shopee: 0 de 1 item(ns) com preço" in str(m) for m in self.log))


class SitesDasLojas(Base):
    def setUp(self):
        super().setUp()
        self.lojas.rotas["/brave"] = self.brave

    def brave(self, p):
        if p.cabecalhos.get("X-Subscription-Token") != "chave-brave":
            return (401, {"error": "unauthorized"})
        self.assertEqual((p.query["country"], p.query["search_lang"]), (["BR"], ["pt-br"]))
        q = p.query["q"][0]
        if q.startswith("Mercado Kuntze"):
            return {"web": {"results": [{"url": "https://www.facebook.com/kuntze", "title": "Kuntze"}, {"url": "https://www.guiamais.com.br/kuntze", "title": "Kuntze"},
                                        {"url": "https://www.outrosite.com.br/", "title": "Outra coisa"},
                                        {"url": "https://www.kuntze.com.br/", "title": "Kuntze Supermercados"}]}}
        if q.startswith("Giassi"):
            return {"web": {"results": [{"url": "https://www.giassi.com.br", "title": "Giassi"}]}}
        return {"web": {"results": []}}

    def test_brave(self):
        S = self.S
        self.assertEqual(S.testar_brave(), {"ok": False, "msg": "Falta a chave do Brave."})
        S.grava_segredos({"brave": {"key": "chave-brave"}})
        self.assertEqual(S.testar_brave(), {"ok": True, "msg": "Pronta: o app procura o site das lojas que o mapa não traz."})
        self.assertEqual(S.site_pelo_brave("Mercado Kuntze", "Joinville", "chave-brave"), "https://www.kuntze.com.br/",
                         "pula rede social, guia e site sem o nome da loja")
        n = len(self.lojas.pedidos)
        self.assertIsNone(S.site_pelo_brave("Supermercado Joinville", "Joinville", "chave-brave"))
        self.assertEqual(len(self.lojas.pedidos), n, "nome só com palavras genéricas: nem busca")
        S.grava_segredos({"brave": {"key": "errada"}})
        self.assertEqual(S.testar_brave(), {"ok": False, "msg": "O Brave recusou a chave (401). Confira em Mais › Integrações."})
        self.lojas.rotas["/brave"] = lambda p: (429, {})
        self.assertEqual(S.testar_brave()["msg"], "O Brave pediu para esperar (limite de buscas do plano).")

    def test_brave_primeiro_depois_a_ia(self):
        S, ha = self.S, self.ha
        S.grava_segredos({"brave": {"key": "chave-brave"}})
        cfg = self.config()
        lojas = [{"nome": "Mercado Kuntze"}, {"nome": "Açougue Boi Dourado", "endereco": "Rua A, 1"}, {"nome": "Mercearia Dona Maria"}]
        ha.responde_ia("sites das lojas", {"lojas": [{"n": 1, "site": "https://www.instagram.com/boidourado"}, {"n": 2, "site": "https://donamaria.com.br"}]})
        r = S.sites_por_ia(cfg, lojas)
        self.assertEqual(r, {"mercado kuntze": "https://www.kuntze.com.br/", "mercearia dona maria": "https://donamaria.com.br"},
                         "Instagram não é site")
        pedido = ha.chamadas_ia[0]["instructions"]
        self.assertIn("lojas de Joinville (SC)", pedido)
        self.assertIn("1) Açougue Boi Dourado (Rua A, 1); 2) Mercearia Dona Maria", pedido, "a IA só para as que o Brave não achou")
        cache = S.ler_json(S.SITES_IA)
        self.assertEqual((cache["mercado kuntze"]["via"], cache["acougue boi dourado"]["via"], cache["acougue boi dourado"]["site"]), ("brave", "ia", None))
        n = len(ha.chamadas_ia), len(self.lojas.pedidos_de("/brave"))
        S.sites_por_ia(cfg, lojas)
        self.assertEqual((len(ha.chamadas_ia), len(self.lojas.pedidos_de("/brave"))), n, "guardado 30 dias, também o \"não tem\"")
        S.sites_por_ia(cfg, lojas, forcar=True)
        self.assertGreater(len(ha.chamadas_ia), n[0])
        self.assertIn("Use a busca na web agora e ache o site oficial", S.instrucoes_sites([{"nome": "X"}], "", ""))
        self.assertTrue(S.sem_site({}, "Mercearia Dona Maria", "", cfg))
        self.assertFalse(S.sem_site({"site": "https://x.com.br"}, "Mercearia Dona Maria", "", cfg))
        self.assertFalse(S.sem_site({"site": "https://www.instagram.com/x"}, "Atacadão", "", cfg), "rede conhecida")


class TesteDePreco(Base):
    def prova(self, cat, nome, l, cfg=None, forcar=False):
        S = self.S
        cfg = cfg or self.config()
        memo, cache_f = S.ler_json(S.LOJAS_SITE, {}) or {}, S.ler_json(S.FOLHETOS, {}) or {}
        st = S.testa_preco_loja(cat, nome, l, memo, "Joinville", cache_f, cfg, [0], forcar)
        return st

    def test_cada_caminho(self):
        S, b = self.S, self.lojas.base
        st = self.prova("mercados", "Super Koch", {"site": b + "/super-koch/"})
        self.assertEqual((st["como"], st["exemplo"], st["site"]), ("site", "Leite Integral Tirol 1L por R$ 4,59", "127.0.0.1:" + str(self.lojas.porta) + "/super-koch"))
        self.assertEqual(st["passos"][0], "✓ Site com busca direta, loja do seu CEP.")
        st = self.prova("farmacias", "Farmácia Vida", {"site": b + "/farmavida/"})
        self.assertEqual((st["como"], st["exemplo"]), ("paginas", "Dipirona Monoidratada 500mg 10 Comprimid por R$ 8,90"), "o nome cortado em 40 letras")
        self.assertIn("✓ Lista de produtos do site: 3 páginas.", st["passos"])
        st = self.prova("mercados", "Mercado Site", {"site": b + "/mercadosite/"})
        self.assertEqual((st["como"], st["exemplo"]), ("busca_site", "Leite Integral Tirol 1L por R$ 4,79"))
        st = self.prova("farmacias", "Farmácia do Zé", {"site": b + "/farmaze/"})
        self.assertEqual((st["como"], st["url"]), ("ofertas_site", b + "/farmaze/"))
        self.assertIn("✓ Achei \"dipirona\": Dipirona 500 mg caixa com 10 comprimidos por R$ 7,49.", st["passos"])
        self.lojas.paginas["/fechado/robots.txt"] = (200, "User-agent: *\nDisallow: /\n", "text/plain")
        st = self.prova("farmacias", "Farmácia Fechada", {"site": b + "/fechado/"}, self.config(usar_ia=False))
        self.assertEqual(st["como"], "nenhum")
        self.assertIn("pede para programas não consultarem os preços", st["passos"][0])
        self.assertEqual(st["passos"][-1], "✗ Sem IA, não há de onde tirar o preço desta loja.")

    def test_sem_site_rede_social_e_folheto(self):
        S, b = self.S, self.lojas.base
        st = self.prova("mercados", "Açougue Boi", {"social": "https://www.facebook.com/boi"})
        self.assertIn("✗ O site desta loja no mapa é o Facebook (www.facebook.com/boi), sem preços para ler.", st["passos"])
        self.assertEqual(st["como"], "ia")
        st = self.prova("mercados", "Mercadinho", {}, self.config(usar_ia=False))
        self.assertEqual(st["passos"][0], "✗ O mapa não traz o site desta loja. Com a chave do Brave em Integrações (ou a IA ligada), o app procura o site.")
        st = self.prova("mercados", "Boi Dourado", {"social": "https://www.instagram.com/boidourado/"})
        self.assertEqual(st["instagram"], "boidourado")
        self.assertIn("Tem Instagram (@boidourado): ligue o Instagram em Mais › Integrações para ler os encartes.", st["passos"])
        # folheto achado nos sites de encartes; depois, já lido e guardado
        self.lojas.paginas["/kimbino/mercadinho/"] = (200, '<a href="/kimbino/mercadinho/ofertas-1234567/">x</a>', "text/html")
        st = self.prova("mercados", "Mercadinho", {})
        self.assertEqual(st["como"], "folheto_novo")
        self.assertEqual(st["passos"][-1], "✓ Tem folheto da semana no Kimbino; a IA lê na próxima busca.")
        S.gravar_json(S.FOLHETOS, {"itens": {"k:1": {"loja": "Mercadinho", "r": {"ofertas": []}, "ate": "2099-01-01"}}})
        self.assertEqual(self.prova("mercados", "Mercadinho", {})["como"], "folheto")
        st = self.prova("mercados", "Sem Nada", {})
        self.assertTrue(st["passos"][1].startswith("✗ Sem folheto no Kimbino, Seus Folhetos, Portafolhetos e Catálogos Ofertas"), st["passos"])

    def test_marketplace(self):
        S, b = self.S, self.lojas.base
        cfg = self.config()
        st = S.testa_marketplace(cfg, "shopee", "Shopee", {})
        self.assertIn("A Shopee tem API de afiliados, que dá preço sem IA: ligue em Mais › Integrações.", st["passos"])
        S.grava_segredos({"shopee": {"app_id": "1", "secret": "s"}})
        self.lojas.rotas["/shopee"] = lambda p: {"data": {"productOfferV2": {"nodes": [{"productName": "Café Pilão 500g", "priceMin": "19.9"}]}}}
        st = S.testa_marketplace(cfg, "shopee", "Shopee", {})
        self.assertEqual((st["como"], st["exemplo"]), ("api", "Café Pilão 500g por R$ 19,90"))
        S.MKT_SITES["mercadolivre"] = b + "/meli"
        self.lojas.paginas["/meli/robots.txt"] = (200, "User-agent: *\nDisallow: /api/\n", "text/plain")
        self.lojas.paginas["/meli/busca"] = (200, LD.format(n="Café Pilão Tradicional 500g", m="Pilão", p="17.90", d="InStock"), "text/html")
        memo = {}
        st = S.testa_marketplace(cfg, "mercadolivre", "Mercado Livre", memo)
        self.assertEqual(st["como"], "busca_site")
        self.assertTrue(memo[b + "/meli"]["marketplace"], "a busca do site entra nas próximas buscas")
        S.MKT_SITES["amazon"] = b + "/amazonfalsa"
        self.lojas.paginas["/amazonfalsa/robots.txt"] = (200, "User-agent: *\nDisallow: /\n", "text/plain")
        st = S.testa_marketplace(self.config(usar_ia=False), "amazon", "Amazon", {})
        self.assertEqual(st["como"], "nenhum")
        self.assertIn("pede para programas não consultarem os preços", st["passos"][0])

    def test_testar_agora_uma_loja(self):
        S, b = self.S, self.lojas.base
        self.config(usar_ia=False)
        self.ofertas({"categorias": [categoria("mercados", [("merc-super-koch", "Super Koch", 1.0, {"site": b + "/super-koch/"})]),
                                     categoria("online", [("onli-amazon", "Amazon", None)])]})
        S.sonda_loja(S.ler_config(), "mercados", "merc-nao-existe")
        self.assertEqual(S.SONDA["resumo"], "Não achei essa loja.")
        S.sonda_loja(S.ler_config(), "mercados", "merc-super-koch")
        self.assertEqual(S.SONDA["resumo"], "Super Koch: achei Leite Integral Tirol 1L por R$ 4,59.")
        self.assertFalse(S.SONDA["rodando"])
        loja = S.ler_json(S.OFERTAS)["categorias"][0]["lojas"][0]
        self.assertEqual(loja["preco_fonte"]["como"], "site", "o resultado vai para a loja")
        S.sonda_loja(S.ler_config(), "online", "mkt:shopee")
        fontes = S.ler_json(S.SONDA_FILE)
        self.assertEqual(fontes["online"]["mkt:shopee"]["como"], "nenhum")
        of = S.ler_json(S.OFERTAS)
        self.assertIn("shopee", next(c for c in of["categorias"] if c["id"] == "online")["fontes_mkt"])

    def test_teste_de_todas_as_lojas(self):
        S, b = self.S, self.lojas.base
        cfg = self.config(usar_ia=False, raio_km=2, lojas={"ignorar": ["farm-ignorada"]})
        self.ofertas({"categorias": [categoria("mercados", [("merc-super-koch", "Super Koch", 1.0, {"site": b + "/super-koch/"}),
                                                            ("merc-longe", "Longe", 9.0)]),
                                     categoria("farmacias", [("farm-farmacia-vida", "Farmácia Vida", 1.0, {"site": b + "/farmavida/"}),
                                                             ("farm-ignorada", "Ignorada", 1.0), ("farm-sem", "Farmácia Sem Site", 1.5)])]})
        self.assertEqual([x[2] for x in S.lojas_acompanhadas(cfg, S.ler_json(S.OFERTAS)["categorias"])], ["Super Koch", "Farmácia Vida", "Farmácia Sem Site"])
        S.sonda_lojas(cfg)
        self.assertEqual(S.SONDA["resumo"], "Testei 3 lojas: 2 com preço direto do site, 1 sem fonte de preço sem IA.")
        self.assertEqual((S.SONDA["atual"], S.SONDA["total"], S.SONDA["rodando"]), (3, 3, False))


class OrdemDosScripts(Base):
    def test_primeiro_o_que_nao_gasta_ia(self):
        S, b = self.S, self.lojas.base
        self.lojas.catalogo["giassi"] = [prod("Leite Integral Tirol 1L", 4.89, "Laticínios/Leites")]
        self.lojas.rotas["/shopee"] = lambda p: {"data": {"productOfferV2": {"nodes": [{"productName": "Leite Integral Tirol 1L Caixa com 12", "priceMin": "59.9",
                                                                                         "ratingStar": "4.9", "productLink": "https://shopee.com.br/leite"}]}}}
        S.grava_segredos({"shopee": {"app_id": "1", "secret": "s"}})
        S.gravar_json(S.LOJAS_SITE, {b + "/farmavida": dict(S.testa_site(b + "/farmavida", "1"), nome="Farmácia Vida", categoria="farmacias", em="2099-01-01T00:00:00+00:00")})
        self.ofertas({"categorias": [categoria("farmacias", [("farm-farmacia-vida", "Farmácia Vida", 1.0)])]})
        cfg = self.config(categorias=["mercados", "farmacias", "online"], lista=[{"produto": "Leite integral"}, {"produto": "Dipirona 500 mg"}])
        res, rel, ja = S.busca_scripts(cfg, cfg["categorias"])
        self.assertEqual(rel["diretas"], ["Angeloni", "Farmácia Vida", "Giassi"])
        self.assertEqual(rel["shopee"], 1)
        self.assertEqual(ja, {"mercados": ["Angeloni", "Giassi"], "farmacias": ["Farmácia Vida"], "online": ["Shopee"]})
        self.assertEqual(self.ha.chamadas_ia, [], "nenhuma chamada de IA")
        self.config(categorias=["mercados"], lista=cfg["lista"], opcoes={"lojas_diretas": False})
        res, rel, ja = S.busca_scripts(S.ler_config(), ["mercados"])
        self.assertNotIn("diretas", rel, "lojas diretas desligado: sem sites")

    def test_uma_fonte_que_quebra_nao_para_as_outras(self):
        S = self.S
        cfg = self.config(categorias=["mercados", "online"], lista=[{"produto": "Leite integral"}])
        S.grava_segredos({"shopee": {"app_id": "1", "secret": "s"}})
        quebra = lambda nome: (lambda *a, **k: (_ for _ in ()).throw(RuntimeError(nome)))  # noqa: E731
        for f in ("busca_direta", "busca_catalogos", "busca_sites", "busca_paginas_ofertas", "busca_shopee", "busca_folhetos", "busca_instagram"):
            setattr(S, f, quebra(f))
        res, rel, ja = S.busca_scripts(cfg, cfg["categorias"])
        self.assertEqual((res, rel, ja), ([], {}, {}))
        for msg in ("busca direta: busca_direta", "páginas de produto: busca_catalogos", "busca do site: busca_sites",
                    "ofertas do site: busca_paginas_ofertas", "shopee: busca_shopee", "folhetos: busca_folhetos", "Instagram: busca_instagram"):
            self.assertTrue(any(msg == str(m) for m in self.log), msg)

    def test_o_que_cada_fonte_achou_vai_no_relatorio(self):
        S = self.S
        cfg = self.config(categorias=["mercados", "farmacias"], lista=[{"produto": "Leite integral"}])
        S.busca_direta = lambda *a, **k: []
        par = lambda cid, nome: (categoria(cid, [(cid[:4] + "-" + S.slug(nome, 30), nome, 1.0)]), {})  # noqa: E731
        S.busca_catalogos = lambda *a, **k: [par("mercados", "Catálogo")]
        S.busca_sites = lambda *a, **k: [par("mercados", "Busca")]
        S.busca_paginas_ofertas = lambda cfg, cats, ja, itens: [par("farmacias", "Página")] if ja == {"mercados": ["Busca", "Catálogo"]} else []
        S.busca_instagram = lambda *a, **k: [par("mercados", "Boi")]
        res, rel, ja = S.busca_scripts(cfg, cfg["categorias"])
        self.assertEqual(len(res), 4)
        self.assertEqual(rel["diretas"], ["Busca", "Catálogo", "Página"])
        self.assertEqual(rel["instagram"], ["Boi"])
        self.assertEqual(ja, {"mercados": ["Busca", "Catálogo"], "farmacias": ["Página"]}, "a página de ofertas sabe quem já tem preço")
