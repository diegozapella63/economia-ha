"""Conversa com a IA (o balão ao lado do microfone): só tarefa de IA (nunca um assistente de conversa, que mexe na casa),
o que vai para a IA (data, tela, casa, lista com preços, histórico, ofertas e cupons das lojas acompanhadas), a resposta
em JSON ou em texto solto, as ações sugeridas conferidas com a lista, IA desligada, erros, o uso contado como Conversa
e a rota POST /api/chat."""
import json

from apoio import CEP, Cenario, categoria
from ha_falso import Erro
from test_api_fluxos import Servidor

HOJE = "2026-11-02"  # segunda-feira

OFERTAS = {"versao": 2, "gerado_em": "2026-11-01T09:00:00-03:00", "categorias": [
    categoria("mercados", [("giassi", "Giassi", 1.0), ("angeloni", "Angeloni", 1.5), ("longe", "Mercado Longe", 9.0)],
              ofertas=[{"id": "g1", "rede": "giassi", "produto": "Picanha kg", "preco_normal": 89.9, "preco_oferta": 59.9, "tipo": "promo"},
                       {"id": "g2", "rede": "giassi", "produto": "Arroz 5 kg", "preco_normal": 30.0, "preco_oferta": 27.0, "tipo": "promo"},
                       {"id": "a1", "rede": "angeloni", "produto": "Cerveja lata", "preco_normal": 4.0, "preco_oferta": 2.0, "tipo": "clube"},
                       {"id": "a2", "rede": "angeloni", "produto": "Oferta escondida", "preco_normal": 10.0, "preco_oferta": 1.0},
                       {"id": "l1", "rede": "longe", "produto": "Oferta de longe", "preco_normal": 10.0, "preco_oferta": 1.0}],
              cupons=[{"rede": "giassi", "codigo": "VALE10", "beneficio": "R$ 10 de desconto", "condicao": "acima de R$ 150",
                       "valido_ate": "2026-11-30", "status": "confirmado"},
                      {"rede": "giassi", "codigo": "VELHO", "beneficio": "Cupom vencido", "valido_ate": "2026-10-01", "status": "confirmado"},
                      {"rede": "angeloni", "codigo": "TALVEZ", "beneficio": "Cupom sem confirmar", "status": "pendente"}])],
    "lista": [{"produto": "Café Pilão 500 g", "precos": {"giassi": 19.9, "angeloni": 21.5}},
              {"produto": "Leite integral", "precos": {}}]}


def lista_cfg():
    return [{"produto": "Café Pilão 500 g", "compras": ["2026-10-05", "2026-10-19"]}, {"produto": "Leite integral"},
            {"produto": "Detergente Ypê 500 ml"}]


