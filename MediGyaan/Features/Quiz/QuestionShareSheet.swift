import SwiftUI
import UIKit

/// Bottom sheet for sharing an MCQ across social media channels and inside MediGyaan.
struct QuestionShareSheet: View {

    let question: Question
    let userId: Int
    var onAddToQuiz: (() -> Void)? = nil
    var onOpenFeed: (() -> Void)? = nil
    var onOpenChallenge: (() -> Void)? = nil
    var onOpenSharedQuestions: (() -> Void)? = nil

    @Environment(\.dismiss) private var dismiss
    @State private var shareFormat: ShareFormat = .imageCard
    @State private var includeAnswer: Bool = false
    @State private var isShowingMediGyaanMenu = false
    @State private var isShowingSystemShare = false
    @State private var shareItems: [Any] = []
    @State private var toastMessage: String? = nil

    enum ShareFormat: String, CaseIterable {
        case imageCard = "🖼️ Image Card"
        case text = "📝 Text + Link"
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    // Format Picker
                    Picker("Format", selection: $shareFormat) {
                        ForEach(ShareFormat.allCases, id: \.self) { format in
                            Text(format.rawValue).tag(format)
                        }
                    }
                    .pickerStyle(.segmented)
                    .padding(.horizontal)

                    // Optional Answer & Explanation Checkbox
                    Toggle(isOn: $includeAnswer) {
                        Text("Include correct answer & explanation")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundStyle(Color(hex: 0x39_49_AB))
                    }
                    .padding(.horizontal)

                    // Mini Preview Card
                    previewCard
                        .padding(.horizontal)

                    // Featured MediGyaan In-App Share Card
                    mediGyaanInAppCard
                        .padding(.horizontal)

                    // Social Channels Grid
                    VStack(alignment: .leading, spacing: 14) {
                        Text("Share to")
                            .font(.system(size: 15, weight: .bold))
                            .foregroundStyle(Color(hex: 0x1A_1C_2E))
                            .padding(.horizontal)

                        // Row 1: MediGyaan, WhatsApp, Telegram, Instagram, X
                        HStack(spacing: 0) {
                            socialButton(name: "MediGyaan", icon: "ic_launcher", isAppIcon: true) {
                                isShowingMediGyaanMenu = true
                            }
                            socialButton(name: "WhatsApp", icon: "message.fill", bgColor: Color(hex: 0x25_D3_66)) {
                                shareToWhatsApp()
                            }
                            socialButton(name: "Telegram", icon: "paperplane.fill", bgColor: Color(hex: 0x00_88_CC)) {
                                shareToTelegram()
                            }
                            socialButton(name: "Instagram", icon: "camera.fill", bgColor: Color(hex: 0xE1_30_6C)) {
                                shareToInstagram()
                            }
                            socialButton(name: "X", icon: "xmark", bgColor: .black) {
                                shareToTwitter()
                            }
                        }

                        // Row 2: Facebook, LinkedIn, Messages, Copy, More
                        HStack(spacing: 0) {
                            socialButton(name: "Facebook", icon: "f.square.fill", bgColor: Color(hex: 0x18_77_F2)) {
                                shareToFacebook()
                            }
                            socialButton(name: "LinkedIn", icon: "link", bgColor: Color(hex: 0x0A_66_C2)) {
                                shareToLinkedIn()
                            }
                            socialButton(name: "Messages", icon: "bubble.left.and.bubble.right.fill", bgColor: Color(hex: 0x00_89_7B)) {
                                shareToSMS()
                            }
                            socialButton(name: "Copy Text", icon: "doc.on.doc.fill", bgColor: Color(hex: 0x54_6E_7A)) {
                                copyToClipboard()
                            }
                            socialButton(name: "More", icon: "square.and.arrow.up", bgColor: Color(hex: 0x5C_6B_C0)) {
                                openSystemShare()
                            }
                        }
                    }

