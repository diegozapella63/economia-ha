"""Lojas do raio pelo mapa: OpenStreetMap (Overpass) e Google Places (Nearby e Text Search, com páginas), juntas por rede
e por lugar, a filial mais perto, o site pelo Google, cache de 7 dias, a casa do HA, aplica_mapa no resultado,
o Encontrar lojas (atualizar_lojas_mapa), lojas sem localização (localiza_sem_local), a cidade do CEP e Testar o Google."""
import json

from apoio import Cenario, categoria

LAT, LON = -26.30, -48.85
KM = 0.009  # ~1 km em latitude


def lugar(nome, km, tipos=("pharmacy",), primario=None, site=None, status="OPERATIONAL", pid=None, endereco=None):
    return {"id": pid or "pl-" + nome.lower().replace(" ", "-"), "displayName": {"text": nome}, "location": {"latitude": LAT - km * KM, "longitude": LON},
            "types": list(tipos), "primaryType": primario or tipos[0], "businessStatus": status, "websiteUri": site,
            "shortFormattedAddress": endereco or f"Rua {nome}, 1"}


class BaseMapa(Cenario):
    def setUp(self):
        super().setUp()
        b = self.lojas.base
        self.osm = [
            {"type": "node", "lat": LAT - 0.5 * KM, "lon": LON, "tags": {"name": "Farmácia Bem Estar", "amenity": "pharmacy", "website": b + "/bemestar",
                                                                        "addr:street": "Rua das Flores", "addr:housenumber": "100", "addr:suburb": "Centro"}},
            {"type": "way", "center": {"lat": LAT - 1.0 * KM, "lon": LON}, "tags": {"name": "Supermercado Kuntze", "shop": "supermarket",
                                                                                   "contact:instagram": "https://www.instagram.com/kuntze"}},
            {"type": "node", "lat": LAT - 0.2 * KM, "lon": LON, "tags": {"name": "Pet Farma Vet", "amenity": "pharmacy"}},
            {"type": "node", "lat": LAT - 0.7 * KM, "lon": LON, "tags": {"name": "Cão Feliz", "shop": "pet"}},
            {"type": "node", "lat": LAT, "lon": LON, "tags": {"amenity": "pharmacy"}},
            {"type": "node", "lat": LAT - 1.5 * KM, "lon": LON, "tags": {"brand": "Drogaria Catarina", "amenity": "pharmacy"}},
        ]
        self.lojas.rotas["/overpass"] = self.overpass
        self.lojas.rotas["/google/nearby"] = self.nearby
        self.lojas.rotas["/google/texto"] = self.texto
        self.textos = []

    def overpass(self, p):
        q = p.form()["data"]
        quer = {"pharmacy": 'amenity"="pharmacy' in q, "supermarket": "supermarket" in q, "pet": 'shop"="pet' in q}
        return {"elements": [e for e in self.osm if quer.get(e["tags"].get("amenity") or e["tags"].get("shop"), True)]}

    def nearby(self, p):
        if p.cabecalhos.get("X-Goog-Api-Key") != "chave-google":
            return (403, {"error": {"code": 403, "message": "API key not valid"}})
        tipos = p.json()["includedTypes"]
        if "pharmacy" in tipos:
            return {"places": [lugar("DROGARIA CATARINA", 0.8, endereco="Rua XV, 10"), lugar("Clínica Vet Amigo", 0.4, ("pharmacy",), "veterinary_care"),
                               lugar("Farmácia Fechada", 0.3, status="CLOSED_PERMANENTLY")]}
        if "supermarket" in tipos:
            return {"places": [lugar("Supermercado Kuntze", 1.0, ("supermarket",), site="https://kuntze.com.br")]}
        return {"places": []}

    def texto(self, p):
        c = p.json()
        self.textos.append(c)
        q = c["textQuery"]
        if "locationRestriction" in c:  # varredura
            if q == "supermercado" and "pageToken" not in c:
                return {"places": [lugar("Komprão Atacadista", 1.2, ("wholesaler",)), lugar("Mercado Longe", 5.0, ("supermarket",))], "nextPageToken": "p2"}
            if q == "supermercado":
                return {"places": [lugar("Mercadinho da Esquina", 0.3, ("grocery_store",))]}
            if q == "atacadista":
                return {"places": [lugar("Atacado de Pisos", 0.9, ("wholesaler",))]}
            return {"places": []}
        raio = c["locationBias"]["circle"]["radius"]
        if raio == 500.0 and q == "Mercadinho da Esquina":  # google_site
            return {"places": [lugar("Mercadinho da Esquina", 0.3, ("grocery_store",), site="https://mercadinhoesquina.com.br")]}
        if raio == 20000.0:  # localiza_sem_local
            if q.startswith("Mercado Kuntze Centro"):
                return {"places": [lugar("Mercado Kuntze", 3.0, ("supermarket",), pid="pl-kuntze-3"), lugar("Mercado Kuntze Filial", 8.0, ("supermarket",))]}
            if q.startswith("Farmácia Longe"):
                return {"places": [lugar("Farmácia Longe", 25.0)]}
        return {"places": []}

    def com_google(self):
        self.S.grava_segredos({"google": {"key": "chave-google"}})

    def sites_google(self):
        return [t["textQuery"] for t in self.textos if (t.get("locationBias") or {}).get("circle", {}).get("radius") == 500.0]


