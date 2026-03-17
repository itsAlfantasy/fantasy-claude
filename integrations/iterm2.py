"""iTerm2 profile integration for claude-hooks.

Creates a Dynamic Profile named "Claude" and installs a zshrc wrapper
that switches to it when running the `claude` command.
macOS only.
"""

import json
import platform
import uuid
from pathlib import Path

DYNAMIC_PROFILE_DIR = Path.home() / "Library" / "Application Support" / "iTerm2" / "DynamicProfiles"
DYNAMIC_PROFILE_FILE = DYNAMIC_PROFILE_DIR / "claude-hooks.json"
ITERM2_PLIST = Path.home() / "Library" / "Preferences" / "com.googlecode.iterm2.plist"
ZSHRC = Path.home() / ".zshrc"

MARKER_START = "# >>> claude-hooks iTerm2 integration >>>"
MARKER_END = "# <<< claude-hooks iTerm2 integration <<<"


def is_macos() -> bool:
    return platform.system() == "Darwin"


def check_iterm2_installed() -> bool:
    if not is_macos():
        return False
    return Path("/Applications/iTerm.app").is_dir()


def get_existing_profiles() -> list[dict]:
    """Read profiles from iTerm2 plist. Returns list of {Name, Guid} dicts."""
    if not ITERM2_PLIST.exists():
        return []
    try:
        import plistlib
        with open(ITERM2_PLIST, "rb") as f:
            plist = plistlib.load(f)
        bookmarks = plist.get("New Bookmarks", [])
        return [{"Name": b.get("Name", ""), "Guid": b.get("Guid", "")} for b in bookmarks]
    except Exception:
        return []


def get_default_profile_name() -> str:
    """Return 'Default' if it exists as a profile, otherwise the first profile name."""
    profiles = get_existing_profiles()
    for p in profiles:
        if p["Name"] == "Default":
            return "Default"
    if profiles:
        return profiles[0]["Name"]
    return "Default"


def claude_profile_exists() -> bool:
    """Check if a 'Claude' profile already exists (dynamic or static)."""
    if DYNAMIC_PROFILE_FILE.exists():
        try:
            data = json.loads(DYNAMIC_PROFILE_FILE.read_text())
            for p in data.get("Profiles", []):
                if p.get("Name") == "Claude":
                    return True
        except Exception:
            pass
    for p in get_existing_profiles():
        if p["Name"] == "Claude":
            return True
    return False


def create_dynamic_profile(parent_name: str) -> tuple[bool, str]:
    """Create a Dynamic Profile named 'Claude' inheriting from parent_name."""
    if claude_profile_exists():
        return True, "Claude profile already exists"
    try:
        DYNAMIC_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        profile = {
            "Profiles": [
                {
                    "Name": "Claude",
                    "Guid": f"claude-hooks-{uuid.uuid4()}",
                    "Dynamic Profile Parent Name": parent_name,
                }
            ]
        }
        DYNAMIC_PROFILE_FILE.write_text(json.dumps(profile, indent=2) + "\n")
        return True, "Claude profile created"
    except Exception as e:
        return False, f"Failed to create profile: {e}"


def remove_dynamic_profile() -> tuple[bool, str]:
    """Remove the dynamic profile file."""
    if not DYNAMIC_PROFILE_FILE.exists():
        return True, "No dynamic profile to remove"
    try:
        DYNAMIC_PROFILE_FILE.unlink()
        return True, "Claude profile removed"
    except Exception as e:
        return False, f"Failed to remove profile: {e}"


def _generate_wrapper(fallback_profile: str) -> str:
    return (
        f"{MARKER_START}\n"
        "claude() {\n"
        '  if [ "$TERM_PROGRAM" = "iTerm.app" ]; then\n'
        "    printf '\\033]1337;SetProfile=Claude\\a'\n"
        "  fi\n"
        '  command claude "$@"\n'
        "  local exit_code=$?\n"
        '  if [ "$TERM_PROGRAM" = "iTerm.app" ]; then\n'
        f"    printf '\\033]1337;SetProfile={fallback_profile}\\a'\n"
        "  fi\n"
        "  return $exit_code\n"
        "}\n"
        f"{MARKER_END}"
    )


def is_zshrc_wrapper_installed() -> bool:
    if not ZSHRC.exists():
        return False
    return MARKER_START in ZSHRC.read_text()


def install_zshrc_wrapper(fallback_profile: str) -> tuple[bool, str]:
    """Install or replace the wrapper function in ~/.zshrc."""
    wrapper = _generate_wrapper(fallback_profile)
    try:
        if ZSHRC.exists():
            content = ZSHRC.read_text()
        else:
            content = ""

        if MARKER_START in content:
            # Replace existing block
            start = content.index(MARKER_START)
            end = content.index(MARKER_END) + len(MARKER_END)
            content = content[:start] + wrapper + content[end:]
        else:
            # Append
            if content and not content.endswith("\n"):
                content += "\n"
            content += "\n" + wrapper + "\n"

        ZSHRC.write_text(content)
        return True, "zshrc wrapper installed"
    except Exception as e:
        return False, f"Failed to update zshrc: {e}"


def remove_zshrc_wrapper() -> tuple[bool, str]:
    """Remove the wrapper block from ~/.zshrc."""
    if not ZSHRC.exists():
        return True, "No zshrc to modify"
    try:
        content = ZSHRC.read_text()
        if MARKER_START not in content:
            return True, "No wrapper found in zshrc"
        start = content.index(MARKER_START)
        end = content.index(MARKER_END) + len(MARKER_END)
        # Also remove surrounding blank lines
        before = content[:start].rstrip("\n") + "\n" if content[:start].strip() else ""
        after = content[end:].lstrip("\n")
        content = before + after
        ZSHRC.write_text(content)
        return True, "zshrc wrapper removed"
    except Exception as e:
        return False, f"Failed to update zshrc: {e}"


def full_install(fallback_profile: str | None = None) -> tuple[bool, str]:
    """Run the complete installation: dynamic profile + zshrc wrapper."""
    if not is_macos():
        return False, "iTerm2 integration is macOS only"
    if not check_iterm2_installed():
        return False, "iTerm2 is not installed"

    if fallback_profile is None:
        fallback_profile = get_default_profile_name()

    ok, msg = create_dynamic_profile(fallback_profile)
    if not ok:
        return False, msg

    ok2, msg2 = install_zshrc_wrapper(fallback_profile)
    if not ok2:
        return False, msg2

    return True, "iTerm2 integration installed"


def full_uninstall() -> tuple[bool, str]:
    """Remove dynamic profile and zshrc wrapper."""
    msgs = []
    ok1, msg1 = remove_dynamic_profile()
    msgs.append(msg1)
    ok2, msg2 = remove_zshrc_wrapper()
    msgs.append(msg2)
    return ok1 and ok2, "; ".join(msgs)
