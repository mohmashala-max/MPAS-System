package com.mpas.mobile.sync

import android.content.Context
import androidx.annotation.Nullable
import androidx.work.ListenableWorker
import androidx.work.WorkerFactory
import androidx.work.WorkerParameters
import com.mpas.mobile.data.InspectionDao

class InspectionWorkerFactory(
    private val dao: InspectionDao,
    private val remote: InspectionRemoteDataSource
) : WorkerFactory() {
    override fun createWorker(
        appContext: Context,
        workerClassName: String,
        workerParameters: WorkerParameters
    ): ListenableWorker? {
        if (workerClassName != InspectionSyncWorker::class.java.name) return null
        return InspectionSyncWorker(appContext, workerParameters, dao, remote)
    }
}
