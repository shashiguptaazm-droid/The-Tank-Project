<?php
require_once "config.php";

$user_id = intval($_GET['user_id']);

$result = $conn->query("SELECT quiz_id, quiz_name FROM user_quizzes WHERE user_id = $user_id");

$data = [];

while ($row = $result->fetch_assoc()) {
    $data[] = $row;
}

echo json_encode([
    "success" => true,
    "data" => $data
]);