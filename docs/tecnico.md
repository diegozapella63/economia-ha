# EconomIA: detalhes técnicos

Painel de cupons, ofertas e lista de compras de farmácias, mercados e pet shops perto de casa, aberto pelo menu lateral do Home Assistant (ingress).

Todos os dados ficam no Home Assistant, na pasta `/data` do add-on:

| Arquivo | Quem grava | Conteúdo |
| --- | --- | --- |
| `config.json` | o painel | CEP, distância, categorias, lojas, lista, perfil, rotina, ofertas escondidas |
| `ofertas.json` | a busca de ofertas | lojas, cupons, ofertas e preços da lista |

Sem `ofertas.json`, o painel mostra um exemplo embutido.

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
| POST | `/api/buscar` | Começa a busca agora, uma categoria por vez, pela ação `ai_task.generate_data` do HA. No fim, faz uma pergunta só sobre os itens que ficaram sem preço. |
| POST | `/api/buscar-itens` | `{itens: ["Pó lava louça"]}` (até 8 itens da lista): busca só esses itens e junta ao `ofertas.json` atual. |
| GET | `/api/busca` | Andamento: `{rodando, etapa, atual, total, erro, avisos, terminou_em}`. |
| GET | `/api/exportar/lista.xlsx` | Lista em Excel: loja mais barata, preços, economia e datas de compra. |
| GET | `/api/exportar/lista.json` | A mesma lista em JSON. |
| GET | `/api/todos` | Listas de tarefas (`todo.*`) do Home Assistant. |
| POST | `/api/sincronizar-lista` | Sincroniza agora com a lista escolhida em `config.sync`. |
| POST | `/api/ler-lista` | `{imagens: ["data:image/jpeg;base64,..."], texto}` (até 4 imagens, 16 MB no total). Devolve `{id}`. |
| GET | `/api/ler-lista?id=...` | `{status: "lendo|pronto|erro", itens: [{produto, quantidade, ja_na_lista}], erro}`. |
| GET | `/api/ias` | `{tarefas: [{id, nome, anexos}], agentes: [{id, nome}]}`: entidades `ai_task.*` e `conversation.*`. |
| POST | `/api/testar-ia` | `{uso: "busca"|"fotos"}` → `{ok, msg}`. A busca faz uma pergunta curta que exige busca na web. |
| GET | `/api/voz/status` | `{pronta, motor, idioma, nome}` ou `{pronta: false, motivo}`: a fala para texto do assistente de voz preferido. |
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

Candidatas: as lojas de `lojas.adicionar` com site, as lojas das categorias físicas do `ofertas.json` com `site` e os mercados regionais de Online (o site sai dos links dos preços). Cada origem é testada uma vez por semana (`testa_site`): lê o `robots.txt` (regras de `User-agent: *`, com `*` e `$`, a regra mais longa vale) e só chama `/api/checkout/pub/regions` se `/api/checkout/pub/regions` e `/api/io/_v/api/intelligent-search/product_search/` forem permitidos. Resposta em lista = VTEX → entra em `VTEX_ACHADAS` e na busca direta, na categoria da loja. Se o `robots.txt` não vem, o motivo fica em `erro` e o texto da exceção em `detalhe`: 401/403/429 = "recusou o acesso de programas"; `RemoteDisconnected`, conexão resetada ou abortada, `EOF occurred` e `IncompleteRead` = "fechou a conexão sem responder" (proteção contra robôs; o add-on não tenta contornar); timeout, SSL e DNS têm texto próprio; o resto mostra o detalhe.

Sites das lojas do mapa: `osm_lojas` guarda `website`/`contact:website`/`brand:website`; `google_lojas` pede `places.websiteUri`. Sem site, `site_da_rede` reconhece redes conhecidas pelo nome sem palavras genéricas nem a cidade (`SITES_REDES`), igual ou, para as redes de `SITES_COM_FILIAL`, seguido do nome da filial; o `testa_site` confirma. `POST /api/lojas-mapa/atualizar` também chama `atualiza_diretas(max_novas=15)` em segundo plano.

### Teste de preço das lojas (`fontes_preco.json`)

