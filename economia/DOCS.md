# EconomIA

Cupons, ofertas e a sua lista de compras nas farmácias, mercados e pet shops perto de casa, numa página só dentro do Home Assistant.

## Antes de começar

O EconomIA usa a IA do próprio Home Assistant (Anthropic Claude, OpenAI, Google Gemini...). Escolha qual usar em **Mais › Integrações › IA do Home Assistant** e toque em **Verificar de novo** para testar. A chave **Usar IA**, no mesmo lugar, desliga tudo o que usa IA (Buscar, leitura de fotos e mensagens, cupons por print e Falar), para todos os aparelhos.

- **Para buscar ofertas**, a IA precisa de busca na web:
  - **Anthropic**: ligue a busca na web nas opções da tarefa de IA.
  - **Google Gemini**: a Pesquisa Google só funciona num **assistente de conversa**. Nas opções do Google Generative AI, crie ou ajuste um assistente com "Controlar o Home Assistant" em nenhum e **Enable Google Search tool** ligado, e escolha esse assistente.
- **Para ler fotos**, escolha uma tarefa de IA que aceite imagens (Google AI Task e Anthropic aceitam).

## Como usar

1. Abra **EconomIA** no menu lateral do Home Assistant.
2. Em **Mais › Casa**, preencha o CEP e a distância e toque em **Encontrar lojas** para registrar as lojas perto de casa pelo mapa. Preencha também quem mora na casa (incluindo quantos pets), restrições, interesses e os dias em que você costuma comprar.
3. Em **Minha lista**, adicione o que você compra sempre, pelo campo do topo, por **Escolher fotos**, por **Colar mensagem** ou por **Falar**. Toque em **Comprei hoje** quando comprar: o painel aprende de quanto em quanto tempo cada coisa acaba. **Limpar lista** apaga tudo, com opção de desfazer.
4. Toque em **Buscar**, no centro do menu de baixo. A busca leva alguns minutos e você pode continuar usando o painel.
5. Em **Ofertas**, use **Não mostrar** em qualquer oferta que não faça sentido para você. Cada oferta tem um link para a fonte.
6. Em **Mais › Lojas**, desmarque as que não quer acompanhar ou adicione uma que não apareceu.

## Mais, em abas

Como nos outros apps (InventarIA, GerencIA, ResolvIA e CronologIA), **Mais** tem abas presas no alto: **Casa** (CEP, quem mora, rotina, restrições, interesses e o que nunca mostrar), **Lojas** (lojas perto de casa, clubes e cupons do app e compras online), **Integrações** (IA do Home Assistant, Usar IA, Falar, Uso da IA, Lista do Home Assistant e Sensores no Home Assistant), **Dados** (Exportar, Importar, Versões anteriores e onde ficam os dados), **Aparência** (tema e cor do app) e **Opções** (as etapas extras da busca).

## Falar

O microfone fica no alto da tela, à direita (e em **Minha lista › Falar**). Fale os itens, por exemplo "leite integral, 2 pacotes de café 500 g e detergente"; o Home Assistant transcreve com a fala para texto do assistente de voz preferido (**Configurações › Assistentes de voz**; com o Home Assistant Cloud já vem pronta) e a IA separa os itens para você conferir e adicionar, com o que foi ouvido no alto. Até 2 minutos de cada vez.

Em **Mais › Integrações › IA do Home Assistant**, a linha **Falar** mostra se está pronto e com qual fala para texto. O microfone some com **Usar IA** desligado. No app do celular, permita o microfone para o app Home Assistant; no navegador, o Home Assistant precisa estar num endereço com https.

## No celular

Arraste para o lado para trocar de aba: Minha lista ⇄ Roteiro ⇄ Ofertas ⇄ Mais. Começando na borda da tela vale o Voltar do celular.

## No computador

