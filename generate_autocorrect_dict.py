"""Generate app/src/main/java/com/rankwarz/edulabsrtm/AiAutoCorrect.kt

Dictionary = curated medical/English base list + topic/subject words from
question_bank_stats.json (lowercased, alphanumeric-only, 3-24 chars).
"""
import json
import re

with open("question_bank_stats.json", encoding="utf-8") as f:
    stats = json.load(f)

words = set()

def add_word(w: str):
    w = w.strip().lower()
    w = re.sub(r"[^a-z]", "", w)
    if 3 <= len(w) <= 24:
        words.add(w)

def add_text(t: str):
    for part in re.split(r"[^a-z]+", t.lower()):
        if 3 <= len(part) <= 24:
            words.add(part)

# Topics from the stats
for t in stats.get("neet_pg_topics", []) + stats.get("neet_ug_topics", []):
    if t.get("topic"):
        add_text(str(t["topic"]))
for subj in stats.get("per_subject_summary", []):
    add_text(str(subj.get("subject", "")))
    for tt in subj.get("top_topics", []):
        # "Topic (1234)" -> "Topic"
        add_text(re.sub(r"\s*\(\d+\)\s*$", "", str(tt)))

# Curated base list: connectors, question words, common verbs/adjectives
BASE = """
the and for with about from this that these those have has had was were will would can could should
shouldnt cant wont dont doesnt is are am be been being do does did not no yes please tell explain
describe define discuss list search find look get need show fetch give write draft create make build
generate produce summarize summarise elaborate compare contrast difference between vs what how why
when where which who whom whose because therefore however also but or if then than very much more
most some any each every other another first last next second treatment causes symptoms diagnosis
management prevention prognosis etiology pathogenesis pathology physiology anatomy biochemistry
microbiology pharmacology medicine surgery pediatrics obstetrics gynecology ophthalmology otolaryngology
orthopedics psychiatry neurology cardiology pulmonology nephrology gastroenterology endocrinology
dermatology oncology hematology immunology rheumatology infectious radiology anesthesia emergency
cataract glaucoma cataracts glaucomatous retina retinal cornea corneal lens optic nerve blindness
vision visual acuity myopia hyperopia presbyopia strabismus uveitis conjunctivitis keratitis
diabetes diabetic hypertension hypertensive hypotension asthma bronchial bronchitis pneumonia
tuberculosis typhoid malaria dengue chikungunya anemia anemia anaemia leukemia lymphoma carcinoma
tumor tumour cancer malignant benign metastasis abscess sepsis septic infection infectious bacteria
bacterial virus viral fungal fungal protozoa parasite parasitic worm helminth fever pyrexia pain
ache headache migraine epilepsy seizure convulsion stroke paralysis palsy parkinson alzheimer
dementia schizophrenia depression anxiety bipolar insomnia apnea thyroid hypothyroid hyperthyroid
goiter goitre iodine cretinism jaundice hepatitis cirrhosis liver hepatic renal kidney nephrotic
nephritis uremia dialysis stones calculus cholelithiasis gallstone peptic ulcer gastric duodenal
heart cardiac coronary myocardial infarction ischemia angina arrhythmia fibrillation hypertension
edema oedema ascites cirrhosis pancreatitis gallbladder spleen splenic appendix appendicitis hernia
hemorrhoids piles fistula fissure fracture dislocation sprain strain ligament tendon arthritis
osteoarthritis rheumatoid gout osteoporosis scoliosis kyphosis lordosis disc prolapse sciatica
proteinuria hematuria glycosuria polyuria oliguria anuria incontinence retention infection
antibiotics antibiotic analgesic antipyretic antiemetic antihypertensive diuretic insulin
metformin sulfonylurea statin aspirin paracetamol ibuprofen penicillin amoxicillin ciprofloxacin
azithromycin ceftriaxone metronidazole albendazole ivermectin artesunate quinine chloroquine
vaccine vaccination immunization immunity antibody antigen serum plasma platelet hemoglobin
haemoglobin red blood white cell count smear culture sensitivity biopsy histology cytology
radiology xray x-ray ultrasound ct mri scan imaging endoscopy colonoscopy bronchoscopy
laparoscopy hysterectomy appendectomy cholecystectomy splenectomy nephrectomy transplant graft
donor recipient prognosis survival mortality morbidity incidence prevalence epidemiology outbreak
pandemic epidemic endemic sporadic quarantine isolation sterilization disinfection antisepsis
aseptic sepsis shock hypovolemic cardiogenic anaphylactic allergic allergen anaphylaxis
respiratory ventilation oxygen saturation hypoxia hypercapnia intubation tracheostomy
cardiac arrest resuscitation cpr defibrillation pacemaker stent bypass angioplasty catheter
intravenous subcutaneous intramuscular oral topical inhaled nebulizer syrup tablet capsule
injection infusion transfusion donor blood group rhesus compatib compatibility crossmatch
pregnancy pregnant antenatal postnatal neonatal infant child adolescent geriatric maternal
fetal foetus placenta umbilical cord labor labour delivery cesarean caesarean episiotomy
miscarriage abortion ectopic infertility contraceptive contraception ovulation menstruation
menopause amenorrhea dysmenorrhea endometriosis polycystic ovarian pcos fibroid cervical
uterine ovarian vaginal genital herpes gonorrhea syphilis chlamydia hiv aids retrovirus
hepatitis viral fungal candidiasis ringworm tinea scabies pediculosis dermatitis eczema
psoriasis acne rosacea urticaria hives vitiligo alopecia cellulitis gangrene necrosis
ischemia ischaemia infarction embolism thrombus thrombosis embolism varicose aneurysm
aortic dissection pericarditis myocarditis endocarditis valvular stenosis regurgitation
prolapse murmur cyanosis clubbing jaundice icterus pallor flushing dehydration electrolyte
sodium potassium calcium magnesium chloride bicarbonate acidosis alkalosis ketoacidosis
uraemia uremia azotemia creatinine urea bilirubin transaminase alkaline phosphatase
albumin globulin total protein lipid cholesterol triglyceride ldl hdl glucose hba1c
fructosamine glycosylated urine analysis routine microscopy pus cells epithelial casts
crystals uric acid ammonia phenylketonuria galactosemia glycogen storage mitochondrial
chromosome gene mutation inheritance autosomal dominant recessive x-linked carrier
genetic prenatal screening amniocentesis chorionic villus karyotype genotype phenotype
sickle thalassemia thalassaemia hemophilia haemophilia von willebrand factor deficiency
protein c s antithrombin heparin warfarin anticoagulant antiplatelet thrombolytic
prothrombin bleeding clotting coagulation fibrinogen platelet transfusion splenectomy
bone marrow transplant stem cell cord blood gene therapy regenerative prosthetics
orthosis brace cast traction immobilization reduction fixation osteotomy arthroscopy
prosthesis implant titanium stainless screw plate rod k-wire pin external fixator
fracture union nonunion malunion delayed avascular necrosis compartment syndrome
crush injury burn scald frostbite hypothermia hyperthermia heatstroke sunstroke
electrical lightning chemical ingestion poisoning overdose antidote activated charcoal
gastric lavage emesis induce emetic syrup ipecac naloxone flumazenil acetylcysteine
snake bite scorpion spider antivenom rabies dog bite tetanus toxoid immunoglobulin
diphtheria pertussis whooping measles mumps rubella varicella chickenpox smallpox
polio poliomyelitis influenza flu covid coronavirus sars mers zika ebola dengue
yellow fever plague cholera typhus leprosy trachoma onchocerciasis filariasis
schistosomiasis leishmaniasis kala-azar trypanosomiasis giardiasis amoebiasis
amebiasis dysentery salmonella shigella campylobacter e.coli escherichia klebsiella
pseudomonas acinetobacter staphylococcus streptococcus pneumococcus meningococcus
haemophilus legionella brucella leptospira rickettsia chlamydia mycoplasma ureaplasma
questions symptoms diseases patients cells drugs causes findings results studies treatments
types levels cases groups signs disorders syndromes children adults women men people data mice
feet teeth criteria indices media topics papers theses bacteria fungi nuclei vertebrae
thesis synopsis dissertation abstract analyze analysis compare contrast difference summary
overview outline describe overview diagnosis diagnostic investigation investigative
"""

