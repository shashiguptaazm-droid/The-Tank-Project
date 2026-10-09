import SwiftUI

/// Unified search result items mirroring Android `GlobalSearchActivity.kt`.
public enum SearchResultItem: Identifiable, Hashable {
    case question(id: String, text: String, subject: String, image: String)
    case user(id: String, name: String, photo: String, isCloseFriend: Bool)
    case post(id: Int, author: String, authorPhoto: String, caption: String, images: [String], likes: Int, uploadDate: String)
    case topic(name: String, subject: String)
    case video(id: Int, title: String, author: String, authorPhoto: String, videoURL: String, thumbnailURL: String, likes: Int, uploadDate: String)

    public var id: String {
        switch self {
        case let .question(id, _, _, _): return "question_\(id)"
        case let .user(id, _, _, _): return "user_\(id)"
        case let .post(id, _, _, _, _, _, _): return "post_\(id)"
        case let .topic(name, subject): return "topic_\(subject)_\(name)"
        case let .video(id, _, _, _, _, _, _, _): return "video_\(id)"
        }
    }
}

/// Global Search Service matching Android `searchv2.php`, `posts_search.php`, and `user_video_search.php`.
public final class SearchService {

    public static let shared = SearchService()
    private let appSignature = "EduLabsRTM_Secure_v1_2026"
    private let session = URLSession.shared

    private init() {}

    public func searchAll(query: String, userId: Int, goalSubject: String = "NEET PG") async -> [SearchResultItem] {
        guard let encoded = query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed), !encoded.isEmpty else {
            return []
        }

        async let globalTask = fetchSearchV2(keyword: encoded)
        async let postsTask = fetchPosts(keyword: encoded, userId: userId)
        async let topicsTask = fetchTopics(keyword: query, goalSubject: goalSubject)
        async let videosTask = fetchVideos(keyword: encoded, userId: userId)

        let (globalItems, posts, topics, videos) = await (globalTask, postsTask, topicsTask, videosTask)
        return globalItems + topics + posts + videos
    }

    private func fetchSearchV2(keyword: String) async -> [SearchResultItem] {
        guard let url = URL(string: "https://medigyaan.com/Neurons/api/searchv2.php?keyword=\(keyword)&type=json") else { return [] }
        var request = URLRequest(url: url)
        request.setValue(appSignature, forHTTPHeaderField: "X-App-Signature")
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        do {
            let (data, resp) = try await session.data(for: request)
            guard (resp as? HTTPURLResponse)?.statusCode == 200,
                  let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  root["status"] as? String == "success",
                  let results = root["results"] as? [String: Any] else { return [] }

            var items: [SearchResultItem] = []

            if let questions = results["questions"] as? [[String: Any]] {
                for q in questions {
                    let id = "\(q["question_id"] ?? "")"
                    let text = q["question"] as? String ?? ""
                    let subj = q["subject"] as? String ?? ""
                    let img = q["question_image"] as? String ?? ""
                    items.append(.question(id: id, text: text, subject: subj, image: img))
                }
            }

            if let users = results["users"] as? [[String: Any]] {
                for u in users {
                    let id = "\(u["user_id"] ?? "")"
                    let name = u["name"] as? String ?? ""
                    let photo = u["photo"] as? String ?? ""
                    items.append(.user(id: id, name: name, photo: photo, isCloseFriend: false))
                }
            }

            return items
        } catch {
            return []
        }
    }

    private func fetchPosts(keyword: String, userId: Int) async -> [SearchResultItem] {
        guard let url = URL(string: "https://medigyaan.com/Neurons/api/posts_search.php?q=\(keyword)&user_id=\(userId)") else { return [] }
        var request = URLRequest(url: url)
        request.setValue(appSignature, forHTTPHeaderField: "X-App-Signature")

        do {
            let (data, resp) = try await session.data(for: request)
            guard (resp as? HTTPURLResponse)?.statusCode == 200,
                  let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  root["status"] as? String == "success",
                  let posts = root["posts"] as? [[String: Any]] else { return [] }

            return posts.compactMap { post in
                let id = post["post_id"] as? Int ?? 0
                guard id > 0 else { return nil }
                let author = post["author"] as? String ?? "Student"
                let authorPhoto = post["author_photo"] as? String ?? ""
                let caption = post["caption"] as? String ?? ""
                let likes = post["likes"] as? Int ?? 0
                let date = post["upload_date"] as? String ?? ""
                let imgs = (post["images"] as? [String]) ?? []
                return .post(id: id, author: author, authorPhoto: authorPhoto, caption: caption, images: imgs, likes: likes, uploadDate: date)
            }
        } catch {
            return []
        }
    }

    private func fetchTopics(keyword: String, goalSubject: String) async -> [SearchResultItem] {
        guard let encodedSubj = goalSubject.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
              let url = URL(string: "https://medigyaan.com/Neurons/api/getTopics.php?subject=\(encodedSubj)") else { return [] }
        var request = URLRequest(url: url)
        request.setValue(appSignature, forHTTPHeaderField: "X-App-Signature")

        do {
            let (data, resp) = try await session.data(for: request)
            guard (resp as? HTTPURLResponse)?.statusCode == 200,
                  let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let arr = root["data"] as? [Any] else { return [] }

            var topics: [SearchResultItem] = []
            for item in arr {
                let name: String
                if let dict = item as? [String: Any] {
                    name = dict["name"] as? String ?? ""
                } else if let str = item as? String {
                    name = str
                } else {
                    continue
                }

                if name.localizedCaseInsensitiveContains(keyword) {
                    topics.append(.topic(name: name, subject: goalSubject))
                }
            }
            return topics
        } catch {
            return []
        }
    }

    private func fetchVideos(keyword: String, userId: Int) async -> [SearchResultItem] {
        guard let url = URL(string: "https://medigyaan.com/Neurons/api/videos_search.php?q=\(keyword)&user_id=\(userId)") else { return [] }
        var request = URLRequest(url: url)
        request.setValue(appSignature, forHTTPHeaderField: "X-App-Signature")

        do {
            let (data, resp) = try await session.data(for: request)
            guard (resp as? HTTPURLResponse)?.statusCode == 200,
                  let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  root["status"] as? String == "success",
                  let videos = root["videos"] as? [[String: Any]] else { return [] }

            return videos.compactMap { v in
                let id = v["video_id"] as? Int ?? 0
                guard id > 0 else { return nil }
                let title = v["title"] as? String ?? "Clinical Case Reel"
                let author = v["author"] as? String ?? "MediGyaan"
                let authorPhoto = v["author_photo"] as? String ?? ""
                let videoURL = v["video_url"] as? String ?? ""
                let thumbURL = v["thumbnail_url"] as? String ?? ""
                let likes = v["likes"] as? Int ?? 0
                let date = v["upload_date"] as? String ?? ""
                return .video(id: id, title: title, author: author, authorPhoto: authorPhoto, videoURL: videoURL, thumbnailURL: thumbURL, likes: likes, uploadDate: date)
            }
        } catch {
            return []
        }
    }
}
