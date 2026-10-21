#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace khora {
constexpr uint32_t lease_us = 50000;
constexpr uint32_t carrier_hz = 40000;
constexpr size_t channels = 16;
using Wave = std::array<uint32_t, 128>;

inline Wave waveform(const std::array<uint8_t, channels>& phases) {
    Wave result{};
    for (unsigned sample = 0; sample < 256; ++sample) {
        uint16_t bits = 0;
        for (unsigned channel = 0; channel < channels; ++channel)
            if (static_cast<uint8_t>(sample + phases[channel]) < 128)
                bits |= static_cast<uint16_t>(1u << channel);
        result[sample / 2] |= static_cast<uint32_t>(bits) << (16 * (sample % 2));
    }
    return result;
}

inline uint16_t crc16(const uint8_t* data, size_t size) {
    uint16_t crc = 0xffff;
    for (size_t i = 0; i < size; ++i) {
        crc ^= static_cast<uint16_t>(data[i]) << 8;
        for (unsigned bit = 0; bit < 8; ++bit)
            crc = static_cast<uint16_t>((crc & 0x8000) ? (crc << 1) ^ 0x1021 : crc << 1);
    }
    return crc;
}
inline uint32_t read32(const uint8_t* p) {
    return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24;
}
inline uint16_t read16(const uint8_t* p) { return uint16_t(p[0]) | uint16_t(p[1]) << 8; }

class Decoder {
public:
    std::array<uint8_t, 268> bytes{};
    size_t used = 0;
    bool push(uint8_t byte) {
        bytes[used++] = byte;
        while (used >= 2) {
            bool discard = bytes[0] != 'K' || bytes[1] != 'H';
            if (!discard && used < 10) return false;
            size_t length = discard ? 0 : read16(bytes.data() + 4);
            discard = discard || bytes[2] != 2 || length > 256;
            if (!discard && used < length + 12) return false;
            if (!discard && crc16(bytes.data(), length + 10) == read16(bytes.data() + length + 10)) {
                used = 0;
                return true;
            }
            --used;
            std::memmove(bytes.data(), bytes.data() + 1, used);
        }
        return false;
    }
};

enum class Action { none, phases, arm, stop, servo_write, servo_read };
struct Reply {
    uint8_t type = 0x80;
    std::array<uint8_t, 32> payload{};
    uint8_t size = 1;
    Action action = Action::none;
};

inline bool valid_servo_write(const uint8_t* p, size_t n, bool armed) {
    if (n < 8 || p[0] != 255 || p[1] != 255 || p[3] != n - 4) return false;
    uint8_t sum = 0;
    for (size_t i = 2; i < n; ++i) sum = static_cast<uint8_t>(sum + p[i]);
    if (sum != 255) return false;
    if (p[4] == 3 && p[5] == 40 && n == 8 && p[6] == 0)
        return p[2] == 254 || (p[2] >= 1 && p[2] <= 6);
    if (!armed) return false;
    if (p[4] == 3 && p[5] == 40 && n == 8 && p[6] == 1)
        return p[2] >= 1 && p[2] <= 6;
    if (p[2] != 254 || p[4] != 0x83 || p[5] != 42 || p[6] != 6 || n < 15 || (n - 8) % 7) return false;
    uint8_t seen = 0;
    for (size_t i = 7; i + 6 < n - 1; i += 7) {
        const uint8_t id = p[i];
        if (id < 1 || id > 6 || (seen & (1u << id))) return false;
        seen |= static_cast<uint8_t>(1u << id);
        const uint16_t position = read16(p + i + 1), speed = read16(p + i + 5);
        if (position < 500 || position > 3500 || read16(p + i + 3) != 0 || speed < 1 || speed > 800) return false;
    }
    return true;
}

class Control {
public:
    explicit Control(bool outputs_enabled = false) : allowed(outputs_enabled) {}
    bool armed = false, session = false, staged = false;
    uint8_t fault = 0;
    uint32_t last_heartbeat = 0;
    std::array<uint8_t, channels> phases{};

    void stop() { armed = false; session = false; }
    bool tick(uint32_t now, bool interlock) {
        if (armed && (!interlock || uint32_t(now - last_heartbeat) >= lease_us)) {
            fault = interlock ? 1 : 2;
            stop();
            return true;
        }
        return false;
    }

    Reply process(uint8_t type, uint32_t seq, const uint8_t* p, size_t n,
                  uint32_t now, bool interlock, bool arm_button) {
        tick(now, interlock);
        Reply reply;
        if (type == 1 && n == 4) {
            stop();
            session = true; staged = false; sequence = seq;
            std::memcpy(nonce.data(), p, 4);
            reply.type = 0x82; reply.size = 9; reply.action = Action::stop;
            std::memcpy(reply.payload.data(), p, 4);
            reply.payload[4] = 16; reply.payload[5] = 0;
            reply.payload[6] = allowed ? 0x0e : 1;
            reply.payload[7] = fault; reply.payload[8] = 3;
            return reply;
        }
        if (type == 3 && n == 0) { stop(); reply.action = Action::stop; return reply; }
        if (type == 9 && n == 0) {
            reply.type = 0x84; reply.size = 4;
            reply.payload[0] = armed; reply.payload[1] = fault;
            reply.payload[2] = staged; reply.payload[3] = allowed;
            return reply;
        }
        const uint32_t advance = seq - sequence;
        if (!session || fault) { reply.payload[0] = 1; return reply; }
        if (!advance || advance >= 0x80000000u) { reply.payload[0] = 2; return reply; }
        sequence = seq;
        if (type == 2 && n == channels) {
            std::memcpy(phases.data(), p, channels); staged = true; reply.action = Action::phases;
        } else if (type == 4 && n == 4 && std::memcmp(p, nonce.data(), 4) == 0) {
            if (!allowed || !interlock || !arm_button || !staged) reply.payload[0] = 3;
            else { armed = true; last_heartbeat = now; reply.action = Action::arm; }
        } else if (type == 5 && n == 0) {
            last_heartbeat = now;
        } else if (type == 6 && valid_servo_write(p, n, armed)) {
            reply.action = Action::servo_write;
        } else if (type == 8 && n == 1 && p[0] >= 1 && p[0] <= 6) {
            reply.action = Action::servo_read;
        } else reply.payload[0] = 4;
        return reply;
    }
private:
    bool allowed;
    uint32_t sequence = 0;
    std::array<uint8_t, 4> nonce{};
};
}
