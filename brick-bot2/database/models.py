import datetime
import sqlalchemy
import sqlalchemy.ext.declarative
import sqlalchemy.orm


Base = sqlalchemy.ext.declarative.declarative_base()


class Vote(Base):
    __tablename__ = 'votes'
    
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), nullable=False)
    group_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('groups.id'), nullable=False)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)
    
    # Уберите unique=True из user_id если хотите разрешить голосовать за разные группы
    # Если хотите только один голос на пользователя, оставьте это
    # __table_args__ = (sqlalchemy.UniqueConstraint('user_id', name='unique_user_vote'),)
    
    # Добавьте отношения
    user = sqlalchemy.orm.relationship("User", back_populates="votes")
    group = sqlalchemy.orm.relationship("Group", back_populates="votes")
    
    # Если хотите разрешить голосовать за разные группы, но не за одну и ту же дважды:
    __table_args__ = (sqlalchemy.UniqueConstraint('user_id', 'group_id', name='unique_user_group_vote'),)


class Group(Base):
    __tablename__ = 'groups'
    
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False)
    points = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    
    # Исправьте на правильное имя класса
    votes = sqlalchemy.orm.relationship("Vote", back_populates="group")


class User(Base):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    telegram_id = sqlalchemy.Column(sqlalchemy.Integer, unique=True, nullable=False)
    username = sqlalchemy.Column(sqlalchemy.String(100))
    full_name = sqlalchemy.Column(sqlalchemy.String(200))
    subscribed = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    role = sqlalchemy.Column(sqlalchemy.String, default='user')
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)

    # Исправьте на правильное имя класса
    votes = sqlalchemy.orm.relationship("Vote", back_populates="user")
    tickets = sqlalchemy.orm.relationship('Ticket', back_populates='user')


class Concert(Base):
    __tablename__ = 'concerts'
    
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String(200), nullable=False)
    description = sqlalchemy.Column(sqlalchemy.Text)
    date = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)
    address = sqlalchemy.Column(sqlalchemy.Text)
    is_active = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    photos = sqlalchemy.Column(sqlalchemy.Text)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)
    
    tickets = sqlalchemy.orm.relationship('Ticket', back_populates="concert")


class Ticket(Base):
    __tablename__ = 'tickets'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    concert_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('concerts.id'))
    code = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False)
    is_used = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    used_at = sqlalchemy.Column(sqlalchemy.DateTime)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)

    user = sqlalchemy.orm.relationship("User", back_populates="tickets")
    concert = sqlalchemy.orm.relationship("Concert", back_populates="tickets")