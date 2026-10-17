# Chrome Web Store: Hanzi Burst (v0.1.0)

## Store listing

**Name:** Hanzi Burst
**Category:** Education (Productivity is the alternative)
**Language:** English (add a Russian localization in the Store Listing tab)

**Summary (max 132 chars):**
Select or hover Chinese text to see pinyin, meaning and how every character breaks into parts. Works offline.

**Description (EN):**
Hanzi Burst helps you read Chinese and learn characters in context.

Select Chinese text on any page, or just hover over it, and a card shows:
• pinyin and the meaning of the word
• the full breakdown of every character into its component parts, down to the radicals, with pinyin and meaning for each part
• which parts you already know

Mark characters as known with one click. Tiles are painted green (known), blue (all parts known) or amber (some parts known). The "My characters" page lists what you know and what is ready to learn next. The list stays on your device and can be copied to or from hanzi.lipu.dev.

Features
• Two modes: selection or mouse hover
• Simplified and traditional characters
• Interface in English and Russian
• Dark theme
• Turn off per site in one click
• Fully offline: the dictionary ships inside the extension, nothing is sent anywhere
• No ads, no analytics, no account

Dictionary data: Make Me a Hanzi (LGPL), CC-CEDICT (CC BY-SA 4.0), Unicode/Unihan. See NOTICE.txt in the package.

**Описание (RU):**
Hanzi Burst помогает читать по-китайски и учить иероглифы в контексте.

Выделите китайский текст на любой странице или просто наведите на него курсор: появится карточка с пиньинем, значением слова и полной разбивкой каждого иероглифа на составные части (вплоть до ключей), с пиньинем и значением каждой части. Отмечайте известные иероглифы одним кликом: они подсвечиваются, а страница «Мои иероглифы» показывает, что вы уже знаете и что пора учить следующим.

Два режима (выделение или наведение), упрощённые и традиционные знаки, интерфейс на русском и английском, тёмная тема, отключение на отдельных сайтах. Работает полностью офлайн: словарь внутри расширения, ничего никуда не отправляется. Без рекламы, аналитики и аккаунтов.

## Assets (in this folder)
- shot1.png, shot2.png, shot3.png: screenshots 1280x800 (up to 5 allowed)
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
