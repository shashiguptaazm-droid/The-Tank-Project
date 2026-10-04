import Foundation
import UIKit

/// Structured variable parsed from a thesis manuscript or PDF text.
public struct ThesisVariable: Identifiable, Codable, Hashable {
    public var id: String { key }
    public let key: String
    public let value: String

    public init(key: String, value: String) {
        self.key = key
        self.value = value
    }
}

/// Shared thesis-art bridge and document parser.
/// 1:1 port of Android `ThesisArtBridge.kt` and `ThesisSharedState.kt`.
public enum ThesisArtBridge {

    /// Extract structured variables (Title, Abstract, Vancouver References, Methodology) from raw PDF or manuscript text.
    public static func extractPdfVariables(
        from text: String,
        onChunk: ((String) -> Void)? = nil
    ) -> [ThesisVariable] {
        var result: [ThesisVariable] = []
        let lines = text.components(separatedBy: .newlines).filter { !$0.trimmingCharacters(in: .whitespaces).isEmpty }

        // 1. Title extractor
        let ignoredTitlePatterns = ["abstract", "introduction", "references", "acknowledgment", "keywords", "table", "figure", "appendix"]
        if let firstValidTitle = lines.first(where: { line in
            let lower = line.trimmingCharacters(in: .whitespaces).lowercased()
            return !ignoredTitlePatterns.contains { lower.hasPrefix($0) }
        }) {
            result.append(ThesisVariable(key: "Title", value: String(firstValidTitle.trimmingCharacters(in: .whitespaces).prefix(300))))
        }

        // 2. Abstract extractor
        let abstractBlock = extractBlock(
            lines: lines,
            headings: ["abstract", "abstract:"],
            stopHeadings: ["introduction", "keywords", "background", "aims", "materials and methods"]
        )
        if !abstractBlock.isEmpty {
            result.append(ThesisVariable(key: "Abstract", value: String(abstractBlock.prefix(6000))))
        }

        // 3. Vancouver References extractor
        let referencesBlock = extractReferencesBlock(lines: lines)
        if !referencesBlock.isEmpty {
            result.append(ThesisVariable(key: "References_Vancouver", value: String(referencesBlock.prefix(12000))))
        }

        onChunk?("Extracted \(result.count) variables")
        return result
    }

    private static func extractBlock(
        lines: [String],
        headings: [String],
        stopHeadings: [String]
    ) -> String {
        let lowers = lines.map { $0.trimmingCharacters(in: .whitespaces).lowercased() }
        guard let startIndex = lowers.firstIndex(where: { h in headings.contains(h) }) else {
            return ""
        }

        let slice = lowers.suffix(from: startIndex + 1)
        let endIndex: Int
        if let stopOffset = slice.firstIndex(where: { s in stopHeadings.contains(s) }) {
            endIndex = stopOffset
        } else {
            endIndex = lines.count
        }

        let extractedLines = lines[(startIndex + 1)..<endIndex]
        return extractedLines.joined(separator: "\n").trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func extractReferencesBlock(lines: [String]) -> String {
        let lowers = lines.map { $0.trimmingCharacters(in: .whitespaces).lowercased() }
        let candidateHeadings = ["references", "references:", "bibliography", "citations", "citations:", "reference list"]

        var startIndex = lowers.firstIndex(where: { candidateHeadings.contains($0) })
        if startIndex == nil {
            // Fallback: look for lines starting with [1] or 1.
            let regex = try? NSRegularExpression(pattern: #"^\s*\[?\d{1,4}\]?\s*[.)]\s*[A-Za-z]"#)
            startIndex = lines.firstIndex(where: { line in
                let range = NSRange(location: 0, length: line.utf16.count)
                return regex?.firstMatch(in: line, range: range) != nil
            })
        }

        guard let start = startIndex else { return "" }
        let refSlice = lines.suffix(from: start + 1)
        return refSlice.joined(separator: "\n").trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
