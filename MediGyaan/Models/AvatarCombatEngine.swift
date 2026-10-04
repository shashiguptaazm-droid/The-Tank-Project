import Foundation

/// Resolution of incoming damage to an avatar warrior.
struct DamageResolution: Hashable {
    let finalDamage: Int
    let blockedByShield: Bool
    let reflectedDamage: Int
    let revivedByPhoenix: Bool
    let emergencyShieldTriggered: Bool
    let floatMessage: String?
    let floatColorHex: String
}

/// Resolution of outgoing attack damage on correct answer.
struct AttackResolution: Hashable {
    let totalDamage: Int
    let trickleHeal: Int
    let scoutHint: String?
    let floatMessage: String?
    let floatColorHex: String
}

/// Resolution of wrong answer penalties and streak preservation.
struct WrongAnswerResolution: Hashable {
    let selfDamage: Int
    let protectStreak: Bool
    let floatMessage: String?
}

/// Combat engine handling unique advantages and limitations for all 27 animal warrior avatars
/// in both Classic Multiplayer/Arena and Single-Player / Subject Test modes.
/// Strictly porting Android's `AvatarCombatEngine.kt`.
final class AvatarCombatEngine {

    let warrior: Warrior
    let maxHp: Int
    var currentHp: Int
    var overguardHp: Int = 0 // Ram: Armor Overguard buffer
    var shieldRoundsActive: Int // Bat: Echo Ward (starts with Round 1 shield)

    // State flags
    var phoenixReviveUsed: Bool = false
    var rhinoShieldTriggered: Bool = false
    var stagHealAccumulated: Int = 0
    var bearGraceUsed: Bool = false
    var stallionStreakProtectionUsed: Bool = false
    var wolfStreakBreakPending: Bool = false
    var lionRushSelfPending: Bool = false
    var scorpionPoisonActive: Bool = false
    var eagleScoutHint: String? = nil
    var ravenLockedThisTurn: Bool = false

    init(warrior: Warrior) {
        self.warrior = warrior
        // Index is 0-based in Android (warrior.id - 1) or 1-based (warrior.id)
        // In Android AvatarManager: 11 is Gorilla, 22 is Fox.
        let idx = warrior.id - 1
        if idx == 11 {
            self.maxHp = 120 // Gorilla: Colossal Frame
        } else if idx == 22 {
            self.maxHp = 90  // Fox: Glass Trickster
        } else {
            self.maxHp = 100
        }
        self.currentHp = self.maxHp
        self.shieldRoundsActive = (idx == 3) ? 1 : 0 // Bat: Echo Ward
    }

    private var avatarIndex: Int {
        warrior.id - 1
    }

    // ─── Timers & Rounds ─────────────────────────────────────────────────────

    func getTimerAdjustmentSeconds() -> Double {
        switch avatarIndex {
        case 4: return -2.0  // Pangolin: Heavy Shell (-2s)
        case 16: return +5.0 // Dolphin: Deep Focus (+5s)
        case 21: return -2.0 // Bear: Drowsy Reflexes (-2s)
        default: return 0.0
        }
    }

    // ─── Power-Up Checks & Usage ─────────────────────────────────────────────

    func getAdrenalineHealAmount() -> Int {
        switch avatarIndex {
        case 0: return 30 // Mantis: Adrenaline Surge (+30 HP)
        case 11: return 10 // Gorilla: Massive Frame (+10 HP)
        default: return 15 // Standard (+15 HP)
        }
    }

    func canActivateAdrenaline() -> (canActivate: Bool, reason: String?) {
        if phoenixReviveUsed {
            return (false, "Phoenix limitation: Powers burned out!")
        }
        if ravenLockedThisTurn {
            return (false, "Raven limitation: Mutual silence active!")
        }
        if avatarIndex == 0 && currentHp >= 50 {
            return (false, "Mantis limitation: HP must be below 50 HP!")
        }
        return (true, nil)
    }

    func getShieldDuration() -> Int {
        switch avatarIndex {
        case 20: return 3 // Elephant: Towering Bastion (3 rounds)
        default: return 2 // Standard (2 rounds)
        }
    }

    func canActivateShield(currentRound: Int) -> (canActivate: Bool, reason: String?) {
        if phoenixReviveUsed {
            return (false, "Phoenix limitation: Powers burned out!")
        }
        if ravenLockedThisTurn {
            return (false, "Raven limitation: Mutual silence active!")
        }
        if avatarIndex == 3 && currentRound < 3 {
            return (false, "Bat limitation: Shield recharges in Round 4!")
        }
        if avatarIndex == 14 && rhinoShieldTriggered {
            return (false, "Rhino limitation: Emergency Plating already spent!")
        }
        return (true, nil)
    }

