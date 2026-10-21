import Foundation
import UIKit
import PDFKit

/// Document block used during export of AI chat replies and generated thesis chapters.
/// Mirrors `AiExportBlock` from Android's `AiChatExporter.kt`.
enum AiExportBlock {
    case heading(text: String, level: Int)
    case paragraph(text: String)
    case bullet(text: String)
    case numbered(number: Int, text: String)
    case table(caption: String, headers: [String], rows: [[String]])
    case chart(title: String, type: String, labels: [String], values: [Double])
}

/// Standalone exporter for AI replies and generated thesis chapters to PDF, DOCX, and PPTX.
/// Fully ports Android's `AiChatExporter.kt`.
@MainActor
final class AiChatExporter {

    static let shared = AiChatExporter()

    private init() {}

    // MARK: - Public API

    /// Exports raw AI chat text (with markdown headings, bold markers, and lists) to a temporary file.
    func exportText(title: String, text: String, format: AiExportFormat) -> URL? {
        let blocks = parseAiMarkdown(text)
        return writeDocument(title: title.isEmpty ? "MediGyaan Medical AI Export" : title, blocks: blocks, format: format)
    }

    /// Exports a structured thesis chapter payload (`ChatChapterJson`) to a temporary file.
    func exportChapter(chapter: ChatChapterJson, format: AiExportFormat) -> URL? {
        let blocks = buildChapterBlocks(chapter)
        let title = chapter.chapterName.isEmpty ? "Thesis Chapter" : chapter.chapterName
        return writeDocument(title: title, blocks: blocks, format: format)
    }

    // MARK: - Markdown Parser (matching Android's parseAiMarkdown)

    private func parseAiMarkdown(_ text: String) -> [AiExportBlock] {
        var blocks: [AiExportBlock] = []
        let lines = text.components(separatedBy: .newlines)

        for raw in lines {
            let line = raw.trimmingCharacters(in: .whitespaces)
            if line.isEmpty { continue }

            if isWholeLineBold(line) {
                blocks.append(.heading(text: stripBold(line), level: 1))
            } else if line.hasPrefix("•") || line.hasPrefix("- ") || (line.hasPrefix("* ") && !line.hasPrefix("**")) {
                let trimmed = line
                    .replacingOccurrences(of: "^(•|- |\\* )", with: "", options: .regularExpression)
                    .trimmingCharacters(in: .whitespaces)
                blocks.append(.bullet(text: stripBold(trimmed)))
            } else if let match = line.range(of: #"^\d+[.)]\s+"#, options: .regularExpression) {
                let numStr = line[match].trimmingCharacters(in: CharacterSet(charactersIn: "0123456789").inverted)
                let num = Int(numStr) ?? 1
                let content = String(line[match.upperBound...]).trimmingCharacters(in: .whitespaces)
                blocks.append(.numbered(number: num, text: stripBold(content)))
            } else {
                blocks.append(.paragraph(text: stripBold(line)))
            }
        }
        return blocks
    }

    private func buildChapterBlocks(_ chapter: ChatChapterJson) -> [AiExportBlock] {
        var blocks: [AiExportBlock] = []
        blocks.append(.heading(text: chapter.chapterName.isEmpty ? "Chapter" : chapter.chapterName, level: 0))

        for section in chapter.sections {
            if !section.heading.isEmpty {
                blocks.append(.heading(text: stripBold(section.heading), level: 1))
            }
            if !section.content.isEmpty {
                blocks.append(.paragraph(text: stripBold(section.content)))
            }
            for p in section.paragraphs {
                blocks.append(.paragraph(text: stripBold(p)))
            }
            for b in section.bullets {
                blocks.append(.bullet(text: stripBold(b)))
            }
            for (i, p) in section.numberedPoints.enumerated() {
                blocks.append(.numbered(number: i + 1, text: stripBold(p)))
            }
            for sub in section.subsections {
                if !sub.heading.isEmpty {
                    blocks.append(.heading(text: stripBold(sub.heading), level: 2))
                }
                if !sub.content.isEmpty {
                    blocks.append(.paragraph(text: stripBold(sub.content)))
                }
                for p in sub.paragraphs {
                    blocks.append(.paragraph(text: stripBold(p)))
                }
            }
            if let t = section.table {
                blocks.append(.table(caption: tableCaption(t), headers: t.headers, rows: t.rows))
            }
            for f in section.figures {
                blocks.append(.paragraph(text: figureLine(f)))
            }
        }

        for t in chapter.tables {
            blocks.append(.table(caption: tableCaption(t), headers: t.headers, rows: t.rows))
        }

        for f in chapter.figures {
            blocks.append(.paragraph(text: figureLine(f)))
        }

        for c in chapter.charts {
            let labels = c.data.isEmpty ? c.labels : c.data.map { $0.label }
            let values = c.data.isEmpty ? c.values : c.data.map { $0.value }
            blocks.append(.chart(title: c.title.isEmpty ? "Chart" : c.title, type: c.type, labels: labels, values: values))
        }

        for a in chapter.abbreviations {
            blocks.append(.paragraph(text: "\(a.short) = \(a.full)"))
        }

        if !chapter.references.isEmpty {
            blocks.append(.heading(text: "References", level: 1))
            for (i, r) in chapter.references.enumerated() {
                let refText = r.referenceText.isEmpty ? r.citation : r.referenceText
                blocks.append(.numbered(number: i + 1, text: stripBold(refText)))
            }
        }

        return blocks
    }

