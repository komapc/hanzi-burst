// hanzi-burst API: Google-вход, список «известных», запоминалки через Gemini.
// Всё, что не /api/*, отдаётся статикой из site/ (см. wrangler.toml).

const SESSION_TTL = 60 * 60 * 24 * 30; // 30 дней
const json = (data, status = 200, headers = {}) =>
  new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json', ...headers } });

/* ---------- подписанная кука-сессия (HMAC-SHA256) ---------- */
const enc = new TextEncoder();
const b64 = buf => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const unb64 = s => Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/')), c => c.charCodeAt(0));

async function hmacKey(secret) {
  return crypto.subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign', 'verify']);
}
async function signSession(env, payload) {
  const body = b64(enc.encode(JSON.stringify(payload)));
  const sig = b64(await crypto.subtle.sign('HMAC', await hmacKey(env.SESSION_SECRET), enc.encode(body)));
  return `${body}.${sig}`;
}
async function readSession(env, request) {
  const m = /(?:^|;\s*)hb_session=([^;]+)/.exec(request.headers.get('Cookie') || '');
  if (!m) return null;
  const [body, sig] = m[1].split('.');
  if (!body || !sig) return null;
  const ok = await crypto.subtle.verify('HMAC', await hmacKey(env.SESSION_SECRET), unb64(sig), enc.encode(body));
  if (!ok) return null;
  const p = JSON.parse(new TextDecoder().decode(unb64(body)));
  return p.exp > Date.now() / 1000 ? p : null;
}
const cookie = (value, maxAge) =>
  `hb_session=${value}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${maxAge}`;

/* ---------- Google ID token ---------- */
async function verifyGoogle(env, credential) {
  // tokeninfo проверяет подпись и срок; aud сверяем сами.
  const r = await fetch('https://oauth2.googleapis.com/tokeninfo?id_token=' + encodeURIComponent(credential));
  if (!r.ok) return null;
  const t = await r.json();
  if (t.aud !== env.GOOGLE_CLIENT_ID) return null;
  if (!['accounts.google.com', 'https://accounts.google.com'].includes(t.iss)) return null;
  if (t.email_verified !== 'true' && t.email_verified !== true) return null;
  return { sub: t.sub, email: t.email, name: t.name };
}

/* ---------- LLM ---------- */
function promptFor({ ch, pinyin, meaning, parts, etymology, lang }) {
  const ru = lang === 'ru';
  return `${ru ? 'Ты помогаешь новичку запомнить китайский иероглиф.' : 'You help a beginner remember a Chinese character.'}
Character: ${ch}  Pinyin: ${pinyin}  Meaning: ${meaning}
Parts: ${parts.map(p => `${p.char} (${p.meaning})`).join(', ') || '—'}
Real etymology (from a dictionary): ${etymology || '—'}

${ru
  ? 'Придумай короткую (1–2 предложения) яркую запоминалку на русском: сюжет из частей, пусть даже смешной или глупый. Если есть подсказка про звук, свяжи её со звучанием. Не выдавай выдумку за реальную этимологию.'
  : 'Write a short (1–2 sentences), vivid mnemonic in English: a little story built from the parts, even a silly one. If there is a sound hint, tie it to the pronunciation. Do not present the invention as real etymology.'}
Ответ строго JSON / Reply strictly as JSON: {"mnemonic": "..."}`;
}

