"""Cada rota da API (a classe Painel do server.py) no mesmo processo, com o Home Assistant e as lojas falsas: os caminhos
de sucesso e os de erro (corpo inválido ou grande, IA desligada, HA fora, busca ou teste já rodando), o acesso só pelo
ingress e as chaves que nunca voltam. O test_api.py e o test_api_fluxos.py fazem o mesmo com o servidor num processo."""
import base64
import http.client
import io
import json
import os
import threading
import urllib.error
import urllib.request
import zipfile
from unittest import mock

from apoio import CEP, Cenario, categoria, prod

PNG = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\0" * 32).decode()


class Rotas(Cenario):
    def setUp(self):
        super().setUp()
        S = self.S
        self.srv = S.ThreadingHTTPServer(("127.0.0.1", 0), S.Painel)
        self.srv.daemon_threads = True
        self.srv.handle_error = lambda *a: None  # cliente que fecha antes da resposta (os testes de tamanho)
        self.porta = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        self.config(lista=[{"produto": "Leite integral"}, {"produto": "Café Pilão 500 g"}])

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        super().tearDown()

    def pede(self, metodo, caminho, corpo=None, bruto=None, cab=None):
        dados = bruto if bruto is not None else (json.dumps(corpo).encode() if corpo is not None else None)
        h = dict({"Content-Type": "application/json"} if dados is not None else {}, **(cab or {}))
        req = urllib.request.Request(f"http://127.0.0.1:{self.porta}{caminho}", data=dados, method=metodo, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                self.cab, d = r.headers, r.read()
                st = r.status
        except urllib.error.HTTPError as e:
            self.cab, d, st = e.headers, e.read(), e.code
        if self.cab.get("Content-Type", "").startswith("application/json"):
            return st, json.loads(d)
        return st, d

    def so_tamanho(self, metodo, caminho, tamanho):
        c = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=10)
        c.putrequest(metodo, caminho)
        c.putheader("Content-Length", str(tamanho))
        c.endheaders()
        r = c.getresponse()
        d = json.loads(r.read() or b"{}")
        c.close()
        return r.status, d

    def espera_leitura(self, job):
        return self.espera(lambda: self.S.LEITURAS[job] if self.S.LEITURAS[job]["status"] != "lendo" else None)


class Pagina(Rotas):
    def test_pagina_e_index(self):
        for c in ("/", "/index.html"):
            st, html = self.pede("GET", c)
            self.assertEqual(st, 200)
            self.assertIn(b"<title>EconomIA</title>", html)
            self.assertEqual(self.cab["Cache-Control"], "no-cache")

    def test_fontes(self):
        st, d = self.pede("GET", "/fonts/barlow-condensed-700.woff")
        self.assertEqual((st, self.cab["Content-Type"], d[:4]), (200, "font/woff", b"wOFF"))
        self.assertIn("immutable", self.cab["Cache-Control"])
        self.assertEqual(self.pede("GET", "/fonts/nao-existe.woff")[0], 404)
        st, d = self.pede("GET", "/fonts/OFL.txt")
        self.assertEqual(st, 200, "a licença das fontes (nome com maiúsculas) também abre")
        self.assertIn(b"SIL", d)
        self.assertEqual(self.pede("GET", "/fonts/../server.py")[0], 404, "só nomes simples de fonte")

    def test_saude_e_rota_que_nao_existe(self):
        self.assertEqual(self.pede("GET", "/api/saude"), (200, {"ok": True}))
        self.assertEqual(self.pede("GET", "/api/nada"), (404, {"erro": "Não encontrado"}))
        self.assertEqual(self.pede("PUT", "/api/nada", {"a": 1}), (404, {"erro": "Não encontrado"}))
        self.assertEqual(self.pede("POST", "/api/nada", {"a": 1}), (404, {"erro": "Não encontrado"}))

    def test_so_pelo_ingress(self):
        S = self.S
        S.ALLOW_ALL, S.INGRESS_IPS = False, {"172.30.32.2"}
        st, d = self.pede("GET", "/api/estado")
        self.assertEqual((st, d), (403, {"erro": "Acesso só pelo Home Assistant."}))
        self.assertEqual(self.pede("PUT", "/api/config", {"cep": "1"})[0], 403)
        self.assertEqual(self.pede("POST", "/api/buscar")[0], 403)
        self.assertNotEqual(S.ler_config().get("cep"), "1", "nada gravado")


