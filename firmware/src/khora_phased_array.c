/**
 * @file khora_phased_array.c
 * @brief 40 kHz Ultrasonic Phased Array Beamforming Driver (RFC-0001)
 *
 * Synthesizes sub-microsecond phase delays across transducer elements
 * with 200 Hz amplitude modulation (AM) envelope for tactile skin sensation.
 */

#include "khora_hal.h"
#include <string.h>

/* Precomputed 32-sample Sine Wave LUT for 200 Hz AM Modulation (Scale: Q15 fixed-point) */
static const uint16_t SINE_AM_LUT[KHORA_AM_LUT_SIZE] = {
    16384, 19579, 22672, 25565, 28165, 30386, 32152, 33405,
    34101, 34219, 33753, 32709, 31110, 28994, 26418, 23450,
    20172, 16675, 13063,  9443,  5922,  2608,   589,     0,
      174,  1101,  2766,  5137,  8161, 11762, 15843, 20286
};

static khora_transducer_channel_t g_channels[KHORA_MAX_TRANSDUCERS];
static volatile uint8_t g_am_lut_index = 0;
static float g_am_modulation_depth = 1.0f;

void khora_phased_array_init(void) {
    for (uint16_t i = 0; i < KHORA_MAX_TRANSDUCERS; i++) {
        g_channels[i].phase_delay_ticks = 0;
        g_channels[i].duty_cycle_ticks  = KHORA_TIMER_TOP_TICKS / 2; /* 50% square wave */
        g_channels[i].enabled           = false;
    }
    g_am_lut_index = 0;
}

void khora_phased_array_update_phases(const uint8_t *phases_8bit, uint16_t count) {
    if (!phases_8bit) return;
    if (count > KHORA_MAX_TRANSDUCERS) count = KHORA_MAX_TRANSDUCERS;

    for (uint16_t i = 0; i < count; i++) {
        /* Map 8-bit phase [0, 255] to Timer compare ticks [0, KHORA_TIMER_TOP_TICKS - 1] */
        uint32_t ticks = ((uint32_t)phases_8bit[i] * KHORA_TIMER_TOP_TICKS) / 256U;
        g_channels[i].phase_delay_ticks = (uint16_t)ticks;
        g_channels[i].enabled = true;
    }
}

void khora_phased_array_set_am_depth(float depth_0_to_1) {
    if (depth_0_to_1 < 0.0f) depth_0_to_1 = 0.0f;
    if (depth_0_to_1 > 1.0f) depth_0_to_1 = 1.0f;
    g_am_modulation_depth = depth_0_to_1;
}

/**
 * @brief High-frequency timer interrupt service routine (called at 6.4 kHz / 32 samples per 200 Hz wave)
 */
void khora_phased_array_modulation_tick_isr(void) {
    /* Advance 200 Hz AM envelope phase */
    g_am_lut_index = (g_am_lut_index + 1) % KHORA_AM_LUT_SIZE;
    uint16_t raw_gain = SINE_AM_LUT[g_am_lut_index];

    /* Scale carrier amplitude using fixed-point duty cycle trimming */
    uint32_t base_duty = KHORA_TIMER_TOP_TICKS / 2;
    uint32_t modulated_duty = (base_duty * raw_gain) >> 15;

    for (uint16_t i = 0; i < KHORA_MAX_TRANSDUCERS; i++) {
        if (g_channels[i].enabled) {
            g_channels[i].duty_cycle_ticks = (uint16_t)modulated_duty;
        }
    }
}
