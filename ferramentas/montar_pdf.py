#!/usr/bin/env python3
# =============================================================
#  montar_pdf.py  —  Da lista de links ao PDF da curadoria.
#
#  Lê um arquivo de texto com UM LINK POR LINHA, em qualquer ordem:
#
#      https://loja.com/sofa-lago
#      https://loja.com/cadeira-ana
#      https://loja.com/sofa-dara | nome: Dara | medidas: 100 × 220 cm
#
#  • Cada produto vai SOZINHO para a página da sua categoria
#    (Sofá, Cadeira, Mesa de jantar…), na ordem da curadoria.
#  • Errou a categoria? Escreva "| categoria: Mesa lateral".
#    Ou agrupe à mão com uma linha "# Título" antes dos links.
#  • Depois do link, opcional, com "|": nome, loja, medidas,
#    detalhe, preco (ex.: 1290), faixa (1 a 5), foto (link da imagem),
#    categoria.
#    O que você escrever aqui vale mais que o capturado.
#
#  Gera, na pasta de saída: curadoria.pdf (A4 vertical, 6 por
#  página), curadoria.html e conferir.txt (o que faltou capturar).
#
#  USO:
#    python3 ferramentas/montar_pdf.py lista.txt
#    python3 ferramentas/montar_pdf.py lista.txt --titulo "Curadoria Europa" --saida capturas/europa
# =============================================================

import argparse
import base64
import datetime as dt
import html
import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capturar as cap  # noqa: E402

POR_PAGINA = 6
# Ordem das páginas — a mesma de CATEGORIES em assets/config.js.
ORDEM = [
    'Aparador & Buffet', 'Banco & Banqueta', 'Cadeira',
    'Cama', 'Cômoda', 'Cristaleira', 'Escritório · Mesas', 'Escritório · Cadeiras', 'Escritório · Armários', 'Estante', 'Rack de TV', 'Mesa de cabeceira',
    'Mesa de centro', 'Mesa de jantar', 'Mesa lateral', 'Carrinho', 'Poltrona', 'Puff', 'Sofá', 'Sofá cama',
    'Área externa', 'Cortina', 'Decoração', 'Espelho',
    'Luminária de teto', 'Luminária de mesa', 'Luminária de piso', 'Luminária de parede', 'Iluminação',
    'Papel de parede', 'Quadros & Arte', 'Roupa de cama & Têxtil', 'Tapete',
    'Infantil · Camas', 'Infantil · Mesas & Cadeiras', 'Infantil · Escrivaninhas', 'Infantil · Organização',
    'Infantil · Almofadas & Tapetes', 'Infantil · Decoração', 'Depósito & Organização', 'Depósito & Organização · Cestos',
]
# Como cada página aparece (plural). O nome interno da categoria não muda.
PLURAL = {
    'Aparador & Buffet': 'Aparadores & Buffets', 'Banco & Banqueta': 'Bancos & Banquetas', 'Cadeira': 'Cadeiras',
    'Cama': 'Camas', 'Cômoda': 'Cômodas', 'Cristaleira': 'Cristaleiras', 'Estante': 'Estantes', 'Rack de TV': 'Racks de TV',
    'Mesa de cabeceira': 'Mesas de cabeceira', 'Mesa de centro': 'Mesas de centro', 'Mesa de jantar': 'Mesas de jantar',
    'Mesa lateral': 'Mesas laterais', 'Carrinho': 'Carrinhos', 'Poltrona': 'Poltronas', 'Puff': 'Pufes', 'Sofá': 'Sofás',
    'Sofá cama': 'Sofás-cama', 'Cortina': 'Cortinas', 'Espelho': 'Espelhos', 'Luminária de teto': 'Luminárias de teto',
    'Luminária de mesa': 'Luminárias de mesa', 'Luminária de piso': 'Luminárias de piso',
    'Luminária de parede': 'Luminárias de parede', 'Papel de parede': 'Papéis de parede', 'Tapete': 'Tapetes',
}


def exibir(t):
    """Nome da página como aparece no catálogo ('Cômoda' -> 'Cômodas')."""
    if ' · ' in t:
        g, sub = t.split(' · ', 1)
        return f'{PLURAL.get(g, g)} · {PLURAL.get(sub, sub)}'
    return PLURAL.get(t, t)


# Páginas em que as medidas aparecem no card (nas outras, não).
COM_MEDIDAS = {'Espelho'}
OUTROS = 'Outros'
SIMB = {'europa': '€', 'brasil': 'R$'}
MOEDA = {'EUR': '€', 'BRL': 'R$', 'GBP': '£', 'USD': '$', 'CHF': 'CHF'}


# ------------------------------------------------------------ lista
def ler_lista(caminho):
    secoes, atual = [], None
    with open(caminho, encoding='utf-8') as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            if linha.startswith('#'):
                atual = {'titulo': linha.lstrip('#').strip(), 'itens': []}
                secoes.append(atual)
                continue
            m = re.match(r'(https?://[^\s|]+)(.*)$', linha)
            if not m:
                continue
            extra = {}
            for parte in m.group(2).split('|')[1:]:
                if ':' in parte:
                    k, v = parte.split(':', 1)
                    extra[cap.sem_acento(k.strip())] = v.strip()
            if atual is None:
                atual = {'titulo': '', 'itens': []}
                secoes.append(atual)
            atual['itens'].append({'url': limpar_link(m.group(1)), 'extra': extra})
    # mesmo link duas vezes (ex.: com e sem "#content") entra uma vez só
    vistos = set()
    for s in secoes:
        unicos = []
        for it in s['itens']:
            if it['url'] in vistos:
                REPETIDOS.append(it['url'])
                continue
            vistos.add(it['url'])
            unicos.append(it)
        s['itens'] = unicos
    return secoes


REPETIDOS = []


def limpar_link(url):
    """Tira #âncora e parâmetros de rastreio (utm, gclid...) do link."""
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
    u = urlsplit(url.rstrip('.,;)'))
    q = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True)
         if not re.match(r'(utm_|gclid|fbclid|mc_|ref$|srsltid)', k, re.I)]
    return urlunsplit((u.scheme, u.netloc.lower(), u.path, urlencode(q), ''))


MEDIDA = re.compile(r'(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)(?:\s*[x×]\s*(\d+(?:[.,]\d+)?))?\s*cm', re.I)


def tamanho(nome):
    """Área aproximada pelas medidas do nome (para ordenar menor → maior)."""
    m = MEDIDA.search(nome or '')
    if not m:
        return 0
    nums = [float(g.replace(',', '.')) for g in m.groups() if g]
    return nums[0] * (nums[1] if len(nums) > 1 else 1)


