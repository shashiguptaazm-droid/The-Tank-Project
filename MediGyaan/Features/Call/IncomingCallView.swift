import SwiftUI

/// Incoming audio / video call full-screen prompt with answer, decline, and ringtone.
///
/// 1:1 port of Android `IncomingCallActivity.kt`.
struct IncomingCallView: View {

    let peerName: String
    let peerAvatar: String
    let isVideo: Bool
    let roomName: String

    var onAccept: (() -> Void)?
    var onDecline: (() -> Void)?

    @Environment(\.dismiss) private var dismiss
    @State private var pulseScale: CGFloat = 1.0

    var body: some View {
        ZStack {
            // Dark gradient backdrop matching Android
            LinearGradient(
                colors: [Color(hex: "#0F172A"), Color(hex: "#020617")],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()

            VStack(spacing: AppTheme.Spacing.xl) {
                Spacer()

                // Caller identity badge
                VStack(spacing: AppTheme.Spacing.md) {
                    ZStack {
                        Circle()
                            .fill(isVideo ? Color.blue.opacity(0.18) : Color.green.opacity(0.18))
                            .frame(width: 140, height: 140)
                            .scaleEffect(pulseScale)
                            .animation(.easeInOut(duration: 1.2).repeatForever(autoreverses: true), value: pulseScale)

                        if let url = URL(string: peerAvatar), !peerAvatar.isEmpty {
                            AsyncImage(url: url) { img in
                                img.resizable().scaledToFill()
                            } placeholder: {
                                Image(systemName: "person.circle.fill")
                                    .font(.system(size: 90))
                                    .foregroundStyle(Color.gray)
                            }
                            .frame(width: 110, height: 110)
                            .clipShape(Circle())
                        } else {
                            Image(systemName: "person.crop.circle.fill")
                                .font(.system(size: 90))
                                .foregroundStyle(Color.gray)
                        }
                    }

                    Text(peerName)
                        .font(.system(size: 28, weight: .bold, design: .rounded))
                        .foregroundStyle(Color.white)

                    HStack(spacing: 6) {
                        Image(systemName: isVideo ? "video.fill" : "phone.fill")
                            .font(.caption)
                        Text(isVideo ? "Incoming Video Call..." : "Incoming Audio Call...")
                            .font(AppTheme.Font.subheadline)
                    }
                    .foregroundStyle(Color.white.opacity(0.75))
                }

                Spacer()

                // Call action triggers
                HStack(spacing: 60) {
                    // Decline Button
                    Button {
                        CallRingtoneManager.shared.stopRinging()
                        onDecline?()
                        dismiss()
                    } label: {
                        VStack(spacing: 8) {
                            ZStack {
                                Circle()
                                    .fill(Color.red)
                                    .frame(width: 72, height: 72)

                                Image(systemName: "phone.down.fill")
                                    .font(.system(size: 28))
                                    .foregroundStyle(Color.white)
                            }

                            Text("Decline")
                                .font(AppTheme.Font.caption.weight(.semibold))
                                .foregroundStyle(Color.white)
                        }
                    }

                    // Accept Button
                    Button {
                        CallRingtoneManager.shared.stopRinging()
                        onAccept?()
                        dismiss()
                    } label: {
                        VStack(spacing: 8) {
                            ZStack {
                                Circle()
                                    .fill(Color.green)
                                    .frame(width: 72, height: 72)

                                Image(systemName: isVideo ? "video.fill" : "phone.fill")
                                    .font(.system(size: 28))
                                    .foregroundStyle(Color.white)
                            }

                            Text("Accept")
                                .font(AppTheme.Font.caption.weight(.semibold))
                                .foregroundStyle(Color.white)
                        }
                    }
                }
                .padding(.bottom, 60)
            }
        }
        .onAppear {
            RemoteLogger.log(tag: "IncomingCall_Ring", message: "Incoming Call alert screen appeared")
            pulseScale = 1.2
            CallRingtoneManager.shared.startRinging()
        }
        .onDisappear {
            CallRingtoneManager.shared.stopRinging()
        }
    }
}
