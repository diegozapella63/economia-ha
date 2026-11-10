# EconomIA: instruções para quem continua o projeto (pessoa ou IA)

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
`OFERTAS_OFF` (Open Food Facts), `OFERTAS_SHOPEE_API`, `OFERTAS_OVERPASS`, `OFERTAS_GOOGLE_PLACES`, `OFERTAS_BRAVE`,
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

## Regras que não mudam

- **Dados pessoais só dentro do Home Assistant** (`/data`). O GitHub tem só o código. Nunca mandar o e-mail do dono
  (ou de ninguém) para serviço externo, cabeçalho ou URL.
- **Chaves e senhas** (Shopee, Google, Brave, Instagram, Mercado Livre) ficam só em `/data/segredos.json` (modo 600) e
  **nunca voltam para a página** (a API devolve só "tem chave"). Ninguém pede chave pelo chat: o usuário cola no app.
- **Não contornar bloqueios**: nada de burlar verificação de robô (captcha, Cloudflare, "playwright-bot-bypass"),
  nada de fingir ser o usuário, nada de usar login ou chave que a loja não abriu para nós. Respeitar o `robots.txt`
  (`robots_permite`) e o `Content-Signal: ai-input=no`. Site bloqueado fica de fora e o app diz por quê.
  Já decidido assim: Catálogos Ofertas (verificação de robô), Raia (403), Tiendeo (sem downloads), VipCommerce (busca só
  com chave da plataforma), SiteMercado (token de sessão), Instabuy (bloqueia o IP por horas). O plano grátis do Brave
  não serve para guardar preços.
- **Primeiro o que não gasta IA** (busca direta VTEX, busca do site, páginas de produto, catálogos, Shopee, folhetos);
  a IA do Home Assistant (`ai_task.generate_data`) entra por último, só para o que faltou, e pode ser desligada.
- **A Conversa (`POST /api/chat`, `conversar` no servidor) só usa tarefa de IA** (`ia_da_conversa`: `ai_task.*`),
  nunca um assistente `conversation.*`, que pode mexer na casa. A IA só **sugere** ações (`acoes_validas` confere
  cada uma com a lista); quem faz é a página, quando a pessoa toca no botão.
- O casamento item × produto é **aprendido** (vocabulário das lojas, seção da loja, código de barras, previsor do
  Mercado Livre), não uma lista fixa de palavras. Veja "Casamento do item com o produto" em `docs/tecnico.md`.

## Jeito da interface

- Textos em português claro e curto, sem jargão; botões com verbos ("Salvar e testar", "Pôr na lista").
- Mesmo visual dos outros apps da família (Barlow e Barlow Condensed, cores por tokens, tema claro e escuro, abas).
- **Mais é um menu**, como no GerencIA e no InventarIA, não uma tela de ajustes: Casa, Lojas, **Configurações** (abas
  Integrações, Dados, Aparência e Opções) e, por último, **Sobre**, cada um na sua tela. A tela aberta fica em
  `ui.maisTela` e ocupa uma entrada no histórico: o Voltar do celular, o ‹ Mais e arrastar para a direita voltam ao menu.
  Nada de misturar uma função do app com as configurações (veja "Mais: o menu" em `docs/tecnico.md`).
- Celular primeiro (390 px, a referência da família; nada sai da tela em 320 px), e no computador a barra lateral a partir de 1000 px.
- A página precisa funcionar também sem o add-on (modo exemplo), sem erros no console.
- **Inativos no fim, recolhidos**: o que está inativo, cancelado, encerrado, arquivado ou ignorado de propósito (por uma opção, como Nunca considerar) fica numa seção no fim da lista, recolhida por padrão, com o nome e a contagem (ex.: **Arquivados (3)**); abre num toque. Vale para todos os apps da família. Aqui: `<details class="inativas">`, aberto só até sair do app: as **Inativas (N)** de Mais › Lojas, as **Escondidas (N)** das Ofertas (`#dealsInat`) e os cupons **Vencidos (N)** (`#ticketsInat`).
- **Caixas de seleção no visual do app**: nenhuma janela nativa do celular. Toda caixa de seleção abre pelo selectsheet.js; sugestões de texto (no lugar do `<datalist>`) e horários (sem AM/PM) também no visual do app; a caixa fechada igual aos outros campos (altura, cantos, seta), no claro e no escuro. Aqui: `select.field` (com a seta do app) e `data-sug="<nome>"` no campo, com as sugestões em `SUG_FONTES[nome]` (a lista `.sug-box` embaixo dele), nunca `list=`.

