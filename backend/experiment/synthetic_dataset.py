"""
Synthetic dataset generator for validating the three-way comparison
(GPTCache baseline vs. SCALM vs. Pareto) without needing real network
access to a dataset or embedding model.

Design mirrors the approach used earlier in this project's SCALM-only
validation: a fixed pool of topics with genuine paraphrase variants,
plus a controlled reuse rate. Extended here with volatility-tagged
topics (some STABLE, some TEMPORAL/PERSONAL-flavored) so the Pareto
extension's second objective actually has something to differentiate.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class SyntheticQAPair:
    query_text: str
    answer_text: str
    topic_id: int


# (query variants, is_volatile) -- volatile topics use temporal/personal
# phrasing that the volatility classifier should catch.
_TOPICS: list[tuple[list[str], bool]] = [
    (["what is the boiling point of water", "at what temperature does water boil"], False),
    (["explain how photosynthesis works", "can you explain the process of photosynthesis"], False),
    (["what is the capital of france", "which city is the capital of france"], False),
    (["describe the theory of relativity", "explain einstein's theory of relativity"], False),
    (["what is my schedule today", "what do i have planned for today"], True),
    (["what is happening in the news today", "what is today's news"], True),
    (["what is my favorite restaurant", "remind me of my favorite place to eat"], True),
    (["what should i cook tonight", "give me a dinner idea for tonight"], True),
]

_SYNTHETIC_VOCAB = [
    "volcano", "trumpet", "glacier", "bicycle", "lantern", "compass",
    "orchid", "falcon", "marble", "thunder", "velvet", "prairie",
    "obsidian", "harbor", "meadow", "citadel", "lagoon", "spindle",
]
_ANSWER_LENGTH_RANGE = (10, 200)


def generate_dataset(
    n_queries: int, reuse_rate: float = 0.15, seed: int = 42
) -> list[SyntheticQAPair]:
    if not 0.0 <= reuse_rate <= 1.0:
        raise ValueError("reuse_rate must be between 0 and 1")

    rng = random.Random(seed)
    topic_pool = list(range(len(_TOPICS)))
    used_topics: list[int] = []
    topic_answers: dict[int, str] = {}
    next_synthetic_id = len(_TOPICS)
    dataset: list[SyntheticQAPair] = []

    for _ in range(n_queries):
        reuse_this = used_topics and rng.random() < reuse_rate
        if reuse_this:
            topic_id = rng.choice(used_topics)
            variants = _TOPICS[topic_id][0] if topic_id < len(_TOPICS) else [
                f"synthetic query about {topic_id}"
            ]
        elif topic_pool:
            topic_id = topic_pool.pop(rng.randrange(len(topic_pool)))
            used_topics.append(topic_id)
            variants = _TOPICS[topic_id][0]
        else:
            topic_id = next_synthetic_id
            next_synthetic_id += 1
            used_topics.append(topic_id)
            words = rng.sample(_SYNTHETIC_VOCAB, k=4)
            variants = [" ".join(words) + "?"]

        if topic_id not in topic_answers:
            length = rng.randint(*_ANSWER_LENGTH_RANGE)
            topic_answers[topic_id] = " ".join(["word"] * length)

        query_text = rng.choice(variants)
        dataset.append(
            SyntheticQAPair(query_text=query_text, answer_text=topic_answers[topic_id], topic_id=topic_id)
        )

    return dataset
