#!/bin/bash

# 1. Assemble
nasm -felf32 boot.s -o boot.o

# 2. Compile
gcc -m32 -c kernel.c -o kernel.o -std=gnu99 -ffreestanding -O2 -Wall -Wextra \
    -fno-stack-protector -fno-pie

# 3. Link DIRECTLY with ld
# We put boot.o first so the linker sees the .multiboot section immediately
ld -m elf_i386 -T linker.ld -o myos.bin boot.o kernel.o

# 4. Verify
if grub-file --is-x86-multiboot myos.bin; then
    echo "Multiboot check: PASSED"
else
    echo "Multiboot check: FAILED - The bootloader will not see this kernel!"
    # DEBUG: Check where the header actually is
    objdump -h myos.bin | grep .multiboot
    exit 1
fi

echo "Launching QEMU direct kernel boot..."
qemu-system-i386 -kernel myos.bin
