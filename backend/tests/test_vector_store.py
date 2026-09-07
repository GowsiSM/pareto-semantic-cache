from backend.vector_store.in_memory import InMemoryVectorStore, cosine_similarity
from backend.domain.entities import CacheEntry

import pytest

faiss = pytest.importorskip("faiss")
from backend.vector_store.faiss_store import FAISSVectorStore


def make_entry(entry_id: str, embedding: list[float]) -> CacheEntry:
    return CacheEntry(
        entry_id=entry_id,
        query_text=f"query-{entry_id}",
        answer_text="answer",
        embedding=embedding,
        pattern_id=None,
        query_token_count=1,
        answer_token_count=1,
    )


def test_cosine_similarity_identical_vectors_is_one():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_cosine_similarity_orthogonal_vectors_is_zero():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_search_returns_most_similar_first():
    store = InMemoryVectorStore()
    store.add(make_entry("a", [1.0, 0.0]))
    store.add(make_entry("b", [0.0, 1.0]))
    store.add(make_entry("c", [0.9, 0.1]))

    results = store.search([1.0, 0.0], top_k=3)

    assert [entry.entry_id for entry, _ in results] == ["a", "c", "b"]


def test_remove_deletes_entry():
    store = InMemoryVectorStore()
    store.add(make_entry("a", [1.0, 0.0]))
    store.remove("a")
    assert store.size() == 0
    assert store.get("a") is None


# ---------------------------------------------------------------------------
# FAISSVectorStore regression tests
#
# The original implementation rebuilt the FAISS index on every remove(),
# which renumbered FAISS's internal positions 0..n-1 while _entries kept
# the old keys.  After any eviction, search() silently returned the WRONG
# entry (no error — data corruption).  These tests pin the fixed behavior:
# stable external IDs via IndexIDMap + native remove_ids.
# ---------------------------------------------------------------------------


def make_faiss_entry(entry_id: str, embedding: list[float]) -> CacheEntry:
    return CacheEntry(
        entry_id=entry_id,
        query_text=f"query-{entry_id}",
        answer_text="answer",
        embedding=embedding,
        pattern_id=None,
        query_token_count=1,
        answer_token_count=1,
    )


class TestFAISSVectorStore:
    def test_search_returns_most_similar_first(self):
        store = FAISSVectorStore(dimension=2)
        store.add(make_faiss_entry("a", [1.0, 0.0]))
        store.add(make_faiss_entry("b", [0.0, 1.0]))
        store.add(make_faiss_entry("c", [0.9, 0.1]))

        results = store.search([1.0, 0.0], top_k=3)

        assert [entry.entry_id for entry, _ in results] == ["a", "c", "b"]

    def test_search_after_remove_returns_correct_entry(self):
        """
        Regression test for the silent-corruption bug: after removing an
        entry (which triggers an index rebuild in the old code), searching
        for a remaining entry's vector must return THAT entry, not a
        mis-mapped one.
        """
        store = FAISSVectorStore(dimension=2)
        store.add(make_faiss_entry("A", [1.0, 0.0]))
        store.add(make_faiss_entry("B", [0.0, 1.0]))
        store.add(make_faiss_entry("C", [0.9, 0.1]))
        store.add(make_faiss_entry("D", [0.1, 0.9]))

        store.remove("B")  # triggers rebuild in the old buggy code

        # D's vector must still map to D.
        results = store.search([0.1, 0.9], top_k=1)
        assert results, "expected a result"
        assert results[0][0].entry_id == "D"

        # A's vector must still map to A.
        results = store.search([1.0, 0.0], top_k=1)
        assert results[0][0].entry_id == "A"

    def test_multiple_removes_keep_mapping_correct(self):
        store = FAISSVectorStore(dimension=2)
        store.add(make_faiss_entry("A", [1.0, 0.0]))
        store.add(make_faiss_entry("B", [0.0, 1.0]))
        store.add(make_faiss_entry("C", [0.9, 0.1]))
        store.add(make_faiss_entry("D", [0.1, 0.9]))

        store.remove("A")
        store.remove("B")

        results = store.search([0.9, 0.1], top_k=1)
        assert results[0][0].entry_id == "C"
        results = store.search([0.1, 0.9], top_k=1)
        assert results[0][0].entry_id == "D"
        assert store.size() == 2

    def test_remove_then_add_keeps_mapping_correct(self):
        """
        After a remove + add, the new entry must be searchable and old
        entries must still map correctly.
        """
        store = FAISSVectorStore(dimension=2)
        store.add(make_faiss_entry("A", [1.0, 0.0]))
        store.add(make_faiss_entry("B", [0.0, 1.0]))
        store.remove("A")
        store.add(make_faiss_entry("E", [0.5, 0.5]))

        results = store.search([0.5, 0.5], top_k=1)
        assert results[0][0].entry_id == "E"
        results = store.search([0.0, 1.0], top_k=1)
        assert results[0][0].entry_id == "B"

    def test_remove_nonexistent_is_noop(self):
        store = FAISSVectorStore(dimension=2)
        store.add(make_faiss_entry("A", [1.0, 0.0]))
        store.remove("does-not-exist")
        assert store.size() == 1
        results = store.search([1.0, 0.0], top_k=1)
        assert results[0][0].entry_id == "A"

    def test_remove_all_entries(self):
        store = FAISSVectorStore(dimension=2)
        store.add(make_faiss_entry("A", [1.0, 0.0]))
        store.add(make_faiss_entry("B", [0.0, 1.0]))
        store.remove("A")
        store.remove("B")
        assert store.size() == 0
        assert store.search([1.0, 0.0], top_k=1) == []

    def test_get_and_all_entries_after_remove(self):
        store = FAISSVectorStore(dimension=2)
        store.add(make_faiss_entry("A", [1.0, 0.0]))
        store.add(make_faiss_entry("B", [0.0, 1.0]))
        store.remove("A")

        assert store.get("A") is None
        assert store.get("B") is not None
        assert [e.entry_id for e in store.all_entries()] == ["B"]
