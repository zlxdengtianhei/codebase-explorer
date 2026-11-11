#include "helper.hpp"
#define LOCAL_ASSERT(x) ((x) ? 0 : helper(1))
int main() {
  bool ok = true;
  demo::v1::missing();
  return LOCAL_ASSERT(ok) + demo::v1::helper(0);
}
