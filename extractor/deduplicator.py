"""Frame deduplication via perceptual hashing (average hash).

Uses PIL to resize, grayscale, and hash extracted frames.  Nearly-identical
frames (e.g. two consecutive screenshots of a loading spinner) are deleted
so only meaningful UI-state changes are forwarded to the vision model.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image


def _average_hash(image: Image.Image, hash_size: int = 8) -> int:
    """Return an integer average-hash (aHash) for *image*."""
    gray = image.convert("L").resize(
        (hash_size, hash_size), Image.Resampling.LANCZOS
    )
    pixels = list(gray.getdata())
    avg = sum(pixels) / len(pixels)
    bits = "".join("1" if p > avg else "0" for p in pixels)
    return int(bits, 2)


def _hamming_distance(hash_a: int, hash_b: int) -> int:
    """Return the number of differing bits between two integer hashes."""
    x = hash_a ^ hash_b
    distance = 0
    while x:
        distance += 1
        x &= x - 1
    return distance


class Deduplicator:
    """Stateful deduplicator that walks a list of frame paths and prunes
    visually-identical neighbours using perceptual hashing.
    """

    def __init__(self, hash_size: int = 8) -> None:
        self.hash_size = hash_size

    def filter_duplicates(
        self,
        frame_paths: list[Path],
        threshold: int = 5,
    ) -> list[Path]:
        """Return the subset of *frame_paths* that differ from the last
        kept frame by at least *threshold* hamming distance.

        Frames whose hamming distance is **below** *threshold* are
        considered duplicates and are deleted from disk via ``path.unlink()``.
        """
        if not frame_paths:
            return []

        sorted_paths = sorted(frame_paths)
        survivors: list[Path] = []
        last_hash: int | None = None

        for path in sorted_paths:
            try:
                with Image.open(path) as img:
                    h = _average_hash(img, self.hash_size)
            except Exception as exc:
                logging.warning(
                    "[deduplicator] Could not read %s: %s", path, exc
                )
                continue

            if last_hash is None:
                survivors.append(path)
                last_hash = h
                continue

            distance = _hamming_distance(last_hash, h)

            if distance < threshold:
                logging.info(
                    "[deduplicator] Hamming distance %d < %d — "
                    "deleting duplicate %s",
                    distance,
                    threshold,
                    path,
                )
                try:
                    path.unlink()
                except OSError as del_exc:
                    logging.warning(
                        "[deduplicator] Failed to delete %s: %s",
                        path,
                        del_exc,
                    )
            else:
                logging.info(
                    "[deduplicator] Hamming distance %d >= %d — keeping %s",
                    distance,
                    threshold,
                    path,
                )
                survivors.append(path)
                last_hash = h

        logging.info(
            "[deduplicator] %d frame(s) survived deduplication.",
            len(survivors),
        )
        return survivors


def deduplicate(frame_paths: list[Path], threshold: int = 5) -> list[Path]:
    """Standalone wrapper around :class:`Deduplicator` for easier importing."""
    d = Deduplicator()
    return d.filter_duplicates(frame_paths, threshold=threshold)
