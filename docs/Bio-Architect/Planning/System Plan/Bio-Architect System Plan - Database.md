# ARCHITECTURE

- Test Driven Development (TDD). Written to tests/ folder.
- SQLite single database (Claude IS the semantic layer - no graph/vector DB needed)
- Immutable knowledge with supersession (never update, only deprecate and create new)
- Single user

# GOAL
- Emergent Discovery

# TABLES

## DNA
model file: src/databases/dna/models.py

### dna_tests
  id              UUID
  source          TEXT        -- Promethease
  collected_date  DATE        -- When the test was taken
  source_file     TEXT        -- Original filename
  created_at      TIMESTAMP

### snps
  id              UUID
  dna_test_id     UUID FK     -- References dna_tests
  rsid            TEXT        -- Standard identifier (rs12345)
  genotype        TEXT        -- User's result (AA, AG, GG)
  magnitude       REAL        -- Significance/importance (0-10)
  repute          TEXT        -- Classification (good, bad, null)
  gene            TEXT        -- Gene affected (MTHFR, COMT)

## Bloodwork
model file: src/databases/bloodwork/models.py
normalization file: data/public/normalization/biomarker_codes.yaml

### lab_reports
  id              UUID
  lab_provider    TEXT        -- LifeForce, Quest, etc.
  collected_date  DATE        -- When blood was drawn
  source_file     TEXT        -- Original filename
  created_at      TIMESTAMP

### panels
  id              UUID
  lab_report_id   UUID FK     -- References lab_reports
  name            TEXT        -- "Lipid Panel", "CBC With Differential"
  comment         TEXT        -- Lab interpretation notes

### biomarkers
  id              UUID
  panel_id        UUID FK     -- References panels
  code            TEXT        -- BiomarkerCode (HOMOCYSTEINE)
  name            TEXT        -- Display name from lab
  value           REAL        -- The measurement
  unit            TEXT        -- mg/dL, etc.
  reference_low   REAL        -- Lab's range low
  reference_high  REAL        -- Lab's range high
  flag            TEXT        -- BiomarkerFlag enum (high/low/normal/critical high/critical low)

## Supplements
model file: src/databases/supplement/models.py
normalization file: data/public/normalization/ingredient_codes.yaml

### supplement_labels
  id              UUID
  brand           TEXT        -- Manufacturer name
  product_name    TEXT        -- Product name
  form            TEXT        -- capsule, tablet, powder
  serving_size    TEXT        -- "2 capsules", "1 scoop"
  servings_per_container INTEGER
  suggested_use   TEXT        -- Usage instructions
  warnings        TEXT        -- Warning statements (JSON array)
  allergen_info   TEXT        -- Allergen information
  source_file     TEXT        -- Original filename
  created_at      TIMESTAMP

### proprietary_blends
  id              UUID
  supplement_label_id UUID FK -- References supplement_labels
  name            TEXT        -- "Proprietary Blend"
  total_amount    REAL        -- Combined amount (900mg)
  total_unit      TEXT        -- mg

### ingredients
  id              UUID
  supplement_label_id UUID FK -- References supplement_labels (null for blend)
  blend_id        UUID FK     -- References proprietary_blends (null for non-blend)
  type            TEXT        -- active, blend, other
  code            TEXT        -- IngredientCode (validated)
  name            TEXT        -- Display name
  amount          REAL        -- null when undisclosed
  unit            TEXT
  form            TEXT
  percent_dv      REAL        -- only for active type

## Supplement Protocols
model file: src/databases/supplement_protocols/models.py

### supplement_protocols
  id              UUID
  protocol_date   DATE        -- When prescribed
  prescriber      TEXT        -- Healthcare provider
  next_visit      TEXT        -- Follow-up timing
  protein_goal    TEXT        -- e.g. "110g/day"
  lifestyle_notes TEXT        -- JSON array of other notes
  source_file     TEXT        -- Original filename
  created_at      TIMESTAMP

