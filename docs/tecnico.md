# EconomIA: detalhes técnicos

Painel de cupons, ofertas e lista de compras de farmácias, mercados e pet shops perto de casa, aberto pelo menu lateral do Home Assistant (ingress).

Todos os dados ficam no Home Assistant, na pasta `/data` do add-on:

| Arquivo | Quem grava | Conteúdo |
| --- | --- | --- |
| `config.json` | o painel | CEP, distância, categorias, lojas, lista, perfil, rotina, ofertas escondidas |
| `ofertas.json` | a busca de ofertas | lojas, cupons, ofertas e preços da lista |

Sem `ofertas.json`, o painel mostra um exemplo embutido.

A fonte da página é `economia/pagina/painel.html` (a mesma da demonstração, com o Google Fonts); `python3 tools/montar_pagina.py`
gera `economia/app/www/index.html` com as fontes embutidas e o `economia/pagina/selectsheet.js` dentro da página (no
lugar do `<script src="selectsheet.js">`). O `selectsheet.js` é o mesmo arquivo em todos os apps da família (ResolvIA,
CronologIA, MemorIA, GerencIA e InventarIA): as caixas de seleção abrem uma janela no visual do app em vez da janela
do celular (a escolha entra na própria `<select>`, com os eventos `input` e `change`), com a cor de `--accent` e o
fundo e o texto de `--surface` e `--ink`; ao mudar, copie para os outros. Fechada, `select.field` tem `appearance: none` e a
seta do app (um `background-image`), com a altura e os cantos dos outros campos. Sugestões de texto, no lugar do
`<datalist>` (que no Android abre a lista do celular): o campo com `data-sug="<nome>"` mostra embaixo dele (`.sug-box`)
até 6 de `SUG_FONTES[nome]()` que combinam com o que foi digitado (`norm`, sem acento); tocar preenche (no `click`, com o
`pointerdown` barrado para o campo não perder o foco) e dispara `input` e `change`. Hoje: `#encLoja` (as lojas do tipo
da aba, `SUG_FONTES.encLojas`). Os testes estão em `tests/` (veja `tests/README.md`) e as
instruções para quem continua o projeto, em `AGENTS.md`.

Tipografia: Barlow (texto) e Barlow Condensed (títulos e números), embutidas em `economia/app/www/fonts` como WOFF (subconjunto latino, licença SIL OFL em `fonts/OFL.txt`), para funcionar sem internet.

## Busca de ofertas

O botão **Buscar** chama `ai_task.generate_data` pela API do Home Assistant (`homeassistant_api: true`), uma vez por categoria ativa. A resposta é validada antes de gravar: ofertas e cupons sem URL de fonte são descartados, preços precisam ser números e a oferta precisa ser menor que o preço normal. Se uma categoria falhar, fica o resultado anterior dela.

## Rotas (relativas ao ingress)

| Método | Rota | O que faz |
| --- | --- | --- |
| GET | `/` | Página do painel. |
| GET | `/api/estado` | `{config, ofertas, usuario}`. `usuario` vem do cabeçalho `X-Remote-User-Display-Name` do ingress. |
| PUT | `/api/config` | Grava `config.json`. |
| PUT | `/api/ofertas` | Grava `ofertas.json` (precisa ter `categorias`). |
| POST | `/api/chat` | Conversa: `{mensagens: [{de: "eu" ou "ia", texto}], tela}` → `{resposta, acoes}`. Ver "Conversa com a IA". |
| POST | `/api/buscar` | Começa a busca agora, uma categoria por vez, pela ação `ai_task.generate_data` do HA. No fim, faz uma pergunta só sobre os itens que ficaram sem preço. |
| POST | `/api/buscar-itens` | `{itens: ["Pó lava louça"]}` (até 8 itens da lista): busca só esses itens e junta ao `ofertas.json` atual. Com `rapida: true` (Compra rápida), itens fora da lista também (de 2 a 80 letras; o da lista vai com o nome de lá), só nas lojas físicas. |
| GET | `/api/busca` | Andamento: `{rodando, etapa, atual, total, erro, avisos, terminou_em}`. |
| GET | `/api/exportar/lista.xlsx` | Lista em Excel: loja mais barata, preços, economia e datas de compra. |
| GET | `/api/exportar/lista.json` | A mesma lista em JSON. |
| GET | `/api/todos` | Listas de tarefas (`todo.*`) do Home Assistant. |
| POST | `/api/sincronizar-lista` | Sincroniza agora com a lista escolhida em `config.sync`. |
| POST | `/api/ler-lista` | `{imagens: ["data:image/jpeg;base64,..."], texto}` (até 4 imagens, 16 MB no total). Devolve `{id}`. |
| GET | `/api/ler-lista?id=...` | `{status: "lendo|pronto|erro", itens: [{produto, quantidade, ja_na_lista}], erro}`. |
| GET | `/api/ias` | `{tarefas: [{id, nome, anexos}], agentes: [{id, nome}]}`: entidades `ai_task.*` e `conversation.*`. |
| POST | `/api/testar-ia` | `{uso: "busca"|"fotos"}` → `{ok, msg}`. A busca faz uma pergunta curta que exige busca na web. |
| GET | `/api/voz/status` | `{pronta, motor, idioma, nome, usando, escolha, escolha_sumiu, opcoes: [{id, nome, preferido}]}` ou `{pronta: false, motivo}`. `opcoes`: os assistentes de voz com fala para texto (`pipeline:{id}`) e as entidades `stt.*` que nenhum assistente usa. A escolha fica em `config.ia.voz`; em branco (ou se sumiu), vale o assistente preferido. |
| POST | `/api/voz` | Corpo: áudio PCM cru, 16 kHz, 16 bits, mono (até 2 min). Manda para `POST /api/stt/<motor>` do HA com o cabeçalho `X-Speech-Content` e devolve `{texto}`. O painel lê o texto em `/api/ler-lista` com `origem: "fala"`. |
| GET | `/api/versoes` | `{versoes: [{nome, quando, motivo, itens, cep}]}`: as 3 cópias mais recentes do `config.json`, em `/data/versoes`. |
| POST | `/api/versoes/guardar` | `{motivo: "importar"|"limpar"}`: guarda uma cópia agora. |
| POST | `/api/versoes/restaurar` | `{nome}`: guarda uma cópia do atual e volta para essa versão. Devolve `{config}`. |
| POST | `/api/ler-encarte` | `{imagens: ["data:image/jpeg;base64,..."], loja, categoria}` (até 8 imagens). A IA de fotos lê o encarte ou o print com o mesmo pedido do encarte do site; o resultado é juntado ao `ofertas.json` (loja com `fontes: ["Encarte"]`). Devolve `{id}`; o andamento sai em `GET /api/ler-lista?id=` com `{status, ofertas, precos, loja, itens}`. |
| GET | `/api/lojas-diretas` | `{lojas: [{id, nome, atende, loja, fixa}]}`: as lojas com busca direta e se atendem o CEP; as lidas pelas páginas de produto vêm com `paginas: true`. |
| GET | `/api/integracoes` | `{shopee: {app_id, tem_senha}}`. A senha nunca sai do add-on. |
| PUT | `/api/integracoes` | `{shopee: {app_id, secret}}` grava em `segredos.json` (modo 600); `secret` vazio mantém a senha guardada; `{shopee: null}` apaga. |
| POST | `/api/integracoes/testar` | `{servico: "shopee"}` → `{ok, msg}`: uma consulta de teste na Open API. |
| POST | `/api/lojas-mapa/atualizar` | `{raio_km, categorias}`: lê o mapa agora (`forcar`) e junta as lojas ao `ofertas.json` (`mesclar_resultado` com `mapa`), sem buscar preços. Devolve `{ok, msg, lojas: {categoria: n}}`. |
| GET | `/api/lojas-mapa/teste` | `{rodando, atual, total, loja, terminou_em, resumo}`: andamento do teste de preço. |
| GET | `/api/lojas-mapa` | `{fontes, em, lojas: {categoria: [{nome, endereco, distancia_km, fonte}]}}`: as lojas do raio pelo mapa. |
| GET | `/api/folhetos` | `{lojas: [{nome, categoria, status: {fonte, folhetos, lidos, guardados, ofertas, ate, erro, em}}]}`. |
| GET | `/api/exportar/ofertas.json` | O `ofertas.json` da última busca. |
| GET | `/api/uso-ia` | `{hoje, semana, mes: {chamadas, erros, cota, tokens, imagens, segundos, tipos, ias}, dias: [{dia, chamadas, erros, cota}], ultimas: [...]}`. Também vai em `/api/estado` como `uso_ia`. |
| GET | `/api/saude` | Verificação simples. |

### Busca direta nas lojas

Giassi e Angeloni (fixos) e as lojas achadas por `testa_site` usam a plataforma VTEX. Para cada item da lista, o add-on pergunta `GET {site}/api/checkout/pub/regions?country=BRA&postalCode={CEP}` (a loja que atende o CEP, guardada por 6 horas) e `GET {site}/api/io/_v/api/intelligent-search/product_search/?query={item}&regionId={região}`. Entram os produtos com estoque cujo nome ou categoria têm as palavras do item; o tamanho sai do nome ("250ml", "1L Caixa com 12"). O resultado vira a categoria `mercados`, com `fonte` no link do produto, e é juntado depois da IA, então vale mais. Não usa login nem IA. Para testar fora do HA, `OFERTAS_VTEX_TESTE` aponta para um servidor falso.

### Ordem da busca: primeiro o que não gasta IA

`busca_scripts` roda antes da IA: busca direta (VTEX), páginas de produto, Shopee e folhetos. As lojas com preço da lista vindo do site vão no pedido da IA ("já vieram direto do site delas: …") para ela não repetir. Os resultados dos scripts são juntados depois da IA e valem mais. `buscar_itens` só chama a IA para os itens com menos de 2 preços. Com `usar_ia: false`, `/api/buscar` roda só os scripts e junta ao `ofertas.json` atual (`mesclar_resultado`).

### Lojas testadas sozinhas (`lojas_site.json`)

Candidatas: as lojas de `lojas.adicionar` com site, as lojas das categorias físicas do `ofertas.json` com `site` e os mercados regionais de Online (o site sai dos links dos preços). Cada origem é testada uma vez por semana (`testa_site`): lê o `robots.txt` (regras de `User-agent: *`, com `*` e `$`, a regra mais longa vale) e só chama `/api/checkout/pub/regions` se `/api/checkout/pub/regions` e `/api/io/_v/api/intelligent-search/product_search/` forem permitidos. Resposta em lista = VTEX → entra em `VTEX_ACHADAS` e na busca direta, na categoria da loja. Se o `robots.txt` não vem, o motivo fica em `erro` e o texto da exceção em `detalhe`: 401/403/429 = "recusou o acesso de programas"; `RemoteDisconnected`, conexão resetada ou abortada, `EOF occurred` e `IncompleteRead` = "fechou a conexão sem responder" (proteção contra robôs; o add-on não tenta contornar). Esses dois casos marcam `bloqueio: true`; timeout, SSL e DNS têm texto próprio; o resto mostra o detalhe.

Sites das lojas do mapa: `osm_lojas` guarda `website`/`contact:website`/`brand:website`; `google_lojas` pede `places.websiteUri`. Sem site, `site_da_rede` reconhece redes conhecidas pelo nome sem palavras genéricas nem a cidade (`SITES_REDES`), igual ou, para as redes de `SITES_COM_FILIAL`, seguido do nome da filial; o `testa_site` confirma. `POST /api/lojas-mapa/atualizar` também chama `atualiza_diretas(max_novas=15)` em segundo plano.

