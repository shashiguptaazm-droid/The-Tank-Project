<?php
/**
 * VPS File Upload API
 * Handles large file uploads with proper limits and error handling
 * 
 * Deploy this to your VPS at /api/upload.php
 * Configure nginx: client_max_body_size 200M;
 * Configure PHP: upload_max_filesize = 200M, post_max_size = 200M, max_execution_time = 300
 */

require_once __DIR__ . '/../config.php';

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: X-Filename, X-File-Size, X-User-Id, Content-Type');

// Handle preflight
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'error' => 'POST method required']);
    exit;
}

// Validate token
$token = $_GET['token'] ?? '';
$validTokens = [
    '00b0e86a671d6635ca9cbdfc98bc5ff4dc2e',  // Original token
    // Add more valid tokens here if needed
];

if (empty($token) || !in_array($token, $validTokens)) {
    http_response_code(401);
    echo json_encode(['success' => false, 'error' => 'Invalid or missing token']);
    exit;
}

// Get headers
$filename = $_SERVER['HTTP_X_FILENAME'] ?? 'unknown';
$fileSize = intval($_SERVER['HTTP_X_FILE_SIZE'] ?? 0);
$userId = intval($_SERVER['HTTP_X_USER_ID'] ?? 0);

// Validate file size (100MB limit)
$maxSize = 100 * 1024 * 1024; // 100MB
if ($fileSize > $maxSize) {
    http_response_code(413);
    echo json_encode(['success' => false, 'error' => 'File too large (max 100MB)']);
    exit;
}

// Create upload directory
$uploadDir = __DIR__ . '/../uploads/messenger/';
if (!is_dir($uploadDir)) {
    if (!mkdir($uploadDir, 0755, true)) {
        http_response_code(500);
        echo json_encode(['success' => false, 'error' => 'Failed to create upload directory']);
        exit;
    }
}

// Generate unique filename
$ext = pathinfo($filename, PATHINFO_EXTENSION);
$safeExt = in_array(strtolower($ext), ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png', 'gif', 'mp4', 'mp3', 'txt', 'zip', 'rar']) ? $ext : 'bin';
$uniqueName = uniqid('msg_', true) . '.' . $safeExt;
$filePath = $uploadDir . $uniqueName;

// Read raw input stream
$input = fopen('php://input', 'rb');
if (!$input) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'Failed to read input stream']);
    exit;
}

$output = fopen($filePath, 'wb');
if (!$output) {
    fclose($input);
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'Failed to open output file']);
    exit;
}

$bytesWritten = 0;
$bufferSize = 8192;
while (!feof($input)) {
    $chunk = fread($input, $bufferSize);
    if ($chunk === false || $chunk === '') break;
    $written = fwrite($output, $chunk);
    if ($written === false) break;
    $bytesWritten += $written;
}

fclose($input);
fclose($output);

// Verify file size matches expected
if ($bytesWritten !== $fileSize && $fileSize > 0) {
    unlink($filePath);
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'File size mismatch: expected ' . $fileSize . ', got ' . $bytesWritten]);
    exit;
}

// Generate URL for the uploaded file
$baseUrl = (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on' ? 'https' : 'http') . '://' . $_SERVER['HTTP_HOST'];
$fileUrl = $baseUrl . '/Neurons/uploads/messenger/' . $uniqueName;

// Save to database for tracking
try {
    $stmt = $pdo->prepare("
        INSERT INTO messenger_uploads 
        (user_id, original_filename, stored_filename, file_size, file_url, mime_type, created_at) 
        VALUES (?, ?, ?, ?, ?, ?, NOW())
    ");
    $mimeType = mime_content_type($filePath) ?: 'application/octet-stream';
    $stmt->execute([$userId, $filename, $uniqueName, $bytesWritten, $fileUrl, $mimeType]);
} catch (PDOException $e) {
    // Log but don't fail the upload
    error_log("Failed to log upload: " . $e->getMessage());
}

// Return success
echo json_encode([
    'success' => true,
    'url' => $fileUrl,
    'file_url' => $fileUrl,
    'download_url' => $fileUrl,
    'filename' => $uniqueName,
    'size' => $bytesWritten,
    'mime_type' => $mimeType
]);
?>