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

Локальный прототип на одной фразе (我想学汉字).

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

Make Me a Hanzi (LGPL/Arphic), CC-CEDICT (CC BY-SA), Unicode/Unihan (Unicode License), фразы и их переводы: Tatoeba (CC BY 2.0 FR, авторы указаны на tatoeba.org по номеру в `source`). Атрибуцию добавить перед публикацией.

## Бэкенд и деплой (Cloudflare Workers + D1)

Один Worker отдаёт статику из `site/` и `/api/*` (`worker/index.js`): вход через Google, список «известных», запоминалки через Gemini (кэш в D1, лимит в сутки).
Без бэкенда (обычный статический сервер) страница работает, кнопки входа и запоминалок просто не показываются.

```bash
npm i -g wrangler && wrangler login
wrangler d1 create hanzi-burst            # id вписать в wrangler.toml
wrangler d1 execute hanzi-burst --remote --file worker/schema.sql
wrangler secret put GOOGLE_CLIENT_ID      # Google Cloud Console -> OAuth client (Web), origin = домен сайта
wrangler secret put SESSION_SECRET        # openssl rand -base64 32
wrangler secret put GEMINI_API_KEY
wrangler deploy
```

## Пул фраз и кнопка «Новая фраза»

`data/pool.json` — пул из 1000 фраз Tatoeba (`fetch_phrases.py --count 1000 --max-new 3 --out data/pool.json`), собирается в `site/pool.json` (грузится лениво). После `fetch_*.py` запускайте `python3 -I scripts/clean_pool.py`: он убирает именные группы и обрывки, оставляя только предложения. Кнопка «Новая фраза» выбирает фразу с минимумом ещё не виденных иероглифов (известные + уже показанные); полученные фразы запоминаются в localStorage (`hanzi-seen-pool`) и попадают в выпадающий список. Данные Tatoeba — CC BY 2.0 FR.

## Предзаполненные запоминалки

`data/mnemonics_prefill.json` — по одной запоминалке (RU и EN) для каждого из 629 иероглифов, написаны моделью по правилам промпта Worker. Залиты в D1 (`mnemonics`, variant 1, `model = 'claude-sonnet-5-5 (prefill)'`, `prompt_version = 2`) через `INSERT OR IGNORE`; «Ещё вариант» по-прежнему просит Gemini. Идеи на будущее — в `ROADMAP.md`.

## Своя фраза (вставка текста)

`python3 -I scripts/build_shards.py` строит `site/data/` (шарды иероглифов, контуров и слов CC-CEDICT по `кодпоинт>>8`, плюс `trad.json`). Каталог в `.gitignore`, генерируется командой `[build]` в `wrangler.toml` при деплое. Клиент грузит нужные шарды лениво, сегментирует текст и открывает обычный интерактивный разбор. Ссылка: `/?t=<текст>`.

## Дыры «？» в разборе

В Make Me a Hanzi у части знаков один компонент записан как «？» (曷 = ⿱日？). `breakdown.py` (`fill_holes`) заполняет такие места разбором из cjkvi-ids (`data/raw/ids/ids.txt`, https://github.com/cjkvi/cjkvi-ids, производное от CHISE IDS, GPL). Берутся только случаи, где все части — обычные унифицированные иероглифы или радикалы (их можно показать шрифтом, контуров у них нет). Остальное помечается в интерфейсе как «неполное дерево» (`incomplete`). Данные IDS не копируются в репозиторий (`data/raw/` в `.gitignore`), в сборку попадают только полученные разборы отдельных знаков.

## Традиционные / упрощённые

Радио-кнопки 简 / 繁 в шапке `index.html` (выбор в `localStorage hanzi-script`). Данные и ссылки остаются упрощёнными; подменяется только отображение: текстовые узлы (`site/script.js`) и начертания SVG (`syncScript` в `index.html`, глифы традиционных знаков берутся из шардов `data/glyphs`). Карта `site/data/s2t.json` строится в `build_shards.py` по частоте пар в словах CC-CEDICT (омографы вроде 发 → 發/髮 дают самый частый вариант). Статические страницы `/c/`, `/p/` всегда упрощённые.
