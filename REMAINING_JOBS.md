=============================================================
MEDIAGYAAN — DETAILED REMAINING JOBS LIST
=============================================================
Project: MediGyaan Android app (com.corp.medigyaan)
Device: Samsung Z Flip 6 SM-F741B (adb: RZCXB2A2VFH)
FTP: ftp.medigyaan.xyz (Owner@medigyaan.xyz / MeriMaa007)
VPS: root@100.71.127.156 (Tailscale) / 213.199.61.156
API: https://medigyaan.xyz/Neurons/api/
DB: 348 MB SQL file on VPS (read-only via SSH)
=============================================================

IMPORTANT RULES (from Notes_260907_212558.txt):
  • Interpret each paragraph ONLY, not by page/separation.
  • Make a FILE BACKUP before every edit.
  • Log every step taken in the log file each turn.
  • Test each paragraph fully before moving to the next.
  • Never derive data — ask the user for credentials/IDs.
  • FTP blocks IPs after too many requests — use VPS as fallback.

=============================================================
SECTION A — ALREADY COMPLETED (do NOT redo)
=============================================================
Para 6    Global search + community posts search skill
Para 7    Custom Mode Battle Card for topic selection (just added)
Para 12   Skills stored in session for text chat
Para 16   Custom room activity topic selection
Para 20   AI chat database inspection
Para 24   AI enhanced explanation saved to DB
Para 26   AI predicted rank saved to server DB
Para 28   Classic bot challenge in history tab
Para 30   VPS upload failure diagnosis
Para 32   Tick + double tick for messages
Para 34   Copy button on click for long messages
Para 36   AI predicted rank in Profile activity
Para 38  Messenger document interpretation (PPT/Word/PDF)
Para 40  Online status + block button in Messenger
Para 42  SettingsActivity WhatsApp-like design + Earn section
Para 43  Widget settings gallery of images
Para 45  TestMode unique ID flow via TestSelectionActivity
Para 46  Google Play referral link in ReferralActivity
Para 47  Referral PHP share.php upgrade (logo + dark theme)
Para 48  Badge emoji overlap removed
Para 49  Survival Mode (increasing XP, random 15 uncategorized)
Para 50-55 Streak mode (5/10/25 bonuses)
Para 56-65 King of the Topic (topic selection, >200 check)
Para 66-75 Today's Challenge (10 Q, 10 min, dashboard)
Para 76-80 AI Chat PDF Parsing upgrade (PubMed validation)
Para 81-85 Community posts table requirements
Para 86-87 Messenger @mention AI
Para 88-89 Rank badge progress circle on dashboard
Para 90-92 Subject Survival Mode
Para 93-95 Subject Test Mode via ExamPDF.php
Para 96-98 Poster Generation Based On Abstract skill
Para 99  Dark/Light Theme in selection activity
Para 100 Lobby Activity profile image + name
Para 101-107 Loading Screen for Single Players
Para 108-109 Bottom bar visible on all screens
Para 110 Rank progress bar placement
Para 111-113 GIF images on dashboard (good evening + profile card)
Para 114 Text with icons on dashboard
Para 115-117 User videos search in GlobalSearchActivity
Para 118 Distinct topics duplicates fix
Para 119-121 Global Search topic search within subject
Para 122-127 Thesis DB restore from backup
Para 135-139 Document interpretation + export in AI chat/Messenger
Para 140-141 VPS scripts (view_pdf, convert_doc, stream_video, upload, health)

=============================================================
SECTION B — REMAINING PARAGRAPHS (TODO IN ORDER)
=============================================================

======================================================================
JOB 1 — Para 8/17/18: Test Mode Battle Card → TestSelectionActivity
======================================================================
WHAT:
  The "Test Mode" battle card on the dashboard currently opens
  SinglePlayerTestModeActivity directly with UniqueId=1. It should
  instead open TestSelectionActivity so the user can pick a test series
  unique ID, which is then passed to SinglePlayerTestModeActivity.

WHY:
  Para 8: "Test Mode in dashboard doesnt Open test selection activity
  for selection of unique id"
  Para 18: "TEST mode Battle Card Must open test selection activity
  to pass Test Series UNiQue Id"