### Teste de preço das lojas (`fontes_preco.json`)

Depois do `POST /api/lojas-mapa/atualizar`, `sonda_lojas` roda em segundo plano: `atualiza_diretas(max_novas=30)` e, para cada loja acompanhada das categorias físicas, `testa_preco_loja` tenta um termo de exemplo (`TERMO_TESTE`): VTEX liberada → `regiao_direta` + `busca_vtex`; páginas liberadas → `baixa_catalogo` + `procura_catalogo` + `preco_produto`; senão folheto guardado ou `achar_folhetos` (até 8 lojas novas). Resultado `{como: site|paginas|folheto|folheto_novo|ia|nenhum, exemplo, site, passos: ["✓ …", "✗ …"], em}` por categoria e nome; `marca_fontes` põe em cada loja (`preco_fonte`) ao gravar o `ofertas.json`.

### Páginas de produto (`catalogos/`)

Para origens com `paginas: true` que não são VTEX liberada: `baixa_catalogo` lê os `Sitemap:` do robots.txt (ou `/sitemap.xml`), segue o índice priorizando os sitemaps de produto (aceita .gz) e guarda as URLs de produto (VTEX: terminam em `/p`) por 1 dia, respeitando o robots.txt. Para cada item, as até 3 URLs cujo texto tem as palavras do item (`combina`) são abertas, uma a cada 0,3 s, e o preço sai do JSON-LD `Product` → `offers` (`price`/`lowPrice`, sem `OutOfStock`) ou da meta `product:price:amount`, guardado por 1 dia. Loja fora do raio (não está em `lojas_perto` nem em `lojas.adicionar`) entra em `online` com `frete: null, carrinho: true`.

### Lojas do raio pelo mapa (`lojas_mapa.json`)

`casa()` lê `GET /api/states/zone.home` (latitude e longitude). `osm_lojas` faz um POST ao Overpass (`OFERTAS_OVERPASS`) com `amenity=pharmacy`, `shop=chemist`, `shop~supermarket|convenience|wholesale|greengrocer|butcher` e `shop=pet` em `around:{raio},{lat},{lon}`; com `segredos.google.key`, `google_lojas` chama `places:searchNearby` (Places API New, `rankPreference: DISTANCE`, 20 por tipo) e `google_varredura` chama `places:searchText` (`OFERTAS_GOOGLE_TEXTO`) com "farmácia", "drogaria", "supermercado", "mercado" e "pet shop", `locationRestriction` no quadrado do raio, `rankPreference: DISTANCE`, até 3 páginas (`nextPageToken`) enquanto vierem lojas dentro do raio; só entram lugares com os tipos de `GOOGLE_TIPOS`. Lojas sem site depois disso (as só do OpenStreetMap, fora das redes de `SITES_REDES`) ganham o site por `google_site` (Text Search pelo nome, `locationBias` de 500 m, mesmo nome e até 400 m); a resposta fica em `lojas_mapa.json` › `sites` por 30 dias. Nomes todos em maiúsculas passam por `nome_bonito` (também os já registrados, em `aplica_mapa`). `site_loja`/`social_loja` separam site de verdade de rede social, WhatsApp, Linktree e apps de entrega (`REDES_SOCIAIS`): esses ficam em `social` e não são testados como site. `da_categoria` tira de farmácias e mercados as lojas de outra categoria: pelo `primaryType` do Google (`OUTRA_CATEGORIA`: `pet_store`, `veterinary_care`; em mercados também `pharmacy`/`drugstore`) e pelo nome (`NOME_FORA`: pet, vet, veterinária, animal, agropecuária); vale no OpenStreetMap, no Nearby e na busca por texto, e `aplica_mapa` remove as lojas só do mapa (`fontes == ["Mapa"]`) que não passam. Distância em linha reta (haversine). Lojas da mesma rede (`chave_loja`: sem "farmácia", "drogaria", "supermercado"…) ficam uma só, a filial mais perto, até 30 por categoria; guardado por 7 dias por casa, raio, categorias e fonte. O pedido de cada categoria leva a lista (`mapa_txt`), e `aplica_mapa` põe endereço e distância do mapa nas lojas de todas as fontes e acrescenta as do mapa que faltaram (`fontes: ["Mapa"]`).

### Folhetos (`folhetos.json`)

Candidatas (`lojas_folheto`): as lojas físicas acompanhadas (fora de `lojas.ignorar`, no raio ou em `lojas.manter`), do `ofertas.json` anterior e, depois da IA, as recém-achadas, mais `lojas.adicionar` sem site, menos as que têm preço pelo site. Até 8 lojas novas procuradas por busca e até 3 com folheto novo lido pela IA. O nome vira começos de endereço sem palavras genéricas nem a cidade (`bases_loja`: "Komprão Koch Atacadista" → `komprao`, `komprao-koch`). `achar_folhetos` tenta `https://www.kimbino.com.br/{base}/` (e `-atacadista`, `-supermercados`, `supermercados-{base}`…) e `https://seusfolhetos.com.br/{base}-ofertas`; o endereço achado fica guardado por 14 dias (loja inexistente: 7 dias). Na página da loja, os links de folheto (Kimbino: `/{loja}/…-{id}/`; Seus Folhetos: `/{loja}-ofertas/folheto-{id}-0`) e o período ("29/10/2026 - 01/11/2026") entre um link e o próximo; antes do link, só o texto que ainda não foi lido como do folheto anterior (sem data própria, a validade vem da página do folheto). Só entram os válidos hoje. Páginas do folheto: Kimbino, as imagens `kimbicdn.com/…/data/{pasta}/{página}.jpg` da pasta que mais aparece (prefere `/0x0/`); Seus Folhetos, as `/public/gimg/…/{id}-{w}-{h}.jpg` do tamanho comprido mais comum. Mais de 2 folhetos: a IA vê só as capas (até 8 por chamada) com a cidade do CEP (ViaCEP) e responde `sim|nao|nao_sei` (guardado em `_vale`). Até 2 folhetos por loja, até 12 páginas, 8 por chamada, com o pedido de `instrucoes_encarte`. A resposta fica em `itens[id].r` até `ate`, com os itens da lista guardados pelo nome. `precos_por_oferta` casa itens da lista com as ofertas do folheto sem IA.

### Shopee Afiliados

`POST https://open-api.affiliate.shopee.com.br/graphql`, corpo `{"query": "{productOfferV2(keyword: \"…\", sortType: 1, page: 1, limit: 20) {nodes {…}}}"}`, cabeçalho `Authorization: SHA256 Credential={AppId}, Timestamp={ts}, Signature={sha256_hex(AppId + ts + corpo + Secret)}`. Entram produtos com nota ≥ 4,5 cujo nome tem as palavras do item; preço `priceMin`, link `productLink` (não o de afiliado). Erros 10020/10030/10035 param as consultas seguintes. `OFERTAS_SHOPEE_API` troca o endereço nos testes.

### Preços online e de quando são

Preço online: `{preco, frete, prazo_dias, obs}`; `frete: null` com `carrinho: true` quando a loja só mostra no carrinho (a IA responde `"frete": "carrinho"`). Lojas de `online` que não são marketplace ganham `regional: true`. Cada item da lista tem `vistos: {rede: {em, via}}` com `via` = `site`, `api`, `encarte` ou `web`.

### Uso da IA

As ações `ai_task.generate_data` e `conversation.process` não devolvem tokens nem custo. O add-on conta cada chamada em `uso_ia.json` (por dia, até 120 dias): tipo (`busca`, `itens`, `encarte`, `fotos`, `cupons`, `teste`), entidade, resultado (`ok`, `cota`, `formato`, `erro`), segundos, imagens e tokens estimados (caracteres do pedido e da resposta ÷ 4).
Com `config.sensores` ligado (vem desligado), a cada chamada e na virada do dia publica `sensor.economia_ia_hoje` pela API de estados do HA: o estado é o número de chamadas de hoje (`state_class: total_increasing`) e os atributos trazem `erros`, `cota_excedida`, `tokens_texto_estimados`, `imagens`, `por_tipo`, `ultimos_7_dias`, `este_mes` e `ultima_chamada`. O sensor some se o HA reiniciar e volta no minuto seguinte. Desligado, o add-on apaga o sensor (`DELETE /api/states/...`) ao iniciar e quando a opção muda.

Os sensores da lista (1.21.0): `estados_lista(cfg, of)` monta `sensor.economia_melhor_loja` e `binary_sensor.economia_oferta`. A melhor loja usa `redes_acompanhadas` (as mesmas lojas do `dados_lista`, sem as online) e `valor_total` (o clube só nas lojas de `config.clubes`); para cada loja, conta os itens da lista com preço lá e soma `preço × qtd_item`; vence a que tem mais itens e, empatado, o menor total; `economia` soma `(média das lojas − preço lá) × qtd` nos itens dela. A oferta usa `_ofertas_vivas` (sem as escondidas e as de `nunca`) e a regra do `economia_preco`: todas as palavras do item (com mais de 2 letras e sem os números) no nome da oferta. `publica_sensores_lista` (no `laco_sincronizacao`, a cada minuto, e depois do `publica_sensor_uso`) só manda quando o corpo muda (`_sensores_lista["sig"]`) ou a cada 15 minutos; `remove_sensor_uso` apaga os três.
Com `config.usar_ia` em `false`, nenhuma chamada de IA sai: `/api/buscar`, `/api/ler-lista` e `/api/voz` respondem 400.

### O que compensa mais no roteiro (1.25.0)

`compensaDe(it, p, r)`: sem `it.escolha`, a `dica` do `melhorTamanho` (só com `principal` e numa loja física) vira a opção do item no `itensDoRoteiro` (`{y: {id, v: total do pacote, obs: o tamanho}, q: 1, auto: true}`, como uma escolha). Na parada, o item mostra o tamanho e "o que compensa mais".

### Benefícios do clube (1.24.0)

`POST /api/clube/beneficios {nome, clube}` (409 com a IA desligada): `beneficios_clube` chama `chamar_ai_task("EconomIA: clube <nome>", instrucoes_clube(...), uso="busca")` (tipo `clube` no Uso da IA), confere com `limpa_clube` (o nome do clube, custo, como entrar, até 8 benefícios com título, a fonte só se `url_ok`; sem clube, `{clube: null, beneficios: []}`) e guarda em `clubes.json` por `chave_loja(nome)`. `/api/estado` manda `clubes`; na página, `beneficiosHtml(c, l)` (ao lado do `clubeHtml`, nas lojas com clube ou já procuradas) e `buscaBeneficios(rid)`; o aberto fica em `CLUBE_ABERTO`.

### Mercados da região que entregam (1.22.0)

