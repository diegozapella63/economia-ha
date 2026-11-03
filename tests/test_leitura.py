"""Ler com IA: a lista por foto ou mensagem colada (ler_lista, comeca_leitura), o Falar (origem "fala"), os cupons do
app (ler_cupons), o encarte mandado pelo morador (comeca_encarte → ofertas.json) e o encarte do site da loja
(ler_encarte: PDF, imagem, página com imagens, só texto, vencido). As fotos ficam na pasta de mídia só durante a
leitura e vão como media-source."""
import base64
import os

from apoio import Cenario, categoria
from ha_falso import Erro

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\0" * 64


def data_url(dado, tipo="image/png"):
    return f"data:{tipo};base64," + base64.b64encode(dado).decode()


class LerLista(Cenario):
    def ler(self, dado):
        job = self.S.comeca_leitura(dado)
        self.assertTrue(job)
        return self.espera(lambda: self.S.LEITURAS[job] if self.S.LEITURAS[job]["status"] != "lendo" else None, msg="a leitura não terminou")

    def test_mensagem_colada(self):
        ha = self.ha
        self.config(lista=[{"produto": "Leite integral 1 L"}, {"produto": "Café Pilão 500 g"}])
        ha.responde_ia("ler lista", {"itens": [{"produto": "leite integral 1 l", "quantidade": "2"}, {"produto": "Detergente Ypê", "obs": "neutro"},
                                               {"produto": "Detergente Ypê"}, {"produto": "x"}, "lixo", {"quantidade": "3"}]})
        r = self.ler({"texto": "Amor, compra 2 leites integrais e detergente Ypê neutro. Bjs"})
        self.assertEqual(r["status"], "pronto")
        self.assertEqual(r["itens"], [{"produto": "Leite integral 1 L", "ja_na_lista": True, "quantidade": "2"},
                                      {"produto": "Detergente Ypê", "ja_na_lista": False, "obs": "neutro"}],
                         "o nome que já está na lista, sem repetidos e sem lixo")
        corpo = ha.chamadas_ia[-1]
        self.assertEqual(corpo["task_name"], "EconomIA: ler lista")
        self.assertNotIn("attachments", corpo)
        self.assertIn('"""Amor, compra 2 leites integrais', corpo["instructions"])
        self.assertIn("Itens que já estão na lista: Leite integral 1 L; Café Pilão 500 g", corpo["instructions"])
        self.assertIn("provavelmente pelo WhatsApp", corpo["instructions"])

    def test_fotos_vao_como_anexo_e_sao_apagadas(self):
        S, ha = self.S, self.ha
        ha.tarefa_ia("ai_task.claude", "Claude")
        self.config(ia={"fotos": "ai_task.claude"})
        pasta = os.path.join(S.MEDIA, "economia")
        vistos = {}

        def resp(corpo):
            vistos["arquivos"] = sorted(os.listdir(pasta))
            vistos["anexos"] = corpo["attachments"]
            return {"itens": [{"produto": "Arroz 5 kg"}]}
        ha.responde_ia("ler lista", resp)
        r = self.ler({"imagens": [data_url(PNG), data_url(JPG, "image/jpeg"), "data:text/html;base64,PGI+", "não é imagem",
                                  data_url(b"", "image/png")]})
        self.assertEqual(r["itens"], [{"produto": "Arroz 5 kg", "ja_na_lista": False}])
        self.assertEqual(len(vistos["arquivos"]), 2, "só as imagens de verdade")
        self.assertEqual([a["media_content_type"] for a in vistos["anexos"]], ["image/png", "image/jpeg"])
        self.assertTrue(all(a["media_content_id"].startswith("media-source://media_source/local/economia/lista-") for a in vistos["anexos"]))
        self.assertEqual(ha.chamadas_ia[-1]["entity_id"], "ai_task.claude", "a IA de fotos")
        self.assertIn("2 imagem(ns) em anexo", ha.chamadas_ia[-1]["instructions"])
        self.assertEqual(os.listdir(pasta), [], "as fotos saem da pasta de mídia depois da leitura")

    def test_fala_e_erros(self):
        S, ha = self.S, self.ha
        self.config()
        ha.responde_ia("falar", {"itens": [{"produto": "Leite integral", "quantidade": "dois"}]})
        r = self.ler({"texto": "compra dois leites integrais", "origem": "fala"})
        self.assertEqual(r["itens"], [{"produto": "Leite integral", "ja_na_lista": False, "quantidade": "dois"}])
        self.assertEqual(ha.chamadas_ia[-1]["task_name"], "EconomIA: falar")
        self.assertIn("a fala para texto do Home Assistant transcreveu", ha.chamadas_ia[-1]["instructions"])
        self.assertEqual(S.uso_resumo()["hoje"]["tipos"], {"fala": 1})
        ha.responde_ia("ler lista", Erro(400, "attachments are not supported"), vezes=1)
        r = self.ler({"imagens": [data_url(PNG)]})
        self.assertEqual((r["status"], r["erro"]), ("erro", "A IA escolhida no Home Assistant não lê imagens. Use uma que leia, como a Anthropic, "
                                                             "ou cole o texto da mensagem."))
        ha.responde_ia("ler lista", "Não vejo itens.", vezes=1)
        r = self.ler({"texto": "oi"})
        self.assertEqual(r["status"], "erro")
        self.assertIn("A IA respondeu fora do formato esperado.", r["erro"])
        self.assertIsNone(S.comeca_leitura({"texto": "   "}), "sem foto e sem texto: nada")
        self.assertIsNone(S.comeca_leitura({"imagens": ["data:image/png;base64,"]}))

    def test_guarda_so_as_ultimas_leituras(self):
        S, ha = self.S, self.ha
        self.config()
        ha.responde_ia("ler lista", {"itens": []})
        for i in range(25):
            S.LEITURAS[f"0000{i:02d}-x"] = {"status": "pronto", "itens": [], "erro": None}
        r = self.ler({"texto": "nada"})
        self.assertEqual(r["itens"], [])
        self.assertLessEqual(len(S.LEITURAS), 21)


