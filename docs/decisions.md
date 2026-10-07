# Decision Log

Decisions agreed for Cite & Seek. Status is `accepted` or `pending`; pending decisions need human sign-off before work that depends on them.

## 1. Eval files locked; golden set unreadable to Claude
**Decision:** `evaluation/questions/**` and `evaluation/synthetic_incidents/**` are locked by Edit deny rules in `.claude/settings.json`, and Read is denied on `evaluation/questions/golden_set.json`. Integrity is verified at every checkpoint with `git diff --stat v0.0 -- evaluation/questions evaluation/synthetic_incidents`, which must print nothing.
**Rationale:** Deny rules stop accidental edits and keep golden content out of Claude's context, preventing leakage into tunable parameters. The git diff catches changes the deny rules cannot, such as scripts or git operations.
**Status:** accepted

## 2. Stripped incident copies for the corpus
**Decision:** Original incident reports stay locked in `evaluation/synthetic_incidents/`. A committed script generates stripped copies into `corpus/incidents/` for indexing, keeping the original filenames (`SCN-xx.md`). Each copy keeps only `scenario`, `hypothetical_situation`, and `label`; `expected_evidence`, `expected_answer`, `real_file`, `real_function`, and `real_observable_behavior` are removed. The script's guard confirms exactly those 3 keys survive and no stripped key remains.
**Rationale:** The originals contain expected answers and evidence; indexing them directly would leak ground truth into retrieval. A real incident ticket describes symptoms, not the verified root-cause location; the `real_*` fields are scoring ground truth.
**Amended:** originally stripped only `expected_*` fields; `real_*` fields added before Commit A.
**Review:** The script's warn-only check flagged SCN-04 and SCN-07, whose kept text contains a whole word from their `real_function` values. The owner reviewed both and judged them not to be leaks: in SCN-04 the match is the config class the developer edited, which is part of the reported symptom; in SCN-07 it is the generic word "migration". Neither names a root-cause function. The owner also confirmed that no golden question references an incident file (`grep -c "SCN-"` on `golden_set.json` returned 0), so stripping cannot affect golden answerability.
**Status:** accepted

## 3. Incident scoring
**Decision:** How the 10 incident scenarios are scored is deferred to v0.2.
**Rationale:** Scoring belongs to the evaluation harness, and building it now would mean building ahead of the current checkpoint.
**Status:** pending

## 4. Embedding model
**Decision:** `all-MiniLM-L6-v2` (sentence-transformers) is the naive baseline embedding model. Its input limit is 256 tokens.
**Rationale:** It is a small, widely used local model that fits the fixed sentence-transformers decision and gives a conventional baseline to measure later changes against.
**Status:** accepted

## 5. Vector store
**Decision:** In-memory numpy brute-force cosine search, behind a swappable interface.
**Rationale:** Brute force is exact search, and a vector database adds no measurable benefit at this corpus size. The interface keeps a later swap possible if a measured need appears.
**Status:** accepted

## 6. Baseline chunking
**Decision:** Fixed-size chunks of about 200 MiniLM tokens, no overlap, applied to all file types. Each chunk carries its line range, `corpus_path` (relative to `corpus/`), and `source_path` (the upstream repo path). Citations display `source_path`. The corpus-to-upstream mapping is the explicit table in `src/cite_and_seek/path_map.py`, derived from the code itself (import statements) and from upstream config at a pinned commit (`alembic.ini`, root file listing), never from the golden set.
**Rationale:** The size is set by the embedding model's 256-token input limit, not by tuning. Carrying both path forms lets recall@k be computed in v0.2 against golden paths written in either form (see decision 13).
**Amended:** originally a single path relative to `corpus/`. The owner's check found golden paths in both upstream (`app/…`) and corpus-relative (`code/…`) forms.
**Corpus coverage:** `app/database.py` and `app/redis_client.py` are imported by the code but absent from the corpus. The owner checked that the golden set references `database.py` 0 times and `redis_client` once, in an unanswerable question, so its absence is intended and correct.
**Status:** accepted

