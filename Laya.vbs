Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
strPath = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strPath

If FSO.FileExists(strPath & "\Laya.exe") Then
    WshShell.Run """" & strPath & "\Laya.exe""", 0, False
Else
    strPythonw = "pythonw.exe"
    If FSO.FileExists("C:\Python312\pythonw.exe") Then
        strPythonw = """C:\Python312\pythonw.exe"""
    End If
    WshShell.Run strPythonw & " -m laya.main --hud", 0, False
End If
