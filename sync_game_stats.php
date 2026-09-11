<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=UTF-8');

require_once 'db.php'; // Must provide $pdo as a valid PDO instance

function respond(string $status, string $message, array $extra = []): void
{
    echo json_encode(array_merge([
        'status'  => $status,
        'message' => $message
    ], $extra));
    exit;
}

function boolFromPost($value): bool
{
    if (is_bool($value)) {
        return $value;
    }

    $value = strtolower(trim((string)$value));
    return in_array($value, ['1', 'true', 'yes', 'on'], true);
}

function rankFromExp(int $exp): string
{
    if ($exp >= 100000) return 'LEGEND';
    if ($exp >= 60000)  return 'GRANDMASTER';
    if ($exp >= 30000)  return 'MASTER';
    if ($exp >= 15000)  return 'SCHOLAR';
    if ($exp >= 7500)   return 'EXPERT';
    if ($exp >= 3500)   return 'WARRIOR';
    if ($exp >= 1500)   return 'SKILLED';
    if ($exp >= 500)    return 'ROOKIE';
    return 'ASPIRANT';
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    respond('error', 'Invalid request method');
}

if (!isset($pdo) || !($pdo instanceof PDO)) {
    respond('error', 'Database connection not available');
}

try {
    // Read inputs
    $userId      = filter_var($_POST['user_id'] ?? null, FILTER_VALIDATE_INT);
    $score       = filter_var($_POST['score'] ?? null, FILTER_VALIDATE_INT);
    $totalQue    = filter_var($_POST['total_questions'] ?? null, FILTER_VALIDATE_INT);
    $hp          = filter_var($_POST['hp'] ?? null, FILTER_VALIDATE_INT);
    $challengeId = filter_var($_POST['challenge_id'] ?? null, FILTER_VALIDATE_INT);
    $isWin       = boolFromPost($_POST['is_win'] ?? false);

    // Validate required fields
    if ($userId === false || $userId <= 0) {
        respond('error', 'Invalid or missing user_id');
    }

    if ($score === false || $score < 0) {
        respond('error', 'Invalid or missing score');
    }

    if ($totalQue === false || $totalQue <= 0) {
        respond('error', 'Invalid or missing total_questions');
    }

    if ($hp === false || $hp < 0) {
        respond('error', 'Invalid or missing hp');
    }

    // Determine type: PRACTICE vs CHALLENGE
    $isPractice = false;
    if ($challengeId === false || $challengeId <= 0) {
        $isPractice = true;
        $challengeId = 0;
    }

    $pdo->beginTransaction();

    // Lock user row for safe updates
    $stmt = $pdo->prepare("
        SELECT user_id, last_activity, streak, exp, wins, losses, level, rank_title
        FROM users_merged
        WHERE user_id = ?
        FOR UPDATE
    ");
    $stmt->execute([$userId]);
    $user = $stmt->fetch(PDO::FETCH_ASSOC);

    if (!$user) {
        throw new Exception('User not found');
    }

    $currentExp    = (int)($user['exp'] ?? 0);
    $currentStreak = (int)($user['streak'] ?? 0);

    // --- DAILY STREAK BONUS ---
    $dailyBonus = 0;
    $streakBonusApplied = false;

    if (!empty($user['last_activity'])) {
        $lastDate = new DateTimeImmutable((string)$user['last_activity']);
        $today    = new DateTimeImmutable('now');
        $daysDiff  = (int)$today->diff($lastDate)->days;

        // If last activity was yesterday, grant bonus
        if ($daysDiff === 1) {
            $dailyBonus = 50;
            $streakBonusApplied = true;
        }
    }

    // --- EXP CALCULATION ---
    if ($isPractice) {
        $totalExpGained = $score; // Direct XP sync from app practice calculation
        $baseExp        = $score;
        $survivalExp    = 0;
        $winExp         = 0;
        $multiplier     = 1.0;
    } else {
        $baseExp     = $score * 10;                 // correct answers reward
        $survivalExp = $hp * 5;                     // hp reward
        $winExp      = $isWin ? 100 : 20;           // result reward

        // Win streak multiplier: every 3 wins increases by 0.2
        $multiplier = 1.0 + (floor($currentStreak / 3) * 0.2);

        // Optional safety cap so multiplier does not grow forever
        if ($multiplier > 3.0) {
            $multiplier = 3.0;
        }

        $rawExpGained    = $baseExp + $survivalExp + $winExp + $dailyBonus;
        $totalExpGained  = (int)round($rawExpGained * $multiplier);
    }

    // --- NEW VALUES ---
    $newExp    = $currentExp + $totalExpGained;
    $newLevel  = (int)floor($newExp / 1000) + 1;
    $newRank   = rankFromExp($newExp);
    $newStreak = $isWin ? ($currentStreak + 1) : 0;

    $winInc  = $isWin ? 1 : 0;
    $lossInc = $isWin ? 0 : 1;

    // --- UPDATE USER TABLE ---
    $updateSql = "
        UPDATE users_merged
        SET
            exp = :exp,
            wins = wins + :winInc,
            losses = losses + :lossInc,
            streak = :streak,
            last_activity = NOW(),
            level = :level,
            rank_title = :rank_title
        WHERE user_id = :userId
    ";

    $updateStmt = $pdo->prepare($updateSql);
    $updateStmt->execute([
        ':exp'        => $newExp,
        ':winInc'     => $winInc,
        ':lossInc'    => $lossInc,
        ':streak'     => $newStreak,
        ':level'      => $newLevel,
        ':rank_title' => $newRank,
        ':userId'     => $userId
    ]);

    if ($updateStmt->rowCount() < 1) {
        throw new Exception('Failed to update user record');
    }

    // --- INSERT LOG ---
    $logSql = "
        INSERT INTO user_exp_logs (user_id, exp_gained, source, reference_id, created_at)
        VALUES (?, ?, ?, ?, NOW())
    ";
    $logStmt = $pdo->prepare($logSql);
    $logStmt->execute([
        $userId,
        $totalExpGained,
        $isPractice ? 'PRACTICE_MCQ' : ($isWin ? 'CHALLENGE_WIN' : 'CHALLENGE_LOSS'),
        $challengeId
    ]);

    $pdo->commit();

    respond('success', 'EXP updated successfully', [
        'earned' => [
            'base_exp'          => (int)$baseExp,
            'survival_exp'      => (int)$survivalExp,
            'win_exp'           => (int)$winExp,
            'daily_bonus'       => (int)$dailyBonus,
            'multiplier'        => $multiplier,
            'total_exp'         => $totalExpGained,
            'bonus_applied'     => $streakBonusApplied ? 'Daily Streak Active' : 'None'
        ],
        'player' => [
            'user_id'    => $userId,
            'exp'        => $newExp,
            'level'      => $newLevel,
            'rank_title' => $newRank,
            'wins'       => (int)$user['wins'] + $winInc,
            'losses'     => (int)$user['losses'] + $lossInc,
            'streak'     => $newStreak
        ]
    ]);

} catch (Throwable $e) {
    if ($pdo->inTransaction()) {
        $pdo->rollBack();
    }

    respond('error', $e->getMessage());
}