<?php
require 'config.php';
$stmt = $conn->query("
  SELECT subject, topic, COUNT(*) AS count
  FROM questions GROUP BY subject, topic
");
echo json_encode($stmt->fetch_all(MYSQLI_ASSOC));
?>