class Mapa(BaseMapa):
    def test_osm_e_google_juntos(self):
        S, lj = self.S, self.lojas
        self.com_google()
        cfg = self.config(raio_km=2, categorias=["farmacias", "mercados"])
        m = S.lojas_do_mapa(cfg, ["farmacias", "mercados", "online"])
        self.assertEqual(len(self.sites_google()), 3)
        nomes = {c: [(l["nome"], l["distancia_km"]) for l in v] for c, v in m.items()}
        self.assertEqual(nomes["farmacias"], [("Farmácia Bem Estar", 0.5), ("Drogaria Catarina", 0.8)],
                         "Pet Farma Vet e a veterinária ficam de fora, a fechada também; o nome em maiúsculas fica bonito; a filial mais perto")
        self.assertEqual(nomes["mercados"], [("Mercadinho da Esquina", 0.3), ("Supermercado Kuntze", 1.0), ("Komprão Atacadista", 1.2)],
                         "atacarejo sem tipo de mercado entra; loja de pisos e a de 5 km não; a segunda página também")
        bem = m["farmacias"][0]
        self.assertEqual((bem["endereco"], bem["site"], bem["fonte"]), ("Rua das Flores, 100, Centro", lj.base + "/bemestar", "OpenStreetMap"))
        kuntze = m["mercados"][1]
        self.assertEqual((kuntze["site"], kuntze["social"]), ("https://kuntze.com.br", "https://www.instagram.com/kuntze"), "site do Google, Instagram do mapa")
        self.assertEqual(m["mercados"][0]["site"], "https://mercadinhoesquina.com.br", "site achado pelo Google, loja por loja")
        q = lj.pedidos_de("/overpass")[-1]
        dados = json.loads(json.dumps(__import__("urllib.parse").parse.parse_qs(q[3])))["data"][0]
        self.assertIn('nwr["amenity"="pharmacy"](around:2000,-26.3,-48.85);', dados)
        self.assertIn("supermarket|convenience|wholesale", dados)
        self.assertEqual(q[2]["User-Agent"], "EconomIA (add-on do Home Assistant)")
        nb = lj.pedidos_de("/google/nearby")[0]
        self.assertIn("places.websiteUri", nb[2]["X-Goog-Fieldmask"])
        self.assertEqual(json.loads(nb[3])["rankPreference"], "DISTANCE")
        guardado = S.ler_json(S.LOJAS_MAPA)
        self.assertEqual(guardado["fontes"], ["OpenStreetMap", "Google"])
        self.assertTrue(any(k.startswith("esquina@") or "esquina" in k for k in guardado["sites"]))
        # guardado por 7 dias; forcar lê de novo
        n = len(lj.pedidos)
        self.assertEqual(S.lojas_do_mapa(cfg, ["farmacias", "mercados"]), m)
        self.assertEqual(len(lj.pedidos), n, "do cache")
        S.lojas_do_mapa(cfg, ["farmacias", "mercados"], forcar=True)
        self.assertGreater(len(lj.pedidos_de("/overpass")), 1)
        self.assertEqual(sorted(self.sites_google()), ["Drogaria Catarina", "Komprão Atacadista", "Mercadinho da Esquina"],
                         "só as lojas sem site e fora das redes conhecidas; o resultado fica guardado 30 dias")

    def test_so_openstreetmap_e_falhas(self):
        S, lj = self.S, self.lojas
        cfg = self.config(raio_km=1, categorias=["farmacias", "petshops"])
        m = S.lojas_do_mapa(cfg, ["farmacias", "petshops"])
        self.assertEqual([l["nome"] for l in m["petshops"]], ["Cão Feliz"])
        self.assertEqual(S.ler_json(S.LOJAS_MAPA)["fontes"], ["OpenStreetMap"])
        self.assertFalse(lj.pedidos_de("/google"), "sem chave: nada do Google")
        del lj.rotas["/overpass"]
        self.assertEqual(S.lojas_do_mapa(cfg, ["farmacias", "petshops"], forcar=True), m, "o mapa não respondeu: fica o de antes")
        self.assertEqual(S.lojas_do_mapa(cfg, ["online"]), {})
        S.CASA_TESTE = None
        self.ha.estados.pop("zone.home")
        self.assertEqual(S.lojas_do_mapa(cfg, ["farmacias"], forcar=True), {})
        self.assertTrue(any("sem a localização da Casa" in str(x) for x in self.log))

    def test_casa_do_home_assistant(self):
        S, ha = self.S, self.ha
        S.CASA_TESTE = None
        ha.estados["zone.home"]["attributes"].update(latitude=-27.5, longitude=-48.5)
        self.assertEqual(S.casa(), (-27.5, -48.5))
        self.assertTrue(ha.pedidos_de("/api/states/zone.home", "GET"))

    def test_google_recusa(self):
        S = self.S
        S.grava_segredos({"google": {"key": "errada"}})
        with self.assertRaisesRegex(S.ErroBusca, r"O Google recusou a chave \(403: API key not valid\)"):
            S.google_lojas(LAT, LON, 1000, ["farmacias"], "errada")
        self.assertEqual(S.testar_google(), {"ok": False, "msg": "O Google recusou a chave (403: API key not valid)."})
        with self.assertRaisesRegex(S.ErroBusca, r"O Google recusou o pedido \(404"):
            S.google_post(self.lojas.base + "/google/nao-existe", {}, "k", "places.id")

    def test_testar_google(self):
        S = self.S
        self.assertEqual(S.testar_google(), {"ok": False, "msg": "Falta a chave do Google."})
        self.com_google()
        self.assertEqual(S.testar_google(), {"ok": True, "msg": "Pronta: 1 farmácias a até 1 km, a mais perto é Drogaria Catarina (0,8 km)."})

    def test_aplica_mapa_no_resultado(self):
        S = self.S
        cfg = self.config()
        cats = [categoria("farmacias", [("farm-drogaria-catarina", "DROGARIA CATARINA", None, {"fontes": ["Site"], "site": "https://www.facebook.com/catarina"}),
                                        ("farm-pet-center", "Pet Center", 0.3)])]
        mapa = {"farmacias": [{"nome": "Drogaria Catarina", "distancia_km": 0.8, "endereco": "Rua XV, 10", "lat": LAT, "lon": LON, "fonte": "Google",
                               "place_id": "pl-1"},
                              {"nome": "Farmácia Bem Estar", "distancia_km": 0.5, "endereco": "Rua das Flores", "site": "https://bemestar.com.br", "fonte": "OpenStreetMap"}],
                "mercados": [{"nome": "Mercadinho da Esquina", "distancia_km": 0.3, "fonte": "Google"}]}
        S.aplica_mapa(cats, mapa, cfg, marcar_novas=True)
        farm = cats[0]
        self.assertEqual([r["nome"] for r in farm["redes"]], ["Drogaria Catarina", "Pet Center", "Farmácia Bem Estar"])
        lojas = {l["rede"]: l for l in farm["lojas"]}
        self.assertNotIn("farm-pet-center", lojas, "pet shop que veio só do mapa sai das farmácias")
        cat = lojas["farm-drogaria-catarina"]
        self.assertEqual((cat["distancia_km"], cat["endereco"], cat["fontes"], cat["place_id"]), (0.8, "Rua XV, 10", ["Mapa", "Site"], "pl-1"))
        self.assertEqual((cat.get("site"), cat["social"]), (None, "https://www.facebook.com/catarina"), "rede social não é site")
        nova = lojas["farm-farmacia-bem-estar"]
        self.assertEqual((nova["fontes"], nova["nova"], nova["site"]), (["Mapa"], True, "https://bemestar.com.br"))
        self.assertEqual([l["rede"] for l in farm["lojas"]], ["farm-farmacia-bem-estar", "farm-drogaria-catarina"], "da mais perto para a mais longe")
        self.assertEqual(cats[1]["id"], "mercados", "categoria que só o mapa tem entra")
        self.assertEqual(S.mapa_txt(dict(cfg, _mapa=mapa), "farmacias"),
                         "Lojas do raio, pelo mapa (são estas que existem perto da casa, com a distância certa): Drogaria Catarina (Rua XV, 10), 0,8 km; "
                         "Farmácia Bem Estar (Rua das Flores), 0,5 km. Procure o preço dos itens da lista nessas lojas e use esses nomes. "
                         "Em \"lojas\", não repita as do mapa: traga só outras do raio que achar.")
        self.assertEqual(S.mapa_txt(cfg, "farmacias"), "")

    def test_redes_sociais_e_categoria(self):
        S = self.S
        self.assertEqual(S.rede_social("https://www.instagram.com/loja"), "o Instagram")
        self.assertEqual(S.rede_social("https://wa.me/5547999"), "o WhatsApp")
        self.assertEqual(S.rede_social("https://www.ifood.com.br/delivery/x"), "o iFood")
        self.assertIsNone(S.rede_social("https://loja.com.br"))
        self.assertIsNone(S.rede_social("não é link"))
        self.assertEqual(S.site_loja("https://loja.com.br"), "https://loja.com.br")
        self.assertIsNone(S.site_loja("https://linktr.ee/loja"))
        self.assertEqual(S.social_loja("https://linktr.ee/loja"), "https://linktr.ee/loja")
        self.assertFalse(S.da_categoria("farmacias", "Farmácia Veterinária São Roque"))
        self.assertFalse(S.da_categoria("mercados", "Mercado Bom", "pharmacy"))
        self.assertTrue(S.da_categoria("mercados", "Agropecuária do Vale"), "agropecuária só sai das farmácias")
        self.assertTrue(S.da_categoria("petshops", "Pet Shop"))


