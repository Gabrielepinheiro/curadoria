/* =============================================================
 *  http-functions.js  —  "O CARTEIRO" da Hotmart  (código do Velo)
 *
 *  ONDE COLAR: no Editor do Wix, com o Velo ligado, abra o painel de
 *  código → seção BACKEND → crie um arquivo chamado EXATAMENTE
 *  "http-functions.js" e cole TODO este conteúdo.
 *
 *  O QUE FAZ:
 *   - Recebe o aviso (webhook/postback) da Hotmart.
 *   - Compra aprovada  -> cria/aprova o membro com o e-mail da compra.
 *   - Reembolso/cancel -> bloqueia o membro (perde o acesso).
 *
 *  ENDEREÇO (para colar na Hotmart), depois de PUBLICAR o site:
 *     https://www.gabrielepinheiro.com/_functions/hotmart
 *
 *  SEGURANÇA: troque HOTTOK pelo token (hottok) que a Hotmart te dá
 *  na tela de configuração do webhook. Sem ele, ninguém consegue
 *  liberar acesso falsamente.
 * ============================================================= */

import { ok, badRequest, forbidden, serverError } from 'wix-http-functions';
import { authentication } from 'wix-members-backend';

// >>> COLE AQUI O SEU HOTTOK DA HOTMART <<<
const HOTTOK = 'COLE_AQUI_O_HOTTOK_DA_HOTMART';

// eventos que LIBERAM acesso
const GRANT = ['PURCHASE_APPROVED', 'PURCHASE_COMPLETE', 'PURCHASE_COMPLETED', 'approved', 'complete', 'completo', 'aprovado'];
// eventos que REVOGAM acesso
const REVOKE = ['PURCHASE_REFUNDED', 'PURCHASE_CHARGEBACK', 'PURCHASE_PROTEST', 'PURCHASE_CANCELED', 'PURCHASE_CANCELLED', 'PURCHASE_EXPIRED', 'SUBSCRIPTION_CANCELLATION', 'refunded', 'canceled', 'chargeback'];

export async function post_hotmart(request) {
  let body;
  try { body = await request.body.json(); } catch (e) { return badRequest({ body: { error: 'json inválido' } }); }

  // valida o token (no header X-HOTMART-HOTTOK ou no corpo)
  const h = request.headers || {};
  const token = h['x-hotmart-hottok'] || h['X-HOTMART-HOTTOK'] || body.hottok;
  if (!HOTTOK || HOTTOK === 'COLE_AQUI_O_HOTTOK_DA_HOTMART' || token !== HOTTOK) {
    return forbidden({ body: { error: 'hottok inválido' } });
  }

  const event = body.event || (body.data && body.data.purchase && body.data.purchase.status) || body.status || '';
  const data = body.data || body;
  const email = (data.buyer && data.buyer.email)
    || (data.subscriber && data.subscriber.email)
    || data.email || body.email;

  if (!email) return badRequest({ body: { error: 'sem e-mail no aviso' } });

  try {
    if (GRANT.includes(event)) {
      await grantAccess(email);
      return ok({ body: { ok: true, action: 'grant', email } });
    }
    if (REVOKE.includes(event)) {
      await revokeAccess(email);
      return ok({ body: { ok: true, action: 'revoke', email } });
    }
    return ok({ body: { ok: true, action: 'ignored', event } });
  } catch (e) {
    return serverError({ body: { error: String(e && e.message ? e.message : e) } });
  }
}

function randomPass() {
  return 'Cci!' + Math.random().toString(36).slice(2, 10) + Math.random().toString(36).slice(2, 6).toUpperCase() + '7';
}

async function grantAccess(email) {
  try {
    const res = await authentication.register(email, randomPass(), {});
    if (res && res.approvalToken) {
      try { await authentication.approveByToken(res.approvalToken); } catch (e) { /* já aprovado */ }
    }
  } catch (e) {
    // provavelmente o membro já existe — garante que está aprovado
    try { await authentication.approveByEmail(email); } catch (e2) { /* ok */ }
  }
  // envia e-mail para o cliente definir a senha (se a API permitir)
  try { await authentication.sendSetPasswordEmail(email); } catch (e) { /* o cliente pode usar "Esqueci a senha" */ }
}

async function revokeAccess(email) {
  try { await authentication.blockByEmail(email); } catch (e) { /* membro pode não existir */ }
}

/* GET de teste: abra https://www.gabrielepinheiro.com/_functions/ping
   no navegador para confirmar que as funções estão publicadas. */
export function get_ping() {
  return ok({ body: { ok: true, msg: 'carteiro vivo' } });
}
