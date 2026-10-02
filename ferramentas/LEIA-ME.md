# Curadoria em PDF — cola o link, sai o catálogo

## O jeito principal: `montar_pdf.py`

Você escreve uma lista simples (ou manda para o Claude no chat):

```
# Sofás
https://loja.com/sofa-lago
https://loja.com/sofa-dara | nome: Dara | medidas: 100 × 220 cm | detalhe: capa algodão off

# Mesa de cabeceira
https://loja.com/mesa-pampa
```

- `# Título` abre uma seção, que vira o título da página.
- Depois do link, com `|`, você pode escrever: `nome`, `loja`, `medidas`,
  `detalhe`, `preco`, `faixa` (1 a 5) e `foto` (link de outra imagem). O que
  você escrever vale mais que o capturado.

```bash
python3 ferramentas/montar_pdf.py lista.txt
python3 ferramentas/montar_pdf.py lista.txt --titulo "Curadoria Europa" --sem-valor
```

Sai em `capturas/<data>/`:
- **curadoria.pdf**: A4 horizontal, fundo branco, capa, sumário clicável e
  8 produtos por página. Cada produto é clicável e abre a loja;
- **curadoria.html**: a mesma coisa, para ajustes;
- **conferir.txt**: o que faltou capturar.

Por padrão, o card mostra a faixa (€€) e o valor aproximado (≈ € 199). Com
`--sem-valor`, mostra só a faixa. Fontes: Cormorant Garamond e Jost, que vão
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
