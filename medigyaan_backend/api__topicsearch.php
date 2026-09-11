<?php
header("Content-Type: application/json");
include "config.php"; // your DB connection

$keyword = isset($_GET['q']) ? trim($_GET['q']) : '';

if ($keyword == '') {
    echo json_encode(["success" => false, "message" => "Empty keyword"]);
    exit;
}

$stmt = $conn->prepare("
    SELECT DISTINCT subject, topic
    FROM questions
    WHERE subject LIKE ? OR topic LIKE ?
    ORDER BY subject ASC, topic ASC
    LIMIT 50
");

$search = "%$keyword%";
$stmt->bind_param("ss", $search, $search);
$stmt->execute();

$result = $stmt->get_result();

$data = [];

while ($row = $result->fetch_assoc()) {
    $data[] = [
        "subject" => $row['subject'],
        "topic" => $row['topic']
    ];
}

echo json_encode([
    "success" => true,
    "data" => $data
]);