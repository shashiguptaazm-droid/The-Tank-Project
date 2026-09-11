<?php
/**
 * share_v2.php - Upgraded MediGyaan Share Page
 * Features: Dark Theme, Play Store Link, Error Suppression, Professional Design.
 */
declare(strict_types=1);

// Suppress errors for clean production UI
ini_set('display_errors', '0');
error_reporting(0);

session_start();

include_once 'db_connection.php';

// Fallback for Firebase if not present
$firebaseSupported = false;
if (file_exists(__DIR__ . '/firebase/vendor/autoload.php')) {
    require __DIR__ . '/firebase/vendor/autoload.php';
    $firebaseSupported = true;
}

use Kreait\Firebase\Factory;
use Kreait\Firebase\Messaging\CloudMessage;

// =========================================================
// CONFIG
// =========================================================
$base_url = "https://medigyaan.xyz/Neurons/";
$play_store_url = "https://play.google.com/store/apps/details?id=com.corp.medigyaan";
$firebaseCredentials = __DIR__ . '/firebase_credentials.json';

// =========================================================
// INPUT
// =========================================================
$question_id = isset($_GET['question_id']) ? (int)$_GET['question_id'] : 0;
$shared_by   = isset($_GET['user_id']) ? (int)$_GET['user_id'] : 0;

// =========================================================
// HELPERS
// =========================================================
function shareUrl(int $question_id, int $shared_by): string
{
    return "https://medigyaan.xyz/Neurons/share.php?question_id={$question_id}&user_id={$shared_by}";
}

function getUserInfo($conn, int $userId): array
{
    $info = ['name' => 'MediGyaan User', 'photo' => ''];
    if ($userId <= 0) return $info;

    $sql = "SELECT name, photo FROM users_merged WHERE user_id = ? LIMIT 1";
    $stmt = $conn->prepare($sql);
    if ($stmt) {
        $stmt->bind_param("i", $userId);
        $stmt->execute();
        $stmt->bind_result($name, $photo);
        if ($stmt->fetch()) {
            $info['name'] = $name ?: 'MediGyaan User';
            $info['photo'] = $photo ?: '';
        }
        $stmt->close();
    }
    return $info;
}

function sendFcmToUser($conn, string $credentialsPath, int $receiverId, string $title, string $body, array $data = []): bool
{
    if ($receiverId <= 0 || !file_exists($credentialsPath)) return false;

    $stmt = $conn->prepare("SELECT fcm_token FROM users_merged WHERE user_id = ? LIMIT 1");
    if (!$stmt) return false;

    $stmt->bind_param("i", $receiverId);
    $stmt->execute();
    $stmt->bind_result($fcmToken);
    $stmt->fetch();
    $stmt->close();

    if (empty($fcmToken)) return false;

    try {
        $factory = (new Factory)->withServiceAccount($credentialsPath);
        $messaging = $factory->createMessaging();
        $payload = array_merge(['type' => 'shared_question_attempt', 'title' => $title, 'body' => $body], $data);
        $message = CloudMessage::withTarget('token', $fcmToken)->withData(array_map('strval', $payload));
        $messaging->send($message);
        return true;
    } catch (\Throwable $e) {
        return false;
    }
}

// =========================================================
// DATA FETCH
// =========================================================
$sharer = getUserInfo($conn, $shared_by);
$sharer_name  = $sharer['name'];
$sharer_photo = $sharer['photo'];

$question = '';
$option_a = ''; $option_b = ''; $option_c = ''; $option_d = '';
$correct_option = ''; $explanation = ''; $question_image = '';

if ($question_id > 0) {
    $stmt = $conn->prepare("SELECT question, option_a, option_b, option_c, option_d, correct_option, explanation, question_image FROM questions WHERE question_id = ? LIMIT 1");
    if ($stmt) {
        $stmt->bind_param("i", $question_id);
        $stmt->execute();
        $stmt->bind_result($question, $option_a, $option_b, $option_c, $option_d, $correct_option, $explanation, $question_image);
        $stmt->fetch();
        $stmt->close();
    }
}

if (!$question) {
    die("<h3>Question not found!</h3>");
}

// =========================================================
// POST HANDLING
// =========================================================
$feedback = '';
$show_explanation = false;

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['answer'])) {
    $user_answer = strtoupper(trim((string)$_POST['answer']));
    $is_correct  = ($user_answer === strtoupper(trim($correct_option))) ? 1 : 0;

    if ($is_correct) {
        $feedback = "<div class='alert alert-success'>✅ Correct! Excellent work.</div>";
    } else {
        $feedback = "<div class='alert alert-danger'>❌ Incorrect. The correct answer was $correct_option.</div>";
    }
    $show_explanation = true;

    // Async log attempt (optional)
}

