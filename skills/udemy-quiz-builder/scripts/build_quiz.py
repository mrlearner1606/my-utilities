#!/usr/bin/env python3
"""
build_quiz.py — Turn a saved Udemy "practice test results" page into a
self-contained, single-file HTML quiz app (Timed Mode + Review Mode).

USAGE:
    python3 build_quiz.py <saved_html_path> <output_html_path> [--title "My Quiz"]

WHAT IT EXPECTS AS INPUT:
    A .html file saved via the browser's "Save Page As... > Webpage, Complete"
    from a Udemy practice-test RESULTS page (i.e. the user opened a practice
    test, answered or skipped through it, submitted, and is now viewing the
    per-question results/review page — NOT the course landing page, and NOT
    the "start test" page). The accompanying "<name>_files" folder (if any,
    for embedded images) must sit next to the .html file, same as when the
    browser saved it.

    How to get this file from a user: tell them to open the practice test,
    click through/submit it (skipping is fine — you don't need real answers,
    you're only harvesting the questions/answers/explanations), then on the
    results page do Ctrl+S / Cmd+S and choose "Webpage, Complete" so images
    get saved alongside the HTML. Zip the .html + "_files" folder together.

WHAT IT DOES:
    1. Parses every question panel using Udemy's shared React component
       classes (these have stayed stable across at least 3 different course
       authors' saved pages, so this selector set is fairly durable):
         - div.result-pane--question-result-pane--sIcOh   (one per question)
         - #question-prompt                                (question text)
         - [data-purpose="answer"]                          (one per option)
         - answer-result-pane--answer-correct--PLOEU class  (marks correct option)
         - #answer-text                                     (option text)
         - #question-explanation                            (per-option explanation)
         - #overall-explanation                             (rich-text overall explanation,
                                                               may contain <b>, <a>, <img>)
         - div.domain-pane--domain-pane--Pw9dK               (exam domain tag, OPTIONAL —
                                                               not all courses tag this)
    2. Auto-detects multi-select questions (>1 correct option = "select TWO" etc.)
    3. Auto-detects and extracts embedded images inside the overall explanation.
       Udemy renders each image TWICE (one hidden <img style="display:none">
       duplicate + one visible one inside a zoom wrapper) — this script keeps
       only the visible one.
    4. ALWAYS compresses extracted images before embedding (resize to max
       1400px width, re-encode as JPEG quality 80). Some courses (e.g. ones
       recorded from a Retina/high-DPI screen) save 3-4.5MB PNG screenshots
       per image — across 70-90 images that balloons a "single file" HTML to
       hundreds of MB. Compressing typically cuts total image weight by
       95%+ with no meaningful loss of readability for diagrams/screenshots.
       Images are embedded as base64 data URIs so the output stays ONE
       portable file (no external images folder to lose track of).
    5. Fills in the HTML template (assets/quiz_app_template.html, sitting
       next to this script) with the extracted data and writes a single
       finished .html file — no external JS/CSS/image files needed.

OUTPUT APP FEATURES (already built into the template, nothing to do here):
    - Review Mode: check each answer immediately, correct/incorrect banner,
      per-option explanations, "Overall Explanation" panel (with images/links).
    - Timed Mode: user sets a time limit, auto-submits at zero.
    - Final results screen (both modes): score %, correct/wrong/skipped counts,
      full review of EVERY question showing ALL options (not just correct +
      picked) each with its own explanation, plus the Overall Explanation.
    - Click-to-zoom lightbox for any embedded diagram images.

DEPENDENCIES: beautifulsoup4, Pillow (both pip-installable:
    pip install beautifulsoup4 Pillow --break-system-packages)
"""

import argparse
import base64
import io
import json
import os
import sys

from bs4 import BeautifulSoup

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

QUESTION_PANEL_CLASS = "result-pane--question-result-pane--sIcOh"
CORRECT_CLASS = "answer-result-pane--answer-correct--PLOEU"
DOMAIN_CLASS = "domain-pane--domain-pane--Pw9dK"
IMG_MAX_WIDTH = 1400
IMG_JPEG_QUALITY = 80

ALLOWED_RICH_TAGS = {"p", "b", "strong", "code", "a", "br", "ul", "li", "i", "em", "ol", "img"}


