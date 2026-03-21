Функция ПолучитьПринтерПоУмолчанию() Экспорт
	
    Скрипт = Новый ComObject("MSScriptControl.ScriptControl");
    Скрипт.Language = "vbscript";                 
    Скрипт.AddCode("
         |Function GetDefaultPrinter()
         |GetDefaultPrinter=vbNullString
         |Set objWMIService=GetObject(""winmgmts:"" _
         |& ""{impersonationLevel=impersonate}!\\.\root\cimv2"")
         |Set colInstalledPrinters=objWMIService.ExecQuery _
         |(""Select * from Win32_Printer"")
         |For Each objPrinter in colInstalledPrinters
         |If objPrinter.Attributes and 4 Then
         |GetDefaultPrinter=objPrinter.Name
         |Exit For
         |End If
         |Next
         |End Function");
	Возврат СокрЛП(Скрипт.run("GetDefaultPrinter"));
	
КонецФункции
