"""
Test TER extraction regex on sample strings.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.extract_web import extract_ter_from_html


def test_ter_extraction():
    """Test TER regex on various HTML samples."""
    # Test case 1: Standard format
    html1 = """
    <div>
        <span>TER: 0.95%</span>
    </div>
    """
    ter1, evidence1 = extract_ter_from_html(html1, "test")
    assert ter1 == 0.95, f"Expected 0.95, got {ter1}"
    assert "0.95" in evidence1

    # Test case 2: German format with comma
    html2 = """
    <p>Laufende Kosten: 0,69 % p.a.</p>
    """
    ter2, evidence2 = extract_ter_from_html(html2, "test")
    assert ter2 == 0.69, f"Expected 0.69, got {ter2}"

    # Test case 3: Total Expense Ratio
    html3 = """
    <div>Total Expense Ratio: 1.20%</div>
    """
    ter3, evidence3 = extract_ter_from_html(html3, "test")
    assert ter3 == 1.20, f"Expected 1.20, got {ter3}"

    # Test case 4: Basis points
    html4 = """
    <span>TER: 95 bps</span>
    """
    ter4, evidence4 = extract_ter_from_html(html4, "test")
    assert ter4 == 0.95, f"Expected 0.95, got {ter4}"

    # Test case 5: Gesamtkostenquote
    html5 = """
    <td>Gesamtkostenquote</td><td>0,45%</td>
    """
    ter5, evidence5 = extract_ter_from_html(html5, "test")
    assert ter5 == 0.45, f"Expected 0.45, got {ter5}"

    # Test case 6: No TER found
    html6 = """
    <p>This is a page without TER information</p>
    """
    ter6, evidence6 = extract_ter_from_html(html6, "test")
    assert ter6 is None, f"Expected None, got {ter6}"

    # Test case 7: Multiple percentages (should take first near keyword)
    html7 = """
    <div>
        <p>Performance: 10.5%</p>
        <p>TER: 0.75%</p>
        <p>Volatility: 15.2%</p>
    </div>
    """
    ter7, evidence7 = extract_ter_from_html(html7, "test")
    assert ter7 == 0.75, f"Expected 0.75, got {ter7}"


if __name__ == "__main__":
    test_ter_extraction()
    print("✅ All extraction tests passed!")
