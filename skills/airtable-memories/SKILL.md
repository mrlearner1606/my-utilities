---
name: airtable-memories
description: Use this skill whenever the user wants to (1) look up personal info/memories from their Airtable "Memories" tables, or (2) save/update a new piece of personal info into Airtable. The memories are spread across multiple tables (Memories_1, Memories_2, ... Memories_n) because each table has a row limit. Trigger this skill on phrases like "check airtable for...", "did I mention...", "remember when I said...", "update airtable with...", "note this down", "save this info".
---

# Airtable Memories Skill

Think of this like a **diary split across multiple notebooks** 📓📓📓 — Notebook 1 (Memories_1), and when it's full, you start Notebook 2 (Memories_2), and so on. This skill tells Claude how to **read from** and **write to** that diary correctly.

## Table Structure

Each Memories table (`Memories_1`, `Memories_2`, ... `Memories_n`) has exactly 3 columns:

| Column | What it holds | Example |
|---|---|---|
| **Knowledge** | The info, written in 1st person ("I did/am/will...") | `I am planning to use perplexity to forecast stocks and wisely invest` |
| **Reference** | Comma-separated keywords for searching | `perplexity, forecast, stocks, invest` |
| **Date** | Date of the info, format: `18 July 2025` | `18 July 2025` |

---

## Part 1: SEARCHING for info (read workflow)

When the user asks "did I mention X?" or "check what I said about Y" — follow this order:

1. **Find the base** — Use `Airtable:search_bases` or `Airtable:list_bases` to locate the correct Airtable base (the one containing the Memories tables).
2. **List the tables** — Use `Airtable:list_tables_for_base` to see which Memories tables exist (Memories_1, Memories_2, Memories_3...). Note them down in order.
3. **Search Memories_1 first**:
   - Use `Airtable:search_records` (free-text search) with the user's keyword(s) against Memories_1, OR
   - Use `Airtable:list_records_for_table` + filter manually if `search_records` isn't precise enough.
   - Match keywords against the **Reference** column primarily (that's what it's built for). Also do a loose check against Knowledge in case the exact keyword wasn't tagged in Reference.
4. **If found** → return the Knowledge + Date to the user. Stop here, no need to check further tables.
5. **If NOT found in Memories_1** → repeat step 3 on Memories_2, then Memories_3, and so on, in numeric order, until either:
   - a match is found (stop and return it), or
   - all Memories_n tables are exhausted (tell the user nothing was found).
6. If multiple matches turn up across different tables, show all of them with their dates (most recent first is a nice touch).

**Search tip:** Break the user's query into individual keywords before searching — e.g. "did I say anything about stock investing?" → search terms: `stock`, `invest`, `investing`. Try a couple variants since Reference tags may not match the exact word the user used.

---

## Part 2: UPDATING / ADDING new info (write workflow)

When the user gives an instruction like "note this down", "update airtable that I..." — follow this order:

1. **Find the base and list tables** (same as search steps 1–2).
2. **Check Memories_1's capacity**:
   - Count records in Memories_1 using `Airtable:list_records_for_table` (paginate through if needed to get a true count).
   - **If record count < 1000** → this is where the new entry goes.
   - **If record count >= 1000 (table is "full")** → move to Memories_2, check its count the same way, and so on — keep walking up (Memories_2, Memories_3, ... Memories_n) until you find a table with room. If even the last existing Memories_n is full, create the next one (Memories_n+1) with the same 3-column structure using `Airtable:create_table`, matching the schema of the existing tables (use `Airtable:get_table_schema` on Memories_1 to copy field types exactly).
3. **Prepare the row data**:
   - **Knowledge**: Rewrite the user's message in **first person**, like a diary entry. E.g. user says "I'm planning to invest via perplexity forecasts" → Knowledge = `I am planning to use perplexity to forecast stocks and wisely invest`.
   - **Reference**: Pull out the key nouns/topics/keywords from the Knowledge sentence, comma-separated, lowercase preferred. E.g. `perplexity, forecast, stocks, invest`.
   - **Date**:
     - If the user specifies a date → use that, formatted as `D Month YYYY` (e.g. `18 July 2025`).
     - If no date is given → use **today's date**, same format (e.g. `3 August 2026`).
4. **Insert the record** — Use `Airtable:create_records_for_table` on the target Memories_n table with the three fields (Knowledge, Reference, Date) filled in as above.
5. **Confirm to the user** — a quick one-liner like: "Saved to Memories_2 ✅ — [Knowledge summary] — dated [date]."

---

## Quick Reference — Tools Used

| Task | Tool |
|---|---|
| Find the base | `Airtable:search_bases` / `Airtable:list_bases` |
| List Memories tables | `Airtable:list_tables_for_base` |
| Check table schema (for creating new table) | `Airtable:get_table_schema` |
| Search for info | `Airtable:search_records` |
| Count records / list all | `Airtable:list_records_for_table` |
| Add new table when all full | `Airtable:create_table` |
| Insert new memory | `Airtable:create_records_for_table` |

---

## Golden Rules 🥇

- **Always search Memories_1 → Memories_2 → Memories_n in order** — like checking notebooks one by one, don't skip.
- **Always write Knowledge in 1st person** ("I did/am/will...") — it's a personal diary, not a report.
- **Never overflow a table past ~1000 records** — check count before inserting, roll over to the next table if full.
- **Date format is always `D Month YYYY`** (e.g. `18 July 2025`) — no slashes, no ISO format.
- **Reference column = searchable keywords**, not full sentences — keep it short and tag-like.
