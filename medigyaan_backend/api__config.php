<?php
// Database connection credentials
$servername = "localhost";
$username = "eqbbvart_Shashi";
$password = "MeriMaa007";
$database = "eqbbvart_NEURONS";
$dbname = "eqbbvart_NEURONS";
$user = "eqbbvart_Shashi";
$host = "localhost";

// Establish a database connection
$conn = new mysqli($servername, $username, $password, $database);

// Check if the connection was successful
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}
?>
