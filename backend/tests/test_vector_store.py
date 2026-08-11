from scalm.vector_store.in_memory import InMemoryVectorStore, cosine_similarity
from scalm.domain.entities import CacheEntry


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
