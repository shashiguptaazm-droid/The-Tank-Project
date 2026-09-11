<?php
header('Content-Type: application/json; charset=UTF-8');

// Include DB config
include_once 'config.php';

// Validate input
$question_id = isset($_GET['question_id']) ? intval($_GET['question_id']) : 0;
$user_id = isset($_GET['user_id']) ? intval($_GET['user_id']) : 0;

if ($question_id <= 0) {
    echo json_encode([
        "success" => false,
        "message" => "Question ID is missing"
    ]);
    exit;
}

try {

    // ? Added correct_option in SELECT
    $sql = "SELECT 
                question_id, 
                question, 
                option_a, 
                option_b, 
                option_c, 
                option_d, 
                question_image, 
                explanation,
                correct_option
            FROM questions 
            WHERE question_id = ?";

    $stmt = $conn->prepare($sql);
    $stmt->bind_param("i", $question_id);
    $stmt->execute();
    $result = $stmt->get_result();

    if ($row = $result->fetch_assoc()) {

        echo json_encode([
            "success" => true,
            "data" => [
                "question_id" => (int)$row['question_id'],
                "question" => $row['question'],
                "option_a" => $row['option_a'],
                "option_b" => $row['option_b'],
                "option_c" => $row['option_c'],
                "option_d" => $row['option_d'],
                "question_image" => $row['question_image'],
                "explanation" => $row['explanation'],
                
                // ? Added correct answer
                "correct_option" => $row['correct_option']
            ]
        ]);

    } else {
        echo json_encode([
            "success" => false,
            "message" => "Question not found"
        ]);
    }

} catch (Exception $e) {
    echo json_encode([
        "success" => false,
        "message" => "Server Error"
    ]);
}

// Cleanup
$stmt->close();
$conn->close();
?>