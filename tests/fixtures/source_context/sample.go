package main

import "fmt"

type Point struct {
	X int
	Y int
}

func (p Point) Sum() int {
	return p.X + p.Y
}

func outer() {
	inner := func(x int) int {
		return x + 1
	}
	fmt.Println(inner(1))
}