    func onShieldActivated() {
        if avatarIndex == 2 {
            overguardHp += 10 // Ram: Armor Overguard (+10 buffer)
        }
    }

    func canActivateShock() -> (canActivate: Bool, reason: String?) {
        if phoenixReviveUsed {
            return (false, "Phoenix limitation: Powers burned out!")
        }
        if ravenLockedThisTurn {
            return (false, "Raven limitation: Mutual silence active!")
        }
        return (true, nil)
    }

    func getShockDamage() -> Int {
        switch avatarIndex {
        case 13: return 35 // Leopard: Ambush Strike (35 burst)
        case 17: return 10 // Scorpion: Delayed Impact (10 instant + 4 poison tick)
        default: return 15 // Standard shock
        }
    }

    func canActivateConfuse() -> (canActivate: Bool, reason: String?) {
        if phoenixReviveUsed {
            return (false, "Phoenix limitation: Powers burned out!")
        }
        if ravenLockedThisTurn {
            return (false, "Raven limitation: Mutual silence active!")
        }
        return (true, nil)
    }

    func getConfuseAccuracyPenalty(is1v1Duel: Bool) -> Float {
        switch avatarIndex {
        case 1: return 0.80 // Octopus: Pitch-Black Ink (accuracy drops to 20%)
        case 15: return is1v1Duel ? 0.25 : 0.40 // Chameleon: Diluted Venom in 1v1
        default: return 0.40 // Standard confuse penalty
        }
    }

    // ─── Incoming Damage Handling ────────────────────────────────────────────

    func resolveIncomingDamage(rawDamage: Int) -> DamageResolution {
        if shieldRoundsActive > 0 {
            shieldRoundsActive -= 1
            let reflect = (avatarIndex == 12) ? 10 : 0 // Crocodile: Thornhide Spikes
            let msg = reflect > 0 ? "🛡️ BLOCKED & REFLECTED 10! 🐊" : "🛡️ BLOCKED!"
            return DamageResolution(
                finalDamage: 0,
                blockedByShield: true,
                reflectedDamage: reflect,
                revivedByPhoenix: false,
                emergencyShieldTriggered: false,
                floatMessage: msg,
                floatColorHex: "#00E5FF"
            )
        }

        var dmg = rawDamage

        // Pangolin: Carapace Dampener (-5 incoming damage reduction, min 1)
        if avatarIndex == 4 {
            dmg = max(1, dmg - 5)
        }

        // Crocodile: Exposed Belly (+5 extra damage when shield inactive)
        if avatarIndex == 12 {
            dmg += 5
        }

        // Wolf: Overextended Pack (+5 extra damage on wrong answer after streak break)
        if avatarIndex == 9 && wolfStreakBreakPending {
            dmg += 5
            wolfStreakBreakPending = false
        }

        // Stallion: Fragile Gallop (+5 extra damage after streak protection spent)
        if avatarIndex == 26 && stallionStreakProtectionUsed {
            dmg += 5
        }

        // Tiger: Death Wish (fatal -25 damage when below 30 HP)
        if avatarIndex == 23 && currentHp <= 30 {
            dmg = 25
        }

        // Ram: Overguard buffer absorbs first
        if overguardHp > 0 {
            if overguardHp >= dmg {
                overguardHp -= dmg
                dmg = 0
            } else {
                dmg -= overguardHp
                overguardHp = 0
            }
        }

        currentHp = max(0, currentHp - dmg)

        // Phoenix: Rise from Ashes (revives on 0 HP with 15 HP, burns remaining powers)
        var revived = false
        if currentHp <= 0 && avatarIndex == 8 && !phoenixReviveUsed {
            phoenixReviveUsed = true
            currentHp = 15
            revived = true
        }

        // Rhino: Emergency Plating (auto-shields 1 round when HP <= 30)
        var rhinoPlating = false
        if avatarIndex == 14 && (1...30).contains(currentHp) && !rhinoShieldTriggered {
            rhinoShieldTriggered = true
            shieldRoundsActive = 1
            rhinoPlating = true
        }

        let floatMsg: String
        if revived {
            floatMsg = "🔥 PHOENIX REBIRTH! (+15 HP)"
        } else if rhinoPlating {
            floatMsg = "🦏 EMERGENCY PLATING DEPLOYED!"
        } else if dmg > rawDamage {
            floatMsg = "-\(dmg) DMG (Limitation Penalty)"
        } else if dmg < rawDamage && dmg > 0 {
            floatMsg = "-\(dmg) DMG (Armor Absorbed)"
        } else {
            floatMsg = "-\(dmg) DMG"
        }

        let floatColorHex = revived ? "#FF6F00" : "#FF1744"

        return DamageResolution(
            finalDamage: dmg,
            blockedByShield: false,
            reflectedDamage: 0,
            revivedByPhoenix: revived,
            emergencyShieldTriggered: rhinoPlating,
            floatMessage: floatMsg,
            floatColorHex: floatColorHex
        )
    }

