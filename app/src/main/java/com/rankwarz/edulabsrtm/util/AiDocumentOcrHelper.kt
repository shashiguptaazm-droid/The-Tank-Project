package com.rankwarz.edulabsrtm.util

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.os.ParcelFileDescriptor
import android.util.Log
import android.view.Gravity
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import com.google.android.gms.tasks.Tasks
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import com.rankwarz.edulabsrtm.AiChatActivity
import com.rankwarz.edulabsrtm.utils.PdfTextExtractor
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import com.rankwarz.edulabsrtm.ApiKeys
import com.rankwarz.edulabsrtm.data.remote.ApiClient
import com.rankwarz.edulabsrtm.data.remote.ChatRequest
import com.rankwarz.edulabsrtm.data.remote.Message
import com.rankwarz.edulabsrtm.AiTrainingLogger
import com.rankwarz.edulabsrtm.utils.ResearchSkillRegistry
import com.rankwarz.edulabsrtm.utils.ResearchSkillHandler
import com.rankwarz.edulabsrtm.utils.SkillOutcome
import com.rankwarz.edulabsrtm.utils.ProjectContextManager
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.util.concurrent.TimeUnit
import java.util.regex.Pattern
import java.util.zip.ZipFile

object AiDocumentOcrHelper {
    private const val TAG = "AiDocumentOcrHelper"
    private val scope = CoroutineScope(Dispatchers.IO)
    private val mainHandler = Handler(Looper.getMainLooper())

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    fun isEligibleForAi(ext: String): Boolean {
        val cleanExt = ext.lowercase().trim().removePrefix(".")
        return cleanExt in listOf(
            "pdf", "doc", "docx", "ppt", "pptx", "txt", "text", "csv", "json", "xml", "md", "markdown", "log", "rtf", "tsv",
            "jpg", "jpeg", "png", "webp", "bmp", "heic"
        )
    }

    suspend fun extractText(context: Context, fileUrlOrPath: String): String = withContext(Dispatchers.IO) {
        val fullUrl = MediaCacheManager.resolveFullUrl(fileUrlOrPath)
        val fileName = fileUrlOrPath.substringAfterLast("/").substringBefore("?").ifBlank { "document" }
        val ext = fileName.substringAfterLast(".", "").lowercase()

        try {
            val localFile = obtainLocalFile(context, fullUrl, fileName)
                ?: return@withContext ""

            extractTextFromFile(context, localFile, ext, fileName)
        } catch (e: Exception) {
            Log.e(TAG, "extractText error for $fileName: ${e.message}", e)
            ""
        }
    }

    suspend fun extractText(context: Context, uri: Uri): String = withContext(Dispatchers.IO) {
        val fileName = queryFileName(context, uri)
        val ext = fileName.substringAfterLast(".", "").lowercase()
        val mime = context.contentResolver.getType(uri).orEmpty().lowercase()
        val resolvedExt = when {
            ext.isNotBlank() -> ext
            mime.contains("presentation") || mime.contains("powerpoint") -> "pptx"
            mime.contains("word") || mime.contains("msword") -> "docx"
            mime.contains("pdf") -> "pdf"
            mime.startsWith("image/") -> "png"
            mime.startsWith("text/") -> "txt"
            else -> "txt"
        }

        if (resolvedExt in listOf("jpg", "jpeg", "png", "webp", "bmp", "heic") || mime.startsWith("image/")) {
            val ocr = extractImageOcrFromUri(context, uri)
            if (ocr.isNotBlank()) return@withContext ocr
        }

        val tempFile = File(context.cacheDir, "ocr_${System.currentTimeMillis()}_${fileName.ifBlank { "file" }}")
        try {
            context.contentResolver.openInputStream(uri)?.use { input ->
                FileOutputStream(tempFile).use { output ->
                    input.copyTo(output)
                }
            } ?: return@withContext ""
            extractTextFromFile(context, tempFile, resolvedExt, fileName)
        } catch (e: Exception) {
            Log.e(TAG, "extractText from Uri failed for $fileName: ${e.message}", e)
            ""
        } finally {
            runCatching { tempFile.delete() }
        }
    }

    suspend fun extractText(context: Context, file: File): String = withContext(Dispatchers.IO) {
        val ext = file.extension.lowercase()
        extractTextFromFile(context, file, ext, file.name)
    }

