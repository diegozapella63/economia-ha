"""O botão Buscar de ponta a ponta (buscar), com lojas VTEX falsas, o mapa (Overpass) e a IA do HA falso: primeiro o
que não gasta IA, depois uma pergunta por categoria, o preço do site valendo mais, a categoria que falhou mantendo o
resultado anterior, cota (espera e tenta de novo), IA desligada, encarte do site, itens sem preço (busca focada) e a
busca de poucos itens (buscar_itens). O andamento (BUSCA) é conferido no instante em que a IA é chamada."""
import os
import types

from apoio import CEP, Cenario, categoria, prod
from ha_falso import Erro

AVES = "Açougue/Aves"
LISTA = [{"produto": "Coxinha da asa"}, {"produto": "Café Pilão 500 g"}, {"produto": "Dipirona 500 mg"}]


def pagina_mercados(corpo):
    return {"lojas": [{"rede": "Giassi Supermercados", "distancia_km": 1.1, "endereco": "Rua C, 3", "fontes": ["Site", "Encarte"]},
                      {"rede": "Bistek", "distancia_km": 2.4, "horario": "Aberto até 22h", "fontes": ["Site", "Clube"]}],
            "cupons": [{"rede": "Bistek", "codigo": "BIS10", "valor": 10, "beneficio": "R$ 10 de desconto", "oficial": True,
                        "fonte": "https://www.bistek.com.br/cupons"},
                       {"rede": "Bistek", "codigo": "SEMLINK", "beneficio": "sem fonte"}],
            "ofertas": [{"rede": "Bistek", "produto": "Arroz Tio João 5 kg", "preco_normal": 29.9, "preco_oferta": 24.9, "tipo": "promo",
                         "tags": ["alimentos", "inventada"], "fonte": "https://www.bistek.com.br/arroz"}],
            "lista": [{"item": 1, "produto": "Coxinha da asa", "base": {"quantidade": 1, "unidade": "kg"},
                       "precos": [{"rede": "Giassi", "preco": 25.0, "fonte": "https://www.giassi.com.br/coxinha"},
                                  {"rede": "Bistek", "preco": 23.5, "preco_clube": 22.9, "fonte": "https://www.bistek.com.br/coxinha"}]},
                      {"item": 2, "produto": "Café Pilão 500 g", "base": {"quantidade": 500, "unidade": "g"},
                       "precos": [{"rede": "Bistek", "preco": 18.9}]},
                      {"item": 9, "produto": "Coisa que não está na lista", "precos": [{"rede": "Bistek", "preco": 1}]}]}


