# EconomIA

Cupons, ofertas e a sua lista de compras nas farmácias, mercados e pet shops perto de casa, numa página só dentro do Home Assistant.

## Antes de começar

O EconomIA usa a IA do próprio Home Assistant (Anthropic Claude, OpenAI, Google Gemini...). Escolha qual usar em **Mais › Configurações › Integrações › IA do Home Assistant** e toque em **Verificar de novo** para testar. A chave **Usar IA**, no mesmo lugar, desliga tudo o que usa IA (leitura de fotos e mensagens, cupons e encartes por print, Falar e Conversa), para todos os aparelhos. O **Buscar** continua, só com o que não gasta IA.

- **Para buscar ofertas**, a IA precisa de busca na web:
  - **Anthropic**: ligue a busca na web nas opções da tarefa de IA.
  - **Google Gemini**: a Pesquisa Google só funciona num **assistente de conversa**. Nas opções do Google Generative AI, crie ou ajuste um assistente com "Controlar o Home Assistant" em nenhum e **Enable Google Search tool** ligado, e escolha esse assistente.
- **Para ler fotos**, escolha uma tarefa de IA que aceite imagens (Google AI Task e Anthropic aceitam).

## Como usar

1. Abra **EconomIA** no menu lateral do Home Assistant.
2. Em **Mais › Casa**, preencha o CEP e a distância e toque em **Encontrar lojas**: o app registra as lojas perto de casa pelo mapa e testa, sem IA, se dá para tirar preço de cada uma (em Mais › Lojas, cada loja mostra o resultado e o passo a passo em "Como foi testado", com **Testar agora** para testar de novo só aquela, inclusive as online; **Só sem fonte de preço** mostra só as que faltam). Preencha também quem mora na casa (incluindo quantos pets), restrições, interesses e os dias em que você costuma comprar.
3. Em **Minha lista**, adicione o que você compra sempre, pelo campo do topo, pelo **código de barras**, por **Escolher fotos**, por **Colar mensagem** ou por **Falar**. Toque em **Comprei hoje** quando comprar: o painel aprende de quanto em quanto tempo cada coisa acaba. Em cada item, o ✓ ao lado de uma loja ou de um tamanho fixa **Sua escolha** (mesmo que não seja a mais barata), que vale também no Roteiro. A "economia de" de cada item é em relação à segunda loja mais barata. Toque num preço para abrir o produto na loja (sem link, o botão **Procurar** abre a busca da loja). **Limpar lista** tira tudo da lista, com opção de desfazer. O que sai da lista (por remover ou limpar) fica no **Histórico**, o botão ao lado do Adicionar: do que você mais compra para o que menos compra, e um toque põe de volta com as compras de antes. Escrever no campo filtra o histórico.
4. Toque em **Buscar**, no centro do menu de baixo. A busca leva alguns minutos e você pode continuar usando o painel. Item que ficou sem preço tem **Buscar este item**, que procura só ele; com preço, **Buscar de novo** fica no pé do cartão.
5. Em **Ofertas**, use **Não mostrar** em qualquer oferta que não faça sentido para você: **Só esta oferta** (aquele produto naquela loja), **Nunca “palavra”** (qualquer oferta com essa palavra, em qualquer loja e tamanho, como "energético"; dá para trocar a palavra antes de esconder) ou **Nada de** uma categoria (medicamentos, bebidas alcoólicas…). As palavras e as categorias ficam em **Mais › Casa › Nunca mostrar**, onde dá para escrever outra palavra ou tirar uma com um toque. Cada oferta tem um link para a fonte e **Comparar preço**, que procura o mesmo produto nas outras lojas (outro produto parecido, como um creme de barbear no lugar de um creme 4 em 1, fica de fora) e mostra embaixo da oferta se tem mais barato (**Mais barato em outra loja**, **Menor preço entre 3 lojas** ou **Não achei em outras lojas**). Outro tamanho conta pelo preço por quilo, litro ou unidade. Primeiro procura nos sites das lojas; a IA só entra se faltar preço, e só se estiver ligada. A comparação não põe nada na Minha lista. Cada oferta também tem **Vale a pena?**, que pede à IA uma avaliação do produto. Tocar no **Destaque para você** leva até a oferta. Os botões de loja mostram só as lojas com oferta, e as lojas que você desligou (em Mais › Lojas ou nas opções de Online) não aparecem. As ofertas escondidas (pelo perfil ou pelo **Não mostrar**) ficam no fim da lista, em **Escondidas (N)**, recolhidas: um toque mostra cada uma com o motivo e o **Mostrar de novo**. Nos cupons, os vencidos ficam no fim, em **Vencidos (N)**, também recolhidos.
6. Em **Mais › Lojas**, desmarque as que não quer acompanhar ou adicione uma que não apareceu (veja **Lojas**, abaixo).

