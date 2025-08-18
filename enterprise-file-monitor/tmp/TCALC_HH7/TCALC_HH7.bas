'#uses "TCALC_GLOBAL.BAS"
'#uses "TCALC_MT.BAS"
'#uses "TCALC_BOHR.BAS"
' Calc_Time.bas
' Version 24.09.2008 (mw)

Option Explicit

' letzte Änderung :



Dim P_T As THopsBasicToolExt
Dim P_Head As Long

'Anzahl ausegwerteter Ziffern des Feldes "WechslerArt" von links
'2007-01-30 KRI
Const WZWTypMask=4

Type TP_Sawing 
	sx As Double
	sy As Double
	sz As Double
	ex As Double
	ey As Double
	ez As Double
	G0Time As Double
	SawTime As Double
End Type


Type TDH_Stroke
	x As Double
	y As Double
	depth As Double
	dh As tDH
	Driller As tDriller
	StrokeTime As Double  ' Bearbeitungszeit Bohren
	G0Time As Double      ' Verfahrzeit zwischen den Bohrungen bzw. Anfahrt auf 1. Bohrung
End Type
	
	

Type Point_3d
	x As Double
	y As Double
	z As Double
End Type

Type Point_3dm
	p As Point_3d
	i As Double
	j As Double
	f As Double   ' Feedrate
	dr As Integer  ' drehrichtung
End Type


Type Contour 
    sp As Point_3d     ' Startpunkt
    K_P() As Point_3dm    ' Kontur - Punkte
    G0_Time As Double     ' Zeit für Anfahrt auf 1. Bearbeitungsposition / Zeit zwischen den Fräsbearbeitungen
End Type


Type TPTTool 
	HeadID As Long 
	ToolID As Long
	ToolName As String
	K() As Contour                ' Hier alle Konturen wegschreiben
	TChangeMoveTime As Double     ' Zeit für fahrt zum Werkzeugwechsel
	TChangeTime As Double         ' Werkzeugwechsel - Zeit Toolbezogen
	G0_Time As Double             ' Gesammelte G0 Zeiten
	TotalTime As Double           ' Gesamt Arbeitszeit des Werkzeugs
	MillingTime As Double	      ' Einsatzzeit Fräsen
	DHTime As Double              ' Einsatzzeit Bohren
	SawTime As Double             ' Einsatzzeit Sägen
	is_dh_drilling As Boolean     ' Drilling mit Bohrkopf
	is_sawing As Boolean          ' Sägen
	ISTCTool As Boolean           ' Werkzeug auf Wechsler Ja/Nein
	TCType As Double              ' falls auf Wechsler, ist dies der Wechslertyp z.B Pickup oder mitfahrenden Tellerwechsler
	TCPlace	As Long               ' Platznummer auf wechsler
	TCCenterX As Double           ' Wechslerposition in X
	TCCenterY As Double           ' Wechslerposition in Y
	TCCenterZ As Double           ' Wechslerposition in Z
	TP_Sawing() As TP_Sawing      ' alle Sägeschnitte
	DH_Stroke() As TDH_Stroke
	BMPName As String             ' Name des dem Fräser hinterlegten Bitmaps
	G1Bearbeitungsweg As Double              '
End Type


' Type für Bearbeitungszeiten
Type TPTime
	TotalTime As Double           ' Gesamt über alles
	ProcesstimeMillingG0 As Double ' G0 Bewegungen Fräsen
	ProcessTimeMilling As Double  ' reine Bearbeitungszeit Fräsen am Teil 
	ProcessTimeDrilling As Double ' reine Bearbeitungszeit Bohren am Teil 
	ProcessTimeDrillingG0 As Double ' Fahrten zwischen den Bohrungen
	ProcesstimeVerticalDrilling As Double ' bohrhübe vertical
	ProcesstimeVerticalDrillingG0 As Double ' bohrhübe G0
	ProcessTimeSawing As Double   ' reine Bearbeitungszeit Sägen am Teil 
	ProcesstimeSawingG0 As Double ' G0 Bewegungen Sägen
	ProcessTimeTotalG0 As Double  'alle G0 -Bewegungen
	TChangeMoveTime As Double     ' Zeit für fahrt zum Werkzeugwechsel gesamt
	TChangeTime As Double         ' Werkzeugwechselzeiten 
	ProcessChangeTime As Double   ' Wechsel zwischen den Bearbeitungen
	Tool() As TPTTool             ' Alle Werkzeug werden hier weggeschrieben
	ClampChangeTime As Double     ' MW 18.07.2014 - Zeit für umspannen gelesen aus PP.INI [PTIME] Clampchange=5 (Default 5)
	G1Bearbeitungsweg As Double              '
End Type
Global TP As TPTime


' Variablen/Konstanten für Bearbeitungszeiten
Type TTPVars
	MAXFEEDRATE_Z As Double
	MAXFEEDRATE_XY As Double
	'TIME_TC1 As Double             ' benötigte Zeit für Werkzeugwechsel mitfahrender Tellerwechsler
	'TIME_TCPICKUP As Double        ' benötigte Zeit für Werkzeugwechsel Pickup
	RANGE_XMIN As Double           ' Verfahrbereich XMin
	RANGE_XMAX As Double           ' Verfahrbereich XMax
	RANGE_YMIN As Double           ' Verfahrbereich YMin
	RANGE_YMAX As Double           ' Verfahrbereich YMax
	RANGE_ZMIN As Double           ' Verfahrbereich ZMin
	RANGE_ZMAX As Double           ' Verfahrbereich ZMax
	ConstdHCylce10 As Double       ' Konstante für Bohrzyklus 10
	ConstdHCylce20 As Double       ' Konstante für Bohrzyklus 20
	ConstdHCylce30 As Double       ' Konstante für Bohrzyklus 30
	Const_Clampchange As Double     ' Konstante für Umspannzeit - MW 18.07.2014 -gelesen aus ID 11xxxxx
	Accel_Decel_G0 As Double		'Beschleunigung/Verzögerung G0-Bewegung
	Accel_Decel_G1 As Double		'Beschleunigung/Verzögerung G1-Bewegung
	Accel_Decel_G2 As Double		'Beschleunigung/Verzögerung G2-Bewegung
End Type
Global TPVars As TTPVars


Type TTimeC_lpos
  x As Double
  y As Double
  z As Double
End Type

Global TimeC_lpos As TTimeC_lpos

Type TTimeC_TMovePara
  Feedrate As Long
End Type
Global TimeC_MovePara As TTimeC_TMovePara

Global TP_FirstTime_Viewchange As Boolean

Global TP_Drilling_Activ As Boolean

Global Empty_Prog As Boolean  ' --  MW 13.09.2007 dann alle Zeiten 0sec

Global Debug_Timecalc As Boolean


Function GET_MTM_BMP_Path
    Dim App As Object
    
    Set App = CreateObject("Hops_DLLInterface.CampusSettings")
    'Set App = CreateObject("Hops_DLLInterface.ibasicSettings")
    GET_MTM_BMP_Path= App.MTM_BMPPath 
	
	Set App= Nothing
	
	
End Function
    
'Global MillPath As Double     ' aufsammeln der Fräslänge
'Global MillTime As Double     ' aufsammeln der sekunden für die aktuelle Bearbeitung
'Global Time_complete As Double
'Global Time_TC As Double
'Global Time_TC_DH As Double
'Global Time_FirstMove As Double

Function HTML_SetFont(font)
	HTML_SetFont= "<font face="+Chr(34)+font+Chr(34)+">"
End Function

Function HTML_EndFont
	HTML_EndFont= "</font"
End Function


Function HTML_StartBody
	HTML_StartBody="<Body>"
End Function

Function HTML_EndBody
	HTML_EndBody="</Body>"
End Function

' LineFeed
Function HTML_LF
	HTML_LF="<br>"
End Function

' Neuer Absatz
Function HTML_NL
	HTML_NL="<p>"
End Function


' Spacing
Function HTML_Space(repeats)
	HTML_Space=repl("&nbsp;",repeats)
End Function

' Style bold etc.
Function HTML_SetStyle(style)
	If Len(style)>0 Then
		HTML_SetStyle="<"+style+">"
	End If
End Function

Function HTML_EndStyle(style)
	If Len(style)>0 Then
		HTML_EndStyle="</"+style+">"
	End If
End Function

Function HTML_Image(image)
	HTML_Image="<IMG SRC="+Chr(34)+image+Chr(34)+" WIDTH="+Chr(34)+"29"+Chr(34)+" HEIGHT="+Chr(34)+"30"+Chr(34)+" BORDER="+Chr(34)+"0"+Chr(34)+" ALT="+Chr(34)+Chr(34)+">"
	
End Function

Function HTML_ImageSize(image,x,y)
	'HTML_ImageSize="<IMG SRC="+Chr(34)+image+Chr(34)+" WIDTH="+Chr(34)+ftos(x)+Chr(34)+" HEIGHT="+Chr(34)+ftos(y)+Chr(34)+" BORDER="+Chr(34)+"0"+Chr(34)+" ALT="+Chr(34)+Chr(34)+">"
       HTML_ImageSize="<IMG SRC="+Chr(34)+image+Chr(34)+" WIDTH="+Chr(34)+CStr(x)+Chr(34)+" HEIGHT="+Chr(34)+CStr(y)+Chr(34)+" BORDER="+Chr(34)+"0"+Chr(34)+" ALT="+Chr(34)+Chr(34)+">"	
End Function


' Font

Function HTML_PrintFont(size,Color,style,txt,lf)
Dim cs As String
	' Color 1=black
	' color 2=blue
	' color 3=red
	
	' black
	cs="#000000"
	If Color=2 Then
		' blue	
		cs="#3300FF"
	ElseIf Color=3 Then
		' red
		cs="#FF0000"
	End If
	HTML_PrintFont="<FONT SIZE="+Chr(34)+inttos(size)+Chr(34)+ " Color="+Chr(34)+cs+Chr(34)+">"+HTML_SetStyle(style)+txt+HTML_EndStyle(style)+"</FONT>"
	If lf=1 Then
		' Absatz
	   HTML_PrintFont=HTML_PrintFont+HTML_NL
	End If
	If lf=2 Then
		' Zeilenumbruch
	   HTML_PrintFont=HTML_PrintFont+HTML_LF
	End If
End Function

Function HTML_HRuler
	HTML_HRuler="<HR>"
End Function

' wird von Sub INIT_plausi aufgerufen
Function TPToolInit
Dim count As Long
	
    Const ID_DebugTimecalc=111111
    Dim addi As Object 
    Dim striVari As Variant

    ' Debug-Info aus der Maschinenkonfiguration lesen
    ' -- JS 03.05.2017
    Set addi=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(ID_DebugTimecalc)
	If  Not addi Is Nothing Then
		striVari=addi.Value 
        If Int(striVari)>0 Then
            Debug_Timecalc = True
        Else
            Debug_Timecalc = False
        End If
    Else
        Debug_Timecalc = False
	End If
	Set addi=Nothing
    
    If Debug_Timecalc=True Then
        Open "C:\temp\debug_timecalc.txt" For Output As #4
	End If
    
	ReDim TP.Tool(0)
	
	FloatFormat="0"
	TP_FirstTime_Viewchange=True
	
	
	
	' Konstanten Einlesen
	TimeC_ReadINI
	
	' letzte Position der Maschine
	TimeC_lpos.X=1500
	TimeC_lpos.Y=1500
	TimeC_lpos.Z=480
  

  
	
End Function

Function TimeC_ReadINI
Dim dummy As Variant
Dim striVari As Variant
Dim addi As Object 

Const ID_ConstdHCycle10=100000
Const ID_ConstdHCycle20=100001
Const ID_ConstdHCycle30=100002

Const ID_MaxFeedrate_Z=100005
Const ID_MaxFeedrate_XY=100006

