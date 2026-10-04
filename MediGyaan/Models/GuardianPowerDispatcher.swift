import SwiftUI
import Combine

/// Runtime power dispatcher and animation engine for Guardian abilities during MCQ quiz sessions.
///
/// 1:1 port of Android `GuardianPowerDispatcher.kt` and `GuardianPowerAnimator.kt`.
/// Manages loadout of up to 3 equipped animal warriors / MBBS guardians, tracking charges,
/// countdown cooldown rounds, and dispatching educational cognitive mutations
/// (Option Elimination, Text Reformatting, Time Freezes & Multipliers, Safety Nets, and Overlays).
public final class GuardianPowerDispatcher: ObservableObject {

    public static let shared = GuardianPowerDispatcher()
    public static let maxLoadoutSize = 3

    @Published public private(set) var loadout: [GuardianLoadoutSlot] = []
    @Published public private(set) var currentRound: Int = 0
    @Published public private(set) var lastActivatedSlotIndex: Int = -1

    public init() {}

    // ─── POWER RESULT DEFINITIONS ──────────────────────────────────────────

    public enum PowerResult: Equatable {
        case eliminate(optionsToRemove: Int, powerName: String)
        case textFormat(formatType: TextFormatType, powerName: String)
        case timeScore(bonusTimeSeconds: Double, scoreMultiplier: Double, freezeTimerSeconds: Double, powerName: String)
        case safetyNet(safetyType: SafetyType, powerName: String)
        case overlay(overlayType: OverlayType, powerName: String)
        case failed(reason: String)
    }

    public enum TextFormatType: String, Equatable {
        case simplifyTerminology   // Octopus: Ink Reformat
        case bulletSummary         // Beaver: Dam Builder
        case decodeDoubleNegative  // Raven: Hex Decode
    }

    public enum SafetyType: String, Equatable {
        case secondAttempt    // Mantis: Adrenaline Surge
        case negatePenalty    // Pangolin: Carapace Shield
        case replaceQuestion  // Phoenix: Phoenix Rebirth
        case scoreLock        // Ram: Armor Ward
        case autoSubmit       // Bear: Hibernate Grace
    }

    public enum OverlayType: String, Equatable {
        case keywordHighlight     // Stag: Verdant Clarity
        case contextualHint       // Rhino: Emergency Hint
        case mnemonicOverlay      // Chameleon: Mirage Lens
        case absoluteMarker       // Cobra: Venom Highlight
        case relevanceMap         // Dolphin: Deep Scan
        case halfReveal           // Eagle: Apex Scout
        case distractorHighlight  // Scorpion: Toxin Neutralizer
        case lowPickReveal        // Vulture: Scavenger Strike
        case mostWrongReveal      // Leopard: Ambush Reveal
    }

    // ─── LOADOUT MANAGEMENT ────────────────────────────────────────────────

    public func initLoadout(avatarIndices: [Int]) {
        loadout.removeAll()
        currentRound = 0
        lastActivatedSlotIndex = -1
        let prefixIndices = Array(avatarIndices.prefix(Self.maxLoadoutSize))
        let slots = GuardianRegistry.createLoadout(avatarIndices: prefixIndices)
        loadout = slots
    }

    public func initSingleGuardian(avatarIndex: Int) {
        initLoadout(avatarIndices: [avatarIndex])
    }

    public var hasActivatablePower: Bool {
        loadout.contains { $0.canActivate }
    }

    public func onNewRound() {
        currentRound += 1
        for i in 0..<loadout.count {
            loadout[i].tickCooldown()
        }
    }

    // ─── POWER ACTIVATION ──────────────────────────────────────────────────

    public func activatePower(slotIndex: Int) -> PowerResult {
        guard slotIndex >= 0 && slotIndex < loadout.count else {
            return .failed(reason: "Invalid slot index")
        }

        var slot = loadout[slotIndex]
        guard slot.canActivate else {
            if !slot.isActive { return .failed(reason: "\(slot.power.powerName) is disabled") }
            if slot.remainingCharges <= 0 { return .failed(reason: "\(slot.power.powerName): No charges remaining") }
            if slot.cooldownRemaining > 0 { return .failed(reason: "\(slot.power.powerName): On cooldown (\(slot.cooldownRemaining) rounds)") }
            return .failed(reason: "Cannot activate \(slot.power.powerName)")
        }

        slot.consume()
        loadout[slotIndex] = slot
        lastActivatedSlotIndex = slotIndex

        return dispatchPower(slot.power)
    }

