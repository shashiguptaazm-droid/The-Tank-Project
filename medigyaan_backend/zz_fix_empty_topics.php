<?php
/**
 * zz_fix_empty_topics.php — one-shot bulk worker (temporary; delete after use).
 *
 * Stateless + resumable: every request takes the next `batch` question rows whose
 * topic is empty or a placeholder ("PG 2020" style), AI-classifies each stem into a
 * concise topic, and writes it back (guarded so it never overwrites a real topic).
 *
 * GET params:
 *   batch     (default 60, max 200) rows processed per request
 *   countonly (1)  -> just report how many rows still need a topic (no AI)
 *
 * Response: {success, remaining, processed, filled, failed, sample:[{question_id,topic}]}
 */

header("Content-Type: application/json; charset=utf-8");
ob_start();

if (($_SERVER['HTTP_X_APP_SIGNATURE'] ?? '') !== "EduLabsRTM_Secure_v1_2026") {
    http_response_code(403);
    echo json_encode(["success" => false, "message" => "Unauthorized App Access"]);
    exit;
}

require_once "config.php";

$GLOBALS['need'] = "topic IS NULL OR TRIM(topic) = ''
    OR TRIM(topic) REGEXP '[0-9]{4}|^PG|^Neet|^pg$'";

function remainingCount($conn): int
{
    $r = $conn->query("SELECT COUNT(*) AS c FROM questions WHERE " . $GLOBALS['need']);
    return (int)$r->fetch_assoc()['c'];
}

/**
 * Classifies stems into topics using ONLY free OpenRouter models (:free,
 * zero pricing) — no paid calls. Rotates across models to spread load.
 * Returns map id => topic.
 */
function aiClassify(array $rows): array
{
    static $rotation = 0;
    // Free OpenRouter models (verified live: pricing 0 / 0)
    $models = [
        "google/gemma-4-31b-it:free",
        "z-ai/glm-5.2:free",
        "minimax/minimax-m2.7:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "google/gemma-4-26b-a4b-it:free",
        "thinkingmachines/inkling-small:free",
        "nvidia/nemotron-3.5-lightning:free",
        "minimax/minimax-m3:free",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
    ];
    $poolFile = __DIR__ . '/zz_ai_keys_pool.php';
    if (!file_exists($poolFile)) { $GLOBALS['aiDebug'] = 'key pool missing'; return []; }
    $pool = include $poolFile;
    $orKey = trim((string)($pool['OPENROUTER_API_KEY'] ?? ''));
    if ($orKey === '') { $GLOBALS['aiDebug'] = 'no openrouter key'; return []; }

    $prompt = "You classify exam MCQs by the single core topic they test.\n"
        . "For each indexed question below reply with ONE concise topic label (1-4 words, e.g. "
        . "\"Severe acute malnutrition\", \"Ohm law\", \"Contract consideration\", \"Hematologic malignancy\"). "
        . "If the stem references an image, classify by the text. Use the disease/drug/concept named in the stem.\n"
        . "Return ONLY a JSON object: {\"items\":[{\"index\":0,\"topic\":\"...\"}, ...]}\n"
        . "No markdown fences, no commentary.\n\nQuestions:\n";

    $chunkList = array_values($rows); // sequential 0..n so model indices map 1:1
    $chunks = array_chunk($chunkList, 40);
    $out = [];
    $attemptLog = [];
    foreach ($chunks as $chunk) {
        $p = $prompt;
        foreach ($chunk as $i => $row) {
            $p .= "[" . $i . "] " . $row['q'] . "\n";
        }
        // Try up to 4 DIFFERENT free models for this chunk (free endpoints are
        // individually rate-limited, so a 429 on one should fall through to the next).
        $raw = null;
        $usedModel = '';
        for ($try = 0; $try < 4; $try++) {
            $model = $models[$rotation % count($models)];
            $rotation++;
            $payload = [
                "model" => $model,
                "messages" => [
                    ["role" => "system", "content" => "You are a precise classifier. Reply with ONLY the requested JSON object and nothing else."],
                    ["role" => "user", "content" => $p],
                ],
                "temperature" => 0.1,
                "max_tokens" => 4096,
            ];
            $ch = curl_init("https://openrouter.ai/api/v1/chat/completions");
            curl_setopt_array($ch, [
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_POST => true,
                CURLOPT_POSTFIELDS => json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
                CURLOPT_HTTPHEADER => [
                    "Authorization: Bearer " . $orKey,
                    "Content-Type: application/json",
                    "HTTP-Referer: https://medigyaan.xyz",
                    "X-Title: Medigyaan Question Bank",
                ],
                CURLOPT_TIMEOUT => 150,
                CURLOPT_CONNECTTIMEOUT => 20,
            ]);
            $raw = curl_exec($ch);
            $http = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
            $attemptLog[] = 'model=' . $model . ' http=' . $http . ' err=' . curl_error($ch);
            curl_close($ch);
            if ($raw !== false && $http === 200) {
                $usedModel = $model;
                break;
            }
            usleep(1200000); // 1.2s between different-model attempts
        }
        if ($raw === false || $raw === '' || $usedModel === '') continue;

        $j = json_decode($raw, true);
        $text = trim((string)($j['choices'][0]['message']['content'] ?? ''));
        if ($text === '') continue;
        if (str_starts_with($text, '```')) {
            $text = preg_replace('/^```[a-zA-Z]*/', '', $text);
            $text = preg_replace('/```$/', '', $text);
        }
        $decoded = json_decode($text, true);
        if (!is_array($decoded)) {
            $s = strpos($text, '{');
            $e = strrpos($text, '}');
            if ($s !== false && $e !== false && $e > $s) {
                $decoded = json_decode(substr($text, $s, $e - $s + 1), true);
            }
        }
        $items = $decoded['items'] ?? null;
        if (!is_array($items)) $items = $decoded;
        foreach ((array)$items as $it) {
            if (!is_array($it)) continue;
            $idx = (int)($it['index'] ?? -1);
            if ($idx < 0 || !isset($chunk[$idx])) continue;
            $topic = trim((string)($it['topic'] ?? ''));
            if ($topic === '' || strlen($topic) < 2) continue;
            $out[$chunk[$idx]['id']] = mb_substr($topic, 0, 120);
        }
    }
    $GLOBALS['aiDebug'] = implode(' | ', $attemptLog);
    return $out;
}

