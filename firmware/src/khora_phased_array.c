/**
 * @file khora_phased_array.c
 * @brief 40 kHz Ultrasonic Phased Array Beamforming Driver (RFC-0001)
 *
 * Synthesizes sub-microsecond phase delays across transducer elements
 * with 200 Hz amplitude modulation (AM) envelope for tactile skin sensation.
 */

#include "khora_hal.h"
#include <string.h>
#include <math.h>

/* Precomputed 32-sample Sine Wave LUT for 200 Hz AM Modulation (Scale: Q15 fixed-point) */
static const uint16_t SINE_AM_LUT[KHORA_AM_LUT_SIZE] = {
    16384, 19580, 22653, 25486, 27969, 30006, 31520, 32452,
    32767, 32452, 31520, 30006, 27969, 25486, 22653, 19580,
    16384, 13187, 10114, 7281, 4798, 2761, 1247, 315,
    0, 315, 1247, 2761, 4798, 7281, 10114, 13187
};

static khora_transducer_channel_t g_channels[KHORA_MAX_TRANSDUCERS];
static volatile uint8_t g_am_lut_index = 0;
static uint16_t g_am_depth_q15 = 32767U;

void khora_phased_array_init(void) {
    for (uint16_t i = 0; i < KHORA_MAX_TRANSDUCERS; i++) {
        g_channels[i].phase_delay_ticks = 0;
        g_channels[i].duty_cycle_ticks  = KHORA_TIMER_TOP_TICKS / 2; /* 50% square wave */
        g_channels[i].enabled           = false;
    }
    g_am_lut_index = 0;
    g_am_depth_q15 = 32767U;
}

void khora_phased_array_update_phases(const uint8_t *phases_8bit, uint16_t count) {
    if (!phases_8bit) return;
    if (count > KHORA_MAX_TRANSDUCERS) count = KHORA_MAX_TRANSDUCERS;

    for (uint16_t i = 0; i < count; i++) {
        /* Map 8-bit phase [0, 255] to Timer compare ticks [0, KHORA_TIMER_TOP_TICKS - 1] */
        uint32_t ticks = ((uint32_t)phases_8bit[i] * KHORA_TIMER_TOP_TICKS) / 256U;
        g_channels[i].phase_delay_ticks = (uint16_t)ticks;
        /* Phase staging must never arm a physical output. */
    }
}

void khora_phased_array_set_am_depth(float depth_0_to_1) {
    if (!isfinite(depth_0_to_1)) depth_0_to_1 = 0.0f;
    if (depth_0_to_1 < 0.0f) depth_0_to_1 = 0.0f;
    if (depth_0_to_1 > 1.0f) depth_0_to_1 = 1.0f;
    g_am_depth_q15 = (uint16_t)(depth_0_to_1 * 32767.0f);
}

void khora_phased_array_disable(void) {
    for (uint16_t i = 0; i < KHORA_MAX_TRANSDUCERS; i++) {
        g_channels[i].enabled = false;
        g_channels[i].duty_cycle_ticks = 0;
    }
}

/**
 * @brief High-frequency timer interrupt service routine (called at 6.4 kHz / 32 samples per 200 Hz wave)
 */
void khora_phased_array_modulation_tick_isr(void) {
    /* Advance 200 Hz AM envelope phase */
    g_am_lut_index = (g_am_lut_index + 1) % KHORA_AM_LUT_SIZE;
    uint16_t raw_gain = (uint16_t)(32767U -
        ((uint32_t)g_am_depth_q15 * (32767U - SINE_AM_LUT[g_am_lut_index])) / 32767U);

    /* Scale carrier amplitude using fixed-point duty cycle trimming */
    uint32_t base_duty = KHORA_TIMER_TOP_TICKS / 2;
    uint32_t modulated_duty = (base_duty * raw_gain) >> 15;

    for (uint16_t i = 0; i < KHORA_MAX_TRANSDUCERS; i++) {
        if (g_channels[i].enabled) {
            g_channels[i].duty_cycle_ticks = (uint16_t)modulated_duty;
        }
    }
}