    private suspend fun extractTextFromFile(context: Context, file: File, ext: String, fileName: String): String {
        return when {
            ext in listOf("jpg", "jpeg", "png", "webp", "bmp", "heic") -> {
                extractImageOcrText(file)
            }
            ext == "pdf" -> {
                extractPdfTextWithOcrFallback(context, file)
            }
            ext in listOf("doc", "docx") -> {
                extractWordText(file)
            }
            ext in listOf("ppt", "pptx") -> {
                extractPowerPointText(file)
            }
            ext in listOf("txt", "text", "csv", "json", "xml", "md", "markdown", "log", "rtf", "tsv") -> {
                extractPlainText(file)
            }
            else -> {
                // Try PowerPoint first
                val ppt = extractPowerPointText(file)
                if (ppt.isNotBlank()) return ppt
                val word = extractWordText(file)
                if (word.isNotBlank()) return word
                val plain = extractPlainText(file)
                if (plain.isNotBlank()) return plain
                extractRawStrings(file)
            }
        }
    }

    fun detectSkillName(userPrompt: String, documentText: String): String {
        val combined = "$userPrompt $documentText".lowercase()

        return when {
            // Statistical power & sample size
            combined.contains("sample size") || combined.contains("sample site") || (combined.contains("power") && combined.contains("calculate")) ->
                "Sample Size Calculator"

            // Autonomous coding & agentic tools
            combined.contains("coding agent") || combined.contains("autonomous coding") || combined.contains("code agent") ->
                "Autonomous Coding Agent"
            combined.contains("diff viewer") || (combined.contains("diff") && combined.contains("change")) ->
                "Diff Change Viewer"
            combined.contains("compiler error") || combined.contains("stack trace") || combined.contains("stacktrace") ->
                "Compiler Error Interpreter"
            combined.contains("research script") || (combined.contains("script") && combined.contains("python")) ->
                "Research Script Generator"

            // Validation & citations
            combined.contains("claim verification") || combined.contains("validate claims") || combined.contains("verify claim") ->
                "Claim Verification"
            combined.contains("doi validator") || combined.contains("validate doi") ->
                "DOI Validator"
            combined.contains("vancouver") ->
                "Vancouver Formatter"
            combined.contains("pmid validator") || combined.contains("validate pmid") || combined.contains("check pmid") ->
                "PMID Validator"
            combined.contains("citation validator") || combined.contains("validate citation") || combined.contains("check citation") ->
                "Citation Validator"
            combined.contains("reference consistency") ->
                "Reference Consistency Checker"

            // Data extraction
            combined.contains("medical entit") || combined.contains("extract entit") ->
                "Medical Entity Extractor"
            combined.contains("numerical data") || combined.contains("odds ratio") || combined.contains("relative risk") || combined.contains("extract statistic") ->
                "Numerical Data Extractor"
            combined.contains("pico") || combined.contains("peco") ->
                "PICO/PECO Extractor"
            combined.contains("clinical fact") ->
                "Clinical Fact Extractor"
            combined.contains("table extraction") ->
                "Table Extraction"

            // Education & Study aids
            combined.contains("flashcard") || combined.contains("anki") ->
                "Spaced Repetition Flashcarder"
            combined.contains("mnemonic") || combined.contains("memory aid") ->
                "Medical Mnemonic Creator"
            combined.contains("abbreviation") || combined.contains("acronym") || combined.contains("decode shorthand") ->
                "Medical Abbreviations Decoder"
            combined.contains("case study") || combined.contains("clinical case") || combined.contains("patient scenario") ->
                "Case Study Generator"
            combined.contains("differential diagnosis") || combined.contains("ddx") ->
                "Differential Diagnosis Builder"

            // Clinical calculations & tools
            combined.contains("abg") || combined.contains("arterial blood gas") || (combined.contains("ph ") && combined.contains("pco2")) ->
                "ABG Acid-Base Solver"
            combined.contains("ascvd") || combined.contains("cvd risk") || combined.contains("cardiovascular risk") ->
                "Cardiovascular Risk Scorer"
            combined.contains("pediatric dose") || combined.contains("weight-based dos") ->
                "Pediatric Dose Calculator"
            combined.contains("drug interaction") ->
                "Drug Interaction Checker"
            combined.contains("soap note") ->
                "SOAP Note Assistant"
            combined.contains("discharge summary") ->
                "Discharge Summary Drafter"
            combined.contains("icd-10") || combined.contains("icd-11") || combined.contains("billing code") ->
                "ICD-10/11 Code Suggester"

            // Research generation & protocols
            combined.contains("hypothesis") || combined.contains("null hypothesis") ->
                "Hypothesis Generator"
            combined.contains("structured abstract") || combined.contains("generate abstract") ->
                "Abstract Generator"
            combined.contains("research audit") || combined.contains("final audit") ->
                "Final Research Auditor"
            combined.contains("irb") || combined.contains("ethics committee") || combined.contains("ethical clearance") ->
                "IRB/Ethics Validator"
            combined.contains("prisma") || combined.contains("systematic review") ->
                "PRISMA Checklist Validator"
            combined.contains("thesis writer") || combined.contains("methodology chapter") || combined.contains("draft chapter") || combined.contains("write chapter") ->
                "Thesis Writer"
            combined.contains("academic poster") || combined.contains("poster from abstract") || combined.contains("generate poster") || combined.contains("poster layout") ->
                "Conference Abstract Generator"
            combined.contains("similar article") || combined.contains("find related research") ->
                "Similar Article Finder"
            combined.contains("research question") || combined.contains("thesis topic") ->
                "Research Question Analyzer"

            // Exact match against any skill in ResearchSkillRegistry
            else -> {
                val matched = ResearchSkillRegistry.SKILLS.firstOrNull { skill ->
                    combined.contains(skill.name.lowercase())
                }
                matched?.name ?: "NONE"
            }
        }
    }

