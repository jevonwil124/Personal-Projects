#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* --- 1. DEFINES, STRUCTS & FORWARD DECLARATIONS --- */
#define PAGE_SIZE 4096
#define MAX_MEM_MB 128
#define TOTAL_PAGES (MAX_MEM_MB * 1024 * 1024 / PAGE_SIZE)
#define BITMAP_SIZE (TOTAL_PAGES / 8)
void terminal_write_hex(uint32_t n);
void itoa_any(uint32_t n, char* str);
void process_command();
void reboot();
int strcmp_simple(const char* s1, const char* s2);
extern uint32_t placement_address;
char key_buffer[128];
int key_index = 0;

typedef struct task {
    uint32_t esp;               // Stack pointer for context switching
    uint32_t page_directory;    // Physical address of the page directory (CR3)
    struct task *next;          // Next task in the linked list
    uint32_t sleep_ticks;       // Counter for sleep (decremented by PIT)
} task_t;

typedef struct vfs_node {
    char name[128];
    uint32_t type;     // 0 = file, 1 = directory
    uint32_t size;
    uint32_t inode;    // Unique ID
    uint8_t* buffer;   // Location in memory (for Ramdisk)
    struct vfs_node* next;
} vfs_node_t;

vfs_node_t* fs_root = NULL;

// Forward Declarations to keep the compiler happy
void* kmalloc(size_t size);
void pmm_mark_used(uint32_t page_index);
int pmm_find_free();
uint32_t* create_address_space();
void terminal_writestring(const char* data);
void clear_screen();

// Assembly linkages
extern void switch_to_task(uint32_t *old_esp, uint32_t new_esp, uint32_t new_cr3);
extern void load_idt(uint32_t);
extern void keyboard_handler_asm();
extern void timer_handler_asm();
extern void syscall_handler_asm();
extern void exception_handler_asm();
extern void page_fault_handler_asm();

/* --- 2. GLOBALS --- */
volatile uint32_t timer_ticks = 0;
volatile task_t *current_task = NULL;
volatile task_t *ready_queue = NULL;
task_t main_task;

uint8_t mem_bitmap[BITMAP_SIZE];
uint16_t* terminal_buffer = (uint16_t*) 0xB8000;
static size_t cursor_pos = 0;
char command_buffer[128];
int command_index = 0;
static uint8_t terminal_color = 0x07;
// This must be the same variable your kmalloc uses!
uint32_t placement_address = 0x1000000; // Example starting point (16MB)
uint32_t page_directory[1024] __attribute__((aligned(4096)));
uint32_t first_page_table[1024] __attribute__((aligned(4096)));
uint32_t heap_page_table[1024] __attribute__((aligned(4096)));



/* --- 3. LOW LEVEL I/O --- */
static inline void outb(uint16_t port, uint8_t val) {
    __asm__ volatile ( "outb %0, %1" : : "a"(val), "Nd"(port) );
}
static inline uint8_t inb(uint16_t port) {
    uint8_t ret;
    __asm__ volatile ( "inb %1, %0" : "=a"(ret) : "Nd"(port) );
    return ret;
}

/* --- 4. UTILITIES --- */

void init_timer(uint32_t frequency) {
    // The PIT has an internal clock of 1.193182 MHz
    uint32_t divisor = 1193182 / frequency;

    // Send the command byte (0x36): sets binary counter, Mode 3, LSB then MSB
    outb(0x43, 0x36);

    // Send the divisor in two steps
    uint8_t l = (uint8_t)(divisor & 0xFF);
    uint8_t h = (uint8_t)((divisor >> 8) & 0xFF);
    outb(0x40, l);
    outb(0x40, h);
}

void idle_task_code() {
    while (1) {
        __asm__ volatile("hlt"); // Save power, wait for next tick
    }
}

void sleep(uint32_t ms) {
    // We must use 'volatile' so the compiler doesn't optimize the loop away
    volatile task_t *task = (task_t*)current_task;
    task->sleep_ticks = ms / 10;

    terminal_writestring("Sleeping...\n");

    while(task->sleep_ticks > 0) {
        // IMPORTANT: In Ring 3, you CANNOT use 'hlt'
        // If you don't have syscalls yet, leave this empty to "busy-wait"
        // This prevents the GPF that causes the hang
    }

    terminal_writestring("Done.\n");
}

