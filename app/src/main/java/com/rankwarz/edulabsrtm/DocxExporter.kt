package com.rankwarz.edulabsrtm

import android.content.Context
import android.net.Uri
import com.rankwarz.edulabsrtm.model.PageInsight
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.apache.poi.xwpf.usermodel.ParagraphAlignment
import org.apache.poi.xwpf.usermodel.XWPFDocument
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale

class DocxExporter {

    suspend fun export(
        context: Context,
        uri: Uri,
        thesisId: Int,
        provider: String,
        pages: List<PageInsight>
    ) = withContext(Dispatchers.IO) {
        val document = XWPFDocument()
        try {
            // Add title page and spacing
            addTitlePage(document, thesisId, provider, pages.size)

            // Use a clear separation for content
            if (pages.isEmpty()) {
                addParagraph(document, "No analysis data available.")
            } else {
                addToc(document, pages)
                pages.forEach { insight ->
                    addSection(document, insight)
                }
            }

            context.contentResolver.openOutputStream(uri)?.use { output ->
                document.write(output)
            } ?: throw IllegalStateException("Unable to open output stream")
        } finally {
            document.close()
        }
    }

    private fun addTitlePage(doc: XWPFDocument, thesisId: Int, provider: String, pageCount: Int) {
        addHeading(doc, "Thesis Analysis Report", 1, ParagraphAlignment.CENTER)
        addParagraph(doc, "Thesis ID: $thesisId", ParagraphAlignment.CENTER)
        addParagraph(doc, "AI Provider: $provider", ParagraphAlignment.CENTER)
        addParagraph(doc, "Generated: ${now()}", ParagraphAlignment.CENTER)
        addParagraph(doc, "Pages analyzed: $pageCount", ParagraphAlignment.CENTER)
        addParagraph(doc, "")
    }

    private fun addToc(doc: XWPFDocument, pages: List<PageInsight>) {
        addHeading(doc, "Table of Contents", 2)
        pages.forEach { page ->
            addParagraph(
                doc,
                "Page ${page.pageNo} • ${page.heading.ifBlank { "Untitled" }} • ${page.sectionType.uppercase(Locale.getDefault())}"
            )
        }
        addParagraph(doc, "") // Spacer after TOC
    }

    private fun addSection(doc: XWPFDocument, insight: PageInsight) {
        val pageTitle = "Page ${insight.pageNo}: ${insight.heading.ifBlank { "Analysis" }}"
        addHeading(doc, pageTitle, 2)
        addParagraph(doc, "Type: ${insight.sectionType}")
        addParagraph(doc, "Summary: ${insight.summary}")
        addParagraph(doc, "AI Comment: ${insight.aiComment}")

        if (insight.subsections.isNotEmpty()) {
            addHeading(doc, "Organized Subsections", 3)
            insight.subsections.forEach { sub ->
                if (sub.subheading.isNotBlank()) {
                    addHeading(doc, sub.subheading, 4)
                }
                sub.points.forEach { point ->
                    addParagraph(doc, "• $point")
                }
            }
        }

        addHeading(doc, "Exact Text", 3)
        val cleanedText = insight.value
            .replace("\r", "")
            .split("\n")
            .filter { it.isNotBlank() }

        if (cleanedText.isEmpty()) {
            addParagraph(doc, "No exact text available.")
        } else {
            cleanedText.forEach { line -> addParagraph(doc, line) }
        }
        addParagraph(doc, "")
    }

    private fun addHeading(doc: XWPFDocument, text: String, level: Int, alignment: ParagraphAlignment = ParagraphAlignment.LEFT) {
        val paragraph = doc.createParagraph()
        paragraph.alignment = alignment
        val run = paragraph.createRun()
        run.setText(text)
        run.isBold = true
        run.fontSize = when (level) {
            1 -> 18
            2 -> 15
            3 -> 13
            else -> 12
        }
    }

    private fun addParagraph(doc: XWPFDocument, text: String, alignment: ParagraphAlignment = ParagraphAlignment.LEFT) {
        val paragraph = doc.createParagraph()
        paragraph.alignment = alignment
        val run = paragraph.createRun()
        run.setText(text)
        run.fontSize = 11
    }

    private fun now(): String {
        val sdf = SimpleDateFormat("MMM dd, yyyy HH:mm", Locale.getDefault())
        return sdf.format(Calendar.getInstance().time)
    }
}