    // ─── Outgoing Attack Resolution ──────────────────────────────────────────

    func resolveOutgoingAttack(
        baseDamage: Int,
        isSpeedBonus: Bool,
        streak: Int,
        targetHp: Int,
        nextCorrectOption: String?
    ) -> AttackResolution {
        var dmg = baseDamage
        var bonusNote = ""

        // Cheetah: Supersonic Blitz (+5 speed strike under 3.0s)
        if avatarIndex == 6 && isSpeedBonus {
            dmg += 5
            bonusNote = "🐆 SPEED STRIKE +5"
        }

        // Vulture: Scavenger Execute (+10 vs <40 HP, -4 vs >70 HP)
        if avatarIndex == 5 {
            if targetHp < 40 {
                dmg += 10
                bonusNote = "🦅 SCAVENGER EXECUTE +10"
            } else if targetHp > 70 {
                dmg = max(1, dmg - 4)
            }
        }

        // Wolf: Pack Escalation (+3 per streak level, max 18)
        if avatarIndex == 9 && streak > 1 {
            let packBonus = min(18, streak * 3)
            dmg += packBonus
            bonusNote = "🐺 PACK ESCALATION +\(packBonus)"
        }

        // Tiger: Berserk Fury (+8 bonus damage while HP <= 30)
        if avatarIndex == 23 && currentHp <= 30 {
            dmg += 8
            bonusNote = "🐅 BERSERK FURY +8"
        }

        // Elephant: Defensive Stance (-5 damage while shield is active)
        if avatarIndex == 20 && shieldRoundsActive > 0 {
            dmg = max(1, dmg - 5)
        }

        // Stag: Verdant Momentum (+4 trickle heal every 2-streak, max 16)
        var heal = 0
        if avatarIndex == 10 && streak > 0 && streak % 2 == 0 {
            if stagHealAccumulated < 16 {
                heal = min(4, 16 - stagHealAccumulated)
                stagHealAccumulated += heal
                currentHp = min(maxHp, currentHp + heal)
            }
        }

        // Eagle: Apex Scout (scouts Top A/B or Bottom C/D for next question)
        var scoutText: String? = nil
        if avatarIndex == 24, let opt = nextCorrectOption {
            let isTop = ["A", "B"].contains(opt.trimmingCharacters(in: .whitespacesAndNewlines).uppercased())
            scoutText = isTop ? "🦅 APEX SCOUT: Answer is in TOP (A or B)" : "🦅 APEX SCOUT: Answer is in BOTTOM (C or D)"
            eagleScoutHint = scoutText
        }

        let msg = !bonusNote.isEmpty ? "\(bonusNote) (Total \(dmg))" : nil

        return AttackResolution(
            totalDamage: dmg,
            trickleHeal: heal,
            scoutHint: scoutText,
            floatMessage: msg,
            floatColorHex: "#00E5FF"
        )
    }

    // ─── Wrong Answer Resolution ─────────────────────────────────────────────

    func resolveWrongAnswer(isSpeedBonus: Bool, priorStreak: Int) -> WrongAnswerResolution {
        var selfDmg = 3
        var protectStreak = false
        var note: String? = nil

        // Cheetah: Reckless Haste (answering wrong in under 3.0s inflicts +10 blunder self-damage)
        if avatarIndex == 6 && isSpeedBonus {
            selfDmg += 10
            note = "🐆 RECKLESS HASTE: +10 Blunder Damage!"
        }

        // Wolf: Marks streak break penalty for subsequent mistake
        if avatarIndex == 9 && priorStreak >= 2 {
            wolfStreakBreakPending = true
        }

        // Stallion: Unbroken Gallop (first wrong answer does not reset streak)
        if avatarIndex == 26 && !stallionStreakProtectionUsed && priorStreak >= 1 {
            stallionStreakProtectionUsed = true
            protectStreak = true
            note = "🐎 UNBROKEN GALLOP: Streak Preserved!"
        }

        // Eagle loses scout view on mistake
        if avatarIndex == 24 {
            eagleScoutHint = nil
        }

        return WrongAnswerResolution(selfDamage: selfDmg, protectStreak: protectStreak, floatMessage: note)
    }

    // ─── End of Round Maintenance ────────────────────────────────────────────

    func onRoundEnd() {
        if avatarIndex == 2 && overguardHp > 0 {
            overguardHp = max(0, overguardHp - 5)
        }
        ravenLockedThisTurn = false
    }
}
