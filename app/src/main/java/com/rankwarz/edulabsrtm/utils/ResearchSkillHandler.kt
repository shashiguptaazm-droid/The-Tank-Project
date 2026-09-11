package com.rankwarz.edulabsrtm.utils

import android.content.Context
import com.rankwarz.edulabsrtm.ThesisArtBridge
import com.rankwarz.edulabsrtm.model.PubMedCitationValidator
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

data class SkillOutcome(
    val contextText: String,
    val uiNote: String = "",
    val success: Boolean = true
)

object ResearchSkillHandler {

    /** 
     * Parses AI structured output and applies it to the Workspace state.
     * This allows the AI to "manage" the workspace as a feature.
     */
    fun updateWorkspace(current: WorkspaceState, aiOutput: String): WorkspaceState {
        // Simple heuristic parser for AI commands in the reply
        var updated = current
        
        if (aiOutput.contains("[RESEARCH_QUESTION:")) {
            val q = aiOutput.substringAfter("[RESEARCH_QUESTION:").substringBefore("]").trim()
            updated = updated.copy(researchQuestion = q)
        }
        
        if (aiOutput.contains("[PICO:")) {
            // Expecting [PICO: P=..., I=..., C=..., O=...]
            val content = aiOutput.substringAfter("[PICO:").substringBefore("]")
            val p = content.substringAfter("P=").substringBefore(",").trim()
            val i = content.substringAfter("I=").substringBefore(",").trim()
            val c = content.substringAfter("C=").substringBefore(",").trim()
            val o = content.substringAfter("O=").trim()
            updated = updated.copy(pico = PicoData(p, i, c, o))
        }
        
        if (aiOutput.contains("[SECTION:")) {
            val section = aiOutput.substringAfter("[SECTION:").substringBefore("]").trim()
            updated = updated.copy(currentSection = section)
        }
        
        return updated
    }

    suspend fun executeSkill(
        skillName: String,
        userInput: String,
        pdfText: String,
        context: Context
    ): SkillOutcome = withContext(Dispatchers.IO) {
        val skill = ResearchSkillRegistry.getSkillByName(skillName)
        if (skill == null) return@withContext SkillOutcome("Skill not found.", success = false)

        return@withContext when (skill.id) {
            // --- 🔬 Research (1-10) ---
            2 -> executePicoExtractor(userInput, pdfText)
            5 -> executeHypothesisGenerator(userInput, pdfText)

            // --- 📚 Search (11-20) ---
            12 -> executePubMedSearch(userInput)
            18 -> executeSimilarArticleFinder(userInput)

            // --- ✅ Validation (21-30) ---
            21 -> executePmidValidator(userInput)
            22 -> executeDoiValidator(userInput)
            23 -> executeCitationValidator(userInput)
            24 -> executeVancouverFormatter(userInput)

            // --- 🧬 Data (31-40) ---
            31 -> executeMedicalEntityExtractor(userInput, pdfText)
            34 -> executeNumericalDataExtractor(userInput, pdfText)

            // --- 🧠 Generation (41-50) ---
            46 -> executeThesisWriter(userInput, pdfText)
            48 -> executeAbstractGenerator(userInput, pdfText)
            197 -> executePosterGenerator(userInput, pdfText)

            // --- 🎓 Education (71-100) ---
            51 -> executeCaseStudyGenerator(userInput)
            53 -> executeMnemonicCreator(userInput)
            75 -> executeAnkiFlashcarder(userInput, pdfText)
            85 -> executeAbbreviationDecoder(userInput)

            // --- 🩺 Clinical (101-150) ---
            69 -> executePediatricDoseCalculator(userInput)
            121 -> executeAbgSolver(userInput)
            134 -> executeCvdRiskScorer(userInput)
            171 -> executeEthicsValidator(userInput, pdfText)
            172 -> executeSampleSizeCalculator(userInput)
            
            // --- 💻 Coding (177-185) ---
            179 -> executeDiffViewer(userInput)
            180 -> executeCompilerInterpreter(userInput)
            181 -> executeAutonomousCodingAgent(userInput)
            
            else -> executeLlmAidedSkill(skill, userInput, pdfText)
        }
    }

