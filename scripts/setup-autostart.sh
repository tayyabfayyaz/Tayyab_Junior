#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# FTE — One-Time Auto-Start Installer
#
# Installs TWO auto-start mechanisms so FTE watchers launch on every boot:
#   1. /etc/wsl.conf [boot] command  → runs when WSL starts (WSL 0.67.6+)
#   2. Windows Task Scheduler task   → runs on Windows user login
#
# Run ONCE from WSL:
#   bash /mnt/d/hackathon-FTE/scripts/setup-autostart.sh
# ─────────────────────────────────────────────────────────────────────────────

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT/scripts/start-watchers.sh"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

log() { echo "[setup] $*"; }
ok()  { echo "  ✅ $*"; }
warn(){ echo "  ⚠️  $*"; }
err() { echo "  ❌ $*"; }

log "FTE Auto-Start Installer"
log "Script to auto-start: $SCRIPT"
echo ""

# ── Make scripts executable ──────────────────────────────────────────────────
chmod +x "$SCRIPT"
chmod +x "$ROOT/scripts/start-fte.sh"
ok "Scripts marked executable"

# ═════════════════════════════════════════════════════════════════════════════
# METHOD 1: /etc/wsl.conf [boot] command
# Runs start-watchers.sh automatically when WSL initialises.
# Requires: WSL 0.67.6+ (Windows 11 or updated Windows 10)
# ═════════════════════════════════════════════════════════════════════════════
log ""
log "Method 1 — WSL boot command (/etc/wsl.conf)"

WSL_CONF="/etc/wsl.conf"
BOOT_CMD="command = bash $SCRIPT >> $LOG_DIR/wsl-boot.log 2>&1"

install_wsl_conf() {
  if [ ! -f "$WSL_CONF" ]; then
    sudo tee "$WSL_CONF" > /dev/null <<EOF
[boot]
$BOOT_CMD
EOF
    ok "Created /etc/wsl.conf with [boot] command"
  elif grep -q '^\[boot\]' "$WSL_CONF" 2>/dev/null; then
    if grep -q 'start-watchers' "$WSL_CONF" 2>/dev/null; then
      ok "/etc/wsl.conf already has FTE boot command — skip"
    else
      # Add command= under existing [boot] section
      sudo sed -i '/^\[boot\]/a '"$BOOT_CMD" "$WSL_CONF"
      ok "Added FTE command to existing [boot] section in /etc/wsl.conf"
    fi
  else
    # Append new [boot] section
    printf '\n[boot]\n%s\n' "$BOOT_CMD" | sudo tee -a "$WSL_CONF" > /dev/null
    ok "Appended [boot] section to /etc/wsl.conf"
  fi
}

if command -v sudo &>/dev/null; then
  install_wsl_conf
else
  warn "sudo not available — skipping /etc/wsl.conf (method 1). Try manually:"
  warn "  Add to /etc/wsl.conf:  [boot]"
  warn "                         $BOOT_CMD"
fi

# ═════════════════════════════════════════════════════════════════════════════
# METHOD 2: Windows Task Scheduler (runs on Windows user login)
# Uses schtasks.exe (available in WSL via Windows interop).
# Creates a hidden task that runs: wsl bash <script>
# ═════════════════════════════════════════════════════════════════════════════
log ""
log "Method 2 — Windows Task Scheduler"

# Convert WSL path to Windows path for Task Scheduler
WIN_SCRIPT=$(wslpath -w "$SCRIPT" 2>/dev/null || echo "")

if [ -z "$WIN_SCRIPT" ]; then
  warn "Could not convert path to Windows format — skipping Task Scheduler"
