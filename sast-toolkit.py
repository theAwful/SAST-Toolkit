#!/usr/bin/env python3
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
import argparse

TOOLS_DIR = Path.home() / "tools"
CODEQL_DIR = TOOLS_DIR / "codeql"                  # CLI
CODEQL_QUERIES_DIR = TOOLS_DIR / "codeql-queries"  # Query packs
DOTNET_DIR = Path("/opt/dotnet")


def run(cmd, check=True):
    print(f"[+] Running: {cmd}")
    subprocess.run(cmd, shell=True, check=check)


def require_root():
    if os.geteuid() != 0:
        print("[-] Run this script as root (sudo).")
        sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="SAST tooling installer")
    parser.add_argument(
        "--lang",
        choices=["csharp", "python", "javascript", "go"],
        help="Primary language to prepare SAST tooling for",
    )
    return parser.parse_args()


# ---------------- Base Packages ----------------

def install_base_packages():
    run("apt update")
    run(
        "apt install -y "
        "curl wget git unzip tar jq python3-pip pipx "
        "ca-certificates gnupg lsb-release software-properties-common"
    )
    run("pipx ensurepath", check=False)


# ---------------- SAST Tools ----------------

def install_semgrep():
    if shutil.which("semgrep"):
        print("[*] Semgrep already installed.")
        return
    run("pipx install semgrep")


def install_trufflehog():
    if shutil.which("trufflehog"):
        print("[*] TruffleHog already installed.")
        return
    run(
        "curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh "
        "| sh -s -- -b /usr/local/bin"
    )


def install_bearer():
    if shutil.which("bearer"):
        print("[*] Bearer already installed.")
        return
    run(
        "curl -sfL https://raw.githubusercontent.com/Bearer/bearer/main/contrib/install.sh "
        "| sh -s -- -b /usr/local/bin"
    )


def install_gitleaks():
    if shutil.which("gitleaks"):
        print("[*] Gitleaks already installed.")
        return

    arch = platform.machine()
    if arch in ["x86_64", "amd64"]:
        asset_arch = "x64"
    elif arch in ["aarch64", "arm64"]:
        asset_arch = "arm64"
    else:
        print(f"[-] Unsupported arch for gitleaks: {arch}")
        return

    run(
        f"""
        set -e
        VERSION=$(curl -s https://api.github.com/repos/gitleaks/gitleaks/releases/latest | jq -r .tag_name)
        TMP=$(mktemp -d)
        cd "$TMP"
        wget -q https://github.com/gitleaks/gitleaks/releases/download/${{VERSION}}/gitleaks_${{VERSION#v}}_linux_{asset_arch}.tar.gz
        tar -xzf gitleaks_*.tar.gz
        install -m 755 gitleaks /usr/local/bin/gitleaks
        cd /
        rm -rf "$TMP"
        """
    )


# ---------------- CodeQL ----------------

def install_codeql():
    if shutil.which("codeql"):
        print("[*] CodeQL CLI already installed.")
        return

    TOOLS_DIR.mkdir(parents=True, exist_ok=True)

    arch = platform.machine()
    if arch not in ["x86_64", "amd64"]:
        print(f"[-] CodeQL install expects x64 Linux. Detected {arch}")
        sys.exit(1)

    run(
        f"""
        set -e
        TMP=$(mktemp -d)
        cd "$TMP"
        VERSION=$(curl -s https://api.github.com/repos/github/codeql-cli-binaries/releases/latest | jq -r .tag_name)
        wget -q https://github.com/github/codeql-cli-binaries/releases/download/${{VERSION}}/codeql-linux64.zip
        unzip -q codeql-linux64.zip -d "{TOOLS_DIR}"
        ln -sf "{CODEQL_DIR}/codeql" /usr/local/bin/codeql
        cd /
        rm -rf "$TMP"
        """
    )


def install_codeql_queries():
    if CODEQL_QUERIES_DIR.exists():
        print("[*] CodeQL query packs already present.")
        return

    run(
        f"git clone --depth 1 https://github.com/github/codeql.git "
        f"\"{CODEQL_QUERIES_DIR}\""
    )


# ---------------- Language‑Specific ----------------

def install_dotnet_csharp():
    if shutil.which("dotnet"):
        result = subprocess.run(
            "dotnet --list-sdks", shell=True,
            capture_output=True, text=True
        )
        if "8.0." in result.stdout:
            print("[*] .NET 8 SDK already installed.")
            return

    print("[+] Installing .NET 8 SDK (tarball method)")

    DOTNET_DIR.mkdir(parents=True, exist_ok=True)

    run(
        f"""
        set -e
        cd /opt
        wget -q https://dotnetcli.azureedge.net/dotnet/Sdk/8.0.204/dotnet-sdk-8.0.204-linux-x64.tar.gz
        tar -xzf dotnet-sdk-8.0.204-linux-x64.tar.gz -C "{DOTNET_DIR}"
        ln -sf "{DOTNET_DIR}/dotnet" /usr/local/bin/dotnet
        """
    )


def install_language_dependencies(lang):
    if lang == "csharp":
        install_dotnet_csharp()
        install_codeql_queries()

    elif lang == "python":
        install_codeql_queries()

    elif lang == "javascript":
        run("apt install -y nodejs npm", check=False)
        install_codeql_queries()

    elif lang == "go":
        run("apt install -y golang", check=False)
        install_codeql_queries()


# ---------------- Verification ----------------

def verify():
    print("\n[+] Installed versions:")
    cmds = [
        "codeql version",
        "dotnet --info",
        "semgrep --version",
        "gitleaks version",
        "trufflehog --version",
        "bearer --version",
    ]
    for cmd in cmds:
        run(cmd, check=False)


# ---------------- Main ----------------

def main():
    args = parse_args()
    require_root()

    install_base_packages()

    install_semgrep()
    install_trufflehog()
    install_bearer()
    install_gitleaks()

    install_codeql()

    if args.lang:
        install_language_dependencies(args.lang)

    verify()


if __name__ == "__main__":
    main()
