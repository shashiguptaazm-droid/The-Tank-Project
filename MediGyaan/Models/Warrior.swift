import SwiftUI

/// Animal Avatar Warrior model strictly conforming to `character_spec/avatar_3d_generation_guide.md`.
/// Authoritative source for all 27 animal warrior avatars in MediGyaan.
struct Warrior: Identifiable, Hashable {
    let id: Int
    let animal: String
    let name: String
    let specialty: String
    let catchphrase: String
    let heroPlotline: String
    let questTitle: String
    let vitality: Int
    let assault: Int
    let defense: Int
    let control: Int
    let speed: Int
    let archetype: Archetype
    let glowColorHex: String

    var displayName: String { "\(animal) • \(name)" }
    var title: String { "The \(animal) • \(name) (\(specialty))" }

    var glowColor: Color {
        Color(hex: glowColorHex)
    }

    /// Corresponding avatar image asset name (avatar_01 through avatar_27)
    var avatarImageName: String {
        String(format: "avatar_%02d", id)
    }

    /// Corresponding 3D GLB asset filename if available (char01_axiom through char19_somnus)
    var glbModelName: String? {
        let glbMap: [Int: String] = [
            1: "char01_axiom.glb",
            2: "char02_pulse.glb",
            3: "char03_catalyst.glb",
            4: "char04_necros.glb",
            5: "char05_pharma.glb",
            6: "char06_microx.glb",
            7: "char07_verdict.glb",
            8: "char08_cura.glb",
            9: "char09_medicus.glb",
            10: "char10_surgon.glb",
            11: "char11_vita.glb",
            12: "char12_pedia.glb",
            13: "char13_osteon.glb",
            14: "char14_optix.glb",
            15: "char15_resona.glb",
            16: "char16_derma.glb",
            17: "char17_synapse.glb",
            18: "char18_rayne.glb",
            19: "char19_somnus.glb"
        ]
        return glbMap[id]
    }

    enum Archetype: String, CaseIterable {
        case vitality = "Vitality & Recovery"
        case fortification = "Fortification & Shield"
        case assault = "Assault & Strike"
        case sabotage = "Sabotage & Disruption"
        case tactics = "Time & Focus"

        var color: Color {
            switch self {
            case .vitality: return Color(hex: "#00E676")
            case .fortification: return Color(hex: "#00E5FF")
            case .assault: return Color(hex: "#FF5252")
            case .sabotage: return Color(hex: "#E040FB")
            case .tactics: return Color(hex: "#FFD700")
            }
        }
    }

