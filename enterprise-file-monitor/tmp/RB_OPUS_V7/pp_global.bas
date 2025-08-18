' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \RB_OH_OPUS_V7\pp_global.bas
' -- 
' -----------------------------------------
' -- 
' -- Reichenbacher - ISG / BECKHOFF Postprocessors V7 (mw) --
' -- 
' -----------------------------------------
'#uses "pp_math.bas"
'#uses "pp_version.bas"


Option Explicit

'***********************************************************************************
'*************************************  GLOBALS  ***********************************
'***********************************************************************************
Global DLLVersion As Variant 


Global Const PPEMPTY = -1    ' 
Global Const PPFLOAT = 0     ' 3.324
Global Const PPBOOLEAN = 1   ' False / True
Global Const PPINTEGER = 2   ' 2
Global Const PPSTRING = 3    ' STRING

'***********************************************************************************
'*************************************  Types  *************************************
'***********************************************************************************

Type TView
   View As Long
   LastView As Long
   IPX As Double
   IPY As Double
   IPZ As Double
   RotA As Double
   TipA As Double
   SPVX As Double
   SPVY As Double
   SPVZ As Double
   Vxx As Double
   Vxy As Double
   Vxz As Double
   Vyx As Double
   Vyy As Double
   Vyz As Double
   Vzx As Double
   Vzy As Double
   Vzz As Double
End Type

Type TOSZ 
	Activ As Boolean
	Feed As Long
	Excursion As Double
End Type


Type TFinishedPart
   X As Double
   Y As Double
   z As Double
End Type

Type TMovePara
  TRC As Long
  Feedrate As Long
End Type

Type TPos
   X As Double
   Y As Double   
   Z As Double
End Type

' Workpiece - Info
Type TWPI
    SName As String       ' AnschlagName
    Sox As Double         ' Anschlag Offset X  
    Soy As Double         ' Anschlag Offset Y
    Soz As Double         ' Anschlag Offset Z
    WPName As String      ' Werkstueck -Name
    WPox As Double        ' Werkstueck Offset X
    WPoy As Double        ' Werkstueck Offset Y
    WPoz As Double        ' Werkstueck Offset Z 
    WPx As Double         ' Werkstueck Breite
    WPy As Double         ' Werkstueck Laenge   
    WPz As Double         ' Werkstueck Dicke
End Type
Global WPI() As TWPI


Type TBMuster
    BM1 As Double
    BM2 As Double
    BM3 As Double   ' neu 18.3.2005 Spindelcodierung nur noch 16Bit
    GroupCode As Long
End Type

Type TLanguage
	id As Long
	display As Variant	
	Ext As Variant	
	id_default As Long 
	display_default As Variant 
	Ext_Default As Variant
End Type

Type TDINISO
	activ As Boolean 
	Filename_EXT As String
End Type

' Variables from interface "work-center"
Global Type ThopsJobPara
	Activ_Fields As Integer         ' Aktive Felder 1=links 2=rechts 3=gekoppelt
	Laser_Activ As Boolean          ' wird 1 gesetzt wenn Punktlaser aktiviert 
' MW 24.10.2016 unnoetige Variablen	
'	    Position As Integer				' Anschlagposition
'	    FLAG As Variant					' Flag
	    NPX As Double					' Nullpunkt X
	    NPY As Double					' Nullpunkt Y
	    NPZ As Double					' Nullpunkt Z
'	    AUFMASSX As Double				' Aufmass X
'	    AUFMASSY As Double				' Aufmass Y
'	'    Pad_Z As Double					' Saugerhoehe
'	    Jig_Z As Double					' Schablonenhoehe
'	    'Sic_Z As Double					' muss von Engine bereits verrechnet worden sein
	    									' zusaetzlicher Sicherheitsabstand z.B. Spannmittel ueberstand uebers Werkstueck
    RealNCFileName As String        ' c:\nc\Field1.spf
'    MirrorX As Boolean
'    MirrorY As Boolean
    Park As Integer					' Parkpos 1 = Links hinten 2=rechts hinten 3=mitte hinten
    ParkX As Double
    Parky As Double
    Language As TLanguage           ' wird aus iiSettings ermittelt
    HopsPath As String 				' wird aus iiSettings ermittelt
    HPGL_TimeStamp As String        ' Neu MW 2.8.2005 fuer check ob korrekte HPGL-Datei
    Add_ZSic As Double              ' Neu MW 14.09.2005 zusaetzliche Z-Sicherheit
    ' --  Radius fahren spezial - Mode (wenn Radius welcher gefahren wird, dem Werkzeugradius entspricht - inkl. Toleranzangabe)
	Jumps_in_NC As Boolean                   ' MW 14.11.2012 - > Aktivierung Sprungmarken
	Jumpvar As String						 ' MW 12.12.2012 - > Name der Sprungvariablen -> Diese muss nummerisch auf 1.. gesetzt werden !
	JumpAktPos As Long                       ' MW 12.12.2012 - > Fortlaufender Zaehler -> 
	JumpCount As Long                        ' MW 12.12.2012 - > Pruefzahl
	JumpList As Integer                      ' MW 12.12.2012 - > Liste der Einsprungmarken
	JumpStamp As Variant                      ' MW 12.12.2012 - > Randomized Nummber
	ActScene As Integer       ' MW 05.03.2014   Zaehler der Szene in der man sich aktuell befindet - Beginnend bei ein 
	TC_SC() As Integer        ' MW 30.03.2015   Toolchange -> Szenen - Marker ueber Vorlauf
    P_Info As String          ' -- MW 21.12.2015 Info- String ueber die Bearbeitung
    lStp As Integer         ' MW 14.01.2016
    is_5Axis_Machine As Boolean    ' MW 20.01.2016 steuert WriteNCMillingPointsHeadData in InitDLLMPs_Milling
    TimerFullSecs As Double          ' MW 01.02.2016 Timer ueber ALLES
    TimerInitTL As Double            ' MW 01.02.2016 Timer wird bei INITToolList gesetzt
	TRC_Strategy As Integer 		' ID 10100 MW 01.06.2016 Strategie fuer Aufbau Fraeserradiuskorrektur
	WorkC_OptionBit As Double
	'ISG As Boolean
	DINISO As TDINISO           ' MW 01.04.2019
	SUPPRES_LAST_POINT_DINISO As Boolean          ' MW 18.10.2021 ID #2020 
End Type
Global JobPara As THopsJobPara

'Global Type ThopsMachineData
'    ParkposX As Double
'    ParkposY As Double
'    ParkposZ As Double
'    DustExt1 As Double	' Schwellwert 1 Absaugung 
'    DustExt2 As Double	' Schwellwert 2 Absaugung
'    DustExt3 As Double	' Schwellwert 3 Absaugung
'    DustExt4 As Double	' Schwellwert 4 Absaugung
'End Type
'Global MachinePara As ThopsMachineData


