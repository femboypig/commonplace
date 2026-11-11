#include "syscall-numbers.h"
#include "shell.h"

int shell_redirect(const struct command *command)
{
    const char *paths[] = {command->input, command->output};
    for (int target = 0; target < 2; ++target) {
        if (!paths[target]) continue;
        int flags = target ? OPEN_WRITE | OPEN_CREATE | (command->append ? OPEN_APPEND : OPEN_TRUNCATE) : OPEN_READ;
        int fd = (int)sys_open(paths[target], flags);
        if (fd < 0) { report_error(paths[target], fd); return -1; }
        long result = sys_dup2(fd, target);
        if (fd != target) sys_close(fd);
        if (result < 0) { report_error("redirection", result); return -1; }
    }
    return 0;
}

static _Noreturn void run_child(struct command *command)
{
    sys_signal(SIGNAL_INT, 0); sys_signal(SIGNAL_QUIT, 0);
    if (shell_redirect(command) < 0) sys_exit(1);
    int ignored = 0;
    int result = shell_builtin(command, &ignored);
    if (result >= 0) sys_exit(result);
    char path[1024];
    const char *program = command->argv[0];
    int has_slash = 0;
    for (const char *p = program; *p; ++p) if (*p == '/') has_slash = 1;
    if (!has_slash) {
        if (path_join(path, sizeof(path), "/bin", program) < 0) {
            print(2, "command path too long\n"); sys_exit(126);
        }
        program = path;
    }
    char *environment[] = {"PATH=/bin", "HOME=/", "TERM=vt100", 0};
    long error = sys_execve(program, command->argv, environment);
    report_error(command->argv[0], error);
    sys_exit(error == -2 ? 127 : 126);
}

static int parent_builtin(struct command *command, int *exit_requested)
{
    int saved[2];
    for (int i = 0; i < 2; ++i) {
        saved[i] = (int)system_call(SYS_dup, i, 0, 0, 0, 0, 0);
        if (saved[i] < 0) {
            if (i) sys_close(saved[0]);
            report_error("dup", saved[i]); return 1;
        }
    }
    int result = shell_redirect(command) < 0 ? 1 : shell_builtin(command, exit_requested);
    for (int i = 0; i < 2; ++i) { sys_dup2(saved[i], i); sys_close(saved[i]); }
    return result;
}

int shell_execute(struct pipeline *pipeline, int *exit_requested)
{
    if (!pipeline->count) return 0;
    if (pipeline->count == 1 && shell_is_builtin(pipeline->commands[0].argv[0]))
        return parent_builtin(&pipeline->commands[0], exit_requested);
    int children[SHELL_COMMANDS], previous = -1;
    unsigned spawned = 0;
    int failed = 0;
    for (unsigned i = 0; i < pipeline->count; ++i) {
        int channel[2] = {-1, -1};
        if (i + 1 < pipeline->count && sys_pipe(channel) < 0) { failed = 1; break; }
        long child = sys_fork();
        if (!child) {
            if (previous >= 0 && sys_dup2(previous, 0) < 0) sys_exit(125);
            if (channel[1] >= 0 && sys_dup2(channel[1], 1) < 0) sys_exit(125);
            if (previous >= 0) sys_close(previous);
            if (channel[0] >= 0) sys_close(channel[0]);
            if (channel[1] >= 0) sys_close(channel[1]);
            run_child(&pipeline->commands[i]);
        }
        if (channel[1] >= 0) sys_close(channel[1]);
        if (previous >= 0) sys_close(previous);
        previous = channel[0];
        if (child < 0) { report_error("fork", child); failed = 1; break; }
        children[spawned++] = (int)child;
    }
    if (previous >= 0) sys_close(previous);
    if (failed) {
        print(2, "pipeline creation failed\n");
        for (unsigned i = 0; i < spawned; ++i)
            system_call(SYS_kill, children[i], SIGNAL_KILL, 1, 0, 0, 0);
    }
    int result = failed ? 125 : 0;
    for (unsigned i = 0; i < spawned; ++i) {
        int status = 0;
        long child;
        do { child = sys_wait(children[i], &status, 0); } while (child == -4);
        if (child < 0) { report_error("wait", child); result = 125; }
        else if (!failed && i + 1 == spawned)
            result = status & 0x7f ? 128 + (status & 0x7f) : (status >> 8) & 255;
    }
    return result;
}
