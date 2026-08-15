package com.smsanalyzer.companion.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.smsanalyzer.companion.SmsAnalyzerApp
import com.smsanalyzer.companion.data.ApiClient
import com.smsanalyzer.companion.data.model.SyncResponse
import kotlinx.coroutines.launch

@Composable
fun HomeScreen(
    hasSmsPermission: Boolean,
    onRequestSmsPermission: () -> Unit,
    onLoggedOut: () -> Unit,
) {
    val app = LocalContext.current.applicationContext as SmsAnalyzerApp
    val scope = rememberCoroutineScope()

    var syncing by remember { mutableStateOf(false) }
    var lastResult by remember { mutableStateOf<SyncResponse?>(null) }
    var error by remember { mutableStateOf<String?>(null) }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background,
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text(
                text = "SMS Ledger",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                text = app.authRepository.email ?: "Signed in",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.secondary,
            )

            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column(Modifier.padding(16.dp)) {
                    Text(
                        text = "SMS permission",
                        fontWeight = FontWeight.Medium,
                    )
                    Spacer(Modifier.height(6.dp))
                    if (hasSmsPermission) {
                        Text(
                            text = "Granted. Only M-Pesa and Airtel Money messages are read and uploaded.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.secondary,
                        )
                    } else {
                        Text(
                            text = "Required to read M-Pesa and Airtel Money SMS on this phone.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.secondary,
                        )
                        Spacer(Modifier.height(12.dp))
                        Button(
                            onClick = onRequestSmsPermission,
                            shape = RoundedCornerShape(24.dp),
                        ) {
                            Text("Grant SMS permission")
                        }
                    }
                }
            }

            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column(Modifier.padding(16.dp)) {
                    Text(
                        text = "Sync to cloud",
                        fontWeight = FontWeight.Medium,
                    )
                    Spacer(Modifier.height(6.dp))
                    Text(
                        text = "Reads mobile-money SMS on this device and uploads them to your cloud dashboard. Safe to run often — duplicates are ignored.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.secondary,
                    )
                    Spacer(Modifier.height(12.dp))
                    Button(
                        onClick = {
                            error = null
                            lastResult = null
                            syncing = true
                            scope.launch {
                                try {
                                    lastResult = app.syncRepository.syncNow()
                                } catch (e: Exception) {
                                    error = ApiClient.errorMessage(e)
                                } finally {
                                    syncing = false
                                }
                            }
                        },
                        enabled = hasSmsPermission && !syncing,
                        modifier = Modifier.fillMaxWidth().height(48.dp),
                        shape = RoundedCornerShape(24.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.primary,
                        ),
                    ) {
                        Text(if (syncing) "Syncing…" else "Sync now")
                    }

                    lastResult?.let { r ->
                        Spacer(Modifier.height(12.dp))
                        Text(
                            text = "Scanned ${r.scanned} · inserted ${r.inserted} · duplicates ${r.duplicates} · unrecognized ${r.unknown}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.primary,
                        )
                    }
                    error?.let { msg ->
                        Spacer(Modifier.height(12.dp))
                        Text(
                            text = msg,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.error,
                        )
                    }
                }
            }

            Text(
                text = "New M-Pesa / Airtel messages will also trigger a background sync a few seconds after they arrive.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.secondary,
            )

            Spacer(Modifier.height(8.dp))
            OutlinedButton(
                onClick = {
                    app.authRepository.logout()
                    onLoggedOut()
                },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(24.dp),
            ) {
                Text("Sign out")
            }
        }
    }
}
