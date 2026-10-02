import Foundation

/// Authoritative registry mapping MBBS Clinical Guardians and Animal Warriors
/// to their 4-Power Tactical Arsenal Kit, Factions, and Master Stories.
/// Strictly ported from Android `GuardianRegistry.kt`.
enum GuardianRegistry {

    // ─── 19 COMPLETE HERO KITS (76 UNIQUE SUBJECT-THEMED POWERS) ─────────────

    static let heroKits: [Int: GuardianHeroKit] = [
        // 1. AXIOM • ANATOMY
        1001: GuardianHeroKit(
            avatarIndex: 1001,
            championName: "Skeletal Guardian • Axiom",
            subjectSpecialty: "Anatomy (Gross & Neuro)",
            faction: .demon,
            intelPower: GuardianPower(
                powerId: "FASCIAL_PLANE_SCAN",
                powerName: "Fascial Plane Scan",
                powerCategory: .overlay,
                description: "Traces anatomical tissue planes to highlight high-yield structural keywords in the question stem.",
                cooldownRounds: 1,
                chargesPerQuiz: 3,
                avatarIndex: 1001,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char01_axiom.glb", backgroundImageUrl: "backgrounds/bg_char01_axiom.jpg", rimColorHex: 0x00E5FF),
                iconResName: "ic_power_axiom_intel"
            ),
            strikePower: GuardianPower(
                powerId: "OSTEOTOME_CHISEL",
                powerName: "Osteotome Chisel",
                powerCategory: .elimination,
                description: "Chisels away the most anatomically implausible distractor option with surgical force.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1001,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char01_axiom.glb", backgroundImageUrl: "backgrounds/bg_char01_axiom.jpg", rimColorHex: 0x00E5FF),
                iconResName: "ic_power_axiom_strike"
            ),
            defensePower: GuardianPower(
                powerId: "RIBCAGE_BASTION",
                powerName: "Ribcage Bastion",
                powerCategory: .safetyNet,
                description: "Heavy ivory bone armor with glowing blue soulfire marrow absorbs incoming penalties and locks in score streak.",
                cooldownRounds: 2,
                chargesPerQuiz: 3,
                avatarIndex: 1001,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char01_axiom.glb", backgroundImageUrl: "backgrounds/bg_char01_axiom.jpg", rimColorHex: 0x00E5FF),
                iconResName: "ic_power_axiom_defense"
            ),
            surgePower: GuardianPower(
                powerId: "OSTEOLOGY_SURGE",
                powerName: "Osteology Surge",
                powerCategory: .timeScore,
                description: "Channels ancient anatomical mastery, granting a 1.5x score multiplier for the next 2 correct answers.",
                cooldownRounds: 3,
                chargesPerQuiz: 1,
                avatarIndex: 1001,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char01_axiom.glb", backgroundImageUrl: "backgrounds/bg_char01_axiom.jpg", rimColorHex: 0x00E5FF),
                iconResName: "ic_power_axiom_surge"
            ),
            story: GuardianStories.getStory(avatarIndex: 1001)!
        ),