class Busca(Cenario):
    def setUp(self):
        super().setUp()
        self.lojas.catalogo["giassi"] = [prod("Coxinha da Asa de Frango Resfriada Kg", 21.90, AVES, "kg", 1),
                                         prod("Café Pilão Tradicional 500g", 19.90, "Mercearia/Café")]
        self.lojas.rotas["/overpass"] = lambda p: {"elements": [
            {"type": "node", "lat": -26.3045, "lon": -48.85, "tags": {"name": "Farmácia Bem Estar", "amenity": "pharmacy",
                                                                      "addr:street": "Rua das Flores", "addr:housenumber": "100"}}]}
        self.momentos = []

    def foto(self, resp):
        """Resposta da IA que guarda o andamento da busca e o que já tinha sido pedido às lojas na hora da chamada."""
        def f(corpo):
            self.momentos.append({"task": corpo["task_name"], "busca": dict(self.S.BUSCA),
                                  "vtex": len(self.lojas.pedidos_de("product_search")), "prompt": corpo["instructions"]})
            return resp(corpo) if callable(resp) else resp
        return f

    def test_busca_completa(self):
        S, ha = self.S, self.ha
        self.config(raio_km=5, categorias=["mercados", "farmacias"], lista=LISTA, email="davi@exemplo.com.br")
        self.ofertas({"categorias": [categoria("farmacias", [("farm-antiga", "Farmácia Antiga", 1.0)])], "lista": []})
        ha.responde_ia("EconomIA: mercados", self.foto(pagina_mercados))
        ha.responde_ia("EconomIA: farmacias", self.foto(Erro(500, "Internal Server Error")))
        ha.responde_ia("itens sem preço", self.foto({"lista": [{"item": 1, "produto": "Dipirona 500 mg", "precos": [
            {"rede": "Farmácia Vida", "categoria": "farmacias", "preco": 4.99, "fonte": "https://farmaciavida.com.br/dipirona"}]}]}))
        S.buscar()
        B = S.BUSCA
        self.assertIsNone(B["erro"])
        self.assertFalse(B["rodando"])
        self.assertIsNone(B["etapa"])
        self.assertTrue(B["terminou_em"])
        # a ordem: primeiro os sites (sem IA), depois uma pergunta por categoria, por último os itens sem preço
        self.assertEqual([m["task"] for m in self.momentos], ["EconomIA: mercados", "EconomIA: farmacias", "EconomIA: itens sem preço"])
        m0 = self.momentos[0]
        self.assertGreater(m0["vtex"], 0, "a busca direta no site veio antes da IA")
        self.assertEqual((m0["busca"]["rodando"], m0["busca"]["etapa"], m0["busca"]["atual"], m0["busca"]["total"]), (True, "mercados", 1, 2))
        self.assertEqual((self.momentos[1]["busca"]["etapa"], self.momentos[1]["busca"]["atual"]), ("farmácias", 2))
        self.assertIn("já vieram direto do site delas: Angeloni, Giassi", m0["prompt"])
        self.assertIn("Farmácia Bem Estar (Rua das Flores, 100), 0,5 km", self.momentos[1]["prompt"], "o mapa vai no pedido")
        self.assertIn("1) Dipirona 500 mg", self.momentos[2]["prompt"], "só o item que ficou sem preço")
        self.assertNotIn("Coxinha", self.momentos[2]["prompt"])
        self.assertEqual(B["avisos"], ["Algumas buscas falharam e mantive o resultado anterior: Farmácias: A IA do Home Assistant recusou "
                                       "o pedido (500): Internal Server Error"])
        of = S.ler_json(S.OFERTAS)
        lista = {i["produto"]: i for i in of["lista"]}
        cox = lista["Coxinha da asa"]
        self.assertEqual(cox["precos"]["merc-giassi"], {"preco": 21.9, "obs": "Coxinha 1 kg"}, "o preço do site vale mais que o da busca na web")
        self.assertEqual(cox["precos"]["merc-bistek"], {"preco": 23.5, "clube": 22.9})
        self.assertEqual((cox["vistos"]["merc-giassi"]["via"], cox["vistos"]["merc-bistek"]["via"]), ("site", "web"))
        self.assertEqual(S.valor_total(lista["Café Pilão 500 g"]["precos"]["merc-giassi"]), 19.9)
        self.assertEqual(lista["Dipirona 500 mg"]["precos"], {"farm-farmacia-vida": 4.99})
        self.assertNotIn("Coisa que não está na lista", lista)
        cats = {c["id"]: c for c in of["categorias"]}
        merc = cats["mercados"]
        self.assertEqual([c["codigo"] for c in merc["cupons"]], ["BIS10"], "cupom sem link fica de fora")
        self.assertEqual(merc["ofertas"][0]["tags"], ["alimentos"])
        self.assertEqual({r["nome"] for r in merc["redes"]} >= {"Giassi", "Bistek", "Angeloni"}, True)
        self.assertTrue(any(c["rede"] == "merc-bistek" for c in merc["contas"]), "loja com Clube nas fontes")
        farm = {r["nome"] for r in cats["farmacias"]["redes"]}
        self.assertTrue({"Farmácia Antiga", "Farmácia Bem Estar", "Farmácia Vida"} <= farm, f"a anterior fica, o mapa e a focada entram ({farm})")
        bem = next(l for l in cats["farmacias"]["lojas"] if l["rede"] == "farm-farmacia-bem-estar")
        self.assertEqual((bem["fontes"], bem["distancia_km"]), (["Mapa"], 0.5))
        rel = of["relatorio"]
        self.assertEqual(rel["categorias"]["farmacias"]["ok"], False)
        self.assertEqual(rel["categorias"]["mercados"]["ok"], True)
        self.assertEqual(rel["sem_preco"], [])
        self.assertEqual(rel["chamadas_ia"], 3)
        self.assertEqual(B["chamadas_ia"], 3)
        self.assertEqual(S.uso_resumo()["hoje"]["chamadas"], 3)
        # o e-mail nunca sai do add-on
        self.assertNotIn("@exemplo.com.br", ha.tudo_que_chegou())
        self.assertFalse(any("@exemplo.com.br" in str(p) for p in self.lojas.pedidos))

    def test_cota_espera_e_tenta_de_novo(self):
        S, ha = self.S, self.ha
        self.config(categorias=["mercados"], lista=LISTA[:1], opcoes={"itens_sem_preco": False})
        ha.responde_ia("mercados", Erro(429, "Too Many Requests"), vezes=1)
        ha.responde_ia("mercados", self.foto(pagina_mercados))
        pausas = []
        S.time = types.SimpleNamespace(time=S.time.time, sleep=lambda s: pausas.append((s, S.BUSCA["etapa"])))
        S.ESPERA_COTA = 60
        S.buscar()
        self.assertIsNone(S.BUSCA["erro"])
        self.assertIn((60, "mercados (a IA pediu uma pausa, tentando de novo em 1 minuto)"), pausas)
        self.assertEqual(len(ha.chamadas_ia), 2)
        u = S.uso_resumo()["hoje"]
        self.assertEqual((u["chamadas"], u["cota"]), (2, 1))

    def test_cota_duas_vezes_para_a_busca(self):
        S, ha = self.S, self.ha
        self.config(categorias=["mercados", "farmacias"], lista=LISTA[:1])
        anterior = {"categorias": [categoria("mercados", [("merc-x", "Mercado X", 1.0)])], "lista": [], "gerado_em": "2026-10-01T10:00:00"}
        self.ofertas(anterior)
        ha.responde_ia("mercados", Erro(429, "quota"))
        S.buscar()
        self.assertIn("A cota da IA acabou", S.BUSCA["erro"])
        self.assertEqual([c["task_name"] for c in ha.chamadas_ia], ["EconomIA: mercados"] * 2, "farmácias nem chega a ser perguntada")
        self.assertEqual(S.ler_json(S.OFERTAS)["gerado_em"], "2026-10-01T10:00:00", "o resultado anterior fica")
        self.assertFalse(S.BUSCA["rodando"])

    def test_ia_sem_busca_na_web_para_tudo(self):
        S, ha = self.S, self.ha
        self.config(categorias=["mercados", "farmacias"], lista=LISTA[:1])
        ha.responde_ia("mercados", {"erro": "sem_busca"})
        S.buscar()
        self.assertEqual(S.BUSCA["erro"], S.SEM_BUSCA)
        self.assertEqual(len(ha.chamadas_ia), 1)
        # 1.36.2: o limite de buscas por resposta acabando no meio não é "sem busca": a IA responde com o que achou
        ins = ha.chamadas_ia[0]["instructions"]
        self.assertIn('Se nenhuma busca na web funcionar (a ferramenta não existe), responda apenas {"erro": "sem_busca"}.', ins)
        self.assertIn("Se o limite de buscas acabar no meio, responda com o que já achou.", ins)

    def test_sem_cep(self):
        S = self.S
        self.config(cep="", lista=LISTA)
        S.buscar()
        self.assertEqual(S.BUSCA["erro"], "Salve o CEP em Mais › Casa antes de buscar.")
        self.assertEqual(self.ha.chamadas_ia, [])

    def test_ia_desligada_so_os_sites(self):
        S, ha = self.S, self.ha
        self.config(usar_ia=False, categorias=["mercados"], lista=LISTA)
        S.buscar()
        self.assertEqual(ha.chamadas_ia, [])
        self.assertEqual((S.BUSCA["erro"], S.BUSCA["avisos"], S.BUSCA["chamadas_ia"]), (None, [], 0))
        lista = {i["produto"]: i for i in S.ler_json(S.OFERTAS)["lista"]}
        self.assertEqual({k: S.valor_total(v) for k, v in lista["Coxinha da asa"]["precos"].items()}, {"merc-giassi": 21.9})
        self.assertIn("Dipirona 500 mg", S.ler_json(S.OFERTAS)["relatorio"]["sem_preco"])
        # nenhum site responde: avisa
        self.lojas.regioes.clear()
        S._regioes.clear()
        S.buscar()
        self.assertEqual(S.BUSCA["avisos"], ["Com a IA desligada, nenhum site trouxe preço agora; as lojas foram atualizadas pelo mapa."])

    def test_itens_sem_preco_desligado(self):
        S, ha = self.S, self.ha
        self.config(categorias=["mercados"], lista=LISTA, opcoes={"itens_sem_preco": False})
        ha.responde_ia("mercados", pagina_mercados)
        S.buscar()
        self.assertEqual([c["task_name"] for c in ha.chamadas_ia], ["EconomIA: mercados"])
        self.assertEqual(S.ler_json(S.OFERTAS)["relatorio"]["sem_preco"], ["Dipirona 500 mg"])

    def test_tudo_falhou(self):
        S, ha = self.S, self.ha
        self.lojas.regioes.clear()  # as lojas VTEX não atendem o CEP: nenhum site responde
        self.config(categorias=["mercados"], lista=LISTA)
        ha.responde_ia("mercados", Erro(500, "boom"))
        S.buscar()
        self.assertEqual(S.BUSCA["erro"], "Mercados: A IA do Home Assistant recusou o pedido (500): boom")
        self.assertIsNone(S.ler_json(S.OFERTAS), "nada gravado")


