SPT mod updater type thing
Takes mods from a web modlist and updates them, generating cache in the process, skipping the need to download it from host

If you wanna use this for your own friend group, you're gonna have change where the modlist is pulled from on line 15

To use this tool, simply run it in your SPTarkov directory
or make a bat file with "start cmd /k python spdmodupd.py" in it to get logs and run that instead

Dependencies:
  *Python 3
  *requests (from pip)
  *py7zr (from pip)
  *7z.exe (downloaded automatically)