`config.online.entrega_km` (10, 15, 20, 30 ou 50; `entrega_km(cfg)` aceita só os maiores que `raio_km`, e sem escolha usa 15 ou o primeiro maior) e `online.entrega_sim` (nomes confirmados à mão). `mercados_da_regiao(cfg)` lê os mercados do mapa (`osm_lojas` com `tipos`: primeiro as redes de `REDES_REGIAO` pelo nome e pela marca, depois supermercados e atacados; com chave, `google_redes`, uma Text Search por rede com `locationBias` na distância de entrega, porque o Nearby traz só os 20 mais perto) entre `raio_km` e `entrega_km`, um por rede, sem as redes com loja no raio (`categoria_da_loja`), até 12, e confere a entrega com `testa_entrega(site, cep)`: `testa_site` (robots.txt e a VTEX) e a consulta `/api/checkout/pub/regions` (com vendedor: entrega; vazia: não entrega; sem consulta, bloqueado ou sem site: `atende: None`, com os passos). Guarda em `mercados_regiao.json` por 7 dias (a chave muda com a casa, o raio, a distância e o CEP). Lido no começo da busca, no **Encontrar lojas** e em `POST /api/regiao/atualizar` (a página chama ao ligar o interruptor ou mudar a distância). `aplica_regiao` (no `mesclar_resultado`) põe cada um em Online (`regional`, `distancia_km`, `lat`/`lon`, `entrega`, e `entrega.confirmada`); `candidatos_site` manda para a busca direta os que o site diz que entregam; `entrega_txt` diz à IA a distância e os que entregam (pelo site ou confirmados). Os que não entregam e não foram confirmados ficam fora das acompanhadas (`nao_entrega` no `redes_acompanhadas`; `acompanha` na página), e o raio deles é o de entrega (`raioDe(id)` na página). Na página: `pintaEntregaKm`, `atualizaRegiao`, `entregaHtml` e `entregaSim`; só a loja do raio da casa esconde o mesmo mercado em Online.

### Ofertas: lojas que aparecem e o Destaque

`acompanha(id)` na página: além de `lojas.ignorar`/`manter` e do raio, na aba Online o marketplace fora de `online.marketplaces` (`mktDe(nome)`) e os mercados da região com `online.mercados_entrega` desligado não contam. Ligar uma dessas lojas em Mais › Lojas (`setAcompanha`) liga também o marketplace na busca ou os mercados da região; desligar tira o marketplace da busca. Os botões de loja (`pintaFiltros`) mostram só as lojas com oferta para mostrar (`comOferta`; as escondidas não contam), e somem com menos de 2. As escondidas (`escondida(o)`: perfil, `perfil.nunca` e `ocultas`) ficam fora de `#deals`, no fim, em `#dealsInat` (`<details class="inativas">` **Escondidas (N)**, recolhido; aberto só até sair do app, em `OCULTAS_ABERTO`), com as mesmas ações (`acaoOferta`); os cupons vencidos (`valido_ate` antes de hoje), em `#ticketsInat` (**Vencidos (N)**, `VENCIDOS_ABERTO`). É a regra dos apps da família: inativos no fim, recolhidos, com o nome e a contagem, como as **Inativas (N)** de Mais › Lojas. O **Destaque para você** é um botão: volta o filtro para Todas e rola até a linha (`li[data-oferta]`), que pisca (`.achada`).

### CorrerIA (o WhatsApp, o Claude e o Gemini)

O contrato é o mesmo dos outros apps (AGENTS.md do CorrerIA). Com `correria: true` na configuração (**Mais › Configurações ›
Integrações › CorrerIA**, desligado por padrão e sem depender da IA), `publicar_correria` grava `share/economia/correria.json`
(`OFERTAS_SHARE`, modo 600, de uma vez): `app: "economia"`, `nome`, `assunto`, `versao` (a do `config.yaml`, `VERSAO`), `url`
(`http://<nome do contêiner>:8099`; `OFERTAS_URL_INTERNA` troca), `ip_url`, `chave` (própria, em `/data/correria.key`) e
`ferramentas: "/api/integracao/ferramentas"`. Sem `rota`: a conversa fica com a IA do CorrerIA. Grava no `main()` e quando
o PUT `/api/config` liga ou desliga; desligado, o arquivo some. A rota (`Painel._ferramentas`) não passa pelo ingress: vale
a chave (`Authorization: Bearer`, `hmac.compare_digest`) com a opção ligada; senão 401. `GET` → `{instrucoes, ferramentas}`
(`FERRAMENTAS_CORRERIA`); `POST {nome, argumentos, pessoa, cliente}` → `{texto}`, 400 `{erro}` (`ErroFerramenta`: o que
vale) ou 404. Ferramentas: `lista`, `preco`, `ofertas` (`categoria`, `loja`, `busca`, `limite` até 50), `cupons` (leitura,
com `redes_acompanhadas` e sem as escondidas) e `por_na_lista`, `tirar_da_lista`, `comprei` (`data` até hoje), que gravam
como a tela (`entraNaLista`, `vaiProHistorico` → `vai_pro_historico`): o item é achado pelo nome igual ou pelo único que
contém o nome (`_indice_na_lista`). Cada gravação guarda a versão anterior, sobe a `rev` com `mudou_por: "CorrerIA"` (a
página avisa "pela CorrerIA"; a próxima gravação tira) e entra no `DIARIO` (`novo` com o `item`, `saiu`, `compra`): a página
que gravar com a revisão velha junta pelo `aplicar_diario`. O último uso fica em `CORRERIA_USO` e vai no `/api/estado`
(`correria: {ligada, ultimo}`). `redes_acompanhadas` também tira, em Online, o marketplace fora de `online.marketplaces`
(`mkt_id`) e os mercados da região com `mercados_entrega` desligado (a mesma regra da página).

### Conversa com a IA

`conversar` no `server.py`. A página manda as últimas 12 mensagens (até 2000 letras cada; a mensagem da IA leva junto
"(Sugeri: …, feito)" com as ações e o que a pessoa fez) e a tela aberta. `contexto_chat` monta o que a IA vê: data e dia
da semana, tela, casa (`descreve_casa`), clubes, a lista com o mais barato e as compras (`dados_lista`, até 80 itens), o
histórico mais comprado fora da lista (15), as ofertas de maior desconto das lojas acompanhadas (`redes_acompanhadas`;
15, ou 40 na tela Ofertas; sem as escondidas) e os cupons válidos (confirmados e os do usuário). A IA é sempre uma tarefa
de IA (`ia_da_conversa`: a de fotos, a de busca ou a opção do add-on, só `ai_task.*`; sem nenhuma, a preferida do HA),
nunca `conversation.*`. A resposta pedida é `{"resposta", "acoes"}`; texto solto também vale como resposta. As ações
(`por_na_lista`, `tirar_da_lista`, `comprei`, `buscar`, `abrir`) passam por `acoes_validas`: item da lista pelo nome
normalizado (ou o único que contém o nome), produto novo só se não estiver na lista, tela que existe, sem repetidas, até 6.
Uso contado como `conversa`. **Vale a pena?** (cada oferta, 1.6.0) manda `web: true`: o uso vira `avaliar`, e `ia_da_conversa(web=True)` prefere a IA de busca (a de fotos depois), sempre só `ai_task.*`; as instruções pedem o veredito (Vale a pena, Depende ou Não vale) com a nota, as avaliações, as reclamações e o preço de costume pela busca na web. A página guarda a conversa no `localStorage` do aparelho (`ofertas-bairro:chat`, 40 mensagens).

### Leitura de fotos

As imagens são gravadas por um instante em `/media/economia` (o add-on mapeia a pasta `media`) e vão para `ai_task.generate_data` como `attachments` (`media-source://media_source/local/economia/...`). O arquivo é apagado depois da resposta.

### Sincronização com a lista do Home Assistant

A cada minuto (e quando o painel volta a ficar visível), o add-on lê a lista escolhida com `todo.get_items`:
item novo pendente entra na Minha lista (`origem: "ha"`); item que passa a concluído registra a compra do dia.
No outro sentido, usa `todo.add_item` para itens novos do painel e para os que devem acabar em até um dia.
`config.json` tem `rev`, que sobe a cada gravação; se o painel salvar com uma revisão antiga, o servidor junta as mudanças que vieram do HA antes de gravar.

O servidor só aceita conexões do ingress (`172.30.32.2`). Para testar fora do HA:
`OFERTAS_ALLOW_ALL=1 OFERTAS_DATA=/tmp/ofertas python3 economia/app/server.py`

## config.json

```json
{
  "cep": "89200-000",
  "raio_km": 2,
  "categorias": ["farmacias", "mercados", "petshops"],
  "lojas": {"ignorar": ["raia"], "manter": ["imperatriz"], "adicionar": [{"categoria": "mercados", "nome": "Mercado Salles", "site": "https://www.mercadosalles.com.br/ofertas"}]},
  "lista": [{"produto": "Café torrado e moído · 500 g", "compras": ["2026-09-20", "2026-09-30"]}],
  "perfil": {"adultos": 2, "criancas": 0, "bebes": 0, "pets": {"cachorro": 0, "gato": 1, "outros": 0}, "restricoes": [], "interesses": ["skincare", "cafe"], "nunca": ["alcool"]},
  "cotidiano": {"mercado": ["sab"], "farmacia": ["qua"], "avisar": "vespera", "estoque": "pouco|normal|bastante"},
  "roteiro": {"paradas": 2, "escopo": "tudo|acabando", "online": true},
  "ia": {"busca": "conversation.google_generative_ai", "fotos": "ai_task.google_ai_task"},
  "usar_ia": true,
  "sensores": false,
  "opcoes": {"itens_sem_preco": true, "encartes_auto": true, "lojas_diretas": true},
  "clubes": ["merc-condor"],
  "cupons_meus": [{"id": "meu-1", "rede": "farm-panvel", "beneficio": "20% em protetor solar", "codigo": null, "valido_ate": "2026-10-24"}],
  "ocultas": ["giassi-cerveja-12"]
}
```

## ofertas.json

```json
{
  "versao": 2,
  "gerado_em": "2026-10-19T07:52:00-03:00",
  "proxima_atualizacao": "2026-10-26T07:52:00-03:00",
  "lista": [{"produto": "Lysoform", "precos": {"giassi": 21.9, "atacadao": 17.49},
             "base": {"quantidade": 1, "unidade": "L"},
             "tamanhos": [{"rede": "atacadao", "embalagem": "Galão 5 L", "quantidade": 5, "preco": 79.9}]}],
  "categorias": [{
    "id": "mercados", "nome": "Mercados", "singular": "Mercado",
    "redes":   [{"id": "giassi", "nome": "Giassi", "curto": "Giassi", "nota": "texto opcional"}],
    "lojas":   [{"rede": "giassi", "distancia_km": 0.8, "horario": "Aberto até 22h", "fontes": ["Site", "Encarte"]}],
    "cupons":  [{"rede": "giassi", "codigo": "X", "valor": 10, "beneficio": "R$ 10 de desconto", "condicao": "Acima de R$ 100", "valido_ate": "2026-10-31", "status": "confirmado|testar|login"}],
    "ofertas": [{"id": "giassi-arroz-5kg", "rede": "giassi", "produto": "Arroz branco tipo 1 · 5 kg", "preco_normal": 27.9, "preco_oferta": 21.9,
                 "tipo": "promo|clube|atacado", "unidade": "kg", "condicao": "A partir de 12 unidades", "receita": "tarja|mip", "tags": ["alimentos"]}],
    "contas":  [{"rede": "condor", "libera": "Ofertas ativadas no Clube Condor", "status": "pendente|conectada"}]
  }]
}
```

