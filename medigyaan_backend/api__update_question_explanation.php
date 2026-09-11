<?php
/**
 * update_question_explanation.php
 * AI-chat data-quality helper: replaces a question's explanation with a better,
 * brief one, but ONLY when the current explanation is missing or shorter than
 * 100 characters (so good explanations are never overwritten).
 * POST: question_id (int), explanation (string)
 */
header("Content-Type: application/json; charset=utf-8");
require_once "config.php";

$response = ["success" => false];

try {
    $question_id = isset($_POST['question_id']) ? intval($_POST['question_id']) : 0;
    $explanation = isset($_POST['explanation']) ? trim($_POST['explanation']) : '';

    if ($question_id <= 0) {
        echo json_encode(["success" => false, "message" => "Invalid question_id"]);
        exit;
    }
    if (strlen($explanation) < 20) {
        echo json_encode(["success" => false, "message" => "Explanation must be at least 20 characters"]);
        exit;
    }

    // Only replace when the stored explanation is missing or shorter than 100 chars.
    $stmt = $conn->prepare(
        "UPDATE questions
         SET explanation = ?
         WHERE question_id = ?
           AND (explanation IS NULL
                OR CHAR_LENGTH(TRIM(explanation)) < 100)"
    );
    if (!$stmt) {
        throw new Exception("Prepare failed: " . $conn->error);
    }
    $stmt->bind_param("si", $explanation, $question_id);
    $stmt->execute();

    if ($stmt->affected_rows > 0) {
        $response = ["success" => true, "message" => "Explanation updated", "question_id" => $question_id];
    } else {
        $response = ["success" => false, "message" => "No update: question missing or explanation already sufficient", "question_id" => $question_id];
    }
    $stmt->close();
} catch (Exception $e) {
    $response = ["success" => false, "message" => $e->getMessage()];
}

echo json_encode($response);
$conn->close();
?>