int strcmp_simple(const char* s1, const char* s2) {
    int i = 0;
    while (s1[i] == s2[i]) { if (s1[i] == '\0') return 0; i++; }
    return s1[i] - s2[i];
}

/* --- 5. PMM & PAGING --- */
void pmm_mark_used(uint32_t page_index) { mem_bitmap[page_index / 8] |= (1 << (page_index % 8)); }
int pmm_find_free() {
    for (uint32_t i = 0; i < BITMAP_SIZE; i++) {
        if (mem_bitmap[i] != 0xFF) {
            for (int j = 0; j < 8; j++) { if (!(mem_bitmap[i] & (1 << j))) return i * 8 + j; }
        }
    }
    return -1;
}

void init_pmm() {
    for (int i = 0; i < BITMAP_SIZE; i++) mem_bitmap[i] = 0;
    for (int i = 0; i < 256; i++) pmm_mark_used(i);
}

uint32_t* create_address_space() {
    int page_idx = pmm_find_free();
    if (page_idx == -1) return NULL;
    pmm_mark_used(page_idx);
    uint32_t* new_pd = (uint32_t*)(page_idx * PAGE_SIZE);
    for(int i = 0; i < 1024; i++) new_pd[i] = 0x00000002;
    new_pd[0] = page_directory[0] | 7; // Ensure User bit is set
    new_pd[4] = page_directory[4] | 7;
    return new_pd;
}

void itoa_any(uint32_t n, char* str) {
    uint32_t tmp = n;
    int i = 0;
    if (n == 0) {
        str[i++] = '0';
    } else {
        char buf[11];
        int j = 0;
        while (tmp > 0) {
            buf[j++] = (tmp % 10) + '0';
            tmp /= 10;
        }
        while (j > 0) {
            str[i++] = buf[--j];
        }
    }
    str[i] = '\0';
}

void terminal_write_dec(uint32_t n) {
    char buf[12];
    itoa_any(n, buf);
    terminal_writestring(buf);
}

void init_paging() {
    // Standard kernel pages: set bit 2 (value 4) to allow User access
    for(int i = 0; i < 1024; i++) page_directory[i] = 0x00000002;

    // Map the first 4MB as User-accessible (7 instead of 3)
    for(unsigned int i = 0; i < 1024; i++) first_page_table[i] = (i * 4096) | 7;
    page_directory[0] = ((uint32_t)first_page_table) | 7;

    // Do the same for the heap if your user mode code uses it
    for(int i = 0; i < 1024; i++) heap_page_table[i] = 0x00000002;
    page_directory[4] = ((uint32_t)heap_page_table) | 7;

    // ... rest of the function (mov cr3, etc)
}

void reboot() {
    uint8_t good = 0x02;
    while (good & 0x02)
        good = inb(0x64);
    outb(0x64, 0xFE);

    // Fallback: If the controller fails, trigger a triple fault
    struct { uint16_t limit; uint32_t base; } __attribute__((packed)) idt_zero = {0, 0};
    __asm__ volatile("lidt %0; int $3" : : "m"(idt_zero));
}

/* --- 6. VIDEO DRIVER --- */

void init_ramdisk() {
    // Manually create a "test.txt" file in memory
    vfs_node_t* test_file = (vfs_node_t*)kmalloc(sizeof(vfs_node_t));

    // Set file details
    for(int i=0; i<128; i++) test_file->name[i] = 0;
    test_file->name[0] = 't'; test_file->name[1] = 'e';
    test_file->name[2] = 's'; test_file->name[3] = 't';

    test_file->type = 0;
    test_file->size = 13;
    test_file->buffer = (uint8_t*)"Hello, World!"; // The "content"
    test_file->next = NULL;

    fs_root = test_file;
}

void update_cursor() {
    uint16_t pos = cursor_pos;
    outb(0x3D4, 0x0F); outb(0x3D5, (uint8_t)(pos & 0xFF));
    outb(0x3D4, 0x0E); outb(0x3D5, (uint8_t)((pos >> 8) & 0xFF));
}

