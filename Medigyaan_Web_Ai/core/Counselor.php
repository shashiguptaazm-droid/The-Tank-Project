<?php
require_once 'Config.php';

class Counselor {
    public static function query($rank, $category, $course, $state) {
        $apiKey = Config::ENDPOINT_AI_API_KEY;
        $url = Config::ENDPOINT_AI_BASE_URL . "ai_predictor.php";

        $body = json_encode([
            'rank' => $rank,
            'category' => $category,
            'course' => $course,
            'state' => $state
        ]);

        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
        curl_setopt($ch, CURLOPT_HTTPHEADER, [
            'Content-Type: application/json',
            'Authorization: Bearer ' . $apiKey
        ]);
        curl_setopt($ch, CURLOPT_TIMEOUT, 60);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($httpCode !== 200) {
            throw new Exception("Counselor API HTTP $httpCode: $response");
        }

        $data = json_decode($response, true);
        return $data['results'] ?? $data;
    }

    public static function generateAdvice($results) {
        $safe = array_filter($results, fn($r) => ($r['chance'] ?? '') === 'Safe');
        $dream = array_filter($results, fn($r) => ($r['chance'] ?? '') === 'Dream');
        $target = array_filter($results, fn($r) => ($r['chance'] ?? '') === 'Target');

        $advice = "Based on your rank, here are your options:\n";
        $advice .= "🎯 Dream (" . count($dream) . "): " . implode(", ", array_column($dream, 'institute')) . "\n";
        $advice .= "✅ Target (" . count($target) . "): " . implode(", ", array_column($target, 'institute')) . "\n";
        $advice .= "🛡 Safe (" . count($safe) . "): " . implode(", ", array_column($safe, 'institute')) . "\n";

        return $advice;
    }
}