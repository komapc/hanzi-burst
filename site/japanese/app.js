// Kana tables + detail panel. Data lives in kana.js (GOJUON, DAKUON, YOON, SMALL_Y).
const VOWELS = ["a", "i", "u", "e", "o"];
const DAKUTEN_NOTE = { ga: "ka", za: "sa", da: "ta", ba: "ha", pa: "ha" };

let script = "hira";
const byGlyph = new Map();   // hiragana -> entry, for deep links and the detail panel
const cells = [];

function entry(e) { byGlyph.set(e.hira, e); return e; }

// Normalise all three tables into one entry shape.
const tables = {
  gojuon: GOJUON.map(([row, cs]) => [row, cs.map(c => c && entry({
    rom: c[0], hira: c[1], hiraSrc: c[2], kata: c[3], kataSrc: c[4], kataPart: c[5], old: c[6] === "obsolete",
  }))]),
  dakuon: DAKUON.map(([row, cs]) => [row, cs.map(c => entry({
    rom: c[0], hira: c[1], kata: c[2],
    note: row === "pa"
      ? `The ${DAKUTEN_NOTE[row]}-row kana with a handakuten ゜ (small circle).`
      : `The ${DAKUTEN_NOTE[row]}-row kana with a dakuten ゛ (two ticks), which voices the consonant.`,
    base: c[1].normalize("NFD")[0],
  }))]),
  yoon: YOON.map(([row, h, k, rom]) => [row, SMALL_Y.map(([v, sh, sk]) => entry({
    rom: rom + v, hira: h + sh, kata: k + sk,
    note: `${h} (${rom.length > 1 && rom.endsWith("y") ? rom.slice(0, -1) + "i" : rom + "i"}) plus a small ${sh}: the two merge into one syllable.`,
    base: h,
  }))]),
};

function glyphHTML(e) {
  if (script === "hira") return e.hira;
  if (script === "kata") return e.kata;
  return `${e.hira}<span class="k">${e.kata}</span>`;
}

function renderTable(id, rows, cols) {
  const t = document.getElementById(id);
  let html = `<thead><tr><th class="row"></th>${cols.map(c => `<th>${c}</th>`).join("")}</tr></thead><tbody>`;
  for (const [row, cs] of rows) {
    html += `<tr><th class="row" scope="row">${row}</th>`;
    for (const e of cs) {
      if (!e) { html += `<td class="empty"></td>`; continue; }
      html += `<td><button class="cell${e.old ? " old" : ""}" data-k="${e.hira}" aria-pressed="false">` +
        `<span class="g">${glyphHTML(e)}</span><span class="r">${e.rom}</span></button></td>`;
    }
    html += `</tr>`;
  }
  t.innerHTML = html + `</tbody>`;
}

function renderAll() {
  renderTable("gojuon", tables.gojuon, VOWELS);
  renderTable("dakuon", tables.dakuon, VOWELS);
  renderTable("yoon", tables.yoon, ["ya", "yu", "yo"]);
  document.getElementById("tables").classList.toggle("both", script === "both");
  markSelected();
}

const USE = {
  on: "Chinese-derived reading",
  kun: "native Japanese word written with this kanji",
  "?": "disputed",
};

// Sound + meaning of a source kanji: which reading the kana took, and what the kanji means.
function srcInfo(k, rom) {
  const s = SRC[k], u = UNIHAN[k];
  if (!s) return "";
  const [reading, use, meaning, note] = s;
  let html = `<dl class="src">` +
    `<dt>Meaning</dt><dd>${meaning}</dd>` +
    `<dt>Sound</dt><dd><b>${reading}</b>${reading !== rom ? ` → <b>${rom}</b>` : ""} <span class="use use-${use === "?" ? "q" : use}">${USE[use]}</span>` +
    (note ? `<br><span class="sub">${note}</span>` : "") + `</dd>`;
  if (u) html += `<dt>Chinese</dt><dd>${u[1] ? `Tang ${u[1]} · ` : ""}Mandarin ${u[0]}</dd>`;
  return html + `</dl>`;
}

