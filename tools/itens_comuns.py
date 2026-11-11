"""Gera economia/app/itens_comuns.txt (1.33.0): os itens comuns de supermercado, hortifrúti, açougue, padaria, farmácia e
pet, e as marcas mais vendidas com o produto delas, a base das sugestões ao digitar um item. Um por linha, como a
sugestão aparece (só a primeira letra maiúscula, as marcas como elas escrevem), na ordem do mais comum para o menos
comum dentro de cada seção. Para mudar a lista, mude aqui e rode: python3 tools/itens_comuns.py"""
import os
import sys

S = {}


def sec(nome, *grupos):
    lst = S.setdefault(nome, [])
    for g in grupos:
        for x in g:
            if x not in lst:
                lst.append(x)


def de(base, coisas, liga="de"):
    return [f"{base} {liga} {c}" if liga else f"{base} {c}" for c in coisas]


FRUTAS = ["laranja", "uva", "maçã", "pêssego", "maracujá", "abacaxi", "manga", "goiaba", "caju", "acerola", "morango", "limão",
          "tangerina", "melancia", "melão", "graviola", "cupuaçu", "açaí", "pera", "frutas vermelhas", "coco", "mamão", "banana"]

sec("Mercearia",
    ["Arroz branco", "Arroz integral", "Arroz parboilizado", "Arroz agulhinha", "Arroz arbóreo", "Arroz japonês", "Arroz negro",
     "Arroz cateto", "Arroz 7 grãos", "Arroz basmati", "Arroz jasmim",
     "Feijão carioca", "Feijão preto", "Feijão branco", "Feijão fradinho", "Feijão vermelho", "Feijão rajado", "Feijão bolinha",
     "Feijão jalo", "Feijão azuki", "Feijão manteiguinha", "Lentilha", "Grão de bico", "Ervilha seca", "Soja em grão", "Canjica",
     "Canjica amarela", "Milho de pipoca", "Pipoca de micro-ondas", "Quinoa", "Chia", "Linhaça", "Gergelim", "Amaranto",
     "Trigo para quibe", "Cuscuz marroquino", "Flocão de milho", "Cevada",
     "Macarrão espaguete", "Macarrão parafuso", "Macarrão penne", "Macarrão talharim", "Macarrão fusilli", "Macarrão ave maria",
     "Macarrão padre nosso", "Macarrão conchinha", "Macarrão gravatinha", "Macarrão cabelo de anjo", "Macarrão de arroz",
     "Macarrão integral", "Macarrão com ovos", "Macarrão para lasanha", "Massa para lasanha", "Macarrão instantâneo", "Lámen",
     "Nhoque", "Capeletti", "Ravióli", "Massa para pastel", "Massa de pizza", "Massa folhada", "Massa para torta",
     "Farinha de trigo", "Farinha de trigo integral", "Farinha de trigo com fermento", "Farinha de mandioca",
     "Farinha de mandioca torrada", "Farinha de milho", "Farinha de rosca", "Farinha de arroz", "Farinha de aveia",
     "Farinha de amêndoas", "Farinha láctea", "Farofa pronta", "Fubá", "Fubá mimoso", "Polvilho doce", "Polvilho azedo",
     "Amido de milho", "Tapioca", "Goma de tapioca", "Sagu", "Aveia em flocos", "Aveia em flocos finos", "Farelo de aveia",
     "Granola", "Cereal matinal", "Sucrilhos", "Flocos de milho", "Mistura para bolo", "Mistura para pão de queijo",
     "Mistura para panqueca", "Fermento químico", "Fermento biológico", "Bicarbonato de sódio",
     "Óleo de soja", "Óleo de girassol", "Óleo de milho", "Óleo de canola", "Óleo de coco", "Azeite de oliva",
     "Azeite extravirgem", "Azeite de dendê", "Vinagre de álcool", "Vinagre de maçã", "Vinagre de vinho tinto",
     "Vinagre balsâmico", "Banha de porco", "Gordura vegetal",
     "Açúcar refinado", "Açúcar cristal", "Açúcar mascavo", "Açúcar demerara", "Açúcar de confeiteiro", "Açúcar orgânico",
     "Adoçante líquido", "Adoçante em pó", "Adoçante stevia", "Xilitol", "Mel", "Melado", "Rapadura", "Glucose de milho",
     "Sal refinado", "Sal grosso", "Sal marinho", "Sal rosa do Himalaia", "Sal light",
     "Café em pó", "Café torrado e moído", "Café em grãos", "Café solúvel", "Café em cápsula", "Café descafeinado",
     "Café extraforte", "Café gourmet", "Cappuccino", "Filtro de papel para café", "Achocolatado em pó", "Chocolate em pó",
     "Cacau em pó", "Chá mate", "Chá verde", "Chá preto", "Chá de camomila", "Chá de erva-doce", "Chá de hortelã",
     "Chá de hibisco", "Chá de capim-cidreira", "Chá de boldo", "Chá de frutas vermelhas", "Chá de gengibre", "Chá de canela",
     "Chá de cavalinha", "Chá de carqueja", "Chá de melissa", "Erva-mate para chimarrão", "Erva-mate para tereré",
     "Extrato de tomate", "Molho de tomate", "Molho de tomate tradicional", "Molho de tomate com manjericão", "Polpa de tomate",
     "Tomate pelado", "Molho branco", "Molho bolonhesa", "Molho pesto", "Molho shoyu", "Molho inglês", "Molho de pimenta",
     "Molho barbecue", "Molho tarê", "Molho de alho", "Molho para salada", "Maionese", "Maionese light", "Ketchup", "Mostarda",
     "Mostarda dijon", "Creme de cebola", "Caldo de galinha", "Caldo de carne", "Caldo de legumes", "Caldo de bacon",
     "Tempero completo", "Tempero para carne", "Tempero para frango", "Tempero para peixe", "Tempero baiano", "Sazón",
     "Alho triturado", "Alho frito", "Cebola desidratada", "Colorau", "Páprica doce", "Páprica defumada", "Cominho",
     "Orégano", "Pimenta-do-reino", "Pimenta calabresa", "Pimenta caiena", "Canela em pó", "Canela em pau", "Cravo-da-índia",
     "Noz-moscada", "Louro", "Alecrim", "Manjericão", "Salsa desidratada", "Cebolinha desidratada", "Açafrão",
     "Cúrcuma", "Curry", "Gengibre em pó", "Ervas finas", "Chimichurri", "Lemon pepper", "Mix de pimentas",
     "Lombo temperado", "Glutamato monossódico",
     "Milho verde em conserva", "Ervilha em conserva", "Seleta de legumes", "Palmito", "Azeitona verde", "Azeitona preta",
     "Pepino em conserva", "Picles", "Champignon", "Alcaparra", "Cogumelo em conserva", "Grão de bico em conserva",
     "Feijão em conserva", "Atum em lata", "Atum ralado", "Atum em pedaços", "Sardinha em lata", "Sardinha com tomate",
     "Sardinha em óleo", "Patê de atum", "Patê de frango", "Salsicha em lata", "Carne em conserva", "Fiambre",
     "Leite de coco", "Coco ralado", "Leite condensado", "Creme de leite", "Creme de leite fresco", "Doce de leite",
     "Goiabada", "Marmelada", "Pessegada", "Geleia de morango", "Geleia de uva", "Geleia de frutas vermelhas",
     "Pasta de amendoim", "Creme de avelã", "Pêssego em calda", "Figo em calda", "Abacaxi em calda", "Cereja em calda",
     "Gelatina", "Gelatina sem açúcar", "Pudim em pó", "Mousse em pó", "Chantili", "Cobertura de chocolate",
     "Chocolate granulado", "Confeitos coloridos", "Leite de soja", "Bebida de amêndoas", "Bebida de aveia",
     "Uva-passa", "Ameixa seca", "Damasco seco", "Tâmara", "Castanha-do-pará", "Castanha de caju", "Nozes", "Amêndoas",
     "Avelã", "Pistache", "Amendoim", "Amendoim torrado", "Amendoim japonês", "Mix de castanhas", "Paçoca", "Pé de moleque",
     "Cocada", "Doce de abóbora", "Bananada", "Torrone",
     "Biscoito água e sal", "Biscoito cream cracker", "Biscoito de maizena", "Biscoito maria", "Biscoito recheado",
     "Biscoito recheado de chocolate", "Biscoito recheado de morango", "Biscoito wafer", "Biscoito amanteigado",
     "Biscoito de polvilho", "Biscoito integral", "Biscoito de arroz", "Biscoito de leite", "Biscoito rosquinha",
     "Biscoito de coco", "Biscoito champanhe", "Biscoito sem glúten", "Bolacha", "Cookies", "Torrada", "Torrada integral",
     "Pão de mel", "Barra de cereal", "Barra de proteína", "Bolinho", "Bolo pronto", "Panetone", "Chocotone",
     "Chocolate ao leite", "Chocolate meio amargo", "Chocolate amargo", "Chocolate branco", "Chocolate 70% cacau",
     "Barra de chocolate", "Bombom", "Caixa de bombom", "Ovo de páscoa", "Bala", "Bala de goma", "Bala de menta", "Pirulito",
     "Chiclete", "Jujuba", "Marshmallow", "Pipoca doce", "Batata chips", "Batata palha", "Salgadinho", "Salgadinho de milho",
     "Amendoim crocante", "Torcida", "Pastilha"],
    de("Suco concentrado", FRUTAS), de("Suco em pó", FRUTAS[:12]), de("Gelatina", ["morango", "uva", "limão", "abacaxi", "cereja", "framboesa"]))

sec("Hortifrúti",
    ["Banana prata", "Banana nanica", "Banana maçã", "Banana da terra", "Banana ouro", "Maçã gala", "Maçã fuji", "Maçã verde",
     "Pera", "Pera williams", "Laranja pera", "Laranja lima", "Laranja bahia", "Tangerina", "Tangerina ponkan", "Mexerica",
     "Limão taiti", "Limão siciliano", "Limão cravo", "Mamão papaia", "Mamão formosa", "Melancia", "Melão", "Melão amarelo",
     "Abacaxi", "Manga palmer", "Manga tommy", "Manga espada", "Uva verde", "Uva roxa", "Uva sem semente", "Morango",
     "Kiwi", "Abacate", "Avocado", "Goiaba", "Maracujá", "Caqui", "Ameixa", "Pêssego", "Nectarina", "Figo", "Lichia",
     "Pitaya", "Romã", "Carambola", "Jabuticaba", "Acerola", "Caju", "Coco verde", "Coco seco", "Mirtilo", "Framboesa",
     "Amora", "Cereja", "Graviola", "Atemoia", "Fruta do conde", "Tamarindo", "Cajá", "Seriguela",
     "Alface americana", "Alface crespa", "Alface lisa", "Alface roxa", "Rúcula", "Agrião", "Couve", "Couve-manteiga",
     "Espinafre", "Acelga", "Repolho", "Repolho roxo", "Brócolis", "Brócolis ninja", "Couve-flor", "Escarola", "Chicória",
     "Almeirão", "Folha de mostarda", "Salsinha", "Cebolinha", "Cheiro-verde", "Coentro", "Hortelã", "Manjericão fresco",
     "Alecrim fresco", "Tomilho", "Louro fresco", "Salsão", "Aipo", "Alho-poró", "Erva-doce fresca", "Gengibre",
     "Tomate", "Tomate italiano", "Tomate cereja", "Tomate débora", "Cebola", "Cebola roxa", "Alho", "Batata", "Batata inglesa",
     "Batata doce", "Batata baroa", "Mandioquinha", "Mandioca", "Aipim", "Inhame", "Cará", "Cenoura", "Beterraba", "Rabanete",
     "Nabo", "Abóbora", "Abóbora cabotiá", "Abóbora moranga", "Abóbora paulista", "Abobrinha", "Abobrinha italiana",
     "Berinjela", "Pepino", "Pepino japonês", "Pimentão verde", "Pimentão vermelho", "Pimentão amarelo", "Pimenta dedo-de-moça",
     "Pimenta biquinho", "Pimenta malagueta", "Quiabo", "Jiló", "Chuchu", "Maxixe", "Vagem", "Ervilha torta", "Milho verde",
     "Milho na espiga", "Cogumelo paris", "Cogumelo shimeji", "Cogumelo shitake", "Champignon fresco", "Broto de feijão",
     "Aspargo", "Alcachofra", "Palmito pupunha", "Salada pronta", "Mix de folhas", "Legumes picados", "Ovos", "Ovos brancos",
     "Ovos vermelhos", "Ovos caipira", "Ovos de codorna", "Ovos orgânicos"])

