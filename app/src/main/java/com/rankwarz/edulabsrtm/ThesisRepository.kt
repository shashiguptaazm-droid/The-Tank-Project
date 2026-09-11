package com.rankwarz.edulabsrtm

import android.content.Context
import android.net.Uri
import com.rankwarz.edulabsrtm.model.AnalysisEvent
import com.rankwarz.edulabsrtm.model.PageInsight
import kotlinx.coroutines.flow.Flow

interface ThesisRepository {

    fun analyzeThesis(
        context: Context,
        thesisId: Int,
        pdfUri: Uri,
        provider: String,
        maxAttempts: Int = 3
    ): Flow<AnalysisEvent>

    suspend fun saveToFirebase(
        thesisId: Int,
        provider: String,
        pages: List<PageInsight>
    )

    suspend fun saveToMySql(
        thesisId: Int,
        provider: String,
        pages: List<PageInsight>
    )
}
