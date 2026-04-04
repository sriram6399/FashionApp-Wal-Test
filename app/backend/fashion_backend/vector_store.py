"""Chroma persistent vector index for semantic image search."""

from __future__ import annotations

import asyncio
from functools import lru_cache
import chromadb


@lru_cache
def _persistent_client() -> chromadb.PersistentClient:
    from fashion_backend.config import settings

    path = settings.data_dir / "chroma"
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path))


@lru_cache
def _collection():
    return _persistent_client().get_or_create_collection(
        name="inspiration",
        metadata={"hnsw:space": "cosine"},
    )


def _upsert_sync(image_id: int, document: str, embedding: list[float]) -> None:
    sid = str(image_id)
    _collection().upsert(
        ids=[sid],
        embeddings=[embedding],
        documents=[document],
        metadatas=[{"image_id": image_id}],
    )


def _delete_sync(image_id: int) -> None:
    try:
        _collection().delete(ids=[str(image_id)])
    except Exception:
        pass


def _query_sync(query_embedding: list[float], top_k: int) -> list[tuple[int, float]]:
    col = _collection()
    n = max(1, min(top_k, 200))
    r = col.query(
        query_embeddings=[query_embedding],
        n_results=n,
        include=["distances"],
    )
    ids_batch = r.get("ids") or []
    dist_batch = r.get("distances") or []
    if not ids_batch or not ids_batch[0]:
        return []
    out: list[tuple[int, float]] = []
    dists = dist_batch[0] if dist_batch else []
    for sid, dist in zip(ids_batch[0], dists):
        try:
            out.append((int(sid), float(dist)))
        except (TypeError, ValueError):
            continue
    return out


async def upsert_image_vector(image_id: int, document: str, embedding: list[float]) -> None:
    await asyncio.to_thread(_upsert_sync, image_id, document, embedding)


async def delete_image_vector(image_id: int) -> None:
    await asyncio.to_thread(_delete_sync, image_id)


async def query_similar(query_embedding: list[float], top_k: int = 80) -> list[tuple[int, float]]:
    return await asyncio.to_thread(_query_sync, query_embedding, top_k)


def clear_cache() -> None:
    """Test helper: reset cached clients."""
    _collection.cache_clear()
    _persistent_client.cache_clear()
