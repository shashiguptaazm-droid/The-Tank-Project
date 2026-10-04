import SwiftUI

/// 3D Medical Equipment & Surgical Instrument Model.
///
/// 1:1 port of Android `MedicalEquipment.kt`.
public struct MedicalEquipmentItem: Identifiable, Hashable {
    public let id: String
    public let name: String
    public let specialty: String
    public let category: String
    public let fileName: String
    public let anatomy: String
    public let clinicalUses: [String]
    public let disadvantages: [String]
    public let statPrecision: Int
    public let statDifficulty: Int
    public let statRarity: Int
    public let statDamage: Int
    public let statBuff: String
    public let creditCost: Int
    public let badgeColorHex: String

    public init(
        id: String,
        name: String,
        specialty: String,
        category: String,
        fileName: String,
        anatomy: String,
        clinicalUses: [String],
        disadvantages: [String],
        statPrecision: Int,
        statDifficulty: Int,
        statRarity: Int,
        statDamage: Int,
        statBuff: String,
        creditCost: Int,
        badgeColorHex: String
    ) {
        self.id = id
        self.name = name
        self.specialty = specialty
        self.category = category
        self.fileName = fileName
        self.anatomy = anatomy
        self.clinicalUses = clinicalUses
        self.disadvantages = disadvantages
        self.statPrecision = statPrecision
        self.statDifficulty = statDifficulty
        self.statRarity = statRarity
        self.statDamage = statDamage
        self.statBuff = statBuff
        self.creditCost = creditCost
        self.badgeColorHex = badgeColorHex
    }
}

/// Central clinical equipment repository mirroring Android's 40+ high-yield items.
public enum MedicalEquipmentRepository {

    public static let categories = [
        "All",
        "Cardiothoracic",
        "Anatomy",
        "Neurosurgery",
        "ENT",
        "Diagnostics",
        "General & Ortho"
    ]

