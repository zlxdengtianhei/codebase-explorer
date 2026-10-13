object Helper {
    fun compute(x: Int): Int {
        var acc = 0
        if (x < 0) {
            acc = -x
        } else {
            for (i in 0 until x) {
                acc += i
            }
        }
        return acc
    }
}
