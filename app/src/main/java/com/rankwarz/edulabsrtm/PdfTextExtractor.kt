package com.rankwarz.edulabsrtm.utils

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.os.ParcelFileDescriptor
import android.util.Log
import com.google.android.gms.tasks.Tasks
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.text.PDFTextStripper
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.io.InputStream

/**
 * High-reliability PDF text extractor:
 * 1. Safely copies streams/URIs to a temporary cached file for seekable, robust access.
 * 2. Initializes PdfBox (PDFBoxResourceLoader) on demand.
 * 3. Extracts embedded text using PdfBox PDFTextStripper.
 * 4. If extracted text is empty or < 50 characters (e.g. scanned PDF, photocopy, images),
 *    falls back to rendering pages via Android's native PdfRenderer and running Google ML Kit OCR.
 */
object PdfTextExtractor {

    private const val TAG = "PdfTextExtractor"

    suspend fun extractText(context: Context, inputStream: InputStream): String = withContext(Dispatchers.IO) {
        var tempFile: File? = null
        try {
            tempFile = File.createTempFile("pdf_in_", ".pdf", context.cacheDir)
            FileOutputStream(tempFile).use { out ->
                inputStream.copyTo(out)
            }
            extractFromFile(context, tempFile)
        } catch (e: Exception) {
            Log.e(TAG, "Failed extracting text from stream: ${e.message}", e)
            ""
        } finally {
            try { tempFile?.delete() } catch (_: Exception) {}
        }
    }

    suspend fun extractText(context: Context, uri: Uri): String = withContext(Dispatchers.IO) {
        var tempFile: File? = null
        try {
            tempFile = File.createTempFile("pdf_uri_", ".pdf", context.cacheDir)
            val resolver = context.contentResolver
            resolver.openInputStream(uri)?.use { input ->
                FileOutputStream(tempFile).use { output ->
                    input.copyTo(output)
                }
            }
            extractFromFile(context, tempFile)
        } catch (e: Exception) {
            Log.e(TAG, "Failed extracting text from uri ($uri): ${e.message}", e)
            ""
        } finally {
            try { tempFile?.delete() } catch (_: Exception) {}
        }
    }

    suspend fun extractText(context: Context, file: File): String = withContext(Dispatchers.IO) {
        extractFromFile(context, file)
    }

    private fun extractFromFile(context: Context, file: File): String {
        if (!file.exists() || file.length() == 0L) {
            Log.w(TAG, "File does not exist or is empty: ${file.absolutePath}")
            return ""
        }

        // 1. Ensure PDFBox is initialized
        try {
            if (!PDFBoxResourceLoader.isReady()) {
                PDFBoxResourceLoader.init(context.applicationContext)
            }
        } catch (e: Exception) {
            Log.w(TAG, "PDFBoxResourceLoader init note: ${e.message}")
        }

        // 2. Try PdfBox text extraction
        var extracted = ""
        var document: PDDocument? = null
        try {
            document = PDDocument.load(file)
            val stripper = PDFTextStripper()
            stripper.sortByPosition = true
            extracted = stripper.getText(document)?.trim().orEmpty()
            Log.d(TAG, "PdfBox extracted ${extracted.length} characters from ${file.name}")
        } catch (e: Exception) {
            Log.w(TAG, "PdfBox text extraction error: ${e.message}")
        } finally {
            try {
                document?.close()
            } catch (e: Exception) {
                Log.w(TAG, "Error closing PDDocument: ${e.message}")
            }
        }

        // If sufficient text was found, return it immediately
        if (extracted.length >= 50) {
            return extracted
        }

        // 3. Fallback: Scanned PDF OCR using native PdfRenderer + ML Kit
        Log.i(TAG, "PdfBox extracted only ${extracted.length} chars; falling back to native PdfRenderer + ML Kit OCR...")
        val ocrText = extractViaOcr(file)
        return if (ocrText.isNotBlank()) ocrText else extracted
    }

    private fun extractViaOcr(file: File): String {
        var pfd: ParcelFileDescriptor? = null
        var renderer: PdfRenderer? = null
        val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
        val sb = StringBuilder()

        try {
            pfd = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY)
            renderer = PdfRenderer(pfd)
            val pageCount = renderer.pageCount
            val maxPages = pageCount.coerceAtMost(15) // OCR up to 15 pages

            Log.d(TAG, "Running OCR on $maxPages / $pageCount pages...")

            for (i in 0 until maxPages) {
                var page: PdfRenderer.Page? = null
                try {
                    page = renderer.openPage(i)
                    val width = 1200
                    val height = (width * page.height / page.width.toFloat()).toInt().coerceAtLeast(100)
                    val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
                    bitmap.eraseColor(Color.WHITE)
                    page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)

                    val image = InputImage.fromBitmap(bitmap, 0)
                    val visionText = Tasks.await(recognizer.process(image))
                    val text = visionText.text.trim()
                    if (text.isNotBlank()) {
                        sb.append("--- [Page ${i + 1}] ---\n").append(text).append("\n\n")
                    }
                    bitmap.recycle()
                } catch (e: Exception) {
                    Log.w(TAG, "OCR page $i error: ${e.message}")
                } finally {
                    try { page?.close() } catch (_: Exception) {}
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "extractViaOcr failed: ${e.message}", e)
        } finally {
            try { recognizer.close() } catch (_: Exception) {}
            try { renderer?.close() } catch (_: Exception) {}
            try { pfd?.close() } catch (_: Exception) {}
        }

        val result = sb.toString().trim()
        Log.d(TAG, "OCR extraction completed with ${result.length} characters")
        return result
    }
}