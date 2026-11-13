// Shared by the service worker, the content script and the "My characters" page.
const IDS_OP = /[⿰-⿻]/;
const shardKey = ch => ch.codePointAt(0).toString(16).slice(0, -2);
const _shards = {};
const shard = (kind, k) => _shards[kind + k] || (_shards[kind + k] =
  fetch(chrome.runtime.getURL(`data/${kind}/${k}.json`)).then(r => (r.ok ? r.json() : {})).catch(() => ({})));

// Replace the children of el with markup built from escaped strings. DOMParser, not innerHTML: parsed nodes are inert
// (no scripts, no handlers run while parsing), which is what addons.mozilla.org review asks for.
function setHTML(el, html) {
  const body = new DOMParser().parseFromString(`<body>${html}</body>`, 'text/html').body;
  el.replaceChildren(...body.childNodes);
}

// Direct parts of a character from its IDS string; null when unknown or incomplete (a "？" hole).
function partsOf(ch, c) {
  if (!c || c.incomplete || c.radical === ch) return null;       // radicals are never split
  const d = c.decomposition || '';
  if (!d || /[？①-⑳]/.test(d)) return null;
  const p = [...d].filter(x => !IDS_OP.test(x));
  return p.length && !p.includes(ch) ? p : null;
}

// Progress state of a tree node {ch, parts:[]} given a Set of known characters:
// 'known' | 'allp' (every leaf part known) | 'somep' (some leaf parts known) | ''.
function stateOf(node, known) {
  if (known.has(node.ch)) return 'known';
  let total = 0, got = 0;
  const walk = (n, cov) => {
    if (!n.parts.length) { total++; if (cov || known.has(n.ch)) got++; return; }
    n.parts.forEach(x => walk(x, cov || known.has(x.ch)));
  };
  node.parts.forEach(x => walk(x, known.has(x.ch)));
  return !total || !got ? '' : got === total ? 'allp' : 'somep';
}

// Merge the site's and the extension's known lists (content.js syncSite; the reasoning is in the comment there).
function mergeKnown(site, ext, base, siteSaved) {   // site: array, or null when the key is absent; base: array or null
  const S = new Set(site || []), E = new Set(ext);
  let B = base ? new Set(base) : null;
  if (B && B.size && (site === null || (![...B].some(c => S.has(c)) && !(siteSaved && B.size === 1)))) B = null;
  return [...new Set([...ext, ...S])].filter(c => !B || !B.has(c) || (S.has(c) && E.has(c)));
}

// Sentence around position pos of s, cut at sentence ends (kept) and at Latin text, at most 100 characters:
// { text, at } (at: the position inside text, in code points), or null. "Goodbye - 再见 (zài jiàn)" gives 再见.
const IN_S = /[\u3000-\u3001\u3003-\u303f\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff\uff01-\uff60\s0-9·—“”‘’…]/, END_S = /[。！？!?；;…]/;
function sentenceIn(s, pos) {
  const ok = c => IN_S.test(c) && !END_S.test(c);
  let i = pos, j = pos + 1;
  while (i > 0 && ok(s[i - 1]) && s[i - 1] !== '\n') i--;
  while (j < s.length && ok(s[j]) && s[j] !== '\n') j++;
  while (j < s.length && END_S.test(s[j])) j++;                     // keep the sentence's own 。？！
  while (j < s.length && /[”’」』）》]/.test(s[j])) j++;                // and the quote it closes
  while (i < pos && /[\s，、。：；）」』》”’]/.test(s[i])) i++;      // no leading spaces or closing punctuation
  const out = s.slice(i, j).replace(/\s+$/, '');
  return out.length > 100 ? null : { text: out, at: [...s.slice(i, pos)].length };
}

// Node tests (tests/js) load this file directly.
if (typeof module !== 'undefined') module.exports = { shardKey, partsOf, stateOf, mergeKnown, sentenceIn };
