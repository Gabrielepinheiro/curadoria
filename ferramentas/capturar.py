#!/usr/bin/env python3
# =============================================================
#  capturar.py  —  Cola o link, sai o produto pronto.
#
#  Lê a página de cada produto e captura: nome, foto, preço,
#  moeda e loja. Sugere a categoria e calcula a faixa de preço
#  (mesmas faixas de assets/config.js). Gera:
#    • produtos.csv  → pronto para importar no Wix CMS (Produtos)
#    • previa.html   → para conferir tudo visualmente antes
#
#  Usa os dados que as lojas já publicam para o Google
#  (JSON-LD schema.org/Product e meta tags Open Graph). Quando
#  algo não vem, o item sai marcado "conferir".
#
#  USO:
#    python3 ferramentas/capturar.py links.txt            (um link por linha)
#    python3 ferramentas/capturar.py URL1 URL2 ...
#    python3 ferramentas/capturar.py links.txt --saida capturas/sofas
#  Só usa a biblioteca padrão do Python (nada para instalar).
# =============================================================

import argparse
import csv
import datetime as dt
import gzip
import html
import json
import os
import re
import sys
import unicodedata
import urllib.request
import zlib
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlparse

AQUI = os.path.dirname(os.path.abspath(__file__))

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')

# Faixas de preço — espelho de PRICE_BANDS em assets/config.js.
# Limite SUPERIOR de cada faixa 1..4 (acima do último = faixa 5).
FAIXAS = {
    'europa': [150, 400, 800, 1500],
    'brasil': [800, 2000, 4000, 6000],
}
SIMBOLO = {'europa': '€', 'brasil': 'R$'}

