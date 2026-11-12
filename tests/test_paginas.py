"""Preços sem IA nas páginas das lojas, os casos que faltavam: dados embutidos em <script> (nome e preço vizinhos, preço
antes do nome, centavos da VTEX), cartões de texto (nome em duas linhas), página de produto (Product dentro de @graph,
AggregateOffer, lowPrice, sem dados: o título e os dados da página), sitemap (.gz quebrado, índice sem produtos),
preço da página do produto (nome pelo endereço, erro), busca do site (o núcleo do item, o nome corrigido) e as lojas
com página de ofertas na busca."""
import json
import types

from apoio import NOMES_VOCAB, Cenario, categoria

LD = '<script type="application/ld+json">{}</script>'


class DadosEmbutidos(Cenario):
    def test_nome_e_preco_depois(self):
        h = ('<script>window.__DADOS__ = {"produtos":[{"name":"Dipirona S\\u00f3dica 500 mg 10 comprimidos","price":7.49},'
             '{"name":"Protetor Solar Nivea FPS 50","preco":"39,90"}]}</script>')
        self.assertEqual(self.S.ofertas_json_embutido(h), [{"produto": "Dipirona Sódica 500 mg 10 comprimidos", "preco": 7.49},
                                                           {"produto": "Protetor Solar Nivea FPS 50", "preco": 39.9}])

    def test_preco_antes_do_nome(self):
        h = '<script>var x = [{"price": 12.5, "name": "Shampoo Seda Ceramidas 325ml"}, {"price": 9.9, "name": "Condicionador Seda Ceramidas 325ml"}];</script>'
        self.assertEqual(self.S.ofertas_json_embutido(h), [{"produto": "Shampoo Seda Ceramidas 325ml", "preco": 12.5},
                                                           {"produto": "Condicionador Seda Ceramidas 325ml", "preco": 9.9}])

    def test_centavos_da_vtex_e_preco_fora_do_razoavel(self):
        h = '<script>{"productName":"Leite Integral Tirol 1L","sellingPrice":489,"bestPrice":479} {"productName":"Geladeira Frost Free 400L","price":50000}</script>'
        self.assertEqual(self.S.ofertas_json_embutido(h), [{"produto": "Leite Integral Tirol 1L", "preco": 4.79}])

    def test_scripts_curtos_e_dados_estruturados_ficam_de_fora(self):
        h = '<script>"a"</script><script type="application/ld+json">{"name":"Produto do schema org","price":5}</script><script>var semAspas = 1;</script>'
        self.assertEqual(self.S.ofertas_json_embutido(h), [])

    def test_nome_com_escape_quebrado_e_script_sem_nome(self):
        h = ('<script>var a = {"descricao": "x", "codigo": "12345678901234567890", "outro": "texto qualquer aqui"};</script>'
             '<script>{"name":"Sabonete Dove \\q Original 90g","price":4.5}</script>')
        self.assertEqual(self.S.ofertas_json_embutido(h), [{"produto": "Sabonete Dove \\q Original 90g", "preco": 4.5}],
                         "o escape que o JSON não aceita fica como veio; o script sem nome de produto é pulado")

    def test_vira_oferta_da_pagina_quando_nao_tem_schema_org(self):
        h = '<script>{"name":"Ração Golden Gatos Castrados 10kg","price":159.9}</script><p>R$ 1,00</p>'
        self.assertEqual(self.S.ofertas_da_pagina(h), [{"produto": "Ração Golden Gatos Castrados 10kg", "preco": 159.9, "preco_normal": None}])


