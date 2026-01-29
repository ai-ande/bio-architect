# Bloodwork Quest Input Format

## Columns
1. Test Name
2. In Range
3. Out of Range
4. Reference Range
5. Lab (ignore this column)

## Panel Format
- **Indentation based**: Panels are separated from markers using indents. Multi-line wrapped text is possible. If the text wraps, it will be indented one level up.
- **Panel names**: Start on level 0 and do not wrap. They end when you encounter a newline.
- **Biomarkers names**: Start on level 1. and end when you encounter a numerical value or "SEE NOTE:"
- **Panel comment**: Some, but not all, panels have comments. If they exist, they begin on level 2 and can be one or more paragraphs long. If paragraphs exist, they are separated by a blank line.
- **Ignore label column**: Ignore the "Lab" column

## Reference
If needed, read user_data/sample_data/pdfs/bloodwork/LABS__2025-11-16__LifeForce.pdf (for Quest input pdf example)
If needed, read user_data/sample_data/extracted/bloodwork/LABS__2025-11-16__LifeForce.json (for Quest output json example)