void terminal_writestring(const char* data) {
    for (size_t i = 0; data[i] != '\0'; i++) {
        if (data[i] == '\n') cursor_pos = (cursor_pos / 80 + 1) * 80;
        else terminal_buffer[cursor_pos++] = (uint16_t)data[i] | (uint16_t)terminal_color << 8;
    }
    update_cursor();
}

void list_files() {
    vfs_node_t* current = fs_root;
    if (!current) {
        terminal_writestring("No files found.\n");
        return;
    }

    terminal_writestring("Contents of /:\n");
    while (current) {
        terminal_writestring("  ");
        terminal_writestring(current->name);
        terminal_writestring("  (Size: ");
        char buf[12];
        itoa_any(current->size, buf);
        terminal_writestring(buf);
        terminal_writestring(" bytes)\n");
        current = current->next;
    }
}

void clear_screen() {
    for (int i = 0; i < 80 * 25; i++) terminal_buffer[i] = (uint16_t)' ' | (uint16_t)0x0700;
    cursor_pos = 0; update_cursor();
}

/* --- 7. HEAP --- */
typedef struct heap_chunk { size_t size; bool is_free; struct heap_chunk* next; } heap_chunk_t;
heap_chunk_t* heap_start = (heap_chunk_t*)0x1000000;

void init_heap() {
    heap_start->size = 0x400000;
    heap_start->is_free = true;
    heap_start->next = NULL;
}

void* kmalloc(size_t size) {
    if (size % 4 != 0) size = (size & 0xFFFFFFFC) + 4;
    heap_chunk_t* current = heap_start;
    while (current != NULL) {
        if (current->is_free && current->size >= size) {
            if (current->size > size + sizeof(heap_chunk_t) + 4) {
                heap_chunk_t* new_chunk = (heap_chunk_t*)((uint8_t*)current + sizeof(heap_chunk_t) + size);
                new_chunk->size = current->size - size - sizeof(heap_chunk_t);
                new_chunk->is_free = true;
                new_chunk->next = current->next;
                current->size = size;
                current->next = new_chunk;
            }
            current->is_free = false;
            return (void*)((uint8_t*)current + sizeof(heap_chunk_t));
        }
        current = current->next;
    }
    return NULL;
}

/* --- 8. GDT & TSS --- */
struct tss_entry_struct { uint32_t prev_tss, esp0, ss0, unused[22]; } __attribute__((packed));
typedef struct tss_entry_struct tss_entry_t;
tss_entry_t tss_entry;
uint64_t gdt[6];

void gdt_set_gate(int num, uint32_t base, uint32_t limit, uint8_t access, uint8_t gran) {
    uint8_t* target = (uint8_t*)&gdt[num];
    target[0] = (limit & 0xFF); target[1] = (limit >> 8) & 0xFF;
    target[2] = (base & 0xFF); target[3] = (base >> 8) & 0xFF;
    target[4] = (base >> 16) & 0xFF; target[5] = access;
    target[6] = ((limit >> 16) & 0x0F) | (gran & 0xF0); target[7] = (base >> 24) & 0xFF;
}

void init_gdt() {
    gdt_set_gate(0, 0, 0, 0, 0);
    gdt_set_gate(1, 0, 0xFFFFFFFF, 0x9A, 0xCF); // Kernel Code
    gdt_set_gate(2, 0, 0xFFFFFFFF, 0x92, 0xCF); // Kernel Data
    gdt_set_gate(3, 0, 0xFFFFFFFF, 0xFA, 0xCF); // User Code
    gdt_set_gate(4, 0, 0xFFFFFFFF, 0xF2, 0xCF); // User Data
    uint32_t tss_base = (uint32_t)&tss_entry;
    gdt_set_gate(5, tss_base, tss_base + sizeof(tss_entry), 0x89, 0x40);
    for(int i=0; i<25; i++) ((uint32_t*)&tss_entry)[i] = 0;
    tss_entry.ss0 = 0x10;
    extern uint32_t stack_top;
    tss_entry.esp0 = (uint32_t)&stack_top;
    struct { uint16_t limit; uint32_t base; } __attribute__((packed)) gdt_ptr = { sizeof(gdt) - 1, (uint32_t)&gdt };
    __asm__ volatile("lgdt %0" : : "m"(gdt_ptr));
    __asm__ volatile("ltr %%ax" : : "a"(0x2B));
}

