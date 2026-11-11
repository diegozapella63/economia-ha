"""1.21.0: sensor.economia_melhor_loja (onde a lista toda sai mais barata) e binary_sensor.economia_oferta (uma oferta
de um item da lista), com o Home Assistant falso."""
import unittest

from apoio import Cenario, categoria

LISTA = [{"produto": "Arroz 5 kg", "qtd": 2}, {"produto": "Café Pilão 500 g"}, {"produto": "Detergente"}, {"produto": "Sem preço"}]


def ofertas_json(**mais):
    mercados = categoria("mercados", [("giassi", "Giassi", 0.8), ("bistek", "Bistek", 1.5), ("longe", "Longe", 9.0)], ofertas=[
        {"id": "g-cafe", "rede": "giassi", "produto": "Café Pilão 500 g", "preco_normal": 20.0, "preco_oferta": 15.0, "tipo": "promo", "valido_ate": "2099-12-31"},
        {"id": "b-arroz", "rede": "bistek", "produto": "Arroz tipo 1 5 kg", "preco_normal": 30.0, "preco_oferta": 27.0, "tipo": "promo"},
        {"id": "b-leite", "rede": "bistek", "produto": "Leite integral", "preco_normal": 6.0, "preco_oferta": 4.0, "tipo": "promo"}])
    online = categoria("online", [("mercadolivre", "Mercado Livre", None)])
    d = {"versao": 2, "gerado_em": "2026-11-09T08:00:00-03:00", "categorias": [mercados, online], "lista": [
        {"produto": "Arroz 5 kg", "precos": {"giassi": 25.0, "bistek": 28.0, "longe": 10.0, "mercadolivre": {"preco": 5.0, "frete": 0}}},
        {"produto": "Café Pilão 500 g", "precos": {"giassi": 18.0, "bistek": {"preco": 19.0, "clube": 16.0}}},
        {"produto": "Detergente", "precos": {"bistek": 2.5}}]}
    d.update(mais)
    return d


class MelhorLoja(Cenario):
    def estados(self, **cfg):
        self.config(lista=LISTA, categorias=["mercados", "online"], **cfg)
        self.ofertas(ofertas_json())
        return self.S.estados_lista()

    def test_a_loja_com_mais_itens_e_o_menor_total(self):
        m = self.estados()["sensor.economia_melhor_loja"]
        a = m["attributes"]
        self.assertEqual(m["state"], "Bistek", "tem os três itens com preço; o Giassi, só dois")
        self.assertEqual((a["total"], a["itens"], a["faltam"], a["tipo"], a["distancia_km"]), (77.5, 3, 1, "Mercado", 1.5), "2 × 28 + 19 + 2,50")
        self.assertEqual(a["economia"], 0, "mais caro que a média nos dois que o Giassi também tem")
        self.assertEqual(a["segunda"], {"loja": "Giassi", "total": 68.0, "itens": 2})
        self.assertEqual(a["atualizado"], "2026-11-09T08:00:00-03:00")

    def test_socio_do_clube_e_loja_longe_ou_online_ficam_de_fora(self):
        a = self.estados(clubes=["bistek"])["sensor.economia_melhor_loja"]["attributes"]
        self.assertEqual(a["total"], 74.5, "o café com o preço do clube")
        self.assertEqual(a["segunda"]["loja"], "Giassi", "a loja a 9 km (fora do raio) e o Mercado Livre não contam")

    def test_sem_preco_nenhum(self):
        self.config(lista=[{"produto": "Nada"}])
        self.ofertas({"categorias": [], "lista": []})
        m = self.S.estados_lista()["sensor.economia_melhor_loja"]
        self.assertEqual((m["state"], m["attributes"]["itens"], m["attributes"]["faltam"]), ("unknown", 0, 1))
        self.assertEqual(self.S.estados_lista()["binary_sensor.economia_oferta"]["state"], "off")


class OfertaDaLista(Cenario):
    def test_oferta_que_bate_com_um_item(self):
        self.config(lista=LISTA, categorias=["mercados", "online"])
        self.ofertas(ofertas_json())
        o = self.S.estados_lista()["binary_sensor.economia_oferta"]
        a = o["attributes"]
        self.assertEqual((o["state"], a["itens"], a["maior_desconto"], a["icon"]), ("on", 2, 25, "mdi:sale"))
        self.assertEqual(a["ofertas"][0], {"item": "Café Pilão 500 g", "produto": "Café Pilão 500 g", "loja": "Giassi", "preco": 15.0,
                                           "preco_normal": 20.0, "desconto": 25, "valido_ate": "2099-12-31"})
        self.assertEqual([x["item"] for x in a["ofertas"]], ["Café Pilão 500 g", "Arroz 5 kg"], "o leite não está na lista")

    def test_escondida_nao_conta(self):
        self.config(lista=[{"produto": "Café Pilão 500 g"}], ocultas=["g-cafe"])
        self.ofertas(ofertas_json())
        self.assertEqual(self.S.estados_lista()["binary_sensor.economia_oferta"]["state"], "off")


class Publicar(Cenario):
    def test_liga_publica_os_dois_e_desliga_tira(self):
        S, ha = self.S, self.ha
        self.config(lista=LISTA, sensores=True)
        self.ofertas(ofertas_json())
        S.publica_sensores_lista()
        self.assertEqual(ha.estados["sensor.economia_melhor_loja"]["state"], "Bistek")
        self.assertEqual(ha.estados["binary_sensor.economia_oferta"]["state"], "on")
        n = len(ha.pedidos_de("/states/sensor.economia_melhor_loja", "POST"))
        S.publica_sensores_lista()
        self.assertEqual(len(ha.pedidos_de("/states/sensor.economia_melhor_loja", "POST")), n, "nada mudou: não manda de novo")
        S._sensores_lista["em"] -= 901
        S.publica_sensores_lista()
        self.assertEqual(len(ha.pedidos_de("/states/sensor.economia_melhor_loja", "POST")), n + 1, "a cada 15 minutos, de novo")
        self.config(lista=LISTA, sensores=False)
        S.publica_sensor_uso()
        self.assertNotIn("sensor.economia_melhor_loja", ha.estados)
        self.assertNotIn("binary_sensor.economia_oferta", ha.estados)

    def test_desligado_ou_sem_home_assistant_nao_publica(self):
        S, ha = self.S, self.ha
        self.config(lista=LISTA)
        S.publica_sensores_lista()
        S.token_ha = lambda: None
        self.config(lista=LISTA, sensores=True)
        S.publica_sensores_lista()
        self.assertFalse(ha.pedidos_de("/states/sensor.economia_melhor_loja"))

    def test_home_assistant_fora_avisa_uma_vez(self):
        S = self.S
        self.config(lista=LISTA, sensores=True)
        S.HA_API = "http://127.0.0.1:9/api"
        S.publica_sensores_lista()
        S.publica_sensores_lista()
        self.assertEqual(len([m for m in self.log if m.startswith("sensores da lista:")]), 1)
        self.assertIsNone(S._sensores_lista["sig"])


if __name__ == "__main__":
    unittest.main()
