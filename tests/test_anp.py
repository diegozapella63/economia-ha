"""Preço dos combustíveis pela ANP (1.63.0; o dono: "Preço do combustível (ANP) no EconomIA. Pode seguir também"): o anp.py
(ler o arquivo, só a cidade, o resumo por produto), a busca em segundo plano do servidor, a rota e a ferramenta combustivel.
A ANP é um servidor de mentira; postos, endereços e preços inventados."""
import http.server
import json
import os
import threading
import unittest
import unittest.mock
import urllib.request
from datetime import datetime, timedelta, timezone

from apoio import limpa, servidor

CAB = "Regiao - Sigla;Estado - Sigla;Municipio;Revenda;CNPJ da Revenda;Nome da Rua;Numero Rua;Complemento;Bairro;Cep;Produto;Data da Coleta;Valor de Venda;Valor de Compra;Unidade de Medida;Bandeira"


def linha(cidade, uf, posto, rua, bairro, produto, data, preco):
    return f"S;{uf};{cidade};{posto}; 00.000.000/0001-00;{rua};10;;{bairro};89200-000;{produto};{data};{preco};;R$ / litro;BRANCA"


GAS = "﻿" + "\n".join([CAB,
    linha("JOINVILLE", "SC", "POSTO DA ANA LTDA", "RUA DAS FLORES", "CENTRO", "GASOLINA", "16/11/2026", "6,29"),
    linha("JOINVILLE", "SC", "POSTO DA ANA LTDA", "RUA DAS FLORES", "CENTRO", "GASOLINA", "23/11/2026", "5,99"),
    linha("JOINVILLE", "SC", "POSTO DO BETO LTDA", "RUA DO SOL", "GLÓRIA", "GASOLINA", "24/11/2026", "6,19"),
    linha("JOINVILLE", "SC", "POSTO VELHO", "RUA ANTIGA", "CENTRO", "GASOLINA", "02/11/2026", "4,00"),
    linha("JOINVILLE", "SC", "POSTO DA ANA LTDA", "RUA DAS FLORES", "CENTRO", "ETANOL", "23/11/2026", "4,19"),
    linha("JOINVILLE", "SC", "POSTO RUIM", "RUA X", "CENTRO", "ETANOL", "99/99/2026", "4,19"),
    linha("JOINVILLE", "SC", "POSTO RUIM", "RUA X", "CENTRO", "ETANOL", "23/11/2026", "abc"),
    linha("JOINVILLE", "PR", "POSTO DE OUTRO ESTADO", "RUA Y", "CENTRO", "GASOLINA", "23/11/2026", "1,00"),
    linha("CANOAS", "RS", "POSTO DE LONGE", "RUA Z", "CENTRO", "GASOLINA", "23/11/2026", "5,50"), "linha quebrada"])
DIESEL = "\n".join([CAB, linha("JOINVILLE", "SC", "POSTO DO BETO LTDA", "RUA DO SOL", "GLÓRIA", "DIESEL S10", "23/11/2026", "6,05")])


class AnpFalsa:
    def __init__(self):
        self.arquivos = {"/ultimas-4-semanas-gasolina-etanol.csv": GAS.encode("utf-8"), "/ultimas-4-semanas-diesel-gnv.csv": DIESEL.encode("latin-1")}
        self.robots, self.pedidos = None, []
        dono = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                dono.pedidos.append(self.path)
                corpo = dono.robots if self.path == "/robots.txt" else dono.arquivos.get(self.path)
                self.send_response(200 if corpo is not None else 404)
                self.end_headers()
                self.wfile.write(corpo or b"")
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def fechar(self):
        self.srv.shutdown()
        self.srv.server_close()


