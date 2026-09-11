<?php
header('Content-Type: application/json');
$out = [
    'dir' => __DIR__,
    'cfg_exists_dir' => file_exists(__DIR__ . '/config.php'),
    'cfg_exists_rel' => file_exists('config.php'),
];
if (isset($GLOBALS['conn'])) {
    $out['conn_set'] = get_class($GLOBALS['conn']);
    $out['conn_err'] = $GLOBALS['conn']->connect_error;
} else {
    $out['conn_set'] = 'no';
}
if (file_exists(__DIR__ . '/config.php')) {
    require_once __DIR__ . '/config.php';
    $out['after_require_conn'] = isset($GLOBALS['conn']) ? get_class($GLOBALS['conn']) : 'no';
}
echo json_encode($out);