    private func tableCaption(_ t: ChatTableJson) -> String {
        let num = t.tableNumber.isEmpty ? "" : "Table \(t.tableNumber)"
        let title = t.title.isEmpty ? "" : (num.isEmpty ? t.title : ": \(t.title)")
        return (num + title).trimmingCharacters(in: .whitespaces)
    }

    private func figureLine(_ f: ChatFigureJson) -> String {
        var str = "Figure \(f.figureNumber)"
        if !f.title.isEmpty { str += ": \(f.title)" }
        if !f.caption.isEmpty { str += " — \(f.caption)" }
        return str
    }

    private func isWholeLineBold(_ line: String) -> Bool {
        let trimmed = line.trimmingCharacters(in: .whitespaces)
        guard trimmed.hasPrefix("**") && trimmed.hasSuffix("**") && trimmed.count > 4 else { return false }
        let inner = trimmed.dropFirst(2).dropLast(2)
        return !inner.isEmpty && !inner.contains("**")
    }

    private func stripBold(_ text: String) -> String {
        var result = ""
        var remainder = text[...]

        while let start = remainder.range(of: "**") {
            result += remainder[..<start.lowerBound]
            remainder = remainder[start.upperBound...]
            if let end = remainder.range(of: "**") {
                result += remainder[..<end.lowerBound]
                remainder = remainder[end.upperBound...]
            } else {
                result += "**"
                break
            }
        }
        result += remainder
        return result
    }

    // MARK: - Document Generation

    private func writeDocument(title: String, blocks: [AiExportBlock], format: AiExportFormat) -> URL? {
        let fileName = "MediGyaan_\(sanitizeFileName(title))_\(Int(Date().timeIntervalSince1970)).\(format.fileExtension)"
        let tempUrl = FileManager.default.temporaryDirectory.appendingPathComponent(fileName)

        switch format {
        case .pdf:
            return generatePdf(title: title, blocks: blocks, targetUrl: tempUrl)
        case .docx:
            return generateDocx(title: title, blocks: blocks, targetUrl: tempUrl)
        case .pptx:
            return generatePptx(title: title, blocks: blocks, targetUrl: tempUrl)
        }
    }

    private func sanitizeFileName(_ name: String) -> String {
        let invalid = CharacterSet(charactersIn: "\\/:*?\"<>| \n\t")
        return name.components(separatedBy: invalid).filter { !$0.isEmpty }.joined(separator: "_").prefix(30).description
    }

    // MARK: - PDF Generation via UIGraphicsPDFRenderer

