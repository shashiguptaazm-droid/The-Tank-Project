import PhotosUI
import SwiftUI
import UIKit

/// Profile editor. Ports `EditProfileActivity` (`activity_edit_profile.xml`).
///
/// The Android screen is one scrolling form of four Material cards — photo,
/// Identity, Academic Details, Contact — under a close-icon toolbar, guarded by
/// an unsaved-changes dialog that only fires once a new photo has been staged.
/// Both the load (`GET update_profile_api.php?user_id&viewer_id`) and the save
/// (`POST update_profile_api.php`) target the same legacy script the Kotlin builds
/// by hand with Volley; the request and response shapes below are copied field
/// for field from `EditProfileActivity.loadProfile()` / `saveProfile()`.
///
/// Requires a host `NavigationStack` — the Kotlin toolbar's `finish()` becomes
/// `dismiss()` plus a custom leading close button so the swipe-back gesture can
/// be gated by ``isDiscardingBlocked``.
struct EditProfileView: View {

    /// Seed profile supplied by the caller. Mirrors Android reading `user_id`
    /// out of `SharedPreferences("MY_APP")` during `onCreate`; when `nil` the
    /// view falls back to `SessionStore.currentUser`.
    private let initialUser: User?

    /// Ports Android's `setResult(RESULT_OK)`: the host refreshes its cached
    /// profile after a successful save. Defaults to `nil` so `ProfileView` can
    /// push this screen with a bare `EditProfileView()`.
    var onSaved: ((User) -> Void)?

    @EnvironmentObject private var session: SessionStore
    @Environment(\.dismiss) private var dismiss
    @StateObject private var model: EditProfileViewModel
    @AppStorage("selected_subject_preference") private var selectedGoal: String = "NEET PG"

    @State private var pickerItem: PhotosPickerItem?
    @State private var isConfirmingDiscard = false

    init(user: User? = nil, onSaved: ((User) -> Void)? = nil) {
        initialUser = user
        self.onSaved = onSaved
        _model = StateObject(wrappedValue: EditProfileViewModel(seed: user))
    }

    /// `updateGoalDisplay()`: the stored preference, falling back to "NEET PG"
    /// when it is absent or blank.
    private var goal: String {
        let trimmed = selectedGoal.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? "NEET PG" : trimmed
    }

    /// `setLoading(true)` — Android shows the progress bar and disables both the
    /// save and change-photo buttons for the *load* and the *save*.
    private var isBusy: Bool { model.loadState.isLoading || model.isSaving }

    /// Android's guard is `selectedPhotoBase64 != null`, so text edits alone
    /// never raise the discard dialog.
    private var hasStagedPhoto: Bool { model.photoBase64 != nil }