class EncarteDoSite(Cenario):
    IMG = b"\xff\xd8\xff\xe0" + b"\x00" * 60000  # JPEG grande (logos e ícones são pequenos e ficam de fora)

    def setUp(self):
        super().setUp()
        lj = self.lojas
        lj.paginas["/mercadobairro/robots.txt"] = (200, "User-agent: *\nDisallow: /api/\n", "text/plain")
        lj.paginas["/mercadobairro/ofertas"] = (200, '<html><body><h1>Ofertas da semana</h1><img src="logo.png">'
                                                     '<img src="/mercadobairro/encarte-1.jpg"><img data-src="encarte-2.jpg"></body></html>', "text/html")
        lj.paginas["/mercadobairro/encarte-1.jpg"] = (200, self.IMG, "image/jpeg")
        lj.paginas["/mercadobairro/encarte-2.jpg"] = (200, b"\xff\xd8pequeno", "image/jpeg")
        lj.paginas["/mercadobairro/logo.png"] = (200, b"\x89PNG" + b"\0" * 50000, "image/png")
        lj.paginas["/bistek/robots.txt"] = (200, "User-agent: *\nDisallow: /api/\n", "text/plain")
        lj.paginas["/bistek/encarte.pdf"] = (200, b"%PDF-1.4 encarte", "application/pdf")
        self.ha.tarefa_ia("ai_task.claude", "Claude")

    def test_encarte_do_site_cadastrado_e_o_automatico(self):
        S, ha = self.S, self.ha
        base = self.lojas.base
        self.config(categorias=["mercados"], lista=LISTA[:2], ia={"fotos": "ai_task.claude"}, opcoes={"itens_sem_preco": False},
                    lojas={"adicionar": [{"categoria": "mercados", "nome": "Mercado do Bairro, Centro", "site": base + "/mercadobairro/ofertas"}]})
        resp = pagina_mercados(None)
        resp["lojas"].append({"rede": "Bistek Encarte", "distancia_km": 1.0, "site": base + "/bistek/encarte.pdf"})
        ha.responde_ia("EconomIA: mercados", resp)
        anexos = {}

        def encarte(corpo):
            anexos[corpo["task_name"]] = corpo.get("attachments")
            return {"validade": "2099-12-31", "ofertas": [{"produto": "Café Pilão 500 g", "preco": 15.98, "tamanho": {"quantidade": 500, "unidade": "g"}}],
                    "lista": [{"item": 2, "base": {"quantidade": 500, "unidade": "g"}, "precos": [{"preco": 15.98}]}]}
        ha.responde_ia("EconomIA: encarte", encarte)
        S.buscar()
        self.assertIsNone(S.BUSCA["erro"])
        self.assertEqual(sorted(anexos), ["EconomIA: encarte Bistek Encarte", "EconomIA: encarte Mercado do Bairro"])
        tipos = [a["media_content_type"] for a in anexos["EconomIA: encarte Mercado do Bairro"]]
        self.assertEqual(tipos, ["image/jpeg"], "só a imagem grande (o logo e a miniatura ficam de fora)")
        self.assertEqual([a["media_content_type"] for a in anexos["EconomIA: encarte Bistek Encarte"]], ["application/pdf"])
        self.assertTrue(anexos["EconomIA: encarte Mercado do Bairro"][0]["media_content_id"].startswith("media-source://media_source/local/economia/encarte-"))
        self.assertEqual(os.listdir(os.path.join(S.MEDIA, "economia")), [], "as imagens são apagadas depois")
        of = S.ler_json(S.OFERTAS)
        merc = next(c for c in of["categorias"] if c["id"] == "mercados")
        nomes = {r["id"]: r["nome"] for r in merc["redes"]}
        self.assertIn("Mercado do Bairro", nomes.values())
        ofs = [o for o in merc["ofertas"] if o.get("encarte")]
        self.assertTrue(all(o["valido_ate"] == "2099-12-31" and o["tipo"] == "encarte" for o in ofs))
        auto = next(l for l in merc["lojas"] if nomes[l["rede"]] == "Bistek Encarte")
        self.assertTrue(auto.get("encarte_auto"))
        self.assertIn("Encarte", auto["fontes"])
        cafe = next(i for i in of["lista"] if i["produto"] == "Café Pilão 500 g")
        self.assertEqual(cafe["precos"]["merc-mercado-do-bairro"], 15.98)

    def test_encarte_vencido_e_automatico_desligado(self):
        S, ha = self.S, self.ha
        base = self.lojas.base
        self.config(categorias=["mercados"], lista=LISTA[:1], opcoes={"itens_sem_preco": False, "encartes_auto": False},
                    lojas={"adicionar": [{"categoria": "mercados", "nome": "Mercado do Bairro", "site": base + "/mercadobairro/ofertas"}]})
        resp = pagina_mercados(None)
        resp["lojas"].append({"rede": "Bistek Encarte", "distancia_km": 1.0, "site": base + "/bistek/encarte.pdf"})
        ha.responde_ia("EconomIA: mercados", resp)
        ha.responde_ia("EconomIA: encarte", {"validade": "2020-01-31", "ofertas": [{"produto": "Café", "preco": 9}]})
        S.buscar()
        self.assertEqual(S.BUSCA["avisos"], ["Algumas buscas falharam e mantive o resultado anterior: Encarte de Mercado do Bairro: "
                                             "o encarte do site é antigo: venceu em 31/01/2020"])
        self.assertEqual([c["task_name"] for c in ha.chamadas_ia], ["EconomIA: mercados", "EconomIA: encarte Mercado do Bairro"],
                         "automático desligado: o Bistek Encarte não é lido")


