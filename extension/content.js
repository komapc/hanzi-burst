(() => {
  const HAN = /[㐀-鿿]/, KANA = /[぀-ヿ]/, JP = /[぀-ヿ㐀-鿿]/;
  // Japanese: the text has kana, or the page / element is marked lang="ja" (kanji-only text otherwise counts as Chinese)
  const isJa = (text, node) => {
    if (KANA.test(text)) return true;
    const el = node && (node.nodeType === 1 ? node : node.parentElement);
    const l = (el && el.closest && el.closest('[lang]') || document.documentElement).getAttribute('lang') || '';
    return /^ja/i.test(l);
  };
  const autoLang = (navigator.language || '').startsWith('ru') ? 'ru' : 'en';
  let host = null, enabled = true, off = false, mode = 'select', langPref = 'auto', known = new Set(), last = null, rubyPref = false;
  const MODES = ['select', 'hover', 'alt'];                         // alt: hover, but only while Alt is held
  const lang = () => (langPref === 'auto' ? autoLang : langPref);
  const key = 'off:' + location.hostname;
  try {
    chrome.storage.local.get(['enabled', 'mode', 'lang', 'known', 'ruby', key], v => { known = new Set(v.known || []); langPref = v.lang || 'auto'; enabled = v.enabled !== false; mode = MODES.includes(v.mode) ? v.mode : 'select'; off = !!v[key]; rubyPref = !!v.ruby; applyRuby(); syncSite(); });
    chrome.storage.onChanged.addListener(ch => {
      if (ch.enabled) { enabled = ch.enabled.newValue !== false; applyRuby(); }
      if (ch.ruby) { rubyPref = !!ch.ruby.newValue; rubyTab = null; applyRuby(); }
      if (ch.known) { known = new Set(ch.known.newValue || []); if (host && last) render(last.r, last.rect, last.scroll); syncSite(); }
      if (ch.lang) langPref = ch.lang.newValue || 'auto';
      if (ch.mode) { mode = MODES.includes(ch.mode.newValue) ? ch.mode.newValue : 'select'; hide(); }
      if (ch[key]) { off = !!ch[key].newValue; applyRuby(); }
    });
  } catch (e) {}

  // ---- hanzi.lipu.dev: our list and the site's (localStorage hanzi-known) are merged both ways ----
  // knownBase is the list after the last merge: a character in it that is now missing on one side was unmarked there.
  // Runs on load, when our list changes, when the site saves its list and, as a fallback, when the tab is hidden.
  //
  // The site writes hanzi-known only on a user action (marking a character, saveKnown in site/index.html) or when a
  // signed-in user's list is synced from the server; learned.html only reads it. So a missing site list does not mean
  // "everything was unmarked":
  // - key absent (site data cleared, new browser profile, incognito): the site has no data. Our list is pushed to the
  //   site (union, nothing deleted), and an empty result is not written.
  // - key present but none of knownBase left in it: ambiguous (the user unmarked every character one by one, or the
  //   data was reset some other way). Treat it as a reset: union, nothing deleted. The one exception is a one-character
  //   knownBase right after the site saved its list (hanzi-known-saved): one save unmarks at most one character, so
  //   that is the user unmarking the last one. Trade-off: if the user unmarks everything on the site while the
  //   extension is not running there (disabled, or the event was missed), those characters come back from our list
  //   on the next visit and have to be unmarked again. Losing the whole list is worse than unmarking twice.
  // Normal unmarks are unaffected: one side drops a character that the other still has and knownBase still has.
  // The merge itself is mergeKnown in common.js (unit-tested in tests/js).
  function syncSite(ev) {
    if (location.hostname !== 'hanzi.lipu.dev') return;
    const siteSaved = !!ev && ev.type === 'hanzi-known-saved';
    let raw, site;
    try { raw = localStorage.getItem('hanzi-known'); site = raw === null ? null : JSON.parse(raw); } catch (e) { return; }
    if (site !== null && !Array.isArray(site)) return;
    try {
      chrome.storage.local.get(['known', 'knownBase'], v => {
        const ext = v.known || [];
        const out = mergeKnown(site, ext, v.knownBase || null, siteSaved);
        const O = new Set(out), same = a => a.length === O.size && a.every(c => O.has(c));
        if (!same(site || [])) {                                       // absent key + empty result: nothing to write
          try { localStorage.setItem('hanzi-known', JSON.stringify(out)); } catch (e) { return; }
          window.dispatchEvent(new Event('hanzi-known'));            // the site reloads its list (index.html, learned.html)
        }
        if (!same(ext) || !v.knownBase || !same(v.knownBase)) chrome.storage.local.set(same(ext) ? { knownBase: out } : { known: out, knownBase: out });
      });
    } catch (e) { /* extension reloaded */ }
  }
  window.addEventListener('hanzi-known-saved', syncSite);              // the site saved its list (site/index.html saveKnown)
  document.addEventListener('visibilitychange', () => { if (document.hidden) syncSite(); });

  const CSS = `:host{all:initial}
  *{box-sizing:border-box}
  .card{--bg:#faf7f2;--fg:#1f1b16;--muted:#6b6257;--card:#fff;--accent:#c8402a;--line:#cfc6b6;--soft:#e6dfd3;--ok:#2a7f51;--info:#2f6fd0;--warn:#d09a1f;
    position:fixed;z-index:2147483647;width:max-content;max-width:360px;max-height:min(80vh,640px);overflow:auto;
    background:var(--card);color:var(--fg);border:1px solid var(--soft);border-radius:16px;padding:6px 0 4px;
    box-shadow:0 12px 40px rgba(31,27,22,.22),0 2px 6px rgba(31,27,22,.1);
    font:14px/1.45 system-ui,"Noto Sans SC",sans-serif;animation:in .12s ease-out;scrollbar-width:thin;scrollbar-color:var(--line) transparent}
  @keyframes in{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
  @media(prefers-reduced-motion:reduce){.card{animation:none}}
  .row{padding:10px 16px}.row+.row{border-top:1px solid var(--soft)}
  .head{display:flex;align-items:center;gap:12px}
  button.tile,button.nt{cursor:pointer;color:inherit;padding:0;position:relative;transition:border-color .12s,background .12s}
  button.tile{padding:0 6px}
  button.tile:hover,button.nt:hover{border-color:var(--accent)}
  .st-known{border-color:var(--ok)!important;background:color-mix(in srgb,var(--ok) 16%,var(--bg))!important}
  .st-known:after,.st-allp:after,.st-somep:after{content:"";position:absolute;top:-4px;right:-4px;width:10px;height:10px;border-radius:50%;background:var(--ok);border:2px solid var(--card)}
  .st-allp:after{background:var(--info)}.st-somep:after{background:var(--warn)}
  .tile{flex:none;white-space:nowrap;display:inline-flex;align-items:center;justify-content:center;min-width:44px;height:44px;padding:0 6px;background:var(--bg);
    border:2px solid var(--line);border-radius:12px;font:28px/1 "Noto Serif SC","Songti SC",serif;letter-spacing:.04em}
  .word .tile{border-color:var(--accent)}
  .tile.l3{font-size:22px}.tile.l5{font-size:17px}
  .head>div{min-width:0}
  .py{font-weight:700;font-size:16px;color:var(--accent)}
  .def{color:var(--muted);margin-top:1px;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}
  .hint{margin-top:3px;font-size:13px;font-style:italic;color:var(--fg);opacity:.85}
  .tree{margin:8px 0 0 22px}
  .node{position:relative;padding-left:18px;margin-top:6px}
  .node:before{content:"";position:absolute;left:0;top:-6px;bottom:0;border-left:1.5px solid var(--line)}
  .node:last-child:before{bottom:auto;height:20px}
  .node:after{content:"";position:absolute;left:0;top:14px;width:14px;border-top:1.5px solid var(--line)}
  .nrow{display:flex;align-items:center;gap:8px;min-height:28px}
  .nt{flex:none;display:inline-flex;align-items:center;justify-content:center;min-width:28px;height:28px;background:var(--bg);
    border:1.5px solid var(--line);border-radius:8px;font:18px/1 "Noto Serif SC","Songti SC",serif}
  .nt.leaf{border-style:dashed}
  .nd{color:var(--muted);font-size:13px}
  .npy{color:var(--accent);font-weight:700;margin-right:6px}
  .foot{display:flex;justify-content:space-between;align-items:center;padding:8px 16px 6px;font-size:12px}
  .foot a{color:var(--accent);text-decoration:none;font-weight:600}.foot a:hover{text-decoration:underline}
  .foot button{all:unset;cursor:pointer;color:var(--muted);font-size:12px}.foot button:hover{color:var(--accent)}
  .card.ja .tile,.card.ja .nt{font-family:"Noto Serif JP","Hiragino Mincho ProN","Yu Mincho",serif}
  .trow{padding:8px 16px}.sent{font:17px/1.5 "Noto Serif SC","Songti SC",serif;margin-bottom:6px}.sent b{color:var(--accent);font-weight:700}.tr{font-size:15px;line-height:1.4}.mt{font-size:11px;color:var(--muted);margin-top:2px}
  .trb{all:unset;cursor:pointer;font-size:13px;font-weight:600;color:var(--accent);padding:4px 10px;border:1.5px solid var(--line);border-radius:999px}.trb:hover{border-color:var(--accent)}.trb[disabled]{opacity:.6;cursor:default}
  .legend{display:flex;gap:10px;padding:4px 16px 0;font-size:11px;color:var(--muted)}.legend i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:4px}
  @media(prefers-color-scheme:dark){.card{--bg:#17140f;--fg:#f1ebe0;--muted:#a59c8e;--card:#221e17;--accent:#ff7a5c;--line:#5a5144;--soft:#352f25;--ok:#5fcf93;--info:#6aa6ff;--warn:#e8b84a;
    box-shadow:0 12px 40px rgba(0,0,0,.6),0 2px 6px rgba(0,0,0,.4)}}`;
  const clean = s => String(s == null ? '' : s).replace(/\s*\[[^\]]*\d[^\]]*\]/g, '').trim();   // drop CC-CEDICT numeric-pinyin cross references
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const lbl = { en: { mark: 'Click: mark as known', unmark: 'Click: unmark', mine: 'My characters', known: 'known', all: 'all parts known', some: 'some parts known', tr: 'Translate phrase', trBusy: 'Translating…', trErr: 'Could not translate', trLimit: 'Daily translation limit reached', trNote: 'Sends the phrase to hanzi.lipu.dev (Gemini machine translation)', mt: 'machine translation', open: 'Open this on hanzi.lipu.dev' },
                ru: { mark: 'Клик: отметить как известный', unmark: 'Клик: снять отметку', mine: 'Мои иероглифы', known: 'знаю', all: 'знаю все части', some: 'знаю часть частей', tr: 'Перевести фразу', trBusy: 'Перевожу…', trErr: 'Не удалось перевести', trLimit: 'Лимит переводов на сегодня', trNote: 'Фраза уйдёт на hanzi.lipu.dev (машинный перевод Gemini)', mt: 'машинный перевод', open: 'Открыть это на hanzi.lipu.dev' } };
  // the site opens the same text: one character as its card (?open=), longer text as "Your own phrase" (?t=, up to 100)
  const siteUrl = r => {
    const t = [...(r.src || (r.word && r.word.w) || (r.chars && r.chars[0] && r.chars[0].ch) || '')], q = new URLSearchParams();
    if (t.length === 1 && !r.ja) q.set('open', t[0]); else if (t.length) q.set('t', t.slice(0, 100).join(''));
    q.set('mode', r.ja ? 'ja' : 'zh'); q.set('lang', lang());
    return 'https://hanzi.lipu.dev/?' + q;
  };
  const tip = ch => lbl[lang()][known.has(ch) ? 'unmark' : 'mark'];
  const tree = parts => (parts && parts.length ? `<div class="tree">${parts.map(p => { const st = stateOf(p, known); return `<div class="node"><div class="nrow"><button class="nt${p.parts.length ? '' : ' leaf'}${st ? ' st-' + st : ''}" data-ch="${esc(p.ch)}" title="${esc(tip(p.ch))}">${esc(p.ch)}</button><span class="nd">${p.py ? `<b class="npy">${esc(p.py)}</b>` : ''}${esc(p.def)}</span></div>${tree(p.parts)}</div>`; }).join('')}</div>` : '');

  function hide() { if (host) { host.remove(); host = null; } shown = ''; }
  let shown = '';

  function render(r, rect, scrollTo) {
    last = { r, rect, scroll: scrollTo || 0 };
    if (host) { host.remove(); host = null; }
    host = document.createElement('div');
    const root = host.attachShadow({ mode: 'closed' });
    const head = (big, py, def, c) => { const st = c ? stateOf(c, known) : ''; return `<div class="head">${c ? `<button class="tile${st ? ' st-' + st : ''}" data-ch="${esc(big)}" title="${esc(tip(big))}">${esc(big)}</button>` : `<span class="tile${[...big].length > 4 ? ' l5' : [...big].length > 2 ? ' l3' : ''}">${esc(big)}</span>`}<div><div class="py">${esc(py)}</div><div class="def" title="${esc(clean(def))}">${esc(clean(def))}</div>${c && c.hint ? `<div class="hint">💡 ${esc(c.hint.replace(/\u00a0/g, ' '))}</div>` : ''}</div></div>`; };
    let h = '';
    // phrase (3+ characters, not a single dictionary word): translation row first, by button (Kobi 2026-11-13)
    const L = lbl[lang()], phrase = r.src && [...r.src].length >= 3 && !(r.word && r.word.w === r.src);
    // hover: the sentence around the character is shown, the hovered word in bold (Kobi 2026-11-13)
    const sent = phrase && r.at != null ? (() => { const a = [...r.src], n = r.word ? [...r.word.w].length : r.ja && r.words && r.words[0] ? [...r.words[0].w].length : 1;
      return `<div class="sent">${esc(a.slice(0, r.at).join(''))}<b>${esc(a.slice(r.at, r.at + n).join(''))}</b>${esc(a.slice(r.at + n).join(''))}</div>`; })() : '';
    if (phrase) h += r.trans ? `<div class="row trow">${sent}<div class="tr">${esc(r.trans)}</div><div class="mt">${L.mt}</div></div>`
      : `<div class="row trow">${sent}<button id="trBtn" class="trb" title="${esc(L.trNote)}"${r.trBusy ? ' disabled' : ''}>${r.trBusy ? L.trBusy : r.trErr ? (r.trErr === 'limit' ? L.trLimit : L.trErr) : '⇄ ' + L.tr}</button></div>`;
    if (r.ja) {
      r.words.forEach(w => { h += `<div class="row word">${head(w.w, [w.reading !== w.w ? w.reading : '', w.tr].filter(Boolean).join(' · '), (w.lemma ? w.lemma + ' — ' : '') + w.def)}</div>`; });
      r.chars.forEach(c => { h += `<div class="row">${head(c.ch, [c.on, c.kun].filter(Boolean).join(' · '), c.def, c)}${tree(c.parts)}</div>`; });   // он (катакана) · кун
    }
    if (r.word) h += `<div class="row word">${head(r.word.w, r.word.pinyin, r.word.def)}</div>`;
    if (!r.ja) r.chars.forEach(c => { h += `<div class="row">${head(c.ch, c.pinyin, c.def, c)}${tree(c.parts)}</div>`; });
    h += `<div class="legend"><span><i style="background:var(--ok)"></i>${lbl[lang()].known}</span><span><i style="background:var(--info)"></i>${lbl[lang()].all}</span><span><i style="background:var(--warn)"></i>${lbl[lang()].some}</span></div>`;
    h += `<div class="foot"><button id="mine">★ ${lbl[lang()].mine} · ${known.size}</button><a href="${esc(siteUrl(r))}" target="_blank" rel="noopener" title="${esc(L.open)}">hanzi.lipu.dev ↗</a></div>`;
    const style = document.createElement('style'); style.textContent = CSS;
    const wrap = document.createElement('div'); wrap.className = 'card' + (r.ja ? ' ja' : ''); wrap.lang = r.ja ? 'ja' : 'zh';
    setHTML(wrap, h); root.append(style, wrap);
    document.documentElement.appendChild(host);
    const card = root.querySelector('.card');
    if (scrollTo != null) card.scrollTop = scrollTo;
    root.addEventListener('click', e => {
      const b = e.target.closest('button[data-ch]');
      if (b) { const c = b.dataset.ch; const k = new Set(known); k.has(c) ? k.delete(c) : k.add(c); known = k; last.scroll = card.scrollTop; try { chrome.storage.local.set({ known: [...k] }); } catch (err) {} render(last.r, last.rect, card.scrollTop); return; }
      if (e.target.closest('#trBtn') && !last.r.trBusy) {
        const rr = last.r; rr.trBusy = true; rr.trErr = null; render(rr, last.rect, card.scrollTop);
        try {
          chrome.runtime.sendMessage({ type: 'translate', text: rr.src, lang: lang() }, res => {
            rr.trBusy = false; if (res && res.tr) rr.trans = res.tr; else rr.trErr = (res && res.err) || 'fail';
            if (last && last.r === rr && host) render(rr, last.rect, 0);
          });
        } catch (err) { rr.trBusy = false; rr.trErr = 'fail'; }
        return;
      }
      if (e.target.closest('#mine')) { try { chrome.runtime.sendMessage({ type: 'open-learned' }); } catch (err) {} }
    });
    // below the text, else above; if neither fits, the roomier side with a shorter (scrolling) card.
    // The card must not cover the text: in hover mode the pointer would land on the card and the lookup would hide it.
    const w = card.offsetWidth, ch = card.offsetHeight, below = innerHeight - rect.bottom - 14, above = rect.top - 14;
    const x = Math.min(Math.max(8, rect.left), innerWidth - w - 8);
    let y;
    if (ch <= below || below >= above) { y = rect.bottom + 6; if (ch > below) card.style.maxHeight = Math.max(80, below) + 'px'; }
    else { if (ch > above) card.style.maxHeight = above + 'px'; y = rect.top - 6 - Math.min(ch, above); }
    card.style.left = x + 'px'; card.style.top = y + 'px';
  }

  // ---- mode: select ----
  // selected text without pinyin from <rt> (pinyin over text mode)
  const selText = sel => {
    if (!sel || !sel.rangeCount) return '';
    const f = sel.getRangeAt(0).cloneContents(); f.querySelectorAll('rt').forEach(r => r.remove());
    return f.textContent.trim();
  };
  async function onSelect(e, force) {
    if (!force && (!enabled || off || mode !== 'select')) return;
    if (host && e && e.composedPath().includes(host)) return;
    const sel = getSelection(); const text = selText(sel);
    if (!text || text.length > 40 || !JP.test(text)) return hide();
    const ja = isJa(text, sel.anchorNode);
    if (!ja && !HAN.test(text)) return hide();
    const rect = sel.getRangeAt(0).getBoundingClientRect();
    try {
      const r = await chrome.runtime.sendMessage({ type: 'lookup', text, lang: lang(), ja });
      if (r && selText(getSelection()) === text) { r.src = text; render(r, rect); }
    } catch (err) { /* extension reloaded */ }
  }
  // composedPath() is empty once dispatch is over, so clicks inside the card are filtered here, not in the timeout
  document.addEventListener('mouseup', e => { if (host && e.composedPath().includes(host)) return; setTimeout(() => onSelect(e), 10); });
  document.addEventListener('keyup', e => { if (e.key === 'Escape') hide(); else if (e.shiftKey) onSelect(e); });
  document.addEventListener('mousedown', e => { if (host && !e.composedPath().includes(host)) hide(); });
  document.addEventListener('scroll', hide, true);

  // ---- mode: hover ----
  // Character under the pointer plus the text that follows it (for word matching), and the character's box.
  function charAt(x, y) {
    let node, off;
    if (document.caretPositionFromPoint) { const p = document.caretPositionFromPoint(x, y); if (p) { node = p.offsetNode; off = p.offset; } }
    else if (document.caretRangeFromPoint) { const p = document.caretRangeFromPoint(x, y); if (p) { node = p.startContainer; off = p.startOffset; } }
    if (!node || node.nodeType !== 3) return null;
    let t = node.data, base = 0;
    const span = node.parentElement && node.parentElement.closest('[data-hb]');
    if (span && RUBY.has(span)) {                                   // pinyin over text: read on in the original string
      for (const ch of span.childNodes) { if (ch === node || ch.firstChild === node) break; base += (ch.nodeType === 3 ? ch.data : ch.firstChild.data).length; }
      t = RUBY.get(span);
    }
    for (const o of [off, off - 1]) {                              // caret sits between characters: try both neighbours
      if (o < 0 || o >= node.data.length || !JP.test(node.data[o])) continue;
      const r = document.createRange(); r.setStart(node, o); r.setEnd(node, o + 1);
      const b = r.getBoundingClientRect();
      const at = base + o;
      if (x >= b.left - 1 && x <= b.right + 1 && y >= b.top - 1 && y <= b.bottom + 1) return { text: t.slice(at, at + 12), rect: b, node, at, id: at + ':' + t.slice(at, at + 12) };
    }
    return null;
  }
  // Sentence around the hovered character: the text of its block (our pinyin spans read as their original text),
  // cut at sentence ends and at Latin text. "Goodbye - 再见 (zài jiàn)" gives 再见.
  function sentenceAt(node, at) {
    const span = node.parentElement && node.parentElement.closest('[data-hb]');
    const block = (span || node.parentElement).closest('p,li,td,th,dd,dt,h1,h2,h3,h4,h5,h6,blockquote,figcaption,div,section,article,body');
    let s = '', pos = -1;
    if (block) {
      const seen = new Set(), w = document.createTreeWalker(block, NodeFilter.SHOW_TEXT);
      for (let n; (n = w.nextNode()) && s.length < 4000;) {
        const el = n.parentElement; if (!el || el.closest('rt,script,style,noscript,textarea')) continue;
        const sp = el.closest('[data-hb]');
        if (sp && RUBY.has(sp)) { if (seen.has(sp)) continue; seen.add(sp); if (sp === span) pos = s.length + at; s += RUBY.get(sp); }
        else { if (n === node) pos = s.length + at; s += n.data; }
      }
    }
    if (pos < 0) { s = span && RUBY.has(span) ? RUBY.get(span) : node.data; pos = at; }
    return sentenceIn(s, pos);
  }
  let timer = 0, seq = 0, mx = -1, my0 = -1;
  document.addEventListener('mousemove', e => {
    mx = e.clientX; my0 = e.clientY;
    if (!enabled || off || !(mode === 'hover' || (mode === 'alt' && e.altKey))) return;
    clearTimeout(timer);
    if (host && e.composedPath().includes(host)) return;           // pointer is on the card: keep it
    hoverAt(e.clientX, e.clientY, 250);
  }, { passive: true });
  // Alt pressed with the pointer still: look up what is under it now
  document.addEventListener('keydown', e => { if (e.key === 'Alt' && mode === 'alt' && enabled && !off && mx >= 0) hoverAt(mx, my0, 0); });
  document.addEventListener('keyup', e => { if (e.key === 'Alt' && mode === 'alt' && host) e.preventDefault(); });   // Firefox: no menu bar
  function hoverAt(x, y, delay) {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      if (host && document.elementFromPoint(x, y) === host) return;   // pointer on the card: keep it
      const hit = charAt(x, y);
      if (!hit) return hide();
      if (hit.id === shown) return;
      const ja = isJa(hit.text, hit.node);
      if (!ja && !HAN.test(hit.text[0])) return hide();
      const my = ++seq;
      try {
        const r = await chrome.runtime.sendMessage({ type: 'lookup', text: hit.text, lang: lang(), hover: true, ja });
        if (my === seq && r) {
          const sn = sentenceAt(hit.node, hit.at);
          if (sn && [...sn.text].length >= 3) { r.src = sn.text; r.at = sn.at; }
          render(r, hit.rect); shown = hit.id;
        }
      } catch (err) {}
    }, delay);
  }

  // ---- pinyin over text: <ruby> per character, words split by the dictionary in the background ----
  // On for every page (popup switch, storage "ruby") or for this tab only (context menu). Japanese text gets furigana (ja.js).
  const RUBY = new Map();                                            // our <span data-hb> -> original text
  let rubyTab = null, rubyObs = null, rubyCount = 0, rubyBusy = false;
  const RUBY_MAX = 5000;                                             // text nodes per page: long feeds stop here
  const rubyOn = () => enabled && !off && (rubyTab == null ? rubyPref : rubyTab);
  const NO_RUBY = 'script,style,noscript,textarea,select,option,svg,ruby,rt,[data-hb]';
  function rubyNodes(root) {
    const out = [];
    if (root.nodeType === 3) root = root.parentNode && { nodes: [root] };
    if (!root) return out;
    const list = root.nodes || (() => {
      const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT), a = [];
      for (let n; (n = w.nextNode()) && a.length < 2000;) a.push(n);
      return a;
    })();
    for (const n of list) {
      const el = n.parentElement;
      if (!el || !HAN.test(n.data) || el.closest(NO_RUBY) || el.isContentEditable || (host && host.contains(n))) continue;
      out.push(n);
    }
    return out;
  }
  async function rubify(nodes) {
    for (let i = 0; i < nodes.length && rubyOn() && rubyCount < RUBY_MAX; i += 200) {
      const batch = nodes.slice(i, i + 200), texts = batch.map(n => n.data), ja = batch.map(n => isJa(n.data, n));
      let res;
      try { res = await chrome.runtime.sendMessage({ type: 'annotate', texts, ja }); } catch (err) { return; }
      if (!res || !rubyOn()) return;
      rubyBusy = true;
      batch.forEach((n, j) => {
        const segs = res[j];
        if (!segs || !n.isConnected || n.data !== texts[j] || !segs.some(x => x[1])) return;
        const span = document.createElement('span'); span.dataset.hb = 'ruby';
        for (const [txt, py] of segs) {
          if (!py) { span.append(txt); continue; }
          const r = document.createElement('ruby'), rt = document.createElement('rt');
          rt.textContent = py;
          rt.style.cssText = 'font-size:.55em;font-weight:400;font-style:normal;letter-spacing:0;text-transform:none;opacity:.8;user-select:none;-webkit-user-select:none';
          r.append(txt, rt); span.append(r);
        }
        n.replaceWith(span); RUBY.set(span, texts[j]); rubyCount++;
      });
      rubyBusy = false;
    }
  }
  function applyRuby() {
    if (!document.body) return;
    if (rubyOn()) {
      rubify(rubyNodes(document.body));
      if (!rubyObs) {
        let pend = [], t = 0;
        rubyObs = new MutationObserver(ms => {
          if (rubyBusy) return;
          ms.forEach(m => m.addedNodes.forEach(n => { if (!(n.dataset && n.dataset.hb)) pend.push(n); }));
          clearTimeout(t); t = setTimeout(() => { const p = pend; pend = []; rubify(p.flatMap(rubyNodes)); }, 400);
        });
        rubyObs.observe(document.body, { childList: true, subtree: true });
      }
    } else {
      if (rubyObs) { rubyObs.disconnect(); rubyObs = null; }
      for (const [span, text] of RUBY) if (span.isConnected) span.replaceWith(document.createTextNode(text));
      RUBY.clear(); rubyCount = 0;
    }
  }

  // ---- context menu (background.js): look up the selection / pinyin on this page ----
  chrome.runtime.onMessage.addListener(msg => {
    if (!msg) return;
    if (msg.type === 'ctx-look') onSelect(null, true);
    if (msg.type === 'ctx-ruby') { rubyTab = !rubyOn(); if (!enabled || off) rubyTab = false; applyRuby(); }
  });
})();
