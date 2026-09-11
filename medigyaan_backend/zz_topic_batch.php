<?php
header("Content-Type: application/json; charset=utf-8");
if (($_SERVER['HTTP_X_APP_SIGNATURE'] ?? '') !== "EduLabsRTM_Secure_v1_2026") {
    http_response_code(403);
    echo json_encode(["success" => false, "message" => "Unauthorized"]);
    exit;
}
require_once "config.php";
$n = min(max((int)($_GET['batch'] ?? 200), 1), 500);
$need = "topic IS NULL OR TRIM(topic) = ''
    OR TRIM(topic) REGEXP '[0-9]{4}|^PG|^Neet|^pg$'";
$r = $conn->query("SELECT COUNT(*) AS c FROM questions WHERE $need");
$out = ["success" => true, "remaining" => (int)$r->fetch_assoc()['c'], "rows" => []];
$stmt = $conn->prepare(
    "SELECT question_id AS id, LEFT(question, 400) AS q
     FROM questions
     WHERE $need
     ORDER BY question_id ASC
     LIMIT ?"
);
$stmt->bind_param("i", $n);
$stmt->execute();
$res = $stmt->get_result();
while ($row = $res->fetch_assoc()) {
    $out["rows"][] = ["id" => (int)$row['id'], "q" => $row['q']];
}
echo json_encode($out, JSON_UNESCAPED_UNICODE);
$conn->close();
