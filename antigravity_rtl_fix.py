# -*- coding: utf-8 -*-
"""
Antigravity RTL Fix
===================
Injects RTL/BiDi CSS into the Antigravity *Agent Manager* (chat) window ONLY.

How it works (verified against Antigravity desktop 2.30.0 / Electron 44.9.1):
  * The chat UI is NOT shipped as CSS/HTML files. It is served at runtime by
    resources/bin/language_server.exe over https://127.0.0.1:<port>/.
    Therefore there is no chat CSS file on disk that can be edited.
  * The window that shows that UI is created by `createWindow()` in
    resources/app.asar -> dist/utils.js (variable `hubContents`).
  * This script adds a small, marked block right after
    `hubContents.on('will-redirect', guardExternalNavigation);`
    that calls `hubContents.insertCSS(css, { cssOrigin: 'user' })` on every
    `dom-ready`. The app itself already uses insertCSS the same way.
  * Scope: only the main Hub document. The in-app <webview> browser, iframes,
    and the separate "Antigravity IDE" program (different folder/exe) are NOT
    touched.

Safety:
  * Original app.asar is copied to app.asar.backup before any change.
  * New archive is written to a temp file, fully re-verified (every file's
    SHA256 checked against the archive's own integrity records), then swapped.
  * Idempotent: if the marker already exists, nothing is injected again.
  * Restore puts the backup back (only if it matches the current app version).

Usage:
  python antigravity_rtl_fix.py              -> interactive menu
  python antigravity_rtl_fix.py --diagnose   -> read-only check
  python antigravity_rtl_fix.py --apply
  python antigravity_rtl_fix.py --restore
  Optional: --install-dir "C:\\path\\to\\antigravity"
"""

import argparse
import datetime
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Optional CSS selector of the chat container. Empty = whole Agent Manager
# window (which is the chat app itself; the IDE is a different program).
# Example if you identify the container class later: CHAT_SCOPE = ".my-chat"
CHAT_SCOPE = ""

MARKER_START = "// >>> ANTIGRAVITY-RTL-FIX START >>>"
MARKER_END = "// <<< ANTIGRAVITY-RTL-FIX END <<<"
ANCHOR = "    hubContents.on('will-redirect', guardExternalNavigation);"
TARGET_FILE = "dist/utils.js"
BACKUP_SUFFIX = ".backup"
META_SUFFIX = ".rtlfix.json"
TMP_SUFFIX = ".rtlfix.tmp"
EXE_NAME = "Antigravity.exe"
BLOCK_SIZE = 4 * 1024 * 1024  # asar integrity block size


def build_css(scope: str) -> str:
    s = (scope.strip() + " ") if scope.strip() else ""
    msg_sel = "[data-testid='user-message-content'], [data-testid='user-message-bubble'], .agy-user-bubble, [data-testid='transcript-line-text'], textarea, input[type='text'], [contenteditable='true']"
    return (
        f"{s}:is(p, h1, h2, h3, h4, h5, h6, {msg_sel}):dir(rtl) {{"
        " direction: rtl !important; text-align: right !important; }"
        f"{s}:is(p, h1, h2, h3, h4, h5, h6, {msg_sel}):dir(ltr) {{"
        " direction: ltr !important; text-align: left !important; }"
        f"{s}:is(p, h1, h2, h3, h4, h5, h6):not([dir]):not(li, li *, pre *, code *, .monaco-editor *) {{"
        " unicode-bidi: plaintext !important; text-align: start !important; }"
        f"{s}:is(ul, ol):dir(rtl), {s}:is(ul, ol):dir(rtl) li, {s}:is(ul, ol):dir(rtl) p {{"
        " direction: rtl !important; text-align: right !important; unicode-bidi: normal !important; }"
        f"{s}:is(ul, ol):dir(ltr), {s}:is(ul, ol):dir(ltr) li, {s}:is(ul, ol):dir(ltr) p {{"
        " direction: ltr !important; text-align: left !important; unicode-bidi: normal !important; }"
        f"{s}:is(pre, code), {s}:is(pre, code) * {{"
        " direction: ltr !important; text-align: left !important; }"
        f"{s}code {{ unicode-bidi: isolate !important; }}"
    )


