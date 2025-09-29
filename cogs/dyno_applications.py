import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import re
from datetime import datetime, timezone
import os
from config.settings import BotConfig


class DynoApplications(commands.Cog):
    """Cog for handling Dyno application approvals and rejections"""
    
    def __init__(self, bot):
        self.bot = bot
        self.announcement_channel_id = int(os.getenv('ANNOUNCEMENT_CHANNEL_ID', '0'))
        self.approved_role_id = int(os.getenv('APPROVED_ROLE_ID', '0'))
        self.pending_role_id = int(os.getenv('PENDING_ROLE_ID', '0'))
        
    async def cog_load(self):
        """Initialize the cog when it loads"""
        print("DynoApplications cog loaded")
    
    def extract_username_from_thread_title(self, thread_title):
        """Extract Discord username from thread title
        Expected format: @username - Application Type (#ID)
        Example: @hen3si - DMH Membership Request (#469)
        """
        # Pattern to match @username at the start of the thread title
        pattern = r'^@([a-zA-Z0-9_]+)'
        match = re.match(pattern, thread_title)
        
        if match:
            return match.group(1)  # Return the username without the @
        return None
    
    async def get_member_from_thread(self, thread):
        """Get the member object from the thread title"""
        if not isinstance(thread, discord.Thread):
            return None
        
        username = self.extract_username_from_thread_title(thread.name)
        if not username:
            return None
        
        # Search for the member in the guild
        for member in thread.guild.members:
            if member.name == username or member.display_name == username:
                return member
        
        return None
    
    def is_thread(self, channel):
        """Check if the channel is a thread"""
        return isinstance(channel, discord.Thread)
        
    async def get_announcement_channel(self, guild):
        """Get the announcement channel for new member announcements"""
        if self.announcement_channel_id:
            channel = guild.get_channel(self.announcement_channel_id)
            if channel:
                return channel
        
        # Fallback: look for channels with "welcome", "announcements", or "general" in the name
        for channel in guild.text_channels:
            if any(keyword in channel.name.lower() for keyword in ['welcome', 'announcements', 'general']):
                return channel
        
        return None
    
    async def get_approved_role(self, guild):
        """Get the role to assign to approved members"""
        if self.approved_role_id:
            role = guild.get_role(self.approved_role_id)
            if role:
                return role
        
        # Fallback: look for roles with "member", "verified", or "approved" in the name
        for role in guild.roles:
            if any(keyword in role.name.lower() for keyword in ['member', 'verified', 'approved']):
                return role
        
        return None
    
    async def get_pending_role(self, guild):
        """Get the pending role to remove from approved members"""
        if self.pending_role_id:
            role = guild.get_role(self.pending_role_id)
            if role:
                return role
        
        # Fallback: look for roles with "pending", "applicant", or "unverified" in the name
        for role in guild.roles:
            if any(keyword in role.name.lower() for keyword in ['pending', 'applicant', 'unverified']):
                return role
        
        return None
    
    async def send_approval_dm(self, member, approver):
        """Send approval DM to the member"""
        try:
            embed = discord.Embed(
                title="🎉 Application Approved!",
                description="Your application has been approved! Welcome to the server!",
                color=0x00ff00,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(
                name="Approved by",
                value=f"{approver.mention}",
                inline=True
            )
            embed.add_field(
                name="Server",
                value=member.guild.name,
                inline=True
            )
            embed.set_footer(text="Welcome to the community!")
            
            await member.send(embed=embed)
            return True
        except discord.Forbidden:
            return False
        except Exception as e:
            print(f"Error sending approval DM: {e}")
            return False
    
    async def send_rejection_dm(self, member, approver, reason=None):
        """Send rejection DM to the member"""
        try:
            embed = discord.Embed(
                title="❌ Application Rejected",
                description="Unfortunately, your application has been rejected.",
                color=0xff0000,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(
                name="Rejected by",
                value=f"{approver.mention}",
                inline=True
            )
            embed.add_field(
                name="Server",
                value=member.guild.name,
                inline=True
            )
            if reason:
                embed.add_field(
                    name="Reason",
                    value=reason,
                    inline=False
                )
            embed.set_footer(text="You can reapply in the future if you wish.")
            
            await member.send(embed=embed)
            return True
        except discord.Forbidden:
            return False
        except Exception as e:
            print(f"Error sending rejection DM: {e}")
            return False
    
    async def announce_new_member(self, member, approver):
        """Announce the new member to the announcement channel"""
        try:
            announcement_channel = await self.get_announcement_channel(member.guild)
            if not announcement_channel:
                return False
            
            embed = discord.Embed(
                title="🎉 New Member Approved!",
                description=f"Please welcome {member.mention} to the server!",
                color=0x00ff00,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(
                name="Member",
                value=f"{member.display_name} ({member})",
                inline=True
            )
            embed.add_field(
                name="Approved by",
                value=f"{approver.mention}",
                inline=True
            )
            embed.add_field(
                name="Account Created",
                value=f"<t:{int(member.created_at.timestamp())}:R>",
                inline=True
            )
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            embed.set_footer(text="Welcome to the community!")
            
            await announcement_channel.send(embed=embed)
            return True
        except Exception as e:
            print(f"Error announcing new member: {e}")
            return False
    
    async def assign_roles(self, member, approver):
        """Assign approved role and remove pending role"""
        try:
            approved_role = await self.get_approved_role(member.guild)
            pending_role = await self.get_pending_role(member.guild)
            
            roles_to_add = []
            roles_to_remove = []
            
            if approved_role and approved_role not in member.roles:
                roles_to_add.append(approved_role)
            
            if pending_role and pending_role in member.roles:
                roles_to_remove.append(pending_role)
            
            if roles_to_add or roles_to_remove:
                if roles_to_add:
                    await member.add_roles(*roles_to_add, reason=f"Application approved by {approver}")
                if roles_to_remove:
                    await member.remove_roles(*roles_to_remove, reason=f"Application approved by {approver}")
                return True
            
            return False
        except Exception as e:
            print(f"Error assigning roles: {e}")
            return False
    
    @app_commands.command(name="approve", description="Approve a member's application (use in thread)")
    async def approve_slash(self, interaction: discord.Interaction):
        """Slash command to approve a member's application from thread title"""
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ You don't have permission to approve applications.", ephemeral=True)
            return
        
        # Check if command is used in a thread
        if not self.is_thread(interaction.channel):
            await interaction.response.send_message("❌ This command can only be used in threads.", ephemeral=True)
            return
        
        # Get member from thread title
        member = await self.get_member_from_thread(interaction.channel)
        if not member:
            await interaction.response.send_message("❌ Could not find the member from the thread title. Please use `!approve @user` instead.", ephemeral=True)
            return
        
        if member.bot:
            await interaction.response.send_message("❌ Cannot approve bots.", ephemeral=True)
            return
        
        # Get role and channel info for confirmation
        approved_role = await self.get_approved_role(interaction.guild)
        announcement_channel = await self.get_announcement_channel(interaction.guild)
        
        # Create confirmation message
        role_name = approved_role.name if approved_role else "No role configured"
        channel_name = announcement_channel.name if announcement_channel else "No channel configured"
        
        confirmation_msg = f"Sending Membership approval to {member.mention}, adding \"{role_name}\", and announcing {member.mention} in \"{channel_name}\". Please confirm."
        
        await interaction.response.send_message(confirmation_msg)
        
        # Wait for confirmation (you can add a reaction-based confirmation system here if needed)
        # For now, we'll proceed automatically after a short delay
        await asyncio.sleep(2)
        
        # Send approval DM
        dm_sent = await self.send_approval_dm(member, interaction.user)
        
        # Assign roles
        roles_assigned = await self.assign_roles(member, interaction.user)
        
        # Announce new member
        announcement_sent = await self.announce_new_member(member, interaction.user)
        
        # Create response embed
        embed = discord.Embed(
            title="✅ Application Approved",
            description=f"Successfully approved {member.mention}'s application!",
            color=0x00ff00,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="Thread",
            value=f"[{interaction.channel.name}]({interaction.channel.jump_url})",
            inline=False
        )
        
        status_fields = []
        if dm_sent:
            status_fields.append("✅ DM sent")
        else:
            status_fields.append("❌ DM failed (user may have DMs disabled)")
        
        if roles_assigned:
            status_fields.append("✅ Roles updated")
        else:
            status_fields.append("⚠️ No roles changed")
        
        if announcement_sent:
            status_fields.append("✅ Announcement posted")
        else:
            status_fields.append("❌ Announcement failed")
        
        embed.add_field(
            name="Status",
            value="\n".join(status_fields),
            inline=False
        )
        embed.set_footer(text=f"Approved by {interaction.user}")
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="reject", description="Reject a member's application (use in thread)")
    @app_commands.describe(reason="Optional reason for rejection")
    async def reject_slash(self, interaction: discord.Interaction, reason: str = None):
        """Slash command to reject a member's application from thread title"""
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ You don't have permission to reject applications.", ephemeral=True)
            return
        
        # Check if command is used in a thread
        if not self.is_thread(interaction.channel):
            await interaction.response.send_message("❌ This command can only be used in threads.", ephemeral=True)
            return
        
        # Get member from thread title
        member = await self.get_member_from_thread(interaction.channel)
        if not member:
            await interaction.response.send_message("❌ Could not find the member from the thread title. Please use `!reject @user [reason]` instead.", ephemeral=True)
            return
        
        if member.bot:
            await interaction.response.send_message("❌ Cannot reject bots.", ephemeral=True)
            return
        
        # Create confirmation message
        reason_text = f" with reason: \"{reason}\"" if reason else ""
        confirmation_msg = f"Sending Membership rejection to {member.mention}{reason_text}. Please confirm."
        
        await interaction.response.send_message(confirmation_msg)
        
        # Wait for confirmation (you can add a reaction-based confirmation system here if needed)
        # For now, we'll proceed automatically after a short delay
        await asyncio.sleep(2)
        
        # Send rejection DM
        dm_sent = await self.send_rejection_dm(member, interaction.user, reason)
        
        # Create response embed
        embed = discord.Embed(
            title="❌ Application Rejected",
            description=f"Successfully rejected {member.mention}'s application.",
            color=0xff0000,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="Thread",
            value=f"[{interaction.channel.name}]({interaction.channel.jump_url})",
            inline=False
        )
        
        if reason:
            embed.add_field(
                name="Reason",
                value=reason,
                inline=False
            )
        
        status_fields = []
        if dm_sent:
            status_fields.append("✅ DM sent")
        else:
            status_fields.append("❌ DM failed (user may have DMs disabled)")
        
        embed.add_field(
            name="Status",
            value="\n".join(status_fields),
            inline=False
        )
        embed.set_footer(text=f"Rejected by {interaction.user}")
        
        await interaction.followup.send(embed=embed)
    
    @commands.command(name="approve")
    @commands.has_permissions(manage_roles=True)
    async def approve_command(self, ctx, member: discord.Member = None):
        """Traditional command to approve a member's application
        Usage: !approve [@member] or !approve (in thread)
        """
        # Check if command is used in a thread and no member specified
        if isinstance(ctx.channel, discord.Thread) and member is None:
            # Get member from thread title
            member = await self.get_member_from_thread(ctx.channel)
            if not member:
                await ctx.send("❌ Could not find the member from the thread title. Please use `!approve @user` instead.")
                return
        elif member is None:
            await ctx.send("❌ Please specify a member to approve or use this command in a thread.")
            return
        
        if member.bot:
            await ctx.send("❌ Cannot approve bots.")
            return
        
        # Get role and channel info for confirmation
        approved_role = await self.get_approved_role(ctx.guild)
        announcement_channel = await self.get_announcement_channel(ctx.guild)
        
        # Create confirmation message
        role_name = approved_role.name if approved_role else "No role configured"
        channel_name = announcement_channel.name if announcement_channel else "No channel configured"
        
        confirmation_msg = f"Sending Membership approval to {member.mention}, adding \"{role_name}\", and announcing {member.mention} in \"{channel_name}\". Please confirm."
        
        await ctx.send(confirmation_msg)
        
        # Wait for confirmation (you can add a reaction-based confirmation system here if needed)
        # For now, we'll proceed automatically after a short delay
        await asyncio.sleep(2)
        
        # Send approval DM
        dm_sent = await self.send_approval_dm(member, ctx.author)
        
        # Assign roles
        roles_assigned = await self.assign_roles(member, ctx.author)
        
        # Announce new member
        announcement_sent = await self.announce_new_member(member, ctx.author)
        
        # Create response embed
        embed = discord.Embed(
            title="✅ Application Approved",
            description=f"Successfully approved {member.mention}'s application!",
            color=0x00ff00,
            timestamp=datetime.now(timezone.utc)
        )
        
        if isinstance(ctx.channel, discord.Thread):
            embed.add_field(
                name="Thread",
                value=f"[{ctx.channel.name}]({ctx.channel.jump_url})",
                inline=False
            )
        
        status_fields = []
        if dm_sent:
            status_fields.append("✅ DM sent")
        else:
            status_fields.append("❌ DM failed (user may have DMs disabled)")
        
        if roles_assigned:
            status_fields.append("✅ Roles updated")
        else:
            status_fields.append("⚠️ No roles changed")
        
        if announcement_sent:
            status_fields.append("✅ Announcement posted")
        else:
            status_fields.append("❌ Announcement failed")
        
        embed.add_field(
            name="Status",
            value="\n".join(status_fields),
            inline=False
        )
        embed.set_footer(text=f"Approved by {ctx.author}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="reject")
    @commands.has_permissions(manage_roles=True)
    async def reject_command(self, ctx, member: discord.Member = None, *, reason: str = None):
        """Traditional command to reject a member's application
        Usage: !reject [@member] [reason] or !reject [reason] (in thread)
        """
        # Check if command is used in a thread and no member specified
        if isinstance(ctx.channel, discord.Thread) and member is None:
            # Get member from thread title
            member = await self.get_member_from_thread(ctx.channel)
            if not member:
                await ctx.send("❌ Could not find the member from the thread title. Please use `!reject @user [reason]` instead.")
                return
        elif member is None:
            await ctx.send("❌ Please specify a member to reject or use this command in a thread.")
            return
        
        if member.bot:
            await ctx.send("❌ Cannot reject bots.")
            return
        
        # Create confirmation message
        reason_text = f" with reason: \"{reason}\"" if reason else ""
        confirmation_msg = f"Sending Membership rejection to {member.mention}{reason_text}. Please confirm."
        
        await ctx.send(confirmation_msg)
        
        # Wait for confirmation (you can add a reaction-based confirmation system here if needed)
        # For now, we'll proceed automatically after a short delay
        await asyncio.sleep(2)
        
        # Send rejection DM
        dm_sent = await self.send_rejection_dm(member, ctx.author, reason)
        
        # Create response embed
        embed = discord.Embed(
            title="❌ Application Rejected",
            description=f"Successfully rejected {member.mention}'s application.",
            color=0xff0000,
            timestamp=datetime.now(timezone.utc)
        )
        
        if isinstance(ctx.channel, discord.Thread):
            embed.add_field(
                name="Thread",
                value=f"[{ctx.channel.name}]({ctx.channel.jump_url})",
                inline=False
            )
        
        if reason:
            embed.add_field(
                name="Reason",
                value=reason,
                inline=False
            )
        
        status_fields = []
        if dm_sent:
            status_fields.append("✅ DM sent")
        else:
            status_fields.append("❌ DM failed (user may have DMs disabled)")
        
        embed.add_field(
            name="Status",
            value="\n".join(status_fields),
            inline=False
        )
        embed.set_footer(text=f"Rejected by {ctx.author}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="dynosetup")
    @commands.has_permissions(manage_guild=True)
    async def dyno_setup_channel(self, ctx, setting: str = None, *, value: str = None):
        """Setup specific Dyno application settings
        
        Usage:
        !dynosetup channel <channel_id_or_mention>
        !dynosetup approved <role_id_or_mention>
        !dynosetup pending <role_id_or_mention>
        !dynosetup test
        """
        if not setting:
            # Show the main setup menu
            embed = discord.Embed(
                title="🔧 Dyno Applications Setup",
                description="Let's configure your Dyno application system step by step!",
                color=0x0099ff,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Show current configuration
            announcement_channel = await self.get_announcement_channel(ctx.guild)
            approved_role = await self.get_approved_role(ctx.guild)
            pending_role = await self.get_pending_role(ctx.guild)
            
            embed.add_field(
                name="📋 Current Configuration",
                value=f"**Announcement Channel:** {announcement_channel.mention if announcement_channel else '❌ Not configured'}\n"
                      f"**Approved Role:** {approved_role.mention if approved_role else '❌ Not configured'}\n"
                      f"**Pending Role:** {pending_role.mention if pending_role else '❌ Not configured'}",
                inline=False
            )
            
            # Instructions
            instructions = (
                "**How to get IDs:**\n"
                "1. **Channel ID:** Right-click channel → Copy ID\n"
                "2. **Role ID:** Right-click role → Copy ID\n"
                "3. **Enable Developer Mode:** User Settings → Advanced → Developer Mode\n\n"
                "**Setup Steps:**\n"
                "1. Use `!dynosetup channel` to set announcement channel\n"
                "2. Use `!dynosetup approved` to set approved role\n"
                "3. Use `!dynosetup pending` to set pending role\n"
                "4. Use `!dynosetup test` to test the configuration"
            )
            
            embed.add_field(
                name="📖 Instructions",
                value=instructions,
                inline=False
            )
            
            embed.set_footer(text="Use the commands above to configure each setting")
            
            await ctx.send(embed=embed)
            return
        
        if setting.lower() == "channel":
            if not value:
                await ctx.send("❌ Please provide a channel ID or mention. Example: `!dynosetup channel #announcements`")
                return
            
            # Try to parse channel
            channel = None
            try:
                # Try to parse as ID first
                channel_id = int(value.strip('<>#'))
                channel = ctx.guild.get_channel(channel_id)
            except ValueError:
                # Try to parse as mention
                if value.startswith('<#') and value.endswith('>'):
                    channel_id = int(value[2:-1])
                    channel = ctx.guild.get_channel(channel_id)
            
            if not channel:
                await ctx.send("❌ Channel not found. Make sure the channel ID is correct and the bot can see the channel.")
                return
            
            # Update the environment variable (this would need to be saved to a file in a real implementation)
            self.announcement_channel_id = channel.id
            
            embed = discord.Embed(
                title="✅ Announcement Channel Set",
                description=f"Announcement channel set to {channel.mention}",
                color=0x00ff00
            )
            embed.add_field(
                name="Channel ID",
                value=str(channel.id),
                inline=True
            )
            embed.add_field(
                name="Environment Variable",
                value=f"ANNOUNCEMENT_CHANNEL_ID={channel.id}",
                inline=False
            )
            embed.set_footer(text="Add this to your .env file to make it permanent")
            
            await ctx.send(embed=embed)
            
        elif setting.lower() == "approved":
            if not value:
                await ctx.send("❌ Please provide a role ID or mention. Example: `!dynosetup approved @Member`")
                return
            
            # Try to parse role
            role = None
            try:
                # Try to parse as ID first
                role_id = int(value.strip('<>@&'))
                role = ctx.guild.get_role(role_id)
            except ValueError:
                # Try to parse as mention
                if value.startswith('<@&') and value.endswith('>'):
                    role_id = int(value[3:-1])
                    role = ctx.guild.get_role(role_id)
            
            if not role:
                await ctx.send("❌ Role not found. Make sure the role ID is correct and the bot can see the role.")
                return
            
            # Update the environment variable
            self.approved_role_id = role.id
            
            embed = discord.Embed(
                title="✅ Approved Role Set",
                description=f"Approved role set to {role.mention}",
                color=0x00ff00
            )
            embed.add_field(
                name="Role ID",
                value=str(role.id),
                inline=True
            )
            embed.add_field(
                name="Environment Variable",
                value=f"APPROVED_ROLE_ID={role.id}",
                inline=False
            )
            embed.set_footer(text="Add this to your .env file to make it permanent")
            
            await ctx.send(embed=embed)
            
        elif setting.lower() == "pending":
            if not value:
                await ctx.send("❌ Please provide a role ID or mention. Example: `!dynosetup pending @Applicant`")
                return
            
            # Try to parse role
            role = None
            try:
                # Try to parse as ID first
                role_id = int(value.strip('<>@&'))
                role = ctx.guild.get_role(role_id)
            except ValueError:
                # Try to parse as mention
                if value.startswith('<@&') and value.endswith('>'):
                    role_id = int(value[3:-1])
                    role = ctx.guild.get_role(role_id)
            
            if not role:
                await ctx.send("❌ Role not found. Make sure the role ID is correct and the bot can see the role.")
                return
            
            # Update the environment variable
            self.pending_role_id = role.id
            
            embed = discord.Embed(
                title="✅ Pending Role Set",
                description=f"Pending role set to {role.mention}",
                color=0x00ff00
            )
            embed.add_field(
                name="Role ID",
                value=str(role.id),
                inline=True
            )
            embed.add_field(
                name="Environment Variable",
                value=f"PENDING_ROLE_ID={role.id}",
                inline=False
            )
            embed.set_footer(text="Add this to your .env file to make it permanent")
            
            await ctx.send(embed=embed)
            
        elif setting.lower() == "test":
            # Test the configuration
            announcement_channel = await self.get_announcement_channel(ctx.guild)
            approved_role = await self.get_approved_role(ctx.guild)
            pending_role = await self.get_pending_role(ctx.guild)
            
            embed = discord.Embed(
                title="🧪 Configuration Test",
                color=0x0099ff,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Test each component
            tests = []
            
            if announcement_channel:
                tests.append("✅ Announcement channel configured")
            else:
                tests.append("❌ Announcement channel not configured")
            
            if approved_role:
                tests.append("✅ Approved role configured")
            else:
                tests.append("❌ Approved role not configured")
            
            if pending_role:
                tests.append("✅ Pending role configured")
            else:
                tests.append("❌ Pending role not configured")
            
            embed.add_field(
                name="Test Results",
                value="\n".join(tests),
                inline=False
            )
            
            if announcement_channel and approved_role:
                embed.add_field(
                    name="✅ Ready to Use",
                    value="Your Dyno application system is ready! You can now use `/approve` and `/reject` commands.",
                    inline=False
                )
            else:
                embed.add_field(
                    name="⚠️ Incomplete Setup",
                    value="Please complete the setup by configuring the missing components.",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        else:
            await ctx.send(
                "❌ Invalid setting. Use one of:\n"
                "• `!dynosetup channel <channel>`\n"
                "• `!dynosetup approved <role>`\n"
                "• `!dynosetup pending <role>`\n"
                "• `!dynosetup test`"
            )
    
    @commands.command(name="dynoconfig")
    @commands.has_permissions(manage_guild=True)
    async def dyno_config(self, ctx):
        """Show current Dyno application configuration"""
        embed = discord.Embed(
            title="Dyno Applications Configuration",
            color=0x0099ff,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Get current settings
        announcement_channel = await self.get_announcement_channel(ctx.guild)
        approved_role = await self.get_approved_role(ctx.guild)
        pending_role = await self.get_pending_role(ctx.guild)
        
        embed.add_field(
            name="Announcement Channel",
            value=announcement_channel.mention if announcement_channel else "Not configured",
            inline=True
        )
        embed.add_field(
            name="Approved Role",
            value=approved_role.mention if approved_role else "Not configured",
            inline=True
        )
        embed.add_field(
            name="Pending Role",
            value=pending_role.mention if pending_role else "Not configured",
            inline=True
        )
        
        embed.add_field(
            name="Environment Variables",
            value=f"ANNOUNCEMENT_CHANNEL_ID: {self.announcement_channel_id or 'Not set'}\n"
                  f"APPROVED_ROLE_ID: {self.approved_role_id or 'Not set'}\n"
                  f"PENDING_ROLE_ID: {self.pending_role_id or 'Not set'}",
            inline=False
        )
        
        embed.set_footer(text="Use !dynosetup to configure these settings")
        
        await ctx.send(embed=embed)
    
    @approve_command.error
    async def approve_error(self, ctx, error):
        """Handle approve command errors"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need 'Manage Roles' permission to approve applications.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Member not found. Please mention a valid member.")
        elif isinstance(error, commands.CommandError):
            await ctx.send(f"❌ Command error: {error}")
    
    @reject_command.error
    async def reject_error(self, ctx, error):
        """Handle reject command errors"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need 'Manage Roles' permission to reject applications.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Member not found. Please mention a valid member.")
        elif isinstance(error, commands.CommandError):
            await ctx.send(f"❌ Command error: {error}")


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(DynoApplications(bot))
