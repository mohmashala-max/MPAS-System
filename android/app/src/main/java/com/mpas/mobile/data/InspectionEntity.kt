package com.mpas.mobile.data

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "inspections")
data class InspectionEntity(
    @PrimaryKey val localId: String,
    val facilityId: String,
    val trapId: String,
    val imageUri: String,
    val payloadJson: String,
    val syncState: String = "PENDING",
    val createdAtEpochMs: Long = System.currentTimeMillis()
)