    private func generatePdf(title: String, blocks: [AiExportBlock], targetUrl: URL) -> URL? {
        let pageWidth: CGFloat = 612 // Letter width
        let pageHeight: CGFloat = 792 // Letter height
        let margin: CGFloat = 40
        let contentWidth = pageWidth - (margin * 2)

        let renderer = UIGraphicsPDFRenderer(bounds: CGRect(x: 0, y: 0, width: pageWidth, height: pageHeight))

        do {
            try renderer.writePDF(to: targetUrl) { context in
                var currentY: CGFloat = margin

                func startNewPage() {
                    context.beginPage()
                    currentY = margin

                    // Header rule and branding
                    let headerAttrs: [NSAttributedString.Key: Any] = [
                        .font: UIFont.systemFont(ofSize: 8, weight: .bold),
                        .foregroundColor: UIColor.systemGray
                    ]
                    "MEDIGYAAN MEDICAL AI CLINICAL EXPORT".draw(at: CGPoint(x: margin, y: margin / 2), withAttributes: headerAttrs)

                    let rule = UIBezierPath()
                    rule.move(to: CGPoint(x: margin, y: margin - 6))
                    rule.addLine(to: CGPoint(x: pageWidth - margin, y: margin - 6))
                    UIColor.systemGray4.setStroke()
                    rule.lineWidth = 0.5
                    rule.stroke()
                }

                startNewPage()

                // Draw Title
                let titleAttrs: [NSAttributedString.Key: Any] = [
                    .font: UIFont.systemFont(ofSize: 18, weight: .bold),
                    .foregroundColor: UIColor(red: 0.08, green: 0.15, blue: 0.35, alpha: 1.0)
                ]
                let titleRect = title.boundingRect(
                    with: CGSize(width: contentWidth, height: .greatestFiniteMagnitude),
                    options: .usesLineFragmentOrigin,
                    attributes: titleAttrs,
                    context: nil
                )
                title.draw(in: CGRect(x: margin, y: currentY, width: contentWidth, height: titleRect.height), withAttributes: titleAttrs)
                currentY += titleRect.height + 14

                // Draw blocks
                for block in blocks {
                    switch block {
                    case .heading(let text, let level):
                        let fontSize: CGFloat = level == 0 ? 16 : (level == 1 ? 14 : 12)
                        let headingAttrs: [NSAttributedString.Key: Any] = [
                            .font: UIFont.systemFont(ofSize: fontSize, weight: .bold),
                            .foregroundColor: UIColor(red: 0.12, green: 0.22, blue: 0.45, alpha: 1.0)
                        ]
                        let rect = text.boundingRect(
                            with: CGSize(width: contentWidth, height: .greatestFiniteMagnitude),
                            options: .usesLineFragmentOrigin,
                            attributes: headingAttrs,
                            context: nil
                        )
                        if currentY + rect.height + 12 > pageHeight - margin {
                            startNewPage()
                        }
                        currentY += 8
                        text.draw(in: CGRect(x: margin, y: currentY, width: contentWidth, height: rect.height), withAttributes: headingAttrs)
                        currentY += rect.height + 6

                    case .paragraph(let text):
                        let paraAttrs: [NSAttributedString.Key: Any] = [
                            .font: UIFont.systemFont(ofSize: 10, weight: .regular),
                            .foregroundColor: UIColor.label
                        ]
                        let rect = text.boundingRect(
                            with: CGSize(width: contentWidth, height: .greatestFiniteMagnitude),
                            options: .usesLineFragmentOrigin,
                            attributes: paraAttrs,
                            context: nil
                        )
                        if currentY + rect.height + 8 > pageHeight - margin {
                            startNewPage()
                        }
                        text.draw(in: CGRect(x: margin, y: currentY, width: contentWidth, height: rect.height), withAttributes: paraAttrs)
                        currentY += rect.height + 5

                    case .bullet(let text):
                        let bulletText = "•  \(text)"
                        let bulletAttrs: [NSAttributedString.Key: Any] = [
                            .font: UIFont.systemFont(ofSize: 10, weight: .regular),
                            .foregroundColor: UIColor.label
                        ]
                        let rect = bulletText.boundingRect(
                            with: CGSize(width: contentWidth - 10, height: .greatestFiniteMagnitude),
                            options: .usesLineFragmentOrigin,
                            attributes: bulletAttrs,
                            context: nil
                        )
                        if currentY + rect.height + 6 > pageHeight - margin {
                            startNewPage()
                        }
                        bulletText.draw(in: CGRect(x: margin + 10, y: currentY, width: contentWidth - 10, height: rect.height), withAttributes: bulletAttrs)
                        currentY += rect.height + 4

                    case .numbered(let number, let text):
                        let numText = "\(number). \(text)"
                        let numAttrs: [NSAttributedString.Key: Any] = [
                            .font: UIFont.systemFont(ofSize: 10, weight: .regular),
                            .foregroundColor: UIColor.label
                        ]
                        let rect = numText.boundingRect(
                            with: CGSize(width: contentWidth - 10, height: .greatestFiniteMagnitude),
                            options: .usesLineFragmentOrigin,
                            attributes: numAttrs,
                            context: nil
                        )
                        if currentY + rect.height + 6 > pageHeight - margin {
                            startNewPage()
                        }
                        numText.draw(in: CGRect(x: margin + 10, y: currentY, width: contentWidth - 10, height: rect.height), withAttributes: numAttrs)
                        currentY += rect.height + 4

                    case .table(let caption, let headers, let rows):
                        if currentY + 120 > pageHeight - margin {
                            startNewPage()
                        }
                        if !caption.isEmpty {
                            let capAttrs: [NSAttributedString.Key: Any] = [
                                .font: UIFont.systemFont(ofSize: 10, weight: .bold),
                                .foregroundColor: UIColor.secondaryLabel
                            ]
                            caption.draw(at: CGPoint(x: margin, y: currentY), withAttributes: capAttrs)
                            currentY += 16
                        }
                        let colCount = max(headers.count, rows.first?.count ?? 1)
                        let colWidth = contentWidth / CGFloat(max(colCount, 1))

                        // Header row
                        if !headers.isEmpty {
                            for (c, h) in headers.enumerated() {
                                let hAttrs: [NSAttributedString.Key: Any] = [
                                    .font: UIFont.systemFont(ofSize: 9, weight: .bold),
                                    .foregroundColor: UIColor.systemBlue
                                ]
                                h.draw(in: CGRect(x: margin + (CGFloat(c) * colWidth), y: currentY, width: colWidth - 4, height: 16), withAttributes: hAttrs)
                            }
                            currentY += 18
                        }

                        // Data rows
                        for row in rows.prefix(20) {
                            if currentY + 16 > pageHeight - margin {
                                startNewPage()
                            }
                            for (c, cell) in row.enumerated() {
                                let cellAttrs: [NSAttributedString.Key: Any] = [
                                    .font: UIFont.systemFont(ofSize: 9, weight: .regular),
                                    .foregroundColor: UIColor.label
                                ]
                                cell.draw(in: CGRect(x: margin + (CGFloat(c) * colWidth), y: currentY, width: colWidth - 4, height: 16), withAttributes: cellAttrs)
                            }
                            currentY += 16
                        }
                        currentY += 8

                    case .chart(let title, let type, let labels, let values):
                        if currentY + 100 > pageHeight - margin {
                            startNewPage()
                        }
                        let chartTitle = "📊 \(title) (\(type))"
                        let chartAttrs: [NSAttributedString.Key: Any] = [
                            .font: UIFont.systemFont(ofSize: 10, weight: .bold),
                            .foregroundColor: UIColor.label
                        ]
                        chartTitle.draw(at: CGPoint(x: margin, y: currentY), withAttributes: chartAttrs)
                        currentY += 18

                        // Summary pairs
                        let pairs = zip(labels, values).prefix(6).map { "\($0): \(String(format: "%.1f", $1))" }.joined(separator: ", ")
                        let pairAttrs: [NSAttributedString.Key: Any] = [
                            .font: UIFont.systemFont(ofSize: 9, weight: .regular),
                            .foregroundColor: UIColor.secondaryLabel
                        ]
                        pairs.draw(at: CGPoint(x: margin, y: currentY), withAttributes: pairAttrs)
                        currentY += 18
                    }
                }
            }
            return targetUrl
        } catch {
            print("AiChatExporter PDF error: \(error)")
            return nil
        }
    }