- `lista[].links`: `{rede: URL}` da página do produto de cada preço; `tamanhos[].fonte` é o link de cada embalagem. Sem link, o painel abre a busca do produto na loja (Mercado Livre, Amazon, Shopee, Magalu) ou no Google.
- `relatorio`: `{categorias: {id: {ok, ofertas, lojas, precos} | {ok: false, erro}}, sem_preco: ["item"], falhas: []}`, da última busca. O registro do add-on mostra, por categoria, quantas lojas, ofertas e preços vieram e quantos foram descartados, e por quê.
- A IA recebe os itens da lista numerados e responde `"item": 1`; o add-on também aceita o nome exato ou parecido. Preço sem link é aceito (`fonte: null`); oferta sem preço "de" vira `tipo: "preco"` (ou `"encarte"`). Preço de loja pode ter `obs` com o produto achado: `{"preco": 32.9, "obs": "Finish 1 kg"}`.
- `ofertas[].id` precisa ser estável entre semanas: é o que o botão "Não mostrar" guarda.
- `redes[].id` é único entre todas as categorias.
- `lista[].produto` usa o mesmo texto da lista do `config.json`.
- `lista[].base` é o tamanho a que `precos` se refere, em `L`, `kg`, `un` (com `rotulo`, como `"rolo"`) ou `m`. `tamanhos` traz as outras embalagens, com a quantidade total na mesma unidade e o preço do pacote inteiro (online, com `frete` e `prazo_dias`). Ofertas podem ter `tamanho: {quantidade, unidade}` para mostrar o preço por litro ou quilo.
- Se duas categorias usarem bases diferentes para o mesmo item, os preços da segunda viram `tamanhos`.
- Encarte do site: para cada loja em `lojas.adicionar` com `site` (e até `OFERTAS_AUTO_ENCARTES`=2 lojas achadas pela busca com `site` e sem preço), o add-on baixa a página, pega as imagens grandes e PDFs (no Wix pede a versão de 1600 px; no `srcset`, separa só na vírgula com espaço ou depois de "1x"/"480w", porque o endereço do Wix tem vírgulas) e manda para a IA de fotos. Ofertas de encarte têm `encarte: true`, `valido_ate` e podem vir sem `preco_normal` (`tipo: "encarte"`). Lojas ganham `site`, `encarte_auto` ou `site_sem_encarte`.
- Loja com preço de clube: `precos[rede] = {"preco": 18.49, "clube": 16.99}`. O painel e a exportação usam `clube` só para as redes em `config.clubes`.
- `config.ia.busca` pode ser uma tarefa de IA (`ai_task.*`, chamada com `ai_task.generate_data`) ou um assistente de conversa (`conversation.*`, chamado com `conversation.process`); a leitura de fotos sempre usa tarefa de IA (`config.ia.fotos`).
- Categoria `online`: ofertas têm também `frete`, `prazo_dias`, `vendedor`, `oficial`, `importado` e `unidades`; na `lista`, o preço de um marketplace é um objeto `{"preco", "frete", "prazo_dias", "obs"}`. O painel compara `preco + frete` com o preço das lojas.
- `config.online`: `{"marketplaces": ["mercadolivre", "amazon"], "assinaturas": ["prime", "melimais"]}`.

### Etiquetas (`tags`) usadas pelo perfil

| Etiqueta | Efeito |
| --- | --- |
| `bebe` | Escondida se o perfil não tem crianças nem bebês. |
| `pet`, `gato`, `cachorro` | Escondida sem pets (`perfil.pets` com zero em tudo), ou se o animal não é o da casa. |
| `lactose`, `gluten`, `carnes`, `acucar` | Escondida pelas restrições (`vegetariano` usa `carnes`). |
| `alcool`, `medicamento`, `maquiagem`, `geriatrico` | Podem ir para "Nunca mostrar". |
| `skincare`, `cafe`, `bucal`, `suplementos`, `limpeza`, `carnes` | Interesses: sobem na lista. |

## Página de ofertas do site (sem IA)

Para lojas sem busca direta e sem sitemap, `testa_preco_loja` lê a página do site (a de `lojas.adicionar` com o mesmo nome vale mais que a do mapa; sem caminho, a inicial) com `ofertas_do_site`: `le_pagina_ofertas` respeita o `robots.txt` (`robots_permite` com o caminho), guarda o resultado em `paginas_ofertas.json` por 12 horas e devolve até 3 links do mesmo site com "oferta" ou "promo" no caminho; o primeiro também é lido se a página trouxe menos de 60 produtos. `ofertas_da_pagina` tenta, nesta ordem: `Product` do schema.org (também dentro de `ItemList`/`@graph`, sem os fora de estoque, via `produto_ld`); dados em `<script>` (`NOME_JSON` + `PRECO_JSON` vizinhos, na ordem em que aparecem; `sellingPrice`/`bestPrice` inteiros em centavos); e o texto (`blocos_da_pagina` junta "R$" + "159" + ",90" e marca `<del>/<s>` como riscado; `ofertas_texto` fecha um cartão a cada nome de produto novo, descarta parcelas e frete, e o riscado ou "De R$" vira `preco_normal`). Achou: `como: "ofertas_site"`, com `url` e `nome`. Na busca, `busca_paginas_ofertas` (até 8 lojas, logo depois das páginas de produto) passa as ofertas por `precos_por_oferta` e devolve a categoria com `_via: "site"` e até 20 ofertas.

## Escolha, economia e preço antigo

- **Escolha:** `lista[i].escolha = {rede, q, obs}`, com `q` nulo para o tamanho de sempre. `botaoEscolher` vai nos chips das lojas e nas linhas de `melhorTamanho`; `ehEscolha` compara loja, quantidade (`igualQ`) e nome. `escolhaDe(it, p)` acha a opção na busca atual (`precosDe` ou `opcoesTamanho`). `caixaEscolha` mostra "Sua escolha", a mais barata e o Desfazer. `itensDoRoteiro` troca o `p` do item pela escolha.
- **Economia do item:** `p[1].v - p[0].v`, ou `best.v - dc.porBase` com o tamanho que compensa. `oportunidades` soma a mesma diferença.
- **Preço antigo:** a busca pelo site (`_via: "site"`) devolve na categoria `_buscados` (itens) e `_redes_buscadas`. `mesclar_resultado` tira do resultado anterior o preço, o link, o visto e os tamanhos dessas lojas para esses itens antes de juntar o novo. `juntar_focada` apaga os dois campos antes de gravar.
- **Abas da Lojas:** `ui.lojasAba` (no navegador). Com `TERMO_LOJA`, todas as categorias aparecem.

## Histórico da lista

`config.historico` (até 300): `{produto, compras, saiu}`. `vaiProHistorico` recebe o que sai da lista (remover, Limpar lista) e junta as compras se o item já estava lá; com mais de 300, ficam os mais comprados e os que saíram por último. `entraNaLista(nome)` é usado pelo Adicionar, pelos itens das fotos e pelo toque no histórico: tira do histórico e devolve as compras. O Desfazer do Limpar tira do histórico o que voltou. `pintaHist` ordena pelos mais comprados (depois a última compra e a saída), esconde o que já está na lista e filtra pelo que está escrito em `#novoItem`; o número no botão é o total.

## Categoria da loja nos preços sem IA

`lojas_perto_cat(cfg)` dá `{nome normalizado: categoria}` de todas as lojas físicas do raio (sem o limite de 20 de `lojas_perto`, que é só para o texto da IA) e das cadastradas pelo morador. `categoria_da_loja(nome, perto)` usa esse mapa (também por `mesma_loja`) e devolve "online" para quem não está nele. `busca_catalogos`, `busca_sites` (marketplace é sempre online) e `busca_direta` (só as VTEX achadas; Giassi e Angeloni continuam fixos) usam isso no lugar da categoria guardada em `lojas_site.json`. Na troca do preço antigo, `mesclar_resultado` também tira o id da mesma loja nas outras categorias (`merc-`, `farm-`, `pets-`, `onli-` + o mesmo slug).

## Loja sem localização

Na página, `semLocal(l)` (sem `distancia_km` e sem `mapaUrl`) tira a loja da aba física em `pintaLojas` (`grupo(c, 'local')`). Na aba Online (e na procura pelo nome), as lojas físicas sem localização aparecem em `grupo(c, 'semLocal')`, "<Categoria> sem localização", junto com as cadastradas que ainda não têm dados. No servidor, `lojas_perto_cat` só conta loja com distância dentro do raio (a cadastrada sem localização não entra), então `categoria_da_loja` a manda para online. `localiza_sem_local(cfg)`, chamado no Encontrar lojas, pergunta ao Google Text Search por "nome cidade" (viés de 20 km na Casa, até 10 consultas), fica com a mais perto de nome parecido (`mesma_loja`) e grava `distancia_km`, `lat`, `lon`, `endereco` e `place_id` na loja; o resultado fica em `locais.json` por 30 dias.

## Atacarejos no mapa

`GOOGLE_BUSCA["mercados"]` inclui "atacadista". Em `google_varredura`, lugar sem tipo de mercado (`GOOGLE_TIPOS`) ainda entra se o nome bater com `ATACAREJO` (atacad…, atacarejo, Assaí, Makro, Komprão), não bater com `ATACADO_FORA` (pisos, embalagens, construção, roupas, bebidas…) e tiver um tipo de `TIPOS_ATACADO` (wholesaler, warehouse_store, food_store, discount_store). Loja de site com preço que não está entre as lojas perto (`lojas_perto`) continua indo para Online como mercado que entrega.

## Peso e volume na VTEX

Em `busca_vtex`, item com `measurementUnit` de peso ou volume (kg, g, L, ml) e `unitMultiplier` diferente de 1: `Price` e `ListPrice` são por unidade de medida; o preço da embalagem é `Price × unitMultiplier` e o tamanho é o `unitMultiplier` nessa unidade. Com multiplicador 1 e sem tamanho no nome, o tamanho é 1 kg (ou 1 L).

## Casamento do item com o produto

`PACOTE_NOME` ("com 12", "c/ 6", "cx com 4") não conta "com 10%", "por cento", "off", "reais" nem "de desconto" como pacote.

Padrão de nome do varejo: tipo + marca + variante + tamanho. `casa_lista(item, textos)` casa o item com os produtos de uma busca de uma vez; `combina(item, produto)` é o mesmo para um produto só, sem tradução.

- **Tipo:** a primeira palavra do item (`palavras_busca`, sem tamanho e sem palavras vazias) tem de ser o tipo do produto (`cabeca_bate`): estar entre as 3 primeiras palavras do nome, sem números, sem outra palavra de tipo antes (`eh_tipo`: abre o nome em pelo menos 5 produtos e em metade das vezes que aparece, pelas contas de `stats_vocab`). Se o tipo do item não for palavra de tipo (item que começa pela marca, "Churu atum"), basta estar nas 4 primeiras. `palavra_bate`: igual ou prefixo de 4+ letras.
- **Outras palavras:** todas (até 3) ou 75% (mais de 3). Cada uma vale se estiver no texto, se for do vocabulário inicial (`EQUIVALENTES` → `FRAGRANCIAS`) ou, só quando nenhum produto do mesmo tipo na busca usa a palavra (`traduz`) e ela não é marca, se o texto tiver uma das `associadas(palavra)`.
- **`associadas(w)`:** palavras que, nos nomes de produto vistos (`vocabulario.json`: até 80.000 nomes sem tamanho, mais as marcas da VTEX), aparecem junto de w (ou da raiz, "perfumad") pelo menos 3 vezes, com lift ≥ 4, df ≤ 5% e sem ser marca, tipo (primeira palavra em mais de 30% das vezes) ou palavra de menos de 4 letras. As associações ficam em memória e são refeitas quando o vocabulário muda (`grava_vocab`, no fim de cada busca e teste).
- **Mais regras do tipo:** em `cabeca_bate`, mesmo quando o tipo do item não é palavra de tipo, produto cuja primeira palavra é um tipo que o item não cita (e o item não começa por marca) fica de fora. Com 4 palavras ou mais, `pi[1]` (a palavra logo depois do tipo) não pode faltar. A associação só conta com palavras do produto que não estão no item.
- **Parecido:** com 3 palavras ou mais, se nenhum produto casa inteiro, `casa_lista` devolve "parecido" (valor verdadeiro) para o produto a que só falta uma palavra que está em `traduz` (nenhum produto do mesmo tipo usa) e não está em `RESTRICOES`. Havendo algum casamento inteiro, os parecidos viram `False`. `combina` (um produto só, sem tradução) nunca dá parecido, então o parecido não guarda EAN.
- **De onde vem o vocabulário:** `aprende_nomes` é chamado com os produtos da busca VTEX (nome e marca), os resultados da busca do site e até 40.000 endereços de cada catálogo (sitemap).
- **Busca de novo:** `termo_nucleo` (tipo + marcas do item, com o acento que a pessoa escreveu) refaz a busca quando o item inteiro não casa nada, em `busca_vtex` (40 resultados) e `busca_do_site`. `procura_catalogo` filtra antes os endereços com o tipo.
- **EAN:** `busca_vtex` devolve `ean`. O candidato que casa firme (`combina`, sem tradução) guarda o EAN em `casados.json` (`guarda_casados`, até 20 por item). Em qualquer loja VTEX, produto com um desses EANs entra como candidato mesmo com outro nome.

