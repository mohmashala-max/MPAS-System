package com.mpas.mobile.sync

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.mpas.mobile.data.InspectionDao

interface InspectionRemoteDataSource {
    suspend fun upload(inspection: com.mpas.mobile.data.InspectionEntity): Boolean
}

class InspectionSyncWorker(
    appContext: Context,
    params: WorkerParameters,
    private val dao: InspectionDao,
    private val remote: InspectionRemoteDataSource
) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result {
        return runCatching {
            dao.pending().forEach { inspection ->
                if (remote.upload(inspection)) dao.markSynced(inspection.localId)
            }
            Result.success()
        }.getOrElse { Result.retry() }
    }
}