' -------------------------------------------------------------
' -- Hier Type fuer Merker
Global Type TMarker
    Last_BM As TBMuster
    Last_DH_Process As String       ' marker lastproces DrillingV->DH Vertikal DrillingH->DH horizontal
    last_DH_TLength As Double    ' marker last length of drilling 
    Last_DH_ToNo As Long            ' letzte Bohrspindel T-Nummer
    Last_DH_Tools As String         ' letztes Bohrmuster als String
    Last_DH_DZ As Double            ' letzter Versatzwert aller Verschiebungen einer Hor. Bohrung
    FirstTime_DH_Drilling As Boolean   ' Merker fuer Bohrkopf Bohren aktiv
    'Viewchangechecked As Boolean    ' spezialmerker zum check ob viewchange bereits durchlaufen
    WP_ActIndex As Long      '  Workpiece - Index - Zaehler
    WP_LastIndex As Long      '  Workpiece - Index - Zaehler
    Programmed_DH_Speed As Double   ' Merker, programmierte Drehzahl Bohrkopf
    Last_SuctionPos As Integer   ' Merker fuer Absaugung
	G0_Up_DH As Boolean          ' Bohrkopf ID#999 / NCIExt #90500 Mode57 ONOFF 0/1
	HorDH_PullBack As Boolean    ' MW 20.02.2007  ' fuer Rueckzugslogik beim horizontalen Bohren
	MachineStopActive As Boolean      ' -- MW 03.12.2008 17:24:29	' --
	TraoriOn As Boolean             ' MW 03.04.2014 Merker fuer NCseitige 5Achs - Transformation
	FirstTool_PosX As Double        ' MW 09.06.2015 Merker 1. X-Pos -> ueber FirstTool
	OscilationOn As Boolean			' AK 03.11.2015 Merker Pendelachse aktiv	
    OffzCAxisMill_Activ As Boolean   ' MW 20.01.2016 G92 aktiv
    TCarr_Activ As Boolean           ' MW 20.01.2016 TCARR - Offset Winkelgetriebe (und Co.) aktiv
	LastSpeed As Double     ' MW 16.02.2016 Merker fuer zuletzt ausgebene Spindeldrehzahl
	BStris As NCData_SetOfString    ' MW 24.02.2016   Liste der Strings fuer wegschreiben NCIExt nach der Anfahrbewegung ueber DLL-Milling
	AStris As NCData_SetOfString    ' MW 24.02.2016   Liste der Strings fuer wegschreiben NCIExt vor der Abfahrbewegung ueber DLL-Milling
	ActProcess As Long              ' MW 31.03.2016
	CountOfTool As Long             ' MW 31.03.2016
	fCommand1 As NCData_SetOfString    ' WCNC_ISG_CONTOUR_START_EXT
	fCommand2 As NCData_SetOfString    ' WCNC_ISG_CONTOUR_END_EXT
	Process_activ As Boolean        ' MW 20.04.2017   Marker ist zum Zeitpunkt zwischen "Process_start und Process_End" = True zwischen "Process_End - Process_start" = False
	Haube_Activ As Boolean 
	Haube_Firsttime As Boolean 
End Type
Global Marker As TMarker

' -------------------------------------------------------------
' -- Hier Type fuer einen Bohrer vom Bohrkopf
Global Type tDriller
	TName As String         ' Name
	TNo As Long              ' TNummer des Bohrers auf der Steuerung
	V As Double        ' Vorschub
	VE As Double       ' Eintauchvorschub
	VA As Double       ' Austauchvorschub
	Length As Double         ' Bohrer Laenge
	E_Len As Double          ' Bohrer ueberstand 
	offx As Double           ' Offset zum Referenzbohrer X 
	offy As Double           ' offset zum Referenzbohrer Y
	offz As Double           ' offset zum Referenzbohrer Z
	Edge As IICuttingEdge    ' Schneidendaten des Bohrers
	TP As IIDH_ToolPlace     ' Toolplace Daten des bohrers
	Speed As Double          ' SollDrehzahl Neu MW 09.08.2005
End Type

' -------------------------------------------------------------
' -- Hier Type fuer Bohrkopfdaten
Global Type tDH
	TName As String         ' Name
	V As Double        ' Vorschub
	VE As Double       ' Eintauchvorschub
	VA As Double       ' Austauchvorschub
	centerx As Double           ' Offset zum Referenzbohrer X 
	centery As Double           ' offset zum Referenzbohrer Y
	centerz As Double           ' offset zum Referenzbohrer Z
End Type


' -------------------------------------------------------------
' -- Hier Type fuer Bohren mit Reihenbohrgetriebe mehrfach
Global Type tMultiDrilling_GBHeadVert
	dw As Double
	angle As Double
End Type

Global Type tUnderside
 	dw As Double
 	view_w As Double 
End Type


' -------------------------------------------------------------
' -- Hier Type Werkzeugzusatzinformation fuer Fraesspindel 
' -- Neu MW 03.04.2007 5Axis
Global Type t_PH_Additions
'	HoodThreshold_DynMode As Boolean 
'	Traori_On As String 
'	Traori_Off As String 
'	Tool_No As Long  ' TNum = 0 dann Wechselplatz - Nummer Tnum>0 dann diese Nummer
'	Corr_No As Long  ' DNum = 0 dann Schneidennummer DNum >0 dann diese Nummer
	RotPointOffZ As Double   ' ID -20001 ==> <>0 wenn Nullpunkt auf PIVOTPOINT eingemessen
	HaubeDown(3) As String   ' ID #20001/#20002/#20003
End Type

Global Type tmPara_Add
	' DEF_PSaeg1 (90)       entfaellt -> bei geruesteter Saege und Spindel horizontal und Raster schwenkbar nicht notwendig
'	Laser_HeadID As Integer  ' DEF_LASER1 (110)     ID 1200
	' -
'	ShowTravLPointer As Boolean      ' (0)               ID1050
'	ShowPadsLPointer As Boolean      ' (1)               ID1051
'	ShowWorkPieceContour As Boolean  '(1)       ID1052 
	' -
'	PARK_DIST_X_Field1 As Double     ' (500)   ID 1010
'	PARK_DIST_X_Field2 As Double     ' (800)   ID 1011
	' -
'	Threshold1 As Double   ' (120)   ID 100100   auch schon In V6
'	Threshold2 As Double   ' (170)   ID 100101   auch schon In V6
'	Threshold3 As Double   ' (220)   ID 100102   auch schon In V6
	' -
	KEEP_ZSIC_AFTER_TC As Boolean  ' (0)        ID 1020
	WRITE_COMMENTS As Boolean      ' (0)        ID 1100
