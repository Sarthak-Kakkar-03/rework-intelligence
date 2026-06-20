# Rework Autopsy

Rework Autopsy is a small product loop for AI-assisted engineering work.

I built it to detect when an AI-generated pull request is followed by likely human rework, show that rework in a dashboard, and let a human add context artifacts that future AI coding agents should use before making similar changes.

The goal is not to blame AI for every follow-up PR. The goal is to help an engineering leader see where AI-assisted work may be creating cleanup work, and what missing context could reduce that next time.

---

## Run With Docker Compose

```bash
docker compose up --build
```

Open:

```text
http://localhost:3000
```

The backend container reseeds SQLite on startup, so every demo starts from the same data.

---

## Manual Local Run

Start the backend:

```bash
./scripts/reset_db.sh
cd backend
uv sync
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Start the frontend in another terminal:

```bash
cd frontend-rework-autopsy
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

---

## What Did I Build?

I built an end-to-end prototype with:

* FastAPI backend
* SQLite database
* Seeded PR, team, repository, rework, and context artifact data
* Rule-based rework detector
* Next.js dashboard
* Rework detail page
* Demo flow for adding PR pairs and recomputing rework
* UI flow for creating context artifacts linked to rework events
* Placeholder root cause labels for grouping different kinds of rework

The core loop is:

```text
AI-assisted PR
  → likely human follow-up PR
  → rework event
  → dashboard/detail page
  → human adds missing context artifact
```

---

## Who Is It For?

This is for engineering leaders, platform teams, and developers responsible for rolling out AI coding agents.

The user I had in mind is someone who does not only care whether AI is making engineers faster. They also care whether AI-assisted work is creating downstream cleanup, and what institutional knowledge should be made available to agents before similar work happens again.

---

## What Question Does It Answer?

Rework Autopsy helps answer:

> Where is AI-assisted work creating follow-up rework, and what context should we preserve so future agents avoid similar mistakes?

The dashboard answers where rework is happening.

The detail page shows why a PR pair was flagged.

The context artifact flow gives the team a lightweight way to capture what the agent may have been missing.

---

## What Data Is Real, Mocked, Or Assumed?

### Mocked

The prototype uses seeded mock data for:

* Pull requests
* Repositories
* Teams
* Changed files
* Rework events
* Context artifacts
* Root cause labels

### Real

The application structure is real:

* FastAPI routes
* SQLite persistence
* Rule-based rework recomputation
* Typed frontend data flow
* Dashboard and detail views
* Human-created context artifacts

### Assumed

The prototype assumes:

* `ai_generated` is already known for each PR
* PR closed timestamps are available
* Changed file paths are available
* A later PR can be compared against an earlier AI-assisted PR
* A human can decide what context is worth preserving
* Root cause labels can be reviewed and edited by a human

In a production version, this data would likely come from GitHub, Faros-style normalized engineering data, or another source of PR metadata.

---

## How Does Rework Detection Work?

The detector looks for likely relationships between an AI-generated PR and a later follow-up PR.

It considers signals like:

* Was the original PR AI-generated?
* Did the follow-up PR happen shortly after?
* Did both PRs touch overlapping files?
* Does the follow-up title or description suggest a fix, cleanup, revert, or adjustment?

I kept the detector rule-based because I wanted the output to be explainable. For this prototype, I cared more about showing the product loop clearly than hiding the logic behind a black-box score.

Root cause labels are lightweight placeholders used to group rework into issue types. In a real system, humans should be able to review and edit them.

---

## What Tradeoffs Did I Make?

I used simple, explainable rules instead of an ML or LLM-based detector. That made the demo easier to test, explain, and trust.

I used SQLite and JSON seed data instead of a real integration. This keeps the project easy to run and avoids spending most of the week on data plumbing.

The current system treats rework as a simple AI PR → follow-up PR relationship. In reality, rework can happen across multiple PRs, partial fixes, reopened tickets, and longer chains.

I did not inspect actual code diffs yet. I focused on metadata and changed-file overlap because code-level analysis would be harder to mock well and easier to overclaim.

Human rework hours are estimated with a simple heuristic. A real version would need better signals like PR size, review time, cycle time, ticket history, or manually entered estimates.

Context artifacts are currently shallow metadata objects that can be created from the UI. They are not backed by a full file or document storage system yet. That is intentional for the demo: I wanted to show the rework-to-context loop first before building a larger system for storing, versioning, and retrieving actual context files.

---

## What Would I Do With One More Week?

With one more week, I would first add a way to mark flagged rework as a false positive. That feedback is important because not every follow-up PR is bad rework, and the system should learn from human judgment instead of treating every detection as final.

I would also replace the seed data with GitHub or Faros-style normalized PR data so the loop could run on a real repository.

If code diffs were available, I would add an LLM-assisted layer to summarize what changed between the AI PR and the follow-up PR. I would still keep the rule-based signals visible so the system remains explainable.

I would add richer signals like PR review comments, linked tickets, revert relationships, lines changed, and commit metadata.

I would expand the data model to support multiple follow-up PRs for one AI-assisted PR.

I would also build a deeper context artifact system. Right now, artifacts are lightweight records. A real version should store the actual files or documents behind them, such as runbooks, architecture notes, API contracts, testing guidelines, or prior incident notes.

---

## Things I Deliberately Did Not Build

I did not build a full GitHub integration. Seeded data made the demo more reliable and kept the focus on the product loop.

I did not build a blame system. The point is not to say “AI caused this.” The point is to surface places where AI-assisted work appears to create human cleanup, then help the team improve future agent context.

I did not build a code-rewriting agent. This product is about visibility, diagnosis, and context improvement rather than automatically changing code.

I did not build a full context file system. Context artifacts are shallow objects for now. They can be created from the UI and linked to rework events, but the underlying file storage, retrieval, versioning, and search layer is out of scope for this demo.

---

## How Did I Use AI?

I used AI as a development assistant, but tried to keep the product decisions and implementation boundaries under my control.

I used Codex locally in my IDE to discuss future additions and help with controlled implementation tasks like boilerplate, SQL changes, and type updates.

I also used CodeRabbit on PRs as a review agent. That helped me get a second pass on possible bugs, unclear code, and places where the implementation was getting too broad.

I kept AI changes incremental so I could still understand and review what changed.

---

## What Did AI Get Wrong Or Make Harder?

AI was helpful for speed, but it sometimes pushed toward unnecessary breadth.

For example, when I asked it to verify a small set of frontend model types against the SQL migration, it generated types for nearly every table instead of only the types needed by the current UI.

Another example was the demo flow for adding PR pairs. I wanted a simple frontend-driven way to create PR pairs with different timestamps. AI tried to move that logic into the backend and compute close-time gaps internally, which made the API more complicated than necessary. I kept the simpler approach because it was easier to explain, test, and revert.

The main lesson was that AI works best when the task is specific and bounded. When the request is vague, it tends to add code instead of protecting the product shape.

---

## Why This Is Faros-Shaped

Faros helps engineering organizations understand how work happens across tools, teams, code, delivery, and outcomes.

Rework Autopsy fits that shape because it connects engineering activity data to a practical operating question:

> Is AI-assisted development creating downstream human cleanup, and what should we change in the engineering system to improve it?

I wanted the output to be more than a metric. The loop should help a team notice a pattern, inspect the evidence, and preserve useful context for the next agent-assisted change.
