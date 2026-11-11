"""1.22.0: Mercados da região que entregam. Os mercados do mapa entre o raio da casa e o de entrega (Mais › Lojas ›
Compras online), a entrega conferida pelo site (a consulta da VTEX), em Online com a distância e o Como foi testado, a
confirmação à mão (online.entrega_sim), o que não entrega fora das acompanhadas, a busca direta e o texto da IA."""
import unittest

from apoio import Cenario, categoria

LAT, LON = -26.30, -48.85
KM = 0.009  # ~1 km em latitude


def mercado(nome, km, site=None):
    t = {"name": nome, "shop": "supermarket"}
    if site:
        t["website"] = site
    return {"type": "node", "lat": LAT - km * KM, "lon": LON, "tags": t}


class Regiao(Cenario):
    def setUp(self):
        super().setUp()
        b, lj = self.lojas.base, self.lojas
        self.osm = [mercado("Mercado do Bairro", 1.0, b + "/bairro"), mercado("Rede Entrega", 8.0, b + "/entrega"),
                    mercado("Rede Longe", 12.0, b + "/longe"), mercado("Rede Sem Site", 9.0), mercado("Rede Bloqueada", 7.0, b + "/bloqueia"),
                    mercado("Rede Comum", 6.0, b + "/comum")]
        lj.rotas["/overpass"] = lambda p: {"elements": self.osm}
        lj.vtex |= {"entrega", "longe"}
        lj.regioes["entrega"] = "entrega01"  # entrega no CEP; a "longe" é VTEX mas não entrega
        lj.paginas["/bloqueia/robots.txt"] = (403, "não", "text/plain")

    def cfg(self, **mais):
        on = dict({"mercados_entrega": True, "entrega_km": 10}, **mais.pop("online", {}))
        return self.config(raio_km=5, categorias=["mercados", "online"], online=on, **mais)

    def test_entrega_km(self):
        S = self.S
        self.assertEqual(S.entrega_km({"raio_km": 5, "online": {"entrega_km": 20}}), 20)
        self.assertEqual(S.entrega_km({"raio_km": 5}), 15, "sem escolha: 15 km")
        self.assertEqual(S.entrega_km({"raio_km": 5, "online": {"entrega_km": 3}}), 15, "menor que o da casa não vale")
        self.assertEqual(S.entrega_km({"raio_km": 15, "online": {"entrega_km": 10}}), 20, "o primeiro maior que o da casa")
        self.assertIsNone(S.entrega_km({"raio_km": 60}))
        self.assertFalse(S.regiao_ligada({"raio_km": 5, "categorias": ["mercados"]}), "sem Online")
        self.assertFalse(S.regiao_ligada({"raio_km": 5, "online": {"mercados_entrega": False}}))

    def test_le_o_mapa_e_confere_a_entrega_pelo_site(self):
        S = self.S
        lojas = S.mercados_da_regiao(self.cfg())
        por = {l["nome"]: l for l in lojas}
        self.assertEqual(list(por), ["Rede Comum", "Rede Bloqueada", "Rede Entrega", "Rede Sem Site"],
                         "só entre o raio da casa (5 km) e o de entrega (10 km), da mais perto para a mais longe")
        self.assertIs(por["Rede Entrega"]["entrega"]["atende"], True)
        self.assertIn("✓ Entrega no CEP", " ".join(por["Rede Entrega"]["entrega"]["passos"]))
        self.assertEqual(por["Rede Entrega"]["distancia_km"], 8.0)
        for nome, trecho in (("Rede Sem Site", "Sem site"), ("Rede Bloqueada", "recusou"), ("Rede Comum", "não tem a consulta de entrega")):
            e = por[nome]["entrega"]
            self.assertIsNone(e["atende"], nome)
            self.assertIn(trecho, e["passos"][0], nome)
            self.assertEqual(e["passos"][-1], "Confirme se entrega.")
        n = len(self.lojas.pedidos_de("/overpass"))
        S.mercados_da_regiao(self.cfg())
        self.assertEqual(len(self.lojas.pedidos_de("/overpass")), n, "guardado por uma semana")
        lojas = S.mercados_da_regiao(self.cfg(online={"entrega_km": 15}))
        self.assertIn("Rede Longe", [l["nome"] for l in lojas], "outra distância: lê de novo")
        self.assertIs(next(l for l in lojas if l["nome"] == "Rede Longe")["entrega"]["atende"], False, "a consulta diz que não entrega")

    def test_em_online_com_a_entrega_e_a_confirmacao(self):
        S = self.S
        cfg = self.cfg(online={"entrega_sim": ["Rede Comum"]})
        S.mercados_da_regiao(cfg)
        self.ofertas({"categorias": [categoria("mercados", [("merc-mercado-do-bairro", "Mercado do Bairro", 1.0)])], "lista": []})
        S.mesclar_resultado([], cfg)
        of = S.ler_json(S.OFERTAS)
        on = next(c for c in of["categorias"] if c["id"] == "online")
        nomes = {r["id"]: r["nome"] for r in on["redes"]}
        lojas = {nomes[l["rede"]]: l for l in on["lojas"]}
        self.assertEqual(set(lojas), {"Rede Comum", "Rede Bloqueada", "Rede Entrega", "Rede Sem Site"})
        self.assertTrue(all(l["regional"] for l in lojas.values()))
        self.assertTrue(lojas["Rede Comum"]["entrega"]["confirmada"])
        self.assertEqual(lojas["Rede Entrega"]["distancia_km"], 8.0)
        # a busca direta: só a que o site diz que entrega, em Online
        cand = S.candidatos_site(cfg)
        self.assertEqual(cand.get(self.lojas.base + "/entrega"), ("Rede Entrega", "online"))
        self.assertNotIn(self.lojas.base + "/comum", cand)
        # o texto da IA: a distância e as que entregam (pelo site ou confirmadas)
        txt = S.entrega_txt(cfg)
        self.assertIn("até 10 km do CEP", txt)
        self.assertIn("Rede Comum", txt)
        self.assertIn("Rede Entrega", txt)
        self.assertNotIn("Rede Sem Site", txt)

    def test_a_que_nao_entrega_fica_de_fora(self):
        S = self.S
        cfg = self.cfg(online={"entrega_km": 15})
        S.mercados_da_regiao(cfg)
        S.mesclar_resultado([], cfg)
        info, acompanha = S.redes_acompanhadas(cfg, S.ler_json(S.OFERTAS))
        longe = next(k for k, v in info.items() if v["nome"] == "Rede Longe")
        entrega = next(k for k, v in info.items() if v["nome"] == "Rede Entrega")
        self.assertFalse(acompanha(longe), "o site diz que não entrega")
        self.assertTrue(acompanha(entrega))
        cfg2 = self.cfg(online={"entrega_km": 15, "entrega_sim": ["Rede Longe"]})
        self.assertTrue(S.redes_acompanhadas(cfg2, S.ler_json(S.OFERTAS))[1](longe), "confirmada à mão: entra")

    def test_desligado_nao_le_nada(self):
        S = self.S
        self.assertEqual(S.mercados_da_regiao(self.cfg(online={"mercados_entrega": False})), [])
        self.assertFalse(self.lojas.pedidos_de("/overpass"))
        self.assertEqual(S.regiao_guardada(self.cfg(online={"mercados_entrega": False})), [])

    def test_rota_atualizar(self):
        S = self.S
        self.cfg(online={"mercados_entrega": False})
        d = S.atualizar_regiao({"entrega_km": 10, "mercados_entrega": True})
        self.assertTrue(d["ok"])
        self.assertEqual(d["msg"], "4 mercados até 10 km: 1 entrega no seu CEP, 3 sem resposta (confirme em Online).")
        self.assertTrue(any(c["id"] == "online" for c in S.ler_json(S.OFERTAS)["categorias"]))
        d = S.atualizar_regiao({"mercados_entrega": False})
        self.assertEqual(d, {"ok": True, "msg": ""})
        self.osm = []
        d = S.atualizar_regiao({"entrega_km": 20, "mercados_entrega": True})
        self.assertEqual(d["msg"], "Nenhum mercado com site entre 5 e 20 km.")


if __name__ == "__main__":
    unittest.main()