class Base(unittest.TestCase):
    def setUp(self):
        self.anp = AnpFalsa()
        self.S, self.pasta, self.log = servidor({"OFERTAS_ANP": self.anp.url})
        self.addCleanup(limpa, self.pasta)
        self.addCleanup(self.anp.fechar)
        self.S.gravar_json(self.S.FOLHETOS, {"_cep": {"cep": "89200000", "cidade": "Joinville", "uf": "SC"}})
        self.S.gravar_config({"cep": "89200-000", "raio_km": 2, "categorias": ["mercados"], "lista": [], "correria": True})


class Modulo(Base):
    def test_ler_so_a_cidade_e_o_resumo(self):
        A = self.S.anp
        ls = A.ler(GAS.split("\n"), "Joinville", "sc")
        self.assertEqual(len(ls), 5, "só Joinville/SC, com data e preço que valem")
        self.assertEqual(ls[1], {"posto": "Posto Da Ana Ltda", "bairro": "Centro", "rua": "Rua Das Flores 10", "bandeira": "Branca", "produto": "gasolina", "data": "2026-11-23", "preco": 5.99})
        r = A.resumo(ls)
        g = r["gasolina"]
        self.assertEqual((g["data"], g["n"], g["media"], [x["preco"] for x in g["postos"]]), ("2026-11-24", 2, 6.09, [5.99, 6.19]),
                         "de cada posto a coleta mais nova; o de três semanas atrás fica de fora")
        self.assertEqual(r["etanol"]["media"], 4.19)
        self.assertEqual(A.resumo([]), {})
        with self.assertRaises(ValueError):
            A.ler(["a;b;c", "1;2;3"], "Joinville", "SC")
        self.assertEqual([A.produto(x) for x in ("Álcool", "gasolina comum", "Aditivada", "S10", "GNV", "querosene", None)],
                         ["etanol", "gasolina", "gasolina aditivada", "diesel s10", "gnv", "", ""])
        self.assertEqual((A.nome_produto("diesel s10"), A.nome_produto("glp")), ("Diesel S10", "Glp"))
        self.assertEqual((A._preco("6.190,00"), A._preco("5.99"), A._preco("0,01")), (0.0, 5.99, 0.0))
        muitas = [CAB] + [linha("JOINVILLE", "SC", f"POSTO {i}", "RUA", "CENTRO", "GASOLINA", "23/11/2026", "6,00") for i in range(A.MAX_LINHAS + 5)]
        self.assertEqual(len(A.ler(muitas, "Joinville", "SC")), A.MAX_LINHAS)

    def test_baixar_linha_a_linha_e_o_limite(self):
        A = self.S.anp
        self.assertEqual(len(A.baixar(self.anp.url + "/ultimas-4-semanas-gasolina-etanol.csv", "Joinville", "SC")), 5)
        self.assertEqual(A.baixar(self.anp.url + "/ultimas-4-semanas-diesel-gnv.csv", "Joinville", "SC")[0]["bairro"], "Glória", "em latin-1 também")
        with unittest.mock.patch.object(A, "LIMITE", 100), self.assertRaises(ValueError):
            A.baixar(self.anp.url + "/ultimas-4-semanas-gasolina-etanol.csv", "Joinville", "SC")