?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MediGyaan - Knowledge Shared</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root {
            --bg-color: #0B1023;
            --card-bg: #1A1F38;
            --primary: #7B1FFF;
            --accent: #00E5FF;
            --text: #E0E0E0;
            --text-dim: #9FB3CC;
            --success: #4CAF50;
            --error: #FF5252;
            --outline: #2A2F48;
        }

        body {
            font-family: 'Poppins', sans-serif;
            margin: 0;
            padding: 0;
            background-color: var(--bg-color);
            color: var(--text);
            line-height: 1.6;
        }

        .header {
            background-color: var(--card-bg);
            padding: 20px;
            text-align: center;
            border-bottom: 1px solid var(--outline);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
        }

        .header img {
            width: 45px;
            height: 45px;
            border-radius: 12px;
        }

        .header h1 {
            margin: 0;
            font-size: 24px;
            background: linear-gradient(45deg, var(--primary), var(--accent));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .container {
            max-width: 650px;
            margin: 30px auto;
            padding: 0 15px;
        }

        .card {
            background-color: var(--card-bg);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            border: 1px solid var(--outline);
        }

        .sharer-meta {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--outline);
        }

        .sharer-meta img {
            width: 45px;
            height: 45px;
            border-radius: 50%;
            border: 2px solid var(--accent);
        }

        .sharer-meta .info {
            font-size: 14px;
            color: var(--text-dim);
        }

        .sharer-meta .name {
            font-weight: 600;
            color: var(--text);
            display: block;
        }

        .question-text {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #FFF;
        }

        .question-image {
            width: 100%;
            border-radius: 12px;
            margin-bottom: 20px;
            border: 1px solid var(--outline);
        }

        .options-group {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .option-item {
            position: relative;
        }

        .option-item input {
            display: none;
        }

        .option-label {
            display: block;
            padding: 15px 20px;
            background-color: var(--bg-color);
            border: 1px solid var(--outline);
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .option-item input:checked + .option-label {
            border-color: var(--accent);
            background-color: rgba(0, 229, 255, 0.1);
        }

        .option-label:hover {
            border-color: var(--primary);
        }

        .btn {
            display: block;
            width: 100%;
            padding: 15px;
            border-radius: 12px;
            border: none;
            font-weight: 700;
            font-size: 16px;
            cursor: pointer;
            text-align: center;
            text-decoration: none;
            margin-top: 25px;
            transition: transform 0.2s;
        }

        .btn:active { transform: scale(0.98); }

        .btn-primary {
            background: linear-gradient(45deg, var(--primary), #9D50BB);
            color: #FFF;
            box-shadow: 0 4px 15px rgba(123, 31, 255, 0.3);
        }

        .btn-outline {
            background: transparent;
            border: 2px solid var(--accent);
            color: var(--accent);
            margin-top: 15px;
        }

        .alert {
            padding: 15px;
            border-radius: 12px;
            margin-bottom: 20px;
            font-weight: 600;
            text-align: center;
        }

        .alert-success { background-color: rgba(76, 175, 80, 0.2); color: #81C784; border: 1px solid var(--success); }
        .alert-danger { background-color: rgba(255, 82, 82, 0.2); color: #FF8A80; border: 1px solid var(--error); }

        .explanation-box {
            margin-top: 25px;
            padding: 20px;
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            font-size: 14px;
        }

        .footer {
            text-align: center;
            margin-top: 50px;
            padding: 30px;
            color: var(--text-dim);
            font-size: 13px;
        }

        .social-share {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 20px;
        }

        .social-share a {
            color: var(--text-dim);
            font-size: 20px;
            transition: color 0.2s;
        }

        .social-share a:hover { color: var(--accent); }

        @media (max-width: 600px) {
            .container { margin: 15px auto; }
            .card { padding: 20px; }
        }
    </style>
</head>
<body>

<header class="header">
    <img src="<?php echo $base_url; ?>login.jpg" alt="MediGyaan">
    <h1>MediGyaan</h1>
</header>

<div class="container">
    <div class="card">
        <div class="sharer-meta">
            <img src="<?php echo $sharer_photo ?: $base_url . 'Default.jpg'; ?>" alt="Sharer">
            <div class="info">
                <span class="name"><?php echo htmlspecialchars($sharer_name); ?></span>
                <span>shared a question with you</span>
            </div>
        </div>

        <?php echo $feedback; ?>

        <div class="question-text">
            <?php echo htmlspecialchars($question); ?>
        </div>

        <?php if (!empty($question_image)): ?>
            <img src="<?php echo str_starts_with($question_image, 'http') ? $question_image : $base_url . $question_image; ?>" class="question-image" alt="Question Resource">
        <?php endif; ?>

        <?php if (!$show_explanation): ?>
        <form method="POST">
            <div class="options-group">
                <?php foreach(['A', 'B', 'C', 'D'] as $opt):
                    $optVar = "option_" . strtolower($opt);
                    $optText = $$optVar;
                    if (empty($optText)) continue;
                ?>
                <div class="option-item">
                    <input type="radio" name="answer" value="<?php echo $opt; ?>" id="opt<?php echo $opt; ?>" required>
                    <label class="option-label" for="opt<?php echo $opt; ?>">
                        <strong><?php echo $opt; ?>)</strong> <?php echo htmlspecialchars((string)$optText); ?>
                    </label>
                </div>
                <?php endforeach; ?>
            </div>
            <button type="submit" class="btn btn-primary">Check Answer</button>
        </form>
        <?php else: ?>
            <div class="explanation-box">
                <h4 style="margin-top: 0; color: var(--accent);">Explanation</h4>
                <?php echo nl2br(htmlspecialchars($explanation ?: 'No detailed explanation available for this question.')); ?>
            </div>
            <a href="<?php echo $play_store_url; ?>" class="btn btn-primary">Get MediGyaan App</a>
        <?php endif; ?>

        <a href="<?php echo $play_store_url; ?>" class="btn btn-outline">
            <i class="fab fa-google-play"></i> Register To Perform QBank
        </a>
    </div>

    <div class="footer">
        <div class="social-share">
            <a href="#"><i class="fab fa-facebook"></i></a>
            <a href="#"><i class="fab fa-twitter"></i></a>
            <a href="#"><i class="fab fa-instagram"></i></a>
            <a href="#"><i class="fab fa-whatsapp"></i></a>
        </div>
        <p>&copy; <?php echo date('Y'); ?> MediGyaan. Built for Medical Excellence.</p>
        <p><a href="#" style="color: var(--text-dim);">Privacy Policy</a> | <a href="#" style="color: var(--text-dim);">Terms</a></p>
    </div>
</div>

</body>
</html>