class EncontrarLojas(BaseMapa):
    def test_encontrar_lojas(self):
        S, lj = self.S, self.lojas
        self.com_google()
        self.config(raio_km=2, categorias=["farmacias", "mercados"], usar_ia=False)
        self.assertEqual(S.atualizar_lojas_mapa({"categorias": ["online"]}), {"ok": False, "msg": "Marque farmácias, mercados ou pet shops."})
        r = S.atualizar_lojas_mapa({"raio_km": "2"})
        self.assertEqual(r["msg"], "Achei 3 mercados e 2 farmácias até 2 km (OpenStreetMap e Google).")
        self.assertEqual((r["ok"], r["lojas"], r["teste"]), (True, {"mercados": 3, "farmacias": 2}, True))
        of = S.ler_json(S.OFERTAS)
        farm = next(c for c in of["categorias"] if c["id"] == "farmacias")
        self.assertTrue(all(l.get("nova") for l in farm["lojas"]), "registradas, esperando a próxima busca")
        self.espera(lambda: not S.SONDA["rodando"] and S.SONDA["terminou_em"], 30, "o teste de preço das lojas não terminou")
        self.assertTrue(S.SONDA["resumo"].startswith("Testei 5 lojas:"), S.SONDA["resumo"])
        fontes = S.ler_json(S.SONDA_FILE)
        self.assertEqual(sorted(fontes), ["farmacias", "mercados"])
        self.assertEqual(fontes["mercados"]["supermercado kuntze"]["instagram"], "kuntze")
        self.assertTrue(all(l.get("preco_fonte") for c in S.ler_json(S.OFERTAS)["categorias"] for l in c["lojas"]), "cada loja com o resultado do teste")

    def test_sem_casa_e_mapa_vazio(self):
        S = self.S
        self.config(categorias=["farmacias"])
        self.lojas.rotas["/overpass"] = lambda p: {"elements": []}
        self.assertIn("não achou lojas nessa distância", S.atualizar_lojas_mapa({})["msg"])
        S.CASA_TESTE = None
        self.ha.estados.pop("zone.home")
        self.assertEqual(S.atualizar_lojas_mapa({})["msg"], "Não achei a localização da Casa no Home Assistant. Confira em Configurações › Sistema › Geral.")


