#include "foundation_checks.h"
#include <fenv.h>
#include <math.h>

static void close_to(double actual, double expected, double tolerance)
{
    CHECK(isfinite(actual));
    CHECK(fabs(actual - expected) <= tolerance);
}

void check_native_math(void)
{
    const double pi = 0x1.921fb54442d18p+1;
    close_to(acos(0.5), pi / 3, 1e-15);
    close_to(asin(0.5), pi / 6, 1e-15);
    close_to(atan(1), pi / 4, 1e-15);
    close_to(atan2(1, -1), 3 * pi / 4, 1e-15);
    close_to(sin(pi / 6), 0.5, 1e-15);
    close_to(cos(pi / 3), 0.5, 1e-15);
    close_to(tan(pi / 4), 1, 1e-15);
    close_to(log(2), 0x1.62e42fefa39efp-1, 1e-16);
    close_to(exp(1), 0x1.5bf0a8b145769p+1, 1e-15);
    close_to(pow(2, -10), 0x1p-10, 0);
    close_to(pow(9, 0.5), 3, 1e-15);
    CHECK(pow(-2, 3) == -8);
    CHECK(sqrt(0x1p-1022) == 0x1p-511);
    CHECK(sqrt(0x1p-1074) == 0x1p-537);
    CHECK(signbit(sqrt(-0.0)));
    CHECK(signbit(sin(-0.0)));
    CHECK(signbit(fmod(-4, 2)));
    CHECK(ceil(-1.25) == -1 && floor(-1.25) == -2 && trunc(-1.25) == -1);
    CHECK(!signbit(fabs(-0.0)));
    double integer;
    CHECK(modf(-2.75, &integer) == -0.75 && integer == -2);
    int exponent;
    CHECK(frexpl(0x1p-16400L, &exponent) == 0.5L && exponent == -16399);
    CHECK(powl(2, 10) == 1024);
    CHECK(fegetround() == FE_TONEAREST);
    CHECK(fesetround(FE_DOWNWARD) == 0);
    CHECK(rint(1.75) == 1 && rintl(-1.25L) == -2);
    CHECK(fesetround(FE_TONEAREST) == 0);
    CHECK(feclearexcept(FE_ALL_EXCEPT) == 0);
    CHECK(isnan(sqrt(-1)) && (fetestexcept(FE_INVALID) & FE_INVALID));
    CHECK(feclearexcept(FE_ALL_EXCEPT) == 0);
    CHECK(isinf(log(0)) && signbit(log(0)));
    CHECK(fetestexcept(FE_DIVBYZERO) & FE_DIVBYZERO);
    CHECK(isnan(pow(-2, 0.5)));
    CHECK(pow(1, NAN) == 1 && pow(NAN, 0) == 1);
    CHECK(feclearexcept(FE_ALL_EXCEPT) == 0);
    CHECK(isinf(exp(1000)));
    CHECK(fetestexcept(FE_OVERFLOW) & FE_OVERFLOW);
    CHECK(feclearexcept(FE_ALL_EXCEPT) == 0);
    CHECK(exp(-1000) == 0);
    CHECK(fetestexcept(FE_UNDERFLOW) & FE_UNDERFLOW);
    CHECK(feclearexcept(FE_ALL_EXCEPT) == 0);
    puts("native math: scalar functions, subnormals, long double and IEEE exceptions passed");
}
