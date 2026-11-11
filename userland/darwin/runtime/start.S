.text
.globl _start
_start:
    xorq %rbp, %rbp
    movq %rsp, %rdi
    andq $-16, %rsp
    callq _commonplace_darwin_start
    ud2
.globl _commonplace_set_tsd
_commonplace_set_tsd:
    movl $0x3000003, %eax
    syscall
    ret
