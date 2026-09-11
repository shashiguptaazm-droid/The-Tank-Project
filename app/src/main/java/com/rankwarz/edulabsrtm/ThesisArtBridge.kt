package com.rankwarz.edulabsrtm

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Typeface
import android.net.Uri
import com.rankwarz.edulabsrtm.model.PubMedCitationValidator
import com.rankwarz.edulabsrtm.model.Variable
import com.rankwarz.edulabsrtm.viewmodel.PdfThemeStyle
import com.rankwarz.edulabsrtm.viewmodel.ThesisViewModel
import com.rankwarz.edulabsrtm.viewmodel.resolvePdfThemeStyle
import com.rankwarz.edulabsrtm.viewmodel.PdfTheme
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.util.Locale
import kotlin.random.Random

/**
 * Shared thesis-art helpers: PDF variable extraction from raw text, a random theme selector,
 * and the PubMed abstract download pipeline used by Chat-with-PDF.
 */
object ThesisArtBridge {

    /** Returns a random [PdfThemeStyle] each call. */
    fun randomThemeStyle(): PdfThemeStyle {
        val theme = PdfTheme.values()[Random.nextInt(PdfTheme.values().size)]
        return resolvePdfThemeStyle(theme)
    }

    /** Extracts structured variables (Title, Abstract, References) from raw text. */
    fun extractPdfVariables(text: String, onChunk: (String) -> Unit = {}): List<Variable> {
        val out = mutableListOf<Variable>()
        val lines = text.lines().filter { it.isNotBlank() }
        val title = lines.firstOrNull { !it.matches(Regex("""^(abstract|introduction|references|acknowledgment|keywords|tables?|figures?|appendi[xc])(\s|:|$)""", RegexOption.IGNORE_CASE)) }
        if (title != null) {
            out += Variable("Title", title.trim().take(300))
        }
        val abstractBlock = extractBlock(lines, listOf("abstract"), stopOn = listOf("introduction", "keywords", "introduction:", "abstract:", "acknowledgments"))
        if (abstractBlock.isNotBlank()) {
            out += Variable("Abstract", abstractBlock.trim().take(6000))
        }
        val refs = extractRefsBlock(lines)
        if (refs.isNotBlank()) {
            out += Variable("References_Vancouver", refs.trim().take(12000))
        }
        onChunk("Extracted " + out.size + " variables")
        return out
    }

    private fun extractBlock(lines: List<String>, heading: List<String>, stopOn: List<String>): String {
        val lower = lines.map { it.trim().lowercase() }
        val start = lower.indexOfFirst { it in heading }
        if (start < 0) return ""
        val stop = lower.subList(start + 1, lower.size).indexOfFirst { it in stopOn }.let { if (it >= 0) start + 1 + it else lower.size }
        return lines.subList(start + 1, stop).joinToString("\n").trim()
    }

    private fun extractRefsBlock(lines: List<String>): String {
        val lower = lines.map { it.trim().lowercase() }
        val candidates = listOf("references", "references:", "bibliography", "citations", "citations:", "reference list")
        val start = lower.indexOfFirst { it in candidates }
        if (start < 0) {
            val idx = lines.indexOfFirst { Regex("""^\s*\[?\d{1,4}\]?\s*[.)]\s*[A-ZÀ-Ž]""").containsMatchIn(it) }
            if (idx < 0) return ""
            return lines.subList(idx, lines.size).joinToString("\n").trim()
        }
        return lines.subList(start + 1, lines.size).joinToString("\n").trim().take(12000)
    }

    // ---------------------------------------------------------------- PubMed abstracts

    /** Card state or downloaded PubMed abstracts. */
    data class PdfAbstractEntry(val pmid: String = "", val title: String = "", val text: String = "")
    data class PdfAbstractsState(val running: Boolean = false, val note: String = "", val entries: List<PdfAbstractEntry> = emptyList())

