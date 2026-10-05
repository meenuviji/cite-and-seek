# Cite & Seek — Evaluation Benchmark (v0.0)

## Corpus provenance

- **Source repository:** `Franklindot04/ecommerce-api` (GitHub)
- **License:** MIT (Copyright (c) 2025 Ajero Franklin) — see `corpus/docs/LICENSE`
- **Snapshot used:** the `main` branch zip provided directly by the project owner and
  inspected file-by-file on 2026-09-16. No specific commit hash was available from the
  zip archive; if reproducibility against a specific commit is needed later, this
  should be re-pinned via `git log -1` against a fresh clone.
- **Total corpus size:** ~1,872 lines of source across 26 application/test files, plus
  2 Alembic migrations and extracted README documentation sections.

All RAG/evaluation engineering in this project is original work built over the above
corpus. See `corpus/docs/LICENSE` for the upstream license terms.

## What's in the corpus, and what's excluded

**Included:** core business logic (`models.py`, `services/*.py`), API route handlers
(`api/*.py`), auth/rate-limiting/config/cache utilities, both Alembic migrations,
5 of 6 test files, and documentation extracted verbatim from the upstream README
(features, configuration, architecture, migration history).

**Excluded:** `main.py`, `database.py`, `redis_client.py`, `seed.py` (wiring/boilerplate,
low retrieval value), Dockerfile/docker-compose.yml, CODE_OF_CONDUCT.md,
CONTRIBUTING.md (no engineering-knowledge content for this use case).

## Question set: `questions/golden_set.json`

- **Total questions:** 53
- **Answerable:** 45 · **Unanswerable:** 8

**Note on the unanswerable count:** the original target discussed was 5 unanswerable
questions out of 50. That was intentionally increased to 8 — with 5, a single
question flipping outcome swings the measured abstention rate by 20 percentage
points, making the metric too noisy to defend confidently. 8 gives more stable
footing for the abstention/false-answer-rate metrics described below, at the cost
of a slightly larger total question count than originally planned. This is a
deliberate adjustment, not scope creep — no answerable-side content was added
"to reach a number."

### Category distribution (emerged bottom-up from repo inspection, not a preset quota)

| Category | Count | What it tests |
|---|---:|---|
| direct_code_lookup | 11 | Single, exact fact from one file (config value, enum, cache key) |
| single_file_reasoning | 9 | Requires understanding logic/control flow within one file |
| documentation_architecture | 6 | Answerable only from README-derived docs |
| troubleshooting | 5 | "What happens when X" scenario requiring tracing behavior |
| multi_file_reasoning | 5 | Requires combining evidence from 2+ files |
| state_machine_reasoning | 5 | Requires reasoning about `ALLOWED_TRANSITIONS` |
| test_derived_behavior | 4 | Ground truth established via test assertions, not just source |
| unanswerable | 8 | Plausible-sounding questions with no support in the corpus |

This distribution was not planned in advance category-by-category — it reflects what
the actual repository supports once inspected. Per the locked methodology, questions
were not generated first and verified after; each question was written only once its
supporting evidence had been read and confirmed (see `verified_by` field on every
entry).

### `source_type` field definitions

- `code` — ground truth established by reading application source code
- `test` — ground truth established by reading an existing test's assertions
- `documentation` — ground truth established from extracted README content, or
  confirmed absence across the full corpus (for unanswerable questions)
- `multi-source` — ground truth required combining two or more of the above

### `verification_status` field definitions

- `verified` — the fact was directly confirmed by reading the cited file(s)
- `verified_absent` — used only for unanswerable questions; confirms that a
  thorough search of the relevant corpus files (and, where relevant,
  `requirements.txt`) found no supporting evidence, rather than simply assuming
  absence

## Negative-evidence questions (handled with extra care per methodology)

Several questions (Q015, Q017, Q022, Q024, SCN-01, SCN-02, SCN-09) depend on
something **not** happening — e.g., no notification being sent from the payment
flow. For each of these, the absence was confirmed by tracing every call site of
the relevant function (e.g. grepping all callers of `write_order_notification`
across `app/api/*.py` and `app/services/*.py`) rather than inferring absence from
a single file. This is noted in each question's `verified_by` field.

## Deliberately calibrated-uncertainty case (SCN-06)

SCN-06 (concurrent checkout stock race) is intentionally not a clean
answerable/unanswerable binary. The corpus confirms there is no explicit
concurrency-control code, but does not confirm what actually happens under
concurrent load (that would depend on the database engine's transaction
isolation behavior, which isn't documented or tested in this corpus). The
expected answer models appropriate epistemic humility rather than a confident
claim in either direction — useful for testing whether a system overclaims
when the honest answer is partial.

## Anti-overclaiming discipline

Per the locked methodology, words like "always," "never," "indefinitely,"
"secure," and "production-ready" are avoided anywhere they aren't explicitly
supported by the corpus. For example, SCN-01's answer says the order "remains
in whatever status it had before the webhook call" rather than "remains PENDING
indefinitely" — the corpus confirms the mechanism, not a permanent outcome.
Similarly, SCN-03 and SCN-10 stop at confirming an observable fact (no auth
dependency; a placeholder secret key default) without asserting a security
judgment the corpus doesn't support.

## Synthetic incidents: `synthetic_incidents/SCN-01.md` – `SCN-10.md`

10 scenarios, each following the locked structure:

```
scenario → real_file → real_function → real_observable_behavior
    → hypothetical_situation → expected_evidence → expected_answer → label
```

Every scenario is explicitly labeled `SYNTHETIC — grounded in verified
repository behavior, not a real historical incident` and is anchored to
specific, verified code paths — none describe invented bugs or pretend
historical events. Where a test independently confirms the behavior
(SCN-01), that's noted; where no test covers the branch (SCN-08), that's
also noted rather than implied.

## What's next

v0.1 (naive baseline RAG) should be built and evaluated against this exact
question set without modification. Any future change to `golden_set.json`
(e.g., adding questions after discovering a retrieval gap) should be versioned
as a new corpus version rather than silently edited, so that experiment
results in `experiments/` remain comparable across checkpoints.
