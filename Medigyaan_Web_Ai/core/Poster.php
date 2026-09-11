<?php
require_once 'LLM.php';

class Poster {
    public static function generateData($abstract) {
        $system = "You are an expert medical conference poster designer. From the given abstract, build the COMPLETE poster content as a single JSON object. Rules: use ONLY information present in the abstract (never invent numbers, results or citations). Return ONLY valid JSON, no markdown fences, exactly this structure: {\"title\":\"<concise poster title>\",\"subtitle\":\"<1 short line>\",\"sections\":[{\"heading\":\"<heading>\",\"body\":\"<poster-ready concise text>\"}]}. Create 6-9 sections chosen from: Background/Introduction, Aim & Objectives, Methods/Materials, Results/Key Findings, Conclusion, Take-home Points, Clinical Significance, References. Keep every body under 500 characters, poster-ready and concise.";
        $messages = [
            ['role' => 'system', 'content' => $system],
            ['role' => 'user', 'content' => $abstract]
        ];

        $raw = LLM::rotateRequest($messages, 2500, 'openrouter');
        return json_decode($raw, true);
    }

    public static function generateImage($posterData) {
        $prompt = "Professional medical conference research poster titled '" . ($posterData['title'] ?? 'Research Poster') . "'. Clean academic design, teal color scheme, legible text sections, scientific layout.";
        $apiKey = Config::OPENROUTER_API_KEY;

        $ch = curl_init('https://openrouter.ai/api/v1/images/generations');
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode([
            'model' => Config::POSTER_IMAGE_MODEL,
            'prompt' => $prompt,
            'size' => Config::POSTER_IMAGE_SIZE
        ]));
        curl_setopt($ch, CURLOPT_HTTPHEADER, [
            'Content-Type: application/json',
            'Authorization: Bearer ' . $apiKey,
            'HTTP-Referer: https://medigyaan.xyz',
            'X-Title: MediGyaan Web AI'
        ]);
        curl_setopt($ch, CURLOPT_TIMEOUT, 60);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($httpCode === 200) {
            $data = json_decode($response, true);
            $url = $data['data'][0]['url'] ?? $data['data'][0]['b64_json'] ?? null;
            if ($url) return $url;
        }

        return "https://via.placeholder.com/800x1200/0d9488/ffffff?text=" . urlencode($posterData['title'] ?? 'Poster');
    }
}