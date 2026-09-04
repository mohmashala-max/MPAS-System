import Foundation

actor OfflineInspectionStore {
    private let fileURL: URL
    private var inspections: [Inspection] = []

    init(fileManager: FileManager = .default) {
        let base = fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        let directory = base.appendingPathComponent("MpasField", isDirectory: true)
        try? fileManager.createDirectory(at: directory, withIntermediateDirectories: true)
        fileURL = directory.appendingPathComponent("inspections.json")
        inspections = Self.load(fileURL: fileURL)
    }

    func enqueue(facilityId: String, trapId: String, imagePath: String) throws {
        guard !facilityId.isEmpty, !trapId.isEmpty, !imagePath.isEmpty else {
            throw StoreError.invalidInspection
        }
        inspections.append(Inspection(
            id: UUID(),
            facilityId: facilityId,
            trapId: trapId,
            imagePath: imagePath,
            syncState: .pending
        ))
        try persist()
    }

    func pending() -> [Inspection] {
        inspections.filter { $0.syncState == .pending }
    }

    func markSynced(_ id: UUID) throws {
        guard let index = inspections.firstIndex(where: { $0.id == id }) else { return }
        inspections[index].syncState = .synced
        try persist()
    }

    private func persist() throws {
        let data = try JSONEncoder().encode(inspections)
        try data.write(to: fileURL, options: .atomic)
    }

    private static func load(fileURL: URL) -> [Inspection] {
        guard let data = try? Data(contentsOf: fileURL),
              let value = try? JSONDecoder().decode([Inspection].self, from: data) else { return [] }
        return value
    }

    enum StoreError: Error {
        case invalidInspection
    }
}
