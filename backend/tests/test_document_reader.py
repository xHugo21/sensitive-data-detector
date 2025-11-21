import os

from app.services import document_reader


def test_sanitize_file_path_decodes_file_uri():
    raw = "file:///tmp/some%20folder/some%20file.txt"
    sanitized = document_reader.sanitize_file_path(raw)
    assert sanitized.endswith("some file.txt")
    if os.name != "nt":
        assert sanitized == "/tmp/some folder/some file.txt"


def test_read_document_returns_none_for_missing_file(tmp_path):
    missing_path = tmp_path / "missing.txt"
    assert document_reader.read_document(str(missing_path)) is None


def test_read_document_reads_plain_text_file(tmp_path):
    file_path = tmp_path / "doc.txt"
    file_path.write_text("line one\nline two", encoding="utf-8")
    assert document_reader.read_document(str(file_path)) == "line one\nline two"


def test_read_document_uses_pdfplumber_for_pdfs(monkeypatch, tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"%PDF-FAKE")

    class FakePage:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class FakePdf:
        def __init__(self):
            self.pages = [
                FakePage("First page"),
                FakePage(None),
                FakePage("Second page"),
            ]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_open(path):
        assert path == str(pdf_path)
        return FakePdf()

    monkeypatch.setattr(document_reader.pdfplumber, "open", fake_open)

    content = document_reader.read_document(str(pdf_path))
    assert content == "First page\nSecond page"
