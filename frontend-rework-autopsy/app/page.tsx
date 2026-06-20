"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import type {
  AutopsySummary,
  ContextArtifact,
  PullRequest,
  Repo,
  ReworkEvent,
  ReworkRecomputeResult,
} from "@/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

function formatLabel(label: string | undefined): string {
  if (!label) {
    return "Unknown";
  }

  return label
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function getRootCauseCounts(reworkEvents: ReworkEvent[]) {
  const counts: Record<string, number> = {};

  for (const event of reworkEvents) {
    const label = event.root_cause_label || "unknown";
    counts[label] = (counts[label] || 0) + 1;
  }

  return Object.entries(counts).map(([root_cause_label, count]) => ({
    root_cause_label,
    count,
  }));
}

function parseFilePaths(filePathText: string): string[] {
  return filePathText
    .split(/\n|,/)
    .map((filePath) => {
      let normalizedPath = filePath.trim().replaceAll("\\", "/");
      while (normalizedPath.startsWith("./")) {
        normalizedPath = normalizedPath.slice(2);
      }
      while (normalizedPath.includes("//")) {
        normalizedPath = normalizedPath.replaceAll("//", "/");
      }
      return normalizedPath;
    })
    .filter((filePath) => filePath.length > 0);
}

/**
 * Main dashboard for rework analysis and context artifact generation.
 *
 * Displays summary statistics, rework events, root cause breakdown, and
 * context artifacts. Provides controls to add pull request pairs for analysis
 * and to recompute rework event metrics.
 */
export default function Home() {
  const [summary, setSummary] = useState<AutopsySummary | null>(null);
  const [reworkEvents, setReworkEvents] = useState<ReworkEvent[]>([]);
  const [contextArtifacts, setContextArtifacts] = useState<ContextArtifact[]>(
    [],
  );
  const [repos, setRepos] = useState<Repo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isComputingRework, setIsComputingRework] = useState(false);
  const [computeReworkMessage, setComputeReworkMessage] = useState<
    string | null
  >(null);
  const [computeReworkError, setComputeReworkError] = useState<string | null>(
    null,
  );

  const [addPrModalOpen, setAddPrModalOpen] = useState(false);
  const [addPrError, setAddPrError] = useState<string | null>(null);
  const [isAddingPrPair, setIsAddingPrPair] = useState(false);
  const [sourcePrTitle, setSourcePrTitle] = useState("");
  const [sourcePrBody, setSourcePrBody] = useState("");
  const [sourcePrRepoId, setSourcePrRepoId] = useState("");
  const [sourcePrAuthorLogin, setSourcePrAuthorLogin] = useState("");
  const [sourcePrMergedByLogin, setSourcePrMergedByLogin] = useState("");
  const [sourcePrHeadBranch, setSourcePrHeadBranch] = useState("");
  const [sourcePrAIGenerated, setSourcePrAIGenerated] = useState(true);
  const [sourcePrFiles, setSourcePrFiles] = useState("");
  const [followupPrTitle, setFollowupPrTitle] = useState("");
  const [followupPrBody, setFollowupPrBody] = useState("");
  const [followupPrRepoId, setFollowupPrRepoId] = useState("");
  const [followupPrAuthorLogin, setFollowupPrAuthorLogin] = useState("");
  const [followupPrMergedByLogin, setFollowupPrMergedByLogin] = useState("");
  const [followupPrHeadBranch, setFollowupPrHeadBranch] = useState("");
  const [followupPrAIGenerated, setFollowupPrAIGenerated] = useState(false);
  const [followupPrFiles, setFollowupPrFiles] = useState("");

  async function loadDashboardData() {
    try {
      setLoading(true);
      setError(null);

      const [summaryResponse, eventsResponse, artifactsResponse] =
        await Promise.all([
          fetch(`${API_BASE_URL}/api/autopsy/summary`),
          fetch(`${API_BASE_URL}/api/rework-events`),
          fetch(`${API_BASE_URL}/api/context-artifacts`),
        ]);

      if (!summaryResponse.ok || !eventsResponse.ok || !artifactsResponse.ok) {
        throw new Error("One or more dashboard requests failed.");
      }

      const [summaryData, eventsData, artifactsData] = await Promise.all([
        summaryResponse.json() as Promise<AutopsySummary>,
        eventsResponse.json() as Promise<ReworkEvent[]>,
        artifactsResponse.json() as Promise<ContextArtifact[]>,
      ]);

      setSummary(summaryData);
      setReworkEvents(eventsData);
      setContextArtifacts(artifactsData);
    } catch {
      setError(
        `Unable to load dashboard data. Make sure the backend is running on ${API_BASE_URL}.`,
      );
    } finally {
      setLoading(false);
    }

    try {
      const reposResponse = await fetch(`${API_BASE_URL}/api/repos`);

      if (!reposResponse.ok) {
        throw new Error("Repos request failed.");
      }

      const reposData = (await reposResponse.json()) as Repo[];
      setRepos(reposData);
    } catch (reposError) {
      console.error("Unable to load repos for Add PR Pair modal.", reposError);
    }
  }

  useEffect(() => {
    void Promise.resolve().then(() => loadDashboardData());
  }, []);

  const rootCauseCounts =
    summary?.top_root_causes && summary.top_root_causes.length > 0
      ? summary.top_root_causes
      : getRootCauseCounts(reworkEvents);

  const fallbackHeadline = `Found ${summary?.rework_event_count ?? reworkEvents.length} rework events across ${summary?.pull_request_count ?? 0} pull requests, with ${summary?.context_artifact_count ?? contextArtifacts.length} context artifacts.`;

  /**
   * Opens the add PR pair modal, pre-filled with example values.
   */
  function openAddPrModal() {
    setSourcePrTitle("Add retry handling for billing sync");
    setSourcePrBody(
      "Adds AI-generated retry behavior for transient billing sync failures.",
    );
    setSourcePrRepoId("repo-jira-sync-worker");
    setSourcePrAuthorLogin("maya-chen");
    setSourcePrMergedByLogin("alex-rivera");
    setSourcePrHeadBranch("maya/billing-sync-retry");
    setSourcePrAIGenerated(true);
    setSourcePrFiles(
      "src/billing_sync/retry_worker.py\ntests/test_billing_retry.py",
    );
    setFollowupPrTitle("Fix duplicate billing sync retries");
    setFollowupPrBody(
      "Fixes duplicate writes from retry replay after the AI-generated retry change.",
    );
    setFollowupPrRepoId("repo-jira-sync-worker");
    setFollowupPrAuthorLogin("alex-rivera");
    setFollowupPrMergedByLogin("maya-chen");
    setFollowupPrHeadBranch("alex/fix-billing-retry");
    setFollowupPrAIGenerated(false);
    setFollowupPrFiles(
      "src/billing_sync/retry_worker.py\ntests/test_billing_retry.py",
    );
    setAddPrError(null);
    setAddPrModalOpen(true);
  }

  /**
   * Creates a pull request with the specified files.
   *
   * @returns The created pull request.
   */
  async function createPullRequestWithFiles(
    pullRequest: {
      title: string;
      body: string;
      author_login: string;
      merged_by_login: string;
      head_branch: string;
      ai_generated: boolean;
      repo_id: string;
      closed_at: string;
    },
    filePaths: string[],
  ): Promise<PullRequest> {
    const response = await fetch(
      `${API_BASE_URL}/api/ingest/pull-request-with-files`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          pull_request: pullRequest,
          file_paths: filePaths,
        }),
      },
    );

    if (!response.ok) {
      throw new Error("Create PR with files request failed");
    }

    return (await response.json()) as PullRequest;
  }

  /**
   * Creates a source pull request and a follow-up pull request from the provided form data.
   *
   * Validates that both source and follow-up PRs have a repo selected and at least one file path.
   * Computes closure timestamps (source: current time, follow-up: one day later) and submits both
   * pull requests to the backend. On success, closes the modal and refreshes the dashboard.
   * On failure, displays an error message.
   */
  async function addPullRequestPair() {
    if (isAddingPrPair) return;

    try {
      setAddPrError(null);
      setIsAddingPrPair(true);

      if (!sourcePrRepoId.trim() || !followupPrRepoId.trim()) {
        setAddPrError("Both PRs need a repo.");
        return;
      }

      const sourceFilePaths = parseFilePaths(sourcePrFiles);
      const followupFilePaths = parseFilePaths(followupPrFiles);

      if (sourceFilePaths.length === 0 || followupFilePaths.length === 0) {
        setAddPrError("Add at least one file path for each PR.");
        return;
      }

      const sourceClosedAt = new Date();
      const followupClosedAt = new Date(sourceClosedAt);
      followupClosedAt.setDate(sourceClosedAt.getDate() + 1);

      await createPullRequestWithFiles(
        {
          title: sourcePrTitle,
          body: sourcePrBody,
          author_login: sourcePrAuthorLogin,
          merged_by_login: sourcePrMergedByLogin,
          head_branch: sourcePrHeadBranch,
          ai_generated: sourcePrAIGenerated,
          repo_id: sourcePrRepoId,
          closed_at: sourceClosedAt.toISOString(),
        },
        sourceFilePaths,
      );

      await createPullRequestWithFiles(
        {
          title: followupPrTitle,
          body: followupPrBody,
          author_login: followupPrAuthorLogin,
          merged_by_login: followupPrMergedByLogin,
          head_branch: followupPrHeadBranch,
          ai_generated: followupPrAIGenerated,
          repo_id: followupPrRepoId,
          closed_at: followupClosedAt.toISOString(),
        },
        followupFilePaths,
      );

      setAddPrModalOpen(false);
      await loadDashboardData();
    } catch {
      setAddPrError(
        "Unable to create PR pair. Check the selected repos and make sure the backend is working.",
      );
    } finally {
      setIsAddingPrPair(false);
    }
  }

  async function computeRework() {
    try {
      setIsComputingRework(true);
      setComputeReworkMessage(null);
      setComputeReworkError(null);

      const response = await fetch(
        `${API_BASE_URL}/api/ingest/rework-events/recompute`,
        {
          method: "POST",
        },
      );

      if (!response.ok) {
        throw new Error("Rework recompute request failed.");
      }

      const result = (await response.json()) as ReworkRecomputeResult;
      setComputeReworkMessage(result.message);
      await loadDashboardData();
    } catch {
      setComputeReworkError(
        `Unable to compute rework events. Make sure the backend is running on ${API_BASE_URL}.`,
      );
    } finally {
      setIsComputingRework(false);
    }
  }

  return (
    <main className="min-h-screen bg-base-200 px-4 py-8 text-base-content">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header>
          <h1 className="text-3xl font-semibold tracking-tight">
            Rework Autopsy
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-base-content/70">
            Identify where AI-assisted engineering work creates follow-up
            rework, then recommend what context to add for future agents.
          </p>
        </header>

        {loading && (
          <div className="alert">
            <span>Loading dashboard data...</span>
          </div>
        )}

        {error && (
          <div className="alert alert-error">
            <span>{error}</span>
          </div>
        )}

        {computeReworkMessage && (
          <div className="alert alert-success">
            <span>{computeReworkMessage}</span>
          </div>
        )}

        {computeReworkError && (
          <div className="alert alert-error">
            <span>{computeReworkError}</span>
          </div>
        )}

        {!loading && !error && (
          <>
            <section className="card bg-base-100 shadow-sm">
              <div className="card-body">
                <p className="text-sm font-medium uppercase text-base-content/60">
                  Current Finding
                </p>
                <h2 className="text-xl font-semibold">
                  {summary?.headline || fallbackHeadline}
                </h2>
              </div>
            </section>

            <section className="stats stats-vertical bg-base-100 shadow-sm lg:stats-horizontal">
              <div className="stat">
                <div className="stat-title">Total PRs</div>
                <div className="stat-value text-2xl">
                  {summary?.pull_request_count ?? 0}
                </div>
              </div>

              <div className="stat">
                <div className="stat-title">AI-generated PRs</div>
                <div className="stat-value text-2xl">
                  {summary?.ai_generated_pr_count ?? 0}
                </div>
              </div>

              <div className="stat">
                <div className="stat-title">Rework Events</div>
                <div className="stat-value text-2xl">
                  {summary?.rework_event_count ?? reworkEvents.length}
                </div>
              </div>

              <div className="stat">
                <div className="stat-title">Estimated Human Hours Lost</div>
                <div className="stat-value text-2xl">
                  {summary?.total_rework_hours ?? 0}
                </div>
              </div>

              <div className="stat">
                <div className="stat-title">Context Artifacts</div>
                <div className="stat-value text-2xl">
                  {summary?.context_artifact_count ?? contextArtifacts.length}
                </div>
              </div>
            </section>

            <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
              <div className="card bg-base-100 shadow-sm">
                <div className="card-body">
                  <h2 className="card-title text-lg">Rework Events</h2>
                  <div className="overflow-x-auto">
                    <table className="table table-zebra">
                      <thead>
                        <tr>
                          <th>Rework ID</th>
                          <th>Source PR</th>
                          <th>Follow-up PR</th>
                          <th>Root Cause</th>
                          <th>Severity</th>
                          <th>Days After Merge</th>
                          <th>Human Hours</th>
                        </tr>
                      </thead>
                      <tbody>
                        {reworkEvents.map((event) => (
                          <tr key={event.id}>
                            <td className="font-medium">
                              <Link
                                className="link link-primary"
                                href={`/rework-events/${encodeURIComponent(event.id)}`}
                              >
                                {event.id}
                              </Link>
                            </td>
                            <td>
                              {event.source_pr_title ||
                                `PR ${event.source_pr_id}`}
                            </td>
                            <td>
                              {event.followup_pr_title ||
                                `PR ${event.followup_pr_id}`}
                            </td>
                            <td>{formatLabel(event.root_cause_label)}</td>
                            <td>
                              <span className="badge badge-outline">
                                {formatLabel(event.severity)}
                              </span>
                            </td>
                            <td>{event.days_after_merge}</td>
                            <td>{event.human_hours_spent}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              <aside className="card bg-base-100 shadow-sm">
                <div className="card-body">
                  <h2 className="card-title text-lg">Root Cause Breakdown</h2>
                  <div className="flex flex-col gap-3">
                    {rootCauseCounts.map((item) => (
                      <div
                        className="flex items-center justify-between border-b border-base-200 pb-2"
                        key={item.root_cause_label}
                      >
                        <span>{formatLabel(item.root_cause_label)}</span>
                        <span className="badge badge-neutral">
                          {item.count}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </aside>
            </section>

            <section>
              <h2 className="mb-3 text-lg font-semibold">
                Latest Context Artifacts
              </h2>
              {contextArtifacts.length > 0 ? (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {contextArtifacts.slice(0, 3).map((item) => (
                    <article
                      className="card bg-base-100 shadow-sm"
                      key={item.id}
                    >
                      <div className="card-body gap-3">
                        <div className="flex items-center justify-between gap-3">
                          <span className="badge badge-outline">
                            {formatLabel(item.artifact_type)}
                          </span>
                          <span className="text-xs text-base-content/60">
                            {item.rework_event_id}
                          </span>
                        </div>
                        <h3 className="font-semibold">{item.name}</h3>
                        <p className="text-sm text-base-content/70">
                          {item.summary}
                        </p>
                        <p className="text-sm">Repo: {item.repo_id}</p>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-base-content/70">
                  No context artifacts are available.
                </p>
              )}
            </section>
            <section className="flex flex-1 justify-evenly">
              <button
                className="btn btn-ghost btn-primary btn-lg"
                onClick={openAddPrModal}
              >
                Add PR Pair
              </button>
              <button
                className="btn btn-ghost btn-primary btn-lg"
                disabled={isComputingRework}
                onClick={computeRework}
              >
                {isComputingRework ? "Computing..." : "Compute Rework"}
              </button>
            </section>

            <div className={`modal ${addPrModalOpen ? "modal-open" : ""}`}>
              <div className="modal-box max-w-5xl">
                <h2 className="text-lg font-semibold">Add PR Pair</h2>
                <p className="mt-1 text-sm text-base-content/70">
                  Create a source PR and a follow-up PR. Add at least one file
                  path for each PR, then run Compute Rework.
                </p>

                {addPrError && (
                  <div className="alert alert-error mt-4">
                    <span>{addPrError}</span>
                  </div>
                )}

                <div className="mt-5 grid gap-6 lg:grid-cols-2">
                  <section className="flex flex-col gap-4">
                    <h3 className="font-semibold">Source PR</h3>
                    <label className="form-control">
                      <span className="label mb-1">
                        <span className="label-text">Title</span>
                      </span>
                      <input
                        className="input input-bordered"
                        onChange={(event) =>
                          setSourcePrTitle(event.target.value)
                        }
                        placeholder="Add retry handling for billing sync"
                        value={sourcePrTitle}
                      />
                    </label>

                    <label className="form-control">
                      <span className="label mb-1">
                        <span className="label-text">Body</span>
                      </span>
                      <textarea
                        className="textarea textarea-bordered min-h-24"
                        onChange={(event) =>
                          setSourcePrBody(event.target.value)
                        }
                        placeholder="Adds AI-generated retry behavior for transient billing sync failures."
                        value={sourcePrBody}
                      />
                    </label>

                    <label className="form-control">
                      <span className="label mb-1">
                        <span className="label-text">Repo</span>
                      </span>
                      <select
                        className="select select-bordered"
                        onChange={(event) =>
                          setSourcePrRepoId(event.target.value)
                        }
                        value={sourcePrRepoId}
                      >
                        <option disabled value="">
                          Choose repo
                        </option>
                        {repos.map((repo) => (
                          <option key={repo.id} value={repo.id}>
                            {repo.name}
                          </option>
                        ))}
                      </select>
                    </label>

                    <div className="grid gap-4 md:grid-cols-2">
                      <label className="form-control">
                        <span className="label mb-1">
                          <span className="label-text">Author</span>
                        </span>
                        <input
                          className="input input-bordered"
                          onChange={(event) =>
                            setSourcePrAuthorLogin(event.target.value)
                          }
                          placeholder="maya-chen"
                          value={sourcePrAuthorLogin}
                        />
                      </label>

                      <label className="form-control">
                        <span className="label mb-1">
                          <span className="label-text">Merged By</span>
                        </span>
                        <input
                          className="input input-bordered"
                          onChange={(event) =>
                            setSourcePrMergedByLogin(event.target.value)
                          }
                          placeholder="alex-rivera"
                          value={sourcePrMergedByLogin}
                        />
                      </label>
                    </div>

                    <label className="form-control">
                      <span className="label mb-1">
                        <span className="label-text">Head Branch</span>
                      </span>
                      <input
                        className="input input-bordered"
                        onChange={(event) =>
                          setSourcePrHeadBranch(event.target.value)
                        }
                        placeholder="maya/billing-sync-retry"
                        value={sourcePrHeadBranch}
                      />
                    </label>

                    <label className="form-control">
                      <span className="label mb-1">
                        <span className="label-text">File Paths</span>
                      </span>
                      <textarea
                        className="textarea textarea-bordered min-h-24"
                        onChange={(event) =>
                          setSourcePrFiles(event.target.value)
                        }
                        placeholder={
                          "src/billing_sync/retry_worker.py\ntests/test_billing_retry.py"
                        }
                        value={sourcePrFiles}
                      />
                    </label>

                    <label className="flex cursor-pointer items-center gap-3">
                      <input
                        checked={sourcePrAIGenerated}
                        className="checkbox checkbox-primary"
                        onChange={(event) =>
                          setSourcePrAIGenerated(event.target.checked)
                        }
                        type="checkbox"
                      />
                      <span className="text-sm">AI-generated</span>
                    </label>
                  </section>

                  <section className="flex flex-col gap-4">
                    <h3 className="font-semibold">Follow-up PR</h3>
                    <label className="form-control">
                      <span className="label mb-1">
                        <span className="label-text">Title</span>
                      </span>
                      <input
                        className="input input-bordered"
                        onChange={(event) =>
                          setFollowupPrTitle(event.target.value)
                        }
                        placeholder="Fix duplicate billing sync retries"
                        value={followupPrTitle}
                      />
                    </label>

                    <label className="form-control">
                      <span className="label mb-1">
                        <span className="label-text">Body</span>
                      </span>
                      <textarea
                        className="textarea textarea-bordered min-h-24"
                        onChange={(event) =>
                          setFollowupPrBody(event.target.value)
                        }
                        placeholder="Fixes duplicate writes from retry replay after the AI-generated retry change."
                        value={followupPrBody}
                      />
                    </label>

                    <label className="form-control">
                      <span className="label mb-1">
                        <span className="label-text">Repo</span>
                      </span>
                      <select
                        className="select select-bordered"
                        onChange={(event) =>
                          setFollowupPrRepoId(event.target.value)
                        }
                        value={followupPrRepoId}
                      >
                        <option disabled value="">
                          Choose repo
                        </option>
                        {repos.map((repo) => (
                          <option key={repo.id} value={repo.id}>
                            {repo.name}
                          </option>
                        ))}
                      </select>
                    </label>

                    <div className="grid gap-4 md:grid-cols-2">
                      <label className="form-control">
                        <span className="label mb-1">
                          <span className="label-text">Author</span>
                        </span>
                        <input
                          className="input input-bordered"
                          onChange={(event) =>
                            setFollowupPrAuthorLogin(event.target.value)
                          }
                          placeholder="alex-rivera"
                          value={followupPrAuthorLogin}
                        />
                      </label>

                      <label className="form-control">
                        <span className="label mb-1">
                          <span className="label-text">Merged By</span>
                        </span>
                        <input
                          className="input input-bordered"
                          onChange={(event) =>
                            setFollowupPrMergedByLogin(event.target.value)
                          }
                          placeholder="maya-chen"
                          value={followupPrMergedByLogin}
                        />
                      </label>
                    </div>

                    <label className="form-control">
                      <span className="label mb-1">
                        <span className="label-text">Head Branch</span>
                      </span>
                      <input
                        className="input input-bordered"
                        onChange={(event) =>
                          setFollowupPrHeadBranch(event.target.value)
                        }
                        placeholder="alex/fix-billing-retry"
                        value={followupPrHeadBranch}
                      />
                    </label>

                    <label className="form-control">
                      <span className="label mb-1">
                        <span className="label-text">File Paths</span>
                      </span>
                      <textarea
                        className="textarea textarea-bordered min-h-24"
                        onChange={(event) =>
                          setFollowupPrFiles(event.target.value)
                        }
                        placeholder={
                          "src/billing_sync/retry_worker.py\ntests/test_billing_retry.py"
                        }
                        value={followupPrFiles}
                      />
                    </label>

                    <label className="flex cursor-pointer items-center gap-3">
                      <input
                        checked={followupPrAIGenerated}
                        className="checkbox checkbox-primary"
                        onChange={(event) =>
                          setFollowupPrAIGenerated(event.target.checked)
                        }
                        type="checkbox"
                      />
                      <span className="text-sm">AI-generated</span>
                    </label>
                  </section>
                </div>

                <div className="modal-action">
                  <button
                    className="btn btn-ghost"
                    onClick={() => setAddPrModalOpen(false)}
                  >
                    Cancel
                  </button>
                  <button
                    className="btn btn-primary"
                    disabled={isAddingPrPair}
                    onClick={addPullRequestPair}
                  >
                    {isAddingPrPair ? "Creating..." : "Create PR Pair"}
                  </button>
                </div>
              </div>
              <button
                aria-label="Close add pull request modal"
                className="modal-backdrop"
                onClick={() => setAddPrModalOpen(false)}
              />
            </div>
          </>
        )}
      </div>
    </main>
  );
}
