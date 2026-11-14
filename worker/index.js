// hanzi-burst API: Google-вход, список «известных», запоминалки через Gemini.
// Всё, что не /api/*, отдаётся статикой из site/ (см. wrangler.toml).

const SESSION_TTL = 60 * 60 * 24 * 30; // 30 дней
const PROMPT_VERSION = 2;   // поднять при смене промпта: старые запоминалки перестанут показываться
const MAX_VARIANTS = 3;
const HAN = /^\p{Script=Han}$/u;
const json = (data, status = 200, headers = {}) =>
  new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json', 'X-Content-Type-Options': 'nosniff', ...headers } });
const isJson = request => /^application\/json\s*(;|$)/i.test(request.headers.get('Content-Type') || '');
// Запросы, что меняют данные вошедшего пользователя или тратят его лимит, — только со своих страниц.
// SameSite=Lax уже не даёт куку чужим сайтам, но соседние *.lipu.dev для браузера «тот же сайт». Без Origin
// (curl, старые браузеры) пропускаем: подделать его из браузера нельзя, а вне браузера куки и так нет.
const sameOrigin = request => { const o = request.headers.get('Origin'); return !o || o === new URL(request.url).origin; };
const COOKIE_WRITES = new Set(['/api/known', '/api/explain', '/api/auth/google', '/api/auth/logout']);
const today = () => new Date().toISOString().slice(0, 10);
// дневной счётчик: свой у каждого (user_id) и общий на сайт; у перевода и запоминалок счётчики раздельные
async function overLimit(env, key, all, limit) {
  const bump = id => env.DB.prepare(
    'INSERT INTO usage (user_id, day, n) VALUES (?1, ?2, 1) ON CONFLICT(user_id, day) DO UPDATE SET n = n + 1 RETURNING n'
  ).bind(id, today()).first();
  if ((await bump(key)).n > limit) return true;
  return (await bump(all)).n > parseInt(env.GLOBAL_DAILY_LIMIT || '300', 10);   // страхует бюджет на весь сайт
}

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
  if (!env.SESSION_SECRET) return null;   // вход ещё не настроен
  const m = /(?:^|;\s*)hb_session=([^;]+)/.exec(request.headers.get('Cookie') || '');
  if (!m) return null;
  const [body, sig] = m[1].split('.');
  if (!body || !sig) return null;
  // испорченная кука (не base64url, не JSON): atob/JSON.parse бросают — это «нет сессии», а не 500 на всём /api/*
  try {
    const ok = await crypto.subtle.verify('HMAC', await hmacKey(env.SESSION_SECRET), unb64(sig), enc.encode(body));
    if (!ok) return null;
    const p = JSON.parse(new TextDecoder().decode(unb64(body)));
    return p && p.exp > Date.now() / 1000 ? p : null;
  } catch (e) {
    return null;
  }
}
const cookie = (value, maxAge) =>
  `hb_session=${value}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${maxAge}`;

/* ---------- анонимный пользователь: хэш IP, без хранения самого адреса ---------- */
// IPv6: провайдер обычно выдаёт абоненту целую /64, и каждый адрес из неё считался бы отдельным клиентом
// (одна /64 выбрала бы весь общий дневной лимит). Поэтому для IPv6 считаем по префиксу /64.
// IPv4 хэшируется как раньше, байт в байт: сегодняшние счётчики не обнуляются.
function ipKey(ip) {
  if (!ip.includes(':')) return ip;
  const v4 = /(\d+\.\d+\.\d+\.\d+)$/.exec(ip);   // ::ffff:1.2.3.4 — это IPv4
  if (v4) return v4[1];
  const [h, t] = ip.toLowerCase().split('%')[0].split('::');
  const part = x => (x ? x.split(':') : []);
  const a = part(h), b = part(t);
  const groups = t === undefined ? a : [...a, ...Array(Math.max(0, 8 - a.length - b.length)).fill('0'), ...b];
  return groups.slice(0, 4).map(g => (parseInt(g, 16) || 0).toString(16)).join(':') + '::/64';
}
async function ipId(request) {
  const ip = ipKey(request.headers.get('CF-Connecting-IP') || 'unknown');
  const d = await crypto.subtle.digest('SHA-256', enc.encode('hanzi-burst:' + ip));
  return 'ip:' + b64(d).slice(0, 22);
}

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

