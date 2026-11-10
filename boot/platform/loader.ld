ENTRY(_start)
SECTIONS
{
    . = 0x10000000;
    loader_start = .;
    .multiboot : { KEEP(*(.multiboot)) }
    .text ALIGN(16) : { *(.text .text.*) }
    .rodata ALIGN(16) : { *(.rodata .rodata.*) }
    .data ALIGN(16) : { *(.data .data.*) }
    .bss ALIGN(16) : { *(.bss .bss.*) *(COMMON) }
    . = ALIGN(4096);
    loader_end = .;
    /DISCARD/ : { *(.comment) *(.eh_frame*) *(.note*) }
}
