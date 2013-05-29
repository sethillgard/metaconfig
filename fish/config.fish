set -x EDITOR vim

set fish_greeting ""

# Detect terminal.
switch $TERM
  case xterm xterm-color xterm-256color screen-256color
    set fancy_terminal true
  case "*"
    set fancy_terminal false
end

# Set LS_COLORS.
# . ~/.config/fish/ls_colors.fish
eval (dircolors -c ~/.dircolors)
set GREP_COLOR "1;31"