### protocol_supplements
  id              UUID
  protocol_id     UUID FK     -- References supplement_protocols
  supplement_label_id UUID FK -- References supplement_labels (nullable)
  type            TEXT        -- scheduled, own
  name            TEXT        -- Supplement name
  instructions    TEXT        -- Special instructions (scheduled)
  dosage          TEXT        -- e.g. "1/day" (own)
  frequency       TEXT        -- daily, 2x_daily, 2x_week, as_needed
  upon_waking     INTEGER     -- Schedule slots (null for own)
  breakfast       INTEGER
  mid_morning     INTEGER
  lunch           INTEGER
  mid_afternoon   INTEGER
  dinner          INTEGER
  before_sleep    INTEGER

## Knowledge
model file: src/databases/knowledge/models.py

### knowledge
  id              UUID
  type            TEXT        -- insight, recommendation, contraindication, memory
  status          TEXT        -- active, deprecated
  summary         TEXT        -- One-line for retrieval
  content         TEXT        -- Full explanation
  confidence      REAL        -- 0.0-1.0
  supersedes_id   UUID FK     -- References knowledge (what this entry replaces)
  supersession_reason TEXT    -- Why this supersedes the old entry
  created_at      TIMESTAMP

### knowledge_links
  id              UUID
  knowledge_id    UUID FK     -- References knowledge
  link_type       TEXT        -- LinkType enum (snp, biomarker, ingredient, supplement, protocol, knowledge)
  target_id       UUID        -- References specific record in linked table

### knowledge_tags
  id              UUID
  knowledge_id    UUID FK     -- References knowledge
  tag             TEXT        -- Searchable tag

# NORMALIZING CODES

During ingestion, validate synonyms against YAML files and store canonical codes. Reject unknown names (require YAML update first)

YAML files:
  data/public/normalization/biomarker_codes.yaml -> BiomarkerCode
  data/public/normalization/ingredient_codes.yaml -> IngredientCode

# CLI SCRIPTS

Standalone scripts for querying and managing data. Each script is independently executable.
Use `--help` for options, `--json` for structured output.

Claude skill: .claude/skills/bio-architect/SKILL.md
scripts: .claude/skills/bio-architect/scripts

## Available Scripts

### `scripts/dna.py`
Query SNP details, find high-impact genetic variants, explore genes.

### `scripts/bloodwork.py`
View recent lab results, track biomarker trends, find flagged markers.

### `scripts/supplements.py`
Query supplement labels and ingredients.

### `scripts/protocol.py`
View current supplement protocol and history.

### `scripts/knowledge.py`
Query and store knowledge entries.

# EXAMPLES

## New Lab Results

1. PDF -> Claude extracts JSON -> Python ingester validates and inserts rows
2. App gathers: prior values, related knowledge, relevant SNPs, current supplements
3. Claude analyzes all biomarkers, returns multiple knowledge entries:
   ```
   type: insight
   summary: "Homocysteine improving with methylfolate supplementation"
   content: "Dropped from 15.8 to 12.5 over 6 months, correlating with 800mcg methylfolate..."
   confidence: 0.85
   tags: [homocysteine, methylation]
   links: [biomarker:<homocysteine-uuid>, snp:<mthfr-uuid>, ingredient:<methylfolate-uuid>]
   ---
   type: recommendation
   summary: "Consider adding K2 to improve vitamin D utilization"
   content: "Vitamin D at 28 ng/mL, suboptimal despite 2000 IU D3. K2 (MK-7) supports D3 efficacy and calcium metabolism."
   confidence: 0.7
   tags: [recommendation, vitamin-d, vitamin-k]
   links: [biomarker:<vitamin-d-uuid>, ingredient:<d3-uuid>]
   ```
4. App stores all knowledge entries

## New Supplement Protocol