/* ---------- данные иероглифа из шардов site/data/chars (строит build_shards.py) ---------- */
// Контекст для промпта берём только отсюда: текст от клиента попадал бы в общий кэш запоминалок.
const shardKey = ch => ch.codePointAt(0).toString(16).slice(0, -2);
async function loadChars(env, request, list) {
  const out = {};
  await Promise.all([...new Set(list.map(shardKey))].map(async k => {
    const r = await env.ASSETS.fetch(new URL(`/data/chars/${k}.json`, request.url));
    if (!r.ok) return;
    const d = await r.json();
    list.forEach(c => { if (d[c]) out[c] = d[c]; });
  }));
  return out;
}
async function charContext(env, request, ch, lang) {
  const c = (await loadChars(env, request, [ch]))[ch];
  if (!c) return null;
  const parts = (c.components || []).slice(0, 8);
  const pc = await loadChars(env, request, parts);
  const def = x => (x && ((lang === 'ru' && x.definition_ru) || x.definition)) || '';
  const et = c.etymology || {};
  return {
    pinyin: (c.pinyin || []).join(', '), meaning: def(c),
    etymology: (lang === 'ru' && et.hint_ru) || et.hint || '',
    parts: parts.map(p => ({ char: p, meaning: def(pc[p]).split(/[;,]/)[0].trim() })),
  };
}

/* ---------- LLM ---------- */
function promptFor({ ch, pinyin, meaning, parts, etymology, lang, avoid = [] }) {
  const ru = lang === 'ru';
  const data = `Character: ${ch}  Pinyin: ${pinyin}  Meaning: ${meaning}
Parts: ${parts.map(p => `${p.char} (${p.meaning})`).join(', ') || '—'}
Real etymology (from a dictionary): ${etymology || '—'}
${avoid.length ? `Already used (write something clearly different): ${avoid.map(x => '"' + x + '"').join(' | ')}` : ''}`;
  const rules = ru
    ? `Ты помогаешь новичку запомнить китайский иероглиф. Напиши ОДНУ запоминалку на русском.
Правила:
- 1–2 коротких предложения (до 35 слов): одна конкретная, яркая, слегка нелепая сценка.
- Используй ровно те части, что даны, и назови каждую по значению (знак можно дать в скобках). Не добавляй частей, которых нет в списке.
- Сценка должна приводить к значению иероглифа целиком (первое значение).
- Юмор через нелепую, но понятную картинку; без каламбуров, требующих знания китайского.
- Связь со звучанием (пиньинь) используй только если она получается естественно, иначе пропусти. Не натягивай.
- Не пиши «древние люди», «изначально», «этимология» и не выдавай выдумку за историю.
- Подсказку из словаря можно использовать как опору, но не пересказывай её дословно.`
    : `You help a beginner remember a Chinese character. Write ONE mnemonic in English.
Rules:
- 1–2 short sentences (up to 35 words): one concrete, vivid, slightly absurd little scene.
- Use exactly the parts given and name each by its meaning (the character may go in parentheses). Do not add parts that are not listed.
- The scene must lead to the meaning of the whole character (its first sense).
- Humor comes from a silly but clear picture; no puns that need knowledge of Chinese.
- Tie in the pronunciation (pinyin) only if it comes out naturally, otherwise skip it. Do not force it.
- Do not write "ancient people", "originally" or "etymology", and do not present the invention as history.
- You may lean on the dictionary hint, but do not retell it word for word.`;
  return `${rules}

${data}

Ответ строго JSON / Reply strictly as JSON: {"mnemonic": "..."}`;
}

