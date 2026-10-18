#include <stdio.h>

struct Point {
    int x;
    int y;
};

/* add two integers */
static int add(int a, int b) {
    return a + b;
}

int main(void) {
    struct Point p = {1, 2};
    printf("%d\n", add(p.x, p.y));
    return 0;
}
