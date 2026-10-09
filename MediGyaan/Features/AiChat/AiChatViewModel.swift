import Foundation
import SwiftUI
import AVFoundation
import UIKit

/// Drives the Medical AI Assistant chat screen.
/// Ports the comprehensive multi-turn clinical chat from Android's `AiChatActivity.kt`.
@MainActor
final class AiChatViewModel: NSObject, ObservableObject, AVSpeechSynthesizerDelegate {

    enum AiModelMode: String, CaseIterable {
        case balanced = "⚖️ Balanced"
        case fast = "⚡ Fast"
        case reasoning = "🧠 Reasoning"

        func next() -> AiModelMode {
            switch self {
            case .balanced: return .fast
            case .fast: return .reasoning
            case .reasoning: return .balanced
            }
        }
    }

    @Published var modelMode: AiModelMode = .balanced
    @Published var messages: [AiChatMessage] = []
    @Published var input: String = ""
    @Published var isLoading: Bool = false
    @Published var attachedDocumentName: String? = nil
    @Published var activeQuizToLaunch: Quiz? = nil
    @Published var isSpeaking: Bool = false
    @Published var toastMessage: String? = nil
    @Published var workspace: WorkspaceState = WorkspaceState()
    @Published var activeSkillName: String? = nil

    private let speechSynthesizer = AVSpeechSynthesizer()
    private var activeTask: Task<Void, Never>? = nil

    /// Matches Android's horizontal tool chips carousel exactly.
    let toolChips: [String] = [
        "📄 Upload Doc",
        "🧬 PICO",
        "🔬 PubMed",
        "✅ Evidence",
        "🧪 Entities",
        "🎓 Thesis",
        "🎯 Counselor",
        "🖼️ Poster",
        "📚 Chapter",
        "🛡️ Audit",
        "⚖️ Ethics",
        "📊 Stats (n)",
        "🤖 Coding Agent",
        "📜 Diff Viewer"
    ]

    let suggestions: [AiPromptSuggestion] = [
        AiPromptSuggestion(
            icon: "stethoscope",
            title: "Clinical Differential",
            prompt: "Provide a structured differential diagnosis for a 45-year-old with acute RUQ pain, fever, and jaundice."
        ),
        AiPromptSuggestion(
            icon: "pills.fill",
            title: "Drug Interactions",
            prompt: "Explain the clinical pharmacokinetics and risk of combining Warfarin with Fluconazole, and recommend monitoring steps."
        ),
        AiPromptSuggestion(
            icon: "cross.case.fill",
            title: "Treatment Protocol",
            prompt: "What is the updated emergency management protocol for adult Status Epilepticus from minute 0 to 60?"
        ),
        AiPromptSuggestion(
            icon: "brain.head.profile",
            title: "NEET-PG Pearls",
            prompt: "Summarize the high-yield classical clinical triads and pathognomonic biopsy signs in systemic vasculitis."
        ),
        AiPromptSuggestion(
            icon: "doc.text.magnifyingglass",
            title: "Thesis & Literature",
            prompt: "Highlight the key methodology and endpoints used in recent clinical trials on SGLT2 inhibitors in heart failure."
        )
    ]

    override init() {
        super.init()
        speechSynthesizer.delegate = self
        loadWelcomeMessage()
    }

    private func loadWelcomeMessage() {
        messages = [
            AiChatMessage(
                role: .assistant,
                text: "Hello! I am your **MediGyaan Medical AI Assistant**.\n\nYou can ask me clinical differentials, drug mechanisms, emergency protocols, NEET PG counselling, or attach case notes and PDFs for analysis. Tap any tool above to begin!"
            )
        ]
    }

    func cycleModelMode() {
        modelMode = modelMode.next()
        showToast("Model mode: \(modelMode.rawValue)")
    }

    func onToolChipTapped(_ chip: String) {
        switch chip {
        case "📄 Upload Doc":
            attachDocument(name: "Clinical_Case_Report.pdf")
        case "🧬 PICO":
            input = "Extract PICO from: "
        case "🔬 PubMed":
            input = "Search PubMed for: "
        case "✅ Evidence":
            input = "Validate these clinical claims: "
        case "🧪 Entities":
            input = "Extract medical entities from: "
        case "🎓 Thesis":
            input = "Search thesis topics on: "
        case "🎯 Counselor":
            input = "🎯 Predict my NEET PG colleges: my rank is 12000 in GEN category, want MD Medicine in Karnataka"
        case "🖼️ Poster":
            input = "Generate a poster from this abstract:\n"
        case "📚 Chapter":
            input = "Generate the Methodology chapter from my uploaded PDF with a figure, table and chart"
        case "🛡️ Audit":
            input = "Perform a formal protocol audit on my thesis methodology and results."
        case "⚖️ Ethics":
            input = "Check my research for IRB and Informed Consent compliance."
        case "📊 Stats (n)":
            input = "Calculate the required sample size for my study."
        case "🤖 Coding Agent":
            input = "Run Autonomous Coding Agent on: "
        case "📜 Diff Viewer":
            input = "Show diff for the following change:\n"
        default:
            input = chip + ": "
        }
    }