class Focada(Cenario):
    def test_categoria_de_cada_preco(self):
        S = self.S
        cats = ["farmacias", "mercados", "petshops", "online"]
        casos = [({"rede": "X", "categoria": "petshops"}, "petshops"), ({"rede": "Amazon"}, "online"), ({"rede": "Loja Y", "frete": 0}, "online"),
                 ({"rede": "Drogaria Z"}, "farmacias"), ({"rede": "Cobasi"}, "petshops"), ({"rede": "Mercado W"}, "mercados")]
        for p, c in casos:
            self.assertEqual(S.categoria_do_preco(p, cats), c, p)
        # 1.16.0: sem Online, um preço online fica fora: antes virava uma "farmácia Amazon"
        for p in ({"rede": "Amazon"}, {"rede": "Loja Y", "frete": 0}, {"rede": "X", "categoria": "online"}):
            self.assertIsNone(S.categoria_do_preco(p, ["farmacias", "mercados"]), p)
        self.assertEqual(S.categoria_do_preco({"rede": "Drogaria Z"}, ["mercados"]), "mercados", "sem farmácias: a física que tiver")
        self.assertIsNone(S.categoria_do_preco({"rede": "Amazon"}, ["online"][:0]))

    def test_pedido_e_resposta(self):
        S, ha = self.S, self.ha
        cfg = self.config(categorias=["mercados", "online"], online={"marketplaces": ["amazon"], "assinaturas": ["melimais"]})
        t = S.instrucoes_focada(cfg, ["Pó lava louça", "Leite"], ["mercados", "online"])
        for trecho in ("1) Pó lava louça; 2) Leite", f"para o CEP {CEP}", "supermercados, hipermercados e atacarejos num raio de 2 km do CEP",
                       "e online em Amazon com entrega no CEP", "mercados que entregam no CEP", "Assinaturas do morador: Meli+",
                       '"categoria" é "mercados", "online"'):
            self.assertIn(trecho, t)
        ha.responde_ia("itens sem preço", {"lista": [
            {"item": 1, "produto": "Pó lava louça", "base": {"quantidade": 1, "unidade": "kg"}, "precos": [
                {"rede": "Bistek", "categoria": "mercados", "preco": 39.9, "obs": "Finish 1 kg", "fonte": "https://bistek.com.br/finish"},
                {"rede": "Amazon", "preco": 35.0, "frete": 0, "prazo_dias": 2, "fonte": "https://amazon.com.br/finish"},
                {"rede": "Mercado Livre", "preco": 33.0, "frete": "carrinho"}]},
            {"item": 2, "produto": "Leite", "precos": [{"rede": "Amazon", "preco": 5.0}]}]})
        out = dict((c["id"], (c, p)) for c, p in S.busca_focada(cfg, ["Pó lava louça", "Leite"], ["mercados", "online"]))
        self.assertEqual(out["mercados"][1]["Pó lava louça"]["precos"], {"merc-bistek": {"preco": 39.9, "obs": "Finish 1 kg"}})
        on = out["online"][1]["Pó lava louça"]["precos"]
        self.assertEqual(on["onli-amazon"], {"preco": 35.0, "frete": 0.0, "prazo_dias": 2})
        self.assertEqual(on["onli-mercado-livre"], {"preco": 33.0, "frete": None, "carrinho": True})
        self.assertNotIn("Leite", out["online"][1], "online sem frete é descartado")

    def test_erros(self):
        S, ha = self.S, self.ha
        cfg = self.config()
        self.assertEqual(S.busca_focada(cfg, [], ["mercados"]), [])
        ha.responde_ia("itens", {"erro": "sem_busca"}, vezes=1)
        with self.assertRaisesRegex(S.ErroBusca, "não usou a busca na web"):
            S.busca_focada(cfg, ["Leite"], ["mercados"])
        ha.responde_ia("itens", Erro(429, "quota"), vezes=1)
        ha.responde_ia("itens", {"lista": []}, vezes=1)
        self.assertEqual(S.busca_focada(cfg, ["Leite"], ["mercados"]), [], "cota: espera e tenta de novo uma vez")
        self.assertEqual(len(ha.chamadas_ia), 3)
        ha.responde_ia("itens", ["lista"], vezes=1)
        with self.assertRaises(S.ErroBusca):
            S.busca_focada(cfg, ["Leite"], ["mercados"])
        ha.responde_ia("itens", {"lista": []})
        S.busca_focada(cfg, [f"Item {i}" for i in range(12)], ["mercados"])
        self.assertIn("8) Item 7", ha.chamadas_ia[-1]["instructions"])
        self.assertNotIn("9) Item 8", ha.chamadas_ia[-1]["instructions"], "até 8 itens por pergunta")


