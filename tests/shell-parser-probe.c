#include "shell.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static struct tokens tokens;
static struct pipeline pipeline;
static const struct expansion expansion = {7,12345};
static const char *parse(const char *line)
{
    const char *error=shell_tokenize(line,&tokens,&expansion);
    return error ? error : shell_parse(&tokens,&pipeline);
}

int main(void)
{
    assert(!parse("echo \"two words\" '' x\\ y '$?' \\$? $? $$ # comment"));
    assert(pipeline.count==1 && pipeline.commands[0].argc==8);
    const char *expected[]={"echo","two words","","x y","$?","$?","7","12345"};
    for (unsigned i=0;i<8;++i) assert(!strcmp(pipeline.commands[0].argv[i],expected[i]));
    assert(!parse("cat<in | cat | wc -c>>out"));
    assert(pipeline.count==3 && !strcmp(pipeline.commands[0].input,"in"));
    assert(pipeline.commands[2].append && !strcmp(pipeline.commands[2].output,"out"));
    assert(!parse("echo a\\;b '|' \"<\""));
    assert(!strcmp(pipeline.commands[0].argv[1],"a;b"));
    const char *invalid[]={"|cat","cat|","cat||cat","echo >","< in","echo >a >b","echo 'x","echo \\","echo a;b","echo &"};
    for (unsigned i=0;i<sizeof(invalid)/sizeof(invalid[0]);++i) assert(parse(invalid[i]));
    char line[1024];
    memset(line,'x',sizeof(line)-1); line[sizeof(line)-1]=0;
    assert(!parse(line));
    unsigned random=1234567;
    const char alphabet[]="abc \t|<>\\\"'$?;&0123#";
    for (unsigned run=0;run<20000;++run) {
        random=random*1664525u+1013904223u;
        unsigned size=random%sizeof(line);
        for (unsigned i=0;i<size;++i) { random=random*1664525u+1013904223u; line[i]=alphabet[random%(sizeof(alphabet)-1)]; }
        line[size]=0;
        if (!parse(line)) {
            assert(pipeline.count<=SHELL_COMMANDS);
            for (unsigned i=0;i<pipeline.count;++i) {
                assert(pipeline.commands[i].argc>0 && pipeline.commands[i].argc<=SHELL_ARGS);
                assert(!pipeline.commands[i].argv[pipeline.commands[i].argc]);
            }
        }
    }
    return 0;
}
