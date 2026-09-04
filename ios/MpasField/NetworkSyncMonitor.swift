import Foundation
import Network

final class NetworkSyncMonitor {
    private let monitor = NWPathMonitor()
    private let queue = DispatchQueue(label: "mpas.network-monitor")
    private let coordinator: SyncCoordinator

    init(coordinator: SyncCoordinator) {
        self.coordinator = coordinator
    }

    func start() {
        monitor.pathUpdateHandler = { [weak self] path in
            guard path.status == .satisfied else { return }
            Task { await self?.coordinator.syncPending() }
        }
        monitor.start(queue: queue)
    }

    func stop() {
        monitor.cancel()
    }
}
