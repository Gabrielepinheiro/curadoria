// =============================================================
//  seed.js  —  Dados de exemplo para o modo 'seed'.
//  Espelham a estrutura real do Wix CMS: Lojas e Produtos
//  separados; o Produto aponta para a Loja (storeId) e herda
//  dela região e países de entrega.
//  Substituídos pelo catálogo real assim que ligarmos no Wix.
// =============================================================

export const STORES_SEED = [
  { id: 'loja-westwing',  name: 'Westwing',   site: 'https://www.westwing.de',     region: 'europa', ships: ['Alemanha', 'Áustria'] },
  { id: 'loja-hm',        name: 'H&M Home',   site: 'https://www2.hm.com',         region: 'europa', ships: ['Alemanha', 'França', 'Itália', 'Portugal', 'Espanha'] },
  { id: 'loja-benuta',    name: 'Benuta',     site: 'https://www.benuta.de',       region: 'europa', ships: ['Alemanha', 'França', 'Itália'] },
  { id: 'loja-urbanara',  name: 'Urbanara',   site: 'https://www.urbanara.de',     region: 'europa', ships: ['Alemanha', 'Reino Unido'] },
  { id: 'loja-kave',      name: 'Kave Home',  site: 'https://kavehome.com',        region: 'europa', ships: ['Portugal', 'Espanha'] },
  { id: 'loja-zarahome',  name: 'Zara Home',  site: 'https://www.zarahome.com',    region: 'europa', ships: ['Portugal', 'Espanha', 'França', 'Itália', 'Alemanha'] },
  { id: 'loja-laredoute', name: 'La Redoute', site: 'https://www.laredoute.fr',    region: 'europa', ships: ['França', 'Bélgica', 'Portugal'] },
  { id: 'loja-selency',   name: 'Selency',    site: 'https://www.selency.com',     region: 'europa', ships: ['França', 'Itália', 'Alemanha'] },
  { id: 'loja-tokstok',   name: 'Tok&Stok',   site: 'https://www.tokstok.com.br',  region: 'brasil', ships: ['Brasil'] },
  { id: 'loja-westwingbr',name: 'Westwing BR',site: 'https://www.westwing.com.br', region: 'brasil', ships: ['Brasil'] },
];

// novidadeAte: data ISO; após essa data a peça sai da aba Novidades
// mas continua no catálogo (briefing §5.6).
const EM_30_DIAS = new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10);

