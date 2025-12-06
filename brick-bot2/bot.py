import asyncio
import datetime
import random

import aiogram
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import types
from aiogram.filters import Command

from config import config
from database.database_queries import database
import keyboards.reply_keyboards as rep_key
import keyboards.inline_keyboards as inl_key
from utils.initialization import bot, dp
import utils.helpers as helpers
import texts as text
from database.models import User


class EditConcertStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_date = State()
    waiting_for_address = State()
    waiting_for_photos = State()
    concert_id = State()


class CreateConcertStates(StatesGroup):
    name = State()
    description = State()
    date = State()
    address = State()
    photos = State()


class AppointLeadingStates(StatesGroup):
    searching_user = State()
    confirming_user = State()
    confirming_appointment = State()


class AppointCheckerStates(StatesGroup):
    searching_user = State()
    confirming_user = State()
    confirming_appointment = State()


class RemoveLeadingStates(StatesGroup):
    searching_user = State()
    confirming_user = State()
    confirming_removal = State()


class RemoveCheckerStates(StatesGroup):
    searching_user = State()
    confirming_user = State()
    confirming_removal = State()


class CheckTicketStates(StatesGroup):
    waiting_for_ticket_code = State()


class StatisticsStates(StatesGroup):
    waiting_for_statistics_type = State()


@dp.message(Command('start'))
async def start(message: types.Message):
    user = await database.get_or_create_user(message.from_user.id,
                                             message.from_user.username,
                                             message.from_user.full_name,)
    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)

    if is_subscribed:
        keyboard = await rep_key.get_role_based_keyboard(user.role)
        await message.answer(text.subscribed_1, reply_markup=keyboard)
    else:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        await message.answer(text.not_subscribed_1, reply_markup=keyboard)


@dp.message(F.text == '➕ Добавить концерт')
async def add_concert_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS:
        return await message.answer('❌ У вас нет доступа к этой команде.')

    await state.update_data(photos=[])
    keyboard = await rep_key.cancel_creation_keyboard()
    await message.answer(
        '🎵 Введите название концерта:',
        reply_markup=keyboard,
    )
    await state.set_state(CreateConcertStates.name)


@dp.message(CreateConcertStates.name, F.text == '❌ Отмена создания')
async def back_from_name(message: types.Message, state: FSMContext):
    await state.clear()
    keyboard = await rep_key.get_admin_keyboard()
    await message.answer('❌ Создание концерта отменено', reply_markup=keyboard)


@dp.message(CreateConcertStates.name)
async def process_creation_of_name(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена создания':
        await state.clear()
        return
    await state.update_data(name=message.text)
    keyboard = await rep_key.get_back_to_edit_creation_keyboard()
    await message.answer('📝 Введите описание концерта:', reply_markup=keyboard)
    await state.set_state(CreateConcertStates.description)


@dp.message(CreateConcertStates.description, F.text == '⬅️ Назад')
async def back_from_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if 'description' in data:
        new_data = {k: v for k, v in data.items() if k != 'description'}
        await state.set_data(new_data)

    await state.set_state(CreateConcertStates.name)
    keyboard = await rep_key.cancel_creation_keyboard()
    await message.answer(
        '🎵 Введите название концерта:',
        reply_markup=keyboard,
    )


@dp.message(F.text == '🔄 Отправить голосвание (по группам)')
async def show_voting_menu(message: types.Message):
    user = await database.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )

    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await message.answer(text.not_subscribed_1, reply_markup=keyboard)

    if user.role not in ('admin', 'leading'):
        await message.answer('Эта функция доступна только администраторам и ведущим.')
        return

    await message.answer('⏳ Начинаю рассылку...')
    await asyncio.sleep(4)
    session = database._get_session()
    users = session.query(User).filter(
        User.subscribed == True, User.role.in_(['member', 'user'])).all()
    total_users = len(users)
    sent_count = 0
    already_voted_count = 0
    for user in users:
        has_voted = await database.has_user_voted(user.id)
        if not has_voted:
            await database.show_voting_keyboard(bot, user.telegram_id)
            sent_count += 1
        else:
            already_voted_count += 1

    report = f"""
                📊 Отчет о рассылке:
👥 Всего подписчиков: {total_users}
✅ Уже проголосовали: {already_voted_count}
📢 Получили голосование: {sent_count}
❌ Не отправилось: {total_users - sent_count - already_voted_count}
    """
    await message.answer(report)


