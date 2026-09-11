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

/* ================= TRAINING LOG (best-effort) ================= */

function logAiExchangeForTraining(array $entry): void
{
    try {
        $ctx = [];
        if (isset($entry['conn']) && $entry['conn'] instanceof PDO) {
            $conn = $entry['conn'];
            $conn->exec("CREATE TABLE IF NOT EXISTS ai_training_log (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                source VARCHAR(40) NOT NULL DEFAULT 'unknown',
                user_id INT NOT NULL DEFAULT 0,
                provider VARCHAR(60) NOT NULL DEFAULT '',
                model VARCHAR(120) NOT NULL DEFAULT '',
                prompt MEDIUMTEXT,
                response MEDIUMTEXT,
                status VARCHAR(20) NOT NULL DEFAULT 'completed',
                context TEXT,
                duration_ms BIGINT NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                KEY idx_source_created (source, created_at),
                KEY idx_user_created (user_id, created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
            $stmt = $conn->prepare(
                'INSERT INTO ai_training_log
                    (source, user_id, provider, model, prompt, response, status, context, duration_ms)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
            );
            $stmt->execute([
                $entry['source'],
                (int)$entry['user_id'],
                $entry['provider'],
                $entry['model'],
                $entry['prompt'],
                $entry['response'],
                $entry['status'],
                $entry['context'],
                (int)$entry['duration_ms']
            ]);
            return;
        }
        if (isset($entry['conn']) && $entry['conn'] instanceof mysqli) {
            $conn = $entry['conn'];
            $conn->query("CREATE TABLE IF NOT EXISTS ai_training_log (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                source VARCHAR(40) NOT NULL DEFAULT 'unknown',
                user_id INT NOT NULL DEFAULT 0,
                provider VARCHAR(60) NOT NULL DEFAULT '',
                model VARCHAR(120) NOT NULL DEFAULT '',
                prompt MEDIUMTEXT,
                response MEDIUMTEXT,
                status VARCHAR(20) NOT NULL DEFAULT 'completed',
                context TEXT,
                duration_ms BIGINT NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                KEY idx_source_created (source, created_at),
                KEY idx_user_created (user_id, created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
            $stmt = $conn->prepare(
                'INSERT INTO ai_training_log
                    (source, user_id, provider, model, prompt, response, status, context, duration_ms)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
            );
            $stmt->bind_param(
                'sissssssi',
                $entry['source'],
                (int)$entry['user_id'],
                $entry['provider'],
                $entry['model'],
                $entry['prompt'],
                $entry['response'],
                $entry['status'],
                $entry['context'],
                (int)$entry['duration_ms']
            );
            $stmt->execute();
            $stmt->close();
        }
    } catch (Throwable $e) {
        // Logging must never break the AI response.
    }
}

/* ================= FINAL ================= */

$trainingCtx = [
    'question' => $question,
    'query'    => $query,
    'subject'  => $subject,
    'topic'    => $topic,
    'mode'     => $mode
];
$trainingContextJson = json_encode($trainingCtx, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);

if (!$result || empty($result['answer'])) {
    if (isset($conn)) {
        logAiExchangeForTraining([
            'conn'        => $conn,
            'source'      => 'ask_ai',
            'user_id'     => (int)post('user_id'),
            'provider'    => is_array($result) ? (string)($result['provider'] ?? '') : '',
            'model'       => is_array($result) ? (string)($result['model'] ?? '') : '',
            'prompt'      => $prompt,
            'response'    => '',
            'status'      => 'failed',
            'context'     => $trainingContextJson,
            'duration_ms' => 0
        ]);
    }
    respond([
        "success" => false,
        "message" => "AI failed",
        "mode" => $mode,
        "debug" => $result
    ]);
}

if (isset($conn)) {
    logAiExchangeForTraining([
        'conn'        => $conn,
        'source'      => 'ask_ai',
        'user_id'     => (int)post('user_id'),
        'provider'    => (string)($result['provider'] ?? ''),
        'model'       => (string)($result['model'] ?? ''),
        'prompt'      => $prompt,
        'response'    => (string)$result['answer'],
        'status'      => 'completed',
        'context'     => $trainingContextJson,
        'duration_ms' => 0
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