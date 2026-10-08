"""Decodes OCR output into Brazilian plates: old (LLLNNNN) or Mercosul (LLLNLNN)."""

from dataclasses import dataclass
from typing import Literal

import numpy as np

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIGITS = "0123456789"

# Allowed characters per position. Old and Mercosul plates differ only in the 5th one.
POSITION_CHARSETS = (LETTERS, LETTERS, LETTERS, DIGITS, LETTERS + DIGITS, DIGITS, DIGITS)

PlateFormat = Literal["old", "mercosul"]


@dataclass(frozen=True)
class BrazilianPlate:
    text: str
    format: PlateFormat
    confidence: float
    """Lowest probability among the chosen characters and the trailing padding slots."""


def decode(slot_probs: np.ndarray, alphabet: str, pad_char: str) -> BrazilianPlate:
    """Picks the most probable reading that fits a Brazilian plate format.

    `slot_probs` has shape (slots, len(alphabet)): one probability distribution per
    character slot, as produced by fast-plate-ocr models. Slots after the 7th must be
    padding, so their padding probability also counts towards the confidence.
    """
    chars: list[str] = []
    probs: list[float] = []
    for slot, charset in zip(slot_probs, POSITION_CHARSETS):
        char = max(charset, key=lambda candidate: slot[alphabet.index(candidate)])
        chars.append(char)
        probs.append(float(slot[alphabet.index(char)]))

    pad_probs = slot_probs[len(POSITION_CHARSETS) :, alphabet.index(pad_char)]
    text = "".join(chars)
    return BrazilianPlate(
        text=text,
        format="mercosul" if text[4] in LETTERS else "old",
        confidence=min(probs + pad_probs.tolist()),
    )
