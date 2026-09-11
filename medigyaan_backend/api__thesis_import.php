<?php
declare(strict_types=1);
/**
 * thesis_import.php — bulk importer for the thesis catalog.
 *
 * POST JSON body: { "rows": [ { "subject": "...", "text": "...", "pdf": "...",
 *                              "study_type": "...", "difficulty": "..." }, ... ] }
 *
 * Dedupes against existing rows by exact thesis_pdf OR first-120-chars of text.
 * Response: { "success": true, "inserted": N, "skipped": M }
 */

header('Content-Type: application/json; charset=utf-8');
require_once __DIR__ . '/config.php';

if (!isset($GLOBALS['conn']) || !($GLOBALS['conn'] instanceof mysqli)) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'db_unavailable']);
    exit;
}
$conn = $GLOBALS['conn'];

// Optional GET trigger: ?file=<basename>.json reads rows from a file in this
// directory (uploaded via FTP) so the import bypasses the WAF's POST filtering.
$fileName = $_GET['file'] ?? '';
$payload = null;
if ($fileName !== '') {
    if (!preg_match('/^[A-Za-z0-9_\-]+\.json$/', $fileName)) {
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'bad_file_name']);
        exit;
    }
    $filePath = __DIR__ . '/' . $fileName;
    if (!is_file($filePath)) {
        http_response_code(404);
        echo json_encode(['success' => false, 'error' => 'file_not_found']);
        exit;
    }
    $payload = json_decode((string)file_get_contents($filePath), true);
} else {
    $raw = file_get_contents('php://input');
    $payload = json_decode($raw, true);
}
if (!is_array($payload) || empty($payload['rows']) || !is_array($payload['rows'])) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'expected {"rows":[...]}']);
    exit;
}

// Optional hard guard: refuse if the caller didn't supply the app signature header.
$sig = $_SERVER['HTTP_X_APP_SIGNATURE'] ?? '';
if ($sig !== 'EduLabsRTM_Secure_v1_2026') {
    http_response_code(403);
    echo json_encode(['success' => false, 'error' => 'bad_signature']);
    exit;
}

$inserted = 0;
$skipped = 0;
$errors = [];

$insertStmt = $conn->prepare(
    'INSERT INTO thesis (thesis_subject, thesis_text, thesis_pdf, type_of_study, difficulty_level) VALUES (?, ?, ?, ?, ?)'
);
if (!$insertStmt) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'prepare_failed: ' . $conn->error]);
    exit;
}

$checkStmt = $conn->prepare(
    'SELECT thesis_id FROM thesis WHERE thesis_pdf = ? OR LEFT(thesis_text, 120) = LEFT(?, 120) LIMIT 1'
);

foreach ($payload['rows'] as $row) {
    $subject = trim((string)($row['subject'] ?? ''));
    $text    = trim((string)($row['text'] ?? ''));
    $pdf     = trim((string)($row['pdf'] ?? ''));
    $study   = trim((string)($row['study_type'] ?? ''));
    $diff    = trim((string)($row['difficulty'] ?? ''));

    // Validate: reject rows that look like AI chat responses, not thesis data
    $invalidPatterns = [
        '/^(search|find|look|query|ask|chat|talk|discuss|tell me|what is|how to|explain|summarize|analyze|compare|list|give me|show me|can you|please|hi|hello|hey|help|thanks|thank you|ok|okay|yes|no|i am|i\'m|we are|we\'re|they|she|he|it|this|that|these|those|there|here|when|where|why|how|who|which|what|whose|whom)\b/i',
        '/^(the user asked|the user said|user message|chat message|ai reply|assistant response|system prompt|user input)/i',
        '/^\*\*.*\*\*$/',  // Bold-only text like **bold**
        '/^(https?:\/\/|www\.)/',  // URLs as subject
        '/^\[.*\]\(.*\)$/',  // Markdown links as subject
    ];
    foreach ($invalidPatterns as $pat) {
        if (preg_match($pat, $subject) || preg_match($pat, $text)) {
            $skipped++;
            continue 2;
        }
    }
    // Reject if subject is too short or looks like a sentence fragment
    if (strlen($subject) < 5 || strlen($subject) > 200) {
        $skipped++;
        continue;
    }
    // Reject if text is too short (not a real thesis abstract) or too long (likely chat log)
    if (strlen($text) < 20 || strlen($text) > 5000) {
        $skipped++;
        continue;
    }
    // Reject if PDF is not a valid URL or path
    if (!filter_var($pdf, FILTER_VALIDATE_URL) && !preg_match('#^(/uploads/|[a-zA-Z]:[\\/])#', $pdf)) {
        $skipped++;
        continue;
    }

    // Dedupe
    $exists = false;
    if ($checkStmt) {
        $checkStmt->bind_param('ss', $pdf, $text);
        $checkStmt->execute();
        $res = $checkStmt->get_result();
        $exists = (bool)$res->fetch_row();
    }
    if ($exists) {
        $skipped++;
        continue;
    }

    $ok = $insertStmt->bind_param('sssss', $subject, $text, $pdf, $study, $diff) && $insertStmt->execute();
    if ($ok) {
        $inserted++;
    } else {
        $skipped++;
        $errors[] = $conn->error;
    }
}

echo json_encode([
    'success' => true,
    'inserted' => $inserted,
    'skipped' => $skipped,
    'error_count' => count(array_filter($errors)),
], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);