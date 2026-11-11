"""CorrerIA (o WhatsApp, o Claude e o Gemini) usando o EconomIA pelas ferramentas: o arquivo share/economia/correria.json
(só ligado, permissão do dono, chave própria guardada), a rota /api/integracao/ferramentas (chave, desligado, 404, 400),
cada ferramenta (lista, preço, ofertas, cupons, pôr e tirar da lista, compra) com as regras da tela (histórico, nomes
parecidos), o diário que junta a gravação da página com revisão velha, o aviso "pela CorrerIA" e as lojas desligadas em
Online (o marketplace fora da busca e os mercados da região), que não entram nas ofertas."""
import json
import os
import stat

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

    def usa(self, nome, **a):
        return self.S.usar_ferramenta(nome, a, "Claude")

    def test_o_catalogo(self):
        S = self.S
        nomes = [f["nome"] for f in S.FERRAMENTAS_CORRERIA]
        self.assertEqual(nomes, ["lista", "preco", "ofertas", "cupons", "por_na_lista", "tirar_da_lista", "comprei"])
        self.assertEqual(set(nomes), set(S.FERR_IMPL))
        for f in S.FERRAMENTAS_CORRERIA:
            self.assertRegex(f["nome"], r"^[a-z0-9_]{1,40}$")
            self.assertEqual(f["entrada"]["type"], "object")
            self.assertEqual(set(f), {"nome", "titulo", "descricao", "entrada", "grava", "apaga"})
        self.assertEqual([f["nome"] for f in S.FERRAMENTAS_CORRERIA if f["grava"]], ["por_na_lista", "tirar_da_lista", "comprei"])
        self.assertIn("economia_lista", S.CORRERIA_INSTRUCOES)

    def test_lista(self):
        t = self.usa("lista")
        self.assertTrue(t.startswith("Lista de compras (3 itens). Preços da última busca, de 01/11/2026."), t)
        self.assertIn("- Café Pilão 500 g: mais barato no Giassi, R$ 19,90 (Angeloni R$ 21,50); comprado 2 vezes, a última em 19/10/2026, "
                      "a cada 14 dias; deve acabar hoje", t)
        self.assertIn("- Leite integral: sem preço na última busca", t)
        self.config(lista=[], categorias=["mercados"], correria=True)
        self.assertEqual(self.usa("lista"), "A lista de compras está vazia.")

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
        self.assertEqual(len(d["ferramentas"]), 7)
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
        self.assertNotIn("mudou_por", d["config"], "gravado pela página: o aviso some")
        # desligar: o arquivo some e a rota fecha
        self.config(correria=False)
        self.assertFalse(os.path.exists(os.path.join(self.pasta, "share", "correria.json")))
        self.assertEqual(self.pede("GET", "/api/integracao/ferramentas", cab={"Authorization": "Bearer x"})[0], 401)