    var body: some View {
        ScrollView {
            VStack(spacing: AppTheme.Spacing.md) {
                photoCard
                identityCard
                academicCard
                contactCard

                if isBusy {
                    ProgressView()
                        .progressViewStyle(.linear)
                        .padding(.top, AppTheme.Spacing.xs)
                }

                PrimaryButton(
                    title: "Save Profile",
                    icon: nil,
                    isLoading: model.isSaving,
                    isEnabled: !isBusy,
                    isSubmit: true
                ) {
                    Task { await save() }
                }
                .padding(.bottom, AppTheme.Spacing.xxl)
            }
            .padding(AppTheme.Spacing.lg)
        }
        .screenBackground()
        .navigationTitle("Edit Profile")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button {
                    requestDismiss()
                } label: {
                    Image(systemName: "xmark")
                }
                .accessibilityLabel("Close")
            }
        }
        .navigationBarBackButtonHidden()
        .interactiveDismissDisabled(hasStagedPhoto)
        .confirmationDialog(
            "Unsaved Profile Changes",
            isPresented: $isConfirmingDiscard,
            titleVisibility: .visible
        ) {
            Button("Discard", role: .destructive) { dismiss() }
            Button("Keep editing", role: .cancel) { }
        } message: {
            Text("You have unsaved changes. Are you sure you want to discard them?")
        }
        .errorAlert(message: binding(\.errorMessage))
        .task {
            await model.load(userId: session.userId)
        }
        .onChange(of: pickerItem) { newValue in
            Task { await model.stagePhoto(from: newValue) }
        }
    }

    // MARK: - Cards

    /// `R.id.imgEditProfile` — 112dp `ShapeableImageView` with the
    /// `CircleImage` shape overlay, a 3dp `@color/primary` stroke and
    /// `@drawable/ic_user_placeholder` as the static `src`.
    private var photoCard: some View {
        CardContainer {
            VStack(spacing: AppTheme.Spacing.xs) {
                avatar

                PhotosPicker(selection: $pickerItem, matching: .images) {
                    Text("Change photo")
                        .font(AppTheme.Font.callout)
                        .foregroundStyle(AppTheme.Palette.primary)
                }
                .disabled(isBusy)

                Text("Keep your profile complete so friends can identify you in battles and leaderboards.")
                    .font(AppTheme.Font.subheadline)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
                    .multilineTextAlignment(.center)

                if let photoError = model.photoError {
                    Text(photoError)
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.danger)
                }
            }
            .frame(maxWidth: .infinity)
        }
    }

    /// `R.id.etName` (`textPersonName`, 1 line) over `R.id.etBio`
    /// (`textMultiLine|textCapSentences`, `minLines="3"`).
    private var identityCard: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                SectionHeader(title: "Identity")

                LabeledField(
                    title: "Full name",
                    systemImage: "person",
                    text: binding(\.name),
                    contentType: .name
                )

                if let nameError = model.nameError {
                    Text(nameError)
                        .font(AppTheme.Font.caption)
                        .foregroundStyle(AppTheme.Palette.danger)
                }

                multilineField(title: "Bio", text: binding(\.bio), minimumLines: 3)
            }
        }
    }

    /// `R.id.layoutGoalSelector` / `R.id.txtEditGoal`, then `R.id.autoCollege`,
    /// `R.id.etState`, `R.id.etCity`, `R.id.etBatchYear`, `R.id.etPassingYear`.
    private var academicCard: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                SectionHeader(title: "Academic Details")

                NavigationLink {
                    GoalSelectionView()
                } label: {
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Target Exam / Goal")
                                .font(AppTheme.Font.caption)
                                .foregroundStyle(AppTheme.Palette.textSecondary)
                            Text(goal)
                                .font(AppTheme.Font.callout.weight(.semibold))
                                .foregroundStyle(AppTheme.Palette.textPrimary)
                        }
                        Spacer()
                        Text("Change ›")
                            .font(AppTheme.Font.callout.weight(.semibold))
                            .foregroundStyle(AppTheme.Palette.primary)
                    }
                    .padding(AppTheme.Spacing.md)
                    .background(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.sm, style: .continuous)
                            .fill(AppTheme.Palette.cardBackgroundElevated)
                    )
                }

                LabeledField(
                    title: "College name",
                    systemImage: "building.columns",
                    text: binding(\.collegeName),
                    contentType: .organizationName
                )

                HStack(alignment: .top, spacing: AppTheme.Spacing.sm) {
                    LabeledField(title: "State", systemImage: "map", text: binding(\.region))
                        .frame(maxWidth: .infinity)
                    LabeledField(title: "City", systemImage: "building.2", text: binding(\.city))
                        .frame(maxWidth: .infinity)
                }

                HStack(alignment: .top, spacing: AppTheme.Spacing.sm) {
                    LabeledField(
                        title: "Batch year",
                        systemImage: "calendar",
                        text: capped(\.batchYear, limit: 4),
                        keyboard: .numberPad
                    )
                    .frame(maxWidth: .infinity)
                    LabeledField(
                        title: "Passing year",
                        systemImage: "graduationcap",
                        text: capped(\.passingYear, limit: 4),
                        keyboard: .numberPad
                    )
                    .frame(maxWidth: .infinity)
                }
            }
        }
    }

    /// `R.id.etMobile` (`inputType="phone"`, `maxLength="15"`) and
    /// `R.id.etAddress` (`textMultiLine|textCapSentences`, `minLines="2"`).
    private var contactCard: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                SectionHeader(title: "Contact")

                LabeledField(
                    title: "Mobile number",
                    systemImage: "phone",
                    text: capped(\.mobile, limit: 15),
                    keyboard: .phonePad,
                    contentType: .telephoneNumber
                )

                multilineField(title: "Address", text: binding(\.address), minimumLines: 2)
            }
        }
    }

    @ViewBuilder
    private var avatar: some View {
        Group {
            if let staged = model.stagedPhoto {
                Image(uiImage: staged)
                    .resizable()
                    .scaledToFill()
            } else if let remote = model.remotePhotoURL {
                AsyncImage(url: remote) { phase in
                    if case let .success(image) = phase {
                        image.resizable().scaledToFill()
                    } else {
                        placeholder
                    }
                }
            } else {
                placeholder
            }
        }
        .frame(width: 112, height: 112)
        .clipShape(Circle())
        .overlay(Circle().stroke(AppTheme.Palette.primary, lineWidth: 3))
    }

    private var placeholder: some View {
        AndroidIcon(.ic_user_placeholder, size: 96, tint: AppTheme.Palette.textMuted)
    }

    /// `TextInputEditText` with `gravity="top"` and a `minLines` floor. The
    /// shared ``LabeledField`` is single-line, so the multi-line inputs keep
    /// their own box built from the same theme tokens.
    private func multilineField(title: String, text: Binding<String>, minimumLines: Int) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.xs) {
            Text(title)
                .font(AppTheme.Font.caption.weight(.medium))
                .foregroundStyle(AppTheme.Palette.textSecondary)

            TextField(title, text: text, axis: .vertical)
                .lineLimit(minimumLines ... (minimumLines + 3))
                .textInputAutocapitalization(.sentences)
                .padding(AppTheme.Spacing.md)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.sm, style: .continuous)
                        .fill(AppTheme.Palette.cardBackground)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.sm, style: .continuous)
                        .stroke(AppTheme.Palette.divider, lineWidth: 1)
                )
        }
    }

    // MARK: - Actions

    /// iOS 16 has no `Bindable`, and the model must stay a `@StateObject` so
    /// half-typed fields survive `ProfileView` re-rendering behind it. This
    /// builds the same two-way bindings by hand.
    private func binding<T>(_ keyPath: ReferenceWritableKeyPath<EditProfileViewModel, T>) -> Binding<T> {
        Binding(
            get: { model[keyPath: keyPath] },
            set: { model[keyPath: keyPath] = $0 }
        )
    }

    /// Ports `android:maxLength` on the year and phone inputs.
    private func capped(_ keyPath: ReferenceWritableKeyPath<EditProfileViewModel, String>, limit: Int) -> Binding<String> {
        Binding(
            get: { model[keyPath: keyPath] },
            set: { model[keyPath: keyPath] = String($0.prefix(limit)) }
        )
    }

    /// `OnBackPressedCallback` — a staged photo raises the discard dialog, any
    /// other state pops straight away.
    private func requestDismiss() {
        guard hasStagedPhoto else {
            dismiss()
            return
        }
        isConfirmingDiscard = true
    }

    @MainActor
    private func save() async {
        await model.save(userId: session.userId)
        guard model.savedSuccessfully else { return }
        let updated = syncSession()
        onSaved?(updated)
        dismiss()
    }

    /// Mirrors Android's `setResult(RESULT_OK)`: the seeded profile is merged
    /// back into `SessionStore` and handed to ``onSaved`` so `ProfileView`
    /// re-renders without a refetch. Fields `User` cannot carry (`bio`, `state`,
    /// `city`, the two years, `address`) are dropped on the way out — the backend
    /// keeps them and the next `get_profilev1.php` restores them.
    @discardableResult
    private func syncSession() -> User {
        let existing = session.currentUser ?? initialUser
        let updated = User(
            id: existing?.id ?? session.userId,
            name: model.name,
            email: existing?.email ?? "",
            phone: model.mobile,
            avatarURL: existing?.avatarURL,
            college: model.collegeName,
            course: existing?.course ?? "",
            referralCode: existing?.referralCode ?? "",
            isVerified: existing?.isVerified ?? true,
            streak: existing?.streak ?? 0,
            overallAttempted: existing?.overallAttempted ?? 0,
            overallCorrect: existing?.overallCorrect ?? 0
        )
        session.updateProfile(updated)
        return updated
    }
}