class Texto(Cenario):
    def test_nome_em_duas_linhas(self):
        h = "<div><h3>Dipirona 500 mg</h3><p>caixa com 10 comprimidos</p><b>R$ 7,49</b></div>"
        self.assertEqual(self.S.ofertas_texto(h), [{"produto": "Dipirona 500 mg caixa com 10 comprimidos", "preco": 7.49, "preco_normal": None}])

    def test_nome_e_preco_no_mesmo_bloco_e_de_por(self):
        h = "<li>Arroz Tio João Tipo 1 5 kg R$ 24,90</li><li>Feijão Carioca Camil 1 kg</li><li>De R$ 9,90</li><li>Por R$ 7,90</li>"
        self.assertEqual(self.S.ofertas_texto(h), [{"produto": "Arroz Tio João Tipo 1 5 kg", "preco": 24.9, "preco_normal": None},
                                                   {"produto": "Feijão Carioca Camil 1 kg", "preco": 7.9, "preco_normal": 9.9}])

    def test_preco_separado_em_partes(self):
        h = "<div><h3>Fralda Pampers Confort Sec G</h3><span>R$</span><span>79</span><span>,90</span></div>"
        self.assertEqual(self.S.ofertas_texto(h)[0]["preco"], 79.9)

    def test_json_ld_quebrado_nao_derruba(self):
        h = LD.format("{quebrado") + "<div><h3>Café Pilão Tradicional 500g</h3><b>R$ 17,90</b></div>"
        self.assertEqual([o["produto"] for o in self.S.ofertas_da_pagina(h)], ["Café Pilão Tradicional 500g"])

    def test_nome_que_nao_parece_produto(self):
        S = self.S
        self.assertFalse(S.parece_nome("Frete grátis"))
        self.assertFalse(S.parece_nome("12345 67890"))
        self.assertFalse(S.parece_nome("R$ 10,00 Arroz"))
        self.assertTrue(S.parece_nome("Arroz Tio João 5 kg"))


class PaginaDoProduto(Cenario):
    def test_product_no_graph_com_marca(self):
        d = {"@graph": [{"@type": "BreadcrumbList"}, {"@type": "Product", "name": "Leite Tirol 1L", "brand": {"name": "Tirol"},
                                                       "offers": [{"price": "5.29", "availability": "InStock"}, {"price": "4.99"}]}]}
        self.assertEqual(self.S.preco_da_pagina(LD.format(json.dumps(d))), {"nome": "Leite Tirol 1L", "marca": "Tirol", "preco": 4.99, "disponivel": True})

    def test_aggregate_offer_e_low_price(self):
        S = self.S
        agg = {"@type": "Product", "name": "Ração", "offers": {"@type": "AggregateOffer", "offers": [{"price": 99, "availability": "OutOfStock"}, {"price": 109}]}}
        self.assertEqual(S.preco_da_pagina(LD.format(json.dumps(agg)))["preco"], 109)
        low = {"@type": "Product", "name": "Ração", "offers": {"@type": "AggregateOffer", "lowPrice": "89,90"}}
        self.assertEqual(S.preco_da_pagina(LD.format(json.dumps(low)))["preco"], 89.9)
        fora = {"@type": "Product", "name": "Ração", "offers": {"lowPrice": 89.9, "availability": "https://schema.org/OutOfStock", "price": None}}
        self.assertIsNone(S.produto_ld(fora))
        self.assertIsNone(S.produto_ld({"@type": "Offer"}))

    def test_bloco_quebrado_e_lista_de_dados(self):
        h = LD.format("{x") + LD.format(json.dumps([{"@type": "Product", "name": "Café", "offers": {"price": 17}}]))
        self.assertEqual(self.S.preco_da_pagina(h)["preco"], 17)

    def test_sem_dados_pelo_titulo_e_os_dados_da_pagina(self):
        S = self.S
        h = ('<meta property="og:title" content="Ração Golden Gatos Castrados 10kg"><script>{"name":"Ração Golden Gatos Castrados 10kg","price":159.9}'
             '{"name":"Areia Pipicat Floral 4kg","price":21.5}</script>')
        self.assertEqual(S.preco_da_pagina(h), {"nome": "Ração Golden Gatos Castrados 10kg", "marca": None, "preco": 159.9, "disponivel": True})
        self.assertIsNone(S.preco_da_pagina(h + "<p>Produto esgotado</p>"), "esgotado não conta")
        self.assertIsNone(S.preco_da_pagina("<p>sem título nem preço</p>"))
        self.assertIsNone(S.preco_da_pagina("<title>Outra coisa completamente diferente</title><script>" + '{"name":"Areia Pipicat Floral 4kg","price":21.5}' * 2 + "</script>"))

    def test_meta_tag_indisponivel(self):
        r = self.S.preco_da_pagina('<h1>Fralda <b>G</b></h1><meta name="product:price:amount" content="79.9"><meta property="og:availability" content="Esgotado">')
        self.assertEqual((r["nome"], r["disponivel"]), ("Fralda G", False))

    def test_nota_de_pagina_de_produto(self):
        S = self.S
        self.assertGreater(S.parece_produto("https://x.com/dipirona-500mg-10-comprimidos/p"), S.parece_produto("https://x.com/categoria/medicamentos"))
        self.assertEqual(S.parece_produto("https://x.com/institucional/sobre"), -5)
        self.assertEqual(S.texto_url("https://x.com/leite-integral_tirol-1l/p"), "leite integral tirol 1l")


