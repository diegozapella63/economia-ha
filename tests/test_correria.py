"""CorrerIA (o WhatsApp, o Claude e o Gemini) usando o EconomIA pelas ferramentas: o arquivo share/economia/correria.json
(só ligado, permissão do dono, chave própria guardada), a rota /api/integracao/ferramentas (chave, desligado, 404, 400),
cada ferramenta (lista, preço, ofertas, cupons, pôr e tirar da lista, compra e, 1.46.1, a Reposição) com as regras da tela (histórico, nomes
parecidos), o diário que junta a gravação da página com revisão velha, o aviso "pela CorrerIA" e as lojas desligadas em
Online (o marketplace fora da busca e os mercados da região), que não entram nas ofertas."""
import json
import os
import stat
import unittest.mock

from apoio import Cenario, categoria
from test_api_fluxos import Servidor

HOJE = "2026-11-02"

OFERTAS = {"versao": 2, "gerado_em": "2026-11-01T09:00:00-03:00", "categorias": [
    categoria("mercados", [("giassi", "Giassi", 1.0), ("angeloni", "Angeloni", 1.5)],
              ofertas=[{"id": "g1", "rede": "giassi", "produto": "Picanha kg", "preco_normal": 89.9, "preco_oferta": 59.9},
                       {"id": "g2", "rede": "giassi", "produto": "Café Pilão 500 g", "preco_normal": 22.9, "preco_oferta": 19.9},
                       {"id": "a1", "rede": "angeloni", "produto": "Cerveja lata", "preco_normal": 4.0, "preco_oferta": 2.0, "tipo": "clube",
                        "valido_ate": "2026-11-10"},
                       {"id": "a2", "rede": "angeloni", "produto": "Oferta escondida", "preco_normal": 10.0, "preco_oferta": 1.0}],
              cupons=[{"rede": "giassi", "codigo": "VALE10", "beneficio": "R$ 10 de desconto", "condicao": "acima de R$ 150",
                       "valido_ate": "2026-11-30", "status": "confirmado"},
                      {"rede": "giassi", "codigo": "VELHO", "beneficio": "Cupom vencido", "valido_ate": "2026-10-01", "status": "confirmado"}]),
    categoria("online", [("ml", "Mercado Livre", None), ("amazon", "Amazon", None), ("bistek", "Bistek", None, {"regional": True})],
              ofertas=[{"id": "m1", "rede": "ml", "produto": "Detergente Finish 1 kg", "preco_normal": 98.99, "preco_oferta": 48.86, "frete": 15.9},
                       {"id": "z1", "rede": "amazon", "produto": "Café Melitta 500 g", "preco_normal": 25.0, "preco_oferta": 20.0, "frete": 0},
                       {"id": "b1", "rede": "bistek", "produto": "Arroz 5 kg", "preco_normal": 30.0, "preco_oferta": 24.9}])],
    "lista": [{"produto": "Café Pilão 500 g", "precos": {"giassi": 19.9, "angeloni": 21.5}}, {"produto": "Leite integral", "precos": {}}]}


def lista_cfg():
    return [{"produto": "Café Pilão 500 g", "compras": ["2026-10-05", "2026-10-19"]}, {"produto": "Leite integral", "compras": []},
            {"produto": "Leite desnatado", "compras": []}]