sec("Açougue e peixaria",
    ["Carne moída", "Carne moída de primeira", "Carne moída de segunda", "Patinho", "Patinho moído", "Acém", "Acém moído",
     "Alcatra", "Picanha", "Maminha", "Fraldinha", "Contrafilé", "Filé mignon", "Coxão mole", "Coxão duro", "Lagarto",
     "Músculo", "Paleta", "Peito bovino", "Costela bovina", "Costela de ripa", "Cupim", "Fígado bovino", "Bisteca bovina",
     "Bife de alcatra", "Bife de contrafilé", "Carne para panela", "Carne para churrasco", "Cubos de carne", "Charque",
     "Carne seca", "Carne de sol", "Rabo bovino", "Mocotó", "Dobradinha", "Língua bovina", "Ossobuco", "Hambúrguer bovino",
     "Frango inteiro", "Frango resfriado", "Frango congelado", "Peito de frango", "Peito de frango sem osso",
     "Filé de peito de frango", "Sassami", "Coxa de frango", "Sobrecoxa de frango", "Coxa e sobrecoxa de frango",
     "Asa de frango", "Coxinha da asa", "Meio da asa", "Frango a passarinho", "Moela de frango", "Coração de frango",
     "Fígado de frango", "Pé de frango", "Carcaça de frango", "Frango desfiado", "Galinha caipira", "Chester", "Peru",
     "Peito de peru", "Pernil suíno", "Lombo suíno", "Costelinha suína", "Bisteca suína", "Paleta suína", "Panceta",
     "Bacon", "Bacon em cubos", "Bacon fatiado", "Toucinho", "Linguiça toscana", "Linguiça calabresa", "Linguiça de frango",
     "Linguiça cuiabana", "Linguiça apimentada", "Linguiça defumada", "Paio", "Salsichão", "Joelho de porco", "Orelha de porco",
     "Pé de porco", "Rabo de porco", "Carré de cordeiro", "Pernil de cordeiro", "Carne de cordeiro", "Carne de carneiro",
     "Tilápia", "Filé de tilápia", "Salmão", "Filé de salmão", "Merluza", "Filé de merluza", "Pescada", "Filé de pescada",
     "Sardinha fresca", "Bacalhau", "Bacalhau dessalgado", "Cação", "Pintado", "Tambaqui", "Pacu", "Truta", "Atum fresco",
     "Polvo", "Lula", "Camarão", "Camarão rosa", "Camarão sete barbas", "Camarão descascado", "Mexilhão", "Marisco", "Siri",
     "Kani", "Surimi"])

QUEIJOS = ["mussarela", "prato", "parmesão", "minas frescal", "minas padrão", "coalho", "cottage", "ricota", "gorgonzola",
           "provolone", "brie", "camembert", "cheddar", "gouda", "emmental", "estepe", "reino", "cream cheese", "maasdam",
           "muçarela de búfala", "burrata", "pecorino", "gruyère", "tilsit", "colonial"]
SABORES_IOG = ["morango", "frutas vermelhas", "coco", "pêssego", "ameixa", "baunilha", "mel", "natural", "grego", "chocolate"]
sec("Frios e laticínios",
    ["Leite integral", "Leite desnatado", "Leite semidesnatado", "Leite sem lactose", "Leite zero lactose", "Leite em pó",
     "Leite em pó integral", "Leite em pó desnatado", "Leite fermentado", "Leite achocolatado", "Bebida láctea", "Iogurte",
     "Iogurte natural", "Iogurte grego", "Iogurte desnatado", "Iogurte zero lactose", "Iogurte com granola", "Coalhada",
     "Kefir", "Petit suisse", "Requeijão", "Requeijão cremoso", "Requeijão light", "Requeijão de copo", "Manteiga",
     "Manteiga com sal", "Manteiga sem sal", "Manteiga ghee", "Margarina", "Margarina com sal", "Margarina sem sal", "Creme vegetal",
     "Nata", "Queijo ralado", "Queijo fatiado", "Queijo em cubos", "Queijo ralado fino",
     "Presunto", "Presunto cozido", "Presunto fatiado", "Presunto parma", "Apresuntado", "Mortadela", "Mortadela defumada",
     "Mortadela de frango", "Salame", "Salame italiano", "Copa", "Lombo defumado", "Peito de peru defumado", "Blanquet de peru",
     "Salsicha", "Salsicha hot dog", "Salsicha de frango", "Hambúrguer", "Hambúrguer de frango", "Almôndega", "Kibe",
     "Empanado de frango", "Nuggets", "Patê", "Pastel congelado", "Massa de pastel", "Pão de queijo congelado", "Tofu"],
    de("Queijo", QUEIJOS, ""), de("Iogurte", [x for x in SABORES_IOG if x not in ("natural", "grego")], "de"), de("Bebida láctea", SABORES_IOG[:6], "de"))

sec("Padaria",
    ["Pão francês", "Pão de forma", "Pão de forma integral", "Pão de forma sem casca", "Pão de forma sem glúten",
     "Pão integral", "Pão sírio", "Pão árabe", "Pão de hambúrguer", "Pão de hot dog", "Pão bisnaguinha", "Bisnaguinha",
     "Pão de leite", "Pão doce", "Pão italiano", "Pão australiano", "Pão de centeio", "Pão multigrãos", "Pão ciabatta",
     "Baguete", "Croissant", "Sonho", "Rosca", "Pão de batata", "Pão de alho", "Pão de queijo", "Broa de milho",
     "Bolo de fubá", "Bolo de cenoura", "Bolo de chocolate", "Bolo de laranja", "Bolo de milho", "Bolo de aipim",
     "Bolo de coco", "Pão de ló", "Torta doce", "Torta salgada", "Empada", "Esfiha", "Coxinha", "Quiche", "Sanduíche natural",
     "Wrap", "Pão folha", "Tortilha", "Rap10", "Pão sueco", "Grissini", "Biscoito de padaria", "Brioche"])

SORVETES = ["chocolate", "creme", "morango", "flocos", "napolitano", "baunilha", "limão", "coco", "doce de leite"]
sec("Congelados",
    ["Pizza congelada", "Pizza de mussarela", "Pizza de calabresa", "Pizza de frango com catupiry", "Pizza portuguesa",
     "Lasanha congelada", "Lasanha à bolonhesa", "Lasanha de frango", "Lasanha quatro queijos", "Lasanha de presunto e queijo",
     "Escondidinho", "Strogonoff congelado", "Prato pronto", "Marmita congelada", "Batata frita congelada",
     "Batata palito congelada", "Batata rústica", "Batata smile", "Polenta congelada", "Mandioca congelada",
     "Brócolis congelado", "Seleta de legumes congelada", "Ervilha congelada", "Milho congelado", "Espinafre congelado",
     "Mix de legumes congelado", "Polpa de fruta", "Polpa de açaí", "Açaí", "Açaí na tigela", "Hambúrguer congelado",
     "Steak de frango", "Filé de frango empanado", "Iscas de frango", "Coxinha congelada", "Kibe congelado",
     "Esfiha congelada", "Mini pizza", "Pão de alho congelado", "Waffle congelado", "Massa de pizza congelada",
     "Peixe empanado", "Filé de peixe congelado", "Camarão congelado", "Sorvete", "Pote de sorvete", "Picolé", "Picolé de fruta",
     "Gelo", "Gelo em cubos", "Gelo de coco", "Gelo saborizado", "Sobremesa congelada", "Torta congelada", "Pão de queijo"],
    de("Sorvete", SORVETES, "de"), de("Polpa", ["acerola", "maracujá", "goiaba", "morango", "caju", "abacaxi", "manga", "cajá"], "de"))

REFRIS = ["Refrigerante cola", "Refrigerante guaraná", "Refrigerante de laranja", "Refrigerante de limão", "Refrigerante de uva",
          "Refrigerante zero", "Refrigerante diet", "Refrigerante 2 litros", "Refrigerante lata", "Refrigerante 600 ml"]
sec("Bebidas",
    ["Água mineral", "Água mineral sem gás", "Água mineral com gás", "Água mineral 5 litros", "Água mineral 1,5 litro",
     "Galão de água", "Água tônica", "Água de coco", "Água saborizada", "Água com gás", "Club soda"],
    REFRIS,
    ["Suco de laranja", "Suco de uva integral", "Suco integral", "Suco de caixinha", "Suco de maçã", "Suco de pêssego",
     "Suco de manga", "Suco de maracujá", "Suco de goiaba", "Suco de abacaxi", "Suco de caju", "Suco detox", "Néctar",
     "Néctar de pêssego", "Néctar de uva", "Néctar de manga", "Chá gelado", "Chá gelado de limão", "Chá gelado de pêssego",
     "Mate gelado", "Isotônico", "Energético", "Bebida de soja", "Kombucha", "Leite de coco para beber", "Café gelado",
     "Cerveja", "Cerveja pilsen", "Cerveja lata", "Cerveja long neck", "Cerveja 600 ml", "Cerveja puro malte", "Cerveja sem álcool",
     "Cerveja artesanal", "Cerveja IPA", "Cerveja weiss", "Cerveja stout", "Chope", "Vinho tinto", "Vinho branco", "Vinho rosé",
     "Vinho tinto seco", "Vinho tinto suave", "Vinho branco seco", "Vinho espumante", "Espumante", "Espumante brut",
     "Espumante moscatel", "Champanhe", "Sidra", "Vinho do Porto", "Cachaça", "Vodca", "Uísque", "Gim", "Rum", "Tequila",
     "Licor", "Licor de chocolate", "Conhaque", "Saquê", "Vermute", "Aperitivo", "Catuaba", "Bebida mista", "Drink pronto",
     "Gelo para bebida", "Xarope de groselha", "Groselha", "Refresco em pó"])

