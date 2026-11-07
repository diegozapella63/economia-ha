"""O teste de preço de cada loja (Encontrar lojas e Testar agora), passo a passo: site VTEX que não diz a loja do CEP ou não
tem o item, busca do site e sitemap que falham, outro produto do sitemap, página de ofertas proibida, sem o item ou sem
preços no texto, Instagram (lido, erro, post novo, nenhum), folheto (de novo no Testar agora, erro), marketplaces (Shopee
com erro ou vazia, busca do site), os erros que não podem parar o teste e o resultado posto em cada loja (marca_fontes)."""
import json
import types
from datetime import datetime, timedelta, timezone

from apoio import Cenario, categoria, prod

LD = '<script type="application/ld+json">{}</script>'


class Base(Cenario):
    def setUp(self):
        super().setUp()
        self.S.time = types.SimpleNamespace(time=self.S.time.time, sleep=lambda s: None)
        self.b = self.lojas.base

    def prova(self, nome, l, cat="farmacias", cfg=None, forcar=False, cache_f=None):
        cfg = cfg or self.config()
        return self.S.testa_preco_loja(cat, nome, l, {}, "Joinville", cache_f if cache_f is not None else {}, cfg, [0], forcar)

    def sem_api(self, pasta):
        self.lojas.paginas[f"/{pasta}/robots.txt"] = (200, "User-agent: *\nDisallow: /api/\n", "text/plain")


class SiteVtex(Base):
    def test_nao_diz_a_loja_do_cep(self):
        S = self.S
        self.lojas.vtex.add("vtexa")
        S.regiao_direta = lambda k, cep: (_ for _ in ()).throw(OSError("tempo esgotado"))
        st = self.prova("Vtex A", {"site": self.b + "/vtexa/"}, cat="mercados")
        self.assertEqual(st["passos"][0], "✗ O site 127.0.0.1:%d/vtexa não disse qual loja atende o seu CEP (tempo esgotado)." % self.lojas.porta)

    def test_nao_entrega_no_cep(self):
        self.lojas.vtex.add("vtex-b")
        st = self.prova("Vtex B", {"site": self.b + "/vtex-b/"}, cat="mercados")
        self.assertEqual(st["passos"][0], "✗ O site 127.0.0.1:%d/vtex-b não entrega no seu CEP." % self.lojas.porta)
        self.assertIn("não entrega no seu CEP", st["passos"][0])

    def test_sem_o_item_de_exemplo_e_busca_que_falha(self):
        S = self.S
        self.lojas.regioes["vtex-c"] = "c1"
        self.lojas.catalogo["vtex-c"] = [prod("Pão de Forma 500g", 8.9)]
        st = self.prova("Vtex C", {"site": self.b + "/vtex-c/"}, cat="mercados")
        self.assertEqual(st["passos"][1], '✗ A busca do site não trouxe "leite" com estoque.')
        S.busca_vtex = lambda *a, **k: (_ for _ in ()).throw(ValueError("json"))
        st = self.prova("Vtex C", {"site": self.b + "/vtex-c/"}, cat="mercados")
        self.assertEqual(st["passos"][1], '✗ A busca do site não trouxe "leite" com estoque.')

    def test_site_achado_pela_ia_fica_no_resultado(self):
        st = self.prova("Loja IA", {"_site_ia": self.b + "/semnada/"}, cfg=self.config(usar_ia=False))
        self.assertEqual(st["site_url"], self.b + "/semnada/")


