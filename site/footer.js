/* Общий футер для страниц без своего (about, privacy, extension, learned, /c/, /p/, /k/, /japanese/).
   Страница ставит <div id="sitefoot"></div> и подключает этот скрипт; на главной футер свой (index.html).
   Язык: data-l у <html> (extension), иначе lang страницы. */
(function () {
  const box = document.getElementById('sitefoot');
  if (!box) return;
  const html = document.documentElement;
  const RU = {
    tag: 'Учим китайские иероглифы через радикалы', explore: 'Разделы', project: 'Проект', more: 'Разделы, о проекте, источники',
    home: 'Главная', all: 'Все иероглифы', phrases: 'Все фразы', hsk: 'Иероглифы по HSK', radicals: '214 ключей', rgame: 'Игра: учим ключи', poster: 'Плакаты ключей (PDF)', learned: 'Мои иероглифы', ext: 'Расширение для Chrome и Firefox',
    kana: 'Кана (японская азбука)', kanji: 'Кандзи по классам', about: 'О проекте', privacy: 'Конфиденциальность', code: 'Исходный код', data: 'Источники данных'
  }, EN = {
    tag: 'Learn Chinese characters by radicals', explore: 'Explore', project: 'Project', more: 'Sections, about, data sources',
    home: 'Home', all: 'All characters', phrases: 'All phrases', hsk: 'HSK characters', radicals: '214 radicals', rgame: 'Radicals game', poster: 'Radicals posters (PDF)', learned: 'My characters', ext: 'Chrome & Firefox extension',
    kana: 'Kana (Japanese syllabaries)', about: 'About', privacy: 'Privacy', code: 'Source code', data: 'Data sources'
  };
  const li = (h, txt) => `<li><a href="${h}">${txt}</a></li>`;
  const css = `
.sfoot{margin:48px auto 0;padding:28px 0 32px;border-top:1px solid var(--soft,var(--line));color:var(--muted);font:14.4px/1.5 system-ui,sans-serif;text-align:left}
.sfoot .sgrid{display:grid;grid-template-columns:minmax(0,1.4fr) repeat(2,minmax(0,1fr));gap:28px 32px}
.sfoot b{color:var(--fg);font-size:1.05rem}
.sfoot .sbrand p{margin:6px 0 0;line-height:1.45;max-width:28ch}
.sfoot h2{margin:0 0 10px;font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;font-weight:600;color:var(--muted)}
.sfoot ul{list-style:none;margin:0;padding:0;display:grid;gap:7px}
.sfoot a{color:var(--fg);text-decoration:none;opacity:.85}
.sfoot a:hover{color:var(--accent);opacity:1}
.sfoot details{margin-top:26px;padding-top:16px;border-top:1px solid var(--soft,var(--line));font-size:.8rem}
.sfoot summary{cursor:pointer;list-style:none}
.sfoot summary::-webkit-details-marker{display:none}
.sfoot summary::before{content:"▸ "}
.sfoot details[open] summary::before{content:"▾ "}
.sfoot details p{line-height:1.6;margin:10px 0 0}
.sfoot details a{color:inherit;text-decoration:underline;text-decoration-color:var(--soft,var(--line))}
.sfoot.cmp{margin-top:28px;padding:14px 0 20px}.sfoot details.all{margin:0;padding:0;border:0;font-size:inherit}
.sfoot details.all>summary{color:var(--muted)}.sfoot details.all>.sgrid{margin-top:18px}
@media (max-width:640px){.sfoot .sgrid{grid-template-columns:1fr 1fr}.sfoot .sbrand{grid-column:1 / -1}}`;
  const st = document.createElement('style'); st.textContent = css; document.head.append(st);
  // data-compact (игра): футер свёрнут в одну строку, чтобы не быть выше самой игры
  const compact = 'compact' in box.dataset;
  const foot = document.createElement('footer'); foot.className = 'sfoot' + (compact ? ' cmp' : ''); box.replaceWith(foot);
  const render = () => {
    const T = (html.dataset.l || html.lang || 'ru').startsWith('ru') ? RU : EN;
    // по-английски ведём на /en/c/, /en/p/ и /en/hsk/
    const pre = T === EN ? '/en' : '';
    // разделы, что уже есть в шапке страницы (nav.tn), в футере не повторяем
    const inTop = new Set([...document.querySelectorAll('nav.tn a')].map(a => a.pathname));
    const links = [[pre + '/', T.home], [pre + '/c/', T.all], [pre + '/p/', T.phrases], [pre + '/hsk/', T.hsk], [pre + '/r/', T.radicals],
      ['/posters' + (T === EN ? '#en' : ''), T.poster], ['/radicals-game' + (T === EN ? '?lang=en' : ''), T.rgame], ['/learned', T.learned],
      ['/extension', T.ext], ['/japanese/', T.kana]].concat(T === EN ? [] : [['/k/', T.kanji]]);
    foot.innerHTML = `<div class="sgrid">
<div class="sbrand"><b>Hanzi Burst</b><p>${T.tag}</p><p><a href="https://lipu.dev/">lipu.dev</a></p></div>
<nav aria-label="${T.explore}"><h2>${T.explore}</h2><ul>${links.filter(([h]) => !inTop.has(h.split(/[?#]/)[0])).map(([h, t]) => li(h, t)).join('')}</ul></nav>
<nav aria-label="${T.project}"><h2>${T.project}</h2><ul>${li('/about', T.about) + li('/privacy', T.privacy) + li('https://github.com/komapc/hanzi-burst', T.code)}</ul></nav>
</div><details><summary>${T.data}</summary><p><a href="https://github.com/skishore/makemeahanzi">Make Me a Hanzi</a> (LGPL, Arphic) · <a href="https://cc-cedict.org/">CC-CEDICT</a> (CC BY-SA) · <a href="https://tatoeba.org/">Tatoeba</a> (CC BY 2.0 FR) · <a href="https://en.wiktionary.org/">Wiktionary</a> via <a href="https://kaikki.org/">kaikki.org</a> (CC BY-SA) · <a href="https://commonvoice.mozilla.org/">Mozilla Common Voice</a> (CC0) · Unicode / Unihan · <a href="https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project">JMdict</a> (EDRDG, CC BY-SA 4.0) via <a href="https://github.com/scriptin/jmdict-simplified">jmdict-simplified</a> · <a href="https://www.edrdg.org/wiki/index.php/KANJIDIC_Project">KANJIDIC2</a> (EDRDG, CC BY-SA 4.0) · <a href="https://kanjivg.tagaini.net/">KanjiVG</a> (Ulrich Apel, CC BY-SA 3.0)</p></details>`;
  };
  const draw = () => {
    render();
    if (compact) foot.innerHTML = `<details class="all"><summary>Hanzi Burst · ${((html.dataset.l || html.lang || 'ru').startsWith('ru') ? RU : EN).more}</summary>${foot.innerHTML}</details>`;
  };
  draw();
  new MutationObserver(draw).observe(html, { attributes: true, attributeFilter: ['lang', 'data-l'] });   // переключатель RU/EN (/extension, «Мои иероглифы», игра)
})();
