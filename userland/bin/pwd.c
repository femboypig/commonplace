#include "runtime.h"
int main(void)
{
    char path[1024];
    int error = get_directory(path, sizeof(path));
    if (error < 0) { report_error("pwd", error); return 1; }
    print(1, path); print(1, "\n"); return 0;
}
