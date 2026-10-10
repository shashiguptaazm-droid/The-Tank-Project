import SwiftUI

/// Full-screen zoomable image viewer with download to photo library and share sheet.
///
/// 1:1 port of Android `FullScreenImageActivity.kt`.
struct FullScreenImageView: View {

    let imageURL: URL?
    var placeholderSystemImage: String = "photo"

    @Environment(\.dismiss) private var dismiss
    @State private var scale: CGFloat = 1.0
    @State private var lastScale: CGFloat = 1.0
    @State private var offset: CGSize = .zero
    @State private var lastOffset: CGSize = .zero
    @State private var isSharing = false
    @State private var showSavedNotification = false

    var body: some View {
        ZStack {
            Color.black
                .ignoresSafeArea()

            // Main Zoomable Image
            if let imageURL = imageURL {
                AsyncImage(url: imageURL) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .scaledToFit()
                            .scaleEffect(scale)
                            .offset(offset)
                            .gesture(
                                MagnificationGesture()
                                    .onChanged { value in
                                        scale = lastScale * value
                                    }
                                    .onEnded { _ in
                                        if scale < 1.0 {
                                            scale = 1.0
                                            offset = .zero
                                        }
                                        lastScale = scale
                                    }
                            )
                            .simultaneousGesture(
                                DragGesture()
                                    .onChanged { value in
                                        offset = CGSize(
                                            width: lastOffset.width + value.translation.width,
                                            height: lastOffset.height + value.translation.height
                                        )
                                    }
                                    .onEnded { _ in
                                        lastOffset = offset
                                    }
                            )
                            .onTapGesture(count: 2) {
                                withAnimation {
                                    if scale > 1.0 {
                                        scale = 1.0
                                        offset = .zero
                                    } else {
                                        scale = 2.5
                                    }
                                    lastScale = scale
                                    lastOffset = offset
                                }
                            }
                    case .failure:
                        VStack(spacing: 8) {
                            Image(systemName: "exclamationmark.triangle")
                                .font(.largeTitle)
                                .foregroundStyle(Color.gray)
                            Text("Failed to load image")
                                .font(.caption)
                                .foregroundStyle(Color.gray)
                        }
                    case .empty:
                        ProgressView()
                            .tint(.white)
                    @unknown default:
                        EmptyView()
                    }
                }
            } else {
                Image(systemName: placeholderSystemImage)
                    .font(.system(size: 64))
                    .foregroundStyle(Color.gray)
            }

            // Top Action Bar overlay
            VStack {
                HStack {
                    Button {
                        dismiss()
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .bold))
                            .foregroundStyle(Color.white)
                            .padding(10)
                            .background(Circle().fill(Color.black.opacity(0.6)))
                    }

                    Spacer()

                    if let imageURL = imageURL {
                        ShareLink(item: imageURL) {
                            Image(systemName: "square.and.arrow.up")
                                .font(.system(size: 16, weight: .bold))
                                .foregroundStyle(Color.white)
                                .padding(10)
                                .background(Circle().fill(Color.black.opacity(0.6)))
                        }
                    }
                }
                .padding()

                Spacer()
            }
        .onAppear {
            RemoteLogger.log(tag: "FullScreenImage_Open", message: "Full screen medical image preview opened")
        }
        }
    }
}