sec("Limpeza",
    ["Sabão em pó", "Sabão líquido", "Lava-roupas líquido", "Lava-roupas em pó", "Sabão em barra", "Sabão de coco",
     "Sabão neutro", "Amaciante", "Amaciante concentrado", "Tira manchas", "Tira manchas em pó", "Tira manchas líquido",
     "Alvejante", "Alvejante sem cloro", "Água sanitária", "Cloro", "Água sanitária 5 litros", "Goma para roupa",
     "Passa roupa", "Removedor de manchas", "Lava-roupas para roupas delicadas", "Bola de lavar",
     "Detergente", "Detergente neutro", "Detergente de limão", "Detergente concentrado", "Detergente para lava-louças",
     "Pastilha para lava-louças", "Secante para lava-louças", "Sal para lava-louças", "Esponja de louça", "Esponja dupla face",
     "Esponja de aço", "Palha de aço", "Lã de aço", "Pano de prato", "Pano multiuso", "Pano de chão", "Flanela", "Perfex",
     "Desengordurante", "Limpador multiuso", "Limpa vidros", "Limpador de cozinha", "Limpa forno", "Limpa inox",
     "Limpa alumínio", "Saponáceo", "Saponáceo cremoso", "Sapólio", "Desinfetante", "Desinfetante de lavanda",
     "Desinfetante de eucalipto", "Desinfetante pinho", "Limpador perfumado", "Limpa pisos", "Limpa porcelanato",
     "Cera líquida", "Cera para piso", "Lustra móveis", "Limpa banheiro", "Limpador sanitário", "Gel sanitário",
     "Pedra sanitária", "Bloco sanitário", "Pastilha para caixa acoplada", "Desentupidor", "Desentupidor de pia",
     "Tira limo", "Removedor de mofo", "Limpa rejunte", "Álcool 70%", "Álcool em gel", "Álcool líquido", "Álcool 46",
     "Álcool etílico", "Álcool de limpeza", "Removedor", "Querosene", "Thinner", "Vinagre de limpeza",
     "Saco de lixo", "Saco de lixo 30 litros", "Saco de lixo 50 litros", "Saco de lixo 100 litros", "Saco de lixo reforçado",
     "Saco para pia", "Saco de lixo para banheiro", "Papel toalha", "Guardanapo", "Papel alumínio", "Filme plástico",
     "Filme PVC", "Papel manteiga", "Saco para congelar", "Saco zip", "Pote plástico", "Copo descartável", "Prato descartável",
     "Talher descartável", "Canudo", "Palito de dente", "Palito de churrasco", "Espeto de bambu", "Forminha de papel",
     "Assadeira descartável", "Luva de borracha", "Luva descartável", "Vassoura", "Rodo", "Pá de lixo", "Balde",
     "Esfregão", "Mop", "Refil de mop", "Escova sanitária", "Escova de lavar roupa", "Prendedor de roupa", "Varal",
     "Cesto de roupa", "Lixeira", "Inseticida", "Inseticida aerossol", "Repelente", "Repelente elétrico", "Refil de repelente",
     "Raticida", "Isca para formiga", "Isca para barata", "Naftalina", "Antimofo", "Desumidificador", "Aromatizador de ambiente",
     "Odorizador", "Purificador de ar", "Difusor de aromas", "Vela", "Vela aromática", "Fósforo", "Isqueiro",
     "Acendedor", "Carvão", "Álcool para churrasco", "Pilha AA", "Pilha AAA", "Bateria 9V", "Lâmpada LED", "Fita adesiva",
     "Fita isolante", "Cola instantânea", "Extensão elétrica", "Adaptador de tomada"])

sec("Higiene e beleza",
    ["Papel higiênico", "Papel higiênico folha dupla", "Papel higiênico folha simples", "Papel higiênico 12 rolos",
     "Lenço de papel", "Lenço umedecido", "Sabonete", "Sabonete em barra", "Sabonete líquido", "Sabonete íntimo",
     "Sabonete antibacteriano", "Sabonete de glicerina", "Refil de sabonete líquido", "Shampoo", "Shampoo anticaspa",
     "Shampoo infantil", "Condicionador", "Creme para pentear", "Máscara capilar", "Óleo capilar", "Leave-in", "Finalizador",
     "Gel para cabelo", "Pomada modeladora", "Spray fixador", "Tinta de cabelo", "Coloração", "Tonalizante", "Descolorante",
     "Água oxigenada", "Creme dental", "Creme dental infantil", "Creme dental para dentes sensíveis", "Creme dental clareador",
     "Escova de dente", "Escova de dente infantil", "Escova de dente elétrica", "Refil de escova elétrica", "Fio dental",
     "Fita dental", "Enxaguante bucal", "Antisséptico bucal", "Desodorante", "Desodorante aerossol", "Desodorante roll-on",
     "Desodorante em creme", "Desodorante masculino", "Desodorante feminino", "Antitranspirante", "Perfume", "Colônia",
     "Hidratante", "Hidratante corporal", "Loção hidratante", "Creme para mãos", "Creme para os pés", "Óleo corporal",
     "Hidratante facial", "Sabonete facial", "Gel de limpeza facial", "Tônico facial", "Água micelar", "Demaquilante",
     "Protetor solar", "Protetor solar facial", "Protetor solar FPS 30", "Protetor solar FPS 50", "Bronzeador", "Pós-sol",
     "Repelente corporal", "Aparelho de barbear", "Lâmina de barbear", "Carga de lâmina", "Barbeador descartável",
     "Espuma de barbear", "Gel de barbear", "Loção pós-barba", "Cera depilatória", "Creme depilatório", "Lâmina de depilação",
     "Absorvente", "Absorvente com abas", "Absorvente noturno", "Absorvente interno", "Protetor diário", "Coletor menstrual",
     "Calcinha absorvente", "Fralda geriátrica", "Fralda geriátrica G", "Roupa íntima descartável", "Algodão", "Algodão em bola",
     "Disco de algodão", "Hastes flexíveis", "Cotonete", "Lixa de unha", "Cortador de unha", "Alicate de unha", "Esmalte",
     "Removedor de esmalte", "Acetona", "Base para unha", "Batom", "Protetor labial", "Manteiga de cacau", "Base",
     "Corretivo", "Pó compacto", "Máscara para cílios", "Rímel", "Lápis de olho", "Delineador", "Sombra", "Blush",
     "Pincel de maquiagem", "Esponja de maquiagem", "Elástico de cabelo", "Pente", "Escova de cabelo", "Touca de banho",
     "Bucha de banho", "Esponja de banho", "Sais de banho", "Talco", "Talco para os pés", "Preservativo", "Lubrificante íntimo",
     "Teste de gravidez"])

sec("Bebê",
    ["Fralda descartável", "Fralda RN", "Fralda P", "Fralda M", "Fralda G", "Fralda XG", "Fralda XXG", "Fralda calça",
     "Fralda de pano", "Lenço umedecido infantil", "Pomada para assaduras", "Creme para assaduras", "Sabonete infantil",
     "Shampoo para bebê", "Condicionador infantil", "Colônia infantil", "Óleo para bebê", "Hidratante infantil",
     "Talco infantil", "Algodão para bebê", "Cotonete infantil", "Leite em pó infantil", "Fórmula infantil",
     "Fórmula infantil 1", "Fórmula infantil 2", "Fórmula infantil 3", "Composto lácteo", "Papinha", "Papinha de frutas",
     "Papinha de legumes", "Cereal infantil", "Farinha láctea infantil", "Suco infantil", "Biscoito infantil", "Mamadeira",
     "Bico de mamadeira", "Chupeta", "Mordedor", "Escova de mamadeira", "Absorvente para seios", "Protetor de mamilo",
     "Termômetro infantil", "Aspirador nasal", "Soro fisiológico", "Repelente infantil", "Protetor solar infantil",
     "Lenço de papel infantil", "Toalha de banho infantil", "Babador"])

sec("Pet",
    ["Ração para cachorro", "Ração para cachorro filhote", "Ração para cachorro adulto", "Ração para cachorro sênior",
     "Ração para cachorro de porte pequeno", "Ração para cachorro de porte grande", "Ração úmida para cachorro",
     "Sachê para cachorro", "Petisco para cachorro", "Bifinho", "Osso para cachorro", "Ração para gato",
     "Ração para gato filhote", "Ração para gato adulto", "Ração para gato castrado", "Ração úmida para gato",
     "Sachê para gato", "Petisco para gato", "Areia sanitária", "Areia para gato", "Areia de sílica", "Granulado higiênico",
     "Tapete higiênico", "Shampoo para cachorro", "Antipulgas", "Coleira antipulgas", "Vermífugo", "Ração para pássaro",
     "Alpiste", "Ração para peixe", "Ração para roedor", "Feno", "Brinquedo para cachorro", "Brinquedo para gato",
     "Comedouro", "Bebedouro", "Saco coletor", "Cama para cachorro", "Arranhador", "Guia", "Coleira", "Peitoral"])

REMEDIOS = ["Dipirona", "Dipirona 500 mg", "Dipirona 1 g", "Dipirona gotas", "Paracetamol", "Paracetamol 500 mg",
            "Paracetamol 750 mg", "Paracetamol gotas", "Ibuprofeno", "Ibuprofeno 400 mg", "Ibuprofeno 600 mg", "Ibuprofeno gotas",
            "Ácido acetilsalicílico", "Naproxeno", "Diclofenaco", "Diclofenaco sódico", "Diclofenaco potássico", "Nimesulida",
            "Cetoprofeno", "Dexametasona", "Prednisona", "Prednisolona", "Loratadina", "Desloratadina", "Cetirizina",
            "Fexofenadina", "Dexclorfeniramina", "Hidroxizina", "Omeprazol", "Omeprazol 20 mg", "Pantoprazol", "Esomeprazol",
            "Ranitidina", "Domperidona", "Metoclopramida", "Bromoprida", "Simeticona", "Hidróxido de alumínio", "Sal de frutas",
            "Lactulose", "Bisacodil", "Loperamida", "Soro de reidratação oral", "Probiótico", "Escopolamina", "Dimenidrinato",
            "Ondansetrona", "Amoxicilina", "Azitromicina", "Cefalexina", "Ciprofloxacino", "Nitrofurantoína", "Fluconazol",
            "Cetoconazol", "Miconazol", "Clotrimazol", "Nistatina", "Aciclovir", "Albendazol", "Mebendazol", "Ivermectina",
            "Losartana", "Losartana 50 mg", "Enalapril", "Captopril", "Anlodipino", "Atenolol", "Propranolol", "Carvedilol",
            "Metoprolol", "Hidroclorotiazida", "Furosemida", "Espironolactona", "Indapamida", "Valsartana", "Olmesartana",
            "Atorvastatina", "Atorvastatina 20 mg", "Sinvastatina", "Sinvastatina 20 mg", "Rosuvastatina", "Ezetimiba",
            "Metformina", "Metformina 850 mg", "Glibenclamida", "Gliclazida", "Sitagliptina", "Insulina", "Levotiroxina",
            "Clopidogrel", "Varfarina", "Rivaroxabana", "Sertralina", "Fluoxetina", "Escitalopram", "Citalopram", "Paroxetina",
            "Venlafaxina", "Bupropiona", "Amitriptilina", "Clonazepam", "Alprazolam", "Diazepam", "Zolpidem", "Quetiapina",
            "Melatonina", "Ciclobenzaprina", "Orfenadrina", "Carisoprodol", "Tramadol", "Codeína", "Gabapentina", "Pregabalina",
            "Topiramato", "Sumatriptana", "Alendronato", "Finasterida", "Tansulosina", "Sildenafila", "Tadalafila",
            "Anticoncepcional", "Pílula do dia seguinte", "Ácido fólico", "Sulfato ferroso", "Vitamina C", "Vitamina D",
            "Vitamina D3", "Vitamina B12", "Complexo B", "Polivitamínico", "Multivitamínico", "Ômega 3", "Cálcio", "Magnésio",
            "Zinco", "Colágeno", "Biotina", "Whey protein", "Creatina", "Xarope para tosse", "Xarope expectorante",
            "Acetilcisteína", "Ambroxol", "Bromexina", "Pastilha para garganta", "Spray para garganta", "Antigripal",
            "Descongestionante nasal", "Soro fisiológico 0,9%", "Spray nasal", "Colírio", "Colírio lubrificante",
            "Lágrima artificial", "Pomada cicatrizante", "Pomada antibiótica", "Pomada para queimadura", "Pomada anti-inflamatória",
            "Gel anti-inflamatório", "Relaxante muscular", "Emplastro", "Antisséptico", "Água oxigenada 10 volumes",
            "Povidine", "Clorexidina", "Mertiolate", "Curativo", "Curativo adesivo", "Gaze", "Esparadrapo", "Micropore",
            "Atadura", "Seringa", "Agulha", "Termômetro", "Termômetro digital", "Medidor de pressão", "Medidor de glicose",
            "Tira para glicose", "Lanceta", "Máscara descartável", "Luva de procedimento", "Bolsa térmica", "Meia de compressão",
            "Teste de covid", "Inalador", "Nebulizador"]
sec("Farmácia", REMEDIOS)