class Ferramentas(Cenario):
    def setUp(self):
        super().setUp()
        self.S.hoje_br = lambda: HOJE
        self.prepara()

    def prepara(self, **kw):
        cfg = dict(categorias=["mercados", "online"], raio_km=2, lista=lista_cfg(), ocultas=["a2"], correria=True,
                   historico=[{"produto": "Sabonete Dove", "compras": ["2026-09-01", "2026-10-01"], "saiu": "2026-10-02", "ean": "7891150037356"}],
                   cupons_meus=[{"id": "m1", "rede": "giassi", "beneficio": "20% em Colgate", "valido_ate": "2026-12-01"}],
                   online={"marketplaces": ["mercadolivre"], "mercados_entrega": False})
        cfg.update(kw)
        self.config(**cfg)
        self.ofertas(OFERTAS)

    def usa(self, _nome, **a):
        return self.S.usar_ferramenta(_nome, a, "Claude")

    def test_ler_arquivo_a_foto_da_conversa_lida_como_lista(self):
        """1.50.0: a foto que a pessoa mandou no CorrerIA, lida pela IA daqui (o Ler com IA da lista); nada entra na lista."""
        import base64
        S = self.S
        f = next(x for x in S.FERRAMENTAS_CORRERIA if x["nome"] == "ler_arquivo")
        self.assertEqual((f["grava"], f["apaga"], f["anexo"]), (False, False, ["image/jpeg", "image/png", "image/webp"]))
        foto = {"tipo": "image/jpeg", "nome": "lista.jpg", "b64": "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8" + b"x" * 50).decode()}
        antes = json.dumps(S.ler_config().get("lista"), sort_keys=True)
        self.ha.responde_ia("ler lista", {"itens": [{"produto": "leite integral", "quantidade": "2"}, {"produto": "Sabão em pó", "obs": "o grande"}]})
        txt = S.usar_ferramenta("ler_arquivo", {"dica": "a lista da geladeira"}, "CorrerIA", anexo=foto)
        self.assertEqual(txt, "Na foto (lida pela IA do EconomIA) há 2 itens:\n- Leite integral (2) [já está na lista]\n- Sabão em pó (o grande)\n"
                              "Nada foi posto na lista. Mostre à pessoa e use economia_por_na_lista com os que ela quiser.")
        self.assertEqual(json.dumps(S.ler_config().get("lista"), sort_keys=True), antes, "a lista não muda")
        self.assertFalse([k for k in S.LEITURAS if k.startswith("correria-")], "a leitura não fica guardada")
        with unittest.mock.patch.object(S, "chamar_ai_task", return_value={"itens": []}):
            self.assertIn("não achou nenhum item de compra", S.usar_ferramenta("ler_arquivo", {}, "CorrerIA", anexo=foto))
        with unittest.mock.patch.object(S, "chamar_ai_task", side_effect=S.ErroBusca("A IA está desligada.")):
            with self.assertRaises(S.ErroFerramenta) as cm:
                S.usar_ferramenta("ler_arquivo", {}, "CorrerIA", anexo=foto)
        self.assertIn("não conseguiu ler a foto: A IA está desligada. Diga isso à pessoa, sem inventar", str(cm.exception))
        for anexo, parte in ((None, "Falta a foto"), (dict(foto, tipo="application/pdf"), "PDF, não"), (dict(foto, b64="data:image/jpeg;base64,"), "Falta a foto"),
                             (dict(foto, b64=base64.b64encode(b"x" * (6 * 1024 * 1024 + 1)).decode()), "grande demais")):
            with self.assertRaises(S.ErroFerramenta) as cm:
                S.usar_ferramenta("ler_arquivo", {}, "CorrerIA", anexo=anexo)
            self.assertIn(parte, str(cm.exception))

    def test_o_catalogo(self):
        S = self.S
        nomes = [f["nome"] for f in S.FERRAMENTAS_CORRERIA]
        self.assertEqual(nomes, ["lista", "preco", "ofertas", "roteiro", "cupons", "por_na_lista", "tirar_da_lista", "comprei", "reposicao", "repor", "reposto", "ler_arquivo",
                                 "mudar_item", "nova_lista", "guardar_cupom"])
        self.assertEqual(set(nomes), set(S.FERR_IMPL))
        for f in S.FERRAMENTAS_CORRERIA:
            self.assertRegex(f["nome"], r"^[a-z0-9_]{1,40}$")
            self.assertEqual(f["entrada"]["type"], "object")
            self.assertEqual(set(f) - {"anexo"}, {"nome", "titulo", "descricao", "entrada", "grava", "apaga"})  # 1.50.0: a que recebe a foto leva `anexo`
        self.assertEqual([f["nome"] for f in S.FERRAMENTAS_CORRERIA if f["grava"]], ["por_na_lista", "tirar_da_lista", "comprei", "repor", "reposto", "mudar_item", "nova_lista", "guardar_cupom"])
        self.assertIn("economia_lista", S.CORRERIA_INSTRUCOES)
        self.assertIn("economia_reposicao", S.CORRERIA_INSTRUCOES)

    def test_lista(self):
        t = self.usa("lista")
        self.assertTrue(t.startswith("Lista de compras (3 itens). Preços da última busca, de 01/11/2026."), t)
        self.assertIn("- Café Pilão 500 g: mais barato no Giassi, R$ 19,90 (Angeloni R$ 21,50); comprado 2 vezes, a última em 19/10/2026, "
                      "a cada 14 dias; deve acabar hoje", t)
        self.assertIn("- Leite integral: sem preço na última busca", t)
        self.config(lista=[], categorias=["mercados"], correria=True)
        self.assertEqual(self.usa("lista"), "A lista de compras está vazia.")

    def test_roteiro(self):
        """1.43.0: as lojas acompanhadas e o total da lista em cada loja física (a conta da melhor loja e do Roteiro)."""
        t = self.usa("roteiro")
        self.assertIn("Lojas acompanhadas: ", t)
        self.assertIn("Giassi (1,0 km)", t)
        self.assertIn("Total da lista em cada loja física (de 3 itens;", t)
        self.assertIn("- Giassi: 1 item, R$ 19,90 (2 sem preço nela)", t)
        self.assertIn("- Angeloni: 1 item, R$ 21,50", t)
        self.assertLess(t.index("Giassi:"), t.index("Angeloni:"), "a de menor total primeiro")
        self.assertNotIn("Mercado Livre:", t, "só as lojas físicas no total")
        self.config(lista=[], categorias=["mercados"], correria=True)
        self.assertIn("Nenhum item da lista tem preço nas lojas físicas ainda.", self.usa("roteiro"))

    def test_preco(self):
        t = self.usa("preco", produto="café pilão")
        self.assertIn("Café Pilão 500 g (na lista), da última busca: Giassi R$ 19,90; Angeloni R$ 21,50.", t)
        self.assertIn("Ofertas que batem:\n- Café Pilão 500 g, no Giassi: R$ 19,90 (era R$ 22,90, 13% menos) [Mercados]", t)
        self.assertIn("Leite integral está na lista, mas ficou sem preço na última busca.", self.usa("preco", produto="Leite integral"))
        self.assertEqual(self.usa("preco", produto="Abacaxi"),
                         'Não achei preço de "Abacaxi" na última busca. Com economia_por_na_lista, o preço vem na próxima busca do app.')
        self.assertIn("Ofertas que batem:\n- Picanha kg", self.usa("preco", produto="picanha"), "fora da lista, só as ofertas")
        with self.assertRaisesRegex(self.S.ErroFerramenta, 'Falta "produto"'):
            self.usa("preco")

    def test_ofertas_sem_as_palavras_de_nunca_mostrar(self):
        """1.11.0: uma palavra em Mais › Casa › Nunca mostrar ("cerveja") tira a oferta de qualquer loja, também das
        ferramentas; só no começo de uma palavra do nome, sem acento e maiúscula ou minúscula."""
        self.prepara(perfil={"nunca_produtos": ["CERVEJA", "", 7, "pão"]})
        t = self.usa("ofertas")
        self.assertNotIn("Cerveja", t)
        self.assertIn("Picanha", t, "o resto continua")
        S = self.S
        self.assertTrue(S.nunca_produto({"perfil": {"nunca_produtos": ["energético"]}}, "Energético Lata 473 ml"))
        self.assertTrue(S.nunca_produto({"perfil": {"nunca_produtos": ["Energetico"]}}, "Bebida ENERGÉTICA? não: Kit ENERGÉTICO 2 un"))
        self.assertFalse(S.nunca_produto({"perfil": {"nunca_produtos": ["getico"]}}, "Energético Lata"), "no começo de uma palavra")
        self.assertFalse(S.nunca_produto({"perfil": {}}, "Energético"))
        self.assertFalse(S.nunca_produto(None, "Energético"))

    def test_ofertas_e_filtros(self):
        S = self.S
        t = self.usa("ofertas")
        self.assertTrue(t.startswith("Ofertas (4 de 4, as de maior desconto primeiro):"), t)
        linhas = t.splitlines()[1:]
        self.assertTrue(linhas[0].startswith("- Detergente Finish 1 kg, no Mercado Livre: R$ 48,86 (era R$ 98,99, 51% menos), frete R$ 15,90 [Online]"), linhas)
        self.assertIn("- Cerveja lata, no Angeloni: R$ 2,00 (era R$ 4,00, 50% menos), com o clube da loja, até 10/11/2026 [Mercados]", linhas)
        self.assertNotIn("escondida", t, "a escondida pela pessoa não vai")
        self.assertNotIn("Amazon", t, "o marketplace fora da busca não vai")
        self.assertNotIn("Bistek", t, "os mercados da região com a opção desligada não vão")
        self.assertIn("Picanha", self.usa("ofertas", categoria="mercados", loja="gias"))
        self.assertNotIn("Detergente", self.usa("ofertas", categoria="mercados"))
        self.assertEqual(self.usa("ofertas", busca="café", limite=1).splitlines()[0], "Ofertas (1 de 1, as de maior desconto primeiro):")
        self.assertEqual(len(self.usa("ofertas", limite=2).splitlines()), 3)
        self.assertEqual(self.usa("ofertas", busca="abacaxi"), "Nenhuma oferta com esse filtro nas lojas acompanhadas.")
        with self.assertRaisesRegex(S.ErroFerramenta, "categoria vale: farmacias, mercados, petshops, online"):
            self.usa("ofertas", categoria="padarias")
        with self.assertRaisesRegex(S.ErroFerramenta, "limite é um número"):
            self.usa("ofertas", limite="muitos")
        self.prepara(online={"marketplaces": ["mercadolivre", "amazon"], "mercados_entrega": True})
        t = self.usa("ofertas")
        self.assertIn("Amazon", t)
        self.assertIn("Bistek", t)
        self.assertIn("frete grátis", t)
        self.prepara(categorias=["mercados"])
        self.assertNotIn("[Online]", self.usa("ofertas"), "categoria desligada não vai")

    def test_cupons(self):
        t = self.usa("cupons")
        self.assertEqual(t, "Cupons válidos:\n- Giassi: R$ 10 de desconto (código VALE10) (acima de R$ 150) até 30/11/2026\n"
                            "- Giassi: 20% em Colgate até 01/12/2026, guardado pela pessoa")
        self.config(categorias=["mercados"], correria=True)
        self.ofertas({"categorias": []})
        self.assertEqual(self.usa("cupons"), "Nenhum cupom válido nas lojas acompanhadas.")

    def test_por_na_lista(self):
        S = self.S
        rev = S.ler_config()["rev"]
        self.assertEqual(self.usa("por_na_lista", produto="  Pão   de forma "), "Pus Pão de forma na lista. O preço vem na próxima busca do app.")
        cfg = S.ler_config()
        self.assertEqual(cfg["lista"][-1], {"produto": "Pão de forma", "compras": []})
        self.assertEqual((cfg["rev"], cfg["mudou_por"]), (rev + 1, "CorrerIA"))
        self.assertEqual(S.DIARIO[-1], {"tipo": "novo", "produto": "Pão de forma", "item": {"produto": "Pão de forma", "compras": []}, "rev": rev + 1})
        self.assertEqual(self.usa("por_na_lista", produto="sabonete dove"),
                         "Pus Sabonete Dove na lista, de volta do histórico com 2 compra(s). O preço vem na próxima busca do app.")
        cfg = S.ler_config()
        self.assertEqual(cfg["lista"][-1], {"produto": "Sabonete Dove", "compras": ["2026-09-01", "2026-10-01"], "ean": "7891150037356"})
        self.assertEqual(cfg["historico"], [], "sai do histórico")
        self.assertEqual(self.usa("por_na_lista", produto="LEITE INTEGRAL"), "Leite integral já está na lista.")
        self.assertEqual(S.ler_config()["rev"], rev + 2, "nada mudou: nem grava")
        with self.assertRaisesRegex(S.ErroFerramenta, 'Falta "produto"'):
            self.usa("por_na_lista", produto="x")
        self.assertTrue(os.listdir(os.path.join(S.DATA, "versoes")), "guarda a versão anterior antes de gravar")

    def test_por_na_lista_com_listas_prontas(self):
        """1.27.0: com as listas prontas ligadas, todo item fica numa lista: a dita, ou a única."""
        S = self.S
        lc = lista_cfg()
        lc[0]["listas"] = ["sem"]
        self.prepara(opcoes={"listas": True}, listas=[], lista=lc)
        with self.assertRaisesRegex(S.ErroFerramenta, r"ainda não há nenhuma: crie uma no app \(Minha lista › \+ Nova\)"):
            self.usa("por_na_lista", produto="Pão de forma")
        self.prepara(opcoes={"listas": True}, listas=[{"id": "sem", "nome": "Compra semanal"}], lista=lc)
        self.assertEqual(self.usa("por_na_lista", produto="Pão de forma"), "Pus Pão de forma na lista Compra semanal. O preço vem na próxima busca do app.")
        self.assertEqual(S.ler_config()["lista"][-1], {"produto": "Pão de forma", "compras": [], "listas": ["sem"]}, "a única lista")
        self.prepara(opcoes={"listas": True}, listas=[{"id": "sem", "nome": "Compra semanal"}, {"id": "men", "nome": "Compra mensal"}], lista=lc)
        with self.assertRaisesRegex(S.ErroFerramenta, r"Diga em qual lista pôr \(lista\): Compra semanal, Compra mensal\."):
            self.usa("por_na_lista", produto="Pão de forma")
        with self.assertRaisesRegex(S.ErroFerramenta, r"lista vale: Compra semanal, Compra mensal\."):
            self.usa("por_na_lista", produto="Pão de forma", lista="Feira")
        self.assertEqual(self.usa("por_na_lista", produto="Pão de forma", lista="mensal"), "Pus Pão de forma na lista Compra mensal. O preço vem na próxima busca do app.")
        # já na lista, noutra lista pronta: entra também nesta (e a página que estava aberta junta)
        pagina = json.loads(json.dumps(S.ler_config()))
        self.assertEqual(self.usa("por_na_lista", produto="café pilão 500 g", lista="Compra mensal"), "Pus Café Pilão 500 g na lista Compra mensal.")
        self.assertEqual(S.ler_config()["lista"][0]["listas"], ["sem", "men"])
        self.assertEqual(S.DIARIO[-1], {"tipo": "lista", "produto": "Café Pilão 500 g", "lista": "men", "rev": S.ler_config()["rev"]})
        S.aplicar_diario(pagina, S.DIARIO[-1])
        self.assertEqual(pagina["lista"][0]["listas"], ["sem", "men"])
        self.assertEqual(self.usa("por_na_lista", produto="Café Pilão 500 g", lista="Compra semanal"), "Café Pilão 500 g já está na lista Compra semanal.")
        # economia_lista diz em qual lista está cada item
        t = self.usa("lista")
        self.assertIn("Listas prontas: Compra semanal, Compra mensal.", t)
        self.assertIn("- Café Pilão 500 g: em Compra semanal e Compra mensal; mais barato no Giassi", t)
        self.assertIn("- Leite integral: sem lista; sem preço na última busca", t)
        self.prepara(opcoes={"listas": True}, listas=[], lista=lc)
        self.assertIn("Listas prontas: nenhuma ainda.", self.usa("lista"))
        self.prepara(opcoes={"listas": False}, listas=[{"id": "sem", "nome": "Compra semanal"}], lista=lc)
        self.assertEqual(self.usa("por_na_lista", produto="Pão de forma"), "Pus Pão de forma na lista. O preço vem na próxima busca do app.", "desligadas: como antes")
        self.assertNotIn("Listas prontas", self.usa("lista"))

    def test_tirar_da_lista(self):
        S = self.S
        self.assertEqual(self.usa("tirar_da_lista", produto="cafe pilao"), "Tirei Café Pilão 500 g da lista. Ficou no histórico, com as compras.")
        cfg = S.ler_config()
        self.assertEqual([i["produto"] for i in cfg["lista"]], ["Leite integral", "Leite desnatado"])
        self.assertEqual(cfg["historico"][-1], {"produto": "Café Pilão 500 g", "compras": ["2026-10-05", "2026-10-19"], "saiu": HOJE})
        self.assertEqual(S.DIARIO[-1]["tipo"], "saiu")
        with self.assertRaisesRegex(S.ErroFerramenta, '"leite" bate com mais de um item da lista: Leite integral; Leite desnatado. Use o nome inteiro.'):
            self.usa("tirar_da_lista", produto="leite")
        with self.assertRaisesRegex(S.ErroFerramenta, '"Abacaxi" não está na lista'):
            self.usa("tirar_da_lista", produto="Abacaxi")
        self.usa("por_na_lista", produto="Café Pilão 500 g")
        self.usa("comprei", produto="Café Pilão 500 g")
        self.usa("tirar_da_lista", produto="Café Pilão 500 g")
        h = [x for x in S.ler_config()["historico"] if x["produto"] == "Café Pilão 500 g"]
        self.assertEqual((len(h), h[0]["compras"]), (1, ["2026-10-05", "2026-10-19", HOJE]), "de novo no histórico: junta as compras")
        # 1.30.0: os similares ligados vão e voltam com o item
        cfg = S.ler_config()
        cfg["lista"][0]["similares"] = True
        S.gravar_config(cfg)
        nome = cfg["lista"][0]["produto"]
        self.usa("tirar_da_lista", produto=nome)
        self.assertTrue(next(x for x in S.ler_config()["historico"] if x["produto"] == nome).get("similares"))
        self.usa("por_na_lista", produto=nome)
        self.assertIs(next(x for x in S.ler_config()["lista"] if x["produto"] == nome).get("similares"), True)
        self.usa("tirar_da_lista", produto=nome)
        cfg = S.ler_config()
        next(x for x in cfg["historico"] if x["produto"] == nome)["similares"] = True
        cfg["lista"].append({"produto": nome, "compras": []})
        S.gravar_config(cfg)
        self.usa("tirar_da_lista", produto=nome)
        self.assertNotIn("similares", next(x for x in S.ler_config()["historico"] if x["produto"] == nome), "saiu sem similares: o histórico também")

    def test_comprei(self):
        S = self.S
        self.assertEqual(self.usa("comprei", produto="Café Pilão 500 g"), "Anotei a compra de Café Pilão 500 g em 02/11/2026; deve acabar em 14 dia(s).")
        self.assertEqual(S.ler_config()["lista"][0]["compras"], ["2026-10-05", "2026-10-19", HOJE])
        self.assertEqual(self.usa("comprei", produto="Café Pilão 500 g"), "A compra de Café Pilão 500 g em 02/11/2026 já estava anotada.")
        self.assertEqual(self.usa("comprei", produto="leite integral", data="2026-10-30"), "Anotei a compra de Leite integral em 30/10/2026.")
        for ruim in ("2026-11-03", "ontem", "2026-13-01"):
            with self.assertRaisesRegex(S.ErroFerramenta, "data vale AAAA-MM-DD, até hoje"):
                self.usa("comprei", produto="Leite integral", data=ruim)
        self.config(lista=["Pão francês"], correria=True)
        self.usa("comprei", produto="pão francês")
        self.assertEqual(S.ler_config()["lista"], [{"produto": "Pão francês", "compras": [HOJE]}], "item antigo em texto vira item")

    def test_diario_junta_a_gravacao_da_pagina(self):
        """A página abriu antes: a gravação dela (revisão velha) não perde o que a CorrerIA fez."""
        S = self.S
        pagina = json.loads(json.dumps(S.ler_config()))
        self.usa("por_na_lista", produto="Sabonete Dove")
        self.usa("tirar_da_lista", produto="Leite desnatado")
        self.usa("comprei", produto="Leite integral")
        for d in [x for x in S.DIARIO if x["rev"] > pagina["rev"]]:
            S.aplicar_diario(pagina, d)
        self.assertEqual([i["produto"] for i in pagina["lista"]], ["Café Pilão 500 g", "Leite integral", "Sabonete Dove"])
        self.assertEqual(pagina["lista"][1]["compras"], [HOJE])
        self.assertEqual([h["produto"] for h in pagina["historico"]], ["Leite desnatado"], "o Sabonete sai e o Leite desnatado entra")

    def test_mudar_item_nova_lista_e_cupom(self):
        """1.51.0 (o dono: "todas"): a quantidade e o setor, a lista pronta nova e o cupom guardado, com o diário."""
        S = self.S
        pagina = json.loads(json.dumps(S.ler_config()))
        self.assertEqual(self.usa("mudar_item", produto="leite integral", quantidade=3, setor="farmacia"), "Leite integral: 3 unidades, comprar na farmácia.")
        it = S.ler_config()["lista"][1]
        self.assertEqual((it["qtd"], it["setor"]), (3, "farmacias"))
        self.usa("mudar_item", produto="Leite integral", quantidade=1)
        self.assertNotIn("qtd", S.ler_config()["lista"][1], "1 é o padrão: sai")
        for args, erro in (({"produto": "Leite integral"}, "quantidade, setor ou lista"), ({"produto": "Leite integral", "quantidade": 0}, "de 1 a 99"),
                           ({"produto": "Leite integral", "setor": "padaria"}, "mercado, farmacia, petshop ou automatico"),
                           ({"produto": "Leite integral", "lista": "Semanal"}, "listas prontas estão desligadas"), ({"produto": "Leite"}, "mais de um item")):
            with self.assertRaisesRegex(S.ErroFerramenta, erro):
                self.usa("mudar_item", **args)
        with self.assertRaisesRegex(S.ErroFerramenta, "listas prontas estão desligadas"):
            self.usa("nova_lista", nome="Churrasco")
        self.prepara(opcoes={"listas": True}, listas=[{"id": "sem", "nome": "Compra semanal"}])
        pagina = json.loads(json.dumps(S.ler_config()))
        self.assertTrue(self.usa("nova_lista", nome="Churrasco").startswith("Lista pronta criada: Churrasco."))
        self.assertEqual([x["nome"] for x in S.ler_config()["listas"]], ["Compra semanal", "Churrasco"])
        with self.assertRaisesRegex(S.ErroFerramenta, "Já tem uma lista"):
            self.usa("nova_lista", nome="churrasco")
        self.assertEqual(self.usa("por_na_lista", produto="Picanha", lista="Churrasco"), "Pus Picanha na lista Churrasco. O preço vem na próxima busca do app.")
        t = self.usa("guardar_cupom", loja="giassi", beneficio="15% em carnes", codigo="CARNE15", valido_ate="2026-11-20")
        self.assertEqual(t, "Cupom guardado: Giassi, 15% em carnes (código CARNE15), até 20/11/2026.")
        self.assertIn("15% em carnes", self.usa("cupons"))
        with self.assertRaisesRegex(S.ErroFerramenta, "já está guardado"):
            self.usa("guardar_cupom", loja="Giassi", beneficio="15% em carnes", codigo="CARNE15")
        with self.assertRaisesRegex(S.ErroFerramenta, "Loja não encontrada: Padaria. As lojas acompanhadas: "):
            self.usa("guardar_cupom", loja="Padaria", beneficio="x")
        with self.assertRaisesRegex(S.ErroFerramenta, "valido_ate"):
            self.usa("guardar_cupom", loja="Giassi", beneficio="y", valido_ate="amanhã")
        self.usa("mudar_item", produto="Café Pilão 500 g", setor="mercado", quantidade=2)
        # 1.54.0: o Mover para a lista e o Automático do Selecionar
        self.assertEqual(self.usa("mudar_item", produto="Picanha", lista="Compra semanal"), "Picanha: na lista Compra semanal.")
        self.assertEqual(next(i for i in S.ler_config()["lista"] if i["produto"] == "Picanha")["listas"], ["sem"], "sai das outras")
        with self.assertRaisesRegex(S.ErroFerramenta, "lista vale: Compra semanal, Churrasco"):
            self.usa("mudar_item", produto="Picanha", lista="Feira")
        self.usa("mudar_item", produto="Leite integral", setor="farmacia")
        self.assertEqual(self.usa("mudar_item", produto="Leite integral", setor="automatico"), "Leite integral: onde comprar automático.")
        self.assertNotIn("setor", next(i for i in S.ler_config()["lista"] if i["produto"] == "Leite integral"))
        # a página que estava aberta junta tudo ao gravar
        for d in [x for x in S.DIARIO if x["rev"] > pagina["rev"]]:
            S.aplicar_diario(pagina, d)
        self.assertEqual([x["nome"] for x in pagina["listas"]], ["Compra semanal", "Churrasco"])
        self.assertEqual(pagina["cupons_meus"][-1]["beneficio"], "15% em carnes")
        cafe = next(i for i in pagina["lista"] if i["produto"] == "Café Pilão 500 g")
        self.assertEqual((cafe["qtd"], cafe["setor"]), (2, "mercados"))
        self.assertEqual(next(i for i in pagina["lista"] if i["produto"] == "Picanha")["listas"], ["sem"])
        self.assertNotIn("setor", next(i for i in pagina["lista"] if i["produto"] == "Leite integral"))

    # ----- 1.46.1: a Reposição (HOJE é 2026-11-02) -----
    REPOR = [{"id": "aaaa1", "nome": "Filtro de água", "cada": 6, "unidade": "mes", "desde": "2026-04-30"},
             {"id": "bbbb2", "nome": "Ração 15 kg", "cada": 30, "unidade": "dia", "desde": "2026-10-20"},
             {"id": "cccc3", "nome": "Vitamina D", "cada": 2, "unidade": "semana", "desde": "2026-10-19", "origem": "cronologia"},
             {"id": "dddd4", "nome": "Pilhas AA", "cada": "muitas", "unidade": "ano", "desde": "2026-11-01", "origem": "inventario"},
             {"nome": "", "cada": 1}, {"id": "eeee5", "nome": "Sem data", "cada": 1}, "torto"]

    def test_reposicao(self):
        self.assertEqual(self.usa("reposicao"), "A Reposição está vazia.")
        self.prepara(reposicao=json.loads(json.dumps(self.REPOR)))
        self.assertEqual(self.usa("reposicao").split("\n"), [
            "Reposição (4 itens; 2 na hora de repor).",
            "- Filtro de água: a cada 6 meses; na hora de repor, desde 30/10/2026",
            "- Vitamina D (remédio do CronologIA): a cada 2 semanas; na hora de repor",
            "- Ração 15 kg: a cada 30 dias; volta em 19/11/2026",
            "- Pilhas AA (consumível do InventarIA): a cada 30 dias; volta em 01/12/2026"])
        self.assertEqual(self.S.ler_config()["reposicao"], self.REPOR, "ler não grava nada")

    def test_reposicao_os_meses_pelo_calendario(self):
        prox = lambda desde, n, un="mes": self.S.repor_proxima({"desde": desde, "cada": n, "unidade": un})
        self.assertEqual([prox("2026-01-31", 1), prox("2026-08-31", 6), prox("2026-11-15", 2), prox("2026-12-31", 12), prox("2024-01-31", 1)],
                         ["2026-02-28", "2027-02-28", "2027-01-15", "2027-12-31", "2024-02-29"])
        self.assertEqual([prox("2026-12-25", 1, "semana"), prox("2026-12-25", 10, "dia")], ["2027-01-01", "2027-01-04"])

    def test_repor(self):
        S = self.S
        self.prepara(reposicao=json.loads(json.dumps(self.REPOR)))
        rev = S.ler_config()["rev"]
        self.assertEqual(self.usa("repor", item="Sabão em pó", a_cada=3, unidade="semanas"), "Pus Sabão em pó na Reposição, a cada 3 semanas: volta em 23/11/2026.")
        c = S.ler_config()
        novo = c["reposicao"][-1]
        self.assertEqual((c["rev"], c["mudou_por"], {k: v for k, v in novo.items() if k != "id"}),
                         (rev + 1, "CorrerIA", {"nome": "Sabão em pó", "cada": 3, "unidade": "semana", "desde": HOJE}))
        self.assertRegex(novo["id"], r"^r[0-9a-f]{8}$")
        self.assertEqual(len(c["reposicao"]), 5, "o que não valia (sem nome, sem data) sai ao gravar")
        # o mesmo item com outro intervalo: muda, e o tempo continua de onde estava
        self.assertEqual(self.usa("repor", item="ração 15 KG", a_cada=1, unidade="meses"), "Ração 15 kg agora volta a cada 1 mês: a próxima em 20/11/2026.")
        r = next(x for x in S.ler_config()["reposicao"] if x["id"] == "bbbb2")
        self.assertEqual((r["cada"], r["unidade"], r["desde"]), (1, "mes", "2026-10-20"))
        self.assertEqual(self.usa("repor", item="Ração 15 kg", a_cada=1, unidade="mês"), "Ração 15 kg já está na Reposição, a cada 1 mês.")
        self.assertEqual(self.usa("repor", item="Fio dental", a_cada=45), "Pus Fio dental na Reposição, a cada 45 dias: volta em 17/12/2026.", "sem a unidade, dias")
        self.assertEqual(S.ler_config()["rev"], rev + 3, "o que não mudou não grava")
        for ruim in ({"item": "Fio", "a_cada": 0}, {"item": "Fio", "a_cada": 366}, {"item": "Fio", "a_cada": "x"}, {"item": "Fio", "a_cada": True},
                     {"item": "Fio", "a_cada": 2, "unidade": "anos"}, {"item": "Fio"}):
            with self.assertRaises(S.ErroFerramenta) as e:
                self.usa("repor", **ruim)
            self.assertEqual(str(e.exception), "a_cada vale de 1 a 365, e unidade, dias, semanas ou meses.", ruim)
        with self.assertRaises(S.ErroFerramenta):
            self.usa("repor", item="", a_cada=2)
        self.prepara(reposicao=[{"id": f"r{i:04d}", "nome": f"Item {i}", "cada": 1, "unidade": "dia", "desde": HOJE} for i in range(200)])
        with self.assertRaises(S.ErroFerramenta) as e:
            self.usa("repor", item="Mais um", a_cada=2)
        self.assertEqual(str(e.exception), "A Reposição chegou a 200 itens.")

    def test_reposto(self):
        S = self.S
        self.prepara(reposicao=json.loads(json.dumps(self.REPOR)), sync={"ativo": True, "entidade": "todo.compras"})
        self.assertEqual(self.usa("reposto", item="filtro"), "Filtro de água: a contagem recomeçou hoje; volta em 02/05/2027.")
        self.assertEqual(next(x for x in S.ler_config()["reposicao"] if x["id"] == "aaaa1")["desde"], HOJE)
        self.assertEqual(self.usa("reposto", item="Filtro de água"), "A contagem de Filtro de água já começou hoje: volta em 02/05/2027.")
        self.assertIn("1 na hora de repor", self.usa("reposicao"))
        for nome, msg in (("Arroz", '"Arroz" não está na Reposição. Veja os nomes em economia_reposicao.'),
                          ("a", 'Falta "item": o nome do produto, como "Café Pilão 500 g".')):
            with self.assertRaises(S.ErroFerramenta) as e:
                self.usa("reposto", item=nome)
            self.assertEqual(str(e.exception), msg)
        self.prepara(reposicao=[dict(self.REPOR[0]), dict(self.REPOR[0], id="ffff6", nome="Filtro do ar")])
        with self.assertRaises(S.ErroFerramenta) as e:
            self.usa("reposto", item="filtro")
        self.assertEqual(str(e.exception), '"filtro" bate com mais de um item: Filtro de água, Filtro do ar. Veja os nomes em economia_reposicao.')

    def test_reposicao_o_diario_junta_a_gravacao_da_pagina(self):
        """A página abriu antes: a gravação dela (revisão velha) não perde o que a CorrerIA fez na Reposição."""
        S = self.S
        self.prepara(reposicao=json.loads(json.dumps(self.REPOR[:3])))
        pagina = json.loads(json.dumps(S.ler_config()))
        self.usa("repor", item="Sabão em pó", a_cada=3, unidade="semanas")
        self.usa("reposto", item="Vitamina D")
        self.usa("repor", item="Ração 15 kg", a_cada=45)
        pagina["reposicao"] = [r for r in pagina["reposicao"] if r["id"] != "aaaa1"]  # enquanto isso, a pessoa apagou o filtro na tela
        for d in [x for x in S.DIARIO if x["rev"] > pagina["rev"]]:
            S.aplicar_diario(pagina, d)
        self.assertEqual(sorted((r["nome"], r["cada"], r["unidade"], r["desde"], r.get("origem")) for r in pagina["reposicao"]),
                         [("Ração 15 kg", 45, "dia", "2026-10-20", None), ("Sabão em pó", 3, "semana", HOJE, None), ("Vitamina D", 2, "semana", HOJE, "cronologia")])
        sem = {"lista": []}
        S.aplicar_diario(sem, next(x for x in S.DIARIO if x["tipo"] == "repor"))
        self.assertEqual([r["nome"] for r in sem["reposicao"]], ["Sabão em pó"], "numa configuração sem a Reposição")

    def test_arquivo_para_o_correria(self):
        S = self.S
        S.publicar_correria()
        with open(S.CORRERIA_ARQ, encoding="utf-8") as f:
            a = json.load(f)
        self.assertEqual(stat.S_IMODE(os.stat(S.CORRERIA_ARQ).st_mode), 0o600)
        self.assertEqual({k: a[k] for k in ("app", "nome", "ferramentas")}, {"app": "economia", "nome": "EconomIA", "ferramentas": "/api/integracao/ferramentas"})
        self.assertEqual(a["versao"], S.Painel.server_version.split("/")[1])
        self.assertTrue(a["url"].startswith("http://") and a["url"].endswith(f":{S.PORT}"), a["url"])
        self.assertGreaterEqual(len(a["chave"]), 32)
        self.assertNotIn("rota", a, "sem conversa pela IA daqui: só as ferramentas")
        chave = a["chave"]
        S.publicar_correria()
        with open(S.CORRERIA_ARQ, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["chave"], chave, "a chave fica guardada")
        self.assertEqual(stat.S_IMODE(os.stat(S.CORRERIA_CHAVE).st_mode), 0o600)
        os.environ["OFERTAS_URL_INTERNA"] = "http://economia.local:8099/"
        try:
            self.assertEqual(S.correria_endereco(), ("http://economia.local:8099", None))
        finally:
            os.environ.pop("OFERTAS_URL_INTERNA")
        self.config(correria=False)
        S.publicar_correria()
        self.assertFalse(os.path.exists(S.CORRERIA_ARQ), "desligado: o arquivo some")
        S.publicar_correria()  # desligado e sem arquivo: nada
        S.SHARE = S.CORRERIA_ARQ = "/proc/nao-pode/correria.json"
        self.config(correria=True)
        S.publicar_correria()
        self.assertTrue(any("CorrerIA: não consegui gravar" in m for m in self.log))