class Estado(Rotas):
    def test_estado_com_o_usuario_do_ingress(self):
        st, d = self.pede("GET", "/api/estado", cab={"X-Remote-User-Display-Name": "Davi"})
        self.assertEqual(d["usuario"], "Davi")
        self.assertEqual(set(d), {"config", "ofertas", "comparacoes", "usuario", "busca", "sync", "uso_ia", "clubes", "similares", "correria", "atalho"})
        self.assertIsNone(self.pede("GET", "/api/estado")[1]["usuario"])

    def test_o_caminho_do_atalho_no_celular(self):
        # Opções › Atalho no celular: o painel do app no Home Assistant, pelo nome do contêiner (o slug com traços)
        self.assertEqual(self.S.atalho("a1b2c3d4-ofertas-do-bairro"), "/app/a1b2c3d4_ofertas_do_bairro")
        self.assertEqual(self.S.atalho("local-ofertas-do-bairro"), "/app/local_ofertas_do_bairro")
        for h in ("meu-computador", "ofertas-do-bairro", "a1b2-resolvia", "A1-ofertas-do-bairro"):
            self.assertIsNone(self.S.atalho(h), h)
        with mock.patch.dict(os.environ, {"OFERTAS_HOST": "a1b2c3d4-ofertas-do-bairro"}):
            self.assertEqual(self.pede("GET", "/api/estado")[1]["atalho"], "/app/a1b2c3d4_ofertas_do_bairro")

    def test_busca_e_uso(self):
        self.assertEqual(self.pede("GET", "/api/busca")[1], self.S.BUSCA)
        self.assertEqual(self.pede("GET", "/api/uso-ia")[1]["hoje"]["chamadas"], 0)

    def test_corrigir_sem_vocabulario(self):
        self.assertEqual(self.pede("GET", "/api/corrigir?texto=leite")[1], {"texto": None})

    def test_sugestoes_ao_digitar(self):
        self.assertEqual(self.pede("GET", "/api/sugestoes?q=sab%C3%A3o")[1], {"nomes": []}, "sem vocabulário, nenhuma")
        self.S.aprende_nomes(["Sabão em Pó Marca Um 1kg", "Sabão em Pó Marca Dois 2kg", "Sabão Líquido Marca Um 1L"], ["Marca Um", "Marca Dois"])
        self.S.grava_vocab()  # como depois de uma busca: o vocabulário novo refaz as contas
        self.assertEqual(self.pede("GET", "/api/sugestoes?q=sab%C3%A3o")[1], {"nomes": ["Sabão em pó"]}, "visto duas vezes; o líquido, uma")
        self.assertEqual(self.pede("GET", "/api/sugestoes")[1], {"nomes": []}, "sem o texto")

    def test_produto_por_codigo_com_erro(self):
        S = self.S
        S.produto_por_ean = lambda e, c: (_ for _ in ()).throw(RuntimeError("caiu"))
        self.assertEqual(self.pede("GET", "/api/produto-por-codigo?ean=7891000100103")[1], {"ok": False, "msg": "Não consegui procurar agora (caiu)."})

    def test_produto_por_codigo_na_loja(self):
        self.lojas.catalogo["giassi"] = [prod("Leite Integral Tirol 1L", 4.89, ean="7891000100103")]
        st, d = self.pede("GET", "/api/produto-por-codigo?ean=7891000100103")
        self.assertEqual((d["ok"], d["fonte"], d["preco"]), (True, "Giassi", 4.89))


