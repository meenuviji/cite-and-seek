# Decision Log

Decisions agreed for Cite & Seek. Status is `accepted` or `pending`; pending decisions need human sign-off before work that depends on them.

## 1. Eval files locked; golden set unreadable to Claude
**Decision:** `evaluation/questions/**` and `evaluation/synthetic_incidents/**` are locked by Edit deny rules in `.claude/settings.json`, and Read is denied on `evaluation/questions/golden_set.json`. Integrity is verified at every checkpoint, and before every commit, with `git diff --quiet v0.0 -- evaluation/questions evaluation/synthetic_incidents && echo PASS || echo FAIL`, which must print `PASS`. The owner runs the check, not the agent: before each commit, Claude asks the owner to run it and waits for the result.
**Rationale:** Deny rules stop accidental edits and keep golden content out of Claude's context, preventing leakage into tunable parameters. The git diff catches changes the deny rules cannot, such as scripts or git operations. The owner runs it for separation of duties: the audited party does not run the audit.
**Amended:** originally `git diff --stat …` with no stated runner. The agent's attempts to run it were denied, most likely because the Read deny rules on the locked paths cover `git diff` on them, which is consistent with this separation.
**Status:** accepted

## 2. Stripped incident copies for the corpus
**Decision:** Original incident reports stay locked in `evaluation/synthetic_incidents/`. A committed script generates stripped copies into `corpus/incidents/` for indexing, keeping the original filenames (`SCN-xx.md`). Each copy keeps only `scenario`, `hypothetical_situation`, and `label`; `expected_evidence`, `expected_answer`, `real_file`, `real_function`, and `real_observable_behavior` are removed. The script's guard confirms exactly those 3 keys survive and no stripped key remains.
**Rationale:** The originals contain expected answers and evidence; indexing them directly would leak ground truth into retrieval. A real incident ticket describes symptoms, not the verified root-cause location; the `real_*` fields are scoring ground truth.
**Amended:** originally stripped only `expected_*` fields; `real_*` fields added before Commit A.
**Review:** The script's warn-only check flagged SCN-04 and SCN-07, whose kept text contains a whole word from their `real_function` values. The owner reviewed both and judged them not to be leaks: in SCN-04 the match is the config class the developer edited, which is part of the reported symptom; in SCN-07 it is the generic word "migration". Neither names a root-cause function. The owner also confirmed that no golden question references an incident file (`grep -c "SCN-"` on `golden_set.json` returned 0), so stripping cannot affect golden answerability.
**Status:** accepted

## 3. Incident scoring
**Decision:** Implemented in v0.2. Each incident's query is its `scenario` plus `hypothetical_situation`. Retrieval is scored as a hit when the incident's normalized `real_file` (decision 13) is in the top k. The answer is scored by the LLM judge (decision 14) against `expected_answer`. Leave-one-out (decision 11) excludes every chunk whose source is the incident's own file, not a single chunk, so it stays correct if chunking changes; exclusion happens in the grader, and the retriever interface stays `search(question: str, k)` (L8). Incidents are reported as a separate set, kept out of the golden split (decision 17), and never used to choose between configurations.
**Rationale:** A real ticket carries symptoms, so the query uses only the fields kept in the corpus copy. File-level exclusion keeps leave-one-out independent of chunk size, which v0.3 will vary. Ten scenarios are too few to steer configuration choices.
**Amended:** originally deferred to v0.2; accepted with the owner's file-level exclusion change.
**Status:** accepted

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
**Verification (upstream `aa86f56`):** All 24 files under `code/`, `tests/`, and `migrations/` are byte-identical to their mapped upstream files, so their line ranges are valid upstream line ranges. `docs/architecture.md` is derived from the upstream `README.md` (131 of its 142 non-blank lines appear verbatim in the README) but is a non-contiguous selection with 2 added header lines, so its line numbers do not correspond to `README.md`. It stays corpus-only (`source_path` = `docs/architecture.md`) to keep citations accurate. If golden evidence cites `README.md`, the v0.2 grader reports a failed mapping (decision 13), and the owner decides whether to add a file-level `README.md` → `docs/architecture.md` equivalence.
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
**Decision:** `claude-haiku-4-5-20251001` via the Anthropic API, temperature 0, pinned model ID.
**Rationale:** Abstention is a headline metric and requires strong instruction-following under uncertainty. A small model keeps retrieval failures visible in the metrics. The pinned ID and stable limits make runs reproducible.
**Comparison:** Done by the owner, as CLAUDE.md requires. Alternatives considered: a GPT-class small model (comparable, no advantage here); Gemini Flash free tier (rate limits and unpinned aliases hurt reproducibility for repeated eval runs); a local model via Ollama (weaker abstention would confound the headline metric).
**Secrets:** The API key lives in `.env`, created by the owner. Claude never reads, prints, or echoes `.env` or its contents; code loads it with python-dotenv at runtime only.
**Status:** accepted

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

