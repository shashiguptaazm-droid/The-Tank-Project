<?php
require_once 'Config.php';

class Exporter {
    public static function exportText($text, $format = 'txt') {
        $tempFile = tempnam(sys_get_temp_dir(), 'medigyaan_') . '.' . $format;
        switch ($format) {
            case 'pdf':
                self::writePdf($tempFile, $text);
                break;
            case 'docx':
                self::writeDocx($tempFile, $text);
                break;
            case 'pptx':
                self::writePptx($tempFile, $text);
                break;
            default:
                file_put_contents($tempFile, $text);
        }
        return $tempFile;
    }

    private static function writePdf($path, $text) {
        $html = '<h1>Medigyaan AI Export</h1><pre>' . htmlspecialchars($text) . '</pre>';
        file_put_contents($path, $html);
    }

    private static function writeDocx($path, $text) {
        $content = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:t>' . htmlspecialchars($text) . '</w:t></w:p></w:body>
</w:document>';
        file_put_contents($path, $content);
    }

    private static function writePptx($path, $text) {
        $content = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sld><p:cSld><p:spTree><p:sp><p:txBody><a:p xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:r><a:t>' . htmlspecialchars($text) . '</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>
</p:presentation>';
        file_put_contents($path, $content);
    }
}