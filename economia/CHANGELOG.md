# Mudanças

## 1.26.0

- **Listas prontas** fixas, para usar em toda compra: numa lista, **Comprei hoje** marca o item e ele vai para **Comprados**, no fim, recolhido. O cupom, as oportunidades e o Roteiro olham só para o que falta. **Desmarcar** devolve um item; **Começar de novo** desmarca todos para a próxima compra, sem tirar nada da lista.
- Cada lista pode ter um **ícone**: escolha ao criar ou em **Editar** (o antigo Renomear).
- A **Compra rápida** saiu do Roteiro: as listas prontas fazem esse papel.

## 1.25.3

- **Vamos começar** aparece só para quem está começando: com a lista limpa (os itens vão para o Histórico), não aparece mais.

## 1.25.2

- **Compra rápida**: os itens do mesmo tamanho, lado a lado da esquerda para a direita.
- Quando a busca termina, a caixa **Busca concluída** no alto não aparece mais; só os avisos, quando houver.

## 1.25.1

- **Roteiro**: a **Lista** fica só com as suas listas e **Nenhuma**, sem **Todas**. De começo vale a lista aberta na Minha lista.

## 1.25.0

- **Roteiro**: sem uma escolha sua, o item já vai no tamanho que **compensa mais** (a Melhor compra da Minha lista), com o preço do pacote e a loja dele; antes só aparecia "Compensa levar…". O ✓ de **Sua escolha** continua mandando.
- **Encontrar lojas** também procura os **mercados que entregam**, até a distância de entrega, e diz quantos achou. As redes de mercado com loja online (Bistek, Fort, Atacadão, Giassi, Angeloni) são procuradas pelo nome, também no Google, porque o mapa perto de casa traz só as lojas mais perto.
- **Só sem fonte de preço** mostra também, em Online, o mercado da região que ainda não teve a entrega confirmada.

## 1.24.0

- **Benefícios do clube** (Mais › Lojas, com a IA ligada): nas lojas com clube, um toque pede à IA o que o clube dá (preço de clube, descontos, cashback, pontos, cupons, frete grátis…), quanto custa e como entrar, com a fonte. Fica guardado na loja; **Procurar de novo** atualiza.

## 1.23.0

- **Compra rápida** recomenda a loja de **melhor preço** entre as que têm mais itens; antes ficava com a mais perto quando a outra saía menos de R$ 5 mais barata. Se a recomendada fica mais longe, o app diz quanto você economiza.
- **Compra rápida** mais organizada: **Buscar preços** e **Limpar** logo embaixo dos itens, lado a lado; depois **Onde comprar**, os preços, **Como chegar** na largura do cartão e **Compare**. Antes o Limpar ficava no fim da tela.
- **Roteiro**: a **Lista** é uma escolha só (**Todas**, uma lista ou **Nenhuma**), com os botões do mesmo tamanho de Paradas e O que comprar.

## 1.22.0

- **Distância dos mercados que entregam** (Mais › Lojas › Compras online, com **Mercados da região que entregam** ligado): até 10, 15, 20, 30 ou 50 km, sempre mais que a da casa. O app procura no mapa os mercados nessa distância e pergunta ao site de cada um se entrega no seu CEP: os que entregam trazem o preço direto do site, mesmo com a loja fora do raio (como o Bistek).
- Em **Mais › Lojas › Online**, cada mercado da região mostra a distância e se entrega: quando o site não diz, aparece **Sem preços**, com o porquê em **Como foi testado**, e **Entrega no meu CEP** para você confirmar; os que não entregam vão para **Inativas**.
- **Botões na largura do cartão em todas as telas**, não só em Mais: **Abrir rota no Maps**, **Ler com IA** e **Fechar**, **Preencher o perfil** e **Importar lista**, **Mover** e **Cancelar**.

## 1.21.1

- **Sem preços de** (nas Ofertas) segue o **Testar agora**: uma loja que o teste achou de onde tirar o preço sai do aviso, e em **Mais › Lojas** diz **Preços na próxima busca**. Antes o aviso olhava só a última busca e não sumia depois do teste.
- **Encarte ou print de preços** na largura do cartão, como os outros botões (250 px no computador).
- **Espaço para estoque** (Mais › Casa) na largura do cartão, como os outros campos.

## 1.21.0

- **Sensores novos** no Home Assistant (com **Sensores no Home Assistant** ligado em **Mais › Configurações › Integrações**):
  - `sensor.economia_melhor_loja`: a loja onde a lista toda sai mais barata, com o total e quanto economiza;
  - `binary_sensor.economia_oferta`: ligado quando um item da lista está em oferta, com a loja e o preço.
- A aba **Documentação** traz um exemplo de automação.

## 1.20.0

- **A leitura por IA mostra o texto todo**: o nome de cada item achado (Ler com IA) e o benefício de cada cupom crescem com o texto, sem ficar cortados, e aumentam puxando o canto.

## 1.19.0

- **Buscar só com o ícone**: o botão do meio da barra de baixo fica só com a lupa, sem o texto embaixo, como em todos os apps da família (buscando, a lupa gira).
- **Botões na largura do cartão** no celular nas telas de Mais (Casa, Lojas e Configurações), como já era em Dados: um sozinho ocupa a linha, dois dividem a linha.
- **Campos de texto que aumentam**: o Colar mensagem aumenta puxando o canto, e o tamanho fica guardado no aparelho, como nos outros apps da família.

## 1.18.0

- **Atalho no celular**, em **Mais › Configurações › Opções**: o caminho do EconomIA no Home Assistant, com **Copiar**, e como criar um ícone na tela inicial do celular que abre o app direto (no app do Home Assistant: Configurações › Aplicativo complementar › Gerenciar atalhos). O mesmo vale em todos os apps da família.

## 1.17.1

- **Ofertas**: as dos itens da sua lista voltam a vir primeiro, com **Está na sua lista** (na 1.17.0 elas saíam do alto).

## 1.17.0

- **Listas prontas**: saiu o **Todas**. No lugar dele, **Nenhuma** mostra só os itens que não estão em lista nenhuma. Tirar um item de uma lista (sem outra) leva ele para Nenhuma, e apagar uma lista também. O **Limpar lista** fica em Nenhuma e tira só os itens dela.
- **Mover itens**, embaixo da barra das listas: escolha a lista de destino, marque os itens (ou **Marcar todos**) e toque em **Mover**.
- No **Roteiro**, as listas que entram são cada lista e **Nenhuma**; de começo, todas, e ao menos uma fica marcada.
- Ao escrever em Nenhuma um item que já está numa lista, o app diz em qual.
- O **Roteiro | Compra rápida** cabe numa linha em telas estreitas.

## 1.16.0

- **Compra rápida**, no **Roteiro**: escolha **Compra rápida** no alto e escreva o que precisa agora (pão, leite, pilha…), com as sugestões de sempre. Os itens não entram na sua lista. O app diz **aonde ir**: uma loja física só, a mais perto que tem tudo, a não ser que outra com os mesmos itens saia bem mais barata (aí ele diz quanto). Mostra o preço de cada item lá, **Como chegar** no Maps, o que falta lá e onde tem, e as outras lojas para comparar num toque. Nada de loja online: quem compra agora não espera a entrega.
- O que ainda não tem preço aparece marcado: **Buscar preços** procura só esses itens, só nas lojas físicas daqui. Um toque no item tira ele; **Limpar** tira tudo.
- Um preço online que a IA trazia sem a aba Online ligada não aparece mais como se fosse de uma loja física.

## 1.15.0

- **Listas prontas**, como Compra semanal e Compra mensal: ligue em **Mais › Configurações › Opções › Listas** (vem desligado). No alto da Minha lista, uma barra com **Todas**, cada lista e **+ Nova** troca de lista num toque. A tela toda segue a lista aberta, com os itens e o Cupom de economia. Um item pode estar em mais de uma lista, e o nome de cada lista no item põe ou tira ele dela. No **Roteiro**, você escolhe quais listas entram.
- Os botões de cada item ficam em duas colunas do mesmo tamanho: o **−** e o **+**, **Comprei hoje** e **Similares**.

## 1.14.1

- A **quantidade** de cada item continua depois de fechar e abrir o app (voltava para 1).

## 1.14.0

- **Quantidade** em cada item: **−** e **+** no começo dos botões do cartão (de 1 a 99). O preço mostra o total e quanto sai cada uma, e a economia, o Cupom de economia e o Roteiro contam a quantidade. No melhor tamanho, levar 2 de 1 kg faz o pacote de 2 kg valer. A lista resumida mostra o total. A quantidade vai junto no Exportar e volta no Importar, e a Conversa e o CorrerIA sabem dela.

## 1.13.0

- **Lista resumida**: acima dos itens, escolha **Completa** ou **Resumida**. Na resumida, cada item é uma linha com o nome, o preço escolhido e onde comprar; um toque abre o cartão inteiro, e tocar no nome dele fecha. A escolha fica guardada no aparelho.
- **Buscar de novo** no pé de cada item com preço: procura só aquele item, sem esperar a busca de tudo.

## 1.12.0

