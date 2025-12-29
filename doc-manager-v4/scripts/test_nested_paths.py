import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from utils import PathManager

def test_nested_paths():
    shadow_root = "/tmp/shadow_test"
    pm = PathManager(shadow_root)
    
    category = "Personal"
    original_path = "01_Sources/Personal/Journal/2025/entry.md"
    
    l1_path = pm.get_l1_path(category, original_path)
    print(f"Original: {original_path}")
    print(f"L1 Path:  {l1_path}")
    
    expected = os.path.join(shadow_root, "L1", "Personal", "Journal", "2025", "[L1] entry.md")
    if l1_path == expected:
        print("SUCCESS: L1 Path matches expectation.")
    else:
        print(f"FAIL: Expected {expected}")

    review_path = pm.get_l1_review_path(category, l1_path)
    print(f"Review:   {review_path}")
    expected_rv = os.path.join(shadow_root, "L1", "Personal", "Journal", "2025", "Reviews", "[L1] entry.review.md")
    if review_path == expected_rv:
        print("SUCCESS: Review Path matches expectation.")
    else:
        print(f"FAIL: Expected {expected_rv}")

if __name__ == "__main__":
    test_nested_paths()