/// Ports `EditProfileActivity`: loads the profile over the legacy
/// `update_profile_api.php` script, stages a downscaled JPEG avatar as base64,
/// and saves the ten editable fields.
///
/// Replaces Volley's `StringRequest` queue and its `setLoading()` visibility
/// juggling with the app's `LoadState` enum and async/await. ``loadState``'s
/// value is the resolved remote avatar `URL`, matching Android's Glide target.
@MainActor
final class EditProfileViewModel: ObservableObject {

    // MARK: - Editable fields (`EditProfileActivity.getParams()`)

    @Published var name = ""
    @Published var bio = ""
    @Published var collegeName = ""
    /// Sent as `state`; renamed off `state` so it cannot be confused with
    /// SwiftUI's own `State`.
    @Published var region = ""
    @Published var city = ""
    @Published var batchYear = ""
    @Published var passingYear = ""
    @Published var mobile = ""
    @Published var address = ""

    // MARK: - Transient state

    @Published private(set) var loadState: LoadState<URL?> = .idle
    @Published private(set) var isSaving = false
    @Published private(set) var savedSuccessfully = false
    @Published private(set) var remotePhotoURL: URL?
    @Published private(set) var stagedPhoto: UIImage?
    /// Base64 JPEG sent as the optional `photo_base64` field.
    @Published private(set) var photoBase64: String?
    @Published var photoError: String?
    @Published var nameError: String?
    @Published var errorMessage: String?

