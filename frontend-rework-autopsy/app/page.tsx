"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import type {
  AutopsySummary,
  ContextArtifact,
  PullRequest,
  ReworkEvent,
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

  const [addPrModalOpen, setAddPrModalOpen] = useState(false);
  const [newPrTitle, setNewPrTitle] = useState("");
  const [newPrBody, setNewPrBody] = useState("");
  const [newPrAuthorLogin, setNewPrAuthorLogin] = useState("");
  const [newPrMergedByLogin, setNewPrMergedByLogin] = useState("");
  const [newPrHeadBranch, setNewPrHeadBranch] = useState("");
  const [newPrAIGenerated, setNewPrAIGenerated] = useState(false);
  const [newPrNumber, setNewPrNumber] = useState("");
  const [newPrRepoId, setNewPrRepoId] = useState("");

  useEffect(() => {
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

        if (
          !summaryResponse.ok ||
          !eventsResponse.ok ||
          !artifactsResponse.ok
        ) {
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

    loadDashboardData();
  }, []);

  const rootCauseCounts =
    summary?.top_root_causes && summary.top_root_causes.length > 0
      ? summary.top_root_causes
      : getRootCauseCounts(reworkEvents);

  const fallbackHeadline = `Found ${summary?.rework_event_count ?? reworkEvents.length} rework events across ${summary?.pull_request_count ?? 0} pull requests, with ${summary?.context_artifact_count ?? contextArtifacts.length} context artifacts.`;

  function openAddPrModal() {
    setNewPrTitle("");
    setNewPrBody("");
    setNewPrAuthorLogin("");
    setNewPrMergedByLogin("");
    setNewPrHeadBranch("");
    setNewPrAIGenerated(false);
    setNewPrNumber("");
    setNewPrRepoId("");
    setAddPrModalOpen(true);
  }

  async function addPullRequest() {
    try {
      setError(null);

      const response = await fetch(`${API_BASE_URL}/api/ingest/pull-request`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: newPrTitle,
          body: newPrBody,
          author_login: newPrAuthorLogin,
          merged_by_login: newPrMergedByLogin,
          head_branch: newPrHeadBranch,
          ai_generated: newPrAIGenerated,
          number: Number(newPrNumber),
          repo_id: newPrRepoId,
        }),
      });

      if (!response.ok) {
        throw new Error("Create New PR request failed");
      }

      const createdPr = (await response.json()) as PullRequest;
      setSummary((currentSummary) => {
        if (!currentSummary) {
          return currentSummary;
        }

        return {
          ...currentSummary,
          pull_request_count: currentSummary.pull_request_count + 1,
          ai_generated_pr_count:
            currentSummary.ai_generated_pr_count +
            (createdPr.ai_generated ? 1 : 0),
        };
      });
      setAddPrModalOpen(false);
    } catch {
      setError("Unable to create Pull Request, make sure backend is working");
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
                Add PR
              </button>
              <button className="btn btn-ghost btn-primary btn-lg">
                Refresh
              </button>
            </section>

            <div className={`modal ${addPrModalOpen ? "modal-open" : ""}`}>
              <div className="modal-box max-w-2xl">
                <h2 className="text-lg font-semibold">Add Pull Request</h2>
                <p className="mt-1 text-sm text-base-content/70">
                  Create a closed pull request record for the prototype data.
                </p>

                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  <label className="form-control md:col-span-2">
                    <span className="label mb-1">
                      <span className="label-text">Title</span>
                    </span>
                    <input
                      className="input input-bordered"
                      onChange={(event) => setNewPrTitle(event.target.value)}
                      placeholder="Update webhook event pagination"
                      value={newPrTitle}
                    />
                  </label>

                  <label className="form-control md:col-span-2">
                    <span className="label mb-1">
                      <span className="label-text">Body</span>
                    </span>
                    <textarea
                      className="textarea textarea-bordered min-h-24"
                      onChange={(event) => setNewPrBody(event.target.value)}
                      placeholder="Describe the pull request."
                      value={newPrBody}
                    />
                  </label>

                  <label className="form-control">
                    <span className="label mb-1">
                      <span className="label-text">PR Number</span>
                    </span>
                    <input
                      className="input input-bordered"
                      min="1"
                      onChange={(event) => setNewPrNumber(event.target.value)}
                      placeholder="80"
                      type="number"
                      value={newPrNumber}
                    />
                  </label>

                  <label className="form-control">
                    <span className="label mb-1">
                      <span className="label-text">Repo ID</span>
                    </span>
                    <input
                      className="input input-bordered"
                      onChange={(event) => setNewPrRepoId(event.target.value)}
                      placeholder="test-repo-1"
                      value={newPrRepoId}
                    />
                  </label>

                  <label className="form-control">
                    <span className="label mb-1">
                      <span className="label-text">Author</span>
                    </span>
                    <input
                      className="input input-bordered"
                      onChange={(event) =>
                        setNewPrAuthorLogin(event.target.value)
                      }
                      placeholder="alex-rivera"
                      value={newPrAuthorLogin}
                    />
                  </label>

                  <label className="form-control">
                    <span className="label mb-1">
                      <span className="label-text">Merged By</span>
                    </span>
                    <input
                      className="input input-bordered"
                      onChange={(event) =>
                        setNewPrMergedByLogin(event.target.value)
                      }
                      placeholder="maya-chen"
                      value={newPrMergedByLogin}
                    />
                  </label>

                  <label className="form-control md:col-span-2">
                    <span className="label mb-1">
                      <span className="label-text">Head Branch</span>
                    </span>
                    <input
                      className="input input-bordered"
                      onChange={(event) =>
                        setNewPrHeadBranch(event.target.value)
                      }
                      placeholder="alex/webhook-pagination"
                      value={newPrHeadBranch}
                    />
                  </label>

                  <label className="flex cursor-pointer items-center gap-3 md:col-span-2">
                    <input
                      checked={newPrAIGenerated}
                      className="checkbox checkbox-primary"
                      onChange={(event) =>
                        setNewPrAIGenerated(event.target.checked)
                      }
                      type="checkbox"
                    />
                    <span className="text-sm">AI-generated</span>
                  </label>
                </div>

                <div className="modal-action">
                  <button
                    className="btn btn-ghost"
                    onClick={() => setAddPrModalOpen(false)}
                  >
                    Cancel
                  </button>
                  <button className="btn btn-primary" onClick={addPullRequest}>
                    Create PR
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
