# EconomIA: instruções para quem continua o projeto (pessoa ou IA)

> Leia também o `PADROES.md`: os padrões da família, iguais em todos os apps. Este arquivo diz o que é só deste app e como cada padrão é feito aqui.

Leia isto antes de mexer. Vale para o Codex, o Claude ou qualquer outro assistente. O dono do projeto é o Diego
(diegozapella63), escreve em português do Brasil e espera respostas, textos de tela e documentação em português.

## O que é

App (add-on) do Home Assistant que compara a lista de compras da casa nas farmácias, mercados e pet shops perto do CEP
e no online. Faz parte de uma família de apps do mesmo dono, com o mesmo visual e as mesmas regras:
ResolvIA (tarefas), CronologIA (agenda), GerencIA (finanças), InventarIA (cômodos e equipamentos), MemorIA (anotações)
e CorrerIA (os apps no WhatsApp, no Claude e no Gemini: com a opção ligada, usa as ferramentas daqui; veja "CorrerIA" em
`docs/tecnico.md` e o contrato no AGENTS.md do `diegozapella63/correria-ha`).

- `economia/app/server.py`: o servidor, **só biblioteca padrão do Python** (sem pip, sem dependências). Serve a página
  pelo ingress, faz as buscas, guarda tudo em `/data`. `voz.py`: o Falar (fala para texto do Home Assistant).
- `economia/app/itens_comuns.txt`: a lista pronta das sugestões ao digitar um item (itens comuns e as marcas mais
  vendidas com o produto delas), **gerada** por `tools/itens_comuns.py` (as linhas de produtos de cada fabricante ficam em
  `tools/itens_marcas.py`): mude lá e rode `python3 tools/itens_comuns.py`.
- `economia/pagina/selectsheet.js`: as caixas de seleção no visual do app, **o mesmo arquivo dos outros apps** (ao
  mudar, copie para os outros); o `montar_pagina.py` põe dentro da página.
- `economia/pagina/painel.html`: **a fonte da página** (HTML + CSS + JS ES5 num arquivo só, sem framework). Roda sozinha
  com os dados de exemplo e, dentro do add-on, com `api/estado`.
- `economia/app/www/index.html`: a página do add-on, **gerada**. Nunca edite à mão: edite a fonte e rode
  `python3 tools/montar_pagina.py` (troca o Google Fonts pelas fontes embutidas em `www/fonts`).
- `economia/config.yaml`: o add-on (versão, slug `ofertas_do_bairro`, ingress na porta 8099).
- `economia/CHANGELOG.md`: o que mudou em cada versão, para o usuário. `economia/DOCS.md`: o manual (aba Documentação
  do Home Assistant). `docs/tecnico.md`: **como cada parte funciona por dentro** (leia a seção do que for mexer).
- `tests/`: unitários e integração (`unittest`) e `tests/e2e/` visuais (Playwright). Veja `tests/README.md`.

## Rodar e testar

```bash
tests/run.sh                                              # unitários e integração (550, ~1 min, só Python)
tests/e2e/run.sh                                          # visuais (21 telas a 390 px; pip install playwright; python3 -m playwright install chromium)
tests/run.sh --cobertura                                  # cobertura de linhas do servidor (98%; o GitHub exige 97%)
python3 tools/montar_pagina.py --conferir                 # a página do add-on está em dia com a fonte?
python3 tools/prints_readme.py                            # refaz as imagens do README (docs/*.png), com o exemplo embutido
```

Para abrir o painel fora do Home Assistant (dados numa pasta qualquer):

```bash
OFERTAS_DATA=/tmp/economia OFERTAS_PORT=8099 OFERTAS_ALLOW_ALL=1 python3 economia/app/server.py
```

