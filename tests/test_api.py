"""O servidor de verdade (economia/app/server.py) num processo, contra lojas falsas: página, estado, config,
integrações (chaves nunca voltam para a página), Mercado Livre, código de barras, correção e acesso."""
import json
import os
import re
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request

from apoio import APP, CEP, NOMES_VOCAB, LojasFalsas, ean13, limpa, porta_livre, prod, servidor


def ip_da_maquina():
    """Um endereço desta máquina que não é o 127.0.0.1 (para testar o acesso de fora do Home Assistant), ou None."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip if not ip.startswith("127.") else None
    except OSError:
        return None


class Servidor(unittest.TestCase):
    permitir_todos = True

    @classmethod
    def setUpClass(cls):
        cls.lojas = LojasFalsas().__enter__()
        cls.lojas.categorias_ml_padrao()
        cls.lojas.catalogo["giassi"] = [prod("Coxinha da Asa de Frango Resfriada Kg", 21.90, "Açougue/Aves", "kg", 1, ean13("789000000001"))]
        cls.lojas.off["7896004000855"] = {"product_name": "Biscoito Recheado", "brands": "Bauducco", "quantity": "140 g"}
        # vocabulário para a correção: gravado antes de o servidor subir
        S, cls.pasta, _ = servidor()
        S.aprende_nomes(NOMES_VOCAB)
        S.grava_vocab()
        cls.porta = porta_livre()
        env = dict(os.environ, OFERTAS_DATA=cls.pasta, OFERTAS_PORT=str(cls.porta), OFERTAS_MEDIA=os.path.join(cls.pasta, "media"),
                   OFERTAS_HA_API="http://127.0.0.1:9/api", OFERTAS_HA_WS="ws://127.0.0.1:9/websocket", SUPERVISOR_TOKEN="", **cls.lojas.env())
        if cls.permitir_todos:
            env["OFERTAS_ALLOW_ALL"] = "1"
        else:
            env.pop("OFERTAS_ALLOW_ALL", None)
        cls.log = open(os.path.join(cls.pasta, "servidor.log"), "w")
        cls.proc = subprocess.Popen([sys.executable, os.path.join(APP, "server.py")], env=env, stdout=cls.log, stderr=subprocess.STDOUT)
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", cls.porta), 0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("o servidor não subiu")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(10)
        cls.log.close()
        cls.lojas.__exit__()
        limpa(cls.pasta)

    def pede(self, metodo, caminho, corpo=None, host="127.0.0.1", bruto=None):
        dados = bruto if bruto is not None else (json.dumps(corpo).encode() if corpo is not None else None)
        req = urllib.request.Request(f"http://{host}:{self.porta}{caminho}", data=dados, method=metodo,
                                     headers={"Content-Type": "application/json"} if dados is not None else {})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                tipo, dados = r.headers.get("Content-Type", ""), r.read()
                if tipo.startswith("application/json"):
                    return r.status, json.loads(dados.decode("utf-8"))
                return r.status, dados.decode("utf-8") if tipo.startswith("text/") else dados
        except urllib.error.HTTPError as e:
            txt = e.read().decode("utf-8")
            try:
                return e.code, json.loads(txt)
            except ValueError:
                return e.code, txt


class Pagina(Servidor):
    def test_pagina_e_fontes(self):
        st, html = self.pede("GET", "/")
        self.assertEqual(st, 200)
        self.assertIn("<title>EconomIA</title>", html)
        self.assertNotIn("fonts.googleapis", html, "no add-on as fontes vão embutidas")
        st, fonte = self.pede("GET", "/fonts/barlow-400.woff")
        self.assertEqual(st, 200)
        self.assertEqual(fonte[:4], b"wOFF")

    def test_mais_e_um_menu(self):
        """1.3.0: Mais é um menu (Casa, Lojas, Configurações e Sobre por último); as abas são só as de Configurações, e
        nenhum texto da página ou do servidor manda para o caminho antigo (Mais › Integrações, Mais › Opções)."""
        st, html = self.pede("GET", "/")
        self.assertEqual(st, 200)
        menu = re.search(r'<nav id="maisMenu" aria-label="Mais">(.*?)</nav>', html, re.S).group(1)
        self.assertEqual(re.findall(r'data-mais="(\w+)"', menu), ["casa", "lojas", "config", "sobre"])
        self.assertEqual(re.findall(r'<span class="mb"><b>([^<]+)</b>', menu), ["Casa", "Lojas", "Configurações", "Sobre"])
        self.assertEqual(menu.count('class="h-ic"'), 4, "cada linha com o ícone no quadradinho")
        self.assertEqual(menu.count('class="chev"'), 4, "e a seta")
        abas = re.search(r'<div class="mais-abas" id="maisAbas" role="tablist" aria-label="Seções de Configurações">(.*?)</div>', html, re.S).group(1)
        self.assertEqual(re.findall(r'data-aba="(\w+)"', abas), ["integracoes", "dados", "aparencia", "opcoes"])
        self.assertNotIn('id="aba-casa"', html)
        self.assertNotIn('id="maisFim"', html)
        with open(os.path.join(APP, "server.py"), encoding="utf-8") as f:
            servidor_txt = f.read()
        for velho in ("Mais › Integrações", "Mais › Opções", "Mais → IA do Home Assistant", "Mais → Lojas", "Salve o CEP em Mais antes"):
            self.assertNotIn(velho, html, velho)
            self.assertNotIn(velho, servidor_txt, velho)

    def test_rota_que_nao_existe(self):
        st, d = self.pede("GET", "/api/nao-existe")
        self.assertEqual(st, 404)

    def test_estado_inicial(self):
        st, d = self.pede("GET", "/api/estado")
        self.assertEqual(st, 200)
        for k in ("config", "ofertas", "busca", "sync", "uso_ia"):
            self.assertIn(k, d)


class Config(Servidor):
    def test_grava_e_conta_a_revisao(self):
        st, d = self.pede("PUT", "/api/config", {"rev": 0, "cep": CEP, "lista": [{"produto": "Leite", "compras": []}]})
        self.assertEqual(st, 200)
        rev = d["config"]["rev"]
        st, d = self.pede("PUT", "/api/config", {"rev": rev, "cep": CEP, "lista": [{"produto": "Leite", "similares": True, "ean": "7891000100103"}]})
        self.assertEqual(d["config"]["rev"], rev + 1)
        st, e = self.pede("GET", "/api/estado")
        self.assertEqual(e["config"]["lista"][0], {"produto": "Leite", "similares": True, "ean": "7891000100103"}, "campos novos do item ficam")

    def test_corpo_invalido(self):
        st, d = self.pede("PUT", "/api/config", bruto=b"{quebrado")
        self.assertEqual(st, 400)
        st, d = self.pede("PUT", "/api/config", bruto=b"[1, 2]")
        self.assertEqual(st, 400)
        st, d = self.pede("PUT", "/api/config", bruto=b"")
        self.assertEqual(st, 413)


class Integracoes(Servidor):
    def test_chaves_nunca_voltam(self):
        self.pede("PUT", "/api/integracoes", {"shopee": {"app_id": "18300000001", "secret": "senha-shopee-secreta"}})
        self.pede("PUT", "/api/integracoes", {"brave": {"key": "chave-brave-secreta"}})
        self.pede("PUT", "/api/integracoes", {"ml": {"app_id": "123456", "secret": "segredo-ml", "url_retorno": "https://www.google.com"}})
        st, d = self.pede("GET", "/api/integracoes")
        txt = json.dumps(d)
        for segredo in ("senha-shopee-secreta", "chave-brave-secreta", "segredo-ml"):
            self.assertNotIn(segredo, txt)
        self.assertTrue(d["shopee"]["tem_senha"])
        self.assertTrue(d["brave"]["tem_chave"])
        self.assertTrue(d["ml"]["tem_senha"])
        st, e = self.pede("GET", "/api/estado")
        self.assertNotIn("senha-shopee-secreta", json.dumps(e))
        modo = os.stat(os.path.join(self.pasta, "segredos.json")).st_mode & 0o777
        self.assertEqual(modo, 0o600, "segredos.json só para o dono")

    def test_shopee_sem_app_id(self):
        st, d = self.pede("PUT", "/api/integracoes", {"shopee": {"app_id": "", "secret": "x"}})
        self.assertEqual(st, 400)

    def test_mercado_livre_do_comeco_ao_fim(self):
        st, d = self.pede("PUT", "/api/integracoes", {"ml": {"app_id": "12a3456", "secret": " segredo-ml ", "url_retorno": "http://inseguro"}})
        self.assertEqual(st, 400, "URL de retorno precisa de https")
        st, d = self.pede("PUT", "/api/integracoes", {"ml": {"app_id": "12a3456", "secret": " segredo-ml ", "url_retorno": "https://www.google.com"}})
        self.assertEqual(st, 200)
        self.assertEqual(d["ml"]["app_id"], "123456", "só os dígitos do App ID")
        self.assertFalse(d["ml"]["conectado"])
        self.assertIn("client_id=123456", d["ml"]["autorizar"])
        st, d = self.pede("POST", "/api/integracoes/ml/conectar", {"codigo": "https://www.google.com/?code=TG-errado"})
        self.assertEqual(st, 400)
        self.assertFalse(d["ok"])
        st, d = self.pede("POST", "/api/integracoes/ml/conectar", {"codigo": "https://www.google.com/?code=TG-abc123"})
        self.assertEqual(st, 200)
        self.assertTrue(d["ok"])
        self.assertIn("Carnes Bovinas", d["msg"])
        st, d = self.pede("GET", "/api/integracoes")
        self.assertTrue(d["ml"]["conectado"])
        self.assertNotIn("tok-", json.dumps(d), "o acesso também não volta")
        # salvar de novo sem mudar nada mantém a autorização; trocar a URL pede outra
        st, d = self.pede("PUT", "/api/integracoes", {"ml": {"app_id": "123456", "secret": "", "url_retorno": "https://www.google.com"}})
        self.assertTrue(d["ml"]["conectado"])
        st, d = self.pede("PUT", "/api/integracoes", {"ml": {"app_id": "123456", "secret": "", "url_retorno": "https://outro.exemplo.com"}})
        self.assertFalse(d["ml"]["conectado"])
        st, d = self.pede("POST", "/api/integracoes/testar", {"servico": "ml"})
        self.assertFalse(d["ok"])
        self.pede("PUT", "/api/integracoes", {"ml": None})
        st, d = self.pede("GET", "/api/integracoes")
        self.assertEqual(d["ml"]["app_id"], "")


class CodigoECorrecao(Servidor):
    def test_produto_por_codigo(self):
        self.pede("PUT", "/api/config", {"rev": 99, "cep": CEP, "lista": []})
        st, d = self.pede("GET", "/api/produto-por-codigo?ean=" + ean13("789000000001"))
        self.assertEqual((d["ok"], d["fonte"], d["preco"]), (True, "Giassi", 21.9))
        st, d = self.pede("GET", "/api/produto-por-codigo?ean=7896004000855")
        self.assertEqual((d["ok"], d["fonte"]), (True, "Open Food Facts"))
        st, d = self.pede("GET", "/api/produto-por-codigo?ean=123")
        self.assertFalse(d["ok"])

    def test_corrigir(self):
        st, d = self.pede("GET", "/api/corrigir?texto=" + urllib.parse.quote("Álcool de lompeza"))
        self.assertEqual(d["texto"], "Álcool de limpeza")
        st, d = self.pede("GET", "/api/corrigir?texto=Leite")
        self.assertIsNone(d["texto"])
        st, d = self.pede("GET", "/api/corrigir")
        self.assertIsNone(d["texto"])


@unittest.skipUnless(ip_da_maquina(), "esta máquina não tem outro endereço além do 127.0.0.1")
class Acesso(Servidor):
    permitir_todos = False

    def test_so_pelo_home_assistant(self):
        st, d = self.pede("GET", "/api/estado", host=ip_da_maquina())
        self.assertEqual(st, 403)
        self.assertIn("Home Assistant", d["erro"])
        st, d = self.pede("GET", "/api/estado")
        self.assertEqual(st, 200, "o ingress (e o 127.0.0.1) entram")


import urllib.parse  # noqa: E402

if __name__ == "__main__":
    unittest.main()
