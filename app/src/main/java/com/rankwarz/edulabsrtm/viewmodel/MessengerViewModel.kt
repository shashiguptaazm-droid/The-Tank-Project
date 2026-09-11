package com.rankwarz.edulabsrtm.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.rankwarz.edulabsrtm.model.ChatMessage
import com.rankwarz.edulabsrtm.model.ChatUserItem
import com.rankwarz.edulabsrtm.repository.MessengerRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class MessengerViewModel(application: Application) : AndroidViewModel(application) {
    private val repository = MessengerRepository(application)

    private val _messages = MutableStateFlow<List<ChatMessage>>(emptyList())
    val messages: StateFlow<List<ChatMessage>> = _messages

    private val _config = MutableStateFlow<MessengerRepository.MessengerConfig?>(null)
    val config: StateFlow<MessengerRepository.MessengerConfig?> = _config

    fun loadConfig(userId: Int) {
        viewModelScope.launch {
            try {
                _config.value = repository.fetchConfig(userId)
            } catch (e: Exception) {
                // Log or handle
            }
        }
    }

    fun loadMessages(userId: Int, receiverId: Int) {
        viewModelScope.launch {
            try {
                _messages.value = repository.fetchMessages(userId, receiverId)
            } catch (e: Exception) {
                // Handle
            }
        }
    }
}
