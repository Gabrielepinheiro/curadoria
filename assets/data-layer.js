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
  mode: 'wix',                                        // 'seed' | 'wix'
  wixClientId: 'b68aa461-9904-4443-b1cc-74d9861f6739',// Client ID do Wix Headless (Curadoria CCI)
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
//  Conexão com o Wix Headless via SDK oficial (ESM, sem build).
//  Lê as coleções Lojas/Produtos/Favoritos do Wix CMS.
//  Login: por enquanto é simples (nome), só para validarmos o catálogo
//  real. O login de MEMBROS de verdade (e a integração Hotmart) entram
//  na Fase 2. Mapeamento é defensivo porque o formato exato dos itens
//  pode variar (campos no topo ou sob .data; referência como id ou objeto).
const wixAdapter = (() => {
  let client = null;
  const LS_USER = 'cci.user';
  const lread = (k, f) => { try { return JSON.parse(localStorage.getItem(k)) ?? f; } catch { return f; } };
  const lwrite = (k, v) => localStorage.setItem(k, JSON.stringify(v));

  async function getClient() {
    if (client) return client;
    const { createClient, OAuthStrategy } = await import('https://esm.sh/@wix/sdk');
    const { items } = await import('https://esm.sh/@wix/data');
    const { members } = await import('https://esm.sh/@wix/members');
    const tokens = lread('cci.wixTokens', null) || undefined;
    client = createClient({
      modules: { items, members },
      auth: OAuthStrategy({ clientId: CONFIG.wixClientId, tokens }),
    });
    return client;
  }

  // Login real de membros é o PADRÃO no modo Wix. Para validar o catálogo
  // com o login simples por nome (sem senha), acesse com ?login=nome.
  const REAL_LOGIN = (typeof location === 'undefined')
    || new URLSearchParams(location.search).get('login') !== 'nome';

  // normaliza um item (campos podem vir no topo ou sob .data)
  const F = (it) => {
    const d = (it && it.data) ? it.data : (it || {});
    return { ...d, _id: (it && it._id) || d._id };
  };
  const refId = (v) => (v && typeof v === 'object') ? (v._id || v.id) : v;
  const nameOf = (o) => o.nome || o.title || o.titulo || o.Title || '';
  // aceita campo vindo como Texto OU como Tags (array) — usa o 1º valor
  const oneTag = (v) => Array.isArray(v) ? (v[0] || '') : (v || '');
  const imgUrl = (v) => {
    if (!v) return '';
    if (typeof v === 'string') return v.startsWith('wix:image://') ? '' : v;
    return v.url || v.src || '';
  };
  const dateStr = (v) => { if (!v) return ''; try { return new Date(v).toISOString().slice(0, 10); } catch { return String(v); } };

  async function queryAll(collectionId) {
    const c = await getClient();
    const res = await c.items.query(collectionId).limit(1000).find();
    return (res.items || []).map(F);
  }

  return {
    auth: REAL_LOGIN ? {
      // --- Login real de membros (Wix-managed login, via redirect) ---
      async currentUser() {
        const c = await getClient();
        try {
          if (typeof location !== 'undefined' && /[?&](code|state|error)=/.test(location.search)) {
            const returned = await c.auth.parseFromUrl();
            const oauthData = lread('cci.oauthData', null);
            if (returned && returned.code && oauthData) {
              const tokens = await c.auth.getMemberTokens(returned.code, returned.state, oauthData);
              c.auth.setTokens(tokens);
              lwrite('cci.wixTokens', tokens);
              localStorage.removeItem('cci.oauthData');
            }
            const p = new URLSearchParams(location.search);
            ['code', 'state', 'error', 'error_description'].forEach((k) => p.delete(k));
            history.replaceState({}, '', location.pathname + (p.toString() ? '?' + p : ''));
          }
        } catch (e) { console.warn('Wix login (callback):', e); }
        try {
          const res = await c.members.getCurrentMember();
          const m = (res && (res.member || res)) || null;
          if (m && (m._id || m.id)) {
            const name = (m.profile && m.profile.nickname)
              || (m.contact && m.contact.firstName) || m.loginEmail || 'Cliente';
            const user = { id: m._id || m.id, name };
            lwrite(LS_USER, user); return user;
          }
        } catch (e) { /* não logado ainda */ }
        return null;
      },
      async login() {
        const setS = (m) => { try { const el = document.getElementById('loginError'); if (el) { el.style.color = 'var(--bronze)'; el.textContent = m; } } catch (_) {} };
        setS('1/4 Carregando conexão com o Wix…');
        const c = await getClient();
        setS('2/4 Preparando login…');
        const redirect = location.href; // preserva ?fonte=wix&login=wix ao voltar
        const oauthData = c.auth.generateOAuthData(redirect, redirect);
        lwrite('cci.oauthData', oauthData);
        setS('3/4 Pedindo o endereço de login ao Wix…');
        const { authUrl } = await c.auth.getAuthUrl(oauthData);
        setS('4/4 Redirecionando para o login…');
        location.href = authUrl;
      },
      async logout() {
        const c = await getClient();
        localStorage.removeItem('cci.wixTokens');
        localStorage.removeItem(LS_USER);
        try {
          const { logoutUrl } = await c.auth.logout(location.href);
          location.href = logoutUrl;
        } catch { location.reload(); }
      },
    } : {
      // --- Login simples por nome (só para validar o catálogo) ---
      currentUser: () => lread(LS_USER, null),
      login: (name) => {
        const u = { id: 'wix-' + (name || 'cliente').toLowerCase().replace(/\s+/g, '-'), name };
        lwrite(LS_USER, u); return u;
      },
      logout: () => localStorage.removeItem(LS_USER),
    },
    data: {
      async listStores() {
        return (await queryAll('Lojas')).map((s) => ({
          id: s._id, name: nameOf(s), site: s.site, region: oneTag(s.regiao), ships: s.entregaEm || [],
        }));
      },
      async createStore() { throw new Error('No modo Wix, cadastre lojas pelo CMS do Wix.'); },
      async listProducts() {
        const stores = Object.fromEntries((await queryAll('Lojas')).map((s) => [s._id, s]));
        const prods = await queryAll('Produtos');
        return prods.map((p) => {
          const loja = stores[refId(p.lojaId)] || {};
          return {
            id: p._id, nome: nameOf(p), referencia: p.referencia, link: p.link || '#',
            imagem: imgUrl(p.imagem), categoria: oneTag(p.categoria),
            faixaPreco: Number(p.faixaPreco) || 1,
            novidade: !!p.novidade, novidadeAte: dateStr(p.novidadeAte),
            region: oneTag(loja.regiao), ships: loja.entregaEm || [], storeName: nameOf(loja),
          };
        });
      },
      async createProduct() { throw new Error('No modo Wix, cadastre produtos pelo CMS do Wix.'); },
    },
    favorites: {
      _uid() { return (lread(LS_USER, {}) || {}).id || 'anon'; },
      async list() {
        try {
          const c = await getClient();
          const res = await c.items.query('Favoritos').eq('membroId', this._uid()).limit(1000).find();
          return new Set((res.items || []).map(F).map((f) => refId(f.produtoId)));
        } catch (e) { console.warn('Favoritos (list):', e); return new Set(); }
      },
      async toggle(productId) {
        try {
          const c = await getClient();
          const ex = await c.items.query('Favoritos').eq('membroId', this._uid()).eq('produtoId', productId).find();
          if ((ex.items || []).length) {
            await c.items.remove('Favoritos', F(ex.items[0])._id);
          } else {
            await c.items.insert('Favoritos', { membroId: this._uid(), produtoId: productId });
          }
        } catch (e) { console.warn('Favoritos (toggle):', e); }
        return this.list();
      },
    },
  };
})();

/* ===================== seletor de modo ===================== */
// Modo padrão = CONFIG.mode (hoje 'seed', preview aprovado intacto).
// Para TESTAR a conexão real com o Wix sem mexer no padrão, acesse com
// ?fonte=wix no fim do endereço. ?fonte=seed força o modo exemplo.
const _params = (typeof location !== 'undefined') ? new URLSearchParams(location.search) : new URLSearchParams();
const _urlMode = _params.get('fonte');
const MODE = (_urlMode === 'wix' || _urlMode === 'seed') ? _urlMode : CONFIG.mode;
// true quando o login real de membros está ativo (padrão no modo Wix).
// Para testar o catálogo com login simples por nome, use ?login=nome.
export const IS_REAL_LOGIN = MODE === 'wix' && _params.get('login') !== 'nome';
const active = MODE === 'wix' ? wixAdapter : seedAdapter;

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
