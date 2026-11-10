.text
.globl _start
_start:
    xorq %rbp, %rbp
    andq $-16, %rsp
    callq _init_main
    ud2
