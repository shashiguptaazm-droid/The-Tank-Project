# Cleanup and Fix for AiChatActivity Duplication

The `AiChatActivity.kt` file currently contains a massive amount of duplicated code, redeclared data classes, and invalid local function definitions. This is causing build failures and potential logic errors.

## User Review Required

> [!IMPORTANT]
> The file `AiChatActivity.kt` has been tripled or quadrupled in size due to duplicated blocks. I will perform a significant cleanup to remove these duplicates.

## Proposed Changes

### [AiChatActivity.kt](file:///C:/Users/Shash/AndroidStudioProjects/MediGyaan/app/src/main/java/com/rankwarz/edulabsrtm/AiChatActivity.kt)

#### [MODIFY]
- Remove redundant data class definitions that are already in `PosterTypes.kt` (`PosterGenState`, `PosterAnalysisData`, `PosterSectionData`, `SavedPoster`).
- Fix visibility of `ChatTableJson`, `ChatFigureJson`, and `ChatChartJson` by removing `internal` to avoid exposure errors in public functions.
- Move logic functions (`detectPosterAbstract`, `detectChapterRequest`, `detectCitationList`, `detectThesisTopicSearch`) out of the `send()` local scope and into the top-level or class-level scope to fix "Modifier 'private' is not applicable to 'local function'" errors.
- Delete the massive duplicated block of code at the end of the file (lines ~3491 to the end).
- Consolidate common helper functions like `parseAttachment` and `fetchPosterQuota` to remove conflicting overloads.

### [ThesisArtBridge.kt](file:///C:/Users/Shash/AndroidStudioProjects/MediGyaan/app/src/main/java/com/rankwarz/edulabsrtm/ThesisArtBridge.kt)

#### [MODIFY]
- Update references to data classes that were moved or made public.
- Fix unresolved references caused by the cleanup in `AiChatActivity.kt`.

## Verification Plan

### Automated Tests
- Run `./gradlew assembleDebug` to ensure the project compiles successfully.

### Manual Verification
- Deploy the app to a device.
- Open AI Chat.
- Verify "Chat with PDF" and "Chapter Generation" work as expected.
- Verify PubMed reference validation works.