HOW:
  1. Backup DashboardActivity.kt
  2. In setupBattleModeCards(), find cardPracticeMode click listener.
     Verify it opens TestSelectionActivity with MODE=TEST.
     If it opens SinglePlayerTestModeActivity directly, change it.
  3. In TestSelectionActivity, verify flow: user picks test →
     uniqueId passed to SinglePlayerTestModeActivity via openSoloMode().
  4. Test: tap Test Mode card → TestSelectionActivity opens → pick test →
     SinglePlayerTestModeActivity opens with correct unique ID.

FILES: DashboardActivity.kt, TestSelectionActivty.kt, SinglePlayer.kt

======================================================================
JOB 2 — Para 11: Dropdown Attempted Questions Color Bug
======================================================================
WHAT:
  In MCQ Activity dropdown, already attempted questions show as RED
  instead of GREEN. Also, when the latest question is attempted,
  ticks appear during the current session but next session marks
  them red again.

WHY:
  Para 11: "In MCQ Activity dropdown the already attempted questions
  Are Not Showed As Green But Red and At Last When I attempt The Latest
  available questions it starts showing tick with question But This
  Happens Only During The Current Session And Next Considers Them Red Again"

HOW:
  1. Backup MCQActivity.kt and dropdown layout
  2. Find where dropdown items are colored — check if attempted
     questions are marked red instead of green
  3. Fix the color logic: attempted+correct = green, attempted+wrong = red
  4. Fix the persistence issue: ensure answered questions are saved
     to SharedPreferences/DB immediately, not just in-memory
  5. Verify: answer a question → close app → reopen → dropdown shows
     correct color

FILES: MCQActivity.kt, dropdown XML layout, MCQ_ANSWERS prefs

======================================================================
JOB 3 — Para 13: Skills Persisted in Session (AI Chat)
======================================================================
WHAT:
  When AI chat uses a skill/module (PubMed validation, poster generation,
  thesis research), the skill state and output should be saved to
  SharedPreferences so reopening the chat shows the skill results.

WHY:
  Para 12/13: "Skills When worked should Be Stored In session Too Not
  Only Text chat But Make Sure Save These Too..."

HOW:
  1. Backup AiChatActivity.kt
  2. Identify all skill invocations (routeToSkill, posterGen, thesisSearch,
     counselSearch, chapterGen, etc.)
  3. After each skill completes, save skill name + output to SharedPreferences
     with key "skill_<skillName>_<timestamp>"
  4. On AiChatActivity.onCreate(), load saved skills and restore to UI
  5. Test: use a skill → close app → reopen → skill output still visible

FILES: AiChatActivity.kt

======================================================================
JOB 4 — Para 14: Line Charts With Pinning for Accuracy Chart
======================================================================
WHAT:
  Redesign Accuracy Chart (AccuracyActivity) to use line charts with
  pinning support. Show accuracy over time with pin-able data points.

HOW:
  1. Backup AccuracyActivity.kt and its layout
  2. Add MPAndroidChart LineChart dependency (already in build.gradle)
  3. Replace current chart with LineChart
  4. Implement data entries from AccuracyHistoryManager
  5. Add long-press/pinch zoom + marker view for pinned points
  6. Style: dark theme, gradient fill, custom markers
  7. Test: chart renders, data correct, pinning works

FILES: AccuracyActivity.kt, AccuracyHistoryManager.kt, accuracy_activity.xml

======================================================================
JOB 5 — Para 16: Custom Room Activity Topic Selection
======================================================================
WHAT:
  TopicChallengeSelectionActivity doesn't allow users to select a topic
  when creating a custom room for inviting users. Fix to allow topic selection.

HOW:
  1. Backup TopicChallengeSelectionActivity.kt and its layout
  2. Add topic selector (ComposeView or Spinner) showing topics for
     selected subject
  3. When user selects topic, store in intent extras
  4. Pass topic to challenge/lobby creation
  5. Test: create custom room → verify topic selected and passed

FILES: TopicChallengeSelectionActivity.kt, topic_challenge_selection.xml

======================================================================
JOB 6 — Para 22/23: AI Chat Reply Search Validation + Google Search
======================================================================
WHAT:
  AI chat says "I can't search questions" but the skill search was
  triggered and completed with a chat message — oxymoron. Fix so AI
  can search Google when needed.

HOW:
  1. Backup AiChatActivity.kt
  2. Find where AI reply is generated after skill search
  3. Ensure AI reply includes search results properly
  4. Fix AI prompt/response handling so it doesn't say "I can't search"
     when search module has completed
  5. Test: trigger skill search → AI reply includes results, no "can't search"

FILES: AiChatActivity.kt

