const $ = id => document.getElementById(id);
const store = chrome.storage.local;

function seg(id, value, onPick) {
  const root = $(id);
  const mark = v => root.querySelectorAll('button').forEach(b => b.classList.toggle('on', b.dataset.v === v));
  root.onclick = e => { const b = e.target.closest('button'); if (b) { mark(b.dataset.v); onPick(b.dataset.v); } };
  mark(value);
}

chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
  let h = ''; try { h = new URL(tab.url).hostname; } catch (e) {}
  const key = 'off:' + h;
  if (h) $('host').textContent = h; else $('site').disabled = true;
  store.get(['enabled', 'mode', 'lang', 'known', 'ruby', key], v => {
    $('mine').textContent = '★ My characters · ' + (v.known || []).length;
    $('on').checked = v.enabled !== false;
    $('site').checked = !!v[key];
    $('ruby').checked = !!v.ruby;
    seg('mode', ['hover', 'alt'].includes(v.mode) ? v.mode : 'select', x => store.set({ mode: x }));
    seg('lang', v.lang || 'auto', x => store.set({ lang: x }));
  });
  $('on').onchange = () => store.set({ enabled: $('on').checked });
  $('ruby').onchange = () => store.set({ ruby: $('ruby').checked });
  $('site').onchange = () => h && store.set({ [key]: $('site').checked });
});
$('mine').onclick = () => { chrome.tabs.create({ url: chrome.runtime.getURL('learned.html') }); window.close(); };