/* --- 9. IDT & SYSCALLS --- */
struct idt_entry { uint16_t base_low, sel; uint8_t always0, flags; uint16_t base_high; } __attribute__((packed));
struct idt_ptr { uint16_t limit; uint32_t base; } __attribute__((packed));
struct idt_entry idt[256];
struct idt_ptr idtp;

void idt_set(uint8_t num, uint32_t base, uint8_t flags) {
    idt[num].base_low = (base & 0xFFFF); idt[num].base_high = (base >> 16) & 0xFFFF;
    idt[num].sel = 0x08; idt[num].always0 = 0; idt[num].flags = flags;
}

void syscall_handler_main(uint32_t eax, uint32_t ebx) {
    if (eax == 1) terminal_writestring((const char*)ebx);
    else if (eax == 2) clear_screen();
}

void init_idt() {
    idtp.limit = (sizeof(struct idt_entry) * 256) - 1;
    idtp.base = (uint32_t)&idt;
    for(int i=0; i<256; i++) idt_set(i, (uint32_t)exception_handler_asm, 0x8E);
    idt_set(14, (uint32_t)page_fault_handler_asm, 0x8E);
    idt_set(32, (uint32_t)timer_handler_asm, 0x8E);
    idt_set(33, (uint32_t)keyboard_handler_asm, 0x8E);
    idt_set(0x80, (uint32_t)syscall_handler_asm, 0xEE);
    outb(0x20,0x11); outb(0xA0,0x11); outb(0x21,0x20); outb(0xA1,0x28);
    outb(0x21,0x04); outb(0xA1,0x02); outb(0x21,0x01); outb(0xA1,0x01);
    outb(0x21,0xFC); outb(0xA1,0xFF);
    load_idt((uint32_t)&idtp);
}

/* --- 10. MULTITASKING CORE --- */
task_t* create_user_process(uint32_t entry_point) {
    task_t* t = (task_t*)kmalloc(sizeof(task_t));
    t->page_directory = (uint32_t)create_address_space();
    t->sleep_ticks = 0;

    int kstack_page = pmm_find_free();
    pmm_mark_used(kstack_page);
    uint32_t* kstack = (uint32_t*)((kstack_page + 1) * PAGE_SIZE);

    // --- Forge stack frame for switching to Ring 3 ---
    // The CPU pops these in reverse order during iret

    *(--kstack) = 0x23;          // SS (User Data Segment + RPL 3)
    *(--kstack) = (uint32_t)kstack; // ESP (User Stack Pointer)
    *(--kstack) = 0x202;         // EFLAGS (IF=1 to keep interrupts on)
    *(--kstack) = 0x1B;          // CS (User Code Segment + RPL 3)
    *(--kstack) = entry_point;   // EIP

    // Registers for your switch_to_task assembly
    *(--kstack) = 0;             // EBP
    *(--kstack) = 0;             // EBX
    *(--kstack) = 0;             // ESI
    *(--kstack) = 0;             // EDI

    t->esp = (uint32_t)kstack;
    t->next = NULL;
    return t;
}

