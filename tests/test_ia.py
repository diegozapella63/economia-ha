"""A IA do Home Assistant pelo HA falso: ai_task.generate_data e conversation.process (formato, erros, cota), a IA
escolhida em Mais, o uso contado em uso_ia.json e o sensor, IA desligada, a lista de IAs, Testar a IA e os pedidos
(o que vai para a IA: casa, lista, lojas, clube, mapa, online; nunca o e-mail)."""
import contextlib
import importlib
import io
import json
import os

from apoio import CEP, Cenario, categoria
from ha_falso import Erro


class ChamarIA(Cenario):
    def test_resposta_estruturada_e_o_que_vai_no_pedido(self):
        S, ha = self.S, self.ha
        self.config()
        ha.responde_ia("teste", {"ok": 1})
        self.assertEqual(S.chamar_ai_task("EconomIA: teste", "instruções"), {"ok": 1})
        corpo = ha.chamadas_ia[-1]
        self.assertEqual(corpo, {"task_name": "EconomIA: teste", "instructions": "instruções"}, "sem IA escolhida: a preferida do HA")
        p = ha.pedidos_de("/services/ai_task/generate_data")[-1]
        self.assertIn("return_response", p[1])
        self.assertEqual(p[2].get("Authorization"), "Bearer " + ha.token, "a chave do Supervisor vai no cabeçalho")

    def test_ia_escolhida_e_a_opcao_antiga_do_add_on(self):
        S, ha = self.S, self.ha
        ha.tarefa_ia("ai_task.claude", "Claude")
        ha.tarefa_ia("ai_task.velha", "Velha")
        ha.responde_ia("x", {"ok": True})
        self.config()
        S.gravar_json(S.OPTIONS, {"ai_task_entity": "ai_task.velha"})
        S.chamar_ai_task("EconomIA: x", "i")
        self.assertEqual(ha.chamadas_ia[-1]["entity_id"], "ai_task.velha", "em branco em Mais: a opção do add-on")
        self.config(ia={"busca": "ai_task.claude", "fotos": "ai_task.velha"})
        S.chamar_ai_task("EconomIA: x", "i")
        self.assertEqual(ha.chamadas_ia[-1]["entity_id"], "ai_task.claude")
        S.chamar_ai_task("EconomIA: x", "i", [{"media_content_id": "media-source://x", "media_content_type": "image/jpeg"}], uso="fotos")
        self.assertEqual(ha.chamadas_ia[-1]["entity_id"], "ai_task.velha", "fotos: a IA de fotos")
        self.assertEqual(ha.chamadas_ia[-1]["attachments"][0]["media_content_id"], "media-source://x")

    def test_resposta_em_texto(self):
        S, ha = self.S, self.ha
        self.config()
        ha.responde_ia("bloco", 'Claro! Aqui está:\n```json\n{"lista": [{"item": 1}],}\n```')
        self.assertEqual(S.chamar_ai_task("EconomIA: bloco", "i"), {"lista": [{"item": 1}]}, "bloco de código e vírgula sobrando")
        ha.responde_ia("aspas", json.dumps(json.dumps({"a": 1})))
        self.assertEqual(S.chamar_ai_task("EconomIA: aspas", "i"), {"a": 1}, "JSON entregue como texto entre aspas")
        ha.responde_ia("conversa", "Não consegui pesquisar agora, desculpe.")
        with self.assertRaises(S.ErroFormato) as e:
            S.chamar_ai_task("EconomIA: conversa", "i")
        self.assertIn("Não consegui pesquisar agora", str(e.exception))
        u = S.uso_resumo()["hoje"]
        self.assertEqual((u["chamadas"], u["erros"]), (3, 1), "formato errado conta como erro")
        self.assertEqual(json.loads(open(S.USO_FILE).read())["ultimas"][0]["resultado"], "formato")

    def test_erros_do_home_assistant(self):
        S, ha = self.S, self.ha
        self.config(ia={"busca": "ai_task.sumiu"})
        with self.assertRaisesRegex(S.ErroBusca, "Falta uma IA"):
            S.chamar_ai_task("EconomIA: a", "i")
        self.config()
        casos = [(Erro(401, "Unauthorized"), "não tem permissão"),
                 (Erro(500, "Internal error: boom"), r"recusou o pedido \(500\): Internal error: boom"),
                 (Erro(400, "This entity does not support attachments"), "não lê imagens")]
        for i, (erro, msg) in enumerate(casos):
            ha.responde_ia(f"caso{i}", erro)
            anexos = [{"media_content_id": "m", "media_content_type": "image/png"}] if i == 2 else None
            with self.assertRaisesRegex(S.ErroBusca, msg):
                S.chamar_ai_task(f"EconomIA: caso{i}", "i", anexos, uso="fotos" if anexos else "busca")

    def test_cota(self):
        S, ha = self.S, self.ha
        self.config()
        self.assertTrue(S.e_cota("Error 429: Too Many Requests"))
        self.assertTrue(S.e_cota("RESOURCE_EXHAUSTED"))
        self.assertTrue(S.e_cota("You exceeded your current quota"))
        self.assertTrue(S.e_cota("rate limit reached"))
        self.assertFalse(S.e_cota("Erro 500"))
        self.assertFalse(S.e_cota(None))
        ha.responde_ia("a", Erro(429, "Too Many Requests"))
        ha.responde_ia("b", Erro(500, '{"error": {"status": "RESOURCE_EXHAUSTED"}}'))
        for t in ("a", "b"):
            with self.assertRaises(S.ErroCota) as e:
                S.chamar_ai_task("EconomIA: " + t, "i")
            self.assertIn("A cota da IA acabou", str(e.exception))
        u = S.uso_resumo()["hoje"]
        self.assertEqual((u["chamadas"], u["cota"], u["erros"]), (2, 2, 0), "cota não conta como erro")

    def test_sem_home_assistant(self):
        S = self.S
        self.config()
        S.HA_API = "http://127.0.0.1:9/api"
        with self.assertRaisesRegex(S.ErroBusca, "Não consegui falar com o Home Assistant"):
            S.chamar_ai_task("EconomIA: x", "i")
        with self.assertRaisesRegex(S.ErroBusca, "Não consegui falar com o Home Assistant"):
            S.ha_api("GET", "/states")
        os.environ.pop("SUPERVISOR_TOKEN")
        with self.assertRaisesRegex(S.ErroBusca, "não tem acesso ao Home Assistant"):
            S.chamar_ai_task("EconomIA: x", "i")
        with self.assertRaisesRegex(S.ErroBusca, "não tem acesso"):
            S.listas_ha()
        self.assertEqual(S.uso_resumo()["hoje"]["erros"], 2)

    def test_ia_desligada_nao_chama_nada(self):
        S, ha = self.S, self.ha
        self.config(usar_ia=False)
        self.assertFalse(S.ia_ligada())
        self.assertTrue(S.ia_ligada({}), "sem a opção, a IA fica ligada")
        with self.assertRaisesRegex(S.ErroBusca, "A IA está desligada"):
            S.chamar_ai_task("EconomIA: x", "i")
        self.assertEqual(ha.chamadas_ia, [])
        self.assertEqual(S.uso_resumo()["hoje"]["chamadas"], 0, "nem conta como chamada")

    def test_opcoes_com_padrao(self):
        S = self.S
        self.assertTrue(S.opcao("itens_sem_preco", {}))
        self.assertTrue(S.opcao("nova_opcao", {}), "opção desconhecida: ligada")
        self.assertFalse(S.opcao("folhetos", {"opcoes": {"folhetos": False}}))
        self.assertFalse(S.opcao("folhetos", {"opcoes": {"folhetos": "sim"}}), "só True liga")
        self.config(opcoes={"encartes_auto": False})
        self.assertFalse(S.opcao("encartes_auto"))


