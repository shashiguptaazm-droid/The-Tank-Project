package com.rankwarz.edulabsrtm

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.rankwarz.edulabsrtm.utils.WorkspaceState

object ResearchSharedState {
    var workspaceState by mutableStateOf(WorkspaceState())
}
