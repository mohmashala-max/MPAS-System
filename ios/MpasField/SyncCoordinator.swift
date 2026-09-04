import Foundation

actor SyncCoordinator {
    private let store: OfflineInspectionStore
    private let api: MpasAPI

    init(store: OfflineInspectionStore, api: MpasAPI) {
        self.store = store
        self.api = api
    }

    func syncPending() async {
        for inspection in await store.pending() {
            do {
                try await api.uploadAndInspect(inspection: inspection)
                try await store.markSynced(inspection.id)
            } catch {
                // Keep the item pending; the next network event retries it.
                continue
            }
        }
    }
}
