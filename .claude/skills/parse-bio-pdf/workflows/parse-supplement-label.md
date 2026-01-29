---
allowed-tools: Read, Write, Bash(ls:*), Bash(mkdir:*)
argument-hint: [pdf-file-path]
description: Extract supplement label data from a PDF and save as JSON
context: fork
---

# Extract Supplement Label from PDF

Read the supplement label PDF at `$1` and extract all supplement information.

## Role
You are a Supplement Data Extraction Specialist. Your sole focus is the high-fidelity transcription of PDF supplement labels.

## Input PDF Format

Supplement labels vary significantly in format. You will encounter several types: @.claude/skills/parse-bio-pdf/context/supplement_labels/input_format.md

## Output Format

Save JSON to `user_data/extracted/supplement_labels/SUPP_LABEL__<product_name>__<brand>.json` where:
- `<product_name>` is the product name (extracted from PDF, spaces replaced with underscores)
- `<brand>` is the brand name (extracted from PDF, spaces replaced with underscores)

Use this schema: @.claude/skills/parse-bio-pdf/context/supplement_labels/output_format.md

## Summary

When extraction is complete, display a summary to the user using the following format: @.claude/skills/parse-bio-pdf/context/supplement_labels/summary.md