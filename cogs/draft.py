import discord, logging
from discord.ext import commands
from discord.commands import Option
import app.config as config
import app.dbinfo as dbinfo

logger = logging.getLogger(__name__)

LOL_season = "1"
TOTAL_ROUNDS = 6
SALARY_CAP = 600

class Draft(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_pick = 0
        self.draft_order = []
        self.draft_rounds = []
        self.picks = {}
        self.salary_caps = {}

    def generate_snake_order(self, initial_order):
        logger.info(f"Generating snak draft order with initial order: {initial_order}")
        rounds = []
        for round_num in range(TOTAL_ROUNDS):
            if round_num % 2 == 0:
                # Normal order for odd rounds
                rounds.append(initial_order)
            else:
                # Reverse order for even rounds
                rounds.append(initial_order[::-1])
        logger.debug(f"Generated snake draft rounds: {rounds}")
        return [team for round_order in rounds for team in round_order]
    
    def player_already_picked(self, player_name):
        logger.info(f"Checking if player {player_name} has already been drafted by another team.")
        for players in self.picks.values():
            if player_name in players:
                logger.warning(f"Player {player_name} has already been drafted")
                return True
        return False
    
    async def get_player_salary(self, player_name):
        logger.info(f"Fetching salary for player: {player_name.display_name}")
        player_info = dbinfo.player_collection.find_one({"discord_id": player_name.id})
        if player_info:
            salary = player_info.get("salary", 0)
            logger.debug(f"Found salary for {player_name.display_name}: ${salary}")
            return salary
        logger.warning(f"No salary info found for player: {player_name.display_name}")
        return 0

    @commands.slash_command(guild_ids=[config.lol_server], description="Sets the draft order for the snake draft")
    @commands.has_any_role("Bot Guy", "League Ops")
    async def set_draft_order(self, ctx, draft_order: Option(str, "Comma-separated team codes for the draft order")):
        logger.info(f"Setting draft order: {draft_order}")
        initial_order = [team.strip() for team in draft_order.split(", ")]
        self.draft_order = initial_order
        self.draft_rounds = self.generate_snake_order(initial_order)
        
        # Initialize picks dictionary using team_code (e.g., SDA)
        self.picks = {team: [] for team in initial_order}
        self.salary_caps = {team: SALARY_CAP for team in initial_order}
        logger.info(f"Draft order set for {TOTAL_ROUNDS} rounds with initial order: {self.draft_order}")

        # Build response message with round-by-round breakdown
        draft_response = ""
        for round_num in range(TOTAL_ROUNDS):
            round_teams = self.draft_rounds[round_num * len(initial_order):(round_num + 1) * len(initial_order)]
            draft_response += f"Round {round_num + 1}: {', '.join(round_teams)}\n"

        await ctx.respond(f"Draft order set for {TOTAL_ROUNDS} rounds with snake draft:\n{draft_response}")

    async def get_next_pick(self):
        logger.debug(f"Getting next pick, current pick number: {self.current_pick}")
        if self.current_pick < len(self.draft_rounds):
            team_code = self.draft_rounds[self.current_pick]
            # Fetch the team info from the database using the team_code
            team_info = dbinfo.team_collection.find_one({"team_code": team_code})

            if team_info:
                gm_role_id = team_info.get("gm_id")  # Ensure this is the GM role ID
                logger.debug(f"Found GM role ID for team {team_code}: {gm_role_id}")
                return team_code, gm_role_id  # Return team_code and gm_role_id
            logger.warning(f"Team info not found for team code: {team_code}")
        return None, None

    @commands.slash_command(guild_ids=[config.lol_server], description="Starts the draft")
    @commands.has_any_role("Bot Guy", "League Ops")
    async def start_draft(self, ctx):
        logger.info("Starting the draft...")
        draft_channel = self.bot.get_channel(config.draft_channel)

        # Ensure draft order has been set
        if not self.draft_rounds:
            logger.error("Draft order not set. Cannot start draft.")
            await ctx.respond("Draft order is not set. Please run the following command to set the draft order: '/set_draft_order'", ephemeral=True)
            return
        
        if draft_channel:
            await draft_channel.send(f"The United Rogue League of Legends draft for Season {LOL_season} is starting...")
            team_code, gm_id = await self.get_next_pick()

            if team_code and gm_id:
                gm_role = ctx.guild.get_role(gm_id)
                if gm_role:
                    logger.info(f"{gm_role.name} is on the clock for team {team_code}")
                    await draft_channel.send(f"{gm_role.mention}, you are now on the clock for {team_code}!")
                else:
                    logger.error(f"GM role for {team_code} not found.")
                    await draft_channel.send(f"GM role for {team_code} not found.")
            
            await ctx.respond("Draft started.", ephemeral=True)
            
        else:
            logger.error("Draft channel not found.")
            await ctx.respond("Draft channel not found.", ephemeral=True)

    @commands.slash_command(guild_ids=[config.lol_server], description="Make your pick.")
    async def draft_pick(self, ctx, player_name: Option(discord.Member)):
        logger.info(f"{ctx.author} is attempting to pick {player_name.display_name}")
        draft_channel = self.bot.get_channel(config.draft_channel)

        # Get team and GM that is on the clock
        team_code, gm_role_id = await self.get_next_pick()

        # Restrict the command to only the GM on the clock
        gm_role = ctx.guild.get_role(gm_role_id)
        if gm_role not in ctx.author.roles:
            logger.warning(f"{ctx.author} attempted to pick, but they are not the GM on the clock.")
            await ctx.respond("You are not the GM on the clock!", ephemeral=True)
            return
        
        # Check if the player has "Not Eligible" or "Spectator" role
        not_eligible_role = discord.utils.get(ctx.guild.roles, name="Not Eligible")
        spectator_role = discord.utils.get(ctx.guild.roles, name="Spectator")

        if player_name.bot:
            logger.warning(f"{player_name.display_name} is a bot and cannot be drafted.")
            await ctx.respond(f"{player_name.display_name} cannot be drafted, because they're a bot...", ephemeral=True)
            return
        
        if not_eligible_role in player_name.roles:
            logger.warning(f"{player_name.display_name} is marked as Not Eligible and cannot be drafted.")
            await ctx.respond(f"{player_name.display_name} cannot be drafted as they are not eligible.", ephemeral=True)
            return

        if spectator_role in player_name.roles:
            logger.warning(f"{player_name.display_name} is a spectator and cannot be drafted.")
            await ctx.respond(f"{player_name.display_name} cannot be drafted as they are a 'Spectator'.", ephemeral=True)
            return
        
        # Fetch player's salary
        player_salary = await self.get_player_salary(player_name)

        # Check if team's remaining salary can afford player
        if self.salary_caps[team_code] < player_salary:
            logger.warning(f"Team {team_code} cannot afford {player_name.display_name}'s salary of ${player_salary}")
            await ctx.respond(f"{player_name.display_name}'s salary of ${player_salary} exceeds your remaining cap of ${self.salary_caps[team_code]}.", ephemeral=True)
            return

        if draft_channel:
            if self.player_already_picked(player_name.display_name):
                logger.warning(f"{player_name.display_name} has already been drafted.")
                await ctx.respond(f"{player_name.display_name} has already been drafted. Please choose another player.", ephemeral=True)
                return

            # Announce the current pick
            if team_code and gm_role_id:
                logger.info(f"{gm_role.name} ({team_code}) selected {player_name.display_name}.")
                await draft_channel.send(f"{gm_role.mention} ({team_code}) selected {player_name.mention}.")

                # Store the pick in the picks dictionary using team_code (e.g., SDA)
                self.picks[team_code].append(player_name.display_name)

                # Deduct player's salary from team's remaining cap
                self.salary_caps[team_code] -= player_salary

                # Notify GM of their remaining cap
                await draft_channel.send(f"{gm_role.mention}, your remaining cap is ${self.salary_caps[team_code]}.")

            # Move to the next pick only after announcing the current pick
            self.current_pick += 1

            # Calculate the current round
            teams_per_round = len(self.draft_order)
            current_round = (self.current_pick // teams_per_round) + 1

            # Check if round has changed
            if self.current_pick % teams_per_round == 0:
                logger.info(f"Round {current_round} has begun.")
                await draft_channel.send(f"**Round {current_round} has begun!**")

            next_team_code, next_gm_id = await self.get_next_pick()

            if next_team_code and next_gm_id:
                next_gm_role = ctx.guild.get_role(next_gm_id)
                if next_gm_role:
                    logger.info(f"{next_gm_role.name} is now on the clock for {next_team_code}.")
                    await draft_channel.send(f"{next_gm_role.mention} ({next_team_code}), you're on the clock!")
                else:
                    logger.error(f"GM role for {next_team_code} not found.")
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
    async def draft_history(self, ctx):
        logger.info("Displaying draft history...")
        picks_message = ""
        for team, players in self.picks.items():
            picks_message += f"{team}: {', '.join(players)}\n"
        await ctx.respond(f"Draft History:\n{picks_message}", ephemeral=True)


    @commands.slash_command(guild_ids=[config.lol_server], description="Show the draft leaderboard")
    async def draft_leaderboard(self, ctx):
        logger.info("Displaying draft leaderboard...")
        leaderboard = sorted(self.picks.items(), key=lambda x:len(x[1]), reverse=True)
        leaderboard_message = "Draft Leaderboard:\n"
        for team, players in leaderboard:
            total_salary = SALARY_CAP - self.salary_caps[team]
            leaderboard_message += f"{team}: {len(players)} players, ${total_salary} spent\n"
        await ctx.respond(leaderboard_message)

def setup(bot):
    bot.add_cog(Draft(bot))
