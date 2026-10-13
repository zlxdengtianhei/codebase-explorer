def compute(x)
  acc = 0
  if x < 0
    acc = -x
  else
    i = 0
    while i < x
      acc += i
      i += 1
    end
  end
  acc
end