Const ID_Accel_Decel_G0=120000
Const ID_Accel_Decel_G1=120001
Const ID_Accel_Decel_G2=120002

	' Maximaler Z-Vorschub etc. aus ini lesen
	' -- 
	' --  MW 19.07.2007 13:02:19
	' --  aus MT-Manager Data lesen 
	' --------------------------------------------------------------------------------------------

	' Zeit in sek für Bohrzyklus 10
	' --------------------------------------------------------------------------------------------
	Set addi=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(ID_ConstdHCycle10)
	If  Not addi Is Nothing Then
		striVari=addi.Value 
		AddHint("ID"+inttos(ID_ConstdHCycle10)+" = "+striVari)
	Else
		ReadStrPP_ini("PTime","ConstdHCycle10","0.3",striVari)
	End If
	Set addi=Nothing
	TPVars.ConstdHCylce10 = StrToFloat(striVari)       
	' --------------------------------------------------------------------------------------------
	
	
	' Zeit in sek für Bohrzyklus 20
	' --------------------------------------------------------------------------------------------
	Set addi=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(ID_ConstdHCycle20)
	If  Not addi Is Nothing Then
		striVari=addi.Value 
		AddHint("ID"+inttos(ID_ConstdHCycle20)+" = "+striVari)
	Else
		ReadStrPP_ini("PTime","ConstdHCycle20","0.7",striVari)
	End If
	Set addi=Nothing
	TPVars.ConstdHCylce20 = StrToFloat(striVari)       

	' --------------------------------------------------------------------------------------------

	' Zeit in sek für Bohrzyklus 30
	' --------------------------------------------------------------------------------------------
	Set addi=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(ID_ConstdHCycle30)
	If  Not addi Is Nothing Then
		striVari=addi.Value 
		AddHint("ID"+inttos(ID_ConstdHCycle30)+" = "+striVari)
	Else
		ReadStrPP_ini("PTime","ConstdHCycle30","1.0",striVari)
	End If
	Set addi=Nothing
	
	TPVars.ConstdHCylce30 = StrToFloat(striVari)       
	
	' --------------------------------------------------------------------------------------------

	Set addi=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(ID_MaxFeedrate_Z)
	If  Not addi Is Nothing Then
		striVari=addi.Value 
		AddHint("ID"+inttos(ID_MaxFeedrate_Z)+" = "+striVari)
	Else
		ReadStrPP_ini("PTime","MAXFEEDRATE_Z","30000",striVari)
	End If
	Set addi=Nothing
	TPVars.MAXFEEDRATE_Z = StrToFloat(striVari)
	' --------------------------------------------------------------------------------------------
	
	' Maximaler XY-Vorschub aus ini lesen
	' --------------------------------------------------------------------------------------------
	Set addi=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(ID_MaxFeedrate_XY)
	If  Not addi Is Nothing Then
		striVari=addi.Value 
		AddHint("ID"+inttos(ID_MaxFeedrate_XY)+" = "+striVari)
	Else
		ReadStrPP_ini("PTime","MAXFEEDRATE_XY","20000",striVari)
	End If
	Set addi=Nothing
		
	TPVars.MAXFEEDRATE_XY = StrToFloat(striVari)
	' --------------------------------------------------------------------------------------------
	' Beschleunigungs/Verzögerungswerte aus ini lesen
	'JS 20.10.2016
	' --------------------------------------------------------------------------------------------
	Set addi=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(ID_Accel_Decel_G0)
	If  Not addi Is Nothing Then
		striVari=addi.Value 
		AddHint("ID"+inttos(ID_Accel_Decel_G0)+" = "+striVari)
	Else
		ReadStrPP_ini("PTime","Accel_Decel_G0","20000",striVari)
	End If
	Set addi=Nothing
	TPVars.Accel_Decel_G0 = StrToFloat(striVari)
	
	Set addi=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(ID_Accel_Decel_G1)
	If  Not addi Is Nothing Then
		striVari=addi.Value 
		AddHint("ID"+inttos(ID_Accel_Decel_G1)+" = "+striVari)
	Else
		ReadStrPP_ini("PTime","Accel_Decel_G1","20000",striVari)
	End If
	Set addi=Nothing		
	TPVars.Accel_Decel_G1 = StrToFloat(striVari)
	
	Set addi=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(ID_Accel_Decel_G2)
	If  Not addi Is Nothing Then
		striVari=addi.Value 
		AddHint("ID"+inttos(ID_Accel_Decel_G2)+" = "+striVari)
	Else
		ReadStrPP_ini("PTime","Accel_Decel_G2","20000",striVari)
	End If
	Set addi=Nothing		
	TPVars.Accel_Decel_G2 = StrToFloat(striVari)

	
	' --------------------------------------------------------------------------------------------	
    ' MW 18.07.2014
	striVari= Read_TC_TimeConst_MT("CLAMPCHANGE")
	If IsNumeric(striVari) Then
	    TPVars.Const_Clampchange = StrToFloat(striVari)
	Else
    	TPVars.Const_Clampchange=30
    End If
    

End Function

Function TPTool_ViewChange(x,y,z)
Dim ct As Long
Dim movepath As Double
	abso(x,y,z)
	ct = UBound(TP.Tool) 

    ' Ermittlung G0 Anfahrt auf 1. Bearbeitungsposition
    If TP_FirstTime_Viewchange Then
    	' 1. Anfahrt aufs Werkstück ohne Z
		movepath = LZWIPU(x,y,TimeC_lpos.X,TimeC_lpos.Y)
        If Debug_Timecalc=True Then
            Print #4, "################################################################################"
            Print #4, "1. Anfahrt aufs Werkstück ohne Z: " ;movepath#
        End If
		'TP.Tool(ct).G0_Time = TP.Tool(ct).G0_Time + GetTimePath(movepath,TPVars.MAXFEEDRATE_XY)  ' Anfahrweg auf Startpunkt
		TP.Tool(ct).G0_Time = TP.Tool(ct).G0_Time + GetTimePathAccelerationDeceleration(movepath,TPVars.MAXFEEDRATE_XY,TPVars.Accel_Decel_G0,TPVars.Accel_Decel_G0)  ' Anfahrweg auf Startpunkt
		TimeC_PosSet(x,y,TimeC_lpos.Z)
		
		movepath = LZWIPU3d(x,y,z,TimeC_lpos.X,TimeC_lpos.Y,TimeC_lpos.Z)
        If Debug_Timecalc=True Then
            Print #4, "################################################################################"
            Print #4, "1. Anfahrt aufs Werkstück: " ;movepath#
        End If
		'TP.Tool(ct).G0_Time = TP.Tool(ct).G0_Time + GetTimePath(movepath,TPVars.MAXFEEDRATE_XY)  ' Anfahrweg auf Startpunkt
		TP.Tool(ct).G0_Time = TP.Tool(ct).G0_Time + GetTimePathAccelerationDeceleration(movepath,TPVars.MAXFEEDRATE_XY,TPVars.Accel_Decel_G0,TPVars.Accel_Decel_G0)  ' Anfahrweg auf Startpunkt
		TP_FirstTime_Viewchange=False
    Else
		movepath = LZWIPU3d(x,y,z,TimeC_lpos.X,TimeC_lpos.Y,TimeC_lpos.Z)
        If Debug_Timecalc=True Then
            Print #4, "################################################################################"
            Print #4, "1. Anfahrt aufs Werkstück: " ;movepath#
        End If
		'TP.Tool(ct).G0_Time = TP.Tool(ct).G0_Time + GetTimePath(movepath,TPVars.MAXFEEDRATE_XY)  ' Anfahrweg auf Startpunkt
		TP.Tool(ct).G0_Time = TP.Tool(ct).G0_Time + GetTimePathAccelerationDeceleration(movepath,TPVars.MAXFEEDRATE_XY,TPVars.Accel_Decel_G0,TPVars.Accel_Decel_G0)  ' Anfahrweg auf Startpunkt
	End If
	
	TimeC_PosSet(x,y,z)

	
End Function

' wird von Sub ToolChange_plausi aufgerufen
Function TPToolChange(t As THopsBasicToolExt)
Dim IITCHead As Object ' IIToolChangerHead

Dim count As Long
Dim movepath As Double

	ActT = t

	MT_Get_RangeXYZ(ACTT,TPVars.RANGE_XMIN,TPVars.RANGE_XMAX,TPVars.RANGE_YMIN, _
	               TPVars.RANGE_YMAX,TPVars.RANGE_ZMIN,TPVars.RANGE_ZMAX)

	' ToolCount hochzählen
	count = UBound(TP.Tool) + 1

	ReDim Preserve TP.Tool(count)
	ReDim TP.Tool(count).K(0)

	TP.Tool(count).HeadID=P_Head
	TP.Tool(count).ToolID=t.t.ID
	TP.Tool(count).ToolName=t.t.Description
	If MT_IsDH(actt) Then
		'TP.Tool(count).BMPName = "drill_01_32.bmp"
		'TP.Tool(count).BMPName = "Tools\drillhead.bmp"
		'TP.Tool(count).BMPName = "Tools\Hops_DH_Drill_Vert_1.bmp"
		TP.Tool(count).BMPName= actt.t_dh.DrillingHead.Picture
	Else
		TP.Tool(count).BMPName = t.t.Picture
	End If
	
	If MT_Is_TC_T(ActT) Then
		' Werkzeug auf Wechsler
		' Werkzeug auf Wechsler
		Set IITCHead = ActT.t.GetOn_TC
		TP.Tool(count).ISTCTool = True     ' Werkzeug auf Wechsler
		TP.Tool(count).TCPlace=	ActT.t.GetPlaceID_OnTC	-1	
		' Werkzeugwechsler - Object wegschreiben
		'Aebderung 2007-01-30 Nur erste xStellen auswerten
		TP.Tool(count).TCType = CLng(Left$(CStr(IITCHead.ChangerType),WZWTypMask))
		'MsgBox CStr(TP.Tool(count).TCType) 
		TP.Tool(count).TCCenterX = IITCHead.CenterX
		TP.Tool(count).TCCenterY = IITCHead.CenterY
		TP.Tool(count).TCCenterZ = IITCHead.CenterZ
		If TP.Tool(count).TCType=7996 Then
			' Tellerwechsler Wechselposition holen X-Pos = letzte pos, da mitfahrend
			TP.Tool(count).TCCenterX=TimeC_lpos.X
			
			' Referenz - Werkzeugwechselplatz auf mitfahrendem Wechsler = 0
			' also immer der 1. Wechselplatz
			TP.Tool(count).TCPlace=0
			
			' Y-Pos absolut auf Maschinennull bezogen
			
			
			TP.Tool(count).TCCenterY=TP.Tool(count).TCCenterY + _
              (IITCHead.ToolPlaces.GetToolPlace_Index(TP.Tool(count).TCPlace).OffsetY  *Cos(IITCHead.ToolPlaces.GetToolPlace_Index(TP.Tool(count).TCPlace).RotAngle))
			         
			' jetzt Zeit für den tatsächlichen Werkzeugwechsel aus Konstante für Tellerwechsler
			TP.Tool(count).TChangeTime = TP.Tool(count).TChangeTime + GetConst_TCTime  ' TPVars.TIME_TC1
		Else
			' Werkzeugwechsel fix montiert z.B. Pickup
			
			
			' -- 
			' tatsächlichen Werkzeugwechselplatz holen!!
			' --
			' -- Modified  MW 24.09.2008 11:40:18
			' --
			' -- über die PlatzNummer den Wechselplatz holen - um zu bestimmen wo z.B. der Pickup-Platz sitzt
			
			TP.Tool(count).TCPlace= TP_GET_TC_PLACE(t)
			
			
			' X-Pos Wechsler absolut auf Maschinennull bezogen
			TP.Tool(count).TCCenterX=TP.Tool(count).TCCenterX + _
			  IITCHead.ToolPlaces.GetToolPlace_Index(TP.Tool(count).TCPlace).OffsetX 
			
			' Y-Pos Wechsler absolut auf Maschinennull bezogen
			TP.Tool(count).TCCenterY=TP.Tool(count).TCCenterY + _
			  IITCHead.ToolPlaces.GetToolPlace_Index(TP.Tool(count).TCPlace).OffsetY 
			         
			' jetzt Zeit für den tatsächlichen Werkzeugwechsel aus Konstante für Tellerwechsler
			TP.Tool(count).TChangeTime = TP.Tool(count).TChangeTime + GetConst_TCTime   'TPVars.TIME_TCPICKUP
		End If
		
		' --
		' jetzt Zeit ermitteln für die Fahrt zum Werkzeugwechsler
		' --
	    movepath = LZWIPU(TP.Tool(count).TCCenterX,TP.Tool(count).TCCenterY,TimeC_lpos.X,TimeC_lpos.Y)
		TP.Tool(count).TChangeMoveTime = TP.Tool(count).TChangeMoveTime + GetTimePath(movepath,TPVars.MAXFEEDRATE_XY)
		' --
		
		' --
		' last position setzen damit nächste Anfahrt richtig berrechnet wird
		' --
		TimeC_PosSet(TP.Tool(count).TCCenterX,TP.Tool(count).TCCenterY,TPVars.RANGE_ZMAX)	


	Else
		TP.Tool(count).ISTCTool = False     ' Werkzeug nicht auf Wechsler
		TP.Tool(count).TChangeMoveTime = 0
		'TP.Tool(count).TChangeTime = 0
		TP.Tool(count).TChangeTime = TP.Tool(count).TChangeTime + GetConst_TCTime   'TPVars.TIME_TCPICKUP
