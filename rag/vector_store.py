import hashlib
import math
import re

import faiss
import numpy as np


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+")
VECTOR_SIZE = 512


class LocalFaissStore:
    def __init__(self, documents, vectors):
        self.documents = documents
        self.index = faiss.IndexFlatIP(VECTOR_SIZE)
        self.index.add(vectors)


def _tokenize(text):
    return TOKEN_PATTERN.findall(text.lower())


def _hash_token(token):
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "little")


def _embed_text(text):
    vector = np.zeros(VECTOR_SIZE, dtype="float32")
    for token in _tokenize(text):
        hashed = _hash_token(token)
        index = hashed % VECTOR_SIZE
        sign = 1.0 if (hashed >> 9) & 1 else -1.0
        vector[index] += sign

    norm = math.sqrt(float(np.dot(vector, vector)))
    if norm:
        vector /= norm
    return vector


def build_vector_store(documents):
    vectors = np.vstack([_embed_text(doc.page_content) for doc in documents]).astype("float32")
    return LocalFaissStore(documents, vectors)


def retrieve_relevant_docs(vector_store, query, k=4):
    query_vector = _embed_text(query).reshape(1, -1)
    scores, indices = vector_store.index.search(query_vector, min(k, len(vector_store.documents)))

    docs = []
    confidence = 0.0
    for score, index in zip(scores[0], indices[0]):
        if index < 0:
            continue
        confidence = max(confidence, float(score))
        if score > 0:
            docs.append(vector_store.documents[int(index)])

    return docs, confidence
