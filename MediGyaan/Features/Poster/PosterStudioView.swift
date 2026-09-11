import SwiftUI
import PhotosUI

/// "Poster" tab — ports `PosterAnalysisActivity` / `activity_thesis_analyzer.xml`,
/// backed by `poster_session_backend.php`.
///
/// The Android screen lets a student photograph a conference poster or paper and
/// have the backend extract its structure, then turn it into a thesis-ready
/// outline.
struct PosterStudioView: View {

    @EnvironmentObject private var session: SessionStore
    @Environment(\.api) private var api

    @State private var selectedItem: PhotosPickerItem?
    @State private var image: UIImage?
    @State private var isAnalyzing = false
    @State private var analysis: String = ""
    @State private var errorMessage: String?
    @State private var analysisState: LoadState<[ThesisChapter]> = .idle

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: AppTheme.Spacing.lg) {
                    header
                    picker
                    analyzeButton
                    results
                }
                .padding(AppTheme.Spacing.lg)
            }
            .screenBackground()
            .navigationTitle("Poster Studio")
            .navigationBarTitleDisplayMode(.inline)
            .errorAlert(message: $errorMessage)
            .onChange(of: selectedItem) { _ in
                Task { await loadImage() }
            }
        }
    }

    // MARK: - Sections

    private var header: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                HStack(spacing: AppTheme.Spacing.sm) {
                    Image(systemName: "doc.text.image")
                        .font(.system(size: 24))
                        .foregroundStyle(AppTheme.Palette.primary)
                    Text("Poster to thesis")
                        .font(AppTheme.Font.cardTitle)
                }

                Text("Photograph a conference poster or paper. MediGyaan extracts its sections and drafts a thesis outline you can keep editing in Thesis Studio.")
                    .font(AppTheme.Font.callout)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var picker: some View {
        PhotosPicker(selection: $selectedItem, matching: .images) {
            if let image {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFill()
                    .frame(maxWidth: .infinity)
                    .frame(height: 220)
                    .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.materialCard, style: .continuous))
            } else {
                VStack(spacing: AppTheme.Spacing.sm) {
                    Image(systemName: "photo.on.rectangle.angled")
                        .font(.system(size: 32))
                        .foregroundStyle(AppTheme.Palette.primary)
                    Text("Select a poster image")
                        .font(AppTheme.Font.callout)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }
                .frame(maxWidth: .infinity)
                .frame(height: 180)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.materialCard, style: .continuous)
                        .fill(AppTheme.Palette.cardBackground)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.materialCard, style: .continuous)
                        .strokeBorder(
                            AppTheme.Palette.outline,
                            style: StrokeStyle(lineWidth: 1, dash: [6, 4])
                        )
                )
            }
        }
        .buttonStyle(.plain)
    }

    private var analyzeButton: some View {
        PrimaryButton(
            title: "Analyse poster",
            isLoading: isAnalyzing,
            isEnabled: image != nil
        ) {
            Task { await analyze() }
        }
    }

    @ViewBuilder
    private var results: some View {
        if isAnalyzing {
            LoadingStateView(message: "Reading your poster…")
                .frame(height: 140)
        } else if !analysis.isEmpty {
            CardContainer {
                VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                    Text("Extracted outline")
                        .font(AppTheme.Font.cardTitle)
                    Text(analysis)
                        .font(AppTheme.Font.callout)
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                    NavigationLink("Open Thesis Studio") { ThesisHomeView() }
                        .font(AppTheme.Font.captionBold)
                }
            }
        }
    }

    // MARK: - Actions

    @MainActor
    private func loadImage() async {
        guard let selectedItem else { return }
        do {
            guard let data = try await selectedItem.loadTransferable(type: Data.self),
                  let uiImage = UIImage(data: data) else {
                errorMessage = "That image could not be read."
                return
            }
            image = uiImage
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    @MainActor
    private func analyze() async {
        guard let image, !isAnalyzing else { return }
        isAnalyzing = true
        defer { isAnalyzing = false }

        // The poster backend expects a base64 payload in a form field, matching
        // how the Android client uploaded the captured bitmap.
        guard let jpeg = image.jpegData(compressionQuality: 0.7) else {
            errorMessage = "That image could not be encoded."
            return
        }

        do {
            let response = try await api.thesis.analyzePoster(
                userId: session.userId,
                imageBase64: jpeg.base64EncodedString()
            )
            analysis = response
            if response.isEmpty {
                errorMessage = "We could not read any sections from that poster."
            }
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

#Preview {
    PosterStudioView()
        .environmentObject(SessionStore())
        .environment(\.api, .live)
}
