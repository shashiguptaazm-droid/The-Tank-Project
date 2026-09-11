package com.rankwarz.edulabsrtm.model

data class ChatMessage(
    val senderId: Int,
    val text: String,
    val attachment: String,
    val sentAt: String,
    val isRead: Int = 0,
    val messageUuid: String = "" // Added UUID - Para 24
)

data class ChatUserItem(
    val id: Int,
    val name: String,
    val image: String,
    val isOnline: Boolean = false,
    val lastSeen: Long = 0
)
