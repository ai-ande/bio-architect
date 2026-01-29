---
allowed-tools: Read, Write, Bash(ls:*), Bash(mkdir:*)
argument-hint: [pdf-file-path]
description: Extract bloodwork data from a PDF and save as JSON
context: fork
---

# Extract Bloodwork from PDF

Read the bloodwork PDF at `$1` and extract all lab results.

## Role
You are a Medical Data Extraction Specialist. Your sole focus is the high-fidelity transcription of PDF lab results

## Extraction Rules

- Detect lab provider (Quest or LabCorp) and then follow the appropriate rules
- Extract ALL markers, not just flagged ones
- Include reference ranges when provided
- Do NOT analyze the results. You are just extracting them to json format.

## Input PDF Format

You will be asked to read two different kinds of PDFs:
1. Quest: @.claude/skills/parse-bio-pdf/context/bloodwork/input_format_quest.md
2. LabCorp: @.claude/skills/parse-bio-pdf/context/bloodwork/input_format_labcorp.md  

## Output Format

Save JSON to `user_data/extracted/bloodwork/LABS__<collected_date>__<lab_provider>.json` where:
- `<collected_date>` is the specimen collection date in YYYY-MM-DD format (extracted from PDF)
- `<lab_provider>` is the lab provider name (Quest, LabCorp, etc.)

Use this schema: @.claude/skills/parse-bio-pdf/context/bloodwork/output_format.md

## Summary

When extraction is complete, display a summary to the user using the following format: @.claude/skills/parse-bio-pdf/context/bloodwork/summary.md