async function askGemini(env, prompt, { field = 'mnemonic', temperature = 0.9, maxOutputTokens = 600 } = {}) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${env.GEMINI_MODEL}:generateContent`;
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-goog-api-key': env.GEMINI_API_KEY },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      // thinkingBudget 0: иначе «размышления» 2.5-flash съедают maxOutputTokens и ответ приходит пустым
      generationConfig: { responseMimeType: 'application/json', temperature, maxOutputTokens, thinkingConfig: { thinkingBudget: 0 } },
    }),
  });
  if (!r.ok) throw new Error('llm http ' + r.status + ' ' + (await r.text()).slice(0, 200));
  const data = await r.json();
  const text = data.candidates?.[0]?.content?.parts?.[0]?.text || '';
  try { return JSON.parse(text)[field]; } catch { throw new Error('llm bad json: ' + JSON.stringify(data).slice(0, 300)); }
}

/* ---------- маршруты ---------- */
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    // Google Search Console: файл подтверждения должен отдаваться по точному адресу, без редиректа на путь без .html
    const gv = path === '/googled1d667f41fecd0d0.html' ? [null, 'googled1d667f41fecd0d0.html'] : null;
    if (gv) return new Response('google-site-verification: ' + gv[1], { headers: { 'content-type': 'text/html; charset=utf-8' } });
    // Старый адрес *.workers.dev: страницы навсегда переезжают на основной домен, API продолжает работать
    if (url.hostname.endsWith('.workers.dev') && !path.startsWith('/api/')) {
      return Response.redirect('https://hanzi.lipu.dev' + path + url.search, 301);
    }
    // http:// на основном домене: навсегда на https (на случай, если «Always Use HTTPS» в зоне выключен).
    // Схему посетителя берём из CF-Visitor, который ставит край Cloudflare: в wrangler dev его нет, и URL там всегда http.
    if (url.hostname === 'hanzi.lipu.dev' && /"scheme":"http"/.test(request.headers.get('CF-Visitor') || '')) {
      url.protocol = 'https:';
      return Response.redirect(url.toString(), 301);
    }
    if (!path.startsWith('/api/')) {
      // ASSETS отвечает 307 на /japanese -> /japanese/ и /c/x.html -> /c/x; для поисковиков это постоянный адрес: 301
      // Несуществующие пути: 404 со страницей site/404.html (not_found_handling в wrangler.toml)
      const r = await env.ASSETS.fetch(request);
      if (r.status === 307 && r.headers.get('Location')) {
        return Response.redirect(new URL(r.headers.get('Location'), url).toString(), 301);
      }
      return r;
    }
    const method = request.method;
    if (method !== 'GET' && COOKIE_WRITES.has(path) && !sameOrigin(request)) return json({ error: 'forbidden_origin' }, 403);

    if (path === '/api/config') return json({ googleClientId: env.GOOGLE_CLIENT_ID || null });

    if (path === '/api/me') {
      const s = await readSession(env, request);
      return json(s ? { id: s.sub, name: s.name, email: s.email } : null);
    }

    if (path === '/api/auth/google' && method === 'POST') {
      // только application/json: обычная HTML-форма (text/plain, без CORS-preflight) не может войти за пользователя (login CSRF)
      if (!isJson(request)) return json({ error: 'unsupported_media_type' }, 415);
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

    // кэш запоминалок читается без входа: показываем уже придуманное всем
    if (path === '/api/mnemonics' && method === 'GET') {
      const ch = url.searchParams.get('ch') || '';
      const lang = url.searchParams.get('lang') === 'en' ? 'en' : 'ru';
      if (!HAN.test(ch)) return json({ error: 'bad_char' }, 400);
      const { results } = await env.DB.prepare(
        'SELECT variant, text FROM mnemonics WHERE ch = ?1 AND lang = ?2 AND prompt_version = ?3 ORDER BY variant'
      ).bind(ch, lang, PROMPT_VERSION).all();
      // no-cache: только что придуманная запоминалка должна быть видна и после перезагрузки (раньше max-age=60 её прятал)
      return json({ variants: results }, 200, { 'Cache-Control': 'no-cache' });
    }

    // сессия необязательна: без входа лимиты считаются по хэшу IP
    const session = await readSession(env, request);
    const uid = session ? session.sub : await ipId(request);

    if (path.startsWith('/api/known') && !session) return json({ error: 'unauthorized' }, 401);

    if (path === '/api/known' && method === 'GET') {
      const { results } = await env.DB.prepare('SELECT ch FROM known WHERE user_id = ?1').bind(uid).all();
      return json(results.map(r => r.ch));
    }
    if (path === '/api/known' && method === 'PUT') {
      if (!isJson(request)) return json({ error: 'unsupported_media_type' }, 415);
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
      if (!isJson(request)) return json({ error: 'unsupported_media_type' }, 415);
      const b = await request.json().catch(() => ({}));
      const lang = b.lang === 'en' ? 'en' : 'ru';
      if (typeof b.ch !== 'string' || !HAN.test(b.ch)) return json({ error: 'bad_char' }, 400);

      const read = async () => (await env.DB.prepare(
        'SELECT variant, text FROM mnemonics WHERE ch = ?1 AND lang = ?2 AND prompt_version = ?3 ORDER BY variant'
      ).bind(b.ch, lang, PROMPT_VERSION).all()).results;

      let have = await read();
      // уже есть и новый вариант не просили, либо упёрлись в максимум: LLM не нужен
      if ((have.length && !b.more) || have.length >= MAX_VARIANTS) return json({ variants: have, cached: true });
      const ctx = await charContext(env, request, b.ch, lang);
      if (!ctx) return json({ error: 'unknown_char', variants: have }, 400);

      if (await overLimit(env, uid, '*', parseInt(env.EXPLAIN_DAILY_LIMIT || '30', 10))) return json({ error: 'rate_limited', variants: have }, 429);

      const clip = (s, n) => String(s || '').slice(0, n);
      const prompt = promptFor({ ch: b.ch, lang, avoid: have.map(v => v.text), ...ctx });
      try {
        const text = clip(await askGemini(env, prompt), 600).trim();
        if (!text) throw new Error('empty');   // пустой ответ не сохраняем: он занял бы вариант навсегда
        // INSERT OR IGNORE: если параллельный запрос успел раньше, остаётся его вариант.
        // Номер считается по всем версиям промпта: первичный ключ их не различает, и номер
        // по текущей версии столкнулся бы со старой строкой, а оплаченный ответ пропал бы.
        // Потолок MAX_VARIANTS (по текущей версии) проверяется в том же запросе: два параллельных
        // запроса оба прошли проверку have.length выше, но вставит только тот, кто ещё влезает.
        await env.DB.prepare(
          'INSERT OR IGNORE INTO mnemonics (ch, lang, variant, text, model, prompt_version, created_by, created_at) ' +
          'SELECT ?1, ?2, (SELECT COALESCE(MAX(variant), 0) + 1 FROM mnemonics WHERE ch = ?1 AND lang = ?2), ?3, ?4, ?5, ?6, ?7 ' +
          'WHERE (SELECT COUNT(*) FROM mnemonics WHERE ch = ?1 AND lang = ?2 AND prompt_version = ?5) < ?8'
        ).bind(b.ch, lang, text, env.GEMINI_MODEL, PROMPT_VERSION, session ? uid : null, Date.now(), MAX_VARIANTS).run();
        return json({ variants: await read(), cached: false });
      } catch (e) {
        console.error('explain failed', e.message);
        return json({ error: 'llm_failed', variants: have }, 502);
      }
    }

    // Перевод всей фразы (по кнопке). Не кэшируется: фразы свои/случайные. Лимит на человека тот же, что у запоминалок.
    if (path === '/api/translate' && method === 'POST') {
      if (!isJson(request)) return json({ error: 'unsupported_media_type' }, 415);   // и сайт, и расширение шлют JSON
      const b = await request.json().catch(() => ({}));
      const lang = b.lang === 'en' ? 'en' : 'ru';
      const zh = typeof b.zh === 'string' ? b.zh.trim() : '';
      if (!zh || zh.length > 120 || !/[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}]/u.test(zh)) return json({ error: 'bad_text' }, 400);

      // общий счётчик свой ('t:*'): переводы больше не съедают дневной потолок запоминалок
      if (await overLimit(env, 't:' + uid, 't:*', parseInt(env.EXPLAIN_DAILY_LIMIT || '30', 10))) return json({ error: 'rate_limited' }, 429);

      const target = lang === 'ru' ? 'русский / Russian' : 'English';
      const prompt = `Переведи китайскую или японскую фразу на ${target}. Только перевод, без пояснений, транскрипции и комментариев. / Translate the Chinese or Japanese phrase into ${target}. Output the translation only, no explanations or romanization.

Фраза / Phrase: ${zh}

Ответ строго JSON / Reply strictly as JSON: {"translation": "..."}`;
      try {
        const text = String(await askGemini(env, prompt, { field: 'translation', temperature: 0.2, maxOutputTokens: 300 }) || '').slice(0, 400);
        if (!text) throw new Error('empty');
        return json({ translation: text });
      } catch (e) {
        console.error('translate failed', e.message);
        return json({ error: 'llm_failed' }, 502);
      }
    }

    return json({ error: 'not_found' }, 404);
  },
};
