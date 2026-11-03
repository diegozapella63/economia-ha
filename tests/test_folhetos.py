"""Folhetos dos sites de encartes (Kimbino, Seus Folhetos, Portafolhetos, Catálogos Ofertas) com páginas salvas feitas
aqui e o OFERTAS_FOLHETOS_TESTE apontando para as lojas falsas: links e validade na página da loja, páginas do folheto,
tamanho das imagens, robots.txt e Content-Signal (ai-input=no), verificação de robô (não contorna), redirecionamento,
a IA escolhendo pelas capas, a leitura guardada até vencer, os preços casados sem IA e as lojas procuradas."""
import struct
from datetime import datetime, timedelta

from apoio import Cenario, categoria

JPG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\0" * 9 + b"\xff\xc0\x00\x11\x08\x09\x60\x03\x20" + b"\0" * 40  # 800 × 2400


def webp_vp8x(w, h):
    return b"RIFF" + struct.pack("<I", 30) + b"WEBPVP8X" + struct.pack("<I", 10) + b"\0" * 4 + (w - 1).to_bytes(3, "little") + (h - 1).to_bytes(3, "little")


def webp_vp8(w, h):
    return b"RIFF" + struct.pack("<I", 30) + b"WEBPVP8 " + struct.pack("<I", 10) + b"\0\0\0\x9d\x01\x2a" + struct.pack("<HH", w, h)


def webp_vp8l(w, h):
    return b"RIFF" + struct.pack("<I", 30) + b"WEBPVP8L" + struct.pack("<I", 10) + b"\x2f" + struct.pack("<I", (w - 1) | ((h - 1) << 14))


def png(w, h):
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", w, h) + b"\x08\x02\0\0\0"


class Base(Cenario):
    def setUp(self):
        super().setUp()
        h = datetime.strptime(self.S.hoje_br(), "%Y-%m-%d")
        self.br = lambda n: (h + timedelta(days=n)).strftime("%d/%m/%Y")  # noqa: E731
        self.iso = lambda n: (h + timedelta(days=n)).strftime("%Y-%m-%d")  # noqa: E731
        self.S.gravar_json(self.S.FOLHETOS, {"_cep": {"cep": "89216120", "cidade": "Joinville", "uf": "SC"}})

    def kimbino(self, loja, folhetos):
        """Página da loja no Kimbino com [(id, desde, até)] e a página de cada folheto com 2 páginas."""
        b, lj = self.lojas.base, self.lojas
        partes = []
        for fid, de, ate in folhetos:
            partes.append(f'<div class="flyer"><a href="/kimbino/{loja}/ofertas-{fid}/"><img src="/x.jpg"></a><p>Válido {self.br(de)} - {self.br(ate)}</p></div>')
            lj.paginas[f"/kimbino/{loja}/ofertas-{fid}/"] = (200, f"""<html><body>
                <img src="{b}/kimbicdn.com/300x0/data/{fid}/9/1.jpg"><img src="{b}/kimbicdn.com/0x0/data/{fid}/9/1.jpg">
                <img src="{b}/kimbicdn.com/0x0/data/{fid}/9/2.jpg"><img src="{b}/kimbicdn.com/0x0/data/555/1/1.jpg"></body></html>""", "text/html")
            for n in (1, 2):
                lj.paginas[f"/kimbicdn.com/0x0/data/{fid}/9/{n}.jpg"] = (200, JPG, "image/jpeg")
        lj.paginas[f"/kimbino/{loja}/"] = (200, "<html><body><h1>Folhetos</h1>" + "".join(partes) + "</body></html>", "text/html")


