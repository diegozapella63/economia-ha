"""A Minha lista com a lista de tarefas do Home Assistant (todo.*): o que chega do HA (item novo, item concluído =
compra de hoje), o que vai para o HA (item novo do painel, item que está acabando), a primeira vez, opções desligadas,
o diário que junta as mudanças do HA com o painel (aplicar_diario) e o laço de cada minuto."""
import types

from apoio import Cenario


class Sincronizar(Cenario):
    ENT = "todo.compras"

    def setUp(self):
        super().setUp()
        self.ha.lista(self.ENT, "Compras")
        self.ha.lista("todo.casa", "Afazeres da casa")
        self.pao = self.ha.item(self.ENT, "Pão francês")
        self.ha.item(self.ENT, "Leite", "completed")

    def sync(self, **kw):
        return dict({"ativo": True, "entidade": self.ENT}, **kw)

    def lista(self):
        return {i["produto"]: i for i in self.S.ler_config()["lista"]}

    def no_ha(self):
        return [(i["summary"], i["status"]) for i in self.ha.todos[self.ENT]]

    def test_listas_do_home_assistant(self):
        self.assertEqual(self.S.listas_ha(), [{"id": "todo.casa", "nome": "Afazeres da casa"}, {"id": "todo.compras", "nome": "Compras"}])
        self.assertEqual([i["summary"] for i in self.S.itens_ha(self.ENT)], ["Pão francês", "Leite"])
        p = self.ha.pedidos_de("/services/todo/get_items")[-1]
        self.assertEqual(p[3], {"entity_id": self.ENT, "status": ["needs_action", "completed"]})

    def test_ida_e_volta(self):
        S, ha = self.S, self.ha
        hoje = S.hoje_br()
        d = lambda n: (S.datetime.strptime(hoje, "%Y-%m-%d") - S.timedelta(days=n)).strftime("%Y-%m-%d")  # noqa: E731
        self.config(sync=self.sync(), lista=[{"produto": "Leite", "compras": []}, {"produto": "Café", "compras": [d(20), d(10)]},
                                             {"produto": "Arroz", "compras": [d(12), d(2)]}])
        rev0 = S.ler_config()["rev"]
        S.sincronizar_lista()
        lista = self.lista()
        self.assertEqual(lista["Pão francês"], {"produto": "Pão francês", "compras": [], "origem": "ha"}, "item novo do HA entra na lista")
        self.assertEqual(lista["Leite"]["compras"], [], "o que já estava concluído na primeira vez não vira compra")
        self.assertEqual(self.no_ha(), [("Pão francês", "needs_action"), ("Leite", "completed"), ("Café", "needs_action")],
                         "o Café acaba hoje: vai para a lista do HA; o Arroz ainda tem 8 dias; os da primeira vez não são mandados")
        self.assertEqual(S.ler_config()["rev"], rev0 + 1)
        self.assertEqual([(x["tipo"], x["produto"], x["rev"]) for x in S.DIARIO], [("novo", "Pão francês", rev0 + 1)])
        self.assertEqual((S.SYNC["chegaram"], S.SYNC["enviados"], S.SYNC["erro"]), (1, 1, None))
        self.assertTrue(S.SYNC["ultima"])
        # no HA: o pão foi comprado; no painel: um item novo
        self.pao["status"] = "completed"
        cfg = S.ler_config()
        cfg["lista"].append({"produto": "Detergente", "compras": []})
        S.gravar_config(cfg)
        S.sincronizar_lista()
        self.assertEqual(self.lista()["Pão francês"]["compras"], [hoje], "concluído no HA = comprei hoje")
        self.assertEqual(S.DIARIO[-1], {"tipo": "compra", "produto": "Pão francês", "data": hoje, "rev": S.ler_config()["rev"]})
        self.assertIn(("Detergente", "needs_action"), self.no_ha(), "item novo do painel vai para o HA")
        n = len(ha.todos[self.ENT])
        S.sincronizar_lista()
        self.assertEqual(len(ha.todos[self.ENT]), n, "nada repetido na volta seguinte")
        self.assertEqual(S.SYNC["enviados"], 2)
        estado = S.ler_json(S.SYNC_FILE)
        self.assertEqual(estado["entidade"], self.ENT)
        self.assertIn("cafe", estado["acabando"])

    def test_opcoes_desligadas(self):
        S, ha = self.S, self.ha
        self.config(sync=self.sync(enviar_novos=False, enviar_acabando=False), lista=[])
        S.sincronizar_lista()
        cfg = S.ler_config()
        cfg["lista"].append({"produto": "Detergente"})
        S.gravar_config(cfg)
        S.sincronizar_lista()
        self.assertNotIn("Detergente", [i["summary"] for i in ha.todos[self.ENT]])
        self.assertFalse(ha.pedidos_de("/services/todo/add_item"))
        for sync in ({"ativo": False, "entidade": self.ENT}, {"ativo": True, "entidade": "sensor.x"}, None):
            self.config(sync=sync)
            n = len(ha.pedidos)
            S.sincronizar_lista()
            self.assertEqual(len(ha.pedidos), n, f"{sync}: não fala com o HA")

    def test_trocar_de_lista_comeca_de_novo(self):
        S, ha = self.S, self.ha
        self.config(sync=self.sync(), lista=[])
        S.sincronizar_lista()
        ha.item("todo.casa", "Vassoura")
        self.config(sync=self.sync(entidade="todo.casa"), lista=self.S.ler_config()["lista"])
        S.sincronizar_lista()
        self.assertIn("Vassoura", self.lista())
        self.assertEqual(S.ler_json(S.SYNC_FILE)["entidade"], "todo.casa")

    def test_diario(self):
        S = self.S
        cfg = {"lista": [{"produto": "Leite", "compras": ["2026-10-01"]}]}
        S.aplicar_diario(cfg, {"tipo": "novo", "produto": "Pão francês"})
        S.aplicar_diario(cfg, {"tipo": "compra", "produto": "leite", "data": "2026-11-02"})
        S.aplicar_diario(cfg, {"tipo": "compra", "produto": "Leite", "data": "2026-11-02"})
        S.aplicar_diario(cfg, {"tipo": "compra", "produto": "Ovos", "data": "2026-11-02"})
        self.assertEqual(cfg["lista"], [{"produto": "Leite", "compras": ["2026-10-01", "2026-11-02"]},
                                        {"produto": "Pão francês", "compras": [], "origem": "ha"},
                                        {"produto": "Ovos", "compras": ["2026-11-02"], "origem": "ha"}])
        vazio = {}
        S.aplicar_diario(vazio, {"tipo": "novo", "produto": "Sal"})
        self.assertEqual(vazio, {"lista": [{"produto": "Sal", "compras": [], "origem": "ha"}]})

    def test_laco_de_cada_minuto(self):
        S = self.S

        class Parar(Exception):
            pass

        def para(_):
            raise Parar
        S.time = types.SimpleNamespace(time=S.time.time, sleep=para)
        self.config(sync=self.sync(), lista=[], sensores=True)
        with self.assertRaises(Parar):
            S.laco_sincronizacao()
        self.assertIn("Pão francês", self.lista())
        self.assertIsNone(S.SYNC["erro"])
        self.assertIn("sensor.economia_ia_hoje", self.ha.estados, "na virada do dia o sensor é publicado")
        S.itens_ha = lambda e: [None]
        with self.assertRaises(Parar):
            S.laco_sincronizacao()
        self.assertTrue(S.SYNC["erro"].startswith("Erro na sincronização:"), S.SYNC["erro"])
        S.HA_API = "http://127.0.0.1:9/api"
        S.itens_ha = lambda e: S.ha_api("POST", "/services/todo/get_items", {})
        with self.assertRaises(Parar):
            S.laco_sincronizacao()
        self.assertEqual(S.SYNC["erro"], "Não consegui falar com o Home Assistant.")

    def test_home_assistant_recusa(self):
        S, ha = self.S, self.ha
        ha.token = "outra-chave"
        self.config(sync=self.sync())
        with self.assertRaisesRegex(S.ErroBusca, r"O Home Assistant recusou o pedido \(401\)"):
            S.sincronizar_lista()
