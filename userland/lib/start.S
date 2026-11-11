.text
.globl _start
_start:
    xorq %rbp, %rbp
    movq (%rsp), %rdi
    leaq 8(%rsp), %rsi
    leaq 16(%rsp,%rdi,8), %rdx
    andq $-16, %rsp
    callq _main
    movl %eax, %edi
    callq _sys_exit
    ud2