End If

	
End Function

' wird von Sub StartMilling aufgerufen
Function TPTool_SP_Set(x,y,z)
Dim ct As Long
Dim ck As Long
	
	ct = UBound(TP.Tool) 
	' Contur - Count hochzählen
	ck = UBound(TP.Tool(ct).K) + 1
	ReDim Preserve TP.Tool(ct).K(ck)
	ReDim TP.Tool(ct).K(ck).K_P(0)
	
	TP.Tool(ct).K(ck).SP.X=x
	TP.Tool(ct).K(ck).SP.Y=y
	TP.Tool(ct).K(ck).SP.Z=z
	
End Function

' wird von Sub Start_vertikal_drillingheadstroke aufgerufen
Function TPTool_VDH_Stroke_Set
Dim ct As Long
Dim ck As Long

	ct = UBound(TP.Tool) 
	' Stroke - Count initialisieren
	ReDim TP.Tool(ct).DH_Stroke(1)
	TP.Tool(ct).is_dh_drilling = True

	
End Function



' wird von Sub vertikal_drillingheadstroke aufgerufen
Function TPTool_DHStroke_Set(x,y,DZ,Depth,tools,DFlag_TypeString)	
Dim dh_c As Long
Dim ct As Long
Dim movepath As Double
Dim DFlag As Long
Dim zmax As Double

	abso(x,y,DZ)   ' umrechnung auf Maschinenkoordinatensystem
	
	ct = UBound(TP.Tool)  ' momentanes Werkzeug

	' Bohrhub - Zähler hochzählen
	dh_c = UBound(TP.Tool(ct).DH_Stroke) + 1
	ReDim Preserve TP.Tool(ct).DH_Stroke(dh_c)
	TP.Tool(ct).DH_Stroke(dh_c).X=x
	TP.Tool(ct).DH_Stroke(dh_c).Y=y
	TP.Tool(ct).DH_Stroke(dh_c).Depth=Depth

	' setzen der Vorschübe für die Bohrhub

	MT_SetDrillingHeadData(tools,TP.Tool(ct).DH_Stroke(dh_c).dh,TP.Tool(ct).DH_Stroke(dh_c).Driller)
	' Bitmap - Data überschreiben, da Bohrkopf ja keine Bitmap hat
'	TP.Tool(ct).BMPName = t.t.Picture

	MoveTime_Result=0
	
	
    If dh_c = 2 Then
		' Anfahrt auf Bohrung
		movepath = LZWIPU(x,y,TimeC_lpos.X,TimeC_lpos.Y)
		'TP.Tool(ct).DH_Stroke(dh_c).G0Time = TP.Tool(ct).DH_Stroke(dh_c).G0Time + GetTimePath(movepath,TPVars.MAXFEEDRATE_XY)
		TP.Tool(ct).DH_Stroke(dh_c).G0Time = TP.Tool(ct).DH_Stroke(dh_c).G0Time + GetTimePathAccelerationDeceleration(movepath,TPVars.MAXFEEDRATE_XY,TPVars.Accel_Decel_G0,TPVars.Accel_Decel_G0)
		TimeC_PosSet(x,y,Depth)

	End If
	
	' Simulieren des Bohrzyklus
	DFlag = Val(Get_First_Token(DFlag_TypeString))
	
	' Neu MW 25. Juli 2005
	zmax=GetZMax(DFlag Mod 10,Depth)

	If (DFlag >19) And (DFlag<30) Then
		' Bohrzyklus Durchgangsloch bohren
		Drilling_DH_Cylce_20(x,y,Depth,ActT.t_dh.GetSecurityZ(0),TP.Tool(ct).DH_Stroke(dh_c).Driller,TP.Tool(ct).DH_Stroke(dh_c).dh,tools,zmax)
		MoveTime_Result = MoveTime_Result + TPVars.ConstdHCylce20
	ElseIf (DFlag >29) And (DFlag<40) Then
		' Bohrzyklus Topfband mit Verweilzeit bohren
		Drilling_DH_Cylce_30(x,y,Depth,ActT.t_dh.GetSecurityZ(0),TP.Tool(ct).DH_Stroke(dh_c).Driller,TP.Tool(ct).DH_Stroke(dh_c).dh,tools,zmax)
		MoveTime_Result = MoveTime_Result + TPVars.ConstdHCylce30
	Else
		'If (DFlag >9) And (DFlag<20) Then
		' Bohrzyklus Sackloch bohren
		Drilling_DH_Cylce_10(x,y,Depth,ActT.t_dh.GetSecurityZ(0),TP.Tool(ct).DH_Stroke(dh_c).Driller,TP.Tool(ct).DH_Stroke(dh_c).dh,tools,zmax)
		MoveTime_Result = MoveTime_Result + TPVars.ConstdHCylce10
	End If
	
	TP.Tool(ct).DH_Stroke(dh_c).StrokeTime = MoveTime_Result
	MoveTime_Result=0
End Function


' wird von Sub EndMilling aufgerufen
Function TPTool_EP_Set
Dim ct As Long
Dim ck As Long
Dim cks As Long
	
	ct = UBound(TP.Tool) 
	ck = UBound(TP.Tool(ct).K)
	cks = UBound(TP.Tool(ct).K(ck).K_P)
	

	'MsgBox("Tool"+TP.Tool(ct).ToolName+"T:"+Str(ct)+" KonturNummer:"+Str(ck)+" KP'S:"+Str(cks) )
	
End Function


' wird von Sub G00 aufgerufen
Function TPTool_G00_Set(ByVal x,ByVal y,ByVal z,ByVal f)
	abso(x,y,z)

	f = MT_CheckFeedrate(ActT,0,0,0,0,0,0,f)
	
	Next_CPoint 

	TP_SetContourPoint(x,y,z,-99999,-99999,f,0)
	
End Function

' wird von Sub G00 aufgerufen
Function TPTool_G01_Set(ByVal x,ByVal y,ByVal z,ByVal f)
	abso(x,y,z)
	f = MT_CheckFeedrate(ActT,0,0,0,0,0,0,f)
	
	Next_CPoint 

	TP_SetContourPoint(x,y,z,-99999,-99999,f,1)
	
End Function


' wird von Sub G02 aufgerufen
Function TPTool_G02_Set(x,y,z,i,j,f)
	abso(x,y,z)
	i=absox(i)
	j=absoy(j)
	f = MT_CheckFeedrate(ActT,0,0,0,0,0,0,f)
	Next_CPoint 
	

	TP_SetContourPoint(x,y,z,i,j,f,2)
	
End Function

' wird von Sub G03 aufgerufen
Function TPTool_G03_Set(x,y,z,i,j,f)
	abso(x,y,z)
	i=absox(i)
	j=absoy(j)
	f = MT_CheckFeedrate(ActT,0,0,0,0,0,0,f)

	Next_CPoint 

	TP_SetContourPoint(x,y,z,i,j,f,3)
	
End Function



Function TimeC_StartMill(PPAX,PPAY,PPAZ)
	abso(PPAX,PPAY,PPAZ)
   	TimeC_StartMove(TimeC_lpos.X,TimeC_lpos.Y,PPAX,PPAY)
   	TimeC_MoveParaReset
    TimeC_PosSet(PPAX,PPAY,PPAZ)
	
End Function

Function TimeC_StartDrill(ByVal PPAX,ByVal PPAY,ByVal PPAZ)
	abso(PPAX,PPAY,PPAZ)
   	TimeC_StartMove(TimeC_lpos.X,TimeC_lpos.Y,PPAX,PPAY)
   	TimeC_MoveParaReset
    TimeC_PosSet(PPAX,PPAY,PPAZ)
	
End Function


Function TimeC_Sawing(sx,sy,sz,ex,ey,ez)
Dim dh_c,ct As Long
Dim start_x,start_y,start_z As Double
    start_x=ActV.SPVX
    start_y=ActV.SPVY
    start_z=ActV.SPVZ
	abso(start_x,start_y,start_z)

	abso(sx,sy,sz)
	abso(ex,ey,ez)
	ct = UBound(TP.Tool)  ' momentanes Werkzeug
	If Not TP.Tool(ct).is_sawing = True Then 
		' initialisiern
		ReDim Preserve TP.Tool(ct).TP_Sawing(0)

	End If

 	' Sägeschnitte hochzählen
	dh_c = UBound(TP.Tool(ct).TP_Sawing) + 1
	ReDim Preserve TP.Tool(ct).TP_Sawing(dh_c)
	
	TP.Tool(ct).is_sawing = True
	TP.Tool(ct).TP_Sawing(dh_c).SX=sx
	TP.Tool(ct).TP_Sawing(dh_c).SY=sy
	TP.Tool(ct).TP_Sawing(dh_c).SZ=sz
	TP.Tool(ct).TP_Sawing(dh_c).EX=ex
	TP.Tool(ct).TP_Sawing(dh_c).EY=ey
	TP.Tool(ct).TP_Sawing(dh_c).EZ=ez
	
	'TP.Tool(ct).TP_Sawing(dh_c).G0Time=GetTimePath(LZWIPU3d(TimeC_lpos.X,TimeC_lpos.Y,TimeC_lpos.Z,start_x,start_y,start_z),TPVars.MAXFEEDRATE_XY)
	TP.Tool(ct).TP_Sawing(dh_c).G0Time=GetTimePathAccelerationDeceleration(LZWIPU3d(TimeC_lpos.X,TimeC_lpos.Y,TimeC_lpos.Z,start_x,start_y,start_z),TPVars.MAXFEEDRATE_XY,TPVars.Accel_Decel_G0,TPVars.Accel_Decel_G0)
	TimeC_PosSet(start_x,start_y,start_z)
	TP.Tool(ct).TP_Sawing(dh_c).SawTime=GetTimePath(LZWIPU(TimeC_lpos.X,TimeC_lpos.Z,sx,ez),ProcessPara.I_Feedrate)
	TimeC_PosSet(sx,TimeC_lpos.Y,ez)
	' Zustellen
	TP.Tool(ct).TP_Sawing(dh_c).SawTime=TP.Tool(ct).TP_Sawing(dh_c).SawTime+ _
	        GetTimePath(LZWIPU(TimeC_lpos.X,TimeC_lpos.Z,sx,ez),ProcessPara.I_Feedrate)
	TimeC_PosSet(sx,TimeC_lpos.Y,ez)
	' Sägeschnitt selbst
	
	'TP.Tool(ct).TP_Sawing(dh_c).SawTime=TP.Tool(ct).TP_Sawing(dh_c).SawTime+ _
	'        GetTimePath(LZWIPU(TimeC_lpos.X,TimeC_lpos.Z,ex,ez),ProcessPara.Feedrate)
	
	' 
	TP.Tool(ct).TP_Sawing(dh_c).SawTime=TP.Tool(ct).TP_Sawing(dh_c).SawTime+ _
	        GetTimePath(LZWIPU3d(TimeC_lpos.X,TimeC_lpos.Y,TimeC_lpos.Z,ex,ey,ez),ProcessPara.Feedrate)
	TimeC_PosSet(ex,TimeC_lpos.Y,ez)
	' hoch
	TP.Tool(ct).TP_Sawing(dh_c).SawTime=TP.Tool(ct).TP_Sawing(dh_c).SawTime+ _
	        GetTimePath(LZWIPU(TimeC_lpos.X,TimeC_lpos.Z,ex,sz),ProcessPara.Feedrate)
