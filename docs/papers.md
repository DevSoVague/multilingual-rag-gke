# Paper corpus

No PDFs are committed to this repo (they are third-party, copyrighted works). Bring your own PDFs and upload them through the **Upload & Index** tab, or use one of the options below.

## Option A: open-access sample corpus (script)

`scripts/download_papers.sh` fetches open-access PDFs from PubMed Central (clinical nutrition topics) into `./papers/` (git-ignored). Then check them with:

```bash
bash scripts/download_papers.sh
python scripts/validate_papers.py --dir papers
```

Some PMC links may have moved since the script was written; failed downloads are reported and can be fetched by hand.

Note: the app's domain labels are `AI / ML`, `Security`, and `Other`, so this corpus will be tagged `Other` unless you edit `PAPER_TYPES` in `indexer.py`.

| Group | Saved as | URL |
|---|---|---|
| preoperative | `PRE_01_nutritional_assessment_surgical.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6723589/pdf/nutrients-11-01824.pdf |
| preoperative | `PRE_02_carbohydrate_loading_insulin.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4858086/pdf/nutrients-08-00260.pdf |
| preoperative | `PRE_03_oral_nutritional_supplements.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5372921/pdf/jpen.2016.21.6.596.pdf |
| preoperative | `PRE_04_immunonutrition_arginine_omega3.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6566799/pdf/nutrients-11-01235.pdf |
| preoperative | `PRE_05_albumin_surgical_outcomes.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5553554/pdf/nihms889368.pdf |
| preoperative | `PRE_06_malnutrition_screening_tools.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6470918/pdf/nutrients-11-00700.pdf |
| preoperative | `PRE_07_protein_supplementation_muscle.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6722943/pdf/nutrients-11-01912.pdf |
| preoperative | `PRE_08_omega3_preoperative_inflammation.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5486608/pdf/nutrients-09-00631.pdf |
| preoperative | `PRE_09_revised_fasting_guidelines.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6723629/pdf/nutrients-11-01868.pdf |
| preoperative | `PRE_10_nutritional_risk_index_mortality.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6049644/pdf/nutrients-10-00828.pdf |
| preoperative | `PRE_11_ERAS_preoperative_nutrition.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5514597/pdf/wjs-41-2065.pdf |
| preoperative | `PRE_12_zinc_wound_healing.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793244/pdf/nutrients-10-00016.pdf |
| preoperative | `PRE_13_preoperative_weight_loss_bariatric.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6723601/pdf/nutrients-11-01876.pdf |
| preoperative | `PRE_14_enteral_vs_parenteral_preoperative.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4932572/pdf/nutrients-08-00355.pdf |
| preoperative | `PRE_15_vitamin_d_surgical_infection.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5452233/pdf/nutrients-09-00515.pdf |
| preoperative | `PRE_16_prehabilitation_colorectal_cancer.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6723570/pdf/nutrients-11-01823.pdf |
| preoperative | `PRE_17_mini_nutritional_assessment_elderly.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6470946/pdf/nutrients-11-00780.pdf |
| preoperative | `PRE_18_gut_microbiome_dietary_intervention.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6566586/pdf/nutrients-11-01263.pdf |
| preoperative | `PRE_19_high_protein_cardiac_surgery.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793259/pdf/nutrients-10-00021.pdf |
| preoperative | `PRE_20_mediterranean_diet_surgical_risk.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6566764/pdf/nutrients-11-01227.pdf |
| postoperative | `POST_01_early_enteral_nutrition_infection.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4848681/pdf/nutrients-08-00216.pdf |
| postoperative | `POST_02_postoperative_protein_requirements.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6723571/pdf/nutrients-11-01817.pdf |
| postoperative | `POST_03_nutrition_icu_postsurgery.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793260/pdf/nutrients-10-00001.pdf |
| postoperative | `POST_04_glutamine_postoperative_recovery.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6357022/pdf/nutrients-11-00171.pdf |
| postoperative | `POST_05_parenteral_nutrition_indications.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5452205/pdf/nutrients-09-00497.pdf |
| postoperative | `POST_06_omega3_postoperative_inflammation.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793293/pdf/nutrients-10-00064.pdf |
| postoperative | `POST_07_nutrition_after_bariatric_surgery.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6567160/pdf/nutrients-11-01315.pdf |
| postoperative | `POST_08_vitamin_c_wound_healing_review.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5579659/pdf/nutrients-09-00866.pdf |
| postoperative | `POST_09_refeeding_syndrome.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6722977/pdf/nutrients-11-01990.pdf |
| postoperative | `POST_10_nutrition_after_knee_replacement.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6470907/pdf/nutrients-11-00716.pdf |
| postoperative | `POST_11_post_gastrectomy_deficiencies.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6357114/pdf/nutrients-11-00074.pdf |
| postoperative | `POST_12_micronutrient_colorectal_surgery.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6566795/pdf/nutrients-11-01241.pdf |
| postoperative | `POST_13_sarcopenia_nutrition_intervention.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6723603/pdf/nutrients-11-01882.pdf |
| postoperative | `POST_14_dietary_fiber_bowel_function.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793267/pdf/nutrients-10-00016.pdf |
| postoperative | `POST_15_bariatric_micronutrient_deficiency.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5452232/pdf/nutrients-09-00519.pdf |
| postoperative | `POST_16_postoperative_nausea_dietary.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6049631/pdf/nutrients-10-00844.pdf |
| postoperative | `POST_17_nutrition_pancreatic_surgery.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5486577/pdf/nutrients-09-00642.pdf |
| postoperative | `POST_18_probiotics_colorectal_gut.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793302/pdf/nutrients-10-00080.pdf |
| postoperative | `POST_19_iron_deficiency_oral_iv.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6357086/pdf/nutrients-11-00125.pdf |
| postoperative | `POST_20_bcaa_liver_resection.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5579643/pdf/nutrients-09-00901.pdf |
| general | `GEN_01_mediterranean_diet_cardiovascular.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793283/pdf/nutrients-10-00010.pdf |
| general | `GEN_02_dietary_protein_muscle_lifespan.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6566799/pdf/nutrients-11-01235.pdf |
| general | `GEN_03_ultra_processed_food_mortality.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6538975/pdf/1900591.pdf |
| general | `GEN_04_gut_microbiome_dietary_fiber.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5350494/pdf/nutrients-09-00220.pdf |
| general | `GEN_05_omega3_cognitive_decline.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793271/pdf/nutrients-10-00028.pdf |
| general | `GEN_06_dietary_patterns_diabetes_meta.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6723580/pdf/nutrients-11-01852.pdf |
| general | `GEN_07_vitamin_d_musculoskeletal.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6566612/pdf/nutrients-11-01297.pdf |
| general | `GEN_08_caloric_restriction_longevity.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6357015/pdf/nutrients-11-00152.pdf |
| general | `GEN_09_plant_based_diet_colorectal_cancer.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793313/pdf/nutrients-10-00081.pdf |
| general | `GEN_10_sugar_beverages_pediatric_obesity.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6566583/pdf/nutrients-11-01246.pdf |
| general | `GEN_11_iron_deficiency_anemia_dietary.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5452213/pdf/nutrients-09-00510.pdf |
| general | `GEN_12_intermittent_fasting_metabolic.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6357517/pdf/nutrients-11-00434.pdf |
| general | `GEN_13_dietary_sodium_hypertension.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793258/pdf/nutrients-10-00002.pdf |
| general | `GEN_14_folate_neural_tube_defect.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6470948/pdf/nutrients-11-00784.pdf |
| general | `GEN_15_antioxidants_oxidative_stress.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6566740/pdf/nutrients-11-01186.pdf |
| general | `GEN_16_calcium_dairy_bone_density.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5579651/pdf/nutrients-09-00874.pdf |
| general | `GEN_17_DASH_diet_blood_pressure_rct.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793299/pdf/nutrients-10-00057.pdf |
| general | `GEN_18_food_insecurity_chronic_disease.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6723591/pdf/nutrients-11-01838.pdf |
| general | `GEN_19_breakfast_cardiometabolic_health.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6566577/pdf/nutrients-11-01215.pdf |
| general | `GEN_20_probiotics_immune_healthy_adults.pdf` | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793260/pdf/nutrients-10-00009.pdf |

## Option B: the AI/ML corpus used for the saved benchmark

The benchmark in `benchmarks/` was run on a corpus of AI/ML papers that included BERT, LLaMA 2, and LoRA (file names `AI_02_BERT.pdf`, `AI_04_LLaMA_2.pdf`, `AI_06_LoRA.pdf`). The full list was not preserved. All three are on arXiv:

- BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding: https://arxiv.org/abs/1810.04805
- Llama 2: Open Foundation and Fine-Tuned Chat Models: https://arxiv.org/abs/2307.09288
- LoRA: Low-Rank Adaptation of Large Language Models: https://arxiv.org/abs/2106.09685