## Mais, um menu

Como nos outros apps (InventarIA, GerencIA, ResolvIA e CronologIA), **Mais** é um menu: cada linha abre a sua tela.

- **Casa**: CEP e distância, o que acompanhar, quem mora, a rotina de compras, restrições, interesses e o que nunca mostrar.
- **Lojas**: as lojas perto de casa, com o clube de cada uma, Encontrar lojas e Testar agora; cupons do app; compras online; e como o EconomIA busca os preços.
- **Configurações**, em abas: **Integrações** (na ordem dos outros apps: CorrerIA; IA do Home Assistant, com Usar IA e Para falar; Uso da IA; Shopee Afiliados, Google Places, Brave Search, Mercado Livre, Instagram e Lista do Home Assistant; e Sensores no Home Assistant), **Dados** (Exportar, Backup na pasta share, Importar, Versões anteriores, Onde ficam os dados e Começar do zero), **Aparência** (tema, cor do app e Cor do dia) e **Opções** (as **Listas** e as etapas da busca que dá para desligar). A aba escolhida fica guardada.
- **Sobre**, a última linha: CorrerIA Code, quem faz os apps, os apps da família, cada um com o link para o GitHub dele (o EconomIA marcado como **Este app**, com a versão), e **Meu GitHub**.

Numa tela de Mais, o **‹ Mais** no alto, o Voltar do celular e arrastar para a direita voltam para o menu. Aberta por um atalho de outra tela (como **Preencher o perfil**, na Minha lista), o Voltar do celular volta para onde você estava.

## Falar

O microfone fica no alto da tela, à direita (e em **Minha lista › Falar**). Fale os itens, por exemplo "leite integral, 2 pacotes de café 500 g e detergente"; o Home Assistant transcreve com a fala para texto escolhida em **Mais › Configurações › Integrações › IA do Home Assistant › Para falar** (um assistente de voz do Home Assistant ou uma entidade de fala para texto; no padrão, a do assistente de voz preferido, em **Configurações › Assistentes de voz**; com o Home Assistant Cloud já vem pronta) e a IA de "Para ler fotos" separa os itens para você conferir e adicionar, com o que foi ouvido no alto. Até 2 minutos de cada vez.

Em **Mais › Configurações › Integrações › IA do Home Assistant**, a linha **Falar** mostra se está pronto e com qual fala para texto. O microfone some com **Usar IA** desligado. No app do celular, permita o microfone para o app Home Assistant; no navegador, o Home Assistant precisa estar num endereço com https.

## Conversa com a IA

O balão ao lado do microfone abre a **Conversa**: pergunte sobre a tela aberta ("onde a compra fica mais barata?", "tem cupom bom agora?") ou sobre qualquer assunto. A IA recebe a data, a tela, quem mora na casa, a sua lista com os preços da última busca, o que você mais compra, as ofertas e os cupons das lojas que você acompanha. Ela responde em texto.

A IA não muda nada sozinha. Quando ajuda, ela sugere ações em botões: **Pôr na lista**, **Tirar da lista**, **Comprei hoje**, **Buscar o preço** e **Abrir** uma tela. Só acontece quando você toca, e o botão fica marcado. O microfone da conversa põe o que você falou na caixa, para conferir antes de enviar.

A conversa usa a tarefa de IA de "Para ler fotos" (ou a de buscar ofertas, ou a preferida do Home Assistant), nunca um assistente de conversa, que poderia mexer na casa. Em cada oferta, **Vale a pena?** abre a conversa e pede uma avaliação do produto: a IA de buscar ofertas procura na web a nota, as avaliações de quem comprou, as reclamações e o preço de costume, e começa pelo veredito (Vale a pena, Depende ou Não vale).

A conversa fica guardada neste aparelho até você tocar em **Nova conversa**. No celular ela sobe de baixo; no computador, abre numa janela no canto. Com **Usar IA** desligado, o balão some.

## No celular

Arraste para o lado para trocar de aba: Minha lista ⇄ Roteiro ⇄ Ofertas ⇄ Mais. Começando na borda da tela vale o Voltar do celular.

As caixas de seleção (como a distância ou o espaço para estoque) têm a mesma altura e os mesmos cantos dos outros campos, com a seta do app, e abrem uma janela de baixo para cima com as opções; a atual vem marcada. O Voltar do celular, o **X** ou tocar fora fecham sem mudar nada. No computador, a janela abre no meio da tela, e dá para escolher com as setas e Enter.