End Function


Function TimeC_PosSet(x,y,z)

  TimeC_lpos.X=x
  TimeC_lpos.Y=y
  TimeC_lpos.Z=z
End Function


Function TimeC_StartMove(xa,ya,xe,ye) As Double
Dim ct,ck As Long
Dim movepath As Double

ct = UBound(TP.Tool)  ' momentanes Werkzeug
ck = UBound(TP.Tool(ct).K)  ' momentane Kontur

' Ermittlung G0 Anfahrt auf nächste Bearbeitungsposition
	movepath = LZWIPU(xa,ya,xe,ye)
	'TP.Time_FirstMovePart = GetTimePath(movepath,TPVars.MAXFEEDRATE_XY)
	'TP.Tool(ct).K(ck).G0_Time = GetTimePath(movepath,TPVars.MAXFEEDRATE_XY)  ' Anfahrweg auf Startpunkt
	TP.Tool(ct).K(ck).G0_Time = GetTimePathAccelerationDeceleration(movepath,TPVars.MAXFEEDRATE_XY,TPVars.Accel_Decel_G0,TPVars.Accel_Decel_G0)  ' Anfahrweg auf Startpunkt
End Function




'Reset the moveparameter to an impossible value
Sub TimeC_MoveParaReset
  TimeC_MovePara.Feedrate=-99999
End Sub



Function GetTimePath(weg,vorschub)
Dim zeit As Double
    If vorschub<=0 Then 
       vorschub=1
    End If
	zeit = weg / (vorschub/60)
	GetTimePath	= zeit
End Function

Function Next_CPoint 
Dim ct,ck,cks As Long

	' Contur Stützpunkt - Count hochzählen
	ct = UBound(TP.Tool) 
	ck = UBound(TP.Tool(ct).K)
	
	' Konturstützpunkt - Zäler hochsetzen
	cks = UBound(TP.Tool(ct).K(ck).K_P) + 1
	ReDim Preserve TP.Tool(ct).K(ck).K_P(cks)
	
End Function


Function TP_SetContourPoint(x,y,z,i,j,f,dr)
Dim id As Integer
Dim ct,ck,cks As Long
	ct = UBound(TP.Tool) 
	' Konturanzahl
	ck = UBound(TP.Tool(ct).K) 
	' Konturstützpunkt
	cks = UBound(TP.Tool(ct).K(ck).K_P)

	TP.Tool(ct).K(ck).K_P(cks).p.X=x
	TP.Tool(ct).K(ck).K_P(cks).p.Y=y
	TP.Tool(ct).K(ck).K_P(cks).p.Z=z

	TP.Tool(ct).K(ck).K_P(cks).i=i
	TP.Tool(ct).K(ck).K_P(cks).j=j
	
	' Feedrate
	TP.Tool(ct).K(ck).K_P(cks).f=f
	
	' Drehrichtung Kreisbogen
	TP.Tool(ct).K(ck).K_P(cks).dr=dr
	TimeC_PosSet(x,y,z)	
	
End Function

' Gesamt - Total zeit
' -----------------------------------------------------------
Function TP_GetTotalTime As Double

TP_GetTotalTime =TP.ProcessTimeMilling + _
                 TP.ProcesstimeVerticalDrilling + _
                 TP.ProcesstimeVerticalDrillingG0 + _
	             TP.TChangeMoveTime + _
	             TP.TChangeTime + _
	             TP.ProcessTimeSawing + _
	             TP_GetTotalG0_Time + _
	             TP.ClampChangeTime
	
End Function

' tatsächliche Bearbeitungszeit
Function TP_GetTotalProcessTime As Double

TP_GetTotalProcessTime =TP.ProcessTimeMilling + _
                 TP.ProcesstimeVerticalDrilling + _
	             TP.ProcessTimeSawing 
	
End Function

' gesamt Werkzeugwechselzeiten
Function TP_GetTotalTCTime
	TP_GetTotalTCTime = TP.TChangeTime	
End Function

' gesamt fahrt für Werkzeugwechsel
Function TP_GetTotalTCMoveTime
	TP_GetTotalTCMoveTime = TP.TChangeMoveTime
End Function


' gesamt BearbeitungswechselZeiten
'Function TP_GetTotalProcessChangeTime
'	TP_GetTotalProcessChangeTime = TP.ProcesstimeMillingG0 + _
'	                               TP.ProcesstimeSawingG0 + _
'	                               TP.ProcesstimeVerticalDrillingG0
'End Function

' gesamt Summe Eilgänge
Function TP_GetTotalG0_Time

	TP_GetTotalG0_Time = TP.ProcessTimeTotalG0
	
End Function


' Gesamt - Total zeit des Werkzeugs
Function TP_GetTotalTimeTool(Tool As TPTTool) As Double

TP_GetTotalTimeTool =TP.ProcessTimeMilling + _
                 TP.ProcesstimeVerticalDrilling + _
                 TP.ProcesstimeVerticalDrillingG0 + _
	             TP.TChangeMoveTime + _
	             TP.TChangeTime + _
	             TP.ProcessTimeSawing + _
	             TP_GetTotalG0_Time
	
End Function

' Einsatzzeiten nach Werkzeug
Function TP_PRINT_HEADER
Dim wName,bmp,wmf As String
Dim id As Long

Const distance =40
Dim ProcessTime As Double
Dim i As Long
Exit Function
    Print #1,HTML_StartBody
    Print #1,HTML_SetFont("Courier New Fett, Courier, Courier New, Arial, Palatino Linotype, Comic")
	Print #1,HTML_LF
	'Print #1,HTML_PrintFont(5,0,"B", "Einsatzzeiten nach Werkzeug",1)
	'Print #1,HTML_LF
	'Print #1,HTML_PrintFont(3,0,"B","Werkzeug:"+HTML_Space(distance+5-Len("Werkzeug:"))+"Dauer",1)
	'Print #1,HTML_LF
	
	'XML-Abschnitt 2007-05-25 KRI
	Print #2,"<ToolData>"	    

	For i = 1 To UBound(WPI) -1
		' alle Werkstücke durchgehen
		'Print #1,HTML_LF
		
		' Bitmap darstellen
		wName = WPI(i).WPName
		'Print #1,HTML_HRuler	
		Print #1,HTML_LF
		bmp=Replace(UCase(wName),".HOP",".bmp")
		wmf=Replace(UCase(wName),".HOP",".WMF")
		Print #1,HTML_PrintFont(3,2,"B",wName,0 )
		If FileExist(bmp) Then
			Print #1,HTML_ImageSize(bmp,400,400)
		End If
		If FileExist(wmf) Then
			Print #1,HTML_ImageSize(wmf,400,400)
		End If

		'Print #1,HTML_Image(GET_MTM_BMP_Path+TP.Tool(i).BMPName)
		
		'Print #1,HTML_PrintFont(3,3,"",MinSek(ProcessTime),1)

        	'XML-Abschnitt 2007-05-25 KRI
		Print #2,"    <tool"	    
		Print #2,"      Number="+Chr(34)+inttos(i)+Chr(34)
		Print #2,"      Id="+Chr(34) + inttos(id)+Chr(34)
		Print #2,"      Graphic="+Chr(34) + GET_MTM_BMP_Path+TP.Tool(i).BMPName+Chr(34)
		Print #2,"      Caption="+Chr(34) + TP.Tool(i).ToolName+Chr(34)
		Print #2,"      Time="+Chr(34) + CStr(ProcessTime)+Chr(34)
		If TP.Tool(i).G1Bearbeitungsweg>0 Then
			Print #2,"      Distance="+Chr(34) + CStr(TP.Tool(i).G1Bearbeitungsweg) +Chr(34)
		Else
			Print #2,"      Distance="+Chr(34)+Chr(34)
		End If
		Print #2,"     >"
		Print #2,"    </tool>"
		
	Next i
	
	'Print #1,HTML_LF
	'Print #1,HTML_HRuler	
	
	'XML-Abschnitt 2007-05-25 KRI
       Print #2,"</ToolData>"	    
	XML_Main_End

	
End Function


Function TP_PRINT_TOTALPROCESSTIME
Dim vers As Variant
Const distance =44
	GetVersion5(vers)

    Print #1,HTML_StartBody
    'Print #1,HTML_SetFont("Comic Sans MS")
    Print #1,HTML_SetFont("Courier New Fett, Courier, Courier New, Arial, Palatino Linotype, Comic")
	Print #1,HTML_LF
	Print #1,HTML_PrintFont(1,0,"F", PostSettings.DefaultPPBasName+" m:"+TDATA.ActMachineName+" Post: "+vers+" Script: "+SCRIPTVERSION,2)
	Print #1,HTML_LF
	
	
	
	Print #1,HTML_PrintFont(5,0,"B", "Summe Bearbeitungszeiten/machining time",2)
	Print #1,HTML_PrintFont(2,0,"F", "* annähernde Berechnung, alle Angaben ohne Gewähr",2)
	Print #1,HTML_PrintFont(2,0,"F", "* expected times, no guarantee for this calculation",2)
	Print #1,HTML_HRuler	
	Print #1,HTML_LF
	Print #1,HTML_PrintFont(3,0,"B","Beschreibung/Description:"+HTML_Space(distance-Len("Beschreibung/Description"))+"Dauer/time",1)
'	Print #1,HTML_LF
	Print #1,HTML_PrintFont(3,3,"B","Gesamtzeit:"+HTML_Space(distance-Len("Gesamtzeit:"))+MinSek(TP_GetTotalTime),2)
	Print #1,HTML_PrintFont(3,3,"B","(total time)",1)


'	Print #1,HTML_LF
	Print #1,HTML_PrintFont(3,0,"B","Summe Bearbeitungszeiten:"+HTML_Space(distance-Len("Summe Bearbeitungszeiten:"))+MinSek(TP_GetTotalProcessTime),2)
	Print #1,HTML_PrintFont(3,0,"B","(total processing time)",1)
	
	Print #1,HTML_PrintFont(3,0,"B","Summe Werkzeugwechselzeiten:"+HTML_Space(distance-Len("Summe Werkzeugwechselzeiten:"))+MinSek(TP_GetTotalTCTime+TP_GetTotalTCMoveTime),2)
	Print #1,HTML_PrintFont(3,0,"B","(total toolchange)",1)
	
    If TP.ClampChangeTime>0 Then
		' MW 18.07.2014
		Print #1,HTML_PrintFont(3,0,"B","Summe Umspannzeiten:"+HTML_Space(distance-Len("Summe Umspannzeiten:"))+MinSek(TP.ClampChangeTime),2)
		Print #1,HTML_PrintFont(3,0,"B","(total clampchange time)",1)
	End If
	
	
	'Print #1,HTML_LF
	'Print #1,HTML_PrintFont(3,0,"B","Summe Bearbeitungswechsel:"+HTML_Space(distance-Len("Summe Bearbeitungswechsel:"))+MinSek(TP_GetTotalProcessChangeTime),1)
	
	'Print #1,HTML_LF
	Print #1,HTML_PrintFont(3,0,"B","Summe Eilgänge:"+HTML_Space(distance-Len("Summe Eilgänge:"))+MinSek(TP_GetTotalG0_Time),2)
	Print #1,HTML_PrintFont(3,0,"B","(total G0)",1)
	Print #1,HTML_PrintFont(3,0,"B","Summe Prozesswege:"+HTML_Space(distance-Len("Summe Prozesswege:"))+MMinM(TP.G1Bearbeitungsweg),2)
	Print #1,HTML_PrintFont(3,0,"B","(total G1/G2 process)",1)
	Print #1,HTML_LF

	Print #1,HTML_HRuler	
	
	Print #1,HTML_EndFont
	Print #1,HTML_LF
	
	'XML-Abschnitt 2007-05-25 KRI
       XML_Main_Begin
       XML_DokHeader_Begin
       Print #2," <Total" 
       Print #2," TotalTime="+Chr(34)+Str(TP_GetTotalTime)+Chr(34)
       Print #2," >"
       Print #2," </Total>" 
       Print #2," <Section" 
       Print #2,"  ProcessTime=" +Chr(34)+ Str(TP_GetTotalProcessTime)+Chr(34)
       Print #2,"  ToolchangeTime="+Chr(34) + Str((TP_GetTotalTCTime+TP_GetTotalTCMoveTime))+Chr(34)
       Print #2,"  RapidTime="+Chr(34) + Str(TP_GetTotalG0_Time)+Chr(34)
       If TP.ClampChangeTime>0 Then
	       Print #2,"  Clampchange="+Chr(34) + Str(TP.ClampChangeTime)+Chr(34)
	   End If
	   If TP.G1Bearbeitungsweg>0 then
	       Print #2,"  Distance="+Chr(34) + Str(TP.G1Bearbeitungsweg)+Chr(34)   
	   End If
       Print #2," >"
       Print #2," </Section>" 
       XML_DokHeader_End

       Print #3,Str(TP_GetTotalTime)
