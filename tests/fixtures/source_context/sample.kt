package demo

fun top(a: Int): Int {
    val numbers = listOf(1, 2, 3)
    return a + numbers.size
}

class Greeter(private val name: String) {
    fun greet(): String {
        return "hi " + name
    }
}

object Util {
    fun helper(): Int {
        return 1
    }
}
