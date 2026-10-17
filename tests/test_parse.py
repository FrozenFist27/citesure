"""M2: parsing tests on the synthetic mini.pdf fixture (no network, no LLM)."""

from __future__ import annotations

import pytest

from citesure.ingest.parse import Block, parse_pdf, parse_summary
from tests.fixtures.make_fixture import build


@pytest.fixture(scope="module")
def mini_pdf(tmp_path_factory):
    path = tmp_path_factory.mktemp("fixtures") / "mini.pdf"
    build(path)
    return path


@pytest.fixture(scope="module")
def blocks(mini_pdf) -> list[Block]:
    return parse_pdf(mini_pdf, doc_id="mini")


def test_pages_are_one_based(blocks):
    pages = {b.page for b in blocks}
    assert pages == {1, 2, 3}


def test_headings_detected_at_all_levels(blocks):
    headings = [(b.level, b.text) for b in blocks if b.kind == "heading"]
    levels = {lv for lv, _ in headings}
    assert 1 in levels and 2 in levels and 3 in levels, headings
    texts = " | ".join(t for _, t in headings)
    assert "Purpose" in texts
    assert "Scope" in texts
    assert "Exclusions" in texts
    assert "Access Control" in texts


def test_table_extracted_as_markdown(blocks):
    tables = [b for b in blocks if b.kind == "table"]
    assert len(tables) == 1, [b.text for b in blocks if b.kind == "table"]
    md = tables[0].text
    assert md.startswith("|")
    assert "Role" in md and "Administrator" in md
    assert "---" in md  # markdown separator row
    assert tables[0].page == 2


def test_table_text_not_duplicated_in_body(blocks):
    # The words inside the table must not also appear in a text block
    table_words = {"Administrator", "Contractor"}
    for b in blocks:
        if b.kind == "text":
            assert not (table_words <= set(b.text.split())), b.text


def test_running_header_removed(blocks):
    for b in blocks:
        assert "RUNNING HEADER" not in b.text


def test_body_text_present(blocks):
    body_text = " ".join(b.text for b in blocks if b.kind == "text")
    assert "twelve characters" in body_text
    assert "quarterly" in body_text
    assert "multi-factor authentication" in body_text


def test_summary_counts(blocks):
    s = parse_summary(blocks)
    assert s["n_blocks"] == s["n_headings"] + s["n_text"] + s["n_tables"]
    assert s["n_tables"] == 1
    assert s["n_headings"] >= 6
