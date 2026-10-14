"""Path normalization against the real corpus (decision 13). No golden data."""

import pytest

from cite_and_seek.eval import CORPUS_ROOT
from cite_and_seek.eval.paths import PathNormalizer, normalize_all, strip_prefixes


@pytest.fixture(scope="module")
def normalizer() -> PathNormalizer:
    return PathNormalizer(CORPUS_ROOT)


@pytest.mark.parametrize("raw, expected", [
    ("app/models.py", "app/models.py"),  # already upstream
    ("code/models.py", "app/models.py"),  # corpus-relative
    ("corpus/code/models.py", "app/models.py"),
    ("./code/models.py", "app/models.py"),
    ("./corpus/code/services/order_service.py", "app/services/order_service.py"),
    ("migrations/6f5e3d5e8133_initial_migration.py",
     "alembic/versions/6f5e3d5e8133_initial_migration.py"),
    ("tests/test_auth.py", "tests/test_auth.py"),  # same in both forms
    ("docs/requirements.txt", "requirements.txt"),
    ("docs/architecture.md", "docs/architecture.md"),  # corpus-only
])
def test_canonical(normalizer, raw, expected):
    assert normalizer.canonical(raw) == expected


@pytest.mark.parametrize("raw", [
    "README.md",  # architecture.md is not mapped to README (decision 6)
    "app/database.py",  # imported by the code but absent from the corpus
    "code/missing.py",
    "",
])
def test_unmapped(normalizer, raw):
    assert normalizer.canonical(raw) is None


def test_strip_prefixes_repeats():
    assert strip_prefixes("./corpus/./code/x.py") == "code/x.py"


def test_normalize_all_counts(normalizer):
    mapped, report = normalize_all(normalizer, {
        "q1": ("code/models.py", "app/schemas.py"),
        "q2": ("README.md",),
    })
    assert mapped["q1"] == {"app/models.py", "app/schemas.py"}
    assert report.paths == 3
    assert report.normalized == 1
    assert report.unmapped_ids == ("q2",)