Variáveis só para testes: `OFERTAS_VTEX_TESTE` (lojas VTEX falsas), `OFERTAS_ML_API`/`OFERTAS_ML_AUTH` (Mercado Livre),
`OFERTAS_OFF` (Open Food Facts), `OFERTAS_SHOPEE_API`, `OFERTAS_ALIEXPRESS_API`, `OFERTAS_OVERPASS`, `OFERTAS_GOOGLE_PLACES`, `OFERTAS_BRAVE`,
`OFERTAS_GRAPH`, `OFERTAS_HA_API`/`OFERTAS_HA_WS`, `OFERTAS_CASA`, `OFERTAS_VOZ_SIMULADA`. O `tests/apoio.py` tem as
lojas falsas (`LojasFalsas`) e carrega o servidor numa pasta de dados temporária (`servidor()`); o `tests/ha_falso.py`
é o Home Assistant falso (IA, listas, fala para texto). Veja `tests/README.md`.

Toda mudança de comportamento vem com teste. Bug corrigido ganha o teste que o pegaria.

## Lançar uma versão (sempre que algo muda para o usuário)

1. Versão nova num lugar só: `economia/config.yaml` (`version`). O servidor lê de lá (o Dockerfile copia o config.yaml para
   `/app`) e o `tools/montar_pagina.py` põe na página do add-on, no lugar do `'__VERSAO__'` da fonte.
2. `economia/CHANGELOG.md`: entrada nova no alto, em português, dizendo o que muda para quem usa.
3. `docs/tecnico.md`: a seção técnica do que mudou (nomes de funções, arquivos, regras). `economia/DOCS.md` quando muda
   algo que o usuário vê.
4. `python3 tools/montar_pagina.py`, depois os testes (unitários, integração e visuais) todos passando.
5. Commit com mensagem `EconomIA x.y.z: resumo em português` (como nos outros apps da família), `git pull --rebase` e push no
   `main`. O Home Assistant oferece a atualização sozinho.

## Arquivos iguais em todos os apps

A lista fica em `tools/iguais.py` e as regras, em **Arquivos iguais** e **Os apps conversam** do `PADROES.md`.

## Regras que não mudam

- **Dados pessoais só dentro do Home Assistant** (`/data`). O GitHub tem só o código. Nunca mandar o e-mail do dono
  (ou de ninguém) para serviço externo, cabeçalho ou URL.
- **Chaves e senhas** (Shopee, AliExpress, Google, Brave, Instagram, Mercado Livre) ficam só em `/data/segredos.json` (modo 600) e
  **nunca voltam para a página** (a API devolve só "tem chave"). Ninguém pede chave pelo chat: o usuário cola no app.
- **Não contornar bloqueios**: nada de burlar verificação de robô (captcha, Cloudflare, "playwright-bot-bypass"),
  nada de fingir ser o usuário, nada de usar login ou chave que a loja não abriu para nós. Respeitar o `robots.txt`
  (`robots_permite`) e o `Content-Signal: ai-input=no`. Site bloqueado fica de fora e o app diz por quê.
  Já decidido assim: Catálogos Ofertas (verificação de robô), Raia (403), Tiendeo (sem downloads), VipCommerce (busca só
  com chave da plataforma), SiteMercado (token de sessão), Instabuy (bloqueia o IP por horas). O plano grátis do Brave
  não serve para guardar preços.
- **Primeiro o que não gasta IA** (busca direta VTEX, busca do site, páginas de produto, catálogos, Shopee, AliExpress, folhetos);
  a IA do Home Assistant (`ai_task.generate_data`) entra por último, só para o que faltou, e pode ser desligada.
- **A Conversa (`POST /api/chat`, `conversar` no servidor) só usa tarefa de IA** (`ia_da_conversa`: `ai_task.*`),
  nunca um assistente `conversation.*`, que pode mexer na casa. A IA só **sugere** ações (`acoes_validas` confere
  cada uma com a lista); quem faz é a página, quando a pessoa toca no botão.
- O casamento item × produto é **aprendido** (vocabulário das lojas, seção da loja, código de barras, previsor do
  Mercado Livre), não uma lista fixa de palavras. Veja "Casamento do item com o produto" em `docs/tecnico.md`.

## Jeito da interface

