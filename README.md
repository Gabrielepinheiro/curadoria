# Casa com Identidade — Plataforma de Curadoria (CCI)

Plataforma web privada onde clientes navegam por uma curadoria de interiores (móveis e
decoração selecionada pela arquiteta Gabriele Pinheiro. Cada peça abre na loja
externa. **Não é e-commerce** — a venda é apenas do *acesso* à curadoria
(pela Hotmart).

Este repositório contém a **tela** (frontend), fiel ao protótipo aprovado, já
estruturada para funcionar de verdade conectada ao **Wix** como back-end
(login + banco de dados).

---

## Como roda

A tela nunca fala direto com o banco — ela passa por `assets/data-layer.js`,
que tem dois modos:

| Modo    | O que usa                                   | Para quê                        |
|---------|---------------------------------------------|---------------------------------|
| `seed`  | Dados de exemplo + `localStorage`           | Desenvolver/demonstrar (atual)  |
| `wix`   | Wix Headless: Membros + Wix CMS (Wix Data)  | Produção, ligado ao seu Wix     |

Trocar de um para o outro é mudar `CONFIG.mode` em `assets/data-layer.js`.
Nada na tela precisa ser reescrito.

### Rodar localmente (modo seed)
Precisa de um servidor estático simples (por causa dos módulos ES):

```bash
python3 -m http.server 8000
# abra http://localhost:8000
```

Entre com qualquer nome. Os dados de exemplo já aparecem.

---

## O que já funciona (Fase 1 — em construção)

- ✅ Login por pessoa (nome no modo seed; **Área de Membros do Wix** no modo wix)
- ✅ Catálogo vindo de um banco (não mais chumbado no código)
- ✅ Navegação por **região** (Europa € / Brasil R$) e filtro **"Você mora em"**
- ✅ Filtro por **categoria** (lista completa do briefing) e **busca** por texto
- ✅ Cards abrem a loja externa em nova aba
- ✅ **Favoritos por cliente** que persistem (localStorage no seed; Wix CMS no wix)
- ✅ **Novidades** com selo "Novo" e **data de expiração**
- ✅ **Aviso legal** com aceite registrado (data/hora/usuário)
- ✅ **Cadastro rápido**: colar imagem (Ctrl+V) ou URL, loja preenche
     região/entrega automaticamente, faixa de preço por símbolos,
     **"Salvar + próximo"**

## O que NÃO é mágica (e por quê)

O protótipo tinha um botão "Extrair" que parecia ler a página da loja e trazer
nome/foto/preço sozinho. **Isso não funciona de forma confiável** com milhares de
lojas diferentes, então foi substituído pelo cadastro rápido honesto do briefing
(colar imagem + campos rápidos + herança da loja + salvar e próximo).

---

## Próximos passos

1. **Ligar no Wix**: criar as coleções (`docs/wix-cms-schema.md`), ativar Wix
   Headless + Área de Membros, preencher `CONFIG`.
2. **Importar o catálogo** real (Airtable → Wix CMS).
3. **Área admin** completa: Lojas, Produtos (lista/editar/excluir), Equipe com
   permissões, Clientes.
4. **Fase 2 — Hotmart**: webhook via Velo cria/ativa e revoga acesso. Sem Zapier.

## Estrutura

```
index.html              estrutura da página (fiel ao protótipo)
assets/
  styles.css            visual CCI (base do protótipo + adições)
  config.js             regiões, países, moedas, categorias, faixas (configurável)
  data-layer.js         a "tomada": modo seed ↔ modo wix
  seed.js               dados de exemplo
  app.js                lógica da tela (filtros, favoritos, cadastro, novidades)
docs/
  wix-cms-schema.md     coleções do Wix e como conectar
```
