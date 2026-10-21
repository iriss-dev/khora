#include "control.hpp"
#include "parallel.pio.h"
#include "pico/stdlib.h"
#include "pico/stdio_usb.h"
#include "hardware/clocks.h"
#include "hardware/dma.h"
#include "hardware/sync.h"
#include "hardware/uart.h"

namespace {
constexpr uint acoustic_gate = 16, interlock_pin = 17, arm_pin = 18;
constexpr uint uart_tx = 20, uart_rx = 21, uart_direction = 22, servo_gate = 26;
PIO pio = pio0;
uint sm, program_offset;
int data_dma, control_dma;
alignas(512) uint32_t banks[3][128]{};
volatile uint32_t next_bank;
khora::Control control(KHORA_ENABLE_OUTPUTS != 0);
khora::Decoder decoder;
bool dma_started = false;

bool interlock_closed() { return gpio_get(interlock_pin) == 0; }
void disable_outputs() {
    gpio_put(acoustic_gate, 0);
    gpio_put(servo_gate, 0);
    pio_sm_set_enabled(pio, sm, false);
    pio_sm_set_pins_with_mask(pio, sm, 0, 0xffff);
}
bool deadline(struct repeating_timer*) {
    if (control.tick(time_us_32(), interlock_closed())) disable_outputs();
    return true;
}
void stop_dma() {
    if (!dma_started) return;
    hw_clear_bits(&dma_hw->ch[control_dma].ctrl_trig, DMA_CH0_CTRL_TRIG_EN_BITS);
    hw_clear_bits(&dma_hw->ch[data_dma].ctrl_trig, DMA_CH0_CTRL_TRIG_EN_BITS);
    dma_channel_abort(control_dma);
    dma_channel_abort(data_dma);
    dma_started = false;
}
void publish_phases() {
    const uint32_t active = dma_channel_hw_addr(data_dma)->read_addr & ~uint32_t(511);
    unsigned index = 0;
    for (; index < 3; ++index) {
        const auto address = reinterpret_cast<uint32_t>(banks[index]);
        if (address != active && address != next_bank) break;
    }
    if (index == 3) return;
    const auto wave = khora::waveform(control.phases);
    std::memcpy(banks[index], wave.data(), sizeof(banks[index]));
    __dmb();
    next_bank = reinterpret_cast<uint32_t>(banks[index]);
}
void start_dma() {
    stop_dma();
    pio_sm_clear_fifos(pio, sm);
    pio_sm_restart(pio, sm);
    pio_sm_exec(pio, sm, pio_encode_jmp(program_offset));
    dma_channel_config data = dma_channel_get_default_config(data_dma);
    channel_config_set_transfer_data_size(&data, DMA_SIZE_32);
    channel_config_set_read_increment(&data, true);
    channel_config_set_write_increment(&data, false);
    channel_config_set_ring(&data, false, 9);
    channel_config_set_dreq(&data, pio_get_dreq(pio, sm, true));
    channel_config_set_chain_to(&data, control_dma);
    channel_config_set_high_priority(&data, true);
    dma_channel_configure(data_dma, &data, &pio->txf[sm], reinterpret_cast<const void*>(next_bank), 128, false);
    dma_channel_config reload = dma_channel_get_default_config(control_dma);
    channel_config_set_transfer_data_size(&reload, DMA_SIZE_32);
    channel_config_set_read_increment(&reload, false);
    channel_config_set_write_increment(&reload, false);
    channel_config_set_high_priority(&reload, true);
    dma_channel_configure(control_dma, &reload, &dma_hw->ch[data_dma].al3_read_addr_trig, &next_bank, 1, false);
    dma_started = true;
    dma_start_channel_mask(1u << data_dma);
    pio_sm_set_enabled(pio, sm, true);
}
void servo_send(const uint8_t* bytes, size_t size) {
    gpio_put(uart_direction, 1);
    busy_wait_us_32(2);
    uart_write_blocking(uart1, bytes, size);
    uart_tx_wait_blocking(uart1);
    while (uart_is_readable(uart1)) (void)uart_getc(uart1);
    gpio_put(uart_direction, 0);
}
khora::Reply servo_read(uint8_t id) {
    uint8_t request[] = {255, 255, id, 4, 2, 56, 12, 0};
    request[7] = static_cast<uint8_t>(~(id + 4 + 2 + 56 + 12));
    servo_send(request, sizeof(request));
    std::array<uint8_t, 32> response{};
    size_t used = 0;
    const uint32_t start = time_us_32();
    while (uint32_t(time_us_32() - start) < 3000) {
        if (!uart_is_readable(uart1)) continue;
        const uint8_t byte = uart_getc(uart1);
        if ((used == 0 || used == 1) && byte != 255) { used = 0; continue; }
        response[used++] = byte;
        if (used == 4 && (response[2] != id || response[3] != 14)) { used = 0; continue; }
        if (used == 18) {
            uint8_t sum = 0;
            for (unsigned i = 2; i < 18; ++i) sum = static_cast<uint8_t>(sum + response[i]);
            if (sum != 255) break;
            khora::Reply reply;
            reply.type = 0x83; reply.size = 14;
            reply.payload[0] = id; reply.payload[1] = response[4];
            std::memcpy(reply.payload.data() + 2, response.data() + 5, 12);
            return reply;
        }
    }
    khora::Reply reply; reply.payload[0] = 5; return reply;
}
void send_reply(uint32_t seq, const khora::Reply& reply) {
    uint8_t frame[44] = {'K', 'H', 2, reply.type, reply.size, 0};
    for (unsigned i = 0; i < 4; ++i) frame[6 + i] = static_cast<uint8_t>(seq >> (8 * i));
    std::memcpy(frame + 10, reply.payload.data(), reply.size);
    const uint16_t crc = khora::crc16(frame, 10 + reply.size);
    frame[10 + reply.size] = static_cast<uint8_t>(crc);
    frame[11 + reply.size] = static_cast<uint8_t>(crc >> 8);
    for (unsigned i = 0; i < 12u + reply.size; ++i) putchar_raw(frame[i]);
    stdio_flush();
}
}