# Categoria sugerida por palavras no nome/link (pt, es, fr, de, it, en).
# A ordem importa: o primeiro que bater vence (mais específico antes).
CATEGORIAS = [
    # Iluminação por tipo — antes de tudo, para "luminária de mesa" não virar mesa
    ('Luminária de piso', ['luminaria de piso', 'luminaria de chao', 'candeeiro de pe', 'candeeiro de chao', 'abajur de chao',
                           'stehleuchte', 'stehlampe', 'lampadaire', 'lampara de pie', 'lampada da terra', 'floor lamp', 'standing lamp']),
    ('Luminária de parede', ['luminaria de parede', 'candeeiro de parede', 'arandela', 'aplique', 'applique', 'wandleuchte',
                             'wandlampe', 'wandfluter', 'wandspot', 'lampara de pared', 'wall lamp', 'wall light', 'sconce']),
    ('Luminária de mesa', ['luminaria de mesa', 'candeeiro de mesa', 'abajur', 'tischleuchte', 'tischlampe', 'schreibtischleuchte',
                           'lampe de table', 'lampe a poser', 'lampe de bureau', 'lampara de mesa', 'lampada da tavolo',
                           'table lamp', 'desk lamp']),
    ('Luminária de teto', ['luminaria de teto', 'candeeiro de teto', 'pendente', 'lustre', 'plafon', 'plafonnier', 'spot', 'spots',
                           'trilho', 'deckenleuchte', 'deckenlampe', 'deckenspot', 'deckenschiene', 'hangeleuchte', 'haengeleuchte',
                           'pendelleuchte', 'kronleuchter', 'suspension', 'lampara de techo', 'colgante', 'lampadario', 'sospensione',
                           'pendant', 'ceiling lamp', 'ceiling light', 'chandelier']),
    ('Cadeira de escritório', ['cadeira de escritorio', 'silla de oficina', 'chaise de bureau', 'burostuhl', 'buerostuhl', 'drehstuhl', 'sedia da ufficio', 'office chair', 'desk chair']),
    ('Mesa de cabeceira', ['mesa de cabeceira', 'criado-mudo', 'criado mudo', 'mesita de noche', 'table de chevet', 'nachttisch', 'comodino', 'bedside', 'nightstand']),
    ('Mesa de centro', ['mesa de centro', 'table basse', 'couchtisch', 'tavolino da salotto', 'coffee table']),
    ('Mesa de jantar', ['mesa de jantar', 'mesa de comedor', 'table a manger', 'esstisch', 'tavolo da pranzo', 'dining table']),
    ('Mesa lateral', ['mesa lateral', 'mesa de apoio', 'ablagetisch', 'mesa tabuleiro', 'mesa bandeja', 'tray table', 'mesa auxiliar', "table d'appoint", 'table d appoint', 'beistelltisch', 'tavolino', 'side table']),
    ('Sofá cama', ['sofa cama', 'sofa-cama', 'sofacama', 'schlafsofa', 'schlafcouch', 'bettsofa', 'canape convertible',
                   'canape lit', 'sofa convertible', 'sofa lit', 'divano letto', 'sofa bed', 'sleeper sofa']),
    ('Carrinho', ['carrinho', 'carrinho de apoio', 'carrinho bar', 'servierwagen', 'rollwagen', 'teewagen', 'barwagen',
                  'carrito', 'desserte', 'trolley', 'bar cart', 'serving cart', 'carrello']),
    ('Rack de TV', ['rack', 'rack de tv', 'movel de tv', 'movel tv', 'painel de tv', 'tv bank', 'tv board', 'tv mobel', 'tv moebel',
                    'tv schrank', 'fernsehschrank', 'lowboard', 'meuble tv', 'meuble television', 'mueble tv', 'mueble de tv',
                    'mobile tv', 'mobile porta tv', 'tv stand', 'tv unit', 'tv bench', 'tv cabinet', 'media console']),
    ('Cristaleira', ['cristaleira', 'vitrine', 'vitrina', 'vitrinenschrank', 'glasturen', 'glastueren', 'glasschiebeturen',
                     'glasschiebetueren', 'portas de vidro', 'porta de vidro', 'display cabinet', 'china cabinet', 'credenza vetrina']),
    ('Aparador & Buffet', ['aparador', 'schrankkombination', 'schiebeturenschrank', 'schiebetuerenschrank', 'aufbewahrung', 'konsolentisch', 'mesa consola', 'console table', 'schrank', 'armario baixo', 'mueble bajo', 'buffet', 'bufete', 'consola', 'console', 'sideboard', 'kommode sideboard', 'credenza', 'enfilade', 'anrichte']),
    ('Banco & Banqueta', ['banqueta', 'banquinho', 'banco', 'taburete', 'tabouret', 'banc ', 'hocker', 'sitzbank', 'sgabello', 'panca', 'stool', 'bench']),
    ('Poltrona', ['poltrona', 'butaca', 'sillon', 'fauteuil', 'sessel', 'armchair', 'lounge chair']),
    ('Sofá', ['sofa', 'canape', 'divano', 'couch', 'chaise longue', 'chaiselongue', 'modulsofa', 'ecksofa',
              'polstersofa', 'sitzer sofa', 'modulares sofa', 'sofa modular', 'sectional']),
    ('Cadeira', ['cadeira', 'silla', 'chaise', 'stuhl', 'sedia', 'chair']),
    ('Cama', ['cama', 'lit ', 'bett', 'bettgestell', 'polsterbett', 'bettrahmen', 'boxspringbett', 'letto', 'bed frame', 'cabeceira', 'headboard']),
    ('Cômoda', ['comoda', 'commode', 'kommode', 'cassettiera', 'chest of drawers', 'dresser']),
    ('Escrivaninha', ['escrivaninha', 'escritorio', 'secretaria', 'bureau', 'schreibtisch', 'scrivania', 'desk']),
    ('Estante', ['bucherregal', 'buecherregal', 'wandregal', 'estante', 'prateleira', 'estanteria', 'libreria', 'etagere', 'bibliotheque', 'regal', 'bookcase', 'shelf', 'shelving']),
    ('Puff', ['puff', 'pouf', 'otomana', 'ottoman']),
    ('Espelho', ['espelho', 'espejo', 'miroir', 'spiegel', 'specchio', 'mirror']),
    ('Iluminação', ['luminaria', 'candeeiro', 'lampada', 'lampara', 'lampe', 'leuchte', 'lamp']),
    ('Tapete', ['tapete', 'alfombra', 'tapis', 'teppich', 'tappeto', 'rug', 'carpet']),
    ('Cortina', ['cortina', 'cortinado', 'rideau', 'vorhang', 'gardine', 'tenda', 'curtain']),
    ('Papel de parede', ['papel de parede', 'papel pintado', 'papier peint', 'tapete wand', 'tapete vlies', 'carta da parati', 'wallpaper']),
    ('Quadros & Arte', ['quadro', 'gravura', 'poster', 'cuadro', 'lamina', 'tableau', 'affiche', 'bild', 'kunstdruck', 'stampa', 'print', 'wall art', 'artwork']),
    ('Roupa de cama & Têxtil', ['roupa de cama', 'lencol', 'edredom', 'edredao', 'fronha', 'manta', 'almofada', 'capa de almofada', 'toalha', 'colcha', 'ropa de cama', 'sabana', 'cojin', 'linge de lit', 'housse', 'drap', 'coussin', 'plaid', 'bettwasche', 'kissen', 'decke', 'biancheria', 'cuscino', 'bedding', 'duvet', 'cushion', 'throw', 'pillow', 'towel']),
    ('Área externa', ['jardim', 'exterior', 'varanda', 'jardin', 'terraza', 'outdoor', 'garten', 'giardino', 'patio']),
    # "mesa" sem tipo (só depois de todas as mesas específicas)
    ('Mesa de jantar?', ['mesa', 'table', 'tisch', 'tavolo']),
    ('Decoração', ['vaso', 'jarra', 'castical', 'vela', 'bandeja', 'cesto', 'escultura', 'florero', 'jarron', 'vase', 'bougeoir', 'plateau', 'panier', 'deko', 'kerze', 'korb', 'candle', 'tray', 'basket', 'decor']),
]


