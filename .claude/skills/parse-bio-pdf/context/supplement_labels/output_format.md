# Supplement Label Output Format

## JSON Format

{
  "brand": "<BRAND_NAME>",
  "product_name": "<PRODUCT_NAME>",
  "form": "<FORM>",
  "serving_size": "<SERVING_SIZE>",
  "servings_per_container": <SERVINGS_COUNT>,
  "suggested_use": "<SUGGESTED_USE_TEXT>",
  "active_ingredients": [
    {
      "name": "<INGREDIENT_NAME_EXACTLY_AS_WRITTEN>",
      "code": "<NORMALIZED_CODE>",
      "amount": <AMOUNT_VALUE>,
      "unit": "<UNIT>",
      "percent_dv": <PERCENT_DV_OR_NULL>,
      "form": "<CHEMICAL_FORM_OR_NULL>"
    }
  ],
  "proprietary_blends": [
    {
      "name": "<BLEND_NAME>",
      "total_amount": <TOTAL_AMOUNT>,
      "total_unit": "<UNIT>",
      "ingredients": [
        {
          "name": "<INGREDIENT_NAME_EXACTLY_AS_WRITTEN>",
          "code": "<NORMALIZED_CODE>",
          "form": "<FORM_OR_NULL>"
        }
      ]
    }
  ],
  "other_ingredients": [
    {
      "name": "<INGREDIENT_NAME>",
      "code": "<NORMALIZED_CODE>"
    }
  ],
  "warnings": ["<WARNING_TEXT>"],
  "allergen_info": "<ALLERGEN_STATEMENT_OR_NULL>"
}

### Field Definitions

- **brand**: Manufacturer/brand name (e.g., "Thorne", "Body Health")
- **product_name**: Full product name as shown on label
- **form**: One of: "capsule", "tablet", "softgel", "powder", "liquid", "lozenge", "gummy"
- **serving_size**: Exactly as written (e.g., "1 capsule", "1 Scoop (5.3g)")
- **servings_per_container**: Integer count
- **suggested_use**: Full dosing instructions text
- **active_ingredients**: Array of active supplement ingredients
- **proprietary_blends**: Array of proprietary blend sections (if any)
- **other_ingredients**: Array of inactive/filler ingredients
- **warnings**: Array of warning statements
- **allergen_info**: Allergen statement if present, null otherwise

## Extraction Rules

1. **Preserve Original Names**: The `name` field must contain the ingredient name EXACTLY as it appears on the label, including parenthetical forms like "Zinc (as Zinc Picolinate)"
2. **Extract Chemical Forms**: If an ingredient shows a chemical form (e.g., "as Zinc Picolinate", "(Methylcobalamin)"), extract it to the `form` field
3. **Handle Proprietary Blends**:
   - Create a separate entry in `proprietary_blends` array
   - Include total blend amount
   - List all ingredients without individual amounts
   - Do NOT duplicate in `active_ingredients`
4. **Handle % Daily Value**:
   - Extract numeric value (e.g., "273%" → 273)
   - Use `null` if marked as "*" or "†" (Daily Value not established)
5. **Unit Handling**:
   - Preserve compound units like "mcg DFE" or "mg NE"
   - Common units: mg, mcg, g, IU, CFU
6. **Other Ingredients**:
   - Extract all inactive ingredients
   - These typically appear as a comma-separated list after "Other Ingredients:"
7. **Warnings & Allergens**:
   - Extract all warning statements
   - Note allergen information separately
8. **Code Normalization**: The `code` field must be normalized across labels. Use this mapping: @.claude/skills/parse-pdf/context/supplement_labels/ingredient_normalization.md