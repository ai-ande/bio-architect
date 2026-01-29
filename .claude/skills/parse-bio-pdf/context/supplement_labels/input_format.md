# Supplement Label Input Format

## Types of Labels

### 1. Standard Supplement Facts Label

Most common format with a table structure:
- **Serving Size**: e.g., "1 capsule", "2 tablets", "1 scoop (5.3g)"
- **Servings Per Container**: e.g., "60", "30", "90"
- **Active Ingredients Table**: Ingredient name, Amount per serving, % Daily Value
- **Other Ingredients**: Listed below the table (inactive ingredients)
- **Suggested Use**: Dosing instructions
- **Warnings**: Safety information

#### Sample Labels

##### Sample Single Ingredient Labels

- user_data/sample_data/pdfs/supplement_labels/SUPP_LABEL__Zinc_Picolinate_30_mg__Thorne.pdf
- user_data/sample_data/pdfs/supplement_labels/SUPP_LABEL__Vitamin_D3_50000_IU__Ortho_Molecular_Products.pdf
- user_data/sample_data/pdfs/supplement_labels/SUPP_LABEL__Fatty15__Fatty15.pdf
- user_data/sample_data/pdfs/supplement_labels/SUPP_LABEL__Scutellaria__Supreme_Nutrition.pdf

##### Sample Multi-Ingredient Labels

- user_data/sample_data/pdfs/supplement_labels/SUPP_LABEL__MethylGenic__Alimentum_Labs.pdf
- user_data/sample_data/pdfs/supplement_labels/SUPP_LABEL__Seriphos__interPlexus.pdf

### 2. Proprietary Blend Labels

Labels with proprietary blends show:
- **Blend Name**: e.g., "Proprietary Blend", "EAA & NA Proprietary Blend"
- **Total Blend Amount**: e.g., "550 mg", "5g"
- **Individual Ingredients**: Listed without individual amounts

#### Sample Proprierty Blend Labels

- user_data/sample_data/pdfs/supplement_labels/SUPP_LABEL__Kalmz__Ver_Vita.pdf
- user_data/sample_data/pdfs/supplement_labels/SUPP_LABEL__Perfect_Amino__Body_Health.pdf
- user_data/sample_data/pdfs/supplement_labels/SUPP_LABEL__KL_Support__CellCore.pdf

### 3. Multi-Section Labels

Complex labels with multiple sections:
- Multiple ingredient tables
- Separate vitamin/mineral sections
- Multiple proprietary blends

#### Sample Complex Multi-Section Labels

- user_data/sample_data/pdfs/supplement_labels/SUPP_LABEL__Green_Vibrance__Vibrant_Health.pdf
- user_data/sample_data/pdfs/supplement_labels/SUPP_LABEL__Fringe_Electrolyte_and_Mineral_Mix__Fringe.pdf
- user_data/sample_data/pdfs/supplement_labels/SUPP_LABEL__Gastro_Digest_II__Ver_Vita.pdf

## Examples

If needed, reference the example files for the corresponding label type (single, multi, proprietary blend, and multi-section ingredient labels).
- The pdf paths are provided. The corresponding json is in user_data/sample_data/extracted/supplement_labels/<filename>.json