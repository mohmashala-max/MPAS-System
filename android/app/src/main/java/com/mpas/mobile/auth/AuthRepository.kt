package com.mpas.mobile.auth

import android.content.Context
import com.mpas.mobile.sync.MpasApi
import com.mpas.mobile.sync.TokenResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class AuthRepository(context: Context, baseUrl: String) {
    private val preferences = context.getSharedPreferences("mpas_auth", Context.MODE_PRIVATE)
    private val api: MpasApi = Retrofit.Builder()
        .baseUrl(if (baseUrl.endsWith('/')) baseUrl else "$baseUrl/")
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(MpasApi::class.java)

    suspend fun login(username: String, password: String): Result<TokenResponse> = withContext(Dispatchers.IO) {
        runCatching {
            api.token(username, password).also { response ->
                preferences.edit().putString("access_token", response.access_token).apply()
            }
        }
    }

    fun logout() {
        preferences.edit().remove("access_token").apply()
    }
}
