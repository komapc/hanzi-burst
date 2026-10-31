# Chrome Web Store: Hanzi Burst (v0.2.4)

Notes only: nothing here is published automatically. Paste the texts into the Chrome Web Store
dashboard (Store listing tab, EN and the RU localization) by hand.
As of 2026-10-29 the live store still shows the pre-0.2 text (summary "Select Chinese text on any
page to see pinyin, meaning and how each character breaks down into parts. Works offline." and the
old description without Japanese); the texts below are the ones to paste.

**2026-10-29: 0.2.3 was rejected for "Keyword Spam" (violation ID Yellow Argon).** The flagged text was the
dictionary-credits line in the RU description (a list of dataset names and licenses). Do not list the
datasets in the store description: credits live in NOTICE.txt and on /about, which satisfies the
CC BY-SA attribution. The descriptions below already have the one-line replacement.

## Store listing

**Name:** from the package (`extName` in `extension/_locales/{en,ru}/messages.json`): "Hanzi Burst: Chinese Pinyin Popup Dictionary" / "Hanzi Burst — словарь иероглифов с пиньинем" (since 0.2.4; `short_name` stays "Hanzi Burst")
**Category:** Education (Productivity is the alternative)
**Language:** English (add a Russian localization in the Store Listing tab)

**Summary (EN, 121 of 132 chars):** the store takes it from the package (`extension/_locales/en/messages.json` → manifest `description`), not from the dashboard.
Chinese & Japanese popup dictionary: hover for pinyin or kana, meaning and a radical-by-radical breakdown. Works offline.

**Description (EN):**
Hanzi Burst is a Chinese & Japanese popup dictionary that helps you read Chinese and learn characters (hanzi) in context.

Hover over Chinese text on any page, hover while holding Alt, or select it, and a card shows:
• pinyin and the meaning of the whole word, plus every character on its own
• the full breakdown of every character into its components, down to the radicals, with pinyin and meaning for each part
• which parts you already know

Pinyin over the whole page: switch it on in the popup, or for the current tab only via right-click → "pinyin on this page". Readings go by words: 银行 is yín háng. On Japanese pages it shows furigana over kanji.

Japanese: when the text has kana or the page is marked as Japanese, the card shows words with their reading (kana and romaji), the dictionary form of verbs (見ました → 見る), and on/kun readings plus parts for each kanji.

Mark characters as known with one click. Tiles are painted green (known), blue (all parts known) or amber (some parts known). The "My characters" page shows your progress by HSK 3.0 level and what is ready to learn next. The list stays on your device and is merged with your list on hanzi.lipu.dev in the same browser.

Features
• Three triggers: mouse hover, hover with Alt, or selection; plus a "Hanzi Burst" item in the right-click menu
• Pinyin (Chinese) or furigana (Japanese) over page text
• HSK 3.0 progress
• Simplified and traditional characters
• Glosses and interface in English and Russian
• Dark theme
• Turn off per site in one click
• Fully offline: the dictionaries ship inside the extension, nothing is sent anywhere
• No ads, no analytics, no account

Built on open dictionary data; full credits and licenses are in NOTICE.txt and on hanzi.lipu.dev/about.

**Краткое описание (RU, 121 из 132 знаков):** берётся из пакета (`extension/_locales/ru/messages.json`).
Китайско-японский словарь при наведении: пиньинь или кана, значение и разбор иероглифа на ключи и части. Работает офлайн.

**Описание (RU):**
(Перевод EN-описания выше, 2026-10-29.)

Hanzi Burst — китайско-японский словарь при наведении: помогает читать по-китайски и учить иероглифы в контексте.

Наведите курсор на китайский текст на любой странице, наведите с зажатым Alt или выделите его, и появится карточка:
• пиньинь и значение слова целиком и каждого иероглифа отдельно
• полный разбор каждого иероглифа на составные части вплоть до ключей (радикалов), с пиньинем и значением каждой части
• какие части вы уже знаете

Пиньинь над всей страницей: переключатель в настройках или, только для текущей вкладки, контекстное меню → «pinyin on this page». Чтение берётся по словам: 银行 — yín háng. На японских страницах — фуригана над кандзи.

Японский: если в тексте есть кана или страница помечена как японская, карточка показывает слова с чтением (кана, ромадзи или кириллица по Поливанову), словарную форму глагола (見ました → 見る), а для кандзи — онные и кунные чтения и части.

Отмечайте известные иероглифы одним кликом. Плитки подсвечиваются зелёным (знаю), синим (знаю все части) или жёлтым (знаю часть частей). Страница «Мои иероглифы» показывает прогресс по уровням HSK 3.0 и подсказывает, что учить следующим. Список хранится на вашем устройстве и объединяется со списком на hanzi.lipu.dev в том же браузере.

Возможности
• Три способа: наведение курсора, наведение с Alt или выделение; плюс пункт «Hanzi Burst» в контекстном меню
• Пиньинь (китайский) или фуригана (японский) над текстом страницы
• Прогресс по HSK 3.0
• Упрощённые и традиционные знаки
• Переводы и интерфейс на русском и английском
• Тёмная тема
• Отключение на отдельном сайте одним кликом
• Полностью офлайн: словари внутри расширения, ничего никуда не отправляется
• Без рекламы, аналитики и аккаунтов

Основано на открытых словарных данных; полный список источников и лицензий — в NOTICE.txt и на hanzi.lipu.dev/about.

## Assets (in this folder)
- shot1.png, shot2.png, shot3.png, shot4.png: screenshots 1280x800 (up to 5 allowed); shot4 = card for 战略 on zh.wikipedia
- tile_440x280.png: small promo tile (required)
- Icon 128x128: taken from the package (icons/128.png)
- Optional: marquee 1400x560 (not made)

## Links
- Website: https://hanzi.lipu.dev/extension
- Privacy policy URL: https://hanzi.lipu.dev/privacy#extension
- Support: GitHub profile https://github.com/komapc (repo is private; use the site or a public issues repo)

## Privacy tab answers
**Single purpose:** Show pinyin, meaning and a component breakdown for Chinese text the user selects or hovers on a web page.

**Permission justifications**
- `storage`: saves the user's settings (mode, language, on/off, per-site opt-outs) and their list of known characters, locally.
- `activeTab`: lets the toolbar popup read the current tab's hostname to show it and to switch the extension off on that site.
- Host access / content script on `http://*/*`, `https://*/*`: the card must appear when the user selects or hovers Chinese text on any website the user reads. The script reads only the selected or hovered text, locally, and makes no network requests.
- Remote code: **No.** All code and data are in the package.

**Data usage disclosure (checkboxes):** "Website content" and "User activity" are handled only on-device. The safest honest answer is to tick none of the collection boxes, because nothing is transmitted off the device. If the form's wording forces a choice, note "processed locally, not collected". Certify all three statements (no sale, no unrelated use, no creditworthiness use).

## Review risk
The broad content-script match is the usual cause of slower review ("in-depth review"). Mitigation: the justification above, the privacy policy, no remote code, no network calls. Not switching to `<all_urls>` and not using `host_permissions` already keeps the footprint small.
