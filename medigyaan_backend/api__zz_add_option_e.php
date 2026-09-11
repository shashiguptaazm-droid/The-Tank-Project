<?php
header("Content-Type: application/json; charset=utf-8");
if (($_SERVER['HTTP_X_APP_SIGNATURE'] ?? '') !== "EduLabsRTM_Secure_v1_2026") {
    http_response_code(403);
    echo json_encode(["success" => false, "message" => "Unauthorized"]);
    exit;
}
require_once "config.php";

$exists = false;
$r = $conn->query("SELECT COUNT(*) AS c FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'questions' AND COLUMN_NAME = 'option_e'");
$exists = (int)$r->fetch_assoc()['c'] > 0;

if (!$exists) {
    if (!$conn->query("ALTER TABLE questions ADD COLUMN option_e TEXT NULL AFTER option_d")) {
        echo json_encode(["success" => false, "message" => "ALTER failed: " . $conn->error]);
        $conn->close();
        exit;
    }
}
echo json_encode(["success" => true, "column_added" => !$exists]);
$conn->close();