package com.rankwarz.edulabsrtm

data class PosterSectionData(val heading: String, val body: String)

data class PosterAnalysisData(
    val title: String = "",
    val subtitle: String = "",
    val sections: List<PosterSectionData> = emptyList()
)

data class PosterGenState(
    val ownerTurn: Int = -1,
    val source: String = "",
    var phase: Int = 0,
    var note: String = "",
    var data: PosterAnalysisData? = null,
    var imageUrl: String? = null,
    var imageFile: java.io.File? = null,
    var error: String = ""
)

data class SavedPoster(
    val ownerTurn: Int,
    val file: String,
    val title: String = "",
    val sections: List<String> = emptyList()
)

data class AttachmentContext(
    val name: String,
    val kind: String,   // image | pdf | text
    val text: String
)

