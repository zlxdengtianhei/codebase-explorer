namespace N {
int global_value = 1;
static int counter = 2;
constexpr int LIMIT = 8;
using Size = unsigned long;
typedef int Old;
struct Point { static int count; int x; int get() { return x; } };
enum class Color { Red, Blue };
int helper(int x) { return x + LIMIT; }
}
