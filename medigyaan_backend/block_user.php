<?php
/**
 * Block User API
 * Allows users to block other users from messaging them
 */

require_once 'config.php';

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, X-App-Signature');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'error' => 'POST method required']);
    exit;
}

// Validate app signature
$signature = $_SERVER['HTTP_X_APP_SIGNATURE'] ?? '';
if ($signature !== 'EduLabsRTM_Secure_v1_2026') {
    http_response_code(401);
    echo json_encode(['success' => false, 'error' => 'Invalid app signature']);
    exit;
}

$user_id = isset($_POST['user_id']) ? intval($_POST['user_id']) : 0;
$blocked_user_id = isset($_POST['blocked_user_id']) ? intval($_POST['blocked_user_id']) : 0;

if ($user_id <= 0 || $blocked_user_id <= 0) {
    echo json_encode(['success' => false, 'error' => 'Invalid user IDs']);
    exit;
}

if ($user_id === $blocked_user_id) {
    echo json_encode(['success' => false, 'error' => 'Cannot block yourself']);
    exit;
}

try {
    // Check if already blocked
    $stmt = $pdo->prepare("SELECT id FROM user_blocks WHERE blocker_id = ? AND blocked_id = ?");
    $stmt->execute([$user_id, $blocked_user_id]);
    if ($stmt->fetch()) {
        echo json_encode(['success' => false, 'error' => 'User already blocked']);
        exit;
    }

    // Insert block
    $stmt = $pdo->prepare("
        INSERT INTO user_blocks (blocker_id, blocked_id, created_at) 
        VALUES (?, ?, NOW())
    ");
    $stmt->execute([$user_id, $blocked_user_id]);

    // Remove any existing chat between them
    $stmt = $pdo->prepare("
        DELETE FROM user_chats 
        WHERE (user_id = ? AND target_user_id = ?) OR (user_id = ? AND target_user_id = ?)
    ");
    $stmt->execute([$user_id, $blocked_user_id, $blocked_user_id, $user_id]);

    echo json_encode([
        'success' => true,
        'message' => 'User blocked successfully'
    ]);

} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'Database error: ' . $e->getMessage()]);
}
?>