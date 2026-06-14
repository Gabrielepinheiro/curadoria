// =============================================================
//  data-layer.js  —  A "tomada" entre a tela e os dados.
//
//  A tela (app.js) NUNCA fala direto com o banco. Ela chama as
//  funções daqui. Assim trocamos a fonte de dados sem reescrever
//  a tela.
//
//  Dois modos:
//   • 'seed'  → dados de exemplo + localStorage. Funciona agora,
//               offline, para desenvolver e demonstrar.
//   • 'wix'   → Wix Headless: login pela Área de Membros do Wix,
//               produtos/lojas/favoritos no Wix CMS (Wix Data).
//
//  Para ligar no Wix de verdade (Fase 1, passo final):
//   1. CONFIG.mode = 'wix'
//   2. CONFIG.wixClientId = '<seu Client ID do Wix Headless>'
//  Nada mais na tela precisa mudar.
// =============================================================

import { STORES_SEED, PRODUCTS_SEED } from './seed.js';

export const CONFIG = {
  mode: 'seed',          // 'seed' | 'wix'
  wixClientId: '',       // preencher ao ligar o Wix Headless
};

// ---------------------------------------------------------------
//  Contrato público (o que a tela usa). Os dois adaptadores
//  abaixo implementam exatamente estas funções.
// ---------------------------------------------------------------
//  auth.currentUser()                  -> { id, name } | null
//  auth.login(name)                    -> { id, name }
//  auth.logout()                       -> void
//  data.listStores()                   -> [ Loja ]
//  data.createStore(store)             -> Loja
//  data.listProducts()                 -> [ Produto (com região/entrega da loja) ]
//  data.createProduct(prod)            -> Produto
//  favorites.list()                    -> Set<productId>
//  favorites.toggle(productId)         -> Set<productId>
// ---------------------------------------------------------------

/* ============================ SEED ============================ */
const seedAdapter = (() => {
  const LS = {
    user:  'cci.user',
    stores:'cci.stores',
    prods: 'cci.products',
    favs:  'cci.favs',     // por usuário: cci.favs.<userId>
  };
  const read  = (k, fallback) => {
    try { return JSON.parse(localStorage.getItem(k)) ?? fallback; }
    catch { return fallback; }
  };
  const write = (k, v) => localStorage.setItem(k, JSON.stringify(v));

  // Semeia o catálogo. SEED_VERSION força recarregar os dados de exemplo
  // quando atualizamos o seed (senão o navegador manteria a versão antiga).
  const SEED_VERSION = '4';
  if (read('cci.seedv', null) !== SEED_VERSION) {
    write(LS.stores, STORES_SEED);
    write(LS.prods, PRODUCTS_SEED);
    write('cci.seedv', SEED_VERSION);
  }

  const storesById = () =>
    Object.fromEntries(read(LS.stores, []).map((s) => [s.id, s]));

  return {
    auth: {
      currentUser: () => read(LS.user, null),
      login: (name) => {
        const user = { id: 'local-' + name.toLowerCase().replace(/\s+/g, '-'), name };
        write(LS.user, user);
        return user;
      },
      logout: () => localStorage.removeItem(LS.user),
    },
    data: {
      listStores: () => read(LS.stores, []),
      createStore: (store) => {
        const stores = read(LS.stores, []);
        const novo = { id: 'loja-' + Date.now(), ...store };
        stores.unshift(novo);
        write(LS.stores, stores);
        return novo;
      },
      listProducts: () => {
        const map = storesById();
        return read(LS.prods, []).map((p) => {
          const loja = map[p.storeId] || {};
          // Região e entrega vêm da loja (briefing §5.7 / §6).
          return { ...p, region: loja.region, ships: loja.ships || [], storeName: loja.name };
        });
      },
      createProduct: (prod) => {
        const prods = read(LS.prods, []);
        const novo = { id: 'prod-' + Date.now(), ...prod };
        prods.unshift(novo);
        write(LS.prods, prods);
        return novo;
      },
    },
    favorites: {
      _key: () => {
        const u = read(LS.user, null);
        return u ? `${LS.favs}.${u.id}` : `${LS.favs}.anon`;
      },
      list() { return new Set(read(this._key(), [])); },
      toggle(productId) {
        const set = this.list();
        set.has(productId) ? set.delete(productId) : set.add(productId);
        write(this._key(), [...set]);
        return set;
      },
    },
  };
})();

