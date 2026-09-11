# MediGyaan for iOS

A native **SwiftUI** rewrite of the MediGyaan Android app, talking to the **same
live PHP backend** at `medigyaan.xyz/Neurons/`.

- **Language:** Swift 5.9 · **UI:** SwiftUI (no UIKit screens)
- **Minimum iOS:** 16.0 (mirrors Android `minSdk 26`)
- **Bundle id:** `com.corp.medigyaan` (mirrors Android `applicationId`)
- **Marketing version:** 4.0 (mirrors Android `versionName`)
- **Project generation:** [XcodeGen](https://github.com/yonaskolb/XcodeGen) — no
  `.xcodeproj` is committed, so merge conflicts in `project.pbxproj` are impossible

## Getting started

```bash
brew install xcodegen
xcodegen generate
open MediGyaan.xcodeproj
```

To build from the command line:

```bash
xcodebuild build \
  -project MediGyaan.xcodeproj \
  -scheme MediGyaan \
  -destination 'platform=iOS Simulator,name=iPhone 16' \
  CODE_SIGNING_ALLOWED=NO
```

## Architecture

```
MediGyaan/
├── App/                     Entry point, root router, DI environment
│   ├── MediGyaanApp.swift
│   ├── RootView.swift        Splash → Login / TabView gate
│   └── AppEnvironment.swift  `\.api` environment key
├── Core/
│   ├── Networking/           APIConfig, HTTPClient, APIError, multipart
│   ├── API/                  One client per backend domain + facade
│   ├── Auth/                 KeychainStore, SessionStore
│   ├── DesignSystem/         Theme tokens, shared components
│   └── Support/              LoadState
├── Models/                   Codable domain models + tolerant decoding
└── Features/                 One folder per screen group
```

### Layering

Views never touch `URLSession`. The dependency direction is:

```
View → ViewModel → MediGyaanAPI (facade) → <Domain>API → HTTPClient
```

`MediGyaanAPI` is injected through the SwiftUI environment (`\.api`), so a
preview or test can point at a stub host:

```swift
.environment(\.api, MediGyaanAPI.pointing(at: someURL))
```

### Tolerant decoding

PHP hands MySQL columns back as strings, so the API mixes
`{"user_id":"42"}` with `{"user_id":42}` and renames keys between scripts
(`user_id` / `userId` / `id`). Rather than fight `Codable`'s all-or-nothing
synthesis, models decode through the non-throwing helpers in
`Models/Support/Flexible.swift`:

```swift
init(from decoder: Decoder) throws {
    let container = try decoder.flexibleContainer()
    id    = container.flexInt("user_id", "userId", "id")
    name  = container.flexString("topic_name", "name", "title")
    items = container.flexArray("topics", "data", "results")
}
```

Each helper accepts several key spellings and falls back to a default instead of
throwing, so one renamed column cannot blank out an entire screen.

## Backend integration

Every endpoint is declared once in `APIConfig.Endpoint`. The full set was
extracted from the Android sources, including endpoints that only appeared
inside string templates there (e.g. `leaderboard1.php`).

**Two request encodings are required**, because the scripts disagree:

| Script style | Content type | Client method |
| --- | --- | --- |
| Reads `php://input` (e.g. `api/login.php`) | `application/json` | `post(json:to:)` |
| Reads `$_POST` (e.g. `api/sync_user_cache.php`) | `application/x-www-form-urlencoded` | `post(form:to:)` |

The `{ "success": false, ... }` envelope is handled in one place
(`HTTPClient.execute`), whether it arrives with HTTP 200, 400, or 401 — the
backend's own message is surfaced to the user via `APIError.server`.

### Verified live contracts

These were checked against production and are asserted in `LiveBackendTests`:

| Endpoint | Response |
| --- | --- |
| `api/login.php` | `{"success":false,"error":"Invalid credentials","code":401}` |
| `dash_api.php` | `{"success":false,"message":"Invalid User ID"}` |
| `get_quiz_questions.php` | `{"success":false,"message":"Invalid quiz_id"}` |
| `quiz_apiv2.php` | `{"success":false,"message":"Invalid user"}` |
| `api/fetch_posts.php` | `{"success":false,"error":"Unauthorized Access"}` |
| `predict_rank.php` | `{"success":false,"message":"No attempts found"}` |

## Testing

```bash
xcodebuild test -project MediGyaan.xcodeproj -scheme MediGyaan \
  -destination 'platform=iOS Simulator,name=iPhone 16'
```

- `ModelDecodingTests` — every payload shape the backend is known to emit
- `HTTPClientTests` — form/JSON encoding, URL construction, error mapping
- `SessionStoreTests` — session persistence and sign-out
- `LiveBackendTests` — **hits production**; asserts the real error contracts
  above. Skips automatically when the host is unreachable, so CI never goes red
  on a network blip.

## Differences from the Android app

Three deliberate changes, all security-motivated:

1. **No API keys in the binary.** Android ships Groq/Gemini/DeepSeek/Mistral keys
   in `ApiKeys.kt`. Those are trivially extractable from an `.ipa`, so `AIAPI`
   routes every call through the project's own `ask_ai2.php` gateway instead.
2. **Tokens live in the Keychain**, not unencrypted `SharedPreferences`
   (`KeychainStore`). Non-sensitive profile fields stay in `UserDefaults`.
3. **No cleartext by default.** The only reason `NSAllowsArbitraryLoads` is set
   in `Info.plist` is the handful of legacy `http://` scripts the Android app
   also allowed; it should be narrowed to those hosts before release.

## Status

Implemented end to end: authentication (login, register, OTP recovery),
dashboard, topics, quiz runner with scoring and sync, leaderboard, attempt
history, profile, settings, news feed, messenger, challenges hub, rank
predictor, referrals, and the thesis studio (chapters, references, PRISMA,
checklist, theme export).

Still to port from Android: live video calls (Jitsi SDK), reels, the home-screen
widget, offline Room-style caching, and admin/quiz-authoring screens.
