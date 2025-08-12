' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \hh7\pp_global.bas
' -- 
' -----------------------------------------
'#uses "pp_math.bas"
'#uses "pp_isg.bas"
'#uses "pp_siemens.bas"

Option Explicit

'***********************************************************************************
'*************************************  GLOBALS  ***********************************
'***********************************************************************************

Global Const SCRIPT_VERSION="7.0.9.0" 
' --> SETUP_VERSION wird aus pp.ini gelesen wo diese wiederrum durch hh_settings.exe (PP-Setup) geschrieben wird
' ------------------------------------------------------------------------------------
' --
' -- Name - Definitions for the subs on the cnc - controller

Global Const SPF_TCheck = "CP_TCheck"  ' check tools
Global Const SPF_TC = "CP_TC"  ' sub name on cnc-controller for the toolchange
Global Const SPF_TCarr = "CP_TCPara"   ' sub name for setting the TCarr - parameters
Global Const SPF_StartProg = "CP_START"   ' Start Programm
Global Const SPF_EndProg = "CP_END"   ' ende Programm
Global Const SPF_DHCode = "CP_DHCode"  ' code for drillers
Global Const SPF_TSpeed = "CP_TSpeed"  ' setting for tool speed
Global Const SPF_TCLift = "CP_Lift"  ' Vorlegehub steuern
Global Const S__PF_TCCHKRPM = "CP_CHKRPM"  ' Drehzahlueberwachung
Global Const SPF_AGGCheck = "CP_RELEASE"  ' Agg ok vorgelegt laeuft etc.
Global Const SPF_REQUEST_FLEX = "CP_SETAPTANGLE"  ' Anforderung die Achsen vom Flex 5 zu stellen
Global Const SPF_LASERONOFF = "CP_LASER" ' fuer Laser AN/Ausschalten
Global Const SPF_PREINFO ="CP_PREINFO"
Global Const SPF_HOOD ="CP_HOOD"    ' Absaughaube 5-Axis 
Global Const SPF_GEOAX = "CP_GEOAX"  
Global Const SPF_Szene = "CP_SZENE"  
Global Const SPF_CONTOUR_START = "CP_CONTOUR_START"    ' Setzt Dynamik und Konturgenauigkeit HSC - Achsbeschleunigung
Global Const SPF_CONTOUR_END = "CP_CONTOUR_END"        ' Ende Dynamik
Global Const SPF_CHK_SPEED = "F_CHKSPEED"
'Global Const SPF_HOODDYN = "CP_HOODDYN"    ' MW 18.02.2016 wurde nicht Steuerungsseitig realisiert
Global Const SPF_DYNAMIC = "CP_DYNAMIC"     ' MW 01.06.2016
Global Const SPF_HLaserPrg = "CP_HLASER"     ' AK 24.11.2016

'***********************************************************************************

Global Const PPEMPTY = -1    ' 
Global Const PPFLOAT = 0     ' 3.324
Global Const PPBOOLEAN = 1   ' False / True
Global Const PPINTEGER = 2   ' 2
Global Const PPSTRING = 3    ' STRING

'***********************************************************************************
'*************************************  Types  *************************************
'***********************************************************************************

Type TSP_EP_No_LeadInOut
	SP_x As Double
	SP_y As Double
	SP_z As Double
	SP_ax As Double
	SP_ay As Double
	SP_az As Double
	SP_Feedrate As Double
	SP_Speed As Double
	SP_RotA As Double
	SP_TipA As Double
	SP_TRC As Long
	SP_TA As Double
	SP_Distance As Double
	EP_x As Double
	EP_y As Double
	EP_z As Double
	EP_ax As Double
	EP_ay As Double
	EP_az As Double
	EP_Feedrate As Double
	EP_Speed As Double
	EP_RotA As Double
	EP_TipA As Double
	EP_TRC As Long
	EP_TA As Double
	EP_DMove As Long
	EP_DFactor As Double
	EP_Retreat As Long
	Dummy1 As String
	Dummy2 As String
	Dummy3 As String
	Dummy4 As String
	Dummy5 As String
	Dummy6 As String
	Dummy7 As String
	Dummy8 As String
	Dummy9 As String
	Dummy10 As String
	Dummy11 As String
	Dummy12 As String
	Dummy13 As String
	Dummy14 As String
	Dummy15 As String
	Dummy16 As String
	Dummy17 As String
	Dummy18 As String
	Dummy19 As String
	Dummy20 As String
End Type


'View adjustments


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


'Type TProcessMinMaxWindow
'	xMin As Double        ' kleinster X - Wert der Bearbeitung
'	yMin As Double        ' kleinster Y - Wert der Bearbeitung 
'	zMin As Double        ' kleinster Z - Wert der Bearbeitung 
'	xMax As Double        ' groesster X - Wert der Bearbeitung
'	yMax As Double        ' groesster Y - Wert der Bearbeitung
'	zMax As Double        ' groesster Z - Wert der Bearbeitung 
'	zMintmp As Double
'	zMaxtmp As Double
'End Type
'Global MinMaxW As TProcessMinMaxWindow


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


Type TMeasure
	MaxQuoteX As Double       ' Max. moegliche Quote ID 3000 -> darf nicht ueberschritten werden
	MaxMessDiffX As Double    ' Max. moegliche MessDifferenz ID 3001 wird im Messzyklus geprueft!
	QuoteXQD As Double        ' Definiert den X-Max Bereich in welchem Bohrungen sich auf einen gemessenen Wert beziehen 
	QuoteXQM As Double        ' Definiert den X-Max Bereich in welchem Fraes-/Saegebearbeitungen sich auf einen gemessenen Wert beziehen 
	MessSzene() As Boolean    ' Wenn True, dann muss fuer diese Szene gemessen werden
	Bea_Mea_activ As Boolean  ' Wenn True, dann X- Wert - Verrechnung aktiv
	Orientation As TOrientation  ' Info fuer Messrichtung 
End Type

Global Type TMeasPart
	PartNo As Integer           ' interne Teilenummer
	Amount As Integer  ' Anzahl Messungen
End Type

Global Type TMeasuring
	activ As Boolean
	NCParts() As TMeasPart   ' Messungen immer Werkstueckbezogen
End Type 


' Variables from interface "work-center"
Global Type ThopsJobPara
	Activ_Fields As Integer         ' Aktive Felder 1=links 2=rechts 3=gekoppelt
	Laser_Activ As Boolean          ' wird 1 gesetzt wenn Punktlaser aktiviert 
    NPX As Double					' Nullpunkt X
    NPY As Double					' Nullpunkt Y
    NPZ As Double					' Nullpunkt Z
    RealNCFileName As String        ' c:\nc\Field1.spf
    Park As Integer					' Parkpos 1 = Links hinten 2=rechts hinten 3=mitte hinten
    ParkX As Double
    Parky As Double
    Language As TLanguage           ' wird aus iiSettings ermittelt
    HopsPath As String 				' wird aus iiSettings ermittelt
    HPGL_TimeStamp As String        ' Neu MW 2.8.2005 fuer check ob korrekte HPGL-Datei
    Add_ZSic As Double              ' Neu MW 14.09.2005 zusaetzliche Z-Sicherheit
    ISG As Boolean 
    ' --  Radius fahren spezial - Mode (wenn Radius welcher gefahren wird, dem Werkzeugradius entspricht - inkl. Toleranzangabe)
	Jumps_in_NC As Boolean                   ' MW 14.11.2012 - > Aktivierung Sprungmarken
	Jumpvar As String						 ' MW 12.12.2012 - > Name der Sprungvariablen -> Diese muss nummerisch auf 1.. gesetzt werden !
	JumpAktPos As Long                       ' MW 12.12.2012 - > Fortlaufender Zaehler -> 
	JumpCount As Long                        ' MW 12.12.2012 - > Pruefzahl
	JumpList As Integer                      ' MW 12.12.2012 - > Liste der Einsprungmarken
	JumpStamp As Variant                      ' MW 12.12.2012 - > Randomized Nummber
	is_Evo As Boolean                    ' MW 31.07.2013   TMData.MachineData.MachineParameter.MachineNo ID muss zwischen 200002 und 200202 
'	DynamicSuctionNC As Boolean            ' MW 10.12.2013 NC-Seitig gesteuerte Dyn. Haube MW 02.02.2016 entfaellt synchronaktion isg nicht moeglich lt. AK
	Mea As TMeasure           ' MW 05.03.2014   Parameter der Messwertverechnung
	ActScene As Integer       ' MW 05.03.2014   Zaehler der Szene in der man sich aktuell befindet - Beginnend bei ein 
	TC_SC() As Integer        ' MW 30.03.2015   Toolchange -> Szenen - Marker ueber Vorlauf
	TC_PreInfo_Activ As Boolean     ' MW 09.06.2015 Merker ob Werkzeug Vorab Information geschrieben wird (optimiert nur einmaliges lesen)
    P_Info As String          ' -- MW 21.12.2015 Info- String ueber die Bearbeitung
    lStp As Integer         ' MW 14.01.2016
    is_5Axis_Machine As Boolean    ' MW 20.01.2016 steuert WriteNCMillingPointsHeadData in InitDLLMPs_Milling
    TimerFullSecs As Double          ' MW 01.02.2016 Timer ueber ALLES
    TimerInitTL As Double            ' MW 01.02.2016 Timer wird bei INITToolList gesetzt
	TCP_ON As String                 ' MW 12.02.2016 nicht mehr ueber ID
	TCP_OFF As String                ' MW 12.02.2016 nicht mehr ueber ID
	TRC_Strategy As Integer 		' ID 10100 MW 01.06.2016 Strategie fuer Aufbau Fraeserradiuskorrektur
	TC_SpeedInfo As Boolean          ' MW 31.05.2017 ID #2010 
	Measuring As TMeasuring          ' MW 26.04.2019 dient zur Festlegung der MessArrays
