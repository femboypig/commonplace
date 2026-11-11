#include "syscall-numbers.h"
.text
.globl _system_signal_trampoline
_system_signal_trampoline:
    pushq %rbp
    movq %rsp, %rbp
    subq $32, %rsp
    movq %r8, -8(%rbp)
    movq %rsi, -16(%rbp)
    movq %rdi, %r11
    movq %rdx, %rdi
    movq %rcx, %rsi
    movq %r8, %rdx
    callq *%r11
    movq -8(%rbp), %rdi
    movq -16(%rbp), %rsi
    movl $(0x2000000 | SYS_sigreturn), %eax
    syscall
    ud2
