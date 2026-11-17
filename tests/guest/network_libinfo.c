#include <arpa/inet.h>
#include <netdb.h>
#include <net/if.h>
#include <net/if_dl.h>
#include <netinet/if_ether.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(test) do { if (!(test)) { \
    fprintf(stderr, "network lookup failed at line %d: %s\n", __LINE__, #test); \
    exit(1); } } while (0)

static void *lookup_thread(void *context)
{
    const char *name = context;
    for (unsigned i = 0; i < 100; ++i) {
        struct netent *network = getnetbyname(name);
        CHECK(network && !strcmp(network->n_name, name));
        struct protoent *protocol = getprotobyname("tcp");
        CHECK(protocol && protocol->p_proto == 6);
        CHECK(!strcmp(network->n_name, name));
    }
    return NULL;
}

int main(void)
{
    fprintf(stderr, "network checks: numeric ipv4\n");
    struct sockaddr_in address;
    memset(&address, 0, sizeof(address));
    address.sin_len = sizeof(address);
    address.sin_family = AF_INET;
    address.sin_port = htons(12345);
    CHECK(inet_pton(AF_INET, "192.0.2.42", &address.sin_addr) == 1);
    char host[NI_MAXHOST], service[NI_MAXSERV];
    CHECK(getnameinfo((struct sockaddr *)&address, sizeof(address), host,
        sizeof(host), service, sizeof(service), NI_NUMERICHOST | NI_NUMERICSERV) == 0);
    CHECK(!strcmp(host, "192.0.2.42") && !strcmp(service, "12345"));
    CHECK(getnameinfo((struct sockaddr *)&address, sizeof(address), host,
        2, service, sizeof(service), NI_NUMERICHOST | NI_NUMERICSERV) == EAI_OVERFLOW);

    fprintf(stderr, "network checks: numeric ipv6\n");
    struct sockaddr_in6 address6;
    memset(&address6, 0, sizeof(address6));
    address6.sin6_len = sizeof(address6);
    address6.sin6_family = AF_INET6;
    CHECK(inet_pton(AF_INET6, "::1", &address6.sin6_addr) == 1);
    CHECK(getnameinfo((struct sockaddr *)&address6, sizeof(address6), host,
        sizeof(host), NULL, 0, NI_NUMERICHOST) == 0 && !strcmp(host, "::1"));

    fprintf(stderr, "network checks: address conversions\n");
    struct ether_addr *ether = ether_aton("52:54:00:12:34:56");
    CHECK(ether && ether->ether_addr_octet[0] == 0x52 && ether->ether_addr_octet[5] == 0x56);
    CHECK(!strcmp(ether_ntoa(ether), "52:54:0:12:34:56"));
    CHECK(inet_lnaof(address.sin_addr) == 42);
    CHECK(inet_makeaddr(0xc00002, 42).s_addr == address.sin_addr.s_addr);
    CHECK(inet_network("192.0.2") == 0xc00002);

    fprintf(stderr, "network checks: file databases\n");
    CHECK(getnetbyname("invalid") == NULL);
    struct netent *network = getnetbyname("testnet");
    CHECK(network && network->n_net == 0xc00002);
    network = getnetbyaddr(0xc00002, AF_INET);
    CHECK(network && !strcmp(network->n_name, "testnet"));
    setnetent(0);
    CHECK(getnetent() != NULL);
    endnetent();
    struct servent *entry = getservbyname("http", "tcp");
    CHECK(entry && entry->s_port == htons(80));
    entry = getservbyport(htons(80), "tcp");
    CHECK(entry && !strcmp(entry->s_name, "http"));
    struct protoent *protocol = getprotobynumber(17);
    CHECK(protocol && !strcmp(protocol->p_name, "udp"));

    fprintf(stderr, "network checks: concurrent lookups\n");
    pthread_t first, second;
    CHECK(!pthread_create(&first, NULL, lookup_thread, "testnet"));
    CHECK(!pthread_create(&second, NULL, lookup_thread, "loopback"));
    CHECK(!pthread_join(first, NULL) && !pthread_join(second, NULL));
    puts("native network address and database lookups passed");
    return 0;
}
