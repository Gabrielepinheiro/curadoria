# Ligar a curadoria no Wix — guia passo a passo (linguagem simples)

> Objetivo: fazer o site da curadoria parar de usar dados de exemplo e passar a
> usar **login real** e **banco de dados de verdade** dentro do seu Wix.
>
> O que **eu (Claude) já fiz**: todo o código está pronto. Para "virar a chave",
> basta preencher 2 informações em `assets/data-layer.js` (`CONFIG.mode = 'wix'`
> e `CONFIG.wixClientId = '...'`). Eu faço isso assim que você me mandar o Client ID.
>
> O que **você faz no Wix** (cliques no painel): os passos abaixo. Faça um de
> cada vez e me avise — eu confirmo antes do próximo.

---

## Passo 1 — Criar o banco de dados (Content Manager / CMS)

No painel do Wix: **CMS** (ou "Content Manager") → **+ Criar coleção**.
Crie **3 coleções** com estes campos (o nome do campo precisa ser igual):

### Coleção `Lojas`
- `nome` — Texto
- `site` — URL
- `regiao` — Texto (use `europa` ou `brasil`)
- `entregaEm` — Tags (vários países)

### Coleção `Produtos`
- `nome` — Texto
- `referencia` — Texto
- `link` — URL
- `imagem` — Imagem
- `lojaId` — Referência → coleção `Lojas`
- `categoria` — Texto
- `faixaPreco` — Número (1 a 5)
- `novidade` — Sim/Não (Booleano)
- `novidadeAte` — Data

### Coleção `Favoritos`
- `membroId` — Texto
- `produtoId` — Referência → coleção `Produtos`

> Dica: dá para criar a coleção e ir adicionando os campos um a um. Não precisa
> cadastrar produtos agora — isso vem no Passo 5 (importação).

---

## Passo 2 — Ligar a Área de Membros (o login dos clientes)

No painel: **Adicionar** → **Área de Membros** (Members Area). Isso cria o
sistema de login/senha e o "esqueci minha senha" automaticamente.

(Depois, na Fase 2, a compra na Hotmart criará o membro sozinho. Por enquanto,
serve para você e testers entrarem.)

---

## Passo 3 — Ativar o Wix Headless e gerar o Client ID  ⬅️ é o que eu preciso

Esta é a "chave" que liga o nosso site ao seu Wix.

1. Painel do Wix → **Configurações (Settings)** → **Headless** (ou "Headless Settings").
2. Crie um **OAuth Client** (cliente OAuth). Tipo: **visitantes/membros** (público).
3. Copie o **Client ID** que aparecer.
4. **Me mande esse Client ID aqui no chat.**

Com ele, eu coloco no código e o site passa a falar com o seu Wix.

---

## Passo 4 — Permissões das coleções

No CMS, em cada coleção → **Permissões (Permissions)**:
- `Lojas` e `Produtos`: leitura **"Qualquer pessoa"** (ou "Membros do site"),
  escrita só **Admin**.
- `Favoritos`: conteúdo **gerado por membro** (cada membro lê/escreve o seu).

---

## Passo 5 — Importar o catálogo do Airtable

1. No Airtable, exporte as tabelas como **CSV**.
2. No Wix CMS, em cada coleção → **Importar CSV**.
3. Importe primeiro `Lojas`, depois `Produtos` (para as referências baterem).

> Se preferir, me mande os CSV que eu te ajudo a ajustar as colunas para
> encaixarem nos campos acima.

---

## Passo 6 — Eu viro a chave

Quando os passos 1–3 estiverem prontos e você me mandar o **Client ID**, eu:
- coloco `CONFIG.mode = 'wix'` e o seu Client ID em `assets/data-layer.js`;
- ajusto qualquer detalhe de nome de campo, se preciso;
- publicamos e testamos o login + catálogo reais.

---

## Observações honestas
- Você está no plano **Light**. Se em algum passo (Headless/Members/CMS) o Wix
  pedir um upgrade, me avise — eu te digo a opção mais barata que resolve.
- A Hotmart (compra libera acesso / reembolso revoga) é a **Fase 2**, depois que
  a curadoria estiver no ar com login e catálogo reais.
