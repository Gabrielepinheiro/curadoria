// =============================================================
//  app.js — lógica da tela. Fala só com a camada de dados
//  (data-layer.js), nunca direto com o banco.
// =============================================================
import {
  REGIONS, COUNTRIES, PRICE_BANDS, CATEGORIES, coverFor, regionById,
} from './config.js';
import { auth, data, favorites } from './data-layer.js';

// ---------- estado ----------
const state = {
  user: null,
  region: REGIONS[0].id,
  category: 'Todos',
  search: '',
  country: '',                 // filtro "Você mora em"
  view: 'curadoria',           // 'curadoria' | 'favoritos' | 'novidades'
  products: [],
  favs: new Set(),
  admin: { price: 3, image: '' },
};

const $ = (id) => document.getElementById(id);
const today = () => new Date().toISOString().slice(0, 10);

// ---------- AVISO LEGAL (texto final fornecido por Gabriele) ----------
const LEGAL_TEXT = `
<p><strong>Curadoria indicativa.</strong> A Casa com Identidade reúne uma seleção de produtos de lojas de terceiros. Não vendemos os produtos exibidos nem intermediamos a compra. Ao clicar numa peça, você é direcionado ao site da loja de origem, onde a compra acontece diretamente com o vendedor.</p>
<p><strong>Seleção por critério editorial.</strong> As peças são escolhidas com base em critérios de estilo, coerência estética, reputação da loja e faixa de preço. Nem todas são inspecionadas fisicamente pela arquiteta.</p>
<p><strong>Informações do produto.</strong> Cores, medidas, materiais e disponibilidade podem variar em relação ao exibido. Recomendamos confirmar os detalhes diretamente na loja antes de finalizar qualquer compra.</p>
<p><strong>Nome das lojas.</strong> O nome original da loja é mantido no idioma de origem para facilitar a localização do produto no site.</p>
<p><strong>Caráter da curadoria.</strong> As sugestões têm caráter inspiracional e editorial. A curadoria não substitui um projeto de arquitetura ou decoração personalizado.</p>
<p><strong>Compra, entrega e atendimento.</strong> Pagamento, entrega, trocas, garantias e suporte ao cliente são de responsabilidade exclusiva da loja de origem.</p>
<p><strong>Propriedade intelectual.</strong> A curadoria, a organização do conteúdo e os textos desta plataforma são de propriedade de Gabriele Pinheiro. É proibida a reprodução sem autorização.</p>

<h4 style="font-family:'Marcellus',serif;font-size:19px;margin:24px 0 8px">Proteção de dados — GDPR (União Europeia) e LGPD (Brasil)</h4>
<p>Esta plataforma está em conformidade com o Regulamento Geral sobre a Proteção de Dados da União Europeia (GDPR, Regulamento (UE) 2016/679), a lei alemã de proteção de dados (DSGVO) e, para usuárias no Brasil, a LGPD (Lei 13.709/2018).</p>
<p><strong>Responsável pelo tratamento.</strong> Gabriele Pinheiro — contato@gabrielepinheiro.com</p>
<p><strong>Dados que tratamos.</strong> Dados de cadastro e acesso (nome e e-mail), registro do aceite deste aviso (data e hora) e preferências dentro da plataforma. Não processamos pagamentos — estes ocorrem diretamente nas lojas de origem, sob as políticas delas.</p>
<p><strong>Base legal.</strong> Execução do contrato de acesso à curadoria (Art. 6(1)(b) GDPR); consentimento, quando aplicável (Art. 6(1)(a)); e legítimo interesse na operação e segurança da plataforma (Art. 6(1)(f)).</p>
<p><strong>Cookies.</strong> Utilizamos apenas armazenamento estritamente necessário ao funcionamento da plataforma: manter o acesso ativo e registrar o aceite deste aviso. Cookies não essenciais só serão utilizados mediante consentimento prévio, por meio do banner de consentimento.</p>
<p><strong>Compartilhamento de dados.</strong> Os dados são tratados em servidores na União Europeia. Eventuais transferências internacionais seguem as salvaguardas do GDPR. Ao acessar uma loja externa, seus dados passam a ser tratados conforme a política de privacidade da própria loja.</p>
<p><strong>Prazo de retenção.</strong> Os dados são mantidos pelo tempo necessário às finalidades descritas ou enquanto durar o seu acesso. Após esse período, são eliminados ou anonimizados.</p>
<p><strong>Seus direitos.</strong> Você pode solicitar acesso, correção, eliminação, portabilidade, limitação ou oposição ao tratamento dos seus dados escrevendo para contato@gabrielepinheiro.com. Também é possível retirar o consentimento a qualquer momento e apresentar reclamação à autoridade de proteção de dados competente (na Alemanha, a autoridade estadual — Landesdatenschutzbehörde).</p>
`;

