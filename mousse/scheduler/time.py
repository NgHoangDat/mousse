from datetime import datetime, timedelta
from functools import partial
from typing import *
from typing import Callable

from dateutil.relativedelta import relativedelta

from ..functional import (
    case,
    compose,
    concat,
    filter,
    identity,
    lt,
    map,
    mock,
    peek_nth,
)

Range = Tuple[int, int]
Time = Union[int, Range]
TimeConf = Union[int, Tuple[Time, ...]]


def __range(moments: Tuple[int, ...]):
    return lambda _: range(*moments)


def __get_moments(
    next_run_getter: Callable,
    pivot: datetime,
    moments: Tuple[int, ...],
    multi: bool,
    **kwargs
):
    return compose(
        tuple,
        sorted,
        concat,
        map(partial(next_run_getter, pivot, multi=False, **kwargs)),
        case(predicate=identity, action=mock(moments), otherwise=__range(moments)),
    )(multi)


def __move_by_delta(
    next_run_getter: Callable, pivot: datetime, delta: timedelta, **kwargs
):
    return compose(tuple, sorted)(
        next_run + delta if pivot >= next_run else next_run
        for next_run in next_run_getter(pivot, multi=True, **kwargs)
    )


def get_next_microsecond(
    now: datetime, microsecond: TimeConf = 0, multi: bool = True, **kwargs
) -> Tuple[datetime, ...]:
    if type(microsecond) is tuple:
        return __get_moments(get_next_microsecond, now, microsecond, multi, **kwargs)
    else:
        next_run = datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=now.hour,
            minute=now.minute,
            second=now.second,
            microsecond=microsecond,
        )
        if now > next_run:
            next_run += relativedelta(seconds=1)
        return (next_run,)


def get_next_second(
    now: datetime, second: Optional[TimeConf] = None, multi: bool = True, **kwargs
) -> Tuple[datetime, ...]:
    if second is not None:
        if type(second) is tuple:
            return __get_moments(get_next_second, now, second, multi, **kwargs)
        else:
            pivot = datetime(
                year=now.year,
                month=now.month,
                day=now.day,
                hour=now.hour,
                minute=now.minute,
                second=second,
            )
            return __move_by_delta(
                get_next_microsecond, pivot, relativedelta(minutes=1), **kwargs
            )

    return get_next_microsecond(now, multi=True, **kwargs)


def get_next_minute(
    now: datetime, minute: Optional[TimeConf] = None, multi: bool = True, **kwargs
) -> datetime:
    if minute is not None:
        if type(minute) is tuple:
            return __get_moments(get_next_minute, now, minute, multi, **kwargs)
        else:
            pivot = datetime(
                year=now.year,
                month=now.month,
                day=now.day,
                hour=now.hour,
                minute=minute,
            )
            return __move_by_delta(
                get_next_second, pivot, relativedelta(hours=1), **kwargs
            )
    return get_next_second(now, multi=True, **kwargs)


def get_next_hour(
    now: datetime, hour: Optional[TimeConf] = None, multi: bool = True, **kwargs
) -> datetime:
    if hour is not None:
        if type(hour) is tuple:
            return __get_moments(get_next_hour, now, hour, multi, **kwargs)
        else:
            pivot = datetime(year=now.year, month=now.month, day=now.day, hour=hour)
            return __move_by_delta(
                get_next_minute, pivot, relativedelta(days=1), **kwargs
            )
    return get_next_minute(now, multi=True, **kwargs)


def get_next_day(
    now: datetime, day: TimeConf = 0, multi: bool = True, **kwargs
) -> datetime:
    if day:
        if type(day) is tuple:
            return __get_moments(get_next_day, now, day, multi, **kwargs)
        else:
            pivot = datetime(year=now.year, month=now.month, day=day)
            return __move_by_delta(
                get_next_hour, pivot, relativedelta(months=1), **kwargs
            )
    return get_next_hour(now, multi=True, **kwargs)


def get_next_weekday(
    now: datetime, weekday: TimeConf = 0, multi: bool = True, **kwargs
) -> datetime:
    if weekday:
        if type(weekday) is tuple:
            return __get_moments(get_next_weekday, now, weekday, multi, **kwargs)
        else:
            weekday = max(weekday - 1, 0)
            pivot = datetime(year=now.year, month=now.month, day=now.day)
            if pivot.weekday() < weekday:
                pivot += relativedelta(days=weekday - pivot.weekday())

            if pivot.weekday() > weekday:
                pivot += relativedelta(days=7 + weekday - pivot.weekday())

            return __move_by_delta(
                get_next_hour, pivot, relativedelta(days=7), **kwargs
            )
    return get_next_day(now, multi=True, **kwargs)


def get_next_week(
    now: datetime, week: TimeConf = 0, multi: bool = True, **kwargs
) -> datetime:
    if week:
        if type(week) is tuple:
            return __get_moments(get_next_week, now, week, multi, **kwargs)
        else:
            pivot = datetime(year=now.year, month=now.month, day=1) + relativedelta(
                weeks=week - 1
            )
            next_runs = get_next_weekday(pivot, multi=True, **kwargs)
            for i, next_run in enumerate(next_runs):
                if next_run <= now:
                    if now.month < 12:
                        pivot = datetime(year=now.year, month=now.month + 1, day=1)
                    else:
                        pivot = datetime(year=now.year + 1, month=1, day=1)
                    pivot += relativedelta(weeks=week - 1)
                    next_runs[i] = get_next_weekday(pivot, multi=True, **kwargs)

            return compose(tuple, sorted)(next_runs)

    return get_next_weekday(now, multi=True, **kwargs)


def get_next_month(
    now: datetime, month: TimeConf = 0, multi: bool = True, **kwargs
) -> datetime:
    if month:
        if type(month) is tuple:
            return __get_moments(get_next_month, now, month, multi, **kwargs)
        else:
            pivot = datetime(
                year=now.year + (1 if now.month > month else 0), month=month, day=1
            )
            return __move_by_delta(
                get_next_week, pivot, relativedelta(years=1), **kwargs
            )
    return get_next_week(now, multi=True, **kwargs)


def get_next_year(
    now: datetime, year: int = 0, multi: bool = True, **kwargs
) -> Optional[datetime]:
    if year:
        if type(year) is tuple:
            return __get_moments(get_next_year, now, year, multi, **kwargs)
        else:
            pivot = datetime(year=year, month=1, day=1)
            return compose(tuple, filter(lt(now)), __move_by_delta)(
                get_next_month, pivot, relativedelta(), **kwargs
            )
    return get_next_month(now, multi=True, **kwargs)


def get_next_runtime(now: datetime, **kwargs) -> Optional[datetime]:
    return compose(peek_nth(0), get_next_year)(now, **kwargs)
