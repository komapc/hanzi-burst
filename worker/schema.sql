CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,          -- Google sub
  email TEXT,
  name TEXT,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS known (
  user_id TEXT NOT NULL,
  ch TEXT NOT NULL,
  added_at INTEGER NOT NULL,
  PRIMARY KEY (user_id, ch)
);

-- Кэш запоминалок: общий для всех пользователей, до 3 вариантов на (иероглиф, язык).
-- Ключ включает variant, поэтому гонка двух запросов не плодит дубли (первый записавший выигрывает).
-- prompt_version: поднимаем в worker/index.js при смене промпта, старые строки тогда игнорируются.
CREATE TABLE IF NOT EXISTS mnemonics (
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

-- Лимит обращений к LLM на пользователя в сутки.
CREATE TABLE IF NOT EXISTS usage (
  user_id TEXT NOT NULL,
  day TEXT NOT NULL,
  n INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, day)
);
