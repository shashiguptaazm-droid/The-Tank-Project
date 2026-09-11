<?php
/**
 * search.php - PROFESSIONAL JSON API VERSION
 * Path: /Neurons/api/search.php
 */

// 1. Prevent any PHP errors/warnings from breaking the JSON format
error_reporting(0);
ini_set('display_errors', 0);

// 2. Identify the App via the Secure Header
$appSignature = $_SERVER['HTTP_X_APP_SIGNATURE'] ?? '';
$expectedSignature = "EduLabsRTM_Secure_v1_2026"; // Matches your Android Kotlin code

// 3. Force JSON header immediately
header('Content-Type: application/json; charset=utf-8');

// 4. Database Connection
// Ensure config.php defines $servername, $username, $password, $dbname
include_once 'config.php'; 

$conn = new mysqli($servername, $username, $password, $dbname);

// Set charset to utf8mb4 for medical symbols/special characters
$conn->set_charset("utf8mb4");

if ($conn->connect_error) {
    echo json_encode([
        "status" => "error", 
        "message" => "Connection failed: " . $conn->connect_error
    ]);
    exit;
}

// 5. Initialize Response Structure
$keyword = isset($_GET['keyword']) ? trim($_GET['keyword']) : "";

$response = [
    "status" => "success",
    "keyword" => $keyword,
    "results" => [
        "questions" => [],
        "users" => []
    ],
    "error" => ""
];

// 6. Security & Logic Check
if ($appSignature !== $expectedSignature) {
    // If someone hits this via browser without the header, you can either:
    // A) Block them (Professional API approach)
    // B) Show your "Bot Verification" HTML (Hybrid approach)
    
    http_response_code(403);
    echo json_encode(["status" => "error", "message" => "Unauthorized App Access"]);
    exit;
}

if (!empty($keyword) && strlen($keyword) >= 3) { // Matches Android's 3-char limit
    $searchTerm = "%" . $keyword . "%";

    // --- SEARCH QUESTIONS ---
    $stmt_q = $conn->prepare("SELECT question_id, question, subject, topic, explanation, question_image FROM questions WHERE question LIKE ? OR subject LIKE ? LIMIT 20");
    $stmt_q->bind_param("ss", $searchTerm, $searchTerm);
    $stmt_q->execute();
    $res_q = $stmt_q->get_result();
    while ($row = $res_q->fetch_assoc()) { 
        // Ensure image URLs are absolute if stored as relative paths
        if (!empty($row['question_image']) && !str_starts_with($row['question_image'], 'http')) {
            $row['question_image'] = "https://medigyaan.xyz/Neurons/uploads/" . $row['question_image'];
        }
        $response["results"]["questions"][] = $row; 
    }
    $stmt_q->close();

    // --- SEARCH USERS ---
    $stmt_u = $conn->prepare("SELECT user_id, name, photo FROM users_merged WHERE name LIKE ? LIMIT 15");
    $stmt_u->bind_param("s", $searchTerm);
    $stmt_u->execute();
    $res_u = $stmt_u->get_result();
    while ($row = $res_u->fetch_assoc()) { 
        $response["results"]["users"][] = $row; 
    }
    $stmt_u->close();

} else {
    $response["status"] = "error";
    $response["error"] = "Keyword too short";
}

// 7. Final Clean Output
// Clean the buffer to remove BOM characters or accidental 'echo's from config.php
if (ob_get_length()) ob_clean();

echo json_encode($response);
$conn->close();
exit;