# EconomIA

Cupons, ofertas e a sua lista de compras nas farmácias, mercados e pet shops perto de casa, numa página só dentro do Home Assistant.

## Antes de começar

A busca de ofertas usa a IA do próprio Home Assistant. Você precisa de:

1. A integração **Anthropic** (ou outra que ofereça *tarefa de IA*) configurada em **Configurações → Dispositivos e serviços**.
2. A **busca na web** ligada nas opções da tarefa de IA dessa integração.

Se você tiver mais de uma tarefa de IA, escolha qual usar na opção `ai_task_entity` deste add-on. Em branco, ele usa a preferida do Home Assistant.

## Como usar

1. Abra **EconomIA** no menu lateral do Home Assistant.
2. Em **Mais**, preencha o CEP, quem mora na casa (incluindo quantos pets), restrições, interesses e os dias em que você costuma comprar.
3. Em **Minha lista**, adicione o que você compra sempre. Toque em **Comprei hoje** quando comprar: o painel aprende de quanto em quanto tempo cada coisa acaba.
4. Toque em **Buscar**, no centro do menu de baixo. A busca leva alguns minutos e você pode continuar usando o painel.
5. Em **Ofertas**, use **Não mostrar** em qualquer oferta que não faça sentido para você. Cada oferta tem um link para a fonte.
6. Em **Lojas**, desmarque as lojas que não quer acompanhar ou adicione uma que não apareceu.

## Lista por voz

Em **Mais → Lista do Home Assistant**, escolha a lista de tarefas que o EconomIA deve acompanhar (por exemplo, a **Lista de compras**). A partir daí:

- O que você pedir ao Assist, como "adicione café na lista de compras", aparece na Minha lista em até um minuto.
- Marcar um item como concluído na lista do Home Assistant conta como **Comprei hoje** no EconomIA.
- O que você adicionar no EconomIA vai para a lista do Home Assistant, e os itens que estão acabando entram sozinhos (dá para desligar as duas coisas).

Também dá para usar uma lista do **Google Tasks** conectada ao Home Assistant pela integração Google Tasks. Ela é atualizada pelo Home Assistant a cada 30 minutos.

Em **Mais → Dados e ajustes** você exporta a lista para Excel ou JSON, importa uma lista e escolhe o tema (automático, claro ou escuro).

Tudo o que você preenche fica guardado só no Home Assistant e entra nos backups dele.
