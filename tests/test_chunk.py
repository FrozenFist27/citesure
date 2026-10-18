"""M3: chunking tests on the mini.pdf fixture."""

from __future__ import annotations

import pytest

from citesure.ingest.chunk import chunk_document, chunk_stats
from citesure.ingest.parse import parse_pdf
from tests.fixtures.make_fixture import build


@pytest.fixture(scope="module")
def chunks():
    path = build.__wrapped__ if False else None  # noqa: F841 - keep linter calm
    import tempfile
    from pathlib import Path

    p = Path(tempfile.mkdtemp()) / "mini.pdf"
    build(p)
    blocks = parse_pdf(p, doc_id="mini")
    return chunk_document(blocks, doc_id="mini", doc_title="MiniCorp Policy")


def test_section_paths_recorded(chunks):
    paths = {c.section_path for c in chunks}
    assert any("1 Purpose" in p for p in paths), paths
    assert any("2 Access Control" in p for p in paths)
    assert any("3 Incident Reporting" in p for p in paths)
    # nested heading appears in the path
    assert any("1.1 Scope" in p or "1.1.1 Exclusions" in p for p in paths)


def test_page_metadata(chunks):
    for c in chunks:
        assert 1 <= c.page_start <= 3
        assert c.page_start <= c.page_end <= 3
        assert c.chunk_id.startswith("mini:")


def test_table_is_its_own_chunk_with_caption(chunks):
    tables = [c for c in chunks if c.kind == "table"]
    assert len(tables) == 1
    t = tables[0]
    assert "|" in t.text and "Administrator" in t.text
    assert "2 Access Control" in t.section_path
    # caption prepended: first line of text is the section name
    assert t.text.startswith("2 Access Control")


def test_text_chunks_respect_max_words(chunks):
    for c in chunks:
        if c.kind == "text":
            assert c.n_words <= 350, c.chunk_id


def test_page_offsets_cover_text(chunks):
    for c in chunks:
        assert c.page_offsets
        assert c.page_offsets[0][0] == 0


def test_section_and_fixed_modes_differ():
    import tempfile
    from pathlib import Path

    from citesure.ingest.parse import parse_pdf

    p = Path(tempfile.mkdtemp()) / "mini.pdf"
    build(p)
    blocks = parse_pdf(p, doc_id="mini")
    sec = chunk_document(blocks, doc_id="mini", doc_title="T", mode="section")
    fx = chunk_document(blocks, doc_id="mini", doc_title="T", mode="fixed")
    assert sec and fx
    assert {c.section_path for c in sec} != {c.section_path for c in fx}


def test_chunk_stats(chunks):
    s = chunk_stats(chunks)
    assert s["n_chunks"] == len(chunks)
    assert s["n_tables"] == 1
    assert s["mean_words"] > 0
