from typing import List, Optional

from sqlalchemy import Boolean, CheckConstraint, Column, Date, ForeignKeyConstraint, Integer, Numeric, PrimaryKeyConstraint, String, Table, Time
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
import decimal

class Base(DeclarativeBase):
    pass


class Instructors(Base):
    __tablename__ = 'instructors'
    __table_args__ = (
        CheckConstraint("phone::text ~ '^\\+?[0-9\\s\\-\\(\\)]{6,20}$'::text", name='instructors_phone_check'),
        PrimaryKeyConstraint('ssn', name='instructors_pkey')
    )

    ssn: Mapped[str] = mapped_column(String(20), primary_key=True)
    firstname: Mapped[str] = mapped_column(String(50))
    lastname: Mapped[str] = mapped_column(String(50))
    phone: Mapped[Optional[str]] = mapped_column(String(20))

    course: Mapped[List['Course']] = relationship('Course', back_populates='instructors')


class Membership(Base):
    __tablename__ = 'membership'
    __table_args__ = (
        PrimaryKeyConstraint('sign', name='membership_pkey'),
    )

    sign: Mapped[str] = mapped_column(String(2), primary_key=True)
    fee: Mapped[decimal.Decimal] = mapped_column(Numeric(7, 2))
    typename: Mapped[str] = mapped_column(String(10))
    plan: Mapped[str] = mapped_column(String(8))

    users: Mapped[List['Users']] = relationship('Users', back_populates='membership')


class Room(Base):
    __tablename__ = 'room'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='room_pkey'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    roomname: Mapped[str] = mapped_column(String(20))

    course: Mapped[List['Course']] = relationship('Course', back_populates='room')
    roomschedule: Mapped[List['Roomschedule']] = relationship('Roomschedule', back_populates='room')
    feedback: Mapped[List['Feedback']] = relationship('Feedback', back_populates='room')


class Course(Base):
    __tablename__ = 'course'
    __table_args__ = (
        ForeignKeyConstraint(['instructorid'], ['instructors.ssn'], name='fk_instructorid'),
        ForeignKeyConstraint(['roomid'], ['room.id'], name='fk_roomid'),
        PrimaryKeyConstraint('coursename', name='course_pkey')
    )

    coursename: Mapped[str] = mapped_column(String(20), primary_key=True)
    capacity: Mapped[decimal.Decimal] = mapped_column(Numeric(2, 0))
    isspecial: Mapped[bool] = mapped_column(Boolean)
    instructorid: Mapped[str] = mapped_column(String(20))
    roomid: Mapped[int] = mapped_column(Integer)

    instructors: Mapped['Instructors'] = relationship('Instructors', back_populates='course')
    room: Mapped['Room'] = relationship('Room', back_populates='course')
    users: Mapped[List['Users']] = relationship('Users', secondary='user_course', back_populates='course')
    roomschedule: Mapped[List['Roomschedule']] = relationship('Roomschedule', back_populates='course')


class Users(Base):
    __tablename__ = 'users'
    __table_args__ = (
        ForeignKeyConstraint(['membershiptype'], ['membership.sign'], name='fk_membershiptype'),
        PrimaryKeyConstraint('ssn', name='users_pkey')
    )

    ssn: Mapped[str] = mapped_column(String(20), primary_key=True)
    firstname: Mapped[str] = mapped_column(String(50))
    lastname: Mapped[str] = mapped_column(String(50))
    membershiptype: Mapped[Optional[str]] = mapped_column(String(2))

    course: Mapped[List['Course']] = relationship('Course', secondary='user_course', back_populates='users')
    membership: Mapped[Optional['Membership']] = relationship('Membership', back_populates='users')
    phone: Mapped[List['Phone']] = relationship('Phone', back_populates='users')
    roomschedule: Mapped[List['Roomschedule']] = relationship('Roomschedule', back_populates='users')
    feedback: Mapped[List['Feedback']] = relationship('Feedback', back_populates='users')


class Phone(Base):
    __tablename__ = 'phone'
    __table_args__ = (
        CheckConstraint("phone::text ~ '^\\+?[0-9\\s\\-\\(\\)]{6,20}$'::text", name='phone_phone_check'),
        ForeignKeyConstraint(['userssn'], ['users.ssn'], name='fk_userssn'),
        PrimaryKeyConstraint('phone', name='phone_pkey')
    )

    phone: Mapped[str] = mapped_column(String(20), primary_key=True)
    userssn: Mapped[Optional[str]] = mapped_column(String(20))

    users: Mapped[Optional['Users']] = relationship('Users', back_populates='phone')


class Roomschedule(Base):
    __tablename__ = 'roomschedule'
    __table_args__ = (
        ForeignKeyConstraint(['coursename'], ['course.coursename'], name='fk_coursename'),
        ForeignKeyConstraint(['roomid'], ['room.id'], name='fk_roomid'),
        ForeignKeyConstraint(['userid'], ['users.ssn'], name='fk_userid'),
        PrimaryKeyConstraint('scheduleid', name='roomschedule_pkey')
    )

    scheduleid: Mapped[int] = mapped_column(Integer, primary_key=True)
    roomid: Mapped[int] = mapped_column(Integer)
    scheduledate: Mapped[datetime.date] = mapped_column(Date)
    scheduletime: Mapped[datetime.time] = mapped_column(Time)
    bookingtype: Mapped[str] = mapped_column(String(10))
    isbooked: Mapped[bool] = mapped_column(Boolean)
    userid: Mapped[Optional[str]] = mapped_column(String(20))
    coursename: Mapped[Optional[str]] = mapped_column(String(20))

    course: Mapped[Optional['Course']] = relationship('Course', back_populates='roomschedule')
    room: Mapped['Room'] = relationship('Room', back_populates='roomschedule')
    users: Mapped[Optional['Users']] = relationship('Users', back_populates='roomschedule')
    feedback: Mapped[List['Feedback']] = relationship('Feedback', back_populates='roomschedule')


t_user_course = Table(
    'user_course', Base.metadata,
    Column('coursename', String(20), primary_key=True, nullable=False),
    Column('userid', String(20), primary_key=True, nullable=False),
    ForeignKeyConstraint(['coursename'], ['course.coursename'], name='fk_coursename'),
    ForeignKeyConstraint(['userid'], ['users.ssn'], name='fk_userid'),
    PrimaryKeyConstraint('coursename', 'userid', name='user_course_pkey')
)


class Feedback(Base):
    __tablename__ = 'feedback'
    __table_args__ = (
        ForeignKeyConstraint(['roomid'], ['room.id'], name='fk_roomid'),
        ForeignKeyConstraint(['scheduleid'], ['roomschedule.scheduleid'], name='fk_scheduleid'),
        ForeignKeyConstraint(['userid'], ['users.ssn'], name='fk_userid'),
        PrimaryKeyConstraint('feedbackno', name='feedback_pkey')
    )

    feedbackno: Mapped[int] = mapped_column(Integer, primary_key=True)
    roomid: Mapped[int] = mapped_column(Integer)
    userid: Mapped[str] = mapped_column(String(20))
    scheduleid: Mapped[int] = mapped_column(Integer)
    score: Mapped[decimal.Decimal] = mapped_column(Numeric(2, 1))
    comment: Mapped[Optional[str]] = mapped_column(String(200))

    room: Mapped['Room'] = relationship('Room', back_populates='feedback')
    roomschedule: Mapped['Roomschedule'] = relationship('Roomschedule', back_populates='feedback')
    users: Mapped['Users'] = relationship('Users', back_populates='feedback')
