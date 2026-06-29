"""
Dynamic data layer for parking data, reservations and admin reviews
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    Boolean, Column, DateTime,
    Float, ForeignKey, Integer,
    String, Text, Time, and_,
    create_engine, exists)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

def utc_now():
    return datetime.now(timezone.utc)

class ParkingSpace(Base):
    __tablename__ = "parking_spaces"
    id = Column(Integer, primary_key=True)
    zone = Column(String(50), nullable=False)
    is_available = Column(Boolean, nullable=False, default=True)
    hourly_price = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

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
        String(36),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: str(uuid4()))
    parking_space_id = Column(
        Integer,
        ForeignKey("parking_spaces.id"),
        nullable=False,
        index=True)
    name = Column(String(100), nullable=False)
    surname = Column(String(100), nullable=False)
    car_number = Column(String(20), nullable=False)
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending")
    admin_request_status = Column(
        String(30),
        nullable=False,
        default="not_sent")
    admin_request_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

class AdminReview(Base):
    """Durable Stage 2 hand-off record linking the two agents."""
    __tablename__ = "admin_reviews"
    id = Column(Integer, primary_key=True)
    reservation_id = Column(
        Integer,
        ForeignKey("reservations.id"),
        nullable=False,
        unique=True,
        index=True)
    thread_id = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True)
    state = Column(
        String(30),
        nullable=False,
        default="pending_admin",
        index=True)
    proposed_action = Column(String(50), nullable=True)
    admin_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    decided_at = Column(DateTime, nullable=True)

class Database:
    def __init__(self, dsn=None, settings=None, echo=False):
        if dsn is None:
            if settings is None:
                raise ValueError("Either dsn or settings must be provided")
            dsn = settings.postgres_dsn
        self.engine = create_engine(
            dsn,
            echo=echo,
            pool_pre_ping=True)
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            expire_on_commit=False)

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
            return [
                {
                    "day": row.day_of_week,
                    "open": row.open_time.strftime("%H:%M"),
                    "close": row.close_time.strftime("%H:%M")}
                for row in session.query(WorkingHours).all()]

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
            return [
                {
                    "zone": row.zone,
                    "hourly_price": row.hourly_price}
                for row in session.query(ParkingSpace).all()]

    def has_reservation_conflict(self, parking_space_id, period_start, period_end):
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

    def find_available_space(self, period_start, period_end, zone=None):
        with self.session() as session:
            overlapping = exists().where(
                and_(
                    Reservation.parking_space_id == ParkingSpace.id,
                    Reservation.status.in_(("pending", "approved")),
                    Reservation.period_start < period_end,
                    Reservation.period_end > period_start))

            query = session.query(ParkingSpace).filter(
                ParkingSpace.is_available.is_(True),
                ~overlapping)
            if zone:
                query = query.filter(ParkingSpace.zone == zone)
            row = query.order_by(ParkingSpace.id).first()
            if row is None:
                return None
            return {
                "id": row.id,
                "zone": row.zone,
                "hourly_price": row.hourly_price}

    def create_reservation(self, parking_space_id, name, surname, car_number, period_start, period_end):
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

    def mark_admin_request(self, reservation_id, status, error=None):
        if status not in {"not_sent", "sent", "failed"}:
            raise ValueError("Unsupported admin request status")

        with self.session() as session:
            reservation = (
                session.query(Reservation)
                .filter(Reservation.public_id == reservation_id)
                .one())
            reservation.admin_request_status = status
            reservation.admin_request_error = error

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
                "status": reservation.status,
                "admin_request_status": reservation.admin_request_status,
                "admin_request_error": reservation.admin_request_error}

    def create_admin_review(self, reservation_id, thread_id):
        with self.session() as session:
            reservation = (
                session.query(Reservation)
                .filter(Reservation.public_id == reservation_id)
                .one_or_none())
            if reservation is None:
                raise KeyError(f"Reservation not found: {reservation_id}")

            existing = (
                session.query(AdminReview)
                .filter(AdminReview.reservation_id == reservation.id)
                .one_or_none())
            if existing is None:
                existing = AdminReview(
                    reservation_id=reservation.id,
                    thread_id=thread_id,
                    state="pending_admin")
                session.add(existing)
                session.flush()

            reservation.admin_request_status = "sent"
            reservation.admin_request_error = None
            return self._review_dict(existing, reservation)

    def get_admin_review(self, reservation_id):
        with self.session() as session:
            row = (
                session.query(AdminReview, Reservation)
                .join(
                    Reservation,
                    AdminReview.reservation_id == Reservation.id)
                .filter(Reservation.public_id == reservation_id)
                .one_or_none())
            if row is None:
                return None
            review, reservation = row
            return self._review_dict(review, reservation)

    def list_admin_reviews(self, state=None):
        with self.session() as session:
            query = (
                session.query(AdminReview, Reservation)
                .join(
                    Reservation,
                    AdminReview.reservation_id == Reservation.id))
            if state:
                query = query.filter(AdminReview.state == state)

            return [
                self._review_dict(review, reservation)
                for review, reservation in query.order_by(
                    AdminReview.created_at.asc()
                ).all()]

    def mark_review_awaiting_confirmation(self, thread_id, proposed_action):
        with self.session() as session:
            review = (
                session.query(AdminReview)
                .filter(AdminReview.thread_id == thread_id)
                .one())
            review.state = "awaiting_confirmation"
            review.proposed_action = proposed_action

    def resolve_admin_review(self, reservation_id, decision, comment=None):
        if decision not in {"approved", "refused"}:
            raise ValueError("Decision must be 'approved' or 'refused'")

        with self.session() as session:
            row = (
                session.query(AdminReview, Reservation)
                .join(
                    Reservation,
                    AdminReview.reservation_id == Reservation.id)
                .filter(Reservation.public_id == reservation_id)
                .one())
            review, reservation = row

            if reservation.status != "pending":
                raise ValueError(
                    f"Reservation is already {reservation.status}")

            reservation.status = decision
            review.state = decision
            review.proposed_action = (
                "approve_reservation"
                if decision == "approved"
                else "refuse_reservation")
            review.admin_comment = comment
            review.decided_at = utc_now()

            session.flush()
            return self._review_dict(review, reservation)

    @staticmethod
    def _review_dict(review, reservation):
        return {
            "reservation_id": reservation.public_id,
            "thread_id": review.thread_id,
            "review_state": review.state,
            "proposed_action": review.proposed_action,
            "admin_comment": review.admin_comment,
            "created_at": review.created_at,
            "decided_at": review.decided_at,
            "reservation": {
                "name": reservation.name,
                "surname": reservation.surname,
                "car_number": reservation.car_number,
                "period_start": reservation.period_start,
                "period_end": reservation.period_end,
                "status": reservation.status,
                "parking_space_id": reservation.parking_space_id}}
