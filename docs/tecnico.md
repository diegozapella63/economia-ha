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
| GET | `/api/saude` | Verificação simples. |

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