    private suspend fun executeDiffViewer(input: String): SkillOutcome {
        val prompt = """
            [CODING_SKILL: Diff Change Viewer]
            Analyze the requested change and output a valid 'diff' block.
            Request: $input
            
            Format:
            ```diff
            - old line
            + new line
            ```
        """.trimIndent()
        return SkillOutcome(prompt, "Generating diff...")
    }

    private suspend fun executeCompilerInterpreter(input: String): SkillOutcome {
        val prompt = """
            [CODING_SKILL: Compiler Error Interpreter]
            Explain the following stack trace or compiler error in simple medical-developer terms.
            Suggest 3 possible fixes.
            Error: $input
        """.trimIndent()
        return SkillOutcome(prompt, "Interpreting error...")
    }

    private suspend fun executeAutonomousCodingAgent(input: String): SkillOutcome {
        val prompt = """
            [CODING_SKILL: Autonomous Coding Agent]
            You are now an autonomous agent. 
            Goal: $input
            
            Follow this loop:
            1. PLAN: Draft a multi-step engineering plan.
            2. INSPECT: Identify which files need to be read or searched.
            3. EXECUTE: Generate the necessary code changes or diffs.
            4. AUDIT: Review the changes for side-effects.
            
            Start by outputting your PLAN.
        """.trimIndent()
        return SkillOutcome(prompt, "Agent Thinking...")
    }

    private suspend fun executeEthicsValidator(input: String, pdfText: String): SkillOutcome {
        val hasIrb = pdfText.contains("IRB", ignoreCase = true) || pdfText.contains("Ethics Committee", ignoreCase = true)
        val hasConsent = pdfText.contains("Informed Consent", ignoreCase = true)
        
        val sb = StringBuilder("Formal Protocol Check:\n")
        sb.append(if (hasIrb) "✅ IRB Approval detected.\n" else "⚠️ WARNING: No IRB/Ethics approval number found. This is mandatory for Methodology.\n")
        sb.append(if (hasConsent) "✅ Informed Consent section found.\n" else "⚠️ WARNING: Informed Consent process not defined.\n")
        
        return SkillOutcome(sb.toString(), "Validating Ethical Clearance")
    }

    private suspend fun executeSampleSizeCalculator(input: String): SkillOutcome {
        // Deterministic power calculation prompt
        val prompt = """
            [PROTOCOL GATE: Sample Size Calculation]
            Based on the user's research question: $input
            
            Perform a formal sample size calculation.
            Determine:
            1. Statistical Power (typically 80% or 90%).
            2. Alpha level (typically 0.05).
            3. Effect Size (based on literature or pilot study).
            4. Final 'n' required per group.
            
            Justify the formula used (e.g., Cochrane's, Yamane's, or specific RCT formula).
        """.trimIndent()
        return SkillOutcome(prompt, "Calculating required Sample Size (n)")
    }

    private suspend fun executeHypothesisGenerator(input: String, pdfText: String): SkillOutcome {
        val prompt = """
            Based on this research goal: $input
            And this context: ${pdfText.take(2000)}
            
            Generate:
            1. A Null Hypothesis (H0)
            2. An Alternative Hypothesis (H1)
            3. A brief justification for the direction of the hypothesis.
        """.trimIndent()
        return SkillOutcome(prompt, "Formulating hypotheses...")
    }

    private suspend fun executeNumericalDataExtractor(input: String, pdfText: String): SkillOutcome {
        val prompt = """
            Find and extract all key statistical numbers from the text.
            Include: Odds Ratios (OR), Relative Risk (RR), p-values, Confidence Intervals (CI), and Sample Sizes (n).
            Text: ${pdfText.take(5000)}
            
            Format as a list: [Study]: [Metric] = [Value] ([CI])
        """.trimIndent()
        return SkillOutcome(prompt, "Extracting statistical data...")
    }