void timer_handler_main() {
    timer_ticks++;
    outb(0x20, 0x20); // EOI

    // 1. Decrement sleep ticks for ALL tasks
    task_t *t = (task_t*)current_task;
    if (t && t->sleep_ticks > 0) t->sleep_ticks--;

    task_t *tmp = (task_t*)ready_queue;
    while (tmp) {
        if (tmp->sleep_ticks > 0) tmp->sleep_ticks--;
        tmp = tmp->next;
    }

    // 2. Preemptive Switch Logic
    // Switch every 100 ticks OR if the current task is sleeping and needs to yield
    if (ready_queue != NULL && (timer_ticks % 100 == 0 || ((task_t*)current_task)->sleep_ticks > 0)) {
        task_t *old_task = (task_t*)current_task;

        // Find the first task in the ready queue that is NOT sleeping
        task_t *prev = NULL;
        task_t *next_task = (task_t*)ready_queue;

        while (next_task != NULL && next_task->sleep_ticks > 0) {
            prev = next_task;
            next_task = next_task->next;
        }

        // If no other task is awake, and the current task is sleeping, we have to idle
        // Otherwise, if we found an awake task, switch to it
        if (next_task != NULL) {
            // Remove next_task from its current position in the ready_queue
            if (prev == NULL) ready_queue = next_task->next;
            else prev->next = next_task->next;

            next_task->next = NULL;

            // Put old_task at the end of the ready_queue
            task_t *tail = (task_t*)ready_queue;
            if (!tail) {
                ready_queue = old_task;
            } else {
                while (tail->next) tail = tail->next;
                tail->next = old_task;
            }
            old_task->next = NULL;

            current_task = next_task;

            __asm__ volatile("cli");
            switch_to_task(&(old_task->esp), next_task->esp, (uint32_t)next_task->page_directory);
            __asm__ volatile("sti");
        }
    }
}
/* --- 11. KEYBOARD & SHELL --- */
void keyboard_handler_main(void) {
    uint8_t scancode = inb(0x60);
    static char kbd_map[] = {
        0,  27, '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', '\b',
        '\t', 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', '\n',
        0, 'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', '\'', '`', 0,
        '\\', 'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/', 0, '*', 0, ' '
    };

    if (!(scancode & 0x80)) {
        char c = kbd_map[scancode];
        if (scancode == 0x1C) { // Enter Key
            process_command();
        } else if (scancode == 0x0E && key_index > 0) { // Backspace
            key_index--;
            cursor_pos--;
            terminal_buffer[cursor_pos] = (uint16_t)' ' | (uint16_t)terminal_color << 8;
            update_cursor();
        } else if (c >= 32 && key_index < 127) {
            key_buffer[key_index++] = c;
            char str[2] = {c, '\0'};
            terminal_writestring(str);
        }
    }
    outb(0x20, 0x20); // End of Interrupt
}
void display_mem_info() {
    uint32_t free_pages = 0;
    uint32_t used_pages = 0;

    // 1. Physical Memory Bitmap Scan
    for (uint32_t i = 0; i < TOTAL_PAGES; i++) {
        if (mem_bitmap[i / 8] & (1 << (i % 8))) {
            used_pages++;
        } else {
            free_pages++;
        }
    }

    terminal_writestring("--- Physical RAM ---\n");
    char buf[12];

    terminal_writestring("  Used: ");
    itoa_any(used_pages * 4, buf);
    terminal_writestring(buf);
    terminal_writestring(" KB\n");

    terminal_writestring("  Free: ");
    itoa_any(free_pages * 4, buf);
    terminal_writestring(buf);
    terminal_writestring(" KB\n");

    // 2. Kernel Heap Analysis
    uint32_t heap_used = 0;
    uint32_t heap_free = 0;
    uint32_t chunk_count = 0;

    // Use your existing heap_start pointer
    heap_chunk_t* current = heap_start;

    while (current != NULL) {
        if (current->is_free) {
            heap_free += current->size;
        } else {
            heap_used += current->size;
        }
        chunk_count++;
        current = current->next;
    }

    terminal_writestring("\n--- Kernel Heap ---\n");

    terminal_writestring("  Used: ");
    itoa_any(heap_used, buf);
    terminal_writestring(buf);
    terminal_writestring(" bytes\n");

    terminal_writestring("  Free: ");
    itoa_any(heap_free, buf);
    terminal_writestring(buf);
    terminal_writestring(" bytes\n");

    terminal_writestring("  Chunks: ");
    itoa_any(chunk_count, buf);
    terminal_writestring(buf);
    terminal_writestring("\n");
}
void vfs_create(char* name, char* content) {
    // 1. Allocate a new VFS node
    vfs_node_t* new_node = (vfs_node_t*)kmalloc(sizeof(vfs_node_t));

    // 2. Set Name
    int i = 0;
    while(name[i] && i < 127) {
        new_node->name[i] = name[i];
        i++;
    }
    new_node->name[i] = '\0';

    // 3. Set Content
    int len = 0;
    while(content[len]) len++;
    new_node->size = len;

    // Allocate space for the content
    new_node->buffer = (uint8_t*)kmalloc(len + 1);
    for(int k = 0; k <= len; k++) {
        new_node->buffer[k] = content[k];
    }

    new_node->type = 0; // Type: File

    // 4. Link into the linked list
    new_node->next = fs_root;
    fs_root = new_node;
}

