.section .multiboot,"a"
.balign 4
.long 0x1badb002
.long 3
.long -(0x1badb002 + 3)

.section .text
.code32
.global _start
.type _start,@function
_start:
    cli
    cld
    movl $stack_top, %esp
    subl $8, %esp
    pushl %ebx
    pushl %eax
    call loader_main
1:  cli
    hlt
    jmp 1b
.size _start, .-_start

.global enter_kernel
.type enter_kernel,@function
enter_kernel:
    movl 4(%esp), %edx
    movl 8(%esp), %eax
    cli
    cld
    jmp *%edx
.size enter_kernel, .-enter_kernel

.section .bss
.balign 16
stack_bottom:
.skip 65536
stack_top:

.section .note.GNU-stack,"",@progbits