## Seção da loja

`busca_vtex` devolve `secao` (o caminho mais fundo de `categories`, normalizado: "acougue/aves") e `secao_nome` (o último nível, como a loja escreve). `mesma_secao(a, b)`: igual, ou uma dentro da outra.

- **`filtra_secao(item, loja, cand, eans)`**, na busca direta, depois do casamento:
  1. Entre os casados firmes (`combina`), se algum está numa seção afim do item (`secao_afim`: o começo de uma palavra do item, `w[:max(4, len-2)]`, abre uma palavra da seção, para "bovina" × "Bovinos"), saem os firmes de seções que não são afins nem aprendidas (menos o EAN conhecido).
  2. As seções dos firmes que ficaram, mais as aprendidas daquela loja (`casados.json` › `secoes[loja]`, até 4), filtram os outros candidatos (parecido, associação). Candidato sem seção passa.
- **`guarda_casados(item, eans, loja, secoes)`** guarda o EAN e a seção só dos firmes que sobraram.

## Similares

O item com `similares: true` (na lista da config) ganha, na busca direta, `similares_vtex`:

1. A seção mais comum entre os candidatos que casaram, com pelo menos 2 níveis, e a unidade mais comum.
2. A busca por facetas da VTEX (`product_search/category-1/<slug>/category-2/<slug>`, slug como o da loja: minúsculas, sem acento, hífens). Se nenhum produto vier daquela seção, busca pelo nome dela (`secao_nome`).
3. Ficam os produtos da seção (ou de dentro dela), na mesma unidade, que não são candidatos e saem pelo menos 2% mais baratos por unidade que o melhor candidato. Os 3 mais baratos por unidade.

`montar_item(…, similares={rede: [produtos]})` põe `similares` na entrada: rede, nome, preço, quantidade, unidade, fonte. O campo passa por `normalizar` (rede vira id), `juntar_item` (soma), `mesclar_resultado` (guarda os de antes e tira os da loja que acabou de ser consultada) e `item_ofertas` (um por loja e nome, o mais recente; os 6 mais baratos por unidade).

Página: o botão `data-sim` liga `estado.lista[i].similares`. `blocoSimilares` mostra até 3 mais baratos por unidade que o melhor preço do item (na mesma unidade da base). A escolha de um similar é `{rede, q, obs: nome, sim: true}`; `ehEscolha` ignora essas escolhas, e `escolhaDe` resolve o similar por loja e nome (`ehSim`).

## "ou" no item

`alternativas(item)` divide em " ou ". `casa_lista` casa com cada lado e junta (True > parecido > False); `combina` herda. A busca direta e a busca do site buscam cada lado (`unicos` tira os repetidos pelo link). `procura_catalogo` aceita o tipo de qualquer lado. "ou" entrou em `VAZIAS_BUSCA`.

## Correção de digitação

`corrige_palavra(w)`, no jeito do SymSpell:

- **Quando corrige:** com 150 nomes ou mais no vocabulário, palavra de 4 letras ou mais, só letras, que nenhum nome visto usa (`df`) e que não é marca.
- **Índice:** cada palavra com `df ≥ 2` e cada versão dela sem uma letra (`_apagas1`), refeito quando o vocabulário muda (`corr_de` é o `stats`).
- **Escolha:** os candidatos são os que dividem alguma versão sem uma letra com a palavra digitada. Vale a de menor distância Damerau-Levenshtein (`_distancia`, até 1 com até 5 letras, até 2 acima), desempatando pela mais usada.

`corrige_texto(t)` corrige cada palavra (menos `VAZIAS_BUSCA` e unidades) e escreve com o acento das lojas (`vocab()["formas"]`, aprendido em `aprende_nomes` e guardado em `vocabulario.json`) e com a maiúscula de quem escreveu.

Onde é usado:

- `GET /api/corrigir?texto=`: o "Quis dizer…?" da página ao adicionar.
- `relatorio.sugestoes`: os itens sem preço, em `mesclar_resultado` e na busca completa.
- `busca_direta` e `busca_sites`: tentam o nome corrigido quando o escrito não casa nada.

## Quantidade e listas prontas

- **Quantidade**: `lista[].qtd` (2 a 99; sem o campo, 1). `qtdDe(it)` na página; `vezesDe(it, es)` dá 1 quando a escolha é uma embalagem ou um similar. Multiplica o preço do cartão, a economia, o cupom (`oportunidades`), o roteiro (`itensDoRoteiro` põe `n` em cada item; `avaliaPlano`, `economiaPlano`) e a duração no melhor tamanho (`dura(Q) = Q / (q0 × N) × ritmo`). No servidor, `qtd_item`; vai como `quantidade` no `dados_lista` (Exportar, Conversa, CorrerIA) e volta no Importar (coluna Quantidade).
- **Listas prontas** (`opcoes.listas`, desligado de começo): `listas: [{id, nome}]` (até 20), `lista[].listas: [id]` e `roteiro.listas: [id]` (vazio: todas; 1.23.0: uma só, Todas, uma lista ou Nenhuma, no `.seg` `#rotListas`), no config.json. A lista aberta é do aparelho (`ui.listaAtual`). `naListaAtual(it)` filtra a Minha lista e o cupom (`oportunidades`, e `calculaRoteiro(true)` para o roteiro do cupom); o Roteiro usa `roteiro.listas`. `entraNaLista` põe o item novo na lista aberta. Apagar uma lista tira o id dos itens e do roteiro.
- **Nenhuma** (1.17.0): com as listas ligadas não há "Todas". `ui.listaAtual = ''` é Nenhuma, os itens sem `listas`; `naLista(it, id)` vale para os dois (`''` ou `NENHUMA` = sem lista). No roteiro, `roteiro.listas` aceita `NENHUMA` (`'_nenhuma'`, que nunca é o id de uma lista: os ids têm o sufixo `-xxxx`); vazio = todas (as listas e Nenhuma), e o toque nunca deixa vazio. O Limpar lista, em Nenhuma, tira só os itens dela.
- **Mover itens** (1.17.0): `LISTA_ED = {mover: de, alvo, sel}` e `pintaMover`; os destinos são as outras listas e, de uma lista, Nenhuma (`alvosMover`). Mover tira o id `de` do item e põe o `alvo` (Nenhuma: só tira).

## Compra rápida (1.16.0)

- **Na página:** o Roteiro tem dois modos (`#rotModo`, `ui.rotModo`: `roteiro` ou `rapida`); `pintaRoteiro` mostra `#rotPlano` ou `#rapida` e chama `pintaRapida`. Os itens ficam no aparelho (`ui.rapida: [{nome}]`, até 10), fora do config.json; o nome igual a um da lista (sem acento e sem caixa) vira o da lista. As sugestões (`SUG_FONTES.rapida`): os da lista (primeiro os com preço numa loja física), o histórico e os nomes do servidor, sem os que já estão na compra.
- **A conta (`calculaRapida`):** os preços de cada item são os de `precosDe` sem os online (`precosFisicos`: nem `online`, nem loja da categoria Online). Cada loja soma os itens que tem. Vence a que tem mais itens; entre as que têm o mesmo tanto, a mais perto (`distLoja`), a não ser que a mais barata saia pelo menos `max(R$ 5, 10%)` a menos (a nota diz quanto). O Compare mostra até 4 lojas; os itens sem preço em loja nenhuma não contam como faltando. Como chegar é `linkLoja` (só o destino: o Maps parte de onde a pessoa está).
- **Buscar preços:** `buscarRapida` manda `{itens, rapida: true}` para `/api/buscar-itens` (os sem preço, ou todos no Buscar de novo; até 8). No servidor, `buscar_itens(itens, rapida=True)` tira a categoria `online` (sem ela: erro dizendo para ligar uma categoria física); o resultado entra no `ofertas.json` como qualquer item, e a lista não muda.
- **Preço online sem Online:** `categoria_do_preco` devolve `None` para um preço online (categoria `online`, `frete` ou marketplace) quando a categoria Online não está na busca; antes ia para a primeira categoria física.

## Sugestões ao digitar

`sugestoes_nomes(q, limite=8)` (rota `GET /api/sugestoes?q=`) tira do vocabulário os nomes genéricos que começam pelo texto:

- **Índice:** os nomes pela primeira palavra (`_por_primeira`), refeito quando o vocabulário muda (`prim_de` é o `stats`).
- **Completa e estende:** a última palavra digitada pode estar pela metade ("sab" → sabonete, sabao); o nome ganha uma palavra, passando pelas de ligação (`LIGA_SUG`: "sabao em" → "sabao em po").
- **Corta:** na marca (`vocab()["marcas"]`; desde a 1.12.0 também as de 2 e 3 palavras, "tio zeca"), na embalagem (`EMBALAGEM_SUG`) e em palavra de uma letra; completar a palavra digitada com uma marca, não.
- **Ordem:** pelo número de nomes vistos, no mínimo 2 (um nome visto uma vez pode ser estranho); o empate, em ordem alfabética.
- **Escrita:** com o acento das lojas (`formas`, ou `CURTAS_SUG` para as palavras de menos de 4 letras: pó, chá, pão) e a primeira letra maiúscula.

Na página, `SUG_FONTES.itens` junta o histórico (`ordemHist`, sem o que já está na lista; com o Histórico aberto, só as das lojas) e as do servidor, guardadas por texto (`SUG_NOMES`, até 60): enquanto a resposta não vem, valem as do começo do texto. O pedido espera 180 ms sem digitar e só sai do que a pessoa digitou (`isTrusted`). A lista entra depois da linha do campo (`.row-form`) e rola até aparecer inteira acima da barra de baixo.

## Código de barras

- **Leitura na página:** `lerCodigoFoto` usa o `BarcodeDetector` do navegador quando existe. Sem ele, `decodificaEAN`:
  - **Linhas:** a foto em 1100, 640 e 2200 px no lado maior, com 16 linhas deitadas e 16 em pé (média de 3 pixels), nos dois sentidos.
  - **Barras:** limiar local (meio entre o mínimo e o máximo numa janela de 1/14 da linha), depois as larguras das corridas.
  - **Leitura:** em `eanCorridas`, guarda de 3 com zona clara antes, 6 dígitos L/G (a paridade dá o 1º dígito), guarda central de 5, 6 dígitos R, guarda final. O EAN-8 tem 4 dígitos de cada lado.
  - **Aceite:** o dígito é o padrão de menor distância nas larguras normalizadas para 7 módulos (até 1,6). O código vale com dígito verificador certo e com 2 linhas concordando, ou se for a única leitura.