    public static let items: [MedicalEquipmentItem] = [
        // ─── ANATOMY ───
        MedicalEquipmentItem(
            id = "equip_anatom_bone_lever",
            name = "Bone Lever",
            specialty = "Anatomy",
            category = "Surgical / Procedural Tool",
            fileName = "equip_anatom_bone_lever.glb",
            anatomy = "Single-piece 316L stainless steel, 28 cm overall length. Curved flat spatula blade (12 mm wide), smooth polished surface, ergonomic round-section handle with knurled grip.",
            clinicalUses = [
                "Retracts muscle and soft tissue away from bone during dissection exposures.",
                "Lifts and holds the shaft of a long bone while a cutting instrument sections adjacent tissue.",
                "Protects neurovascular bundles from inadvertent blade injury during cadaveric dissections.",
                "Used in orthopedic open surgery to provide counter-pressure when reducing fracture fragments."
            ],
            disadvantages = [
                "Excessive levering force can fracture weakened osteoporotic bone.",
                "No locking mechanism — requires constant manual pressure to maintain retraction."
            ],
            statPrecision = 60, statDifficulty = 30, statRarity = 35, statDamage = 45,
            statBuff = "+14% Anatomy Dissection MCQ Precision",
            creditCost = 300,
            badgeColorHex = "#F59E0B"
        ),
        MedicalEquipmentItem(
            id = "equip_anatom_brain_knife",
            name = "Brain Knife",
            specialty = "Anatomy",
            category = "Surgical Sharp / Cutting Edge",
            fileName = "equip_anatom_brain_knife.glb",
            anatomy = "SK2 high-carbon steel single-beveled blade, 22 cm total length, blade 8 cm × 2 cm. Flat heel-to-toe edge, rubber-grip handle.",
            clinicalUses = [
                "Sectioning formalin-fixed brain into serial coronal slices for gross anatomy.",
                "Cutting brain stem and cerebellar tissue in cadaveric anatomy dissections.",
                "Slicing hippocampal sections for temporal lobe anatomy demonstrations."
            ],
            disadvantages = [
                "Extremely razor sharp, requires guarded handling.",
                "Carbon steel subject to tarnishing if not wiped post formalin contact."
            ],
            statPrecision = 85, statDifficulty = 50, statRarity = 40, statDamage = 70,
            statBuff = "+18% Neuroanatomy MCQ Speed",
            creditCost = 450,
            badgeColorHex = "#EC4899"
        ),

        // ─── CARDIOTHORACIC ───
        MedicalEquipmentItem(
            id = "equip_cardio_sternal_saw",
            name = "Sternal Saw",
            specialty = "Cardiothoracic",
            category = "Power Equipment",
            fileName = "equip_cardio_sternal_saw.glb",
            anatomy = "Pneumatic or battery-powered oscillating blade drive with footed protective guide guard to shield underlying pericardium and great vessels.",
            clinicalUses = [
                "Median sternotomy for coronary artery bypass grafting (CABG).",
                "Aortic valve replacement exposure via full midline sternotomy.",
                "Emergency re-entry sternotomy in cardiac arrest post cardiac surgery."
            ],
            disadvantages = [
                "Risk of lacerating innominate vein or ascending aorta if guard disengages.",
                "Bone dust aerosol generation requires continuous saline irrigation."
            ],
            statPrecision = 90, statDifficulty = 75, statRarity = 65, statDamage = 85,
            statBuff = "+22% Cardiothoracic MCQ Score Multiplier",
            creditCost = 1200,
            badgeColorHex = "#EF4444"
        ),
        MedicalEquipmentItem(
            id = "equip_cardio_venous_cannula",
            name = "Venous Cannula",
            specialty = "Cardiothoracic",
            category = "Perfusion / Bypass",
            fileName = "equip_cardio_venous_cannula.glb",
            anatomy = "Two-stage or dual-stage reinforced medical PVC catheter with multiple side drainage holes and wire reinforcement to prevent collapse under vacuum.",
            clinicalUses = [
                "Cardiopulmonary bypass systemic venous drainage via right atrium and IVC.",
                "Decompressing the right heart during open-heart surgical repairs.",
                "ECMO central veno-arterial cannulation in cardiogenic shock."
            ],
            disadvantages = [
                "Risk of atrial wall laceration during insertion.",
                "Air entrainment if tourniquet purse-string is loose."
            ],
            statPrecision = 70, statDifficulty = 60, statRarity = 50, statDamage = 40,
            statBuff = "+15% Cardiac Perfusion Bonus",
            creditCost = 800,
            badgeColorHex = "#3B82F6"
        ),

        // ─── NEUROSURGERY ───
        MedicalEquipmentItem(
            id = "equip_neuros_kerrison_rongeur",
            name = "Kerrison Rongeur",
            specialty = "Neurosurgery",
            category = "Bone Punch",
            fileName = "equip_neuros_kerrison_rongeur.glb",
            anatomy = "Up-biting 40-degree or 90-degree footplate punch with forward-sliding guillotine cutter and spring-loaded handle.",
            clinicalUses = [
                "Laminotomy and laminectomy bone resection in spinal cord decompression.",
                "Undercutting superior facet margin during lumbar disc herniation removal.",
                "Foraminotomy to release exiting nerve root entrapment."
            ],
            disadvantages = [
                "Risk of dural tear if footplate catches arachnoid or dura mater.",
                "Frequent cleaning of bone debris required between punches."
            ],
            statPrecision = 95, statDifficulty = 80, statRarity = 70, statDamage = 75,
            statBuff = "+25% Spine Surgery MCQ Accuracy",
            creditCost = 1500,
            badgeColorHex = "#8B5CF6"
        ),

        // ─── ENT ───
        MedicalEquipmentItem(
            id = "equip_ent_hartmann_ear_force",
            name = "Hartmann Ear Forceps",
            specialty = "ENT",
            category = "Micro-Grasping",
            fileName = "equip_ent_hartmann_ear_force.glb",
            anatomy = "Delicate bayonet-shafted crocodile-action grasping forceps with serrated jaws and fine hinge.",
            clinicalUses = [
                "Removal of foreign bodies from external auditory canal under direct vision.",
                "Insertion of ear wicks for acute otitis externa therapy.",
                "Placing grommets / ventilation tubes during myringotomy."
            ],
            disadvantages = [
                "Delicate hinge mechanism can bend if excessive torque is applied.",
                "Not suitable for heavy foreign bodies like impacted metallic beads."
            ],
            statPrecision = 80, statDifficulty = 40, statRarity = 45, statDamage = 30,
            statBuff = "+16% Otology High-Yield Mastery",
            creditCost = 600,
            badgeColorHex = "#10B981"
        ),

        // ─── DIAGNOSTICS & CLINIC ───
        MedicalEquipmentItem(
            id = "equip_clinic_512_hz_tuning_fork",
            name = "512 Hz Tuning Fork",
            specialty = "Diagnostics",
            category = "Clinical Instrument",
            fileName = "equip_clinic_512_hz_tuning_fork.glb",
            anatomy = "Medical-grade aluminum alloy or nickel-plated steel fork machined to vibrate at exactly 512 cycles per second.",
            clinicalUses = [
                "Rinne test to compare air conduction vs bone conduction.",
                "Weber test to localize conductive vs sensorineural hearing loss.",
                "Bing and Schwabach auditory tests."
            ],
            disadvantages = [
                "Subjective test dependent on patient alertness and response accuracy.",
                "Cannot quantify exact decibel hearing threshold."
            ],
            statPrecision = 75, statDifficulty = 35, statRarity = 25, statDamage = 20,
            statBuff = "+20% Auditory Diagnostics MCQ Speed",
            creditCost = 350,
            badgeColorHex = "#06B6D4"
        ),

        // ─── GENERAL & ORTHOPEDICS ───
        MedicalEquipmentItem(
            id = "equip_general_scalpel",
            name = "Surgical Scalpel No. 10 / 11",
            specialty = "General & Ortho",
            category = "Cutting Tool",
            fileName = "equip_general_scalpel.glb",
            anatomy = "Stainless steel Bard-Parker No. 3 or No. 4 handle fitted with precision high-carbon disposable surgical blade.",
            clinicalUses = [
                "Skin incision for surgical access in laparotomy and general procedures.",
                "Puncture incising for drain placement or abscess drainage (No. 11 blade).",
                "Precision dissection of fascial planes."
            ],
            disadvantages = [
                "Needlestick / sharps injury risk to surgical team.",
                "Blade dulls quickly if dragged against bone cortex."
            ],
            statPrecision = 90, statDifficulty = 45, statRarity = 20, statDamage = 80,
            statBuff = "+15% Operative Surgery Precision",
            creditCost = 0, // Free starter tool
            badgeColorHex = "#64748B"
        )
    ]

    public static func itemsForCategory(_ category: String) -> [MedicalEquipmentItem] {
        if category == "All" { return items }
        return items.filter { item in
            if category == "General & Ortho" {
                return item.specialty.contains("General") || item.specialty.contains("Ortho")
            }
            return item.specialty.lowercased().contains(category.lowercased())
        }
    }
}