'	Script_Info As Boolean         ' (0)        ID 1101
	' -
'	sc_minfeed As Double 
'	sc_contprec As Double 
	'WithPadPos As Boolean             ' ID #20050
	'WriteWorkTypeInfo As Boolean      ' ID #20051  - setzt Zyklus mit Uebergabe der Bearbeitungsart
End Type

Global mPara_Add As tmPara_Add


'***********************************************************************************
'*************************************  Variables  *********************************
'***********************************************************************************

'global nc path
Global ncpathGlobal As String
Global NCNameGlobal As String
'Global NCExtGlobal As String
'aktual nc line number
Global NCLine As Long

'actual view
Global ActV As TView
'last view
Global LastV As TView

Global FinishedPart As TFinishedPart
'last TRC and Feedrate
Global MovePara As TMovePara
'saved feedrates, speed, tipA, RotA

'Last x,y,z position
Global LastPos As TPos

'true if safe position
Global Z_Is_Safety As Boolean
Global Z_Is_SafetyPart As Boolean


Global ToolChangeBeforeStr As String


'Global DistanceToOutLineValue As Double
Global FloatFormat As String



Global Nullpunkt As String
Global NullpunktNummer As Integer
Global Firsttime_Viewchange As Boolean



Global sc_minfeed As Double
Global sc_contprec As Double

Public AktSpindelCodeDH_X As Double
Public AktSpindelCodeDH_Y As Double

Global DZMax01 As Double
Global DZMax02 As Double
Global DZMax03 As Double
Global DZMax04 As Double
Global DZMax05 As Double
Global DZMax06 As Double
Global DZMax07 As Double
Global DZMax08 As Double
Global DZMax09 As Double

Global Allowed_ToolTypes()

Global FirsttimeDrilling As Boolean

Global Const DRILL_DHV="DRILLINGV"
Global Const DRILL_DHH="DRILLINGH"

'Global Const NCINFOPARKINFO=55
'Global Const NCINFO_NO_G0_UP_DH=57    ' MW 18.02.2016 muss nicht einstellbar sein!
'Global Const NCINFO_HORDH_PULLBACK=58        ' * para1=1
'Global Const NCINFO_HORMILLING_PULLBACK=58   ' * para2=1


Global DH_View0 As TView

' erst wenn diese Variable True, dann setzt wcnc auch was ab
Global WritingNCData As Boolean
Global MoveTime_Result As Double

' Log-Datei Array
Global LogArr() As String

Global NCFileNo As Long   ' NEU MW 12.07.2005   oeffnen - und schreiben des NC-Programms umgestellt

Global MultiDrilling_GBHeadVert As tMultiDrilling_GBHeadVert

Global UndersideTool As tUnderside


' --------------------------------------------------
' --
' Viewchange Drillinghead
' -- nur Ebenen - Wechsel ohne Verfahrbewegung
' --------------------------------------------------
Sub wcncViewChange_DH(dh As tdh,View,LastView,ByVal IPX,IPY,IPZ,RotA,TipA,Driller As tDriller)
Dim offx,offy,offz As Double ' Gesamtoffset PlatzOffset + Werkzeuglaenge
	
	MT_get_DH_Drill_Offsets(Driller,offx,offy,offz)

    wcncCom("Viewchange DH View "+View)
	
	WCNC_SUB(SUB_TRANSOFF)
	
	' AggOffsets werden von Engine bereits in die Ebene gerechnet (bei Einstellung Kopfdaten berechnen)
	WCNC_SUB("ATRANSAROT_DH",IPX,IPY,IPZ,RotA,TipA,offx,offy,offz)
	
    wcncCom("ViewchangeEnd DH ")		

    LastV.View=View
    LastV.IPX=IPX
    LastV.IPY=IPY
    LastV.IPZ=IPZ


End Sub


'Reset the moveparameter to an impossible value
Sub MoveParaReset
  MovePara.TRC=-99999
  MovePara.Feedrate=-99999
End Sub

'set the moveparameter
Sub MoveParaSet(Feedrate,TRC)
  MovePara.TRC=TRC
  MovePara.Feedrate=Feedrate
End Sub