- **Sugestões ao digitar** o nome do item: a partir de 2 letras, aparecem logo abaixo o que já esteve na sua lista e os nomes que as lojas usam, sem marca e sem tamanho, do mais comum para o menos comum ("arroz" → Arroz branco, Arroz integral, Arroz parboilizado…). Toque numa para pôr no campo.

## 1.11.1

- **Tema**: **Automático** agora se chama **Sistema** (segue o claro ou escuro do Home Assistant, como antes). O nome cabe ao lado do ícone e é o mesmo em todos os apps da família.

## 1.11.0

- **Não mostrar › Nunca “palavra”**: esconde qualquer oferta com essa palavra, em qualquer loja e tamanho, como "energético"; dá para trocar a palavra antes. As palavras ficam em **Mais › Casa › Nunca mostrar**, junto das categorias: dá para escrever outra ali ou tirar com um toque. Elas também valem na Conversa e no CorrerIA.
- **Comparar preço** só junta o mesmo produto: um creme de barbear não aparece mais como "mais barato" que um creme 4 em 1.
- **Código de barras › Tirar foto**: abre a câmera do próprio app, em tela cheia, que lê o código sozinha quando ele entra no quadro (no app do Home Assistant abria a galeria).
- **Uma altura só**: botões, campos, caixas de seleção, botões de escolha (as abas de Configurações, o Tema) e as escolhas em botões têm a mesma altura, a mesma de todos os apps da família. O **Adicionar** da Minha lista e os botões de Integrações também. O Tema ficou com o ícone ao lado do nome.

## 1.10.0

- **Mais › Configurações › Dados**: os botões no padrão dos outros apps da família: na largura do cartão, da mesma altura, com o ícone pequeno ao lado do texto (o ícone do Criar backup e do Apagar tudo ocupava o botão inteiro). **Apagar tudo** fica vermelho, e na confirmação ele e o Cancelar ficam lado a lado.
- **Falar › Para falar**: a lista é a mesma do GerencIA, uma linha por fala para texto, com o nome do Home Assistant. Quem tinha escolhido um assistente continua com a fala para texto dele.

## 1.9.1

- Nada muda na tela. A versão do app agora é escrita num lugar só, e os testes conferem tudo na largura de um celular (390 px).

## 1.9.0

O EconomIA fica igual aos outros apps da família:

- **Dados**, na ordem dos outros apps: **Exportar**, **Backup na pasta share** (novo: **Criar backup** grava um `.zip` em `share/economia`, com **Restaurar**), **Importar** (agora também a planilha do Exportar), **Versões anteriores**, **Onde ficam os dados** e **Começar do zero** (novo: apaga a lista, o histórico, o perfil, as lojas e as ofertas, com uma confirmação em vermelho; os ajustes continuam e uma cópia fica em Versões anteriores).
- **Aparência**: o tema começa em **Automático** para quem nunca escolheu (antes era Escuro) e vale só no aparelho. A **cor do app** passa a valer para a casa toda: na primeira vez, fica a deste aparelho.
- **Cores**: as 12 cores da família, com os mesmos nomes dos outros apps. Amarelo vira Ouro, Roxo vira Lilás, Magenta vira Rosa e Cinza vira Grafite; chegam Laranja, Turquesa, Índigo e Menta. A **Cor do dia** é a mesma em todos os apps.
- **Integrações** na ordem dos outros apps: **CorrerIA**, **IA do Home Assistant**, **Uso da IA**, as integrações daqui e, por último, **Sensores no Home Assistant**.
- **Conversa**: o Voltar do celular fecha a conversa, como nos outros apps.

## 1.8.0

- **Ofertas**: as ofertas escondidas (pelo perfil, por **Nunca mostrar** ou por **Só esta oferta**) ficam no fim da lista, em **Escondidas (N)**, recolhidas. Um toque abre, com o motivo de cada uma e o **Mostrar de novo**. A faixa "Escondidas pelo perfil" do alto saiu.
- **Cupons**: os vencidos ficam no fim, em **Vencidos (N)**, recolhidos até um toque.
- **Encarte ou print de preços**: as lojas sugeridas para **De qual loja?** aparecem logo abaixo do campo, no visual do app, e não mais na lista do celular. Tocar numa preenche o campo.
- **Caixas de seleção**: fechadas, ficam iguais aos outros campos, com a mesma altura, os mesmos cantos e a seta do app.

## 1.7.1

- **Mais › Configurações › Integrações**: o que você começava a digitar logo ao abrir a aba (o App ID da Shopee, uma chave) podia ser apagado. Agora fica.

## 1.7.0

- **CorrerIA**: em **Mais › Configurações › Integrações**, ligue **Ligar a CorrerIA** e o EconomIA passa a responder no WhatsApp, no Claude e no Gemini, como os outros apps da família.
  - Dá para ver a lista com o preço mais barato de cada item, perguntar onde um produto está mais barato, ver as ofertas e os cupons.
  - Também dá para pôr e tirar itens da lista e anotar compras, com as mesmas regras da tela.
  - A tela avisa quando a lista mudou pela CorrerIA, e o quadro mostra o último uso.
  - Vem desligado e não precisa da IA daqui. Ao atualizar, o Home Assistant dá ao app acesso à pasta compartilhada, onde fica o endereço que a CorrerIA usa.

## 1.6.1

- **Mais › Sobre**: a CorrerIA agora é descrita como o chat com todos os apps (pergunte e peça, também pelo WhatsApp).

## 1.6.0

- **Vale a pena?** em cada oferta: abre a Conversa e a IA avalia o produto. Ela procura na web a nota, as avaliações de quem comprou, as reclamações e o preço de costume, e começa pelo veredito: Vale a pena, Depende ou Não vale. Usa a IA de buscar ofertas, a que tem a busca na web.
- **Destaque para você:** tocar nele leva até a oferta, que pisca na lista. Se outra loja estava filtrada, volta para Todas.
- **Botões de loja nas Ofertas:** aparecem só as lojas que têm oferta. Com uma loja só, os botões nem aparecem.
- **Lojas desligadas não aparecem nas Ofertas,** nem nos cupons, no Destaque e nos preços da lista. Isso agora vale também para:
  - o marketplace tirado da busca em Online;
  - os mercados da região, com **Mercados da região que entregam** desligado.

  Ligar uma dessas lojas em **Mais › Lojas** liga ela de novo na busca.

## 1.5.0

- **Ofertas › Comparar preço**: cada oferta tem **Comparar preço**, ao lado do **Não mostrar**. Ele procura o mesmo produto nas outras lojas e mostra a resposta embaixo da oferta.
  - **Mais barato em outra loja**: as lojas que têm o produto, da mais barata para a mais cara, com a mais barata marcada. Toque numa loja para abrir o produto.
  - **Menor preço entre 3 lojas** quando a oferta ganha, ou **Não achei em outras lojas**.
  - Outro tamanho conta pelo preço por quilo, litro ou unidade, e o tamanho dele aparece.
  - Procura primeiro nos sites das lojas, sem IA. A IA só entra quando faltam preços, e só se estiver ligada.
  - A comparação não mexe na Minha lista e continua lá depois de fechar o app.
- As ações de cada oferta (**Comparar preço** e **Não mostrar**) ficam numa linha só, embaixo da oferta.

## 1.4.2

- **Mais › Sobre**: a **CorrerIA** (o contato no WhatsApp) entra na lista dos apps.

## 1.4.1

- **Loja cujo site barra programas** (como a Droga Raia, que responde "erro 403"): em **Mais › Lojas › Como foi testado**, o último passo agora diz que o preço dela vem da busca na web da IA, que pesquisa em seu nome, como o Google e o Claude fazem. O EconomIA não força a entrada no site.
  - Sem a promessa de "Tento de novo amanhã", porque esse bloqueio não costuma mudar.
  - Sem IA, o passo diz onde ligar: **Mais › Configurações › Integrações › Usar IA**.
- O selo **Só com IA** virou **Preço pela busca da IA**. Com a IA desligada, a loja mostra "Ligue a IA para ter o preço".

## 1.4.0

- **Cor do dia**, igual nos outros apps: em **Mais › Configurações › Aparência**, a cor do app muda sozinha todo dia, uma por dia, na ordem das cores (sem o cinza). Vem ligada. Escolher uma cor desliga a Cor do dia e fica com ela; desligar volta para a última cor escolhida.
- Com o app aberto na virada do dia, a cor troca sem precisar recarregar.

## 1.3.0

- **Mais virou um menu, igual ao dos outros apps** (GerencIA, InventarIA): uma linha para cada coisa, com o ícone, o nome e o que tem, e cada uma abre a sua tela.
  - **Casa** e **Lojas** ganharam tela própria.
  - **Configurações** junta, em abas, **Integrações**, **Dados**, **Aparência** e **Opções**. A aba escolhida fica guardada.
  - **Sobre** é a última linha do menu, fácil de achar.
  - O **‹ Mais** no alto, o Voltar do celular e arrastar para a direita voltam para o menu. Aberta por um atalho (como **Preencher o perfil**), o Voltar volta para onde você estava.
  - O ícone de **Mais**, embaixo e na barra lateral, agora são os três pontinhos, como nos outros apps.
