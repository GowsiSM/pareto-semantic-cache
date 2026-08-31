from backend.clustering.dbscan_clustering import DBSCANRoundClustering
from backend.embedding.mock_embedding import MockEmbeddingProvider


def test_similar_queries_land_in_same_pattern():
    embedder = MockEmbeddingProvider()  # default 512 dims — see mock_embedding.py note
    texts = [
        "How can AI help in the field of healthcare?",
        "How can AI technology be used in the healthcare industry?",
        "What is the weather like in Tokyo today?",
    ]
    embeddings = embedder.embed_batch(texts)
    entry_ids = ["q1", "q2", "q3"]

    clustering = DBSCANRoundClustering(eps=0.6, min_samples=2)
    patterns = clustering.cluster_round(round_index=1, embeddings=embeddings, entry_ids=entry_ids)

    # The two healthcare queries should end up together in some pattern;
    # the unrelated weather query should not share that pattern.
    healthcare_pattern = next(p for p in patterns if "q1" in p.member_entry_ids)
    assert "q2" in healthcare_pattern.member_entry_ids
    assert "q3" not in healthcare_pattern.member_entry_ids


def test_empty_input_returns_no_patterns():
    clustering = DBSCANRoundClustering()
    assert clustering.cluster_round(1, [], []) == []


def test_mismatched_lengths_raises():
    clustering = DBSCANRoundClustering()
    try:
        clustering.cluster_round(1, [[0.1, 0.2]], ["a", "b"])
        assert False, "expected ValueError"
    except ValueError:
        pass
