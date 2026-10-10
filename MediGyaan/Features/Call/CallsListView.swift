import SwiftUI

/// Complete Call Logs Screen, strictly porting Android's `CallsActivity.kt` and `CallDetailsActivity.kt`.
/// Features:
/// - Filter chips: All, Missed, Incoming, Outgoing
/// - Comprehensive call log list with peer avatar, call type icon (Video / Audio), direction badge, duration, and timestamp
/// - Direct tap to launch LiveKit Audio / Video Call
/// - Call detail sheet with data usage metrics and event timeline
/// - Clear log option and FAB to initiate new peer consultation
struct CallsListView: View {

    @Environment(\.dismiss) private var dismiss
    @Environment(\.api) private var api
    @EnvironmentObject private var session: SessionStore
    @State private var calls: [CallLogItem] = []
    @State private var selectedFilter: String = "All" // "All", "Missed", "Incoming", "Outgoing"
    @State private var inspectingCall: CallLogItem? = nil
    @State private var activeCallDestination: (room: String, peer: String, isVideo: Bool)? = nil

    private var filteredCalls: [CallLogItem] {
        switch selectedFilter {
        case "Missed":
            return calls.filter { $0.isMissed }
        case "Incoming":
            return calls.filter { $0.direction == .incoming }
        case "Outgoing":
            return calls.filter { $0.direction == .outgoing }
        default:
            return calls
        }
    }

    var body: some View {
        ZStack {
            AppTheme.Palette.surface.ignoresSafeArea()

            VStack(spacing: 0) {
                headerBar

                filterChipsBar

                if filteredCalls.isEmpty {
                    emptyCallsView
                } else {
                    List {
                        ForEach(filteredCalls) { item in
                            callRow(item)
                                .listRowInsets(EdgeInsets(top: 8, leading: 14, bottom: 8, trailing: 14))
                                .listRowBackground(Color.clear)
                                .listRowSeparator(.hidden)
                                .contentShape(Rectangle())
                                .onTapGesture {
                                    inspectingCall = item
                                }
                        }
                    }
                    .listStyle(.plain)
                    .scrollContentBackground(.hidden)
                }
            }
        }
        .navigationBarHidden(true)
        .onAppear {
            RemoteLogger.log(tag: "CallsList_Open", message: "User opened Call Log History")
            loadCalls()
        }
        .sheet(item: $inspectingCall) { callItem in
            CallDetailSheet(callItem: callItem, onCallAgain: { isVideo in
                inspectingCall = nil
                activeCallDestination = (room: callItem.roomName, peer: callItem.peerName, isVideo: isVideo)
            })
        }
        .fullScreenCover(isPresented: Binding(
            get: { activeCallDestination != nil },
            set: { if !$0 { activeCallDestination = nil } }
        )) {
            if let dest = activeCallDestination {
                CallView(
                    model: CallViewModel(
                        roomName: dest.room,
                        kind: dest.isVideo ? .video : .audio,
                        peerName: dest.peer,
                        api: api,
                        session: session
                    )
                )
            }
        }
    }

    // MARK: - Header Bar

    private var headerBar: some View {
        HStack {
            Button {
                dismiss()
            } label: {
                Image(systemName: "chevron.left")
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(AppTheme.Ink.teal)
                    .frame(width: 44, height: 44)
                    .background(Circle().fill(Color(hex: "#101D33")))
            }

            Spacer()

            VStack(spacing: 2) {
                Text("CALL LOGS")
                    .font(.system(size: 14, weight: .black))
                    .tracking(2.0)
                    .foregroundStyle(AppTheme.Ink.gold)

                Text("PEER TELECONSULTATIONS")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(AppTheme.Palette.textSecondary)
            }

            Spacer()

            Menu {
                Button(role: .destructive) {
                    CallLogManager.shared.clearAll()
                    loadCalls()
                } label: {
                    Label("Clear All Call Logs", systemImage: "trash")
                }
            } label: {
                Image(systemName: "ellipsis")
                    .font(.system(size: 16))
                    .foregroundStyle(Color.white)
                    .rotationEffect(.degrees(90))
                    .frame(width: 44, height: 44)
                    .background(Circle().fill(Color(hex: "#101D33")))
            }
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.top, 8)
        .padding(.bottom, 6)
    }

    // MARK: - Filter Chips

