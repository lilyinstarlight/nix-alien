import argparse
import subprocess
import sys
from importlib.resources import read_text
from pathlib import Path
from string import Template

from .libs import get_unique_packages, find_libs
from .helpers import get_cache_path

NIX_LD_TEMPLATE = Template(read_text(__package__, "nix_ld.template.nix"))


def create_nix_ld_drv(program: str) -> str:
    path = Path(program).expanduser()
    libs = find_libs(path)

    return NIX_LD_TEMPLATE.safe_substitute(
        __name__=path.name,
        __packages__=("\n" + 4 * " ").join(get_unique_packages(libs)),
        __program__=path.absolute(),
    )


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument("program", help="Program to run")
    parser.add_argument(
        "-r",
        "--recreate",
        help="Recreate 'default.nix' file if exists",
        action="store_true",
    )
    parser.add_argument(
        "-d",
        "--destination",
        metavar="PATH",
        help="Path where 'default.nix' file will be created",
    )
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Arguments to be passed to the program",
    )

    parsed_args = parser.parse_args(args=args)
    if parsed_args.destination:
        destination = (
            Path(parsed_args.destination).expanduser().resolve() / "default.nix"
        )
    else:
        destination = get_cache_path(parsed_args.program) / "nix-ld/default.nix"

    if parsed_args.recreate:
        destination.unlink(missing_ok=True)

    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        ld_shell = create_nix_ld_drv(parsed_args.program)
        with open(destination, "w") as f:
            f.write(ld_shell)
        print(f"File '{destination}' created successfuly!")

    build_path = Path(
        subprocess.run(
            ["nix-build", "--no-out-link", destination],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )

    name = Path(parsed_args.program).name
    subprocess.run([build_path / "bin" / name, *parsed_args.args])