End Function


' Einsatzzeiten nach Werkzeug
Function TP_PRINT_ToolTimes
Dim tname,bmp As String
Dim id As Long

Const distance =40
Dim ProcessTime As Double
Dim i As Long

    Print #1,HTML_StartBody
    Print #1,HTML_SetFont("Courier New Fett, Courier, Courier New, Arial, Palatino Linotype, Comic")
	Print #1,HTML_LF
	Print #1,HTML_PrintFont(5,0,"B", "Einsatzzeiten nach Werkzeug",2)
	Print #1,HTML_PrintFont(5,0,"B", "(tool processing time)",1)
	Print #1,HTML_PrintFont(3,0,"B","Werkzeug/Tool:"+HTML_Space(distance+6-Len("Werkzeug/Tool:"))+"Zeit/Time"+HTML_Space(15)+"Processdistance",1)
	Print #1,HTML_LF

	'XML-Abschnitt 2007-05-25 KRI
	Print #2,"<ToolData>"	    

	For i = 1 To UBound(TP.Tool) 
		' alle Werkzeuge durchgehen
		' Bitmap darstellen
		bmp = TP.Tool(i).BMPName
		id = TP.Tool(i).ToolID
		tname = "("+inttos(id)+")  "+TP.Tool(i).ToolName
		tname = LTrim(RTrim(tname))
		' alle doppelte Blanks entfernen
		While InStr(tname,"  ") 
			tname=Replace(tname,"  "," ")
		Wend
		
		ProcessTime = TP.Tool(i).MillingTime + TP.Tool(i).DHTime + TP.Tool(i).SawTime
		
		' leerzeichen füllen bis distance 
		tname = tname + HTML_Space(distance-Len(tname))

		Print #1,HTML_ImageSize(GET_MTM_BMP_Path+TP.Tool(i).BMPName,40,40)
		
		Print #1,HTML_PrintFont(3,2,"B",tname,0 )
		Print #1,HTML_PrintFont(3,3,"",MinSek(ProcessTime)+HTML_Space(10),0)
		
		If TP.Tool(i).G1Bearbeitungsweg>0 Then
			Print #1,HTML_PrintFont(3,3,"",MMinM(TP.Tool(i).G1Bearbeitungsweg),1)
		Else
			Print #1,HTML_PrintFont(3,3,"","",1)
		End If
		
    	      'XML-Abschnitt 2007-05-25 KRI
		Print #2,"    <tool"	    
		'Print #2,"     <details"	    
		Print #2,"      Number="+Chr(34)+inttos(i)+Chr(34)
		Print #2,"      Id="+Chr(34) + inttos(id)+Chr(34)
		Print #2,"      Graphic="+Chr(34) + GET_MTM_BMP_Path+TP.Tool(i).BMPName+Chr(34)
		Print #2,"      Caption="+Chr(34) + TP.Tool(i).ToolName+Chr(34)
		Print #2,"      Time="+Chr(34) + CStr(ProcessTime)+Chr(34)
		If TP.Tool(i).G1Bearbeitungsweg>0 Then
			Print #2,"      Distance="+Chr(34) + CStr(TP.Tool(i).G1Bearbeitungsweg) +Chr(34)
		Else
			Print #2,"      Distance="+Chr(34)+Chr(34)
		End If
		Print #2,"     >"
	'	Print #2,"     </details>"
		Print #2,"    </tool>"
	
	Next i
	
	
	Print #1,HTML_LF
	Print #1,HTML_HRuler	
	
       'XML-Abschnitt 2007-05-25 KRI
       Print #2,"</ToolData>"	    
	XML_Main_End

	
End Function




Function TP_Calc

Dim i,j,l,k As Long
Dim kp As Point_3d
Dim sp As Point_3d
Dim mx,my As Double
Dim dr As Integer 
Dim mill_time As Double
Dim mill_len As Double
Dim feedrate As Double
Dim BogenLaenge,GeradenLaenge,ZLaenge As Double
'Dim Tool_Edge_Life As Double    ' Werkzeug - Standzeit
Dim Milling,Sawing,Drilling,DH_vDrilling,DH_hDrilling As Boolean   ' Art der Bearbeitung
Dim striVari As Variant
Dim htmlpfad As Variant 

	TP.ProcessTimeMilling=0
	TP.ProcesstimeVerticalDrilling=0
      

  		htmlpfad = Get_PP_Path + TDATA.PostProzessor

	If Not FolderExists(htmlpfad) Then
		AddMistake("path not found - "+htmlpfad)
	Else

	Open htmlpfad & "\PTime.html" For Output As #1
	
	'XML-Abschnitt 2007-05-25 KRI
	Open htmlpfad & "\PTime.xml" For Output As #2
	Open htmlpfad & "\PTime.txt" For Append As #3
   	
	End If

	For i = 1 To UBound(TP.Tool) 
		' alle Werkzeuge durchgehen
		Milling=False
		Sawing=False
		Drilling=False
		DH_vDrilling=False
		DH_hDrilling=False
		TP.Tool(i).TotalTime =0 
		
		TP.Tool(i).MillingTime = 0
		TP.Tool(i).DHTime = 0
		TP.Tool(i).SawTime = 0
		TP.Tool(i).G1Bearbeitungsweg = 0
		mill_time = 0
		' Gesamt - Werkzeugwechsel zeiten
		TP.TChangeTime = TP.TChangeTime + TP.Tool(i).TChangeTime   
		' Gesamt - fahrten zum Werkzeugwechsler
		TP.TChangeMoveTime = TP.TChangeMoveTime + TP.Tool(i).TChangeMoveTime   
		' Gesamt - G0 fahrten
		TP.ProcessTimeTotalG0 = TP.ProcessTimeTotalG0 +TP.Tool(i).G0_Time
		For j = 1 To UBound(TP.Tool(i).K) 
			' alle Fräsbahnen durchgehen
			mill_len = 0
			' Startpunkt
			sp.X=TP.Tool(i).K(j).SP.X
			sp.Y=TP.Tool(i).K(j).SP.Y
			sp.Z=TP.Tool(i).K(j).SP.Z
			'Print #1,"Startpunkt X:"+ ftos(sp.X) + " Y:"+ ftos(sp.Y) + " Z:"+ ftos(sp.Z) 
			
			' alle G0 - fahrten aufsammeln zwischen den Fräskonturen
			TP.Tool(i).G0_Time = TP.Tool(i).G0_Time + TP.Tool(i).K(j).G0_Time
			For k = 1 To UBound(TP.Tool(i).K(j).K_P)
				' Konturstützpunkt val
				Milling=True
				kp.X=TP.Tool(i).K(j).K_P(k).p.X
				kp.Y=TP.Tool(i).K(j).K_P(k).p.Y
				kp.Z=TP.Tool(i).K(j).K_P(k).p.Z
				feedrate=TP.Tool(i).K(j).K_P(k).f
				mx = TP.Tool(i).K(j).K_P(k).i
				my = TP.Tool(i).K(j).K_P(k).j
				dr = TP.Tool(i).K(j).K_P(k).dr
			    If mx>-99998 Or my>-99998 Then
			    	' Kreisbogen
			    	BogenLaenge = LZWIPU3d(sp.X,sp.Y,sp.Z,kp.X,kp.Y,kp.Z)
			    	BogenLaenge = LRadian(sp.X,sp.Y,sp.Z,kp.X,kp.Y,kp.Z,mx,my,dr)
			    	ZLaenge = LZWIPU3d(0,0,sp.Z,0,0,kp.Z)
					mill_len = mill_len + BogenLaenge+ZLaenge
					' Zeit für diesen Kreisbogen fräsen
					'mill_time=mill_time + GetTimePath(BogenLaenge+ZLaenge,feedrate)
					mill_time=mill_time + GetTimePathAccelerationDeceleration(BogenLaenge+ZLaenge,feedrate,TPVars.Accel_Decel_G2,TPVars.Accel_Decel_G2)
                    If Debug_Timecalc=True Then
                        Print #4, "################################################################################"
                        Print #4, "Bogen (G2) mit Laenge: " + ftos(BogenLaenge) + " am Punkt: " + ftos(sp.X) + " | " + ftos(sp.Y) + " | " + ftos(sp.Z)
                    End If
					
				Else
					' Gerade
					GeradenLaenge = LZWIPU3d(sp.X,sp.Y,sp.Z,kp.X,kp.Y,kp.Z)
					mill_len = mill_len + GeradenLaenge
                    If Debug_Timecalc=True Then
                        Print #4, "################################################################################"
                        Print #4, "Gerade (G1) mit Laenge: " + ftos(GeradenLaenge)
                        Print #4, "Von Punkt: "; sp.X#; " | ";sp.Y#; " | " ;sp.Z#; "  Zu Punkt: "; kp.X#;" | ";kp.Y#;" | ";kp.Z#
                    End If
					' Zeit für diese Gerade fräsen
					'mill_time=mill_time + GetTimePath(GeradenLaenge,feedrate)
					mill_time=mill_time + GetTimePathAccelerationDeceleration(GeradenLaenge,feedrate,TPVars.Accel_Decel_G1,TPVars.Accel_Decel_G1)

				End If
				'Print #1,"X:"+ ftos(kp.X) + " Y:"+ ftos(kp.Y) + " Z:"+ ftos(kp.Z) + _
			    '        " Feedrate:" + ftos(feedrate)+ " Zeit:" + ftos(mill_time)
				
				sp.X=kp.X
  				sp.Y=kp.Y
			    sp.Z=kp.Z

			    
			Next k
			'Print #1, "Fraesbahnlänge: "+Inttos(mill_len)+"mm" +" Zeit:"+ftos(mill_time)+"sec."
			TP.Tool(i).G1Bearbeitungsweg = TP.Tool(i).G1Bearbeitungsweg + mill_len
	'msgbox("Fraesbahnlänge: "+Inttos(mill_len)+"mm" +" Zeit:"+ftos(mill_time)+"sec.")
		Next j
		
		If TP.Tool(i).is_dh_drilling Then
			For j = 1 To UBound(TP.Tool(i).DH_Stroke )
				' alle Bohrhübe durchgehen
				' todo
				DH_vDrilling=True
				TP.ProcesstimeVerticalDrilling = TP.ProcesstimeVerticalDrilling+TP.Tool(i).DH_Stroke(j).StrokeTime
				                                 
				TP.ProcesstimeVerticalDrillingG0 = TP.ProcesstimeVerticalDrillingG0 + TP.Tool(i).DH_Stroke(j).G0Time
				                    
			Next j
			TP.Tool(i).DHTime = TP.Tool(i).DHTime + TP.ProcesstimeVerticalDrilling

		End If
		If TP.Tool(i).is_sawing Then
			For j = 1 To UBound(TP.Tool(i).TP_Sawing )
				' alle sägeschnitte durchgehen
				' todo
				Sawing=True
				TP.ProcessTimeSawing = TP.ProcessTimeSawing+TP.Tool(i).TP_Sawing(j).SawTime
				                                 
				TP.ProcesstimeSawingG0 = TP.ProcesstimeSawingG0 + TP.Tool(i).TP_Sawing(j).G0Time
				                    
			Next j
			TP.Tool(i).SawTime = TP.Tool(i).DHTime + TP.ProcessTimeSawing

		End If
		
		
		If Milling Then
			TP.ProcessTimeMilling = TP.ProcessTimeMilling + mill_time
			TP.ProcesstimeMillingG0 = TP.ProcesstimeMillingG0 + TP.Tool(i).G0_Time
			TP.G1Bearbeitungsweg = TP.G1Bearbeitungsweg + TP.Tool(i).G1Bearbeitungsweg
			'Print #1,"****************************************************"
		    'Print #1,"*"+TP.Tool(i).ToolName
			'Print #1,HTML_Image("Cutter.JPG")
			'Print #1,"Fräszeit:"+MinSek(mill_time)
			'Print #1,"Fräslänge:"+ftos(Tool_Edge_Life\1000)+"m "+ftos(Tool_Edge_Life Mod 1000)+"mm"
			'Print #1,"Eilgang:" + Minsek(TP.Tool(i).G0_Time)
			'Print #1,"****************************************************"
			
			TP.Tool(i).MillingTime = TP.Tool(i).MillingTime + mill_time
			
	'msgbox( ftos(TP.Tool(i).G1Bearbeitungsweg))
		End If
		If DH_vDrilling Then
			'Print #1,"****************************************************"
			'Print #1,HTML_Image("Cutter.JPG")
		    'Print #1,"*"+TP.Tool(i).ToolName
			'Print #1,"Bohrzeit:"+MinSek(TP.ProcesstimeVerticalDrilling)
			'Print #1,"G0 ZeitBohrzeit:"+MinSek(TP.ProcesstimeVerticalDrillingG0)
			'Print #1,"Hübe:"+ftos(UBound(TP.Tool(i).DH_Stroke )-1)
			'Print #1,"****************************************************"
			'TP.ProcessTimeVDHDrilling = TP.ProcessTimeVDHDrilling + mill_time
		End If

		TP.Tool(i).TotalTime=TP.Tool(i).TotalTime + TP.ProcessTimeMilling+TP.ProcesstimeMillingG0
		' jetzt nächstes Werkzeug
	Next i
	
	TP_PRINT_TOTALPROCESSTIME
	TP_PRINT_ToolTimes
	'TP_PRINT_ToolTimesSeperate
	TP_PRINT_HEADER
		
		
	Close #1
	'XML-Abschnitt 2007-05-25 KRI
	Close #2
	'TXT-Abschnitt 2007-05-29 KRI
	Close #3
	'JS 11-14-2016 debug file
    If Debug_Timecalc=True Then
        Close #4	   
    End If    