Com a tela de 1000 pixels ou mais, as abas de baixo viram uma **barra lateral** com Minha lista (com o número de itens acabando), Roteiro, Ofertas, Mais, o botão **Buscar ofertas** e as ofertas por tipo de loja. No alto à direita ficam **Falar**, **Ler com IA** e **Adicionar item**. As seções ficam direto na página, com título grande e ícone, e o cupom de economia fica ao lado das oportunidades. No celular e no tablet nada muda.

## Itens por foto ou mensagem

Em **Minha lista → Escolher fotos**, tire ou escolha quantas fotos precisar, até 8 (print de conversa, lista escrita à mão, embalagem que acabou). Dá para tirar uma foto da lista. Quando terminar, toque em **Digitalizar com IA**: a IA do Home Assistant devolve os itens, você confere, ajusta o nome se quiser e adiciona. Se a lista veio em texto, use **Colar mensagem**.

Para ler fotos, a IA escolhida precisa aceitar imagens (a Anthropic aceita). A foto fica um instante na pasta de mídia do Home Assistant, só para a IA ler, e é apagada em seguida.

## Melhor tamanho

Pode escrever só o produto, como **Lysoform**. Na busca, o EconomIA traz também as outras embalagens (galão de 5 L, kits, fardos, leve 3 pague 2) e compara o **preço por litro, quilo ou unidade**:

- **Compensa o maior**: diz qual embalagem levar, onde, quanto economiza em relação a comprar a mesma quantidade no tamanho de sempre e quanto tempo dura no seu ritmo.
- **Tamanho de sempre**: o maior não compensa. Quando é o caso, mostra que, por exemplo, 5 de 1 L saem mais baratos que 1 de 5 L.
- **Compensa o menor**: uma embalagem menor sai mais barata por quilo ou litro (por exemplo, pote de 700 g contra o pacote de 1 kg).
- **Compensa, mas dura muito**: o maior é mais barato, mas duraria mais do que você costuma guardar. Ajuste em **Mais › Casa › Rotina de compras › Espaço para estoque**.

## Roteiro de compras

Na aba **Roteiro**, ao lado da Minha lista, diga em até quantas lojas você topa parar (1 a 4) e se é a lista toda ou só o que está acabando. O EconomIA testa as combinações de lojas e mostra:

- o total e a economia sobre o preço médio;
- o que comprar em cada parada, da loja mais perto para a mais longe, com link para a rota no Maps;
- o que compensa pedir online (pode desligar);
- quanto uma parada a mais economizaria. Se for pouco, ele recomenda menos paradas, e dá para comparar as opções com um toque.

## Clubes e cupons do app

Em **Mais › Lojas › Clubes e cupons do app**:

- Marque **Sou do clube** nas lojas em que você é cadastrado (quase sempre é só o CPF no caixa). O preço de clube dessas lojas passa a valer na lista, no roteiro e nas ofertas. Nas outras, o preço de clube aparece marcado e o EconomIA avisa quando valeria a pena entrar no clube.
- Em **Cupons do app**, escolha prints da carteira de cupons do app da loja (Bem Panvel, Raia, Meu Atacadão...) e toque em **Digitalizar com IA**. Confira a loja de cada cupom e guarde: eles aparecem em Ofertas como **Seu cupom** e na abertura quando estiverem perto de vencer.

O EconomIA não entra na sua conta das lojas: esses apps não têm acesso aberto e pedem código por SMS.

## Mercadinhos e encartes no site

A busca na web lê texto; muitos mercados do bairro publicam as ofertas como **imagem de encarte** no site. Por isso:

