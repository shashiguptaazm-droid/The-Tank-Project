<?php
/**
 * generate_questions_ai.php
 * "No user goes empty handed" module.
 *
 * If a (subject, topic) has no questions (or very few), this module asks an AI
 * (Groq llama) to write exam-style MCQs and inserts them into the same `questions`
 * table used everywhere else, so getQuestions/getTopics/searchv2 pick them up.
 *
 * Endpoint (signed, POST):
 *   subject  (string, required)
 *   topic    (string, required)
 *   count    (int, default 5, max 10)  -> desired total questions for the topic
 *
 * Also exposes generateQuestionsForTopic($conn, $subject, $topic, $count)
 * so getQuestions.php can auto-top-up on an empty result.
 */

function generateQuestionsForTopic($conn, string $subject, string $topic, int $count): array
{
    $count = max(1, min(10, $count));

    // Existing questions for this topic
    $stmt = $conn->prepare("SELECT COUNT(*) AS c FROM questions WHERE subject = ? AND topic = ?");
    $stmt->bind_param("ss", $subject, $topic);
    $stmt->execute();
    $existing = (int)$stmt->get_result()->fetch_assoc()['c'];
    $stmt->close();

    $toCreate = max(0, $count - $existing);
    if ($toCreate === 0) {
        return ["success" => true, "existing" => $existing, "generated" => 0, "total" => $existing, "questions" => []];
    }

    // Load server-side AI keys (Neurons/api -> ../api_key.php)
    $cfgFile = __DIR__ . '/../api_key.php';
    if (!file_exists($cfgFile)) {
        throw new Exception("api_key.php missing");
    }
    $cfg = include $cfgFile;
    $groqKey = trim((string)($cfg['GROQ_API_KEY'] ?? ''));
    if ($groqKey === '' || str_contains($groqKey, 'YOUR_')) {
        throw new Exception("GROQ_API_KEY missing");
    }

    // Build the prompt: valid NEET PG style questions for the topic.
    $prompt = <<<PROMPT
You are an expert NEET PG (National Eligibility cum Entrance Test Postgraduate) question writer.

Write {$toCreate} high-quality single-best-answer multiple choice questions for:
Subject: {$subject}
Topic: {$topic}

Requirements:
- Exam style, clinically relevant, accurate to standard textbooks (Harrison's, Guyton, Robbins, etc).
- Exactly 4 options per question (A, B, C, D), exactly one correct.
- Each question needs a short exam-focused explanation (2-4 lines) of why the correct answer is right.
- Do NOT reuse standard question-bank questions verbatim; write fresh but conventional questions.
- Vary difficulty: most moderate, some easy/hard.
- No images needed.

Return ONLY a JSON array (no markdown fences, no commentary). Each element must have exactly these keys:
question (string), option_a (string), option_b (string), option_c (string), option_d (string), correct_option (single letter "A","B","C" or "D"), explanation (string).
PROMPT;

    $payload = [
        "model" => "qwen/qwen3.8-27b",
        "messages" => [
            ["role" => "system", "content" => "You output strict JSON only."],
            ["role" => "user", "content" => $prompt]
        ],
        "temperature" => 0.7,
        "max_tokens" => 3000,
        "response_format" => ["type" => "json_object"]
    ];

    $raw = null;
    for ($attempt = 0; $attempt < 2; $attempt++) {
        $ch = curl_init("https://api.groq.com/openai/v1/chat/completions");
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
            CURLOPT_HTTPHEADER => [
                "Authorization: Bearer " . $groqKey,
                "Content-Type: application/json"
            ],
            CURLOPT_TIMEOUT => 90,
            CURLOPT_CONNECTTIMEOUT => 20,
        ]);
        $raw = curl_exec($ch);
        $httpCode = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $curlErr = curl_error($ch);
        curl_close($ch);

        if ($raw !== false && $httpCode === 200) {
            break;
        }
        $payload["temperature"] = 0.9; // retry with more variety
    }

    if ($raw === false || $raw === '') {
        throw new Exception("AI request failed: " . ($curlErr ?? 'empty response'));
    }

    $json = json_decode($raw, true);
    $text = trim((string)($json['choices'][0]['message']['content'] ?? ''));
    if ($text === '') {
        throw new Exception("AI returned an empty answer");
    }

    // Defensive JSON extraction
    $text = trim($text);
    if (str_starts_with($text, '```')) {
        $text = preg_replace('/^```[a-zA-Z]*/', '', $text);
        $text = preg_replace('/```$/', '', $text);
        $text = trim($text);
    }
    // Some models wrap in {"questions": [...]} or {"data": [...]}
    $decoded = json_decode($text, true);
    if (!is_array($decoded)) {
        $jsonStart = strpos($text, '[');
        $jsonEnd = strrpos($text, ']');
        if ($jsonStart !== false && $jsonEnd !== false && $jsonEnd > $jsonStart) {
            $decoded = json_decode(substr($text, $jsonStart, $jsonEnd - $jsonStart + 1), true);
        }
    }
    if (!is_array($decoded)) {
        throw new Exception("AI returned unparsable JSON");
    }
    if (isset($decoded['questions']) && is_array($decoded['questions'])) {
        $decoded = $decoded['questions'];
    }
    if (isset($decoded['data']) && is_array($decoded['data'])) {
        $decoded = $decoded['data'];
    }
    $items = array_values($decoded);

    $inserted = [];
    $insertedCount = 0;
    foreach ($items as $item) {
        if ($insertedCount >= $toCreate) break;
        if (!is_array($item)) continue;

        $q = trim((string)($item['question'] ?? ''));
        $oa = trim((string)($item['option_a'] ?? ''));
        $ob = trim((string)($item['option_b'] ?? ''));
        $oc = trim((string)($item['option_c'] ?? ''));
        $od = trim((string)($item['option_d'] ?? ''));
        $exp = trim((string)($item['explanation'] ?? ''));
        $correct = strtoupper(trim((string)($item['correct_option'] ?? '')));
        if (!in_array($correct, ["A", "B", "C", "D"], true)) $correct = "A";

        if ($q === '' || $oa === '' || $ob === '' || $oc === '' || $od === '') continue;

        $ins = $conn->prepare(
            "INSERT INTO questions (subject, topic, question, option_a, option_b, option_c, option_d, correct_option, explanation, question_image)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)"
        );
        if (!$ins) {
            throw new Exception("Insert prepare failed: " . $conn->error);
        }
        $ins->bind_param("sssssssss", $subject, $topic, $q, $oa, $ob, $oc, $od, $correct, $exp);
        $ins->execute();
        if ($ins->affected_rows > 0) {
            $newId = (int)$conn->insert_id;
            $inserted[] = [
                "question_id" => $newId,
                "question" => $q,
                "option_a" => $oa,
                "option_b" => $ob,
                "option_c" => $oc,
                "option_d" => $od,
                "correct_option" => $correct,
                "explanation" => $exp,
                "subject" => $subject,
                "topic" => $topic,
                "question_image" => null
            ];
            $insertedCount++;
        }
        $ins->close();
    }

    if ($insertedCount === 0) {
        throw new Exception("No valid questions could be inserted");
    }

    return [
        "success" => true,
        "existing" => $existing,
        "generated" => $insertedCount,
        "total" => $existing + $insertedCount,
        "subject" => $subject,
        "topic" => $topic,
        "questions" => $inserted
    ];
}

