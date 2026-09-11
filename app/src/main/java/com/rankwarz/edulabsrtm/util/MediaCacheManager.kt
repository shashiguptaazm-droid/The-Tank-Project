package com.rankwarz.edulabsrtm.util

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.pdf.PdfRenderer
import android.os.Handler
import android.os.Looper
import android.os.ParcelFileDescriptor
import android.util.Log
import android.util.LruCache
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit
import java.util.zip.ZipFile

object MediaCacheManager {
    private const val TAG = "MediaCacheManager"
    private val scope = CoroutineScope(Dispatchers.IO)
    private val mainHandler = Handler(Looper.getMainLooper())

    // Memory caches
    private val thumbMemoryCache = LruCache<String, Bitmap>(50)
    private val pageCountCache = ConcurrentHashMap<String, Int>()

    // Tracking active downloads to avoid duplicate network calls
    private val activeVideoDownloads = ConcurrentHashMap<String, Boolean>()
    private val activeDocDownloads = ConcurrentHashMap<String, Boolean>()

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .build()

    // -------------------------------------------------------------
    // DIRECTORIES
    // -------------------------------------------------------------
    fun getVideoDir(context: Context): File =
        File(context.cacheDir, "cached_videos").apply { if (!exists()) mkdirs() }

    fun getDocDir(context: Context): File =
        File(context.cacheDir, "cached_docs").apply { if (!exists()) mkdirs() }

    fun getThumbDir(context: Context): File =
        File(context.cacheDir, "cached_thumbs").apply { if (!exists()) mkdirs() }