    // MARK: - Word DOCX Generation (HTML-wrapped XML DOCX)

    private func generateDocx(title: String, blocks: [AiExportBlock], targetUrl: URL) -> URL? {
        var html = """
        <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
        <head><meta charset='utf-8'><title>\(title)</title>
        <style>
            body { font-family: 'Calibri', sans-serif; font-size: 11pt; color: #1a1a1a; margin: 40px; }
            h1 { font-size: 18pt; color: #1e3a8a; border-bottom: 2px solid #3b82f6; padding-bottom: 6px; }
            h2 { font-size: 14pt; color: #2563eb; margin-top: 18px; }
            h3 { font-size: 12pt; color: #475569; }
            p { margin: 6px 0; line-height: 1.5; }
            ul, ol { margin: 6px 0; padding-left: 24px; }
            li { margin: 3px 0; }
            table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 10pt; }
            th { background-color: #f1f5f9; color: #1e293b; font-weight: bold; border: 1px solid #cbd5e1; padding: 6px 10px; }
            td { border: 1px solid #cbd5e1; padding: 5px 10px; }
            .chart-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px; margin: 10px 0; }
            .footer { margin-top: 30px; font-size: 9pt; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 8px; }
        </style>
        </head><body>
        <h1>\(title)</h1>
        """

        for block in blocks {
            switch block {
            case .heading(let text, let level):
                if level == 0 || level == 1 {
                    html += "<h2>\(text)</h2>"
                } else {
                    html += "<h3>\(text)</h3>"
                }
            case .paragraph(let text):
                html += "<p>\(text)</p>"
            case .bullet(let text):
                html += "<ul><li>\(text)</li></ul>"
            case .numbered(let number, let text):
                html += "<ol start='\(number)'><li>\(text)</li></ol>"
            case .table(let caption, let headers, let rows):
                if !caption.isEmpty { html += "<p><strong>\(caption)</strong></p>" }
                html += "<table>"
                if !headers.isEmpty {
                    html += "<tr>"
                    for h in headers { html += "<th>\(h)</th>" }
                    html += "</tr>"
                }
                for row in rows {
                    html += "<tr>"
                    for cell in row { html += "<td>\(cell)</td>" }
                    html += "</tr>"
                }
                html += "</table>"
            case .chart(let title, let type, let labels, let values):
                let pairs = zip(labels, values).map { "\($0): \(String(format: "%.1f", $1))" }.joined(separator: ", ")
                html += "<div class='chart-box'><strong>📊 \(title) (\(type))</strong><br><span>\(pairs)</span></div>"
            }
        }

        html += """
        <div class='footer'>Exported from MediGyaan Medical AI Assistant — \(Date().formatted())</div>
        </body></html>
        """

        do {
            try html.write(to: targetUrl, atomically: true, encoding: .utf8)
            return targetUrl
        } catch {
            print("AiChatExporter DOCX error: \(error)")
            return nil
        }
    }

