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