                    // System Chooser Full-Width Button
                    Button {
                        openSystemShare()
                    } label: {
                        HStack {
                            Image(systemName: "square.and.arrow.up")
                            Text("More Options & Apps…")
                        }
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .frame(height: 50)
                        .background(Color(hex: 0x5C_6B_C0))
                        .clipShape(RoundedRectangle(cornerRadius: 14))
                    }
                    .padding(.horizontal)
                    .padding(.top, 4)
                }
                .padding(.vertical)
            }
            .navigationTitle("Share Question")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
            }
            .confirmationDialog("Share inside MediGyaan", isPresented: $isShowingMediGyaanMenu, titleVisibility: .visible) {
                Button("📢 Post to Community Feed") {
                    dismiss()
                    onOpenFeed?()
                }
                Button("⚔️ Challenge a Peer (1v1 Battle)") {
                    dismiss()
                    onOpenChallenge?()
                }
                Button("📑 Add to My Custom Quiz") {
                    dismiss()
                    onAddToQuiz?()
                }
                Button("📊 View My Shared Questions") {
                    dismiss()
                    onOpenSharedQuestions?()
                }
                Button("Cancel", role: .cancel) {}
            }
            .sheet(isPresented: $isShowingSystemShare) {
                ActivityView(activityItems: shareItems)
            }
            .overlay(alignment: .bottom) {
                if let message = toastMessage {
                    Text(message)
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 10)
                        .background(Color.black.opacity(0.85))
                        .clipShape(Capsule())
                        .padding(.bottom, 20)
                        .transition(.opacity)
                }
            }
        }
    }

    // MARK: - Mini Preview Card

    private var previewCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("🧠 MediGyaan MCQ")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(Color(hex: 0x64_DF_DF))

                Spacer()

                Text("Q#\(question.id)")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(Color(hex: 0xF4_C9_5D))
            }

            Text(cleanQuestionText)
                .font(.system(size: 14, weight: .bold))
                .foregroundStyle(.white)
                .lineLimit(3)

            Text(optionsPreviewText)
                .font(.system(size: 12))
                .foregroundStyle(Color(hex: 0x9F_B3_CC))
                .lineLimit(2)
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(hex: 0x0D_1B_2A))
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(Color(hex: 0x2E_40_68), lineWidth: 1)
        )
    }

    // MARK: - Featured MediGyaan Card

    private var mediGyaanInAppCard: some View {
        Button {
            isShowingMediGyaanMenu = true
        } label: {
            HStack(spacing: 14) {
                ZStack {
                    Circle()
                        .fill(
                            LinearGradient(
                                colors: [Color(hex: 0x5C_6B_C0), Color(hex: 0x1A_23_7E)],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .frame(width: 44, height: 44)

                    Image("ic_launcher")
                        .resizable()
                        .scaledToFit()
                        .frame(width: 28, height: 28)
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                }

                VStack(alignment: .leading, spacing: 2) {
                    Text("Share in MediGyaan")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundStyle(Color(hex: 0x1E_1B_4B))

                    Text("Community Feed • 1v1 Battle • My Quizzes")
                        .font(.system(size: 12))
                        .foregroundStyle(Color(hex: 0x4F_46_E5))
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(Color(hex: 0x43_38_CA))
            }
            .padding(12)
            .background(Color(hex: 0xEE_F2_FF))
            .clipShape(RoundedRectangle(cornerRadius: 14))
            .overlay(
                RoundedRectangle(cornerRadius: 14)
                    .stroke(Color(hex: 0xC7_D2_FE), lineWidth: 1.5)
            )
        }
        .buttonStyle(.plain)
    }

    // MARK: - Social Channel Icon Button

    private func socialButton(
        name: String,
        icon: String,
        bgColor: Color = .blue,
        isAppIcon: Bool = false,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            VStack(spacing: 6) {
                if isAppIcon {
                    ZStack {
                        Circle()
                            .fill(
                                LinearGradient(
                                    colors: [Color(hex: 0x5C_6B_C0), Color(hex: 0x1A_23_7E)],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                            .frame(width: 46, height: 46)

                        Image(icon)
                            .resizable()
                            .scaledToFit()
                            .frame(width: 28, height: 28)
                            .clipShape(RoundedRectangle(cornerRadius: 6))
                    }
                } else {
                    ZStack {
                        Circle()
                            .fill(bgColor)
                            .frame(width: 46, height: 46)

                        Image(systemName: icon)
                            .font(.system(size: 20))
                            .foregroundStyle(.white)
                    }
                }

                Text(name)
                    .font(.system(size: 11, weight: isAppIcon ? .bold : .regular))
                    .foregroundStyle(isAppIcon ? Color(hex: 0x1E_1B_4B) : Color(hex: 0x1A_1C_2E))
                    .lineLimit(1)
            }
            .frame(maxWidth: .infinity)
        }
        .buttonStyle(.plain)
    }

    // MARK: - Actions

    private var shareURL: String {
        "https://medigyaan.com/Neurons/share.php?question_id=\(question.id)&ref=\(userId)"
    }

    private var shareText: String {
        var text = "🧠 *MediGyaan Medical MCQ Challenge*\n"
        if !question.subject.isEmpty {
            text += "📚 *Subject:* \(question.subject)"
            if !question.topic.isEmpty, question.topic != "General", question.topic != "Uncategorized" {
                text += " • *Topic:* \(question.topic)"
            }
            text += "\n\n"
        }
        text += "*Q:* \(cleanQuestionText)\n\n"
        let letters = ["A", "B", "C", "D", "E"]
        for (i, opt) in question.options.enumerated() {
            let l = letters.indices.contains(i) ? letters[i] : "\(i + 1)"
            text += "\(l)) \(opt)\n"
        }
        text += "\n"
        if includeAnswer {
            if let correct = question.correctOption {
                text += "✅ *Correct Answer:* \(correct)\n"
            }
            if !question.explanation.isEmpty {
                text += "💡 *Explanation:* \(question.explanation)\n\n"
            }
        }
        text += "🎯 *Can you solve this? Attempt on MediGyaan:*\n👉 \(shareURL)\n\n#MediGyaan #NEETPG #MedicalMCQ"
        return text
    }

    private func copyToClipboard() {
        UIPasteboard.general.string = shareText
        showToast("Question copied to clipboard! 📋")
    }

    private func shareToWhatsApp() {
        if shareFormat == .imageCard, let image = QuestionCardRenderer.render(question: question, includeAnswer: includeAnswer) {
            shareItems = [image, shareText]
            isShowingSystemShare = true
            return
        }
        if let encoded = shareText.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
           let url = URL(string: "whatsapp://send?text=\(encoded)"),
           UIApplication.shared.canOpenURL(url) {
            UIApplication.shared.open(url)
        } else {
            openSystemShare()
        }
    }

    private func shareToTelegram() {
        if shareFormat == .imageCard, let image = QuestionCardRenderer.render(question: question, includeAnswer: includeAnswer) {
            shareItems = [image, shareText]
            isShowingSystemShare = true
            return
        }
        if let encoded = shareText.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
           let url = URL(string: "tg://msg?text=\(encoded)"),
           UIApplication.shared.canOpenURL(url) {
            UIApplication.shared.open(url)
        } else if let web = URL(string: "https://t.me/share/url?url=\(shareURL)&text=\(shareText.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")") {
            UIApplication.shared.open(web)
        } else {
            openSystemShare()
        }
    }

    private func shareToInstagram() {
        if let image = QuestionCardRenderer.render(question: question, includeAnswer: includeAnswer) {
            shareItems = [image, shareText]
            isShowingSystemShare = true
        } else {
            openSystemShare()
        }
    }

    private func shareToTwitter() {
        if shareFormat == .imageCard, let image = QuestionCardRenderer.render(question: question, includeAnswer: includeAnswer) {
            shareItems = [image, shareText]
            isShowingSystemShare = true
            return
        }
        if let encoded = shareText.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
           let url = URL(string: "https://twitter.com/intent/tweet?text=\(encoded)") {
            UIApplication.shared.open(url)
        } else {
            openSystemShare()
        }
    }

    private func shareToFacebook() {
        openSystemShare()
    }

    private func shareToLinkedIn() {
        openSystemShare()
    }

    private func shareToSMS() {
        if let encoded = shareText.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
           let url = URL(string: "sms:&body=\(encoded)"),
           UIApplication.shared.canOpenURL(url) {
            UIApplication.shared.open(url)
        } else {
            copyToClipboard()
        }
    }

    private func openSystemShare() {
        if shareFormat == .imageCard, let image = QuestionCardRenderer.render(question: question, includeAnswer: includeAnswer) {
            shareItems = [image, shareText]
        } else {
            shareItems = [shareText]
        }
        isShowingSystemShare = true
    }

    private func showToast(_ msg: String) {
        withAnimation { toastMessage = msg }
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
            withAnimation { toastMessage = nil }
        }
    }

    private var cleanQuestionText: String {
        question.text.replacingOccurrences(of: #"^\d+[.\s\-)\]]+\s*"#, with: "", options: .regularExpression)
    }

    private var optionsPreviewText: String {
        let letters = ["A", "B", "C", "D", "E"]
        return question.options.enumerated().map { i, opt in
            let l = letters.indices.contains(i) ? letters[i] : "\(i + 1)"
            return "\(l)) \(opt)"
        }.joined(separator: " • ")
    }
}

/// A SwiftUI wrapper for `UIActivityViewController`.
struct ActivityView: UIViewControllerRepresentable {
    let activityItems: [Any]
    let applicationActivities: [UIActivity]? = nil

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: activityItems, applicationActivities: applicationActivities)
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}
