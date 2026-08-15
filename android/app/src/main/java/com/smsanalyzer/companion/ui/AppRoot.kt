package com.smsanalyzer.companion.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import com.smsanalyzer.companion.SmsAnalyzerApp

@Composable
fun AppRoot(
    hasSmsPermission: Boolean,
    onRequestSmsPermission: () -> Unit,
) {
    val app = LocalContext.current.applicationContext as SmsAnalyzerApp
    var loggedIn by remember { mutableStateOf(app.authRepository.isLoggedIn) }

    if (loggedIn) {
        HomeScreen(
            hasSmsPermission = hasSmsPermission,
            onRequestSmsPermission = onRequestSmsPermission,
            onLoggedOut = { loggedIn = false },
        )
    } else {
        LoginScreen(
            onLoggedIn = { loggedIn = true },
        )
    }
}
