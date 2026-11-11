#include "shell.h"

static int evaluate(const char *line, int *exit_requested, int previous_status)
{
    struct tokens tokens;
    struct pipeline pipeline;
    struct expansion expansion = {previous_status, (unsigned long)sys_getpid()};
    const char *error = shell_tokenize(line, &tokens, &expansion);
    if (!error) error = shell_parse(&tokens, &pipeline);
    if (error) { print(2, "sh: "); print(2, error); print(2, "\n"); return 2; }
    return shell_execute(&pipeline, exit_requested);
}

int main(int argc, char **argv)
{
    int exit_requested = 0, status = 0;
    if (argc == 3 && !strcmp(argv[1], "-c")) return evaluate(argv[2], &exit_requested, 0);
    int interactive = argc == 1;
    if (argc > 2) { print(2, "usage: sh [script] | sh -c command\n"); return 2; }
    if (!interactive) {
        int fd = (int)sys_open(argv[1], OPEN_READ);
        if (fd < 0) { report_error(argv[1], fd); return 1; }
        if (sys_dup2(fd, 0) < 0) { sys_close(fd); return 1; }
        if (fd) sys_close(fd);
    } else {
        sys_signal(SIGNAL_INT, 1); sys_signal(SIGNAL_QUIT, 1); sys_signal(SIGNAL_TSTP, 1);
        print(1, "commonplace shell; type help\n");
    }
    char line[SHELL_LINE];
    while (!exit_requested) {
        if (interactive) shell_prompt();
        int result = read_line(0, line, sizeof(line));
        if (result == -2) { print(2, "sh: input exceeds 1023 bytes\n"); status = 2; continue; }
        if (result < 0) { if (interactive) print(1, "\n"); break; }
        status = evaluate(line, &exit_requested, status);
    }
    return status;
}