// =============================================================
//  LOGIN
// =============================================================
async function doLogin() {
  const name = $('accessName').value.trim();
  if (!name) { $('loginError').textContent = 'Digite seu nome para entrar.'; return; }
  state.user = await auth.login(name);
  $('loginScreen').style.display = 'none';
  await afterLogin();
}

async function afterLogin() {
  await maybeShowLegal();
  state.favs = await favorites.list();
  state.products = await data.listProducts();
  renderGreeting();
  renderAtlas();
  renderCountryPick();
  renderCats();
  renderGrid();
  updateFavCount();
}

// =============================================================
//  AVISO LEGAL — registra o aceite (data/hora/usuário) §5.2
// =============================================================
function legalKey() { return 'cci.legal.' + (state.user?.id || 'anon'); }

function maybeShowLegal() {
  $('legalBody').innerHTML = LEGAL_TEXT;
  const accepted = localStorage.getItem(legalKey());
  if (accepted) return Promise.resolve();
  return new Promise((resolve) => {
    $('legalCloseBtn').style.display = 'none';
    $('legalAcceptBtn').style.display = '';
    $('legalModal').classList.add('open');
    $('legalAcceptBtn').onclick = () => {
      localStorage.setItem(legalKey(), JSON.stringify({ user: state.user, at: new Date().toISOString() }));
      $('legalModal').classList.remove('open');
      resolve();
    };
  });
}

function openLegalReadOnly() {
  $('legalBody').innerHTML = LEGAL_TEXT;
  $('legalAcceptBtn').style.display = 'none';
  $('legalCloseBtn').style.display = '';
  $('legalModal').classList.add('open');
  $('legalCloseBtn').onclick = () => $('legalModal').classList.remove('open');
}

// =============================================================
//  RENDER
// =============================================================
function renderGreeting() {
  $('greet').innerHTML =
    `Bem-vindo(a), ${state.user.name} · <button id="editName">editar nome</button>`;
  $('editName').onclick = async () => {
    const novo = prompt('Como prefere ser chamado(a)?', state.user.name);
    if (novo && novo.trim()) {
      state.user = await auth.login(novo.trim());
      renderGreeting();
    }
  };
}

function renderAtlas() {
  $('atlas').innerHTML = REGIONS.map((r) =>
    `<button data-region="${r.id}" class="${(state.view === 'curadoria' && r.id === state.region) ? 'active' : ''}">
       ${r.label}<span class="cur">${r.currency}</span>
     </button>`).join('');
  $('atlas').querySelectorAll('button').forEach((b) => {
    b.onclick = () => setRegion(b.dataset.region);
  });
}

function renderCountryPick() {
  const list = COUNTRIES[state.region] || [];
  const pick = $('countryPick');
  // "Você mora em" só faz sentido quando a região tem vários países (Europa).
  if (list.length > 1) {
    pick.style.display = '';
    $('countrySelect').innerHTML =
      `<option value="">Todos os países</option>` +
      list.map((c) => `<option value="${c}">${c}</option>`).join('');
    $('countrySelect').value = state.country;
  } else {
    pick.style.display = 'none';
    state.country = '';
  }
}

function renderCats() {
  const cats = ['Todos', ...CATEGORIES];
  $('cats').innerHTML = cats.map((c) =>
    `<button data-cat="${c}" class="${c === state.category ? 'active' : ''}">${c}</button>`).join('');
  $('cats').querySelectorAll('button').forEach((b) => {
    b.onclick = () => { state.category = b.dataset.cat; renderCats(); renderGrid(); };
  });
}

