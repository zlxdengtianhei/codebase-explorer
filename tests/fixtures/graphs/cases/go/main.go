package main
import (
  "fmt"
  "example.com/fixture/helper"
)
type Runner interface { Run() int }
type Server struct { Value int }
func (s Server) Run() int { return s.Value }
func main() {
  data := []byte("x")
  text := string(data)
  fmt.Print(text)
  server := Server{Value: helper.Helper(1)}
  var runner Runner = server
  runner.Run()
}
