package com.smsanalyzer.companion.data

import com.smsanalyzer.companion.data.model.LoginRequest
import com.smsanalyzer.companion.data.model.RegisterRequest
import com.smsanalyzer.companion.data.model.User

class AuthRepository(
    private val apiClient: ApiClient,
    private val tokenStore: TokenStore,
) {
    val isLoggedIn: Boolean get() = tokenStore.isLoggedIn
    val email: String? get() = tokenStore.email

    suspend fun login(email: String, password: String): User {
        val res = apiClient.api.login(LoginRequest(email = email.trim(), password = password))
        tokenStore.token = res.accessToken
        tokenStore.email = res.user.email
        return res.user
    }

    suspend fun register(email: String, password: String, fullName: String?): User {
        val res = apiClient.api.register(
            RegisterRequest(
                email = email.trim(),
                password = password,
                fullName = fullName?.trim()?.ifEmpty { null },
            )
        )
        tokenStore.token = res.accessToken
        tokenStore.email = res.user.email
        return res.user
    }

    suspend fun refreshMe(): User {
        return apiClient.api.me(apiClient.bearer())
    }

    fun logout() {
        tokenStore.clear()
    }
}