def medidas_do_nome(nome):
    """'... 160x200 cm' -> '160 × 200 cm'; '... 50 cm' (redondo) -> 'Ø 50 cm'"""
    m = MEDIDA.search(nome or '')
    if m:
        return ' × '.join(g for g in m.groups() if g) + ' cm'
    m = re.search(r'(?:Ø|ø|⌀)?\s*(\d+(?:[.,]\d+)?)\s*cm\b', nome or '')
    return f'Ø {m.group(1)} cm' if m else ''


def variacao(nome):
    """'RAMNEFJÄLL Bettgestell - Idekulla beige/Luröy 160x200 cm' -> 'Idekulla beige'"""
    partes = re.split(r'\s+[-–—]\s+', nome or '', maxsplit=1)
    if len(partes) < 2:
        return ''
    v = MEDIDA.sub('', partes[1]).split('/')[0].split(',')[0].strip()
    return v[:24]


def _carregar_traducoes():
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'traducoes.json'), encoding='utf-8') as f:
            return {cap.sem_acento(k): v for k, v in json.load(f).items() if not k.startswith('_')}
    except Exception:
        return {}


TRADUCOES = _carregar_traducoes()


def traduzir(texto):
    """'4 Schubladen dunkel graublau' -> '4 gavetas azul acinzentado escuro'."""
    texto = texto.replace('~', ' ')
    texto = re.sub(r'\bmit\s+aufbewahrung\b', 'com baú', texto, flags=re.I)
    texto = re.sub(r'\bmit\s+stauraum\b', 'com baú', texto, flags=re.I)
    saida, adiar = [], ''
    for w in texto.split():
        t = TRADUCOES.get(cap.sem_acento(w).strip('-'), w)
        if t in ('escuro', 'claro'):  # "dunkel graublau" -> "azul acinzentado escuro"
            adiar = t
            continue
        if t:
            saida.append(t)
            if adiar:
                saida.append(adiar)
                adiar = ''
    if adiar:
        saida.append(adiar)
    # sem palavras repetidas ("branco Lappviken branco" -> "branco Lappviken")
    vistas, unicas = set(), []
    for w in ' '.join(saida).split():
        if w.lower() not in vistas:
            vistas.add(w.lower())
            unicas.append(w)
    return ' '.join(unicas)


def diferencas(nomes):
    """Do grupo de nomes completos, devolve para cada um só as palavras que
    os outros não têm (sem medidas): o que distingue a variação."""
    def palavras(n):
        n = MEDIDA.sub('', n or '')
        # "mit Fach" fica junto (vira "com nicho"), senão o "mit" some como palavra comum
        n = re.sub(r'\b(mit|m\.|com|with|avec|con)\s+(?=[^\W\d])', lambda m: m.group(1) + '~', n, flags=re.I)
        n = re.sub(r'(?:Ø|ø|⌀)?\s*\d+(?:[.,]\d+)?\s*(?:cm|mm|l|cl|ml)\b', '', n)
        return [w for w in re.split(r'[\s/,()]+|\s[-–—]\s', n) if w and w not in '-–—']
    listas = [palavras(n) for n in nomes]
    comuns = set.intersection(*[set(cap.sem_acento(w) for w in l) for l in listas]) if listas else set()
    saida = []
    for l in listas:
        # número sozinho leva a palavra seguinte junto ("3" -> "3 Spots")
        v = ' '.join(w + (' ' + l[i + 1] if w.isdigit() and i + 1 < len(l) and cap.sem_acento(l[i + 1]) in comuns else '')
                     for i, w in enumerate(l) if cap.sem_acento(w) not in comuns)
        saida.append(v)
    return saida


def nome_curto(nome, secao=''):
    """Nome de vitrine, sem repetir a categoria da página:
    'STRANDMON Poltrona - Talliden bege' -> 'Strandmon'
    'Poltrona Beegees Suede Preta' (seção Poltronas) -> 'Beegees Suede Preta'"""
    n = re.split(r'\s+[-–—|]\s+|,\s', nome or '')[0].strip()
    # padrão IKEA (MODELO em maiúsculas no começo) é tratado mais abaixo
    ikea = bool(re.match(r'^[A-ZÀ-Þ]{2,}\b', n)) and not n.split()[0].isdigit()
    # padrão "Tipo aus/in/em Material Modelo" (Sklum e outras):
    # '3-Sitzer-Sofa aus Chenille Coco' -> 'Coco'
    m = None if ikea else re.match(r'^(\S+(?:\s\S+){0,3}?)\s+(?:aus|in|mit|em|de|en|with)\s+.+\s([A-ZÀ-Þ][\w\'’-]+)$', n)
    if m and cap.sugerir_categoria(m.group(1).replace('-', ' ')):
        return m.group(2)
    # padrão "Modelo Tipo ..." ('Olivia 3-Sitzer-Sofa aus Akazienholz' -> 'Olivia')
    m = re.match(r'^([A-ZÀ-Þ][a-zà-ÿ]+)\s+(\S+)', n)
    if m and not m.group(1).isupper() and cap.sugerir_categoria(m.group(2).replace('-', ' ')) \
            and not cap.sugerir_categoria(m.group(1)):
        return m.group(1)
    # padrão "Tipo aus Modelo-Stoff" ('3-Sitzer-Schlafsofa aus Oleguer-Stoff' -> 'Oleguer')
    m = re.match(r'^(\S+(?:\s\S+){0,3}?)\s+(?:aus|in|em|de)\s+([A-ZÀ-Þ][\w]+)-(?:Stoff|Leinen|Samt|Bouclé|Boucle)\b', n)
    if m and cap.sugerir_categoria(m.group(1).replace('-', ' ')):
        return m.group(2)
    palavras = n.split()
    # padrão IKEA: MODELO EM MAIÚSCULAS + descrição -> só o modelo
    caps = []
    for w in palavras:
        if (len(w) >= 2 and w.isupper() and any(c.isalpha() for c in w)) or (w == '/' and caps):
            caps.append(w)
        else:
            break
    if caps and len(caps) < len(palavras):
        palavras = caps
    # tira a categoria do começo ("Poltrona ...", "Mesa de cabeceira ...")
    sec = cap.sem_acento(secao).split()
    i = 0
    while i < len(palavras) - 1 and i < len(sec) and cap.sem_acento(palavras[i]).rstrip('s') == sec[i].rstrip('s'):
        i += 1
    palavras = palavras[i:]
    n = ' '.join(w.capitalize() if w.isupper() and len(w) > 3 else w for w in palavras)
    if len(n) > 34:
        n = n[:34].rsplit(' ', 1)[0] + '…'
    return n[:1].upper() + n[1:]


