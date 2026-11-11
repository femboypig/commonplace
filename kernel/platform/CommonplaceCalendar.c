#include "rtc-calendar.h"

static unsigned decode(unsigned value, unsigned binary)
{
    if (binary) return value;
    if ((value & 15) > 9 || (value >> 4) > 9) return 1000;
    return (value >> 4) * 10 + (value & 15);
}

unsigned long commonplace_rtc_decode(const struct commonplace_rtc_date *date)
{
    static const unsigned days[] = {31,28,31,30,31,30,31,31,30,31,30,31};
    unsigned binary = date->status & 4;
    unsigned second = decode(date->second, binary), minute = decode(date->minute, binary);
    unsigned hour = decode(date->hour & 0x7f, binary);
    unsigned day = decode(date->day, binary), month = decode(date->month, binary);
    unsigned year = decode(date->year, binary), century = decode(date->century, binary);
    if (!(date->status & 2)) {
        if (!hour || hour > 12) return 0;
        hour = hour % 12 + ((date->hour & 0x80) ? 12 : 0);
    }
    if (century != 20 || year > 99 || month < 1 || month > 12 ||
        !day || second > 59 || minute > 59 || hour > 23) return 0;
    year += century * 100;
    unsigned leap = !(year % 4) && (year % 100 || !(year % 400));
    if (day > days[month - 1] + (month == 2 && leap)) return 0;
    unsigned long total = 0;
    for (unsigned y = 1970; y < year; ++y)
        total += 365 + (!(y % 4) && (y % 100 || !(y % 400)));
    for (unsigned m = 1; m < month; ++m)
        total += days[m - 1] + (m == 2 && leap);
    return (((total + day - 1) * 24 + hour) * 60 + minute) * 60 + second;
}