    suspend fun queryAiAboutDocument(
        userPrompt: String,
        documentText: String,
        fileName: String,
        context: Context? = null
    ): String = withContext(Dispatchers.IO) {
        val detectedSkill = detectSkillName(userPrompt, documentText)
        var skillOutcome: SkillOutcome? = null
        if (detectedSkill != "NONE" && context != null) {
            try {
                skillOutcome = ResearchSkillHandler.executeSkill(detectedSkill, userPrompt, documentText, context)
            } catch (e: Exception) {
                Log.w(TAG, "Skill execution failed for $detectedSkill: ${e.message}")
            }
        }

        val systemPrompt = "You are MediGyaan AI, an intelligent medical AI assistant inside MediGyaan Messenger (functioning just like Meta AI in WhatsApp). When a user asks about a document, medical query, or research task, provide a clear, concise, accurate, and clinically helpful reply. Format all main section titles as **Title** without asterisks in the displayed text. Highlight key medical findings, diagnosis, abnormal lab values, or main takeaways using neat WhatsApp-friendly formatting (bullet points, bold key terms). Keep answers concise and readable on a mobile screen."

        val promptBuilder = StringBuilder()
        if (userPrompt.isNotBlank()) {
            promptBuilder.append("User Query: ").append(userPrompt).append("\n\n")
        } else {
            promptBuilder.append("User Query: Please summarize this document and highlight the key findings.\n\n")
        }
        promptBuilder.append("Document: ").append(fileName).append("\n")
        if (documentText.isNotBlank()) {
            promptBuilder.append("Extracted Document Content:\n").append(documentText.take(16000))
        } else {
            promptBuilder.append("(No readable text could be recognized from this file)")
        }

        val messages = mutableListOf<Message>()
        messages.add(Message("system", systemPrompt))

        // Inject Project Context for coding/agent skills
        if (detectedSkill in listOf("Autonomous Coding Agent", "Diff Change Viewer", "Compiler Error Interpreter", "Research Script Generator") ||
            userPrompt.contains("coding", ignoreCase = true) || userPrompt.contains("agent", ignoreCase = true)) {
            messages.add(Message("system", ProjectContextManager.getProjectSummary()))
        }

        // Inject Specialized Skill Outcome if activated
        if (detectedSkill != "NONE" && skillOutcome != null && skillOutcome.success) {
            messages.add(Message("system", """
                [SPECIALIZED RESEARCH SKILL ACTIVATED: $detectedSkill]
                Skill Execution Directive / Verified Context:
                ${skillOutcome.contextText}
                
                Fulfill this specialized skill requirement with full scientific and clinical rigor.
                Structure your reply with prominent bold titles (**Title**) for each main section.
            """.trimIndent()))
        }

        messages.add(Message("user", promptBuilder.toString()))

        // Try fast models in rotation: Groq -> OpenRouter -> DeepSeek -> Cerebras -> Mistral
        val candidates = listOf(
            "groq" to "llama-3.3-70b-versatile",
            "groq" to "llama-3.1-8b-instant",
            "openrouter" to "google/gemini-2.0-flash-lite-001",
            "openrouter" to "meta-llama/llama-3.3-70b-instruct:free",
            "openrouter" to "openrouter/free",
            "cerebras" to "llama3.1-70b",
            "mistral" to "mistral-small-latest"
        )

        val startTime = System.currentTimeMillis()
        val fullPrompt = promptBuilder.toString()
        val source = if (fileName == "Chat Question") "messenger_ai_chat" else "messenger_ask_ai"

        for ((provider, model) in candidates) {
            val apiKey = when (provider) {
                "groq" -> ApiKeys.GROQ_API_KEY
                "openrouter" -> ApiKeys.OPENROUTER_API_KEY
                "deepseek" -> ApiKeys.DEEPSEEK_API_KEY
                "cerebras" -> ApiKeys.CEREBRAS_API_KEY
                "mistral" -> ApiKeys.MISTRAL_API_KEY
                else -> ""
            }.trim()

            if (apiKey.isBlank()) continue

            try {
                val request = ChatRequest(
                    model = model,
                    messages = messages,
                    temperature = 0.3,
                    maxTokens = 1200
                )

                val response = when (provider) {
                    "groq" -> ApiClient.groqApi.chatCompletion("openai/v1/chat/completions", "Bearer $apiKey", request)
                    "openrouter" -> ApiClient.openRouterApi.chatCompletion("api/v1/chat/completions", "Bearer $apiKey", request)
                    "deepseek" -> ApiClient.deepSeekApi.chatCompletion("chat/completions", "Bearer $apiKey", request)
                    "cerebras" -> ApiClient.cerebrasApi.chatCompletion("v1/chat/completions", "Bearer $apiKey", request)
                    "mistral" -> ApiClient.mistralApi.chatCompletion("v1/chat/completions", "Bearer $apiKey", request)
                    else -> continue
                }

                val content = response.choices.firstOrNull()?.message?.content?.trim().orEmpty()
                if (content.isNotBlank()) {
                    val durationMs = System.currentTimeMillis() - startTime
                    val contextObj = JSONObject().apply {
                        put("file_name", fileName)
                        put("has_document_text", documentText.isNotBlank())
                        put("document_text_len", documentText.length)
                        put("user_prompt", userPrompt)
                        put("skill", detectedSkill)
                        put("skill_note", skillOutcome?.uiNote ?: "")
                        put("skill_success", skillOutcome?.success ?: false)
                    }
                    AiTrainingLogger.log(
                        source = source,
                        provider = provider,
                        model = model,
                        prompt = fullPrompt,
                        response = content,
                        status = "completed",
                        contextJson = contextObj.toString(),
                        durationMs = durationMs
                    )
                    return@withContext content
                }
            } catch (e: Exception) {
                Log.w(TAG, "AI candidate failed ($provider/$model): ${e.message}")
            }
        }

        val durationMs = System.currentTimeMillis() - startTime
        val failContext = JSONObject().apply {
            put("file_name", fileName)
            put("user_prompt", userPrompt)
            put("skill", detectedSkill)
        }
        AiTrainingLogger.log(
            source = source,
            provider = "none",
            model = "none",
            prompt = fullPrompt,
            response = "",
            status = "failed",
            contextJson = failContext.toString(),
            durationMs = durationMs
        )

        "I was unable to analyze this document right now. Please try again in a moment."
    }

