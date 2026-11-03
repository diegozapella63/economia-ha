"""As peças pequenas que as buscas usam: a resposta da IA fora do formato, o JSON escondido no texto, o tipo de cada
chamada no uso da IA, preço e data no jeito brasileiro, o @ do Instagram, os blocos de texto de uma página, o tamanho
das imagens (WebP, PNG, JPEG), os períodos dos folhetos, o robots.txt (o mais específico vale, * e $), o que o teste
de um site diz quando ele não responde, a distância entre palavras e os tamanhos repetidos."""
import struct
import urllib.error

from apoio import Cenario


class FormatoDaIA(Cenario):
    def test_mensagem_conforme_o_trecho(self):
        S = self.S
        self.assertEqual(str(S.ErroFormato()), "A IA respondeu fora do formato esperado.")
        self.assertEqual(str(S.ErroFormato("Não sei   responder\nisso")), 'A IA respondeu fora do formato esperado. Ela disse: "Não sei responder isso"')
        e = S.ErroFormato('{"lojas": [ quebrado')
        self.assertIn("formato que o EconomIA não conseguiu ler", str(e))
        self.assertEqual(len(S.ErroFormato("x" * 500).trecho), 220, "guarda só um trecho")

    def test_json_dentro_do_texto(self):
        S = self.S
        self.assertEqual(S.extrai_json('Aqui está:\n```json\n{"a": 1}\n```\nAbraço'), {"a": 1})
        self.assertEqual(S.extrai_json('Resultado: {"a": [1, 2,], "b": 3,} fim'), {"a": [1, 2], "b": 3}, "vírgula sobrando")
        self.assertEqual(S.extrai_json({"a": 1}), {"a": 1})

    def test_json_como_texto_entre_aspas(self):
        S = self.S
        self.assertEqual(S.extrai_json('"{\\"lojas\\": []}"'), {"lojas": []})
        self.assertEqual(S.extrai_json('A resposta: {\\"lojas\\": [{\\"nome\\": \\"Giassi\\"}]}\nfim'), {"lojas": [{"nome": "Giassi"}]},
                         "aspas escapadas no meio do texto")

    def test_texto_entre_aspas_que_nao_e_json(self):
        S = self.S
        with self.assertRaises(S.ErroFormato) as c:
            S.extrai_json('"Não encontrei ofertas hoje."')
        self.assertIn("Não encontrei ofertas hoje.", c.exception.trecho)

    def test_sem_json_registra_e_avisa(self):
        S = self.S
        with self.assertRaises(S.ErroFormato) as c:
            S.extrai_json("Desculpe, não consegui buscar agora.")
        self.assertEqual(c.exception.trecho, "Desculpe, não consegui buscar agora.")
        self.assertTrue(any("resposta da IA fora do formato: Desculpe" in str(m) for m in self.log))
        with self.assertRaises(S.ErroFormato):
            S.extrai_json("[1, 2, 3]")

    def test_tipo_de_cada_chamada(self):
        S = self.S
        casos = {"EconomIA: teste": "teste", "EconomIA: encarte Giassi": "encarte", "EconomIA: itens sem preço": "itens",
                 "EconomIA: ler cupons": "cupons", "EconomIA: ler lista": "fotos", "EconomIA: falar": "fala",
                 "EconomIA: mercados": "busca", None: "busca"}
        self.assertEqual({k: S.tipo_uso(k) for k in casos}, casos)


