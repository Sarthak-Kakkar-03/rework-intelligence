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
  ai_assisted: boolean;
  ai_tool: string | null;
  work_type: string;
};

export type ReworkEvent = {
  id: string;
  source_pr_id: number;
  followup_pr_id: number | null;
  issue_key: string | null;
  detected_from: string;
  rework_type: string;
  severity: string;
  days_after_merge: number;
  human_hours_spent: number;
  root_cause_label: string;
  summary: string;
};

export type ContextRecommendation = {
  id: string;
  rework_event_id: string;
  recommended_artifact_id: string | null;
  missing_context_type: string;
  priority: string;
  recommendation: string;
  reason: string;
};

export type AutopsySummary = {
  team_count: number;
  repo_count: number;
  issue_count: number;
  pull_request_count: number;
  rework_event_count: number;
  context_artifact_count: number;
  context_recommendation_count: number;
  ai_assisted_pr_count: number;
  total_rework_hours: number;
  avg_days_after_merge: number;
};

export type ApiResponses = {
  "/api/autopsy/summary": AutopsySummary;
  "/api/pull-requests": PullRequest[];
  "/api/rework-events": ReworkEvent[];
  "/api/context-recommendations": ContextRecommendation[];
};
