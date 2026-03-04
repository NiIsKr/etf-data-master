"""
Test comparison logic for names and TERs.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.monitor import normalize_name, names_match, ters_match


def test_normalize_name():
    """Test name normalization."""
    assert normalize_name("  TEQ  ETF  ") == "TEQ ETF"
    assert normalize_name("TEQ\t\tETF") == "TEQ ETF"
    assert normalize_name("TEQ\nETF") == "TEQ ETF"
    assert normalize_name("   Multiple   Spaces   ") == "Multiple Spaces"


def test_names_match():
    """Test name comparison."""
    # Exact match
    assert names_match("TEQ ETF", "TEQ ETF")

    # Whitespace variations
    assert names_match("TEQ  ETF", "TEQ ETF")
    assert names_match("  TEQ ETF  ", "TEQ ETF")
    assert names_match("TEQ\tETF", "TEQ ETF")

    # Mismatches
    assert not names_match("TEQ ETF", "TEQ General AI ETF")
    assert not names_match("TEQ - ETF", "TEQ ETF")

    # Case sensitivity (strict mode - case matters)
    assert not names_match("TEQ ETF", "teq etf")


def test_ters_match():
    """Test TER comparison with rounding."""
    # Exact match
    assert ters_match(0.69, 0.69)

    # Rounding to 4 decimals
    assert ters_match(0.69, 0.6900)
    assert ters_match(0.6950, 0.6950)
    assert ters_match(0.694999, 0.6950)

    # Mismatches
    assert not ters_match(0.69, 0.70)
    assert not ters_match(0.6949, 0.6950)


def test_edge_cases():
    """Test edge cases."""
    # Empty strings
    assert names_match("", "")
    assert not names_match("TEQ", "")

    # Very close TERs
    assert ters_match(0.95000001, 0.95000002)  # Within rounding
    assert not ters_match(0.9500, 0.9501)  # Outside rounding


if __name__ == "__main__":
    test_normalize_name()
    test_names_match()
    test_ters_match()
    test_edge_cases()
    print("✅ All comparison tests passed!")
