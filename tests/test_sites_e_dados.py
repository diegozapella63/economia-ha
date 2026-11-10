"""Preços sem IA nas páginas das lojas (schema.org, meta tags, dados embutidos, texto), busca do site com robots.txt,
Shopee Afiliados (assinatura), versões da configuração, uso da IA, exportar e categoria das lojas."""
import hashlib
import io
import json
import os
import time
import unittest
import zipfile

from apoio import LojasFalsas, limpa, servidor

LD = """<html><head><script type="application/ld+json">{"@context":"https://schema.org","@graph":[
 {"@type":"Product","name":"Detergente Ypê Neutro 500ml","offers":{"@type":"Offer","price":"2.39","availability":"https://schema.org/InStock"}},
 {"@type":"Product","name":"Detergente Limpol 500ml","offers":{"@type":"Offer","price":"2.19","availability":"https://schema.org/InStock"}},
 {"@type":"Product","name":"Detergente Esgotado 500ml","offers":{"@type":"Offer","price":"1.99","availability":"https://schema.org/OutOfStock"}}]}
</script></head><body></body></html>"""

TEXTO = """<div class="card"><h3>Ração Golden Gatos Castrados 1kg</h3><s>R$ 39,90</s><span>R$ 34,90</span></div>
<div class="card"><h3>Areia Higiênica Pipicat 4kg</h3><span>R$ 21,50</span><small>3x de R$ 7,17</small></div>
<p>Frete grátis acima de R$ 99,00</p>"""


class Base(unittest.TestCase):
    def setUp(self):
        self.lojas = LojasFalsas().__enter__()
        self.S, self.pasta, self.log = servidor(self.lojas.env())

    def tearDown(self):
        self.lojas.__exit__()
        limpa(self.pasta)


class PaginasDaLoja(Base):
    def test_schema_org_em_grafo_sem_esgotado(self):
        ofs = self.S.ofertas_da_pagina(LD)
        self.assertEqual([(o["produto"], o["preco"]) for o in ofs], [("Detergente Ypê Neutro 500ml", 2.39), ("Detergente Limpol 500ml", 2.19)])

    def test_cartoes_de_texto_com_preco_riscado_e_sem_parcela(self):
        ofs = {o["produto"]: o for o in self.S.ofertas_da_pagina(TEXTO)}
        self.assertEqual(ofs["Ração Golden Gatos Castrados 1kg"]["preco"], 34.90)
        self.assertEqual(ofs["Ração Golden Gatos Castrados 1kg"]["preco_normal"], 39.90)
        self.assertEqual(ofs["Areia Higiênica Pipicat 4kg"]["preco"], 21.50, "a parcela 3x de R$ 7,17 não é o preço")
        self.assertFalse(any("Frete" in n for n in ofs))

    def test_pagina_de_produto_por_meta_tags(self):
        h = ('<meta property="og:title" content="Fralda Pampers Confort Sec G 46un">'
             '<meta content="89.90" property="product:price:amount"><meta property="product:sale_price:amount" content="79,90">'
             '<meta property="product:availability" content="in stock">')
        r = self.S.preco_da_pagina(h)
        self.assertEqual((r["nome"], r["preco"]), ("Fralda Pampers Confort Sec G 46un", 79.90), "vale o menor entre preço e promoção")

    def test_busca_do_site_respeita_robots_e_tenta_o_nucleo(self):
        S = self.S
        origem = self.lojas.base + "/loja"
        self.lojas.paginas["/loja/busca"] = (200, LD, "text/html")
        info = {"regras": S.robots_regras("User-agent: *\nDisallow: /busca\n"), "busca": "/busca?q={}"}
        self.assertEqual(S.busca_do_site(origem, info, "Detergente"), [], "o robots.txt proíbe a busca")
        self.assertFalse(self.lojas.pedidos_de("/loja/busca"))
        info = {"regras": [], "busca": "/busca?q={}"}
        ofs = S.busca_do_site(origem, info, "Detergente Ypê")
        self.assertEqual([o["produto"] for o in ofs], ["Detergente Ypê Neutro 500ml"])

    def test_sem_busca_que_funcione_espera_uma_semana(self):
        S = self.S
        origem = self.lojas.base + "/vazia"
        info = {"regras": []}
        self.assertEqual(S.busca_do_site(origem, info, "Leite"), [])
        self.assertIn("sem_busca", info)
        n = len(self.lojas.pedidos)
        self.assertEqual(S.busca_do_site(origem, info, "Leite"), [])
        self.assertEqual(len(self.lojas.pedidos), n, "não tenta de novo antes de uma semana")
        S.busca_do_site(origem, info, "Leite", forcar=True)
        self.assertGreater(len(self.lojas.pedidos), n)

    def test_procura_catalogo_pelo_endereco(self):
        S = self.S
        urls = ["https://loja.com/detergente-ype-neutro-500ml/p", "https://loja.com/detergente-limpol-500ml/p",
                "https://loja.com/amaciante-comfort-1l/p", "https://loja.com/detergente-ype-neutro-5l/p"]
        r = S.procura_catalogo(urls, "Detergente Ypê")
        self.assertEqual(r, ["https://loja.com/detergente-ype-neutro-5l/p", "https://loja.com/detergente-ype-neutro-500ml/p"],
                         "do endereço mais curto para o mais longo")
        self.assertEqual(S.procura_catalogo(urls, "Amaciante ou detergente Limpol"),
                         ["https://loja.com/amaciante-comfort-1l/p", "https://loja.com/detergente-limpol-500ml/p"])


