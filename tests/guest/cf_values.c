#include "cf_checks.h"
#include <string.h>

void check_cf_values(void)
{
    CFMutableStringRef text = CFStringCreateMutableCopy(NULL, 0, CFSTR("e\u0301"));
    CHECK(text != NULL);
    CFStringNormalize(text, kCFStringNormalizationFormC);
    CHECK(CFEqual(text, CFSTR("\u00e9")));
    CFStringAppend(text, CFSTR(" \u0434\u0430\u0440\u0432\u0438\u043d"));
    char utf8[64];
    CHECK(CFStringGetCString(text, utf8, sizeof(utf8), kCFStringEncodingUTF8));
    CHECK(strcmp(utf8, "\xc3\xa9 \xd0\xb4\xd0\xb0\xd1\x80\xd0\xb2\xd0\xb8\xd0\xbd") == 0);

    int64_t original = 0x123456789abcdefLL;
    CFNumberRef number = CFNumberCreate(NULL, kCFNumberSInt64Type, &original);
    CFDateRef date = CFDateCreate(NULL, 123456789.0);
    CFMutableDictionaryRef dictionary = CFDictionaryCreateMutable(
        NULL, 0, &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
    CHECK(dictionary && number && date);
    CFDictionarySetValue(dictionary, CFSTR("text"), text);
    CFDictionarySetValue(dictionary, CFSTR("integer"), number);
    CFDictionarySetValue(dictionary, CFSTR("date"), date);
    CFDictionarySetValue(dictionary, CFSTR("enabled"), kCFBooleanTrue);
    const CFPropertyListFormat formats[] = {kCFPropertyListXMLFormat_v1_0,
                                            kCFPropertyListBinaryFormat_v1_0};
    for (unsigned i = 0; i < 2; ++i)
    {
        CFErrorRef error = NULL;
        CFDataRef encoded = CFPropertyListCreateData(NULL, dictionary, formats[i], 0, &error);
        CHECK(encoded && error == NULL);
        CFPropertyListFormat parsed_format;
        CFPropertyListRef decoded = CFPropertyListCreateWithData(
            NULL, encoded, kCFPropertyListImmutable, &parsed_format, &error);
        CHECK(decoded && error == NULL && parsed_format == formats[i]);
        CHECK(CFEqual(dictionary, decoded));
        int64_t recovered;
        CHECK(CFNumberGetValue(CFDictionaryGetValue(decoded, CFSTR("integer")), kCFNumberSInt64Type,
                               &recovered) &&
              recovered == original);
        CFRelease(decoded);
        CFRelease(encoded);
    }
    const UInt8 malformed[] = "<?xml version=\"1.0\"?><plist><dict><key>x</key></dict></plist>";
    CFDataRef invalid = CFDataCreate(NULL, malformed, sizeof(malformed) - 1);
    CFErrorRef error = NULL;
    CHECK(CFPropertyListCreateWithData(NULL, invalid, 0, NULL, &error) == NULL && error);
    CFRelease(error);
    CFRelease(invalid);
    CFRelease(dictionary);
    CFRelease(number);
    CFRelease(date);
    CFRelease(text);
    puts("corefoundation values: Unicode, XML and binary property lists passed");
}
