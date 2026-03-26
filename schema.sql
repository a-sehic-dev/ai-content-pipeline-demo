-- AI Content Pipeline Demo - SQLite schema
-- Notes:
-- - SQLite is used as a lightweight stand-in for Supabase/Postgres.
-- - JSON fields are stored as TEXT for simplicity.
-- - Timestamps are stored as ISO-8601 text (UTC).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS services (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS websites (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  service_id INTEGER NOT NULL,
  city TEXT NOT NULL,
  country TEXT,
  language TEXT NOT NULL,             -- e.g. de, en, nl
  domain TEXT NOT NULL UNIQUE,        -- e.g. berlin-roofing.example
  brand_name TEXT,                    -- optional display name
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS social_accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  website_id INTEGER NOT NULL,
  platform TEXT NOT NULL,             -- facebook, instagram, linkedin, etc.
  handle TEXT,                        -- e.g. @berlinroofing
  external_account_id TEXT,           -- placeholder for real platform IDs
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  UNIQUE (website_id, platform),
  FOREIGN KEY (website_id) REFERENCES websites(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS content_campaigns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  service_name TEXT NOT NULL,         -- campaign-level service filter
  content_idea TEXT NOT NULL,
  cta TEXT,
  link TEXT,
  selected_platforms_json TEXT NOT NULL,  -- JSON array of platform strings
  source TEXT NOT NULL DEFAULT 'airtable',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS generated_posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  campaign_id INTEGER NOT NULL,
  website_id INTEGER NOT NULL,
  platform TEXT NOT NULL,
  variation_index INTEGER NOT NULL,   -- 1..N per site/platform
  language TEXT NOT NULL,
  city TEXT NOT NULL,
  domain TEXT NOT NULL,
  service_name TEXT NOT NULL,
  title TEXT,                         -- optional
  body TEXT NOT NULL,
  hashtags TEXT,                      -- optional
  metadata_json TEXT,                 -- optional JSON (prompt vars, etc.)
  created_at TEXT NOT NULL,
  UNIQUE (campaign_id, website_id, platform, variation_index),
  FOREIGN KEY (campaign_id) REFERENCES content_campaigns(id) ON DELETE CASCADE,
  FOREIGN KEY (website_id) REFERENCES websites(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS post_jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  generated_post_id INTEGER NOT NULL,
  platform TEXT NOT NULL,
  status TEXT NOT NULL,               -- pending, processing, success, failed
  attempts INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL DEFAULT 3,
  last_error TEXT,
  locked_at TEXT,                     -- set when picked by worker
  completed_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (generated_post_id),
  FOREIGN KEY (generated_post_id) REFERENCES generated_posts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  level TEXT NOT NULL,                -- INFO, WARN, ERROR
  event_type TEXT NOT NULL,           -- seed, sync, generate, enqueue, publish
  message TEXT NOT NULL,
  context_json TEXT,                  -- optional JSON payload
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_websites_service_id ON websites(service_id);
CREATE INDEX IF NOT EXISTS idx_social_accounts_website_id ON social_accounts(website_id);
CREATE INDEX IF NOT EXISTS idx_generated_posts_campaign_id ON generated_posts(campaign_id);
CREATE INDEX IF NOT EXISTS idx_post_jobs_status ON post_jobs(status);
CREATE INDEX IF NOT EXISTS idx_logs_event_type_created_at ON logs(event_type, created_at);