class Shopee(Base):
    def test_assinatura_e_erros(self):
        S = self.S
        with self.assertRaises(S.ErroShopee):
            S.shopee_consulta("{x}")
        seg = S.segredos()
        seg["shopee"] = {"app_id": "18300000001", "secret": "segredo"}
        S.grava_segredos(seg)
        S.SHOPEE_API = self.lojas.base + "/shopee"
        self.lojas.paginas["/shopee"] = (200, "{}", "application/json")

        capturado = {}

        def post(h, corpo):
            capturado["auth"], capturado["corpo"] = h.headers.get("Authorization"), corpo
            h._out({"data": {"productOfferV2": {"nodes": [{"productName": "Ração Golden 10kg", "priceMin": "129.9"}]}}})
        self.lojas._post = post
        nodes = S.shopee_produtos("Ração Golden")
        self.assertEqual(nodes[0]["productName"], "Ração Golden 10kg")
        cred = dict(x.split("=", 1) for x in capturado["auth"].replace("SHA256 ", "").split(", "))
        esperado = hashlib.sha256((cred["Credential"] + cred["Timestamp"] + capturado["corpo"] + "segredo").encode()).hexdigest()
        self.assertEqual(cred["Signature"], esperado, "SHA256(app_id + timestamp + corpo + senha)")
        self.assertLess(abs(int(cred["Timestamp"]) - time.time()), 60)


class Versoes(Base):
    def test_guarda_lista_e_restaura(self):
        S = self.S
        S.gravar_config({"cep": "1", "lista": [{"produto": "A"}]})
        n1 = S.guardar_versao("auto", forcar=True)
        self.assertIsNone(S.guardar_versao("auto"), "menos de 10 minutos depois: não guarda de novo")
        S.gravar_config({"cep": "2", "lista": []})
        v = S.listar_versoes()
        self.assertEqual(v[0]["nome"], n1)
        self.assertEqual((v[0]["itens"], v[0]["cep"]), (1, "1"))
        novo = S.restaurar_versao(n1)
        self.assertEqual(novo["cep"], "1")
        self.assertTrue(any(x["nome"].endswith("-restaurar.json") for x in S.listar_versoes()), "guarda a de antes de restaurar")
        with self.assertRaises(S.ErroBusca):
            S.restaurar_versao("../segredos.json")

    def test_so_as_tres_mais_recentes(self):
        S = self.S
        S.gravar_config({"cep": "1"})
        os.makedirs(S.VERSOES, exist_ok=True)
        for i in range(5):
            with open(os.path.join(S.VERSOES, f"config-2026010{i}-120000-auto.json"), "w") as f:
                f.write("{}")
        S.guardar_versao("auto", forcar=True)
        self.assertEqual(len(S.listar_versoes()), S.MAX_VERSOES)


    def test_sem_pasta_e_nome_estranho(self):
        S = self.S
        self.assertEqual(S.listar_versoes(), [], "sem nenhuma versão guardada")
        S.gravar_config({"cep": "1", "lista": ["Café", {"produto": ""}]})
        n = S.guardar_versao("qualquer", forcar=True)
        self.assertTrue(n.endswith("-auto.json"), "motivo desconhecido vira automática")
        open(os.path.join(S.VERSOES, "anotacoes.txt"), "w").close()
        open(os.path.join(S.VERSOES, "config-x.json"), "w").close()
        self.assertEqual([(v["nome"], v["itens"], v["motivo"]) for v in S.listar_versoes()], [(n, 1, "automática")], "só os arquivos de versão")
        with self.assertRaisesRegex(S.ErroBusca, "Versão não encontrada."):
            S.restaurar_versao("config-20200101-000000-auto.json")


