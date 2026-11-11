# Testes do EconomIA

Três camadas, rodando a cada push no GitHub (aba Actions):

| Camada | Onde | Como rodar | O que confere |
|---|---|---|---|
| Unitários | `tests/test_*.py` | `tests/run.sh` (o mesmo que `python3 -m unittest discover -s tests -p "test_*.py"`) | cada parte do servidor (`economia/app/server.py` e `voz.py`), sem Home Assistant de verdade e sem internet |
| Integração | `tests/test_api*.py` (no mesmo comando) | idem | o servidor pela API HTTP, num processo ou no mesmo, contra lojas e Home Assistant falsos |
| Visuais | `tests/e2e/ec_*.py` | `tests/e2e/run.sh` (ou `tests/e2e/run.sh ec_lista ...`) | a página no Chromium (Playwright), num celular de 390 px (as de computador e de tamanhos, na largura delas): clica, digita, confere e grava capturas |

Só Python 3 para as duas primeiras (uns 60 segundos), e nada de internet: os pedidos para fora vão para um proxy que
não existe, e tudo o que o app consulta é falso e local. As visuais precisam de `pip install playwright` e
`python3 -m playwright install chromium`; as capturas ficam em `$E2E_TMP/shots`. Um script visual que falha por tempo esgotado
(`TimeoutError` do Playwright; o GitHub às vezes fica lento) roda mais uma vez: a linha `~~` e o `logs/<script>.1.txt`
guardam a 1ª falha. Uma conferência que falha não repete.

Cobertura de linhas (sem dependências): `tests/run.sh --cobertura` (o mesmo que `TZ=America/Sao_Paulo python3
tools/cobertura.py --linhas`) mostra o % de cada arquivo do servidor e as linhas que nenhum teste roda. Na 1.9.1: 98,1% do
`server.py` e 98,9% do `voz.py`. A página (`economia/pagina/painel.html`) não tem cobertura medida: o Playwright em
Python não dá a cobertura do JavaScript, e ela é conferida pelos visuais, tela a tela.

Regras: nada de relógio real além do que o app já usa (o GitHub roda com `TZ=America/Sao_Paulo`), nada de `sleep` para
esperar (espera-se a condição: `Cenario.espera`, `espera()` nas visuais), sempre portas livres.

## Peças de apoio

- `apoio.py`: `servidor()` carrega o `server.py` do zero numa pasta de dados temporária, sem internet; `LojasFalsas`
  responde como a busca da VTEX (regiões, texto, código de barras, seção), o OAuth e o previsor de categorias do
  Mercado Livre, o Open Food Facts, páginas soltas (com cabeçalhos, redirecionamento ou `FECHA`, a conexão fechada sem
  resposta) e rotas com função (`rotas[caminho] = f(pedido)`: Overpass, Google, Brave, Graph API, Shopee); `prod()` monta
  um produto da VTEX; `categoria()` uma categoria do `ofertas.json`; `Cenario` é a base dos testes novos (lojas falsas,
  Home Assistant falso e servidor ligados entre si, `config()`, `ofertas()`, `espera()`).
- `ha_falso.py`: o Home Assistant falso (REST e WebSocket): estados, `ai_task.generate_data` com roteiro por tarefa
  (resposta, função ou `Erro`), assistentes de conversa, listas de tarefas (`todo.*`), fala para texto (`/api/stt`),
  assistentes de voz pelo WebSocket, token conferido e tudo o que chegou guardado para conferir.
- `e2e/base_e2e.py`: o servidor do add-on num processo com as lojas falsas (`App`), o Chromium (`pagina`), `check`,
  `espera` e `abrir_mais(pg, onde)`, que abre Mais e a linha da tela (casa, lojas, config, sobre) ou Configurações numa
  aba (integracoes, dados, aparencia, opcoes).

## Unitários e integração

- `test_ajudantes.py`: a resposta da IA fora do formato e o JSON no meio do texto, o tipo de cada chamada, preço e data,
  o @ do Instagram, blocos de texto da página, tamanho de imagem, períodos de folheto, robots.txt, o teste de um site que
  não responde (cada erro explicado), distância entre palavras, tamanhos repetidos e textos para a IA.
- `test_casamento.py`: palavras, "ou", tipo do produto, parecido, restrições, fragrâncias, dose (500 mg = 500mg),
  vocabulário (os mais recentes, palavras associadas), correção de digitação, código de barras e `casados.json`.
- `test_utilidades.py`: números, tamanhos e pacotes, links, datas, robots.txt, meta tags e schema.org, nomes de loja.
- `test_normalizar.py`: a resposta da IA de cada categoria virando lojas, cupons, ofertas, preços da lista, tamanhos,
  a junção de categorias e o casamento do item.