## No computador

Com a tela de 1000 pixels ou mais, as abas de baixo viram uma **barra lateral** com Minha lista (com o número de itens acabando), Roteiro, Ofertas, Mais, o botão **Buscar ofertas** e as ofertas por tipo de loja. No alto à direita ficam **Conversa**, **Falar**, **Ler com IA** e **Adicionar item**. As seções ficam direto na página, com título grande e ícone, e o cupom de economia fica ao lado das oportunidades. No celular e no tablet nada muda.

## Itens por foto ou mensagem

Em **Minha lista → Escolher fotos**, tire ou escolha quantas fotos precisar, até 8 (print de conversa, lista escrita à mão, embalagem que acabou). Dá para tirar uma foto da lista. Quando terminar, toque em **Digitalizar com IA**: a IA do Home Assistant devolve os itens, você confere, ajusta o nome se quiser e adiciona. Se a lista veio em texto, use **Colar mensagem**.

Para ler fotos, a IA escolhida precisa aceitar imagens (a Anthropic aceita). A foto fica um instante na pasta de mídia do Home Assistant, só para a IA ler, e é apagada em seguida.

## Listas prontas

Ligue em **Mais › Configurações › Opções › Listas** (vem desligado). No alto da Minha lista aparece uma barra com **Todas**, cada lista (com quantos itens tem) e **+ Nova**: crie, por exemplo, **Compra semanal** e **Compra mensal**, e troque de uma para outra com um toque. A lista aberta fica guardada no aparelho.

- Continua uma lista só de produtos, com os preços e o histórico de cada um; as listas dizem o que entra em cada compra. Um item pode estar em mais de uma.
- A tela toda segue a lista aberta: os itens, o Cupom de economia e as oportunidades.
- O que você adiciona com uma lista aberta entra nela. Um item que já está em Todas também: é só escrever o nome (ele aparece nas sugestões). Em Todas, cada item mostra o nome de cada lista: um toque põe ou tira o item dela.
- Numa lista, **tirar desta lista** tira o item só dela, e ele continua em Todas; **Limpar lista** fica só em Todas.
- **Renomear** e **Apagar lista** ficam embaixo da barra, com a lista aberta. Apagar uma lista não apaga os itens.
- No **Roteiro**, escolha quais listas entram: **Todas**, ou uma ou mais listas.
- Desligar a opção esconde as listas, sem apagar: ligue de novo e elas voltam.

## Quantidade

No começo dos botões de cada item, **−** e **+** escolhem quantas unidades você leva (de 1 a 99). O preço mostra o total e quanto sai cada uma ("R$ 163,80 · 2 × R$ 81,90"), e a economia, o Cupom de economia do Início e o Roteiro contam a quantidade. O melhor tamanho também: levando 2 de 1 kg, o pacote de 2 kg dura o mesmo que a sua compra de sempre. Quando a sua escolha é uma embalagem (um fardo, um galão), ela vale como está. A quantidade vai junto no Exportar e volta no Importar.

## Lista completa ou resumida

Acima dos itens, escolha **Completa** (cada item com o cartão inteiro: os preços das lojas, os tamanhos, os similares) ou **Resumida** (uma linha por item: o nome, o preço escolhido e onde comprar). O preço da resumida é a sua escolha, a melhor compra (quando compensa outro tamanho) ou o mais barato; o ponto colorido marca o que está acabando. Toque numa linha para abrir o cartão ali mesmo e no nome dele para fechar. A escolha fica guardada no aparelho.

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

## Compra rápida

Para quando precisa de umas coisas agora, sem planejar: no **Roteiro**, escolha **Compra rápida** e escreva cada item (as sugestões trazem os da sua lista e os nomes das lojas). Os itens não entram na lista e ficam guardados no aparelho até você tirar.

- **Onde comprar**: uma loja física só, a mais perto que tem tudo. Se outra loja com os mesmos itens sair bem mais barata (pelo menos R$ 5 e 10% a menos), ela vira a recomendada, e o app diz quanto economiza indo mais longe. Lojas online ficam de fora.
- O preço de cada item na loja, **Como chegar** (a rota no Maps de onde você está) e, se a loja não tiver tudo, o que falta lá e onde tem.
- **Compare**: as outras lojas, com o total e quantos itens faltam em cada uma. Um toque mostra a loja.
- Item ainda **sem preço**: **Buscar preços** procura só esses (até 8), só nas lojas físicas. Com todos com preço, **Buscar de novo** atualiza.
- Um toque no item tira ele; **Limpar** tira tudo.

