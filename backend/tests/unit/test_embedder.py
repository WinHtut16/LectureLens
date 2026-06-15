"""Unit tests for app.ml.embedder — real SentenceTransformer never loaded."""

import numpy as np

from app.ml.embedder import MockEmbedder


def test_embed_shape():
    emb = MockEmbedder()
    result = emb.embed(["hello", "world", "foo"])
    assert result.shape == (3, 384)


def test_embed_dtype_float32():
    emb = MockEmbedder()
    assert emb.embed(["test"]).dtype == np.float32


def test_embed_one_shape():
    emb = MockEmbedder()
    assert emb.embed_one("single").shape == (384,)


def test_embed_one_matches_first_row_of_embed():
    emb = MockEmbedder()
    text = "compare"
    np.testing.assert_array_equal(emb.embed_one(text), emb.embed([text])[0])


def test_embed_is_l2_normalised():
    emb = MockEmbedder()
    vecs = emb.embed(["a", "b", "c"])
    norms = np.linalg.norm(vecs, axis=1)
    np.testing.assert_allclose(norms, np.ones(3), atol=1e-6)


def test_embed_one_is_l2_normalised():
    emb = MockEmbedder()
    vec = emb.embed_one("unit check")
    assert abs(float(np.linalg.norm(vec)) - 1.0) < 1e-6


def test_embed_empty_list():
    emb = MockEmbedder()
    result = emb.embed([])
    assert result.shape == (0, 384)
    assert result.dtype == np.float32
