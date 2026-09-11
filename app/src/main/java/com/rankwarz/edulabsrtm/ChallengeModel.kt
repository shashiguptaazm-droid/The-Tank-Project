package com.rankwarz.edulabsrtm

import android.net.Uri
import androidx.annotation.Keep
import com.rankwarz.edulabsrtm.model.PageInsight

@Keep // Prevents ProGuard from stripping these fields during release builds
data class ChallengeModel(
    var id: String = "",              // e.g., "lobby_489"
    val status: String = "waiting",   // waiting, started, or ended
    val createdAt: Long = 0,          // Timestamp for sorting
    val topicName: String = "",       // e.g., "Cardiology" or "General Medicine"
    val creatorId: String = "",       // The User ID who created the room
    val maxPlayers: Int = 2,          // Limit for the lobby
    val currentQuestionIndex: Int = 0 // Track progress of the game
)

data class ThesisUiState(
    val selectedPdfUri: Uri? = null,
    val selectedProvider: String = "gemini",
    val processing: Boolean = false,
    val status: String = "Select a PDF to begin",
    val progressCurrent: Int = 0,
    val progressTotal: Int = 0,
    val pages: List<PageInsight> = emptyList(),
    val canExport: Boolean = false,
    val lastError: String? = null
)