# ------------------------------------------------------------- util
def sem_acento(s):
    s = unicodedata.normalize('NFKD', s or '')
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()


def limpa(s):
    return re.sub(r'\s+', ' ', html.unescape(str(s or ''))).strip()


def baixar(url, timeout=25):
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pt-PT,pt;q=0.9,en;q=0.8,de;q=0.7,fr;q=0.6,es;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        enc = (r.headers.get('Content-Encoding') or '').lower()
        if enc == 'gzip':
            raw = gzip.decompress(raw)
        elif enc == 'deflate':
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        charset = r.headers.get_content_charset() or 'utf-8'
        return r.geturl(), raw.decode(charset, errors='replace')


# ------------------------------------------------------- leitor HTML
class Leitor(HTMLParser):
    """Junta meta tags, blocos JSON-LD, <title> e itemprops."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.jsonld = []
        self.title = ''
        self.itemprop = {}
        self._em = None
        self._buf = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or '') for k, v in attrs}
        if tag == 'meta':
            chave = (a.get('property') or a.get('name') or a.get('itemprop') or '').lower()
            if chave and 'content' in a and chave not in self.meta:
                self.meta[chave] = a['content']
        if a.get('itemprop') and a.get('itemprop') not in self.itemprop:
            v = a.get('content') or a.get('src') or a.get('href')
            if v:
                self.itemprop[a['itemprop']] = v
        if tag == 'script' and 'ld+json' in a.get('type', '').lower():
            self._em, self._buf = 'ld', []
        elif tag == 'title' and not self.title:
            self._em, self._buf = 'title', []

    def handle_data(self, data):
        if self._em:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if self._em == 'ld' and tag == 'script':
            self.jsonld.append(''.join(self._buf))
            self._em = None
        elif self._em == 'title' and tag == 'title':
            self.title = limpa(''.join(self._buf))
            self._em = None


def nos_jsonld(textos):
    """Achata todos os objetos JSON-LD (inclui @graph e listas)."""
    saida = []

    def anda(o):
        if isinstance(o, list):
            for x in o:
                anda(x)
        elif isinstance(o, dict):
            saida.append(o)
            for k in ('@graph', 'mainEntity', 'itemListElement', 'hasVariant'):
                if k in o:
                    anda(o[k])
    for t in textos:
        t = t.strip().rstrip(';')
        try:
            anda(json.loads(t))
        except Exception:
            # alguns sites colocam vários JSON seguidos ou com lixo
            try:
                anda(json.loads(re.sub(r'[\x00-\x1f]', ' ', t)))
            except Exception:
                pass
    return saida


def eh_tipo(o, nome):
    t = o.get('@type')
    t = t if isinstance(t, list) else [t]
    return any(str(x).lower() == nome.lower() for x in t)


def primeira_img(v):
    if isinstance(v, list):
        for x in v:
            r = primeira_img(x)
            if r:
                return r
        return ''
    if isinstance(v, dict):
        return v.get('contentUrl') or v.get('url') or ''
    return v or ''


def numero(v):
    """'1.299,00 €' / '1,299.00' / 499 -> 1299.0"""
    if v is None or v == '':
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r'[^\d,.]', '', str(v))
    if not s:
        return None
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.') if s.rfind(',') > s.rfind('.') else s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.') if len(s.split(',')[-1]) in (1, 2) else s.replace(',', '')
    elif s.count('.') > 1 or (s.count('.') == 1 and len(s.split('.')[-1]) == 3):
        s = s.replace('.', '')
    try:
        return float(s)
    except ValueError:
        return None


def preco_das_ofertas(offers):
    """Devolve (preço, moeda) da oferta (menor preço se houver várias)."""
    lista = offers if isinstance(offers, list) else [offers]
    achados = []
    for of in lista:
        if not isinstance(of, dict):
            continue
        moeda = of.get('priceCurrency') or ''
        for k in ('price', 'lowPrice'):
            p = numero(of.get(k))
            if p:
                achados.append((p, moeda))
                break
        spec = of.get('priceSpecification')
        for sp in (spec if isinstance(spec, list) else [spec]):
            if isinstance(sp, dict) and numero(sp.get('price')):
                achados.append((numero(sp.get('price')), sp.get('priceCurrency') or moeda))
        if 'offers' in of:
            r = preco_das_ofertas(of['offers'])
            if r[0]:
                achados.append(r)
    achados = [a for a in achados if a[0] and a[0] > 0]
    return min(achados) if achados else (None, '')


# ------------------------------------------------------------ lojas
def carregar_lojas():
    """ferramentas/lojas.json: domínio -> {nome, regiao}.
    Se existir ferramentas/lojas-wix.csv (export da coleção Lojas do
    Wix), também pega o ID para preencher a referência lojaId."""
    caminho = os.path.join(AQUI, 'lojas.json')
    lojas = {}
    if os.path.exists(caminho):
        with open(caminho, encoding='utf-8') as f:
            for dom, info in json.load(f).items():
                lojas[dom.lower()] = dict(info)
    csv_wix = os.path.join(AQUI, 'lojas-wix.csv')
    if os.path.exists(csv_wix):
        with open(csv_wix, encoding='utf-8-sig') as f:
            for linha in csv.DictReader(f):
                low = {k.lower().strip(): (v or '').strip() for k, v in linha.items() if k}
                site = low.get('site') or ''
                dom = dominio(site) if site else ''
                if not dom:
                    continue
                item = lojas.setdefault(dom, {})
                item.setdefault('nome', low.get('nome') or low.get('title') or dom)
                if low.get('regiao'):
                    item.setdefault('regiao', low['regiao'].strip('[]" '))
                item['id'] = low.get('id') or low.get('_id') or ''
    return lojas


def dominio(url):
    h = urlparse(url if '//' in url else '//' + url).netloc.lower()
    return h[4:] if h.startswith('www.') else h


def achar_loja(url, lojas):
    d = dominio(url)
    partes = d.split('.')
    for i in range(len(partes) - 1):
        cand = '.'.join(partes[i:])
        if cand in lojas:
            return cand, lojas[cand]
    return d, None


def regiao_por(moeda, dom):
    m = (moeda or '').upper()
    if m == 'BRL' or dom.endswith('.br'):
        return 'brasil'
    return 'europa'


def faixa(preco, regiao):
    if not preco:
        return ''
    for i, lim in enumerate(FAIXAS.get(regiao, FAIXAS['europa']), start=1):
        if preco <= lim:
            return i
    return 5


def sugerir_categoria(*textos):
    t = ' ' + sem_acento(' '.join(textos)).replace('-', ' ').replace('_', ' ').replace('/', ' ') + ' '
    for cat, palavras in CATEGORIAS:
        for p in palavras:
            if re.search(r'(?<![a-z])' + re.escape(p.strip()) + r'(?![a-z])', t):
                return cat
    return ''


def nome_do_link(url):
    """Quando a loja bloqueia: tira um nome provisório do próprio link."""
    partes = [x for x in urlparse(url).path.split('/') if x]
    if not partes:
        return ''
    slug = max(partes, key=len)
    slug = re.sub(r'\.(html?|aspx?|php)$', '', slug)
    slug = re.sub(r'[-_]?[A-Za-z]*\d{5,}[A-Za-z0-9]*$', '', slug)
    return slug.replace('-', ' ').replace('_', ' ').strip().capitalize()


def variante_sklum(pagina, url, r):
    """Sklum: cada cor (?id_c=...) é a mesma página, mas tem código, cor,
    foto e preço próprios num bloco de dados. Sem id_c, vale a 1ª cor."""
    if 'sklum.' not in urlparse(url).netloc:
        return
    combos = list(re.finditer(r'"(\d{4,})":\{"p":([\d.]+),"att"', pagina))
    if not combos:
        return
    colecao = re.search(r'"collection":"((?:[^"\\]|\\.)+)"', pagina)
    if colecao:
        r['modelo'] = json.loads('"' + colecao.group(1) + '"').strip()
    pedido = (parse_qs(urlparse(url).query).get('id_c') or [''])[0]
    m = next((c for c in combos if c.group(1) == pedido), combos[0])
    bloco = pagina[m.start():m.start() + 4000]
    r['referencia'] = m.group(1)
    r['preco'] = float(m.group(2))
    r['moeda'] = r['moeda'] or 'EUR'
    cor = re.search(r'"color":"((?:[^"\\]|\\.)*)"', bloco)
    if cor:
        cor = json.loads('"' + cor.group(1) + '"')
        cor = re.sub(r'^\S*(farbe|color|colour|cor)\S*\s+', '', cor, flags=re.I).strip()
        if cor and r['nome']:
            r['nome'] = f"{r['nome']} - {cor}"
    # iM = foto principal da cor (a que a loja mostra primeiro)
    foto = re.search(r'"iM":(\d+)', bloco)
    if foto and r['imagem']:
        r['imagem'] = re.sub(r'/\d+/([^/]+)$', '/' + foto.group(1) + r'/\1', r['imagem'])


# -------------------------------------------------------- captura
def capturar(url, lojas):
    r = {'link': url, 'nome': '', 'imagem': '', 'preco': None, 'moeda': '',
         'loja': '', 'lojaId': '', 'regiao': '', 'categoria': '', 'faixaPreco': '',
         'referencia': '', 'conferir': []}
    try:
        final, pagina = baixar(url)
    except Exception as e:
        r['conferir'].append(f'não abriu ({getattr(e, "code", "") or e.__class__.__name__})')
        dom, info = achar_loja(url, lojas)
        r['loja'] = (info or {}).get('nome', dom)
        r['lojaId'] = (info or {}).get('id', '')
        r['regiao'] = (info or {}).get('regiao') or regiao_por('', dom)
        r['nome'] = nome_do_link(url)
        r['categoria'] = sugerir_categoria(url).rstrip('?')
        return r

    p = Leitor()
    try:
        p.feed(pagina)
    except Exception:
        pass
    nos = nos_jsonld(p.jsonld)
    prod = next((o for o in nos if eh_tipo(o, 'Product') or eh_tipo(o, 'ProductGroup')), None)
    m = p.meta

    if prod:
        r['nome'] = limpa(prod.get('name'))
        r['imagem'] = primeira_img(prod.get('image'))
        r['preco'], r['moeda'] = preco_das_ofertas(prod.get('offers'))
        if not r['preco'] and prod.get('hasVariant'):
            r['preco'], r['moeda'] = preco_das_ofertas([v.get('offers') for v in prod['hasVariant'] if isinstance(v, dict)])
        r['referencia'] = limpa(prod.get('sku') or prod.get('mpn') or '')

    r['nome'] = r['nome'] or limpa(m.get('og:title') or m.get('twitter:title') or p.title)
    r['imagem'] = r['imagem'] or m.get('og:image') or m.get('og:image:secure_url') or m.get('twitter:image') or p.itemprop.get('image', '')
    if not r['preco']:
        for k in ('product:price:amount', 'og:price:amount', 'product:sale_price:amount', 'price'):
            if numero(m.get(k)):
                r['preco'] = numero(m.get(k))
                r['moeda'] = m.get(k.replace('amount', 'currency')) or m.get('pricecurrency') or ''
                break
    if not r['preco'] and numero(p.itemprop.get('price')):
        r['preco'] = numero(p.itemprop.get('price'))
        r['moeda'] = p.itemprop.get('priceCurrency', '')
    variante_sklum(pagina, url, r)
    if r['imagem']:
        r['imagem'] = urljoin(final, r['imagem'].strip())
        if r['imagem'].startswith('//'):
            r['imagem'] = 'https:' + r['imagem']

    dom, info = achar_loja(final, lojas)
    r['loja'] = (info or {}).get('nome') or limpa(m.get('og:site_name')) or dom
    r['lojaId'] = (info or {}).get('id', '')
    r['regiao'] = (info or {}).get('regiao') or regiao_por(r['moeda'], dom)
    r['faixaPreco'] = faixa(r['preco'], r['regiao'])
    # categoria: primeiro pelo nome; se não der, pelo link; por fim pela
    # trilha da loja (ex.: "Casa > Móveis > Cadeiras") e categoria da ficha
    trilha = [limpa((x.get('item') or {}).get('name') if isinstance(x.get('item'), dict) else x.get('name'))
              for o in nos if eh_tipo(o, 'BreadcrumbList')
              for x in (o.get('itemListElement') or []) if isinstance(x, dict)]
    ficha_cat = limpa((prod or {}).get('category') if not isinstance((prod or {}).get('category'), dict) else '')
    palpites = [sugerir_categoria(t) for t in (r['nome'], urlparse(final).path,
                                                 ' '.join(reversed(trilha)), ficha_cat)]
    palpites = [c for c in palpites if c]
    # um palpite específico (ex.: "Mesa de jantar" pela trilha) vence o genérico "mesa"
    r['categoria'] = next((c for c in palpites if not c.endswith('?')), palpites[0] if palpites else '')
    r['link'] = url

    # nome sem o "| Loja" do fim do <title>
    if r['nome'] and r['loja']:
        r['nome'] = re.sub(r'\s*[|\-–—]\s*' + re.escape(r['loja']) + r'.*$', '', r['nome'], flags=re.I).strip()

    r['eh_lista'] = (not prod and any(o for o in nos if eh_tipo(o, 'ItemList') or eh_tipo(o, 'CollectionPage'))) \
        or bool(re.search(r'/(cat|category|categoria|kategorie|c)/', urlparse(final).path)) and not prod
    if not prod:
        r['conferir'].append('loja não publica ficha do produto')
    if not r['nome']:
        r['conferir'].append('sem nome')
    if not r['imagem']:
        r['conferir'].append('sem foto')
    if not r['preco']:
        r['conferir'].append('sem preço')
    if r['categoria'].endswith('?'):  # "mesa" sem tipo: palpite, confirmar
        r['categoria'] = r['categoria'].rstrip('?')
        r['conferir'].append('categoria (confirmar tipo de mesa)')
    if not r['categoria']:
        r['conferir'].append('categoria')
    if not info:
        r['conferir'].append('loja nova (cadastrar)')
    return r


# ---------------------------------------------------------- saídas
COLUNAS = ['nome', 'referencia', 'link', 'imagem', 'lojaId', 'loja', 'categoria',
           'faixaPreco', 'preco', 'moeda', 'regiao', 'conferir']


def salvar_csv(itens, caminho):
    with open(caminho, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, extrasaction='ignore')
        w.writeheader()
        for it in itens:
            linha = dict(it)
            linha['preco'] = f"{it['preco']:.2f}" if it['preco'] else ''
            linha['conferir'] = '; '.join(it['conferir'])
            w.writerow(linha)


def fmt_preco(it):
    if not it['preco']:
        return '—'
    s = f"{it['preco']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    simb = {'EUR': '€', 'BRL': 'R$', 'GBP': '£', 'USD': '$', 'CHF': 'CHF', 'SEK': 'kr', 'DKK': 'kr', 'PLN': 'zł'}
    return f"{simb.get((it['moeda'] or '').upper(), it['moeda'] or '')} {s}".strip()


def salvar_previa(itens, caminho):
    e = html.escape
    cards = []
    for it in itens:
        simb = SIMBOLO.get(it['regiao'], '€')
        faixa_txt = simb * int(it['faixaPreco']) if it['faixaPreco'] else '—'
        aviso = ''
        if it['conferir']:
            aviso = '<p class="aviso">Conferir: ' + e(', '.join(it['conferir'])) + '</p>'
        img = (f'<img src="{e(it["imagem"])}" alt="" loading="lazy" referrerpolicy="no-referrer">'
               if it['imagem'] else '<div class="semfoto">sem foto</div>')
        cards.append(f'''
<article class="card{' alerta' if it['conferir'] else ''}">
  <a href="{e(it['link'])}" target="_blank" rel="noopener">{img}</a>
  <div class="info">
    <p class="loja">{e(it['loja'])}</p>
    <h2>{e(it['nome'] or '(sem nome)')}</h2>
    <p class="cat">{e(it['categoria'] or 'sem categoria')}</p>
    <p class="preco"><span>{e(fmt_preco(it))}</span><b>{e(faixa_txt)}</b></p>
    {aviso}
  </div>
</article>''')
    ok = sum(1 for it in itens if not it['conferir'])
    hoje = dt.date.today().strftime('%d/%m/%Y')
    doc = f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prévia da captura</title>
<link href="https://fonts.googleapis.com/css2?family=Marcellus&family=Lato:wght@400;700&display=swap" rel="stylesheet">
<style>
:root{{--linho:#F4EFE7;--papel:#FBF8F3;--tinta:#2E2A26;--bronze:#9A7B4F;--suave:#7A716A;--alerta:#A05A4A;--borda:#E4DCCF}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--linho:#1E1B18;--papel:#26221E;--tinta:#EFE8DD;--bronze:#C9A878;--suave:#A99F95;--alerta:#D98C7A;--borda:#3A342E}}}}
:root[data-theme="dark"]{{--linho:#1E1B18;--papel:#26221E;--tinta:#EFE8DD;--bronze:#C9A878;--suave:#A99F95;--alerta:#D98C7A;--borda:#3A342E}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--linho);color:var(--tinta);font-family:Lato,system-ui,sans-serif;padding:24px 16px}}
header{{max-width:1100px;margin:0 auto 20px}}
h1{{font-family:Marcellus,serif;font-weight:400;font-size:28px;margin:0 0 4px}}
header p{{margin:0;color:var(--suave)}}
.grade{{max-width:1100px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:16px}}
.card{{background:var(--papel);border:1px solid var(--borda);border-radius:10px;overflow:hidden;display:flex;flex-direction:column}}
.card.alerta{{border-color:var(--alerta)}}
.card img,.semfoto{{width:100%;aspect-ratio:1/1;object-fit:contain;background:#fff;display:block}}
.semfoto{{display:grid;place-items:center;color:var(--suave);background:var(--linho)}}
.info{{padding:12px 14px 14px}}
.loja{{margin:0;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--bronze)}}
h2{{font-family:Marcellus,serif;font-weight:400;font-size:17px;margin:4px 0 6px;line-height:1.25}}
.cat{{margin:0 0 8px;font-size:13px;color:var(--suave)}}
.preco{{margin:0;display:flex;justify-content:space-between;font-size:14px}}
.preco b{{color:var(--bronze);font-weight:700}}
.aviso{{margin:10px 0 0;font-size:12px;color:var(--alerta)}}
</style></head><body>
<header><h1>Prévia da captura</h1>
<p>{hoje} · {len(itens)} produtos · {ok} completos · {len(itens) - ok} para conferir</p></header>
<main class="grade">{''.join(cards)}</main>
</body></html>'''
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(doc)


# ------------------------------------------------------------ main
def ler_links(entradas):
    links = []
    for x in entradas:
        if os.path.exists(x):
            with open(x, encoding='utf-8') as f:
                texto = f.read()
        else:
            texto = x
        links += re.findall(r'https?://[^\s<>"\']+', texto)
    vistos, unicos = set(), []
    for l in links:
        l = l.rstrip('.,;)')
        if l not in vistos:
            vistos.add(l)
            unicos.append(l)
    return unicos


def main():
    ap = argparse.ArgumentParser(description='Captura produtos a partir dos links das lojas.')
    ap.add_argument('entradas', nargs='+', help='links ou arquivo(s) .txt com links')
    ap.add_argument('--saida', default=None, help='pasta de saída (padrão: capturas/AAAA-MM-DD-HHMM)')
    a = ap.parse_args()

    links = ler_links(a.entradas)
    if not links:
        sys.exit('Nenhum link encontrado.')
    saida = a.saida or os.path.join(os.path.dirname(AQUI), 'capturas', dt.datetime.now().strftime('%Y-%m-%d-%H%M'))
    os.makedirs(saida, exist_ok=True)

    lojas = carregar_lojas()
    itens = []
    for i, url in enumerate(links, 1):
        it = capturar(url, lojas)
        itens.append(it)
        marca = '✓' if not it['conferir'] else '!'
        print(f"[{i}/{len(links)}] {marca} {it['loja']} · {it['nome'][:60] or '(sem nome)'} · {fmt_preco(it)} · {it['categoria'] or '?'}"
              + (f"  → conferir: {', '.join(it['conferir'])}" if it['conferir'] else ''))

    salvar_csv(itens, os.path.join(saida, 'produtos.csv'))
    salvar_previa(itens, os.path.join(saida, 'previa.html'))
    with open(os.path.join(saida, 'produtos.json'), 'w', encoding='utf-8') as f:
        json.dump(itens, f, ensure_ascii=False, indent=2)
    print(f'\nPronto: {saida}/previa.html e {saida}/produtos.csv')


if __name__ == '__main__':
    main()