# as marcas mais vendidas, com o produto delas (quem digita só a marca acha o produto)
MARCAS = {
    "Limpeza": [
        "Tira manchas Vanish", "Tira manchas Vanish Oxi Action", "Alvejante Vanish", "Sabão em pó Omo", "Lava-roupas líquido Omo",
        "Sabão em pó Ariel", "Lava-roupas líquido Ariel", "Sabão em pó Brilhante", "Lava-roupas líquido Brilhante",
        "Sabão em pó Tixan Ypê", "Sabão em pó Surf", "Sabão em pó Ace", "Sabão em pó Minuano", "Sabão em pó Assim",
        "Lava-roupas Ypê", "Sabão em barra Ypê", "Sabão em barra Minuano", "Sabão em barra Brilhante", "Sabão de coco Ypê",
        "Sabão em barra Fazendeiro", "Amaciante Comfort", "Amaciante Downy", "Amaciante Ypê", "Amaciante Mon Bijou",
        "Amaciante Fofo", "Amaciante Minuano", "Amaciante Confort", "Detergente Ypê", "Detergente Limpol", "Detergente Minuano",
        "Detergente Brilhante", "Detergente Pril", "Detergente Lava Louças Ypê", "Água sanitária Qboa", "Água sanitária Ypê",
        "Água sanitária Candura", "Água sanitária Super Globo", "Desinfetante Pinho Sol", "Desinfetante Veja",
        "Desinfetante Ypê", "Desinfetante Pato", "Desinfetante Lysoform", "Desinfetante Minuano", "Desinfetante Bombril",
        "Desinfetante Pinho Bril", "Lysoform", "Lysoform bruto", "Limpador Veja", "Veja multiuso", "Veja limpeza pesada",
        "Veja vidrex", "Limpa vidros Veja", "Limpador Cif", "Saponáceo Cif", "Mr. Músculo", "Limpador Mr. Músculo",
        "Limpador Ajax", "Limpador Flash Limp", "Multiuso Ypê", "Esponja Scotch-Brite", "Esponja Bombril", "Bombril",
        "Esponja de aço Bombril", "Esponja de aço Assolan", "Assolan", "Pano Perfex", "Saco de lixo Dover Roll",
        "Papel alumínio Wyda", "Filme plástico Wyda", "Gel sanitário Harpic", "Harpic", "Pato purific", "Pato gel adesivo",
        "Desodorizador Glade", "Aromatizador Glade", "Bom Ar", "Aromatizador Bom Ar", "Inseticida SBP", "Inseticida Raid",
        "Inseticida Baygon", "Repelente Off", "Repelente SBP", "Repelente Raid", "Desentupidor Diabo Verde", "Diabo Verde",
        "Sapólio Radium", "Lustra móveis Poliflor", "Cera Poliflor", "Cera Brilho Fácil", "Álcool Tupi", "Álcool Coperalcool",
        "Álcool Zulu", "Álcool Start", "Limpa alumínio Ypê", "Amaciante Comfort concentrado", "Sabão líquido Omo",
        "Tira manchas Ypê", "Lava-louças Finish", "Pastilha Finish"],
    "Mercearia": [
        "Arroz Tio João", "Arroz Camil", "Arroz Prato Fino", "Arroz Namorado", "Arroz Blue Ville", "Feijão Camil",
        "Feijão Kicaldo", "Feijão Tio João", "Feijão Broto Legal", "Açúcar União", "Açúcar Caravelas", "Açúcar Da Barra",
        "Açúcar Guarani", "Sal Cisne", "Sal Lebre", "Café Pilão", "Café 3 Corações", "Café Melitta", "Café Pelé",
        "Café Santa Clara", "Café do Ponto", "Café Caboclo", "Café Melitta Tradicional", "Café Nescafé", "Nescafé",
        "Café Dolce Gusto", "Cápsula Nespresso", "Cápsula Três Corações", "Cappuccino 3 Corações", "Achocolatado Nescau",
        "Nescau", "Achocolatado Toddy", "Toddy", "Achocolatado Ovomaltine", "Ovomaltine", "Leite condensado Moça",
        "Leite condensado Itambé", "Leite condensado Piracanjuba", "Creme de leite Nestlé", "Creme de leite Piracanjuba",
        "Creme de leite Itambé", "Leite Ninho", "Leite em pó Ninho", "Farinha láctea Nestlé", "Mucilon", "Neston",
        "Aveia Quaker", "Sucrilhos Kellogg's", "Cereal Nescau", "Granola Mãe Terra", "Nutella", "Creme de avelã Nutella",
        "Gelatina Royal", "Fermento Royal", "Fermento Fleischmann", "Pudim Royal", "Mistura para bolo Fleischmann",
        "Mistura para bolo Dona Benta", "Farinha de trigo Dona Benta", "Farinha de trigo Renata", "Farinha de trigo Anaconda",
        "Farinha de trigo Sol", "Farinha de trigo Venturelli", "Macarrão Renata", "Macarrão Barilla", "Macarrão Adria",
        "Macarrão Dona Benta", "Macarrão Santa Amália", "Macarrão Divella", "Macarrão Petybon", "Macarrão Galo",
        "Macarrão instantâneo Nissin", "Miojo", "Nissin Miojo", "Lámen Nissin", "Cup Noodles", "Óleo de soja Soya",
        "Óleo de soja Liza", "Óleo de soja Leve", "Óleo de soja Cocamar", "Óleo de girassol Liza", "Azeite Gallo",
        "Azeite Andorinha", "Azeite Borges", "Azeite Carbonell", "Azeite La Violetera", "Azeite O-Live", "Maionese Hellmann's",
        "Maionese Heinz", "Maionese Quero", "Maionese Arisco", "Ketchup Heinz", "Ketchup Hellmann's", "Ketchup Quero",
        "Mostarda Hellmann's", "Mostarda Heinz", "Extrato de tomate Elefante", "Extrato de tomate Quero",
        "Molho de tomate Pomarola", "Molho de tomate Quero", "Molho de tomate Fugini", "Molho de tomate Heinz",
        "Molho de tomate Predilecta", "Molho de tomate Salsaretti", "Tempero Sazón", "Sazón Ajinomoto", "Caldo Knorr",
        "Caldo Maggi", "Tempero Arisco", "Ajinomoto", "Shoyu Sakura", "Shoyu Kikkoman", "Milho verde Quero",
        "Milho verde Predilecta", "Ervilha Quero", "Seleta de legumes Quero", "Atum Gomes da Costa", "Atum Coqueiro",
        "Sardinha Gomes da Costa", "Sardinha Coqueiro", "Sardinha 88", "Leite de coco Sococo", "Leite de coco Ducoco",
        "Coco ralado Sococo", "Biscoito Oreo", "Biscoito Passatempo", "Biscoito Negresco", "Biscoito Trakinas",
        "Biscoito Bono", "Biscoito Calipso", "Biscoito Bauducco", "Wafer Bauducco", "Biscoito Club Social", "Club Social",
        "Biscoito Tostines", "Biscoito Piraquê", "Biscoito Vitarella", "Biscoito Marilan", "Biscoito Mabel", "Biscoito Richester",
        "Biscoito Triunfo", "Biscoito Fortaleza", "Biscoito Nesfit", "Torrada Bauducco", "Torrada Visconti", "Panetone Bauducco",
        "Panetone Visconti", "Chocotone Bauducco", "Chocolate Lacta", "Chocolate Garoto", "Chocolate Nestlé",
        "Chocolate Hershey's", "Chocolate Lindt", "Chocolate Cacau Show", "Chocolate Diamante Negro", "Chocolate Laka",
        "Chocolate Talento", "Chocolate Classic", "Chocolate Alpino", "Chocolate Suflair", "Chocolate Bis", "Bis",
        "Chocolate Kit Kat", "Kit Kat", "Chocolate Prestígio", "Prestígio", "Chocolate Baton", "Baton", "Chocolate Crunch",
        "Chocolate Galak", "Bombom Sonho de Valsa", "Sonho de Valsa", "Bombom Ouro Branco", "Ouro Branco",
        "Bombom Serenata do Amor", "Bombom Ferrero Rocher", "Caixa de bombom Garoto", "Caixa de bombom Nestlé",
        "Chocolate M&M's", "M&M's", "Chocolate Twix", "Chocolate Snickers", "Chocolate Kinder", "Kinder Ovo", "Bala Fini",
        "Bala Halls", "Halls", "Chiclete Trident", "Trident", "Chiclete Mentos", "Mentos", "Pirulito Pop", "Bala 7 Belo",
        "Batata Ruffles", "Ruffles", "Batata Pringles", "Pringles", "Batata Lay's", "Salgadinho Doritos", "Doritos",
        "Salgadinho Cheetos", "Cheetos", "Salgadinho Fandangos", "Fandangos", "Salgadinho Baconzitos", "Salgadinho Torcida",
        "Batata palha Elma Chips", "Batata palha Yoki", "Pipoca Yoki", "Yoki", "Amendoim Dori", "Amendoim Elma Chips",
        "Paçoca Paçoquita", "Paçoquita", "Goiabada Predilecta", "Geleia Queensberry", "Doce de leite Itambé",
        "Doce de leite Aviação", "Barra de cereal Nutry", "Nutry", "Barra de proteína Bold", "Bolinho Ana Maria",
        "Bolinho Bauducco", "Adoçante Zero-Cal", "Adoçante Adocyl", "Adoçante Linea", "Adoçante Tal e Qual",
        "Chá Leão", "Chá Matte Leão", "Chá Dr. Oetker", "Chá Twinings", "Erva-mate Barão", "Erva-mate Ximango",
        "Gelatina Dr. Oetker", "Chantili Amélia", "Cobertura Harald", "Chocolate em pó Melken", "Chocolate em pó Nestlé"],
    "Frios, laticínios e congelados": [
        "Leite Italac", "Leite Piracanjuba", "Leite Parmalat", "Leite Itambé", "Leite Elegê", "Leite Tirol", "Leite Jussara",
        "Leite Ninho Forti+", "Leite Molico", "Molico", "Leite Batavo", "Leite Aviação", "Leite Shefa", "Leite Lider",
        "Leite Piracanjuba Zero Lactose", "Leite Italac Zero Lactose", "Leite Parmalat Zero Lactose", "Leite Nestlé Zero Lactose",
        "Iogurte Danone", "Iogurte Activia", "Activia", "Danoninho", "Iogurte Nestlé", "Iogurte Batavo", "Iogurte Vigor",
        "Iogurte Itambé", "Iogurte Piracanjuba", "Iogurte Grego Vigor", "Iogurte Grego Danone", "Iogurte Nestlé Grego",
        "Yakult", "Leite fermentado Yakult", "Chamyto", "Requeijão Catupiry", "Catupiry", "Requeijão Vigor",
        "Requeijão Itambé", "Requeijão Danúbio", "Requeijão Poços de Caldas", "Requeijão Tirolez", "Requeijão Polenghi",
        "Cream cheese Philadelphia", "Queijo Polenghi", "Polenghi", "Polenguinho", "Queijo Tirolez", "Queijo Président",
        "Queijo Faixa Azul", "Queijo Quatá", "Queijo Vigor", "Manteiga Aviação", "Manteiga Itambé", "Manteiga Président",
        "Manteiga Tirolez", "Manteiga Piracanjuba", "Manteiga Batavo", "Margarina Qualy", "Qualy", "Margarina Doriana",
        "Margarina Delícia", "Margarina Becel", "Margarina Claybom", "Margarina Primor", "Presunto Sadia", "Presunto Perdigão",
        "Presunto Seara", "Presunto Aurora", "Mortadela Sadia", "Mortadela Seara", "Mortadela Perdigão", "Mortadela Ceratti",
        "Mortadela Marba", "Salsicha Sadia", "Salsicha Perdigão", "Salsicha Seara", "Salsicha Aurora", "Salsicha Swift",
        "Linguiça Sadia", "Linguiça Seara", "Linguiça Perdigão", "Linguiça Aurora", "Peito de peru Sadia", "Peito de peru Seara",
        "Peito de peru Perdigão", "Salame Sadia", "Hambúrguer Sadia", "Hambúrguer Seara", "Hambúrguer Perdigão",
        "Hambúrguer Swift", "Hambúrguer Friboi", "Nuggets Sadia", "Nuggets Seara", "Nuggets Perdigão", "Empanado Sadia",
        "Lasanha Sadia", "Lasanha Perdigão", "Lasanha Seara", "Pizza Sadia", "Pizza Seara", "Pizza Perdigão",
        "Pão de queijo Forno de Minas", "Forno de Minas", "Pão de queijo Pif Paf", "Batata McCain", "Batata Bem Brasil",
        "Frango Sadia", "Frango Seara", "Frango Perdigão", "Frango Aurora", "Frango Copacol", "Frango Lar", "Frango C.Vale",
        "Frango Korin", "Frango Diplomata", "Carne Friboi", "Carne Swift", "Carne Maturatta", "Bacon Sadia", "Bacon Seara",
        "Sorvete Kibon", "Kibon", "Picolé Kibon", "Sorvete Nestlé", "Sorvete Häagen-Dazs", "Picolé Magnum", "Magnum",
        "Sorvete Jundiá", "Sorvete Cremosy", "Açaí Frooty", "Polpa de fruta DeMarchi", "Polpa de fruta Ricaeli"],
    "Bebidas": [
        "Coca-Cola", "Coca-Cola Zero", "Refrigerante Coca-Cola", "Refrigerante Coca-Cola Zero", "Guaraná Antarctica",
        "Refrigerante Guaraná Antarctica", "Guaraná Antarctica Zero", "Fanta", "Fanta Laranja", "Fanta Uva", "Fanta Guaraná",
        "Sprite", "Pepsi", "Pepsi Black", "Refrigerante Pepsi", "Guaraná Kuat", "Schweppes", "Água tônica Schweppes",
        "Guaraná Jesus", "Refrigerante Itubaína", "Soda Antarctica", "H2OH!", "Refrigerante Dolly", "Guaraná Dolly",
        "Água mineral Crystal", "Água mineral Bonafont", "Água mineral Lindoya", "Água mineral São Lourenço",
        "Água mineral Minalba", "Água mineral Indaiá", "Água mineral Petrópolis", "Água de coco Kero Coco", "Kero Coco",
        "Água de coco Obrigado", "Suco Del Valle", "Del Valle", "Suco Maguary", "Maguary", "Suco Ades", "Ades", "Suco Natural One",
        "Suco Do Bem", "Suco Tial", "Suco Sufresh", "Suco Tang", "Tang", "Suco Fresh", "Suco Mid", "Refresco Clight",
        "Chá Matte Leão gelado", "Chá Lipton", "Lipton Ice Tea", "Isotônico Gatorade", "Gatorade", "Isotônico Powerade",
        "Energético Red Bull", "Red Bull", "Energético Monster", "Monster", "Energético TNT", "Energético Fusion",
        "Cerveja Skol", "Skol", "Cerveja Brahma", "Brahma", "Brahma Duplo Malte", "Cerveja Antarctica", "Antarctica Subzero",
        "Cerveja Heineken", "Heineken", "Heineken zero", "Cerveja Budweiser", "Budweiser", "Cerveja Amstel", "Amstel",
        "Cerveja Original", "Cerveja Stella Artois", "Stella Artois", "Cerveja Itaipava", "Itaipava",
        "Cerveja Spaten", "Spaten", "Cerveja Corona", "Corona", "Cerveja Eisenbahn", "Eisenbahn", "Cerveja Bohemia",
        "Cerveja Petra", "Cerveja Devassa", "Cerveja Schin", "Cerveja Kaiser", "Cerveja Crystal", "Cerveja Glacial",
        "Cerveja Império", "Cerveja Colorado", "Cerveja Baden Baden", "Cerveja Becks", "Cerveja Michelob", "Cerveja Patagonia",
        "Cerveja Sol", "Cerveja Black Princess", "Vinho Casillero del Diablo", "Vinho Concha y Toro", "Vinho Santa Helena",
        "Vinho Pérgola", "Vinho Salton", "Vinho Miolo", "Vinho Aurora", "Vinho Chalise", "Vinho Quinta do Morgado",
        "Espumante Chandon", "Chandon", "Espumante Salton", "Espumante Aurora", "Espumante Freixenet", "Sidra Cereser",
        "Cachaça 51", "Cachaça Ypióca", "Ypióca", "Cachaça Velho Barreiro", "Cachaça Sagatiba", "Cachaça Pitú",
        "Cachaça Seleta", "Vodca Smirnoff", "Smirnoff", "Vodca Absolut", "Absolut", "Vodca Orloff", "Vodca Askov",
        "Uísque Johnnie Walker", "Johnnie Walker", "Uísque Jack Daniel's", "Jack Daniel's", "Uísque Ballantine's",
        "Uísque Chivas Regal", "Uísque Red Label", "Uísque White Horse", "Uísque Passport", "Gim Tanqueray", "Gim Beefeater",
        "Gim Bombay Sapphire", "Rum Bacardi", "Bacardi", "Rum Montilla", "Tequila José Cuervo", "Licor 43", "Licor Baileys",
        "Campari", "Aperol", "Martini", "Catuaba Selvagem", "Corote", "Smirnoff Ice", "Beats Skol", "Skol Beats"],
    "Higiene e beleza": [
        "Creme dental Colgate", "Colgate", "Colgate Total 12", "Colgate Luminous White", "Creme dental Sorriso", "Sorriso",
        "Creme dental Oral-B", "Creme dental Close Up", "Close Up", "Creme dental Sensodyne", "Sensodyne", "Creme dental Elmex",
        "Creme dental Signal", "Escova de dente Oral-B", "Escova de dente Colgate", "Escova Curaprox", "Fio dental Oral-B",
        "Fio dental Colgate", "Fio dental Johnson's", "Enxaguante bucal Listerine", "Listerine", "Enxaguante bucal Colgate",
        "Enxaguante Colgate Plax", "Plax", "Sabonete Dove", "Dove", "Sabonete Lux", "Lux", "Sabonete Protex", "Protex",
        "Sabonete Lifebuoy", "Sabonete Nivea", "Sabonete Palmolive", "Palmolive", "Sabonete Rexona", "Sabonete Francis",
        "Sabonete Phebo", "Sabonete Granado", "Granado", "Sabonete Albany", "Sabonete Johnson's", "Sabonete líquido Dove",
        "Sabonete líquido Protex", "Sabonete líquido Lux", "Sabonete íntimo Dermacyd", "Dermacyd", "Sabonete íntimo Lucretin",
        "Desodorante Rexona", "Rexona", "Desodorante Dove", "Desodorante Nivea", "Desodorante Axe", "Axe", "Desodorante Old Spice",
        "Old Spice", "Desodorante Monange", "Desodorante Avanço", "Desodorante Herbíssimo", "Desodorante Bozzano",
        "Desodorante Above", "Desodorante Adidas", "Desodorante Gillette", "Shampoo Pantene", "Pantene", "Shampoo Seda", "Shampoo Elseve", "Elseve", "Shampoo Dove", "Shampoo Head & Shoulders", "Head & Shoulders", "Shampoo Clear", "Shampoo TRESemmé", "TRESemmé", "Shampoo Johnson's", "Shampoo Garnier Fructis", "Fructis", "Shampoo Herbal Essences",
        "Shampoo Darling", "Shampoo Salon Line", "Salon Line", "Shampoo Palmolive", "Shampoo Lola", "Shampoo Kerasys",
        "Shampoo Wella", "Shampoo Nivea Men", "Condicionador Pantene", "Condicionador Seda", "Condicionador Elseve",
        "Condicionador Dove", "Condicionador TRESemmé", "Creme para pentear Seda", "Creme para pentear Salon Line",
        "Creme para pentear Elseve", "Creme para pentear Novex", "Novex", "Máscara Lola", "Óleo Elseve", "Tinta Koleston",
        "Koleston", "Tinta Imédia", "Imédia", "Tinta Garnier Nutrisse", "Nutrisse", "Tinta Igora", "Tinta Wella",
        "Hidratante Nivea", "Nivea", "Creme Nivea", "Hidratante Dove", "Hidratante Monange", "Monange", "Hidratante Neutrogena",
        "Neutrogena", "Hidratante Cetaphil", "Cetaphil", "Hidratante Vasenol", "Vasenol", "Hidratante Paixão", "Hidratante Natura",
        "Hidratante Cerave", "CeraVe", "Hidratante Darrow", "Hidratante Johnson's", "Hidratante L'Oréal", "Protetor solar Sundown",
        "Sundown", "Protetor solar Nivea", "Protetor solar Neutrogena", "Protetor solar La Roche-Posay", "Protetor solar Episol",
        "Protetor solar Cenoura e Bronze", "Protetor solar L'Oréal", "Protetor solar Banana Boat", "Água micelar Garnier",
        "Água micelar Nivea", "Água micelar L'Oréal", "Aparelho de barbear Gillette", "Gillette", "Gillette Mach3",
        "Gillette Prestobarba", "Prestobarba", "Aparelho Bic", "Bic", "Espuma de barbear Gillette", "Gel de barbear Gillette",
        "Espuma de barbear Bozzano", "Absorvente Always", "Always", "Absorvente Intimus", "Intimus", "Absorvente Carefree",
        "Carefree", "Absorvente Sym", "Absorvente o.b.", "Absorvente Ela", "Absorvente Kotex", "Papel higiênico Neve",
        "Papel higiênico Personal", "Papel higiênico Mili", "Papel higiênico Sublime", "Papel higiênico Leve",
        "Papel higiênico Scott", "Papel higiênico Familia", "Papel higiênico Max Pure", "Papel higiênico Carinho",
        "Papel higiênico Fofinho", "Papel toalha Snob", "Snob", "Papel toalha Scott", "Papel toalha Kitchen", "Lenço Kleenex",
        "Kleenex", "Lenço umedecido Huggies", "Lenço umedecido Pampers", "Lenço umedecido Johnson's", "Lenço umedecido Personal",
        "Cotonete Johnson's", "Algodão Apolo", "Algodão Cremer", "Esmalte Risqué", "Risqué", "Esmalte Colorama", "Colorama",
        "Esmalte Impala", "Impala", "Acetona Farmax", "Batom Maybelline", "Rímel Maybelline", "Base Maybelline", "Maybelline",
        "Base Vult", "Vult", "Base Ruby Rose", "Ruby Rose", "Protetor labial Nivea", "Carmed", "Bepantol", "Bepantol Derma",
        "Leite de Rosas", "Nivea Men", "Lâmina Gillette", "Preservativo Jontex", "Jontex", "Preservativo Prudence",
        "Preservativo Olla", "Lubrificante KY", "Fralda geriátrica Tena", "Tena", "Fralda geriátrica Plenitud",
        "Plenitud", "Fralda geriátrica Bigfral", "Bigfral", "Talco Granado", "Talco Barla"],
    "Bebê": [
        "Fralda Pampers", "Pampers", "Fralda Pampers Confort Sec", "Fralda Pampers Premium Care", "Fralda Huggies", "Huggies",
        "Fralda Huggies Tripla Proteção", "Fralda MamyPoko", "MamyPoko", "Fralda Turma da Mônica", "Fralda Babysec",
        "Fralda Personal Baby", "Fralda Pom Pom", "Pom Pom", "Fralda Cremer", "Fralda Bigfral Baby", "Pomada Hipoglós", "Hipoglós",
        "Pomada Bepantol Baby", "Bepantol Baby", "Pomada Desitin", "Pomada Dermodex", "Shampoo Johnson's Baby", "Johnson's Baby",
        "Sabonete Johnson's Baby", "Colônia Johnson's Baby", "Óleo Johnson's Baby", "Lenço Huggies", "Leite Nan", "Leite Nan Comfor", "Leite Aptamil", "Aptamil", "Leite Milnutri", "Milnutri", "Leite Nestogeno", "Nestogeno",
        "Leite Enfamil", "Enfamil", "Leite Ninho Fases", "Leite Similac", "Papinha Nestlé", "Mucilon arroz", "Mucilon milho",
        "Mamadeira Avent", "Mamadeira Lillo", "Lillo", "Chupeta Lillo", "Chupeta Nuk", "Nuk", "Chupeta MAM", "Chupeta Avent", "Avent"],
    "Pet": [
        "Ração Pedigree", "Pedigree", "Sachê Pedigree", "Ração Whiskas", "Whiskas", "Sachê Whiskas", "Ração Golden", "Ração Golden Gatos", "Ração Premier", "Ração Royal Canin", "Royal Canin", "Ração Dog Chow", "Dog Chow",
        "Ração Cat Chow", "Cat Chow", "Ração Friskies", "Friskies", "Ração Purina", "Purina", "Ração Pro Plan", "Pro Plan",
        "Ração Special Dog", "Special Dog", "Ração Special Cat", "Ração Magnus", "Magnus", "Ração Quatree", "Quatree",
        "Ração Max", "Ração Guabi Natural", "Guabi Natural", "Ração N&D", "N&D", "Ração Hill's", "Ração Premiatta",
        "Ração Biofresh", "Biofresh", "Ração Formula Natural", "Ração GranPlus", "GranPlus", "Ração Fit Formula",
        "Ração Origens", "Ração Baw Waw", "Baw Waw", "Petisco Dreamies", "Dreamies", "Petisco Keldog", "Petisco Bifinho Keldog",
        "Areia Pipicat", "Pipicat", "Areia Chalesco", "Areia Viva Verde", "Areia Kelco", "Tapete higiênico Super Secão",
        "Tapete Chalesco", "Antipulgas Bravecto", "Bravecto", "Antipulgas NexGard", "NexGard", "Antipulgas Simparic",
        "Simparic", "Antipulgas Frontline", "Frontline", "Coleira Seresto", "Seresto", "Vermífugo Drontal", "Drontal",
        "Vermífugo Vermivet", "Shampoo Sanol", "Sanol"],
    "Farmácia": [
        "Dorflex", "Neosaldina", "Tylenol", "Buscopan", "Buscopan Composto", "Engov", "Eno", "Sal de fruta Eno", "Estomazil",
        "Sonrisal", "Benegrip", "Cimegripe", "Resfenol", "Coristina D", "Apracur", "Vick VapoRub", "Strepsils",
        "Benalet", "Neosoro", "Rinosoro", "Sorine", "Maxidex", "Lacrima Plus", "Systane", "Hipoglós", "Bepantol",
        "Bepantol Derma", "Merthiolate", "Band-Aid", "Nebacetin", "Nebacetin pomada", "Cataflam", "Cataflam gel", "Voltaren",
        "Voltaren gel", "Gelol", "Salonpas", "Advil", "Aspirina", "AAS", "Novalgina", "Anador", "Lisador", "Doril",
        "Torsilax", "Miosan", "Mioflex", "Allegra", "Claritin", "Polaramine", "Histamin", "Luftal", "Epocler", "Plasil",
        "Dramin", "Imosec", "Floratil", "Simeticona Luftal", "Tamarine", "Lacto-Purga", "Dulcolax", "Ozempic", "Centrum",
        "Redoxon", "Cebion", "Addera D3", "Depura", "Lavitan", "Puran T4", "Euthyrox", "Glifage", "Xarelto", "Aradois",
        "Losartana EMS", "Atorvastatina EMS", "Rivotril", "Frontal", "Benegrip multi", "Multigrip", "Targifor", "Biotônico Fontoura",
        "Emulsão Scott", "Ômega 3 Vitafor", "Colágeno Sanavita", "Whey Growth", "Whey Max Titanium", "Creatina Max Titanium",
        "Creatina Growth", "Teste de gravidez Clearblue", "Teste de gravidez Confirme", "Durex", "Hydrogel", "Fisiofor",
        "Cicatricure", "Hidratante Cicaplast", "Sabonete Granado Antisséptico", "Soro fisiológico Arboreto", "Termômetro G-Tech",
        "Medidor de pressão Omron", "Omron", "Medidor de glicose Accu-Chek", "Accu-Chek", "Tira Accu-Chek", "Lanceta Accu-Chek",
        "Seringa BD", "Agulha BD", "Fralda Tena", "Dermacyd", "Pomada Minancora", "Minancora", "Leite de Magnésia Phillips",
        "Leite de Magnésia", "Óleo de rícino", "Água boricada", "Polvilho antisséptico", "Talco Barla"],
}


