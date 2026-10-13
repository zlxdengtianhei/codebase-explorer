<?php

namespace Demo;

function top(int $a): int
{
    $inner = fn ($x) => $x + 1;
    return $inner($a);
}

class Greeter
{
    private string $name;

    public function __construct(string $name)
    {
        $this->name = $name;
    }

    public function greet(): string
    {
        return "hi " . $this->name;
    }
}

interface Shape
{
    public function area(): float;
}

$result = top(1);
