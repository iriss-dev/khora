#include "khora_protocol.h"
#include <string.h>

static uint32_t read32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
uint16_t khora_crc16(const uint8_t *data, size_t length) {
    uint16_t crc = 0xffffU;
    for (size_t i=0; i<length; i++) {
        crc ^= (uint16_t)data[i]<<8;
        for (uint8_t j=0; j<8; j++)
            crc = (uint16_t)((crc & 0x8000U) ? ((uint32_t)crc<<1)^0x1021U : (uint32_t)crc<<1);
    }
    return crc;
}
void khora_protocol_init(khora_protocol_t *ctx, khora_protocol_send_fn send, void *user) {
    if (!ctx) return;
    memset(ctx, 0, sizeof(*ctx)); ctx->send=send; ctx->user=user;
    khora_phased_array_disable();
}
static void reply(khora_protocol_t *ctx, uint8_t type, uint32_t seq, const uint8_t *payload, uint8_t length) {
    uint8_t out[19] = {0x4b, 0x48, 1, 0};
    out[3]=type; out[4]=length;
    for (uint8_t i=0; i<4; i++) out[6+i]=(uint8_t)(seq>>(8*i));
    memcpy(out+10, payload, length);
    uint16_t crc=khora_crc16(out, 10U+length);
    out[10U+length]=(uint8_t)crc; out[11U+length]=(uint8_t)(crc>>8);
    if (ctx->send) ctx->send(out, 12U+length, ctx->user);
}
static void dispatch(khora_protocol_t *ctx, uint16_t length) {
    const uint8_t *p=ctx->bytes;
    uint32_t seq=read32(p+6);
    uint8_t status=0;
    if (p[3]==1 && length==4) {
        uint8_t ready[7]; memcpy(ready, p+10, 4);
        ready[4]=0; ready[5]=1; ready[6]=1; /* 256 channels; dry-staging-only */
        khora_phased_array_disable(); ctx->session=true; ctx->sequence=seq;
        reply(ctx, 130, seq, ready, 7); return;
    }
    if (p[3]==3 && length==0) {
        khora_phased_array_disable(); ctx->session=false;
        reply(ctx, 128, seq, &status, 1); return;
    }
    if (p[3]!=2 || length!=256 || !ctx->session) status=1;
    else if ((uint32_t)(seq-ctx->sequence)==0U || (uint32_t)(seq-ctx->sequence)>=0x80000000UL) status=2;
    else {ctx->sequence=seq; khora_phased_array_update_phases(p+10, 256);}
    reply(ctx, 128, seq, &status, 1);
}
void khora_protocol_receive(khora_protocol_t *ctx, const uint8_t *data, size_t length) {
    if (!ctx || !data) return;
    for (size_t i=0; i<length; i++) {
        ctx->bytes[ctx->used++]=data[i];
        while (ctx->used>=2) {
            bool discard=ctx->bytes[0]!=0x4b || ctx->bytes[1]!=0x48;
            if (!discard && ctx->used<10) break;
            uint16_t n=0;
            if (!discard) {
                n=(uint16_t)(ctx->bytes[4] | (uint16_t)ctx->bytes[5]<<8);
                discard=ctx->bytes[2]!=1 || n>256;
                if (!discard && ctx->used<(size_t)n+12U) break;
            }
            if (!discard) {
                uint16_t crc=(uint16_t)(ctx->bytes[10U+n] | (uint16_t)ctx->bytes[11U+n]<<8);
                discard=crc!=khora_crc16(ctx->bytes, 10U+n);
            }
            size_t consumed=1;
            if (!discard) {dispatch(ctx,n); consumed=(size_t)n+12U;}
            ctx->used-=consumed; memmove(ctx->bytes,ctx->bytes+consumed,ctx->used);
        }
    }
}