class Conversa(Cenario):
    def test_assistente_de_conversa(self):
        S, ha = self.S, self.ha
        self.config(ia={"busca": "conversation.gemini"})
        ha.responde_conversa("conversation.gemini", '```json\n{"lista": []}\n```')
        self.assertEqual(S.chamar_ai_task("EconomIA: mercados", "procure"), {"lista": []})
        p = ha.pedidos_de("/services/conversation/process")[-1]
        self.assertEqual(p[3], {"text": "procure", "agent_id": "conversation.gemini"})
        self.assertEqual(ha.chamadas_ia, [], "assistente de conversa não usa ai_task")
        with self.assertRaisesRegex(S.ErroBusca, "não lê imagens"):
            S.chamar_ai_task("EconomIA: ler lista", "i", [{"media_content_id": "m", "media_content_type": "image/jpeg"}])
        self.assertEqual(len(ha.pedidos_de("/services/conversation/process")), 1, "nem pergunta")

    def test_erro_e_cota_na_conversa(self):
        S, ha = self.S, self.ha
        self.config(ia={"busca": "conversation.gemini"})
        ha.responde_conversa("gemini", "Desculpe, não entendi", tipo="error", vezes=1)
        with self.assertRaisesRegex(S.ErroBusca, "respondeu com erro: Desculpe, não entendi"):
            S.chamar_ai_task("EconomIA: x", "i")
        ha.responde_conversa("gemini", "Error talking to Google Generative AI: 429 RESOURCE_EXHAUSTED", vezes=1)
        with self.assertRaises(S.ErroCota) as e:
            S.chamar_ai_task("EconomIA: x", "i")
        self.assertIn("(Google Gemini)", str(e.exception))
        self.assertEqual(S.uso_resumo()["hoje"]["ias"], {"conversation.gemini": 2})


