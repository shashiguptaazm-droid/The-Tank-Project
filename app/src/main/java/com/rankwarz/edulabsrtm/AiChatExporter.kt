package com.rankwarz.edulabsrtm

import android.content.Context
import android.graphics.Color
import android.graphics.Paint
import android.graphics.pdf.PdfDocument
import android.net.Uri
import com.rankwarz.edulabsrtm.viewmodel.PdfThemeStyle
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.apache.poi.xwpf.usermodel.ParagraphAlignment
import org.apache.poi.xwpf.usermodel.XWPFDocument
import org.apache.poi.xwpf.usermodel.XWPFParagraph
import org.apache.poi.xwpf.usermodel.XWPFTableCell
import org.apache.poi.xwpf.usermodel.XWPFTableRow
import java.io.OutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/** Export formats offered on AI chat replies and generated chapters. */
enum class AiExportFormat(
    val mime: String,
    val extension: String,
    val label: String
) {
    PDF("application/pdf", "pdf", "PDF"),
    DOCX("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx", "Word"),
    PPTX("application/vnd.openxmlformats-officedocument.presentationml.presentation", "pptx", "PowerPoint")
}

/** A structured piece of an exported document (AI reply or generated chapter). */
internal sealed class AiExportBlock {
    data class Heading(val text: String, val level: Int) : AiExportBlock()
    data class Paragraph(val text: String) : AiExportBlock()
    data class Bullet(val text: String) : AiExportBlock()
    data class Numbered(val number: Int, val text: String) : AiExportBlock()
    data class Table(val caption: String, val headers: List<String>, val rows: List<List<String>>) : AiExportBlock()
    data class Chart(val title: String, val type: String, val labels: List<String>, val values: List<Double>) : AiExportBlock()
}

/**
 * Exports AI chat replies and generated thesis chapters to PDF / Word (DOCX) / PowerPoint (PPTX).
 *
 * The PPTX writer follows the same hand-rolled OOXML-zip approach used by the thesis
 * exporter (POI's XSLF needs java.awt, which is only stubbed on Android).
 */
object AiChatExporter {

    // ------------------------------------------------------------------ entry points

    suspend fun exportText(
        context: Context,
        uri: Uri,
        format: AiExportFormat,
        title: String,
        text: String,
        theme: PdfThemeStyle? = null
    ) = withContext(Dispatchers.IO) {
        val blocks = parseAiMarkdown(text)
        writeDocument(context, uri, format, title, blocks, theme)
    }

    internal suspend fun exportChapter(
        context: Context,
        uri: Uri,
        format: AiExportFormat,
        chapter: ChatChapterJson,
        theme: PdfThemeStyle? = null
    ) = withContext(Dispatchers.IO) {
        val blocks = buildChapterBlocks(chapter)
        writeDocument(context, uri, format, chapter.chapterName.ifBlank { "Chapter" }, blocks, theme)
    }

    // ------------------------------------------------------------------ markdown parsing

    /** Parses AI reply text (matching the app's AiRichText `**bold**` rules) into export blocks. */
    private fun parseAiMarkdown(text: String): List<AiExportBlock> {
        val blocks = mutableListOf<AiExportBlock>()
        text.lines().forEach { raw ->
            val line = raw.trim()
            if (line.isBlank()) return@forEach
            when {
                isWholeLineBold(line) -> blocks += AiExportBlock.Heading(stripBold(line), 1)
                line.startsWith("•") || line.startsWith("- ") || (line.startsWith("* ") && !line.startsWith("**")) ->
                    blocks += AiExportBlock.Bullet(stripBold(line.removePrefix("•").removePrefix("- ").removePrefix("* ").trim()))
                Regex("""^\d+[.)]\s+""").containsMatchIn(line) -> {
                    val sep = line.indexOfFirst { it == '.' || it == ')' }
                    val num = line.substring(0, sep).toIntOrNull() ?: 1
                    blocks += AiExportBlock.Numbered(num, stripBold(line.substring(sep + 1).trim()))
                }
                else -> blocks += AiExportBlock.Paragraph(stripBold(line))
            }
        }
        return blocks
    }

