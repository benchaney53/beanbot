import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timezone
import json
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class MemberSync(commands.Cog):
    """Cog for synchronizing Discord member data to Google Sheets"""
    
    def __init__(self, bot):
        self.bot = bot
        self.sheets_service = None
        self.google_sheet_id = os.getenv('GOOGLE_SHEET_ID')
        self.google_credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'google_credentials.json')
        
    async def cog_load(self):
        """Initialize Google Sheets service when cog loads"""
        await self.init_google_sheets()
    
    async def init_google_sheets(self):
        """Initialize Google Sheets API with write permissions"""
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
            print("MemberSync: Google Sheets API initialized with write permissions")
            
        except Exception as e:
            print(f"MemberSync: Failed to initialize Google Sheets: {e}")
            self.sheets_service = None
    
    async def get_all_roles(self, guild):
        """Get all unique roles from the guild (excluding @everyone)"""
        roles = []
        for role in guild.roles:
            if role.name != "@everyone":
                roles.append(role.name)
        return sorted(roles)  # Sort for consistent column order
    
    async def get_member_data(self, guild):
        """Extract member information from Discord guild"""
        members_data = []
        
        # Ensure we have all members loaded (including offline ones)
        if not guild.chunked:
            print("Fetching all members from Discord...")
            try:
                await guild.chunk()
            except Exception as e:
                print(f"Chunking failed, trying alternative method: {e}")
                # Alternative: fetch members individually if chunking fails
                # This is slower but more reliable
                pass
        
        # Get all unique roles in the guild
        all_roles = await self.get_all_roles(guild)
        print(f"Found {len(all_roles)} unique roles: {', '.join(all_roles)}")
        
        total_members = len(guild.members)
        bot_count = len([m for m in guild.members if m.bot])
        human_members = total_members - bot_count
        
        print(f"Found {total_members} total members in guild")
        print(f"Bots: {bot_count}, Humans: {human_members}")
        
        for member in guild.members:
            # Skip bots
            if member.bot:
                continue
                
            # Get member roles (excluding @everyone)
            member_roles = [role.name for role in member.roles if role.name != "@everyone"]
            
            # Get member's highest role
            highest_role = member.top_role.name if member.top_role.name != "@everyone" else "Member"
            
            # Calculate account age
            account_created = member.created_at
            now_aware = datetime.now(timezone.utc)
            
            try:
                account_age_days = (now_aware - account_created).days
            except TypeError:
                # Fallback for timezone issues
                account_age_days = 0
            
            # Calculate server join age
            joined_at = member.joined_at
            try:
                server_age_days = (now_aware - joined_at).days if joined_at else 0
            except TypeError:
                # Fallback for timezone issues
                server_age_days = 0
            
            # Create role columns - each role gets its own column with "Yes" or "No"
            role_columns = {}
            for role_name in all_roles:
                role_columns[f"role_{role_name}"] = "Yes" if role_name in member_roles else "No"
            
            member_info = {
                'username': str(member),
                'display_name': member.display_name,
                'user_id': str(member.id),
                'discriminator': member.discriminator,
                'nickname': member.nick or '',
                'roles': ', '.join(member_roles) if member_roles else 'None',  # Keep original for reference
                'highest_role': highest_role,
                'account_created': account_created.strftime('%Y-%m-%d %H:%M:%S'),
                'account_age_days': account_age_days,
                'joined_server': joined_at.strftime('%Y-%m-%d %H:%M:%S') if joined_at else 'Unknown',
                'server_age_days': server_age_days,
                'status': str(member.status),
                'is_online': member.status != discord.Status.offline,
                'avatar_url': str(member.avatar.url) if member.avatar else 'No Avatar',
                'last_synced': now_aware.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Add individual role columns
            member_info.update(role_columns)
            
            members_data.append(member_info)
        
        print(f"Processed {len(members_data)} human members for sync")
        return members_data, all_roles
    
    async def clear_sheet(self, sheet_name):
        """Clear all data from the specified sheet"""
        try:
            # Get sheet dimensions
            spreadsheet = self.sheets_service.spreadsheets().get(
                spreadsheetId=self.google_sheet_id
            ).execute()
            
            sheet_id = None
            for sheet in spreadsheet.get('sheets', []):
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                raise ValueError(f"Sheet '{sheet_name}' not found")
            
            # Clear the sheet
            self.sheets_service.spreadsheets().values().clear(
                spreadsheetId=self.google_sheet_id,
                range=f"{sheet_name}!A:Z"
            ).execute()
            
            print(f"Cleared {sheet_name} sheet")
            
        except Exception as e:
            print(f"Error clearing sheet: {e}")
            raise
    
    async def write_member_data(self, members_data, all_roles, sheet_name="Benji"):
        """Write member data to Google Sheet"""
        if not self.sheets_service:
            raise Exception("Google Sheets service not available")
        
        try:
            # Prepare headers - base headers first, then role columns
            base_headers = [
                'Username', 'Display Name', 'User ID', 'Discriminator', 'Nickname',
                'Roles', 'Highest Role', 'Account Created', 'Account Age (Days)',
                'Joined Server', 'Server Age (Days)', 'Status', 'Is Online',
                'Avatar URL', 'Last Synced'
            ]
            
            # Add role columns to headers
            role_headers = [f"Role: {role}" for role in all_roles]
            headers = base_headers + role_headers
            
            # Prepare data rows
            data_rows = [headers]
            for member in members_data:
                # Base data
                base_row = [
                    member['username'],
                    member['display_name'],
                    member['user_id'],
                    member['discriminator'],
                    member['nickname'],
                    member['roles'],
                    member['highest_role'],
                    member['account_created'],
                    member['account_age_days'],
                    member['joined_server'],
                    member['server_age_days'],
                    member['status'],
                    'Yes' if member['is_online'] else 'No',
                    member['avatar_url'],
                    member['last_synced']
                ]
                
                # Add role data
                role_data = [member.get(f"role_{role}", "No") for role in all_roles]
                
                # Combine base data and role data
                row = base_row + role_data
                data_rows.append(row)
            
            # Clear existing data
            await self.clear_sheet(sheet_name)
            
            # Write new data
            range_name = f"{sheet_name}!A1"
            body = {'values': data_rows}
            
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=self.google_sheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"Wrote {len(members_data)} members to {sheet_name} sheet with {len(all_roles)} role columns")
            return len(members_data)
            
        except Exception as e:
            print(f"Error writing member data: {e}")
            raise
    
    @commands.command(name='syncmembers')
    @commands.has_permissions(manage_guild=True)
    async def sync_members(self, ctx, sheet_name="Benji"):
        """Sync all server members to Google Sheet
        
        Usage: !syncmembers [sheet_name]
        Example: !syncmembers Benji
        """
        if not self.sheets_service:
            await ctx.send("Google Sheets service not available")
            return
        
        if not self.google_sheet_id:
            await ctx.send("Google Sheet ID not configured")
            return
        
        # Send initial message
        status_msg = await ctx.send("Starting member synchronization...")
        
        try:
            # Get member data
            await status_msg.edit(content="Collecting member data...")
            members_data, all_roles = await self.get_member_data(ctx.guild)
            
            if not members_data:
                await status_msg.edit(content="No human members found to sync (only bots in server?)")
                return
            
            # Write to sheet
            await status_msg.edit(content=f"Writing {len(members_data)} members to {sheet_name} sheet...")
            member_count = await self.write_member_data(members_data, all_roles, sheet_name)
            
            # Success message
            embed = discord.Embed(
                title="Member Sync Complete",
                color=0x00ff00,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(
                name="Members Synced",
                value=f"{member_count} members",
                inline=True
            )
            embed.add_field(
                name="Role Columns",
                value=f"{len(all_roles)} roles",
                inline=True
            )
            embed.add_field(
                name="Sheet",
                value=sheet_name,
                inline=True
            )
            embed.add_field(
                name="Server",
                value=ctx.guild.name,
                inline=True
            )
            if all_roles:
                embed.add_field(
                    name="Roles Found",
                    value=", ".join(all_roles[:5]) + ("..." if len(all_roles) > 5 else ""),
                    inline=False
                )
            embed.set_footer(text=f"Synced by {ctx.author}")
            
            await status_msg.edit(content="", embed=embed)
            
        except Exception as e:
            await status_msg.edit(content=f"Sync failed: {str(e)}")
            print(f"Member sync error: {e}")
    
    @sync_members.error
    async def sync_members_error(self, ctx, error):
        """Handle sync_members command errors"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need 'Manage Server' permission to sync members")
        elif isinstance(error, commands.CommandError):
            await ctx.send(f"Command error: {error}")
        else:
            await ctx.send(f"Unexpected error: {error}")
    
    @commands.command(name='membercount')
    async def member_count(self, ctx):
        """Show current member count and online status"""
        guild = ctx.guild
        
        # Ensure we have all members loaded
        if not guild.chunked:
            await ctx.send("Fetching all members...")
            try:
                await guild.chunk()
            except Exception as e:
                await ctx.send(f"Could not fetch all members: {e}")
        
        total_members = len(guild.members)
        online_members = len([m for m in guild.members if m.status != discord.Status.offline and not m.bot])
        bot_count = len([m for m in guild.members if m.bot])
        human_members = total_members - bot_count
        
        embed = discord.Embed(
            title="Server Member Statistics",
            color=0x0099ff,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Total Members", value=total_members, inline=True)
        embed.add_field(name="Human Members", value=human_members, inline=True)
        embed.add_field(name="Online Now", value=online_members, inline=True)
        embed.add_field(name="Bots", value=bot_count, inline=True)
        embed.add_field(name="Guild Chunked", value="Yes" if guild.chunked else "No", inline=True)
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='debugmembers')
    @commands.has_permissions(manage_guild=True)
    async def debug_members(self, ctx):
        """Debug member access and show detailed member information"""
        guild = ctx.guild
        
        # Try to fetch all members
        if not guild.chunked:
            await ctx.send("Attempting to fetch all members...")
            try:
                await guild.chunk()
                await ctx.send("Successfully fetched all members")
            except Exception as e:
                await ctx.send(f"Failed to fetch all members: {e}")
                return
        
        # Show detailed member info
        members_info = []
        for i, member in enumerate(guild.members[:10]):  # Show first 10 members
            member_type = "Bot" if member.bot else "Human"
            status = str(member.status)
            members_info.append(f"{i+1}. {member} ({member_type}) - {status}")
        
        info_text = "\n".join(members_info)
        if len(guild.members) > 10:
            info_text += f"\n... and {len(guild.members) - 10} more members"
        
        embed = discord.Embed(
            title="Member Debug Information",
            description=info_text,
            color=0xff9900
        )
        embed.add_field(name="Total Members", value=len(guild.members), inline=True)
        embed.add_field(name="Guild Chunked", value="Yes" if guild.chunked else "No", inline=True)
        embed.add_field(name="Bot Permissions", value="Members Intent: Enabled" if ctx.bot.intents.members else "Members Intent: Disabled", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='listroles')
    async def list_roles(self, ctx):
        """List all roles that will be created as columns in the sheet"""
        guild = ctx.guild
        all_roles = await self.get_all_roles(guild)
        
        if not all_roles:
            await ctx.send("No roles found in this server (excluding @everyone)")
            return
        
        embed = discord.Embed(
            title="Server Roles for Sheet Columns",
            description=f"Found {len(all_roles)} roles that will be created as individual columns:",
            color=0x0099ff
        )
        
        # Split roles into chunks for better display
        role_chunks = [all_roles[i:i+10] for i in range(0, len(all_roles), 10)]
        
        for i, chunk in enumerate(role_chunks):
            field_name = f"Roles {i*10+1}-{min((i+1)*10, len(all_roles))}"
            field_value = "\n".join([f"• {role}" for role in chunk])
            embed.add_field(name=field_name, value=field_value, inline=True)
        
        embed.set_footer(text="Each role will have its own column with 'Yes' or 'No' values")
        
        await ctx.send(embed=embed)


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(MemberSync(bot))