        // 2. PULSE • PHYSIOLOGY
        1002: GuardianHeroKit(
            avatarIndex: 1002,
            championName: "Bioelectric Speedster • Pulse",
            subjectSpecialty: "Physiology & Cardiac Electrophysiology",
            faction: .human,
            intelPower: GuardianPower(
                powerId: "ECG_RHYTHM_TRACE",
                powerName: "ECG Rhythm Trace",
                powerCategory: .overlay,
                description: "Analyzes systemic physiological gradients, revealing the primary functional clue in the vignette.",
                cooldownRounds: 1,
                chargesPerQuiz: 3,
                avatarIndex: 1002,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char02_pulse.glb", backgroundImageUrl: "backgrounds/bg_char02_pulse.jpg", rimColorHex: 0xFFD700),
                iconResName: "ic_power_pulse_intel"
            ),
            strikePower: GuardianPower(
                powerId: "DEFIBRILLATOR_SHOCK",
                powerName: "Defibrillator Shock",
                powerCategory: .elimination,
                description: "Delivers a 360-joule bioelectric countershock, instantly vaporizing 2 misleading options.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1002,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char02_pulse.glb", backgroundImageUrl: "backgrounds/bg_char02_pulse.jpg", rimColorHex: 0xFFD700),
                iconResName: "ic_power_pulse_strike"
            ),
            defensePower: GuardianPower(
                powerId: "VAGAL_REFRACTORY",
                powerName: "Vagal Refractory",
                powerCategory: .timeScore,
                description: "Triggers vagal stimulation, freezing countdown tension for 6 seconds while stabilizing thinking calm.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1002,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char02_pulse.glb", backgroundImageUrl: "backgrounds/bg_char02_pulse.jpg", rimColorHex: 0xFFD700),
                iconResName: "ic_power_pulse_defense"
            ),
            surgePower: GuardianPower(
                powerId: "BIOELECTRIC_SURGE",
                powerName: "Bioelectric Surge",
                powerCategory: .timeScore,
                description: "Pulsing ECG cardiac waves boost response speed and grant double points (2.0x) for rapid answers.",
                cooldownRounds: 3,
                chargesPerQuiz: 2,
                avatarIndex: 1002,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char02_pulse.glb", backgroundImageUrl: "backgrounds/bg_char02_pulse.jpg", rimColorHex: 0xFFD700),
                iconResName: "ic_power_pulse_surge"
            ),
            story: GuardianStories.getStory(avatarIndex: 1002)!
        ),

        // 3. CATALYST • BIOCHEMISTRY
        1003: GuardianHeroKit(
            avatarIndex: 1003,
            championName: "Biochemistry Alchemist • Catalyst",
            subjectSpecialty: "Biochemistry & Genetics",
            faction: .demon,
            intelPower: GuardianPower(
                powerId: "METABOLIC_PATHWAY_MAP",
                powerName: "Metabolic Pathway Map",
                powerCategory: .overlay,
                description: "Illuminates the regulatory rate-limiting enzyme step hidden in complex metabolic questions.",
                cooldownRounds: 1,
                chargesPerQuiz: 3,
                avatarIndex: 1003,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char03_catalyst.glb", backgroundImageUrl: "backgrounds/bg_char03_catalyst.jpg", rimColorHex: 0x9C27B0),
                iconResName: "ic_power_catalyst_intel"
            ),
            strikePower: GuardianPower(
                powerId: "ENZYME_CLEAVAGE",
                powerName: "Enzyme Cleavage",
                powerCategory: .elimination,
                description: "Hydrolyzes peptide bonds of the most deceptive distractor trap, removing it from play.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1003,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char03_catalyst.glb", backgroundImageUrl: "backgrounds/bg_char03_catalyst.jpg", rimColorHex: 0x9C27B0),
                iconResName: "ic_power_catalyst_strike"
            ),
            defensePower: GuardianPower(
                powerId: "BUFFER_EQUILIBRIUM",
                powerName: "Buffer Equilibrium",
                powerCategory: .safetyNet,
                description: "Bicarbonate buffer solution neutralizes the next negative mark, keeping streak pH balanced at 7.4.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1003,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char03_catalyst.glb", backgroundImageUrl: "backgrounds/bg_char03_catalyst.jpg", rimColorHex: 0x9C27B0),
                iconResName: "ic_power_catalyst_defense"
            ),
            surgePower: GuardianPower(
                powerId: "ATP_SURGE",
                powerName: "ATP Surge",
                powerCategory: .timeScore,
                description: "Doubles score points gained (2.0x) for 3 consecutive correct questions through enzymatic acceleration.",
                cooldownRounds: 3,
                chargesPerQuiz: 2,
                avatarIndex: 1003,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char03_catalyst.glb", backgroundImageUrl: "backgrounds/bg_char03_catalyst.jpg", rimColorHex: 0x9C27B0),
                iconResName: "ic_power_catalyst_surge"
            ),
            story: GuardianStories.getStory(avatarIndex: 1003)!
        ),

        // 4. NECROS • PATHOLOGY
        1004: GuardianHeroKit(
            avatarIndex: 1004,
            championName: "Reaper of Pathology • Necros",
            subjectSpecialty: "Pathology & Histopathology",
            faction: .demon,
            intelPower: GuardianPower(
                powerId: "BIOPSY_STAIN",
                powerName: "Biopsy Stain",
                powerCategory: .overlay,
                description: "Applies emergency H&E staining to reveal pathognomonic microscopic criteria in the question.",
                cooldownRounds: 1,
                chargesPerQuiz: 3,
                avatarIndex: 1004,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char04_necros.glb", backgroundImageUrl: "backgrounds/bg_char04_necros.jpg", rimColorHex: 0x7E57C2),
                iconResName: "ic_power_necros_intel"
            ),
            strikePower: GuardianPower(
                powerId: "CELLULAR_NECROSIS",
                powerName: "Cellular Necrosis",
                powerCategory: .elimination,
                description: "Inflicts necrotic pathology on choices, dissolving the two most misleading distractor options.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1004,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char04_necros.glb", backgroundImageUrl: "backgrounds/bg_char04_necros.jpg", rimColorHex: 0x7E57C2),
                iconResName: "ic_power_necros_strike"
            ),
            defensePower: GuardianPower(
                powerId: "APOPTOSIS_WARD",
                powerName: "Apoptosis Ward",
                powerCategory: .safetyNet,
                description: "Locks in score streak health with zero inflammatory spillover, preventing penalty on error.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1004,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char04_necros.glb", backgroundImageUrl: "backgrounds/bg_char04_necros.jpg", rimColorHex: 0x7E57C2),
                iconResName: "ic_power_necros_defense"
            ),
            surgePower: GuardianPower(
                powerId: "CYTOKINE_STORM",
                powerName: "Cytokine Storm",
                powerCategory: .timeScore,
                description: "Unleashes overwhelming systemic diagnostic focus, granting 5s time freeze and 1.5x score bonus.",
                cooldownRounds: 3,
                chargesPerQuiz: 1,
                avatarIndex: 1004,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char04_necros.glb", backgroundImageUrl: "backgrounds/bg_char04_necros.jpg", rimColorHex: 0x7E57C2),
                iconResName: "ic_power_necros_surge"
            ),
            story: GuardianStories.getStory(avatarIndex: 1004)!
        ),

        // 5. PHARMA • PHARMACOLOGY
        1005: GuardianHeroKit(
            avatarIndex: 1005,
            championName: "Vanguard Chemist • Pharma",
            subjectSpecialty: "Pharmacology & Therapeutics",
            faction: .human,
            intelPower: GuardianPower(
                powerId: "RECEPTOR_BINDING_SCAN",
                powerName: "Receptor Binding Scan",
                powerCategory: .overlay,
                description: "Scans drug-receptor interactions to highlight primary indications and mechanism of action.",
                cooldownRounds: 1,
                chargesPerQuiz: 3,
                avatarIndex: 1005,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char05_pharma.glb", backgroundImageUrl: "backgrounds/bg_char05_pharma.jpg", rimColorHex: 0x00E676),
                iconResName: "ic_power_pharma_intel"
            ),
            strikePower: GuardianPower(
                powerId: "ANTAGONIST_BLOCK",
                powerName: "Antagonist Block",
                powerCategory: .elimination,
                description: "Competitive receptor antagonist binds and blocks the most hazardous toxic distractor.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1005,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char05_pharma.glb", backgroundImageUrl: "backgrounds/bg_char05_pharma.jpg", rimColorHex: 0x00E676),
                iconResName: "ic_power_pharma_strike"
            ),
            defensePower: GuardianPower(
                powerId: "RECEPTOR_ANTIDOTE",
                powerName: "Receptor Antidote",
                powerCategory: .safetyNet,
                description: "Injects a clinical antidote granting a second attempt on an erroneous answer without score penalty.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1005,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char05_pharma.glb", backgroundImageUrl: "backgrounds/bg_char05_pharma.jpg", rimColorHex: 0x00E676),
                iconResName: "ic_power_pharma_defense"
            ),
            surgePower: GuardianPower(
                powerId: "ADRENALINE_INFUSION",
                powerName: "Adrenaline Infusion",
                powerCategory: .timeScore,
                description: "Rapid IV adrenaline spike boosts neural processing speed, granting 2.0x points on the next prompt.",
                cooldownRounds: 3,
                chargesPerQuiz: 1,
                avatarIndex: 1005,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char05_pharma.glb", backgroundImageUrl: "backgrounds/bg_char05_pharma.jpg", rimColorHex: 0x00E676),
                iconResName: "ic_power_pharma_surge"
            ),
            story: GuardianStories.getStory(avatarIndex: 1005)!
        ),

        // 6. MICROX • MICROBIOLOGY
        1006: GuardianHeroKit(
            avatarIndex: 1006,
            championName: "Microbe Hunter • Microx",
            subjectSpecialty: "Microbiology & Infectious Diseases",
            faction: .demon,
            intelPower: GuardianPower(
                powerId: "GRAM_STAIN_ID",
                powerName: "Gram Stain ID",
                powerCategory: .overlay,
                description: "Differentiates peptidoglycan envelope markers, classifying bacterial and viral clues instantly.",
                cooldownRounds: 1,
                chargesPerQuiz: 3,
                avatarIndex: 1006,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char06_microx.glb", backgroundImageUrl: "backgrounds/bg_char06_microx.jpg", rimColorHex: 0x76FF03),
                iconResName: "ic_power_microx_intel"
            ),
            strikePower: GuardianPower(
                powerId: "PETRI_CONTAINMENT",
                powerName: "Petri Containment",
                powerCategory: .elimination,
                description: "Deploys sterile bio-containment seals that isolate bacterial traps and neutralize 2 distractor options.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1006,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char06_microx.glb", backgroundImageUrl: "backgrounds/bg_char06_microx.jpg", rimColorHex: 0x76FF03),
                iconResName: "ic_power_microx_strike"
            ),
            defensePower: GuardianPower(
                powerId: "STERILE_ISOLATION",
                powerName: "Sterile Isolation",
                powerCategory: .safetyNet,
                description: "Erects a laminar airflow bio-shield, completely absorbing negative marking on a single error.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1006,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char06_microx.glb", backgroundImageUrl: "backgrounds/bg_char06_microx.jpg", rimColorHex: 0x76FF03),
                iconResName: "ic_power_microx_defense"
            ),
            surgePower: GuardianPower(
                powerId: "EXPONENTIAL_COLONY",
                powerName: "Exponential Colony",
                powerCategory: .timeScore,
                description: "Accelerates logarithmic growth curve, granting a 1.5x score bonus across 2 successive questions.",
                cooldownRounds: 3,
                chargesPerQuiz: 1,
                avatarIndex: 1006,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char06_microx.glb", backgroundImageUrl: "backgrounds/bg_char06_microx.jpg", rimColorHex: 0x76FF03),
                iconResName: "ic_power_microx_surge"
            ),
            story: GuardianStories.getStory(avatarIndex: 1006)!
        ),

        // 7. VERDICT • FORENSIC MEDICINE
        1007: GuardianHeroKit(
            avatarIndex: 1007,
            championName: "Forensic Inquisitor • Verdict",
            subjectSpecialty: "Forensic Medicine & Toxicology",
            faction: .human,
            intelPower: GuardianPower(
                powerId: "FORENSIC_AUTOPSY",
                powerName: "Forensic Autopsy",
                powerCategory: .overlay,
                description: "Illuminates the decisive diagnostic finding and eliminates forensic anomalies from the question stem.",
                cooldownRounds: 1,
                chargesPerQuiz: 3,
                avatarIndex: 1007,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char07_verdict.glb", backgroundImageUrl: "backgrounds/bg_char07_verdict.jpg", rimColorHex: 0xFF9800),
                iconResName: "ic_power_verdict_intel"
            ),
            strikePower: GuardianPower(
                powerId: "INQUEST_EXCISION",
                powerName: "Inquest Excision",
                powerCategory: .elimination,
                description: "Discredits fabricated testimony, eliminating the single most deceptive diagnostic decoy.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1007,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char07_verdict.glb", backgroundImageUrl: "backgrounds/bg_char07_verdict.jpg", rimColorHex: 0xFF9800),
                iconResName: "ic_power_verdict_strike"
            ),
            defensePower: GuardianPower(
                powerId: "JURISPRUDENCE_IMMUNITY",
                powerName: "Jurisprudence Immunity",
                powerCategory: .safetyNet,
                description: "Legal immunity seals your score against penalties, offering an immediate retrial on miss.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1007,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char07_verdict.glb", backgroundImageUrl: "backgrounds/bg_char07_verdict.jpg", rimColorHex: 0xFF9800),
                iconResName: "ic_power_verdict_defense"
            ),
            surgePower: GuardianPower(
                powerId: "POST_MORTEM_CERTAINTY",
                powerName: "Post-Mortem Certainty",
                powerCategory: .timeScore,
                description: "Unlocks undeniable medicolegal proof, delivering double score points (2.0x) on your verdict.",
                cooldownRounds: 3,
                chargesPerQuiz: 1,
                avatarIndex: 1007,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char07_verdict.glb", backgroundImageUrl: "backgrounds/bg_char07_verdict.jpg", rimColorHex: 0xFF9800),
                iconResName: "ic_power_verdict_surge"
            ),
            story: GuardianStories.getStory(avatarIndex: 1007)!
        ),

        // 8. CURA • COMMUNITY MEDICINE
        1008: GuardianHeroKit(
            avatarIndex: 1008,
            championName: "Public-Health Strategist • Cura",
            subjectSpecialty: "Community Medicine & PSM",
            faction: .angel,
            intelPower: GuardianPower(
                powerId: "EPIDEMIOLOGIC_SURVEY",
                powerName: "Epidemiologic Survey",
                powerCategory: .overlay,
                description: "Surveys population morbidity rates to highlight statistical bias and true incidence clues.",
                cooldownRounds: 1,
                chargesPerQuiz: 3,
                avatarIndex: 1008,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char08_cura.glb", backgroundImageUrl: "backgrounds/bg_char08_cura.jpg", rimColorHex: 0x00E676),
                iconResName: "ic_power_cura_intel"
            ),
            strikePower: GuardianPower(
                powerId: "QUARANTINE_VECTOR",
                powerName: "Quarantine Vector",
                powerCategory: .elimination,
                description: "Isolates the disease vector, eliminating 1 dangerous distractor trap immediately.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1008,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char08_cura.glb", backgroundImageUrl: "backgrounds/bg_char08_cura.jpg", rimColorHex: 0x00E676),
                iconResName: "ic_power_cura_strike"
            ),
            defensePower: GuardianPower(
                powerId: "EPIDEMIC_QUARANTINE",
                powerName: "Epidemic Quarantine",
                powerCategory: .safetyNet,
                description: "Deploys a global public health barrier isolating incorrect options and protecting streak health.",
                cooldownRounds: 2,
                chargesPerQuiz: 3,
                avatarIndex: 1008,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char08_cura.glb", backgroundImageUrl: "backgrounds/bg_char08_cura.jpg", rimColorHex: 0x00E676),
                iconResName: "ic_power_cura_defense"
            ),
            surgePower: GuardianPower(
                powerId: "HERD_IMMUNITY",
                powerName: "Herd Immunity",
                powerCategory: .timeScore,
                description: "Achieves threshold herd immunity, shielding against penalties for 2 consecutive rounds.",
                cooldownRounds: 3,
                chargesPerQuiz: 1,
                avatarIndex: 1008,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char08_cura.glb", backgroundImageUrl: "backgrounds/bg_char08_cura.jpg", rimColorHex: 0x00E676),
                iconResName: "ic_power_cura_surge"
            ),
            story: GuardianStories.getStory(avatarIndex: 1008)!
        ),

        // 9. MEDICUS • GENERAL MEDICINE
        1009: GuardianHeroKit(
            avatarIndex: 1009,
            championName: "Versatile Diagnostician • Medicus",
            subjectSpecialty: "General Medicine",
            faction: .angel,
            intelPower: GuardianPower(
                powerId: "CLINICAL_DIFFERENTIAL",
                powerName: "Clinical Differential",
                powerCategory: .overlay,
                description: "Synthesizes multi-system diagnostic signs to reveal the high-yield correct clinical path.",
                cooldownRounds: 1,
                chargesPerQuiz: 3,
                avatarIndex: 1009,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char09_medicus.glb", backgroundImageUrl: "backgrounds/bg_char09_medicus.jpg", rimColorHex: 0x00E5FF),
                iconResName: "ic_power_medicus_intel"
            ),
            strikePower: GuardianPower(
                powerId: "TARGETED_THERAPY",
                powerName: "Targeted Therapy",
                powerCategory: .elimination,
                description: "Applies evidence-based clinical protocols to strike out the most common clinical pitfall.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1009,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char09_medicus.glb", backgroundImageUrl: "backgrounds/bg_char09_medicus.jpg", rimColorHex: 0x00E5FF),
                iconResName: "ic_power_medicus_strike"
            ),
            defensePower: GuardianPower(
                powerId: "CLINICAL_STABILIZER",
                powerName: "Clinical Stabilizer",
                powerCategory: .safetyNet,
                description: "Stabilizes deteriorating clinical parameters, negating negative marks on one mistake.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1009,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char09_medicus.glb", backgroundImageUrl: "backgrounds/bg_char09_medicus.jpg", rimColorHex: 0x00E5FF),
                iconResName: "ic_power_medicus_defense"
            ),
            surgePower: GuardianPower(
                powerId: "GRAND_ROUNDS_INSIGHT",
                powerName: "Grand Rounds Insight",
                powerCategory: .timeScore,
                description: "Synthesizes bedside medicine with academic brilliance, doubling score (2.0x) on your solve.",
                cooldownRounds: 3,
                chargesPerQuiz: 1,
                avatarIndex: 1009,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char09_medicus.glb", backgroundImageUrl: "backgrounds/bg_char09_medicus.jpg", rimColorHex: 0x00E5FF),
                iconResName: "ic_power_medicus_surge"
            ),
            story: GuardianStories.getStory(avatarIndex: 1009)!
        ),

        // 10. SURGON • GENERAL SURGERY
        1010: GuardianHeroKit(
            avatarIndex: 1010,
            championName: "Precision Surgeon • Surgon",
            subjectSpecialty: "General Surgery & OT",
            faction: .human,
            intelPower: GuardianPower(
                powerId: "PRE_OP_IMAGING",
                powerName: "Pre-Op Imaging",
                powerCategory: .overlay,
                description: "Visualizes operative anatomy and margins, illuminating critical clinical milestones.",
                cooldownRounds: 1,
                chargesPerQuiz: 3,
                avatarIndex: 1010,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char10_surgon.glb", backgroundImageUrl: "backgrounds/bg_char10_surgon.jpg", rimColorHex: 0x00E5FF),
                iconResName: "ic_power_surgon_intel"
            ),
            strikePower: GuardianPower(
                powerId: "SURGICAL_EXCISION",
                powerName: "Surgical Excision",
                powerCategory: .elimination,
                description: "Deftly excises the two most lethal clinical distractor traps with ultrasonic precision.",
                cooldownRounds: 2,
                chargesPerQuiz: 3,
                avatarIndex: 1010,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char10_surgon.glb", backgroundImageUrl: "backgrounds/bg_char10_surgon.jpg", rimColorHex: 0x00E5FF),
                iconResName: "ic_power_surgon_strike"
            ),
            defensePower: GuardianPower(
                powerId: "HEMOSTATIC_CLAMP",
                powerName: "Hemostatic Clamp",
                powerCategory: .safetyNet,
                description: "Arrests intellectual hemorrhage, clamping streak points against accidental loss.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1010,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char10_surgon.glb", backgroundImageUrl: "backgrounds/bg_char10_surgon.jpg", rimColorHex: 0x00E5FF),
                iconResName: "ic_power_surgon_defense"
            ),
            surgePower: GuardianPower(
                powerId: "LAPAROSCOPIC_SURGE",
                powerName: "Laparoscopic Surge",
                powerCategory: .timeScore,
                description: "Precision multi-port focus speeds problem-solving, yielding a 1.5x score bonus.",
                cooldownRounds: 3,
                chargesPerQuiz: 1,
                avatarIndex: 1010,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char10_surgon.glb", backgroundImageUrl: "backgrounds/bg_char10_surgon.jpg", rimColorHex: 0x00E5FF),
                iconResName: "ic_power_surgon_surge"
            ),
            story: GuardianStories.getStory(avatarIndex: 1010)!
        ),

        // 11. VITA • OBGYN
        1011: GuardianHeroKit(
            avatarIndex: 1011,
            championName: "Maternal-Fetal Guardian • Vita",
            subjectSpecialty: "Obstetrics & Gynecology",
            faction: .angel,
            intelPower: GuardianPower(
                powerId: "NST_MONITORING",
                powerName: "NST Monitoring",
                powerCategory: .overlay,
                description: "Monitors fetal-maternal well-being, detecting subtle clinical decelerations and high-yield signs.",
                cooldownRounds: 1,
                chargesPerQuiz: 3,
                avatarIndex: 1011,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char11_vita.glb", backgroundImageUrl: "backgrounds/bg_char11_vita.jpg", rimColorHex: 0xF48FB1),
                iconResName: "ic_power_vita_intel"
            ),
            strikePower: GuardianPower(
                powerId: "AMNIOTIC_CLEAVE",
                powerName: "Amniotic Cleave",
                powerCategory: .elimination,
                description: "Cleaves away confusing distractor membranes to present a clear clinical choice.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1011,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char11_vita.glb", backgroundImageUrl: "backgrounds/bg_char11_vita.jpg", rimColorHex: 0xF48FB1),
                iconResName: "ic_power_vita_strike"
            ),
            defensePower: GuardianPower(
                powerId: "FETAL_HEART_SHIELD",
                powerName: "Fetal Heart Shield",
                powerCategory: .safetyNet,
                description: "Radiates protective maternal warmth that shields score health and grants a second chance on error.",
                cooldownRounds: 2,
                chargesPerQuiz: 3,
                avatarIndex: 1011,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char11_vita.glb", backgroundImageUrl: "backgrounds/bg_char11_vita.jpg", rimColorHex: 0xF48FB1),
                iconResName: "ic_power_vita_defense"
            ),
            surgePower: GuardianPower(
                powerId: "PARTURITION_POWER",
                powerName: "Parturition Power",
                powerCategory: .timeScore,
                description: "Unleashes the tremendous energy of labor completion, doubling score (2.0x) on your answer.",
                cooldownRounds: 3,
                chargesPerQuiz: 1,
                avatarIndex: 1011,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char11_vita.glb", backgroundImageUrl: "backgrounds/bg_char11_vita.jpg", rimColorHex: 0xF48FB1),
                iconResName: "ic_power_vita_surge"
            ),
            story: GuardianStories.getStory(avatarIndex: 1011)!
        ),

        // 12. PEDIA • PEDIATRICS
        1012: GuardianHeroKit(
            avatarIndex: 1012,
            championName: "Child Specialist • Pedia",
            subjectSpecialty: "Pediatrics & Neonatology",
            faction: .angel,
            intelPower: GuardianPower(
                powerId: "APGAR_ASSESSMENT",
                powerName: "Apgar Assessment",
                powerCategory: .overlay,
                description: "Evaluates appearance, pulse, and activity to reveal pediatric milestones in the vignette.",
                cooldownRounds: 1,
                chargesPerQuiz: 3,
                avatarIndex: 1012,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char12_pedia.glb", backgroundImageUrl: "backgrounds/bg_char12_pedia.jpg", rimColorHex: 0xFFD700),
                iconResName: "ic_power_pedia_intel"
            ),
            strikePower: GuardianPower(
                powerId: "VACCINE_SHIELD_EXCISION",
                powerName: "Vaccine Excision",
                powerCategory: .elimination,
                description: "Administers targeted prophylactic logic, eradicating 1 misleading diagnostic option.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1012,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char12_pedia.glb", backgroundImageUrl: "backgrounds/bg_char12_pedia.jpg", rimColorHex: 0xFFD700),
                iconResName: "ic_power_pedia_strike"
            ),
            defensePower: GuardianPower(
                powerId: "PEDIATRIC_IMMUNITY",
                powerName: "Pediatric Immunity",
                powerCategory: .safetyNet,
                description: "Provides warm pediatric comfort, granting immunity to negative marking for 2 rounds.",
                cooldownRounds: 2,
                chargesPerQuiz: 3,
                avatarIndex: 1012,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char12_pedia.glb", backgroundImageUrl: "backgrounds/bg_char12_pedia.jpg", rimColorHex: 0xFFD700),
                iconResName: "ic_power_pedia_defense"
            ),
            surgePower: GuardianPower(
                powerId: "GROWTH_SPURT_SURGE",
                powerName: "Growth Spurt Surge",
                powerCategory: .timeScore,
                description: "Rapid developmental acceleration grants a 1.5x score bonus for consecutive correct answers.",
                cooldownRounds: 3,
                chargesPerQuiz: 1,
                avatarIndex: 1012,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char12_pedia.glb", backgroundImageUrl: "backgrounds/bg_char12_pedia.jpg", rimColorHex: 0xFFD700),
                iconResName: "ic_power_pedia_surge"
            ),
            story: GuardianStories.getStory(avatarIndex: 1012)!
        ),

        // 13. OSTEON • ORTHOPEDICS
        1013: GuardianHeroKit(
            avatarIndex: 1013,
            championName: "Bone-and-Joint Warrior • Osteon",
            subjectSpecialty: "Orthopedics & Biomechanics",
            faction: .human,
            intelPower: GuardianPower(
                powerId: "STRESS_FRACTURE_SCAN",
                powerName: "Stress Fracture Scan",
                powerCategory: .overlay,
                description: "Locates biomechanical failure lines, pinpointing the critical orthopedic clue.",
                cooldownRounds: 1,
                chargesPerQuiz: 3,
                avatarIndex: 1013,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char13_osteon.glb", backgroundImageUrl: "backgrounds/bg_char13_osteon.jpg", rimColorHex: 0x90CAF9),
                iconResName: "ic_power_osteon_intel"
            ),
            strikePower: GuardianPower(
                powerId: "ORTHOPEDIC_HAMMER",
                powerName: "Orthopedic Hammer",
                powerCategory: .elimination,
                description: "Shatters the primary distractor option with crushing titanium force.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1013,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char13_osteon.glb", backgroundImageUrl: "backgrounds/bg_char13_osteon.jpg", rimColorHex: 0x90CAF9),
                iconResName: "ic_power_osteon_strike"
            ),
            defensePower: GuardianPower(
                powerId: "ORTHOPEDIC_CAST",
                powerName: "Orthopedic Cast",
                powerCategory: .safetyNet,
                description: "Encases your score streak in an indestructible plaster-titanium cast resisting penalty.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1013,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char13_osteon.glb", backgroundImageUrl: "backgrounds/bg_char13_osteon.jpg", rimColorHex: 0x90CAF9),
                iconResName: "ic_power_osteon_defense"
            ),
            surgePower: GuardianPower(
                powerId: "CALLUS_REMODELING",
                powerName: "Callus Remodeling",
                powerCategory: .timeScore,
                description: "Rapid bone remodeling restores momentum, granting 1.5x score bonus on your next answer.",
                cooldownRounds: 3,
                chargesPerQuiz: 1,
                avatarIndex: 1013,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char13_osteon.glb", backgroundImageUrl: "backgrounds/bg_char13_osteon.jpg", rimColorHex: 0x90CAF9),
                iconResName: "ic_power_osteon_surge"
            ),
            story: GuardianStories.getStory(avatarIndex: 1013)!
        ),

        // 14. OPTIX • OPHTHALMOLOGY
        1014: GuardianHeroKit(
            avatarIndex: 1014,
            championName: "Retinal Sharpshooter • Optix",
            subjectSpecialty: "Ophthalmology & Optics",
            faction: .angel,
            intelPower: GuardianPower(
                powerId: "FUNDUS_EXAMINATION",
                powerName: "Fundus Examination",
                powerCategory: .overlay,
                description: "Magnifies the optic disc and fovea, revealing microscopic diagnostic details in the vignette.",
                cooldownRounds: 1,
                chargesPerQuiz: 3,
                avatarIndex: 1014,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char14_optix.glb", backgroundImageUrl: "backgrounds/bg_char14_optix.jpg", rimColorHex: 0x00E5FF),
                iconResName: "ic_power_optix_intel"
            ),
            strikePower: GuardianPower(
                powerId: "RETINAL_BEAM",
                powerName: "Retinal Beam",
                powerCategory: .elimination,
                description: "Precision argon laser cuts away optical distractor traps with clinical accuracy (removes 2).",
                cooldownRounds: 2,
                chargesPerQuiz: 3,
                avatarIndex: 1014,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char14_optix.glb", backgroundImageUrl: "backgrounds/bg_char14_optix.jpg", rimColorHex: 0x00E5FF),
                iconResName: "ic_power_optix_strike"
            ),
            defensePower: GuardianPower(
                powerId: "CORNEAL_SHIELD",
                powerName: "Corneal Shield",
                powerCategory: .safetyNet,
                description: "Transparent crystalline shield deflects penalty consequences on an incorrect response.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1014,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char14_optix.glb", backgroundImageUrl: "backgrounds/bg_char14_optix.jpg", rimColorHex: 0x00E5FF),
                iconResName: "ic_power_optix_defense"
            ),
            surgePower: GuardianPower(
                powerId: "TWENTY_TWENTY_CLARITY",
                powerName: "20/20 Clarity",
                powerCategory: .timeScore,
                description: "Crystal-clear visual acuity pauses countdown tension for 8 seconds, granting pure focus.",
                cooldownRounds: 3,
                chargesPerQuiz: 1,
                avatarIndex: 1014,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char14_optix.glb", backgroundImageUrl: "backgrounds/bg_char14_optix.jpg", rimColorHex: 0x00E5FF),
                iconResName: "ic_power_optix_surge"
            ),
            story: GuardianStories.getStory(avatarIndex: 1014)!
        ),

        // 15. RESONA • ENT
        1015: GuardianHeroKit(
            avatarIndex: 1015,
            championName: "Acoustic Resonance Scout • Resona",
            subjectSpecialty: "Otorhinolaryngology (ENT)",
            faction: .demon,
            intelPower: GuardianPower(
                powerId: "SONIC_RESONANCE",
                powerName: "Sonic Resonance",
                powerCategory: .overlay,
                description: "Acoustic frequency tuning reveals hidden diagnostic clues in the question stem.",
                cooldownRounds: 1,
                chargesPerQuiz: 3,
                avatarIndex: 1015,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char15_resona.glb", backgroundImageUrl: "backgrounds/bg_char15_resona.jpg", rimColorHex: 0xBA68C8),
                iconResName: "ic_power_resona_intel"
            ),
            strikePower: GuardianPower(
                powerId: "MYRINGOTOMY_PROBE",
                powerName: "Myringotomy Probe",
                powerCategory: .elimination,
                description: "Ventilates trapped diagnostic pressure by eliminating 1 deceptive distractor choice.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1015,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char15_resona.glb", backgroundImageUrl: "backgrounds/bg_char15_resona.jpg", rimColorHex: 0xBA68C8),
                iconResName: "ic_power_resona_strike"
            ),
            defensePower: GuardianPower(
                powerId: "TYMPANIC_MEMBRANE",
                powerName: "Tympanic Membrane",
                powerCategory: .safetyNet,
                description: "Vibratory acoustic damping absorbs errors, neutralizing negative marking on one answer.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1015,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char15_resona.glb", backgroundImageUrl: "backgrounds/bg_char15_resona.jpg", rimColorHex: 0xBA68C8),
                iconResName: "ic_power_resona_defense"
            ),
            surgePower: GuardianPower(
                powerId: "HARMONIC_AMPLIFICATION",
                powerName: "Harmonic Amplification",
                powerCategory: .timeScore,
                description: "Resonates across the auditory cortex, amplifying correct solve score by 1.5x.",
                cooldownRounds: 3,
                chargesPerQuiz: 1,
                avatarIndex: 1015,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char15_resona.glb", backgroundImageUrl: "backgrounds/bg_char15_resona.jpg", rimColorHex: 0xBA68C8),
                iconResName: "ic_power_resona_surge"
            ),
            story: GuardianStories.getStory(avatarIndex: 1015)!
        ),

        // 16. DERMA • DERMATOLOGY
        1016: GuardianHeroKit(
            avatarIndex: 1016,
            championName: "Epidermal Shield Barrier • Derma",
            subjectSpecialty: "Dermatology & Venereology",
            faction: .human,
            intelPower: GuardianPower(
                powerId: "DERMOSCOPY_PATTERN",
                powerName: "Dermoscopy Pattern",
                powerCategory: .overlay,
                description: "Inspects pigmentary networks to distinguish benign simulators from malignant traps.",
                cooldownRounds: 1,
                chargesPerQuiz: 3,
                avatarIndex: 1016,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char16_derma.glb", backgroundImageUrl: "backgrounds/bg_char16_derma.jpg", rimColorHex: 0xFFB74D),
                iconResName: "ic_power_derma_intel"
            ),
            strikePower: GuardianPower(
                powerId: "CRYOTHERAPY_FREEZE",
                powerName: "Cryotherapy Freeze",
                powerCategory: .elimination,
                description: "Applies liquid nitrogen logic, freezing and eliminating 1 hazardous distractor lesion.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1016,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char16_derma.glb", backgroundImageUrl: "backgrounds/bg_char16_derma.jpg", rimColorHex: 0xFFB74D),
                iconResName: "ic_power_derma_strike"
            ),
            defensePower: GuardianPower(
                powerId: "EPIDERMAL_BARRIER",
                powerName: "Epidermal Barrier",
                powerCategory: .safetyNet,
                description: "Multilayered keratin protective shield completely blocks negative marking on one error.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1016,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char16_derma.glb", backgroundImageUrl: "backgrounds/bg_char16_derma.jpg", rimColorHex: 0xFFB74D),
                iconResName: "ic_power_derma_defense"
            ),
            surgePower: GuardianPower(
                powerId: "STRATUM_LUCIDUM_GLOW",
                powerName: "Stratum Glow",
                powerCategory: .timeScore,
                description: "A radiant keratin shield illuminates clarity, yielding 1.5x score points on correct answer.",
                cooldownRounds: 3,
                chargesPerQuiz: 1,
                avatarIndex: 1016,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char16_derma.glb", backgroundImageUrl: "backgrounds/bg_char16_derma.jpg", rimColorHex: 0xFFB74D),
                iconResName: "ic_power_derma_surge"
            ),
            story: GuardianStories.getStory(avatarIndex: 1016)!
        ),

        // 17. SYNAPSE • PSYCHIATRY
        1017: GuardianHeroKit(
            avatarIndex: 1017,
            championName: "Neural Psionic Mystic • Synapse",
            subjectSpecialty: "Psychiatry & Behavioral Sciences",
            faction: .angel,
            intelPower: GuardianPower(
                powerId: "MSE_COGNITIVE_SCAN",
                powerName: "MSE Cognitive Scan",
                powerCategory: .overlay,
                description: "Performs a rapid mental status examination, highlighting emotional and cognitive indicators.",
                cooldownRounds: 1,
                chargesPerQuiz: 3,
                avatarIndex: 1017,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char17_synapse.glb", backgroundImageUrl: "backgrounds/bg_char17_synapse.jpg", rimColorHex: 0x7E57C2),
                iconResName: "ic_power_synapse_intel"
            ),
            strikePower: GuardianPower(
                powerId: "SYNAPTIC_PRUNING",
                powerName: "Synaptic Pruning",
                powerCategory: .elimination,
                description: "Prunes redundant neuro-pathways, clearing 1 confusing cognitive trap from the choices.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1017,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char17_synapse.glb", backgroundImageUrl: "backgrounds/bg_char17_synapse.jpg", rimColorHex: 0x7E57C2),
                iconResName: "ic_power_synapse_strike"
            ),
            defensePower: GuardianPower(
                powerId: "NEURAL_CALM",
                powerName: "Neural Calm",
                powerCategory: .timeScore,
                description: "Soothes exam panic, pausing countdown tension for 8 seconds and restoring clarity.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1017,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char17_synapse.glb", backgroundImageUrl: "backgrounds/bg_char17_synapse.jpg", rimColorHex: 0x7E57C2),
                iconResName: "ic_power_synapse_defense"
            ),
            surgePower: GuardianPower(
                powerId: "COGNITIVE_RESTRUCTURING",
                powerName: "Cognitive Restructuring",
                powerCategory: .safetyNet,
                description: "Reframes cognitive distortion, granting a second attempt without penalty if your choice misses.",
                cooldownRounds: 3,
                chargesPerQuiz: 1,
                avatarIndex: 1017,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char17_synapse.glb", backgroundImageUrl: "backgrounds/bg_char17_synapse.jpg", rimColorHex: 0x7E57C2),
                iconResName: "ic_power_synapse_surge"
            ),
            story: GuardianStories.getStory(avatarIndex: 1017)!
        ),

        // 18. RAYNE • RADIODIAGNOSIS
        1018: GuardianHeroKit(
            avatarIndex: 1018,
            championName: "Photon Recon Scout • Rayne",
            subjectSpecialty: "Radiodiagnosis & Imaging",
            faction: .human,
            intelPower: GuardianPower(
                powerId: "PHOTON_SCAN",
                powerName: "Photon Scan",
                powerCategory: .overlay,
                description: "Penetrates opaque diagnostic dilemmas, revealing high-yield radiological findings.",
                cooldownRounds: 1,
                chargesPerQuiz: 3,
                avatarIndex: 1018,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char18_rayne.glb", backgroundImageUrl: "backgrounds/bg_char18_rayne.jpg", rimColorHex: 0x29B6F6),
                iconResName: "ic_power_rayne_intel"
            ),
            strikePower: GuardianPower(
                powerId: "FOCUSED_XRAY_BEAM",
                powerName: "Focused X-Ray Beam",
                powerCategory: .elimination,
                description: "Fires a collimated high-kV beam that dissolves 2 false diagnostic radiological artifacts.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1018,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char18_rayne.glb", backgroundImageUrl: "backgrounds/bg_char18_rayne.jpg", rimColorHex: 0x29B6F6),
                iconResName: "ic_power_rayne_strike"
            ),
            defensePower: GuardianPower(
                powerId: "LEAD_APRON_BARRIER",
                powerName: "Lead Apron Barrier",
                powerCategory: .safetyNet,
                description: "Shields against ionizing exam penalty, negating negative marking on one mistake.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1018,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char18_rayne.glb", backgroundImageUrl: "backgrounds/bg_char18_rayne.jpg", rimColorHex: 0x29B6F6),
                iconResName: "ic_power_rayne_defense"
            ),
            surgePower: GuardianPower(
                powerId: "THREE_D_RECONSTRUCTION",
                powerName: "3D Reconstruction",
                powerCategory: .timeScore,
                description: "Constructs a multi-planar volumetric diagnostic view, granting double score points (2.0x).",
                cooldownRounds: 3,
                chargesPerQuiz: 1,
                avatarIndex: 1018,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char18_rayne.glb", backgroundImageUrl: "backgrounds/bg_char18_rayne.jpg", rimColorHex: 0x29B6F6),
                iconResName: "ic_power_rayne_surge"
            ),
            story: GuardianStories.getStory(avatarIndex: 1018)!
        ),

        // 19. SOMNUS • ANESTHESIOLOGY
        1019: GuardianHeroKit(
            avatarIndex: 1019,
            championName: "Narcosis Dream-Keeper • Somnus",
            subjectSpecialty: "Anesthesiology & Critical Care",
            faction: .demon,
            intelPower: GuardianPower(
                powerId: "MAC_VOLATILE_MONITOR",
                powerName: "MAC Volatile Monitor",
                powerCategory: .overlay,
                description: "Monitors end-tidal anesthetic depth and vitals, illuminating subtle physiological clues.",
                cooldownRounds: 1,
                chargesPerQuiz: 3,
                avatarIndex: 1019,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char19_somnus.glb", backgroundImageUrl: "backgrounds/bg_char19_somnus.jpg", rimColorHex: 0x9575CD),
                iconResName: "ic_power_somnus_intel"
            ),
            strikePower: GuardianPower(
                powerId: "LARYNGOSCOPIC_SWEEP",
                powerName: "Laryngoscopic Sweep",
                powerCategory: .elimination,
                description: "Sweeps the tongue and epiglottis, directly visualizing the glottis and eliminating 1 distractor.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1019,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char19_somnus.glb", backgroundImageUrl: "backgrounds/bg_char19_somnus.jpg", rimColorHex: 0x9575CD),
                iconResName: "ic_power_somnus_strike"
            ),
            defensePower: GuardianPower(
                powerId: "NARCOSIS_FIELD",
                powerName: "Narcosis Field",
                powerCategory: .safetyNet,
                description: "Soothes systemic penalty, stabilizing vital signs and reviving lost streak HP on error.",
                cooldownRounds: 2,
                chargesPerQuiz: 2,
                avatarIndex: 1019,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char19_somnus.glb", backgroundImageUrl: "backgrounds/bg_char19_somnus.jpg", rimColorHex: 0x9575CD),
                iconResName: "ic_power_somnus_defense"
            ),
            surgePower: GuardianPower(
                powerId: "EMERGENCE_ACCELERATION",
                powerName: "Emergence Acceleration",
                powerCategory: .timeScore,
                description: "Smoothly awakens cerebral clarity with zero post-op delirium, yielding 1.5x score bonus.",
                cooldownRounds: 3,
                chargesPerQuiz: 1,
                avatarIndex: 1019,
                renderConfig: Guardian3DConfig(modelGlbUrl: "char19_somnus.glb", backgroundImageUrl: "backgrounds/bg_char19_somnus.jpg", rimColorHex: 0x9575CD),
                iconResName: "ic_power_somnus_surge"
            ),
            story: GuardianStories.getStory(avatarIndex: 1019)!
        )
    ]

    /// Map a Warrior's 1-based ID (1...27) to their 1000-based Avatar Index if available
    static func avatarIndex(for warriorId: Int) -> Int {
        if warriorId >= 1 && warriorId <= 19 {
            return 1000 + warriorId
        }
        return 1000 + ((warriorId - 1) % 19 + 1)
    }

    /// Retrieve the 4-power hero kit by avatar index or warrior ID.
    static func getHeroKit(for avatarIndex: Int) -> GuardianHeroKit? {
        if let kit = heroKits[avatarIndex] {
            return kit
        }
        let mappedIndex = 1000 + ((avatarIndex - 1) % 19 + 1)
        return heroKits[mappedIndex]
    }

    /// Tactical text analysis for any power.
    static func tacticalDynamicsText(for power: GuardianPower) -> String {
        switch power.powerId {
        // Intel powers
        case "FASCIAL_PLANE_SCAN": return "🔍 TACTICAL SCAN: Highlights fascia & neurovascular landmarks, cutting question stem ambiguity."
        case "ECG_RHYTHM_TRACE": return "🔍 TACTICAL SCAN: Traces electrical conduction vector, locking the diagnostic lead."
        case "METABOLIC_PATHWAY_MAP": return "🔍 TACTICAL SCAN: Illuminates enzyme crossroads & rate-limiting regulatory steps."
        case "BIOPSY_STAIN": return "🔍 TACTICAL SCAN: Stains histological markers (H&E / Congo Red) revealing cellular pathognomonic keys."
        case "RECEPTOR_BINDING_SCAN": return "🔍 TACTICAL SCAN: Scans agonist/antagonist affinity kinetics to isolate drug mechanism."
        case "GRAM_STAIN_ID": return "🔍 TACTICAL SCAN: Differentiates cell wall peptidoglycan morphology, pinpointing pathogen class."
        case "FORENSIC_AUTOPSY": return "🔍 TACTICAL SCAN: Uncovers forensic post-mortem markers and legal causality clues."
        case "INCIDENCE_MAPPER": return "🔍 TACTICAL SCAN: Calculates odds ratio & relative risk metrics to filter statistical traps."
        case "SLIT_LAMP_BEAM": return "🔍 TACTICAL SCAN: Focused optical beam cuts through corneal and retinal confounders."
        case "ACOUSTIC_SPECTROGRAM": return "🔍 TACTICAL SCAN: Decodes frequency wave patterns, filtering audio-otolaryngology clues."
        case "DIAGNOSTIC_LAPAROSCOPY": return "🔍 TACTICAL SCAN: Visualizes abdominal quadrant anatomy with 4K surgical fiberoptics."
        case "DEVELOPMENTAL_MILESTONE": return "🔍 TACTICAL SCAN: Maps chronological pediatric growth percentiles to rule out outliers."
        case "TRABECULAR_STRESS_MAP": return "🔍 TACTICAL SCAN: Analyzes bone load vectors and ligamentous stress zones."
        case "DERMATOSCOPY_POLAR": return "🔍 TACTICAL SCAN: Cross-polarized light reveals sub-epidermal melanin distribution."
        case "VOXEL_RECONSTRUCTION": return "🔍 TACTICAL SCAN: Reconstructs high-resolution multi-planar CT/MRI slices."
        case "MENTAL_STATUS_EXAM": return "🔍 TACTICAL SCAN: Isolates psychiatric affect, thought form, and cognitive delusions."
        case "ANESTHETIC_DEPTH_MONITOR": return "🔍 TACTICAL SCAN: Tracks EEG bispectral index (BIS) to assess hypnotic depth."
        case "LABOR_PARTOGRAM": return "🔍 TACTICAL SCAN: Plots cervical dilatation curves against alert and action lines."
        case "CHRONOTHERAPY_MAP": return "🔍 TACTICAL SCAN: Synchronizes circadian hormone rhythms with peak therapeutic windows."

        // Strike powers
        case "OSTEOTOME_CHISEL", "ENZYME_CLEAVAGE", "PETRI_CONTAINMENT", "MICROSURGICAL_EXCISION",
             "DERMATOME_DEBRIDEMENT", "STRESS_FRACTURE_CLEAVE", "TOXICOLOGY_FLUSH", "EXHAUSTION_STRIKE":
            return "🎯 SURGICAL EXCISION: Vaporizes 1 high-probability distractor trap option with extreme precision."
        case "DEFIBRILLATOR_SHOCK", "CELLULAR_NECROSIS", "ANTAGONIST_BLOCK", "LETHAL_TRIAD_PUNCH",
             "VECTOR_ERADICATION", "PHAKIC_ABLATION", "TYMPANOCENTESIS_DRAIN", "SCALPEL_RESECTION",
             "CYTOKINE_PURGE", "FRACTURE_REDUCTION", "CORONA_INCISION", "CONTRAST_WASHOUT",
             "SYNAPSE_ABLATION", "ISOMER_SHATTER":
            return "🎯 SURGICAL EXCISION: Cleaves 2 misleading distractor options simultaneously, leaving a 50/50 duel."

        // Defense powers
        case "RIBCAGE_BASTION", "BUFFER_EQUILIBRIUM", "APOPTOSIS_WARD", "STERILE_ISOLATION",
             "EPIDEMIC_QUARANTINE", "CLINICAL_STABILIZER", "HEMOSTATIC_CLAMP", "PEDIATRIC_IMMUNITY",
             "ORTHOPEDIC_CAST", "CORNEAL_SHIELD", "TYMPANIC_MEMBRANE", "EPIDERMAL_BARRIER",
             "LEAD_APRON_BARRIER", "NARCOSIS_FIELD", "CARAPACE_SHIELD":
            return "🛡️ WARD OF PROTECTION: Negates next incorrect answer penalty (-1 point penalty absorbed) & sustains streak."
        case "VAGAL_REFRACTORY", "NEURAL_CALM":
            return "⏱️ REFRACTORY CALM: Freezes quiz countdown timer for 6 seconds while stabilizing thinking composure."
        case "TWENTY_TWENTY_CLARITY", "BASTION_FREEZE":
            return "⏱️ CHRONO STASIS: Freezes question timer for 8 seconds to allow thorough vignette analysis."
        case "ADRENALINE_SURGE", "RECEPTOR_ANTIDOTE", "JURISPRUDENCE_IMMUNITY", "FETAL_HEART_SHIELD", "COGNITIVE_RESTRUCTURING":
            return "🛡️ RESURRECTION: Grants a second chance retry if the first selected option is wrong."

        // Surge powers
        case "BIOELECTRIC_SURGE", "ATP_SURGE", "ADRENALINE_INFUSION", "POST_MORTEM_CERTAINTY",
             "HERD_IMMUNITY", "GRAND_ROUNDS_INSIGHT", "PARTURITION_POWER", "THREE_D_RECONSTRUCTION", "BLITZ_BONUS":
            return "⚡ HIGH-YIELD SURGE: 2.0x DOUBLE SCORE multiplier on correct diagnosis & +50 Arena Combat Momentum."
        case "BERSERK_SOLVE":
            return "⚡ HIGH-YIELD SURGE: 3.0x TRIPLE SCORE multiplier on rapid answer submission."
        case "TIME_SIPHON", "DOMINANT_TIMER":
            return "⚡ CHRONO SURGE: Adds +15s bonus clock time to master high-yield multi-step calculations."
        default:
            switch power.powerCategory {
            case .overlay: return "🔍 TACTICAL SCAN: Highlights core high-yield keywords & eliminates vignette distractors."
            case .elimination: return "🎯 SURGICAL EXCISION: Vaporizes \(power.chargesPerQuiz <= 2 ? 2 : 1) incorrect options from the duel."
            case .safetyNet: return "🛡️ WARD OF PROTECTION: Absorbs negative mark (-1 penalty) & maintains bonus score streak."
            case .timeScore: return "⚡ HIGH-YIELD SURGE: 1.5x score bonus multiplier for consecutive rapid correct answers."
            case .textFormat: return "📝 CLINICAL CLARITY: Restructures confusing terminology into high-yield core bullet points."
            }
        }
    }
}