else
  TASK_NAME="FTE_WatcherAutoStart"
  WIN_LOG=$(wslpath -w "$LOG_DIR/taskscheduler.log" 2>/dev/null || echo "%TEMP%\\fte.log")

  # Build the action: wsl.exe -d Ubuntu bash -c "<script>"
  WSL_DISTRO=$(wslpath -w / 2>/dev/null | grep -oE '^[A-Z]:' || echo "")
  # Use wsl.exe with distro name if available
  DISTRO_NAME=$(cat /etc/os-release 2>/dev/null | grep '^NAME=' | cut -d= -f2 | tr -d '"' | head -1)
  DISTRO_NAME="${DISTRO_NAME:-Ubuntu}"

  # Create task via schtasks.exe
  TASK_CMD="wsl.exe -d \"$DISTRO_NAME\" bash \"$SCRIPT\" >> \"$LOG_DIR/taskscheduler.log\" 2>&1"

  # Use XML for reliable task creation
  TASK_XML=$(cat <<XMLEOF
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>FTE — Auto-start Gmail watcher and executor on login</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <Delay>PT30S</Delay>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>wsl.exe</Command>
      <Arguments>-d $DISTRO_NAME bash $SCRIPT</Arguments>
    </Exec>
  </Actions>
</Task>
XMLEOF
)

  # Write XML to temp file in Windows temp directory
  TEMP_XML="/tmp/fte_task.xml"
  echo "$TASK_XML" > "$TEMP_XML"
  WIN_TEMP_XML=$(wslpath -w "$TEMP_XML" 2>/dev/null)

  # Delete old task if exists, then create new
  schtasks.exe /Delete /TN "$TASK_NAME" /F > /dev/null 2>&1 || true
  if schtasks.exe /Create /TN "$TASK_NAME" /XML "$WIN_TEMP_XML" /F > /dev/null 2>&1; then
    ok "Windows Task Scheduler task '$TASK_NAME' created"
    ok "Trigger: 30 seconds after Windows login"
    ok "Action:  wsl.exe -d $DISTRO_NAME bash $SCRIPT"
  else
    warn "Task Scheduler creation failed (may need admin rights)"
    warn "Manual fallback — see Method 3 below"
  fi

  rm -f "$TEMP_XML"
fi

# ═════════════════════════════════════════════════════════════════════════════
# METHOD 3: Windows Startup folder (manual fallback)
# Place fte-launcher.vbs in Windows Startup folder for silent auto-run.
# ═════════════════════════════════════════════════════════════════════════════
log ""
log "Method 3 — Windows Startup Folder (manual fallback)"

VBS_FILE="$ROOT/scripts/fte-launcher.vbs"
WIN_VBS=$(wslpath -w "$VBS_FILE" 2>/dev/null || echo "")

if [ -f "$VBS_FILE" ] && [ -n "$WIN_VBS" ]; then
  STARTUP_DIR=$(cmd.exe /c "echo %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup" 2>/dev/null | tr -d '\r')
  WIN_STARTUP_LINK="$STARTUP_DIR\\FTE_Watcher.vbs"

  if cmd.exe /c "copy \"$WIN_VBS\" \"$WIN_STARTUP_LINK\"" > /dev/null 2>&1; then
    ok "Copied fte-launcher.vbs to Windows Startup folder"
    ok "Location: $WIN_STARTUP_LINK"
  else
    warn "Could not auto-copy to Startup folder."
    warn "Manually copy this file to your Windows Startup folder:"
    warn "  File:   $VBS_FILE"
    warn "  Dest:   shell:startup  (paste in Windows Run dialog)"
  fi
fi

# ═════════════════════════════════════════════════════════════════════════════
# Summary
# ═════════════════════════════════════════════════════════════════════════════
echo ""
echo "══════════════════════════════════════════════════════"
echo " FTE Auto-Start Setup Complete"
echo "══════════════════════════════════════════════════════"
echo ""
echo " What happens now:"
echo "   • Every time Windows starts and you log in:"
echo "     - WSL boot (/etc/wsl.conf) starts the watchers"
echo "     - Task Scheduler fires 30s after login as backup"
echo ""
echo " Startup log:    $LOG_DIR/autostart.log"
echo " Watcher log:    $LOG_DIR/watchers.log"
echo " WSL boot log:   $LOG_DIR/wsl-boot.log"
echo ""
echo " To test right now:"
echo "   bash $SCRIPT"
echo ""
echo " To check status:"
echo "   bash $ROOT/scripts/status.sh"
echo ""
echo " To uninstall auto-start:"
echo "   schtasks.exe /Delete /TN FTE_WatcherAutoStart /F"
echo "   sudo sed -i '/start-watchers/d' /etc/wsl.conf"
echo "══════════════════════════════════════════════════════"