class Sitemap(Cenario):
    def setUp(self):
        super().setUp()
        self.S.time = types.SimpleNamespace(time=self.S.time.time, sleep=lambda s: None)
        self.o = self.lojas.base + "/mk"

    def test_gz_quebrado_e_sitemap_que_nao_abre(self):
        lj, b = self.lojas, self.lojas.base
        lj.paginas["/mk/a.xml.gz"] = (200, b"\x1f\x8bnao e gzip", "application/gzip")
        lj.paginas["/mk/c.xml"] = (200, f"<urlset><url><loc>{b}/mk/cafe-pilao-500g/p</loc></url></urlset>", "application/xml")
        c = self.S.baixa_catalogo(self.o, {"sitemaps": [b + "/mk/a.xml.gz", b + "/mk/nao-existe.xml", b + "/mk/c.xml"]})
        self.assertEqual(c["urls"], [b + "/mk/cafe-pilao-500g/p"])

    def test_indice_sem_sitemap_de_produto(self):
        lj, b = self.lojas, self.lojas.base
        lj.paginas["/mk/sitemap.xml"] = (200, f"<sitemapindex><sitemap><loc>{b}/mk/sitemap-blog.xml</loc></sitemap><sitemap><loc>{b}/mk/sitemap-1.xml</loc></sitemap>"
                                                "</sitemapindex>", "application/xml")
        lj.paginas["/mk/sitemap-1.xml"] = (200, f"<urlset><url><loc>{b}/mk/leite-tirol-1l</loc></url></urlset>", "application/xml")
        lj.paginas["/mk/sitemap-blog.xml"] = (200, f"<urlset><url><loc>{b}/mk/receita-de-bolo</loc></url></urlset>", "application/xml")
        c = self.S.baixa_catalogo(self.o, {})
        self.assertEqual(c["urls"], [b + "/mk/leite-tirol-1l"], "o blog fica de fora")
        self.assertFalse(lj.pedidos_de("sitemap-blog"))

    def test_sitemap_de_categoria_so_os_produtos(self):
        lj, b = self.lojas, self.lojas.base
        lj.paginas["/mk/sitemap-categorias.xml"] = (200, f"<urlset><url><loc>{b}/mk/leites</loc></url><url><loc>{b}/mk/leite-tirol/p</loc></url></urlset>", "text/xml")
        c = self.S.baixa_catalogo(self.o, {"sitemaps": [b + "/mk/sitemap-categorias.xml"]})
        self.assertEqual(c["urls"], [b + "/mk/leite-tirol/p"])

    def test_preco_do_produto_sem_nome_e_com_erro(self):
        S, lj, b = self.S, self.lojas, self.lojas.base
        lj.paginas["/mk/leite-integral-tirol-1l/p"] = (200, '<meta property="product:price:amount" content="4.99">', "text/html")
        cat = {}
        r = S.preco_produto(self.o, cat, b + "/mk/leite-integral-tirol-1l/p")
        self.assertEqual((r["nome"], r["preco"]), ("Leite integral tirol 1l", 4.99), "sem título: o nome sai do endereço")
        self.assertIsNone(S.preco_produto(self.o, cat, b + "/mk/nao-existe/p"))
        self.assertIsNone(cat["precos"][b + "/mk/nao-existe/p"]["r"], "o erro também fica guardado por um dia")
        self.assertTrue(any("página de produto" in str(m) for m in self.log))

    def test_busca_pelos_catalogos_erros_e_categorias(self):
        S, b = self.S, self.lojas.base
        memo = {self.o: {"nome": "Loja Boa", "paginas": True}, b + "/vazia": {"nome": "Loja Vazia", "paginas": True}, b + "/erro": {"nome": "Loja Erro", "paginas": True}}
        S.gravar_json(S.LOJAS_SITE, memo)
        cfg = self.config(lista=[{"produto": "Café Pilão 500 g"}])
        orig = S.baixa_catalogo

        def baixa(o, m):
            if o.endswith("/erro"):
                raise RuntimeError("caiu")
            if o.endswith("/vazia"):
                return {"urls": []}
            return {"urls": [b + "/mk/cafe-pilao-tradicional-500g/p"], "precos": {}}
        S.baixa_catalogo = baixa
        self.lojas.paginas["/mk/cafe-pilao-tradicional-500g/p"] = (200, LD.format(json.dumps({"@type": "Product", "name": "Café Pilão Tradicional 500g",
                                                                                               "brand": "Pilão", "offers": {"price": 17.9}})), "text/html")
        res = S.busca_catalogos(cfg)
        self.assertEqual([c["id"] for c, _ in res], ["online"], "loja fora do raio: online")
        self.assertTrue(any("lista de produtos de Loja Erro: caiu" in str(m) for m in self.log))
        self.assertEqual(S.busca_catalogos(cfg, cats=["mercados"]), [])
        S.baixa_catalogo = orig


