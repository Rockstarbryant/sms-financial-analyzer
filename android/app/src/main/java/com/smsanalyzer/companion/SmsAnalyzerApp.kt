package com.smsanalyzer.companion

import android.app.Application
import com.smsanalyzer.companion.data.ApiClient
import com.smsanalyzer.companion.data.AuthRepository
import com.smsanalyzer.companion.data.SmsRepository
import com.smsanalyzer.companion.data.SyncRepository
import com.smsanalyzer.companion.data.TokenStore

class SmsAnalyzerApp : Application() {
    lateinit var tokenStore: TokenStore
        private set
    lateinit var apiClient: ApiClient
        private set
    lateinit var authRepository: AuthRepository
        private set
    lateinit var smsRepository: SmsRepository
        private set
    lateinit var syncRepository: SyncRepository
        private set

    override fun onCreate() {
        super.onCreate()
        tokenStore = TokenStore(this)
        apiClient = ApiClient(tokenStore)
        authRepository = AuthRepository(apiClient, tokenStore)
        smsRepository = SmsRepository(this)
        syncRepository = SyncRepository(apiClient, smsRepository)
    }
}
