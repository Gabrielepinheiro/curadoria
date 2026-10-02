#!/usr/bin/env python3
# =============================================================
#  verificar_links.py  —  Confere TODOS os links do PDF antes de vender.
#
#  1. No PDF: cada produto tem um link clicável, na página certa,
#     apontando para a página DAQUELE produto (compara com produtos.json).
#  2. Na loja: cada link abre (sem erro), continua sendo a página de um
#     produto (não foi retirado nem redireciona para uma lista).
#  3. Sumário: cada item leva para a página certa do PDF.
#
#  Lojas que bloqueiam robôs (Maisons du Monde, home24…) não deixam
#  abrir a página daqui: para elas confere-se o link (formato, código
#  do produto batendo com o da foto) e o relatório pede uma checagem
#  manual rápida.
#
#  USO: python3 ferramentas/verificar_links.py capturas/<pasta>
#  (a pasta onde o montar_pdf.py gerou curadoria.pdf e produtos.json)
# =============================================================

import json
import os
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capturar as cap  # noqa: E402

BLOQUEIAM = ('maisonsdumonde.', 'home24.', 'hm.com')


def links_do_pdf(arq):
    """{página (1..n): [uri, ...]} e {página: [página destino, ...]} (links internos)."""
    from pypdf import PdfReader
    leitor = PdfReader(arq)
    idx = {p.indirect_reference.idnum: i + 1 for i, p in enumerate(leitor.pages)}
    externos, internos = {}, {}
    for n, pag in enumerate(leitor.pages, 1):
        for a in pag.get('/Annots') or []:
            a = a.get_object()
            if a.get('/Subtype') != '/Link':
                continue
            r = [float(x) for x in a.get('/Rect', [0, 0, 0, 0])]
            if abs(r[2] - r[0]) < 5 or abs(r[3] - r[1]) < 5:
                continue  # área clicável vazia não conta
            acao = a.get('/A')
            acao = acao.get_object() if acao else {}
            if acao.get('/URI'):
                externos.setdefault(n, []).append(str(acao['/URI']))
                continue
            dest = a.get('/Dest') or acao.get('/D')
            if dest is not None:
                if isinstance(dest, str) or hasattr(dest, 'startswith'):
                    nomeados = leitor.named_destinations
                    d = nomeados.get(str(dest))
                    alvo = leitor.get_destination_page_number(d) + 1 if d is not None else None
                else:
                    dest = dest.get_object() if hasattr(dest, 'get_object') else dest
                    alvo = idx.get(dest[0].idnum) if len(dest) else None
                internos.setdefault(n, []).append(alvo)
    return externos, internos


def checar_na_loja(link):
    """('ok'|'quebrado'|'retirado'|'bloqueado', detalhe)"""
    dom = urlparse(link).netloc
    if any(b in dom for b in BLOQUEIAM):
        return 'bloqueado', 'loja bloqueia acesso automático'
    try:
        final, pagina = cap.baixar(link, timeout=30)
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            return 'bloqueado', f'loja recusou o robô ({e.code})'
        return 'quebrado', f'erro {e.code}'
    except Exception as e:
        return 'quebrado', f'não abriu ({e.__class__.__name__})'
    p_orig, p_final = urlparse(link).path.rstrip('/'), urlparse(final).path.rstrip('/')
    if 'ikea.' in dom and '/p/' not in p_final:
        return 'retirado', f'a IKEA redireciona para {p_final} (produto saiu de linha?)'
    if p_orig != p_final and not p_final.endswith(p_orig.split('/')[-1]):
        return 'retirado', f'redireciona para {final}'
    leitor = cap.Leitor()
    try:
        leitor.feed(pagina)
    except Exception:
        pass
    if not any(cap.eh_tipo(o, 'Product') or cap.eh_tipo(o, 'ProductGroup') for o in cap.nos_jsonld(leitor.jsonld)) \
            and 'product' not in (leitor.meta.get('og:type') or ''):
        return 'retirado', 'a página abriu, mas não é mais a página de um produto'
    return 'ok', ''


def coerencia_bloqueado(p):
    """Para loja bloqueada: o código do produto no link bate com o da foto?"""
    m = re.search(r'-(M\d{6,})\.htm', p['link'])
    if m and p.get('foto'):
        return 'código do link e da foto conferem' if m.group(1) in p['foto'] else \
            f'ATENÇÃO: a foto não é do produto {m.group(1)}'
    return ''


def main():
    pasta = sys.argv[1] if len(sys.argv) > 1 else '.'
    prods = json.load(open(os.path.join(pasta, 'produtos.json'), encoding='utf-8'))
    sumario = json.load(open(os.path.join(pasta, 'sumario.json'), encoding='utf-8'))
    externos, internos = links_do_pdf(os.path.join(pasta, 'curadoria.pdf'))
    problemas, avisos = [], []

    # 1) cada produto: link clicável na página certa, apontando para ele
    por_pagina = {}
    for p in prods:
        por_pagina.setdefault(p['pagina'], []).append(p)
    for pag, lista in sorted(por_pagina.items()):
        achados = list(externos.get(pag, []))
        for p in lista:
            if p['link'] in achados:
                achados.remove(p['link'])
            else:
                problemas.append(f"pág. {pag} · {p['nome']}: sem link clicável para {p['link']}")
        for sobra in achados:
            problemas.append(f'pág. {pag}: link que não é de nenhum produto da página: {sobra}')
    total_links = sum(len(v) for v in externos.values())

    # 3) sumário
    destinos = [d for v in internos.values() for d in v]
    for titulo, pag in sumario:
        if pag not in destinos:
            problemas.append(f'sumário: "{titulo}" não leva para a página {pag}')

    # 2) na loja
    unicos = list(dict.fromkeys(p['link'] for p in prods))
    with ThreadPoolExecutor(max_workers=6) as ex:
        res = dict(zip(unicos, ex.map(checar_na_loja, unicos)))
    ok = bloq = 0
    for p in prods:
        estado, det = res[p['link']]
        if estado == 'ok':
            ok += 1
        elif estado == 'bloqueado':
            bloq += 1
            c = coerencia_bloqueado(p)
            (problemas if c.startswith('ATENÇÃO') else avisos).append(
                f"{p['loja']} · {p['nome']} (pág. {p['pagina']}): {det}. Conferir à mão: {p['link']}"
                + (f' ({c})' if c else ''))
        else:
            problemas.append(f"{p['loja']} · {p['nome']} (pág. {p['pagina']}): {det} → {p['link']}")

    linhas = [
        f'Produtos no PDF: {len(prods)} · links clicáveis encontrados: {total_links}',
        f'Sumário: {len(sumario)} itens · links internos: {len(destinos)}',
        f'Abrem certinho na loja: {ok} · lojas que bloqueiam robô (conferir à mão): {bloq}',
        '',
        'PROBLEMAS:' if problemas else 'PROBLEMAS: nenhum',
        *[f'  ✗ {x}' for x in problemas],
        '',
        'CONFERIR À MÃO (loja não deixa o robô abrir):' if avisos else '',
        *[f'  · {x}' for x in avisos],
    ]
    texto = '\n'.join(linhas).rstrip() + '\n'
    with open(os.path.join(pasta, 'verificacao-links.txt'), 'w', encoding='utf-8') as f:
        f.write(texto)
    print(texto)
    sys.exit(1 if problemas else 0)


if __name__ == '__main__':
    main()
