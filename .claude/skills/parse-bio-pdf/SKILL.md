---
allowed-tools: Read, Write, Bash(ls:*), Bash(mkdir:*)
argument-hint: [pdf-file-path]
description: Use when user asks to "parse" PDF files - bloodwork labs, supplement labels, or protocols. Activates when PDFs are dropped in IDE or file paths provided in terminal with parse request.
---

# Parse Bio-Data PDF Skill

Extract structured JSON data from health-related PDFs.

## When to Activate

Use this skill when:
- User drops PDF file(s) in IDE and says "parse"
- User provides file path(s) in terminal and says "parse"
- User asks to extract/parse bloodwork, supplement labels, or protocols

## File Type Detection

Read the PDF and detect type from content:

| Content Indicators | Type | Workflow |
|-------------------|------|----------|
| Biomarker panels, reference ranges, lab provider (Quest/LabCorp) | Bloodwork | .claude/skills/parse-bio-pdf/workflows/parse-bloodwork.md |
| "Supplement Facts", serving size, ingredients list | Supplement Label | .claude/skills/parse-bio-pdf/workflows/parse-supplement-label.md |
| Dosing schedule table, timing columns (breakfast, lunch, dinner) | Protocol | .claude/skills/parse-bio-pdf/workflows/parse-supplement-protocol.md |

## Processing

1. Identify all PDF file(s) to process
2. For each file (in parallel -- each command has setting context: fork):
   a. Detect file type from filename or content
   b. Call the appropriate workflow, passing the file path
3. Report results for each file processed

## Examples

### Bloodwork Labs
```
User: parse my_lab_results.pdf

Action: Read PDF, detect bloodwork content, call .claude/skills/parse-bio-pdf/workflows/parse-bloodwork.md
Output: Saves to user_data/extracted/bloodwork/LABS__<collected_date>__<lab_provider>.json
```

### Supplement Labels
```
User: parse vitamin_d.pdf

Action: Read PDF, detect supplement label content, call .claude/skills/parse-bio-pdf/workflows/parse-supplement-label.md
Output: Saves to user_data/extracted/supplement_labels/SUPP_LABEL__<product_name>__<brand>.json
```

### Supplement Protocols
```
User: parse protocol.pdf

Action: Read PDF, detect protocol content, call .claude/skills/parse-bio-pdf/workflows/parse-supplement-protocol.md
Output: Saves to user_data/extracted/supplement_protocols/SUPP_PROTOCOL__<protocol_date>__The_Spring.json
```
