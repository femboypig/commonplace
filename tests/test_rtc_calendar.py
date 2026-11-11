"""Compare CMOS calendar decoding with the host's independent UTC calendar."""
import ctypes
from datetime import datetime, timezone
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent


class Date(ctypes.Structure):
    _fields_=[(name,ctypes.c_uint) for name in ('second','minute','hour','day','month','year','century','status')]


class CalendarTest(unittest.TestCase):
    def test_binary_bcd_leap_days_and_invalid_fields(self):
        with tempfile.TemporaryDirectory(prefix='commonplace-clock-') as temporary:
            library=Path(temporary)/'calendar.so'
            subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-shared','-fPIC',
                            str(ROOT/'kernel/platform/CommonplaceCalendar.c'),'-o',str(library)],check=True)
            decode=ctypes.CDLL(str(library)).commonplace_rtc_decode
            decode.argtypes=[ctypes.POINTER(Date)];decode.restype=ctypes.c_ulong
            generator=random.Random(739)
            for _ in range(1500):
                value=datetime(generator.randrange(2000,2100),generator.randrange(1,13),
                               generator.randrange(1,29),generator.randrange(24),generator.randrange(60),
                               generator.randrange(60),tzinfo=timezone.utc)
                for binary in (False,True):
                    encode=(lambda n:n) if binary else (lambda n:(n//10)*16+n%10)
                    for full_day in (False,True):
                        hour=value.hour if full_day else value.hour%12 or 12
                        raw_hour=encode(hour)|(0x80 if not full_day and value.hour>=12 else 0)
                        date=Date(encode(value.second),encode(value.minute),raw_hour,encode(value.day),
                                  encode(value.month),encode(value.year%100),encode(20),
                                  (4 if binary else 0)|(2 if full_day else 0))
                        self.assertEqual(decode(date),int(value.timestamp()))
            leap=Date(0,0,0,29,2,0,20,6)
            self.assertEqual(decode(leap),int(datetime(2000,2,29,tzinfo=timezone.utc).timestamp()))
            leap.year=25;self.assertEqual(decode(leap),0)
            for date in (Date(0x6a,0,0,1,1,0,0x20,2),Date(0,0,24,1,1,0,20,6),
                         Date(0,0,0,1,13,0,20,6),Date(0,0,0,0,1,0,20,6)):
                self.assertEqual(decode(date),0)
