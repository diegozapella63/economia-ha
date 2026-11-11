"""As linhas de produtos das marcas mais vendidas no Brasil, por fabricante (1.34.0): o que a pessoa digita para achar
o produto ("Biscoito Passatempo", "Leite condensado Moça"). Usado por tools/itens_comuns.py."""

ALIMENTOS = {
    "Nestlé": """Leite condensado Moça | Leite condensado Moça lata | Leite condensado Moça caixinha | Moça Fiesta | Creme de leite Nestlé |
        Creme de leite Nestlé lata | Leite em pó Ninho | Leite em pó Ninho integral | Leite em pó Ninho Forti+ | Ninho Fases 1+ | Ninho Fases 3+ |
        Leite Ninho Zero Lactose | Leite Molico | Leite em pó Molico | Nescau | Achocolatado Nescau | Nescau 2.0 | Nescau Light | Nescau pronto para beber |
        Neston | Neston 3 cereais | Farinha láctea Nestlé | Mucilon | Mucilon arroz e aveia | Mucilon milho | Mucilon multicereais |
        Nescafé Original | Nescafé Matinal | Nescafé Gold | Nescafé Cappuccino | Nescafé Dolce Gusto | Cápsula Dolce Gusto | Cereal Nescau |
        Cereal Snow Flakes | Cereal Nesfit | Cereal Moça Flakes | Cereal Crunch | Cereal Passatempo | Cereal Chocapic | Biscoito Passatempo |
        Biscoito recheado Passatempo | Biscoito Bono | Biscoito Negresco | Biscoito Calipso | Biscoito Tostines | Biscoito São Luiz | Biscoito Nesfit |
        Biscoito Prestígio | Chocolate Classic | Chocolate Alpino | Chocolate Crunch | Chocolate Galak | Chocolate Suflair | Chocolate Prestígio |
        Chocolate Kit Kat | Chocolate Charge | Chocolate Sensação | Chocolate Lollo | Chocolate Chokito | Chocolate Nestlé Blend | Chocolate Surpresa |
        Bombom Especialidades Nestlé | Caixa de bombom Especialidades Nestlé | Chamyto | Chambinho | Iogurte Nestlé | Iogurte Nestlé Grego |
        Iogurte Nestlé Grego light | Iogurte Molico | Leite fermentado Chamyto | Iogurte Ninho | Petit suisse Chambinho | Chandelle |
        Sobremesa Chandelle | Pudim Moça | Picolé La Frutta | Picolé Kit Kat | Sorvete Nestlé | Sorvete Moça | Caldo Maggi | Caldo Maggi galinha |
        Caldo Maggi carne | Tempero Maggi | Macarrão instantâneo Maggi | Sopa Maggi | Maggi Fondor | Nestogeno | Nan | Nan Comfor | Nan Supreme |
        Leite Nan | Ninho Soleil | Sustagen | Nesquik | Nestea | Água Pureza Vital | São Lourenço""",
    "Unilever (alimentos)": """Maionese Hellmann's | Maionese Hellmann's light | Ketchup Hellmann's | Mostarda Hellmann's | Molho Hellmann's |
        Caldo Knorr | Caldo Knorr galinha | Caldo Knorr carne | Caldo Knorr legumes | Knorr Meu Caldo | Sopa Knorr | Creme de cebola Knorr |
        Tempero Knorr | Arroz Knorr | Purê de batata Knorr | Molho Knorr | Sazón | Sazón Ajinomoto | Kibon | Sorvete Kibon | Picolé Kibon |
        Cornetto | Picolé Fruttare | Fruttare | Sorvete Magnum | Magnum | Picolé Chicabon | Chicabon | Eskibon | Tablito | Sorvete Brigadeiro Kibon |
        Sorvete Napolitano Kibon | Sorvete Carte d'Or | Carte d'Or | Sorvete Ben & Jerry's""",
    "Mondelez": """Chocolate Lacta | Chocolate Lacta ao leite | Chocolate Laka | Chocolate Diamante Negro | Chocolate Bis | Bis | Bis Xtra |
        Chocolate Ouro Branco | Bombom Sonho de Valsa | Bombom Ouro Branco | Caixa de bombom Lacta | Chocolate Lacta Intense | Chocolate Shot |
        Chocolate Lacta 5Star | Chocolate Milka | Chocolate Toblerone | Biscoito Oreo | Biscoito Club Social | Club Social | Biscoito Trakinas |
        Biscoito Belvita | Biscoito Lacta | Biscoito Tortinhas Trakinas | Biscoito Club Social integral | Chiclete Trident | Trident |
        Chiclete Bubbaloo | Bubbaloo | Bala Halls | Halls | Chiclete Chiclets | Tang | Suco Tang | Refresco Tang | Clight | Fresh | Royal |
        Gelatina Royal | Fermento Royal | Pudim Royal | Cream cheese Philadelphia | Philadelphia""",
    "PepsiCo": """Batata Ruffles | Ruffles | Batata Lay's | Lay's | Salgadinho Doritos | Doritos | Salgadinho Cheetos | Cheetos | Salgadinho Fandangos |
        Fandangos | Baconzitos | Salgadinho Baconzitos | Torcida | Salgadinho Torcida | Cebolitos | Stiksy | Sensações | Batata Sensações |
        Pingo d'Ouro | Kero Coco | Água de coco Kero Coco | Elma Chips | Batata palha Elma Chips | Amendoim Elma Chips | Toddy |
        Achocolatado Toddy | Toddynho | Cereal Toddy | Aveia Quaker | Quaker | Farinha de aveia Quaker | Aveia em flocos Quaker | Granola Quaker |
        Cereal Quaker | Mabel | Biscoito Mabel | Biscoito Toddy | Cookies Toddy | Pepsi | Pepsi Black | Refrigerante Pepsi | H2OH! | Gatorade |
        Isotônico Gatorade | Lipton Ice Tea | Chá Lipton | Guaraná Antarctica | Sukita | Refrigerante Sukita | Soda Antarctica | Tônica Antarctica""",
    "Kraft Heinz": """Ketchup Heinz | Maionese Heinz | Mostarda Heinz | Molho de tomate Heinz | Molho barbecue Heinz | Molho de tomate Quero |
        Extrato de tomate Quero | Ketchup Quero | Maionese Quero | Milho verde Quero | Ervilha Quero | Seleta de legumes Quero | Atomatado Quero |
        Molho de pimenta Quero | Catchup Quero | Polpa de tomate Quero""",
    "Cargill": """Óleo de soja Liza | Óleo de girassol Liza | Óleo de milho Liza | Óleo de canola Liza | Azeite Gallo | Molho de tomate Pomarola |
        Extrato de tomate Pomarola | Extrato de tomate Elefante | Pomarola | Elefante | Molho de tomate Tarantella | Tarantella | Maionese Mazola |
        Óleo Mazola""",
    "Bunge": """Óleo de soja Soya | Soya | Margarina Delícia | Margarina Primor | Primor | Creme vegetal Primor | Gordura vegetal Primor | Óleo Salada |
        Farinha de trigo Suprema | Azeite Salada | Maionese Primor""",
    "Camil e grãos": """Arroz Camil | Arroz Camil tipo 1 | Arroz Camil integral | Arroz Camil parboilizado | Feijão Camil | Feijão Camil carioca |
        Feijão Camil preto | Açúcar União | Açúcar União refinado | Açúcar União cristal | Açúcar União mascavo | Açúcar Da Barra | Açúcar Caravelas |
        Açúcar Guarani | Açúcar Doce Mel | Açúcar Alto Alegre | Café União | Arroz Tio João | Arroz Tio João tipo 1 | Arroz Tio João integral |
        Arroz Tio João parboilizado | Feijão Tio João | Arroz Prato Fino | Arroz Namorado | Arroz Blue Ville | Arroz Urbano | Arroz Pilecco |
        Arroz Rei Sul | Arroz Broto Legal | Feijão Broto Legal | Feijão Kicaldo | Feijão Kicaldo carioca | Feijão Kicaldo preto | Arroz Kicaldo |
        Arroz Fazenda | Arroz Pop | Arroz Emoções | Arroz Sepé | Feijão Pantera | Feijão Turquesa | Feijão Combrasil | Feijão Biju |
        Arroz Codil | Arroz Saboroso | Arroz Dona Benta | Lentilha Camil | Grão de bico Camil | Pipoca Camil | Canjica Camil""",
    "M. Dias Branco": """Biscoito Vitarella | Biscoito Piraquê | Biscoito Piraquê leite maltado | Biscoito Piraquê goiabinha | Biscoito Piraquê cream cracker |
        Biscoito Piraquê água e sal | Biscoito Piraquê Presuntinho | Biscoito Piraquê Queijinho | Biscoito Piraquê recheado | Biscoito Treloso |
        Treloso | Biscoito Richester | Biscoito Fortaleza | Biscoito Isabela | Biscoito Estrela | Biscoito Pelaggio | Biscoito Basilar | Biscoito Predilleto |
        Macarrão Adria | Macarrão Adria espaguete | Macarrão Adria parafuso | Macarrão Adria com ovos | Macarrão Adria grano duro | Macarrão Vitarella |
        Macarrão Fortaleza | Macarrão Richester | Macarrão Isabela | Macarrão Pilar | Macarrão Basilar | Macarrão Medalha de Ouro | Macarrão instantâneo Adria |
        Torrada Adria | Bolinho Adria | Farinha de trigo Fortaleza | Farinha de trigo Medalha de Ouro | Farinha de trigo Finna | Finna | Margarina Puro Sabor |
        Mistura para bolo Isabela | Mistura para bolo Adria | Snack Frontera | Salgadinho Frontera | Pipoca Vitarella""",
    "Massas e farinhas": """Macarrão Renata | Macarrão Renata espaguete | Macarrão Renata parafuso | Macarrão Renata com ovos | Macarrão Barilla |
        Macarrão Barilla espaguete | Macarrão Barilla penne | Macarrão Santa Amália | Macarrão Dona Benta | Macarrão Petybon | Macarrão Galo |
        Macarrão Divella | Macarrão De Cecco | Macarrão Nissin | Macarrão Paganini | Macarrão Orquídea | Macarrão Germani | Macarrão Mosmann |
        Macarrão Floriani | Macarrão Bonsabor | Macarrão Santa Lúcia | Lasanha Renata | Lasanha Barilla | Macarrão instantâneo Nissin | Miojo |
        Nissin Miojo | Lámen Nissin | Cup Noodles | Nissin Lámen | Macarrão instantâneo Turma da Mônica | Farinha de trigo Dona Benta |
        Farinha de trigo Renata | Farinha de trigo Anaconda | Farinha de trigo Sol | Farinha de trigo Venturelli | Farinha de trigo Rosa Branca |
        Farinha de trigo Nita | Farinha de trigo Boa Sorte | Farinha de trigo Globo | Farinha de trigo Orquídea | Farinha de trigo Mirella |
        Farinha de trigo Anaconda tipo 1 | Mistura para bolo Dona Benta | Mistura para pão Dona Benta | Fubá Yoki | Farinha de mandioca Yoki |
        Farofa Yoki | Pipoca Yoki | Pipoca de micro-ondas Yoki | Amendoim Yoki | Batata palha Yoki | Mistura para bolo Yoki | Polvilho Yoki |
        Canjica Yoki | Tapioca Yoki | Sagu Yoki | Kitano | Tempero Kitano | Orégano Kitano | Pimenta Kitano | Canela Kitano | Fermento Fleischmann |
        Mistura para bolo Fleischmann | Fubá Sinhá | Farinha de milho Sinhá | Flocão Sinhá | Milharina | Fubá Kimilho | Flocão Kimilho |
        Farinha de mandioca Pinduca | Polvilho Amafil | Tapioca Da Terrinha | Massa de pastel Brasileira | Massa de pastel Romanha""",
    "Biscoitos, bolos e panetones": """Biscoito Bauducco | Wafer Bauducco | Torrada Bauducco | Panetone Bauducco | Chocotone Bauducco | Bolinho Bauducco |
        Cookies Bauducco | Biscoito Bauducco Maizena | Biscoito Bauducco Cookies | Pão de mel Bauducco | Bolo Bauducco | Biscoito Visconti |
        Panetone Visconti | Chocotone Visconti | Wafer Visconti | Torrada Visconti | Biscoito Marilan | Biscoito Marilan cream cracker |
        Biscoito Marilan Teens | Biscoito Pit Stop | Pit Stop | Biscoito Marilan Maizena | Biscoito Triunfo | Biscoito Nikito | Biscoito Aymoré |
        Biscoito Mabel Doce de Leite | Biscoito Zezé | Biscoito Fortaleza Maria | Biscoito Tostines Maizena | Biscoito Bono chocolate |
        Biscoito Negresco morango | Biscoito Oreo baunilha | Biscoito Passatempo chocolate | Bolinho Ana Maria | Ana Maria | Bolinho Pullman |
        Bolinho Seven Boys | Bolinho Plus Vita | Bolinho Bauducco Gotas | Rocambole Seven Boys | Panetone Pullman | Panetone Casa Suíça |
        Panetone Village | Panetone Trento | Biscoito Fofura | Biscoito Globo | Biscoito de polvilho Globo | Biscoito Kodilar | Biscoito Dauper |
        Biscoito Liane | Biscoito Mabel cream cracker | Biscoito Água Matilde | Biscoito Tia Sônia | Torrada Magic Toast | Magic Toast |
        Biscoito Club Social Original | Biscoito Belvita aveia | Biscoito Nesfit integral | Barra de cereal Nutry | Nutry | Barra de cereal Trio |
        Barra de cereal Ritter | Barra de proteína Bold | Barra de proteína Nutry | Barra de cereal Quaker | Granola Mãe Terra | Mãe Terra |
        Biscoito Mãe Terra | Tostines | Bauducco""",
    "Doces e chocolates": """Chocolate Garoto | Chocolate Garoto Talento | Chocolate Talento | Chocolate Serenata do Amor | Bombom Serenata do Amor |
        Caixa de bombom Garoto | Chocolate Baton | Baton | Chocolate Crocante Garoto | Chocolate Garoto Meio Amargo | Chocolate Negresco |
        Bombom Garoto | Chocolate Hershey's | Hershey's | Chocolate Hershey's Cookies'n'Creme | Chocolate Kisses | Chocolate Lindt | Lindt |
        Chocolate Lindt Excellence | Chocolate Cacau Show | Cacau Show | Trufa Cacau Show | Bombom Ferrero Rocher | Ferrero Rocher | Nutella |
        Creme de avelã Nutella | Kinder Ovo | Kinder Bueno | Chocolate Kinder | Tic Tac | Chocolate M&M's | M&M's | Chocolate Twix | Twix |
        Chocolate Snickers | Snickers | Chocolate Milky Way | Chocolate Arcor | Bala Arcor | Pirulito Pop | Pirulito Arcor | Bala 7 Belo |
        7 Belo | Chiclete Poosh | Bala Butter Toffees | Butter Toffees | Chocolate Tortuguita | Tortuguita | Bala Fini | Fini | Gelatina Fini |
        Bala Mentos | Mentos | Chiclete Mentos | Bala Freegells | Freegells | Paçoca Paçoquita | Paçoquita | Paçoca Amor | Pé de moleque Santa Helena |
        Amendoim Santa Helena | Mendorato | Amendoim Dori | Dori | Bala Dori | Jujuba Dori | Gomets | Bala de goma Fini | Pirulito Chupa Chups |
        Chupa Chups | Chocolate Montevérgine | Chocolate Neugebauer | Neugebauer | Chocolate Harald | Cobertura Harald | Harald |
        Chocolate em pó Harald | Chocolate Melken | Chocolate em pó Melken | Chocolate em pó Nestlé Dois Frades | Dois Frades | Granulado Mavalério |
        Confeitos Dori | Marshmallow Fini | Goiabada Predilecta | Goiabada Cascão | Doce de leite Itambé | Doce de leite Aviação | Doce de leite Viçosa |
        Doce de leite Mococa | Leite condensado Mococa | Leite condensado Itambé | Leite condensado Piracanjuba | Leite condensado Italac |
        Leite condensado Triângulo | Leite condensado Camponesa | Creme de leite Itambé | Creme de leite Piracanjuba | Creme de leite Italac |
        Creme de leite Mococa | Chantili Amélia | Amélia | Chantilly Vigor | Gelatina Dr. Oetker | Pudim Dr. Oetker | Mistura para bolo Dr. Oetker |
        Fermento Dr. Oetker | Confeitos Dr. Oetker | Dr. Oetker | Geleia Queensberry | Queensberry | Geleia Ritter | Ritter | Geleia Predilecta |
        Pasta de amendoim Dr. Peanut | Dr. Peanut | Pasta de amendoim Integralmédica | Pasta de amendoim Amendupã | Creme de avelã Nucita |
        Adoçante Zero-Cal | Zero-Cal | Adoçante Adocyl | Adocyl | Adoçante Linea | Linea | Adoçante Tal e Qual | Adoçante Finn | Finn |
        Adoçante Stevita | Stevita | Adoçante Doce Menor | Adoçante Assugrin | Assugrin | Adoçante Sucralose Linea | Mel Baldoni | Baldoni""",
    "Temperos, molhos e conservas": """Tempero Arisco | Arisco | Tempero completo Arisco | Caldo Arisco | Ajinomoto | Glutamato Ajinomoto | Hondashi |
        Shoyu Sakura | Sakura | Shoyu Kikkoman | Kikkoman | Shoyu Mitsuwa | Molho inglês Cepêra | Cepêra | Vinagre Castelo | Castelo |
        Vinagre Toscano | Vinagre Minhoto | Vinagre Heinz | Azeite Andorinha | Andorinha | Azeite Borges | Borges | Azeite Carbonell | Carbonell |
        Azeite La Violetera | Azeite O-Live | O-Live | Azeite Cocinero | Cocinero | Azeite Gallo | Gallo | Azeite Português | Azeite Serrata |
        Azeite Paganini | Azeite Figueira da Foz | Óleo Cocamar | Óleo de soja Leve | Óleo de soja Coamo | Óleo de soja Vila Velha | Óleo Sinhá |
        Óleo de soja ABC | Molho de tomate Fugini | Fugini | Extrato de tomate Fugini | Ketchup Fugini | Maionese Fugini | Molho de tomate Predilecta |
        Predilecta | Extrato de tomate Predilecta | Milho verde Predilecta | Ervilha Predilecta | Molho de tomate Salsaretti | Molho de tomate Cajamar |
        Molho de tomate Bonare | Molho de tomate Olé | Olé | Molho de tomate Pomodoro | Molho de tomate Barilla | Molho Barilla | Molho de pimenta Tabasco |
        Tabasco | Molho de pimenta Cepêra | Molho de pimenta Kitano | Molho de pimenta Mineira | Molho de pimenta Ana Maria | Palmito Bonare |
        Bonare | Palmito Predilecta | Azeitona Raiola | Raiola | Azeitona La Violetera | Azeitona Vale Fértil | Vale Fértil | Champignon Raiola |
        Atum Gomes da Costa | Gomes da Costa | Atum ralado Gomes da Costa | Sardinha Gomes da Costa | Patê de atum Gomes da Costa | Atum Coqueiro |
        Coqueiro | Sardinha Coqueiro | Atum Pescador | Pescador | Sardinha 88 | 88 | Sardinha Pescador | Atum Robinson Crusoe | Leite de coco Sococo |
        Sococo | Coco ralado Sococo | Leite de coco Ducoco | Ducoco | Leite de coco Menina | Leite de coco Copra | Copra | Óleo de coco Copra |
        Sal Cisne | Cisne | Sal Lebre | Lebre | Sal Norsal | Sal Smart | Sal Moc | Tempero Sabor Ajinomoto | Tempero Sazón | Tempero Kisabor |
        Tempero Fugini | Alho Arisco | Alho Elefante | Pimenta-do-reino Kitano | Colorau Kitano | Orégano Chinezinho | Chinezinho | Tempero Chinezinho |
        Pimenta Chinezinho | Canela Chinezinho | Cravo Chinezinho | Coentro Chinezinho | Batata palha Visconti | Batata palha Pingo d'Ouro |
        Batata palha Sinhá | Batata palha Kró | Kró | Batata palha Crocantíssima | Farofa Kisabor | Farofa Pronta Yoki | Farofa Hikari | Hikari""",
    "Café e chá": """Café Pilão | Pilão | Café Pilão tradicional | Café Pilão extraforte | Café Pilão a vácuo | Café Pilão em cápsula | Café 3 Corações |
        3 Corações | Café 3 Corações tradicional | Café 3 Corações extraforte | Cápsula 3 Corações | Cápsula Três | Café Melitta | Melitta |
        Café Melitta tradicional | Café Melitta extraforte | Filtro de papel Melitta | Filtro de café Melitta | Café Pelé | Pelé | Café Santa Clara |
        Santa Clara | Café do Ponto | Café Caboclo | Caboclo | Café Seleto | Seleto | Café Marata | Café Maratá | Café Pimpinela | Café Bom Jesus |
        Café Damasco | Damasco | Café Baggio | Baggio | Café Utam | Café Brasileiro | Café Cajubá | Café Toko | Café Odebrecht | Café Iguaçu |
        Café Solúvel Iguaçu | Café Orfeu | Orfeu | Café Fazenda Rio Grande | Café Starbucks | Café L'Or | Cápsula L'Or | Cápsula Nespresso |
        Nespresso | Café Nescafé Dolce Gusto | Café Solúvel Nescafé | Café Solúvel Pelé | Cappuccino 3 Corações | Cappuccino Pilão | Cappuccino Melitta |
        Cappuccino Nescafé | Chá Leão | Leão | Chá Matte Leão | Matte Leão | Chá mate Leão | Chá Dr. Oetker | Chá Twinings | Twinings |
        Chá Lipton | Chá Real | Chá Celestial | Chá Mais Leve | Erva-mate Barão | Barão | Erva-mate Ximango | Ximango | Erva-mate Mate Laranjeiras |
        Erva-mate Rei Verde | Erva-mate Campeiro | Erva-mate Seiva Pura | Erva-mate Madrugada | Chimarrão Barão | Filtro de papel 3 Corações |
        Filtro de papel Brigitta | Filtro de papel Bom Jesus""",
    "Laticínios": """Leite Italac | Italac | Leite Piracanjuba | Piracanjuba | Leite Parmalat | Parmalat | Leite Itambé | Itambé | Leite Elegê | Elegê |
        Leite Tirol | Tirol | Leite Jussara | Jussara | Leite Batavo | Batavo | Leite Aviação | Leite Shefa | Shefa | Leite Lider | Leite Quatá | Quatá |
        Leite Betânia | Betânia | Leite Camponesa | Camponesa | Leite Vigor | Leite Ninho Forti+ | Leite Frimesa | Frimesa | Leite Polly |
        Leite Danby | Leite Dalia | Leite Cativa | Cativa | Leite Lactalis | Leite Président | Leite Zero Lactose Piracanjuba |
        Leite Zero Lactose Italac | Leite Zero Lactose Parmalat | Leite Zero Lactose Itambé | Leite Zero Lactose Elegê | Leite Zero Lactose Tirol |
        Leite Nestlé Zero Lactose | Leite Liane Zero Lactose | Leite Liane | Leite Cooperativa | Leite Languiru | Languiru | Leite Santa Clara |
        Leite Piá | Piá | Leite Verde Campo | Verde Campo | Leite Holandês | Iogurte Danone | Danone | Iogurte Activia | Activia | Danoninho |
        Iogurte Danone Grego | Danone Grego | Iogurte Corpus | Corpus | Iogurte Danio | Danio | Iogurte YoPRO | YoPRO | Iogurte Batavo |
        Iogurte Batavo Pense Zero | Pense Zero | Iogurte Vigor | Iogurte Grego Vigor | Vigor | Iogurte Itambé | Iogurte Piracanjuba |
        Iogurte Italac | Iogurte Elegê | Iogurte Tirol | Iogurte Frimesa | Iogurte Verde Campo | Iogurte Paulista | Paulista | Iogurte Nestlé Grego |
        Iogurte Molico Zero | Yakult | Leite fermentado Yakult | Yakult 40 | Sofyl | Leite fermentado Batavo | Requeijão Catupiry | Catupiry |
        Requeijão Vigor | Requeijão Itambé | Requeijão Danúbio | Danúbio | Requeijão Poços de Caldas | Poços de Caldas | Requeijão Tirolez |
        Tirolez | Requeijão Polenghi | Requeijão Nestlé | Requeijão Piracanjuba | Requeijão Italac | Requeijão Elegê | Requeijão Batavo |
        Requeijão Président | Requeijão Scala | Scala | Requeijão Quatá | Requeijão Verde Campo | Cream cheese Philadelphia | Cream cheese Polenghi |
        Cream cheese Scala | Queijo Polenghi | Polenghi | Polenguinho | Queijo Tirolez | Queijo Président | Président | Queijo Faixa Azul | Faixa Azul |
        Queijo Quatá | Queijo Vigor | Queijo Scala | Queijo Sadia | Queijo Itambé | Queijo Piracanjuba | Queijo Ipanema | Queijo Teixeira |
        Queijo Damare | Queijo Cruzília | Queijo Regina | Queijo Santa Amália | Queijo Coalho Sertanejo | Queijo Davaca | Queijo Gran Mestri |
        Gran Mestri | Queijo Parmesão Faixa Azul | Queijo Parmesão Vigor | Queijo ralado Vigor | Queijo ralado Faixa Azul | Queijo ralado Quatá |
        Queijo ralado Président | Manteiga Aviação | Aviação | Manteiga Itambé | Manteiga Président | Manteiga Tirolez | Manteiga Piracanjuba |
        Manteiga Batavo | Manteiga Vigor | Manteiga Elegê | Manteiga Scala | Manteiga Italac | Manteiga Frimesa | Manteiga Ghee Benni |
        Margarina Qualy | Qualy | Margarina Doriana | Doriana | Margarina Becel | Becel | Margarina Claybom | Claybom | Margarina Vigor |
        Margarina Sadia | Creme vegetal Becel | Margarina Deline | Deline | Margarina Soya | Margarina Mila | Margarina Coamo""",
}