def cortar_sobra(im, folga=0.04):
    """Corta a margem branca/clara em volta do móvel (fotos de loja
    costumam ter muita sobra) e deixa uma folga pequena."""
    from PIL import ImageChops, Image
    cinza = im.convert('L')
    w, h = im.size
    cantos = [cinza.getpixel(p) for p in ((2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3))]
    fundo = cinza.getpixel((0, 0))
    # só mexe em fundo de estúdio: claro (branco ou cinza claro) e uniforme nos cantos
    if min(cantos) < 165 or max(cantos) - min(cantos) > 30:
        return im
    limite = 14 if fundo >= 225 else 26  # cinza de estúdio tem sombra suave: tolera mais
    dif = ImageChops.difference(cinza, Image.new('L', im.size, fundo)).point(lambda v: 255 if v > limite else 0)
    caixa = dif.getbbox()
    if not caixa:
        return im
    l, t, r, b = caixa
    f = int(max(r - l, b - t) * folga)
    l, t, r, b = max(0, l - f), max(0, t - f), min(im.width, r + f), min(im.height, b + f)
    novo = Image.new('RGB', (r - l, b - t), (fundo,) * 3)
    novo.paste(im.crop((l, t, r, b)))
    return novo


def enquadrar(im, proporcao=1.7):
    """Foto vertical (comum em fotos de estúdio/ambiente) num quadro
    horizontal: corta na largura toda, centralizando na faixa onde está o
    móvel (as linhas com mais detalhe)."""
    w, h = im.size
    if w / h >= 0.85:  # só fotos claramente verticais (quadradas ficam inteiras)
        return im
    from PIL import ImageFilter
    from PIL import Image
    bordas = im.convert('L').filter(ImageFilter.FIND_EDGES)
    linhas = list(bordas.resize((1, h), Image.BOX).tobytes())  # média de detalhe por linha
    total = sum(linhas) or 1
    centro = sum(y * v for y, v in enumerate(linhas)) / total
    alto = min(h, int(w / proporcao))
    topo = int(min(max(0, centro - alto / 2), h - alto))
    return im.crop((0, topo, w, topo + alto))


def reduzir(dados, tipo, lado=900):
    """Deixa o PDF leve: foto até 900px, JPEG, fundo branco.
    Sem o Pillow instalado (pip install pillow), usa a foto original."""
    try:
        from io import BytesIO
        from PIL import Image
        im = Image.open(BytesIO(dados))
        im.thumbnail((lado, lado))
        if im.mode in ('RGBA', 'LA', 'P'):
            im = im.convert('RGBA')
            fundo = Image.new('RGB', im.size, 'white')
            fundo.paste(im, mask=im.split()[-1])
            im = fundo
        else:
            im = im.convert('RGB')
        cortada = cortar_sobra(im)
        # recorte de verdade (móvel em fundo branco) fica como está, mesmo
        # vertical (luminárias); se o corte mal mudou a foto, enquadra
        recortou = cortada.width * cortada.height < 0.7 * im.width * im.height
        im = cortada if recortou else enquadrar(im)
        out = BytesIO()
        im.save(out, 'JPEG', quality=84, optimize=True)
        return out.getvalue(), 'image/jpeg'
    except Exception:
        return dados, tipo


# ------------------------------------------------- fotos: só o móvel, fundo branco
PASTA_FOTOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'capturas', '.fotos')
VERSAO_FOTOS = '7'  # mude para refazer todas as fotos
_sessao, _trava = None, threading.Lock()