    private let client: HTTPClient

    init(client: HTTPClient = .shared, seed: User? = nil) {
        self.client = client
        if let seed {
            name = seed.name
            mobile = seed.phone
            collegeName = seed.college
            remotePhotoURL = seed.avatarURL
        }
    }

    // MARK: - Load

    /// Ports `EditProfileActivity.loadProfile()`:
    /// `GET {BASE_URL}update_profile_api.php?user_id=<id>&viewer_id=<id>`.
    func load(userId: Int) async {
        guard userId > 0 else {
            errorMessage = "Please login again"
            return
        }
        loadState = .loading
        do {
            let payload = try await client.getObject(
                .updateProfile,
                query: ["user_id": String(userId), "viewer_id": String(userId)]
            )
            guard Self.isSuccess(payload) else {
                let message = Self.message(of: payload) ?? "Profile load failed"
                loadState = .failed(message)
                errorMessage = message
                return
            }
            apply(payload["data"] as? [String: Any] ?? [:])
            loadState = .loaded(remotePhotoURL)
        } catch {
            loadState = .failed(LoadState<Never>.message(for: error))
            errorMessage = LoadState<Never>.message(for: error)
        }
    }

    /// Ports `EditProfileActivity.bindProfile(JSONObject)`.
    private func apply(_ data: [String: Any]) {
        name = Self.string(data["name"])
        bio = Self.string(data["bio"])
        collegeName = Self.string(data["college_name"])
        region = Self.string(data["state"])
        city = Self.string(data["city"])
        batchYear = Self.positiveYear(data["batch_year"])
        passingYear = Self.positiveYear(data["passing_year"])
        mobile = Self.string(data["mobile_no"])
        address = Self.string(data["address"])
        remotePhotoURL = Self.photoURL(from: data)
    }

    // MARK: - Photo

    /// Ports `EditProfileActivity.handleSelectedPhoto()` +
    /// `scaleBitmap(bitmap, 900)`: downscale so the longest side is at most
    /// 900 px, JPEG-compress at quality 84, then base64-encode without line
    /// breaks. `ActivityResultContracts.GetContent()` becomes `PhotosPicker`.
    func stagePhoto(from item: PhotosPickerItem?) async {
        guard let item else { return }
        photoError = nil
        guard let data = try? await item.loadTransferable(type: Data.self),
              let image = UIImage(data: data) else {
            photoError = "Could not read image"
            return
        }
        let scaled = image.scaledToFit(maxSide: 900)
        guard let jpeg = scaled.jpegData(compressionQuality: 0.84) else {
            photoError = "Could not prepare image"
            return
        }
        stagedPhoto = scaled
        photoBase64 = jpeg.base64EncodedString()
    }

    // MARK: - Save

