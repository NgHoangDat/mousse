from datetime import datetime, timedelta
from typing import *
from typing import Callable

from dateutil.relativedelta import relativedelta

Range = Tuple[int, int]
Time = Union[int, Range]
TimeConf = Union[int, Tuple[Time, ...]]


def log_result(func: Callable):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        print(func.__name__, result)
        return result

    return wrapper


# @log_result
def __get_moments(
    next_run_getter: Callable,
    now: datetime,
    pivot: datetime,
    moments: Tuple[int, ...],
    **kwargs
):
    if type(moments) is tuple:
        moments = range(*moments)

    candiates = []
    for momment in moments:
        if type(momment) in (tuple, list, set):
            candiate = __get_moments(next_run_getter, now, pivot, momment, **kwargs)
        else:
            candiate = next_run_getter(now, pivot, momment, **kwargs)

        if candiate:
            candiates.append(candiate)

    if candiates:
        candiates.sort()
        return candiates.pop(0)

    return None


def __get_closest_time(
    next_run_getter: Callable,
    now: datetime,
    pivot: datetime,
    delta: timedelta = None,
    **kwargs
):
    while True:
        next_run = next_run_getter(now, pivot, **kwargs)
        if next_run and next_run > now:
            return next_run

        if delta is None:
            return None

        pivot += delta


# @log_result
def get_next_microsecond(
    now: datetime, pivot: datetime = None, microsecond: TimeConf = 0, **kwargs
) -> Tuple[datetime, ...]:
    if type(microsecond) in (tuple, list, set):
        return __get_moments(get_next_microsecond, now, pivot, microsecond, **kwargs)
    else:
        pivot = pivot or now

        next_run = datetime(
            year=pivot.year,
            month=pivot.month,
            day=pivot.day,
            hour=pivot.hour,
            minute=pivot.minute,
            second=pivot.second,
            microsecond=microsecond,
        )

        # while now > next_run:
        #     next_run += relativedelta(seconds=1)

        return next_run


# @log_result
def get_next_second(
    now: datetime, pivot: datetime = None, second: TimeConf = None, **kwargs
) -> Tuple[datetime, ...]:
    if second is not None:
        if type(second) in (tuple, list, set):
            return __get_moments(get_next_second, now, pivot, second, **kwargs)
        else:
            pivot = pivot or now

            pivot = datetime(
                year=pivot.year,
                month=pivot.month,
                day=pivot.day,
                hour=pivot.hour,
                minute=pivot.minute,
                second=second,
            )
            next_run = __get_closest_time(
                get_next_microsecond, now, pivot, relativedelta(minutes=1), **kwargs
            )
            if next_run and next_run.second == second:
                return next_run

            return None

    return get_next_microsecond(now, pivot, **kwargs)


# @log_result
def get_next_minute(
    now: datetime, pivot: datetime = None, minute: Optional[TimeConf] = None, **kwargs
) -> datetime:
    if minute is not None:
        if type(minute) in (tuple, list, set):
            return __get_moments(get_next_minute, now, pivot, minute, **kwargs)
        else:
            pivot = pivot or now

            pivot = datetime(
                year=pivot.year,
                month=pivot.month,
                day=pivot.day,
                hour=pivot.hour,
                minute=minute,
            )
            next_run = __get_closest_time(
                get_next_second, now, pivot, relativedelta(hours=1), **kwargs
            )
            if next_run and next_run.minute == minute:
                return next_run

            return None

    return get_next_second(now, pivot, **kwargs)


# @log_result
def get_next_hour(
    now: datetime, pivot: datetime = None, hour: TimeConf = None, **kwargs
) -> datetime:
    if hour is not None:
        if type(hour) in (tuple, list, set):
            return __get_moments(get_next_hour, now, pivot, hour, **kwargs)
        else:
            pivot = pivot or now

            pivot = datetime(
                year=pivot.year, month=pivot.month, day=pivot.day, hour=hour
            )
            next_run = __get_closest_time(
                get_next_minute, now, pivot, relativedelta(days=1), **kwargs
            )
            if next_run and next_run.hour == hour:
                return next_run

            return None

    return get_next_minute(now, pivot, **kwargs)


