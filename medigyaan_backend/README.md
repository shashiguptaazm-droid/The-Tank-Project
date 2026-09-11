# MediGyaan AI Chat — Search & Source-Citing Scripts (collected Sep 5, 2026)

Everything the AI Chat activity (`AiChatActivity.kt`) uses for **search** and **source citing**,
pulled from the live server (FTP `ftp.medigyaan.xyz` / `Owner@medigyaan.xyz`) on Sep 5, 2026.

> FTP mapping: FTP `/` == web `/Neurons/`, FTP `/api/` == web `/Neurons/api/`.
> `MANIFEST.txt` lists remote path + size ( `-1` = not found on this FTP account; local copy supplied where available ).

---

## 1. Question-bank search (the 280k NEET PG questions)

| File (local) | Remote / web URL | Purpose | Called from |
|---|---|---|---|
| `searchv2.php` | `/api/searchv2.php` → `medigyaan.xyz/Neurons/api/searchv2.php?keyword=...&type=json` | Full-text search over the question bank; used to show related questions after every AI reply (`[SEARCH: ...]` keyword) | `AiChatActivity.kt` → `findRelatedQuestions()` |
| `getQuestions.php` | `/api/getQuestions.php` | Fetch questions by filters (subject/topic) | app quiz modules |
| `getTopics.php` | `/api/getTopics.php` | List topics (by subject) | app quiz modules |
| `topicsearch.php` | `/api/topicsearch.php` | Topic search helper | app |
| `get_single_question.php` | `/api/get_single_question.php?question_id=` | Single question fetch | app |
| `getuserquizzes.php` | `/api/getuserquizzes.php` | User's quiz list | app |
| `getQuizBank.php` | `/api/getQuizBank.php` | Quiz bank metadata | app |
| `submitAnswerx1.php` | `/api/submitAnswerx1.php` | Answer submission / grading | app |
| `get_quiz_questions.php` | `/get_quiz_questions.php` | Quiz question fetch | app |
| `generate_questions_ai.php` | `/api/generate_questions_ai.php` | AI-generated questions (for topics with no questions) | app / backfill |

## 2. Thesis topics search (thesis catalog in the `thesis` table)

| File (local) | Remote / web URL | Purpose | Called from |
|---|---|---|---|
| `thesis_topics_search.php` | `/thesis_topics_search.php` → `medigyaan.xyz/Neurons/thesis_topics_search.php?q=...&limit=15&user_id=` | Searches the thesis catalog (subject/topic/PDF). Patched for multi-word search (word-boundary splitting) so "typhoid fever" / "glaucoma surgery" no longer return 0 | `AiChatActivity.kt` → `fetchThesisTopics()` |
| `thesis_import.php` | `/api/thesis_import.php` | Bulk import of thesis rows (dedupe by PDF / first-120-chars); supports `?file=<name>.json` GET trigger + `X-App-Signature` header to bypass the WAF POST ban | backfill tooling |
| `backfill_rows.json` | (data) | 336 papers collected from PubMed/PMC/OpenAlex/Semantic Scholar across 37 topics — already imported into `thesis` | — |

## 3. Source citing / citation maintenance

| File (local) | Remote / web URL | Purpose | Called from |
|---|---|---|---|
| `PubMedCitationValidator.kt` (app_side) | in-app | PubMed ESCI/PMID validation of reference lists pasted in chat ("Validate these references:"), ELink similar-article pulls | `AiChatActivity.kt` → `runCitationValidation()` |
| `validate_references.php` | `/validate_references.php` | Server-side reference validation helper | older web flow |
| `update_question_explanation.php` | `/api/update_question_explanation.php` | Fills/updates question explanations (<100 chars get rewritten via AI) | `AiChatActivity.kt` (citation enrichment), backfill |
| `update_question_topic.php` | `/api/update_question_topic.php` | AI assigns/updates question topic when missing/null | `AiChatActivity.kt`, topic backfill |
| `ai_training_log.php` | `/ai_training_log.php` | Persists every AI exchange (prompt→response) used for training/debug | `AiTrainingLogger` |
| `ask_ai2.php` | `/ask_ai2.php` | General AI answer endpoint (legacy) | older flows |

## 4. AI keys / utilities

| File (local) | Purpose |
|---|---|
| `config.php` | DB connection (sets global `$conn`) — all live `/api/` endpoints require it |
| `zz_ai_keys_pool.php` | AI key pool used by backfill drivers |
| `zz_fix_empty_topics.php` | Driver: fix empty topic rows across the question bank |
| `zz_repair_eopts.php` | Driver: repair NEET PG image-challenge rows missing option E |
| `zz_add_option_e.php` | Adds the option_e column / rows |
| `zz_topic_batch.php`, `zz_topic_save.php` | Topic classification batch/save drivers |
| `zz_dbg_poster.php`, `zz_cleanup_smoke.php` | Debug/smoke helpers |
| `poster_credits.php` | 5-free-posters quota per user (check/consume/add) |
| `get_topics.php` | (root copy not found on this FTP account — app calls `/Neurons/get_topics.php`; `/api/getTopics.php` is the available copy) |

## 5. App-side files (`app_side/`)

| File | Role |
|---|---|
| `AiChatActivity.kt` | The whole AI Chat: chat, `[SEARCH:]` keyword → `searchv2`, thesis topics search, PubMed citation validation, poster generation, **chapter generation** (schemas/figures/charts/tables), JSON session log (`ChatLog`) |
| `PubMedCitationValidator.kt` | PubMed validation + ELink evidence used for citing |
| `ModelRotator.kt` | Provider/model rotation pool (groq/openrouter/deepseek/mistral/cerebras) |
| `ApiClient.kt` | Retrofit clients + raw OkHttp for image generation |
| `AiService.kt` | Chat/completions API definitions |
| `AiRichText.kt` | Bold/markdown renderer used in chat cards |

---

## Debugging: pull the AI Chat session log

Every user input and every AI reply is written as one JSON line to
`files/chat_logs/chat_log.jsonl` inside the app (mirrored to logcat tag `ChatLog`):

```bash
adb exec-out run-as com.corp.medigyaan cat files/chat_logs/chat_log.jsonl > chat_log.jsonl
```

Chapter generation adds `chapter_request` entries with the **full prompt + schema + raw LLM JSON reply**
(and `chapter` outcome / `chapter_error` entries), so failures are visible end-to-end.