class Conversa(Cenario):
    def setUp(self):
        super().setUp()
        self.S.hoje_br = lambda: HOJE

    def prepara(self, **kw):
        cfg = dict(categorias=["mercados"], raio_km=2, lista=lista_cfg(), clubes=["angeloni"], ocultas=["a2"],
                   perfil={"adultos": 2, "criancas": 1, "bebes": 0, "pets": {"gato": 1}, "restricoes": ["lactose"]},
                   historico=[{"produto": "Papel higiênico 12 rolos", "compras": ["2026-09-01", "2026-10-01"], "saiu": "2026-10-02"},
                              {"produto": "Sabonete", "compras": ["2026-08-01"], "saiu": "2026-08-02"},
                              {"produto": "Nunca comprado", "compras": [], "saiu": "2026-08-02"}],
                   cupons_meus=[{"id": "m1", "rede": "giassi", "beneficio": "20% em Colgate", "valido_ate": "2026-12-01"}])
        cfg.update(kw)
        self.config(**cfg)
        self.ofertas(OFERTAS)

    def conversa(self, *textos, tela="lista"):
        msgs = [{"de": "ia" if i % 2 else "eu", "texto": t} for i, t in enumerate(textos)]
        return self.S.conversar({"mensagens": msgs, "tela": tela})

    # ----- qual IA -----
    def test_so_tarefa_de_ia_nunca_assistente_de_conversa(self):
        S, ha = self.S, self.ha
        ha.tarefa_ia("ai_task.fotos", "Fotos")
        ha.tarefa_ia("ai_task.busca", "Busca")
        ha.tarefa_ia("ai_task.velha", "Velha")
        ha.agente("conversation.gemini", "Gemini")
        ha.responde_ia("conversa", {"resposta": "Oi!", "acoes": []})
        self.prepara()
        self.assertEqual(S.ia_da_conversa(), "", "sem escolha: a tarefa de IA preferida do HA")
        self.conversa("oi")
        self.assertNotIn("entity_id", ha.chamadas_ia[-1])
        self.prepara(ia={"fotos": "ai_task.fotos", "busca": "ai_task.busca"})
        self.assertEqual(S.ia_da_conversa(), "ai_task.fotos", "a IA de fotos primeiro")
        self.prepara(ia={"fotos": "", "busca": "conversation.gemini"})
        S.gravar_json(S.OPTIONS, {"ai_task_entity": "ai_task.velha"})
        self.assertEqual(S.ia_da_conversa(), "ai_task.velha", "a busca por assistente de conversa não vale: a opção do add-on")
        self.prepara(ia={"fotos": "conversation.gemini", "busca": "ai_task.busca"})
        self.assertEqual(S.ia_da_conversa(), "ai_task.busca")
        S.gravar_json(S.OPTIONS, {"ai_task_entity": "conversation.gemini"})
        self.prepara(ia={"fotos": "conversation.gemini", "busca": "conversation.gemini"})
        self.assertEqual(S.ia_da_conversa(), "", "só assistentes de conversa: nenhum deles")
        self.assertEqual(self.conversa("oi")["resposta"], "Oi!")
        self.assertEqual(ha.pedidos_de("/services/conversation/process"), [], "a conversa nunca vai para um assistente que mexe na casa")
        self.assertEqual(ha.chamadas_ia[-1]["task_name"], "EconomIA: conversa")

    # ----- o que vai para a IA -----
    def test_a_quantidade_de_cada_item(self):
        """1.14.0: o item com mais de uma unidade vai com a quantidade, na conversa e nas ferramentas do CorrerIA."""
        S = self.S
        self.prepara()
        cfg = S.ler_config()
        cfg["lista"][0]["qtd"] = 3
        S.gravar_config(cfg)
        nome = S.nome_item(cfg["lista"][0])
        self.assertIn(f"- 3 × {nome}; ", S.contexto_chat("lista"))
        self.assertIn(f"- 3 × {nome}: ", S._ferr_lista({}, S.ler_config(), S.ler_json(S.OFERTAS, {})))

    def test_o_contexto_da_tela_e_dos_dados(self):
        S = self.S
        self.prepara()
        t = S.contexto_chat("lista")
        self.assertIn("Hoje é segunda, 02/11/2026.", t)
        self.assertIn("Tela aberta no app: Minha lista.", t)
        self.assertIn("Preços da última busca, de 01/11/2026.", t)
        self.assertIn("Casa: 2 adulto(s); 1 criança(s) e 0 bebê(s); pets: 1 gato; restrições: lactose.", t)
        self.assertIn("Participa dos clubes de desconto: Angeloni.", t)
        self.assertIn("Lista de compras (3 itens):", t)
        self.assertIn("- Café Pilão 500 g; mais barato no Giassi por R$ 19,90 (também Angeloni R$ 21,50); comprado 2 vezes, "
                      "a última em 19/10/2026, costuma comprar a cada 14 dias", t)
        self.assertIn("- Leite integral; sem preço na última busca", t)
        self.assertIn("Já comprou e não está na lista: Papel higiênico 12 rolos (2x, a última em 01/10/2026); Sabonete (1x, a última em 01/08/2026).", t)
        self.assertNotIn("Nunca comprado", t, "do histórico, só o que já foi comprado")
        ofertas = t[t.index("Ofertas das lojas"):t.index("Cupons válidos")]
        self.assertIn("(3; as de maior desconto)", ofertas)
        self.assertLess(ofertas.index("Cerveja lata"), ofertas.index("Picanha kg"), "a de maior desconto primeiro")
        self.assertIn("- Cerveja lata, no Angeloni: R$ 2,00 (era R$ 4,00, 50% menos) com o clube da loja", ofertas)
        self.assertIn("- Arroz 5 kg, no Giassi: R$ 27,00 (era R$ 30,00, 10% menos)", ofertas)
        self.assertNotIn("escondida", t, "a oferta que a pessoa escondeu não vai")
        self.assertNotIn("de longe", t, "nem a de loja longe")
        self.assertIn("- Giassi: R$ 10 de desconto (código VALE10) (acima de R$ 150) até 30/11/2026", t)
        self.assertIn("- Giassi: 20% em Colgate até 01/12/2026, guardado pela pessoa", t)
        self.assertNotIn("vencido", t)
        self.assertNotIn("sem confirmar", t)
        self.assertIn("Tela aberta no app: Ofertas.", S.contexto_chat("ofertas"))
        self.assertIn("Tela aberta no app: Minha lista.", S.contexto_chat("outra"), "tela desconhecida: a lista")

    def test_quantas_ofertas_e_itens_vao(self):
        S = self.S
        muitas = [{"id": f"o{i}", "rede": "giassi", "produto": f"Produto {i:02d}", "preco_normal": 100.0, "preco_oferta": 100.0 - i}
                  for i in range(1, 51)]
        of = json.loads(json.dumps(OFERTAS))
        of["categorias"][0]["ofertas"] = muitas
        self.config(categorias=["mercados"], lista=[{"produto": f"Item {i}"} for i in range(90)])
        self.ofertas(of)
        lista = S.contexto_chat("lista")
        self.assertEqual(lista.count("- Produto "), 15, "fora da tela Ofertas, as 15 de maior desconto")
        self.assertIn("- Produto 50,", lista)
        self.assertEqual(S.contexto_chat("ofertas").count("- Produto "), 40, "na tela Ofertas, 40")
        self.assertEqual(lista.count("- Item "), 80)
        self.assertIn("- e mais 10 itens", lista)
        self.config(categorias=["mercados"], lista=[])
        self.ofertas({"categorias": []})
        vazio = S.contexto_chat("lista")
        self.assertIn("A lista de compras está vazia.", vazio)
        self.assertNotIn("Ofertas das lojas", vazio)
        self.assertNotIn("Preços da última busca", vazio)

    def test_as_instrucoes_e_a_conversa(self):
        S, ha = self.S, self.ha
        ha.responde_ia("conversa", {"resposta": "Certo.", "acoes": []})
        self.prepara()
        msgs = [{"de": "eu" if i % 2 == 0 else "ia", "texto": f"mensagem {i}"} for i in range(15)]
        msgs.append({"de": "eu", "texto": "  e agora?\n\n  com   espaços  " + "x" * 3000})
        S.conversar({"mensagens": msgs, "tela": "ofertas"})
        t = ha.chamadas_ia[-1]["instructions"]
        self.assertIn("Você é a IA do EconomIA", t)
        self.assertIn("Você não muda nada sozinho.", t)
        for tipo in ("por_na_lista", "tirar_da_lista", "comprei", "buscar", "abrir"):
            self.assertIn(f"- {tipo} (", t)
        self.assertIn("Tela aberta no app: Ofertas.", t)
        self.assertNotIn("mensagem 3\n", t, "só as últimas 12 mensagens")
        self.assertIn("(responda à última mensagem da pessoa):\nPessoa: mensagem 4\nEconomIA: mensagem 5\n", t)
        ultima = t[t.rindex("Pessoa: e agora?"):]
        self.assertTrue(ultima.startswith("Pessoa: e agora?\n\ncom espaços x"), "espaços de mais saem, quebras de linha ficam")
        self.assertEqual(len(ultima), len("Pessoa: ") + 2000, "cada mensagem com até 2000 letras")
        self.assertNotIn(CEP, t, "o CEP não precisa ir")

    # ----- a resposta -----
    def test_acoes_conferidas_com_a_lista(self):
        S, ha = self.S, self.ha
        ha.responde_ia("conversa", {"resposta": "Feito o plano.", "acoes": [
            {"tipo": "por_na_lista", "produto": "  Pão   de forma "},
            {"tipo": "por_na_lista", "produto": "leite integral"},          # já está na lista
            {"tipo": "tirar_da_lista", "produto": "Detergente Ypê 500 ml"},
            {"tipo": "comprei", "produto": "cafe pilao"},                   # só um item bate
            {"tipo": "comprei", "produto": "Café Pilão 500 g"},             # repetida
            {"tipo": "buscar", "produto": "Picanha"},                       # não está na lista
            {"tipo": "Abrir", "tela": "Ofertas"},
            {"tipo": "abrir", "tela": "carrinho"},
            {"tipo": "apagar_tudo", "produto": "Leite integral"},
            {"tipo": "por_na_lista", "produto": "x"},
            "lixo"]})
        self.prepara()
        r = self.conversa("organiza aí")
        self.assertEqual(r["resposta"], "Feito o plano.")
        self.assertEqual(r["acoes"], [{"tipo": "por_na_lista", "produto": "Pão de forma"},
                                      {"tipo": "tirar_da_lista", "produto": "Detergente Ypê 500 ml"},
                                      {"tipo": "comprei", "produto": "Café Pilão 500 g"},
                                      {"tipo": "abrir", "tela": "ofertas"}])
        self.assertEqual([i["produto"] for i in S.ler_config()["lista"]], [i["produto"] for i in lista_cfg()],
                         "nada muda sozinho: a lista fica igual")

    def test_acoes_ambiguas_e_o_limite(self):
        S = self.S
        cfg = {"lista": [{"produto": "Leite integral 1 L"}, {"produto": "Leite desnatado 1 L"}]}
        self.assertEqual(S.acoes_validas([{"tipo": "comprei", "produto": "leite"}], cfg), [], "dois itens batem: nenhuma")
        self.assertEqual(S.acoes_validas([{"tipo": "comprei", "produto": "leite integral"}], cfg),
                         [{"tipo": "comprei", "produto": "Leite integral 1 L"}])
        muitas = [{"tipo": "por_na_lista", "produto": f"Produto {i}"} for i in range(10)]
        self.assertEqual(len(S.acoes_validas(muitas, {"lista": []})), 6, "no máximo 6")
        self.assertEqual(S.acoes_validas({"tipo": "abrir"}, cfg), [], "fora de uma lista: nenhuma")
        self.assertEqual(S.acoes_validas([{"tipo": "abrir", "produto": "minha lista"}], cfg), [{"tipo": "abrir", "tela": "lista"}])

    def test_resposta_em_texto_solto_e_em_bloco(self):
        S, ha = self.S, self.ha
        self.prepara()
        ha.responde_ia("conversa", "O café está mais barato no Giassi.", vezes=1)
        self.assertEqual(self.conversa("e o café?"), {"resposta": "O café está mais barato no Giassi.", "acoes": []})
        ha.responde_ia("conversa", "Use a {chave} certa, não sei de JSON", vezes=1)
        self.assertEqual(self.conversa("oi")["resposta"], "Use a {chave} certa, não sei de JSON")
        ha.responde_ia("conversa", 'Claro!\n```json\n{"resposta": "No bloco.", "acoes": [{"tipo": "abrir", "tela": "roteiro"}]}\n```', vezes=1)
        self.assertEqual(self.conversa("oi"), {"resposta": "No bloco.", "acoes": [{"tipo": "abrir", "tela": "roteiro"}]})
        ha.responde_ia("conversa", {"texto": "Com outra chave.", "actions": [{"tipo": "abrir", "tela": "mais"}]}, vezes=1)
        self.assertEqual(self.conversa("oi"), {"resposta": "Com outra chave.", "acoes": [{"tipo": "abrir", "tela": "mais"}]})
        ha.responde_ia("conversa", {"resposta": "", "acoes": [{"tipo": "abrir", "tela": "ofertas"}]}, vezes=1)
        self.assertEqual(self.conversa("abre as ofertas")["acoes"], [{"tipo": "abrir", "tela": "ofertas"}], "só a ação, sem texto, vale")
        ha.responde_ia("conversa", {"resposta": "   ", "acoes": []}, vezes=1)
        with self.assertRaisesRegex(S.ErroBusca, "A IA não respondeu"):
            self.conversa("oi")
        u = S.uso_resumo()["hoje"]
        self.assertEqual(u["tipos"], {"conversa": 6})
        self.assertEqual(u["erros"], 0, "texto solto na conversa não é erro de formato")

    def test_ia_desligada_pergunta_vazia_e_erros(self):
        S, ha = self.S, self.ha
        self.prepara(usar_ia=False)
        with self.assertRaises(S.ErroBusca) as e:
            self.conversa("oi")
        self.assertEqual(str(e.exception), S.IA_DESLIGADA)
        self.assertEqual(ha.chamadas_ia, [], "desligada: nem pergunta")
        self.prepara()
        for dado in ({}, {"mensagens": "oi"}, {"mensagens": [{"de": "eu", "texto": "   "}]}, {"mensagens": [{"de": "eu", "texto": "oi"}, {"de": "ia", "texto": "olá"}]}):
            with self.assertRaisesRegex(S.ErroBusca, "Escreva a sua pergunta"):
                S.conversar(dado)
        self.assertEqual(ha.chamadas_ia, [])
        ha.responde_ia("conversa", Erro(429, "quota"), vezes=1)
        with self.assertRaises(S.ErroCota):
            self.conversa("oi")
        ha.responde_ia("conversa", Erro(500, "Internal Server Error"), vezes=1)
        with self.assertRaisesRegex(S.ErroBusca, r"recusou o pedido \(500\)"):
            self.conversa("oi")
        ultimas = S.uso_resumo()["ultimas"]
        self.assertEqual([(u["tipo"], u["resultado"]) for u in ultimas[:2]], [("conversa", "erro"), ("conversa", "cota")])

    def test_avaliar_um_produto_usa_a_ia_de_busca(self):
        S, ha = self.S, self.ha
        ha.tarefa_ia("ai_task.fotos", "Fotos")
        ha.tarefa_ia("ai_task.busca", "Busca")
        ha.responde_ia("conversa", {"resposta": "Vale a pena.", "acoes": []})
        self.prepara(ia={"fotos": "ai_task.fotos", "busca": "ai_task.busca"})
        self.assertEqual(S.ia_da_conversa(web=True), "ai_task.busca", "avaliar: a IA de busca primeiro (tem a busca na web)")
        r = S.conversar({"mensagens": [{"de": "eu", "texto": "Vale a pena? Picanha kg, R$ 59,90 no Giassi."}], "tela": "ofertas", "web": True})
        self.assertEqual(r["resposta"], "Vale a pena.")
        c = ha.chamadas_ia[-1]
        self.assertEqual(c["entity_id"], "ai_task.busca")
        self.assertIn("Comece com o veredito (Vale a pena, Depende ou Não vale)", c["instructions"])
        S.conversar({"mensagens": [{"de": "eu", "texto": "e o café?"}], "web": "sim"})
        self.assertEqual(ha.chamadas_ia[-1]["entity_id"], "ai_task.fotos", "só web: true vale; o resto é conversa")
        self.prepara(ia={"fotos": "ai_task.fotos", "busca": "conversation.gemini"})
        self.assertEqual(S.ia_da_conversa(web=True), "ai_task.fotos", "a de busca é assistente de conversa: fica de fora")
        self.assertEqual(S.uso_resumo()["hoje"]["tipos"], {"conversa": 2}, "conta como Conversa")

    def test_tipo_de_uso(self):
        self.assertEqual(self.S.tipo_uso("EconomIA: conversa"), "conversa")
        self.assertEqual(self.S.tipo_uso("conversa"), "conversa")