    /// All 27 unique characters from the authoritative specification.
    static let allWarriors: [Warrior] = [
        Warrior(
            id: 1,
            animal: "Mantis",
            name: "Zerek",
            specialty: "ER Trauma",
            catchphrase: "Sleep is just a trial version of death; pass NEET first!",
            heroPlotline: "Zerek quests across hospital corridors to discover the legendary 1,000th cup of espresso that grants permanent immunity to sleep deprivation during 36-hour ER shifts.",
            questTitle: "The Caffeine Chronicles",
            vitality: 9, assault: 7, defense: 5, control: 4, speed: 8,
            archetype: .vitality,
            glowColorHex: "#00E676"
        ),
        Warrior(
            id: 2,
            animal: "Octopus",
            name: "Octavius",
            specialty: "Critical Care ICU",
            catchphrase: "Why use two hands when you can type answers and hold an IV simultaneously?",
            heroPlotline: "Juggles emergency resuscitations across four simultaneous hospital wards while hunting down the rogue pager that keeps beeping at 4:15 AM.",
            questTitle: "The Eight-Armed Round",
            vitality: 6, assault: 5, defense: 6, control: 10, speed: 6,
            archetype: .tactics,
            glowColorHex: "#7C4DFF"
        ),
        Warrior(
            id: 3,
            animal: "Ram",
            name: "Balthazar",
            specialty: "Orthopedic Trauma",
            catchphrase: "If memorization fails, brute-force the cranium!",
            heroPlotline: "Embarks on a grueling quest to head-butt every standard medical textbook until the entire syllabus is permanently etched into his frontal lobe.",
            questTitle: "The Cranial Siege",
            vitality: 8, assault: 6, defense: 9, control: 4, speed: 5,
            archetype: .fortification,
            glowColorHex: "#00E5FF"
        ),
        Warrior(
            id: 4,
            animal: "Bat",
            name: "Vesper",
            specialty: "Radiology Night Shift",
            catchphrase: "The sun is just a thermal radiation hazard.",
            heroPlotline: "Solves complex clinical mysteries in absolute library darkness using only echolocation and dusty, forgotten medical journals.",
            questTitle: "Ghost of the Sub-Basement",
            vitality: 6, assault: 6, defense: 8, control: 7, speed: 8,
            archetype: .fortification,
            glowColorHex: "#2979FF"
        ),
        Warrior(
            id: 5,
            animal: "Pangolin",
            name: "Kaido",
            specialty: "Dermatology",
            catchphrase: "Bullets and negative markings bounce off equally.",
            heroPlotline: "Seeks absolute emotional armor against sarcastic external examiners and critical viva boards that try to puncture his peace of mind.",
            questTitle: "The Untouchable Shell",
            vitality: 8, assault: 5, defense: 10, control: 4, speed: 4,
            archetype: .fortification,
            glowColorHex: "#00E5FF"
        ),
        Warrior(
            id: 6,
            animal: "Vulture",
            name: "Malakor",
            specialty: "Pathology",
            catchphrase: "Your dropped marks are my gourmet feast.",
            heroPlotline: "Roams the competitive quiz leaderboards collecting the academic tears of students who failed pathology blocks.",
            questTitle: "The Score Harvester",
            vitality: 5, assault: 9, defense: 5, control: 7, speed: 7,
            archetype: .assault,
            glowColorHex: "#FF1744"
        ),
        Warrior(
            id: 7,
            animal: "Cheetah",
            name: "Swift",
            specialty: "Emergency Triage",
            catchphrase: "Click option B and pray!",
            heroPlotline: "Races against the ticking countdown clock to answer 500 emergency clinical MCQs before his phone battery hits 1%.",
            questTitle: "The 1.2-Second Guess",
            vitality: 5, assault: 9, defense: 4, control: 5, speed: 10,
            archetype: .assault,
            glowColorHex: "#FF5252"
        ),
        Warrior(
            id: 8,
            animal: "Beaver",
            name: "Thistle",
            specialty: "Public Health",
            catchphrase: "I will chew through the entire syllabus!",
            heroPlotline: "Builds an impenetrable dam of flashcards and sticky notes to hold back the tidal wave of upcoming professional exams.",
            questTitle: "The Great Syllabus Dam",
            vitality: 7, assault: 6, defense: 7, control: 8, speed: 6,
            archetype: .tactics,
            glowColorHex: "#E040FB"
        ),
        Warrior(
            id: 9,
            animal: "Phoenix",
            name: "Pyra",
            specialty: "Pharmacology Recovery",
            catchphrase: "Failed exams three times? Watch me top this time!",
            heroPlotline: "Rises gloriously from the ashes of three failed professional exam attempts to claim the university gold medal.",
            questTitle: "Ash and Adrenaline",
            vitality: 9, assault: 7, defense: 6, control: 6, speed: 7,
            archetype: .vitality,
            glowColorHex: "#FF6D00"
        ),
        Warrior(
            id: 10,
            animal: "Wolf",
            name: "Fenrir",
            specialty: "Cardiology Streaks",
            catchphrase: "I never lose my 20-win streak!",
            heroPlotline: "Leads a ruthless pack of study partners on an unstoppable 20-win quiz battle streak across national tournament brackets.",
            questTitle: "The 20-Win Pack",
            vitality: 6, assault: 10, defense: 5, control: 5, speed: 8,
            archetype: .assault,
            glowColorHex: "#D50000"
        ),
        Warrior(
            id: 11,
            animal: "Stag",
            name: "Cernun",
            specialty: "Psychiatry",
            catchphrase: "Your anxiety cannot outrun my herbal tea.",
            heroPlotline: "Defends the botanical healing gardens against stressed-out medical students looking for illicit energy drinks.",
            questTitle: "The Herbal Sanctuary",
            vitality: 8, assault: 6, defense: 6, control: 5, speed: 8,
            archetype: .vitality,
            glowColorHex: "#00E676"
        ),
        Warrior(
            id: 12,
            animal: "Gorilla",
            name: "Titan",
            specialty: "Sports Medicine",
            catchphrase: "Why read about hypertrophy when you can lift textbooks?",
            heroPlotline: "Bench-presses entire anatomical atlases and heavy encyclopedias to prove that physical strength equals clinical prowess.",
            questTitle: "The Atlas Lifter",
            vitality: 10, assault: 8, defense: 9, control: 4, speed: 4,
            archetype: .fortification,
            glowColorHex: "#00E5FF"
        ),
        Warrior(
            id: 13,
            animal: "Crocodile",
            name: "Sobek",
            specialty: "General Surgery",
            catchphrase: "Keep smiling during rounds. Hide the terror.",
            heroPlotline: "Lies dormant in murky clinical postings, waiting to strike viva professors with unshakeable diagnostic precision.",
            questTitle: "Swamp of the External Examiner",
            vitality: 8, assault: 7, defense: 9, control: 5, speed: 5,
            archetype: .fortification,
            glowColorHex: "#00B0FF"
        ),
        Warrior(
            id: 14,
            animal: "Leopard",
            name: "Orion",
            specialty: "Ophthalmology",
            catchphrase: "Dark mode on PDFs is my superpower.",
            heroPlotline: "Infiltrates hostel dormitories at midnight to extract secret high-yield question banks under blanket forts.",
            questTitle: "Shadows of the PDF",
            vitality: 5, assault: 10, defense: 5, control: 6, speed: 9,
            archetype: .assault,
            glowColorHex: "#FF1744"
        ),
        Warrior(
            id: 15,
            animal: "Rhino",
            name: "Goliath",
            specialty: "Nephrology",
            catchphrase: "My exam anxiety is over 9000!",
            heroPlotline: "Charges head-first into rogue hospital vending machines that eat currency coins without dropping iced coffee.",
            questTitle: "Vending Machine Vengeance",
            vitality: 9, assault: 6, defense: 10, control: 4, speed: 4,
            archetype: .fortification,
            glowColorHex: "#00E5FF"
        ),
        Warrior(
            id: 16,
            animal: "Chameleon",
            name: "Spectra",
            specialty: "Medical Ethics",
            catchphrase: "Did I attend this lecture? Even the professor isn't sure.",
            heroPlotline: "Masters quantum invisibility to attend mandatory lectures without physically existing in the room.",
            questTitle: "The Phantom Attending",
            vitality: 6, assault: 5, defense: 6, control: 10, speed: 7,
            archetype: .sabotage,
            glowColorHex: "#E040FB"
        ),
        Warrior(
            id: 17,
            animal: "Dolphin",
            name: "Echo",
            specialty: "ENT Audiology",
            catchphrase: "We have 5 extra seconds to overthink.",
            heroPlotline: "Navigates chaotic sonic turbulence of hostel roommates playing dubstep during critical pharmacology revision.",
            questTitle: "Auditory Zen",
            vitality: 7, assault: 5, defense: 6, control: 7, speed: 9,
            archetype: .tactics,
            glowColorHex: "#FFD700"
        ),
        Warrior(
            id: 18,
            animal: "Scorpion",
            name: "Venom",
            specialty: "Toxicology",
            catchphrase: "One wrong MCQ choice and my neurotoxin strikes!",
            heroPlotline: "Crafts diabolical clinical vignettes known to medical science to test and eliminate worthy challengers.",
            questTitle: "The Toxic Vignette",
            vitality: 6, assault: 9, defense: 6, control: 8, speed: 6,
            archetype: .assault,
            glowColorHex: "#FF5252"
        ),
        Warrior(
            id: 19,
            animal: "Lion",
            name: "Aurelius",
            specialty: "Administration",
            catchphrase: "Bow before the king of clinical viva.",
            heroPlotline: "Rules over clinical rounds with absolute monarchical authority and effortless batch-topping scores.",
            questTitle: "The Regent of the Ward",
            vitality: 7, assault: 8, defense: 7, control: 8, speed: 8,
            archetype: .tactics,
            glowColorHex: "#FFD700"
        ),
        Warrior(
            id: 20,
            animal: "Raven",
            name: "Corvus",
            specialty: "Forensic Medicine",
            catchphrase: "Nevermore shall you borrow my stethoscope.",
            heroPlotline: "Places ancient forensic curses on anyone who steals lab coats or stethoscopes from the dissection hall.",
            questTitle: "Curse of the Borrowed Stethoscope",
            vitality: 5, assault: 6, defense: 6, control: 10, speed: 8,
            archetype: .sabotage,
            glowColorHex: "#7C4DFF"
        ),
        Warrior(
            id: 21,
            animal: "Elephant",
            name: "Ganesha",
            specialty: "Pharmacology Memory",
            catchphrase: "I never forget a drug side effect.",
            heroPlotline: "Guards ancient library archives containing every pharmacological drug interaction discovered since 1950.",
            questTitle: "The Vault of Alexandria",
            vitality: 10, assault: 6, defense: 10, control: 5, speed: 4,
            archetype: .fortification,
            glowColorHex: "#00E5FF"
        ),
        Warrior(
            id: 22,
            animal: "Bear",
            name: "Ursa",
            specialty: "Sleep Medicine",
            catchphrase: "Do not disturb hibernation until exam day.",
            heroPlotline: "Sleeps for 14 hours and submits the high-scoring quiz in the final 3 seconds before deadline.",
            questTitle: "The Hibernation Submission",
            vitality: 9, assault: 7, defense: 8, control: 5, speed: 5,
            archetype: .vitality,
            glowColorHex: "#FFA000"
        ),
        Warrior(
            id: 23,
            animal: "Fox",
            name: "Reynard",
            specialty: "Plastic Surgery",
            catchphrase: "Why work hard when you can siphon time?",
            heroPlotline: "Siphons precious seconds off opponents' clocks while whispering tricky differential diagnoses in quiet lecture halls.",
            questTitle: "The Chrono-Bandit",
            vitality: 5, assault: 7, defense: 5, control: 9, speed: 9,
            archetype: .sabotage,
            glowColorHex: "#E040FB"
        ),
        Warrior(
            id: 24,
            animal: "Tiger",
            name: "Tigris",
            specialty: "Critical Care Comebacks",
            catchphrase: "When HP hits zero, berserker rage awakens!",
            heroPlotline: "Unleashes devastating berserk counter-attacks when reduced to his final 30 health points in brutal quiz duels.",
            questTitle: "The 30-HP Comeback",
            vitality: 6, assault: 10, defense: 6, control: 5, speed: 8,
            archetype: .assault,
            glowColorHex: "#FF1744"
        ),
        Warrior(
            id: 25,
            animal: "Eagle",
            name: "Aquila",
            specialty: "Radiology Targeting",
            catchphrase: "I spot the correct answer from 30,000 feet.",
            heroPlotline: "Scans complex radiological scans with sniper-like precision to eliminate wrong choices instantly.",
            questTitle: "The 30,000-Foot Diagnosis",
            vitality: 5, assault: 8, defense: 5, control: 7, speed: 10,
            archetype: .tactics,
            glowColorHex: "#FFD700"
        ),
        Warrior(
            id: 26,
            animal: "Cobra",
            name: "Naja",
            specialty: "Infectious Diseases",
            catchphrase: "Trust me, option C is correct... or is it?",
            heroPlotline: "Weaves intricate webs of deceptive clinical choices to trip up overconfident opponents during tense multiplayer matches.",
            questTitle: "The Serpentine Delusion",
            vitality: 6, assault: 8, defense: 5, control: 9, speed: 8,
            archetype: .sabotage,
            glowColorHex: "#AA00FF"
        ),
        Warrior(
            id: 27,
            animal: "Stallion",
            name: "Pegasus",
            specialty: "Pediatrics & Optimism",
            catchphrase: "Pure positive energy will carry me through!",
            heroPlotline: "Charges through medical school finals fueled entirely by boundless optimism and zero prior studying.",
            questTitle: "The Gallop of Pure Optimism",
            vitality: 7, assault: 7, defense: 7, control: 6, speed: 10,
            archetype: .tactics,
            glowColorHex: "#FFD700"
        )
    ]
}