    suspend fun enrichPdfVariablesWithAbstracts(
        variables: List<Variable>,
        onState: (PdfAbstractsState) -> Unit
    ): List<Variable> {
        val refsText = variables
            .filter { v ->
                val n = v.name.lowercase()
                n.contains("reference") || n.contains("citation") || n.contains("vancouver")
            }
            .joinToString("\n") { it.value }
            .trim()
        val entries = PubMedCitationValidator.extractCitationEntries(refsText)
        if (entries.size < 2) return emptyList()
        
        onState(PdfAbstractsState(running = true, note = "Verifying references..."))
        val results = PubMedCitationValidator.validate(entries) { progress ->
            onState(PdfAbstractsState(running = true, note = progress.status))
        }
        val verified = results.filter { it.found && it.pmid.isNotBlank() }
        val abstracts = linkedMapOf<String, String>()
        verified.forEachIndexed { i, r ->
            onState(PdfAbstractsState(running = true, note = "Downloading abstract ${i+1}/${verified.size}"))
            fetchAbstract(r.pmid)?.let { abstracts[r.pmid] = it }
        }
        return abstractsToVariables(abstracts)
    }

    suspend fun fetchAbstract(pmid: String): String? = withContext(Dispatchers.IO) {
        val url = "https://efetch.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=$pmid&retmode=text&rettype=abstract"
        runCatching {
            val conn = URL(url).openConnection() as HttpURLConnection
            conn.connectTimeout = 20_000
            conn.readTimeout = 30_000
            conn.inputStream.use { stream ->
                stream.bufferedReader().use { it.readText() }.take(3000)
            }
        }.getOrNull()
    }

    fun abstractsToVariables(abstracts: Map<String, String>): List<Variable> {
        return abstracts.map { (pmid, text) ->
            Variable(name = "PubmedAbstract_$pmid", value = "PMID $pmid\n\n$text")
        }
    }

    suspend fun fetchSimilarPmids(pmid: String): List<String> = withContext(Dispatchers.IO) {
        val url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=pubmed&db=pubmed&id=$pmid&cmd=neighbor_score&retmode=xml"
        runCatching {
            val conn = URL(url).openConnection() as HttpURLConnection
            val xml = conn.inputStream.use { it.bufferedReader().readText() }
            val regex = Regex("<Id>(\\d+)</Id>")
            regex.findAll(xml).map { it.groupValues[1] }.filter { it != pmid }.take(10).toList()
        }.getOrDefault(emptyList())
    }

    suspend fun searchSimilarArticles(query: String): List<String> = withContext(Dispatchers.IO) {
        val url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&retmax=10&term=${URLEncoder.encode(query, "UTF-8")}"
        runCatching {
            val conn = URL(url).openConnection() as HttpURLConnection
            val json = conn.inputStream.use { it.bufferedReader().readText() }
            val obj = JSONObject(json)
            val ids = obj.getJSONObject("esearchresult").getJSONArray("idlist")
            val list = mutableListOf<String>()
            for (i in 0 until ids.length()) list.add(ids.getString(i))
            list
        }.getOrDefault(emptyList())
    }

    suspend fun fetchAbstractJson(pmid: String): String? = withContext(Dispatchers.IO) {
        val url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=$pmid&retmode=xml&rettype=abstract"
        runCatching {
            val conn = URL(url).openConnection() as HttpURLConnection
            val xml = conn.inputStream.use { it.bufferedReader().readText() }
            // Simple extraction of abstract text from XML
            val regex = Regex("<AbstractText[^>]*>(.*?)</AbstractText>")
            regex.findAll(xml).joinToString("\n") { it.groupValues[1] }.take(4000)
        }.getOrNull()
    }
}

/** Helper for themed page painting. */
fun paintPdfPage(
    canvas: Canvas,
    widthPx: Int,
    heightPx: Int,
    style: PdfThemeStyle
) {
    val paint = Paint().apply { isAntiAlias = true }
    paint.color = style.accentColor
    canvas.drawRect(0f, 0f, widthPx.toFloat(), 80f, paint)
    paint.color = style.ruleColor
    paint.strokeWidth = 3f
    canvas.drawLine(0f, 80f, widthPx.toFloat(), 80f, paint)
}
