import os
import re
from datetime import datetime, timedelta
from pathlib import Path


def parse_backup_timestamp(filename: str) -> datetime:
    """
    Parses timestamp from format: db_backup_20260724_132817.sql.gz.enc
    or config_backup_20260724_132817.tar.gz.enc
    """
    match = re.search(r"(\d{8})_(\d{6})", filename)
    if match:
        date_str, time_str = match.groups()
        try:
            return datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
        except ValueError:
            pass
    return None


def perform_gfs_retention_cleanup(backup_path: Path, prefix: str, stdout=None):
    """
    Performs Grandfather-Father-Son (GFS) retention cleanup on backup directory.
    prefix can be 'db_backup_' or 'config_backup_'.
    """
    retention_hourly = int(os.environ.get("RETENTION_HOURLY", 24))
    retention_daily = int(os.environ.get("RETENTION_DAILY", 7))
    retention_weekly = int(os.environ.get("RETENTION_WEEKLY", 4))
    retention_monthly = int(os.environ.get("RETENTION_MONTHLY", 12))

    if stdout:
        stdout.write(
            f"Initiating GFS Retention cleanup for '{prefix}' (Hourly: {retention_hourly}, Daily: {retention_daily}, Weekly: {retention_weekly}, Monthly: {retention_monthly})..."
        )

    # 1. Gather all files and their parsed timestamps
    backups = []
    for item in backup_path.iterdir():
        if (
            item.is_file()
            and item.name.startswith(prefix)
            and not item.name.endswith("_manifest.json")
        ):
            ts = parse_backup_timestamp(item.name)
            if ts:
                backups.append((item, ts))

    if not backups:
        if stdout:
            stdout.write("No backups found for GFS retention cleanup.")
        return

    # Sort backups by timestamp descending (newest first)
    backups.sort(key=lambda x: x[1], reverse=True)

    # Absolute newest backup is protected unconditionally
    newest_backup, newest_ts = backups[0]
    keep_set = {newest_backup}

    now = datetime.utcnow()

    # Buckets to keep the latest backup for each interval
    hourly_buckets = {}
    daily_buckets = {}
    weekly_buckets = {}
    monthly_buckets = {}

    for item, ts in backups:
        age = now - ts

        # Hourly GFS bucket
        if age <= timedelta(hours=retention_hourly):
            hour_key = (ts.date(), ts.hour)
            if hour_key not in hourly_buckets:
                hourly_buckets[hour_key] = item

        # Daily GFS bucket
        if age <= timedelta(days=retention_daily):
            day_key = ts.date()
            if day_key not in daily_buckets:
                daily_buckets[day_key] = item

        # Weekly GFS bucket
        if age <= timedelta(weeks=retention_weekly):
            week_key = ts.isocalendar()[:2]
            if week_key not in weekly_buckets:
                weekly_buckets[week_key] = item

        # Monthly GFS bucket
        if age <= timedelta(days=30 * retention_monthly):
            month_key = (ts.year, ts.month)
            if month_key not in monthly_buckets:
                monthly_buckets[month_key] = item

    # Add all bucket matches to keep set
    keep_set.update(hourly_buckets.values())
    keep_set.update(daily_buckets.values())
    keep_set.update(weekly_buckets.values())
    keep_set.update(monthly_buckets.values())

    # Perform actual deletion of expired files and log audit trails
    deleted_count = 0
    for item, ts in backups:
        if item not in keep_set:
            if stdout:
                stdout.write(
                    f" -> [AUDIT Retention Policy Purge] Deleting expired backup: {item.name} (Timestamp: {ts}, Age: {now - ts})"
                )

            item.unlink()
            deleted_count += 1

            # Delete matching manifest
            manifest = item.parent / f"{item.name}_manifest.json"
            if manifest.exists():
                manifest.unlink()

    if stdout:
        stdout.write(
            f"GFS Retention cleanup completed. Purged {deleted_count} expired files. Kept {len(keep_set)} files."
        )
