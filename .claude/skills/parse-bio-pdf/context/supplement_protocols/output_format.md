# Supplement Protocol Output Format

## JSON Format

{
  "patient_name": "<PATIENT_NAME>",
  "protocol_date": "<YYYY-MM-DD>",
  "prescriber": null,
  "supplements": [
    {
      "name": "<SUPPLEMENT_NAME>",
      "instructions": "<SPECIAL_INSTRUCTIONS_OR_NULL>",
      "frequency": "<FREQUENCY>",
      "schedule": {
        "upon_waking": <COUNT_OR_0>,
        "breakfast": <COUNT_OR_0>,
        "mid_morning": <COUNT_OR_0>,
        "lunch": <COUNT_OR_0>,
        "mid_afternoon": <COUNT_OR_0>,
        "dinner": <COUNT_OR_0>,
        "before_sleep": <COUNT_OR_0>
      }
    }
  ],
  "own_supplements": [
    {
      "name": "<SUPPLEMENT_NAME>",
      "dosage": "<DOSAGE_TEXT>",
      "frequency": "<FREQUENCY>"
    }
  ],
  "lifestyle_notes": {
    "protein_goal": "<PROTEIN_GOAL_OR_NULL>",
    "other": []
  },
  "next_visit": "<NEXT_VISIT_OR_NULL>"
}

### Field Definitions

#### protocol_date

Convert to ISO format YYYY-MM-DD:
- "12/29/2025" -> "2025-12-29"
- "12-29-25" -> "2025-12-29"

#### supplements[].frequency

Extract from instructions column. Common values:
- `"daily"` - default if no specific frequency
- `"2x_week"` - "2x/week"
- `"3x_week"` - "3x/week"
- `"1x_week"` - "1x/week", "once weekly"
- `"as_needed"` - "as needed", "prn"
- `"with_meals"` - "with meals", "before meals"

#### supplements[].schedule

Map table columns to schedule keys:
| Column Header | JSON Key |
|---------------|----------|
| Upon Waking | `upon_waking` |
| Breakfast | `breakfast` |
| 10:00am | `mid_morning` |
| Lunch | `lunch` |
| 3:00pm | `mid_afternoon` |
| Dinner | `dinner` |
| Before Sleep | `before_sleep` |

If a cell contains text like "1 scoop", extract the numeric value (1).
If empty, use 0.

#### own_supplements[].frequency

Parse from dose column:
- "1/day" -> "daily"
- "2/day" -> "2x_daily"
- "as needed" -> "as_needed"

## Extraction Rules

1. **Preserve Supplement Names**: Extract names EXACTLY as written (e.g., "Vitamin D", "KL Support", "Zinc30")
2. **Handle Instructions**:
   - Capture full instruction text
   - Extract frequency from instructions when present
   - Common patterns: "with food", "take before noon", "5-10 minutes before meals"
3. **Handle Special Dosages**:
   - "1 scoop" -> schedule count = 1, note "scoop" in instructions
   - "2x/week" with no schedule numbers -> frequency = "2x_week", schedule all 0s
4. **Empty Schedule**:
   - If a supplement has instructions but no schedule numbers (e.g., "Vitamin D" with "2x/week"), set all schedule values to 0 and capture in frequency
5. **Own Supplements**:
   - These are user's personal supplements, not prescribed
   - Extract name and dosage as-is
   - No schedule needed (schedule is implicit in dosage like "1/day")

## Example Extraction