End Type
Global JobPara As THopsJobPara


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
    WP_ActIndex As Long      '  Workpiece - Index - Zaehler
    WP_LastIndex As Long      '  Workpiece - Index - Zaehler
    'Pneumatic_Channel() As Long   ' pneumatik channel - merker, da NCInfo viel zu frueh kommt - wird dann erst bei StartMilling aufgerufen
    Programmed_DH_Speed As Double   ' Merker, programmierte Drehzahl Bohrkopf
    Last_SuctionPos As Integer   ' Merker fuer Absaugung
	'DINISO_PROCESS As Boolean   
	'DINISO_MODE As Integer ' Mode fuer DINISO-Programm
	'DINISO_LIFTPOS	As Integer ' Position fuer Vorlegehub -1 = bevorzugte Stellung
	'DINISO_TC As Integer     ' Neu MW 22.03.2005 DINISO - Aufruf mit Toolchange absetzen
	'DINISO_SPEED As Integer  ' Neu MW 22.03.2005 DINISO - Aufruf mit Drehzahl absetzen
	'DINISO_VC As Integer     ' Neu MW 22.03.2005 DINISO - Aufruf mit Ebene absetzen
	No_G0_Up_DH As Boolean       ' g0 abschaltbar ueber ncinfo 70 
	HorDH_PullBack As Boolean    ' MW 20.02.2007  ' fuer Rueckzugslogik beim horizontalen Bohren
	'HorMilling_PullBack As Boolean    ' MW 21.06.2007  ' fuer Rueckzugslogik beim horizontalen fraesen NCINFO 58 para2=1
	MachineStopActive As Boolean      ' -- MW 03.12.2008 17:24:29	' --
	Z_Schwenk As Double
	'XPosAfterToolChange	As Double		'AK 21.09.2011 naechste XPosition im ToolChangezyklus mitgeben
	AutoXStrategie As Integer		'AK 21.02.2012 - Strategieermittlung fuer Park und Umspannposition je nach Tischbelegung 
	RollerTrackDown As Boolean      ' MW 04.09.2013 Evolution 
	'HoodDynActiv As Boolean         ' MW 02.12.2013 CNC-seitige dyn. Haubensteuerung . (ueber Synchronbefehle)
	TraoriOn As Boolean             ' MW 03.04.2014 Merker fuer NCseitige 5Achs - Transformation
	FirstTool_PosX As Double        ' MW 09.06.2015 Merker 1. X-Pos -> ueber FirstTool
	OscilationOn As Boolean			' AK 03.11.2015 Merker Pendelachse aktiv	
    OffzCAxisMill_Activ As Boolean   ' MW 20.01.2016 G92 aktiv
    TCarr_Activ As Boolean           ' MW 20.01.2016 TCARR - Offset Winkelgetriebe (und Co.) aktiv
    LastLiftpos As Integer
	LastSpeed As Double     ' MW 16.02.2016 Merker fuer zuletzt ausgebene Spindeldrehzahl
	BStris As NCData_SetOfString    ' MW 24.02.2016   Liste der Strings fuer wegschreiben NCIExt nach der Anfahrbewegung ueber DLL-Milling
	AStris As NCData_SetOfString    ' MW 24.02.2016   Liste der Strings fuer wegschreiben NCIExt vor der Abfahrbewegung ueber DLL-Milling
	ActProcess As Long              ' MW 31.03.2016
	CountOfTool As Long             ' MW 31.03.2016
	fCommand1 As NCData_SetOfString    ' WCNC_ISG_CONTOUR_START_EXT
	fCommand2 As NCData_SetOfString    ' WCNC_ISG_CONTOUR_END_EXT
	MaxSceneNo as Integer		' AK 20.03.2019 Anzahl der Szenen speichern, letzte Szene bei Evo mit Stripcut X Aufruf
	XCUT_Done as Boolean			' AK 20.03.2019 
	AktProzessIsXMove as Boolean ' AK 19.04.2019 Erkennung X Trennschnitt f�r XCut
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
	G0_UP As Boolean            ' Rueckzug mit G0
End Type


' -------------------------------------------------------------
' -- Hier Type fuer Bohren mit Reihenbohrgetriebe mehrfach
'Global Type tMultiDrilling_GBHeadVert
'	dw As Double
'	angle As Double
'End Type

Global Type tUnderside
 	dw As Double
 	view_w As Double 
End Type


Global Type t5Axis
	Yes As Boolean   ' wenn Maschine mit 5-Achskopf ausgestattet
	ISG As Boolean      ' Feinunterscheidung - wenn ISG, dann handelt es sich um eine 5-Achs 
						' mit vorlegbarem Bohrkopf und keiner weiteren Spindel
						' MW Stand 09.05.2011
End Type

Global FiveAxis As t5Axis


' -------------------------------------------------------------
' -- Hier Type Werkzeugzusatzinformation fuer Fraesspindel 
' -- Neu MW 03.04.2007 5Axis
Global Type t_PH_Additions
	MaxDiamM5Turn5Axis As Double  ' -- MW 06.03.2014  #20050
	MaxDiamM5Turn5Axis_RedSpeed As Double ' -- MW 06.03.2014  #20051
	HoodThreshold_DynMode As Integer   ' MW 11.01.2017
End Type

Global Type tmPara_Add
	' DEF_PSaeg1 (90)       entfaellt -> bei geruesteter Saege und Spindel horizontal und Raster schwenkbar nicht notwendig
	Laser_HeadID As Integer  ' DEF_LASER1 (110)     ID 1200
	' -
	ShowTravLPointer As Boolean      ' (0)               ID1050
	ShowPadsLPointer As Boolean      ' (1)               ID1051
	ShowWorkPieceContour As Boolean  '(1)       ID1052 
	' -
	PARK_DIST_X_Field1 As Double     ' (500)   ID 1010
	PARK_DIST_X_Field2 As Double     ' (800)   ID 1011
	' -
	Threshold1 As Double   ' (120)   ID 100100   auch schon In V6
	Threshold2 As Double   ' (170)   ID 100101   auch schon In V6
	Threshold3 As Double   ' (220)   ID 100102   auch schon In V6
	' -
	KEEP_ZSIC_AFTER_TC As Boolean  ' (0)        ID 1020
	WRITE_COMMENTS As Boolean      ' (0)        ID 1100
	Script_Info As Boolean         ' (0)        ID 1101
	' -
	sc_minfeed As Double 
	sc_contprec As Double 
End Type

Global mPara_Add As tmPara_Add


' 24.11.2016 AK HLaserInfo
Global Type t_HLaser
	HLaserX_Active As Boolean                 ' Aktivierung HLaserX
	HLaserY_Active As Boolean                 ' Aktivierung HLaserY
	ActPosX As Double			
	ActPosY As Double			
	HLaserListTyp As Integer                    ' Liste der Positionen
	HLaserListX As Integer                      ' Liste der Positionen
	HLaserListY As Integer                      ' Liste der Positionen
	HLaserStamp As Variant                      ' Randomized Nummber
End Type

Global HLaserInfo As t_HLaser

'***********************************************************************************
'*************************************  Variables  *********************************
'***********************************************************************************

'global nc path
Global ncpathGlobal As String
Global NCNameGlobal As String
'aktual nc line number
Global NCLine As Long

Global ActV As TView
Global LastV As TView
Global ViewBefore As TView

Global FinishedPart As TFinishedPart
Global MovePara As TMovePara

Global LastPos As TPos

'true if safe position
Global Z_Is_Safety As Boolean
Global Z_Is_SafetyPart As Boolean


Global ToolChangeBeforeStr As String

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



Global Last_TC_Call_NCStr As String   ' mark for Toolchange call if same as before no toolchange will be called


Global Const DRILL_DHV="DRILLINGV"
Global Const DRILL_DHH="DRILLINGH"

' -- Unterdrueckung Anfahrt in 4-Achsen (X,Y,Z,C) wird fuer Maschinen mit getrailter A-Achse benoetigt
Global Const SPECIAL_ID_HEAD_NO_4AXISINTERPOL = 10010

' -- Neu AK 06.10.2009  
' -- Kennung fuer Werkzeugbearbeitung im Briskmode (DPI) ID aus Schneide Zusatzinfo
'Global Const ID_CONTOURMODEID     = 10600
'Global Const ID_CONTOURMODEACCEL  = 10601
'Global Const ID_CONTOURMODEJERK   = 10602
Global DH_View0 As TView

' -- Neu AK 03.11.2016  
' -- Kennung fuer Werkzeugbearbeitung im Pendelbearbeitungsmode Z - ID aus Schneide Zusatzinfo
Global Const ID_CONTOUROSC_ACTIVE 		= 10610
Global Const ID_CONTOUROSC_FEED   		= 10611
Global Const ID_CONTOUROSC_EXCURSION   	= 10612


' -- Neu AK 04.05.2011  
' -- Aufraeumflag fuer Bohrkopf heben bei vorgelegtem Bohrkopf
'Global ViewInfoToolChangeFlag   		As Boolean

'Save Information for Start and Endpoint from Hops
Global SP_EP As TSP_EP_No_LeadInOut

' erst wenn diese Variable True, dann setzt wcnc auch was ab
Global WritingNCData As Boolean
Global MoveTime_Result As Double

' Log-Datei Array
Global LogArr() As String

Global NCFileNo As Long   ' NEU MW 12.07.2005   oeffnen - und schreiben des NC-Programms umgestellt

'Global MultiDrilling_GBHeadVert As tMultiDrilling_GBHeadVert

Global UndersideTool As tUnderside


Global Const Fix_Zero = 1   ' G54 written Zeropoint 

Global g_OffPX As String
Global g_OffPY As String
Global g_OffPZ As String

Global g_PARKXVAR As String
Global g_PARKYVAR As String

Global g_TCARR As String
Global g_TCARROFF As String
Global g_MAX_LIMIT_ZPLUS As String
Global g_MAX_LIMIT_Z2PLUS As String
Global g_MAX_LIMIT_Z3PLUS As String
Global g_MAX_LIMIT_XPLUS As String
Global g_MAX_LIMIT_XMINUS As String
Global g_MAX_LIMIT_YPLUS As String
Global g_MAX_LIMIT_YMINUS As String
Global g_DCORRECTIONMARKER As String
Global g_LIFTOFFSETX As String
Global g_LIFTOFFSETY As String
Global g_LIFTOFFSETZ As String


' --------------------------------------------------
' --
' Viewchange Drillinghead
' -- nur Ebenen - Wechsel ohne Verfahrbewegung
' --------------------------------------------------
Sub wcncViewChange_DH(dh As tdh,View,LastView,ByVal IPX,IPY,IPZ,RotA,TipA,ByVal SPVX,SPVY,SPVZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)

    wcncCom("Viewchange DH View "+View)
	
	WCNC_IDD("TRANSOFF")
	
	WCNC_IDD("ATRANSAROT_DH",IPX,IPY,IPZ,RotA,TipA,0,0,0)
	
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
	If (JobPara.mea.Bea_Mea_activ) And ((JobPara.mea.Orientation=orVertical) Or (JobPara.mea.Orientation=orYPlus) Or (JobPara.mea.Orientation=orYMinus)) Then
		XToS=" X="+FToS(x)+"+"+ISG_MEA_X
	Else
		XToS=" X"+FToS(x)
	End If
End Function

Function YToS(Y)
  YToS=" Y"+FToS(Y)
End Function

Function ZToS(z)
'	If (JobPara.mea.Bea_Mea_activ) And ((JobPara.mea.Orientation=orXPlus)) Then
'		ZToS=" Z="+FToS(z)+"+"+ISG_MEA_X
'	Else
  ZToS=" Z="+FToS(z)
'	End If
End Function

Function XEqualToS(x)
  XEqualToS=" X="+FToS(x)
End Function

Function YEqualToS(Y)
  YEqualToS=" Y="+FToS(Y)
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
	' Neu 08.11.2004 MW 
	' -- nachfolgende Nullen z.B. bei 34.100 werden geloescht = 34.1
	' -- dadurch bei Dokus etc. kurzere Zeilenlaengen und weniger NC-Code
	' -- 
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
		' --  wirklichen Int- Wert ausgeben ohne Nachkommastellen: weder "," noch "."
		W=Round(W)	
	End If
	IntToS= Trim(Str(W))
  
