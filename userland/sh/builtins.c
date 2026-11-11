#include "shell.h"

int shell_is_builtin(const char *name)
{
    return !strcmp(name, "cd") || !strcmp(name, "exit") ||
           !strcmp(name, "help") || !strcmp(name, "pid");
}

int shell_builtin(struct command *command, int *exit_requested)
{
    const char *name = command->argv[0];
    if (!strcmp(name, "help")) {
        print(1, "builtins: cd exit help pid\nprograms in /bin: cat chmod cp date echo edit false kill ls mkdir mount mv pid poweroff pwd reboot rm rmdir seq sh sleep sync touch true umount uname wc\n");
        print(1, "syntax: quotes, escapes, $? $$, < > >> and pipelines; RAM root is temporary; files in mounted /data persist\n");
        return 0;
    }
    if (!strcmp(name, "pid")) { print_number(1, sys_getpid()); print(1, "\n"); return 0; }
    if (!strcmp(name, "cd")) {
        if (command->argc > 2) { print(2, "cd: too many arguments\n"); return 2; }
        const char *path = command->argc == 2 ? command->argv[1] : "/";
        long error = sys_chdir(path);
        if (error < 0) { report_error(path, error); return 1; }
        return 0;
    }
    if (!strcmp(name, "exit")) {
        long status = command->argc == 2 ? parse_unsigned(command->argv[1]) : 0;
        if (command->argc > 2 || status < 0 || status > 255) {
            print(2, "exit: expected a status from 0 to 255\n"); return 2;
        }
        *exit_requested = 1;
        return (int)status;
    }
    return -1;
}
