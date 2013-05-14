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
import time
import sys
import yaml
import os.path
import readline
import glob
import fnmatch
import filecmp
import argparse
import string
import shutil

# Arguments to the program
args = None

class bc:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    END = '\033[0m'

def main(argv):
  global args
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

  parser = argparse.ArgumentParser()
  parser.add_argument("-d", "--dry-run", default=False, action="store_true",
    help = "run the script without making any changes to the filesystem.")
  parser.add_argument("--non-interactive", default=False, action="store_true",
    help = "don't prompt the user for any information.")
  parser.add_argument("-m", "--modules", nargs='+', default = [],
    help = "only install the modules listed after this option.")
  parser.add_argument("-e", "--exclude-modules", nargs='+', default = [],
    help = "exclude the list of modules listed after this option.")
  parser.add_argument("-f", "--flavors", nargs='+', default = [],
    help = "use the flavors listed after this option. Flavors allow you to " +
      "filter the modules and files installed when this script runs. See the " +
      "website above for more info.")

  args = parser.parse_args()

  ignored_files = ["metaconfig.yaml", "localmetaconfig.yaml"]

  for (module_meta_path, dir_name, file_names) in os.walk(meta_dir):
    module_meta_path = expandPath(module_meta_path)

    common_prefix = os.path.commonprefix([module_meta_path, meta_dir])
    module_name = os.path.relpath(module_meta_path, common_prefix)

    # Ignore the config dir itself
    if module_meta_path is meta_dir:
      continue

    module = None

    # Ignore modules not listed as parameters, ignored ones, and hidden ones.
    if len(args.modules) > 0 and module_name not in args.modules: continue
    if module_name in args.exclude_modules: continue
    if module_name[0] is ".": continue

    if "localmetaconfig.yaml" in file_names:
      stream = open(module_meta_path + "/localmetaconfig.yaml", 'r')
    elif "metaconfig.yaml" in file_names:
      stream = open(module_meta_path + "/metaconfig.yaml", 'r')
    else:
      if os.sep in module_name:
        continue
      # For top level modules without metaconfig.yaml file, infer files and
      # prompt for the location.
      module = {"location": "?", "infer_symlinks": True}

    # Load it's yaml file.
    if module is None:
      module = yaml.load(stream)

    printWithDelay("\n--- Module: " + module_name + " ---")
    if "localmetaconfig.yaml" in file_names:
      printWithDelay(" - Using localmetaconfig.yaml")
    elif "metaconfig.yaml" in file_names:
      printWithDelay(" - Using metaconfig.yaml")

    # Should we skip this one?
    if ("enabled" in module and module["enabled"] is False) or \
        ("ignore" in module and module["ignore"] is True):
      printWithDelay(" - Module not enabled. Skipping.")
      continue

    # Check the flavors.
    if "flavors" in module:
      # If these lists don't intersect, just skip the module.
      if not set(args.flavors) & set(module["flavors"]):
        printWithDelay(" - Module has flavor requirements. Skipping because " +
          "we are not running with the correct flavors.")
        continue

    # Infer links from the files in the module
    if not "symlinks" in module or "infer_symlinks" in module and \
        module["infer_symlinks"]:
      if not "location" in module:
        module["location"] = "?"
      if not "symlinks" in module:
        module["symlinks"] = []
      infered_links = os.listdir(module_meta_path)
      infered_links = [x for x in infered_links if not isTempFile(x) and
        x not in ignored_files]
      module["symlinks"] = list(set(module["symlinks"] + infered_links))

    if not "symlinks" in module or len(module["symlinks"]) == 0:
      printWithDelay("This module contains no files. Skipping.")
      continue

    # Print a list of links to be installed and ask the user if the module
    # should be installed.
    printWithDelay("This module includes the following files: ")
    for link in module["symlinks"]:
      if isinstance(link, str):
        printWithDelay(" - " + link)
      else:
        if not "symlink" in link:
          printWithDelay(" - [unnamed] -  This will throw an error!")
        else:
          printWithDelay(" - " + link["symlink"])
    if not promptYesNo("Install this module?"):
      continue

    # If the location for the module is "?", we should ask each time.
    if "location" in module and module["location"] == "?":
      printWithDelay("Please provide the base path for this module.")
      location = promptPath(None)
      if location is not None and location != "":
        module["location"] = location

    # Install symlinks
    if "symlinks" in module:
      for link in module["symlinks"]:
        result = installSymlink(link, module, module_meta_path, meta_dir)

  printWithDelay("\n    ------ Done ------\n")
  return 0

