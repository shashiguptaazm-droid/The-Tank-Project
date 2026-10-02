# MediGyaan Engineering Runbook: Agent Continuity Guide

**Date**: 2026-10-02  
**Target Projects**:
- **iOS Repository**: `C:\Users\Shash\AndroidStudioProjects\ios_project\MediGyaan`
- **Android Repository**: `C:\Users\Shash\AndroidStudioProjects\MediGyaan`
- **Remote Tank Repository**: `https://github.com/shashiguptaazm-droid/The-Tank-Project.git` (branch `main` pushed to remote `tank:ios-swiftui`)
- **CI / CD Releases**: [The-Tank-Project GitHub Releases `v4.0-latest`](https://github.com/shashiguptaazm-droid/The-Tank-Project/releases/tag/v4.0-latest)

---

## 1. Project Identity & Critical Rules

1. **Application Identity**:
   - Application Name: **MediGyaan**
   - Package/Bundle: `com.corp.medigyaan` / `com.rankwarz.edulabsrtm`
   - Purpose: Medical learning and NEET preparation platform featuring 3D gamified animal warrior avatars.
   - **Do NOT rename the app to "Rank Warz"** ("Rank Warz" is exclusively reserved for the 1v1 battle mini-game modes).

2. **Authoritative Character Specification**:
   - Refer to `character_spec/avatar_3d_generation_guide.md` for the 27 animal warrior avatars (Mantis Zerek through Stallion Pegasus). Never invent, delete, or rename avatar attributes or stats.

---

## 2. Active Architecture & State Machine

### A. Authentication & Session Strategy
- **Backend Host**: `https://medigyaan.com/Neurons/`
- **Auth Philosophy**:
  - The legacy backend authenticates requests via **`user_id` parameter passing** rather than Bearer JWT verification.
  - Sending `user_id=0` or leaving it unauthenticated causes server rejections (`"Invalid User ID"`, `"Invalid user"`, or `"Invalid credentials"`).
- **SessionStore Implementation** (`MediGyaan/Core/Auth/SessionStore.swift`):
  - Always keeps a valid fallback guest ID (`userId: 1`, `name: "Aspirant"`, `email: "student@medigyaan.com"`).
  - On fresh install or when unauthenticated, `restore()` automatically signs into the demo guest profile so users never see an "Invalid user" banner upon launching the IPA.
  - `SessionStore.userId` property clamps `id > 0 ? id : 1`.

### B. Outgoing Network Requirements (`HTTPClient.swift`)
Every HTTP request **MUST** contain these headers:
```http
X-App-Signature: EduLabsRTM_Secure_v1_2026
User-Agent: MediGyaan-iOS/4.0
Accept: application/json
```
If omitted, secured endpoints (like `api/fetch_posts.php`) return:
`{"success":false,"error":"Unauthorized Access"}`.

### C. Live Wire Formats Verified Against Production

| Script | Method | Encoding | Key Gotcha |
| :--- | :---: | :---: | :--- |
| `api/login.php` | `POST` | `application/json` | Reads `php://input`. Form-encoded data will fail with 400. |
| `dash_api.php` | `POST` | `application/x-www-form-urlencoded` | **Must be POST form data** (`user_id=X`). GET fails with "Invalid User ID". |
| `quiz_apiv2.php` | `POST` | `application/x-www-form-urlencoded` | **Must be POST form data** (`topic_id=X&user_id=X`). GET fails with "Invalid user". |
| `get_profilev1.php` | `GET` | Query parameters | Requires `user_id=X&viewer_id=X`. |
| `messenger_api.php` | `GET` / `POST` | Query (`fetch_messages=X&user_id=Y`) / Form (`receiver_id=X&user_id=Y&message=Z`) | Peer chat sync. |
| `sync_challenge_v16_authenticated.php` | `GET` | Query | Deprecated (returns 404). Android uses Firebase Realtime Database. Safe fallback returning `[]` is in place. |

---

## 3. Git & Deployment Operations

### How to Commit & Trigger Builds
1. Work is executed locally in `C:\Users\Shash\AndroidStudioProjects\ios_project\MediGyaan`.
2. Commit with conventional commit messages:
   ```bash
   git add -A
   git commit -m "feat/fix(...): description"
   ```
3. Push to the CI branch:
   ```bash
   git push tank main:ios-swiftui
   ```
4. Pushing to `tank main:ios-swiftui` triggers the GitHub Actions workflow in `The-Tank-Project`.
5. The workflow builds the iOS app, codesigns the `.ipa`, and uploads it to GitHub Release tag `v4.0-latest`.

### Verification Commands (PowerShell / Windows CMD)
- **Check Workflow Status**:
  ```powershell
  Invoke-RestMethod -Uri 'https://api.github.com/repos/shashiguptaazm-droid/The-Tank-Project/actions/runs?per_page=3' | Select-Object -ExpandProperty workflow_runs | Select-Object id, run_number, status, conclusion, html_url
  ```
- **Check Release Asset Timestamp**:
  ```powershell
  Invoke-RestMethod -Uri 'https://api.github.com/repos/shashiguptaazm-droid/The-Tank-Project/releases/tags/v4.0-latest' | Select-Object -ExpandProperty assets | Select-Object name, size, updated_at, browser_download_url
  ```

---

## 4. Work Completed vs. Work Remaining

### Work Completed:
- [x] Fixed "Invalid user" app-wide: `SessionStore.swift` auto-initializes guest demo session (`userId: 1`) on fresh install.
- [x] Fixed `quiz_apiv2.php` request method: switched from GET to POST form data.
- [x] Guarded against 404 on `sync_challenge_v16_authenticated.php`.
- [x] In-app `APILogger` & `NetworkInspectorView` created to capture live request/response data.
- [x] Indexed all 187 Android Kotlin `.kt` files to `C:\Users\Shash\OneDrive\Desktop\MediGyaan_Android_Kotlin_Files.txt`.
- [x] CI Run #30 passed; IPA updated on GitHub Releases `v4.0-latest`.

### Work Remaining for Next Coding Agent:
1. **Firebase Realtime Database for Live Battles**:
   - Android (`DashboardActivity.kt` & `SinglePlayer.kt` / `ChallengeListActivity.kt`) utilizes Firebase Realtime Database nodes (`challenges/`, `lobbies/`, `users/`) for match-making and 1v1 challenges.
   - iOS currently stubs live matchmaking. Implement Swift Firebase Database listeners for live multiplayer battles.
2. **Offline Data Persistence (SwiftData / SQLite)**:
   - Android caches question history locally (`HistoryManager.kt`, `DailyStatsManager.kt`).
   - Add local caching on iOS for offline practice questions and daily streak maintenance.
3. **StoreKit 2 Subscriptions**:
   - Port Android `PlayBillingManager.kt` to StoreKit 2 for MediGyaan Premium/Pro subscription tiers.