class SemLocalizacao(BaseMapa):
    def test_localiza_pelo_google(self):
        S = self.S
        self.config()
        S.gravar_json(S.FOLHETOS, {"_cep": {"cep": "89216120", "cidade": "Joinville", "uf": "SC"}})
        self.ofertas({"categorias": [categoria("mercados", [("merc-kuntze", "Mercado Kuntze Centro", None, {"fontes": ["Site"]}),
                                                            ("merc-perto", "Mercado Perto", 1.0)]),
                                     categoria("farmacias", [("farm-longe", "Farmácia Longe", None)]),
                                     categoria("online", [("onli-amazon", "Amazon", None)])]})
        self.assertEqual(S.localiza_sem_local(S.ler_config()), 0, "sem a chave do Google: nada")
        self.com_google()
        self.assertEqual(S.localiza_sem_local(S.ler_config()), 1)
        consultas = [t["textQuery"] for t in self.textos]
        self.assertEqual(consultas, ["Mercado Kuntze Centro Joinville", "Farmácia Longe Joinville"], "só as físicas sem localização, com a cidade")
        of = S.ler_json(S.OFERTAS)
        k = next(l for c in of["categorias"] for l in c["lojas"] if l["rede"] == "merc-kuntze")
        self.assertEqual((k["distancia_km"], k["place_id"], k["fontes"]), (3.0, "pl-kuntze-3", ["Mapa", "Site"]), "a filial mais perto, até 20 km")
        longe = next(l for c in of["categorias"] for l in c["lojas"] if l["rede"] == "farm-longe")
        self.assertIsNone(longe["distancia_km"], "a 25 km não conta: continua sem localização")
        self.assertTrue(S.ler_json(S.LOCAIS)["farmacia longe"]["nada"])
        S.localiza_sem_local(S.ler_config())
        self.assertEqual(len(self.textos), 2, "a resposta (também o 'não achei') fica guardada 30 dias")