End Function


Sub ResetActV
   ActV.View=-99999
   ActV.IPX=0
   ActV.IPY=0
   ActV.IPZ=0
   ActV.RotA =0
   ActV.TipA =0
End Sub


'***********************************************************************************
'*************************************  Filemacros  ********************************
'***********************************************************************************

'open file
Sub FileOpen(NCName)
    
    If FileExist(ncpathGlobal+NCName) Then
		NCFileNo= FOpenWrite(ncpathGlobal+NCName)  
		If NCFileNo=-1 Then
			Exit All
 		Else
      		FClose(NCFileNo)
    		Kill(ncpathGlobal+NCName)
		End If
    End If
	    
    NCFileNo= FOpenWrite(ncpathGlobal+NCName)
    If NCFileNo=-1 Then
		Exit All
    End If
End Sub

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

'If NCLine=570 Then Stop
' NCLine = 0
	If WritingNCData = True	Then
		If (Len(ncs)>0) And (ncs<>"G1") Then
			' --
			' -- keine leere G1 Zeilen ausgeben 5-Axis interpol.
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
		' wcnc("TRAFOOF")
		' G53 faehrt absolut ohne traori
		WCNC_IDD("TRANSOFF")
		WCNC_IDD("G90 D0")
		If FiveAxis.Yes And Not FiveAxis.ISG Then
			' MW 09.05.2011 - nicht fuer ISG
			WCNC_IDD("SUPAZ5AXIS")
			'wcnc("SUPA G0 Z="+g_MAX_LIMIT_ZPLUS +" Z3="+g_MAX_LIMIT_Z3PLUS)
		Else
			WCNC_IDD("SUPAZ")
			'wcnc("SUPA G0 Z="+g_MAX_LIMIT_ZPLUS)
		End If
	End If
	
	'ResetActV
	Safety=True
End Sub



'write NCstart
Sub NCStart
Dim vers As Variant 

	wcncCom("created:"+Str$(Date)+" - "+Str$(Time)+" - DiREKT CNC-Systeme GmbH",True)

	If JobPara.isg Then
		' das ist der Standard
		wcncCom("machine parameters id1000=1")
		WCNC_START_DEF_ISG
	Else
	'	wcncCom("machine parameters id1000<>1")
		WCNC_START_DEF_SIEMENS
	End If
	
	GetVersion5(vers)
	wcncCom("WZ:"+TDATA.ActMachineName,True)
	' -- Versionsinfo immer schreiben
	wcnc(StrToCom("Post:"+TDATA.MachineData.MachineParameter.PostProzessor+" V"+vers+" Script"+SCRIPT_VERSION))
	
	wcncCom("total processes[#"+IntToS(NCData.ProcessList.Count)+"]",True)
	
	If Marker.CountOfTool>0 Then
		' Neu MW 04.07.2005 damit auch ohne Bearbeitungen ein NC-Prog erzeugbar
		MT_Write_TCheck
	End If

	WCNC_IDD("G500 G90 D0")
	WCNC_IDD("CUT2DF")
	WCNC_IDD("CFIN")
	
	If JobPara.isg And Marker.AutoXStrategie>0 Then
		wcnc("V.P.AutoXStrategie = " & FToS( Marker.AutoXStrategie))
	End If
	
	WCNC_IDD(SPF_StartProg)
	
	WCNC_IDD("G64G17SOFT")
	If (JobPara.Laser_Activ) Then
		If Laser_HPGL_TimeStampOk Then
			do_LaserPointer
		End If
	End If
	
	If JobPara.isg Then
		WCNC_START_DEF_ISG_EXT2
	Else
		WCNC_START_DEF_SIEMENS_EXT2
	End If
	' Neu AK 24.11.2016 
	If (HLaserInfo.HLaserX_Active=True) Or (HLaserInfo.HLaserY_Active=True) Then
		ISG_SUB(SPF_HLaserPrg)
	End If
	WCNC_IDD("CP_FIRST_TOOL_PREINFO")


End Sub


'write nc header
Sub wcncHeader(NCName,TDB,FX,FY,FZ,Comment,Add_X,Add_Y,Add_Z)
Dim i As Long
Dim stri As Variant
Dim stri_merker As Variant
	
	If JobPara.isg Then
		wcncwo("%"+WithoutExtension(NCName))
	Else
	End If
	
	wcncCom("FinishedPart: X: "+FToS(FX)+" Y: "+FToS(FY)+" Z: "+FToS(FZ))
	wcncCom("TData:"+TDB)
	
	Call NCStart
	

End Sub

Sub NCEnd

	 wcnc("M30")
End Sub



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


' *****************************************************************************************
' ** Nullpunkt schreiben
' *****************************************************************************************
Function SET_Zero(pos,oxg,oyg,ozg,oxf,oyf,ozf)  ',mirrx,flag)

' axis definition
Const X = "X"
Const Y = "Y"
Const Z = "Z"
Const Z1 = "Z1"

Dim NP_Stri As String

	NP_Stri = "$P_UIFR[" + IntToS(Fix_Zero)+ "]=CTRANS("
	NP_Stri = NP_Stri + ""+X+","
	NP_Stri = NP_Stri + FToS(oxg)
	NP_Stri = NP_Stri + ","+Y+","
	NP_Stri = NP_Stri + FToS(oyg)
	
	NP_Stri = NP_Stri + ","+Z+","
	NP_Stri = NP_Stri + FToS(ozg)
	If FiveAxis.Yes And Not FiveAxis.isg Then
		' -- 
		' -- fuer 5-Achs
		' --
		NP_Stri = NP_Stri + ",Z3,"
		NP_Stri = NP_Stri + FToS(ozg)
	End If
	NP_Stri = NP_Stri + ")"
	
	' --
	' -- Fine offset
	' --
	NP_Stri = NP_Stri + ":CFINE("
	NP_Stri = NP_Stri + ""+X+","
	NP_Stri = NP_Stri + FToS(oxf)
	NP_Stri = NP_Stri + ","+Y+","
	NP_Stri = NP_Stri + FToS(oyf)
	NP_Stri = NP_Stri + ","+Z+","
	NP_Stri = NP_Stri + FToS(ozf)
	If FiveAxis.Yes And Not FiveAxis.isg Then
		' --
		' -- fuer 5-Achs
		' --
		NP_Stri = NP_Stri + ",Z3,"
		NP_Stri = NP_Stri + FToS(ozf)
	End If
	
	NP_Stri = NP_Stri + ")"
	
  	
	wcnc(NP_Stri)	
	wcncCom("Hier evtl. auch :CROT, : CSCALE : CMIRROR")
	
	wcncCom("")
	WCNC_IDD("STOPRE")
	wcnc("G"+IntToS(53+Fix_Zero))
	wcncCom("")

End Function


Function init_MachineData

	FiveAxis.Yes= MT_Find5AxisHead
	FiveAxis.isg=MT_IS_ISG
End Function

Function Init_JobData
Dim ddd As Variant 
    JobPara.Activ_Fields = MCDATA.ActiveFields	'  Aktive Felder 1=links 2=rechts 3=gekoppelt
	JobPara.laser_activ = PostSettings.LaserActive ' Laser aktiv - dann mit Laserpointer Konturen abfahren
    JobPara.NPX = 99999.99 					' Nullpunkt X
    JobPara.NPY = 99999.99					' Nullpunkt Y
    JobPara.NPZ = 99999.99					' Nullpunkt Z
	JobPara.HPGL_TimeStamp = PostSettings.LaserTimecode	
	JobPara.Add_ZSic = NCData.ProgInfo.SupplementZOffset
	JobPara.ISG = MT_IS_ISG

    ' --  Radius fahren spezial - Mode (wenn Radius welcher gefahren wird, dem Werkzeugradius entspricht - inkl. Toleranzangabe)

	JobPara.Jumps_in_NC	= JobPara.ISG And Val(MT_Get_MachPara_Add(1005))
	JobPara.Jumpvar = "V.E.M_DataINT[29]"
	JobPara.JumpAktPos = 0
	JobPara.JumpCount = 0
	JobPara.JumpList = 0
	ddd = Rnd()
	JobPara.JumpStamp = Replace(ddd,",",".")

	' NC-Seitig gesteuerte Dyn. Haube
	'	JobPara.DynamicSuctionNC	= JobPara.ISG And Val(MT_Get_MachPara_Add(1006))

	' Merker ob Werkzeug Vorab Information geschrieben wird (optimiert nur einmaliges lesen)
	' -----------------------------------------------------------------------------------
	JobPara.TC_PreInfo_Activ = False
	
	If Val(MT_Get_MachPara_Add(2000))=1 Then
		JobPara.TC_PreInfo_Activ = True
		AddHint("CP_PreChange - activ MachParam ID 2000 / PP.INI - OPTIONS WZPRECHANGE")
		If MT_Count_TC_Heads > 1 Then
			pp_err(121)
		End If
		
	End If
	
	' zusaetzliche Drehzahl - Info
	' -----------------------------------------------------------------------------------
	JobPara.TC_SpeedInfo = False
	If Val(MT_Get_MachPara_Add(2010))=1 Then
		JobPara.TC_SpeedInfo = True
	End If
	
	
	' -----------------------------------------------------------------------------------
	If JobPara.ISG Then
		JobPara.TCP_ON  = "CP_TRAFO(1)"
		JobPara.TCP_OFF = "CP_TRAFO(0)"
	Else
		JobPara.TCP_ON  = "TRAORION"
		JobPara.TCP_OFF = "TRAORIOFF"

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

	Marker.LastLiftpos = -1   '      => zuletzt gesetzte Position wenn < 0 dann war TC aktiv
	Set Marker.BStris = CreateObject("NC_Data.NCData_SetOfString")	
	Set Marker.AStris = CreateObject("NC_Data.NCData_SetOfString")	

	Marker.ActProcess = 0   ' 

	Set Marker.fCommand1 = CreateObject("NC_Data.NCData_SetOfString")	  ' WCNC_ISG_CONTOUR_START_EXT
	Set Marker.fCommand2 = CreateObject("NC_Data.NCData_SetOfString")	  ' WCNC_ISG_CONTOUR_END_EXT
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

		wcncCom("WP:"+FToS(Marker.wp_actindex)+" Stop:"+(wp.SName)+" X:"+FToS(wp.Sox)+" Y:"+FToS(wp.Soy)+" Z:"+FToS(wp.Soz), True)
		wcncCom(wp.WPName, True)
		wcncCom("FX:"+FToS(wp.WPx)+" FY:"+FToS(wp.WPy)+" Z:"+FToS(wp.WPz), True)
	End If
End Function

