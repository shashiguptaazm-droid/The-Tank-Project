import SwiftUI

/// In-app Network Inspector View.
/// Displays every network request in real-time, its status code, latency, headers, request payload, and server response.
struct NetworkInspectorView: View {

    @ObservedObject private var logger = APILogger.shared
    @State private var selectedEntry: APILogger.Entry?
    @State private var filter: String = ""

    var filteredEntries: [APILogger.Entry] {
        if filter.isEmpty { return logger.entries }
        return logger.entries.filter {
            $0.url.localizedCaseInsensitiveContains(filter) ||
            $0.method.localizedCaseInsensitiveContains(filter) ||
            String($0.statusCode).contains(filter)
        }
    }

    var body: some View {
        List {
            if logger.entries.isEmpty {
                VStack(spacing: 8) {
                    Image(systemName: "network")
                        .font(.system(size: 32))
                        .foregroundStyle(.secondary)
                    Text("No API calls recorded yet")
                        .font(.headline)
                    Text("Use the app to start capturing live network traffic.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, alignment: .center)
                .padding(.vertical, 40)
            } else {
                ForEach(filteredEntries) { entry in
                    Button {
                        selectedEntry = entry
                    } label: {
                        HStack(alignment: .center, spacing: 10) {
                            Text(entry.method)
                                .font(.system(size: 11, weight: .bold, design: .monospaced))
                                .padding(.horizontal, 6)
                                .padding(.vertical, 3)
                                .background(methodColor(entry.method).opacity(0.18))
                                .foregroundStyle(methodColor(entry.method))
                                .clipShape(RoundedRectangle(cornerRadius: 4))

                            VStack(alignment: .leading, spacing: 3) {
                                Text(displayPath(entry.url))
                                    .font(.system(size: 13, weight: .medium, design: .monospaced))
                                    .lineLimit(1)
                                    .foregroundStyle(.primary)

                                HStack(spacing: 6) {
                                    Text(entry.formattedTime)
                                    Text("·")
                                    Text("\(entry.durationMs)ms")
                                }
                                .font(.system(size: 11))
                                .foregroundStyle(.secondary)
                            }

                            Spacer()

                            Text(entry.statusCode == 0 ? "ERR" : String(entry.statusCode))
                                .font(.system(size: 12, weight: .bold, design: .monospaced))
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(entry.isSuccess ? Color.green.opacity(0.18) : Color.red.opacity(0.18))
                                .foregroundStyle(entry.isSuccess ? Color.green : Color.red)
                                .clipShape(RoundedRectangle(cornerRadius: 4))
                        }
                    }
                }
            }
        }
        .searchable(text: $filter, prompt: "Filter by path or status")
        .navigationTitle("Network Inspector")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Menu {
                    Button(role: .destructive) {
                        logger.clear()
                    } label: {
                        Label("Clear logs", systemImage: "trash")
                    }

                    ShareLink(item: logger.exportJSON()) {
                        Label("Export JSON", systemImage: "square.and.arrow.up")
                    }
                } label: {
                    Image(systemName: "ellipsis.circle")
                }
            }
        }
        .sheet(item: $selectedEntry) { entry in
            NetworkDetailView(entry: entry)
        }
    }

    private func displayPath(_ fullURL: String) -> String {
        guard let url = URL(string: fullURL) else { return fullURL }
        let path = url.path.replacingOccurrences(of: "/Neurons/", with: "")
        if let query = url.query, !query.isEmpty {
            return "\(path)?\(query)"
        }
        return path
    }

    private func methodColor(_ method: String) -> Color {
        switch method.uppercased() {
        case "GET": return .blue
        case "POST": return .green
        case "PUT": return .orange
        case "DELETE": return .red
        default: return .gray
        }
    }
}

/// Detail sheet for an inspected network call
struct NetworkDetailView: View {
    let entry: APILogger.Entry
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                Section("Request") {
                    LabeledContent("Method", value: entry.method)
                    LabeledContent("URL", value: entry.url)
                    LabeledContent("Timestamp", value: entry.formattedTime)
                    LabeledContent("Latency", value: "\(entry.durationMs) ms")
                    LabeledContent("Status", value: String(entry.statusCode))
                }

                Section("Headers") {
                    ForEach(Array(entry.requestHeaders.sorted(by: { $0.key < $1.key })), id: \.key) { k, v in
                        VStack(alignment: .leading, spacing: 2) {
                            Text(k).font(.system(size: 11, weight: .bold, design: .monospaced)).foregroundStyle(.secondary)
                            Text(v).font(.system(size: 12, design: .monospaced))
                        }
                    }
                }

                if let body = entry.requestBody, !body.isEmpty {
                    Section("Request Payload") {
                        Text(body)
                            .font(.system(size: 11, design: .monospaced))
                            .textSelection(.enabled)
                    }
                }

                if let res = entry.responseBody, !res.isEmpty {
                    Section("Response Body") {
                        Text(res)
                            .font(.system(size: 11, design: .monospaced))
                            .textSelection(.enabled)
                    }
                }

                if let err = entry.error {
                    Section("Error") {
                        Text(err)
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(.red)
                    }
                }
            }
            .navigationTitle(entry.method)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") { dismiss() }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    ShareLink(item: "\(entry.method) \(entry.url)\nStatus: \(entry.statusCode)\n\nResponse:\n\(entry.responseBody ?? "")") {
                        Image(systemName: "square.and.arrow.up")
                    }
                }
            }
        }
    }
}