class BuscarItens(Cenario):
    def setUp(self):
        super().setUp()
        cox = prod("Coxinha da Asa de Frango Resfriada Kg", 21.90, AVES, "kg", 1)
        self.lojas.catalogo["giassi"] = [cox, prod("Café Pilão Tradicional 500g", 19.90, "Mercearia/Café")]
        self.lojas.catalogo["angeloni"] = [dict(cox, link="/coxinha-ang/p")]

    def test_ia_so_para_o_que_tem_menos_de_dois_precos(self):
        S, ha = self.S, self.ha
        self.config(categorias=["mercados"], lista=LISTA)
        self.ofertas({"categorias": [], "lista": [{"produto": "Dipirona 500 mg", "precos": {"farm-x": 5.0}}]})
        ha.responde_ia("itens sem preço", {"lista": [{"item": 1, "produto": "Café Pilão 500 g", "precos": [
            {"rede": "Bistek", "categoria": "mercados", "preco": 18.5}]}]})
        S.buscar_itens(["Coxinha da asa", "Café Pilão 500 g"])
        self.assertIsNone(S.BUSCA["erro"])
        self.assertEqual(len(ha.chamadas_ia), 1)
        self.assertIn("1) Café Pilão 500 g", ha.chamadas_ia[0]["instructions"])
        self.assertNotIn("Coxinha", ha.chamadas_ia[0]["instructions"], "a coxinha já tem 2 preços pelos sites")
        lista = {i["produto"]: i for i in S.ler_json(S.OFERTAS)["lista"]}
        self.assertEqual({k: S.valor_total(v) for k, v in lista["Coxinha da asa"]["precos"].items()}, {"merc-giassi": 21.9, "merc-angeloni": 21.9})
        self.assertEqual({k: S.valor_total(v) for k, v in lista["Café Pilão 500 g"]["precos"].items()}, {"merc-bistek": 18.5, "merc-giassi": 19.9})
        self.assertEqual(lista["Dipirona 500 mg"]["precos"], {"farm-x": 5.0}, "o resto do resultado anterior fica")
        self.assertEqual((S.BUSCA["chamadas_ia"], S.BUSCA["rodando"], S.BUSCA["avisos"]), (1, False, []))

    def test_sem_categoria_valida(self):
        S = self.S
        self.config(categorias=["nada"], lista=[{"produto": "Pilha AA"}])
        S.buscar_itens(["Pilha AA"])
        self.assertEqual(S.BUSCA["erro"], "Ligue mercados, farmácias, pet shops ou lojas online em Mais › Lojas.")

    def test_a_ia_falha_e_os_sites_respondem(self):
        S, ha = self.S, self.ha
        self.config(categorias=["mercados"], lista=[{"produto": "Abacaxi pérola"}, {"produto": "Café Pilão 500 g"}])
        ha.responde_ia("itens", Erro(500, "boom"))
        S.buscar_itens(["Abacaxi pérola"])
        self.assertIsNone(S.BUSCA["erro"], "os sites responderam: não é erro da busca")
        self.assertEqual(S.BUSCA["avisos"], ["Não achei preço para Abacaxi pérola nos sites das lojas, e a IA falhou: "
                                             "a IA do Home Assistant recusou o pedido (500): boom"], "o aviso diz que a IA falhou")
        S.buscar_itens(["Café Pilão 500 g"])  # só o Giassi tem: 1 preço, e a IA falha
        self.assertEqual(S.BUSCA["avisos"], ["A IA falhou, e Café Pilão 500 g ficou só com os preços dos sites das lojas: "
                                             "a IA do Home Assistant recusou o pedido (500): boom"])
        lista = {i["produto"]: i for i in S.ler_json(S.OFERTAS)["lista"]}
        self.assertEqual({k: S.valor_total(v) for k, v in lista["Café Pilão 500 g"]["precos"].items()}, {"merc-giassi": 19.9}, "o preço do site fica")
        ha.responde_ia("itens", Erro(429, "quota"), vezes=2)
        ha.regras_ia.insert(0, ha.regras_ia.pop())
        S.buscar_itens(["Café Pilão 500 g"])
        self.assertTrue(S.BUSCA["avisos"][0].startswith("A IA falhou, e Café Pilão 500 g ficou só com os preços dos sites das lojas: a cota da IA acabou"),
                        S.BUSCA["avisos"])

    def test_nada_achado_e_erros(self):
        S, ha = self.S, self.ha
        self.config(categorias=["mercados"], lista=[{"produto": "Abacaxi pérola"}])
        ha.responde_ia("itens", {"lista": []}, vezes=1)
        S.buscar_itens(["Abacaxi pérola"])
        self.assertEqual(S.BUSCA["avisos"], ['Não achei preço para Abacaxi pérola. Tente com marca e tamanho, por exemplo "Detergente Ypê 500 ml".'])
        ha.responde_ia("itens", Erro(500, "boom"))
        S.buscar_itens(["Coxinha da asa"])  # os sites acham: o erro da IA não conta
        self.assertIsNone(S.BUSCA["erro"])
        self.lojas.regioes.clear()  # nenhum site responde (e a região guardada por 6 horas sai)
        S._regioes.clear()
        S.buscar_itens(["Abacaxi pérola"])
        self.assertIn("recusou o pedido (500)", S.BUSCA["erro"], "a IA falhou e nenhum site respondeu: erro")
        self.config(usar_ia=False, categorias=["mercados"], lista=[{"produto": "Abacaxi pérola"}])
        n = len(ha.chamadas_ia)
        S.buscar_itens(["Abacaxi pérola"])
        self.assertEqual(len(ha.chamadas_ia), n, "IA desligada: só os sites")
        self.config(cep="", lista=[])
        S.buscar_itens(["x"])
        self.assertEqual(S.BUSCA["erro"], "Salve o CEP em Mais › Casa antes de buscar.")