class UsoESensor(Cenario):
    def test_tipos_e_entidades_contados(self):
        S, ha = self.S, self.ha
        ha.tarefa_ia("ai_task.claude", "Claude")
        self.config(ia={"fotos": "ai_task.claude"})
        ha.responde_ia("", {"ok": True})
        for nome, uso in (("EconomIA: mercados", "busca"), ("EconomIA: itens sem preço", "busca"), ("EconomIA: encarte Giassi", "fotos"),
                          ("EconomIA: ler lista", "fotos"), ("EconomIA: ler cupons", "fotos"), ("EconomIA: falar", "fotos")):
            S.chamar_ai_task(nome, "x" * 400, [{"media_content_id": "m", "media_content_type": "image/png"}] if uso == "fotos" else None, uso=uso)
        h = S.uso_resumo()["hoje"]
        self.assertEqual(h["tipos"], {"busca": 1, "itens": 1, "encarte": 1, "fotos": 1, "cupons": 1, "fala": 1})
        self.assertEqual(h["ias"], {"padrão do Home Assistant": 2, "ai_task.claude": 4})
        self.assertEqual(h["imagens"], 4)
        self.assertGreaterEqual(h["tokens"], 6 * 100, "uns 4 caracteres por token")

    def test_sensor_ligado_e_desligado(self):
        S, ha = self.S, self.ha
        self.config(sensores=True)
        ha.responde_ia("", {"ok": True})
        S.chamar_ai_task("EconomIA: mercados", "i")
        e = self.espera(lambda: ha.estados.get("sensor.economia_ia_hoje"), msg="o sensor não foi publicado")
        self.assertEqual(e["state"], "1")
        self.assertEqual(e["attributes"]["state_class"], "total_increasing")
        self.assertEqual(e["attributes"]["por_tipo"], {"busca": 1})
        self.config(sensores=False)
        S.publica_sensor_uso()
        self.assertNotIn("sensor.economia_ia_hoje", ha.estados, "desligado: o sensor sai do HA")
        self.assertTrue(ha.pedidos_de("/states/sensor.economia_ia_hoje", "DELETE"))


