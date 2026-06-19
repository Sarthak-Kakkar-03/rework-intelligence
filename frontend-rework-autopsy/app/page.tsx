"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import type {
  AutopsySummary,
  ContextArtifact,
  PullRequest,
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
    .map((filePath) => filePath.trim())
    .filter((filePath) => filePath.length > 0);
}

/**
 * Renders the main rework autopsy dashboard.
 *
 * Displays summary data, rework event statistics and table, root cause
 * breakdown, and context artifacts.
 */
export default function Home() {
  const [summary, setSummary] = useState<AutopsySummary | null>(null);
  const [reworkEvents, setReworkEvents] = useState<ReworkEvent[]>([]);
  const [contextArtifacts, setContextArtifacts] = useState<ContextArtifact[]>(
    [],
  );
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
  const [sourcePrNumber, setSourcePrNumber] = useState("");
  const [sourcePrRepoId, setSourcePrRepoId] = useState("");
  const [sourcePrAuthorLogin, setSourcePrAuthorLogin] = useState("");
  const [sourcePrMergedByLogin, setSourcePrMergedByLogin] = useState("");
  const [sourcePrHeadBranch, setSourcePrHeadBranch] = useState("");
  const [sourcePrAIGenerated, setSourcePrAIGenerated] = useState(true);
  const [sourcePrFiles, setSourcePrFiles] = useState("");
  const [followupPrTitle, setFollowupPrTitle] = useState("");
  const [followupPrBody, setFollowupPrBody] = useState("");
  const [followupPrNumber, setFollowupPrNumber] = useState("");
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
  }

  useEffect(() => {
    void Promise.resolve().then(() => loadDashboardData());
  }, []);

  const rootCauseCounts =
    summary?.top_root_causes && summary.top_root_causes.length > 0
      ? summary.top_root_causes
      : getRootCauseCounts(reworkEvents);

  const fallbackHeadline = `Found ${summary?.rework_event_count ?? reworkEvents.length} rework events across ${summary?.pull_request_count ?? 0} pull requests, with ${summary?.context_artifact_count ?? contextArtifacts.length} context artifacts.`;

  function openAddPrModal() {
    setSourcePrTitle("");
    setSourcePrBody("");
    setSourcePrNumber("");
    setSourcePrRepoId("");
    setSourcePrAuthorLogin("");
    setSourcePrMergedByLogin("");
    setSourcePrHeadBranch("");
    setSourcePrAIGenerated(true);
    setSourcePrFiles("");
    setFollowupPrTitle("");
    setFollowupPrBody("");
    setFollowupPrNumber("");
    setFollowupPrAuthorLogin("");
    setFollowupPrMergedByLogin("");
    setFollowupPrHeadBranch("");
    setFollowupPrAIGenerated(false);
    setFollowupPrFiles("");
    setAddPrError(null);
    setAddPrModalOpen(true);
  }

  async function createPullRequestWithFiles(
    pullRequest: {
      title: string;
      body: string;
      author_login: string;
      merged_by_login: string;
      head_branch: string;
      ai_generated: boolean;
      number: number;
      repo_id: string;
    },
    filePaths: string[],
  ): Promise<PullRequest> {
    const response = await fetch(`${API_BASE_URL}/api/ingest/pull-request`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(pullRequest),
    });

    if (!response.ok) {
      throw new Error("Create PR request failed");
    }

    const createdPr = (await response.json()) as PullRequest;

    if (filePaths.length > 0) {
      const filesResponse = await fetch(
        `${API_BASE_URL}/api/ingest/pull-request/${createdPr.id}/files`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            file_paths: filePaths,
          }),
        },
      );

      if (!filesResponse.ok) {
        throw new Error("Create PR files request failed");
      }
    }

    return createdPr;
  }

  async function addPullRequestPair() {
    if (isAddingPrPair) return;

    try {
      setAddPrError(null);
      setIsAddingPrPair(true);

      const sourceNumber = Number(sourcePrNumber);
      const followupNumber = Number(followupPrNumber);

      if (!Number.isInteger(sourceNumber) || sourceNumber <= 0) {
        setAddPrError("Source PR number must be a positive whole number.");
        return;
      }

      if (!Number.isInteger(followupNumber) || followupNumber <= 0) {
        setAddPrError("Follow-up PR number must be a positive whole number.");
        return;
      }

      if (!sourcePrRepoId.trim()) {
        setAddPrError("Repo ID is required.");
        return;
      }

      await createPullRequestWithFiles(
        {
          title: sourcePrTitle,
          body: sourcePrBody,
          author_login: sourcePrAuthorLogin,
          merged_by_login: sourcePrMergedByLogin,
          head_branch: sourcePrHeadBranch,
          ai_generated: sourcePrAIGenerated,
          number: sourceNumber,
          repo_id: sourcePrRepoId,
        },
        parseFilePaths(sourcePrFiles),
      );

      await createPullRequestWithFiles(
        {
          title: followupPrTitle,
          body: followupPrBody,
          author_login: followupPrAuthorLogin,
          merged_by_login: followupPrMergedByLogin,
          head_branch: followupPrHeadBranch,
          ai_generated: followupPrAIGenerated,
          number: followupNumber,
          repo_id: sourcePrRepoId,
        },
        parseFilePaths(followupPrFiles),
      );

      setAddPrModalOpen(false);
      await loadDashboardData();
    } catch {
      setAddPrError(
        "Unable to create PR pair. Check for duplicate PR numbers and make sure the backend is working.",
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
                  Create a source PR and a follow-up PR. Add at least one shared
                  file path, then run Compute Rework.
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

                    <div className="grid gap-4 md:grid-cols-2">
                      <label className="form-control">
                        <span className="label mb-1">
                          <span className="label-text">PR Number</span>
                        </span>
                        <input
                          className="input input-bordered"
                          min="1"
                          onChange={(event) =>
                            setSourcePrNumber(event.target.value)
                          }
                          placeholder="90"
                          type="number"
                          value={sourcePrNumber}
                        />
                      </label>

                      <label className="form-control">
                        <span className="label mb-1">
                          <span className="label-text">Repo ID</span>
                        </span>
                        <input
                          className="input input-bordered"
                          onChange={(event) =>
                            setSourcePrRepoId(event.target.value)
                          }
                          placeholder="repo-jira-sync-worker"
                          value={sourcePrRepoId}
                        />
                      </label>
                    </div>

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

                    <div className="grid gap-4 md:grid-cols-2">
                      <label className="form-control">
                        <span className="label mb-1">
                          <span className="label-text">PR Number</span>
                        </span>
                        <input
                          className="input input-bordered"
                          min="1"
                          onChange={(event) =>
                            setFollowupPrNumber(event.target.value)
                          }
                          placeholder="91"
                          type="number"
                          value={followupPrNumber}
                        />
                      </label>

                      <label className="form-control">
                        <span className="label mb-1">
                          <span className="label-text">Repo ID</span>
                        </span>
                        <input
                          className="input input-bordered"
                          disabled
                          value={sourcePrRepoId}
                        />
                      </label>
                    </div>

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
