import os
import sys
import re
import json

def test_keyword_extraction():
    summary_output = """
# Summary Title
This is some content.

keywords:
- AI
- Machine Learning
- Metadata
"""
    
    # Logic from L1Builder
    tags = []
    kw_match = re.search(r'keywords:\s*\n((?:\s*-\s*.*\n?)+)', summary_output, re.IGNORECASE)
    if kw_match:
        kw_block = kw_match.group(1)
        tags = [line.strip().replace('- ', '').strip() for line in kw_block.split('\n') if line.strip() and '- ' in line]
    
    print(f"Extracted Tags: {tags}")
    if tags == ["AI", "Machine Learning", "Metadata"]:
        print("SUCCESS: Keywords extracted correctly.")
    else:
        print("FAIL: Extraction failure.")

if __name__ == "__main__":
    test_keyword_extraction()
