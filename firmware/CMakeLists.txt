cmake_minimum_required(VERSION 3.15)
project(khora_firmware C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

include_directories(include)

add_library(khora_hal STATIC
    src/khora_phased_array.c
    src/khora_watchdog.c
)

target_compile_options(khora_hal PRIVATE
    -Wall -Wextra -Werror -pedantic -Wno-unused-parameter
)
