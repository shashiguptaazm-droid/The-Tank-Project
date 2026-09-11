package com.rankwarz.edulabsrtm

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.pdf.PdfDocument
import android.net.Uri
import com.rankwarz.edulabsrtm.model.PageInsight
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Exports a list of [PageInsight] objects into a PDF file.
 *
 * @param context Android context
 * @param uri Destination URI for the PDF file (e.g. from CreateDocument)
 * @param thesisId Identifier of the thesis
 * @param provider Name of the AI provider used
 * @param pages List of page insights to export
 */
class PdfExporter {

    private data class PdfPageState(
        val page: PdfDocument.Page,
        val canvas: Canvas,
        val pageNumber: Int,
        var y: Float
    )

    companion object {
        private const val PDF_WIDTH = 595
        private const val PDF_HEIGHT = 842
        private const val MARGIN_LEFT = 40f
        private const val MARGIN_RIGHT = 40f
        private const val MARGIN_BOTTOM = 40f
    }

    suspend fun export(
        context: Context,
        uri: Uri,
        thesisId: Int,
        provider: String,
        pages: List<PageInsight>
    ) = withContext(Dispatchers.IO) {
        val document = PdfDocument()
        try {
            var pageNumber = 1

            pageNumber = renderCoverPage(
                document = document,
                pageNumber = pageNumber,
                thesisId = thesisId,
                provider = provider,
                pageCount = pages.size
            )

            pageNumber = renderTocPages(
                document = document,
                pageNumber = pageNumber,
                pages = pages
            )

            if (pages.isEmpty()) {
                pageNumber = renderSingleInfoPage(
                    document = document,
                    pageNumber = pageNumber,
                    title = "No analysis data",
                    body = "Run analysis first."
                )
            } else {
                pages.forEach { insight ->
                    pageNumber = renderInsightToPdf(document, pageNumber, insight)
                }
            }

            context.contentResolver.openOutputStream(uri)?.use { output ->
                document.writeTo(output)
            } ?: throw IllegalStateException("Unable to open output stream")
        } finally {
            document.close()
        }
    }

    private fun renderCoverPage(
        document: PdfDocument,
        pageNumber: Int,
        thesisId: Int,
        provider: String,
        pageCount: Int
    ): Int {
        val page = document.startPage(
            PdfDocument.PageInfo.Builder(PDF_WIDTH, PDF_HEIGHT, pageNumber).create()
        )
        val canvas = page.canvas

        val titlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            textSize = 26f
            isFakeBoldText = true
            color = Color.rgb(33, 37, 41)
            textAlign = Paint.Align.CENTER
        }