======================================================================
JOB 7 — Para 25: AI Enhanced Explanation Saved to DB
======================================================================
WHAT:
  MCQ Activity doesn't have a condition to generate AI enhanced
  explanation which should be saved over the database as explanation
  and updating its current explanation.

HOW:
  1. Backup MCQActivity.kt
  2. Find where question explanations are handled
  3. Add AI enhanced explanation generation after user answers
  4. Save the enhanced explanation to the database for that question
  5. Update current explanation with the AI enhanced one
  6. Test: answer a question → verify AI enhanced explanation saved

FILES: MCQActivity.kt, question database

======================================================================
JOB 8 — Para 27: AI Predicted Rank Saved to Server DB
======================================================================
WHAT:
  AI Predicted Rank on Dashboard has data but resets at logout.
  Should be saved to server database for complete user record.

HOW:
  1. Backup DashboardActivity.kt
  2. Verify predicted rank is being saved to server API
  3. Check api_save_predicted_rank.php exists and works
  4. Ensure predicted rank data is loaded from server on login
  5. Test: logout → login → predicted rank still shows

FILES: DashboardActivity.kt, predicted rank PHP APIs

======================================================================
JOB 9 — Para 28: Ranked Quiz Challenge in History Tab
======================================================================
WHAT:
  Classic bot challenge in recent challenges (history tab) should be
  moved to "challenge" tab and named "Ranked Quiz Challenge". Cards
  show XP gained, correct/total, review data on click. Data saved to server.

HOW:
  1. Backup RecentChallengesActivity.kt, ChallengeListActivity.kt, layouts
  2. Find where classic bot challenges are stored/displayed
  3. Move from history tab to challenge tab
  4. Rename to "Ranked Quiz Challenge"
  5. Add XP gained, correct/total on each card
  6. Add review data on card click (detailed results)
  7. Ensure data loaded from and saved to server
  8. Test: create ranked quiz challenge → verify in challenge tab

FILES: RecentChallengesActivity.kt, ChallengeListActivity.kt,
       ChallengeAdapter.kt, challenge_list.xml, recent_challenges.xml

======================================================================
JOB 10 — Para 30: VPS Upload Fix for Large Attachments
======================================================================
WHAT:
  VPS uploads failing when large attachments sent in MessengerActivity.
  Diagnose and fix. Test with large file.

HOW:
  1. SSH to VPS (root@100.71.127.156 via Tailscale or 213.199.61.156)
  2. Check upload logs: tail -f /var/log/nginx/error.log
  3. Check PHP upload limits: php.ini upload_max_filesize, post_max_size
  4. Check disk space: df -h
  5. Check VPS RAM/swap: free -m
  6. Test upload from MessengerActivity with large file (>2MB)
  7. Fix: increase PHP limits, add VPS upload fallback, proper error handling
  8. Test: upload 10MB+ file → verify success

FILES: MessengerActivity.kt, VPS PHP upload handler, php.ini

======================================================================
JOB 11 — Para 33: Community Posts Table Requirements
======================================================================
WHAT:
  Understand Users community posts table requirements and use them
  inside AI chat activity with new skill-based search for questions on topics.
  LLM should see NEET PG topics inside MCQ activity for selection.

HOW:
  1. Backup AiChatActivity.kt
  2. Check community posts database table structure
  3. Add new skill in AI chat for community post search
  4. Ensure LLM can see NEET PG topics from MCQ activity
  5. Show topics to LLM for selection when user searches
  6. Test: search community posts → results appear in chat

FILES: AiChatActivity.kt, community posts PHP API

======================================================================
JOB 12 — Para 34: Messenger @mention AI UI
======================================================================
WHAT:
  Messenger @mention AI works but UI must match WhatsApp Meta AI usage.
  AI reply should look identical to user messages. Thinking/showing state
  and model skills UI should match AI chat activity design.

HOW:
  1. Backup MessengerActivity.kt and message layouts
  2. Compare AI message UI with user message UI in Messenger
  3. Make AI messages visually identical to user messages
  4. Add thinking indicator (typing animation) for AI replies
  5. Add model skills display UI (same as AI chat activity)
  6. Test: send @medigyaanAI message → UI matches user messages

FILES: MessengerActivity.kt, MessageAdapter.kt, item_message_received.xml

