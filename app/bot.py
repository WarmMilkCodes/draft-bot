import discord, os, asyncio
from discord.ext import commands
from utils.logging_config import setup_logging
from config import DISCORD_TOKEN

logger = setup_logging()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='?', intents=intents)

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="UR LOL Draft"))


# Load all cogs
def load_extensions():
    logger.info("Loading cogs...")
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                bot.load_extension(f'cogs.{filename[:-3]}')
                logger.info(f'Successfully loaded cogs.{filename[:-3]}')
            except Exception as e:
                logger.error(f'Error loading cogs.{filename[:-3]}: {e}')


async def main():
    async with bot:
        load_extensions()
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())