CARNES_PAES_CONGELADOS = {
    "BRF": """Sadia | Presunto Sadia | Mortadela Sadia | Salsicha Sadia | Linguiça Sadia | Linguiça toscana Sadia | Linguiça calabresa Sadia |
        Peito de peru Sadia | Salame Sadia | Bacon Sadia | Hambúrguer Sadia | Nuggets Sadia | Empanado Sadia | Steak Sadia | Lasanha Sadia |
        Pizza Sadia | Frango Sadia | Peito de frango Sadia | Coxinha da asa Sadia | Sassami Sadia | Chester Sadia | Peru Sadia | Lombo Sadia |
        Pão de queijo Sadia | Margarina Sadia | Hot Pocket Sadia | Hot Pocket | Kibe Sadia | Almôndega Sadia | Escondidinho Sadia | Speciale Sadia |
        Sadia Bio | Presunto Sadia sem capa | Requeijão Sadia | Perdigão | Presunto Perdigão | Mortadela Perdigão | Salsicha Perdigão |
        Linguiça Perdigão | Peito de peru Perdigão | Hambúrguer Perdigão | Nuggets Perdigão | Lasanha Perdigão | Pizza Perdigão | Chester Perdigão |
        Frango Perdigão | Empanado Perdigão | Perdigão Na Brasa | Linguiça Perdigão Na Brasa | Apresuntado Perdigão | Batavo | Qualy""",
    "JBS": """Seara | Presunto Seara | Mortadela Seara | Salsicha Seara | Linguiça Seara | Peito de peru Seara | Hambúrguer Seara | Nuggets Seara |
        Empanado Seara | Lasanha Seara | Pizza Seara | Frango Seara | Peito de frango Seara | Coxinha da asa Seara | Bacon Seara | Kibe Seara |
        Seara Gourmet | Seara Da Granja | Seara Incrível | Hambúrguer Incrível | Frango Incrível | Margarina Seara | Friboi | Carne Friboi |
        Picanha Friboi | Maminha Friboi | Alcatra Friboi | Fraldinha Friboi | Contrafilé Friboi | Carne moída Friboi | Friboi Maturatta | Maturatta |
        Swift | Hambúrguer Swift | Salsicha Swift | Picanha Swift | Batata Swift | Pão de queijo Swift | Massa Leve | Margarina Doriana | Primor""",
    "Outros frigoríficos": """Aurora | Presunto Aurora | Mortadela Aurora | Salsicha Aurora | Linguiça Aurora | Frango Aurora | Bacon Aurora | Pernil Aurora |
        Lombo Aurora | Copacol | Frango Copacol | Coxa e sobrecoxa Copacol | Filé de peito Copacol | Tilápia Copacol | Lar | Frango Lar |
        Frango a passarinho Lar | Peito de frango Lar | Coxa de frango Lar | Asa de frango Lar | C.Vale | Frango C.Vale | Frimesa | Presunto Frimesa |
        Mortadela Frimesa | Salsicha Frimesa | Linguiça Frimesa | Pif Paf | Pão de queijo Pif Paf | Frango Pif Paf | Lasanha Pif Paf | Rezende |
        Salsicha Rezende | Mortadela Rezende | Marba | Mortadela Marba | Presunto Marba | Ceratti | Mortadela Ceratti | Salame Ceratti |
        Mortadela Bologna Ceratti | Minerva | Minerva Foods | Marfrig | Bassi | Picanha Bassi | Frango Korin | Korin | Ovos Korin | Frango Diplomata |
        Diplomata | Frango Jaguá | Frango Bello | Frango Canção | Frango Avivar | Frango Rivelli | Frango Pioneiro | Frango Ad'oro | Frango Alliz |
        Frango Seara Nature | Frango Granja Faria | Ovos Mantiqueira | Mantiqueira | Ovos Happy Eggs | Ovos Granja Faria | Granja Faria |
        Ovos Yabuta | Tilápia Tilabras | Peixe Gomes da Costa | Salmão Pescanova | Bacalhau Riberalves | Bacalhau Gadus Morhua | Camarão Costa Sul |
        Seara Bacalhau | Pescanova | Linguiça Saudali | Saudali | Presunto Saudali | Mortadela Confiança | Salsicha Hot Dog Pif Paf |
        Linguiça Alegra | Alegra | Lombo Alegra | Bacon Alegra | Prieto | Linguiça Prieto | Salame Prieto | Copa Prieto | Salame Aurora |
        Defumados Frimesa | Peito de peru Rezende | Presunto Pif Paf""",
    "Pães e padaria": """Pão de forma Pullman | Pullman | Pão Pullman integral | Bisnaguinha Pullman | Pão de hambúrguer Pullman | Pão de forma Seven Boys |
        Seven Boys | Bisnaguinha Seven Boys | Pão de hot dog Seven Boys | Pão de forma Wickbold | Wickbold | Pão Wickbold 5 Zero | Pão Wickbold Leve |
        Pão de forma Plus Vita | Plus Vita | Pão Plus Vita integral | Pão de forma Nutrella | Nutrella | Pão Nutrella integral | Pão de forma Visconti |
        Pão de forma Panco | Panco | Bisnaguinha Panco | Pão de forma Bimbo | Bimbo | Rap10 | Rap10 integral | Tortilha Bimbo | Pão de forma Ana Maria |
        Pão de forma Bauducco | Pão Pão de Açúcar | Pão Qualitá | Pão de forma Romanha | Pão de forma Firenze | Pão de forma Dom Paulo | Pão Bauducco |
        Torrada Wickbold | Torrada Visconti integral | Pão sírio Wickbold | Pão de queijo Forno de Minas | Forno de Minas | Pão de queijo Massa Leve |
        Pão de queijo Yoki | Pão de queijo Bauducco | Pão de queijo Pif Paf | Pão de queijo Sadia | Pão de queijo Seara | Pão de queijo Minas Mais |
        Biscoito de queijo Forno de Minas | Chipa Forno de Minas | Massa de pizza Massa Leve | Massa de pastel Massa Leve | Massa Leve""",
    "Congelados": """Batata McCain | McCain | Batata palito McCain | Batata Smiles McCain | Batata rústica McCain | Batata Bem Brasil | Bem Brasil |
        Batata Pratigel | Batata Simplot | Batata Lamb Weston | Polenta Bem Brasil | Mandioca Bem Brasil | Brócolis Pratigel | Pratigel |
        Seleta Pratigel | Ervilha Pratigel | Vegetais Bonduelle | Bonduelle | Milho Bonduelle | Ervilha Bonduelle | Grão de bico Bonduelle |
        Açaí Frooty | Frooty | Açaí Oakberry | Açaí Tia Sônia | Açaí Yoki | Polpa de fruta DeMarchi | DeMarchi | Polpa de fruta Ricaeli | Ricaeli |
        Polpa de fruta Mais Fruta | Polpa de fruta Bela Ischia | Sorvete Jundiá | Jundiá | Sorvete Cremosy | Cremosy | Sorvete Häagen-Dazs |
        Häagen-Dazs | Sorvete Diletto | Diletto | Sorvete Frutos do Brasil | Sorvete Sorvetão | Sorvete Garoto | Sorvete Nestlé | Sorvete Kibon |
        Sorvete Rochinha | Sorvete Pardal | Sorvete Lacta | Sorvete Bauducco | Picolé Kibon | Picolé Nestlé | Lasanha Sadia | Lasanha Perdigão |
        Lasanha Seara | Lasanha Pif Paf | Lasanha Massa Leve | Pizza Sadia | Pizza Seara | Pizza Perdigão | Pizza Dr. Oetker | Pizza Pif Paf |
        Pizza Massa Leve | Pizza Mama Mia | Strogonoff Sadia | Escondidinho Seara | Prato pronto Sadia | Prato pronto Seara | Hambúrguer Big Burger |
        Mini pizza Seara | Coxinha Sadia | Coxinha Seara | Esfiha Sadia | Bolinha de queijo Sadia | Steak Seara | Filé de peixe Seara |
        Peixe empanado Sadia | Camarão empanado Sadia | Waffle Forno de Minas | Gelo Polar | Gelo em cubo""",
}

