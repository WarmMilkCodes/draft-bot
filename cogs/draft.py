import discord, logging
from discord.ext import commands
import app.config as config
import app.dbinfo as dbinfo

logger = logging.getLogger(__name__)

class Draft(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_pick = 0
        self.draft_order = []

    @commands.slash_command(guild_ids=[config.lol_server], description="Starts the draft")
    @commands.has_role("Bot Guy")
    async def start_draft(self, ctx):
        draft_channel = self.bot.get_channel(config.bot_testing_channel)
        if draft_channel:
            await draft_channel.send("Draft is starting...")
        else:
            await ctx.respond("Draft channel not found.", ephemeral=True)


def setup(bot):
    bot.add_cog(Draft(bot))