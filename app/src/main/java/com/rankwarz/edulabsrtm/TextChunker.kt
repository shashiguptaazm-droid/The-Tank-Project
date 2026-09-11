package com.rankwarz.edulabsrtm.utils

object TextChunker {
    fun chunkText(text: String, chunkSize: Int): List<String> {
        return text.chunked(chunkSize)
    }
}