<?php
declare(strict_types=1);

header("Content-Type: application/json; charset=UTF-8");
ini_set('display_errors', '0');
error_reporting(E_ALL);

// Optional. Keep only if you really need DB in this file.
if (file_exists(__DIR__ . '/db_connection.php')) {
    include __DIR__ . '/db_connection.php';
}

/* ================= SAFE RESPONSE ================= */

function respond(array $arr): void
{
    echo json_encode($arr, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function clean(string $value): string
{
    return trim($value);
}

function post(string $key, string $default = ''): string
{
    return isset($_POST[$key]) ? clean((string)$_POST[$key]) : $default;
}

function lower(string $value): string
{
    return function_exists('mb_strtolower')
        ? mb_strtolower($value, 'UTF-8')
        : strtolower($value);
}

/* ================= LOAD KEYS ================= */

$cfgFile = __DIR__ . '/api_key.php';

if (!file_exists($cfgFile)) {
    respond(["success" => false, "message" => "api_key.php missing"]);
}

$cfg = include $cfgFile;

$groqKey       = trim((string)($cfg['GROQ_API_KEY'] ?? ''));
$geminiKey     = trim((string)($cfg['GEMINI_API_KEY'] ?? ''));
$openRouterKey = trim((string)($cfg['OPENROUTER_API_KEY'] ?? ''));

/* ================= INPUT ================= */

$question    = post('question');
$query       = post('query');
$subject     = post('subject');
$topic       = post('topic');
$explanation = post('explanation');
$chat_history = post('chat_history');

if ($question === '' && $query === '') {
    respond([
        "success" => false,
        "message" => "No input provided"
    ]);
}

/* ================= MODE DECIDER ================= */

$qLower = lower($query);

$chatTriggers = ["hi", "hello", "what is", "who is", "tell me", "define", "joke", "ai", "life"];

$mode = "exam";

if ($question === '') {
    $mode = "chat";
}

foreach ($chatTriggers as $word) {
    if ($query !== '' && strpos($qLower, $word) !== false && strlen($query) < 120) {
        $mode = "chat";
        break;
    }
}

if ($question !== '' && strlen($query) < 80 && $explanation !== '') {
    $mode = "follow";
}

/* ================= PROMPT BUILDER ================= */

if ($mode === "chat") {
    $prompt = "
You are a ChatGPT-like assistant.
" . ($chat_history !== "" ? "\nConversation History:\n" . $chat_history . "\n" : "") . "
User:
$query

Instructions:
- Answer freely on any topic
- Be natural and helpful
- Do NOT mention MCQ unless asked
";
} elseif ($mode === "follow") {
    $prompt = "
Context:
Question: $question

Previous explanation:
$explanation
" . ($chat_history !== "" ? "\nConversation History:\n" . $chat_history . "\n" : "") . "
User follow-up:
$query

Instructions:
- Do NOT repeat full explanation
- Answer ONLY what user asked
- Add extra concept / trick / memory tip
- Be short (max 4 lines)
";
} else {
    $prompt = "
Subject: $subject
Topic: $topic

Question:
$question

User request:
$query

Instructions:
- Give exam-focused explanation
- Mention correct answer clearly
- Briefly explain why others are wrong
- Max 5 lines
";
}

/* ================= CURL HELPER ================= */

function apiRequest(string $url, array $headers, array $payload): array
{
    $ch = curl_init($url);

    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_TIMEOUT => 60,
        CURLOPT_CONNECTTIMEOUT => 20,
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_SSL_VERIFYHOST => 2,
    ]);

    $response = curl_exec($ch);
    $httpCode = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $curlErr  = curl_error($ch);

    curl_close($ch);

    return [
        'http' => $httpCode,
        'error' => $curlErr,
        'response' => $response
    ];
}

/* =========================================================
   GEMINI
========================================================= */

