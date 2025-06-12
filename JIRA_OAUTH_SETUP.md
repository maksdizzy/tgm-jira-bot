# Jira Cloud OAuth 2.0 Setup Instructions

## ✅ WORKING CONFIGURATION

Your bot is now correctly configured and **WORKING** for **Jira Cloud OAuth 2.0 (3LO)**:

- **Jira Instance**: `https://gurunetwork.atlassian.net` ✅
- **Client ID**: `YZUr8XfS3KbmzcBFIF1EVb2c7aZoqOUA` ✅
- **Project Key**: `GNB` ✅
- **Callback URL**: `https://tgbot.maksdizzy.ddns.net/auth/callback` ✅
- **OAuth Flow**: Fixed and working ✅
- **Ticket Creation**: Fixed enum handling ✅

## Authorization Steps

### 1. Start the Bot
```bash
venv\Scripts\python run_dev.py
```

### 2. Visit Authorization URL
Copy and paste this URL in your browser:
```
https://auth.atlassian.com/authorize?response_type=code&client_id=YZUr8XfS3KbmzcBFIF1EVb2c7aZoqOUA&redirect_uri=https%3A%2F%2Ftgbot.maksdizzy.ddns.net%2Fauth%2Fcallback&scope=read%3Ajira-user+read%3Ajira-work+write%3Ajira-work+offline_access&audience=api.atlassian.com&prompt=consent
```

### 3. Grant Permissions
- You'll be redirected to Atlassian's authorization server
- Log in with your Jira account
- Grant the requested permissions:
  - `read:jira-user` - Read user information
  - `read:jira-work` - Read issues and projects
  - `write:jira-work` - Create and update issues
  - `offline_access` - Refresh tokens

### 4. Callback Handling
- After granting permissions, you'll be redirected to: `https://tgbot.maksdizzy.ddns.net/auth/callback`
- The bot will automatically exchange the authorization code for access tokens
- You should see a success message

### 5. Test the Bot
Send a message in Telegram with the format:
```
#ticket Your issue description here
```

## What Changed

### Fixed OAuth 2.0 Implementation
- **Endpoints**: Now using correct Jira Cloud OAuth 2.0 endpoints (`auth.atlassian.com`)
- **Scopes**: Added `offline_access` for refresh token support
- **Parameters**: Added required `audience=api.atlassian.com` parameter
- **Token Exchange**: Updated to use proper Jira Cloud token exchange format

### API Configuration
- **API Version**: Using `/rest/api/3` for Jira Cloud
- **Description Format**: Using Atlassian Document Format (ADF) for ticket descriptions
- **Reporter Field**: Using `accountId` format for Jira Cloud

## Troubleshooting

### If Authorization Fails
1. **Check Callback URL**: Ensure `https://tgbot.maksdizzy.ddns.net/auth/callback` is exactly configured in your Jira app
2. **Verify Client Credentials**: Double-check Client ID and Secret in your `.env` file
3. **Check Bot Status**: Ensure the bot is running and accessible at the callback URL

### If Ticket Creation Fails
1. **Verify Permissions**: Ensure you granted all required scopes
2. **Check Project Access**: Verify you have permission to create issues in project `GNB`
3. **Review Logs**: Check bot logs for detailed error messages

## Next Steps

Once authorized, the bot will:
1. Monitor Telegram messages for `#ticket` hashtag
2. Process content with GPT-4 Turbo
3. Create structured Jira tickets in project `GNB`
4. Respond with ticket links

The OAuth 2.0 integration is now properly configured for Jira Cloud! 🎉