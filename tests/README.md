# Testes do EconomIA

Três camadas, rodando a cada push no GitHub (aba Actions):

| Camada | Onde | Como rodar | O que confere |
|---|---|---|---|
| Unitários | `tests/test_*.py` | `python3 -m unittest discover -s tests -p "test_*.py"` | cada parte do servidor (`economia/app/server.py`), sem Home Assistant e sem internet |
| Integração | `tests/test_api.py` (no mesmo comando) | idem | o servidor de verdade num processo, pela API, contra lojas falsas |
| Visuais | `tests/e2e/ec_*.py` | `tests/e2e/run.sh` | a página no Chromium (Playwright): clica, digita, confere e grava capturas |

Só Python 3 para as duas primeiras (uns 30 segundos). As visuais precisam de `pip install playwright` e
`python3 -m playwright install chromium`; as capturas ficam em `$E2E_TMP/shots`.

- `apoio.py`: `servidor()` carrega o `server.py` do zero numa pasta de dados temporária; `LojasFalsas` responde como a
  busca da VTEX (regiões, texto, código de barras, seção), o OAuth e o previsor de categorias do Mercado Livre, o Open
  Food Facts e páginas soltas; `prod()` monta um produto da VTEX.
- `test_casamento.py`: palavras, "ou", tipo do produto, parecido, restrições, fragrâncias, vocabulário, correção de
  digitação, código de barras e o que fica guardado em `casados.json`.
- `test_utilidades.py`: números, tamanhos e pacotes, links, datas, robots.txt, meta tags e schema.org, nomes de loja.
- `test_busca_direta.py`: preço por peso, seção da loja, similares, "ou", item pelo código, produto pelo código (loja e
  Open Food Facts), nome corrigido, loja que não atende o CEP.
- `test_juntar.py`: montar os preços de um item, normalizar a resposta, juntar categorias, o `ofertas.json` gravado.
- `test_mercadolivre.py`: autorização, renovação, revogação, limite por hora, 429, cache e o filtro de categoria.
- `test_sites_e_dados.py`: páginas das lojas sem IA, busca do site com robots.txt, Shopee (assinatura), versões, uso da
  IA, exportar (JSON e planilha), categoria das lojas.
- `test_api.py`: página e fontes, estado, config, integrações (chaves nunca voltam), Mercado Livre do começo ao fim,
  código de barras, correção, acesso só pelo Home Assistant.
- `e2e/ec_lista.py`: a lista com preços (busca de verdade contra lojas falsas), similares, escolher, roteiro, adicionar,
  "Quis dizer…?", Comprei hoje, histórico, limpar.
- `e2e/ec_codigo.py`: código de barras por foto (deitada, em pé, de ponta-cabeça, borrada, com ruído, pequena, EAN-8,
  UPC-A) e por número, loja, Open Food Facts, balança, número errado, item com o código.
- `e2e/ec_integracoes.py`: Mercado Livre em Mais › Integrações, do salvar ao apagar.
- `e2e/ec_lojas.py`: Mais › Lojas: abas, procurar, só sem fonte, inativas, clube, loja sem localização.

`python3 tools/montar_pagina.py --conferir` (também no GitHub) garante que a página do add-on foi montada da fonte.