- Os avisos que mandam para outro lugar já dizem o caminho novo, como **Mais › Configurações › Integrações**.

## 1.2.0

- **Caixas de seleção** (a distância, o espaço para estoque, o tipo de loja, as IAs, a lista do Home Assistant, a loja de um item) abrem uma janela no visual do app, de baixo para cima, com as opções em linhas e a atual marcada na cor do app, no tema escuro ou claro, e não mais a janela padrão do celular, como nos outros apps da família. O Voltar do celular, o X ou tocar fora fecham só ela.

## 1.1.1

- **Os textos só dizem o que vai acontecer:**
  - **Mais › Casa › Rotina de compras:** sai o **Avisar no celular**. O aviso no celular ainda não existe, e a tela mostrava o dia em que ele chegaria.
  - **Mais › Integrações:** o **Instagram** só diz que os encartes entram na busca com a IA e os Folhetos ligados. A **Shopee** só diz de onde vem o preço quando ele vem mesmo (com a aba Online; sem a chave, só com a IA e a Shopee marcada em Compras online). A **Lista do Home Assistant** só explica o que sincroniza com uma lista escolhida.
  - **Mais › Lojas:** **Compras online** aparece só com a aba Online. A ordem da busca não mostra as etapas desligadas em Mais › Opções. Com a IA desligada, a loja adicionada à mão não promete mais o encarte nem a próxima busca. No **Como foi testado**, "a IA lê na próxima busca" só aparece com os Folhetos ligados.
  - **Minha lista:** com a busca direta desligada, **Similares** diz que ela está desligada em vez de prometer a próxima busca, e o item posto pelo código de barras não promete ser achado nas lojas.

## 1.1.0

- **Mais › Sobre:** a última linha de Mais, embaixo das abas, abre a página de quem faz os apps: **CorrerIA Code** (desenvolvimento de softwares), por que o nome, os seis apps da família (CronologIA, ResolvIA, GerencIA, InventarIA, EconomIA e MemorIA), cada um com uma linha e o link para o GitHub dele, e **Meu GitHub**. O EconomIA aparece marcado como **Este app**, com a versão. O Voltar do celular, o **‹ Mais** no alto e arrastar para a direita voltam para Mais. A mesma página dos outros apps, nas cores do EconomIA.

## 1.0.0

- **Versão 1.0:** a EconomIA sai da fase de testes. Tudo continua igual ao 0.20.2.

## 0.20.2

- **Buscar o preço de um item:** quando a IA falha (cota, erro) e os sites das lojas respondem, o aviso agora diz que a IA falhou e por quê. Antes, aparecia só "Não achei preço" ou nada.
- **Encarte do site feito no Wix:** as imagens do encarte não viram mais pedaços de endereço sem sentido (o endereço do Wix tem vírgulas).
- **Folhetos:** um folheto sem data na página da loja não pega mais a data do folheto ao lado. A validade vem da página do próprio folheto.

## 0.20.1

- **Remédio pela dose:** "Dipirona 500 mg" e "Dipirona 500mg" agora são o mesmo item, e 500 mg continua sem casar com 1000 mg.
- **Frete escrito como texto** ("R$ 9,90", "Grátis") agora conta. Antes, a oferta online com frete assim ficava de fora.
- **Telas:**
  - O selo do cupom que vence logo não fica mais esticado.
  - O ícone de "pronto" do Falar e o círculo girando do Buscar voltaram a aparecer.
  - Em Mais › Lojas, a loja adicionada à mão sem endereço aparece também antes da primeira busca online.
- **Por dentro:** 511 testes automáticos e 15 telas testadas no navegador, cobrindo 99% do código do servidor. O GitHub roda tudo a cada mudança.

## 0.20.0

- **Conversa com a IA:** um balão ao lado do microfone, no alto da tela. Pergunte sobre a tela aberta ou sobre qualquer assunto, a qualquer momento.
  - A IA vê a sua lista com os preços, o que você mais compra, as ofertas e os cupons das lojas que você acompanha, e quem mora na casa.
  - Ela só sugere: **Pôr na lista**, **Tirar da lista**, **Comprei hoje**, **Buscar o preço** ou **Abrir** uma tela viram botões, e nada muda sem o seu toque.
  - Tem sugestões de pergunta para cada tela e microfone próprio (o que você fala vai para a caixa, para conferir antes de enviar).
  - Usa uma tarefa de IA do Home Assistant, nunca um assistente de conversa, que poderia mexer na casa. Some com **Usar IA** desligado. Conta em **Uso da IA** como "Conversa".

## 0.19.0

- **Código de barras:** botão ao lado do Adicionar, na Minha lista.
  - **Como ler:** tire uma foto do código, ou digite os números de baixo. No Chrome do Android, o próprio navegador lê a foto; nos outros, o EconomIA lê pelas larguras das barras (EAN-13, UPC-A e EAN-8, com o código deitado, em pé ou de ponta-cabeça) e confere pelo dígito verificador. A foto funciona também com o Home Assistant sem https, ao contrário da câmera ao vivo.
  - **Onde procura o produto:** primeiro nas lojas com busca no site (nome, preço e link da loja do seu CEP), depois no Open Food Facts (base aberta).
  - **Na lista:** o item entra com o código. Na busca direta, o mesmo produto é achado pelo código mesmo quando o nome da loja é outro. O código também fica no histórico.
  - **Código de balança ou da loja** (começa com 2): o EconomIA avisa que só vale naquela loja.
- **"Quis dizer…?":** ao adicionar "Álcool de lompeza", o EconomIA sugere "Álcool de limpeza". A correção usa as palavras dos produtos que as lojas já mostraram: uma palavra que nenhum produto usa vira a mais parecida, com o acento das lojas.
  - O item sem preço também mostra a sugestão, que troca o nome com um toque.
  - Se o nome escrito não acha nada, a busca direta e a busca do site tentam o nome corrigido sozinhas.

## 0.18.0