- `test_juntar.py`: montar os preços de um item, normalizar a resposta, juntar categorias, o `ofertas.json` gravado
  (a loja consultada de novo, a mesma loja em outra categoria, a busca completa e o relatório).
- `test_busca_direta.py`: preço por peso, seção da loja, similares, "ou", item pelo código, produto pelo código (loja e
  Open Food Facts, fora do ar), nome corrigido, loja que não atende o CEP ou não responde, loja achada fora do bairro.
- `test_paginas.py`: dados embutidos nos scripts, texto das páginas, página do produto, sitemap, busca do site e
  páginas de ofertas (limites, validade, robots.txt).
- `test_sites_e_dados.py`: páginas das lojas sem IA, busca do site com robots.txt, Shopee (assinatura), versões, uso da
  IA, exportar (JSON e planilha, as lojas que não contam), categoria das lojas.
- `test_lojas_online.py`: o robots.txt e a busca direta nas lojas VTEX achadas, sitemap, busca do site, página de
  ofertas, Shopee (busca e erros), o site das lojas pelo Brave e pela IA, o teste de cada loja e a ordem dos scripts
  (uma fonte que quebra não para as outras).
- `test_sondagem.py`: o teste de preço de cada loja passo a passo (VTEX, sitemap, outro produto, página de ofertas,
  Instagram, folheto, marketplaces), as rodadas (Encontrar lojas e Testar agora) e o resultado posto em cada loja.
- `test_mercadolivre.py`: autorização, renovação, revogação, limite por hora, 429, cache (até 8000), erros e o filtro.
- `test_mapa.py`: OpenStreetMap e Google juntos, filial mais perto, falhas no meio, site pelo Google, Encontrar lojas,
  lojas sem localização (com erros e limite) e a cidade do CEP.
- `test_folhetos.py`: Kimbino, Seus Folhetos, Portafolhetos e Catálogos Ofertas: links e validade, páginas e tamanho
  das imagens, robots.txt e `ai-input=no`, verificação de robô (não contorna), o site que recusa, quebra ou vem vazio,
  as capas, a leitura guardada até vencer e os limites por busca.
- `test_instagram.py`: a conta pela chave, a validade, os erros da Meta, os posts de oferta, as lojas com Instagram,
  a leitura guardada, imagens que não baixam e a IA que falha.
- `test_ia.py`: a chamada à IA do Home Assistant (estruturada, em texto, erros, cota, desligada), conversa, uso e
  sensor (120 dias, sensor que falha), lista de IAs, Testar a IA, os pedidos de cada categoria e o registro.
- `test_busca_ia.py`: o Buscar de ponta a ponta (sites primeiro, uma pergunta por categoria, cota, IA desligada,
  encarte do site, itens sem preço) e o que não pode derrubar a busca; a busca de poucos itens.
- `test_leitura.py`: Ler com IA (foto, mensagem, fala), cupons do app, encarte mandado pelo morador, encarte do site
  (limites de arquivos e tamanho) e os erros (pasta de mídia, erro inesperado, foto que não é base64).
- `test_sincronizacao.py`: a Minha lista com a lista de tarefas do Home Assistant, nos dois sentidos, o diário e o laço.
- `test_voz.py`: Falar (opções, escolha, áudio para texto, erros) e o WebSocket do Home Assistant falado à mão
  (ping, pedaços, mensagens grandes, wss, cada erro), contra um servidor de soquete com roteiro.
- `test_privacidade.py`: o e-mail do dono nunca sai, cada chave só vai para o serviço dela, as chaves não ficam no
  config.json nem no arquivo exportado, as fotos saem da pasta de mídia.
- `test_api.py`: página e fontes, Mais como menu (as linhas, as abas de Configurações, nenhum texto com o caminho
  antigo), estado, config, integrações (chaves nunca voltam), Mercado Livre do começo ao fim, código de barras, correção,
  acesso só pelo Home Assistant (servidor num processo).
- `test_api_fluxos.py`: os fluxos pela API com o Home Assistant falso (busca, leitura, sincronizar, Falar, integrações)
  e o `main()`, com o servidor num processo.
- `test_comparar.py`: Comparar preço (a oferta nas outras lojas): sites primeiro e a IA só se faltar, a loja da oferta
  de fora, outro tamanho pelo preço por quilo, medidas diferentes, online com frete, o que guarda e os erros.
- `test_correria.py`: a CorrerIA pelas ferramentas: o arquivo em share (só ligado, modo 600, chave guardada), a rota com
  a chave (401, 404, 400), cada ferramenta com as regras da tela, o diário que junta a gravação da página e as lojas
  desligadas em Online.
- `test_api_rotas.py`: cada rota no mesmo processo, com os casos de sucesso e de erro (corpo inválido ou grande, IA
  desligada, HA fora, busca ou teste já rodando) e o acesso só pelo ingress.

## Visuais