- Textos em português claro e curto, sem jargão; botões com verbos ("Salvar e testar", "Pôr na lista").
- Mesmo visual dos outros apps da família (Barlow e Barlow Condensed, cores por tokens, tema claro e escuro, abas).
- **Mais é um menu**, como no GerencIA e no InventarIA, não uma tela de ajustes: Casa, Lojas, Reposição, **Configurações** (abas
  Integrações, Dados, Aparência e Opções) e, por último, **Sobre**, cada um na sua tela. A tela aberta fica em
  `ui.maisTela` e ocupa uma entrada no histórico: o Voltar do celular, o ‹ Mais e arrastar para a direita voltam ao menu.
  Nada de misturar uma função do app com as configurações (veja "Mais: o menu" em `docs/tecnico.md`).
- Celular primeiro (390 px, a referência da família; nada sai da tela em 320 px), e no computador a barra lateral a partir de 1000 px.
- A página precisa funcionar também sem o add-on (modo exemplo), sem erros no console.
- **Inativos no fim, recolhidos**: o que está inativo, cancelado, encerrado, arquivado ou ignorado de propósito (por uma opção, como Nunca considerar) fica numa seção no fim da lista, recolhida por padrão, com o nome e a contagem (ex.: **Arquivados (3)**); abre num toque. Vale para todos os apps da família. Aqui: `<details class="inativas">`, aberto só até sair do app: as **Inativas (N)** de Mais › Lojas, as **Escondidas (N)** das Ofertas (`#dealsInat`) e os cupons **Vencidos (N)** (`#ticketsInat`).
- **Caixas de seleção no visual do app**: nenhuma janela nativa do celular. Toda caixa de seleção abre pelo selectsheet.js; sugestões de texto (no lugar do `<datalist>`) e horários (sem AM/PM) também no visual do app; a caixa fechada igual aos outros campos (altura, cantos, seta), no claro e no escuro. Aqui: `select.field` (com a seta do app) e `data-sug="<nome>"` no campo, com as sugestões em `SUG_FONTES[nome]` (a lista `.sug-box` embaixo dele), nunca `list=`.

