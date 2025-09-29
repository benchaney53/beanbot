import os
import asyncio
import json
import discord
from discord.ext import commands
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables
load_dotenv()


class BeanBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True  # Required to access member information
        intents.guilds = True   # Required for guild information
        super().__init__(command_prefix='!', intents=intents)
        
        # Configuration
        self.discord_token = os.getenv('DISCORD_TOKEN')
        self.discord_guild_id = os.getenv('DISCORD_GUILD_ID')
        self.google_credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'google_credentials.json')
        self.google_sheet_id = os.getenv('GOOGLE_SHEET_ID')
        self.sheets_service = None
        
    async def setup_hook(self):
        """Initialize bot on startup"""
        print("Bean Bot is starting up...")
        self.validate_config()
        await self.init_google_sheets()
        await self.print_sheet_info()
        
        # Load cogs
        await self.load_extension('cogs.member_sync')
        await self.load_extension('cogs.dyno_applications')
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} slash commands")
        except Exception as e:
            print(f"Failed to sync slash commands: {e}")
        
    def validate_config(self):
        """Validate required configuration"""
        if not self.discord_token:
            raise ValueError("Missing DISCORD_TOKEN")
        if not self.google_sheet_id:
            raise ValueError("Missing GOOGLE_SHEET_ID")
        if not os.path.exists(self.google_credentials_file):
            raise FileNotFoundError(f"Credentials file not found: {self.google_credentials_file}")
        print("Configuration validated")
    
    async def init_google_sheets(self):
        """Initialize Google Sheets API"""
        try:
            with open(self.google_credentials_file) as f:
                creds_data = json.load(f)
            
            credentials = Credentials.from_service_account_info(
                creds_data,
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
            )
            
            self.sheets_service = build('sheets', 'v4', credentials=credentials)
            print("Google Sheets API initialized")
        except Exception as e:
            print(f"Failed to initialize Google Sheets: {e}")
            raise
    
    async def print_sheet_info(self):
        """Display sheet information on startup"""
        if not self.sheets_service:
            return
        
        try:
            spreadsheet = self.sheets_service.spreadsheets().get(
                spreadsheetId=self.google_sheet_id
            ).execute()
            
            title = spreadsheet.get('properties', {}).get('title', 'Unknown')
            sheets = spreadsheet.get('sheets', [])
            
            print(f"\nSheet: {title}")
            print(f"🆔 ID: {self.google_sheet_id}")
            print(f"Sheets: {len(sheets)}")
            
            for i, sheet in enumerate(sheets, 1):
                props = sheet.get('properties', {})
                name = props.get('title', 'Unknown')
                grid = props.get('gridProperties', {})
                print(f"  {i}. {name} ({grid.get('rowCount')}x{grid.get('columnCount')})")
            
            if sheets:
                first_sheet = sheets[0]['properties']['title']
                print(f"\nSample from '{first_sheet}':")
                await self.print_sheet_data(first_sheet)
        except HttpError as e:
            print(f"API error: {e}")
    
    async def print_sheet_data(self, sheet_name, max_rows=10):
        """Print sample data from sheet"""
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.google_sheet_id,
                range=f"{sheet_name}!A1:Z{max_rows}"
            ).execute()
            
            values = result.get('values', [])
            if not values:
                print("  (No data)")
                return
            
            for i, row in enumerate(values):
                prefix = "Header:" if i == 0 else f"Row {i}:"
                print(f"  {prefix} {' | '.join(str(cell) for cell in row)}")
        except Exception as e:
                print(f"  Error: {e}")
    
    async def on_ready(self):
        """Called when bot connects"""
        print(f"\n{self.user} is online!")
        
        if self.discord_guild_id:
            guild = self.get_guild(int(self.discord_guild_id))
            print(f"Guild: {guild.name if guild else 'Not found'}")
    
    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            return
        print(f"Error: {error}")
        await ctx.send(f"Error: {error}")


# Commands
@commands.command(name='sheetinfo')
async def sheet_info(ctx):
    """Display sheet information"""
    if not bot.sheets_service:
        await ctx.send("Google Sheets not available")
        return
    
    try:
        spreadsheet = bot.sheets_service.spreadsheets().get(
            spreadsheetId=bot.google_sheet_id
        ).execute()
        
        embed = discord.Embed(title="Google Sheet Info", color=0x00ff00)
        embed.add_field(
            name="Title",
            value=spreadsheet.get('properties', {}).get('title', 'Unknown'),
            inline=False
        )
        embed.add_field(name="Sheet ID", value=bot.google_sheet_id, inline=False)
        embed.add_field(
            name="Sheets",
            value=len(spreadsheet.get('sheets', [])),
            inline=False
        )
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Error: {e}")


@commands.command(name='sheetdata')
async def sheet_data(ctx, sheet_name="Sheet1", range_spec=None):
    """Display sheet data
    
    Usage: !sheetdata [sheet_name] [range]
    Example: !sheetdata "Sales" "A1:C10"
    """
    if not bot.sheets_service:
        await ctx.send("Google Sheets not available")
        return
    
    try:
        range_name = range_spec or f"{sheet_name}!A1:Z10"
        
        result = bot.sheets_service.spreadsheets().values().get(
            spreadsheetId=bot.google_sheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        if not values:
            await ctx.send(f"No data in {sheet_name}")
            return
        
        data_text = f"Data from {sheet_name}:\n```\n"
        for row in values[:20]:
            row_text = " | ".join(str(cell) for cell in row) + "\n"
            if len(data_text + row_text) > 1900:
                data_text += "... (truncated)\n"
                break
            data_text += row_text
        
        data_text += "```"
        await ctx.send(data_text)
    except Exception as e:
        await ctx.send(f"Error: {e}")


# Initialize bot
bot = BeanBot()
bot.add_command(sheet_info)
bot.add_command(sheet_data)


async def main():
    """Run the bot"""
    try:
        await bot.start(bot.discord_token)
    except Exception as e:
        print(f"Failed to start: {e}")


if __name__ == "__main__":
    print("Starting Bean Bot...")
    print("Required environment variables:")
    print("   - DISCORD_TOKEN")
    print("   - GOOGLE_SHEET_ID")
    print("   - GOOGLE_CREDENTIALS_FILE (optional)\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"\nCrashed: {e}")