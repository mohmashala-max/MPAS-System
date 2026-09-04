import Foundation

struct Inspection: Codable, Identifiable {
    let id: UUID
    let facilityId: String
    let trapId: String
    let imagePath: String
    var syncState: SyncState

    enum SyncState: String, Codable {
        case pending
        case synced
    }
}