class FerramentasPelaAPI(Servidor):
    def chave(self):
        with open(os.path.join(self.pasta, "share", "correria.json"), encoding="utf-8") as f:
            return json.load(f)["chave"]

    def ferr(self, metodo="GET", corpo=None, chave=None):
        cab = {"Authorization": "Bearer " + (chave if chave is not None else self.chave()), "X-App": "CorrerIA"}
        return self.pede(metodo, "/api/integracao/ferramentas", corpo, cab=cab)

    def test_rota(self):
        st, d = self.pede("GET", "/api/integracao/ferramentas")
        self.assertEqual((st, d["erro"]), (401, "Chave inválida ou CorrerIA desligado no EconomIA."))
        self.config(lista=[{"produto": "Café Pilão 500 g", "compras": []}], correria=True)
        self.assertTrue(os.path.exists(os.path.join(self.pasta, "share", "correria.json")), "ligar grava o arquivo")
        self.assertEqual(self.ferr(chave="errada")[0], 401)
        self.assertEqual(self.pede("GET", "/api/integracao/ferramentas", cab={"Authorization": "Basic x"})[0], 401)
        st, d = self.ferr()
        self.assertEqual(st, 200)
        self.assertEqual(len(d["ferramentas"]), 15)
        self.assertIn("economia_lista", d["instrucoes"])
        st, d = self.ferr("POST", {"nome": "por_na_lista", "argumentos": {"produto": "Pão de forma"}, "pessoa": {"id": "p1", "nome": "Ana"}, "cliente": "Claude"})
        self.assertEqual((st, d), (200, {"texto": "Pus Pão de forma na lista. O preço vem na próxima busca do app."}))
        st, est = self.pede("GET", "/api/estado")
        self.assertEqual([i["produto"] for i in est["config"]["lista"]], ["Café Pilão 500 g", "Pão de forma"])
        self.assertEqual(est["config"]["mudou_por"], "CorrerIA")
        self.assertEqual((est["correria"]["ligada"], est["correria"]["ultimo"]["app"], est["correria"]["ultimo"]["nome"]), (True, "Claude", "por_na_lista"))
        st, d = self.ferr("POST", {"nome": "lista"})
        self.assertIn("- Pão de forma: sem preço na última busca", d["texto"])
        self.assertEqual(self.ferr("POST", {"nome": "apagar_tudo"})[0], 404)
        st, d = self.ferr("POST", {"nome": "tirar_da_lista", "argumentos": {"produto": "Abacaxi"}})
        self.assertEqual(st, 400)
        self.assertIn("não está na lista", d["erro"])
        self.assertEqual(self.ferr("POST", [1, 2])[0], 400)
        # a página gravou com a revisão de antes: junta o que a CorrerIA fez
        rev_velha = est["config"]["rev"] - 1
        st, d = self.pede("PUT", "/api/config", dict(est["config"], rev=rev_velha, lista=[{"produto": "Café Pilão 500 g", "compras": []}], mudou_por=None))
        self.assertEqual((st, d["mesclado"]), (200, True))
        self.assertIn("Pão de forma", [i["produto"] for i in d["config"]["lista"]])
        # 1.46.1: a Reposição pela rota, e a página com a revisão de antes junta também
        antes = d["config"]
        st, d = self.ferr("POST", {"nome": "repor", "argumentos": {"item": "Filtro de água", "a_cada": 6, "unidade": "meses"}, "cliente": "WhatsApp"})
        self.assertEqual(st, 200)
        self.assertIn("Pus Filtro de água na Reposição, a cada 6 meses", d["texto"])
        st, d = self.ferr("POST", {"nome": "repor", "argumentos": {"item": "Filtro de água", "a_cada": 900}})
        self.assertEqual((st, d["erro"]), (400, "a_cada vale de 1 a 365, e unidade, dias, semanas ou meses."))
        self.assertIn("- Filtro de água: a cada 6 meses; volta em", self.ferr("POST", {"nome": "reposicao"})[1]["texto"])
        st, d = self.pede("PUT", "/api/config", dict(antes, mudou_por=None))
        self.assertEqual((st, d["mesclado"], [r["nome"] for r in d["config"]["reposicao"]]), (200, True, ["Filtro de água"]))
        self.assertNotIn("mudou_por", d["config"], "gravado pela página: o aviso some")
        # desligar: o arquivo some e a rota fecha
        self.config(correria=False)
        self.assertFalse(os.path.exists(os.path.join(self.pasta, "share", "correria.json")))
        self.assertEqual(self.pede("GET", "/api/integracao/ferramentas", cab={"Authorization": "Bearer x"})[0], 401)