export const PRODUCTS_SEED = [
  { id: 'p1',  nome: 'Mesa de jantar Linnea, carvalho',     referencia: 'Esstisch Linnea Eiche',   storeId: 'loja-westwing',  categoria: 'Mesa de jantar',  faixaPreco: 3, imagem: '', link: 'https://www.westwing.de',  novidade: true,  novidadeAte: EM_30_DIAS },
  { id: 'p2',  nome: 'Cadeira Bouclé Ada',                  referencia: 'Bouclé Chair Ada',        storeId: 'loja-hm',        categoria: 'Cadeira',         faixaPreco: 2, imagem: '', link: 'https://www2.hm.com',     novidade: false, novidadeAte: '' },
  { id: 'p3',  nome: 'Tapete de juta natural 200×300',      referencia: 'Juteteppich Natur',       storeId: 'loja-benuta',    categoria: 'Tapete',          faixaPreco: 2, imagem: '', link: 'https://www.benuta.de',   novidade: false, novidadeAte: '' },
  { id: 'p4',  nome: 'Cortina de linho cru, par',           referencia: 'Leinenvorhang Natur',     storeId: 'loja-urbanara',  categoria: 'Cortina',         faixaPreco: 3, imagem: '', link: 'https://www.urbanara.de', novidade: false, novidadeAte: '' },
  { id: 'p5',  nome: 'Mesa de centro Travertino Roma',      referencia: 'Mesa Travertino Roma',    storeId: 'loja-kave',      categoria: 'Mesa de centro',  faixaPreco: 4, imagem: '', link: 'https://kavehome.com',    novidade: true,  novidadeAte: EM_30_DIAS },
  { id: 'p6',  nome: 'Vaso artesanal em terracota',         referencia: 'Vaso Terracota',         storeId: 'loja-zarahome',  categoria: 'Decoração',       faixaPreco: 1, imagem: '', link: 'https://www.zarahome.com',novidade: false, novidadeAte: '' },
  { id: 'p7',  nome: 'Puff Capitonê Margaux',               referencia: 'Pouf Margaux',            storeId: 'loja-laredoute', categoria: 'Puff',            faixaPreco: 2, imagem: '', link: 'https://www.laredoute.fr',novidade: false, novidadeAte: '' },
  { id: 'p8',  nome: 'Cadeira Thonet n.º 14, vintage',      referencia: 'Chaise Thonet n°14',      storeId: 'loja-selency',   categoria: 'Cadeira',         faixaPreco: 4, imagem: '', link: 'https://www.selency.com', novidade: false, novidadeAte: '' },
  { id: 'p9',  nome: 'Poltrona Costela, couro caramelo',    referencia: 'Poltrona Costela',        storeId: 'loja-tokstok',   categoria: 'Poltrona',        faixaPreco: 3, imagem: '', link: 'https://www.tokstok.com.br',novidade: false, novidadeAte: '' },
  { id: 'p10', nome: 'Manta tramada em algodão rústico',    referencia: 'Manta Algodão',          storeId: 'loja-westwingbr',categoria: 'Decoração',       faixaPreco: 1, imagem: '', link: 'https://www.westwing.com.br',novidade: false, novidadeAte: '' },
  { id: 'p11', nome: 'Sofá Hampton 3 lugares, linho',       referencia: 'Sofa Hampton Leinen',     storeId: 'loja-westwing',  categoria: 'Sofá',                  faixaPreco: 5, imagem: '', link: 'https://www.westwing.de',  novidade: true,  novidadeAte: EM_30_DIAS },
  { id: 'p12', nome: 'Banqueta de madeira Oslo',            referencia: 'Hocker Oslo',             storeId: 'loja-hm',        categoria: 'Banco & Banqueta',      faixaPreco: 1, imagem: '', link: 'https://www2.hm.com',     novidade: false, novidadeAte: '' },
  { id: 'p13', nome: 'Mesa lateral redonda Nara',           referencia: 'Mesa auxiliar Nara',      storeId: 'loja-kave',      categoria: 'Mesa lateral',          faixaPreco: 2, imagem: '', link: 'https://kavehome.com',    novidade: false, novidadeAte: '' },
  { id: 'p14', nome: 'Mesa de cabeceira Linnea',            referencia: 'Nachttisch Linnea',       storeId: 'loja-westwing',  categoria: 'Mesa de cabeceira',     faixaPreco: 2, imagem: '', link: 'https://www.westwing.de',  novidade: false, novidadeAte: '' },
  { id: 'p15', nome: 'Aparador Surry em carvalho',          referencia: 'Sideboard Surry',         storeId: 'loja-kave',      categoria: 'Aparador & Buffet',     faixaPreco: 4, imagem: '', link: 'https://kavehome.com',    novidade: false, novidadeAte: '' },
  { id: 'p16', nome: 'Estante modular Berg',                referencia: 'Regal Berg',              storeId: 'loja-urbanara',  categoria: 'Estante',               faixaPreco: 3, imagem: '', link: 'https://www.urbanara.de', novidade: false, novidadeAte: '' },
  { id: 'p17', nome: 'Cama de casal estofada Mara',         referencia: 'Polsterbett Mara',        storeId: 'loja-westwing',  categoria: 'Cama',                  faixaPreco: 5, imagem: '', link: 'https://www.westwing.de',  novidade: false, novidadeAte: '' },
  { id: 'p18', nome: 'Cômoda 3 gavetas Brienne',            referencia: 'Commode Brienne',         storeId: 'loja-laredoute', categoria: 'Cômoda',                faixaPreco: 3, imagem: '', link: 'https://www.laredoute.fr',novidade: false, novidadeAte: '' },
  { id: 'p19', nome: 'Escrivaninha minimalista Aria',       referencia: 'Schreibtisch Aria',       storeId: 'loja-hm',        categoria: 'Escrivaninha',          faixaPreco: 2, imagem: '', link: 'https://www2.hm.com',     novidade: false, novidadeAte: '' },
  { id: 'p20', nome: 'Luminária de chão arco Lua',          referencia: 'Stehlampe Lua',           storeId: 'loja-zarahome',  categoria: 'Iluminação',            faixaPreco: 3, imagem: '', link: 'https://www.zarahome.com',novidade: true,  novidadeAte: EM_30_DIAS },
  { id: 'p21', nome: 'Conjunto de quadros botânicos',       referencia: 'Set láminas botánicas',   storeId: 'loja-zarahome',  categoria: 'Quadros & Arte',        faixaPreco: 1, imagem: '', link: 'https://www.zarahome.com',novidade: false, novidadeAte: '' },
  { id: 'p22', nome: 'Espelho redondo aro bronze',          referencia: 'Espejo redondo',          storeId: 'loja-zarahome',  categoria: 'Espelho',               faixaPreco: 2, imagem: '', link: 'https://www.zarahome.com',novidade: false, novidadeAte: '' },
  { id: 'p23', nome: 'Jogo de cama percal 200 fios',        referencia: 'Bettwäsche Perkal',       storeId: 'loja-urbanara',  categoria: 'Roupa de cama & Têxtil',faixaPreco: 2, imagem: '', link: 'https://www.urbanara.de', novidade: false, novidadeAte: '' },
  { id: 'p24', nome: 'Espreguiçadeira de jardim Riviera',   referencia: 'Bain de soleil Riviera',  storeId: 'loja-laredoute', categoria: 'Área externa',          faixaPreco: 3, imagem: '', link: 'https://www.laredoute.fr',novidade: false, novidadeAte: '' },
  { id: 'p25', nome: 'Poltrona de leitura Lounge',          referencia: 'Sessel Lounge',           storeId: 'loja-westwing',  categoria: 'Poltrona',              faixaPreco: 4, imagem: '', link: 'https://www.westwing.de',  novidade: false, novidadeAte: '' },
  { id: 'p26', nome: 'Cadeira de escritório ergonômica',    referencia: 'Bürostuhl Stockholm',     storeId: 'loja-westwing',  categoria: 'Cadeira de escritório', faixaPreco: 3, imagem: '', link: 'https://www.westwing.de',  novidade: false, novidadeAte: '' },
  { id: 'p27', nome: 'Papel de parede floral Sauge',        referencia: 'Papier peint floral',     storeId: 'loja-laredoute', categoria: 'Papel de parede',       faixaPreco: 2, imagem: '', link: 'https://www.laredoute.fr',novidade: true,  novidadeAte: EM_30_DIAS },
];