BEBIDAS = {
    "Coca-Cola": """Coca-Cola | Coca-Cola Zero | Coca-Cola sem açúcar | Coca-Cola lata | Coca-Cola 2 litros | Coca-Cola 600 ml | Coca-Cola Café |
        Refrigerante Coca-Cola | Fanta | Fanta Laranja | Fanta Uva | Fanta Guaraná | Fanta Maracujá | Fanta Zero | Sprite | Sprite Zero | Kuat |
        Guaraná Kuat | Schweppes | Água tônica Schweppes | Schweppes Citrus | Del Valle | Suco Del Valle | Del Valle Frut | Néctar Del Valle |
        Del Valle 100% | Água mineral Crystal | Crystal | Água Crystal com gás | Powerade | Isotônico Powerade | Monster | Energético Monster |
        Monster Ultra | Chá Leão Fuze | Fuze Tea | Ades | Bebida de soja Ades | Água de coco Verde Campo""",
    "Ambev": """Skol | Cerveja Skol | Skol Pilsen | Skol Puro Malte | Skol Hops | Skol Beats | Brahma | Cerveja Brahma | Brahma Duplo Malte |
        Brahma Chopp | Brahma Zero | Antarctica | Cerveja Antarctica | Antarctica Original | Original | Cerveja Original | Antarctica Subzero |
        Budweiser | Cerveja Budweiser | Budweiser Zero | Stella Artois | Cerveja Stella Artois | Stella Pure Gold | Corona | Cerveja Corona |
        Corona Extra | Beck's | Cerveja Beck's | Spaten | Cerveja Spaten | Michelob Ultra | Bohemia | Cerveja Bohemia | Colorado | Cerveja Colorado |
        Patagonia | Cerveja Patagonia | Goose Island | Wäls | Serramalte | Polar | Cerveja Polar | Caracu | Cerveja Caracu | Malzbier Brahma |
        Guaraná Antarctica | Guaraná Antarctica Zero | Soda Limonada Antarctica | Pepsi | Sukita | Tônica Antarctica | H2OH! | Gatorade | Lipton Ice Tea |
        Fusion | Energético Fusion | Beats | Mike's | Água AMA""",
    "Heineken e Petrópolis": """Heineken | Cerveja Heineken | Heineken Zero | Heineken lata | Heineken long neck | Amstel | Cerveja Amstel | Amstel Ultra |
        Devassa | Cerveja Devassa | Eisenbahn | Cerveja Eisenbahn | Baden Baden | Cerveja Baden Baden | Kaiser | Cerveja Kaiser | Bavaria |
        Cerveja Bavaria | Sol | Cerveja Sol | Tiger | Blue Moon | Lagunitas | Schin | Cerveja Schin | Glacial | Cerveja Glacial | Itubaína |
        Refrigerante Itubaína | Água Schin | Itaipava | Cerveja Itaipava | Itaipava Premium | Petra | Cerveja Petra | Crystal | Cerveja Crystal |
        Black Princess | Cerveja Black Princess | Lokal | Cerveja Lokal | Weltenburger | Tnt | Energético TNT | Blue Spirit Ice | Cabaré Ice |
        Refrigerante Petrópolis | Império | Cerveja Império | Proibida | Cerveja Proibida | Conti | Cerveja Conti | Bierland | Cerveja Bierland""",
    "Refrigerantes, sucos e águas": """Refrigerante Dolly | Dolly | Guaraná Dolly | Refrigerante Convenção | Guaraná Jesus | Refrigerante Mineirinho | Mineirinho |
        Refrigerante Cotuba | Refrigerante Funada | Refrigerante Charrua | Refrigerante Frevo | Guaraná Fruki | Fruki | Refrigerante Goianinho |
        Refrigerante Simba | Refrigerante Tubaína | Tubaína | Refrigerante Xereta | Guaraná Real | Refrigerante It | Água mineral Bonafont | Bonafont |
        Água mineral Lindoya | Lindoya | Água mineral São Lourenço | Água mineral Minalba | Minalba | Água mineral Indaiá | Indaiá |
        Água mineral Petrópolis | Água mineral Prata | Água mineral Ouro Fino | Ouro Fino | Água mineral Fonte Ijuí | Água mineral Santa Bárbara |
        Água mineral Igarapé | Água mineral Serra da Canastra | Água mineral Puríssima | Água mineral Schin | Água mineral Acqua Lia | Acqua Lia |
        Água mineral Perrier | Perrier | Água San Pellegrino | San Pellegrino | Água Evian | Água Fiji | Água de coco Obrigado | Obrigado |
        Água de coco Kero Coco | Água de coco Ducoco | Água de coco Mais Coco | Água de coco Puro Coco | Suco Maguary | Maguary | Suco Dafruta |
        Dafruta | Suco Do Bem | Do Bem | Suco Natural One | Natural One | Suco Tial | Tial | Suco Sufresh | Sufresh | Suco Prats | Prats |
        Suco Aurora | Suco de uva Aurora | Suco de uva Casa de Bento | Suco de uva Garibaldi | Suco de uva Salton | Suco de uva Tetê | Suco Mid | Mid |
        Suco Frisco | Frisco | Suco Qualimax | Suco Camp | Suco Vitao | Suco Ki-Suco | Ki-Suco | Suco Tang | Suco Fresh | Suco Clight |
        Suco Xereta | Suco Feel Good | Feel Good | Suco Purity | Suco Greenpeople | Kombucha Tao | Kombucha Companhia dos Fermentados |
        Kombucha Fermentaria | Isotônico Gatorade | Isotônico Powerade | Isotônico Marathon | Energético Red Bull | Red Bull | Red Bull Sugarfree |
        Energético Monster | Energético Burn | Burn | Energético Baly | Baly | Energético Flash Power | Energético Night Power | Energético Vibe |
        Energético Furioso | Energético 220V | Energético Fusion | Chá gelado Leão | Chá Matte Leão gelado | Mate Couro | Guaraviton |
        Guaraná Viton | Guaraná Power | Café gelado Starbucks""",
    "Vinhos e destilados": """Vinho Casillero del Diablo | Casillero del Diablo | Vinho Concha y Toro | Concha y Toro | Vinho Reservado Concha y Toro |
        Vinho Santa Helena | Santa Helena | Vinho Santa Carolina | Vinho Gato Negro | Gato Negro | Vinho Alma Mora | Vinho Pérgola | Pérgola |
        Vinho Salton | Salton | Vinho Miolo | Miolo | Vinho Aurora | Vinho Chalise | Chalise | Vinho Quinta do Morgado | Quinta do Morgado |
        Vinho Sangue de Boi | Sangue de Boi | Vinho Canção | Vinho Campo Largo | Campo Largo | Vinho Casa Valduga | Casa Valduga | Vinho Almadén |
        Almadén | Vinho Periquita | Vinho Catena | Vinho Trapiche | Vinho Norton | Vinho El Enemigo | Vinho Cordero con Piel de Lobo |
        Vinho Dom Bosco | Vinho Galiotto | Vinho Country Wine | Vinho Bordô | Vinho Château Duvalier | Vinho Frontera | Vinho Undurraga |
        Vinho Cono Sur | Vinho Santa Rita | Vinho 120 | Vinho Lambrusco | Lambrusco | Vinho Porto Ferreira | Porto Ferreira | Espumante Chandon |
        Chandon | Espumante Salton | Espumante Aurora | Espumante Freixenet | Freixenet | Espumante Garibaldi | Espumante Peterlongo | Peterlongo |
        Espumante Casa Valduga | Espumante Miolo | Espumante Cereser | Sidra Cereser | Cereser | Sidra Peterlongo | Champanhe Moët & Chandon |
        Cachaça 51 | Cachaça Ypióca | Ypióca | Cachaça Velho Barreiro | Velho Barreiro | Cachaça Sagatiba | Cachaça Pitú | Pitú | Cachaça Seleta |
        Cachaça Salinas | Cachaça Sapupara | Cachaça Leblon | Cachaça Boazinha | Cachaça Tatuzinho | Cachaça Caninha da Roça | Cachaça Chico Mineiro |
        Cachaça Vale Verde | Cachaça Espírito de Minas | Vodca Smirnoff | Smirnoff | Vodca Absolut | Absolut | Vodca Orloff | Orloff | Vodca Askov |
        Askov | Vodca Natasha | Vodca Ketel One | Vodca Grey Goose | Vodca Belvedere | Vodca Skyy | Vodca Kovak | Vodca Balalaika | Uísque Johnnie Walker |
        Johnnie Walker | Johnnie Walker Red Label | Red Label | Johnnie Walker Black Label | Black Label | Uísque Jack Daniel's | Jack Daniel's |
        Uísque Ballantine's | Ballantine's | Uísque Chivas Regal | Chivas | Uísque White Horse | White Horse | Uísque Passport | Passport |
        Uísque Old Parr | Old Parr | Uísque Buchanan's | Buchanan's | Uísque Jim Beam | Jim Beam | Uísque Jameson | Jameson | Uísque Grant's |
        Uísque J&B | Uísque Teacher's | Uísque Black & White | Uísque Natu Nobilis | Uísque Old Eight | Uísque Bell's | Uísque Dewar's |
        Gim Tanqueray | Tanqueray | Gim Beefeater | Beefeater | Gim Bombay Sapphire | Bombay | Gim Gordon's | Gordon's | Gim Seagers | Seagers |
        Gim Hendrick's | Gim Amázzoni | Gim Rocks | Gim Eternity | Rum Bacardi | Bacardi | Rum Montilla | Montilla | Rum Havana Club | Havana Club |
        Rum Captain Morgan | Tequila José Cuervo | José Cuervo | Tequila Olmeca | Tequila Sauza | Licor 43 | Licor Baileys | Baileys | Licor Amarula |
        Amarula | Licor Cointreau | Licor Frangelico | Licor Jägermeister | Jägermeister | Licor Fireball | Campari | Aperol | Martini | Martini Bianco |
        Cinzano | Conhaque Dreher | Dreher | Conhaque Domecq | Conhaque São João da Barra | Catuaba Selvagem | Catuaba | Corote | Smirnoff Ice |
        Skol Beats | Beats Senses | Ice Kiss | Vinho Quinta do Morgado suave | Vermute Contini | Steinhäger Becosa | Saquê Azuma | Saquê Sagaz |
        Licor Stock | Licor de cacau Stock | Licor Bols | Bitter Campari | Underberg | Fernet Branca | Malibu""",
}

