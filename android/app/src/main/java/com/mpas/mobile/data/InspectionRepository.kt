package com.mpas.mobile.data

import java.util.UUID
import org.json.JSONArray
import org.json.JSONObject

class InspectionRepository(private val dao: InspectionDao) {
    suspend fun queue(facilityId: String, trapId: String, imageUri: String) {
        val payload = JSONObject()
            .put("facility_id", facilityId)
            .put("trap_id", trapId)
            .put("image_uri", imageUri)
            .put("threshold", 5)
            .put("detections", JSONArray())
        dao.insert(
            InspectionEntity(
                localId = UUID.randomUUID().toString(),
                facilityId = facilityId,
                trapId = trapId,
                imageUri = imageUri,
                payloadJson = payload.toString()
            )
        )
    }
}
