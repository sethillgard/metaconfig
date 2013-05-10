#!/usr/bin/env python3

# Author: Daniel Rodriguez (itsalllowercasenospaces@gmail.com)
# Licence: MIT

# The MIT License (MIT)

# Copyright (c) 2013 Daniel Rodriguez

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os
import sys
import yaml
import os.path
import readline
import glob

def main(argv):
  print("""
    --- META CONFIG ---""")

  # Get the path of this file
  meta_dir = expandPath(os.path.dirname(os.path.realpath(__file__)))

  print("""
    This script will replace some of the files on this computer according to the
    module configuration in: """ + meta_dir + """.

    Make sure you reviewed all the modules in this directory and that they
    contain the correct configuration files that you want to use in this
    computer.

    Documentation on how to configure the modules is available at:
    http://www.github.com/sethillgard/metaconfig/

    This script will create a backup of every modified file, appending the
    extension .bak1 to the original file or directory. If a .bak1 file is
    already present, the backup will be named .bak2 and so on.

    Don't worry about running this multiple times. If a symlink to the right
    location is detected, no action will be taken for that file or directory.
    """)

  modules_to_run = ["vim"]
  ignored_modules = []

  should_continue = promptYesNo("Do you wish to continue?")
  if not should_continue:
    print("Goodbye.")
    return 0

  for (module_meta_path, dir_name, file_names) in os.walk(meta_dir):
    module_meta_path = expandPath(module_meta_path)

    common_prefix = os.path.commonprefix([module_meta_path, meta_dir])
    module_name = os.path.relpath(module_meta_path, common_prefix)

    # Ignore the config dir itself
    if module_meta_path is meta_dir:
      continue

    # Ignore modules not listed as parameters, ignored ones, and hidden ones
    if module_name not in modules_to_run: continue
    if module_name in ignored_modules: continue
    if module_name[0] is ".": continue

    print("\n--- Module: " + module_name + " ---")

    if "localmetaconfig.yaml" in file_names:
      print("Using localmetaconfig.yaml")
      stream = open(module_meta_path + "/localmetaconfig.yaml", 'r')
    elif "metaconfig.yaml" in file_names:
      stream = open(module_meta_path + "/metaconfig.yaml", 'r')
    else:
      print("No meta file for module. Skipping.")
      continue

    module = yaml.load(stream)

    if "basepath" in module:
      module["basepath"] = expandPath(module["basepath"])

    # Install symlinks
    if "symlinks" in module:
      for symlink in module["symlinks"]:
        result = installSymlink(symlink, module, module_meta_path)

  print("\n--- Done ---")
  return 0

def installSymlink(symlink, module, module_meta_path):

  # If the symlink itself contains a path, use it
  path, filename = os.path.split(expandPath(symlink))
  # Correct in case the symlink is a folder and ends in /
  if path is not "" and filename is "" and os.path.isdir(path):
    path, filename = os.path.split(expandPath(symlink)[:-1])

  if filename is "":
    print("Error: Found empty filename for symlink.")
    return "error"

  print("Installing symlink: " + filename)

  # The path where we want the symlink to go (in the metaconfig folder).
  link_target = os.path.join(module_meta_path, filename)

  # Make sure we have a file of the same name in the metaconfig folder.
  if not os.path.lexists(link_target):
    print("Error: No matching element for " + filename + " at " + link_target)
    print("This would create a broken symlink. Skipping this element.")
    return "error"

  # Use the location tag of the module if [symlink] is just the filename.
  if path is "":
    if "location" in module:
      path = expandPath(os.path.join(module["location"], filename))
    else:
      print("No path specified for " + filename)
      path = promptPath(filename, is_dir)

  # Fix this mess
  if not os.path.isdir(path):
    print ("Inexistent path: " + path)
    path = promptPath()


  # If path is still None, we should just skip this element, because the user
  # told us to.
  if path is None or path is "":
    print("Skipping: " + filename)
    return "ok"

  # At this point, path is guaranteed to exist because promptPath makes sure
  # it does.
  path = expandPath(path)
  norm_path = os.path.normpath(path)

  # If the file is already a symlink to where we want it, do nothing.
  # This possibly means this tool ran before.
  if os.path.islink(path):
    if os.path.samefile(os.path.realpath(path), link_target):
      print("Symlink already present. Skipping.")
      return "ok"

  # Get the backup info
  bak_path = getNextBak(norm_path)
  print("Creating backup: " + bak_path)

  # Here we go. Rename the file to the backup and replace it with a symlink.
  try:
    os.rename(norm_path, bak_path)
    os.symlink(link_target, norm_path)
  except IOError:
    print("Error creating symlink from: " + norm_path + " to path: " +
      link_target)

def promptPath(name):
  readline.set_completer_delims(' \t\n;')
  readline.parse_and_bind("tab: complete")
  readline.set_completer(promptPathCompleter)

  path = None
  while True:
    print("Provide a path for " + name)
    print("You can press tab to autocomplete.")
    print("Leave empty to skip.")
    path = input("Where should I put " + name + "? ")

    # If we get an empty string back, just return, indicating to skip this file.
    if path.strip() is "":
      return None

    path = expandPath(path)

    # We get something that exists
    if os.path.lexists(path):
      return path

    # The full path fails, but the base path is correct, so we are being given
    # the path to a new file. Which is fine.
    base, _ = os.path.split(path)
    if os.path.lexists(base) and os.path.isdir(base):
      return path

    print("Invalid path. Please try again.")

  raise ValueError("We should never make it here.")
  return None

def promptYesNo(question, default="yes"):
  """Ask a yes/no question via input() and return their answer.

  "question" is a string that is presented to the user.
  "default" is the presumed answer if the user just hits <Enter>.
      It must be "yes" (the default), "no" or None (meaning
      an answer is required of the user).

  The "answer" return value is one of "yes" or "no".
  Taken from: http://code.activestate.com/recipes/577058/
  """
  readline.set_completer(None)
  valid = {"yes":True, "y":True, "ye":True, "no":False, "n":False}
  if default == None:
    prompt = " [y/n] "
  elif default == "yes":
    prompt = " [Y/n] "
  elif default == "no":
    prompt = " [y/N] "
  else:
    raise ValueError("Invalid default answer: '%s'" % default)

  while True:
    sys.stdout.write(question + prompt)
    choice = input().lower()
    if default is not None and choice == '':
      return valid[default]
    elif choice in valid:
      return valid[choice]
    else:
        sys.stdout.write("Please respond with 'yes' or 'no' "\
                         "(or 'y' or 'n').\n")

def expandPath(path):
  return os.path.expandvars(os.path.expanduser(path))

def getNextBak(path):
  path = expandPath(os.path.normpath(path))
  i = 0
  while True:
    i += 1
    bak_path = path + ".bak" + str(i)
    if not os.path.lexists(bak_path):
      return bak_path

def usage():
  print("""Usage text""")

def promptPathCompleter(text, state):
  text = expandPath(text)
  return (glob.glob(text + '*')+[None])[state]

if __name__ == "__main__":
    main(sys.argv[1:])