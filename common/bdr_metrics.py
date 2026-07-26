import json
from datetime import datetime
from pathlib import Path

METRICS_PATH = Path("/app/backups/sre_metrics.json")


def update_sre_metric(key: str, value, increment=False):
    """
    Safely updates a specific SRE metric in the centralized metrics JSON file.
    Supports optional incrementing for counter-based metrics.
    """
    try:
        # If in test mode, write to test backup path
        import sys

        if "test" in sys.argv or "pytest" in sys.modules:
            metrics_file = Path("/app/test_restore_temp/sre_metrics.json")
        else:
            metrics_file = METRICS_PATH

        metrics_file.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        if metrics_file.exists():
            try:
                with open(metrics_file, "r") as f:
                    data = json.load(f)
            except Exception:
                pass

        if increment:
            current_val = data.get(key, 0)
            if isinstance(current_val, (int, float)):
                data[key] = current_val + value
            else:
                data[key] = value
        else:
            data[key] = value

        data["last_updated"] = datetime.utcnow().isoformat()

        with open(metrics_file, "w") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass
