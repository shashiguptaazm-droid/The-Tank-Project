package com.rankwarz.edulabsrtm

import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.util.Log
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.Verified
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilledIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.rankwarz.edulabsrtm.data.remote.ApiClient
import com.rankwarz.edulabsrtm.data.remote.ChatRequest
import com.rankwarz.edulabsrtm.data.remote.Message
import com.rankwarz.edulabsrtm.model.ModelCandidate
import com.rankwarz.edulabsrtm.model.ModelRotator
import com.rankwarz.edulabsrtm.model.PubMedCitationValidator
import com.rankwarz.edulabsrtm.model.Variable
import com.rankwarz.edulabsrtm.ui.theme.EduLabsRTMThemeFromPreferences
import com.rankwarz.edulabsrtm.utils.PdfTextExtractor
import com.rankwarz.edulabsrtm.utils.TextChunker
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.URLEncoder
import java.util.concurrent.TimeUnit

/**
 * Standalone general-purpose AI chat ("AI Chat" nav destination).
 *
 * Replies stream in with a ChatGPT-style typing effect, then the app searches the
 * 280k question bank for related questions (via Neurons searchv2 full-text search)
 * and lets the user jump straight into a practice test with those questions.
 */
class AiChatActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            EduLabsRTMThemeFromPreferences {
                AiChatScreen(onBack = { finish() })
            }
        }
    }
}

private data class ChatTurn(val role: String, val content: String)

private data class RelatedQuestion(
    val id: Int,
    val text: String,
    val subject: String,
    val topic: String,
    val explanation: String = ""
)

private data class QuestionSet(
    val keyword: String,
    val questions: List<RelatedQuestion>,
    val testIds: List<Int>,
    val primarySubject: String
)

/** A chat message's detectable reference list (as plain lines) plus its source intent. */
private data class DetectedReferences(
    val entries: List<PubMedCitationValidator.CitationEntry>,
    val explicitIntent: Boolean // user actually asked to validate / format references
)

private data class CitationValidationState(
    val ownerTurn: Int,           // index of the assistant turn this belongs to
    val detected: List<PubMedCitationValidator.CitationEntry>,
    val intentRequested: Boolean, // user asked for validation
    val running: Boolean = false,
    val note: String = "",        // status line shown while running
    val current: Int = 0,
    val total: Int = 0,
    val results: List<PubMedCitationValidator.ValidationResult>? = null
)

/** A thesis topic found in the catalog (thesis table) with its paper PDF. */
private data class ThesisTopicResult(
    val thesisId: Int,
    val subject: String,
    val snippet: String,
    val pdfUrl: String,
    val studyType: String,
    val difficulty: String
)

private data class ThesisSearchState(
    val ownerTurn: Int,
    val query: String,
    var running: Boolean = false,
    var note: String = "",
    var results: List<ThesisTopicResult>? = null
)

/** A community post matched to the current topic (caption search). */
private data class CommunityPostResult(
    val postId: Int,
    val author: String,
    val authorPhoto: String,
    val caption: String,
    val images: List<String>,
    val likes: Int,
    val uploadDate: String
)

private data class CommunityPostsState(
    val ownerTurn: Int,
    val keyword: String,
    var running: Boolean = false,
    var note: String = "",
    var results: List<CommunityPostResult>? = null
)

/** LLM-classified intent for a user message — drives which modules fire. */
private data class IntentDecision(
    val module: String,             // "poster" | "chapter" | "thesis_search" | "citation" | "chat"
    val chapterName: String = "",   // only for module="chapter"
    val thesisQuery: String = "",   // only for module="thesis_search"
    val keyword: String = "",       // search keyword for related questions + community posts
    val runChat: Boolean = true     // false = module handles reply; true = also send AI reply
)

private const val INTENT_CLASSIFICATION_SYSTEM =
    "You are an intent classifier for a medical AI chat app. " +
    "Given the user message and context flags, decide which module to activate. " +
    "Reply with ONLY valid JSON, no markdown fences:\n" +
    "{\"module\":\"<poster|chapter|thesis_search|citation|chat>\"," +
    "\"chapter_name\":\"<chapter name or empty>\"," +
    "\"thesis_query\":\"<2-4 word topic or empty>\"," +
    "\"keyword\":\"<2-4 word MCQ search phrase>\"," +
    "\"run_chat\":<true|false>}\n\n" +
    "Rules:\n" +
    "module=poster: user wants a medical conference poster (poster, infographic, visual summary, etc.)\n" +
    "module=chapter: user wants a thesis chapter (chapter, methodology, introduction, discussion, write for my thesis, etc.) — set chapter_name to the chapter name or 'methodology' if unclear\n" +
    "module=thesis_search: user is looking for thesis topics or research ideas\n" +
    "module=citation: user pasted references to validate OR asks to check/validate references\n" +
    "module=chat: everything else\n" +
    "run_chat=false for poster and chapter; run_chat=true for chat, thesis_search, citation\n" +
    "keyword: always set to best 2-4 word medical topic for MCQ search. Empty only if no medical topic.\n" +
    "Return ONLY valid JSON. No prose."

/** Poster generation flow: abstract -> structured poster data (free text LLM) -> AI poster image (OpenRouter image model). */
private data class PosterGenState(
    val ownerTurn: Int,
    val source: String = "",
    var phase: Int = 0,          // 1 analyzing abstract, 2 generating image, 3 done, 4 error
    var note: String = "",
    var data: PosterAnalysisData? = null,
    var imageUrl: String? = null,
    var imageFile: File? = null,
    var error: String = ""
)

private data class PosterAnalysisData(
    val title: String,
    val subtitle: String = "",
    val sections: List<PosterSectionData> = emptyList()
)

private data class PosterSectionData(val heading: String, val body: String)

// ---------------------------------------------------------------- Chapter generation (PDF -> thesis chapter)

/** Chapter generation from an uploaded PDF, mirroring the thesis analyzer's chapter schemas. */
private data class ChapterGenState(
    val ownerTurn: Int,
    val chapterName: String = "",
    var phase: Int = 0,          // 1 generating, 2 done, 3 error
    var note: String = "",
    var json: ChatChapterJson? = null,
    var error: String = ""
)

/** Parsed chapter payload. Keys mirror the thesis analyzer's chapter JSON schemas exactly. */
private data class ChatChapterJson(
    val chapterName: String = "",
    val chapterType: String = "",
    val sections: List<ChatSectionJson> = emptyList(),
    val tables: List<ChatTableJson> = emptyList(),
    val figures: List<ChatFigureJson> = emptyList(),
    val charts: List<ChatChartJson> = emptyList(),
    val abbreviations: List<ChatAbbreviationJson> = emptyList(),
    val references: List<ChatReferenceJson> = emptyList()
)

private data class ChatSectionJson(
    val heading: String = "",
    val content: String = "",
    val paragraphs: List<String> = emptyList(),
    val bullets: List<String> = emptyList(),
    val numberedPoints: List<String> = emptyList(),
    val subsections: List<ChatSubsectionJson> = emptyList(),
    val table: ChatTableJson? = null,
    val figures: List<ChatFigureJson> = emptyList(),
    val references: List<ChatReferenceJson> = emptyList()
)

private data class ChatSubsectionJson(val heading: String = "", val content: String = "", val paragraphs: List<String> = emptyList())

private data class ChatTableJson(
    val tableNumber: String = "",
    val title: String = "",
    val headers: List<String> = emptyList(),
    val rows: List<List<String>> = emptyList(),
    val footnote: String = ""
)

private data class ChatFigureJson(
    val figureNumber: String = "",
    val title: String = "",
    val caption: String = "",
    val imageSearchQuery: String = ""
)

private data class ChatChartJson(
    val chartId: String = "",
    val title: String = "",
    val type: String = "",          // bar | line | pie | column | doughnut
    val labels: List<String> = emptyList(),
    val values: List<Double> = emptyList(),
    val data: List<ChatChartPointJson> = emptyList()
)

private data class ChatChartPointJson(val label: String = "", val value: Double = 0.0)

private data class ChatAbbreviationJson(val short: String = "", val full: String = "")

private data class ChatReferenceJson(
    val citation: String = "",
    val referenceText: String = "",
    val pmid: String = "",
    val doi: String = ""
)

/** Context loaded from a user-uploaded PDF for Chat-with-PDF. */
private data class PdfChatContext(
    val fileName: String,
    val variables: List<Variable>,
    val textPreview: String
) {
    fun contextPrompt(): String {
        val sb = StringBuilder()
        if (variables.isNotEmpty()) {
            sb.append("You have access to a user-uploaded thesis PDF (\"").append(fileName).append("\"). Use the extracted variables below when answering.\n")
            val important = variables.filter { it.value.isNotBlank() }
            important.take(60).forEach { v ->
                val value = v.value.replace(Regex("\\s+"), " ").trim()
                sb.append("- ").append(v.name).append(": ").append(value.take(1200)).append("\n")
            }
        } else if (textPreview.isNotBlank()) {
            // Variable extraction failed — fall back to raw text preview so chapter/poster
            // generation still has something to work with.
            sb.append("You have access to a user-uploaded thesis PDF (\"").append(fileName)
                .append("\"). Variable extraction failed; use the raw text excerpt below.\n\n")
                .append(textPreview.take(3500))
        }
        return sb.toString().trim()
    }
}

private const val AI_CHAT_SYSTEM_PROMPT =
    "You are Medigyaan AI, a friendly medical exam assistant helping NEET PG aspirants. " +
        "Answer clearly and concisely in plain text (no markdown tables). Use short paragraphs or " +
        "bullets when helpful. If the question is outside medicine, still answer briefly and helpfully.\n\n" +
        "IMPORTANT: end your reply with a line exactly in this format: [SEARCH: keyword]\n" +
        "where keyword is the best 2-4 word medical search phrase that would find related exam " +
        "MCQ questions in a question bank (for example [SEARCH: typhoid fever] or [SEARCH: vitamin b12 deficiency]). " +
        "Do not include that marker anywhere else."

private val SEARCH_STOP_WORDS = setOf(
    "a", "an", "the", "of", "for", "with", "what", "why", "how", "is", "are", "was", "were",
    "me", "my", "this", "that", "these", "those", "please", "explain", "about", "tell", "give",
    "question", "questions", "and", "or", "in", "on", "to", "from", "can", "could", "would",
    "should", "does", "do", "did", "it", "its", "i", "you", "your", "he", "she", "they", "help",
    "me", "some", "any", "related", "disease", "condition", "diagnosis", "treatment", "treatments",
    "symptoms", "symptom", "therapy", "therapies", "management", "medicine", "medicines", "drug",
    "drugs", "clinical", "feature", "features", "patient", "patients", "cause", "causes", "effect",
    "effects", "describe", "definition", "define", "meaning", "differential", "findings", "find", "get"
)

// ---------------------------------------------------------------- Poster generation (abstract -> poster image)

/** Only free text models are used for the poster analysis step. */
private val FALLBACK_FREE_OR_MODELS = listOf(
    "z-ai/glm-5.2:free",
    "minimax/minimax-m3:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "google/gemma-4-31b-it:free",
    "thinkingmachines/inkling:free",
    "openrouter/free",
    "meta-llama/llama-3-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free"
)

private val GROQ_FREE_MODELS = listOf("llama-3.3-70b-versatile", "llama-3.1-8b-instant")

/** Cheapest OpenRouter image model (~₹3 per 1024x1024 poster). */
private const val POSTER_IMAGE_MODEL = "google/gemini-3.1-flash-lite-image"
private const val POSTER_IMAGE_SIZE = "1024x1024"
private const val POSTER_FREE_LIMIT = 5

private const val POSTER_ANALYSIS_SYSTEM =
    "You are an expert medical conference poster designer. From the given abstract, build the COMPLETE poster content as a single JSON object. " +
        "Rules: use ONLY information present in the abstract (never invent numbers, results or citations; if a section has no abstract data write \"Not stated in the abstract\"). " +
        "Return ONLY valid JSON, no markdown fences, exactly this structure: " +
        "{\"title\":\"<concise poster title>\",\"subtitle\":\"<1 short line, e.g. authors/institution or focus>\",\"sections\":[{\"heading\":\"<heading>\",\"body\":\"<poster-ready concise text>\"}]}. " +
        "Create 6-9 sections chosen from: Background/Introduction, Aim & Objectives, Methods/Materials, Results/Key Findings, Conclusion, Take-home Points, Clinical Significance, References. " +
        "Keep every body under 500 characters, poster-ready and concise. Escape quotes properly."

private val POSTER_COMMAND_PREFIX = Regex(
    """(?i)^(please\s+)?(generate|make|create|design|build|prepare|draft|write)\s+(me\s+)?(an?\s+)?(ai\s+|research\s+|medical\s+|conference\s+)?poster\s+(from|for|based\s+on|using|of)\s+(this\s+)?(the\s+)?(following\s+)?(abstract|text|content|information)?\s*[:.\n-]*"""
)