CASA = {
    "Ypê": """Ypê | Detergente Ypê | Detergente Ypê neutro | Detergente Ypê limão | Detergente Ypê coco | Detergente Ypê clear | Lava-louças Ypê |
        Lava-louças Ypê Concentrado | Lava-roupas Ypê | Lava-roupas líquido Ypê | Lava-roupas Ypê Power Act | Ypê Power Act | Sabão em pó Tixan Ypê |
        Tixan Ypê | Tixan | Lava-roupas Tixan Ypê | Amaciante Ypê | Amaciante Ypê concentrado | Amaciante Ypê Essencial | Desinfetante Ypê |
        Desinfetante Ypê Bak | Multiuso Ypê | Limpador Multiuso Ypê | Sabão em barra Ypê | Sabão de coco Ypê | Água sanitária Ypê | Alvejante Ypê |
        Tira manchas Ypê | Limpa vidros Ypê | Limpador perfumado Ypê | Esponja Ypê | Assolan | Esponja de aço Assolan | Lã de aço Assolan | Perfex |
        Pano Perfex | Atol | Ypê Premium | Sabonete Ypê | Lava-louças Ypê Green | Ypê Green | Gel sanitário Ypê | Limpa banheiro Ypê""",
    "Unilever (casa)": """Omo | Sabão em pó Omo | Lava-roupas líquido Omo | Omo líquido | Omo Lavagem Perfeita | Omo Puro Cuidado | Omo Multiação |
        Omo Sports | Omo cápsulas | Comfort | Amaciante Comfort | Amaciante Comfort concentrado | Comfort Puro Cuidado | Brilhante | Sabão em pó Brilhante |
        Lava-roupas líquido Brilhante | Brilhante líquido | Surf | Sabão em pó Surf | Lava-roupas Surf | Cif | Limpador Cif | Saponáceo Cif |
        Cif cremoso | Cif multiuso | Cif tira limo | Cif banheiro | Cif cozinha | Cif vidros | Cif lava-louças | Minerva | Sabão em pó Minerva""",
    "P&G (casa)": """Ariel | Sabão em pó Ariel | Lava-roupas líquido Ariel | Ariel líquido | Ariel cápsulas | Ace | Sabão em pó Ace | Downy | Amaciante Downy |
        Downy concentrado | Downy perfume | Downy Brisa de Verão | Downy Lírios do Campo | Febreze | Odorizador Febreze | Pampers""",
    "Reckitt": """Vanish | Tira manchas Vanish | Tira manchas Vanish Oxi Action | Vanish Oxi Action | Vanish Crystal White | Vanish líquido | Vanish em pó |
        Vanish Gold | Vanish Poder O2 | Alvejante Vanish | Veja | Limpador Veja | Veja multiuso | Veja Limpeza Pesada | Veja Gold | Veja Vidrex |
        Vidrex | Veja Banheiro X-14 | X-14 | Limpador X-14 | Veja Cozinha | Veja Desengordurante | Veja Perfumes | Veja Naturals | Harpic |
        Gel sanitário Harpic | Harpic Power Plus | Harpic pastilha | Lysoform | Desinfetante Lysoform | Lysoform bruto | Lysoform spray | Lysol |
        Lysol spray | Desinfetante Lysol | Air Wick | Aromatizador Air Wick | Bom Ar | Aromatizador Bom Ar | Bom Ar Air Wick | SBP | Inseticida SBP |
        Repelente SBP | SBP multi-insetos | SBP elétrico | Finish | Lava-louças Finish | Pastilha Finish | Secante Finish | Sal Finish | Detergente Finish |
        Mortein | Durex | Preservativo Durex | Dettol | Sabonete Dettol | Calgon""",
    "Colgate-Palmolive (casa)": """Pinho Sol | Desinfetante Pinho Sol | Pinho Sol original | Pinho Sol lavanda | Ajax | Limpador Ajax | Ajax Fiesta das Flores |
        Ajax Bicarbonato | Ajax multiuso | Murphy | Sabão Murphy""",
    "Bombril e outras": """Bombril | Esponja de aço Bombril | Esponja Bombril | Lã de aço Bombril | Mon Bijou | Amaciante Mon Bijou | Limpol | Detergente Limpol |
        Lava-louças Limpol | Pinho Bril | Desinfetante Pinho Bril | Kalipto | Desinfetante Kalipto | Sapólio Radium | Radium | Saponáceo Radium |
        Brilhol | Limpador Brilhol | Pratice | Lava-roupas Pratice | Sanol | Desinfetante Sanol | Qboa | Água sanitária Qboa | Alvejante Qboa |
        Água sanitária Candura | Candura | Água sanitária Super Globo | Super Globo | Água sanitária Brilux | Água sanitária Dragão | Água sanitária Clorox |
        Água sanitária Ypê | Água sanitária Nobre | Água sanitária Girando Sol | Girando Sol | Amaciante Girando Sol | Lava-roupas Girando Sol |
        Detergente Girando Sol | Minuano | Detergente Minuano | Amaciante Minuano | Sabão em pó Minuano | Sabão em barra Minuano | Desinfetante Minuano |
        Assim | Sabão em pó Assim | Amaciante Assim | Detergente Assim | Fofo | Amaciante Fofo | Urca | Amaciante Urca | Detergente Urca |
        Sabão em barra Urca | Flor de Ypê | Sabão em barra Fazendeiro | Fazendeiro | Sabão Rio | Sabão Granado | Sabão de coco Granado | Sabão Pantera |
        Sabão Bem-te-vi | Sabão Barra Vitória | Detergente Clear | Detergente Brilhante | Detergente Pril | Pril | Detergente Lava Bem | Detergente Toque de Brilho |
        Diabo Verde | Desentupidor Diabo Verde | Desentupidor Destop | Destop | Mr. Músculo | Limpador Mr. Músculo | Mr. Músculo cozinha |
        Mr. Músculo banheiro | Pato | Pato purific | Pato gel adesivo | Pato pastilha | Pato desinfetante | Glade | Aromatizador Glade | Glade automático |
        Glade toque de frescor | Odorizador Glade | Raid | Inseticida Raid | Raid elétrico | Repelente Raid | Off | Repelente Off | Off Kids | Baygon |
        Inseticida Baygon | Repelente Exposis | Exposis | Repelente Repelex | Repelex | Ultrathon | Poliflor | Lustra móveis Poliflor | Cera Poliflor |
        Cera Brilho Fácil | Brilho Fácil | Cera Grand Prix | Grand Prix | Lustra móveis Peroba | Óleo de peroba | Peroba | Limpa alumínio Ypê |
        Limpa alumínio Brilhante | Limpa alumínio Mon Bijou | Álcool Tupi | Tupi | Álcool Coperalcool | Álcool Zulu | Zulu | Álcool Start | Start |
        Álcool Santa Cruz | Álcool Prolink | Álcool em gel Asseptgel | Asseptgel | Álcool em gel Tupi | Álcool Jimo | Querosene Jimo | Jimo |
        Removedor Jimo | Tira limo Jimo | Cupinicida Jimo | Desengordurante Uau | Uau | Limpa pedra | Saco de lixo Dover Roll | Dover Roll |
        Saco de lixo Embalixo | Embalixo | Saco de lixo Lixo Mix | Saco de lixo Bettanin | Bettanin | Rodo Bettanin | Vassoura Bettanin |
        Esfregão Bettanin | Mop Bettanin | Esponja Scotch-Brite | Scotch-Brite | Esponja dupla face Scotch-Brite | Esponja Limppano | Limppano |
        Pano Limppano | Flanela Limppano | Luva Mucambo | Mucambo | Luva Sanro | Sanro | Papel alumínio Wyda | Wyda | Filme plástico Wyda |
        Papel alumínio Royal Pack | Filme PVC Royal Pack | Papel alumínio Alcoa | Papel manteiga Wyda | Saco zip Wyda | Copo descartável Copobras |
        Copobras | Copo Copaza | Prato descartável Copobras | Guardanapo Snob | Guardanapo Santepel | Papel toalha Snob | Snob | Papel toalha Scott |
        Papel toalha Kitchen | Papel toalha Sublime | Papel toalha Personal | Palito Gina | Gina | Fósforo Paraná | Fósforo Pinheiro | Fósforo Fiat Lux |
        Fiat Lux | Vela Fiat Lux | Isqueiro Bic | Carvão Carvãozinho | Acendedor Zippo | Pilha Duracell | Duracell | Pilha Rayovac | Rayovac |
        Pilha Panasonic | Pilha Energizer | Energizer | Pilha Elgin | Lâmpada Philips | Lâmpada Osram | Lâmpada Elgin | Lâmpada Avant | Lâmpada Taschibra |
        Fita adesiva Durex 3M | Durex 3M | Super Bonder | Cola Super Bonder | Cola Tenaz | Tenaz | Cola Pritt | Fita isolante 3M""",
}