        val subPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            textSize = 14f
            color = Color.rgb(73, 80, 87)
            textAlign = Paint.Align.CENTER
        }

        val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            textSize = 12f
            isFakeBoldText = true
            color = Color.rgb(0, 123, 255)
            textAlign = Paint.Align.CENTER
        }

        val rulePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            strokeWidth = 2f
            color = Color.rgb(222, 226, 230)
        }

        canvas.drawText("Thesis Analysis Report", PDF_WIDTH / 2f, 180f, titlePaint)
        canvas.drawLine(120f, 210f, PDF_WIDTH - 120f, 210f, rulePaint)
        canvas.drawText("Thesis ID: $thesisId", PDF_WIDTH / 2f, 255f, labelPaint)
        canvas.drawText("AI Provider: $provider", PDF_WIDTH / 2f, 285f, subPaint)
        canvas.drawText("Generated: ${now()}", PDF_WIDTH / 2f, 315f, subPaint)
        canvas.drawText("Pages analyzed: $pageCount", PDF_WIDTH / 2f, 345f, subPaint)

        drawFooter(canvas, pageNumber)
        document.finishPage(page)
        return pageNumber + 1
    }

    private fun renderTocPages(
        document: PdfDocument,
        pageNumber: Int,
        pages: List<PageInsight>
    ): Int {
        if (pages.isEmpty()) return pageNumber

        var currentPageNumber = pageNumber
        var index = 0

        while (index < pages.size) {
            val page = document.startPage(
                PdfDocument.PageInfo.Builder(PDF_WIDTH, PDF_HEIGHT, currentPageNumber).create()
            )
            val canvas = page.canvas
            drawHeader(canvas, "Table of Contents", "Pages in thesis order")

            val titlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                textSize = 15f
                isFakeBoldText = true
                color = Color.rgb(33, 37, 41)
            }
            val bodyPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                textSize = 11f
                color = Color.rgb(33, 37, 41)
            }
            val mutedPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                textSize = 10f
                color = Color.rgb(108, 117, 125)
            }

            var y = 155f
            canvas.drawText("Section", MARGIN_LEFT, y, titlePaint)
            canvas.drawText("Type", 360f, y, titlePaint)
            canvas.drawText("Thesis Page", 450f, y, titlePaint)
            y += 18f

            val lineHeight = bodyPaint.fontSpacing + 3f

            while (index < pages.size) {
                val insight = pages[index]
                if (y > PDF_HEIGHT - MARGIN_BOTTOM - 30f) break

                canvas.drawText(trimText(insight.heading, 40), MARGIN_LEFT, y, bodyPaint)
                canvas.drawText(trimText(insight.sectionType.uppercase(Locale.getDefault()), 12), 360f, y, mutedPaint)
                canvas.drawText(insight.pageNo.toString(), 470f, y, bodyPaint)
                y += lineHeight
                index++
            }

            drawFooter(canvas, currentPageNumber)
            document.finishPage(page)
            currentPageNumber++
        }

        return currentPageNumber
    }

    private fun renderInsightToPdf(
        document: PdfDocument,
        startPageNumber: Int,
        insight: PageInsight
    ): Int {
        val titlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            textSize = 20f
            isFakeBoldText = true
            color = Color.rgb(33, 37, 41)
        }

        val metaPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            textSize = 11f
            color = Color.rgb(108, 117, 125)
        }

        val sectionTitlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            textSize = 14f
            isFakeBoldText = true
            color = Color.rgb(33, 37, 41)
        }

        val bodyPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            textSize = 12f
            color = Color.rgb(33, 37, 41)
        }

        val smallItalicPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            textSize = 11f
            color = Color.rgb(73, 80, 87)
        }

        val linePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            strokeWidth = 1f
            color = Color.rgb(222, 226, 230)
        }

        val contentWidth = PDF_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
        val bodyLineHeight = bodyPaint.fontSpacing
        val sectionLineHeight = sectionTitlePaint.fontSpacing

        var state = startContentPage(
            document = document,
            pageNumber = startPageNumber,
            insight = insight,
            titlePaint = titlePaint,
            metaPaint = metaPaint,
            linePaint = linePaint
        )

        state = drawParagraph(
            document = document,
            state = state,
            insight = insight,
            text = "Summary: ${normalizeText(insight.summary)}",
            paint = smallItalicPaint,
            maxWidth = contentWidth,
            lineHeight = smallItalicPaint.fontSpacing,
            titlePaint = titlePaint,
            metaPaint = metaPaint,
            linePaint = linePaint,
            extraSpacing = 8f
        )

        state = drawParagraph(
            document = document,
            state = state,
            insight = insight,
            text = "AI Comment: ${normalizeText(insight.aiComment)}",
            paint = smallItalicPaint,
            maxWidth = contentWidth,
            lineHeight = smallItalicPaint.fontSpacing,
            titlePaint = titlePaint,
            metaPaint = metaPaint,
            linePaint = linePaint,
            extraSpacing = 12f
        )

        if (insight.subsections.isNotEmpty()) {
            state = ensureSpace(
                document,
                state,
                sectionLineHeight + 8f,
                insight,
                titlePaint,
                metaPaint,
                linePaint
            )
            state.canvas.drawText("Organized Subsections", MARGIN_LEFT, state.y, sectionTitlePaint)
            state.y += sectionLineHeight

            for (sub in insight.subsections) {
                if (sub.subheading.isNotBlank()) {
                    state = drawParagraph(
                        document = document,
                        state = state,
                        insight = insight,
                        text = normalizeText(sub.subheading),
                        paint = sectionTitlePaint,
                        maxWidth = contentWidth,
                        lineHeight = sectionLineHeight,
                        titlePaint = titlePaint,
                        metaPaint = metaPaint,
                        linePaint = linePaint,
                        extraSpacing = 3f
                    )
                }

                for (point in sub.points) {
                    state = drawParagraph(
                        document = document,
                        state = state,
                        insight = insight,
                        text = "• ${normalizeText(point)}",
                        paint = bodyPaint,
                        maxWidth = contentWidth - 12f,
                        lineHeight = bodyLineHeight,
                        titlePaint = titlePaint,
                        metaPaint = metaPaint,
                        linePaint = linePaint,
                        indentX = 12f,
                        extraSpacing = 2f
                    )
                }
            }

            state.y += 6f
        }

        state = ensureSpace(
            document,
            state,
            sectionLineHeight + 8f,
            insight,
            titlePaint,
            metaPaint,
            linePaint
        )
        state.canvas.drawText("Exact Text", MARGIN_LEFT, state.y, sectionTitlePaint)
        state.y += sectionLineHeight

        state = drawParagraph(
            document = document,
            state = state,
            insight = insight,
            text = normalizeText(insight.value.ifBlank { "No exact text available." }),
            paint = bodyPaint,
            maxWidth = contentWidth,
            lineHeight = bodyLineHeight,
            titlePaint = titlePaint,
            metaPaint = metaPaint,
            linePaint = linePaint,
            extraSpacing = 6f
        )

        drawFooter(state.canvas, state.pageNumber)
        document.finishPage(state.page)
        return state.pageNumber + 1
    }

    private fun renderSingleInfoPage(
        document: PdfDocument,
        pageNumber: Int,
        title: String,
        body: String
    ): Int {
        val page = document.startPage(
            PdfDocument.PageInfo.Builder(PDF_WIDTH, PDF_HEIGHT, pageNumber).create()
        )
        val canvas = page.canvas

        drawHeader(canvas, title, "Export placeholder")

        val bodyPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            textSize = 12f
            color = Color.rgb(33, 37, 41)
        }

        val lineHeight = bodyPaint.fontSpacing
        var y = 170f
        val wrapped = wrapText(bodyPaint, normalizeText(body), PDF_WIDTH - MARGIN_LEFT - MARGIN_RIGHT)

        for (line in wrapped) {
            if (y > PDF_HEIGHT - MARGIN_BOTTOM - 20f) break
            if (line.isNotBlank()) {
                canvas.drawText(line, MARGIN_LEFT, y, bodyPaint)
            }
            y += lineHeight
        }

        drawFooter(canvas, pageNumber)
        document.finishPage(page)
        return pageNumber + 1
    }

    private fun startContentPage(
        document: PdfDocument,
        pageNumber: Int,
        insight: PageInsight,
        titlePaint: Paint,
        metaPaint: Paint,
        linePaint: Paint
    ): PdfPageState {
        val page = document.startPage(
            PdfDocument.PageInfo.Builder(PDF_WIDTH, PDF_HEIGHT, pageNumber).create()
        )
        val canvas = page.canvas

        canvas.drawRect(0f, 0f, PDF_WIDTH.toFloat(), 124f, Paint().apply {
            color = Color.rgb(248, 249, 250)
            style = Paint.Style.FILL
        })

        canvas.drawText(
            "Thesis Page ${insight.pageNo}",
            MARGIN_LEFT,
            50f,
            metaPaint
        )

        canvas.drawText(
            insight.heading,
            MARGIN_LEFT,
            82f,
            titlePaint
        )

        canvas.drawText(
            "Type: ${insight.sectionType}",
            MARGIN_LEFT,
            106f,
            metaPaint
        )

        canvas.drawLine(
            MARGIN_LEFT,
            120f,
            PDF_WIDTH - MARGIN_RIGHT,
            120f,
            linePaint
        )

        return PdfPageState(page = page, canvas = canvas, pageNumber = pageNumber, y = 142f)
    }

    private fun drawHeader(canvas: Canvas, title: String, subtitle: String) {
        val titlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            textSize = 18f
            isFakeBoldText = true
            color = Color.rgb(33, 37, 41)
        }
        val subPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            textSize = 11f
            color = Color.rgb(108, 117, 125)
        }
        canvas.drawRect(0f, 0f, PDF_WIDTH.toFloat(), 124f, Paint().apply {
            color = Color.rgb(248, 249, 250)
            style = Paint.Style.FILL
        })
        canvas.drawText(title, MARGIN_LEFT, 72f, titlePaint)
        canvas.drawText(subtitle, MARGIN_LEFT, 102f, subPaint)
    }

    private fun ensureSpace(
        document: PdfDocument,
        state: PdfPageState,
        requiredHeight: Float,
        insight: PageInsight,
        titlePaint: Paint,
        metaPaint: Paint,
        linePaint: Paint
    ): PdfPageState {
        return if (state.y + requiredHeight > PDF_HEIGHT - MARGIN_BOTTOM) {
            drawFooter(state.canvas, state.pageNumber)
            document.finishPage(state.page)
            startContentPage(
                document = document,
                pageNumber = state.pageNumber + 1,
                insight = insight,
                titlePaint = titlePaint,
                metaPaint = metaPaint,
                linePaint = linePaint
            )
        } else {
            state
        }
    }

    private fun drawParagraph(
        document: PdfDocument,
        state: PdfPageState,
        insight: PageInsight,
        text: String,
        paint: Paint,
        maxWidth: Float,
        lineHeight: Float,
        titlePaint: Paint,
        metaPaint: Paint,
        linePaint: Paint,
        indentX: Float = 0f,
        extraSpacing: Float = 4f
    ): PdfPageState {
        var currentState = state
        val paragraphs = text.split("\n")

        for (paragraph in paragraphs) {
            val wrapped = wrapText(paint, paragraph, maxWidth)

            if (wrapped.isEmpty()) {
                currentState = ensureSpace(
                    document,
                    currentState,
                    lineHeight,
                    insight,
                    titlePaint,
                    metaPaint,
                    linePaint
                )
                currentState.y += lineHeight * 0.6f
                continue
            }

            for (line in wrapped) {
                currentState = ensureSpace(
                    document,
                    currentState,
                    lineHeight,
                    insight,
                    titlePaint,
                    metaPaint,
                    linePaint
                )
                if (line.isNotBlank()) {
                    currentState.canvas.drawText(
                        line,
                        MARGIN_LEFT + indentX,
                        currentState.y,
                        paint
                    )
                }
                currentState.y += lineHeight
            }

            currentState.y += extraSpacing
        }

        return currentState
    }

    private fun wrapText(paint: Paint, text: String, maxWidth: Float): List<String> {
        val result = mutableListOf<String>()
        val paragraphs = text.split("\n")

        for (paragraph in paragraphs) {
            val trimmed = paragraph.trim()
            if (trimmed.isBlank()) {
                result.add("")
                continue
            }

            val words = trimmed.split(Regex("\\s+"))
            var line = StringBuilder()

            for (word in words) {
                val testLine = if (line.isEmpty()) word else "${line} $word"

                if (paint.measureText(testLine) <= maxWidth) {
                    line = StringBuilder(testLine)
                } else {
                    if (line.isNotEmpty()) {
                        result.add(line.toString())
                        line = StringBuilder(word)
                    } else {
                        // Force-break very long words
                        var temp = ""
                        for (ch in word) {
                            val test = temp + ch
                            if (paint.measureText(test) <= maxWidth) {
                                temp = test
                            } else {
                                if (temp.isNotEmpty()) result.add(temp)
                                temp = ch.toString()
                            }
                        }
                        line = StringBuilder(temp)
                    }
                }
            }

            if (line.isNotEmpty()) {
                result.add(line.toString())
            }

            result.add("")
        }

        return result
    }

    private fun drawFooter(canvas: Canvas, pageNumber: Int) {
        val footerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            textSize = 10f
            color = Color.rgb(108, 117, 125)
            textAlign = Paint.Align.CENTER
        }
        val linePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            strokeWidth = 1f
            color = Color.rgb(222, 226, 230)
        }

        canvas.drawLine(
            MARGIN_LEFT,
            PDF_HEIGHT - 38f,
            PDF_WIDTH - MARGIN_RIGHT,
            PDF_HEIGHT - 38f,
            linePaint
        )
        canvas.drawText(
            "Page $pageNumber",
            PDF_WIDTH / 2f,
            PDF_HEIGHT - 18f,
            footerPaint
        )
    }

    private fun trimText(text: String, maxChars: Int): String {
        val clean = text.replace(Regex("\\s+"), " ").trim()
        return if (clean.length <= maxChars) clean else clean.substring(0, maxChars - 1) + "…"
    }

    private fun normalizeText(text: String): String {
        return text
            .replace("\r\n", "\n")
            .replace(Regex("\\s{2,}"), " ")
            .replace(" . ", ".\n")
            .replace(" ? ", "?\n")
            .replace(" ! ", "!\n")
            .trim()
    }

    private fun now(): String {
        val sdf = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault())
        return sdf.format(Date())
    }
}