class SitemapEPaginas(Base):
    def test_busca_do_site_que_falha_e_sitemap_que_falha(self):
        S = self.S
        self.sem_api("loja1")
        S.busca_do_site = lambda *a, **k: (_ for _ in ()).throw(OSError("x"))
        S.baixa_catalogo = lambda o, m: (_ for _ in ()).throw(OSError("y"))
        st = self.prova("Loja 1", {"site": self.b + "/loja1/"})
        self.assertIn("✗ Não achei uma busca do site que mostre os preços para programas.", st["passos"])
        self.assertIn("✗ O site 127.0.0.1:%d/loja1 não publica a lista de produtos (sitemap)." % self.lojas.porta, st["passos"])

    def test_outro_produto_do_sitemap(self):
        lj, b = self.lojas, self.b
        self.sem_api("loja2")
        lj.paginas["/loja2/sitemap.xml"] = (200, f"<urlset><url><loc>{b}/loja2/protetor-solar-nivea-fps-50-200ml/p</loc></url>"
                                                 f"<url><loc>{b}/loja2/institucional/sobre</loc></url></urlset>", "application/xml")
        lj.paginas["/loja2/protetor-solar-nivea-fps-50-200ml/p"] = (200, LD.format(json.dumps({"@type": "Product", "name": "Protetor Nivea FPS 50", "offers": {"price": 59.9}})), "text/html")
        st = self.prova("Loja 2", {"site": b + "/loja2/"})
        self.assertIn('Não achei "dipirona" no site; testei outro produto.', st["passos"])
        self.assertEqual((st["como"], st["exemplo"]), ("paginas", "Protetor Nivea FPS 50 por R$ 59,90"))

    def test_nenhuma_pagina_de_produto_com_preco(self):
        lj, b = self.lojas, self.b
        self.sem_api("loja3")
        lj.paginas["/loja3/sitemap.xml"] = (200, f"<urlset><url><loc>{b}/loja3/dipirona-500mg/p</loc></url></urlset>", "application/xml")
        lj.paginas["/loja3/dipirona-500mg/p"] = (200, "<p>sem preço</p>", "text/html")
        lj.paginas["/loja3/"] = (200, "<p>Bem-vindo à Loja 3</p>", "text/html")
        st = self.prova("Loja 3", {"site": b + "/loja3/"}, cfg=self.config(usar_ia=False))
        self.assertIn("✗ Não consegui ler o preço nas páginas de produto do site.", st["passos"])
        self.assertIn("✗ Não achei preços no texto da página 127.0.0.1:%d/loja3/ (o site monta os preços no navegador)." % self.lojas.porta, st["passos"])
        self.assertEqual(st["como"], "nenhum")

    def test_pagina_de_ofertas_proibida(self):
        self.lojas.paginas["/loja4/robots.txt"] = (200, "User-agent: *\nDisallow: /api/\nDisallow: /loja4/ofertas\n", "text/plain")
        st = self.prova("Loja 4", {"site": self.b + "/loja4/ofertas"})
        self.assertIn("✗ O site pede para programas não lerem essa página.", st["passos"])

    def test_ofertas_sem_o_item_de_exemplo(self):
        self.sem_api("loja5")
        self.lojas.paginas["/loja5/"] = (200, "<div><h3>Protetor Solar Nivea FPS 50</h3><b>R$ 39,90</b></div>", "text/html")
        st = self.prova("Loja 5", {"site": self.b + "/loja5/"})
        self.assertEqual(st["como"], "ofertas_site")
        self.assertIn('Não tem "dipirona" nas ofertas de hoje. A cada busca, os itens da sua lista são procurados nelas.', st["passos"])

    def test_pagina_que_nao_abre(self):
        S = self.S
        self.sem_api("loja6")
        S.ofertas_do_site = lambda *a: (_ for _ in ()).throw(OSError("conexão recusada"))
        st = self.prova("Loja 6", {"site": self.b + "/loja6/"})
        self.assertIn("✗ Não consegui abrir a página do site (conexão recusada).", st["passos"])


