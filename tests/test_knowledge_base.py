"""
tests/test_knowledge_base.py — RAG civic knowledge base
-----------------------------------------------------------------------------
Covers the retrieval layer in tools/knowledge.py without any live embedding API calls:
- corpus is well-formed (every chunk has the fields the retriever and citations rely on),
- cosine similarity math is correct,
- retrieve()/search_knowledge_base() rank, threshold, and format correctly, using a deterministic
  one-hot embedder injected in place of the real Gemini embeddings.
"""
import os
import re
import pytest

import tools.knowledge as kb


# ── Corpus shape ──────────────────────────────────────────────────────────────

def test_corpus_nonempty_and_sized():
    assert kb.corpus_size() == len(kb.KNOWLEDGE_BASE)
    assert kb.corpus_size() >= 100  # broad enough to cover the top citizen intents, not a toy


def test_corpus_covers_the_major_agencies():
    # A credible civic KB must span the agencies citizens actually deal with, not cluster on one.
    agencies = " ".join(d["agency"] for d in kb.KNOWLEDGE_BASE).upper()
    for token in ("CPF", "IRAS", "HDB", "MOM", "MOH", "MOE", "LTA", "ICA", "NEA"):
        assert token in agencies, f"corpus has no chunk from {token}"


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


# ── Retrieval QUALITY: measured against the real Gemini embedder ──────────────
# The tests above prove the plumbing (ranking, thresholding, formatting) with a mock embedder.
# This one measures whether the *actual* embeddings put the right chunk near the top for
# natural-language citizen questions — the metric that matters for grounding. It calls the live
# embedding API, so it self-skips when no key is configured (e.g. CI), keeping the suite green
# while giving a real, repeatable quality number locally and in any keyed environment.

# Natural-language question → the corpus id that should answer it. Phrasings deliberately avoid
# copying the chunk text so this measures semantic retrieval, not lexical overlap.
GOLDEN_QUERIES = [
    ("how do the CPF LIFE monthly payouts work after I retire", "cpf-life"),
    ("what's the difference between a BTO flat and a resale flat", "hdb-bto-vs-resale"),
    ("do I need to file an income tax return this year", "iras-who-files"),
    ("extra stamp duty when buying my second property", "iras-absd"),
    ("how many years must I live in my HDB flat before selling it", "hdb-mop"),
    ("can I pay my child's university tuition from CPF", "cpf-education-scheme"),
    ("what is the Assurance Package payout", "assurance-package"),
    ("how do I register my marriage in Singapore", "rom-marriage"),
    ("are there rebates for buying an electric car", "lta-ev-incentives"),
    ("what does a Certificate of Entitlement mean for car ownership", "lta-coe"),
    ("how does the GST Voucher scheme help lower income families", "gst-voucher"),
    ("long term care insurance if I become severely disabled", "careshield-life"),
    ("how can I apply to become a permanent resident", "ica-pr-application"),
    ("what is a Notice of Assessment from the tax office", "iras-noa"),
    ("rules for riding e-scooters and personal mobility devices", "lta-active-mobility"),
    ("using my SkillsFuture credit to pay for a course", "skillsfuture"),
    ("how do I stop mosquitoes breeding and prevent dengue", "nea-dengue"),
    ("small dispute over a faulty product, which tribunal", "small-claims"),
    ("digital identity a company uses to file with the government", "corppass"),
    ("cash help for elderly with low income and little family support", "silver-support"),
]

_HAS_EMBED_KEY = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


@pytest.mark.skipif(not _HAS_EMBED_KEY, reason="no Gemini API key — live retrieval-quality test skipped")
def test_retrieval_quality_meets_threshold(capsys):
    """Measures top-1 accuracy and recall@3 of the real embedder over the golden set, and asserts
    the KB clears a quality bar. Thresholds are set below observed performance with headroom for
    normal embedding variance, so this catches real regressions (a bad chunk edit, a corpus split
    that strands an intent) without being flaky."""
    if not kb.ensure_corpus_embedded():
        pytest.skip("embedding API unavailable at runtime")

    top1_hits = 0
    recall3_hits = 0
    misses = []
    for query, expected_id in GOLDEN_QUERIES:
        hits = kb.retrieve(query, top_k=5, min_score=0.0)
        ranked_ids = [h["id"] for h in hits]
        if ranked_ids[:1] == [expected_id]:
            top1_hits += 1
        if expected_id in ranked_ids[:3]:
            recall3_hits += 1
        else:
            misses.append((query, expected_id, ranked_ids[:3]))

    n = len(GOLDEN_QUERIES)
    top1 = top1_hits / n
    recall3 = recall3_hits / n
    with capsys.disabled():
        print(f"\n[kb quality] top-1 accuracy: {top1:.0%}  |  recall@3: {recall3:.0%}  (n={n})")
        for q, want, got in misses:
            print(f"  MISS: {q!r} -> wanted {want}, top3={got}")

    assert recall3 >= 0.80, f"recall@3 {recall3:.0%} below 80% — retrieval quality regressed"
    assert top1 >= 0.55, f"top-1 accuracy {top1:.0%} below 55% — ranking quality regressed"