$response = ["success" => true];
try {
    $countOnly = (($_GET['countonly'] ?? '0') === '1');
    $batch = min(max((int)($_GET['batch'] ?? 60), 1), 200);

    $remaining = remainingCount($conn);
    $response['remaining'] = $remaining;

    if ($countOnly || $remaining === 0) {
        $response['processed'] = 0;
        $response['filled'] = 0;
        $response['failed'] = 0;
        echo json_encode($response);
        $conn->close();
        exit;
    }

    // Pick the next batch
    $stmt = $conn->prepare(
        "SELECT question_id AS id, LEFT(question, 300) AS q
         FROM questions
         WHERE " . $GLOBALS['need'] . "
         ORDER BY question_id ASC
         LIMIT ?"
    );
    $stmt->bind_param("i", $batch);
    $stmt->execute();
    $res = $stmt->get_result();
    $rows = [];
    while ($row = $res->fetch_assoc()) $rows[$row['id']] = ['id' => (int)$row['id'], 'q' => $row['q']];
    $stmt->close();

    if (count($rows) === 0) {
        $response['remaining'] = 0;
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $labels = aiClassify($rows);

    $filled = 0;
    $failed = 0;
    $sample = [];
    foreach ($rows as $id => $row) {
        $topic = $labels[$id] ?? '';
        if ($topic === '') { $failed++; continue; }
        $upd = $conn->prepare(
            "UPDATE questions SET topic = ?
             WHERE question_id = ?
               AND (" . $GLOBALS['need'] . ")"
        );
        $upd->bind_param("si", $topic, $id);
        $upd->execute();
        if ($upd->affected_rows > 0) {
            $filled++;
            if (count($sample) < 8) $sample[] = ["question_id" => $id, "topic" => $topic];
        } else {
            $failed++;
        }
        $upd->close();
    }

    $response['processed'] = count($rows);
    $response['filled'] = $filled;
    $response['failed'] = $failed;
    $response['sample'] = $sample;
    $response['remaining'] = remainingCount($conn);
    $response['debug'] = $GLOBALS['aiDebug'] ?? '';
} catch (Exception $e) {
    $response = ["success" => false, "message" => $e->getMessage()];
}

if (ob_get_length()) ob_clean();
echo json_encode($response);
$conn->close();
exit;
