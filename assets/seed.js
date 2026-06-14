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
];
