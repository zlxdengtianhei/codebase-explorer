class Demo {
 static final int LIMIT = 8;
 int value = 2;
 int helper(int x) { return x + LIMIT; }
}
enum Color { RED, BLUE }
record Point(int x, int y) {}
@interface Marker { String value() default "x"; }
interface Action { int get(); }