def L(texto):
    """Uma lista escrita como texto: um item por linha ou separados por |."""
    return [x.strip() for x in texto.replace("\n", "|").split("|") if x.strip()]


# ---------------------------------------------------------------- 1.34.0: as variações dos itens comuns
SABORES = ["chocolate", "morango", "baunilha", "coco", "limão", "maracujá", "doce de leite", "brigadeiro", "chocolate branco",
           "frutas vermelhas", "banana", "abacaxi", "uva", "cereja", "framboesa", "napolitano", "flocos", "creme", "leite ninho",
           "pistache", "amendoim", "café", "caramelo", "menta"]
ERVAS = ["camomila", "erva-doce", "hortelã", "hibisco", "capim-cidreira", "boldo", "frutas vermelhas", "gengibre", "canela",
         "cavalinha", "carqueja", "melissa", "maçã com canela", "limão", "pêssego", "morango", "abacaxi com hortelã", "chá verde com limão",
         "laranja", "jasmim", "rooibos", "mate com limão", "cranberry", "erva-cidreira", "alecrim", "anis-estrelado", "chá branco",
         "chá vermelho", "chá preto com limão", "cereja"]
CORTES_BOI = ["alcatra", "picanha", "maminha", "fraldinha", "contrafilé", "filé mignon", "coxão mole", "coxão duro", "patinho",
              "lagarto", "músculo", "acém", "cupim", "costela", "paleta", "peito", "fígado"]
