# Mudanças

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