class Dados19(Base):
    """1.9.0: Backup na pasta share, Começar do zero e a planilha do Exportar no Importar."""

    def test_backup_lista_restaura_e_guarda_os_dez_mais_recentes(self):
        S = self.S
        S.gravar_config({"cep": "1", "lista": [{"produto": "Café"}], "usar_ia": False})
        S.gravar_json(S.OFERTAS, {"gerado_em": "x", "categorias": []})
        open(os.path.join(S.DATA, "segredos.json"), "w").write('{"google": {"key": "segredo"}}')
        self.assertTrue(S.share_ok())
        nome = S.criar_backup()
        b = S.listar_backups()
        self.assertEqual(b[0]["nome"], nome)
        self.assertGreater(b[0]["tamanho"], 0)
        with zipfile.ZipFile(os.path.join(S.SHARE, nome)) as z:
            self.assertEqual(sorted(z.namelist()), ["config.json", "ofertas.json"], "sem as chaves das integrações")
        S.gravar_config({"cep": "2", "lista": []})
        os.remove(S.OFERTAS)
        novo = S.restaurar_backup(nome)
        self.assertEqual((novo["cep"], novo["lista"][0]["produto"]), ("1", "Café"))
        self.assertTrue(os.path.exists(S.OFERTAS), "o resultado da busca volta junto")
        self.assertTrue(any(v["nome"].endswith("-restaurar.json") for v in S.listar_versoes()), "antes, uma versão do que existia")
        for i in range(12):
            open(os.path.join(S.SHARE, f"economia-202601{i % 9 + 1:02d}-1200{i:02d}.zip"), "w").close()
        open(os.path.join(S.SHARE, "economia-20261399-000000.zip"), "w").close()  # uma data que não existe: fica de fora
        S.criar_backup()
        self.assertEqual(len(S.listar_backups()), S.MAX_BACKUPS)
        with self.assertRaisesRegex(S.ErroBusca, "Backup não encontrado."):
            S.restaurar_backup("../config.json")
        open(os.path.join(S.SHARE, "economia-20200101-000000.zip"), "w").write("não é zip")
        with self.assertRaisesRegex(S.ErroBusca, "não parece um backup"):
            S.restaurar_backup("economia-20200101-000000.zip")

    def test_sem_pasta_share(self):
        S = self.S
        S.SHARE = os.path.join(S.DATA, "arquivo")
        open(S.SHARE, "w").close()  # um arquivo no lugar da pasta: não dá para gravar
        self.assertFalse(S.share_ok())
        self.assertEqual(S.listar_backups(), [])
        with self.assertRaisesRegex(S.ErroBusca, "share não está disponível"):
            S.criar_backup()

    def test_zerar_deixa_so_os_ajustes(self):
        S = self.S
        S.gravar_config({"cep": "1", "lista": [{"produto": "Café"}], "historico": [{"produto": "Pão"}], "perfil": {"adultos": 3},
                         "usar_ia": False, "sensores": True, "cor": "azul", "cor_dia": False, "opcoes": {"folhetos": False}})
        S.gravar_json(S.OFERTAS, {"categorias": []})
        novo = S.zerar()
        self.assertEqual({k for k in novo if k not in ("rev", "atualizado_em")}, {"usar_ia", "sensores", "cor", "cor_dia", "opcoes"})
        self.assertFalse(os.path.exists(S.OFERTAS))
        v = S.listar_versoes()
        self.assertEqual((v[0]["motivo"], v[0]["itens"]), ("antes de começar do zero", 1), "uma versão antes, que traz tudo de volta")

    def test_cor_da_casa_so_mexe_na_cor(self):
        S = self.S
        S.gravar_config({"cep": "1", "lista": [{"produto": "Café"}]})
        rev = S.gravar_cor("magenta", False)
        c = S.ler_config()
        self.assertEqual((c["cor"], c["cor_dia"], c["rev"], c["cep"]), ("rosa", False, rev, "1"), "Magenta de antes é Rosa; o resto fica")
        S.gravar_cor("nada", True)
        self.assertEqual((S.ler_config()["cor"], S.ler_config()["cor_dia"]), ("rosa", True), "uma cor fora da paleta não muda a cor")
        S.gravar_cor(None, None)
        self.assertNotIn("cor", S.ler_config())

    def test_planilha_do_exportar_volta_no_importar(self):
        S = self.S
        S.gravar_config({"lista": [{"produto": "Leite integral", "compras": ["2026-10-01", "2026-10-11"], "qtd": 6}, {"produto": "Café & Cia", "qtd": "x"},
                                   {"produto": "ab"}, {"produto": "Arroz", "qtd": 500}]})
        corpo, _ = S.exportar("xlsx")
        d = S.ler_planilha(corpo)
        self.assertEqual(d["lista"], [{"produto": "Leite integral", "compras": ["2026-10-01", "2026-10-11"], "qtd": 6}, {"produto": "Café & Cia", "compras": []},
                                      {"produto": "Arroz", "compras": []}], "1.14.0: a quantidade vai e volta (fora de 1 a 99, vale 1)")
        self.assertEqual([i["quantidade"] for i in json.loads(S.exportar("json")[0])["lista"]], [6, 1, 1, 1])
        with self.assertRaisesRegex(S.ErroBusca, "não parece a planilha"):
            S.ler_planilha(b"isto nao e um zip")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:  # outra planilha (texto compartilhado), sem a coluna Produto
            z.writestr("xl/worksheets/sheet1.xml", '<worksheet><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c></row></sheetData></worksheet>')
            z.writestr("xl/sharedStrings.xml", "<sst><si><t>Nome</t></si></sst>")
        with self.assertRaisesRegex(S.ErroBusca, "coluna Produto"):
            S.ler_planilha(buf.getvalue())


