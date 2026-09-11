<?php
require_once 'Config.php';

class PdfExtractor {
    public static function extractText($filePath) {
        if (!file_exists($filePath)) {
            throw new Exception("File not found: $filePath");
        }

        $ext = strtolower(pathinfo($filePath, PATHINFO_EXTENSION));
        if ($ext === 'pdf') {
            return self::extractFromPdf($filePath);
        }

        return file_get_contents($filePath);
    }

    private static function extractFromPdf($filePath) {
        $content = file_get_contents($filePath);
        if ($content === false) return '';

        $text = '';
        $lines = preg_split('/\r\n|\r|\n/', $content);
        foreach ($lines as $line) {
            $cleaned = trim($line);
            if (empty($cleaned)) continue;
            if (preg_match('/^[\x00-\x1F\x80-\xFF]+$/', $cleaned)) continue;
            $text .= $cleaned . "\n";
        }
        return $text ?: 'PDF content could not be fully extracted. Please upload a text-based PDF.';
    }
}