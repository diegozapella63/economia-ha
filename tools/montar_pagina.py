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
# os arquivos iguais aos dos outros apps, ao lado da fonte; no add-on, vão embutidos: as caixas de seleção no visual do
# app (selectsheet.js) e os campos de texto que guardam o tamanho (textareas.js, 1.19.0)
IGUAIS = ("selectsheet.js", "textareas.js")
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


CONFIG = os.path.join(RAIZ, "economia", "config.yaml")


def versao():
    """A versão fica num lugar só, o economia/config.yaml; a página do add-on recebe no lugar do __VERSAO__."""
    import re
    return re.search(r'^version:\s*"?([\d.]+)', open(CONFIG, encoding="utf-8").read(), re.M).group(1)


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
    for nome in IGUAIS:
        tag = '<script src="%s"></script>' % nome
        js = open(os.path.join(RAIZ, "economia", "pagina", nome), encoding="utf-8").read()
        if s.count(tag) != 1 or "</script" in js:
            raise SystemExit("A fonte precisa carregar o %s uma vez, antes do script da página." % nome)
        s = s.replace(tag, "<script>\n" + js.rstrip("\n") + "\n</script>")
    if s.count("'__VERSAO__'") != 1:
        raise SystemExit("A fonte precisa ter a versão uma vez, como '__VERSAO__'.")
    s = s.replace("'__VERSAO__'", "'" + versao() + "'")
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
