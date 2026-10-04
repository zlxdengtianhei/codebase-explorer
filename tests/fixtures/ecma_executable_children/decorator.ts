function deco(fn = () => 9) { return fn; }
@deco(() => 8)
class Decorated {
  @deco(() => 7)
  method() { return 1; }
}