    fun processAndLaunchAi(
        activity: Activity,
        fileUrlOrPath: String,
        userMessage: String
    ) {
        val fullUrl = MediaCacheManager.resolveFullUrl(fileUrlOrPath)
        val fileName = fileUrlOrPath.substringAfterLast("/").substringBefore("?").ifBlank { "document" }
        val ext = fileName.substringAfterLast(".", "").lowercase()

        if (!isEligibleForAi(ext)) {
            Toast.makeText(activity, "AI analysis only supported for PDF, Word, and Images", Toast.LENGTH_SHORT).show()
            return
        }

        // Show elegant modern loading dialog
        val dialogView = LinearLayout(activity).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(48, 40, 48, 40)

            val pb = ProgressBar(activity).apply { isIndeterminate = true }
            addView(pb)

            val tv = TextView(activity).apply {
                text = "Extracting text with AI OCR…"
                textSize = 15f
                setPadding(32, 0, 0, 0)
            }
            addView(tv)
        }

        val dialog = AlertDialog.Builder(activity)
            .setView(dialogView)
            .setCancelable(false)
            .create()

        dialog.show()

        scope.launch {
            try {
                // 1. Obtain local file (either already cached or downloaded)
                val localFile = obtainLocalFile(activity, fullUrl, fileName)
                if (localFile == null || !localFile.exists() || localFile.length() == 0L) {
                    throw IllegalStateException("Failed to download or read document file")
                }

                // 2. Perform OCR / text extraction based on file type
                val extractedText = when {
                    ext in listOf("jpg", "jpeg", "png", "webp", "bmp", "heic") -> {
                        extractImageOcrText(localFile)
                    }
                    ext == "pdf" -> {
                        extractPdfTextWithOcrFallback(activity, localFile)
                    }
                    ext in listOf("doc", "docx") -> {
                        extractWordText(localFile)
                    }
                    else -> ""
                }

                // 3. Formulate the complete message for AiChatActivity
                val completePrompt = buildString {
                    if (userMessage.isNotBlank()) {
                        append(userMessage.trim())
                        append("\n\n")
                    }
                    append("--- [Document Analysis: $fileName] ---\n")
                    if (extractedText.isNotBlank()) {
                        append(extractedText.trim().take(35000))
                    } else {
                        append("(No readable text could be recognized from this document)")
                    }
                }

                mainHandler.post {
                    dialog.dismiss()

                    val intent = Intent(activity, AiChatActivity::class.java).apply {
                        putExtra("INITIAL_PROMPT", completePrompt)
                        putExtra("INPUT_TEXT", completePrompt)
                        putExtra("DOCUMENT_NAME", fileName)
                        putExtra("DOCUMENT_URL", fullUrl)
                    }
                    activity.startActivity(intent)
                }
            } catch (e: Exception) {
                Log.e(TAG, "OCR / Text extraction error for $fileName: ${e.message}", e)
                mainHandler.post {
                    dialog.dismiss()
                    Toast.makeText(activity, "Failed to analyze document: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun obtainLocalFile(context: Context, fullUrl: String, fileName: String): File? {
        val cleanUrl = fullUrl.removePrefix("file://")
        if (cleanUrl.startsWith("/") || (cleanUrl.length >= 3 && cleanUrl[1] == ':' && (cleanUrl[2] == '\\' || cleanUrl[2] == '/'))) {
            val f = File(cleanUrl)
            if (f.exists()) return f
        }

        // Check doc cache
        val docCached = MediaCacheManager.getCachedDocFile(context, fullUrl)
        if (docCached.exists() && docCached.length() > 0) return docCached

        // Check app cacheDir
        val cacheFile = File(context.cacheDir, fileName)
        if (cacheFile.exists() && cacheFile.length() > 0) return cacheFile

        // Download directly to temp file
        return try {
            val req = Request.Builder().url(fullUrl).build()
            val resp = httpClient.newCall(req).execute()
            if (resp.isSuccessful && resp.body != null) {
                val temp = File(context.cacheDir, "ocr_${System.currentTimeMillis()}_$fileName")
                resp.body!!.byteStream().use { input ->
                    FileOutputStream(temp).use { output ->
                        input.copyTo(output)
                    }
                }
                temp
            } else null
        } catch (e: Exception) {
            Log.e(TAG, "Download failed for OCR: ${e.message}")
            null
        }
    }

    /**
     * Extracts text from images using on-device ML Kit Text Recognition.
     */
    private fun extractImageOcrText(file: File): String {
        val bitmap = BitmapFactory.decodeFile(file.absolutePath) ?: return ""
        val inputImage = InputImage.fromBitmap(bitmap, 0)
        val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
        return try {
            val result = Tasks.await(recognizer.process(inputImage))
            result.text.trim()
        } catch (e: Exception) {
            Log.e(TAG, "ML Kit OCR failed: ${e.message}")
            ""
        } finally {
            recognizer.close()
        }
    }

    /**
     * Extracts text from PDF using PdfBox, and if text is empty or scanned,
     * renders pages to bitmaps and applies ML Kit OCR.
     */
    private suspend fun extractPdfTextWithOcrFallback(context: Context, file: File): String {
        // 1. Try text extraction via PdfTextExtractor (PdfBox)
        var text = ""
        try {
            FileInputStream(file).use { stream ->
                text = PdfTextExtractor.extractText(context, stream).trim()
            }
        } catch (e: Exception) {
            Log.d(TAG, "PdfBox extraction note: ${e.message}")
        }

        if (text.length > 50) {
            return text
        }

        // 2. Scanned PDF fallback: render first 3 pages and OCR with ML Kit
        val ocrSb = StringBuilder()
        var pfd: ParcelFileDescriptor? = null
        var renderer: PdfRenderer? = null
        val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)

        try {
            pfd = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY)
            renderer = PdfRenderer(pfd)
            val pagesToScan = renderer.pageCount.coerceAtMost(3)

            for (i in 0 until pagesToScan) {
                var page: PdfRenderer.Page? = null
                try {
                    page = renderer.openPage(i)
                    val width = 1080
                    val height = (width * page.height / page.width.toFloat()).toInt()
                    val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
                    bitmap.eraseColor(Color.WHITE)
                    page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)

                    val inputImage = InputImage.fromBitmap(bitmap, 0)
                    val result = Tasks.await(recognizer.process(inputImage))
                    if (result.text.isNotBlank()) {
                        ocrSb.append("[Page ${i + 1}]\n").append(result.text).append("\n\n")
                    }
                } finally {
                    try { page?.close() } catch (_: Exception) {}
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "PDF OCR fallback error: ${e.message}")
        } finally {
            recognizer.close()
            try { renderer?.close() } catch (_: Exception) {}
            try { pfd?.close() } catch (_: Exception) {}
        }

        return if (ocrSb.isNotBlank()) ocrSb.toString().trim() else text
    }

    /**
     * Extracts text from DOCX OpenXML archive with fallback for legacy .doc binary files.
     */
    fun extractWordText(file: File): String {
        return try {
            ZipFile(file).use { zip ->
                val entry = zip.getEntry("word/document.xml") ?: return extractRawStrings(file)
                val xml = zip.getInputStream(entry).bufferedReader(Charsets.UTF_8).readText()
                val pPattern = Pattern.compile("<w:p(?:\\s+[^>]*)?>(.*?)</w:p>", Pattern.DOTALL)
                val tPattern = Pattern.compile("<w:t(?:\\s+[^>]*)?>(.*?)</w:t>", Pattern.DOTALL)
                val pMatcher = pPattern.matcher(xml)
                val sb = StringBuilder()

                while (pMatcher.find()) {
                    val pXml = pMatcher.group(1) ?: continue
                    val tMatcher = tPattern.matcher(pXml)
                    val pSb = StringBuilder()
                    while (tMatcher.find()) {
                        val rawText = tMatcher.group(1) ?: ""
                        pSb.append(unescapeXml(rawText))
                    }
                    val paragraphText = pSb.toString().trim()
                    if (paragraphText.isNotBlank()) {
                        sb.append(paragraphText).append("\n\n")
                    }
                }

                val result = sb.toString().trim()
                if (result.isNotBlank()) result else extractRawStrings(file)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Word text extraction error: ${e.message}")
            extractRawStrings(file)
        }
    }

    /**
     * Extracts text from PPTX OpenXML presentation with slide-by-slide formatting and fallback for legacy .ppt files.
     */
    fun extractPowerPointText(file: File): String {
        return try {
            ZipFile(file).use { zip ->
                val slidePattern = Regex("""ppt/slides/slide(\d+)\.xml""")
                val slideEntries = zip.entries().asSequence()
                    .mapNotNull { entry ->
                        slidePattern.matchEntire(entry.name)?.let { match ->
                            val num = match.groupValues[1].toIntOrNull() ?: 0
                            num to entry
                        }
                    }
                    .sortedBy { it.first }
                    .toList()

                if (slideEntries.isEmpty()) {
                    return extractRawStrings(file)
                }

                val pPattern = Pattern.compile("<a:p(?:\\s+[^>]*)?>(.*?)</a:p>", Pattern.DOTALL)
                val tPattern = Pattern.compile("<a:t(?:\\s+[^>]*)?>(.*?)</a:t>", Pattern.DOTALL)
                val sb = StringBuilder()

                for ((slideNum, entry) in slideEntries) {
                    val xml = zip.getInputStream(entry).bufferedReader(Charsets.UTF_8).readText()
                    val pMatcher = pPattern.matcher(xml)
                    val paragraphs = mutableListOf<String>()

                    while (pMatcher.find()) {
                        val pXml = pMatcher.group(1) ?: continue
                        val tMatcher = tPattern.matcher(pXml)
                        val tSb = StringBuilder()
                        while (tMatcher.find()) {
                            val rawText = tMatcher.group(1) ?: ""
                            tSb.append(unescapeXml(rawText))
                        }
                        val pText = tSb.toString().trim()
                        if (pText.isNotBlank()) {
                            paragraphs.add(pText)
                        }
                    }

                    if (paragraphs.isNotEmpty()) {
                        sb.append("[Slide ").append(slideNum).append("]\n")
                        for (p in paragraphs) {
                            sb.append(p).append("\n")
                        }
                        sb.append("\n")
                    }
                }

                val result = sb.toString().trim()
                if (result.length >= 20) result else extractRawStrings(file)
            }
        } catch (e: Exception) {
            Log.e(TAG, "PowerPoint text extraction error: ${e.message}")
            extractRawStrings(file)
        }
    }

    /**
     * Extracts plain text from UTF-8 / ASCII / ISO text files (TXT, CSV, JSON, MD, RTF, XML).
     */
    fun extractPlainText(file: File): String {
        return try {
            val text = file.readText(Charsets.UTF_8)
            if (text.isNotBlank()) text.trim()
            else file.readText(Charsets.ISO_8859_1).trim()
        } catch (e: Exception) {
            Log.e(TAG, "Plain text extraction error: ${e.message}")
            extractRawStrings(file)
        }
    }

    /**
     * Helper for ML Kit OCR from content:// Uri.
     */
    fun extractImageOcrFromUri(context: Context, uri: Uri): String {
        val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
        return try {
            val image = InputImage.fromFilePath(context, uri)
            val result = Tasks.await(recognizer.process(image))
            result.text.trim()
        } catch (e: Exception) {
            Log.e(TAG, "ML Kit OCR from Uri failed: ${e.message}")
            ""
        } finally {
            recognizer.close()
        }
    }

    /**
     * Queries display name from content resolver or falls back to last path segment.
     */
    fun queryFileName(context: Context, uri: Uri): String {
        var name = ""
        if (uri.scheme == "content") {
            try {
                val cursor = context.contentResolver.query(uri, null, null, null, null)
                cursor?.use {
                    if (it.moveToFirst()) {
                        val idx = it.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
                        if (idx >= 0) name = it.getString(idx).orEmpty()
                    }
                }
            } catch (_: Exception) {}
        }
        if (name.isBlank()) {
            name = uri.lastPathSegment?.substringAfterLast("/") ?: "document"
        }
        return name
    }

    private fun unescapeXml(text: String): String {
        return text.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", "\"")
            .replace("&apos;", "'")
            .replace("&#39;", "'")
    }

    private fun extractRawStrings(file: File): String {
        return try {
            val bytes = file.readBytes()
            val sb = StringBuilder()
            val cur = StringBuilder()
            for (b in bytes) {
                val c = b.toInt().toChar()
                if (c in ' '..'~' || c == '\n' || c == '\t') {
                    cur.append(c)
                } else {
                    if (cur.length >= 4) {
                        sb.append(cur).append("\n")
                    }
                    cur.clear()
                }
            }
            if (cur.length >= 4) sb.append(cur)
            sb.toString().trim()
        } catch (e: Exception) {
            ""
        }
    }
}