'	WriteStrPP_ini("PTime","ID",TP.Tool(i-1).ToolID)
'	WriteStrPP_ini("PTime","FirstTC",TP.Tool(i-1).TCType)
'	WriteStrPP_ini("PTime","FirstHead",TP.Tool(i-1).HeadID)

End Function

Function GetTimePathAccelerationDeceleration(weg,vorschub As Double,accel As Double,decel As Double)
	' Weg:mm, vorschub:mm/min, accel(Beschleunigung): mm/s^2, decel(Verzögerung): mm/s^2

If Debug_Timecalc=True Then
    Print #4, "---------------------------------------------------------------------------------"
    Print #4, "------------------Start Zeitberechnung------------------"
End If	

Dim vorschub_sec As Double
Dim xa As Double
Dim xb As Double
Dim x_teila As Double
Dim x_teilb As Double
Dim x_konst As Double
Dim t_teila As Double
Dim t_teilb As Double
Dim zeit As Double
Dim max_v As Double

'vorschub immer als vorschub/60 = vorschub_sec verwenden
vorschub_sec = vorschub/60

If Debug_Timecalc=True Then
    Print #4, "Weg: " +ftos(weg)
    Print #4, "Vorschub: "; vorschub#
    Print #4, "Vorschub/sec: "; vorschub_sec#
    Print #4, "Beschleunigung: "; accel#
    Print #4, "Verzögerung: "; decel#
End If
	zeit = 0 
    If (decel <= 0) Or (accel <= 0) Then
	zeit = GetTimePath(weg,vorschub)
    Else
	'Beschleunigungsweg bis Vorschubsgeschwindigkeit erreicht
	xa = (vorschub_sec*vorschub_sec)/(2*accel)
    If Debug_Timecalc=True Then
        Print #4, "Beschleunigungsweg: ";xa#
    End If
	'Bremsweg
	xb = (vorschub_sec*vorschub_sec)/(2*decel)
    If Debug_Timecalc=True Then
        Print #4, "Bremsweg: ";xb#
    End If
	'Sonderfall wenn der Gesamtweg kürzer ist als accelsweg+Bremsweg
		If(weg < (xa+xb)) Then
			'Teilweg Beschleunigung
			x_teila=(accel/(accel+decel))*weg
            If Debug_Timecalc=True Then
                Print #4, "Teilweg Beschleunigung: "; x_teila#
            End If
			'Teilweg Bremsen
			x_teilb=(decel/(accel+decel))*weg
            If Debug_Timecalc=True Then
                Print #4, "Teilweg Bremsen: "; x_teilb#
            End If
			'maximale Geschwindigkeit
			max_v=Sqr(2*accel*x_teila)
            If Debug_Timecalc=True Then
                Print #4, "maximale Geschwindigkeit: "; max_v#
            End If
			'Teilzeit Beschleunigung
			t_teila=max_v/accel
            If Debug_Timecalc=True Then
                Print #4, "Teilzeit Beschleunigung: "; t_teila#
            End If
			'Teilzeit Bremsen
			t_teilb=max_v/decel
            If Debug_Timecalc=True Then
                Print #4, "Teilzeit Bremsen: "; t_teilb#
            End If
			'Gesamtzeit
			zeit=t_teila+t_teilb
            If Debug_Timecalc=True Then
                Print #4, "Gesamtzeit ohne voller Vorschub erreicht: "; zeit#
            End If
		Else
			'Teilweg Vorschub konstant
			x_konst = weg - (xa + xb)
            If Debug_Timecalc=True Then
                Print #4, "Teilweg Vorschub konstant: "; x_konst#
            End If
			'Gesamtzeit
			zeit = (vorschub_sec/accel) + (x_konst/vorschub_sec) + (vorschub_sec/decel)
            If Debug_Timecalc=True Then
                Print #4, "Gesamtzeit mit voller Vorschub erreicht: "; zeit#
            End If
		
		End If
	End If
    If Debug_Timecalc=True Then
        Print #4, "------------------------------------------------------------------------"
    End If
	GetTimePathAccelerationDeceleration = zeit
End Function

' gibt den wert verrechnet mit Nullpunkt zurück
Function absox(value)
	absox=value+JobPara.npx
End Function
' gibt den wert verrechnet mit Nullpunkt zurück
Function absoy(value)
	absoy=value+JobPara.npy
End Function
' gibt den wert verrechnet mit Nullpunkt zurück
Function absoz(value)
	absoz=value+JobPara.npz
End Function

Function abso(x,y,z)
	x= absox(x)	
	y= absoy(y)	
	z= absoz(z)	
End Function


Sub ToolListInit(Count)
	If Count<=0 Then
		' -- 
		' --  MW 13.09.2007 08:44:20
		' --
		Empty_Prog=True
		'MsgBox("error 4711")
		'Exit All
	Else
		Empty_Prog=False
	End If
End Sub

Sub HeadInfo(id)

   P_Head=id
	
End Sub

'Sub Tool(BoxNo,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15,d16,d17,d18,d19,d20,d21,d22,d23,d24,d25,d26,d27,d28,d29,d30,d31,d32)
Sub Tool(BoxNo,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15,d16,d17,d18,d19,d20,d21,d22)
	MT_SetTHopsBasicToolExt(P_T,BoxNo,P_Head)
	
End Sub

Sub ProcessListInit(Count)
	
End Sub