int main() {
    set_sys_clock_khz(133000, true);
    for (uint pin : {acoustic_gate, servo_gate, uart_direction}) {
        gpio_init(pin); gpio_put(pin, 0); gpio_set_dir(pin, GPIO_OUT);
    }
    for (uint pin : {interlock_pin, arm_pin}) {
        gpio_init(pin); gpio_set_dir(pin, GPIO_IN); gpio_pull_up(pin);
    }
    stdio_init_all();
    uart_init(uart1, 1000000);
    gpio_set_function(uart_tx, GPIO_FUNC_UART);
    gpio_set_function(uart_rx, GPIO_FUNC_UART);
    uart_set_format(uart1, 8, 1, UART_PARITY_NONE);
    uart_set_hw_flow(uart1, false, false);
    sm = pio_claim_unused_sm(pio, true);
    program_offset = pio_add_program(pio, &khora_parallel_program);
    for (uint pin = 0; pin < 16; ++pin) pio_gpio_init(pio, pin);
    pio_sm_set_consecutive_pindirs(pio, sm, 0, 16, true);
    pio_sm_config config = khora_parallel_program_get_default_config(program_offset);
    sm_config_set_out_pins(&config, 0, 16);
    sm_config_set_out_shift(&config, true, true, 32);
    sm_config_set_fifo_join(&config, PIO_FIFO_JOIN_TX);
    sm_config_set_clkdiv(&config, static_cast<float>(clock_get_hz(clk_sys)) / (khora::carrier_hz * 256));
    pio_sm_init(pio, sm, program_offset, &config);
    disable_outputs();
    data_dma = dma_claim_unused_channel(true);
    control_dma = dma_claim_unused_channel(true);
    next_bank = reinterpret_cast<uint32_t>(banks[0]);
    struct repeating_timer timer;
    add_repeating_timer_us(-250, deadline, nullptr, &timer);
    bool was_armed = false;
    while (true) {
        const uint32_t irq = save_and_disable_interrupts();
        if (!stdio_usb_connected() && control.armed) { control.fault = 3; control.stop(); disable_outputs(); }
        const bool armed_now = control.armed;
        restore_interrupts(irq);
        if (!armed_now && dma_started) stop_dma();
        if (was_armed && !armed_now) {
            constexpr uint8_t torque_off[] = {255, 255, 254, 4, 3, 40, 0, 210};
            servo_send(torque_off, sizeof(torque_off));
        }
        was_armed = armed_now;
        const int c = getchar_timeout_us(0);
        if (c < 0) { tight_loop_contents(); continue; }
        if (!decoder.push(static_cast<uint8_t>(c))) continue;
        const auto* bytes = decoder.bytes.data();
        const uint32_t seq = khora::read32(bytes + 6);
        const uint32_t flags = save_and_disable_interrupts();
        auto reply = control.process(bytes[3], seq, bytes + 10, khora::read16(bytes + 4), time_us_32(), interlock_closed(), gpio_get(arm_pin) == 0);
        if (!control.armed) disable_outputs();
        restore_interrupts(flags);
        if (reply.action == khora::Action::phases) publish_phases();
        if (reply.action == khora::Action::arm) {
            start_dma();
            const uint32_t lock = save_and_disable_interrupts();
            if (control.armed && interlock_closed()) { gpio_put(acoustic_gate, control.output_mask & 1); gpio_put(servo_gate, (control.output_mask & 2) != 0); }
            else disable_outputs();
            restore_interrupts(lock);
        }
        if (reply.action == khora::Action::servo_write) {
            const uint32_t lock = save_and_disable_interrupts();
            const bool can_write = control.armed || (bytes[14] == 3 && bytes[16] == 0);
            restore_interrupts(lock);
            if (can_write) servo_send(bytes + 10, khora::read16(bytes + 4));
            else reply.payload[0] = 1;
        }
        if (reply.action == khora::Action::servo_read) reply = servo_read(bytes[10]);
        send_reply(seq, reply);
    }
}