1. PDF -> Claude extracts JSON -> Python ingester validates and inserts rows
2. App gathers: previous protocols, matching supplement labels, relevant SNPs, recent bloodwork
3. Claude analyzes protocol AND identifies gaps, returns multiple knowledge entries:
   ```
   type: insight
   summary: "Protocol adds methylfolate to address MTHFR status"
   content: "New protocol includes 800mcg methylfolate, appropriate for TT genotype..."
   confidence: 0.9
   tags: [protocol, methylation, mthfr]
   links: [protocol:<uuid>, snp:<mthfr-uuid>, ingredient:<methylfolate-uuid>]
   ---
   type: recommendation
   summary: "Consider adding B12 to complement methylfolate"
   content: "Protocol includes methylfolate but no B12. Methylation requires both; B12 deficiency can cause folate trap. Discuss with prescriber."
   confidence: 0.8
   tags: [recommendation, methylation, b12]
   links: [protocol:<uuid>, snp:<mthfr-uuid>]
   ```
4. App stores both knowledge entries

## User Query: Genetic Interactions

User asks: "What genetic interactions do I have?"

1. App gathers: all SNPs, existing knowledge tagged "epistasis"
2. Claude analyzes SNP combinations using training data:
   ```
   type: insight
   summary: "MTHFR + COMT epistasis compounds methylation burden"
   content: "MTHFR C677T TT reduces methylfolate production. COMT V158M AA (slow) reduces methylation clearance. Together: methylation bottleneck at both production and clearance. May need higher methylfolate doses and methylation support."
   confidence: 0.85
   tags: [epistasis, methylation, mthfr, comt]
   links: [snp:<mthfr-uuid>, snp:<comt-uuid>]
   ---
   type: insight
   summary: "Three-way vitamin D resistance pattern"
   content: "VDR Taq TT (reduced receptor sensitivity) + CYP2R1 rs10741657 GG (poor D3 hydroxylation) + GC rs4588 AA (reduced D-binding protein). Triple hit: impaired conversion, transport, AND receptor function. May require significantly higher D3 doses with K2 and magnesium cofactors."
   confidence: 0.8
   tags: [epistasis, vitamin-d, vdr, multi-snp]
   links: [snp:<vdr-uuid>, snp:<cyp2r1-uuid>, snp:<gc-uuid>]
   ```
3. App stores knowledge entries

## User Query: Optimal Workouts

User asks: "What workouts are optimal for my genetics and current health?"

1. App gathers: fitness-related SNPs (ACTN3, PPARGC1A, COL1A1), recent bloodwork (testosterone, cortisol, ferritin, CRP), current protocol, existing fitness knowledge
2. Claude synthesizes across data types:
   ```
   type: recommendation
   summary: "Favor power training over endurance based on ACTN3 status"
   content: "ACTN3 R577X RR indicates fast-twitch muscle fiber dominance. Combined with testosterone at upper range (780 ng/dL), well-suited for strength/power training. Current protocol includes creatine which supports this approach."
   confidence: 0.8
   tags: [fitness, strength, actn3]
   links: [snp:<actn3-uuid>, biomarker:<testosterone-uuid>, ingredient:<creatine-uuid>]
   ---
   type: contraindication
   summary: "Reduce training intensity until ferritin improves"
   content: "Ferritin at 28 ng/mL is suboptimal for athletic performance. High-intensity training increases iron demands. Consider reducing volume until ferritin reaches 50+ ng/mL."
   confidence: 0.75
   tags: [fitness, iron, recovery]
   links: [biomarker:<ferritin-uuid>]
   ```
3. App stores knowledge entries

## User Query: Weekly Nutrition Plan

User asks: "Create an optimal nutrition plan for this week"

