# CLAUDE.md — Cite & Seek

Operating rules for Claude Code in this repository.

## Project
Cite & Seek is an evaluation-first RAG system over a small, real, MIT-licensed ecommerce API codebase (Franklindot04/ecommerce-api). Corpus: source code, documentation, and synthetic incident reports grounded in that code. Out of scope: chat logs, diagrams, agents, fine-tuning.

Objective: every component in the pipeline is justified by a measured result on a fixed evaluation set. The commit history is the experiment log.

## Methodology
1. Evaluation precedes retrieval. The golden eval set (53 questions: 45 answerable, 8 unanswerable) and 10 incident scenarios were frozen at tag v0.0, before any retrieval code existed.
2. Single-variable changes. Each checkpoint changes exactly one variable so metric deltas are attributable. Never bundle changes.
3. Measured justification. A component is added only if it produces a measured improvement on the fixed eval set, not because it is conventional practice.
4. Abstention is a first-class metric. The 8 unanswerable questions make abstention rate statistically meaningful. Do not remove or modify them.
5. No orchestration frameworks. LangChain and LlamaIndex are excluded to keep retrieval, embedding, and LLM components swappable behind hand-written interfaces and their behavior fully inspectable.

## Evaluation integrity
- Golden eval set and incident scenario files are read-only, enforced by deny rules in .claude/settings.json. Never edit, regenerate, reformat, or correct them. If an entry appears wrong, stop and report it.
- Leakage prevention: golden answers may be read only by the evaluation harness, for scoring. They must never inform prompts, chunk sizes, top-k, thresholds, rerankers, or any other tunable parameter.
- Ground-truth standard: every golden answer was verified by direct code inspection, not README inference or LLM generation. Any new ground truth must meet the same standard.

## Fixed decisions
- Language: Python.
- Embeddings: local sentence-transformers.
- Version control: Git + GitHub. Each checkpoint ends with a commit and an annotated tag (v0.1, v0.2, ...).
- Secrets: API keys live in .env, which is gitignored. Never hardcode credentials.
- Excluded: LangChain, LlamaIndex.

## Pending decisions (require human sign-off)
Generation LLM and LLM-as-judge model (vector store resolved in decision 5). When one arises, stop and present a comparison of industry-standard and free-tier options covering cost, latency, operational burden, and lock-in risk. Do not select unilaterally.

## Decision log
@docs/decisions.md

## Roadmap
- v0.0: Golden eval set, incident scenarios, evaluation README (complete)
- v0.1: Naive baseline CLI RAG, no optimization
- v0.2: Evaluation harness (recall@k, LLM-as-judge, abstention rate)
- v0.3: Chunking experiments, one variable at a time
- v0.4: Hybrid search and reranking, only if justified by measured improvement
- v0.5: Cost and latency profiling, abstention behavior
- v1.0: Deployment and experiment-log writeup

Work only on the current checkpoint. Do not build ahead.

## Change protocol
- Plan before execution. For each step, state the change, the rationale, and the expected effect on metrics, then wait for approval.
- Every plan includes the rationale for each design decision and each shell or git command.
- Challenge flawed assumptions or instructions with reasoning; do not comply silently.
- Keep diffs small and reviewable. Prefer several reviewed changes over one large one.
- No commits, tags, or pushes without explicit approval.
