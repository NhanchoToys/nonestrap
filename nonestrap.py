from argparse import ArgumentParser
import os
from pathlib import Path
import py_compile
from shutil import SameFileError
import subprocess
import sys
from typing import List
import venv

ADAPTERS_L = (
    "onebot-v11", "ding", "feishu", "telegram", "qqguild", "kaiheila",
    "mirai2", "onebot-v12", "console", "github", "ntchat"
)

BOT_PY_T = """
{EMBED_CD}

import nonebot

nonebot.init()

app = nonebot.get_asgi()
driver = nonebot.get_driver()

{ADAPTER_LOAD}

nonebot.load_from_toml("pyproject.toml")

if __name__ == "__main__":
    nonebot.run(app="__mp_main__:app")
""".strip()

DOTENV_DEV = """
HOST=127.0.0.1
PORT=8080
DEBUG=true
FASTAPI_RELOAD=true
""".strip()

DOTENV_PROD = """
HOST=127.0.0.1
PORT=8080
""".strip()

DOTENV_ALL = """
SUPERUSERS=[]
COMMAND_START=["/", ""]
"""

PYPROJECT = """
[tool.nonebot]
plugins = [{PLUGINS}]
plugin_dirs = ["src/plugins"]
""".strip()


def createvenv(venv_path: Path):
    venv_path.mkdir(exist_ok=True)
    venv.create(venv_path, system_site_packages=False, with_pip=True)


def venvinstall(vp: Path, package: str):
    bindirname = ("Scripts" if sys.platform == "win32" else "bin")
    subprocess.run(
        [(vp / bindirname / "pip").absolute(), "install", "-U", package]
    )


def directinstall(_: Path, package: str):
    subprocess.run(["python", "-m", "pip", "install", "-U", package])


def embedinstall(ep: Path, package: str):
    exc = (ep, )
    if sys.platform != "win32":
        print("[WARNING] Detected you are not using a win32 environment, attempting to use wine.")
        exc = ("wine", ep)
    arg = "-m", "pip", "install", "-U", package
    subprocess.run([*exc, *arg])


def main(target: str, packages: List[str], adapters: List[str], env: str, embed_path: str, _venv: bool):
    tp = Path(target)
    tp.mkdir(exist_ok=True)
    embed = False
    if _venv:
        venv_path = tp / ".venv"
        try:
            createvenv(venv_path)
            print("[NOTICE] Successfully created a new virtual environment.")
        except SameFileError:
            print("[NOTICE] Virtual environment already exists. Delete .venv manually if you don't need it.")
        install_dir = venv_path
        install = venvinstall
    elif embed_path:
        embed = True
        install_dir = Path(embed_path)
        install = embedinstall
    else:
        install_dir = Path()  # stub
        install = directinstall
    print("[NOTICE] Installing nonebot2...")
    install(install_dir, "nonebot2")
    if adapters:
        print("[NOTICE] Installing adapters for nonebot2...")
        adapter_l = []
        for adp in adapters:
            if adp.startswith("onebot-"):
                _adp = adp.replace("-", ".")
                _aim = adp.replace("-", "_")
                _ain = "onebot"
            else:
                _adp = _ain = _aim = adp
            install(install_dir, f"nonebot-adapter-{_ain}")
            adapter_l.append(
                f"from nonebot.adapters.{_adp} import Adapter as {_aim}"
            )
            adapter_l.append(f"driver.register_adapter({_aim})")
        adapter_t = "\n".join(adapter_l)
        print("[NOTICE] Creating entry file for the bot...")
        botpy = tp / "bot.py"
        with open(botpy, "w") as f:
            f.write(BOT_PY_T.format(EMBED_CD=f"__import__('os').chdir({str(tp)})" if embed else "", ADAPTER_LOAD=adapter_t))
        py_compile.compile(str(botpy), cfile=str(tp / "bot.pyc"))
        os.remove(botpy)
    print("[NOTICE] Generating misc files...")
    with open(tp / ".env", "w") as f:
        f.write(DOTENV_DEV if env == "dev" else DOTENV_PROD)
        f.write(DOTENV_ALL)
    for pkg in packages:
        install(install_dir, pkg)
    with open(tp / "pyproject.toml", "w") as f:
        f.write(
            PYPROJECT.format(
                PLUGINS=", ".join(
                    f'"{p.replace("-", "_")}"'
                    for p in packages
                    if p.startswith("nonebot-plugin-")
                )
            )
        )
    os.makedirs(tp / "src" / "plugins", exist_ok=True)
    print("[NOTICE] Done!")


def _entry():
    ap = ArgumentParser("nonestrap", description="NoneBot2 bootstrap file generating tool")
    ap.add_argument("-a", "--adapter", action="append", choices=ADAPTERS_L, help="specify adapter to register")
    ap.add_argument("-e", "--dotenv", choices=("dev", "prod"), default="dev", help="choose .env style")
    ap.add_argument("-E", "--embed", default="", help="use embedded python instead of system python, works with -V. path to python is required")
    ap.add_argument("-V", "--no-venv", "--in-venv", action="store_false", help="whether not to use venv")
    ap.add_argument("target", help="specify bootstrap target directory")
    ap.add_argument("package", nargs="*", help="install specified packages")
    args = ap.parse_args()
    # print(args)
    main(args.target, args.package, args.adapter, args.dotenv, args.embed, args.no_venv)


if __name__ == "__main__":
    _entry()
