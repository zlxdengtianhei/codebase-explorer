export default function (cb = () => 17) { return cb(); }
class Item { method(cb = function inner() { return 23; }) { return cb(); } }