'Save SP_EP_No_LeadInOut Parameter
Sub SP_EP_No_LeadInOutSave(SP_EP As TSP_EP_No_LeadInOut,SP_x,SP_y,SP_z,SP_ax,SP_ay,SP_az,SP_Feedrate,SP_Speed,SP_RotA,SP_TipA,SP_TRC,SP_TA,SP_Distance, _
                       EP_x,EP_y,EP_z,EP_ax,EP_ay,EP_az,EP_Feedrate,EP_Speed,EP_RotA,EP_TipA,EP_TRC,EP_TA,EP_DMove,EP_DFactor,EP_Retreat, _
                       Dummy1,Dummy2,Dummy3,Dummy4,Dummy5,Dummy6,Dummy7,Dummy8,Dummy9,Dummy10,Dummy11,Dummy12,Dummy13,Dummy14,Dummy15,Dummy16,Dummy17,Dummy18,Dummy19,Dummy20)
	SP_EP.SP_x=SP_x
	SP_EP.SP_y=SP_y
	SP_EP.SP_z=SP_z
	SP_EP.SP_ax=SP_ax
	SP_EP.SP_ay=SP_ay
	SP_EP.SP_az=SP_az
	SP_EP.SP_Feedrate=SP_Feedrate
	SP_EP.SP_Speed=SP_Speed
	SP_EP.SP_RotA=SP_RotA
	SP_EP.SP_TipA=SP_TipA
	SP_EP.SP_TRC=SP_TRC
	SP_EP.SP_TA=SP_TA
	SP_EP.SP_Distance=SP_Distance
	SP_EP.EP_x=EP_x
	SP_EP.EP_y=EP_y
	SP_EP.EP_z=EP_z
	SP_EP.EP_ax=EP_ax
	SP_EP.EP_ay=EP_ay
	SP_EP.EP_az=EP_az
	SP_EP.EP_Feedrate=EP_Feedrate
	SP_EP.EP_Speed=EP_Speed
	SP_EP.EP_RotA=EP_RotA
	SP_EP.EP_TipA=EP_TipA
	SP_EP.EP_TRC=EP_TRC
	SP_EP.EP_TA=EP_TA
	SP_EP.EP_DMove=EP_DMove
	SP_EP.EP_DFactor=EP_DFactor
	SP_EP.EP_Retreat=EP_Retreat
	SP_EP.Dummy1=Dummy1
	SP_EP.Dummy2=Dummy2
	SP_EP.Dummy3=Dummy3
	SP_EP.Dummy4=Dummy4
	SP_EP.Dummy5=Dummy5
	SP_EP.Dummy6=Dummy6
	SP_EP.Dummy7=Dummy7
	SP_EP.Dummy8=Dummy8
	SP_EP.Dummy9=Dummy9
	SP_EP.Dummy10=Dummy10
	SP_EP.Dummy11=Dummy11
	SP_EP.Dummy12=Dummy12
	SP_EP.Dummy13=Dummy13
	SP_EP.Dummy14=Dummy14
	SP_EP.Dummy15=Dummy15
	SP_EP.Dummy16=Dummy16
	SP_EP.Dummy17=Dummy17
	SP_EP.Dummy18=Dummy18
	SP_EP.Dummy19=Dummy19
	SP_EP.Dummy20=Dummy20
End Sub

Function EndandPark
Dim xstr,ystr As String
	
	' nix - Maschine bleibt nach letzter Bearbeitung stehen
	xstr=""
	ystr=""
	
	Get_ParkStrXY(xstr,ystr)
	
	If JobPara.park > 0 Then
		If JobPara.park = 12 Then
			If JobPara.isg Then
				wcnc("#MCS ON")
				wcnc(g_PARKXVAR+"=V.A.ACT_POS.X")
				wcnc(g_PARKYVAR+"="+ystr)
				wcnc("#MCS OFF")
				ISG_CC(SPF_EndProg,g_PARKXVAR,g_PARKYVAR)
			Else
                wcnc(g_PARKYVAR+"="+ystr)
				wcnc(SPF_EndProg +"("+","+g_PARKYVAR+",)")
			End If
		Else
		
			wcnc(g_PARKXVAR+"="+xstr)
			wcnc(g_PARKYVAR+"="+ystr)
			If JobPara.isg Then
				ISG_CC(SPF_EndProg,g_PARKXVAR,g_PARKYVAR)

			Else
				wcnc(SPF_EndProg +"("+g_PARKXVAR+","+g_PARKYVAR+",)")
			End If
		End If
	Else
		' -- ohne Parken keine Parameter
		If JobPara.isg Then
			wcncCom("ohne parken - Achsen stehen lassen!")
			wcnc("#MCS ON")
			wcnc(g_PARKXVAR+"=V.A.ACT_POS.X")
			wcnc(g_PARKYVAR+"=V.A.ACT_POS.Y")
			wcnc("#MCS OFF")
			ISG_CC(SPF_EndProg,g_PARKXVAR,g_PARKYVAR)
		Else
		wcnc(SPF_EndProg +"("+","+",)")
	End If
	End If

End Function

Function Get_ParkStrXY(xstr,ystr As String)

	If JobPara.park=1 Then
		' links hinten Parken
		xstr=g_MAX_LIMIT_XMINUS
		ystr=g_MAX_LIMIT_YPLUS
	ElseIf JobPara.park=2 Then
		' rechts hinten Parken
		xstr=g_MAX_LIMIT_XPLUS
		ystr=g_MAX_LIMIT_YPLUS
	ElseIf JobPara.park=3 Then
		' mitte hinten Parken
		xstr="("+g_MAX_LIMIT_XPLUS+"+"+g_MAX_LIMIT_XMINUS+")/2"
		ystr=g_MAX_LIMIT_YPLUS
	ElseIf JobPara.park=4 Then
		' links vorne parken
		xstr=g_MAX_LIMIT_XMINUS
		ystr=g_MAX_LIMIT_YMINUS
	ElseIf JobPara.park=5 Then
		' rechts vorne parken
		xstr=g_MAX_LIMIT_XPLUS
		ystr=g_MAX_LIMIT_YMINUS
	ElseIf JobPara.park=6 Then
		' mitte vorne parken
		xstr="("+g_MAX_LIMIT_XPLUS+"+"+g_MAX_LIMIT_XMINUS+")/2"
		ystr=g_MAX_LIMIT_YMINUS
	ElseIf JobPara.park=7 Then
		' mitte links parken
		xstr=g_MAX_LIMIT_XMINUS
		ystr="("+g_MAX_LIMIT_YPLUS+"+"+g_MAX_LIMIT_YMINUS+")/2"
	ElseIf JobPara.park=8 Then
		' mitte rechts parken
		xstr=g_MAX_LIMIT_XPLUS
		ystr="("+g_MAX_LIMIT_YPLUS+"+"+g_MAX_LIMIT_YMINUS+")/2"
	ElseIf JobPara.park=9 Then
		' mitte mitte parken
		xstr="("+g_MAX_LIMIT_XPLUS+"+"+g_MAX_LIMIT_XMINUS+")/2"
		ystr="("+g_MAX_LIMIT_YPLUS+"+"+g_MAX_LIMIT_YMINUS+")/2"
	ElseIf JobPara.park=10 Then
		' Freie X/Y - Position
		xstr=FToS(JobPara.parkx)
		ystr=FToS(JobPara.parky)
	ElseIf JobPara.park=11 Then
		' automatische Parkposition
		If JobPara.Activ_Fields = 1 Then
			' Werkstueck links 
			' in X rechts vom Werkstueck parken
			xstr= FToS(JobPara.npx + FinishedPart.X + mPara_Add.PARK_DIST_X_Field1)
			ystr= g_MAX_LIMIT_YPLUS
		ElseIf JobPara.Activ_Fields= 2 Then
			' Werkstueck rechts
			' in X links vom Werkstueck parken
			xstr= FToS(JobPara.npx -  mPara_Add.PARK_DIST_X_Field2)
			ystr= g_MAX_LIMIT_YPLUS
		Else
			' Felder gekoppelt
			' Mitten hinten parken
			xstr="("+g_MAX_LIMIT_XPLUS+"+"+g_MAX_LIMIT_XMINUS+")/2"
			ystr=g_MAX_LIMIT_YPLUS
		End If
	ElseIf JobPara.park=12 Then
		' --nur Y- Parken
		xstr=""
		ystr=g_MAX_LIMIT_YPLUS
		
	End If
	
	If JobPara.isg Then
		' pruefen, ob mathemathischer Ausdruck runde Klammern enthaelt - diese ist bei ISG  "["
		xstr = Check_Term(xstr)
		ystr = Check_Term(ystr)
	End If
	

End Function

Function AddLog(stri As String)
	ReDim Preserve LogArr(UBound(LogArr)+1) 
	LogArr(UBound(LogArr))=stri
	
End Function

Function Write_DebuggerLog
Dim Debugg As Integer
Dim i As Long
Dim path As Variant
Dim file As String
Dim MaxNCLines,MaxNCLinesStandardMilling,vers,RealNCName As Variant
Dim FileSize As Long
Dim FileSizeS As String

	GetBasic_Path(path)
	GetVersion5(vers)
	FileSize  = FileLen(JobPara.RealNCFileName)
	
	If (FileSize > 1048576) Then
		FileSizeS= IntToS(FileSize/1024/1024)+ "MB"
	ElseIf FileSize > 1024 Then
		FileSizeS= IntToS(FileSize/1024)+ "KB"
	Else
		FileSizeS= IntToS(FileSize)+ "Bytes"
	End If
	
	
	file = path+"pp.log"
	If FileExist(file) Then
		If FileLen(file)<1000000 Then
			' bis 1MB anhaengen
	 		Open file For Append As #1
	 	Else
	 		FileCopy file,path+"pp"+JobPara.JumpStamp+".log"
			Open file For Output As #1
		End If
	Else
		Open file For Output As #1
	End If
	Print #1, repl("-",125)
	Print #1, Date + Time
	Print #1, "---- LOG deaktivierbar ueber ID 1102=0 ----"
	Print #1, "WZ:"+TDATA.ActMachineName+ "Post:"+TDATA.MachineData.MachineParameter.PostProzessor+" V"+vers+" Script"+SCRIPT_VERSION
	Print #1, " Processes :"+IntToS(Marker.CountOfTool)+ " NC Lines :"+IntToS(NCLine/JobPara.lstp)+ " - Size: " + FileSizeS
	Print #1, "------------------------------------------------"
	For i = 1 To UBound(WPI)-1
		Print #1, "activefield:" +IntToS(MCDATA.ActiveFields)
		Print #1, "workpiece:" + WPI(i).WPName + " Stop:"+(WPI(i).SName)
	Next i 
	Print #1, "ncprog:"+ncpathGlobal+NCNameGlobal
	For i = 1 To UBound(LogArr)
		Print #1, LogArr(i)
	Next i 
	Print #1, ""
	Print #1, ""
	Close #1
	
	If MT_Get_MachPara_Add(2140000999) = "1" Then
		Begin Dialog UserDialog 880,385 ' %GRID:10,7,1,1
			GroupBox 10,0,870,350,"Infos",.GroupBox1
			ListBox 30,21,840,308,LogArr(),.Debugg
			OKButton 10,350,870,35
		End Dialog
		Dim dlg As UserDialog
		Dialog dlg
	End If
	
