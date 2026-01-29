# Supplement Label Ingredient Code Normalization

## Types

### Vitamins
| Normalized Code | Label Variations |
|-----------------|------------------|
| VITAMIN_A | Vitamin A, Retinol, Beta-Carotene |
| VITAMIN_B1 | Vitamin B1, Thiamine, Thiamin |
| VITAMIN_B2 | Vitamin B2, Riboflavin, Riboflavin-5-Phosphate |
| VITAMIN_B3 | Vitamin B3, Niacin, Niacinamide, Nicotinamide |
| VITAMIN_B5 | Vitamin B5, Pantothenic Acid, Calcium Pantothenate |
| VITAMIN_B6 | Vitamin B6, Pyridoxine, Pyridoxal-5-Phosphate, P5P |
| VITAMIN_B7 | Biotin, D-Biotin, Vitamin B7 |
| VITAMIN_B9 | Folate, 5-MTHF, Folate/5-MTHF, Methylfolate, Folic Acid |
| VITAMIN_B12 | Vitamin B12, Methylcobalamin, Cyanocobalamin, Cobalamin, Adenosylcobalamin |
| VITAMIN_C | Vitamin C, Ascorbic Acid, Ascorbate |
| VITAMIN_D3 | Vitamin D3, Cholecalciferol, Vitamin D |
| VITAMIN_E | Vitamin E, Tocopherol, Mixed Tocopherols |
| VITAMIN_K | Vitamin K, Vitamin K1, Vitamin K2, Phylloquinone, Menaquinone |

### Minerals
| Normalized Code | Label Variations |
|-----------------|------------------|
| CALCIUM | Calcium |
| MAGNESIUM | Magnesium, Magnesium Glycinate, Mg |
| ZINC | Zinc, Zinc Picolinate, Zinc Citrate, Zinc Bisglycinate |
| IRON | Iron, Ferrous |
| SELENIUM | Selenium, L-Selenomethionine, Selenomethionine |
| COPPER | Copper |
| MANGANESE | Manganese |
| CHROMIUM | Chromium, Chromium Picolinate |
| MOLYBDENUM | Molybdenum |
| IODINE | Iodine, Iodide |
| POTASSIUM | Potassium |
| SODIUM | Sodium |
| PHOSPHORUS | Phosphorus |
| CHLORIDE | Chloride |

### Amino Acids
| Normalized Code | Label Variations |
|-----------------|------------------|
| L_LEUCINE | L-Leucine, Leucine |
| L_ISOLEUCINE | L-Isoleucine, Isoleucine |
| L_VALINE | L-Valine, Valine |
| L_LYSINE | L-Lysine, Lysine HCl, Lysine |
| L_METHIONINE | L-Methionine, Methionine |
| L_PHENYLALANINE | L-Phenylalanine, Phenylalanine |
| L_THREONINE | L-Threonine, Threonine |
| L_TRYPTOPHAN | L-Tryptophan, Tryptophan |
| L_HISTIDINE | L-Histidine, Histidine |
| L_ARGININE | L-Arginine, Arginine |
| L_GLUTAMINE | L-Glutamine, Glutamine |
| L_GLYCINE | Glycine |
| L_PROLINE | L-Proline, Proline |
| L_SERINE | L-Serine, Serine |
| L_TYROSINE | L-Tyrosine, Tyrosine |
| L_CYSTEINE | L-Cysteine, Cysteine, NAC, N-Acetyl Cysteine |
| L_TAURINE | Taurine |
| L_CARNITINE | L-Carnitine, Carnitine, Acetyl-L-Carnitine |

### Herbs & Botanicals
| Normalized Code | Label Variations |
|-----------------|------------------|
| VALERIAN | Valerian, Valeriana officinalis |
| HOPS | Hops, Humulus lupulus |
| PASSIONFLOWER | Passionflower, Passiflora incarnata |
| SCUTELLARIA | Scutellaria, Chinese Skullcap, Scutellaria baicalensis |
| ASHWAGANDHA | Ashwagandha, Withania somnifera |
| RHODIOLA | Rhodiola, Rhodiola rosea |
| GINSENG | Ginseng, Panax ginseng |
| TURMERIC | Turmeric, Curcuma longa, Curcumin |
| GINGER | Ginger, Zingiber officinale |
| MILK_THISTLE | Milk Thistle, Silybum marianum, Silymarin |
| ECHINACEA | Echinacea |
| GINKGO | Ginkgo, Ginkgo biloba |
| SAW_PALMETTO | Saw Palmetto, Serenoa repens |

### Fatty Acids & Lipids
| Normalized Code | Label Variations |
|-----------------|------------------|
| OMEGA_3 | Omega-3, Fish Oil, EPA, DHA |
| EPA | EPA, Eicosapentaenoic Acid |
| DHA | DHA, Docosahexaenoic Acid |
| GLA | GLA, Gamma-Linolenic Acid |
| C15_FATTY_ACID | C15:0, Pentadecanoic Acid, FA15 |
| PHOSPHATIDYLSERINE | Phosphatidylserine, PS |
| PHOSPHATIDYLCHOLINE | Phosphatidylcholine, PC |

### Other Common Ingredients
| Normalized Code | Label Variations |
|-----------------|------------------|
| COENZYME_Q10 | CoQ10, Coenzyme Q10, Ubiquinone, Ubiquinol |
| ALPHA_LIPOIC_ACID | Alpha-Lipoic Acid, ALA, R-Lipoic Acid |
| PROBIOTICS | Probiotics, Lactobacillus, Bifidobacterium |
| DIGESTIVE_ENZYMES | Digestive Enzymes, Protease, Amylase, Lipase |
| COLLAGEN | Collagen, Collagen Peptides |
| GLUTATHIONE | Glutathione, Reduced Glutathione |
| MSM | MSM, Methylsulfonylmethane |
| GLUCOSAMINE | Glucosamine |
| CHONDROITIN | Chondroitin |
| MELATONIN | Melatonin |
| DHEA | DHEA, Dehydroepiandrosterone |
| QUERCETIN | Quercetin |
| RESVERATROL | Resveratrol |

### Other Common (Inactive) Ingredients
| Normalized Code | Label Variations |
|-----------------|------------------|
| MICROCRYSTALLINE_CELLULOSE | Microcrystalline Cellulose, Cellulose |
| HYPROMELLOSE | Hypromellose, HPMC, Vegetable Capsule |
| MAGNESIUM_STEARATE | Magnesium Stearate, Vegetable Stearate |
| SILICON_DIOXIDE | Silicon Dioxide, Silica |
| LEUCINE | Leucine (as flow agent) |
| RICE_FLOUR | Rice Flour |
| GELATIN | Gelatin |
| TITANIUM_DIOXIDE | Titanium Dioxide |
| STEVIA | Stevia, Stevia Extract |
| MONK_FRUIT | Monk Fruit, Luo Han Guo |

## Unlisted Ingredients

For ingredients not listed above, create a code by:
1. Convert to UPPERCASE
2. Replace spaces with underscores
3. Remove parentheses, commas, and special characters
4. For amino acids, keep `L_` prefix (e.g., L-Glutamine → L_GLUTAMINE)
5. For herbs with Latin names, use common name (e.g., Valeriana officinalis → VALERIAN)
6. For proprietary names, create a descriptive code
