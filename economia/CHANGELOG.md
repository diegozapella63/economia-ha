# Mudanças

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
