#include <stdint.h>
#include <stdio.h>

static const char *kGreeting = "hello";

static int add_values(int a, int b) {
    return a + b;
}

int main(int argc, char **argv) {
    volatile int total = add_values(argc, 2);
    if (argv && argv[0]) {
        printf("%s %d\n", kGreeting, total);
    }
    return total == 0 ? 1 : 0;
}
