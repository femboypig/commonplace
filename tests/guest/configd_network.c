#include <SystemConfiguration/SystemConfiguration.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(test) do { if (!(test)) { \
    fprintf(stderr, "network configuration failed at line %d: %s (SCError=%d)\n", \
        __LINE__, #test, SCError()); \
    exit(1); } } while (0)

static SCNetworkInterfaceRef ethernet(CFArrayRef interfaces)
{
    for (CFIndex i = 0; i < CFArrayGetCount(interfaces); ++i) {
        SCNetworkInterfaceRef interface = CFArrayGetValueAtIndex(interfaces, i);
        CFStringRef name = SCNetworkInterfaceGetBSDName(interface);
        if (name && CFEqual(name, CFSTR("en0"))) {
            CHECK(CFEqual(SCNetworkInterfaceGetInterfaceType(interface), kSCNetworkInterfaceTypeEthernet));
            CHECK(SCNetworkInterfaceGetHardwareAddressString(interface));
            return interface;
        }
    }
    CHECK(0 && "en0 missing from native interface discovery");
    return NULL;
}

static void check_service(SCNetworkServiceRef service)
{
    CHECK(SCNetworkServiceGetEnabled(service));
    CHECK(CFEqual(SCNetworkInterfaceGetBSDName(SCNetworkServiceGetInterface(service)), CFSTR("en0")));
    SCNetworkProtocolRef protocol = SCNetworkServiceCopyProtocol(service, kSCNetworkProtocolTypeIPv4);
    CHECK(protocol && SCNetworkProtocolGetEnabled(protocol));
    CFDictionaryRef configuration = SCNetworkProtocolGetConfiguration(protocol);
    CHECK(configuration && CFEqual(CFDictionaryGetValue(configuration, kSCPropNetIPv4ConfigMethod), kSCValNetIPv4ConfigMethodDHCP));
    CFRelease(protocol);
    protocol = SCNetworkServiceCopyProtocol(service, kSCNetworkProtocolTypeDNS);
    CHECK(protocol);
    configuration = SCNetworkProtocolGetConfiguration(protocol);
    CFArrayRef servers = configuration ? CFDictionaryGetValue(configuration, kSCPropNetDNSServerAddresses) : NULL;
    CHECK(servers && CFArrayGetCount(servers) == 1 && CFEqual(CFArrayGetValueAtIndex(servers, 0), CFSTR("192.0.2.53")));
    CFRelease(protocol);
}

static void check_applied(SCNetworkServiceRef service)
{
    SCDynamicStoreRef store = SCDynamicStoreCreate(NULL, CFSTR("applied network check"), NULL, NULL);
    CHECK(store);
    CFStringRef key = SCDynamicStoreKeyCreateNetworkServiceEntity(NULL,
        kSCDynamicStoreDomainSetup, SCNetworkServiceGetServiceID(service), kSCEntNetIPv4);
    CHECK(key);
    CFDictionaryRef configuration = NULL;
    for (unsigned attempt = 0; attempt < 100 && !configuration; ++attempt) {
        configuration = SCDynamicStoreCopyValue(store, key);
        if (!configuration) CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.1, true);
    }
    CHECK(configuration && CFEqual(CFDictionaryGetValue(configuration, kSCPropNetIPv4ConfigMethod),
        kSCValNetIPv4ConfigMethodDHCP));
    CFRelease(configuration);
    CFRelease(key);
    key = SCDynamicStoreKeyCreateNetworkInterface(NULL, kSCDynamicStoreDomainState);
    configuration = SCDynamicStoreCopyValue(store, key);
    CFArrayRef interfaces = configuration ? CFDictionaryGetValue(configuration, kSCPropNetInterfaces) : NULL;
    CHECK(interfaces && CFArrayContainsValue(interfaces, CFRangeMake(0, CFArrayGetCount(interfaces)), CFSTR("en0")));
    CFRelease(configuration);
    CFRelease(key);
    int mtu = 0;
    for (unsigned attempt = 0; attempt < 100 && mtu != 1400; ++attempt) {
        CHECK(SCNetworkInterfaceCopyMTU(SCNetworkServiceGetInterface(service), &mtu, NULL, NULL));
        if (mtu != 1400) CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.1, true);
    }
    CHECK(mtu == 1400);
    CFRelease(store);
}