    private suspend fun executeCaseStudyGenerator(input: String): SkillOutcome {
        val prompt = """
            Create a complex clinical case study for a student focusing on: $input
            Include:
            - Chief Complaint
            - History of Present Illness
            - Physical Exam Findings
            - Laboratory/Imaging Data
            - 3 Critical Thinking Questions
        """.trimIndent()
        return SkillOutcome(prompt, "Designing patient scenario...")
    }

    private suspend fun executeMnemonicCreator(input: String): SkillOutcome {
        val prompt = """
            Generate an easy-to-remember medical mnemonic for the following concept: $input
            Explain what each letter represents and why it's clinically relevant.
        """.trimIndent()
        return SkillOutcome(prompt, "Creating memory aid...")
    }

    private suspend fun executeAnkiFlashcarder(input: String, pdfText: String): SkillOutcome {
        val prompt = """
            Convert the following medical text into Anki-style flashcards (Front/Back format).
            Focus on high-yield facts, dosages, and diagnostic criteria.
            Text: ${if (pdfText.length > 500) pdfText.take(3000) else input}
        """.trimIndent()
        return SkillOutcome(prompt, "Generating flashcards...")
    }

    private suspend fun executeAbbreviationDecoder(text: String): SkillOutcome {
        val prompt = """
            Identify and decode all medical abbreviations in this text. 
            Provide the full form and a 1-sentence definition of each.
            Text: $text
        """.trimIndent()
        return SkillOutcome(prompt, "Decoding shorthand...")
    }

    private suspend fun executeAbgSolver(input: String): SkillOutcome {
        // Deterministic regex check for values
        val ph = Regex("""pH\s*[:=]?\s*(\d+\.\d+)""").find(input)?.groupValues?.get(1)?.toDoubleOrNull()
        val pco2 = Regex("""pCO2\s*[:=]?\s*(\d+)""").find(input)?.groupValues?.get(1)?.toDoubleOrNull()
        val hco3 = Regex("""HCO3\s*[:=]?\s*(\d+)""").find(input)?.groupValues?.get(1)?.toDoubleOrNull()

        if (ph == null || pco2 == null || hco3 == null) {
            return SkillOutcome("Missing values. Please provide pH, pCO2, and HCO3 (e.g., pH 7.32, pCO2 50, HCO3 26).", success = false)
        }

        val analysisPrompt = """
            Analyze these ABG values: pH $ph, pCO2 $pco2, HCO3 $hco3.
            Determine:
            1. Primary acid-base disturbance.
            2. Compensatory response (Full/Partial/None).
            3. Possible clinical causes.
        """.trimIndent()
        return SkillOutcome(analysisPrompt, "Analyzing acid-base status")
    }

    private suspend fun executeCvdRiskScorer(input: String): SkillOutcome {
        val prompt = """
            Calculate the 10-year Cardiovascular Risk (ASCVD) for this patient profile:
            Details: $input
            
            Use the standard ACC/AHA guidelines logic. 
            Provide the risk percentage and recommended intervention (Statin intensity, lifestyle).
        """.trimIndent()
        return SkillOutcome(prompt, "Calculating ASCVD risk...")
    }

    private suspend fun executePediatricDoseCalculator(input: String): SkillOutcome {
        // Simple logic for educational weighting/dosing
        val weight = Regex("""\b(\d+)\s*(kg|lb)\b""").find(input)?.groupValues?.get(1)?.toIntOrNull() ?: 0
        if (weight == 0) return SkillOutcome("Please specify the patient's weight (e.g., 20kg).", success = false)
        
        return SkillOutcome("Dosing logic initialized for $weight kg. Requesting standardized pediatric formulary data...", "Calculating weight-based dose")
    }

