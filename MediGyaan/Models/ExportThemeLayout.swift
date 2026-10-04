import SwiftUI

/// Export theme model matching Android's `ExportThemeSelectionActivity.kt` and `ThemeLayoutBackend.kt`.
public struct ExportThemeLayout: Identifiable, Hashable {
    public let id: String
    public let label: String
    public let family: String
    public let cover: String
    public let page: String
    public let table: String
    public let chart: String
    public let accentHex: String
    public let softHex: String
    public let fontScheme: String

    public init(
        id: String,
        label: String,
        family: String,
        cover: String,
        page: String,
        table: String,
        chart: String,
        accentHex: String = "#1D4ED8",
        softHex: String = "#EFF6FF",
        fontScheme: String = "Serif"
    ) {
        self.id = id
        self.label = label
        self.family = family
        self.cover = cover
        self.page = page
        self.table = table
        self.chart = chart
        self.accentHex = accentHex
        self.softHex = softHex
        self.fontScheme = fontScheme
    }
}

/// Central repository of standard and server-synced export layouts.
public enum ExportThemeRepository {

    public static let standardLayouts: [ExportThemeLayout] = [
        ExportThemeLayout(id: "FORMAL", label: "Formal Thesis", family: "Academic", cover: "Centered university title", page: "Double academic border", table: "Full grid tables", chart: "Academic charts", accentHex: "#1E3A8A", softHex: "#EFF6FF", fontScheme: "Times New Roman"),
        ExportThemeLayout(id: "JOURNAL", label: "Research Journal", family: "Journal", cover: "Manuscript opening", page: "Thin journal rules", table: "Minimal tables", chart: "Clean line charts", accentHex: "#0F766E", softHex: "#F0FDFA", fontScheme: "Georgia"),
        ExportThemeLayout(id: "CLINICAL", label: "Clinical Report", family: "Clinical", cover: "Official medical header", page: "Clinical left rail", table: "Boxed findings", chart: "Muted charts", accentHex: "#0369A1", softHex: "#F0F9FF", fontScheme: "San Francisco"),
        ExportThemeLayout(id: "BINDER", label: "Official Binder", family: "Academic", cover: "Authority cover band", page: "Binder spine frame", table: "Registrar grid", chart: "Formal evidence", accentHex: "#374151", softHex: "#F9FAFB", fontScheme: "Garamond"),
        ExportThemeLayout(id: "DASHBOARD", label: "Data Dashboard", family: "Analytics", cover: "Control header", page: "Metric side rail", table: "Dashboard blocks", chart: "Bold results", accentHex: "#7C3AED", softHex: "#F5F3FF", fontScheme: "Helvetica Neue"),
        ExportThemeLayout(id: "EDITORIAL", label: "Editorial Folio", family: "Journal", cover: "Magazine-style thesis opener", page: "Asymmetric folio margins", table: "Light manuscript tables", chart: "Editorial line charts", accentHex: "#BE185D", softHex: "#FDF2F8", fontScheme: "Palatino"),
        ExportThemeLayout(id: "ATLAS", label: "Atlas Plate", family: "Clinical", cover: "Plate catalogue identity", page: "Topographic plate frame", table: "Specimen data panels", chart: "Plate comparison charts", accentHex: "#B45309", softHex: "#FFFBEB", fontScheme: "Baskerville"),
        ExportThemeLayout(id: "MINIMAL", label: "Minimal Journal", family: "Minimal", cover: "Quiet manuscript", page: "Whitespace system", table: "Sparse rules", chart: "Mono charts", accentHex: "#18181B", softHex: "#FAFAFA", fontScheme: "Courier"),
        ExportThemeLayout(id: "GOLD", label: "Gold Premium", family: "Premium", cover: "Gold foil cover", page: "Golden ratio borders", table: "Gold-accent tables", chart: "Luxury gold charts", accentHex: "#D97706", softHex: "#FEF3C7", fontScheme: "Didot")
    ]

    public static let families: [String] = ["All", "Academic", "Journal", "Clinical", "Analytics", "Minimal", "Premium"]

    public static func layoutsForFamily(_ family: String) -> [ExportThemeLayout] {
        if family == "All" { return standardLayouts }
        return standardLayouts.filter { $0.family.caseInsensitiveCompare(family) == .orderedSame }
    }
}
