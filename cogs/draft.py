import discord, logging
from discord.ext import commands
from discord.commands import Option
import app.config as config
import app.dbinfo as dbinfo

logger = logging.getLogger(__name__)

LOL_season = "1"
TOTAL_ROUNDS = 6

class Draft(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_pick = 0
        self.draft_order = []
        self.draft_rounds = []
        self.picks = {}

    def generate_snake_order(self, initial_order):
        rounds = []
        for round_num in range(TOTAL_ROUNDS):
            if round_num % 2 == 0:
                # Normal order for odd rounds
                rounds.append(initial_order)
            else:
                # Reverse order for even rounds
                rounds.append(initial_order[::-1])
        return [team for round_order in rounds for team in round_order]
    
    def player_already_picked(self, player_name):
        for players in self.picks.values():
            if player_name in players:
                return True
        return False

    @commands.slash_command(guild_ids=[config.lol_server], description="Sets the draft order for the snake draft")
    @commands.has_role("Bot Guy")
    async def set_draft_order(self, ctx, draft_order: Option(str, "Comma-separated team codes for the draft order")):
        initial_order = [team.strip() for team in draft_order.split(", ")]
        self.draft_order = initial_order
        self.draft_rounds = self.generate_snake_order(initial_order)

        # Initialize picks dictionary using team_code (e.g., SDA)
        self.picks = {team: [] for team in initial_order}

        # Build response message with round-by-round breakdown
        draft_response = ""
        for round_num in range(TOTAL_ROUNDS):
            round_teams = self.draft_rounds[round_num * len(initial_order):(round_num + 1) * len(initial_order)]
            draft_response += f"Round {round_num + 1}: {', '.join(round_teams)}\n"

        await ctx.respond(f"Draft order set for {TOTAL_ROUNDS} rounds with snake draft:\n{draft_response}")

    async def get_next_pick(self):
        if self.current_pick < len(self.draft_rounds):
            team_code = self.draft_rounds[self.current_pick]
            team_info = dbinfo.team_collection.find_one({"team_code": team_code})

            if team_info:
                gm_id = team_info.get("gm_id")
                return team_code, gm_id  # Return team_code to maintain consistency
        return None, None

    @commands.slash_command(guild_ids=[config.lol_server], description="Starts the draft")
    @commands.has_role("Bot Guy")
    async def start_draft(self, ctx):
        draft_channel = self.bot.get_channel(config.bot_testing_channel)

        # Ensure draft order has been set
        if not self.draft_rounds:
            await ctx.respond("Draft order is not set. Please run the following command to set the draft order: '/set_draft_order'", ephemeral=True)
            return
        
        if draft_channel:
            await draft_channel.send(f"The United Rogue League of Legends draft for Season {LOL_season} is starting...")
            team_code, gm_id = await self.get_next_pick()

            if team_code and gm_id:
                gm_role = ctx.guild.get_role(gm_id)
                if gm_role:
                    await draft_channel.send(f"{gm_role.mention}, you are now on the clock for {team_code}!")
                else:
                    await draft_channel.send(f"GM role for {team_code} not found.")
            
            await ctx.respond("Draft started.", ephemeral=True)
            
        else:
            logger.error("Draft channel not found.")
            await ctx.respond("Draft channel not found.", ephemeral=True)

    @commands.slash_command(guild_ids=[config.lol_server], description="Make your pick.")
    async def draft_pick(self, ctx, player_name: Option(discord.Member)):
        draft_channel = self.bot.get_channel(config.bot_testing_channel)

        if draft_channel:
            # Check if the player has already been picked
            if self.player_already_picked(player_name.display_name):
                await ctx.respond(f"{player_name.display_name} has already been drafted. Please choose another player.", ephemeral=True)
                return  # Exit if player is already picked

            # Announce the current pick (before incrementing the pick)
            team_code, gm_id = await self.get_next_pick()

            if team_code and gm_id:
                gm_role = ctx.guild.get_role(gm_id)
                if gm_role:
                    await draft_channel.send(f"{gm_role.mention} ({team_code}) selected {player_name.mention}.")

                    # Store the pick in the picks dictionary using team_code (e.g., SDA)
                    self.picks[team_code].append(player_name.display_name)
                else:
                    await draft_channel.send(f"GM role for {team_code} not found.")

            # Move to the next pick only after announcing the current pick
            self.current_pick += 1
            next_team_code, next_gm_id = await self.get_next_pick()

            if next_team_code and next_gm_id:
                next_gm_role = ctx.guild.get_role(next_gm_id)
                if next_gm_role:
                    await draft_channel.send(f"{next_gm_role.mention} ({next_team_code}), you're on the clock!")
                else:
                    await draft_channel.send(f"GM role for {next_team_code} not found.")
            else:
                # When draft is over, send the draft results to staff channel
                staff_channel = self.bot.get_channel(config.transaction_bot_channel)
                if staff_channel:
                    picks_message = ""
                    for team, players in self.picks.items():
                        picks_message += f"{team}: {', '.join(players)}\n"  # Added newline for formatting
                    await staff_channel.send(f"The draft has concluded. Here are the final picks:\n{picks_message}")
                await draft_channel.send(f"United Rogue's League of Legends Season {LOL_season} Draft has concluded. Thank you all for participating!")
            await ctx.respond(f"Player {player_name} picked for {team_code}.", ephemeral=True)

    @commands.slash_command(guild_ids=[config.lol_server], description="Show picks to this this point in the draft")
    @commands.has_role("Bot Guy")
    async def show_picks(self, ctx):
        picks_message = ""
        for team, players in self.picks.items():
            picks_message += f"{team}: {', '.join(players)}\n"
        await ctx.respond(f"Draft Picks so far:\n{picks_message}", ephemeral=True)


def setup(bot):
    bot.add_cog(Draft(bot))