- **Produto:** `GET /api/produto-por-codigo?ean=` (`produto_por_ean`) valida o dígito, transforma UPC-A em EAN-13 e recusa código de circulação restrita (13 dígitos começando com 2). Procura primeiro em `busca_vtex(loja, ean)` nas lojas diretas (fixas primeiro), aceitando só o produto com `ean` igual. Depois tenta o Open Food Facts (`OFERTAS_OFF`, `/api/v2/product/{ean}.json`, User-Agent do projeto). `na_lista` diz se o código já é de um item (`ean` na config ou `casados.json`).
- **Item:** o item da lista ganha `ean`, também no histórico. `eans_da_lista` guarda esse código em `casados.json` no começo da busca direta. Se a busca pelo nome não traz um produto com esse código, `busca_vtex(loja, ean, 5)` traz.

## Previsor de categorias do Mercado Livre

`GET /sites/MLB/domain_discovery/search?limit=3&q=` com `Authorization: Bearer`. O token vem do OAuth do app da pessoa:

- **Autorização:** `ML_AUTH` (`auth.mercadolivre.com.br/authorization?response_type=code&client_id&redirect_uri`).
- **Código:** a pessoa cola o endereço de volta. `ml_conectar` tira o `code=` e troca em `POST /oauth/token` (`authorization_code`).
- **Renovação:** `ml_token` renova com `refresh_token`, que o Mercado Livre troca a cada uso. Com `invalid_grant` ou `invalid_client`, apaga o acesso e pede para autorizar de novo.
- **Cache:** `ml_prever(titulo)` guarda `[{d, c, n}]` (domínio, categoria, nome) em `categorias_ml.json` por 90 dias, até 8.000 nomes. Grava junto com o vocabulário (`grava_ml` em `grava_vocab`).
- **Limites:** no máximo `ML_POR_HORA` (400) consultas novas por hora. Com 429, pausa de 10 minutos.

`confere_ml(item, nomes)`: o alvo são o domínio e a categoria das 3 previsões de cada lado do item. Cada produto vale True se a 1ª previsão dele está no alvo, False se não está, None sem resposta. `filtra_ml` (no começo de `montar_item`, então vale para todas as fontes sem IA) só tira os False quando há pelo menos um True, e nunca tira o EAN conhecido do item.

Rotas:

- `GET /api/integracoes` › `ml`: `app_id`, `tem_senha`, `url_retorno`, `conectado`, `autorizar`, `erro`.
- `PUT {"ml": {app_id, secret, url_retorno}}` (`null` apaga). Mudar a URL ou a chave pede nova autorização.
- `POST /api/integracoes/ml/conectar {"codigo"}`.
- `POST /api/integracoes/testar {"servico": "ml"}`: classifica uma carne moída e um hambúrguer.

## Clube em cada loja

A seção "Clubes e cupons do app" virou só "Cupons do app"; o clube fica na linha de cada loja física (`clubeHtml`). `clubeDe` decide o rótulo: o nome do clube conferido (`CLUBES`, por expressão no nome da rede) — preço de membro: Amigo Giassi, Club Nissei, Bem Panvel, Clube DC, Clube PP, Mais Saúde (Raia/Drogasil), Clube Mais (Fort); ofertas ativadas no app: Clube Bistek, Super Clube (Imperatriz), Clube K (Komprão/Koch), Meu Atacadão, Sempre Bem (Pague Menos), Amigo Cobasi, Clubz (Petz), `null` para clube só de pontos ou cartão (`SEM_CLUBE`, como o Clube Angeloni: sem botão, a não ser que já esteja marcado), "Tem clube" quando a busca com IA marcou a loja (`contas` da categoria ou "Clube" nas fontes) e "Adicionar clube" nas outras. O toque liga e desliga a rede em `config.clubes` (o mesmo campo de antes). Com a IA desligada e algum clube marcado, `#clubeSemIA` avisa que o preço de clube só chega pela IA. `instrucoes_para` diz à IA de quais lojas daquela categoria o morador é sócio, para ela trazer o `preco_clube`.

## Rede sem loja

`aplica_mapa` tira lojas que só vieram do mapa e são de outra categoria (pet shop nas farmácias) e lojas duplicadas, mas a rede fica em `redes`, às vezes com ofertas. Na página, `acompanha` de uma rede sem loja numa categoria física segue a loja de mesmo nome da categoria (`GEMEA`, por `chaveLoja`), ou fica de fora; assim a rede não aparece nos filtros nem nas ofertas da tela Ofertas. `dados_lista` faz o mesmo no servidor. O botão **Encontrar lojas** também está em Mais › Lojas (`encontrarLojas`, com a mensagem em `#lojasAcharMsg`).

## Teste das lojas online

`POST /api/lojas-mapa/testar-loja` aceita `categoria: "online"`. `rede` é o id da rede da última busca ou `mkt:{id}` para um marketplace escolhido que ainda não tem loja (`MARKETPLACES`). `sonda_loja` acha o marketplace pelo nome (`mkt_id`, também "Magazine Luiza" → `magalu`) e chama `testa_marketplace`: Shopee pela Open API de afiliados (`shopee_produtos("café 500 g")`, `como: "api"`), depois `testa_site` no domínio de `MKT_SITES` e `busca_do_site` com "café". Busca que funcionou vai para `lojas_site.json` com `marketplace: true` e entra em `busca_sites`; `busca_catalogos` pula marketplace (`marketplace` ou `e_marketplace`), porque o sitemap deles tem milhões de páginas. O resultado fica em `fontes_preco.json["online"]` pelo nome e também em `mkt:{id}`; `marca_fontes` copia os `mkt:` para `fontes_mkt` da categoria Online, que a página usa nas linhas de marketplace sem loja. Rede regional (mercado que entrega) usa `testa_preco_loja` com a categoria Online.

Na página, as linhas de marketplace têm a mesma forma das redes (caixa `data-mkt`, "Entrega no seu CEP", Site, App, `fonteHtml`/`fonteOnline` + `botaoTestar`); desmarcar mexe em `online.marketplaces` e a linha vai para Inativas. O campo **Procurar loja na lista** (`TERMO_LOJA`, pelo `norm` do nome, não fica guardado) filtra redes, marketplaces e lojas adicionadas, abre as Inativas e esconde as categorias sem resultado. O filtro **Só sem fonte de preço** (`ui.soSemFonte`, guardado no navegador) usa `semFonte`: teste `nenhum`, ou `ia` com a IA desligada, ou "Sem preços" (`semPrecos`); online sem teste conta como sem fonte quando a IA está desligada (menos a Shopee com a API). As lojas adicionadas à mão, ainda sem teste, somem com o filtro ligado.

## Meta tags de produto (Magazord)

`preco_da_pagina`, depois do JSON-LD, lê as meta tags com `meta_tag` (`property`, `name` ou `itemprop`, com `content` antes ou depois): `product:price:amount`, `product:sale_price:amount`, `og:price:amount` e `og:price`, e fica com o menor. `product:availability`/`og:availability` com "out of stock", "oos", "esgotado" ou "indisponível" marca sem estoque. Nome: `og:title`, senão `<h1>`; sem os dois, `preco_produto` usa o texto do endereço. No teste, quando o item de exemplo não está no sitemap, `parece_produto` ordena até 5.000 endereços (+3 para `/p`, +2 para tamanho como "50ml", +1 para quatro palavras ou mais, −5 para categoria, marca, institucional, busca) e testa os 4 primeiros. A Fique Bem (Magazord) monta vitrine, categorias e busca por JavaScript e proíbe `/busca` no robots.txt; a página de produto traz `og:price` e `product:price:amount` com o preço do PIX.

## Catálogos Ofertas

Terceiro item de `AGREGADORES` (`catalogosofertas`). Página da loja: `/lojas/{slug}/ofertas-catalogos`; os folhetos são os links `/vista/ofertas/{nome}-{id}` cujo nome contém o slug da loja (os "encartes parecidos" de outras redes ficam de fora), com a validade "30 out. até 10 nov." (`periodo_mes`). Na página do encarte, a validade também vem da descrição ("30-10-2026 … 10-11-2026", `PERIODO_TRACO`) e as páginas são as imagens `/assets/uploads/flyers/{id}/{tamanho}/{nome}-{página}-{n}-{hash}.webp` (`CO_IMG`), que a página só traz em `260x270WebP`. `paginas_grandes` troca a pasta de tamanho pelos candidatos de `CO_TAMANHOS`, baixa a primeira página de cada um e mede a largura pelo cabeçalho (`tamanho_imagem`: WebP VP8/VP8L/VP8X, PNG, JPEG); vale o maior com pelo menos 700 px. O resultado fica em `catalogos_tamanho.json` por 30 dias (sem nenhum: tenta de novo em 7 dias, e o folheto fica com `pequeno: true`, sem ir para a IA). `agreg_permite` lê o `robots.txt` do site e do servidor de imagens uma vez por dia (regras de `User-agent: *`) e não abre o que for proibido.

`achar_folhetos` pede as páginas com `pagina_resp` (cabeçalho `Accept` de navegador e um `CookieJar` em memória, para os cookies que o site manda nos redirecionamentos) e tenta os slugs do mais comprido para o mais curto (`droga-raia` antes de `droga`). Página com menos de 3 KB que só redireciona (`redireciona_para`: meta refresh ou `location` em JS, no mesmo site) é seguida uma vez; redirecionamento para um caminho sem o nome da loja (a página inicial, por exemplo) conta como "não tem a loja". `pede_robo` reconhece verificação de robô pelos cabeçalhos (`x-amzn-waf-action`, `cf-mitigated: challenge`), por marcas fortes em qualquer página (título "Just a moment", `cf_chl_opt`, DataDome, PerimeterX) e por marcas fracas só em páginas com menos de 20 KB (`challenge-platform`, `awswaf`, Imperva, captcha, cookie posto em JS), porque páginas normais atrás do Cloudflare também carregam o script de `challenge-platform`. O motivo no diagnóstico vem só da página com o nome inteiro; página com menos de 2 KB vira "veio vazia (código, bytes, servidor)" e o começo dela vai para o log. Na página do encarte, a mesma página em JPEG e WebP fica com a WebP.

## Portafolhetos e sinais de conteúdo

`portafolhetos` usa `tipo: "kimbino"`: mesma estrutura de páginas (`/{loja}/` e `/{loja}/{nome}-{data}-{id}/`) e imagens no thumbor do `leafletscdn.com` (`KIMBI_IMG` aceita `kimbicdn` e `leafletscdn`). Ordem: Kimbino, Seus Folhetos, Portafolhetos, Catálogos Ofertas. `agreg_permite` vale para todos: página da loja, página do folheto e primeira imagem (servidor de imagens). Uma linha `Content-Signal: … ai-input=no` no robots.txt bloqueia o site inteiro (o folheto iria para a IA); `ai-train=no` não muda nada.

## Instagram (Business Discovery)