'Save the View adjustments
Sub ViewSave(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPVX,SPVY,SPVZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
   ActV.View=View
   ActV.LastView=LastView
   ActV.IPX=IPX
   ActV.IPY=IPY
   ActV.IPZ=IPZ
   ActV.RotA =RotA
   ActV.TipA =TipA
   ActV.SPVX=SPVX
   ActV.SPVY =SPVY
   ActV.SPVZ =SPVZ
   ActV.Vxx=Vxx
   ActV.Vxy=Vxy
   ActV.Vxz=Vxz
   ActV.Vyx=Vyx
   ActV.Vyy=Vyy
   ActV.Vyz=Vyz
   ActV.Vzx=Vzx
   ActV.Vzy=Vzy
   ActV.Vzz=Vzz
End Sub



Sub SaveFinishedPart(FX,FY,FZ)
  FinishedPart.X=FX
  FinishedPart.Y=FY
  FinishedPart.Z=FZ
End Sub

Sub PosReset
  LastPos.X=-99999
  LastPos.Y=-99999
  LastPos.Z=-99999
End Sub

Sub PosSet(x,Y,z)
  LastPos.X=x
  LastPos.Y=Y
  LastPos.Z=z
End Sub


Function G0
  G0="G0"
End Function

Function G1
  G1="G1"
End Function

Function G2
  G2="G2"
End Function

Function G3
  G3="G3"
End Function

Function XToS(x)
	XToS=" X"+FToS(x)
End Function

Function YToS(Y)
  YToS=" Y"+FToS(Y)
End Function

Function ZToS(z)
	ZToS=" Z="+FToS(z)
End Function

Function XEqualToS(x)
  XEqualToS=" X="+FToS(x)
End Function

Function YEqualToS(y)
  YEqualToS=" Y="+FToS(y)
End Function

Function ZEqualToS(z)
  ZEqualToS=" Z="+FToS(z)
End Function

Function IToS(i)
  IToS=" I"+FToS(i)
End Function

Function JToS(j)
  JToS=" J"+FToS(j)
End Function


Function GetTRCStr(TRC)
  Select Case TRC
    Case 0
        GetTRCStr=" G40"
    Case 1
        GetTRCStr=" G41"
    Case 2
        GetTRCStr=" G42"
    End Select
End Function



Function GetFeedrateStr(Feedrate)
  GetFeedrateStr=" F"+IntToS(Feedrate)
End Function

Function GetSpeedStr(speed)
  GetSpeedStr=IntToS(Abs(Round(speed/100)))
  If speed<0 Then
    GetSpeedStr=GetSpeedStr
  Else
    GetSpeedStr=GetSpeedStr
  End If
End Function



'compare the last and actual view if equal -> true
Function ViewEqual
	' Neu MW 31.10.2006 - Wenn Saegen auf Saegen folgt immer Ebenenwechsel 
	ViewEqual=equal(LastV.View,ActV.View) And _
	        equal(LastV.IPX,ActV.IPX) And _
	        equal(LastV.IPY,ActV.IPY) And _
	        equal(LastV.IPZ,ActV.IPZ) And _
	        equal(LastV.TipA,ActV.TipA) And _
	        equal(LastV.RotA,ActV.RotA)
	        
End Function

Function FToS(W)

Dim n As Integer
Dim FToSSave As String
Dim erg As String
Dim anz As Long

	anz=0
	erg=""

	If (UCase(TypeName(W)) = "STRING") And (IsNumeric(W)) Then
		' d.h. numerischer String - Sonderfall - z.B. parken ueber Stringvariablen - kann auch string sein - numerisch
		erg = Replace$(Format$(StrToFloat(W),FloatFormat),",",".")
	Else
		erg = Replace$(Format$(W,FloatFormat),",",".")
	End If
	
	' -- 
	If InStr(erg,".")>0 Then
		' MW 05.01.2015 nur noetig, wenn es Nachkommstellen gibt -> dadurch auch Fehlervermeidung 100 ===>  1
		For n=Len(erg) To 1 Step -1
			If (Mid(erg,n,1)=".") Or (Mid(erg,n,1)<>"0") Then
				Exit For
			Else
				If Mid(erg,n,1)="0" Then
					anz = anz + 1   ' diese koennen geloescht werden
				End If
			End If
		Next n
	End If
	
	If anz > 0 Then
		erg = Mid(erg,1,Len(erg)-anz)
	End If
	
	If erg="" Then
		'AddHint("schwerwiegender Fehler")
	Else
		If Mid(erg,Len(erg),1)="." Then
			' punkt loeschen
			erg=Mid(erg,1,Len(erg)-1)
		End If
	
	End If
	
	FToS=erg
	
End Function

Function IntToS(W)
	If Len(Str(W))>0 Then
		' --  neu jetzt wirklichen Int- Wert ausgeben ohne Nachkommastellen: weder "," noch "."
		W=Round(W)	
	End If
	IntToS= Trim(Str(W))
  
End Function

Function IntToS_f(W,f)
	' --  neue Funktion mit Anzahl Dezimalstellen
	W=Round(W,f)	
	IntToS_f= Trim(Str(W))
End Function


'Reset the actual view
Sub ResetActV
   ActV.View=-99999
   ActV.IPX=0
   ActV.IPY=0
   ActV.IPZ=0
   ActV.RotA =0
   ActV.TipA =0
End Sub

Function View0SurfacePart
  View0SurfacePart=False'equal(ActV.View,0) 
End Function

'***********************************************************************************
'*************************************  Filemacros  ********************************
'***********************************************************************************

'open file
Function File_Open(NCName) As Long 
Dim FileNo As Long  
Dim fold As String 
	fold = ncpathGlobal+NCName
    If FileExist(fold) Then
		FileNo= FOpenWrite(fold)  
		If FileNo=-1 Then
			Exit All
 		Else
      		FClose(FileNo)
    		Kill(fold)
		End If
    End If
	    
    FileNo= FOpenWrite(fold)
    If FileNo=-1 Then
    	pp_err(1,fold+" could not be opened")
    End If
    File_Open = FileNo
End Function


'close file
Sub FileClose
    FClose(NCFileNo)

End Sub

'global command function
Function StrToCom(Str)
  StrToCom="; --- "+Str + " ---"
End Function


'write line with line number
Function wcnc(ncs,Optional SuppressLineNo As Boolean)
Dim ncstr As Variant

' If NCLine=1070 Then Stop
'NCLine = 0
' If InStr(ncs,"SpeedCall")>0 Then Stop
	If WritingNCData = True	Then
		If (Len(ncs)>0) And (ncs<>"G1") Then
			' --
			' -- MW 27.04.2007 09:32:27 keine leere G1 Zeilen ausgeben 5-Axis interpol.
			' --
			' Neu MW 17.04.2007 - keine Leerzeilen ausgeben
		    'Print #1,"N";Trim(Str(NCLine));" ";ncs
		    If SuppressLineNo Then
			    ncstr = ncs
		    Else
			    ncstr = "N"+Trim(Str(NCLine))+" "+ncs
			End If
 			FWriteln(NCFileNo,ncstr)
		    NCLine=NCLine+JobPara.lStp
		End If
	End If
End Function

'write NC code and command
Function wcncAddCom(ncs,Com,Optional forced As Boolean,Optional sl=False)
    'wcnc(ncs+"    ")
    If mPara_Add.WRITE_COMMENTS Or forced Then
		If sl Then
			' ohne Zeilennummerierung			
	    	wcncwo(ncs+"    "+StrToCom(Com))
		Else
	    	wcnc(ncs+"    "+StrToCom(Com))
	    End If
	Else
		If sl Then
	    	wcncwo(ncs)
		Else
		    wcnc(ncs)
		End If
	End If
	
End Function


Function wcncCom(Com,Optional forced As Boolean)
	If mPara_Add.WRITE_COMMENTS Or forced Then
	    wcnc(StrToCom(Com))
	End If
End Function



' -- ohne Zeilennummern
Sub wcncwo(ncs)
Dim ncstr As Variant

	If WritingNCData = True	Then
		If (Len(ncs)>0) And (ncs<>"G1") Then
			' keine leere G1 Zeilen ausgeben 5-Axis interpol.
			' keine Leerzeilen ausgeben
		    'Print #1,"N";Trim(Str(NCLine));" ";ncs
		    ncstr = ncs
			FWriteln(NCFileNo,ncstr)
		End If
	End If
End Sub


'write safety absolut
Sub wSafetyAbs(Safety)
	' for all aggregats at the moment
	If Not Safety Then
		wcncCom("Go Safety")
		
		WCNC_SUB(SUB_TRANSOFF)
		WCNC_SUB("G90 D0")
		WCNC_SUB("SUPAZ")
	End If
	
	'ResetActV
	Safety=True
End Sub







' ------------------------------------------------------------------------------------------
' ------------------------------------------------------------------------------------------
' ------------------------------------------------------------------------------------------
' ------------------------------------------------------------------------------------------
' Funktionen fuer                  Aggregat - Gruppe 2   5-ACHS   
' ------------------------------------------------------------------------------------------
' ------------------------------------------------------------------------------------------
' ------------------------------------------------------------------------------------------
' ------------------------------------------------------------------------------------------


Function GetZeilennummer(s) As String
Dim i As Long
Dim wert As String
   If Mid(s,1,1) <> "N" Then 
      Exit Function 
    End If
 
 
    i=2
	While (Mid(s,i,1) <> Chr(32)) And (i<Len(s))
		wert = wert + Mid(s,i,1)
		i = i + 1
	Wend
	GetZeilennummer = wert 
	
End Function
		

' ------------------------------------------------------------------------------------------
' ------------------------------------------------------------------------------------------
' ------------------------------------------------------------------------------------------

Function Check_drehzahl(P_Speed,T_Speed) As Double
	Dim Speed As Double
	
    	'Check the Speed for Process with the maximum Tool-Speed
    	If Abs(P_Speed)<=Abs(T_Speed) Then
    	    ' Programmierte Spindeldrehzahl erlaubt
    	    Speed=P_Speed
    	Else 
    	    ' Programmierte Spindeldrehzahl zu hoch
    	    ' der Werkzeugverwaltung hinterlegte Spindeldrehzahl wird verwendet
    	    Speed=T_Speed
    	End If
		Check_drehzahl=Speed/100
	
End Function




Function GetSpindleCodeString(SpindlecodeAsString)
Dim i As Integer
Dim erg As Double
    erg=0 
	For i = (Len(SpindlecodeAsString)) To 1 Step -1
	
		If Mid$(SpindlecodeAsString,i,1)="1" Then erg=erg+exponent2(Len(SpindlecodeAsString)-i)
	Debug.Print erg	
	Next
	SpindlecodeAsString = IntToS(erg)
	
End Function



Function GetZMax(DFlag,Depth)
    Select Case DFlag
    Case 0
      GetZMax=Depth    
    Case 1
        GetZMax=DZMax01
    Case 2
        GetZMax=DZMax02
    Case 3
        GetZMax=DZMax03
    Case 4
        GetZMax=DZMax04
    Case 5
        GetZMax=DZMax05
    Case 6
        GetZMax=DZMax06
    Case 7
        GetZMax=DZMax07
    Case 8
        GetZMax=DZMax08
    Case 9
        GetZMax=DZMax09
    End Select
End Function




Function init_MachineData
Dim BList(5) As Long 
Dim I As Integer 

	
'	mPara_Add.Laser_HeadID = IIf(MT_Get_MachPara_Add(1200)="",110,MT_Get_MachPara_Add(1200))
	' -
'	mPara_Add.ShowTravLPointer = IIf(MT_Get_MachPara_Add(1070)="",0,MT_Get_MachPara_Add(1070))
'	mPara_Add.ShowPadsLPointer = IIf(MT_Get_MachPara_Add(1071)="",1,MT_Get_MachPara_Add(1071))
'	mPara_Add.ShowWorkPieceContour = IIf(MT_Get_MachPara_Add(1072)="",1,MT_Get_MachPara_Add(1072))
	' -
'	mPara_Add.PARK_DIST_X_Field1 = IIf(MT_Get_MachPara_Add(1130)="",500,MT_Get_MachPara_Add(1130))
'	mPara_Add.PARK_DIST_X_Field2 = IIf(MT_Get_MachPara_Add(1131)="",800,MT_Get_MachPara_Add(1131))
	' - 
'	mPara_Add.sc_minfeed = 30
'    If Not MT_Get_MachPara_Add(1015)="" Then
'		mPara_Add.sc_minfeed = StrToFloat(MT_Get_MachPara_Add(1015))
'	End If
'	mPara_Add.sc_contprec = 0.05
'	If Not MT_Get_MachPara_Add(1016)="" Then
'		mPara_Add.sc_contprec = StrToFloat(MT_Get_MachPara_Add(1016))
'	End If
		
	' -
'	mPara_Add.Threshold1 = IIf(MT_Get_MachPara_Add(100100)="",120,MT_Get_MachPara_Add(100100))
'	mPara_Add.Threshold2 = IIf(MT_Get_MachPara_Add(100101)="",170,MT_Get_MachPara_Add(100101))
'	mPara_Add.Threshold3 = IIf(MT_Get_MachPara_Add(100102)="",220,MT_Get_MachPara_Add(100102))
	' -
'	mPara_Add.KEEP_ZSIC_AFTER_TC = IIf(MT_Get_MachPara_Add(1020)="",False,MT_Get_MachPara_Add(1020))
	MT_Get_ID_MachinePara(1100,False,mPara_Add.WRITE_COMMENTS)
'	JobPara.isg = IIf(MT_Get_MachPara_Add(1000)="",False,MT_Get_MachPara_Add(1000))
'	mPara_Add.Script_Info = IIf(MT_Get_MachPara_Add(1101)="",False,MT_Get_MachPara_Add(1101))

	
	'mPara_Add.WithPadPos = IIf(MT_Get_MachPara_Add(20050)="",False,MT_Get_MachPara_Add(20050))
	
	'mPara_Add.WriteWorkTypeInfo = IIf(MT_Get_MachPara_Add(20051)="",False,MT_Get_MachPara_Add(20051))
End Function

Function Init_JobData
Dim ddd As Variant 
'	JobPara.isg = True
    JobPara.Activ_Fields = MCDATA.ActiveFields	'  Aktive Felder 1=links 2=rechts 3=gekoppelt
	JobPara.laser_activ = PostSettings.LaserActive ' Laser aktiv - dann mit Laserpointer Konturen abfahren
    JobPara.NPX = 99999.99 					' Nullpunkt X
    JobPara.NPY = 99999.99					' Nullpunkt Y
    JobPara.NPZ = 99999.99					' Nullpunkt Z
	JobPara.HPGL_TimeStamp = PostSettings.LaserTimecode	
	JobPara.Add_ZSic = NCData.ProgInfo.SupplementZOffset
	JobPara.Jumps_in_NC	= False ' Val(MT_Get_MachPara_Add(1005))
	JobPara.Jumpvar = "V.E.M_DataINT[29]"
	JobPara.JumpAktPos = 0
	JobPara.JumpCount = 0
	JobPara.JumpList = 0
	ddd = Rnd()
	JobPara.JumpStamp = Replace(ddd,",",".")

	JobPara.diniso.Activ = False
	JobPara.diniso.Filename_EXT = ""
	' -----------------------------------------------------------------------------------
	JobPara.SUPPRES_LAST_POINT_DINISO = False
	If Val(MT_Get_MachPara_Add(2020))=1 Then
		JobPara.SUPPRES_LAST_POINT_DINISO = True
	End If
	
	
End Function


Function init_Marker
	Marker.Last_Bm.BM1 = 0
	Marker.Last_Bm.BM2 = 0
	Marker.Last_Bm.BM3 = 0
	Marker.Last_Bm.GroupCode = 0
    Marker.Last_DH_Process =""     ' marker lastproces DrillingV->DH Vertikal DrillingH->DH horizontal
    Marker.Last_DH_ToNo = -9999
	Marker.Last_DH_Tools=""
	Marker.FirstTime_DH_Drilling=True
	Marker.WP_Lastindex = -1
	Marker.WP_Actindex = -1
	Marker.Last_SuctionPos = -1
	'Marker.DINISO_PROCESS=False
	'Marker.DINISO_Mode=-1
	'Marker.HorDH_PullBack=False geht nicht, da globaler ncinfo zuerst kommt
	'Marker.HoodDynActiv=False
	Marker.TraoriOn=False

	Set Marker.BStris = CreateObject("NC_Data.NCData_SetOfString")	
	Set Marker.AStris = CreateObject("NC_Data.NCData_SetOfString")	

	Marker.ActProcess = 0   ' 

	Set Marker.fCommand1 = CreateObject("NC_Data.NCData_SetOfString")	  ' WCNC_ISG_CONTOUR_START_EXT
	Set Marker.fCommand2 = CreateObject("NC_Data.NCData_SetOfString")	  ' WCNC_ISG_CONTOUR_END_EXT
	Marker.Haube_Activ = False
	Marker.Haube_Firsttime = True
	Marker.G0_Up_DH = True  ' Rueckzug Standard = G0
	If TDATA.MachineData.DrillingHeadsCount>0 Then
		If Not TDATA.MachineData.GetDrillingHead_Index(0) Is Nothing Then
			If Not TDATA.MachineData.GetDrillingHead_Index(0).Additions.GetAddition_ID(999) Is Nothing Then
				If Val(TDATA.MachineData.GetDrillingHead_Index(0).Additions.GetAddition_ID(999).Value)>0 Then
					' Voreinstellung fuer Rueckzug aus Bohrloch -> ueberschreibend ueber auch ueber NCIExt 90500 Para1 = 57
					Marker.G0_Up_DH = False
				Else
					Marker.G0_Up_DH = True
				End If
			End If
		End If
	End If

End Function


Function ClearObjects

	Marker.BStris.Clear 	 '  Marker erzeugt in InitMarker
	Marker.AStris.Clear 	 '  Marker erzeugt in InitMarker 	
	Marker.fCommand1.Clear
	Marker.fCommand2.Clear
	
End Function


Function wcnc_Workpiece_Info
Dim wp As TWPI
	wp = WPI(Marker.wp_actindex)

	If (Marker.wp_actindex >=0) And (Marker.wp_actindex<= UBound(WPI)) Then

		wcncCom("WP:"+FToS(Marker.wp_actindex)+" Stop:"+(wp.SName)+" X:"+FToS(wp.Sox)+" Y:"+FToS(wp.Soy)+" Z:"+FToS(wp.Soz))
		wcncCom(wp.WPName)
		wcncCom("FX:"+FToS(wp.WPx)+" FY:"+FToS(wp.WPy)+" Z:"+FToS(wp.WPz))
	End If
End Function

Function AddLog(stri As String)
	ReDim Preserve LogArr(UBound(LogArr)+1) 
	LogArr(UBound(LogArr))=stri
	
End Function


Function Get_Language_info As String

Dim iiSet As Object
Dim Language As Object
  
	Set iiSet = CreateObject("Hops_DLLInterface.CampusSettings")	
	iiSet.GetActualLanguageParameter(JobPara.language.ID,JobPara.language.display,JobPara.language.Ext)
	iiSet.GetDefaultLanguageParameter(JobPara.language.id_default,JobPara.language.display_default,JobPara.language.Ext_Default)
   	Set iiSet = Nothing
	
End Function

Function Get_Hops_Path As String

Dim iiSet As Object
Dim Language As Object
  
	Set iiSet = CreateObject("Hops_DLLInterface.HopsSettings")	
	JobPara.HopsPath = iiSet.hopspath
   	Set iiSet = Nothing
	
End Function


' holt Fehlermeldung aus der Datei ppscript_de.ini in Abhaengigkeit der gewaehlten Sprache
Function GetErrMsg(no,stri,mode) As String

Dim iiSet As Object
Dim Language As Object
Dim errstri As Variant
Dim path As String
Dim path_Default As String

	path  = JobPara.hopspath+"language\moduls\ppscript\ppscript"+JobPara.language.Ext+".ini"
	path_Default  = JobPara.hopspath+"language\moduls\ppscript\ppscript"+JobPara.language.Ext_Default+".ini"
  
	Set iiSet = CreateObject("BasicExt5.BasicExtension5")	
	errstri = iiSet.IniFileReadstr(path,"errmsg",IntToS(no),"")
	If errstri="" Then
  		errstri = iiSet.IniFileReadstr(path_Default,"errmsg",IntToS(no),stri)
	End If 
	If mode=1 Then
		errstri = "PPScript("+IntToS(no)+") - " + errstri
	End If
	GetErrMsg = errstri
   	Set iiSet = Nothing
	
End Function


Function GetAddZSic As Double
	GetAddZSic = JobPara.add_zsic
End Function


Function Reset_FirstTime_Viewchange
	If mPara_Add.KEEP_ZSIC_AFTER_TC Then
		Firsttime_Viewchange = True
	End If
End Function




Function Version_Check(Target_Version) As Boolean
Dim Version As Variant
Dim Versi As Boolean

	GetVersion5(Version)
	Versi = False
	
	Version = Replace(Version,".",";")
	
	Target_Version = Replace(Target_Version,".",";")
	
	' wegen Saegen als Fraesen mindestens Version 5.7.0.54
	If Val(Param(1,Version)) > (Val(Param(1,Target_Version))) Then
		' 6.x.x.x oder hoeher
		Versi = True
	ElseIf Val(Param(1,Version)) = (Val(Param(1,Target_Version))) Then
		' 5.x.x.x 
		If Val(Param(2,Version)) > (Val(Param(2,Target_Version))) Then
			' 5.7.x.x  oder hoeher
			Versi = True
		ElseIf Val(Param(2,Version)) = (Val(Param(2,Target_Version))) Then
			' 5.7.x.x
			If Val(Param(3,Version)) > (Val(Param(3,Target_Version))) Then
				Versi = True
				' 5.7.0 oder hoeher
			ElseIf Val(Param(3,Version)) = (Val(Param(3,Target_Version))) Then
                ' 5.7.0.x			
				If Val(Param(4,Version)) > (Val(Param(4,Target_Version))) Then
					Versi = True
					' 5.7.0 oder hoeher
				ElseIf Val(Param(4,Version)) = (Val(Param(4,Target_Version))) Then
					' 5.7.0.54 oder hoeher
					' alles ok
					Versi = True
				End If
				
			End If
			
		End If
	
	End If
	
	Version_Check = Versi
	If Not Versi Then
		pp_Err(1513,Target_Version)
	End If
	
End Function


Function MT_GetToolId_Next_Process(Next_Working_Box,Next_Working_Head)

' -- 
' -- MW 20.02.2012
' -- ID des benutzten Werkzeug naechster Prozess
' --

Dim Next_Working_Tool As THopsBasicToolExt   ' entspricht somit dem naechsten ToolChange - Tool
Dim I,Find As Long

	Next_Working_Box = -1
	
	For I =  Marker.ActProcess To Marker.CountOfTool-1 
		Next_Working_Box = ToolArray(I).t.ID
		Next_Working_Head = ToolArray(I).HId
		'If Next_Working_Head=Find Then
		'	MT_SetTHopsBasicToolExt(BeforeT,Next_Working_Box,Next_Working_Head)		
		Exit For
		'End If
	Next I
		
	MT_GetToolId_Next_Process = Next_Working_Box
End Function

Function Set_LastTool_ActTool()
Dim Dummy As Object
	
	Set LastT.t = TDATA.GetTool_ID(ActT.T.ID)
	Set Dummy = LastT.T
	
	Set LastT.t_dh = Dummy
	
	' --  Wegen ueberpruefung auf pneum. schwenkbarer Saege in Werkzeugabwahl MT_Func / Function MT_Tool_Re_Change
	If Not ActT.T_PH Is Nothing Then
		Set LastT.t_ph = ActT.t_ph
	End If
	
	
	
	Set LastT.t_dhsaw = Dummy
	
	' --------------------------------
	''If MT_IsGearBoxTool(LastT) Or MT_IsGearBoxTool_Special(LastT) Then
	' MW 23.12.2015
	If MT_IsGB(LastT) Then
		Set LastT.gb = Dummy.GearBox
		
		' MW 23.12.2015 nur wenn es auch Gearbox ist
		Set LastT.t_gb = Dummy
	End If
	
	'Set LastT.t_gb = Dummy
	' --------------------------------
	
	LastT.HId = ActT.HId
	LastT.aggname = ActT.aggname
	
	' -- 5 Axis
	Set LastT.h = TDATA.GetProcessHead_ID(LastT.HId)
	
	If MT_Is_Vertical_StandardTool5Axis(LastT) Then
		' Zusatzinfos von Spindel
		Set_Ph_Additions(LastT,LastT.h.Additions)
	End If
	
End Function


Function ClearMTData
Dim i As Integer
  MT_ClearTHopsBasicToolExt(ActT)
  MT_ClearTHopsBasicToolExt(LastT)
  MT_ClearTHopsBasicToolExt(FirstT) ' MW 24.02.2016
  
  If Marker.CountOfTool>0 Then
	  For i = LBound(ToolArray) To UBound(ToolArray) Step 1
    	MT_ClearTHopsBasicToolExt(ToolArray(i))
	  Next i
  End If
  ProcessInfoClear(PParaLast)
  ProcessInfoClear(PPara)
  ProcessInfoClear(PParaNext)
End Function




Function wcnc_NCIExt_Strs(iNC As Object,Optional pointoftime=-1)  ' Alle Strings ueber ParaCount wegschreiben
Dim i As Long 
Dim j As Long
Dim ParaDouble As Double
Dim ParaString As String
Const STR_START = 5   ' ab PARA6 werden alle als abzusetzende Strings interpretiert
				
	For j = STR_START To iNC.NCIExt.ParaCount-1 
		If iNC.NCIExt.GetString(j,ParaString) Then
			' String - Wert 
			If Len(ParaString)>0 Then
				' inc.para2=1 -> Zeilennummerierung unterdrucken
				wcncAddCom(ParaString,"NCIExt "+IntToS(iNC.Kind)+" PoT="+IntToS(pointoftime)+" sL="+IntToS(iNC.Para2),True,equal(iNC.Para2,1))
			End If
		End If
		
	Next j
	
End Function
				

Function wcnc_NCIExt_Before(pointoftime)
Dim i As Long 
Dim iNC As Object ' INCNCInfo
' MW 17.02.2016 
' Vorwirksame NCIExt absetzen
	For i =  0 To UBound(PPara.NCiExtB) 
		Set iNC = PPara.NCiExtB(i) 
		If Not iNC Is Nothing Then
			Select Case iNC.Kind
				Case 70000
				
				
					If equal(iNC.Para1,pointoftime) Then    ' 
					
						wcnc_NCIExt_Strs(iNC,pointoftime)   ' Alle Strings ueber ParaCount wegschreiben
					
'						For j = 0 To iNC.NCIExt.ParaCount-1 
'							If iNC.NCIExt.GetFloat(j,ParaDouble) Then
'								' Double - Wert 
'							ElseIf iNC.NCIExt.GetString(j,ParaString) Then
'								' String - Wert 
'								If Len(ParaString)>0 Then
'									wcncAddCom(ParaString," -------  NCIExt "+IntToS(iNC.Kind)+" PointOfTime = "+IntToS(pointoftime),True)
'								End If
'							End If
'							
'						Next j
					End If
			End Select
		End If
	Next i
	'If PPara.NCiE.blower.activ = True Then
	'	If (pointoftime = PPara.NCiE.blower.pot) Then
	'		WCNC_BLOWING(PPara.ActT)
	'	Else
	'		If pointoftime=50 Then
	'			WCNC_BLOWINGOFF(PPara.ActT)
	'		End If
	'	End If
	'End If

End Function

Function wcnc_NCIExt_After()
Dim i As Long 
Dim iNC As Object ' INCNCInfo

	' Nachwirksame NCIExt absetzen
	For i =  0 To UBound(PPara.NCiExtA) 
		Set iNC = PPara.NCiExtA(i) 
		If Not iNC Is Nothing Then
			Select Case iNC.Kind
				Case 80000
					wcnc_NCIExt_Strs(iNC)   ' Alle Strings ueber ParaCount wegschreiben
			End Select
		End If
	Next i
	
End Function



Function is_WorkC_OptionBit(Bit,OptionDez) As Boolean 
Dim suche As Long

	suche = exponent2(Bit)
	is_WorkC_OptionBit = IIf((OptionDez And suche)=suche,True,False)

End Function


Function isDINISO_Process
Dim resu As Boolean
	resu = False
	If (PPara.PreObjectTyp = otNCInfoProcessMPs) Or (PPara.PreObjectTyp = otNCInfoProcess) Then
		If NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Kind=77710 Then
			resu = True
		End If
	End If

	isDINISO_Process = resu
End Function

Function isDINISO_LastProcess
Dim resu As Boolean
	resu = False
	
	If (ppara.plNo>1) Then

		If (aPPara(ppara.plNo-1).p.PreObjectTyp = otNCInfoProcessMPs) Or (aPPara(ppara.plNo-1).p.PreObjectTyp = otNCInfoProcess) Then
			If NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-2).Kind=77710 Then
				resu = True
			End If
		End If
	End If
	isDINISO_LastProcess = resu