sec("Variações",
    de("Iogurte", SABORES[:12], "de"), de("Iogurte grego", ["morango", "frutas vermelhas", "coco", "mel", "baunilha", "tradicional"], "de"),
    de("Iogurte natural", ["integral", "desnatado", "com mel"], ""), de("Bebida láctea", SABORES[:8], "de"),
    de("Leite fermentado", ["natural", "light"], ""), de("Sorvete", SABORES, "de"), de("Picolé", ["chocolate", "limão", "uva", "morango", "coco",
    "abacaxi", "maracujá", "milho", "creme", "açaí"], "de"), de("Biscoito recheado", SABORES[:9], "de"), de("Biscoito wafer", SABORES[:7], "de"),
    de("Cookies", ["chocolate", "baunilha", "aveia e mel", "castanha", "gotas de chocolate"], "de"), de("Bolo", ["fubá", "cenoura", "chocolate",
    "laranja", "milho", "aipim", "coco", "banana", "formigueiro", "limão", "maçã", "nozes", "red velvet", "pão de mel", "prestígio", "abacaxi"], "de"),
    de("Mistura para bolo", ["chocolate", "baunilha", "laranja", "milho", "cenoura", "coco", "fubá", "limão", "abacaxi", "formigueiro", "morango",
    "aipim", "banana"], "de"), de("Pizza", ["mussarela", "calabresa", "frango com catupiry", "portuguesa", "marguerita", "quatro queijos",
    "pepperoni", "atum", "palmito", "presunto", "bacon", "chocolate"], "de"), de("Chá", ERVAS, "de"), de("Gelatina", ["morango", "uva", "limão",
    "abacaxi", "cereja", "framboesa", "tutti-frutti", "maracujá", "pêssego", "sem sabor"], "de"), de("Pudim", ["chocolate", "baunilha", "leite condensado", "coco"], "de"),
    de("Mousse", ["maracujá", "chocolate", "limão", "morango"], "de"), de("Suco", ["laranja", "uva", "maçã", "pêssego", "manga", "maracujá", "goiaba",
    "abacaxi", "caju", "acerola", "tangerina", "limão", "melancia", "morango", "graviola", "cupuaçu", "frutas vermelhas", "laranja com acerola",
    "abacaxi com hortelã", "uva integral", "laranja integral", "maçã integral", "tomate", "beterraba", "verde", "detox"], "de"),
    de("Néctar", ["pêssego", "uva", "manga", "maracujá", "goiaba", "abacaxi", "laranja", "caju", "maçã", "morango"], "de"),
    de("Refresco em pó", FRUTAS[:12], "de"), de("Doce", ["leite", "abóbora", "banana", "goiaba", "figo", "mamão", "coco", "batata-doce", "cidra"], "de"),
    de("Geleia", ["morango", "uva", "framboesa", "amora", "damasco", "laranja", "pimenta", "goiaba", "frutas vermelhas", "mocotó"], "de"),
    de("Queijo", ["mussarela fatiado", "prato fatiado", "parmesão ralado", "mussarela ralado", "minas light", "cottage light", "ricota fresca",
    "coalho espeto", "provolone defumado", "gouda fatiado", "cheddar fatiado", "brie em pedaço", "parmesão em pedaço"], ""),
    de("Presunto", ["cozido fatiado", "sem capa de gordura", "parma fatiado", "de peru", "defumado"], ""),
    de("Bife de", CORTES_BOI[:8], ""), de("Carne moída de", ["patinho", "acém", "músculo", "coxão mole", "paleta"], ""),
    de("Linguiça", ["toscana", "calabresa", "de frango", "cuiabana", "apimentada", "defumada", "de pernil", "mista", "fina", "de porco"], ""),
    de("Salsicha", ["hot dog", "de frango", "tipo viena", "de peru", "defumada"], ""),
    de("Hambúrguer", ["bovino", "de frango", "de picanha", "de costela", "vegetal", "de fraldinha", "de peixe"], ""),
    de("Nuggets", ["de frango", "de peixe", "vegetal", "de frango com queijo"], ""),
    de("Desinfetante", ["lavanda", "eucalipto", "pinho", "floral", "talco", "jasmim", "marine", "citrus", "erva-doce", "bambu"], ""),
    de("Detergente", ["neutro", "limão", "coco", "maçã", "clear", "laranja", "glicerina", "erva-doce"], ""),
    de("Amaciante", ["concentrado", "diluído", "para roupas de bebê", "lavanda", "rosas", "floral", "brisa"], ""),
    de("Sabão em pó", ["para roupas brancas", "para roupas coloridas", "com amaciante", "multiação", "3 kg", "4 kg"], ""),
    de("Sabão líquido", ["para roupas brancas", "para roupas coloridas", "para roupas escuras", "concentrado", "refil"], ""),
    de("Shampoo", ["para cabelos cacheados", "para cabelos crespos", "para cabelos lisos", "para cabelos oleosos", "para cabelos secos",
    "para cabelos danificados", "para cabelos tingidos", "para cabelos finos", "antiqueda", "hidratante", "masculino", "anticaspa masculino",
    "detox", "a seco", "sem sal", "de camomila"], ""),
    de("Condicionador", ["para cabelos cacheados", "para cabelos crespos", "para cabelos lisos", "para cabelos oleosos", "para cabelos secos",
    "para cabelos danificados", "infantil", "hidratante"], ""),
    de("Creme para pentear", ["para cabelos cacheados", "para cabelos crespos", "para cabelos lisos", "infantil", "sem enxágue"], ""),
    de("Desodorante", ["aerossol feminino", "aerossol masculino", "roll-on feminino", "roll-on masculino", "sem perfume", "antitranspirante 48h",
    "sem alumínio", "para os pés"], ""),
    de("Sabonete", ["de aveia", "de mel", "de erva-doce", "esfoliante", "hidratante", "para o rosto", "de enxofre", "de carvão", "de glicerina infantil",
    "de coco", "de lavanda", "de rosas", "em barra pacote"], ""),
    de("Creme dental", ["com flúor", "sem flúor", "branqueador", "para gengivas", "herbal", "tripla ação", "gel", "com carvão"], ""),
    de("Ração para cachorro", ["sabor carne", "sabor frango", "sabor cordeiro", "light", "castrado", "raças pequenas", "raças grandes",
    "filhote raças pequenas", "15 kg", "10 kg"], ""),
    de("Ração para gato", ["sabor peixe", "sabor carne", "sabor frango", "sabor salmão", "filhote", "castrado", "10 kg", "urinário"], ""),
)

