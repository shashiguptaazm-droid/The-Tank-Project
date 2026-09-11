<?php
header("Content-Type: application/json");
require_once "config.php";

// ? LOG FILE
$logFile = "submit_log.txt";

function logMsg($msg) {
    global $logFile;
    file_put_contents($logFile, date("Y-m-d H:i:s") . " | " . $msg . "\n", FILE_APPEND);
}

logMsg("---- NEW REQUEST ----");
logMsg("POST: " . json_encode($_POST));

$response = ["success" => false];

try {

    // ? Validate input
    if (!isset($_POST['user_id'], $_POST['question_id'], $_POST['answer'])) {
        logMsg("ERROR: Missing params");
        echo json_encode(["success" => false, "message" => "Missing params"]);
        exit;
    }

    $user_id = intval($_POST['user_id']);
    $question_id = intval($_POST['question_id']);
    $answer = strtoupper(trim($_POST['answer']));

    logMsg("Parsed ? user_id=$user_id, question_id=$question_id, answer=$answer");

    // ? ONLY correct_option exists
    $stmt = $conn->prepare("
        SELECT correct_option, explanation 
        FROM questions 
        WHERE question_id = ?
    ");

    if (!$stmt) {
        logMsg("SQL ERROR: " . $conn->error);
        throw new Exception("Prepare failed");
    }

    $stmt->bind_param("i", $question_id);
    $stmt->execute();
    $res = $stmt->get_result();

    if ($res->num_rows == 0) {
        logMsg("ERROR: Question not found");
        echo json_encode(["success" => false, "message" => "Question not found"]);
        exit;
    }

    $row = $res->fetch_assoc();

    // ? DEBUG LOG (IMPORTANT)
    logMsg("DB ROW: " . json_encode($row));

    $correct = strtoupper(trim($row['correct_option']));
    $explanation = $row['explanation'] ?? "";

    logMsg("Correct Answer: $correct");

    if (empty($correct)) {
        logMsg("ERROR: correct_option is EMPTY");
        echo json_encode(["success" => false, "message" => "Correct answer missing"]);
        exit;
    }

    $is_correct = ($answer === $correct) ? 1 : 0;

    // ? Check existing
    $check = $conn->prepare("
        SELECT progress_id FROM user_progress 
        WHERE user_id = ? AND question_id = ?
        LIMIT 1
    ");

    $check->bind_param("ii", $user_id, $question_id);
    $check->execute();
    $checkRes = $check->get_result();

    if ($checkRes->num_rows > 0) {

        logMsg("Updating existing");

        $update = $conn->prepare("
            UPDATE user_progress 
            SET user_answer = ?, is_correct = ?, attempted_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND question_id = ?
        ");

        $update->bind_param("siii", $answer, $is_correct, $user_id, $question_id);
        $update->execute();

    } else {

        logMsg("Inserting new");

        $insert = $conn->prepare("
            INSERT INTO user_progress (user_id, question_id, user_answer, is_correct)
            VALUES (?, ?, ?, ?)
        ");

        $insert->bind_param("iisi", $user_id, $question_id, $answer, $is_correct);
        $insert->execute();
    }

    $response = [
        "success" => true,
        "correct_answer" => $correct,
        "is_correct" => $is_correct,
        "explanation" => $explanation
    ];

    logMsg("SUCCESS: " . json_encode($response));

    echo json_encode($response);

} catch (Exception $e) {

    logMsg("EXCEPTION: " . $e->getMessage());

    echo json_encode([
        "success" => false,
        "message" => $e->getMessage()
    ]);
}
?>