End Function



Function wcnc_msg(msg As String)
Const nr = "<<"+Chr(34)+"$67301"+Chr(34)
	
	WCNC_IDD("MSG",msg,nr)
	
End Function


Function wcnc_msgOff
	WCNC_IDD("MSGOFF")
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



' schreibt funktion id - Abhaengig ins NCprogramm
' s wird hierbei geprueft
Function WCNC_IDD(s,Optional v1,Optional v2,Optional v3,Optional v4,Optional v5,Optional v6,Optional v7,Optional v8,Optional v9,Optional v10,Optional v11,Optional v12)
' -- Neu AK 06.10.2009  
' -- Parameteruebergabe fuer Werkzeugbearbeitung im Briskmode (DPI) ID aus Schneide Zusatzinfo
Dim var_id1, var_id2, var_id3 As Variant
Dim done As Boolean
	done = False
	' -- 
	' -- FueR ISG CONTROLLER
	' --  MW 11.04.2008 12:40:28
	' --
    Select Case UCase(s)
    Case "STOPRE"
		If JobPara.isg Then	WCNC_ISG_STOPRE	Else WCNC_SIEMENS_STOPRE
		done = True
    Case "TRANSOFF"
		If JobPara.isg Then	WCNC_ISG_TRANSOFF Else WCNC_SIEMENS_TRANSOFF
		done = True
    Case "TRANSON"
		If JobPara.isg Then	WCNC_ISG_TRANSON(v1,v2,v3,v4,v5,v6)	Else WCNC_SIEMENS_TRANSON(v1,v2,v3,v4,v5,v6)
		done = True
	Case "ATRANSAROT","ATRANSAROT_P2"
		' -- 
		' --  MW 06.10.2008 09:25:58
		' --  ATRANSAROT_P2 hat gefehlt
		If JobPara.isg Then	WCNC_ISG_ATRANS_AROT(v1,v2,v3,v4,v5) Else WCNC_SIEMENS_ATRANS_AROT(v1,v2,v3,v4,v5)
		done = True
	Case "ATRANSAROT_DH"
		If JobPara.isg Then	WCNC_ISG_ATRANS_AROT_DH(v1,v2,v3,v4,v5,v6,v7,v8) Else WCNC_SIEMENS_ATRANS_AROT_DH(v1,v2,v3,v4,v5,v6,v7,v8)
		done = True
	Case "SUPAZ"
		If JobPara.isg Then	WCNC_ISG_SUPAZ Else WCNC_SIEMENS_SUPAZ
		done = True
	Case "SUPAZ5AXIS"
		If JobPara.isg Then	WCNC_ISG_SUPAZ5AXIS Else WCNC_SIEMENS_SUPAZ5AXIS
		done = True
	Case "G601"
		If JobPara.isg Then	wcnc(";G601") Else wcnc("G601")
		done = True
	Case "G602"
		If JobPara.isg Then	WCNC_ISG_G602 Else WCNC_SIEMENS_G602
		done = True
	Case "BRISK"
		If JobPara.isg Then	WCNC_ISG_BRISK Else WCNC_SIEMENS_BRISK
		done = True
	Case "SOFT"
		If JobPara.isg Then	WCNC_ISG_SOFT Else WCNC_SIEMENS_SOFT
		done = True
	Case "G64G17SOFT"
		If JobPara.isg Then	WCNC_ISG_G64G17SOFT Else WCNC_SIEMENS_G64G17SOFT
		done = True
	Case "G500"
		If JobPara.isg Then	WCNC_ISG_G500 Else WCNC_SIEMENS_G500
		done = True
	Case "G500 G90 D0"
		If JobPara.isg Then	WCNC_ISG_G500G90D0 Else WCNC_SIEMENS_G500G90D0
		done = True
	Case "G90 D0"
		If JobPara.isg Then	WCNC_ISG_G90D0 Else WCNC_SIEMENS_G90D0
		done = True
	Case "CUT2DF"
		If JobPara.isg Then	WCNC_ISG_CUT2DF Else WCNC_SIEMENS_CUT2DF
		done = True
	Case "CFIN"
		If JobPara.isg Then	WCNC_ISG_CFIN Else WCNC_SIEMENS_CFIN
		done = True
	Case SPF_StartProg
		If JobPara.isg Then	ISG_CC(SPF_StartProg) Else wcncAddCom(SPF_StartProg," Start ")
		done = True
	Case SPF_AGGCheck
		If JobPara.isg Then	ISG_CC(SPF_AGGCheck) Else wcnc(SPF_AGGCheck)
		done = True
	Case "M5"
		If JobPara.isg Then	wcnc("M5") Else wcnc("M5")
		done = True