# frutas, verduras e legumes também orgânicos; os itens de dieta
ORGANICOS = L("""Banana orgânica | Maçã orgânica | Tomate orgânico | Alface orgânica | Cenoura orgânica | Batata orgânica |
    Cebola orgânica | Brócolis orgânico | Couve orgânica | Rúcula orgânica | Morango orgânico | Laranja orgânica | Limão orgânico |
    Abobrinha orgânica | Beterraba orgânica | Pepino orgânico | Mamão orgânico | Café orgânico | Arroz orgânico | Feijão orgânico |
    Leite orgânico | Mel orgânico | Aveia orgânica | Frango orgânico | Azeite orgânico""")
DIETA = ["Pão integral", "Biscoito integral", "Macarrão integral", "Arroz integral", "Iogurte desnatado", "Leite desnatado", "Requeijão light",
         "Queijo cottage", "Peito de peru light", "Refrigerante zero", "Chocolate zero açúcar", "Gelatina zero", "Geleia zero açúcar",
         "Barra de cereal zero", "Achocolatado zero", "Sorvete zero açúcar", "Biscoito sem glúten", "Pão sem glúten", "Macarrão sem glúten",
         "Farinha sem glúten", "Bolo sem glúten", "Leite sem lactose", "Queijo sem lactose", "Requeijão sem lactose", "Iogurte sem lactose",
         "Manteiga sem lactose", "Creme de leite sem lactose", "Leite condensado sem lactose", "Doce de leite sem lactose",
         "Chocolate sem lactose", "Sorvete sem lactose", "Pão vegano", "Queijo vegano", "Hambúrguer vegano", "Maionese vegana",
         "Leite vegetal", "Proteína de soja", "Proteína texturizada de soja", "Carne vegetal", "Frango vegetal", "Tofu defumado"]
sec("Orgânicos e dieta", ORGANICOS, DIETA)

sec("Frutas, verduras e legumes (mais)", L("""Maçã red | Maçã argentina | Pera portuguesa | Pera d'água | Laranja-da-terra | Laranja seleta | Kinkan | Physalis |
    Cajá-manga | Umbu | Pequi | Buriti | Bacuri | Cupuaçu | Jaca | Fruta-pão | Jambo | Pitanga | Mangaba | Sapoti | Abiu | Tamarillo |
    Maracujá doce | Banana-figo | Banana-pacova | Melão cantaloupe | Melão gália | Melão orange | Melancia baby | Uva thompson | Uva niágara |
    Uva rubi | Uva itália | Uva crimson | Morango orgânico | Amora fresca | Mirtilo fresco | Ameixa preta fresca | Nêspera | Cereja fresca |
    Kiwi gold | Lima-da-pérsia | Grapefruit | Toranja | Limão-cravo | Coco ralado fresco | Cana-de-açúcar | Pinhão | Castanha portuguesa |
    Couve chinesa | Acelga chinesa | Pak choi | Endívia | Radicchio | Mostarda em folha | Taioba | Ora-pro-nóbis | Bertalha | Serralha |
    Beldroega | Agrião d'água | Alface americana hidropônica | Alface crespa hidropônica | Rúcula hidropônica | Mix de brotos | Broto de alfafa |
    Microverdes | Salsa crespa | Salsa lisa | Endro | Dill | Sálvia | Estragão | Manjerona | Cebolinha francesa | Capim-santo | Hortelã-pimenta |
    Ervas frescas | Pimenta-de-cheiro | Pimenta jalapeño | Pimenta habanero | Pimenta cambuci | Pimenta-de-bode | Alho negro | Alho roxo |
    Cebola pérola | Cebola branca | Chalota | Echalote | Batata asterix | Batata monalisa | Batata bolinha | Batata yacon | Batata-doce roxa |
    Batata-doce laranja | Mandioca descascada | Mandioca congelada descascada | Inhame chinês | Gengibre fresco | Cúrcuma fresca |
    Raiz-forte | Abóbora japonesa | Abóbora menina | Abóbora seca | Abóbora d'água | Abobrinha brasileira | Abobrinha amarela | Berinjela japonesa |
    Pepino caipira | Pepino conserva | Tomate grape | Tomate holandês | Tomate caqui | Tomate orgânico | Pimentão laranja | Milho verde debulhado |
    Vagem macarrão | Feijão-verde | Fava | Quiabo cortado | Couve picada | Couve-flor congelada | Repolho picado | Cenoura ralada |
    Beterraba cozida | Salada de frutas | Frutas picadas | Abacaxi descascado | Melancia cortada | Coco fresco ralado""")
)
sec("Rotisseria e pratos prontos", L("""Frango assado | Frango de padaria | Galeto | Costela assada | Maionese de batata | Salpicão | Salada de maionese | Farofa de padaria |
    Arroz carreteiro | Feijoada pronta | Feijão tropeiro | Baião de dois | Strogonoff de frango | Strogonoff de carne | Escondidinho de carne seca |
    Lasanha pronta | Nhoque pronto | Macarrão à bolonhesa | Panqueca de carne | Torta de frango | Empadão | Quiche de alho-poró | Esfiha de carne |
    Esfiha de queijo | Coxinha de frango | Risole | Bolinha de queijo | Kibe frito | Pastel de carne | Pastel de queijo | Enroladinho de salsicha |
    Pão de queijo assado | Salgado assado | Sanduíche natural | Wrap de frango | Sushi | Temaki | Hot roll | Yakisoba | Frango xadrez |
    Marmita | Marmita fit | Sopa pronta | Caldo verde | Canja | Purê de batata pronto | Salada pronta | Salada de folhas | Salada caprese |
    Tabule | Homus | Babaganuche | Pasta de grão de bico | Pasta de ricota | Patê de frango caseiro | Antepasto de berinjela""")
)
sec("Confeitaria", L("""Brigadeiro | Beijinho | Cajuzinho | Bicho de pé | Brownie | Blondie | Muffin | Cupcake | Bolo de pote | Bolo no pote | Torta holandesa |
    Torta de limão | Torta de morango | Cheesecake | Pudim de leite | Pavê | Mousse de chocolate pronto | Carolina | Bomba de chocolate | Mil-folhas |
    Sonho de creme | Croissant de chocolate | Pão doce com creme | Pão de coco | Pão de milho | Pão de mandioca | Pão de cebola | Pão de batata doce |
    Pão de cenoura | Rosca de coco | Rosca de leite condensado | Cuca | Cuca de banana | Strudel | Torta alemã | Bolo de rolo | Bolo de casamento |
    Bolo de aniversário | Bolo confeitado | Bolo vulcão | Bolo gelado | Bolo de mandioca | Bolo de cenoura com chocolate | Biscoito amanteigado de padaria |
    Biscoito de nata | Sequilho | Broinha de fubá | Petit four | Macaron | Churros | Alfajor | Pé de moleque caseiro | Doce de abóbora com coco |
    Cocada branca | Cocada queimada | Quindim | Olho de sogra | Bem-casado | Pão de mel com doce de leite | Panetone de frutas | Panetone de chocolate |
    Colomba pascal | Massa de bolo pronta | Pasta americana | Glacê | Corante alimentício | Granulado colorido | Granulado de chocolate | Forminha de brigadeiro |
    Vela de aniversário | Confeito de açúcar | Leite em pó para confeitaria | Gordura hidrogenada | Essência de baunilha | Extrato de baunilha |
    Cacau 100% | Chocolate fracionado | Chocolate em gotas | Cobertura sabor chocolate | Chocolate para derreter | Creme de confeiteiro""")
)
sec("Cozinhas do mundo", L("""Alga nori | Arroz para sushi | Arroz japonês tipo gohan | Gengibre em conserva | Wasabi | Missô | Kani kama | Hashi | Molho tarê |
    Molho teriyaki | Molho agridoce | Molho de ostra | Óleo de gergelim | Vinagre de arroz | Saquê culinário | Mirin | Macarrão udon | Macarrão soba |
    Bifum | Lámen fresco | Massa de guioza | Rolinho primavera | Leite de coco tailandês | Curry tailandês | Pasta de curry | Molho de peixe |
    Tortilha de milho | Tortilha de trigo | Nachos | Guacamole | Molho de queijo cheddar | Salsa mexicana | Feijão refrito | Jalapeño em conserva |
    Taco shell | Pimenta chipotle | Tempero mexicano | Pesto de manjericão | Tomate seco | Funghi seco | Parmesão em lascas | Massa fresca |
    Ravióli de queijo | Ravióli de carne | Capeletti de frango | Tortellini | Gnocchi | Fettuccine | Pappardelle | Mezzi rigatoni | Massa de arroz |
    Polenta pronta | Burrata | Mozzarella de búfala | Presunto cru | Salame milano | Copa lombo | Mortadela italiana | Grana padano | Pecorino romano |
    Azeite trufado | Creme balsâmico | Alcaparras em conserva | Anchova | Pimenta biquinho em conserva | Pão sírio integral | Coalhada seca | Zaatar |
    Tahine | Grão de bico cozido | Faláfel | Quibe cru | Charuto de repolho | Esfiha aberta | Pasta de berinjela | Cuscuz nordestino | Massa de cuscuz |
    Flocão de milho para cuscuz | Tapioca pronta | Goma de tapioca hidratada | Beiju | Carne de sol desfiada | Queijo coalho em espeto | Manteiga de garrafa |
    Charque desfiado | Paçoca de carne | Vatapá | Caruru | Acarajé | Moqueca pronta | Pirão | Pão de queijo mineiro | Doce de leite mineiro |
    Queijo canastra | Queijo serro | Linguiça mineira | Arroz com pequi | Tacacá | Tucupi | Jambu | Farinha d'água | Farinha de tapioca""")
)
sec("Suplementos e fitness", L("""Whey protein chocolate | Whey protein baunilha | Whey protein morango | Whey protein isolado | Whey protein concentrado |
    Creatina monohidratada | BCAA | Glutamina | Albumina | Hipercalórico | Pré-treino | Termogênico | Cafeína em cápsula | Beta-alanina |
    Proteína vegana | Colágeno hidrolisado | Colágeno verisol | Ômega 3 cápsulas | Vitamina D3 gotas | Multivitamínico A-Z | Magnésio dimalato |
    Magnésio quelato | Zinco quelato | Vitamina K2 | Vitamina B12 sublingual | Ferro quelato | Coenzima Q10 | Melatonina gotas | Ashwagandha |
    Spirulina | Chlorella | Maca peruana | Psyllium | Fibra solúvel | Probiótico em cápsula | Pasta de amendoim integral | Pasta de amendoim com whey |
    Barra de proteína chocolate | Barra de proteína cookies | Bebida proteica | Shake proteico | Iogurte proteico | Snack proteico | Panqueca proteica |
    Mistura para panqueca proteica | Café com colágeno | Chá termogênico | Eletrólito | Gel de carboidrato | Isotônico em pó | Coqueteleira""")
)
sec("Bazar e utilidades", L("""Panela de pressão | Panela antiaderente | Frigideira antiaderente | Caçarola | Leiteira | Chaleira | Assadeira | Forma de bolo |
    Forma de pudim | Forma de gelo | Tábua de corte | Faca de cozinha | Faca de pão | Jogo de facas | Tesoura de cozinha | Abridor de latas |
    Saca-rolhas | Descascador | Ralador | Espremedor de alho | Espremedor de laranja | Peneira | Escorredor de macarrão | Escorredor de louça |
    Coador de café | Coador de pano | Garrafa térmica | Bule | Jarra | Copo de vidro | Xícara | Caneca | Prato raso | Prato fundo | Tigela |
    Talheres | Colher de pau | Concha | Escumadeira | Espátula | Pegador de massa | Batedor de ovos | Fouet | Rolo de massa | Medidor de cozinha |
    Balança de cozinha | Pote hermético | Pote de vidro | Marmita de vidro | Garrafa de água | Squeeze | Lancheira | Bolsa térmica | Caixa térmica |
    Saco térmico | Pano de prato de algodão | Avental | Luva térmica | Descanso de panela | Toalha de mesa | Jogo americano | Guardanapo de pano |
    Porta-guardanapo | Saleiro | Açucareiro | Fruteira | Lixeira de pia | Lixeira com pedal | Organizador de geladeira | Organizador de gaveta |
    Cabide | Prendedor de roupa de madeira | Varal de chão | Tábua de passar roupa | Ferro de passar | Cesto organizador | Caixa organizadora |
    Saco a vácuo | Etiqueta | Fita crepe | Fita dupla face | Barbante | Elástico de borracha | Grampo | Clipes | Caneta esferográfica |
    Lápis | Borracha | Apontador | Caderno | Bloco de notas | Post-it | Cola branca | Cola bastão | Tesoura escolar | Régua | Marca-texto |
    Envelope | Papel sulfite | Pasta plástica | Pilha recarregável | Carregador de pilha | Lâmpada fluorescente | Lâmpada de emergência | Lanterna |
    Benjamim | Filtro de linha | Tomada | Interruptor | Chuveiro elétrico | Resistência de chuveiro | Torneira | Rodo de pia | Desentupidor de borracha |
    Mangueira | Regador | Vaso de planta | Terra vegetal | Substrato | Adubo | Fertilizante | Semente de hortaliça | Inseticida para jardim |
    Carvão vegetal | Acendedor de carvão | Grelha | Espeto | Faca de churrasco | Tábua de churrasco | Sal grosso para churrasco | Cooler |
    Cera automotiva | Shampoo automotivo | Pretinho para pneu | Limpa para-brisa | Aditivo para radiador | Óleo de motor | Fluido de freio |
    Flanela para carro | Aromatizador de carro | Vela de aniversário número | Balão de festa | Prato de festa | Copo de festa | Toalha de festa |
    Chapéu de festa | Língua de sogra | Saco de presente | Papel de presente | Fita de cetim | Laço de presente | Cartão de presente""")
)
# 1.34.1: os nomes de cada região para a mesma coisa
sec("Nomes regionais", L("""Bolacha água e sal | Bolacha cream cracker | Bolacha recheada | Bolacha maizena | Bolacha maria | Bolacha de polvilho |
    Bolacha de chocolate | Bolacha doce | Bolacha salgada | Areia de gato | Areia para gato | Macaxeira | Aipim | Jerimum | Bergamota | Mimosa |
    Pão de sal | Cacetinho | Pão careca | Pão jacó | Vina | Jabá | Carne de charque | Feijão de corda | Feijão-macassar | Jabuticaba |
    Cândida | Água de lavadeira | Pasta de dente | Pasta de dentes | Refri | Guaraná | Chimia | Schmier | Cuscuz | Farinha de milho flocada |
    Tapioca de goma | Polvilho | Mortadela de frango | Linguiça de carne | Requeijão de corte | Queijo manteiga | Queijo de coalho | Manteiga da terra |
    Nata de leite | Doce de leite em tablete | Sabão de pedra | Sabão em pedra | Palha de aço | Bombril | Esponja de pia | Rodo de pia |
    Bolinho de chuva | Pão de batata | Salsichão | Cebolinha verde | Cheiro verde | Coentro fresco | Pimenta de cheiro | Vinagrete pronto |
    Pastel de feira | Caldo de cana | Farofa de mandioca | Farinha de puba | Massa puba | Paçoca de amendoim | Cocada mole | Rapadura de leite""")
)
DOSES = {"Losartana": ["25 mg", "100 mg"], "Atorvastatina": ["10 mg", "40 mg", "80 mg"], "Sinvastatina": ["10 mg", "40 mg"],
         "Rosuvastatina": ["10 mg", "20 mg"], "Metformina": ["500 mg", "1 g", "XR 500 mg"], "Anlodipino": ["5 mg", "10 mg"],
         "Enalapril": ["10 mg", "20 mg"], "Hidroclorotiazida": ["25 mg"], "Atenolol": ["25 mg", "50 mg"], "Propranolol": ["40 mg"],
         "Levotiroxina": ["25 mcg", "50 mcg", "75 mcg", "88 mcg", "100 mcg"], "Omeprazol": ["40 mg"], "Pantoprazol": ["20 mg", "40 mg"],
         "Sertralina": ["50 mg", "100 mg"], "Fluoxetina": ["20 mg"], "Escitalopram": ["10 mg", "20 mg"], "Clonazepam": ["0,5 mg", "2 mg", "gotas"],
         "Amoxicilina": ["500 mg", "875 mg", "suspensão"], "Azitromicina": ["500 mg", "suspensão"], "Cefalexina": ["500 mg"],
         "Prednisona": ["5 mg", "20 mg"], "Loratadina": ["10 mg", "xarope"], "Dexametasona": ["4 mg", "creme"], "Diclofenaco": ["50 mg", "gel"],
         "Nimesulida": ["100 mg", "gotas"], "Ibuprofeno": ["200 mg", "suspensão"], "Paracetamol": ["1 g", "infantil"],
         "Dipirona": ["xarope", "infantil"], "Furosemida": ["40 mg"], "Espironolactona": ["25 mg"], "Carvedilol": ["6,25 mg", "12,5 mg", "25 mg"],
         "Glibenclamida": ["5 mg"], "Gliclazida": ["30 mg", "60 mg"], "Clopidogrel": ["75 mg"], "Ácido acetilsalicílico": ["100 mg"],
         "Alendronato": ["70 mg"], "Vitamina D": ["1.000 UI", "7.000 UI", "50.000 UI"], "Sulfato ferroso": ["40 mg"], "Ácido fólico": ["5 mg"],
         "Melatonina": ["3 mg"], "Zolpidem": ["10 mg"], "Quetiapina": ["25 mg"], "Bupropiona": ["150 mg"], "Venlafaxina": ["75 mg"],
         "Amitriptilina": ["25 mg"], "Pregabalina": ["75 mg"], "Gabapentina": ["300 mg"], "Topiramato": ["25 mg", "50 mg"],
         "Tansulosina": ["0,4 mg"], "Finasterida": ["1 mg", "5 mg"], "Sildenafila": ["50 mg"], "Tadalafila": ["5 mg", "20 mg"],
         "Ciprofloxacino": ["500 mg"], "Fluconazol": ["150 mg"], "Albendazol": ["400 mg"], "Ivermectina": ["6 mg"], "Valsartana": ["160 mg"],
         "Olmesartana": ["20 mg", "40 mg"], "Metoprolol": ["50 mg"], "Ezetimiba": ["10 mg"], "Domperidona": ["10 mg"], "Ondansetrona": ["8 mg"],
         "Cetirizina": ["10 mg"], "Desloratadina": ["5 mg"], "Fexofenadina": ["120 mg", "180 mg"], "Hidroxizina": ["25 mg"], "Prednisolona": ["xarope"],
         "Acetilcisteína": ["600 mg", "xarope"], "Ambroxol": ["xarope"], "Simeticona": ["gotas", "40 mg"], "Bromoprida": ["gotas"]}
