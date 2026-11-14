# Hanzi Burst

Учим китайские иероглифы (и японские кандзи) через разбор на ключи и радикалы. Фраза → слова с пиньинем и
переводом → клик по иероглифу → дерево частей с объяснением, почему знак значит именно это, и запоминалкой.
Аудитория — новички чуть выше нулевого уровня.

- Сайт: https://hanzi.lipu.dev (код — `site/`, бэкенд — `worker/`).
- Расширение для Chrome и Firefox (`extension/`): то же самое для выделенного текста на любой странице, пиньинь
  и фуригана над текстом. Подробности — [`extension/README.md`](extension/README.md), тексты магазинов — `store/LISTING.md`.
- Идеи и отложенное — [`ROADMAP.md`](ROADMAP.md).

## Статус (2026-11-14)

- Сайт: деплоится из `main` автоматически (см. «Деплой»).
- Расширение: 0.2.6 отправлена в Chrome Web Store и на addons.mozilla.org 2026-11-13, обе на проверке.
  В `main` уже 0.2.7 (новая иконка, разбор традиционных знаков как есть); тег `v0.2.7` ставится, когда 0.2.6 одобрят
  в обоих магазинах.

## Содержание

- [Быстрый старт](#быстрый-старт) · [Тесты](#тесты) · [Устройство репозитория](#устройство-репозитория)
- Сайт: [адреса и ссылки](#адреса-ссылки-на-сайт) · [localStorage](#что-хранится-в-браузере) · [своя фраза](#своя-фраза-вставка-текста) ·
  [японский режим](#японский-режим-中--日) · [简/繁](#традиционные--упрощённые-简--繁) · [чтения и вид](#чтения-и-вид-фразы) ·
  [поиск и фраза дня](#поиск-знака-и-фраза-дня) · [HSK](#прогресс-по-hsk) · [телефон и тур](#телефон-первый-вход) · [загрузка](#загрузка-и-доступность)
- Данные: [источники и лицензии](#источники-и-лицензии) · [пул фраз](#пул-фраз) · [дыры «？»](#дыры--в-разборе) ·
  [русские значения](#русские-значения) · [запоминалки](#предзаполненные-запоминалки)
- [Статические страницы и SEO](#статические-страницы-и-seo) · [Бэкенд](#бэкенд-cloudflare-workers--d1) ·
  [Деплой](#деплой) · [Выпуск расширения](#выпуск-новой-версии-расширения)

## Быстрый старт

```bash
# 1. Сырые данные (в гит не кладутся) -> data/raw/. Проще всего взять снимок, которым пользуется CI:
gh release download raw-data-2026-10-25b -p raw-data.tar.xz     # тег — RAW_DATA_TAG в .github/workflows/deploy.yml
mkdir -p data/raw && tar -xJf raw-data.tar.xz -C data/raw
pip install Pillow

# 2. Сборка: шарды site/data/, страницы /c/ /p/ /hsk/ /k/ /r/, sitemap, zip расширения
sh scripts/build_all.sh

# 3. Сайт вместе с API (вход, запоминалки; локальная D1) — http://localhost:8787/?open=想&explode=1&lang=ru
npx wrangler dev          # сам запустит сборку из шага 2; HB_BUILT=1 npx wrangler dev — без неё
# или только статика, без API (кнопки входа и запоминалок не показываются):
cd site && python3 -m http.server 8765
```

Готовые фразы (`site/phrase.json`, `site/glyphs.json`, пулы `site/pool*.json`) лежат в репозитории; как их пересобрать —
в разделе «Пул фраз». Минификация (`minify.py`) работает только в CI, локально код остаётся читаемым.

## Тесты

```bash
node --test tests/js/*.test.js                # расширение: common.js (слияние списков, предложение под курсором,
                                             # состояние узла) и lookup() из background.js на фикстурах tests/js/fixtures
python3 -m unittest discover -s tests/py      # скрипты сборки: пиньинь, сегментация, разбор, дыры «？», Палладий
```

Без зависимостей и без `data/raw`; оба набора идут в CI (`check.yml`) на каждый PR.

Сайт (`site/index.html`) проверяется в браузере: Playwright + Chromium открывают собранный `site/` (нужен `site/data`,
то есть `sh scripts/build_all.sh`) и проходят по интерфейсу: фраза, дерево, кнопки плитки (+/−, ★), ссылки
в описании, Copy, 简/繁 (части не переводятся в 繁: 你 = 亻 + 尔, не 爾), `?t=`, японский режим. Любая JS-ошибка
на странице тоже валит тест.

```bash
pip install playwright && python3 -m playwright install chromium
python3 -m unittest discover -s tests/e2e -v
```

В CI (`deploy.yml`) сайт собирается один раз, на нём идут эти тесты (уже минифицированный код), и только потом
`wrangler deploy` (или `--dry-run` в PR) с `HB_BUILT=1`, чтобы wrangler не собирал заново. Упали тесты — деплоя нет.

## Устройство репозитория

| Путь | Что там |
|---|---|
| `site/index.html` | всё приложение: фраза, дерево, карточка, режимы; инлайн-скрипт без сборщика |
| `site/script.js`, `ja.js`, `footer.js`, `nav.js`, `static.js` | 简/繁 для текста страницы; японский анализатор (JMdict, общий с расширением); подвал; шапка и «знаю» на статических страницах |
| `site/learned.html`, `radicals-game.html` | «Мои иероглифы» (прогресс по HSK); игра по ключам |
| `site/phrase.json`, `glyphs.json`, `pool*.json` | заготовленные фразы с разбором, контуры их знаков, пулы фраз (коммитятся) |
| `site/data/` | шарды словаря, разборов и контуров (генерируется, в `.gitignore`) |
| `scripts/breakdown.py` | сегментация (CC-CEDICT), рекурсивный разбор на части и этимология (Make Me a Hanzi), запасные описания радикалов (Unicode, Unihan), контуры черт |
| `scripts/build_*.py`, `build_all.sh` | сборка: шарды, японские шарды и кандзи, статические страницы, zip расширения |
| `scripts/fetch_*.py`, `clean_pool.py`, `build_*_pool.py` | пополнение и чистка пулов фраз (Tatoeba, Wiktionary, Common Voice) |
| `scripts/radical*.py`, `kanji_pages.py` | ключи Канси (таблица, страницы, PDF, плакат), страницы кандзи |
| `data/` | исходники, которые коммитятся: фразы, пул, переводы на русский (`translations/ru.json`), ключи, запоминалки; `data/raw/` — сырые словари, не коммитятся |
| `worker/` | Cloudflare Worker: статика + `/api/*`, схема и миграции D1 |
| `extension/` | расширение (Manifest V3; Firefox — та же сборка с `background.scripts`) |
| `tests/` | `js` (расширение), `py` (скрипты), `e2e` (сайт в браузере) |
| `store/` | тексты листингов Chrome Web Store и AMO |

## Сайт

### Адреса (ссылки на сайт)

| Параметр | Что делает |
|---|---|
| `?open=想` | сразу открыть разбор знака (знак не из фраз грузится из шардов); `&explode=1` — раскрыть всё дерево |
| `?t=<текст>` | своя фраза (кана включает режим 日); так ссылается расширение |
| `?z=<фраза>` | фраза из пула по тексту |
| `?p=<номер>` | заготовленная фраза по номеру |
| `?mode=ja` / `?mode=zh` | режим 日 / 中 |
| `?lang=ru` / `?lang=en` | язык интерфейса |
| `?q=<запрос>` | поиск знака (из шапки статических страниц) |
| `?day` | фраза дня |

### Что хранится в браузере

Всё — `localStorage`, ключи с префиксом `hanzi-`: `known` (знаки «Знаю»; событие `hanzi-known-saved` для расширения),
`lang`, `mode` (中/日), `script` (简/繁), `rd` / `phon` (чтения над китайским), `ja-rd` (чтения над японским), `view`
(скрытые пиньинь/перевод), `phrase` / `phrase-ja` (текущая фраза), `seen-pool` / `seen-ja` (полученные из пула),
`textlang`, `tour` (`done` — тур пройден), `consent` (баннер аналитики), `radicals-srs` (игра по ключам).
Расширение синхронизирует «известные» с сайтом само (см. `extension/README.md`).

### Своя фраза (вставка текста)

`python3 -I scripts/build_shards.py` строит `site/data/` (шарды иероглифов, контуров и слов CC-CEDICT по `кодпоинт>>8`,
плюс `trad.json`). Каталог в `.gitignore`, генерируется сборкой. Клиент грузит нужные шарды лениво, сегментирует текст
и открывает обычный интерактивный разбор. Ссылка: `/?t=<текст>`.

### Японский режим (中 / 日)

Переключатель 中 / 日 в шапке (`hanzi-mode`, ссылка `/?mode=ja`). В режиме 日:

- фразы берутся из `site/pool-ja.json` (≈2700 предложений японского Tatoeba с переводами; `python3 -I scripts/build_ja_pool.py`,
  результат коммитится, как `site/pool.json`; сырые файлы `data/raw/tatoeba/jpn*` в снимок не входят). Слова и чтения
  считает клиент (`site/ja.js`, JMdict) при первом показе фразы. «Новая фраза» берёт фразу с минимумом новых кандзи
  и младшим школьным классом; полученные фразы — `hanzi-seen-ja`;
- кандзи и кана рисуются чертами KanjiVG, разбор на части — по группам KanjiVG, чтения (он/кун) и английские значения —
  KANJIDIC2, русское значение — значение однознакового слова JMdict с кун-чтением (это значение слова, оно помечено).
  Шарды `site/data/kanji/` строит `build_kanji_shards.py`;
- над группами кандзи — фуригана, под словом — транскрипция; чтение сопоставляется с окуриганой (`furi`), группа кандзи не делится;
- 简/繁 и китайские чтения скрыты; японский текст (`lang="ja"`) не переводится в традиционные знаки.

Своя фраза с каной включает режим 日 сама, китайская — режим 中.

### Традиционные / упрощённые (简 / 繁)

Радио-кнопки 简 / 繁 в шапке (`hanzi-script`). Данные и ссылки остаются упрощёнными; подменяется только отображение:
текстовые узлы (`site/script.js`) и начертания SVG (`syncScript` в `index.html`, глифы традиционных знаков берутся
из шардов `data/g`). Карта `site/data/s2t.json` строится в `build_shards.py` по частоте пар в словах CC-CEDICT (омографы
вроде 发 → 發/髮 дают самый частый вариант). Статические страницы `/c/`, `/p/` всегда упрощённые.

В 繁 разбирается традиционная форма (学 → 學), но сам разбор не переводится: дерево и описание в карточке рисуют сам знак
(`hz(ch, '', true)`, `[data-noconv]` пропускает `script.js`), иначе части разбора конвертировались бы второй раз
(尔 в 你 стал бы 爾). Расширение разбирает традиционный знак как есть, если у него есть своя статья (禰 = 礻 + 爾),
и падает на упрощённый, если нет.

### Чтения и вид фразы

- ⚙ Настройки → галочки чтений над иероглифами (`hanzi-rd`): пиньинь, бопомофо (注音), Палладий (только в русском интерфейсе).
  Первое отмеченное используется в карточке, списках слов и поиске. Конвертеры (`ZY`, Палладий) работают на лету,
  данные не меняются; подсказки (hover) и запоминалки остаются в пиньине. В режиме 日 — фуригана, латиница, кириллица (`hanzi-ja-rd`).
- Кнопки над фразой (`#view`, `hanzi-view`): «Пиньинь» (в 日 — «Чтение») и «Перевод» скрывают подписи для самопроверки.
  Скрытое чтение — серая полоска, нажатие открывает чтение одного слова (сбрасывается при смене фразы); скрытый перевод
  размыт, нажатие открывает его вместе с пословным разбором. Пиньинь всегда раскрашен по тону (`--t1…--t5`).
- «Слушать» — синтез речи браузера; «Копировать» — фраза с выбранными строками (знаки, чтения, перевод).
- Плитка в дереве: клик по знаку — объяснение в карточке (части раскрываются один раз и не закрываются),
  `+`/`−` в углу — показать/скрыть части, ★ — «Знаю». Иероглифы в описании — ссылки на их разбор.

### Поиск знака и фраза дня

Поле справа от переключателей вида: иероглиф открывается сразу (в режиме 日 — кандзи), пиньинь даёт список знаков —
`xiang`, `xiang3`, `xiǎng`, `lü4`/`lv4`. Индекс `site/data/pyindex.json` (слог+тон и слог без тона → до 24 знаков,
частые первыми; только упрощённые) строит `build_shards.py`.

«☀ Фраза дня» — одна на день для всех (выбор по дате), из пула: HSK 1–3 с русским переводом, в режиме 日 — кандзи 1–2 класса.
Ссылка `/?day` открывает её сразу.

### Прогресс по HSK

На странице «Мои иероглифы» — полоски по уровням HSK 3.0: сколько знаков уровня отмечено «Знаю». Клик по уровню
показывает неотмеченные знаки (частые первыми). Знаки по уровням — `site/data/hsk.json` из `build_shards.py`:
уровень знака = самый низкий уровень слова HSK, где он встречается (выходит 300/299/301/305/310/518/1001,
почти ровно официальный список знаков).

### Телефон, первый вход

- На экранах ≤640px карточка иероглифа выезжает снизу (фраза остаётся видна); закрыть — «×», Esc или потянуть вниз за ручку.
- Первый вход (`hanzi-tour`): пульсирующий иероглиф фразы, затем подсказка про части и «+». У кого в localStorage уже
  есть фразы или «известные», тур не показывается.

### Загрузка и доступность

Контуры черт лежат в шардах `site/data/g/<cp>>4>.json` по 16 знаков (~18 КБ): страница грузит только шарды показанных
знаков (`loadGlyphs`), а `MutationObserver` заменяет текстовые заглушки `span.serif[data-c]` на SVG, когда контуры пришли.
Шарды `data/*` кэшируются на сутки (+ неделя stale-while-revalidate), остальной JSON — на час (`site/_headers`).
Цвета (приглушённый текст, тоны, «Знаю», кнопки) подобраны под контраст WCAG AA в светлой и тёмной теме; проверка — axe-core.

## Данные

### Источники и лицензии

Make Me a Hanzi (LGPL/Arphic), CC-CEDICT (CC BY-SA), Unicode/Unihan (Unicode License), cjkvi-ids (GPL, только
вычисленные разборы отдельных знаков), HSK 3.0 (drkameleon/complete-hsk-vocabulary, MIT), JMdict и KANJIDIC2 (EDRDG,
CC BY-SA 4.0), KanjiVG (Ulrich Apel, CC BY-SA 3.0), фразы и их переводы: Tatoeba (CC BY 2.0 FR, авторы указаны на
tatoeba.org по номеру в `source`), Wiktionary (CC BY-SA), Common Voice (CC0). Атрибуция: страница `/about`
(`site/about.html`) и `extension/NOTICE.txt` в пакете расширения.

Что лежит в `data/raw/` (и в снимке для CI): `mmh/{dictionary,graphics}.txt`, `cedict/cedict_ts.u8`,
`unicode/CJKRadicals.txt`, `unihan/Unihan_*.txt`, `ids/ids.txt`, `hsk/complete.json`, `jmdict/jmdict-{eng,rus}-*.json`
([jmdict-simplified](https://github.com/scriptin/jmdict-simplified/releases)), `kanjidic/kanjidic2.xml.gz`,
`kanjivg/kanjivg-*.xml.gz`. Для пополнения пулов (в снимок не входят): `tatoeba/`, `kaikki/`, `commonvoice/`.

### Пул фраз

- `data/phrases.json` → `site/phrase.json` + `site/glyphs.json` — заготовленные фразы с полным разбором:

  ```bash
  # data/raw/tatoeba/: cmn_sentences, cmn-eng_links, cmn-rus_links, eng_sentences, rus_sentences .tsv.bz2
  # с https://downloads.tatoeba.org/exports/per_language/
  python3 -I scripts/fetch_phrases.py --count 40 --max-new 2   # --dry-run — посмотреть без записи
  python3 -I scripts/breakdown.py data/phrases.json site/phrase.json
  ```

  Фразы выбираются как учебная программа: мало новых иероглифов относительно уже имеющихся, оба перевода (ru, en) из Tatoeba.
  Для новых иероглифов нужны русские переводы определений в `data/translations/ru.json` (без них показывается английский).
- `data/pool.json` → `site/pool.json` (грузится лениво) — пул для кнопки «Новая фраза».
  `scripts/build_tatoeba_pool.py` отбирает из всего китайского Tatoeba (≈89 тыс.) простые целые предложения (4–16 знаков,
  знаки из топ-1300 по частоте, есть английский перевод; русский в приоритете) по квотам на уровень HSK (3000 штук).
  Дополнительно — `fetch_wiktionary.py` и `fetch_commonvoice.py` (`--candidates` — только список). После любого `fetch_*.py`
  запускать `python3 -I scripts/clean_pool.py`: он убирает именные группы и обрывки.
- Уровень слов — `data/raw/hsk/complete.json` через `scripts/hsk.py` (7 = уровни 7–9); `breakdown.py` кладёт `hsk` в каждую фразу.
- «Новая фраза» выбирает фразу с минимумом ещё не виденных иероглифов (известные + уже показанные), при равенстве —
  более низкий уровень. Полученные фразы запоминаются (`hanzi-seen-pool`) и попадают в выпадающий список. Слова фраз
  из пула получают значения из шардов `data/words/` при открытии; `usage.json` грузится отдельно после старта.

### Дыры «？» в разборе

В Make Me a Hanzi у части знаков один компонент записан как «？» (曷 = ⿱日？). `breakdown.py` (`fill_holes`) заполняет
такие места разбором из cjkvi-ids (`data/raw/ids/ids.txt`, https://github.com/cjkvi/cjkvi-ids, производное от CHISE IDS, GPL).
Берутся только случаи, где все части — обычные унифицированные иероглифы или радикалы (их можно показать шрифтом,
контуров у них нет). Остальное помечается в интерфейсе как «неполное дерево» (`incomplete`). Данные IDS в репозиторий
не копируются, в сборку попадают только полученные разборы отдельных знаков.

### Русские значения

`data/translations/ru.json` ({en: ru}, переведено вручную) покрывает основные значения всех знаков HSK 1–9 и чтения
их 多音字. Неверные или редкие первые значения MMH (机 «desk», 离 «rare beast», 着 «to make a move»…) заменяет
`DEFINITION_OVERRIDES` в `breakdown.py`.

### Предзаполненные запоминалки

`data/mnemonics_prefill.json` — по одной запоминалке (RU и EN) для каждого из 629 иероглифов, написаны моделью по правилам
промпта Worker. Залиты в D1 (`mnemonics`, variant 1, `model = 'claude-sonnet-5-5 (prefill)'`, `prompt_version = 2`)
через `INSERT OR IGNORE`; «Ещё вариант» по-прежнему просит Gemini.

## Статические страницы и SEO

`build_static.py` строит `/c/<hex>` (знаки), `/p/` (фразы), `/hsk/`, `/k/<hex>` (кандзи, `scripts/kanji_pages.py`),
`/r/<hex>` и `/en/r/<hex>` (214 ключей Канси, `scripts/radical_pages.py`), `sitemap.xml`. Интерактивная версия любой
страницы — ссылка `/?open=<знак>`.

- **Ключи.** Таблица `data/radicals.json` коммитится; её собирает `scripts/build_radicals.py` (запускать вручную после
  правки названий и вариантов в `scripts/radical_names.py`, там же названия на эсперанто). Там же `PICTURES` — что нарисовано (又 значит «снова», а нарисована правая рука): строка «Что нарисовано» на `/r/` и `/en/r/`, только где картинка не совпадает со значением и этимология устоявшаяся; в `data/radicals.json` не входит, чтобы не пересобирать плакат. Частые ключи (`top`, первые 60
  по числу знаков HSK) идут первыми в указателе `/r/`.
- **PDF ключей** (коммитятся): карточки `site/radicals-{ru,en}.pdf` — `python3 scripts/radicals_pdf.py` (нужны
  `google-chrome` и Noto CJK); плакат A2 `site/radicals-poster-{ru,en,eo}.pdf` + превью `.jpg` — `python3 scripts/radicals_poster.py`
  (QR — `segno`, метаданные — `pypdf`, превью — ImageMagick). Страницы плаката `/r/poster`, `/en/r/poster`, `/eo/r/poster`
  собирает `radical_pages.py`.
- **Английские версии:** `/en/c/<hex>`, `/en/c/`, `/en/p/<id>`, `/en/p/`, `/en/hsk/`, `/en/hsk/N` со своими canonical
  и взаимными `hreflang` ru↔en (`x-default` — русская версия); значения только английские. Ссылки «в приложение»
  с английских страниц добавляют `lang=en`. Кандзи `/k/` — только по-русски.
- **Заголовки:** главная «Разбор китайских иероглифов на ключи и радикалы — Hanzi Burst» (H1 «Разбор китайских иероглифов
  на ключи», по-английски «Chinese characters broken down into radicals»); знак «Иероглиф 吗 (ma): значение и разбор на
  ключи | Hanzi Burst», ключ «Ключ 口 (kǒu): значение и иероглифы с ним | Hanzi Burst»; по-английски «吗 ma — meaning,
  radicals and components | Hanzi Burst» и «Radical 口 kǒu — meaning and characters that use it | Hanzi Burst».
  Дубликатов title и description нет — проверять после правок шаблона.
- **Страница знака**, кроме разбора: уровень HSK (ссылка на `/hsk/N`), до 10 слов CC-CEDICT (сначала слова HSK), до 8 фраз,
  «Иероглифы, в которых есть X» (до 20 + общее число), «Похожие по написанию» (до 12). Всё из данных сборки, без текста от LLM.
- **Страницы кандзи** `/k/<hex>` — 2136 знаков дзёё (KANJIDIC2: классы 1–6 и средняя школа), только по-русски: онъёми
  и кунъёми каной и кириллицей (Поливанов, как `transcribe` в `ja.js`; окуригана серым), значения KANJIDIC2, класс, число
  черт, старый уровень JLPT, состав по KanjiVG, «Кандзи, в которых есть X», похожие, до 10 частых слов JMdict (только кандзи
  дзёё и хирагана), до 8 фраз из `pool-ja.json` (ссылки `/?t=<фраза>` открывают режим 日). Русское значение знака берётся
  из китайских шардов, если английское значение CC-CEDICT совпадает с одним из значений KANJIDIC2 (иначе 机 стал бы
  «машиной»), затем — глосса JMdict. Хаб `/k/` — по классам. `/c/X` и `/k/X` одного знака ссылаются друг на друга.
- **HSK-списки** `/hsk/1` … `/hsk/7` (7 = уровни 7–9) и хаб `/hsk/`: знак, пиньинь, первое значение; ссылка на `/c/<код>`
  или `/?open=<знак>`, если своей страницы у знака нет.
- **`sitemap.xml`** — только хабы, `/hsk/*`, знаки HSK 1–3 и кандзи 1 класса, ключи, плюс те же хабы, HSK и знаки HSK 1–3
  под `/en/`. Остальные `/c/`, `/en/c/` и все страницы фраз не в sitemap, но и не `noindex`: тысячи шаблонных страниц
  в sitemap мешали индексации (на 2026-10-29 Google не индексировал сайт).
- **Подтверждения владения:** `site/yandex_075f1191e804f3a2.html` (Яндекс Вебмастер), `site/BingSiteAuth.xml`,
  ключ IndexNow `site/483e472b63ec64808ac4046f1b87eeb1.txt` — не удалять. Google Search Console — доменный ресурс `sc-domain:lipu.dev`.

## Бэкенд (Cloudflare Workers + D1)

Один Worker отдаёт статику из `site/` и `/api/*` (`worker/index.js`): вход через Google и список «известных» на сервере
(код готов, но `GOOGLE_CLIENT_ID` не задан, поэтому вход выключен — см. `ROADMAP.md`), запоминалки
через Gemini (кэш в D1, лимиты в сутки — `[vars]` в `wrangler.toml`), перевод фразы (`/api/translate`, им же пользуется
расширение). Без бэкенда (обычный статический сервер) страница работает, кнопки входа и запоминалок просто не показываются.
`hanzi-burst.komapc.workers.dev` отвечает 301 на hanzi.lipu.dev.

Первоначальная настройка (один раз; сделано всё, кроме `GOOGLE_CLIENT_ID` и `SESSION_SECRET`):

```bash
npm i -g wrangler && wrangler login
wrangler d1 create hanzi-burst            # id вписать в wrangler.toml
wrangler d1 execute hanzi-burst --remote --file worker/schema.sql
wrangler secret put GOOGLE_CLIENT_ID      # Google Cloud Console -> OAuth client (Web), origin = домен сайта
wrangler secret put SESSION_SECRET        # openssl rand -base64 32
wrangler secret put GEMINI_API_KEY
```

Секреты Worker хранятся в Cloudflare и при деплое не трогаются. Изменения схемы D1 (`worker/schema.sql`,
`worker/migrations/`) применяются вручную, деплой их не накатывает.

## Деплой

Деплой делает CI (`.github/workflows/deploy.yml`):

| Событие | Что происходит |
|---|---|
| PR | сборка + браузерные тесты + `wrangler deploy --dry-run`, ничего не публикуется; отдельно `check.yml` — синтаксис, JSON, unit-тесты |
| push в `main` | сборка + браузерные тесты + деплой на hanzi.lipu.dev, проверка, что сайт отдаёт zip расширения нужной версии |
| push тега `v*` | то же + выпуск расширения в Chrome Web Store и AMO (`extension-release.yml`) |
| Actions → deploy → Run workflow | передеплой текущего `main` |

Сборка — `scripts/build_all.sh`: `build_shards.py` → `build_ja_shards.py` → `build_kanji_shards.py` → `build_static.py`
→ `build_extension.py --zip` → `minify.py` (terser через npx сжимает `script.js`, `ja.js`, `footer.js` и инлайн-скрипты
страниц; только в CI или с `--force DIR`, при ошибке оставляет исходник). Её же вызывает `[build]` в `wrangler.toml`,
если не задан `HB_BUILT`. Нужны `data/raw/` и Pillow; CI берёт `data/raw/` из закреплённого снимка — ассет
`raw-data.tar.xz` релиза `raw-data-YYYY-MM-DD` (тег и sha256 — в `env` у `deploy.yml`).

Секреты репозитория (Settings → Secrets → Actions):

- `CLOUDFLARE_API_TOKEN` — https://dash.cloudflare.com/profile/api-tokens, шаблон «Edit Cloudflare Workers» + Account → D1 → Edit.
- `CWS_EXTENSION_ID`, `CWS_CLIENT_ID`, `CWS_CLIENT_SECRET`, `CWS_REFRESH_TOKEN` — Chrome Web Store API (OAuth-клиент
  `hanzi-burst-ci-desktop` в Google Cloud, проект hanzi-burst-ci).
- `AMO_JWT_ISSUER`, `AMO_JWT_SECRET` — ключ API addons.mozilla.org (https://addons.mozilla.org/developers/addon/api/key/,
  «JWT issuer» и «JWT secret»). Без них Firefox пропускается с предупреждением.

### Обновление снимка data/raw/

```bash
cd data/raw && tar -cJf /tmp/raw-data.tar.xz mmh/dictionary.txt mmh/graphics.txt cedict/cedict_ts.u8 \
  unicode/CJKRadicals.txt unihan/Unihan_*.txt ids/ids.txt hsk/complete.json jmdict/jmdict-eng-*.json jmdict/jmdict-rus-*.json \
  kanjidic/kanjidic2.xml.gz kanjivg/kanjivg-*.xml.gz
sha256sum /tmp/raw-data.tar.xz
gh release create raw-data-$(date +%F) /tmp/raw-data.tar.xz --prerelease --title "raw-data-$(date +%F) (build inputs)" --notes "data/raw/ snapshot for deploy.yml"
```

Затем вписать новый тег и sha256 в `RAW_DATA_TAG` / `RAW_DATA_SHA256` в `deploy.yml`. Имя тега не должно начинаться
с `v` (такие теги запускают выпуск расширения).

### Ручной деплой (запасной вариант)

При наличии `data/raw/` и Pillow: `npx wrangler deploy` из корня репозитория — та же сборка, что в CI, но без браузерных тестов.

## Выпуск новой версии расширения

1. Поднять `version` в `extension/manifest.json` (и в `store/LISTING.md`, `site/extension.html`), смёржить в `main`
   (сайт задеплоится сам).
2. Дождаться, пока предыдущая версия пройдёт проверку в обоих магазинах.
3. `git tag v<версия> && git push origin v<версия>` — CI задеплоит этот коммит (только если он — текущий HEAD `main`:
   тег на старом коммите прод не откатывает), загрузит расширение в Web Store с отправкой на проверку и отправит
   Firefox-сборку на addons.mozilla.org (`web-ext sign --channel listed`; проверку AMO делает человек, CI её не ждёт).
4. Если предыдущая версия ещё на проверке, Web Store ответит `ITEM_NOT_UPDATABLE`: шаг завершится предупреждением,
   а не ошибкой. Дождаться проверки (или отменить её в https://chrome.google.com/webstore/devconsole) и перезапустить
   Actions → extension-release. Только загрузить, без отправки на проверку: Actions → extension-release → Run workflow
   с `publish=false`.
5. Краткое описание в магазинах («Summary») берётся из пакета: `description` в манифесте = `__MSG_extDescription__` из
   `extension/_locales/{en,ru}/messages.json` (до 132 знаков). Полное описание, скриншоты и обоснования разрешений
   вставляются в дашборд вручную — тексты в `store/LISTING.md`. Не перечислять в описании словари и лицензии: 0.2.3
   отклоняли за «Keyword Spam».
6. Firefox уходит в AMO из того же запуска (job `firefox`, только при `publish=true` — у AMO нет «загрузить без проверки»).
   Повторный запуск той же версии AMO не примет — это предупреждение, не ошибка. Без секретов `AMO_JWT_*` — загрузить
   `hanzi-burst-firefox.zip` (https://hanzi.lipu.dev/hanzi-burst-firefox.zip) вручную в
   https://addons.mozilla.org/developers/addon/hanzi-burst/versions/submit/; на вопрос об исходниках — «нет»
   (JS копируется как есть, `data/` — сгенерированные словарные JSON). Тексты листинга AMO правятся в devhub вручную.
