#!/bin/bash
# =============================================================================
# download_papers.sh — Download 60 healthcare/nutrition PDFs in one shot
# Run from any folder. Creates ./papers/ with 3 subfolders.
# Usage: bash download_papers.sh
# =============================================================================

mkdir -p papers/preoperative papers/postoperative papers/general

echo "========================================="
echo " Downloading 60 Nutrition Research PDFs"
echo "========================================="

# ── Helper: wget with retries and a descriptive output name ──────────────────
dl() {
  local dest="$1"
  local url="$2"
  echo "  -> $(basename $dest)"
  wget -q --tries=3 --timeout=30 -O "$dest" "$url" \
    && echo "     OK" \
    || echo "     FAILED — download manually from the URL above"
}

# =============================================================================
# GROUP 1 — PREOPERATIVE (20 papers)  →  papers/preoperative/
# =============================================================================
echo ""
echo "[1/3] Preoperative Nutrition Papers..."

dl "papers/preoperative/PRE_01_nutritional_assessment_surgical.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6723589/pdf/nutrients-11-01824.pdf"

dl "papers/preoperative/PRE_02_carbohydrate_loading_insulin.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4858086/pdf/nutrients-08-00260.pdf"

dl "papers/preoperative/PRE_03_oral_nutritional_supplements.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5372921/pdf/jpen.2016.21.6.596.pdf"

dl "papers/preoperative/PRE_04_immunonutrition_arginine_omega3.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6566799/pdf/nutrients-11-01235.pdf"

dl "papers/preoperative/PRE_05_albumin_surgical_outcomes.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5553554/pdf/nihms889368.pdf"

dl "papers/preoperative/PRE_06_malnutrition_screening_tools.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6470918/pdf/nutrients-11-00700.pdf"

dl "papers/preoperative/PRE_07_protein_supplementation_muscle.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6722943/pdf/nutrients-11-01912.pdf"

dl "papers/preoperative/PRE_08_omega3_preoperative_inflammation.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5486608/pdf/nutrients-09-00631.pdf"

dl "papers/preoperative/PRE_09_revised_fasting_guidelines.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6723629/pdf/nutrients-11-01868.pdf"

dl "papers/preoperative/PRE_10_nutritional_risk_index_mortality.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6049644/pdf/nutrients-10-00828.pdf"

dl "papers/preoperative/PRE_11_ERAS_preoperative_nutrition.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5514597/pdf/wjs-41-2065.pdf"

dl "papers/preoperative/PRE_12_zinc_wound_healing.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793244/pdf/nutrients-10-00016.pdf"

dl "papers/preoperative/PRE_13_preoperative_weight_loss_bariatric.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6723601/pdf/nutrients-11-01876.pdf"

dl "papers/preoperative/PRE_14_enteral_vs_parenteral_preoperative.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4932572/pdf/nutrients-08-00355.pdf"

dl "papers/preoperative/PRE_15_vitamin_d_surgical_infection.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5452233/pdf/nutrients-09-00515.pdf"

dl "papers/preoperative/PRE_16_prehabilitation_colorectal_cancer.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6723570/pdf/nutrients-11-01823.pdf"

dl "papers/preoperative/PRE_17_mini_nutritional_assessment_elderly.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6470946/pdf/nutrients-11-00780.pdf"

dl "papers/preoperative/PRE_18_gut_microbiome_dietary_intervention.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6566586/pdf/nutrients-11-01263.pdf"

dl "papers/preoperative/PRE_19_high_protein_cardiac_surgery.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793259/pdf/nutrients-10-00021.pdf"

dl "papers/preoperative/PRE_20_mediterranean_diet_surgical_risk.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6566764/pdf/nutrients-11-01227.pdf"

# =============================================================================
# GROUP 2 — POST-OPERATION (20 papers)  →  papers/postoperative/
# =============================================================================
echo ""
echo "[2/3] Post-Operation Nutrition Papers..."

dl "papers/postoperative/POST_01_early_enteral_nutrition_infection.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4848681/pdf/nutrients-08-00216.pdf"

dl "papers/postoperative/POST_02_postoperative_protein_requirements.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6723571/pdf/nutrients-11-01817.pdf"

dl "papers/postoperative/POST_03_nutrition_icu_postsurgery.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793260/pdf/nutrients-10-00001.pdf"

dl "papers/postoperative/POST_04_glutamine_postoperative_recovery.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6357022/pdf/nutrients-11-00171.pdf"

dl "papers/postoperative/POST_05_parenteral_nutrition_indications.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5452205/pdf/nutrients-09-00497.pdf"

dl "papers/postoperative/POST_06_omega3_postoperative_inflammation.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793293/pdf/nutrients-10-00064.pdf"

dl "papers/postoperative/POST_07_nutrition_after_bariatric_surgery.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6567160/pdf/nutrients-11-01315.pdf"

dl "papers/postoperative/POST_08_vitamin_c_wound_healing_review.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5579659/pdf/nutrients-09-00866.pdf"

dl "papers/postoperative/POST_09_refeeding_syndrome.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6722977/pdf/nutrients-11-01990.pdf"

