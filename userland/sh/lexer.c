#include "shell.h"

static int space(char c) { return c==' ' || c=='\t' || c=='\r' || c=='\n'; }
static int operation(char c) { return c=='|' || c=='<' || c=='>'; }

const char *shell_tokenize(const char *input, struct tokens *tokens, const struct expansion *expansion)
{
    tokens->count = 0;
    size_t used = 0;
    while (*input) {
        if (space(*input)) { ++input; continue; }
        if (*input == '#') break;
        if (tokens->count == SHELL_WORDS) return "too many tokens";
        struct token *token = &tokens->values[tokens->count++];
        token->text = 0;
        if (operation(*input)) {
            token->type = *input=='|' ? PIPE : *input=='<' ? INPUT : OUTPUT;
            ++input;
            if (token->type == OUTPUT && *input == '>') { token->type = APPEND; ++input; }
            continue;
        }
        token->type = WORD;
        token->text = tokens->storage + used;
        char quote = 0;
        while (*input && (quote || (!space(*input) && !operation(*input)))) {
            char byte = *input++;
            if (!quote && (byte=='\'' || byte=='"')) { quote = byte; continue; }
            if (quote && byte == quote) { quote = 0; continue; }
            int escaped = 0;
            if (byte=='\\' && quote!='\'') {
                if (!*input) return "unfinished escape";
                byte = *input++;
                escaped = 1;
            }
            if (!escaped && byte=='$' && quote!='\'' && (*input=='?' || *input=='$')) {
                unsigned long value = *input++ == '?' ? (unsigned long)expansion->status : expansion->pid;
                char digits[32]; unsigned count = 0;
                do { digits[count++] = '0' + value % 10; value /= 10; } while (value);
                if (used + count + 1 >= sizeof(tokens->storage)) return "expanded input too long";
                while (count) tokens->storage[used++] = digits[--count];
                continue;
            }
            if (!quote && !escaped && (byte=='&' || byte==';')) return "command lists and background jobs are not supported";
            if (used + 1 >= sizeof(tokens->storage)) return "expanded input too long";
            tokens->storage[used++] = byte;
        }
        if (quote) return "unclosed quote";
        if (used == sizeof(tokens->storage)) return "expanded input too long";
        tokens->storage[used++] = 0;
    }
    return 0;
}
