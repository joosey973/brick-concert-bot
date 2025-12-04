import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN = os.environ.get('BOT_TOKEN')
    CHANNEL_USERNAMES = os.environ.get('CHANNEL_USERNAMES').replace(' ', '').split(',')
    DATABASE_URL = os.environ.get('DATABASE_URL')
    ADMIN_IDS = list(map(int, os.environ.get('ADMIN_IDS').replace(' ', '').split(',')))
    groups = ['Смысловая нагрузка', 'Реинкарнация',
              'Послезавтра', 'Only minus one',
              'ЭлектропроспектЪ!', 'АСТРАV',
              'Китовые песни', 'Завтрак чемпиона',
              'Степень свободы', 'Признаки чувств',
              'Строй Аккорд', 'Spring Fever']


config = Config()
