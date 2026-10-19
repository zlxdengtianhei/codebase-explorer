#define LIMIT 8
#define INC(x) ((x)+1)
static int counter = 0;
int global_value = 2;
typedef unsigned long Size;
typedef struct { int x; } Point;
struct Named { int field; };
union Value { int i; float f; };
enum Color { RED, BLUE };
struct Forward;
int prototype(int x);
int helper(int x) { static int local = 1; counter += x; return INC(counter)+local; }
