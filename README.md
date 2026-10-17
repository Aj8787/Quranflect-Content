# Quranflect Content

Public content delivery for **Quranflect — Swipe, Read, Reflect**. GitHub Pages serves a validated JSON manifest and original card images. The Android app refreshes on app open and optional Firebase messages. Adding cards does not require an Android rebuild or a Play Store update.

The repository starts empty. It contains no prototype cards. Only upload artwork you own or have explicit rights to distribute in an app and allow users to download/share. Magnific prototype illustrations are excluded.

## Upload just a photo

After the one-time setup below:

1. Rename the square original image **24-30-001.jpg**: Surah 24, ayah 30, unique card ID 001. Keep its real extension (`.jpg`, `.png`, or `.webp`).
2. Open **uploads → Add file → Upload files** on GitHub and upload it.
3. Commit to `main`. The workflow generates the metadata, validates the reference and image, and publishes it. Open Quranflect to refresh. No app rebuild or Play update is needed.

For two cards of the same ayah, use `24-30-001.jpg` and `24-30-002.jpg`. Keep an existing filename when updating that card. The original image bytes are preserved for sharing and downloading. Reference/text masks only affect presentation inside the app.

Complete **publisher.json once** with the actual artwork rights holder, the permission/license covering app display, downloads and sharing, and `redistributionAllowed: true`. It starts unconfirmed so the app never makes up ownership or permissions. The default masks match the approved white-background card layout. For different text placements, use a custom `cards/<id>/card.json` based on `card.example.json` instead. No topic/category is required.

Use only artwork you own or are permitted to redistribute in this app. Prototype Magnific images remain excluded. Never upload credentials or signing keys.

## One-time hosting setup

Repository visibility: **Public**. In **Settings → Pages → Build and deployment**, select **GitHub Actions**. Enable Actions. After the workflow finishes, the feed is `https://aj8787.github.io/Quranflect-Content/manifest.json`.

For notifications, add the `FIREBASE_SERVICE_ACCOUNT` Actions secret containing the dedicated Firebase messaging service-account JSON. Keep repository variable `FCM_ENABLED=false` during setup. The account needs **Firebase Cloud Messaging API Admin** (`roles/firebasecloudmessaging.admin`) on project `quranflect` in **Google Cloud → IAM**. The Android repository separately needs `FIREBASE_ANDROID_CONFIG` for package `io.github.aj8787.quranflect`.

In **Actions → Verify Firebase connection → Run workflow**, validate credentials and permission. This workflow always uses `validate_only: true`, independently of `FCM_ENABLED`, and never delivers a notification. After it passes, install the Firebase-configured APK from the private app repository’s **Releases** and opt in under **Settings → New card notifications → Often**. Then set `FCM_ENABLED=true` before uploading a new, properly licensed card to test real delivery.

Normal publication sends to the `cards_often` topic only when new card IDs appear. The weekly workflow sends a digest to `cards_weekly`. Both are opt-in in the app. The separate **Verify Firebase connection** workflow is the setup check. **Publish content** also supports a dry-run input when manually invoked; it only considers card IDs not present in the previous live manifest, so rerunning an unchanged publication does not resend a notification.

## Validate locally

`python3 -m pip install -r requirements.txt`

`python3 scripts/publish.py --output site`

`python3 -m unittest discover -s tests`

Application code, images and Qur’an data have separate rights. Being in this public repository is not a blanket open-source or artwork license. Each card must specify its own rights and attribution.
