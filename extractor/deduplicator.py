"""Frame deduplication via Mean Squared Error thresholding.

Uses OpenCV to load extracted frames and NumPy to compute the per-pixel
MSE between adjacent candidates.  Nearly-identical frames (e.g. two
consecutive screenshots of a loading spinner) are deleted so only
meaningful UI-state changes are forwarded to the vision model.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np


def calculate_mse(image_a: np.ndarray, image_b: np.ndarray) -> float:
    """Return the Mean Squared Error between two identically-shaped images.

    The arrays are cast to ``float32`` before subtraction to avoid
    uint8 wrap-around overflow.
    """
    if image_a.shape != image_b.shape:
        raise ValueError(
            f"Shape mismatch: {image_a.shape} vs {image_b.shape}"
        )

    a = image_a.astype(np.float32)
    b = image_b.astype(np.float32)

    mse = np.mean((a - b) ** 2)
    return float(mse)


class Deduplicator:
    """Stateful deduplicator that walks a list of frame paths and prunes
    visually-identical neighbours.
    """

    def filter_duplicates(
        self,
        frame_paths: list[Path],
        threshold: float = 150.0,
    ) -> list[Path]:
        """Return the subset of *frame_paths* that differ from the last
        kept frame by at least *threshold* MSE.

        Frames whose MSE is **below** *threshold* are considered duplicates
        and are deleted from disk via ``path.unlink()``.
        """
        if not frame_paths:
            return []

        sorted_paths = sorted(frame_paths)
        survivors: list[Path] = []
        last_kept_image: np.ndarray | None = None

        for path in sorted_paths:
            image = cv2.imread(str(path))
            if image is None:
                logging.warning(
                    "[deduplicator] Could not read %s; skipping.", path
                )
                continue

            # First frame is always kept
            if last_kept_image is None:
                survivors.append(path)
                last_kept_image = image
                continue

            try:
                mse = calculate_mse(last_kept_image, image)
            except ValueError:
                # Shape mismatch — keep both to be safe
                survivors.append(path)
                last_kept_image = image
                continue

            if mse < threshold:
                # Too similar → duplicate; delete and skip
                logging.info(
                    "[deduplicator] MSE %.1f < %.1f — deleting duplicate %s",
                    mse,
                    threshold,
                    path,
                )
                try:
                    path.unlink()
                except OSError as exc:
                    logging.warning(
                        "[deduplicator] Failed to delete %s: %s", path, exc
                    )
            else:
                # Sufficient visual change → keep
                logging.info(
                    "[deduplicator] MSE %.1f >= %.1f — keeping %s",
                    mse,
                    threshold,
                    path,
                )
                survivors.append(path)
                last_kept_image = image

        logging.info(
            "[deduplicator] %d frame(s) survived deduplication.", len(survivors)
        )
        return survivors