class PaginasDosSites(Base):
    def test_kimbino(self):
        S, b = self.S, self.lojas.base
        a = S.AGREGADORES[0]
        self.assertEqual(S.agreg_base(a), b + "/kimbino")
        self.kimbino("kuntze", [(1234567, -3, 4), (7654321, -10, -1)])
        url = b + "/kimbino/kuntze/"
        fs = S.folhetos_da_pagina(a, url, self.lojas.paginas["/kimbino/kuntze/"][1])
        self.assertEqual(fs, [{"url": b + "/kimbino/kuntze/ofertas-1234567/", "id": "kimbino:1234567", "de": self.iso(-3), "ate": self.iso(4)},
                              {"url": b + "/kimbino/kuntze/ofertas-7654321/", "id": "kimbino:7654321", "de": self.iso(-10), "ate": self.iso(-1)}])
        pg = S.paginas_folheto(a, dict(fs[0]))
        self.assertEqual(pg, [b + "/kimbicdn.com/0x0/data/1234567/9/1.jpg", b + "/kimbicdn.com/0x0/data/1234567/9/2.jpg"],
                         "a pasta que mais aparece, na versão /0x0/; a capa sugerida de outro folheto fica de fora")

    def test_seus_folhetos_e_data_no_endereco(self):
        S, b = self.S, self.lojas.base
        a = S.AGREGADORES[1]
        html = ('<a href="/seusfolhetos/kuntze-ofertas/folheto-especial">Especial</a>'
                f'<a href="/seusfolhetos/kuntze-ofertas/folheto-555-0">Folheto</a> <span>{self.br(-1)[:5]} a {self.br(5)}</span>')
        fs = S.folhetos_da_pagina(a, b + "/seusfolhetos/kuntze-ofertas", html)
        self.assertEqual([(f["id"], f["de"], f["ate"]) for f in fs], [("seusfolhetos:seusfolhetos-kuntze-ofertas-folheto-especial", None, None),
                                                                     ("seusfolhetos:555", self.iso(-1), self.iso(5))],
                         "\"dd/mm a dd/mm/aaaa\": o ano vem da data final")
        self.lojas.paginas["/seusfolhetos/kuntze-ofertas/folheto-555-0"] = (200, (
            '<meta property="og:description" content="Ofertas válidas de 01/11/2026 até 09/11/2026">'
            '<img src="/public/gimg/7/8/1-800-2400.jpg"><img src="/public/gimg/7/8/2-800-2400.webp"><img src="/public/gimg/7/8/1-300-400.jpg">'
            '<img src="/public/gimg/9/1-1200-630.jpg">'), "text/html")
        f = {"url": b + "/seusfolhetos/kuntze-ofertas/folheto-555-0", "id": "seusfolhetos:555", "de": None, "ate": None}
        self.assertEqual(S.paginas_folheto(a, f), [b + "/public/gimg/7/8/1-800-2400.jpg", b + "/public/gimg/7/8/2-800-2400.webp"],
                         "as páginas compridas; capa e imagem de compartilhar ficam de fora")
        self.assertEqual((f["de"], f["ate"]), ("2026-11-01", "2026-11-09"), "a validade da descrição da página")
        self.assertIs(S.paginas_folheto(a, f), f["paginas"], "lido uma vez só")
        kim = {"url": b + "/kimbino/loja/x-30-10-2026-1234567/", "id": "k:1"}
        fs = S.folhetos_da_pagina(S.AGREGADORES[0], b + "/kimbino/loja/", f'<a href="{kim["url"]}">x</a>')
        self.assertEqual(fs[0]["de"], "2026-10-30", "a data do começo pelo endereço do folheto")

    def test_catalogos_ofertas_e_tamanho_das_paginas(self):
        S, b, lj = self.S, self.lojas.base, self.lojas
        a = S.AGREGADORES[3]
        meses = "jan fev mar abr mai jun jul ago set out nov dez".split()
        h0, h1 = datetime.strptime(self.iso(-2), "%Y-%m-%d"), datetime.strptime(self.iso(6), "%Y-%m-%d")
        periodo = f"{h0.day} {meses[h0.month - 1]}. até {h1.day} {meses[h1.month - 1]}."
        html = (f'<a href="/catalogosofertas/vista/ofertas/kuntze-semana-123456"><p>{periodo}</p></a>'
                '<h2>Encartes parecidos</h2><a href="/catalogosofertas/vista/ofertas/outra-loja-999999">x</a>')
        fs = S.folhetos_da_pagina(a, b + "/catalogosofertas/lojas/kuntze/ofertas-catalogos", html)
        self.assertEqual([(f["id"], f["de"], f["ate"]) for f in fs], [("catalogosofertas:123456", self.iso(-2), self.iso(6))],
                         "só os folhetos da loja, com a validade \"30 out. até 10 nov.\"")
        self.assertEqual(S.periodo_mes("30 dez. até 5 jan."), (f"{S.hoje_br()[:4]}-12-30", f"{int(S.hoje_br()[:4]) + 1}-01-05"), "vira o ano")
        self.assertEqual(S.periodo_mes("sem data"), (None, None))
        mini = "/assets/uploads/flyers/123456/260x270WebP/kuntze-semana-{}-1-abc123.webp"
        lj.paginas["/catalogosofertas/vista/ofertas/kuntze-semana-123456"] = (200, (
            f'<meta name="description" content="Válido de 30-10-2026 até 10-11-2026"><img src="{mini.format(1)}"><img src="{mini.format(2)}">'
            '<img src="/assets/uploads/flyers/123456/260x270WebP/kuntze-semana-1-1-abc123.jpg">'), "text/html")
        lj.paginas["/assets/uploads/flyers/123456/780x810WebP/kuntze-semana-1-1-abc123.webp"] = (200, webp_vp8(780, 810), "image/webp")
        lj.paginas["/assets/uploads/flyers/123456/1300x1350WebP/kuntze-semana-1-1-abc123.webp"] = (200, webp_vp8x(1300, 1350), "image/webp")
        f = dict(fs[0])
        f["ate"] = None
        pg = S.paginas_folheto(a, f)
        self.assertEqual(pg, [b + "/assets/uploads/flyers/123456/1300x1350WebP/kuntze-semana-1-1-abc123.webp",
                              b + "/assets/uploads/flyers/123456/1300x1350WebP/kuntze-semana-2-1-abc123.webp"],
                         "a maior pasta que o servidor de imagens tiver (a página só mostra miniaturas)")
        self.assertEqual((f["de"], f["ate"]), ("2026-10-30", "2026-11-10"))
        self.assertEqual(S.ler_json(S.CO_TAMANHO_ARQ)["pasta"], "1300x1350WebP")
        n = len(lj.pedidos)
        self.assertEqual(S.paginas_grandes([b + mini.format(3)]), [b + "/assets/uploads/flyers/123456/1300x1350WebP/kuntze-semana-3-1-abc123.webp"])
        self.assertEqual(len(lj.pedidos), n, "o tamanho fica guardado")
        S.gravar_json(S.CO_TAMANHO_ARQ, {})
        lj.paginas = {k: v for k, v in lj.paginas.items() if "WebP/" not in k or "260x270" in k}
        f2 = dict(fs[0], paginas=None)
        self.assertEqual(S.paginas_folheto(a, f2), [])
        self.assertTrue(f2["pequeno"], "só miniaturas: pequeno demais para a IA")
        self.assertTrue(S.ler_json(S.CO_TAMANHO_ARQ)["nenhum"])

    def test_tamanho_das_imagens(self):
        S = self.S
        for dado, wh in ((webp_vp8x(1040, 1080), (1040, 1080)), (webp_vp8(780, 810), (780, 810)), (webp_vp8l(520, 540), (520, 540)),
                         (png(1200, 3000), (1200, 3000)), (JPG, (800, 2400))):
            self.assertEqual(S.tamanho_imagem(dado), wh)
        self.assertIsNone(S.tamanho_imagem(b"GIF89a"))
        self.assertIsNone(S.tamanho_imagem(b"\xff\xd8\xff"))


