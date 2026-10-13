namespace Probe {
    public class Helper {
        public static int Compute(int x) {
            int acc = 0;
            if (x < 0) {
                acc = -x;
            } else {
                for (int i = 0; i < x; i++) {
                    acc += i;
                }
            }
            return acc;
        }
    }
}
