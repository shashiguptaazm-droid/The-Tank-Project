import SwiftUI

/// Data models for Conference Posters & Thesis Vision Analysis.
///
/// 1:1 port of Android `PosterTypes.kt`.
public struct PosterSectionData: Identifiable, Codable, Hashable {
    public var id: String { heading }
    public let heading: String
    public let body: String

    public init(heading: String, body: String) {
        self.heading = heading
        self.body = body
    }
}

public struct PosterAnalysisData: Codable, Hashable {
    public let title: String
    public let subtitle: String
    public let sections: [PosterSectionData]

    public init(title: String = "", subtitle: String = "", sections: [PosterSectionData] = []) {
        self.title = title
        self.subtitle = subtitle
        self.sections = sections
    }
}

public struct SavedPoster: Identifiable, Codable, Hashable {
    public var id: String { file }
    public let ownerTurn: Int
    public let file: String
    public let title: String
    public let sections: [String]

    public init(ownerTurn: Int, file: String, title: String = "", sections: [String] = []) {
        self.ownerTurn = ownerTurn
        self.file = file
        self.title = title
        self.sections = sections
    }
}

public struct AttachmentContext: Identifiable, Codable, Hashable {
    public var id: String { name }
    public let name: String
    public let kind: String // image | pdf | text
    public let text: String

    public init(name: String, kind: String, text: String) {
        self.name = name
        self.kind = kind
        self.text = text
    }
}
