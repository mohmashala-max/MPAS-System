package com.mpas.mobile

import android.app.Application
import androidx.work.Configuration
import androidx.work.WorkManager
import com.mpas.mobile.data.MpasDatabase
import com.mpas.mobile.sync.HttpInspectionRemoteDataSource
import com.mpas.mobile.sync.InspectionWorkerFactory
import com.mpas.mobile.sync.scheduleInspectionSync

class MpasApplication : Application(), Configuration.Provider {
    val database by lazy { MpasDatabaseProvider.create(this) }

    override fun onCreate() {
        super.onCreate()
        scheduleInspectionSync(WorkManager.getInstance(this))
    }

    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder()
            .setWorkerFactory(
                InspectionWorkerFactory(
                    database.inspectionDao(),
                    HttpInspectionRemoteDataSource(contentResolver, BuildConfig.MPAS_API_BASE_URL) {
                        getSharedPreferences("mpas_auth", MODE_PRIVATE)
                            .getString("access_token", "")
                            .orEmpty()
                    }
                )
            )
            .build()
}

private object MpasDatabaseProvider {
    fun create(application: Application): MpasDatabase =
        androidx.room.Room.databaseBuilder(application, MpasDatabase::class.java, "mpas.db").build()
}
