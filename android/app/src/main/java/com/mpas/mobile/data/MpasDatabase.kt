package com.mpas.mobile.data

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(entities = [InspectionEntity::class], version = 1, exportSchema = false)
abstract class MpasDatabase : RoomDatabase() {
    abstract fun inspectionDao(): InspectionDao
}