class BuscaBordas(Cenario):
    """O que não pode derrubar a busca: o mapa que quebra, o folheto das lojas novas que falha (ou que traz preço),
    o encarte automático que falha ou vem vazio, a busca dos itens sem preço que falha, a resposta estranha da busca
    focada, o online só pela Shopee e o erro inesperado."""

    def setUp(self):
        super().setUp()
        self.config(raio_km=5, categorias=["mercados"], lista=LISTA[:2], opcoes={"itens_sem_preco": False})

    def test_mapa_que_quebra(self):
        S, ha = self.S, self.ha
        ha.responde_ia("EconomIA: mercados", pagina_mercados)
        S.lojas_do_mapa = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("overpass fora"))
        S.buscar()
        self.assertIsNone(S.BUSCA["erro"])
        self.assertIn("mapa: overpass fora", self.log)
        self.assertEqual(S.ler_json(S.OFERTAS)["categorias"][0]["id"], "mercados")

    def test_folheto_das_lojas_novas(self):
        S, ha = self.S, self.ha
        ha.responde_ia("EconomIA: mercados", pagina_mercados)
        S.busca_folhetos = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("kimbino fora"))
        S.buscar()
        self.assertIsNone(S.BUSCA["erro"])
        self.assertEqual(self.log.count("folhetos: kimbino fora"), 2, "o dos sites e o das lojas que a busca achou")
        resultado = S.resultado_folheto

        def folhetos(cfg, lojas, so_guardados=False):
            if not any(l["nome"] == "Bistek" for l in lojas):
                return [], {}
            r = resultado({"nome": "Bistek", "categoria": "mercados"}, {"url": "https://f/1", "ate": "2099-01-01"},
                          {"ofertas": [{"produto": "Café Pilão Tradicional 500 g", "preco": 14.5}], "lista": []}, cfg)
            return [r], {"bistek": {"loja": "Bistek", "fonte": "Kimbino", "ofertas": 1}}
        S.busca_folhetos = folhetos
        S.gravar_json(S.OFERTAS, {})  # a Bistek ainda não estava no resultado: só a busca na web a acha
        S.buscar()
        of = S.ler_json(S.OFERTAS)
        cafe = next(i for i in of["lista"] if i["produto"] == "Café Pilão 500 g")
        self.assertEqual(S.valor_total(cafe["precos"]["merc-bistek"]), 14.5, "o folheto da loja que a busca achou vale mais que a busca na web")
        self.assertEqual([x["loja"] for x in of["relatorio"]["folhetos"]], ["Bistek"])

    def test_encarte_automatico_que_falha_ou_vem_vazio(self):
        S, ha = self.S, self.ha
        resp = pagina_mercados(None)
        resp["lojas"] += [{"rede": "Loja Erro", "distancia_km": 1.0, "site": "https://erro.com.br/ofertas"},
                          {"rede": "Loja Vazia", "distancia_km": 1.5, "site": "https://vazia.com.br/"}]
        ha.responde_ia("EconomIA: mercados", resp)

        def encarte(loja, cfg):
            if loja["nome"] == "Loja Erro":
                raise S.ErroBusca("não achei o encarte no site")
            return categoria("mercados", [("merc-loja-vazia", "Loja Vazia", 1.5)]), {}
        S.ler_encarte = encarte
        S.buscar()
        self.assertIsNone(S.BUSCA["erro"])
        merc = S.ler_json(S.OFERTAS)["categorias"][0]
        nomes = {r["id"]: r["nome"] for r in merc["redes"]}
        sem = sorted(nomes[l["rede"]] for l in merc["lojas"] if l.get("site_sem_encarte"))
        self.assertEqual(sem, ["Loja Erro", "Loja Vazia"], "não tenta de novo como se tivesse encarte")
        self.assertIn("encarte automático de Loja Erro: não achei o encarte no site", self.log)

    def test_itens_sem_preco_que_falham(self):
        S, ha = self.S, self.ha
        self.config(categorias=["mercados"], lista=LISTA)
        ha.responde_ia("EconomIA: mercados", pagina_mercados)
        ha.responde_ia("itens sem preço", Erro(500, "falhou"))
        S.buscar()
        self.assertIsNone(S.BUSCA["erro"])
        self.assertIn("Dipirona 500 mg", S.ler_json(S.OFERTAS)["relatorio"]["sem_preco"])
        self.assertTrue(any(m.startswith("busca dos itens sem preço: A IA do Home Assistant recusou o pedido (500)") for m in self.log))

    def test_resposta_estranha_da_busca_focada(self):
        S, ha = self.S, self.ha
        ha.responde_ia("itens sem preço", {"lista": ["x", {"item": 1, "precos": ["y", {"rede": "Mercado X", "preco": 5}, {"rede": "Amazon", "preco": 6, "frete": 0}]}]})
        out = S.busca_focada(self.config(categorias=["online"]), ["Leite"], ["online"])
        self.assertEqual([c["id"] for c, _ in out], ["online"], "o preço de loja física fica de fora quando só tem online")
        self.assertEqual(list(out[0][1]["Leite"]["precos"]), ["onli-amazon"])

    def test_online_so_pela_shopee(self):
        S, ha = self.S, self.ha
        S.grava_segredos({"shopee": {"app_id": "1", "secret": "s"}})
        self.lojas.rotas["/shopee"] = lambda p: {"data": {"productOfferV2": {"nodes": [
            {"productName": "Café Pilão Tradicional 500g", "priceMin": "17.9", "ratingStar": "4.9", "productLink": "https://shopee.com.br/cafe"}]}}}
        self.config(categorias=["online"], lista=LISTA[1:2], opcoes={"itens_sem_preco": False},
                    online={"marketplaces": ["shopee"], "mercados_entrega": False})
        S.buscar()
        self.assertIsNone(S.BUSCA["erro"])
        self.assertEqual(ha.chamadas_ia, [], "só a Shopee, que já veio pela API")
        cafe = S.ler_json(S.OFERTAS)["lista"][0]
        self.assertEqual(list(cafe["precos"]), ["onli-shopee"])

    def test_erro_inesperado(self):
        S, ha = self.S, self.ha
        ha.responde_ia("EconomIA: mercados", pagina_mercados)
        S.juntar_categorias = lambda *a: (_ for _ in ()).throw(RuntimeError("juntar quebrou"))
        S.grava_vocab = lambda: (_ for _ in ()).throw(OSError("disco cheio"))
        S.buscar()
        self.assertEqual((S.BUSCA["erro"], S.BUSCA["rodando"], S.BUSCA["etapa"]), ("Erro inesperado na busca: juntar quebrou", False, None))
        self.assertIn("Erro inesperado na busca: juntar quebrou", self.log)

    def test_erro_inesperado_na_busca_de_itens(self):
        S = self.S
        S.busca_scripts = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("sites quebrou"))
        S.grava_vocab = lambda: (_ for _ in ()).throw(OSError("disco cheio"))
        S.buscar_itens(["Leite"])
        self.assertEqual((S.BUSCA["erro"], S.BUSCA["rodando"]), ("Erro inesperado na busca: sites quebrou", False))

    def test_busca_na_web_falha_mas_o_encarte_cadastrado_vale(self):
        S, ha = self.S, self.ha
        self.lojas.regioes.clear()
        S._regioes.clear()
        self.config(raio_km=5, categorias=["mercados"], lista=LISTA[1:2], opcoes={"itens_sem_preco": False},
                    lojas={"adicionar": [{"nome": "Mercado do Bairro, Centro", "categoria": "mercados", "site": "https://bairro.com.br/ofertas"}]})
        ha.responde_ia("EconomIA: mercados", Erro(500, "falhou"))
        resultado = S.resultado_folheto
        S.ler_encarte = lambda loja, cfg: resultado(dict(loja, site=None), {"url": loja["site"], "ate": "2099-01-01"},
                                                    {"ofertas": [{"produto": "Café Pilão Tradicional 500 g", "preco": 15.9}], "lista": []}, cfg)
        S.buscar()
        self.assertIsNone(S.BUSCA["erro"], "o encarte salva a busca")
        self.assertTrue(S.BUSCA["avisos"][0].startswith("Algumas buscas falharam e mantive o resultado anterior: Mercados:"))
        of = S.ler_json(S.OFERTAS)
        self.assertEqual([r["nome"] for r in of["categorias"][0]["redes"]], ["Mercado do Bairro"])
        self.assertEqual(S.valor_total(of["lista"][0]["precos"]["merc-mercado-do-bairro"]), 15.9)
