import datetime
import json
import string
import random

import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.exc
from aiogram.types import InputMediaPhoto

from config import config
from database.models import Base, User, Concert, Ticket, Group, Vote

RUSSIAN_MONTHS = {
    1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
    5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
    9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
}

RUSSIAN_WEEKDAYS = {
    0: 'понедельник', 1: 'вторник', 2: 'среда',
    3: 'четверг', 4: 'пятница', 5: 'суббота', 6: 'воскресенье'
}


class Database:
    def __init__(self):
        self.engine = sqlalchemy.create_engine(config.DATABASE_URL)
        self.Session = sqlalchemy.orm.sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        self._initialize_default_data()
    
    def _initialize_default_data(self):
        self._ensure_groups_exist()
    
    def _ensure_groups_exist(self):
        session = self.Session()
        
        groups_list = [
            'Смысловая нагрузка', 'Реинкарнация', 'Послезавтра',
            'Only minus one', 'ЭлектропроспектЪ!', 'АСТРАV',
            'Китовые песни', 'Завтрак чемпиона', 'Степень свободы',
            'Признаки чувств', 'Строй Аккорд', 'Spring Fever'
        ]
        
        try:
            for group_name in groups_list:
                group = session.query(Group).filter_by(name=group_name).first()
                if not group:
                    group = Group(name=group_name, points=0)
                    session.add(group)
            
            session.commit()
        except Exception as e:
            print(f'Ошибка при создании групп: {e}')
            session.rollback()
        finally:
            session.close()

    def _get_session(self):
        return self.Session()
    
    def generate_ticket_code(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    
    async def get_all_groups(self):
        session = self._get_session()
        return session.query(Group).all()
    
    async def vote_for_group(self, user_id: int, group_id: int) -> tuple[bool, str]:
        session = self._get_session()
        
        try:
            existing_vote = session.query(Vote).filter_by(
                user_id=user_id, 
                group_id=group_id
            ).first()
            
            if existing_vote:
                session.close()
                return False, '❌ Вы уже голосовали за группу!'
            
            group = session.query(Group).filter_by(id=group_id).first()
            if not group:
                session.close()
                return False, '❌ Группа не найдена!'
            
            vote = Vote(user_id=user_id, group_id=group_id)
            session.add(vote)
            
            group.points += 1
            
            session.commit()
            session.close()
            
            return True, '✅ Ваш голос учтен!'
            
        except sqlalchemy.exc.IntegrityError:
            session.rollback()
            session.close()
            return False, '❌ Вы уже голосовали за эту группу!'
        except Exception as e:
            session.rollback()
            session.close()
            print(f'Ошибка при голосовании: {e}')
            return False, '❌ Произошла ошибка при голосовании!'

    async def get_user_votes(self, user_id: int):
        session = self._get_session()
        votes = session.query(Vote).filter_by(user_id=user_id).all()
        
        result = [vote.group_id for vote in votes]
        session.close()
        return result

    async def has_user_voted(self, user_id, group_id=None):
        session = self._get_session()
        if group_id is not None:
            vote = session.query(Vote).filter_by(user_id=user_id, group_id=group_id).first()
        else:
            vote = session.query(Vote).filter_by(user_id=user_id).first()
        session.close()
        return vote is not None
    
    async def show_voting_keyboard(self, bot, telegram_id):
        import keyboards.inline_keyboards as inl_key
        keyboard = await inl_key.all_groups_keyboard()
        await bot.send_message(chat_id=telegram_id, text='👋 Еще раз здравствуйте! Проголусйте пожалуйста за группу, от которой вы пришли)', reply_markup=keyboard)

    async def get_or_create_user(self, telegram_id, username, full_name):
        session = self.Session()
        try:
            user = session.query(User).filter(User.telegram_id==telegram_id).first()
            
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    full_name=full_name,
                )
                
                if telegram_id in config.ADMIN_IDS:
                    user.role = 'admin'
                
                session.add(user)
                session.commit()
                
            else:
                if telegram_id in config.ADMIN_IDS and user.role != 'admin':
                    user.role = 'admin'
                    session.commit()
            
            session.refresh(user)
            return user
            
        except Exception as e:
            print(f"Ошибка в get_or_create_user: {e}")
            session.rollback()
            raise
        finally:
            session.close()  # Всегда закрываем сессию
    
    async def update_user_subscription(self, telegram_id, subscribed):
        session = self._get_session()
        user = session.query(User).filter(User.telegram_id == telegram_id)
        if user:
            user = user.first()
            user.subscribed = subscribed
            session.commit()
        session.close()
        return
    
    async def get_active_concerts(self, user_id=None):
        session = self._get_session()
        current_time = datetime.datetime.now()
        one_day_ago = current_time - datetime.timedelta(days=1)

        concerts = session.query(Concert).filter(
            Concert.is_active == True,
            Concert.date > one_day_ago,
        ).all()

        result = []
        for concert in concerts:
            if user_id:
                existing_ticket = session.query(Ticket).filter(
                    Ticket.user_id == user_id,
                    Ticket.concert_id == concert.id
                ).first()
                
                if existing_ticket:
                    continue

            photos = json.loads(concert.photos) if concert.photos else []
            result.append({
                'id': concert.id,
                'name': concert.name,
                'description': concert.description,
                'date': concert.date,
                'address': concert.address,
                'photos': photos,
                'is_active': concert.is_active,
            })
        session.close()
        return result

    async def create_ticket(self, user_id, concert_id):
        session = self._get_session()
        existing_ticket = session.query(Ticket).filter_by(user_id=user_id, concert_id=concert_id).first()
        if existing_ticket:
            return {
                    'id': existing_ticket.id,
                    'code': existing_ticket.code,
                    'is_used': existing_ticket.is_used
                }
        
        ticket = Ticket(
            user_id=user_id,
            concert_id=concert_id,
            code=self.generate_ticket_code(),
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        session.close()

        return {
                'id': ticket.id,
                'code': ticket.code,
                'is_used': ticket.is_used
            }
    
    async def get_user_tickets(self, user_id):
        session = self._get_session()
        tickets = session.query(Ticket).options(
            sqlalchemy.orm.joinedload(Ticket.concert),
        ).filter_by(user_id=user_id)
        if tickets:
            tickets = tickets.all()
        else:
            return
        
        result = []
        for ticket in tickets:
            result.append({
                'concert_name': ticket.concert.name,
                'concert_date': ticket.concert.date,
                'concert_id': ticket.concert.id,
            })
        
        session.close()
        return result
    
    async def get_user_ticket(self, user_id, concert_id):
        session = self._get_session()
        ticket = session.query(Ticket).options(
            sqlalchemy.orm.joinedload(Ticket.concert),
        ).filter_by(user_id=user_id, concert_id=concert_id)
        if ticket:
            ticket = ticket.first()
        else:
            return
        
        photos = json.loads(ticket.concert.photos) if ticket.concert.photos else []
        result = {
            'concert_name': ticket.concert.name,
            'concert_date': ticket.concert.date,
            'concert_photos': photos,
            'code': ticket.code,
            'is_used': ticket.is_used,
            'used_at': ticket.used_at
        }
        
        session.close()
        return result
    
    async def get_all_concerts(self):
        session = self._get_session()
        concerts = session.query(Concert).order_by(Concert.date.desc()).all()
        result = []
        for concert in concerts:
            photos = json.loads(concert.photos) if concert.photos else []
            result.append({
                'id': concert.id,
                'name': concert.name,
                'description': concert.description,
                'date': concert.date,
                'address': concert.address,
                'photos': photos,
                'is_active': concert.is_active
            })
        session.close()
        return result
    
    async def get_concert_by_id(self, concert_id):
        session = self._get_session()
        concert = session.query(Concert).filter_by(id=concert_id).first()
        if concert:
            photos = json.loads(concert.photos) if concert.photos else []
            session.close()
            return {
                'id': concert.id,
                'name': concert.name,
                'description': concert.description,
                'date': concert.date,
                'address': concert.address,
                'photos': photos,
                'is_active': concert.is_active
            }
        session.close()
        return None
    
    async def toggle_concert_active(self, concert_id):
        session = self._get_session()
        concert = session.query(Concert).filter_by(id=concert_id).first()
        if concert:
            concert.is_active = not concert.is_active
            status = concert.is_active
            session.commit()
            session.close()
            return status
        session.close()
        return None
    
    async def update_concert_field(self, concert_id, field, new_value):
        session = self._get_session()
        concert = session.query(Concert).filter_by(id=concert_id).first()
        if not concert:
            return False
        
        match field:
            case 'name': concert.name = new_value
            case 'description': concert.description = new_value
            case 'date': concert.date = new_value
            case 'address': concert.address = new_value
        session.commit()
        session.close()
        return True
    
    async def update_concert_photos(self, concert_id, photo_ids):
        session = self._get_session()
        concert = session.query(Concert).filter_by(id=concert_id).first()
        if not concert:
            return False

        import json
        concert.photos = json.dumps(photo_ids)

        session.commit()
        return True
    
    async def is_valid_concert_date(self, date):
        now = datetime.datetime.now()

        if date < now:
            return False, '❌ Дата концерта не может быть в прошлом!'
        
        max_date = now + datetime.timedelta(days=730)
        if date > max_date:
            return False, '❌ Дата концерта слишком далеко в будущем (максимум 2 года)!'
        
        return True, '✅ Дата корректна'

    async def create_concert(self, name, description, date, address, photos):
        session = self._get_session()
        photos_json = json.dumps(photos) if photos else '[]'
        concert = Concert(
            name=name,
            description=description,
            date=date,
            address=address,
            photos=photos_json,
            is_active=False,
        )
        session.add(concert)
        session.commit()
        session.refresh(concert)
        return concert

    async def get_all_users(self):
        session = self._get_session()
        try:
            users = session.query(User).all()
            return users
        finally:
            session.close()

    async def get_all_subscribed_users(self):
        session = self._get_session()
        try:
            users = session.query(User).filter(User.subscribed == True, User.role.in_(['member', 'user'])).all()
            return users
        finally:
            session.close()

    async def format_date_russian(self, date_obj):
        day = date_obj.day
        month = RUSSIAN_MONTHS[date_obj.month]
        year = date_obj.year
        weekday = RUSSIAN_WEEKDAYS[date_obj.weekday()]
        
        return f'{day} {month} {year} года ({weekday})'

    async def broadcast_existing_concert(self, concert, bot, is_active, callback):
        if not is_active:
            await callback.answer('❌ Нельзя запустить рассылку, пока анонс не активен!', show_alert=True,)
            return None
        
        users = await self.get_all_users()
        
        concert_date = concert['date']
        formatted_date = await self.format_date_russian(concert_date)
        text =  f'''🎉 АНОНС КОНЦЕРТА!\n\n''' \
                f'''🎵 {concert['name']}\n''' \
                f'''📅 Дата: {formatted_date}\n''' \
                f'''🕐 Время: {concert['date'].strftime('%H:%M')}\n''' \
                f'''📍 Место: {concert.get('address', 'Не указан')}\n''' \
                f'''{concert['description']}\n\n''' \
                f''' Чтобы получить билет, нажмите '🎫 Получить билет' '''
        
        success_count = 0
        for user in users:
            if concert['photos']:
                media = []
                for i, photo_id in enumerate(concert['photos']):
                    if i == 0:
                        media.append(InputMediaPhoto(media=photo_id, caption=text))
                    else:
                        media.append(InputMediaPhoto(media=photo_id))
                
                await bot.send_media_group(chat_id=user.telegram_id, media=media)
            else:
                await bot.send_message(chat_id=user.telegram_id, text=text)

            success_count += 1
        
        return f'✅ Рассылка завершена. Успешно: {success_count}/{len(users)}'
    
    async def search_users(self, search_query):
        session = self._get_session()
        try:
            query = session.query(User)
            
            if search_query.isdigit():
                user_id = int(search_query)
                users = query.filter(User.telegram_id == user_id).all()
            else:
                if search_query.startswith('@'):
                    search_query = search_query[1:]
                
                users_by_username = query.filter(
                    User.username.ilike(f'%{search_query}%')
                ).all()
                
                users_by_name = query.filter(
                    User.full_name.ilike(f'%{search_query}%')
                ).all()
                
                users = list({u.id: u for u in users_by_username + users_by_name}.values())
            
            result = []
            for user in users:
                result.append({
                    'id': user.id,
                    'telegram_id': user.telegram_id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'role': user.role,
                    'subscribed': user.subscribed
                })
            
            return result
            
        except Exception as e:
            print(f'Ошибка при поиске пользователей: {e}')
            return []
        finally:
            session.close()

    async def update_user_role(self, telegram_id, new_role):
        session = self._get_session()
        try:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            
            if not user:
                print(f'Пользователь с ID {telegram_id} не найден')
                return False
            
            if telegram_id in config.ADMIN_IDS:
                print(f'Пользователь {telegram_id} является системным админом, роль не может быть изменена')
                user.role = 'admin'
                session.commit()
                session.refresh(user)
                return False
            
            valid_roles = ['user', 'member', 'leading', 'checker', 'admin']
            if new_role not in valid_roles:
                print(f'Некорректная роль: {new_role}')
                return False
            
            user.role = new_role
            session.commit()
            
            print(f'Роль пользователя {telegram_id} изменена на {new_role}')
            return True
            
        except Exception as e:
            print(f'Ошибка при обновлении роли: {e}')
            session.rollback()
            return False
        finally:
            session.close()

    async def get_users_by_role(self, role):
        session = self._get_session()
        try:
            users = session.query(User).filter(User.role == role).all()
            
            result = []
            for user in users:
                result.append({
                    'id': user.id,
                    'telegram_id': user.telegram_id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'role': user.role,
                    'subscribed': user.subscribed,
                    'created_at': user.created_at
                })
            
            return result
            
        except Exception as e:
            print(f'Ошибка при получении пользователей по роли: {e}')
            return []
        finally:
            session.close()

    async def get_ticket_by_code(self, code):
        session = self.Session()
        try:
            ticket = session.query(Ticket).options(
                sqlalchemy.orm.joinedload(Ticket.user),
                sqlalchemy.orm.joinedload(Ticket.concert)
            ).filter(Ticket.code == code).first()
            
            if not ticket:
                return None
            
            return {
                'id': ticket.id,
                'code': ticket.code,
                'is_used': ticket.is_used,
                'used_at': ticket.used_at,
                'user_name': ticket.user.full_name if ticket.user else 'Неизвестно',
                'user_username': ticket.user.username if ticket.user and ticket.user.username else None,
                'concert_name': ticket.concert.name,
                'concert_date': ticket.concert.date
            }
            
        except Exception as e:
            print(f'Ошибка при поиске билета: {e}')
            return None
        finally:
            session.close()


    async def mark_ticket_as_used(self, ticket_id):
            session = self.Session()
            try:
                ticket = session.query(Ticket).filter(Ticket.id == ticket_id).first()
                
                if not ticket:
                    return False
                
                if ticket.is_used:
                    return False
                
                ticket.is_used = True
                ticket.used_at = datetime.datetime.now()
                session.commit()
                
                return True
                
            except Exception as e:
                print(f'Ошибка при отметке билета: {e}')
                session.rollback()
                return False
            finally:
                session.close()


    async def get_concerts_statistics(self):
        session = self.Session()
        try:
            # Общая статистика по концертам
            total_concerts = session.query(Concert).count()
            active_concerts = session.query(Concert).filter(Concert.is_active == True).count()
            inactive_concerts = total_concerts - active_concerts
            
            # Статистика по билетам
            total_tickets = session.query(Ticket).count()
            used_tickets = session.query(Ticket).filter(Ticket.is_used == True).count()
            active_tickets = total_tickets - used_tickets
            
            # Самый популярный концерт
            popular_concert = session.query(
                Concert.name,
                Concert.id,
                sqlalchemy.func.count(Ticket.id).label('tickets_count')
            ).join(Ticket, Concert.id == Ticket.concert_id)\
            .group_by(Concert.id)\
            .order_by(sqlalchemy.desc('tickets_count'))\
            .first()
            
            # Концерты по статусу
            concerts_by_status = session.query(
                Concert.name,
                Concert.is_active,
                sqlalchemy.func.count(Ticket.id).label('tickets_count')
            ).outerjoin(Ticket, Concert.id == Ticket.concert_id)\
            .group_by(Concert.id)\
            .order_by(Concert.is_active.desc(), Concert.date.desc())\
            .all()
            
            popular_concert_info = None
            if popular_concert:
                popular_concert_info = {
                    'name': popular_concert[0],
                    'tickets_count': popular_concert[2]
                }
            
            concerts_info = []
            for concert in concerts_by_status:
                concerts_info.append({
                    'name': concert[0],
                    'is_active': concert[1],
                    'tickets_count': concert[2]
                })
            
            return {
                'total_concerts': total_concerts,
                'active_concerts': active_concerts,
                'inactive_concerts': inactive_concerts,
                'total_tickets': total_tickets,
                'used_tickets': used_tickets,
                'active_tickets': active_tickets,
                'popular_concert': popular_concert_info,
                'concerts_by_status': concerts_info
            }
            
        except Exception as e:
            print(f'Ошибка при получении статистики по концертам: {e}')
            return {}
        finally:
            session.close()


    async def get_users_statistics(self):
        session = self.Session()
        try:
            # Общая статистика по пользователям
            total_users = session.query(User).count()
            
            # Статистика по ролям
            leading_count = session.query(User).filter(User.role == 'leading').count()
            checker_count = session.query(User).filter(User.role == 'checker').count()
            admin_count = session.query(User).filter(User.role == 'admin').count()
            user_count = session.query(User).filter(User.role == 'user').count()
            
            # Распределение по ролям
            roles_distribution = []
            roles = ['user', 'leading', 'checker', 'admin']
            
            for role in roles:
                count = session.query(User).filter(User.role == role).count()
                percentage = (count / total_users * 100) if total_users > 0 else 0
                roles_distribution.append({
                    'role': role,
                    'count': count,
                    'percentage': percentage
                })
            
            return {
                'total_users': total_users,
                'leading_count': leading_count,
                'checker_count': checker_count,
                'admin_count': admin_count,
                'user_count': user_count,
                'roles_distribution': roles_distribution
            }
            
        except Exception as e:
            print(f'Ошибка при получении статистики по пользователям: {e}')
            return {}
        finally:
            session.close()


    async def get_tickets_statistics(self):
        session = self.Session()
        try:
            # Общая статистика по билетам
            total_tickets = session.query(Ticket).count()
            used_tickets = session.query(Ticket).filter(Ticket.is_used == True).count()
            active_tickets = total_tickets - used_tickets
            
            used_percentage = (used_tickets / total_tickets * 100) if total_tickets > 0 else 0
            active_percentage = (active_tickets / total_tickets * 100) if total_tickets > 0 else 0
            
            # Билеты по концертам
            tickets_by_concert = session.query(
                Concert.name,
                Concert.id,
                sqlalchemy.func.count(Ticket.id).label('total_tickets'),
                sqlalchemy.func.count(
                    sqlalchemy.case((Ticket.is_used == True, 1))
                ).label('used_tickets'),
                sqlalchemy.func.count(
                    sqlalchemy.case((Ticket.is_used == False, 1))
                ).label('active_tickets')
            ).outerjoin(Ticket, Concert.id == Ticket.concert_id)\
            .group_by(Concert.id)\
            .order_by(sqlalchemy.desc('total_tickets'))\
            .all()
            
            concerts_info = []
            for concert in tickets_by_concert:
                concerts_info.append({
                    'concert_name': concert[0],
                    'total_tickets': concert[2] or 0,
                    'used_tickets': concert[3] or 0,
                    'active_tickets': concert[4] or 0
                })
            
            return {
                'total_tickets': total_tickets,
                'used_tickets': used_tickets,
                'active_tickets': active_tickets,
                'used_percentage': used_percentage,
                'active_percentage': active_percentage,
                'tickets_by_concert': concerts_info
            }
            
        except Exception as e:
            print(f'Ошибка при получении статистики по билетам: {e}')
            return {}
        finally:
            session.close()


database = Database()