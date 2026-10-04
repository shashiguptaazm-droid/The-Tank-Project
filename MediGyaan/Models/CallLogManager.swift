import Foundation

/// Direction of a call item.
enum CallDirection: String, Codable, CaseIterable {
    case incoming = "INCOMING"
    case outgoing = "OUTGOING"
    case missed = "MISSED"

    var iconName: String {
        switch self {
        case .incoming: return "phone.arrow.down.left.fill"
        case .outgoing: return "phone.arrow.up.right.fill"
        case .missed: return "phone.arrow.down.left.fill"
        }
    }
}

/// Final status of a call attempt.
enum CallStatus: String, Codable, CaseIterable {
    case connected = "CONNECTED"
    case missed = "MISSED"
    case declined = "DECLINED"
    case noAnswer = "NO_ANSWER"
}

/// Call Log record strictly porting Android's `CallLogItem.kt`.
struct CallLogItem: Identifiable, Codable, Hashable {
    let id: String
    let peerId: Int
    let peerName: String
    let peerAvatar: String
    let roomName: String
    let callType: String // "AUDIO" or "VIDEO"
    let direction: CallDirection
    let timestamp: Int64
    var durationSeconds: Int
    var dataUsageBytes: Int64
    var status: CallStatus

    var isVideo: Bool {
        callType.uppercased() == "VIDEO"
    }

    var isMissed: Bool {
        direction == .missed || status == .missed
    }

    var isIncoming: Bool {
        direction == .incoming
    }

    init(
        id: String = UUID().uuidString,
        peerId: Int,
        peerName: String,
        peerAvatar: String = "",
        roomName: String,
        callType: String = "AUDIO",
        direction: CallDirection = .outgoing,
        timestamp: Int64 = Int64(Date().timeIntervalSince1970 * 1000),
        durationSeconds: Int = 0,
        dataUsageBytes: Int64 = 0,
        status: CallStatus = .connected
    ) {
        self.id = id
        self.peerId = peerId
        self.peerName = peerName
        self.peerAvatar = peerAvatar
        self.roomName = roomName
        self.callType = callType
        self.direction = direction
        self.timestamp = timestamp
        self.durationSeconds = durationSeconds
        self.dataUsageBytes = dataUsageBytes
        self.status = status
    }

    var formattedTime: String {
        let date = Date(timeIntervalSince1970: Double(timestamp) / 1000.0)
        let formatter = DateFormatter()
        formatter.dateFormat = "h:mm a"
        return formatter.string(from: date)
    }

    var formattedDate: String {
        let date = Date(timeIntervalSince1970: Double(timestamp) / 1000.0)
        if Calendar.current.isDateInToday(date) {
            return "Today"
        } else if Calendar.current.isDateInYesterday(date) {
            return "Yesterday"
        } else {
            let formatter = DateFormatter()
            formatter.dateFormat = "MMMM d, yyyy"
            return formatter.string(from: date)
        }
    }

    var formattedDuration: String {
        let mins = durationSeconds / 60
        let secs = durationSeconds % 60
        if mins > 0 {
            return "\(mins) min \(secs) sec"
        } else {
            return "\(secs) sec"
        }
    }

    var formattedDataUsage: String {
        if dataUsageBytes >= 1_048_576 {
            return String(format: "%.1f MB", Double(dataUsageBytes) / 1_048_576.0)
        } else if dataUsageBytes >= 1024 {
            return String(format: "%.1f KB", Double(dataUsageBytes) / 1024.0)
        } else {
            return "\(dataUsageBytes) B"
        }
    }
}

/// Call Log local storage & management, strictly porting Android's `CallLogManager.kt`.
final class CallLogManager {

    static let shared = CallLogManager()

    private let userDefaultsKey = "MEDIGYAAN_CALL_LOGS_ARRAY"

    private init() {}

    func getAllCalls() -> [CallLogItem] {
        guard let data = UserDefaults.standard.data(forKey: userDefaultsKey),
              let list = try? JSONDecoder().decode([CallLogItem].self, from: data) else {
            let defaults = generateSampleCalls()
            saveCalls(defaults)
            return defaults
        }
        return list.sorted { $0.timestamp > $1.timestamp }
    }

    func getCallsForPeer(peerId: Int) -> [CallLogItem] {
        getAllCalls().filter { $0.peerId == peerId }
    }

    func getCallById(_ callId: String) -> CallLogItem? {
        getAllCalls().first { $0.id == callId }
    }

    func addCall(_ item: CallLogItem) {
        var list = getAllCalls()
        list.removeAll { $0.id == item.id }
        list.insert(item, at: 0)
        saveCalls(list)
    }

    func deleteCall(callId: String) {
        var list = getAllCalls()
        list.removeAll { $0.id == callId }
        saveCalls(list)
    }

    func clearAll() {
        saveCalls([])
    }

    private func saveCalls(_ calls: [CallLogItem]) {
        if let data = try? JSONEncoder().encode(calls) {
            UserDefaults.standard.set(data, forKey: userDefaultsKey)
        }
    }

    private func generateSampleCalls() -> [CallLogItem] {
        let now = Int64(Date().timeIntervalSince1970 * 1000)
        let hour = Int64(3600 * 1000)
        let day = Int64(86400 * 1000)

        return [
            CallLogItem(
                peerId: 101,
                peerName: "Dr. Ananya Sharma",
                peerAvatar: "avatar_01",
                roomName: "edu_lab_rtm_101_demo",
                callType: "VIDEO",
                direction: .incoming,
                timestamp: now - hour * 2,
                durationSeconds: 312,
                dataUsageBytes: 15_240_000,
                status: .connected
            ),
            CallLogItem(
                peerId: 102,
                peerName: "Dr. Rohan Verma",
                peerAvatar: "avatar_02",
                roomName: "edu_lab_rtm_102_demo",
                callType: "AUDIO",
                direction: .outgoing,
                timestamp: now - hour * 5,
                durationSeconds: 145,
                dataUsageBytes: 1_280_000,
                status: .connected
            ),
            CallLogItem(
                peerId: 103,
                peerName: "Dr. Priya Nair",
                peerAvatar: "avatar_03",
                roomName: "edu_lab_rtm_103_demo",
                callType: "VIDEO",
                direction: .missed,
                timestamp: now - day,
                durationSeconds: 0,
                dataUsageBytes: 0,
                status: .missed
            )
        ]
    }
}