def _baixar_bytes(url):
    if not re.match(r'https?://', url):  # foto salva no repositório (ex.: curadoria/fotos/x.webp)
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(url if os.path.isabs(url) else os.path.join(raiz, url), 'rb') as f:
            return f.read()
    req = urllib.request.Request(url, headers={'User-Agent': cap.UA, 'Accept': 'image/avif,image/webp,image/*,*/*;q=0.8'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def _abrir(dados):
    from io import BytesIO
    from PIL import Image
    im = Image.open(BytesIO(dados))
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA')
        fundo = Image.new('RGB', im.size, 'white')
        fundo.paste(im, mask=im.split()[-1])
        return fundo
    return im.convert('RGB')


def _borda(im):
    """(média, desvio) do brilho numa moldura fina em volta da foto."""
    from PIL import ImageStat
    g = im.convert('L')
    w, h = g.size
    e = max(2, min(w, h) // 50)
    faixas = [g.crop((0, 0, w, e)), g.crop((0, h - e, w, h)), g.crop((0, 0, e, h)), g.crop((w - e, 0, w, h))]
    medias = [ImageStat.Stat(f).mean[0] for f in faixas]
    desvios = [ImageStat.Stat(f).stddev[0] for f in faixas]
    return sum(medias) / 4, max(desvios), min(medias)


def _ja_branca(im):
    media, desvio, minimo = _borda(im)
    return minimo >= 248 and desvio < 6


def _quase_branca(im):
    """Fundo liso quase branco (ex.: cinza clarinho da IKEA)."""
    media, desvio, minimo = _borda(im)
    return minimo >= 222 and desvio < 20  # tolera a sombra suave embaixo do móvel


def _clarear(im):
    """Leva o fundo quase branco a branco puro (sem recortar o móvel,
    então móvel branco não ganha contorno)."""
    from PIL import ImageStat
    w, h = im.size
    e = max(2, min(w, h) // 50)
    amostra = [im.crop(c) for c in ((0, 0, w, e), (0, h - e, w, h))]
    ref = [sum(ImageStat.Stat(a).median[i] for a in amostra) / 2 for i in range(3)]
    canais = [c.point(lambda v, k=255 / max(r, 1): min(255, int(v * k + 0.5))) for c, r in zip(im.split(), ref)]
    from PIL import Image
    return Image.merge('RGB', canais)


def _eh_desenho(im):
    """Desenho técnico/medidas: quase tudo branco puro, sem cor, só linhas."""
    from PIL import ImageStat
    p = im.copy()
    p.thumbnail((240, 240))
    h = p.convert('L').histogram()
    n = sum(h) or 1
    branco = sum(h[240:]) / n
    escuro = sum(h[:150]) / (sum(h[:240]) or 1)  # linhas escuras (móvel branco só tem sombra clara)
    saturacao = ImageStat.Stat(p.convert('HSV').split()[1]).mean[0]
    return branco > 0.86 and saturacao < 6 and escuro > 0.2


def _parece_estudio(im):
    """Fundo liso e claro em volta (estúdio), não um ambiente decorado."""
    media, desvio, minimo = _borda(im)
    return minimo > 140 and desvio < 40  # ambiente decorado passa de ~60


def _recortar(im):
    """Tira o fundo (rembg) e põe o móvel no branco. None se não der
    (sem rembg, recorte vazio, ou foto de detalhe que encosta nas bordas)."""
    global _sessao
    try:
        from rembg import remove, new_session
    except Exception:
        return None
    from PIL import Image
    im.thumbnail((1200, 1200))
    with _trava:
        if _sessao is None:
            _sessao = new_session('isnet-general-use')
        out = remove(im, session=_sessao)
    alfa = out.split()[-1].point(lambda v: 255 if v > 128 else 0)
    caixa = alfa.getbbox()
    if not caixa:
        return None
    w, h = im.size
    l, t, rr, b = caixa
    encosta = sum([l <= 2, t <= 2, rr >= w - 2, b >= h - 2])
    area = sum(alfa.histogram()[255:]) / (w * h)
    if encosta >= 3 or area < 0.03:
        return None
    branco = Image.new('RGB', im.size, 'white')
    branco.paste(out, mask=out.split()[-1])
    f = int(max(rr - l, b - t) * 0.05)
    final = branco.crop((max(0, l - f), max(0, t - f), min(w, rr + f), min(h, b + f)))
    final.info['encosta'] = encosta
    final.info['largura'] = (rr - l) / max(1, b - t)
    return final


def foto_produto(r):
    """Escolhe a foto (só o móvel, inteiro), deixa o fundo branco, reduz
    e devolve como data URI. Resultado fica guardado em capturas/.fotos."""
    from io import BytesIO
    import hashlib
    candidatas = [u for u in (r.get('candidatas') or [r['imagem']]) if u]
    if not candidatas:
        return ''
    chave = hashlib.sha1(('|'.join(candidatas) + VERSAO_FOTOS).encode()).hexdigest()
    arq = os.path.join(PASTA_FOTOS, chave + '.jpg')
    if os.path.exists(arq):
        with open(arq, 'rb') as f:
            dados = f.read()
        r['cor'] = familia_cor(dados)
        return _embutir(dados)
    escolhida, primeira, recortes = None, None, []
    lista = candidatas[:10]
    for i, url in enumerate(lista):
        try:
            im = _abrir(_baixar_bytes(url))
        except Exception:
            continue
        primeira = primeira or im
        if _ja_branca(im) or _quase_branca(im):
            # fundo branco: só vale se ainda não há recorte bom de uma foto anterior
            # (as últimas fotos da IKEA costumam ser o desenho técnico) e se não é desenho
            if recortes or _eh_desenho(im):
                continue
            escolhida = cortar_sobra(im if _ja_branca(im) else _clarear(im))
            break
        ultima = i == len(lista) - 1
        if len(lista) > 1 and not _parece_estudio(im) and not (ultima and not recortes):
            continue  # foto de ambiente: tenta a próxima
        rec = _recortar(im)
        if rec is not None:
            recortes.append(rec)
            if len(recortes) >= 5 or len(lista) == 1:
                break
    if escolhida is None and recortes:
        # o móvel inteiro (sem encostar na borda), na ordem da loja (a 1ª costuma
        # ser a frontal); só pula as vistas bem mais estreitas (detalhe, lateral)
        inteiros = [x for x in recortes if x.info.get('encosta', 0) == 0] or recortes
        maior = max(x.info.get('largura', 0) for x in inteiros)
        escolhida = next(x for x in inteiros if x.info.get('largura', 0) >= 0.75 * maior)
    if escolhida is None:
        if primeira is None:
            return ''
        escolhida = enquadrar(primeira)  # último recurso: foto original
        r['conferir'].append('foto sem fundo branco')
    escolhida.thumbnail((900, 900))
    out = BytesIO()
    escolhida.save(out, 'JPEG', quality=84, optimize=True)
    dados = out.getvalue()
    os.makedirs(PASTA_FOTOS, exist_ok=True)
    with open(arq, 'wb') as f:
        f.write(dados)
    r['cor'] = familia_cor(dados)
    return _embutir(dados)


FAMILIAS_COR = ['branco', 'creme', 'bege', 'madeira clara', 'madeira média', 'madeira escura', 'cinza', 'preto',
                'verde', 'azul', 'rosa', 'vermelho', 'amarelo', 'outras']


def familia_cor(dados):
    """Família de cor do móvel (ignora o fundo branco), para ordenar a página:
    brancos, depois creme/bege, madeiras da clara à escura, cinzas, pretos e cores."""
    import colorsys
    from io import BytesIO
    from PIL import Image
    im = Image.open(BytesIO(dados)).convert('RGB')
    im.thumbnail((120, 120))
    px = [p for p in im.getdata() if min(p) < 236]  # sem o fundo branco
    if len(px) < 30:
        return 'branco'
    rr, gg, bb = (sum(c[i] for c in px) / len(px) for i in range(3))
    h, sat, v = colorsys.rgb_to_hsv(rr / 255, gg / 255, bb / 255)
    h *= 360
    if sat < 0.10:
        return 'branco' if v > 0.80 else ('cinza' if v > 0.38 else 'preto')
    if 15 <= h < 50:  # tons quentes: creme, bege e madeiras
        if sat < 0.22:
            return 'creme' if v > 0.80 else ('bege' if v > 0.62 else 'cinza')
        if v > 0.70:
            return 'bege' if sat < 0.35 else 'madeira clara'
        return 'madeira média' if v > 0.45 else 'madeira escura'
    if sat < 0.16:
        return 'branco' if v > 0.80 else ('cinza' if v > 0.38 else 'preto')
    if 50 <= h < 70:
        return 'amarelo'
    if 70 <= h < 170:
        return 'verde'
    if 170 <= h < 260:
        return 'azul'
    if 260 <= h < 340:
        return 'rosa'
    return 'vermelho' if v < 0.75 or sat > 0.5 else 'rosa'


def _embutir(dados, lado=720, qualidade=80):
    """Foto já tratada -> data URI leve para o PDF (o card tem ~8 cm)."""
    from io import BytesIO
    from PIL import Image
    im = Image.open(BytesIO(dados)).convert('RGB')
    im.thumbnail((lado, lado))
    out = BytesIO()
    im.save(out, 'JPEG', quality=qualidade, optimize=True, progressive=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(out.getvalue()).decode()


def baixar_imagem(url):
    if not url:
        return ''
    try:
        req = urllib.request.Request(url, headers={'User-Agent': cap.UA, 'Accept': 'image/avif,image/webp,image/*,*/*;q=0.8'})
        with urllib.request.urlopen(req, timeout=30) as r:
            dados = r.read()
            tipo = (r.headers.get_content_type() or mimetypes.guess_type(url)[0] or 'image/jpeg')
        if not tipo.startswith('image/'):
            return ''
        dados, tipo = reduzir(dados, tipo)
        return f'data:{tipo};base64,' + base64.b64encode(dados).decode()
    except Exception:
        return ''


def preparar(item, lojas, secao=''):
    r = cap.capturar(item['url'], lojas)
    x = item['extra']
    if x.get('nome'):
        r['nome_pdf'] = x['nome']
    else:
        r['nome_pdf'] = ''
    if x.get('loja'):
        r['loja'] = x['loja']
    if x.get('foto'):
        r['imagem'] = x['foto']
    if x.get('preco'):
        r['preco'] = cap.numero(x['preco'])
        r['faixaPreco'] = cap.faixa(r['preco'], r['regiao'])
    if x.get('faixa'):
        r['faixaPreco'] = int(x['faixa'])
    r['medidas'] = ''  # medidas não aparecem no PDF (decisão da curadoria)
    r['detalhe'] = x.get('detalhe', '')
    if x.get('foto'):
        # home24: a mesma foto existe maior no servidor (troca 500x500 por 1000x1000)
        foto = re.sub(r'(home24\.net/images/media/catalog/product/)\d+x\d+/', r'\g<1>1000x1000/', x['foto'])
        r['candidatas'] = [foto]
        if x.get('preco'):  # loja bloqueada, mas você completou foto e preço: nada a conferir
            r['conferir'] = [c for c in r['conferir'] if not c.startswith('não abriu') and c != 'sem preço']
    try:
        r['img64'] = foto_produto(r)
    except Exception:
        r['img64'] = baixar_imagem(r['imagem'])
    if r['imagem'] and not r['img64']:
        r['conferir'].append('foto não baixou')
    return r


# --------------------------------------------------------- páginas
def categoria_oficial(texto):
    """'mesa lateral' / 'Mesas laterais' -> 'Mesa lateral' (ou o texto como veio)."""
    t = cap.sem_acento(texto).strip()
    for c in ORDEM:
        if cap.sem_acento(c) == t:
            return c
    for c in ORDEM:  # plural simples: "Cadeiras", "Sofás", "Mesas de jantar"
        if re.sub(r's\b', '', t) == re.sub(r's\b', '', cap.sem_acento(c)):
            return c
    return texto.strip()


SUB_INFANTIL = [  # a 1ª que bater vence
    ('Camas', ['bett', 'bettgest', 'bettgestell', 'kinderbett', 'babybett', 'cama', 'berco', 'bed', 'lit', 'cuna']),
    ('Escrivaninhas', ['schreibtisch', 'escrivaninha', 'desk', 'bureau', 'escritorio']),
    ('Mesas & Cadeiras', ['tisch', 'kindertisch', 'stuhl', 'kinderstuhl', 'hocker', 'kinderhocker', 'pouf', 'puff', 'sessel',
                          'mesa', 'cadeira', 'banqueta', 'banco', 'poltrona', 'table', 'chair', 'stool', 'silla', 'chaise']),
    ('Organização', ['aufbewahrung', 'regal', 'box', 'boxen', 'kasten', 'schrank', 'kommode', 'organizacao', 'estante',
                     'armario', 'bau', 'storage', 'shelf']),
    ('Almofadas & Tapetes', ['kissen', 'teppich', 'decke', 'almofada', 'tapete', 'manta', 'cushion', 'pillow', 'rug',
                             'blanket', 'coussin', 'tapis']),
]


def sub_infantil(r):
    """Subpágina de Infantil pelo nome/link (sem achar: Decoração)."""
    t = ' ' + cap.sem_acento(r['nome'] + ' ' + r['link']).replace('-', ' ').replace('/', ' ').replace('.', ' ') + ' '
    for sub, palavras in SUB_INFANTIL:
        if any(re.search(r'(?<![a-z])' + re.escape(p) + r'(?![a-z])', t) for p in palavras):
            return sub
    return 'Decoração'


def agrupar(todos, res):
    """Cada produto vai para a página da sua categoria. Vale, nesta ordem:
    '| categoria: X' > '# Título' da lista > categoria detectada."""
    paginas = {}
    for (s, it), r in zip(todos, res):
        escolhida = it['extra'].get('categoria') or s['titulo'] or r['categoria']
        if escolhida:
            titulo = categoria_oficial(escolhida)
            if it['extra'].get('categoria') or s['titulo']:
                r['conferir'] = [c for c in r['conferir'] if not c.startswith('categoria')]
        else:
            titulo = OUTROS
        if titulo == 'Infantil':
            titulo = 'Infantil · ' + sub_infantil(r)
        paginas.setdefault(titulo, []).append(r)
        r['nome_pdf'] = it['extra'].get('nome') or r.get('modelo') or nome_curto(r['nome'], titulo)
        if titulo in COM_MEDIDAS:
            r['medidas'] = it['extra'].get('medidas') or medidas_do_nome(r['nome'])

    # mesmo modelo em cores/tecidos/tamanhos diferentes: acrescenta o que
    # muda entre eles ("Nymane · 4 Spots", "Ramnefjäll · Idekulla beige")
    for prods in paginas.values():
        for nome in {r['nome_pdf'] for r in prods}:
            iguais = [r for r in prods if r['nome_pdf'] == nome]
            if len(iguais) > 1:
                difs = diferencas([r['nome'] for r in iguais])
                if not any(difs) and len({r['nome'] for r in iguais}) > 1:
                    # só o tamanho muda (e medidas não aparecem): versão menor/maior
                    por_tamanho = sorted(iguais, key=lambda r: tamanho(r['nome']))
                    rotulos = ['versão menor'] + ['versão intermediária'] * (len(iguais) - 2) + ['versão maior']
                    for r, rot in zip(por_tamanho, rotulos):
                        r['nome_pdf'] = f'{nome} · {rot}'
                    continue
                trad = [traduzir(v) for v in difs]
                for r, v in zip(iguais, difs):
                    # sem palavra própria (ex.: a versão "padrão"): usa a própria cor/acabamento
                    v = traduzir(v or variacao(r['nome']))
                    # "armário" ao lado de "armário pinho claro": acrescenta a própria cor
                    if v and any(o != v and o.startswith(v + ' ') for o in trad):
                        v = traduzir(v + ' ' + variacao(r['nome']))
                    if len(v) > 48:
                        v = v[:48].rsplit(' ', 1)[0]
                    if v:
                        r['nome_pdf'] = f'{nome} · {v}'
                # ainda iguais entre si (só o tamanho muda): versão menor/maior
                for n2 in {r['nome_pdf'] for r in iguais}:
                    gemeos = sorted([r for r in iguais if r['nome_pdf'] == n2], key=lambda r: tamanho(r['nome']))
                    if len(gemeos) > 1:
                        rotulos = ['versão menor'] + ['versão intermediária'] * (len(gemeos) - 2) + ['versão maior']
                        for r, rot in zip(gemeos, rotulos):
                            r['nome_pdf'] = f'{n2} · {rot}'

    # ordem visual na página: por cor (brancos, beges, madeiras claras → escuras,
    # cinzas, pretos, cores); dentro da mesma cor, variações do mesmo modelo juntas
    for t, prods in paginas.items():
        primeira = {}
        for i, r in enumerate(prods):
            primeira.setdefault(r['nome_pdf'].split(' · ')[0], i)
        ordem_cor = lambda r: FAMILIAS_COR.index(r['cor']) if r.get('cor') in FAMILIAS_COR else 99
        prods.sort(key=lambda r: (ordem_cor(r), primeira[r['nome_pdf'].split(' · ')[0]]))

    def ordem(t):
        if t in ORDEM:
            return (0, ORDEM.index(t))
        return (2, 0) if t == OUTROS else (1, 0)
    return [{'titulo': t, 'prod': paginas[t]} for t in sorted(paginas, key=ordem)]


# ------------------------------------------------------------- HTML
def fontes_embutidas():
    """Embute Cormorant Garamond e Jost (ferramentas/fontes) no próprio HTML."""
    pasta = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fontes')
    with open(os.path.join(pasta, 'fontes.css'), encoding='utf-8') as f:
        css = f.read()

    def troca(m):
        with open(os.path.join(pasta, m.group(1)), 'rb') as f:
            return 'url(data:font/woff2;base64,' + base64.b64encode(f.read()).decode() + ')'
    return re.sub(r'url\(([^)]+\.woff2)\)', troca, css)


CSS = """
@page { size: A4 portrait; margin: 0; }
:root { --tinta:#2B2723; --suave:#8C8379; --linha:#DCD5CB; --bronze:#9A7B4F; }
* { box-sizing: border-box; }
html, body { margin: 0; background: #fff; color: var(--tinta); }
body { font-family: 'Jost', 'Helvetica Neue', Arial, sans-serif; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.pagina { width: 210mm; height: 297mm; padding: 14mm 16mm 12mm; position: relative;
  display: flex; flex-direction: column; page-break-after: always; break-after: page; overflow: hidden; background:#fff; }
.pagina:last-child { page-break-after: auto; break-after: auto; }
.topo, .rodape { display: flex; justify-content: space-between; font-size: 7pt;
  letter-spacing: .22em; text-transform: uppercase; color: var(--suave); }
.topo { padding-bottom: 2.6mm; border-bottom: .25mm solid var(--linha); }
.rodape { margin-top: auto; padding-top: 2.6mm; border-top: .25mm solid var(--linha); }
h1 { font-family: 'EB Garamond', Georgia, serif; font-weight: 400; font-size: 28pt;
  letter-spacing: .01em; text-align: center; margin: 8mm 0 7mm; }
.grupo { text-align: center; font-size: 7.5pt; letter-spacing: .32em; text-transform: uppercase;
  color: var(--bronze); margin: 7mm 0 0; }
h1.sub { margin-top: 2mm; }
.grade { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); grid-template-rows: repeat(3, minmax(0, 1fr));
  gap: 6mm 7mm; flex: 1; min-height: 0; margin-bottom: 5mm; }
.card { border: .25mm solid var(--linha); display: flex; flex-direction: column; min-height: 0;
  text-decoration: none; color: inherit; }
.foto { flex: 1; min-height: 0; display: flex; align-items: center; justify-content: center;
  padding: 5mm 8mm; border-bottom: .25mm solid var(--linha); }
.foto img { max-width: 100%; max-height: 100%; object-fit: contain; }
.foto .vazio { font-size: 7pt; letter-spacing: .2em; color: var(--suave); text-transform: uppercase; }
.legenda { padding: 3mm 4mm 3.4mm; text-align: center; }
.nome { font-family: 'Cormorant Garamond', Georgia, serif; font-style: italic; font-weight: 500;
  font-size: 15pt; line-height: 1.1; margin: 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.loja { font-size: 7pt; letter-spacing: .2em; text-transform: uppercase; margin: 1.1mm 0 0; }
.meta { font-size: 7.4pt; letter-spacing: .08em; color: var(--suave); margin: 1mm 0 0; }
.meta b { color: var(--bronze); font-weight: 500; letter-spacing: .12em; }
/* capa e sumário */
.capa { justify-content: center; align-items: center; text-align: center; }
.capa .sobre { font-size: 7.5pt; letter-spacing: .4em; text-transform: uppercase; color: var(--suave); }
.capa h2 { font-family: 'EB Garamond', Georgia, serif; font-weight: 400; font-size: 40pt;
  margin: 7mm 0 4mm; letter-spacing: .01em; }
.capa .fio { width: 22mm; height: .3mm; background: var(--bronze); margin: 2mm auto 6mm; }
.capa .sub { font-family: 'Cormorant Garamond', Georgia, serif; font-style: italic; font-size: 14pt; color: var(--suave); }
.capa .assina { position: absolute; bottom: 14mm; left: 0; right: 0; font-size: 7pt;
  letter-spacing: .32em; text-transform: uppercase; color: var(--suave); }
.sumario { width: 100%; margin: 2mm auto 0; column-count: 2; column-gap: 12mm; column-fill: auto; height: 225mm; }
.sumario a { display: flex; align-items: baseline; gap: 3mm; text-decoration: none; color: inherit;
  padding: 1.6mm 0; border-bottom: .25mm solid var(--linha); break-inside: avoid;
  font-family: 'EB Garamond', Georgia, serif; font-size: 12pt; }
.sumario a.subitem { padding-left: 4mm; font-size: 11pt; }
.sumario .grupo-sum { break-inside: avoid; break-after: avoid; margin: 3mm 0 0; padding: 1.6mm 0 1mm;
  font-family: 'Jost', sans-serif; font-size: 6.8pt; letter-spacing: .28em; text-transform: uppercase; color: var(--bronze); }
.sumario a span:last-child { margin-left: auto; font-family: 'Jost', sans-serif; font-size: 7pt;
  letter-spacing: .2em; color: var(--suave); }
"""


def fmt_valor(r):
    if not r['preco']:
        return ''
    s = f"{r['preco']:,.0f}".replace(',', '.')
    return f"{MOEDA.get((r['moeda'] or '').upper(), SIMB.get(r['regiao'], '€'))} {s}"


def card(r, mostrar_valor):
    e = html.escape
    foto = (f'<img src="{r["img64"]}" alt="">' if r['img64']
            else '<span class="vazio">sem foto</span>')
    meta = []
    if r['faixaPreco']:
        meta.append(f'<b>{e(SIMB.get(r["regiao"], "€") * int(r["faixaPreco"]))}</b>')
    if mostrar_valor and fmt_valor(r):
        meta.append(e('≈ ' + fmt_valor(r)))
    if r['medidas']:
        meta.append(e(r['medidas']))
    if r['detalhe']:
        meta.append(e(r['detalhe']))
    return (f'<a class="card" href="{e(r["link"])}">'
            f'<div class="foto">{foto}</div>'
            f'<div class="legenda"><p class="nome">{e(r["nome_pdf"] or "—")}</p>'
            f'<p class="loja">{e(r["loja"])}</p>'
            + (f'<p class="meta">{" &nbsp;·&nbsp; ".join(meta)}</p>' if meta else '')
            + '</div></a>')


WEB_CSS = """
/* Layout: catálogo em coluna, índice de categorias no topo, cards 2-4 por linha */
:root { --papel:#FFFFFF; --tinta:#2B2723; --suave:#857C72; --linha:#E2DBD1; --bronze:#94744A; --chip:#F6F2EC;
  --display:'EB Garamond', Georgia, serif; --nome:'Cormorant Garamond', Georgia, serif; --util:'Jost', 'Helvetica Neue', Arial, sans-serif; }
body { background: var(--papel); color: var(--tinta); font-family: var(--util); }
.wrap { max-width: 1080px; margin: 0 auto; padding-inline: 16px; padding-block: 28px 56px; }
.topo { text-align: center; padding-block: 12px 20px; border-bottom: 1px solid var(--linha); }
.topo .sobre { font-size: 11px; letter-spacing: .32em; text-transform: uppercase; color: var(--suave); margin: 0; }
.topo h1 { font-family: var(--display); font-weight: 400; font-size: clamp(30px, 7vw, 46px); margin: 10px 0 6px; text-wrap: balance; }
.topo .conta { font-size: 12px; letter-spacing: .12em; color: var(--suave); margin: 0; font-variant-numeric: tabular-nums; }
nav.indice { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; padding-block: 18px; }
nav.indice a { font-size: 12px; letter-spacing: .04em; color: var(--tinta); text-decoration: none; background: var(--chip);
  border: 1px solid var(--linha); border-radius: 999px; padding: 6px 12px; }
nav.indice a:focus-visible, .card:focus-visible { outline: 2px solid var(--bronze); outline-offset: 2px; }
section.cat { padding-block: 28px 8px; scroll-margin-top: 12px; }
.cat .grupo { text-align: center; font-size: 11px; letter-spacing: .3em; text-transform: uppercase; color: var(--bronze); margin: 0 0 4px; }
.cat h2 { font-family: var(--display); font-weight: 400; font-size: clamp(26px, 6vw, 34px); text-align: center; margin: 0 0 18px; }
.grade { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.card { display: flex; flex-direction: column; min-width: 0; border: 1px solid var(--linha); color: inherit; text-decoration: none; background: var(--papel); }
.card .foto { aspect-ratio: 4 / 3; max-width: 100%; display: flex; align-items: center; justify-content: center; padding: 10px;
  border-bottom: 1px solid var(--linha); overflow: hidden; }
.card .foto img { width: 100%; height: 100%; object-fit: contain; }
.card .legenda { margin-top: auto; }
.card .legenda { padding: 10px 8px 12px; text-align: center; }
.card .nome { font-family: var(--nome); font-style: italic; font-weight: 500; font-size: 18px; line-height: 1.15; margin: 0; text-wrap: balance; }
.card .loja { font-size: 10px; letter-spacing: .2em; text-transform: uppercase; margin: 6px 0 0; }
.card .meta { font-size: 11px; color: var(--suave); margin: 4px 0 0; }
.card .meta b { color: var(--bronze); font-weight: 500; letter-spacing: .1em; }
.vazio { font-size: 11px; color: var(--suave); }
@media (min-width: 720px) { .grade { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; } }
"""


def montar_web(secoes, titulo, assinatura, mostrar_valor):
    """Prévia para ver no celular: mesmo conteúdo do PDF, em coluna responsiva."""
    e = html.escape
    total = sum(len(s['prod']) for s in secoes)
    indice, blocos = [], []
    for i, s in enumerate(secoes, 1):
        t = exibir(s['titulo'])
        grupo, nome = (t.split(' · ', 1) if ' · ' in t else ('', t))
        ancora = f'c{i}'
        indice.append(f'<a href="#{ancora}">{e((grupo + " — " if grupo else "") + nome)}</a>')
        cards = ''.join(card(r, mostrar_valor) for r in s['prod'])
        blocos.append(f'<section class="cat" id="{ancora}">'
                      + (f'<p class="grupo">{e(grupo)}</p>' if grupo else '')
                      + f'<h2>{e(nome)}</h2><div class="grade">{cards}</div></section>')
    return (f'<title>{e(titulo)}</title>\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@1,500'
            '&family=EB+Garamond&family=Jost:wght@400;500&display=swap" rel="stylesheet">\n'
            f'<style>{WEB_CSS}</style>\n'
            f'<div class="wrap"><header class="topo"><p class="sobre">{e(assinatura)}</p>'
            f'<h1>{e(titulo)}</h1><p class="conta">{total} peças · {len(secoes)} categorias</p></header>'
            f'<nav class="indice">{"".join(indice)}</nav>{"".join(blocos)}</div>')


def titulo_pagina(t):
    """'Decoração · Cestos' -> 'Cestos' com 'Decoração' pequeno em cima."""
    e = html.escape
    if ' · ' in t:
        grupo, sub = t.split(' · ', 1)
        return f'<p class="grupo">{e(grupo)}</p><h1 class="sub">{e(sub)}</h1>'
    return f'<h1>{e(t)}</h1>'


def montar_html(secoes, titulo, subtitulo, assinatura, mostrar_valor):
    e = html.escape
    paginas, sumario = [], []
    n = 3  # 1 = capa, 2 = sumário
    for s in secoes:
        blocos = [s['prod'][i:i + POR_PAGINA] for i in range(0, len(s['prod']), POR_PAGINA)] or [[]]
        s['ancora'] = 'sec-' + str(len(sumario) + 1)
        sumario.append((exibir(s['titulo']), n, s['ancora']))
        for j, bloco in enumerate(blocos):
            cards = ''.join(card(r, mostrar_valor) for r in bloco)
            ident = f' id="{s["ancora"]}"' if j == 0 else ''
            paginas.append(f'''
<section class="pagina"{ident}>
  <div class="topo"><span>{e(assinatura)}</span><span>{e(titulo)}</span></div>
  {titulo_pagina(exibir(s["titulo"]))}
  <div class="grade">{cards}</div>
  <div class="rodape"><span>{e(exibir(s["titulo"]).replace(" · ", " — "))}</span><span>{n}</span></div>
</section>''')
            n += 1

    capa = f'''
<section class="pagina capa">
  <p class="sobre">Seleção</p>
  <h2>{e(titulo)}</h2>
  <div class="fio"></div>
  <p class="sub">{e(subtitulo)}</p>
  <p class="assina">{e(assinatura)}</p>
</section>'''
    itens, grupo_atual = [], None
    for t, p, a in sumario:
        if ' · ' in t:  # subcategoria: o grupo aparece uma vez, as subs embaixo
            grupo, sub = t.split(' · ', 1)
            if grupo != grupo_atual:
                itens.append(f'<p class="grupo-sum">{e(grupo)}</p>')
                grupo_atual = grupo
            itens.append(f'<a class="subitem" href="#{a}"><span>{e(sub)}</span><span>{p}</span></a>')
        else:
            grupo_atual = t  # subs deste grupo logo abaixo entram sem repetir o nome
            itens.append(f'<a href="#{a}"><span>{e(t)}</span><span>{p}</span></a>')
    itens = ''.join(itens)
    pag_sumario = f'''
<section class="pagina">
  <div class="topo"><span>{e(assinatura)}</span><span>{e(titulo)}</span></div>
  <h1>Sumário</h1>
  <nav class="sumario">{itens}</nav>
  <div class="rodape"><span>Sumário</span><span>2</span></div>
</section>'''

    return f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>{e(titulo)}</title>
<style>{fontes_embutidas()}{CSS}</style></head>
<body>{capa}{pag_sumario}{''.join(paginas)}</body></html>'''


# ------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description='Monta o PDF da curadoria a partir de uma lista de links.')
    ap.add_argument('lista')
    ap.add_argument('--titulo', default='Curadoria de Interiores')
    ap.add_argument('--subtitulo', default='Peças escolhidas uma a uma')
    ap.add_argument('--assinatura', default='Gabriele Pinheiro')
    ap.add_argument('--com-valor', action='store_true', help='além da faixa (€€), mostra o valor aproximado')
    ap.add_argument('--saida', default=None)
    a = ap.parse_args()

    secoes = ler_lista(a.lista)
    total = sum(len(s['itens']) for s in secoes)
    if not total:
        sys.exit('Nenhum link na lista.')
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    saida = a.saida or os.path.join(raiz, 'capturas', dt.datetime.now().strftime('%Y-%m-%d-%H%M'))
    os.makedirs(saida, exist_ok=True)

    lojas = cap.carregar_lojas()
    todos = [(s, it) for s in secoes for it in s['itens']]
    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(lambda p: preparar(p[1], lojas, p[0]['titulo']), todos))
    # fora do PDF: links de lista/categoria e produtos repetidos
    # (mesmo produto com links diferentes: mesma loja + mesmo nome ou foto)
    fora, ja = [], {}
    filtrados = []
    for par, r in zip(todos, res):
        if r.get('eh_lista'):
            fora.append(f"link de lista, não de produto: {r['link']}")
            continue
        if not r.get('img64'):
            # card sem foto não entra no catálogo: completar com "| foto: link | preco: valor"
            fora.append(f"sem foto (loja bloqueou ou não publicou): {r['link']}")
            continue
        # repetido = o MESMO produto: mesmo código da loja, ou mesmo nome
        # completo E mesma foto. Outra cor/tecido/tamanho não é repetido.
        chaves = [k for k in ((r['loja'], 'ref', r['referencia']) if r['referencia'] else None,
                              (r['loja'], cap.sem_acento(r['nome']), r['imagem']) if r['nome'] and r['imagem'] else None) if k]
        dup = next((ja[k] for k in chaves if k in ja), None)
        if dup:
            fora.append(f"repetido: {r['link']}  (igual a {dup})")
            continue
        for k in chaves:
            ja[k] = r['link']
        filtrados.append((par, r))
    fora += [f'link repetido na lista: {u}' for u in REPETIDOS]
    secoes = agrupar([p for p, _ in filtrados], [r for _, r in filtrados])
    total = len(filtrados)
    for f_ in fora:
        print('✗ fora do PDF —', f_)

    avisos = []
    for s in secoes:
        for r in s['prod']:
            ok = '✓' if not r['conferir'] else '!'
            print(f"{ok} [{s['titulo']}] {r['loja']} · {r['nome_pdf'] or '(sem nome)'} · {fmt_valor(r) or '—'}")
            if r['conferir']:
                avisos.append(f"[{s['titulo']}] {r['link']}\n    falta: {', '.join(r['conferir'])}")

    pagina = montar_html(secoes, a.titulo, a.subtitulo, a.assinatura, a.com_valor)
    with open(os.path.join(saida, 'previa-web.html'), 'w', encoding='utf-8') as f:
        f.write(montar_web(secoes, a.titulo, a.assinatura, a.com_valor))
    arq_html = os.path.join(saida, 'curadoria.html')
    with open(arq_html, 'w', encoding='utf-8') as f:
        f.write(pagina)
    with open(os.path.join(saida, 'conferir.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(avisos + [''] + ['FORA DO PDF: ' + x for x in fora]).strip() or 'Tudo completo.')
    arq_pdf = os.path.join(saida, 'curadoria.pdf')
    subprocess.run(['node', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pdf.mjs'), arq_html, arq_pdf], check=True)
    print(f'\n{total} produtos · {len(avisos)} para conferir\nPDF: {arq_pdf}')


if __name__ == '__main__':
    main()
