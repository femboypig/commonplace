#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/types.h>

typedef int Boolean;
#define FALSE 0
#define LCK_MTX_ASSERT_NOTOWNED 0
#define lck_mtx_assert(...) ((void)0)
#define panic(...) abort()
#define KEYDEBUG(...)
#define ipseclog(...)
#define PFKEY_STAT_INCREMENT(...) ((void)0)
#define PFKEY_UNUNIT64(length) ((length) << 3)
#define KEY_SENDUP_ONE 1
#define M_PKTHDR 1
#define mtod(packet, type) ((type)(packet)->data)
struct sadb_msg {
    uint8_t version, type, error, satype;
    uint16_t sadb_msg_len, reserved;
    uint32_t sequence, pid;
};
struct sadb_msghdr { int unused; };
struct socket { int unused; };
struct mbuf {
    int m_len, m_flags;
    struct { unsigned int len; } m_pkthdr;
    void *data;
};
static struct mbuf *m_pullup(struct mbuf *packet, int bytes)
{
    return NULL;
}

/* XNU_FRAMING */

int main(void)
{
    struct socket socket = {0};
    struct sadb_msg header = {0};
    struct mbuf packet = {sizeof(header), M_PKTHDR, {sizeof(header)}, &header};
    header.sadb_msg_len = sizeof(header) / 8;
    assert(key_parse(&packet, &socket) == 0);
    for (unsigned int words = 0; words < 5; ++words) {
        header.sadb_msg_len = words;
        assert(key_parse(&packet, &socket) == (words * 8 == sizeof(header) ? 0 : EINVAL));
    }
    header.sadb_msg_len = sizeof(header) / 8;
    packet.m_pkthdr.len += 8;
    assert(key_parse(&packet, &socket) == EINVAL);
    packet.m_pkthdr.len = sizeof(header);
    packet.m_flags = 0;
    assert(key_parse(&packet, &socket) == EINVAL);
    return 0;
}
