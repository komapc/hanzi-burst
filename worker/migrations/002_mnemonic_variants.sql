-- Первая версия таблицы хранила один текст на (ch, lang). Данных в ней ещё не было.
DROP TABLE IF EXISTS mnemonics;
CREATE TABLE mnemonics (
  ch TEXT NOT NULL,
  lang TEXT NOT NULL,
  variant INTEGER NOT NULL,
  text TEXT NOT NULL,
  model TEXT,
  prompt_version INTEGER NOT NULL,
  created_by TEXT,
  created_at INTEGER NOT NULL,
  PRIMARY KEY (ch, lang, variant)
);