- **Seção da loja confere o produto.** A busca do site (Giassi, Angeloni, Fort, Sam's Club) já dizia em que seção cada produto está, e o app não usava isso. Agora usa:
  - Entre os produtos que casam com o item, fica quem está numa seção que fala do item. A almôndega de "Carne moída bovina" em Congelados › Pratos prontos sai, e fica a carne moída do Açougue › Bovinos.
  - A seção de cada item é aprendida por loja (`casados.json`). Nas buscas seguintes, produto de outra seção só entra se for o mesmo produto, reconhecido pelo código de barras.
- **Previsor de categorias do Mercado Livre (opcional, grátis):** em Mais › Integrações. Ele classifica o item da lista e cada produto achado, com o mesmo modelo que o Mercado Livre usa nos anúncios; produto de outra categoria sai.
  - Vale para todas as fontes sem IA: site da loja, busca do site, catálogos, encartes e Shopee.
  - Só tira produto quando confirma ao menos um na categoria do item; se não confirma nenhum, quem pode estar errado é o palpite para o item, e nada sai.
  - Precisa de um app de desenvolvedor do Mercado Livre, autorizado uma vez. O EconomIA renova o acesso sozinho. O App ID, a chave e o acesso ficam em `segredos.json`; as respostas, em `categorias_ml.json` por 90 dias, com no máximo 400 consultas novas por hora.
- **Similares:** botão **Similares** em cada item da lista. Ligado, aparece "Similares mais em conta" com até 3 produtos da mesma seção da loja, mais baratos pelo preço do quilo ou do litro: sobrecoxa, asa ou frango inteiro para quem pediu coxinha da asa. Nunca substituem o preço do item.
  - O ✓ (Escolher esse) num similar faz dele a sua escolha, também no Roteiro, onde aparece "Similar: …".
  - Por enquanto vêm das lojas com busca direta no site. Seção de um nível só ("Açougue") não serve: misturaria boi, porco e frango.
- **"ou" no item:** "Coxinha da asa ou asinha" busca os dois e vale o mais em conta.

## 0.17.9

- **"Carne moída bovina de primeira" não casa mais com "Hambúrguer Texas Burger Carne de Frango e Bovina".** Três ajustes:
  - **Outro tipo:** produto que começa por outro tipo (hambúrguer), que o item nem cita, não é o item.
  - **Palavra logo depois do tipo:** com 4 palavras ou mais, ela é obrigatória ("carne **moída**", "papel **higiênico**"). Pode faltar uma das outras.
  - **Palavra associada:** só vale se for outra palavra, e não uma que o próprio item já tem. "Primeira" não podia mais ser cumprida por "bovina".

## 0.17.8

- **Produto vendido por peso na busca direta (VTEX):** a loja dá o preço por kg (ou por litro), e o `unitMultiplier` diz quanto vem na embalagem. O app usava o preço do kg como se fosse o da bandeja. A sobrecoxa Member's Mark de 2,3 kg do Sam's Club aparecia por R$ 14,98, ou R$ 6,51 o kg, quando a bandeja custa R$ 34,45 (R$ 14,98 o kg). Agora o preço é o do kg vezes o peso da embalagem. A "Melhor compra" e a economia erradas desse item somem na próxima busca.

## 0.17.7

- **Sem localização = online.** Loja sem endereço no mapa, cadastrada à mão ou que veio só de um site (como a Cobasi), sai da aba dela em Mais › Lojas. Ela aparece em Online, no grupo "Pet shops sem localização" (ou farmácias, mercados). Os preços dela também contam como online, que entrega.
- **Encontrar lojas procura onde fica a loja sem localização:** com a chave do Google, pelo nome e pela cidade, a filial mais perto até 20 km. Achada, ganha endereço, distância e o botão Mapa, e volta para a aba dela; se ficar mais longe que o seu raio, vai para as Inativas. A resposta fica guardada por 30 dias (`locais.json`), também o "não achei".

## 0.17.6

- **Item com uma palavra que a loja não usa, como "Álcool perfumado de cozinha":** nenhum álcool tem "cozinha" no nome, e item de até 3 palavras precisava de todas. Agora, quando nenhum produto casa inteiro, vale o **parecido**: só falta uma palavra, e nenhum produto daquele tipo na loja a usa. Assim o "Álcool Araras Bactericida Eucalipto" entra para o álcool perfumado de cozinha, e o nome do produto aparece no item para você conferir.
- Palavras de restrição nunca ficam de fora: lactose, glúten, açúcar, diet, light, zero, integral, desnatado, orgânico, sódio, filhote, castrado, gato e cachorro, entre outras. "Leite sem lactose" continua sem casar com leite comum.
- O parecido não guarda o código de barras: ele não é usado para reconhecer o produto em outra loja.

## 0.17.5

- **Fort (e outras lojas do bairro) nos preços como loja física, não online.** Duas coisas mandavam o preço para Online:
  - **Categoria guardada:** o teste do site guardava a categoria com que a loja foi vista primeiro. O Fort tinha aparecido antes como "mercado da região que entrega" e continuava online.
  - **Limite de 20 lojas:** a lista de lojas do bairro usada nessa decisão parava nas 20 primeiras em ordem alfabética.
  
  Agora a categoria vem das lojas do raio na hora da busca, todas elas, e das que você cadastrou. Só fica online quem não está entre elas. Vale para as páginas de produto, a busca do site e a busca direta.
- O preço antigo da mesma loja em outra categoria também sai quando ela é consultada de novo: o "Fort Atacadista · Online" de R$ 4,59 no papel toalha some depois da próxima busca.

## 0.17.4

- **Escolher esse:** cada loja nos preços do item e cada linha do Comparar tamanhos têm um botão ✓. A opção escolhida, mesmo que não seja a mais barata, vira **Sua escolha** no alto do item, com o aviso de qual é a mais barata e o **Desfazer escolha**. Ela também vale no Roteiro: o item vai para a loja escolhida. Se a loja não trouxer a opção na busca seguinte, o item avisa.
- **Economia comparada à segunda opção:** a "economia de" de cada item agora é o que você deixa de pagar em relação à segunda loja mais barata, e não à mais cara. No café em grãos ficava R$ 70 só por causa de um 1 kg de R$ 151,90 no Angeloni. A soma no cupom de economia segue a mesma regra. Com o tamanho que compensa, a comparação é com o avulso mais barato.
- **Ícone em cada item da lista** (café, leite, papel, limpeza, ração, remédio…), para achar o item rolando. Sem um tipo conhecido, o ícone é o do tipo de loja. O **Comparar tamanhos** também ganhou um ícone.
- **Abas em Mais › Lojas:** Farmácias, Mercados, Pet shops e Online, uma de cada vez. A procura pelo nome continua olhando a lista inteira, e o tipo do "Loja que não apareceu" acompanha a aba.
- **Preço antigo trocado pelo novo:** sem IA, a busca juntava o resultado novo ao anterior e nunca tirava o preço de uma loja. Um produto casado errado numa busca antiga (o "Limpador VEJA … e Álcool" no álcool perfumado) ficava para sempre. Agora a loja consultada de novo pelo site troca o preço antigo do item pelo novo, ou tira o preço quando não acha nada.

## 0.17.3

- **Histórico em Minha lista:** o botão ao lado do Adicionar mostra os itens que já estiveram na lista, do que você mais compra para o que menos compra, com quantas vezes comprou e a última data. Um toque põe o item de volta na lista, com as compras de antes (o app continua sabendo de quanto em quanto tempo ele acaba).
  - **Filtro:** escrever no campo do Adicionar filtra o histórico.
  - **Adicionar pelo nome:** adicionar um item que já esteve na lista também traz as compras de antes.
- **Remover ou limpar não apaga mais as compras:** os itens vão para o Histórico. "Tirar" no histórico apaga de vez.
- O histórico guarda até 300 itens, em `config.historico`.

## 0.17.2

- **Atacarejos no mapa:** a busca do Google por mercados também procura "atacadista". Fort, Atacadão, Assaí e Komprão entram mesmo quando o Google os marca só como atacado ("wholesaler" ou "warehouse_store"), sem "supermarket". Atacados de outras coisas (pisos, embalagens, materiais de construção, roupas, bebidas…) ficam de fora.
- Antes disso, o Fort do Bucarein não aparecia entre as lojas perto de casa. Como o site dele tinha preço, ele ia para Online como "mercado da região que entrega", com "frete no carrinho".

## 0.17.1

- **Tamanho errado pelo desconto:** "Limpador VEJA 500ml com 10% de Desconto" virava 5 L, porque o "com 10" era lido como pacote com 10 unidades. "Café 500g com 20% off" virava 10 kg. Agora "com N%", "por cento", "off", "reais" e "de desconto" não contam como pacote. Isso também inflava o "Compensa o maior" e a economia possível.
- **Tipo do produto:** o tipo do item (a primeira palavra) precisa ser o tipo do produto. Ele tem de estar entre as 3 primeiras palavras do nome (a marca pode vir antes), sem outro tipo antes dele. "Limpador Multiuso VEJA … Lavanda e Álcool" não conta mais como álcool, e "Pão Nino … Leite" não conta como leite. Os tipos são aprendidos do vocabulário: as palavras que costumam abrir o nome dos produtos. Item que começa pela marca, como "Churu atum", só precisa da marca no começo do nome.

## 0.17.0

- **Casamento do item com o produto pelo padrão de nome do varejo** (tipo + marca + variante + tamanho), sem IA:
  - **Tipo e marca:** o tipo, que é a primeira palavra do item ("álcool", "leite"), e a marca precisam estar no nome do produto.
  - **Palavra que a loja não usa:** se nenhum produto do mesmo tipo usa uma palavra do item (como "perfumado" entre os álcoois), ela vale pelas palavras que andam junto dela nos produtos que as lojas já mostraram, como lavanda e eucalipto. Essas palavras são aprendidas sozinhas, dos catálogos e das buscas, e ficam em `vocabulario.json`.
  - **Palavra que a loja usa:** se os produtos do mesmo tipo usam a palavra (como "integral" entre os leites), ela tem de estar no nome.
- **Mesmo produto em outra loja pelo código de barras (EAN):** o produto achado com certeza numa loja guarda o EAN (em `casados.json`). Assim ele é reconhecido em outra loja com outro nome, como "Alcool Liquido 46 Araras Euca 1L" no Angeloni, igual ao "Álcool Araras Bactericida Eucalipto" do Giassi.
- **Segunda busca pelo tipo e pela marca:** quando a busca com o item inteiro não traz nada, o app busca de novo só pelo tipo e pela marca e casa o resultado pelas regras acima. Vale na busca direta, na busca do site e nas páginas de produto.
- A lista de fragrâncias da 0.16.12 fica como vocabulário inicial; o aprendido soma a ela.

## 0.16.12

- Item com "perfumado" (ou "aromatizado", "cheiroso") acha o produto pelo nome da fragrância: "Álcool perfumado" bate com "Álcool Araras Bactericida Eucalipto" e "Álcool … Lavanda". Os sites não escrevem "perfumado" no nome do produto, e o item ficava sem preço.
- Quando a busca do site não traz nada com todas as palavras, o app busca de novo só pelo principal ("álcool") e fica com os produtos de fragrância. Vale para a busca direta (Giassi, Angeloni…), para a busca do site e para as páginas de produto (Condor).

## 0.16.11

- Online: cada marketplace mostra o link do próprio site (amazon.com.br, magazineluiza.com.br, ifood.com.br…) no lugar do selo "Site", como as lojas físicas.

## 0.16.10

- Mais › Lojas: campo **Procurar loja na lista**. Mostra só as lojas com aquele nome, em todas as categorias e também nas Inativas (que abrem sozinhas), nos marketplaces e nas lojas adicionadas por você. Funciona junto com o Só sem fonte de preço.

## 0.16.9

- Clubes conferidos de mais redes, com o nome no botão de cada loja:
  - **Preço de membro pelo CPF:** Bem Panvel, Clube DC (Drogaria Catarinense), Clube PP (Preço Popular), Mais Saúde (Raia e Drogasil) e Clube Mais (Fort).
  - **Ofertas ativadas no app:** Clube Bistek, Super Clube (Imperatriz), Clube K (Komprão), Meu Atacadão, Sempre Bem (Pague Menos), Amigo Cobasi e Clubz (Petz). Essas ofertas também entram pelo print em Cupons do app.
- Drogão, FarmaSesi e São João ficam como "Adicionar clube" até dar para confirmar as regras.

## 0.16.8

- **Clube em cada loja.** Em Mais › Lojas, cada farmácia, mercado e pet shop tem o botão do clube: o nome do clube quando ele foi conferido (Amigo Giassi, Club Nissei), **Tem clube** quando a busca achou um, ou **Adicionar clube**. Um toque vira **Sou do clube**. A lista separada de clubes no fim saiu (a seção ficou só com os Cupons do app).
- Clube só de pontos ou cartão, como o Clube Angeloni, não aparece: ele não muda o preço da prateleira.
- A busca com IA recebe as lojas de que você é sócio e procura o preço de membro delas. Com a IA desligada e algum clube marcado, a tela avisa que o preço de clube só chega pela IA.
- **Encontrar lojas** também em Mais › Lojas, no alto da lista.
- **Ofertas:** lojas que o mapa tirou da categoria (pet shop e farmácia veterinária nas farmácias) ou que estavam duplicadas não aparecem mais nos filtros nem nas ofertas; seguem a loja de mesmo nome, se houver, ou ficam de fora.

## 0.16.7

- Mais › Lojas: no "Loja que não apareceu", o tipo de loja e o botão Adicionar têm a mesma largura, e os dois campos de texto ficam alinhados.

## 0.16.6

- **Online:** os marketplaces escolhidos (Amazon, Shopee, Magalu, Americanas, Casas Bahia, iFood, Rappi) aparecem como o Mercado Livre: caixa de marcar, "Entrega no seu CEP", Site e App. Desmarcar tira o marketplace da busca (vai para Inativas, onde dá para marcar de novo); é o mesmo "Onde procurar" de Compras online.
- **Testar agora nas lojas online.** Marketplace: a Shopee pela API de afiliados (quando ligada); os outros pela busca do próprio site, se o robots.txt deixar e o resultado mostrar preço. Se a busca do site funcionar, ela entra nas próximas buscas, sem IA. A lista de produtos (sitemap) de marketplace nunca é baixada. Mercados da região que entregam usam o mesmo teste das lojas físicas.
- **Só sem fonte de preço**, em Mais › Lojas: mostra só as lojas com "Sem fonte de preço" ou "Sem preços" (também nas Inativas), com a contagem ao lado.

## 0.16.5

- Preço da página do produto pelas meta tags em qualquer ordem de atributos (`<meta content="90.25" property="product:price:amount">`), também `og:price` e o preço promocional (`product:sale_price:amount`, fica o menor). É o caso da Farmácia Fique Bem (plataforma Magazord): a vitrine e a busca do site são montadas por JavaScript, e a busca é proibida para robôs, mas a página de cada produto traz o preço do PIX nas meta tags.
- O nome do produto vem do `og:title` ou do `<h1>`; sem eles, do endereço da página (o `<title>` desses sites costuma ser texto de SEO). Produto marcado como sem estoque na meta tag fica de fora.
- No teste, quando a loja não vende o item de exemplo, o app escolhe no sitemap os endereços com cara de produto (com tamanho, como "50ml", ou terminados em `/p`) em vez dos primeiros da lista, que podem ser categorias.

## 0.16.4

- Catálogos Ofertas: o app pede a página como um navegador comum pede (dizendo que aceita HTML) e guarda os cookies que o próprio site manda entre um redirecionamento e outro. Na 0.16.3 a página da Droga Raia chegava vazia ao Home Assistant (0 KB), embora tenha o encarte.
- O endereço com o nome inteiro da loja é tentado primeiro (`droga-raia` antes de `droga`), e o motivo no "Como foi testado" é sempre o da página certa.
- Página que chega vazia: o "Como foi testado" mostra o código da resposta, o tamanho e o servidor. Página que só redireciona (meta refresh) é seguida uma vez; a que manda para a página inicial conta como "não tem a loja".
- Verificação de robô reconhecida também no AWS WAF, Imperva, DataDome e PerimeterX, sem confundir com páginas normais que só carregam o script do Cloudflare. O app não tenta passar por ela.
- Página do encarte que vem em JPEG e WebP fica com a WebP (o formato das imagens grandes).

## 0.16.3

- Catálogos Ofertas: o link do folheto é achado em qualquer lugar da página da loja (link com parâmetros, atributos `data-*` ou os dados que a página traz em JSON), não só num `href` simples. O encarte da Droga Raia não era reconhecido na página real.
- "Como foi testado" diz quando a página da loja abriu mas não tinha folheto que o app consiga ler (com o tamanho da página) e quando o site pediu verificação de robô (Cloudflare).

## 0.16.2

- "Como foi testado" diz por que cada site de encartes não trouxe o folheto, em vez de só "Sem folheto": "Catálogos Ofertas: o site recusou o acesso de programas (erro 403)", "o robots.txt do site não deixa", "o site não deixa mandar o conteúdo para IA", "só tem folheto vencido" ou "o site não respondeu". Os sites que simplesmente não têm a loja continuam em "Sem folheto no …".

## 0.16.1

- **Brave Search (opcional), em Mais › Integrações.** Acha o site das lojas que o mapa não traz, sem IA: o app busca "nome da loja + cidade" e fica com o primeiro resultado que é o site da própria loja (pula Instagram, Facebook, guias e listas de empresas, CNPJ, marketplaces, iFood e sites de encartes, e exige uma palavra do nome da loja no endereço ou no título). O site achado é testado na hora. Chave grátis com 2.000 buscas por mês em api-dashboard.search.brave.com; o app faz uma busca por segundo, só para as lojas sem site, e guarda a resposta por 30 dias.
- Com o Brave e a IA, o Brave procura primeiro; a IA só procura as lojas que ele não achou.
- O Testar agora procura o site de novo, sem o que ficou guardado.

## 0.16.0

- **O app procura o site das lojas sozinho.** Loja que o mapa trouxe sem site (como a Agropecuária Manchester) tem o site procurado pela busca na web da IA: uma pergunta só, para todas as lojas sem site, no Encontrar lojas (e no Testar agora daquela loja). A resposta fica guardada por 30 dias, também o "não tem site". O site achado é testado na hora e passa a aparecer na loja, com o Trocar site. Precisa da IA ligada; sem ela, o "Como foi testado" avisa.
- **Preço da página do produto sem dados schema.org.** Sites que mostram o preço só no texto (Cobasi, Pet Finess) agora têm o preço lido pelo produto de nome parecido com o título da página. Preço de "Compra Programada", parcelas e produtos sugeridos ficam de fora.
- **Loja que não vende o item de teste.** Se o site não tem "ração" (uma loja de camas, por exemplo), o teste lê o preço de outro produto do site, para mostrar que o preço vem dali.

## 0.15.9

- **Preço pela busca do site.** Sites como o da Cobasi não têm a busca direta (API) nem os dados de preço nas páginas de produto, mas a página de resultados da busca mostra os produtos com preço. O teste de preço agora tenta a busca do próprio site (nos endereços comuns, como `/pesquisa?terms=` e `/busca?q=`, só os que o robots.txt deixa), guarda o endereço que funcionou e, nas buscas, procura cada item da lista ali (até 15 itens, devagar). A loja aparece com **Preço pela busca do site**. Sem IA.
- **Agropecuárias** (que vendem ração) entram em Pet shops: no OpenStreetMap (`shop=agrarian`) e na busca do Google por "agropecuária".

## 0.15.8

- **Comparar tamanhos repetido.** O mesmo produto da mesma loja ("Pilão 500 g · Giassi · R$ 19,98") entrava de novo a cada busca e a lista crescia. Agora cada produto de cada loja aparece uma vez, com o preço mais recente; a tela já esconde os repetidos que estavam guardados, e a próxima busca limpa o arquivo.

## 0.15.7

- **Testar agora** também nas lojas Inativas, e o resultado do teste aparece nelas. Dá para ver se vale a pena voltar a acompanhar uma loja antes de marcar.

## 0.15.6

- **Loja repetida.** A mesma loja vinha duas vezes quando o OpenStreetMap e o Google escrevem o nome diferente ("Supermercado Impeatriz", com erro de digitação, e "Supermercado Imperatriz - Joinville"). Agora:
  - o que vem depois do traço (" - Joinville", " - Glória") não conta na comparação;
  - duas lojas a até 150 m uma da outra com nomes quase iguais são a mesma;
  - fica o nome do Google, e as repetidas que já estavam na lista saem no próximo Encontrar lojas ou Buscar.
- Mercado da região que também está em Mercados (perto de casa), como o Giassi, não aparece de novo em Online.

## 0.15.5

- **Testar agora**, em cada loja de Mais › Lojas: testa o preço só daquela loja, na hora, sem a busca geral nem o Encontrar lojas. Testa de novo o site, a página de ofertas, o Instagram e os sites de encartes, sem usar o que ficou guardado, e abre o "Como foi testado" com o resultado. Serve para conferir na hora o que mudou numa loja (um site trocado, um @ do Instagram).

## 0.15.4

- Em Mais › Lojas › Online aparecem todos os marketplaces escolhidos (Mercado Livre e Amazon, por padrão), mesmo os que a última busca não trouxe, com a fonte do preço: **Preço pela API** (Shopee, com a integração ligada) ou **Só com IA** (Amazon, Mercado Livre e os outros, que não têm API aberta). Com a IA desligada, eles aparecem como Sem fonte de preço.
- Loja online não mostra mais "Sem localização" nem a distância.

## 0.15.3

- **Menos texto.** Saíram as explicações do óbvio em todas as telas: o porquê de cada opção, o que a IA faz depois de cada botão, o que já está no nome do botão ou da opção. Os textos que ficaram dizem só o que é preciso para usar (de onde vem a chave, o que precisa ligar). Exemplos: "Desmarque as lojas que não quer ver" no lugar de três frases; "Em quantas lojas você topa parar?"; o passo a passo da busca com uma frase por etapa; o rodapé só com a versão.
- "Como foi testado" mais curto: sem repetir "dá para informar em Adicionar site de ofertas" (o botão está logo abaixo).

## 0.15.2

- Em IA do Home Assistant, as três escolhas (Para buscar ofertas, Para ler fotos e Para falar) ficam juntas, uma embaixo da outra, com a mesma largura. O Verificar de novo vem depois delas e testa as três.

## 0.15.1

- **Para falar** com opções, como "Para ler fotos": em Mais › Integrações › IA do Home Assistant, escolha qual fala para texto o Falar usa. A lista traz os assistentes de voz do Home Assistant que têm fala para texto (com o nome do motor, por exemplo "Assistente: Home Assistant (Home Assistant Cloud)") e as outras entidades de fala para texto (por exemplo "Google Generative AI STT"). No padrão, continua o assistente de voz preferido do Home Assistant. Se a escolhida sumir, o app volta para o padrão e avisa.

## 0.15.0

- **Instagram (opcional), em Mais › Integrações.** Muito mercado do bairro posta o encarte só no Instagram, como o Boi Dourado. Com uma chave da Meta, o app olha os posts das lojas que você acompanha (API oficial do Instagram, "Business Discovery"). Post de oferta dos últimos 8 dias, pela legenda, é lido uma vez pela IA, como o folheto, e os preços ficam guardados até a validade do encarte. Precisa de uma conta profissional do Instagram ligada a uma página do Facebook, e a loja precisa ter conta comercial. Passo a passo no DOCS.
- O Instagram da loja vem do mapa (OpenStreetMap e Google) ou de você: em Adicionar site de ofertas, escreva o @ da loja. A loja mostra o @ com link e, depois da leitura, "Encarte do Instagram até 05/11" com o link do post.
- "Como foi testado" diz se a loja tem post de oferta no Instagram, se o encarte já foi lido, ou que a conta não é comercial.
- **Encarte vencido não entra mais.** A página do Mercado Engenho (keepo.bio) ainda mostra ofertas "válidas até 09/04/24": a leitura do encarte do site é descartada quando a validade já passou, e a leitura sem IA da página de ofertas também.
- Depois da busca, "Tem folheto" e "Tem encarte no Instagram" viram "Folheto da semana" e "Encarte do Instagram" quando a IA já leu.

## 0.14.9

- **Portafolhetos** entra como fonte de folhetos (é da mesma empresa do Kimbino e tem Angeloni, Atacadão, Bistek, Fort, Komprão, Drogasil e Pague Menos). Serve quando a loja não aparece no Kimbino.
- Todos os sites de encartes (e os servidores das imagens) têm o robots.txt conferido antes de abrir. Se o site disser **ai-input=no** (sinal de conteúdo que proíbe mandar o conteúdo para uma IA), o EconomIA não usa aquele site, porque o folheto é lido pela IA.

## 0.14.8

- **Catálogos Ofertas** entra como terceira fonte de folhetos, depois do Kimbino e do Seus Folhetos. Ele tem o encarte da **Droga Raia** (e de outras redes que não estão nos outros dois). O app abre só a página da loja e a do encarte, que o robots.txt do site libera, e confere essas regras antes de abrir.
- A página do encarte traz só miniaturas de 260 px. O add-on procura sozinho o maior tamanho que o servidor de imagens tiver e guarda o que achou por 30 dias. Se só houver miniatura, o folheto não é mandado para a IA (não dá para ler preço nelas) e o app diz isso, em vez de gastar IA à toa.
- Ler o folheto continua precisando da IA ligada: uma leitura por folheto, guardada até ele vencer.

## 0.14.7

- A loja mostra o site que ela já tem, com link (ex.: "drogariadrogao.com.br"), ao lado do Mapa. O site é o que você informou, o do mapa ou o que o teste usou.
- Com site, o botão diz **Trocar site** (e o campo já vem com o endereço). "Adicionar site de ofertas" só aparece quando a loja não tem site.

## 0.14.6

- "Como foi testado" mostra qual site e qual página foram testados ("O site drogao….com.br não publica a lista de produtos", "Não achei preços no texto da página …").
- Quando o "site" da loja no Google ou no OpenStreetMap é Instagram, Facebook, WhatsApp, Linktree ou iFood, o app não testa como site e diz isso no "Como foi testado".
- Lojas registradas antes com o nome todo em maiúsculas ("DROGARIA DROGÃO JOINVILLE") passam a aparecer com o nome normal.
- Texto do erro do site mais limpo: "recusou o acesso de programas (erro 403). Tento de novo amanhã."

## 0.14.5

- **Preço pela página do site, sem IA.** Farmácias e mercados pequenos que mostram os produtos e os preços na própria página (como a Drogaria Floresta, "Comprar pelo WhatsApp") agora têm preço sem IA. O app lê o texto da página que você informou em Adicionar site de ofertas (ou a página inicial e a página de ofertas ligada a ela), acha os cartões "produto + R$" (também dados schema.org e os dados que a página traz em JSON) e procura os itens da lista neles. A loja aparece com **Preço pela página do site** e um exemplo. Vale o robots.txt; cada página é lida no máximo a cada 12 horas.
- No teste de preço, o site que você informou em Adicionar site de ofertas vale mais que o do mapa.
- Quando a página não traz os preços no texto (o site monta tudo depois, no navegador), o "Como foi testado" diz isso.

## 0.14.4

- **Pet shop não aparece mais em Farmácias.** O Google marca como farmácia o pet shop que vende remédio (Vanilla Pet Center) e a farmácia veterinária (Animal Farma). Agora valem o tipo principal da loja no Google e o nome (pet, vet, veterinária, animal, agropecuária). As que o mapa já tinha registrado saem da lista no próximo Encontrar lojas ou Buscar.
- **FarmaSesi** reconhecida pelo nome, com o site farmasesi.com.br, mesmo sem o Google.
- Redes de farmácia com o nome da filial depois ("FarmaSesi - Itoupava Norte", "Drogaria Catarinense Floresta") também são reconhecidas: Raia, Drogasil, Pague Menos, Nissei, Panvel, Catarinense, São João e FarmaSesi.

## 0.14.3

- **Mais lojas do Google.** Além das 20 lojas mais perto de cada tipo, o Encontrar lojas procura também por "farmácia", "drogaria", "supermercado", "mercado" e "pet shop" no Google Maps, página a página, até a distância escolhida. Entram lojas que antes ficavam de fora, como a Drogaria Drogão.
- **Site das lojas que o mapa trouxe sem site.** Quando a loja veio só do OpenStreetMap, o app pergunta ao Google o site dela (como a Farmácia Fique Bem). A resposta fica guardada por 30 dias, para não gastar a cota do Google.
- Nomes em maiúsculas no Google aparecem normais ("DROGARIA DROGÃO JOINVILLE" vira "Drogaria Drogão Joinville").
- "Como foi testado" diz quando o site **fechou a conexão sem responder ao EconomIA** (no navegador ele abre: é a proteção do site contra programas, como acontece com a Droga Raia). Nos outros erros, mostra o detalhe técnico, para dar para entender o que houve.

## 0.14.2

- No **Encontrar lojas**, o site que tinha falhado é testado de novo na hora, em vez de esperar o dia seguinte.

## 0.14.1

- "Como foi testado" diz por que o site não respondeu: recusou o acesso de programas (erro 403), demorou demais, erro de conexão segura, endereço não encontrado ou outro erro. Antes aparecia só "não respondeu".

## 0.14.0

- **Encontrar lojas testa o preço de cada loja.** Depois de achar as lojas no mapa, o app tenta, sem IA, um preço de exemplo em cada loja que você acompanha (leite nos mercados, dipirona nas farmácias, ração nos pet shops). A loja mostra de onde dá para tirar preço: **Preço pelo site**, **Preço pelas páginas do site**, **Folheto da semana**, **Tem folheto**, **Só com IA** ou **Sem fonte de preço**, com um exemplo ("ex.: Leite Integral Tirol 1L por R$ 4,89").
- **Como foi testado**: cada loja tem o passo a passo do teste, com ✓ e ✗. Por exemplo: o site não respondeu, o site pede para programas não consultarem, o site não publica a lista de produtos, não há folheto no Kimbino nem no Seus Folhetos. Assim dá para ver o que funcionou e o que não funcionou em cada uma.
- O andamento aparece no Onde ("Testando o preço de cada loja: Farmácia Nissei (3 de 12)…"), e no fim um resumo: quantas têm preço direto do site, quantas com folheto, quantas só com IA.
- O resultado do teste fica guardado (`fontes_preco.json`) e continua aparecendo depois das buscas.

## 0.13.9

- Loja registrada pelo **Encontrar lojas** aparece com "Preços na próxima busca", e não mais "Sem preços", até a busca rodar. Ela também não entra no aviso "Sem preços de" das Ofertas.
- Depois de Encontrar lojas, a mensagem traz o atalho **Buscar preços agora**.

## 0.13.8

- **Preço sem IA também nas farmácias de rede.** As lojas que vieram do mapa agora trazem o site (do OpenStreetMap ou do Google), e as redes conhecidas (Pague Menos, Nissei, Drogaria Catarinense, Panvel, Raia, Drogasil, São João, Cobasi, Petz, Bistek, Fort, Atacadão) são reconhecidas pelo nome. O app testa o site de cada uma: Pague Menos usa VTEX e pode responder direto; Nissei, Drogaria Catarinense e Panvel publicam a lista de produtos e são lidas pelas páginas de produto, uma vez por dia. A Raia não publica a lista de produtos, então continua dependendo da busca com IA.
- **Encontrar lojas** já testa os sites das lojas achadas, em segundo plano.
- A leitura pela lista de produtos aceita sitemaps simples (Magento, WooCommerce) e lê até 6 lojas por busca.

## 0.13.7

- Em Mais › Lojas, toda loja ganha o botão **Mapa**, com o ícone de localização: abre a loja no Google Maps (pelo lugar do Google, pelas coordenadas do mapa ou pelo endereço). Loja sem endereço nem localização aparece como "Sem localização". O selo "Mapa" de origem saiu, porque agora é o botão.
- Sai o "Horário não informado" repetido nas lojas.

## 0.13.6

- Sai a palavra "raio" da tela: o botão agora é só **Encontrar lojas**, e os textos falam em "lojas perto de casa".

## 0.13.5

- **Encontrar lojas no raio**, em Mais › Casa › Onde: lê o mapa (OpenStreetMap e, com chave, Google Maps) na hora e registra as lojas do raio em Mais › Lojas, sem buscar preços e sem IA. Funciona antes da primeira busca e usa a distância escolhida, mesmo antes de salvar.
- Chave guardada aparece preenchida (••••) e com o selo **Guardada** (senha da Shopee e chave do Google). Tocar no campo limpa para colar outra.
- Sai o rodapé "Preço do site pode ser diferente do preço na loja".
- O andamento da busca não mostra mais "(0 de 4)" nas etapas sem IA, e os nomes ficam no formato "preços no site · Drogaria Catarinense".

## 0.13.4

- Com a IA desligada, o passo a passo da busca (fim de Mais › Lojas) não diz mais que a IA lê os folhetos: a etapa vira **Folhetos já lidos**, explicando que só entram os que foram lidos com a IA ligada, e a nota final diz como ligar a IA.

## 0.13.3

- Com a IA desligada, o **Buscar** também atualiza as **lojas do raio pelo mapa** (OpenStreetMap e Google Places). Antes o mapa só entrava na busca com IA, e por isso a Farmácia Medfarma Popular não aparecia em Lojas.
- Sem IA e sem nenhum preço dos sites, a busca não dá mais erro: ela atualiza as lojas e avisa.
- O resultado da busca (concluída ou com erro) aparece como aviso em qualquer tela, não só em Ofertas, e avisos longos ficam mais tempo na tela.
- A barra lateral do computador mostra a versão certa.

## 0.13.2

- Com **Usar IA** desligado, somem também o que só funciona com IA: em Opções, a leitura de folhetos novos, a busca dos itens sem preço e o encarte do site; em Lojas, Compras online (marketplaces, assinaturas e mercados que entregam, que a busca com IA procura); em Integrações, os sensores de uso da IA; e, no passo a passo da busca, as etapas com IA. Ficam a busca direta nas lojas, a Shopee, o Google Places e os folhetos já lidos.

## 0.13.1

- **Lojas do raio pelo mapa.** As lojas perto de casa vêm da localização da zona Casa do Home Assistant e do OpenStreetMap, com endereço e distância certos, e de rede entra a filial mais perto. Antes, era a IA que estimava, e por isso aparecia a Droga Raia da Getúlio Vargas em vez da que fica do lado de casa, e a Farmácia Preço Popular ficava de fora. A IA recebe a lista pronta e só procura os preços. O mapa é atualizado uma vez por semana.
- **Google Places (opcional)**, em Mais › Integrações: com uma chave, o app usa também o Google Maps para achar as lojas pequenas que o OpenStreetMap não tem.
- **Folheto automático**: sai o quadro "Folhetos de encarte". Toda loja que você acompanha e que não tem preço pelo site tem o folheto da semana procurado sozinho no Kimbino e no Seus Folhetos, logo depois do site. Nomes como "Komprão Koch Atacadista" e "Atacadão Joinville" são achados como "komprao" e "atacadao". A loja mostra "Folheto da semana até 04/11".
- **Inativas**: lojas desmarcadas vão para o fim de cada grupo, num bloco "Inativas" fechado.
- **Como o EconomIA busca os preços**: o passo a passo fica no fim de Mais › Lojas.
- Loja cadastrada por você que a busca também achou aparece uma vez só, com o "remover".

## 0.13.0

- **Primeiro o que não gasta IA.** A busca começa pelo site das lojas, pela Shopee e pelos folhetos já lidos, e a IA entra por último, só para o que faltar. Ela é avisada das lojas que já têm preço e não traz esses preços de novo. O **Buscar este item** só chama a IA quando os sites trazem menos de 2 preços. Com a IA desligada, o **Buscar** continua, só com os sites, a Shopee e os folhetos guardados.
- **Busca direta para qualquer mercado**, não só Giassi e Angeloni. O app testa uma vez por semana o site de cada loja cadastrada ou achada na busca. Se for uma loja VTEX e o robots.txt permitir, ela passa a ter preço direto. Sites que não deixam programas usarem a busca, mas liberam as páginas de produto (como o do Bistek), são lidos pela lista de produtos que a loja publica no sitemap, uma vez por dia. O preço vem da página de cada produto e é o preço padrão do site.
- **Folhetos de encarte** (Mais › Lojas): para mercados sem site de ofertas, como Komprão e Atacadão, o EconomIA procura o folheto da semana no Kimbino e no Seus Folhetos. A IA lê cada folheto uma vez e os preços ficam guardados até ele vencer. Itens novos da lista são casados com as ofertas do folheto pelo nome, sem IA. Quando a loja tem muitos folhetos regionais, a IA olha só as capas e escolhe os que valem para a sua cidade. O aviso **Sem preços de** ganhou **Ler folheto**.
- **Shopee Afiliados** (Mais › Integrações): com o App ID e a senha da Open API, os preços da Shopee vêm direto da Shopee, sem IA. As chaves ficam em `segredos.json` e a senha não volta para o painel.
- **Mercados da região que entregam**: mercados fora do raio que entregam no seu CEP, como o Bistek, entram em Online, separados dos marketplaces (no filtro e em Mais › Lojas). Quando o site só mostra a taxa no carrinho, o preço aparece com "+ frete", e o app avisa para conferir o frete antes de decidir.
- **De quando é cada preço**: o cartão mostra "preços de hoje 07:22". Preço que veio da busca na web aparece como "visto pela busca na web, confira no link". Na Amazon e nos marketplaces, a IA passa a usar o preço da página do produto, não o do Google Shopping.

## 0.12.1

- **Encarte ou print de preços**, nas Ofertas: mande fotos ou prints do encarte (do WhatsApp, do Tiendeo, do app da loja ou da gôndola), diga de qual loja é e toque em **Ler com IA**. As ofertas entram com o rótulo "Encarte" e os preços que batem com a sua lista entram na comparação e no roteiro, sem apagar o resto da busca. Serve para mercados sem site de ofertas, como Koch, Komprão e Atacadão.
- O aviso **Sem preços de** das Ofertas ganhou o atalho **Mandar encarte**.

## 0.12.0

- **Busca direta nas lojas**: o **Giassi** e o **Angeloni** respondem direto pelo próprio site, com o preço da loja que atende o seu CEP, o link do produto e as promoções (preço "de" e "por"). Não precisa de login nem gasta IA, e o preço do site vale mais que o que a busca na web achou. Entra na busca e no **Buscar este item**.
- Em **Mais › Opções › Busca de preços**, a chave **Busca direta nas lojas** (ligada) mostra qual loja de cada rede atende o seu CEP (por exemplo, "Angeloni João Colin").
- Os produtos achados entram com marca e tamanho ("JIMO 100 ml"), e pacotes ("Leite 1L Caixa com 12") contam a quantidade total na comparação por litro ou quilo.
- O mesmo mercado com nomes diferentes ("Giassi" e "Giassi Supermercados") vira uma loja só.

## 0.11.7

- **Arrastar para o lado** troca de aba no celular, como nos outros apps: Minha lista ⇄ Roteiro ⇄ Ofertas ⇄ Mais, com a tela nova entrando pelo lado. Não vale começando na borda da tela (é o Voltar do celular), num campo, numa fileira que rola para o lado (como as abas de Mais) nem no computador.

## 0.11.6

- O **ícone do app** ao lado do nome, no alto da tela e na barra lateral do computador, como no InventarIA, no GerencIA, no ResolvIA e no CronologIA: o cupom fiscal com %, na cor escolhida em Aparência.

## 0.11.5

- A arrumação em colunas vale para o app todo:
  - **Ofertas**: Farmácias, Mercados, Pet shops e Online dividem a largura em partes iguais, e o filtro de lojas fica em colunas.
  - Os quadros do alto das Ofertas ficam lado a lado no celular; quadro sem nada (sem cupom, sem destaque) some, e **Escondidas pelo perfil** virou uma faixa fina.
  - **Outros preços** do cartão preenchem a linha toda, sem cortar o preço.
  - **Roteiro**: Paradas e O que comprar ocupam a largura toda.
  - **Onde**: CEP, distância e Salvar numa linha; o que acompanhar em duas colunas.
  - **Uso da IA**: os tipos de chamada em colunas.

## 0.11.4

- Saem os textos antigos de "depois do login" nos cupons: os cupons do app da loja entram pelo print (Mais › Lojas › Cupons do app) e o preço de clube pelo **Sou do clube**.

## 0.11.3

- **Opções em grade**: restrições, interesses, nunca mostrar, onde procurar online e assinaturas viram botões do mesmo tamanho em colunas que ocupam a largura toda (duas no celular, mais no computador), sem sobra no fim das linhas. Os dias de mercado e de farmácia ficam numa linha só.

## 0.11.2

- No cartão de cada item, o que fica à mostra é a **Melhor compra** (ou o Mais barato) e os outros preços. Comprar online ou na loja, o melhor tamanho e a comparação de tamanhos ficam juntos em **Online e tamanhos**, recolhido como o Comparar tamanhos. Aberto, continua aberto quando a lista atualiza.
- Ícones em **Comprei hoje** e **Buscar este item**.

## 0.11.1

- **Escolher fotos, Colar mensagem e Falar numa linha só**, em quadrinhos com o ícone em cima.
- Os cartões da lista não repetem mais o mesmo texto: "Toque em Comprei hoje..." e "Os preços aparecem depois da próxima busca" aparecem uma vez só, acima da lista, e só quando valem para algum item.

## 0.11.0

- **Falar**, como no GerencIA, no ResolvIA, no CronologIA e no InventarIA: o microfone no alto da tela, à direita (e em Minha lista › Falar). Fale os itens; o Home Assistant transcreve com a fala para texto do assistente de voz (com o Home Assistant Cloud já vem pronta) e a IA separa os itens para você conferir e adicionar. Até 2 minutos por vez. O Uso da IA conta o Falar como um tipo próprio.
- **No computador** (tela de 1000 pixels ou mais), como nos outros apps: barra lateral com as telas, o número de itens acabando, **Buscar ofertas** e as ofertas por tipo de loja; no alto à direita, **Falar**, **Ler com IA** e **Adicionar item**; seções direto na página, com título grande e ícone; o cupom de economia ao lado das oportunidades. No celular nada muda.
- **Mais em abas**, presas no alto: Casa, Lojas, Integrações, Dados, Aparência e Opções. Cada seção ganhou um ícone no título.
- **Usar IA**, em Mais › Integrações: desligado, somem o Buscar, a leitura de fotos e mensagens, os cupons por print e o Falar, para todos os aparelhos.
- **Sensores no Home Assistant** agora é uma opção e vem **desligada**. Desligada, o app apaga o `sensor.economia_ia_hoje` que a 0.10.5 criou sem perguntar.
- **Opções**: ligar ou desligar a busca extra dos itens sem preço e a leitura automática de encartes, para gastar menos da cota da IA.
- **Versões anteriores**, em Mais › Dados: o app guarda uma cópia da lista, do perfil e dos ajustes a cada 10 minutos de uso e antes de importar, restaurar ou limpar a lista, e fica com as 3 mais recentes, cada uma com **Restaurar**.
- **Exportar** em linhas, com o arquivo de cada uma e o botão Baixar, e as **ofertas da última busca** em JSON.
- **Aparência** como nos outros apps: o tema em três botões com ícone e a cor do app em etiquetas com nome.
- Corrige a leitura dos cupons por print, que caía na leitura de itens da lista.

## 0.10.5

- **Uso da IA** em Mais: chamadas de hoje, dos últimos 7 dias e do mês, gráfico por dia, tipo de uso (busca, itens sem preço, encartes, fotos, cupons, testes), erros e cota excedida, e as últimas chamadas com tempo e tokens estimados.
- Sensor **sensor.economia_ia_hoje** no Home Assistant, com as chamadas de hoje e os detalhes nos atributos, para painel e automação.
- A mensagem do fim da busca diz quantas chamadas de IA ela usou.
- Atalho para o painel de consumo do provedor (Google Cloud Console, OpenAI ou Claude Console).

## 0.10.4

- **Melhor tamanho** também considera embalagens menores: um pote de 700 g a R$ 34,27/kg ganha do pacote de 1 kg a R$ 47,30/kg ("Compensa o menor").
- **Compensa pedir online?** compara com a melhor compra por quilo ou litro, não só com o tamanho de sempre.

## 0.10.3

- **Abrir na loja**: toque no preço mais barato, na melhor compra, nos outros preços ou em Comparar tamanhos para abrir o anúncio (por exemplo, no Mercado Livre). Quando a busca não trouxe o link, o botão vira **Procurar** e abre a busca do produto na loja.
- A busca pede o link da página do produto, não da loja.

## 0.10.2

- **Itens sem preço**: no fim da busca, o app faz uma pergunta só sobre os itens que ficaram sem preço, procurando item por item. Em item genérico, como "Pó lava louça", a IA escolhe as marcas mais vendidas e o cartão mostra qual produto é.
- Botão **Buscar este item** no cartão sem preço, que procura só aquele item em cerca de 1 minuto.
- Preço que veio sem link ou sem o valor "de" passa a valer: aparece como **Preço atual** nas Ofertas.
- Os itens vão numerados para a IA, então nome escrito diferente não perde mais o preço. Preço escrito como "R$ 12,90" também é lido.
- A linha da última busca diz quantos itens ficaram sem preço, e o registro do app mostra o que veio de cada categoria e o que foi descartado.

## 0.10.1

- Novo ícone e logo: o cupom fiscal da abertura.
- Página do repositório com imagens, no mesmo padrão dos outros apps.
- Descrição da opção de tarefa de IA nas configurações do app.

## 0.10.0

- **Encarte do site**: em Adicionar loja, informe o site de ofertas. Na busca, o app abre a página, baixa o encarte (imagens ou PDF) e a IA de fotos lê produto, preço e validade.
- A busca inclui mercadinhos do raio. Se achar o site de uma loja sem preço, tenta ler o encarte sozinha (até 2 por busca).
- Selo **Sem preços** em Lojas, com **Adicionar site de ofertas**, e aviso nas Ofertas.
- **iFood e Rappi** como canais online, com a taxa de entrega somada, e **Clube iFood** como assinatura.

## 0.9.4

- A abertura virou um **cupom fiscal** saindo da impressora, com os itens que mais economizam.
- Erro de cota da IA (429): mensagem clara e nova tentativa depois de 1 minuto.

## 0.9.3

- Tipografia Barlow e Barlow Condensed, embutida no app para funcionar sem internet.

## 0.9.2

- **Cor do app**: 10 cores em Mais → Aparência.
- A resposta da IA é lida mesmo quando vem em formatos diferentes.

## 0.9.1

- Quando a IA responde fora do formato, o app mostra o que ela disse.

## 0.9.0

- **IA do Home Assistant** em Mais: escolha a IA para buscar ofertas (tarefa de IA ou assistente de conversa, como o Gemini com Pesquisa Google) e para ler fotos, com o botão Verificar de novo.
- **Sou do clube** em cada loja: o preço de clube entra na lista, no roteiro e nas ofertas.
- **Cupons do app pelo print**: a IA lê a carteira de cupons da loja.

## 0.8.6

- Corrige "O add-on não tem acesso ao Home Assistant".

## 0.8.0 a 0.8.5

- **Melhor tamanho** com preço por litro, quilo ou unidade e a melhor compra no topo do item.
- **Roteiro de compras** com até 4 paradas, em aba própria.
- **Itens por foto ou mensagem**, com várias fotos antes de digitalizar.
- Adicionar no topo da lista e **Limpar lista** com desfazer.
- Oportunidades em lista alinhada e frete grátis explicado.

## 0.7.0

- Compras online (Mercado Livre, Amazon e outros) com frete e prazo para o seu CEP.

## 0.6.0

- Lista por voz com a lista de compras do Home Assistant e ícone do app.

## 0.5.0

- Botão Buscar no menu de baixo, exportação para Excel e JSON, importação e tema.
