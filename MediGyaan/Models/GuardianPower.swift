import SwiftUI

/// Educational cognitive power categories during MCQ quiz sessions.
enum PowerCategory: String, CaseIterable, Codable {
    case elimination = "ELIMINATION"
    case textFormat = "TEXT_FORMAT"
    case timeScore = "TIME_SCORE"
    case safetyNet = "SAFETY_NET"
    case overlay = "OVERLAY"

    var displayName: String {
        switch self {
        case .elimination: return "Elimination"
        case .textFormat: return "Text Format"
        case .timeScore: return "Time & Score"
        case .safetyNet: return "Safety Net"
        case .overlay: return "Overlay"
        }
    }

    var iconEmoji: String {
        switch self {
        case .elimination: return "🎯"
        case .textFormat: return "📝"
        case .timeScore: return "⏱️"
        case .safetyNet: return "🛡️"
        case .overlay: return "🔍"
        }
    }

    var color: Color {
        switch self {
        case .elimination: return Color(hex: "#FF5252")
        case .textFormat: return Color(hex: "#E040FB")
        case .timeScore: return Color(hex: "#FFD700")
        case .safetyNet: return Color(hex: "#00E676")
        case .overlay: return Color(hex: "#00E5FF")
        }
    }
}

/// 3D configuration parameters matching Android's `Guardian3DConfig`.
struct Guardian3DConfig: Codable, Hashable {
    let modelGlbUrl: String?
    let backgroundImageUrl: String?
    let rimColorHex: UInt32
    let cameraDistance: Float
    let cameraHeight: Float
    let pedestalRuneColor: UInt32?

    init(
        modelGlbUrl: String? = nil,
        backgroundImageUrl: String? = nil,
        rimColorHex: UInt32 = 0x40E0D0,
        cameraDistance: Float = 3.4,
        cameraHeight: Float = 1.6,
        pedestalRuneColor: UInt32? = nil
    ) {
        self.modelGlbUrl = modelGlbUrl
        self.backgroundImageUrl = backgroundImageUrl
        self.rimColorHex = rimColorHex
        self.cameraDistance = cameraDistance
        self.cameraHeight = cameraHeight
        self.pedestalRuneColor = pedestalRuneColor
    }
}

/// A Guardian power definition mapped to an Animal Warrior / MBBS Champion.
struct GuardianPower: Identifiable, Codable, Hashable {
    var id: String { powerId }
    let powerId: String
    let powerName: String
    let powerCategory: PowerCategory
    let description: String
    let cooldownRounds: Int
    let chargesPerQuiz: Int
    let avatarIndex: Int
    let renderConfig: Guardian3DConfig
    let iconResName: String

    init(
        powerId: String,
        powerName: String,
        powerCategory: PowerCategory,
        description: String,
        cooldownRounds: Int = 0,
        chargesPerQuiz: Int = 1,
        avatarIndex: Int,
        renderConfig: Guardian3DConfig = Guardian3DConfig(),
        iconResName: String = ""
    ) {
        self.powerId = powerId
        self.powerName = powerName
        self.powerCategory = powerCategory
        self.description = description
        self.cooldownRounds = cooldownRounds
        self.chargesPerQuiz = chargesPerQuiz
        self.avatarIndex = avatarIndex
        self.renderConfig = renderConfig
        self.iconResName = iconResName
    }