Depois do `POST /api/lojas-mapa/atualizar`, `sonda_lojas` roda em segundo plano: `atualiza_diretas(max_novas=30)` e, para cada loja acompanhada das categorias físicas, `testa_preco_loja` tenta um termo de exemplo (`TERMO_TESTE`): VTEX liberada → `regiao_direta` + `busca_vtex`; páginas liberadas → `baixa_catalogo` + `procura_catalogo` + `preco_produto`; senão folheto guardado ou `achar_folhetos` (até 8 lojas novas). Resultado `{como: site|paginas|folheto|folheto_novo|ia|nenhum, exemplo, site, passos: ["✓ …", "✗ …"], em}` por categoria e nome; `marca_fontes` põe em cada loja (`preco_fonte`) ao gravar o `ofertas.json`.

### Páginas de produto (`catalogos/`)

Para origens com `paginas: true` que não são VTEX liberada: `baixa_catalogo` lê os `Sitemap:` do robots.txt (ou `/sitemap.xml`), segue o índice priorizando os sitemaps de produto (aceita .gz) e guarda as URLs de produto (VTEX: terminam em `/p`) por 1 dia, respeitando o robots.txt. Para cada item, as até 3 URLs cujo texto tem as palavras do item (`combina`) são abertas, uma a cada 0,3 s, e o preço sai do JSON-LD `Product` → `offers` (`price`/`lowPrice`, sem `OutOfStock`) ou da meta `product:price:amount`, guardado por 1 dia. Loja fora do raio (não está em `lojas_perto` nem em `lojas.adicionar`) entra em `online` com `frete: null, carrinho: true`.

### Lojas do raio pelo mapa (`lojas_mapa.json`)

`casa()` lê `GET /api/states/zone.home` (latitude e longitude). `osm_lojas` faz um POST ao Overpass (`OFERTAS_OVERPASS`) com `amenity=pharmacy`, `shop=chemist`, `shop~supermarket|convenience|wholesale|greengrocer|butcher` e `shop=pet` em `around:{raio},{lat},{lon}`; com `segredos.google.key`, `google_lojas` chama `places:searchNearby` (Places API New, `rankPreference: DISTANCE`, 20 por tipo) e `google_varredura` chama `places:searchText` (`OFERTAS_GOOGLE_TEXTO`) com "farmácia", "drogaria", "supermercado", "mercado" e "pet shop", `locationRestriction` no quadrado do raio, `rankPreference: DISTANCE`, até 3 páginas (`nextPageToken`) enquanto vierem lojas dentro do raio; só entram lugares com os tipos de `GOOGLE_TIPOS`. Lojas sem site depois disso (as só do OpenStreetMap, fora das redes de `SITES_REDES`) ganham o site por `google_site` (Text Search pelo nome, `locationBias` de 500 m, mesmo nome e até 400 m); a resposta fica em `lojas_mapa.json` › `sites` por 30 dias. Nomes todos em maiúsculas passam por `nome_bonito` (também os já registrados, em `aplica_mapa`). `site_loja`/`social_loja` separam site de verdade de rede social, WhatsApp, Linktree e apps de entrega (`REDES_SOCIAIS`): esses ficam em `social` e não são testados como site. `da_categoria` tira de farmácias e mercados as lojas de outra categoria: pelo `primaryType` do Google (`OUTRA_CATEGORIA`: `pet_store`, `veterinary_care`; em mercados também `pharmacy`/`drugstore`) e pelo nome (`NOME_FORA`: pet, vet, veterinária, animal, agropecuária); vale no OpenStreetMap, no Nearby e na busca por texto, e `aplica_mapa` remove as lojas só do mapa (`fontes == ["Mapa"]`) que não passam. Distância em linha reta (haversine). Lojas da mesma rede (`chave_loja`: sem "farmácia", "drogaria", "supermercado"…) ficam uma só, a filial mais perto, até 30 por categoria; guardado por 7 dias por casa, raio, categorias e fonte. O pedido de cada categoria leva a lista (`mapa_txt`), e `aplica_mapa` põe endereço e distância do mapa nas lojas de todas as fontes e acrescenta as do mapa que faltaram (`fontes: ["Mapa"]`).

### Folhetos (`folhetos.json`)

