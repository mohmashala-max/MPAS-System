package com.mpas.mobile.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query

@Dao
interface InspectionDao {
    @Insert
    suspend fun insert(inspection: InspectionEntity)

    @Query("SELECT * FROM inspections WHERE syncState = 'PENDING' ORDER BY createdAtEpochMs LIMIT 50")
    suspend fun pending(): List<InspectionEntity>

    @Query("UPDATE inspections SET syncState = 'SYNCED' WHERE localId = :localId")
    suspend fun markSynced(localId: String)
}
