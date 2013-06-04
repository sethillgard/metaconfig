
function fish_prompt

   # Just calculate these once, to save a few cycles when displaying the prompt
   if not set -q __fish_prompt_hostname
     set -g __fish_prompt_hostname (hostname|cut -d . -f 1)
   end

  printf '╭─ %s%s@%s %s' (set_color blue) (whoami) $__fish_prompt_hostname
  printf '%s%s' (set_color purple --bold) (prompt_pwd)
  printf '%s%s' (set_color red --bold) (__fish_git_prompt)

  printf '\n%s' (set_color normal)
  printf '╰%s➤ ' (set_color red --bold)
end