function askGemini(string $prompt, string $apiKey)
{
    if ($apiKey === '' || str_contains($apiKey, 'YOUR_')) {
        return false;
    }

    $url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" . urlencode($apiKey);

    // Correct Gemini payload
    $payload = [
        "contents" => [
            [
                "parts" => [
                    [
                        "text" => $prompt
                    ]
                ]
            ]
        ]
    ];

    $res = apiRequest(
        $url,
        ["Content-Type: application/json"],
        $payload
    );

    if (!empty($res['error'])) {
        return [
            "provider" => "Gemini",
            "error" => $res['error'],
            "debug" => $res
        ];
    }

    $json = json_decode((string)$res['response'], true);

    $text = trim((string)($json['candidates'][0]['content']['parts'][0]['text'] ?? ''));

    if ($text !== '') {
        return [
            "provider" => "Gemini",
            "model" => "gemini-2.0-flash",
            "answer" => $text
        ];
    }

    return [
        "provider" => "Gemini",
        "error" => "Empty or invalid response",
        "debug" => $json
    ];
}

/* =========================================================
   GROQ
========================================================= */

function askGroq(string $prompt, string $apiKey)
{
    if ($apiKey === '' || str_contains($apiKey, 'YOUR_')) {
        return false;
    }

    $payload = [
        "model" => "llama-3.1-8b-instant",
        "messages" => [
            ["role" => "system", "content" => "You are a smart AI assistant."],
            ["role" => "user", "content" => $prompt]
        ],
        "temperature" => 0.5,
        "max_tokens" => 500
    ];

    $res = apiRequest(
        "https://api.groq.com/openai/v1/chat/completions",
        [
            "Authorization: Bearer " . $apiKey,
            "Content-Type: application/json"
        ],
        $payload
    );

    if (!empty($res['error'])) {
        return [
            "provider" => "Groq",
            "error" => $res['error'],
            "debug" => $res
        ];
    }

    $json = json_decode((string)$res['response'], true);

    $text = trim((string)($json['choices'][0]['message']['content'] ?? ''));

    if ($text !== '') {
        return [
            "provider" => "Groq",
            "model" => "llama-3.1-8b-instant",
            "answer" => $text
        ];
    }

    return [
        "provider" => "Groq",
        "error" => "Empty or invalid response",
        "debug" => $json
    ];
}

/* =========================================================
   OPENROUTER
========================================================= */

function askOpenRouter(string $prompt, string $apiKey)
{
    if ($apiKey === '' || str_contains($apiKey, 'YOUR_')) {
        return false;
    }

    $payload = [
        "model" => "openai/gpt-3.5-turbo",
        "messages" => [
            ["role" => "system", "content" => "You are a helpful AI."],
            ["role" => "user", "content" => $prompt]
        ],
        "temperature" => 0.5,
        "max_tokens" => 500
    ];

    $res = apiRequest(
        "https://openrouter.ai/api/v1/chat/completions",
        [
            "Authorization: Bearer " . $apiKey,
            "Content-Type: application/json",
            "HTTP-Referer: http://localhost",
            "X-Title: Voice AI Assistant"
        ],
        $payload
    );

    if (!empty($res['error'])) {
        return [
            "provider" => "OpenRouter",
            "error" => $res['error'],
            "debug" => $res
        ];
    }

    $json = json_decode((string)$res['response'], true);

    $text = trim((string)($json['choices'][0]['message']['content'] ?? ''));

    if ($text !== '') {
        return [
            "provider" => "OpenRouter",
            "model" => "openai/gpt-3.5-turbo",
            "answer" => $text
        ];
    }

    return [
        "provider" => "OpenRouter",
        "error" => "Empty or invalid response",
        "debug" => $json
    ];
}

/* ================= AI FALLBACK ================= */

$result = askGemini($prompt, $geminiKey);

if (!$result || empty($result['answer'])) {
    $result = askGroq($prompt, $groqKey);
}

if ((!$result || empty($result['answer'])) && $openRouterKey !== '') {
    $result = askOpenRouter($prompt, $openRouterKey);
}

/* ================= FINAL ================= */

if (!$result || empty($result['answer'])) {
    respond([
        "success" => false,
        "message" => "AI failed",
        "mode" => $mode,
        "debug" => $result
    ]);
}

respond([
    "success" => true,
    "mode" => $mode,
    "provider" => $result['provider'],
    "model" => $result['model'] ?? '',
    "answer" => $result['answer']
]);
?>