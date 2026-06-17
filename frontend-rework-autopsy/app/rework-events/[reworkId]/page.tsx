"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { API_BASE_URL, apiGet } from "@/lib/api";
import type { ReworkEventDetail } from "@/types";

function formatLabel(label: string | undefined): string {
  if (!label) {
    return "Unknown";
  }

  return label
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
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

export default function ReworkEventDetailPage() {
  const params = useParams<{ reworkId: string }>();
  const reworkId = params.reworkId;

  const [detail, setDetail] = useState<ReworkEventDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadReworkEventDetail() {
      try {
        setLoading(true);
        setError(null);

        const path = `/api/rework-events/${encodeURIComponent(
          reworkId,
        )}` as `/api/rework-events/${string}`;
        const data = await apiGet(path);

        setDetail(data);
      } catch {
        setError(
          `Unable to load rework event ${reworkId}. Make sure the backend is running on ${API_BASE_URL}.`,
        );
      } finally {
        setLoading(false);
      }
    }

    loadReworkEventDetail();
  }, [reworkId]);

  return (
    <main className="min-h-screen bg-base-200 px-4 py-8 text-base-content">
      <div className="mx-auto flex max-w-5xl flex-col gap-6">
        <header className="flex flex-col gap-3">
          <Link className="link link-primary w-fit text-sm" href="/">
            Back to dashboard
          </Link>
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">
              Rework Event {reworkId}
            </h1>
            <p className="mt-2 max-w-3xl text-sm text-base-content/70">
              Review the source pull request, follow-up work, missing context,
              and recommended artifact for this rework case.
            </p>
          </div>
        </header>

        {loading && (
          <div className="alert">
            <span>Loading rework event...</span>
          </div>
        )}

        {error && (
          <div className="alert alert-error">
            <span>{error}</span>
          </div>
        )}

        {!loading && !error && detail && (
          <>
            <section className="card bg-base-100 shadow-sm">
              <div className="card-body gap-4">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="badge badge-outline">
                    {formatLabel(detail.rework_event.severity)}
                  </span>
                  <span className="badge badge-neutral">
                    {formatLabel(detail.rework_event.root_cause_label)}
                  </span>
                </div>
                <h2 className="text-xl font-semibold">
                  {detail.rework_event.summary}
                </h2>
                <div className="stats stats-vertical bg-base-200 lg:stats-horizontal">
                  <div className="stat">
                    <div className="stat-title">Days After Merge</div>
                    <div className="stat-value text-2xl">
                      {detail.rework_event.days_after_merge}
                    </div>
                  </div>
                  <div className="stat">
                    <div className="stat-title">Human Hours</div>
                    <div className="stat-value text-2xl">
                      {detail.rework_event.human_hours_spent}
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section className="grid gap-6 lg:grid-cols-2">
              <article className="card bg-base-100 shadow-sm">
                <div className="card-body">
                  <h2 className="card-title text-lg">Source PR</h2>
                  <p className="font-semibold">{detail.source_pr.title}</p>
                  <div className="text-sm text-base-content/70">
                    PR {detail.source_pr.number} in {detail.source_pr.repo_name}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {detail.source_pr.ai_assisted && (
                      <span className="badge badge-info">AI-assisted</span>
                    )}
                    {detail.source_pr.ai_tool && (
                      <span className="badge badge-outline">
                        {detail.source_pr.ai_tool}
                      </span>
                    )}
                  </div>
                </div>
              </article>

              <article className="card bg-base-100 shadow-sm">
                <div className="card-body">
                  <h2 className="card-title text-lg">Follow-up PR</h2>
                  {detail.followup_pr ? (
                    <>
                      <p className="font-semibold">
                        {detail.followup_pr.title}
                      </p>
                      <div className="text-sm text-base-content/70">
                        PR {detail.followup_pr.number} in{" "}
                        {detail.followup_pr.repo_name}
                      </div>
                    </>
                  ) : (
                    <p className="text-sm text-base-content/70">
                      No follow-up PR is linked to this rework event.
                    </p>
                  )}
                </div>
              </article>
            </section>

            <section className="grid gap-6 lg:grid-cols-2">
              <article className="card bg-base-100 shadow-sm">
                <div className="card-body">
                  <div className="flex items-center justify-between gap-3">
                    <h2 className="card-title text-lg">Recommendation</h2>
                    {detail.recommendation && (
                      <span
                        className={`badge ${getPriorityBadgeClass(
                          detail.recommendation.priority,
                        )}`}
                      >
                        {formatLabel(detail.recommendation.priority)}
                      </span>
                    )}
                  </div>
                  {detail.recommendation ? (
                    <>
                      <p className="font-semibold">
                        {detail.recommendation.recommendation}
                      </p>
                      <p className="text-sm text-base-content/70">
                        {detail.recommendation.reason}
                      </p>
                      <p className="text-sm">
                        Missing context:{" "}
                        {formatLabel(
                          detail.recommendation.missing_context_type,
                        )}
                      </p>
                    </>
                  ) : (
                    <p className="text-sm text-base-content/70">
                      No recommendation is linked to this rework event.
                    </p>
                  )}
                </div>
              </article>

              <article className="card bg-base-100 shadow-sm">
                <div className="card-body">
                  <h2 className="card-title text-lg">Context Artifact</h2>
                  {detail.context_artifact ? (
                    <>
                      <p className="font-semibold">
                        {detail.context_artifact.name}
                      </p>
                      <div className="flex flex-wrap gap-2">
                        <span className="badge badge-outline">
                          {formatLabel(detail.context_artifact.artifact_type)}
                        </span>
                        <span className="badge badge-neutral">
                          {formatLabel(detail.context_artifact.freshness)}
                        </span>
                      </div>
                    </>
                  ) : (
                    <p className="text-sm text-base-content/70">
                      No context artifact is linked to this recommendation.
                    </p>
                  )}
                </div>
              </article>
            </section>
          </>
        )}
      </div>
    </main>
  );
}