## Como o item da lista acha o produto

O EconomIA lê o nome dos produtos como o varejo escreve: tipo, marca, variante e tamanho ("Álcool Araras Bactericida Eucalipto 1L"). O tipo (a primeira palavra do item, como "álcool" ou "leite") e a marca precisam estar no nome. Uma palavra que a loja não usa em nenhum produto daquele tipo, como "perfumado" entre os álcoois, vale pelas palavras que andam junto dela nos produtos que as lojas já mostraram (lavanda, eucalipto…); o app aprende isso sozinho, dos catálogos e das buscas. Uma palavra que a loja usa, como "integral" entre os leites, tem de estar no nome. Quando acha o produto com certeza, o app guarda o código de barras e reconhece o mesmo produto em outra loja, mesmo com outro nome. Se um item continuar sem preço, escreva como na embalagem: tipo, marca e tamanho.

Antes de valer, cada produto é conferido. Nas lojas com busca no site, pela seção onde a loja o cadastrou: a carne moída fica no Açougue, e a almôndega em Congelados não entra. Com o Mercado Livre ligado (veja abaixo), também pela categoria que ele daria ao produto: hambúrguer não é carne moída.

Aceita mais de um produto? Escreva com "ou": "Coxinha da asa ou asinha" busca os dois e fica com o mais em conta.

### Código de barras

Toque no botão de código de barras, ao lado do Adicionar, e em **Tirar foto**: a câmera abre aqui dentro, em tela cheia, e lê o código sozinha quando ele entra no quadro (ou toque no botão do meio para tirar a foto). Também dá para digitar os números que ficam embaixo dele. A câmera só abre com o Home Assistant num endereço com https (como o do Home Assistant Cloud) ou no app do celular; sem isso, o app explica e abre a escolha da foto. O EconomIA procura o produto nas lojas com busca no site e, se não achar, no Open Food Facts. Confira o nome e toque em **Pôr na lista**. O item fica com o código, o que ajuda a achar exatamente o mesmo produto nas lojas, mesmo com outro nome. Código de balança ou da própria loja (os que começam com 2) só vale naquela loja.

### Sugestões ao digitar

A partir de 2 letras, o nome do item mostra sugestões logo abaixo: primeiro o que já esteve na sua lista (do que você mais compra para o que menos compra), depois os nomes que as lojas usam, sem marca e sem tamanho, do mais comum para o menos comum. "arroz" sugere *Arroz branco*, *Arroz integral*, *Arroz parboilizado*…; "sab" sugere *Sabonete*, *Sabão*, *Sabão em pó*… Toque numa para pôr no campo e, se quiser, complete com a marca ou o tamanho. Os nomes vêm dos produtos que as lojas já mostraram nas buscas: quanto mais você busca, mais sugestões aparecem.

### Quis dizer…?

Se uma palavra do item não aparece em nenhum produto que as lojas já mostraram, o EconomIA sugere a mais parecida ("Álcool de lompeza" → "Álcool de limpeza"). Toque na sugestão para trocar. Se você não trocar, a busca tenta o nome corrigido sozinha quando o escrito não acha nada.

### Similares

Toque em **Similares** no item para ver até 3 produtos parecidos, da mesma seção da loja, que saem mais em conta pelo preço do quilo ou do litro: para "coxinha da asa", sobrecoxa, asa ou frango inteiro. O preço do item continua o mesmo. Se preferir um similar, toque no ✓ dele: vira a sua escolha, também no Roteiro. Os similares vêm das lojas com busca no próprio site (como Giassi e Angeloni) e aparecem na busca seguinte, com a **Busca direta nas lojas** ligada em Mais › Configurações › Opções.

## Clubes e cupons

Em **Mais › Lojas**:

- Cada loja tem o botão do clube: o nome do clube quando o EconomIA conhece (como Amigo Giassi), **Tem clube** quando a busca achou um, ou **Adicionar clube**. Toque nele nas lojas em que você é cadastrado (quase sempre é só o CPF no caixa) e ele vira **Sou do clube**. O preço de clube dessas lojas passa a valer na lista, no roteiro e nas ofertas, e a busca com IA procura o preço de membro delas. Nas outras, o preço de clube aparece marcado e o EconomIA avisa quando valeria a pena entrar no clube. Clube só de pontos ou cartão (como o Clube Angeloni) não muda o preço da prateleira e não aparece. O preço de clube chega pela IA (busca, encarte ou print dos cupons): com a IA desligada, a tela avisa.
- Em **Cupons do app**, escolha prints da carteira de cupons do app da loja (Bem Panvel, Raia, Meu Atacadão...) e toque em **Digitalizar com IA**. Confira a loja de cada cupom e guarde: eles aparecem em Ofertas como **Seu cupom** e na abertura quando estiverem perto de vencer.