class UsoBordas(Cenario):
    """O histórico de uso fica com 120 dias, o sensor que falha avisa uma vez por dia, a conta do uso que falha não
    derruba a chamada, e a lista de IAs ignora estados estranhos."""

    def test_historico_de_120_dias(self):
        S = self.S
        S.gravar_json(S.USO_FILE, {"dias": {f"2025-{m:02d}-{d:02d}": {"chamadas": 1} for m in range(1, 13) for d in range(1, 29)}})
        S.registra_uso("EconomIA: mercados", None, 40, 0, 0, 1, "ok")
        dias = S.ler_json(S.USO_FILE)["dias"]
        self.assertEqual(len(dias), S.DIAS_USO)
        self.assertIn(S.hoje_br(), dias)
        self.assertNotIn("2025-01-01", dias, "os mais antigos saem")

    def test_sensor_que_falha_avisa_uma_vez_por_dia(self):
        S = self.S
        self.config(sensores=True)
        S._sensor_dia.update(dia=None, ligado=True)
        S.HA_API = "http://127.0.0.1:9/api"
        S.publica_sensor_uso()
        S.publica_sensor_uso()
        self.assertEqual(len([m for m in self.log if m.startswith("sensor de uso da IA:")]), 1)

    def test_conta_do_uso_que_falha(self):
        S, ha = self.S, self.ha
        self.config()
        ha.responde_ia("", {"ok": True})
        S.registra_uso = lambda *a: (_ for _ in ()).throw(OSError("sem disco"))
        self.assertEqual(S.chamar_ai_task("EconomIA: mercados", "i"), {"ok": True})
        self.assertIn("uso da IA: sem disco", self.log)

    def test_estados_estranhos_na_lista_de_ias(self):
        S, ha = self.S, self.ha
        ha.tarefa_ia("ai_task.claude", "Claude")
        S.ha_api = (lambda orig: (lambda m, c, *a, **k: (orig(m, c, *a, **k) or []) + ["lixo", None] if c == "/states" else orig(m, c, *a, **k)))(S.ha_api)
        self.assertEqual(S.ias_disponiveis()["tarefas"], [{"id": "ai_task.claude", "nome": "Claude", "anexos": True}])

    def test_teste_com_json_quebrado(self):
        S, ha = self.S, self.ha
        self.config()
        ha.responde_ia("teste", 'Achei: {"busca": true, "exemplo": "Giassi" "fonte"}', vezes=1)
        r = S.testar_ia("busca")
        self.assertFalse(r["ok"])
        self.assertIn("formato que o EconomIA não conseguiu ler", r["msg"])


class ListaDeIAs(Cenario):
    def test_tarefas_e_assistentes(self):
        S, ha = self.S, self.ha
        ha.tarefa_ia("ai_task.openai", "OpenAI", anexos=False)
        ha.tarefa_ia("ai_task.claude", "Claude")
        ha.agente("conversation.home_assistant", "Home Assistant")
        ha.agente("conversation.gemini", "Google Gemini")
        ha.lista("todo.compras", "Compras")
        r = S.ias_disponiveis()
        self.assertEqual(r["tarefas"], [{"id": "ai_task.claude", "nome": "Claude", "anexos": True},
                                        {"id": "ai_task.openai", "nome": "OpenAI", "anexos": False}])
        self.assertEqual(r["agentes"], [{"id": "conversation.gemini", "nome": "Google Gemini"}], "o assistente padrão do HA fica de fora")