/* ============================ WIX ============================ */
//  Esqueleto pronto para ligar no Wix Headless. Usa o SDK oficial
//  do Wix via ESM (sem build/empacotador). Mantido inativo até
//  CONFIG.mode === 'wix'. As coleções do Wix CMS estão definidas
//  em docs/wix-cms-schema.md.
const wixAdapter = (() => {
  let client = null;
  let _user = null;

  async function getClient() {
    if (client) return client;
    const { createClient, OAuthStrategy } = await import('https://esm.sh/@wix/sdk');
    const { items }    = await import('https://esm.sh/@wix/data');
    const { members }  = await import('https://esm.sh/@wix/members');
    const { authentication } = await import('https://esm.sh/@wix/members');
    client = createClient({
      modules: { items, members, authentication },
      auth: OAuthStrategy({ clientId: CONFIG.wixClientId }),
    });
    return client;
  }

  const storesById = async () => {
    const c = await getClient();
    const res = await c.items.query('Lojas').limit(1000).find();
    return Object.fromEntries(res.items.map((s) => [s._id, s]));
  };

  return {
    auth: {
      currentUser: () => _user,
      async login() {
        const c = await getClient();
        // Fluxo de login da Área de Membros do Wix (redirect/managed).
        const data = c.authentication.generateOAuthData(window.location.href);
        const { authUrl } = await c.authentication.getAuthUrl(data);
        window.location.href = authUrl;
      },
      async logout() {
        const c = await getClient();
        const { logoutUrl } = await c.authentication.logout(window.location.href);
        _user = null;
        window.location.href = logoutUrl;
      },
    },
    data: {
      async listStores() {
        const c = await getClient();
        const res = await c.items.query('Lojas').limit(1000).find();
        return res.items;
      },
      async createStore(store) {
        const c = await getClient();
        const res = await c.items.insert('Lojas', store);
        return res;
      },
      async listProducts() {
        const c = await getClient();
        const map = await storesById();
        const res = await c.items.query('Produtos').limit(1000).find();
        return res.items.map((p) => {
          const loja = map[p.lojaId] || {};
          return { ...p, region: loja.regiao, ships: loja.entregaEm || [], storeName: loja.nome };
        });
      },
      async createProduct(prod) {
        const c = await getClient();
        return c.items.insert('Produtos', prod);
      },
    },
    favorites: {
      async list() {
        const c = await getClient();
        const res = await c.items.query('Favoritos')
          .eq('membroId', _user?.id).limit(1000).find();
        return new Set(res.items.map((f) => f.produtoId));
      },
      async toggle(productId) {
        const c = await getClient();
        const existing = await c.items.query('Favoritos')
          .eq('membroId', _user?.id).eq('produtoId', productId).find();
        if (existing.items.length) {
          await c.items.remove('Favoritos', existing.items[0]._id);
        } else {
          await c.items.insert('Favoritos', { membroId: _user?.id, produtoId: productId });
        }
        return this.list();
      },
    },
  };
})();

/* ===================== seletor de modo ===================== */
const active = CONFIG.mode === 'wix' ? wixAdapter : seedAdapter;

// Normaliza tudo para Promise, para a tela poder usar await
// independentemente do modo (seed é síncrono, wix é assíncrono).
const wrap = (obj) =>
  Object.fromEntries(
    Object.entries(obj).map(([name, fn]) => [
      name,
      typeof fn === 'function' ? (...args) => Promise.resolve(fn.apply(obj, args)) : fn,
    ]),
  );

export const auth      = wrap(active.auth);
export const data      = wrap(active.data);
export const favorites = wrap(active.favorites);
