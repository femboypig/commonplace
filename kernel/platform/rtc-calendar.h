#ifndef COMMONPLACE_RTC_CALENDAR_H
#define COMMONPLACE_RTC_CALENDAR_H
#ifdef __cplusplus
extern "C" {
#endif
struct commonplace_rtc_date {
    unsigned second, minute, hour, day, month, year, century, status;
};
unsigned long commonplace_rtc_decode(const struct commonplace_rtc_date *date);
long commonplace_rtc_seconds(void);
#ifdef __cplusplus
}
#endif
#endif
