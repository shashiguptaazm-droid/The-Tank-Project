import Foundation

/// A short medical video reel from `api/getReels.php`.
struct Reel: Decodable, Identifiable, Hashable {
    let id: Int
    let videoURL: URL?
    let caption: String
    var likes: Int
    let authorId: Int
    let authorName: String
    let authorPhotoURL: URL?
    var isLiked: Bool = false

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        id = container.flexInt("video_id", "id")
        let rawVideo = container.flexString("video_path", "video_url", "video")
        videoURL = rawVideo.isEmpty ? nil : URL(string: rawVideo)
        caption = container.flexString("caption", "title", "description")
        likes = container.flexInt("likes", "like_count")
        authorId = container.flexInt("user_id", "author_id")
        authorName = container.flexString("name", "author_name", "username")
        let rawPhoto = container.flexString("photo", "avatar", "profile_pic")
        authorPhotoURL = rawPhoto.isEmpty ? nil : URL(string: rawPhoto)
    }

    init(
        id: Int,
        videoURL: URL?,
        caption: String,
        likes: Int = 0,
        authorId: Int = 0,
        authorName: String = "",
        authorPhotoURL: URL? = nil,
        isLiked: Bool = false
    ) {
        self.id = id
        self.videoURL = videoURL
        self.caption = caption
        self.likes = likes
        self.authorId = authorId
        self.authorName = authorName
        self.authorPhotoURL = authorPhotoURL
        self.isLiked = isLiked
    }
}