    public func activatePowerById(_ powerId: String) -> PowerResult {
        guard let slotIndex = loadout.firstIndex(where: { $0.power.powerId == powerId }) else {
            return .failed(reason: "Power \(powerId) not equipped in loadout")
        }
        return activatePower(slotIndex: slotIndex)
    }

    private func dispatchPower(_ power: GuardianPower) -> PowerResult {
        switch power.powerId {
        // ─── ELIMINATION (1 OPTION REMOVED) ───
        case "ECHO_SCAN", "OSTEOTOME_CHISEL", "ENZYME_CLEAVAGE", "ANTAGONIST_BLOCK",
             "INQUEST_EXCISION", "QUARANTINE_VECTOR", "TARGETED_THERAPY", "AMNIOTIC_CLEAVE",
             "VACCINE_SHIELD_EXCISION", "ORTHOPEDIC_HAMMER", "MYRINGOTOMY_PROBE",
             "CRYOTHERAPY_FREEZE", "SYNAPTIC_PRUNING", "LARYNGOSCOPIC_SWEEP":
            return .eliminate(optionsToRemove: 1, powerName: power.powerName)

        // ─── ELIMINATION (2 OPTIONS REMOVED) ───
        case "THORNHIDE_FILTER", "DEFIBRILLATOR_SHOCK", "CELLULAR_NECROSIS",
             "PETRI_CONTAINMENT", "SURGICAL_EXCISION", "RETINAL_BEAM", "FOCUSED_XRAY_BEAM":
            return .eliminate(optionsToRemove: 2, powerName: power.powerName)

        // ─── OVERLAYS / HINTS ───
        case "FASCIAL_PLANE_SCAN", "VERDANT_CLARITY":
            return .overlay(overlayType: .keywordHighlight, powerName: power.powerName)

        case "ECG_RHYTHM_TRACE", "METABOLIC_PATHWAY_MAP", "BIOPSY_STAIN", "RECEPTOR_BINDING_SCAN",
             "GRAM_STAIN_ID", "FORENSIC_AUTOPSY", "EPIDEMIOLOGIC_SURVEY", "CLINICAL_DIFFERENTIAL",
             "PRE_OP_IMAGING", "NST_MONITORING", "APGAR_ASSESSMENT", "STRESS_FRACTURE_SCAN",
             "FUNDUS_EXAMINATION", "SONIC_RESONANCE", "DERMOSCOPY_PATTERN", "MSE_COGNITIVE_SCAN",
             "PHOTON_SCAN", "MAC_VOLATILE_MONITOR", "EMERGENCY_HINT", "MIRAGE_LENS",
             "VENOM_HIGHLIGHT", "DEEP_SCAN", "APEX_SCOUT":
            return .overlay(overlayType: .contextualHint, powerName: power.powerName)

        case "SCAVENGER_STRIKE":
            return .overlay(overlayType: .lowPickReveal, powerName: power.powerName)
        case "AMBUSH_REVEAL":
            return .overlay(overlayType: .mostWrongReveal, powerName: power.powerName)
        case "TOXIN_NEUTRALIZER":
            return .overlay(overlayType: .distractorHighlight, powerName: power.powerName)

        // ─── TEXT FORMATTING ───
        case "INK_REFORMAT":
            return .textFormat(formatType: .simplifyTerminology, powerName: power.powerName)
        case "DAM_BUILDER":
            return .textFormat(formatType: .bulletSummary, powerName: power.powerName)
        case "HEX_DECODE":
            return .textFormat(formatType: .decodeDoubleNegative, powerName: power.powerName)

        // ─── SAFETY NETS (SECOND CHANCE) ───
        case "ADRENALINE_SURGE", "RECEPTOR_ANTIDOTE", "JURISPRUDENCE_IMMUNITY",
             "FETAL_HEART_SHIELD", "COGNITIVE_RESTRUCTURING":
            return .safetyNet(safetyType: .secondAttempt, powerName: power.powerName)

        // ─── SAFETY NETS (PENALTY NEGATION) ───
        case "RIBCAGE_BASTION", "BUFFER_EQUILIBRIUM", "APOPTOSIS_WARD", "STERILE_ISOLATION",
             "EPIDEMIC_QUARANTINE", "CLINICAL_STABILIZER", "HEMOSTATIC_CLAMP", "PEDIATRIC_IMMUNITY",
             "ORTHOPEDIC_CAST", "CORNEAL_SHIELD", "TYMPANIC_MEMBRANE", "EPIDERMAL_BARRIER",
             "LEAD_APRON_BARRIER", "NARCOSIS_FIELD", "CARAPACE_SHIELD":
            return .safetyNet(safetyType: .negatePenalty, powerName: power.powerName)

        case "PHOENIX_REBIRTH":
            return .safetyNet(safetyType: .replaceQuestion, powerName: power.powerName)
        case "ARMOR_WARD":
            return .safetyNet(safetyType: .scoreLock, powerName: power.powerName)
        case "HIBERNATE_GRACE":
            return .safetyNet(safetyType: .autoSubmit, powerName: power.powerName)

        // ─── TIME FREEZES ───
        case "VAGAL_REFRACTORY", "NEURAL_CALM":
            return .timeScore(bonusTimeSeconds: 0, scoreMultiplier: 1.0, freezeTimerSeconds: 6.0, powerName: power.powerName)
        case "TWENTY_TWENTY_CLARITY", "BASTION_FREEZE":
            return .timeScore(bonusTimeSeconds: 0, scoreMultiplier: 1.0, freezeTimerSeconds: 8.0, powerName: power.powerName)

        // ─── TIME & SCORE MULTIPLIERS ───
        case "OSTEOLOGY_SURGE", "EXPONENTIAL_COLONY", "LAPAROSCOPIC_SURGE",
             "GROWTH_SPURT_SURGE", "CALLUS_REMODELING", "HARMONIC_AMPLIFICATION",
             "STRATUM_LUCIDUM_GLOW", "EMERGENCE_ACCELERATION", "CYTOKINE_STORM", "PACK_STREAK":
            return .timeScore(bonusTimeSeconds: 0, scoreMultiplier: 1.5, freezeTimerSeconds: 0, powerName: power.powerName)

        case "BIOELECTRIC_SURGE", "ATP_SURGE", "ADRENALINE_INFUSION", "POST_MORTEM_CERTAINTY",
             "HERD_IMMUNITY", "GRAND_ROUNDS_INSIGHT", "PARTURITION_POWER",
             "THREE_D_RECONSTRUCTION", "BLITZ_BONUS":
            return .timeScore(bonusTimeSeconds: 0, scoreMultiplier: 2.0, freezeTimerSeconds: 0, powerName: power.powerName)

        case "BERSERK_SOLVE":
            return .timeScore(bonusTimeSeconds: 0, scoreMultiplier: 3.0, freezeTimerSeconds: 0, powerName: power.powerName)
        case "TIME_SIPHON":
            return .timeScore(bonusTimeSeconds: 15.0, scoreMultiplier: 1.0, freezeTimerSeconds: 0, powerName: power.powerName)
        case "DOMINANT_TIMER":
            return .timeScore(bonusTimeSeconds: 20.0, scoreMultiplier: 1.0, freezeTimerSeconds: 0, powerName: power.powerName)

        default:
            switch power.powerCategory {
            case .elimination:
                return .eliminate(optionsToRemove: power.chargesPerQuiz <= 2 ? 2 : 1, powerName: power.powerName)
            case .timeScore:
                return .timeScore(bonusTimeSeconds: 0, scoreMultiplier: 1.5, freezeTimerSeconds: 5.0, powerName: power.powerName)
            case .safetyNet:
                return .safetyNet(safetyType: .negatePenalty, powerName: power.powerName)
            case .overlay:
                return .overlay(overlayType: .contextualHint, powerName: power.powerName)
            case .textFormat:
                return .textFormat(formatType: .simplifyTerminology, powerName: power.powerName)
            }
        }
    }
}

/// Loadout slot model representing an equipped guardian power in battle / quiz.
public struct GuardianLoadoutSlot: Identifiable, Hashable {
    public var id: String { power.powerId }
    public let power: GuardianPower
    public var remainingCharges: Int
    public var cooldownRemaining: Int
    public var isActive: Bool

    public init(power: GuardianPower, remainingCharges: Int? = nil, cooldownRemaining: Int = 0, isActive: Bool = true) {
        self.power = power
        self.remainingCharges = remainingCharges ?? power.chargesPerQuiz
        self.cooldownRemaining = cooldownRemaining
        self.isActive = isActive
    }

    public var canActivate: Bool {
        isActive && remainingCharges > 0 && cooldownRemaining <= 0
    }

    public mutating func consume() {
        if remainingCharges > 0 {
            remainingCharges -= 1
            cooldownRemaining = power.cooldownRounds
        }
    }

    public mutating func tickCooldown() {
        if cooldownRemaining > 0 {
            cooldownRemaining -= 1
        }
    }
}
