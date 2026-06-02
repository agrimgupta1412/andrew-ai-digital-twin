from src.chunking import chunk_pages, chunk_text
from src.document_loader import DocumentPage


def test_chunks_are_created_and_not_empty():
    text = "Machine learning benefits from iteration. " * 200
    chunks = chunk_text(text, chunk_size=1000, chunk_overlap=100, min_chunk_size=200)
    assert chunks
    assert all(chunk.strip() for chunk in chunks)


def test_chunks_preserve_metadata():
    source = {
        "id": "test-source",
        "title": "Test Source",
        "type": "lecture_notes",
        "url": "https://example.com",
        "domain": "machine_learning",
    }
    chunks = chunk_pages(source, [DocumentPage("Gradient descent is useful. " * 100, 7)], chunk_size=900, chunk_overlap=100)
    assert chunks
    metadata = chunks[0].metadata
    assert metadata["source_id"] == "test-source"
    assert metadata["source_title"] == "Test Source"
    assert metadata["page"] == 7
    assert metadata["chunk_id"].startswith("test-source-p7")


def test_chunks_respect_overlap():
    text = "".join(str(index % 10) for index in range(3000))
    chunks = chunk_text(text, chunk_size=1000, chunk_overlap=120, min_chunk_size=200)
    assert len(chunks) > 1
    assert chunks[0][-80:] == chunks[1][:80]