    /// Ports `EditProfileActivity.saveProfile()`: trims every field, requires a
    /// name of at least two characters, then `POST`s the ten parameters plus an
    /// optional `photo_base64` to `update_profile_api.php`.
    func save(userId: Int) async {
        let trimmedName = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmedName.count >= 2 else {
            nameError = "Required"
            return
        }
        nameError = nil
        guard userId > 0, !isSaving else { return }

        isSaving = true
        defer { isSaving = false }
        savedSuccessfully = false

        var form: [String: String] = [
            "user_id": String(userId),
            "name": trimmedName,
            "bio": bio.trimmed,
            "college_name": collegeName.trimmed,
            "state": region.trimmed,
            "city": city.trimmed,
            "batch_year": batchYear.trimmed,
            "passing_year": passingYear.trimmed,
            "mobile_no": mobile.trimmed,
            "address": address.trimmed,
        ]
        if let photoBase64 {
            form["photo_base64"] = photoBase64
        }

        do {
            let payload = try await client.postObject(form: form, to: .updateProfile)
            guard Self.isSuccess(payload) else {
                errorMessage = Self.message(of: payload) ?? "Update failed"
                return
            }
            name = trimmedName
            savedSuccessfully = true
            RemoteLogger.log(tag: "EditProfile_Saved", message: "Profile updated for userId \(userId)")
        } catch {
            errorMessage = LoadState<Never>.message(for: error)
        }
    }

    // MARK: - Payload helpers

    /// Kotlin compares `root.optString("status") != "success"`. The same scripts
    /// sometimes answer with `success: true` instead, so both are accepted.
    private static func isSuccess(_ payload: [String: Any]) -> Bool {
        if let status = payload["status"] as? String, !status.isEmpty {
            return status == "success"
        }
        if let success = payload["success"] as? Bool {
            return success
        }
        return false
    }

    private static func message(of payload: [String: Any]) -> String? {
        for key in ["message", "error"] {
            if let text = payload[key] as? String, !text.isEmpty { return text }
        }
        return nil
    }

    /// `JSONObject.optString` coerces numbers and booleans to text.
    private static func string(_ value: Any?) -> String {
        switch value {
        case let text as String: return text
        case let number as NSNumber: return number.stringValue
        default: return ""
        }
    }

    /// Mirrors `optInt(key, 0).takeIf { it > 0 }?.toString().orEmpty()`.
    private static func positiveYear(_ value: Any?) -> String {
        switch value {
        case let number as NSNumber:
            let year = number.intValue
            return year > 0 ? String(year) : ""
        case let text as String:
            let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
            guard let year = Int(trimmed), year > 0 else { return "" }
            return String(year)
        default:
            return ""
        }
    }

    /// Kotlin: `photo.startsWith("http") ? photo : BASE_URL + photo.removePrefix("./").trimStart('/')`,
    /// skipped entirely when the field is blank or the literal string `"null"`.
    private static func photoURL(from data: [String: Any]) -> URL? {
        let raw = string(data["photo"]).trimmingCharacters(in: .whitespacesAndNewlines)
        guard !raw.isEmpty, raw != "null" else { return nil }
        if raw.lowercased().hasPrefix("http") {
            return URL(string: raw)
        }
        var relative = raw
        if relative.hasPrefix("./") { relative.removeFirst(2) }
        while relative.hasPrefix("/") { relative.removeFirst() }
        return URL(string: APIConfig.baseURL.absoluteString + relative)
    }
}

private extension String {
    /// Android's `TextInputEditText.textValue()`: `text?.trim().orEmpty()`.
    var trimmed: String {
        trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

private extension UIImage {
    /// Ports `EditProfileActivity.scaleBitmap(source, maxSide)` — returns the
    /// receiver untouched when it already fits inside the box.
    func scaledToFit(maxSide: CGFloat) -> UIImage {
        let largest = max(size.width, size.height)
        guard largest > maxSide, largest > 0 else { return self }
        let scale = maxSide / largest
        let target = CGSize(
            width: max(1, (size.width * scale).rounded(.down)),
            height: max(1, (size.height * scale).rounded(.down))
        )
        return UIGraphicsImageRenderer(size: target).image { _ in
            draw(in: CGRect(origin: .zero, size: target))
        }
    }
}