class LeituraBordas(Cenario):
    """A pasta de mídia que não dá para usar, o erro inesperado ao ler (lista e encarte) e fotos que não são base64."""

    def espera_job(self, job):
        return self.espera(lambda: self.S.LEITURAS[job] if self.S.LEITURAS[job]["status"] != "lendo" else None, msg="a leitura não terminou")

    def test_pasta_de_midia_que_nao_da_para_usar(self):
        S = self.S
        self.config()
        arq = os.path.join(S.DATA, "nao-e-pasta")
        open(arq, "w").close()
        S.MEDIA = arq
        r = self.espera_job(S.comeca_leitura({"imagens": [data_url(PNG)]}))
        self.assertEqual((r["status"], r["erro"]), ("erro", "O add-on não consegue usar a pasta de mídia do Home Assistant. Reinstale a versão mais nova."))
        self.assertEqual(self.ha.chamadas_ia, [], "nem chega à IA")

    def test_erro_inesperado_ao_ler(self):
        S, ha = self.S, self.ha
        self.config()
        ha.responde_ia("ler lista", {"itens": [{"produto": "Leite integral"}]})
        S.texto = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("texto quebrou"))
        r = self.espera_job(S.comeca_leitura({"texto": "leite"}))
        self.assertEqual((r["status"], r["erro"]), ("erro", "Erro inesperado ao ler: texto quebrou"))
        self.assertIn("Erro inesperado ao ler: texto quebrou", self.log)

    def test_erro_inesperado_no_encarte(self):
        S, ha = self.S, self.ha
        self.config()
        ha.responde_ia("encarte", {"ofertas": [{"produto": "Café", "preco": 9}]})
        S.mesclar_resultado = lambda *a, **k: (_ for _ in ()).throw(KeyError("lista"))
        r = self.espera_job(S.comeca_encarte({"imagens": [data_url(JPG, "image/jpeg")], "loja": "Giassi"}))
        self.assertEqual((r["status"], r["erro"]), ("erro", "Erro inesperado ao ler: 'lista'"))
        self.assertEqual(os.listdir(os.path.join(S.MEDIA, "economia")), [], "a foto é apagada mesmo assim")

    def test_guarda_so_os_ultimos_encartes(self):
        S, ha = self.S, self.ha
        self.config()
        ha.responde_ia("encarte", {"ofertas": []})
        for i in range(25):
            S.LEITURAS[f"0000{i:02d}-x"] = {"status": "pronto", "itens": [], "erro": None}
        self.espera_job(S.comeca_encarte({"imagens": [data_url(JPG, "image/jpeg")], "loja": "Giassi"}))
        self.assertLessEqual(len(S.LEITURAS), 21)
        self.assertNotIn("000000-x", S.LEITURAS, "as mais antigas saem")

    def test_fotos_que_nao_sao_base64(self):
        S = self.S
        self.config()
        ruins = ["data:image/png;base64,abc", "data:image/gif;base64," + base64.b64encode(PNG).decode(), "http://x/foto.png"]
        self.assertIsNone(S.comeca_leitura({"imagens": ruins}))
        self.assertIsNone(S.comeca_encarte({"imagens": ruins, "loja": "Giassi"}))


