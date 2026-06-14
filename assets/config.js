// =============================================================
//  config.js  —  Tudo que muda por região/categoria fica AQUI.
//  Briefing §6 e §10: regiões, países, moedas e faixas de preço
//  devem ser configuráveis, não chumbados no código. Para
//  adicionar os EUA ($) no futuro, basta editar este arquivo.
// =============================================================

export const REGIONS = [
  { id: 'europa', label: 'Europa', currency: '€'  },
  { id: 'brasil', label: 'Brasil', currency: 'R$' },
  // Futuro — descomentar quando entrar:
  // { id: 'eua', label: 'EUA', currency: '$' },
];

// Países de entrega disponíveis por região (briefing §6).
export const COUNTRIES = {
  europa: [
    'Alemanha', 'Áustria', 'Suíça', 'Portugal', 'Espanha', 'França',
    'Itália', 'Holanda', 'Bélgica', 'Luxemburgo', 'Reino Unido',
    'Irlanda', 'Dinamarca', 'Suécia', 'Polônia',
  ],
  brasil: ['Brasil'],
};

// Faixas de preço: a pessoa escolhe a faixa e o sistema mostra os
// símbolos de moeda (1 a 5). Valores ajustáveis (briefing §5.4).
export const PRICE_BANDS = {
  europa: [
    { level: 1, label: 'até €150' },
    { level: 2, label: '€150 – €400' },
    { level: 3, label: '€400 – €700' },
    { level: 4, label: '€700 – €1.000' },
    { level: 5, label: 'acima de €1.000' },
  ],
  brasil: [
    { level: 1, label: 'até R$800' },
    { level: 2, label: 'R$800 – R$2.000' },
    { level: 3, label: 'R$2.000 – R$4.000' },
    { level: 4, label: 'R$4.000 – R$6.000' },
    { level: 5, label: 'acima de R$6.000' },
  ],
};

// Lista de categorias (24). Móveis em ordem alfabética, depois
// iluminação/têxteis/decoração em ordem alfabética (briefing §6 + ajustes).
export const CATEGORIES = [
  // Móveis
  'Aparador & Buffet', 'Banco & Banqueta', 'Cadeira', 'Cadeira de escritório',
  'Cama', 'Cômoda', 'Escrivaninha', 'Estante', 'Mesa de cabeceira',
  'Mesa de centro', 'Mesa de jantar', 'Mesa lateral', 'Poltrona', 'Puff', 'Sofá',
  // Iluminação, têxteis e decoração
  'Área externa', 'Cortina', 'Decoração', 'Espelho', 'Iluminação',
  'Papel de parede', 'Quadros & Arte', 'Roupa de cama & Têxtil', 'Tapete',
];