class Bordas(BaseMapa):
    """O nome da rede, o Google que falha sem dizer o motivo, a varredura ou o site que falham no meio, lugares sem nome
    ou fechados, raio inválido, nome com erro de digitação no mapa, e as lojas sem localização com erros e limite."""

    def test_nome_da_rede(self):
        S = self.S
        self.assertEqual([S.chave_loja(n) for n in ("Supermercado Imperatriz - Joinville", "Droga Raia", "Farmácia", "Farmácia Preço Popular | Centro")],
                         ["imperatriz", "raia", "farmacia", "preco popular"], "só palavras de loja: fica o nome inteiro")
        self.assertEqual([S.nome_direta(n) for n in ("Giassi Supermercados", "Angeloni Joinville", "Mercado Novo")], ["Giassi", "Angeloni", "Mercado Novo"],
                         "a loja com busca direta escrita do jeito dela")

    def test_google_sem_motivo(self):
        S = self.S
        self.lojas.rotas["/google/nearby"] = lambda p: (500, "<html>erro</html>", "text/html")
        with self.assertRaisesRegex(S.ErroBusca, r"^O Google recusou a chave \(500\)\.$"):
            S.google_lojas(LAT, LON, 1000, ["online", "farmacias"], "k")
        self.assertEqual(len(self.lojas.pedidos_de("/google/nearby")), 1, "online não tem tipo no Google: nem pergunta")
        self.lojas.rotas["/google/texto"] = lambda p: (502, "", "text/html")
        with self.assertRaisesRegex(S.ErroBusca, r"^O Google recusou o pedido \(502\)\.$"):
            S.google_post(S.GOOGLE_TEXTO, {}, "k", "places.id")

    def test_google_que_falha_no_meio(self):
        S = self.S
        self.com_google()
        cfg = self.config(raio_km="perto", categorias=["mercados"])
        S.google_lojas = lambda *a, **k: (_ for _ in ()).throw(S.ErroBusca("O Google recusou a chave (403)."))
        S.google_varredura = lambda *a, **k: (_ for _ in ()).throw(OSError("caiu"))
        S.google_site = lambda *a, **k: (_ for _ in ()).throw(OSError("sem rede"))
        m = S.lojas_do_mapa(cfg, ["mercados"])
        self.assertEqual([l["nome"] for l in m["mercados"]], ["Supermercado Kuntze"], "fica o OpenStreetMap")
        self.assertEqual(S.ler_json(S.LOJAS_MAPA)["fontes"], ["OpenStreetMap"])
        self.assertIn(",2000,", S.ler_json(S.LOJAS_MAPA)["chave"], "raio inválido: 2 km")
        for msg in ("mapa: O Google recusou a chave (403).", "mapa: busca por texto no Google: caiu", "mapa: site de Supermercado Kuntze no Google: sem rede"):
            self.assertTrue(any(msg == str(x) for x in self.log), msg)

    def test_varredura_ignora_lugar_sem_nome_ou_fechado(self):
        S = self.S
        sem_nome = dict(lugar("x", 0.2, ("supermarket",)), displayName={"text": ""})
        sem_local = dict(lugar("Mercado Sem Local", 0.2, ("supermarket",)), location={})
        self.lojas.rotas["/google/texto"] = lambda p: {"places": [sem_nome, sem_local, lugar("Mercado Fechado", 0.2, ("supermarket",), status="CLOSED_PERMANENTLY"),
                                                                  lugar("Mercado Aberto", 0.2, ("supermarket",))]}
        out = S.google_varredura(LAT, LON, 1000, ["mercados"], "k", paginas=1)
        self.assertEqual({l["nome"] for l in out}, {"Mercado Aberto"})

    def test_site_pelo_google_so_bem_perto(self):
        S = self.S
        self.lojas.rotas["/google/texto"] = lambda p: {"places": [lugar("Mercadinho", 1.0, site="https://longe.com.br"), dict(lugar("Mercadinho", 0.1), location={}),
                                                                  lugar("Outro Nome", 0.1, site="https://outro.com.br"),
                                                                  lugar("Mercadinho", 0.2, site="https://www.instagram.com/mercadinho/")]}
        self.assertEqual(S.google_site("Mercadinho", LAT, LON, "k"),
                         {"site": None, "social": "https://www.instagram.com/mercadinho/", "place_id": "pl-mercadinho"},
                         "a 1 km não é a mesma loja; o Instagram vai como rede social")
        self.lojas.rotas["/google/texto"] = lambda p: {"places": []}
        self.assertEqual(S.google_site("Mercadinho", LAT, LON, "k"), {})

    def test_nome_com_erro_no_mapa_e_site_da_rede_social(self):
        S = self.S
        cats = [categoria("farmacias", [("farm-drogaria-catarinna", "Drogaria Catarinna", None, {"fontes": ["Site"], "site": "https://www.instagram.com/catarina/"})])]
        mapa = {"farmacias": [{"nome": "Drogaria Catarina", "categoria": "farmacias", "distancia_km": 0.8, "fonte": "Google", "lat": LAT, "lon": LON,
                               "site": "https://catarina.com.br", "endereco": "Rua XV, 10"}]}
        S.mesma_loja = (lambda orig: (lambda a, b: orig(a, b) and "catarinna" not in S.norm(a + b)))(S.mesma_loja)
        S.mesmo_lugar = lambda *a: True
        S.aplica_mapa(cats, mapa, self.config())
        r, l = cats[0]["redes"][0], cats[0]["lojas"][0]
        self.assertEqual((r["nome"], r["curto"]), ("Drogaria Catarina", "Drogaria Catarin"), "o nome do Google corrige o digitado")
        self.assertEqual((l["social"], l["site"], l["distancia_km"]), ("https://www.instagram.com/catarina/", "https://catarina.com.br", 0.8),
                         "a rede social sai do site; o site do mapa entra")

    def test_encontrar_lojas_com_raio_invalido_e_erro_ao_localizar(self):
        S = self.S
        self.config(raio_km=1, categorias=["farmacias"], usar_ia=False)
        S.localiza_sem_local = lambda cfg: (_ for _ in ()).throw(RuntimeError("quebrou"))
        S.sonda_lojas = lambda cfg: None
        r = S.atualizar_lojas_mapa({"raio_km": "um"})
        self.assertTrue(r["msg"].endswith("até 1 km (OpenStreetMap)."), r["msg"])
        self.assertTrue(any("lojas sem localização: quebrou" == str(x) for x in self.log))

    def test_sem_localizacao_com_erros_e_limite(self):
        S = self.S
        self.com_google()
        self.config()
        self.ofertas({"categorias": [categoria("mercados", [(f"merc-{i}", f"Mercado Sem Lugar {i}", None) for i in range(3)])]})
        self.lojas.rotas["/google/texto"] = lambda p: (500, {"error": {"message": "interno"}})
        self.assertEqual(S.localiza_sem_local(S.ler_config(), maximo=2), 0)
        self.assertEqual(len(self.lojas.pedidos_de("/google/texto")), 2, "até o máximo de consultas por vez")
        self.assertTrue(any(str(x).startswith("onde fica Mercado Sem Lugar 0: O Google recusou o pedido (500: interno)") for x in self.log))
        self.assertEqual(S.ler_json(S.LOCAIS), {}, "o erro não fica guardado como \"não achei\"")
        self.lojas.rotas["/google/texto"] = lambda p: {"places": [lugar("Mercado Sem Lugar 0", 1.0, status="CLOSED_PERMANENTLY"), lugar("Outra Loja", 1.0)]}
        S.localiza_sem_local(S.ler_config(), maximo=1)
        self.assertTrue(S.ler_json(S.LOCAIS)["mercado sem lugar 0"]["nada"], "fechada ou de outro nome: não achou")
        S.CASA_TESTE = None
        self.ha.estados.pop("zone.home")
        self.assertEqual(S.localiza_sem_local(S.ler_config()), 0, "sem a casa: nada")


class CidadeDoCep(Cenario):
    def test_cidade(self):
        S = self.S
        cache = {}
        self.assertEqual(S.cidade_do_cep("89216-120", cache), ("Joinville", "SC"))
        self.assertEqual(cache["_cep"], {"cep": "89216120", "cidade": "Joinville", "uf": "SC"})
        S.FOLHETOS_TESTE = None
        pedidos = []
        S.http_json = lambda u, timeout=15: pedidos.append(u) or {"localidade": "Blumenau", "uf": "SC"}
        self.assertEqual(S.cidade_do_cep("89216120", cache), ("Joinville", "SC"), "guardada")
        self.assertEqual(S.cidade_do_cep("89010000", cache), ("Blumenau", "SC"))
        self.assertEqual(pedidos, ["https://viacep.com.br/ws/89010000/json/"], "o ViaCEP só com o CEP, nada mais")
        S.http_json = lambda u, timeout=15: (_ for _ in ()).throw(OSError("sem rede"))
        self.assertEqual(S.cidade_do_cep("01000000", {}), (None, None))
