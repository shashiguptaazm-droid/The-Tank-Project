import SwiftUI

/// An interactive medical AI assistant sheet for an MCQ.
/// Ports the "Ask AI" dialog from Android's `MCQActivity.kt`.
struct AskAiSheet: View {

    let question: Question
    @Environment(\.dismiss) private var dismiss
    @Environment(\.api) private var api

    @State private var userPrompt: String = ""
    @State private var messages: [AiMessage] = []
    @State private var isLoading: Bool = false

    struct AiMessage: Identifiable, Equatable {
        let id = UUID()
        let text: String
        let isUser: Bool
        let timestamp: Date = Date()
    }

    private let quickPrompts = [
        "💡 Explain key concepts",
        "❌ Why are other options wrong?",
        "🩺 High-yield clinical pearls",
        "🧬 Pathophysiology overview"
    ]

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Question Context Banner
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text("Question Context")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundStyle(Color(hex: 0x5C_6B_C0))
                        Spacer()
                        if !question.topic.isEmpty {
                            Text(question.topic)
                                .font(.system(size: 11, weight: .medium))
                                .foregroundStyle(.secondary)
                        }
                    }

                    Text(cleanQuestionText)
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(Color(hex: 0x1A_1C_2E))
                        .lineLimit(2)
                }
                .padding(12)
                .background(Color(hex: 0xF0_F4_FF))

                Divider()

                // Messages ScrollView
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 14) {
                            if messages.isEmpty {
                                initialWelcomeView
                            } else {
                                ForEach(messages) { message in
                                    messageBubble(message)
                                        .id(message.id)
                                }
                            }

                            if isLoading {
                                HStack(spacing: 8) {
                                    ProgressView()
                                        .scaleEffect(0.8)
                                    Text("MediGyaan AI is analyzing…")
                                        .font(.system(size: 13))
                                        .foregroundStyle(.secondary)
                                }
                                .padding(.horizontal)
                                .padding(.vertical, 8)
                            }
                        }
                        .padding(16)
                    }
                    .onChange(of: messages.count) { _ in
                        if let last = messages.last {
                            withAnimation {
                                proxy.scrollTo(last.id, anchor: .bottom)
                            }
                        }
                    }
                }

                Divider()

                // Preset Chips
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(quickPrompts, id: \.self) { prompt in
                            Button {
                                sendQuery(prompt)
                            } label: {
                                Text(prompt)
                                    .font(.system(size: 12, weight: .medium))
                                    .foregroundStyle(Color(hex: 0x39_49_AB))
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 6)
                                    .background(Color(hex: 0xE8_EA_F6))
                                    .clipShape(Capsule())
                            }
                            .disabled(isLoading)
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                }

                // Input Bar
                HStack(spacing: 10) {
                    TextField("Ask anything about this question…", text: $userPrompt)
                        .padding(10)
                        .background(Color(hex: 0xF5_F7_FA))
                        .clipShape(RoundedRectangle(cornerRadius: 12))

                    Button {
                        let query = userPrompt.trimmingCharacters(in: .whitespacesAndNewlines)
                        guard !query.isEmpty else { return }
                        userPrompt = ""
                        sendQuery(query)
                    } label: {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.system(size: 32))
                            .foregroundStyle(userPrompt.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isLoading ? Color.gray.opacity(0.4) : Color(hex: 0x5C_6B_C0))
                    }
                    .disabled(userPrompt.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isLoading)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
            }
            .navigationTitle("Ask MediGyaan AI")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
            }
            .onAppear {
                // If question has an explanation, load it as first AI insight
                if !question.explanation.isEmpty && messages.isEmpty {
                    messages.append(AiMessage(
                        text: "💡 **Clinical Explanation:**\n\(question.explanation)\n\nYou can ask follow-up questions or tap any topic below!",
                        isUser: false
                    ))
                }
            }
        }
    }

    private var initialWelcomeView: some View {
        VStack(spacing: 12) {
            Image(systemName: "brain.head.profile")
                .font(.system(size: 40))
                .foregroundStyle(Color(hex: 0x5C_6B_C0))
                .padding(.top, 20)

            Text("Medical AI Assistant")
                .font(.system(size: 16, weight: .bold))

            Text("Ask questions about this MCQ, dive into pathophysiology, or ask why specific choices are incorrect.")
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 24)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 20)
    }

    private func messageBubble(_ message: AiMessage) -> some View {
        HStack {
            if message.isUser { Spacer() }

            VStack(alignment: message.isUser ? .trailing : .leading, spacing: 4) {
                Text(LocalizedStringKey(message.text))
                    .font(.system(size: 14))
                    .foregroundStyle(message.isUser ? .white : Color(hex: 0x1A_1C_2E))
                    .padding(12)
                    .background(message.isUser ? Color(hex: 0x5C_6B_C0) : Color(hex: 0xF0_F4_FF))
                    .clipShape(RoundedRectangle(cornerRadius: 16))
            }
            .frame(maxWidth: 280, alignment: message.isUser ? .trailing : .leading)

            if !message.isUser { Spacer() }
        }
    }

    private func sendQuery(_ query: String) {
        messages.append(AiMessage(text: query, isUser: true))
        isLoading = true

        Task {
            // Build contextual prompt with question, options, and user query
            var promptContext = "MCQ: \(cleanQuestionText)\nOptions:\n"
            for (i, opt) in question.options.enumerated() {
                promptContext += "Option \(i + 1): \(opt)\n"
            }
            if !question.explanation.isEmpty {
                promptContext += "Existing explanation: \(question.explanation)\n"
            }
            promptContext += "User question: \(query)"

            // Call backend AI endpoint or generate clinical response
            do {
                let response = try await fetchAiResponse(prompt: promptContext, query: query)
                await MainActor.run {
                    messages.append(AiMessage(text: response, isUser: false))
                    isLoading = false
                }
            } catch {
                await MainActor.run {
                    // Fallback clinical pearls generated for client responsiveness
                    let fallback = generateLocalClinicalInsight(for: query)
                    messages.append(AiMessage(text: fallback, isUser: false))
                    isLoading = false
                }
            }
        }
    }

    private func fetchAiResponse(prompt: String, query: String) async throws -> String {
        // Try calling the live backend ask_ai2.php endpoint
        var request = URLRequest(url: APIConfig.baseURL.appendingPathComponent("ask_ai2.php"))
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        let bodyString = "question=\(prompt.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")&query=\(query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")"
        request.httpBody = bodyString.data(using: .utf8)
        request.timeoutInterval = 20

        let (data, response) = try await URLSession.shared.data(for: request)
        if let http = response as? HTTPURLResponse, http.statusCode == 200,
           let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let answer = json["answer"] as? String ?? json["response"] as? String, !answer.isEmpty {
            return answer
        }

        throw URLError(.badServerResponse)
    }

    private func generateLocalClinicalInsight(for query: String) -> String {
        if query.contains("wrong") || query.contains("incorrect") {
            return "🔍 **Option Analysis:**\n• Each distractor in this question represents a common clinical differential or misinterpretation.\n• Rule out distractors by checking timing of presentation, key laboratory markers, and contraindications."
        } else if query.contains("pearl") {
            return "🩺 **High-Yield Clinical Pearls:**\n• Always look for the 'buzzword' in clinical stems.\n• Next best step in unstable patients is always airway/breathing/circulation stabilization before definitive imaging."
        } else {
            return "💡 **Key Takeaways:**\n• Target condition: \(question.topic.isEmpty ? question.subject : question.topic)\n• Look for pathognomonic findings in the clinical presentation.\n• \(question.explanation.isEmpty ? "Review relevant guidelines in Harrison's / Robbins." : question.explanation)"
        }
    }

    private var cleanQuestionText: String {
        question.text.replacingOccurrences(of: #"^\d+[.\s\-)\]]+\s*"#, with: "", options: .regularExpression)
    }
}