// Ícones de categoria — traço bronze sobre fundo linho (do protótipo).
// As categorias ainda sem SVG próprio usam DEFAULT até chegar o
// pacote oficial de ícones/capas mencionado no briefing §8.
export const CATEGORY_ICONS = {
  'Mesa de jantar': '<svg viewBox="0 0 100 100"><path d="M10 38 H90 M16 38 V80 M84 38 V80 M16 58 H84"/></svg>',
  'Cadeira':        '<svg viewBox="0 0 100 100"><path d="M30 15 V55 H70 M30 55 V85 M70 55 V85 M30 38 H70 V55"/></svg>',
  'Poltrona':       '<svg viewBox="0 0 100 100"><path d="M24 46 V78 H76 V46 M24 46 Q24 34 36 34 H64 Q76 34 76 46 M18 50 V70 M82 50 V70"/></svg>',
  'Mesa de centro': '<svg viewBox="0 0 100 100"><ellipse cx="50" cy="42" rx="38" ry="12"/><path d="M22 48 V72 M78 48 V72 M50 54 V78"/></svg>',
  'Puff':           '<svg viewBox="0 0 100 100"><path d="M20 50 Q20 30 50 30 Q80 30 80 50 V70 Q80 78 50 78 Q20 78 20 70 Z M20 58 Q50 68 80 58"/></svg>',
  'Decoração':      '<svg viewBox="0 0 100 100"><path d="M40 20 Q36 40 30 50 Q24 62 32 74 Q40 84 50 84 Q60 84 68 74 Q76 62 70 50 Q64 40 60 20 Z M40 20 H60"/></svg>',
  'Cortina':        '<svg viewBox="0 0 100 100"><path d="M15 18 H85 M22 18 Q26 50 20 82 M38 18 Q42 50 36 82 M54 18 Q58 50 52 82 M70 18 Q74 50 70 82"/></svg>',
  'Tapete':         '<svg viewBox="0 0 100 100"><rect x="18" y="26" width="64" height="48" rx="3"/><rect x="28" y="36" width="44" height="28" rx="2"/><path d="M18 30 H12 M18 44 H12 M18 58 H12 M18 70 H12 M82 30 H88 M82 44 H88 M82 58 H88 M82 70 H88"/></svg>',
  'Iluminação':     '<svg viewBox="0 0 100 100"><path d="M35 20 H65 L74 44 H26 Z M50 44 V78 M38 80 H62"/></svg>',
  'Espelho':        '<svg viewBox="0 0 100 100"><rect x="30" y="14" width="40" height="64" rx="20"/><path d="M40 30 Q38 44 46 54"/></svg>',
  'Estante':        '<svg viewBox="0 0 100 100"><rect x="22" y="16" width="56" height="68"/><path d="M22 38 H78 M22 60 H78"/></svg>',
  'Cama':           '<svg viewBox="0 0 100 100"><path d="M14 50 H86 V74 M14 40 V74 M86 50 V74 M14 50 Q14 40 26 40 H58 Q70 40 70 50"/></svg>',
  DEFAULT:          '<svg viewBox="0 0 100 100"><rect x="24" y="24" width="52" height="52" rx="6"/><path d="M24 44 H76 M44 24 V76"/></svg>',
};

export function iconFor(category) {
  return CATEGORY_ICONS[category] || CATEGORY_ICONS.DEFAULT;
}

// Capas oficiais aprovadas (PNG 1000×850, ícone bronze sobre linho).
// Usadas como imagem do card quando o produto não tem foto própria.
const COVERS = {
  'Aparador & Buffet': 'capa-aparador-buffet.png',
  'Banco & Banqueta': 'capa-banco-banqueta.png',
  'Cadeira': 'capa-cadeira.png',
  'Cadeira de escritório': 'capa-cadeira-de-escritorio.png',
  'Cama': 'capa-cama.png',
  'Cômoda': 'capa-comoda.png',
  'Escrivaninha': 'capa-escrivaninha.png',
  'Estante': 'capa-estante.png',
  'Mesa de cabeceira': 'capa-mesa-de-cabeceira.png',
  'Mesa de centro': 'capa-mesa-de-centro.png',
  'Mesa de jantar': 'capa-mesa-de-jantar.png',
  'Mesa lateral': 'capa-mesa-lateral.png',
  'Poltrona': 'capa-poltrona.png',
  'Puff': 'capa-puff.png',
  'Sofá': 'capa-sofa.png',
  'Área externa': 'capa-area-externa.png',
  'Cortina': 'capa-cortina.png',
  'Decoração': 'capa-decoracao.png',
  'Espelho': 'capa-espelho.png',
  'Iluminação': 'capa-luminaria.png',
  'Papel de parede': 'capa-papel-de-parede.png',
  'Quadros & Arte': 'capa-quadros-arte.png',
  'Roupa de cama & Têxtil': 'capa-roupa-de-cama-textil.png',
  'Tapete': 'capa-tapete.png',
};

export function coverFor(category) {
  const file = COVERS[category] || COVERS['Decoração'];
  return `./assets/capas/${file}`;
}

export function regionById(id) {
  return REGIONS.find((r) => r.id === id) || REGIONS[0];
}