int check_network_configuration(const char *mode)
{
    CFArrayRef interfaces = SCNetworkInterfaceCopyAll();
    CHECK(interfaces);
    SCNetworkInterfaceRef interface = ethernet(interfaces);
    SCPreferencesRef preferences = SCPreferencesCreate(NULL, CFSTR("network configuration check"), NULL);
    CHECK(preferences);
    if (!strcmp(mode, "network-write")) {
        CHECK(SCPreferencesLock(preferences, true));
        SCNetworkSetRef set = SCNetworkSetCreate(preferences);
        CHECK(set && SCNetworkSetSetName(set, CFSTR("commonplace test")));
        CHECK(SCNetworkSetSetCurrent(set));
        SCNetworkServiceRef service = SCNetworkServiceCreate(preferences, interface);
        CHECK(service && SCNetworkServiceSetName(service, CFSTR("ethernet test")));
        CHECK(SCNetworkServiceSetEnabled(service, true));
        CHECK(SCNetworkSetAddService(set, service));
        int requested_mtu = 1400;
        CFNumberRef mtu = CFNumberCreate(NULL, kCFNumberIntType, &requested_mtu);
        const void *mtu_key = kSCPropNetEthernetMTU, *mtu_value = mtu;
        CFDictionaryRef ethernet_configuration = CFDictionaryCreate(NULL, &mtu_key, &mtu_value, 1,
            &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
        CHECK(SCNetworkInterfaceSetConfiguration(SCNetworkServiceGetInterface(service), ethernet_configuration));
        CFRelease(ethernet_configuration);
        CFRelease(mtu);
        CHECK(SCNetworkServiceAddProtocolType(service, kSCNetworkProtocolTypeIPv4));
        CHECK(SCNetworkServiceAddProtocolType(service, kSCNetworkProtocolTypeDNS));
        const void *key = kSCPropNetIPv4ConfigMethod, *value = kSCValNetIPv4ConfigMethodDHCP;
        CFDictionaryRef configuration = CFDictionaryCreate(NULL, &key, &value, 1,
            &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
        SCNetworkProtocolRef protocol = SCNetworkServiceCopyProtocol(service, kSCNetworkProtocolTypeIPv4);
        CHECK(protocol && SCNetworkProtocolSetConfiguration(protocol, configuration));
        CHECK(SCNetworkProtocolSetEnabled(protocol, true));
        CFRelease(protocol);
        CFRelease(configuration);
        value = CFSTR("192.0.2.53");
        CFArrayRef servers = CFArrayCreate(NULL, &value, 1, &kCFTypeArrayCallBacks);
        key = kSCPropNetDNSServerAddresses;
        value = servers;
        configuration = CFDictionaryCreate(NULL, &key, &value, 1,
            &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
        protocol = SCNetworkServiceCopyProtocol(service, kSCNetworkProtocolTypeDNS);
        CHECK(protocol && SCNetworkProtocolSetConfiguration(protocol, configuration));
        CFRelease(protocol);
        CFRelease(configuration);
        CFRelease(servers);
        check_service(service);
        CHECK(SCPreferencesCommitChanges(preferences));
        CHECK(SCPreferencesApplyChanges(preferences));
        CHECK(SCPreferencesUnlock(preferences));
        check_applied(service);
        CFRelease(service);
        CFRelease(set);
    } else {
        CHECK(!strcmp(mode, "network-read"));
        SCNetworkSetRef set = SCNetworkSetCopyCurrent(preferences);
        CHECK(set && CFEqual(SCNetworkSetGetName(set), CFSTR("commonplace test")));
        CFArrayRef services = SCNetworkSetCopyServices(set);
        CHECK(services && CFArrayGetCount(services) == 1);
        check_service((SCNetworkServiceRef)CFArrayGetValueAtIndex(services, 0));
        check_applied((SCNetworkServiceRef)CFArrayGetValueAtIndex(services, 0));
        CFRelease(services);
        CFRelease(set);
    }
    CFRelease(preferences);
    CFRelease(interfaces);
    puts("native ethernet service and protocol configuration passed");
    return 0;
}
