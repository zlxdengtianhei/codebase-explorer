#include "helper.h"
#define FALSE 0
#define BUFFER_AT_OFFSET(p) helper((p), 0)
int main(void) {
  char *p = 0;
  if (FALSE) return 1;
  return BUFFER_AT_OFFSET(p) + helper(p, 1);
}