O EconomIA não entra na sua conta das lojas: esses apps não têm acesso aberto e pedem código por SMS.

## Mercadinhos e encartes no site

A busca na web lê texto; muitos mercados do bairro publicam as ofertas como **imagem de encarte** no site. Por isso:

- A busca procura também mercadinhos e lojas independentes perto de casa. Se achar o site de uma loja sem nenhum preço, o EconomIA abre o site, baixa o encarte e a IA de fotos lê os preços (até 2 lojas por busca).
- Loja que continua sem preço aparece com o selo **Sem preços** em Mais › Lojas e um aviso nas Ofertas. Toque em **Adicionar site de ofertas** e cole o endereço da página do encarte (por exemplo `mercadosalles.com.br/ofertas`): a partir da próxima busca, o encarte é lido sempre.
- Também dá para informar o site ao adicionar uma loja que não apareceu, no fim de Mais › Lojas.
- Mercado sem site de ofertas (Koch, Komprão, Atacadão): nas Ofertas, toque em **Encarte ou print de preços**, escolha as fotos ou prints do encarte (até 8: do WhatsApp, do Tiendeo, do app da loja ou da gôndola), diga de qual loja é (as lojas do tipo da aba aparecem logo abaixo do campo: toque numa para preencher) e toque em **Ler com IA**. Os preços valem até a próxima busca.

As ofertas de encarte aparecem com o rótulo "Encarte" e a validade, e os preços entram na comparação da lista e no roteiro.

## Primeiro o que não gasta IA

A busca começa pelo que não gasta IA e só chama a IA para o que faltar (o passo a passo também está no fim de Mais › Lojas):

1. **Lojas perto de casa, pelo mapa.** A localização da zona Casa do Home Assistant e o OpenStreetMap dizem quais farmácias, mercados e pet shops existem perto, com endereço e distância certos (de rede, a filial mais perto). Com uma chave do Google Places em Mais › Configurações › Integrações, entra também o Google Maps, que tem as lojas pequenas e o site de cada uma. Atualiza uma vez por semana e quando você toca em Encontrar lojas.
2. **Site das lojas sem site.** Pelo Brave Search (com chave, em Mais › Configurações › Integrações) e, com a IA ligada, pela busca na web da IA. Uma vez por mês.
3. **Site da loja.** O site de cada loja cadastrada ou achada na busca é testado uma vez por semana. Se a loja usa VTEX e o robots.txt permite, o preço vem direto da loja que atende o seu CEP (Giassi, Angeloni e outros).
4. **Busca do site.** A página de resultados da busca da própria loja, como a da Cobasi.
5. **Páginas de produto.** Se o site não deixa programas usarem a busca, mas libera as páginas de produto (como o Bistek), o EconomIA baixa uma vez por dia a lista de produtos que a loja publica, acha os itens da sua lista pelo nome e lê o preço na página de cada produto. Esse é o preço padrão do site, que pode variar de loja para loja.
6. **Página de ofertas do site.** Loja pequena que mostra os produtos com preço na própria página (como a Drogaria Floresta) tem o preço lido dali, no máximo a cada 12 horas.
7. **Shopee**, pela Open API do Shopee Afiliados, se você ligou em Mais › Configurações › Integrações.
8. **Folheto da semana** e **Instagram** das lojas que você acompanha e que não têm preço pelo site (veja abaixo). A IA lê cada um uma vez.
9. **IA**: busca na web com a lista de lojas do mapa, para ofertas, cupons, marketplaces e os preços que faltam, avisada das lojas que já têm preço. Depois, o encarte do site das lojas que você cadastrou e uma última pergunta só sobre os itens sem preço.

Com a IA desligada, o Buscar faz só o que não usa IA e aproveita os folhetos já lidos. O EconomIA respeita o robots.txt de cada site e não dribla bloqueio.

## Folhetos de encarte

Toda loja que você acompanha e que não tem preço pelo site, como Komprão e Atacadão, tem o folheto da semana procurado sozinho no Kimbino, no Portafolhetos, no Seus Folhetos e no Catálogos Ofertas (que tem o da Droga Raia e de outras redes), logo depois do site. Não precisa configurar nada (dá para desligar em Mais › Configurações › Opções). Até 3 lojas com folheto novo por busca. A IA de fotos lê cada folheto uma vez, e as ofertas ficam guardadas até ele vencer. Os itens da sua lista que aparecem no folheto ganham preço, inclusive os que você adicionar depois, sem IA. Quando a loja tem vários folhetos regionais (o Atacadão tem um por região), a IA olha só a capa de cada um e escolhe os que valem para a sua cidade.

