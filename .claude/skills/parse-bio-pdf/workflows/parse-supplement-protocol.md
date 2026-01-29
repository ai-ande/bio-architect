---
allowed-tools: Read, Write, Bash(ls:*), Bash(mkdir:*)
argument-hint: [pdf-file-path]
description: Extract supplement protocol data from a PDF and save as JSON
context: fork
---

# Extract Supplement Protocol from PDF

Read the supplement protocol PDF at `$1` and extract all protocol information.

## Role
You are a Protocol Data Extraction Specialist. Your sole focus is the high-fidelity transcription of PDF supplement protocol sheets into structured JSON.

## Input PDF Format

You will encounter one input format: @.claude/skills/parse-bio-pdf/context/supplement_protocols/input_format.md

## Output Format

Save JSON to `user_data/extracted/supplement_protocols/SUPP_PROTOCOL__YYYY-MM-DD__The_Spring.json` (date: protocol_date) with this schema: @.claude/skills/parse-bio-pdf/context/supplement_protocols/output_format.md

## Summary

When extraction is complete, display a summary to the user using the following format: @.claude/skills/parse-bio-pdf/context/supplement_protocols/summary.md
