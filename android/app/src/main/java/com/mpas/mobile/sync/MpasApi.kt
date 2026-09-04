package com.mpas.mobile.sync

import com.google.gson.JsonObject
import com.mpas.mobile.data.InspectionEntity
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Multipart
import retrofit2.http.Part
import okhttp3.MultipartBody
import okhttp3.MediaType

interface MpasApi {
    @Multipart
    @POST("api/v1/images")
    suspend fun uploadImage(
        @Header("Authorization") authorization: String,
        @Part image: MultipartBody.Part
    ): Response<JsonObject>

    @FormUrlEncoded
    @POST("api/v1/auth/token")
    suspend fun token(
        @Field("username") username: String,
        @Field("password") password: String
    ): TokenResponse

    @POST("api/v1/ai/inspect")
    suspend fun inspect(
        @Header("Authorization") authorization: String,
        @Body body: JsonObject
    ): Response<JsonObject>
}

data class TokenResponse(
    val access_token: String,
    val token_type: String
)

class HttpInspectionRemoteDataSource(
    private val contentResolver: android.content.ContentResolver,
    baseUrl: String,
    private val accessToken: () -> String = { "" },
) : InspectionRemoteDataSource {
    private companion object {
        const val MAX_IMAGE_BYTES = 10L * 1024L * 1024L
    }

    private val api: MpasApi = Retrofit.Builder()
        .baseUrl(if (baseUrl.endsWith('/')) baseUrl else "$baseUrl/")
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(MpasApi::class.java)

    override suspend fun upload(inspection: InspectionEntity): Boolean {
        val payload = com.google.gson.JsonParser.parseString(inspection.payloadJson).asJsonObject
        val imageUri = android.net.Uri.parse(inspection.imageUri)
        val descriptor = contentResolver.openAssetFileDescriptor(imageUri, "r")
        if (descriptor != null && descriptor.length > MAX_IMAGE_BYTES) {
            descriptor.close()
            return false
        }
        descriptor?.close()
        val stream = contentResolver.openInputStream(imageUri) ?: return false
        val bytes = stream.use { it.readBytes() }
        if (bytes.size > MAX_IMAGE_BYTES) return false
        val mediaType = contentResolver.getType(imageUri)?.let { MediaType.parse(it) }
        val imageBody = okhttp3.RequestBody.create(mediaType, bytes)
        val imagePart = okhttp3.MultipartBody.Part.createFormData("image", "inspection-image", imageBody)
        val upload = api.uploadImage("Bearer ${accessToken()}", imagePart)
        if (!upload.isSuccessful || upload.body() == null) return false
        payload.addProperty("image_uri", upload.body()!!.get("image_uri").asString)
        val response = api.inspect("Bearer ${accessToken()}", payload)
        return response.isSuccessful
    }
}
