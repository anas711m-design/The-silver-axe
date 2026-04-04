import discord
from discord.ext import commands
from datetime import datetime, timezone
import asyncio
from config import MOD_ROLE_ID, PENALTY_SECONDS

class VoiceGuard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

                    if role and role in executor.roles:
                        try:
                            print(f"⚠️  {executor.name} disconnected a member. Applying penalty.")
                            await executor.remove_roles(role, reason="Disconnected member (penalty)")
                            await asyncio.sleep(PENALTY_SECONDS)
                            await executor.add_roles(role, reason="Penalty finished.")
                            print(f"✅ Role restored to {executor.name}.")
                        except Exception as e:
                            print(f"❌ Error: {e}")

async def setup(bot):
    await bot.add_cog(VoiceGuard(bot))
