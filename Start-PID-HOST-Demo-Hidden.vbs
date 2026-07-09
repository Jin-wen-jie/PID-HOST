Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
command = "wscript.exe " & """" & scriptDir & "\Start-PID-HOST-Hidden.vbs" & """ " & "--demo"

shell.CurrentDirectory = scriptDir
shell.Run command, 0, False
