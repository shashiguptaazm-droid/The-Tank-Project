package com.rankwarz.edulabsrtm.util

import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.util.LruCache
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import org.jsoup.Jsoup
import java.util.regex.Pattern

data class LinkPreviewData(
    val url: String,
    val title: String,
    val description: String,
    val imageUrl: String?,
    val domain: String
)

object LinkPreviewHelper {
    private const val TAG = "LinkPreviewHelper"
    private val memoryCache = LruCache<String, LinkPreviewData>(100)
    private val scope = CoroutineScope(Dispatchers.IO)
    private val mainHandler = Handler(Looper.getMainLooper())

    private val URL_PATTERN = Pattern.compile(
        "\\b(https?://[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}(/[^\\s<>\"]*)?)",
        Pattern.CASE_INSENSITIVE
    )

    fun extractFirstUrl(text: String): String? {
        if (text.isBlank()) return null
        val matcher = URL_PATTERN.matcher(text)
        return if (matcher.find()) matcher.group(1) else null
    }

    fun getCachedPreview(url: String): LinkPreviewData? {
        return memoryCache.get(url)
    }

    fun fetchPreview(url: String, callback: (LinkPreviewData?) -> Unit) {
        val cached = memoryCache.get(url)
        if (cached != null) {
            callback(cached)
            return
        }

        scope.launch {
            try {
                val host = Uri.parse(url).host?.removePrefix("www.") ?: "link"
                val doc = Jsoup.connect(url)
                    .userAgent("Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")
                    .timeout(4000)
                    .followRedirects(true)
                    .get()

                val ogTitle = doc.select("meta[property=og:title]").attr("content").trim()
                val twitterTitle = doc.select("meta[name=twitter:title]").attr("content").trim()
                val docTitle = doc.title().trim()
                val finalTitle = ogTitle.ifBlank { twitterTitle.ifBlank { docTitle } }

                val ogDesc = doc.select("meta[property=og:description]").attr("content").trim()
                val twitterDesc = doc.select("meta[name=twitter:description]").attr("content").trim()
                val metaDesc = doc.select("meta[name=description]").attr("content").trim()
                val finalDesc = ogDesc.ifBlank { twitterDesc.ifBlank { metaDesc } }

                var ogImage = doc.select("meta[property=og:image]").attr("abs:content").trim()
                if (ogImage.isBlank()) {
                    ogImage = doc.select("meta[name=twitter:image]").attr("abs:content").trim()
                }
                if (ogImage.isBlank()) {
                    ogImage = doc.select("link[rel=image_src]").attr("abs:href").trim()
                }

                val siteName = doc.select("meta[property=og:site_name]").attr("content").trim()
                val finalDomain = siteName.ifBlank { host }

                if (finalTitle.isNotBlank() || finalDesc.isNotBlank() || ogImage.isNotBlank()) {
                    val previewData = LinkPreviewData(
                        url = url,
                        title = if (finalTitle.isNotBlank()) finalTitle else host,
                        description = finalDesc,
                        imageUrl = ogImage.ifBlank { null },
                        domain = finalDomain
                    )
                    memoryCache.put(url, previewData)
                    mainHandler.post { callback(previewData) }
                } else {
                    mainHandler.post { callback(null) }
                }
            } catch (e: Exception) {
                Log.d(TAG, "Failed to load link preview for $url: ${e.message}")
                mainHandler.post { callback(null) }
            }
        }
    }
}
