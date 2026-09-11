<?php
header("Content-Type: application/json; charset=utf-8");
if (($_SERVER['HTTP_X_APP_SIGNATURE'] ?? '') !== "EduLabsRTM_Secure_v1_2026") {
    http_response_code(403);
    echo json_encode(["success" => false, "message" => "Unauthorized"]);
    exit;
}
require_once "config.php";
$need = "topic IS NULL OR TRIM(topic) = ''
    OR TRIM(topic) REGEXP '[0-9]{4}|^PG|^Neet|^pg$'";
$body = json_decode(file_get_contents('php://input'), true);
$updates = $body['updates'] ?? [];
$filled = 0;
$fail = 0;
$filled_ids = [];
$stmt = $conn->prepare(
    "UPDATE questions SET topic = ?
     WHERE question_id = ?
       AND ($need)"
);
foreach ($updates as $u) {
    $id = (int)($u['id'] ?? 0);
    $topic = trim((string)($u['topic'] ?? ''));
    if ($id <= 0 || $topic === '' || strlen($topic) < 2) { $fail++; continue; }
    $topic = mb_substr($topic, 0, 120);
    $stmt->bind_param("si", $topic, $id);
    $stmt->execute();
    if ($stmt->affected_rows > 0) { $filled++; $filled_ids[] = $id; } else { $fail++; }
}
$stmt->close();
$r = $conn->query("SELECT COUNT(*) AS c FROM questions WHERE $need");
echo json_encode([
    "success" => true,
    "filled" => $filled,
    "fail" => $fail,
    "filled_ids" => $filled_ids,
    "remaining" => (int)$r->fetch_assoc()['c'],
], JSON_UNESCAPED_UNICODE);
$conn->close();