- A busca procura também mercadinhos e lojas independentes do raio. Se achar o site de uma loja sem nenhum preço, o EconomIA abre o site, baixa o encarte e a IA de fotos lê os preços (até 2 lojas por busca).
- Loja que continua sem preço aparece com o selo **Sem preços** em Mais › Lojas e um aviso nas Ofertas. Toque em **Adicionar site de ofertas** e cole o endereço da página do encarte (por exemplo `mercadosalles.com.br/ofertas`): a partir da próxima busca, o encarte é lido sempre.
- Também dá para informar o site ao **Adicionar loja**.
- Mercado sem site de ofertas (Koch, Komprão, Atacadão): nas Ofertas, toque em **Encarte ou print de preços**, escolha as fotos ou prints do encarte (até 8: do WhatsApp, do Tiendeo, do app da loja ou da gôndola), diga de qual loja é e toque em **Ler com IA**. Os preços valem até a próxima busca.

As ofertas de encarte aparecem com o rótulo "Encarte" e a validade, e os preços entram na comparação da lista e no roteiro.

## Primeiro o que não gasta IA

A busca começa pelo que não gasta IA e só chama a IA para o que faltar (o passo a passo também está no fim de Mais › Lojas):

1. **Lojas do raio, pelo mapa.** A localização da zona Casa do Home Assistant e o OpenStreetMap dizem quais farmácias, mercados e pet shops existem no raio, com endereço e distância certos (de rede, a filial mais perto). Com uma chave do Google Places em Mais › Integrações, entra também o Google Maps, que tem as lojas pequenas. Atualiza uma vez por semana.
2. **Site das lojas.** O site de cada mercado cadastrado ou achado na busca é testado uma vez por semana. Se a loja usa VTEX e o robots.txt permite, o preço vem direto da loja que atende o seu CEP (Giassi, Angeloni e outros). Se o site não deixa programas usarem a busca, mas libera as páginas de produto (como o Bistek), o EconomIA baixa uma vez por dia a lista de produtos que a loja publica, acha os itens da sua lista pelo nome e lê o preço na página de cada produto. Esse é o preço padrão do site, que pode variar de loja para loja. O EconomIA não dribla bloqueio de site.
3. **Shopee**, pela Open API do Shopee Afiliados, se você ligou em Mais › Integrações.
4. **Folheto da semana** das lojas que você acompanha e que não têm preço pelo site (veja abaixo).
5. **IA**: busca na web com a lista de lojas do mapa, para ofertas, cupons e os preços que faltam, avisada das lojas que já têm preço.

Com a IA desligada, o Buscar faz só os passos 2 a 4, com os folhetos já lidos.

## Folhetos de encarte

Toda loja que você acompanha e que não tem preço pelo site, como Komprão e Atacadão, tem o folheto da semana procurado sozinho no Kimbino e no Seus Folhetos, logo depois do site. Não precisa configurar nada (dá para desligar em Mais › Opções). Até 3 lojas com folheto novo por busca. A IA de fotos lê cada folheto uma vez, e as ofertas ficam guardadas até ele vencer. Os itens da sua lista que aparecem no folheto ganham preço, inclusive os que você adicionar depois, sem IA. Quando a loja tem vários folhetos regionais (o Atacadão tem um por região), a IA olha só a capa de cada um e escolhe os que valem para a sua cidade.

## Google Places (opcional)

O OpenStreetMap é gratuito, mas pode não ter as lojas pequenas do bairro. Em **Mais › Integrações › Google Places**, cole uma chave da Places API (New), criada em console.cloud.google.com › APIs e serviços. O Google pede cartão cadastrado e dá uma cota gratuita por mês; o EconomIA consulta uma vez por semana, três pedidos (farmácias, mercados e pet shops). A chave fica em `segredos.json`.

## Lojas inativas

Em **Mais › Lojas**, desmarque a loja que não quer acompanhar: ela vai para **Inativas**, um bloco fechado no fim de cada grupo, e sai das ofertas, do roteiro e da procura de folhetos.

## Shopee Afiliados

Em **Mais › Integrações › Shopee Afiliados**, informe o App ID e a senha (Secret) da Open API, que você pega em affiliate.shopee.com.br › Open API. Toque em **Salvar e testar**. A partir daí, os preços da Shopee vêm direto da Shopee, sem IA, com o link do produto. A Shopee não informa o frete antes do carrinho, então o preço aparece com "+ frete". As chaves ficam só no Home Assistant, em `segredos.json`, e a senha não aparece de novo no painel.

