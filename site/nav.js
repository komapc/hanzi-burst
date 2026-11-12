/* Общая шапка для страниц без своей: «Мои иероглифы», игра, расширение, о проекте, конфиденциальность, кана, 404.
   Страница ставит в начале <main> <nav class="tn" id="sitenav">[свой переключатель RU/EN]</nav><script src="/nav.js"></script>
   (синхронно, чтобы шапка не сдвигала страницу). Разделы те же, что в шапке статических страниц (build_static.page)
   и на главной (UI.nav в index.html) — меняйте их вместе. Язык: data-l у <html> (extension), иначе lang страницы. */
(function () {
  const nav = document.getElementById('sitenav');
  if (!nav) return;
  const html = document.documentElement;
  const NAV = {
    ru: [['/', 'Фразы'], ['/r/', 'Ключи'], ['/c/', 'Иероглифы'], ['/hsk/', 'HSK'], ['/radicals-game', 'Игра'], ['/learned', 'Мои иероглифы']],
    en: [['/?lang=en', 'Phrases'], ['/en/r/', 'Radicals'], ['/en/c/', 'Characters'], ['/en/hsk/', 'HSK'], ['/radicals-game?lang=en', 'Game'], ['/learned', 'My characters']]
  };
  const css = `
.tn{display:flex;align-items:center;gap:10px;margin:0 0 14px;padding-bottom:10px;border-bottom:1px solid var(--line,#cfc6b6);font:16px/1.4 system-ui,sans-serif}
.tn a{text-decoration:none;white-space:nowrap}.tn .tb{font-weight:600;color:var(--fg)}
.tn .ts{display:flex;gap:4px;flex:1;min-width:0;overflow-x:auto;scrollbar-width:none}.tn .ts::-webkit-scrollbar{display:none}
.tn .ts a{padding:3px 10px;border-radius:999px;font-size:15px;color:var(--accent)}
.tn .ts a:hover{background:color-mix(in srgb,var(--accent) 10%,transparent)}.tn .ts a.on{background:var(--accent);color:var(--bg)}
.tq{margin:0;display:flex}.tq input{width:34px;height:30px;box-sizing:border-box;padding:0 8px 0 28px;border:1px solid var(--line,#cfc6b6);border-radius:999px;
  background:transparent url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23888' stroke-width='2.4' stroke-linecap='round'%3E%3Ccircle cx='11' cy='11' r='7'/%3E%3Cpath d='m20 20-3.5-3.5'/%3E%3C/svg%3E") 9px 50%/15px no-repeat;
  color:var(--fg);font:inherit;font-size:15px;transition:width .15s;cursor:pointer}
.tq input:focus,.tq input:not(:placeholder-shown){width:150px;outline:none;border-color:var(--accent);cursor:text}
.tq input::placeholder{color:transparent}.tq input:focus::placeholder{color:var(--muted,#888)}
.tq input::-webkit-search-cancel-button{display:none}
.tn .lang,.tn #lang{display:inline-flex;flex:none;margin:0;padding:2px;border:1px solid var(--line,#cfc6b6);border-radius:999px}
.tn .lang button,.tn #lang button{border:0;border-radius:999px;padding:3px 9px;font:inherit;font-size:13px;background:none;color:var(--muted,#888);cursor:pointer}
.tn .lang button.on,.tn #lang button.on{background:var(--accent);color:var(--bg)}
@media(max-width:520px){.tn{gap:6px;flex-wrap:wrap}.tq{margin-left:auto}.tn .tb{font-size:14px}.tn .ts{order:9;flex:1 0 100%;-webkit-mask-image:linear-gradient(90deg,#000 85%,transparent);mask-image:linear-gradient(90deg,#000 85%,transparent)}
  .tn .ts a{padding:3px 8px;font-size:14px}.tn .ts::after{content:"";flex:0 0 36px}.tq input:focus,.tq input:not(:placeholder-shown){width:120px}}
@media(pointer:coarse){.tn .ts a{display:inline-flex;align-items:center;min-height:40px;box-sizing:border-box}.tq input{width:40px;height:40px}}`;
  const st = document.createElement('style'); st.textContent = css; document.head.append(st);
  // свой переключатель языка страницы (если есть) остаётся последним элементом шапки, его обработчики не трогаем
  const own = [...nav.children];
  const brand = document.createElement('a'); brand.className = 'tb';
  const ts = document.createElement('span'); ts.className = 'ts';
  const form = document.createElement('form'); form.className = 'tq'; form.action = '/'; form.setAttribute('role', 'search');
  nav.prepend(brand, ts, form);
  const here = location.pathname.replace(/\.html$/, '').replace(/\/index$/, '/');
  const render = () => {
    const en = !(html.dataset.l || html.lang || 'ru').startsWith('ru');
    brand.href = en ? '/?lang=en' : '/'; brand.textContent = 'Hanzi Burst';
    ts.innerHTML = NAV[en ? 'en' : 'ru'].map(([h, t]) => {
      const p = h.split('?')[0];
      const on = p !== '/' && (p.endsWith('/') ? here.startsWith(p) : here === p);
      return `<a href="${h}"${on ? ' class="on" aria-current="page"' : ''}>${t}</a>`;
    }).join('');
    form.innerHTML = `<input type="search" name="q" placeholder="${en ? '想 / xiang' : '想, xiang, сян'}" aria-label="${en ? 'Find a character' : 'Найти иероглиф'}" autocomplete="off" spellcheck="false" enterkeyhint="search">`
      + (en ? '<input type="hidden" name="lang" value="en">' : '');
    own.forEach(x => nav.append(x));
    const o = ts.querySelector('.on'); if (o) ts.scrollLeft = o.offsetLeft - ts.offsetLeft - (ts.clientWidth - o.offsetWidth) / 2;   // по центру, не в затухании
  };
  render();
  new MutationObserver(render).observe(html, { attributes: true, attributeFilter: ['lang', 'data-l'] });
})();