void vfs_delete(char* name) {
    vfs_node_t* current = fs_root;
    vfs_node_t* prev = NULL;

    while (current != NULL) {
        if (strcmp_simple(current->name, name) == 0) {
            if (prev == NULL) {
                fs_root = current->next; // Removing the first node
            } else {
                prev->next = current->next; // Bypassing the current node
            }
            // Optional: If you had a 'kfree', you would free current->buffer and current here.
            terminal_writestring("File deleted.\n");
            return;
        }
        prev = current;
        current = current->next;
    }
    terminal_writestring("File not found.\n");
}

void process_command() {
    terminal_writestring("\n");
    key_buffer[key_index] = '\0';

    if (key_index > 0) {
        char cmd[32] = {0};
        char arg[64] = {0};
        int i = 0;

        // Split command and first argument
        while (key_buffer[i] != ' ' && key_buffer[i] != '\0' && i < 31) {
            cmd[i] = key_buffer[i];
            i++;
        }
        cmd[i] = '\0';

        if (key_buffer[i] == ' ') {
            int j = 0;
            i++;
            while (key_buffer[i] != '\0' && j < 63) {
                arg[j++] = key_buffer[i++];
            }
            arg[j] = '\0';
        }

        // --- COMMAND LOGIC ---
        if (strcmp_simple(cmd, "ls") == 0) {
            list_files();
        }
        else if (strcmp_simple(cmd, "cat") == 0) {
            if (arg[0] == '\0') {
                terminal_writestring("Usage: cat <filename>\n");
            } else {
                vfs_node_t* current = fs_root;
                int found = 0;
                while (current != NULL) {
                    if (strcmp_simple(current->name, arg) == 0) {
                        terminal_writestring((const char*)current->buffer);
                        terminal_writestring("\n");
                        found = 1;
                        break;
                    }
                    current = current->next;
                }
                if (!found) {
                    terminal_writestring("File not found: ");
                    terminal_writestring(arg);
                    terminal_writestring("\n");
                }
            }
        }
        else if (strcmp_simple(cmd, "sleep") == 0) {
            if (arg[0] == '\0') {
                terminal_writestring("Usage: sleep <ms>\n");
            } else {
                // Convert string argument to integer
                uint32_t ms = 0;
                for(int k = 0; arg[k] != '\0'; k++) {
                    if (arg[k] >= '0' && arg[k] <= '9') {
                        ms = ms * 10 + (arg[k] - '0');
                    }
                }
                terminal_writestring("Sleeping...\n");
                sleep(ms); // Calls the helper using timer_ticks
                terminal_writestring("Done.\n");
            }
        }
        else if (strcmp_simple(cmd, "uptime") == 0) {
            extern volatile uint32_t timer_ticks;
            uint32_t seconds = timer_ticks / 100;
            terminal_writestring("System Uptime: ");
            char buf[12];
            itoa_any(seconds, buf);
            terminal_writestring(buf);
            terminal_writestring(" seconds\n");
        }
        else if (strcmp_simple(cmd, "clear") == 0) {
            clear_screen();
        }
        else if (strcmp_simple(cmd, "mem") == 0) {
            display_mem_info();
        }
        else if (strcmp_simple(cmd, "help") == 0) {
            terminal_writestring("Commands: ls, cat, write, rm, mem, uptime, sleep, clear, reboot\n");
        }
        else if (strcmp_simple(cmd, "rm") == 0) {
            if (arg[0] == '\0') {
                terminal_writestring("Usage: rm <filename>\n");
            } else {
                vfs_delete(arg);
            }
        }
        else if (strcmp_simple(cmd, "write") == 0) {
            if (arg[0] == '\0') {
                terminal_writestring("Usage: write <filename> <content>\n");
            } else {
                char* filename = arg;
                char* content = "";
                int k = 0;
                while(arg[k] != ' ' && arg[k] != '\0') k++;

                if (arg[k] == ' ') {
                    arg[k] = '\0';
                    content = &arg[k+1];
                    vfs_create(filename, content);
                    terminal_writestring("File written.\n");
                } else {
                    vfs_create(filename, "");
                    terminal_writestring("Empty file created.\n");
                }
            }
        }
        else if (strcmp_simple(cmd, "reboot") == 0) {
            terminal_writestring("System rebooting...\n");
            reboot();
        }
        else {
            terminal_writestring("Unknown command: ");
            terminal_writestring(cmd);
            terminal_writestring("\n");
        }
    }

    terminal_writestring("> ");
    key_index = 0;
    for(int i = 0; i < 128; i++) key_buffer[i] = 0;
}
void jump_to_user_mode() {
    terminal_writestring("Transitioning... ");
    __asm__ volatile(
        "cli;"
        "mov $0x23, %ax;"
        "mov %ax, %ds;"
        "mov %ax, %es;"
        "mov %ax, %fs;"
        "mov %ax, %gs;"
        "mov %esp, %eax;"
        "push $0x23;"         // User Data Segment
        "push %eax;"          // Current ESP
        "pushf;"              // Push EFLAGS
        "pop %eax;"           // Get EFLAGS into EAX
        "or $0x200, %eax;"    // Force-enable IF (Interrupt Flag)
        "push %eax;"          // Put EFLAGS back on stack
        "push $0x1B;"         // User Code Segment
        "push $1f;"           // Address of the label below
        "iret;"               // THE JUMP
        "1:"
        "user_loop:"
        "jmp user_loop;"      // Standard User Mode infinite loop
    );
}