Sub ProcessInfo(Processtype,View,IPX,IPY,IPZ,RotA#,TipA#,SPVX,SPVY,SPVZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
	
End Sub


Sub Init(NCPath)
	TPToolInit
  
End Sub

Sub SetDrillingZMax(DZMax1,DZMax2,DZMax3,DZMax4,DZMax5,DZMax6,DZMax7,DZMax8,DZMax9)
  DZMax01=DZMax1
  DZMax02=DZMax2
  DZMax03=DZMax3
  DZMax04=DZMax4
  DZMax05=DZMax5
  DZMax06=DZMax6
  DZMax07=DZMax7
  DZMax08=DZMax8
  DZMax09=DZMax9	
	
End Sub

Sub FirstTool(BoxNo,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15,d16,d17,d18,d19,d20,d21,d22,d23,d24,d25,d26,d27,d28)
End Sub

Sub NC_Start(NCName,NCExt,TDB,FX,FY,FZ,Comment,Add_X,Add_Y,Add_Z)
   	JobPara.NPX=Add_X   ' G54 Nullpunkt X
   	JobPara.NPY=Add_Y   ' G54 Nullpunkt Y
   	JobPara.NPZ=Add_Z   ' G54 Nullpunkt Z
End Sub

Sub ToolChange(BoxNo,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,pspeed,d12,d13,d14,d15,d16,d17,d18,d19,d20,d21,d22,d23)
Dim dummy As Object
	' letztes benutztes Werkzeug auf Lastt schreiben
	If Not ActT.t Is Nothing Then
		Set LastT.t = TDATA.GetTool_ID(ActT.T.ID)
		Set dummy = LastT.T
		
		Set LastT.t_dh = dummy
		Set LastT.t_dhsaw = dummy
		
		' Neu MW 22.03.2005
		' Gearbox und 
		' --------------------------------
		If MT_IsGearBoxTool(LastT) Or MT_IsGearBoxTool_Special(LastT) Then
			Set LastT.gb = dummy.GearBox
		End If
		
		Set LastT.t_gb = dummy
		' --------------------------------
		
		LastT.hid = ActT.hid
		LastT.aggname = ActT.aggname
	Else
		If Not LastT.t Is Nothing Then
			Set LastT.t = Nothing
		End If
	End If
	
	If BoxNo > 0 Then
		MT_SetTHopsBasicToolExt(P_T,BoxNo,P_Head)
	End If
	TPToolChange(P_T)
End Sub


Sub ToolChangeBefore(BoxNo,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15,d16,d17,d18,d19,d20,d21,d22,d23,d24,d25,d26,d27,d28)
End Sub

Sub ViewChange(View,LastView,IPX,IPY,IPZ,RotA#,TipA#,SPAX,SPAY,SPAZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
	Call ViewSave(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPAX,SPAY,SPAZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
	' todo - endlagencheck Bohrkopf
	
	' Time Calc
	TPTool_ViewChange(SPAX,SPAY,SPAZ)
	
   	If MT_isDH(ActT) Then
	   'Marker.Last_DH_Process=""
   	   'DH_View0= ActV
   	   Exit Sub
	End If
End Sub

Sub Start_Milling(PNo,TRC,StartMove,StartFactor,I_Feedrate,feedrate,S_Feedrate,speed,PPVX,PPVY,PPVZ,PPAX,PPAY,PPAZ,RotA,TipA,TAngle,Start_End_MoveReady)
	TimeC_StartMill(PPAX,PPAY,PPAZ)
	TPTool_SP_Set(PPAX,PPAY,PPAZ)	
End Sub

Sub G00(PPVX,PPVY,PPVZ,PPAX,PPAY,PPAZ,feedrate,speed,RotA,TipA,TRC,TAngle)
	TPTool_G00_Set(PPAX,PPAY,PPAZ,feedrate)	
End Sub

Sub G01(PPVX,PPVY,PPVZ,PPAX,PPAY,PPAZ,feedrate,speed,RotA,TipA,TRC,TAngle)
	TPTool_G01_Set(PPAX,PPAY,PPAZ,feedrate)	
End Sub

Sub G02(PPVX,PPVY,PPVZ,CVI,CVJ,RCVI,RCVJ,PPAX,PPAY,PPAZ,CAI,CAJ,CAK,RCAI,RCAJ,RCAK,radius,feedrate,speed,RotA,TipA,TRC,TAngleB,TAngleE)
	TPTool_G02_Set(PPAX,PPAY,PPAZ,CAI,CAJ,feedrate)	

	
End Sub

Sub G03(PPVX,PPVY,PPVZ,CVI,CVJ,RCVI,RCVJ,PPAX,PPAY,PPAZ,CAI,CAJ,CAK,RCAI,RCAJ,RCAK,radius,feedrate,speed,RotA,TipA,TRC,TAngleB,TAngleE)
	TPTool_G03_Set(PPAX,PPAY,PPAZ,CAI,CAJ,feedrate)	

	
End Sub

'Sub End_Milling(DMove,DFactor,Retreat)
Sub End_Milling(DMove,DFactor,Retreat,x,y,z)
	 TPTool_EP_Set
End Sub

Sub DistanceToOutLine(Value)
End Sub


Sub Sawing(PNo,I_Feedrate,feedrate,S_Feedrate,speed,SPX,SPY,SPZ,EPX,EPY,EPZ,ZRef,TC,Flag,CPSawUnit_PosSX,CPSawUnit_PosSY,CPSawUnit_PosSZ,CPSawUnit_PosRX,CPSawUnit_PosRY,CPSawUnit_PosRZ,CPSawUnit_SPX,CPSawUnit_SPY,CPSawUnit_SPZ,CPSawUnit_EPX,CPSawUnit_EPY,CPSawUnit_EPZ,ViewCPSawUnit_PosSX,ViewCPSawUnit_PosSY,ViewCPSawUnit_PosSZ,ViewCPSawUnit_PosRX,ViewCPSawUnit_PosRY,ViewCPSawUnit_PosRZ,ViewCPSawUnit_SPX,ViewCPSawUnit_SPY,ViewCPSawUnit_SPZ,ViewCPSawUnit_EPX,ViewCPSawUnit_EPY,ViewCPSawUnit_EPZ,Retreat)
	Call PParaSet(I_Feedrate,feedrate,S_Feedrate,speed,0,0)

   TimeC_Sawing(CPSawUnit_SPX,CPSawUnit_SPY,CPSawUnit_SPZ,CPSawUnit_EPX,CPSawUnit_EPY,CPSawUnit_EPZ)
	
End Sub

Sub Start_Drilling(PNo,I_Feedrate,feedrate,S_Feedrate,speed)
	I_Feedrate = MT_CheckFeedrate(actt,0,0,0,0,0,0,I_Feedrate)
	feedrate = MT_CheckFeedrate(actt,0,0,0,0,0,0,feedrate)
	S_Feedrate = MT_CheckFeedrate(actt,0,0,0,0,0,0,S_Feedrate)

	Call PParaSet(I_Feedrate,feedrate,S_Feedrate,speed,0,0)
	
	PosReset
	MoveParaReset

	
End Sub

Sub Drilling(DNo,PPVX,PPVY,PPVZ,PPAX,PPAY,PPAZ,D,Depth,DFlag,Free,ZMax)
	If Not TP_Drilling_Activ Then
		TimeC_StartDrill(PPAX,PPAY,PPAZ)
		TPTool_SP_Set(PPAX,PPAY,PPAZ)	
	End If
	TP_Drilling_Activ=True
	
	
	Dim actfeedrate As Double
  Dim Count As Integer
  Dim I As Integer
  Dim ActDepth As Double
  Dim dx As Double
  Const DFI=-3
  Const DFS=-3
  
  ZMax=GetZMax(DFlag Mod 10,Depth)
  PPVZ=IIf(ActV.TipA < 45, ActT.T.GetSecurityZ(0),ActT.T.SecurityHorz)
    'wcnc(G0+Move(PPVX,PPVY,PPVZ,MovePara.Feedrate,MovePara.TRC))
	TPTool_G00_Set(PPAX,PPAY,PPAZ,ProcessPara.Feedrate)	
    
    If (DFI>Depth) And ((DFI>ZMax) Or (DFlag=0)) And Not equal(ProcessPara.I_Feedrate,ProcessPara.Feedrate) Then
       'Drilling with the surface feed
       'wcnc(G1+Move(PPVX,PPVY,DFI,ProcessPara.I_Feedrate,MovePara.TRC)) 
	 	TPTool_G01_Set(PPAX,PPAY,DFI,ProcessPara.I_Feedrate)	
       
    End If
    If Not equal(ProcessPara.S_Feedrate,ProcessPara.Feedrate) Then
        dx=ActV.IPZ+(Depth*Cosinus(ActV.TipA))   ' in Berücksichtigung mit Kippwinkel
        If dx<0 Then
           ' dann Bohrung <<DURCH>>	
          dx=dx+DFS
          Depth=Depth-dx
        End If
    End If
    If DFlag=0 Then
      'Drilling all depth
      'wcnc(G1+Move(PPVX,PPVY,Depth,ProcessPara.Feedrate,MovePara.TRC))
	 TPTool_G01_Set(PPAX,PPAY,PPAZ+Depth,ProcessPara.Feedrate)	
      
    Else  
       'Drilling   only a maximum depth (ZMax)
      Count=Depth\ZMax  
      For I = 1 To Count Step 1
        ActDepth=I*ZMax
        'wcnc(G1+Move(PPVX,PPVY,ActDepth,ProcessPara.Feedrate,MovePara.TRC))
		TPTool_G01_Set(PPAX,PPAY,ActDepth,ProcessPara.Feedrate)	
        
        'wcnc(G0+Move(PPVX,PPVY,0,ProcessPara.Feedrate,MovePara.TRC))
		TPTool_G00_Set(PPAX,PPAY,0,ProcessPara.Feedrate)	
      Next I
      If ActDepth>Depth Then
        'wcnc(G1+Move(PPVX,PPVY,Depth,ProcessPara.Feedrate,MovePara.TRC))
		TPTool_G01_Set(PPAX,PPAY,PPAZ+Depth,ProcessPara.Feedrate)	
        
        If Not ((ActV.View=0) And Not equal(ProcessPara.S_Feedrate,ProcessPara.Feedrate) And (dx<0)) Then
          'wcnc(G0+Move(PPVX,PPVY,0,ProcessPara.Feedrate,MovePara.TRC))
		TPTool_G00_Set(PPAX,PPAY,0,ProcessPara.Feedrate)	
        End If
      End If
    End If
    If Not equal(ProcessPara.S_Feedrate,ProcessPara.Feedrate) And (dx<0) Then
        If ProcessPara.S_Feedrate < ProcessPara.Feedrate Then
	        'S_Feedrate (go out of the part) is smaler then the Feedrate
        	actfeedrate = ProcessPara.S_Feedrate
	    Else
        	actfeedrate = ProcessPara.Feedrate
	    End If
	    
	    'wcnc(G1+Move(PPVX,PPVY,Depth+dx,actfeedrate,MovePara.TRC))
		TPTool_G01_Set(PPAX,PPAY,PPAZ+Depth+dx,actfeedrate)	
       'wcnc(G0+Move(PPVX,PPVY,0,MovePara.Feedrate,MovePara.TRC))
		TPTool_G00_Set(PPAX,PPAY,0,MovePara.Feedrate)	
    End If
    'Go to safety position on the view
    'wcnc(G0+Move(PPVX,PPVY,PPVZ,MovePara.Feedrate,MovePara.TRC))
	TPTool_G00_Set(PPAX,PPAY,PPAZ,Processpara.Feedrate)	
	
	
	
End Sub

Sub End_Drilling(Retreat)
	TP_Drilling_Activ=False
	 TPTool_EP_Set

	
End Sub

Sub Start_Vertical_DrillingHead_Stroke(PNo,I_Feedrate,feedrate,S_Feedrate,speed)
	Call PParaSet(I_Feedrate,feedrate,S_Feedrate,speed,0,0)

	TPTool_VDH_Stroke_Set
	
End Sub

Sub Vertical_DrillingHead_Stroke(SNo,SPosX,SPosY,PosFirstX,PosFirstY,Depth,DZ,DType,DFlag_Type,Dummy,tools,DFlag_TypeString)
	
	' Für Zeitberechnung
	TPTool_DHStroke_Set(PosFirstX,PosFirstY,DZ,Depth,tools,DFlag_TypeString)	


End Sub


Sub Horizontal_DrillingHead_Stroke(SNo,View,IPX,IPY,IPZ,RotA,TipA,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz,SPosX,SPosY,PosFirstX,PosFirstY,PosZ,SPosX_V,SPosY_V,PosFirstX_V,PosFirstY_V,SPosZ_V,PosFirstZ_V,Depth,DZ,DType,DFlag_Type,Dummy,tools,DFlag_TypeString)

	' Für Zeitberechnung
	TPTool_DHStroke_Set(PosFirstX,PosFirstY,DZ,Depth,tools,DFlag_TypeString)	

End Sub

Sub End_Vertical_DrillingHead_Stroke(Retreat)
   

End Sub

Sub NC_End()
	TP_Calc
End Sub

Sub NCInfo(Kind,NCType,Para1,Para2,Para3,Para4,Para5,Para6,Para7,Para8,Para9,characters)
End Sub


Sub ViewInfoToolChange(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPVX,SPVY,SPVZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz,dummy1,dummy2,dummy3,dummy4,dummy5,dummy6,dummy7,dummy8,dummy9,dummy10)

	
End Sub

Sub ProcessMinMaxInfo(xmin,ymin,zmin,xmax,ymax,ZMax)

End Sub

Sub WorkPieceListInit(Count)
	ReDim WPI(1)	

	
End Sub

Sub WorkPieceIndex(idx)
	Marker.wp_lastindex = Marker.wp_actindex
	Marker.wp_actindex = idx+1
End Sub

Sub WorkPieceInfo(SName,Sox,Soy,Soz,WPName,WPox,WPoy,WPoz,WPx,WPy,WPz)
    WPI(UBound(WPI)).SName = SName     ' Stop name
    WPI(UBound(WPI)).Sox = Sox         ' Stop offset x   
    WPI(UBound(WPI)).Soy = Soy         ' stop offset y
    WPI(UBound(WPI)).Soz = Soz         ' stop offset z
    WPI(UBound(WPI)).WPName = WPName   ' workpiece name
    WPI(UBound(WPI)).WPox = WPox       ' workpiece offset x
    WPI(UBound(WPI)).WPoy = WPoy       ' workpiece offset y
    WPI(UBound(WPI)).WPoz = WPoz       ' workpiece offset z
    WPI(UBound(WPI)).WPx = WPx         ' workpiece x
    WPI(UBound(WPI)).WPy = WPy         ' workpiece y
    WPI(UBound(WPI)).WPz = WPz         ' workpiece z
    ReDim Preserve WPI(UBound(WPI)+1) 
	
End Sub



Sub NCInfoProcess(InfoTyp,x1,y1,z1,x2,y2,z2,w1,w2,w3,w4,w5,w6,w7,w8,w9,w10,w11,w12,w13,w14,w15,w16,w17,w18,w19,w20,w21,str1,str2)
	
End Sub

Sub AdditionalSPInfo(DirectionMode,ExcessLength,Mode,Laser,AxisRotA,Res1,Res2,Res3,Res4,Res5,KW,TRC,distance,DW,s1,s2,s3,s4,s5)

End Sub

' Gibt hinterlegte Wechselzeit zurück
Function GetConst_TCTime 
Dim act_h,last_h As Long
Dim act_tc,last_tc As Long	
'Dim last_id As Long    ' im Letzten generierten Programm 
Dim search As String
Dim striVari As Variant 
	act_tc=0
	last_tc=0
	If TP.Tool(UBound(TP.Tool)).ISTCTool Then
		' aktuelles Tool von Werkzeugwechsler holen
		act_tc = TP.Tool(UBound(TP.Tool)).TCType	
	End If
	If TP.Tool(UBound(TP.Tool)-1).ISTCTool Then
		' letztes Tool auf Werkzeugwechsler ablegen
		last_tc = TP.Tool(UBound(TP.Tool)-1).TCType	
	End If
	
	' aktuelles Tool = Nebenaggregat z.b. hori-spindel oder pneum. Säge von Werkzeugwechsler 
	act_h = TP.Tool(UBound(TP.Tool)).HeadID	
	last_h = TP.Tool(UBound(TP.Tool)-1).HeadID	
	
	' letztes Werkzeug aus ini holen - Ausgangsituation
	If lastt.t Is Nothing Then
		'ReadStrPP_ini("PTime","FirstHead","1",striVari)
		'last_h=Int(striVari)
		'ReadStrPP_ini("PTime","FirstTC","7996",striVari)
		'last_tc=Int(striVari)
	End If
		
	
	search = "TC"
	search = search+IIf(act_h>0,"_"+inttos(act_h),"")  ' aktuelle HeadInfo
	search = search+IIf(act_tc>0,"_"+inttos(act_tc),"")  ' aktuelle Toolchanger info
	search = search+IIf(last_h>0,"_"+inttos(last_h),"")  ' letzter Head
	search = search+IIf(last_tc>0,"_"+inttos(last_tc),"")  ' letzter Toolchanger

	' -- 
	' --  MW 19.07.2007 12:38:05
	' --  aus MT-Manager Data lesen 
	striVari = Read_TC_TimeConst_MT(search)
	If Len(striVari)<=0 Then
		' Kompatibilitätsmodus
		ReadStrPP_ini("PTime",search,"10.0001",striVari)
		WriteStrPP_ini("PTime",search,striVari)
		AddHint("")
		AddHint("Time calculation constant value real toolchange:"+search+" result:"+striVari+" "+TP.Tool(UBound(TP.Tool)).ToolName+" -> "+TP.Tool(UBound(TP.Tool)-1).ToolName)
		AddHint("")
	Else
		AddHint("")
		AddHint("MTParam found! - Time calculation constant value tc:"+search+" result:"+striVari+" "+TP.Tool(UBound(TP.Tool)).ToolName+" -> "+TP.Tool(UBound(TP.Tool)-1).ToolName)
		AddHint("")
		
	End If
	
	GetConst_TCTime = StrToFloat(striVari)
	'MsgBox search
	' Eintrag in der INI - Datei anlegen

	If (TP.Tool(UBound(TP.Tool)).ISTCTool) And (last_h<>act_h) Then
		' jetzt muss noch berücksichtigt werden, dass evtl. zuletzt auf der Spindel befindliches
		' Werkzeug ausgwechselt werden muss
		last_h=TP.Tool(Get_LastToolHead(act_h)).HeadID  ' zuletzt verwendetes Werkzeug für dieses Aggregat suchen
		last_tc=TP.Tool(Get_LastToolHead(act_h)).TCType  ' wo muss letztes Werkzeug hin(Wechsler)
		If TP.Tool(last_h).ISTCTool Then
			search = "TC"
			search = search+IIf(act_h>0,"_"+inttos(act_h),"")  ' aktuelle HeadInfo
			search = search+IIf(act_tc>0,"_"+inttos(act_tc),"")  ' aktuelle Toolchanger info
			search = search+IIf(last_h>0,"_"+inttos(last_h),"")  ' letzter Head
			search = search+IIf(last_tc>0,"_"+inttos(last_tc),"")  ' letzter Toolchanger
			
			' -- 
			' --  MW 19.07.2007 12:38:05
			' --  aus MT-Manager Data lesen 
			striVari = Read_TC_TimeConst_MT(search)
			If Len(striVari)<=0 Then
				ReadStrPP_ini("PTime",search,"10.0001",striVari)
				' Eintrag in der INI - Datei anlegen
				WriteStrPP_ini("PTime",search,striVari)
				AddHint("Time calculation constant value tc toolchange:"+search+" result:"+striVari+" "+TP.Tool(UBound(TP.Tool)).ToolName+" -> "+TP.Tool(Get_LastToolHead(act_h)).ToolName)
			Else
				AddHint("MTParam found! - Tc:"+search+" result:"+striVari+" "+TP.Tool(UBound(TP.Tool)).ToolName+" -> "+TP.Tool(UBound(TP.Tool)-1).ToolName)
			End If
			GetConst_TCTime = GetConst_TCTime + StrToFloat(striVari)
		
		End If
	
	End If
End Function

Function Get_LastToolHead(h)  ' zuletzt verwendetes Werkzeug für dieses Aggregat suchen
Dim i As Integer
Dim erg As Integer 
	erg=0
	If UBound(TP.Tool)>0 Then
		For i = (UBound(TP.Tool)-1) To 0 Step -1
			If TP.Tool(i).HeadID=h Then
				erg=i
				Exit For
			End If
		Next i
	End If
	Get_LastToolHead=erg
	
End Function

Sub SawingExt(PNo,I_Feedrate,feedrate,S_Feedrate,speed,SPX,SPY,SPZ,EPX,EPY,EPZ,ZRef,TC,Flag, _
              CPSawUnit_PosSX,CPSawUnit_PosSY,CPSawUnit_PosSZ,CPSawUnit_PosRX,CPSawUnit_PosRY,CPSawUnit_PosRZ, _
              CPSawUnit_SPX,CPSawUnit_SPY,CPSawUnit_SPZ,CPSawUnit_EPX,CPSawUnit_EPY,CPSawUnit_EPZ, _
              ViewCPSawUnit_PosSX,ViewCPSawUnit_PosSY,ViewCPSawUnit_PosSZ,ViewCPSawUnit_PosRX,ViewCPSawUnit_PosRY,ViewCPSawUnit_PosRZ, _
              ViewCPSawUnit_SPX,ViewCPSawUnit_SPY,ViewCPSawUnit_SPZ,ViewCPSawUnit_EPX,ViewCPSawUnit_EPY,ViewCPSawUnit_EPZ,Retreat, _
              CPSawUnit_PosSX2,CPSawUnit_PosSY2,CPSawUnit_PosSZ2,CPSawUnit_PosRX2,CPSawUnit_PosRY2,CPSawUnit_PosRZ2, _
              ViewCPSawUnit_PosSX2,ViewCPSawUnit_PosSY2,ViewCPSawUnit_PosSZ2,ViewCPSawUnit_PosRX2,ViewCPSawUnit_PosRY2,ViewCPSawUnit_PosRZ2, _
              RViewx,RViewy,RViewz, _
              Res1,Res2,Res3,Res4,Res5)
	Call PParaSet(I_Feedrate,feedrate,S_Feedrate,speed,0,0)

   TimeC_Sawing(CPSawUnit_SPX,CPSawUnit_SPY,CPSawUnit_SPZ,CPSawUnit_EPX,CPSawUnit_EPY,CPSawUnit_EPZ)
	
End Sub

	'XML-Abschnitt 2007-05-25 KRI
Sub XML_Main_Begin
	Print #2,"<?xml version=""1.0""?>"
	Print #2,"<!-- Process Calculate CAMPUS -->"
	Print #2,"<Report>"
End Sub
Sub XML_Main_End
	Print #2,"</Report>"
End Sub
Sub XML_DokHeader_Begin
	Print #2,"  <Global>"
End Sub
Sub XML_DokHeader_End
	Print #2,"  </Global>"
End Sub


Function Read_TC_TimeConst_MT(search) As Variant
If Debug_Timecalc=True Then
    Print #4,"LOOKING FOR Tool Change Time Constant: " + search
End If
Const anz = 1000
Dim i As Long
Dim addi As IIAddition
Dim iDName As Variant 
Dim result As String
	result=""
	
	For i = 110000-1+i To 110000-1+anz
		Set addi = TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(i)
		If Not addi Is Nothing Then
			iDName=addi.Name
			If Not IsNumeric(iDName) Then
				iDName=UCase(iDName)    ' MW 18.07.2014
			End If
			If iDName=search Then
				result=addi.Value 
				Exit For
			End If
		End If
			
	Next i 
    If Debug_Timecalc=True Then
        Print #4,"result is: " + CStr(result)
    End If
	Read_TC_TimeConst_MT=result
	If result="" Then
		AddHint("Read_TC_TimeConst_MT not found " +search)
	End If
	Set addi=Nothing
End Function

Sub SP_EP_No_LeadInOut(SP_x,SP_y,SP_z,SP_ax,SP_ay,SP_az,SP_Feedrate,SP_Speed,SP_RotA,SP_TipA,SP_TRC,SP_TA,SP_Distance, _
                       EP_x,EP_y,EP_z,EP_ax,EP_ay,EP_az,EP_Feedrate,EP_Speed,EP_RotA,EP_TipA,EP_TRC,EP_TA,EP_DMove,EP_DFactor,EP_Retreat, _
                       Dummy1,Dummy2,Dummy3,Dummy4,Dummy5,Dummy6,Dummy7,Dummy8,Dummy9,Dummy10,Dummy11,Dummy12,Dummy13,Dummy14,Dummy15,Dummy16,Dummy17,Dummy18,Dummy19,Dummy20)
End Sub

Function Get_PP_Path As String

Dim iiSet As Object
Dim Language As Object
  
	Set iiSet = CreateObject("Hops_DLLInterface.HopsSettings")	
	Get_PP_Path = iiSet.HopsPostprozessorPath
   	Set iiSet = Nothing
	
End Function


Function TP_GET_TC_PLACE(t As THopsBasicToolExt) As Integer
Dim PlaceId As Long
Dim tplace,IITCHead As Object 
Dim itc As IITC_ToolPlace
Dim i As Integer 

	TP_GET_TC_PLACE = -1
	Set IITCHead = ActT.t.GetOn_TC   ' IIToolchangerHead
	PlaceId = ActT.t.GetPlaceID_OnTC
	
	' IIToolchangerHead Plätze durchgehen, und nach placeid suchen
	For i = 0 To IITCHead.ToolPlaces.Count-1
		Set itc = IITCHead.ToolPlaces.GetToolPlace_Index(i)
		If itc.PlaceID = PlaceId Then
			TP_GET_TC_PLACE = i
			'Set TP_GET_TC_PLACE = IITCHead.ToolPlaces.GetToolPlace_Index(i)
			Exit For
		End If
	Next i
	
	

End Function

Function Start_HTML_Viewer
Dim iiSet As Object
Dim viewer As Variant 
  
  	'icampussettings
	Set iiSet = CreateObject("Hops_DLLInterface.CampusSettings")	
	viewer= iiSet.ReadString("Jobliste","PPTimesFileViewer","explorer.exe")
	Set iiSet = Nothing
    Shell(viewer+" " + MacroDir & "\PTime.html") 
	
End Function

Sub ClampChange(par1,par2,par3,par4,par5,par6,par7,par8,par9,par10,par11,par12)
Dim t_ini As Double 
	
	
	TP.ClampChangeTime= TP.ClampChangeTime + TPVars.Const_Clampchange

		
End Sub

Sub InitZero
End Sub

Sub StartLeadOut
End Sub

Sub EndLeadIn
End Sub


Sub Park (Index)
End Sub


Sub NCIExt (Kind,NCType,Index)

End Sub

Sub MachineStop(Index, NextBoxNoWorking, HeadID)
'	Call Machine_Stopp_7 (Index, NextBoxNoWorking, HeadID)
End Sub

Sub SuctionHood (Index)
	
End Sub

Sub ClampChangeExt(Situa1,Situa2,Index)
end sub 