class Config(Rotas):
    def test_revisao_antiga_junta_o_que_veio_do_ha(self):
        S = self.S
        rev = S.ler_config()["rev"]
        S.DIARIO.append({"tipo": "novo", "produto": "Pão francês", "rev": rev + 1})
        S.gravar_config(S.ler_config())  # o HA gravou depois
        st, d = self.pede("PUT", "/api/config", {"rev": rev, "cep": CEP, "lista": [{"produto": "Leite integral"}]})
        self.assertTrue(d["mesclado"])
        self.assertEqual([i["produto"] for i in d["config"]["lista"]], ["Leite integral", "Pão francês"])
        self.assertEqual(d["config"]["rev"], rev + 2)

    def test_revisao_em_dia_nao_mistura(self):
        rev = self.S.ler_config()["rev"]
        self.S.DIARIO.append({"tipo": "novo", "produto": "Pão francês", "rev": rev})
        st, d = self.pede("PUT", "/api/config", {"rev": rev, "cep": CEP, "lista": []})
        self.assertEqual((d["mesclado"], d["config"]["lista"]), (False, []))

    def test_guarda_versao_e_falha_da_versao_nao_impede(self):
        S = self.S
        self.pede("PUT", "/api/config", {"rev": 99, "cep": CEP})
        self.assertEqual(len(S.listar_versoes()), 1, "cópia automática antes de gravar")
        S.guardar_versao = lambda *a, **k: (_ for _ in ()).throw(OSError("disco cheio"))
        st, d = self.pede("PUT", "/api/config", {"rev": 99, "cep": "2"})
        self.assertEqual((st, d["config"]["cep"]), (200, "2"))
        self.assertIn("versão anterior: disco cheio", self.log)

    def test_beneficios_do_clube_pela_rota(self):
        """1.24.0: POST /api/clube/beneficios; o que a IA achou vai para a página em /api/estado (clubes)."""
        self.ha.responde_ia("clube Giassi", {"clube": "Clube Giassi", "beneficios": [{"titulo": "Preço de clube", "detalhe": "Nos produtos marcados."}]})
        st, d = self.pede("POST", "/api/clube/beneficios", {"nome": "Giassi"})
        self.assertEqual((st, d["clube"]), (200, "Clube Giassi"))
        self.assertEqual(self.pede("GET", "/api/estado")[1]["clubes"][self.S.chave_loja("Giassi")]["beneficios"][0]["titulo"], "Preço de clube")
        self.assertEqual(self.pede("POST", "/api/clube/beneficios", {"nome": ""}), (400, {"erro": "Qual loja?"}))
        self.assertEqual(self.pede("POST", "/api/clube/beneficios", bruto=b"[1]")[0], 400)
        self.config(usar_ia=False)
        self.assertEqual(self.pede("POST", "/api/clube/beneficios", {"nome": "Giassi"})[0], 409)

    def test_mercados_da_regiao_pela_rota(self):
        """1.22.0: POST /api/regiao/atualizar (Mais › Lojas › Compras online); não durante a busca."""
        st, d = self.pede("POST", "/api/regiao/atualizar", {"mercados_entrega": False})
        self.assertEqual((st, d), (200, {"ok": True, "msg": ""}))
        st, d = self.pede("POST", "/api/regiao/atualizar", bruto=b"[1]")
        self.assertEqual(st, 200, "corpo estranho: vale a configuração gravada")
        self.S.BUSCA["rodando"] = True
        try:
            self.assertEqual(self.pede("POST", "/api/regiao/atualizar", {})[1], {"ok": False, "msg": "Espere a busca terminar."})
        finally:
            self.S.BUSCA["rodando"] = False

    def test_ligar_sensores_publica_no_ha(self):
        st, d = self.pede("PUT", "/api/config", {"rev": 0, "cep": CEP, "sensores": True})
        self.espera(lambda: "sensor.economia_ia_hoje" in self.ha.estados, msg="o sensor não apareceu")
        self.pede("PUT", "/api/config", {"rev": 0, "cep": CEP, "sensores": False})
        self.espera(lambda: "sensor.economia_ia_hoje" not in self.ha.estados, msg="o sensor não saiu")

    def test_corpo_vazio_invalido_ou_grande(self):
        self.assertEqual(self.pede("PUT", "/api/config", bruto=b"")[0], 413)
        self.assertEqual(self.pede("PUT", "/api/config", bruto=b"[1]"), (400, {"erro": "Conteúdo inválido."}))
        self.assertEqual(self.pede("PUT", "/api/config", bruto="ç".encode("latin-1")), (400, {"erro": "Conteúdo inválido."}))
        self.assertEqual(self.so_tamanho("PUT", "/api/config", 2 * 1024 * 1024 + 1)[0], 413)

    def test_corpo_invalido_em_cada_rota(self):
        for metodo, rota in (("PUT", "/api/integracoes"), ("PUT", "/api/ofertas"), ("POST", "/api/ler-encarte"), ("POST", "/api/ler-lista"),
                             ("POST", "/api/integracoes/ml/conectar")):
            with self.subTest(rota=rota):
                self.assertEqual(self.pede(metodo, rota, bruto=b'["nao", "objeto"]'), (400, {"erro": "Conteúdo inválido."}))
        self.assertEqual(self.S.segredos(), {}, "nada gravado")
        self.assertIsNone(self.S.ler_json(self.S.OFERTAS))

    def test_put_ofertas(self):
        self.assertEqual(self.pede("PUT", "/api/ofertas", {"lista": []}), (400, {"erro": "Faltou a lista de categorias."}))
        self.assertEqual(self.pede("PUT", "/api/ofertas", {"categorias": [], "lista": []}), (200, {"ok": True}))
        self.assertEqual(self.S.ler_json(self.S.OFERTAS), {"categorias": [], "lista": []})


