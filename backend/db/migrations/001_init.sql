PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS teams (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS repos (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  team_id TEXT NOT NULL,

  FOREIGN KEY (team_id) REFERENCES teams(id)
);

CREATE TABLE IF NOT EXISTS issues (
  issue_key TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  team_id TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  resolved_at TEXT,
  reopened_at TEXT,
  reopened_count INTEGER NOT NULL DEFAULT 0,

  FOREIGN KEY (team_id) REFERENCES teams(id)
);

CREATE TABLE IF NOT EXISTS pull_requests (
  id INTEGER PRIMARY KEY,
  number INTEGER NOT NULL,
  repo_id TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT,
  state TEXT NOT NULL,
  draft INTEGER NOT NULL DEFAULT 0,

  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  closed_at TEXT,
  merged_at TEXT,
  merged INTEGER NOT NULL DEFAULT 0,

  author_login TEXT NOT NULL,
  merged_by_login TEXT,

  base_branch TEXT NOT NULL,
  head_branch TEXT NOT NULL,

  additions INTEGER NOT NULL DEFAULT 0,
  deletions INTEGER NOT NULL DEFAULT 0,
  changed_files INTEGER NOT NULL DEFAULT 0,
  commits INTEGER NOT NULL DEFAULT 0,
  comments INTEGER NOT NULL DEFAULT 0,
  review_comments INTEGER NOT NULL DEFAULT 0,

  linked_issue_key TEXT,
  ai_assisted INTEGER NOT NULL DEFAULT 0,
  ai_tool TEXT,
  work_type TEXT NOT NULL,

  UNIQUE (repo_id, number),
  FOREIGN KEY (repo_id) REFERENCES repos(id),
  FOREIGN KEY (linked_issue_key) REFERENCES issues(issue_key)
);

CREATE TABLE IF NOT EXISTS rework_events (
  id TEXT PRIMARY KEY,

  source_pr_id INTEGER NOT NULL,
  followup_pr_id INTEGER,
  issue_key TEXT,

  detected_from TEXT NOT NULL,
  rework_type TEXT NOT NULL,
  severity TEXT NOT NULL,

  days_after_merge INTEGER NOT NULL,
  human_hours_spent REAL NOT NULL,

  root_cause_label TEXT NOT NULL,
  summary TEXT NOT NULL,

  FOREIGN KEY (source_pr_id) REFERENCES pull_requests(id),
  FOREIGN KEY (followup_pr_id) REFERENCES pull_requests(id),
  FOREIGN KEY (issue_key) REFERENCES issues(issue_key)
);

CREATE TABLE IF NOT EXISTS context_artifacts (
  id TEXT PRIMARY KEY,

  name TEXT NOT NULL,
  rework_event_id TEXT NOT NULL,
  artifact_type TEXT NOT NULL,

  repo_id TEXT NOT NULL,
  team_id TEXT NOT NULL,

  last_updated_at TEXT,
  summary TEXT NOT NULL,

  FOREIGN KEY (rework_event_id) REFERENCES rework_events(id),
  FOREIGN KEY (repo_id) REFERENCES repos(id),
  FOREIGN KEY (team_id) REFERENCES teams(id)
);