@Composable
private fun AiChatScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val listState = rememberLazyListState()

    var turns by remember { mutableStateOf(listOf<ChatTurn>()) }
    var input by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var streamingText by remember { mutableStateOf<String?>(null) }

    // Chat-with-PDF: uploaded document context + extraction state
    var pdfContext by remember { mutableStateOf<PdfChatContext?>(null) }
    var pdfExtracting by remember { mutableStateOf(false) }
    var pdfExtractNote by remember { mutableStateOf("") }

    // Thesis topics module state
    var thesisSearch by remember { mutableStateOf<ThesisSearchState?>(null) }

    // Related-question search state (only shown after the assistant turn that produced it)
    var searchPhase by remember { mutableStateOf(0) } // 0 idle, 1 searching, 2 done, 3 none
    var questionSet by remember { mutableStateOf<QuestionSet?>(null) }
    var suggestionOwner by remember { mutableStateOf(-1) } // index of assistant turn owning suggestions
    var enriching by remember { mutableStateOf(false) }
    var enrichmentNote by remember { mutableStateOf("") }

    // PubMed citation validation state (assistant-turn owned)
    var validation by remember { mutableStateOf<CitationValidationState?>(null) }

    // Poster generation: flow state + the 5-per-user free quota
    var posterGen by remember { mutableStateOf<PosterGenState?>(null) }
    var posterRemaining by remember { mutableStateOf<Int?>(null) }

    // Chapter generation from an uploaded PDF (thesis analyzer-style schemas, figures, charts, tables)
    var chapterGen by remember { mutableStateOf<ChapterGenState?>(null) }

    // Community posts matched to the current topic keyword
    var communityPosts by remember { mutableStateOf<CommunityPostsState?>(null) }
    var showPosterLimitDialog by remember { mutableStateOf(false) }
    var showPurchaseDialog by remember { mutableStateOf(false) }

    // PDF picker (Chat-with-PDF)
    val pdfPicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri ->
        if (uri != null) {
            pdfExtracting = true
            pdfExtractNote = "Reading PDF…"
            scope.launch {
                val result = runCatching {
                    withContext(Dispatchers.IO) {
                        val resolver = context.contentResolver
                        val name = queryPdfDisplayName(resolver, uri) ?: "thesis.pdf"
                        val text = resolver.openInputStream(uri)?.use { stream ->
                            PdfTextExtractor.extractText(context, stream)
                        }.orEmpty()
                        name to text
                    }
                }.getOrNull()
                if (result == null || result.second.isBlank()) {
                    pdfExtracting = false
                    pdfExtractNote = "Could not read that PDF. Try another file."
                    return@launch
                }
                val (fileName, pdfText) = result
                pdfExtractNote = "Extracting variables…"
                val variables = withContext(Dispatchers.IO) {
                    extractPdfVariables(pdfText, onChunk = { note ->
                        // onChunk is called from a coroutine launched on Dispatchers.IO;
                        // mutableStateOf is snapshot-safe so this is fine, but
                        // explicitly post to Main for clarity.
                        pdfExtractNote = note
                    })
                }
                // Always set pdfContext even when variables is empty so the text-preview
                // fallback (poster / chapter generation from raw PDF text) still works.
                pdfContext = PdfChatContext(
                    fileName = fileName,
                    variables = variables,
                    textPreview = pdfText.take(4000)
                )
                pdfExtracting = false
                pdfExtractNote = when {
                    variables.isNotEmpty() -> "${variables.size} variables extracted from $fileName"
                    pdfText.isNotBlank() -> "⚠ Variables could not be extracted (check Logcat: AiChatPdfExtract). PDF text is loaded — poster and chapter generation will use the raw text."
                    else -> "⚠ Could not read text from this PDF. Try a different file."
                }
            }
        }
    }

    val canSend = input.isNotBlank() && !busy

    fun send() {
        val text = input.trim()
        if (text.isEmpty() || busy) return
        input = ""
        questionSet = null
        searchPhase = 0
        suggestionOwner = -1
        enriching = false
        enrichmentNote = ""
        validation = null
        posterGen = null
        chapterGen = null
        communityPosts = null

        val updated = turns + ChatTurn("user", text)
        turns = updated
        busy = true
        val userTurnIndex = updated.lastIndex

        // JSON session log: every user input is recorded for debugging.
        appendChatLog(context, JSONObject().put("type", "user").put("text", text))

        // ── LLM INTENT CLASSIFICATION ─────────────────────────────────────────────────────────
        // One fast LLM call (Groq/Cerebras) decides which module to activate.
        // Falls back to regex detection on any error so the app never hard-breaks.
        val citationIntent = detectCitationList(userText = text, assistantReply = text)
        if (citationIntent != null) {
            val state = CitationValidationState(
                ownerTurn = userTurnIndex,
                detected = citationIntent.entries,
                intentRequested = citationIntent.explicitIntent,
                running = true,
                note = "Checking reference 0/${citationIntent.entries.size}",
                total = citationIntent.entries.size
            )
            validation = state
            scope.launch { runCitationValidation(state) { upd -> validation = upd } }
        }

        scope.launch {
            val decision = classifyIntent(text, pdfContext != null)
            Log.i("AiChatIntent", "module=${decision.module} kw=${decision.keyword} chap=${decision.chapterName}")

            val kw = decision.keyword.ifBlank { extractEarlyKeyword(text).orEmpty() }
            if (kw.isNotBlank()) {
                suggestionOwner = userTurnIndex
                searchPhase = 1
                scope.launch {
                    val found = withContext(Dispatchers.IO) { findRelatedQuestions(context, kw, text) }
                    if (found != null && found.questions.isNotEmpty()) { questionSet = found; searchPhase = 2 } else searchPhase = 3
                }
                val cpState = CommunityPostsState(ownerTurn = userTurnIndex, keyword = kw, running = true, note = "\uD83D\uDD0D Finding related community posts\u2026")
                communityPosts = cpState
                scope.launch {
                    val posts = withContext(Dispatchers.IO) { searchCommunityPosts(context, kw) }
                    communityPosts = cpState.copy(running = false, results = posts,
                        note = if (posts.isNullOrEmpty()) "" else "${posts.size} community post${if (posts.size == 1) "" else "s"} on \u201C${kw}\u201D")
                }
            }

            when (decision.module) {
                "poster" -> {
                    val posterSource = detectPosterAbstract(text, pdfContext)
                        ?: pdfContext?.let { buildPosterAbstractFromPdf(it) }
                        ?: text.takeIf { it.length >= 60 }
                    if (posterSource != null) {
                        val quota = withContext(Dispatchers.IO) { fetchPosterQuota(context) }
                        if (quota != null && quota <= 0) {
                            posterRemaining = 0; showPosterLimitDialog = true; busy = false; return@launch
                        }
                        posterRemaining = quota
                        posterGen = PosterGenState(ownerTurn = userTurnIndex, source = posterSource, phase = 1, note = "\uD83E\uDDE0 Analyzing abstract & building poster data\u2026")
                        val finalState = runPosterGeneration(posterSource) { u -> posterGen = u }
                        posterGen = finalState
                        if (finalState.phase == 3) {
                            val newRemaining = withContext(Dispatchers.IO) { consumePosterQuota(context) }
                            if (newRemaining != null) posterRemaining = newRemaining
                        }
                        turns = turns + ChatTurn("assistant",
                            if (finalState.phase == 3) "\uD83C\uDFA8 **Poster generated.**\n\n**${finalState.data?.title?.ifBlank { "Untitled poster" }}**\n\nSave with the button on the card."
                            else "\u26A0 Poster generation didn\u2019t complete: ${finalState.error.take(200)}"
                        )
                    } else {
                        turns = turns + ChatTurn("assistant", "\uD83D\uDCCE To generate a poster, please paste your abstract, or upload your thesis PDF first.")
                    }
                    busy = false
                    if (turns.isNotEmpty()) listState.animateScrollToItem(turns.lastIndex)
                }

                "chapter" -> {
                    val chapterName = decision.chapterName.ifBlank { "methodology" }
                    val ctx = pdfContext
                    if (ctx != null && ctx.textPreview.isNotBlank()) {
                        chapterGen = ChapterGenState(ownerTurn = userTurnIndex, chapterName = chapterName, phase = 1, note = "\uD83D\uDCDA Generating the $chapterName chapter\u2026")
                        val finalState = runChapterGeneration(userTurnIndex, chapterName, ctx, context) { u -> chapterGen = u }
                        chapterGen = finalState
                        turns = turns + ChatTurn("assistant",
                            if (finalState.phase == 2) "\uD83D\uDCDA **${chapterName.uppercase()}** chapter generated.\n\n${finalState.json?.sections?.size ?: 0} sections \u00B7 ${finalState.json?.tables?.size ?: 0} tables \u00B7 ${finalState.json?.figures?.size ?: 0} figures \u00B7 ${finalState.json?.charts?.size ?: 0} charts."
                            else "\u26A0 Chapter generation didn\u2019t complete: ${finalState.error.take(200)}"
                        )
                        appendChatLog(context, JSONObject().put("type", "chapter").put("chapter_name", chapterName).put("user_text", text).put("phase", finalState.phase).put("error", finalState.error))
                    } else {
                        turns = turns + ChatTurn("assistant", "\uD83D\uDCCE Please upload your thesis PDF first using the **Chat with PDF** button, then ask me to generate the $chapterName chapter.")
                    }
                    busy = false
                    if (turns.isNotEmpty()) listState.animateScrollToItem(turns.lastIndex)
                }

                "thesis_search" -> {
                    val query = decision.thesisQuery.ifBlank { extractEarlyKeyword(text) ?: text.take(60) }
                    val state = ThesisSearchState(ownerTurn = userTurnIndex, query = query, running = true, note = "Searching thesis topics for \u201C${query}\u201D\u2026")
                    thesisSearch = state
                    scope.launch {
                        val results = withContext(Dispatchers.IO) { fetchThesisTopics(context, query) }
                        thesisSearch = state.copy(running = false, results = results,
                            note = if (results.isEmpty()) "No thesis topics found for \u201C${query}\u201D"
                            else "${results.size} thesis topic${if (results.size == 1) "" else "s"} found for \u201C${query}\u201D")
                    }
                    val raw = try { withContext(Dispatchers.IO) { requestAiChat(updated, pdfContext) } }
                    catch (e: Throwable) { "\u26A0 ${e.message ?: "AI request failed."}" }
                    val fullText = raw.substringBefore("[SEARCH:").trimEnd().ifBlank { raw }
                    val reveal: suspend () -> Unit = {
                        val step = (fullText.length / 160).coerceIn(1, 6); var i = 0
                        while (i < fullText.length) { i = (i + step).coerceAtMost(fullText.length); streamingText = fullText.substring(0, i); delay(11) }
                        streamingText = null
                    }
                    reveal(); turns = turns + ChatTurn("assistant", fullText)
                    busy = false
                    if (turns.isNotEmpty()) listState.animateScrollToItem(turns.lastIndex)
                }

                else -> {
                    val raw = try { withContext(Dispatchers.IO) { requestAiChat(updated, pdfContext) } }
                    catch (e: Throwable) {
                        appendChatLog(context, JSONObject().put("type", "assistant_error").put("user_text", text).put("error", e.message ?: "AI request failed"))
                        "\u26A0 ${e.message ?: "AI request failed. Try again."}"
                    }
                    val cleaned = raw.substringBefore("[SEARCH:").trimEnd()
                    val aiKeyword = parseSearchKeyword(raw)
                    val fullText = cleaned.ifBlank { if (raw.contains("[SEARCH:")) raw else "\u26A0 AI gave an empty reply. Try again." }
                    appendChatLog(context, JSONObject().put("type", "assistant").put("user_text", text).put("keyword", aiKeyword ?: "").put("text", fullText))
                    val reveal: suspend () -> Unit = {
                        val step = (fullText.length / 160).coerceIn(1, 6); var i = 0
                        while (i < fullText.length) { i = (i + step).coerceAtMost(fullText.length); streamingText = fullText.substring(0, i); delay(11) }
                        streamingText = null
                    }
                    reveal()
                    turns = turns + ChatTurn("assistant", fullText)
                    val ownerIndex = turns.lastIndex
                    if (aiKeyword != null && aiKeyword != kw) {
                        suggestionOwner = ownerIndex; searchPhase = 1
                        val found = withContext(Dispatchers.IO) { findRelatedQuestions(context, aiKeyword, text) }
                        if (found != null && found.questions.isNotEmpty()) { questionSet = found; searchPhase = 2 } else if (searchPhase != 2) searchPhase = 3
                        val cpState2 = CommunityPostsState(ownerTurn = ownerIndex, keyword = aiKeyword, running = true, note = "\uD83D\uDD0D Refining community posts\u2026")
                        communityPosts = cpState2
                        scope.launch {
                            val posts = withContext(Dispatchers.IO) { searchCommunityPosts(context, aiKeyword) }
                            communityPosts = cpState2.copy(running = false, results = posts,
                                note = if (posts.isNullOrEmpty()) "" else "${posts.size} community post${if (posts.size == 1) "" else "s"} on \u201C${aiKeyword}\u201D")
                        }
                    } else {
                        suggestionOwner = ownerIndex
                    }
                    busy = false
                    if (turns.isNotEmpty()) listState.animateScrollToItem(turns.lastIndex)



            // Background data-quality pass on the shown questions: fix (a) topics that are
            // missing/placeholder (e.g. "PG 2020") and (b) explanations that are missing or
            // shorter than 100 chars — ask the AI, then persist the result into the DB.
            val qSet = questionSet
            val toFix = qSet?.questions?.filter { needsAiTopic(it) || needsAiExplanation(it) }?.take(4).orEmpty()
            if (toFix.isNotEmpty()) {
                enriching = true
                scope.launch {
                    var tagCount = 0
                    var explainCount = 0
                    for (q in toFix) {
                        // --- Topic: AI picks a topic/subject when blank or placeholder ---
                        if (needsAiTopic(q)) {
                            val label = runCatching { withContext(Dispatchers.IO) { requestTopicLabel(q.text) } }.getOrNull()
                            if (label != null && label.first.isNotBlank()) {
                                val newSubject = if (isPaperLikeSubject(q.subject)) label.second else q.subject
                                val ok = withContext(Dispatchers.IO) { postTopicAssignment(q.id, label.first, newSubject) }
                                if (ok) {
                                    tagCount++
                                    questionSet = questionSet?.let { s ->
                                        if (s.questions.none { it.id == q.id }) s
                                        else s.copy(questions = s.questions.map {
                                            if (it.id == q.id) it.copy(topic = label.first, subject = newSubject.ifBlank { it.subject }) else it
                                        })
                                    }
                                }
                            }
                        }
                        // --- Explanation: AI writes a brief one when missing or < 100 chars ---
                        if (needsAiExplanation(q)) {
                            val explanation = runCatching {
                                withContext(Dispatchers.IO) { requestExplanation(q.text, q.explanation) }
                            }.getOrNull()
                            if (!explanation.isNullOrBlank()) {
                                val ok = withContext(Dispatchers.IO) { postExplanation(q.id, explanation) }
                                if (ok) {
                                    explainCount++
                                    questionSet = questionSet?.let { s ->
                                        if (s.questions.none { it.id == q.id }) s
                                        else s.copy(questions = s.questions.map {
                                            if (it.id == q.id) it.copy(explanation = explanation) else it
                                        })
                                    }
                                }
                            }
                        }
                    }
                    enrichmentNote = buildString {
                        if (tagCount > 0) append("🧠 AI tagged $tagCount question${if (tagCount == 1) "" else "s"} with a topic")
                        if (tagCount > 0 && explainCount > 0) append(" and ")
                        if (explainCount > 0) append("✍️ rewrote $explainCount short explanation${if (explainCount == 1) "" else "s"}")
                    }
                    enriching = false
                }
            }
        }
    }

    LaunchedEffect(turns.size, streamingText) {
        val target = if (streamingText != null) turns.size else (turns.size - 1).coerceAtLeast(0)
        if (target >= 0) listState.animateScrollToItem(target)
    }

    Surface(modifier = Modifier.fillMaxSize()) {
        Column(modifier = Modifier.fillMaxSize()) {
            ChatHeader(
                onBack = onBack,
                onChatPdf = { pdfPicker.launch("application/pdf") },
                onPubMed = {
                    input = "Validate these references with PubMed:"
                },
                onThesisTopics = {
                    input = "Search thesis topics on:"
                },
                onPoster = {
                    if (pdfContext != null) {
                        // PDF loaded — generate poster directly from it, no text entry needed.
                        val posterSource = buildPosterAbstractFromPdf(pdfContext!!)
                        if (posterSource.isNotBlank() && !busy) {
                            val userTxt = "Generate a poster from my uploaded PDF"
                            val updated = turns + ChatTurn("user", userTxt)
                            turns = updated
                            busy = true
                            val ownerIdx = updated.lastIndex
                            scope.launch {
                                val quota = withContext(Dispatchers.IO) { fetchPosterQuota(context) }
                                if (quota != null && quota <= 0) {
                                    posterRemaining = 0
                                    showPosterLimitDialog = true
                                    busy = false
                                    return@launch
                                }
                                posterRemaining = quota
                                posterGen = PosterGenState(ownerTurn = ownerIdx, source = posterSource, phase = 1, note = "🧠 Analyzing abstract & building poster data…")
                                val finalState = runPosterGeneration(posterSource) { u -> posterGen = u }
                                posterGen = finalState
                                if (finalState.phase == 3) {
                                    val newRemaining = withContext(Dispatchers.IO) { consumePosterQuota(context) }
                                    if (newRemaining != null) posterRemaining = newRemaining
                                }
                                turns = turns + ChatTurn("assistant",
                                    if (finalState.phase == 3) "🎨 **Poster generated** from your PDF.\n\n**${finalState.data?.title?.ifBlank { "Untitled poster" }}**\n\nSave it with the button on the card."
                                    else "⚠ Poster generation didn't complete: ${finalState.error.take(200)}"
                                )
                                busy = false
                                if (turns.isNotEmpty()) listState.animateScrollToItem(turns.lastIndex)
                            }
                        } else {
                            // PDF loaded but couldn't extract content
                            input = "Generate a poster from this abstract:\n"
                        }
                    } else {
                        // No PDF — prompt user to paste abstract
                        input = "Generate a poster from this abstract:\n"
                    }
                },
                onChapter = {
                    if (pdfContext != null && pdfContext!!.textPreview.isNotBlank()) {
                        // PDF loaded — show a chapter picker by pre-filling with the most common chapter
                        input = "Generate the Methodology chapter from my uploaded PDF"
                    } else {
                        // No PDF — prompt to upload one first
                        input = ""
                        scope.launch {
                            turns = turns + ChatTurn("assistant", "📎 Please upload your thesis PDF first using the **Chat with PDF** button above, then I can generate chapters from it.")
                            if (turns.isNotEmpty()) listState.animateScrollToItem(turns.lastIndex)
                        }
                    }
                }
            )

            Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
                if (turns.isEmpty() && streamingText == null) {
                    ChatWelcomeHint(onSuggestion = { input = it })
                }
                LazyColumn(
                    state = listState,
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    turns.forEachIndexed { index, turn ->
                        item(key = "turn-$index") { ChatBubble(turn = turn) }
                        // Module cards attach to the turn that produced them, never all at once.
                        thesisSearch?.takeIf { it.ownerTurn == index }?.let { tState ->
                            item(key = "thesis-$index") { ThesisTopicsCard(state = tState, context = context) }
                        }
                        validation?.takeIf { it.ownerTurn == index }?.let { vState ->
                            item(key = "pubmed-$index") { CitationValidationCard(state = vState) }
                        }
                        posterGen?.takeIf { it.ownerTurn == index }?.let { pState ->
                            item(key = "poster-$index") {
                                PosterGenCard(
                                    state = pState,
                                    remaining = posterRemaining,
                                    onSave = { scope.launch { downloadAndSavePoster(context, pState.imageUrl, pState.imageFile, pState.data?.title.orEmpty()) } },
                                    onRetry = {
                                        if (pState.source.isNotBlank()) {
                                            posterGen = PosterGenState(ownerTurn = index, source = pState.source, phase = 1, note = "🧠 Retrying poster generation…")
                                            scope.launch {
                                                posterGen = runPosterGeneration(pState.source) { u -> posterGen = u }
                                            }
                                        }
                                    }
                                )
                            }
                        }
                        chapterGen?.takeIf { it.ownerTurn == index }?.let { cState ->
                            item(key = "chapter-$index") { ChapterGenCard(state = cState) }
                        }
                        communityPosts?.takeIf { it.ownerTurn == index }?.let { cpState ->
                            if (cpState.running || !cpState.results.isNullOrEmpty()) {
                                item(key = "community-$index") { CommunityPostsCard(state = cpState) }
                            }
                        }
                    }
                    streamingText?.let { partial ->
                        item(key = "streaming") { StreamingBubble(partial) }
                    }
                    if (searchPhase == 1) {
                        item(key = "searching") { SearchingRow() }
                    }
                    val qs = questionSet
                    if (searchPhase == 2 && qs != null && suggestionOwner == turns.lastIndex) {
                        item(key = "questions") { QuestionSuggestionBlock(context, qs) }
                    } else if (searchPhase == 3 && suggestionOwner == turns.lastIndex) {
                        item(key = "noquestions") { NoQuestionsRow() }
                    }
                    val note = enrichmentNote
                    if (suggestionOwner == turns.lastIndex && (enriching || note.isNotBlank())) {
                        item(key = "enrichtag") {
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(top = 2.dp),
                                horizontalArrangement = Arrangement.Start,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                if (enriching) {
                                    CircularProgressIndicator(modifier = Modifier.size(14.dp), strokeWidth = 2.dp)
                                    Spacer(modifier = Modifier.size(8.dp))
                                }
                                Text(
                                    text = if (note.isNotBlank()) note else "🧠 AI is enriching these questions…",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                }
            }

            PdfStatusChip(
                extracting = pdfExtracting,
                note = pdfExtractNote,
                contextData = pdfContext,
                onRemove = { pdfContext = null; pdfExtractNote = "" }
            )

            ChatInputBar(
                value = input,
                onValueChange = { input = it },
                enabled = !busy,
                canSend = canSend,
                onSend = { send() }
            )
        }
    }

    if (showPosterLimitDialog) {
        AlertDialog(
            onDismissRequest = { showPosterLimitDialog = false },
            title = { Text("🎨 Free poster limit reached") },
            text = {
                Text(
                    "You have reached your free poster limit ($POSTER_FREE_LIMIT/$POSTER_FREE_LIMIT).\n\nPurchase credits to generate more posters — every additional poster costs just ₹3 and is billed to your OpenRouter key."
                )
            },
            confirmButton = {
                Button(onClick = { showPosterLimitDialog = false; showPurchaseDialog = true }) {
                    Text("Purchase credits")
                }
            },
            dismissButton = {
                TextButton(onClick = { showPosterLimitDialog = false }) { Text("Cancel") }
            }
        )
    }

    if (showPurchaseDialog) {
        AlertDialog(
            onDismissRequest = { showPurchaseDialog = false },
            title = { Text("💳 Poster credits") },
            text = {
                Text(
                    "Credit purchase is coming soon.\n\nFor now, ask the admin to top up your account (poster credits), or contact support to unlock more poster generations."
                )
            },
            confirmButton = {
                Button(onClick = { showPurchaseDialog = false }) { Text("OK") }
            }
        )
    }
}

@Composable
private fun ChatHeader(
    onBack: () -> Unit,
    onChatPdf: () -> Unit,
    onPubMed: () -> Unit,
    onThesisTopics: () -> Unit,
    onPoster: () -> Unit,
    onChapter: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .statusBarsPadding()
            .background(MaterialTheme.colorScheme.surface)
            .padding(horizontal = 4.dp, vertical = 6.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = "Back",
                    tint = MaterialTheme.colorScheme.onSurface
                )
            }
            Column(modifier = Modifier.padding(start = 4.dp)) {
                Text(
                    text = "AI Chat",
                    color = MaterialTheme.colorScheme.onSurface,
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "Medical study assistant",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    fontSize = 12.sp
                )
            }
        }
        Row(
            modifier = Modifier.fillMaxWidth().padding(start = 12.dp, end = 8.dp, bottom = 2.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            ToolChip("📄 Chat with PDF", onChatPdf)
            ToolChip("🔬 PubMed", onPubMed)
            ToolChip("🎓 Thesis Topics", onThesisTopics)
            ToolChip("🖼️ Poster", onPoster)
            ToolChip("📚 Chapter", onChapter)
        }
    }
}

@Composable
private fun ToolChip(label: String, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(18.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.65f)
    ) {
        Text(
            text = label,
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun ChatWelcomeHint(onSuggestion: (String) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 36.dp, start = 20.dp, end = 20.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(text = "🧠", fontSize = 40.sp)
        Text(
            text = "How can I help you today?",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onSurface
        )
        Text(
            text = "Ask about NEET PG, diseases, drugs — or use the tools above.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(8.dp))

        val suggestions = listOf(
            "Explain typhoid fever presentation and treatment" to "🦠",
            "Give me 3 PubMed references for dengue fever" to "🔬",
            "Search thesis topics on diabetes mellitus" to "🎓",
            "Generate a poster from this abstract" to "🖼️",
            "Generate the Discussion chapter from my PDF" to "📚",
            "Validate these references:" to "✅"
        )
        suggestions.chunked(2).forEach { rowItems ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                rowItems.forEach { (text, emoji) ->
                    SuggestionCard(
                        text = text,
                        emoji = emoji,
                        onClick = { onSuggestion(text) },
                        modifier = Modifier.weight(1f)
                    )
                }
                if (rowItems.size == 1) Spacer(modifier = Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun SuggestionCard(
    text: String,
    emoji: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(14.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        modifier = modifier.height(92.dp)
    ) {
        Column(
            modifier = Modifier.padding(10.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Text(text = emoji, fontSize = 18.sp)
            Text(
                text = text,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 3,
                overflow = TextOverflow.Ellipsis
            )
        }
    }
}

@Composable
private fun ChatBubble(turn: ChatTurn) {
    val isUser = turn.role == "user"
    if (isUser) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.End
        ) {
            Surface(
                shape = RoundedCornerShape(18.dp, 18.dp, 6.dp, 18.dp),
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier.widthIn(max = 340.dp)
            ) {
                Text(
                    text = turn.content,
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                    color = MaterialTheme.colorScheme.onPrimary,
                    style = MaterialTheme.typography.bodyMedium
                )
            }
        }
    } else {
        // ChatGPT/Gemini style: assistant replies are plain text on the background
        // (no bubble) with a small AI badge, keeping the conversation easy to scan.
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.Top
        ) {
            Surface(
                shape = RoundedCornerShape(50),
                color = MaterialTheme.colorScheme.secondaryContainer,
                modifier = Modifier.size(26.dp)
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text(text = "AI", fontSize = 10.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSecondaryContainer)
                }
            }
            Column(modifier = Modifier.weight(1f).padding(top = 2.dp)) {
                AiRichText(
                    text = turn.content,
                    color = MaterialTheme.colorScheme.onSurface,
                    style = MaterialTheme.typography.bodyMedium,
                    lineHeight = 21.sp
                )
            }
        }
    }
}

@Composable
private fun StreamingBubble(partial: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.Top
    ) {
        Surface(
            shape = RoundedCornerShape(50),
            color = MaterialTheme.colorScheme.secondaryContainer,
            modifier = Modifier.size(26.dp)
        ) {
            Box(contentAlignment = Alignment.Center) {
                Text(text = "AI", fontSize = 10.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSecondaryContainer)
            }
        }
        Column(modifier = Modifier.weight(1f).padding(top = 2.dp)) {
            AiRichText(
                text = partial + "▌",
                color = MaterialTheme.colorScheme.onSurface,
                style = MaterialTheme.typography.bodyMedium,
                lineHeight = 21.sp
            )
        }
    }
}

@Composable
private fun SearchingRow() {
    Row(
        modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
        horizontalArrangement = Arrangement.Start,
        verticalAlignment = Alignment.CenterVertically
    ) {
        CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
        Spacer(modifier = Modifier.size(8.dp))
        Text(
            text = "🔎 Searching the 280k question bank…",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun NoQuestionsRow() {
    Text(
        text = "No closely related questions found in the bank for that search.",
        modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant
    )
}

@Composable
private fun QuestionSuggestionBlock(context: Context, set: QuestionSet) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(
                text = "📚 Related questions · “${set.keyword}”",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface
            )

            set.questions.take(4).forEach { q ->
                Surface(
                    shape = RoundedCornerShape(12.dp),
                    color = MaterialTheme.colorScheme.surface,
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable {
                            context.startActivity(
                                Intent(context, MCQActivity::class.java).apply {
                                    putExtra("question_id", q.id)
                                    putExtra("SELECTED_SUBJECT", q.subject.ifBlank { set.primarySubject })
                                }
                            )
                        }
                ) {
                    Column(modifier = Modifier.padding(10.dp)) {
                        val labelParts = listOfNotNull(
                            q.subject.ifBlank { set.primarySubject }.takeIf { it.isNotBlank() },
                            q.topic.takeIf { it.isNotBlank() }
                        )
                        Text(
                            text = labelParts.joinToString(" · "),
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.primary,
                            fontWeight = FontWeight.Bold,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = q.text,
                            style = MaterialTheme.typography.bodySmall,
                            maxLines = 3,
                            overflow = TextOverflow.Ellipsis,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    }
                }
            }

            Button(
                onClick = {
                    context.startActivity(
                        Intent(context, MCQActivity::class.java).apply {
                            putIntegerArrayListExtra("QUESTION_ID_LIST", ArrayList(set.testIds))
                            putExtra("SELECTED_SUBJECT", set.primarySubject)
                        }
                    )
                },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("▶ Take a practice test (${set.testIds.size} questions)")
            }
        }
    }
}

@Composable
private fun ChatInputBar(
    value: String,
    onValueChange: (String) -> Unit,
    enabled: Boolean,
    canSend: Boolean,
    onSend: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .navigationBarsPadding()
            .imePadding()
            .background(MaterialTheme.colorScheme.surface)
            .padding(horizontal = 12.dp, vertical = 8.dp)
    ) {
        Surface(
            shape = RoundedCornerShape(26.dp),
            color = MaterialTheme.colorScheme.surface,
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(
                modifier = Modifier.padding(start = 14.dp, end = 6.dp),
                verticalAlignment = Alignment.Bottom
            ) {
                OutlinedTextField(
                    value = value,
                    onValueChange = onValueChange,
                    modifier = Modifier.weight(1f),
                    placeholder = { Text("Ask anything…", color = MaterialTheme.colorScheme.onSurfaceVariant) },
                    maxLines = 4,
                    enabled = enabled,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                    keyboardActions = KeyboardActions(onSend = { if (canSend) onSend() }),
                    shape = RoundedCornerShape(26.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = Color.Transparent,
                        unfocusedBorderColor = Color.Transparent,
                        focusedContainerColor = Color.Transparent,
                        unfocusedContainerColor = Color.Transparent,
                        disabledContainerColor = Color.Transparent,
                        cursorColor = MaterialTheme.colorScheme.primary
                    )
                )
                FilledIconButton(
                    onClick = onSend,
                    enabled = canSend,
                    modifier = Modifier.padding(bottom = 6.dp)
                ) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.Send,
                        contentDescription = "Send"
                    )
                }
            }
        }
    }
}

@Composable
private fun CitationValidationCard(state: CitationValidationState) {
    val running = state.running
    val results = state.results
    val total = state.detected.size

    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            when {
                running && results == null -> {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Text(
                                text = "🔬 Validating against PubMed…",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            Text(
                                text = state.note.ifBlank { "Checking reference 0/$total" },
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                    if (total > 0) {
                        LinearProgressIndicator(
                            progress = { (state.current.toFloat() / total).coerceIn(0f, 1f) },
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }

                results != null -> {
                    val verifiedCount = results.count { it.found }
                    val failedCount = results.size - verifiedCount
                    Text(
                        text = if (verifiedCount == results.size) {
                            "✅ All $verifiedCount of ${results.size} references verified on PubMed"
                        } else {
                            "🔬 PubMed validation finished: $verifiedCount/${results.size} verified, $failedCount not found"
                        },
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    results.forEachIndexed { index, r ->
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(vertical = 1.dp),
                            verticalAlignment = Alignment.Top,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            if (r.found) {
                                Icon(
                                    imageVector = Icons.Filled.Verified,
                                    contentDescription = "Verified",
                                    tint = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.size(16.dp).padding(top = 1.dp)
                                )
                            } else {
                                Icon(
                                    imageVector = Icons.Filled.Error,
                                    contentDescription = "Not found",
                                    tint = MaterialTheme.colorScheme.error,
                                    modifier = Modifier.size(16.dp).padding(top = 1.dp)
                                )
                            }
                            Column(verticalArrangement = Arrangement.spacedBy(1.dp)) {
                                val preview = r.originalText.lineSequence()
                                    .map { it.trim().replace(Regex("""^\[?\d+]?\s*[.)-]?\s*"""), "") }
                                    .filter { it.isNotBlank() }
                                    .joinToString(" ")
                                    .let { if (it.length > 90) it.take(90) + "…" else it }
                                Text(
                                    text = "${index + 1}. $preview",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                                Text(
                                    text = if (r.found) {
                                        val pmidPart = "PMID: ${r.pmid}"
                                        val doiPart = r.doi?.takeIf { it.isNotBlank() }?.let { " · DOI: $it" }.orEmpty()
                                        "✅ Found on PubMed · $pmidPart$doiPart"
                                    } else {
                                        "❌ Not found on PubMed — check the citation details (authors, title, year)"
                                    },
                                    style = MaterialTheme.typography.labelSmall,
                                    color = if (r.found) MaterialTheme.colorScheme.primary
                                    else MaterialTheme.colorScheme.error
                                )
                            }
                        }
                    }
                }

                else -> {
                    // Detection finished but nothing worth validating ran
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                        Text(
                            text = state.note,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ThesisTopicsCard(state: ThesisSearchState, context: Context) {
    val results = state.results
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            if (results == null) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                    Text(
                        text = state.note,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            } else if (results.isEmpty()) {
                Text(
                    text = "📭 ${state.note}\nNo thesis topics or papers found in the catalog for this topic yet. Once thesis topics are added to the server catalog, they will appear here with their PDFs.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            } else {
                Text(
                    text = "🎓 ${state.note}",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                results.forEach { result ->
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = MaterialTheme.colorScheme.surface,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(10.dp)) {
                            Text(
                                text = result.subject.ifBlank { "Thesis #${result.thesisId}" },
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            if (result.studyType.isNotBlank() || result.difficulty.isNotBlank()) {
                                Text(
                                    text = listOfNotNull(
                                        result.studyType.takeIf { it.isNotBlank() },
                                        result.difficulty.takeIf { it.isNotBlank() }
                                    ).joinToString(" · "),
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.primary
                                )
                            }
                            if (result.snippet.isNotBlank()) {
                                Text(
                                    text = result.snippet,
                                    style = MaterialTheme.typography.bodySmall,
                                    maxLines = 3,
                                    overflow = TextOverflow.Ellipsis,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            if (result.pdfUrl.isNotBlank()) {
                                OutlinedButton(
                                    onClick = {
                                        context.startActivity(
                                            Intent(Intent.ACTION_VIEW, Uri.parse(result.pdfUrl))
                                        )
                                    },
                                    modifier = Modifier.padding(top = 4.dp)
                                ) {
                                    Text("📄 Open Paper PDF")
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

/** Card showing community posts related to the current chat topic. */
@Composable
private fun CommunityPostsCard(state: CommunityPostsState) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (state.running) {
                    CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                }
                Text(
                    text = if (state.running) state.note else "🗣️ Community posts on \"${state.keyword}\"",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface
                )
            }
            val posts = state.results
            if (!posts.isNullOrEmpty()) {
                posts.take(5).forEach { post ->
                    Surface(
                        shape = RoundedCornerShape(10.dp),
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            // Author row
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                if (post.authorPhoto.isNotBlank()) {
                                    AsyncImage(
                                        model = post.authorPhoto,
                                        contentDescription = "Profile photo",
                                        modifier = Modifier.size(24.dp).clip(RoundedCornerShape(12.dp))
                                    )
                                }
                                Text(
                                    text = post.author,
                                    style = MaterialTheme.typography.labelMedium,
                                    fontWeight = FontWeight.SemiBold,
                                    color = MaterialTheme.colorScheme.primary
                                )
                                if (post.likes > 0) {
                                    Text(
                                        text = "❤️ ${post.likes}",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            }
                            // Caption
                            if (post.caption.isNotBlank()) {
                                Text(
                                    text = post.caption.take(300),
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurface,
                                    maxLines = 4,
                                    overflow = TextOverflow.Ellipsis
                                )
                            }
                            // First image thumbnail (if any)
                            val img = post.images.firstOrNull()
                            if (img != null) {
                                AsyncImage(
                                    model = img,
                                    contentDescription = "Post image",
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .heightIn(max = 160.dp)
                                        .clip(RoundedCornerShape(8.dp))
                                )
                            }
                        }
                    }
                }
            } else if (!state.running && state.note.isNotBlank()) {
                Text(
                    text = state.note,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}


    state: PosterGenState,
    remaining: Int?,
    onSave: () -> Unit,
    onRetry: () -> Unit
) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            when {
                state.phase == 1 || state.phase == 2 -> {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        CircularProgressIndicator(modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
                        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Text(
                                text = state.note,
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            Text(
                                text = if (state.phase == 1)
                                    "Free AI builds the complete poster data from your abstract"
                                else
                                    "OpenRouter image model renders the poster (~₹3 each, billed to your key)",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                    LinearProgressIndicator(
                        progress = { if (state.phase == 1) 0.45f else 0.85f },
                        modifier = Modifier.fillMaxWidth()
                    )
                }

                state.phase == 3 -> {
                    val imageModel: Any? = state.imageUrl?.takeIf { it.isNotBlank() }
                        ?: state.imageFile?.takeIf { it.exists() }
                    Text(
                        text = "🎨 Generated poster" + (remaining?.let { " · $it free posters left" } ?: ""),
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    if (imageModel != null) {
                        AsyncImage(
                            model = imageModel,
                            contentDescription = "AI generated poster",
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(12.dp))
                        )
                    }
                    val d = state.data
                    if (d != null && (d.title.isNotBlank() || d.sections.isNotEmpty())) {
                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(
                                modifier = Modifier
                                    .padding(10.dp)
                                    .heightIn(max = 280.dp)
                                    .verticalScroll(rememberScrollState()),
                                verticalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                if (d.title.isNotBlank()) {
                                    Text(
                                        text = d.title,
                                        style = MaterialTheme.typography.titleSmall,
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.onSurface
                                    )
                                }
                                if (d.subtitle.isNotBlank()) {
                                    Text(
                                        text = d.subtitle,
                                        style = MaterialTheme.typography.labelMedium,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                                d.sections.forEach { s ->
                                    Text(
                                        text = s.heading,
                                        style = MaterialTheme.typography.labelMedium,
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.primary
                                    )
                                    AiRichText(
                                        text = s.body,
                                        color = MaterialTheme.colorScheme.onSurface,
                                        style = MaterialTheme.typography.bodySmall,
                                        lineHeight = 17.sp
                                    )
                                }
                            }
                        }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = onSave, modifier = Modifier.weight(1f)) {
                            Text("💾 Save to device")
                        }
                        OutlinedButton(onClick = onRetry, modifier = Modifier.weight(1f)) {
                            Text("🔄 Regenerate")
                        }
                    }
                }

                else -> {
                    Text(
                        text = "⚠ ${state.note.ifBlank { "Poster generation failed" }}",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.error
                    )
                    if (state.error.isNotBlank()) {
                        Text(
                            text = state.error.take(300),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    val d = state.data
                    if (d != null && d.sections.isNotEmpty()) {
                        Text(
                            text = "The structured poster data was still built — you can retry the image step.",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(
                                modifier = Modifier
                                    .padding(10.dp)
                                    .heightIn(max = 220.dp)
                                    .verticalScroll(rememberScrollState()),
                                verticalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                d.sections.forEach { s ->
                                    Text(
                                        text = s.heading,
                                        style = MaterialTheme.typography.labelMedium,
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.primary
                                    )
                                    Text(
                                        text = s.body,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurface
                                    )
                                }
                            }
                        }
                    }
                    OutlinedButton(onClick = onRetry, modifier = Modifier.padding(top = 2.dp)) {
                        Text("🔄 Retry")
                    }
                }
            }
        }
    }
}

@Composable
private fun ChapterGenCard(state: ChapterGenState) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            when {
                state.phase == 1 -> {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        CircularProgressIndicator(modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
                        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Text(
                                text = state.note,
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            Text(
                                text = "Using the thesis chapter schema — sections, tables, figures and charts parsed from the JSON reply",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                    LinearProgressIndicator(progress = { 0.45f }, modifier = Modifier.fillMaxWidth())
                }

                state.phase == 2 -> {
                    val json = state.json
                    if (json != null) {
                        Text(
                            text = "📚 ${json.chapterName.ifBlank { state.chapterName.uppercase() }}",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        json.sections.forEach { section -> ChapterSectionBlock(section) }
                        json.tables.forEach { table -> ChapterTableBlock(table) }
                        json.figures.forEach { figure -> ChapterFigureBlock(figure) }
                        json.charts.forEach { chart -> ChapterChartBlock(chart) }
                        if (json.abbreviations.isNotEmpty()) {
                            ChapterMiniBlock(title = "Abbreviations") {
                                json.abbreviations.forEach { ab ->
                                    Text(
                                        text = "${ab.short} = ${ab.full}",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurface
                                    )
                                }
                            }
                        }
                        if (json.references.isNotEmpty()) {
                            ChapterMiniBlock(title = "References (${json.references.size})") {
                                json.references.forEachIndexed { i, r ->
                                    Text(
                                        text = "${i + 1}. ${r.referenceText.take(220)}",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            }
                        }
                        if (json.sections.isEmpty() && json.tables.isEmpty() && json.figures.isEmpty() && json.charts.isEmpty()) {
                            Text(
                                text = "The chapter was generated but contained no parseable sections. Try asking again with a clearer chapter name.",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    } else {
                        Text(
                            text = "Chapter ready but no data to show.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                else -> {
                    Text(
                        text = "⚠ ${state.note.ifBlank { "Chapter generation failed" }}",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.error
                    )
                    if (state.error.isNotBlank()) {
                        Text(
                            text = state.error.take(300),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ChapterSectionBlock(section: ChatSectionJson) {
    if (section.heading.isBlank() && section.paragraphs.isEmpty() && section.bullets.isEmpty() &&
        section.numberedPoints.isEmpty() && section.subsections.isEmpty()
    ) return
    Column(
        modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        if (section.heading.isNotBlank()) {
            Text(
                text = section.heading,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary
            )
        }
        if (section.content.isNotBlank()) {
            AiRichText(
                text = section.content,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                style = MaterialTheme.typography.bodySmall,
                lineHeight = 17.sp
            )
        }
        section.paragraphs.forEach { p ->
            AiRichText(
                text = p,
                color = MaterialTheme.colorScheme.onSurface,
                style = MaterialTheme.typography.bodyMedium,
                lineHeight = 19.sp
            )
        }
        section.bullets.forEach { b ->
            AiRichText(
                text = "• $b",
                color = MaterialTheme.colorScheme.onSurface,
                style = MaterialTheme.typography.bodySmall,
                lineHeight = 17.sp
            )
        }
        section.numberedPoints.forEachIndexed { i, p ->
            AiRichText(
                text = "${i + 1}. $p",
                color = MaterialTheme.colorScheme.onSurface,
                style = MaterialTheme.typography.bodySmall,
                lineHeight = 17.sp
            )
        }
        section.subsections.forEach { sub ->
            if (sub.heading.isNotBlank()) {
                Text(
                    text = sub.heading,
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface
                )
            }
            sub.paragraphs.forEach { p ->
                AiRichText(
                    text = p,
                    color = MaterialTheme.colorScheme.onSurface,
                    style = MaterialTheme.typography.bodySmall,
                    lineHeight = 17.sp
                )
            }
        }
        section.table?.let { ChapterTableBlock(it) }
        section.figures.forEach { ChapterFigureBlock(it) }
        if (section.references.isNotEmpty()) {
            Text(
                text = "Refs: " + section.references.take(8).joinToString("; ") { it.citation.ifBlank { it.referenceText.take(60) } },
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun ChapterTableBlock(table: ChatTableJson) {
    if (table.headers.isEmpty() && table.rows.isEmpty()) return
    Surface(
        shape = RoundedCornerShape(10.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f),
        modifier = Modifier.fillMaxWidth().padding(top = 2.dp)
    ) {
        Column(modifier = Modifier.padding(8.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                text = "${table.tableNumber.ifBlank { "Table" }}${if (table.title.isNotBlank()) ": ${table.title}" else ""}",
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface
            )
            if (table.headers.isNotEmpty()) {
                Row(modifier = Modifier.fillMaxWidth()) {
                    table.headers.forEachIndexed { i, h ->
                        Text(
                            text = h,
                            modifier = Modifier.weight(1f),
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary,
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                }
            }
            table.rows.take(30).forEach { row ->
                Row(modifier = Modifier.fillMaxWidth()) {
                    val cells = if (row.size >= table.headers.size) row else row + List(table.headers.size - row.size) { "" }
                    cells.forEach { c ->
                        Text(
                            text = c,
                            modifier = Modifier.weight(1f),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurface,
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                }
            }
            if (table.footnote.isNotBlank()) {
                Text(
                    text = table.footnote,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun ChapterFigureBlock(figure: ChatFigureJson) {
    if (figure.title.isBlank() && figure.caption.isBlank() && figure.imageSearchQuery.isBlank()) return
    Surface(
        shape = RoundedCornerShape(10.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.25f),
        modifier = Modifier.fillMaxWidth().padding(top = 2.dp)
    ) {
        Column(modifier = Modifier.padding(8.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
            Text(
                text = "🖼️ Figure ${figure.figureNumber.ifBlank { "" }}${if (figure.title.isNotBlank()) ": ${figure.title}" else ""}",
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface
            )
            if (figure.caption.isNotBlank()) {
                Text(
                    text = figure.caption,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface
                )
            }
            if (figure.imageSearchQuery.isNotBlank()) {
                Text(
                    text = "🔎 image: ${figure.imageSearchQuery}",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun ChapterChartBlock(chart: ChatChartJson) {
    val labels = chart.data.map { it.label }.ifEmpty { chart.labels }
    val values = chart.data.map { it.value }.ifEmpty { chart.values }
    if (values.isEmpty() || values.none { !it.isNaN() }) return
    Surface(
        shape = RoundedCornerShape(10.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.25f),
        modifier = Modifier.fillMaxWidth().padding(top = 2.dp)
    ) {
        Column(modifier = Modifier.padding(8.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                text = "📊 ${chart.title.ifBlank { "Chart" }}",
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface
            )
            MiniChart(type = chart.type, labels = labels, values = values)
        }
    }
}

@Composable
private fun MiniChart(type: String, labels: List<String>, values: List<Double>) {
    val nums = values.filter { !it.isNaN() }
    if (nums.isEmpty()) return
    val maxV = (nums.maxOrNull() ?: 1.0).coerceAtLeast(0.0001)
    val total = nums.sum().takeIf { it > 0 } ?: 1.0
    val t = type.lowercase()
    val colors = listOf(
        MaterialTheme.colorScheme.primary,
        MaterialTheme.colorScheme.tertiary,
        MaterialTheme.colorScheme.secondary,
        MaterialTheme.colorScheme.error,
        MaterialTheme.colorScheme.primary.copy(alpha = 0.6f),
        MaterialTheme.colorScheme.tertiary.copy(alpha = 0.6f)
    )
    Column(modifier = Modifier.fillMaxWidth()) {
        Canvas(modifier = Modifier.fillMaxWidth().height(110.dp)) {
            val n = nums.size
            when {
                t.contains("pie") || t.contains("doughnut") -> {
                    var start = -90f
                    nums.forEachIndexed { i, v ->
                        val sweep = (v / total * 360f).toFloat()
                        drawArc(color = colors[i % colors.size], startAngle = start, sweepAngle = sweep, useCenter = true)
                        start += sweep
                    }
                }
                t.contains("line") || t.contains("area") -> {
                    val stepX = size.width / (n - 1).coerceAtLeast(1)
                    val pts = nums.mapIndexed { i, v ->
                        Offset(stepX * i, size.height - (v / maxV * size.height * 0.88f).toFloat())
                    }
                    pts.zipWithNext().forEach { (a, b) ->
                        drawLine(color = colors[0], start = a, end = b, strokeWidth = 4f)
                    }
                    pts.forEach { p -> drawCircle(color = colors[1], radius = 5f, center = p) }
                }
                else -> {
                    val barW = size.width / n
                    nums.forEachIndexed { i, v ->
                        val h = (v / maxV * size.height * 0.88f).toFloat()
                        drawRect(
                            color = colors[i % colors.size],
                            topLeft = Offset(barW * i + barW * 0.18f, size.height - h),
                            size = Size(barW * 0.64f, h)
                        )
                    }
                }
            }
        }
        if (labels.isNotEmpty()) {
            Row(modifier = Modifier.fillMaxWidth()) {
                labels.take(8).forEach { label ->
                    Text(
                        text = label,
                        modifier = Modifier.weight(1f),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }
        }
    }
}

@Composable
private fun ChapterMiniBlock(title: String, content: @Composable () -> Unit) {
    Surface(
        shape = RoundedCornerShape(10.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.25f),
        modifier = Modifier.fillMaxWidth().padding(top = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .padding(8.dp)
                .heightIn(max = 180.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(3.dp)
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface
            )
            content()
        }
    }
}

@Composable
private fun PdfStatusChip(
    extracting: Boolean,
    note: String,
    contextData: PdfChatContext?,
    onRemove: () -> Unit
) {
    if (!extracting && contextData == null && note.isBlank()) return
    Surface(
        shape = RoundedCornerShape(14.dp),
        color = if (extracting) MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.4f)
        else MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.45f),
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 2.dp)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            if (extracting) {
                CircularProgressIndicator(modifier = Modifier.size(14.dp), strokeWidth = 2.dp)
                Text(
                    text = note.ifBlank { "Reading PDF…" },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            } else if (contextData != null) {
                Text(text = "📄", fontSize = 14.sp)
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = contextData.fileName,
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurface,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    Text(
                        text = if (contextData.variables.isNotEmpty())
                            "${contextData.variables.size} variables extracted — AI uses them for answers"
                        else "PDF loaded — ask a question about it",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
                IconButton(
                    onClick = onRemove,
                    modifier = Modifier.size(26.dp)
                ) {
                    Icon(
                        imageVector = Icons.Filled.Close,
                        contentDescription = "Remove PDF",
                        tint = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.size(16.dp)
                    )
                }
            } else {
                Text(
                    text = note,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error
                )
            }
        }
    }
}

// ---------------------------------------------------------------- Thesis topics module

/** Detects a "search thesis topics/papers on <topic>" request and returns the topic. */
private fun detectThesisTopicSearch(text: String): String? {
    val t = text.trim()
    if (t.isBlank() || t.length < 6) return null
    val lower = t.lowercase()
    val thesisSignal = Regex(
        """\b(thesis|theses|synopsis|dissertation|paper|papers|research paper|research papers|publication|review paper)\b""",
        RegexOption.IGNORE_CASE
    ).containsMatchIn(lower)
    val searchSignal = Regex(
        """\b(search|find|look|get|need|show|fetch|list|give)\b""",
        RegexOption.IGNORE_CASE
    ).containsMatchIn(lower)
    val topicMarker = Regex(
        """\b(on|about|for|regarding|related to|topic|topics|paper on|papers on)\b""",
        RegexOption.IGNORE_CASE
    ).containsMatchIn(lower)
    if (!thesisSignal || !searchSignal || !topicMarker) return null

    // Pull out the topic: "search thesis topics on X" -> X
    val cleaned = t
        .replace(Regex("""(?i)\b(search|find|look|get|need|show|fetch|list|give)\b"""), " ")
        .replace(Regex("""(?i)\b(thesis|theses|synopsis|dissertation|paper|papers|research paper|research papers|publication|review paper|topics?|pdfs?|with pdfs?)\b"""), " ")
        .replace(Regex("""(?i)\b(on|about|for|regarding|related to|with)\b"""), " ")
        .replace(Regex("""[?,.!]"""), " ")
        .replace(Regex("""\s+"""), " ")
        .trim()
    val topic = cleaned.trim().let { if (it.length > 2) it else t.replace(Regex("""(?i)\b(search|thesis|topics|papers|pdf|on|about|for)\b"""), " ").replace(Regex("""\s+"""), " ").trim() }
    return topic.takeIf { it.length >= 2 }?.take(120)
}

/** Fetches thesis topics + PDFs from the thesis catalog endpoint. */
private fun fetchThesisTopics(context: Context, query: String): List<ThesisTopicResult> {
    val userId = context.getSharedPreferences("MY_APP", Context.MODE_PRIVATE).getInt("user_id", 0)
    val url = "https://medigyaan.xyz/Neurons/thesis_topics_search.php?q=${URLEncoder.encode(query, "UTF-8")}&limit=15&user_id=$userId"
    val request = Request.Builder()
        .url(url)
        .addHeader("X-App-Signature", "EduLabsRTM_Secure_v1_2026")
        .addHeader("Accept", "application/json")
        .get()
        .build()
    return try {
        httpClient.newCall(request).execute().use { response ->
            val body = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                Log.e(POSTER_LOG_TAG, "thesis topics search HTTP ${response.code}: ${body.take(200)}")
                return emptyList()
            }
            val root = JSONObject(body)
            if (!root.optBoolean("success", false)) {
                Log.e(POSTER_LOG_TAG, "thesis topics search failed: ${body.take(200)}")
                return emptyList()
            }
            Log.i(POSTER_LOG_TAG, "thesis topics search '$query' -> ${root.optInt("count", 0)} results")
            val arr = root.optJSONArray("data") ?: return emptyList()
            val out = mutableListOf<ThesisTopicResult>()
            for (i in 0 until arr.length()) {
                val obj = arr.optJSONObject(i) ?: continue
                out += ThesisTopicResult(
                    thesisId = obj.optInt("thesis_id", 0),
                    subject = obj.optString("subject", ""),
                    snippet = obj.optString("snippet", ""),
                    pdfUrl = obj.optString("pdf_url", ""),
                    studyType = obj.optString("study_type", ""),
                    difficulty = obj.optString("difficulty", "")
                )
            }
            out
        }
    } catch (e: Exception) {
        emptyList()
    }
}

// ---------------------------------------------------------------- Chat-with-PDF module

/** Extracts structured variables from PDF text using the same approach as the Thesis Analyzer. */
private suspend fun extractPdfVariables(
    pdfText: String,
    onChunk: (String) -> Unit = {}
): List<Variable> {
    if (pdfText.isBlank()) return emptyList()
    val chunks = TextChunker.chunkText(pdfText, 8000)
    val merged = linkedMapOf<String, Variable>()
    for ((idx, chunk) in chunks.withIndex()) {
        onChunk("Extracting variables (chunk ${idx + 1}/${chunks.size})…")
        try {
            val raw = withContext(Dispatchers.IO) {
                rotateAiRequest(
                    messages = listOf(Message("system", PDF_VARIABLE_EXTRACTION_SYSTEM), Message("user", chunk)),
                    maxTokens = 3500,
                    source = "ai_chat_pdf_extract"
                )
            }
            parseExtractedVariables(raw).forEach { v ->
                if (v.name.isNotBlank() && v.value.isNotBlank()) {
                    val existing = merged[v.name]
                    merged[v.name] = if (existing == null) v
                    else existing.copy(value = (existing.value + "\n" + v.value).trim())
                }
            }
        } catch (e: Throwable) {
            Log.e("AiChatPdfExtract", "chunk ${idx + 1}/${chunks.size} extraction failed: ${e.message}", e)
            onChunk("⚠ Chunk ${idx + 1} failed: ${e.message?.take(80) ?: "unknown error"}")
        }
    }
    return merged.values.toList()
}

private const val PDF_VARIABLE_EXTRACTION_SYSTEM =
    "You are an expert medical thesis extractor. From the given thesis text, extract ALL the following variables " +
        "and provide the complete content (do not truncate or summarise). Preserve headings, numbering, bullets and paragraph breaks. " +
        "Return ONLY valid JSON in this exact structure: " +
        "{\"variables\":[{\"variable_name\":\"Title\",\"variable_value\":\"...\"},{\"variable_name\":\"Disease_or_Condition\",\"variable_value\":\"...\"}, " +
        "{\"variable_name\":\"Study_Design\",\"variable_value\":\"...\"},{\"variable_name\":\"Study_Setting\",\"variable_value\":\"...\"}, " +
        "{\"variable_name\":\"Study_Population\",\"variable_value\":\"...\"},{\"variable_name\":\"Sample_Size\",\"variable_value\":\"...\"}, " +
        "{\"variable_name\":\"Inclusion_Criteria\",\"variable_value\":\"...\"},{\"variable_name\":\"Exclusion_Criteria\",\"variable_value\":\"...\"}, " +
        "{\"variable_name\":\"Objectives_primary\",\"variable_value\":\"...\"},{\"variable_name\":\"Hypothesis_null\",\"variable_value\":\"...\"}, " +
        "{\"variable_name\":\"Hypothesis_alternate\",\"variable_value\":\"...\"},{\"variable_name\":\"Data_Collection\",\"variable_value\":\"...\"}, " +
        "{\"variable_name\":\"Statistical_Analysis\",\"variable_value\":\"...\"},{\"variable_name\":\"Results_text\",\"variable_value\":\"...\"}, " +
        "{\"variable_name\":\"Discussion_text\",\"variable_value\":\"...\"},{\"variable_name\":\"Limitations\",\"variable_value\":\"...\"}, " +
        "{\"variable_name\":\"Conclusion_text\",\"variable_value\":\"...\"},{\"variable_name\":\"References_Vancouver\",\"variable_value\":\"numbered Vancouver references exactly as present; preserve PMID and DOI if shown\"}, " +
        "{\"variable_name\":\"Abstract_structured\",\"variable_value\":\"Background:...\\nAim:...\\nMethods:...\\nResults:...\\nConclusion:...\"}]}. " +
        "If a variable is not present, omit it (never set empty). Keep variable_name exactly as written. Do not invent PMIDs or DOIs."

private fun parseExtractedVariables(raw: String): List<Variable> {
    return try {
        val trimmed = raw.trim()
            .removePrefix("```json").removePrefix("```").removeSuffix("```")
            .trim()
        val first = trimmed.indexOf('{')
        if (first < 0) return emptyList()
        val slice = trimmed.substring(first)
        val obj = JSONObject(slice)
        val arr = obj.optJSONArray("variables") ?: return emptyList()
        val out = mutableListOf<Variable>()
        for (i in 0 until arr.length()) {
            val item = arr.optJSONObject(i) ?: continue
            val name = item.optString("variable_name", "").trim()
            val value = item.optString("variable_value", "").trim()
            if (name.isNotBlank() && value.isNotBlank()) out += Variable(name, value)
        }
        out
    } catch (e: Exception) {
        emptyList()
    }
}

/** Resolves a display name for the picked PDF. */
private fun queryPdfDisplayName(resolver: android.content.ContentResolver, uri: Uri): String? {
    return runCatching {
        resolver.query(uri, null, null, null, null)?.use { cursor ->
            if (cursor.moveToFirst()) {
                val idx = cursor.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
                if (idx >= 0) cursor.getString(idx) else null
            } else null
        }
    }.getOrNull()
}

// ---------------------------------------------------------------- PubMed citation validation helpers

/**
 * Decides whether a PubMed validation run should happen for a finished exchange.
 *
 * Triggered when:
 *  1. the user pasted a citation list AND asked to validate/check/verify it — the pasted list
 *     itself is validated (no need for the AI to echo it), or
 *  2. the AI reply contains a numbered reference/citation list AND the user's message asked for
 *     references/citations/sources (e.g. "give me PubMed references for typhoid fever"), or
 *  3. the user pasted a list with an explicit validation ask but the AI reply is where a
 *     canonical list would live (defensive — validates whichever copy looks real).
 */
private fun detectCitationList(userText: String, assistantReply: String): DetectedReferences? {
    // "validate/check these references"
    val userWantsValidation = Regex(
        """(?:validate|check|verify|confirm|look\s*up|are\s*these|are\s*the|is\s*this|is\s*that)\b[^\n]{0,90}\b(?:reference|citation|source|pubmed|pmid|doi)\b""",
        RegexOption.IGNORE_CASE
    ).containsMatchIn(userText)
    // "give me / list / provide references..."
    val userAskingForReferences = Regex(
        """\b(?:list|give|provide|need|write|format|find|share|suggest|include)\b[^\n]{0,50}\b(?:references|citations|sources|pubmed)\b""",
        RegexOption.IGNORE_CASE
    ).containsMatchIn(userText)
    val userAskedForCitationWork = userWantsValidation || userAskingForReferences

    val userEntries = PubMedCitationValidator.extractCitationEntries(userText)
    val userHasRealList = PubMedCitationValidator.looksLikeReferenceBlock(userText) && userEntries.size >= 2

    // 1) User pasted a citation list and is asking anything citation-related → validate the pasted list.
    if (userHasRealList && userAskedForCitationWork) {
        return DetectedReferences(userEntries, explicitIntent = userWantsValidation)
    }

    // 2) Explicit ask that did not paste a list → the AI reply is where the list lives.
    val replyListBlock = referenceListSlice(assistantReply)
    if (userAskedForCitationWork && PubMedCitationValidator.looksLikeReferenceBlock(replyListBlock)) {
        val aiEntries = PubMedCitationValidator.extractCitationEntries(replyListBlock)
        if (aiEntries.size >= 2) return DetectedReferences(aiEntries, explicitIntent = userWantsValidation)
    }
    return null
}

/** Slices a reply down to its numbered reference block (skips intro/outro prose). */
private fun referenceListSlice(reply: String): String {
    if (reply.isBlank()) return reply
    val lines = reply.replace("\r\n", "\n").split("\n")
    var startIdx = -1
    for ((index, line) in lines.withIndex()) {
        val t = line.trim()
        if (t.equals("References", ignoreCase = true) || t.equals("References:", ignoreCase = true) ||
            t.equals("REFERENCES", ignoreCase = true) || t.equals("Citations", ignoreCase = true) ||
            t.equals("Citations:", ignoreCase = true)
        ) {
            startIdx = index + 1
            break
        }
        if (Regex("""^\s*\[?\d+]?\s*[.)]\s*[A-ZÀ-Ž]""").containsMatchIn(t)) {
            startIdx = index
            break
        }
    }
    if (startIdx < 0) return reply
    return lines.subList(startIdx, lines.size).joinToString("\n")
}

/**
 * Runs the validator for the given detected references.
 * @param emit invoked on the main thread with the updated immutable state (Compose-safe).
 */
private suspend fun runCitationValidation(
    state: CitationValidationState,
    emit: (CitationValidationState) -> Unit
) {
    try {
        val results = PubMedCitationValidator.validate(state.detected) { progress ->
            emit(
                state.copy(
                    note = progress.status,
                    current = progress.current,
                    total = progress.total
                )
            )
        }
        emit(
            state.copy(
                running = false,
                note = "PubMed validation complete ${results.count { it.found }}/${results.size}",
                current = state.detected.size,
                total = state.detected.size,
                results = results
            )
        )
    } catch (e: Throwable) {
        emit(
            state.copy(
                running = false,
                note = "PubMed validation failed: ${e.message ?: "network error"}",
                results = emptyList()
            )
        )
    }
}

// ---------------------------------------------------------------- AI + backend

/** Sends the whole conversation (plus uploaded-PDF context) to the AI providers. */
// ---------------------------------------------------------------- Chapter generation backend

private const val CHAPTER_LOG_TAG = "ChapterGen"
private const val CHAT_LOG_TAG = "ChatLog"

/**
 * Appends one JSON line to files/chat_logs/chat_log.jsonl — every user input and
 * every AI reply (plus full chapter-generation requests/replies) so the exchange
 * can be pulled with: adb exec-out run-as com.corp.medigyaan cat files/chat_logs/chat_log.jsonl
 * Mirrors the same JSON to logcat under the "ChatLog" tag.
 */
private val chatLogLock = Any()

private fun appendChatLog(context: Context, entry: JSONObject) {
    try {
        entry.put("ts", System.currentTimeMillis())
        synchronized(chatLogLock) {
            val dir = File(context.filesDir, "chat_logs")
            if (!dir.exists()) dir.mkdirs()
            File(dir, "chat_log.jsonl").appendText(entry.toString() + "\n")
        }
        Log.i(CHAT_LOG_TAG, entry.toString())
    } catch (e: Throwable) {
        Log.e(CHAT_LOG_TAG, "log write failed: ${e.message}")
    }
}

/**
 * Chapter catalog: name -> (chapter type, section headings, guidance).
 * Mirrors the thesis analyzer's default chapter headings so interpretation matches the analyzer.
 */
private val CHAT_CHAPTERS: Map<String, Triple<String, List<String>, String>> = mapOf(
    "introduction" to Triple("CHAPTER_1", listOf("Background", "Problem Statement", "Need for the Study", "Aim", "Objectives", "Scope"),
        "Build the chapter from broad clinical context to the specific problem. Use a formal thesis tone and avoid filler text."),
    "background" to Triple("CHAPTER_1", listOf("Epidemiology", "Clinical Relevance", "Current Evidence", "Knowledge Gap"),
        "Write a clinically grounded background with a clear evidence trail and a polished academic flow."),
    "disease burden" to Triple("CHAPTER_1", listOf("Global Burden", "National Burden", "Local/Regional Burden", "Clinical Burden", "Public Health Impact", "Disability Adjusted Life Years (DALYs)", "Economic Burden", "Burden Relevance to Thesis"),
        "Cover magnitude, prevalence, incidence, clinical/public-health burden, disability/mortality, economic burden and local relevance. Never invent statistics; if a statistic is absent from the PDF, describe the burden qualitatively."),
    "epidemiology" to Triple("CHAPTER_1", listOf("Prevalence", "Incidence", "Age Distribution", "Sex Distribution", "Geographic Distribution", "Risk Groups", "Time Trends", "Epidemiological Determinants", "Local Epidemiological Data"),
        "Cover prevalence, incidence, age/sex distribution, risk groups, geography, trends and determinants. Cite every factual sentence. Include an epidemiology figure and an epidemiological summary table."),
    "pathophysiology" to Triple("CHAPTER_1", listOf("Disease Mechanism Overview", "Cellular and Molecular Basis", "Organ System Involvement", "Disease Progression", "Compensatory Mechanisms", "Pathophysiological Basis of Symptoms", "Clinical-Pathological Correlation"),
        "Explain the disease mechanism from molecular to clinical level. Include a disease mechanism figure with a detailed caption and a mechanism-summary reference table."),
    "current treatment" to Triple("CHAPTER_1", listOf("Medical Management", "Pharmacological Therapy", "Surgical/Interventional Options", "Treatment Guidelines", "Treatment Algorithms", "Novel/Experimental Therapies", "Treatment Outcomes and Prognosis"),
        "Cover medical, pharmacological, surgical/interventional options, guidelines, algorithms, novel therapies and outcomes. Include a treatment algorithm figure and a treatment-regimen-outcome table."),
    "research gap" to Triple("CHAPTER_1", listOf("Existing Evidence", "Identified Gaps", "Unanswered Questions", "Why This Study"), "Write the research gap chapter using only the PDF data."),
    "need for study" to Triple("CHAPTER_1", listOf("Rationale", "Significance", "Justification", "Potential Impact"), "Write the need-for-study chapter using only the PDF data."),
    "literature review" to Triple("CHAPTER_2", listOf("Epidemiology", "Risk Factors", "Pathophysiology", "Investigations", "Current Evidence", "Knowledge Gap"),
        "Review the literature with verified evidence. Add separate figures for epidemiology, risk factors, pathophysiology and investigations with concrete image_search_query values, plus a summary table."),
    "aim of study" to Triple("CHAPTER_2", listOf("Primary Aim", "Secondary Aims"), "State the aim(s) concisely from the PDF data."),
    "objectives" to Triple("CHAPTER_2", listOf("Primary Objectives", "Secondary Objectives"), "State the objectives clearly from the PDF data."),
    "hypothesis" to Triple("CHAPTER_2", listOf("Null Hypothesis", "Alternative Hypothesis"), "State the hypotheses from the PDF data."),
    "materials and methods" to Triple("CHAPTER_3", listOf("Study Design", "Study Setting", "Study Duration", "Study Population", "Inclusion Criteria", "Exclusion Criteria", "Sample Size", "Sampling Technique", "Data Collection", "Variables Collected", "Investigations", "Study Procedure", "Outcome Measures", "Statistical Analysis"),
        "Describe the methodology in detail. Include a study design flowchart figure and a variables/measurements table."),
    "methodology" to Triple("CHAPTER_3", listOf("Study Design", "Study Setting", "Study Duration", "Study Population", "Inclusion Criteria", "Exclusion Criteria", "Sample Size", "Sampling Technique", "Data Collection", "Variables Collected", "Investigations", "Study Procedure", "Outcome Measures", "Statistical Analysis"),
        "Describe the methodology in detail. Include a study design flowchart figure and a variables/measurements table."),
    "study design" to Triple("CHAPTER_3", listOf("Type of Study", "Design Rationale", "Comparison Groups"), "Describe the study design from the PDF data. Include a study design flowchart figure."),
    "study setting" to Triple("CHAPTER_3", listOf("Place of Study", "Duration", "Facilities"), "Describe the study setting from the PDF data."),
    "study duration" to Triple("CHAPTER_3", listOf("Duration", "Timeline"), "Describe the study duration from the PDF data."),
    "study population" to Triple("CHAPTER_3", listOf("Source Population", "Target Population"), "Describe the study population from the PDF data."),
    "inclusion criteria" to Triple("CHAPTER_3", listOf("Inclusion Criteria"), "List the inclusion criteria from the PDF data."),
    "exclusion criteria" to Triple("CHAPTER_3", listOf("Exclusion Criteria"), "List the exclusion criteria from the PDF data."),
    "sample size" to Triple("CHAPTER_3", listOf("Sample Size Calculation", "Assumptions", "Final Sample Size"), "Explain the sample size calculation from the PDF data."),
    "sampling technique" to Triple("CHAPTER_3", listOf("Sampling Method", "Technique Rationale"), "Describe the sampling technique from the PDF data."),
    "data collection" to Triple("CHAPTER_3", listOf("Data Sources", "Collection Procedure", "Instruments"), "Describe the data collection from the PDF data."),
    "variables collected" to Triple("CHAPTER_3", listOf("Independent Variables", "Dependent Variables", "Operational Definitions"), "List the variables from the PDF data. Include a variables table."),
    "investigations" to Triple("CHAPTER_3", listOf("Diagnostic Tests", "Laboratory Investigations", "Imaging", "Interpretation"),
        "Cover the investigations. Include a diagnostic workflow figure and an investigation-purpose-interpretation table."),
    "study procedure" to Triple("CHAPTER_3", listOf("Stepwise Procedure", "Flow of Participants"), "Describe the study procedure. Include a procedure flowchart figure."),
    "outcome measures" to Triple("CHAPTER_3", listOf("Primary Outcomes", "Secondary Outcomes", "Measurement Methods"), "Describe the outcome measures from the PDF data."),
    "statistical analysis" to Triple("CHAPTER_3", listOf("Statistical Tests", "Software", "Significance Level"), "Describe the statistical analysis from the PDF data."),
    "ethical considerations" to Triple("CHAPTER_3", listOf("Ethical Approval", "Informed Consent", "Confidentiality", "Declaration of Helsinki"), "Describe the ethical considerations from the PDF data."),
    "results" to Triple("CHAPTER_4", listOf("Demographic Profile", "Primary Outcome Results", "Secondary Outcome Results", "Subgroup Analysis", "Summary of Findings"),
        "Present the results with tables and charts for the key numeric findings. Every numeric claim must match the PDF data exactly."),
    "observations" to Triple("CHAPTER_4", listOf("Observations", "Findings"), "Present the observations with tables and charts from the PDF data."),
    "discussion" to Triple("CHAPTER_5", listOf("Summary of Findings", "Comparison with Literature", "Mechanisms", "Strengths", "Limitations", "Clinical Implications"),
        "Discuss the findings against the literature. Include a comparison table when the data supports one."),
    "conclusion" to Triple("CHAPTER_5", listOf("Conclusion", "Take-home Message"), "Conclude concisely from the PDF data."),
    "summary" to Triple("CHAPTER_5", listOf("Summary"), "Summarize the chapter content from the PDF data."),
    "recommendations" to Triple("CHAPTER_5", listOf("Recommendations"), "Give actionable recommendations from the PDF data."),
    "limitations" to Triple("CHAPTER_5", listOf("Limitations"), "List the limitations from the PDF data."),
    "future scope" to Triple("CHAPTER_5", listOf("Future Research Directions"), "Describe the future scope from the PDF data."),
    "abstract" to Triple("CHAPTER_0", listOf("Background", "Aim", "Methods", "Results", "Conclusion", "Keywords"), "Write a structured abstract (max 250 words) with keywords."),
    "keywords" to Triple("CHAPTER_0", listOf("Keywords"), "List 4-8 keywords.")
)

/** Builds the JSON schema for a chapter using the same structure as the thesis analyzer's professionalTextSchema. */
private fun chatChapterSchema(chapterName: String): String {
    val entry = CHAT_CHAPTERS[chapterName.lowercase().trim()]
        ?: Triple("CHAPTER_1", listOf("Background", "Aim", "Objectives", "Materials and Methods", "Results", "Discussion", "Conclusion"), "Write the chapter in formal thesis style using only the PDF data.")
    val (chapterType, sections, guidance) = entry
    val sectionObjects = sections.joinToString(",\n") { section ->
        """{"heading":"$section","content":"short section summary [1]","paragraphs":["Paragraph 1 with inline citation [1]","Paragraph 2 with inline citation [2]"],"bullets":["... [1]"],"numbered_points":["... [1]"],"subsections":[{"heading":"...","content":"... [1]"}],"table":{"table_number":"T1","title":"...","headers":["..."],"rows":[["... [1]"]]},"figures":[{"figure_number":"1","title":"...","caption":"...","image_search_query":"..."}],"references":[{"citation":"[1]","reference_text":"Author AA, Author BB. Complete article title. Journal Name. 2020;12(3):123-130. PMID: 12345678. DOI: 10.xxxx/xxxxx","pmid":"12345678","doi":"10.xxxx/xxxxx"}]}"""
    }
    return """
    {
      "chapter_name": "${chapterName.uppercase()}",
      "chapter_type": "$chapterType",
      "sections": [
$sectionObjects
      ],
      "tables": [{"table_number":"T1","title":"...","headers":["..."],"rows":[["..."]],"footnote":"..."}],
      "figures": [{"figure_number":"1","title":"...","caption":"...","image_search_query":"..."}],
      "charts": [{"chart_id":"chart_1","title":"...","type":"bar","labels":["..."],"values":[1],"data":[{"label":"...","value":1}]}],
      "abbreviations": [{"short":"BMI","full":"Body Mass Index"}],
      "chapter_references": [{"citation":"[1]","reference_text":"Author AA, Author BB. Complete article title. Journal Name. 2020;12(3):123-130. PMID: 12345678. DOI: 10.xxxx/xxxxx","pmid":"12345678","doi":"10.xxxx/xxxxx"}]
    }
    """.trimIndent()
}

/**
 * Detects a chapter-generation request. Only fires when the user explicitly asks for a chapter
 * (the word "chapter" or "thesis" plus a chapter name / generation verb), never for plain chat.
 */
private fun detectChapterRequest(text: String, pdfContext: PdfChatContext?): String? {
    // Require a PDF context — but allow even when variables is empty, because
    // the chapter generator can fall back to textPreview if extraction failed.
    if (pdfContext == null || pdfContext.textPreview.isBlank()) return null
    val lower = text.lowercase()
    val hasChapterWord = Regex("\\bchapter\\b").containsMatchIn(lower)
    val hasThesisWord = Regex("\\bthesis\\b").containsMatchIn(lower)
    if (!hasChapterWord && !hasThesisWord) return null

    // "chapter: <name>" / "chapter <name>"
    Regex("chapter\\s*:?\\s+([a-z][a-z ]{2,40})").find(lower)?.let { m ->
        normalizeChapterName(m.groupValues[1].trim())?.let { return it }
    }
    // "the <name> chapter" / "<name> chapter"
    Regex("(?:the\\s+)?([a-z][a-z ]{2,40})\\s+chapter").find(lower)?.let { m ->
        normalizeChapterName(m.groupValues[1].trim())?.let { return it }
    }
    // "write/generate ... <name>" (needs chapter/thesis word, checked above)
    for (name in CHAT_CHAPTERS.keys) {
        val escaped = Regex.escape(name)
        if (Regex("(?:generate|write|create|draft|make|prepare|produce).{0,30}$escaped").containsMatchIn(lower) ||
            Regex("$escaped\\s+chapter").containsMatchIn(lower)
        ) {
            return name
        }
    }
    // User said "chapter" or "thesis" with a PDF loaded but no specific chapter name was parsed.
    // Default to "methodology" — the most commonly requested chapter — so the module fires
    // rather than falling through to plain AI chat.
    val hasGenerateVerb = Regex("""(?:generate|write|create|draft|make|prepare|produce|build)\b""").containsMatchIn(lower)
    if (hasGenerateVerb) return "methodology"
    return null
}

private fun normalizeChapterName(raw: String): String? {
    val t = raw.trim().replace(Regex("\\s+"), " ").removeSuffix("chapter").trim()
    if (t.isEmpty()) return null
    CHAT_CHAPTERS.keys.firstOrNull { name -> t == name || t.contains(name) || name.contains(t) }?.let { return it }
    return t.takeIf { it.length in 3..40 && it.split(" ").size <= 4 }
}

private fun optStringList(o: JSONObject, key: String): List<String> =
    o.optJSONArray(key)?.let { a -> (0 until a.length()).mapNotNull { i -> a.optString(i).takeIf { it.isNotBlank() } } } ?: emptyList()

private fun parseChatTable(t: JSONObject): ChatTableJson = ChatTableJson(
    tableNumber = t.optString("table_number"),
    title = t.optString("title"),
    headers = optStringList(t, "headers"),
    rows = t.optJSONArray("rows")?.let { ra ->
        (0 until ra.length()).mapNotNull { i ->
            val row = ra.optJSONArray(i) ?: return@mapNotNull null
            (0 until row.length()).map { j -> row.optString(j) }
        }
    } ?: emptyList(),
    footnote = t.optString("footnote")
)

private fun parseChatFigures(arr: JSONArray?): List<ChatFigureJson> = arr?.let { a ->
    (0 until a.length()).mapNotNull { i ->
        val f = a.optJSONObject(i) ?: return@mapNotNull null
        ChatFigureJson(f.optString("figure_number"), f.optString("title"), f.optString("caption"), f.optString("image_search_query"))
    }
} ?: emptyList()

private fun parseChatReferences(arr: JSONArray?): List<ChatReferenceJson> = arr?.let { a ->
    (0 until a.length()).mapNotNull { i ->
        val r = a.optJSONObject(i) ?: return@mapNotNull null
        ChatReferenceJson(r.optString("citation"), r.optString("reference_text"), r.optString("pmid"), r.optString("doi"))
    }
} ?: emptyList()

/** Parses the LLM's JSON reply into a ChatChapterJson using the same keys as the thesis analyzer schemas. */
private fun parseChatChapter(raw: String): ChatChapterJson {
    var cleaned = raw.trim()
    cleaned = cleaned.removePrefix("```json").removePrefix("```").trim()
    cleaned = cleaned.removeSuffix("```").trim()
    val obj = JSONObject(cleaned)
    val sections = obj.optJSONArray("sections")?.let { arr ->
        (0 until arr.length()).mapNotNull { i ->
            val s = arr.optJSONObject(i) ?: return@mapNotNull null
            ChatSectionJson(
                heading = s.optString("heading"),
                content = s.optString("content"),
                paragraphs = optStringList(s, "paragraphs"),
                bullets = optStringList(s, "bullets"),
                numberedPoints = optStringList(s, "numbered_points"),
                subsections = s.optJSONArray("subsections")?.let { sa ->
                    (0 until sa.length()).mapNotNull { j ->
                        val sub = sa.optJSONObject(j) ?: return@mapNotNull null
                        ChatSubsectionJson(sub.optString("heading"), sub.optString("content"), optStringList(sub, "paragraphs"))
                    }
                } ?: emptyList(),
                table = s.optJSONObject("table")?.let { parseChatTable(it) },
                figures = parseChatFigures(s.optJSONArray("figures")),
                references = parseChatReferences(s.optJSONArray("references"))
            )
        }
    } ?: emptyList()
    return ChatChapterJson(
        chapterName = obj.optString("chapter_name"),
        chapterType = obj.optString("chapter_type"),
        sections = sections,
        tables = obj.optJSONArray("tables")?.let { arr -> (0 until arr.length()).mapNotNull { i -> arr.optJSONObject(i)?.let { parseChatTable(it) } } } ?: emptyList(),
        figures = parseChatFigures(obj.optJSONArray("figures")),
        charts = obj.optJSONArray("charts")?.let { arr ->
            (0 until arr.length()).mapNotNull { i ->
                val c = arr.optJSONObject(i) ?: return@mapNotNull null
                ChatChartJson(
                    chartId = c.optString("chart_id"),
                    title = c.optString("title"),
                    type = c.optString("type"),
                    labels = optStringList(c, "labels"),
                    values = c.optJSONArray("values")?.let { va ->
                        (0 until va.length()).mapNotNull { k -> va.optDouble(k).takeIf { !va.isNull(k) } }
                    } ?: emptyList(),
                    data = c.optJSONArray("data")?.let { da ->
                        (0 until da.length()).mapNotNull { k ->
                            val p = da.optJSONObject(k) ?: return@mapNotNull null
                            ChatChartPointJson(p.optString("label"), p.optDouble("value"))
                        }
                    } ?: emptyList()
                )
            }
        } ?: emptyList(),
        abbreviations = obj.optJSONArray("abbreviations")?.let { arr ->
            (0 until arr.length()).mapNotNull { i ->
                val a = arr.optJSONObject(i) ?: return@mapNotNull null
                ChatAbbreviationJson(a.optString("short"), a.optString("full"))
            }
        } ?: emptyList(),
        references = parseChatReferences(obj.optJSONArray("chapter_references"))
    )
}

/** Generates a thesis chapter from the uploaded PDF using the matching chapter schema. */
private suspend fun runChapterGeneration(
    ownerTurn: Int,
    chapterName: String,
    pdfContext: PdfChatContext,
    context: Context,
    onUpdate: (ChapterGenState) -> Unit
): ChapterGenState {
    var state = ChapterGenState(ownerTurn = ownerTurn, chapterName = chapterName, phase = 1, note = "📚 Generating the $chapterName chapter from your PDF…")
    onUpdate(state)
    return try {
        val schema = chatChapterSchema(chapterName)
        val guidance = CHAT_CHAPTERS[chapterName.lowercase().trim()]?.third ?: "Write the chapter in formal thesis style using only the PDF data."
        val prompt = buildString {
            appendLine("The user uploaded a thesis PDF and asked you to generate the \"$chapterName\" chapter as a medical thesis chapter.")
            appendLine("Chapter guidance: $guidance")
            appendLine()
            appendLine("Return ONLY valid JSON. Do not put markdown fences or prose outside the JSON.")
            appendLine("Follow this JSON schema exactly:")
            appendLine(schema)
            appendLine()
            appendLine("Rules:")
            appendLine("- Use only information present in the PDF variables above. Never invent data, statistics, or references.")
            appendLine("- Write formal thesis-style narrative. Put complete body text in each section's `paragraphs` array; use `content` only as a short summary.")
            appendLine("- For every factual claim, add inline Vancouver citation labels like [1] in the text.")
            appendLine("- Add a `figure` whenever a figure naturally supports this chapter (pathology diagram, study design flowchart, treatment algorithm, etc.) with a concrete `image_search_query` that could retrieve the image, and add 3-5 explanatory points about the figure in the nearby text.")
            appendLine("- Add a `table` whenever tabular data (demographics, investigations, comparisons, results) is present in the PDF.")
            appendLine("- Add a `chart` (type bar/line/pie) with `labels` and `values` whenever numeric data supports one and the user asked for it or a chart would clarify the results.")
            appendLine("- Keep section headings exactly as given in the schema. Do not invent extra top-level keys.")
        }
        val messages = buildList {
            pdfContext.contextPrompt().takeIf { it.isNotBlank() }?.let { add(Message("system", it)) }
            add(Message("user", prompt))
        }
        val raw = rotateAiRequest(messages, maxTokens = 8000, source = "ai_chat_chapter")
        Log.i(CHAPTER_LOG_TAG, "raw chapter reply (${raw.length} chars) for $chapterName")
        // JSON session log: full chapter request (prompt + schema) and the raw LLM reply.
        appendChatLog(
            context,
            JSONObject()
                .put("type", "chapter_request")
                .put("chapter_name", chapterName)
                .put("pdf", pdfContext.fileName)
                .put("schema", schema)
                .put("prompt", prompt)
                .put("raw_reply", raw)
        )
        val json = parseChatChapter(raw)
        state = state.copy(phase = 2, json = json, note = "")
        onUpdate(state)
        state
    } catch (e: Throwable) {
        Log.e(CHAPTER_LOG_TAG, "chapter generation failed: ${e.message}", e)
        appendChatLog(
            context,
            JSONObject()
                .put("type", "chapter_error")
                .put("chapter_name", chapterName)
                .put("error", e.message ?: "Chapter generation failed")
                .put("stack", e.stackTraceToString().take(2000))
        )
        state = state.copy(phase = 3, error = e.message ?: "Chapter generation failed")
        onUpdate(state)
        state
    }
}

private suspend fun requestAiChat(history: List<ChatTurn>, pdfContext: PdfChatContext?): String {
    val messages = buildList {
        pdfContext?.contextPrompt()?.takeIf { it.isNotBlank() }?.let { prompt ->
            add(Message("system", prompt))
        }
        add(Message("system", AI_CHAT_SYSTEM_PROMPT))
        history.forEach { add(Message(it.role, it.content)) }
    }
    return rotateAiRequest(messages, maxTokens = 2000, source = "ai_chat")
}

/** Short classification call: returns (topic, subject) guessed for a question. */
private suspend fun requestTopicLabel(questionText: String): Pair<String, String> {
    val system = "You classify NEET PG medical MCQs into a concise topic and a medical subject discipline."
    val user = "Question:\n$questionText\n\nReply with exactly two lines:\nTOPIC: <2-4 word topic, e.g. Glaucoma>\nSUBJECT: <medical discipline, e.g. Ophthalmology>"
    val raw = rotateAiRequest(
        listOf(Message("system", system), Message("user", user)),
        maxTokens = 60,
        source = "ai_chat_topic_label"
    )
    val topic = Regex("""TOPIC:\s*(.+)""", RegexOption.IGNORE_CASE).find(raw)
        ?.groupValues?.get(1)?.trim().orEmpty()
    val subject = Regex("""SUBJECT:\s*(.+)""", RegexOption.IGNORE_CASE).find(raw)
        ?.groupValues?.get(1)?.trim().orEmpty()
    return topic to subject
}

/** Shared provider rotation used by chat + topic tagging. */
/** Fast LLM-based intent classifier — uses Groq/Cerebras for <500ms latency. */
private suspend fun classifyIntent(userText: String, pdfLoaded: Boolean): IntentDecision {
    val contextNote = if (pdfLoaded) "User has a PDF uploaded." else "No PDF uploaded."
    val prompt = "Context: $contextNote\nUser message: ${userText.take(1500)}"
    return try {
        val raw = withContext(Dispatchers.IO) {
            rotateAiRequestFast(listOf(
                Message("system", INTENT_CLASSIFICATION_SYSTEM),
                Message("user", prompt)
            ))
        }
        val trimmed = raw.trim().removePrefix("```json").removePrefix("```").removeSuffix("```").trim()
        val first = trimmed.indexOf('{')
        val last = trimmed.lastIndexOf('}')
        if (first < 0 || last <= first) throw IllegalStateException("No JSON in response")
        val obj = JSONObject(trimmed.substring(first, last + 1))
        val mod = obj.optString("module", "chat")
            .takeIf { it in setOf("poster", "chapter", "thesis_search", "citation", "chat") } ?: "chat"
        IntentDecision(
            module = mod,
            chapterName = obj.optString("chapter_name", "").trim().ifBlank { "methodology" },
            thesisQuery = obj.optString("thesis_query", "").trim(),
            keyword = obj.optString("keyword", "").trim().ifBlank { extractEarlyKeyword(userText).orEmpty() },
            runChat = obj.optBoolean("run_chat", true)
        ).also { Log.i("AiChatIntent", "classified: module=${it.module} chapter=${it.chapterName} kw=${it.keyword} runChat=${it.runChat}") }
    } catch (e: Throwable) {
        Log.w("AiChatIntent", "classifyIntent failed, using regex fallback: ${e.message}")
        // Fallback: regex detection so the app never hard-breaks
        val posterSrc = detectPosterAbstract(userText, null)
        val chapterNm = detectChapterRequest(userText, null)
        val thesisTxt = detectThesisTopicSearch(userText)
        val mod = when {
            posterSrc != null -> "poster"
            chapterNm != null -> "chapter"
            thesisTxt != null -> "thesis_search"
            else -> "chat"
        }
        IntentDecision(
            module = mod,
            chapterName = chapterNm ?: "methodology",
            thesisQuery = thesisTxt ?: "",
            keyword = extractEarlyKeyword(userText).orEmpty(),
            runChat = mod == "chat" || mod == "thesis_search" || mod == "citation"
        )
    }
}

/** Like rotateAiRequest but restricted to fast providers (Groq/Cerebras) for sub-second calls. */
private suspend fun rotateAiRequestFast(messages: List<Message>): String {
    val fastProviders = setOf("groq", "cerebras")
    for (candidate in ModelRotator.buildPool("auto")) {
        if (candidate.provider !in fastProviders) continue
        val apiKey = when (candidate.provider) {
            "groq" -> ApiKeys.GROQ_API_KEY
            "cerebras" -> ApiKeys.CEREBRAS_API_KEY
            else -> ""
        }.trim()
        if (apiKey.isBlank()) continue
        try {
            val request = ChatRequest(model = candidate.model, messages = messages, temperature = 0.0, maxTokens = 200)
            val response = when (candidate.provider) {
                "groq" -> ApiClient.groqApi.chatCompletion("openai/v1/chat/completions", "Bearer $apiKey", request)
                "cerebras" -> ApiClient.cerebrasApi.chatCompletion("v1/chat/completions", "Bearer $apiKey", request)
                else -> continue
            }
            return response.choices.firstOrNull()?.message?.content.orEmpty().trim()
        } catch (_: Throwable) { continue }
    }
    // No fast provider available — fall back to normal rotation
    return rotateAiRequest(messages, maxTokens = 200, source = "intent_classify")
}

private suspend fun rotateAiRequest(messages: List<Message>, maxTokens: Int, source: String = "ai_chat"): String {
    val errors = mutableListOf<String>()
    for (candidate in ModelRotator.buildPool("auto")) {
        if (candidate.provider !in setOf("groq", "openrouter", "deepseek", "mistral", "cerebras")) continue
        val apiKey = when (candidate.provider) {
            "groq" -> ApiKeys.GROQ_API_KEY
            "openrouter" -> ApiKeys.OPENROUTER_API_KEY
            "deepseek" -> ApiKeys.DEEPSEEK_API_KEY
            "mistral" -> ApiKeys.MISTRAL_API_KEY
            "cerebras" -> ApiKeys.CEREBRAS_API_KEY
            else -> ""
        }.trim()
        if (apiKey.isBlank()) continue

        val startedAt = System.currentTimeMillis()
        try {
            val request = ChatRequest(
                model = candidate.model,
                messages = messages,
                temperature = 0.3,
                maxTokens = maxTokens
            )
            val response = when (candidate.provider) {
                "groq" -> ApiClient.groqApi.chatCompletion("openai/v1/chat/completions", "Bearer $apiKey", request)
                "openrouter" -> ApiClient.openRouterApi.chatCompletion("api/v1/chat/completions", "Bearer $apiKey", request)
                "deepseek" -> ApiClient.deepSeekApi.chatCompletion("chat/completions", "Bearer $apiKey", request)
                "mistral" -> ApiClient.mistralApi.chatCompletion("v1/chat/completions", "Bearer $apiKey", request)
                "cerebras" -> ApiClient.cerebrasApi.chatCompletion("v1/chat/completions", "Bearer $apiKey", request)
                else -> error("Unsupported provider")
            }
            val content = response.choices.firstOrNull()?.message?.content?.trim().orEmpty()
            if (content.isNotBlank()) {
                // Save the exchange for model training.
                AiTrainingLogger.log(
                    source = source,
                    provider = candidate.provider,
                    model = candidate.model,
                    prompt = messages.joinToString("\n\n") { "[${it.role}] ${it.content}" },
                    response = content,
                    status = "completed",
                    durationMs = System.currentTimeMillis() - startedAt
                )
                return content
            }
            errors += "${candidate.provider}/${candidate.model}: empty response"
        } catch (e: Throwable) {
            errors += "${candidate.provider}/${candidate.model}: ${e.message}"
        }
    }
    error(errors.joinToString(" | ").ifBlank { "No usable AI provider" })
}

// ---------------------------------------------------------------- Poster generation backend

/**
 * Text LLM call restricted to FREE models only (OpenRouter :free pool + Groq free tier).
 * Used for the poster analysis step — never charges the user.
 */
private suspend fun rotateFreeAiRequest(messages: List<Message>, maxTokens: Int, source: String = "ai_chat_poster"): String {
    val errors = mutableListOf<String>()
    for (candidate in freeTextCandidates()) {
        val apiKey = when (candidate.provider) {
            "openrouter" -> ApiKeys.OPENROUTER_API_KEY
            "groq" -> ApiKeys.GROQ_API_KEY
            else -> ""
        }.trim()
        if (apiKey.isBlank()) continue
        val startedAt = System.currentTimeMillis()
        try {
            val request = ChatRequest(
                model = candidate.model,
                messages = messages,
                temperature = 0.3,
                maxTokens = maxTokens
            )
            val response = when (candidate.provider) {
                "openrouter" -> ApiClient.openRouterApi.chatCompletion("api/v1/chat/completions", "Bearer $apiKey", request)
                "groq" -> ApiClient.groqApi.chatCompletion("openai/v1/chat/completions", "Bearer $apiKey", request)
                else -> error("Unsupported provider")
            }
            val content = response.choices.firstOrNull()?.message?.content?.trim().orEmpty()
            if (content.isNotBlank()) {
                AiTrainingLogger.log(
                    source = source,
                    provider = candidate.provider,
                    model = candidate.model,
                    prompt = messages.joinToString("\n\n") { "[${it.role}] ${it.content}" },
                    response = content,
                    status = "completed",
                    durationMs = System.currentTimeMillis() - startedAt
                )
                return content
            }
            errors += "${candidate.provider}/${candidate.model}: empty response"
        } catch (e: Throwable) {
            errors += "${candidate.provider}/${candidate.model}: ${e.message}"
        }
    }
    error(errors.joinToString(" | ").ifBlank { "No free AI provider available" })
}

/** Free-only candidate pool: OpenRouter dynamic list filtered to :free + fallbacks, then Groq free tier. */
private fun freeTextCandidates(): List<ModelCandidate> {
    val dynamic = ModelRotator.buildPool("openrouter").map { it.model }
    val orModels = (dynamic + FALLBACK_FREE_OR_MODELS).distinct()
        .filter { it.contains(":free") || it == "openrouter/free" }
    val out = mutableListOf<ModelCandidate>()
    orModels.forEach { out += ModelCandidate("openrouter", it) }
    GROQ_FREE_MODELS.forEach { out += ModelCandidate("groq", it) }
    return out
}

/**
 * Runs the two-phase poster pipeline: (1) free text LLM builds the complete poster data
 * from the abstract, (2) the OpenRouter image model renders it as a poster image.
 * @param emit called on the main thread with the updated immutable state (Compose-safe).
 */
private suspend fun runPosterGeneration(
    abstractSource: String,
    emit: (PosterGenState) -> Unit
): PosterGenState {
    var current = PosterGenState(ownerTurn = -1, source = abstractSource, phase = 1, note = "🧠 Analyzing abstract & building poster data…")
    emit(current)
    Log.i(POSTER_LOG_TAG, "phase 1: analyzing abstract (${abstractSource.length} chars)")

    val data = try {
        val raw = rotateFreeAiRequest(
            listOf(Message("system", POSTER_ANALYSIS_SYSTEM), Message("user", abstractSource)),
            maxTokens = 2600,
            source = "ai_chat_poster_analysis"
        )
        Log.i(POSTER_LOG_TAG, "phase 1 done, raw length=${raw.length}")
        parsePosterAnalysisData(raw)
    } catch (e: Throwable) {
        Log.e(POSTER_LOG_TAG, "phase 1 failed", e)
        current = current.copy(phase = 4, note = "Poster analysis failed", error = e.message ?: "unknown error")
        emit(current)
        return current
    }

    if (data.title.isBlank() && data.sections.isEmpty()) {
        current = current.copy(phase = 4, note = "Poster analysis failed", error = "The AI returned no usable poster data.")
        emit(current)
        return current
    }

    current = current.copy(phase = 2, note = "🎨 Generating poster image with AI…", data = data)
    emit(current)
    Log.i(POSTER_LOG_TAG, "phase 2: generating image (sections=${data.sections.size})")

    val image = try {
        // generatePosterImage is a blocking OkHttp call — must run off the main thread.
        withContext(Dispatchers.IO) { generatePosterImage(buildPosterImagePrompt(data)) }
    } catch (e: Throwable) {
        Log.e(POSTER_LOG_TAG, "phase 2 failed: ${e.message}", e)
        current = current.copy(phase = 4, note = "Poster image generation failed", error = e.message ?: "image error", data = data)
        emit(current)
        return current
    }

    current = current.copy(phase = 3, note = "Poster ready", data = data, imageUrl = image.first, imageFile = image.second)
    emit(current)
    Log.i(POSTER_LOG_TAG, "phase 3 done: url=${image.first?.take(80)} file=${image.second?.name} exists=${image.second?.exists()}")
    return current
}

private const val POSTER_LOG_TAG = "PosterGen"

/** A question's topic needs AI assignment when it is blank or a placeholder like "PG 2020". */
private fun needsAiTopic(q: RelatedQuestion): Boolean {
    val t = q.topic.trim()
    if (t.isEmpty()) return true
    return Regex("[0-9]{4}|^PG|^Neet|^pg$", RegexOption.IGNORE_CASE).containsMatchIn(t)
}

/** Old bulk imports used exam names ("NEET PG", "Neet pg 2020") in the subject column. */
private fun isPaperLikeSubject(subject: String): Boolean {
    val s = subject.trim().lowercase()
    return s.isEmpty() || s.contains("neet pg") || Regex("\\d").containsMatchIn(s)
}

/** Persists an AI-chosen topic (+ optional subject) via update_question_topic.php. */
private fun postTopicAssignment(questionId: Int, topic: String, subject: String): Boolean = runCatching {
    val form = okhttp3.FormBody.Builder()
        .add("question_id", questionId.toString())
        .add("topic", topic)
        .add("subject", subject)
        .build()
    val request = Request.Builder()
        .url("https://medigyaan.xyz/Neurons/api/update_question_topic.php")
        .post(form)
        .build()
    httpClient.newCall(request).execute().use { response ->
        val body = response.body?.string().orEmpty()
        response.isSuccessful && JSONObject(body).optBoolean("success", false)
    }
}.getOrDefault(false)

/** A question needs an AI-written explanation when it is missing or very short (< 100 chars). */
private fun needsAiExplanation(q: RelatedQuestion): Boolean {
    val e = q.explanation.trim()
    return e.isEmpty() || e.length < 100
}

/**
 * Short AI call: given the full question and its current (possibly weak/missing)
 * explanation, returns a brief but complete explanation that teaches the concept.
 */
private suspend fun requestExplanation(questionText: String, currentExplanation: String): String {
    val system = "You are a concise medical teacher. Given an exam MCQ and its current (possibly weak or missing) explanation, write a brief but complete explanation that teaches the concept being tested."
    val user = buildString {
        appendLine("Question:")
        appendLine(questionText)
        appendLine()
        append("Current explanation: ")
        appendLine(currentExplanation.ifBlank { "(none)" })
        appendLine()
        append("Write a brief, correct explanation — 1 or 2 clear sentences. Reply with the explanation text only: no labels, no prefixes like 'Explanation:', no extra commentary.")
    }
    return rotateAiRequest(
        listOf(Message("system", system), Message("user", user)),
        maxTokens = 220,
        source = "ai_chat_explanation"
    ).trim()
}

/** Persists an AI-written explanation via update_question_explanation.php (server keeps existing good ones). */
private fun postExplanation(questionId: Int, explanation: String): Boolean = runCatching {
    val form = okhttp3.FormBody.Builder()
        .add("question_id", questionId.toString())
        .add("explanation", explanation)
        .build()
    val request = Request.Builder()
        .url("https://medigyaan.xyz/Neurons/api/update_question_explanation.php")
        .post(form)
        .build()
    httpClient.newCall(request).execute().use { response ->
        val body = response.body?.string().orEmpty()
        response.isSuccessful && JSONObject(body).optBoolean("success", false)
    }
}.getOrDefault(false)

/** Pulls the [SEARCH: keyword] marker the model was asked to append. */
private fun parseSearchKeyword(raw: String): String? {
    val regex = Regex("""\[SEARCH:\s*([^\]]{2,80})\]""", RegexOption.IGNORE_CASE)
    val m = regex.find(raw) ?: return null
    return m.groupValues[1].trim().trimEnd('.', ',', '!', '?').ifBlank { null }
}

/**
 * Derives a search keyword directly from the user's message, without waiting for the AI reply.
 * Used to fire related-question and community-post searches immediately for every request,
 * including poster/chapter generation requests that would otherwise skip the AI chat path.
 *
 * Strategy:
 *  1. Strip common command prefixes (generate/create/make/explain/tell me about…).
 *  2. Tokenize, drop stop words and very short tokens.
 *  3. Return the best 2-3 tokens joined, or null if nothing meaningful remains.
 */
private fun extractEarlyKeyword(userText: String): String? {
    val stripped = userText.trim()
        .replace(Regex("""(?i)^(please\s+)?(generate|make|create|design|build|prepare|draft|write|explain|describe|tell me about|what is|what are|give me|show me|list|define|summarize|summarise|search for|find|get)\s+"""), "")
        .replace(Regex("""(?i)\b(poster|chapter|thesis|abstract|reference|citation|a|an|the)\b"""), " ")
        .replace(Regex("[^a-zA-Z0-9 ]"), " ")
        .trim()
    val tokens = stripped.lowercase().split(" ")
        .map { it.trim() }
        .filter { it.length > 2 && it !in SEARCH_STOP_WORDS }
        .distinct()
    if (tokens.isEmpty()) return null
    return tokens.take(3).joinToString(" ").ifBlank { null }
}

/** Client-side keyword tokens from the user text, used if the model forgot its [SEARCH:] marker. */
private fun fallbackKeywords(userText: String): List<String> {
    return userText
        .lowercase()
        .replace(Regex("[^a-z0-9 ]"), " ")
        .split(" ")
        .filter { it.isNotBlank() && it.length > 2 && it !in SEARCH_STOP_WORDS }
        .distinct()
}

private val httpClient = OkHttpClient.Builder()
    .connectTimeout(25, TimeUnit.SECONDS)
    .readTimeout(25, TimeUnit.SECONDS)
    .build()

/** Image generation can take 30-90s — use a generous client. */
private val imageHttpClient = OkHttpClient.Builder()
    .connectTimeout(60, TimeUnit.SECONDS)
    .readTimeout(180, TimeUnit.SECONDS)
    .writeTimeout(60, TimeUnit.SECONDS)
    .build()

/** Parses the poster JSON returned by the free analysis model. */
private fun parsePosterAnalysisData(raw: String): PosterAnalysisData {
    var trimmed = raw.trim()
        .removePrefix("```json").removePrefix("```").removeSuffix("```")
        .trim()
    val first = trimmed.indexOf('{')
    val last = trimmed.lastIndexOf('}')
    if (first < 0 || last <= first) return PosterAnalysisData("", "")
    trimmed = trimmed.substring(first, last + 1)
    val obj = JSONObject(trimmed)
    val title = obj.optString("title", "").trim()
    val subtitle = obj.optString("subtitle", "").trim()
    val sections = mutableListOf<PosterSectionData>()
    val arr = obj.optJSONArray("sections") ?: JSONArray()
    for (i in 0 until arr.length()) {
        val s = arr.optJSONObject(i) ?: continue
        val h = s.optString("heading", "").trim()
        val b = s.optString("body", "").trim()
        if (h.isNotBlank() && b.isNotBlank()) sections += PosterSectionData(h, b)
    }
    return PosterAnalysisData(title, subtitle, sections)
}

/** Turns the structured poster data into a detailed image-generation prompt. */
private fun buildPosterImagePrompt(data: PosterAnalysisData): String {
    val sb = StringBuilder()
    sb.append("Create a professional medical research conference poster as a single clean, readable image. ")
    sb.append("Portrait layout. Use a modern academic design: a bold colored header band across the top with the title, ")
    sb.append("a subtitle line under it, then the content organized in clear columns/boxes with section headings. ")
    sb.append("Use a calm medical color palette (deep blue/teal with white and soft accents). Avoid generic clipart; ")
    sb.append("use subtle medical line icons or a clean geometric motif. Make all text legible and correctly spelled. ")
    sb.append("POSTER TITLE: \"").append(data.title.ifBlank { "Medical Research Poster" }).append("\". ")
    if (data.subtitle.isNotBlank()) sb.append("SUBTITLE: \"").append(data.subtitle).append("\". ")
    sb.append("SECTIONS:\n")
    data.sections.forEachIndexed { i, s ->
        sb.append(i + 1).append(". \"").append(s.heading).append("\": ")
            .append(s.body.replace("\"", "'")).append("\n")
    }
    return sb.toString().trim()
}

/**
 * Calls the OpenRouter images/generations endpoint with the cheapest image model.
 * Returns (url, file) — b64_json responses are decoded into a temp file.
 */
private fun generatePosterImage(prompt: String): Pair<String?, File> {
    val json = JSONObject()
        .put("model", POSTER_IMAGE_MODEL)
        .put("prompt", prompt)
        .put("n", 1)
        .put("size", POSTER_IMAGE_SIZE)
    val request = Request.Builder()
        .url("https://openrouter.ai/api/v1/images/generations")
        .addHeader("Authorization", "Bearer ${ApiKeys.OPENROUTER_API_KEY}")
        .addHeader("X-Title", "MediGyaan AI")
        .addHeader("Accept", "application/json")
        .post(json.toString().toRequestBody("application/json".toMediaType()))
        .build()
    Log.i(POSTER_LOG_TAG, "POST images/generations model=$POSTER_IMAGE_MODEL promptChars=${prompt.length}")
    val startedAt = System.currentTimeMillis()
    imageHttpClient.newCall(request).execute().use { response ->
        val raw = response.body?.string().orEmpty()
        Log.i(POSTER_LOG_TAG, "images/generations -> HTTP ${response.code} in ${System.currentTimeMillis() - startedAt}ms bodyLen=${raw.length}")
        if (!response.isSuccessful) error("Image API HTTP ${response.code}: ${raw.take(300)}")
        val root = JSONObject(raw)
        val arr = root.optJSONArray("data") ?: error("Image API returned no data: ${raw.take(300)}")
        val item = arr.optJSONObject(0) ?: error("Image API returned empty data")
        val url = item.optString("url", "").takeIf { it.isNotBlank() }
        val b64 = item.optString("b64_json", "").takeIf { it.isNotBlank() }
        if (url != null) return url to File("")
        if (b64 != null) {
            val bytes = try {
                android.util.Base64.decode(b64, android.util.Base64.DEFAULT)
            } catch (e: Throwable) {
                Log.e(POSTER_LOG_TAG, "base64 decode failed: ${e.message}")
                throw e
            }
            Log.i(POSTER_LOG_TAG, "decoded b64 -> ${bytes.size} bytes")
            val f = File.createTempFile("medigyaan_poster_", ".png")
            f.writeBytes(bytes)
            return null to f
        }
        error("Image API returned neither url nor b64_json")
    }
}

/**
 * Detects a poster request and returns the abstract source text, or null.
 * Priority: pasted abstract in the message > abstract mentioned > uploaded PDF context.
 */
private fun detectPosterAbstract(userText: String, pdfContext: PdfChatContext?): String? {
    val trimmed = userText.trim()
    val lower = trimmed.lowercase()
    // Trigger on "poster" OR common generation verbs that imply poster intent
    val hasPosterWord = Regex("""\b(poster|posters)\b""").containsMatchIn(lower)
    if (!hasPosterWord) return null
    val stripped = POSTER_COMMAND_PREFIX.replace(trimmed, "").trim()
    val mentionsAbstract = Regex("""\babstract\b""").containsMatchIn(lower)
    // User pasted content inline (long enough)
    if (stripped.length >= 250) return stripped.take(8000)
    if (stripped.length >= 60 && mentionsAbstract) return stripped.take(8000)
    // PDF loaded → use it as the source even if the message is short ("generate poster", "make poster")
    if (pdfContext != null && pdfContext.textPreview.isNotBlank()) return buildPosterAbstractFromPdf(pdfContext)
    // Short message, no PDF → return null so the user sees the AI ask them to paste the abstract
    return null
}

/** Builds an abstract source from the uploaded PDF chat context. */
private fun buildPosterAbstractFromPdf(pdf: PdfChatContext): String {
    val sb = StringBuilder()
    pdf.variables.firstOrNull { it.name.equals("Title", ignoreCase = true) }?.value
        ?.takeIf { it.isNotBlank() }?.let { sb.append("Title: ").append(it).append("\n\n") }
    pdf.variables.firstOrNull { it.name.contains("Abstract", ignoreCase = true) }?.value
        ?.takeIf { it.isNotBlank() }?.let { sb.append(it).append("\n\n") }

    // If we didn't get an Abstract variable (e.g. extraction failed), try pulling the abstract
    // section heuristically from the raw text preview before falling back to the whole preview.
    val hasAbstractContent = sb.length > (if (sb.startsWith("Title:")) 30 else 10)
    if (!hasAbstractContent) {
        val preview = pdf.textPreview
        // Look for an "Abstract" or "Summary" section header in the raw text.
        val abstractMatch = Regex(
            """(?im)^\s*(?:abstract|structured\s+abstract|summary)\s*[:\n]""",
            setOf(RegexOption.MULTILINE, RegexOption.IGNORE_CASE)
        ).find(preview)
        if (abstractMatch != null) {
            // Take up to 3 000 chars from the abstract heading onwards (likely captures the full abstract).
            sb.append(preview.substring(abstractMatch.range.first).take(3000))
        } else {
            // No heading found — use the first 3 000 chars of the raw text as-is.
            sb.append(preview.take(3000))
        }
    } else {
        // We have enough structured content; append a short raw text tail for extra context.
        sb.append(pdf.textPreview.take(1500))
    }
    return sb.toString().trim().take(8000)
}

/** Reads the server-side poster quota for this user (5 free posters). Null = quota unknown (allow). */
private fun fetchPosterQuota(context: Context): Int? = runCatching {
    val userId = context.getSharedPreferences("MY_APP", Context.MODE_PRIVATE).getInt("user_id", 0)
    val url = "https://medigyaan.xyz/Neurons/api/poster_credits.php?action=check&user_id=$userId"
    val request = Request.Builder()
        .url(url)
        .addHeader("X-App-Signature", "EduLabsRTM_Secure_v1_2026")
        .addHeader("Accept", "application/json")
        .get()
        .build()
    httpClient.newCall(request).execute().use { response ->
        val body = response.body?.string().orEmpty()
        if (!response.isSuccessful) return null
        val root = JSONObject(body)
        if (!root.optBoolean("success", false)) return null
        root.optInt("remaining", -1).takeIf { it >= 0 }
    }
}.getOrNull()

/** Decrements the server-side quota after a successful poster generation. Returns new remaining. */
private fun consumePosterQuota(context: Context): Int? = runCatching {
    val userId = context.getSharedPreferences("MY_APP", Context.MODE_PRIVATE).getInt("user_id", 0)
    val form = okhttp3.FormBody.Builder()
        .add("user_id", userId.toString())
        .build()
    val request = Request.Builder()
        .url("https://medigyaan.xyz/Neurons/api/poster_credits.php?action=consume")
        .addHeader("X-App-Signature", "EduLabsRTM_Secure_v1_2026")
        .addHeader("Accept", "application/json")
        .post(form)
        .build()
    httpClient.newCall(request).execute().use { response ->
        val body = response.body?.string().orEmpty()
        if (!response.isSuccessful) return null
        val root = JSONObject(body)
        if (!root.optBoolean("success", false)) return null
        root.optInt("remaining", -1).takeIf { it >= 0 }
    }
}.getOrNull()

/** Downloads the poster image (or uses the temp file) and saves it to Pictures/MediGyaan. */
private suspend fun downloadAndSavePoster(context: Context, url: String?, file: File?, title: String) {
    val bytes: ByteArray? = try {
        withContext(Dispatchers.IO) {
            when {
                file != null && file.exists() -> file.readBytes()
                !url.isNullOrBlank() -> imageHttpClient.newCall(Request.Builder().url(url).get().build()).execute().use { it.body?.bytes() }
                else -> null
            }
        }
    } catch (e: Throwable) {
        null
    }
    if (bytes == null || bytes.isEmpty()) {
        Toast.makeText(context, "Could not download the poster image", Toast.LENGTH_SHORT).show()
        return
    }
    try {
        val displayName = "poster_${System.currentTimeMillis()}.png"
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, displayName)
                put(MediaStore.Images.Media.MIME_TYPE, "image/png")
                put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/MediGyaan")
            }
            val uri = context.contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
            if (uri != null) {
                context.contentResolver.openOutputStream(uri)?.use { it.write(bytes) }
                Toast.makeText(context, "Poster saved to Pictures/MediGyaan", Toast.LENGTH_SHORT).show()
                return
            }
        }
        Toast.makeText(context, "Saving needs Android 10+. Poster is shown above — take a screenshot.", Toast.LENGTH_LONG).show()
    } catch (e: Throwable) {
        Toast.makeText(context, "Could not save poster: ${e.message?.take(60)}", Toast.LENGTH_SHORT).show()
    }
}

/**
 * Searches the 280k question bank for related questions.
 * The AI keyword sometimes arrives as a phrase the full-text matcher can't hit
 * (e.g. "glaucoma causes treatment"), so we also try each meaningful single word
 * and the tokens of the user's question, merging results across candidates.
 */
private fun findRelatedQuestions(context: Context, aiKeyword: String?, userText: String): QuestionSet? {
    val candidates = linkedSetOf<String>()
    aiKeyword?.takeIf { it.length >= 2 }?.let { candidates.add(it) }
    aiKeyword?.split(" ")?.forEach { token ->
        val t = token.trim().lowercase()
        if (t.length > 2 && t !in SEARCH_STOP_WORDS) candidates.add(t)
    }
    fallbackKeywords(userText).forEach { candidates.add(it) }

    val merged = LinkedHashMap<Int, RelatedQuestion>()
    var successLabel = ""
    for (candidate in candidates) {
        val results = searchQuestionsForKeyword(context, candidate) ?: emptyList()
        if (results.isNotEmpty() && successLabel.isBlank()) successLabel = candidate
        results.forEach { q -> if (!merged.containsKey(q.id)) merged[q.id] = q }
        // Stop once we have enough coverage so a bad tail candidate doesn't slow things down
        if (merged.size >= 12) break
    }
    if (merged.isEmpty()) return null
    val ordered = merged.values.toList()
    return QuestionSet(
        keyword = successLabel,
        questions = ordered,
        testIds = ordered.map { it.id }.take(15),
        primarySubject = ordered.firstOrNull { it.subject.isNotBlank() }?.subject ?: "NEET PG"
    )
}

/** Full-text search of the 280k question bank via Neurons searchv2 for a single keyword. */
private fun searchQuestionsForKeyword(context: Context, keyword: String): List<RelatedQuestion>? {
    val userId = context.getSharedPreferences("MY_APP", Context.MODE_PRIVATE).getInt("user_id", 0)
    val url = "https://medigyaan.xyz/Neurons/api/searchv2.php?keyword=${URLEncoder.encode(keyword, "UTF-8")}&type=json&user_id=$userId"
    val request = Request.Builder()
        .url(url)
        .addHeader("X-App-Signature", "EduLabsRTM_Secure_v1_2026")
        .addHeader("Accept", "application/json")
        .get()
        .build()
    return try {
        httpClient.newCall(request).execute().use { response ->
            val body = response.body?.string().orEmpty()
            if (!response.isSuccessful) return null
            val root = JSONObject(body)
            if (root.optString("status") != "success") return null

            val questions = mutableListOf<RelatedQuestion>()
            val qArray: JSONArray = root.optJSONObject("results")
                ?.optJSONArray("questions")
                ?: JSONArray()
            for (i in 0 until qArray.length()) {
                val q = qArray.optJSONObject(i) ?: continue
                val id = q.optInt("question_id", 0)
                if (id <= 0) continue
                val text = q.optString("question", "").trim()
                if (text.isBlank()) continue
                questions.add(
                    RelatedQuestion(
                        id = id,
                        text = text,
                        subject = q.optString("subject", "").trim(),
                        topic = q.optString("topic", "").trim(),
                        explanation = q.optString("explanation", "").trim()
                    )
                )
            }
            questions
        }
    } catch (e: Exception) {
        null
    }
}

/**
 * Searches community posts by keyword via the posts_search.php endpoint.
 * Returns a list of matching posts, or null on network/parse error.
 */
private fun searchCommunityPosts(context: Context, keyword: String): List<CommunityPostResult>? {
    val userId = context.getSharedPreferences("MY_APP", Context.MODE_PRIVATE).getInt("user_id", 0)
    val url = "https://medigyaan.xyz/Neurons/api/posts_search.php?q=${URLEncoder.encode(keyword, "UTF-8")}&user_id=$userId"
    val request = Request.Builder()
        .url(url)
        .addHeader("X-App-Signature", "EduLabsRTM_Secure_v1_2026")
        .addHeader("Accept", "application/json")
        .get()
        .build()
    return try {
        httpClient.newCall(request).execute().use { response ->
            val body = response.body?.string().orEmpty()
            if (!response.isSuccessful) return null
            val root = JSONObject(body)
            if (root.optString("status") != "success") return null
            val arr = root.optJSONArray("posts") ?: return emptyList()
            val out = mutableListOf<CommunityPostResult>()
            for (i in 0 until arr.length()) {
                val p = arr.optJSONObject(i) ?: continue
                val postId = p.optInt("post_id", 0)
                if (postId <= 0) continue
                val images = p.optJSONArray("images")?.let { a ->
                    (0 until a.length()).mapNotNull { j -> a.optString(j).takeIf { it.isNotBlank() } }
                } ?: emptyList()
                out += CommunityPostResult(
                    postId = postId,
                    author = p.optString("author", "MediGyaan user"),
                    authorPhoto = p.optString("author_photo", ""),
                    caption = p.optString("caption", "").trim(),
                    images = images,
                    likes = p.optInt("likes", 0),
                    uploadDate = p.optString("upload_date", "")
                )
            }
            out
        }
    } catch (e: Exception) {
        Log.e("AiChatCommunity", "searchCommunityPosts failed: ${e.message}", e)
        null
    }
}