    /** Converts a parsed chapter payload into the same block model (sections, tables, charts, references). */
    private fun buildChapterBlocks(chapter: ChatChapterJson): List<AiExportBlock> {
        val blocks = mutableListOf<AiExportBlock>()
        blocks += AiExportBlock.Heading(chapter.chapterName.ifBlank { "Chapter" }, 0)
        chapter.sections.forEach { section ->
            if (section.heading.isNotBlank()) blocks += AiExportBlock.Heading(stripBold(section.heading), 1)
            if (section.content.isNotBlank()) blocks += AiExportBlock.Paragraph(stripBold(section.content))
            section.paragraphs.forEach { p -> blocks += AiExportBlock.Paragraph(stripBold(p)) }
            section.bullets.forEach { b -> blocks += AiExportBlock.Bullet(stripBold(b)) }
            section.numberedPoints.forEachIndexed { i, p -> blocks += AiExportBlock.Numbered(i + 1, stripBold(p)) }
            section.subsections.forEach { sub ->
                if (sub.heading.isNotBlank()) blocks += AiExportBlock.Heading(stripBold(sub.heading), 2)
                if (sub.content.isNotBlank()) blocks += AiExportBlock.Paragraph(stripBold(sub.content))
                sub.paragraphs.forEach { p -> blocks += AiExportBlock.Paragraph(stripBold(p)) }
            }
            section.table?.let { blocks += AiExportBlock.Table(tableCaption(it), it.headers, it.rows) }
            section.figures.forEach { f ->
                blocks += AiExportBlock.Paragraph(figureLine(f))
            }
        }
        chapter.tables.forEach { t -> blocks += AiExportBlock.Table(tableCaption(t), t.headers, t.rows) }
        chapter.figures.forEach { f -> blocks += AiExportBlock.Paragraph(figureLine(f)) }
        chapter.charts.forEach { c ->
            val labels = c.data.map { it.label }.ifEmpty { c.labels }
            val values = c.data.map { it.value }.ifEmpty { c.values }
            blocks += AiExportBlock.Chart(c.title.ifBlank { "Chart" }, c.type, labels, values)
        }
        chapter.abbreviations.forEach { a -> blocks += AiExportBlock.Paragraph("${a.short} = ${a.full}") }
        if (chapter.references.isNotEmpty()) {
            blocks += AiExportBlock.Heading("References", 1)
            chapter.references.forEachIndexed { i, r ->
                blocks += AiExportBlock.Numbered(i + 1, stripBold(r.referenceText.ifBlank { r.citation }))
            }
        }
        return blocks
    }

    private fun tableCaption(t: ChatTableJson): String =
        "Table ${t.tableNumber.ifBlank { "" }}${if (t.title.isNotBlank()) ": ${t.title}" else ""}".trim()

    private fun figureLine(f: ChatFigureJson): String =
        "🖼 Figure ${f.figureNumber}${if (f.title.isNotBlank()) ": ${f.title}" else ""}" +
            (if (f.caption.isNotBlank()) " — ${f.caption}" else "")

    private fun chartLine(c: AiExportBlock.Chart): String {
        val pairs = c.labels.zip(c.values).take(10).joinToString(", ") { (l, v) ->
            "${l.ifBlank { "—" }}: ${formatNumber(v)}"
        }
        return "📊 ${c.title} (${c.type.ifBlank { "chart" }})${if (pairs.isNotBlank()) " — $pairs" else ""}"
    }

    private fun formatNumber(v: Double): String =
        if (v == v.toLong().toDouble()) v.toLong().toString() else "%.2f".format(Locale.US, v)

    private fun isWholeLineBold(line: String): Boolean {
        val trimmed = line.trim()
        if (!trimmed.startsWith("**") || !trimmed.endsWith("**") || trimmed.length <= 4) return false
        val inner = trimmed.substring(2, trimmed.length - 2)
        return inner.isNotBlank() && !inner.contains("**")
    }