class Cupons(Cenario):
    def test_cupons_do_app(self):
        S, ha = self.S, self.ha
        self.config()
        self.ofertas({"categorias": [categoria("farmacias", [("farm-panvel", "Panvel", 1.0)])]})
        ha.responde_ia("ler cupons", {"cupons": [
            {"loja": "panvel", "codigo": None, "beneficio": "20% em Colgate", "condicao": "Ativado no app", "valido_ate": "2026-11-30", "produto": "Colgate"},
            {"loja": "Panvel", "beneficio": "20% em Colgate"}, {"loja": "Outra", "beneficio": "R$ 10 acima de R$ 80", "valido_ate": "30/11"},
            {"loja": "Sem benefício"}]})
        job = S.comeca_leitura({"tipo": "cupons", "imagens": [data_url(PNG)], "texto": "ignorado"})
        r = self.espera(lambda: S.LEITURAS[job] if S.LEITURAS[job]["status"] != "lendo" else None)
        self.assertEqual(r["cupons"], [
            {"loja": "panvel", "beneficio": "20% em Colgate", "rede": "farm-panvel", "condicao": "Ativado no app", "produto": "Colgate", "valido_ate": "2026-11-30"},
            {"loja": "Outra", "beneficio": "R$ 10 acima de R$ 80", "rede": None}], "repetido e sem benefício saem; data fora do formato também")
        self.assertIn("Lojas que o morador acompanha: Panvel", ha.chamadas_ia[-1]["instructions"])
        self.assertEqual(S.uso_resumo()["hoje"]["tipos"], {"cupons": 1})
        self.assertIsNone(S.comeca_leitura({"tipo": "cupons", "texto": "só texto não vale para cupons"}))