# @log_result
def get_next_day(
    now: datetime, pivot: datetime = None, day: TimeConf = 0, **kwargs
) -> datetime:
    if day:
        if type(day) in (tuple, list, set):
            return __get_moments(get_next_day, now, pivot, day, **kwargs)
        else:
            pivot = pivot or now
            pivot = datetime(year=pivot.year, month=pivot.month, day=day)
            next_run = __get_closest_time(
                get_next_hour, now, pivot, relativedelta(months=1), **kwargs
            )
            if next_run and next_run.day == day:
                return next_run

            return None

    return get_next_hour(now, pivot, **kwargs)


# @log_result
def get_next_weekday(
    now: datetime, pivot: datetime = None, weekday: TimeConf = 0, **kwargs
) -> datetime:
    if weekday:
        if type(weekday) in (tuple, list, set):
            return __get_moments(get_next_weekday, now, pivot, weekday, **kwargs)
        else:
            weekday = max(weekday - 1, 0)
            pivot = pivot or now

            pivot = datetime(year=pivot.year, month=pivot.month, day=pivot.day)
            if pivot.weekday() < weekday:
                pivot += relativedelta(days=weekday - pivot.weekday())

            if pivot.weekday() > weekday:
                pivot += relativedelta(days=7 + weekday - pivot.weekday())

            next_run = __get_closest_time(
                get_next_hour, now, pivot, relativedelta(days=7), **kwargs
            )
            if next_run and next_run.weekday() == weekday:
                return next_run

            return None

    return get_next_day(now, pivot, **kwargs)


# @log_result
def get_next_week(
    now: datetime,
    pivot: datetime = None,
    week: TimeConf = 0,
    weekday: TimeConf = 0,
    **kwargs
) -> datetime:
    if week:
        if type(week) in (tuple, list, set):
            return __get_moments(
                get_next_week, now, pivot, week, weekday=weekday, **kwargs
            )
        else:
            pivot = pivot or now
            pivot = datetime(year=pivot.year, month=pivot.month, day=1)

            if week > 1:
                pivot += relativedelta(weeks=week - 1) - relativedelta(
                    days=pivot.weekday()
                )

            if weekday > 0:
                if pivot.weekday() > weekday - 1:
                    pivot += relativedelta(days=7 - pivot.weekday())

            next_run = __get_closest_time(
                get_next_weekday,
                now,
                pivot,
                relativedelta(months=1),
                weekday=weekday,
                **kwargs
            )

            if next_run is None:
                return None

            if (next_run - relativedelta(weeks=week)).month >= next_run.month:
                return None

            if (next_run - relativedelta(weeks=week - 1)).month != next_run.month:
                return None

            return next_run

    return get_next_weekday(now, pivot, weekday=weekday, **kwargs)


# @log_result
def get_next_month(
    now: datetime, pivot: datetime = None, month: TimeConf = 0, **kwargs
) -> datetime:
    if month:
        if type(month) in (tuple, list, set):
            return __get_moments(get_next_month, now, pivot, month, **kwargs)
        else:
            pivot = pivot or now
            pivot = datetime(year=pivot.year, month=month, day=1)
            if month < now.month:
                pivot += relativedelta(years=1)

            next_run = __get_closest_time(
                get_next_week, now, pivot, relativedelta(years=1), **kwargs
            )

            if next_run and next_run.month == month:
                return next_run
            return None

    return get_next_week(now, pivot, **kwargs)


# @log_result
def get_next_year(
    now: datetime, pivot: datetime = None, year: TimeConf = 0, **kwargs
) -> Optional[datetime]:
    if year:
        if type(year) in (tuple, list, set):
            return __get_moments(get_next_year, now, pivot, year, **kwargs)
        else:
            if now.year > year:
                return None

            pivot = datetime(year=year, month=1, day=1)
            next_run = __get_closest_time(get_next_month, now, pivot, None, **kwargs)

            if next_run and next_run.year == year:
                return next_run
            return None

    return get_next_month(now, pivot, **kwargs)


def get_next_runtime(now: datetime, **kwargs) -> Optional[datetime]:
    return get_next_year(now, **kwargs)
