# SAGE ONE — Huawei P40 Pro Development

The Huawei P40 series is an HMS device without Google Mobile Services, so the SAGE ONE development APK uses the explicit local Owner/Developer flow rather than depending on Google Sign-In.

## Connect the phone to the PC

1. Enable Developer options and USB debugging on the Huawei device.
2. Connect the phone by USB.
3. Confirm ADB sees it:

```text
adb devices
```

4. Forward the SAGE backend port from the phone to the PC:

```text
adb reverse tcp:8010 tcp:8010
```

The Huawei development APK is built with:

```text
SAGE_API_URL=http://127.0.0.1:8010
```

so the phone reaches the PC backend through the ADB reverse tunnel.

## Start SAGE

From the canonical backend:

```text
cd C:\SageOne\sage_core
C:\SageOne\Backend\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
```

Then install the GitHub Actions artifact `sage-one-android-release` from the successful **SAGE ONE Android Release** run. It is built for the phone-to-PC ADB reverse tunnel shown above. For an Android emulator, manually run the workflow with `api_url` set to `http://10.0.2.2:8010`.

## Developer flow

The APK uses:

```text
SAGE ONE
  ↓
Enter SAGE Owner Mode
  ↓
Developer identity
  ↓
Owner / God Mode
```

No SMS, OTP, or Google account is required for this private development path.

This is a development-only flow. Production authentication remains separate.
