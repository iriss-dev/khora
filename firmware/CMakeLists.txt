cmake_minimum_required(VERSION 3.15)
project(khora_firmware C CXX)
set(CMAKE_CXX_STANDARD 17)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

include_directories(include)

add_library(khora_hal STATIC
    src/khora_phased_array.c
    src/khora_watchdog.c
    src/khora_protocol.c
)

target_compile_options(khora_hal PRIVATE
    -Wall -Wextra -Werror -pedantic -Wno-unused-parameter
)

include(CTest)
if(BUILD_TESTING)
    add_executable(khora_firmware_test ../tests/test_firmware.c)
    target_link_libraries(khora_firmware_test PRIVATE khora_hal)
    add_test(NAME firmware_protocol_and_watchdog COMMAND khora_firmware_test)
    add_executable(khora_pico_control_test ../tests/test_pico.cpp)
    add_test(NAME pico_waveform_and_interlock COMMAND khora_pico_control_test)
endif()
