<?php
function compute($x) {
    $acc = 0;
    if ($x < 0) {
        $acc = -$x;
    } else {
        for ($i = 0; $i < $x; $i++) {
            $acc += $i;
        }
    }
    return $acc;
}
