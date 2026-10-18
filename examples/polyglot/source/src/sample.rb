# frozen_string_literal: true

require "set"

def top(a, b = 1)
  inner = ->(x) { x + 1 }
  inner.call(a) + b
end

class Greeter
  def initialize(name)
    @name = name
  end

  def greet
    "hi #{@name}"
  end
end

module Util
  def self.helper
    1
  end
end

result = top(1)