class Instagram(Base):
    def setUp(self):
        super().setUp()
        self.S.grava_segredos({"instagram": {"token": "t", "ig_id": "99"}})
        self.posts = []
        self.lojas.rotas["/graph/99"] = lambda p: {"business_discovery": {"media": {"data": self.posts}}}

    def quando(self, d):
        return (datetime.now(timezone.utc) - timedelta(days=d)).strftime("%Y-%m-%dT10:00:00+0000")

    def test_ja_lido(self):
        S = self.S
        S.gravar_json(S.INSTAGRAM, {"lidos": {"1": {"handle": "boi", "r": {"ofertas": [1]}, "ate": "2099-01-10"}}})
        st = self.prova("Boi", {"social": "https://www.instagram.com/boi/"}, cat="mercados")
        self.assertEqual(st["como"], "instagram")
        self.assertIn("✓ Encarte do Instagram (@boi) já lido, guardado até 10/01.", st["passos"])

    def test_post_novo_e_nenhum(self):
        self.posts = [{"id": "1", "media_type": "IMAGE", "caption": "Ofertas da semana", "media_url": self.b + "/x.jpg", "timestamp": self.quando(1)}]
        st = self.prova("Boi", {"social": "https://www.instagram.com/boi/"}, cat="mercados")
        self.assertEqual(st["como"], "instagram_novo")
        self.assertTrue(st["passos"][-1].endswith("; a IA lê na próxima busca."))
        self.posts = []
        st = self.prova("Boi", {"social": "https://www.instagram.com/boi/"}, cat="mercados", forcar=True)
        self.assertIn("✗ Instagram @boi: nenhum post de oferta nos últimos 8 dias.", st["passos"])

    def test_erro_do_instagram(self):
        self.lojas.rotas["/graph/99"] = lambda p: (400, {"error": {"code": 190}})
        st = self.prova("Boi", {"social": "https://www.instagram.com/boi/"}, cat="mercados")
        self.assertIn("✗ Instagram @boi: A chave do Instagram venceu ou foi cancelada. Gere outra e cole em Mais › Integrações..", st["passos"])

    def test_instagram_cadastrado_a_mao(self):
        self.posts = [{"id": "1", "media_type": "IMAGE", "caption": "Promoção", "media_url": self.b + "/x.jpg", "timestamp": self.quando(1)}]
        cfg = self.config(usar_ia=False, lojas={"adicionar": [{"nome": "Açougue Boi", "categoria": "mercados", "site": "https://www.instagram.com/boi/"}]})
        st = self.prova("Açougue Boi", {}, cat="mercados", cfg=cfg)
        self.assertEqual((st["instagram"], st["como"]), ("boi", "instagram_novo"))
        self.assertTrue(st["passos"][-1].endswith("; ler o post precisa da IA."))

    def test_post_novo_com_folhetos_desligados(self):
        """Folhetos desligados em Mais › Opções: a busca não lê o Instagram, então o passo não diz que a IA vai ler."""
        self.posts = [{"id": "1", "media_type": "IMAGE", "caption": "Ofertas da semana", "media_url": self.b + "/x.jpg", "timestamp": self.quando(1)}]
        st = self.prova("Boi", {"social": "https://www.instagram.com/boi/"}, cat="mercados", cfg=self.config(opcoes={"folhetos": False}))
        self.assertEqual(st["como"], "instagram_novo")
        self.assertTrue(st["passos"][-1].endswith("; Folhetos desligados em Mais › Opções."), st["passos"])
        self.assertEqual(self.S.busca_instagram(self.config(opcoes={"folhetos": False}), ["mercados"], {}), [], "e a busca não lê mesmo")


class Folhetos(Base):
    def test_testar_agora_procura_de_novo(self):
        cache = {"_lojas": {"kimbino:mercadinho": {"url": None, "em": datetime.now(timezone.utc).isoformat(), "motivo": None}}}
        self.lojas.paginas["/kimbino/mercadinho/"] = (200, '<a href="/kimbino/mercadinho/ofertas-1234567/">x</a>', "text/html")
        st = self.prova("Mercadinho", {}, cat="mercados", cache_f=cache)
        self.assertNotEqual(st["como"], "folheto_novo", "\"não tem\" guardado: não procura de novo")
        st = self.prova("Mercadinho", {}, cat="mercados", cache_f=cache, forcar=True)
        self.assertEqual(st["como"], "folheto_novo", "Testar agora esquece o \"não tem\"")
        self.assertTrue(st["passos"][-1].endswith("; a IA lê na próxima busca."), st["passos"])

    def test_folheto_novo_com_folhetos_desligados(self):
        """Só diz que a IA lê na próxima busca quando a busca vai ler: com Folhetos desligados, diz onde ligar."""
        self.lojas.paginas["/kimbino/mercadinho/"] = (200, '<a href="/kimbino/mercadinho/ofertas-1234567/">x</a>', "text/html")
        cfg = self.config(opcoes={"folhetos": False})
        st = self.prova("Mercadinho", {}, cat="mercados", cfg=cfg)
        self.assertEqual(st["como"], "folheto_novo")
        self.assertEqual(st["passos"][-1], "✓ Tem folheto da semana no Kimbino; Folhetos desligados em Mais › Opções.")
        self.assertEqual(self.S.busca_folhetos(cfg, [{"nome": "Mercadinho", "categoria": "mercados"}]), ([], {}), "e a busca não lê mesmo")
        st = self.prova("Mercadinho", {}, cat="mercados", cfg=self.config(usar_ia=False), forcar=True)
        self.assertEqual(st["passos"][-1], "✓ Tem folheto da semana no Kimbino; ler o folheto precisa da IA.")

    def test_erro_ao_procurar_folheto(self):
        S = self.S
        S.achar_folhetos = lambda loja, cache: (_ for _ in ()).throw(RuntimeError("caiu"))
        st = self.prova("Mercadinho", {}, cat="mercados", cfg=self.config(usar_ia=False))
        self.assertTrue(st["passos"][1].startswith("✗ Sem folheto no Kimbino"))


