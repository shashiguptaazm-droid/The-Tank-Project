import Foundation

/// A study topic/subject as returned by `get_topics.php` and `api/topicsearch.php`.
struct Topic: Decodable, Identifiable, Hashable {
    let id: Int
    let name: String
    let description: String
    let subject: String
    let iconName: String
    let colorHex: String
    let questionCount: Int
    let isLocked: Bool

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        id = container.flexInt("topic_id", "id")
        name = container.flexString("topic_name", "name", "title")
        description = container.flexString("description", "desc", "summary")
        subject = container.flexString("subject", "category")
        iconName = container.flexString("icon", "icon_name")
        colorHex = container.flexString("color", "color_hex")
        questionCount = container.flexInt("question_count", "questions", "count", "total_questions")
        isLocked = container.flexBool("locked", "is_locked", "premium")
    }

    init(
        id: Int,
        name: String,
        description: String = "",
        subject: String = "",
        iconName: String = "",
        colorHex: String = "",
        questionCount: Int = 0,
        isLocked: Bool = false
    ) {
        self.id = id
        self.name = name
        self.description = description
        self.subject = subject
        self.iconName = iconName
        self.colorHex = colorHex
        self.questionCount = questionCount
        self.isLocked = isLocked
    }
}

/// A top-level exam/subject grouping used by the topic picker.
struct Subject: Decodable, Identifiable, Hashable {
    let id: Int
    let name: String
    let iconName: String
    let topicCount: Int

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        id = container.flexInt("subject_id", "id")
        name = container.flexString("subject", "subject_name", "name")
        iconName = container.flexString("icon", "icon_name")
        topicCount = container.flexInt("topic_count", "count", "topics")
    }

    init(id: Int, name: String, iconName: String = "", topicCount: Int = 0) {
        self.id = id
        self.name = name
        self.iconName = iconName
        self.topicCount = topicCount
    }
}
