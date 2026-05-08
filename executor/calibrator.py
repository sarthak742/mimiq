"""DPI-aware coordinate calibrator for Mimiq.

Detects the system's actual DPI scaling factor and applies it (plus an
optional vertical offset) to raw screen coordinates before they are fed
to PyAutoGUI.
"""

from __future__ import annotations

import logging
import platform
import threading
from ctypes import c_uint
from typing import Final


class Calibrator:
    """Single-point DPI / offset scaler for click coordinates."""

    def __init__(self) -> None:
        self._dpi_scale: float = 1.0
        self._y_offset: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calibrate(self) -> None:
        """Detect the system's DPI scale factor.

        On Windows this queries ``GetDpiForSystem()`` via *ctypes* and
        divides by the legacy 96 DPI baseline.  On other platforms (or
        when *ctypes* is unavailable) the scale defaults to ``1.0``.
        """
        scale = 1.0

        if platform.system() == "Windows":
            try:
                import ctypes

                user32 = ctypes.windll.user32
                # GetDpiForSystem returns UINT (0 on failure / unsupported)
                dpi: int = user32.GetDpiForSystem()
                if dpi > 0:
                    scale = dpi / 96.0
                    logging.info(
                        "Calibrator: detected DPI=%d → scale=%.2f", dpi, scale
                    )
                else:
                    logging.warning(
                        "Calibrator: GetDpiForSystem returned 0; falling back to 1.0"
                    )
            except Exception as exc:
                logging.warning(
                    "Calibrator: could not detect DPI via ctypes (%s); using 1.0", exc
                )
        else:
            logging.info(
                "Calibrator: non-Windows platform ('%s'); scale=1.0", platform.system()
            )

        self._dpi_scale = scale

    def scale_coordinates(self, x: int, y: int) -> tuple[int, int]:
        """Apply DPI scale and vertical offset to raw coordinates.

        Returns ``(int(x * _dpi_scale), int(y * _dpi_scale) + _y_offset)``.
        """
        scaled_x = int(x * self._dpi_scale)
        scaled_y = int(y * self._dpi_scale) + self._y_offset
        return (scaled_x, scaled_y)

    # ------------------------------------------------------------------
    # Property accessors (read-only from the outside)
    # ------------------------------------------------------------------

    @property
    def dpi_scale(self) -> float:
        return self._dpi_scale

    @property
    def y_offset(self) -> int:
        return self._y_offset

    @y_offset.setter
    def y_offset(self, value: int) -> None:
        self._y_offset = value


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_calibrator_lock: Final[threading.Lock] = threading.Lock()
_calibrator_instance: Calibrator | None = None


def get_calibrator() -> Calibrator:
    """Return the thread-safe singleton ``Calibrator``.

    The first call lazily initialises the instance and runs
    :meth:`Calibrator.calibrate` so downstream code never has to think
    about DPI detection order.
    """
    global _calibrator_instance  # noqa: PLW0603

    if _calibrator_instance is not None:
        return _calibrator_instance

    with _calibrator_lock:
        if _calibrator_instance is None:
            _calibrator_instance = Calibrator()
            _calibrator_instance.calibrate()
    return _calibrator_instance