class Marketplace(Base):
    def test_shopee_com_erro_e_vazia(self):
        S = self.S
        S.grava_segredos({"shopee": {"app_id": "1", "secret": "s"}})
        S.MKT_SITES["shopee"] = self.b + "/shopee-site"
        self.sem_api("shopee-site")
        self.lojas.rotas["/shopee"] = lambda p: {"errors": [{"extensions": {"code": 10030}}]}
        st = S.testa_marketplace(self.config(usar_ia=False), "shopee", "Shopee", {})
        self.assertEqual(st["passos"][0], "✗ API de afiliados da Shopee: " + S.SHOPEE_ERROS[10030])
        self.lojas.rotas["/shopee"] = lambda p: {"data": {"productOfferV2": {"nodes": [{"productName": "x"}]}}}
        st = S.testa_marketplace(self.config(), "shopee", "Shopee", {})
        self.assertEqual(st["passos"][0], "✗ A API de afiliados da Shopee não trouxe produtos no teste.")
        self.assertEqual(st["como"], "ia")

    def test_busca_do_site_do_marketplace(self):
        S = self.S
        S.MKT_SITES["magalu"] = self.b + "/magalu"
        self.sem_api("magalu")
        st = S.testa_marketplace(self.config(), "magalu", "Magalu", {})
        self.assertIn("✗ A busca do site 127.0.0.1:%d/magalu não mostra os preços para programas (ou o robots.txt não deixa)." % self.lojas.porta, st["passos"])
        S.busca_do_site = lambda *a, **k: (_ for _ in ()).throw(OSError("x"))
        self.assertEqual(S.testa_marketplace(self.config(), "magalu", "Magalu", {})["como"], "ia")
        S.MKT_SITES["amazon"] = "http://127.0.0.1:9"
        st = S.testa_marketplace(self.config(), "amazon", "Amazon", {})
        self.assertTrue(st["passos"][0].startswith("✗ O site 127.0.0.1:9 não respondeu"), st["passos"])


class Rodadas(Base):
    def test_teste_de_todas_com_erro_numa_loja(self):
        S = self.S
        self.ofertas({"categorias": [categoria("mercados", [("merc-a", "Loja A", 1.0), ("merc-b", "Loja B", 1.5)])]})
        orig = S.testa_preco_loja
        S.testa_preco_loja = lambda c, n, *a, **k: (_ for _ in ()).throw(RuntimeError("quebrou")) if n == "Loja A" else {"como": "folheto", "passos": [], "em": "x"}
        S.sonda_lojas(self.config(usar_ia=False, raio_km="muito"))
        f = S.ler_json(S.SONDA_FILE)["mercados"]
        self.assertEqual(f["loja a"]["passos"], ["✗ Erro no teste: quebrou"])
        self.assertEqual(S.SONDA["resumo"], "Testei 2 lojas: 1 com folheto ou encarte no Instagram, 1 sem fonte de preço sem IA.")
        S.testa_preco_loja = lambda *a, **k: {"como": "ia", "passos": [], "em": "x"}
        S.sonda_lojas(self.config())
        self.assertEqual(S.SONDA["resumo"], "Testei 2 lojas: 2 só pela busca com IA.")
        S.testa_preco_loja = orig

    def test_o_teste_para_e_avisa(self):
        S = self.S
        S.atualiza_diretas = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("sem disco"))
        S.sonda_lojas(self.config())
        self.assertEqual((S.SONDA["resumo"], S.SONDA["rodando"]), ("O teste parou: sem disco", False))
        S.ler_json = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("sem disco"))
        S.sonda_loja({}, "mercados", "merc-x")
        self.assertEqual((S.SONDA["resumo"], S.SONDA["rodando"]), ("O teste parou: sem disco", False))

    def test_nenhuma_loja(self):
        S = self.S
        S.sonda_lojas(self.config())
        self.assertEqual(S.SONDA["resumo"], "Nenhuma loja para testar.")

    def test_uma_loja_sem_site_procura_o_site(self):
        S = self.S
        self.ofertas({"categorias": [categoria("mercados", [("merc-a", "Loja Sem Site", 1.0)])]})
        S.sites_por_ia = lambda cfg, lojas, forcar=False: {"loja sem site": self.b + "/achado/"} if forcar else {}
        S.sonda_loja(self.config(usar_ia=False), "mercados", "merc-a")
        st = S.ler_json(S.SONDA_FILE)["mercados"]["loja sem site"]
        self.assertEqual(st["site_url"], self.b + "/achado/")
        loja = S.ler_json(S.OFERTAS)["categorias"][0]["lojas"][0]
        self.assertEqual(loja["site"], self.b + "/achado/", "o site achado vai para a loja")

    def test_uma_loja_com_erro_no_teste(self):
        S = self.S
        self.ofertas({"categorias": [categoria("mercados", [("merc-a", "Loja A", 1.0)])]})
        S.testa_preco_loja = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("quebrou"))
        S.sonda_loja(self.config(), "mercados", "merc-a")
        self.assertEqual(S.ler_json(S.SONDA_FILE)["mercados"]["loja a"]["passos"], ["✗ Erro no teste: quebrou"])
        S.sonda_loja(self.config(), "online", "mkt:inexistente")
        self.assertEqual(S.SONDA["resumo"], "Não achei essa loja.")