async function askGemini(env, prompt) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${env.GEMINI_MODEL}:generateContent`;
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-goog-api-key': env.GEMINI_API_KEY },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: { responseMimeType: 'application/json', temperature: 0.9, maxOutputTokens: 300 },
    }),
  });
  if (!r.ok) throw new Error('llm ' + r.status);
  const data = await r.json();
  const text = data.candidates?.[0]?.content?.parts?.[0]?.text || '';
  return JSON.parse(text).mnemonic;
}

/* ---------- маршруты ---------- */
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    if (path === '/api/config') return json({ googleClientId: env.GOOGLE_CLIENT_ID || null });

    if (path === '/api/me') {
      const s = await readSession(env, request);
      return json(s ? { id: s.sub, name: s.name, email: s.email } : null);
    }

    if (path === '/api/auth/google' && method === 'POST') {
      const { credential } = await request.json().catch(() => ({}));
      const u = credential && (await verifyGoogle(env, credential));
      if (!u) return json({ error: 'invalid_token' }, 401);
      await env.DB.prepare(
        'INSERT INTO users (id, email, name, created_at) VALUES (?1, ?2, ?3, ?4) ' +
        'ON CONFLICT(id) DO UPDATE SET email = ?2, name = ?3'
      ).bind(u.sub, u.email, u.name, Date.now()).run();
      const value = await signSession(env, { sub: u.sub, name: u.name, email: u.email, exp: Math.floor(Date.now() / 1000) + SESSION_TTL });
      return json({ id: u.sub, name: u.name, email: u.email }, 200, { 'Set-Cookie': cookie(value, SESSION_TTL) });
    }

    if (path === '/api/auth/logout' && method === 'POST') {
      return json({ ok: true }, 200, { 'Set-Cookie': cookie('', 0) });
    }

    // дальше нужна сессия
    const session = await readSession(env, request);
    if (!session) return json({ error: 'unauthorized' }, 401);
    const uid = session.sub;

    if (path === '/api/known' && method === 'GET') {
      const { results } = await env.DB.prepare('SELECT ch FROM known WHERE user_id = ?1').bind(uid).all();
      return json(results.map(r => r.ch));
    }
    if (path === '/api/known' && method === 'PUT') {
      // тело: {add: [...], remove: [...]}; значения только одиночные символы, не больше 500 за раз
      const body = await request.json().catch(() => ({}));
      const ok = a => Array.isArray(a) ? a.filter(c => typeof c === 'string' && [...c].length === 1).slice(0, 500) : [];
      const stmts = [
        ...ok(body.add).map(c => env.DB.prepare('INSERT OR IGNORE INTO known (user_id, ch, added_at) VALUES (?1, ?2, ?3)').bind(uid, c, Date.now())),
        ...ok(body.remove).map(c => env.DB.prepare('DELETE FROM known WHERE user_id = ?1 AND ch = ?2').bind(uid, c)),
      ];
      if (stmts.length) await env.DB.batch(stmts);
      return json({ ok: true });
    }

    if (path === '/api/explain' && method === 'POST') {
      const b = await request.json().catch(() => ({}));
      const lang = b.lang === 'en' ? 'en' : 'ru';
      if (typeof b.ch !== 'string' || [...b.ch].length !== 1) return json({ error: 'bad_char' }, 400);

      const cached = await env.DB.prepare('SELECT text FROM mnemonics WHERE ch = ?1 AND lang = ?2').bind(b.ch, lang).first();
      if (cached) return json({ mnemonic: cached.text, cached: true });

      const day = new Date().toISOString().slice(0, 10);
      const limit = parseInt(env.EXPLAIN_DAILY_LIMIT || '30', 10);
      const row = await env.DB.prepare(
        'INSERT INTO usage (user_id, day, n) VALUES (?1, ?2, 1) ON CONFLICT(user_id, day) DO UPDATE SET n = n + 1 RETURNING n'
      ).bind(uid, day).first();
      if (row.n > limit) return json({ error: 'rate_limited' }, 429);

      const clip = (s, n) => String(s || '').slice(0, n);
      const prompt = promptFor({
        ch: b.ch, lang,
        pinyin: clip(b.pinyin, 40), meaning: clip(b.meaning, 200), etymology: clip(b.etymology, 300),
        parts: (Array.isArray(b.parts) ? b.parts : []).slice(0, 8).map(p => ({ char: clip(p.char, 4), meaning: clip(p.meaning, 80) })),
      });
      try {
        const text = clip(await askGemini(env, prompt), 600);
        await env.DB.prepare('INSERT OR REPLACE INTO mnemonics (ch, lang, text, model, created_at) VALUES (?1, ?2, ?3, ?4, ?5)')
          .bind(b.ch, lang, text, env.GEMINI_MODEL, Date.now()).run();
        return json({ mnemonic: text, cached: false });
      } catch (e) {
        return json({ error: 'llm_failed' }, 502);
      }
    }

    return json({ error: 'not_found' }, 404);
  },
};