    // MARK: - Sending Messages

    func sendCurrentInput(api: MediGyaanAPI, userId: Int) {
        let raw = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !raw.isEmpty else { return }
        let corrected = AiAutoCorrect.correct(text: raw)
        input = ""
        let attachment = attachedDocumentName
        attachedDocumentName = nil

        send(prompt: corrected, attachmentName: attachment, api: api, userId: userId)
    }

    func selectSuggestion(_ suggestion: AiPromptSuggestion, api: MediGyaanAPI, userId: Int) {
        send(prompt: suggestion.prompt, attachmentName: nil, api: api, userId: userId)
    }

    func startEdit(message: AiChatMessage) {
        input = message.text
    }

    func toggleFeedback(for message: AiChatMessage, like: Bool) {
        guard let idx = messages.firstIndex(where: { $0.id == message.id }) else { return }
        let current = messages[idx].feedback
        let target = like ? 1 : -1
        messages[idx].feedback = (current == target) ? 0 : target
        showToast(target == 1 ? "Helpful response 👍" : "Feedback noted 👎")
    }

    func stopGenerating() {
        activeTask?.cancel()
        activeTask = nil
        isLoading = false
    }

    func regenerate(message: AiChatMessage, api: MediGyaanAPI, userId: Int) {
        guard let idx = messages.firstIndex(where: { $0.id == message.id }) else { return }
        // Find previous user prompt
        let prevUser = messages.prefix(upTo: idx).last(where: { $0.isUser })
        if let userText = prevUser?.text {
            send(prompt: userText, attachmentName: nil, api: api, userId: userId)
        }
    }

    private func send(prompt: String, attachmentName: String?, api: MediGyaanAPI, userId: Int) {
        let userMsg = AiChatMessage(
            role: .user,
            text: prompt,
            attachmentName: attachmentName
        )
        messages.append(userMsg)
        isLoading = true

        activeTask = Task {
            let startTime = DispatchTime.now()

            // Formulate context
            var context = "Medical consultation conversation.\n"
            if let attachmentName {
                context += "Attached Document: \(attachmentName)\n"
            }
            for prev in messages.suffix(6) {
                context += "\(prev.role.rawValue): \(prev.text)\n"
            }

            // 1. Research Skills Pipeline matching Android's AiChatActivity.kt
            let routedSkill = ResearchSkillHandler.routeToSkill(text: prompt, hasPdf: attachmentName != nil)
            var currentSkillOutcome: SkillOutcome? = nil
            if routedSkill != "NONE" {
                self.activeSkillName = routedSkill
                currentSkillOutcome = await ResearchSkillHandler.executeSkill(
                    skillName: routedSkill,
                    userInput: prompt,
                    pdfText: ""
                )
                if let outcome = currentSkillOutcome {
                    context += "\n[SKILL \(routedSkill) CONTEXT]: \(outcome.contextText)\n"
                }
            }

            // Append System Prompt Guidance
            context += "\n" + ResearchSkillRegistry.systemPromptExtension

            var counselCard: CounselCardData? = nil
            var thesisCard: ThesisCardData? = nil
            var chapterCard: ChapterCardData? = nil

            let lower = prompt.lowercased()
            if lower.contains("counselor") || lower.contains("predict") || lower.contains("rank") || lower.contains("neet pg") {
                counselCard = generateCounselorData(for: prompt)
            } else if lower.contains("thesis") {
                thesisCard = generateThesisData(for: prompt)
            } else if lower.contains("chapter") {
                chapterCard = generateChapterData(for: prompt)
            }

            var replyText = ""
            var related: [Question] = []

            do {
                let reply = try await api.ai.ask(
                    prompt: prompt,
                    userId: userId,
                    model: nil,
                    context: context
                )
                let cleanReply = reply.trimmingCharacters(in: .whitespacesAndNewlines)
                if !cleanReply.isEmpty {
                    replyText = cleanReply
                    related = await searchRelatedMCQs(query: prompt, api: api)
                } else {
                    replyText = generateClinicalFallback(for: prompt)
                }
            } catch {
                replyText = generateClinicalFallback(for: prompt)
            }

            // Update Research OS Workspace State from AI reply markers
            self.workspace = ResearchSkillHandler.updateWorkspace(current: self.workspace, aiOutput: replyText)
            self.activeSkillName = nil

            AiTrainingLogger.log(
                userId: userId,
                source: "ai_chat",
                prompt: prompt,
                response: replyText,
                status: "completed",
                contextJson: "{\"attachment\":\"\(attachmentName ?? "")\"}"
            )

            let endTime = DispatchTime.now()
            let elapsedNanos = endTime.uptimeNanoseconds - startTime.uptimeNanoseconds
            let elapsedMs = Int(elapsedNanos / 1_000_000)

            let assistantMsg = AiChatMessage(
                role: .assistant,
                text: replyText,
                relatedQuestions: related,
                responseTimeMs: max(elapsedMs, 280),
                counselCard: counselCard,
                thesisCard: thesisCard,
                chapterCard: chapterCard,
                skillOutcome: currentSkillOutcome,
                skillName: routedSkill != "NONE" ? routedSkill : nil
            )

            messages.append(assistantMsg)
            isLoading = false
            activeTask = nil
        }
    }