**Padrão da família**: as regras de todos os apps estão no `PADROES.md` (igual nos 8 repositórios; leia antes de mexer). Como cada uma é feita aqui:
- Ícones: `iconesTitulos` (`T_IC`, pelas palavras de `T_PAL`) e `iconesBotoes` (`B_PAL`), no `iniciar()`; o `tests/e2e/ec_familia.py` confere.
- **Reposição** (1.46.0, Mais › Reposição): o que se compra de tempos em tempos (`config.reposicao`), que na hora aparece no cartão **Hora de repor** da Minha lista; com as chaves de **Opções › Reposição** (`config.repor`, desligadas de início), o item pode ser escolhido entre os remédios do CronologIA (`remedios` no `share/cronologia/integracao.json`) e os consumíveis do InventarIA (`/api/integracao/consumiveis`, com a chave do `share/inventario/integracao.json`). Só o nome escolhido fica guardado aqui; mudar esses formatos exige mudar os outros apps junto (veja "Reposição" em `docs/tecnico.md`). 1.46.3: os consumíveis do InventarIA 1.82.0 vêm com `duracao_dias` (sem `quantidade`); o item da fonte leva `dias` e o **A cada** já vem com ela (`repFonte`: 30 → 1 mês, 7 → 1 semana).
- **Comprei hoje → Reposição → InventarIA** (1.49.0, com o InventarIA 1.87.0): na página, o `[data-comprei]` chama `repComprou(produto)`: o item da Reposição com o nome igual ou parecido (`repParecido`/`repChave`, a regra do `nome_parecido` do servidor) recomeça de hoje, o consumível do InventarIA com esse nome é avisado (`repAvisaInventario` → `POST /api/reposicao/comprado {nome, dias?}` → `inventario_comprado` → `POST <InventarIA>/api/integracao/consumiveis/comprado`, só com `repor.inventario` ligado; 404 de lá não é erro) e o cartão `#repComprou` pergunta **Dura quanto tempo?** (`REP_DUR`; a escolha grava `cada`/`unidade`, cria o item da Reposição se não havia, com `origem: inventario` quando é um consumível, e manda os `dias` ao InventarIA; **Agora não** fecha). A ferramenta `comprei` da CorrerIA faz o mesmo (`dura_dias`; a Reposição vai em `repor` no diário, que o `aplicar_diario` junta). Mudar o formato exige mudar o InventarIA junto.
- **Compras no EconomIA** (1.47.0, para o InventarIA 1.85.0): com `repor.inventario` ligado, o app grava `share/economia/integracao.json` (`app`, `nome`, `versao`, `gravado_em`, `url`, `ip_url`, `chave` própria em `/data/integracao.key`, `compras: /api/integracao/compras`; 600, atômico; desligado, some; nenhum dado da casa) e responde, fora do ingress e só com `Authorization: Bearer <chave>` (401 desligado ou chave errada), em `GET /api/integracao/compras?nome=` → `{versao, nome, na_lista, vezes, ultima, compras (as 5 últimas datas), reposicao: {cada, unidade, texto, proxima, na_hora} ou null}` (`compras_de`: o `norm` do nome contra a lista, o histórico e a Reposição) e `POST {nome, acao: lista | repor, dias?}` → o mesmo, com `texto` (`compras_fazer`: o `_ferr_por` e o `_ferr_repor` das ferramentas, o diário e a revisão; `dias` é a duração do consumível, `_dias_em_cada`; 400 `{erro}`). 1.48.0: o nome casa pelo igual ou pelo parecido (`nome_parecido`: o mesmo tipo, a primeira palavra das `palavras_busca`, sem o plural, e as palavras de um dentro das do outro; primeiro o que tem todas as do nome, depois o de menos palavras de diferença; `_compras_achar`), a resposta ganha `item` (o nome do item daqui que casou), `reposicao.nome` e `listas` (os nomes das listas prontas, só com mais de uma), e o `POST` aceita `lista`; o Pôr na lista e o Repor usam o item parecido que já existe. Mudar o formato exige mudar o InventarIA junto.
- **Falar** (1.46.0): o cartão dele em Integrações, depois do IA, com os textos dos outros apps (Pronto para ouvir · Transcreve com…, **Fala para texto** com **Automático: nome**, **Verificar de novo**, que lê os motores na hora com `?novo=1`, e **Como configurar**); as perguntas prontas da Conversa no meio, uma por linha; um site citado na tela é um link que abre o site (`a.site`).
- **Sub-opções**: o que só vale com uma chave ligada fica num quadro recuado logo abaixo dela (`.sub-op > .sub-box`: a IA embaixo de Usar IA, a lista `#sensLista` embaixo de **Criar sensores**).
- **Abas**: quando as abas não cabem na largura, a ponta de onde há mais some aos poucos, com uma seta (`marcaAbas`, `.abas-wrap`).
- Contrair e expandir: `aplicaDobras` e `alternaDobra`; a chave é o id do cabeçalho, em `economia.fechadas` no localStorage.

Aqui não há aviso no celular ainda (o **Avisar no celular** da rotina fica de fora da tela até existir; quando entrar, é o componente da família: Quem recebe, Testar no meu celular, o horário e o A cada, como no GerencIA). O `config.yaml` não tem `panel_admin`: fica como está, no padrão do Home Assistant (o painel só para administradores), até o dono decidir outra coisa. A ação principal do meio é o **Buscar** (não há outra aba Buscar); Integrações põe as integrações próprias (Shopee, Google, Brave, Mercado Livre, Instagram, Lista do Home Assistant) entre o Uso da IA e os Sensores, e o Falar fica dentro da IA do Home Assistant (**Para falar**); a cor da casa em `config.json` (`cor`, `cor_dia`; `corDaCasa()` na página, com a cópia do aparelho em `ofertas-bairro:ui` só para o script do `<head>`); a paleta em `CORES` (as regras `:root[data-cor]` geradas das 12 cores); a Conversa ocupa uma entrada no histórico no celular (`histChat`, `fechaChat(depois)`).

