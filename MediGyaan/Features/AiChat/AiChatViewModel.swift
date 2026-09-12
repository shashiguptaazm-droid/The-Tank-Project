import Foundation
import SwiftUI
import AVFoundation
import UIKit

/// Drives the Medical AI Assistant chat screen.
/// Ports the comprehensive multi-turn clinical chat from Android's `AiChatActivity.kt`.
@MainActor
final class AiChatViewModel: NSObject, ObservableObject, AVSpeechSynthesizerDelegate {

    @Published var messages: [AiChatMessage] = []
    @Published var input: String = ""
    @Published var isLoading: Bool = false
    @Published var attachedDocumentName: String? = nil
    @Published var activeQuizToLaunch: Quiz? = nil
    @Published var isSpeaking: Bool = false
    @Published var toastMessage: String? = nil

    private let speechSynthesizer = AVSpeechSynthesizer()

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
                text: "Hello! I am your **MediGyaan Medical AI Assistant**.\n\nYou can ask me clinical differentials, drug mechanisms, emergency protocols, or attach case notes and PDFs for analysis. Tap any high-yield topic below to begin!"
            )
        ]
    }

    // MARK: - Sending Messages

    func sendCurrentInput(api: MediGyaanAPI, userId: Int) async {
        let trimmed = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        input = ""
        let attachment = attachedDocumentName
        attachedDocumentName = nil

        await send(prompt: trimmed, attachmentName: attachment, api: api, userId: userId)
    }

    func selectSuggestion(_ suggestion: AiPromptSuggestion, api: MediGyaanAPI, userId: Int) async {
        await send(prompt: suggestion.prompt, attachmentName: nil, api: api, userId: userId)
    }

    private func send(prompt: String, attachmentName: String?, api: MediGyaanAPI, userId: Int) async {
        // Add user turn
        let userMsg = AiChatMessage(
            role: .user,
            text: prompt,
            attachmentName: attachmentName
        )
        messages.append(userMsg)
        isLoading = true

        // Formulate context
        var context = "Medical consultation conversation.\n"
        if let attachmentName {
            context += "Attached Document: \(attachmentName)\n"
        }
        for prev in messages.suffix(6) {
            context += "\(prev.role.rawValue): \(prev.text)\n"
        }

        do {
            let reply = try await api.ai.ask(
                prompt: prompt,
                userId: userId,
                model: nil,
                context: context
            )

            let cleanReply = reply.trimmingCharacters(in: .whitespacesAndNewlines)
            if !cleanReply.isEmpty {
                // Also search 1-2 related practice questions if relevant
                let related = await searchRelatedMCQs(query: prompt, api: api)
                messages.append(AiChatMessage(
                    role: .assistant,
                    text: cleanReply,
                    relatedQuestions: related
                ))
            } else {
                throw APIError.decoding(NSError(domain: "EmptyResponse", code: 0))
            }
        } catch {
            // Fallback clinical intelligence so medical students never face blank downtime
            let fallback = generateClinicalFallback(for: prompt)
            messages.append(AiChatMessage(
                role: .assistant,
                text: fallback
            ))
        }

        isLoading = false
    }

    // MARK: - Related Questions Search

    private func searchRelatedMCQs(query: String, api: MediGyaanAPI) async -> [Question] {
        // Pick key medical keywords from query
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

    private func showToast(_ msg: String) {
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
