package com.rankwarz.edulabsrtm

data class PostModel(
    val postId: Int,
    val ownerName: String,
    val ownerPhoto: String,
    val caption: String,
    val filePaths: List<String>,
    var likes: Int,      // Change 'val' to 'var'
    var isLiked: Boolean // Change 'val' to 'var'
)