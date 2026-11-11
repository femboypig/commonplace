#include "syscall-numbers.h"
.text
.globl _system_call
_system_call:
    movq %rdi, %rax
    orq $0x2000000, %rax
    movq %rsi, %rdi
    movq %rdx, %rsi
    movq %rcx, %rdx
    movq %r8, %r10
    movq %r9, %r8
    movq 8(%rsp), %r9
    syscall
    jnc 1f
    negq %rax
1:  ret

.globl _sys_fork
_sys_fork:
    movl $(0x2000000 | SYS_fork), %eax
    syscall
    jc 2f
    testl %edx, %edx
    jz 1f
    xorl %eax, %eax
1:  ret
2:  negq %rax
    ret

.globl _sys_pipe
_sys_pipe:
    movl $(0x2000000 | SYS_pipe), %eax
    syscall
    jc 2f
    movl %eax, (%rdi)
    movl %edx, 4(%rdi)
    xorl %eax, %eax
    ret
2:  negq %rax
    ret

.globl _sys_gettimeofday
_sys_gettimeofday:
    movl $(0x2000000 | SYS_gettimeofday), %eax
    xorl %esi, %esi
    syscall
    jc 2f
    movq %rax, (%rdi)
    movl %edx, 8(%rdi)
    xorl %eax, %eax
    ret
2:  negq %rax
    ret