## 7. Smoke testing
**Decision:** Smoke testing uses a separate dev set written by the developer, never golden questions.
**Rationale:** Developing against golden questions would leak the eval set into design choices and inflate measured results.
**Status:** accepted

## 8. Environment
**Decision:** Python 3.12, uv, and `pyproject.toml` at the repo root. `corpus/docs/requirements.txt` belongs to the corpus, not this project.
**Rationale:** One project manifest at the root keeps project dependencies separate from upstream corpus content.
**Status:** accepted

## 9. Generation LLM
**Decision:** Not yet chosen.
**Rationale:** Needs a human-approved comparison of cost, latency, operational burden, and lock-in risk, per CLAUDE.md.
**Status:** pending

## 10. README count discrepancy
**Decision:** Not yet resolved. `evaluation/README.md` is left unchanged while the discrepancy is reviewed.
**Rationale:** The README's corpus size figures don't match a direct file count; the owner is reviewing it separately.
**Status:** pending

## 11. Leave-one-out incident scoring
**Decision:** In v0.2, when an incident scenario is scored, its own stripped copy in `corpus/incidents/` is excluded from retrieval.
**Rationale:** The scenario query is drawn from the same incident text that is indexed, so the incident would otherwise retrieve itself and inflate the score.
**Note:** SCN-07's `hypothetical_situation` hints at its cause, so it may score high in v0.2 even with leave-one-out.
**Status:** accepted

## 12. Chunk sizes at or below 128 tokens
**Decision:** Not yet run. v0.3 candidate: test chunk sizes at or below 128 tokens against the 200-token baseline (decision 6).
**Rationale:** `all-MiniLM-L6-v2` was trained on 128-token sequences; the 256-token input limit does not mean longer inputs embed well.
**Status:** pending

## 13. Grader path normalization
**Decision:** In v0.2, the grader normalizes every path on both sides before comparing: strip a leading `./` and `corpus/`, then map through the committed table (`src/cite_and_seek/path_map.py`) to one canonical form. It reports counts only: how many golden paths needed normalization, and how many failed to map. Any failed mapping stops the run.
**Rationale:** Golden paths appear in upstream, corpus-relative, `corpus/`-prefixed, and `./` forms. Comparing without normalization would score correct retrievals as misses.
**Status:** accepted

## Leakage controls
Each control lists its status and the point where it is implemented.

| ID | Control | Implemented at | Status |
|---|---|---|---|
| L1 | The loader indexes only files under `corpus/` and raises an error on any other path. | Commit C | accepted |
| L2 | Incident stripping per amended decision 2. | Commit A | accepted |
| L3 | Leave-one-out incident scoring per decision 11. | v0.2 | accepted |
| L4 | After the strip script runs, add a Read deny on `/evaluation/synthetic_incidents/**` in the same commit. | Commit A | accepted |
| L5 | Read and Edit deny on `/evaluation/README.md`. The owner fixes its counts by hand. | Commit 0 | accepted |
| L6 | Deny rules block `git show`, `git cat-file`, and `git grep`. Golden and incident originals are never accessed through scripts, git, or any other route except the v0.2 grader and the Commit A strip script. | Commit 0 | accepted |
| L7 | Grader terminal output shows aggregates and question IDs only; per-question detail goes to `reports/`, which is gitignored. | v0.2 | accepted |
| L8 | The pipeline interface accepts `question: str` only. | Commit E / v0.2 | accepted |
| L9 | Few-shot examples in any prompt come only from the dev set. | generation | accepted |
| L10 | Fixed-seed stratified 80/20 split of golden IDs into a tuning split and a held-out split, IDs only. v0.3 to v0.5 use the tuning split only; the held-out split runs once at v1.0. | v0.2, before any tuning | accepted |
| L11 | Each experiment's variants and target metric are preregistered in this file before running; every run is logged. | v0.3 onward | accepted |
| L12 | The grader reports each dev query's maximum embedding similarity to any golden question, scores only. | v0.2 | accepted |
| L13 | Closed-book baseline: the generation LLM answers golden questions with no retrieval; RAG gain is reported relative to it. | v0.2 | accepted |
