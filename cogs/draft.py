import discord, logging
from discord.ext import commands
from discord.commands import Option
import app.config as config
import app.dbinfo as dbinfo

logger = logging.getLogger(__name__)

LOL_season = "1"

class Draft(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_pick = 0
        # Testing
        self.draft_order = ["SDA", "DEN", "HAV", "WAR", "LAG", "HOU"]

    async def get_next_pick(self):
        if self.current_pick < len(self.draft_order):
            team_code = self.draft_order[self.current_pick]
            team_info = dbinfo.team_collection.find_one({"team_code": team_code})

            if team_info:
                gm_id = team_info.get("gm_id")
                self.current_pick += 1
                return team_info["team_name"], gm_id
        return None, None

    @commands.slash_command(guild_ids=[config.lol_server], description="Starts the draft")
    @commands.has_role("Bot Guy")
    async def start_draft(self, ctx):
        draft_channel = self.bot.get_channel(config.bot_testing_channel)
        if draft_channel:
            await draft_channel.send(f"The United Rogue League of Legends draft for Season {LOL_season} is starting...")
            team_name, gm_id= await self.get_next_pick()

            if team_name and gm_id:
                gm_role = ctx.guild.get_role(gm_id)
                if gm_role:
                    await draft_channel.send(f"{gm_role.mention}, you are now on the clock for {team_name}!")
                else:
                    await draft_channel.send(f"GM role for {team_name} not found.")
            
            await ctx.respond("Draft started.", ephemeral=True)
            
        else:
            logger.error("Draft channel not found.")
            await ctx.respond("Draft channel not found.", ephemeral=True)

    @commands.slash_command(guild_ids=[config.lol_server], description="Make your pick.")
    async def draft_pick(self, ctx, player_name: Option(discord.Member)):
        draft_channel = self.bot.get_channel(config.bot_testing_channel)
        if draft_channel:
            team_name, gm_id = await self.get_next_pick()

            if team_name and gm_id:
                gm_role = ctx.guild.get_role(gm_id)
                if gm_role:
                    await draft_channel.send(f"{gm_role} selected {player_name.mention}.")
                    await draft_channel.send(f"{gm_role.mention} ({team_name}), you're on the clock!")
                else:
                    await draft_channel.send(f"{team_name}'s GM role not found.")
            else:
                await draft_channel.send(f"The draft is over. Thank you all for participating!")
            await ctx.respond(f"Player {player_name} picked.", ephemeral=True)

def setup(bot):
    bot.add_cog(Draft(bot))