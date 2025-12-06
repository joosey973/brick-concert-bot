from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

async def get_role_based_keyboard(role):
    # if role == 'member' or role == 'user':
    #     return await get_user_keyboard()
    if role == 'leading':
        return await get_leading_keyboard()
    elif role == 'checker':
        return await get_checker_keyboard()
    elif role == 'admin':
        return await get_admin_keyboard()
    # return await get_user_keyboard()


async def get_user_keyboard():
    buttons = [
        [KeyboardButton(text='🎫 Получить билет')],
        [KeyboardButton(text='📋 Мои билеты')],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


async def get_leading_keyboard():
    buttons = [
        [KeyboardButton(text='💰 Розыгрыш среди групп')],
        [KeyboardButton(text='🎲 Розыгрыш среди зала')],
        [KeyboardButton(text='🔄 Отправить голосвание (по группам)')],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


async def get_checker_keyboard():
    buttons = [
        [KeyboardButton(text='🎫 Проверить билет')],
        [KeyboardButton(text='🎫 Получить билет')],
        [KeyboardButton(text='📋 Мои билеты')],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


async def get_admin_keyboard():
    buttons = [
        [KeyboardButton(text='➕ Добавить концерт')],
        [KeyboardButton(text='📋 Управление концертами'), KeyboardButton(text='👥 Управление ролями')],
        [KeyboardButton(text='🎫 Проверить билет'), KeyboardButton(text='📊 Статистика')],
        [KeyboardButton(text='🎰 Розыгрыш')],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


async def raffle_keyboard():
    buttons = [
        [KeyboardButton(text='💰 Розыгрыш среди групп'), KeyboardButton(text='🎲 Розыгрыш среди зала')],
        [KeyboardButton(text='👹 Рассылка нашего тгк')],
        [KeyboardButton(text='🔄 Отправить голосвание (по группам)')],
        [KeyboardButton(text='🔙 Назад в меню')],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


async def get_back_to_edit_creation_keyboard():
    buttons = [
        [KeyboardButton(text='⬅️ Назад'), KeyboardButton(text='❌ Отмена создания')]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


async def cancel_creation_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='❌ Отмена создания')]], resize_keyboard=True)


async def get_photos_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='💾 Сохранить фото')],
            [KeyboardButton(text='🗑️ Очистить список')],
            [KeyboardButton(text='↩️ Назад')],
            [KeyboardButton(text='❌ Отмена создания')],
        ],
        resize_keyboard=True,
    )


async def cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='❌ Отмена')]
        ],
        resize_keyboard=True
    )


async def confirm_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='✅ Да, назначить'), KeyboardButton(text='❌ Нет, выбрать другого')],
            [KeyboardButton(text='❌ Отмена')]
        ],
        resize_keyboard=True
    )


async def final_confirm_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='✅ Подтвердить назначение'), KeyboardButton(text='❌ Отменить')]
        ],
        resize_keyboard=True
    )


async def users_list_keyboard(users):
    buttons = []
    for user in users[:10]:
        display_name = user.get('full_name', 'Без имени')
        if user.get('username'):
            display_name = f"{display_name} (@{user['username']})"
        
        buttons.append([
            InlineKeyboardButton(
                text=display_name[:40],
                callback_data=f"select_user_{user['telegram_id']}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text='❌ Отмена', callback_data='cancel_selection')
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def manage_roles_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='🎤 Назначить ведущего'), KeyboardButton(text='👤 Снять роль ведущего')],
            [KeyboardButton(text='🎫 Назначить проверяющего'), KeyboardButton(text='🛑 Снять роль проверяющего')],
            [KeyboardButton(text='📋 Список по ролям')],
            [KeyboardButton(text='🔙 Назад')]
        ],
        resize_keyboard=True
    )


async def role_list_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='👑 Ведущие'), KeyboardButton(text='🎫 Проверяющие')],
            [KeyboardButton(text='👥 Обычные пользователи'), KeyboardButton(text='👨‍💻 Администраторы')],
            [KeyboardButton(text='🔙 Назад')]
        ],
        resize_keyboard=True
    )


async def statistics_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📊 Статистика по концертам')],
            [KeyboardButton(text='👥 Статистика по пользователям')],
            [KeyboardButton(text='🎫 Статистика по билетам')],
            [KeyboardButton(text='🔙 Назад')]
        ],
        resize_keyboard=True
    )


async def check_ticket_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='🎫 Проверить по коду')],
            [KeyboardButton(text='🔙 Назад')]
        ],
        resize_keyboard=True
    )