class Servidor(Base):
    def test_busca_guarda_a_cidade_e_nao_repete(self):
        S = self.S
        self.assertEqual(S.combustivel_estado()["produtos"], [], "sem pedir, nada é buscado")
        self.assertEqual(self.anp.pedidos, [])
        e = S.combustivel_estado(buscar=True, esperar=True)
        self.assertEqual([(p["nome"], p["media"], p["n"]) for p in e["produtos"]], [("Gasolina", 6.09, 2), ("Etanol", 4.19, 1), ("Diesel S10", 6.05, 1)])
        self.assertEqual((e["cidade"], e["uf"], e["buscando"], e["erro"]), ("Joinville", "SC", False, ""))
        guardado = S.ler_json(S.COMBUSTIVEL)
        self.assertEqual(len(guardado["linhas"]), 6)
        self.assertNotIn("Canoas", json.dumps(guardado), "só a cidade da casa fica guardada")
        n = len(self.anp.pedidos)
        S.combustivel_estado(buscar=True, esperar=True)
        self.assertEqual(len(self.anp.pedidos), n, "dentro do prazo, não baixa de novo")
        guardado["buscado_em"] = (datetime.now(timezone.utc) - timedelta(days=S.COMB_DIAS + 1)).isoformat(timespec="seconds")
        S.gravar_json(S.COMBUSTIVEL, guardado)
        S.combustivel_estado(buscar=True, esperar=True)
        self.assertGreater(len(self.anp.pedidos), n, "velho, baixa de novo")
        # outra cidade: o guardado não vale
        S.gravar_json(S.FOLHETOS, {"_cep": {"cep": "1", "cidade": "Blumenau", "uf": "SC"}})
        e = S.combustivel_estado(buscar=True, esperar=True)
        self.assertEqual((e["produtos"], e["erro"]), ([], "A ANP não tem postos pesquisados em Blumenau nas últimas semanas."))

    def test_erros_sem_cep_robots_e_arquivo(self):
        S = self.S
        os.remove(S.FOLHETOS)
        S.gravar_config({"cep": "", "raio_km": 2, "categorias": ["mercados"], "lista": []})
        self.assertEqual(S.combustivel_estado(buscar=True)["erro"], "Falta o CEP da casa, em Mais › Casa.")
        with self.assertRaises(S.ErroFerramenta):
            S._ferr_combustivel({}, {}, {})
        S.gravar_json(S.FOLHETOS, {"_cep": {"cep": "89200000", "cidade": "Joinville", "uf": "SC"}})
        self.anp.robots = b"User-agent: *\nDisallow: /\n"
        self.assertEqual(S.combustivel_estado(buscar=True, esperar=True)["erro"], "O site da ANP não deixa programas abrirem esse arquivo agora.")
        S._robots_agreg.clear()
        self.anp.robots = None
        self.anp.arquivos["/ultimas-4-semanas-gasolina-etanol.csv"] = b"a;b\n1;2\n"
        self.assertEqual(S.combustivel_estado(buscar=True, esperar=True)["erro"], "Não consegui abrir os preços da ANP agora.")
        self.assertFalse(S.COMB["rodando"])

    def test_ferramenta_e_rota(self):
        S = self.S
        t = S.usar_ferramenta("combustivel", {}, "Claude")
        self.assertIn("Estou buscando os preços dos postos na ANP", t)
        fim = datetime.now() + timedelta(seconds=10)
        while S.COMB["rodando"] and datetime.now() < fim:
            pass
        t = S.usar_ferramenta("combustivel", {}, "Claude").split("\n")
        self.assertEqual(t[0], "Preços dos postos em Joinville pela pesquisa semanal da ANP (nem todo posto entra toda semana):")
        self.assertEqual(t[1:4], ["Gasolina: média R$ 6,09 em 2 postos (coleta de 24/11). Os mais baratos:", "- R$ 5,99: Posto Da Ana Ltda (Rua Das Flores 10, Centro), 23/11",
                                  "- R$ 6,19: Posto Do Beto Ltda (Rua Do Sol 10, Glória)"])
        t = S.usar_ferramenta("combustivel", {"produto": "álcool"}, "Claude").split("\n")
        self.assertEqual(t[1:], ["Etanol: média R$ 4,19 em 1 posto (coleta de 23/11). Os mais baratos:", "- R$ 4,19: Posto Da Ana Ltda (Rua Das Flores 10, Centro)"])
        self.assertIn("não tem gnv pesquisado em Joinville", S.usar_ferramenta("combustivel", {"produto": "gnv"}, "Claude"))
        with self.assertRaises(S.ErroFerramenta) as cm:
            S.usar_ferramenta("combustivel", {"produto": "querosene"}, "Claude")
        self.assertIn("produto: gasolina", str(cm.exception))
        self.assertEqual(S._reais3(5.999), "R$ 6,00")


if __name__ == "__main__":
    unittest.main()