def installSymlink(symlink, module, module_meta_path, meta_dir):
  global args
  basepath = "?"
  if "location" in module:
    basepath = module["location"]

  if isinstance(symlink, str):
    filename = symlink
  else:
    if not "symlink" in symlink:
      printWithDelay("Error: Symlink as a dict without a 'symlink' field.",
        error = True)
      return "error"
    filename = symlink["symlink"]

    # Should we skip this one?
    if ("enabled" in symlink and symlink["enabled"] is False) or \
        ("ignore" in symlink and symlink["ignore"] is True):
      printWithDelay("Symlink not enabled. Skipping.")
      return

    # Check the flavors.
    if "flavors" in symlink:
      # If this lists don't intersect, just skip the symlink.
      if not set(args.flavors) & set(module["flavors"]):
        printWithDelay(" - Symlink has flavor requirements. Skipping because " +
          "we are not running with the correct flavors.")
        return "ok"

    if "location" in symlink:
      basepath = symlink["location"]

  if filename is "":
    printWithDelay(bc.ERROR, end='')
    printWithDelay("Error: Found empty filename for symlink.")
    printWithDelay(bc.END, end='')
    return "error"

  # Cleanup
  if basepath[-1:] != os.sep:
    basepath += os.sep

  filename = expandPath(filename)
  basepath = expandPath(basepath)

  # Take out the last "/" if it's the last character so that split works
  # correctly.
  if filename[-1:] is os.sep:
    filename = filename[:-1]

  # We do this because the filename may add to the basepath, or override it.
  # For example, if basepath is "~/", filename may be "somedir/somefile", in
  # which case the full path should be "~/somedir/somefile". But filename may
  # also be "/logs/somelog", in which case the "/" means it's an absolute path,
  # and we should ignore the basepath.
  # Save the old filename because it's useful to tell the user which file
  # in particular we are talking about.
  old_filename = filename
  middle, filename = os.path.split(filename)

  target = os.path.join(module_meta_path, middle, filename)
  # Target may be explicitly defined. The type check is to avoid hits when the
  # string contains "target" as a substring.
  if not isinstance(symlink, str) and "target" in symlink:
    target = expandPath(os.path.join(module_meta_path, symlink["target"]))

  printWithDelay("Installing symlink: " + old_filename)

  # Make sure we have a file of the same name in the metaconfig folder.
  if not os.path.lexists(target):
    printWithDelay(" - Error: No matching element for " + filename + " at " +
      target, error = True)
    printWithDelay(" - This would create a broken symlink. Skipping this " +
      "element.", error = True)
    return "error"

  # Figure out where should we install thsi symlink
  path = getFullPath(basepath, middle, filename, meta_dir)
  if path is None:
    print (" - Skipping " + filename)
    return "ok"

  # If the file is already a symlink to where we want it, do nothing.
  # This possibly means this tool ran before.
  if os.path.islink(path):
    real_path = os.path.realpath(path)
    if os.path.lexists(real_path) and os.path.samefile(real_path, target):
      printWithDelay(" - Symlink already present. Skipping.")
      return "ok"

  # Get the backup info
  need_backup = os.path.lexists(path)
  current_backup = None
  next_backup = None
  if need_backup:
    current_backup, next_backup = getBackupPaths(path)
    if current_backup is not None:
      # Check if we need to create a backup by comparing the file with most
      # recent backup, we do this differently if its just a file or a dir, but
      # in both cases we asssume they are equal if the names and contents are
      # the same (recursively).
      if os.path.isdir(target):
        need_backup = not compareDirs(target, current_backup)
      else:
        need_backup = not filecmp.cmp(target, current_backup)

  # Here we go. Rename the file to the backup and replace it with a symlink.
  try:
    if need_backup:
      printWithDelay(" - Creating backup: " + next_backup)
      if not args.dry_run:
        shutil.move(path, next_backup)
    else:
      if current_backup is not None:
        printWithDelay(" - Exact backup already present: " + current_backup)
    if not args.dry_run:
        os.symlink(target, path)
    printWithDelay(" - Installed symlink successfuly.")
  except IOError:
    printWithDelay(" - Error creating symlink from: " + path , error = True)
    printWithDelay(" - To: " + target , error = True)
    printWithDelay(" - Do we have the correct permissions?", error = True)

def getFullPath(basepath, middle, filename, meta_dir):
  global args
  if os.path.normpath(basepath) is "?":
    # If the basepath is "?" we should always prompt
    path = promptPath(filename)
  elif middle is "":
    if basepath is "":
      # We have no information, just prompt.
      path = promptPath(filename)
    else:
      # We have a basepath and no middle.
      path = os.path.join(basepath, filename)
  else:
    if middle[0] in ["~", "/", "."]:
      # Middle suggests its an absolute or relative part, ignore basepath.
      path = os.path.join(middle, filename)
    else:
      # We actually have 3 parts.
      path = os.path.join(basepath, middle, filename)

  path_valid = False
  while not path_valid:
    path_valid = True

    # Skip this element?
    if path is "" or path is None:
      return None

    # Whoa, lots of ifs. At this point we have a path. Let's make sure it exists,
    # otherwise, prompt. We actually don't need it to exist, we just need the
    # base dir to exist.
    parent_dir, _ = os.path.split(path)
    if not os.path.isdir(parent_dir):
      printWithDelay(" - Inexistent path: " + parent_dir, error = True)
      path_valid = False

    # Make sure the path provided is not in the metaconfig folder.
    # The only valid case for this is if it's a symlink on the leaf, meaning
    # its a symlink createad by this script or something similar.
    if not os.path.islink(path):
      real_path = os.path.realpath(path)
      real_meta_dir = os.path.realpath(meta_dir)
      length = len(real_meta_dir)
      if len(real_path) >= length and real_path[:length] == meta_dir:
        printWithDelay("Error: The path provided is inside the metaconfig " +
          "folder.", error = True)
        printWithDelay("Please provide a path to the local file you want " +
          "replaced.", error = True)
        path_valid = False

    if not path_valid:
      path = promptPath(filename)

  return path