'	Case g_TCARR
'		' Tool carrier
'		If JobPara.isg Then	WCNC_ISG_TCarr(v1,v2) Else WCNC_SIEMENS_TCarr(v1,v2)
'		done = True
'	Case "OFFN"
'		' Abstandsverrechnung zu Kontur
'		'If (JobPara.CMill_EngineCalcs_Offset = True) And (Mill_C.activ) Then
'			' nix machen
'			' dann wird offn nicht benoetigt beim C-Achsfraesen
'			' Achtung wird benoetigt vom 5-Achs fraesen
'		'Else
'			If JobPara.isg Then	
'				WCNC_ISG_OFFN(v1,v2) 
'			Else 
'				WCNC_SIEMENS_OFFN(v1,v2)
'			End If
'		'End If
'		done = True
	Case "IFLASERA"
		' IF LASER CALL
		If JobPara.isg Then	WCNC_ISG_IFLASERA Else WCNC_SIEMENS_IFLASERA
		done = True
	Case "IFLASERB"
		' IF LASER CALL
		If JobPara.isg Then	WCNC_ISG_IFLASERB Else WCNC_SIEMENS_IFLASERB
		done = True
	Case "ENDLASER"
		' IF LASER CALL
		If JobPara.isg Then	wcnc("[NOLASERMODE]") Else wcnc("ENDIF")
		done = True
	Case "ENDIF"
		' IF LASER CALL
		If JobPara.isg Then	wcnc("$ENDIF") Else wcnc("ENDIF")
		done = True
	Case SPF_LASERONOFF
		' IF LASER CALL
		If JobPara.isg Then	WCNC_ISG_SPF_LASERONOFF(v1,v2,v3) Else WCNC_SIEMENS_SPF_LASERONOFF(v1,v2,v3)
		done = True
	Case "EXTCALL"
		' IF LASER CALL
		If JobPara.isg Then	WCNC_ISG_EXTCALL(v1) Else WCNC_SIEMENS_EXTCALL(v1)
		done = True
	Case "G04"
		' IF LASER CALL
		If JobPara.isg Then	WCNC_ISG_G04(v1) Else WCNC_SIEMENS_G04(v1)
		done = True
	Case "MSG"
		If JobPara.isg Then	WCNC_ISG_MSG(v1,v2) Else WCNC_SIEMENS_MSG(v1,v2)
		done = True
	Case "MSGOFF"
		If JobPara.isg Then	WCNC_ISG_MSGOFF Else WCNC_SIEMENS_MSGOFF
		done = True
	Case "TCARROFF"		
		If JobPara.isg Then	WCNC_ISG_TCARROFF Else WCNC_SIEMENS_TCARROFF(v1,v2)
		done = True
	Case SPF_REQUEST_FLEX
		If JobPara.isg Then	WCNC_ISG_REQUEST_FLEX(v1,v2,v3,v4) Else WCNC_SIEMENS_REQUEST_FLEX(v1,v2,v3,v4)
		done = True
	Case SPF_PREINFO
		' NEU MW 24.09.2012 v5 = VorposX
		If JobPara.isg Then	WCNC_ISG_PREINFO(v1,v2,v3,v4,v5) Else WCNC_SIEMENS_PREINFO(v1,v2,v3,v4,v5)
		done = True
	Case "ATRANSZ"
		If JobPara.isg Then	WCNC_ISG_ATRANSZ(v1) Else WCNC_SIEMENS_ATRANSZ(v1)
		done = True
	Case "TCARRACTIVATE"
		' -- 
		' -- ISG CONTROLLER
		' --  MW 16.06.2008 09:10:41
		' --
		' -- wohl was uebersehen..   
		'If JobPara.isg Then	WCNC_ISG_TCARR_ACTIVATE(v1,v2) Else WCNC_ISG_TCARR_ACTIVATE(v1,v2)
		If JobPara.isg Then	WCNC_ISG_TCARR_ACTIVATE(v1,v2) Else WCNC_SIEMENS_TCARR_ACTIVATE(v1,v2)
		done = True
	Case "CONTOUR_START"
		If JobPara.isg Then	
			If (ppara.PreObjectTyp=2) Then
				' MW 11.11.2016 nur fuer Fraesen
				WCNC_ISG_CONTOUR_START
			End If
			' -- Neu AK 06.10.2009  
      ' -- Parameteruebergabe fuer Werkzeugbearbeitung im Briskmode (DPI) ID aus Schneide Zusatzinfo

		Else
			pp_err(7,10600)
			'If Not ActT.t.CuttingEdge.Additions.GetAddition_ID(ID_CONTOURMODEID) Is Nothing Then
			'	var_id1 = ActT.t.CuttingEdge.Additions.GetAddition_ID(ID_CONTOURMODEID).Value	
			'Else 
			'	var_id1 = ""
			'End If
			'If Not ActT.t.CuttingEdge.Additions.GetAddition_ID(ID_CONTOURMODEACCEL) Is Nothing Then
			'	var_id2 = ActT.t.CuttingEdge.Additions.GetAddition_ID(ID_CONTOURMODEACCEL).Value	
			'Else 
			'	var_id2 = ""
			'End If
			'If Not ActT.t.CuttingEdge.Additions.GetAddition_ID(ID_CONTOURMODEJERK) Is Nothing Then
			'	var_id3 = ActT.t.CuttingEdge.Additions.GetAddition_ID(ID_CONTOURMODEJERK).Value	
			'Else 
			'	var_id3 = ""
			'End If
			'WCNC_SIEMENS_CONTOUR_START(var_id1, var_id2, var_id3) 
		End If
		done = True
	Case "CONTOUR_END"
		If JobPara.isg Then	
			If (ppara.PreObjectTyp=2) Then
				' MW 11.11.2016 nur fuer Fraesen
				WCNC_ISG_CONTOUR_END
			End If
		Else
			pp_err(7,10600)
			'If Not ActT.t.CuttingEdge.Additions.GetAddition_ID(ID_CONTOURMODEID) Is Nothing Then
			'	var_id1 = ActT.t.CuttingEdge.Additions.GetAddition_ID(ID_CONTOURMODEID).Value	
			'Else 
			'	var_id1 = ""
			'End If
			'WCNC_SIEMENS_CONTOUR_END(var_id1)
		End If
		done = True
	Case "CP_TRAFO(1)"
		If JobPara.isg Then	
			WCNC_ISG_KINEMATIK("CP_TRAFO","1")
		Else
			WCNC_SIEMENS_KINEMATIK(s)
		End If
		done = True
	Case "CP_TRAFO(0)"
		If JobPara.isg Then	
			WCNC_ISG_KINEMATIK("CP_TRAFO","0")
		Else
			WCNC_SIEMENS_KINEMATIK(s)
		End If
		done = True

	Case "CP_HOOD"
		If JobPara.isg Then	
			WCNC_ISG_HAUBE(s,v1,v2)
			done = True
		End If
		
	Case "CP_SZENE"
		' MW 11.01.2012
		If JobPara.isg Then	
			WCNC_ISG_SZENE(v1, v2, v3, v4, v5, v6, v7) 			
		End If		
		done = True
		
	Case "CP_DRILLSTART"
		' MW 03.04.2012
		If JobPara.isg Then	
			ISG_CC(s,v1) 
		Else 
			'wcnc("CP_DRILLSTART")
		End If
		done = True

	Case "CP_DRILLEND"
		' MW 03.04.2012
		If JobPara.isg Then	
			ISG_CC(s,v1) 
		Else 
			'wcnc("CP_DRILLSTART")
		End If
		done = True
		
	Case "CP_FIRST_TOOL_PREINFO"
		' MW 09.06.2015
		If JobPara.isg Then	
			If JobPara.TC_PreInfo_Activ = True Then
			
			
		'				H_Id=t.HID
	'					id = t.t.ID   '  Campus - No ID
	'					TC_Id = t.T.GetOn_TC.HeadID
	'					TC_PlaceNo = t.t.GetPlaceID_OnTC
		
			'			wcncCom("-- Vorwechsel:"+t.t.Description)
			'			wcncCom("Headid:"+IntToS(H_Id)+"  TC_Id:"+IntToS(TC_Id)+"  TC_Platz:"+IntToS(TC_PlaceNo)+"  Id:"+IntToS(id))
			
				If (Not FirstT.t.GetOn_TC Is Nothing) Then
				
					wcncCom("-- Vorwechsel:"+FirstT.t.Description)
					wcncCom("Headid:"+IntToS(FirstT.HId)+"  TC_Id:"+IntToS(FirstT.T.GetOn_TC.HeadID)+"  TC_Platz:"+IntToS(FirstT.t.GetPlaceID_OnTC)+"  Id:"+IntToS(FirstT.t.ID))
					WCNC_IDD(SPF_PREINFO,FirstT.HId,FirstT.T.GetOn_TC.HeadID,FirstT.t.GetPlaceID_OnTC,FirstT.t.ID,-1*FirstT.h.CenterX+Marker.FirstTool_PosX)
				End If
				
			End If
		End If		
		done = True
		
	' Neu AK 03.11.2015 Oszillierendes Fraesen 		
	Case "CONTOUR_START_EXCLUSIV"
		If JobPara.isg Then	
			'Pruefen ob in der Schneide der Parameter fuer Oszillierendes Fraesen aktiv ist (ID10610)
			If Not ActT.t.CuttingEdge.Additions.GetAddition_ID(ID_CONTOUROSC_ACTIVE) Is Nothing Then
				var_id1 = ActT.t.CuttingEdge.Additions.GetAddition_ID(ID_CONTOUROSC_ACTIVE).Value	
			Else 
				var_id1 = "0"
			End If
			If (var_id1 <> "0") And (var_id1<>"1") Then
				var_id1 = "0"			
			End If
			
			If Not ActT.t.CuttingEdge.Additions.GetAddition_ID(ID_CONTOUROSC_FEED) Is Nothing Then
				var_id2 = ActT.t.CuttingEdge.Additions.GetAddition_ID(ID_CONTOUROSC_FEED).Value	
			Else 
				var_id2 = "500"
			End If

			If Not ActT.t.CuttingEdge.Additions.GetAddition_ID(ID_CONTOUROSC_EXCURSION) Is Nothing Then
				var_id3 = ActT.t.CuttingEdge.Additions.GetAddition_ID(ID_CONTOUROSC_EXCURSION).Value	
			Else 
				var_id3 = "1"
			End If	
			Select Case var_id3
				Case "0","1","2","3","4","5","6","7","8","9","10"
					'var_id3 bleibt
				Case Else
					var_id3=1
			End Select
			If var_id1 ="0" Then
				var_id2="0"
				var_id3="0"
			Else
				'Oszillierendes Fraesen erkannt -> aktivieren
				' MW 15.02.2016 der Schneide hinterlegt nicht sinnvoll - umstellen auf NCIExt
				' MW 11.11.2016 kompatibilitaet sicherstellen
				If (ActV.View=0) And (ActV.TipA =0) And (equal(PPara.MinTipA,0)) And (equal(PPara.MaxTipA,0)) Then
					WCNC_ISG_CONTOUR_START_EXT("CP_CONTOUR_START_EXT","1",var_id1, var_id2,var_id3)
				Else
					pp_err(1558)
				End If
			End If
		End If
		done = True
		
	' Neu AK 03.11.2015 Oszillierendes Fraesen 	
	Case "CONTOUR_END_EXCLUSIV"
		If Marker.OscilationOn=True Then
			WCNC_ISG_CONTOUR_END_EXT("CP_CONTOUR_END_EXT","1","0","0","0")
		End If
		done = True
	Case "CP_DYNAMIC"
		' MW 27.06.2016
		If JobPara.isg Then	
			
			' Eigenschaft von Schneide
			var_id1 = -1 
			If Not ActT.T_CEdge Is Nothing Then
				If Not ActT.T_CEdge.Additions.GetAddition_ID(100) Is Nothing Then
					If Val(ActT.T_CEdge.Additions.GetAddition_ID(100).Value) > -1 Then
						var_id1 = Val(ActT.T_CEdge.Additions.GetAddition_ID(100).Value)
					End If
				End If
			End If
			If PPara.NCiE.dynamic.Activ Then
				var_id1 = PPara.NCiE.dynamic.No
			End If
			
			' ProcessKind
			var_id2 = GetObjectTypNo(NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1))
			
			WCNC_ISG_CONTOUR_DYNAMIC("CP_DYNAMIC",var_id1,var_id2)
		Else
			pp_err(7,"CP_DYNAMIC")
		End If
		done = True		
	Case "CP_MEAS"
		' MW 24.04.2019 - Messzyklus
		If JobPara.isg Then	
			WCNC_ISG_MEAS(v1,v2,v3,v4,v5,v6,v7,v8,v9,v10,v11,v12)
		Else
			pp_err(7,"CP_MEAS")
		End If
		done = True		
	Case "CP_MEAS_OFFSET"		
		' MW 24.04.2019 - Messwert - Verrechnung
		If JobPara.isg Then	
			WCNC_ISG_MEAS_OFFSET(v1,v2,v3)
		Else
			pp_err(7,"CP_MEAS_OFFSET")
		End If
		
		done = True		
	End Select

	If Not done Then 
		pp_err(122)
	End If
	
End Function


Function Version_Check(Target_Version, Optional check = True) As Boolean
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
	If (Not Versi) And (check) Then
		pp_Err(1513,Target_Version)
	End If
	
End Function


Function MT_GetToolId_Next_Process(Next_Working_Box,Next_Working_Head)

' -- 
' -- ID des benutzten Werkzeug naechster Prozess
' --

Dim Next_Working_Tool As THopsBasicToolExt   ' entspricht somit dem naechsten ToolChange - Tool
Dim I,Find As Long

	Next_Working_Box = -1
	
	For I =  Marker.ActProcess To Marker.CountOfTool-1 
		Next_Working_Box = ToolArray(I).t.ID
		Next_Working_Head = ToolArray(I).hid
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
		
		If MT_IsGB(lastt) Then
			Set LastT.gb = Dummy.GearBox
			Set LastT.t_gb = Dummy
		End If
		
		LastT.hid = ActT.hid
		LastT.aggname = ActT.aggname
		
		' -- 5 Axis
		Set LastT.h = TDATA.GetProcessHead_ID(LastT.hid)
		
		If MT_Is_Vertical_StandardTool5Axis(LastT) Then
			' Zusatzinfos von Spindel
			Set_Ph_Additions(LastT,LastT.h.Additions)
		End If
	
End Function

' -------------------------------------------------------------------------------------------------
Function Jumps_ok 
	Jumps_ok = False
	
	If (Marker.CountOfTool > 0) And (JobPara.Jumps_in_NC) Then
		Jumps_ok = True
	
	End If
	
End Function


' -- Absprungmarken und Einsprungmoeglichkeit zu einem bestimmten Werkzeugwechsel setzen
' -------------------------------------------------------------------------------------------------
' T = aktuelles Werkzeug
Function Jumps_Goto_and_In
		
