"""Path normalization for scoring (decision 13).

Every path is reduced to one canonical form, the upstream source_path that
chunks carry: strip a leading "./" and "corpus/", then map a corpus path
through path_map. A path that is already a known source_path is kept. Anything
else is unmapped, and an unmapped path stops the run.
"""

from dataclasses import dataclass
from pathlib import Path

from cite_and_seek.corpus import list_corpus_paths
from cite_and_seek.path_map import to_source_path


class UnmappedPathsError(ValueError):
    """Raised when scored paths fail to map; carries question IDs, not paths."""

    def __init__(self, ids: list[str]) -> None:
        super().__init__(f"{len(ids)} item(s) have unmapped paths: {sorted(ids)}")
        self.ids = sorted(ids)


def strip_prefixes(path: str) -> str:
    path = path.strip()
    while True:
        if path.startswith("./"):
            path = path[2:]
        elif path.startswith("corpus/"):
            path = path[len("corpus/"):]
        else:
            return path


class PathNormalizer:
    def __init__(self, corpus_root: Path) -> None:
        self.by_corpus_path = {p: to_source_path(p) for p in list_corpus_paths(corpus_root)}
        self.source_paths = set(self.by_corpus_path.values())
        # A string that is both a corpus path and a source path must mean the same file.
        for path in self.source_paths & self.by_corpus_path.keys():
            if self.by_corpus_path[path] != path:
                raise ValueError(f"ambiguous path form: {path}")

    def canonical(self, path: str) -> str | None:
        stripped = strip_prefixes(path)
        if stripped in self.by_corpus_path:
            return self.by_corpus_path[stripped]
        if stripped in self.source_paths:
            return stripped
        return None


@dataclass(frozen=True)
class NormalizationReport:
    paths: int  # total paths seen
    normalized: int  # paths whose canonical form differs from the input
    unmapped_ids: tuple[str, ...]  # items with at least one unmapped path


def normalize_all(
    normalizer: PathNormalizer, items: dict[str, tuple[str, ...]]
) -> tuple[dict[str, frozenset[str]], NormalizationReport]:
    """Map each item's paths to canonical form. Does not raise; check unmapped_ids."""
    mapped, paths, normalized, unmapped = {}, 0, 0, []
    for item_id, raw_paths in items.items():
        canonical = set()
        for raw in raw_paths:
            paths += 1
            result = normalizer.canonical(raw)
            if result is None:
                unmapped.append(item_id)
                continue
            normalized += result != raw
            canonical.add(result)
        mapped[item_id] = frozenset(canonical)
    return mapped, NormalizationReport(paths, normalized, tuple(sorted(set(unmapped))))
