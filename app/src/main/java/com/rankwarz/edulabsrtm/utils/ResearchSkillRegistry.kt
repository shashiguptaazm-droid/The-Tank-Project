package com.rankwarz.edulabsrtm.utils

import org.json.JSONObject

data class ResearchSkill(
    val id: Int,
    val name: String,
    val description: String,
    val category: String,
    val isDeterministic: Boolean = false
)

object ResearchSkillRegistry {
    val SKILLS = listOf(
        // 🔎 Research & Question Skills (1-10)
        ResearchSkill(1, "Research Question Analyzer", "Understands the user's research question.", "Research"),
        ResearchSkill(2, "PICO/PECO Extractor", "Extracts Population, Intervention/Exposure, Comparison and Outcome.", "Research"),
        ResearchSkill(3, "Research Type Classifier", "Identifies RCT, cohort, case-control, systematic review, thesis, etc.", "Research"),
        ResearchSkill(4, "Objective Generator", "Creates primary and secondary objectives.", "Research"),
        ResearchSkill(5, "Hypothesis Generator", "Generates null/alternative hypotheses.", "Research"),
        ResearchSkill(6, "Variable Extractor", "Identifies independent, dependent and confounding variables.", "Research"),
        ResearchSkill(7, "Outcome Definition", "Converts outcomes into measurable endpoints.", "Research"),
        ResearchSkill(8, "Eligibility Criteria Builder", "Creates inclusion/exclusion criteria.", "Research"),
        ResearchSkill(9, "Study Design Advisor", "Suggests appropriate study design.", "Research"),
        ResearchSkill(10, "Research Gap Finder", "Finds unanswered questions in existing literature.", "Research"),

        // 📚 Literature Search Skills (11-20)
        ResearchSkill(11, "PubMed Search Builder", "Creates optimized PubMed/MeSH/Boolean queries.", "Search"),
        ResearchSkill(12, "PubMed Search", "Retrieves relevant publications.", "Search", true),
        ResearchSkill(13, "MeSH Mapper", "Maps medical concepts to MeSH terms.", "Search"),
        ResearchSkill(14, "Synonym Generator", "Expands terminology and abbreviations.", "Search"),
        ResearchSkill(15, "Article Deduplicator", "Removes duplicate papers.", "Search", true),
        ResearchSkill(16, "Article Relevance Ranker", "Scores papers against the research question.", "Search"),
        ResearchSkill(17, "Citation Chaining", "Finds references and citing papers.", "Search"),
        ResearchSkill(18, "Similar Article Finder", "Finds related research.", "Search", true),
        ResearchSkill(19, "Full-Text Retriever", "Retrieves available article content.", "Search", true),
        ResearchSkill(20, "Literature Timeline", "Organizes research chronologically.", "Search"),

        // ✅ Validation Skills (21-30) - All Deterministic
        ResearchSkill(21, "PMID Validator", "Confirms PMID and article identity.", "Validation", true),
        ResearchSkill(22, "DOI Validator", "Verifies DOI and metadata.", "Validation", true),
        ResearchSkill(23, "Citation Validator", "Checks authors, title, journal, year, pages, etc.", "Validation", true),
        ResearchSkill(24, "Vancouver Formatter", "Generates validated Vancouver references.", "Validation", true),
        ResearchSkill(25, "Reference Consistency Checker", "Checks in-text citations vs bibliography.", "Validation", true),
        ResearchSkill(26, "Source Provenance Tracker", "Records where every claim came from.", "Validation", true),
        ResearchSkill(27, "Evidence Extractor", "Extracts evidence supporting claims.", "Validation", true),
        ResearchSkill(28, "Claim Verification", "Checks claim ↔ source correspondence.", "Validation", true),
        ResearchSkill(29, "Evidence-Level Classifier", "Classifies strength/type of evidence.", "Validation", true),
        ResearchSkill(30, "Conflicting Evidence Detector", "Finds contradictory study results.", "Validation", true),

        // 🧬 Medical Data Skills (31-40)
        ResearchSkill(31, "Medical Entity Extractor", "Extracts diseases, drugs, anatomy, procedures, etc.", "Data"),
        ResearchSkill(32, "Clinical Fact Extractor", "Extracts symptoms, signs, diagnosis and treatment facts.", "Data"),
        ResearchSkill(33, "Study Metadata Extractor", "Extracts design, sample size, population, duration, location.", "Data"),
        ResearchSkill(34, "Numerical Data Extractor", "Extracts OR, RR, HR, CI, p-values, means, percentages.", "Data"),
        ResearchSkill(35, "Table Extraction", "Converts research tables into structured data.", "Data"),
        ResearchSkill(36, "Outcome Extractor", "Identifies primary and secondary outcomes.", "Data"),
        ResearchSkill(37, "Intervention Extractor", "Extracts treatments, doses and protocols.", "Data"),
        ResearchSkill(38, "Adverse Event Extractor", "Extracts complications and adverse effects.", "Data"),
        ResearchSkill(39, "Study Quality Analyzer", "Assesses methodological quality/risk-of-bias information.", "Data"),
        ResearchSkill(40, "Evidence Dataset Builder", "Converts extracted information into your database schema.", "Data"),

        // 🧠 Analysis & Research Generation (41-50)
        ResearchSkill(41, "Evidence Synthesizer", "Combines findings from multiple studies.", "Generation"),
        ResearchSkill(42, "Study Comparison Engine", "Compares studies side-by-side.", "Generation"),
        ResearchSkill(43, "Statistical Analysis Planner", "Selects appropriate statistical approaches.", "Generation"),
        ResearchSkill(44, "Statistical Calculator", "Performs validated statistical calculations.", "Generation", true),
        ResearchSkill(45, "Bias & Confounder Detector", "Identifies methodological problems.", "Generation"),
        ResearchSkill(46, "Thesis Writer", "Generates structured thesis sections from verified evidence.", "Generation"),
        ResearchSkill(47, "Discussion Generator", "Compares findings with previous literature.", "Generation"),
        ResearchSkill(48, "Abstract Generator", "Creates structured research abstracts.", "Generation"),
        ResearchSkill(49, "Future Research Generator", "Identifies unanswered questions and future studies.", "Generation"),
        ResearchSkill(50, "Final Research Auditor", "Checks every claim, citation, number and reference before the final answer.", "Generation", true),

        // 🎓 Medical Education & Clinical Reasoning (51-60)
        ResearchSkill(51, "Case Study Generator", "Creates realistic patient scenarios for clinical reasoning practice.", "Education"),
        ResearchSkill(52, "Differential Diagnosis Builder", "Guides students from symptoms to a prioritized list of diagnoses.", "Education"),
        ResearchSkill(53, "Medical Mnemonic Creator", "Generates high-retention memory aids for complex medical facts.", "Education"),
        ResearchSkill(54, "Socratic Medical Tutor", "Interactive tutoring that guides students via questioning.", "Education"),
        ResearchSkill(55, "Guideline Distiller", "Summarizes official clinical guidelines (AHA, GOLD, etc.) for quick review.", "Education"),
        ResearchSkill(56, "Anatomy Atlas Linker", "Correlates medical terms with detailed anatomical structures.", "Education"),
        ResearchSkill(57, "Clinical Pearl Extractor", "Identifies high-yield 'pearls' and 'pitfalls' for specific conditions.", "Education"),
        ResearchSkill(58, "Journal Club Assistant", "Helps students critique the methodology and results of a research paper.", "Education"),
        ResearchSkill(59, "Medical Ethics Analyzer", "Explores ethical dilemmas and legal frameworks in healthcare.", "Education"),
        ResearchSkill(60, "Radiology/Image Interpreter", "Guides the systematic approach to reading X-rays, CTs, and MRIs.", "Education"),

        // 🩺 Specialized Clinical Skills (61-70)
        ResearchSkill(61, "Pharmacology Mechanism Mapper", "Explains drug mechanisms of action and pathopharmacology.", "Clinical"),
        ResearchSkill(62, "Lab Value Interpreter", "Analyzes abnormal lab results and suggests underlying causes.", "Clinical"),
        ResearchSkill(63, "Procedural Step-by-Step", "Provides detailed walkthroughs for common medical procedures.", "Clinical"),
        ResearchSkill(64, "Physical Exam Protocol", "Outlines standardized physical examination techniques.", "Clinical"),
        ResearchSkill(65, "Triage Decision Support", "Assists in learning patient prioritization and triage logic.", "Clinical"),
        ResearchSkill(66, "Drug Interaction Checker", "Analyzes potential interactions between multiple medications.", "Clinical"),
        ResearchSkill(67, "Surgical Anatomy Review", "Reviews surgical planes and critical structures for specific operations.", "Clinical"),
        ResearchSkill(68, "Emergency Protocol Guide", "Walks through ACLS, BLS, and trauma primary surveys.", "Clinical"),
        ResearchSkill(69, "Pediatric Dose Calculator", "Educational tool for learning weight-based dosing logic.", "Clinical", true),
        ResearchSkill(70, "Obstetric Risk Assessor", "Teaches identification of high-risk factors in pregnancy.", "Clinical"),

        // 🎓 Advanced Education & Reasoning (71-100)
        ResearchSkill(71, "Prompt Engineering for Medics", "Templates for high-accuracy medical AI queries.", "Education"),
        ResearchSkill(72, "Virtual Patient Simulation", "Interactive case-taking with AI-driven patient personas.", "Education"),
        ResearchSkill(73, "MCQ Distractor Analyzer", "Explains logic behind incorrect exam options.", "Education"),
        ResearchSkill(74, "Medical Concept Mapper", "Visualizes hierarchies between clinical terms.", "Education"),
        ResearchSkill(75, "Spaced Repetition Flashcarder", "Generates Anki-ready facts from research text.", "Education"),
        ResearchSkill(76, "Curriculum Alignment Guide", "Maps study material to NEET PG/USMLE standards.", "Education"),
        ResearchSkill(77, "Socratic Clinical Tutor", "Guides reasoning via interactive questioning.", "Education"),
        ResearchSkill(78, "Medical Error Predictor", "Flags common student pitfalls in specific topics.", "Education"),
        ResearchSkill(79, "High-Yield Fact Extractor", "Condenses long text into exam-ready bullet points.", "Education"),
        ResearchSkill(80, "Clinical Pearl Generator", "Creates memorable clinical 'pearls' for retention.", "Education"),
        ResearchSkill(81, "Anatomy Spatial Relation Trainer", "Tests spatial logic of anatomical structures.", "Education"),
        ResearchSkill(82, "Histology/Radiology Quizzer", "Text-based description identification for images.", "Education"),
        ResearchSkill(83, "Evidence Level Classifier", "Teaches the grading of scientific evidence quality.", "Education"),
        ResearchSkill(84, "Research Gap Identifier", "Finds unanswered questions in recent papers.", "Education"),
        ResearchSkill(85, "Medical Abbreviations Decoder", "Standardizes complex clinical shorthand.", "Education"),
        ResearchSkill(86, "Logical Fallacy Detector", "Checks clinical arguments for reasoning errors.", "Education"),
        ResearchSkill(87, "Patient Scenario Randomizer", "Generates infinite variations of a base case.", "Education"),
        ResearchSkill(88, "Medical Trivia Engine", "Gamified learning of rare medical facts.", "Education"),
        ResearchSkill(89, "Peer Review Simulator", "Critiques a student's research draft for quality.", "Education"),
        ResearchSkill(90, "Grant Proposal Optimizer", "Aligns research ideas with funding criteria.", "Education"),
        ResearchSkill(91, "Qualitative Theme Coder", "Extracts themes from patient interviews.", "Education"),
        ResearchSkill(92, "Multilingual Research Bridge", "Summarizes foreign medical journals.", "Education"),
        ResearchSkill(93, "Bibliometric Impact Analyzer", "Analyzes the reach of specific medical researchers.", "Education"),
        ResearchSkill(94, "Conflict of Interest Screener", "Scans author lists for potential biases.", "Education"),
        ResearchSkill(95, "PRISMA Checklist Validator", "Checks if a paper follows systematic review rules.", "Education"),
        ResearchSkill(96, "Bioinformatics Linkage Assistant", "Connects genomic data to clinical diseases.", "Education"),
        ResearchSkill(97, "Statistical Power Calculator", "Educational logic for sample size determination.", "Education"),
        ResearchSkill(98, "Forest Plot Interpreter", "Explains meta-analysis charts simply.", "Education"),
        ResearchSkill(99, "Ethical Dilemma Solver", "Guides through the 4 principles of medical ethics.", "Education"),
        ResearchSkill(100, "Clinical Workflow Visualizer", "Maps the steps from admission to discharge.", "Education"),

        // 📝 Clinical Efficiency & Support (101-125)
        ResearchSkill(101, "SOAP Note Assistant", "Structures patient encounters into SOAP format.", "Clinical Efficiency"),
        ResearchSkill(102, "Discharge Summary Drafter", "Summarizes hospital stays for planning.", "Clinical Efficiency"),
        ResearchSkill(103, "ICD-10/11 Code Suggester", "Suggests billing codes based on clinical notes.", "Clinical Efficiency"),
        ResearchSkill(104, "Referral Letter Drafter", "Professional writing for specialty consultations.", "Clinical Efficiency"),
        ResearchSkill(105, "Radiology Report Simplifier", "Converts jargon into patient-friendly text.", "Clinical Efficiency"),
        ResearchSkill(106, "Prescription Safety Auditor", "Checks for dosing and interaction risks.", "Clinical Efficiency"),
        ResearchSkill(107, "Ambient Scribe Integration", "Prepares for real-time voice-to-text notes.", "Clinical Efficiency"),
        ResearchSkill(108, "EHR Narrative Cleaner", "Removes repetitive data from messy clinical logs.", "Clinical Efficiency"),
        ResearchSkill(109, "H&P Admission Template", "Structures the History and Physical exam.", "Clinical Efficiency"),
        ResearchSkill(110, "Medication Reconciliation Aid", "Cross-checks home vs. inpatient med lists.", "Clinical Efficiency"),
        ResearchSkill(111, "Surgical Consent Outline", "Lists specific risks and benefits for surgery.", "Clinical Efficiency"),
        ResearchSkill(112, "Patient Education Pamphlet", "Generates customized health advice documents.", "Clinical Efficiency"),
        ResearchSkill(113, "Lab Order Prioritizer", "Suggests the most critical first-line labs.", "Clinical Efficiency"),
        ResearchSkill(114, "Triage Urgency Scorer", "Predicts case severity using standard scales.", "Clinical Efficiency"),
        ResearchSkill(115, "Inpatient Handoff Summary", "Structures the SBAR (Situation-Background-Assessment-Recommendation).", "Clinical Efficiency"),
        ResearchSkill(116, "Diagnostic Algorithm Builder", "Creates step-by-step logic for symptom workup.", "Clinical Efficiency"),
        ResearchSkill(117, "Rare Disease Finder", "Suggests 'Zebra' diagnoses for complex cases.", "Clinical Efficiency"),
        ResearchSkill(118, "Antibiotic Stewardship Advisor", "Suggests narrow-spectrum alternatives.", "Clinical Efficiency"),
        ResearchSkill(119, "Geriatric Polypharmacy Alert", "Flags high-risk med combos in elderly patients.", "Clinical Efficiency"),
        ResearchSkill(120, "Pediatric Developmental Tracker", "Compares milestones to WHO/CDC standards.", "Clinical Efficiency"),
        ResearchSkill(121, "ABG Acid-Base Solver", "Calculates anion gap and compensation.", "Clinical Efficiency"),
        ResearchSkill(122, "ECG Waveform Description", "Guided systematic reading of heart rhythms.", "Clinical Efficiency"),
        ResearchSkill(123, "Psychiatric Mental Status Exam", "Standardizes behavioral health assessments.", "Clinical Efficiency"),
        ResearchSkill(124, "Clinical Guidelines Distiller", "Summarizes AHA/ACC/NICE guidelines.", "Clinical Efficiency"),
        ResearchSkill(125, "Treatment Personalization Engine", "Matches patient traits to targeted therapies.", "Clinical Efficiency"),

        // 🩺 Advanced Diagnostics & Specialization (126-150)
        ResearchSkill(126, "Dermatological Morphology Guide", "Analyzes lesion descriptions for classification.", "Diagnostics"),
        ResearchSkill(127, "Neurological Localization Logic", "Pinpoints deficits to specific CNS/PNS levels.", "Diagnostics"),
        ResearchSkill(128, "Infectious Outbreak Watcher", "Analyzes local case data for trends.", "Diagnostics"),
        ResearchSkill(129, "Toxicology Antidote Finder", "Rapid lookup for poisoning management.", "Diagnostics"),
        ResearchSkill(130, "Palliative Symptom Manager", "Focuses on comfort-based clinical protocols.", "Diagnostics"),
        ResearchSkill(131, "Genetic Variant Interpreter", "Explains the significance of SNP findings.", "Diagnostics"),
        ResearchSkill(132, "Precision Oncology Matcher", "Links biomarkers to drug trials.", "Diagnostics"),
        ResearchSkill(133, "Pharmacogenomics Advisor", "Gene-drug metabolism interaction guide.", "Diagnostics"),
        ResearchSkill(134, "Cardiovascular Risk Scorer", "Calculates ASCVD and other risk profiles.", "Diagnostics"),
        ResearchSkill(135, "Renal Function Auditor", "Calculates GFR and suggests dose adjusts.", "Diagnostics"),
        ResearchSkill(136, "Pulmonary Function Interpreter", "Analyzes spirometry for obstruction/restriction.", "Diagnostics"),
        ResearchSkill(137, "Endocrine Panel Analyzer", "Coordinates TSH/T4/Cortisol feedback logic.", "Diagnostics"),
        ResearchSkill(138, "Hematology Differential Guide", "Breaks down CBC results and morphology.", "Diagnostics"),
        ResearchSkill(139, "Surgical Plane Reviewer", "Reviews critical anatomy for procedures.", "Diagnostics"),
        ResearchSkill(140, "Obstetric Ultrasound Sync", "Correlates dates with biometric measurements.", "Diagnostics"),
        ResearchSkill(141, "Neonatal Triage Scorer", "Analyzes APGAR and newborn risk factors.", "Diagnostics"),
        ResearchSkill(142, "Autoimmune Serology Map", "Links antibodies to specific diseases.", "Diagnostics"),
        ResearchSkill(143, "Fluid & Electrolyte Planner", "Calculates deficit and replacement rates.", "Diagnostics"),
        ResearchSkill(144, "Trauma Primary Survey Guide", "Step-by-step logic for ATLS protocol.", "Diagnostics"),
        ResearchSkill(145, "Malignancy Staging Assistant", "Guides through TNM classification logic.", "Diagnostics"),
        ResearchSkill(146, "Nutrition & Micro-nutrient Audit", "Identifies deficiencies in dietary logs.", "Diagnostics"),
        ResearchSkill(147, "Pain Management Protocol", "Step-ladder approach to analgesia.", "Diagnostics"),
        ResearchSkill(148, "Sleep Hygiene Analyzer", "Interprets sleep logs for insomnia causes.", "Diagnostics"),
        ResearchSkill(149, "Sports Medicine Injury Logic", "Mechanisms of injury to ligament grading.", "Diagnostics"),
        ResearchSkill(150, "Occupational Health Hazard Map", "Links environment to chronic symptoms.", "Diagnostics"),

        // 🤝 Interaction & Patient Communication (151-170)
        ResearchSkill(151, "Breaking Bad News Simulator", "Practices SPIKES protocol communication.", "Interaction"),
        ResearchSkill(152, "Motivational Interviewing Aid", "Techniques for behavioral change talks.", "Interaction"),
        ResearchSkill(153, "Health Literacy Level Tester", "Checks if text is too complex for patients.", "Interaction"),
        ResearchSkill(154, "Cross-Cultural Care Guide", "Advises on religious/cultural health beliefs.", "Interaction"),
        ResearchSkill(155, "Shared Decision Making Helper", "Structures risk/benefit trade-off talks.", "Interaction"),
        ResearchSkill(156, "End-of-Life Talk Navigator", "Sensitive guidance for hospice discussions.", "Interaction"),
        ResearchSkill(157, "Clinical Empathy Rewriter", "Humanizes robotic clinical documentation.", "Interaction"),
        ResearchSkill(158, "De-escalation Coach", "Techniques for managing aggressive patients.", "Interaction"),
        ResearchSkill(159, "Patient Advocacy Letter", "Drafters for insurance appeals/support.", "Interaction"),
        ResearchSkill(160, "Telemedicine Protocol Guide", "Conducting effective virtual examinations.", "Interaction"),
        ResearchSkill(161, "Medical Ethics Committee Prep", "Structures cases for institutional review.", "Interaction"),
        ResearchSkill(162, "Physician Wellness Sentinel", "Identifies signs of burnout in chat logs.", "Interaction"),
        ResearchSkill(163, "Team Conflict Resolver", "Strategies for medical team disagreements.", "Interaction"),
        ResearchSkill(164, "Public Health Messaging", "Drafts community vaccine/health alerts.", "Interaction"),
        ResearchSkill(165, "Informed Consent Checker", "Ensures all legal elements are explained.", "Interaction"),
        ResearchSkill(166, "Patient Portal Auto-Responder", "Drafts replies to non-urgent portal mail.", "Interaction"),
        ResearchSkill(167, "Med-Tech Trend Watcher", "Latest wearable and sensor technology news.", "Interaction"),
        ResearchSkill(168, "Synthetic Case Generator", "Creates anonymized data for clinical testing.", "Interaction"),
        ResearchSkill(169, "Medical Prompt Engineer", "Refines user queries for better AI output.", "Interaction"),
        ResearchSkill(170, "Future Medicine Sentinel", "Identification of breakthrough therapies.", "Interaction"),

        // 🔬 Formal Thesis Protocol Gates (New)
        ResearchSkill(171, "IRB/Ethics Validator", "Ensures Ethical Committee approval and Informed Consent sections are present.", "Protocol", true),
        ResearchSkill(172, "Sample Size Calculator", "Calculates required n based on power, alpha, and expected effect size.", "Protocol", true),
        ResearchSkill(173, "Source vs Literature Separator", "Strictly distinguishes between user's primary data and external references.", "Protocol", true),
        ResearchSkill(174, "Statistical Software Auditor", "Ensures specific software versions (SPSS/R) and tests are defined.", "Protocol", true),
        ResearchSkill(175, "Discussion Logic Engine", "Enforces the 'Compare & Contrast' structure against external PMIDs.", "Protocol"),
        ResearchSkill(176, "Outcome-Objective Mapper", "Verifies every objective has a corresponding outcome and result.", "Protocol", true),

        // 💻 Research Coding & Agentic Skills (177-200)
        ResearchSkill(177, "Research Script Generator", "Generates R/Python scripts for medical data analysis.", "Coding"),
        ResearchSkill(178, "Statistical Code Debugger", "Fixes errors in research analysis scripts.", "Coding"),
        ResearchSkill(179, "Diff Change Viewer", "Shows exact line-by-line changes for code or thesis drafts.", "Coding", true),
        ResearchSkill(180, "Compiler Error Interpreter", "Explains complex stack traces and coding errors.", "Coding"),
        ResearchSkill(181, "Autonomous Coding Agent", "Plan, inspect, modify, and test research software logic.", "Coding"),
        ResearchSkill(182, "API Endpoint Designer", "Drafts PHP/REST endpoints for medical data sync.", "Coding"),
        ResearchSkill(183, "Database Schema Architect", "Designs optimized MySQL/NoSQL structures for research.", "Coding", true),
        ResearchSkill(184, "Unit Test Generator", "Creates JUnit/PHPUnit tests for research modules.", "Coding"),
        ResearchSkill(185, "Refactoring Copilot", "Optimizes legacy code for better performance.", "Coding"),

        // 📝 Systematic Review & Advanced Publishing (186-200)
        ResearchSkill(186, "Systematic Review Screener", "Screens titles/abstracts for inclusion/exclusion criteria.", "Publishing"),
        ResearchSkill(187, "Meta-Analysis Helper", "Extracts data points needed for forest plots and meta-analysis.", "Publishing"),
        ResearchSkill(188, "PRISMA Flowchart Generator", "Drafts the study flow diagram for systematic reviews.", "Publishing"),
        ResearchSkill(189, "CONSORT Compliance Checker", "Verifies RCT reporting against CONSORT standards.", "Publishing"),
        ResearchSkill(190, "STROBE Compliance Checker", "Verifies observational study reporting against STROBE standards.", "Publishing"),
        ResearchSkill(191, "JBI Critical Appraisal", "Quality assessment framework for various study types.", "Publishing"),
        ResearchSkill(192, "QUADAS-2 Analyzer", "Assesses risk of bias in diagnostic accuracy studies.", "Publishing"),
        ResearchSkill(193, "Patient Recruitment Strategy", "Plans strategies for clinical trial participant enrollment.", "Publishing"),
        ResearchSkill(194, "Pilot Study Designer", "Drafts feasibility protocols for small-scale pilot studies.", "Publishing"),
        ResearchSkill(195, "Research Protocol Reviewer", "Internal quality review before institutional submission.", "Publishing"),
        ResearchSkill(196, "Academic Cover Letter Drafter", "Professional writing for journal editor submissions.", "Publishing"),
        ResearchSkill(197, "Conference Abstract Generator", "Summarizes research for conference poster/oral submissions.", "Publishing"),
        ResearchSkill(198, "PubMed Citation Chainer", "Recursively finds related papers via reference networks.", "Publishing", true),
        ResearchSkill(199, "Medical Lexicon Normalizer", "Standardizes medical terminology to UMLS/MeSH standards.", "Publishing", true),
        ResearchSkill(200, "Research Agent Final Sentinel", "Ultimate multi-layered verification of an entire study profile.", "Publishing", true)
    )

    fun getSkill(id: Int): ResearchSkill? = SKILLS.find { it.id == id }
    fun getSkillByName(name: String): ResearchSkill? {
        val exact = SKILLS.find { it.name.equals(name, ignoreCase = true) }
        if (exact != null) return exact
        val clean = name.trim().lowercase()
        // Check alias or substring
        return SKILLS.find { skill ->
            val s = skill.name.lowercase()
            s == clean || s.contains(clean) || clean.contains(s)
        }
    }

    fun getSystemPromptExtension(): String {
        val sb = StringBuilder("\n\nRESEARCH SKILLS: You have access to the following 50 specialized medical research skills. ")
        sb.append("The app handles these automatically. When you need to use a skill, start your reply with [SKILL: Name] and the app will process it first.\n")
        SKILLS.forEach { skill ->
            sb.append("${skill.id}. ${skill.name} - ${skill.description}\n")
        }
        return sb.toString()
    }
}
