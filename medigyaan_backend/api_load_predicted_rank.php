<?php
require_once 'config.php';

header('Content-Type: application/json');

$user_id = isset($_GET['user_id']) ? intval($_GET['user_id']) : 0;

if ($user_id <= 0) {
    echo json_encode(['success' => false, 'error' => 'Invalid user_id']);
    exit;
}

try {
    $stmt = $pdo->prepare("
        SELECT predicted_min_rank, predicted_max_rank, tier, confidence, timestamp 
        FROM user_predicted_ranks 
        WHERE user_id = ? 
        ORDER BY updated_at DESC 
        LIMIT 1
    ");
    $stmt->execute([$user_id]);
    $row = $stmt->fetch(PDO::FETCH_ASSOC);
    
    if ($row) {
        echo json_encode([
            'success' => true,
            'predicted_min_rank' => $row['predicted_min_rank'],
            'predicted_max_rank' => $row['predicted_max_rank'],
            'tier' => $row['tier'],
            'confidence' => intval($row['confidence']),
            'timestamp' => intval($row['timestamp'])
        ]);
    } else {
        echo json_encode(['success' => false, 'error' => 'No predicted rank found']);
    }
} catch (PDOException $e) {
    echo json_encode(['success' => false, 'error' => 'Database error: ' . $e->getMessage()]);
}
?>
