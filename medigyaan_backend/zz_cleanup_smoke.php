<?php
header("Content-Type: application/json");
require_once "config.php";
$stmt = $conn->prepare("DELETE FROM questions WHERE topic IN ('AI Gen Smoke Test 9x7','AI AutoGen Test 5v9')");
$stmt->execute();
echo json_encode(["deleted" => $stmt->affected_rows]);
?>