End Function


Function IsDINISO_No_Speed
Dim resu As Boolean
	resu = False
	If (PPara.PreObjectTyp = otNCInfoProcessMPs) Or (PPara.PreObjectTyp = otNCInfoProcess) Then
		' NCINFOProcess als Bohren oder Fraesen
		If NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Kind=77710 Then
			resu = NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Para10=0
		End If
	End If
	IsDINISO_No_Speed = resu
End Function

Function IsDINISO_No_TC
Dim resu As Boolean
	resu = False
	If (PPara.PreObjectTyp = otNCInfoProcessMPs) Or (PPara.PreObjectTyp = otNCInfoProcess) Then
		' NCINFOProcess als Bohren oder Fraesen
		If NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Kind=77710 Then
			resu = NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Para8=0
		End If
	End If
	IsDINISO_No_TC = resu
End Function

Function IsDINISO_No_VC
Dim resu As Boolean
	resu = False
	If (PPara.PreObjectTyp = otNCInfoProcessMPs) Or (PPara.PreObjectTyp = otNCInfoProcess) Then
		' NCINFOProcess als Bohren oder Fraesen
		If NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Kind=77710 Then
			resu = NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Para9=0
		End If
	End If
	IsDINISO_No_VC = resu
End Function



Function DINISO_Get_Liftpos
Dim resu As Integer
	resu = -1
	If (PPara.PreObjectTyp = otNCInfoProcessMPs) Or (PPara.PreObjectTyp = otNCInfoProcess) Then
		' NCINFOProcess als Bohren oder Fraesen
		If NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Kind=77710 Then
			resu = NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Para11
		End If
	End If
	DINISO_Get_Liftpos = resu
