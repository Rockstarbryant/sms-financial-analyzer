package com.smsanalyzer.companion.data

import com.smsanalyzer.companion.data.model.CloudSyncRequest
import com.smsanalyzer.companion.data.model.RawSmsIn
import com.smsanalyzer.companion.data.model.SyncResponse
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

class SyncRepository(
    private val apiClient: ApiClient,
    private val smsRepository: SmsRepository,
) {
    /**
     * Read mobile-money SMS from the device and upload them to the cloud backend.
     * Returns the server's sync stats.
     */
    suspend fun syncNow(limit: Int = 500): SyncResponse {
        val deviceMessages = smsRepository.readMobileMoneySms(limit = limit)
        if (deviceMessages.isEmpty()) {
            return SyncResponse(
                scanned = 0,
                recognized = 0,
                inserted = 0,
                duplicates = 0,
                unknown = 0,
            )
        }

        val payload = CloudSyncRequest(
            messages = deviceMessages.map { sms ->
                RawSmsIn(
                    sender = sms.sender,
                    body = sms.body,
                    timestamp = formatIso(sms.timestampMillis),
                )
            }
        )

        return apiClient.api.sync(apiClient.bearer(), payload)
    }

    private fun formatIso(millis: Long): String {
        return Instant.ofEpochMilli(millis)
            .atOffset(ZoneOffset.UTC)
            .format(DateTimeFormatter.ISO_OFFSET_DATE_TIME)
    }
}
