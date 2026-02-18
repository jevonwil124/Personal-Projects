#!/bin/bash

# Remove old files to ensure a clean build
rm -f *.o myos.bin qemu_log.txt

# 1. Assemble
nasm -felf32 boot.s -o boot.o

# 2. Compile
# -fno-stack-protector and -fno-pie are essential for kernel dev
gcc -m32 -c kernel.c -o kernel.o -std=gnu99 -ffreestanding -O2 -Wall -Wextra \
    -fno-stack-protector -fno-pie -fno-asynchronous-unwind-tables

# 3. Link
# boot.o MUST be first to ensure the Multiboot header is at the start of the binary
ld -m elf_i386 -T linker.ld -o myos.bin boot.o kernel.o

# 4. Verify
if grub-file --is-x86-multiboot myos.bin; then
    echo "Multiboot check: PASSED"
else
    echo "Multiboot check: FAILED"
    exit 1
fi

echo "Launching QEMU with Debug Logging (qemu_log.txt)..."

# 5. Launch with detailed CPU and Interrupt logging
# -d int: Log interrupts/exceptions
# -d cpu_reset: Log why the CPU triple-faulted
# -D qemu_log.txt: Save the output to a file
# -no-reboot: Stop QEMU from looping on crash
qemu-system-i386 -kernel myos.bin \
    -d int,cpu_reset \
    -D qemu_log.txt \
    -no-reboot \
    -no-shutdown \
    -monitor stdio