class Integracoes(Rotas):
    def test_shopee_guarda_mantem_e_apaga(self):
        S = self.S
        st, d = self.pede("PUT", "/api/integracoes", {"shopee": {"app_id": " 183 0000 0001 ", "secret": "s1"}})
        self.assertEqual(d["shopee"], {"app_id": "18300000001", "tem_senha": True})
        self.pede("PUT", "/api/integracoes", {"shopee": {"app_id": "18300000001", "secret": ""}})
        self.assertEqual(S.segredos()["shopee"]["secret"], "s1", "senha em branco mantém a guardada")
        self.pede("PUT", "/api/integracoes", {"shopee": {"app_id": "999", "secret": ""}})
        self.assertEqual(S.segredos()["shopee"]["secret"], "", "outro App ID: a senha antiga não vale")
        self.assertEqual(self.pede("PUT", "/api/integracoes", {"shopee": {"app_id": "", "secret": "x"}})[0], 400)
        self.pede("PUT", "/api/integracoes", {"shopee": None})
        self.assertNotIn("shopee", S.segredos())

    def test_google_brave_e_instagram(self):
        S = self.S
        S.gravar_json(S.LOJAS_MAPA, {"lojas": {}})
        st, d = self.pede("PUT", "/api/integracoes", {"google": {"key": " AIza 123 "}, "brave": {"key": "BSA1"}, "instagram": {"token": "EAAG 1"}})
        self.assertEqual(d["google"], {"tem_chave": True})
        self.assertEqual(S.segredos()["google"], {"key": "AIza123"})
        self.assertEqual(S.segredos()["instagram"], {"token": "EAAG1"})
        self.assertIsNone(S.ler_json(S.LOJAS_MAPA), "trocar a chave do Google lê o mapa de novo")
        st, d = self.pede("GET", "/api/integracoes")
        self.assertEqual((d["google"], d["brave"], d["instagram"]), ({"tem_chave": True}, {"tem_chave": True}, {"tem_chave": True, "usuario": None}))
        self.assertNotIn("AIza123", json.dumps(d))
        self.pede("PUT", "/api/integracoes", {"google": None, "brave": None, "instagram": None})
        self.assertEqual(S.segredos(), {})

    def test_mercado_livre(self):
        S = self.S
        self.assertEqual(self.pede("PUT", "/api/integracoes", {"ml": {"app_id": "abc", "url_retorno": "https://x.com"}})[0], 400)
        self.assertEqual(self.pede("PUT", "/api/integracoes", {"ml": {"app_id": "12", "url_retorno": "ftp://x"}})[0], 400)
        st, d = self.pede("PUT", "/api/integracoes", {"ml": {"app_id": "123456", "secret": "segredo-ml", "url_retorno": "https://www.google.com"}})
        self.assertEqual((d["ml"]["app_id"], d["ml"]["tem_senha"], d["ml"]["conectado"]), ("123456", True, False))
        seg = S.segredos()
        seg["ml"].update(access_token="tok", refresh_token="r", expira=9e9)
        S.grava_segredos(seg)
        st, d = self.pede("PUT", "/api/integracoes", {"ml": {"app_id": "123456", "secret": "", "url_retorno": "https://www.google.com"}})
        self.assertTrue(d["ml"]["conectado"], "sem mudar nada, continua autorizado")
        self.assertNotIn("tok", json.dumps(self.pede("GET", "/api/integracoes")[1]["ml"]))
        self.pede("PUT", "/api/integracoes", {"ml": None})
        self.assertNotIn("ml", S.segredos())

    def test_conectar_mercado_livre(self):
        S = self.S
        st, d = self.pede("POST", "/api/integracoes/ml/conectar", {"codigo": "sem código"})
        self.assertEqual(st, 400)
        self.assertFalse(d["ok"])
        S.ml_conectar = lambda t: (_ for _ in ()).throw(KeyError("x"))
        st, d = self.pede("POST", "/api/integracoes/ml/conectar", {"codigo": "code=TG-1"})
        self.assertEqual((st, d["msg"]), (400, "Não consegui conectar ('x')."))
        S.ml_conectar = lambda t: None
        S.testar_ml = lambda: {"ok": True, "msg": "Conectado."}
        self.assertEqual(self.pede("POST", "/api/integracoes/ml/conectar", {"codigo": "code=TG-1"}), (200, {"ok": True, "msg": "Conectado."}))
        self.assertEqual(self.pede("POST", "/api/integracoes/ml/conectar", bruto=b"")[0], 413)

    def test_testar_cada_servico(self):
        S = self.S
        for s, f in (("google", "testar_google"), ("instagram", "testar_instagram"), ("brave", "testar_brave"), ("ml", "testar_ml"), ("shopee", "testar_shopee")):
            setattr(S, f, (lambda n: lambda: {"ok": True, "msg": n})(s))
            self.assertEqual(self.pede("POST", "/api/integracoes/testar", {"servico": s})[1], {"ok": True, "msg": s})
        self.assertEqual(self.pede("POST", "/api/integracoes/testar", bruto=b"{quebrado")[1]["msg"], "shopee", "sem serviço: a Shopee")
        self.assertEqual(self.pede("POST", "/api/integracoes/testar")[1]["msg"], "shopee")