1.54.3 (o dono: "revisar as 20 perguntas padrões da IA, tem algumas muito específicas"): as **perguntas prontas** da Conversa (as 6 à vista e as 20 do Mais perguntas, `PERG_APP`) são gerais e valem em qualquer casa: nada de itens, valores, lojas ou nomes inventados («Comprei o pão», «Quanto custa o arroz em cada mercado?»); o pedido com o detalhe é o que a pessoa escreve. Vale em todos os apps da família.

## Ideias combinadas e ainda não feitas

Em ordem sugerida: "Promoção de verdade?" (o de/por contra o histórico de preços, antes da Black Friday);
ler a nota fiscal pelo QR code (preço pago, loja e data; conferir se a consulta da SEF/SC abre sem verificação de robô);
"Hora de estocar"; dia da semana de cada loja; descontos fixos por loja (cartão, cashback); custo do deslocamento
no roteiro (preço da ANP × km); reduflação; resumo semanal no celular; orçamento do mês; alerta de preço-alvo.
Pendente de antes: papel toalha com tamanho errado ("Pague Menos R$ 233,99").

**Teclado no celular** (1.46.5): em `economia/pagina/teclado.js` (embutido pelo `tools/montar_pagina.py`, como o `textareas.js`), o `tecladoCalmo` (o mesmo código do `teclado.js` dos outros apps): com o foco num campo de texto, ou quando o teclado muda a altura da tela, as páginas em volta do app (a do Home Assistant) voltam para o começo; a página do próprio app não é tocada.

1.48.1: na Conversa, no celular (`noCelular()`: `(hover: none) and (pointer: coarse)`, o dedo como jeito principal), o Enter é uma linha nova e o botão envia (`enterkeyhint="enter"`); com teclado de verdade, o Enter envia. Vale em todos os apps da família. Na Minha lista, o Histórico (`#histBtn`) e o Código de barras (`#codBtn`) são quadrinhos (`.ler-tile.hist-btn`) da `.ler-tiles`, na linha de baixo (os da IA levam o `so-ia` cada um). Os vinhos das sugestões ficam em `"Vinhos"` no `tools/itens_marcas.py`.

1.51.0: as lembranças da casa (a Memória da IA do CorrerIA 1.28.0, em `share/correria/lembrancas.json`: `{lembrancas: [frases]}`) vão na frente de toda instrução da IA daqui, logo depois da guarda, só com a opção CorrerIA ligada: `lembrancas_da_casa()` no server.py (relido uma vez por minuto; `ECONOMIA_LEMBRANCAS` troca o arquivo nos testes), usada no `chamar_ai_task`.

1.52.0 (o dono: "e se eu não usar o CorrerIA e só decidir usar o InventarIA e o ResolvIA?"; "memória compartilhada"; "deixa claro na observação das opções que a memória é compartilhada"): a **Memória da IA** é uma só, da casa, de todos os apps, em `share/familia/memoria_ia.json` (`{versao: 1, gravado_em, lista: [{id, texto, em, app, quem?}]}`, até 60 frases de 240 letras, 600; `MEMORIA_IA_ARQ` troca o arquivo nos testes), e não depende mais da opção CorrerIA nem do arquivo do CorrerIA (o `share/correria/lembrancas.json` acabou). `economia/app/memoria_ia.py` (igual nos quatro apps em Python); no server.py, `MEMORIA_ARQ` (a pasta acima do `OFERTAS_SHARE`), `lembrancas_da_casa()` = `memoria_ia.para_a_ia` (no `chamar_ai_task`), `memoria_estado()`, `memoria_mudar(c, quem)` e as rotas `GET`/`POST /api/memoria-ia` (`{acao: nova, texto}` | `{acao: apagar, id}` → `{lista, max}`; 400 `{erro}`); na página, a seção `#memoriaIa` (`so-ia`) logo antes do Falar (`carregaMemoria`, `pintaMemoria`, `mudaMemoria`; o modo exemplo imita). É dado da casa na pasta share do Home Assistant, sem chave nem senha. Testes: `tests/test_memoria_ia.py`, `tests/test_memoria_ia_api.py`, o trecho no `tests/test_ia.py` e `tests/e2e/ec_memoria.py`. O texto do cartão é o mesmo em todos os apps: «Uma memória só, da casa, compartilhada por todos os apps: o que você escreve aqui a IA lembra em toda conversa, em qualquer um deles.» A memória não entra no Exportar nem no Começar do zero de um app.

