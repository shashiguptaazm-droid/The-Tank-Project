import Foundation
import UIKit
import PDFKit
import Vision

/// Extracts text and OCR from medical documents, clinical PDFs, and exam slides.
/// 1:1 port of Android `AiDocumentOcrHelper.kt`.
public enum AiDocumentOcrHelper {

    /// Checks if a file extension is supported for automated AI extraction.
    public static func isEligibleForAi(extension ext: String) -> Bool {
        let clean = ext.lowercased().trimmingCharacters(in: .whitespacesAndNewlines).replacingOccurrences(of: ".", with: "")
        let eligible = [
            "pdf", "doc", "docx", "ppt", "pptx", "txt", "text", "csv", "json", "xml", "md", "markdown", "log", "rtf", "tsv",
            "jpg", "jpeg", "png", "webp", "bmp", "heic"
        ]
        return eligible.contains(clean)
    }

    /// Extract text directly from PDF data or OCR scanned pages.
    public static func extractText(from pdfData: Data) -> String {
        guard let document = PDFDocument(data: pdfData) else { return "" }
        var fullText = ""

        for pageIndex in 0..<document.pageCount {
            guard let page = document.page(at: pageIndex) else { continue }
            if let pageString = page.string, !pageString.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                fullText += "\n--- Page \(pageIndex + 1) ---\n" + pageString
            }
        }

        return fullText.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// Native Vision OCR on image for lab charts, ECGs, and scanned clinical images.
    public static func recognizeText(from image: UIImage) async -> String {
        guard let cgImage = image.cgImage else { return "" }

        return await withCheckedContinuation { continuation in
            let request = VNRecognizeTextRequest { request, error in
                guard error == nil,
                      let observations = request.results as? [VNRecognizedTextObservation] else {
                    continuation.resume(returning: "")
                    return
                }

                let recognizedStrings = observations.compactMap { observation in
                    observation.topCandidates(1).first?.string
                }

                continuation.resume(returning: recognizedStrings.joined(separator: "\n"))
            }

            request.recognitionLevel = .accurate
            request.usesLanguageCorrection = true

            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
            do {
                try handler.perform([request])
            } catch {
                continuation.resume(returning: "")
            }
        }
    }
}