**Padrão da família (igual em todos os apps)**
- Barra de baixo: o botão do meio é **Adicionar** (no EconomIA, a ação principal dele); **Buscar**, quando houver, é a 2ª aba; **Mais** é a última, com o ícone de três pontos.
- **Mais** é um menu: as funções do app, depois **Configurações** e por último **Sobre**. Os relatórios se chamam **Relatório de/do …**.
- **Configurações** em 4 abas, nesta ordem: **Integrações › Dados › Aparência › Opções**; abre em Integrações. Nenhuma função do app vira aba.
- **Integrações**, nesta ordem: os outros apps da família › CorrerIA › **IA do Home Assistant** (o Usar IA) › Falar › Uso da IA › Sensores.
- IA: as entradas se chamam **Colar mensagem**, **Escolher fotos** (ou **Escolher fotos ou PDF**, onde PDF vale) e **Digitalizar com IA**; a conversa recomeça em **Nova conversa**; o Voltar do celular fecha a Conversa.
- Palavras: **Apagar** (nunca Excluir); **Testar no meu celular**; **Home Assistant Cloud** (não Nabu Casa); recolhidos como **Nome (n)**; o CHANGELOG começa com "# Mudanças".
- **Dados**: Exportar › Backup na pasta share › Importar › Versões anteriores › Onde ficam os dados › Começar do zero.
- **Aparência**: o tema vale no aparelho (começa em Automático); a cor do app vale para a casa toda; uma paleta só, de 12 cores (Vermelho, Coral, Laranja, Ouro, Verde, Menta, Turquesa, Azul, Índigo, Lilás, Rosa, Grafite); a Cor do dia é a mesma em todos os apps (as 11 sem o Grafite, pelo número do dia).

Aqui não há aviso no celular ainda (o **Avisar no celular** da rotina fica de fora da tela até existir; quando entrar, é o componente da família: Quem recebe, Testar no meu celular, o horário e o A cada, como no GerencIA). O `config.yaml` não tem `panel_admin`: fica como está, no padrão do Home Assistant (o painel só para administradores), até o dono decidir outra coisa. A ação principal do meio é o **Buscar** (não há outra aba Buscar); Integrações põe as integrações próprias (Shopee, Google, Brave, Mercado Livre, Instagram, Lista do Home Assistant) entre o Uso da IA e os Sensores, e o Falar fica dentro da IA do Home Assistant (**Para falar**); a cor da casa em `config.json` (`cor`, `cor_dia`; `corDaCasa()` na página, com a cópia do aparelho em `ofertas-bairro:ui` só para o script do `<head>`); a paleta em `CORES` (as regras `:root[data-cor]` geradas das 12 cores); a Conversa ocupa uma entrada no histórico no celular (`histChat`, `fechaChat(depois)`).

## Ideias combinadas e ainda não feitas

Em ordem sugerida: "Promoção de verdade?" (o de/por contra o histórico de preços, antes da Black Friday);
ler a nota fiscal pelo QR code (preço pago, loja e data; conferir se a consulta da SEF/SC abre sem verificação de robô);
"Hora de estocar"; dia da semana de cada loja; descontos fixos por loja (cartão, cashback); custo do deslocamento
no roteiro (preço da ANP × km); reduflação; resumo semanal no celular; orçamento do mês; alerta de preço-alvo.
Pendente de antes: papel toalha com tamanho errado ("Pague Menos R$ 233,99").
