package com.rankwarz.edulabsrtm.model

import com.google.gson.JsonObject
import com.google.gson.JsonParser
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.net.URLEncoder
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit

/**
 * Standalone PubMed citation validator, ported from the Thesis Analyzer's
 * reference-checking logic so results are identical. Used by the AI chat to
 * validate pasted / AI-generated reference lists against PubMed.
 *
 * For each reference it:
 *  1. If a PMID is already present, verifies it via NCBI esummary (no guessing).
 *  2. Otherwise searches esearch (title / DOI queries), scores candidates, and
 *     accepts a match only when it passes the same title-overlap thresholds the
 *     thesis analyzer enforces. The found PMID/DOI/canonical citation are returned.
 *
 * References that cannot be matched are reported as "not found".
 */
object PubMedCitationValidator {

    /** A single line the detector believes might be a citation. */
    class CitationEntry(
        val text: String,
        val startsWithNumber: Boolean = false
    )

    /** One reference after validation. */
    class ValidationResult(
        val index: Int,
        val originalText: String,
        val found: Boolean,
        val pmid: String = "",
        val doi: String? = null,
        val articleTitle: String = "",
        val canonicalReference: String = ""
    )

    /** Live progress of a validation run (mirrors the thesis analyzer's status text). */
    data class ValidationProgress(
        val status: String,
        val current: Int,
        val total: Int
    )

    data class PubMedMatch(
        val pmid: String,
        val doi: String?,
        val articleTitle: String,
        val canonicalReference: String
    )

