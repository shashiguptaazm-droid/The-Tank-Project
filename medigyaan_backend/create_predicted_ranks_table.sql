CREATE TABLE IF NOT EXISTS user_predicted_ranks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    predicted_min_rank VARCHAR(20) NOT NULL,
    predicted_max_rank VARCHAR(20) NOT NULL,
    tier VARCHAR(50) DEFAULT '',
    confidence INT DEFAULT 0,
    timestamp BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user (user_id),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