End Function



Function WCNC_EXTCALL_DINISO()
Dim FileN As String 
' EXTCALL "/_N_SPF_DIR/_N_FIELD1_SPF"
' EXTCALL("LOCAL_DRIVE:HOPS.WPD/FIELD1.SPF")	


	FileN = JobPara.diniso.Filename_EXT

	If JobPara.diniso.Activ Then
		If Len(FileN) > 4 Then
			wcnc("EXTCALL("+Chr(34)+"LOCAL_DRIVE:HOPS.WPD/"+FileN+Chr(34)+")")
		End If
	End If
End Function



Function Get_ID_RESULT(value As Variant, default As Variant, result As Variant ) As Boolean 
Dim ok As Boolean 
	ok = True
	
	If VarType(default)=vbBoolean Then
		' true or false zurück
		If value = "0" Then
			result=False
		ElseIf value = "1" Then
			result=True
		Else
			ok = False
			'pp_err(140,inttos(ID))
		End If
	Else
		If UCase(TypeName(default))="DOUBLE" Then
			result = StrToFloat(value)
		Else
			result = value
		End If
	End If
	
	Get_ID_RESULT = ok 
End Function

Function wcnc_Haube5A(Pos,Optional Trail As Boolean )
Dim IsGBoxT As Integer
Dim VP_HEADID As Integer
Dim VP_SETTING As Integer
Dim VP_POS As Double
Dim VP_VORPOS_X As Double
Dim VP_VORPOS_Y As Integer 
Dim VP_VORPOS_Z As Integer 

	VP_HEADID = PPara.HId  ' gibt es immer
	VP_SETTING = 0
	VP_POS = 0
	VP_VORPOS_X = 0 
	VP_VORPOS_Y = 0
	VP_VORPOS_Z = 0

	
	If (Pos>0) Then  ' If Equal(Wi,0) Then						'Winkel des 5-Achskopfes=0° vorlegen erlaubt
		'If (Haube.P5AchsAktiv=False) Or (Marker.Haube_Firsttime) Then
		VP_POS = Pos
		VP_SETTING = 1
