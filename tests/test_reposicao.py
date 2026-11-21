"""Reposição (1.46.0): o que os outros apps da casa têm para comprar de novo. Os remédios do CronologIA vêm do
share/cronologia/integracao.json; os consumíveis do InventarIA, da rota dele com a chave do share/inventario/integracao.json.
Cada app com a sua chave em Opções (config.repor), desligada de início: desligada, nada é lido. Casa de teste inventada."""
import http.server
import json
import os
import threading
import urllib.request

from apoio import Cenario


class InventarioFalso:
    """O InventarIA de mentira: a rota dos consumíveis com a chave; `resposta` troca o que ele devolve."""

    def __init__(self, chave="chave-inv"):
        self.chave, self.pedidos, self.resposta = chave, [], None
        dono = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                dono.pedidos.append((self.path, self.headers.get("Authorization"), self.headers.get("X-App")))
                st, corpo = dono.resposta or (200, {"versao": "1.81.0", "ligado": True, "consumiveis": [
                    {"id": "c1", "nome": "Pasta  térmica", "categoria": "Informática", "duracao_dias": 365, "duracao": "1 ano", "para_que_serve": "Processador"},
                    {"id": "c2", "nome": "Pilhas AA", "categoria": "", "duracao_dias": 180, "duracao": "6 meses", "para_que_serve": ""},
                    {"id": "c3", "nome": "  ", "categoria": "x"}, "torto"]})
                if self.headers.get("Authorization") != "Bearer " + dono.chave:
                    st, corpo = 401, {"erro": "chave"}
                d = corpo if isinstance(corpo, bytes) else json.dumps(corpo).encode()
                self.send_response(st)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(d)))
                self.end_headers()
                self.wfile.write(d)

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()

    def fecha(self):
        self.srv.shutdown()
        self.srv.server_close()