class HomeAssistant(Rotas):
    def test_listas_e_ias(self):
        self.ha.lista("todo.compras", "Compras")
        self.ha.tarefa_ia("ai_task.claude", "Claude")
        self.assertEqual(self.pede("GET", "/api/todos")[1], {"listas": [{"id": "todo.compras", "nome": "Compras"}]})
        self.assertEqual(self.pede("GET", "/api/ias")[1]["tarefas"], [{"id": "ai_task.claude", "nome": "Claude", "anexos": True}])

    def test_ha_fora(self):
        self.S.HA_API = "http://127.0.0.1:9/api"
        self.assertEqual(self.pede("GET", "/api/todos"), (502, {"erro": "Não consegui falar com o Home Assistant."}))
        self.assertEqual(self.pede("GET", "/api/ias"), (502, {"erro": "Não consegui falar com o Home Assistant.", "tarefas": [], "agentes": []}))

    def test_sincronizar(self):
        self.ha.lista("todo.compras", "Compras")
        self.ha.item("todo.compras", "Ovos")
        self.config(lista=[], sync={"ativo": True, "entidade": "todo.compras"})
        st, d = self.pede("POST", "/api/sincronizar-lista")
        self.assertEqual((d["sync"]["chegaram"], d["sync"]["erro"]), (1, None))
        self.S.HA_API = "http://127.0.0.1:9/api"
        st, d = self.pede("POST", "/api/sincronizar-lista")
        self.assertEqual((st, d["sync"]["erro"]), (200, "Não consegui falar com o Home Assistant."))

    def test_testar_ia(self):
        self.ha.responde_ia("teste", {"busca": True, "fonte": "https://x.com/y"})
        self.assertEqual(self.pede("POST", "/api/testar-ia", {"uso": "busca"})[1], {"ok": True, "msg": "Pronta para buscar ofertas."})
        self.assertEqual(self.pede("POST", "/api/testar-ia", {"uso": "fotos"})[1], {"ok": False, "msg": "Nenhuma tarefa de IA no Home Assistant."})
        self.S.testar_ia = lambda uso: (_ for _ in ()).throw(self.S.ErroBusca("sem HA"))
        self.assertEqual(self.pede("POST", "/api/testar-ia", {"uso": "busca"})[1], {"ok": False, "msg": "sem HA"})

    def test_voz(self):
        S = self.S
        self.assertFalse(self.pede("GET", "/api/voz/status")[1]["pronta"], "sem fala para texto no HA")
        self.assertEqual(self.so_tamanho("POST", "/api/voz", 0), (413, {"erro": "Fale até 2 minutos de cada vez."}))
        self.assertEqual(self.so_tamanho("POST", "/api/voz", S.voz.MAX_BYTES + 5000)[0], 413)
        S.voz_texto = lambda pcm: {"texto": f"{len(pcm)} bytes", "nome": "x"}
        self.assertEqual(self.pede("POST", "/api/voz", bruto=b"\0" * 1000)[1], {"texto": "1000 bytes", "nome": "x"})
        S.voz_texto = lambda pcm: (_ for _ in ()).throw(S.ErroBusca("Não ouvi nada."))
        self.assertEqual(self.pede("POST", "/api/voz", bruto=b"\0" * 10), (400, {"erro": "Não ouvi nada."}))


