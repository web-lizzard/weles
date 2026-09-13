from domain.capture.value_objects import Embedding, SimilarityScore


def cosine_similarity(left: Embedding, right: Embedding) -> SimilarityScore:
    _ = (left, right)
    raise NotImplementedError