    private suspend fun executeDoiValidator(text: String): SkillOutcome {
        val dois = Regex("""10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+""").findAll(text).map { it.value }.toList().distinct()
        if (dois.isEmpty()) return SkillOutcome("No DOIs found to validate.")
        return SkillOutcome("Identified DOIs: ${dois.joinToString(", ")}. CrossRef validation pending API integration.", "Detected ${dois.size} DOIs")
    }

    private suspend fun executeThesisWriter(input: String, pdfText: String): SkillOutcome {
        val prompt = """
            [THESIS WRITER PROTOCOL]
            Task: Draft a formal academic thesis chapter/section based on the user's request and document context.
            User Request: $input
            Document Context: ${pdfText.take(5000)}
            
            Enforce these academic standards:
            1. Clear section heading (**Title**).
            2. Structured breakdown (Background / Methodology / Results / Discussion).
            3. Include at least one structured Markdown table (with proper headers | Column 1 | Column 2 |).
            4. Cite relevant medical parameters, variables, and clinical endpoints.
        """.trimIndent()
        return SkillOutcome(prompt, "Drafting thesis chapter...")
    }

    private suspend fun executePosterGenerator(input: String, pdfText: String): SkillOutcome {
        val prompt = """
            [ACADEMIC POSTER GENERATOR PROTOCOL]
            Task: Generate a complete academic conference poster layout from the provided abstract or text.
            User Request: $input
            Content: ${if (pdfText.isNotBlank()) pdfText.take(5000) else input}
            
            Structure into these standardized poster sections:
            - **Poster Title & Authors**
            - **Background & Clinical Rationale**
            - **Aims & Hypotheses**
            - **Methods & Study Design**
            - **Key Results & Statistical Findings** (include a formatted summary table)
            - **Clinical Takeaway & Conclusions**
            - **References / PMIDs**
        """.trimIndent()
        return SkillOutcome(prompt, "Generating academic poster layout...")
    }

    private suspend fun executeAbstractGenerator(input: String, pdfText: String): SkillOutcome {
        val prompt = """
            Generate a structured medical abstract (Background, Methods, Results, Conclusion) from the provided text.
            User Request: $input
            PDF Data: ${pdfText.take(4000)}
            
            Format clearly with headings.
        """.trimIndent()
        return SkillOutcome(prompt, "Generating structured abstract...")
    }

    private suspend fun executePicoExtractor(input: String, pdfText: String): SkillOutcome {
        val prompt = """
            Extract PICO/PECO elements from the following research request or abstract:
            Request: $input
            PDF Data: ${pdfText.take(2000)}
            
            Return ONLY a valid JSON object:
            {"P":"...", "I":"...", "C":"...", "O":"..."}
        """.trimIndent()
        return SkillOutcome(prompt, "Extracting PICO elements...")
    }

    private suspend fun executeMedicalEntityExtractor(input: String, pdfText: String): SkillOutcome {
        val prompt = """
            Identify all medical entities (diseases, drugs, procedures, anatomy) in the text below.
            Text: $input
            PDF Data: ${pdfText.take(1000)}
            
            Return a comma-separated list of entities.
        """.trimIndent()
        return SkillOutcome(prompt, "Identifying medical entities...")
    }

    private suspend fun executePubMedSearch(query: String): SkillOutcome {
        val pmids = ThesisArtBridge.searchSimilarArticles(query)
        if (pmids.isEmpty()) return SkillOutcome("No articles found on PubMed for '$query'.")
        val sb = StringBuilder("Found ${pmids.size} articles on PubMed:\n")
        pmids.forEach { pmid ->
            val abs = ThesisArtBridge.fetchAbstract(pmid)
            sb.append("- PMID $pmid: ${abs?.take(300)}...\n")
        }
        return SkillOutcome(sb.toString(), "Retrieved ${pmids.size} PubMed results")
    }

