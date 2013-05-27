metaconfig
==========

A simple interactive script that allows you to quickly put all of your dotfiles, configuration files and plug-in folders under version control, or at least put them all in a shared folder so you can keep them in sync across multiple computers.

metaconfig.py will create a backup of the files you indicate, and then replace them with a symlink to the shared file in the metaconfig directory.

You can create modules (directories) to organize your files, install only a subset of them or keep different configurations for different computers.

If you are using version control, you can use branches to manage configurations (up to you!), but metaconfig allows you to have a simple way of filtering symlinks by specifying flavors.

Requirements
-------------------

- Python 3.x
- PyYaml (http://pyyaml.org/).

To install PyYaml on Ubuntu simply do:

    sudo apt-get install python3-yaml

This program will not work with previous versions of python.

Usage: Super simple version (Not using version control)
-----------------------------------------------------------------------------

- Download this repo. If you are using DropBox or a similar service, it's a good idea to place it there so you can share it with other computers.
- Create a directory inside it. A good name for it is dotfiles.
- Put your dotfiles and config files inside this new directory.
- Run metaconfig.py with no options.
- When prompted for the folder where the files should be installed, type ~/

Recommended usage: Using git
-----------------------------------------------------------------------------

- Fork this repo.
- Clone your fork.
- Create a directory inside it for each group of files you would like to install. I tend to group them by program, so I have a vim directory, a bash directory, a tmux directory, and a sublime_text directory and so on.
- Put your dotfiles and config files inside the new directories you created.
- Run metaconfig.py with no options.
- When prompted for the folder where the files should be installed, type the appropriate paths.
- Push your changes to your fork.

Program flags
--------------------------------------

- *-h* Show help
- *-d* Dry run. No changes will be made to the filesystem. Use this to test the effects of this program.
- *-m* Only install the modules listed after this option.
- *-e* Exclude the modules listed after this option.
- *-f* Use the flavors listed after this option. See the [flavors] section for more information.
- *--non-interactive* Run in non interactive mode. Will not prompt the user for any additional information. Make sure to test before running with this option.

Examples:

Install only the vim an bash modules:
```metaconfig.py -m vim bash```

Install every module except zsh:
```metaconfig.py -e zsh```

Test the effects of installing the linux and the home flavors on this computer:
```metaconfig.py -d -f linux home```

metaconfig.yaml files
-----------------------------

Inside each module (directory), you can create an optional file called metaconfig.yaml

If present, the script will read this file for additional information regarding which files to install, where, and how.

The simplest metaconfig.yaml file looks like this:

```yaml
    location: ~/
```

This indicates that the files in this folder should be installed in your home folder, so when the program is run, it will install them there instead of asking for the path.

Generally, you don't need to configure it much further.

The full list of possible fields in a metaconfig.yaml file are:

- location: The path to where this module should be installed. Individual symlinks can override this path, or append to it. You can set this to "?", including quotation marks to ask the user each time.
- enabled: If set to False, this module will not be installed. Defaults to True.
- infer_symlinks: If set to True, it will install all the files in this directory. If set to False, only the files listed in the "symlinks" list will be installed. Defaults to False if the "symlinks" option is defined, True otherwise.
- exclude: A list of files to exclude. Useful when infer_symlinks is set to True.
- flavors: The list of flavors for this module. See the [flavors] section for more information.
- symlinks: A list of symlinks to install. Each item in this list can have 2 forms:
  - A string: The name of  a file in this module to be installed.
  - A symlink object: See below.

Example of every option:
```yaml
    location: "?"
    enabled: True
    infer_symlinks: False
    exclude: []
    flavors: [linux]
    symlinks: [file1.txt, file2.txt]
```

Symlink objects can have the following fields:

- file: Mandatory. The name or path to the file to be installed. This can override or append to the location set in the module.
- target: The path to the file the symlink should point to. This file must be in the module directory.
- enabled: If set to False, this symlink will be ignored. Defaults to True.
- flavors: The list of flavors for this symlink. See the [flavors] section for more information.

Example of every option:
```yaml
    file: ~/.myconfig
    target: .myconfig_linux
    enabled: True
    flavors: [linux]
```

The options are very clear once you see some examples.

This example would be a good metaconfig.yaml file for a vim module. It will install a file (.vimrc) and a folder (.vim), both of them in the user's home directory:
```yaml
   location: ~/
   symlinks: [.vim, .vimrc]
```
This shows how you can set the symlinks field to a list of strings, filenames to be installed. However, listing the files like this is not always necessary.

Here is a more complicated example using symlink objects:
```yaml
   location: ~/apps/myapp/
   symlinks:
     - file: .project
     - file: res/manifest.xml
       target: project_manifest.xml
```
This will create 2 symlinks. The first one does not specify a target, meaning that the target is a file of the same name in the module's directory. The second one has a target, so the symlink will point to that file.

The 2 symlinks generated will be:
- _~/apps/myapp/.project -----> [metaconfig/module]/.project_
- _~/apps/myapp/res/manifest -----> [metaconfig/module]/project_manifest.xml_

localmetaconfig.yaml files
-----------------------------

If a file named _localmetaconfig.yaml_ is present on the module's directory, that file will be read instead of _metaconfig.yaml_. This is useful for when there is a quick config change that needs to happen locally and nowhere else.

_localmetaconfig.yaml_ files are ignored in the default .gitignore for this repo.

Flavors
----------

Flavors are a simple way of creating multiple configurations for different computers. If you need something more complicated, consider using git branches.

You can specify flavors for modules or individual symlinks. If a module or symlink has a flavor list, it will only be installed if the script is run with at least one of the flavors in that list.

For example, in your vim module, you can have the following _metaconfig.yaml_:

```yaml
    location: ~/
    symlinks:
      - file: .vim
      - file: .vimrc
        target: .vimrc_linux
        flavors: [linux]
      - file: .vimrc
        target: .vimrc_mac
        flavors: [mac]
```

This will create 2 symlinks.

_.vim_ will always be installed, regardless of the flavors used.
_.vimrc_ will only be installed if the _linux_ or _mac_ flavors are used when running the program.

```metaconfig.py -f linux``` will create a .vimrc symlink pointing to [metaconfig/module]/.vimrc_linux

```metaconfig.py -f mac``` will create a .vimrc symlink pointing to [metaconfig/module]/.vimrc_mac

You can use the same technique to select which modules to install based on the flavors used.

[flavors]: (https://github.com/sethillgard/metaconfig/master/README.md#flavors)