class JeitoBrasileiro(Cenario):
    def test_preco_e_data(self):
        S = self.S
        self.assertEqual([S.br_preco(v) for v in (4.5, 1299.9, 1234567.891, 0)], ["R$ 4,50", "R$ 1.299,90", "R$ 1.234.567,89", "R$ 0,00"])
        self.assertEqual(S.br_data("2026-11-03"), "03/11/2026")

    def test_numero_de_texto(self):
        S = self.S
        self.assertEqual([S.numero(v) for v in ("R$ 1.299,90", "12.5", "0", "-3", "abc", None, 7, "R$ 0,00")],
                         [1299.9, 12.5, None, 3.0, None, None, 7.0, None], "o sinal some: '-3' vira 3")

    def test_medida_fora_do_razoavel(self):
        S = self.S
        self.assertEqual(S.medida("500", "g"), (0.5, "kg"))
        self.assertEqual(S.medida(2, "L."), (2.0, "L"))
        self.assertEqual([S.medida(*x) for x in ((0, "kg"), (100000, "g"), ("muito", "kg"), (1, "caixa"), (1, None))], [None] * 5)

    def test_nomes_da_lista_e_similares(self):
        S = self.S
        cfg = {"lista": [{"produto": " Leite "}, "Café", {"produto": ""}, None, {"produto": "Sabão", "similares": True}, {"produto": " ", "similares": True}]}
        self.assertEqual(S.nomes_da_lista(cfg), ["Leite", "Café", "Sabão"])
        self.assertEqual(S.quer_similares(cfg), {"sabao"})
        self.assertEqual(S.nome_item(None), "")


class Instagram(Cenario):
    def test_arroba_da_loja(self):
        S = self.S
        casos = {"https://www.instagram.com/mercado_boidourado/": "mercado_boidourado", "@Mercado.Boi": "mercado.boi",
                 "instagram.com/loja.": "loja", "https://www.instagram.com/p/Cxyz/": None, "https://www.instagram.com/reel/abc": None,
                 "@a": None, "mercado_boi": None, "": None, None: None, "https://www.facebook.com/boi": None}
        self.assertEqual({k: S.insta_handle(k) for k in casos}, casos)

    def test_rede_social(self):
        S = self.S
        self.assertTrue(S.social_loja("https://www.instagram.com/boi/"))
        self.assertIsNone(S.social_loja("https://www.boi.com.br/"))


class Paginas(Cenario):
    def test_blocos_de_texto(self):
        S = self.S
        html = ("<html><head><title>x</title></head><body><script>var a = 'R$ 1,00';</script><style>.a{}</style>"
                "<div><h3>Arroz Tio João 5 kg</h3><del>R$ 29,90</del><span>R$</span><span>21</span><span>,90</span></div>"
                "<p>Feijão &amp; cia</p></body></html>")
        self.assertEqual(S.blocos_da_pagina(html), ["Arroz Tio João 5 kg", "~R$ 29,90~", "R$ 21,90", "Feijão & cia"])

    def test_resumo_da_pagina_vazia(self):
        S = self.S
        self.assertEqual(S.resumo_vazia("", 202, {"Server": "CloudFront"}), "código 202, 0 bytes, servidor CloudFront")
        self.assertEqual(S.resumo_vazia("ç", 200, None), "código 200, 2 bytes")
        self.assertEqual(S.sem_tags("<p>Oi&nbsp;<b>você</b></p>\n<br>tudo"), "Oi você tudo")


class TamanhoDaImagem(Cenario):
    def test_desconhecida_ou_cortada(self):
        S = self.S
        dht = b"\xff\xc4" + struct.pack(">H", 4) + b"\0\0"
        self.assertEqual([S.tamanho_imagem(d) for d in (b"GIF89a" + b"\0" * 30, b"\xff\xd8" + dht + b"\xff\xd9" + b"\0" * 4, b"", b"RIFF\0\0\0\0WEBPVP8Z")],
                         [None] * 4, "GIF, JPEG sem o quadro do tamanho, vazio e WebP de outro tipo")


class Periodos(Cenario):
    def test_por_mes_escrito(self):
        S = self.S
        ano = int(S.hoje_br()[:4])
        self.assertEqual(S.periodo_mes("Ofertas de 30 out. até 10 nov."), (f"{ano}-10-30", f"{ano}-11-10"))
        self.assertEqual(S.periodo_mes("28 dezembro a 3 janeiro"), (f"{ano}-12-28", f"{ano + 1}-01-03"), "vira o ano")
        self.assertEqual(S.periodo_mes("31 fev - 2 mar"), (None, None), "dia que não existe")
        self.assertEqual(S.periodo_mes("sem data"), (None, None))

    def test_por_barras(self):
        S = self.S
        m = S.PERIODO.search("Válido de 30/10 a 05/11/2026")
        self.assertEqual(S.periodo_de(m), ("2026-10-30", "2026-11-05"), "o ano do fim vale para o começo")
        m = S.PERIODO.search("28/12/2025 até 03/01/2026")
        self.assertEqual(S.periodo_de(m), ("2025-12-28", "2026-01-03"))


