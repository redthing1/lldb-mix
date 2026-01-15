#include <stdio.h>

static const char *kYes = "branch-taken";
static const char *kNo = "branch-not-taken";

static int compute(int value)
{
    if (value & 1)
    {
        return value + 7;
    }
    return value - 3;
}

int main(int argc, char **argv)
{
    volatile int input = argc;
    volatile int out = compute(input);
    const char *msg = (out > 3) ? kYes : kNo;
    if (argv && argv[0])
    {
        printf("%s %d\n", msg, out);
    }
    return out == 0 ? 1 : 0;
}
