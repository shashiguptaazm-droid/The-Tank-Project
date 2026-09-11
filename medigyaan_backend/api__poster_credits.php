<?php
declare(strict_types=1);
/**
 * poster_credits.php — per-user poster generation quota.
 *
 * Actions:
 *   GET/POST ?action=check&user_id=N   -> {success, limit, used, remaining}
 *   POST    ?action=consume            -> atomically consumes 1 credit if remaining > 0
 *   POST    ?action=add&user_id=N&amount=M  -> admin top-up (credits purchase)
 *
 * Response JSON: { "success": bool, "limit": int, "used": int, "remaining": int,
 *                  "message": string, "error": string? }
 */

header('Content-Type: application/json');

// config.php must be required at top level so $conn lands in the global scope.
require_once __DIR__ . '/config.php';

function poster_db(): ?mysqli
{
    if (isset($GLOBALS['conn']) && $GLOBALS['conn'] instanceof mysqli && !$GLOBALS['conn']->connect_error) {
        return $GLOBALS['conn'];
    }
    return null;
}

function poster_exec(mysqli $conn, string $sql, string $types = '', array $params = []): bool
{
    $stmt = $conn->prepare($sql);
    if (!$stmt) {
        return false;
    }
    if ($types !== '' && $params) {
        $refs = [];
        foreach ($params as $index => $value) {
            $refs[$index] = $params[$index];
        }
        $bind = [$types];
        foreach ($refs as $index => $value) {
            $bind[] = &$refs[$index];
        }
        call_user_func_array([$stmt, 'bind_param'], $bind);
    }
    $ok = $stmt->execute();
    $stmt->close();
    return $ok;
}

function poster_query_one(mysqli $conn, string $sql, string $types = '', array $params = []): ?array
{
    $stmt = $conn->prepare($sql);
    if (!$stmt) {
        return null;
    }
    if ($types !== '' && $params) {
        $refs = [];
        foreach ($params as $index => $value) {
            $refs[$index] = $params[$index];
        }
        $bind = [$types];
        foreach ($refs as $index => $value) {
            $bind[] = &$refs[$index];
        }
        call_user_func_array([$stmt, 'bind_param'], $bind);
    }
    $stmt->execute();
    $result = $stmt->get_result();
    $row = $result ? $result->fetch_assoc() : null;
    $stmt->close();
    return $row ?: null;
}

function json_out(array $payload): void
{
    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

$conn = poster_db();
if ($conn === null) {
    json_out(['success' => false, 'error' => 'db_unavailable']);
}

poster_exec($conn, <<<SQL
CREATE TABLE IF NOT EXISTS poster_credits (
  user_id INT NOT NULL,
  used INT NOT NULL DEFAULT 0,
  credit_limit INT NOT NULL DEFAULT 5,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
SQL);

$action = strval($_GET['action'] ?? $_POST['action'] ?? 'check');
$userId = intval($_GET['user_id'] ?? $_POST['user_id'] ?? 0);

if ($userId <= 0) {
    json_out(['success' => false, 'error' => 'invalid_user']);
}

switch ($action) {
    case 'check': {
        $row = poster_query_one($conn, 'SELECT used, credit_limit FROM poster_credits WHERE user_id = ?', 'i', [$userId]);
        $used = (int)($row['used'] ?? 0);
        $limit = (int)($row['credit_limit'] ?? 5);
        json_out([
            'success' => true,
            'limit' => $limit,
            'used' => $used,
            'remaining' => max(0, $limit - $used),
            'message' => 'quota'
        ]);
    }

    case 'consume': {
        // Atomic: insert-if-missing then increment only when under the limit.
        poster_exec($conn, 'INSERT IGNORE INTO poster_credits (user_id, used, credit_limit) VALUES (?, 0, 5)', 'i', [$userId]);
        $row = poster_query_one($conn, 'SELECT used, credit_limit FROM poster_credits WHERE user_id = ?', 'i', [$userId]);
        $used = (int)($row['used'] ?? 0);
        $limit = (int)($row['credit_limit'] ?? 5);
        if ($used >= $limit) {
            json_out([
                'success' => false,
                'error' => 'limit_reached',
                'limit' => $limit,
                'used' => $used,
                'remaining' => 0,
                'message' => 'Free poster limit reached. Purchase credits to generate more posters.'
            ]);
        }
        poster_exec($conn, 'UPDATE poster_credits SET used = used + 1 WHERE user_id = ? AND used < credit_limit', 'i', [$userId]);
        $row2 = poster_query_one($conn, 'SELECT used, credit_limit FROM poster_credits WHERE user_id = ?', 'i', [$userId]);
        $used2 = (int)($row2['used'] ?? 0);
        $limit2 = (int)($row2['credit_limit'] ?? 5);
        json_out([
            'success' => true,
            'limit' => $limit2,
            'used' => $used2,
            'remaining' => max(0, $limit2 - $used2),
            'message' => 'consumed'
        ]);
    }

    case 'add': {
        // Admin top-up (credits purchase): amount can be negative to revoke.
        $amount = intval($_POST['amount'] ?? 0);
        poster_exec($conn, 'INSERT IGNORE INTO poster_credits (user_id, used, credit_limit) VALUES (?, 0, 5)', 'i', [$userId]);
        poster_exec($conn, 'UPDATE poster_credits SET credit_limit = credit_limit + ? WHERE user_id = ?', 'ii', [$amount, $userId]);
        $row = poster_query_one($conn, 'SELECT used, credit_limit FROM poster_credits WHERE user_id = ?', 'i', [$userId]);
        json_out([
            'success' => true,
            'limit' => (int)($row['credit_limit'] ?? 5),
            'used' => (int)($row['used'] ?? 0),
            'remaining' => max(0, ((int)($row['credit_limit'] ?? 5)) - ((int)($row['used'] ?? 0))),
            'message' => 'credited'
        ]);
    }

    default:
        json_out(['success' => false, 'error' => 'unknown_action']);
}