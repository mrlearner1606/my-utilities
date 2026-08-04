#!/usr/bin/env python3
"""
PMBOK Guide 8th Edition - Section Extractor
Run this to pull relevant pages/sections based on a search topic.

Usage:
    python3 extract_pmp_topics.py "Earned Value Management"
    python3 extract_pmp_topics.py "risk register"
    python3 extract_pmp_topics.py "process groups"
"""

import sys
import json
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    print("ERROR: pypdf not installed. Run: pip install pypdf --break-system-packages")
    sys.exit(1)

SKILL_DIR = Path(__file__).parent
SOURCE_DIR = SKILL_DIR / "source"
PDF_PATH = SOURCE_DIR / "PMBOK Guide 8th Edition.pdf"


def search_pdf(pdf_path, keywords, max_results=5, chars_per_hit=600):
    """Search PDF page by page for keyword matches, return context chunks."""
    reader = PdfReader(pdf_path)
    results = []

    for page_num, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        text_lower = text.lower()

        if any(kw.lower() in text_lower for kw in keywords):
            results.append({
                "page": page_num + 1,
                "content": text[:chars_per_hit].strip(),
            })
            if len(results) >= max_results:
                break

    return results


def extract_topic(search_query):
    if not PDF_PATH.exists():
        return {
            "error": f"PDF not found at: {PDF_PATH}. "
                     f"Drop 'PMBOK Guide 8th Edition.pdf' into the source/ folder first."
        }

    keywords = search_query.split()
    print(f"🔍 Searching PMBOK Guide 8th Edition for: {search_query}\n")

    results = search_pdf(PDF_PATH, keywords)

    if not results:
        return {"status": "No results found", "query": search_query}

    output = f"## Found {len(results)} matching section(s):\n\n"
    for r in results:
        output += f"### Page {r['page']}\n{r['content']}...\n\n"

    return {"status": "success", "results": output}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 extract_pmp_topics.py '<search topic>'")
        print("\nExamples:")
        print("  python3 extract_pmp_topics.py 'Earned Value Management'")
        print("  python3 extract_pmp_topics.py 'risk register'")
        print("  python3 extract_pmp_topics.py 'process groups'")
        sys.exit(0)

    query = " ".join(sys.argv[1:])
    result = extract_topic(query)

    if isinstance(result, dict) and "results" in result:
        print(result["results"])
    else:
        print(json.dumps(result, indent=2))