## Instagram (opcional)

Muito mercado do bairro posta o encarte da semana só no Instagram. Com a integração ligada, o EconomIA olha os posts das lojas que você acompanha pela API oficial do Instagram (Business Discovery). Post de oferta dos últimos 8 dias (pela legenda: "ofertas", "promoção", "válidas", "fim de semana", "R$"…) é lido uma vez pela IA de fotos, e os preços ficam guardados até a validade do encarte. Raspar o Instagram sem a API não é permitido pelas regras dele, por isso precisa da chave.

O que precisa, uma vez:

1. **Conta profissional no Instagram.** No app do Instagram: perfil › ☰ › Tipo de conta e ferramentas › Mudar para conta profissional › Criador (ou Empresa). Pode ser a sua conta ou uma conta nova só para isso.
2. **Página no Facebook ligada a ela.** No Facebook, crie uma página (pode ser vazia, por exemplo "EconomIA da Ana"). Nas configurações da página, em Contas vinculadas › Instagram, conecte a conta do passo 1.
3. **App da Meta.** Em developers.facebook.com › Meus apps › Criar app, escolha o uso "Outro" e o tipo "Empresa". O app fica em modo de desenvolvimento, só para você; não precisa de análise da Meta.
4. **Chave de acesso.** No Explorador da Graph API (developers.facebook.com/tools/explorer), escolha o app, peça um token de usuário com as permissões `pages_show_list`, `pages_read_engagement`, `instagram_basic`, `instagram_manage_insights` e `business_management`, toque em Gerar e marque a página e a conta do Instagram.
5. **Chave que dura.** A chave do Explorador vale umas horas. No Depurador de token (developers.facebook.com/tools/debug/accesstoken), cole a chave e toque em "Estender token de acesso": ela passa a valer 60 dias. Para uma chave que não vence, crie um usuário do sistema em business.facebook.com › Configurações do negócio › Usuários do sistema, dê a ele a página e a conta do Instagram, e gere a chave com validade "Nunca" e as mesmas permissões, mais `ads_read` (a Meta pede essa a mais quando a página foi dada pelo Gerenciador de Negócios).
6. Em **Mais › Configurações › Integrações › Instagram**, cole a chave e toque em **Salvar e testar**. O teste acha a sua conta do Instagram sozinho e diz até quando a chave vale.

O Instagram de cada loja vem do mapa ou de você: em Mais › Lojas, toque em Adicionar site de ofertas (ou Trocar site) e escreva o @ da loja. Só contas comerciais ou de criador podem ser lidas pela API; se a loja tiver perfil pessoal, o "Como foi testado" avisa. A chave fica em `segredos.json` e nunca volta para a página. Ler o encarte precisa da IA e dos **Folhetos** ligados (Mais › Configurações › Opções).

## Google Places (opcional)

O OpenStreetMap é gratuito, mas pode não ter as lojas pequenas do bairro. Em **Mais › Configurações › Integrações › Google Places**, cole uma chave da Places API (New), criada em console.cloud.google.com › APIs e serviços. O Google pede cartão cadastrado e dá uma cota gratuita por mês; o EconomIA consulta uma vez por semana e quando você toca em Encontrar lojas: as lojas mais perto de cada tipo, a busca por "farmácia", "supermercado"… e o site das lojas que vieram sem site (guardado por 30 dias). São algumas dezenas de pedidos por vez, o que cabe na cota gratuita no uso normal. A chave fica em `segredos.json`.

## Brave Search (opcional)

Acha o site das lojas que o mapa trouxe sem site, sem IA: o EconomIA busca "nome da loja + cidade" e fica com o primeiro resultado que é o site da própria loja (pula redes sociais, guias, marketplaces e sites de encartes). O site achado é testado na hora. Em **Mais › Configurações › Integrações › Brave Search**, cole uma chave grátis (2.000 buscas por mês), criada em api-dashboard.search.brave.com, e toque em **Salvar e testar**. O app faz uma busca por segundo, só para as lojas sem site, e guarda a resposta por 30 dias. Com a IA ligada, ela procura só as lojas que o Brave não achou. A chave fica em `segredos.json`.

## Lojas

Em **Mais › Lojas**, as lojas ficam em abas: **Farmácias**, **Mercados**, **Pet shops** e **Online**. **Procurar loja na lista** acha uma loja pelo nome em todas as abas, também nas Inativas.

