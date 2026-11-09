"""Instagram pela API oficial (Business Discovery, Graph API falsa em OFERTAS_GRAPH): a conta achada pela chave, o teste
com a validade da chave, os erros da Meta, os posts de oferta pela legenda (imagem e carrossel, até 8 dias), as lojas
com Instagram, a leitura pela IA guardada até vencer, e a chave que nunca vai para a IA nem para o Home Assistant."""
import json
from datetime import datetime, timedelta, timezone

from apoio import Cenario, categoria

IG = "17841400000000001"
TOKEN = "EAAG-chave-do-instagram-secreta"


class Base(Cenario):
    def setUp(self):
        super().setUp()
        self.contas = {"kuntze_oficial": self.posts()}
        self.erro = None
        self.validade = {"expires_at": 0}
        self.lojas.rotas["/graph/me/accounts"] = lambda p: self.resp(p, {"data": [{"name": "Página sem IG"}, {"name": "Minha página",
                                                                                   "instagram_business_account": {"id": IG, "username": "davicasa"}}]})
        self.lojas.rotas["/graph/debug_token"] = lambda p: self.resp(p, {"data": self.validade})
        self.lojas.rotas["/graph/" + IG] = self.discovery
        for n in ("p1", "c1", "c2"):
            self.lojas.paginas[f"/ig/{n}.jpg"] = (200, b"\xff\xd8" + n.encode() * 100, "image/jpeg")

    def resp(self, p, d):
        if self.erro:
            return (400, {"error": self.erro})
        self.assertEqual(p.query["access_token"], [TOKEN])
        return d

    def quando(self, dias):
        return (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%dT12:00:00+0000")

    def posts(self):
        b = self.lojas.base
        return [{"id": "1", "media_type": "IMAGE", "caption": "Ofertas de sexta! Picanha R$ 49,90", "media_url": b + "/ig/p1.jpg",
                 "permalink": "https://www.instagram.com/p/AAA/", "timestamp": self.quando(1)},
                {"id": "2", "media_type": "CAROUSEL_ALBUM", "caption": "Encarte da semana", "permalink": "https://www.instagram.com/p/BBB/",
                 "timestamp": self.quando(2), "children": {"data": [{"media_type": "IMAGE", "media_url": b + "/ig/c1.jpg"}, {"media_type": "VIDEO", "media_url": b + "/v.mp4"},
                                                                    {"media_type": "IMAGE", "media_url": b + "/ig/c2.jpg"}]}},
                {"id": "3", "media_type": "VIDEO", "caption": "promoção", "media_url": b + "/v.mp4", "timestamp": self.quando(1)},
                {"id": "4", "media_type": "IMAGE", "caption": "Oferta antiga", "media_url": b + "/ig/p1.jpg", "timestamp": self.quando(20)},
                {"id": "5", "media_type": "IMAGE", "caption": "Feliz aniversário, Maria!", "media_url": b + "/ig/p1.jpg", "timestamp": self.quando(1)}]

    def discovery(self, p):
        campos = p.query["fields"][0]
        h = campos.split("business_discovery.username(", 1)[1].split(")", 1)[0]
        if h == "instagram":
            return self.resp(p, {"business_discovery": {"username": "instagram", "media_count": 8000}, "id": IG})
        if h not in self.contas:
            return (400, {"error": {"code": 110, "error_subcode": 2207013, "message": "Cannot find User"}})
        self.assertIn("media.limit(12){id,caption,media_type,media_url,permalink,timestamp,children{media_type,media_url}}", campos)
        return self.resp(p, {"business_discovery": {"username": h, "media": {"data": self.contas[h]}}, "id": IG})

    def chave(self, ig=True):
        self.S.grava_segredos({"instagram": dict({"token": TOKEN}, **({"ig_id": IG, "usuario": "davicasa"} if ig else {}))})


class Conta(Base):
    def test_testar_acha_a_conta_e_diz_a_validade(self):
        S = self.S
        self.assertEqual(S.testar_instagram(), {"ok": False, "msg": "Falta a chave do Instagram."})
        self.assertFalse(S.insta_pronto())
        self.chave(ig=False)
        self.assertEqual(S.insta_chave(), (TOKEN, None))
        r = S.testar_instagram()
        self.assertEqual(r, {"ok": True, "msg": "Pronta: conta @davicasa. Consigo ler os posts das contas comerciais das lojas. A chave não vence."})
        self.assertEqual(S.segredos()["instagram"], {"token": TOKEN, "ig_id": IG, "usuario": "davicasa"}, "a conta fica guardada")
        self.assertTrue(S.insta_pronto())
        fim = int(datetime(2027, 1, 15, 15, tzinfo=timezone.utc).timestamp())
        self.validade = {"expires_at": fim}
        self.assertTrue(S.testar_instagram()["msg"].endswith("A chave vale até 15/01/2027."))
        self.validade = {"expires_at": None, "data_access_expires_at": fim}
        self.assertTrue(S.testar_instagram()["msg"].endswith("A chave vale até 15/01/2027."))
        self.validade = {}
        self.assertTrue(S.testar_instagram()["msg"].endswith("lojas."))

    def test_sem_conta_profissional_e_erros_da_meta(self):
        S = self.S
        self.chave(ig=False)
        self.lojas.rotas["/graph/me/accounts"] = lambda p: {"data": [{"name": "Só página"}]}
        self.assertIn("não achei conta profissional do Instagram", S.testar_instagram()["msg"])
        self.chave()
        casos = [({"code": 190, "message": "Session has expired"}, "A chave do Instagram venceu ou foi cancelada"),
                 ({"code": 4, "message": "Application request limit reached"}, "O Instagram pediu para esperar"),
                 ({"code": 10, "message": "Permission denied"}, "a chave não tem as permissões instagram_basic"),
                 ({"code": 100, "message": "Invalid parameter"}, r"O Instagram recusou o pedido \(400: Invalid parameter\)")]
        for erro, msg in casos:
            self.erro = erro
            r = S.testar_instagram()
            self.assertFalse(r["ok"])
            self.assertRegex(r["msg"], msg)
        self.erro = None
        self.lojas.rotas["/graph/" + IG] = lambda p: {"id": IG}
        self.assertEqual(S.testar_instagram(), {"ok": False, "msg": "O Instagram não respondeu como esperado."})
        with self.assertRaisesRegex(S.ErroBusca, "conta não encontrada ou não é comercial"):
            self.lojas.rotas["/graph/" + IG] = self.discovery
            S.graph_get(IG, {"fields": "business_discovery.username(nao_existe){username}"}, TOKEN)

    def test_handle(self):
        S = self.S
        for u, h in (("https://www.instagram.com/Mercado_BoiDourado/", "mercado_boidourado"), ("@kuntze.oficial.", "kuntze.oficial"),
                     ("instagram.com/kuntze?igsh=1", "kuntze"), ("https://www.instagram.com/p/AAA/", None), ("https://www.instagram.com/reel/x", None),
                     ("@a", None), ("https://kuntze.com.br", None), (None, None)):
            self.assertEqual(S.insta_handle(u), h, u)


class Posts(Base):
    def test_posts_de_oferta(self):
        S = self.S
        self.chave()
        cache = {}
        posts, erro = S.insta_posts("kuntze_oficial", cache)
        self.assertIsNone(erro)
        self.assertEqual(len(posts), 5)
        enc = S.posts_encarte(posts)
        self.assertEqual([(p["id"], p["imgs"]) for p in enc], [("1", [self.lojas.base + "/ig/p1.jpg"]),
                                                               ("2", [self.lojas.base + "/ig/c1.jpg", self.lojas.base + "/ig/c2.jpg"])],
                         "só imagem e carrossel, dos últimos 8 dias, com legenda de oferta; o vídeo do carrossel fica de fora")
        n = len(self.lojas.pedidos)
        S.insta_posts("kuntze_oficial", cache)
        self.assertEqual(len(self.lojas.pedidos), n, "guardado por 12 horas")
        S.insta_posts("kuntze_oficial", cache, forcar=True)
        self.assertGreater(len(self.lojas.pedidos), n)
        posts, erro = S.insta_posts("nao_existe", cache)
        self.assertEqual(posts, [])
        self.assertIn("não é comercial", erro)
        self.assertIn("erro", cache["contas"]["nao_existe"])

    def test_lojas_com_instagram(self):
        S = self.S
        cfg = {"raio_km": 2, "lojas": {"ignorar": ["merc-ignorada"], "adicionar": [{"nome": "Kuntze, Centro", "categoria": "mercados", "site": "@kuntze_oficial"},
                                                                                  {"nome": "Sem Insta", "categoria": "mercados", "site": "https://x.com.br"}]}}
        cats = [categoria("mercados", [("merc-boi", "Boi Dourado", 1.0, {"social": "https://www.instagram.com/boidourado/"}),
                                       ("merc-kuntze", "Kuntze", 1.0, {"instagram_perfil": "@kuntze_oficial"}),
                                       ("merc-ignorada", "Ignorada", 1.0, {"social": "https://instagram.com/ignorada"}),
                                       ("merc-longe", "Longe", 9.0, {"social": "https://instagram.com/longe"})]),
                categoria("petshops", [("pets-cao", "Cão", 1.0, {"social": "https://instagram.com/cao"})])]
        r = S.lojas_instagram(cfg, ["mercados"], cats)
        self.assertEqual(r, [{"nome": "Kuntze", "categoria": "mercados", "handle": "kuntze_oficial"},
                             {"nome": "Boi Dourado", "categoria": "mercados", "handle": "boidourado"}])

    def test_le_os_posts_novos_e_guarda(self):
        S, ha = self.S, self.ha
        self.chave()
        cfg = self.config(lista=[{"produto": "Picanha"}, {"produto": "Café"}],
                          lojas={"adicionar": [{"nome": "Kuntze", "categoria": "mercados", "site": "https://www.instagram.com/kuntze_oficial/"}]})
        ate = (datetime.strptime(S.hoje_br(), "%Y-%m-%d") + timedelta(days=3)).strftime("%Y-%m-%d")

        def le(corpo):
            if "Picanha R$ 49,90" in corpo["instructions"]:
                return {"validade": ate, "ofertas": [{"produto": "Picanha Bovina kg", "preco": 49.9, "unidade": "kg"}],
                        "lista": [{"item": 1, "precos": [{"preco": 49.9}]}, {"item": 9, "precos": [{"preco": 1}]}]}
            return {"validade": None, "ofertas": []}
        ha.responde_ia("Instagram Kuntze", le)
        out = S.busca_instagram(cfg, ["mercados"], {})
        self.assertEqual(len(ha.chamadas_ia), 2, "os 2 posts de oferta")
        self.assertIn("Legenda do post: Ofertas de sexta!", ha.chamadas_ia[0]["instructions"])
        self.assertEqual(len(ha.chamadas_ia[1]["attachments"]), 2, "o carrossel com as 2 imagens")
        self.assertEqual(len(out), 1, "o post sem ofertas não entra")
        cat, parcial = out[0]
        loja = cat["lojas"][0]
        self.assertEqual((loja["fontes"], loja["instagram"], loja["instagram_ate"]), (["Instagram"], "https://www.instagram.com/p/AAA/", ate))
        self.assertEqual(parcial["Picanha"]["precos"], {"merc-kuntze": 49.9})
        lidos = S.ler_json(S.INSTAGRAM)["lidos"]
        self.assertEqual(lidos["1"]["ate"], ate)
        self.assertIsNone(lidos["2"]["r"], "sem ofertas: guardado como lido, sem resultado")
        self.assertEqual(lidos["2"]["ate"], (datetime.fromisoformat(self.quando(2)[:10]) + timedelta(days=7)).date().isoformat(),
                         "sem validade: 7 dias depois do post")
        # na próxima busca: o que já foi lido, sem IA
        out = S.busca_instagram(cfg, ["mercados"], {})
        self.assertEqual((len(out), len(ha.chamadas_ia)), (1, 2))
        self.assertEqual(S.busca_instagram(cfg, ["mercados"], {"mercados": ["Kuntze"]}), [], "loja com preço pelo site fica de fora")
        self.assertEqual(len(S.busca_instagram(cfg, ["mercados"], {}, ler=False)), 1)
        # a chave só vai para a Graph API
        self.assertNotIn(TOKEN, ha.tudo_que_chegou())
        self.assertFalse([p for p in self.lojas.pedidos if TOKEN in json.dumps(p) and not p[1].startswith("/graph/")])

    def test_post_vencido_e_limite_por_busca(self):
        S, ha = self.S, self.ha
        self.chave()
        cfg = self.config(lista=[{"produto": "Picanha"}], lojas={"adicionar": [{"nome": "Kuntze", "categoria": "mercados", "site": "@kuntze_oficial"}]})
        ha.responde_ia("Instagram", {"validade": "2020-01-01", "ofertas": [{"produto": "Picanha", "preco": 40}]})
        self.assertEqual(S.busca_instagram(cfg, ["mercados"], {}, max_novos=1), [])
        self.assertEqual(len(ha.chamadas_ia), 1, "até max_novos posts novos por busca")
        self.assertIsNone(S.ler_json(S.INSTAGRAM)["lidos"]["1"]["r"], "vencido: não guarda as ofertas")
        self.assertEqual(S.busca_instagram(self.config(opcoes={"folhetos": False}), ["mercados"], {}), [])
        self.assertEqual(S.busca_instagram(self.config(usar_ia=False, lojas=cfg["lojas"]), ["mercados"], {}), [])
        self.assertEqual(len(ha.chamadas_ia), 1)


class Bordas(Base):
    """Erro sem JSON da Graph API, validade que não dá para saber, teste que quebra, raio inválido, nada para ler,
    imagens que não baixam e a IA que falha no meio."""

    def test_erro_sem_json_e_validade_desconhecida(self):
        S = self.S
        self.chave()
        self.lojas.rotas["/graph/" + IG] = lambda p: (502, "<html>Bad Gateway</html>", "text/html")
        with self.assertRaisesRegex(S.ErroBusca, r"^O Instagram recusou o pedido \(502: \)\.$"):
            S.graph_get(IG, {"fields": "x"}, TOKEN)
        self.erro = {"code": 190}
        self.assertEqual(S.insta_validade(TOKEN), "", "a validade não dá para saber: não diz nada")

    def test_teste_que_quebra(self):
        S = self.S
        self.chave()
        S.graph_get = lambda *a, **k: (_ for _ in ()).throw(ValueError("resposta estranha"))
        self.assertEqual(S.testar_instagram(), {"ok": False, "msg": "Não consegui testar (resposta estranha)."})

    def test_lojas_com_raio_invalido(self):
        S = self.S
        cats = [categoria("mercados", [("merc-boi", "Boi", 1.5, {"social": "https://www.instagram.com/boi/"}),
                                       ("merc-longe", "Longe", 2.5, {"social": "https://www.instagram.com/longe/"})])]
        self.assertEqual([x["handle"] for x in S.lojas_instagram({"raio_km": "x"}, None, cats)], ["boi"], "raio inválido: 2 km")

    def test_nenhuma_loja_com_instagram(self):
        S = self.S
        self.chave()
        self.assertEqual(S.busca_instagram(self.config(), ["mercados"], {}), [])
        self.assertFalse(self.lojas.pedidos_de("/graph/"))

    def test_conta_com_erro_e_imagens_que_nao_baixam(self):
        S, ha = self.S, self.ha
        self.chave()
        self.contas["kuntze_oficial"] = [dict(p, media_url=self.lojas.base + "/sumiu.jpg") for p in self.posts()[:1]]
        lojas = {"adicionar": [{"nome": "Sem Conta", "categoria": "mercados", "site": "@nao_existe"},
                               {"nome": "Kuntze", "categoria": "mercados", "site": "@kuntze_oficial"}]}
        self.assertEqual(S.busca_instagram(self.config(lojas=lojas), ["mercados"], {}), [])
        self.assertEqual(ha.chamadas_ia, [], "a imagem não baixou: nada para a IA")
        self.assertTrue(any("Instagram de Sem Conta (@nao_existe): conta não encontrada" in str(m) for m in self.log))

    def test_ia_que_falha_para_a_loja(self):
        S, ha = self.S, self.ha
        self.chave()
        ha.responde_ia("Instagram Kuntze", __import__("ha_falso").Erro(500, "falhou"))
        cfg = self.config(lojas={"adicionar": [{"nome": "Kuntze", "categoria": "mercados", "site": "@kuntze_oficial"}]})
        self.assertEqual(S.busca_instagram(cfg, ["mercados"], {}), [])
        self.assertEqual(len(ha.chamadas_ia), 1, "a IA falhou: não tenta o outro post da mesma loja")
        self.assertTrue(any("Instagram de Kuntze: A IA do Home Assistant recusou o pedido (500)" in str(m) for m in self.log))
        self.assertEqual(S.ler_json(S.INSTAGRAM).get("lidos"), {}, "nada fica como lido")
