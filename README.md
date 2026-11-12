# hanzi-burst

Учим китайские иероглифы через разбор на радикалы.

## Идея (сырая)

- Простые тексты на китайском (адаптированные новости, учебные тексты, «фраза дня»).
- Клик/ховер на иероглиф (или слово из 2–3 иероглифов): значение + разбивка на радикалы с объяснением.
- Визуально радикалы «разлетаются» из иероглифа.
- Мнемоника: пусть глупое, но объяснение, почему иероглиф значит именно это; если есть фонетик — почему так звучит.
- Связи: «этот радикал уже был в иероглифе X», «этот иероглиф был во фразе Y».
- LLM для генерации объяснений/текстов, логин для хранения прогресса.
- Аудитория: новички (чуть выше нулевого уровня).

## Статус

Сайт работает на https://hanzi.lipu.dev (бренд «Hanzi Burst»). Расширение для браузера (`extension/`):
Chrome Web Store — 0.2.3 опубликована (одобрена 2026-10-30); Firefox (addons.mozilla.org, листинг `hanzi-burst`) —
0.2.3 отправлена 2026-10-29, ждёт проверки. Подробнее — `extension/README.md` и `store/LISTING.md`.

## Запуск

```bash
# 1. Сырые данные (в гит не кладутся) -> data/raw/{mmh,cedict,unicode,unihan}
#    Make Me a Hanzi: dictionary.txt, graphics.txt (github.com/skishore/makemeahanzi)
#    CC-CEDICT: cedict_ts.u8, Unicode: CJKRadicals.txt, Unihan.zip (распаковать)
# 2. Разбор фразы -> site/phrase.json + site/glyphs.json
python3 -I scripts/breakdown.py "我想学汉字" site/phrase.json
# 3. Сайт
cd site && python3 -m http.server 8765   # http://127.0.0.1:8765/?open=想&explode=1&lang=ru
```

## Устройство

- `scripts/breakdown.py`: сегментация фразы (CC-CEDICT), рекурсивная разбивка на компоненты и этимология (Make Me a Hanzi),
  запасные описания для вариантов радикалов (Unicode, Unihan), контуры черт для SVG.
- `data/translations/ru.json`: переводы определений, подсказок и слов {en: ru} (черновик, переведено вручную).
- `site/`: статическая страница, иероглифы рисуются SVG по контурам, язык RU/EN, «известные» в localStorage.

## Добавление фраз

```bash
# сырые данные Tatoeba: data/raw/tatoeba/ (cmn_sentences, cmn-eng_links, cmn-rus_links, eng_sentences, rus_sentences .tsv.bz2
# с https://downloads.tatoeba.org/exports/per_language/)
python3 -I scripts/fetch_phrases.py --count 40 --max-new 2   # --dry-run чтобы посмотреть без записи
python3 -I scripts/breakdown.py data/phrases.json site/phrase.json
```

Скрипт выбирает фразы как учебную программу: мало новых иероглифов относительно уже имеющихся фраз, оба перевода (ru, en) берутся из Tatoeba.
Для новых иероглифов нужны русские переводы определений в `data/translations/ru.json` (без них показывается английский).

## Данные и лицензии

Make Me a Hanzi (LGPL/Arphic), CC-CEDICT (CC BY-SA), Unicode/Unihan (Unicode License), JMdict и KANJIDIC2 (EDRDG, CC BY-SA 4.0), KanjiVG (Ulrich Apel, CC BY-SA 3.0), фразы и их переводы: Tatoeba (CC BY 2.0 FR, авторы указаны на tatoeba.org по номеру в `source`). Атрибуция: страница `/about` (`site/about.html`) и `extension/NOTICE.txt` в пакете расширения.

## Бэкенд и деплой (Cloudflare Workers + D1)

Один Worker отдаёт статику из `site/` и `/api/*` (`worker/index.js`): вход через Google, список «известных», запоминалки через Gemini (кэш в D1, лимит в сутки).
Без бэкенда (обычный статический сервер) страница работает, кнопки входа и запоминалок просто не показываются.

