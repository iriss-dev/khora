#include "khora_hal.h"

void khora_watchdog_init(khora_watchdog_ctx_t *ctx) {
    if (!ctx) return;
    ctx->last_heartbeat_timestamp_ms = 0;
    ctx->sequence_id                 = 0;
    ctx->fault_code                  = KHORA_FAULT_NONE;
    ctx->current_state               = KHORA_STATE_STANDBY;
}

void khora_watchdog_feed(khora_watchdog_ctx_t *ctx, uint32_t seq, uint32_t now_ms) {
    if (!ctx) return;
    if (ctx->current_state == KHORA_STATE_FAULT_TRIPPED) {
        return;
    }

    /* A late packet cannot hide a missed deadline by arriving before the check. */
    if (ctx->current_state == KHORA_STATE_ENGAGED &&
        (uint32_t)(now_ms - ctx->last_heartbeat_timestamp_ms) >= KHORA_WATCHDOG_TIMEOUT_MS) {
        khora_emergency_braking_trigger(ctx, KHORA_FAULT_WATCHDOG_LOST);
        return;
    }

    /* Reject duplicate and backwards sequence numbers, including across wrap. */
    if (ctx->current_state == KHORA_STATE_ENGAGED &&
        ((uint32_t)(seq - ctx->sequence_id) == 0U ||
         (uint32_t)(seq - ctx->sequence_id) >= 0x80000000UL)) return;
    ctx->sequence_id = seq;
    ctx->last_heartbeat_timestamp_ms = now_ms;
    ctx->current_state = KHORA_STATE_ENGAGED;
}

bool khora_watchdog_check(khora_watchdog_ctx_t *ctx, uint32_t current_time_ms) {
    if (!ctx) return false;

    if (ctx->current_state == KHORA_STATE_FAULT_TRIPPED) {
        return false;
    }

    if (ctx->current_state == KHORA_STATE_ENGAGED) {
        uint32_t elapsed_ms = current_time_ms - ctx->last_heartbeat_timestamp_ms;
        if (elapsed_ms >= KHORA_WATCHDOG_TIMEOUT_MS) {
            khora_emergency_braking_trigger(ctx, KHORA_FAULT_WATCHDOG_LOST);
            return false;
        }
    }

    return true;
}

void khora_emergency_braking_trigger(khora_watchdog_ctx_t *ctx, uint8_t fault_reason) {
    if (!ctx) return;

    ctx->fault_code    = fault_reason;
    ctx->current_state = KHORA_STATE_FAULT_TRIPPED;
    khora_phased_array_disable();

    /* A board adapter must also disable physical outputs; this state is in RAM. */
}