class Robots(Cenario):
    def test_o_mais_especifico_vale(self):
        S = self.S
        regras = S.robots_regras("User-agent: *\nDisallow: /busca\nAllow: /busca/ofertas\nDisallow: /*.pdf$\nDisallow:\nAllow: /x\nDisallow: /x\n")
        self.assertTrue(S.robots_permite(regras, "/busca/ofertas/hoje"))
        self.assertFalse(S.robots_permite(regras, "/busca?q=leite"))
        self.assertFalse(S.robots_permite(regras, "/encarte/semana.pdf"))
        self.assertTrue(S.robots_permite(regras, "/encarte/semana.pdf?v=2"), "$ é o fim do endereço")
        self.assertTrue(S.robots_permite(regras, "/x"), "empate: Allow vale")
        self.assertTrue(S.robots_permite(regras, "/"), "Disallow vazio não proíbe nada")

    def test_grupos_com_varios_programas(self):
        S = self.S
        txt = "User-agent: Googlebot\nUser-agent: *\nDisallow: /a # comentário\nUser-agent: GPTBot\nDisallow: /\nlinha solta\n"
        self.assertEqual(S.robots_regras(txt), [("disallow", "/a")])
        self.assertEqual(S.robots_regras(None), [])


class TesteDoSite(Cenario):
    def com_erro(self, e):
        S = self.S
        S.pagina_txt = lambda *a, **k: (_ for _ in ()).throw(e)
        return S.testa_site("https://loja.com.br", "89201100")

    def test_cada_erro_explicado(self):
        S = self.S
        casos = [(TimeoutError("timed out"), "demorou demais para responder"),
                 (urllib.error.URLError(ConnectionResetError(104, "Connection reset by peer")), "fechou a conexão sem responder ao EconomIA"),
                 (urllib.error.URLError(OSError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")), "teve erro de conexão segura"),
                 (urllib.error.URLError(OSError("[Errno -2] Name or service not known")), "não foi encontrado"),
                 (ValueError("estranho"), "não respondeu (ValueError: estranho)")]
        for e, msg in casos:
            with self.subTest(msg=msg):
                r = self.com_erro(e)
                self.assertTrue(r["sem_resposta"])
                self.assertTrue(r["erro"].startswith(msg), r["erro"])
        self.assertLess(r["em"], S.agora(), "sem resposta: guardado como velho, para testar de novo amanhã")

    def test_erros_http(self):
        h = lambda c: urllib.error.HTTPError("https://loja.com.br/robots.txt", c, "x", {}, None)  # noqa: E731
        self.assertEqual(self.com_erro(h(403))["erro"], "recusou o acesso de programas (erro 403)")
        self.assertEqual(self.com_erro(h(500))["erro"], "respondeu com erro 500")
        r = self.com_erro(h(404))
        self.assertNotIn("sem_resposta", r)
        self.assertTrue(r["paginas"], "sem robots.txt: pode ler as páginas")


class Palavras(Cenario):
    def test_distancia_com_troca_de_vizinhas(self):
        S = self.S
        d = S._distancia
        self.assertEqual([d("limpeza", "lompeza"), d("leite", "leiet"), d("cafe", "cafe"), d("arroz", "arrozinho"), d("abcdef", "badcfe")],
                         [1, 1, 0, 3, 3], "longe demais para no limite + 1")
        self.assertEqual(S._apagas1("cafe"), {"afe", "cfe", "cae", "caf"})

    def test_cabeca_do_nome(self):
        S = self.S
        S.vocab()["set"].update({"secante", "limpador", "alcool"})
        orig = S.eh_tipo
        S.eh_tipo = lambda w: w in ("secante", "limpador", "alcool", "pao", "leite")
        try:
            self.assertTrue(S.cabeca_bate("secante", ["jimo", "secante", "500ml"]), "a marca antes do tipo")
            self.assertFalse(S.cabeca_bate("alcool", ["limpador", "lavanda", "alcool"]), "outro tipo antes")
            self.assertFalse(S.cabeca_bate("leite", ["marca", "outra", "coisa", "leite"]), "além das 3 primeiras")
            self.assertTrue(S.cabeca_bate("churu", ["petisco", "churu", "atum"]), "item pela marca: basta estar no começo")
            self.assertFalse(S.cabeca_bate("churu", ["pao", "churu"]), "o produto é de outro tipo, que o item nem cita")
            self.assertTrue(S.cabeca_bate("churu", ["pao", "churu"], ["pao"]), "a não ser que o item seja desse tipo")
        finally:
            S.eh_tipo = orig


class Tamanhos(Cenario):
    def test_sem_repetir_fica_o_ultimo(self):
        S = self.S
        t = [{"rede": "a", "quantidade": 1, "preco": 5, "nome": "Leite"}, {"rede": "a", "quantidade": 1.0, "preco": 4, "nome": "LEITE"},
             {"rede": "a", "quantidade": 2, "preco": 9}, {"rede": "a", "quantidade": None, "preco": 1}, "x", {"rede": "b", "quantidade": 1, "preco": 0}]
        self.assertEqual(S.sem_repetir_tamanhos(t), [t[1], t[2]])

    def test_oferta_do_folheto_vira_preco(self):
        S = self.S
        ofs = [{"produto": "Leite Integral Tirol 1L", "preco": "4,99"}, {"produto": "Picanha bovina", "preco": 59.9, "unidade": "kg"},
               {"produto": "Leite em pó", "preco": None}, "x"]
        out = S.precos_por_oferta(ofs, ["Leite integral", "Picanha", "Café"], {"Café"})
        self.assertEqual([x["produto"] for x in out], ["Leite integral", "Picanha"])
        self.assertEqual(out[0]["precos"][0]["preco"], 4.99)
        self.assertEqual(out[1]["base"], {"quantidade": 1.0, "unidade": "kg"}, "por quilo")


class Textos(Cenario):
    def test_entrega_e_lojas_ja_consultadas(self):
        S = self.S
        self.ofertas({"categorias": [{"id": "mercados", "redes": [{"id": "m-a", "nome": "Giassi"}, {"id": "m-b", "nome": "Fort"}],
                                      "lojas": [{"rede": "m-a", "distancia_km": 1.0}, {"rede": "m-b", "distancia_km": 9.0}, "x"]}, "y"]})
        cfg = {"raio_km": 3, "categorias": ["mercados", "online"]}
        t = S.entrega_txt(cfg)
        self.assertIn("procure também supermercados da cidade e da região, inclusive fora do raio de 3 km", t)
        self.assertIn("Não precisa trazer estas lojas, que ficam perto e já são buscadas: Giassi.", t)
        self.assertEqual(S.entrega_txt({"online": {"mercados_entrega": False}}), "")
        self.assertEqual(S.lojas_perto({"raio_km": "x"}), ["Giassi"], "raio inválido: 2 km")
        self.assertEqual(S.lojas_perto_cat({"raio_km": "x"}), {"giassi": "mercados"})
        self.assertEqual(S.categoria_da_loja("Fort Atacadista", S.lojas_perto_cat({"raio_km": 10})), "mercados", "nome parecido com a do bairro")
        self.assertEqual(S.categoria_da_loja("Loja Distante", {"giassi": "mercados"}), "online", "a que não fica no bairro entrega")
        self.assertEqual(S.ja_tenho_txt({"_ja_tenho": {"mercados": ["Giassi", "Angeloni"]}}, "mercados"),
                         "Os preços da lista destas lojas já vieram direto do site delas: Giassi, Angeloni. Não traga preços da lista dessas lojas; procure as outras.")
        self.assertEqual(S.ja_tenho_txt({}, "mercados"), "")
