package com.rankwarz.edulabsrtm.utils

object ProjectContextManager {
    fun getProjectSummary(): String {
        return """
            [PROJECT_CONTEXT]
            App Name: MediGyaan
            Primary Tech: Kotlin, Jetpack Compose, MVVM, Firebase
            Key Modules:
            - AiChatActivity: 170+ Research/Coding Skills
            - ThesisAnalyzer: Full automated dissertation writer
            - MCQActivity: 280k question bank integration
            - Dashboard: Gamified medical learning
            - Research OS: AI-managed structured workspace
            
            Backend: PHP (Neurons API), MySQL, Tailscale VPS
        """.trimIndent()
    }
}
