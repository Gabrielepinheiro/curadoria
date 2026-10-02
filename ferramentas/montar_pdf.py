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
import mimetypes
import os
import re
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capturar as cap  # noqa: E402

POR_PAGINA = 6
# Ordem das páginas — a mesma de CATEGORIES em assets/config.js.
ORDEM = [
    'Aparador & Buffet', 'Banco & Banqueta', 'Cadeira', 'Cadeira de escritório',
    'Cama', 'Cômoda', 'Escrivaninha', 'Estante', 'Mesa de cabeceira',
    'Mesa de centro', 'Mesa de jantar', 'Mesa lateral', 'Poltrona', 'Puff', 'Sofá',
    'Área externa', 'Cortina', 'Decoração', 'Espelho', 'Iluminação',
    'Papel de parede', 'Quadros & Arte', 'Roupa de cama & Têxtil', 'Tapete',
]
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
            m = re.match(r'(https?://\S+)(.*)$', linha)
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


def medidas_do_nome(nome):
    """'... 160x200 cm' -> '160 × 200 cm'"""
    m = MEDIDA.search(nome or '')
    return ' × '.join(g for g in m.groups() if g) + ' cm' if m else ''


def variacao(nome):
    """'RAMNEFJÄLL Bettgestell - Idekulla beige/Luröy 160x200 cm' -> 'Idekulla beige'"""
    partes = re.split(r'\s+[-–—]\s+', nome or '', maxsplit=1)
    if len(partes) < 2:
        return ''
    v = MEDIDA.sub('', partes[1]).split('/')[0].split(',')[0].strip()
    return v[:24]


def nome_curto(nome, secao=''):
    """Nome de vitrine, sem repetir a categoria da página:
    'STRANDMON Poltrona - Talliden bege' -> 'Strandmon'
    'Poltrona Beegees Suede Preta' (seção Poltronas) -> 'Beegees Suede Preta'"""
    n = re.split(r'\s+[-–—|]\s+|,\s', nome or '')[0].strip()
    palavras = n.split()
    # padrão IKEA: MODELO EM MAIÚSCULAS + descrição -> só o modelo
    caps = []
    for w in palavras:
        if len(w) >= 2 and w.isupper() and any(c.isalpha() for c in w):
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
    fundo = cinza.getpixel((0, 0))
    if fundo < 225:  # foto de ambiente, não fundo claro: não mexe
        return im
    dif = ImageChops.difference(cinza, Image.new('L', im.size, fundo)).point(lambda v: 255 if v > 14 else 0)
    caixa = dif.getbbox()
    if not caixa:
        return im
    l, t, r, b = caixa
    f = int(max(r - l, b - t) * folga)
    l, t, r, b = max(0, l - f), max(0, t - f), min(im.width, r + f), min(im.height, b + f)
    novo = Image.new('RGB', (r - l, b - t), (fundo,) * 3)
    novo.paste(im.crop((l, t, r, b)))
    return novo


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
        im = cortar_sobra(im)
        out = BytesIO()
        im.save(out, 'JPEG', quality=84, optimize=True)
        return out.getvalue(), 'image/jpeg'
    except Exception:
        return dados, tipo


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
    r['medidas'] = x.get('medidas') or medidas_do_nome(r['nome'])
    r['detalhe'] = x.get('detalhe', '')
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
        paginas.setdefault(titulo, []).append(r)
        r['nome_pdf'] = it['extra'].get('nome') or nome_curto(r['nome'], titulo)

    # mesmo modelo em cores/tecidos diferentes: acrescenta a variação
    for prods in paginas.values():
        for nome in {r['nome_pdf'] for r in prods}:
            iguais = [r for r in prods if r['nome_pdf'] == nome]
            if len(iguais) > 1:
                for r in iguais:
                    v = variacao(r['nome'])
                    if v:
                        r['nome_pdf'] = f'{nome} · {v}'

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
h1 { font-family: 'Cormorant Garamond', Georgia, serif; font-weight: 500; font-size: 30pt;
  letter-spacing: .01em; text-align: center; margin: 8mm 0 7mm; }
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
  font-size: 15pt; line-height: 1.1; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.loja { font-size: 7pt; letter-spacing: .2em; text-transform: uppercase; margin: 1.1mm 0 0; }
.meta { font-size: 7.4pt; letter-spacing: .08em; color: var(--suave); margin: 1mm 0 0; }
.meta b { color: var(--bronze); font-weight: 500; letter-spacing: .12em; }
/* capa e sumário */
.capa { justify-content: center; align-items: center; text-align: center; }
.capa .sobre { font-size: 7.5pt; letter-spacing: .4em; text-transform: uppercase; color: var(--suave); }
.capa h2 { font-family: 'Cormorant Garamond', Georgia, serif; font-weight: 400; font-size: 44pt;
  margin: 7mm 0 4mm; letter-spacing: .01em; }
.capa .fio { width: 22mm; height: .3mm; background: var(--bronze); margin: 2mm auto 6mm; }
.capa .sub { font-family: 'Cormorant Garamond', Georgia, serif; font-style: italic; font-size: 14pt; color: var(--suave); }
.capa .assina { position: absolute; bottom: 14mm; left: 0; right: 0; font-size: 7pt;
  letter-spacing: .32em; text-transform: uppercase; color: var(--suave); }
.sumario { width: 130mm; margin: 4mm auto 0; }
.sumario a { display: flex; align-items: baseline; gap: 3mm; text-decoration: none; color: inherit;
  padding: 2.2mm 0; border-bottom: .25mm solid var(--linha); break-inside: avoid;
  font-family: 'Cormorant Garamond', Georgia, serif; font-size: 13.5pt; }
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


def montar_html(secoes, titulo, subtitulo, assinatura, mostrar_valor):
    e = html.escape
    paginas, sumario = [], []
    n = 3  # 1 = capa, 2 = sumário
    for s in secoes:
        blocos = [s['prod'][i:i + POR_PAGINA] for i in range(0, len(s['prod']), POR_PAGINA)] or [[]]
        s['ancora'] = 'sec-' + str(len(sumario) + 1)
        sumario.append((s['titulo'], n, s['ancora']))
        for j, bloco in enumerate(blocos):
            cards = ''.join(card(r, mostrar_valor) for r in bloco)
            ident = f' id="{s["ancora"]}"' if j == 0 else ''
            paginas.append(f'''
<section class="pagina"{ident}>
  <div class="topo"><span>{e(assinatura)}</span><span>{e(titulo)}</span></div>
  <h1>{e(s["titulo"])}</h1>
  <div class="grade">{cards}</div>
  <div class="rodape"><span>{e(s["titulo"])}</span><span>{n}</span></div>
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
    itens = ''.join(f'<a href="#{a}"><span>{e(t)}</span><span>{p}</span></a>' for t, p, a in sumario)
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
        chaves = [k for k in ((r['loja'], cap.sem_acento(r['nome'])) if r['nome'] else None,
                              ('img', r['imagem']) if r['imagem'] else None) if k]
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
