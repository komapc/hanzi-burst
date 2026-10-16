/* Статические страницы /c/ и /p/: отмечаем знакомые иероглифы (hanzi-known из localStorage) —
   зелёная точка = знаю, синяя = знаю все части, жёлтая = знаю часть частей. Как в приложении. */
(function () {
  let known = new Set();
  try { known = new Set(JSON.parse(localStorage.getItem('hanzi-known') || '[]')); } catch (e) {}
  const links = [...document.querySelectorAll('a[data-c]')];
  if (!known.size || !links.length) return;
  fetch('/comps.json').then(r => r.json()).then(C => {
    const state = ch => {
      if (known.has(ch)) return 'known';
      let total = 0, got = 0;
      const walk = (c, covered, depth) => {
        const comps = C[c] || '';
        if (!comps || depth > 6) { total++; if (covered || known.has(c)) got++; return; }
        [...comps].forEach(x => walk(x, covered || known.has(x), depth + 1));
      };
      [...(C[ch] || '')].forEach(x => walk(x, known.has(x), 1));
      return !total || !got ? '' : got === total ? 'allp' : 'somep';
    };
    let any = false;
    links.forEach(a => { const s = state(a.dataset.c); if (s) { a.classList.add(s); any = true; } });
    const box = document.querySelector('.chs');
    if (any && box && /^\/c\/(index\.html)?$/.test(location.pathname)) {
      const lg = document.createElement('p'); lg.className = 'legend m';
      lg.innerHTML = '<span class="k">●</span> знаю / known <span class="a">●</span> знаю все части / all parts <span class="s">●</span> знаю часть / some parts';
      box.before(lg);
    }
  }).catch(() => {});
})();