'		If PPara.sHood.Mode=0 Then
'			wcnc(PPara.actT.pH_ADD.HaubeDown(Pos))
'		ElseIf PPara.sHood.Mode=1 Or PPara.sHood.Mode=2 Then '1 Fix 2 trailing
'			If PPara.sHood.Mode=2 Then 
'				Trail=True
'			Else
'				Trail=False
'			End If
'			If MT_IsGB(PPara.actT) Then
'				IsGBoxT=1
'			Else
'				IsGBoxT=0
'			End If
'			If Trail=True Then
'				wcnc("CH_SUCTION("+"1,"+PPara.sHood.RPosLi+","+FToS(PPara.sHood.Tip_LiE)+",0,"+IntToS(IsGBoxT)+")")
'				'wcnc(PPara.sHood.RPosWC)
'			Else
'				wcnc("CH_SUCTION("+"1,"+PPara.sHood.RPosWC+","+FToS(PPara.sHood.Tip_WC)+",0,"+IntToS(IsGBoxT)+")")
'				'wcnc(PPara.sHood.RPosWC)
'			End If
'			
'		Else 
'			AddMistake("Mode Not allowed")
'		End If
		'End If
		CC(SUB_HOOD,VP_HEADID,VP_SETTING,VP_POS,VP_VORPOS_X,VP_VORPOS_Y,VP_VORPOS_Z)
		Marker.Haube_activ = True
	Else									
		If (Marker.Haube_activ) Or (Marker.Haube_Firsttime) Then
			' wcnc("CH_SUCTION(0,0,,,)")
			CC(SUB_HOOD,VP_HEADID,VP_SETTING,VP_POS,VP_VORPOS_X,VP_VORPOS_Y,VP_VORPOS_Z)
			'wcnc(PPara.actT.H_ADD.HaubeUP)
		End If 
		Marker.Haube_activ=False
	End If
	Marker.Haube_Firsttime = False
	
	
End Function



Function wcnc_Haube5ATrailOn(Pos,Optional Trail As Boolean )
Dim IsGBoxT As Integer
	If MT_IsGB(PPara.actt) Then
		IsGBoxT=1
	Else
		IsGBoxT=0
	End If
	If PPara.sHood.Mode=2 And Pos>0 Then
		If Trail=True Then 
			If PPara.sHood.preobt=otSawing Then
				wcnc("G0 G40 X0 Y0 Z0")
			End If
			Marker.BStris.Add("CH_SUCTION("+"11,"+IntToS(PPara.sHood.RPosLI)+","+FToS(PPara.sHood.Tip_LiE)+",1,"+IntToS(IsGBoxT)+")")
			PPDLLAddStrsAfterLeadIn(Marker.BStris,0)
			'wcnc("CH_SUCTION("+"11,"+IntToS(PPara.sHood.RPosWC)+","+FToS(PPara.sHood.Tip_LiE)+",1)")
		Else
			wcnc("CH_SUCTION("+"11,,,0,)")
		End If
		'wcnc("TRAIL")
	End If
	
End Function
