package com.smsanalyzer.companion.worker

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.smsanalyzer.companion.SmsAnalyzerApp
import java.util.concurrent.TimeUnit

/**
 * Background worker that re-reads SMS and pushes any new mobile-money
 * messages to the cloud backend. Safe to run often — server dedupes.
 */
class SmsSyncWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val app = applicationContext as? SmsAnalyzerApp
            ?: return Result.failure()

        if (!app.tokenStore.isLoggedIn) {
            return Result.success()
        }

        return try {
            app.syncRepository.syncNow()
            Result.success()
        } catch (_: Exception) {
            Result.retry()
        }
    }

    companion object {
        private const val UNIQUE_WORK = "sms_sync_once"

        /** Enqueue a one-shot sync (e.g. after a new SMS arrives). */
        fun enqueue(context: Context, delaySeconds: Long = 5) {
            val request = OneTimeWorkRequestBuilder<SmsSyncWorker>()
                .setInitialDelay(delaySeconds, TimeUnit.SECONDS)
                .build()
            WorkManager.getInstance(context).enqueueUniqueWork(
                UNIQUE_WORK,
                ExistingWorkPolicy.REPLACE,
                request,
            )
        }
    }
}
