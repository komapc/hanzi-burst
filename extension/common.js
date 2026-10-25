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
