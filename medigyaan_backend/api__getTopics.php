<?php
// Prevent any accidental whitespace/warnings from corrupting the JSON output
ob_start();
header('Content-Type: application/json');

require_once "config.php"; 

// 1. Validate Input
$subject = isset($_GET['subject']) ? trim($_GET['subject']) : '';

if (empty($subject)) {
    ob_clean();
    echo json_encode([
        "success" => false, 
        "error" => "Subject is required",
        "data" => [] 
    ]);
    exit();
}

// 2. Query topics with question counts - Para 118 & King of Topic
// Optimized query to get count of questions per topic
$stmt = $conn->prepare("SELECT topic, COUNT(*) as count FROM questions WHERE subject = ? AND topic IS NOT NULL AND topic != '' GROUP BY topic ORDER BY topic ASC");
$stmt->bind_param("s", $subject);
$stmt->execute();
$result = $stmt->get_result();

$topics = [];
while ($row = $result->fetch_assoc()) {
    $topics[] = [
        "name" => $row['topic'],
        "count" => intval($row['count'])
    ];
}

// 3. Final Output
ob_clean(); // Clear buffer to ensure ONLY the JSON is sent
echo json_encode([
    "success" => true,
    "data" => $topics
]);

$stmt->close();
$conn->close();
?>