- **De onde vem o preço:** o **Encontrar lojas** testa, sem IA, cada loja que você acompanha, e ela mostra o resultado: **Preço pelo site**, **Preço pela busca do site**, **Preço pelas páginas do site**, **Preço pela página do site**, **Folheto da semana**, **Encarte do Instagram**, **Preço pela busca da IA** ou **Sem fonte de preço**, com um exemplo. Quando o site da loja barra programas (como a Droga Raia, com erro 403), o EconomIA não força a entrada: o preço vem da busca na web da IA, que pesquisa em seu nome, como o Google e o Claude fazem. **Como foi testado** mostra o passo a passo, com ✓ e ✗. **Testar agora** testa de novo só aquela loja, sem o que ficou guardado. **Só sem fonte de preço** mostra só as que faltam.
- **Inativas:** desmarque a loja que não quer acompanhar. Ela vai para um bloco fechado no fim de cada grupo e sai das ofertas, do roteiro e da procura de folhetos. Dá para testar e marcar de novo.
- **Sem localização:** loja sem endereço no mapa (adicionada à mão ou que veio só de um site, como a Cobasi) fica em Online e conta como loja online. Com a chave do Google, o Encontrar lojas procura onde ela fica (a filial mais perto, até 20 km).
- **Loja que não apareceu:** no fim da lista, escreva o nome, escolha o tipo e, se quiser, o site de ofertas, e toque em **Adicionar**.

## Mercado Livre: categorias (opcional)

Confere se o produto achado é mesmo o item da lista, pela categoria que o Mercado Livre daria a ele. É grátis e não lê nada da sua conta: o EconomIA só pergunta a categoria de nomes de produto.

1. Em developers.mercadolivre.com.br, entre com sua conta e crie uma aplicação (Minhas aplicações › Criar aplicação).
2. Em **URI de redirect**, ponha `https://www.google.com`. Se aparecer a permissão **offline_access**, marque: é ela que deixa o EconomIA renovar o acesso sozinho.
3. Em **Mais › Configurações › Integrações › Mercado Livre**, cole o App ID e a Chave secreta, com a mesma URL de retorno, e toque em **Salvar**.
4. Toque em **Autorizar no Mercado Livre** e aceite. A página que abrir tem `code=TG-…` no endereço: copie o endereço inteiro, cole no EconomIA e toque em **Conectar**. O código vale só alguns minutos.

O App ID, a chave e o acesso ficam só no Home Assistant, em `segredos.json`.

## Shopee Afiliados

Em **Mais › Configurações › Integrações › Shopee Afiliados**, informe o App ID e a senha (Secret) da Open API, que você pega em affiliate.shopee.com.br › Open API. Toque em **Salvar e testar**. A partir daí, os preços da Shopee vêm direto da Shopee, sem IA, com o link do produto. A Shopee não informa o frete antes do carrinho, então o preço aparece com "+ frete". As chaves ficam só no Home Assistant, em `segredos.json`, e a senha não aparece de novo no painel.

## Compras online

A aba **Online** compara iFood, Rappi, Mercado Livre, Amazon e outros que você marcar em **Mais › Lojas › Compras online**. Marque também as assinaturas que dão frete grátis (Amazon Prime, Meli+, Clube iFood). Compras online aparece com **Online** marcado em Mais › Casa.

- **iFood e Rappi**: trazem os preços dos mercados, farmácias e pet shops do bairro no app, com a taxa de entrega somada. O preço no app pode ser maior que no balcão. Com Clube iFood, a taxa fica zerada nas lojas participantes; os cupons pessoais do Clube entram pelo print, em Cupons do app.

- O preço considerado é o **preço mais o frete** para o seu CEP. Kits aparecem com o preço por unidade.
- Prime e Meli+ dão frete grátis só nos produtos elegíveis (na Amazon, os com selo Prime). O frete de cada item já vem com a assinatura considerada.
- Na Minha lista, cada item mostra se **compensa pedir** ou se é melhor **comprar na loja**. Se o pedido chegaria depois de o item acabar, o EconomIA sugere comprar na loja agora e diz até quando pedir da próxima vez.
- Só entram lojas oficiais ou vendedores bem avaliados. Importados ficam marcados, e remédios de receita ficam só nas farmácias.
- **Mercados da região que entregam** (ligado em Mais › Lojas › Compras online): mercados fora do raio que vendem pelo site ou app e entregam no seu CEP, como o Bistek, aparecem em Online, separados dos marketplaces. Quando a taxa só aparece no carrinho, o preço vem com "+ frete".
- **De quando é o preço**: o cartão mostra a hora dos preços. Preço da busca na web aparece marcado para você conferir no link: a Amazon, por exemplo, muda o preço várias vezes por dia, e o Google Shopping costuma estar atrasado.