def promptPath(filename):
  global args
  if args.non_interactive:
    printWithDelay("No path provided. Cannot prompt in non-interactive mode.",
      error = True)
    return None

  readline.set_completer_delims(' \t\n;')
  readline.parse_and_bind("tab: complete")
  readline.set_completer(promptPathCompleter)

  path = None
  while True:
    if filename is None:
      printWithDelay(" - Provide the base path (local) for the all the files " +
        "in this module.")
      printWithDelay(" - You can press tab to autocomplete. " +
        "Leave empty to enter the location of each link individually.")
    else:
      printWithDelay(" - Provide a path for the local " + filename +
        " in this computer.")
      printWithDelay(" - You can press tab to autocomplete. " +
        "Leave empty to skip this file.")
    if filename is None:
      path = input(" >>> ")
    else:
      path = input(" - " + filename + " >>> ")

    # If we get an empty string back, just return, indicating to skip this file.
    if path.strip() is "":
      return None

    path = expandPath(path)

    # We were given a path to the parent folder maybe?
    if filename is not None:
      join = os.path.join(path, filename)
      if os.path.isdir(path) and os.path.lexists(join):
        if promptYesNo("Replace " + join + " ?"):
          return join

    # We get something that exists
    if os.path.lexists(path):
      if filename is None:
        # This means we are trying to get the location for the whole module
        return path
      if promptYesNo("Replace " + path + " ?"):
        return path
      else:
        continue

    # The full path fails, but the base path is correct, so we are being given
    # the path to a new file, which is fine.
    base, _ = os.path.split(path)
    if os.path.lexists(base) and os.path.isdir(base):
      if promptYesNo("Replace " + path + " ?"):
        return path
      else:
        continue

    printWithDelay("Invalid path. Please try again.", error = True)

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
  global args
  if args.non_interactive:
    return True

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
      sys.stdout.write("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")


def compareDirs(dir1, dir2):
  """
  Compare two directories recursively. Files in each directory are
  assumed to be equal if their names and contents are equal.

  @param dir1: First directory path
  @param dir2: Second directory path

  @return: True if the directory trees are the same and
      there were no errors while accessing the directories or files,
      False otherwise.
  Taken from: http://stackoverflow.com/a/6681395/131319
  """
  dirs_cmp = filecmp.dircmp(dir1, dir2)
  if len(dirs_cmp.left_only)>0 or len(dirs_cmp.right_only)>0 or \
    len(dirs_cmp.funny_files)>0:
    return False
  (_, mismatch, errors) =  filecmp.cmpfiles(
    dir1, dir2, dirs_cmp.common_files, shallow=False)
  if len(mismatch)>0 or len(errors)>0:
    return False
  for common_dir in dirs_cmp.common_dirs:
    new_dir1 = os.path.join(dir1, common_dir)
    new_dir2 = os.path.join(dir2, common_dir)
    if not compareDirs(new_dir1, new_dir2):
      return False
  return True

def expandPath(path):
  return os.path.expandvars(os.path.expanduser(path))

def getBackupPaths(path):
  """
  Determines the current and next backup names for the specified path.

  @param path: The path to the file or folder to be checked.

  @return: A string consisting of path +  ".bak" + n where n is the biggest
    (most recent) backup.

  @return: A string consisting of path +  ".bak" + n where n is the next
     available (non-existent) backup path.
  """
  path = expandPath(os.path.normpath(path))
  i = 0
  current = None
  next = None
  while True:
    i += 1
    next = path + ".bak" + str(i)
    if not os.path.lexists(next):
      return current, next
    current = next

def isTempFile(filename):
  temp = ["*.*~", "*.swp", ".DS_Store"]
  for pattern in temp:
    if fnmatch.fnmatch(filename, pattern):
      return True
  return False

def promptPathCompleter(text, state):
  text = expandPath(text)
  return (glob.glob(text + '*')+[None])[state]

def printWithDelay(text, error = False, delay = 0.003):
  global args
  if error:
    print(bc.ERROR, end='')
  if args.non_interactive:
    print(text, end='')
  else:
    for l in text:
      sys.stdout.write(l)
      sys.stdout.flush()
      time.sleep(delay)
  print(bc.END)

if __name__ == "__main__":
    main(sys.argv[1:])