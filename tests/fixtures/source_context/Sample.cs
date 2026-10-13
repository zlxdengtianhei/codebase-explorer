using System;

namespace Demo
{
    public class Greeter
    {
        private string name;

        public Greeter(string name)
        {
            this.name = name;
        }

        public string Greet()
        {
            return "hi " + name;
        }

        public int Add(int a) => a + 1;
    }

    public interface IShape
    {
        double Area();
    }

    public static class Program
    {
        public static void Main()
        {
            Console.WriteLine(new Greeter("x").Greet());
        }
    }
}