class RobotsERobos(Base):
    def test_robots_e_sinal_de_conteudo(self):
        S, b, lj = self.S, self.lojas.base, self.lojas
        lj.paginas["/kimbino/robots.txt"] = (200, "User-agent: *\nDisallow: /busca\n", "text/plain")
        self.assertTrue(S.agreg_permite(b + "/kimbino/kuntze/"))
        self.assertFalse(S.agreg_permite(b + "/kimbino/busca?q=x"))
        lj.paginas["/seusfolhetos/robots.txt"] = (200, "User-agent: *\nContent-Signal: search=yes, ai-input=no\nAllow: /\n", "text/plain")
        self.assertFalse(S.agreg_permite(b + "/seusfolhetos/kuntze-ofertas"))
        self.assertEqual(S._robots_agreg["_ultimo"], "o site não deixa mandar o conteúdo para IA (ai-input=no)")
        lj.paginas["/portafolhetos/robots.txt"] = (200, "User-agent: *\nContent-Signal: ai-train=no, search=yes\nAllow: /\n", "text/plain")
        self.assertTrue(S.agreg_permite(b + "/portafolhetos/kuntze/"), "ai-train=no não muda nada: o app não treina IA")
        lj.paginas["/catalogosofertas/robots.txt"] = (403, "Forbidden", "text/plain")
        self.assertFalse(S.agreg_permite(b + "/catalogosofertas/lojas/x/ofertas-catalogos"))
        self.assertEqual(S._robots_agreg["_ultimo"], "o site recusou o acesso de programas (erro 403)")
        n = len(lj.pedidos_de("/kimbino/robots.txt"))
        S.agreg_permite(b + "/kimbino/outra/")
        self.assertEqual(len(lj.pedidos_de("/kimbino/robots.txt")), n, "o robots.txt é lido uma vez por dia")

    def test_verificacao_de_robo(self):
        S = self.S
        self.assertTrue(S.pede_robo("<html>ok</html>", {"cf-mitigated": "challenge"}))
        self.assertTrue(S.pede_robo("<html>ok</html>", {"x-amzn-waf-action": "captcha"}))
        self.assertTrue(S.pede_robo("<title>Just a moment...</title>" + "x" * 50000))
        self.assertTrue(S.pede_robo("<script>window._cf_chl_opt={}</script>"))
        self.assertTrue(S.pede_robo('<script src="/cdn-cgi/challenge-platform/h/b"></script>'))
        self.assertFalse(S.pede_robo('<script src="/cdn-cgi/challenge-platform/h/b"></script>' + "<p>produto</p>" * 3000),
                         "página normal atrás do Cloudflare também carrega o challenge-platform")
        self.assertFalse(S.pede_robo("<html><h1>Folhetos</h1></html>"))
        self.assertEqual(S.redireciona_para('<meta http-equiv="refresh" content="0; url=/kimbino/kuntze-sc/">', "https://k.com/kimbino/kuntze/"),
                         "https://k.com/kimbino/kuntze-sc/")
        self.assertEqual(S.redireciona_para("<script>window.location.href = '/a/b';</script>", "https://k.com/x"), "https://k.com/a/b")
        self.assertEqual(S.redireciona_para("<script>location.replace(\"https://k.com/c\")</script>", "https://k.com/x"), "https://k.com/c")
        self.assertIsNone(S.redireciona_para("<p>nada</p>", "https://k.com/x"))
        self.assertEqual(S.resumo_vazia("", 202, {"Server": "CloudFront"}), "código 202, 0 bytes, servidor CloudFront")

    def test_achar_folhetos(self):
        S, b, lj = self.S, self.lojas.base, self.lojas
        self.kimbino("kuntze", [(1234567, -3, 4), (7654321, -10, -1)])
        cache = S.ler_json(S.FOLHETOS)
        self.assertEqual(S.bases_loja("Supermercado Kuntze Joinville", cache), ["kuntze"], "sem palavras genéricas nem a cidade")
        self.assertEqual(S.bases_loja("Komprão Koch Atacadista", cache), ["komprao", "komprao-koch"])
        a, url, fs = S.achar_folhetos({"nome": "Supermercado Kuntze"}, cache)
        self.assertEqual((a["id"], url, [f["id"] for f in fs]), ("kimbino", b + "/kimbino/kuntze/", ["kimbino:1234567"]), "só o válido hoje")
        self.assertEqual(cache["_lojas"]["kimbino:supermercado-kuntze"]["url"], b + "/kimbino/kuntze/")
        # verificação de robô no Kimbino, ai-input=no no Seus Folhetos, redirecionamento para o início no Portafolhetos
        lj.paginas["/kimbino/bloqueado/"] = (200, "<html><title>Just a moment...</title></html>", "text/html")
        lj.paginas["/seusfolhetos/robots.txt"] = (200, "User-agent: *\nContent-Signal: ai-input=no\n", "text/plain")
        lj.paginas["/portafolhetos/bloqueado/"] = (302, "", "text/html", {"Location": "/portafolhetos/"})
        lj.paginas["/portafolhetos/"] = (200, "<html>" + "início " * 500 + "</html>", "text/html")
        loja = {"nome": "Mercado Bloqueado"}
        self.assertEqual(S.achar_folhetos(loja, cache), (None, None, []))
        self.assertEqual(loja["_diag"], {"Kimbino": "o site pediu verificação de robô",
                                         "Seus Folhetos": "o site não deixa mandar o conteúdo para IA (ai-input=no)"})
        self.assertFalse([p for p in lj.pedidos_de("/seusfolhetos/") if "robots" not in p[1]], "nenhuma página do site que proibiu")
        self.assertEqual(len(lj.pedidos_de("/kimbino/bloqueado")), 1, "não tenta passar pela verificação")
        n = len(lj.pedidos)
        S.achar_folhetos({"nome": "Mercado Bloqueado"}, cache)
        self.assertEqual(len(lj.pedidos), n, "\"não tem\" fica guardado por uma semana")

    def test_pagina_quase_vazia_que_redireciona(self):
        S, b, lj = self.S, self.lojas.base, self.lojas
        self.kimbino("kuntze-sc", [(1111111, 0, 3)])
        lj.paginas["/kimbino/kuntze/"] = (200, '<meta http-equiv="refresh" content="0;url=/kimbino/kuntze-sc/">', "text/html")
        a, url, fs = S.achar_folhetos({"nome": "Kuntze"}, {})
        self.assertEqual((url, [f["id"] for f in fs]), (b + "/kimbino/kuntze-sc/", ["kimbino:1111111"]))


