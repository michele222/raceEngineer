from datetime import datetime, timezone, timedelta


def is_float(element: any) -> bool:
    # If you expect None to be passed:
    if element is None:
        return False
    try:
        float(element)
        return True
    except ValueError:
        return False


def timestamp():
    return datetime.now()


def timestamp_formatted():
    return datetime.now().strftime('%d-%m-%Y %H:%M:%S')


def time_iso(delta_seconds=0):
    time = datetime.now(timezone.utc) + timedelta(seconds=delta_seconds)
    return time.replace(microsecond=0).isoformat()


def current_year():
    return datetime.now().year


def get_hex_color(color):
    if not color:
        return '#111111'
    return f'#{color.lower()}'
