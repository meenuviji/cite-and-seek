# Cite & Seek

Evaluation-first retrieval-augmented generation (RAG) for question answering over a real codebase. Cite & Seek answers questions about an open-source ecommerce API ([Franklindot04/ecommerce-api](https://github.com/Franklindot04/ecommerce-api), MIT) from its source code, tests, migrations, and documentation, cites the file and line range behind every claim, and abstains explicitly when the retrieved context does not contain the answer.

The point of the project is the measurement, not the pipeline. Every component is meant to earn its place through a measured result on a fixed evaluation set, and the commit history is the experiment log.

## Why evaluation-first

RAG systems are easy to build and hard to trust. Changes that feel like improvements (bigger chunks, more context, a reranker) often move nothing, or quietly trade correctness for confident wrong answers. This project inverts the usual order:

1. **The test set came first.** A golden set of 53 questions (45 answerable, 8 deliberately unanswerable) and 10 synthetic incident scenarios were written, verified by direct code inspection, and frozen at tag `v0.0`, before any retrieval code existed.
2. **One variable per change.** Each checkpoint changes exactly one thing, so a metric delta can be attributed to it.
3. **Abstention is a headline metric.** "I don't know" is scored as a correct answer to an unanswerable question and as a failure on an answerable one, so a system cannot look good by always answering.
4. **No orchestration frameworks.** Retrieval, embedding, and generation sit behind small hand-written interfaces so every step is inspectable and swappable.

## Architecture

```
corpus/ ──► loader ──► line-aligned chunker ──► MiniLM embeddings ──► numpy brute-force index
                       (~200 tokens, no overlap,        (all-MiniLM-L6-v2,       (exact cosine search)
                        path + line range per chunk)     normalized vectors)
question ──► embed ──► top-k chunks (k = 5) ──► Claude Haiku 4.5 ──► answer with [path:start-end] citations
                                                (temperature 0)        or "ABSTAIN: <what is missing>"
```

- **Loader** reads only files under `corpus/` and refuses any path that resolves elsewhere.
- **Chunker** packs whole lines into chunks of at most 200 tokens of the embedding model's tokenizer (202 with special tokens, under the model's 256-token limit), so every chunk has an exact line range.
- **Paths**: each chunk carries its corpus path and its upstream repository path; citations use the upstream path. The mapping is an explicit table derived from the code's imports and the upstream Alembic config, and 24 of the corpus files are verified byte-identical to upstream, so cited line ranges are real upstream line ranges.
- **Retrieval**: `all-MiniLM-L6-v2` sentence embeddings with exact cosine search behind `Embedder`, `VectorIndex`, and `Retriever` interfaces.
- **Generation**: `claude-haiku-4-5-20251001` at temperature 0 with a zero-shot prompt that answers only from the retrieved chunks, cites each claim, and abstains with a fixed `ABSTAIN:` marker so abstention is detected by a string check, not a model call.
- **Evaluation harness** (`src/cite_and_seek/eval/`): split loader, path normalization, retrieval metrics, answer checks, and an LLM judge (`gemini-3.6-flash`, temperature 0, JSON-schema output) from a different model family than the generator.

## How to run

Requirements: Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

API keys go in `.env` at the repository root (gitignored):

```
ANTHROPIC_API_KEY=...   # generation (ask, eval run)
GEMINI_API_KEY=...      # LLM judge (eval judge)
```

Retrieval and generation:

```bash
uv run cite-and-seek search "What happens when a client exceeds the request limit?"      # top-5 chunks, no LLM
uv run cite-and-seek ask "What happens when a client exceeds the request limit?"         # cited answer or explicit abstention
```

Evaluation (tuning split by default; every run refuses to start on uncommitted code and records the git SHA):

```bash
uv run cite-and-seek eval check         # load golden set and incidents, normalize paths
uv run cite-and-seek eval retrieval     # hit@k, recall@k, MRR at k = 1, 3, 5, 10
uv run cite-and-seek eval run           # generate answers; abstention, citation, cost, latency
uv run cite-and-seek eval judge         # LLM-judge correctness of the latest run
uv run cite-and-seek eval run --closed-book && uv run cite-and-seek eval judge --closed-book
uv run cite-and-seek eval incidents     # incident retrieval, leave-one-out by file
uv run cite-and-seek eval dev-overlap   # dev-query similarity to golden questions
uv run pytest -q                        # unit tests (synthetic fixtures only)
```

Aggregates go to `results/` (committed). Per-question detail goes to `reports/` (gitignored).

## Baseline results (v0.2)

Tuning split (42 questions: 36 answerable, 6 unanswerable). Proportions show count/n with a 95% Wilson interval; recall and MRR are means with a 95% bootstrap interval. Full table, configuration, and caveats: [`results/v0.2-summary.md`](results/v0.2-summary.md).

RESULTS_TABLE

## Evaluation integrity

The golden set and incident scenarios were frozen at `v0.0` and are protected by editor deny rules, plus a `git diff --quiet v0.0` check the owner runs before every push; the agent that writes the code cannot read the golden set, the incident originals, or the per-question reports. Fifteen leakage controls (L1–L15 in [`docs/decisions.md`](docs/decisions.md)) keep ground truth out of everything tunable: the corpus copies of incidents are stripped of their answers and root-cause fields; only the grader reads ground truth and it prints aggregates and IDs only; prompt examples may come only from a separate developer-written dev set; only aggregates are committed; and each experiment is preregistered. A fixed-seed split holds out 11 of the 53 questions, untouched until the v1.0 run. A closed-book baseline (the same model with no retrieval) measures what retrieval actually adds and would reveal contamination if future models learn the public test set.

## Known limitations

- **Small sample.** 42 tuning questions, of which only 6 are unanswerable: one abstention moves that rate by about 17 points, so intervals are wide and are always reported.
- **Public test set.** The golden set is in this public repository, so future models may train on it; the closed-book baseline is the guard.
- **No faithfulness metric.** The judge scores agreement with the reference answer, not whether each claim is supported by the retrieved chunks; citation validity checks only that a citation points at a retrieved chunk.
- **Uncalibrated judge.** Judge-human agreement has not yet been measured, so judge-based numbers are labeled uncalibrated.
- **Closed-book baseline pending** (API access issue during the v0.2 run); RAG gain over closed-book is not yet measured.
- **Incident scenario SCN-07** describes a symptom that hints at its own cause, so its retrieval score is likely optimistic.

## Roadmap

- **v0.3** Chunking experiments, one variable at a time, starting with chunk sizes at or below 128 tokens (the embedding model's training length).
- **v0.4** Hybrid lexical + dense search and reranking, kept only if they improve the measured baseline.
- **v0.5** Cost and latency profiling; abstention behavior.
- **v1.0** One run on the held-out split, deployment, and an experiment-log writeup.

Design decisions and their rationale are logged in [`docs/decisions.md`](docs/decisions.md).
