#!/usr/bin/env python3
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path.home() / "tools"
CODEQL_DIR = TOOLS_DIR / "codeql"


def run(cmd, check=True):
    print(f"[+] Running: {cmd}")
    return subprocess.run(cmd, shell=True, check=check)


def require_root():
    if os.geteuid() != 0:
        print("[-] Run this with sudo.")
        sys.exit(1)


def install_base_packages():
    run("apt update")
    run(
        "apt install -y "
        "curl wget git unzip tar jq python3-pip pipx apt-transport-https "
        "ca-certificates gnupg lsb-release software-properties-common"
    )
    run("pipx ensurepath", check=False)


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
        "curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh | sh -s -- -b /usr/local/bin"
    )

def install_bearer():
    if shutil.which("bearer"):
        print("[*] Bearer already installed.")
        return

    run(
        "curl -sfL https://raw.githubusercontent.com/Bearer/bearer/main/contrib/install.sh | sh -s -- -b /usr/local/bin"
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
        print(f"[-] Unsupported arch for auto gitleaks install: {arch}")
        return

    run(
        f"""
        set -e
        VERSION=$(curl -s https://api.github.com/repos/gitleaks/gitleaks/releases/latest | jq -r .tag_name)
        TMP=$(mktemp -d)
        cd "$TMP"
        wget -q "https://github.com/gitleaks/gitleaks/releases/download/${{VERSION}}/gitleaks_${{VERSION#v}}_linux_{asset_arch}.tar.gz"
        tar -xzf gitleaks_*.tar.gz
        install -m 755 gitleaks /usr/local/bin/gitleaks
        cd /
        rm -rf "$TMP"
        """
    )


def install_codeql():
    if shutil.which("codeql"):
        print("[*] CodeQL already in PATH.")
        return

    TOOLS_DIR.mkdir(parents=True, exist_ok=True)

    arch = platform.machine()
    if arch not in ["x86_64", "amd64"]:
        print(f"[-] CodeQL auto install currently assumes x64 Linux. Detected: {arch}")
        return

    run(
        f"""
        set -e
        rm -rf "{CODEQL_DIR}"
        TMP=$(mktemp -d)
        cd "$TMP"
        VERSION=$(curl -s https://api.github.com/repos/github/codeql-cli-binaries/releases/latest | jq -r .tag_name)
        wget -q "https://github.com/github/codeql-cli-binaries/releases/download/${{VERSION}}/codeql-linux64.zip"
        unzip -q codeql-linux64.zip -d "{TOOLS_DIR}"
        ln -sf "{CODEQL_DIR}/codeql" /usr/local/bin/codeql
        cd /
        rm -rf "$TMP"
        """
    )


def install_vscode():
    if shutil.which("code"):
        print("[*] VS Code already installed.")
        return

    run(
        """
        set -e
        wget -qO- https://packages.microsoft.com/keys/microsoft.asc \
          | gpg --dearmor > /tmp/packages.microsoft.gpg
        install -o root -g root -m 644 /tmp/packages.microsoft.gpg /etc/apt/keyrings/packages.microsoft.gpg
        echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" \
          > /etc/apt/sources.list.d/vscode.list
        apt update
        apt install -y code
        """
    )


def verify():
    print("\n[+] Installed versions:")
    for cmd in [
        "codeql version",
        "trufflehog --version",
        "bearer --version",
        "semgrep --version",
        "gitleaks version",
        "code --version",
    ]:
        run(cmd, check=False)


def main():
    require_root()
    install_base_packages()
    install_semgrep()
    install_trufflehog()
    install_bearer()
    install_gitleaks()
    install_codeql()
    install_vscode()
    verify()


if __name__ == "__main__":
    main()
