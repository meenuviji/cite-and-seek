"""Corpus-to-upstream path mapping (decision 6).

Each chunk carries corpus_path (relative to corpus/) and source_path (the path
in the upstream repo). Every row is derived from the code or from upstream
config at the pinned commit, never from the golden set.
"""

UPSTREAM_REPO = "https://github.com/Franklindot04/ecommerce-api"
UPSTREAM_COMMIT = "aa86f56f571bb3eda9d366ec37d01ffdc8bc5512"

# (corpus path or folder prefix, upstream path or folder prefix, evidence).
# Folder rows end with "/"; file rows match exactly; the longest match wins.
# An upstream value of None means the file has no upstream counterpart, and
# its source_path is its corpus_path.
PATH_MAP: tuple[tuple[str, str | None, str], ...] = (
    ("code/", "app/",
     "imports: from app.models, app.database, app.schemas, app.auth_utils, app.config, "
     "app.cache_utils, app.rate_limiter, app.services.*_service; import app.api.products"),
    ("tests/", "tests/", "import: from tests.conftest"),
    ("migrations/", "alembic/versions/",
     "upstream alembic.ini: script_location = %(here)s/alembic, no version_locations"),
    ("docs/LICENSE", "LICENSE", "upstream root listing"),
    ("docs/requirements.txt", "requirements.txt", "upstream root listing"),
    ("docs/architecture.md", None,
     "no upstream counterpart: upstream has no docs/ folder, and README.md does not match"),
    ("incidents/", None, "synthetic incident reports, no upstream counterpart"),
)


class UnmappedPathError(ValueError):
    """Raised for a corpus path that no PATH_MAP row covers."""


def to_source_path(corpus_path: str) -> str:
    """Map a corpus-relative path to its upstream source path."""
    for prefix, upstream, _ in sorted(PATH_MAP, key=lambda row: len(row[0]), reverse=True):
        if corpus_path == prefix or (prefix.endswith("/") and corpus_path.startswith(prefix)):
            return corpus_path if upstream is None else upstream + corpus_path[len(prefix):]
    raise UnmappedPathError(corpus_path)