class EncarteDoMorador(Cenario):
    def test_fotos_do_encarte_entram_no_resultado(self):
        S, ha = self.S, self.ha
        self.config(lista=[{"produto": "Café Pilão 500 g"}, {"produto": "Leite"}])
        self.ofertas({"categorias": [categoria("mercados", [("merc-giassi", "Giassi", 1.0)])],
                      "lista": [{"produto": "Leite", "precos": {"merc-giassi": 4.89}}]})
        ha.responde_ia("encarte Mercado Kuntze", {"validade": "2099-01-10", "ofertas": [
            {"produto": "Café Pilão 500 g", "preco": 15.98, "tamanho": {"quantidade": 500, "unidade": "g"}, "tags": ["cafe"]},
            {"produto": "Picanha kg", "preco": 59.9, "unidade": "kg", "tipo": "clube", "condicao": "clube"}],
            "lista": [{"item": 1, "base": {"quantidade": 500, "unidade": "g"}, "precos": [{"preco": 15.98}]}]})
        job = S.comeca_encarte({"imagens": [data_url(JPG, "image/jpeg")], "loja": "Mercado Kuntze", "categoria": "online"})
        r = self.espera(lambda: S.LEITURAS[job] if S.LEITURAS[job]["status"] != "lendo" else None)
        self.assertEqual(r["status"], "pronto")
        self.assertEqual((r["loja"], r["ofertas"], r["precos"]), ("Mercado Kuntze", 2, ["Café Pilão 500 g"]))
        self.assertEqual(r["itens"], [{"produto": "Café Pilão 500 g", "preco": 15.98}, {"produto": "Picanha kg", "preco": 59.9}])
        self.assertIn("fotos ou prints do encarte, do app ou da gôndola, mandados pelo morador", ha.chamadas_ia[-1]["instructions"])
        of = S.ler_json(S.OFERTAS)
        merc = next(c for c in of["categorias"] if c["id"] == "mercados")
        self.assertEqual(sorted(r["nome"] for r in merc["redes"]), ["Giassi", "Mercado Kuntze"], "online vira mercados")
        loja = next(l for l in merc["lojas"] if l["rede"] == "merc-mercado-kuntze")
        self.assertEqual(loja["fontes"], ["Encarte"])
        oferta = next(o for o in merc["ofertas"] if o["produto"] == "Café Pilão 500 g")
        self.assertEqual((oferta["tipo"], oferta["encarte"], oferta["valido_ate"], oferta["fonte"]), ("encarte", True, "2099-01-10", None))
        lista = {i["produto"]: i for i in of["lista"]}
        self.assertEqual(lista["Café Pilão 500 g"]["precos"], {"merc-mercado-kuntze": 15.98})
        self.assertEqual(lista["Leite"]["precos"], {"merc-giassi": 4.89}, "o que já estava fica")
        self.assertIsNone(S.comeca_encarte({"imagens": [data_url(PNG)]}), "sem a loja: não lê")
        self.assertIsNone(S.comeca_encarte({"loja": "X", "imagens": []}))

    def test_erro_na_leitura(self):
        S, ha = self.S, self.ha
        self.config()
        ha.responde_ia("encarte", Erro(429, "quota"))
        job = S.comeca_encarte({"imagens": [data_url(PNG)], "loja": "Giassi"})
        r = self.espera(lambda: S.LEITURAS[job] if S.LEITURAS[job]["status"] != "lendo" else None)
        self.assertEqual(r["status"], "erro")
        self.assertIn("A cota da IA acabou", r["erro"])
        self.assertIsNone(S.ler_json(S.OFERTAS), "nada gravado")