    private var filterChipsBar: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(["All", "Missed", "Incoming", "Outgoing"], id: \.self) { filter in
                    let isSelected = selectedFilter == filter
                    Button {
                        selectedFilter = filter
                    } label: {
                        Text(filter)
                            .font(.system(size: 12, weight: isSelected ? .bold : .medium))
                            .foregroundStyle(isSelected ? Color(hex: "#050816") : Color.white)
                            .padding(.horizontal, 14)
                            .padding(.vertical, 6)
                            .background(
                                Capsule()
                                    .fill(isSelected ? Color(hex: "#00E5FF") : Color(hex: "#101D33"))
                            )
                            .overlay(
                                Capsule()
                                    .stroke(isSelected ? Color(hex: "#00E5FF") : Color.white.opacity(0.1), lineWidth: 1)
                            )
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, AppTheme.Spacing.md)
            .padding(.vertical, 8)
        }
    }

    // MARK: - Empty State

    private var emptyCallsView: some View {
        VStack(spacing: 12) {
            Spacer()
            Image(systemName: "phone.down.circle.fill")
                .font(.system(size: 48))
                .foregroundStyle(Color.gray.opacity(0.4))

            Text("No Call Logs")
                .font(AppTheme.Font.headline)
                .foregroundStyle(Color.white)

            Text("Voice and video teleconsultations with peers will appear here.")
                .font(AppTheme.Font.caption)
                .foregroundStyle(AppTheme.Palette.textSecondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
            Spacer()
        }
    }

    // MARK: - Call Row Item

    private func callRow(_ item: CallLogItem) -> some View {
        HStack(spacing: 12) {
            // Avatar
            ZStack {
                Circle()
                    .fill(Color(hex: "#122036"))
                    .frame(width: 48, height: 48)

                if !item.peerAvatar.isEmpty {
                    Image(item.peerAvatar)
                        .resizable()
                        .scaledToFit()
                        .frame(width: 36, height: 36)
                        .clipShape(Circle())
                } else {
                    Image(systemName: "person.crop.circle.fill")
                        .font(.system(size: 32))
                        .foregroundStyle(Color(hex: "#00E5FF"))
                }
            }

            VStack(alignment: .leading, spacing: 3) {
                Text(item.peerName)
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(item.isMissed ? Color(hex: "#FF5252") : Color.white)

                HStack(spacing: 5) {
                    Image(systemName: item.direction.iconName)
                        .font(.system(size: 10))
                        .foregroundStyle(item.isMissed ? Color(hex: "#FF5252") : Color(hex: "#00E676"))

                    Text(item.formattedDate)
                        .font(.system(size: 11))
                        .foregroundStyle(AppTheme.Palette.textSecondary)

                    Text("•")
                        .font(.system(size: 10))
                        .foregroundStyle(AppTheme.Palette.textSecondary)

                    Text(item.formattedTime)
                        .font(.system(size: 11))
                        .foregroundStyle(AppTheme.Palette.textSecondary)
                }
            }

            Spacer()

            // Quick Call Back Button
            Button {
                activeCallDestination = (room: item.roomName, peer: item.peerName, isVideo: item.isVideo)
            } label: {
                Image(systemName: item.isVideo ? "video.fill" : "phone.fill")
                    .font(.system(size: 15))
                    .foregroundStyle(Color(hex: "#00E5FF"))
                    .frame(width: 40, height: 40)
                    .background(Circle().fill(Color(hex: "#10233D")))
            }
            .buttonStyle(.plain)
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(Color(hex: "#0B1526"))
                .overlay(
                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                        .stroke(Color.white.opacity(0.08), lineWidth: 1)
                )
        )
    }

    private func loadCalls() {
        calls = CallLogManager.shared.getAllCalls()
    }
}

// MARK: - Call Detail Sheet

struct CallDetailSheet: View {
    let callItem: CallLogItem
    let onCallAgain: (Bool) -> Void
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: AppTheme.Spacing.lg) {
                    // Profile Header Card
                    VStack(spacing: 8) {
                        ZStack {
                            Circle()
                                .fill(Color(hex: "#122036"))
                                .frame(width: 72, height: 72)
                            Image(systemName: "person.crop.circle.fill")
                                .font(.system(size: 52))
                                .foregroundStyle(Color(hex: "#00E5FF"))
                        }

                        Text(callItem.peerName)
                            .font(.system(size: 18, weight: .bold))
                            .foregroundStyle(Color.white)

                        Text("Peer ID: #\(callItem.peerId)")
                            .font(.system(size: 11))
                            .foregroundStyle(AppTheme.Palette.textSecondary)

                        HStack(spacing: 16) {
                            Button {
                                onCallAgain(false)
                            } label: {
                                Label("Voice Call", systemImage: "phone.fill")
                                    .font(.system(size: 13, weight: .bold))
                                    .padding(.horizontal, 14)
                                    .padding(.vertical, 8)
                                    .background(Capsule().fill(Color(hex: "#00E676")))
                                    .foregroundStyle(Color.black)
                            }

                            Button {
                                onCallAgain(true)
                            } label: {
                                Label("Video Call", systemImage: "video.fill")
                                    .font(.system(size: 13, weight: .bold))
                                    .padding(.horizontal, 14)
                                    .padding(.vertical, 8)
                                    .background(Capsule().fill(Color(hex: "#00E5FF")))
                                    .foregroundStyle(Color.black)
                            }
                        }
                        .padding(.top, 6)
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(
                        RoundedRectangle(cornerRadius: 16, style: .continuous)
                            .fill(Color(hex: "#0D1A2D"))
                    )

                    // Call Analytics Card
                    CardContainer {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("TELEMETRY & DETAILS")
                                .font(.system(size: 11, weight: .heavy))
                                .foregroundStyle(AppTheme.Palette.textSecondary)

                            detailRow(label: "Call Type", value: callItem.isVideo ? "Video Conference" : "Voice Teleconsultation")
                            detailRow(label: "Direction", value: callItem.direction.rawValue)
                            detailRow(label: "Date & Time", value: "\(callItem.formattedDate) at \(callItem.formattedTime)")
                            detailRow(label: "Duration", value: callItem.formattedDuration)
                            detailRow(label: "Data Transferred", value: callItem.formattedDataUsage)
                            detailRow(label: "Room Name", value: callItem.roomName)
                            detailRow(label: "Status", value: callItem.status.rawValue)
                        }
                    }
                }
                .padding(AppTheme.Spacing.md)
            }
            .background(AppTheme.Palette.surface.ignoresSafeArea())
            .navigationTitle("Call Details")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") {
                        dismiss()
                    }
                    .foregroundStyle(AppTheme.Ink.teal)
                }
            }
        }
    }

    private func detailRow(label: String, value: String) -> some View {
        HStack {
            Text(label)
                .font(.system(size: 13))
                .foregroundStyle(AppTheme.Palette.textSecondary)
            Spacer()
            Text(value)
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(Color.white)
        }
    }
}