def build_js_block(css: str, nl: str) -> str:
    client_js = (
        "(() => {"
        " if (window.__antigravityRtlFixInstalled) return;"
        " window.__antigravityRtlFixInstalled = true;"
        " const arRegex = /[\\u0600-\\u06FF\\u0750-\\u077F\\u08A0-\\u08FF\\uFB50-\\uFDFF\\uFE70-\\uFEFF]/;"
        " let timer = null;"
        " const sel = 'p, h1, h2, h3, h4, h5, h6, ol, ul, [data-testid=\"user-message-content\"], [data-testid=\"user-message-bubble\"], .agy-user-bubble, [data-testid=\"transcript-line-text\"], textarea, [contenteditable=\"true\"]';"
        " const scan = () => {"
        "  try {"
        "   document.querySelectorAll(sel).forEach(el => {"
        "    if (el.closest('pre, code, .monaco-editor')) return;"
        "    if (el.matches('ol, ul') && el.parentElement?.closest('ol, ul')) return;"
        "    if (el.matches('p') && el.closest('li')) return;"
        "    const text = el.value || el.textContent || '';"
        "    const target = arRegex.test(text) ? 'rtl' : 'ltr';"
        "    if (el.getAttribute('dir') !== target) el.setAttribute('dir', target);"
        "   });"
        "  } catch (_) {}"
        " };"
        " scan();"
        " const obs = new MutationObserver(() => {"
        "  if (timer) return;"
        "  timer = setTimeout(() => { timer = null; scan(); }, 60);"
        " });"
        " const target = document.body || document.documentElement;"
        " if (target) obs.observe(target, { childList: true, subtree: true, characterData: true });"
        " document.addEventListener('input', e => {"
        "  const t = e.target;"
        "  if (t && (t.matches?.('textarea, input, [contenteditable=\"true\"]') || t.closest?.('.surface-composer'))) {"
        "   const text = t.value || t.textContent || '';"
        "   const dir = arRegex.test(text) ? 'rtl' : 'ltr';"
        "   if (t.getAttribute('dir') !== dir) t.setAttribute('dir', dir);"
        "  }"
        " }, true);"
        "})();"
    )
    lines = [
        "    " + MARKER_START,
        "    try {",
        "        const __rtlFixCss = " + json.dumps(css) + ";",
        "        const __rtlFixJs = " + json.dumps(client_js) + ";",
        "        const __rtlFixInject = () => {",
        "            if (win.isDestroyed?.() || hubContents.isDestroyed?.()) {",
        "                return;",
        "            }",
        "            void Promise.resolve(hubContents.insertCSS(__rtlFixCss, { cssOrigin: 'user' })).catch(() => undefined);",
        "            void Promise.resolve(hubContents.executeJavaScript(__rtlFixJs)).catch(() => undefined);",
        "        };",
        "        hubContents.on('dom-ready', __rtlFixInject);",
        "        win.on('closed', () => {",
        "            hubContents.off?.('dom-ready', __rtlFixInject);",
        "        });",
        "    }",
        "    catch (_rtlFixErr) {",
        "        // Never break window creation because of the RTL fix.",
        "    }",
        "    " + MARKER_END,
    ]
    return nl.join(lines)


# ---------------------------------------------------------------------------
# ASAR helpers
# ---------------------------------------------------------------------------

class Asar:
    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            raw = f.read()
        a, b, c, d = struct.unpack("<IIII", raw[:16])
        if a != 4 or c + 4 != b or d > c:
            raise ValueError("Unrecognized app.asar header layout.")
        self.header = json.loads(raw[16:16 + d].decode("utf-8"))
        self.data = raw[8 + b:]

    def entry(self, rel):
        node = self.header
        for part in rel.split("/"):
            node = node["files"][part]
        return node

    def read(self, rel):
        e = self.entry(rel)
        if e.get("unpacked"):
            raise ValueError(f"{rel} is unpacked; unexpected layout.")
        off = int(e["offset"])
        return self.data[off:off + e["size"]]

    def iter_files(self, node=None, prefix=""):
        node = node or self.header
        for name, child in node.get("files", {}).items():
            p = f"{prefix}/{name}" if prefix else name
            if "files" in child:
                yield from self.iter_files(child, p)
            else:
                yield p, child


def integrity_for(data: bytes) -> dict:
    blocks = [hashlib.sha256(data[i:i + BLOCK_SIZE]).hexdigest()
              for i in range(0, max(len(data), 1), BLOCK_SIZE)]
    return {"algorithm": "SHA256", "hash": hashlib.sha256(data).hexdigest(),
            "blockSize": BLOCK_SIZE, "blocks": blocks}


def serialize_asar(header: dict, data: bytes) -> bytes:
    js = json.dumps(header, separators=(",", ":")).encode("utf-8")
    d = len(js)
    padded = (d + 3) // 4 * 4
    c = padded + 4
    b = c + 4
    return struct.pack("<IIII", 4, b, c, d) + js + b"\0" * (padded - d) + data