- `e2e/ec_busca_velha.py`: a última busca com mais de 3 dias em alerta no alto (há N dias, Buscar agora) e na barra lateral; até 3 dias, como antes.
- `e2e/ec_lista.py`: a lista com preços (busca de verdade contra lojas falsas), similares, escolher, roteiro, adicionar,
  "Quis dizer…?", Comprei hoje, histórico, limpar.
- `e2e/ec_codigo.py`: código de barras por foto (deitada, em pé, de ponta-cabeça, borrada, com ruído, pequena, EAN-8,
  UPC-A) e por número, loja, Open Food Facts, balança, número errado, item com o código.
- `e2e/ec_integracoes.py`: Mercado Livre em Mais › Configurações › Integrações, do salvar ao apagar.
- `e2e/ec_integracoes_chaves.py`: Shopee, Google, Brave e Instagram em Mais › Configurações › Integrações (salvar,
  testar, apagar, chave que nunca volta para a página), Usar IA e a escolha das IAs.
- `e2e/ec_lojas.py`: Mais › Lojas: abas, procurar, só sem fonte, inativas, clube, loja sem localização.
- `e2e/ec_lojas_acoes.py`: Encontrar lojas, Testar agora, Como foi testado, adicionar e ignorar loja.
- `e2e/ec_ofertas.py`: Ofertas e cupons por categoria, filtros, cupom que vence, online com frete; as escondidas no fim, em
  Escondidas (N), e os cupons vencidos em Vencidos (N), recolhidos até um toque.
- `e2e/ec_comparar.py`: Comparar preço numa oferta (busca de verdade contra as lojas falsas): mais barato em outra loja,
  menor preço, não achado, "Comparando…", o aviso no fim, depois de recarregar; 390 px e 320 px.
- `e2e/ec_correria.py`: Integrações › CorrerIA: ligar (o arquivo), uma ferramenta grava e a página avisa "pela
  CorrerIA", o último uso, recarregar e desligar (o arquivo some e a rota fecha).
- `e2e/ec_roteiro.py`: o roteiro de compras por loja, distância e total.
- `e2e/ec_buscar.py`: o Buscar com o andamento, a cota, o erro e os avisos.
- `e2e/ec_ler_ia.py`: Ler com IA (mensagem, foto, cupons, encarte) e o Falar com microfone falso do Chromium; no encarte,
  as lojas sugeridas no visual do app, embaixo do campo (sem `<datalist>`).
- `e2e/ec_dados.py`: Mais › Configurações › Dados: exportar (downloads), importar, versões e restaurar.
- `e2e/ec_aparencia.py`: tema claro e escuro, a Cor do dia (ligada de começo, escolher uma cor desliga, a troca na virada do dia com relógio de mentira), sem IA, estados vazios e textos sem inglês.
- `e2e/ec_tamanhos.py`: os tamanhos do item, a base e o preço por quilo ou litro.
- `e2e/ec_mais.py`: Mais é um menu (Casa, Lojas, Configurações e Sobre por último): as linhas (ícone, título, o que tem,
  seta, alinhadas, nada cortado), cada tela com o ‹ Mais e só o painel dela, as abas de Configurações (só a aba aberta,
  as setas do teclado, a aba guardada, as quatro cabendo em 320 px), o ‹ Mais, o Voltar, arrastar e o Mais de baixo
  voltando ao menu, recarregar na mesma tela, o atalho Preencher o perfil (o Voltar volta para a Minha lista), quem vinha
  das abas da 1.2 e o endereço #lojas; 390 px escuro, 320 px claro e o computador.
- `e2e/ec_sobre.py`: Mais › Sobre, a última linha do menu de Mais: os textos, os 8 links para o GitHub, a versão em Este
  app, o Voltar, o ‹ Mais e arrastar de volta para o menu, recarregar em Sobre; 390 px escuro, 320 px claro e o computador.
- `e2e/ec_selecao.py`: as caixas de seleção (`economia/pagina/selectsheet.js`, igual nos outros apps): tocar abre a
  janela do app (não a do celular), título, opções, a atual marcada, cores do app no escuro e no claro; escolher grava;
  Voltar, X e tocar fora fecham só ela; no computador, no meio e pelo teclado; fechada, igual aos outros campos (altura,
  cantos, borda) e com a seta do app.
- `e2e/ec_desligado.py`: com a opção ou a integração desligada, nada promete o que não acontece: Rotina de compras sem
  Avisar no celular, Compras online só com a aba Online, a ordem da busca sem as etapas desligadas, Similares e código de
  barras sem a busca direta, Lista do Home Assistant sem sincronizar, Instagram e Shopee, loja adicionada sem IA.
- `e2e/ec_desktop.py`: no computador (1280 px): barra lateral, ações no alto e colunas lado a lado.

`python3 tools/montar_pagina.py --conferir` (também no GitHub) garante que a página do add-on foi montada da fonte.
