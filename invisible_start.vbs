Set WshShell = CreateObject("WScript.Shell")

' 1. Запускаем сервер (невидимо)
WshShell.Run "cmd /c start_server.bat", 0, False

' 2. Ждем 7 секунд (7000 миллисекунд), чтобы сервер успел "подняться"
' Можешь подправить это число, если твой компьютер очень быстрый или наоборот
WScript.Sleep 7000

' 3. Открываем вкладку в браузере по умолчанию
WshShell.Run "http://localhost:8501"