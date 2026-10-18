# EconomIA

Cupons, ofertas e a sua lista de compras nas farmácias, mercados e pet shops perto de casa, numa página só dentro do Home Assistant.

## Antes de começar

O EconomIA usa a IA do próprio Home Assistant (Anthropic Claude, OpenAI, Google Gemini...). Escolha qual usar em **Mais → Dados e ajustes → IA do Home Assistant** e toque em **Verificar de novo** para testar.

- **Para buscar ofertas**, a IA precisa de busca na web:
  - **Anthropic**: ligue a busca na web nas opções da tarefa de IA.
  - **Google Gemini**: a Pesquisa Google só funciona num **assistente de conversa**. Nas opções do Google Generative AI, crie ou ajuste um assistente com "Controlar o Home Assistant" em nenhum e **Enable Google Search tool** ligado, e escolha esse assistente.
- **Para ler fotos**, escolha uma tarefa de IA que aceite imagens (Google AI Task e Anthropic aceitam).

## Como usar

1. Abra **EconomIA** no menu lateral do Home Assistant.
2. Em **Mais**, preencha o CEP, quem mora na casa (incluindo quantos pets), restrições, interesses e os dias em que você costuma comprar.
3. Em **Minha lista**, adicione o que você compra sempre, pelo campo do topo, por **Escolher fotos** ou por **Colar mensagem**. Toque em **Comprei hoje** quando comprar: o painel aprende de quanto em quanto tempo cada coisa acaba. **Limpar lista** apaga tudo, com opção de desfazer.
4. Toque em **Buscar**, no centro do menu de baixo. A busca leva alguns minutos e você pode continuar usando o painel.
5. Em **Ofertas**, use **Não mostrar** em qualquer oferta que não faça sentido para você. Cada oferta tem um link para a fonte.
6. Em **Mais**, no fim da tela, fica **Lojas**: desmarque as que não quer acompanhar ou adicione uma que não apareceu.

## Itens por foto ou mensagem

Em **Minha lista → Escolher fotos**, tire ou escolha quantas fotos precisar, até 8 (print de conversa, lista escrita à mão, embalagem que acabou). Dá para tirar uma foto da lista. Quando terminar, toque em **Digitalizar com IA**: a IA do Home Assistant devolve os itens, você confere, ajusta o nome se quiser e adiciona. Se a lista veio em texto, use **Colar mensagem**.

Para ler fotos, a IA escolhida precisa aceitar imagens (a Anthropic aceita). A foto fica um instante na pasta de mídia do Home Assistant, só para a IA ler, e é apagada em seguida.

## Melhor tamanho

Pode escrever só o produto, como **Lysoform**. Na busca, o EconomIA traz também as outras embalagens (galão de 5 L, kits, fardos, leve 3 pague 2) e compara o **preço por litro, quilo ou unidade**:

- **Compensa o maior**: diz qual embalagem levar, onde, quanto economiza em relação a comprar a mesma quantidade no tamanho de sempre e quanto tempo dura no seu ritmo.
- **Tamanho de sempre**: o maior não compensa. Quando é o caso, mostra que, por exemplo, 5 de 1 L saem mais baratos que 1 de 5 L.
- **Compensa, mas dura muito**: o maior é mais barato, mas duraria mais do que você costuma guardar. Ajuste em **Mais → Rotina de compras → Espaço para estoque**.

## Roteiro de compras

Na aba **Roteiro**, ao lado da Minha lista, diga em até quantas lojas você topa parar (1 a 4) e se é a lista toda ou só o que está acabando. O EconomIA testa as combinações de lojas e mostra:

- o total e a economia sobre o preço médio;
- o que comprar em cada parada, da loja mais perto para a mais longe, com link para a rota no Maps;
- o que compensa pedir online (pode desligar);
- quanto uma parada a mais economizaria. Se for pouco, ele recomenda menos paradas, e dá para comparar as opções com um toque.

## Clubes e cupons do app

Em **Mais → Lojas → Clubes e cupons do app**:

- Marque **Sou do clube** nas lojas em que você é cadastrado (quase sempre é só o CPF no caixa). O preço de clube dessas lojas passa a valer na lista, no roteiro e nas ofertas. Nas outras, o preço de clube aparece marcado e o EconomIA avisa quando valeria a pena entrar no clube.
- Em **Cupons do app**, escolha prints da carteira de cupons do app da loja (Bem Panvel, Raia, Meu Atacadão...) e toque em **Digitalizar com IA**. Confira a loja de cada cupom e guarde: eles aparecem em Ofertas como **Seu cupom** e na abertura quando estiverem perto de vencer.

O EconomIA não entra na sua conta das lojas: esses apps não têm acesso aberto e pedem código por SMS.

## Compras online

A aba **Online** compara Mercado Livre, Amazon e outros marketplaces que você marcar em **Mais → Compras online**. Marque também as assinaturas que dão frete grátis (Amazon Prime, Meli+).

- O preço considerado é o **preço mais o frete** para o seu CEP. Kits aparecem com o preço por unidade.
- Prime e Meli+ dão frete grátis só nos produtos elegíveis (na Amazon, os com selo Prime). O frete de cada item já vem com a assinatura considerada.
- Na Minha lista, cada item mostra se **compensa pedir** ou se é melhor **comprar na loja**. Se o pedido chegaria depois de o item acabar, o EconomIA sugere comprar na loja agora e diz até quando pedir da próxima vez.
- Só entram lojas oficiais ou vendedores bem avaliados. Importados ficam marcados, e remédios de receita ficam só nas farmácias.

## Lista por voz

Em **Mais → Lista do Home Assistant**, escolha a lista de tarefas que o EconomIA deve acompanhar (por exemplo, a **Lista de compras**). A partir daí:

- O que você pedir ao Assist, como "adicione café na lista de compras", aparece na Minha lista em até um minuto.
- Marcar um item como concluído na lista do Home Assistant conta como **Comprei hoje** no EconomIA.
- O que você adicionar no EconomIA vai para a lista do Home Assistant, e os itens que estão acabando entram sozinhos (dá para desligar as duas coisas).

Também dá para usar uma lista do **Google Tasks** conectada ao Home Assistant pela integração Google Tasks. Ela é atualizada pelo Home Assistant a cada 30 minutos.

Em **Mais → Dados e ajustes** você exporta a lista para Excel ou JSON, importa uma lista, escolhe o tema (automático, claro ou escuro) e a **cor do app** (o tema e a cor ficam guardados em cada aparelho).

Tudo o que você preenche fica guardado só no Home Assistant e entra nos backups dele.
