#!/usr/bin/env python3
"""按到家时间推出该在什么时候问「玩得怎么样」。

判定顺序（与 review/timing.md 第二节的表一一对应）：
    12:00 前到家        → 当天 17:00
    12:00–16:00 到家    → 当天 19:00
    16:00–18:00 到家    → 当天 20:30
    18:00 及以后到家    → 次日 10:00

「延迟约 5 小时」是这张表的来由，不是独立算法；表优先。
问询只落在 09:00–21:00。

用法:
    python3 scripts/remind_at.py 2026-11-27 16:20
    python3 scripts/remind_at.py --test
"""

import argparse
import sys
from datetime import datetime, timedelta

NEXT_DAY_HOUR = 10


def remind_at(home_at):
    h = home_at.hour + home_at.minute / 60.0
    day = home_at.replace(hour=0, minute=0, second=0, microsecond=0)
    if h < 12:
        return day.replace(hour=17, minute=0)
    if h < 16:
        return day.replace(hour=19, minute=0)
    if h < 18:
        return day.replace(hour=20, minute=30)
    return (day + timedelta(days=1)).replace(hour=NEXT_DAY_HOUR, minute=0)


CASES = [
    ("2026-11-27 11:30", "2026-11-27T17:00"),
    ("2026-11-27 09:00", "2026-11-27T17:00"),
    ("2026-11-27 12:00", "2026-11-27T19:00"),
    ("2026-11-27 15:10", "2026-11-27T19:00"),
    ("2026-11-27 17:40", "2026-11-27T20:30"),
    ("2026-11-27 18:00", "2026-11-28T10:00"),
    ("2026-11-27 20:30", "2026-11-28T10:00"),
    ("2026-11-27 23:10", "2026-11-28T10:00"),
]


def main():
    ap = argparse.ArgumentParser(description="推算反馈提醒时刻")
    ap.add_argument("date", nargs="?", help="出行日期 YYYY-MM-DD")
    ap.add_argument("home", nargs="?", help="预计到家时间 HH:MM")
    ap.add_argument("--test", action="store_true", help="跑内置用例")
    args = ap.parse_args()

    if args.test:
        ok = True
        for raw, expect in CASES:
            got = remind_at(datetime.strptime(raw, "%Y-%m-%d %H:%M")).strftime(
                "%Y-%m-%dT%H:%M"
            )
            good = got == expect
            ok = ok and good
            print(f"{'OK  ' if good else 'FAIL'} 到家 {raw} → 问 {got}　（期望 {expect}）")
        return 0 if ok else 1

    if not args.date or not args.home:
        print("用法: remind_at.py YYYY-MM-DD HH:MM", file=sys.stderr)
        return 1
    try:
        home_at = datetime.strptime(f"{args.date} {args.home}", "%Y-%m-%d %H:%M")
    except ValueError as e:
        print(f"[error] 时间格式不对：{e}", file=sys.stderr)
        return 1

    print(remind_at(home_at).isoformat())
    return 0


if __name__ == "__main__":
    sys.exit(main())