    fun resolveFullUrl(pathOrUrl: String): String {
        return if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) {
            pathOrUrl
        } else {
            "https://medigyaan.xyz/Neurons/" + pathOrUrl.removePrefix("/")
        }
    }

    private fun getSafeFileName(url: String): String {
        val segment = url.substringAfterLast("/").substringBefore("?").ifBlank { "media_${url.hashCode()}" }
        return segment.replace(Regex("[^a-zA-Z0-9._-]"), "_")
    }

    // -------------------------------------------------------------
    // VIDEO CACHING & PLAYBACK ELIGIBILITY
    // -------------------------------------------------------------
    fun getCachedVideoFile(context: Context, url: String): File {
        val fullUrl = resolveFullUrl(url)
        val name = getSafeFileName(fullUrl)
        return File(getVideoDir(context), name)
    }

    fun isVideoDownloaded(context: Context, url: String): Boolean {
        val file = getCachedVideoFile(context, url)
        return file.exists() && file.length() > 0
    }

    fun isVideoDownloading(url: String): Boolean {
        return activeVideoDownloads[resolveFullUrl(url)] == true
    }

    fun downloadVideo(
        context: Context,
        url: String,
        onProgress: (Int) -> Unit,
        onComplete: (File?) -> Unit
    ) {
        val fullUrl = resolveFullUrl(url)
        val targetFile = getCachedVideoFile(context, fullUrl)

        if (targetFile.exists() && targetFile.length() > 0) {
            onComplete(targetFile)
            return
        }

        if (activeVideoDownloads[fullUrl] == true) {
            // Already downloading
            return
        }

        activeVideoDownloads[fullUrl] = true
        scope.launch {
            try {
                val request = Request.Builder().url(fullUrl).build()
                val response = httpClient.newCall(request).execute()

                if (!response.isSuccessful) {
                    throw IllegalStateException("HTTP ${response.code}")
                }

                val body = response.body ?: throw IllegalStateException("Empty body")
                val totalLength = body.contentLength().coerceAtLeast(1L)
                val tempFile = File(getVideoDir(context), targetFile.name + ".tmp")

                body.byteStream().use { input ->
                    FileOutputStream(tempFile).use { output ->
                        val buffer = ByteArray(64 * 1024)
                        var downloaded = 0L
                        var lastPercent = -1
                        while (true) {
                            val read = input.read(buffer)
                            if (read == -1) break
                            output.write(buffer, 0, read)
                            downloaded += read
                            val percent = ((downloaded * 100) / totalLength).toInt().coerceIn(0, 99)
                            if (percent != lastPercent) {
                                lastPercent = percent
                                mainHandler.post { onProgress(percent) }
                            }
                        }
                    }
                }

                if (tempFile.exists() && tempFile.length() > 0) {
                    tempFile.renameTo(targetFile)
                    mainHandler.post {
                        onProgress(100)
                        onComplete(targetFile)
                    }
                } else {
                    mainHandler.post { onComplete(null) }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Video download failed for $fullUrl: ${e.message}", e)
                mainHandler.post { onComplete(null) }
            } finally {
                activeVideoDownloads.remove(fullUrl)
            }
        }
    }

    // -------------------------------------------------------------
    // DOCUMENT PRELOADING & 1ST PAGE THUMBNAIL CONVERSION
    // -------------------------------------------------------------
    fun getCachedDocFile(context: Context, url: String): File {
        val fullUrl = resolveFullUrl(url)
        val name = getSafeFileName(fullUrl)
        return File(getDocDir(context), name)
    }

    fun isDocDownloaded(context: Context, url: String): Boolean {
        val file = getCachedDocFile(context, url)
        return file.exists() && file.length() > 0
    }

    fun getCachedPageCount(url: String): Int? {
        return pageCountCache[resolveFullUrl(url)]
    }

    fun getCachedThumbnail(url: String): Bitmap? {
        return thumbMemoryCache.get(resolveFullUrl(url))
    }

    /**
     * Preloads the document in the background, converts page 1 to an image bitmap,
     * and delivers it to the callback on the main thread.
     */
    fun preloadDocumentAndGetFirstPage(
        context: Context,
        url: String,
        callback: (Bitmap?, Int /* pageCount */) -> Unit
    ) {
        val fullUrl = resolveFullUrl(url)

        // 1. Check memory cache first
        val cachedMem = thumbMemoryCache.get(fullUrl)
        val cachedPages = pageCountCache[fullUrl] ?: 1
        if (cachedMem != null) {
            callback(cachedMem, cachedPages)
            return
        }

        // 2. Check disk thumbnail cache
        val thumbDiskFile = File(getThumbDir(context), "thumb_${fullUrl.hashCode()}.png")
        if (thumbDiskFile.exists() && thumbDiskFile.length() > 0) {
            scope.launch {
                try {
                    val diskBitmap = BitmapFactory.decodeFile(thumbDiskFile.absolutePath)
                    if (diskBitmap != null) {
                        thumbMemoryCache.put(fullUrl, diskBitmap)
                        mainHandler.post { callback(diskBitmap, pageCountCache[fullUrl] ?: 1) }
                        return@launch
                    }
                } catch (_: Exception) {}
            }
        }

        val docFile = getCachedDocFile(context, fullUrl)

        // 3. If document is already cached, render immediately
        if (docFile.exists() && docFile.length() > 0) {
            scope.launch {
                renderAndCacheFirstPage(context, fullUrl, docFile, callback)
            }
            return
        }

        // 4. Document not cached yet: download and preload in background
        if (activeDocDownloads[fullUrl] == true) return
        activeDocDownloads[fullUrl] = true

        scope.launch {
            try {
                val request = Request.Builder().url(fullUrl).build()
                val response = httpClient.newCall(request).execute()

                if (response.isSuccessful && response.body != null) {
                    val tempFile = File(getDocDir(context), docFile.name + ".tmp")
                    response.body!!.byteStream().use { input ->
                        FileOutputStream(tempFile).use { output ->
                            input.copyTo(output)
                        }
                    }
                    if (tempFile.exists() && tempFile.length() > 0) {
                        tempFile.renameTo(docFile)
                        renderAndCacheFirstPage(context, fullUrl, docFile, callback)
                    } else {
                        mainHandler.post { callback(null, 1) }
                    }
                } else {
                    mainHandler.post { callback(null, 1) }
                }
            } catch (e: Exception) {
                Log.d(TAG, "Document preload failed for $fullUrl: ${e.message}")
                mainHandler.post { callback(null, 1) }
            } finally {
                activeDocDownloads.remove(fullUrl)
            }
        }
    }

    private fun renderAndCacheFirstPage(
        context: Context,
        fullUrl: String,
        file: File,
        callback: (Bitmap?, Int) -> Unit
    ) {
        val ext = file.extension.lowercase()
        var bitmap: Bitmap? = null
        var pageCount = 1

        try {
            if (ext == "pdf") {
                // Render first page using native PdfRenderer
                var pfd: ParcelFileDescriptor? = null
                var renderer: PdfRenderer? = null
                var page: PdfRenderer.Page? = null
                try {
                    pfd = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY)
                    renderer = PdfRenderer(pfd)
                    pageCount = renderer.pageCount
                    if (pageCount > 0) {
                        page = renderer.openPage(0)
                        val targetWidth = 480
                        val targetHeight = (targetWidth * page.height / page.width.toFloat()).toInt().coerceIn(320, 640)
                        bitmap = Bitmap.createBitmap(targetWidth, targetHeight, Bitmap.Config.ARGB_8888)
                        bitmap.eraseColor(Color.WHITE)
                        page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                    }
                } finally {
                    try { page?.close() } catch (_: Exception) {}
                    try { renderer?.close() } catch (_: Exception) {}
                    try { pfd?.close() } catch (_: Exception) {}
                }
            } else if (ext in listOf("docx", "pptx", "xlsx")) {
                // Check if OpenXML archive has an embedded thumbnail
                try {
                    ZipFile(file).use { zip ->
                        val thumbEntry = zip.getEntry("docProps/thumbnail.jpeg")
                            ?: zip.getEntry("docProps/thumbnail.png")
                            ?: zip.getEntry("docProps/thumbnail.wmf")
                        if (thumbEntry != null) {
                            zip.getInputStream(thumbEntry).use { input ->
                                bitmap = BitmapFactory.decodeStream(input)
                            }
                        }
                    }
                } catch (_: Exception) {}
            }

            // Fallback: create a crisp stylized document page preview if no direct renderer
            if (bitmap == null) {
                bitmap = generateDocumentSheetPreview(file.name, ext)
            }

            if (bitmap != null) {
                thumbMemoryCache.put(fullUrl, bitmap)
                pageCountCache[fullUrl] = pageCount

                // Save to private thumbnail disk cache (NOT in user gallery)
                try {
                    val thumbDiskFile = File(getThumbDir(context), "thumb_${fullUrl.hashCode()}.png")
                    FileOutputStream(thumbDiskFile).use { out ->
                        bitmap.compress(Bitmap.CompressFormat.PNG, 85, out)
                    }
                } catch (_: Exception) {}

                mainHandler.post { callback(bitmap, pageCount) }
            } else {
                mainHandler.post { callback(null, 1) }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error rendering first page for ${file.name}: ${e.message}", e)
            mainHandler.post { callback(null, 1) }
        }
    }

    /**
     * Generates a clean, modern white document sheet graphic with ruled content lines
     * for documents where a direct renderer is not available.
     */
    private fun generateDocumentSheetPreview(fileName: String, ext: String): Bitmap {
        val width = 400
        val height = 300
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)

        // Background
        canvas.drawColor(Color.parseColor("#ECEFF1"))

        // White sheet in center with rounded corners
        val sheetPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.WHITE
            setShadowLayer(8f, 0f, 4f, Color.parseColor("#33000000"))
        }
        val sheetRect = RectF(40f, 20f, width - 40f, height - 20f)
        canvas.drawRoundRect(sheetRect, 12f, 12f, sheetPaint)

        // Accent header bar
        val accentColor = when (ext) {
            "pdf" -> Color.parseColor("#E53935")
            "doc", "docx" -> Color.parseColor("#1E88E5")
            "ppt", "pptx" -> Color.parseColor("#FB8C00")
            "xls", "xlsx" -> Color.parseColor("#43A047")
            else -> Color.parseColor("#546E7A")
        }
        val headerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = accentColor }
        canvas.drawRoundRect(RectF(60f, 40f, width - 60f, 65f), 6f, 6f, headerPaint)

        // Content lines
        val linePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.parseColor("#CFD8DC") }
        canvas.drawRoundRect(RectF(60f, 90f, width - 100f, 102f), 4f, 4f, linePaint)
        canvas.drawRoundRect(RectF(60f, 120f, width - 80f, 132f), 4f, 4f, linePaint)
        canvas.drawRoundRect(RectF(60f, 150f, width - 120f, 162f), 4f, 4f, linePaint)
        canvas.drawRoundRect(RectF(60f, 180f, width - 70f, 192f), 4f, 4f, linePaint)
        canvas.drawRoundRect(RectF(60f, 210f, width - 140f, 222f), 4f, 4f, linePaint)

        return bitmap
    }
}
