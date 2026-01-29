# Bloodwork LabCorp Input Format

## Columns
1. Test
2. Current Result and Flag
3. Previous Result and Date (ignore this column)
4. Units
5. Reference Interval

## Panel Format
- **Sections with table**: Panels are presented in table format
- **Panel names**: Bolded header above the biomarker table. If the panel spans multiple pages, the header will be repeated with "(Cont.)" appended.
- **Biomarkers names**: Column 1 of the table
- **Biomarker values**: Column 2 of the table
- **Ignore label column**: Ignore the "Previous Result and Date" column (column 3)
- **Biomarker units**: Column 4 of the table
- **Biomarker comment**: Some, but not all, biomarkers have comments. If they exist, they start on a new row of the table. Sometimes, they begin with "Please Note:", but they do not have to. They can span multiple columns.
- **Multiple comments**: If a panel has multiple biomarkers with a comment, concatenate them in the "comment" field of that panel's final json output

## Reference
If needed, read:
- user_data/sample_data/pdfs/bloodwork/LABS__2025-02-14__LifeForce.pdf (for LabCorp input pdf example)
- user_data/sample_data/extracted/bloodwork/LABS__2025-02-14__LifeForce.json (for LabCorp output json example)