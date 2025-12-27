# Firebase Setup Guide for Notifications

This guide will help you set up Firebase Cloud Messaging (FCM) to enable push notifications for your Mufu Farm application.

## Step 1: Create a Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project" or select an existing project
3. Follow the setup wizard to create your project

## Step 2: Enable Cloud Messaging API

1. In your Firebase project, go to **Project Settings** (gear icon)
2. Click on the **Cloud Messaging** tab
3. Make sure Cloud Messaging API is enabled

## Step 3: Generate Service Account Credentials

1. In Firebase Console, go to **Project Settings**
2. Click on the **Service Accounts** tab
3. Click **Generate New Private Key**
4. A JSON file will be downloaded - this is your service account credentials
5. **IMPORTANT**: Keep this file secure and never commit it to version control

## Step 4: Save the Credentials File

1. Copy the downloaded JSON file to your `Farm-backend` directory
2. Rename it to something like `firebase-credentials.json`
3. Example location: `Farm-backend/firebase-credentials.json`

## Step 5: Configure Environment Variable

1. Open the `.env` file in `Farm-backend` directory
2. Set the `FIREBASE_CREDENTIALS_PATH` variable:

```env
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
```

**Note**: Use a relative path from the `Farm-backend` directory, or an absolute path.

**Windows Example:**
```env
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
# OR absolute path:
FIREBASE_CREDENTIALS_PATH=C:\Users\USER\Mufu catfish farm\Farm-backend\firebase-credentials.json
```

**Linux/Mac Example:**
```env
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
# OR absolute path:
FIREBASE_CREDENTIALS_PATH=/home/user/mufu-farm/Farm-backend/firebase-credentials.json
```

## Step 6: Install Firebase Admin SDK

Make sure you have installed the Firebase Admin SDK:

```bash
cd Farm-backend
pip install -r requirements.txt
```

This will install `firebase-admin==6.5.0` along with other dependencies.

## Step 7: Restart the Backend Server

After configuring the credentials, restart your FastAPI server:

```bash
cd Farm-backend
uvicorn app:app --reload --port 8000
```

You should see this message in the console:
```
Firebase Admin SDK initialized successfully
```

## Step 8: Verify Setup

1. Go to the admin dashboard
2. Navigate to the "Notifications" tab
3. Try sending a test notification
4. If configured correctly, you should see a success message

## Troubleshooting

### Error: "Firebase credentials not found"
- Check that the path in `.env` is correct
- Verify the file exists at that location
- Make sure you're using forward slashes `/` or double backslashes `\\` in Windows paths

### Error: "firebase-admin not installed"
- Run: `pip install firebase-admin`
- Or: `pip install -r requirements.txt`

### Error: "Invalid credentials"
- Make sure you downloaded the correct service account JSON file
- Verify the JSON file is not corrupted
- Try downloading a new credentials file from Firebase Console

### Error: "Permission denied"
- Check file permissions on the credentials JSON file
- Make sure the backend process has read access to the file

## Security Notes

⚠️ **IMPORTANT SECURITY CONSIDERATIONS:**

1. **Never commit** the `firebase-credentials.json` file to version control
2. Add it to `.gitignore`:
   ```
   firebase-credentials.json
   *.json
   ```
3. Keep your credentials file secure
4. In production, consider using environment variables or a secrets manager instead of a file

## Frontend Configuration

Make sure your frontend is also configured with Firebase. Check:
- `mufu-farm-ui/src/config/firebase.js` - Should have your Firebase config
- `mufu-farm-ui/.env` - Should have `REACT_APP_FIREBASE_VAPID_KEY`

For more details on frontend Firebase setup, see: `mufu-farm-ui/FCM_SETUP_GUIDE.md`

## Need Help?

If you encounter issues:
1. Check the backend console logs for error messages
2. Verify all paths are correct
3. Ensure Firebase Admin SDK is installed
4. Check that the credentials JSON file is valid

