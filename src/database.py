"""
Dynamic data layer for parking availability, working hours, prices and reservations
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    Boolean, Column, DateTime,
    Float, ForeignKey, Integer,
    String, Time, and_,
    create_engine, exists)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class ParkingSpace(Base):
    __tablename__ = "parking_spaces"
    id = Column(Integer, primary_key=True)
    zone = Column(String(50), nullable=False)
    is_available = Column(Boolean, nullable=False, default=True)
    hourly_price = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

class WorkingHours(Base):
    __tablename__ = "working_hours"
    id = Column(Integer, primary_key=True)
    day_of_week = Column(String(20), nullable=False)
    open_time = Column(Time, nullable=False)
    close_time = Column(Time, nullable=False)

class Reservation(Base):
    __tablename__ = "reservations"
    id = Column(Integer, primary_key=True)
    public_id = Column(
        String(36), nullable=False, unique=True, index=True, default=lambda: str(uuid4()))
    parking_space_id = Column(Integer, ForeignKey("parking_spaces.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    surname = Column(String(100), nullable=False)
    car_number = Column(String(20), nullable=False)
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

class Database:
    def __init__(self, dsn=None, settings=None, echo=False):
        if dsn is None:
            if settings is None:
                raise ValueError("Either dsn or settings must be provided")
            dsn = settings.postgres_dsn
        self.engine = create_engine(dsn, echo=echo, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

    def create_all(self):
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self):
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_available_spaces(self, zone=None):
        with self.session() as session:
            query = session.query(ParkingSpace).filter(
                ParkingSpace.is_available.is_(True))
            if zone:
                query = query.filter(ParkingSpace.zone == zone)

            return [
                {
                    "id": row.id,
                    "zone": row.zone,
                    "hourly_price": row.hourly_price}
                for row in query.all()]

    def get_working_hours(self):
        with self.session() as session:
            rows = session.query(WorkingHours).all()
            return [
                {
                    "day": row.day_of_week,
                    "open": row.open_time.strftime("%H:%M"),
                    "close": row.close_time.strftime("%H:%M"),
                }
                for row in rows]

    def get_working_hours_for_day(self, day_of_week):
        with self.session() as session:
            row = (
                session.query(WorkingHours)
                .filter(WorkingHours.day_of_week == day_of_week)
                .one_or_none())
            if row is None:
                return None

            return {
                "day": row.day_of_week,
                "open_time": row.open_time,
                "close_time": row.close_time}

    def get_prices(self):
        with self.session() as session:
            rows = session.query(ParkingSpace).all()
            return [
                {"zone": row.zone, "hourly_price": row.hourly_price}
                for row in rows]

    def has_reservation_conflict(
            self, parking_space_id, period_start, period_end):
        with self.session() as session:
            conflict = (
                session.query(Reservation.id)
                .filter(
                    Reservation.parking_space_id == parking_space_id,
                    Reservation.status.in_(("pending", "approved")),
                    Reservation.period_start < period_end,
                    Reservation.period_end > period_start)
                .first())
            return conflict is not None

    def find_available_space(
        self, period_start, period_end, zone=None):
        with self.session() as session:
            overlapping_reservation = exists().where(
                and_(
                    Reservation.parking_space_id == ParkingSpace.id,
                    Reservation.status.in_(("pending", "approved")),
                    Reservation.period_start < period_end,
                    Reservation.period_end > period_start))

            query = session.query(ParkingSpace).filter(
                ParkingSpace.is_available.is_(True),
                ~overlapping_reservation)

            if zone:
                query = query.filter(ParkingSpace.zone == zone)
            row = query.order_by(ParkingSpace.id).first()
            if row is None:
                return None
            return {
                "id": row.id,
                "zone": row.zone,
                "hourly_price": row.hourly_price}

    def create_reservation(
        self, parking_space_id, name, surname, car_number,
        period_start, period_end):
        with self.session() as session:
            reservation = Reservation(
                parking_space_id=parking_space_id,
                name=name,
                surname=surname,
                car_number=car_number,
                period_start=period_start,
                period_end=period_end,
                status="pending")
            session.add(reservation)
            session.flush()
            return reservation.public_id

    def update_reservation_status(self, reservation_id, status):
        if status not in {"pending", "approved", "refused"}:
            raise ValueError("Unsupported reservation status")

        with self.session() as session:
            reservation = (
                session.query(Reservation)
                .filter(Reservation.public_id == reservation_id)
                .one())
            reservation.status = status

    def get_reservation(self, reservation_id):
        with self.session() as session:
            reservation = (
                session.query(Reservation)
                .filter(Reservation.public_id == reservation_id)
                .one_or_none())
            if reservation is None:
                return None

            return {
                "id": reservation.public_id,
                "parking_space_id": reservation.parking_space_id,
                "name": reservation.name,
                "surname": reservation.surname,
                "car_number": reservation.car_number,
                "period_start": reservation.period_start,
                "period_end": reservation.period_end,
                "status": reservation.status}