class EncarteDoSite(Cenario):
    def loja(self, caminho, cat="mercados"):
        return {"nome": "Mercado do Bairro", "site": self.lojas.base + caminho, "categoria": cat}

    def test_pagina_com_imagens(self):
        S, ha, lj = self.S, self.ha, self.lojas
        self.config(lista=[{"produto": "Arroz 5 kg"}])
        grande = b"\xff\xd8" + b"\1" * 50000
        lj.paginas["/mb/ofertas"] = (200, """<html><head><style>.x{}</style><script>var a=1</script></head><body>
            <h1>Ofertas &amp; promoções</h1><img src="/mb/favicon.png"><img srcset="/mb/p1.jpg 1x, /mb/p1-2x.jpg 2x">
            <a href="/mb/encarte.pdf">Encarte em PDF</a><img src="data:image/png;base64,AAA"><img src="/mb/p1.jpg">
            <img src="https://static.wixstatic.com/media/abc_123~mv2.jpg/v1/fill/w_300/abc.jpg"></body></html>""", "text/html")
        lj.paginas["/mb/p1.jpg"] = (200, grande, "image/jpeg")
        lj.paginas["/mb/p1-2x.jpg"] = (200, b"\xff\xd8pequena", "image/jpeg")
        lj.paginas["/mb/encarte.pdf"] = (200, b"%PDF-1.4 x", "application/pdf")
        self.assertEqual(S.candidatos_encarte(lj.paginas["/mb/ofertas"][1], lj.base + "/mb/ofertas"),
                         [lj.base + "/mb/p1.jpg", lj.base + "/mb/p1-2x.jpg", lj.base + "/mb/encarte.pdf",
                          "https://static.wixstatic.com/media/abc_123~mv2.jpg/v1/fit/w_1600,h_3200,q_85/encarte.jpg"],
                         "sem ícone, sem data:, sem repetido; Wix em 1600 px")
        wix = "https://static.wixstatic.com/media/def_456~mv2.png"
        html_wix = (f'<img src="{wix}/v1/fill/w_400,h_600,al_c,q_80,enc_auto/def.png" '
                    f'srcset="{wix}/v1/fill/w_400,h_600,al_c/def.png 1x, {wix}/v1/fill/w_800,h_1200,al_c/def.png 2x">'
                    '<img srcset="/mb/a.jpg 480w,/mb/b.jpg 960w">')
        self.assertEqual(S.candidatos_encarte(html_wix, lj.base + "/mb/ofertas"),
                         [wix + "/v1/fit/w_1600,h_3200,q_85/encarte.jpg", lj.base + "/mb/a.jpg", lj.base + "/mb/b.jpg"],
                         "o endereço do Wix com vírgulas não vira pedaços; srcset sem espaço depois da vírgula também separa")
        texto_pag = S.texto_da_pagina(lj.paginas["/mb/ofertas"][1])
        self.assertTrue(texto_pag.startswith("Ofertas & promoções Encarte em PDF"), texto_pag)
        ha.responde_ia("encarte", {"validade": None, "ofertas": [{"produto": "Arroz Tio João 5 kg", "preco": 24.9, "preco_normal": 29.9}],
                                   "lista": [{"item": 1, "precos": [{"preco": 24.9}]}]})
        cat, parcial = S.ler_encarte(self.loja("/mb/ofertas"), S.ler_config())
        anexos = ha.chamadas_ia[-1]["attachments"]
        self.assertEqual([a["media_content_type"] for a in anexos], ["image/jpeg", "application/pdf"], "a miniatura e o Wix (fora do ar) ficam de fora")
        self.assertIn('do site da loja "Mercado do Bairro"', ha.chamadas_ia[-1]["instructions"])
        self.assertIn("Texto da página: \"\"\"Ofertas & promoções", ha.chamadas_ia[-1]["instructions"])
        self.assertEqual(cat["ofertas"][0]["tipo"], "promo")
        self.assertEqual(cat["lojas"][0]["fontes"], ["Site", "Encarte"])
        self.assertEqual(parcial["Arroz 5 kg"]["precos"], {"merc-mercado-do-bairro": 24.9})
        self.assertEqual(parcial["Arroz 5 kg"]["links"], {"merc-mercado-do-bairro": lj.base + "/mb/ofertas"})

    def test_pdf_imagem_texto_e_erros(self):
        S, ha, lj = self.S, self.ha, self.lojas
        self.config()
        ha.responde_ia("encarte", {"ofertas": []})
        lj.paginas["/mb/encarte"] = (200, b"%PDF-1.7 tudo", "application/octet-stream")
        S.ler_encarte(self.loja("/mb/encarte"), {})
        self.assertEqual([a["media_content_type"] for a in ha.chamadas_ia[-1]["attachments"]], ["application/pdf"])
        lj.paginas["/mb/encarte.png"] = (200, PNG, "image/png")
        S.ler_encarte(self.loja("/mb/encarte.png"), {})
        self.assertEqual([a["media_content_type"] for a in ha.chamadas_ia[-1]["attachments"]], ["image/png"])
        lj.paginas["/mb/texto"] = (200, "<p>" + "Leite integral R$ 4,99. " * 20 + "</p>", "text/html")
        S.ler_encarte(self.loja("/mb/texto"), {})
        self.assertNotIn("attachments", ha.chamadas_ia[-1], "só o texto da página")
        self.assertIn("o texto da página de ofertas", ha.chamadas_ia[-1]["instructions"])
        lj.paginas["/mb/vazia"] = (200, "<p>Em breve</p>", "text/html")
        n = len(ha.chamadas_ia)
        with self.assertRaisesRegex(S.ErroBusca, "não achei encarte nem ofertas no site"):
            S.ler_encarte(self.loja("/mb/vazia"), {})
        with self.assertRaisesRegex(S.ErroBusca, r"não consegui abrir o site \(HTTP Error 404"):
            S.ler_encarte(self.loja("/mb/nao-existe"), {})
        self.assertEqual(len(ha.chamadas_ia), n, "sem encarte: não gasta IA")
        ha.regras_ia.clear()
        ha.responde_ia("encarte", {"validade": "2020-01-01", "ofertas": [{"produto": "Café", "preco": 9}]})
        with self.assertRaisesRegex(S.ErroBusca, "o encarte do site é antigo: venceu em 01/01/2020"):
            S.ler_encarte(self.loja("/mb/encarte"), {})

    def test_limites_de_arquivos_e_tamanho(self):
        S, ha, lj = self.S, self.ha, self.lojas
        self.config()
        ha.responde_ia("encarte", {"ofertas": []})
        grande = b"\xff\xd8" + b"\1" * 50000
        imgs = "".join(f'<img src="/mb/p{i}.jpg">' for i in range(8))
        pdfs = "".join(f'<a href="/mb/e{i}.pdf">PDF</a>' for i in range(3))
        lj.paginas["/mb/muitas"] = (200, f"<html><body>{pdfs}{imgs}<img src='/mb/enorme.jpg'></body></html>", "text/html")
        for i in range(8):
            lj.paginas[f"/mb/p{i}.jpg"] = (200, grande, "image/jpeg")
        for i in range(3):
            lj.paginas[f"/mb/e{i}.pdf"] = (200, b"%PDF-1.4 " + bytes([48 + i]), "application/pdf")
        S.ler_encarte(self.loja("/mb/muitas"), {})
        tipos = [a["media_content_type"] for a in ha.chamadas_ia[-1]["attachments"]]
        self.assertEqual(tipos, ["application/pdf", "application/pdf", "image/jpeg", "image/jpeg", "image/jpeg", "image/jpeg"],
                         "até 2 PDFs e 6 arquivos por encarte")
        lj.paginas["/mb/gigante.pdf"] = (200, b"%PDF-1.4 " + b"0" * (3 * 1024 * 1024), "application/pdf")
        with self.assertRaisesRegex(S.ErroBusca, r"não consegui abrir o site \(arquivo grande demais\)"):
            S.ler_encarte(self.loja("/mb/gigante.pdf"), {})

    def test_juntar_encarte_a_categoria(self):
        S = self.S
        dest = categoria("mercados", [("merc-giassi", "Giassi", 1.0)], ofertas=[{"id": "merc-giassi-arroz", "rede": "merc-giassi"}])
        nova = categoria("mercados", [("merc-giassi", "Giassi", None, {"fontes": ["Encarte"], "folheto": "https://f/1", "folheto_ate": "2099-01-01"}),
                                      ("merc-kuntze", "Kuntze", None)],
                         ofertas=[{"id": "merc-giassi-arroz", "rede": "merc-giassi"}, {"id": "merc-kuntze-cafe", "rede": "merc-kuntze"}])
        S.juntar_categoria(dest, nova)
        self.assertEqual([r["id"] for r in dest["redes"]], ["merc-giassi", "merc-kuntze"])
        g = dest["lojas"][0]
        self.assertEqual((g["fontes"], g["folheto"], g["folheto_ate"], g["distancia_km"]), (["Encarte", "Mapa"], "https://f/1", "2099-01-01", 1.0))
        self.assertEqual([o["id"] for o in dest["ofertas"]], ["merc-giassi-arroz", "merc-kuntze-cafe"], "oferta repetida não entra")
