from __future__ import annotations

import importlib.util
from pathlib import Path


def _module():  # type: ignore[no-untyped-def]
    path = Path(__file__).resolve().parents[3] / "scripts" / "phase14_public_corpus.py"
    spec = importlib.util.spec_from_file_location("phase14_public_corpus", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_public_corpus_has_exact_safe_provenance_without_local_paths() -> None:
    corpus = _module().PUBLIC_PROJECTS

    assert len(corpus) == 4
    assert len({item["url"] for item in corpus}) == 4
    assert all(len(str(item["commit"])) == 40 for item in corpus)
    assert all(item["license"] for item in corpus)
    assert sum("APPLICATION" in item["roles"] for item in corpus) >= 2
    assert any("LARGE_PROJECT" in item["roles"] for item in corpus)
    assert any("WORKSPACE" in item["roles"] for item in corpus)
    assert all(str(item["url"]).startswith("https://github.com/") for item in corpus)
    assert "/Users/" not in repr(corpus)
    assert "C:\\" not in repr(corpus)


def test_rejected_candidates_have_explicit_safety_reasons() -> None:
    rejected = _module().REJECTED_PROJECTS

    assert len(rejected) >= 3
    assert all(item["url"].startswith("https://github.com/") for item in rejected)
    assert all(len(item["reason"]) >= 40 for item in rejected)
