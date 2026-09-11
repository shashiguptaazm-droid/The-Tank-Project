<?php
/**
 * ai_training_log.php
 *
 * Accepts an AI exchange (prompt + model reply + provider/model + source screen)
 * and persists it to the `ai_training_log` table for future model training /
 * fine-tuning data collection.
 *
 * The table is auto-created on first use, so no phpMyAdmin step is required.
 *
 * POST (JSON body or form fields):
 *   source      - which feature produced the reply: ai_chat | ask_ai | thesis | poster | predict | other
 *   user_id     - app user id (0 when unknown)
 *   provider    - e.g. groq | gemini | openrouter | deepseek | mistral | cerebras | cloudflare ...
 *   model       - model id used
 *   prompt      - the full prompt/messages that produced the reply (plain text or JSON)
 *   response    - the model's reply text
 *   status      - completed | failed (default completed)
 *   context     - optional extra context (e.g. question id, mode, chapter) as JSON string
 *   duration_ms - optional request duration
 *
 * Response: { "success": true } — always 200 unless the DB insert itself throws.
 */

require_once __DIR__ . '/db_connection.php';

header('Content-Type: application/json; charset=UTF-8');
ini_set('display_errors', '0');
error_reporting(0);

function ai_log_fail(string $msg): void
{
    http_response_code(400);
    echo json_encode(['success' => false, 'message' => $msg]);
    exit;
}

if (!isset($conn) && isset($pdo)) {
    $conn = $pdo;
}
if (!isset($conn)) {
    ai_log_fail('Database connection not available');
}

/* ------------------------- READ INPUT ------------------------- */

$raw = file_get_contents('php://input');
$jsonIn = null;
if ($raw !== false && $raw !== '') {
    $decoded = json_decode($raw, true);
    if (is_array($decoded)) {
        $jsonIn = $decoded;
    }
}

function ai_log_val(array $src, string $key, string $default = ''): string
{
    if (isset($src[$key])) {
        return trim((string)$src[$key]);
    }
    if (isset($_POST[$key])) {
        return trim((string)$_POST[$key]);
    }
    return $default;
}

$source    = ai_log_val($jsonIn ?? [], 'source', 'other');
$userId    = (int)(isset($jsonIn['user_id']) ? $jsonIn['user_id'] : (isset($_POST['user_id']) ? (int)$_POST['user_id'] : 0));
$provider  = ai_log_val($jsonIn ?? [], 'provider', '');
$model     = ai_log_val($jsonIn ?? [], 'model', '');
$prompt    = ai_log_val($jsonIn ?? [], 'prompt', '');
$response  = ai_log_val($jsonIn ?? [], 'response', '');
$status    = ai_log_val($jsonIn ?? [], 'status', 'completed');
$context   = ai_log_val($jsonIn ?? [], 'context', '');
$durationMs = (int)(isset($jsonIn['duration_ms']) ? $jsonIn['duration_ms'] : (isset($_POST['duration_ms']) ? (int)$_POST['duration_ms'] : 0));

// Guardrails: keep the rows bounded and useful for training.
if ($source === '' || $source === 'other') {
    $source = 'unknown';
}
if (mb_strlen($source) > 40)   { $source   = mb_substr($source, 0, 40); }
if (mb_strlen($provider) > 60) { $provider = mb_substr($provider, 0, 60); }
if (mb_strlen($model) > 120)   { $model    = mb_substr($model, 0, 120); }
if (mb_strlen($status) > 20)   { $status   = mb_substr($status, 0, 20); }
$prompt   = mb_substr($prompt, 0, 500000);
$response = mb_substr($response, 0, 500000);
$context  = mb_substr($context, 0, 20000);
if ($status === '') { $status = 'completed'; }

/* ------------------------- TABLE (auto-create) ------------------------- */

$createSql = "CREATE TABLE IF NOT EXISTS ai_training_log (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";

/* ------------------------- INSERT ------------------------- */

try {
    if ($conn instanceof PDO) {
        $conn->exec($createSql);
        $stmt = $conn->prepare(
            'INSERT INTO ai_training_log
                (source, user_id, provider, model, prompt, response, status, context, duration_ms)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
        );
        $stmt->execute([$source, $userId, $provider, $model, $prompt, $response, $status, $context, $durationMs]);
    } else {
        $conn->query($createSql);
        $stmt = $conn->prepare(
            'INSERT INTO ai_training_log
                (source, user_id, provider, model, prompt, response, status, context, duration_ms)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
        );
        $stmt->bind_param(
            'sissssssi',
            $source, $userId, $provider, $model, $prompt, $response, $status, $context, $durationMs
        );
        $stmt->execute();
        $stmt->close();
    }
} catch (Throwable $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'message' => 'Log write failed']);
    exit;
}

echo json_encode(['success' => true]);