for w in BASE.split():
    add_word(w)

sorted_words = sorted(words)
print(f"dictionary words: {len(sorted_words)}")

with open("app/src/main/java/com/rankwarz/edulabsrtm/AiAutoCorrect.kt", "w", encoding="utf-8") as f:
    f.write("""package com.rankwarz.edulabsrtm

/**
 * Lightweight auto-correct for chat queries, backed by a medical + English dictionary
 * (generated from the question-bank inventory plus a curated base list).
 *
 * Only rewrites a word when the closest dictionary match is clearly better, so it
 * never mangles correctly spelled words, numbers, URLs or pasted abstracts.
 */
object AiAutoCorrect {

    private val DICT: Set<String> = setOf(
""")
    for i in range(0, len(sorted_words), 8):
        chunk = sorted_words[i:i+8]
        f.write("        " + ", ".join(f'"{w}"' for w in chunk) + ",\n")
    f.write("""    )

    /** Long pasted text (abstracts, articles) is never rewritten. */
    private const val MAX_CORRECT_LENGTH = 600

    /** Corrects whole sentences word-by-word; preserves punctuation, numbers and casing. */
    fun correct(text: String): String {
        if (text.length > MAX_CORRECT_LENGTH) return text
        return text.split(Regex("\\\\s+")).joinToString(" ") { token -> correctWord(token) }
    }

    private fun correctWord(token: String): String {
        if (token.length < 4 || token.length > 20) return token
        val lower = token.lowercase().trim('"', '\\'', '(', ')', ',', '.', ':', ';', '!', '?', '-', '_')
        if (lower.length < 4 || lower.length > 20) return token
        if (!lower.all { it.isLetter() }) return token
        if (lower in DICT) return token
        // Accept regular plurals of known words (topics -> topic, cataracts -> cataract).
        if (lower.endsWith("es") && lower.dropLast(2) in DICT) return token
        if (lower.endsWith("s") && lower.dropLast(1) in DICT) return token

        var best: String? = null
        var bestDist = Int.MAX_VALUE
        for (word in DICT) {
            if (kotlin.math.abs(word.length - lower.length) > 2) continue
            val d = levenshtein(lower, word, 2)
            if (d in 1..bestDist) {
                if (d < bestDist || (d == bestDist && best != null && word.length < best!!.length)) {
                    best = word
                    bestDist = d
                }
            }
        }
        val corrected = best ?: return token
        val accept = bestDist == 1 ||
            (bestDist == 2 && lower.length >= 7 && lower.startsWith(corrected.take(2)))
        if (!accept) return token

        return if (token.firstOrNull()?.isUpperCase() == true) {
            corrected.replaceFirstChar { it.uppercase() }
        } else {
            corrected
        }
    }

    /** Classic Levenshtein distance with an early cutoff (stops at [maxDist]+1). */
    private fun levenshtein(a: String, b: String, maxDist: Int): Int {
        if (kotlin.math.abs(a.length - b.length) > maxDist) return maxDist + 1
        val dp = IntArray(b.length + 1) { it }
        for (i in 1..a.length) {
            var prev = dp[0]
            dp[0] = i
            var rowMin = dp[0]
            for (j in 1..b.length) {
                val tmp = dp[j]
                dp[j] = minOf(
                    dp[j] + 1,
                    dp[j - 1] + 1,
                    prev + if (a[i - 1] == b[j - 1]) 0 else 1
                )
                if (dp[j] < rowMin) rowMin = dp[j]
                prev = tmp
            }
            if (rowMin > maxDist) return maxDist + 1
        }
        return dp[b.length]
    }
}
""")
print("written AiAutoCorrect.kt")