    /** Removes paired **bold** markers only; leaves unmatched markers intact. */
    private fun stripBold(text: String): String {
        val result = StringBuilder()
        var index = 0
        while (index < text.length) {
            val start = text.indexOf("**", startIndex = index)
            if (start < 0) { result.append(text.substring(index)); break }
            result.append(text.substring(index, start))
            val end = text.indexOf("**", startIndex = start + 2)
            if (end < 0) { result.append("**"); index = start + 2; continue }
            result.append(text.substring(start + 2, end))
            index = end + 2
        }
        return result.toString()
    }

    // ------------------------------------------------------------------ writers

    private fun writeDocument(
        context: Context,
        uri: Uri,
        format: AiExportFormat,
        title: String,
        blocks: List<AiExportBlock>,
        theme: PdfThemeStyle?
    ) {
        when (format) {
            AiExportFormat.PDF -> writePdf(context, uri, title, blocks, theme)
            AiExportFormat.DOCX -> writeDocx(context, uri, title, blocks, theme)
            AiExportFormat.PPTX -> writePptx(context, uri, title, blocks, theme)
        }
    }

    /** Hex color of the export theme's accent (falls back to the default MediGyaan blue). */
    private fun PdfThemeStyle?.accentHex(): String =
        String.format("#%06X", 0xFFFFFF and (this?.accentColor ?: Color.parseColor("#0B57D0")))

    private fun now(): String =
        SimpleDateFormat("MMM dd, yyyy HH:mm", Locale.getDefault()).format(Date())

    // ================================================================== PDF

