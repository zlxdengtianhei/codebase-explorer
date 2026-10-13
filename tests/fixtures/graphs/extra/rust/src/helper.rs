pub fn compute(x: i32) -> i32 {
    let mut acc = 0;
    if x < 0 {
        acc = -x;
    } else {
        let mut i = 0;
        while i < x {
            acc += i;
            i += 1;
        }
    }
    acc
}
