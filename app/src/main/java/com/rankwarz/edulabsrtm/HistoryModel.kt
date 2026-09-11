package com.rankwarz.edulabsrtm

data class HistoryModel(
    var historyId: String = "",
    var userId: Int = 0,
    var mode: String = "", // PRACTICE / CHALLENGE / FINAL_TEST / SINGLE_PLAYER
    var title: String = "",
    var topic: String = "",
    var score: Int = 0,
    var totalQuestions: Int = 0,
    var correctAnswers: Int = 0,
    var wrongAnswers: Int = 0,
    var percentage: Float = 0f,
    var challengeId: String = "",
    var reviewJson: String = "", // Detailed question-by-question data
    var timestamp: Long = System.currentTimeMillis()
)