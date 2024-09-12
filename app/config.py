import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME")
INTENT_COLLECTION = os.getenv("INTENT_COLLECTION")
PLAYER_COLLECTION = os.getenv("PLAYER_COLLECTION")
TEAM_COLLECTION = os.getenv("TEAM_COLLECTION")

# Server ID
lol_server = 1171263858971770901

# Server Channels
bot_admin_channel = 1171263860716601366
transaction_bot_channel = 1264833838916567090
transactions_channel = 1171263861987475482
bot_report_channel = 1171263860716601368
bot_testing_channel = 1171263860716601367