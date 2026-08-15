# SMS Ledger — Android companion app

Minimal Android app that:

1. Signs in with the **same account** as the web dashboard
2. Requests **READ_SMS** permission
3. Reads only **M-Pesa** and **Airtel Money** messages
4. Uploads them to `POST /api/v1/sync` on your cloud backend
5. Optionally triggers a background sync when a new mobile-money SMS arrives

It is **not** a full finance UI — the web dashboard is the product surface. This app is the SMS bridge for non-technical users.

## Requirements

- Android Studio Ladybug (2024.2+) or newer
- JDK 17
- Android device or emulator (API 26+)
- A running backend with auth + `/api/v1/sync` (see main project README)

## Open the project

```bash
# From the repo root
cd android
# Open this folder in Android Studio: File → Open → select android/
```

Android Studio will download the Gradle wrapper and dependencies on first sync.

## Configure the API URL

In `app/build.gradle.kts`:

| Build type | Default `API_BASE_URL` |
|------------|------------------------|
| `debug` | `http://10.0.2.2:8000` (emulator → host machine) |
| `release` | `https://api.example.com` (change this) |

For a **physical device** on the same Wi‑Fi as your dev machine, use your computer’s LAN IP, e.g. `http://192.168.1.20:8000`.

Backend must allow your origin / cleartext as needed:

- Local: `SMS_ANALYZER_HOST=0.0.0.0` and CORS if you also open the web UI from another host
- Production: HTTPS only; set `SMS_ANALYZER_JWT_SECRET` and `SMS_ANALYZER_CORS_ORIGINS`

## Build & run

1. Start the backend (with a reachable host, not only `127.0.0.1` if using a real phone).
2. In Android Studio: select a device → **Run**.
3. Create an account or sign in (same email/password as the web app).
4. Tap **Grant SMS permission**.
5. Tap **Sync now**.

You should see stats like `Scanned 12 · inserted 8 · duplicates 4 · unrecognized 0`. Open the web dashboard (signed in as the same user) to view the transactions.

## What gets uploaded

Only SMS whose sender address matches known mobile-money patterns:

- `MPESA`, `M-PESA`, `SAFARICOM`
- `AIRTEL`, `AIRTEL MONEY`, `AIRTELMONEY`

Full SMS body + sender + timestamp are sent to the server. The server runs the same parser pipeline as demo/Termux mode and **never** returns raw SMS bodies to the web UI.

## Background sync

- `SmsReceivedReceiver` listens for `SMS_RECEIVED`.
- If the sender looks like mobile money, it enqueues `SmsSyncWorker` after a short delay.
- The worker re-reads the inbox and calls `/api/v1/sync` (dedupe is server-side).

## Project layout

```
android/
├── app/src/main/java/com/smsanalyzer/companion/
│   ├── MainActivity.kt          # Permission + Compose host
│   ├── SmsAnalyzerApp.kt        # DI / singletons
│   ├── data/
│   │   ├── ApiService.kt        # Retrofit + auth header helpers
│   │   ├── AuthRepository.kt
│   │   ├── SmsRepository.kt     # ContentResolver inbox reader
│   │   ├── SyncRepository.kt
│   │   ├── TokenStore.kt        # EncryptedSharedPreferences
│   │   └── model/Models.kt
│   ├── ui/
│   │   ├── AppRoot.kt
│   │   ├── LoginScreen.kt
│   │   ├── HomeScreen.kt
│   │   └── Theme.kt
│   └── worker/
│       ├── SmsSyncWorker.kt
│       └── SmsReceivedReceiver.kt
└── README.md
```

## Privacy notes

- JWT is stored in **EncryptedSharedPreferences**
- HTTP logging is BASIC (no bodies) in debug, off in release
- Only filtered senders are read and uploaded
- Users can sign out from the home screen (clears the token)

## Still optional / later

- Periodic WorkManager schedule (e.g. every 6 hours) as a safety net
- In-app link to open the web dashboard
- Play Store listing + privacy policy for SMS permission declaration
