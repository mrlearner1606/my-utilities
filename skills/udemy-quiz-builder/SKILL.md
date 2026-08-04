---
name: udemy-quiz-builder
description: Build a self-contained, single-file HTML practice-exam app (Timed Mode + Review Mode, instant grading, per-option explanations, an "Overall Explanation" with embedded diagrams, and a full end-of-quiz review) from a saved Udemy practice-test results page. Use this whenever the user uploads a zip/HTML file that looks like a saved Udemy quiz/practice-test page (mentions "practice test", "results", has question/answer panels) and asks for a quiz app, practice test app, or similar — even if they don't say "Udemy" explicitly. Also use it if the user references a previously-built quiz app like this one and wants "the same thing" for a new file.
---

# Udemy Quiz Builder

Turns a browser-saved Udemy practice-test **results** page into a polished,
portable HTML quiz app the user can open and use completely offline —
no login, no course subscription needed, nothing sent anywhere.

## Why this works at all

Udemy's practice-test results page already contains every question, every
option, which one is correct, a per-option explanation, AND a richly
formatted "Overall Explanation" (with bold text, doc links, and sometimes
embedded diagram images) — it's just buried inside deeply nested React
component HTML, not visible as plain text. A casual `view` of the file
looks empty/promotional because the real content is inside collapsed
result panels. **Always grep/parse before concluding a file has no
questions in it** (see Step 1).

This selector set has proven stable across at least 3 different course
authors' saved pages (Frank Kane, Stephane Maarek, an unnamed "Vladimir"
course) — it's Udemy's shared platform template, not something specific
to one instructor.

## Step 0 — Get the right file from the user

The user needs to give you a **results** page, not the course landing
page. Tell them, if they haven't already done this:

1. Open the practice test in Udemy.
2. Click/answer through it (skipping every question is fine — you only
   need the questions/answers/explanations, not their real performance).
3. Submit, and view the **results/review screen** (the one that shows
   right/wrong per question).
4. `Ctrl+S` / `Cmd+S` → save as **"Webpage, Complete"** (not "HTML only")
   so any embedded images get saved into the accompanying `_files` folder.
5. Zip the `.html` file together with its `_files` folder and upload it.

If a zip only contains a landing/promo page (course overview, "what
you'll learn", instructor bio) with no question panels, say so plainly —
don't force a quiz out of it. Extraction in Step 1 will report 0 question
panels found, which is your confirmation.

## Step 1 — Extract

Use the bundled script — don't hand-roll extraction each time:

```bash
pip install beautifulsoup4 Pillow --break-system-packages -q
python3 scripts/build_quiz.py <extracted_html_path> <output.html> --title "<Course/Test name> — Practice Test"
```

`extracted_html_path` is the `.html` file after unzipping (the script
auto-locates the sibling `<name>_files` folder for images, same convention
the browser uses).

The script prints a summary — **read it and relay the highlights to the
user** before/while building (question count, how many are multi-select,
how many have embedded images, whether any exam-domain tags were found).
This is also your sanity check: 0 questions found means Step 0 wasn't
followed; report that back instead of shipping an empty app.

### If you need to inspect the format first (new/unfamiliar course)

Before assuming the standard selectors apply, spot-check with BeautifulSoup:

```python
from bs4 import BeautifulSoup
soup = BeautifulSoup(open(html_path, encoding='utf-8', errors='ignore').read(), 'html.parser')
panels = soup.find_all('div', class_='result-pane--question-result-pane--sIcOh')
print(len(panels))  # should roughly match the test's advertised question count
```

If that comes back 0, the class names may have drifted (Udemy occasionally
rebuilds their frontend) — search the raw HTML for text you know is in a
question (e.g. a distinctive phrase from a screenshot) to find the current
wrapper classes, and update the constants at the top of
`scripts/build_quiz.py` (`QUESTION_PANEL_CLASS`, `CORRECT_CLASS`,
`DOMAIN_CLASS`) accordingly — the rest of the script's logic doesn't need
to change.

## Step 2 — Watch for the large-image trap

Some courses' explanation images are full-resolution retina screenshots
(3-4.5MB PNG *each*). Across 70-90 questions that's hundreds of MB —
completely impractical as a single portable HTML file. **The bundled
script already handles this automatically** (resizes to max 1400px width,
re-encodes as JPEG quality 80 — typically a 95%+ size reduction with no
real loss of readability for diagrams/screenshots), so you don't need to
think about it manually. Just be aware of *why* the output file size
varies so wildly between courses (some are ~400KB, some are ~50MB) so you
can set the user's expectations when you hand off the file — mention the
size and that it's normal.

## Step 3 — Deliver

Copy the finished file to `/mnt/user-data/outputs/`, present it, and tell
the user concretely what's in it (question count, multi-select count,
whether it has diagrams). Match the tone of whatever course number/name
context you have (e.g. "Practice Test 2", "Warm Up", "Full Exam") in the
filename and in the on-screen title — don't just call every output
`quiz.html`, since the user will likely be building several of these
across a course's multiple practice tests in the same conversation.

## What NOT to reinvent

The template at `assets/quiz_app_template.html` already implements, don't
rebuild from scratch:

- **Review Mode**: per-question "Check Answer" → immediate ✅/❌ banner,
  per-option explanations, and the Overall Explanation box.
- **Timed Mode**: user sets a time limit, auto-submits at zero.
- **End-of-quiz screen** (both modes): score %, correct/wrong/skipped
  counts, and a full review showing **every** option per question (not
  just the correct one and the user's pick) — this matters because seeing
  the *close* wrong answers with their explanations is the actual study
  value, not just "here's the right one."
- Click-to-zoom lightbox for embedded diagram images.
- Multi-select ("choose TWO") auto-detected from how many options are
  marked correct — checkboxes render automatically, no manual flagging
  needed.

If the user asks for a tweak (e.g. "add a banner telling me if I got it
right"), edit `assets/quiz_app_template.html` directly (it uses
`{{PAGE_TITLE}}`, `{{HEADER_TITLE}}`, `{{HEADER_BADGE}}`,
`{{HERO_HEADING}}`, `{{HERO_SUBTEXT}}`, `{{QUIZ_DATA_JS}}` as the only
placeholders — everything else is plain HTML/CSS/JS you can edit
directly) — then re-run `build_quiz.py` for every test/file already in
the conversation so they all get the improvement, not just the next one.
