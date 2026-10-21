/* Host regression tests; no transducers or board drivers are enabled. */
#include "khora_protocol.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <string.h>

static uint8_t reply_bytes[268];
static size_t reply_size;
static unsigned replies;
static void capture(const uint8_t *bytes, size_t n, void *user) {
    (void)user; assert(n<=sizeof(reply_bytes));
    memcpy(reply_bytes,bytes,n); reply_size=n; replies++;
}
static size_t packet(uint8_t *bytes, uint8_t type, uint32_t seq, uint16_t length) {
    memset(bytes,0,(size_t)length+12U);
    bytes[0]=0x4b; bytes[1]=0x48; bytes[2]=1; bytes[3]=type;
    bytes[4]=(uint8_t)length; bytes[5]=(uint8_t)(length>>8);
    for (unsigned i=0;i<4;i++) bytes[6+i]=(uint8_t)(seq>>(8*i));
    for (unsigned i=0;i<length;i++) bytes[10+i]=(uint8_t)i;
    uint16_t crc=khora_crc16(bytes,(size_t)length+10U);
    bytes[10U+length]=(uint8_t)crc; bytes[11U+length]=(uint8_t)(crc>>8);
    return (size_t)length+12U;
}
int main(void) {
    khora_watchdog_ctx_t watchdog;
    khora_watchdog_init(&watchdog);
    khora_watchdog_feed(&watchdog,1,100);
    assert(khora_watchdog_check(&watchdog,149));
    assert(!khora_watchdog_check(&watchdog,150));
    khora_watchdog_feed(&watchdog,2,151);
    assert(watchdog.current_state==KHORA_STATE_FAULT_TRIPPED);

    khora_watchdog_init(&watchdog);
    khora_watchdog_feed(&watchdog,0xffffffffU,0xfffffff0U);
    khora_watchdog_feed(&watchdog,0,4); /* sequence and timer wrap */
    khora_watchdog_feed(&watchdog,0,20); /* duplicate cannot extend lease */
    assert(watchdog.last_heartbeat_timestamp_ms==4);
    assert(!khora_watchdog_check(&watchdog,54));
    khora_watchdog_init(&watchdog);
    khora_watchdog_feed(&watchdog,1,100);
    khora_watchdog_feed(&watchdog,2,150); /* late packet before check */
    assert(watchdog.current_state==KHORA_STATE_FAULT_TRIPPED);

    assert(khora_crc16((const uint8_t *)"123456789",9)==0x29b1U);
    khora_protocol_t protocol;
    khora_protocol_init(&protocol,capture,NULL);
    uint8_t bytes[268]; size_t n=packet(bytes,1,1,4);
    for (size_t i=0;i<n;i++) khora_protocol_receive(&protocol,bytes+i,1);
    assert(replies==1 && reply_size==19 && reply_bytes[3]==130 && reply_bytes[16]==1);
    assert(reply_bytes[10]==0 && reply_bytes[13]==3); /* nonce echoed */
    n=packet(bytes,2,2,256);
    khora_protocol_receive(&protocol,bytes,n);
    assert(reply_bytes[3]==128 && reply_bytes[10]==0);
    khora_protocol_receive(&protocol,bytes,n);
    assert(reply_bytes[10]==2); /* replay */
    unsigned before=replies; bytes[20]^=1;
    khora_protocol_receive(&protocol,bytes,n);
    assert(replies==before);
    n=packet(bytes,3,3,0); khora_protocol_receive(&protocol,bytes,n);
    assert(!protocol.session && reply_bytes[10]==0);
    n=packet(bytes,2,4,256); khora_protocol_receive(&protocol,bytes,n);
    assert(reply_bytes[10]==1); /* phases require handshake */
    return 0;
}