1. App gathers: nutrition-related SNPs (APOE, FTO, FADS1, LCT), recent bloodwork (glucose, lipids, HbA1c), current protocol, existing nutrition knowledge
2. Claude synthesizes across data types:
   ```
   type: recommendation
   summary: "Favor Mediterranean-style diet based on APOE E3/E4 status"
   content: "APOE E4 carrier increases cardiovascular risk with high saturated fat. LDL at 142 mg/dL elevated. Prioritize olive oil, fish, nuts. Limit red meat to 1-2x/week."
   confidence: 0.85
   tags: [nutrition, cardiovascular, apoe, lipids]
   links: [snp:<apoe-uuid>, biomarker:<ldl-uuid>]
   ---
   type: recommendation
   summary: "Include omega-3 rich fish 3x/week due to FADS1 status"
   content: "FADS1 rs174546 TT reduces conversion of ALA to EPA/DHA. Protocol includes fish oil but dietary EPA/DHA from salmon, sardines, mackerel provides additional benefit."
   confidence: 0.8
   tags: [nutrition, omega-3, fads1]
   links: [snp:<fads1-uuid>, ingredient:<fish-oil-uuid>]
   ---
   type: contraindication
   summary: "Avoid high-glycemic meals due to impaired glucose control"
   content: "Fasting glucose at 104 mg/dL (prediabetic range). FTO rs9939609 AA increases obesity risk. Prioritize protein + fiber at each meal, avoid refined carbs."
   confidence: 0.85
   tags: [nutrition, glucose, fto]
   links: [snp:<fto-uuid>, biomarker:<glucose-uuid>]
   ```
3. App stores knowledge entries

## User Query: Cognitive Optimization

User asks: "How can I optimize my cognitive performance?"

1. App gathers: cognition-related SNPs (COMT, BDNF, APOE, KIBRA), recent bloodwork (B12, folate, homocysteine, thyroid, vitamin D), current protocol, existing cognition knowledge
2. Claude synthesizes across data types:
   ```
   type: insight
   summary: "COMT + BDNF pattern suggests dopamine sensitivity with reduced plasticity"
   content: "COMT Val158Met AA (slow) increases prefrontal dopamine, enhancing focus but increasing anxiety under stress. BDNF Val66Met AG reduces activity-dependent plasticity. Combined: strong baseline cognition but may struggle with cognitive flexibility under pressure."
   confidence: 0.8
   tags: [cognition, dopamine, comt, bdnf, multi-snp]
   links: [snp:<comt-uuid>, snp:<bdnf-uuid>]
   ---
   type: recommendation
   summary: "Address suboptimal B12 to support methylation and cognition"
   content: "B12 at 320 pg/mL is functional but suboptimal for cognition (target 500+). With COMT slow status, adequate B12 supports dopamine clearance. Consider methylcobalamin given MTHFR status."
   confidence: 0.85
   tags: [cognition, b12, methylation]
   links: [biomarker:<b12-uuid>, snp:<comt-uuid>, snp:<mthfr-uuid>]
   ---
   type: recommendation
   summary: "Consider lion's mane for BDNF support"
   content: "BDNF AG variant reduces neuroplasticity. Lion's mane (Hericium erinaceus) stimulates NGF and BDNF production, potentially compensating for genetic reduction. Protocol currently lacks nootropic support."
   confidence: 0.7
   tags: [cognition, bdnf, nootropics]
   links: [snp:<bdnf-uuid>]
   ```
3. App stores knowledge entries

## User Query: Relationship Tendencies

User asks: "What do my genetics say about relationships and emotional patterns?"

