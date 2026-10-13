#include <vector>

namespace demo {

template <typename T>
class Box {
public:
    T value;
    Box(T v) : value(v) {}
    T get() const { return value; }
};

template <typename T>
T maximum(T a, T b) {
    if (a > b) {
        return a;
    }
    return b;
}

}  // namespace demo
