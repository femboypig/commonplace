#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>

void panic(const char *format, ...)
{
    va_list arguments;
    va_start(arguments, format);
    vfprintf(stderr, format, arguments);
    va_end(arguments);
    abort();
}
