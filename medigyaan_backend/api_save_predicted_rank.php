<?php
require_once 'config.php';

header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'error' => 'POST method required']);
    exit;
}

$user_id = isset($_POST['user_id']) ? intval($_POST['user_id']) : 0;
$min_rank = isset($_POST['predicted_min_rank']) ? trim($_POST['predicted_min_rank']) : '';
$max_rank = isset($_POST['predicted_max_rank']) ? trim($_POST['predicted_max_rank']) : '';
$tier = isset($_POST['tier']) ? trim($_POST['tier']) : '';
$confidence = isset($_POST['confidence']) ? intval($_POST['confidence']) : 0;
$timestamp = isset($_POST['timestamp']) ? intval($_POST['timestamp']) : 0;

if ($user_id <= 0 || empty($min_rank) || empty($max_rank)) {
    echo json_encode(['success' => false, 'error' => 'Invalid parameters']);
    exit;
}

try {
    $stmt = $pdo->prepare("
        INSERT INTO user_predicted_ranks 
        (user_id, predicted_min_rank, predicted_max_rank, tier, confidence, timestamp) 
        VALUES (?, ?, ?, ?, ?, ?)
        ON DUPLICATE KEY UPDATE 
        predicted_min_rank = VALUES(predicted_min_rank),
        predicted_max_rank = VALUES(predicted_max_rank),
        tier = VALUES(tier),
        confidence = VALUES(confidence),
        timestamp = VALUES(timestamp)
    ");
    
    $result = $stmt->execute([
        $user_id,
        $min_rank,
        $max_rank,
        $tier,
        $confidence,
        $timestamp
    ]);
    
    if ($result) {
        echo json_encode(['success' => true, 'message' => 'Predicted rank saved']);
    } else {
        echo json_encode(['success' => false, 'error' => 'Failed to save']);
    }
} catch (PDOException $e) {
    echo json_encode(['success' => false, 'error' => 'Database error: ' . $e->getMessage()]);
}
?>
