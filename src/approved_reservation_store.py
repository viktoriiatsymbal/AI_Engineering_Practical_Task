"""
Text-file storage for approved reservations
"""
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from filelock import FileLock

class ApprovedReservationStore:
    """Append approved reservations while preventing duplicate writes."""

    def __init__(self, output_file, index_file):
        self.output_file = Path(output_file).expanduser().resolve()
        self.index_file = Path(index_file).expanduser().resolve()
        self.lock_file = self.output_file.with_suffix(
            self.output_file.suffix + ".lock")

    @staticmethod
    def _safe(value):
        """Keep each reservation on one pipe-delimited line."""
        return str(value).replace("|", "/").replace("\r", " ").replace("\n", " ").strip()

    def _load_index(self):
        if not self.index_file.exists():
            return set()
        raw = json.loads(self.index_file.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("The reservation recording index must be a JSON list")
        return {str(item) for item in raw}

    def _write_index(self, recorded_ids):
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self.index_file.parent,
            delete=False) as temporary:
            json.dump(sorted(recorded_ids), temporary, indent=2)
            temporary.write("\n")
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, self.index_file)

    def format_line(self, reservation, approval_time):
        full_name = self._safe(
            f"{reservation['name']} {reservation['surname']}")
        car_number = self._safe(reservation["car_number"])
        period = self._safe(
            f"{reservation['period_start'].isoformat()} to "
            f"{reservation['period_end'].isoformat()}")
        approved_at = self._safe(approval_time.isoformat())
        return f"{full_name} | {car_number} | {period} | {approved_at}"

    def record(self, reservation_id, reservation, approval_time):
        """Write one exact-format entry; repeated calls are idempotent."""
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        line = self.format_line(reservation, approval_time)

        with FileLock(str(self.lock_file), timeout=10):
            recorded_ids = self._load_index()
            if reservation_id in recorded_ids:
                return {
                    "status": "already_recorded",
                    "reservation_id": reservation_id,
                    "file": str(self.output_file),
                    "line": line}

            if self.output_file.exists():
                existing_lines = set(
                    self.output_file.read_text(encoding="utf-8").splitlines())
                if line in existing_lines:
                    recorded_ids.add(reservation_id)
                    self._write_index(recorded_ids)
                    return {
                        "status": "already_recorded",
                        "reservation_id": reservation_id,
                        "file": str(self.output_file),
                        "line": line}

            with self.output_file.open("a", encoding="utf-8") as output:
                output.write(line + "\n")
                output.flush()
                os.fsync(output.fileno())

            recorded_ids.add(reservation_id)
            self._write_index(recorded_ids)

        return {
            "status": "recorded",
            "reservation_id": reservation_id,
            "file": str(self.output_file),
            "line": line}