function originBlock(kana, src, how, rom) {
  return `<div class="flow"><span class="kj">${src || "?"}</span><span class="ar">→</span><span class="kn">${kana}</span>` +
    `<span class="how">${how}</span></div>${src ? srcInfo(src, rom) : ""}`;
}

let selected = null;
function show(k) {
  const e = byGlyph.get(k);
  if (!e) return;
  selected = k;
  const d = document.getElementById("detail");
  let html = `<div class="big"><span>${e.hira}</span><span>${e.kata}</span></div>` +
    `<div class="rom">${e.rom}${canSpeak() ? `<button id="say" title="Listen" aria-label="Listen">▶</button>` : ""}</div>`;
  if (e.old) html += `<p class="note">Obsolete: not used in modern spelling.</p>`;
  if (e.note) html += `<p class="note">${e.note}</p>`;
  if (e.hiraSrc !== undefined) {
    html += `<div class="origin"><h3>Origin</h3>` +
      originBlock(e.hira, e.hiraSrc, `hiragana · cursive of the whole kanji`, e.rom) +
      (e.kataSrc === e.hiraSrc
        ? `<div class="flow"><span class="kj">${e.kataSrc}</span><span class="ar">→</span><span class="kn">${e.kata}</span><span class="how">katakana · ${e.kataPart}</span></div>`
        : originBlock(e.kata, e.kataSrc, e.kataSrc ? `katakana · ${e.kataPart}` : `katakana · ${e.kataPart}`, e.rom)) +
      `</div>`;
  } else if (e.base) {
    let b = byGlyph.get(e.base);
    while (b && b.hiraSrc === undefined && b.base) b = byGlyph.get(b.base);   // ぎゃ → ぎ → き
    html += `<div class="origin"><h3>Origin</h3><p>Built on ${b.hira} / ${b.kata}, which come from ${b.hiraSrc}${b.kataSrc && b.kataSrc !== b.hiraSrc ? ` / ${b.kataSrc}` : ""}.</p>` +
      `<p><a href="#${b.hira}" data-k="${b.hira}">Show ${b.hira}</a></p></div>`;
  }
  d.innerHTML = html;
  document.getElementById("say")?.addEventListener("click", () => speak(e.hira));
  if (location.hash.slice(1) !== encodeURIComponent(k)) history.replaceState(null, "", "#" + encodeURIComponent(k));
  markSelected();
}

function markSelected() {
  for (const b of document.querySelectorAll(".cell")) b.setAttribute("aria-pressed", String(b.dataset.k === selected));
}

// Speech: only offered when the browser has a Japanese voice.
function jaVoice() { return speechSynthesis.getVoices().find(v => v.lang.replace("_", "-").startsWith("ja")); }
function canSpeak() { return "speechSynthesis" in window && !!jaVoice(); }
function speak(text) {
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "ja-JP"; u.voice = jaVoice(); u.rate = 0.8;
  speechSynthesis.cancel(); speechSynthesis.speak(u);
}
if ("speechSynthesis" in window) speechSynthesis.addEventListener("voiceschanged", () => selected && show(selected));

document.addEventListener("click", ev => {
  const t = ev.target.closest("[data-k]");
  if (t) { ev.preventDefault(); show(t.dataset.k); return; }
  const s = ev.target.closest("[data-script]");
  if (s) {
    script = s.dataset.script;
    for (const b of document.querySelectorAll("[data-script]")) b.setAttribute("aria-pressed", String(b === s));
    try { localStorage.setItem("kana-script", script); } catch {}
    renderAll();
  }
});
document.getElementById("romaji").addEventListener("change", ev => {
  document.body.classList.toggle("noromaji", !ev.target.checked);
});

try {
  const saved = localStorage.getItem("kana-script");
  if (saved) { script = saved; for (const b of document.querySelectorAll("[data-script]")) b.setAttribute("aria-pressed", String(b.dataset.script === saved)); }
} catch {}
renderAll();
show(decodeURIComponent(location.hash.slice(1)) || "あ");