## Lista por voz

Em **Mais › Configurações › Integrações › Lista do Home Assistant**, escolha a lista de tarefas que o EconomIA deve acompanhar (por exemplo, a **Lista de compras**). A partir daí:

- O que você pedir ao Assist, como "adicione café na lista de compras", aparece na Minha lista em até um minuto.
- Marcar um item como concluído na lista do Home Assistant conta como **Comprei hoje** no EconomIA.
- O que você adicionar no EconomIA vai para a lista do Home Assistant, e os itens que estão acabando entram sozinhos (dá para desligar as duas coisas).

Também dá para usar uma lista do **Google Tasks** conectada ao Home Assistant pela integração Google Tasks. Ela é atualizada pelo Home Assistant a cada 30 minutos.

## Uso da IA e sensores

Em **Mais › Configurações › Integrações › Uso da IA**: as chamadas de hoje, dos últimos 7 dias e do mês, o gráfico por dia, o tipo de uso (busca, itens sem preço, encartes, fotos, cupons, Falar, Conversa e testes), erros e cota excedida, e as últimas chamadas. Para economizar a cota, desligue em **Mais › Configurações › Opções** a busca extra dos itens sem preço e a leitura automática de encartes.

**Sensores no Home Assistant** vem desligado. Ligado, o app cria o `sensor.economia_ia_hoje`, com as chamadas de hoje e os detalhes nos atributos; desligado, apaga o sensor.

## CorrerIA (opcional)

A **CorrerIA** é o app da família que põe os apps da casa no WhatsApp, no Claude e no Gemini. Em **Mais › Configurações › Integrações › CorrerIA**, ligue **Ligar a CorrerIA**: o EconomIA aparece sozinho na CorrerIA (o app CorrerIA precisa estar instalado no Home Assistant). Vem desligado e não depende da IA daqui.

Pela CorrerIA dá para ver a lista com o preço mais barato de cada item, perguntar onde um produto está mais barato, ver as ofertas (por tipo de loja, loja ou produto) e os cupons, pôr e tirar itens da lista e anotar compras. As mudanças seguem as mesmas regras da tela: o item tirado fica no histórico e volta com as compras. Os preços são os da última busca do app. A tela avisa "Sua lista foi atualizada pela CorrerIA", e o quadro mostra o último uso. Desligar fecha o acesso na hora.

## Dados

Em **Mais › Configurações › Dados**, na ordem dos outros apps:

- **Exportar**: a lista para Excel ou JSON e as ofertas da última busca.
- **Backup na pasta share**: **Criar backup** grava um `.zip` com a lista, o perfil, os ajustes e a última busca em `share/economia` (os 10 mais recentes), que você acessa pela rede (por exemplo com o app Samba). Os backups aparecem logo abaixo, com **Restaurar**. As chaves das integrações ficam de fora.
- **Importar**: o `.json` ou a planilha (Excel) do Exportar. Itens repetidos não duplicam, e as datas de compra novas entram.
- **Versões anteriores**: uma cópia da lista, do perfil e dos ajustes a cada 10 minutos de uso e antes de importar, restaurar, limpar a lista ou começar do zero; ficam as 3 mais recentes.
- **Onde ficam os dados**: em arquivos JSON dentro do app, no backup do Home Assistant.
- **Começar do zero**: **Apagar tudo** tira a lista, o histórico, o perfil, as lojas, os cupons e as ofertas da última busca, depois de uma confirmação em vermelho. A IA, as integrações, as opções e a cor continuam, e uma cópia fica em **Versões anteriores**.

Em **Mais › Configurações › Aparência**: o **tema** (Sistema, Claro ou Escuro) vale só para o aparelho e começa em **Sistema**, que segue o do Home Assistant. A **cor do app** vale para a casa toda, em todos os aparelhos: são as 12 cores da família (Vermelho, Coral, Laranja, Ouro, Verde, Menta, Turquesa, Azul, Índigo, Lilás, Rosa e Grafite). Com a **Cor do dia** ligada (vem assim), a cor muda sozinha todo dia, a mesma em todos os apps da família; escolher uma cor desliga. Quem tinha uma cor escolhida só no aparelho passa a ter essa cor na casa toda (Amarelo agora é Ouro, Roxo é Lilás, Magenta é Rosa e Cinza é Grafite).

Tudo o que você preenche fica guardado só no Home Assistant e entra nos backups dele.
