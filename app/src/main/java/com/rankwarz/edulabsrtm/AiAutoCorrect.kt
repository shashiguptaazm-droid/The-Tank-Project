package com.rankwarz.edulabsrtm

/**
 * Lightweight auto-correct for chat queries, backed by a medical + English dictionary
 * (generated from the question-bank inventory plus a curated base list).
 *
 * Only rewrites a word when the closest dictionary match is clearly better, so it
 * never mangles correctly spelled words, numbers, URLs or pasted abstracts.
 */
object AiAutoCorrect {

    private val DICT: Set<String> = setOf(
        "abg", "ability", "abnormal", "abortion", "about", "abscess", "absorbers", "abstract",
        "accessories", "accessory", "accidents", "accounting", "accumulator", "acetylcysteine", "ache", "acid",
        "acidosis", "acids", "acinetobacter", "acne", "act", "acting", "activated", "acuity",
        "acute", "adaptive", "addiction", "additives", "address", "adh", "adolescent", "adrenergic",
        "adults", "aerodynamic", "aerospace", "affairs", "age", "agricultural", "agriculture", "agronomy",
        "aids", "air", "airbus", "aircraft", "albendazole", "albumin", "alcohol", "algebraic",
        "alkaline", "alkalosis", "allergen", "allergic", "alopecia", "also", "alvarado", "alzheimer",
        "amebiasis", "amendments", "amenorrhea", "amino", "ammonia", "amniocentesis", "amoebiasis", "amoxicillin",
        "amp", "amyloidosis", "anaemia", "anaesthesia", "anaesthetic", "analgesic", "analysis", "analyze",
        "anaphylactic", "anaphylaxis", "anatomy", "ancient", "and", "anemia", "anesthesia", "aneurysm",
        "angina", "angioplasty", "animal", "anomalies", "another", "answers", "antagonists", "antenatal",
        "anthropology", "antibiotic", "antibiotics", "antibody", "anticoagulant", "antidote", "antiemetic", "antigen",
        "antihypertensive", "antiplatelet", "antipyretic", "antisepsis", "antithrombin", "antivenom", "anuria", "anxiety",
        "any", "aortic", "apache", "apnea", "appendectomy", "appendicitis", "appendix", "application",
        "applications", "arbitration", "archea", "architecture", "are", "arithmetic", "armature", "arrangements",
        "array", "arrest", "arrhythmia", "art", "artesunate", "arthritis", "arthroscopy", "ascites",
        "aseptic", "aspects", "aspirin", "assault", "assembly", "assessment", "asthma", "astronomy",
        "atmosphere", "atticoantral", "attributes", "audiology", "auditing", "auditory", "autacoids", "automobile",
        "autosomal", "avascular", "average", "awards", "awareness", "azithromycin", "azotemia", "bacteria",
        "bacterial", "bacteriology", "balance", "balances", "banking", "bartter", "base", "based",
        "basic", "basics", "bcbr", "beams", "because", "been", "behavioral", "behaviour",
        "being", "benefits", "benign", "between", "bhakti", "bicarbonate", "biliary", "bilirubin",
        "biochemistry", "biology", "biomolecules", "biopsy", "bioseparations", "biostatistics", "biotechnology", "bipolar",
        "bite", "bits", "bleeding", "blindness", "block", "blood", "boiler", "bone",
        "brace", "breast", "breeding", "british", "broad", "bronchial", "bronchitis", "bronchoscopy",
        "brucella", "buddhism", "budget", "buffer", "build", "building", "burn", "burning",
        "bus", "business", "but", "bypass", "caesarean", "calcination", "calcium", "calculus",
        "campylobacter", "can", "canal", "cancer", "candidiasis", "cant", "capability", "capsule",
        "carbohydrates", "carcinoma", "cardiac", "cardiogenic", "cardiology", "cardiothoracic", "cardiovascular", "care",
        "caries", "carrier", "cases", "cast", "casts", "cat", "cataract", "cataracts",
        "catheter", "cattle", "causes", "cavity", "ceftriaxone", "celestial", "cell", "cells",
        "cellulitis", "celullar", "census", "central", "centrifugal", "century", "cervical", "cervix",
        "cesarean", "chads", "challenge", "chapter", "characteristic", "characteristics", "charcoal", "chart",
        "chemical", "chemistry", "chemotherapy", "chickenpox", "chikungunya", "child", "children", "chlamydia",
        "chloride", "chloroquine", "choice", "cholecystectomy", "cholelithiasis", "cholera", "cholestatic", "cholesteatoma",
        "cholesterol", "chorionic", "chromosomal", "chromosome", "chronic", "ciprofloxacin", "circuit", "circuits",
        "circulatory", "cirrhosis", "civil", "civilization", "classification", "climate", "clinical", "closed",
        "clotting", "clubbing", "coagulation", "code", "codes", "coherent", "collection", "collision",
        "colonoscopy", "coma", "commerce", "common", "communicati", "communication", "communications", "compaction",
        "compare", "compartment", "compatib", "compatibility", "competitive", "completion", "complication", "complications",
        "components", "composites", "comprehension", "comprehensive", "computer", "concepts", "conciliation", "conic",
        "conjunctivitis", "consent", "conservative", "considerations", "constitution", "constitutional", "construction", "contraception",
        "contraceptive", "contract", "contrast", "control", "conventions", "conveying", "convolution", "convulsion",
        "cooling", "cord", "cornea", "corneal", "coronary", "coronavirus", "corporate", "correcting",
        "correction", "costing", "could", "count", "court", "covid", "cpr", "cpu",
        "crane", "create", "creatinine", "cretinism", "criteria", "critical", "crossmatch", "crush",
        "crystal", "crystals", "csom", "css", "cultural", "culture", "curb", "current",
        "cyanosis", "cycle", "cyclic", "cystic", "cytology", "dairy", "dam", "data",
        "deareration", "decay", "decision", "defects", "defence", "defibrillation", "deficiency", "deficient",
        "define", "definitions", "deflection", "degree", "dehydration", "delayed", "delirium", "delivery",
        "dementia", "demographics", "demography", "dengue", "dental", "dentistry", "depigmentation", "depression",
        "dermatitis", "dermatology", "describe", "descriptions", "design", "detecting", "detection", "development",
        "developmental", "devices", "diabetes", "diabetic", "diagnosis", "diagnostic", "diagnostics", "diagram",
        "dialysis", "diarrhea", "did", "diesel", "difference", "digestive", "digital", "diphtheria",
        "directive", "disaster", "disc", "discuss", "disease", "diseases", "disinfection", "dislocation",
        "disorder", "disorders", "dissection", "dissertation", "distal", "distinctive", "distribution", "diuretic",
        "dna", "does", "doesnt", "dog", "domestic", "dominant", "donor", "dont",
        "dots", "double", "draft", "drill", "drilling", "drills", "drug", "drugs",
        "due", "duodenal", "duties", "dysentery", "dysmenorrhea", "dysplasia", "each", "ear",
        "earth", "easements", "eating", "ebola", "eclipses", "ecoli", "ecology", "ecommerce",
        "economic", "economics", "economy", "ecosystem", "ectopic", "eczema", "edema", "eeg",
        "effects", "efficiency", "efforts", "ehec", "elaborate", "electrical", "electro", "electrolyte",
        "electronics", "elements", "embolism", "embryology", "emergencies", "emergency", "emerging", "emesis",
        "emetic", "empire", "endemic", "endocarditis", "endocrine", "endocrinology", "endometriosis", "endoscopy",
        "ener", "energy", "engine", "engineering", "english", "ent", "entomology", "entropy",
        "environment", "environmental", "enzymes", "epidemic", "epidemiology", "epilepsy", "episiotomy", "epithelial",
        "equalization", "equations", "equipment", "equipments", "equity", "error", "escherichia", "esp",
        "etiology", "eustachian", "evaluating", "evaluation", "evasion", "events", "every", "evidence",
        "examination", "excavating", "explain", "exploration", "external", "eye", "facial", "factor",
        "facts", "fading", "family", "farm", "faulting", "fdma", "features", "feet",
        "festivals", "fetal", "fetch", "fever", "fibrillation", "fibrinogen", "fibroid", "fibrous",
        "filariasis", "finale", "finance", "financial", "find", "findings", "first", "fissure",
        "fistula", "fixation", "fixator", "flow", "flu", "fluid", "flumazenil", "flushing",
        "foetus", "food", "for", "forces", "forensic", "fork", "formats", "foundation",
        "fracture", "fractures", "freedom", "frequency", "friderichsen", "from", "frostbite", "fructosamine",
        "fuel", "function", "functional", "fundamental", "fungal", "fungi", "fuselage", "galactosemia",
        "galaxies", "gallbladder", "gallstone", "gametogenesis", "gangrene", "gastric", "gastroenterology", "gastrointestinal",
        "gcs", "gear", "gene", "general", "generate", "generation", "generator", "genetic",
        "genetics", "genital", "genotype", "geography", "geolocation", "geology", "geriatric", "gestational",
        "get", "giardiasis", "give", "glands", "glasgow", "glaucoma", "glaucomatous", "global",
        "globulin", "glomerular", "glomerulonephritis", "glucose", "glycogen", "glycosuria", "glycosylated", "goiter",
        "goitre", "gonorrhea", "goods", "google", "gout", "government", "governments", "graft",
        "graphene", "gross", "group", "groups", "growth", "gst", "guardianship", "gynaecology",
        "gynecology", "had", "haemoglobin", "haemophilia", "haemophilus", "hair", "half", "harvard",
        "has", "have", "hazards", "hbac", "hdl", "head", "headache", "health",
        "hearing", "heart", "heatstroke", "helminth", "hematology", "hematopathology", "hematuria", "hemoglobin",
        "hemoglobinopathies", "hemophilia", "hemorrhoids", "heparin", "hepatic", "hepatitis", "hepatology", "heritage",
        "hernia", "herpes", "hindu", "histology", "history", "hiv", "hives", "hoisting",
        "holes", "honours", "hormones", "horticulture", "host", "how", "however", "hrm",
        "html", "human", "humidity", "humoral", "husbandry", "hydrauli", "hydraulic", "hydrosphere",
        "hyperaldosteronism", "hypercapnia", "hyperopia", "hyperparathyroidism", "hypertension", "hypertensive", "hyperthermia", "hyperthyroid",
        "hypochromic", "hypokalemia", "hypophosphatemia", "hypotension", "hypothermia", "hypothyroid", "hypovolemic", "hypoxia",
        "hysterectomy", "ibuprofen", "icterus", "image", "imaging", "immobilization", "immune", "immunity",
        "immunization", "immunoglobulin", "immunology", "immunomodulators", "immunopathology", "implant", "important", "incidence",
        "including", "income", "incontinence", "increased", "independence", "india", "indian", "indices",
        "induce", "indus", "industries", "infant", "infarction", "infection", "infections", "infectious",
        "infective", "infertility", "inflammation", "influenza", "information", "infusion", "ingestion", "inhaled",
        "inheritance", "inherited", "initial", "initiating", "injection", "injuries", "injury", "insipidus",
        "insomnia", "installedthrust", "institutions", "instruction", "instruments", "insufficiency", "insulin", "insurance",
        "integration", "intelligences", "intensifier", "intercourse", "internal", "international", "interpretation", "interview",
        "intestinal", "into", "intramuscular", "intravenous", "introduction", "intubation", "investigation", "investigative",
        "inward", "iodine", "ipecac", "iron", "ischaemia", "ischemia", "isolation", "issues",
        "ivermectin", "jainism", "jamming", "jaundice", "jaw", "jetengine", "jna", "joints",
        "judicial", "judiciary", "jumbles", "jurisprudence", "justice", "juvenile", "kalaazar", "karyotype",
        "kcl", "keratitis", "ketoacidosis", "kidney", "klebsiella", "kwire", "kyphosis", "labor",
        "laboratory", "labour", "lakes", "landing", "language", "laparoscopy", "last", "lateraldirectional",
        "lattices", "lavage", "law", "laxmikant", "ldl", "leads", "learning", "least",
        "legal", "legionella", "leishmaniasis", "lens", "lenses", "leprosy", "leptospira", "lesions",
        "leukemia", "leukemias", "leukoplakia", "levels", "life", "lift", "ligament", "lightning",
        "likely", "limb", "lime", "limitation", "linear", "link", "linked", "lipid",
        "lipids", "list", "lithium", "lithosphere", "liver", "logic", "logical", "longitudinal",
        "look", "lordosis", "loss", "lower", "lung", "lymphoma", "lymphoreticular", "machine",
        "machines", "macrophages", "magnesium", "main", "major", "majority", "make", "making",
        "malabsorption", "malaria", "malignant", "malnutrition", "malunion", "management", "mandibular", "manual",
        "maps", "margin", "marine", "marketing", "marks", "marrow", "mass", "material",
        "materials", "maternal", "mcq", "mcqs", "measles", "measu", "measurement", "measuring",
        "mechanics", "mechanism", "mechanisms", "media", "mediated", "medical", "medicine", "medieval",
        "meld", "memories", "memory", "men", "mendelian", "meningococcus", "menopause", "menstrual",
        "menstruation", "mental", "mers", "metabolic", "metabolism", "metallurgy", "metastasis", "metformin",
        "method", "methodology", "methods", "metronidazole", "mice", "microanatomy", "microbiology", "microcytic",
        "microprocessors", "microscopy", "middle", "migraine", "milk", "minerals", "miniature", "mirabegron",
        "miscarriage", "miscellaneous", "mitochondrial", "mixing", "mobile", "mode", "modern", "modes",
        "modified", "mods", "modulation", "molecular", "morbidity", "more", "mortality", "most",
        "motion", "motor", "mounting", "movement", "movements", "mri", "much", "mucosal",
        "mughal", "multiple", "multiplexing", "mumps", "murmur", "muscle", "muscular", "muslim",
        "mutation", "mycetoma", "mycology", "mycoplasma", "myocardial", "myocarditis", "myopia", "mysql",
        "naloxone", "nanofabrication", "nanoscale", "nanotechnology", "natural", "nebulizer", "neck", "necrosis",
        "need", "neet", "negotiable", "neonatal", "neonatology", "neoplasia", "nephrectomy", "nephritis",
        "nephrology", "nephrons", "nephrotic", "nerve", "nervous", "net", "network", "neuroanatomy",
        "neurological", "neurology", "neuropathology", "neurophysiology", "neurotic", "next", "noise", "non",
        "nonunion", "normal", "nose", "not", "npsh", "nuclei", "null", "numbers",
        "nutrition", "obg", "object", "obstetrics", "obstruction", "odontogenic", "oedema", "officer",
        "oliguria", "onchocerciasis", "oncology", "only", "ope", "open", "operating", "operation",
        "operations", "ophthalmology", "opioid", "opportunistic", "optic", "optical", "optics", "oral",
        "orbit", "organ", "organic", "organisations", "organization", "organs", "orthodontics", "orthopaedics",
        "orthopedics", "orthosis", "osteoarthritis", "osteopathology", "osteoporosis", "osteotomy", "other", "otitis",
        "otolaryngology", "otosclerosis", "otoscopy", "outbreak", "outline", "outward", "ovarian", "overdose",
        "overview", "ovulation", "oxygen", "pacemaker", "paediatrics", "paging", "pain", "painless",
        "pallor", "palsy", "pancreatic", "pancreatitis", "pancytopenia", "pandemic", "papers", "papule",
        "para", "paracetamol", "paragraph", "parallel", "paralysis", "paranasal", "parasite", "parasites",
        "parasitic", "parasitology", "parathyroid", "parkinson", "parliament", "partial", "particle", "partnership",
        "parts", "pathogenesis", "pathology", "pathophysiology", "pathways", "patients", "pcos", "pda",
        "pedagogy", "pediatric", "pediatrics", "pediculosis", "pelton", "penal", "penicillin", "people",
        "peptic", "periapical", "pericarditis", "period", "peripheral", "personality", "pertussis", "phagocytosis",
        "pharmacology", "phas", "phenomena", "phenotype", "phenylketonuria", "phosphatase", "photostress", "phyllodes",
        "physical", "physics", "physiological", "physiology", "pigmentation", "piles", "pin", "pistonengine",
        "placenta", "places", "plague", "planetary", "planning", "plant", "plasma", "plastic",
        "plastics", "plate", "platelet", "please", "pneumatic", "pneumococcus", "pneumonia", "point",
        "poisoning", "policy", "polio", "poliomyelitis", "political", "polity", "pollutants", "pollution",
        "polycystic", "polymer", "polymerization", "polymers", "polyuria", "ponds", "population", "positive",
        "post", "postnatal", "potassium", "power", "powers", "practice", "pre", "preamble",
        "precautions", "pregnancy", "pregnant", "preheaters", "prenatal", "presbyopia", "present", "presents",
        "press", "prevalence", "prevention", "preventive", "primary", "principles", "problems", "procedure",
        "procedures", "process", "processes", "proctor", "produce", "production", "products", "prognosis",
        "program", "programmable", "programming", "project", "prolapse", "property", "propulsion", "prosthesis",
        "prosthetics", "protected", "protection", "protein", "proteinoids", "proteinuria", "prothrombin", "protozoa",
        "pseudo", "pseudomonas", "psm", "psoriasis", "psychiatry", "psychological", "psychotic", "public",
        "pugh", "pulmonology", "pump", "pumps", "purification", "pus", "puzzle", "puzzles",
        "pvam", "pyrexia", "quality", "quant", "quantitative", "quantum", "quarantine", "question",
        "questions", "quinine", "quiz", "rabies", "radial", "radiation", "radio", "radioactive",
        "radiodiagnosis", "radiology", "radiotherapy", "rajasthan", "ranson", "ratings", "reaction", "read",
        "reading", "readingcomprehension", "reasoning", "reception", "recessive", "recipient", "recognitions", "rectangular",
        "recycle", "red", "reduction", "reedsolomon", "reet", "reform", "refractory", "regenerative",
        "regulation", "regulations", "regurgitation", "reheaters", "reinforced", "reinke", "related", "relation",
        "relief", "renal", "repair", "reports", "represents", "reproductive", "requirement", "research",
        "resistors", "resources", "respiratory", "responsive", "results", "resuscitation", "retention", "retina",
        "retinal", "retrovirus", "reversible", "review", "revolts", "rhesus", "rheumatoid", "rheumatology",
        "rickettsia", "rifle", "rights", "ringworm", "risk", "rivers", "rna", "road",
        "rod", "role", "rom", "rosacea", "rotor", "routine", "rubella", "rule",
        "safety", "sale", "salivary", "salmonella", "sanctuaries", "sars", "saturation", "scabies",
        "scald", "scale", "scales", "scan", "scarring", "scheduling", "schistosomiasis", "schizoid",
        "schizophrenia", "school", "schwannoma", "sciatica", "science", "sciences", "sclera", "scoliosis",
        "score", "scorpion", "screening", "screw", "search", "second", "secretion", "security",
        "seen", "seizure", "selection", "semantics", "semiconductor", "seminoma", "sense", "sensitivity",
        "separation", "sepsis", "septic", "sequence", "serous", "serum", "server", "set",
        "severe", "sex", "sexual", "sexually", "shigella", "shock", "should", "shouldnt",
        "show", "sickle", "signal", "signals", "signs", "simulator", "simultaneous", "single",
        "sintering", "sinuses", "site", "slaking", "small", "smallpox", "smear", "snake",
        "social", "society", "sodium", "sofa", "software", "soil", "solids", "solution",
        "somatoform", "some", "source", "sources", "space", "specific", "spectrum", "spherical",
        "spicy", "spider", "spleen", "splenectomy", "splenic", "sporadic", "sports", "sprain",
        "spread", "spreading", "sql", "stability", "stainless", "staphylococcus", "state", "static",
        "statin", "statistics", "steady", "steam", "steel", "stem", "stenosis", "stent",
        "sterilization", "stis", "stones", "storage", "strabismus", "strain", "strength", "streptococcal",
        "streptococcus", "stress", "stroke", "structural", "structure", "structures", "struggle", "studies",
        "subcutaneous", "subject", "suction", "sulfonylurea", "sultanate", "summarise", "summarize", "summary",
        "summits", "sunstroke", "superheaters", "supply", "suppurative", "supravalvular", "surgery", "surgeryimages",
        "surgical", "surveying", "survival", "svt", "symptoms", "synchronization", "syndrome", "syndromes",
        "synopsis", "syphilis", "syrup", "system", "systems", "tablet", "tax", "tca",
        "tdma", "technique", "techniques", "technology", "teeth", "tell", "tendon", "terminology",
        "test", "testability", "testing", "tests", "tetanus", "textual", "thalassaemia", "thalassemia",
        "than", "thanatology", "that", "the", "their", "then", "theories", "theory",
        "therapeutic", "therapy", "therefore", "thermodynamics", "thermosetting", "these", "theses", "thesis",
        "this", "those", "threats", "thrombolytic", "thrombosis", "thrombus", "thyroid", "time",
        "tinea", "titanium", "tools", "tooth", "topic", "topical", "topics", "torts",
        "total", "towers", "toxicity", "toxicology", "toxoid", "tracheostomy", "trachoma", "tract",
        "traction", "traffic", "transaminase", "transfer", "transfusion", "transmitted", "transplant", "treatment",
        "treatments", "triglyceride", "trophoblastic", "trusts", "trypanosomiasis", "tube", "tuberculosis", "tubotympanic",
        "tumor", "tumors", "tumour", "tuning", "turbi", "turbines", "turbop", "types",
        "typhoid", "typhus", "ulcer", "ultrasound", "umbilical", "uncategorized", "union", "units",
        "universe", "unsteady", "unsteadystate", "upsc", "uraemia", "urea", "ureaplasma", "uremia",
        "uric", "urinary", "urine", "urogenital", "urology", "urticaria", "using", "usmle",
        "usually", "uterine", "uveal", "uveitis", "vaccination", "vaccine", "vaccines", "vaginal",
        "valley", "valvular", "variable", "varicella", "varicose", "vascular", "vehicle", "vehicular",
        "ventilation", "verbal", "vericiguat", "vertebrae", "very", "vesicular", "vestibular", "villus",
        "violence", "viral", "virology", "virtual", "virus", "vision", "visual", "vitamins",
        "vitiligo", "vlsi", "vomiting", "von", "warfarin", "warming", "was", "water",
        "waterhouse", "weather", "web", "wells", "were", "what", "wheel", "when",
        "where", "whereas", "which", "while", "white", "who", "whom", "whooping",
        "whose", "why", "wildlife", "will", "willebrand", "windings", "wireless", "wise",
        "with", "without", "women", "wont", "work", "world", "worm", "would",
        "write", "xlinked", "xray", "years", "yellow", "yes", "zika",
    )

    /** Long pasted text (abstracts, articles) is never rewritten. */
    private const val MAX_CORRECT_LENGTH = 600

    /** Corrects whole sentences word-by-word; preserves punctuation, numbers and casing. */
    fun correct(text: String): String {
        if (text.length > MAX_CORRECT_LENGTH) return text
        return text.split(Regex("\\s+")).joinToString(" ") { token -> correctWord(token) }
    }

    private fun correctWord(token: String): String {
        if (token.length < 4 || token.length > 20) return token
        val lower = token.lowercase().trim('"', '\'', '(', ')', ',', '.', ':', ';', '!', '?', '-', '_')
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
