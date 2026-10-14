"""Clean-tree guard: which `git status --porcelain` lines block an eval run."""

from pathlib import Path

from cite_and_seek.eval.runinfo import dirty_paths


def test_clean_tree_has_no_blocking_paths():
    assert dirty_paths("") == []


def test_tracked_and_untracked_code_changes_block():
    porcelain = " M src/cite_and_seek/cli.py\n?? src/cite_and_seek/eval/new_stage.py\nA  tests/test_x.py\n"
    assert dirty_paths(porcelain) == [
        "src/cite_and_seek/cli.py", "src/cite_and_seek/eval/new_stage.py", "tests/test_x.py"]


def test_pending_results_files_do_not_block():
    assert dirty_paths("?? results/20261014T000000Z-run-abc1234.json\n?? results/\n") == []


def test_rename_uses_new_path():
    assert dirty_paths("R  old.py -> src/new.py\n") == ["src/new.py"]


def test_live_git_status_paths_are_complete():
    # Regression: stripping leading whitespace from git output cut the first path short.
    from cite_and_seek.eval.runinfo import _git

    for path in dirty_paths(_git("status", "--porcelain")):
        assert (Path(__file__).resolve().parents[1] / path).exists() or path.endswith("/")
