# EconomIA — add-on do Home Assistant

Painel de cupons, ofertas e lista de compras de farmácias, mercados e pet shops perto de casa, aberto pelo menu lateral do Home Assistant (ingress).

Todos os dados ficam no Home Assistant, na pasta `/data` do add-on:

| Arquivo | Quem grava | Conteúdo |
| --- | --- | --- |
| `config.json` | o painel | CEP, distância, categorias, lojas, lista, perfil, rotina, ofertas escondidas |
| `ofertas.json` | a busca de ofertas | lojas, cupons, ofertas e preços da lista |

Sem `ofertas.json`, o painel mostra um exemplo embutido.

## Busca de ofertas

O botão **Buscar** chama `ai_task.generate_data` pela API do Home Assistant (`homeassistant_api: true`), uma vez por categoria ativa. A resposta é validada antes de gravar: ofertas e cupons sem URL de fonte são descartados, preços precisam ser números e a oferta precisa ser menor que o preço normal. Se uma categoria falhar, fica o resultado anterior dela.

## Rotas (relativas ao ingress)

| Método | Rota | O que faz |
| --- | --- | --- |
| GET | `/` | Página do painel. |
| GET | `/api/estado` | `{config, ofertas, usuario}`. `usuario` vem do cabeçalho `X-Remote-User-Display-Name` do ingress. |
| PUT | `/api/config` | Grava `config.json`. |
| PUT | `/api/ofertas` | Grava `ofertas.json` (precisa ter `categorias`). |
| POST | `/api/buscar` | Começa a busca agora, uma categoria por vez, pela ação `ai_task.generate_data` do HA. |
| GET | `/api/busca` | Andamento: `{rodando, etapa, atual, total, erro, avisos, terminou_em}`. |
| GET | `/api/exportar/lista.xlsx` | Lista em Excel: loja mais barata, preços, economia e datas de compra. |
| GET | `/api/exportar/lista.json` | A mesma lista em JSON. |
| GET | `/api/todos` | Listas de tarefas (`todo.*`) do Home Assistant. |
| POST | `/api/sincronizar-lista` | Sincroniza agora com a lista escolhida em `config.sync`. |

### Sincronização com a lista do Home Assistant

A cada minuto (e quando o painel volta a ficar visível), o add-on lê a lista escolhida com `todo.get_items`:
item novo pendente entra na Minha lista (`origem: "ha"`); item que passa a concluído registra a compra do dia.
No outro sentido, usa `todo.add_item` para itens novos do painel e para os que devem acabar em até um dia.
`config.json` tem `rev`, que sobe a cada gravação; se o painel salvar com uma revisão antiga, o servidor junta as mudanças que vieram do HA antes de gravar.
| GET | `/api/saude` | Verificação simples. |

O servidor só aceita conexões do ingress (`172.30.32.2`). Para testar fora do HA:
`OFERTAS_ALLOW_ALL=1 OFERTAS_DATA=/tmp/ofertas python3 app/server.py`

## config.json

```json
{
  "cep": "89200-000",
  "raio_km": 2,
  "categorias": ["farmacias", "mercados", "petshops"],
  "lojas": {"ignorar": ["raia"], "manter": ["imperatriz"], "adicionar": [{"categoria": "mercados", "nome": "Mercado da esquina"}]},
  "lista": [{"produto": "Café torrado e moído · 500 g", "compras": ["2026-09-20", "2026-09-30"]}],
  "perfil": {"adultos": 2, "criancas": 0, "bebes": 0, "pets": {"cachorro": 0, "gato": 1, "outros": 0}, "restricoes": [], "interesses": ["skincare", "cafe"], "nunca": ["alcool"]},
  "cotidiano": {"mercado": ["sab"], "farmacia": ["qua"], "avisar": "vespera"},
  "ocultas": ["giassi-cerveja-12"]
}
```

## ofertas.json

```json
{
  "versao": 2,
  "gerado_em": "2026-10-19T07:52:00-03:00",
  "proxima_atualizacao": "2026-10-26T07:52:00-03:00",
  "lista": [{"produto": "Café torrado e moído · 500 g", "precos": {"giassi": 19.9, "angeloni": 17.98}}],
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

- `ofertas[].id` precisa ser estável entre semanas: é o que o botão "Não mostrar" guarda.
- `redes[].id` é único entre todas as categorias.
- `lista[].produto` usa o mesmo texto da lista do `config.json`.

### Etiquetas (`tags`) usadas pelo perfil

| Etiqueta | Efeito |
| --- | --- |
| `bebe` | Escondida se o perfil não tem crianças nem bebês. |
| `pet`, `gato`, `cachorro` | Escondida sem pets (`perfil.pets` com zero em tudo), ou se o animal não é o da casa. |
| `lactose`, `gluten`, `carnes`, `acucar` | Escondida pelas restrições (`vegetariano` usa `carnes`). |
| `alcool`, `medicamento`, `maquiagem`, `geriatrico` | Podem ir para "Nunca mostrar". |
| `skincare`, `cafe`, `bucal`, `suplementos`, `limpeza`, `carnes` | Interesses: sobem na lista. |
