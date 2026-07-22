"""
tests/test_knowledge_base.py — RAG civic knowledge base
-----------------------------------------------------------------------------
Covers the retrieval layer in tools/knowledge.py without any live embedding API calls:
- corpus is well-formed (every chunk has the fields the retriever and citations rely on),
- cosine similarity math is correct,
- retrieve()/search_knowledge_base() rank, threshold, and format correctly, using a deterministic
  one-hot embedder injected in place of the real Gemini embeddings.
"""
import re
import pytest

import tools.knowledge as kb


# ── Corpus shape ──────────────────────────────────────────────────────────────

def test_corpus_nonempty_and_sized():
    assert kb.corpus_size() == len(kb.KNOWLEDGE_BASE)
    assert kb.corpus_size() >= 30  # enough breadth to be a credible KB, not a toy


def test_every_chunk_is_wellformed():
    seen_ids = set()
    url_re = re.compile(r"^https://[\w.-]+\.(gov\.sg|sg)/?", re.IGNORECASE)
    for doc in kb.KNOWLEDGE_BASE:
        for field in ("id", "title", "agency", "source_url", "text"):
            assert doc.get(field), f"chunk missing/empty '{field}': {doc.get('id')}"
        assert doc["id"] not in seen_ids, f"duplicate id: {doc['id']}"
        seen_ids.add(doc["id"])
        assert url_re.match(doc["source_url"]), f"non-official source_url: {doc['source_url']}"
        assert len(doc["text"]) >= 60, f"chunk text too thin to be useful: {doc['id']}"


def test_fingerprint_is_stable_and_text_sensitive():
    fp1 = kb._corpus_fingerprint()
    assert fp1 == kb._corpus_fingerprint()  # deterministic
    original = kb.KNOWLEDGE_BASE[0]["text"]
    kb.KNOWLEDGE_BASE[0]["text"] = original + " (edited)"
    try:
        assert kb._corpus_fingerprint() != fp1  # a text change invalidates the cache
    finally:
        kb.KNOWLEDGE_BASE[0]["text"] = original


# ── Cosine similarity ─────────────────────────────────────────────────────────

def test_cosine_identical_is_one():
    v = [0.2, 0.5, 0.9, 0.1]
    assert kb._cosine(v, v) == pytest.approx(1.0)


def test_cosine_orthogonal_is_zero():
    assert kb._cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_zero_vector_is_zero_not_error():
    assert kb._cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_cosine_orders_by_direction():
    q = [1.0, 0.0]
    near = [1.0, 0.2]
    far = [0.2, 1.0]
    assert kb._cosine(q, near) > kb._cosine(q, far)


# ── Retrieval with a deterministic (mocked) embedder ─────────────────────────

@pytest.fixture
def onehot_embedder(monkeypatch):
    """Replaces the Gemini embedder with deterministic one-hot vectors so retrieval ranking is
    exactly controllable: corpus chunk i -> e_i; a query 'IDX:i' -> e_i (so it matches chunk i and
    nothing else); any other query -> zero vector (matches nothing). Also disables the disk cache
    so the mock is always exercised."""
    text_to_index = {doc["text"]: i for i, doc in enumerate(kb.KNOWLEDGE_BASE)}
    n = len(kb.KNOWLEDGE_BASE)

    def fake_embed(texts, task_type):
        out = []
        for t in texts:
            vec = [0.0] * n
            if task_type == "RETRIEVAL_DOCUMENT":
                vec[text_to_index[t]] = 1.0
            elif task_type == "RETRIEVAL_QUERY" and t.startswith("IDX:"):
                vec[int(t.split(":", 1)[1])] = 1.0
            out.append(vec)
        return out

    monkeypatch.setattr(kb, "_embed", fake_embed)
    monkeypatch.setattr(kb, "_load_cached_vectors", lambda: None)
    monkeypatch.setattr(kb, "_save_cached_vectors", lambda vectors: None)
    monkeypatch.setattr(kb, "_corpus_vectors", None, raising=False)
    yield
    kb._corpus_vectors = None  # don't leak mock vectors into other tests


def test_retrieve_returns_the_targeted_chunk(onehot_embedder):
    target = 5
    hits = kb.retrieve(f"IDX:{target}", top_k=3)
    assert hits, "expected at least one hit"
    assert hits[0]["id"] == kb.KNOWLEDGE_BASE[target]["id"]
    assert hits[0]["score"] == pytest.approx(1.0)


def test_retrieve_filters_out_below_threshold(onehot_embedder):
    # A query that embeds to the zero vector matches nothing above min_score.
    assert kb.retrieve("no marker here", top_k=3) == []


def test_retrieve_empty_query_returns_empty(onehot_embedder):
    assert kb.retrieve("   ", top_k=3) == []


def test_search_knowledge_base_formats_sources(onehot_embedder):
    target = 3
    out = kb.search_knowledge_base(f"IDX:{target}")
    doc = kb.KNOWLEDGE_BASE[target]
    assert doc["title"] in out
    assert doc["source_url"] in out
    assert "cite these sources" in out.lower()


def test_search_knowledge_base_graceful_when_no_hits(onehot_embedder):
    out = kb.search_knowledge_base("nothing relevant")
    assert "No sufficiently relevant entry" in out


def test_retrieve_returns_empty_when_embeddings_unavailable(monkeypatch):
    # If the corpus can't be embedded (e.g. API down), retrieval degrades to empty, never raises.
    monkeypatch.setattr(kb, "ensure_corpus_embedded", lambda: False)
    assert kb.retrieve("IDX:1", top_k=3) == []
    assert "No sufficiently relevant entry" in kb.search_knowledge_base("IDX:1")
