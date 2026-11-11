require_relative "helper"
class Builder
  def map(value)
    value
  end
end
def run(values)
  values.map(&:size)
  Helper.compute(1)
end