======================================================================
JOB 13 — Para 38: Messenger Document Interpretation Full UI
======================================================================
WHAT:
  Check MessengerActivity for document interpretation. All known document
  formats (PPT, Word, PDF) must be interpreted correctly with proper UI.
  Documents uploaded must show properly with document loaded UI.
  PDF viewer and uploads rendered via VPS only. Each works inside chat.
  Messages can be deleted like WhatsApp. Docs can be sent to AI chat
  activity with "Ask With Medigyaan AI" button.

HOW:
  1. Backup MessengerActivity.kt, MessageAdapter.kt, related layouts
  2. Verify all document format interpretations work (PPT/Word/PDF)
  3. Fix UI for each document type when uploaded
  4. Ensure PDF viewer uses VPS rendering
  5. Verify messages can be deleted
  6. Verify "Ask With Medigyaan AI" button for docs works
  7. Test each document type end-to-end

FILES: MessengerActivity.kt, MessageAdapter.kt, VPS PHP handlers

======================================================================
JOB 14 — Para 40: Online Status + Block Button in Messenger
======================================================================
WHAT:
  Add online status for users in Messenger top bar. Add block button
  to block user. If API doesn't exist, create PHP and upload to FTP.

HOW:
  1. Backup MessengerActivity.kt and layouts
  2. Check if online status API exists on server
  3. If not, create PHP API for online status + block user
  4. Upload PHP to FTP server root/api/
  5. Add online status indicator in Messenger top bar
  6. Add block button functionality
  7. Test: online status shows, block button works

FILES: MessengerActivity.kt, FTP PHP files

======================================================================
JOB 15 — Para 43: Widget Settings Gallery + Professional Design
======================================================================
WHAT:
  Widget settings must have gallery of images for selection. User decides
  images. Separate "Add" button for own image. Function already exists
  but design must be professional.

HOW:
  1. Backup WidgetSettingsActivity.kt and its layout
  2. Add image gallery (GridLayout/RecyclerView) showing available images
  3. Add "Add" button to use own image from gallery/photos
  4. Make design professional (cards, proper spacing, dark theme)
  5. Test: select image from gallery → add own image → preview works

FILES: WidgetSettingsActivity.kt, widget_settings.xml

======================================================================
JOB 16 — Para 44: Referral PHP share.php Fix
======================================================================
WHAT:
  Load share.php from FTP, check functioning, upgrade with new logo
  and dark theme. Register should open Medigyaan Playstore link when
  clicked. Shareable WhatsApp should properly share the link.
  PHP errors shown to user — suppress them.

HOW:
  1. Download share.php from FTP server
  2. Read and understand current functionality
  3. Fix PHP errors shown to user (suppress error display)
  4. Add new logo to share.php output
  5. Add dark theme to share.php UI
  6. Make "Register" button open Google Play store link
  7. Make WhatsApp share button properly share the referral link
  8. Upload updated share.php to FTP
  9. Test: access share.php → verify no errors, logo, dark theme,
     register button, WhatsApp share

FILES: FTP share.php, ReferralActivity.kt

======================================================================
JOB 17 — Para 50: Bottom Nav Bar on All Screens
======================================================================
WHAT:
  Many screens have bottom bar but some are not visible. College
  predictor activity on dashboard — make sure bottom bar visible on
  ALL screens.

HOW:
  1. Backup all activity layouts
  2. Check each activity XML for BottomNavigationView
  3. Check PredictCollegeActivity specifically
  4. Add bottom navigation bar to any screen missing it
  5. Ensure bottom bar not overlapped by content (add padding)
  6. Test: navigate to each screen → bottom bar visible

FILES: All activity XML layouts, PredictCollegeActivity.kt,
       AppBottomNavigation.kt

======================================================================
JOB 18 — Para 51-53: Referral Link + share.php Upgrade
======================================================================
WHAT:
  Load PHP https://medigyaan.xyz/Neurons/share.php?question_id=840&ref=239
  From FTP, see functioning, upgrade with new logo + dark theme.
  Register opens Playstore link. WhatsApp shares properly.
  PHP errors suppressed.

(Same as JOB 16 above — combine implementation)

FILES: FTP share.php, ReferralActivity.kt

======================================================================
JOB 19 — Para 55: Badge Emoji Overlap Fix
======================================================================
WHAT:
  Badge emoji overlapping badge icons everywhere. Remove emoji overlap
  over badge icons on dashboard and all screens.

