/**
 * @file khora_hal.h
 * @brief KHORA Hardware Abstraction Layer & Real-Time Bus Protocol (RFC-0002)
 *
 * Targets: ARM Cortex-M0+ (RP2040 / STM32F0) and Cortex-M4F (STM32F4).
 * Pure deterministic C99 with zero dynamic memory allocation.
 */

#ifndef KHORA_HAL_H
#define KHORA_HAL_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* System Clock & Timer Constants */
#define KHORA_SYS_CLK_HZ           125000000UL /* 125 MHz RP2040 default */
#define KHORA_ULTRASOUND_FREQ_HZ   40000UL     /* 40 kHz ultrasound carrier */
#define KHORA_TIMER_TOP_TICKS      (KHORA_SYS_CLK_HZ / KHORA_ULTRASOUND_FREQ_HZ) /* 3125 ticks */

/* Hardware Watchdog Policy (RFC-0002 Section 3) */
#define KHORA_WATCHDOG_TIMEOUT_MS  50U         /* Trip cutoff threshold */
#define KHORA_HEARTBEAT_PERIOD_MS  10U         /* Nominal supervisor period */

/* Phased Array Hardware Dimensions */
#define KHORA_MAX_TRANSDUCERS      256U        /* 16x16 matrix maximum */
#define KHORA_AM_LUT_SIZE          32U         /* 200 Hz envelope lookup table */

/* Joint Actuator Limits */
#define KHORA_MAX_AXES             6U

typedef enum {
    KHORA_STATE_BOOT           = 0x00,
    KHORA_STATE_STANDBY        = 0x01,
    KHORA_STATE_ENGAGED        = 0x02,
    KHORA_STATE_DECEL_BRAKING  = 0x03,
    KHORA_STATE_FAULT_TRIPPED  = 0xFF,
} khora_system_state_t;

typedef enum {
    KHORA_FAULT_NONE           = 0x00,
    KHORA_FAULT_WATCHDOG_LOST  = 0x01,
    KHORA_FAULT_OVERCURRENT    = 0x02,
    KHORA_FAULT_LIMIT_EXCEEDED = 0x04,
    KHORA_FAULT_THERMAL_WARN   = 0x08,
} khora_fault_flags_t;

/* CAN Bus Kinematic Packet Frame */
typedef struct {
    uint32_t can_id;
    uint8_t  axis_index;
    int32_t  target_position_pulses;
    int16_t  target_velocity_rad_s_q8; /* Q8.8 fixed-point */
    uint16_t torque_feedforward_ma;
    uint8_t  sequence_counter;
} __attribute__((packed)) khora_motor_cmd_t;

/* Transducer Array Channel State */
typedef struct {
    uint16_t phase_delay_ticks; /* 0 to (KHORA_TIMER_TOP_TICKS - 1) */
    uint16_t duty_cycle_ticks;  /* 50% = KHORA_TIMER_TOP_TICKS / 2 */
    bool     enabled;
} khora_transducer_channel_t;

/* Hardware Watchdog Context */
typedef struct {
    volatile uint32_t last_heartbeat_timestamp_ms;
    volatile uint32_t sequence_id;
    volatile uint8_t  fault_code;
    khora_system_state_t current_state;
} khora_watchdog_ctx_t;

/* HAL Function Prototypes */
void khora_hal_init(void);
void khora_watchdog_init(khora_watchdog_ctx_t *ctx);
void khora_watchdog_feed(khora_watchdog_ctx_t *ctx, uint32_t seq);
bool khora_watchdog_check(khora_watchdog_ctx_t *ctx, uint32_t current_time_ms);
void khora_emergency_braking_trigger(khora_watchdog_ctx_t *ctx, uint8_t fault_reason);

void khora_phased_array_init(void);
void khora_phased_array_update_phases(const uint8_t *phases_8bit, uint16_t count);
void khora_phased_array_set_am_depth(float depth_0_to_1);

#ifdef __cplusplus
}
#endif

#endif /* KHORA_HAL_H */