class BuscaDoSite(Cenario):
    def setUp(self):
        super().setUp()
        self.S.time = types.SimpleNamespace(time=self.S.time.time, sleep=lambda s: None)
        self.o = self.lojas.base + "/s"

    def test_tenta_o_nucleo_do_item(self):
        S, lj = self.S, self.lojas
        lj.paginas["/s/busca?q=%C3%81lcool%20perfumado"] = (200, "<p>Nenhum produto</p>", "text/html")
        lj.paginas["/s/busca?q=%C3%81lcool"] = (200, LD.format(json.dumps({"@type": "Product", "name": "Álcool Líquido Lavanda 1L", "offers": {"price": 9.9}})), "text/html")
        ofs = S.busca_do_site(self.o, {"regras": [], "busca": "/busca?q={}"}, "Álcool perfumado")
        self.assertEqual([o["produto"] for o in ofs], ["Álcool Líquido Lavanda 1L"], "a fragrância vale como perfumado")

    def test_nucleo_que_falha(self):
        S = self.S
        S.pagina_txt = lambda u: "<p>nada</p>" if "perfumado" in u else (_ for _ in ()).throw(OSError("caiu"))
        self.assertEqual(S.busca_do_site(self.o, {"regras": [], "busca": "/busca?q={}"}, "Álcool perfumado"), [])

    def test_nome_corrigido_na_busca_do_site(self):
        S, lj = self.S, self.lojas
        S.aprende_nomes(NOMES_VOCAB)
        S.grava_vocab()
        lj.paginas["/s/busca"] = (200, LD.format(json.dumps({"@type": "Product", "name": "Detergente Líquido Neutro Ypê 500ml", "offers": {"price": 2.39}})), "text/html")
        S.gravar_json(S.LOJAS_SITE, {self.o: {"nome": "Mercado S", "regras": [], "busca": "/busca?q={}"}})
        cat, parcial = S.busca_sites(self.config(lista=[{"produto": "Detergemte Ypê"}]))[0]
        self.assertEqual(S.valor_total(parcial["Detergemte Ypê"]["precos"]["onli-mercado-s"]), 2.39)
        self.assertIn("Detergente%20Yp%C3%AA", parcial["Detergemte Ypê"]["links"]["onli-mercado-s"], "o link é da busca corrigida")

    def test_erro_na_busca_do_site_para_a_loja(self):
        S = self.S
        S.gravar_json(S.LOJAS_SITE, {self.o: {"nome": "Mercado S", "busca": "/busca?q={}"}})
        S.busca_do_site = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("quebrou"))
        self.assertEqual(S.busca_sites(self.config(lista=[{"produto": "Leite"}, {"produto": "Café"}])), [])
        self.assertTrue(any("busca do site de Mercado S: quebrou" in str(m) for m in self.log))


