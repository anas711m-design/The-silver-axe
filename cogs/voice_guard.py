import discord
from discord.ext import commands
from datetime import datetime, timezone
import asyncio
from collections import defaultdict
from config import MOD_ROLE_ID, PENALTY_SECONDS, PENALIZED_ROLE_ID

class VoiceGuard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.disconnect_tracker = defaultdict(list)
        self.global_penalty_counter = 0  # Global counter across all users

    async def apply_penalty(self, executor, guild, reason):
        mod_role = guild.get_role(MOD_ROLE_ID)
        penalized_role = guild.get_role(PENALIZED_ROLE_ID)

        if not mod_role or mod_role not in executor.roles:
            print(f"⛔ Skipped: {executor.name} does not have the mod role.")
            return

        # Increment global counter
        self.global_penalty_counter += 1
        penalty_number = self.global_penalty_counter

        # Save original nickname to restore later
        original_nickname = executor.nick

        try:
            print(f"⚠️  Penalty #{penalty_number} applied to {executor.name} | Reason: {reason}")

            # Change nickname
            await executor.edit(nick=f"ضحية الرأس الفضي #{penalty_number}", reason=reason)

            # Remove mod role, add penalized role
            await executor.remove_roles(mod_role, reason=reason)
            if penalized_role:
                await executor.add_roles(penalized_role, reason="Penalty applied")

            # Wait for penalty duration
            await asyncio.sleep(PENALTY_SECONDS)

            # Restore everything
            await executor.edit(nick=original_nickname, reason="Penalty finished.")
            await executor.add_roles(mod_role, reason="Penalty finished.")
            if penalized_role:
                await executor.remove_roles(penalized_role, reason="Penalty finished.")

            print(f"✅ Penalty #{penalty_number} finished. {executor.name} restored.")

        except Exception as e:
            print(f"❌ Error during penalty #{penalty_number} for {executor.name}: {e}")

    # ---------------------------------------------------------------
    # FEATURE 1: 3 disconnects within 2 minutes → penalty
    # ---------------------------------------------------------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel is not None and after.channel is None:
            print(f"🔊 {member.name} disconnected from {before.channel.name}")
            guild = member.guild
            await asyncio.sleep(1.5)

            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.member_disconnect):
                time_diff = (datetime.now(timezone.utc) - entry.created_at).total_seconds()
                print(f"📋 Audit log: {entry.user.name} | time_diff: {time_diff:.2f}s")

                if time_diff < 90:
                    executor = entry.user

                    print(f"👤 Executor: {executor.name} | bot: {executor.bot} | admin: {executor.guild_permissions.administrator}")

                    if executor.bot or executor.guild_permissions.administrator:
                        print("⛔ Skipped: executor is bot or admin")
                        return

                    mod_role = guild.get_role(MOD_ROLE_ID)
                    print(f"🎭 Role found: {mod_role} | has role: {mod_role in executor.roles if mod_role else 'N/A'}")

                    if not mod_role or mod_role not in executor.roles:
                        return

                    now = datetime.now(timezone.utc).timestamp()

                    # Track this disconnect
                    self.disconnect_tracker[executor.id].append(now)

                    # Keep only disconnects from the last 120 seconds (2 minutes)
                    self.disconnect_tracker[executor.id] = [
                        t for t in self.disconnect_tracker[executor.id]
                        if now - t <= 120
                    ]

                    count = len(self.disconnect_tracker[executor.id])
                    print(f"📊 {executor.name} disconnect count in last 2 min: {count}/3")

                    if count >= 3:
                        # Don't clear counter so it keeps accumulating
                        self.disconnect_tracker[executor.id] = []
                        await self.apply_penalty(executor, guild, "Disconnected 3+ members in 2 minutes")
                    break

    # ---------------------------------------------------------------
    # FEATURE 2: Deleting a voice channel with people in it → penalty
    # ---------------------------------------------------------------
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if not isinstance(channel, discord.VoiceChannel):
            return

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

            if time_diff < 90:
                executor = entry.user

                print(f"👤 Executor: {executor.name} | bot: {executor.bot} | admin: {executor.guild_permissions.administrator}")

                if executor.bot or executor.guild_permissions.administrator:
                    print("⛔ Skipped: executor is bot or admin")
                    return

                await self.apply_penalty(executor, guild, f"Deleted voice channel '{channel.name}' with {member_count} members inside")

async def setup(bot):
    await bot.add_cog(VoiceGuard(bot))
