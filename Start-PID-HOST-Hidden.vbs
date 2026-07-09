Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
command = """" & scriptDir & "\Start-PID-HOST.bat" & """"

For Each arg In WScript.Arguments
  command = command & " " & """" & Replace(arg, """", """""") & """"
Next

shell.CurrentDirectory = scriptDir
shell.Run command, 0, False
