#include "../firmware/rp2040/control.hpp"
#include <cassert>

int main() {
    std::array<uint8_t, 16> phases{};
    phases[1] = 64; phases[2] = 255;
    auto wave = khora::waveform(phases);
    for (unsigned channel = 0; channel < 16; ++channel) {
        unsigned high = 0;
        for (unsigned sample = 0; sample < 256; ++sample) {
            const uint16_t bits = wave[sample / 2] >> (16 * (sample % 2));
            const bool expected = uint8_t(sample + phases[channel]) < 128;
            assert(bool(bits & (1u << channel)) == expected);
            high += bool(bits & (1u << channel));
        }
        assert(high == 128);
    }
    const uint8_t nonce[] = {1, 2, 3, 4};
    khora::Control control(true);
    assert(control.process(1, 1, nonce, 4, 0, true, true).type == 0x82);
    assert(control.process(4, 2, nonce, 4, 0, true, true).payload[0] == 3);
    assert(control.process(2, 3, phases.data(), 16, 0, true, true).payload[0] == 0);
    assert(control.process(4, 4, nonce, 4, 0xfffffff0, true, true).payload[0] == 0);
    assert(control.armed);
    assert(!control.tick(0xfffffff0 + uint32_t(49999), true));
    assert(control.tick(0xfffffff0 + uint32_t(50000), true));
    assert(!control.armed && control.fault == 1);
    control.process(1, 100, nonce, 4, 60000, true, true);
    assert(control.process(4, 101, nonce, 4, 60000, true, true).payload[0] != 0);
    khora::Control late(true);
    late.process(1, 1, nonce, 4, 0, true, true);
    late.process(2, 2, phases.data(), 16, 0, true, true);
    late.process(4, 3, nonce, 4, 0, true, true);
    assert(late.process(5, 4, nullptr, 0, 50000, true, true).payload[0] != 0);
    assert(late.fault == 1);
    const uint8_t off[] = {255, 255, 254, 4, 3, 40, 0, 210};
    assert(khora::valid_servo_write(off, 8, false));
    khora::Control interlock(true);
    interlock.process(1, 1, nonce, 4, 0, true, true);
    interlock.process(2, 2, phases.data(), 16, 0, true, true);
    interlock.process(4, 3, nonce, 4, 0, true, true);
    assert(interlock.tick(1, false));
    assert(interlock.fault == 2 && !interlock.armed);
    return 0;
}