    // MARK: - PowerPoint PPTX Generation (HTML presentation container)

    private func generatePptx(title: String, blocks: [AiExportBlock], targetUrl: URL) -> URL? {
        var html = """
        <!DOCTYPE html>
        <html><head><meta charset='utf-8'><title>\(title)</title>
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; background: #0e131f; color: #f8fafc; margin: 0; padding: 20px; }
            .slide { background: #151b28; border: 1px solid #2e3a52; border-radius: 12px; padding: 30px; margin-bottom: 24px; min-height: 380px; box-shadow: 0 4px 12px rgba(0,0,0,0.4); }
            h1 { color: #bac7ff; font-size: 24pt; margin-top: 0; border-bottom: 2px solid #5c6bc0; padding-bottom: 8px; }
            h2 { color: #818cf8; font-size: 18pt; margin-top: 0; }
            p { font-size: 13pt; line-height: 1.6; color: #cbd5e1; }
            li { font-size: 13pt; line-height: 1.6; margin-bottom: 8px; color: #e2e8f0; }
            .tag { display: inline-block; background: #252f46; color: #a5b4fc; padding: 4px 10px; border-radius: 6px; font-size: 10pt; font-weight: bold; margin-bottom: 12px; }
        </style>
        </head><body>
        <div class='slide'>
            <span class='tag'>MEDIGYAAN MEDICAL RESEARCH</span>
            <h1>\(title)</h1>
            <p>Clinical Thesis & Evidence Synthesis Presentation</p>
        </div>
        """

        var currentSlideItems = ""
        var currentSlideTitle = "Overview"

        func flushSlide() {
            if !currentSlideItems.isEmpty {
                html += """
                <div class='slide'>
                    <span class='tag'>SECTION</span>
                    <h2>\(currentSlideTitle)</h2>
                    \(currentSlideItems)
                </div>
                """
                currentSlideItems = ""
            }
        }

        for block in blocks {
            switch block {
            case .heading(let text, _):
                flushSlide()
                currentSlideTitle = text
            case .paragraph(let text):
                currentSlideItems += "<p>\(text)</p>"
            case .bullet(let text):
                currentSlideItems += "<ul><li>\(text)</li></ul>"
            case .numbered(let number, let text):
                currentSlideItems += "<ol start='\(number)'><li>\(text)</li></ol>"
            case .table(let caption, let headers, let rows):
                currentSlideItems += "<p><strong>\(caption)</strong></p><ul>"
                for h in headers.prefix(4) { currentSlideItems += "<li>\(h)</li>" }
                currentSlideItems += "</ul>"
            case .chart(let title, let type, let labels, let values):
                let pairs = zip(labels, values).prefix(4).map { "\($0): \($1)" }.joined(separator: ", ")
                currentSlideItems += "<p><strong>📊 \(title) (\(type))</strong>: \(pairs)</p>"
            }
        }
        flushSlide()

        html += "</body></html>"

        do {
            try html.write(to: targetUrl, atomically: true, encoding: .utf8)
            return targetUrl
        } catch {
            print("AiChatExporter PPTX error: \(error)")
            return nil
        }
    }
}