function isActiveNovelty(p) {
  return p.novidade && (!p.novidadeAte || p.novidadeAte >= today());
}

function currentItems() {
  let items = state.products.slice();

  if (state.view === 'favoritos') {
    items = items.filter((p) => state.favs.has(p.id));
  } else if (state.view === 'novidades') {
    items = items.filter(isActiveNovelty);
  } else {
    items = items.filter((p) => p.region === state.region);
    if (state.country) items = items.filter((p) => (p.ships || []).includes(state.country));
  }

  if (state.category !== 'Todos') items = items.filter((p) => p.categoria === state.category);

  if (state.search) {
    const q = state.search.toLowerCase();
    items = items.filter((p) =>
      [p.nome, p.referencia, p.storeName].filter(Boolean)
        .some((t) => t.toLowerCase().includes(q)));
  }
  return items;
}

function priceHTML(level, currency) {
  let s = '';
  for (let i = 1; i <= 5; i++) s += `<span class="${i <= level ? '' : 'dim'}">${currency}</span>`;
  return s;
}

function renderGrid() {
  const grid = $('grid');
  const empty = $('emptyState');

  // Entrada da curadoria: mostra só as categorias (capas). Clicar abre os produtos.
  const isLanding = state.view === 'curadoria' && state.category === 'Todos' && !state.search;

  if (state.view === 'favoritos') {
    $('heroTitle').innerHTML = 'Seus favoritos, <em class="ital">num só lugar.</em>';
    $('heroSub').textContent = 'Espaço feito para você não perder os itens que mais gostou.';
  } else if (state.view === 'novidades') {
    $('heroTitle').innerHTML = '<em class="ital">Novidades</em> da curadoria.';
    $('heroSub').textContent = 'Aqui você encontra as peças que acabaram de entrar na curadoria. Todo mês, novas peças pra você.';
  } else if (isLanding) {
    $('heroTitle').innerHTML = 'Móveis e decoração <em class="ital">com&nbsp;curadoria</em>, loja a loja.';
    $('heroSub').textContent = 'Explore a curadoria por categoria — uma seleção editorial de móveis e decoração, escolhida peça por peça.';
  } else if (state.search) {
    $('heroTitle').innerHTML = 'Resultados da <em class="ital">busca.</em>';
    $('heroSub').textContent = 'Peças que combinam com o que você procura.';
  } else {
    $('heroTitle').textContent = state.category;
    $('heroSub').textContent = 'Cada peça foi avaliada: reputação da loja e países de entrega. Clique para abrir direto na loja.';
  }

  // toolbar de país só na curadoria
  $('countryPick').style.display =
    (state.view === 'curadoria' && (COUNTRIES[state.region] || []).length > 1) ? '' : 'none';

  if (isLanding) {
    empty.style.display = 'none';
    grid.className = 'grid grid-cats';
    grid.innerHTML = CATEGORIES.map((cat) => `<article class="cat-tile" data-cat="${escapeAttr(cat)}">
        <div class="cat-tile-img"><img src="${coverFor(cat)}" alt="${escapeAttr(cat)}" loading="lazy"></div>
        <div class="cat-tile-name">${cat}</div>
      </article>`).join('');
    grid.querySelectorAll('[data-cat]').forEach((el) => {
      el.onclick = () => setCat(el.dataset.cat);
    });
    return;
  }

  grid.className = 'grid';
  const items = currentItems();

  if (!items.length) {
    grid.innerHTML = '';
    empty.style.display = 'block';
    $('emptyMsg').textContent =
      state.view === 'favoritos' ? 'Toque no coração de qualquer peça para guardá-la aqui.'
      : state.view === 'novidades' ? 'Sem novidades no momento — volte em breve.'
      : state.search ? 'Nada encontrado para esta busca.'
      : 'Nenhuma peça nesta categoria ainda.';
    return;
  }
  empty.style.display = 'none';

  grid.innerHTML = items.map((p) => {
    const region = regionById(p.region);
    const fav = state.favs.has(p.id);
    // Foto própria do produto, ou a capa oficial aprovada da categoria.
    const imgSrc = p.imagem || coverFor(p.categoria);
    const imgInner = `<img src="${imgSrc}" alt="${escapeAttr(p.nome)}" loading="lazy">`;
    return `<article class="card">
      ${isActiveNovelty(p) ? '<span class="badge-new">Novo</span>' : ''}
      <button class="fav ${fav ? 'on' : ''}" data-fav="${p.id}" aria-label="Favoritar">♥</button>
      <div class="img" data-open="${escapeAttr(p.link)}">${imgInner}</div>
      <div class="info">
        <div class="store">${p.storeName || ''} · ${region.label}</div>
        <div class="name" data-open="${escapeAttr(p.link)}">${p.nome}</div>
        ${p.referencia ? `<div class="ref">${p.referencia}</div>` : ''}
        <div class="meta">
          <div class="ships">Entrega:<br>${(p.ships || []).join(', ') || '—'}</div>
          <div class="price">${priceHTML(p.faixaPreco, region.currency)}</div>
        </div>
      </div>
    </article>`;
  }).join('');

  grid.querySelectorAll('[data-open]').forEach((el) => {
    el.onclick = () => { const u = el.dataset.open; if (u && u !== '#') window.open(u, '_blank'); };
  });
  grid.querySelectorAll('[data-fav]').forEach((el) => {
    el.onclick = async (e) => { e.stopPropagation(); await toggleFav(el.dataset.fav); };
  });
}