    private suspend fun executeSimilarArticleFinder(pmid: String): SkillOutcome {
        val cleanPmid = pmid.filter { it.isDigit() }
        if (cleanPmid.isBlank()) return SkillOutcome("Invalid PMID provided.", success = false)
        val pmids = ThesisArtBridge.fetchSimilarPmids(cleanPmid)
        if (pmids.isEmpty()) return SkillOutcome("No similar articles found for PMID $cleanPmid.")
        val sb = StringBuilder("Similar articles for PMID $cleanPmid:\n")
        pmids.take(5).forEach { p ->
            val abs = ThesisArtBridge.fetchAbstract(p)
            sb.append("- PMID $p: ${abs?.take(300)}...\n")
        }
        return SkillOutcome(sb.toString(), "Found ${pmids.size} similar articles")
    }

    private suspend fun executePmidValidator(text: String): SkillOutcome {
        val pmids = Regex("""\d{7,10}""").findAll(text).map { it.value }.toList().distinct()
        if (pmids.isEmpty()) return SkillOutcome("No PMIDs found to validate.")
        val sb = StringBuilder("PMID Validation Results:\n")
        pmids.forEach { pmid ->
            val match = PubMedCitationValidator.fetchByPmid(pmid)
            if (match != null) {
                sb.append("✅ PMID $pmid: ${match.articleTitle}\n")
            } else {
                sb.append("❌ PMID $pmid: Not found or invalid\n")
            }
        }
        return SkillOutcome(sb.toString(), "Validated ${pmids.size} PMIDs")
    }

    private suspend fun executeCitationValidator(text: String): SkillOutcome {
        val entries = PubMedCitationValidator.extractCitationEntries(text)
        if (entries.isEmpty()) return SkillOutcome("No citations detected in text.")
        val results = PubMedCitationValidator.validate(entries) { }
        val sb = StringBuilder("Citation Validation Results:\n")
        results.forEach { r ->
            val status = if (r.found) "✅ FOUND (PMID ${r.pmid})" else "❌ NOT FOUND"
            sb.append("- ${r.originalText.take(100)}... -> $status\n")
        }
        return SkillOutcome(sb.toString(), "Validated ${results.size} citations")
    }

    private suspend fun executeVancouverFormatter(text: String): SkillOutcome {
        val entries = PubMedCitationValidator.extractCitationEntries(text)
        val results = PubMedCitationValidator.validate(entries) { }
        val sb = StringBuilder("Validated Vancouver References:\n")
        results.filter { it.found }.forEach { r ->
            sb.append("${r.canonicalReference}\n")
        }
        return SkillOutcome(sb.toString(), "Formatted ${results.count { it.found }} references")
    }

    private suspend fun executeLlmAidedSkill(skill: ResearchSkill, input: String, pdfText: String): SkillOutcome {
        // For Skill 50 (Auditor), we need a specific prompt.
        if (skill.id == 50) {
            val auditPrompt = """
                [FINAL RESEARCH AUDITOR]
                Verify the following research claims and citations against medical standards:
                Reply: $input
                
                Check for:
                1. Hallucinated PMIDs (citations must be real).
                2. Methodological inconsistencies.
                3. Numerical errors.
                
                If everything is correct, reply 'SUCCESS'. 
                Otherwise, provide a brief warning note.
            """.trimIndent()
            return SkillOutcome(auditPrompt, "Auditing response...")
        }

        // For other skills, we return a prompt that tells the final AI call 
        // to perform this specific analysis as part of its reply.
        val context = """
            [SKILL_INSTRUCTION: ${skill.name}]
            Task: ${skill.description}
            User Input: $input
            Available PDF Context (first 2000 chars): ${pdfText.take(2000)}
            
            Perform this skill analysis now.
        """.trimIndent()
        return SkillOutcome(context, "Running ${skill.name}...")
    }
}