## 14. LLM judge
**Decision:** Implemented in v0.2. The LLM judge is Gemini Flash via Google AI Studio on the free tier, with a pinned model ID, temperature 0. The judge client retries with backoff on rate-limit errors.
**Rationale:** A judge from a different model family than the generator avoids self-preference bias. The free tier's data-use terms are not a material risk, because the golden set is already public in this repository. Free-tier rate limits are acceptable for judging, which is a small, infrequent workload.
**Fallback:** If free-tier limits or terms become a problem, a local open-source judge via Ollama, behind the same judge interface. If the fallback is used, every run being compared is re-judged with the new judge and the calibration (decision 15) is repeated, so scores from different judges are never compared directly.
**Known tradeoff:** The golden set is public, so future models may train on it. The closed-book baseline (L13) helps detect this: a rise in closed-book accuracy signals contamination.
**Amended:** originally the paid tier, on the grounds that free-tier terms risked the test set entering training data. Reversed by the owner because the golden set is already public.
**Model ID:** The newest stable Gemini Flash model, with no `preview`, `exp`, `lite`, `image`, `tts`, or `live` suffix. The owner confirms the exact ID from the models list on their account before v0.2 Commit D. The `google-genai` SDK is added at Commit D, not before. The owner adds `GEMINI_API_KEY` to `.env`.
**Labels:** `correct`, `partial`, or `incorrect` against the reference answer, with a one-sentence reason written to `reports/` only. The judge prompt was approved as a draft; its final text is shown again at Commit D.
**Status:** accepted

## 15. Judge calibration
**Decision:** Implemented in v0.2. Before the judge is trusted, the owner hand-grades a sample of about 15 answers, and the grader reports judge-human agreement as percent agreement plus the 3x3 confusion counts (judge label by owner label). Cohen's kappa is not a headline metric at this sample size.
**Rationale:** An uncalibrated judge's scores cannot be distinguished from judge error. With about 15 items, kappa is unstable, while raw agreement and confusion counts show exactly where the judge and the owner differ.
**Status:** accepted

## 16. Retrieval metrics
**Decision:** Implemented in v0.2. The headline retrieval metrics are file-level. recall@k is the fraction of a question's golden evidence files found among the top-k chunks' `source_path`s after normalization (decision 13), averaged over questions. hit@k is the fraction of questions with at least one golden evidence file in the top k. Both are reported at k = 1, 3, 5, and 10, alongside MRR; the pipeline's k stays 5. Line-level overlap is reported as a secondary metric only if the golden schema includes line ranges.
**Rationale:** File-level matching is robust to chunk boundaries, which v0.3 will vary. Reporting several k values describes the retrieval curve without tuning k.
**Status:** accepted

## 17. Golden split and reporting
**Decision:** Implemented in v0.2, before any tuning. A fixed-seed 80/20 split of golden question IDs into a tuning split and a held-out split, stratified by answerable vs unanswerable, and by category if the schema has one. The split (IDs only) is committed. v0.2 to v0.5 use the tuning split only; the held-out split stays untouched until v1.0. Incidents stay out of the split. Every rate is reported with raw counts and a 95% Wilson confidence interval.
**Rationale:** Implements L10. The split leaves about 6 unanswerable questions for tuning and 2 held out, so one abstention moves the rate by roughly 17 or 50 points; raw counts and intervals keep small-sample rates from being over-read.
**Status:** accepted

## 18. Judge faithfulness gap
**Decision:** Known gap, not yet addressed. The judge (decision 14) measures agreement with the reference answer, not faithfulness to the retrieved chunks, so unsupported extra claims are not penalized. Citation validity (v0.2) only checks that each citation points at a retrieved chunk, not that the chunk supports the claim.
**Rationale:** Recorded so v0.2 correctness scores are not read as faithfulness scores. Addressing it is planned for a later checkpoint.
**Status:** pending

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
| L14 | Read deny on `/reports/**`. Per-question reports contain golden questions, answers, and judge reasons, so the agent cannot read them. | v0.2 Commit A | accepted |
| L15 | Only aggregate metrics and run configuration are committed, to `results/`: no question text, answers, or judge reasons, and question IDs only where needed. | v0.2 | accepted |
