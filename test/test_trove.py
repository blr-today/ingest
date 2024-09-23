from trove import fetch_timings
import datetime
from common.tz import IST

d = datetime.datetime

DATE_FIXTURES = [
    ['Sat | Jun 29 | 10 AM - 12:30 PM', d(2024, 6, 29, 10, 0, tzinfo=IST), d(2024, 6, 29, 12, 30, tzinfo=IST)],
    ['Sat | Jun 29 | 3 - 6 PM', d(2024, 6, 29, 15, 0, tzinfo=IST), d(2024, 6, 29, 18, 0, tzinfo=IST)],
    ['Sun | Jun 30 | 9:30 -11:30 AM', d(2024, 6, 30, 9, 30, tzinfo=IST), d(2024, 6, 30, 11, 30, tzinfo=IST)],
    ['Sun | Jun 30 | 11 AM - 1 PM', d(2024, 6, 30, 11, 0, tzinfo=IST), d(2024, 6, 30, 13, 0, tzinfo=IST)],
    ['Sat | Jul 06 | 4 - 6:30 PM', d(2024, 7, 6, 16, 0, tzinfo=IST), d(2024, 7, 6, 18, 30, tzinfo=IST)],
    ['Sun | Jul 07 | 8:30 AM to 11:30 AM', d(2024, 7, 7, 8, 30, tzinfo=IST), d(2024, 7, 7, 11, 30, tzinfo=IST)],
    ['Sun | Jul 07 | 10 AM to 12:30 PM', d(2024, 7, 7, 10, 0, tzinfo=IST), d(2024, 7, 7, 12, 30, tzinfo=IST)],
    ['Sun | Jul 14 | 10:30 AM - 1 PM', d(2024, 7, 14, 10, 30, tzinfo=IST), d(2024, 7, 14, 13, 0, tzinfo=IST)],
    ['Sun | Jul 14 | 4 - 7 PM', d(2024, 7, 14, 16, 0, tzinfo=IST), d(2024, 7, 14, 19, 0, tzinfo=IST)]
]

class TestFetch:
    def test_time_splits(self):
        for date_str, expected_start, expected_end in DATE_FIXTURES:
            start_d, end_d = fetch_timings(date_str)
            assert start_d == expected_start
            assert end_d == expected_end
