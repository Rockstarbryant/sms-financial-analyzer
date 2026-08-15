package com.smsanalyzer.companion.worker

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import java.util.Locale

/**
 * Lightweight receiver: when an SMS arrives from a known mobile-money sender,
 * schedule a background sync a few seconds later.
 */
class SmsReceivedReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return

        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent) ?: return
        val known = listOf("MPESA", "M-PESA", "AIRTEL", "SAFARICOM")
        val relevant = messages.any { msg ->
            val from = msg.displayOriginatingAddress?.uppercase(Locale.US).orEmpty()
            known.any { from.contains(it) }
        }
        if (relevant) {
            SmsSyncWorker.enqueue(context, delaySeconds = 8)
        }
    }
}
