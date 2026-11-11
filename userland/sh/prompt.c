#include "shell.h"

void shell_prompt(void)
{
    char path[1024];
    print(1, "commonplace:");
    print(1, get_directory(path, sizeof(path)) < 0 ? "?" : path);
    print(1, " root# ");
}
