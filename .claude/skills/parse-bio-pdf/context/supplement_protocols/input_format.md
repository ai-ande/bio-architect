# Supplement Protocol Input Format

## Supplement Protocol Sheet Structure

### Header Section
- **Name**: Patient name (e.g., "Andy Kaplan")
- **Date**: Protocol date (e.g., "12/29/2025")

### Main Supplements Table

Columns:
1. **Supplements** - Supplement name
2. **Instructions** - Special dosing notes (e.g., "with food: 1 pack 2x/week", "take before noon")
3. **Upon Waking** - Dosage count at waking
4. **Breakfast** - Dosage count at breakfast
5. **10:00am** - Dosage count mid-morning
6. **Lunch** - Dosage count at lunch
7. **3:00pm** - Dosage count mid-afternoon
8. **Dinner** - Dosage count at dinner
9. **Before Sleep** - Dosage count before bed

Each cell contains:
- An integer dosage count (1, 2, etc.)
- A special instruction (e.g., "1 scoop", "2x/week")
- Empty if not taken at that time

### Lifestyle Section

- **Protein Goal**: Daily protein target (e.g., "110g/day")
- Other lifestyle instructions

### Own Supplements Section

User's existing supplements to continue:
- **Supplement name** + **Dose** (e.g., "Zinc30" + "1/day")

### Next Visit

Follow-up timing (e.g., "4 weeks")

## Reference

### Example
For this row:
| Supplements | Instructions | Upon Waking | Breakfast | 10:00am | Lunch | 3:00pm | Dinner | Before Sleep |
|-------------|--------------|-------------|-----------|---------|-------|--------|--------|--------------|
| Kalmz | | | 2 | | | | 2 | |

Output:
```json
{
  "name": "Kalmz",
  "instructions": null,
  "frequency": "daily",
  "schedule": {
    "upon_waking": 0,
    "breakfast": 1,
    "mid_morning": 0,
    "lunch": 0,
    "mid_afternoon": 0,
    "dinner": 2,
    "before_sleep": 0
  }
}

### Example Files
If needed, read:
- user_data/sample_data/pdfs/supplement_protocols/SUPP_PROTOCOL__2025-12-29__The_Spring.pdf (input pdf)
- user_data/sample_data/extracted/supplement_protocols/SUPP_PROTOCOL__2025-12-29__The_Spring.json (output json)