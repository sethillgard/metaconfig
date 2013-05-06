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

    This script will also generate a log file with the full list of changes
    performed, and there is a script called uninstall.py that can be used to
    revert any changes made.
    """)

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

    # Ignore hidden folders. This includes .git
    if module_name[0] is ".":
      continue

    print("\n--- Installing module: " + module_name)

    if "localmetaconfig.yaml" in file_names:
      stream = open(module_meta_path + "/localmetaconfig.yaml", 'r')
    elif "metaconfig.yaml" in file_names:
      stream = open(module_meta_path + "/metaconfig.yaml", 'r')
    else:
      print("No meta file for module. Skipping.")
      continue

    module = yaml.load(stream)
    for element in module:
      result = installElement(element, module_meta_path)
      if result is "parse_error":
        print ("Error: Could not parse yaml file for module: " + module_name)


  print("\n--- Done ---")
  return 0

def installElement(element, module_meta_path):
  if "dir" in element:
    name = element["dir"]
    is_dir = True
  elif "file" in element:
    name = element["file"]
    is_dir = False
  else:
    return "parse_error"

  print("Installing element: " + name)

  # The path where we want the symlink to go
  meta_path = module_meta_path + "/" + name
  suggested_location = None
  path = None

  if not os.path.lexists(meta_path):
    print("Error: No matching element at " + meta_path)
    print("This would create a broken symlink. Skipping this element.")
    return "error"

  if "location" in element:
    suggested_location = os.path.normpath(element["location"])
    suggested_location = expandPath(suggested_location + "/" + name)
    if os.path.lexists(suggested_location):
      path = suggested_location
    else:
      print ("File not in the suggested location: " + suggested_location)

  # In case the file is not on the suggested location, or if no location was
  # suggested, ask the user for the path.
  if path is None:
    path = promptPath(name, is_dir)

    # If path is still None, we should just skip this element, because the user
    # told us to.
    if path is None:
      print("Skipping: " + name)
      return "ok"

  # At this point, path is guaranteed to exist because promptPath makes sure
  # it does.
  path = expandPath(os.path.normpath(path))

  # If the file is already a symlink to where we want it, do nothing.
  # This possibly means this tool ran before.
  if os.path.islink(path):
    if os.path.samefile(os.path.realpath(path), meta_path):
      print("Symlink already present. Skipping.")
      return "ok"

  # Check the type of the element
  if is_dir and not os.path.isdir(path):
    print("Error: " + path + " is a file, not a directory.")
    return "error"
  if not is_dir and os.path.isdir(path):
    print("Error: " + path + " is a directory, not a file.")
    return "error"

  # Get the backup info
  bak_path = getNextBak(path)
  print("Creating backup: " + bak_path)

  # Here we go. Rename the file to the backup and replace it with a symlink.
  try:
    os.rename(path, bak_path)
    os.symlink(meta_path, path)
  except IOError:
    print("Error creating symlink from: " + path + " to path: " + meta_path)

def promptPath(name, is_dir):
  readline.set_completer_delims(' \t\n;')
  readline.parse_and_bind("tab: complete")
  readline.set_completer(complete)

  path = None
  while True:
    print("You can press tab to autocomplete.")
    if is_dir:
      print("Leave empty to skip this directory.")
    else:
      print("Leave empty to skip this file.")

    path = input("Where is " + name + "? ")

    # If we get an empty string back, just return, indicating to skip this file.
    if path.strip() is "":
      return None

    # If we are prompting for a directory...
    if is_dir and os.path.isdir(path):
      if name is os.path.basename(os.path.normpath(path)):
        return path
      else:
        use = promptYesNo("The directory provided has a different name. " +
          "Use anyways?")
        if use:
          return path

    # If we are prompting for a file...
    elif not is_dir and os.path.lexists(path):
      if name is os.path.basename(path):
        return path
      else:
        use = promptYesNo("The file provided has a different name. " +
          "Use anyways?")
        if use:
          return path

    # Input error. Invalid path.
    else:
      print("The provided path is invalid. Please try again.")
      if is_dir:
        print("A valid path to a directory is needed.")
      else:
        print("A valid path to a file is needed.")
      print("")

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

def complete(text, state):
  text = expandPath(text)
  return (glob.glob(text + '*')+[None])[state]

if __name__ == "__main__":
    main(sys.argv[1:])