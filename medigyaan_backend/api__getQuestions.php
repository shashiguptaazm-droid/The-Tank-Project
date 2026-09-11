<?php
// Prevent any accidental whitespace/warnings from ruining the JSON output
ob_start();
header('Content-Type: application/json');

// Improved Error Handling for Production
set_error_handler(function($errno, $errstr) {
    if (!(error_reporting() & $errno)) return;
    ob_clean(); // Clear buffer before sending error JSON
    echo json_encode(["success" => false, "error" => "PHP Error: $errstr"]); 
    exit;
});

require 'config.php'; 

// Use type casting and trimming for clean inputs
$subject = isset($_GET['subject']) ? trim($_GET['subject']) : 'BCBR';
$topic = (isset($_GET['topic']) && !empty($_GET['topic'])) ? trim($_GET['topic']) : null;
$question_id = isset($_GET['question_id']) ? intval($_GET['question_id']) : null;
$user_id = isset($_GET['user_id']) ? intval($_GET['user_id']) : 0;

try {
    // --- STEP 1: Fetch all IDs for the specific Subject AND Topic ---
    // This is critical so the "Question X of Y" index is correct
    $id_query = "SELECT question_id FROM questions WHERE subject = ?";
    if ($topic) {
        $id_query .= " AND topic = ?";
    }
    $id_query .= " ORDER BY question_id ASC";

    $id_stmt = $conn->prepare($id_query);
    if ($topic) {
        $id_stmt->bind_param("ss", $subject, $topic);
    } else {
        $id_stmt->bind_param("s", $subject);
    }
    
    $id_stmt->execute();
    $id_result = $id_stmt->get_result();
    
    $all_ids = [];
    while ($row = $id_result->fetch_assoc()) {
        $all_ids[] = intval($row['question_id']);
    }
    $id_stmt->close();

    // --- STEP 1.5: Fetch answered IDs for this user in this Subject AND Topic ---
    $answered_ids = [];
    if ($user_id > 0 && !empty($all_ids)) {
        $ans_query = "SELECT up.question_id FROM user_progress up
                      JOIN questions q ON up.question_id = q.question_id
                      WHERE up.user_id = ? AND q.subject = ?";
        if ($topic) {
            $ans_query .= " AND q.topic = ?";
        }
        $ans_stmt = $conn->prepare($ans_query);
        if ($topic) {
            $ans_stmt->bind_param("iss", $user_id, $subject, $topic);
        } else {
            $ans_stmt->bind_param("is", $user_id, $subject);
        }
        $ans_stmt->execute();
        $ans_result = $ans_stmt->get_result();
        while ($row = $ans_result->fetch_assoc()) {
            $answered_ids[] = intval($row['question_id']);
        }
        $ans_stmt->close();
    }

    // No user goes empty handed: if a real topic has zero questions, ask the
    // AI module to generate a starter set, then re-run the id query.
    if (empty($all_ids) && $topic !== null && $topic !== '' && $subject !== 'BCBR') {
        require_once __DIR__ . '/generate_questions_ai.php';
        try {
            generateQuestionsForTopic($conn, $subject, $topic, 5);
            $id_stmt = $conn->prepare("SELECT question_id FROM questions WHERE subject = ? AND topic = ? ORDER BY question_id ASC");
            $id_stmt->bind_param("ss", $subject, $topic);
            $id_stmt->execute();
            $id_result = $id_stmt->get_result();
            $all_ids = [];
            while ($row = $id_result->fetch_assoc()) {
                $all_ids[] = intval($row['question_id']);
            }
            $id_stmt->close();
        } catch (Exception $genErr) {
            // Generation failed; fall through so the caller still sees the error below.
        }
    }

    if (empty($all_ids)) {
        throw new Exception("No questions found for this topic.");
    }

    // --- STEP 2: Logic for which question to show ---
    // If a specific ID is requested (Next/Prev), use it. 
    // Otherwise, find the first unanswered question in this specific list.
    if (!$question_id) {
        $find_stmt = $conn->prepare("
            SELECT q.question_id 
            FROM questions q 
            LEFT JOIN user_progress up ON q.question_id = up.question_id AND up.user_id = ? 
            WHERE q.subject = ? " . ($topic ? "AND q.topic = ?" : "") . " 
            AND up.user_answer IS NULL 
            ORDER BY q.question_id ASC LIMIT 1
        ");

        if ($topic) {
            $find_stmt->bind_param("iss", $user_id, $subject, $topic);
        } else {
            $find_stmt->bind_param("is", $user_id, $subject);
        }

        $find_stmt->execute();
        $find_result = $find_stmt->get_result();
        $found = $find_result->fetch_assoc();
        
        // If all are answered, go to the first ID in the list; otherwise, use the found unanswered ID
        $question_id = ($found) ? intval($found['question_id']) : $all_ids[0];
        $find_stmt->close();
    }

    // --- STEP 3: Fetch Question + User Progress ---
    $stmt = $conn->prepare("
        SELECT q.question_id, q.question, q.option_a, q.option_b, q.option_c, q.option_d, 
               q.correct_option, q.explanation, q.question_image,
               up.user_answer
        FROM questions q
        LEFT JOIN user_progress up ON q.question_id = up.question_id AND up.user_id = ?
        WHERE q.question_id = ?
    ");
    
    $stmt->bind_param("ii", $user_id, $question_id);
    $stmt->execute();
    $result = $stmt->get_result();
    $data = $result->fetch_assoc();
    $stmt->close();

    if (!$data) {
        throw new Exception("Question data not found.");
    }

    // Determine current index based on the filtered list of IDs
    $current_index = array_search(intval($question_id), $all_ids);

    // --- STEP 4: Final JSON Output ---
    ob_end_clean(); 
    
    echo json_encode([
        "success" => true,
        "all_question_ids" => $all_ids,
        "answered_ids" => $answered_ids,
        "current_index" => $current_index !== false ? $current_index : 0,
        "data" => [
            "question_id"    => intval($data['question_id']),
            "question"       => $data['question'],
            "question_image" => $data['question_image'],
            "option_a"       => $data['option_a'],
            "option_b"       => $data['option_b'],
            "option_c"       => $data['option_c'],
            "option_d"       => $data['option_d'],
            "answered"       => ($data['user_answer'] !== null),
            "user_answer"    => $data['user_answer'],
            "correct_answer" => $data['correct_option'],
            "explanation"    => $data['explanation']
        ]
    ]);

} catch (Exception $e) {
    ob_end_clean();
    echo json_encode(["success" => false, "error" => $e->getMessage()]);
}

if (isset($conn)) {
    $conn->close();
}
exit;