HOW:
  1. Backup DashboardActivity.kt and relevant layouts
  2. Find where badge emoji is drawn over badge icon
  3. Fix positioning — emoji should not overlap the badge icon
  4. Check all screens for same issue
  5. Test: badge icons display without emoji overlap

FILES: DashboardActivity.kt, activity_dashboard.xml, rank badge layouts

======================================================================
JOB 20 — Para 56-65: Streak Mode (5/10/25 Bonuses)
======================================================================
WHAT:
  Streak mode: Answer continuously. Correct → +1 streak. Wrong → reset.
  5 streak → bonus XP, 10 streak → bigger bonus, 25 streak → special badge.
  Goal: beat personal longest streak.

HOW:
  1. Verify streak logic exists in MCQActivity (check currentStreak, maxStreak)
  2. Verify 5/10/25 streak bonuses are implemented
  3. Verify badge unlock at 25 streak
  4. Ensure streak persists across sessions (saved to DB/server)
  5. Test: answer 5 correct → verify bonus, 10 correct → bigger bonus,
     25 correct → badge unlocked

FILES: MCQActivity.kt, streak PHP APIs, badge unlock logic

======================================================================
JOB 21 — Para 66-75: King of the Topic
======================================================================
WHAT:
  Pick one topic, keep answering until wrong. Record: questions survived.
  Compare with other students. Topic must have >200 questions to select.
  If topic exists but <200 questions, show "Not Enough Questions" overlay
  but topic name must be visible.

HOW:
  1. Verify King of the Topic card exists on dashboard (cardKingOfTopic)
  2. Verify topic selector shows only topics with >200 questions
  3. Verify "Not Enough Questions" overlay for <200 topics
  4. Verify record display (questions survived vs other students)
  5. Test: select topic → play → wrong answer → see results

FILES: DashboardActivity.kt, MCQActivity.kt, topic selector dialog

======================================================================
JOB 22 — Para 76-87: Today's Challenge Full Implementation
======================================================================
WHAT:
  Today's Challenge on dashboard — same for everyone, resets at 12:00 PM.
  Only uncategorized NEET PG questions from the pool. Collapsible, compact,
  clickable on dashboard. Scrollable to next question at dashboard.
  10 questions, 10 minutes. Review questions after completion.

HOW:
  1. Backup DashboardActivity.kt, activity_dashboard.xml, MCQActivity.kt
  2. Verify Today's Challenge card (cardTodayChallenge) exists
  3. Make collapsible (expandable/collapsible CardView)
  4. Add scrollable question view within dashboard
  5. Ensure 10 questions, 10 min timer, reset at 12 PM
  6. Add review functionality after completion
  7. Ensure only uncategorized NEET PG questions used
  8. Test: start challenge → complete → review questions

FILES: DashboardActivity.kt, activity_dashboard.xml, MCQActivity.kt

======================================================================
JOB 23 — Para 88-100: AI Chat PDF Parsing Upgrade (PubMed Validation)
======================================================================
WHAT:
  AI chat PDF parsing upgrade: validate references via PubMed validation,
  download abstracts from validated references, update variables with only
  validated references, download similar articles list, download abstracts
  from similar articles, show progress for each step, generate Literature
  Review and Discussion chapters. All operations collapsible with proper UI.
  LLM initiates but cannot decide citation validity — Thesis View Model
  decides. Multi-source upgrade: PubMed + OpenAlex + other sources.
  Each reference has PMID, citation, validation status, abstract, similar articles.

HOW:
  1. Backup ThesisArtBridge.kt, AiChatActivity.kt, PubMedCitationValidator.kt
  2. Verify PDF parsing flow in AiChatActivity
  3. Ensure PubMed validation called for each reference
  4. Add PMID and citation correction from PubMed
  5. Download abstracts for all validated references
  6. Find similar articles from PubMed/OpenAlex
  7. Download abstracts from similar articles
  8. Merge all abstracts
  9. Generate Literature Review from downloaded abstracts
  10. Generate Discussion Chapter
  11. Show progress for each step with collapsible UI
  12. Add "Not Enough Questions" overlay for topics <200
  13. Test: upload PDF → verify each step completes correctly

FILES: ThesisArtBridge.kt, AiChatActivity.kt, PubMedCitationValidator.kt,
       thesis_view_model files

======================================================================
JOB 24 — Para 101-110: Rank Badge Progress Circle + Subject Survival Mode
======================================================================
WHAT:
  Replace simple badge icon on dashboard with rank badge icon showing
  activity with progress in circle. Add Subject Survival Mode battle card
  where users select topic from NEET PG distinct topics in MCQ activity,
  then get 15 random questions from that subject.

