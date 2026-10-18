import Foundation

struct Point {
    var x: Int
    var y: Int
}

func top(_ a: Int) -> Int {
    let inner = { (x: Int) in x + 1 }
    return inner(a)
}

class Greeter {
    let name: String

    init(name: String) {
        self.name = name
    }

    func greet() -> String {
        return "hi " + name
    }
}

protocol Shape {
    func area() -> Double
}
