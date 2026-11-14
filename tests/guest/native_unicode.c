#include "foundation_checks.h"
#include <NSSystemDirectories.h>
#include <limits.h>
#include <pthread.h>
#include <string.h>
#include <unicode/ucal.h>
#include <unicode/ucnv.h>
#include <unicode/ucol.h>
#include <unicode/udata.h>
#include <unicode/unorm2.h>
#include <unicode/ustring.h>

static void *normalize(void *argument)
{
    UErrorCode error = U_ZERO_ERROR;
    const UNormalizer2 *normalizer = unorm2_getNFCInstance(&error);
    CHECK(U_SUCCESS(error));
    const UChar input[] = {0x65, 0x301, 0x20, 0x1e9b, 0x323};
    const UChar expected[] = {0xe9, 0x20, 0x1e9b, 0x323};
    for (int i = 0; i < 100; ++i)
    {
        UChar output[16];
        CHECK(unorm2_normalize(normalizer, input, 5, output, 16, &error) == 4);
        CHECK(U_SUCCESS(error) && memcmp(output, expected, sizeof(expected)) == 0);
    }
    return argument;
}

void check_native_unicode(void)
{
    UErrorCode error = U_ZERO_ERROR;
    /* Require the installed data archive; do not fall back to external files. */
    udata_setFileAccess(UDATA_ONLY_PACKAGES, &error);
    CHECK(U_SUCCESS(error));
    CHECK(strcmp(u_getDataDirectory(), "/usr/share/icu") == 0);
    pthread_t threads[4];
    for (int i = 0; i < 4; ++i)
        CHECK(pthread_create(&threads[i], NULL, normalize, NULL) == 0);
    for (int i = 0; i < 4; ++i)
        CHECK(pthread_join(threads[i], NULL) == 0);

    UChar lower[32], upper[32];
    int32_t count;
    u_strFromUTF8(lower, 32, &count,
                  "stra\xc3\x9f"
                  "e",
                  -1, &error);
    CHECK(U_SUCCESS(error));
    CHECK(u_strToUpper(upper, 32, lower, count, "de", &error) == 7);
    CHECK(U_SUCCESS(error) && upper[4] == 'S' && upper[5] == 'S');

    UCollator *collator = ucol_open("sv_SE", &error);
    CHECK(U_SUCCESS(error) && collator);
    const UChar z[] = {'z'}, a_ring[] = {0xe5};
    CHECK(ucol_strcoll(collator, z, 1, a_ring, 1) == UCOL_LESS);
    ucol_close(collator);

    UConverter *converter = ucnv_open("windows-1251", &error);
    CHECK(U_SUCCESS(error) && converter);
    const char russian[] = {(char)0xcf, (char)0xf0, (char)0xe8, (char)0xe2, (char)0xe5, (char)0xf2};
    CHECK(ucnv_toUChars(converter, lower, 32, russian, 6, &error) == 6);
    CHECK(U_SUCCESS(error) && lower[0] == 0x41f && lower[5] == 0x442);
    ucnv_close(converter);

    const UChar zone[] = {'E', 't', 'c', '/', 'U', 'T', 'C', 0};
    UCalendar *calendar = ucal_open(zone, -1, "en_US", UCAL_GREGORIAN, &error);
    CHECK(U_SUCCESS(error) && calendar);
    ucal_setMillis(calendar, 0, &error);
    CHECK(ucal_get(calendar, UCAL_YEAR, &error) == 1970);
    CHECK(ucal_get(calendar, UCAL_MONTH, &error) == UCAL_JANUARY);
    CHECK(ucal_get(calendar, UCAL_DATE, &error) == 1 && U_SUCCESS(error));
    ucal_close(calendar);

    char path[PATH_MAX];
    NSSearchPathEnumerationState state = NSStartSearchPathEnumeration(
        NSLibraryDirectory, NSUserDomainMask | NSLocalDomainMask | NSNetworkDomainMask);
    const char *expected[] = {"~/Library", "/Library", "/Network/Library"};
    for (int i = 0; i < 3; ++i)
    {
        state = NSGetNextSearchPathEnumeration(state, path);
        CHECK(state && strcmp(path, expected[i]) == 0);
    }
    CHECK(NSGetNextSearchPathEnumeration(state, path) == 0);
    puts("native unicode: concurrent normalization, collation, conversion and calendar passed");
}

int main(void)
{
    check_native_math();
    check_native_unicode();
    puts("native foundation dependencies passed");
    return 0;
}