class LerFolhetos(Base):
    def resposta(self, corpo):
        return {"validade": self.iso(4), "ofertas": [{"produto": "Café Pilão Tradicional 500 g", "preco": 15.98, "tamanho": {"quantidade": 500, "unidade": "g"}},
                                                     {"produto": "Leite Integral Tirol 1 L", "preco": 4.79}],
                "lista": [{"item": 1, "produto": "Café Pilão 500 g", "base": {"quantidade": 500, "unidade": "g"}, "precos": [{"preco": 15.98}]}]}

    def test_le_uma_vez_e_guarda_ate_vencer(self):
        S, ha = self.S, self.ha
        self.kimbino("kuntze", [(1234567, -3, 4)])
        cfg = self.config(lista=[{"produto": "Café Pilão 500 g"}, {"produto": "Leite integral"}])
        ha.responde_ia("folheto Supermercado Kuntze", self.resposta)
        loja = {"nome": "Supermercado Kuntze", "categoria": "mercados"}
        res, st = S.busca_folhetos(cfg, [loja])
        self.assertEqual(len(ha.chamadas_ia), 1)
        anexos = ha.chamadas_ia[0]["attachments"]
        self.assertEqual(len(anexos), 2)
        self.assertTrue(all(x["media_content_id"].startswith("media-source://media_source/local/economia/folheto-") for x in anexos))
        self.assertIn('do site da loja "Supermercado Kuntze"', ha.chamadas_ia[0]["instructions"])
        cat, parcial = res[0]
        self.assertEqual(parcial["Café Pilão 500 g"]["precos"], {"merc-supermercado-kuntze": 15.98})
        self.assertEqual(parcial["Leite integral"]["precos"], {"merc-supermercado-kuntze": {"preco": 4.79, "obs": "Leite Integral Tirol 1 L"}},
                         "casado pelo nome com a oferta, sem IA")
        lj = cat["lojas"][0]
        self.assertEqual((lj["fontes"], lj["folheto"], lj["folheto_ate"]), (["Encarte"], self.lojas.base + "/kimbino/kuntze/ofertas-1234567/", self.iso(4)))
        s = st["supermercado kuntze"]
        self.assertEqual((s["fonte"], s["folhetos"], s["lidos"], s["guardados"], s["ofertas"], s["ate"], s["erro"]), ("Kimbino", 1, 1, 0, 2, self.iso(4), None))
        g = S.ler_json(S.FOLHETOS)["itens"]["kimbino:1234567"]
        self.assertEqual((g["loja"], g["paginas"], g["ate"]), ("Supermercado Kuntze", 2, self.iso(4)))
        # na busca seguinte: o guardado, sem IA; folhetos_painel mostra como foi
        res, st = S.busca_folhetos(cfg, [loja])
        self.assertEqual(len(ha.chamadas_ia), 1)
        self.assertEqual(st["supermercado kuntze"]["guardados"], 1)
        res, st = S.busca_folhetos(cfg, [loja], so_guardados=True)
        self.assertEqual((len(res), st), (1, {}))
        self.config(lista=cfg["lista"], lojas={"adicionar": [{"nome": "Supermercado Kuntze", "categoria": "mercados"}]})
        painel = S.folhetos_painel(S.ler_config())
        self.assertEqual(painel[0]["nome"], "Supermercado Kuntze")
        self.assertEqual(painel[0]["status"]["fonte"], "Kimbino")
        # vencido: sai do guardado
        c = S.ler_json(S.FOLHETOS)
        c["itens"]["kimbino:1234567"]["ate"] = self.iso(-1)
        S.gravar_json(S.FOLHETOS, c)
        S.busca_folhetos(cfg, [loja], so_guardados=True)
        self.assertNotIn("kimbino:1234567", S.ler_json(S.FOLHETOS)["itens"])

    def test_sem_ia_e_desligado(self):
        S, ha = self.S, self.ha
        self.kimbino("kuntze", [(1234567, -3, 4)])
        cfg = self.config(usar_ia=False, lista=[{"produto": "Café"}])
        res, st = S.busca_folhetos(cfg, [{"nome": "Supermercado Kuntze", "categoria": "mercados"}])
        self.assertEqual((res, ha.chamadas_ia), ([], []), "sem IA: acha o folheto, mas não lê")
        self.assertEqual(st["supermercado kuntze"]["fonte"], "Kimbino")
        cfg = self.config(opcoes={"folhetos": False})
        self.assertEqual(S.busca_folhetos(cfg, [{"nome": "X", "categoria": "mercados"}]), ([], {}))
        res, st = S.busca_folhetos(self.config(), [{"nome": "Loja Sem Folheto", "categoria": "mercados"}])
        self.assertEqual((st["loja sem folheto"]["erro"], st["loja sem folheto"]["sem_folheto"]), (None, True), "não estar nos sites é o normal")

    def test_mais_de_dois_folhetos_a_ia_olha_as_capas(self):
        S, ha = self.S, self.ha
        self.kimbino("rede", [(3000001, -1, 5), (3000002, -2, 5), (3000003, -3, 5)])
        cfg = self.config(lista=[{"produto": "Café"}])
        ha.responde_ia("capas de Rede Grande", {"encartes": [{"n": 1, "vale": "nao", "onde": "Curitiba"}, {"n": 2, "vale": "sim"}, {"n": 3, "vale": "talvez"}]})
        ha.responde_ia("folheto Rede Grande", {"ofertas": [{"produto": "Café Pilão 500 g", "preco": 15.98}]})
        res, st = S.busca_folhetos(cfg, [{"nome": "Rede Grande", "categoria": "mercados"}])
        capas = ha.chamadas_ia[0]
        self.assertEqual(capas["task_name"], "EconomIA: capas de Rede Grande")
        self.assertEqual(len(capas["attachments"]), 3)
        self.assertIn("O morador mora em Joinville (SC)", capas["instructions"])
        self.assertEqual([c["task_name"] for c in ha.chamadas_ia[1:]], ["EconomIA: folheto Rede Grande"], "só o que vale para a cidade")
        self.assertEqual(st["rede grande"]["folhetos"], 3)
        vale = S.ler_json(S.FOLHETOS)["_vale"]
        self.assertEqual({k: v["v"] for k, v in vale.items()}, {"kimbino:3000001": "nao", "kimbino:3000002": "sim", "kimbino:3000003": "nao_sei"})
        self.assertIn("kimbino:3000002", S.ler_json(S.FOLHETOS)["itens"])

    def test_precos_por_oferta_e_resultado(self):
        S = self.S
        cfg = self.config(lista=[{"produto": "Picanha"}, {"produto": "Café Pilão 500 g"}, {"produto": "Feijão"}])
        ofs = [{"produto": "Picanha Bovina Resfriada", "preco": 59.9, "unidade": "kg"}, {"produto": "Café Pilão 500 g", "preco": "15,98"},
               {"produto": "Feijão Carioca 1 kg"}]
        lista = S.precos_por_oferta(ofs, ["Picanha", "Café Pilão 500 g", "Feijão"], {"Café Pilão 500 g"})
        self.assertEqual(lista, [{"produto": "Picanha", "base": {"quantidade": 1.0, "unidade": "kg"}, "precos": [{"preco": 59.9, "obs": "Picanha Bovina Resfriada", "fonte": None}],
                                  "tamanhos": []}], "preço por quilo; sem preço não casa; o que a IA já leu fica")
        cat, parcial = S.resultado_folheto({"nome": "Açougue Boi", "categoria": "mercados"}, {"url": "https://f/1", "ate": "2099-01-01"},
                                           {"ofertas": ofs, "lista": []}, cfg)
        self.assertEqual(cat["lojas"][0]["folheto_ate"], "2099-01-01")
        self.assertEqual(sorted(parcial), ["Café Pilão 500 g", "Picanha"])

    def test_lojas_procuradas(self):
        S = self.S
        cfg = {"raio_km": 2, "lojas": {"ignorar": ["merc-ignorada"], "manter": ["merc-mantida"], "folhetos": [{"nome": "Velha", "categoria": "farmacias"}],
                                       "adicionar": [{"nome": "Mercado Cadastrado, Centro", "categoria": "mercados"},
                                                     {"nome": "Mercado Com Site", "categoria": "mercados", "site": "https://x.com.br"}]}}
        cats = [categoria("mercados", [("merc-perto", "Mercado Perto", 1.0), ("merc-longe", "Mercado Longe", 9.0), ("merc-mantida", "Mercado Mantido", 9.0),
                                       ("merc-ignorada", "Mercado Ignorado", 0.5), ("merc-giassi", "Giassi", 1.0)]),
                categoria("online", [("onli-amazon", "Amazon", None)])]
        nomes = [(l["nome"], l["categoria"]) for l in S.lojas_folheto(cfg, categorias=cats, ja={"mercados": ["Giassi"]})]
        self.assertEqual(nomes, [("Velha", "farmacias"), ("Mercado Cadastrado", "mercados"), ("Mercado Perto", "mercados"), ("Mercado Mantido", "mercados")],
                         "sem a longe, a ignorada, a que tem site e a que já tem preço pelo site")
        self.assertEqual([l["nome"] for l in S.lojas_folheto(cfg, ["farmacias"], categorias=cats)], ["Velha"])
        rel = {"folhetos": [{"loja": "A", "ofertas": 1}]}
        S.juntar_folheto_status(rel, {"b": {"loja": "B"}, "a": {"loja": "A", "ofertas": 3}})
        self.assertEqual(rel["folhetos"], [{"loja": "A", "ofertas": 3}, {"loja": "B"}])
