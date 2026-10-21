#include "control.hpp"
#include <cstdio>

int main() {
    khora::Decoder decoder;
    khora::Control control(false);
    int byte;
    while ((byte = std::getchar()) != EOF) {
        if (!decoder.push(static_cast<uint8_t>(byte))) continue;
        const auto* input = decoder.bytes.data();
        const auto sequence = khora::read32(input + 6);
        auto reply = control.process(input[3], sequence, input + 10, khora::read16(input + 4), 0, false, false);
        uint8_t frame[44] = {'K', 'H', 2, reply.type, reply.size, 0};
        for (unsigned i = 0; i < 4; ++i) frame[6+i] = sequence >> (8*i);
        std::memcpy(frame + 10, reply.payload.data(), reply.size);
        const uint16_t crc = khora::crc16(frame, 10 + reply.size);
        frame[10+reply.size] = crc; frame[11+reply.size] = crc >> 8;
        std::fwrite(frame, 1, 12 + reply.size, stdout);
        std::fflush(stdout);
    }
}