class ConversaPelaAPI(Servidor):
    """POST /api/chat no servidor de verdade."""

    def test_rota(self):
        ha = self.ha
        ha.responde_ia("conversa", {"resposta": "Tem picanha em oferta.", "acoes": [{"tipo": "por_na_lista", "produto": "Picanha kg"}]})
        self.config(lista=[{"produto": "Café Pilão 500 g"}])
        st, d = self.pede("POST", "/api/chat", {"mensagens": [{"de": "eu", "texto": "tem churrasco?"}], "tela": "ofertas"})
        self.assertEqual((st, d), (200, {"resposta": "Tem picanha em oferta.", "acoes": [{"tipo": "por_na_lista", "produto": "Picanha kg"}]}))
        self.assertIn("Tela aberta no app: Ofertas.", ha.chamadas_ia[-1]["instructions"])
        self.assertIn("- Café Pilão 500 g", ha.chamadas_ia[-1]["instructions"])
        st, d = self.pede("POST", "/api/chat", {"mensagens": []})
        self.assertEqual((st, d["erro"]), (400, "Escreva a sua pergunta."))
        st, d = self.pede("POST", "/api/chat", bruto=b"[1, 2]")
        self.assertEqual((st, d["erro"]), (400, "Conteúdo inválido."))
        self.assertEqual(self.so_tamanho("POST", "/api/chat", self.S.MAX_BODY + 1), (413, {"erro": "Conteúdo vazio ou grande demais."}),
                         "grande demais: recusa sem ler")
        st, d = self.pede("GET", "/api/uso-ia")
        self.assertEqual(d["hoje"]["tipos"].get("conversa"), 1)
        self.config(usar_ia=False)
        st, d = self.pede("POST", "/api/chat", {"mensagens": [{"de": "eu", "texto": "oi"}]})
        self.assertEqual((st, d["erro"]), (400, self.S.IA_DESLIGADA))