def compress_image_to_data_uri(path):
    """Resize + re-encode an image file to a small base64 JPEG data URI."""
    if not HAVE_PIL:
        # Fallback: embed raw bytes if Pillow isn't available (NOT recommended —
        # will produce a much larger file for high-res screenshots).
        with open(path, "rb") as f:
            raw = f.read()
        ext = path.rsplit(".", 1)[-1].lower()
        mime = "image/png" if ext == "png" else "image/jpeg"
        return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")

    im = Image.open(path).convert("RGB")
    w, h = im.size
    if w > IMG_MAX_WIDTH:
        ratio = IMG_MAX_WIDTH / w
        im = im.resize((IMG_MAX_WIDTH, max(1, int(h * ratio))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=IMG_JPEG_QUALITY, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def clean_rich_html(node, files_dir, img_cache):
    """Strip an explanation fragment down to a safe subset of tags, and
    convert any <img> src to a compressed base64 data URI."""
    # Drop the hidden duplicate image Udemy always renders alongside the
    # visible one (style="display:none").
    for img in node.find_all("img"):
        style = img.get("style", "") or ""
        if "display: none" in style or "display:none" in style:
            img.decompose()

    for tag in node.find_all(True):
        if tag.name not in ALLOWED_RICH_TAGS:
            tag.unwrap()
            continue
        if tag.name == "a":
            href = tag.get("href", "")
            tag.attrs = {"href": href, "target": "_blank", "rel": "noopener noreferrer"}
        elif tag.name == "img":
            src = tag.get("src", "")
            fname = os.path.basename(src) if src else ""
            data_uri = None
            if fname:
                if fname in img_cache:
                    data_uri = img_cache[fname]
                else:
                    fpath = os.path.join(files_dir, fname) if files_dir else fname
                    if os.path.exists(fpath):
                        data_uri = compress_image_to_data_uri(fpath)
                        img_cache[fname] = data_uri
            if data_uri:
                tag.attrs = {"src": data_uri, "alt": "diagram", "class": "oe-img"}
            else:
                tag.decompose()
        else:
            tag.attrs = {}
    return str(node)


def extract_questions(html_path):
    files_dir = None
    base_no_ext = os.path.splitext(html_path)[0]
    candidate = base_no_ext + "_files"
    if os.path.isdir(candidate):
        files_dir = candidate

    with open(html_path, encoding="utf-8", errors="ignore") as f:
        content = f.read()
    soup = BeautifulSoup(content, "html.parser")
    panels = soup.find_all("div", class_=QUESTION_PANEL_CLASS)

    if not panels:
        print(
            "WARNING: found 0 question panels. This usually means the saved "
            "HTML is the course LANDING page, not a practice-test RESULTS "
            "page. Ask the user to open the test, submit/skip through it, "
            "and re-save from the results screen.",
            file=sys.stderr,
        )

    img_cache = {}
    questions = []
    for i, p in enumerate(panels, 1):
        qtext_div = p.find(id="question-prompt")
        qtext = qtext_div.get_text(separator="\n").strip() if qtext_div else ""

        ans_blocks = p.find_all(attrs={"data-purpose": "answer"})
        options = []
        for ab in ans_blocks:
            is_correct = CORRECT_CLASS in ab.get("class", [])
            text_div = ab.find(id="answer-text")
            opt_text = text_div.get_text(separator=" ").strip() if text_div else ""
            wrapper = ab.parent
            expl_div = wrapper.find(id="question-explanation") if wrapper else None
            expl_text = expl_div.get_text(separator=" ").strip() if expl_div else ""
            options.append({"text": opt_text, "correct": is_correct, "explanation": expl_text})

        oe_div = p.find(id="overall-explanation")
        overall_html = ""
        if oe_div:
            oe_copy = BeautifulSoup(str(oe_div), "html.parser").find(id="overall-explanation")
            oe_copy.attrs = {}
            cleaned = clean_rich_html(oe_copy, files_dir, img_cache)
            inner = BeautifulSoup(cleaned, "html.parser").find("div")
            overall_html = inner.decode_contents() if inner else cleaned

        domain_div = p.find("div", class_=DOMAIN_CLASS)
        domain_text = ""
        if domain_div:
            parts = [t.strip() for t in domain_div.get_text(separator="|").split("|") if t.strip()]
            domain_text = parts[-1] if parts else ""

        questions.append(
            {
                "num": i,
                "question": qtext,
                "options": options,
                "overall_explanation": overall_html,
                "domain": domain_text,
            }
        )

    return questions


def summarize(questions):
    total = len(questions)
    multi = sum(1 for q in questions if sum(1 for o in q["options"] if o["correct"]) > 1)
    with_images = sum(1 for q in questions if "<img" in q["overall_explanation"])
    with_domain = sum(1 for q in questions if q["domain"])
    bad = [
        q["num"]
        for q in questions
        if not q["question"] or any(not o["text"] for o in q["options"]) or not q["overall_explanation"]
    ]
    print(f"Extracted {total} questions.")
    print(f"  Multi-select ('select TWO' etc.): {multi}")
    print(f"  With embedded diagram images:     {with_images}")
    print(f"  With an exam-domain tag:          {with_domain}")
    if bad:
        print(f"  WARNING - possibly incomplete questions (check manually): {bad}")


def build_html(questions, template_path, output_path, title=None):
    with open(template_path, encoding="utf-8") as f:
        template = f.read()

    n = len(questions)
    page_title = title or f"Practice Exam — {n} Questions"
    header_title = title.split("—")[0].strip() if title else "Practice Exam"
    hero_heading = f"Practice Exam — {n} Questions"
    hero_subtext = "Pick how you want to practice today 😎"

    quiz_data_js = "const QUIZ_DATA = " + json.dumps(questions, ensure_ascii=False) + ";"

    html = template
    html = html.replace("{{PAGE_TITLE}}", page_title)
    html = html.replace("{{HEADER_TITLE}}", header_title)
    html = html.replace("{{HEADER_BADGE}}", "QUIZ")
    html = html.replace("{{HERO_HEADING}}", hero_heading)
    html = html.replace("{{HERO_SUBTEXT}}", hero_subtext)
    html = html.replace("{{QUIZ_DATA_JS}}", quiz_data_js)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    size_mb = os.path.getsize(output_path) / 1e6
    print(f"Wrote {output_path} ({size_mb:.1f} MB)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input_html", help="Path to the saved Udemy results-page HTML file")
    ap.add_argument("output_html", help="Path to write the finished quiz app HTML file to")
    ap.add_argument("--title", default=None, help="Custom title, e.g. 'AWS AIP-C01 — Practice Test 2'")
    ap.add_argument(
        "--template",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "quiz_app_template.html"),
        help="Path to the HTML template (defaults to assets/quiz_app_template.html next to this script)",
    )
    args = ap.parse_args()

    if not HAVE_PIL:
        print(
            "NOTE: Pillow not installed — images (if any) will be embedded "
            "uncompressed, which can make the output file huge. Install with:\n"
            "  pip install Pillow --break-system-packages",
            file=sys.stderr,
        )

    questions = extract_questions(args.input_html)
    summarize(questions)
    build_html(questions, args.template, args.output_html, title=args.title)


if __name__ == "__main__":
    main()