def verify_archive(path) -> None:
    """Re-parse archive and check every packed file against its integrity hash."""
    arc = Asar(path)
    checked = 0
    for rel, e in arc.iter_files():
        if e.get("unpacked") or "integrity" not in e or "link" in e:
            continue
        if hashlib.sha256(arc.read(rel)).hexdigest() != e["integrity"]["hash"]:
            raise ValueError(f"Integrity mismatch in {rel}")
        checked += 1
    if checked == 0:
        raise ValueError("No files verified.")


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def is_antigravity_app(folder) -> bool:
    """True only for the Antigravity desktop (Agent Manager), never the IDE."""
    asar = os.path.join(folder, "resources", "app.asar")
    if not (os.path.isfile(os.path.join(folder, EXE_NAME)) and os.path.isfile(asar)):
        return False
    try:
        pkg = json.loads(Asar(asar).read("package.json").decode("utf-8"))
    except Exception:
        return False
    return pkg.get("name") == "antigravity" and pkg.get("main") == "dist/main.js"


def find_install_dirs():
    roots = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
        os.environ.get("ProgramFiles", ""),
        os.environ.get("ProgramFiles(x86)", ""),
        os.environ.get("LOCALAPPDATA", ""),
    ]
    found = []
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for name in os.listdir(root):
            if "antigravity" not in name.lower() or "ide" in name.lower().split():
                continue
            full = os.path.join(root, name)
            if os.path.isdir(full) and is_antigravity_app(full) and full not in found:
                found.append(full)
    return found


def is_running() -> bool:
    try:
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {EXE_NAME}", "/NH"],
                             capture_output=True, text=True, timeout=15).stdout
    except Exception:
        return False
    return EXE_NAME.lower() in out.lower()


def kill_running() -> bool:
    try:
        subprocess.run(["taskkill", "/F", "/IM", EXE_NAME, "/T"],
                       capture_output=True, text=True, timeout=10)
        import time
        time.sleep(1)
        return not is_running()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def paths(install_dir):
    asar = os.path.join(install_dir, "resources", "app.asar")
    return asar, asar + BACKUP_SUFFIX, asar + META_SUFFIX, asar + TMP_SUFFIX


def app_version(asar_path):
    return json.loads(Asar(asar_path).read("package.json").decode("utf-8")).get("version")


def diagnose(install_dir) -> dict:
    asar, backup, meta, _ = paths(install_dir)
    arc = Asar(asar)
    src = arc.read(TARGET_FILE).decode("utf-8")
    info = {
        "install_dir": install_dir,
        "app_version": app_version(asar),
        "patched": MARKER_START in src,
        "anchor_count": src.count(ANCHOR),
        "backup_exists": os.path.isfile(backup),
        "running": is_running(),
    }
    print("\n=== Diagnostic ===")
    print(f"Install folder : {install_dir}")
    print(f"App version    : {info['app_version']}")
    print(f"Target         : resources\\app.asar -> {TARGET_FILE} (Agent Manager window only)")
    print(f"Already patched: {'YES' if info['patched'] else 'no'}")
    print(f"Anchor found   : {info['anchor_count']} time(s) (must be 1 to patch)")
    print(f"Backup exists  : {'yes' if info['backup_exists'] else 'no'}")
    print(f"App running    : {'YES - close it first' if info['running'] else 'no'}")
    print("IDE (Antigravity IDE) : not touched (separate program).")
    return info


def apply_patch(install_dir) -> bool:
    asar, backup, meta, tmp = paths(install_dir)
    info = diagnose(install_dir)
    if info["running"]:
        print("\n[!] Antigravity is currently running in the background.")
        choice = input("Do you want to close it automatically to apply the fix? (y/n): ").strip().lower()
        if choice in ["y", "yes"]:
            if kill_running():
                print("[OK] Antigravity closed successfully.")
                info = diagnose(install_dir)
            else:
                print("[STOP] Failed to close Antigravity automatically. Please close it manually and retry.")
                return False
        else:
            print("[STOP] Antigravity must be closed to apply changes.")
            return False
    arc = Asar(asar)
    raw = arc.read(TARGET_FILE)
    src = raw.decode("utf-8")
    nl = "\r\n" if "\r\n" in src else "\n"
    target_block = build_js_block(build_css(CHAT_SCOPE), nl)

    if info["patched"]:
        if target_block in src:
            print("\n[OK] Fix is already up to date. Nothing to do (no duplicate injection).")
            return True
        print("\n[INFO] Updating existing patch to the latest version...")
        if not info["backup_exists"]:
            print("[STOP] Cannot update: backup file not found. Reinstall or restore original first.")
            return False
        shutil.copy2(backup, asar)
        arc = Asar(asar)
        raw = arc.read(TARGET_FILE)
        src = raw.decode("utf-8")
        info = diagnose(install_dir)

    if info["anchor_count"] != 1:
        print("\n[STOP] App code differs from the verified version. Not safe to patch. No changes made.")
        return False

    new_src = src.replace(ANCHOR, ANCHOR + nl + target_block, 1)
    new_bytes = new_src.encode("utf-8")

    # Backup the current (unpatched) archive if backup doesn't already exist.
    if not os.path.isfile(backup):
        shutil.copy2(asar, backup)
        if sha256_file(backup) != sha256_file(asar):
            print("[STOP] Backup verification failed. No changes made.")
            return False
        print(f"\n[OK] Backup created: {backup}")

    # Append new utils.js bytes; all other file bytes stay byte-identical.
    entry = arc.entry(TARGET_FILE)
    entry["offset"] = str(len(arc.data))
    entry["size"] = len(new_bytes)
    if "integrity" in entry:
        entry["integrity"] = integrity_for(new_bytes)
    with open(tmp, "wb") as f:
        f.write(serialize_asar(arc.header, arc.data + new_bytes))

    try:
        verify_archive(tmp)
        if MARKER_START not in Asar(tmp).read(TARGET_FILE).decode("utf-8"):
            raise ValueError("Marker missing after write.")
    except Exception as exc:
        os.remove(tmp)
        print(f"[STOP] Verification of new archive failed ({exc}). Original untouched.")
        return False

    os.replace(tmp, asar)
    with open(meta, "w", encoding="utf-8") as f:
        json.dump({"app_version": info["app_version"],
                   "original_sha256": sha256_file(backup),
                   "patched_sha256": sha256_file(asar),
                   "date": datetime.datetime.now().isoformat(timespec="seconds"),
                   "chat_scope": CHAT_SCOPE}, f, indent=2)
    print("[OK] RTL fix applied. Start Antigravity normally.")
    return True


