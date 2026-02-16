; 1. MULTIBOOT HEADER
section .multiboot
align 4
    dd 0x1BADB002               ; magic number
    dd 0x00                     ; flags
    dd -(0x1BADB002 + 0x00)     ; checksum

; 2. GLOBAL DECLARATIONS
section .text
global _start
global load_idt
global keyboard_handler_asm
global timer_handler_asm
global syscall_handler_asm      ; <--- Added for Path A
global exception_handler_asm
global page_fault_handler_asm
global switch_to_task
global stack_top

; 3. EXTERNAL C FUNCTIONS
extern kernel_main
extern keyboard_handler_main
extern timer_handler_main
extern syscall_handler_main     ; <--- Added for Path A
extern page_fault_handler_main

; 4. ENTRY POINT
_start:
    cli                         ; Disable interrupts immediately
    mov esp, stack_top          ; Set up the stack

    lgdt [gdt_ptr]              ; Load basic GDT (C will reload a better one later)
    jmp 0x08:.reload_cs         ; Far jump to reload CS
.reload_cs:
    mov ax, 0x10                ; 0x10 is the offset to our data segment
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax

    call kernel_main            ; Call the C kernel

    cli
.hang:
    hlt
    jmp .hang

; 5. INTERRUPT & TASK HANDLERS

; --- New Syscall Wrapper ---
syscall_handler_asm:
    push ebx                    ; Second argument (e.g. string pointer)
    push eax                    ; First argument (Syscall number)
    call syscall_handler_main
    add esp, 8                  ; Clean up stack
    iret

; Example of a proper stack switch
switch_to_task:
    push ebp
    mov ebp, esp
    ; Save old ESP
    mov eax, [ebp+8]  ; first arg: &(old_task->esp)
    mov [eax], esp
    ; Load new ESP
    mov esp, [ebp+12] ; second arg: next_task->esp
    ; Load new Page Directory
    mov eax, [ebp+16] ; third arg: page_directory
    mov cr3, eax
    pop ebp
    ret
    popfd
    pop edi
    pop esi
    pop ebx
    pop ebp
    ret

timer_handler_asm:
    pusha
    call timer_handler_main
    popa
    iret

keyboard_handler_asm:
    pusha
    call keyboard_handler_main
    popa
    iret

page_fault_handler_asm:
    pushad              ; Push all registers
    push ds
    push es
    push fs
    push gs

    ; The error code is already on the stack from the CPU
    ; We just need to call the C function
    call page_fault_handler_main

    pop gs
    pop fs
    pop es
    pop ds
    popad
    add esp, 4          ; Clean up the error code
    iret
load_idt:
    mov edx, [esp + 4]
    lidt [edx]
    ret

exception_handler_asm:
    cli
.loop: hlt
    jmp .loop

; 6. DATA & GDT
section .data
align 4
gdt_start:
    dq 0x0                      ; Null descriptor
    dq 0x00cf9a000000ffff       ; Code segment descriptor (Kernel)
    dq 0x00cf92000000ffff       ; Data segment descriptor (Kernel)
gdt_end:

gdt_ptr:
    dw gdt_end - gdt_start - 1
    dd gdt_start

; 7. STACK & BSS
section .bss
align 16
stack_bottom:
    resb 16384                  ; 16KB Kernel Stack
stack_top:

section .note.GNU-stack noalloc noexec nowrite progbits
