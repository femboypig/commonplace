#include "runtime.h"
#define TEXT_LIMIT 65536
static char text[TEXT_LIMIT];
static size_t used;
static int dirty;

static int load(const char *path,unsigned *mode)
{
    int fd=(int)sys_open(path,OPEN_READ);
    if (fd==-2) return 0;
    if (fd<0) return fd;
    struct system_stat status;
    long error=file_status(fd,&status);
    if (error<0 || (status.mode&0170000)!=0100000) { sys_close(fd); return error<0 ? (int)error : -22; }
    *mode=status.mode&0777;
    for (;;) {
        if (used==sizeof(text)) {
            char extra;
            long size=sys_read(fd,&extra,1);
            if (size==-4) continue;
            error=size<0 ? size : size ? -27 : 0;
            break;
        }
        long size=sys_read(fd,text+used,sizeof(text)-used);
        if (size==-4) continue;
        if (size<=0) { error=size<0 ? size : 0; break; }
        for (long i=0;i<size;++i)
            if (!text[used+(size_t)i]) { sys_close(fd); return -22; }
        used+=(size_t)size;
    }
    sys_close(fd); return (int)error;
}

static void show(void)
{
    unsigned long line=1;
    for (size_t start=0;start<used;) {
        size_t end=start;
        while (end<used && text[end]!='\n') ++end;
        if (end<used) ++end;
        print_number(1,line++); print(1,"\t"); write_all(1,text+start,end-start);
        if (!end || text[end-1]!='\n') print(1,"\n");
        start=end;
    }
}

static void erase_line(long number)
{
    if (number<1) { print(2,"edit: expected a positive line number\n"); return; }
    size_t start=0;
    for (long line=1;line<number && start<used;++line)
        while (start<used && text[start++]!='\n') {}
    if (start==used) { print(2,"edit: no such line\n"); return; }
    size_t end=start;
    while (end<used && text[end++]!='\n') {}
    for (size_t i=end;i<used;++i) text[start+i-end]=text[i];
    used-=end-start; dirty=1;
}

static void append(void)
{
    char line[1024];
    print(1,"append text; a single . ends input\n");
    for (;;) {
        int result=read_line(0,line,sizeof(line));
        if (result==-2) { print(2,"edit: input line too long\n"); continue; }
        if (result<0 || !strcmp(line,".")) return;
        size_t size=strlen(line);
        int separator=used && text[used-1]!='\n';
        if (size+1+(unsigned)separator>sizeof(text)-used) { print(2,"edit: 64 KiB limit reached\n"); return; }
        if (separator) text[used++]='\n';
        memcpy(text+used,line,size); used+=size; text[used++]='\n'; dirty=1;
    }
}

int main(int argc,char **argv)
{
    if (argc!=2) { print(2,"usage: edit file\n"); return 2; }
    unsigned mode=0644;
    int error=load(argv[1],&mode);
    if (error<0) { report_error(argv[1],error); return 1; }
    print(1,"commands: show, append, delete N, write, quit, quit!\n");
    char command[128];
    for (;;) {
        print(1,"edit> ");
        int result=read_line(0,command,sizeof(command));
        if (result==-2) { print(2,"edit: command too long\n"); continue; }
        if (result<0) {
            if (dirty) print(2,"edit: input closed; file left unchanged\n");
            return dirty ? 1 : 0;
        }
        if (!strcmp(command,"show")) show();
        else if (!strcmp(command,"append")) append();
        else if (!strcmp(command,"write")) {
            error=replace_file(argv[1],text,used,mode);
            if (error<0) report_error(argv[1],error);
            else { dirty=0; print(1,"saved\n"); }
        } else if (!strcmp(command,"quit!")) return 0;
        else if (!strcmp(command,"quit")) {
            if (!dirty) return 0;
            print(2,"edit: unsaved changes; use write or quit!\n");
        } else if (strlen(command)>7 && !memcmp(command,"delete ",7))
            erase_line(parse_unsigned(command+7));
        else if (*command) print(2,"edit: unknown command\n");
    }
}