def restore(install_dir) -> bool:
    asar, backup, meta, _ = paths(install_dir)
    info = diagnose(install_dir)
    if info["running"]:
        print("\n[!] Antigravity is currently running in the background.")
        choice = input("Do you want to close it automatically to restore? (y/n): ").strip().lower()
        if choice in ["y", "yes"]:
            if kill_running():
                print("[OK] Antigravity closed successfully.")
                info = diagnose(install_dir)
            else:
                print("[STOP] Failed to close Antigravity automatically. Please close it manually and retry.")
                return False
        else:
            print("[STOP] Antigravity must be closed to restore.")
            return False
    if not info["patched"]:
        print("\n[OK] Current app is not patched (or was updated). Nothing to restore.")
        return True
    if not os.path.isfile(backup):
        print("\n[STOP] No backup file found. Reinstalling Antigravity also restores the original.")
        return False
    try:
        if app_version(backup) != info["app_version"]:
            print("\n[STOP] Backup is from a different app version. Not restoring.")
            return False
        verify_archive(backup)
        if MARKER_START in Asar(backup).read(TARGET_FILE).decode("utf-8"):
            print("\n[STOP] Backup itself contains the patch. Not restoring.")
            return False
    except Exception as exc:
        print(f"\n[STOP] Backup is invalid ({exc}). Not restoring.")
        return False
    shutil.copy2(backup, asar)
    if os.path.isfile(meta):
        os.remove(meta)
    print("\n[OK] Original restored. Start Antigravity normally.")
    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def pick_install(arg_dir):
    if arg_dir:
        if not is_antigravity_app(arg_dir):
            print(f"[STOP] '{arg_dir}' is not the Antigravity desktop app folder.")
            return None
        return arg_dir
    dirs = find_install_dirs()
    if not dirs:
        print("[STOP] Antigravity desktop app not found in LocalAppData or Program Files.")
        return None
    if len(dirs) > 1:
        print("Multiple installs found:")
        for i, d in enumerate(dirs, 1):
            print(f"  {i}) {d}")
        choice = input("Pick number: ").strip()
        if not choice.isdigit() or not 1 <= int(choice) <= len(dirs):
            return None
        return dirs[int(choice) - 1]
    return dirs[0]


def main():
    ap = argparse.ArgumentParser(description="Antigravity chat RTL fix")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--diagnose", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--restore", action="store_true")
    ap.add_argument("--install-dir")
    args = ap.parse_args()

    install = pick_install(args.install_dir)
    if not install:
        return 1
    try:
        if args.diagnose:
            diagnose(install)
            return 0
        if args.apply:
            return 0 if apply_patch(install) else 1
        if args.restore:
            return 0 if restore(install) else 1
        while True:
            print("\n==== Antigravity RTL Fix ====")
            print("  1) Diagnose (read-only)")
            print("  2) Apply RTL fix")
            print("  3) Restore original (Undo)")
            print("  4) Exit")
            c = input("Choose 1-4: ").strip()
            if c == "1":
                diagnose(install)
            elif c == "2":
                apply_patch(install)
            elif c == "3":
                restore(install)
            elif c == "4":
                return 0
    except PermissionError:
        print("[STOP] Access denied. Close Antigravity, or run the .bat as Administrator if installed in Program Files.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
