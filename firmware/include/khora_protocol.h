#ifndef KHORA_PROTOCOL_H
#define KHORA_PROTOCOL_H
#include "khora_hal.h"
#include <stddef.h>

/* Dry-run transport adapter. USB CDC/UART and the hardware output gate belong
 * to the target board. This protocol deliberately has no ARM command. */
typedef void (*khora_protocol_send_fn)(const uint8_t *, size_t, void *);
typedef struct {
    uint8_t bytes[268];
    size_t used;
    uint32_t sequence;
    bool session;
    khora_protocol_send_fn send;
    void *user;
} khora_protocol_t;
uint16_t khora_crc16(const uint8_t *data, size_t length);
void khora_protocol_init(khora_protocol_t *ctx, khora_protocol_send_fn send, void *user);
void khora_protocol_receive(khora_protocol_t *ctx, const uint8_t *data, size_t length);
#endif
