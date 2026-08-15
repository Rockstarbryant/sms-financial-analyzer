package com.smsanalyzer.companion.data

import android.content.Context
import android.net.Uri
import android.provider.Telephony
import com.smsanalyzer.companion.data.model.DeviceSms
import java.util.Locale

/**
 * Reads SMS from the device inbox and filters to known M-Pesa / Airtel Money senders.
 *
 * Requires READ_SMS permission (and that the user has granted it).
 */
class SmsRepository(private val context: Context) {

    /**
     * Known sender addresses / shortcodes for Kenyan mobile money.
     * Matching is case-insensitive and checks if the sender *contains* any of these.
     */
    private val knownSenders = listOf(
        "MPESA",
        "M-PESA",
        "SAFARICOM",
        "AIRTEL MONEY",
        "AIRTELMONEY",
        "AIRTEL",
    )

    fun readMobileMoneySms(limit: Int = 500): List<DeviceSms> {
        val uri: Uri = Telephony.Sms.Inbox.CONTENT_URI
        val projection = arrayOf(
            Telephony.Sms.ADDRESS,
            Telephony.Sms.BODY,
            Telephony.Sms.DATE,
        )
        val sortOrder = "${Telephony.Sms.DATE} DESC"

        val results = mutableListOf<DeviceSms>()
        context.contentResolver.query(
            uri,
            projection,
            null,
            null,
            sortOrder,
        )?.use { cursor ->
            val idxAddress = cursor.getColumnIndexOrThrow(Telephony.Sms.ADDRESS)
            val idxBody = cursor.getColumnIndexOrThrow(Telephony.Sms.BODY)
            val idxDate = cursor.getColumnIndexOrThrow(Telephony.Sms.DATE)

            while (cursor.moveToNext() && results.size < limit) {
                val sender = cursor.getString(idxAddress)?.trim().orEmpty()
                val body = cursor.getString(idxBody)?.trim().orEmpty()
                val date = cursor.getLong(idxDate)

                if (sender.isEmpty() || body.isEmpty()) continue
                if (!isMobileMoneySender(sender)) continue

                results.add(
                    DeviceSms(
                        sender = sender,
                        body = body,
                        timestampMillis = date,
                    )
                )
            }
        }
        return results
    }

    private fun isMobileMoneySender(sender: String): Boolean {
        val upper = sender.uppercase(Locale.US)
        return knownSenders.any { known -> upper.contains(known) }
    }
}