function escapeAttr(s) { return String(s || '').replace(/"/g, '&quot;'); }

// =============================================================
//  AÇÕES
// =============================================================
function setRegion(id) {
  state.region = id;
  state.view = 'curadoria';
  state.country = '';
  setActiveChips();
  renderAtlas(); renderCountryPick(); renderGrid();
}

function setView(view) {
  state.view = (state.view === view) ? 'curadoria' : view;
  setActiveChips();
  renderAtlas(); renderGrid();
}

function setActiveChips() {
  $('favBtn').classList.toggle('active', state.view === 'favoritos');
  $('newsBtn').classList.toggle('active', state.view === 'novidades');
}

async function toggleFav(productId) {
  state.favs = await favorites.toggle(productId);
  updateFavCount();
  renderGrid();
}
function updateFavCount() { $('favCount').textContent = state.favs.size; }

// =============================================================
//  ADMIN — cadastro rápido (briefing §5.7)
// =============================================================
async function openAdmin() {
  const stores = await data.listStores();
  $('aStore').innerHTML = stores.map((s) => `<option value="${s.id}">${s.name}</option>`).join('');
  $('aCat').innerHTML = CATEGORIES.map((c) => `<option>${c}</option>`).join('');
  fillShipsFromStore(stores);
  $('aStore').onchange = () => fillShipsFromStore();
  renderEuroPick();
  $('adminPanel').classList.add('open');
}
function closeAdmin() { $('adminPanel').classList.remove('open'); }

let _storesCache = [];
async function fillShipsFromStore(stores) {
  if (stores) _storesCache = stores;
  const loja = _storesCache.find((s) => s.id === $('aStore').value);
  $('aShips').value = loja ? (loja.ships || []).join(', ') : '—';
  renderEuroPick(); // a moeda da faixa depende da região da loja
}

function storeRegion() {
  const loja = _storesCache.find((s) => s.id === $('aStore').value);
  return regionById(loja?.region || REGIONS[0].id);
}

function renderEuroPick() {
  const region = storeRegion();
  const bands = PRICE_BANDS[region.id] || PRICE_BANDS.europa;
  $('euroPick').innerHTML = bands.map((b) =>
    `<button data-lvl="${b.level}" class="${b.level === state.admin.price ? 'sel' : ''}" title="${b.label}">
       ${region.currency.repeat(b.level)}<span class="lvl-label">${b.label}</span>
     </button>`).join('');
  $('euroPick').querySelectorAll('button').forEach((b) => {
    b.onclick = () => { state.admin.price = +b.dataset.lvl; renderEuroPick(); };
  });
}

// Colar imagem (Ctrl+V) ou arrastar arquivo → preview (data URL no modo seed)
function setupPaste() {
  const zone = $('pasteZone');
  const showImg = (src) => {
    state.admin.image = src;
    zone.classList.add('has-img');
    zone.innerHTML = `<img src="${src}" alt="prévia">`;
  };
  const fileToImg = (file) => {
    const reader = new FileReader();
    reader.onload = (e) => showImg(e.target.result);
    reader.readAsDataURL(file);
  };
  zone.addEventListener('paste', (e) => {
    const item = [...(e.clipboardData?.items || [])].find((i) => i.type.startsWith('image/'));
    if (item) fileToImg(item.getAsFile());
  });
  zone.addEventListener('click', () => zone.focus());
  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('drag'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault(); zone.classList.remove('drag');
    const f = e.dataTransfer.files[0]; if (f && f.type.startsWith('image/')) fileToImg(f);
  });
  $('aImgUrl').addEventListener('input', (e) => {
    const url = e.target.value.trim();
    if (url) showImg(url);
  });
}

function resetPasteZone() {
  const zone = $('pasteZone');
  zone.classList.remove('has-img');
  zone.innerHTML = `<span class="hint"><b>Clique aqui e tecle Ctrl+V</b><br>para colar a imagem, ou arraste um arquivo</span>`;
  state.admin.image = '';
}

async function saveProduct(keepOpen) {
  const nome = $('aName').value.trim();
  const storeId = $('aStore').value;
  if (!nome || !storeId) { $('adminNote').textContent = 'Preencha pelo menos o nome e a loja.'; return; }

  await data.createProduct({
    nome,
    referencia: $('aRef').value.trim(),
    link: $('aLink').value.trim() || '#',
    imagem: state.admin.image || $('aImgUrl').value.trim(),
    storeId,
    categoria: $('aCat').value,
    faixaPreco: state.admin.price,
    novidade: $('aNew').checked,
    novidadeAte: $('aNew').checked ? ($('aNewUntil').value || '') : '',
  });

  state.products = await data.listProducts();
  showToast('Produto adicionado à curadoria ✓');

  if (keepOpen) {
    // "Salvar + próximo": limpa só o que muda, preserva loja/categoria/faixa.
    ['aName', 'aRef', 'aLink', 'aImgUrl'].forEach((id) => ($(id).value = ''));
    $('aNew').checked = false; $('aNewUntil').style.display = 'none';
    resetPasteZone();
    $('adminNote').textContent = '';
    $('aName').focus();
  } else {
    closeAdmin();
  }
  renderGrid();
}

// =============================================================
//  TOAST
// =============================================================
let toastTimer;
function showToast(msg) {
  const t = $('toast');
  t.textContent = msg; t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 2600);
}

