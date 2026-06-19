export type IsoDateTime = string;

export type PullRequest = {
  id: number;
  number: number;
  repo_id: string;
  title: string;
  body: string | null;
  state: string;
  draft: boolean;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
  closed_at: IsoDateTime | null;
  merged_at: IsoDateTime | null;
  merged: boolean;
  author_login: string;
  merged_by_login: string | null;
  base_branch: string;
  head_branch: string;
  additions: number;
  deletions: number;
  changed_files: number;
  commits: number;
  comments: number;
  review_comments: number;
  linked_issue_key: string | null;
  ai_generated: boolean;
};

export type ReworkEvent = {
  id: string;
  source_pr_id: number;
  source_pr_title?: string;
  followup_pr_id: number;
  followup_pr_title?: string;
  issue_key: string | null;
  detected_from: string;
  rework_type: string;
  severity: string;
  days_after_merge: number;
  human_hours_spent: number;
  root_cause_label: string;
  summary: string;
};

export type ContextArtifact = {
  id: string;
  rework_event_id: string;
  name: string;
  artifact_type: string;
  repo_id: string;
  team_id: string;
  last_updated_at: IsoDateTime | null;
  summary: string;
};

export type AutopsySummary = {
  headline?: string;
  team_count: number;
  repo_count: number;
  issue_count: number;
  pull_request_count: number;
  rework_event_count: number;
  context_artifact_count: number;
  ai_generated_pr_count: number;
  total_rework_hours: number;
  avg_days_after_merge: number;
  top_root_causes?: {
    root_cause_label: string;
    count: number;
  }[];
};

export type ReworkEventDetailEvent = {
  id: string;
  severity: string;
  root_cause_label: string;
  days_after_merge: number;
  human_hours_spent: number;
  summary: string;
};

export type ReworkEventDetailPullRequest = {
  id: number;
  number: number;
  title: string;
  repo_name: string;
  ai_generated: boolean | null;
};

export type ReworkEventDetailContextArtifact = {
  id: string;
  name: string;
  artifact_type: string;
  summary: string;
};

export type ReworkEventDetail = {
  rework_event: ReworkEventDetailEvent;
  source_pr: ReworkEventDetailPullRequest;
  followup_pr: ReworkEventDetailPullRequest;
  context_artifacts: ReworkEventDetailContextArtifact[];
};