class Leituras(Rotas):
    def test_ler_lista(self):
        self.ha.responde_ia("ler lista", {"itens": [{"produto": "Ovos"}]})
        self.assertEqual(self.pede("POST", "/api/ler-lista", {"texto": ""}), (400, {"erro": "Escolha uma foto ou cole o texto da mensagem."}))
        st, d = self.pede("POST", "/api/ler-lista", {"texto": "ovos"})
        self.assertEqual(st, 202)
        r = self.espera_leitura(d["id"])
        self.assertEqual(self.pede("GET", "/api/ler-lista?id=" + d["id"])[1], r)
        self.assertEqual(r["itens"], [{"produto": "Ovos", "ja_na_lista": False}])
        self.assertEqual(self.pede("GET", "/api/ler-lista")[0], 404)
        self.assertEqual(self.so_tamanho("POST", "/api/ler-lista", 16 * 1024 * 1024 + 1)[0], 413)

    def test_ler_encarte(self):
        self.ha.responde_ia("encarte Kuntze", {"ofertas": [{"produto": "Café Pilão 500 g", "preco": 15.9}]})
        self.assertEqual(self.pede("POST", "/api/ler-encarte", {"imagens": [PNG]})[0], 400)
        st, d = self.pede("POST", "/api/ler-encarte", {"imagens": [PNG], "loja": "Kuntze", "categoria": "farmacias"})
        r = self.espera_leitura(d["id"])
        self.assertEqual((r["status"], r["ofertas"]), ("pronto", 1))
        cat = next(c for c in self.S.ler_json(self.S.OFERTAS)["categorias"] if c["id"] == "farmacias")
        self.assertEqual(cat["redes"][0]["nome"], "Kuntze")

    def test_ia_desligada(self):
        self.config(usar_ia=False)
        for c in ("/api/ler-lista", "/api/ler-encarte"):
            self.assertEqual(self.pede("POST", c, {"texto": "x", "imagens": [PNG], "loja": "X"}), (400, {"erro": self.S.IA_DESLIGADA}))


