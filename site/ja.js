/* Японский текст: сегментация по словарю JMdict (шарды site/data/ja/), снятие спряжений,
   чтение словами + ромадзи (Хэпбёрн) и кириллица (Поливанов). Подключается из index.html. */
window.JA = (() => {
  const KANA = /[぀-ヿ]/, HAN = /[㐀-鿿]/, JP = /[぀-ヿ㐀-鿿々〆ヶ]/;
  const isJapanese = s => KANA.test(s);
  const shardOf = ch => KANA.test(ch) ? 'k' + ch.codePointAt(0).toString(16) : ch.codePointAt(0).toString(16).slice(0, -2);
  const toHira = s => s.replace(/[ァ-ヶ]/g, c => String.fromCharCode(c.charCodeAt(0) - 0x60));

  /* ---------- снятие спряжений ----------
     Правило: [окончание формы, окончание словарной формы, класс результата, класс входа ('' = любая форма)].
     Классы: v1 (ichidan), v5 (godan), vs (する), vk (来る), adj-i. Производные формы (могу/заставляю/меня...)
     сами спрягаются как v1, поэтому снимаются в два шага: 食べられない → 食べられる → 食べる. */
  const RULES = [];
  const add = (from, to, cls, inCls = '', imp = false) => RULES.push([from, to, cls, inCls, imp]);
  const MASU = ['ます', 'ました', 'ません', 'ませんでした', 'ましょう', 'まして', 'たい', 'たかった', 'たくない', 'たくなかった', 'たくて', 'ながら', 'なさい'];
  const NAI = ['ない', 'なかった', 'なくて', 'なければ', 'ず', 'ずに'];
  // godan: словарное окончание → [i-основа, a-основа, e-основа, o-основа, て, た]
  const GODAN = {
    'う': ['い', 'わ', 'え', 'お', 'って', 'った'], 'く': ['き', 'か', 'け', 'こ', 'いて', 'いた'], 'ぐ': ['ぎ', 'が', 'げ', 'ご', 'いで', 'いだ'],
    'す': ['し', 'さ', 'せ', 'そ', 'して', 'した'], 'つ': ['ち', 'た', 'て', 'と', 'って', 'った'], 'ぬ': ['に', 'な', 'ね', 'の', 'んで', 'んだ'],
    'ぶ': ['び', 'ば', 'べ', 'ぼ', 'んで', 'んだ'], 'む': ['み', 'ま', 'め', 'も', 'んで', 'んだ'], 'る': ['り', 'ら', 'れ', 'ろ', 'って', 'った'],
  };
  // 行く: て-форма неправильная; правило раньше общего, иначе 行った читается как 行う
  add('いって', 'いく', 'v5'); add('いった', 'いく', 'v5'); add('行って', '行く', 'v5'); add('行った', '行く', 'v5');
  for (const [u, [i, a, e, o, te, ta]] of Object.entries(GODAN)) {
    MASU.forEach(s => add(i + s, u, 'v5'));
    NAI.forEach(s => add(a + s, u, 'v5'));
    [te, ta, ta + 'ら', ta + 'り', te + 'も'].forEach(s => add(s, u, 'v5'));
    add(e + 'ば', u, 'v5'); add(o + 'う', u, 'v5'); add(e, u, 'v5', '', true);               // 書けば, 書こう, 書け
    // потенциал 書ける, пассив, каузатив: и сами по себе (泳げる), и как основа дальнейших форм (泳げない)
    for (const inCls of ['', 'v1']) { add(e + 'る', u, 'v5', inCls); add(a + 'れる', u, 'v5', inCls); add(a + 'せる', u, 'v5', inCls); }
  }
  // ichidan: основа = словарная форма без る
  [...MASU, ...NAI, 'て', 'た', 'たら', 'たり', 'ても', 'れば', 'よう', 'ろ'].forEach(s => add(s, 'る', 'v1'));
  for (const inCls of ['', 'v1']) { add('られる', 'る', 'v1', inCls); add('させる', 'る', 'v1', inCls); }
  // する и 来る
  for (const [stem, base, cls] of [['し', 'する', 'vs'], ['き', 'くる', 'vk'], ['来', '来る', 'vk']]) {
    MASU.forEach(s => add(stem + s, base, cls));
    ['て', 'た', 'たら', 'たり', 'ても'].forEach(s => add(stem + s, base, cls));
  }
  NAI.forEach(s => { add('し' + s, 'する', 'vs'); add('こ' + s, 'くる', 'vk'); add('来' + s, '来る', 'vk'); });
  [['しよう', 'する', 'vs'], ['すれば', 'する', 'vs'], ['される', 'する', 'vs', 'v1'], ['させる', 'する', 'vs', 'v1'], ['できる', 'する', 'vs', 'v1'],
   ['こよう', 'くる', 'vk'], ['くれば', 'くる', 'vk'], ['こられる', 'くる', 'vk', 'v1'], ['来よう', '来る', 'vk'], ['来れば', '来る', 'vk'], ['来られる', '来る', 'vk', 'v1']]
    .forEach(r => add(...r));
  // i-прилагательные
  ['く', 'くない', 'くなかった', 'かった', 'くて', 'ければ', 'さ', 'そう', 'くありません'].forEach(s => add(s, 'い', 'adj-i'));
  [['でした', 'です'], ['でしょう', 'です'], ['だった', 'だ'], ['だろう', 'だ'], ['でしたら', 'です']].forEach(([f, t]) => add(f, t, 'cop'));
  add('なかった', 'ない', 'adj-i'); add('なくて', 'ない', 'adj-i');                 // ない как прилагательное

  const posMatch = (pos, cls) => pos.split(' ').some(p =>
    cls === 'v5' ? p.startsWith('v5') : cls === 'v1' ? p.startsWith('v1') : cls === 'vs' ? p.startsWith('vs') : cls === 'adj-i' ? p.startsWith('adj-i') : p === cls);

  // Все словарные формы, к которым сводится s: [{base, cls, depth}]
  function deinflect(s) {
    const out = [], seen = new Set([s + '|']);
    let level = [{ base: s, cls: '' }];
    for (let depth = 0; depth < 3 && level.length; depth++) {
      const next = [];
      for (const c of level) for (const [from, to, cls, inCls, imp] of RULES) {
        if (!c.base.endsWith(from) || c.base.length - from.length + to.length < 1) continue;
        if (inCls !== c.cls) continue;                                              // производные формы — только с шага v1
        const base = c.base.slice(0, c.base.length - from.length) + to, k = base + '|' + cls;
        if (seen.has(k) || !base) continue;
        seen.add(k); const r = { base, cls, imp }; out.push(r); next.push(r);
      }
      level = next;
    }
    return out;
  }

  /* ---------- чтение формы ---------- */
  function readingOf(surface, base, baseReading, pos) {
    if (surface === base) return baseReading;
    let k = 0; while (k < surface.length && k < base.length && surface[k] === base[k]) k++;
    let head = baseReading.slice(0, baseReading.length - (base.length - k));
    if (/vk/.test(pos) && base.startsWith('来')) {                                   // 来る: く/き/こ по следующему знаку
      const nx = surface[1] || '';
      head = /[なよら]/.test(nx) ? 'こ' : nx === 'れ' ? 'く' : 'き';
      return head + surface.slice(1);
    }
    return head + surface.slice(k);
  }

  /* ---------- кана → латиница / кириллица ---------- */
  const ROW = { '': 'aiueo', k: 'かきくけこ', s: 'さしすせそ', t: 'たちつてと', n: 'なにぬねの', h: 'はひふへほ', m: 'まみむめも',
    r: 'らりるれろ', g: 'がぎぐげご', z: 'ざじずぜぞ', d: 'だぢづでど', b: 'ばびぶべぼ', p: 'ぱぴぷぺぽ' };
  const LAT = {}, CYR = {};
  const V = 'aiueo', CV = 'аиуэо';
  'あいうえお'.split('').forEach((c, i) => { LAT[c] = V[i]; CYR[c] = CV[i]; });
  const CYRC = { k: 'к', s: 'с', t: 'т', n: 'н', h: 'х', m: 'м', r: 'р', g: 'г', z: 'дз', d: 'д', b: 'б', p: 'п' };
  for (const [cons, kana] of Object.entries(ROW)) if (cons) kana.split('').forEach((c, i) => { LAT[c] = cons + V[i]; CYR[c] = CYRC[cons] + CV[i]; });
  Object.assign(LAT, { し: 'shi', ち: 'chi', つ: 'tsu', ふ: 'fu', じ: 'ji', ぢ: 'ji', づ: 'zu', や: 'ya', ゆ: 'yu', よ: 'yo', わ: 'wa', を: 'o', ん: 'n', ゐ: 'i', ゑ: 'e', ゔ: 'vu' });
  Object.assign(CYR, { し: 'си', ち: 'ти', つ: 'цу', ふ: 'фу', じ: 'дзи', ぢ: 'дзи', づ: 'дзу', ず: 'дзу', す: 'су', や: 'я', ゆ: 'ю', よ: 'ё', わ: 'ва', を: 'о', ん: 'н', ゐ: 'и', ゑ: 'э', ゔ: 'ву' });
  const SMALL = { ゃ: ['ya', 'я'], ゅ: ['yu', 'ю'], ょ: ['yo', 'ё'] };
  const SMALLV = { ぁ: 'a', ぃ: 'i', ぅ: 'u', ぇ: 'e', ぉ: 'o' };
  const MACRON = { a: 'ā', i: 'ī', u: 'ū', e: 'ē', o: 'ō' };
  const CMAC = '̄';

  // Кана → массив слогов [{lat, cyr}] с учётом ゃゅょ, っ, ー
  function syllables(kana) {
    const s = [...toHira(kana)], out = [];
    for (let i = 0; i < s.length; i++) {
      const c = s[i], n = s[i + 1];
      if (c === 'ー') { const p = out[out.length - 1]; if (p) { p.lat = p.lat.replace(/[aiueo]$/, v => MACRON[v]); p.cyr += CMAC; } continue; }
      if (c === 'っ') { out.push({ sokuon: true }); continue; }
      if (!LAT[c]) { out.push({ lat: c, cyr: c }); continue; }
      if (n && SMALL[n]) {
        const [l, cy] = SMALL[n];
        let lat = /^(shi|chi|ji)$/.test(LAT[c]) ? LAT[c].slice(0, -1) + l.slice(1) : LAT[c].slice(0, -1) + l;
        if (LAT[c] === 'ji') lat = 'j' + l.slice(1);
        const cyr = CYR[c].slice(0, -1) + cy;
        out.push({ lat, cyr }); i++; continue;
      }
      if (n && SMALLV[n]) { out.push({ lat: LAT[c].slice(0, -1) + SMALLV[n], cyr: CYR[c].slice(0, -1) + CYR[{ a: 'あ', i: 'い', u: 'う', e: 'え', o: 'お' }[SMALLV[n]]] }); i++; continue; }
      out.push({ lat: LAT[c], cyr: CYR[c] });
    }
    return out;
  }

  // Слово → {lat, cyr}. particle: は/へ/を читаются wa/e/o; long: свести ou/uu/ei в долгие гласные (не для глаголов)
  function transcribe(kana, { particle = false, long = true } = {}) {
    if (/(んにち|んばん)は$/.test(toHira(kana))) kana = kana.slice(0, -1) + 'わ';     // こんにちは, こんばんは
    if (particle) {
      const p = { は: ['wa', 'ва'], へ: ['e', 'э'], を: ['o', 'о'] }[toHira(kana)];
      if (p) return { lat: p[0], cyr: p[1] };
    }
    const syl = syllables(kana);
    let lat = '', cyr = '';
    syl.forEach((x, i) => {
      if (x.sokuon) {                                                               // っ: удвоить следующую согласную
        const nx = syl[i + 1];
        if (nx && !nx.sokuon) { lat += nx.lat.startsWith('ch') ? 't' : nx.lat[0]; cyr += nx.cyr[0]; }
        return;
      }
      let l = x.lat, c = x.cyr;
      if (l === 'n') {                                                              // ん перед гласной/y — n', перед м/б/п у Поливанова — м
        const nx = syl[i + 1];
        if (nx && !nx.sokuon && /^[aiueoy]/.test(nx.lat)) { l = "n'"; c = 'нъ'; }
        else if (nx && /^[mbp]/.test(nx.lat)) c = 'м';
      }
      // Поливанов: い после гласной — й
      if (c === 'и' && i > 0 && /[ауэояюё]\u0304?$/.test(cyr) && !syl[i - 1].sokuon) c = 'й';
      lat += l; cyr += c;
    });
    if (long) {
      lat = lat.replace(/ou/g, 'ō').replace(/uu/g, 'ū').replace(/oo/g, 'ō');
      cyr = cyr.replace(/оу/g, 'о' + CMAC).replace(/уу/g, 'у' + CMAC).replace(/ёу/g, 'ё' + CMAC).replace(/юу/g, 'ю' + CMAC).replace(/оо/g, 'о' + CMAC);
    }
    return { lat, cyr };
  }

  /* ---------- разбор фразы ---------- */
  async function analyze(raw, loadShard) {
    const cs = [...raw].slice(0, 100), text = cs.join('');
    const keys = new Set(cs.filter(c => JP.test(c)).map(shardOf));
    ['く', 'す'].forEach(c => keys.add(shardOf(c)));                               // くる/する: основа начинается с другого знака
    const dict = {};
    await Promise.all([...keys].map(async k => Object.assign(dict, await loadShard('ja', k))));

    // Все словарные совпадения, начинающиеся в позиции i: [{n, surface, base, entry, cost}]
    const PARTICLE = /^[はがをにとものへやかねよ]$/;
    // служебные глаголы: их формы (して, いた, なって) почти всегда спряжение, а не омоним
    const AUX = new Set(['する', 'くる', 'いる', 'ある', 'なる', 'いく', 'くれる', 'もらう', 'あげる', 'しまう', 'おく', 'みる']);
    // устойчивые выражения, которые и есть слово (иначе штраф exp разбивает ください на でく + ださい)
    const EXP_OK = new Set(['ください', '下さい', 'ありがとう', 'ございます', 'おはよう', 'すみません', 'いただきます', 'ごちそうさま', 'おやすみ', 'さようなら', 'よろしく', 'ちょっと']);
    const matches = (i, b) => {
      const out = [];
      for (let m = Math.min(12, b - i); m >= 1; m--) {
        const s = cs.slice(i, i + m).join('');
        // кандидаты: словарная форма как есть и все снятые спряжения; берём самый дешёвый
        const cands = [];
        if (dict[s]) cands.push({ base: s, e: dict[s][0], extra: 0 });
        for (const d of deinflect(s)) {
          const f = (dict[d.base] || []).find(x => posMatch(x[1], d.cls));
          // повелительное служебного глагола (あれ ← ある) — без бонуса: обычно это другое слово (あれ «то»)
          if (f) cands.push({ base: d.base, e: f, extra: AUX.has(d.base) && !d.imp ? -1 : 1 });
        }
        let best = null;
        for (const c of cands) {
          // стоимость слова: меньше слов — лучше; редкие слова, кана вместо обычных кандзи и устойчивые выражения
          // дороже (выражения вроде 雨が降る лучше показать по словам); частица после кандзи/катаканы дешевле
          let cost = 10 + c.extra + (c.e[4] ? 0 : 5) + (c.e[5] === 0 ? 4 : 0) + (/\bexp\b/.test(c.e[1]) && !EXP_OK.has(c.base) ? 10 + 4 * m : 0);   // длинное выражение дороже: お元気ですか → お元気 です か
          const afterContent = i > 0 && /[㐀-鿿\u30a0-\u30ffー]/.test(cs[i - 1]);
          if (m === 1 && PARTICLE.test(s)) cost -= afterContent ? 4 : 3;
          if (m === 1 && s === 'で' && afterContent) cost -= 4;                       // で иначе отбирает слог у です
          if (m > 1 && PARTICLE.test(s[s.length - 1]) && dict[s.slice(0, -1)]) cost += 8;   // 何を, 今日は: лучше слово + частица
          if (!best || cost < best.cost) best = { n: m, surface: s, base: c.base, entry: c.e, cost };
        }
        if (best) out.push(best);
      }
      return out;
    };

    // Минимальная стоимость разбиения каждого японского отрезка (динамика по позициям)
    const segment = (a, b) => {
      const best = Array(b - a + 1).fill(null); best[0] = { cost: 0 };
      for (let i = a; i < b; i++) {
        const cur = best[i - a]; if (!cur) continue;
        const opts = matches(i, b);
        opts.push({ n: 1, surface: cs[i], cost: 20 });                              // незнакомый знак по одному
        for (const o of opts) {
          const j = i + o.n - a, c = cur.cost + o.cost;
          if (!best[j] || c < best[j].cost) best[j] = { cost: c, prev: i - a, tok: o };
        }
      }
      const toks = []; for (let j = b - a; j > 0; j = best[j].prev) toks.unshift(best[j].tok);
      return toks;
    };

    const parts = [];
    for (let i = 0; i < cs.length;) {
      let j = i;
      if (!JP.test(cs[i])) {
        while (j < cs.length && !JP.test(cs[j])) j++;
        const p = cs.slice(i, j).join('').trim(); if (p) parts.push({ word: p, punct: true });
        i = j; continue;
      }
      while (j < cs.length && (JP.test(cs[j]) || cs[j] === 'ー')) j++;
      for (const t of segment(i, j)) {
        const chars = [...t.surface];
        if (!t.entry) {
          const kana = KANA.test(t.surface) ? t.surface : '';
          parts.push({ word: t.surface, chars, ja: true, reading: kana, ...(kana ? transcribe(kana) : {}) });
          continue;
        }
        const [rd, pos, en, ru] = t.entry;
        const reading = readingOf(t.surface, t.base, rd, pos);
        const godanU = /\bv5u/.test(pos) && t.base === t.surface && reading.endsWith('う');   // 思う: ou — не долгая
        parts.push({
          word: t.surface, chars, ja: true, lemma: t.base !== t.surface ? t.base : null,
          reading, ...transcribe(reading, { particle: pos.split(' ').includes('prt'), long: !godanU }),
          gloss: en, gloss_ru: ru,
        });
      }
      i = j;
    }
    return { zh: text, custom: true, ja: true, words: parts };
  }

  return { isJapanese, analyze, transcribe, toHira, deinflect, KANA, HAN };
})();