@dp.message(CreateConcertStates.description)
async def process_description_creation(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена создания':
        await state.clear()
        keyboard = await rep_key.get_admin_keyboard()
        await message.answer('❌ Добавление концерта отменено', reply_markup=keyboard)
        return

    await state.update_data(description=message.text)
    keyboard = await rep_key.get_back_to_edit_creation_keyboard()
    await message.answer(
        '📅 Введите дату концерта в формате ДД.ММ.ГГГГ ЧЧ:ММ:\n\n'
        'Пример: 25.12.2024 19:00',
        reply_markup=keyboard,
    )
    await state.set_state(CreateConcertStates.date)


@dp.message(CreateConcertStates.date, F.text == '⬅️ Назад')
async def back_from_date(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if 'date' in data:
        new_data = {k: v for k, v in data.items() if k != 'date'}
        await state.set_data(new_data)

    await state.set_state(CreateConcertStates.description)
    keyboard = await rep_key.get_back_to_edit_creation_keyboard()
    await message.answer(
        '📝 Введите описание концерта:',
        reply_markup=keyboard,
    )


@dp.message(CreateConcertStates.date)
async def process_date_creation(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        keyboard = await rep_key.get_admin_keyboard()
        await state.clear()
        await message.answer('❌ Добавление концерта отменено', reply_markup=keyboard)
        return

    date_str = message.text
    try:
        concert_date = datetime.datetime.strptime(date_str, '%d.%m.%Y %H:%M')
    except ValueError:
        return await message.answer(
            '❌ Неверный формат даты!\n\n'
            '📅 Используйте формат: ДД.ММ.ГГГГ ЧЧ:ММ\n'
            'Пример: 25.12.2024 19:00'
        )
    print(concert_date)
    is_valid, error_message = await database.is_valid_concert_date(concert_date)
    if not is_valid:
        return await message.answer(
            f'{error_message}\n\n'
            f'📅 Введите корректную дату в формате ДД.ММ.ГГГГ ЧЧ:ММ:'
        )

    await state.update_data(date=concert_date)
    keyboard = await rep_key.get_back_to_edit_creation_keyboard()
    await message.answer(
        '📍 Введите адрес проведения концерта:',
        reply_markup=keyboard
    )
    await state.set_state(CreateConcertStates.address)


@dp.message(CreateConcertStates.address, F.text == '⬅️ Назад')
async def back_from_date(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if 'address' in data:
        new_data = {k: v for k, v in data.items() if k != 'address'}
        await state.set_data(new_data)

    await state.set_state(CreateConcertStates.date)
    keyboard = await rep_key.get_back_to_edit_creation_keyboard()
    await message.answer(
        '📅 Введите дату концерта в формате ДД.ММ.ГГГГ ЧЧ:ММ:\n\n'
        'Пример: 25.12.2024 19:00',
        reply_markup=keyboard,
    )


@dp.message(CreateConcertStates.address)
async def process_address_creation(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.clear()
        keyboard = await rep_key.get_admin_keyboard()
        await message.answer('❌ Добавление концерта отменено.', reply_markup=keyboard)
        return

    await state.update_data(address=message.text)

    data = await state.get_data()
    original_photo_count = 0
    current_photos = data.get('photos', [])

    keyboard = await rep_key.get_photos_keyboard()
    await message.answer(
        f'🖼️ <b>Добавление фото концерта</b>\n\n'
        f'Текущее количество фото: <b>{original_photo_count}</b>\n'
        f'Добавлено новых фото: <b>{len(current_photos)}</b>\n'
        f'Осталось мест: <b>{10 - len(current_photos)}</b>\n\n'
        f'<b>Инструкция:</b>\n'
        f'1. Отправляйте фото по одному\n'
        f'2. Максимум 10 фото\n'
        f'3. Используйте кнопки ниже для управления\n\n'
        f'⚠️ После нажатия "Сохранить фото" фото будут добавлены к концерту.',
        reply_markup=keyboard,
        parse_mode='HTML'
    )
    await state.set_state(CreateConcertStates.photos)


@dp.message(CreateConcertStates.photos, F.text == '⬅️ Назад')
async def back_from_photos(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if 'photos' in data:
        new_data = {k: v for k, v in data.items() if k != 'photos'}
        new_data['photos'] = []
        await state.set_data(new_data)

    await state.set_state(CreateConcertStates.address)
    keyboard = await rep_key.get_back_to_edit_creation_keyboard()
    await message.answer(
        '📍 Введите адрес проведения концерта:',
        reply_markup=keyboard,
    )


@dp.message(CreateConcertStates.photos)
async def process_photos(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.clear()
        keyboard = await rep_key.get_admin_keyboard()
        await message.answer('❌ Добавление концерта отменено', reply_markup=keyboard)
        return
    elif message.text == '🗑️ Очистить список':
        data = await state.get_data()
        data['photos'] = []
        await state.set_data(data)

        keyboard = await rep_key.get_photos_keyboard()
        await message.answer(
            '🗑️ Список фото очищен!\n\n'
            f'🖼️ Добавлено новых фото: <b>0</b>\n'
            f'Осталось мест: <b>10</b>\n\n'
            'Продолжайте отправлять фото или нажмите "Сохранить фото" для завершения.',
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        return
    elif message.text == '💾 Сохранить фото':
        data = await state.get_data()

        required_fields = ['name', 'description', 'date', 'address']
        missing_fields = [
            field for field in required_fields if field not in data]

        if missing_fields:
            keyboard = await rep_key.get_admin_keyboard()
            await message.answer(
                f'''❌ Ошибка: отсутствуют обязательные поля: {", ".join(missing_fields)}\n'''
                f'''Пожалуйста, начните создание заново.''',
                reply_markup=keyboard,
            )
            await state.clear()
            return

        concert = await database.create_concert(
            name=data['name'],
            description=data['description'],
            date=data['date'],
            address=data['address'],
            photos=data['photos']
        )

        status = '🔴 Неактивен'
        address = concert.address

        text = f'🎵 Концерт создан! Управление:\n\n'
        text += f'📝 Название: {concert.name}\n'
        text += f'📄 Описание: {concert.description}\n'
        text += f'📅 Дата: {concert.date}\n'
        text += f'📍 Адрес: {address}\n'
        text += f'🖼️ Фото: {len(data.get("photos", []))} шт.\n'
        text += f'📊 Статус: {status}\n'

        admin_keyboard = await rep_key.get_admin_keyboard()
        await message.answer(
            '✅ Концерт успешно создан!\n'
            'Вы можете сделать рассылку после активации концерта или отредактировать его)',
            reply_markup=admin_keyboard
        )

        keyboard = await inl_key.get_concert_management_keyboard(False, concert.id)
        await message.answer(text, reply_markup=keyboard)

        await state.clear()
        return
    elif message.photo:
        data = await state.get_data()
        photos = data.get('photos', [])

        if len(photos) >= 10:
            await message.answer('❌ Достигнут лимит в 10 фото!')
            return

        photos.append(message.photo[-1].file_id)
        await state.update_data(photos=photos)

        keyboard = await rep_key.get_photos_keyboard()
        await message.answer(
            f'📸 Добавлено новых фото: <b>{len(photos)}</b>\n'
            f'Осталось мест: <b>{10 - len(photos)}</b>\n\n'
            f'Продолжайте отправлять фото или нажмите "Сохранить фото" для завершения.',
            reply_markup=keyboard,
            parse_mode='HTML',
        )


@dp.callback_query(F.data == 'check_subscription')
async def check_subscription(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    await callback.answer('🔍 Проверяю подписку...')

    await asyncio.sleep(2)

    is_subscribed = await helpers.check_channel_subscription(user_id)
    await database.update_user_subscription(user_id, is_subscribed)

    if is_subscribed:
        user = await database.get_or_create_user(
            telegram_id=user_id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name
        )

        has_voted = await database.has_user_voted(user_id)

        if not has_voted:
            keyboard = await inl_key.all_groups_keyboard()
            return await callback.message.edit_text(
                text.after_subscribed_1,
                reply_markup=keyboard
            )
        else:
            return await callback.message.edit_text(text.after_subscribed_1)
    else:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await callback.message.answer(text.not_subscribed_1, reply_markup=keyboard)


@dp.callback_query(F.data == 'no_each_one')
async def no_each_one(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        '🙏 Благодарим за ваш голос!\n💃 В конце вы сможете проголосовать за группу, которая вам понравилась! 🕺',
    )
    return


@dp.callback_query(F.data.startswith('group_'))
async def get_group_clicked(callback: types.CallbackQuery):
    group_id = int(callback.data.split('_')[1])
    user_id = callback.from_user.id

    user = await database.get_or_create_user(
        telegram_id=user_id,
        username=callback.from_user.username,
        full_name=callback.from_user.full_name
    )

    is_subscribed = await helpers.check_channel_subscription(callback.from_user.id)

    await database.update_user_subscription(callback.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await callback.message.answer(text.not_subscribed_1, reply_markup=keyboard)

    success, message = await database.vote_for_group(user.id, group_id)

    if success:
        await callback.message.delete()
        await callback.message.answer(
            '🙏 Благодарим за ваш голос!\n💃 Ожидайте розыгрыша! 🕺',
        )
    else:
        await callback.answer(message, show_alert=True)


@dp.message(F.text == '💰 Розыгрыш среди групп')
async def show_voting_results(message: types.Message):
    user = await database.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )

    is_subscribed = await helpers.check_channel_subscription(user.telegram_id)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        await message.answer(
            text.not_subscribed_by_ticket,
            reply_markup=keyboard,
        )
        return

    if user.role not in ('admin', 'leading'):
        return await message.answer('❌ У вас нет доступа к этой команде')

    groups = await database.get_all_groups()

    if not groups:
        await message.answer('Голосование еще не началось.')
        return

    text = '📊 <b>Результаты голосования:</b>\n\n'

    winners = []
    max_votes = -1

    # Собираем данные о голосах и находим максимальное количество
    groups_data = []
    for i, group in enumerate(groups, start=1):
        votes = int(group.points) if group.points else 0
        groups_data.append({
            'name': group.name,
            'votes': votes,
            'index': i
        })

        text += f'{i}. {group.name}: {votes} голосов\n'

        # Находим группы с максимальным количеством голосов
        if votes > max_votes:
            max_votes = votes
            winners = [group.name]
        elif votes == max_votes and votes > 0:
            winners.append(group.name)

    # Формируем текст с результатами
    if winners and max_votes > 0:
        if len(winners) == 1:
            text += f'\n\n🏆 Победитель: Группа "{winners[0]}" -- {max_votes} голосов'
        else:
            winners_text = ', '.join([f'"{w}"' for w in winners])
            text += f'\n\n🏆 Победители (ничья): Группы {winners_text} -- по {max_votes} голосов'
    else:
        text += '\n\n🏆 Пока нет голосов'

    await message.answer(text, parse_mode='HTML')


@dp.message(F.text == '🎫 Получить билет')
async def get_ticket(message: types.Message):
    user = await database.get_or_create_user(message.from_user.id,
                                             message.from_user.username,
                                             message.from_user.full_name,)

    is_subscribed = await helpers.check_channel_subscription(user.telegram_id)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        await message.answer(
            text.not_subscribed_by_ticket,
            reply_markup=keyboard,
        )
        return

    concerts = await database.get_active_concerts(user.id)
    if not concerts:
        await message.answer(text.no_concerts)
        return

    keyboard = await inl_key.get_concerts_keyboard(concerts)
    await message.answer('🎸 Выберите концерт:', reply_markup=keyboard)


@dp.callback_query(F.data.startswith('concert_'))
async def select_concert(callback: types.CallbackQuery):
    concert_id = int(callback.data.split('_')[1])
    user = await database.get_or_create_user(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.full_name
    )

    is_subscribed = await helpers.check_channel_subscription(callback.from_user.id)

    await database.update_user_subscription(callback.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await callback.message.answer(text.not_subscribed_1, reply_markup=keyboard)
    ticket_data = await database.create_ticket(user.id, concert_id)

    await callback.message.edit_text(
        f'🎫 Ваш билет сгенерирован!\n\n'
        f'🎟️ Код: <code>{ticket_data["code"]}</code>\n'
        f'⚠️ Сохраните этот код! Он понадобится при входе на концерт.\n\n'
        f'🎭 Покажите этот код организатору при входе.',
        parse_mode='HTML'
    )


@dp.message(F.text == '📋 Мои билеты')
async def my_tickets(message: types.Message):
    user = await database.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
    )
    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await message.answer(text.not_subscribed_1, reply_markup=keyboard)
    tickets = await database.get_user_tickets(user.id)

    if not tickets:
        await message.answer('🎫 У вас пока нет билетов.')
        return

    keyboard = await inl_key.get_available_concerts_keyboard(tickets)
    await message.answer('🎫 Выберите билет:', reply_markup=keyboard)


@dp.callback_query(F.data.startswith('ticket_concert_'))
async def select_ticket_concert(callback: types.CallbackQuery):
    concert_id = int(callback.data.split('_')[2])
    user = await database.get_or_create_user(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.full_name,
    )
    is_subscribed = await helpers.check_channel_subscription(callback.from_user.id)

    await database.update_user_subscription(callback.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await callback.message.answer(text.not_subscribed_1, reply_markup=keyboard)

    ticket = await database.get_user_ticket(user.id, concert_id)
    status = '✅ Использован' if ticket['is_used'] else '🟢 Активен'
    used_time = ''

    if ticket.get('used_at'):
        used_time = f'\n🕒 Использован: {ticket["used_at"].strftime("%d.%m.%Y %H:%M")}'

    txt = (
        f'🎵 Концерт: {ticket["concert_name"]}\n'
        f'📅 Дата: {ticket["concert_date"].strftime("%d.%m.%Y %H:%M")}\n'
        f'🎟️ Код: <code>{ticket["code"]}</code>\n'
        f'📊 Статус билета: {status}{used_time}\n'
    )

    if ticket.get('concert_photos'):
        await callback.message.delete()
        media = []
        for i, photo_id in enumerate(ticket.get('concert_photos')):
            if i == 0:
                media.append(types.InputMediaPhoto(
                    media=photo_id, caption=txt, parse_mode='HTML'))
            else:
                media.append(types.InputMediaPhoto(media=photo_id))
        return await callback.bot.send_media_group(chat_id=user.telegram_id, media=media,)

    await callback.message.edit_text(txt, parse_mode='HTML')


@dp.message(Command('admin'))
async def admin(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return await message.answer('❌ У вас нет доступа к этой команде.')

    keyboard = await rep_key.get_admin_keyboard()
    await message.answer('👨‍💻 Панель администратора', reply_markup=keyboard)


@dp.message(F.text == '📋 Управление концертами')
async def manage_concerts(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return await message.answer('❌ У вас нет доступа к этой команде.')

    concerts = await database.get_all_concerts()
    keyboard = await rep_key.get_admin_keyboard()
    if not concerts:
        return await message.answer('🎵 Нет созданных концертов.', reply_markup=keyboard)

    keyboard = await inl_key.get_admin_concerts_keyboard(concerts)
    await message.answer('🎵 Выберите концерт для управления:', reply_markup=keyboard)


@dp.callback_query(F.data.startswith('admin_concert_'))
async def select_concert_for_management(callback: types.CallbackQuery, state: FSMContext):
    concert_id = int(callback.data.split('_')[2])
    concert = await database.get_concert_by_id(concert_id)

    if not concert:
        await callback.answer('❌ Концерт не найден!', show_alert=True)
        return

    status = '🟢 Активен' if concert['is_active'] else '🔴 Неактивен'
    address = concert.get('address', 'Не указан')

    text = f'🎵 Управление концертом:\n\n'
    text += f'📝 Название: {concert["name"]}\n'
    text += f'📄 Описание: {concert["description"]}\n'
    text += f'📅 Дата: {concert["date"].strftime("%d.%m.%Y %H:%M")}\n'
    text += f'📍 Адрес: {address}\n'
    text += f'🖼️ Фото: {len(concert["photos"])} шт.\n'
    text += f'📊 Статус: {status}\n'

    keyboard = await inl_key.get_concert_management_keyboard(concert['is_active'], concert_id)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await state.update_data(concert_id=concert_id)


@dp.callback_query(F.data.startswith('deactivate_concert_'))
async def deactivate_concert(callback: types.CallbackQuery):
    concert_id = int(callback.data.split('_')[2])

    if not concert_id:
        await callback.answer('❌ Ошибка: концерт не выбран!', show_alert=True)
        return

    new_status = await database.toggle_concert_active(concert_id)
    status_text = 'активен' if new_status else 'неактивен'

    await callback.answer(f'✅ Концерт теперь {status_text}!', show_alert=True)

    concert = await database.get_concert_by_id(concert_id)
    status = '🟢 Активен' if concert['is_active'] else '🔴 Неактивен'
    address = concert.get('address', 'Не указан')

    text = f'🎵 Управление концертом:\n\n'
    text += f'📝 Название: {concert["name"]}\n'
    text += f'📄 Описание: {concert["description"]}\n'
    text += f'📅 Дата: {concert["date"].strftime("%d.%m.%Y %H:%M")}\n'
    text += f'📍 Адрес: {address}\n'
    text += f'🖼️ Фото: {len(concert["photos"])} шт.\n'
    text += f'📊 Статус: {status}\n'

    keyboard = await inl_key.get_concert_management_keyboard(concert['is_active'], concert_id)
    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query(F.data == 'list_concerts')
async def back_to_concerts_list(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    concerts = await database.get_all_concerts()
    keyboard = await inl_key.get_admin_concerts_keyboard(concerts)
    await callback.message.edit_text(
        '🎵 Выберите концерт для управления:',
        reply_markup=keyboard,
    )


@dp.callback_query(F.data.startswith('edit_concert_'))
async def edit_concert_menu(callback: types.CallbackQuery):
    concert_id = int(callback.data.split('_')[2])

    if not concert_id:
        await callback.answer('❌ Ошибка: концерт не выбран!', show_alert=True)
        return

    keyboard = await inl_key.get_edit_concert_keyboard(concert_id)
    await callback.message.edit_text(
        '✏️ Выберите что хотите отредактировать:',
        reply_markup=keyboard,
    )


@dp.callback_query(F.data.startswith('back_to_management_'))
async def back_to_management(callback: types.CallbackQuery, state: FSMContext):
    concert_id = int(callback.data.split('_')[3])

    if not concert_id:
        await callback.answer('❌ Ошибка: концерт не выбран!', show_alert=True)
        return

    await state.clear()

    concert = await database.get_concert_by_id(concert_id)
    if not concert:
        await callback.answer('❌ Концерт не найден!', show_alert=True)
        return

    status = '🟢 Активен' if concert['is_active'] else '🔴 Неактивен'
    address = concert.get('address', 'Не указан')

    text = f'🎵 Управление концертом:\n\n'
    text += f'📝 Название: {concert["name"]}\n'
    text += f'📄 Описание: {concert["description"]}\n'
    text += f'📅 Дата: {concert["date"].strftime("%d.%m.%Y %H:%M")}\n'
    text += f'📍 Адрес: {address}\n'
    text += f'🖼️ Фото: {len(concert["photos"])} шт.\n'
    text += f'📊 Статус: {status}\n'

    keyboard = await inl_key.get_concert_management_keyboard(status, concert_id)
    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query(F.data.startswith('edit_name_'))
async def edit_name_start(callback: types.CallbackQuery, state: FSMContext):
    concert_id = int(callback.data.split('_')[2])

    if not concert_id:
        await callback.answer('❌ Ошибка: концерт не выбран!', show_alert=True)
        return

    await state.update_data(concert_id=concert_id)
    await state.set_state(EditConcertStates.waiting_for_name)

    concert = await database.get_concert_by_id(concert_id)
    current_name = concert.get('name', 'Не указано')

    keyboard = await inl_key.get_back_to_edit_keyboard(concert_id)
    await callback.message.edit_text(
        f'📝 Введите новое название концерта:\n\n'
        f'Текущее название: <b>{current_name}</b>\n'
        f'Концерт ID: {concert_id}',
        parse_mode='HTML',
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith('back_to_edit_menu_'))
async def back_after_editing(callback: types.CallbackQuery, state: FSMContext):
    concert_id = int(callback.data.split('_')[4])

    if not concert_id:
        await callback.answer('❌ Ошибка: концерт не выбран!', show_alert=True)
        return

    await state.clear()
    await state.update_data(concert_id=concert_id)

    keyboard = await inl_key.get_edit_concert_keyboard(concert_id)
    await callback.message.edit_text(
        '✏️ Выберите что хотите отредактировать:',
        reply_markup=keyboard,
    )


@dp.callback_query(F.data.startswith('edit_description_'))
async def edit_description_start(callback: types.CallbackQuery, state: FSMContext):
    concert_id = int(callback.data.split('_')[2])

    if not concert_id:
        await callback.answer('❌ Ошибка: концерт не выбран!', show_alert=True)
        return

    await state.update_data(concert_id=concert_id)
    await state.set_state(EditConcertStates.waiting_for_description)

    concert = await database.get_concert_by_id(concert_id)
    current_description = concert.get('description', 'Не указано')
    if len(current_description) > 100:
        current_description = current_description[:100] + '...'

    keyboard = await inl_key.get_back_to_edit_keyboard(concert_id)
    await callback.message.edit_text(
        f'📄 Введите новое описание концерта:\n\n'
        f'Текущее описание: <i>{current_description}</i>\n'
        f'Концерт ID: {concert_id}',
        parse_mode='HTML',
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith('edit_date_'))
async def edit_date_start(callback: types.CallbackQuery, state: FSMContext):
    concert_id = int(callback.data.split('_')[2])

    if not concert_id:
        await callback.answer('❌ Ошибка: концерт не выбран!', show_alert=True)
        return

    await state.update_data(concert_id=concert_id)
    await state.set_state(EditConcertStates.waiting_for_date)

    concert = await database.get_concert_by_id(concert_id)
    current_date = concert.get('date')
    if current_date and hasattr(current_date, 'strftime'):
        current_date_str = current_date.strftime('%d.%m.%Y %H:%M')
    else:
        current_date_str = 'Не указана'

    keyboard = await inl_key.get_back_to_edit_keyboard(concert_id)
    await callback.message.edit_text(
        f'📅 Введите новую дату концерта в формате ДД.ММ.ГГГГ ЧЧ:ММ:\n\n'
        f'Пример: 25.12.2024 19:00\n'
        f'Текущая дата: <b>{current_date_str}</b>\n'
        f'Концерт ID: {concert_id}',
        parse_mode='HTML',
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith('edit_address_'))
async def edit_address_start(callback: types.CallbackQuery, state: FSMContext):
    concert_id = int(callback.data.split('_')[2])

    if not concert_id:
        await callback.answer('❌ Ошибка: концерт не выбран!', show_alert=True)
        return

    await state.update_data(concert_id=concert_id)
    await state.set_state(EditConcertStates.waiting_for_address)

    concert = await database.get_concert_by_id(concert_id)
    current_address = concert.get('address', 'Не указан')

    keyboard = await inl_key.get_back_to_edit_keyboard(concert_id)
    await callback.message.edit_text(
        f'📍 Введите новый адрес концерта:\n\n'
        f'Текущий адрес: <b>{current_address}</b>\n'
        f'Концерт ID: {concert_id}',
        parse_mode='HTML',
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith('edit_photos_'))
async def edit_photos_start(callback: types.CallbackQuery, state: FSMContext):
    concert_id = int(callback.data.split('_')[2])

    if not concert_id:
        await callback.answer('❌ Ошибка: концерт не выбран!', show_alert=True)
        return

    await state.update_data(concert_id=concert_id)
    await state.set_state(EditConcertStates.waiting_for_photos)

    concert = await database.get_concert_by_id(concert_id)
    photo_count = len(concert.get('photos', []))

    data = await state.get_data()
    if 'photos' not in data:
        await state.update_data(photos=[])

    keyboard = await inl_key.get_photos_edit_keyboard(concert_id)
    await callback.message.edit_text(
        f'🖼️ <b>Редактирование фото концерта</b>\n\n'
        f'Текущее количество фото: <b>{photo_count}</b>\n'
        f'Концерт ID: {concert_id}\n\n'
        f'<b>Инструкция:</b>\n'
        f'1. Отправляйте фото по одному\n'
        f'2. Максимум 10 фото\n'
        f'3. Используйте кнопки ниже для управления\n\n'
        f'⚠️ После нажатия "Сохранить" все старые фото будут заменены.',
        parse_mode='HTML',
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith('back_to_concert_card_'))
async def edit_photos_start(callback: types.CallbackQuery, state: FSMContext):
    concert_id = int(callback.data.split('_')[4])

    if not concert_id:
        await callback.answer('❌ Ошибка: концерт не выбран!', show_alert=True)
        return

    await state.clear()
    await state.update_data(concert_id=concert_id)

    concert = await database.get_concert_by_id(concert_id)
    if not concert:
        await callback.answer('❌ Концерт не найден!', show_alert=True)
        return

    status = '🟢 Активен' if concert['is_active'] else '🔴 Неактивен'
    address = concert.get('address', 'Не указан')

    text = f'🎵 Управление концертом:\n\n'
    text += f'📝 Название: {concert["name"]}\n'
    text += f'📄 Описание: {concert["description"]}\n'
    text += f'📅 Дата: {concert["date"].strftime("%d.%m.%Y %H:%M")}\n'
    text += f'📍 Адрес: {address}\n'
    text += f'🖼️ Фото: {len(concert["photos"])} шт.\n'
    text += f'📊 Статус: {status}\n'

    keyboard = await inl_key.get_concert_management_keyboard(status, concert_id)
    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query(F.data.startswith('save_photos_'))
async def save_photos(callback: types.CallbackQuery, state: FSMContext):
    concert_id = int(callback.data.split('_')[2])

    if not concert_id:
        await callback.answer('❌ Ошибка: концерт не выбран!', show_alert=True)
        return

    data = await state.get_data()
    photos = data.get('photos', [])

    if not photos:
        await callback.answer('❌ Нет фото для сохранения!', show_alert=True)
        return

    success = await database.update_concert_photos(concert_id, photos)

    if success:
        await state.clear()
        await state.update_data(concert_id=concert_id)

        await callback.answer(f'✅ Сохранено {len(photos)} фото!', show_alert=True)

        keyboard = await inl_key.get_edit_concert_keyboard(concert_id)
        await callback.message.edit_text(
            f'✅ Успешно сохранено {len(photos)} фото!\n\n'
            f'✏️ Выберите что хотите отредактировать:',
            reply_markup=keyboard,
        )
    else:
        await callback.answer('❌ Ошибка при сохранении фото!', show_alert=True)


@dp.callback_query(F.data.startswith('clear_photos_'))
async def clear_photos(callback: types.CallbackQuery, state: FSMContext):
    concert_id = int(callback.data.split('_')[2])

    if not concert_id:
        await callback.answer('❌ Ошибка: концерт не выбран!', show_alert=True)
        return

    await state.update_data(photos=[])

    await callback.answer('✅ Список фото очищен!', show_alert=True)

    concert = await database.get_concert_by_id(concert_id)
    photo_count = len(concert.get('photos', []))
    keyboard = await inl_key.get_photos_edit_keyboard(concert_id)
    await callback.message.edit_text(
        f'🖼️ <b>Редактирование фото концерта</b>\n\n'
        f'Текущее количество фото: <b>{photo_count}</b>\n'
        f'Концерт ID: {concert_id}\n'
        f'Добавлено новых фото: <b>0</b>\n\n'
        f'<b>Инструкция:</b>\n'
        f'1. Отправляйте фото по одному\n'
        f'2. Максимум 10 фото\n'
        f'3. Используйте кнопки ниже для управления\n\n'
        f'⚠️ После нажатия "Сохранить" все старые фото будут заменены.',
        parse_mode='HTML',
        reply_markup=keyboard
    )


@dp.message(EditConcertStates.waiting_for_name)
async def process_new_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    concert_id = data.get('concert_id')

    if not concert_id:
        await message.answer('❌ Ошибка: концерт не выбран!')
        await state.clear()
        return

    new_name = message.text.strip()
    if not new_name:
        await message.answer('❌ Название не может быть пустым.')
        return

    success = await database.update_concert_field(concert_id, 'name', new_name)

    if success:
        await message.answer(f'✅ Название концерта обновлено на: <b>{new_name}</b>', parse_mode='HTML')

        await state.clear()
        await state.update_data(concert_id=concert_id)

        keyboard = await inl_key.get_edit_concert_keyboard(concert_id)
        await message.answer(
            '✏️ Выберите что хотите отредактировать:',
            reply_markup=keyboard,
        )
    else:
        await message.answer('❌ Ошибка при обновлении названия.')
        await state.clear()


@dp.message(EditConcertStates.waiting_for_description)
async def process_new_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    concert_id = data.get('concert_id')

    if not concert_id:
        await message.answer('❌ Ошибка: концерт не выбран!')
        await state.clear()
        return

    new_description = message.text.strip()
    if not new_description:
        await message.answer('❌ Описание не может быть пустым.')
        return

    success = await database.update_concert_field(concert_id, 'description', new_description)

    if success:
        display_desc = new_description[:100] + \
            '...' if len(new_description) > 100 else new_description
        await message.answer(f'✅ Описание концерта обновлено: <i>{display_desc}</i>', parse_mode='HTML')

        await state.clear()
        await state.update_data(concert_id=concert_id)

        keyboard = await inl_key.get_edit_concert_keyboard(concert_id)
        await message.answer(
            '✏️ Выберите что хотите отредактировать:',
            reply_markup=keyboard,
        )
    else:
        await message.answer('❌ Ошибка при обновлении описания.')
        await state.clear()


@dp.message(EditConcertStates.waiting_for_date)
async def process_new_date(message: types.Message, state: FSMContext):
    data = await state.get_data()
    concert_id = data.get('concert_id')

    if not concert_id:
        await message.answer('❌ Ошибка: концерт не выбран!')
        await state.clear()
        return

    date_str = message.text.strip()

    date_format = '%d.%m.%Y %H:%M'
    new_date = None

    try:
        new_date = datetime.datetime.strptime(date_str, date_format)
    except ValueError:
        new_date = None

    if not new_date:
        await message.answer(
            '❌ Неверный формат даты. Используйте: ДД.ММ.ГГГГ ЧЧ:ММ\n'
            'Пример: 25.12.2024 19:00'
        )
        return

    success = await database.update_concert_field(concert_id, 'date', new_date)

    if success:
        formatted_date = new_date.strftime('%d.%m.%Y %H:%M')
        await message.answer(f'✅ Дата концерта обновлена на: <b>{formatted_date}</b>', parse_mode='HTML')

        await state.clear()
        await state.update_data(concert_id=concert_id)

        keyboard = await inl_key.get_edit_concert_keyboard(concert_id)
        await message.answer(
            '✏️ Выберите что хотите отредактировать:',
            reply_markup=keyboard,
        )
    else:
        await message.answer('❌ Ошибка при обновлении даты.')
        await state.clear()


@dp.message(EditConcertStates.waiting_for_address)
async def process_new_address(message: types.Message, state: FSMContext):
    data = await state.get_data()
    concert_id = data.get('concert_id')

    if not concert_id:
        await message.answer('❌ Ошибка: концерт не выбран!')
        await state.clear()
        return

    new_address = message.text.strip()
    if not new_address:
        await message.answer('❌ Адрес не может быть пустым.')
        return

    success = await database.update_concert_field(concert_id, 'address', new_address)

    if success:
        await message.answer(f'✅ Адрес концерта обновлен на: <b>{new_address}</b>', parse_mode='HTML')

        await state.clear()
        await state.update_data(concert_id=concert_id)

        keyboard = await inl_key.get_edit_concert_keyboard(concert_id)
        await message.answer(
            '✏️ Выберите что хотите отредактировать:',
            reply_markup=keyboard,
        )
    else:
        await message.answer('❌ Ошибка при обновлении адреса.')
        await state.clear()


@dp.message(EditConcertStates.waiting_for_photos)
async def process_new_photos(message: types.Message, state: FSMContext):
    data = await state.get_data()
    concert_id = data.get('concert_id')

    if not concert_id:
        await message.answer('❌ Ошибка: концерт не выбран!')
        await state.clear()
        return

    if not message.photo:
        await message.answer('❌ Пожалуйста, отправьте фото!')
        return

    if message.media_group_id:
        await message.answer('⚠️ Пожалуйста, отправляйте фото по одному для лучшего контроля.')
        return

    current_photos = data.get('photos', [])

    if len(current_photos) >= 10:
        await message.answer('❌ Достигнут лимит в 10 фото!')
        return

    largest_photo = message.photo[-1]
    photo_id = largest_photo.file_id

    current_photos.append(photo_id)
    await state.update_data(photos=current_photos)

    concert = await database.get_concert_by_id(concert_id)
    original_photo_count = len(concert.get('photos', []))

    keyboard = await inl_key.get_photos_edit_keyboard(concert_id)
    await message.answer(
        f'✅ Фото добавлено!\n\n'
        f'Текущее количество фото: <b>{original_photo_count}</b>\n'
        f'Добавлено новых фото: <b>{len(current_photos)}</b>\n'
        f'Осталось мест: <b>{10 - len(current_photos)}</b>\n\n'
        f'Продолжайте отправлять фото или нажмите "Сохранить фото" для завершения.',
        parse_mode='HTML',
        reply_markup=keyboard
    )


@dp.message(F.text == 'ℹ️ О нас')
async def about_us(message: types.Message):
    await message.answer(
        '🎵 Система билетов университета\n\n'
        'Здесь вы можете получить билеты на наши концерты и мероприятия.\n\n'
        'Для получения билета необходимо быть подписанным на наш канал.'
    )


@dp.callback_query(F.data.startswith('broadcast_concert_'))
async def broadcast_concert(callback: types.CallbackQuery, state: FSMContext):
    concert_id = int(callback.data.split('_')[2])

    if not concert_id:
        await callback.answer('❌ Ошибка: концерт не выбран!', show_alert=True)
        return

    concert = await database.get_concert_by_id(concert_id)
    if not concert:
        await callback.answer('❌ Концерт не найден!', show_alert=True)
        return

    final_answer = await database.broadcast_existing_concert(concert, bot, concert['is_active'], callback)
    if final_answer is None:
        return

    await callback.answer('✅ Рассылка запущена!', show_alert=True)
    await asyncio.sleep(4)
    await callback.answer(final_answer, show_alert=True)


@dp.message(F.text == '🎰 Розыгрыш')
async def raffle_section(message: types.Message):
    keyboard = await rep_key.raffle_keyboard()
    await message.answer('🌟 Вы можете назначить ведущего или провести розыгрыш!', reply_markup=keyboard)


@dp.message(F.text == '🔙 Назад в меню')
async def back_from_raffle(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        keyboard = await rep_key.get_role_based_keyboard('user')
    else:
        keyboard = await rep_key.get_admin_keyboard()

    await message.answer('🔙 Возврат в главное меню', reply_markup=keyboard)


@dp.message(F.text == '🎤 Назначить ведущего')
async def appoint_leading_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer('❌ У вас нет доступа к этой команде.')
        return

    keyboard = await rep_key.cancel_keyboard()
    await message.answer(
        '🔍 Введите username, имя пользователя или id пользователя для поиска:\n\n'
        'Примеры:\n'
        '@username\n'
        'Иван Иванов\n'
        '123456789 (ID пользователя)',
        reply_markup=keyboard
    )
    await state.set_state(AppointLeadingStates.searching_user)


@dp.message(AppointLeadingStates.searching_user, F.text == '❌ Отмена')
async def cancel_searching_user(message: types.Message, state: FSMContext):
    await state.clear()
    user = await database.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
    )
    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await message.answer(text.not_subscribed_1, reply_markup=keyboard)
    keyboard = await rep_key.get_role_based_keyboard(user.role)
    await message.answer('❌ Поиск пользователя отменен.', reply_markup=keyboard)


@dp.message(AppointLeadingStates.searching_user)
async def search_user(message: types.Message, state: FSMContext):
    search_query = message.text.strip()

    if not search_query:
        await message.answer('❌ Пожалуйста, введите поисковый запрос.')
        return

    found_users = await database.search_users(search_query)

    if not found_users:
        await message.answer(
            f'❌ Пользователь не найден по запросу: "{search_query}"\n\n'
            f'Попробуйте:\n'
            f'• Полный username (с @)\n'
            f'• Имя и фамилию\n'
            f'• ID пользователя'
        )
        return

    if len(found_users) == 1:
        user = found_users[0]
        await state.update_data(
            selected_user_id=user['telegram_id'],
            selected_user_info=user
        )

        keyboard = await rep_key.confirm_cancel_keyboard()
        await message.answer(
            f'✅ Найден пользователь:\n\n'
            f'👤 Имя: {user.get("full_name", "Не указано")}\n'
            f'📱 Username: @{user.get("username", "Не указан")}\n'
            f'🆔 ID: {user["telegram_id"]}\n'
            f'🎭 Текущая роль: {user.get("role", "user")}\n\n'
            f'Назначить этого пользователя ведущим?',
            reply_markup=keyboard
        )
        await state.set_state(AppointLeadingStates.confirming_user)
    else:
        keyboard = await rep_key.users_list_keyboard(found_users)
        await message.answer(
            f'🔍 Найдено несколько пользователей ({len(found_users)}):\n\n'
            f'Выберите пользователя из списка:',
            reply_markup=keyboard
        )
        await state.update_data(found_users=found_users)
        await state.set_state(AppointLeadingStates.confirming_user)


@dp.callback_query(F.data.startswith('select_user_'))
async def select_user_from_list(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split('_')[2])

    data = await state.get_data()
    found_users = data.get('found_users', [])

    selected_user = None
    for user in found_users:
        if user['telegram_id'] == user_id:
            selected_user = user
            break

    if not selected_user:
        await callback.answer('❌ Пользователь не найден!')
        return

    await state.update_data(
        selected_user_id=selected_user['telegram_id'],
        selected_user_info=selected_user
    )

    keyboard = await rep_key.confirm_cancel_keyboard()
    await callback.message.edit_text(
        f'✅ Выбран пользователь:\n\n'
        f'👤 Имя: {selected_user.get("full_name", "Не указано")}\n'
        f'📱 Username: @{selected_user.get("username", "Не указан")}\n'
        f'🆔 ID: {selected_user["telegram_id"]}\n'
        f'🎭 Текущая роль: {selected_user.get("role", "user")}\n\n'
        f'Назначить этого пользователя ведущим?',
        reply_markup=keyboard
    )
    await callback.answer()


@dp.message(AppointLeadingStates.confirming_user, F.text == '✅ Да, назначить')
async def confirm_appointment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('selected_user_id')
    user_info = data.get('selected_user_info', {})

    keyboard = await rep_key.final_confirm_cancel_keyboard()
    await message.answer(
        f'⚠️ <b>Подтверждение назначения</b>\n\n'
        f'Вы собираетесь назначить ведущим:\n\n'
        f'👤 <b>Пользователь:</b> {user_info.get("full_name", "Не указано")}\n'
        f'📱 <b>Username:</b> @{user_info.get("username", "Не указан")}\n'
        f'🆔 <b>ID:</b> {user_id}\n\n'
        f'После назначения пользователь получит доступ к функциям розыгрыша.\n\n'
        f'<b>Подтвердить назначение?</b>',
        parse_mode='HTML',
        reply_markup=keyboard
    )
    await state.set_state(AppointLeadingStates.confirming_appointment)


@dp.message(AppointLeadingStates.confirming_user, F.text == '❌ Нет, выбрать другого')
async def select_another_user(message: types.Message, state: FSMContext):
    keyboard = await rep_key.cancel_keyboard()
    await message.answer(
        '🔍 Введите username, имя пользователя или id пользователя для поиска:\n\n'
        'Примеры:\n'
        '@username\n'
        'Иван Иванов\n'
        '123456789 (ID пользователя)',
        reply_markup=keyboard
    )
    await state.set_state(AppointLeadingStates.searching_user)


@dp.message(AppointLeadingStates.confirming_user, F.text == '❌ Отмена')
async def cancel_in_confirming_user(message: types.Message, state: FSMContext):
    await state.clear()
    user = await database.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
    )

    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await message.answer(text.not_subscribed_1, reply_markup=keyboard)
    keyboard = await rep_key.get_role_based_keyboard(user.role)
    await message.answer('❌ Назначение ведущего отменено.', reply_markup=keyboard)


@dp.message(AppointLeadingStates.confirming_appointment, F.text == '✅ Подтвердить назначение')
async def final_confirm_appointment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('selected_user_id')
    user_info = data.get('selected_user_info', {})

    success = await database.update_user_role(user_id, 'leading')

    if success:
        try:
            keyboard = await rep_key.get_leading_keyboard()
            await bot.send_message(
                chat_id=user_id,
                text='🎉 <b>Вас назначили ведущим!</b>\n\n'
                     'Теперь у вас есть доступ к функциям розыгрыша:\n'
                     '• Проведение розыгрышей среди групп\n'
                     '• Проведение розыгрышей среди зала\n\n'
                     'Используйте кнопки в меню для доступа к функциям.',
                parse_mode='HTML',
                reply_markup=keyboard,
            )
        except Exception as e:
            print(
                f'Не удалось отправить уведомление пользователю {user_id}: {e}')

        await state.clear()
        keyboard = await rep_key.raffle_keyboard()
        await message.answer(
            f'✅ <b>Пользователь назначен ведущим!</b>\n\n'
            f'👤 Имя: {user_info.get("full_name", "Не указано")}\n'
            f'📱 Username: @{user_info.get("username", "Не указан")}\n'
            f'🆔 ID: {user_id}\n\n'
            f'Пользователь получил уведомление о назначении.',
            parse_mode='HTML',
            reply_markup=keyboard
        )
    else:
        await message.answer(
            '❌ Не удалось назначить пользователя ведущим.\n'
            'Возможно, произошла ошибка в базе данных.'
        )
        await state.clear()


@dp.message(AppointLeadingStates.confirming_appointment, F.text == '❌ Отменить')
async def cancel_appointment(message: types.Message, state: FSMContext):
    await state.clear()
    keyboard = await rep_key.raffle_keyboard()
    await message.answer('❌ Назначение ведущего отменено.', reply_markup=keyboard)


@dp.message(F.text == '👥 Управление ролями')
async def manage_roles(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer('❌ У вас нет доступа к этой команде.')
        return

    keyboard = await rep_key.manage_roles_keyboard()
    await message.answer(
        '🛠️ <b>Управление ролями пользователей</b>\n\n'
        'Вы можете:\n'
        '• Назначить ведущего\n'
        '• Снять роль ведущего\n'
        '• Назначить проверяющего\n'
        '• Посмотреть список пользователей по ролям',
        parse_mode='HTML',
        reply_markup=keyboard
    )


@dp.message(F.text == '🔙 Назад')
async def back_from_manage_roles(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer('❌ У вас нет доступа к этой команде.')
        return

    keyboard = await rep_key.get_admin_keyboard()
    await message.answer('🔙 Возврат в главное меню администратора', reply_markup=keyboard)


@dp.message(F.text == '🎫 Назначить проверяющего')
async def appoint_checker_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer('❌ У вас нет доступа к этой команде.')
        return

    keyboard = await rep_key.cancel_keyboard()
    await message.answer(
        '🔍 Введите username, имя пользователя или id пользователя для поиска:\n\n'
        'Примеры:\n'
        '@username\n'
        'Иван Иванов\n'
        '123456789 (ID пользователя)',
        reply_markup=keyboard
    )
    await state.set_state(AppointCheckerStates.searching_user)


@dp.message(AppointCheckerStates.searching_user, F.text == '❌ Отмена')
async def cancel_checker_search(message: types.Message, state: FSMContext):
    await state.clear()
    user = await database.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
    )

    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await message.answer(text.not_subscribed_1, reply_markup=keyboard)
    keyboard = await rep_key.get_role_based_keyboard(user.role)
    await message.answer('❌ Поиск пользователя отменен.', reply_markup=keyboard)


@dp.message(AppointCheckerStates.searching_user)
async def search_user_checker(message: types.Message, state: FSMContext):
    search_query = message.text.strip()

    if not search_query:
        await message.answer('❌ Пожалуйста, введите поисковый запрос.')
        return

    found_users = await database.search_users(search_query)

    if not found_users:
        await message.answer(
            f'❌ Пользователь не найден по запросу: "{search_query}"\n\n'
            f'Попробуйте:\n'
            f'• Полный username (с @)\n'
            f'• Имя и фамилию\n'
            f'• ID пользователя'
        )
        return

    if len(found_users) == 1:
        user = found_users[0]
        await state.update_data(
            selected_user_id=user['telegram_id'],
            selected_user_info=user
        )

        keyboard = await rep_key.confirm_cancel_keyboard()
        await message.answer(
            f'✅ Найден пользователь:\n\n'
            f'👤 Имя: {user.get("full_name", "Не указано")}\n'
            f'📱 Username: @{user.get("username", "Не указан")}\n'
            f'🆔 ID: {user["telegram_id"]}\n'
            f'🎭 Текущая роль: {user.get("role", "user")}\n\n'
            f'Назначить этого пользователя проверяющим?',
            reply_markup=keyboard
        )
        await state.set_state(AppointCheckerStates.confirming_user)
    else:
        keyboard = await rep_key.users_list_keyboard(found_users)
        await message.answer(
            f'🔍 Найдено несколько пользователей ({len(found_users)}):\n\n'
            f'Выберите пользователя из списка:',
            reply_markup=keyboard
        )
        await state.update_data(found_users=found_users)
        await state.set_state(AppointCheckerStates.confirming_user)


@dp.message(AppointCheckerStates.confirming_user, F.text == '✅ Да, назначить')
async def confirm_checker_appointment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('selected_user_id')
    user_info = data.get('selected_user_info', {})

    keyboard = await rep_key.final_confirm_cancel_keyboard()
    await message.answer(
        f'⚠️ <b>Подтверждение назначения</b>\n\n'
        f'Вы собираетесь назначить проверяющим:\n\n'
        f'👤 <b>Пользователь:</b> {user_info.get("full_name", "Не указано")}\n'
        f'📱 <b>Username:</b> @{user_info.get("username", "Не указан")}\n'
        f'🆔 <b>ID:</b> {user_id}\n\n'
        f'После назначения пользователь получит доступ к функциям проверки билетов.\n\n'
        f'<b>Подтвердить назначение?</b>',
        parse_mode='HTML',
        reply_markup=keyboard
    )
    await state.set_state(AppointCheckerStates.confirming_appointment)


@dp.message(AppointCheckerStates.confirming_user, F.text == '❌ Нет, выбрать другого')
async def select_another_user_checker(message: types.Message, state: FSMContext):
    keyboard = await rep_key.cancel_keyboard()
    await message.answer(
        '🔍 Введите username, имя пользователя или id пользователя для поиска:\n\n'
        'Примеры:\n'
        '@username\n'
        'Иван Иванов\n'
        '123456789 (ID пользователя)',
        reply_markup=keyboard
    )
    await state.set_state(AppointCheckerStates.searching_user)


@dp.message(AppointCheckerStates.confirming_user, F.text == '❌ Отмена')
async def cancel_checker_in_confirming(message: types.Message, state: FSMContext):
    await state.clear()
    user = await database.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
    )

    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await message.answer(text.not_subscribed_1, reply_markup=keyboard)
    keyboard = await rep_key.get_role_based_keyboard(user.role)
    await message.answer('❌ Назначение проверяющего отменено.', reply_markup=keyboard)


@dp.message(AppointCheckerStates.confirming_appointment, F.text == '✅ Подтвердить назначение')
async def final_confirm_checker_appointment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('selected_user_id')
    user_info = data.get('selected_user_info', {})

    success = await database.update_user_role(user_id, 'checker')

    if success:
        try:
            await bot.send_message(
                chat_id=user_id,
                text='🎉 <b>Вас назначили проверяющим!</b>\n\n'
                     'Теперь у вас есть доступ к функциям проверки билетов:\n'
                     '• Проверка билетов на входе\n\n'
                     'Используйте кнопку "🎫 Проверить билет" в меню.',
                parse_mode='HTML'
            )
        except Exception as e:
            print(
                f'Не удалось отправить уведомление пользователю {user_id}: {e}')

        await state.clear()
        keyboard = await rep_key.manage_roles_keyboard()
        await message.answer(
            f'✅ <b>Пользователь назначен проверяющим!</b>\n\n'
            f'👤 Имя: {user_info.get("full_name", "Не указано")}\n'
            f'📱 Username: @{user_info.get("username", "Не указан")}\n'
            f'🆔 ID: {user_id}\n\n'
            f'Пользователь получил уведомление о назначении.',
            parse_mode='HTML',
            reply_markup=keyboard
        )
    else:
        await message.answer(
            '❌ Не удалось назначить пользователя проверяющим.\n'
            'Возможно, произошла ошибка в базе данных.'
        )
        await state.clear()


@dp.message(AppointCheckerStates.confirming_appointment, F.text == '❌ Отменить')
async def cancel_checker_appointment(message: types.Message, state: FSMContext):
    await state.clear()
    keyboard = await rep_key.manage_roles_keyboard()
    await message.answer('❌ Назначение проверяющего отменено.', reply_markup=keyboard)


@dp.message(F.text == '👤 Снять роль ведущего')
async def remove_leading_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer('❌ У вас нет доступа к этой команде.')
        return

    keyboard = await rep_key.cancel_keyboard()
    await message.answer(
        '🔍 Введите username, имя пользователя или id пользователя для поиска:\n\n'
        'Примеры:\n'
        '@username\n'
        'Иван Иванов\n'
        '123456789 (ID пользователя)',
        reply_markup=keyboard
    )
    await state.set_state(RemoveLeadingStates.searching_user)


@dp.message(RemoveLeadingStates.searching_user, F.text == '❌ Отмена')
async def cancel_remove_leading_search(message: types.Message, state: FSMContext):
    await state.clear()
    user = await database.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
    )

    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await message.answer(text.not_subscribed_1, reply_markup=keyboard)
    keyboard = await rep_key.get_role_based_keyboard(user.role)
    await message.answer('❌ Поиск пользователя отменен.', reply_markup=keyboard)


@dp.message(RemoveLeadingStates.searching_user)
async def search_user_remove_leading(message: types.Message, state: FSMContext):
    search_query = message.text.strip()

    if not search_query:
        await message.answer('❌ Пожалуйста, введите поисковый запрос.')
        return

    found_users = await database.search_users(search_query)

    if not found_users:
        await message.answer(
            f'❌ Пользователь не найден по запросу: "{search_query}"\n\n'
            f'Попробуйте:\n'
            f'• Полный username (с @)\n'
            f'• Имя и фамилию\n'
            f'• ID пользователя'
        )
        return

    leading_users = [u for u in found_users if u.get('role') == 'leading']

    if len(leading_users) == 1:
        user = leading_users[0]
        await state.update_data(
            selected_user_id=user['telegram_id'],
            selected_user_info=user
        )

        keyboard = await rep_key.confirm_cancel_keyboard()
        await message.answer(
            f'⚠️ <b>Снятие роли ведущего</b>\n\n'
            f'👤 Пользователь: {user.get("full_name", "Не указано")}\n'
            f'📱 Username: @{user.get("username", "Не указан")}\n'
            f'🆔 ID: {user["telegram_id"]}\n'
            f'🎭 Текущая роль: {user.get("role", "user")}\n\n'
            f'Снять роль ведущего у этого пользователя?',
            parse_mode='HTML',
            reply_markup=keyboard
        )
        await state.set_state(RemoveLeadingStates.confirming_user)
    else:
        if not leading_users:
            await message.answer('❌ Среди найденных пользователей нет ведущих.')
            return

        keyboard = await rep_key.users_list_keyboard(leading_users)
        await message.answer(
            f'🔍 Найдено несколько ведущих ({len(leading_users)}):\n\n'
            f'Выберите пользователя из списка:',
            reply_markup=keyboard
        )
        await state.update_data(found_users=leading_users)
        await state.set_state(RemoveLeadingStates.confirming_user)


@dp.message(RemoveLeadingStates.confirming_user, F.text == '✅ Да, назначить')
async def confirm_leading_removal(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('selected_user_id')
    user_info = data.get('selected_user_info', {})

    keyboard = await rep_key.final_confirm_cancel_keyboard()
    await message.answer(
        f'⚠️ <b>Подтверждение снятия роли</b>\n\n'
        f'Вы собираетесь снять роль ведущего у:\n\n'
        f'👤 <b>Пользователь:</b> {user_info.get("full_name", "Не указано")}\n'
        f'📱 <b>Username:</b> @{user_info.get("username", "Не указан")}\n'
        f'🆔 <b>ID:</b> {user_id}\n\n'
        f'После этого пользователь потеряет доступ к функциям розыгрыша.\n\n'
        f'<b>Подтвердить снятие роли?</b>',
        parse_mode='HTML',
        reply_markup=keyboard
    )
    await state.set_state(RemoveLeadingStates.confirming_removal)


@dp.message(RemoveLeadingStates.confirming_user, F.text == '❌ Нет, выбрать другого')
async def select_another_user_remove_leading(message: types.Message, state: FSMContext):
    keyboard = await rep_key.cancel_keyboard()
    await message.answer(
        '🔍 Введите username, имя пользователя или id пользователя для поиска:\n\n'
        'Примеры:\n'
        '@username\n'
        'Иван Иванов\n'
        '123456789 (ID пользователя)',
        reply_markup=keyboard
    )
    await state.set_state(RemoveLeadingStates.searching_user)


@dp.message(RemoveLeadingStates.confirming_user, F.text == '❌ Отмена')
async def cancel_remove_leading_in_confirming(message: types.Message, state: FSMContext):
    await state.clear()
    user = await database.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
    )

    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await message.answer(text.not_subscribed_1, reply_markup=keyboard)
    keyboard = await rep_key.get_role_based_keyboard(user.role)
    await message.answer('❌ Снятие роли ведущего отменено.', reply_markup=keyboard)


@dp.message(RemoveLeadingStates.confirming_removal, F.text == '✅ Подтвердить назначение')
async def final_confirm_leading_removal(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('selected_user_id')
    user_info = data.get('selected_user_info', {})

    success = await database.update_user_role(user_id, 'user')

    if success:
        import aiogram.types
        try:
            keyboard = aiogram.types.ReplyKeyboardRemove()
            await bot.send_message(
                chat_id=user_id,
                text='ℹ️ <b>С вас снята роль ведущего</b>\n\n'
                     'Вы больше не имеете доступа к функциям розыгрыша.',
                parse_mode='HTML',
                reply_markup=keyboard
            )
        except Exception as e:
            print(
                f'Не удалось отправить уведомление пользователю {user_id}: {e}')

        await state.clear()
        keyboard = await rep_key.manage_roles_keyboard()
        await message.answer(
            f'✅ <b>Роль ведущего снята!</b>\n\n'
            f'👤 Имя: {user_info.get("full_name", "Не указано")}\n'
            f'📱 Username: @{user_info.get("username", "Не указан")}\n'
            f'🆔 ID: {user_id}\n\n'
            f'Пользователь получил уведомление.',
            parse_mode='HTML',
            reply_markup=keyboard
        )
    else:
        await message.answer(
            '❌ Не удалось снять роль ведущего.\n'
            'Возможно, произошла ошибка в базе данных.'
        )
        await state.clear()


@dp.message(F.text == '🛑 Снять роль проверяющего')
async def remove_checker_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer('❌ У вас нет доступа к этой команде.')
        return

    keyboard = await rep_key.cancel_keyboard()
    await message.answer(
        '🔍 Введите username, имя пользователя или id пользователя для поиска:\n\n'
        'Примеры:\n'
        '@username\n'
        'Иван Иванов\n'
        '123456789 (ID пользователя)',
        reply_markup=keyboard
    )
    await state.set_state(RemoveCheckerStates.searching_user)


@dp.message(RemoveCheckerStates.searching_user, F.text == '❌ Отмена')
async def cancel_remove_checker_search(message: types.Message, state: FSMContext):
    await state.clear()
    user = await database.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
    )

    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await message.answer(text.not_subscribed_1, reply_markup=keyboard)
    keyboard = await rep_key.get_role_based_keyboard(user.role)
    await message.answer('❌ Поиск пользователя отменен.', reply_markup=keyboard)


@dp.message(RemoveCheckerStates.searching_user)
async def search_user_remove_checker(message: types.Message, state: FSMContext):
    search_query = message.text.strip()

    if not search_query:
        await message.answer('❌ Пожалуйста, введите поисковый запрос.')
        return

    found_users = await database.search_users(search_query)

    if not found_users:
        await message.answer(
            f'❌ Пользователь не найден по запросу: "{search_query}"\n\n'
            f'Попробуйте:\n'
            f'• Полный username (с @)\n'
            f'• Имя и фамилию\n'
            f'• ID пользователя'
        )
        return

    checker_users = [u for u in found_users if u.get('role') == 'checker']

    if len(checker_users) == 1:
        user = checker_users[0]
        await state.update_data(
            selected_user_id=user['telegram_id'],
            selected_user_info=user
        )

        keyboard = await rep_key.confirm_cancel_keyboard()
        await message.answer(
            f'⚠️ <b>Снятие роли проверяющего</b>\n\n'
            f'👤 Пользователь: {user.get("full_name", "Не указано")}\n'
            f'📱 Username: @{user.get("username", "Не указан")}\n'
            f'🆔 ID: {user["telegram_id"]}\n'
            f'🎭 Текущая роль: {user.get("role", "user")}\n\n'
            f'Снять роль проверяющего у этого пользователя?',
            parse_mode='HTML',
            reply_markup=keyboard
        )
        await state.set_state(RemoveCheckerStates.confirming_user)
    else:
        if not checker_users:
            await message.answer('❌ Среди найденных пользователей нет проверяющих.')
            return

        keyboard = await rep_key.users_list_keyboard(checker_users)
        await message.answer(
            f'🔍 Найдено несколько проверяющих ({len(checker_users)}):\n\n'
            f'Выберите пользователя из списка:',
            reply_markup=keyboard
        )
        await state.update_data(found_users=checker_users)
        await state.set_state(RemoveCheckerStates.confirming_user)


@dp.message(RemoveCheckerStates.confirming_user, F.text == '✅ Да, назначить')
async def confirm_checker_removal(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('selected_user_id')
    user_info = data.get('selected_user_info', {})

    keyboard = await rep_key.final_confirm_cancel_keyboard()
    await message.answer(
        f'⚠️ <b>Подтверждение снятия роли</b>\n\n'
        f'Вы собираетесь снять роль проверяющего у:\n\n'
        f'👤 <b>Пользователь:</b> {user_info.get("full_name", "Не указано")}\n'
        f'📱 <b>Username:</b> @{user_info.get("username", "Не указан")}\n'
        f'🆔 <b>ID:</b> {user_id}\n\n'
        f'После этого пользователь потеряет доступ к функциям проверки билетов.\n\n'
        f'<b>Подтвердить снятие роли?</b>',
        parse_mode='HTML',
        reply_markup=keyboard
    )
    await state.set_state(RemoveCheckerStates.confirming_removal)


@dp.message(RemoveCheckerStates.confirming_user, F.text == '❌ Нет, выбрать другого')
async def select_another_user_remove_checker(message: types.Message, state: FSMContext):
    keyboard = await rep_key.cancel_keyboard()
    await message.answer(
        '🔍 Введите username, имя пользователя или id пользователя для поиска:\n\n'
        'Примеры:\n'
        '@username\n'
        'Иван Иванов\n'
        '123456789 (ID пользователя)',
        reply_markup=keyboard
    )
    await state.set_state(RemoveCheckerStates.searching_user)


@dp.message(RemoveCheckerStates.confirming_user, F.text == '❌ Отмена')
async def cancel_remove_checker_in_confirming(message: types.Message, state: FSMContext):
    await state.clear()
    user = await database.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
    )

    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await message.answer(text.not_subscribed_1, reply_markup=keyboard)
    keyboard = await rep_key.get_role_based_keyboard(user.role)
    await message.answer('❌ Снятие роли проверяющего отменено.', reply_markup=keyboard)


@dp.message(RemoveCheckerStates.confirming_removal, F.text == '✅ Подтвердить назначение')
async def final_confirm_checker_removal(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('selected_user_id')
    user_info = data.get('selected_user_info', {})

    success = await database.update_user_role(user_id, 'user')

    if success:
        try:
            await bot.send_message(
                chat_id=user_id,
                text='ℹ️ <b>С вас снята роль проверяющего</b>\n\n'
                     'Вы больше не имеете доступа к функциям проверки билетов.',
                parse_mode='HTML'
            )
        except Exception as e:
            print(
                f'Не удалось отправить уведомление пользователю {user_id}: {e}')

        await state.clear()
        keyboard = await rep_key.manage_roles_keyboard()
        await message.answer(
            f'✅ <b>Роль проверяющего снята!</b>\n\n'
            f'👤 Имя: {user_info.get("full_name", "Не указано")}\n'
            f'📱 Username: @{user_info.get("username", "Не указан")}\n'
            f'🆔 ID: {user_id}\n\n'
            f'Пользователь получил уведомление.',
            parse_mode='HTML',
            reply_markup=keyboard
        )
    else:
        await message.answer(
            '❌ Не удалось снять роль проверяющего.\n'
            'Возможно, произошла ошибка в базе данных.'
        )
        await state.clear()


@dp.message(F.text == '📋 Список по ролям')
async def show_users_by_role(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer('❌ У вас нет доступа к этой команде.')
        return

    keyboard = await rep_key.role_list_keyboard()
    await message.answer(
        '👥 <b>Выберите роль для просмотра пользователей:</b>',
        parse_mode='HTML',
        reply_markup=keyboard
    )


@dp.message(F.text == '👑 Ведущие')
async def show_leading_users(message: types.Message):
    leading_users = await database.get_users_by_role('leading')

    if not leading_users:
        await message.answer('📭 Нет пользователей с ролью "ведущий".')
        return

    text = '👑 <b>Список ведущих:</b>\n\n'
    for i, user in enumerate(leading_users, 1):
        text += f'{i}. <b>{user["full_name"]}</b>\n'
        if user['username']:
            text += f'   @{user["username"]}\n'
        text += f'   🆔 ID: {user["telegram_id"]}\n'
        text += f'   📅 Создан: {user["created_at"].strftime("%d.%m.%Y")}\n\n'

    await message.answer(text, parse_mode='HTML')


@dp.message(F.text == '🎫 Проверяющие')
async def show_checker_users(message: types.Message):
    checker_users = await database.get_users_by_role('checker')

    if not checker_users:
        await message.answer('📭 Нет пользователей с ролью "проверяющий".')
        return

    text = '🎫 <b>Список проверяющих:</b>\n\n'
    for i, user in enumerate(checker_users, 1):
        text += f'{i}. <b>{user["full_name"]}</b>\n'
        if user['username']:
            text += f'   @{user["username"]}\n'
        text += f'   🆔 ID: {user["telegram_id"]}\n'
        text += f'   📅 Создан: {user["created_at"].strftime("%d.%m.%Y")}\n\n'

    await message.answer(text, parse_mode='HTML')


@dp.message(F.text == '👥 Обычные пользователи')
async def show_regular_users(message: types.Message):
    regular_users = await database.get_users_by_role('user')

    if not regular_users:
        await message.answer('📭 Нет пользователей с ролью "обычный пользователь".')
        return

    text = '👥 <b>Список обычных пользователей:</b>\n\n'
    for i, user in enumerate(regular_users[:20], 1):
        text += f'{i}. <b>{user["full_name"]}</b>\n'
        if user['username']:
            text += f'   @{user["username"]}\n'
        text += f'   🆔 ID: {user["telegram_id"]}\n'
        text += f'   📅 Создан: {user["created_at"].strftime("%d.%m.%Y")}\n\n'

    if len(regular_users) > 20:
        text += f'\n📊 И еще {len(regular_users) - 20} пользователей...'

    await message.answer(text, parse_mode='HTML')


@dp.message(F.text == '👨‍💻 Администраторы')
async def show_admin_users(message: types.Message):
    admin_users = await database.get_users_by_role('admin')

    if not admin_users:
        await message.answer('📭 Нет пользователей с ролью "администратор".')
        return

    text = '👨‍💻 <b>Список администраторов:</b>\n\n'
    for i, user in enumerate(admin_users, 1):
        text += f'{i}. <b>{user["full_name"]}</b>\n'
        if user['username']:
            text += f'   @{user["username"]}\n'
        text += f'   🆔 ID: {user["telegram_id"]}\n'
        text += f'   📅 Создан: {user["created_at"].strftime("%d.%m.%Y")}\n\n'

    await message.answer(text, parse_mode='HTML')


@dp.callback_query(F.data == 'cancel_selection')
async def cancel_user_selection(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text('❌ Выбор пользователя отменен.')
    await callback.answer()


@dp.message(F.text == '🎫 Проверить билет')
async def check_ticket_start(message: types.Message, state: FSMContext):
    user = await database.get_or_create_user(message.from_user.id,
                                             message.from_user.username,
                                             message.from_user.full_name,)

    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await message.answer(text.not_subscribed_1, reply_markup=keyboard)
    if user.role not in ['admin', 'checker']:
        await message.answer('❌ У вас нет доступа к этой функции.')
        return

    keyboard = await rep_key.check_ticket_keyboard()
    await message.answer(
        '🔍 <b>Проверка билетов</b>\n\n'
        'Выберите способ проверки:',
        parse_mode='HTML',
        reply_markup=keyboard
    )


@dp.message(F.text == '🎫 Проверить по коду')
async def check_ticket_by_code(message: types.Message, state: FSMContext):
    user = await database.get_or_create_user(message.from_user.id,
                                             message.from_user.username,
                                             message.from_user.full_name,)

    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await message.answer(text.not_subscribed_1, reply_markup=keyboard)

    if user.role not in ['admin', 'checker']:
        await message.answer('❌ У вас нет доступа к этой функции.')
        return

    keyboard = await rep_key.cancel_keyboard()
    await message.answer(
        '🔢 Введите код билета для проверки:\n\n'
        'Код состоит из 8 символов (буквы и цифры)',
        reply_markup=keyboard
    )
    await state.set_state(CheckTicketStates.waiting_for_ticket_code)


@dp.message(CheckTicketStates.waiting_for_ticket_code, F.text == '❌ Отмена')
async def cancel_ticket_check(message: types.Message, state: FSMContext):
    await state.clear()
    user = await database.get_or_create_user(message.from_user.id,
                                             message.from_user.username,
                                             message.from_user.full_name,)

    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await message.answer(text.not_subscribed_1, reply_markup=keyboard)
    keyboard = await rep_key.get_role_based_keyboard(user.role)
    await message.answer('❌ Проверка билета отменена.', reply_markup=keyboard)


@dp.message(CheckTicketStates.waiting_for_ticket_code)
async def process_ticket_code(message: types.Message, state: FSMContext):
    ticket_code = message.text.strip().upper()

    if len(ticket_code) != 8:
        await message.answer('❌ Код билета должен состоять из 8 символов.')
        return

    ticket_info = await database.get_ticket_by_code(ticket_code)

    if not ticket_info:
        await message.answer('❌ Билет с таким кодом не найден.')
        return

    status = '✅ Использован' if ticket_info['is_used'] else '🟢 Активен'
    used_time = ''

    if ticket_info.get('used_at'):
        used_time = f'\n🕒 Использован: {ticket_info["used_at"].strftime("%d.%m.%Y %H:%M")}'

    text = f'🎫 <b>Информация о билете</b>\n\n'
    text += f'🎵 Концерт: {ticket_info["concert_name"]}\n'
    text += f'📅 Дата: {ticket_info["concert_date"].strftime("%d.%m.%Y %H:%M")}\n'
    text += f'👤 Владелец: {ticket_info["user_name"]}\n'
    if ticket_info['user_username']:
        text += f'📱 Username: @{ticket_info["user_username"]}\n'
    text += f'🎟️ Код: <code>{ticket_info["code"]}</code>\n'
    text += f'📊 Статус: {status}{used_time}\n'

    if not ticket_info['is_used']:
        keyboard = await rep_key.confirm_use_ticket_keyboard(ticket_info['id'])
        await message.answer(text, parse_mode='HTML', reply_markup=keyboard)
    else:
        await message.answer(text, parse_mode='HTML')

    await state.clear()


@dp.callback_query(F.data.startswith('use_ticket_'))
async def use_ticket(callback: types.CallbackQuery):
    ticket_id = int(callback.data.split('_')[2])

    success = await database.mark_ticket_as_used(ticket_id)

    if success:
        await callback.answer('✅ Билет отмечен как использованный!', show_alert=True)
        await callback.message.edit_text(
            callback.message.text + '\n\n✅ Билет использован',
            parse_mode='HTML'
        )
    else:
        await callback.answer('❌ Ошибка при отметке билета', show_alert=True)


@dp.message(F.text == '📊 Статистика')
async def statistics_start(message: types.Message):
    user = await database.get_or_create_user(message.from_user.id,
                                             message.from_user.username,
                                             message.from_user.full_name,)

    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await message.answer(text.not_subscribed_1, reply_markup=keyboard)
    if user.role != 'admin':
        await message.answer('❌ У вас нет доступа к этой функции.')
        return

    keyboard = await rep_key.statistics_keyboard()
    await message.answer(
        '📈 <b>Статистика</b>\n\n'
        'Выберите тип статистики:',
        parse_mode='HTML',
        reply_markup=keyboard
    )


@dp.message(F.text == '📊 Статистика по концертам')
async def concerts_statistics(message: types.Message):
    user = await database.get_or_create_user(message.from_user.id,
                                             message.from_user.username,
                                             message.from_user.full_name,)

    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await message.answer(text.not_subscribed_1, reply_markup=keyboard)
    if user.role != 'admin':
        await message.answer('❌ У вас нет доступа к этой функции.')
        return

    stats = await database.get_concerts_statistics()

    text = '🎵 <b>Статистика по концертам</b>\n\n'
    text += f"📊 Всего концертов: {stats['total_concerts']}\n"
    text += f"🟢 Активных: {stats['active_concerts']}\n"
    text += f"🔴 Неактивных: {stats['inactive_concerts']}\n"
    text += f"🎫 Всего билетов продано: {stats['total_tickets']}\n"
    text += f"✅ Использовано билетов: {stats['used_tickets']}\n"
    text += f"🟢 Активных билетов: {stats['active_tickets']}\n\n"

    if stats['popular_concert']:
        text += f"🏆 <b>Самый популярный концерт:</b>\n"
        text += f"{stats['popular_concert']['name']}\n"
        text += f"🎫 Билетов продано: {stats['popular_concert']['tickets_count']}\n\n"

    text += '<b>Концерты по статусу:</b>\n'
    for concert in stats['concerts_by_status']:
        status = '🟢 Активен' if concert['is_active'] else '🔴 Неактивен'
        text += f'{status} {concert["name"]} - {concert["tickets_count"]} билетов\n'

    await message.answer(text, parse_mode='HTML')


@dp.message(F.text == '👥 Статистика по пользователям')
async def users_statistics(message: types.Message):
    user = await database.get_or_create_user(message.from_user.id,
                                             message.from_user.username,
                                             message.from_user.full_name,)

    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await message.answer(text.not_subscribed_1, reply_markup=keyboard)
    if user.role != 'admin':
        await message.answer('❌ У вас нет доступа к этой функции.')
        return

    stats = await database.get_users_statistics()

    text = '👥 <b>Статистика по пользователям</b>\n\n'
    text += f'📊 Всего пользователей: {stats["total_users"]}\n'
    text += f'👑 Ведущих: {stats["leading_count"]}\n'
    text += f'🎫 Проверяющих: {stats["checker_count"]}\n'
    text += f'👨‍💻 Администраторов: {stats["admin_count"]}\n'
    text += f'👥 Обычных пользователей: {stats["user_count"]}\n\n'

    text += '<b>Распределение по ролям:</b>\n'
    for role_stat in stats['roles_distribution']:
        role_name = {
            'user': '👥 Обычные',
            'leading': '👑 Ведущие',
            'checker': '🎫 Проверяющие',
            'admin': '👨‍💻 Администраторы'
        }.get(role_stat['role'], role_stat['role'])
        text += f'{role_name}: {role_stat["count"]} ({role_stat["percentage"]:.1f}%)\n'

    await message.answer(text, parse_mode='HTML')


@dp.message(F.text == '🎫 Статистика по билетам')
async def tickets_statistics(message: types.Message):
    user = await database.get_or_create_user(message.from_user.id,
                                             message.from_user.username,
                                             message.from_user.full_name,)

    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await message.answer(text.not_subscribed_1, reply_markup=keyboard)
    if user.role != 'admin':
        await message.answer('❌ У вас нет доступа к этой функции.')
        return

    stats = await database.get_tickets_statistics()

    text = '🎫 <b>Статистика по билетам</b>\n\n'
    text += f"📊 Всего билетов: {stats['total_tickets']}\n"
    text += f"✅ Использовано: {stats['used_tickets']} ({stats['used_percentage']:.1f}%)\n"
    text += f"🟢 Активных: {stats['active_tickets']} ({stats['active_percentage']:.1f}%)\n\n"

    text += '<b>Распределение по концертам:</b>\n'
    for concert_stat in stats['tickets_by_concert']:
        text += f"🎵 {concert_stat['concert_name']}\n"
        text += f"   🎫 Всего: {concert_stat['total_tickets']}\n"
        text += f"   ✅ Использовано: {concert_stat['used_tickets']}\n"
        text += f"   🟢 Активных: {concert_stat['active_tickets']}\n\n"

    await message.answer(text, parse_mode='HTML')


@dp.message(F.text == '🔙 Назад')
async def back_to_previous(message: types.Message):
    user = await database.get_or_create_user(message.from_user.id,
                                             message.from_user.username,
                                             message.from_user.full_name,)

    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await message.answer(text.not_subscribed_1, reply_markup=keyboard)
    keyboard = await rep_key.get_role_based_keyboard(user.role)
    await message.answer('🔙 Возврат в главное меню', reply_markup=keyboard)


@dp.message(F.text == '🎲 Розыгрыш среди зала')
async def choose_human_from_hall(message: types.Message):
    user = await database.get_or_create_user(message.from_user.id,
                                             message.from_user.username,
                                             message.from_user.full_name,)

    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await message.answer(text.not_subscribed_1, reply_markup=keyboard)
    if user.role not in ('admin', 'leading'):
        return await message.answer('❌ У вас нет доступа к этой функции.')

    all_users = await database.get_all_subscribed_users()
    for i in range(100):
        random.shuffle(all_users)
    try:
        winner = random.choice(all_users)
        await message.answer(f'Победитель: @{winner.username} ({winner.full_name} | {winner.telegram_id})')
        await bot.send_message(chat_id=winner.telegram_id,
                               text='Поздравляем, вы победили в розыгрыше! 🎉\n\n'
                               'Подойдите к ведущему, чтобы забрать приз 🏆',)
    except IndexError:
        await message.answer('❌ Нет пользователей для проведения розыгрыша(')


@dp.message()
async def handle_all(message: types.Message):
    user = await database.get_or_create_user(message.from_user.id,
                                             message.from_user.username,
                                             message.from_user.full_name,)

    is_subscribed = await helpers.check_channel_subscription(message.from_user.id)

    await database.update_user_subscription(message.from_user.id, is_subscribed)
    if not is_subscribed:
        keyboard = await inl_key.get_subscription_keyboard_with_link(config.CHANNEL_USERNAMES)
        return await message.answer(text.not_subscribed_1, reply_markup=keyboard)


async def main():
    print('🤖 Бот запущен...')
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