class Dados(Rotas):
    def test_versoes(self):
        S = self.S
        st, d = self.pede("POST", "/api/versoes/guardar", {"motivo": "limpar"})
        self.assertTrue(d["nome"].endswith("-limpar.json"))
        st, d = self.pede("POST", "/api/versoes/guardar", {"motivo": "inventado"})
        self.assertTrue(d["nome"].endswith("-auto.json"), "motivo desconhecido vira automática")
        self.assertEqual(len(self.pede("GET", "/api/versoes")[1]["versoes"]), 2)
        S.guardar_versao = lambda *a, **k: (_ for _ in ()).throw(OSError("sem espaço"))
        self.assertEqual(self.pede("POST", "/api/versoes/guardar", {"motivo": "auto"}), (500, {"erro": "Não consegui guardar a cópia (sem espaço)."}))

    def test_restaurar(self):
        nome = self.pede("POST", "/api/versoes/guardar", {"motivo": "importar"})[1]["nome"]
        self.config(lista=[])
        st, d = self.pede("POST", "/api/versoes/restaurar", {"nome": nome})
        self.assertEqual([i["produto"] for i in d["config"]["lista"]], ["Leite integral", "Café Pilão 500 g"])
        self.assertEqual(self.pede("POST", "/api/versoes/restaurar", {"nome": "config-20200101-000000-x.json"}), (400, {"erro": "Versão não encontrada."}))

    def test_exportar(self):
        self.ofertas({"gerado_em": "2026-11-01T10:00:00", "categorias": [categoria("mercados", [("merc-giassi", "Giassi", 1.0)])],
                      "lista": [{"produto": "Leite integral", "precos": {"merc-giassi": 4.89}}]})
        st, j = self.pede("GET", "/api/exportar/lista.json")
        self.assertEqual(j["lista"][0]["mais_barato"], {"loja": "Giassi", "tipo": "Mercado", "preco": 4.89})
        self.assertIn('filename="economia-minha-lista-', self.cab["Content-Disposition"])
        st, x = self.pede("GET", "/api/exportar/lista.xlsx")
        self.assertIn("Leite integral", zipfile.ZipFile(io.BytesIO(x)).read("xl/worksheets/sheet1.xml").decode())
        st, o = self.pede("GET", "/api/exportar/ofertas.json")
        self.assertEqual(o["gerado_em"], "2026-11-01T10:00:00")


class Mapa(Rotas):
    def test_atualizar_ocupado(self):
        S = self.S
        S.BUSCA["rodando"] = True
        self.assertEqual(self.pede("POST", "/api/lojas-mapa/atualizar", {})[1], {"ok": False, "msg": "Espere a busca terminar."})
        S.BUSCA["rodando"], S.SONDA["rodando"] = False, True
        self.assertEqual(self.pede("POST", "/api/lojas-mapa/atualizar", {})[1]["msg"], "Ainda estou testando as lojas. Espere terminar.")

    def test_atualizar_com_corpo_ruim(self):
        S = self.S
        S.atualizar_lojas_mapa = lambda d: {"ok": True, "recebi": d}
        self.assertEqual(self.pede("POST", "/api/lojas-mapa/atualizar", bruto=b"{x")[1]["recebi"], {})
        self.assertEqual(self.pede("POST", "/api/lojas-mapa/atualizar", bruto=b"[1]")[1]["recebi"], {})
        self.assertEqual(self.pede("POST", "/api/lojas-mapa/atualizar", {"raio_km": 1})[1]["recebi"], {"raio_km": 1})

    def test_testar_uma_loja(self):
        S = self.S
        feito = threading.Event()
        S.sonda_loja = lambda cfg, c, r: (feito.set(), S.SONDA.update(rodando=False))
        self.assertEqual(self.pede("POST", "/api/lojas-mapa/testar-loja", {"categoria": "x", "rede": "y"}), (400, {"ok": False, "msg": "Loja inválida."}))
        self.assertEqual(self.pede("POST", "/api/lojas-mapa/testar-loja", {"categoria": "mercados", "rede": ""})[0], 400)
        self.assertEqual(self.pede("POST", "/api/lojas-mapa/testar-loja", bruto=b"{x")[0], 400)
        self.assertEqual(self.pede("POST", "/api/lojas-mapa/testar-loja", {"categoria": "online", "rede": "mkt:shopee"}), (200, {"ok": True}))
        self.assertTrue(feito.wait(5))
        S.SONDA["rodando"] = True
        self.assertEqual(self.pede("POST", "/api/lojas-mapa/testar-loja", {"categoria": "mercados", "rede": "merc-x"})[0], 409)

    def test_consultas(self):
        S = self.S
        S.gravar_json(S.LOJAS_MAPA, {"fontes": ["OpenStreetMap"], "em": "2026-11-01", "lojas": {"mercados": [{"nome": "X"}]}, "sites": {"segredo": 1}})
        self.assertEqual(self.pede("GET", "/api/lojas-mapa")[1], {"fontes": ["OpenStreetMap"], "em": "2026-11-01", "lojas": {"mercados": [{"nome": "X"}]}})
        self.assertEqual(self.pede("GET", "/api/lojas-mapa/teste")[1], S.SONDA)
        self.assertEqual(self.pede("GET", "/api/folhetos")[1], {"lojas": []})
        self.assertEqual([x["id"] for x in self.pede("GET", "/api/lojas-diretas")[1]["lojas"]], ["giassi", "angeloni"])