class TestarIA(Cenario):
    def test_busca(self):
        S, ha = self.S, self.ha
        self.config()
        ha.responde_ia("teste", {"busca": True, "exemplo": "Giassi, café Pilão 500 g por R$ 19,90", "fonte": "https://www.giassi.com.br/cafe"}, vezes=1)
        r = S.testar_ia("busca")
        self.assertEqual(r, {"ok": True, "msg": "Pronta para buscar ofertas. Exemplo: Giassi, café Pilão 500 g por R$ 19,90"})
        self.assertIn("Use a busca na web agora", ha.chamadas_ia[-1]["instructions"])
        ha.responde_ia("teste", {"erro": "sem_busca"}, vezes=1)
        self.assertEqual(S.testar_ia("busca"), {"ok": False, "msg": S.SEM_BUSCA})
        ha.responde_ia("teste", {"busca": True, "exemplo": "x", "fonte": "não sei"}, vezes=1)
        self.assertFalse(S.testar_ia("busca")["ok"], "sem link da fonte: não usou a busca")
        ha.responde_ia("teste", "Não tenho acesso à internet.", vezes=1)
        r = S.testar_ia("busca")
        self.assertFalse(r["ok"])
        self.assertIn('respondeu sem usar a busca na web ("Não tenho acesso à internet.")', r["msg"])
        ha.responde_ia("teste", Erro(429, "quota"), vezes=1)
        self.assertIn("A cota da IA acabou", S.testar_ia("busca")["msg"])

    def test_fotos(self):
        S, ha = self.S, self.ha
        self.config()
        self.assertEqual(S.testar_ia("fotos"), {"ok": False, "msg": "Nenhuma tarefa de IA no Home Assistant."})
        ha.tarefa_ia("ai_task.claude", "Claude")
        ha.tarefa_ia("ai_task.texto", "Só texto", anexos=False)
        self.assertEqual(S.testar_ia("fotos")["msg"], "Usando a IA preferida do Home Assistant.")
        for ent, ok, msg in (("ai_task.claude", True, "Pronta para ler fotos."), ("ai_task.texto", False, "Essa IA não lê imagens."),
                             ("ai_task.sumiu", False, "Essa IA não existe mais no Home Assistant."),
                             ("conversation.gemini", False, "Assistente de conversa não lê imagens. Escolha uma tarefa de IA.")):
            self.config(ia={"fotos": ent})
            self.assertEqual(S.testar_ia("fotos"), {"ok": ok, "msg": msg}, ent)
        self.assertEqual(ha.chamadas_ia, [], "testar fotos não gasta IA")


