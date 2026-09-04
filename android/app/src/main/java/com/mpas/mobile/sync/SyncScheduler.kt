package com.mpas.mobile.sync

import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

fun scheduleInspectionSync(workManager: WorkManager) {
    val constraints = Constraints.Builder()
        .setRequiredNetworkType(NetworkType.CONNECTED)
        .build()
    val request = PeriodicWorkRequestBuilder<InspectionSyncWorker>(15, TimeUnit.MINUTES)
        .setConstraints(constraints)
        .build()
    workManager.enqueueUniquePeriodicWork(
        "mpas-inspection-sync",
        ExistingPeriodicWorkPolicy.KEEP,
        request
    )
}

fun enqueueInspectionSync(workManager: WorkManager) {
    val constraints = Constraints.Builder()
        .setRequiredNetworkType(NetworkType.CONNECTED)
        .build()
    val request = OneTimeWorkRequestBuilder<InspectionSyncWorker>()
        .setConstraints(constraints)
        .build()
    workManager.enqueue(request)
}
