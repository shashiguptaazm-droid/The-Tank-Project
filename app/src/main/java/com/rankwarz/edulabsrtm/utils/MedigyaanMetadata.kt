package com.rankwarz.edulabsrtm.utils

object MedigyaanMetadata {

    val SUBJECT_ICONS = mapOf(
        "NEET PG" to "🩺",
        "NEET UG" to "🧠",
        "Law" to "⚖️",
        "Commerce" to "💼",
        "UPSC" to "🏛️",
        "CAT" to "📈",
        "Software" to "💻"
    )

    val TOPIC_ICONS = mapOf(
        // NEET PG
        "Pathology" to "🔬",
        "Microbiology" to "🧫",
        "Anatomy" to "💀",
        "Physiology" to "🫀",
        "Biochemistry" to "🧪",
        "Medicine" to "💊",
        "Pharmacology" to "💉",
        "Surgery" to "🔪",
        "Ophthalmology" to "👁️",
        "Otolaryngology" to "👂",
        "Pediatrics" to "👶",
        "Dermatology" to "🧴",
        "Obstetrics" to "🤰",
        "Gynaecology" to "🚺",
        "Psychiatry" to "🗣️",
        "Radiology" to "☢️",
        "Anaesthesia" to "💤",
        "Orthopaedics" to "🦴",
        "Forensic medicine" to "🔍",
        "Psm" to "🏘️",
        "Image Based Questions" to "🖼️",
        "Uncategorized NEET Questions" to "❓",
        
        // NEET UG
        "Biology" to "🌿",
        "Physics" to "⚡",
        "Chemistry" to "🧪",
        
        // Others
        "General medicine" to "🏥",
        "Ent" to "👃",
        "Orthopedics" to "🦿",
        "Forensic Medicine" to "🔍",
        "Social And Preventive Medicine" to "🏘️",
        "Gcs score" to "🧠",
        "Abg analysis" to "🩸",
        "Neonatology" to "👶",
        "Hematology" to "🩸",
        "Genetics" to "🧬",
        "Infectious diseases" to "🦠"
    )

    fun getIconForSubject(subject: String): String = SUBJECT_ICONS[subject] ?: "📚"

    fun getIconForTopic(topic: String): String = TOPIC_ICONS.entries.firstOrNull { 
        topic.contains(it.key, ignoreCase = true) 
    }?.value ?: "📝"

    /** Returns the text with an icon prepended if a match is found. */
    fun iconify(text: String): String {
        val topicIcon = TOPIC_ICONS.entries.firstOrNull { 
            text.equals(it.key, ignoreCase = true) || text.startsWith("${it.key}:")
        }?.value
        if (topicIcon != null) return "$topicIcon $text"
        
        val subjectIcon = SUBJECT_ICONS.entries.firstOrNull { 
            text.equals(it.key, ignoreCase = true)
        }?.value
        if (subjectIcon != null) return "$subjectIcon $text"
        
        return text
    }
}