Dim LastTool As THopsBasicToolExt
Dim AktTool As THopsBasicToolExt
Dim I,Find,Box,HeadID As Long
Dim Get_JumpStr As Variant
Dim HH_Str, InfoStr, Description,GB_Description As String 
Dim Scene As Integer 
	
	If (Jumps_ok) And (Firsttime_Viewchange) Then
		' Beim 1. Werkzeugaufruf koennen die Absprungmarken gesetzt werden !
		wcncCom("---",True)
		wcncCom("Benutzte Werzeuge - Einsprungmoeglichkeit",True)
		wcncCom("---",True)
		
		LastTool = ToolArray(0)
		For I =  1 To Marker.CountOfTool-1 
			AktTool = ToolArray(I)
			
			' Sonderfall Saege auf Bohrkopf -> dann kein TC und gleiches Werkzeug nochmals kommt
			' == > sollte der einzigste Fall sein, das sowohl bei Winkelgetriebe - Ausgangswechsel als auch bei Schneidenwechsel immer ein TC - Aufruf kommt!
			If MT_isDH_wasDH(LastTool,AktTool) Or MT_SameTools(LastTool,AktTool) Then
				' war ist Bohrkopf kein Wechsel aufrufen
				' und bei gleichem Werkzeug wie zuvor auch nicht!
				' und keine WEchsel von Bohrkopf Saegen auf Bohrkopf bohren 
			Else			
				JobPara.JumpCount = JobPara.JumpCount+1   ' Variable zur ueberpruefung, ob gleich viele Einsprungmarken wie Sprungmarken
				Scene = JobPara.tc_sc(I)

				Box = AktTool.t.ID
				HeadID = AktTool.hid
				Description = AktTool.t.Description
				GB_Description = ""
				If MT_isgb(AktTool) Then
					GB_Description = ";"+AktTool.gb.Description
				End If
				
				InfoStr = ";" + StrSize(Description,50,1)+ " Box."+StrSize(IntToS(Box),6,2)+ " Head:"+StrSize(IntToS(HeadID),2,2)
				HH_Str = GetJumpStr(JobPara.JumpCount,Scene,HeadID,Box,Description,GB_Description)
				'HH_Str = "JUMP"+IntToS(JobPara.JumpCount)+";"+IntToS(HeadID)+";"+IntToS(Box)+";"+Description+GB_Description
				If JobPara.JumpList <= 0 Then
					JobPara.JumpList = StringListCreate
					StringListAdd(JobPara.JumpList,"TIMESTAMP="+JobPara.JumpStamp)
				End If
				StringListAdd(JobPara.JumpList,HH_Str)
				
				
				' wcncwo("$If V.P."+JobPara.jumpvar +" = "+IntToS(JobPara.JumpCount) +" $GOTO ["+ JobPara.jumpvar +IntToS(JobPara.JumpCount)+"]"+InfoStr)
				wcnc(";"+JobPara.jumpvar +" = JUMP"+IntToS(JobPara.JumpCount) +" ==> "+InfoStr)
			End If
			LastTool = AktTool
		Next I
		If Marker.CountOfTool>1 Then
					'AK 15.04.2015
					wcnc("$IF "+JobPara.jumpvar+ ">0")
					wcnc("L F_JUMPCHECK.nc")
					wcnc("$IF V.P.JMPVALID == 1 $GOTO N"+JobPara.jumpvar)
					wcncwo("")
					wcnc("$ENDIF")
				End If
		
		wcncCom("---",True)
		wcncCom("---",True)
		wcncCom("---",True)
	ElseIf (Jumps_ok) Then
		' jetzt Einsprungmarken setzen! 
		' also ab dem 2. Werkzeugaufruf

		If MT_isDH_wasDH(ActT,LastT) Then
		    ' Bohrkopf folgt Bohrkopf
		Else
			JobPara.JumpAktPos = JobPara.JumpAktPos + 1
			'wcncwo("["+ JobPara.jumpvar + IntToS(JobPara.JumpAktPos)+"]")
			'AK 15.04.2015
			wcncwo("N" + IntToS(JobPara.JumpAktPos)+":")
			wcncwo("[JUMP" + IntToS(JobPara.JumpAktPos)+"]")
			wcncwo("V.E.M_DataINT[46]= " + IntToS(JobPara.JumpAktPos))
			Get_JumpStr = StringListStrings(JobPara.JumpList,JobPara.JumpAktPos)
			'hier jetzt noch abfragen, ob diese Sprungmarke zum Werkzeug (die Liste ist schon fertig) passt ! 
		
			Scene = JobPara.actscene
			Box = ActT.t.ID
			HeadID = ActT.hid
			Description = ActT.t.Description
			GB_Description = ""
			If MT_isgb(ActT) Then
				GB_Description = ";"+ActT.gb.Description
			End If
			HH_Str = GetJumpStr(JobPara.JumpAktPos,Scene,HeadID,Box,Description,GB_Description)
			
			If Not (Get_JumpStr = HH_Str) Then
	   			pp_err(120)
			End If
				
			
		End If
	End If
		
	
End Function

Function Check_Jumps  'MW 12.12.2012

	If (Jumps_ok) Then
		' MW 10.12.2013
		If (Marker.CountOfTool>1) Then
			If Not equal(JobPara.jumpcount,JobPara.jumpaktpos) Then
				pp_err(125)
				Exit All
			End If
		End If
	
		StringListSaveToFile(JobPara.JumpList,ncpathGlobal+"\Jumplist.txt")
	End If
End Function

' -------------------------------------------------------------------------------------------------

Function GetJumpStr(Count,Scene,HeadID,Box,Description,GB_Description) As String 

	GetJumpStr = "JUMP"+IntToS(Count)+";"+IntToS(Scene)+";"+IntToS(HeadID)+";"+IntToS(Box)+";"+Description+GB_Description
	
End Function


Function wcnc_Move_Zangen(situation1,situation2)
Dim CS_Old, CS_New As ClampSituation
Dim MCD_old, MCD_New As IMachineComponentsData
Dim TMC_Old,TMC_New As IMachineComponent
Dim j As Integer 
Dim Fehler As Byte
Dim Diff As Double 
	Set CS_Old = NCData.NCClampSituations.ClampSituations.GetItem_Index(situation1)
	Set CS_New = NCData.NCClampSituations.ClampSituations.GetItem_Index(situation2)
	
	Set MCD_old = CS_Old.MachineComponentsData
	Set MCD_New = CS_New.MachineComponentsData
	
	Fehler = 0
	
	For j = 0 To MCD_old.MachineComponents.ComponentList.TraverseCount-1 Step 1
		Set TMC_Old = MCD_old.MachineComponents.ComponentList.GetTraverse_Index(j)
		Set TMC_New = MCD_New.MachineComponents.ComponentList.GetTraverse_Index(j)
		
		If (TMC_Old.MoveX=True) And (TMC_Old.Kind=mckTraverse) And (TMC_New.MoveX=True) And (TMC_New.Kind=mckTraverse) Then
			' Verschiebbare Traverse gefunden
			' Differenz der Zangenposition ueber Zyklus ausgeben..
			Diff = TMC_Old.PosX-TMC_New.PosX
			If Not equal(Diff,0) Then
				JobPara.NPX = JobPara.NPX+Diff

				SET_Zero_ISG(WPI(1).WPName,JobPara.NPX,JobPara.NPY,JobPara.NPZ)

			Else
				Fehler = 1
			End If
		End If
	Next j
	Select Case Fehler
	Case 1
		' pp_err(221)  MW 02.02.2018 durch Implementierung Maschinenstopp - ist diese Plausibilisierung nicht mehr moeglich
	End Select
End Function


Function Evo_GetMinMax_V1(Obj,MinX,MaxX)  ' alte NCData - Logik
Dim P_MinMax As NCProcessMinMaxInfo
Dim tmp_MinX,tmp_MaxX As Double 
Dim OffX As Double
Dim AggOffX As Double
Dim T_Tmp As THopsBasicToolExt
	OffX = 0
	MT_SetTHopsBasicToolExt(T_Tmp,Obj.Tool.ID,Val(Obj.HeadInfo))
	
	If MT_isDHSaw(T_Tmp) Then
		AggOffX = 0
	Else
		AggOffX = T_Tmp.h.CenterX
	End If
	
	Set P_MinMax = NCData.GetExtInfo(ekNCProcess_HeadMinMax,Obj) ' -> [INCProcessMinMaxInfo@0x0B7D77F0]
	If Not P_MinMax Is Nothing Then
		tmp_MinX = P_MinMax.Minx
		tmp_MaxX = P_MinMax.Maxx
		' Achtung 
		' * fuer Bearbeitungen auf Ebene (otMillingMPs) ist Min/Max der reale Wert
		' * fuer Bearbeitungen C-Achsfraesen / Oberflaechenfraesen / 5-Achsfraesen (otMillingMPs) muss Offset mit eingerechnet werden
		If (Obj.ObjectTyp = otMillingMPs) Then
			If Not Obj.View.IsTopView Then   ' Obj.Tool.ObjectType = htokGearBoxTool Then
				If PostSettings.GeneralSettings.RelativToRefSpindle Then
					OffX = -Obj.HeadOffX + AggOffX  ' statischer offset () zu Spindelbezugspunkt
				Else
					OffX = -Obj.HeadOffX ' statischer offset () zu Spindelbezugspunkt
				End If
				
			Else
				If PostSettings.GeneralSettings.RelativToRefSpindle Then
					OffX = 0   '??? in neuer Version korrigiert.  AggOffX   ' Aggregatsoffset
				Else
					OffX = 0
				End If
			End If
			'OffX = 0
		ElseIf (Obj.ObjectTyp = otMillingPoints) Then
			If PostSettings.GeneralSettings.RelativToRefSpindle Then
				OffX = AggOffX   ' Aggregatsoffset
			Else
				OffX = 0
			End If
		Else 
			pp_err(0,"wrong kind of working"+Obj.Tool.Description)
		End If
		
		MinX = tmp_MinX + OffX - NCData.NCParts.GetNCPart_Index(0).OffX - NCData.NCParts.GetNCPart_Index(0).StopX
		MaxX = tmp_MaxX + OffX - NCData.NCParts.GetNCPart_Index(0).OffX - NCData.NCParts.GetNCPart_Index(0).StopX
	End If

	MT_ClearTHopsBasicToolExt(T_Tmp)
	
End Function


Function Evo_GetMinMax_V2(Obj,MinX,MaxX)  ' korrigierte NCData 
Dim P_MinMax As NCProcessMinMaxInfo
Dim tmp_MinX,tmp_MaxX As Double 
Dim OffX As Double
Dim AggOffX As Double
Dim T_Tmp As THopsBasicToolExt
	OffX = 0
	
	MT_SetTHopsBasicToolExt(T_Tmp,Obj.Tool.ID,Val(Obj.HeadInfo))
	
	If MT_isDHSaw(T_Tmp) Then
		AggOffX = 0
	Else
		AggOffX = T_Tmp.h.CenterX
	End If
	
	Set P_MinMax = NCData.GetExtInfo(ekNCProcess_HeadMinMax,Obj) ' -> [INCProcessMinMaxInfo@0x0B7D77F0]
	If Not P_MinMax Is Nothing Then
		tmp_MinX = P_MinMax.Minx
		tmp_MaxX = P_MinMax.Maxx
		' Achtung 
		' * fuer Bearbeitungen auf Ebene (otMillingMPs) ist Min/Max der reale Wert
		' * fuer Bearbeitungen C-Achsfraesen / Oberflaechenfraesen / 5-Achsfraesen (otMillingMPs) muss Offset mit eingerechnet werden
		If (Obj.ObjectTyp = otMillingMPs) Then
			If (Obj.Tool.ObjectType = htokGearBoxTool) Or (Obj.Tool.ObjectType = htokDH_SawTool) Then
				If PostSettings.GeneralSettings.RelativToRefSpindle Then
					OffX = -Obj.HeadOffX + AggOffX   ' statischer offset () zu Spindelbezugspunkt
				Else
					OffX = -Obj.HeadOffX ' statischer offset () zu Spindelbezugspunkt
				End If
				
			Else
				If PostSettings.GeneralSettings.RelativToRefSpindle Then
					OffX = AggOffX   ' statischer offset () zu Spindelbezugspunkt
				Else
					OffX = -Obj.HeadOffX ' statischer offset () zu Spindelbezugspunkt
				End If
			End If
			'OffX = 0
		ElseIf (Obj.ObjectTyp = otMillingPoints) Then
			If PostSettings.GeneralSettings.RelativToRefSpindle Then
				OffX = AggOffX   ' Aggregatsoffset
			Else
				OffX = 0
			End If
		Else 
			pp_err(0,"wrong kind of working"+Obj.Tool.Description)
		End If
		
		MinX = tmp_MinX + OffX - NCData.NCParts.GetNCPart_Index(0).OffX - NCData.NCParts.GetNCPart_Index(0).StopX
		MaxX = tmp_MaxX + OffX - NCData.NCParts.GetNCPart_Index(0).OffX - NCData.NCParts.GetNCPart_Index(0).StopX

	End If

	MT_ClearTHopsBasicToolExt(T_Tmp)

	
