"""Exact and near-duplicate detection for silver documents."""

from __future__ import annotations

import hashlib
import re
import zlib
from collections import defaultdict
from collections.abc import Iterable

from .config import DedupConfig
from .models import DuplicateGroup, QualityFlag, SilverDocument

_MASK = 0xFFFFFFFF
_PRIME = 4_294_967_291
_WORD = re.compile(r"[a-z0-9áéíóúüñ]+", re.IGNORECASE)


def normalize_for_hash(text: str) -> str:
    words = _WORD.findall(text.lower())
    return " ".join(words)


def text_fingerprint(text: str) -> str:
    return hashlib.sha256(normalize_for_hash(text).encode()).hexdigest()


def _shingles(text: str, size: int) -> set[int]:
    words = _WORD.findall(text.lower())
    if len(words) < size:
        return {zlib.crc32(" ".join(words).encode())} if words else set()
    return {
        zlib.crc32(" ".join(words[index : index + size]).encode())
        for index in range(len(words) - size + 1)
    }


def _params(num_perm: int) -> list[tuple[int, int]]:
    params: list[tuple[int, int]] = []
    for index in range(num_perm):
        seed = f"silver-minhash-{index}".encode()
        digest = hashlib.blake2b(seed, digest_size=8).digest()
        a = int.from_bytes(digest[:4], "big") | 1
        b = int.from_bytes(digest[4:], "big")
        params.append((a, b))
    return params


def minhash_signature(shingles: set[int], params: list[tuple[int, int]]) -> tuple[int, ...]:
    if not shingles:
        return tuple(0 for _ in params)
    return tuple(min(((a * value + b) & _MASK) for value in shingles) for a, b in params)


def jaccard(left: set[int], right: set[int]) -> float:
    if not left or not right:
        return 0.0
    intersection = len(left & right)
    union = len(left | right)
    return intersection / union if union else 0.0


def _candidate_pairs(signatures: dict[str, tuple[int, ...]], bands: int) -> set[tuple[str, str]]:
    rows = len(next(iter(signatures.values()))) // bands if signatures else 0
    if rows == 0:
        return set()
    buckets: dict[tuple[int, tuple[int, ...]], list[str]] = defaultdict(list)
    for doc_id, signature in signatures.items():
        for band in range(bands):
            start = band * rows
            buckets[(band, signature[start : start + rows])].append(doc_id)
    pairs: set[tuple[str, str]] = set()
    for members in buckets.values():
        if len(members) < 2:
            continue
        members.sort()
        for index, left in enumerate(members):
            for right in members[index + 1 :]:
                pairs.add((left, right))
    return pairs


class _UnionFind:
    def __init__(self, items: Iterable[str]) -> None:
        self.parent = {item: item for item in items}

    def find(self, item: str) -> str:
        root = item
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[item] != item:
            self.parent[item], item = root, self.parent[item]
        return root

    def union(self, left: str, right: str) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def _authority_rank(authority: str) -> int:
    return {"first_party": 0, "open_data": 1, "third_party": 2}.get(authority, 3)


def _choose_canonical(members: list[SilverDocument]) -> SilverDocument:
    return sorted(
        members,
        key=lambda document: (
            _authority_rank(document.authority),
            -document.version,
            _date_key(document.retrieved_at),
            -len(document.text),
            document.doc_id,
        ),
    )[0]


def _date_key(value: str) -> float:
    from datetime import datetime

    try:
        return -datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _reason(members: list[SilverDocument], *, kind: str) -> str:
    urls = {document.url_canonical for document in members}
    if len(urls) == 1:
        return "same_url_newer"
    if kind == "exact":
        return "same_text"
    authorities = {document.authority for document in members}
    if len(authorities) > 1:
        return "official_preferred"
    return "longer_text"


def deduplicate(
    documents: list[SilverDocument],
    *,
    config: DedupConfig,
) -> tuple[dict[str, str], list[DuplicateGroup]]:
    """Return ``alias -> canonical`` mapping and the duplicate groups."""
    if len(documents) < 2:
        return {}, []
    by_id = {document.doc_id: document for document in documents}
    union = _UnionFind(by_id)
    fingerprints = {document.doc_id: text_fingerprint(document.text) for document in documents}

    exact_groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for document in documents:
        exact_groups[(document.language, fingerprints[document.doc_id])].append(document.doc_id)
    for members in exact_groups.values():
        for member in members[1:]:
            union.union(members[0], member)

    by_url: dict[str, list[str]] = defaultdict(list)
    for document in documents:
        by_url[document.url_canonical].append(document.doc_id)
    for members in by_url.values():
        for member in members[1:]:
            union.union(members[0], member)

    shingles = {
        document.doc_id: _shingles(document.text, config.shingle_size) for document in documents
    }
    params = _params(config.num_perm)
    signatures = {doc_id: minhash_signature(values, params) for doc_id, values in shingles.items()}
    for left, right in _candidate_pairs(signatures, config.bands):
        if by_id[left].language != by_id[right].language:
            continue
        if union.find(left) == union.find(right):
            continue
        if jaccard(shingles[left], shingles[right]) >= config.near_threshold:
            union.union(left, right)

    clusters: dict[str, list[str]] = defaultdict(list)
    for document in documents:
        clusters[union.find(document.doc_id)].append(document.doc_id)

    alias_map: dict[str, str] = {}
    groups: list[DuplicateGroup] = []
    for members in clusters.values():
        if len(members) < 2:
            continue
        member_docs = [by_id[member] for member in members]
        fingerprint_set = {fingerprints[member] for member in members}
        kind = "exact" if len(fingerprint_set) == 1 else "near"
        canonical = _choose_canonical(member_docs)
        aliases = sorted(member for member in members if member != canonical.doc_id)
        group = DuplicateGroup(
            group_id="dup_" + hashlib.sha256(",".join(sorted(members)).encode()).hexdigest()[:16],
            kind=kind,
            canonical_doc_id=canonical.doc_id,
            members=sorted(members),
            similarity=_average_similarity(member_docs, shingles) if kind == "near" else 1.0,
            reason=_reason(member_docs, kind=kind),
        )
        groups.append(group)
        canonical.status = "canonical"
        canonical.canonical_doc_id = None
        canonical.duplicate_of = None
        canonical.aliases = aliases
        for alias in aliases:
            alias_doc = by_id[alias]
            alias_doc.status = "alias"
            alias_doc.canonical_doc_id = canonical.doc_id
            alias_doc.duplicate_of = canonical.doc_id
            alias_doc.aliases = []
            flag = (
                QualityFlag.EXACT_DUPLICATE.value
                if kind == "exact"
                else QualityFlag.NEAR_DUPLICATE.value
            )
            if flag not in alias_doc.quality_flags:
                alias_doc.quality_flags.append(flag)
            alias_map[alias] = canonical.doc_id
    return alias_map, groups


def _average_similarity(documents: list[SilverDocument], shingles: dict[str, set[int]]) -> float:
    values: list[float] = []
    for index, left in enumerate(documents):
        for right in documents[index + 1 :]:
            values.append(jaccard(shingles[left.doc_id], shingles[right.doc_id]))
    return round(sum(values) / len(values), 4) if values else 0.0