HIGIENE = {
    "Unilever (higiene)": """Dove | Sabonete Dove | Sabonete líquido Dove | Desodorante Dove | Desodorante Dove Men+Care | Dove Men+Care | Shampoo Dove |
        Condicionador Dove | Creme para pentear Dove | Hidratante Dove | Creme Dove | Rexona | Desodorante Rexona | Rexona Men | Rexona Clinical |
        Rexona aerossol | Rexona roll-on | Sabonete Rexona | Axe | Desodorante Axe | Axe Black | Axe Dark Temptation | Body spray Axe | Lux | Sabonete Lux |
        Sabonete líquido Lux | Lifebuoy | Sabonete Lifebuoy | Seda | Shampoo Seda | Condicionador Seda | Creme para pentear Seda | Seda Cocriações |
        Clear | Shampoo Clear | Clear Men | Shampoo Clear Men | TRESemmé | Shampoo TRESemmé | Condicionador TRESemmé | Creme para pentear TRESemmé |
        Close Up | Creme dental Close Up | Close Up Triple | Vasenol | Hidratante Vasenol | Pond's | Creme Pond's | Hidratante Pond's | Suave |
        Shampoo Suave | Simple | Sabonete facial Simple | Nexxus | Creme Seda | Rexona Women | Dove Baby | Sabonete Dove Baby""",
    "P&G (higiene)": """Pantene | Shampoo Pantene | Condicionador Pantene | Creme para pentear Pantene | Pantene Bambu | Pantene Hidratação |
        Pantene Cachos | Pantene Restauração | Head & Shoulders | Shampoo Head & Shoulders | Head & Shoulders Men | Herbal Essences |
        Shampoo Herbal Essences | Condicionador Herbal Essences | Gillette | Aparelho de barbear Gillette | Gillette Mach3 | Mach3 | Gillette Fusion |
        Gillette Fusion5 | Gillette Prestobarba | Prestobarba | Prestobarba3 | Gillette Venus | Venus | Espuma de barbear Gillette | Gel de barbear Gillette |
        Lâmina Gillette | Carga Gillette Mach3 | Oral-B | Creme dental Oral-B | Escova de dente Oral-B | Fio dental Oral-B | Oral-B Pro-Saúde |
        Escova elétrica Oral-B | Enxaguante Oral-B | Always | Absorvente Always | Always Noturno | Always Protetor Diário | Old Spice |
        Desodorante Old Spice | Secret | Desodorante Secret | Vick | Vick VapoRub | Vick Pastilha | Vick 44""",
    "Colgate-Palmolive (higiene)": """Colgate | Creme dental Colgate | Colgate Total 12 | Colgate Máxima Proteção Anticáries | Colgate Luminous White |
        Colgate Tripla Ação | Colgate Sensitive | Colgate Natural Extracts | Colgate Herbal | Colgate Kids | Colgate Neutraçúcar | Escova de dente Colgate |
        Escova Colgate Slim Soft | Colgate Slim Soft | Fio dental Colgate | Enxaguante Colgate | Enxaguante bucal Colgate Plax | Plax | Colgate Plax |
        Sorriso | Creme dental Sorriso | Sorriso Dentes Brancos | Sorriso Xtreme | Escova de dente Sorriso | Elmex | Creme dental Elmex | Palmolive |
        Sabonete Palmolive | Sabonete líquido Palmolive | Shampoo Palmolive | Palmolive Naturals | Protex | Sabonete Protex | Sabonete líquido Protex |
        Protex Aveia | Protex Erva-doce | Speed Stick | Desodorante Speed Stick | Lady Speed Stick | Tom's of Maine""",
    "L'Oréal e Garnier": """Elseve | Shampoo Elseve | Condicionador Elseve | Creme para pentear Elseve | Óleo Elseve | Elseve Óleo Extraordinário |
        Elseve Hydra Hialurônico | Elseve Cicatri Renov | Elseve Liso dos Sonhos | Elseve Reparação Total 5 | Máscara Elseve | Imédia | Tinta Imédia |
        Imédia Excellence | Excellence | Tinta L'Oréal | Casting Creme Gloss | L'Oréal | Protetor solar L'Oréal | Revitalift | L'Oréal Revitalift |
        Água micelar L'Oréal | Garnier | Fructis | Shampoo Fructis | Condicionador Fructis | Creme para pentear Fructis | Nutrisse | Tinta Nutrisse |
        Garnier Nutrisse | Água micelar Garnier | Garnier SkinActive | Uniq One | Kérastase | Maybelline | Rímel Maybelline | Base Maybelline |
        Batom Maybelline | Maybelline Colossal | Maybelline Fit Me | Fit Me | La Roche-Posay | Protetor solar La Roche-Posay | Anthelios |
        Effaclar | Cicaplast | Vichy | CeraVe | Hidratante CeraVe | Loção CeraVe""",
    "Natura, Boticário e outros": """Natura | Hidratante Natura | Natura Ekos | Ekos | Natura Tododia | Tododia | Natura Lumina | Lumina | Natura Chronos |
        Natura Kaiak | Kaiak | Natura Homem | Natura Essencial | Sabonete Natura | Boticário | O Boticário | Nativa SPA | Malbec | Lily | Egeo |
        Quasar | Floratta | Cuide-se Bem | Make B | Eudora | Siàge | Quem disse, Berenice? | Avon | Avon Care | Renew | Jequiti | Granado |
        Sabonete Granado | Talco Granado | Granado Bebê | Phebo | Sabonete Phebo | Nivea | Creme Nivea | Hidratante Nivea | Desodorante Nivea |
        Nivea Men | Protetor solar Nivea | Nivea Sun | Sabonete Nivea | Protetor labial Nivea | Nivea Milk | Monange | Hidratante Monange |
        Desodorante Monange | Monange Hidratação | Neutrogena | Hidratante Neutrogena | Protetor solar Neutrogena | Sundown | Protetor solar Sundown |
        Cenoura & Bronze | Protetor solar Cenoura & Bronze | Episol | Protetor solar Episol | Banana Boat | Cetaphil | Hidratante Cetaphil |
        Sabonete Cetaphil | Darrow | Bioderma | Água micelar Bioderma | Avène | Eucerin | Hidratante Eucerin | Johnson's | Johnson's Baby |
        Shampoo Johnson's Baby | Sabonete Johnson's | Óleo Johnson's | Hidratante Johnson's | Cotonete Johnson's | Fio dental Johnson's |
        Listerine | Enxaguante bucal Listerine | Listerine Cool Mint | Listerine Zero | Sensodyne | Creme dental Sensodyne | Sensodyne Repair |
        Escova Sensodyne | Parodontax | Corega | Curaprox | Escova Curaprox | Kolynos | Gessy | Sabonete Francis | Francis | Sabonete Albany |
        Albany | Sabonete Flor de Ypê | Sabonete Davene | Davene | Sabonete Lux Botanicals | Senador | Sabonete Senador | Bozzano | Desodorante Bozzano |
        Espuma de barbear Bozzano | Gel Bozzano | Avanço | Desodorante Avanço | Herbíssimo | Desodorante Herbíssimo | Above | Desodorante Above |
        Adidas | Desodorante Adidas | Desodorante Gillette | Desodorante Giovanna Baby | Giovanna Baby | Desodorante Leite de Rosas | Leite de Rosas |
        Desodorante Contouré | Contouré | Desodorante Soffie | Hidratante Paixão | Paixão | Hidratante Hidramais | Hidramais | Hidratante Skala | Skala |
        Creme Skala | Salon Line | Creme Salon Line | Shampoo Salon Line | Gelatina Salon Line | Novex | Creme Novex | Shampoo Novex | Lola Cosmetics |
        Lola | Máscara Lola | Kerasys | Shampoo Kerasys | Wella | Shampoo Wella | Koleston | Tinta Koleston | Igora | Tinta Igora | Keraton |
        Tinta Keraton | Beautycolor | Tinta Beautycolor | Haskell | Shampoo Haskell | Darling | Shampoo Darling | Palmolive Ultra Suave | Neutrox |
        Creme Neutrox | Bio Extratus | Shampoo Bio Extratus | Yamasterol | Pantene Pro-V | Dove Men | Esmalte Risqué | Risqué | Esmalte Colorama |
        Colorama | Esmalte Impala | Impala | Esmalte Dailus | Dailus | Esmalte Vult | Vult | Base Vult | Ruby Rose | Base Ruby Rose | Max Love |
        Acetona Farmax | Farmax | Removedor de esmalte Farmax | Algodão Apolo | Apolo | Algodão Cremer | Cremer | Hastes Cremer | Lenço Kleenex |
        Kleenex | Neve | Papel higiênico Neve | Neve Naturali | Neve Supreme | Papel higiênico Personal | Personal | Papel higiênico Mili | Mili |
        Papel higiênico Sublime | Sublime | Papel higiênico Leve | Papel higiênico Scott | Scott | Papel higiênico Familia | Papel higiênico Max Pure |
        Papel higiênico Carinho | Papel higiênico Fofinho | Papel higiênico Floral | Papel higiênico Paloma | Papel higiênico Elite | Elite |
        Papel higiênico Primavera | Papel higiênico Folhas de Ouro | Papel higiênico Dualette | Lenço umedecido Personal | Intimus | Absorvente Intimus |
        Intimus Gel | Intimus Days | Carefree | Absorvente Carefree | Sym | Absorvente Sym | o.b. | Absorvente o.b. | Absorvente Ela | Absorvente Kotex |
        Kotex | Absorvente Mili | Absorvente Herbíssimo | Coletor Inciclo | Inciclo | Calcinha absorvente Pantys | Pantys | Tena | Fralda geriátrica Tena |
        Plenitud | Fralda geriátrica Plenitud | Bigfral | Fralda geriátrica Bigfral | Fralda geriátrica Confort | Jontex | Preservativo Jontex |
        Preservativo Prudence | Prudence | Preservativo Olla | Olla | Preservativo Blowtex | Blowtex | Gel lubrificante KY | Lubrificante KY | Carmed |
        Protetor labial Carmed | Bepantol | Bepantol Derma | Hipoglós | Dermacyd | Sabonete íntimo Dermacyd | Lucretin | Nivea Men Sensitive""",
}

