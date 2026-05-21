Set WshShell = CreateObject("WScript.Shell")

' Запускаем батник из подпапки скрытно (флаг 0)
WshShell.Run "cmd /c .services\start_server.bat", 0, False

' Ждем 5 секунд и открываем браузер
WScript.Sleep 5000
WshShell.Run "http://localhost:8501"