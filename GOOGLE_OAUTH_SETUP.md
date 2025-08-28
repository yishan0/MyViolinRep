# Google OAuth Setup Guide

## 1. Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.developers.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Choose "Web application"
6. Add authorized redirect URIs:
   - `http://localhost:5000/google-callback` (for development)
   - `https://yourdomain.com/google-callback` (for production)

## 2. Update Configuration

In `app.py`, replace the placeholder values:

```python
GOOGLE_CLIENT_ID = "your-actual-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "your-actual-client-secret"
GOOGLE_REDIRECT_URI = "http://localhost:5000/google-callback"  # Update for production
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Test the Integration

1. Start your Flask app
2. Go to login/register page
3. Click "Continue with Google"
4. Complete OAuth flow

## Security Notes

- Never commit real credentials to version control
- Use environment variables in production
- Keep your client secret secure
- Regularly rotate credentials
