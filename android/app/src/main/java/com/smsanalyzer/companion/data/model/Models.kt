package com.smsanalyzer.companion.data.model

import com.squareup.moshi.Json

data class User(
    val id: Int,
    val email: String,
    @Json(name = "full_name") val fullName: String?,
    @Json(name = "is_active") val isActive: Boolean,
    @Json(name = "created_at") val createdAt: String,
)

data class TokenResponse(
    @Json(name = "access_token") val accessToken: String,
    @Json(name = "token_type") val tokenType: String,
    val user: User,
)

data class LoginRequest(
    val email: String,
    val password: String,
)

data class RegisterRequest(
    val email: String,
    val password: String,
    @Json(name = "full_name") val fullName: String? = null,
)

data class RawSmsIn(
    val sender: String,
    val body: String,
    val timestamp: String, // ISO-8601
)

data class CloudSyncRequest(
    val messages: List<RawSmsIn>,
)

data class SyncResponse(
    val scanned: Int,
    val recognized: Int,
    val inserted: Int,
    val duplicates: Int,
    val unknown: Int,
)

/** Local representation of an SMS read from the device inbox. */
data class DeviceSms(
    val sender: String,
    val body: String,
    val timestampMillis: Long,
)
