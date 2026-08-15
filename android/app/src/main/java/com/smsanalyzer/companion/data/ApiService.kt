package com.smsanalyzer.companion.data

import com.smsanalyzer.companion.BuildConfig
import com.smsanalyzer.companion.data.model.CloudSyncRequest
import com.smsanalyzer.companion.data.model.LoginRequest
import com.smsanalyzer.companion.data.model.RegisterRequest
import com.smsanalyzer.companion.data.model.SyncResponse
import com.smsanalyzer.companion.data.model.TokenResponse
import com.smsanalyzer.companion.data.model.User
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.HttpException
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import java.util.concurrent.TimeUnit

interface ApiService {
    @POST("/api/auth/login")
    suspend fun login(@Body body: LoginRequest): TokenResponse

    @POST("/api/auth/register")
    suspend fun register(@Body body: RegisterRequest): TokenResponse

    @GET("/api/auth/me")
    suspend fun me(@Header("Authorization") bearer: String): User

    @POST("/api/v1/sync")
    suspend fun sync(
        @Header("Authorization") bearer: String,
        @Body body: CloudSyncRequest,
    ): SyncResponse
}

class ApiClient(private val tokenStore: TokenStore) {
    private val moshi = Moshi.Builder()
        .add(KotlinJsonAdapterFactory())
        .build()

    private val logging = HttpLoggingInterceptor().apply {
        // Never log bodies in production — they can contain SMS text
        level = if (BuildConfig.DEBUG) {
            HttpLoggingInterceptor.Level.BASIC
        } else {
            HttpLoggingInterceptor.Level.NONE
        }
    }

    private val authInterceptor = Interceptor { chain ->
        val request = chain.request()
        chain.proceed(request)
    }

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .addInterceptor(logging)
        .addInterceptor(authInterceptor)
        .build()

    val api: ApiService = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL.trimEnd('/') + "/")
        .client(client)
        .addConverterFactory(MoshiConverterFactory.create(moshi))
        .build()
        .create(ApiService::class.java)

    fun bearer(): String {
        val token = tokenStore.token
            ?: throw IllegalStateException("Not logged in")
        return "Bearer $token"
    }

    companion object {
        fun errorMessage(e: Throwable): String {
            return when (e) {
                is HttpException -> {
                    val body = try {
                        e.response()?.errorBody()?.string()
                    } catch (_: Exception) {
                        null
                    }
                    // FastAPI usually returns {"detail": "..."}
                    val detail = body
                        ?.let {
                            Regex("\"detail\"\\s*:\\s*\"([^\"]+)\"").find(it)?.groupValues?.get(1)
                        }
                    detail ?: "Server error (${e.code()})"
                }
                else -> e.message ?: "Network error"
            }
        }
    }
}
