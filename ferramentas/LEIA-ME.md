# Curadoria em PDF — cola o link, sai o catálogo

## O jeito principal: `montar_pdf.py`

> A lista da curadoria fica em **`curadoria/lista.txt`**. Ela é guardada no
> repositório, e cada novo lote de links é acrescentado no fim.
>
> `python3 ferramentas/montar_pdf.py curadoria/lista.txt`

Você cola os links (ou manda para o Claude no chat), **um por linha, em
qualquer ordem**:

```
https://loja.com/sofa-lago
https://loja.com/cadeira-ana
https://loja.com/mesa-pampa | detalhe: carvalho maciço
https://loja.com/peca-x | categoria: Mesa lateral
```

- **Cada produto vai sozinho para a página da sua categoria** (Cadeira, Mesa de
  jantar, Poltrona…). As páginas seguem a ordem das categorias da curadoria.
- A categoria é descoberta pelo nome do produto e, se não der, pelo link. Uma
  "mesa" sem tipo vai para Mesa de jantar marcada para conferir. Produto sem
  categoria vai para a página **Outros**.
- Para corrigir, escreva `| categoria: Mesa lateral` depois do link. Também
  dá para agrupar à mão com uma linha `# Título` antes dos links.
- **Nada se repete:** o mesmo link duas vezes (com ou sem `#content`), ou o
  mesmo produto por links diferentes, entra uma vez só. Links de lista ou de
  categoria (ex.: `/cat/betten`) ficam de fora. Tudo isso fica anotado em
  `conferir.txt`.
- O mesmo modelo em cores diferentes ganha a variação no nome ("Ramnefjäll ·
  Idekulla beige", "Fågelfjället · 4 gavetas marfim"), com cores e acabamentos
  traduzidos (`traducoes.json`). Sklum: cada cor (`?id_c=`) traz a própria
  foto e o próprio preço. Medidas não aparecem no PDF.
- **Fotos: só o produto, sempre em fundo branco.** Entre as fotos da ficha,
  o programa escolhe a primeira que mostra só o móvel, inteiro (pula
  ambiente e detalhe). Fundo quase branco é clareado. Fundo cinza de estúdio
  é recortado com o `rembg` (`pip install "rembg[cpu]"`). As fotos tratadas
  ficam guardadas em `capturas/.fotos`, para não refazer a cada lote.
- **Subcategorias**: uma categoria `Grupo · Sub` (ex.: `Depósito & Organização · Cestos`)
  vira a página "Cestos", com "Depósito & Organização" pequeno acima do título.
- **Ordem por cor** dentro de cada página: brancos, creme e bege, madeiras (da
  clara à escura), cinzas, pretos e cores. É calculada pela foto. Os títulos
  aparecem no plural (`PLURAL` em `montar_pdf.py`).
- Desenho técnico (linhas escuras em fundo branco) nunca é usado como foto.
- **Medidas** só aparecem na página Espelho (`COM_MEDIDAS` em `montar_pdf.py`).
- Outros campos opcionais depois de `|`: `nome`, `loja`, `detalhe`,
  `preco`, `faixa` (1 a 5) e `foto` (link de outra imagem). O que você
  escrever vale mais que o capturado.

```bash
python3 ferramentas/montar_pdf.py lista.txt
python3 ferramentas/montar_pdf.py lista.txt --titulo "Curadoria Europa" --com-valor
```

Sai em `capturas/<data>/`:
- **curadoria.pdf**: A4 vertical (bom de ler no celular), fundo branco, capa,
  sumário clicável e 6 produtos por página. Cada produto é clicável e abre a loja;
- **curadoria.html**: a mesma coisa, para ajustes;
- **conferir.txt**: o que faltou capturar.

Por padrão, o card mostra só a faixa: € até 150 · €€ 150–400 · €€€ 400–800 ·
€€€€ 800–1.500 · €€€€€ acima de 1.500 (ajustável em `FAIXAS`, no `capturar.py`).
Com `--com-valor`, mostra também o valor aproximado (≈ € 199). Fontes: Cormorant Garamond e Jost, que vão
embutidas no arquivo (`fontes/`). Requisitos: Python 3, Node com Playwright
(Chromium) e, opcionalmente, o Pillow, para deixar o PDF leve.

---

## Só a captura (CSV / prévia): `capturar.py`

Você manda os links (no chat com o Claude, um por linha) e a ferramenta
`capturar.py` lê cada página e traz:

| Campo        | De onde vem                                                   |
|--------------|---------------------------------------------------------------|
| nome         | ficha do produto que a loja publica para o Google             |
| imagem       | foto principal do produto (link direto)                       |
| preço/moeda  | oferta da página (o menor preço, se houver variações)         |
| faixaPreco   | calculada pelas faixas de `assets/config.js` (€ / R$)          |
| loja/região  | pelo endereço do site (`lojas.json`)                           |
| categoria    | sugerida por palavras do nome/link (pt, es, fr, de, it, en)   |

Ela gera, numa pasta `capturas/<data>/`:
- **previa.html**: os cards para você conferir visualmente;
- **produtos.csv**: para importar no Wix (CMS → Produtos → Importar);
- **produtos.json**: o mesmo, para uso interno.

Itens incompletos saem com a coluna **conferir** preenchida (ex.: "sem preço",
"categoria", "loja nova"). Lojas que bloqueiam leitura automática (ex.: H&M,
Maisons du Monde) saem com o nome provisório tirado do link. O Claude ainda
tenta completá-los por outro caminho; se não der, você completa só o que faltou.

## Rodar

```bash
python3 ferramentas/capturar.py links.txt          # um link por linha
python3 ferramentas/capturar.py URL1 URL2 ...
```

Sem instalar nada (só Python padrão). Precisa de acesso à internet liberado
para os sites das lojas.

## Ligar o produto à loja no Wix (campo `lojaId`)

No Wix, o campo `lojaId` é uma referência e a importação precisa do **ID** da
loja. Para a ferramenta preencher sozinha:
1. Wix → CMS → coleção **Lojas** → Exportar CSV;
2. salve como `ferramentas/lojas-wix.csv` (ou mande para o Claude).

Sem esse arquivo, a coluna `loja` vem com o nome e o `lojaId` fica vazio.

## Loja nova

Acrescente o domínio em `lojas.json`:
```json
"exemplo.com": {"nome": "Exemplo", "regiao": "europa"}
```
