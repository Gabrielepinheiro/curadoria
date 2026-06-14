# Banco de dados — coleções do Wix CMS

Estas são as "tabelas" a criar no Wix CMS (Content Manager) para a Fase 1.
Espelham o modelo do briefing §6 e o que `assets/data-layer.js` (modo `wix`) espera.

> Permissões sugeridas: **Lojas** e **Produtos** com leitura pública (clientes
> logados veem) e escrita só para Admin/Equipe. **Favoritos** com leitura/escrita
> restrita ao próprio membro (Member-generated content).

---

## Coleção: `Lojas`
Cadastrada uma vez por loja; o produto herda região e entrega daqui (briefing §5.8).

| Campo (ID)   | Tipo            | Observação                                |
|--------------|-----------------|-------------------------------------------|
| `nome`       | Texto           | Nome da loja                              |
| `site`       | URL             | Site da loja                              |
| `regiao`     | Texto           | `europa` \| `brasil` (id da região)       |
| `entregaEm`  | Tags / Array    | Países onde entrega                       |

## Coleção: `Produtos`
| Campo (ID)    | Tipo          | Observação                                         |
|---------------|---------------|---------------------------------------------------|
| `nome`        | Texto         | Nome em português                                 |
| `referencia`  | Texto         | Nome original na loja (outro idioma)              |
| `link`        | URL           | Página do produto na loja (abre em nova aba)      |
| `imagem`      | Imagem        | Foto do produto (upload/colar)                    |
| `lojaId`      | Referência → `Lojas` | Define região e entrega automaticamente    |
| `categoria`   | Texto         | Uma das categorias de `assets/config.js`          |
| `faixaPreco`  | Número (1–5)  | Faixa de preço; vira símbolos de moeda            |
| `novidade`    | Booleano      | Aparece na aba Novidades                          |
| `novidadeAte` | Data          | Após esta data sai de Novidades (fica no catálogo)|

## Coleção: `Favoritos`
| Campo (ID)   | Tipo          | Observação                                  |
|--------------|---------------|---------------------------------------------|
| `membroId`   | Texto         | ID do membro logado (Wix Members)           |
| `produtoId`  | Referência → `Produtos` | Peça favoritada                   |

---

## Como ligar a tela ao Wix (modo `wix`)
1. Ativar **Wix Headless** no painel do site e criar um **OAuth Client** (Client ID).
2. Em `assets/data-layer.js`:
   - `CONFIG.mode = 'wix'`
   - `CONFIG.wixClientId = '<Client ID>'`
3. Habilitar a **Área de Membros** (login/senha + "esqueci a senha").
4. Importar o catálogo (Airtable → CSV → Wix CMS) para `Lojas` e `Produtos`.

## Fase 2 — Hotmart (depois)
Webhook/postback da Hotmart → uma **http-function** do Velo cria/ativa o membro na
compra e revoga no reembolso. **Sem Zapier.** Detalhar quando chegarmos nesta fase.
