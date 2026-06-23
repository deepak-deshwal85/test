import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rag.ingest import chunk_text, load_documents


def test_chunk_text_splits_long_resume_text():
    text = " ".join(["experience"] * 200)
    chunks = chunk_text(text, max_chars=100, overlap=20)
    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)


def test_load_documents_reads_txt_files(tmp_path: Path):
    resume = tmp_path / "resume.txt"
    resume.write_text("Deepak Kumar\nPython engineer", encoding="utf-8")
    documents = load_documents(resume)
    assert len(documents) == 1
    assert "Deepak Kumar" in documents[0].text


def test_load_documents_raises_for_missing_path(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_documents(tmp_path / "missing")