    /// Unique action-oriented concise power label for buttons and badges.
    var shortLabel: String {
        switch powerId {
        case "FASCIAL_PLANE_SCAN": return "Fascial"
        case "OSTEOTOME_CHISEL": return "Chisel"
        case "RIBCAGE_BASTION": return "Ribcage"
        case "OSTEOLOGY_SURGE": return "Osteology"
        case "ECG_RHYTHM_TRACE": return "ECG Trace"
        case "DEFIBRILLATOR_SHOCK": return "Defib"
        case "VAGAL_REFRACTORY": return "Vagal Calm"
        case "BIOELECTRIC_SURGE": return "Bioelectric"
        case "METABOLIC_PATHWAY_MAP": return "Pathway"
        case "ENZYME_CLEAVAGE": return "Enzyme Cut"
        case "BUFFER_EQUILIBRIUM": return "Buffer Ward"
        case "ATP_SURGE": return "ATP Surge"
        case "BIOPSY_STAIN": return "Biopsy"
        case "CELLULAR_NECROSIS": return "Necrosis"
        case "APOPTOSIS_WARD": return "Apoptosis"
        case "CYTOKINE_STORM": return "Cytokine"
        case "RECEPTOR_BINDING_SCAN": return "Receptor"
        case "ANTAGONIST_BLOCK": return "Blockade"
        case "RECEPTOR_ANTIDOTE": return "Antidote"
        case "ADRENALINE_INFUSION": return "Adrenaline"
        case "GRAM_STAIN_ID": return "Gram Stain"
        case "PETRI_CONTAINMENT": return "Petri Trap"
        case "STERILE_ISOLATION": return "Isolation"
        case "EXPONENTIAL_COLONY": return "Colony"
        case "FORENSIC_AUTOPSY": return "Autopsy"
        case "INQUEST_EXCISION": return "Inquest"
        case "JURISPRUDENCE_IMMUNITY": return "Legal Ward"
        case "POST_MORTEM_CERTAINTY": return "Certainty"
        case "EPIDEMIOLOGIC_SURVEY": return "Survey"
        case "QUARANTINE_VECTOR": return "Vector Purge"
        case "EPIDEMIC_QUARANTINE": return "Quarantine"
        case "HERD_IMMUNITY": return "Herd Ward"
        case "CLINICAL_DIFFERENTIAL": return "Differential"
        case "TARGETED_THERAPY": return "Target Rx"
        case "CLINICAL_STABILIZER": return "Stabilizer"
        case "GRAND_ROUNDS_INSIGHT": return "Rounds"
        case "PRE_OP_IMAGING": return "Pre-Op"
        case "SURGICAL_EXCISION": return "Scalpel"
        case "HEMOSTATIC_CLAMP": return "Hemostat"
        case "LAPAROSCOPIC_SURGE": return "Laparo"
        case "NST_MONITORING": return "NST Trace"
        case "AMNIOTIC_CLEAVE": return "Amniotic"
        case "FETAL_HEART_SHIELD": return "Fetal Ward"
        case "PARTURITION_POWER": return "Parturition"
        case "APGAR_ASSESSMENT": return "Apgar"
        case "VACCINE_SHIELD_EXCISION": return "Vaccine"
        case "PEDIATRIC_IMMUNITY": return "Immunity"
        case "GROWTH_SPURT_SURGE": return "Growth"
        case "STRESS_FRACTURE_SCAN": return "Fracture"
        case "ORTHOPEDIC_HAMMER": return "Traction"
        case "ORTHOPEDIC_CAST": return "Plaster Cast"
        case "CALLUS_REMODELING": return "Callus"
        case "FUNDUS_EXAMINATION": return "Fundus"
        case "RETINAL_BEAM": return "Laser"
        case "CORNEAL_SHIELD": return "Cornea"
        case "TWENTY_TWENTY_CLARITY": return "20/20 Focus"
        case "SONIC_RESONANCE": return "Resonance"
        case "MYRINGOTOMY_PROBE": return "Myringotomy"
        case "TYMPANIC_MEMBRANE": return "Tympanic"
        case "HARMONIC_AMPLIFICATION": return "Harmonic"
        case "DERMOSCOPY_PATTERN": return "Dermoscopy"
        case "CRYOTHERAPY_FREEZE": return "Cryo Freeze"
        case "EPIDERMAL_BARRIER": return "Epidermal"
        case "STRATUM_LUCIDUM_GLOW": return "Stratum"
        case "MSE_COGNITIVE_SCAN": return "MSE Scan"
        case "SYNAPTIC_PRUNING": return "Pruning"
        case "NEURAL_CALM": return "Neural Calm"
        case "COGNITIVE_RESTRUCTURING": return "Reframe"
        case "PHOTON_SCAN": return "Photon"
        case "FOCUSED_XRAY_BEAM": return "X-Ray"
        case "LEAD_APRON_BARRIER": return "Lead Apron"
        case "THREE_D_RECONSTRUCTION": return "3D Voxel"
        case "MAC_VOLATILE_MONITOR": return "MAC Trace"
        case "LARYNGOSCOPIC_SWEEP": return "Laryngo"
        case "NARCOSIS_FIELD": return "Narcosis"
        case "EMERGENCE_ACCELERATION": return "Emergence"
        default: return powerName.components(separatedBy: " ").first ?? powerName
        }
    }

    /// System SF Symbol fallback or asset-based representation.
    var systemIconName: String {
        switch powerCategory {
        case .overlay, .textFormat: return "magnifyingglass.circle.fill"
        case .elimination: return "bolt.shield.fill"
        case .safetyNet: return "shield.fill"
        case .timeScore: return "flame.fill"
        }
    }
}

/// Tri-Faction classification matching MediGyaan Android:
/// - ANGEL: Celestial Divine Order, restoration, light, and protection.
/// - DEMON: Nether Abyssal Power, necrosis, plagues, soulfire, and entropy.
/// - HUMAN: Cybernetic Clinical Intellect, biomechanics, precision surgery, and pharmaceuticals.
enum GuardianFaction: String, CaseIterable, Codable {
    case angel = "ANGEL"
    case demon = "DEMON"
    case human = "HUMAN"

    var displayName: String {
        switch self {
        case .angel: return "ANGEL"
        case .demon: return "DEMON"
        case .human: return "HUMAN"
        }
    }

    var badgeColorHex: String {
        switch self {
        case .angel: return "#FFD700"
        case .demon: return "#FF1744"
        case .human: return "#00E5FF"
        }
    }

    var badgeColor: Color {
        Color(hex: badgeColorHex)
    }

    var loreTitle: String {
        switch self {
        case .angel: return "Celestial Divine Order"
        case .demon: return "Nether Abyssal Power"
        case .human: return "Cybernetic Clinical Savant"
        }
    }

    var iconEmoji: String {
        switch self {
        case .angel: return "✨"
        case .demon: return "🔥"
        case .human: return "⚡"
        }
    }
}

/// Mastery Origin Story for an MBBS Subject Master Guardian.
struct MasteryStory: Identifiable, Codable, Hashable {
    var id: Int { avatarIndex }
    let avatarIndex: Int
    let subjectTitle: String
    let chapterName: String
    let narrative: String
    let clinicalPhilosophy: String
    let highYieldMnemonic: String
}

/// 4-Power Tactical Arsenal Kit for an MBBS Guardian.
struct GuardianHeroKit: Identifiable, Hashable {
    var id: Int { avatarIndex }
    let avatarIndex: Int
    let championName: String
    let subjectSpecialty: String
    let faction: GuardianFaction
    let intelPower: GuardianPower
    let strikePower: GuardianPower
    let defensePower: GuardianPower
    let surgePower: GuardianPower
    let story: MasteryStory

    var allPowers: [GuardianPower] {
        [intelPower, strikePower, defensePower, surgePower]
    }
}
