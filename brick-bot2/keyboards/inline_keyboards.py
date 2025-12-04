from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import config


async def confirm_use_ticket_keyboard(ticket_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text='✅ Отметить как использованный', callback_data=f'use_ticket_{ticket_id}')
    ]])


async def all_groups_keyboard():
    groups = config.groups
    buttons = []
    count = 0
    cnt = 1
    temp = []
    for i in groups:
        temp.append(InlineKeyboardButton(text=i, callback_data=f'group_{cnt}'))
        cnt += 1
        count += 1
        
        if count == 3:
            buttons.append(temp)
            temp = []
            count = 0
    buttons.append(temp)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_subscription_keyboard_with_link(channels):
    buttons = []
    if len(channels) == 1:
        buttons.append([InlineKeyboardButton(text='📢 Перейти в канал', url=f'https://t.me/{channels[0]}')])
    else:
        for index, channel in enumerate(channels):
            buttons.append([
                InlineKeyboardButton(f'📢 Перейти в канал {index}',
                                     url=f'https://t.me/{channel}')
            ])
    
    buttons.append([InlineKeyboardButton(text='✅ Я подписался', callback_data='check_subscription')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_concerts_keyboard(concerts):
    buttons = []
    for concert in concerts:
        buttons.append([
            InlineKeyboardButton(
                text=f'''{concert['name']} ({concert['date'].strftime('%d.%m.%Y')})''',
                callback_data=f'''concert_{concert['id']}'''
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_available_concerts_keyboard(tickets):
    buttons = []
    for ticket in tickets:
        buttons.append([
            InlineKeyboardButton(
                text=f'''{ticket['concert_name']} ({ticket['concert_date'].strftime('%d.%m.%Y')})''',
                callback_data=f'''ticket_concert_{ticket['concert_id']}''',
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_admin_concerts_keyboard(concerts):
    buttons = []
    for concert in concerts:
        status = '🟢' if concert.get('is_active', True) else '🔴'
        buttons.append([
            InlineKeyboardButton(
                text=f'''{status} {concert['name']} ({concert['date'].strftime('%d.%m.%Y')})''',
                callback_data=f'admin_concert_{concert['id']}'
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def get_concert_management_keyboard(status, concert_id):
    act_inact_text = '🟢 Активировать' if not status else '🔴 Деактивировать'
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='✏️ Редактировать', callback_data=f'''edit_concert_{concert_id}'''),
            InlineKeyboardButton(text='📢 Рассылка', callback_data=f'broadcast_concert_{concert_id}')
        ],
        [
            InlineKeyboardButton(text=act_inact_text, callback_data=f'''deactivate_concert_{concert_id}'''),
            InlineKeyboardButton(text='📋 Список концертов', callback_data='list_concerts')
        ]
    ])


async def get_edit_concert_keyboard(concert_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='📝 Название', callback_data=f'edit_name_{concert_id}'),
            InlineKeyboardButton(text='📄 Описание', callback_data=f'edit_description_{concert_id}')
        ],
        [
            InlineKeyboardButton(text='📅 Дата', callback_data=f'edit_date_{concert_id}'),
            InlineKeyboardButton(text='📍 Адрес', callback_data=f'edit_address_{concert_id}')
        ],
        [
            InlineKeyboardButton(text='🖼️ Фото', callback_data=f'edit_photos_{concert_id}')
        ],
        [
            InlineKeyboardButton(text='⬅️ Назад', callback_data=f'back_to_management_{concert_id}')
        ]
    ])


async def get_photos_edit_keyboard(concert_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text='💾 Сохранить фото',
                callback_data=f'save_photos_{concert_id}'
            )],
            [InlineKeyboardButton(
                text='🗑️ Очистить список',
                callback_data=f'clear_photos_{concert_id}'
            )],
            [InlineKeyboardButton(
                text='↩️ Назад',
                callback_data=f'back_to_edit_menu_{concert_id}'
            )],
            [InlineKeyboardButton(
                text='❌ Отмена редактирования',
                callback_data=f'back_to_concert_card_{concert_id}'
            )],
        ]
    )


async def get_back_to_edit_keyboard(concert_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='⬅️ Назад', callback_data=f'back_to_edit_menu_{concert_id}'),
            InlineKeyboardButton(text='❌ Отмена редактирования', callback_data=f'back_to_concert_card_{concert_id}'),
        ]])
