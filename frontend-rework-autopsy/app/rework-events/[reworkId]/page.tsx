"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import type {
  ContextArtifact,
  ReworkDisposition,
  ReworkEventDetail,
} from "@/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

/**
 * Converts an underscore-delimited label into a space-separated, title-cased string.
 *
 * @returns The label formatted as space-separated, title-cased words, or `"Unknown"` if the input is falsy.
 */
function formatLabel(label: string | undefined): string {
  if (!label) {
    return "Unknown";
  }

  return label
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

const DISPOSITION_OPTIONS: { value: ReworkDisposition; label: string }[] = [
  { value: "unreviewed", label: "Unreviewed" },
  { value: "confirmed_rework", label: "Confirmed Rework" },
  { value: "partial_rework", label: "Partial Rework" },
  { value: "related_expected", label: "Related but Expected Follow-Up" },
  { value: "unrelated", label: "Unrelated / False Positive" },
];

const DISPOSITION_BADGE_CLASS: Record<ReworkDisposition, string> = {
  unreviewed: "badge-ghost",
  confirmed_rework: "badge-error",
  partial_rework: "badge-warning",
  related_expected: "badge-info",
  unrelated: "badge-neutral",
};

/**
 * Renders detailed information about a rework event identified by the `reworkId` URL parameter.
 *
 * Displays the event summary, severity and root cause, core statistics, source PR details,
 * follow-up PR, and context artifacts.
 */
export default function ReworkEventDetailPage() {
  const params = useParams<{ reworkId: string }>();
  const reworkId = params.reworkId;

  const [detail, setDetail] = useState<ReworkEventDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addArtifactModalOpen, setAddArtifactModalOpen] = useState(false);
  const [newArtifactName, setNewArtifactName] = useState("");
  const [newArtifactType, setNewArtifactType] = useState("");
  const [newArtifactSummary, setNewArtifactSummary] = useState("");
  const [isSubmittingArtifact, setIsSubmittingArtifact] = useState(false);
  const [rootCauseInput, setRootCauseInput] = useState("");
  const [isUpdatingRootCause, setIsUpdatingRootCause] = useState(false);
  const [rootCauseError, setRootCauseError] = useState<string | null>(null);
  const [dispositionInput, setDispositionInput] =
    useState<ReworkDisposition>("unreviewed");
  const [isUpdatingDisposition, setIsUpdatingDisposition] = useState(false);
  const [dispositionError, setDispositionError] = useState<string | null>(null);

  useEffect(() => {
    async function loadReworkEventDetail() {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(
          `${API_BASE_URL}/api/rework-events/${encodeURIComponent(reworkId)}`,
        );

        if (!response.ok) {
          throw new Error("Rework event request failed.");
        }

        const data = (await response.json()) as ReworkEventDetail;

        setDetail(data);
        setRootCauseInput(data.rework_event.root_cause_label);
        setDispositionInput(data.rework_event.disposition);
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

  function openAddArtifactModal() {
    setNewArtifactName("");
    setNewArtifactType("");
    setNewArtifactSummary("");
    setAddArtifactModalOpen(true);
  }

  async function addContextArtifact() {
    if (isSubmittingArtifact) return;
    setIsSubmittingArtifact(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/ingest/context-artifact/${encodeURIComponent(
          reworkId,
        )}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name: newArtifactName,
            artifact_type: newArtifactType,
            summary: newArtifactSummary,
          }),
        },
      );

      if (!response.ok) {
        throw new Error("Create context artifact request failed.");
      }

      const createdArtifact = (await response.json()) as ContextArtifact;

      setDetail((currentDetail) => {
        if (!currentDetail) {
          return currentDetail;
        }

        return {
          ...currentDetail,
          context_artifacts: [
            ...currentDetail.context_artifacts,
            {
              id: createdArtifact.id,
              name: createdArtifact.name,
              artifact_type: createdArtifact.artifact_type,
              summary: createdArtifact.summary,
            },
          ],
        };
      });

      setAddArtifactModalOpen(false);
    } catch {
      setError(
        `Unable to create context artifact. Make sure the backend is running on ${API_BASE_URL}.`,
      );
    } finally {
      setIsSubmittingArtifact(false);
    }
  }

  async function updateRootCause() {
    if (isUpdatingRootCause) return;
    setIsUpdatingRootCause(true);
    setRootCauseError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/ingest/${encodeURIComponent(reworkId)}/root-cause`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            root_cause: rootCauseInput,
          }),
        },
      );

      if (!response.ok) {
        throw new Error("Update root cause request failed.");
      }

      const updatedDetail = (await response.json()) as ReworkEventDetail;
      setDetail(updatedDetail);
      setRootCauseInput(updatedDetail.rework_event.root_cause_label);
    } catch {
      setRootCauseError(
        `Unable to update root cause. Make sure the backend is running on ${API_BASE_URL}.`,
      );
    } finally {
      setIsUpdatingRootCause(false);
    }
  }

  async function updateDisposition() {
    if (isUpdatingDisposition) return;
    setIsUpdatingDisposition(true);
    setDispositionError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/ingest/${encodeURIComponent(reworkId)}/disposition`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            disposition: dispositionInput,
          }),
        },
      );

      if (!response.ok) {
        throw new Error("Update disposition request failed.");
      }

      const updatedDetail = (await response.json()) as ReworkEventDetail;
      setDetail(updatedDetail);
      setDispositionInput(updatedDetail.rework_event.disposition);
    } catch {
      setDispositionError(
        `Unable to update disposition. Make sure the backend is running on ${API_BASE_URL}.`,
      );
    } finally {
      setIsUpdatingDisposition(false);
    }
  }

  return (
    <main className="min-h-screen bg-base-200 px-4 py-8 text-base-content">
      <div className="mx-auto flex max-w-5xl flex-col gap-6">
        <header className="flex flex-col gap-3">
          <Link className="btn btn-primary w-fit btn-ghost" href="/">
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
                  <span
                    className={`badge whitespace-nowrap ${DISPOSITION_BADGE_CLASS[detail.rework_event.disposition]}`}
                  >
                    {
                      DISPOSITION_OPTIONS.find(
                        (option) =>
                          option.value === detail.rework_event.disposition,
                      )?.label
                    }
                  </span>
                </div>
                <h2 className="text-xl font-semibold">
                  {detail.rework_event.summary}
                </h2>
                <div className="flex flex-col gap-3 md:flex-row md:items-end">
                  <label className="form-control flex-1">
                    <span className="label mb-1">
                      <span className="label-text">Root Cause</span>
                    </span>
                    <input
                      className="input input-bordered"
                      onChange={(event) =>
                        setRootCauseInput(event.target.value)
                      }
                      value={rootCauseInput}
                    />
                  </label>
                  <button
                    className="btn btn-primary"
                    disabled={
                      isUpdatingRootCause ||
                      rootCauseInput === detail.rework_event.root_cause_label
                    }
                    onClick={updateRootCause}
                  >
                    {isUpdatingRootCause ? "Saving..." : "Save Root Cause"}
                  </button>
                </div>
                {rootCauseError && (
                  <div className="alert alert-error">
                    <span>{rootCauseError}</span>
                  </div>
                )}
                <div className="flex flex-col gap-3 md:flex-row md:items-end">
                  <label className="form-control flex-1">
                    <span className="label mb-1">
                      <span className="label-text">Reviewer Disposition</span>
                    </span>
                    <select
                      className="select select-bordered"
                      onChange={(event) =>
                        setDispositionInput(
                          event.target.value as ReworkDisposition,
                        )
                      }
                      value={dispositionInput}
                    >
                      {DISPOSITION_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    className="btn btn-primary"
                    disabled={
                      isUpdatingDisposition ||
                      dispositionInput === detail.rework_event.disposition
                    }
                    onClick={updateDisposition}
                  >
                    {isUpdatingDisposition ? "Saving..." : "Save Disposition"}
                  </button>
                </div>
                {dispositionError && (
                  <div className="alert alert-error">
                    <span>{dispositionError}</span>
                  </div>
                )}
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
                    {detail.source_pr.ai_generated && (
                      <span className="badge badge-info">AI-generated</span>
                    )}
                  </div>
                </div>
              </article>

              <article className="card bg-base-100 shadow-sm">
                <div className="card-body">
                  <h2 className="card-title text-lg">Follow-up PR</h2>
                  <p className="font-semibold">{detail.followup_pr.title}</p>
                  <div className="text-sm text-base-content/70">
                    PR {detail.followup_pr.number} in{" "}
                    {detail.followup_pr.repo_name}
                  </div>
                </div>
              </article>
            </section>

            <section className="grid gap-6 lg:grid-cols-2">
              <article className="card bg-base-100 shadow-sm lg:col-span-2">
                <div className="card-body">
                  <h2 className="card-title text-lg">Context Artifacts</h2>
                  {detail.context_artifacts &&
                  detail.context_artifacts.length > 0 ? (
                    <div className="grid gap-4 md:grid-cols-2">
                      {detail.context_artifacts.map((artifact) => (
                        <div
                          className="rounded-box border border-base-300 p-4"
                          key={artifact.id}
                        >
                          <p className="font-semibold">{artifact.name}</p>
                          <div className="mt-2 flex flex-wrap gap-2">
                            <span className="badge badge-outline">
                              {formatLabel(artifact.artifact_type)}
                            </span>
                          </div>
                          <p className="mt-3 text-sm text-base-content/70">
                            {artifact.summary}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-base-content/70">
                      No context artifacts are linked to this rework event.
                    </p>
                  )}
                </div>
              </article>
            </section>
            <section>
              <button
                className="btn btn-ghost btn-success btn-lg"
                onClick={openAddArtifactModal}
              >
                Add Context Artifact
              </button>
            </section>

            <div
              className={`modal ${addArtifactModalOpen ? "modal-open" : ""}`}
            >
              <div className="modal-box">
                <h2 className="text-lg font-semibold">Add Context Artifact</h2>
                <p className="mt-1 text-sm text-base-content/70">
                  Create a context artifact for rework event {reworkId}.
                </p>

                <div className="mt-5 flex flex-col gap-4">
                  <label className="form-control">
                    <span className="label mb-1">
                      <span className="label-text">Name</span>
                    </span>
                    <input
                      className="input input-bordered"
                      onChange={(event) =>
                        setNewArtifactName(event.target.value)
                      }
                      placeholder="Jira Sync Idempotency Contract"
                      value={newArtifactName}
                    />
                  </label>

                  <label className="form-control">
                    <span className="label mb-1">
                      <span className="label-text">Artifact Type</span>
                    </span>
                    <input
                      className="input input-bordered"
                      onChange={(event) =>
                        setNewArtifactType(event.target.value)
                      }
                      placeholder="runbook"
                      value={newArtifactType}
                    />
                  </label>

                  <label className="form-control">
                    <span className="label mb-1">
                      <span className="label-text">Summary</span>
                    </span>
                    <textarea
                      className="textarea textarea-bordered min-h-28"
                      onChange={(event) =>
                        setNewArtifactSummary(event.target.value)
                      }
                      placeholder="Describe the context this artifact gives future agents."
                      value={newArtifactSummary}
                    />
                  </label>
                </div>

                <div className="modal-action">
                  <button
                    className="btn btn-ghost"
                    onClick={() => setAddArtifactModalOpen(false)}
                  >
                    Cancel
                  </button>
                  <button
                    className="btn btn-success"
                    onClick={addContextArtifact}
                    disabled={isSubmittingArtifact}
                  >
                    Create Artifact
                  </button>
                </div>
              </div>
              <button
                aria-label="Close add artifact modal"
                className="modal-backdrop"
                onClick={() => setAddArtifactModalOpen(false)}
              />
            </div>
          </>
        )}
      </div>
    </main>
  );
}
