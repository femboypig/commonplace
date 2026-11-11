#include "shell.h"

const char *shell_parse(const struct tokens *tokens, struct pipeline *pipeline)
{
    memset(pipeline, 0, sizeof(*pipeline));
    if (!tokens->count) return 0;
    pipeline->count = 1;
    struct command *command = &pipeline->commands[0];
    for (unsigned i = 0; i < tokens->count; ++i) {
        const struct token *token = &tokens->values[i];
        if (token->type == WORD) {
            if (command->argc == SHELL_ARGS) return "too many arguments";
            command->argv[command->argc++] = token->text;
        } else if (token->type == PIPE) {
            if (!command->argc) return "missing command before pipe";
            if (pipeline->count == SHELL_COMMANDS) return "too many pipeline stages";
            command = &pipeline->commands[pipeline->count++];
        } else {
            if (++i == tokens->count || tokens->values[i].type != WORD)
                return "missing redirection path";
            if (token->type == INPUT) {
                if (command->input) return "duplicate input redirection";
                command->input = tokens->values[i].text;
            } else {
                if (command->output) return "duplicate output redirection";
                command->output = tokens->values[i].text;
                command->append = token->type == APPEND;
            }
        }
    }
    return command->argc ? 0 : "missing command";
}
