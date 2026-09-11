<?php
require_once 'Config.php';
require_once 'LLM.php';

class Thesis {
    public static function searchTopics($subject) {
        $apiKey = Config::ENDPOINT_AI_API_KEY;
        $url = Config::ENDPOINT_AI_BASE_URL . "thesis_search.php?subject=" . urlencode($subject);

        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 30);
        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($httpCode !== 200) {
            throw new Exception("Thesis search HTTP $httpCode");
        }

        $data = json_decode($response, true);
        return $data['results'] ?? $data ?? [];
    }

    public static function generateChapter($chapterName, $pdfContext) {
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