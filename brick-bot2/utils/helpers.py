from config import config

from utils.initialization import bot

async def check_channel_subscription(user_id):
    if not config.CHANNEL_USERNAMES:
        return True
    
    channels = config.CHANNEL_USERNAMES
    for channel in channels:
        member = await bot.get_chat_member(f'@{channel}', user_id)
        if member.status not in ('member', 'administrator', 'creator'):
            return False
    return True