# csm demo — drives the real curses TUI against the fake demo dataset.
# Render with ./build.sh (Docker). Produces picker.gif (README) + picker.mp4.

Output picker.gif
Output picker.mp4

Require csm

Set Shell bash
Set FontFamily "DejaVu Sans Mono"
Set FontSize 20
Set Width 1500
Set Height 850
Set Padding 24
Set Theme "Catppuccin Mocha"
Set TypingSpeed 55ms
Set Framerate 24

# Read the sandboxed demo ~/.claude (never the real one)
Env HOME "/vhs/home"

# Land in a project dir so "Current" scope shows just this project first
Hide
Type "cd /home/dev/payments && clear"
Enter
Show

Type "csm"
Enter
Sleep 2.5s

# Browse this project's sessions (note the tree group + status icons)
Down 2
Sleep 1s
Down 1
Sleep 1.2s

# Tab → All scope: every project, every session
Tab
Sleep 2s

# Fuzzy search
Type "oauth"
Sleep 1.8s
Backspace 5
Sleep 800ms

# Cycle the view presets with Shift+Tab (Grouped·Date → A-Z → Flat·Date → Flat·A-Z)
Down 4
Sleep 600ms
Shift+Tab
Sleep 1.3s
Shift+Tab
Sleep 1.3s
Shift+Tab
Sleep 1.3s
Shift+Tab
Sleep 1s

# Toggle a task's status (open → wip → done → blocked)
Ctrl+S
Sleep 1.3s
Ctrl+S
Sleep 1.3s

# Rename the selected session inline
Ctrl+E
Sleep 800ms
Type " (now with split payments)"
Sleep 600ms
Enter
Sleep 1.5s

# Refresh picks up external changes
Ctrl+R
Sleep 1.2s

# Detail panel: notes, branch, context, last message
Down 2
Sleep 2s

Escape
Sleep 800ms