    private fun writePdf(context: Context, uri: Uri, title: String, blocks: List<AiExportBlock>, theme: PdfThemeStyle?) {
        val document = PdfDocument()
        try {
            var pageNumber = 1
            var page = document.startPage(PdfDocument.PageInfo.Builder(595, 842, pageNumber).create())
            var canvas = page.canvas
            var y = 64f
            val marginLeft = 40f
            val maxWidth = 595f - marginLeft * 2
            val bottomLimit = 842f - 42f

            val titlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                textSize = 21f; isFakeBoldText = true; color = Color.rgb(31, 41, 55); textAlign = Paint.Align.CENTER
            }
            val metaPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                textSize = 9.5f; color = Color.rgb(108, 117, 125); textAlign = Paint.Align.CENTER
            }
            val h0Paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                textSize = 17f; isFakeBoldText = true; color = Color.rgb(31, 41, 55)
            }
            val h1Paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                textSize = 14f; isFakeBoldText = true; color = Color.rgb(11, 87, 208)
            }
            val h2Paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                textSize = 12.5f; isFakeBoldText = true; color = Color.rgb(31, 41, 55)
            }
            val bodyPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                textSize = 11.5f; color = Color.rgb(33, 37, 41)
            }
            val smallPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                textSize = 10f; color = Color.rgb(73, 80, 87)
            }

            fun ensureSpace(needed: Float) {
                if (y + needed > bottomLimit) {
                    document.finishPage(page)
                    pageNumber++
                    page = document.startPage(PdfDocument.PageInfo.Builder(595, 842, pageNumber).create())
                    canvas = page.canvas
                    y = 64f
                    theme?.let { t ->
                        canvas.drawRect(0f, 842f - 14f, 595f, 842f, Paint(Paint.ANTI_ALIAS_FLAG).apply { color = t.footerFillColor })
                    }
                }
            }

            fun drawWrapped(text: String, paint: Paint, indent: Float = 0f, lineHeight: Float = paint.textSize * 1.45f, spacing: Float = 5f) {
                val lines = wrapText(paint, text, maxWidth - indent)
                if (lines.isEmpty()) return
                ensureSpace(lines.size * lineHeight + spacing)
                lines.forEach { line ->
                    canvas.drawText(line, marginLeft + indent, y, paint)
                    y += lineHeight
                }
                y += spacing
            }

            // Title + meta — themed per export (a random theme is picked on every download click).
            if (theme != null) {
                canvas.drawRect(0f, 0f, 595f, 12f, Paint(Paint.ANTI_ALIAS_FLAG).apply { color = theme.accentColor })
            }
            canvas.drawText(title, 297.5f, y, if (theme != null) titlePaint.apply { color = theme.accentColor } else titlePaint); y += 30f
            canvas.drawText("MediGyaan AI • ${now()}", 297.5f, y, if (theme != null) metaPaint.apply { color = theme.ruleColor } else metaPaint); y += 26f
            if (theme != null) {
                canvas.drawLine(40f, y - 14f, 555f, y - 14f, Paint(Paint.ANTI_ALIAS_FLAG).apply { color = theme.ruleColor; strokeWidth = 2f })
            }

            for (block in blocks) {
                when (block) {
                    is AiExportBlock.Heading -> {
                        val paint = when (block.level) {
                            0 -> if (theme != null) h0Paint.apply { color = theme.accentColor } else h0Paint
                            1 -> if (theme != null) h1Paint.apply { color = theme.accentColor } else h1Paint
                            else -> h2Paint
                        }
                        ensureSpace(paint.textSize * 2)
                        y += 6f
                        canvas.drawText(block.text, marginLeft, y, paint)
                        y += paint.textSize * 1.6f
                    }
                    is AiExportBlock.Paragraph -> drawWrapped(block.text, bodyPaint)
                    is AiExportBlock.Bullet -> drawWrapped("• ${block.text}", bodyPaint, indent = 14f)
                    is AiExportBlock.Numbered -> drawWrapped("${block.number}. ${block.text}", bodyPaint, indent = 14f)
                    is AiExportBlock.Table -> {
                        if (block.caption.isNotBlank()) {
                            ensureSpace(smallPaint.textSize * 2)
                            canvas.drawText(block.caption, marginLeft, y, smallPaint)
                            y += smallPaint.textSize * 1.6f
                        }
                        val header = block.headers.joinToString("   |   ")
                        if (header.isNotBlank()) drawWrapped(header, smallPaint.apply { isFakeBoldText = true })
                        block.rows.take(60).forEach { row ->
                            drawWrapped(row.joinToString("   |   "), smallPaint.apply { isFakeBoldText = false })
                        }
                    }
                    is AiExportBlock.Chart -> drawWrapped(chartLine(block), bodyPaint)
                }
            }
            document.finishPage(page)
            context.contentResolver.openOutputStream(uri)?.use { output ->
                document.writeTo(output)
            } ?: throw IllegalStateException("Unable to open output stream")
        } finally {
            document.close()
        }
    }

    private fun wrapText(paint: Paint, text: String, maxWidth: Float): List<String> {
        val result = mutableListOf<String>()
        var line = StringBuilder()
        text.trim().split(Regex("\\s+")).forEach { word ->
            val test = if (line.isEmpty()) word else "$line $word"
            if (paint.measureText(test) <= maxWidth) {
                line.append(if (line.isEmpty()) word else " $word")
            } else {
                if (line.isNotEmpty()) {
                    result += line.toString()
                    line = StringBuilder()
                }
                if (paint.measureText(word) <= maxWidth) {
                    line.append(word)
                } else {
                    // Force-break an over-long word (e.g. a URL).
                    var chunk = StringBuilder()
                    word.forEach { ch ->
                        val probe = chunk.toString() + ch
                        if (paint.measureText(probe) <= maxWidth) chunk.append(ch)
                        else {
                            if (chunk.isNotEmpty()) result += chunk.toString()
                            chunk = StringBuilder(ch.toString())
                        }
                    }
                    if (chunk.isNotEmpty()) line.append(chunk)
                }
            }
        }
        if (line.isNotEmpty()) result += line.toString()
        return result
    }

    // ================================================================== DOCX

    private fun writeDocx(context: Context, uri: Uri, title: String, blocks: List<AiExportBlock>, theme: PdfThemeStyle?) {
        val doc = XWPFDocument()
        try {
            val titleP = doc.createParagraph()
            titleP.alignment = ParagraphAlignment.CENTER
            val titleRun = titleP.createRun()
            titleRun.setText(title)
            titleRun.isBold = true
            titleRun.fontSize = 18
            val metaP = doc.createParagraph()
            metaP.alignment = ParagraphAlignment.CENTER
            val metaRun = metaP.createRun()
            metaRun.setText("MediGyaan AI • ${now()}")
            metaRun.fontSize = 9
            metaRun.color = "6C757D"

            for (block in blocks) {
                when (block) {
                    is AiExportBlock.Heading -> {
                        val p = doc.createParagraph()
                        p.spacingBefore = if (block.level <= 1) 200 else 120
                        p.spacingAfter = 80
                        val size = when (block.level) { 0 -> 16; 1 -> 14; else -> 12 }
                        val color = if (block.level == 1) theme?.accentHex() ?: "0B57D0" else "1F2937"
                        addMarkdownRuns(p, "**${block.text}**", size = size, color = color)
                    }
                    is AiExportBlock.Paragraph -> {
                        val p = doc.createParagraph()
                        p.spacingAfter = 60
                        addMarkdownRuns(p, block.text, size = 11)
                    }
                    is AiExportBlock.Bullet -> {
                        val p = doc.createParagraph()
                        p.indentationLeft = 420
                        p.spacingAfter = 40
                        addMarkdownRuns(p, "• ${block.text}", size = 11)
                    }
                    is AiExportBlock.Numbered -> {
                        val p = doc.createParagraph()
                        p.indentationLeft = 420
                        p.spacingAfter = 40
                        addMarkdownRuns(p, "${block.number}. ${block.text}", size = 11)
                    }
                    is AiExportBlock.Table -> addDocxTable(doc, block)
                    is AiExportBlock.Chart -> {
                        val p = doc.createParagraph()
                        p.spacingAfter = 60
                        addMarkdownRuns(p, chartLine(block), size = 11)
                    }
                }
            }

            context.contentResolver.openOutputStream(uri)?.use { output ->
                doc.write(output)
            } ?: throw IllegalStateException("Unable to open output stream")
        } finally {
            doc.close()
        }
    }

    private fun addDocxTable(doc: XWPFDocument, block: AiExportBlock.Table) {
        if (block.caption.isNotBlank()) {
            val p = doc.createParagraph()
            p.spacingBefore = 120
            p.spacingAfter = 60
            addMarkdownRuns(p, "**${block.caption}**", size = 11)
        }
        val rows = block.rows.take(60)
        val colCount = block.headers.size.coerceAtLeast(rows.maxOfOrNull { it.size } ?: 1).coerceAtLeast(1)
        val table = doc.createTable(rows.size + 1, colCount)
        block.headers.forEachIndexed { i, h ->
            setCellText(table.getRow(0), i, h, bold = true)
        }
        rows.forEachIndexed { r, row ->
            val target = table.getRow(r + 1)
            row.forEachIndexed { c, cellText ->
                if (c < colCount) setCellText(target, c, cellText, bold = false)
            }
        }
    }

    private fun setCellText(row: XWPFTableRow, col: Int, text: String, bold: Boolean) {
        val cell = row.getCell(col)
        val p = cell.paragraphs.firstOrNull() ?: cell.addParagraph()
        val run = p.createRun()
        run.setText(text)
        run.isBold = bold
        run.fontSize = 9
    }

    /** Adds `**bold**` runs to a paragraph (plain segments stay normal weight). */
    private fun addMarkdownRuns(p: XWPFParagraph, text: String, size: Int, color: String = "212529", forceBold: Boolean = false) {
        parseBoldRuns(text).forEach { (segment, bold) ->
            val run = p.createRun()
            run.setText(segment)
            run.fontSize = size
            run.isBold = bold || forceBold
            run.color = color
        }
    }

    private data class MarkdownRun(val text: String, val bold: Boolean)

    private fun parseBoldRuns(text: String): List<MarkdownRun> {
        val runs = mutableListOf<MarkdownRun>()
        var index = 0
        while (index < text.length) {
            val start = text.indexOf("**", startIndex = index)
            if (start < 0) {
                if (index < text.length) runs += MarkdownRun(text.substring(index), bold = false)
                break
            }
            if (start > index) runs += MarkdownRun(text.substring(index, start), bold = false)
            val end = text.indexOf("**", startIndex = start + 2)
            if (end < 0) {
                runs += MarkdownRun(text.substring(start), bold = false)
                break
            }
            runs += MarkdownRun(text.substring(start + 2, end), bold = true)
            index = end + 2
        }
        return runs.filter { it.text.isNotEmpty() }
    }

    // ================================================================== PPTX (hand-rolled OOXML zip, same approach as the thesis exporter)

    private fun writePptx(context: Context, uri: Uri, title: String, blocks: List<AiExportBlock>, theme: PdfThemeStyle?) {
        val slides = buildPptxSlides(title, blocks)
        val accent = theme?.accentHex() ?: "0B57D0"
        context.contentResolver.openOutputStream(uri)?.use { output ->
            ZipOutputStream(output).use { zip ->
                zipText(zip, "[Content_Types].xml", pptxContentTypes(slides.size))
                zipText(zip, "_rels/.rels", pptxRootRels())
                zipText(zip, "docProps/core.xml", pptxCoreProperties(title))
                zipText(zip, "docProps/app.xml", pptxAppProperties(slides.size))
                zipText(zip, "ppt/presentation.xml", pptxPresentation(slides.size))
                zipText(zip, "ppt/_rels/presentation.xml.rels", pptxPresentationRels(slides.size))
                zipText(zip, "ppt/theme/theme1.xml", pptxTheme(accent))
                zipText(zip, "ppt/slideMasters/slideMaster1.xml", pptxSlideMaster())
                zipText(zip, "ppt/slideMasters/_rels/slideMaster1.xml.rels", pptxSlideMasterRels())
                zipText(zip, "ppt/slideLayouts/slideLayout1.xml", pptxSlideLayout())
                zipText(zip, "ppt/slideLayouts/_rels/slideLayout1.xml.rels", pptxSlideLayoutRels())
                slides.forEachIndexed { index, slideLines ->
                    val n = index + 1
                    zipText(zip, "ppt/slides/slide$n.xml", pptxSlideXml(slideLines, n, accent))
                    zipText(zip, "ppt/slides/_rels/slide$n.xml.rels", pptxSlideRels(n))
                }
            }
        }
    }

    /** Flattens blocks into slide chunks (max ~14 lines each; headings keep their bold marker). */
    private fun buildPptxSlides(title: String, blocks: List<AiExportBlock>): List<List<String>> {
        val lines = mutableListOf<String>()
        blocks.forEach { block ->
            when (block) {
                is AiExportBlock.Heading -> lines += "**${block.text}**"
                is AiExportBlock.Paragraph -> lines += block.text
                is AiExportBlock.Bullet -> lines += "• ${block.text}"
                is AiExportBlock.Numbered -> lines += "${block.number}. ${block.text}"
                is AiExportBlock.Table -> {
                    if (block.caption.isNotBlank()) lines += "**${block.caption}**"
                    if (block.headers.isNotEmpty()) lines += block.headers.joinToString("   |   ")
                    block.rows.take(12).forEach { row -> lines += row.joinToString("   |   ") }
                }
                is AiExportBlock.Chart -> lines += chartLine(block)
            }
        }
        val slides = mutableListOf<List<String>>()
        slides += listOf("**$title**", "MediGyaan AI • ${now()}", "", "")
        var current = mutableListOf<String>()
        fun flush() {
            if (current.isNotEmpty()) {
                slides += current.toList()
                current = mutableListOf()
            }
        }
        lines.forEach { line ->
            val isHeading = line.startsWith("**")
            if (current.size >= 14 || (isHeading && current.size >= 4)) flush()
            current += line
        }
        flush()
        return slides
    }

    private fun pptxTextShape(id: Int, text: String, x: Int, y: Int, cx: Int, cy: Int, size: Int, bold: Boolean, color: String): String {
        val paragraphs = text.lines().ifEmpty { listOf("") }.joinToString("") { line ->
            val runs = parseBoldRuns(line).ifEmpty { listOf(MarkdownRun("", false)) }
            val xmlRuns = runs.joinToString("") { run ->
                val runBold = bold || run.bold
                """<a:r><a:rPr lang="en-US" sz="${size * 100}"${if (runBold) """ b="1"""" else ""}><a:solidFill><a:srgbClr val="$color"/></a:solidFill></a:rPr><a:t>${xml(run.text)}</a:t></a:r>"""
            }
            "<a:p>$xmlRuns</a:p>"
        }
        return """<p:sp><p:nvSpPr><p:cNvPr id="$id" name="Text $id"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="$x" y="$y"/><a:ext cx="$cx" cy="$cy"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr><p:txBody><a:bodyPr wrap="square"/><a:lstStyle/>$paragraphs</p:txBody></p:sp>"""
    }

    private fun pptxRectShape(id: Int, x: Int, y: Int, cx: Int, cy: Int, fill: String, stroke: String?): String {
        val line = stroke?.let { """<a:ln w="9525"><a:solidFill><a:srgbClr val="$it"/></a:solidFill></a:ln>""" } ?: "<a:ln><a:noFill/></a:ln>"
        return """<p:sp><p:nvSpPr><p:cNvPr id="$id" name="Block $id"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="$x" y="$y"/><a:ext cx="$cx" cy="$cy"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="$fill"/></a:solidFill>$line</p:spPr><p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>"""
    }

    private fun pptxSlideXml(slideLines: List<String>, slideNumber: Int, accent: String = "0B57D0"): String {
        val shapes = StringBuilder()
        shapes.append(pptxRectShape(90, 0, 0, 12192000, 6858000, "FFFFFF", null))
        shapes.append(pptxRectShape(91, 0, 0, 12192000, 300000, accent, null))
        shapes.append(pptxRectShape(92, 0, 6550000, 12192000, 308000, "F1F5F9", null))
        if (slideNumber == 1) {
            shapes.append(pptxTextShape(2, "MEDIGYAAN AI", 650000, 900000, 4000000, 300000, 12, true, accent))
            shapes.append(pptxTextShape(3, slideLines.getOrElse(0) { "" }, 650000, 1400000, 10900000, 1400000, 30, true, "1F2937"))
            shapes.append(pptxTextShape(4, slideLines.getOrElse(1) { "" }, 650000, 3000000, 10900000, 500000, 15, false, "6C757D"))
            shapes.append(pptxRectShape(5, 650000, 3600000, 1600000, 40000, accent, null))
        } else {
            val first = slideLines.firstOrNull { it.isNotBlank() } ?: ""
            val isTitleSlide = first.startsWith("**")
            if (isTitleSlide) {
                shapes.append(pptxTextShape(2, stripBold(first).uppercase(Locale.getDefault()), 650000, 480000, 10900000, 320000, 11, true, accent))
                shapes.append(pptxRectShape(3, 650000, 830000, 10900000, 40000, "E2E8F0", null))
                shapes.append(pptxTextShape(4, slideLines.drop(1).joinToString("\n"), 650000, 1100000, 10900000, 5100000, 15, false, "212529"))
            } else {
                shapes.append(pptxTextShape(2, "MEDIGYAAN AI", 650000, 480000, 4000000, 300000, 11, true, accent))
                shapes.append(pptxTextShape(3, slideLines.joinToString("\n"), 650000, 1000000, 10900000, 5200000, 15, false, "212529"))
            }
        }
        shapes.append(pptxTextShape(99, "MediGyaan AI • ${now()}", 650000, 6620000, 10900000, 250000, 9, false, "6C757D"))
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>$shapes</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>"""
    }

    private fun xml(value: String): String = value
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\"", "&quot;")
        .replace("'", "&apos;")

    private fun zipText(zip: ZipOutputStream, path: String, text: String) {
        zip.putNextEntry(ZipEntry(path))
        zip.write(text.toByteArray(Charsets.UTF_8))
        zip.closeEntry()
    }

    private fun pptxContentTypes(slideCount: Int): String = buildString {
        append("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">""")
        append("""<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>""")
        append("""<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>""")
        append("""<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/><Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/><Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/><Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>""")
        repeat(slideCount) { append("""<Override PartName="/ppt/slides/slide${it + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>""") }
        append("</Types>")
    }

    private fun pptxRootRels(): String =
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>"""

    private fun pptxCoreProperties(title: String): String =
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>${xml(title)}</dc:title><dc:creator>MediGyaan AI</dc:creator><cp:lastModifiedBy>MediGyaan AI</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">${now()}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">${now()}</dcterms:modified></cp:coreProperties>"""

    private fun pptxAppProperties(slideCount: Int): String =
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>MediGyaan</Application><PresentationFormat>On-screen Show (16:9)</PresentationFormat><Slides>$slideCount</Slides><Notes>0</Notes><HiddenSlides>0</HiddenSlides><MMClips>0</MMClips><ScaleCrop>false</ScaleCrop><HeadingPairs><vt:vector size="2" baseType="variant"><vt:variant><vt:lpstr>Slides</vt:lpstr></vt:variant><vt:variant><vt:i4>$slideCount</vt:i4></vt:variant></vt:vector></HeadingPairs><TitlesOfParts><vt:vector size="$slideCount" baseType="lpstr">${(1..slideCount).joinToString("") { "<vt:lpstr>Slide $it</vt:lpstr>" }}</vt:vector></TitlesOfParts><Company>MediGyaan</Company><LinksUpToDate>false</LinksUpToDate><SharedDoc>false</SharedDoc><HyperlinksChanged>false</HyperlinksChanged><AppVersion>16.0000</AppVersion></Properties>"""

    private fun pptxPresentation(slideCount: Int): String = buildString {
        append("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rIdMaster1"/></p:sldMasterIdLst><p:sldIdLst>""")
        repeat(slideCount) { append("""<p:sldId id="${256 + it}" r:id="rId${it + 1}"/>""") }
        append("""</p:sldIdLst><p:sldSz cx="12192000" cy="6858000" type="screen16x9"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>""")
    }

    private fun pptxPresentationRels(slideCount: Int): String = buildString {
        append("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">""")
        repeat(slideCount) { append("""<Relationship Id="rId${it + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide${it + 1}.xml"/>""") }
        append("""<Relationship Id="rIdMaster1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>""")
        append("""<Relationship Id="rIdTheme1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>""")
        append("</Relationships>")
    }

    private fun pptxSlideRels(slideNumber: Int): String =
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdLayout1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/></Relationships>"""

    private fun pptxSlideMaster(): String =
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:effectLst/></p:bgPr></p:bg><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/><p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rIdLayout1"/></p:sldLayoutIdLst><p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>"""

    private fun pptxSlideMasterRels(): String =
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdLayout1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/><Relationship Id="rIdTheme1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/></Relationships>"""

    private fun pptxSlideLayout(): String =
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1"><p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>"""

    private fun pptxSlideLayoutRels(): String =
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdMaster1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/></Relationships>"""

    private fun pptxTheme(accent: String = "0B57D0"): String =
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="MediGyaan AI"><a:themeElements><a:clrScheme name="MediGyaan"><a:dk1><a:srgbClr val="1F2937"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="0B57D0"/></a:dk2><a:lt2><a:srgbClr val="F1F5F9"/></a:lt2><a:accent1><a:srgbClr val="0B57D0"/></a:accent1><a:accent2><a:srgbClr val="334155"/></a:accent2><a:accent3><a:srgbClr val="64748B"/></a:accent3><a:accent4><a:srgbClr val="E2E8F0"/></a:accent4><a:accent5><a:srgbClr val="334155"/></a:accent5><a:accent6><a:srgbClr val="64748B"/></a:accent6><a:hlink><a:srgbClr val="0B57D0"/></a:hlink><a:folHlink><a:srgbClr val="64748B"/></a:folHlink></a:clrScheme><a:fontScheme name="MediGyaan"><a:majorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme><a:fmtScheme name="MediGyaan"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0"><a:schemeClr val="phClr"/></a:gs><a:gs pos="100000"><a:schemeClr val="phClr"/></a:gs></a:gsLst><a:lin ang="5400000" scaled="0"/></a:gradFill><a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0"><a:schemeClr val="phClr"/></a:gs><a:gs pos="100000"><a:schemeClr val="phClr"/></a:gs></a:gsLst><a:lin ang="5400000" scaled="0"/></a:gradFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="25400"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="38100"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements><a:objectDefaults/><a:extraClrSchemeLst/></a:theme>""".replace("0B57D0", accent)
}