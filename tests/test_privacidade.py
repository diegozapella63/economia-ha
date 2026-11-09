"""As regras de privacidade do AGENTS.md, conferidas no que sai do app de verdade (todos os pedidos que chegam às lojas
falsas, aos serviços e ao Home Assistant falso): o e-mail do dono nunca sai, cada chave só vai para o serviço dela (a
senha da Shopee nem isso: só a assinatura), as chaves não ficam no config.json nem no arquivo exportado, e as fotos
lidas pela IA não ficam na pasta de mídia."""
import base64
import json
import os

from apoio import Cenario, categoria

EMAIL = "davi.souza@exemplo.com.br"
CHAVES = {"brave": "chave-brave-secreta", "google": "chave-google-secreta", "shopee": "senha-shopee-secreta", "instagram": "token-instagram-secreto"}


class Privacidade(Cenario):
    def setUp(self):
        super().setUp()
        S, lj = self.S, self.lojas
        S.grava_segredos({"brave": {"key": CHAVES["brave"]}, "google": {"key": CHAVES["google"]},
                          "shopee": {"app_id": "18300000001", "secret": CHAVES["shopee"]},
                          "instagram": {"token": CHAVES["instagram"], "ig_id": "99", "usuario": "casa"}})
        lj.rotas["/brave"] = lambda p: {"web": {"results": [{"url": "https://www.giassi.com.br", "title": "Giassi"}]}}
        lj.rotas["/google/nearby"] = lambda p: {"places": []}
        lj.rotas["/google/texto"] = lambda p: {"places": []}
        lj.rotas["/overpass"] = lambda p: {"elements": [{"type": "node", "lat": -26.304, "lon": -48.85, "tags": {"name": "Mercado Kuntze", "shop": "supermarket"}}]}
        lj.rotas["/shopee"] = lambda p: {"data": {"productOfferV2": {"nodes": []}}}
        lj.rotas["/graph/99"] = lambda p: {"business_discovery": {"username": "instagram", "media": {"data": []}}, "id": "99"}
        lj.rotas["/graph/debug_token"] = lambda p: {"data": {"expires_at": 0}}
        self.ha.responde_ia("", {"lojas": [{"rede": "Mercado Kuntze", "distancia_km": 1.0}], "lista": [], "ofertas": [], "cupons": []})
        self.config(email=EMAIL, usuario=EMAIL, categorias=["mercados", "online"], lista=[{"produto": "Leite integral"}],
                    lojas={"adicionar": [{"nome": "Açougue Boi", "categoria": "mercados", "site": "@boi"}]})

    def tudo_que_saiu(self):
        return json.dumps(self.lojas.pedidos, ensure_ascii=False, default=str) + self.ha.tudo_que_chegou()

    def roda_tudo(self):
        S = self.S
        S.buscar()
        self.assertIsNone(S.BUSCA["erro"])
        S.lojas_do_mapa(S.ler_config(), ["mercados"], forcar=True)
        S.sonda_lojas(S.ler_config())
        S.produto_por_ean("7896004000855", S.ler_config())
        for f in (S.testar_brave, S.testar_google, S.testar_shopee, S.testar_instagram, lambda: S.testar_ia("busca")):
            f()

    def test_o_email_do_dono_nunca_sai(self):
        self.roda_tudo()
        saiu = self.tudo_que_saiu()
        self.assertIn("Leite integral", saiu, "a conferência vê o que sai")
        self.assertNotIn(EMAIL, saiu)
        self.assertNotIn("davi.souza", saiu.lower())
        self.assertNotIn("@exemplo.com.br", saiu.lower())

    def test_cada_chave_so_vai_para_o_seu_servico(self):
        self.roda_tudo()
        donos = {"brave": "/brave", "google": "/google/", "instagram": "/graph/"}
        for nome, chave in CHAVES.items():
            with self.subTest(chave=nome):
                self.assertNotIn(chave, self.ha.tudo_que_chegou(), "nem para a IA nem para o Home Assistant")
                fora = [p[1] for p in self.lojas.pedidos if chave in json.dumps(p, ensure_ascii=False, default=str) and not p[1].startswith(donos.get(nome, "/nunca"))]
                self.assertEqual(fora, [], f"a chave {nome} só vai para o serviço dela")
        self.assertTrue(self.lojas.pedidos_de("/shopee"), "a Shopee foi consultada (só com a assinatura)")

    def test_chaves_fora_do_config_e_da_pagina(self):
        S = self.S
        cfg_txt = open(S.CONFIG, encoding="utf-8").read()
        for chave in CHAVES.values():
            self.assertNotIn(chave, cfg_txt)
        self.assertEqual(oct(os.stat(S.SEGREDOS).st_mode & 0o777), "0o600")
        exportado = S.exportar("json")[0].decode()
        for chave in list(CHAVES.values()) + [EMAIL]:
            self.assertNotIn(chave, exportado, "o arquivo exportado não leva chave nem e-mail")

    def test_fotos_nao_ficam_na_pasta_de_midia(self):
        S, ha = self.S, self.ha
        self.ofertas({"categorias": [categoria("mercados", [("merc-giassi", "Giassi", 1.0)])]})
        ha.responde_ia("ler lista", {"itens": [{"produto": "Café"}]})
        ha.responde_ia("encarte", {"ofertas": [{"produto": "Café", "preco": 9.9}]})
        jpg = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0" + b"\0" * 200).decode()
        for job in (S.comeca_leitura({"imagens": [jpg]}), S.comeca_encarte({"imagens": [jpg], "loja": "Giassi"})):
            self.espera(lambda: S.LEITURAS[job]["status"] != "lendo", msg="a leitura não terminou")
        self.assertEqual(os.listdir(os.path.join(S.MEDIA, "economia")), [], "as fotos saem da pasta de mídia depois de lidas")
        anexos = [a for c in ha.chamadas_ia for a in c.get("attachments") or []]
        self.assertEqual(len(anexos), 2)
        self.assertTrue(all(a["media_content_id"].startswith("media-source://media_source/local/economia/") for a in anexos))
