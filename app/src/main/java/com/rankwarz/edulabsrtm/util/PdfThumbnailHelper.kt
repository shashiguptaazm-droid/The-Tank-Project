package com.rankwarz.edulabsrtm.util

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.os.Handler
import android.os.Looper
import android.os.ParcelFileDescriptor
import android.util.Log
import android.util.LruCache
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.io.File

object PdfThumbnailHelper {
    private const val TAG = "PdfThumbnailHelper"
    private val bitmapCache = LruCache<String, Bitmap>(30)
    private val scope = CoroutineScope(Dispatchers.IO)
    private val mainHandler = Handler(Looper.getMainLooper())

    fun getCachedThumbnail(key: String): Bitmap? {
        return bitmapCache.get(key)
    }

    fun renderFirstPage(pdfFile: File, callback: (Bitmap?) -> Unit) {
        val cacheKey = pdfFile.absolutePath + "_" + pdfFile.lastModified()
        val cached = bitmapCache.get(cacheKey)
        if (cached != null) {
            callback(cached)
            return
        }

        if (!pdfFile.exists() || pdfFile.length() == 0L) {
            callback(null)
            return
        }

        scope.launch {
            var fileDescriptor: ParcelFileDescriptor? = null
            var pdfRenderer: PdfRenderer? = null
            var page: PdfRenderer.Page? = null

            try {
                fileDescriptor = ParcelFileDescriptor.open(pdfFile, ParcelFileDescriptor.MODE_READ_ONLY)
                pdfRenderer = PdfRenderer(fileDescriptor)
                
                if (pdfRenderer.pageCount > 0) {
                    page = pdfRenderer.openPage(0)
                    val width = 240
                    val height = (width * page.height / page.width.toFloat()).toInt().coerceIn(180, 320)
                    val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
                    bitmap.eraseColor(Color.WHITE)
                    
                    page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                    bitmapCache.put(cacheKey, bitmap)
                    mainHandler.post { callback(bitmap) }
                } else {
                    mainHandler.post { callback(null) }
                }
            } catch (e: Exception) {
                Log.d(TAG, "PdfRenderer error for ${pdfFile.name}: ${e.message}")
                mainHandler.post { callback(null) }
            } finally {
                try { page?.close() } catch (_: Exception) {}
                try { pdfRenderer?.close() } catch (_: Exception) {}
                try { fileDescriptor?.close() } catch (_: Exception) {}
            }
        }
    }
}