class PaginasDeOfertas(Cenario):
    def test_limites_erros_e_vazias(self):
        S, b = self.S, self.lojas.base
        self.lojas.paginas["/vazia/"] = (200, "<p>em breve</p>", "text/html")
        fontes = {"farmacias": {f"loja {i}": {"como": "ofertas_site", "url": f"{b}/vazia/", "nome": f"Loja {i}"} for i in range(10)}}
        fontes["farmacias"]["quebrada"] = {"como": "ofertas_site", "url": "não é url"}
        S.gravar_json(S.SONDA_FILE, fontes)
        cfg = self.config(lista=[{"produto": "Dipirona"}])
        self.assertEqual(S.busca_paginas_ofertas(cfg, ["farmacias"], {}), [])
        self.assertEqual(len(self.lojas.pedidos_de("/vazia/")), 1, "a página é lida uma vez e guardada; no máximo 8 lojas")
        S.ofertas_do_site = lambda *a: (_ for _ in ()).throw(RuntimeError("caiu"))
        S.busca_paginas_ofertas(cfg, ["farmacias"], {})
        self.assertTrue(any("ofertas do site de Loja 0: caiu" in str(m) for m in self.log))
        self.assertEqual(S.busca_paginas_ofertas(cfg, ["mercados"], {}), [], "outra categoria")

    def test_validade_na_pagina_e_robots(self):
        S, b = self.S, self.lojas.base
        self.lojas.paginas["/promo/"] = (200, "<p>Ofertas válidas até 30/12/2099</p><div><h3>Arroz Tio João 5 kg</h3><b>R$ 24,90</b></div>", "text/html")
        ofs, links = S.le_pagina_ofertas(b + "/promo/", [])
        self.assertEqual([o["produto"] for o in ofs], ["Arroz Tio João 5 kg"], "ainda vale")
        self.assertIsNone(S.le_pagina_ofertas(b + "/promo/?x=1", S.robots_regras("User-agent: *\nDisallow: /promo/?x\n")))
        self.ofertas({"categorias": [categoria("farmacias", [("farm-a", "A", 1.0)])]})