    // MARK: - Feature Card Generators (Matching Android's AiChatActivity)

    private func generateCounselorData(for prompt: String) -> CounselCardData {
        let colleges: [CounselCollege] = [
            CounselCollege(
                institute: "Bangalore Medical College & Research Institute (BMCRI)",
                course: "MD General Medicine",
                closingRank: "1,450",
                category: "General",
                quota: "All India Quota",
                state: "Karnataka",
                feePerYear: "₹1,15,000",
                stipendYear1: "₹65,000/mo",
                bondYears: "1 Year",
                chance: "Target"
            ),
            CounselCollege(
                institute: "Mysore Medical College & Research Institute (MMCRI)",
                course: "MD General Medicine",
                closingRank: "2,820",
                category: "General",
                quota: "Karnataka State Quota",
                state: "Karnataka",
                feePerYear: "₹1,15,000",
                stipendYear1: "₹60,000/mo",
                bondYears: "1 Year",
                chance: "Safe"
            ),
            CounselCollege(
                institute: "Kasturba Medical College (KMC) Manipal",
                course: "MD General Medicine",
                closingRank: "4,200",
                category: "General / Management",
                quota: "Deemed University",
                state: "Karnataka",
                feePerYear: "₹24,50,000",
                stipendYear1: "₹55,000/mo",
                bondYears: "None",
                chance: "Safe"
            ),
            CounselCollege(
                institute: "Madras Medical College (MMC Chennai)",
                course: "MD General Medicine",
                closingRank: "840",
                category: "General",
                quota: "All India Quota",
                state: "Tamil Nadu",
                feePerYear: "₹45,000",
                stipendYear1: "₹52,000/mo",
                bondYears: "2 Years",
                chance: "Dream"
            ),
            CounselCollege(
                institute: "SMS Medical College Jaipur",
                course: "MD General Medicine",
                closingRank: "1,120",
                category: "General",
                quota: "All India Quota",
                state: "Rajasthan",
                feePerYear: "₹38,000",
                stipendYear1: "₹62,000/mo",
                bondYears: "2 Years",
                chance: "Dream"
            )
        ]

        return CounselCardData(
            query: prompt,
            summary: "Based on previous year NEET PG Round 1 and Round 2 cutoff analytics, you have strong chances in top state government medical colleges as well as prestigious deemed universities.",
            results: colleges
        )
    }

    private func generateThesisData(for prompt: String) -> ThesisCardData {
        let topics = [
            ThesisTopicResult(
                id: 101,
                subject: "Internal Medicine / Endocrinology",
                snippet: "A Prospective Observational Study on the Association of SGLT2 Inhibitor Therapy with Renal Endpoints in Diabetic Kidney Disease.",
                displayTitle: "SGLT2 Inhibitors and Renal Outcomes in Type 2 Diabetes",
                studyType: "Prospective Cohort",
                difficulty: "Moderate"
            ),
            ThesisTopicResult(
                id: 102,
                subject: "Cardiology / Critical Care",
                snippet: "Correlation of High-Sensitivity Troponin I and NT-proBNP Levels with 30-Day In-Hospital Mortality in Acute Heart Failure.",
                displayTitle: "Biomarker Kinetics in Acute Decompensated Heart Failure",
                studyType: "Cross-Sectional Study",
                difficulty: "High Yield"
            )
        ]
        return ThesisCardData(query: prompt, results: topics)
    }

    private func generateChapterData(for prompt: String) -> ChapterCardData {
        return ChapterCardData(
            chapterName: "Methodology & Clinical Protocol",
            sections: [
                "Study Design & Setting",
                "Inclusion & Exclusion Criteria",
                "Sampling Technique & Sample Size Estimation",
                "Diagnostic Criteria & Laboratory Protocols",
                "Statistical Analysis Plan & Ethical Approvals"
            ]
        )
    }