Candidatas (`lojas_folheto`): as lojas físicas acompanhadas (fora de `lojas.ignorar`, no raio ou em `lojas.manter`), do `ofertas.json` anterior e, depois da IA, as recém-achadas, mais `lojas.adicionar` sem site, menos as que têm preço pelo site. Até 8 lojas novas procuradas por busca e até 3 com folheto novo lido pela IA. O nome vira começos de endereço sem palavras genéricas nem a cidade (`bases_loja`: "Komprão Koch Atacadista" → `komprao`, `komprao-koch`). `achar_folhetos` tenta `https://www.kimbino.com.br/{base}/` (e `-atacadista`, `-supermercados`, `supermercados-{base}`…) e `https://seusfolhetos.com.br/{base}-ofertas`; o endereço achado fica guardado por 14 dias (loja inexistente: 7 dias). Na página da loja, os links de folheto (Kimbino: `/{loja}/…-{id}/`; Seus Folhetos: `/{loja}-ofertas/folheto-{id}-0`) e o período ("29/10/2026 - 01/11/2026") entre um link e o próximo. Só entram os válidos hoje. Páginas do folheto: Kimbino, as imagens `kimbicdn.com/…/data/{pasta}/{página}.jpg` da pasta que mais aparece (prefere `/0x0/`); Seus Folhetos, as `/public/gimg/…/{id}-{w}-{h}.jpg` do tamanho comprido mais comum. Mais de 2 folhetos: a IA vê só as capas (até 8 por chamada) com a cidade do CEP (ViaCEP) e responde `sim|nao|nao_sei` (guardado em `_vale`). Até 2 folhetos por loja, até 12 páginas, 8 por chamada, com o pedido de `instrucoes_encarte`. A resposta fica em `itens[id].r` até `ate`, com os itens da lista guardados pelo nome. `precos_por_oferta` casa itens da lista com as ofertas do folheto sem IA.

### Shopee Afiliados

`POST https://open-api.affiliate.shopee.com.br/graphql`, corpo `{"query": "{productOfferV2(keyword: \"…\", sortType: 1, page: 1, limit: 20) {nodes {…}}}"}`, cabeçalho `Authorization: SHA256 Credential={AppId}, Timestamp={ts}, Signature={sha256_hex(AppId + ts + corpo + Secret)}`. Entram produtos com nota ≥ 4,5 cujo nome tem as palavras do item; preço `priceMin`, link `productLink` (não o de afiliado). Erros 10020/10030/10035 param as consultas seguintes. `OFERTAS_SHOPEE_API` troca o endereço nos testes.

### Preços online e de quando são

Preço online: `{preco, frete, prazo_dias, obs}`; `frete: null` com `carrinho: true` quando a loja só mostra no carrinho (a IA responde `"frete": "carrinho"`). Lojas de `online` que não são marketplace ganham `regional: true`. Cada item da lista tem `vistos: {rede: {em, via}}` com `via` = `site`, `api`, `encarte` ou `web`.

### Uso da IA

As ações `ai_task.generate_data` e `conversation.process` não devolvem tokens nem custo. O add-on conta cada chamada em `uso_ia.json` (por dia, até 120 dias): tipo (`busca`, `itens`, `encarte`, `fotos`, `cupons`, `teste`), entidade, resultado (`ok`, `cota`, `formato`, `erro`), segundos, imagens e tokens estimados (caracteres do pedido e da resposta ÷ 4).
Com `config.sensores` ligado (vem desligado), a cada chamada e na virada do dia publica `sensor.economia_ia_hoje` pela API de estados do HA: o estado é o número de chamadas de hoje (`state_class: total_increasing`) e os atributos trazem `erros`, `cota_excedida`, `tokens_texto_estimados`, `imagens`, `por_tipo`, `ultimos_7_dias`, `este_mes` e `ultima_chamada`. O sensor some se o HA reiniciar e volta no minuto seguinte. Desligado, o add-on apaga o sensor (`DELETE /api/states/...`) ao iniciar e quando a opção muda.
Com `config.usar_ia` em `false`, nenhuma chamada de IA sai: `/api/buscar`, `/api/ler-lista` e `/api/voz` respondem 400.

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
- Encarte do site: para cada loja em `lojas.adicionar` com `site` (e até `OFERTAS_AUTO_ENCARTES`=2 lojas achadas pela busca com `site` e sem preço), o add-on baixa a página, pega as imagens grandes e PDFs (no Wix pede a versão de 1600 px) e manda para a IA de fotos. Ofertas de encarte têm `encarte: true`, `valido_ate` e podem vir sem `preco_normal` (`tipo: "encarte"`). Lojas ganham `site`, `encarte_auto` ou `site_sem_encarte`.
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