class LinkDoProduto(Cenario):
    """1.36.3: o link de cada produto da página (o Abrir na loja vai direto nele, não na página de ofertas)."""

    def test_json_ld_dados_embutidos_e_vtex(self):
        S = self.S
        base = "https://www.loja.exemplo/ofertas/"
        ld = LD.format(json.dumps({"@type": "Product", "name": "Shampoo Seda Ceramidas 325 ml", "url": "/shampoo-seda-ceramidas-325ml/p",
                                   "offers": {"price": "12.90", "availability": "InStock"}}))
        self.assertEqual(S.ofertas_da_pagina(ld, base)[0]["link"], "https://www.loja.exemplo/shampoo-seda-ceramidas-325ml/p")
        h = ('<script>window.__D__ = {"itens":[{"name":"Dipirona Sódica 500 mg 10 comprimidos","price":7.49,"url":"\\/dipirona-500\\/p"},'
             '{"name":"Protetor Solar Nivea FPS 50","price":39.9,"url":"https:\\/\\/outro.exemplo\\/protetor"},'
             '{"productName":"Leite Integral Tirol 1L","sellingPrice":479,"linkText":"leite-integral-tirol-1l"},'
             '{"name":"Fralda Pampers Confort Sec G","price":79.9,"url":"fralda-pampers"}]}</script>')
        ofs = {o["produto"]: o.get("link") for o in S.ofertas_da_pagina(h, base)}
        self.assertEqual(ofs, {"Dipirona Sódica 500 mg 10 comprimidos": "https://www.loja.exemplo/dipirona-500/p",
                               "Protetor Solar Nivea FPS 50": None,  # de outro site
                               "Leite Integral Tirol 1L": "https://www.loja.exemplo/leite-integral-tirol-1l/p",  # VTEX
                               "Fralda Pampers Confort Sec G": None})  # um nome solto, fora do linkText
        self.assertNotIn("link", S.ofertas_da_pagina(h)[0], "sem o endereço da página, sem link")

    def test_link_do_produto(self):
        S = self.S
        b = "https://loja.exemplo/ofertas"
        self.assertEqual(S.link_do_produto("https://www.loja.exemplo/cafe/p", b), "https://www.loja.exemplo/cafe/p", "com ou sem www")
        for ruim in (None, "/", "/ofertas/", "mailto:a@b.c", "https://outra.exemplo/cafe"):
            self.assertIsNone(S.link_do_produto(ruim, b), ruim)
        self.assertIsNone(S.link_do_produto("/cafe", None))
        self.assertIsNone(S.link_do_produto("http://[::1", b), "endereço quebrado")

    def test_a_oferta_e_o_preco_da_lista_abrem_o_produto(self):
        S, b = self.S, self.lojas.base
        self.lojas.paginas["/promo/"] = (200, '<script>{"name":"Arroz Tio João Tipo 1 5 kg","price":24.9,"url":"/arroz-tio-joao-5kg/p"}'
                                              ' {"name":"Feijão Carioca Camil 1 kg","price":7.9}</script>', "text/html")
        S.gravar_json(S.SONDA_FILE, {"mercados": {"loja": {"como": "ofertas_site", "url": b + "/promo/", "nome": "Mercado P"}}})
        cfg = self.config(lista=[{"produto": "Arroz 5 kg"}])
        [(cat, parcial)] = S.busca_paginas_ofertas(cfg, ["mercados"], {})
        fontes = {o["produto"]: o.get("fonte") for o in cat["ofertas"]}
        self.assertEqual(fontes["Arroz Tio João Tipo 1 5 kg"], b + "/arroz-tio-joao-5kg/p")
        self.assertEqual(fontes["Feijão Carioca Camil 1 kg"], b + "/promo/", "sem o link do produto: a página de ofertas")
        self.assertEqual(parcial["Arroz 5 kg"]["links"], {"merc-mercado-p": b + "/arroz-tio-joao-5kg/p"}, "o preço do item da lista também")

    def test_buscas_dos_sites(self):
        S = self.S
        S.gravar_json(S.LOJAS_SITE, {"https://www.panvel.com": {"nome": "Panvel Farmácias", "busca": "/busca?q={}"},
                                     "https://www.giassi.com.br": {"nome": "Giassi", "vtex": True},
                                     "não é url": {"nome": "X", "busca": "/b?q={}"},
                                     "https://sem.exemplo": {"nome": "Sem", "busca": "/b"}})
        self.assertEqual(S.buscas_dos_sites(), {S.chave_loja("Panvel Farmácias"): "https://www.panvel.com/busca?q={}"})
