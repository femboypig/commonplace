#include "runtime.h"
static void padded(unsigned long value, unsigned width)
{
    unsigned long bound=1;
    for (unsigned i=1; i<width; ++i) bound*=10;
    while (bound>1 && value<bound) { print(1, "0"); bound/=10; }
    print_number(1, value);
}
int main(void)
{
    struct system_time now;
    long error = sys_gettimeofday(&now);
    if (error < 0) { report_error("date", error); return 1; }
    if (now.seconds < 0) { print(2, "date: invalid calendar time\n"); return 1; }
    unsigned long days=(unsigned long)now.seconds/86400, time=(unsigned long)now.seconds%86400;
    unsigned year=1970, month=1;
    for (;;) {
        unsigned count=365 + (!(year%4) && (year%100 || !(year%400)));
        if (days<count) break;
        days-=count; ++year;
    }
    static const unsigned lengths[]={31,28,31,30,31,30,31,31,30,31,30,31};
    while (month<12) {
        unsigned count=lengths[month-1]+(month==2 && !(year%4) && (year%100 || !(year%400)));
        if (days<count) break;
        days-=count; ++month;
    }
    padded(year,4); print(1,"-"); padded(month,2); print(1,"-"); padded(days+1,2);
    print(1," "); padded(time/3600,2); print(1,":"); padded(time/60%60,2);
    print(1,":"); padded(time%60,2); print(1," UTC\n"); return 0;
}
