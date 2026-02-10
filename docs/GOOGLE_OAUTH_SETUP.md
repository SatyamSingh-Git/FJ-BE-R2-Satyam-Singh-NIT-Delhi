# Google OAuth Setup Guide

To enable Google Sign-In for the Finance Tracker, follow these steps:

## 1. Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Go to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth client ID**
5. Select **Web application**
6. Add authorized redirect URIs:
   - Development: `http://127.0.0.1:8000/accounts/google/login/callback/`
   - Production: `https://yourdomain.com/accounts/google/login/callback/`
7. Copy the **Client ID** and **Client Secret**

## 2. Add Credentials via Django Admin

1. Run the development server: `python manage.py runserver`
2. Go to: `http://127.0.0.1:8000/admin/`
3. Navigate to **Sites** and update the default site:
   - Domain: `127.0.0.1:8000` (dev) or your production domain
   - Display name: Your app name
4. Navigate to **Social Applications** and add a new application:
   - Provider: **Google**
   - Name: `Google OAuth`
   - Client ID: *(paste from Google Console)*
   - Secret Key: *(paste from Google Console)*
   - Sites: Move your site to "Chosen sites"
5. Save

## 3. Test the Integration

1. Visit the login page: `http://127.0.0.1:8000/accounts/login/`
2. Click "Continue with Google"
3. Complete the Google sign-in flow
4. You should be redirected to the dashboard

## Environment Variables (Optional)

For production, you can store credentials in `.env`:

```
GOOGLE_CLIENT_ID=your-client-id-here
GOOGLE_CLIENT_SECRET=your-client-secret-here
```

And load them in Django admin programmatically.

## Troubleshooting

- **"Site matching query does not exist"**: Update the Sites in admin
- **Redirect URI mismatch**: Verify URIs match exactly in Google Console
- **Provider not found**: Ensure `allauth.socialaccount.providers.google` is in INSTALLED_APPS