class Buscar(Rotas):
    def test_buscar(self):
        S = self.S
        comecou = threading.Event()
        S.buscar = lambda: (comecou.set(), S.BUSCA.update(rodando=False))
        self.assertEqual(self.pede("POST", "/api/buscar"), (202, {"ok": True}))
        self.assertTrue(comecou.wait(5))
        S.BUSCA["rodando"] = True
        self.assertEqual(self.pede("POST", "/api/buscar"), (202, {"ok": True, "ja_rodando": True}))
        S.BUSCA["rodando"] = False
        self.config(cep="")
        self.assertEqual(self.pede("POST", "/api/buscar"), (400, {"erro": "Salve o CEP em Mais › Casa antes de buscar."}))

    def test_buscar_itens(self):
        S = self.S
        pedidos = []
        S.buscar_itens = lambda itens: (pedidos.append(itens), S.BUSCA.update(rodando=False))
        self.assertEqual(self.pede("POST", "/api/buscar-itens", {"itens": ["nada"]}), (400, {"erro": "Esse item não está na lista."}))
        self.assertEqual(self.pede("POST", "/api/buscar-itens", bruto=b"")[0], 413)
        self.config(lista=[{"produto": f"Item {i}"} for i in range(12)])
        self.assertEqual(self.pede("POST", "/api/buscar-itens", {"itens": [f"item {i}" for i in range(12)] + ["Item 0"]})[0], 202)
        self.espera(lambda: pedidos)
        self.assertEqual(pedidos[0], [f"Item {i}" for i in range(8)], "o nome da lista, sem repetir, até 8")
        self.assertEqual(self.pede("POST", "/api/buscar-itens", {"itens": "Item 0"}), (400, {"erro": "Esse item não está na lista."}))

    def test_comparar(self):
        S = self.S
        pedidos = []
        S.comparar_oferta = lambda oid: (pedidos.append(oid), S.BUSCA.update(rodando=False))
        sumiu = (400, {"erro": "Essa oferta não está mais nas ofertas. Toque em Buscar para atualizar."})
        self.assertEqual(self.pede("POST", "/api/comparar", {"id": "o-1"}), sumiu)
        self.assertEqual(self.pede("POST", "/api/comparar", {"id": 3}), sumiu)
        self.assertEqual(self.pede("POST", "/api/comparar", bruto=b"[1]")[0], 400)
        self.assertEqual(self.pede("POST", "/api/comparar", bruto=b"")[0], 413)
        S.gravar_json(S.OFERTAS, {"categorias": [{"id": "mercados", "redes": [{"id": "merc-a", "nome": "A"}], "ofertas": [
            {"id": "o-1", "rede": "merc-a", "produto": "Café 500 g", "preco_oferta": 20}, {"id": "o-2", "rede": "merc-a", "produto": "Sem preço"}]}]})
        self.assertEqual(self.pede("POST", "/api/comparar", {"id": "o-2"}), sumiu, "oferta sem preço não se compara")
        self.assertEqual(self.pede("POST", "/api/comparar", {"id": "o-1"}), (202, {"ok": True}))
        self.espera(lambda: pedidos)
        self.assertEqual(pedidos, ["o-1"])
        S.BUSCA["rodando"] = True
        self.assertEqual(self.pede("POST", "/api/comparar", {"id": "o-1"}), (202, {"ok": True, "ja_rodando": True}), "uma busca de cada vez")
        S.BUSCA["rodando"] = False
        S.guarda_comparacao("o-1", {"em": "2026-11-08T10:00:00-03:00", "produto": "Café", "preco": 20, "precos": []})
        self.assertEqual(self.pede("GET", "/api/estado")[1]["comparacoes"], {"o-1": {"em": "2026-11-08T10:00:00-03:00", "produto": "Café", "preco": 20, "precos": []}})