Первоначальная настройка (один раз, уже сделана):

```bash
npm i -g wrangler && wrangler login
wrangler d1 create hanzi-burst            # id вписать в wrangler.toml
wrangler d1 execute hanzi-burst --remote --file worker/schema.sql
wrangler secret put GOOGLE_CLIENT_ID      # Google Cloud Console -> OAuth client (Web), origin = домен сайта
wrangler secret put SESSION_SECRET        # openssl rand -base64 32
wrangler secret put GEMINI_API_KEY
```

Секреты Worker хранятся в Cloudflare и при деплое не трогаются. Изменения схемы D1 (`worker/schema.sql`) применяются вручную, деплой их не накатывает.

## Деплой

Деплой делает CI (`.github/workflows/deploy.yml`):

| Событие | Что происходит |
|---|---|
| PR | полная сборка + `wrangler deploy --dry-run`, ничего не публикуется |
| push в `main` | сборка + деплой на hanzi.lipu.dev, проверка, что сайт отдаёт zip расширения нужной версии |
| push тега `v*` | то же + загрузка расширения в Chrome Web Store с отправкой на проверку (`extension-release.yml`) |
| Actions → deploy → Run workflow | передеплой текущего `main` |

Сборка — команда `[build]` в `wrangler.toml`: `build_shards.py` → `build_ja_shards.py` → `build_kanji_shards.py` → `build_static.py` → `build_extension.py --zip` → `minify.py` (terser через npx сжимает `script.js`, `ja.js`, `footer.js` и инлайн-скрипты страниц; только в CI или с `--force DIR`, при ошибке оставляет исходник). Ей нужны `data/raw/` (в гит не кладутся) и Pillow. CI берёт `data/raw/` из закреплённого снимка — ассет `raw-data.tar.xz` релиза `raw-data-YYYY-MM-DD` (тег и sha256 — в `env` у `deploy.yml`). В снимке только то, что читает сборка: `mmh/{dictionary,graphics}.txt`, `cedict/cedict_ts.u8`, `unicode/CJKRadicals.txt`, `unihan/Unihan_*.txt`, `ids/ids.txt`, `hsk/complete.json`, `jmdict/jmdict-{eng,rus}-*.json` (японский словарь, [jmdict-simplified](https://github.com/scriptin/jmdict-simplified/releases)).

Секреты репозитория (Settings → Secrets → Actions):

- `CLOUDFLARE_API_TOKEN` — https://dash.cloudflare.com/profile/api-tokens, шаблон «Edit Cloudflare Workers» + Account → D1 → Edit.
- `CWS_EXTENSION_ID`, `CWS_CLIENT_ID`, `CWS_CLIENT_SECRET`, `CWS_REFRESH_TOKEN` — Chrome Web Store API (OAuth-клиент `hanzi-burst-ci-desktop` в Google Cloud, проект hanzi-burst-ci).
- `AMO_JWT_ISSUER`, `AMO_JWT_SECRET` — ключ API addons.mozilla.org (https://addons.mozilla.org/developers/addon/api/key/, «JWT issuer» и «JWT secret»). Без них Firefox пропускается с предупреждением.

### Выпуск новой версии расширения

1. Поднять `version` в `extension/manifest.json`, смёржить в `main` (сайт задеплоится сам).
2. `git tag v<версия> && git push origin v<версия>` — CI задеплоит этот коммит (только если он — текущий HEAD `main`: тег на старом коммите прод не откатывает), загрузит расширение в Web Store на проверку
   и отправит Firefox-сборку на addons.mozilla.org (`web-ext sign --channel listed`; проверку AMO делает человек, CI её не ждёт).
3. Если предыдущая версия ещё на проверке, Web Store ответит `ITEM_NOT_UPDATABLE`: шаг завершится предупреждением, а не ошибкой. Дождаться проверки (или отменить её в https://chrome.google.com/webstore/devconsole) и перезапустить Actions → extension-release.
   Только загрузить, без отправки на проверку: Actions → extension-release → Run workflow с `publish=false`.
4. Краткое описание в магазинах («Summary») берётся из пакета: `description` в манифесте = `__MSG_extDescription__` из
   `extension/_locales/{en,ru}/messages.json` (до 132 знаков). Полное описание, скриншоты и обоснования разрешений вставляются
   в дашборд вручную — тексты в `store/LISTING.md`. Не перечислять в описании словари и лицензии: 0.2.3 отклоняли за «Keyword Spam».
5. Firefox уходит в AMO из того же запуска (job `firefox`, только при `publish=true` — у AMO нет «загрузить без проверки»).
   Повторный запуск той же версии AMO не примет — это предупреждение, не ошибка. Без секретов `AMO_JWT_*` — загрузить
   `hanzi-burst-firefox.zip` (https://hanzi.lipu.dev/hanzi-burst-firefox.zip) вручную в
   https://addons.mozilla.org/developers/addon/hanzi-burst/versions/submit/; на вопрос об исходниках — «нет»
   (JS копируется как есть, `data/` — сгенерированные словарные JSON). Тексты листинга AMO правятся в devhub вручную.

### Обновление снимка data/raw/

```bash
cd data/raw && tar -cJf /tmp/raw-data.tar.xz mmh/dictionary.txt mmh/graphics.txt cedict/cedict_ts.u8 \
  unicode/CJKRadicals.txt unihan/Unihan_*.txt ids/ids.txt hsk/complete.json jmdict/jmdict-eng-*.json jmdict/jmdict-rus-*.json \
  kanjidic/kanjidic2.xml.gz kanjivg/kanjivg-*.xml.gz
sha256sum /tmp/raw-data.tar.xz
gh release create raw-data-$(date +%F) /tmp/raw-data.tar.xz --prerelease --title "raw-data-$(date +%F) (build inputs)" --notes "data/raw/ snapshot for deploy.yml"
```

Затем вписать новый тег и sha256 в `RAW_DATA_TAG` / `RAW_DATA_SHA256` в `deploy.yml`. Имя тега не должно начинаться с `v` (такие теги запускают выпуск расширения).

### Ручной деплой (запасной вариант)

При наличии `data/raw/` и Pillow: `npx wrangler deploy` из корня репозитория — та же сборка, что в CI.

## Пул фраз и кнопка «Новая фраза»

`data/pool.json` — пул из 1000 фраз Tatoeba (`fetch_phrases.py --count 1000 --max-new 3 --out data/pool.json`), собирается в `site/pool.json` (грузится лениво). После `fetch_*.py` запускайте `python3 -I scripts/clean_pool.py`: он убирает именные группы и обрывки, оставляя только предложения. Кнопка «Новая фраза» выбирает фразу с минимумом ещё не виденных иероглифов (известные + уже показанные); полученные фразы запоминаются в localStorage (`hanzi-seen-pool`) и попадают в выпадающий список. Данные Tatoeba — CC BY 2.0 FR.

## Японский режим (中 / 日)

Переключатель 中 / 日 в шапке (`localStorage hanzi-mode`, ссылка `/?mode=ja`). В режиме 日:

- фразы берутся из `site/pool-ja.json` (≈2700 предложений японского Tatoeba с переводами; `python3 -I scripts/build_ja_pool.py`, результат коммитится, как `site/pool.json`; сырые файлы `data/raw/tatoeba/jpn*` в снимок не входят). Слова и чтения считает клиент (`site/ja.js`, JMdict) при первом показе фразы. «Новая фраза» берёт фразу с минимумом новых кандзи и младшим школьным классом; полученные фразы — `hanzi-seen-ja`;
- кандзи и кана рисуются чертами KanjiVG, разбор на части — по группам KanjiVG, чтения (он/кун) и английские значения — KANJIDIC2, русское значение — значение однознакового слова JMdict с кун-чтением (это значение слова, оно помечено). Шарды `site/data/kanji/` строит `build_kanji_shards.py` при деплое;
- переключатели 拼音/注音 и 简/繁 скрыты; японский текст (`lang="ja"`) не переводится в традиционные знаки.

Своя фраза с каной включает режим 日 сама, китайская — режим 中.

## Предзаполненные запоминалки

`data/mnemonics_prefill.json` — по одной запоминалке (RU и EN) для каждого из 629 иероглифов, написаны моделью по правилам промпта Worker. Залиты в D1 (`mnemonics`, variant 1, `model = 'claude-sonnet-5-5 (prefill)'`, `prompt_version = 2`) через `INSERT OR IGNORE`; «Ещё вариант» по-прежнему просит Gemini. Идеи на будущее — в `ROADMAP.md`.

## Своя фраза (вставка текста)

`python3 -I scripts/build_shards.py` строит `site/data/` (шарды иероглифов, контуров и слов CC-CEDICT по `кодпоинт>>8`, плюс `trad.json`). Каталог в `.gitignore`, генерируется командой `[build]` в `wrangler.toml` при деплое. Клиент грузит нужные шарды лениво, сегментирует текст и открывает обычный интерактивный разбор. Ссылка: `/?t=<текст>`.

## Дыры «？» в разборе

В Make Me a Hanzi у части знаков один компонент записан как «？» (曷 = ⿱日？). `breakdown.py` (`fill_holes`) заполняет такие места разбором из cjkvi-ids (`data/raw/ids/ids.txt`, https://github.com/cjkvi/cjkvi-ids, производное от CHISE IDS, GPL). Берутся только случаи, где все части — обычные унифицированные иероглифы или радикалы (их можно показать шрифтом, контуров у них нет). Остальное помечается в интерфейсе как «неполное дерево» (`incomplete`). Данные IDS не копируются в репозиторий (`data/raw/` в `.gitignore`), в сборку попадают только полученные разборы отдельных знаков.

## Традиционные / упрощённые

Радио-кнопки 简 / 繁 в шапке `index.html` (выбор в `localStorage hanzi-script`). Данные и ссылки остаются упрощёнными; подменяется только отображение: текстовые узлы (`site/script.js`) и начертания SVG (`syncScript` в `index.html`, глифы традиционных знаков берутся из шардов `data/g`). Карта `site/data/s2t.json` строится в `build_shards.py` по частоте пар в словах CC-CEDICT (омографы вроде 发 → 發/髮 дают самый частый вариант). Статические страницы `/c/`, `/p/` всегда упрощённые.

## Вид фразы: скрыть чтение и перевод, цвет тонов

Кнопки над фразой (`#view`, `localStorage hanzi-view`): «Пиньинь» (в японском режиме «Чтение») и «Перевод» скрывают подписи для самопроверки. Скрытое чтение — серая полоска, нажатие открывает чтение одного слова (`revealed`, сбрасывается при смене фразы); скрытый перевод размыт, нажатие открывает его вместе с пословным разбором, всплывающие подсказки со значениями тоже скрыты. «Тоны» раскрашивают пиньинь и бопомофо по тону (`--t1…--t5`, по умолчанию включено). В японском режиме акцентный цвет — индиго.

## Телефон, фуригана, первый вход

- На экранах ≤640px карточка иероглифа выезжает снизу (фраза остаётся видна); закрыть — «×», Esc или потянуть вниз за ручку.
- В японском режиме над группами кандзи — фуригана (кана), под словом — транскрипция; чтение сопоставляется с окуриганой (`furi`), группа кандзи не делится.
- Первый вход (`hanzi-tour`): пульсирующий иероглиф фразы, затем подсказка про части и «+». У кого в localStorage уже есть фразы или «известные», тур не показывается.

## Прогресс по HSK

На странице «Мои иероглифы» — полоски по уровням HSK 3.0: сколько знаков уровня отмечено «Знаю». Клик по уровню
показывает неотмеченные знаки (частые первыми). Знаки по уровням — `site/data/hsk.json` из `build_shards.py`:
уровень знака = самый низкий уровень слова HSK, где он встречается (выходит 300/299/301/305/310/518/1001,
почти ровно официальный список знаков).

Для поисковиков — статические списки `/hsk/1` … `/hsk/7` (7 = уровни 7–9) и хаб `/hsk/` из `build_static.py`:
знак, пиньинь, первое значение; ссылка на `/c/<код>` или `/?open=<знак>`, если своей страницы у знака нет.

## Статические страницы и SEO

`build_static.py` строит `/c/<hex>` (знаки), `/p/` (фразы), `/hsk/`, `/k/<hex>` (кандзи, `scripts/kanji_pages.py`), `/r/<hex>` и `/en/r/<hex>` (214 ключей Канси, `scripts/radical_pages.py`), `sitemap.xml`.
Таблица ключей `data/radicals.json` коммитится; её собирает `scripts/build_radicals.py` (запускать вручную после правки названий и вариантов в `scripts/radical_names.py`). Частые ключи (`top`, первые 60 по числу знаков HSK) идут первыми в указателе `/r/`. Карточки для печати `site/radicals-{ru,en}.pdf` тоже коммитятся: после правки таблицы пересобрать `python3 scripts/radicals_pdf.py` (нужны `google-chrome` и шрифт Noto CJK). Плакат на одну страницу A2 `site/radicals-poster-{ru,en,eo}.pdf` и его превью `site/radicals-poster-{ru,en,eo}.jpg` — `python3 scripts/radicals_poster.py` (QR-код рисует пакет `segno`, метаданные PDF — `pypdf`, превью — ImageMagick). Страницы плаката `/r/poster`, `/en/r/poster`, `/eo/r/poster` (описание, превью, hreflang, JSON-LD) собирает `radical_pages.py`; названия ключей на эсперанто (`eo`) — в `scripts/radical_names.py`.

Английские версии: `/en/c/<hex>`, `/en/c/`, `/en/p/<id>`, `/en/p/`, `/en/hsk/`, `/en/hsk/N` со своими canonical и взаимными `hreflang` ru↔en (`x-default` — русская версия); значения только английские. Ссылки «в приложение» с английских страниц добавляют `lang=en`. Кандзи `/k/` — только по-русски.

- Заголовки: главная «Разбор китайских иероглифов на ключи и радикалы — Hanzi Burst» (H1 «Разбор китайских иероглифов на
  ключи», по-английски «Chinese characters broken down into radicals»; бренд — мелкой надписью в шапке); знак «Иероглиф 吗 (ma): значение и
  разбор на ключи | Hanzi Burst», ключ «Ключ 口 (kǒu): значение и иероглифы с ним | Hanzi Burst»; по-английски
  «吗 ma — meaning, radicals and components | Hanzi Burst» и «Radical 口 kǒu — meaning and characters that use it | Hanzi Burst». Дубликатов title и
  description нет — проверять после правок шаблона.
- Страница знака, кроме разбора: уровень HSK (ссылка на `/hsk/N`), до 10 слов CC-CEDICT (сначала слова HSK), до 8 фраз,
  «Где встречается этот ключ» / «Иероглифы, в которых есть X» (до 20 + общее число), «Похожие по написанию» (до 12).
  Всё из данных сборки, без текста от LLM.
- Страницы кандзи `/k/<hex>` — 2136 знаков дзёё (KANJIDIC2: классы 1–6 и средняя школа), только по-русски: онъёми и кунъёми
  каной и кириллицей (Поливанов, как `transcribe` в `ja.js`; окуригана серым), значения KANJIDIC2, класс, число черт, старый
  уровень JLPT, состав по KanjiVG, «Кандзи, в которых есть X», похожие, до 10 частых слов JMdict (только кандзи дзёё и хирагана),
  до 8 фраз из `pool-ja.json` (ссылки `/?t=<фраза>` открывают режим 日). Русское значение знака берётся из китайских шардов,
  если английское значение CC-CEDICT совпадает с одним из значений KANJIDIC2 (иначе 机 стал бы «машиной»), затем — глосса JMdict.
  Хаб `/k/` — по классам. `/c/X` и `/k/X` одного знака ссылаются друг на друга.
- `sitemap.xml` — только хабы, `/hsk/*`, знаки HSK 1–3 и кандзи 1 класса, плюс те же хабы, HSK и знаки HSK 1–3 под `/en/`. Остальные `/c/`, `/en/c/` и все страницы фраз не в sitemap, но и не
  `noindex`: тысячи шаблонных страниц в sitemap мешали индексации (на 2026-10-29 Google не индексировал сайт).
- Подтверждения владения: `site/yandex_075f1191e804f3a2.html` (Яндекс Вебмастер), `site/BingSiteAuth.xml` — не удалять.
  Google Search Console — доменный ресурс `sc-domain:lipu.dev`.

## Загрузка и доступность

Контуры черт лежат в шардах `site/data/g/<cp>>4>.json` по 16 знаков (~18 КБ): страница грузит только шарды показанных
знаков (`loadGlyphs`), а `MutationObserver` заменяет текстовые заглушки `span.serif[data-c]` на SVG, когда контуры пришли.
Шарды `data/*` кэшируются на сутки (+ неделя stale-while-revalidate), остальной JSON — на час (`site/_headers`).
Цвета (приглушённый текст, тоны, «Знаю», кнопки) подобраны под контраст WCAG AA в светлой и тёмной теме; проверка — axe-core.

## Русские значения

`data/translations/ru.json` покрывает основные значения всех знаков HSK 1–9 и чтения их 多音字. Неверные или
редкие первые значения MMH (机 «desk», 离 «rare beast», 着 «to make a move»…) заменяет `DEFINITION_OVERRIDES` в `breakdown.py`.

## Поиск знака и фраза дня

Поле справа от переключателей вида: иероглиф открывается сразу (в режиме 日 — кандзи), пиньинь даёт список знаков —
`xiang`, `xiang3`, `xiǎng`, `lü4`/`lv4`. Индекс `site/data/pyindex.json` (слог+тон и слог без тона → до 24 знаков,
частые первыми; только упрощённые) строит `scripts/build_shards.py`.

«☀ Фраза дня» — одна на день для всех (выбор по дате), из пула: HSK 1–3 с русским переводом, в режиме 日 — кандзи 1–2 класса.
Ссылка `/?day` открывает её сразу.

## Бопомофо

Переключатель `abc` / `ㄅㄆ` в шапке (`localStorage hanzi-phon`, по умолчанию пиньинь). Конвертер пиньинь → 注音 (`ZY` в `index.html`) работает на лету, данные не меняются; применяется к подписям над иероглифами, заголовку описания и спискам слов. Подсказки (hover) и тексты запоминалок остаются в пиньине.

## Пул фраз и уровни HSK

`scripts/build_tatoeba_pool.py` отбирает из всего китайского Tatoeba (≈89 тыс.) простые целые предложения (4–16 знаков, знаки из топ-1300 по частоте, есть английский перевод; русский в приоритете) по квотам на уровень HSK (3000 штук) и заменяет ими старые записи Tatoeba в `data/pool.json`. Уровень слов берётся из `data/raw/hsk/complete.json` (drkameleon/complete-hsk-vocabulary, MIT; HSK 3.0, 7 = уровни 7–9) через `scripts/hsk.py`; `breakdown.py` кладёт `hsk` в каждую фразу. «Новая фраза» сначала минимизирует число новых знаков, при равенстве берёт более низкий уровень. Слова фраз из пула получают значения из шардов `data/words/` при открытии; `usage.json` грузится отдельно после старта.
