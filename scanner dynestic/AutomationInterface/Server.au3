#include <GUIConstantsEx.au3>
#include <GUIConstants.au3>
#include <Array.au3>

#include <ButtonConstants.au3>
#include <EditConstants.au3>
#include <GUIConstantsEx.au3>
#include <WindowsConstants.au3>

;~ Server Ip
$MaxConnect = 100
TCPStartup()
$Socket = TCPListen(@IPAddress1, 50000, $MaxConnect) ;~ für 100 Clients
ConsoleWrite(@IPAddress1 & @CRLF)
ConsoleWrite($Socket & @CRLF)
Global $aSendstr[1]
Global $iJobCount, $jobfilename="autojob.txt", $i
$Verbindung = -1

#Region ### START Koda GUI section ### Form=
$Form1 = GUICreate("MVP Simulator", 633, 447, 192, 124)
$Edit1 = GUICtrlCreateEdit("", 40, 192, 561, 249)
$SEND = GUICtrlCreateButton("Send", 500, 130, 100, 30, $WS_GROUP)
$SEND2 = GUICtrlCreateButton("Autojob.txt", 500, 90, 100, 30, $WS_GROUP)
$SENDGetTemp = GUICtrlCreateButton("MVPGetTemplates", 500, 10, 100, 30, $WS_GROUP)
$SENDGetProfile = GUICtrlCreateButton("MVPGetProfile", 500, 50, 100, 30, $WS_GROUP)
$Button2 = GUICtrlCreateButton("StartServer", 40, 10, 100, 50, $WS_GROUP)
$Input1 = GUICtrlCreateInput("Input command", 40, 135, 440, 21)
Global $Textbox

GUISetState(@SW_SHOW)
#EndRegion ### END Koda GUI section ###


While 1

	$nMsg = GUIGetMsg()
	Switch $nMsg
		Case $GUI_EVENT_CLOSE
			Exit
		Case $SEND
			$strTemp=GUICtrlRead($Input1)
			$strTemp=StringReplace($strTemp,"|",ChrW(9))
			TCPSend($Verbindung,$strTemp)
		Case $SEND2
			SendArray()
		Case $Button2
			TCPCloseSocket($Verbindung)
			TCPShutdown()
			$Verbindung= -1
			sleep(1000)
			TCPStartup()
			sleep(1000)
			$Socket = TCPListen(@IPAddress1, 50000, $MaxConnect) ;~ für 100 Clients
			GUICtrlSetData($Edit1, "Restart Server")
;~ 			$Verbindung = TCPAccept($Socket)
			ConsoleWrite(@IPAddress1 & @CRLF)
			ConsoleWrite($Socket & @CRLF)
;~ 			ConsoleWrite($Verbindung & @CRLF)
		case $SENDGetTemp
			GetTemplate()
		case $SENDGetProfile
			GetProfile()


	EndSwitch




		If $Verbindung = -1 Then
			$Verbindung = TCPAccept($Socket)
		EndIf

		If $Verbindung <> -1 Then
			$Resv = TCPRecv($Verbindung, 2048)
			If @error Then
				TCPCloseSocket($Verbindung)
				$Verbindung= -1
			EndIf

			If $Resv <> "" Then
					If $Verbindung <> -1 Then
						if StringInStr($Resv,"KEEP_ALIVE")=0 Then
							GUICtrlSetData($Edit1, $Resv)
						EndIf
						if StringInStr($Resv,"HHCNC1NEW")>0 THEN
							TCPSend($Verbindung, "NEWPORT=59000")
							TCPCloseSocket($Verbindung)
							$Socket = TCPListen(@IPAddress1, 59000, $MaxConnect) ;~ für 100 Clients
							$Verbindung = TCPAccept($Socket)
						EndIf
					EndIf
					$Textbox=$Resv&@CRLF&$Textbox
					GUICtrlSetData($Edit1, $Textbox)
			EndIf
		EndIf
WEnd

Func SendArray()
	dim $strTemp, $i, $timeout
	Redim $aSendstr[1]

	$iJobCount=IniRead($jobfilename,"job","count",0)
	for $i=1 to $iJobCount
		_ArrayAdd($aSendstr,iniRead($jobfilename,"job",$i,""))
	Next
	_ArrayDisplay($aSendstr)

	for $i = 1 to $iJobCount
		if $aSendstr[$i]<>"" Then
			$strTemp=StringReplace($aSendstr[$i],"|",ChrW(9))
			TCPSend($Verbindung,$strTemp)
			$ok=false
			$timeout = TimerInit()
			while $ok=false
				$Resv = TCPRecv($Verbindung, 2048)
				if StringInStr($Resv,"Command_Executed")>0 OR StringInStr($Resv,"HHGetHostname")>0 OR StringInStr($Resv,"MVPGetTemplates")>0 THEN
					;MsgBox(1,"Receive", $Resv)
					$Textbox=$Resv&@CRLF&$Textbox
					GUICtrlSetData($Edit1, $Textbox)
					$ok=True
				EndIf
				if TimerDiff($timeout)>30000 Then
					$Textbox="Sync Error: "&$strTemp&@CRLF&$Textbox
					GUICtrlSetData($Edit1, $Textbox)
					;MsgBox(1,"Sync Error","Sync > 30sec")
					ExitLoop
				EndIf
			WEnd
		EndIf
		if GUIGetMsg() = $Button2 THEN
				MsgBox(1,"Exit Error","Exit")
			ExitLoop
		EndIf
		
	Next



EndFunc

Func GetTemplate()

	TCPSend($Verbindung,"MVPGetTemplates")


EndFunc

Func GetProfile()

	TCPSend($Verbindung,"MVPGetProfiles")

EndFunc

