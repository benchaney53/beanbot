# Bean Bot - Discord Bot

A Python Discord bot built with discord.py featuring Google Sheets integration, member synchronization, and Dyno application management with a modular cog system.

## Features

- **Google Sheets Integration**: Read and display data from Google Sheets
- **Member Synchronization**: Sync Discord server members to Google Sheets with detailed role tracking
- **Dyno Application Management**: Handle application approvals/rejections with thread-based workflow
- **Slash Commands**: Modern Discord slash command support
- **Modular Cog System**: Easy extension with automatic cog discovery
- **Environment-based Configuration**: Secure configuration management
- **Error Handling and Logging**: Comprehensive error handling
- **Interactive Setup**: Easy configuration with step-by-step setup commands

## Setup Instructions

### 1. Prerequisites

- Python 3.8 or higher
- A Discord application and bot token
- A Google Cloud Project with Sheets API enabled
- Google Service Account credentials

### 2. Virtual Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Google Sheets Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API
4. Create a Service Account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Give it a name and description
   - Click "Create and Continue"
   - Skip the optional steps and click "Done"
5. Create credentials for the Service Account:
   - Click on the created service account
   - Go to the "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose "JSON" format
   - Download the JSON file and rename it to `google_credentials.json`
   - Place it in the project root directory
6. Share your Google Sheet with the service account email (found in the JSON file)

### 5. Discord Bot Setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to the "Bot" section and create a bot
4. Copy the bot token
5. Create a `.env` file in the project root:

```env
DISCORD_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=your_guild_id_here
DISCORD_CLIENT_ID=your_client_id_here
GOOGLE_CREDENTIALS_FILE=google_credentials.json
GOOGLE_SHEET_ID=your_google_sheet_id_here

# Dyno Applications Configuration (Optional - can be set via !dynosetup)
ANNOUNCEMENT_CHANNEL_ID=channel_id_for_new_member_announcements
APPROVED_ROLE_ID=role_id_to_assign_to_approved_members
PENDING_ROLE_ID=role_id_to_remove_from_approved_members

# Bot Settings (Optional)
COMMAND_PREFIX=!
BOT_NAME=Bean Bot
BOT_VERSION=1.0.0
LOG_LEVEL=INFO
```

### 6. Bot Permissions

Invite your bot to a server with the following permissions:
- Send Messages
- Read Message History
- Use Slash Commands
- Embed Links
- Attach Files
- Manage Roles (for Dyno applications)
- Manage Server (for member sync)
- Read Members (for member sync)

### 7. Run the Bot

```bash
python bot.py
```

## Project Structure

```
Bean Bot/
├── bot.py                    # Main bot file
├── requirements.txt          # Python dependencies
├── env.example              # Environment variables template
├── .gitignore              # Git ignore file
├── README.md               # This file
├── cogs/                   # Bot extensions/cogs
│   ├── __init__.py
│   ├── member_sync.py      # Member synchronization to Google Sheets
│   └── dyno_applications.py # Dyno application management
├── utils/                  # Utility functions
│   └── __init__.py
└── config/                 # Configuration files
    ├── __init__.py
    └── settings.py
```

## Available Commands

### Google Sheets Commands
- `!sheetinfo` - Display information about the connected Google Sheet
- `!sheetdata [sheet_name] [range]` - Display data from a specific sheet
  - Example: `!sheetdata "My Sheet" "A1:C10"`

### Member Synchronization Commands
- `!syncmembers [sheet_name]` - Sync all server members to Google Sheet
- `!membercount` - Show current member count and online status
- `!debugmembers` - Debug member access and show detailed information
- `!listroles` - List all roles that will be created as columns in the sheet

### Dyno Application Commands
- `/approve` - Approve a member's application (use in thread)
- `/reject [reason]` - Reject a member's application (use in thread)
- `!approve [@member]` - Approve application (traditional command)
- `!reject [@member] [reason]` - Reject application (traditional command)
- `!dynosetup` - Interactive setup for Dyno application configuration
- `!dynoconfig` - Show current Dyno application configuration

### Setup Commands
- `!dynosetup channel <channel>` - Set announcement channel
- `!dynosetup approved <role>` - Set approved role
- `!dynosetup pending <role>` - Set pending role
- `!dynosetup test` - Test configuration

## Dyno Application Workflow

### Thread-Based Approvals
1. **Application Thread**: Dyno creates a thread with format `@username - Application Type (#ID)`
2. **Approval Process**: Use `/approve` in the thread to approve the application
3. **Rejection Process**: Use `/reject [reason]` in the thread to reject the application
4. **Automatic Actions**:
   - Sends DM to the applicant
   - Assigns approved role
   - Removes pending role
   - Announces new member in specified channel

### Fallback Commands
- If username not found in thread title, use `!approve @user` or `!reject @user [reason]`

## Adding New Cogs

**🎉 Automatic Loading**: The bot automatically discovers and loads all `.py` files in the `cogs/` directory!

### Steps to add a new cog:
1. Create a new Python file in the `cogs/` directory
2. Follow the structure below
3. Restart the bot - your cog will be automatically loaded!

### Example cog structure:
```python
import discord
from discord.ext import commands

class YourCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    async def your_command(self, ctx):
        await ctx.send("Your command response")

async def setup(bot):
    await bot.add_cog(YourCog(bot))
```

### Error Handling:
- If a cog fails to load, the bot will log the error but continue running
- Use `!reloadall` to reload all cogs after making changes
- Check the console logs for detailed error information

## Configuration

The bot uses environment variables for configuration. See `env.example` for all available options.

## Troubleshooting

1. **Bot not responding**: Check if the bot token is correct and the bot has proper permissions
2. **Import errors**: Make sure you've activated the virtual environment and installed dependencies
3. **Permission errors**: Verify the bot has the necessary permissions in the Discord server
4. **Google Sheets errors**: Ensure the service account has access to the sheet and the sheet ID is correct

## Contributing

Feel free to add new features, cogs, or improvements to the bot! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is open source and available under the [MIT License](LICENSE).