# Bloodwork Output Format

## JSON Format

{
  "lab_provider": "<LAB_PROVIDER>",
  "collected_date": "<COLLECTED_DATE>",
  "received_date": "<RECEIVED_DATE>",
  "reported_date": "<REPORTED_DATE>",
  "panels": [
    {
      "name": "<PANEL_NAME>",
      "comment": "<PANEL_COMMENT>",
      "biomarkers": [
        {
          "name": "<MARKER_NAME>",
          "code": "<NORMALIZED_CODE>",
          "value": <MARKER_VALUE>,
          "unit": "<MARKER_UNIT>",
          "reference_low": <MARKER_REF_LOW>,
          "reference_high": <MARKER_REF_HIGH>,
          "flag": "<MARKER_FLAG>"
        }
      ]
    }
  ]
}

## Biomarker Code Normalization

The `code` field must be normalized across labs. Use this mapping: @.claude/skills/parse-pdf/context/bloodwork/biomarker_normalization.md

## Flag

- Flag can be:
1. `low`
2. `normal`
3. `high`
4. `critical`
- If it's null, mark it as `normal`