class UsoDaIA(Base):
    def test_conta_chamadas_tokens_e_erros(self):
        S = self.S
        S.registra_uso("buscar ofertas", "ai_task.claude", 4000, 400, 0, 12.3, "ok")
        S.registra_uso("ler encarte", None, 400, 0, 2, 3, "erro")
        S.registra_uso("buscar ofertas", "ai_task.claude", 0, 0, 0, 1, "cota")
        r = S.uso_resumo()
        h = r["hoje"]
        self.assertEqual((h["chamadas"], h["erros"], h["cota"], h["imagens"]), (3, 1, 1, 2))
        self.assertEqual(h["tokens"], 1100 + 100)
        self.assertEqual(h["ias"]["padrão do Home Assistant"], 1)
        self.assertEqual(len(r["dias"]), 7)
        self.assertEqual(r["ultimas"][0]["resultado"], "cota")


class Exportar(Base):
    def prepara(self):
        S = self.S
        S.gravar_config({"cep": "89216120", "raio_km": 5, "categorias": ["mercados"], "lista": [
            {"produto": "Leite integral", "compras": ["2026-10-01", "2026-10-11"]}, {"produto": "Café"}]})
        S.gravar_json(S.OFERTAS, {"gerado_em": "2026-11-02T10:00:00", "categorias": [
            {"id": "mercados", "nome": "Mercados", "singular": "Mercado", "redes": [{"id": "merc-giassi", "nome": "Giassi"}, {"id": "merc-fort", "nome": "Fort"}],
             "lojas": [{"rede": "merc-giassi", "distancia_km": 1.0}, {"rede": "merc-fort", "distancia_km": 2.0}]}],
            "lista": [{"produto": "Leite integral", "precos": {"merc-giassi": 4.89, "merc-fort": 4.49}}]})

    def test_json(self):
        self.prepara()
        corpo, tipo = self.S.exportar("json")
        d = json.loads(corpo)
        self.assertEqual(d["app"], "EconomIA")
        leite = next(i for i in d["lista"] if i["produto"] == "Leite integral")
        self.assertEqual(leite["mais_barato"]["loja"], "Fort")
        self.assertEqual(leite["economia"], 0.4)

    def test_planilha(self):
        self.prepara()
        corpo, tipo = self.S.exportar("xlsx")
        self.assertIn("spreadsheetml", tipo)
        z = zipfile.ZipFile(io.BytesIO(corpo))
        self.assertIn("xl/worksheets/sheet1.xml", z.namelist())
        folha = z.read("xl/worksheets/sheet1.xml").decode()
        self.assertIn("Leite integral", folha)
        self.assertIn("Giassi R$ 4,89", folha)


    def test_lojas_que_nao_contam(self):
        S = self.S
        S.gravar_config({"raio_km": "perto", "categorias": ["mercados", "online"], "clubes": ["merc-fort"],
                         "lojas": {"ignorar": ["merc-ignorada"], "manter": ["merc-mantida"]},
                         "lista": [{"produto": "Leite", "compras": ["2026-10-01", "x", "2026-10-03", "2026-10-08"]}, {"produto": ""}, "Café"]})
        S.gravar_json(S.OFERTAS, {"categorias": ["x", {"id": "mercados", "singular": "Mercado", "redes": [
            {"id": "merc-perto", "nome": "Perto"}, {"id": "merc-longe", "nome": "Longe"}, {"id": "merc-ignorada", "nome": "Ignorada"},
            {"id": "merc-mantida", "nome": "Mantida"}, {"id": "merc-sem-loja", "nome": "Sem loja"}, {"id": "merc-fort", "nome": "Fort"}, "y"],
            "lojas": [{"rede": "merc-perto", "distancia_km": 1.0}, {"rede": "merc-longe", "distancia_km": 2.5}, {"rede": "merc-ignorada", "distancia_km": 1.0},
                      {"rede": "merc-mantida", "distancia_km": 9.0}, {"rede": "merc-fort", "distancia_km": 1.5}, "z"]},
            {"id": "farmacias", "redes": [{"id": "farm-x", "nome": "X"}], "lojas": [{"rede": "farm-x", "distancia_km": 1}]}],
            "lista": [{"produto": "Leite", "precos": {"merc-perto": 5.0, "merc-longe": 4.0, "merc-ignorada": 3.0, "merc-mantida": 4.5,
                                                      "merc-sem-loja": 2.0, "farm-x": 1.0, "merc-desconhecida": 1.5,
                                                      "merc-fort": {"preco": 6.0, "clube": 4.2}}}]})
        itens = json.loads(S.exportar("json")[0])["lista"]
        self.assertEqual([i["produto"] for i in itens], ["Leite", "Café"], "sem nome: fica de fora")
        leite = itens[0]
        self.assertEqual([(p["loja"], p["preco"]) for p in leite["precos"]], [("Fort", 4.2), ("Mantida", 4.5), ("Perto", 5.0)],
                         "raio inválido: 2 km; sem a longe, a ignorada, a sem loja, a de categoria desmarcada e a desconhecida; clube do sócio")
        self.assertEqual((leite["compras"], leite["compra_a_cada_dias"], leite["economia"]), (["2026-10-01", "2026-10-03", "2026-10-08"], 4, 0.8))
        self.assertEqual((itens[1]["precos"], itens[1]["mais_barato"], itens[1]["compra_a_cada_dias"]), ([], None, None))


