#!/usr/bin/env python3
"""Build Apple's Intel scalar math implementations for the native runtime."""

from darwin_build import OUT, compile_source, archive, prepare_source


def main():
    source = prepare_source("libm") / "Source/Intel"
    names = (
        "nan.c",
        "nanl.c",
        "floor.s",
        "floorl.s",
        "fmaxfminfdim.s",
        "nearbyintl.s",
        "xmm_misc.c",
        "trunc.s",
        "ilogb.s",
        "fenv.c",
        "acos.c",
        "asin.c",
        "atan.c",
        "sincostan.c",
        "xmm_arcsincostan.c",
        "xmm_power.c",
        "xmm_sqrt.c",
        "copysign.s",
        "ceil.s",
        "fmod.s",
        "modf.s",
        "log.s",
        "log2.s",
        "exp.s",
        "exp2.s",
        "expl.s",
        "e_exp.s",
        "e_log.s",
        "e_log10.s",
        "e_atan2.s",
        "e_sqrt.s",
        "frexp.s",
        "scalbn.s",
        "scalbnf.s",
        "scalbnl.s",
        "round.s",
        "roundf.s",
        "roundl.s",
        "e_remquol.s",
        "rint.s",
        "rintl.s",
    )
    objects = [
        compile_source(
            source / name,
            OUT / "obj/math" / (name + ".o"),
            [
                "-ftrapping-math",
                "-I" + str(source),
                *(["-x", "assembler-with-cpp"] if name.endswith(".s") else []),
            ],
        )
        for name in names
    ]
    objects.append(
        compile_source(
            source / "fenv.c",
            OUT / "obj/math/fenv_legacy.o",
            ["-ftrapping-math", "-DBUILDING_FOR_CARBONCORE_LEGACY"],
        )
    )
    archive(OUT / "lib/libsystem_m.a", objects)
    print("Darwin scalar math: " + str(OUT / "lib/libsystem_m.a"))


if __name__ == "__main__":
    main()