BEBE_PET = {
    "Bebê": """Pampers | Fralda Pampers | Pampers Confort Sec | Pampers Premium Care | Pampers Pants | Pampers Ajuste Total | Lenço umedecido Pampers |
        Huggies | Fralda Huggies | Huggies Tripla Proteção | Huggies Supreme Care | Huggies Natural Care | Huggies Roupinha | Lenço umedecido Huggies |
        MamyPoko | Fralda MamyPoko | MamyPoko Pants | Turma da Mônica | Fralda Turma da Mônica | Babysec | Fralda Babysec | Personal Baby |
        Fralda Personal Baby | Pom Pom | Fralda Pom Pom | Fralda Cremer | Bigfral Baby | Fralda Mônica Plus | Fralda Capricho | Fralda Sapeka |
        Fralda Bigfral Baby | Lenço Johnson's | Hipoglós | Pomada Hipoglós | Bepantol Baby | Pomada Bepantol Baby | Desitin | Pomada Desitin |
        Dermodex | Pomada Dermodex | Johnson's Baby | Shampoo Johnson's Baby | Sabonete Johnson's Baby | Colônia Johnson's Baby | Óleo Johnson's Baby |
        Condicionador Johnson's Baby | Granado Bebê | Mustela | Huggies Shampoo | Nan | Leite Nan | Nan Comfor | Nan Supreme | Nan Sem Lactose |
        Aptamil | Leite Aptamil | Aptamil Premium | Milnutri | Leite Milnutri | Nestogeno | Leite Nestogeno | Enfamil | Leite Enfamil | Similac |
        Leite Similac | Ninho Fases | Neocate | Pregomin | Mucilon | Papinha Nestlé | Nestlé Naturnes | Papinha Heinz Baby | Mamadeira Avent |
        Avent | Philips Avent | Mamadeira Lillo | Lillo | Chupeta Lillo | Chupeta Nuk | Nuk | Mamadeira Nuk | Chupeta MAM | Mamadeira MAM |
        Chupeta Avent | Mamadeira Kuka | Kuka | Chupeta Kuka | Mamadeira Pigeon | Pigeon | Chicco | Mamadeira Chicco | Chupeta Chicco | Fisher-Price""",
    "Pet": """Pedigree | Ração Pedigree | Ração Pedigree filhote | Ração Pedigree adulto | Sachê Pedigree | Petisco Pedigree | Pedigree Dentastix |
        Dentastix | Whiskas | Ração Whiskas | Sachê Whiskas | Whiskas Temptations | Golden | Ração Golden | Ração Golden Fórmula | Ração Golden Gatos |
        Golden Mega | Golden Seleção Natural | Premier | Ração Premier | Premier Pet | Premier Fórmula | Premier Nattu | Royal Canin | Ração Royal Canin |
        Royal Canin Mini | Royal Canin Indoor | Dog Chow | Ração Dog Chow | Cat Chow | Ração Cat Chow | Friskies | Ração Friskies | Sachê Friskies |
        Purina | Pro Plan | Ração Pro Plan | Alpo | Ração Alpo | Felix | Sachê Felix | Special Dog | Ração Special Dog | Special Cat | Ração Special Cat |
        Magnus | Ração Magnus | Quatree | Ração Quatree | Ração Max | Total Max | Guabi Natural | Ração Guabi Natural | Guabi | Ração Gran Plus |
        GranPlus | N&D | Ração N&D | Farmina | Hill's | Ração Hill's | Ração Premiatta | Premiatta | Biofresh | Ração Biofresh | Formula Natural |
        Ração Formula Natural | Fit Formula | Ração Fit Formula | Origens | Ração Origens | Baw Waw | Ração Baw Waw | Petisco Baw Waw | Kelcat |
        Ração Kelcat | Keldog | Ração Keldog | Petisco Keldog | Bifinho Keldog | Dreamies | Petisco Dreamies | Max Cat | Ração Max Cat | Equilíbrio |
        Ração Equilíbrio | Total Equilíbrio | Optimum | Ração Optimum | Three Cats | Ração Three Cats | Three Dogs | Ração Three Dogs | Faro |
        Ração Faro | Champ | Ração Champ | Foster | Ração Foster | Granplus Menu | Pipicat | Areia Pipicat | Areia Chalesco | Chalesco |
        Tapete Chalesco | Areia Viva Verde | Viva Verde | Areia Kelco | Kelco | Areia Pet Clean | Pet Clean | Areia Snow | Granulado Pipicat |
        Tapete higiênico Super Secão | Super Secão | Tapete Expet | Expet | Bravecto | Antipulgas Bravecto | NexGard | Antipulgas NexGard |
        Simparic | Antipulgas Simparic | Frontline | Antipulgas Frontline | Seresto | Coleira Seresto | Advocate | Revolution | Credeli |
        Drontal | Vermífugo Drontal | Vermivet | Vermífugo Vermivet | Endogard | Milbemax | Sanol | Shampoo Sanol | Sanol Dog | Petisco Petz |
        Ração Zee.Dog | Zee.Dog | Alpiste Zootekna | Ração Alcon | Alcon | Ração Tetra | Ração Nutrópica | Nutrópica | Ração Megazoo | Megazoo""",
}

