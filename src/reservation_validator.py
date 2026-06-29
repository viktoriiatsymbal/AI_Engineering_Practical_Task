"""
Validation rules for reservation
"""
import re
from datetime import datetime, timedelta

_NAME_RE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ'’-]{2,100}$")
_CAR_RE = re.compile(r"^[A-Z]{1,3}\d{3,4}[A-Z]{0,2}$")

class ReservationValidator:
    def __init__(self, database, max_duration_hours=24, now_provider=datetime.now):
        self.db = database
        self.max_duration = timedelta(hours=max_duration_hours)
        self.now_provider = now_provider

    def validate(self, *, name, surname, car_number, period_start, period_end):
        errors = {}

        if not _NAME_RE.fullmatch(name.strip()):
            errors["name"] = (
                "The first name must contain at least 2 letters and may only "
                "contain letters, apostrophes or hyphens.")

        if not _NAME_RE.fullmatch(surname.strip()):
            errors["surname"] = (
                "The surname must contain at least 2 letters and may only "
                "contain letters, apostrophes or hyphens.")

        normalized_car = car_number.replace(" ", "").replace("-", "").upper()
        if not _CAR_RE.fullmatch(normalized_car):
            errors["car_number"] = (
                "The car registration number has an invalid format. "
                "Example: AA1234BB.")

        now = self.now_provider()
        if period_start <= now:
            errors["period_start"] = "The reservation start time must be in the future."

        if period_end <= period_start:
            errors["period_end"] = (
                "The reservation end time must be later than the start time.")
            return errors

        if period_end - period_start > self.max_duration:
            errors["period_end"] = (
                f"The reservation cannot exceed "
                f"{int(self.max_duration.total_seconds() // 3600)} hours.")

        if period_start.date() != period_end.date():
            errors["period_end"] = (
                "A reservation must start and end on the same calendar day.")
            return errors

        working_hours = self.db.get_working_hours_for_day(
            period_start.strftime("%A"))
        if working_hours is None:
            errors["period_start"] = (
                "The parking facility has no configured working hours for that day.")
            return errors

        if (
            period_start.time() < working_hours["open_time"]
            or period_end.time() > working_hours["close_time"]):
            errors["period_start"] = (
                "The requested period is outside the parking facility's working hours "
                f"({working_hours['open_time'].strftime('%H:%M')}-"
                f"{working_hours['close_time'].strftime('%H:%M')}).")
        return errors
