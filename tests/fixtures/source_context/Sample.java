package com.example;

import java.util.List;

public class Main {
    private int count;

    public Main(int count) {
        this.count = count;
    }

    public int add(int value) {
        return value + count;
    }

    static class Nested {
        void run() {
        }
    }
}

interface Greeter {
    String greet(String name);
}

enum Color {
    RED,
    GREEN
}