## Compras online

A aba **Online** compara iFood, Rappi, Mercado Livre, Amazon e outros que você marcar em **Mais › Lojas › Compras online**. Marque também as assinaturas que dão frete grátis (Amazon Prime, Meli+, Clube iFood).

- **iFood e Rappi**: trazem os preços dos mercados, farmácias e pet shops do bairro no app, com a taxa de entrega somada. O preço no app pode ser maior que no balcão. Com Clube iFood, a taxa fica zerada nas lojas participantes; os cupons pessoais do Clube entram pelo print, em Cupons do app.

- O preço considerado é o **preço mais o frete** para o seu CEP. Kits aparecem com o preço por unidade.
- Prime e Meli+ dão frete grátis só nos produtos elegíveis (na Amazon, os com selo Prime). O frete de cada item já vem com a assinatura considerada.
- Na Minha lista, cada item mostra se **compensa pedir** ou se é melhor **comprar na loja**. Se o pedido chegaria depois de o item acabar, o EconomIA sugere comprar na loja agora e diz até quando pedir da próxima vez.
- Só entram lojas oficiais ou vendedores bem avaliados. Importados ficam marcados, e remédios de receita ficam só nas farmácias.
- **Mercados da região que entregam** (ligado em Mais › Lojas › Compras online): mercados fora do raio que vendem pelo site ou app e entregam no seu CEP, como o Bistek, aparecem em Online, separados dos marketplaces. Quando a taxa só aparece no carrinho, o preço vem com "+ frete".
- **De quando é o preço**: o cartão mostra a hora dos preços. Preço da busca na web aparece marcado para você conferir no link: a Amazon, por exemplo, muda o preço várias vezes por dia, e o Google Shopping costuma estar atrasado.

## Lista por voz

Em **Mais › Integrações › Lista do Home Assistant**, escolha a lista de tarefas que o EconomIA deve acompanhar (por exemplo, a **Lista de compras**). A partir daí:

- O que você pedir ao Assist, como "adicione café na lista de compras", aparece na Minha lista em até um minuto.
- Marcar um item como concluído na lista do Home Assistant conta como **Comprei hoje** no EconomIA.
- O que você adicionar no EconomIA vai para a lista do Home Assistant, e os itens que estão acabando entram sozinhos (dá para desligar as duas coisas).

Também dá para usar uma lista do **Google Tasks** conectada ao Home Assistant pela integração Google Tasks. Ela é atualizada pelo Home Assistant a cada 30 minutos.

## Uso da IA e sensores

Em **Mais › Integrações › Uso da IA**: as chamadas de hoje, dos últimos 7 dias e do mês, o gráfico por dia, o tipo de uso (busca, itens sem preço, encartes, fotos, cupons, Falar e testes), erros e cota excedida, e as últimas chamadas. Para economizar a cota, desligue em **Mais › Opções** a busca extra dos itens sem preço e a leitura automática de encartes.

**Sensores no Home Assistant** vem desligado. Ligado, o app cria o `sensor.economia_ia_hoje`, com as chamadas de hoje e os detalhes nos atributos; desligado, apaga o sensor.

## Dados

Em **Mais › Dados** você exporta a lista para Excel ou JSON e as ofertas da última busca, importa uma lista e volta para uma das **Versões anteriores**: o app guarda uma cópia da lista, do perfil e dos ajustes a cada 10 minutos de uso e antes de importar, restaurar ou limpar a lista, e fica com as 3 mais recentes. Em **Mais › Aparência**, o tema (automático, claro ou escuro) e a **cor do app**, guardados em cada aparelho.

Tudo o que você preenche fica guardado só no Home Assistant e entra nos backups dele.
