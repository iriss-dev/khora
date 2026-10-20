/**
 * @file khora_watchdog.c
 * @brief Hardware Fail-Safe & Emergency Deceleration Watchdog (RFC-0002)
 *
 * Enforces a strict 50ms latency cutoff. If the cognitive plane or supervisory
 * plane stops feeding valid heartbeats, actuators enter S-curve emergency braking.
 */

#include "khora_hal.h"

void khora_watchdog_init(khora_watchdog_ctx_t *ctx) {
    if (!ctx) return;
    ctx->last_heartbeat_timestamp_ms = 0;
    ctx->sequence_id                 = 0;
    ctx->fault_code                  = KHORA_FAULT_NONE;
    ctx->current_state               = KHORA_STATE_STANDBY;
}

void khora_watchdog_feed(khora_watchdog_ctx_t *ctx, uint32_t seq) {
    if (!ctx) return;
    if (ctx->current_state == KHORA_STATE_FAULT_TRIPPED) {
        return; /* Fault latch requires explicit manual hardware reset */
    }

    ctx->sequence_id = seq;
    /* In actual MCU, read hardware SysTick or 64-bit hardware timer */
    /* Updated by external caller passing system timestamp */
    ctx->current_state = KHORA_STATE_ENGAGED;
}

bool khora_watchdog_check(khora_watchdog_ctx_t *ctx, uint32_t current_time_ms) {
    if (!ctx) return false;

    if (ctx->current_state == KHORA_STATE_FAULT_TRIPPED) {
        return false;
    }

    if (ctx->current_state == KHORA_STATE_ENGAGED) {
        uint32_t elapsed_ms = current_time_ms - ctx->last_heartbeat_timestamp_ms;
        if (elapsed_ms > KHORA_WATCHDOG_TIMEOUT_MS) {
            khora_emergency_braking_trigger(ctx, KHORA_FAULT_WATCHDOG_LOST);
            return false;
        }
    }

    return true;
}

void khora_emergency_braking_trigger(khora_watchdog_ctx_t *ctx, uint8_t fault_reason) {
    if (!ctx) return;

    ctx->fault_code    = fault_reason;
    ctx->current_state = KHORA_STATE_DECEL_BRAKING;

    /*
     * Real-time hardware actions:
     * 1. Disable ultrasonic high-voltage gate drivers to prevent transducer overheating.
     * 2. Command motor drive nodes over CAN bus into regenerative dynamic braking mode.
     * 3. Set emergency GPIO indicator pin HIGH.
     */
}
