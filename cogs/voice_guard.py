import discord
from discord.ext import commands
from datetime import datetime, timezone
import asyncio
from collections import defaultdict
from config import MOD_ROLE_ID, PENALTY_SECONDS

class VoiceGuard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Tracks disconnect counts: {executor_id: [timestamp, timestamp, ...]}
        self.disconnect_tracker = defaultdict(list)

    async def apply_penalty(self, executor, guild, reason):
        """Remove mod role for PENALTY_SECONDS then restore it."""
        role = guild.get_role(MOD_ROLE_ID)
        if role and role in executor.roles:
            try:
                print(f"⚠️  Penalty applied to {executor.name} | Reason: {reason}")
                await executor.remove_roles(role, reason=reason)
                await asyncio.sleep(PENALTY_SECONDS)
                await executor.add_roles(role, reason="Penalty finished.")
                print(f"✅ Role restored to {executor.name}.")
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print(f"⛔ Skipped: {executor.name} does not have the mod role or role not found.")

    # ---------------------------------------------------------------
    # FEATURE 1: Single disconnect → penalty
    # FEATURE 2: 3 disconnects within 60 seconds → penalty
    # ---------------------------------------------------------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel is not None and after.channel is None:
            print(f"🔊 {member.name} disconnected from {before.channel.name}")
            guild = member.guild
            await asyncio.sleep(1.5)

            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.member_disconnect):
                time_diff = (datetime.now(timezone.utc) - entry.created_at).total_seconds()
                print(f"📋 Audit log: {entry.user.name} | time_diff: {time_diff:.2f}s")

                if time_diff < 10:
                    executor = entry.user

                    print(f"👤 Executor: {executor.name} | bot: {executor.bot} | admin: {executor.guild_permissions.administrator}")

                    if executor.bot or executor.guild_permissions.administrator:
                        print("⛔ Skipped: executor is bot or admin")
                        return

                    role = guild.get_role(MOD_ROLE_ID)
                    print(f"🎭 Role found: {role} | has role: {role in executor.roles if role else 'N/A'}")

                    if not role or role not in executor.roles:
                        return

                    now = datetime.now(timezone.utc).timestamp()

                    # Track this disconnect
                    self.disconnect_tracker[executor.id].append(now)

                    # Keep only disconnects from the last 60 seconds
                    self.disconnect_tracker[executor.id] = [
                        t for t in self.disconnect_tracker[executor.id]
                        if now - t <= 60
                    ]

                    count = len(self.disconnect_tracker[executor.id])
                    print(f"📊 {executor.name} disconnect count in last 60s: {count}")

                    if count >= 3:
                        # 3+ disconnects in 60s → penalty
                        self.disconnect_tracker[executor.id].clear()
                        await self.apply_penalty(executor, guild, "Disconnected 3+ members in 60 seconds")
                    else:
                        # Single disconnect → penalty
                        await self.apply_penalty(executor, guild, "Disconnected a member")

    # ---------------------------------------------------------------
    # FEATURE 3: Deleting a voice channel with people in it → penalty
    # ---------------------------------------------------------------
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        # Only care about voice channels
        if not isinstance(channel, discord.VoiceChannel):
            return

        # Check if there were members in it (Discord keeps member cache briefly)
        member_count = len(channel.members)
        print(f"🗑️  Voice channel deleted: {channel.name} | Members inside: {member_count}")

        if member_count == 0:
            print("⛔ Channel was empty, no penalty.")
            return

        guild = channel.guild
        await asyncio.sleep(1.5)

        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            time_diff = (datetime.now(timezone.utc) - entry.created_at).total_seconds()
            print(f"📋 Audit log: {entry.user.name} | time_diff: {time_diff:.2f}s")

            if time_diff < 10:
                executor = entry.user

                print(f"👤 Executor: {executor.name} | bot: {executor.bot} | admin: {executor.guild_permissions.administrator}")

                if executor.bot or executor.guild_permissions.administrator:
                    print("⛔ Skipped: executor is bot or admin")
                    return

                await self.apply_penalty(executor, guild, f"Deleted voice channel '{channel.name}' with {member_count} members inside")

async def setup(bot):
    await bot.add_cog(VoiceGuard(bot))
