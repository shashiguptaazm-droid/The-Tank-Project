<?php
ob_start();
header('Content-Type: application/json');

include 'db_connection.php';

$quiz_id = isset($_POST['quiz_id']) ? (int)$_POST['quiz_id'] : 0;

if ($quiz_id <= 0) {
    echo json_encode([
        "success" => false,
        "message" => "Invalid quiz_id"
    ]);
    exit;
}

$sql = "SELECT 
            q.question,
            q.option_a,
            q.option_b,
            q.option_c,
            q.option_d,
            q.correct_option
        FROM quiz_questions qq
        JOIN questions q ON qq.question_id = q.question_id
        WHERE qq.quiz_id = ?";

$stmt = $conn->prepare($sql);
$stmt->bind_param("i", $quiz_id);
$stmt->execute();

$result = $stmt->get_result();

$questions = [];

while ($row = $result->fetch_assoc()) {
    $questions[] = $row;
}

ob_clean();
echo json_encode([
    "success" => true,
    "questions" => $questions
]);
exit;