    private data class SearchHints(
        val doi: String? = null,
        val year: String? = null,
        val titleHint: String? = null,
        val titleCandidates: List<String> = emptyList(),
        val authorHint: String? = null,
        val cleanedText: String = ""
    )

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(25, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .build()

    private val pmidCache = ConcurrentHashMap<String, PubMedMatch>()
    private val searchCache = ConcurrentHashMap<String, PubMedMatch>()

    private val exactMatchScore = 90
    private val minimumSearchScore = 45
    private val minimumTitleTokenOverlap = 15

    // NCBI E-utilities is limited to 3 requests/sec without an API key.
    private var lastRequestAt = 0L

    private suspend fun ncbiThrottle() = withContext(Dispatchers.IO) {
        val now = System.currentTimeMillis()
        val wait = 180L - (now - lastRequestAt)
        if (wait > 0) delay(wait)
        lastRequestAt = System.currentTimeMillis()
    }

    // ---------------------------------------------------------------- entry parsing

    /** Splits multi-line text into individual citation candidates (continuation lines merge). */
    fun extractCitationEntries(text: String): List<CitationEntry> {
        val cleanedLines = text
            .replace("\r\n", "\n")
            .split("\n")
            .map { it.trim() }
            .filter { it.isNotBlank() }
            .filterNot { line ->
                val t = line.trim().lowercase().trimEnd(':', '.')
                t == "references" || t == "citations" || t == "bibliography" || t == "sources"
            }

        // Only ever parse when there is a real multi-line block to work with.
        if (cleanedLines.size < 2) return emptyList()

        val entries = mutableListOf<CitationEntry>()
        var pending = StringBuilder()

        fun flush() {
            if (pending.isNotBlank()) {
                entries += CitationEntry(pending.toString().trim())
                pending = StringBuilder()
            }
        }

        for (line in cleanedLines) {
            val stripped = line
                .replace(Regex("""^\s*\[\d+]\s*"""), "")
                .replace(Regex("""^\s*\d+\s*[.)-]\s*"""), "")
                .replace(Regex("""^\s*[-•*]\s+"""), "")
                .trim()
            if (stripped.isBlank()) continue

            // A new physical line either continues the pending citation (wrapped text)
            // or starts a fresh one. Numbered markers always start fresh; a continuation
            // almost always begins lowercase ("what works…") or with a bare year/pages.
            if (pending.isNotBlank()) {
                val startsNumbered = Regex("""^\s*\[?\d+]?\s*[.)-]\s*""").containsMatchIn(line)
                val looksWrapped = startsWithLowercase(stripped) ||
                    Regex("""^\s*\(?\d{2,4}[;,:.)-]""").containsMatchIn(stripped) ||
                    stripped.length <= 2
                // Flush when this line starts a fresh citation (numbered, or a
                // capitalized line that is not wrapped text from the previous one).
                if (startsNumbered || !looksWrapped) {
                    flush()
                }
            }
            if (pending.isNotBlank()) pending.append(' ')
            pending.append(stripped)
        }
        flush()
        return entries
    }

    private fun startsWithLowercase(s: String): Boolean {
        val first = s.firstOrNull() ?: return false
        return first.isLowerCase() || first in "(["
    }

    /**
     * Detection trigger — used by the chat to decide when to offer PubMed validation.
     * Requires a multi-line block where enough lines look like real citations.
     */
    fun looksLikeReferenceBlock(text: String): Boolean {
        if (text.isBlank()) return false
        val lines = text.replace("\r\n", "\n").split("\n").map { it.trim() }.filter { it.isNotBlank() }
        if (lines.size < 2) return false
        var numbered = 0
        var explicitMarker = false
        var withYear = 0
        var withEtAl = 0
        for (line in lines) {
            val t = line.trim()
            if (Regex("""^\s*\[\d+]\s*""").containsMatchIn(t) || Regex("""^\s*\d+[.)]\s*""").containsMatchIn(t)) numbered++
            if (Regex("""\bPMID\s*:?\s*\d{4,12}\b""", RegexOption.IGNORE_CASE).containsMatchIn(t)) explicitMarker = true
            if (Regex("""\b10\.\d{4,9}/\S+""").containsMatchIn(t)) explicitMarker = true
            if (Regex("""\b(19|20)\d{2}""").containsMatchIn(t) && t.length >= 30) withYear++
            if (Regex("""et al\.""", RegexOption.IGNORE_CASE).containsMatchIn(t)) withEtAl++
        }
        return explicitMarker ||
            numbered >= 2 ||
            withYear >= 2 && withEtAl >= 1 ||
            withYear >= 3
    }

    // ---------------------------------------------------------------- validation

    /**
     * Validates a list of citation entries against PubMed.
     * @param onProgress receives live status after each reference (index + 1 / total).
     */
    suspend fun validate(
        entries: List<CitationEntry>,
        onProgress: (ValidationProgress) -> Unit = {}
    ): List<ValidationResult> {
        if (entries.isEmpty()) return emptyList()

        val results = mutableListOf<ValidationResult>()
        for ((index, entry) in entries.withIndex()) {
            val label = "${index + 1}/${entries.size}"
            onProgress(ValidationProgress("Verifying PubMed reference $label", index, entries.size))
            val result = withContext(Dispatchers.IO) { resolveEntry(entry, index) }
            results += result
            onProgress(ValidationProgress(
                status = if (result.found) "PubMed reference found $label"
                else "No PubMed match $label",
                current = index + 1,
                total = entries.size
            ))
        }
        return results
    }

    private suspend fun resolveEntry(entry: CitationEntry, index: Int): ValidationResult {
        val raw = entry.text.trim()
        if (raw.isBlank()) return ValidationResult(index, raw, found = false)

        val stripped = stripReferenceMetadata(raw)
        val cleanedForLookup = stripped.ifBlank { raw }

        // A supplied PMID is authoritative: verify it directly instead of searching.
        val suppliedPmid = extractPmid(raw).takeIf { it.isNotBlank() }
        if (suppliedPmid != null) {
            val match = fetchByPmid(suppliedPmid)
            if (match != null) {
                val canonical = cleanedForLookup
                    .ifBlank { match.canonicalReference }
                    .replace(Regex("""\bPMID\s*:?\s*\d{4,12}\b\.?""", RegexOption.IGNORE_CASE), "")
                    .replace(Regex("""\s+"""), " ")
                    .trim()
                    .trimEnd('.', ';', ',')
                    .let { if (it.isBlank()) match.canonicalReference else "$it. PMID: ${match.pmid}" }
                return ValidationResult(index, raw, found = true, pmid = match.pmid, doi = match.doi, articleTitle = match.articleTitle, canonicalReference = canonical)
            }
            return ValidationResult(index, raw, found = false)
        }

        val match = searchReference(cleanedForLookup) ?: run {
            // Fall back to the DOI extracted from the raw citation when the text search missed.
            val doi = extractDoi(raw) ?: extractDoi(stripped)
            if (!doi.isNullOrBlank()) {
                val doiMatch = searchReference(doi)
                if (doiMatch != null && doiMatch.doi?.equals(doi, ignoreCase = true) == true) doiMatch else null
            } else null
        }

        if (match != null) {
            return ValidationResult(
                index = index,
                originalText = raw,
                found = true,
                pmid = match.pmid,
                doi = match.doi,
                articleTitle = match.articleTitle,
                canonicalReference = match.canonicalReference
            )
        }
        return ValidationResult(index, raw, found = false)
    }

    // ---------------------------------------------------------------- reference text helpers

    fun stripReferenceMetadata(text: String): String {
        return text
            .replace(Regex("""\bPMID\s*:?\s*\d{4,12}\b\.?""", RegexOption.IGNORE_CASE), "")
            .replace(Regex("""\bDOI\s*:?\s*10\.\d{4,9}/[^\s<>"']+\.?""", RegexOption.IGNORE_CASE), "")
            .replace(Regex("""\s+"""), " ")
            .trim()
            .trimEnd('.', ';', ',')
            .trim()
    }

    fun extractPmid(text: String): String {
        return Regex("""\bPMID\s*:?\s*(\d{4,12})\b""", RegexOption.IGNORE_CASE)
            .find(text)
            ?.groupValues
            ?.getOrNull(1)
            ?: text.trim().takeIf { it.matches(Regex("""\d{4,12}""")) }
            .orEmpty()
    }

    fun extractDoi(text: String): String? {
        return Regex("""10\.\d{4,9}/[^\s<>"']+""", RegexOption.IGNORE_CASE)
            .find(text)
            ?.value
            ?.trimEnd('.', ',', ';', ')', ']', '}')
    }

    private fun buildHints(referenceText: String): SearchHints {
        val cleaned = referenceText
            .replace(Regex("""^\s*\[?\d+]?\s*[.)-]?\s*"""), "")
            .replace(Regex("""\s+"""), " ")
            .trim()

        val doi = Regex("""10\.\d{4,9}/[^\s<>"']+""", RegexOption.IGNORE_CASE).find(cleaned)?.value
        val year = Regex("""\b(19|20)\d{2}\b""").find(cleaned)?.value
        val authorPart = cleaned.substringBefore(".").trim().takeIf { it.isNotBlank() }
        val titleCandidates = extractTitleCandidates(cleaned)

        return SearchHints(
            doi = doi,
            year = year,
            titleHint = titleCandidates.firstOrNull(),
            titleCandidates = titleCandidates,
            authorHint = authorPart,
            cleanedText = cleaned
        )
    }

    private fun extractTitleCandidates(cleanedReference: String): List<String> {
        val cleaned = cleanedReference
            .replace(Regex("""\bPMID\s*:?\s*\d{4,12}\b\.?""", RegexOption.IGNORE_CASE), "")
            .replace(Regex("""\bDOI\s*:?\s*10\.\d{4,9}/[^\s<>"']+\.?""", RegexOption.IGNORE_CASE), "")
            .replace(Regex("""\s+"""), " ")
            .trim()
            .trimEnd('.', ';', ',')

        val segments = cleaned
            .split(Regex("""\.\s+"""))
            .map { it.trim().trim('.', ';', ',') }
            .filter { it.isNotBlank() }

        val candidates = linkedSetOf<String>()
        segments.drop(1).forEach { if (looksLikeTitle(it)) candidates += it }
        segments.forEach { if (looksLikeTitle(it)) candidates += it }

        val longest = cleaned
            .split(Regex("""[.;]"""))
            .map { it.trim() }
            .filter { looksLikeTitle(it) }
            .maxByOrNull { searchableTokenCount(it) }
        if (!longest.isNullOrBlank()) candidates += longest

        return candidates
            .map { it.replace(Regex("""\s+"""), " ").trim().trimEnd('.', ';', ',') }
            .filter { searchableTokenCount(it) >= 3 || it.length >= 20 }
            .distinct()
            .take(5)
    }

    private fun looksLikeTitle(segment: String): Boolean {
        val normalized = normalizeText(segment)
        if (normalized.isBlank()) return false
        if (Regex("""\b(19|20)\d{2}\b""").containsMatchIn(segment)) return false
        if (normalized.contains("doi") || normalized.contains("pmid")) return false
        val tokens = segment.split(Regex("""\s+""")).filter { it.any(Char::isLetter) }
        if (tokens.size < 3) return false
        return true
    }

    private fun searchableTokenCount(text: String): Int {
        return text.split(Regex("""\s+""")).count { it.length >= 4 }
    }

    private fun normalizeText(text: String): String {
        return text.replace(Regex("""\s+"""), " ").trim().lowercase()
    }

    // ---------------------------------------------------------------- NCBI E-utilities

    private suspend fun searchReference(referenceText: String): PubMedMatch? = withContext(Dispatchers.IO) {
        runCatching {
            val hints = buildHints(referenceText)
            val cacheKey = normalizeText(hints.cleanedText).take(240)
            searchCache[cacheKey]?.let { return@runCatching it }

            val queries = buildQueries(hints)
            val candidates = mutableListOf<PubMedMatch>()

            for (query in queries) {
                candidates += searchMatches(query, hints)
                val best = candidates.maxByOrNull { score(it, hints) }
                if (best != null && score(best, hints) >= exactMatchScore) {
                    searchCache[cacheKey] = best
                    return@runCatching best
                }
            }

            candidates
                .maxByOrNull { score(it, hints) }
                ?.takeIf { acceptableMatch(it, hints) }
                ?.also { searchCache[cacheKey] = it }
        }.getOrNull()
    }

    private fun buildQueries(hints: SearchHints): List<String> {
        val queries = linkedSetOf<String>()

        hints.doi?.takeIf { it.isNotBlank() }?.let { doi ->
            queries += "\"$doi\""
            queries += doi
        }

        hints.titleCandidates.forEach { title ->
            val cleanTitle = title.take(220)
            queries += "\"${cleanTitle.take(160)}\""
            hints.year?.takeIf { it.isNotBlank() }?.let { queries += "\"${cleanTitle.take(140)}\" AND $it[dp]" }
            queries += cleanTitle
            hints.authorHint?.takeIf { it.isNotBlank() }?.let { queries += "${it.take(80)} ${cleanTitle.take(120)}" }
        }

        hints.authorHint?.takeIf { it.isNotBlank() }?.let { queries += it.take(180) }

        val words = (hints.titleHint ?: hints.cleanedText)
            .split(Regex("""\s+"""))
            .map { it.trim('.', ',', ';', ':', '(', ')', '[', ']') }
            .filter { it.length >= 4 && !it.all(Char::isDigit) }
            .take(10)
        if (words.isNotEmpty()) {
            queries += words.joinToString(" ")
            hints.year?.takeIf { it.isNotBlank() }?.let { queries += "${words.joinToString(" ")} AND $it[dp]" }
            queries += words.take(6).joinToString(" ")
        }

        val compact = hints.cleanedText.take(220)
        if (compact.isNotBlank()) queries += compact

        return queries.filter { it.isNotBlank() }.distinct()
    }

    private suspend fun searchMatches(query: String, hints: SearchHints, limit: Int = 10): List<PubMedMatch> = withContext(Dispatchers.IO) {
        try {
            ncbiThrottle()
            val url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&retmax=$limit&term=${URLEncoder.encode(query, "UTF-8")}"
            val searchJson = httpClient.newCall(Request.Builder().url(url).build()).execute().use { response ->
                if (!response.isSuccessful) "" else response.body?.string().orEmpty()
            }
            if (searchJson.isBlank()) return@withContext emptyList()
            val obj = JsonParser.parseString(searchJson).asJsonObject
            val ids = obj
                .getAsJsonObject("esearchresult")
                ?.getAsJsonArray("idlist")
                ?.map { it.asString }
                .orEmpty()
                .distinct()
            fetchByPmids(ids).values.toList()
        } catch (e: Throwable) {
            emptyList()
        }
    }

    suspend fun fetchByPmid(pmid: String): PubMedMatch? {
        val trimmed = pmid.trim()
        if (trimmed.isBlank()) return null
        pmidCache[trimmed]?.let { return it }
        return fetchByPmids(listOf(trimmed))[trimmed]
    }

    private suspend fun fetchByPmids(pmids: List<String>): Map<String, PubMedMatch> = withContext(Dispatchers.IO) {
        val clean = pmids.map { it.trim() }.filter { it.isNotBlank() }.distinct()
        if (clean.isEmpty()) return@withContext emptyMap()

        val found = linkedMapOf<String, PubMedMatch>()
        clean.forEach { pmid -> pmidCache[pmid]?.let { found[pmid] = it } }
        val missing = clean.filterNot { found.containsKey(it) }
        if (missing.isEmpty()) return@withContext found

        missing.chunked(80).forEach { chunk ->
            runCatching {
                ncbiThrottle()
                val url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id=${chunk.joinToString(",")}"
                httpClient.newCall(Request.Builder().url(url).build()).execute().use { response ->
                    if (!response.isSuccessful) return@forEach
                    val root = JsonParser.parseString(response.body?.string().orEmpty()).asJsonObject
                    val resultObj = root.getAsJsonObject("result") ?: return@forEach
                    chunk.forEach { pmid ->
                        parseSummaryItem(pmid, resultObj.getAsJsonObject(pmid))?.let { match ->
                            pmidCache[pmid] = match
                            found[pmid] = match
                        }
                    }
                }
            }
        }
        found
    }

    private fun parseSummaryItem(pmid: String, item: JsonObject?): PubMedMatch? {
        val title = item?.get("title")?.takeIf { it.isJsonPrimitive }?.asString.orEmpty()
        val source = item?.get("source")?.takeIf { it.isJsonPrimitive }?.asString.orEmpty()
        val pubDate = item?.get("pubdate")?.takeIf { it.isJsonPrimitive }?.asString.orEmpty()
        val doi = item?.getAsJsonArray("articleids")
            ?.mapNotNull { el ->
                val obj = el.asJsonObject
                val type = obj.get("idtype")?.takeIf { it.isJsonPrimitive }?.asString.orEmpty()
                val value = obj.get("value")?.takeIf { it.isJsonPrimitive }?.asString.orEmpty()
                if (type.equals("doi", ignoreCase = true) && value.isNotBlank()) value else null
            }
            ?.firstOrNull()

        val authors = item?.getAsJsonArray("authors")
            ?.mapNotNull { el -> el.asJsonObject.get("name")?.takeIf { it.isJsonPrimitive }?.asString?.trim() }
            ?.take(3)
            .orEmpty()

        val canonical = buildString {
            if (authors.isNotEmpty()) append(authors.joinToString(", ")).append(". ")
            if (title.isNotBlank()) append(title).append(". ")
            append(source.ifBlank { "PubMed" })
            if (pubDate.isNotBlank()) append(". ").append(pubDate)
            append(". PMID: ").append(pmid)
            doi?.takeIf { it.isNotBlank() }?.let { append(". DOI: ").append(it) }
        }.trim()

        return PubMedMatch(pmid = pmid, doi = doi, articleTitle = title, canonicalReference = canonical)
    }

    // ---------------------------------------------------------------- scoring (identical thresholds to the thesis analyzer)

    private fun score(match: PubMedMatch, hints: SearchHints): Int {
        var score = 0
        val canonical = normalizeText(match.canonicalReference)
        val articleTitle = normalizeText(match.articleTitle)
        val titleHint = normalizeText(hints.titleHint.orEmpty())
        val cleaned = normalizeText(hints.cleanedText)
        val year = hints.year.orEmpty()

        if (hints.doi != null && match.doi != null && normalizeText(hints.doi) == normalizeText(match.doi)) score += 100
        if (year.isNotBlank() && canonical.contains(year)) score += 20

        val bestTitleOverlap = hints.titleCandidates
            .maxOfOrNull { candidate ->
                maxOf(
                    tokenOverlap(normalizeText(candidate), articleTitle),
                    tokenOverlap(normalizeText(candidate), canonical)
                )
            }
            ?: tokenOverlap(titleHint, articleTitle)

        score += bestTitleOverlap * 2
        score += tokenOverlap(cleaned, articleTitle)
        score += tokenOverlap(cleaned, canonical) / 2

        if (hints.titleCandidates.any { candidate ->
                val c = normalizeText(candidate)
                c.length >= 30 && articleTitle.contains(c.take(30))
            }
        ) score += 30
        if (canonical.contains(titleHint.take(40)) && titleHint.isNotBlank()) score += 10
        if (canonical.contains(cleaned.take(40)) && cleaned.isNotBlank()) score += 10

        return score
    }

    private fun acceptableMatch(match: PubMedMatch, hints: SearchHints): Boolean {
        val canonical = normalizeText(match.canonicalReference)
        val articleTitle = normalizeText(match.articleTitle)
        val titleHint = normalizeText(hints.titleHint.orEmpty())
        val cleaned = normalizeText(hints.cleanedText)
        val score = score(match, hints)

        if (hints.doi != null && match.doi != null && normalizeText(hints.doi) == normalizeText(match.doi)) return true

        val bestTitle = hints.titleCandidates.maxByOrNull { searchableTokenCount(it) } ?: hints.titleHint.orEmpty()
        val normalizedBest = normalizeText(bestTitle)
        if (normalizedBest.isNotBlank()) {
            val titleOverlap = maxOf(tokenOverlap(normalizedBest, articleTitle), tokenOverlap(normalizedBest, canonical))
            val tokenCount = searchableTokenCount(normalizedBest)
            val required = when {
                tokenCount <= 3 -> 10
                tokenCount <= 6 -> minimumTitleTokenOverlap
                else -> 20
            }
            val hasPhrase = normalizedBest.length >= 30 &&
                (articleTitle.contains(normalizedBest.take(30)) || canonical.contains(normalizedBest.take(30)))
            return score >= minimumSearchScore && (titleOverlap >= required || hasPhrase)
        }
        return score >= exactMatchScore && tokenOverlap(cleaned, canonical) >= minimumTitleTokenOverlap
    }

    private fun tokenOverlap(source: String, target: String): Int {
        if (source.isBlank() || target.isBlank()) return 0
        val sourceTokens = source.split(Regex("""\s+""")).filter { it.length >= 4 }.take(20).toSet()
        val targetTokens = target.split(Regex("""\s+""")).filter { it.length >= 4 }.toSet()
        if (sourceTokens.isEmpty() || targetTokens.isEmpty()) return 0
        return sourceTokens.count { it in targetTokens } * 5
    }
}
