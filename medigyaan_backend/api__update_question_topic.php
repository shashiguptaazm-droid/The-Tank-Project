<?php
/**
 * update_question_topic.php
 * AI-chat data-quality helper: assigns a topic (and optionally a cleaner subject)
 * to a question row, but ONLY when the row currently has no topic.
 * POST: question_id (int), topic (string), subject (optional string)
 */
header("Content-Type: application/json; charset=utf-8");
require_once "config.php";

$response = ["success" => false];

try {
    $question_id = isset($_POST['question_id']) ? intval($_POST['question_id']) : 0;
    $topic = isset($_POST['topic']) ? trim($_POST['topic']) : '';
    $subject = isset($_POST['subject']) ? trim($_POST['subject']) : '';

    if ($question_id <= 0) {
        echo json_encode(["success" => false, "message" => "Invalid question_id"]);
        exit;
    }
    if (strlen($topic) < 2 || strlen($topic) > 120) {
        echo json_encode(["success" => false, "message" => "Topic must be 2-120 characters"]);
        exit;
    }

    // Fill the topic when it is missing OR is a placeholder (e.g. "PG 2020", "Neet pg 2020")
    // so curated topics are never overwritten but junk ones get fixed.
    $stmt = $conn->prepare(
        "UPDATE questions
         SET topic = ?,
             subject = COALESCE(NULLIF(?, ''), subject)
         WHERE question_id = ?
           AND (topic IS NULL OR topic = ''
                OR topic REGEXP '[0-9]{4}|^PG|^Neet|^pg$')"
    );
    if (!$stmt) {
        throw new Exception("Prepare failed: " . $conn->error);
    }
    $stmt->bind_param("ssi", $topic, $subject, $question_id);
    $stmt->execute();

    if ($stmt->affected_rows > 0) {
        $response = ["success" => true, "message" => "Topic assigned", "question_id" => $question_id, "topic" => $topic];
    } else {
        // Either the row does not exist or it already has a topic.
        $response = ["success" => false, "message" => "No update: question missing or topic already set", "question_id" => $question_id];
    }
    $stmt->close();
} catch (Exception $e) {
    $response = ["success" => false, "message" => $e->getMessage()];
}

echo json_encode($response);
$conn->close();
?>