sec("Farmácia com dosagem", [f"{r} {d}" for r, ds in DOSES.items() for d in ds])


for k, v in MARCAS.items():
    sec("Marcas · " + k, v)

# 1.34.0: as linhas de produtos das marcas mais vendidas, por fabricante (tools/itens_marcas.py)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import itens_marcas  # noqa: E402

for grupo in itens_marcas.TODOS:
    for fabricante, texto in grupo.items():
        sec("Marcas · " + fabricante, L(texto))

# as marcas com o sabor, o tamanho do pacote ou o tipo mais pedidos
def X(marcas, tipos, molde="{m} {t}"):
    return [molde.format(m=m, t=t) for m in marcas for t in tipos]


sec("Marcas · combinações", X(["Danone", "Nestlé", "Batavo", "Vigor", "Itambé", "Piracanjuba"], ["morango", "coco", "frutas vermelhas", "ameixa", "pêssego"],
                              "Iogurte {m} {t}"),
    X(["Passatempo", "Bono", "Trakinas", "Negresco", "Treloso"], ["chocolate", "morango"], "Biscoito {m} {t}"),
    ["Biscoito Bono doce de leite", "Biscoito Oreo original", "Biscoito Oreo chocolate", "Biscoito Trakinas chocolate branco", "Biscoito Passatempo leite"],
    X(["Coca-Cola", "Guaraná Antarctica", "Fanta Laranja", "Pepsi", "Sprite", "Coca-Cola Zero"], ["lata", "2 litros", "600 ml"]),
    X(["Skol", "Brahma", "Heineken", "Amstel", "Budweiser", "Itaipava", "Original", "Stella Artois", "Corona", "Spaten", "Brahma Duplo Malte", "Petra"],
      ["lata", "long neck", "600 ml"], "Cerveja {m} {t}"),
    X(["Del Valle", "Maguary", "Dafruta", "Natural One", "Do Bem"], ["laranja", "uva", "pêssego", "manga", "maracujá", "goiaba"], "Suco {m} {t}"),
    X(["Dove", "Lux", "Protex", "Palmolive", "Nivea", "Rexona"], ["em barra", "líquido"], "Sabonete {m} {t}"),
    X(["Pedigree", "Golden", "Premier", "Dog Chow", "Special Dog", "Magnus"], ["filhote", "adulto", "raças pequenas"], "Ração {m} {t}"),
    X(["Whiskas", "Golden Gatos", "Premier Gatos", "Cat Chow", "Friskies", "Special Cat"], ["filhote", "adulto", "castrado"], "Ração {m} {t}"),
    X(["Pampers", "Huggies", "MamyPoko", "Turma da Mônica", "Babysec", "Pom Pom"], ["P", "M", "G", "XG", "XXG"], "Fralda {m} {t}"),
    X(["Italac", "Piracanjuba", "Parmalat", "Itambé", "Elegê", "Tirol", "Ninho", "Molico"], ["integral", "desnatado", "semidesnatado", "zero lactose"],
      "Leite {m} {t}"),
    X(["Pilão", "3 Corações", "Melitta", "Pelé", "Santa Clara", "Café do Ponto", "Caboclo"], ["tradicional", "extraforte", "a vácuo", "em grãos"],
      "Café {m} {t}"),
    X(["Omo", "Ariel", "Brilhante", "Tixan Ypê", "Surf", "Minuano"], ["em pó", "líquido"], "Lava-roupas {m} {t}"),
    X(["Comfort", "Downy", "Ypê", "Mon Bijou", "Fofo", "Minuano"], ["concentrado", "diluído"], "Amaciante {m} {t}"),
    X(["Pantene", "Seda", "Elseve", "Dove", "TRESemmé", "Fructis", "Head & Shoulders", "Clear"], ["shampoo", "condicionador"], "{t} {m}"),
    X(["Colgate", "Sorriso", "Oral-B", "Close Up", "Sensodyne"], ["creme dental", "escova de dente"], "{t} {m}"),
    X(["Rexona", "Dove", "Nivea", "Axe", "Monange", "Above"], ["aerossol", "roll-on"], "Desodorante {m} {t}"),
    X(["Neve", "Personal", "Mili", "Sublime", "Scott", "Familia"], ["folha dupla", "folha simples", "12 rolos"], "Papel higiênico {m} {t}"),
)

if __name__ == "__main__":
    vistos, linhas, n = set(), ["# Itens comuns de supermercado, hortifrúti, açougue, padaria, farmácia e pet, e as marcas mais",
                                "# vendidas com o produto delas: a base das sugestões ao digitar um item (1.33.0; 1.34.0 com as linhas",
                                "# de produtos de cada fabricante, em tools/itens_marcas.py). Um por linha;",
                                "# as linhas com # são seções. Gerado por tools/itens_comuns.py: mude lá e rode de novo."], 0
    import re  # noqa: PLC0415
    import unicodedata  # noqa: PLC0415
    chave = lambda t: re.sub(r"[^a-z0-9]+", " ", unicodedata.normalize("NFD", t).encode("ascii", "ignore").decode().lower()).strip()  # noqa: E731
    for nome, itens in S.items():
        linhas.append("")
        linhas.append(f"# {nome}")
        for x in itens:
            x = x[:1].upper() + x[1:]
            k = chave(x)  # sem repetir, nem com outro acento
            if k in vistos:
                continue
            vistos.add(k)
            linhas.append(x)
            n += 1
    saida = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "economia", "app", "itens_comuns.txt")
    open(saida, "w", encoding="utf-8").write("\n".join(linhas) + "\n")
    print(n, "itens")
