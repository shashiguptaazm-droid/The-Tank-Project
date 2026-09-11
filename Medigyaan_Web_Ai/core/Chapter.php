<?php
require_once 'LLM.php';

class Chapter {
    public static function generate($chapterName, $pdfContext) {
        $schema = "{ \"chapter_name\": \"...\", \"sections\": [{ \"heading\": \"...\", \"paragraphs\": [\"...\"] }] }";
        $system = "Generate a medical thesis chapter named '$chapterName' using the provided PDF context. Return ONLY valid JSON matching this schema: $schema";

        $messages = [
            ['role' => 'system', 'content' => $pdfContext],
            ['role' => 'system', 'content' => $system],
            ['role' => 'user', 'content' => "Write the $chapterName chapter."]
        ];

        $raw = LLM::rotateRequest($messages, 4000);
        return json_decode($raw, true);
    }
}
