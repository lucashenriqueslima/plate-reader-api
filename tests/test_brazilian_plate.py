import numpy as np
import pytest

from plate_reader_api.brazilian_plate import decode

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_"
PAD_CHAR = "_"
SLOTS = 10


def slot_probs_for(text: str) -> np.ndarray:
    """One-hot OCR output for `text`, padded to the model's slot count."""
    probs = np.zeros((SLOTS, len(ALPHABET)))
    for slot, char in enumerate(text.ljust(SLOTS, PAD_CHAR)):
        probs[slot, ALPHABET.index(char)] = 1.0
    return probs


def set_slot(probs: np.ndarray, slot: int, char_probs: dict[str, float]) -> None:
    probs[slot] = 0.0
    for char, prob in char_probs.items():
        probs[slot, ALPHABET.index(char)] = prob


def test_reads_mercosul_plate():
    plate = decode(slot_probs_for("BRA2E19"), ALPHABET, PAD_CHAR)

    assert plate.text == "BRA2E19"
    assert plate.format == "mercosul"
    assert plate.confidence == pytest.approx(1.0)


def test_reads_old_plate():
    plate = decode(slot_probs_for("ABC1234"), ALPHABET, PAD_CHAR)

    assert plate.text == "ABC1234"
    assert plate.format == "old"


def test_letter_position_never_returns_a_digit():
    probs = slot_probs_for("OBC1D23")
    set_slot(probs, 0, {"0": 0.6, "O": 0.3, "Q": 0.1})

    plate = decode(probs, ALPHABET, PAD_CHAR)

    assert plate.text == "OBC1D23"
    assert plate.confidence == pytest.approx(0.3)


def test_digit_position_never_returns_a_letter():
    probs = slot_probs_for("ABC8D23")
    set_slot(probs, 3, {"B": 0.6, "8": 0.4})

    plate = decode(probs, ALPHABET, PAD_CHAR)

    assert plate.text == "ABC8D23"


def test_fifth_position_accepts_letter_or_digit():
    probs = slot_probs_for("ABC1D23")
    set_slot(probs, 4, {"0": 0.7, "D": 0.3})

    plate = decode(probs, ALPHABET, PAD_CHAR)

    assert plate.text == "ABC1023"
    assert plate.format == "old"


def test_extra_character_lowers_confidence():
    probs = slot_probs_for("ABC1D234")
    set_slot(probs, 7, {"4": 0.95, PAD_CHAR: 0.05})

    plate = decode(probs, ALPHABET, PAD_CHAR)

    assert plate.confidence == pytest.approx(0.05)