HOW:
  1. Backup DashboardActivity.kt, MCQActivity.kt, activity_dashboard.xml
  2. Replace badge icon with circular progress indicator showing rank badge
  3. Add "Subject Survival" card to dashboard battle modes
  4. When clicked, show topic selector for current subject
  5. Launch MCQActivity with MODE="SUBJECT_SURVIVAL" and selected topic
  6. In MCQActivity, handle SUBJECT_SURVIVAL mode: load 15 random questions
  7. Add new icon for the card
  8. Test: select subject survival → pick topic → play 15 questions

FILES: DashboardActivity.kt, MCQActivity.kt, activity_dashboard.xml

======================================================================
JOB 25 — Para 111-120: Subject Test Mode + Poster Generation + Theme Fix
======================================================================
WHAT:
  Subject Test Mode like TestSelectionActivity but passes unique ID for
  subject-specific test series using ExamPDF.php. Make 50 test series with
  200 questions per topic. Wire new app logo to PDF generation script.
  Clickable chips for each module/skill in AI chat.
  Poster Generation: AI chat auto-fulfills required fields for poster
  generation by LLM before sending to skill. Reuse poster analysis activity.
  Dark/Light Theme fix in selection activity (dark theme with dark text).

HOW:
  1. Backup TestSelectionActivty.kt, DashboardActivity.kt, AiChatActivity.kt,
     PosterAnalysisActivity.kt, GoalActivity.kt
  2. Download and read ExamPDF.php from FTP
  3. Create SubjectTestMode using ExamPDF.php pattern for subject-specific tests
  4. Generate 50 test series with 200 questions per topic via script
  5. Wire new app logo to PDF generation script
  6. Add clickable chips for modules/skills in AI chat
  7. Fix dark theme in GoalActivity/selection activity
  8. Implement poster auto-fulfill in AiChatActivity
  9. Test each feature end-to-end

FILES: TestSelectionActivty.kt, DashboardActivity.kt, AiChatActivity.kt,
       PosterAnalysisActivity.kt, GoalActivity.kt, ExamPDF.php (FTP)

======================================================================
JOB 26 — Para 121-130: Lobby Profile + Loading Screen + Bottom Bar
======================================================================
WHAT:
  Lobby Activity: users profile image shown with name. Loading Screen for
  Single Players: same PVP screen but only player's side loaded (opponent
  empty). TWO XML layouts. Add animations and dynamic messages:
  "Preparing your battle... ⚔️", "Loading today's questions...",
  "Finding your challenge...", "Sharpening your brain... 🧠", "Battle Ready! 🔥".
  Bottom bar visible on ALL screens including College predictor.

HOW:
  1. Backup LobbyActivity.kt, LobbyPlayerAdapter.kt, LoadingActivity.kt,
     MatchmakingLoadingActivity.kt, and their layouts
  2. Add profile image (ShapeableImageView) + name to lobby player item
  3. Create activity_loading_single.xml layout
  4. Add animations (fade in, slide up) for loading screen
  5. Add dynamic messages cycling through the list
  6. Add bottom navigation to College predictor activity
  7. Test: lobby shows profile images, loading screen works, bottom bar visible

FILES: LobbyActivity.kt, LobbyPlayerAdapter.kt, LoadingActivity.kt,
       MatchmakingLoadingActivity.kt, PredictCollegeActivity.kt,
       lobby_activity.xml, item_lobby_player.xml, activity_loading.xml,
       activity_loading_single.xml (new)

======================================================================
JOB 27 — Para 131-140: GIF Images + Text with Icons + User Videos Search
======================================================================
WHAT:
  Two GIF images on dashboard (good evening + profile card) — don't ruin design.
  Text with icons on dashboard — some icons don't have visible text.
  User videos search in GlobalSearchActivity — load videos with proper script,
  users can comment. Same for posts in Global Search.

HOW:
  1. Backup DashboardActivity.kt, activity_dashboard.xml, GlobalSearchActivity.kt
  2. Verify GIF images display correctly without overlapping
  3. Fix text with icons — ensure all icons have visible text labels
  4. Implement user videos search in GlobalSearchActivity
  5. Load videos with proper PHP script from FTP
  6. Add comment functionality for videos and posts
  7. Test: dashboard GIFs visible, text+icons readable, videos searchable