class CategoriaDaLoja(Base):
    def test_loja_do_bairro_e_online(self):
        S = self.S
        S.gravar_json(S.OFERTAS, {"categorias": [
            {"id": "mercados", "redes": [{"id": "merc-fort", "nome": "Fort Atacadista"}, {"id": "merc-longe", "nome": "Mercado Longe"},
                                         {"id": "merc-sem", "nome": "Sem Endereço"}],
             "lojas": [{"rede": "merc-fort", "distancia_km": 4.2}, {"rede": "merc-longe", "distancia_km": 12}, {"rede": "merc-sem", "distancia_km": None}]},
            {"id": "online", "redes": [{"id": "onli-amazon", "nome": "Amazon"}], "lojas": [{"rede": "onli-amazon", "distancia_km": 1}]}]})
        perto = S.lojas_perto_cat({"raio_km": 5})
        self.assertEqual(perto, {"fort atacadista": "mercados"})
        self.assertEqual(S.categoria_da_loja("Fort Atacadista", perto), "mercados")
        self.assertEqual(S.categoria_da_loja("Fort", perto), "mercados", "pelo nome da rede")
        self.assertEqual(S.categoria_da_loja("Sem Endereço", perto), "online", "sem localização = online")
        self.assertEqual(S.categoria_da_loja("Mercado Longe", perto), "online", "fora do raio entrega")


if __name__ == "__main__":
    unittest.main()