class Reposicao(Cenario):
    def setUp(self):
        super().setUp()
        self.inv = InventarioFalso()
        self.casa = self.S.SHARE_CASA

    def tearDown(self):
        self.inv.fecha()
        super().tearDown()

    def grava(self, app, dado):
        os.makedirs(os.path.join(self.casa, app), exist_ok=True)
        with open(os.path.join(self.casa, app, "integracao.json"), "w", encoding="utf-8") as f:
            f.write(dado if isinstance(dado, str) else json.dumps(dado))

    def test_a_pasta_da_casa_e_a_de_cima_da_do_app(self):
        self.assertEqual(self.casa, os.path.dirname(self.S.SHARE))
        self.assertEqual(os.path.basename(self.S.SHARE), "share")

    def test_sem_os_apps_na_casa(self):
        cfg = self.config(repor={"cronologia": True, "inventario": True})
        vazio = {"tem": False, "ligado": True, "itens": [], "aviso": ""}
        self.assertEqual(self.S.reposicao_fontes(cfg), {"cronologia": vazio, "inventario": vazio})
        self.grava("cronologia", "{torto")
        self.grava("inventario", "[1]")
        self.assertEqual(self.S.reposicao_fontes(cfg), {"cronologia": vazio, "inventario": vazio}, "um arquivo que não dá para ler é como não ter")

    def test_desligado_de_inicio_nada_e_lido(self):
        self.grava("cronologia", {"remedios": [{"nome": "Vitamina D", "dose": "1 cápsula", "vezes": 1}]})
        self.grava("inventario", {"url": self.inv.url, "chave": self.inv.chave})
        for repor in (None, {}, "sim", {"cronologia": "sim", "inventario": 1}):
            cfg = self.config(**({"repor": repor} if repor is not None else {}))
            f = self.S.reposicao_fontes(cfg)
            self.assertEqual(f["cronologia"], {"tem": True, "ligado": False, "itens": [], "aviso": ""}, repor)
            self.assertEqual(f["inventario"], {"tem": True, "ligado": False, "itens": [], "aviso": ""}, repor)
        self.assertEqual(self.inv.pedidos, [], "sem a chave ligada, o InventarIA nem é chamado")

    def test_os_remedios_do_cronologia(self):
        cfg = self.config(repor={"cronologia": True})
        self.grava("cronologia", {"app": "CronologIA", "versao": "1.105.1", "placar": None})
        self.assertEqual(self.S.reposicao_fontes(cfg)["cronologia"],
                         {"tem": True, "ligado": True, "itens": [], "aviso": "Atualize o CronologIA (1.106.0 ou mais novo)."})
        self.grava("cronologia", {"versao": "1.106.0", "remedios": [
            {"nome": "Vitamina  D", "dose": " 1 cápsula ", "vezes": 1}, {"nome": "vitamina d", "dose": "outra"}, {"nome": ""}, "torto",
            {"nome": "Antialérgico", "vezes": 2}]})
        f = self.S.reposicao_fontes(cfg)
        self.assertEqual(f["cronologia"], {"tem": True, "ligado": True, "aviso": "", "itens": [
            {"nome": "Vitamina D", "detalhe": "1 cápsula"}, {"nome": "Antialérgico", "detalhe": ""}]})
        self.assertEqual(f["inventario"]["ligado"], False)

    def test_os_consumiveis_do_inventario(self):
        cfg = self.config(repor={"inventario": True})
        self.grava("inventario", {"url": "http://127.0.0.1:9", "ip_url": self.inv.url + "/", "chave": self.inv.chave})
        f = self.S.reposicao_fontes(cfg)["inventario"]
        self.assertEqual(f, {"tem": True, "ligado": True, "aviso": "", "itens": [
            {"nome": "Pasta térmica", "detalhe": "Informática", "dias": 365}, {"nome": "Pilhas AA", "detalhe": "", "dias": 180}]}, "1.46.3: com a duração estimada, quando há")
        self.assertEqual(self.inv.pedidos, [("/api/integracao/consumiveis", "Bearer chave-inv", "EconomIA")], "o endereço que responde, com a chave")

    def test_o_inventario_de_antes_desligado_ou_fora(self):
        cfg = self.config(repor={"inventario": True})
        self.grava("inventario", {"url": self.inv.url, "chave": self.inv.chave})
        le = lambda: self.S.reposicao_fontes(cfg)["inventario"]
        self.inv.resposta = (404, {"error": "não encontrado"})
        self.assertEqual(le(), {"tem": True, "ligado": True, "itens": [], "aviso": "Atualize o InventarIA (1.81.0 ou mais novo)."})
        self.inv.resposta = (200, {"versao": "1.81.0", "ligado": False, "consumiveis": []})
        self.assertEqual(le()["aviso"], "Ligue Usar consumíveis no InventarIA.")
        for resposta in ((500, {"erro": "x"}), (200, b"<html>"), (200, {"consumiveis": "muitos"}), (200, [1])):
            self.inv.resposta = resposta
            self.assertEqual(le(), {"tem": True, "ligado": True, "itens": [], "aviso": "O InventarIA não respondeu."}, resposta)
        self.inv.resposta = None
        self.grava("inventario", {"url": self.inv.url, "chave": "outra"})
        self.assertEqual(le()["aviso"], "O InventarIA não respondeu.", "chave errada (401)")
        n = len(self.inv.pedidos)
        for torto in ({"url": self.inv.url}, {"chave": "x"}, {"url": "ftp://x", "ip_url": "file:///etc/passwd", "chave": "x"}):
            self.grava("inventario", torto)
            self.assertEqual(le()["aviso"], "O InventarIA não respondeu.", torto)
        self.assertEqual(len(self.inv.pedidos), n, "sem chave ou sem um endereço http, nada é chamado")

    def test_a_rota_e_a_configuracao_guardada(self):
        S = self.S
        srv = S.ThreadingHTTPServer(("127.0.0.1", 0), S.Painel)
        threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        try:
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            self.grava("cronologia", {"remedios": [{"nome": "Vitamina D", "dose": "1 cápsula"}]})
            cfg = self.config(repor={"cronologia": True, "inventario": False},
                              reposicao=[{"id": "ab12cd", "nome": "Vitamina D", "cada": 2, "unidade": "mes", "desde": "2026-11-04", "origem": "cronologia"}])
            with urllib.request.urlopen(base + "/api/reposicao/fontes", timeout=10) as r:
                f = json.loads(r.read())
            self.assertEqual(f["cronologia"]["itens"], [{"nome": "Vitamina D", "detalhe": "1 cápsula"}])
            self.assertEqual(f["inventario"], {"tem": False, "ligado": False, "itens": [], "aviso": ""})
            # a página grava a configuração inteira: a Reposição e as chaves ficam como foram
            req = urllib.request.Request(base + "/api/config", data=json.dumps(cfg).encode(), method="PUT", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as r:
                novo = json.loads(r.read())["config"]
            self.assertEqual((novo["reposicao"], novo["repor"]), (cfg["reposicao"], cfg["repor"]))
            self.assertEqual(S.ler_config()["reposicao"][0]["desde"], "2026-11-04")
        finally:
            srv.shutdown()
            srv.server_close()