1. App gathers: social/emotional SNPs (OXTR, SLC6A4, COMT, MAO-A), recent bloodwork (testosterone, cortisol, estrogen), existing relationship/emotional knowledge
2. Claude synthesizes across data types:
   ```
   type: insight
   summary: "OXTR + SLC6A4 pattern indicates high emotional sensitivity with strong bonding capacity"
   content: "OXTR rs53576 GG associated with increased empathy and social sensitivity. SLC6A4 (5-HTTLPR) short/short increases emotional reactivity to both positive and negative social cues. Combined: deep capacity for connection but may experience relationship stress intensely."
   confidence: 0.75
   tags: [relationships, oxtr, serotonin, emotional-sensitivity]
   links: [snp:<oxtr-uuid>, snp:<slc6a4-uuid>]
   ---
   type: insight
   summary: "Cortisol pattern suggests chronic stress affecting emotional regulation"
   content: "Morning cortisol at 22 mcg/dL (elevated) with COMT slow status compounds stress response. High baseline stress hormones can increase emotional reactivity and reduce relationship patience."
   confidence: 0.8
   tags: [relationships, stress, cortisol, comt]
   links: [biomarker:<cortisol-uuid>, snp:<comt-uuid>]
   ---
   type: recommendation
   summary: "Stress management practices especially important given genetic profile"
   content: "OXTR GG + SLC6A4 short/short + elevated cortisol creates heightened emotional reactivity. Regular stress management (meditation, breathwork) may help regulate responses. Magnesium in current protocol supports this."
   confidence: 0.75
   tags: [relationships, stress-management, emotional-regulation]
   links: [snp:<oxtr-uuid>, snp:<slc6a4-uuid>, biomarker:<cortisol-uuid>, ingredient:<magnesium-uuid>]
   ```
3. App stores knowledge entries

## User Query: Spiritual Practice Optimization

User asks: "What practices might resonate with my biology?"

1. App gathers: consciousness-related SNPs (DRD4, 5-HT2A, COMT), recent bloodwork (cortisol, vitamin D, magnesium), current protocol, existing spirituality/mindfulness knowledge
2. Claude synthesizes across data types:
   ```
   type: insight
   summary: "DRD4 7R+ suggests openness to novel experiences and altered states"
   content: "DRD4 7-repeat allele associated with novelty-seeking and openness to experience. Combined with 5-HT2A rs6313 CC (increased receptor density), may have heightened responsiveness to contemplative practices, breathwork, or flow states."
   confidence: 0.7
   tags: [spirituality, consciousness, drd4, serotonin]
   links: [snp:<drd4-uuid>, snp:<5ht2a-uuid>]
   ---
   type: recommendation
   summary: "Morning practice may be more effective given cortisol rhythm"
   content: "Elevated morning cortisol (22 mcg/dL) indicates strong circadian activation. Contemplative practice during this window may leverage natural alertness. Evening practice may help normalize cortisol before sleep."
   confidence: 0.7
   tags: [spirituality, cortisol, circadian, meditation]
   links: [biomarker:<cortisol-uuid>]
   ---
   type: insight
   summary: "COMT slow status may enhance meditation depth but increase overthinking"
   content: "COMT AA (slow) maintains higher prefrontal dopamine, supporting sustained attention in meditation. However, same variant can increase rumination. Practices emphasizing present-moment awareness (vs. analytical meditation) may be more beneficial."
   confidence: 0.75
   tags: [spirituality, meditation, comt, dopamine]
   links: [snp:<comt-uuid>]
   ```
3. App stores knowledge entries

## Knowledge Supersession

New bloodwork shows homocysteine normalized. Previous insight no longer applies.

1. App gathers: new biomarker values, existing knowledge linked to homocysteine
2. Claude identifies outdated insight and creates superseding entry:
   ```
   type: insight
   summary: "Homocysteine now optimal - methylation support effective"
   content: "Homocysteine at 8.2 umol/L (previously 12.5). Methylfolate + B12 supplementation has normalized levels. Continue current protocol."
   confidence: 0.9
   tags: [homocysteine, methylation]
   links: [biomarker:<homocysteine-uuid>, snp:<mthfr-uuid>]
   supersedes_id: <previous-homocysteine-insight-uuid>
   supersession_reason: "New bloodwork shows homocysteine normalized from 12.5 to 8.2. Previous concern about elevated levels no longer applies."
   ```
3. App stores new entry and marks old entry status = deprecated