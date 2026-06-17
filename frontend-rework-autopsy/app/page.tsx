"use client";

import { useEffect, useState } from "react";

import { API_BASE_URL, apiGet } from "@/lib/api";
import type {
  AutopsySummary,
  ContextRecommendation,
  ReworkEvent,
} from "@/types";

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

function getPriorityBadgeClass(priority: string): string {
  if (priority === "high") {
    return "badge-error";
  }

  if (priority === "medium") {
    return "badge-warning";
  }

  if (priority === "low") {
    return "badge-info";
  }

  return "badge-neutral";
}

export default function Home() {
  const [summary, setSummary] = useState<AutopsySummary | null>(null);
  const [reworkEvents, setReworkEvents] = useState<ReworkEvent[]>([]);
  const [recommendations, setRecommendations] = useState<
    ContextRecommendation[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDashboardData() {
      try {
        setLoading(true);
        setError(null);

        const [summaryData, eventsData, recommendationsData] =
          await Promise.all([
            apiGet("/api/autopsy/summary"),
            apiGet("/api/rework-events"),
            apiGet("/api/context-recommendations"),
          ]);

        setSummary(summaryData);
        setReworkEvents(eventsData);
        setRecommendations(recommendationsData);
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

  const fallbackHeadline = `Found ${summary?.rework_event_count ?? reworkEvents.length} rework events across ${summary?.pull_request_count ?? 0} pull requests, with ${summary?.context_recommendation_count ?? recommendations.length} context recommendations.`;

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
                <div className="stat-title">AI-assisted PRs</div>
                <div className="stat-value text-2xl">
                  {summary?.ai_assisted_pr_count ?? 0}
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
                <div className="stat-title">Context Recommendations</div>
                <div className="stat-value text-2xl">
                  {summary?.context_recommendation_count ??
                    recommendations.length}
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
                            <td className="font-medium">{event.id}</td>
                            <td>
                              {event.source_pr_title ||
                                `PR ${event.source_pr_id}`}
                            </td>
                            <td>
                              {event.followup_pr_title ||
                                (event.followup_pr_id
                                  ? `PR ${event.followup_pr_id}`
                                  : "None")}
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
                Context Recommendations
              </h2>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {recommendations.map((item) => (
                  <article className="card bg-base-100 shadow-sm" key={item.id}>
                    <div className="card-body gap-3">
                      <div className="flex items-center justify-between gap-3">
                        <span
                          className={`badge ${getPriorityBadgeClass(item.priority)}`}
                        >
                          {formatLabel(item.priority)}
                        </span>
                        <span className="text-xs text-base-content/60">
                          {formatLabel(item.missing_context_type)}
                        </span>
                      </div>
                      <h3 className="font-semibold">{item.recommendation}</h3>
                      <p className="text-sm text-base-content/70">
                        {item.reason}
                      </p>
                      {item.recommended_artifact_name && (
                        <p className="text-sm">
                          Artifact: {item.recommended_artifact_name}
                        </p>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </main>
  );
}