class Pedidos(Cenario):
    def cfg(self, **kw):
        c = {"cep": CEP, "raio_km": 3, "categorias": ["farmacias", "mercados", "petshops", "online"],
             "perfil": {"adultos": 2, "criancas": 1, "bebes": 0, "pets": {"gato": 1, "cachorro": 0}, "restricoes": ["lactose"],
                        "interesses": ["cafe"], "nunca": ["alcool"]},
             "lista": [{"produto": "Leite integral"}, {"produto": "Café Pilão 500 g"}, {"produto": "Dipirona"}],
             "lojas": {"ignorar": ["merc-longe"], "manter": ["farm-nissei"],
                       "adicionar": [{"categoria": "farmacias", "nome": "Farmácia do Zé", "site": "https://farmaciadoze.com.br/ofertas"}]},
             "clubes": ["farm-panvel"], "online": {"marketplaces": ["mercadolivre", "amazon", "ifood", "shopee"], "assinaturas": ["prime"]}}
        c.update(kw)
        return c

    def test_casa_e_itens(self):
        S = self.S
        casa, excluir, restr, inter = S.descreve_casa(self.cfg())
        self.assertEqual(casa, "2 adulto(s); 1 criança(s) e 0 bebê(s); pets: 1 gato")
        self.assertEqual((excluir, restr, inter), (["etiqueta alcool"], ["lactose"], ["cafe"]))
        casa, excluir, _, _ = S.descreve_casa({"perfil": {"pets": ["cachorro"]}})
        self.assertEqual(casa, "1 adulto(s); sem crianças; pets: 1 cachorro")
        self.assertEqual(excluir, ["produtos de bebê e infantis"])
        self.assertIn("produtos para animais", S.descreve_casa({})[1])
        self.ofertas({"lista": [{"produto": "Leite integral", "base": {"quantidade": 1, "unidade": "L"}},
                                {"produto": "Café Pilão 500 g", "base": {"quantidade": 0.5, "unidade": "kg"}}]})
        self.assertEqual(S.itens_prompt(self.cfg()), ["1) Leite integral (base: 1 L)", "2) Café Pilão 500 g (base: 500 g)", "3) Dipirona"])
        self.assertEqual(S.fmt_base({"quantidade": 0.35, "unidade": "L"}), "350 ml")
        self.assertEqual(S.fmt_base({"quantidade": 12, "unidade": "un", "rotulo": "rolo"}), "12 rolo")

    def test_pedido_das_lojas_fisicas(self):
        S = self.S
        self.ofertas({"categorias": [categoria("farmacias", [("farm-panvel", "Panvel", 1.2), ("farm-nissei", "Nissei", 5.0)])]})
        cfg = dict(self.cfg(), _ja_tenho={"farmacias": ["Nissei"]},
                   _mapa={"farmacias": [{"nome": "Panvel", "endereco": "Rua A, 10", "distancia_km": 1.2}]})
        t = S.instrucoes_para("farmacias", cfg)
        for trecho in (f"perto do CEP {CEP}, num raio de 3 km", "Casa: 2 adulto(s)", "Não traga: etiqueta alcool", "Restrições: lactose",
                       "Interesses, que devem vir primeiro: cafe", "1) Leite integral; 2) Café Pilão 500 g; 3) Dipirona",
                       "Lojas para ignorar: merc-longe", "Lojas para incluir mesmo mais longe: farm-nissei",
                       "Farmácia do Zé (site: https://farmaciadoze.com.br/ofertas)", '"receita": "tarja"',
                       'O morador é do clube de Panvel: traga o "preco_clube"', "já vieram direto do site delas: Nissei",
                       "Lojas do raio, pelo mapa", "Panvel (Rua A, 10), 1,2 km"):
            self.assertIn(trecho, t)
        self.assertIn('"pet" e "gato" ou "cachorro"', S.instrucoes_para("petshops", cfg))
        self.assertNotIn("clube de", S.instrucoes_para("mercados", cfg), "clube só das lojas daquela categoria")
        self.assertNotIn("Lojas do raio, pelo mapa", S.instrucoes_para("mercados", cfg))

    def test_pedido_online(self):
        S = self.S
        self.ofertas({"categorias": [categoria("mercados", [("merc-giassi", "Giassi", 1.0), ("merc-longe", "Mercado Longe", 9.0)])]})
        t = S.instrucoes_para("online", self.cfg())
        self.assertIn("em Mercado Livre, Amazon, iFood, Shopee para entrega no CEP", t)
        self.assertIn("Assinaturas do morador: Amazon Prime", t)
        self.assertIn("No iFood e no Rappi", t)
        self.assertIn("Não precisa trazer estas lojas, que ficam perto e já são buscadas: Giassi.", t)
        self.assertEqual(S.lojas_perto(self.cfg()), ["Giassi"])
        S.grava_segredos({"shopee": {"app_id": "1", "secret": "s"}})
        self.assertTrue(S.shopee_pronta())
        self.assertEqual(S.mkts_online(self.cfg()), ["Mercado Livre", "Amazon", "iFood"], "a Shopee vem pela API, não pela IA")
        sem = S.instrucoes_online(self.cfg(online={"marketplaces": ["amazon"], "mercados_entrega": False}))
        self.assertIn("em Amazon para entrega", sem)
        self.assertNotIn("Mercados que entregam", sem)
        self.assertNotIn("No iFood e no Rappi", sem)
        self.assertEqual(S.entrega_txt(self.cfg(online={"mercados_entrega": False})), "")
        self.assertEqual(S.ja_tenho_txt(self.cfg(), "online"), "")

    def test_nunca_vai_o_email(self):
        S = self.S
        cfg = self.cfg(email="davi.souza@exemplo.com.br", usuario="davi.souza@exemplo.com.br")
        textos = [S.instrucoes_para(c, cfg) for c in ("farmacias", "mercados", "petshops", "online")]
        textos += [S.instrucoes_focada(cfg, ["Leite integral"], ["mercados", "online"]), S.instrucoes_leitura("leite", 0, cfg),
                   S.instrucoes_encarte({"nome": "Giassi", "site": None}, "", 1, cfg), S.instrucoes_cupons(1, ["Giassi"])]
        for t in textos:
            self.assertNotIn("@exemplo.com.br", t)


class Registro(Cenario):
    def test_linha_do_registro(self):
        S = importlib.reload(self.S)  # o log de verdade (o servidor() dos testes troca por uma lista)
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            S.log("busca concluída")
            with self.assertRaises(S.ErroFormato):
                S.extrai_json("sem json " * 200)
        linhas = saida.getvalue().splitlines()
        self.assertRegex(linhas[0], r"^\[ofertas\] \d\d:\d\d:\d\d busca concluída$")
        self.assertIn("resposta da IA fora do formato: sem json", linhas[1])
        self.assertLess(len(linhas[1]), 700, "a resposta vai cortada para o registro")