End Function



Function Evo_Check_MeaDrill(x)

	If JobPara.is_Evo Then
		JobPara.mea.Bea_Mea_activ = False
		If x <= JobPara.mea.QuoteXQD Then
			' Bohrung mit Messwert - Verrechnung gefunden
			JobPara.mea.Bea_Mea_activ = True
		End If
	End If
	
End Function

Function Evo_Check_MeaMill(Obj,MinX,MaxX)   ' MinMax Rueckgabe fuer InfoZwecke
	If (JobPara.is_Evo) And (Not Obj Is Nothing) Then
		JobPara.mea.Bea_Mea_activ = False
		
		If Version_Check("7.0.0.449",False) Then
			' ab Version > 7.0.0.440 		
			Evo_GetMinMax_V2(Obj,MinX,MaxX)  ' korrigierte Version
		Else
			' bis Version 7.0.0.440 
			Evo_GetMinMax_V1(Obj,MinX,MaxX)  ' alte NCData - Logik
		End If
		

		If (MinX <= JobPara.mea.QuoteXQM) And (MaxX <= JobPara.mea.QuoteXQM) Then
			' Bearbeitung liegt komplett im Messbereich
			JobPara.mea.Bea_Mea_activ = True
		End If
	End If
	
End Function

Function wcnc_Evo_Mea

	If JobPara.is_Evo Then
		If (Firsttime_Viewchange) And (Marker.RollerTrackDown) Then
			' MW 04.04.2014
			' Formatierung unten aktiv 
			' Aufruf Messzyklus darf erst nach Rollerbahn hoch kommen
		'ElseIf JobPara.mea.MessSzene(JobPara.actscene)=True Then
		ElseIf (JobPara.mea.MessSzene(JobPara.actscene)=True) And (Not Marker.RollerTrackDown)  Then
			' MW 17.07.2014 erst wenn die Rollen freigeben (also nach letzter Formatierung unten kann gemessen werden)			
			' MW 05.03.2014
			wcncCom("TEILE Laengenvermessung - MaxMessDiff:"+FToS(JobPara.Mea.MaxMessDiffX)+" DH_HorSic:"+(TDATA.MachineData.GetDrillingHead_Index(0).SecurityHorz))
			'wcnc(ISG_MEACYCLE+"("+FToS(JobPara.Mea.MaxMessDiffX)+","+FToS(TDATA.MachineData.GetDrillingHead_Index(0).SecurityHorz)+")")
			ISG_CC(ISG_MEACYCLE,JobPara.Mea.MaxMessDiffX, TDATA.MachineData.GetDrillingHead_Index(0).SecurityHorz)
			JobPara.mea.MessSzene(JobPara.actscene)=False  ' stellt einmaliges absetzen sicher !
		End If
	End If
	
End Function

Function Read_MPara_ADD
Dim BList(5) As Long 
Dim i As Integer 
	BList(0) = 1006
	BList(1) = 1010
	BList(2) = 1050
	BList(3) = 1060
	
	If JobPara.isg Then
		BList(4) = 1015
		BList(5) = 1016
	End If
	
	For i = 0 To UBound(BList)
		If MT_Get_MachPara_Add(BList(i))<>"" Then
			pp_err(7,BList(i))
		End If
	Next i
	
	mPara_Add.Laser_HeadID = IIf(MT_Get_MachPara_Add(1200)="",110,MT_Get_MachPara_Add(1200))
	' -
	mPara_Add.ShowTravLPointer = IIf(MT_Get_MachPara_Add(1070)="",0,MT_Get_MachPara_Add(1070))
	mPara_Add.ShowPadsLPointer = IIf(MT_Get_MachPara_Add(1071)="",1,MT_Get_MachPara_Add(1071))
	mPara_Add.ShowWorkPieceContour = IIf(MT_Get_MachPara_Add(1072)="",1,MT_Get_MachPara_Add(1072))
	' -
	mPara_Add.PARK_DIST_X_Field1 = IIf(MT_Get_MachPara_Add(1130)="",500,MT_Get_MachPara_Add(1130))
	mPara_Add.PARK_DIST_X_Field2 = IIf(MT_Get_MachPara_Add(1131)="",800,MT_Get_MachPara_Add(1131))
	' - 
	mPara_Add.sc_minfeed = 30
    If Not MT_Get_MachPara_Add(1015)="" Then
		mPara_Add.sc_minfeed = StrToFloat(MT_Get_MachPara_Add(1015))
	End If
	mPara_Add.sc_contprec = 0.05
	If Not MT_Get_MachPara_Add(1016)="" Then
		mPara_Add.sc_contprec = StrToFloat(MT_Get_MachPara_Add(1016))
	End If
		
	' -
	mPara_Add.Threshold1 = IIf(MT_Get_MachPara_Add(100100)="",120,MT_Get_MachPara_Add(100100))
	mPara_Add.Threshold2 = IIf(MT_Get_MachPara_Add(100101)="",170,MT_Get_MachPara_Add(100101))
	mPara_Add.Threshold3 = IIf(MT_Get_MachPara_Add(100102)="",220,MT_Get_MachPara_Add(100102))
	' -
	mPara_Add.KEEP_ZSIC_AFTER_TC = IIf(MT_Get_MachPara_Add(1020)="",False,MT_Get_MachPara_Add(1020))
	mPara_Add.WRITE_COMMENTS = IIf(MT_Get_MachPara_Add(1100)="",False,MT_Get_MachPara_Add(1100))
	mPara_Add.Script_Info = IIf(MT_Get_MachPara_Add(1101)="",False,MT_Get_MachPara_Add(1101))
	
	
End Function

Function Mill_c_Activ As Boolean
	Mill_c_Activ = equal(PPara.MMode,1)
End Function


Function Get_mill_c_kw As Double
	Get_mill_c_kw = PPara.MinTipA
End Function

Function ClearMTData
Dim i As Integer
  MT_ClearTHopsBasicToolExt(ActT)
  MT_ClearTHopsBasicToolExt(LastT)
  MT_ClearTHopsBasicToolExt(FirstT)
  MT_ClearTHopsBasicToolExt(TCB_T)
  
  If Marker.CountOfTool>0 Then
	  For i = LBound(ToolArray) To UBound(ToolArray) Step 1
    	MT_ClearTHopsBasicToolExt(ToolArray(i))
	  Next i
  End If
  ProcessInfoClear(Ppara)
End Function


Function wcnc_DustSuction(Pos)

	If Not actt.SetOf_DustPositions Is Nothing Then
		If Not equal(Pos,Marker.Last_SuctionPos) Then
			' Pos
			' 0: Keine
			' 1: dynamisch
			' >1 : definierte Position -> dann muss Pos -1 gerechnet werden
			wcncAddCom(actt.SetOf_DustPositionsMFunc.GetString(IIf(Pos>1,Pos-1,Pos)),"DustSuction",True)
			Marker.Last_SuctionPos = Pos			
		End If
	End If

		
	
End Function


Function wcnc_TCP_Offset_On(Kind)

	'If MT_Is_Vertical_StandardTool5Axis(ActT) Then
    If (MT_Is_Vertical_StandardTool5Axis(ActT)) Or (MT_IsGearBoxTool(actt) And MT_H_Is_5_Axis(actt)) Then	
		If (MT_IsGearBoxTool(actt) And MT_H_Is_5_Axis(actt)) Then
			' MW 22.03.2016 Bei Winkelgetrieben auf 5Achs Bezug immer Kopf
			' d.h. nur bei Kind = -1 setzen
			If equal(Kind,-1) Then
				If Not equal(actt.h.RotPointOffZ,0) Then
					' Bezugspunkt Schnittpunkt Achsen
					' MW 21.01.2016 die folgenden Koordinaten beziehen sich immer auf die Plananlage der Spindel - Werkzeugbezugspunkt
					' MW 28.01.2016 hier muss eigentlich die ID -20001 verrechnet werden
					wcnc("G90 G92 X=0 Y=0 Z="+FToS(actt.h.RotPointOffZ))
				Else
					wcnc(";G90 G92 X=0 Y=0 Z="+FToS(actt.h.RotPointOffZ))
				End If
			End If
		Else
			If (equal(Kind,-1) Or equal(Kind,1)) Then
				If Not equal(actt.h.RotPointOffZ,0) Then
					' Bezugspunkt Schnittpunkt Achsen
					' MW 21.01.2016 die folgenden Koordinaten beziehen sich immer auf die Plananlage der Spindel - Werkzeugbezugspunkt
					' MW 28.01.2016 hier muss eigentlich die ID -20001 verrechnet werden
					wcnc("G90 G92 X=0 Y=0 Z="+FToS(actt.h.RotPointOffZ))
				Else
					wcnc(";G90 G92 X=0 Y=0 Z="+FToS(actt.h.RotPointOffZ))
				End If
			End If
		End If
	End If
	
End Function

Function wcnc_TCP_Offset_Off(Kind)
	'If (MT_Is_Vertical_StandardTool5Axis(ActT)) Then
    If (MT_Is_Vertical_StandardTool5Axis(ActT)) Or (MT_IsGearBoxTool(actt) And MT_H_Is_5_Axis(actt)) Then	
		If (MT_IsGearBoxTool(actt) And MT_H_Is_5_Axis(actt)) Then
			' MW 22.03.2016 Bei Winkelgetrieben auf 5Achs Bezug immer Kopf
			' d.h. erst bei Kind =1 wieder abloeschen
			If equal(Kind,1) Then
				If Not equal(actt.h.RotPointOffZ,0)Then
					wcnc("G90 G92 X=0 Y=0 Z=0")
				Else
					wcnc(";G90 G92 X=0 Y=0 Z=0")
				End If
			End If
		Else
			If equal(Kind,-1) Or equal(Kind,1) Then
				If Not equal(actt.h.RotPointOffZ,0)Then
					wcnc("G90 G92 X=0 Y=0 Z=0")
				Else
					wcnc(";G90 G92 X=0 Y=0 Z=0")
				End If
			End If
		End If
	End If
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
	For i =  0 To UBound(PPara.NCIExtB) 
		Set iNC = PPara.NCIExtB(i) 
		If Not iNC Is Nothing Then
			Select Case iNC.Kind
				Case 70000,70099
				
				
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

End Function

Function wcnc_NCIExt_After()
Dim i As Long 
Dim iNC As Object ' INCNCInfo
	' Nachwirksame NCIExt absetzen
	For i =  0 To UBound(PPara.NCIExtA) 
		Set iNC = PPara.NCIExtA(i) 
		If Not iNC Is Nothing Then
			Select Case iNC.Kind
				Case 80000
					wcnc_NCIExt_Strs(iNC)   ' Alle Strings ueber ParaCount wegschreiben
			End Select
		End If
	Next i
	
End Function

Function Inc_Process
	Marker.actprocess = Marker.actprocess + 1
	If Not equal(Marker.actprocess,ppara.plno) Then
		pp_err(126)
	End If
End Function