// =============================================================
//  LIGAÇÕES (event listeners)
// =============================================================
function wireEvents() {
  $('loginBtn').onclick = doLogin;
  $('accessName').addEventListener('keydown', (e) => { if (e.key === 'Enter') doLogin(); });

  $('favBtn').onclick = () => setView('favoritos');
  $('newsBtn').onclick = () => setView('novidades');
  $('adminBtn').onclick = openAdmin;
  $('logoutBtn').onclick = async () => { await auth.logout(); location.reload(); };

  $('searchInput').addEventListener('input', (e) => { state.search = e.target.value; renderGrid(); });
  $('countrySelect').addEventListener('change', (e) => { state.country = e.target.value; renderGrid(); });

  $('legalLink').onclick = openLegalReadOnly;

  $('adminCloseBtn').onclick = closeAdmin;
  $('saveCloseBtn').onclick = () => saveProduct(false);
  $('saveNextBtn').onclick = () => saveProduct(true);
  $('aNew').addEventListener('change', (e) => {
    $('aNewUntil').style.display = e.target.checked ? '' : 'none';
  });

  setupPaste();
}

// =============================================================
//  INIT
// =============================================================
async function init() {
  wireEvents();
  // "Cadastrar produto" é só para a administradora/equipe — escondido do cliente.
  // No preview, acesse com ?admin=1 no fim do endereço. No Wix, virá da permissão real.
  const isAdmin = new URLSearchParams(location.search).get('admin') === '1';
  if (isAdmin) $('adminBtn').style.display = '';
  state.user = await auth.currentUser();
  if (state.user) {
    $('loginScreen').style.display = 'none';
    await afterLogin();
  }
}
init();