`segredos.instagram = {token, ig_id, usuario}`. `testar_instagram` acha a conta profissional pela chave (`GET me/accounts?fields=instagram_business_account{id,username}`), guarda `ig_id` e testa `GET {ig_id}?fields=business_discovery.username(instagram){username,media_count}`; a validade vem de `debug_token` (`expires_at` 0 = não vence). Base `GRAPH` (`OFERTAS_GRAPH`, padrão `https://graph.facebook.com/v26.0`). Erros: 190 chave vencida; 4/17/32/613 limite; 110 ou subcódigo 2207013 conta não comercial; 10/200 permissões.

Lojas com Instagram (`lojas_instagram`): `lojas.adicionar` com site do Instagram ou `@usuario` (a página converte para URL) e lojas das categorias com `social` do Instagram (`insta_handle`), dentro da distância ou mantidas. `insta_posts` pede `business_discovery.username(x){media.limit(12){id,caption,media_type,media_url,permalink,timestamp,children{media_type,media_url}}}` e guarda 12 horas em `instagram.json › contas`. `posts_encarte`: imagem ou carrossel dos últimos `INSTA_DIAS` (8) com legenda de oferta (`LEGENDA_OFERTA`), até 3, até 6 imagens cada. `busca_instagram` (no fim de `busca_scripts`, pula lojas que já têm preço pelo site) usa o que já foi lido e, com IA e `ler`, lê até `MAX_INSTA_NOVOS` (3) posts novos por busca com `instrucoes_encarte` + a legenda; guarda em `instagram.json › lidos[id]` com `ate` (validade do encarte, ou 7 dias depois do post), `r` nulo quando não tinha ofertas ou já venceu. O resultado passa por `resultado_folheto` e a loja ganha `fontes: ["Instagram"]`, `instagram` (link do post) e `instagram_ate`.

Encarte vencido: `ler_encarte` recusa quando a validade lida já passou; `le_pagina_ofertas` descarta as ofertas quando o texto da página diz "válidas … dd/mm/aa" e todas as datas já passaram. `marca_fontes` troca `folheto_novo`/`instagram_novo` por `folheto`/`instagram` quando a busca já leu.

## Testar agora (uma loja)

`POST /api/lojas-mapa/testar-loja {"categoria", "rede"}` começa `sonda_loja` numa thread (409 se já houver teste rodando) e a página acompanha por `GET /api/lojas-mapa/teste` (o mesmo `SONDA` do Encontrar lojas, com `total: 1`). `testa_preco_loja(..., forcar=True)` testa o site de novo (menos as lojas fixas), lê a página de ofertas e o Instagram sem o cache de 12 horas e apaga a memória de "não tem" dos sites de encartes para essa loja; a lista de produtos do site (sitemap) continua com o cache de um dia. O resultado vai para `fontes_preco.json` e para o `ofertas.json` (`marca_fontes`).

## Lojas repetidas

`chave_loja` ignora o que vem depois de " - ", " – " ou " | " (filial, bairro ou cidade), a não ser que antes do traço só haja palavras genéricas. `mesmo_lugar`: até 150 m e `difflib.SequenceMatcher` ≥ 0,8 entre as chaves (erro de digitação). Vale na junção do mapa (OpenStreetMap + Google) e no `aplica_mapa`, que também renomeia a rede para o nome do Google quando o casamento foi por lugar e tira as lojas só do mapa repetidas (fica a de mais fontes). Na página, o Online esconde o mercado regional cuja chave existe numa categoria física.

## Busca do site

`busca_do_site(origem, info, termo)`: tenta os modelos de `BUSCAS_SITE` (`/pesquisa?terms={}`, `/busca?q={}`, `/search?q={}`…), só os permitidos por `robots_permite`, e lê o resultado com `ofertas_da_pagina`, ficando com os produtos que `combina` com o termo. O modelo que funcionou fica em `lojas_site.json › {origem}.busca`; sem nenhum, `sem_busca` (tenta de novo em 7 dias, ou no Testar agora). No teste de preço vem antes da lista de produtos (sitemap), que é pesada: `como: "busca_site"`. Na busca, `busca_sites` (até `MAX_SITES_BUSCA` lojas e `ITENS_BUSCA_SITE` itens, 0,4 s entre pedidos) monta os preços com `montar_item`; loja fora do raio vai para Online com frete no carrinho.

Agropecuárias: `OSM_TIPOS.petshops` inclui `shop=agrarian`; `GOOGLE_BUSCA.petshops` inclui "agropecuária" e aceita o lugar sem o tipo `pet_store` quando o nome tem "agro" ou "ração" (`AGRO`).

## Site das lojas pela IA

`sites_por_ia(cfg, lojas)`: as lojas acompanhadas sem site por nenhum caminho (`sem_site`: informado em `lojas.adicionar`, `site` do mapa ou `site_da_rede`) vão numa pergunta só para a IA de busca (`instrucoes_sites`, até 15), que devolve `{"lojas": [{"n", "site"}]}`. Só entra site de verdade (`site_loja`: sem rede social, WhatsApp, iFood…). Fica em `sites_ia.json` por 30 dias, por nome normalizado, também o `null`. O `sonda_lojas` (Encontrar lojas) e o `sonda_loja` (Testar agora) passam o site como `_site_ia` para `testa_preco_loja`, que guarda `site_url` no resultado; `marca_fontes` põe esse site na loja.

`preco_da_pagina` sem schema.org nem `product:price:amount`: pega o título (og:title, h1 ou title) e o produto de `ofertas_json_embutido` + `ofertas_texto` com `SequenceMatcher` ≥ 0,6 contra ele; página com "esgotado", "indisponível" ou "avise-me" não conta. No teste de preço, sem o item de exemplo nas páginas do sitemap, testa 3 outros produtos.

## Brave Search

`segredos.brave.key`. `brave_busca` chama `GET {OFERTAS_BRAVE}?q=&country=BR&search_lang=pt-br&count=10` com `X-Subscription-Token` (401/403/422 = chave recusada, 429 = limite). `site_pelo_brave(nome, cidade)` busca "nome cidade" e fica com o primeiro resultado que não está em `NAO_SITE` (redes sociais, guias, CNPJ, marketplaces, apps de entrega, sites de encartes, gov.br…), passa em `site_loja` e tem no endereço ou no título uma palavra do nome (`chave_loja`, 4 letras ou mais, sem palavras genéricas nem a cidade; nome só genérico não busca). `sites_por_ia` usa o Brave primeiro (até 15 lojas, 1,1 s entre buscas, `via: "brave"`) e a IA para as que ficaram sem site e ainda não passaram por ela (`via: "ia"`). `forcar` (Testar agora) ignora os 30 dias.

## Textos que dependem de uma opção ou integração

A tela só diz que algo vai acontecer quando a opção ou a integração que faz isso está ligada:

- **Ordem da busca** (fim de Mais › Lojas): além de `so-ia`/`so-semia` (Usar IA), as etapas têm `so-diretas` (site da loja,
  busca do site, páginas de produto, página de ofertas: `opcoes.lojas_diretas`), `so-folhetos` (folheto da semana,
  Instagram e folhetos já lidos: `opcoes.folhetos`, que `busca_folhetos` e `busca_instagram` conferem) e `so-itens`
  (`opcoes.itens_sem_preco`). `pintaEtapas` põe `sem-diretas`, `sem-folhetos` e `sem-itens` no `<html>`.
- **Similares e código de barras**: só a busca direta traz similares (`similares_vtex`) e usa o código do item
  (`eans_da_lista`). Com `lojas_diretas` desligada, `blocoSimilares` diz que ela está desligada (sem o Buscar agora) e o
  item posto pelo código não promete ser achado nas lojas.
- **Integrações**: `carregaShopee` guarda a resposta de `/api/integracoes` em `INTEG`, e `pintaIntegSt` (também ao mudar
  Usar IA) escreve o estado do Instagram e da Shopee. Instagram: "os encartes … entram na busca" só com IA e
  `opcoes.folhetos`. Shopee ligada: "os preços vêm direto da Shopee" só com a aba Online (`busca_shopee` só roda com
  `online` nas categorias); desligada: "entra pela busca com IA" só com IA, a aba Online e `shopee` em
  `online.marketplaces` (`mkts_online`).
- **Lista do Home Assistant**: `#syncDesc` só com `sync.ativo` (sem lista, `sincronizar_lista` não faz nada).
- **Compras online** (`#onlineSec`): só com `online` em `estado.categorias`.
- **Loja adicionada à mão**: com `usar_ia: false`, nem o encarte do site (`ler_encarte`) nem o nome (no pedido da IA)
  entram na busca; a linha diz só "Adicionada por você" e o Adicionar, "adicionada".
- **Como foi testado**: `passo_ia(cfg, barrado, de)` é o último passo quando só sobra a IA. `barrado` = o site barra programas (`bloqueio` ou `robots.txt` que proíbe): com IA, "✓ O preço desta loja vem da busca na web da IA, que pesquisa em seu nome"; sem barrar, "Preço só pela busca na web com IA."; sem IA, diz onde ligar. No bloqueio, o passo do site não promete "Tento de novo amanhã" (o teste repete no dia seguinte do mesmo jeito). Na página, o selo é **Preço pela busca da IA**, e sem IA aparece "Ligue a IA para ter o preço".
- `quem_le(cfg, o_que)` fecha o passo do folheto ou do post novo: sem IA, "precisa da IA"; com IA e
  Folhetos desligados, "Folhetos desligados em Mais › Configurações › Opções"; só com os dois, "a IA lê na próxima busca".
- **Avisar no celular**: fora da tela enquanto o aviso no celular não existe; `cotidiano.avisar` continua na config.

## Mais: o menu (1.3.0)

Como no GerencIA e no InventarIA, Mais é um menu (`#maisMenu`, `.menu-list` com um `.menu-row` por linha: o ícone no
`.h-ic`, o título e a linha em `.mb`, a seta `.chev`), e cada linha (`data-mais`) abre a sua tela: **Casa** (`#mp-casa`),
**Lojas** (`#mp-lojas`), **Configurações** (as abas `#maisAbas`: `#mp-integracoes`, `#mp-dados`, `#mp-aparencia` e
`#mp-opcoes`) e, por último, **Sobre** (`#sobreBtn`, `#mp-sobre`). Nada de função do app misturada com as configurações.

- **Estado**: `ui.maisTela` (`MAIS_IDS`: `casa`, `lojas`, `config`, `sobre`; `''` é o menu) e `ui.maisAba` (`CONFIG_ABAS`;
  `integracoes` de começo), guardados em `ofertas-bairro:ui`. Recarregar volta na mesma tela e aba.
- **`irPara(v, tela)`**: só com `v === 'mais'` e uma tela de `MAIS_IDS` abre a tela; sem ela, Mais abre no menu, e
  qualquer outro caminho (abas de baixo, barra lateral, arrastar, ‹ Mais) sai da tela. Põe no `<html>` `na-menu` (sem a
  linha da busca e o aviso de exemplo), `na-tela` (mostra o `#maisVolta`, ‹ Mais; no computador, o título desce uma
  linha) e `na-sobre` (também sem a linha e o aviso; sem o rodapé `#maisPe`, porque a versão está em Este app).
  `abaConfig(k)` troca a aba (setas do teclado também) e carrega o Uso da IA, a Shopee e as lojas diretas como antes.
  `abrirMais(tela, aba, alvo)` é o atalho de outras telas: Preencher o perfil e Buscar sem CEP (Casa), Ver lojas (Lojas),
  Importar lista (Configurações › Dados, no quadro Importar) e o "Ajuste no perfil" das ofertas.