/* --- 13. PAGE FAULT HANDLER (C Side) --- */
// Helper to print hex values (add this above the handler)
void terminal_write_hex(uint32_t n) {
    char* hex_chars = "0123456789ABCDEF";
    char buffer[11];
    buffer[0] = '0';
    buffer[1] = 'x';
    for (int i = 0; i < 8; i++) {
        buffer[9 - i] = hex_chars[(n >> (i * 4)) & 0xF];
    }
    buffer[10] = '\0';
    terminal_writestring(buffer);
}

void page_fault_handler_main(uint32_t error_code) {
    uint32_t faulting_address;
    __asm__ volatile("mov %%cr2, %0" : "=r"(faulting_address));

    terminal_writestring("\n--- !!! PAGE FAULT !!! ---");
    terminal_writestring("\nAddress: ");
    terminal_write_hex(faulting_address);

    terminal_writestring("\nReason: ");
    if (!(error_code & 0x01)) terminal_writestring("Page Not Present ");
    if (error_code & 0x02)    terminal_writestring("Write Violation ");
    if (error_code & 0x04)    terminal_writestring("User Mode Access ");
    if (error_code & 0x08)    terminal_writestring("Reserved Bit Set ");
    if (error_code & 0x10)    terminal_writestring("Instruction Fetch ");

    terminal_writestring("\nSystem Halted.");
    while(1) { __asm__ volatile("hlt"); }
}

/* --- 12. MAIN --- */
void kernel_main(void) {
    // 1. Core System Initialization
    clear_screen();
    terminal_writestring("Kernel Online - Privilege Separation Active\n");

    init_gdt();      // Sets up GDT and TSS
    init_pmm();      // Physical Memory Manager
    init_heap();     // Kernel Heap (kmalloc)
    init_paging();   // Virtual Memory & Page Tables
    init_idt();      // Interrupts & Syscalls

    // 2. Initialize VFS and Ramdisk
    // This must happen after the heap is ready so we can kmalloc vfs_nodes
    init_ramdisk();  // Sets up our initial in-memory files
    terminal_writestring("VFS & Ramdisk initialized.\n");

    // 3. Prepare for the Shell
    key_index = 0;   // Reset the keyboard buffer index
    terminal_writestring("System initialized. Type 'help' or 'ls' for commands.\n");
    terminal_writestring("> "); // Display initial prompt

    // 4. Hardware/TSS Final Check
    // Ensure the CPU knows where to land when Ring 3 hits an interrupt
    extern uint32_t stack_top;
    tss_entry.esp0 = (uint32_t)&stack_top;
    tss_entry.ss0 = 0x10;

    // 5. Enable Hardware Interrupts
    // Unmask Timer (0) and Keyboard (1) on the PIC
    outb(0x21, 0xFD);
    __asm__ volatile("sti");

    // 6. The Point of No Return
    terminal_writestring("Dropping to Ring 3...\n");
    jump_to_user_mode(); // Jump to user-level code

    // We should never reach this
    while(1) { __asm__ volatile("hlt"); }
}