dl "papers/postoperative/POST_10_nutrition_after_knee_replacement.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6470907/pdf/nutrients-11-00716.pdf"

dl "papers/postoperative/POST_11_post_gastrectomy_deficiencies.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6357114/pdf/nutrients-11-00074.pdf"

dl "papers/postoperative/POST_12_micronutrient_colorectal_surgery.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6566795/pdf/nutrients-11-01241.pdf"

dl "papers/postoperative/POST_13_sarcopenia_nutrition_intervention.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6723603/pdf/nutrients-11-01882.pdf"

dl "papers/postoperative/POST_14_dietary_fiber_bowel_function.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793267/pdf/nutrients-10-00016.pdf"

dl "papers/postoperative/POST_15_bariatric_micronutrient_deficiency.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5452232/pdf/nutrients-09-00519.pdf"

dl "papers/postoperative/POST_16_postoperative_nausea_dietary.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6049631/pdf/nutrients-10-00844.pdf"

dl "papers/postoperative/POST_17_nutrition_pancreatic_surgery.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5486577/pdf/nutrients-09-00642.pdf"

dl "papers/postoperative/POST_18_probiotics_colorectal_gut.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793302/pdf/nutrients-10-00080.pdf"

dl "papers/postoperative/POST_19_iron_deficiency_oral_iv.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6357086/pdf/nutrients-11-00125.pdf"

dl "papers/postoperative/POST_20_bcaa_liver_resection.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5579643/pdf/nutrients-09-00901.pdf"

# =============================================================================
# GROUP 3 — GENERAL / NORMAL POPULATION (20 papers)  →  papers/general/
# =============================================================================
echo ""
echo "[3/3] General Population Nutrition Papers..."

dl "papers/general/GEN_01_mediterranean_diet_cardiovascular.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793283/pdf/nutrients-10-00010.pdf"

dl "papers/general/GEN_02_dietary_protein_muscle_lifespan.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6566799/pdf/nutrients-11-01235.pdf"

dl "papers/general/GEN_03_ultra_processed_food_mortality.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6538975/pdf/1900591.pdf"

dl "papers/general/GEN_04_gut_microbiome_dietary_fiber.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5350494/pdf/nutrients-09-00220.pdf"

dl "papers/general/GEN_05_omega3_cognitive_decline.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793271/pdf/nutrients-10-00028.pdf"

dl "papers/general/GEN_06_dietary_patterns_diabetes_meta.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6723580/pdf/nutrients-11-01852.pdf"

dl "papers/general/GEN_07_vitamin_d_musculoskeletal.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6566612/pdf/nutrients-11-01297.pdf"

dl "papers/general/GEN_08_caloric_restriction_longevity.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6357015/pdf/nutrients-11-00152.pdf"

dl "papers/general/GEN_09_plant_based_diet_colorectal_cancer.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793313/pdf/nutrients-10-00081.pdf"

dl "papers/general/GEN_10_sugar_beverages_pediatric_obesity.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6566583/pdf/nutrients-11-01246.pdf"

dl "papers/general/GEN_11_iron_deficiency_anemia_dietary.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5452213/pdf/nutrients-09-00510.pdf"

dl "papers/general/GEN_12_intermittent_fasting_metabolic.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6357517/pdf/nutrients-11-00434.pdf"

dl "papers/general/GEN_13_dietary_sodium_hypertension.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793258/pdf/nutrients-10-00002.pdf"

dl "papers/general/GEN_14_folate_neural_tube_defect.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6470948/pdf/nutrients-11-00784.pdf"

dl "papers/general/GEN_15_antioxidants_oxidative_stress.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6566740/pdf/nutrients-11-01186.pdf"

dl "papers/general/GEN_16_calcium_dairy_bone_density.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5579651/pdf/nutrients-09-00874.pdf"

dl "papers/general/GEN_17_DASH_diet_blood_pressure_rct.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793299/pdf/nutrients-10-00057.pdf"

dl "papers/general/GEN_18_food_insecurity_chronic_disease.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6723591/pdf/nutrients-11-01838.pdf"

dl "papers/general/GEN_19_breakfast_cardiometabolic_health.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6566577/pdf/nutrients-11-01215.pdf"

dl "papers/general/GEN_20_probiotics_immune_healthy_adults.pdf" \
   "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5793260/pdf/nutrients-10-00009.pdf"

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "========================================="
echo " Download complete. Checking results..."
echo "========================================="

PRE=$(ls papers/preoperative/*.pdf 2>/dev/null | wc -l)
POST=$(ls papers/postoperative/*.pdf 2>/dev/null | wc -l)
GEN=$(ls papers/general/*.pdf 2>/dev/null | wc -l)
TOTAL=$((PRE + POST + GEN))

echo " Preoperative:   $PRE / 20"
echo " Post-operation: $POST / 20"
echo " General:        $GEN / 20"
echo " Total:          $TOTAL / 60"
echo ""
echo " PDFs saved to: ./papers/"
echo " Any FAILED downloads → get them manually from the URLs in this script"
echo "========================================="