- **Histórico**: `marcarTela` dá a cada tela uma entrada (`{tela}`, como no GerencIA; de uma tela para outra,
  `replaceState`). O Voltar do celular (`popstate`) volta para o menu ou, se um atalho abriu a tela (`TELA_DE`: a aba de
  baixo de onde veio), para essa aba. Saindo de outro jeito, a entrada é desfeita com `history.back()`. Arrastar para a
  direita numa tela volta para o menu; para a esquerda, não faz nada.
- **Da 1.2**: Mais era em abas (`maisAba` com `casa` e `lojas`). Sem `ui.menuMais`, quem estava em Mais abre na tela
  nova do mesmo lugar (Casa, Lojas ou Configurações na aba de antes) e `maisAba` vira `integracoes` se não for uma aba de
  Configurações. O endereço antigo `#lojas` abre Mais › Lojas.
- O ícone de Mais (barra de baixo e lateral) são os três pontinhos, como nos outros apps; a linha de Configurações usa
  o ícone dos controles deslizantes, como no GerencIA e no InventarIA.

## Dados, Aparência e Integrações na ordem da família (1.9.0)

- **Dados**: Exportar › Backup na pasta share › Importar › Versões anteriores › Onde ficam os dados › Começar do zero.
  `criar_backup` grava `SHARE/economia-AAAAMMDD-HHMMSS.zip` com `ARQ_BACKUP` (`config.json`, `ofertas.json`,
  `comparacoes.json`; sem `segredos.json` nem `correria.key`) e fica com os `MAX_BACKUPS` = 10 mais recentes
  (`GET /api/backups`, `POST /api/backup`); `restaurar_backup` guarda uma versão antes (`POST /api/backup/restaurar`).
  `zerar` (`POST /api/zerar`) guarda a versão `zerar` e deixa só `FICA_NO_ZERO` (IA, sensores, CorrerIA, opções, a
  sincronização e a cor), apagando também o `ofertas.json` e o `comparacoes.json`; a página volta ao exemplo. O
  Importar aceita a planilha do Exportar: `ler_planilha` (`POST /api/importar/planilha {"xlsx": base64}`) lê a coluna
  Produto e as Datas de compra (texto em linha ou compartilhado) e devolve `{lista}`, que segue pelo mesmo `importa`.
- **Aparência**: o tema (`ui.tema`, no aparelho) começa em `auto`. A cor do app é da casa: `config.json` `cor` e
  `cor_dia` (null até a casa ter uma; `corDaCasa()` adota a do aparelho na primeira vez; a cor vai por `POST /api/cor`, `gravar_cor`, que grava só esses dois campos, sem mexer no resto), e
  o aparelho guarda uma cópia em `ofertas-bairro:ui` só para o script do `<head>`. `CORES` é a paleta da família (12, na
  ordem do CronologIA); `corDaPaleta` troca os nomes de antes (`CORES_VELHAS`: amarelo › ouro, roxo › lilás, magenta ›
  rosa, cinza › grafite); `data-cor` vai sempre no `<html>` (o Verde também).
- **Integrações**: CorrerIA › IA do Home Assistant (com o Para falar) › Uso da IA › Shopee, Google, Brave, Mercado
  Livre, Instagram e a Lista do Home Assistant › Sensores.
- **Conversa**: no celular, `abreChat` põe uma entrada `{chat: true}` no histórico; o Voltar do celular (`popstate`)
  fecha só a Conversa; fechada de outro jeito, `fechaChat(depois)` desfaz a entrada e roda `depois` (o Abrir de uma
  tela) quando o histórico voltou.

## Nunca mostrar uma palavra (1.11.0)

`perfil.nunca_produtos` (até 100 palavras, como a pessoa escreveu): uma oferta com uma delas no começo de uma palavra do
nome (sem acento, maiúscula ou minúscula) fica escondida, em qualquer loja e tamanho. Na página, `termoNunca(o)` (em
`escondida`, motivo `tipo: 'termo'`, com **Mostrar de novo**), `palavraDe(produto)` (a sugestão: a primeira palavra com
três letras ou mais e sem números), o menu do Não mostrar (**Nunca “palavra”** abre `.termo-form` com o campo `#termoIn`)
e Mais › Casa › Nunca mostrar (`#pNuncaProd`, um toque tira; `#fNuncaProd` acrescenta). No servidor, `nunca_produto(cfg,
produto)`, a mesma regra, tira as ofertas da Conversa e das ferramentas do CorrerIA (`_ofertas_vivas`).

## Comparar só o mesmo produto (1.11.0)

`outro_produto(oferta, nome)`: em `comparar_precos`, o preço cujo `obs` (o nome do produto na loja) é outro produto fica de
fora. É outro quando o "N em 1" não bate (a oferta tem e o produto não, ou é outro número; `palavras_produto` junta o
"4 em 1" numa palavra) ou quando o nome tem 2 palavras ou mais que a oferta não tem e falta nele alguma palavra da
oferta (o "Creme de Barbear Nivea Men Sensitive" para o "Creme Nivea Men 4 em 1"). Palavras a mais sozinhas ("de Oliva",
"Rosto Barba Mãos") não bastam.

## Câmera do código de barras (1.11.0)

**Tirar foto** (`#codFoto`) abre `#codCamUI`, a câmera em tela cheia (`getUserMedia`, a de trás), com uma entrada no
histórico (`{cam: true}`, para o Voltar do celular); o X e o Esc fecham (`fechaCam`). Com o `BarcodeDetector` do navegador,
lê o vídeo a cada 300 ms e, achando um EAN válido, fecha e procura; o botão do meio tira a foto e vai pelo leitor próprio
(`leFotoCodigo`, o mesmo da foto escolhida). Sem `isSecureContext` ou sem câmera, explica (https ou o app do celular) e
abre a escolha da foto (`#codArq`, sem `capture`: no app do Home Assistant, o seletor com `capture` abria a galeria).
`tests/e2e/ec_camera.py` confere com a câmera de teste do Chromium.

## Uma altura só (1.11.0)

Botões (`.btn`, `.ghost.big`), campos (`input.field`, `select.field`), botões de escolha (`.seg`, as abas de
Configurações em `.mais-abas`, o Tema em `.seg.temas`, com o ícone ao lado) e as escolhas em botões (`.pick`) têm a altura
da família, 50 px (`--altura`, no fim do `<style>` do `painel.html`), a mesma dos outros apps. Ficam de fora os botões só
com ícone, os quadrinhos da IA (`.ler-tile`), os botões pequenos das linhas da lista (Comprei hoje, remover), os preços
das lojas, os interruptores e as cores. `tests/e2e/ec_alturas.py` confere na Minha lista, em Casa, Lojas e nas quatro abas
de Configurações, em 390, 320 e 1280 px.

## Cor do dia (1.4.0)

Como no InventarIA, no GerencIA, no ResolvIA e no CronologIA: em Mais › Configurações › Aparência, a chave `#corDia`
(`ui.corDia`, guardada no aparelho em `ofertas-bairro:ui`; ligada até ser `false`) troca a cor do app a cada dia.
`corDoDia()` pega uma de `CORES_DIA` (as `CORES` sem o Grafite, na ordem; 1.9.0: as 11 da família) pelo número do dia na data local
(`numeroDoDia`: `Date.UTC` do ano, mês e dia ÷ 86400000), a mesma o dia todo; amanhã, a seguinte. `corAtual()` é a do
dia ou, desligada, `ui.cor` (verde de começo), e é a etiqueta marcada em `#cores`. Escolher uma cor grava `ui.cor` e
`ui.corDia = false`. O script do `<head>` faz a mesma conta (com a lista das cores escrita nele) antes de pintar a tela.
Com o app aberto, `confereCorDoDia` (a cada minuto, no `focus` e ao voltar a ficar visível) troca a cor quando o dia muda.

## Mais › Sobre

A mesma página dos outros apps (o `about.js` do CronologIA), em JavaScript puro na fonte da página: `PRODUTOS` (nome,
repositório, ícone e a linha de cada app, na ordem), `IC_SOBRE` (ícones do Lucide escritos à mão), `marcaNome` (o "IA"
do nome num `<span>`, sem espaço) e `linkFora` (`target="_blank" rel="noopener"`) montam `#mp-sobre` uma vez. "Este app"
fica no `economia-ha`, com a versão lida do `#versaoTxt` (a do `config.yaml`, que o `tools/montar_pagina.py` põe no lugar do `'__VERSAO__'`). É a última linha
do menu de Mais e segue as regras das outras telas de Mais (acima).

## Comparar preço (1.5.0)

Uma oferta "−49%" numa loja pode ser mais cara que o preço normal de outra. **Comparar preço** (`data-act="comparar"`
em cada oferta) manda `POST api/comparar` com o `id` da oferta; o servidor acha a oferta no `ofertas.json`
(`acha_oferta`: 400 com `OFERTA_SUMIU` se ela saiu ou não tem preço) e roda `comparar_oferta` numa thread, com o mesmo
`BUSCA` do Buscar (uma busca de cada vez: `ja_rodando`; o botão Buscar gira e o `api/busca` mostra o andamento).

- O que procurar: `termo_da_oferta`, o nome sem o tamanho que vem depois do " · ". Onde: a oferta de uma loja do bairro
  procura nas lojas do mesmo tipo e no online; a do online, em todas as categorias ligadas.
- Como: `busca_scripts` com uma configuração só para a busca (`lista` = o termo, sem folhetos novos) e, se sobrarem
  menos de 2 preços e a IA estiver ligada, `busca_focada`. Nada vai para o `ofertas.json` nem para a lista (não usa o
  `mesclar_resultado`); o vocabulário aprendido é gravado como numa busca.
- `comparar_precos` junta as categorias (`juntar_categorias`) e devolve até 6 preços, um por loja, do mais barato para o
  mais caro. A loja da oferta fica de fora (pelo nome ou pelo id sem o prefixo da categoria). `equivale` é o preço no
  tamanho da oferta (`tamanho_da_oferta`: `unidade` do preço por quilo, `tamanho` ou o tamanho no nome): outro tamanho
  vale pelo preço por quilo, litro ou unidade e leva `quantidade`/`unidade`; medidas diferentes ficam de fora. Online
  conta o frete (`valor_total`); frete no carrinho vira `carrinho`.
- Guarda em `/data/comparacoes.json` (`{id: {em, produto, preco, precos}}`, as `MAX_COMPARACOES` = 60 mais recentes), que
  o `api/estado` devolve em `comparacoes`. `BUSCA.avisos` diz o resultado ("mais barato em Giassi.", "a oferta é o menor
  preço." ou "não achei em outras lojas", com o erro da IA se ela falhou).
- Na página: `COMP` (de `api/estado`), `comparando` (o id em andamento: o botão vira "Comparando…") e `blocoComparar`,
  que pinta `.cmp` embaixo da oferta com o veredito pelo preço atual da oferta (`precoDaOferta`, com frete): "Mais barato
  em outra loja" (ou "em N lojas", na cor das ofertas), "Menor preço entre N lojas" ou "Não achei em outras lojas", a data
  quando não é de hoje e as lojas como os chips da Minha lista (`.i-others`, a mais barata `.barato`, o link do produto).
  No fim, `recarrega(comp)` troca o "Ofertas atualizadas" pelo aviso do resultado. No exemplo, o botão só explica.
- As ações da oferta (Comparar preço e Não mostrar, ou Mostrar de novo) ficam em `.d-acts`, uma linha na largura toda.
