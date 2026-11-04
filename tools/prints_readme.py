#!/usr/bin/env python3
"""Refaz as imagens do README (docs/inicio.png, lista.png, roteiro.png e ofertas.png).

Abre a página do add-on (economia/app/www/index.html) num servidor local em porta livre, sem o add-on: ela roda com
o exemplo embutido (nenhum dado pessoal). O relógio fica parado no dia do exemplo (18/10, 10h) e o aviso "Exemplo"
some da tela. Celular de 390 x 844 com densidade 2 (PNG de 780 x 1688), tema escuro.

    python3 tools/prints_readme.py           grava em docs/
    python3 tools/prints_readme.py /tmp/x    grava em outra pasta (para conferir antes)

Precisa do Playwright: pip install playwright && python3 -m playwright install chromium
"""
import datetime
import functools
import http.server
import os
import struct
import sys
import threading

from playwright.sync_api import sync_playwright

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WWW = os.path.join(RAIZ, "economia", "app", "www")
DIA_DO_EXEMPLO = datetime.datetime(2026, 10, 18, 10, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=-3)))
LARGURA, ALTURA, DENSIDADE = 390, 844, 2


class Pagina(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def calma(pg):
    """Espera as animações (o cupom saindo da impressora, a troca de tela) terminarem."""
    pg.wait_for_function("document.getAnimations().every(a => a.playState !== 'running'"
                         " || (a.effect && a.effect.getTiming().iterations === Infinity))", timeout=15000)
    pg.wait_for_timeout(300)


def rola_ate(pg, seletor, folga=12):
    y = pg.locator(seletor).first.evaluate("e => e.getBoundingClientRect().top + scrollY")
    pg.evaluate("y => scrollTo(0, y)", max(0, y - folga))
    calma(pg)


def tamanho_png(caminho):
    with open(caminho, "rb") as f:
        cab = f.read(24)
    return struct.unpack(">II", cab[16:24])


def main():
    saida = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(RAIZ, "docs")
    os.makedirs(saida, exist_ok=True)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Pagina, directory=WWW))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/index.html"
    erros = []
    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={"width": LARGURA, "height": ALTURA}, device_scale_factor=DENSIDADE,
                              color_scheme="dark", has_touch=True, locale="pt-BR", timezone_id="America/Sao_Paulo")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.clock.set_fixed_time(DIA_DO_EXEMPLO)
        pg.goto(url)
        pg.wait_for_function("document.getElementById('syncText').textContent.indexOf('Carregando') < 0")
        pg.add_style_tag(content="#banner{display:none!important}")
        calma(pg)

        def foto(nome):
            caminho = os.path.join(saida, nome + ".png")
            pg.screenshot(path=caminho)
            if tamanho_png(caminho) != (LARGURA * DENSIDADE, ALTURA * DENSIDADE):
                erros.append(f"{nome}.png com tamanho {tamanho_png(caminho)}")
            print("ok", caminho)

        # Minha lista, no alto: o cupom de economia e as oportunidades
        foto("inicio")
        # um item da lista: a melhor compra, os outros preços com o ✓ e as ações
        lyso = pg.locator("#wish > li", has_text="Lysoform").first
        lyso.wait_for()
        rola_ate(pg, "#wish > li:has-text('Lysoform')")
        foto("lista")
        # Roteiro: paradas, total e o que comprar em cada loja
        pg.click(".tabbar [data-view=roteiro]")
        calma(pg)
        rola_ate(pg, "#v-roteiro .sec-meta", folga=8)
        foto("roteiro")
        # Ofertas dos mercados perto de casa
        pg.click(".tabbar [data-view=ofertas]")
        calma(pg)
        pg.locator("#cats button", has_text="Mercados").click()
        calma(pg)
        rola_ate(pg, "#v-ofertas .panel:has(#h-ofertas)")
        foto("ofertas")
        nav.close()
    srv.shutdown()
    if erros:
        raise SystemExit("Erros na página: " + "; ".join(erros))


if __name__ == "__main__":
    main()