/* ---------------- Direct endpoint usage ---------------- */
if (basename($_SERVER['SCRIPT_NAME'] ?? '') === basename(__FILE__)) {
    header("Content-Type: application/json; charset=utf-8");
    ob_start();

    $expectedSignature = "EduLabsRTM_Secure_v1_2026";
    $appSignature = $_SERVER['HTTP_X_APP_SIGNATURE'] ?? '';
    if ($appSignature !== $expectedSignature) {
        http_response_code(403);
        echo json_encode(["success" => false, "message" => "Unauthorized App Access"]);
        exit;
    }

    require_once "config.php";

    $subject = isset($_POST['subject']) ? trim($_POST['subject']) : '';
    $topic = isset($_POST['topic']) ? trim($_POST['topic']) : '';
    $count = isset($_POST['count']) ? intval($_POST['count']) : 5;

    $response = ["success" => false];
    try {
        if ($subject === '' || $topic === '') {
            throw new Exception("subject and topic are required");
        }
        $response = generateQuestionsForTopic($conn, $subject, $topic, $count);
    } catch (Exception $e) {
        $response = ["success" => false, "message" => $e->getMessage()];
    }

    if (ob_get_length()) ob_clean();
    echo json_encode($response);
    if (isset($conn)) $conn->close();
    exit;
}
