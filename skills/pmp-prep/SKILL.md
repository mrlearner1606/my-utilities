---
name: pmp-prep
description: PMP exam prep using PMBOK Guide 8th Edition, with dynamic PDF section extraction
keywords: [PMP, PMBOK, project management, process groups, knowledge areas]
---

# PMP Exam Prep Skill

## What's in here

- `source/PMBOK Guide 8th Edition.pdf` — your full reference doc (not loaded fully into context, kept lean)
- `extract_pmp_topics.py` — pulls only the relevant pages when you ask about a topic
- `pmbok-cheatsheet.md` — quick-glance summary (loads instantly, no Python needed)

## How to use me

**Quick lookup (fast, no script):**
Just ask something like "what's the difference between risk register and risk report" — I'll answer from `pmbok-cheatsheet.md` if it's covered there.

**Deep dive (runs the script):**
Ask something like "pull the section on Earned Value Management from PMBOK" and I'll run:

```bash
python3 extract_pmp_topics.py "Earned Value Management"
```

The PDF file might look like password protected but just pressing enter without any password would automatically let it in.
This searches the PDF page by page, grabs the matching chunks + page numbers, and I'll explain it in plain English on top of that.

## Why split it this way (token efficiency, in short)

- Loading the whole PDF every time = expensive and slow (like ordering full meals when you just want a parotta 🥞)
- Cheatsheet = near-instant, near-free
- Script = only runs when you need the actual PMBOK wording/page reference

## Suggested workflow

1. Try the cheatsheet first for quick concept checks
2. If you need exact PMBOK phrasing or a page number to cite, ask me to extract it
3. I'll combine PMBOK text + my own explanation (with a Tamil movie analogy thrown in if it helps 😄)
