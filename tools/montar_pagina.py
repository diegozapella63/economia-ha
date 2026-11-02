#!/usr/bin/env python3
"""Monta economia/app/www/index.html (a página do add-on) a partir de economia/pagina/painel.html (a fonte).

A fonte é a mesma página da demonstração: carrega as fontes do Google Fonts e roda sozinha com os dados de exemplo.
No add-on, as fontes vão embutidas (fonts/*.woff, funciona sem internet) e o cabeçalho ganha o viewport do app.

    python3 tools/montar_pagina.py            monta
    python3 tools/montar_pagina.py --conferir  só confere se o index.html está igual ao que sairia (usado nos testes)
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTE = os.path.join(RAIZ, "economia", "pagina", "painel.html")
DESTINO = os.path.join(RAIZ, "economia", "app", "www", "index.html")

CABECALHO = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}img{max-width:100%}</style>"""

GOOGLE_FONTS = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600'
                '&family=Barlow+Condensed:wght@500;600;700&display=swap">')
PRECONNECT = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n', '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n')
FACES = (("Barlow", "barlow", 400), ("Barlow", "barlow", 500), ("Barlow", "barlow", 600),
         ("Barlow Condensed", "barlow-condensed", 500), ("Barlow Condensed", "barlow-condensed", 600), ("Barlow Condensed", "barlow-condensed", 700))


def montar(fonte_txt):
    if fonte_txt.count(GOOGLE_FONTS) != 1:
        raise SystemExit("A fonte precisa ter exatamente um <link> do Google Fonts (Barlow e Barlow Condensed).")
    faces = ['@font-face{font-family:"%s";font-style:normal;font-weight:%d;font-display:swap;src:url(fonts/%s-%d.woff) format("woff")}'
             % (fam, peso, arq, peso) for fam, arq, peso in FACES]
    s = fonte_txt.replace(GOOGLE_FONTS, "<style>\n" + "\n".join(faces) + "\n</style>")
    for p in PRECONNECT:
        s = s.replace(p, "")
    if "fonts.googleapis" in s or "gstatic" in s:
        raise SystemExit("Sobrou link do Google Fonts na página.")
    return CABECALHO + "\n" + s.rstrip("\n") + "\n\n</html>\n"


def main():
    novo = montar(open(FONTE, encoding="utf-8").read())
    if "--conferir" in sys.argv:
        atual = open(DESTINO, encoding="utf-8").read() if os.path.exists(DESTINO) else ""
        if atual != novo:
            raise SystemExit("economia/app/www/index.html está diferente da fonte: rode python3 tools/montar_pagina.py")
        print("index.html em dia com a fonte")
        return
    with open(DESTINO, "w", encoding="utf-8") as f:
        f.write(novo)
    print("index.html montado")


if __name__ == "__main__":
    main()