class MarcaFontes(Base):
    def test_folheto_e_instagram_ja_lidos(self):
        S = self.S
        S.gravar_json(S.SONDA_FILE, {"mercados": {"a": {"como": "folheto_novo"}, "b": {"como": "instagram_novo"}, "c": {"como": "ia", "site_url": "https://c.com.br"}}})
        cats = ["x", categoria("mercados", [("m-a", "A", 1, {"folheto": "u", "folheto_ate": "2026-11-09"}), ("m-b", "B", 1, {"instagram": "u", "instagram_ate": None}),
                                            ("m-c", "C", 1, {"site": "https://www.instagram.com/c"})])]
        S.marca_fontes(cats)
        a, b, c = cats[1]["lojas"]
        self.assertEqual((a["preco_fonte"]["como"], a["preco_fonte"]["passos"]), ("folheto", ["✓ Folheto da semana lido pela IA, vale até 09/11."]))
        self.assertEqual((b["preco_fonte"]["como"], b["preco_fonte"]["passos"]), ("instagram", ["✓ Encarte do Instagram lido pela IA."]))
        self.assertEqual(c["site"], "https://c.com.br", "o site achado troca o da rede social")

    def test_lojas_acompanhadas_com_raio_invalido(self):
        S = self.S
        cats = [{"id": "online"}, categoria("mercados", [("m-a", "A", 1.5), ("m-b", "B", 3.0)])]
        self.assertEqual([x[1] for x in S.lojas_acompanhadas({"raio_km": "x"}, cats)], ["m-a"], "raio inválido: 2 km")


class TestarGoogleEBrave(Base):
    def test_google_sem_farmacias_e_com_erro(self):
        S = self.S
        S.grava_segredos({"google": {"key": "k"}})
        self.lojas.rotas["/google/nearby"] = lambda p: {"places": []}
        self.assertEqual(S.testar_google(), {"ok": True, "msg": "O Google aceitou a chave, mas não achou farmácias a 1 km da sua casa."})
        S.casa = lambda cfg=None: (_ for _ in ()).throw(KeyError("latitude"))
        self.assertEqual(S.testar_google(), {"ok": False, "msg": "Não consegui testar ('latitude')."})

    def test_brave_erros(self):
        S = self.S
        S.grava_segredos({"brave": {"key": "k"}})
        self.lojas.rotas["/brave"] = lambda p: (500, {})
        self.assertEqual(S.testar_brave(), {"ok": False, "msg": "O Brave respondeu com erro 500."})
        S.brave_busca = lambda *a, **k: (_ for _ in ()).throw(ValueError("json"))
        self.assertEqual(S.testar_brave(), {"ok": False, "msg": "Não consegui testar (json)."})

    def test_sites_por_ia_com_erros(self):
        S = self.S
        S.grava_segredos({"brave": {"key": "k"}})
        self.lojas.rotas["/brave"] = lambda p: (429, {})
        self.ha.responde_ia("sites das lojas", lambda c: __import__("ha_falso").Erro(500, "x"))
        self.assertEqual(S.sites_por_ia(self.config(), [{"nome": "Mercearia Dona Maria"}]), {})
        self.assertTrue(any("sites das lojas (Brave): O Brave pediu para esperar" in str(m) for m in self.log))
        self.assertTrue(any("sites das lojas: A IA do Home Assistant recusou o pedido (500)" in str(m) for m in self.log))
