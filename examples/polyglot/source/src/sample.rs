use std::collections::HashMap;

pub struct Point {
    pub x: i32,
    pub y: i32,
}

impl Point {
    pub fn sum(&self) -> i32 {
        self.x + self.y
    }
}

pub fn top(a: i32) -> i32 {
    let inner = |x: i32| x + 1;
    inner(a)
}

mod util {
    pub fn helper() -> i32 {
        1
    }
}

fn main() {
    println!("{}", top(1));
}