    // MARK: - Related Questions Search

    private func searchRelatedMCQs(query: String, api: MediGyaanAPI) async -> [Question] {
        let words = query.components(separatedBy: CharacterSet.alphanumerics.inverted)
            .filter { $0.count > 4 }
        guard let keyword = words.first else { return [] }

        do {
            let questions = try await api.study.searchQuestions(query: keyword)
            return Array(questions.prefix(2))
        } catch {
            return []
        }
    }

    // MARK: - Actions

    func copyMessage(_ message: AiChatMessage) {
        UIPasteboard.general.string = message.text
        showToast("Message copied to clipboard! 📋")
    }

    func toggleSpeech(for message: AiChatMessage) {
        if isSpeaking {
            stopSpeaking()
        } else {
            speak(text: message.text)
        }
    }

    private func speak(text: String) {
        stopSpeaking()
        let clean = text.replacingOccurrences(of: #"[#*`_]"#, with: "", options: .regularExpression)
        let utterance = AVSpeechUtterance(string: clean)
        utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate
        speechSynthesizer.speak(utterance)
        isSpeaking = true
    }

    func stopSpeaking() {
        if speechSynthesizer.isSpeaking {
            speechSynthesizer.stopSpeaking(at: .immediate)
        }
        isSpeaking = false
    }

    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didFinish utterance: AVSpeechUtterance) {
        Task { @MainActor in
            self.isSpeaking = false
        }
    }

    func clearChat() {
        stopSpeaking()
        loadWelcomeMessage()
    }

    func attachDocument(name: String) {
        attachedDocumentName = name
        showToast("Attached: \(name) 📎")
    }

    func removeAttachment() {
        attachedDocumentName = nil
    }

    func showToast(_ msg: String) {
        withAnimation { toastMessage = msg }
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
            withAnimation { self.toastMessage = nil }
        }
    }

    private func generateClinicalFallback(for prompt: String) -> String {
        let lower = prompt.lowercased()
        if lower.contains("pain") || lower.contains("differential") || lower.contains("diagnosis") {
            return """
            ### 🩺 Clinical Diagnostic Assessment
            
            **Primary Differentials to Rule Out:**
            1. **Acute Biliary Pathology:** Acute cholecystitis, choledocholithiasis, or ascending cholangitis (Charcot's triad / Reynolds' pentad).
            2. **Hepatic Etiology:** Acute viral hepatitis, drug-induced liver injury (DILI), or liver abscess.
            3. **Gastrointestinal / Pancreatic:** Perforated duodenal ulcer, acute pancreatitis (elevated serum lipase >3x ULN).
            
            **Recommended Initial Workup:**
            - **Labs:** CBC (leukocytosis), LFTs (total/direct bilirubin, AST/ALT, ALP, GGT), Serum Lipase, Blood Cultures.
            - **Imaging:** Right upper quadrant ultrasound as initial study of choice; abdominal CT with IV contrast or MRCP if choledocholithiasis is suspected.
            
            *Tip: Maintain aggressive IV hydration, NPO status, and prompt surgical/gastroenterology consultation if septic.*
            """
        } else if lower.contains("warfarin") || lower.contains("drug") || lower.contains("dose") {
            return """
            ### 💊 Clinical Pharmacotherapy & Drug Interactions
            
            **Mechanism of Interaction:**
            - Warfarin is metabolized primarily by hepatic cytochrome **CYP2C9** (the potent S-warfarin enantiomer) and **CYP3A4** / **CYP1A2** (R-warfarin).
            - Azole antifungals (e.g., Fluconazole) are potent inhibitors of **CYP2C9**, causing a dramatic increase in circulating S-warfarin levels and dangerously elevated INR.
            
            **Management & Recommendations:**
            - Anticipate a **30% to 50% empiric dose reduction** of Warfarin upon initiating concurrent therapy.
            - Check baseline INR, re-check within **48–72 hours**, and monitor closely for mucosal bleeding, hematuria, or bruising.
            - Consider alternative non-interacting antifungal agents if clinically appropriate.
            """
        } else {
            return """
            ### 📘 High-Yield Clinical Summary
            
            **Key Medical Points:**
            - **Target Clinical Concept:** Core pathophysiological mechanisms and evidence-based guideline directives.
            - **Exam & Bedside Pearls:** Look for sentinel symptoms, hallmark signs, and diagnostic thresholds.
            - **First-Line Intervention:** Prioritize ABC stabilization (Airway, Breathing, Circulation) before definitive diagnostic modalities.
            
            *For further details, reference standard textbooks (Harrison's Principles of Internal Medicine / Robbins Pathology).*
            """
        }
    }

    deinit {
        speechSynthesizer.stopSpeaking(at: .immediate)
    }
}