FILES: DashboardActivity.kt, activity_dashboard.xml, GlobalSearchActivity.kt,
       FTP PHP scripts for videos/posts

======================================================================
JOB 28 — Para 141-150: Distinct Topics Fix + Topic Search + Thesis DB Restore
======================================================================
WHAT:
  Incorrect distinct topics in database — filter by NEET PG and NEET UG only.
  Fix duplicates in distinct topic list. Global search topic search within
  chosen subject. Thesis DB restore from backup + anti-destruction measures.

HOW:
  1. SSH to VPS, query database for distinct topics
  2. Identify duplicates and incorrect entries
  3. Fix duplicates in database
  4. Verify app topic list shows correct distinct topics
  5. Verify global search topic search within chosen subject
  6. Backup thesis database, restore from old backup
  7. Find destructive APIs, add safety conditions
  8. Add logging for thesis data modifications
  9. Test: topics correct, search works, thesis data restored

FILES: VPS database, GlobalSearchActivity.kt, thesis PHP APIs

======================================================================
JOB 29 — Para 151-160: FTP Endpoints + Humanize AI Chat Skills
======================================================================
WHAT:
  Check all useful FTP endpoints for different screens and connections.
  Check every skill made during project and humanize input so real-time
  user AI chat activity tests occur naturally.

HOW:
  1. Connect to FTP server, list all PHP files in root and api/ folder
  2. Document each endpoint and what it does
  3. Verify each endpoint works correctly
  4. List all skills/modules in AiChatActivity (routeToSkill)
  5. For each skill, review input prompts — make more natural/human-like
  6. Ensure AI chat flows naturally when users trigger skills
  7. Test each skill in real-time chat

FILES: FTP server PHP files, AiChatActivity.kt

======================================================================
JOB 30 — Para 161-170: Export Buttons + Chapter Generation + VPS Scripts
======================================================================
WHAT:
  Every AI reply in AI chat and Messenger has buttons: copy, PDF, Word,
  PowerPoint, Word document. Test all document interpretations.
  Generate chapter from thesis PDF variables — must work correctly.
  Test series generation in AI chat must have export PDF generated by
  ExamPdf PHP, viewed via VPS.
  VPS scripts for viewing PDFs inside app, viewing videos, viewing large
  documents, fallback if VPS fails.

HOW:
  1. Backup AiChatActivity.kt, MessengerActivity.kt, AiChatExporter.kt,
     ThesisArtBridge.kt, ExamPDF.php
  2. Verify copy/PDF/Word/PPTX buttons on every AI reply
  3. Test each export format
  4. Verify chapter generation from thesis PDF variables
  5. Verify test series export PDF works with ExamPdf.php
  6. Test VPS document viewing for large PDFs
  7. Create VPS independent API scripts with fallback mechanisms
  8. Test each VPS script independently
  9. Fix any issues found

FILES: AiChatActivity.kt, MessengerActivity.kt, AiChatExporter.kt,
       DocxExporter.kt, PdfExporter.kt, ExamPDF.php (FTP), VPS scripts

======================================================================
SECTION C — QUICK REFERENCE: KEY FILES
=============================================================
DashboardActivity.kt      - Battle modes, badge UI, today's challenge
MCQActivity.kt            - Question flow, survival, streak, king mode
TestSelectionActivty.kt   - Test series unique ID selection
AiChatActivity.kt         - AI chat, skills, PDF parsing, exports
ThesisArtBridge.kt        - PDF variable extraction, PubMed validation
MessengerActivity.kt      - Chat, @mention AI, document handling
GlobalSearchActivity.kt   - Search questions, users, posts, topics, videos
SettingsActivity.kt       - Settings UI (just updated)
LobbyActivity.kt          - Multiplayer lobby
SubjectTestActivity.kt    - Subject battle mode
LoadingActivity.kt        - Loading screen
MatchmakingLoadingActivity.kt - PVP loading screen
PredictCollegeActivity.kt - College predictor (check bottom bar)
PosterAnalysisActivity.kt - Poster generation
GoalActivity.kt           - Subject selection + dark theme fix
TopicChallengeSelectionActivity.kt - Custom room topic selection
ReferralActivity.kt       - Referral link + share.php
AccuracyActivity.kt       - Accuracy chart (line chart upgrade)
WidgetSettingsActivity.kt - Widget settings gallery

=============================================================
END OF TASK LIST
=============================================================