FARMACIA = {
    "Analgésicos, gripe e estômago": """Dorflex | Dorflex comprimido | Dorflex gotas | Neosaldina | Tylenol | Tylenol 750 | Tylenol gotas | Novalgina |
        Novalgina gotas | Anador | Lisador | Doril | Torsilax | Buscopan | Buscopan Composto | Buscofem | Advil | Alivium | Aspirina | AAS | AAS Infantil |
        Cataflam | Cataflam gel | Voltaren | Voltaren gel | Gelol | Salonpas | Calminex | Mioflex | Miosan | Benegrip | Cimegripe | Resfenol |
        Coristina D | Apracur | Multigrip | Gripen | Naldecon | Vick VapoRub | Benalet | Strepsils | Neosoro | Rinosoro | Sorine | Maresis |
        Afrin | Allegra | Claritin | Polaramine | Histamin | Loratamed | Engov | Eno | Sal de fruta Eno | Estomazil | Sonrisal | Epocler | Luftal |
        Gaviscon | Mylanta | Pepsamar | Omeprazol EMS | Plasil | Dramin | Imosec | Floratil | Tamarine | Lacto-Purga | Dulcolax | Leite de Magnésia Phillips |
        Leite de Magnésia | Simeticona Luftal | Muvinlax | Buscopan gotas | Atroveran | Ponstan | Nimesulida EMS | Tandrilla | Flanax | Nisulid""",
    "Vitaminas e saúde": """Centrum | Centrum Silver | Redoxon | Cebion | Addera D3 | Depura | Lavitan | Lavitan Mulher | Lavitan A-Z | Pharmaton | Targifor |
        Biotônico Fontoura | Emulsão Scott | Ômega 3 Vitafor | Vitafor | Colágeno Sanavita | Sanavita | Whey Growth | Growth | Whey Max Titanium |
        Max Titanium | Creatina Max Titanium | Creatina Growth | Integralmédica | Whey Integralmédica | Essential Nutrition | Puran T4 | Euthyrox |
        Synthroid | Glifage | Glifage XR | Xarelto | Aradois | Selozok | Atenol | Losartana EMS | Atorvastatina EMS | Rosuvastatina EMS | Rivotril |
        Frontal | Ozempic | Puran | Clearblue | Teste de gravidez Clearblue | Teste de gravidez Confirme | Confirme | Omron | Medidor de pressão Omron |
        G-Tech | Termômetro G-Tech | Accu-Chek | Medidor de glicose Accu-Chek | Tira Accu-Chek | Lanceta Accu-Chek | FreeStyle Libre | OneTouch |
        Seringa BD | Agulha BD | BD | Band-Aid | Curativo Band-Aid | Nexcare | Curativo Nexcare | Micropore Nexcare | Esparadrapo Cremer |
        Gaze Cremer | Merthiolate | Povidine | Nebacetin | Nebacetin pomada | Fibrinase | Kollagenase | Cicatricure | Hidrogel | Fisiofor |
        Minancora | Pomada Minancora | Hipoglós | Bepantol | Picrato de butesina | Água boricada | Óleo de rícino | Polvilho antisséptico |
        Talco Barla | Barla | Soro fisiológico Arboreto | Arboreto | Lacrima Plus | Systane | Optive | Lágrima Moura Brasil | Moura Brasil |
        Colírio Moura Brasil | Maxidex | Dexaneurin | Citoneurin | Dipirona EMS | Dipirona Medley | Paracetamol EMS | Ibuprofeno EMS |
        Medley | EMS | Neo Química | Eurofarma | Prati-Donaduzzi | Cimed | Germed | Sanofi | Bayer""",
}

TODOS = [ALIMENTOS, CARNES_PAES_CONGELADOS, BEBIDAS, CASA, HIGIENE, BEBE_PET, FARMACIA]