1.52.1: a vez de gravar a Memória da IA entre os apps (`memoria_ia.py: `_vez``: uma pasta `memoria_ia.json.trava` ao lado do arquivo, criada num passo só; espera até 3 s, tira a que ficou de um app que caiu, há mais de 10 s, e sem a vez grava assim mesmo; o arquivo temporário leva um sufixo ao acaso). Antes, dois apps gravando no mesmo instante liam a mesma lista e um apagava a frase do outro (num teste com 40 gravações simultâneas, uma se perdia). Um caminho que não é uma pasta não prende o app (espera só o prazo).

1.52.2 (o dono: "esses campos com scroll quebram as pernas"): o campo da Memória da IA cresce com o texto (`field-sizing: content`, até 40vh), sem rolagem dentro dele; uma linha continua com 50 px e o tamanho puxado pelo canto continua guardado.

1.52.2: a Conversa abre sempre no chat (`abreChat` zera `CHAT.menu`, `CHAT.rapidas` e `CHAT.ed`; o `ec_chat` confere).


1.53.0: as ferramentas `mudar_item`, `nova_lista` e `guardar_cupom` (diários `campos`, `nova_lista` e `cupom`).

1.54.0: **Selecionar** na Minha lista (`SELL`, `entraSel`, `saiSel`, `pintaSel`, `selFaz`, `#selBar`; o histórico como o do Comparar) e o `mudar_item` com `lista` e `setor: automatico` (ver `docs/tecnico.md`; teste `ec_selecionar`).

1.54.4 (a revisão dos padrões da família, `PADROES.md`: todo botão com texto tem ícone): `bIc(k)` (o `<svg class="b-ic">` de um `T_IC`) nos botões feitos depois do `iniciar()`, que o `iconesBotoes` não alcança: o **Mandar encarte** e o **Adicionar site** do `#semPrecos`. O `ec_ofertas` confere.

1.55.0 (o dono, no ResolvIA: "Tirar foto não funciona (abre a galeria) e Escolher fotos… nada acontece"; "veja se esse bug tem em outros apps"): o app do Home Assistant no Android ignora o `capture` e perde o que se escolhe com `multiple` (`haAndroid()`). O **Tirar foto** do clipe da Conversa abre a câmera do app (`abreCam('chat')`, a mesma do Código de barras, `#codCamUI.livre`: sem a guia, sem o Escolher foto e sem ler o código; o botão manda a foto para o `poeArqs`); sem câmera (http) ou sem permissão, o seletor (`escolheArqChat`). No Android, os `#encArq`, `#fotoArq` e `#cupArq` (no `iniciar()`) e o Escolher fotos da Conversa ficam sem `multiple`. O `ec_chat` confere a câmera (com um `getUserMedia` de mentira).

1.56.0 (o dono: "do mesmo jeito que criamos esse agrupar por… [nos Consumíveis do InventarIA]… a gente precisa adicionar ele em outros locais"): Minha lista › Agrupar por: `#listaAgrupar` (`pintaAgrupar`: o título `.agrupar-l` com `data-agrupar-dobra`, `ui.agruparFechado`; o `.seg.agrupar-seg` com `data-agrupar`, `ui.agrupar`; fora do Selecionar), `opcoesAgrupar` (Nenhum, Onde comprar com mais de um setor ligado, Loja), `gruposLista` (Onde comprar pelo `setorDe`; Loja pelo `lojaDe`, a escolha, a melhor compra ou o mais barato, como o `precoResumido`) e, no `pintaLista`, o `cartao` de cada item dentro dos grupos (`li.wish-grp` com o `.grp-h`, `data-grupo`, `ui.gruposLista`). Teste: `tests/e2e/ec_agrupar.py`.
