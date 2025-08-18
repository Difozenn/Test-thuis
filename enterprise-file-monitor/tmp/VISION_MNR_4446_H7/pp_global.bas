' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \%postdir%\pp_global.bas
' -- 
' -----------------------------------------
'#uses "pp_math.bas"
'#uses "pp_clamps.bas"

Option Explicit

'***********************************************************************************
'*************************************  Types  *************************************
'***********************************************************************************


Global Const SCRIPT_VERSION="V7.0.0.1" 

' MW 06.07.2016 -> Aenderung Offsetverrechnung BK

Global Const PPGRP="RB" 'Reichenbacher PP'S Vision, Artis, Ranc Retrofit, Univers 
' mw 04.11.2015 V1.0.5.1 Offsetberechnung fuer winkelgetriebe unter traori ueberarbeitet
' MW 26.02.2013 
' * Rückzugsposition vor dem Zurückschwenken wird mit der aktuellen Position verglichen
'   -> sollte diese "hoeher" sein, dann wird die Ausgabe der PP - Rueckzugsposition unterdrückt !
'   -> gilt für Fräsbearbeitungen !

' MW 02.09.2010 Rückzug hor. Bohren bei Werkstück + ORIAXES

' Neu fuer Artis X neue 2. Version
' Anschlaggruppen von M111 bis M118 maximal
' ist den Nullpunkten hinterlegbar

' OS 02.05.2013
' 1. Sägen als fräsen / Bohren als fräsen
' 2. Neue Schwenklogik	0=Bisherige 1=Dyn 2=ZMax
' 3. Post Bug: RB_BUG_REPORT_2013_04_23_C-Achse_in_Reichenbacher_PPs.doc !!! Normierung C-Achse C <= -360° !!!
' 4. Schwenken ohne Sicherheit eingebaut.
' 5. Konstanten für die Häufigsten Optinosbits angelegt.
' 6. Neue Maschienparameter angelegt

' OS V1.0.1.1 02.09.2013 Gegentest für Spannfunktionen eingeführt.

' OS V1.0.1.2 04.09.2013 Reihenbohraggregat eingeführt.

' OS V1.0.2.0 05.03.2014 Drehbahren Bohrkopf Schaltbar eingefügt.
'						 Verbesserung Dynamisches Schwenken eingeführt.
'						 CPREC ON/OFF Für Frässpindeln über Additions 10201 im Kopf schaltbar gemacht

' OS V1.0.4.0 14.08.2014 PP für Artis X erweitert
' 						 Pfostenspanner hinzugefügt
'						 Spähnetransport Optionsbit eingerichtet.

'OS V1.0.4.2 04.09.2014 	'1. Erkennung Bohrkopftyp angepasst Drehbahr/NichtDrehbar Bug behoben
						   	'2. Stopre vor radiusschreiben C-Achsenfräsen eingeführt weil Maschine unerwartet vorliest.
							'3. Mill_C Trc=0 gesetzt

'OS V1.0.4.3 02.03.2015		'1. Reichenbacher lagemessen mit eingebaut.
							'2. Rotationsachse eingebaut
							'3. Messen xyz vorbereitet
							
'OS V1.0.5.0 21.09.2015		'1. Reichenbacher Leitblech-Haube für 4-Achsspindel eingebaut
							'2. C-Achsfräsen überarbeitet
							'3. Unterflurfräsen eingeführt
							'4. Winkelgetriebe überarbeitet
							'5. Neue Vorwechsel-Startegie eingeführt.
'-------------------------------------------------------------------------------------------------------------------------							


'Nummer der Optionsbits OS 02.05.2013 Hier knoenen die optionsbits den namen zugewiesen werden.
'Unbenutzte sind auf eienen Wert >=15 <=31 zu setzen
'---------------------------------------------------
'OS 28.11.2016 Optionsbits für MNR 44446 eingestellt. 
Global Const VacOffAtEnd=1			'Switchen der Optionsbits Vakuum aus am ende des programms
Global Const PneuOffAtEnd=2		    'Pneumatik aus am ende des Programms
Global Const PinsUpAtEnd=3			'Anschläge Hoch am ende des Programms
Global Const IsNestingMode=15		'Maschen Läuft im nesting Modus
Global Const PinsUpAtStart=4 		'Pins Hoch am Anfang
Global Const HoldVacPads=5			'Vacuum für Sauger halten wenn am Ende entspannt wird
Global Const DontUse2VacField=6 	'2. Vacuumkreis aus
Global Const DontUse3VacField=15	'3. Vacuumkreis aus
Global Const DontUse4VacField=15	'4. Vacuumkreis aus 
Global Const RotAddAAxis=15    		'Zusätzliche Rotationsachse ansteuern
Global Const Tornado=15      		'Tornado ein
Global Const SuppsUpAtEnd=15		'Unterstützer Hoch am ende
Global Const SuppsUpAtStart=15		'unterstützer hoch am anfang
Global Const CleanTable=15    		'Tisch Reinigen am Anfang
Global Const TurnCleanDirection=15   'Richtung Reinigen umkehren
Global Const AusTransPortPos=15   	'Träger für Austransport einrichten
Global Const EinTransPortPos=15   	'Träger für Austransport einrichten
Global Const UsePfosten=15			'Pfostenspannvorrichtung ein
Global Const UnClampPfo=15			'Pfostenspanner am ende des Pgm. Entspannen
Global Const UseSTransp=15			'Spähnetransport ein/aus
Global Const PinsUpSonder=15			'Anschlag Moebel
Global Const CheckToolOnChange=15   'CheckTool mit messen Werkzeug

Global Const DrillingWithG9=True	'Bohren mit genauhalt ein	

Global Const SEPSTR_DOT="."

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

'Machine Kinematik behaviour OS 29.03.2016 
Type TMachineKinematiks
	P(3) As String
End Type

'Marker for Global Machine Kinematik behaviour OS 29.03.2016 
'Switch On at beginn of Process
Global MKG_ON(13) As TMachineKinematiks
'Switch OFF at END of Process
Global MKG_OFF(13) As TMachineKinematiks
'Head
Global HK_ON(13) As TMachineKinematiks
Global HK_OFF(13) As TMachineKinematiks

Global ActHK_OFF As String
Global ActHK_ON As String

Type TMacHKin 
	HK_ON As String
	HK_OFF As String
End Type

Global MachKin As TMacHKin

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


'Process Parameter
'Type TProcessPara
'	PLNo As Long        ' MW 30.03.2016 wird ueber ProcessIndex uebergeben
'	ToolId As Long 
'	Tool As Object 
'	HeadInfo As Variant 
'	HId As Long 
'	ProcInfoStr As String  ' MW 30.03.2016
'	Feedrate As Double
'	I_Feedrate As Double
'	S_Feedrate As Double
'	Speed As Double
'	'RotA As Double
'	'TipA As Double
'	mMode As Integer          ' MillingMode MW 11.01.2016 Parameter von AdditionalSPInfoMPs 
'	ObjectTyp As Integer
'	PreObjectTyp As Integer
'	MinRotA As Double
'	MaxRotA As Double
'	MinTipA As Double
'	MaxTipA As Double
'	DustPosNCIExt As Boolean   ' MW 09.02.2016 NCIExt fuer Haube wurde programmiert
'	NCIExtB() As Object            ' Objectliste aller vorwegwirksamen NCIExt 
'	NCIExtA() As Object            ' Objectliste aller nachwegwirksamen NCIExt 
'	'   OSZ As sTOSZ
'	NTool As Object     ' folgendes Werkzeug
'	NHeadInfo As Variant  ' Head folgendes Werkzeug
'End Type
'
'Global PPara As TProcessPara    ' MW 16.02.2016 hier werden unter anderem Vorschuebe, NCInfos (Haubenpos) etc. zugeordnet

'ALL Process Parameter
Type TAllProcessPara
	ProcessType As String
	View As Integer
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


Type TFinishedPart
   x As Double
   Y As Double
   Z As Double
End Type

Type TMovePara
  TRC As Long
  Feedrate As Long
End Type

Type TPos
   x As Double
   Y As Double   
   Z As Double
End Type

Type TMessPunkt
	Mess_Nr As Integer
	Xm As Double   ' Messpunkt X
	Ym As Double	' Messpunkt Y
	Zm As Double 	' Messpunkt Z
	X_S As Double   ' Messpunkt Start X
	Y_S As Double   ' Messpunkt Start Y
	Z_S As Double   ' Messpunkt Start Z
	Richtung As Integer  ' (0=Z) (1=Y+) (2=X+) (3=Y-) (4=X-)
	Messtyp As Integer  ' 
	str1 As String 
	Str2 As String 
	gemessen As Boolean
	RPara As String  ' Parameter in welchem Steuerungsseitig die gemessenen Werte gespeichert werden - jeweils in einer Achse!
End Type

' Workpiece - Info
Type TWPI
    SName As String       ' AnschlagName
    Sox As Double         ' Anschlag Offset X  
    Soy As Double         ' Anschlag Offset Y
    Soz As Double         ' Anschlag Offset Z
    WPName As String      ' Werkstück -Name
    WPox As Double        ' Werkstück Offset X
    WPoy As Double        ' Werkstück Offset Y
    WPoz As Double        ' Werkstück Offset Z 
    WPx As Double         ' Werkstück Breite
    WPy As Double         ' Werkstück Länge   
    WPz As Double         ' Werkstück Dicke
    Trav() As TTrav       ' array of traversen
    Origin As Long        ' AnoptiMT - Nullpunkt
    ClampType As Long  ' Spanntyp Vacuum, uniclamp
    xMessPunkte() As TMessPunkt   ' auf dieses Array werden alle Messpunkte geschrieben
	Activ_Messpoint As Integer    ' das ist die Aktive MessPos wenn gemessen werden soll, oder gemessener  
End Type

Global WPI() As TWPI
'Global wpi_actindex As Long    ' Aktueller Indexzähler
'Global wpi_lastindex As Long    ' letzter Indexzähler - wird für Werkstückwechsel benötigt

Type TLage
	V_MESS As Long
	V_WKZ_NR As Long
	V_ANSCHLAGART As Long
	V_MESSPOS_Y1 As Double
	V_MESSPOS_X1 As Double
	V_MESSPOS_X2 As Double
	V_MESSPOS_Z1 As Double
	V_MESSPOS_ZX As Double
	V_MESSPOS_ZY As Double
End Type

Global Lage As TLage


Type TProcessMinMaxWindow
	xMin As Double        ' kleinster X - Wert der Bearbeitung
	yMin As Double        ' kleinster Y - Wert der Bearbeitung 
	zMin As Double        ' kleinster Z - Wert der Bearbeitung 
	xMax As Double        ' größter X - Wert der Bearbeitung
	yMax As Double        ' größter Y - Wert der Bearbeitung
	zMax As Double        ' größter Z - Wert der Bearbeitung 
	zMintmp As Double
	zMaxtmp As Double
End Type
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


' Variables from interface "work-center"
Global Type ThopsJobPara
	Activ_Fields As Integer         ' Aktive Felder 1=links 2=rechts 3=gekoppelt
	Laser_Activ As Boolean          ' wird 1 gesetzt wenn Punktlaser aktiviert 
    Position As Integer				' Anschlagposition
    flag As Variant					' Flag
    NPX As Double					' Nullpunkt X
    NPY As Double					' Nullpunkt Y
    NPZ As Double					' Nullpunkt Z
    AUFMASSX As Double				' Aufmass X
    AUFMASSY As Double				' Aufmass Y
    Pad_Z As Double					' Saugerhöhe
    Jig_Z As Double					' Schablonenhöhe
    'Sic_Z As Double					' muss von Engine bereits verrechnet worden sein
    									' zusätzlicher Sicherheitsabstand z.B. Spannmittel Überstand übers Werkstück
    MirrorX As Boolean
    MirrorY As Boolean
    Park As Integer					' Parkpos 1 = Links hinten 2=rechts hinten 3=mitte hinten
    ParkX As Double
    Parky As Double
    Language As TLanguage           ' wird aus iiSettings ermittelt
    HopsPath As String 				' wird aus iiSettings ermittelt
    HPGL_TimeStamp As String        ' Neu MW 2.8.2005 für check ob korrekte HPGL-Datei
    Add_ZSic As Double              ' Neu MW 14.09.2005 zusätzliche Z-Sicherheit
    WorkC_OptionBit As Long         ' -- MW 17.07.2008 15:47:38 Optionsbits aus Workcenter pp.ini [Workcenter] BitOptions=1
    RealNCFileName As String        ' -- ToCheck OS/MW
    lStp As Integer                 ' -- MW 14.01.2016 LineStep
    is_5Axis_Machine As Boolean    ' MW 20.01.2016 steuert WriteNCMillingPointsHeadData in InitDLLMPs_Milling
    TimerFullSecs As Double        ' MW 01.02.2016 Timer ueber ALLES
    P_Info As String          	   ' -- MW 21.12.2015 Info- String ueber die Bearbeitung  ToCheck OS/MW
End Type
Global JobPara As THopsJobPara

Global Type ThopsMachineData
    ParkposX As Double
    ParkposY As Double
    ParkposZ As Double
    DustExt1 As Double	' Schwellwert 1 Absaugung 
    DustExt2 As Double	' Schwellwert 2 Absaugung
    DustExt3 As Double	' Schwellwert 3 Absaugung
    DustExt4 As Double	' Schwellwert 4 Absaugung
End Type

Global MachinePara As ThopsMachineData


' -------------------------------------------------------------
' -- Hier Type für Merker
Global Type TMarker
    Last_Liftpos As Integer
    LiftPos_Startup As Integer
    LiftPos_Processing As Integer
    Last_BM As TBMuster
    Last_DH_Process As String       	' marker lastproces DrillingV->DH Vertikal DrillingH->DH horizontal
    last_DH_TLength As Double    		' marker last length of drilling 
    Last_DH_ToNo As Long            	' letzte Bohrspindel T-Nummer
	Last_DH_DZ As Double 
	FirstTime_DH_Drilling As Boolean   	' Merker für Bohrkopf Bohren aktiv
    Viewchangechecked As Boolean    	' spezialmerker zum check ob viewchange bereits durchlaufen
    WP_ActIndex As Long      			'  Workpiece - Index - Zähler
    WP_LastIndex As Long      			'  Workpiece - Index - Zähler
    Pneumatic_Channel() As Long   		' pneumatik channel - merker, da NCInfo viel zu früh kommt - wird dann erst bei StartMilling aufgerufen
    Programmed_DH_Speed As Double   	' Merker, programmierte Drehzahl Bohrkopf
    Last_ExhaustPos As Integer   		' Merker für Absaugung
	DINISO_PROCESS As Boolean   
	DINISO_MODE As Integer 				' Mode für DINISO-Programm
	DINISO_LIFTPOS	As Integer 			' Position für Vorlegehub -1 = bevorzugte Stellung
	LastNC As String            		' Merker zuletzt abgesetzter NCCode - Zeile
	DH_String As String    				' MW 19.06.2008
	Blowing As Boolean     				' MW 31.03.2010
	AAxiss As Boolean      				' OS 22.04.2010
	Etikett As Boolean     				' OS 23.11.2010
	PrinterIsUp As Boolean 				' OS 14.12.2010
	PNo As Long
	Spez_Schwenk As Boolean 			' OS 02.05.2013 Neue Scherheits-/Schwenklogik 0=Aus [Alte Logik] 1=SaftyPart 2=ZMax
	Z_Schwenk As Double					' OS 02.05.2013 Neue Scherheits-/Schwenklogik Schwenkhöhe 
	X_Schwenk As Double					' OS 02.05.2013 Neue Scherheits-/Schwenklogik Schwenkhöhe 
	Y_Schwenk As Double					' OS 02.05.2013 Neue Scherheits-/Schwenklogik Schwenkhöhe 
	Messbezug As Boolean 
	MessbezugX As Long
	MessbezugY As Long
	MessbezugZ As Long
	FaktorX As Double
	FaktorY As Double
	FaktorZ As Double
	LastFaktorX As Double
	LastFaktorY As Double
	LastFaktorZ As Double
	LastMove As String
	LastMessbezugX As Long
	LastMessbezugY As Long
	LastMessbezugZ As Long
	MeasureActiv As Boolean 		
	Ueberfahren As Double
	MeasProtPath As String
	DoorMeasureActiv As Boolean
	GetDoorMeasure As Boolean
	DoorMeasureCount As Integer
	Path_OFF As Boolean 
	GetDrillMeasureX As Boolean 
	DrillMeasureXCount As Integer
	GetDrillMeasureY As Boolean 
	DrillMeasureYCount As Integer
	FirstMeasure As Boolean 
	C_Poly As Boolean
	RotAngle_DrillingHead_Stroke As Double  	' -- OS 03.03.2014 Drehbarer Bohrkopf Eingebaut
    LastRotAngle_DrillingHead_Stroke As Double  ' -- OS 03.03.2014 Drehbarer Bohrkopf Eingebaut
    CPREC As Long								' -- OS 03.03.2014 Schaltbar gemacht
    TranspOn As String 
    TranspOff As String 
    NextHid As Long 
    FirstT As Boolean 
	LastSpeed As Double     ' MW 16.02.2016 Merker fuer zuletzt ausgebene Spindeldrehzahl
	BStris As NCData_SetOfString    ' MW 24.02.2016   Liste der Strings fuer wegschreiben NCIExt nach der Anfahrbewegung ueber DLL-Milling
	AStris As NCData_SetOfString    ' MW 24.02.2016   Liste der Strings fuer wegschreiben NCIExt vor der Abfahrbewegung ueber DLL-Milling
	actprocess As Long
End Type

Global Marker As TMarker
'    Last_BM1 As Double
'    last_BM2 As Double

' -------------------------------------------------------------
' -- Hier Type für einen Bohrer vom Bohrkopf
Global Type tDriller
	TName As String         ' Name
	TNo As Long              ' TNummer des Bohrers auf der Steuerung
	V As Double        ' Vorschub
	VE As Double       ' Eintauchvorschub
	VA As Double       ' Austauchvorschub
	Length As Double         ' Bohrer Länge
	E_Len As Double          ' Bohrer Überstand 
	offx As Double           ' Offset zum Referenzbohrer X 
	offy As Double           ' offset zum Referenzbohrer Y
	offz As Double           ' offset zum Referenzbohrer Z
	Edge As IICuttingEdge    ' Schneidendaten des Bohrers
	TP As IIDH_ToolPlace     ' Toolplace Daten des bohrers
	Speed As Double          ' SollDrehzahl Neu MW 09.08.2005
	ActRot As Double         ' MW 10.08.2009 10:19:00 gibt den aktiven Rotationswinkel für drehbare Bohrkoepfe
End Type

' -------------------------------------------------------------
' -- Hier Type für Bohrkopfdaten
Global Type tDH
	TName As String         ' Name
	V As Double        ' Vorschub
	VE As Double       ' Eintauchvorschub
	VA As Double       ' Austauchvorschub
	centerx As Double           ' Offset zum Referenzbohrer X 
	centery As Double           ' offset zum Referenzbohrer Y
	centerz As Double           ' offset zum Referenzbohrer Z
End Type

Type Info_T
	BoxNo As Long
	AggNo As String
	HeadID As String 
	TC_PLACE As Integer 
	T_Speed As Integer
	P_Speed As Integer 
	MaxRotSpeed As Integer
	Dr As Integer 
	Dz As Integer 
	AddMx As Double 
	AddMy As Double 
	AddMz As Double 
	SPVX As Double 
	SPVY As Double 
	SPVZ As Double 
	DoIt As Integer
End Type

Global Info_FT As Info_T
Global Info_TCBT As Info_T 
Global info_h1 As Info_T  
Global info_h2 As Info_T  

' -------------------------------------------------------------
' -- Hier Type für Bohren mit Reihenbohrgetriebe mehrfach
Global Type tMultiDrilling_GBHeadVert
	dw As Double
	angle As Double
End Type

Global Type tUnderside
 	dw As Double
 	view_w As Double 
End Type

' -------------------------------------------------------------
' -- Hier Type für Laserpointer
Global Type TLaserPointerf
	x As Double
	Y As Double
	Typ As Double
End Type
Global LaserPointer() As TLaserPointerf
Global isLaserpointer As Boolean

'Spanninfo für Nestingtisch
Global Type TFieldMask
	M(3) As Boolean 
	BitMask As Long 
	AsStr As String 
	BitMaskR As Long 
	AsStrR As String 
End Type

Global FieldMask As TFieldMask


' -------------------------------------------------------------
' -- Hier Type Werkzeugzusatzinformation für Frässpindel
Global Type t_PH_Additions
	ToolChangeMode As Integer              	' Werkzeugwechsel - Modus #10000
	Traori As Boolean        				' 5-Achs Transformation vorhanden oder nicht #10001
	TraoriOn As String
	TraoriOff As String
	ToolNo As Long  						' TNum = 0 dann Wechselplatz - Nummer Tnum>0 dann diese Nummer
	CorrNo As Long  						' DNum = 0 dann Schneidennummer DNum >0 dann diese Nummer
	HaubeTyp3Achs As Long					' -- OS 02.05.2013 Typ 3-Achshaube 0=Keine/Statische 1=FixVorlegbar 2=FreiVorlegbar 3=DynVorlegbar
	HaubeTyp5Achs As Long					' -- OS 02.05.2013 Typ 5-Achshaube 0=Keine/Statische 1=FixVorlegbar 2=FreiVorlegbar 3=DynVorlegbar
	HaubeTypDH As Long						' -- OS 05.03.2014 Typ DrillHeadHaube 0=Keine/Statische 1=FixVorlegbar 2=FreiVorlegbar 3=DynVorlegbar
	HaubeMaxToolRad3Achs As Double			' -- OS 02.05.2013 Typ 3-Achshaube Collradius Tool
	HaubeMaxToolRad5Achs As Double			' -- OS 02.05.2013 Typ 5-Achshaube Collradius Tool
	Haube3AchsCPos As Double				' -- OS 16.05.2013 Typ 3-Achshaube C-Achs-position für vor und zurücklegen
	ToolChangeType As Long 					' -- OS 13.03.2014 0= Wechsel(T,Dr,S) 1=Wechsel(T,Dr,S,,) 1=Wechsel(T,Dr,S,XS,YS)
	ToolCheckForDrillhead As String
	SpindleOff As String					' -- OS 27.06.2014 Spindel Aus
End Type


Global Type t_H_Additions
	ToolChangeMode As Integer              	' Werkzeugwechsel - Modus #10000
	Traori As Boolean        				' 5-Achs Transformation vorhanden oder nicht #10001
	TraoriOn As String
	TraoriOff As String
	ToolNo As Long  						' TNum = 0 dann Wechselplatz - Nummer Tnum>0 dann diese Nummer
	CorrNo As Long  						' DNum = 0 dann Schneidennummer DNum >0 dann diese Nummer	
	HaubeTyp3Achs As Long					' -- OS 02.05.2013 Typ 3-Achshaube 0=Keine/Statische 1=FixVorlegbar 2=FreiVorlegbar 3=DynVorlegbar
	HaubeTyp5Achs As Long					' -- OS 02.05.2013 Typ 5-Achshaube 0=Keine/Statische 1=FixVorlegbar 2=FreiVorlegbar 3=DynVorlegbar
	HaubeTypDH As Long						' -- OS 05.03.2014 Typ DrillHeadHaube 0=Keine/Statische 1=FixVorlegbar 2=FreiVorlegbar 3=DynVorlegbar
	HaubeMaxToolRad3Achs As Double			' -- OS 02.05.2013 Typ 3-Achshaube Collradius Tool
	HaubeMaxToolRad5Achs As Double			' -- OS 02.05.2013 Typ 5-Achshaube Collradius Tool
	Haube3AchsCPos As Double				' -- OS 16.05.2013 Typ 3-Achshaube C-Achs-position für vor und zurücklegen
	ToolChangeType As Long 					' -- OS 13.03.2014 0= Wechsel(T,Dr,S) 1=Wechsel(T,Dr,S,,) 1=Wechsel(T,Dr,S,XS,YS)
	ToolCheckForDrillhead As String
	SpindleOff As String
	HK_ON(13) As TMachineKinematiks
	HK_OFF(13) As TMachineKinematiks
	MCorrNo As Long 
	MLTolCorr As Double 
	MRTolCorr As Double
End Type

Global Type t_DH_Additions
	HaubeTyp3Achs As Long					' -- OS 02.05.2013 Typ 3-Achshaube 0=Keine/Statische 1=FixVorlegbar 2=FreiVorlegbar 3=DynVorlegbar
	HaubeTyp5Achs As Long					' -- OS 02.05.2013 Typ 5-Achshaube 0=Keine/Statische 1=FixVorlegbar 2=FreiVorlegbar 3=DynVorlegbar
	HaubeTypDH As Long						' -- OS 05.03.2014 Typ DrillHeadHaube 0=Keine/Statische 1=FixVorlegbar 2=FreiVorlegbar 3=DynVorlegbar
	HaubeMaxToolRad3Achs As Double			' -- OS 02.05.2013 Typ 3-Achshaube Collradius Tool
	HaubeMaxToolRad5Achs As Double			' -- OS 02.05.2013 Typ 5-Achshaube Collradius Tool
	Haube3AchsCPos As Double				' -- OS 16.05.2013 Typ 3-Achshaube C-Achs-position für vor und zurücklegen
	ToolCheckForDrillhead As String
End Type
' merker fürs Sägen

Global Type TMarkerSawing
	LastIsSawing As Boolean
	LastKW As Double
End Type

'-------------------------------------------------------------------
'Merker für die Haube M21/M20
'-------------------------------------------------------------------

Global Type THaube
	pos As Long					'Wird im Toolaufruf gesetzt Auto
	IsEbene0 As Boolean  		'3-Achsbearbeitung ja/nein nur in Null ebene erlaubt
	P3AchsUseIt As Boolean 		'Haube vorgelegt ja/nein
	P5AchsUseIt As Boolean		'Haube vorgelegt ja/nein
	PDHUseIt As Boolean			'Haube vorgelegt ja/nein
	P3AchsAktiv As Boolean 		'Haube vorgelegt ja/nein
	P5AchsAktiv As Boolean		'Haube vorgelegt ja/nein
	PDHAktiv As Boolean			'Haube vorgelegt ja/nein
	P3AchsPos As Double			'Letzte position
	P5AchsPos As Double			'Letzte position
	PDHPos As Double		'Letzte position
	P3AchsLastPos As Double		'Letzte position
	P5AchsLastPos As Double		'Letzte position
	PDHLastPos As Double		'Letzte position
	P3AchsAuto As Boolean		'Automatisch Vorlegen wenn Ebene0
	P5AchsAuto As Boolean		'Automatisch Vorlegen wenn Ebene0
	PDHAuto As Boolean			'Automatisch Vorlegen wenn Ebene0
	P3AchsTc As Boolean			'Vor ToolChange Auswechseln
	P5AchsTc As Boolean			'Vort ToolChange Auswechseln
	PDHTc As Boolean			'Vort ToolChange Auswechseln
	P3AchsRetreat As Boolean
	PLeitBlechUseIT As Boolean 
	PLeitblechAktiv As Boolean 
	PLeitblechPos As Double 
	PleitblechDist As Double 
	PLeitblechLastPos As Double 
	PleitblechLastDist As Double 
	PLeitblechTc As Boolean 
	NewHaubePosBeforeTC As Long
	LastTipAng As Double
End Type

Global Haube As THaube

Global Type TSpruehEinr
	Spruehen As Boolean 
	MittelOn As String 
	MittelOff As String
End Type

Global SpruehEinr As TSpruehEinr

Global Type TSpindleBlowNozzle
	Blow As Boolean
	Nozzle As Integer
	LNozzle As Integer
End Type

Global SpindleBlowNozzle As TSpindleBlowNozzle

Global Type TSawBlowNozzle
	Blow As Boolean
	Nozzle As Integer 
	LNozzle As Integer
End Type

Global SawBlowNozzle As TSawBlowNozzle


Global Type TDrehmoment
	Blow As Boolean
	Nozzles As Integer
End Type

Global Drehmoment As TDrehmoment

'Pintisch Infos
Global Type TPinTischPins
	BitStr As Integer 
	Pins(22) As String
	VerweilZeit As String
	PinsUp As String
	Unterstuetzer As String
End Type

Global PinTischPins As TPinTischPins

'Global MFunction As TMFunctions
' Optionbits ersetzt dies


' MW 23.02.2016 Ex - Ascript - Einstellungen
Global Type tmPara_Add
	' -
	' -
	PARK_DIST_X_Field1 As Double     ' (500)   ID 1010
	PARK_DIST_X_Field2 As Double     ' (800)   ID 1011
	' -
'	Threshold1 As Double   ' (120)   ID 100100   auch schon In V6
'	Threshold2 As Double   ' (170)   ID 100101   auch schon In V6
'	Threshold3 As Double   ' (220)   ID 100102   auch schon In V6
	' -
'	KEEP_ZSIC_AFTER_TC As Boolean  ' (0)        ID 1020
	Write_COMMENTS As Boolean      ' (0)        ID 1100
	Script_Info As Boolean         ' (0)        ID 1101
	' -
'	sc_minfeed As Double 
'	sc_contprec As Double 
End Type

Global mPara_Add As tmPara_Add
'***********************************************************************************
'*************************************  Variables  *********************************
'***********************************************************************************



'global nc path
Global ncpathGlobal As String
Global NCNameGlobal As String
'aktual nc line number
Global NCLine As Long

'actual view
Global ActV As TView
'last view
Global LastV As TView

' --
' Neu MW 09.11.2004
' --
Global ViewBefore As TView


Global FinishedPart As TFinishedPart
'last TRC and Feedrate
Global MovePara As TMovePara
'saved feedrates, speed, tipA, RotA
'Global ProcessPara As TProcessPara
'Global ProcessListCount As Integer
'Global AllProcessListArray() As TAllProcessPara
'Global ProcessNumber As Integer
'Global AllProcessPara As TAllProcessPara


'Last x,y,z position
Global LastPos As TPos
Global LastPosAbs As TPos   ' MW 26.02.2013  Letzte Fräsposition absolut


'true if safe position
Global Z_Is_Safety As Boolean
Global Z_Is_SafetyPart As Boolean


'true if last process is Sawing
Global MarkerSawing As TMarkerSawing

Global ToolChangeBeforeStr As String


Global FloatFormat As String

Global Nullpunkt As String
Global NullpunktNummer As Integer
Global Firsttime_Viewchange As Boolean



'Global ToolsUsed As Long
'Count of Tools in ToolArray
Global CountOfTool As Long

' Neu MW 14.05.2003
Global C_AchsPos_Mehrspindler As Double

Global Bahnverhalten As Long

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

Global HeadID As Variant

'Global G_T As THopsBasicToolExt

' Offset Parameter für die Verrechnung bis zum Bearbeitungskopf - Ausgang
Global Const OffPX = "OOX"
Global Const OffPY = "OOY"
Global Const OffPZ = "OOZ"

Global Const TCARR = "TCARR=1"
Global Const PARKXVAR = "PX"
Global Const PARKYVAR = "PY"


Global Const DRILL_DHV="DRILLINGV"
Global Const DRILL_DHH="DRILLINGH"

Global Const NCINFOPARKINFO=55
Global Const NCINFOMFUNCTIONS=56

Global Const MAX_LIMIT_ZPLUS="MAXZ"
Global Const MAX_LIMIT_XPLUS="MAXX"
Global Const MAX_LIMIT_XMINUS="MINX"
Global Const MAX_LIMIT_YPLUS="MAXY"
Global Const MAX_LIMIT_YMINUS="MINY"

Global Const DCORRECTIONMARKER="DCMARKER"


Global DH_View0 As TView

Global SecMidnight As Double

Global StartMoveReady As Boolean

'Save Information for Start and Endpoint from Hops
'SF 27.10.2003
Global SP_EP As TSP_EP_No_LeadInOut

' erst wenn diese Variable True, dann setzt wcnc auch was ab
'Global WritingNCData As Boolean
'Global MoveTime_Result As Double

' Log-Datei Array
' MW 5.4.2005
Global LogArr() As String

Global Secs_ToolList As Double


Global NCFileNo As Long   ' NEU MW 12.07.2005   Öffnen - und schreiben des NC-Programms umgestellt

Global MultiDrilling_GBHeadVert As tMultiDrilling_GBHeadVert

Global UndersideTool As tUnderside

Global Retreat_ClampChange As Integer

'Arrays für die Tischfunktionen  OS 02.05.2013
Dim Spannen(10) As Variant   ' M-Funktionen für die Spannabfrage

Dim EntSpannen(10) As Variant   ' M-Funktionen für die Spannabfrage aus

Dim PneumEntSpannen(10) As Variant   ' M-Funktionen für die Spannabfrage aus

Dim PfoSpannen(10) As Variant   ' M-Funktionen für die Spannabfrage aus

Dim PfoEntSpannen(10) As Variant   ' M-Funktionen für die Spannabfrage aus

Dim Anschlag_up(10) As Variant  ' H-Funktionen für die Anschläge

Dim Anschlag_down(10) As Variant  ' H-Funktionen für die Anschläge

Dim Anschlag_downAll(10) As Variant  ' H-Funktionen für die Anschläge

Dim Supporters_down(10) As Variant ' Supporter Hoch

Dim Supporters_Up(10) As Variant   ' Supporter Runter

Dim SpezAnschlag_up(10) As Variant 

Dim SpezAnschlag_down(10) As Variant

Dim Anschlag_Used(10) As Variant

Dim SpezAnschlag_Used(10) As Variant

Dim Supporters_Used(10) As Variant

Global Fix_Zero As Long

Global GTableType As Long 'TischTyp 0=Glatt 1=Traverse

Global GSiemens840DType As Long '840D 0=Bisher 1=Operate

Global GToolChangeCycleName As String 


Function GetT_LENGTH
	GetT_LENGTH="TLENGTH"
End Function

Function GetT_RADIUS
	GetT_RADIUS="TRADIUS"
End Function

' --------------------------------------------------
' --
' -- Viewchange Standard
' -- uses for vertical milling view 0
' --
' --------------------------------------------------

Sub wcncViewChange(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPVX,SPVY,SPVZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
	
	wcnc("TRANS")
	'wcnc("C_FRAME_SAVE")
	'wcnc("D"+IntToS(ActT.T.CorrNo))
	
	' calculate aggregat- offsets 
	
	' (agg offsets) + (output offset) + (Lift offsets)
	
	MT_Write_Offset_NC_Vars   ' writes actual offsets to NC-Vars AOX, AOY, AOZ
								' without rotating output - offset

	If Firsttime_Viewchange Then 
		' Without Z- Positioning
		'wcnc(G0+XEqualToS(SPVX)+"+"+OffPX+ _
		'        YEqualToS(SPVY)+"+"+OffPY)
		        
	End If
	'wcnc(G0+XEqualToS(SPVX)+"+"+OffPX + _
	'        YEqualToS(SPVY)+"+"+OffPY + _
	'        ZEqualToS(SPVZ)+"+"+OffPZ )
	
	'If MT_FiveAxisesToolOK(ActT) Then 
		'wcnc(G0+GetHeadAngles5Achs(RotA,TipA))
	'End If
	
	
	wcnc("TRANS")
	wcnc("ATRANS"+XEqualToS(IPX)+"+"+OffPX+ _
	              YEqualToS(IPY)+"+"+OffPY+ _
	              ZEqualToS(IPZ)+"+"+OffPZ)
	              
	wcnc("AROT"+ZToS(RotA)+XToS(TipA))
	'wcnc("C_FRAME_SAVE")

	
End Sub
' --------------------------------------------------
' --
' -- Viewchange for Printer
' -- uses for vertical milling view 0
' --
' --------------------------------------------------

Sub wcncViewChangePrinter(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPVX,SPVY,SPVZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)

	wcnc("TRANS")
	'wcnc("C_FRAME_SAVE")
	'wcnc("D"+IntToS(ActT.T.CorrNo))
	
	' calculate aggregat- offsets 
	
	' (agg offsets) + (output offset) + (Lift offsets)

	
	MT_Write_Offset_NC_Vars   ' writes actual offsets to NC-Vars AOX, AOY, AOZ
								' without rotating output - offset

	If Firsttime_Viewchange Then 
		' Without Z- Positioning
		wcnc(G0+XEqualToS(SPVX)+"+"+OffPX+ _
		        YEqualToS(SPVY)+"+"+OffPY)
		        
	End If
	wcnc(G0+XEqualToS(SPVX)+"+"+OffPX + _
	        YEqualToS(SPVY)+"+"+OffPY)' + _
	       ' ZEqualToS(SPVZ)+"+"+OffPZ )
	
	'If MT_FiveAxisesToolOK(ActT) Then 
		'wcnc(G0+GetHeadAngles5Achs(RotA,TipA))
	'End If
	
	
	wcnc("TRANS")
	wcnc("ATRANS"+XEqualToS(IPX)+"+"+OffPX+ _
	              YEqualToS(IPY)+"+"+OffPY)'+ _
	              'ZEqualToS(IPZ)+"+"+OffPZ)
	              
	wcnc("AROT"+ZToS(RotA)+XToS(TipA))
	'wcnc("C_FRAME_SAVE")

	
End Sub

' --------------------------------------------------
' --
' -- Viewchange Gearboxes
' --
' --------------------------------------------------
Sub wcncViewChange_GB(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPVX,SPVY,SPVZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
Dim sec,DiffZ As Double
Dim T As IIHopsBasicTool
Dim LiftposDiffZ As Double

	'sec = ActT.t.GetSecurityZ(View)
'	MsgBox(ActT.t.Description+" SecurityZ:"+FToS(sec),vbExclamation)
	
	wcnc("TRANS")
	'wcnc("C_FRAME_SAVE")
	' hier ist jetzt bereits TCorr aktiv (Verrechnung vom Winkelgetriebe) !
	' hier muss jetzt bis zum Aggregatsausgang verrechnet werden..
	'lkjh
	
	MT_Write_Offset_NC_Vars    ' writes actual offsets to NC-Vars 
	
	' check ob spindel korrekt vorgelegt, nur dann darf C-Achse drehen
	MT_Write_Check_Spindle
	wcnc("TRANS")
	wcnc("ATRANS"+XEqualToS(IPX)+"+"+OffPX+YEqualToS(IPY)+"+"+OffPY+ZEqualToS(IPZ)+"+"+OffPZ)
	wcnc("AROT"+ZToS(RotA)+XToS(TipA))
	'wcnc("C_FRAME_SAVE")
	
	
End Sub





' --------------------------------------------------
' --
' -- Viewchange fix Drilling Head and pneumatic Groove Sawing
' --
' --------------------------------------------------
Sub wcncViewChange_SawFix(View,LastView,ByVal IPX,ByVal IPY,ByVal IPZ,RotA,TipA,ByVal SPVX,ByVal SPVY,ByVal SPVZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)


	wcnc("TRANS")
	'wcnc("C_FRAME_SAVE")
'	IPX=IPX-ActT.T.MoveX
'	IPY=IPY-ActT.T.MoveY
'	IPZ=IPZ-ActT.T.MoveZ

	MT_Write_Offset_NC_Vars    ' writes actual offsets to NC-Vars 

	If Firsttime_Viewchange Then 
		' Without Z- Positioning
		wcnc(G0+XEqualToS(SPVX)+"+"+OffPX+ _
		        YEqualToS(SPVY)+"+"+OffPY)
		        
	End If
	wcnc(G0+XEqualToS(SPVX)+"+"+OffPX + _
	        YEqualToS(SPVY)+"+"+OffPY + _
	        ZEqualToS(SPVZ)+"+"+OffPZ )
	
	
	wcnc("TRANS")
	wcnc("ATRANS"+XEqualToS(IPX)+"+"+OffPX+ _
	              YEqualToS(IPY)+"+"+OffPY+ _
	              ZEqualToS(IPZ)+"+"+OffPZ)
	              
	wcnc("AROT"+ZToS(RotA)+XToS(TipA))
	'wcnc("C_FRAME_SAVE")
	
End Sub

' --------------------------------------------------
' --
' Viewchange Drillinghead
' -- nur Ebenen - Wechsel ohne Verfahrbewegung
' --------------------------------------------------
Sub wcncViewChange_DH(dh As tdh,View,LastView,ByVal IPX,IPY,IPZ,RotA,TipA,ByVal SPVX,SPVY,SPVZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
	Dim r As Integer
	
    wcncCom("Viewchange DH View "+View)
	

	wcnc("TRANS")
	'wcnc("C_FRAME_SAVE")
	If Marker.Messbezug Then
		r= Marker.WP_ActIndex * 100
		'Ftos(WPI(Marker.WP_ActIndex).xMessPunkte(MessPunkt.Mess_Nr-3).Ym
		wcnc(OffPX+"=("+FToS(0)+")+("+FToS(Marker.FaktorX)+")*(R"+IntToS(r+Marker.MessbezugX)+")")
		wcnc(OffPY+"=("+FToS(0)+")+("+FToS(Marker.FaktorY)+")*(R"+IntToS(r+Marker.MessbezugY)+")")
		wcnc(OffPZ+"=("+FToS(0)+")+("+FToS(Marker.FaktorZ)+")*(R"+IntToS(r+Marker.MessbezugZ)+")")
		
'		wcnc("ATRANS"+XEqualToS(IPX)+Get_Val_Signed(-dh.CenterX)+"+"+OffPX+" "+YEqualToS(IPY)+Get_Val_Signed(-dh.CenterY)+"+"+OffPY+" "+ _
'	              ZEqualToS(IPZ)+Get_Val_Signed(-dh.CenterZ)+"+"+OffPZ)
	' MW 06.07.2016 AggOffsets werden von Engine bereits in die Ebene gerechnet (bei Einstellung Kopfdaten berechnen)
		
		wcnc("ATRANS"+XEqualToS(IPX)+Get_Val_Signed(0)+"+"+OffPX+" "+YEqualToS(IPY)+Get_Val_Signed(0)+"+"+OffPY+" "+ _
	              ZEqualToS(IPZ)+Get_Val_Signed(0)+"+"+OffPZ)
	Else
'		wcnc("ATRANS"+XEqualToS(IPX)+Get_Val_Signed(-dh.CenterX)+YEqualToS(IPY)+Get_Val_Signed(-dh.CenterY)+ _
'	              ZEqualToS(IPZ)+Get_Val_Signed(-dh.CenterZ))
	              
	' MW 06.07.2016 AggOffsets werden von Engine bereits in die Ebene gerechnet (bei Einstellung Kopfdaten berechnen)
		wcnc("ATRANS"+XEqualToS(IPX)+Get_Val_Signed(0)+YEqualToS(IPY)+Get_Val_Signed(0)+ _
	              ZEqualToS(IPZ)+Get_Val_Signed(0))
	              
	End If
	

	wcnc("AROT "+ZToS(RotA)+" "+XToS(TipA))
	'wcnc("C_FRAME_SAVE")

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

'get move string with x,y,z,feedrate,trc parameter
Function Move(ByVal x,ByVal Y,ByVal Z,Feedrate,TRC)

   Dim chars As String
   Dim checked_feedrate As Double
   
   
   chars=""

   
   ' Neu MW 20.04.2005
   ' check Vorschub 
   If Feedrate>0 Then
	   checked_feedrate = MT_CheckFeedrate(actt,x,Y,Z,LastPos.X,LastPos.Y,LastPos.Z,Feedrate)
	End If
      
   If (MovePara.TRC<>TRC)  Then
     chars= chars + GetTRCStr(TRC)
   End If
   If Marker.CPREC=1 Then
		chars= chars + " CPRECON"
		Marker.CPREC=2
   ElseIf Marker.CPREC=11 Then
		chars= chars + " FFWON"
		Marker.CPREC=12
   End If
   If Marker.CPREC=3 Then
		chars= chars + " CPRECOF"
		Marker.CPREC=0
   ElseIf Marker.CPREC=13 Then
		chars= chars + " FFWOF"
		Marker.CPREC=0
   End If
   If Not equal(x,LastPos.X) Then
      chars= chars + XToS(x)
   End If
   If Not equal(Y,LastPos.Y) Then
      chars= chars +  YToS(Y)
   End If
   If Not equal(Z,LastPos.Z) Then
      chars= chars + ZToS(Z)
   End If

   If (MovePara.Feedrate<>checked_feedrate) And (checked_feedrate>0) Then
     chars= chars + GetFeedrateStr(checked_feedrate)
   End If
   Call PosSet(LastPos,x,Y,Z)
   Call MoveParaSet(checked_feedrate,TRC)
   Move=chars
End Function

'get move string with x,y,z,feedrate,trc parameter
Function MoveOhneZ(ByVal x,ByVal Y,ByVal Z,Feedrate,TRC)

   Dim chars As String
   Dim checked_feedrate As Double
   
   
   chars=""

   
   ' Neu MW 20.04.2005
   ' check Vorschub 
   If Feedrate>0 Then
	   checked_feedrate = MT_CheckFeedrate(actt,x,Y,Z,LastPos.X,LastPos.Y,LastPos.Z,Feedrate)
	End If
   
   
   If (MovePara.TRC<>TRC)  Then
     chars= chars + GetTRCStr(TRC)
   End If
   If Not equal(x,LastPos.X) Then
      chars= chars + XToS(x)
   End If
   If Not equal(Y,LastPos.Y) Then
      chars= chars +  YToS(Y)
   End If
   If Not equal(Z,LastPos.Z) Then
      'chars= chars + ZToS(Z)
   End If

   
   If (MovePara.Feedrate<>checked_feedrate) And (checked_feedrate>0) Then
     chars= chars + GetFeedrateStr(checked_feedrate)
   End If
   Call PosSet(LastPos,x,Y,Z)
   Call MoveParaSet(checked_feedrate,TRC)
   MoveOhneZ=chars
End Function

Function Move5(ByVal x,ByVal Y,ByVal Z,ByVal RotA,ByVal TipA,Feedrate,TRC)
Dim chars As String
Dim checked_feedrate As Double
Dim BCI_Mode As Integer ' Modified  MW 27.04.2007 damit werden kleine A/C-Achs Änderungen ohne X/Y/Z - Änderung unterdrückt
   
   
   chars=""

   
   ' Neu MW 20.04.2005
   ' check Vorschub 
   If Feedrate>0 Then
	   checked_feedrate = MT_CheckFeedrate(actt,x,Y,Z,LastPos.X,LastPos.Y,LastPos.Z,Feedrate)
	End If
   
   
   If (MovePara.TRC<>TRC)  Then
     chars= chars + GetTRCStr(TRC)
   End If
   If Marker.CPREC=1 Then
		chars= chars + " CPRECON"
		Marker.CPREC=2
   ElseIf Marker.CPREC=11 Then
		chars= chars + " FFWON"
		Marker.CPREC=12
   End If
   If Marker.CPREC=3 Then
		chars= chars + " CPRECOF"
		Marker.CPREC=0
   ElseIf Marker.CPREC=13 Then
		chars= chars + " FFWOF"
		Marker.CPREC=0
   End If
   If (Not equal(x,LastPos.X)) Or (Not equal(Z,LastPos.Z)) Then
      chars= chars + XToS(x)
   End If
   If (Not equal(Y,LastPos.Y)) Or (Not equal(Z,LastPos.Z)) Then
      chars= chars +  YToS(Y)
   End If
   If Not equal(Z,LastPos.Z) Then
      chars= chars + ZToS(Z)
   End If

   
   If (MovePara.Feedrate<>checked_feedrate) And (checked_feedrate>0) Then
     chars= chars + GetFeedrateStr(checked_feedrate)
   End If
   
   Call PosSet(LastPos,x,Y,Z)
   Call MoveParaSet(checked_feedrate,TRC)

   Move5=chars
End Function

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
   
   Marker.viewchangechecked = True
   
End Sub

'Const SepStr=";"

'delete from index to index+count all chars
'Function delete(S,index,Count)
'Dim	ns As String
'Dim n As  Integer
'Dim indexpluscount As Integer
'  ns=""
''  indexpluscount=index+Count-1
'  For n= 1 To Len(S) Step 1
'     If Not ((n>=index) And  (n<=indexpluscount)) Then
'       ns=ns+Mid(S,n,1)
'     End If
'  Next n
'  delete=ns
'End Function


'count of parameters in the string
'Function ParamCount(S)
'Dim	n As Integer
'Dim Count As Integer
' ParamCount=0
'  Count = 0
'  S= Trim(S)
'  If Len(S) > 0 Then
'     For n= 1 To Len(S) Step 1
'        If Mid(S,n,1) = SepStr Then
'           Count = Count + 1
'        End If
'     Next n
'     ParamCount = Count + 1
'  End If
'End Function



'pick the parameter at position 'nr' of the string 'S'
Function ParamSep(NR,S,Sep)
Dim	Count As Integer
Dim n As Integer
Dim p As Integer
Dim SSave As String
  Count = ParamCountSep(S,Sep)

  If (NR > Count) Or (NR < 1)Then
     ParamSep = ""
     Exit Function
  End If

If Count = 1 Then
     ParamSep = Trim(S)
     Exit Function
  End If

  If NR = 1 Then
     p= InStr(S,Sep)

     ParamSep = Trim (Mid(S, 1, p-1))

  ElseIf NR < Count Then
     SSave=S 
     For n = 1 To NR-1 Step 1
        SSave=delete(SSave,1,InStr(SSave,Sep))
     Next n

     p= InStr(SSave,Sep)
     ParamSep = Trim(Mid (SSave,1, p-1))

  ElseIf NR = Count Then 
     p = InStrRev(S,Sep)
     ParamSep = Trim(Mid (S, p+1, Len(S)-p))

  End If
End Function


'count of parameters in the string
Function ParamCountSep(S,Sep)
Dim	n As Integer
Dim Count As Integer
 ParamCountSep=0
  Count = 0
  S= Trim(S)
  If Len(S) > 0 Then
     For n= 1 To Len(S) Step 1
        If Mid(S,n,1) = Sep Then
           Count = Count + 1
        End If
     Next n
     ParamCountSep = Count + 1
  End If
End Function


'pick the parameter at position 'nr' of the string 'S'


'Function Param(nr,S)
'Dim	Count As Integer
'Dim n As Integer
'Dim p As Integer
'Dim SSave As String
'  Count = ParamCount(S)
'
'  If (nr > Count) Or (nr < 1)Then
'     Param = ""
'     Exit Function
'  End If

'If Count = 1 Then
'     Param = Trim(S)
'     Exit Function
'  End If

'  If nr = 1 Then
'     p= InStr(S,SepStr)
'
'     Param = Trim (Mid(S, 1, p-1))
'
'  ElseIf nr < Count Then
'     SSave=S 
'     For n = 1 To nr-1 Step 1
'        SSave=delete(SSave,1,InStr(SSave,SepStr))
'     Next n

'     p= InStr(SSave,SepStr)
'     Param = Trim(Mid (SSave,1, p-1))

'  ElseIf nr = Count Then 
'     p = InStrRev(S,SepStr)
'     Param = Trim(Mid (S, p+1, Len(S)-p))

'  End If
'End Function


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

Sub PosSet(varpos,X,y,z)
  varpos.X=X
  varpos.Y=y
  varpos.Z=z
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
Function G9
	If DrillingWithG9 Then
  		G9="G1 G9"
  	Else
  		G9="G1"
  	End If
End Function
Function XToS(x)
  XToS=" X"+FToS(x)
End Function

Function YToS(Y)
  YToS=" Y"+FToS(Y)
End Function

Function ZToS(Z)
  ZToS=" Z="+FToS(Z)
End Function

Function XEqualToS(X)
  XEqualToS=" X="+FToS(X)
End Function

Function YEqualToS(Y)
  YEqualToS=" Y="+FToS(Y)
End Function

Function ZEqualToS(Z)
  ZEqualToS=" Z="+FToS(Z)
End Function

Function QXToS(X)
  QXToS=" QX="+FToS(X)
End Function

Function QYToS(Y)
  QYToS=" QY="+FToS(Y)
End Function

Function QZToS(Z)
  QZToS=" QZ="+FToS(Z)
End Function

Function IToS(I)
  IToS=" I"+FToS(I)
End Function

Function JToS(J)
  JToS=" J"+FToS(J)
End Function

Function RotDC_Axis_ToS(I)
Dim AxName As String

	'If actT.PH_Add.RotAxisName = "" Then
		' z.B. wenn Rückzug mit Bohrkopf 
		' dann von 1. Spindel die Achsnamen holen
 	'	AxName = TDATA.GetProcessHead_ID(1).Additions.GetAddition_ID(10011).Value
		 		
	'Else
	'	AxName = actT.PH_Add.RotAxisName
	'End If
  'RotDC_Axis_ToS=" "+AxName+"=DC("+FToS(I)+")"
  	'AddMistake("Check Function")
End Function
Function GetActHeadKartanAng() As Double
	GetActHeadKartanAng=-9999
	If Not TDATA.GetProcessHead_ID(Actt.hid).Additions.GetAddition_ID(10200) Is Nothing Then
		GetActHeadKartanAng=CDbl(TDATA.GetProcessHead_ID(Actt.hid).Additions.GetAddition_ID(10200).Value)
	Else
		AddMistake("Define KartanAng(ID:10200) for Head: "+IntToS(CInt(Actt.hid)))
	End If
	
End Function


Function Rot_Axis_ToS(I)

Dim AxName As String
	
	'If actT.PH_Add.RotAxisName = "" Then
		' z.B. wenn Rückzug mit Bohrkopf 
		' dann von 1. Spindel die Achsnamen holen
 	'	AxName = TDATA.GetProcessHead_ID(1).Additions.GetAddition_ID(10011).Value
		 		
	'Else
	'	AxName = actT.PH_Add.RotAxisName
	'End If

  'Rot_Axis_ToS=DEF_Rot_Axis_Name+"="+FToS(i)
  
  'Rot_Axis_ToS=AxName+"="+FToS(I)
   'AddMistake("Check Function")

End Function


Function Tip_Axis_ToS(j)
Dim AxName As String

  ' Tip_Axis_ToS=DEF_Tip_Axis_Name+"="+FToS(j)
  
	'If actT.PH_Add.TipAxisName = "" Then
		' z.B. wenn Rückzug mit Bohrkopf 
		' dann von 1. Spindel die Achsnamen holen
 	'	AxName = TDATA.GetProcessHead_ID(1).Additions.GetAddition_ID(10010).Value
		 		
	'Else
	'	AxName = actT.PH_Add.TipAxisName
	'End If
  
  'Tip_Axis_ToS=AxName+"="+FToS(J)
End Function

Public Function C_Inc(RotA)
	If Not equal(RotA,0) Then
		' nur wenn nicht 0 - macht keinen Sinn	
		C_Inc = " AX[CAX]=IC(" +FToS(RotA)+")"
	Else
		C_Inc = " "
	End If
End Function

Public Function B_Inc(TipA)
	If Not equal(TipA,0) Then
		' nur wenn nicht 0 - macht keinen Sinn	
		B_Inc = " AX[BAX]=IC(" +FToS(TipA)+")"
	Else
		B_Inc = " "
	End If
End Function



   
Public Function GetHeadAnglesRot(RotA)
Dim RotA_ As Double
   
   RotA_=RotA 
   ' Drehsinn berücksichtigen - Einstellung über AScript
   RotA_ = RotA_  * (-1)  'DEF_Direction_RotationAxis
   ' ToCheck OS/MW  -> muss eigentlich aus MT-Manager gelesen werden
   
   While RotA_ > ActT.H.RotMax   
       RotA_ = RotA_ - 360
   Wend
   
   While RotA_ < ActT.H.RotMin
       RotA_ = RotA_ + 360
   Wend
   
	If (RotA_ < ActT.H.RotMin) Or (RotA_ > ActT.H.RotMax) Then
		AddMistake(GetErrMsg(107,"_Drehwinkel außerhalb Drehbereich der Drehachse",1))
	End If

   GetHeadAnglesRot=RotDC_Axis_ToS(RotA_)
   

	
End Function

Public Function GetHeadAnglesRot_HorPT(RotA)
Dim RotA_ As Double
   
   RotA_=RotA 
   ' Drehsinn berücksichtigen - Einstellung über AScript
   RotA_ = RotA_  * (-1)  '* DEF_Direction_RotationAxis
   ' ToCheck OS/MW  -> muss eigentlich aus MT-Manager gelesen werden
   
   While RotA_ > ActT.H.RotMax   
       RotA_ = RotA_ - 360
   Wend
   
   While RotA_ < ActT.H.RotMin
       RotA_ = RotA_ + 360
   Wend
   
	If (RotA_ < ActT.H.RotMin) Or (RotA_ > ActT.H.RotMax) Then
		AddMistake(GetErrMsg(107,"_Drehwinkel außerhalb Drehbereich der Drehachse",1))
	End If

   GetHeadAnglesRot_HorPT=Rot_Axis_ToS(RotA_)
   

	
End Function

Public Function GetHeadAngles_GB(RotA)
Dim RotA_ As Double
	'RotA_=RotA + MT_Get_RotOffGB(ActT.t) + MT_Get_RotOffGB_TP(ActT.t)  ' offsetc additional
	
	' Neu MW 08.11.2005 
	' reine mathematische ermittlung
	RotA_ = GetHeadAnglesMath_GB(RotA)
	
	' Neu MW 2.11.2005
	' für Winkelgetriebe auf fixer Hauptspindel keine C-Achs - Ausgabe
	If (MT_Is_Vertical_Rot_Axis(ActT)) And (MT_IsGearBoxTool(ActT) Or MT_IsGearBoxTool_5thAxis(actt) Or MT_IsGearBoxTool_Special(actt) ) Then
	   'GetHeadAngles_GB=RotDC_Axis_ToS(RotA_)
	   ' MW 24.10.2007 keine Rundachse
	   GetHeadAngles_GB=" "+Rot_Axis_ToS(RotA_)
	Else
	   GetHeadAngles_GB=""
	
	End If
   
End Function
Public Function GetHeadAnglesCAxis_GB(RotA)
Dim RotA_ As Double
	'RotA_=RotA + MT_Get_RotOffGB(ActT.t) + MT_Get_RotOffGB_TP(ActT.t)  ' offsetc additional
	
	' Neu MW 08.11.2005 
	' reine mathematische ermittlung
	RotA_ = RotA
	
	' Neu MW 2.11.2005
	' für Winkelgetriebe auf fixer Hauptspindel keine C-Achs - Ausgabe
	If (MT_Is_Vertical_Rot_Axis(ActT)) And (MT_IsGearBoxTool(ActT) Or MT_IsGearBoxTool_5thAxis(actt) Or MT_IsGearBoxTool_Special(actt) ) Then
	   'GetHeadAngles_GB=RotDC_Axis_ToS(RotA_)
	   ' MW 24.10.2007 keine Rundachse
	   GetHeadAnglesCAxis_GB=" "+Rot_Axis_ToS(RotA_)
	Else
	   GetHeadAnglesCAxis_GB=""
	
	End If
   
End Function
Public Function GetHeadAnglesMath_GB(RotA) As Double
' ermittelt die C-Achsposition
Dim RotA_ As Double

	' Drehsinn berücksichtigen - Einstellung über AScript
	RotA_ = RotA  * (-1)  ' DEF_Direction_RotationAxis
   ' ToCheck OS/MW  -> muss eigentlich aus MT-Manager gelesen werden
	
	RotA_ = RotA_ 
	
	
	RotA_= RotA_ + MT_Get_RotAxisOffset(actt)  ' offsetc additional Winkelgetriebe offset + ausgang offset
	
	MT_C_AxisNorm(RotA_)
	
	If (RotA_ < ActT.H.RotMin) Or (RotA_ > ActT.H.RotMax) Then
		AddMistake(GetErrMsg(107,"_Drehwinkel außerhalb Drehbereich der Drehachse",1))
	End If

	GetHeadAnglesMath_GB = RotA_
End Function



Function MT_C_AxisNorm(axis)
   While axis > ActT.H.RotMax   
       axis = axis - 360
   Wend
   
   While axis < ActT.H.RotMin
       axis = axis + 360
   Wend
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
  GetSpeedStr=IntToS(Abs(Round(speed)))
  If speed<0 Then
    GetSpeedStr=GetSpeedStr
  Else
    GetSpeedStr=GetSpeedStr
  End If
End Function

Sub WriteSpeed(speed)
Dim SpeedStr As String
  SpeedStr=IntToS(Abs(Round(speed)))
  If speed<0 Then
    wcnc("DRR=4")
  Else
    wcnc("DRR=3")
  End If
  wcnc("DRZ="+SpeedStr)
End Sub


'compare the last and actual view if equal -> true
Function ViewEqual
  ViewEqual=equal(LastV.View,ActV.View) _
                And equal(LastV.IPX,ActV.IPX) And equal(LastV.IPY,ActV.IPY)  And equal(LastV.IPZ,ActV.IPZ) _
                And equal(LastV.TipA,ActV.TipA)  And equal(LastV.RotA,ActV.RotA)


	If Haube.P3AchsRetreat=True Then
		ViewEqual=False
	End If

End Function


Function FToS(w)
  Dim n As Integer
  Dim FToSSave As String
  Dim erg As String
  Dim anz As Long
  
  anz=0
  erg=""
  'FToSSave = Format$(W,FloatFormat)
  erg = Replace$(Format$(w,FloatFormat),",",".")
'  For n=1 To Len(FToSSave) Step 1
'	If Mid(FToSSave,n,1)="," Then
'  	    erg=erg+"."
'  	Else
'       erg=erg+Mid(FToSSave,n,1) 	
'  	End If
'  Next n
	
  ' -- 
  ' Neu 08.11.2004 MW 
  ' -- nachfolgende Nullen z.B. bei 34.100 werden gelöscht = 34.1
  ' -- dadurch bei Dokus etc. kurzere Zeilenlängen und weniger NC-Code
  ' -- 
  ' -- 
  For n=Len(erg) To 1 Step -1
	If (Mid(erg,n,1)=".") Or (Mid(erg,n,1)<>"0") Then
		Exit For
  	Else
       If Mid(erg,n,1)="0" Then
       		anz = anz + 1   ' diese können gelöscht werden
       End If
  	End If
  Next n
  If anz > 0 Then
	  erg = Mid(erg,1,Len(erg)-anz)
  End If
  If erg="" Then
  	'AddHint("schwerwiegender Fehler")
Else
  If Mid(erg,Len(erg),1)="." Then
  	 ' punkt löschen
  	 erg=Mid(erg,1,Len(erg)-1)
  End If

  End If
  FToS=erg
End Function

Function IntToS(w)
  IntToS= Trim(Str(w))
End Function

Function XYZToS(x,Y,Z)
  XYZToS=XToS(x)+YToS(Y)+ZToS(Z)
End Function

Function QXQYQZToS(x,Y,Z)
  QXQYQZToS=QXToS(x)+QYToS(Y)+QZToS(Z)
End Function

Function QXQYToS(x,Y)
  QXQYToS=QXToS(x)+QYToS(Y)
End Function

Function XYToS(x,Y)
  XYToS=XToS(x)+YToS(y)
End Function

Function ZXToS(z,x)
  ZXToS=ZToS(z)+XToS(x)
End Function

Function IJToS(I,j,r)
IJToS= " CR="+FToS(r)
  'IJToS=IToS(I)+JToS(j)+StrToCom(" Radius: "+FToS(r))
End Function

'Function equal(W1,W2)
'  equal= Abs(W1-W2)<0.00001
'End Function

'Function equal_t(W1,W2,T)
'  equal_t= Abs(W1-W2)<T
'End Function


'Reset the actual view
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

'If NCLine=700 Then Stop
' NCLine = 0
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
	    NCLine=NCLine + JobPara.lstp
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

	If (Len(ncs)>0) And (ncs<>"G1") Then
		' keine leere G1 Zeilen ausgeben 5-Axis interpol.
		' keine Leerzeilen ausgeben
	    'Print #1,"N";Trim(Str(NCLine));" ";ncs
	    ncstr = ncs
		FWriteln(NCFileNo,ncstr)
	End If
End Sub


'write safety absolut
Sub wSafetyAbs(Safety)
	' for all aggregats at the moment
	If Not Safety Then
		wcncCom("Go Safety")
		'wcnc("TRAFOOF")
		' G153 fährt absolut ohne traori
		If MT_Is_Vertical_StandardTool5Axis(actt) Then
			wcnc("TRANS")
			'wcnc("C_FRAME_SAVE")
			wcnc("G90 D0")
			wcnc("G153 G0 Z="+MAX_LIMIT_ZPLUS)
		Else
			wcnc("TRANS")
			'wcnc("C_FRAME_SAVE")
			wcnc("G90 D0")

			wcnc("G153 G0 Z="+MAX_LIMIT_ZPLUS)
		End If
	End If
	
	'ResetActV
	Safety=True
End Sub

'write safety above the part safety included
Sub wSafetyPart(Optional DMove As Integer )
Dim dz_off As Double    ' offset für Winkelgetriebe wenn für die Anfahrt die höhere Stellung benutzt
                        ' werden muss, da sonst Z+ Endlage
Dim SawRadius As Double
Dim DNum_Dh As Long
Dim SafeZ,DiffZ As Double     ' Aufgrund Abfahren ohne Z-Sicherheit
Dim Z_Safe As String
' wSafetyAbs
' Exit Sub
'  wcnc("********************************** 1")	
	If IsEmpty(DMove) Then
		DMove=-1
	End If


' MW 12.3.2004 muss gehen bei 4-Achs
' geht nicht, da bei folgender hor. Ebene 
' der KAK auf Kollission mit WKS fährt

	
	If Not Z_Is_SafetyPart Then
	'If Not Z_Is_Safety	Then

		If Not MT_isDH(ActT ) Then
			If (Marker.LiftPos_Startup<>Marker.LiftPos_Processing) And (Marker.LiftPos_Startup>0) And (Marker.LiftPos_Processing>0)  Then
				dz_off= (ActT.H.LiftOffsets.GetLiftOffset_ID(Marker.LiftPos_Processing).OffsetZ) - (ActT.H.LiftOffsets.GetLiftOffset_ID(Marker.LiftPos_StartUp).OffsetZ)
			End If
		Else
			dz_off = 0
		End If
		AddLog("Fahrt auf Sicherheit übers Werkstück hat stattgefunden:"+IntToS(NCLine))
		

       wcncCom("Sicherheit übers Werkstück!")
       wcnc("TRANS")
	   'wcnc("C_FRAME_SAVE")
       ' geändert MW 13.04.2005
       'wcncAddCom("G0 D"+IntToS(ActT.T.CorrNo)+ZToS(FinishedPart.Z+ActT.T.GetSecurityZ(0)+dz_off) +"+"+OffPZ ," absolut: Z:"+FToS(FinishedPart.Z+ActT.T.GetSecurityZ(0)))
		' Neu MW 15.09.2005 * zusätzlichen Sicherheitsabstand einrechnen
	    wcncCom("Additives ZMass:"+FToS(GetAddZSic))
	    
	    If MarkerSawing.LastIsSawing=True Then
	    	SawRadius = actt.t.Radius
	    Else
	    	SawRadius = 0
	    End If

        DiffZ=MT_Get_Sic_Diff_Saw_Router(actT,ActV.TipA)

       
       'wcncAddCom("G0 D"+IntToS(ActT.T.CorrNo)+ZToS(FinishedPart.Z+ActT.T.GetSecurityZ(ActV.TipA)+dz_off) +"+"+OffPZ ," absolut: Z:"+FToS(FinishedPart.Z+ActT.T.GetSecurityZ(0)))
	   'wcncAddCom("G0 D"+IntToS(ActT.T.CorrNo)+ZToS(FinishedPart.Z+ActT.T.GetSecurityZ(ActV.TipA)+dz_off+GetAddZSic+SawRadius) +"+"+OffPZ ," absolut: Z:"+FToS(FinishedPart.Z+ActT.T.GetSecurityZ(0)))
	   ' Achtung MW 09.03.2006 hier muss auch die Correktur-Nummer aus Spezial - Einstellungen genommen werden
	   If MT_IsDH(actT) Or MT_IsDHSaw(actT) Then
	   		' Neu MW 22.06.2006
	   		' Für Bohrkopf gilt andere Logik der D-Korrektur
	   	   DNum_Dh = MT_Get_DNum_DrillingHead(ActT)
		   wcncAddCom("G0 D"+IntToS(DNum_Dh)+ZToS(FinishedPart.Z+ActT.T.GetSecurityZ(ActV.TipA)+dz_off+GetAddZSic+SawRadius) +"+"+OffPZ ," absolut: Z:"+FToS(FinishedPart.Z+ActT.T.GetSecurityZ(0)))
	   Else
	   		' NEU MW 29.10.2012 - Abfahren ohne Z-Sicherheit - hier wird geprüft, ob die Sicherheit mindestens dem werkzeugabhängigen entspricht
			SafeZ = FinishedPart.Z+ActT.T.GetSecurityZ(ActV.TipA)+dz_off+GetAddZSic+SawRadius
   			
	   		If (DMove=6) Then
	   			If (LastPosAbs.Z) > (SafeZ) Then 
	   				' MW 26.02.2013 über LastposAbs.z 
	   				'If (LastPos.Z+ActV.IPZ) > (SafeZ) Then
	   				' Die vom Vektorfräsen/Fräsen kommende Z-Position ist OK! -> mindestens so hoch  
				   'SafeZ= (LastPos.Z+ActV.IPZ) 
				   wcnc(StrToCom("ohne Z aktiv - > (LastPosZ > Sic Z)"))
				   SafeZ= LastPosAbs.Z
				End If
			End If
		    If MT_Is_Vertical_StandardTool5Axis(actt) Then	   
				
				
			Else
				wcncAddCom("G0 D"+IntToS(ActT.H_Add.CorrNo)+ZToS(SafeZ+DiffZ) +"+"+OffPZ ," last Z("+FToS(LastPosAbs.Z)+ ") Sic Z("+FToS(FinishedPart.Z+ActT.T.GetSecurityZ(ActV.TipA)+dz_off+GetAddZSic+SawRadius+DiffZ)+ ")" +" FZ:("+ FToS(FinishedPart.Z) +")" +" SIC:("+ FToS(ActT.T.GetSecurityZ(0)) +")")
			End If
			
	  	End If
       
	   If MT_Is_Vertical_StandardTool5Axis(actt) And Not MarkerSawing.LastIsSawing Then
			' 5-Achs 
			'wcnc("G153 G0 "+ActT.PH_Add.TipAxisName+"=0 "+ ActT.PH_Add.RotAxisName+"=0")
			' MW 23.04.2007 - ohne C-Achse zurueckschwenken

	   End If
    End If
	Z_Is_SafetyPart=True
       
'       wcnc("SUPA "+GetHeadAngles5Achs(0,0))
'       wcnc("STOPRE")
'  wcnc("********************************** 2")
End Sub



'write NCstart
Sub NCStart
Dim vers As Variant
Dim ZPos As Double 
	wcnc("DEF REAL h_LAENGE= "+FToS(FinishedPart.X))
	wcnc("DEF REAL h_BREITE= "+FToS(FinishedPart.Y))
	wcnc("DEF REAL h_DICKE= "+FToS(FinishedPart.Z))
	wcncAddCom("DEF REAL "+OffPX+"=0","Output offset X")
	wcncAddCom("DEF REAL "+OffPY+"=0","Output offset Y")
	wcncAddCom("DEF REAL "+OffPZ+"=0","Output offset Z")
	wcnc("DEF REAL DOOX=0")
	wcnc("DEF REAL DOOY=0")
	wcnc("DEF REAL DOOZ=0")
	wcnc("DEF REAL DDL=0")
	wcnc("DEF REAL PIH=3.1415926536")
  'wcnc("M51")
	wcnc("DEF REAL "+MAX_LIMIT_ZPLUS+"=0")
	wcnc("DEF REAL "+MAX_LIMIT_XPLUS+"=0")
	wcnc("DEF REAL "+MAX_LIMIT_XMINUS+"=0")
	wcnc("DEF REAL "+MAX_LIMIT_YPLUS+"=0")
	wcnc("DEF REAL "+MAX_LIMIT_YMINUS+"=0")
	
	wcnc("DEF REAL PX=0")
	wcnc("DEF REAL PY=0")
	wcnc("DEF INT "+DCORRECTIONMARKER+"=0")
	
	If Lage.V_MESS=1 Or Lage.V_MESS=2 Then
		wcnc("DEF INT V_MESS_LOK="+IntToS(0))
		wcnc("DEF INT V_WKZ_NR_LOK="+IntToS(0))
		wcnc("DEF INT V_ANSCHLAGART_LOK="+IntToS(0))
		wcnc("DEF REAL V_MESSPOS_X1_LOK="+FToS(0))
		wcnc("DEF REAL V_MESSPOS_X2_LOK="+FToS(0))
		wcnc("DEF REAL V_MESSPOS_Y1_LOK="+FToS(0))
		wcnc("DEF REAL V_MESSPOS_Z1_LOK="+FToS(0))
		wcnc("DEF REAL V_MESSPOS_ZX_LOK="+FToS(0))
		wcnc("DEF REAL V_MESSPOS_ZY_LOK="+FToS(0))
		wcnc("STOPRE")
		wcnc("V_MESS_LOK="+IntToS(Lage.V_MESS))
		If Firstt.t.CuttingEdge.ID=Lage.V_WKZ_NR Then
			wcnc("V_WKZ_NR_LOK="+IntToS(Firstt.t.GetPlaceID_OnTC))
		Else
		
			AddMistake("Wrong toolno for meassure Tool")
		End If
		
		wcnc("V_ANSCHLAGART_LOK="+IntToS(Lage.V_ANSCHLAGART))
		wcnc("V_MESSPOS_X1_LOK="+FToS(Lage.V_MESSPOS_X1))
		wcnc("V_MESSPOS_X2_LOK="+FToS(Lage.V_MESSPOS_X2))
		wcnc("V_MESSPOS_Y1_LOK="+FToS(Lage.V_MESSPOS_Y1))
		wcnc("V_MESSPOS_Z1_LOK="+FToS(Lage.V_MESSPOS_Z1))
		wcnc("V_MESSPOS_ZX_LOK="+FToS(Lage.V_MESSPOS_ZX))
		wcnc("V_MESSPOS_ZY_LOK="+FToS(Lage.V_MESSPOS_ZY))
	Else
		wcnc("STOPRE")
	End If
	

	
	'Maschine mit 2 unabhängig zu schreibenden Z-Achsen
	'-------------------------------------------------------------------
	'wcnc("IF ($MA_POS_LIMIT_PLUS[Z1]-0.5)>($MA_POS_LIMIT_PLUS[Z1]-0.5)")
	'	wcnc(MAX_LIMIT_ZPLUS+"=$MA_POS_LIMIT_PLUS[Z2]-0.5")
	'wcnc("ELSE")
	'	wcnc(MAX_LIMIT_ZPLUS+"=$MA_POS_LIMIT_PLUS[Z1]-0.5")
	'wcnc("ENDIF")
	
	'Maschine mit einer unabhängigen Z-Achse
	'-------------------------------------------------------------------
	wcnc(MAX_LIMIT_ZPLUS+"=$MA_POS_LIMIT_PLUS[Z]-0.5")
	
	'Maschine mit einer unabhängigen X-Achse
	'-------------------------------------------------------------------
	wcnc(MAX_LIMIT_XPLUS+"=$MA_POS_LIMIT_PLUS[X]-0.5")
	wcnc(MAX_LIMIT_XMINUS+"=$MA_POS_LIMIT_MINUS[X]+1")
	
	
	'Maschine mit 2 unabhängig zu schreibenden Y-Achsen
	'-------------------------------------------------------------------
	'wcnc("If $MA_POS_LIMIT_PLUS[Y]>$MA_POS_LIMIT_PLUS2[Y]")
	
	'wcnc("ELSE")
	'	wcnc("   "+MAX_LIMIT_YPLUS+"=$MA_POS_LIMIT_PLUS[Y]-500")
	'wcnc("ENDIF")
	
	'Maschine mit 1 unabhängig zu schreibenden Y-Achse
	'-------------------------------------------------------------------
	wcnc(MAX_LIMIT_YPLUS+"=$MA_POS_LIMIT_PLUS[Y]-300")
	wcnc(MAX_LIMIT_YMINUS+"=$MA_POS_LIMIT_MINUS[Y]+1")
	wcnc("STOPRE")
	
	If JobPara.activ_fields=1 Then
'		wcnc("M51")
	ElseIf JobPara.activ_fields=2 Then
'		wcnc("M52")
	ElseIf JobPara.activ_fields=3 Then
'		wcnc("M51")
'		wcnc("M52")
	Else	
		AddMistake(GetErrMsg(234107,"_activ fields ?",1))
	End If
	
	
	WKS_GetTabeleFuctions

	'1=Atotomatisch
	'2=Traverse mit anzeige
	If GTableType=1 Or GTableType=2 Then
		If is_WorkC_OptionBit(CleanTable ,JobPara.WorkC_OptionBit) Then
			If is_WorkC_OptionBit(TurnCleanDirection ,JobPara.WorkC_OptionBit) Then
				wcnc("C_REINIGEN_RECHTS")
			Else
				wcnc("C_REINIGEN_LINKS")
			End If
		
		End If
			'Call WCNC_VORWECHSEL()
			Call wcncMachineComponentData(0)
		End If

	'NestingModus
	If is_WorkC_OptionBit(IsNestingMode,JobPara.WorkC_OptionBit) Then	
		WKS_SpannenNesting(False)
	Else
		WKS_Spannen
	End If 




  
	
	wcncCom("created:"+Str$(Date)+" - "+Str$(Time))
	' MW 14.04.2007
	GetVersion5(vers)
	wcncCom("WZ:"+TDATA.ActMachineName)
	wcncCom("Post:"+TDATA.MachineData.MachineParameter.PostProzessor+" V"+vers+" Script"+SCRIPT_VERSION)
	

	
	If CountOfTool>0 Then
		' Neu MW 04.07.2005 damit auch ohne Bearbeitungen ein NC-Prog erzeugbar
		MT_Write_TCheck
	End If

	wcnc("G500 G90 D0")
	wcnc("CUT2DF")
	wcnc("CFIN")
	
	wcnc("G153 G0 Z="+MAX_LIMIT_ZPLUS)
	'wcnc("G153 G0 Z2="+MAX_LIMIT_ZPLUS)
	
	'If (ActT.h.RotType=atFree) And (ActT.h.TipType=atFree) Then
		'Set ActT.h = TDATA.GetProcessHead_ID(1)
		' Vorsicht Werkzeug noch nicht bekannt !!!
		' geht nicht
		' 5-Achs 
		'wcnc("G153 G0 "+ActT.PH_Add.TipAxisName+"=0 "+ ActT.PH_Add.RotAxisName+"=0")
	'End If

	'wcncAddCom(SPF_StartProg," Maschine in 0-Stellung")

	'wcnc_EinlegeHilfen_Runter
	'Anschlaege_Runter
	'Vakuum_Ueberwachung_Ein
	
	'Alles_Zuruecklegen_undAus
	
	If Bahnverhalten<>1 Then
		wcnc("G64 G17 SOFT")
		wcnc("G451")
		
	Else
		wcnc("G451 G17")
	End If
	wcnc("ORIAXES")
	wcnc("ORIMKS")
	
	

	SET_Zero(True,WPI(0).WPName,TDATA.MachineData.OffsetX+JobPara.NPX,TDATA.MachineData.OffsetY+JobPara.NPY,TDATA.MachineData.OffsetZ+JobPara.NPZ,0,0,0,JobPara.MirrorX,JobPara.MirrorY)
	
	' --------------------------------------
	' Konturgenauigkeit eingestellen
	
	ContPrec_Einlesen
	
	'wcnc("$SC_MINFEED="+FToS(sc_minfeed))
	'wcnc("$SC_CONTPREC="+FToS(sc_contprec))
	wcnc("$SC_MINFEED="+FToS(2000))
	wcnc("$SC_CONTPREC="+FToS(0.05))
	' --------------------------------------
	MT_AllDrillHeadsUp
	If Marker.Messbezug=True Then
		wcnc("C_MESSEN_NULL(V_MESS_LOK, V_WKZ_NR_LOK, V_ANSCHLAGART_LOK, V_MESSPOS_X1_LOK, V_MESSPOS_X2_LOK, V_MESSPOS_Y1_LOK, V_MESSPOS_Z1_LOK, V_MESSPOS_ZX_LOK, V_MESSPOS_ZY_LOK, H_LAENGE, H_BREITE, H_DICKE)")
		    'C_MESSEN_NULL( V_MESS_LOK, V_WKZ_NR_LOK, V_ANSCHLAGART_LOK, V_MESSPOS_X1_LOK, V_MESSPOS_X2_LOK, V_MESSPOS_Y1_LOK, V_MESSPOS_Z1_LOK, V_MESSPOS_ZX_LOK, V_MESSPOS_ZY_LOK, H_LAENGE, H_BREITE, H_DICKE) 
	End If
	
	wcnc("STOPRE")
End Sub


'write nc header
Sub wcncHeader(NCName,TDB,FX,FY,FZ,Comment,Add_X,Add_Y,Add_Z)
Dim I As Long
Dim stri As Variant
Dim stri_merker As Variant
	
	wcncCom("FinishedPart: X: "+FToS(FX)+" Y: "+FToS(FY)+" Z: "+FToS(FZ))
	wcncCom("TData:"+TDB)
	wcncCom("POST FOR VISION/ARTIS 3-5Axis 05.02.2014")
	
	
	
	Call NCStart
	
	
End Sub

Sub NCEnd
'    All_Agg_UP_AND_Off
'     wcnc("IF R64==1 GOTOF ENDE1")
'     wcnc("G0"+XToS(4250))
'     wcnc("GOTOF ENDE")
'     wcnc("ENDE1:")
'     If InStr("G54",Nullpunkt)>0 Then
'        wcnc("G0 X=800 Y="+FToS(Finishedpart.y+1000))
'     End If
'     If InStr("G506",Nullpunkt)>0 Then
''        wcnc("G0"+" "+"X="+FToS(FinishedPart.x)+"+"+FToS(1500))
'     End If
     
'     If InStr("G56",Nullpunkt)>0 Then
'        wcnc("G0"+" "+"X="+FToS(-1500))
'     End If
'     If InStr("G57",Nullpunkt)>0 Then
'        wcnc("G0"+" "+"X="+FToS(-FinishedPart.x)+"-"+FToS(1500))
'     End If
     'wcnc("G0"+XToS(0))
     'wcnc("ENDE:")
'     Vakuum_Ueberwachung_Aus
'     wcnc_EinlegeHilfen_Hoch

'     Anschlaege_Hoch


	 wcnc("M30")

End Sub
'write nc end





' ------------------------------------------------------------------------------------------
' ------------------------------------------------------------------------------------------
' ------------------------------------------------------------------------------------------
' ------------------------------------------------------------------------------------------
' Funktionen für                  Aggregat - Gruppe 2   5-ACHS   
' ------------------------------------------------------------------------------------------
' ------------------------------------------------------------------------------------------
' ------------------------------------------------------------------------------------------
' ------------------------------------------------------------------------------------------

Function WerkzeugWechsel_5Achs_RANC_1(WerkzeugwechselModus,BoxNo,ToolNo,CorrNo,P_Speed,T_Speed)
Dim Drehzahl As Double
Dim richtung As Integer

  
		wcnc("")
		wcncCom("--- 5-Achs Werkzeugwechsel  ---")
		wcnc("")
		Drehzahl=Check_drehzahl(P_Speed,T_Speed)
		If Drehzahl < 0 Then 
		   richtung=4
		Else
		   richtung=3
		End If
		'Drehzahl=0
		If GSiemens840DType=1 Then
			wcncAddCom("C_TSL("+IntToS(ToolNo)+","+IntToS(Abs(Actt.t.MaxRotSpeed))+")","Set Speed limits for next Tool!")
		End If
		wcncAddCom(GToolChangeCycleName+"("+IntToS(ToolNo)+","+IntToS(richtung)+","+IntToS(Abs(Drehzahl))+")","")		
	    
End Function

Function WerkzeugWechsel_5Achs_RANC_2(WerkzeugwechselModus,BoxNo,ToolNo,CorrNo,P_Speed,T_Speed)
Dim Drehzahl As Double
Dim richtung As Integer

		If T_Speed>0 Then
			If GSiemens840DType=1 Then
				wcncAddCom("C_TSL("+IntToS(ToolNo)+","+IntToS(Abs(Actt.t.MaxRotSpeed))+")","Set Speed limits for next Tool!")
			End If
			wcnc(GToolChangeCycleName+"("+IntToS(ToolNo)+",3,"+IntToS(Abs(P_Speed))+","+ToolChangeBeforeStr+","+IntToS(CorrNo)+")")
			' MW 21.08.2001 kein 5. parameter !!!!!!!!!!!!!!11
			'    wcnc(GToolChangeCycleName+"("+IntToS(ToolNo)+",3,"+IntTos(Abs(P_Speed))+","+ToolChangeBeforeStr+")")
		Else
			If GSiemens840DType=1 Then
				wcncAddCom("C_TSL("+IntToS(ToolNo)+","+IntToS(Abs(Actt.t.MaxRotSpeed))+")","Set Speed limits for next Tool!")
			End If
			wcnc(GToolChangeCycleName+"("+IntToS(ToolNo)+",4,"+IntToS(Abs(P_Speed))+","+ToolChangeBeforeStr+","+IntToS(CorrNo)+")")
			' wcnc(GToolChangeCycleName+"("+IntToS(ToolNo)+",4,"+IntTos(Abs(P_Speed))+","+ToolChangeBeforeStr+")")
		End If
  
	    
End Function




Function GetZeilennummer(s) As String
Dim I As Long
Dim wert As String
   If Mid(s,1,1) <> "N" Then 
      Exit Function 
    End If
 
 
    I=2
	While (Mid(s,I,1) <> Chr(32)) And (I<Len(s))
		wert = wert + Mid(s,I,1)
		I = I + 1
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
		Check_drehzahl=Speed
	
End Function

Function Z__HochAufMaxZ
            wcnc("SUPA G0 D0 Z="+MAX_LIMIT_ZPLUS)
End Function


Function ContPrec_Einlesen
Dim wertstr As Variant

  'ReadStrPP_ini("FAHRVERHALTEN","SC_MINFEED","",wertstr)
  'sc_minfeed=StrToFloat(wertstr)
  'ReadStrPP_ini("FAHRVERHALTEN","SC_CONTPREC","",wertstr)
  'sc_contprec=StrToFloat(wertstr)
	
End Function


Function GetSpindleCodeString(SpindlecodeAsString)
Dim I As Integer
Dim erg As Double
    erg=0 
	For I = (Len(SpindlecodeAsString)) To 1 Step -1
	
		If Mid$(SpindlecodeAsString,I,1)="1" Then erg=erg+exponent2(Len(SpindlecodeAsString)-I)
	Debug.Print erg	
	Next
	SpindlecodeAsString = IntToS(erg)
	
End Function

'Function exponent2(zahl) As Double
'Dim I As Integer
'Dim erg As Double
'    erg = 1
'	If zahl = 1 Then
'		exponent2=erg
'	   	Exit Function
'	End If
'
'	For I = 1 To zahl-1 Step 1
'		erg = erg * 2
'	Next
'	exponent2=erg
'End Function







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



Sub PParaSetALL(AllProcessPara,Processtype,View,IPX,IPY,IPZ,RotA#,TipA#,SPVX,SPVY,SPVZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
  	AllProcessPara.ProcessType=Processtype
	AllProcessPara.View=View
	AllProcessPara.IPX=IPX
	AllProcessPara.IPY=IPY
	AllProcessPara.IPZ=IPZ
	AllProcessPara.RotA=RotA
	AllProcessPara.TipA=TipA
	AllProcessPara.SPVX=SPVX
	AllProcessPara.SPVY=SPVY
	AllProcessPara.SPVZ=SPVZ
	AllProcessPara.Vxx=Vxx
	AllProcessPara.Vxy=Vxy
	AllProcessPara.Vxz=Vxz
	AllProcessPara.Vyx=Vyx
	AllProcessPara.Vyy=Vyy
	AllProcessPara.Vyz=Vyz
	AllProcessPara.Vzx=Vzx
	AllProcessPara.Vzy=Vzy
	AllProcessPara.Vzz=Vzz
End Sub



Function WriteBoolPP_ini(section,ident,bool)
	If bool Then
		'WriteIntPP_ini(section,ident,1)
	Else
		'WriteIntPP_ini(section,ident,0)
	End If
	
End Function





Sub SawingXY_Direction(I_Feedrate,Feedrate,S_Feedrate,speed,SPX,SPY,SPZ,EPX,EPY,EPZ,ZRef,TC,flag,CPSawUnit_PosSX,CPSawUnit_PosSY,CPSawUnit_PosSZ,CPSawUnit_PosRX,CPSawUnit_PosRY,CPSawUnit_PosRZ,CPSawUnit_SPX,CPSawUnit_SPY,CPSawUnit_SPZ,CPSawUnit_EPX,CPSawUnit_EPY,CPSawUnit_EPZ,ViewCPSawUnit_PosSX,ViewCPSawUnit_PosSY,ViewCPSawUnit_PosSZ,ViewCPSawUnit_PosRX,ViewCPSawUnit_PosRY,ViewCPSawUnit_PosRZ,ViewCPSawUnit_SPX,ViewCPSawUnit_SPY,ViewCPSawUnit_SPZ,ViewCPSawUnit_EPX,ViewCPSawUnit_EPY,ViewCPSawUnit_EPZ,Retreat)
	wcncCom("*****************************************")
	wcncCom("*************  Sägen  *******************")
	wcncCom("*****************************************")
	' zurücklegen bei Werkzeugaufruf
    If (equal(ActV.RotA,90) Or equal(ActV.RotA,270)) And (equal(LastV.RotA,0) Or equal(LastV.RotA,180)) And (MarkerSawing.LastIsSawing) Then
       'SAW_UP(ActT.T.aggno)
    End If
    If (equal(LastV.RotA,90) Or equal(LastV.RotA,270)) And (equal(ActV.RotA,0) Or equal(ActV.RotA,180))  And (MarkerSawing.LastIsSawing) Then
       'SAW_UP(ActT.T.aggno)
    End If
	
	If equal(ActV.RotA,90) Or equal(ActV.RotA,270) Then
		'FixeSaegeEinheit(90)
	ElseIf equal(ActV.RotA,0) Or equal(ActV.RotA,180) Then
		'FixeSaegeEinheit(0)
	Else
		AddMistake("Säge-Richtung muss 0° oder 90° liegen!")
	Exit All
	End If
	wcnc(G1+Move(ViewCPSawUnit_SPX,ViewCPSawUnit_SPY,ViewCPSawUnit_SPZ,I_Feedrate,MovePara.TRC))
	wcnc(G1+Move(ViewCPSawUnit_EPX,ViewCPSawUnit_EPY,ViewCPSawUnit_EPZ,Feedrate,MovePara.TRC))
	wcnc(G1+Move(ViewCPSawUnit_PosRX,ViewCPSawUnit_PosRY,ViewCPSawUnit_PosRZ,S_Feedrate,MovePara.TRC))
	MarkerSawing.LastIsSawing=True
	
End Sub



' ch mit anzahl vervielfachen und als string zurückgeben
'Function repl(ch,anz) As String
'Dim I As Long
'Dim result As String
'
'
'result = ""
'For I = 1 To anz
'	result = result + ch
'Next I
'repl = result
'	
'End Function


' String formaten auf anzahl zeichen
' 
'Function StrSize(S,anz,Typ) As String
' Typ = 1 linksbündig
' Typ = 2 rechtsbündig
' Typ = 3 mittig

'StrSize = S
'If Typ = 1 Then
	' linksbündig
'	StrSize = S + repl(" ",anz-Len(S))
'End If
'
'If Typ = 2 Then
'	' rechtsbündig
'	StrSize =  repl(" ",anz-Len(S)) + S
'End If
'
'StrSize = Left(StrSize,anz)
	
'End Function

' *****************************************************************************************
' ** Wert mit vorangestellem Vorzeichen (+/) zurückgeben
' *****************************************************************************************
'Function Get_Val_Signed(v) As String
	'Get_Val_Signed = IIf((v>0)Or(equal(v,0)),"+"+FToS(v),FToS(v)) 
'End Function


Global PathMode_CPREC As Boolean    ' Merker ob aktiv

Function Begin_Continuous_Path_Mode
	If Not PathMode_CPREC Then
		'wcnc("CPRECON")
	End If
	PathMode_CPREC = True

	
End Function

Function End_Continuous_Path_Mode(Retreat)
	If PathMode_CPREC And Retreat Then
		'wcnc("CPRECOF")
		PathMode_CPREC = False
	End If
End Function


' *****************************************************************************************
' ** Nullpunkt schreiben
' *****************************************************************************************
Function SET_Zero(WSetting, pos,oxg,oyg,ozg,oxf,oyf,ozf,mirrx,flag)

'Const Fix_Zero = 2   ' G54 written Zeropoint 
' axis definition
'X-Achsen----------------
Const x1 = "X"
Const X2 = "X1"
'Y-Achsen----------------
Const Y1 = "Y"
Const Y2 = "Y2"
'Z-Achsen----------------
Const Z1 = "Z"
Const Z2 = "Z2"
'Zweite Achse vorhanden?
Const X2Use= False
Const Y2Use= False
Const Z2Use= False


Dim NP_Stri As String
    If WSetting Then
    	' write Zero-Point - Data
		NP_Stri = "$P_UIFR[" + IntToS(Fix_Zero)+ "]=CTRANS("
		NP_Stri = NP_Stri + ""+x1+","
		NP_Stri = NP_Stri + FToS(oxg)
		If X2Use Then
			NP_Stri = NP_Stri + ","+X2+","
			NP_Stri = NP_Stri + FToS(oxg)
		End If
		NP_Stri = NP_Stri + ","+Y1+","
		NP_Stri = NP_Stri + FToS(oyg)
		If Y2Use Then
			NP_Stri = NP_Stri + ","+Y2+","
			NP_Stri = NP_Stri + FToS(oyg)
		End If
		NP_Stri = NP_Stri + ","+Z1+","
		NP_Stri = NP_Stri + FToS(ozg)
		If Z2Use Then
			NP_Stri = NP_Stri + ","+Z2+","
			NP_Stri = NP_Stri + FToS(ozg)
		End If
		NP_Stri = NP_Stri + ")"
	  	' fine offset
		NP_Stri = NP_Stri + ":CFINE("
		NP_Stri = NP_Stri + ""+x1+","
		NP_Stri = NP_Stri + FToS(oxf)
		If X2Use Then
			NP_Stri = NP_Stri + ","+X2+","
			NP_Stri = NP_Stri + FToS(oxf)
		End If
		NP_Stri = NP_Stri + ","+Y1+","
		NP_Stri = NP_Stri + FToS(oyf)
		If Y2Use Then
			NP_Stri = NP_Stri + ","+Y2+","
			NP_Stri = NP_Stri + FToS(oyf)
		End If
		NP_Stri = NP_Stri + ","+Z1+","
		NP_Stri = NP_Stri + FToS(ozf)
		If Z2Use Then
			NP_Stri = NP_Stri + ","+Z2+","
			NP_Stri = NP_Stri + FToS(ozf)
		End If
		NP_Stri = NP_Stri + ")"
		
	  	
		wcnc(NP_Stri)	
		'wcncCom("Hier evtl. auch :CROT, : CSCALE : CMIRROR")
		
		wcncCom("")
		'wcnc("STOPRE")
		'wcnc("R840="+IntToS(Fix_Zero))
		wcnc("STOPRE")
	End If
	If Fix_Zero<=5 Then
		wcnc("G"+IntToS(53+Fix_Zero))
	ElseIf Fix_Zero>5 And Fix_Zero<100 Then
		wcnc("G"+IntToS(499+Fix_Zero))
	Else 
		AddMistake("Check ZereoPoint Number!")
	End If
	wcncCom("")

End Function




'Function BinToDouble(binstri As String) As Variant
'Dim I As Long
'Dim erg As Variant
'
'	erg = 0
''	For I = Len(binstri) To 1 Step -1
'		If Mid$(binstri,I,1)="1" Then erg=erg+exponent2(Len(binstri)-I+1)
'		'Debug.Print erg	
'	Next I
'	BinToDouble=erg

	
'End Function


'Function Str_Replace(test,pos,char)
'Dim I As Long
'Dim erg As String
'Dim ss As String
'
'For I = 1 To Len(test)
'	
'	ss = Mid(test,I,1)
'	If I = pos Then
'		erg = erg + char
'	Else
'		erg = erg + ss
'	End If
'Next

'Str_Replace = erg	
'End Function

'Function Get_First_Token(stri As String) As String      ' stri = "109;110;117"  result = "109"
'Dim I As Long
'Dim erg As String
'
'	erg = ""
'	For I = 1 To Len(stri) 
'		If (Mid(stri,I,1)=";") Then
'			Exit For
'		Else
'			erg = erg + Mid(stri,I,1)
'		End If
'	Next I
'	Get_First_Token = erg
'	
'	
'End Function








Function init_MachineData

	
'	MachinePara.RangeXMin =-500
'    MachinePara.RangeXMax = 3050
'    MachinePara.RangeYMin = -200
'    MachinePara.RangeYMax = 1800
'    MachinePara.RangeZMin = 60'+200
'    MachinePara.RangeZMax = 400'+200
 '   MachinePara.RangeCMin = 0
 '   MachinePara.RangeCMax = 360
    MachinePara.ParkposX = 3432
    MachinePara.ParkposY = 234
    MachinePara.ParkposZ = 400
    MachinePara.DustExt1 = 156      ' Schwellwert 1 Absaugung 
    MachinePara.DustExt2 = 250  	' Schwellwert 2 Absaugung
    MachinePara.DustExt3 = 350   	' Schwellwert 3 Absaugung
    MachinePara.DustExt4 = 450      ' Schwellwert 4 Absaugung
	
End Function

Function Init_JobData
    JobPara.Activ_Fields = MCDATA.ActiveFields	'  Aktive Felder 1=links 2=rechts 3=gekoppelt
	JobPara.laser_activ = PostSettings.LaserActive ' Laser aktiv - dann mit Laserpointer Konturen abfahren
    JobPara.Position =1						' Anschlagposition
    JobPara.Flag = 2        				' Flag
    JobPara.NPX = 440    					' Nullpunkt X
    JobPara.NPY = 342.34  					' Nullpunkt Y
    JobPara.NPZ = 34.3443					' Nullpunkt Z
    JobPara.AUFMASSX =1        				' Aufmass X
    JobPara.AUFMASSY = 2					' Aufmass Y
    JobPara.Pad_Z = 100 						' Saugerhöhe
    JobPara.Jig_Z = 00  					' Schablonenhöhe
    'JobPara.Sic_Z = 14  					' Spannmittel Überstand übers Werkstück -> muss über Jobliste kommen
    'JobPara.Park=1
	JobPara.HPGL_TimeStamp = PostSettings.LaserTimecode	
	JobPara.Add_ZSic = NCData.ProgInfo.SupplementZOffset
	
End Function


Function init_Marker
	Marker.Last_Bm.BM1 = 0
	Marker.Last_Bm.BM2 = 0
	Marker.Last_Bm.BM3 = 0
	Marker.Last_Bm.GroupCode = 0
    Marker.Last_DH_Process =""     ' marker lastproces DrillingV->DH Vertikal DrillingH->DH horizontal
    Marker.Last_DH_ToNo = -9999
	Marker.FirstTime_DH_Drilling=True
	Marker.WP_Lastindex = -1
	Marker.WP_Actindex = -1
	Marker.Last_ExhaustPos = 9999
	ReDim Marker.pneumatic_channel(3)	
	Marker.pneumatic_channel(1)=-1
	Marker.pneumatic_channel(2)=-1
	Marker.pneumatic_channel(3)=-1
	Marker.DINISO_PROCESS=False
	Marker.DINISO_Mode=-1
	Set Marker.BStris = CreateObject("NC_Data.NCData_SetOfString")	
	Set Marker.AStris = CreateObject("NC_Data.NCData_SetOfString")	
End Function

Function wcnc_Workpiece_Info
Dim wp As TWPI
	wp = WPI(Marker.wp_actindex)

	If (Marker.wp_actindex >=0) And (Marker.wp_actindex<= UBound(WPI)) Then

		wcncCom("WP:"+FToS(Marker.wp_actindex)+" Stop:"+FToS(wp.SName)+" X:"+FToS(wp.Sox)+" Y:"+FToS(wp.Soy)+" Z:"+FToS(wp.Soz))
		wcncCom(wp.WPName)
		wcncCom("FX:"+FToS(wp.WPx)+" FY:"+FToS(wp.WPy)+" Z:"+FToS(wp.WPz))
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
		If Len(xstr)>0 Then
			wcnc(PARKXVAR+"="+xstr)
		End If
		If Len(ystr)>0 Then
			wcnc(PARKYVAR+"="+ystr)
		End If
		If (Len(xstr)>0) And (Len(ystr)>0) Then
			wcnc("G153 "+ G0 + " X="+FToS(PARKXVAR)+" Y="+ FToS(PARKYVAR) )
		ElseIf Len(xstr)>0 Then
			' nur x
			wcnc("G153 "+ G0 + " X="+FToS(PARKXVAR) )
		ElseIf Len(ystr)>0 Then
			' nur Y
			wcnc("G153 "+ G0 + " Y="+ FToS(PARKYVAR) )
	 	End If
		
	Else
		' nix tun
	End If
	
'	If MFunction.M41M42 = True Then
'		' vacuum entspannen
'		If (JobPara.activ_fields=1) Then
'			wcnc("M41")
'		ElseIf JobPara.activ_fields=2 Then
'			wcnc("M42")
'		ElseIf JobPara.activ_fields=3 Then
'			wcnc("M41")
'			wcnc("M42")
'		End If
'	End If
'	If MFunction.M60M62 = True Then
'		' Unterstützungstraeger hoch
'		If JobPara.activ_fields=1 Then
'			wcnc("M60")
'		ElseIf JobPara.activ_fields=2 Then
'			wcnc("M62")
'		ElseIf JobPara.activ_fields=3 Then
'			wcnc("M60")
'			wcnc("M62")
'		End If
'	End If
'	If MFunction.M111M112 = True Then
'		' Anschläge hoch
'		If JobPara.activ_fields=1 Then
'			wcnc("M111")
'		ElseIf JobPara.activ_fields=2 Then
'			wcnc("M112")
'		ElseIf JobPara.activ_fields=3 Then
'			wcnc("M111")
'			wcnc("M112")
'		End If
'End If
	

End Function

Function AddLog(stri As String)
	ReDim Preserve LogArr(UBound(LogArr)+1) 
	LogArr(UBound(LogArr))=stri
	
End Function


Function Write_DebuggerLog
Dim Debugg As Integer
Dim I As Long
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
			Open file For Output As #1
		End If
	Else
		Open file For Output As #1
	End If
	Print #1, repl("-",125)
	Print #1, Date + Time
	Print #1, "---- LOG deaktivierbar ueber ID 1102=0 ----"
	Print #1, "WZ:"+TDATA.ActMachineName+ "Post:"+TDATA.MachineData.MachineParameter.PostProzessor+" V"+vers+" Script"+SCRIPT_VERSION
	Print #1, " Processes :"+IntToS(CountOfTool)+ " NC Lines :"+IntToS(NCLine/JobPara.lstp)+ " - Size: " + FileSizeS
	Print #1, "------------------------------------------------"
	For I = 1 To UBound(WPI)-1
		Print #1, "activefield:" +IntToS(MCDATA.ActiveFields)
		Print #1, "workpiece:" + WPI(I).WPName + " Stop:"+(WPI(I).SName)
	Next I 
	Print #1, "ncprog:"+ncpathGlobal+NCNameGlobal
	For I = 1 To UBound(LogArr)
		Print #1, LogArr(I)
	Next I 
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

' Werkstückwechsel stattgefunden ?
Function Is_WP_Change As Boolean
Dim erg As Boolean

	erg = False

	If (UBound(WPI)>1) And (Marker.wp_actindex>0) And (Marker.wp_lastindex>0) Then
		' mindesten 2 Bearbeitungen und 
		If (WPI(Marker.wp_lastindex).SName <> WPI(Marker.wp_actindex).SName) Then
			' Anschlag  - Namen unterschiedlich
			If Marker.wp_lastindex <> Marker.wp_actindex Then
				' index hat sich geändert
				erg = True
			End If
		End If
	End If
	Is_WP_Change=erg
	
End Function

Function Verschleiss_BasismassNullen(Tnum,DNum)
Dim isok As Boolean
Dim CalcPivotPointOffset As Boolean

		'Verschleiss
		'CalcPivotPointOffset = MT_get_Add_ID(ActT,10006,isok)
		'If isok And CalcPivotPointOffset Then
		'	wcncAddCom("$TC_DP12["+IntToS(Tnum)+","+IntToS(DNum)+"]=" + FToS(-actt.PH_Add.ToolCenterPoint)," Verschleiss")
		'Else
		wcncAddCom("$TC_DP12["+IntToS(Tnum)+","+IntToS(DNum)+"]=0"," Verschleiss")
		'End If
		wcncAddCom("$TC_DP13["+IntToS(Tnum)+","+IntToS(DNum)+"]=0","")
		wcncAddCom("$TC_DP14["+IntToS(Tnum)+","+IntToS(DNum)+"]=0","")
		'Basismass
		wcncAddCom("$TC_DP21["+IntToS(Tnum)+","+IntToS(DNum)+"]=0"," Basismass")
		wcncAddCom("$TC_DP22["+IntToS(Tnum)+","+IntToS(DNum)+"]=0","")
		wcncAddCom("$TC_DP23["+IntToS(Tnum)+","+IntToS(DNum)+"]=0","")
End Function

Function wcnc_msg(msg As String)
Const NR = "" ' +Chr(34)+"$67301"+Chr(34)

	wcnc("MSG ("+Chr(34)+msg+Chr(34)+NR + ")" )
End Function


Function wcnc_msgOff

	wcnc("MSG ("+Chr(34)+Chr(34)+ ")" )
End Function

'pick the parameter at position 'nr' of the string 'S'
Function GetParamHPGL(S, GTyp,X,Y)
Dim	Count As Integer
Dim n As Integer
Dim p As Integer
Dim SSave As String
	' Version 1 Punkte
	' PA 731.800,0.00;
	SSave=UCase(S)	
	If InStr(SSave,"PA")>0 Then
		GTyp = "1"
		 ' PA entfernen
		 SSave = delete(SSave,1,InStr(S,"PA")+2)
	     p= InStr(SSave,",")
		
		x=RTrim(LTrim(Mid(SSave,1,p-1)))
		Y=RTrim(LTrim(Mid(SSave,p+1,Len(SSave)-p-1)))
	Else
		GTyp = "???"
	End If
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


' holt Fehlermeldung aus der Datei ppscript_de.ini in Abhängigkeit der gewählten Sprache
Function GetErrMsg(no As Long,stri,mode) As String

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




Function Norm0_180(w) As Double
	While w<-180 
		w=w+360
	Wend
	While w>=180 
		w=w-360
	Wend
	Norm0_180 = w
End Function


Function Norm360_360(w) As Double
	While w<-360 
		w=w+360
	Wend
	While w>=360 
		w=w-360
	Wend
	Norm360_360 = w
End Function

Function NormPlusMinus_180(w) As Double
	While w<-180 
		w=w+360
	Wend
	While w>180 
		w=w-360
	Wend
	NormPlusMinus_180 = w
End Function


Function GetAddZSic As Double
	GetAddZSic = JobPara.add_zsic
End Function



Function Get_ParkStrXY(xstr,ystr As String)

	If JobPara.park=1 Then
		' links hinten Parken
		xstr=MAX_LIMIT_XMINUS
		ystr=MAX_LIMIT_YPLUS
	ElseIf JobPara.park=2 Then
		' rechts hinten Parken
		xstr=MAX_LIMIT_XPLUS
		ystr=MAX_LIMIT_YPLUS
	ElseIf JobPara.park=3 Then
		' mitte hinten Parken
		xstr="("+MAX_LIMIT_XPLUS+"-"+MAX_LIMIT_XMINUS+")/2"
		ystr=MAX_LIMIT_YPLUS
	ElseIf JobPara.park=4 Then
		' links vorne parken
		xstr=MAX_LIMIT_XMINUS
		ystr=MAX_LIMIT_YMINUS
	ElseIf JobPara.park=5 Then
		' rechts vorne parken
		xstr=MAX_LIMIT_XPLUS
		ystr=MAX_LIMIT_YMINUS
	ElseIf JobPara.park=6 Then
		' mitte vorne parken
		xstr="("+MAX_LIMIT_XPLUS+"-"+MAX_LIMIT_XMINUS+")/2"
		ystr=MAX_LIMIT_YMINUS
	ElseIf JobPara.park=7 Then
		' mitte links parken
		xstr=MAX_LIMIT_XMINUS
		ystr="("+MAX_LIMIT_YPLUS+"-"+MAX_LIMIT_YMINUS+")/2"
	ElseIf JobPara.park=8 Then
		' mitte rechts parken
		xstr=MAX_LIMIT_XPLUS
		ystr="("+MAX_LIMIT_YPLUS+"-"+MAX_LIMIT_YMINUS+")/2"
	ElseIf JobPara.park=9 Then
		' mitte mitte parken
		xstr="("+MAX_LIMIT_XPLUS+"-"+MAX_LIMIT_XMINUS+")/2"
		ystr="("+MAX_LIMIT_YPLUS+"-"+MAX_LIMIT_YMINUS+")/2"
	ElseIf JobPara.park=10 Then
		' Freie X/Y - Position
		xstr=FToS(JobPara.parkx)
		ystr=FToS(JobPara.parky)
	ElseIf JobPara.park=11 Then
		' automatische Parkposition
		If JobPara.Activ_Fields = 1 Then
			' Werkstück links 
			' in X rechts vom Werkstück parken
			xstr= FToS(JobPara.npx + FinishedPart.X + mPara_Add.PARK_DIST_X_Field1)
			ystr= MAX_LIMIT_YPLUS
		ElseIf JobPara.Activ_Fields= 2 Then
			' Werkstück rechts
			' in X links vom Werkstück parken
			xstr= FToS(JobPara.npx -  mPara_Add.PARK_DIST_X_Field2)
			ystr= MAX_LIMIT_YPLUS
		Else
			' Felder gekoppelt
			' Mitten hinten parken
			xstr="("+MAX_LIMIT_XPLUS+"-"+MAX_LIMIT_XMINUS+")/2"
			ystr=MAX_LIMIT_YPLUS
		End If
	ElseIf JobPara.park=12 Then
		' Neu 20.03.2006
		' Parken in Y
		xstr=""
		ystr=MAX_LIMIT_YPLUS
	End If

	
End Function

Function MarkerSawingReset

	MarkerSawing.LastIsSawing=False
	MarkerSawing.LastKW=99999
	
End Function

Function WritePPVersion
' MW 15.03.2007
	'WriteStrPP_ini("VERSION", "PPSCRIPT",SCRIPTVERSION)
	
End Function


' spannen kommt als Array[10] of variant
' es kommt z.B. Stri="M65,M32,M33"
' Funktino prüf
Function M_Hinzu(Arr,stri)
Dim I,j,K As Integer 
Dim ns As String  ' new M-Funktion
Dim found As Boolean 
	For K = 1 To ParamCountSep(stri,",") 
		found = False
		ns = ParamSep(K,stri,",")
		
		For I = 1 To UBound(Arr)
			If ns=Arr(I) Then
				found = True
			End If
		Next I
		If Not found Then
			For I = 1 To UBound(Arr)
				If Arr(I)="" Then
					Arr(I)=ns
					Exit For
				End If
			Next I
	    				
		End If
	Next K
	
	
End Function

Function WKS_GetTabeleFuctions

Dim i,J,K As Long
Const UsedPins=100101
Const UsedSpezPins=100102
Const SupportersUsed=100103

Const Ist_Nesting_Machiene=900001
Const SpKTischVac=900004
Const SpKreiseTischVacModus=900005
Const SpKPneu=900006
Const SpKPneuModus=900007
Const SpPinsGpCount=900008
Const SpSupportersCount=900009
Const SpKSupporterstableMode=900010
Const SpKHoldVacCircles=900011
Const SiemensZeroPoint=900012
Const TableType=900013
Const ToolChangeCycleName=900014
Const Siemens840DType=900015
Const SpKPfo=900016
Const SpKPfoModus=900017
Const STranspON=900018
Const STranspOFF=900019

Const VacuumKreisOn=900101
Const VacuumKreisNotUsed=900151
Const VacuumKreisOff=900201
Const VacuumKreisOffHp=900251
Const PneuKreisOff=900301
Const PinsUp=900401
Const PinsDown=900501
Const SupportersUp=900601
Const SupportersDown=900701
Const PfoClamp=900801
Const PfoUnClamp=900901

Dim mcd_zp As IZeroPoint

Dim SpannkreiseTischVac As Long					'Anz. Spannfunktionen auf dem Tisch
Dim SpannKreiseTischVacModus As Long			'Betriebsmodus Spannkreise 1=Fortlaufend 2=Tischhälften weise, gekoppelt fortlaufend
Dim SpannKreiseTischPneu As Long				'Anz. PneumatikSpannfunktionen auf dem Tisch
Dim SpannKreiseTischPneuModus As Long 			'Betriebsmodus PneumatikSpannkreise 1=Fortlaufend 2=Tischhälften weise, gekoppelt fortlaufend
Dim SpannKreiseTischPfo As Long					'Anz. PfostenSpannfunktionen auf dem Tisch
Dim SpannKreiseTischPfoModus As Long			'Betriebsmodus PfostenSpannkreise 1=Fortlaufend 2=Tischhälften weise, gekoppelt fortlaufend
Dim PinsGpCount As Long							'Anzahl Anschlaggruppen
Dim SupportersCount As Long            			'Anzahl Unterstützungsträger
Dim SupportersTableMode As Long					'Betriebsmodus Unterstützungsträger 1=Fortlaufend 2=Tischhälften weise, gekoppelt fortlaufend
Dim HoldVacCircles As Long
Dim VacNotUsed(10) As Boolean
Dim HoldCircles(10) As Boolean

Dim SpkStart, SpkEnde, PneuStart, PneuEnde, SuppStart, SuppEnde, PinsStart, PinsEnde, PfoStart, PfoEnde As Long

	JobPara.WorkC_OptionBit = Val(MCDATA.Additions.GetAddition_ID(80000).Value)

	'If Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(Ist_Nesting_Machiene)) Is Nothing Then 
		'Not Used But Reserved
	'End If
		
	If Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SpKTischVac)) Is Nothing Then 
		SpannkreiseTischVac=CLng(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SpKTischVac).Value)
	Else
		AddMistake("MachinParameter Missing ID: "+CStr(SpKTischVac))
	End If
	
	If Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SpKreiseTischVacModus)) Is Nothing Then 
		SpannKreiseTischVacModus=CLng(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SpKreiseTischVacModus).Value)
	Else
		AddMistake("MachinParameter Missing ID: "+CStr(SpKreiseTischVacModus))
	End If
	
	If Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SpKPneu)) Is Nothing Then 
		SpannKreiseTischPneu=CLng(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SpKPneu).Value)
	Else
		AddMistake("MachinParameter Missing ID: "+CStr(SpKPneu))
	End If

	If Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SpKPneuModus)) Is Nothing Then 
		SpannKreiseTischPneuModus=CLng(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SpKPneuModus).Value)
	Else
		AddMistake("MachinParameter Missing ID: "+CStr(SpKPneuModus))
	End If
	
	If Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SpPinsGpCount)) Is Nothing Then 
		PinsGpCount=CLng(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SpPinsGpCount).Value)
	Else
		AddMistake("MachinParameter Missing ID: "+CStr(PinsGpCount))
	End If
	
	If Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SpSupportersCount)) Is Nothing Then 
		SupportersCount=CLng(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SpSupportersCount).Value)
	Else
		AddMistake("MachinParameter Missing ID: "+CStr(SpSupportersCount))
	End If
	
	If Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SpKSupporterstableMode)) Is Nothing Then 
		SupportersTableMode=CLng(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SpKSupporterstableMode).Value)
	Else
		AddMistake("MachinParameter Missing ID: "+CStr(SpKSupporterstableMode))
	End If

	'NotUsed Just Reserved
	'If Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SpKHoldVacCircles)) Is Nothing Then 
	'	HoldVacCircles=CLng(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SpKHoldVacCircles).Value)
	'Else
	'	AddMistake("MachinParameter Missing ID: "+CStr(SpKHoldVacCircles))
	'End If
	
	If (Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SiemensZeroPoint)) Is Nothing) Then
		Fix_Zero=CLng(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SiemensZeroPoint).Value)
	Else
		AddHint("NoZeropiontNumber ID:"+IntToS(SiemensZeroPoint))
		Fix_Zero=2
	End If

	If (Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(TableType)) Is Nothing) Then
		GTableType=CLng(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(TableType).Value)
	Else
		AddHint("TableType ID:"+IntToS(TableType))
		GTableType=0
	End If
	
	If (Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(ToolChangeCycleName)) Is Nothing) Then
		GToolChangeCycleName=(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(ToolChangeCycleName).Value)
	Else
		AddHint("NoZeropiontNumber ID:"+IntToS(SiemensZeroPoint))
		GToolChangeCycleName="C_WECHSEL"
	End If
	
	If (Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(Siemens840DType)) Is Nothing) Then
		GSiemens840DType=CLng(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(Siemens840DType).Value)
	Else
		AddHint("NoZeropiontNumber ID:"+IntToS(SiemensZeroPoint))
		GSiemens840DType=1
	End If
	'----------------------------------------------------------------------
	If (Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SpKPfo)) Is Nothing) Then
		SpannKreiseTischPfo=CLng(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SpKPfo).Value)
	Else
		AddMistake("MachinParameter Missing ID: "+CStr(SpKPfo))
		SpannKreiseTischPfo=0
	End If
	
	If (Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SpKPfoModus)) Is Nothing) Then
		SpannKreiseTischPfoModus=CLng(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SpKPfoModus).Value)
	Else
		AddMistake("MachinParameter Missing ID: "+CStr(SpKPfoModus))
		SpannKreiseTischPfoModus=0
	End If
	'-----------------------------------------------------------------------
	If (Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(STranspON)) Is Nothing) Then
		Marker.TranspOn=CStr(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(STranspON).Value)
	Else
		AddHint("NoZeropiontNumber ID:"+IntToS(SiemensZeroPoint))
		Marker.TranspOn=";NoDustTransport"
	End If
	
	If (Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(STranspOFF)) Is Nothing) Then
		Marker.TranspOff=CStr(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(STranspOFF).Value)
	Else
		AddHint("NoZeropiontNumber ID:"+IntToS(SiemensZeroPoint))
		Marker.TranspOff=";NoDustTransport"
	End If

	
	'START Aenderung OS für Anzahl Kreise=1 OS 10.09.2013
	'Sonderfall ein Kreis zugelassen Ungerade Fälle werden abgefangen
	If SpannkreiseTischVac>1 And (SpannkreiseTischVac Mod 2)=1 Then
		AddMistake("Unzulässige anzahl Kriese: "+vbCrLf+"SpannkreiseTischVac"+vbCrLf+"Tischparameter prüfen!")  
	ElseIf SpannKreiseTischPneu>1 And (SpannKreiseTischPneu Mod 2)=1 Then
		AddMistake("Unzulässige anzahl Kriese: SpannKreiseTischPneu"+vbCrLf+"Tischparameter prüfen!")  
	ElseIf SupportersCount>1 And (SupportersCount Mod 2)=1 Then
		AddMistake("Unzulässige anzahl Kriese: SupportersCount"+vbCrLf+"Tischparameter prüfen!")  
	ElseIf PinsGpCount>1 And (PinsGpCount Mod 2)=1 Then
		AddMistake("Unzulässige anzahl Kriese: PinsGpCount"+vbCrLf+"Tischparameter prüfen!")  
	End If
	
	If JobPara.Activ_fields=1 Then
		
		If SpannkreiseTischVac>1 Then
			SpkStart=0
			SpkEnde=SpannkreiseTischVac/2 
		Else
			If SpannkreiseTischVac=1 Then
				SpkStart=0
				SpkEnde=1
			Else
				SpkStart=0
				SpkEnde=0
			End If
		End If
	
		If SpannKreiseTischPneu>1 Then
			PneuStart=0
			PneuEnde=SpannKreiseTischPneu/2
		Else
			If SpannKreiseTischPneu=1 Then
				PneuStart=0
				PneuEnde=1
			Else
				PneuStart=0
				PneuEnde=0
			End If
		End If
		
		If SpannKreiseTischPfo>1 Then
			PfoStart=0
			PfoEnde=SpannKreiseTischPfo/2
		Else
			If SpannKreiseTischPfo=1 Then
				PfoStart=0
				PfoEnde=1
			Else
				PfoStart=0
				PfoEnde=0
			End If
		End If
		
		If SupportersCount>1 Then
			SuppStart=0
			SuppEnde=SupportersCount/2
		Else
			If SupportersCount=1 Then
				SuppStart=0
				SuppEnde=1
			Else
				SuppStart=0
				SuppEnde=0
			End If
		End If

		If PinsGpCount>1 Then
			PinsStart=0 
			PinsEnde=PinsGpCount/2
		Else
			If PinsGpCount=1 Then
				PinsStart=0
				PinsEnde=1
			Else
				PinsStart=0
				PinsEnde=0
			End If
		End If
		
	ElseIf JobPara.Activ_fields=2 Then
	
		If SpannkreiseTischVac>1 Then
			SpkStart=SpannkreiseTischVac/2
	 		SpkEnde=SpannkreiseTischVac
		Else
			If SpannkreiseTischVac=1 Then
				SpkStart=0
				SpkEnde=1
			Else
				SpkStart=0
				SpkEnde=0
			End If
		End If
		
		If SpannKreiseTischPneu>1 Then
			PneuStart=SpannKreiseTischPneu/2
			PneuEnde=SpannKreiseTischPneu
		Else
			If SpannKreiseTischPneu=1 Then
				PneuStart=0
				PneuEnde=1
			Else
				PneuStart=0
				PneuEnde=0
			End If
		End If
		
		If SpannKreiseTischPfo>1 Then
			PfoStart=SpannKreiseTischPfo/2
			PfoEnde=SpannKreiseTischPfo
		Else
			If SpannKreiseTischPfo=1 Then
				PfoStart=0
				PfoEnde=1
			Else
				PfoStart=0
				PfoEnde=0
			End If
		End If
		
		If SupportersCount>1 Then
			SuppStart=SupportersCount/2
			SuppEnde=SupportersCount
		Else
			If SupportersCount=1 Then
				SuppStart=0
				SuppEnde=1
			Else
				SuppStart=0
				SuppEnde=0
			End If	
		End If
		
		If PinsGpCount>1 Then
			PinsStart=PinsGpCount/2
			PinsEnde=PinsGpCount
		Else
			If PinsGpCount=1 Then
				PinsStart=0
				PinsEnde=1
			Else
				PinsStart=0
				PinsEnde=0
			End If	
		End If
		
	ElseIf JobPara.Activ_fields=3 Then
		SpkStart=0
		SpkEnde=SpannkreiseTischVac
		PneuStart=0
		PneuEnde=SpannKreiseTischPneu
		PfoStart=0
		PfoEnde=SpannKreiseTischPfo
		SuppStart=0
		SuppEnde=SupportersCount
		PinsStart=0 
		PinsEnde=PinsGpCount
	End If
	
	'ENDE Aenderung OS 10.09.2013 für Anzahl Kreise=1 OS 10.09.2013
	
	For I=0 To 10 
		If (Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(VacuumKreisNotUsed+I)) Is Nothing) Then
			If CLng(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(VacuumKreisNotUsed+I).Value)>0 Then
				If is_WorkC_OptionBit(CLng(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(VacuumKreisNotUsed+I).Value),JobPara.WorkC_OptionBit) Then
					VacNotUsed(I)=True
				End If	
			End If
		End If
		If (Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(VacuumKreisOffHp+I)) Is Nothing) Then
			If CLng(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(VacuumKreisOffHp+I).Value)>0 Then
				HoldCircles(I)=True
			End If
		End If
	Next I
	
	'Anschlagsfunktionen einlesen
	'----------------------------
	
	For I = 1 To UBound(WPI) -1
	
		Set mcd_zp = MCDATA.ZeroPoints.GetZeroPointName(WPI(I).SName)		
		' Izeropoint
		
	 	If (Not mcd_zp Is Nothing) And (PostSettings.PPStarterType=ppstWorkcenter) Then
			' Anschläge benutzt
	 		If Not mcd_zp.Additions.GetAddition_ID(UsedPins) Is Nothing Then
	 			M_Hinzu(Anschlag_Used,mcd_zp.Additions.GetAddition_ID(UsedPins).Value)
			Else
				AddHint("No function for stops down found : ID="+IntToS(UsedPins) +" ZP: " + mcd_zp.Name)
			End If		  
		Else
			AddMistake("zeropoint not found -"+WPI(I).SName)
		End If 
		
		If (Not mcd_zp Is Nothing) And (PostSettings.PPStarterType=ppstWorkcenter) Then
			' Anschläge Spezial benutzt
	 		If Not mcd_zp.Additions.GetAddition_ID(UsedSpezPins) Is Nothing Then
	 			M_Hinzu(SpezAnschlag_Used,mcd_zp.Additions.GetAddition_ID(UsedSpezPins).Value)
			Else
				AddHint("No function for stops down found : ID="+IntToS(UsedSpezPins) +" ZP: " + mcd_zp.Name)
			End If		  
		Else
			AddMistake("zeropoint not found -"+WPI(I).SName)
		End If 
	
		If (Not mcd_zp Is Nothing) And (PostSettings.PPStarterType=ppstWorkcenter) Then
			' Supporter benutzt
	 		If Not mcd_zp.Additions.GetAddition_ID(SupportersUsed) Is Nothing Then
	 			M_Hinzu(Supporters_Used,mcd_zp.Additions.GetAddition_ID(SupportersUsed).Value)
			Else
				AddHint("No function for stops down found : ID="+IntToS(SupportersUsed) +" ZP: " + mcd_zp.Name)
			End If		  
		Else
			AddMistake("zeropoint not found -"+WPI(I).SName)
		End If 
	
	Next I
	

	
	For I = 0 To 10
	
		'Anschläge Hoch
		If CLng(Anschlag_Used(I))>0 Then
			For J=0 To 10   
				If Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PinsDown+J)) Is Nothing Then 
					If CLng(Anschlag_Used(I)) And CLng(exponent2_v2(J)) Then
						If Trim(Anschlag_down(I)="") Then
					 		Anschlag_down(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PinsDown+J).Value
					 	End If
					End If
				End If
				If Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PinsUp+J)) Is Nothing Then 
					If CLng(Anschlag_Used(I)) And CLng(exponent2_v2(J)) Then
						If Trim(Anschlag_up(I)="") Then
					 		Anschlag_up(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PinsUp+J).Value
					 	End If
					End If
				End If
			Next J
		End If
		
		'Sonderanschläge Hoch
		If CLng(SpezAnschlag_Used(I))>0 Then
			For J=0 To 10   
				If Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PinsDown+J)) Is Nothing Then 
					If CLng(SpezAnschlag_Used(I)) And CLng(exponent2_v2(J)) Then
						If Trim(SpezAnschlag_down(I)="") Then
					 		SpezAnschlag_down(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PinsDown+J).Value
					 	End If
					End If
				End If
				If Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PinsUp+J)) Is Nothing Then 
					If CLng(SpezAnschlag_Used(I)) And CLng(exponent2_v2(J)) Then
						If Trim(SpezAnschlag_up(I)="") Then
					 		SpezAnschlag_up(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PinsUp+J).Value
					 	End If
					End If
				End If
			Next J
			AddMistake("Spezialanschlaege groesser 0!!! Diese Funktion ist nicht eingefahren!")
		End If
		
		'Untertuetzer Agedachte variante Wenn anschlagabhaengig!!!
		'If CLng(Supporters_Used(I))>0 Then
		'	For J=0 To 10   
		'		If Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(900501+J)) Is Nothing Then 
		'			If CLng(Anschlag_Used(I)) And CLng(exponent2_v2(J)) Then
		'				If Trim(Anschlag_down(I)="") Then
		'			 		Anschlag_down(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(900501+J).Value
		'			 	End If
		'			End If
		'		End If
		'		If Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(900401+J)) Is Nothing Then 
		'			If CLng(Anschlag_Used(I)) And CLng(exponent2_v2(J)) Then
		'				If Trim(Anschlag_up(I)="") Then
		'			 		Anschlag_down(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(900401+J).Value
		'			 	End If
		'			End If
		'		End If
		'	Next J
		'End If
		
		
		'---------------------------------
		'Spannkreis Handling Spannen
			
		If (I>=(SpkStart) And (I<SpkEnde)) Then 
			If (Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(VacuumKreisOn+I)) Is Nothing) Then
				If VacNotUsed(I)=False Then
					If SpannKreiseTischVacModus=2 And JobPara.Activ_fields=2 Then
						Spannen(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(VacuumKreisOn-SpkStart+I).Value
					ElseIf SpannKreiseTischVacModus=3 And JobPara.Activ_fields=2 Then
						Spannen(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(VacuumKreisOn+SpkEnde-I-1).Value
					Else
						Spannen(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(VacuumKreisOn+I).Value
					End If
				End If
			Else
				AddMistake("MachinParameter Missing ID: "+CStr(VacuumKreisOn+I))
			End If
		End If
			
		'---------------------------------
		'Spannkreis Handling EntSpannen
			
		If (I>=(SpkStart) And (I<SpkEnde)) Then 
			If (Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(VacuumKreisOff+I)) Is Nothing) Then
				If (Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(VacuumKreisOffHp+I)) Is Nothing) Then
					If is_WorkC_OptionBit(HoldVacPads,JobPara.WorkC_OptionBit) Then
						If VacNotUsed(I)=False And HoldCircles(I)=False Then
							If SpannKreiseTischVacModus=2 And JobPara.Activ_fields=2 Then
								EntSpannen(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(VacuumKreisOff-SpkStart+I).Value
							ElseIf SpannKreiseTischVacModus=3 And JobPara.Activ_fields=2 Then
								EntSpannen(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(VacuumKreisOff+SpkEnde-I-1).Value
							Else
								EntSpannen(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(VacuumKreisOff+I).Value
							End If
						End If
					Else
						If VacNotUsed(I)=False Then
							If SpannKreiseTischVacModus=2 And JobPara.Activ_fields=2 Then
								EntSpannen(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(VacuumKreisOff-SpkStart+I).Value
							ElseIf SpannKreiseTischVacModus=3 And JobPara.Activ_fields=2 Then
								EntSpannen(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(VacuumKreisOff+SpkEnde-I-1).Value
							Else
								EntSpannen(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(VacuumKreisOff+I).Value
							End If
						End If
					End If
				Else
					AddMistake("MachinParameter Missing ID: "+CStr(VacuumKreisOffHp+I))
				End If
			Else
				AddMistake("MachinParameter Missing ID: "+CStr(VacuumKreisOff+I))
			End If
		End If
			
		'---------------------------------
		'Pneumatik Spannkreis Handling EntSpannen
			
		If (I>=(PneuStart) And (I<PneuEnde)) Then 
			If (Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PneuKreisOff+I)) Is Nothing) Then 
				If SpannKreiseTischPneuModus=2 And JobPara.Activ_fields=2 Then
					PneumEntSpannen(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PneuKreisOff-PneuStart+I).Value
				ElseIf SpannKreiseTischPneuModus=3 And JobPara.Activ_fields=2 Then
					PneumEntSpannen(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PneuKreisOff+PneuEnde-I-1).Value
				Else
					PneumEntSpannen(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PneuKreisOff+I).Value
				End If
			Else
				AddMistake("MachinParameter Missing ID: "+CStr(PneuKreisOff+I))
			End If
		End If
			
		'---------------------------------
		'Supporters UP
			
		If (I>=(SuppStart) And (I<SuppEnde)) Then 
			If (Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SupportersUp+I)) Is Nothing) Then 
				If SupportersTableMode=2 And JobPara.Activ_fields=2 Then
					Supporters_Up(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SupportersUp-SuppStart+I).Value
				ElseIf SupportersTableMode=3 And JobPara.Activ_fields=2 Then
					Supporters_Up(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SupportersUp+SuppEnde-I-1).Value
				Else
					Supporters_Up(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SupportersUp+I).Value
				End If
			Else
				AddMistake("MachinParameter Missing ID: "+CStr(SupportersUp+I))
			End If
		End If
				
		'---------------------------------
		'Supporters Down
		
		If (I>=(SuppStart) And (I<SuppEnde)) Then 
			If (Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SupportersDown+I)) Is Nothing) Then 
				If SupportersTableMode=2 And JobPara.Activ_fields=2 Then
					Supporters_down(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SupportersDown-SuppStart+I).Value
				ElseIf SupportersTableMode=3 And JobPara.Activ_fields=2 Then
					Supporters_down(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SupportersDown+SuppEnde-I-1).Value
				Else
					Supporters_down(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(SupportersDown+I).Value
				End If
			Else
				AddMistake("MachinParameter Missing ID: "+CStr(SupportersDown+I))
			End If
		End If
		
		
		'---------------------------------
		'Pfosten On
			
		If (I>=(PfoStart) And (I<PfoEnde)) Then 
			If (Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PfoClamp+I)) Is Nothing) Then 
				If SpannKreiseTischPfoModus=2 And JobPara.Activ_fields=2 Then
					PfoSpannen(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PfoClamp-PfoStart+I).Value
				ElseIf SpannKreiseTischPfoModus=3 And JobPara.Activ_fields=2 Then
					PfoSpannen(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PfoClamp+PfoEnde-I-1).Value
				Else
					PfoSpannen(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PfoClamp+I).Value
				End If
			Else
				AddMistake("MachinParameter Missing ID: "+CStr(PfoClamp+I))
			End If
		End If
				
		'---------------------------------
		'Pfosten Off
		
		If (I>=(PfoStart) And (I<PfoEnde)) Then 
			If (Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PfoUnClamp+I)) Is Nothing) Then 
				If SpannKreiseTischPfoModus=2 And JobPara.Activ_fields=2 Then
					PfoEntSpannen(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PfoUnClamp-SuppStart+I).Value
				ElseIf SpannKreiseTischPfoModus=3 And JobPara.Activ_fields=2 Then
					PfoEntSpannen(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PfoUnClamp+SuppEnde-I-1).Value
				Else
					PfoEntSpannen(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PfoUnClamp+I).Value
				End If
			Else
				AddMistake("MachinParameter Missing ID: "+CStr(PfoUnClamp+I))
			End If
		End If
		
		'---------------------------------
		'Get All Pins Down
		
		If (I>=(PinsStart) And (I<PinsEnde)) Then 
			If (Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PinsDown+I)) Is Nothing) Then 
				Anschlag_downAll(I)=TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(PinsDown+I).Value
			End If
		End If	
	Next I

End Function


Function WKS_ENTSPANNEN

Dim xstr,ystr As String
	
	'Auf jedenfall Ionisator ausschalten
	
	Call Blasen_AUS
	Call BlasenSaw_AUS
	
	
	'Nummer der Optionsbits OS 02.05.2013 Hier knoenen die optionsbits den namen zugewiesen werden.
	'Global Const VacOffAtEnd		'Switchen der Optionsbits Vakuum aus am ende des programms
	'Global Const PneuOffAtEnd		'Pneumatik aus am ende des Programms
	'Global Const PinsUpAtEnd		'Anschläge Hoch am ende des Programms
	'Global Const IsNestingMode		'Maschen Läuft im nesting Modus
	'Global Const PinsUpAtStart		'Pins Hoch am Anfang
	'Global Const HoldVacPads		'Vacuum für Sauger halten wenn am ende entspannt wird
	'Global Const Use2VacField		'2. Vacuumkreis dazu
	'Global Const RotAddAAxis		'Zusätzliche Rotationsachse ansteuern
	'Global Const Tornado      		'Tornado ein
	'Global Const SuppsUpAtEnd		'Unterstützer Hoch am ende
	'Global Const SuppsUpAtStart    'unterstützer hoch am anfang
	
	If is_WorkC_OptionBit(Tornado ,JobPara.WorkC_OptionBit) Then
		'Ohne Tornado
	Else
		'Mit Tornado
		'wcnc("M94")
	End If

	' nix - Maschine bleibt nach letzter Bearbeitung stehen
	xstr=""
	ystr=""
	Get_ParkStrXY(xstr,ystr)
	
	If JobPara.park > 0 Then
		If Len(xstr)>0 Then
			wcnc(PARKXVAR+"="+xstr)
		End If
		If Len(ystr)>0 Then
			wcnc(PARKYVAR+"="+ystr)
		End If
		wcnc("G153 "+ G0 + " Z=MAXZ")
		If (Len(xstr)>0) And (Len(ystr)>0) Then

			wcnc("G153 "+ G0 + " X="+FToS(PARKXVAR)+" Y="+ FToS(PARKYVAR) )
		
		ElseIf Len(xstr)>0 Then
			' nur x
			wcnc("G153 "+ G0 + " X="+FToS(PARKXVAR) )
		ElseIf Len(ystr)>0 Then
			' nur Y
			wcnc("G153 "+ G0 + " Y="+ FToS(PARKYVAR))
	 	End If
		
	Else
		' nix tun - 
	End If

	' Vakuum lösen  Bit
	If is_WorkC_OptionBit(VacOffAtEnd,JobPara.WorkC_OptionBit) Then	
		vacuum_entspannen(0)	
	End If
	
	' Pneumatic lösen  Bit
	If is_WorkC_OptionBit(PneuOffAtEnd,JobPara.WorkC_OptionBit) Then	
		pneumatik_entspannen(0)	
	End If
	
	If is_WorkC_OptionBit(UnClampPfo,JobPara.WorkC_OptionBit) Then
		Pfosten_entspannen(0)	
	End If
	wcnc("STOPRE")
	' Anschläge hoch
	If is_WorkC_OptionBit(PinsUpAtEnd,JobPara.WorkC_OptionBit) Then
		' Anschläge Programmende hoch  Bit 3
		Anschlaege_hoch(0)
		If is_WorkC_OptionBit(PinsUpSonder,JobPara.WorkC_OptionBit) Then 
			wcnc("H38")
		End If
	End If
	
	' Unterstützer Hoch
	If is_WorkC_OptionBit(SuppsUpAtEnd,JobPara.WorkC_OptionBit) Then
		' Anschläge Programmende hoch  Bit 3
		Unterstuetzer_hoch(0)
	End If
	
	If is_WorkC_OptionBit(UseSTransp,JobPara.WorkC_OptionBit) Then
		wcnc(Marker.TranspOff)
	End If
	
	If is_WorkC_OptionBit(AusTransportPos,JobPara.WorkC_OptionBit) Then
		If JobPara.activ_fields=3 Then
			If is_WorkC_OptionBit(SuppsUpAtEnd,JobPara.WorkC_OptionBit) And is_WorkC_OptionBit(VacOffAtEnd,JobPara.WorkC_OptionBit) Then
				wcnc("C_TRANSPORT")
			Else
				AddMistake("Werkstueck entspannen! Unterstuetzer Hoch!")
			End If
			
		Else
			AddMistake("Austransport nur mit FeldKopplung erlaubt!")
		End If
		
	
	End If
	

End Function
	

Function is_WorkC_OptionBit(Bit,OptionDez) As Boolean 
Dim suche As Long
    suche = exponent2(Bit)

		
 	is_WorkC_OptionBit = IIf((OptionDez And suche)=suche,True,False)
Exit Function
	
End Function

'Wahlweise als WCNC oder schreiben in die Aktuelle Stringliste.
Function vacuum_on(NR)
Dim I As Long 
Dim gefunden As Boolean 
Dim Links As Boolean
Dim Rechts As Boolean


	Links=False
	Rechts=False
	wcncCom("--- Vakuum Kontrolle ein")



		' Vakuumüberwachung einschalten
		For I = 0 To 10
			If Len(Spannen(I))>0 Then
				gefunden = True   ' gefunden
				'os 02.09.2013 PRÜFEN OB DIE SPANNFUNKTIONEN RICHTIG SIND 
				'AENDERUNG OS 10.09.2013 Für Maschine Romankowski ausgeschaltet 
				'If (Trim(Spannen(I))="M51") Or (Trim(Spannen(I))="M52") Then
				'	Links=True
				'End If
				'If (Trim(Spannen(I))="M52") Or (Trim(Spannen(I))="M54") Then
				'	Rechts=True
				'End If
				'wcnc(Spannen(I))
				If NR>0 Then
					StringListAdd(NR,Spannen(I))
				Else
					wcnc(Spannen(I))
				End If
			End If
		Next I
		
		If Not gefunden Then
			AddMistake("Spannkreise nicht gefunden!")
		End If
		
		gefunden = True
		If Not gefunden Then
			If JobPara.activ_fields=1 Then
				wcnc("M51")
				If is_WorkC_OptionBit(1,JobPara.WorkC_OptionBit) Then
					' 2. Station dazu
					wcnc("M52")
				End If
				If is_WorkC_OptionBit(2,JobPara.WorkC_OptionBit) Then
					' Sauger dazu
					If Not is_WorkC_OptionBit(7,JobPara.WorkC_OptionBit)Then
						wcnc("M53")
					End If
					If Not is_WorkC_OptionBit(8,JobPara.WorkC_OptionBit)Then
						wcnc("M54")
					End If
					
				End If
				wcnc("H35")
				wcnc("H37")
			ElseIf JobPara.activ_fields=2 Then
				wcnc("M56")
					If is_WorkC_OptionBit(1,JobPara.WorkC_OptionBit) Then
					' 2. Station dazu
					 wcnc("M55")
					End If
				If is_WorkC_OptionBit(2,JobPara.WorkC_OptionBit) Then
					' Sauger dazu
					If Not is_WorkC_OptionBit(7,JobPara.WorkC_OptionBit)Then
						wcnc("M58")
					End If
					If Not is_WorkC_OptionBit(8,JobPara.WorkC_OptionBit)Then
						wcnc("M57")
					End If
				End If
				wcnc("H39")
				wcnc("H41")
			ElseIf JobPara.activ_fields=3 Then
				wcnc("M51")
				wcnc("M52")
				wcnc("M55")
				wcnc("M56")	
				If is_WorkC_OptionBit(2,JobPara.WorkC_OptionBit) Then
					' Sauger dazu
					wcnc("M53")					
					wcnc("M54")
					wcnc("M57")
					wcnc("M58")
				End If
				wcnc("H35 H37")
				wcnc("H39 H41")
			Else	
				AddMistake(GetErrMsg(234107,"_activ fields ?",1))
			End If
	
		End If
		
	'AENDERUNG os 02.09.2013 PRÜFEN OB DIE SPANNFUNKTIONEN RICHTIG SIND 
	'AENDERUNG OS 10.09.2013 Für Maschine Romankowski ausgeschaltet Weil faktisch jeweils nur ein funktion da ist. 
	'	If JobPara.activ_fields=1 Then
	'		If Links=True And Not(Rechts) Then
	'			If NCNameGlobal<>"Field1" Then
	'				AddMistake("M5x Error Wrong NC Programm Field1!")
	'			End If
	'		Else
	'			AddMistake("M5x Error Wrong NC Programm Field1!")
	'		End If
	'		
	'	ElseIf JobPara.activ_fields=2 Then
	'		If Not(Links) And Rechts Then
	'			If NCNameGlobal<>"Field2" Then
	'				AddMistake("M5x Error Wrong NC Programm Field2!")
	'			End If
	'		Else
	'			AddMistake("M5x Error Wrong NC Programm Field2!")
	'		End If
	'	ElseIf JobPara.activ_fields=3 Then
	'		If Links And Rechts Then
	'			If NCNameGlobal<>"Field1" Then
	'				AddMistake("M5x Error Wrong NC Programm Field12!")
	'			End If
	'		Else
	'			AddMistake("M5x Error Wrong NC Programm Field2!")
	'		End If
	'	Else	
	'		AddMistake(GetErrMsg(234107,"_activ fields ?",1))
	'	End If
	
End Function

'Wahlweise als WCNC oder schreiben in die Aktuelle Stringliste.
Function vacuum_entspannen(NR)
Dim I As Long 
Dim gefunden As Boolean


		wcncCom("--- Vakuum lösen")
	
		' Vakuum entspannen / lösen 
		For I = 0 To 10
			If Len(EntSpannen(I))>0 Then
				'wcnc(EntSpannen(I))
				If NR>0 Then
					StringListAdd(NR,EntSpannen(I))
				Else
					wcnc(EntSpannen(I))
				End If
				gefunden = True
			End If
		Next I
		
		
	gefunden = True
	If Not gefunden Then
		If JobPara.activ_fields=1 Then
			
			If is_WorkC_OptionBit(2,JobPara.WorkC_OptionBit) Then
				If is_WorkC_OptionBit(3,JobPara.WorkC_OptionBit) Then
					If Not is_WorkC_OptionBit(7,JobPara.WorkC_OptionBit)Then
						wcnc("M143")
					End If
					If Not is_WorkC_OptionBit(8,JobPara.WorkC_OptionBit)Then
						wcnc("M144")
					End If
				Else
					wcnc("M141")
					If is_WorkC_OptionBit(1,JobPara.WorkC_OptionBit) Then
						wcnc("M142")
					End If
					If Not is_WorkC_OptionBit(7,JobPara.WorkC_OptionBit)Then
						wcnc("M143")
					End If
					If Not is_WorkC_OptionBit(8,JobPara.WorkC_OptionBit)Then
						wcnc("M144")
					End If
				End If
			Else
				If Not(is_WorkC_OptionBit(3,JobPara.WorkC_OptionBit)) Then
					wcnc("M141")
					If is_WorkC_OptionBit(1,JobPara.WorkC_OptionBit) Then
						wcnc("M142")
					End If	
				End If
			End If
			

		ElseIf JobPara.activ_fields=2 Then

			If is_WorkC_OptionBit(2,JobPara.WorkC_OptionBit) Then
				If is_WorkC_OptionBit(3,JobPara.WorkC_OptionBit) Then
					If Not is_WorkC_OptionBit(7,JobPara.WorkC_OptionBit)Then
						wcnc("M147")
					End If
					If Not is_WorkC_OptionBit(8,JobPara.WorkC_OptionBit)Then
						wcnc("M148")
					End If
				Else
					wcnc("M146")
					If is_WorkC_OptionBit(1,JobPara.WorkC_OptionBit) Then
						wcnc("M145")
					End If
					If Not is_WorkC_OptionBit(7,JobPara.WorkC_OptionBit)Then
						wcnc("M148")
					End If
					If Not is_WorkC_OptionBit(8,JobPara.WorkC_OptionBit)Then
						wcnc("M147")
					End If
				End If
			Else
				If Not(is_WorkC_OptionBit(3,JobPara.WorkC_OptionBit)) Then
					wcnc("M146")
					If is_WorkC_OptionBit(1,JobPara.WorkC_OptionBit) Then
						wcnc("M145")
					End If
				End If
			End If
		ElseIf JobPara.activ_fields=3 Then

			If is_WorkC_OptionBit(2,JobPara.WorkC_OptionBit) Then
				If is_WorkC_OptionBit(3,JobPara.WorkC_OptionBit) Then
					wcnc("M143")
					wcnc("M144")
					wcnc("M147")
					wcnc("M148")
				Else
					wcnc("M141")
					wcnc("M142")
					wcnc("M143")
					wcnc("M144")
					wcnc("M145")
					wcnc("M146")
					wcnc("M147")
					wcnc("M148")
				End If
			Else
				If Not(is_WorkC_OptionBit(3,JobPara.WorkC_OptionBit)) Then
					wcnc("M141")
					wcnc("M142")
					wcnc("M145")
					wcnc("M146")
				End If
			End If
		Else	
			AddMistake(GetErrMsg(234107,"_activ fields ?",1))
		End If
	
	End If
		
	
End Function

'Wahlweise als WCNC oder schreiben in die Aktuelle Stringliste.
Function pneumatik_entspannen(NR)
Dim I As Long 
Dim gefunden As Boolean
	
		wcncCom("--- Pneumatik entspannen")
	
		' pneum. entspannen / lösen 
		For I = 0 To 10
			If Len(PneumEntSpannen(I))>0 Then
				'wcnc(PneumEntSpannen(I))
				If NR>0 Then
					StringListAdd(NR,PneumEntSpannen(i))
				Else
					wcnc(PneumEntSpannen(i))
				End If
				gefunden = True
			End If
		Next i

	'gefunden = True
	If Not gefunden Then	
		AddMistake("No Pneumatic to Unclamp")
	End If

End Function
'Wahlweise als WCNC oder schreiben in die Aktuelle Stringliste.
Function Pfosten_entspannen(NR)
Dim i As Long 
Dim gefunden As Boolean
	
		wcncCom("--- Pfosten entspannen")
	
		' pneum. entspannen / lösen 
		For i = 0 To 10
			If Len(PfoEntSpannen(i))>0 Then
				'wcnc(PneumEntSpannen(I))
				If NR>0 Then
					StringListAdd(NR,PfoEntSpannen(I))
				Else
					wcnc(PfoEntSpannen(I))
				End If
				gefunden = True
			End If
		Next I

	'gefunden = True
	If Not gefunden Then	
		AddMistake("No Post to Unclamp")
	End If

End Function

'Wahlweise als WCNC oder schreiben in die Aktuelle Stringliste.
Function Pfosten_spannen(NR)
Dim I As Long 
Dim gefunden As Boolean
	
		wcncCom("--- Pfosten spannen")
	
		' pneum. entspannen / lösen 
		For I = 0 To 10
			If Len(PfoSpannen(I))>0 Then
				'wcnc(PneumEntSpannen(I))
				If NR>0 Then
					StringListAdd(NR,PfoSpannen(I))
				Else
					wcnc(PfoSpannen(I))
				End If
				gefunden = True
			End If
		Next I

	'gefunden = True
	If Not gefunden Then	
		AddMistake("No Post to clamp")
	End If

End Function

'Wahlweise als WCNC oder schreiben in die Aktuelle Stringliste.
Function Anschlaege_hoch(NR)

Dim I As Long 
Dim gefunden As Boolean


wcncCom("--- Anschläge hoch ...")
For I = 0 To 10
	If Len(Anschlag_up(I))>0 Then
		'wcnc(Anschlag_up(I))
		If NR>0 Then
			StringListAdd(NR,Anschlag_up(I))
		Else
			wcnc(Anschlag_up(I))
		End If
		gefunden = True
	End If
Next I


End Function

'Wahlweise als WCNC oder schreiben in die Aktuelle Stringliste.
Function Anschlaege_runterAll(NR)

Dim I As Long 
Dim gefunden As Boolean

wcncCom("--- Anschläge Runter All...")

	For I = 0 To 10
		If Len(Anschlag_downAll(I))>0 Then
			'wcnc(Anschlag_downAll(I))
			gefunden = True
			If NR>0 Then
				StringListAdd(NR,Anschlag_downAll(I))
			Else
				wcnc(Anschlag_downAll(I))
			End If
		End If
	Next I

End Function

'Wahlweise als WCNC oder schreiben in die Aktuelle Stringliste.
Function Anschlaege_runter(NR)

Dim I As Long 
Dim gefunden As Boolean

wcncCom("--- Anschläge Runter Used...")

	For I = 0 To 10
		If Len(Anschlag_down(I))>0 Then
			'wcnc(Anschlag_down(I))
			gefunden = True
			If NR>0 Then
				StringListAdd(NR,Anschlag_down(I))
			Else
				wcnc(Anschlag_down(I))
			End If
		End If
	Next I

End Function

'Wahlweise als WCNC oder schreiben in die Aktuelle Stringliste.
Function Unterstuetzer_hoch(NR)

Dim I As Long 
Dim gefunden As Boolean

wcncCom("--- Unterstützer hoch ...")

For I = 0 To 10
	If Len(Supporters_Up(I))>0 Then
		'wcnc(Supporters_Up(I))	
		If NR>0 Then
			StringListAdd(NR,Supporters_Up(I))
		Else
			wcnc(Supporters_Up(I))
		End If
		gefunden = True
	End If
Next I


End Function

'Wahlweise als WCNC oder schreiben in die Aktuelle Stringliste.
Function Unterstuetzer_runter(NR)

Dim I As Long 
Dim gefunden As Boolean

wcncCom("--- Anschläge hoch ...")

For I = 0 To 10
	If Len(Supporters_down(I))>0 Then
		'wcnc(Supporters_down(I))
		If NR>0 Then
			StringListAdd(NR,Supporters_down(I))
		Else
			wcnc(Supporters_down(I))
		End If
		gefunden = True
	End If
Next I


End Function


Function WKS_Spannen
Dim I,K As Integer 

Dim mcd_zp As IZeroPoint

	'WKS_Spannen_Spez
	' --
	' -- Modified  MW 17.07.2008 14:40:23
	' --
	' -- Neu mit Bitschalter
	If Not MCDATA.Additions.GetAddition_ID(80000) Is Nothing Then
		JobPara.WorkC_OptionBit = Val(MCDATA.Additions.GetAddition_ID(80000).Value)
	Else	
		AddMistake("Falsche Einstellung in PP.INI - Option Bits nicht gesetzt!")
	End If
	wcncCom("Bitmode: "+FToS(JobPara.WorkC_OptionBit))
	
	'Global Const VacOffAtEnd=1		'Switchen der Optionsbits Vakuum aus am ende des programms
	'Global Const PneuOffAtEnd=2		'Pneumatik aus am ende des Programms
	'Global Const PinsUpAtEnd=3		'Anschläge Hoch am ende des Programms
	'Global Const IsNestingMode=4	'Maschen Läuft im nesting Modus
	
	If is_WorkC_OptionBit(VacOffAtEnd,JobPara.WorkC_OptionBit) Then
		' 1. Bit
		wcncCom("Vacuum Off @End of Pgm.")
	End If
	If is_WorkC_OptionBit(PinsUpAtEnd,JobPara.WorkC_OptionBit) Then
		' 2. Bit		
		wcncCom("Pins Up@End of Pgm.")
	End If
	If is_WorkC_OptionBit(PneuOffAtEnd,JobPara.WorkC_OptionBit) Then
		' 3. Bit		
		wcncCom("Penumatic Off @End of Pgm.")
	End If
	If is_WorkC_OptionBit(IsNestingMode,JobPara.WorkC_OptionBit) Then
		' 4. Bit		
		wcncCom("Nestingmodus is Used.")
	End If  
	
	If GTableType<>1 Then
		If is_WorkC_OptionBit(SuppsUpAtStart,JobPara.WorkC_OptionBit) Then 
			Unterstuetzer_hoch(0)
		End If
		If is_WorkC_OptionBit(PinsUpAtStart,JobPara.WorkC_OptionBit) Then
			'wcnc("M50")
			'wcnc("STOPRE")
			'wcnc("G04 f3")
			Anschlaege_hoch(0)
			If is_WorkC_OptionBit(PinsUpSonder,JobPara.WorkC_OptionBit) Then 
				wcnc("H38")
			End If
			
		End If
		'If is_WorkC_OptionBit(3,JobPara.WorkC_OptionBit) Then
		'	wcnc("M50")
		'	wcnc("M102")
		'	wcnc("STOPRE")
		'	For I=1 To 22 Step 1
		'		wcnc(PinTischPins.Pins(I))
		'	Next I
		'	wcnc(PinTischPins.PinsUp)
		'	wcnc("STOPRE")
		'	wcnc(PinTischPins.VerweilZeit)
		'	wcnc("STOPRE")
		'	wcnc(PinTischPins.Unterstuetzer)
		'	wcnc("STOPRE")
		'End If
		
		If is_WorkC_OptionBit(SuppsUpAtStart,JobPara.WorkC_OptionBit) Or is_WorkC_OptionBit(PinsUpAtStart,JobPara.WorkC_OptionBit) Then
			wcnc("G04F2")
			wcnc("STOPRE")
			wcnc("M00")
		End If
	End If
	
    
	wcncCom("--- Supps down")
	Unterstuetzer_runter(0)
	
	
	' Alle belegten Anschläge weg
	wcncCom("--- Stops down")
	Anschlaege_runterAll(0)

	wcncCom("---")
    
	'Vacuumkontrolle An
	If is_WorkC_OptionBit(UsePfosten,JobPara.WorkC_OptionBit) Then
		Pfosten_spannen(0)
	Else
		vacuum_on(0)
	End If

	wcncCom("---")
    
	If is_WorkC_OptionBit(UseSTransp,JobPara.WorkC_OptionBit) Then
		wcnc(Marker.TranspOn)
	End If



End Function

Sub Spruehen_EIN(Luft, Nebel)

	If Luft=1 Then 
		wcnc("M79")
	'ElseIf Luft=2 Then
	'	wcnc("M77")
	'ElseIf Luft=12 Then
	'	wcnc("M75 M77")

	Else
		If Luft<>0 Then AddMistake("Nur 1 erlaubt!")
	End If
	
	If Nebel=1 Then 
		wcnc("M161")
	Else
		If Nebel<>0 Then AddMistake("Nur 1 erlaubt!")
	End If
End Sub


Sub SetBlasen()
	If SpindleBlowNozzle.Nozzle<>SpindleBlowNozzle.LNozzle Then
		If SpindleBlowNozzle.LNozzle=1 Then
			wcnc("M78; Blasdüse an Spindel Aus")
			SpindleBlowNozzle.LNozzle=0
			SpindleBlowNozzle.Blow=False
		End If
		If SpindleBlowNozzle.Nozzle=1 Then
			wcnc("M79; Blasüse an Spindel ein")
			SpindleBlowNozzle.LNozzle=1
		End If
	End If
End Sub

Sub Blasen_AUS
	SpindleBlowNozzle.Nozzle=0
	Call SetBlasen()
End Sub

Sub SetBlasenSaw()
	If SawBlowNozzle.Nozzle<>SawBlowNozzle.LNozzle Then
		If SawBlowNozzle.LNozzle=1 Then
			wcnc("M58; Blasdüse an Sägel Aus")
			SawBlowNozzle.LNozzle=0
			SpindleBlowNozzle.Blow=False
		End If
		If SawBlowNozzle.Nozzle=1 Then
			wcnc("M59; Blasüse an Säge ein")
			SawBlowNozzle.LNozzle=1
		End If
	End If
End Sub

Sub BlasenSaw_AUS
	SawBlowNozzle.Nozzle=0
	Call SetBlasenSaw()
End Sub

Sub HaubeBac3A
		If Haube.P3AchsAktiv Then 
			wcncCom("3-AchsHaube zurücklegen! Typ:"+FToS(Actt.H_Add.HaubeTyp3Achs) )
			'wSafetyPart
			If Not Z_Is_SafetyPart Then
				wSafetyPart
				'Z_IS_Safetypart=True
				'Firsttime_Viewchange=True	
			End If
			wcnc("Stopre")
			'wcnc("G0 "+ActT.PH_Add.TipAxisName+"="+FToS(0)+" "+ActT.PH_Add.RotAxisName+"="+FToS(ActT.PH_Add.Haube3AchsCPos))
			wcnc("G0 B="+FToS(0)+" C="+FToS(ActT.H_Add.Haube3AchsCPos))
			AddMistake("Check Function")
			wcnc("Stopre")
			If Actt.H_Add.HaubeTyp3Achs=1 Then
				wcnc("C_A3_HAUBENPOS(0,0)")
			ElseIf Actt.H_Add.HaubeTyp3Achs=2 Then
				wcnc("C_A3_HAUBENPOS(0,0)")
			ElseIf Actt.H_Add.HaubeTyp3Achs=3 Then
				wcnc("C_A3_HAUBENPOS(0,0)")
			End If
			Haube.P3AchsAktiv=False
			If Not(Haube.P3AchsTc) Then
				Haube.P3AchsUseit=False
			Else
				Haube.P3AchsTc=False	
			End If
			Haube.P3AchsLastPos=-9999
			Haube.P3AchsRetreat=True
		End If
End Sub
Sub HaubeBac5A
	If Haube.P5AchsAktiv Or Haube.PLeitblechAktiv Then 
		wcncCom("5-AchsHaube zurücklegen! Typ:"+FToS(Actt.H_Add.HaubeTyp5Achs) )
		If Actt.H_Add.HaubeTyp5Achs=1 Then
			wcnc("C_A5_HAUBENPOS0,0)")
		ElseIf Actt.H_Add.HaubeTyp5Achs=2 Then
			wcnc("C_A5_HAUBENPOS(0,0)")
		ElseIf Actt.H_Add.HaubeTyp5Achs=3 Then
			wcnc("C_A5_HAUBENPOS(0,0)")
		ElseIf Actt.H_Add.HaubeTyp5Achs=4 Or Actt.H_Add.HaubeTyp5Achs=5 Then
			wcnc("C_HAUBENPOS(0,0,0,0,0,0)")
		End If
		Haube.P5AchsAktiv=False
		If Not(Haube.P5AchsTc) Then
			Haube.P5AchsUseit=False
		Else
			Haube.P5AchsTc=False	
		End If
		Haube.P5AchsLastPos=-9999
		'Haube.P5AchsTc=True
		'If Not(Haube.P5AchsTc) Then
		If Not(Haube.PLeitblechTc) Then	
			Haube.PLeitBlechUseIT=False
		Else
			Haube.PLeitblechTc=False	
		End If
		Haube.PLeitblechAktiv=False
		Haube.PLeitblechLastPos=-9999
		Haube.PleitblechLastDist=-9999
	End If
End Sub
Sub HaubeBacDH
	If Haube.PDHAktiv Then 
		wcncCom("5-AchsHaube zurücklegen! Typ:"+FToS(Actt.H_Add.HaubeTypDH) )
		If Actt.H_Add.HaubeTypDH=1 Then
			wcnc("C_DH_HAUBENPOS(0,0)")
		End If
		Haube.PDHAktiv=False
		If Not(Haube.PDHTc) Then
			Haube.PDHUseit=False
		Else
			Haube.PDHTc=False	
		End If
		Haube.PDHLastPos=-9999
		Haube.PDHTc=True
	End If
End Sub

Sub HaubeVor3A

	wcncCom("3-AchsHaube Vorlegen! Typ:"+FToS(Actt.H_Add.HaubeTyp3Achs) )
	If Actt.H_Add.HaubeTyp3Achs=1 Then
		If (Haube.P3AchsLastPos<>Haube.P3AchsPos) Then
			'wSafetyPart
			If Haube.P3AchsLastPos = -9999 Then
				If Not Z_Is_SafetyPart Then
					wSafetyPart
					Haube.P3AchsRetreat=True
				End If
			End If
			wcnc("Stopre")
			'wcnc("G0 "+ActT.H_Add.TipAxisName+"="+FToS(0)+" "+ActT.H_Add.RotAxisName+"="+FToS(ActT.H_Add.Haube3AchsCPos))
			wcnc("G0 B="+FToS(0)+" C="+FToS(ActT.H_Add.Haube3AchsCPos))
			AddMistake("Check Function")
			wcnc("Stopre")
			wcnc("C_A3_HAUBENPOS(1,1)")
		End If
	ElseIf Actt.H_Add.HaubeTyp3Achs=2 Then
		If (Haube.P3AchsLastPos<>Haube.P3AchsPos) Then 
			If Haube.P3AchsLastPos = -9999 Then
				If Not Z_Is_SafetyPart Then
					wSafetyPart
					Haube.P3AchsRetreat=True
				End If
			End If
			wcnc("Stopre")
			'wcnc("G0 "+ActT.H_Add.TipAxisName+"="+FToS(0)+" "+ActT.H_Add.RotAxisName+"="+FToS(ActT.H_Add.Haube3AchsCPos))
			wcnc("G0 B="+FToS(0)+" C="+FToS(ActT.H_Add.Haube3AchsCPos))
			AddMistake("Check Function")
			wcnc("Stopre")
			wcnc("C_A3_HAUBENPOS(1,"+FToS(Haube.P3AchsPos)+")")
		End If
	ElseIf Actt.H_Add.HaubeTyp3Achs=3 Then
		If (Haube.P3AchsLastPos<>Haube.P3AchsPos) Then 
			If Haube.P3AchsLastPos = -9999 Then
				If Not Z_Is_SafetyPart Then
					wSafetyPart
					Haube.P3AchsRetreat=True
				End If
			End If
			wcnc("Stopre")
			'wcnc("G0 "+ActT.H_Add.TipAxisName+"="+FToS(0)+" "+ActT.H_Add.RotAxisName+"="+FToS(ActT.H_Add.Haube3AchsCPos))
			wcnc("G0 B="+FToS(0)+" C="+FToS(ActT.H_Add.Haube3AchsCPos))
			AddMistake("Check Function")
			wcnc("Stopre")
			wcnc("C_A3_HAUBENPOS(1,"+FToS(Haube.P3AchsPos)+")")
		End If
	End If
	Haube.P3AchsAktiv=True
	Haube.P3AchsLastPos=Haube.P3AchsPos
End Sub
Sub HaubeVor5A
	Dim TipAng As Double
	
'	If  Surface_Mill.activ Then
'		TipAng=Surface_Mill.KW
'	ElseIf mill_c.activ Then
'		TipAng=Mill_C.KW
'	Else
'		TipAng=ActV.TipA
'	'End If
	' ToCheck OS/MW
	If Abs(PPara.MinTipA) > Abs(PPara.MaxTipA) Then
		TipAng = Abs(PPara.MinTipA)
	Else
		TipAng = Abs(PPara.MaxTipA)
	End If
	
	wcncCom("5-AchsHaube Vorlegen! Typ:"+FToS(Actt.H_Add.HaubeTyp5Achs) )
	If Actt.H_Add.HaubeTyp5Achs=1 Then
		If (Haube.P5AchsLastPos<>Haube.P5AchsPos) Or Haube.Isebene0=False Then 
			wcnc("C_A5_HAUBENPOS(1,1)")
		End If
		Haube.P5AchsAktiv=True
	ElseIf Actt.H_Add.HaubeTyp5Achs=2 Then
		If (Haube.P5AchsLastPos<>Haube.P5AchsPos) Or Haube.Isebene0=False  Then 
			wcnc("C_A5_HAUBENPOS(1,"+FToS(Haube.P5AchsPos)+")")
		End If
		Haube.P5AchsAktiv=True
	ElseIf Actt.H_Add.HaubeTyp5Achs=3 Then
		If (Haube.P5AchsLastPos<>Haube.P5AchsPos) Or Haube.Isebene0=False Or (TipAng<>Haube.LastTipAng) Then
			wcnc("C_A5_HAUBENPOS(1,"+FToS(Haube.P5AchsPos)+","+FToS(Abs(TipAng))+ ")")
		End If	
		Haube.P5AchsAktiv=True
	ElseIf Actt.H_Add.HaubeTyp5Achs=4 Or Actt.H_Add.HaubeTyp5Achs=5 Then
		If (Haube.P5AchsLastPos<>Haube.P5AchsPos) Or (Haube.PLeitblechLastPos<>Haube.PLeitblechPos) Or Haube.Isebene0=False Or (TipAng<>Haube.LastTipAng) Or (Haube.PLeitblechAktiv<>Haube.PLeitBlechUseIT) Or (Haube.P5AchsAktiv<>Haube.P5AchsUseIT) Then
			If PPara.MMode=1 And Actt.H_Add.HaubeTyp5Achs=5 Then
				If Haube.PLeitBlechUseIT And Haube.P5AchsUseIT Then
					Call MT_Write_Act_D_Correction
					wcnc("C_HAUBENPOS(1,"+FToS(Haube.P5AchsPos)+","+FToS(Abs(TipAng))+ ",1,"+FToS(Haube.PLeitBlechPos)+","+FToS(Haube.PLeitBlechDist)+");Hier Das leiblech mit ausgeben")
					Haube.PLeitblechAktiv=True
					Haube.P5AchsAktiv=True
				ElseIf Haube.PLeitBlechUseIT Then
					Call MT_Write_Act_D_Correction
					wcnc("C_HAUBENPOS(0,"+FToS(0)+","+FToS(Abs(0))+ ",1,"+FToS(Haube.PLeitBlechPos)+","+FToS(Haube.PLeitBlechDist)+");Hier Das leiblech mit ausgeben")
					Haube.PLeitblechAktiv=True
					Haube.P5AchsAktiv=False				
				ElseIf Haube.P5AchsUseIT Then
					Call MT_Write_Act_D_Correction
					wcnc("C_HAUBENPOS(1,"+FToS(Haube.P5AchsPos)+","+FToS(Abs(TipAng))+ ",0,"+FToS(0)+","+FToS(0)+");Hier Das leiblech mit ausgeben")
					Haube.PLeitblechAktiv=False
					Haube.P5AchsAktiv=True				
				End If
				
			Else
				If Haube.P5AchsUseIT Then 
					Call MT_Write_Act_D_Correction
					wcnc("C_HAUBENPOS(1,"+FToS(Haube.P5AchsPos)+","+FToS(Abs(TipAng))+ ",0,0,0)")
					'Haube.PLeitBlechUseIT=False
					Haube.P5AchsAktiv=True
				ElseIf Not(Haube.P5AchsUseIT) Then
					Call MT_Write_Act_D_Correction
					wcnc("C_HAUBENPOS(0,"+FToS(0)+","+FToS(Abs(0))+ ",0,0,0)")
					Haube.P5AchsAktiv=False
					
				End If
				
				Haube.PLeitblechAktiv=False
				Haube.PLeitblechPos=-9999
				Haube.PleitblechDist=-9999 
					
			End If
		End If
	
	End If
	'Haube.P5AchsAktiv=True
	Haube.P5AchsLastPos=Haube.P5AchsPos
	Haube.PLeitblechLastPos=Haube.PLeitblechPos
	Haube.PleitblechLastDist=Haube.PleitblechDist
	Haube.LastTipAng=TipAng
End Sub

Sub HaubeVorDH

	wcncCom("DrillHead-Haube Vorlegen! Typ:"+FToS(Actt.H_Add.HaubeTypDH) )
	If Actt.H_Add.HaubeTypDH=1 Then
		If (Haube.PDHLastPos<>Haube.PDHPos) Or Haube.Isebene0=False Then 
			wcnc("C_DH_HAUBENPOS(1,1)")
		End If
	End If
	Haube.PDHAktiv=True
	Haube.PDHLastPos=Haube.PDHPos
	
End Sub

Sub CheckHaube

	'Rückzug Haube
	If Haube.Pos<0 Then
		Call HaubeBac3A
		Call HaubeBac5A
		Call HaubeBacDH
	'Vorlegen Haube
	Else
	
		'3 Achshaube
		If Actt.H_Add.HaubeTyp3Achs>0 Then 								'Haube vorhanden?
			If Actt.H_Add.HaubeMaxToolRad3Achs>=Actt.t.CollRadius Then		'Haube hält den Collrad ein?
				If Haube.IsEbene0 Then
					If Haube.P3AchsUseIt Then
						Call HaubeVor3A
					End If
				End If
			End If
		End If
		If Haube.P3AchsUseIt=False Then
			Call HaubeBac3A	
		End If
		If Not(Haube.P3AchsAktiv) Then
			Haube.P3AchsAktiv=False
			Haube.P3AchsUseit=False
			Haube.P3AchsTc=False	
			Haube.P3AchsLastPos=-9999
			Haube.P3AchsTc=False
		End If			
	
		
		'5 Achshaube
		
		If Actt.H_Add.HaubeTyp5Achs>0 Then 								'Haube vorhanden?
			If Actt.H_Add.HaubeMaxToolRad5Achs>=Actt.t.CollRadius Then		'Haube hält den Collrad ein?
				If Haube.IsEbene0 Then
					If Not MT_Is_UndersideTool(Actt) Then
						If Not(MT_IsAnyGearboxTool(Actt)) Or (MT_IsGearboxTool(Actt) And (ActV.View=0)) Then
							If Haube.P5AchsUseIt Or Haube.PleitblechUseIt Then
								Call HaubeVor5A
							End If
						End If
					End If
				End If
			End If
		End If
		If Haube.P5AchsUseIt=False And Haube.PleitblechUseIt=False Then
			Call HaubeBac5A	
		End If
		If Not(Haube.P5AchsAktiv) Then
			Haube.P5AchsAktiv=False
			Haube.P5AchsUseit=False
			Haube.P5AchsTc=False	
			Haube.P5AchsLastPos=-9999
			Haube.P5AchsTc=False
		End If
		
		If Not(Haube.PLeitblechAktiv) Then
			Haube.PLeitblechAktiv=False
			Haube.PLeitblechUseit=False
			Haube.PLeitblechTc=False	
			Haube.PLeitblechLastPos=-9999
			Haube.PLeitblechLastDist=-9999
		End If
		
		' DrillHeadHaube
		
		If Actt.H_Add.HaubeTypDH>0 Then 								'Haube vorhanden?
			If Haube.IsEbene0 Then
				If Haube.PDHUseIt Then
					Call HaubeVorDH
				End If
			End If
		End If
		If Haube.PDHUseIt=False Then
			Call HaubeBacDH
		End If
		If Not(Haube.PDHAktiv) Then
			Haube.PDHAktiv=False
			Haube.PDHUseit=False
			Haube.PDHTc=False	
			Haube.PDHLastPos=-9999
			Haube.PDHTc=False
		End If
	End If
	If Haube.PLeitblechAktiv And (Not (PPara.MMode=1)) Then
	
		AddMistake("Fräsen ohen C-Achse mit Leitblechhaube! Leitblech Zurücklegen!")
	End If
	
End Sub
Sub CheckHaube2

	'Rückzug Haube
	If Haube.Pos=0 Then
		Call HaubeBac3A
		Call HaubeBac5A
	'Vorlegen Haube
	Else
		If Haube.P3AchsUseIt=True And Haube.P3AchsAktiv=False Then 
			If Actt.H_Add.HaubeMaxToolRad3Achs>=Actt.t.CollRadius And Haube.IsEbene0 Then
				wcncCom("3-AchsHaube Vorlegen! Typ:"+FToS(Actt.H_Add.HaubeTyp3Achs) )
				If Actt.H_Add.HaubeTyp3Achs=1 Then
					If (Haube.P3AchsLastPos<>Haube.P3AchsPos) Then
						'wSafetyPart
						If Haube.P3AchsLastPos = -9999 Then
							If Not Z_Is_SafetyPart Then
								wSafetyPart
								Haube.P3AchsRetreat=True
							End If
						End If
						wcnc("Stopre")
						'wcnc("G0 "+ActT.PH_Add.TipAxisName+"="+FToS(0)+" "+ActT.PH_Add.RotAxisName+"="+FToS(ActT.PH_Add.Haube3AchsCPos))
						wcnc("G0 B="+FToS(0)+" C="+FToS(ActT.H_Add.Haube3AchsCPos))
						AddMistake("Check Function")
						wcnc("Stopre")
						wcnc("C_A3_HAUBENPOS(1,1)")
					End If
				ElseIf Actt.H_Add.HaubeTyp3Achs=2 Then
					If (Haube.P3AchsLastPos<>Haube.P3AchsPos) Then 
						If Haube.P3AchsLastPos = -9999 Then
							If Not Z_Is_SafetyPart Then
								wSafetyPart
								Haube.P3AchsRetreat=True
							End If
						End If
						wcnc("Stopre")
						'wcnc("G0 "+ActT.PH_Add.TipAxisName+"="+FToS(0)+" "+ActT.PH_Add.RotAxisName+"="+FToS(ActT.PH_Add.Haube3AchsCPos))
						wcnc("G0 B="+FToS(0)+" C="+FToS(ActT.H_Add.Haube3AchsCPos))
						AddMistake("Check Function")
						wcnc("Stopre")
						wcnc("C_A3_HAUBENPOS(1,"+FToS(Haube.P3AchsPos)+")")
					End If
				ElseIf Actt.H_Add.HaubeTyp3Achs=3 Then
					If (Haube.P3AchsLastPos<>Haube.P3AchsPos) Then 
						If Haube.P3AchsLastPos = -9999 Then
							If Not Z_Is_SafetyPart Then
								wSafetyPart
								Haube.P3AchsRetreat=True
							End If
						End If
						wcnc("Stopre")
						'wcnc("G0 "+ActT.PH_Add.TipAxisName+"="+FToS(0)+" "+ActT.PH_Add.RotAxisName+"="+FToS(ActT.PH_Add.Haube3AchsCPos))
						wcnc("G0 B="+FToS(0)+" C="+FToS(ActT.H_Add.Haube3AchsCPos))
						AddMistake("Check Function")
						wcnc("Stopre")
						wcnc("C_A3_HAUBENPOS(1,"+FToS(Haube.P3AchsPos)+")")
					End If
				End If
				Haube.P3AchsAktiv=True
				Haube.P3AchsLastPos=Haube.P3AchsPos
			Else
				If Haube.P3AchsAktiv=True And Haube.IsEbene0=False Then
					Call HaubeBac3A	
				End If
				wcncCom("3-AchsHaube Radius zu Gross! Typ:"+FToS(Actt.H_Add.HaubeTyp3Achs) )
				Haube.P3AchsLastPos=-9999
				Haube.P3AchsAktiv=False
			End If
		ElseIf (Haube.P3AchsUseIt=True And Haube.P3AchsAktiv=True) Or (Haube.P3AchsUseIt=False And Haube.P3AchsAktiv=True) Then
			If Haube.P3AchsPos=0 Or Haube.P5AchsUseIt=False Then
				Call HaubeBac3A
			End If
		End If
		
		If (Haube.P5AchsUseIt=True And Haube.P5AchsAktiv=False) And Haube.IsEbene0 Then
			If Actt.H_Add.HaubeMaxToolRad5Achs>=Actt.t.CollRadius Then
				wcncCom("5-AchsHaube Vorlegen! Typ:"+FToS(Actt.H_Add.HaubeTyp5Achs) )
				If Actt.H_Add.HaubeTyp5Achs=1 Then
					If (Haube.P5AchsLastPos<>Haube.P5AchsPos) Or Haube.Isebene0=False Then 
						wcnc("C_A5_HAUBENPOS(1,1)")
					End If
				ElseIf Actt.H_Add.HaubeTyp5Achs=2 Then
					If (Haube.P5AchsLastPos<>Haube.P5AchsPos) Or Haube.Isebene0=False  Then 
						wcnc("C_A5_HAUBENPOS(1,"+FToS(Haube.P5AchsPos)+")")
					End If	
				ElseIf Actt.H_Add.HaubeTyp5Achs=3 Then
					If (Haube.P5AchsLastPos<>Haube.P5AchsPos) Or Haube.Isebene0=False  Then
						wcnc("C_A5_HAUBENPOS(1,"+FToS(Haube.P5AchsPos)+")")
					End If	
				End If
				Haube.P5AchsAktiv=True
				Haube.P5AchsLastPos=Haube.P5AchsPos
			Else
				wcncCom("5-AchsHaube Radius zu Gross! Typ:"+FToS(Actt.H_Add.HaubeTyp3Achs) )
				Haube.P5AchsLastPos=-9999
				Haube.P5AchsAktiv=False
			End If
		ElseIf (Haube.P5AchsUseIt=True And Haube.P5AchsAktiv=True) Or (Haube.P5AchsUseIt=False And Haube.P5AchsAktiv=True) Then
			If Haube.P5AchsPos=0 Or Haube.P5AchsUseIt=False Then
				Call HaubeBac5A	
			End If
		End If
	End If
	
	
	'Global Type THaube
	'Pos As Long				'Wird im Toolaufruf gesetzt Auto
	'IsEbene0 As Boolean  		'3-Achsbearbeitung ja/nein nur in Null ebene erlaubt
	'P3AchsUseIt As Boolean 	'Haube vorgelegt ja/nein
	'P5AchsUseIt As Boolean		'Haube vorgelegt ja/nein
	'P3AchsAktiv As Boolean 	'Haube vorgelegt ja/nein
	'P5AchsAktiv As Boolean		'Haube vorgelegt ja/nein
	'P3AchsPos As Double		'Letzte position
	'P5AchsPos As Double		'Letzte position
	'P3AchsLastPos As Double	'Letzte position
	'P5AchsLastPos As Double	'Letzte position
	'P3AchsAuto As Boolean		'Automatisch Vorlegen wenn Ebene0
	'P5AchsAuto As Boolean		'Automatisch Vorlegen wenn Ebene0
	'End Type
	
	
	'Haube.pos = MT_Get_HaubenPos
	'HaubeTyp3Achs As Long					' -- OS 02.05.2013 Typ 3-Achshaube 0=Keine/Statische 1=FixVorlegbar 2=FreiVorlegbar 3=DynVorlegbar
	'HaubeTyp5Achs As Long					' -- OS 02.05.2013 Typ 5-Achshaube 0=Keine/Statische 1=FixVorlegbar 2=FreiVorlegbar 3=DynVorlegbar
	'HaubeMaxToolRad3Achs As Double			' -- OS 02.05.2013 Typ 3-Achshaube Collradius Tool
	'HaubeMaxToolRad5Achs As Double

End Sub
Sub PrintEtikett(Para1 As Variant ,Para2 As Variant ,Para7 As Variant )
	Marker.Etikett=True
End Sub
Sub SetStrings(str1 As String )
	Dim PrintStrings(8)As String
	Dim Tempstr As String
	Dim PrintHeadLabelStatus As String
	Dim Isok As Boolean 
	Dim I,cut As Integer 
	
	Tempstr=str1
	For I=1 To 8
		cut=InStr(Tempstr,";")
		PrintStrings(I)=Mid$(Tempstr,1,cut-1)			
		If Tempstr<>"" Then
			Tempstr=Mid$(Tempstr,cut+1,Len(Tempstr))
		End If
		wcnc("STRING"+IntToS(I)+"="+Chr(34)+PrintStrings(I)+Chr(34))
	Next
	
	PrintHeadLabelStatus=MT_get_Add_ID(actT,10158,Isok)
	If Isok Then
		wcncAddCom(PrintHeadLabelStatus+"=1","Label komplett")
	Else
		AddMistake("Unbekannte Add_ID: 10158")
	End If
	wcnc("STOPRE")
End Sub
Function exponent2_v2(zahl) As Long
	exponent2_v2 = Exp(zahl*Log(2))
End Function
Function WKS_SpannenNesting(Stopp As Boolean)
 Dim I As Integer
 
	
	If Stopp=False Then
		If FieldMask.M(0) Then
			wcnc("H10="+IntToS(FieldMask.BitMask))
			wcnc("STOPRE")
			wcnc_msg("Felder: "+FieldMask.AsStr+" OK?")	
		End If
		
		If FieldMask.M(1) Then
			wcnc("H30="+IntToS(FieldMask.BitMaskR))
			wcnc("STOPRE")
			wcnc_msg("Felder: "+FieldMask.AsStrR+" OK?")
		End If
		wcnc("M0")
		wcnc_msg("")
		Anschlaege_runterAll(0)
	End If
	
	For I=0 To 3
		If FieldMask.M(I) Then
			wcnc("M5"+Trim(IntToS(I+1)))
		End If
	Next
	
End Function
Function TC_SPez

Dim T As THopsBasicToolExt
Dim TC_PlaceNo As Long 


	T=ToolArray(Marker.PNo)	
	
	If (actt.t.ID <> T.t.ID) And (MT_Is_Vertical_StandardTool5Axis(T)) Then
		If Not MT_isDH(T) And (MT_Is_TC_T(T)) Then
			If Not T.T.GetOn_TC Is Nothing Then
				' Tool - on toolchanger
				wcncCom("S0")
				If (T.h_add.traori) Then
					' 5-Axis mit Traori -
					wcncAddCom(ActT.H_Add.TraoriOff, " 5-Achs - Transformation abschalten")  ' "TRAFOOF"
				End If
				
				TC_PlaceNo = T.t.GetPlaceID_OnTC 't.T.ToolNo_Place
				
				
				wcncCom("VORWECHSEL:  " + T.t.Description + "   auf Kopf " + HeadID)
				wcncCom("C_Vorwechsel("+IntToS(HeadID)+","+IntToS(TC_PlaceNo)+")")
				
				
				'wcnc(GToolChangeCycleName+"("+IntToS(TC_PlaceNo)+")")
				'wcnc(GToolChangeCycleName+"("+IntToS(TC_PlaceNo)+","+IntToS(T.t.RotDirection)+","+IntToS(T.t.RotSpeed)+")")
			End If
		End If
	Else
		'ClampChangeParkXY	  ' Parken X / Y 
				
		'wcnc("STOPRE")	
		'wcnc(actt.PH_Add.TraoriOn)  '  "TRAORI"	

	End If
End Function
Function Param2x(NR,S)
Dim	Count As Long
Dim n As Long
Dim p As Long
Dim SSave As String
  Count = ParamCountX2(S)

  If (NR > Count) Or (NR < 1)Then
     Param2x = ""
     Exit Function
  End If

If Count = 1 Then
     Param2x = Trim(S)
     Exit Function
  End If

  If NR = 1 Then
     p= InStr(S,SEPSTR_DOT)

     Param2x = Trim (Mid(S, 1, p-1))

  ElseIf NR < Count Then
     SSave=S 
     For n = 1 To NR-1 Step 1
        SSave=delete(SSave,1,InStr(SSave,SEPSTR_DOT))
     Next n

     p= InStr(SSave,SEPSTR_DOT)
     Param2x = Trim(Mid (SSave,1, p-1))

  ElseIf NR = Count Then 
     p = InStrRev(S,SEPSTR_DOT)
     Param2x = Trim(Mid (S, p+1, Len(S)-p))

  End If
End Function


Function ParamCountX2(S)
Dim	n As Long
Dim Count As Long
 ParamCountX2=0
  Count = 0
  S= Trim(S)
  If Len(S) > 0 Then
     For n= 1 To Len(S) Step 1
        If Mid(S,n,1) = SEPSTR_DOT Then
           Count = Count + 1
        End If
     Next n
     ParamCountX2 = Count + 1
  End If
End Function
Function RotAxisDh(I)

Dim AxName As String
	
	'If actT.PH_Add.RotAxisName = "" Then
		' z.B. wenn Rückzug mit Bohrkopf 
		' dann von 1. Spindel die Achsnamen holen
 	'	AxName = TDATA.GetProcessHead_ID(1).Additions.GetAddition_ID(10011).Value
		 		
	'Else
	'	AxName = actT.PH_Add.RotAxisName
	'End If

	AddMistake("Check Function")
  RotAxisDh = " " +AxName +"=" +  FToS(NormPlusMinus_180(I))  '15.07.2014 SF +-180° normiert
  'RotAxisDh = " " +AxName +"=" +  FToS(Norm0_360(I))

End Function

Function MessBezChanged As Boolean
	
	If Marker.LastMessbezugX<>Marker.MessbezugX Or Marker.LastMessbezugY<>Marker.MessbezugY Or Marker.LastMessbezugZ<>Marker.MessbezugZ Then
		MessBezChanged=True
	ElseIf Marker.LastFaktorX<>Marker.FaktorX Or Marker.LastFaktorY<>Marker.FaktorY Or Marker.LastFaktorZ<>Marker.FaktorZ Then
		MessBezChanged=True
	Else
		MessBezChanged=False
	End If
	
End Function
Sub Reset_Messbezug()
	Marker.Messbezug=False
	Marker.LastMessbezugX=Marker.MessbezugX
	Marker.LastMessbezugY=Marker.MessbezugY
	Marker.LastMessbezugZ=Marker.MessbezugZ
	Marker.LastFaktorX=Marker.MessbezugX
	Marker.LastFaktorY=Marker.MessbezugY
	Marker.LastFaktorZ=Marker.MessbezugZ
	Marker.MessbezugX=0
	Marker.MessbezugY=0
	Marker.MessbezugZ=0
	Marker.FaktorX=0
	Marker.FaktorY=0
	Marker.FaktorZ=0
End Sub

Function MoveUs(ByVal x,ByVal Y,ByVal Z,Feedrate,TRC)

   Dim chars As String
   Dim checked_feedrate As Double
   
   chars=""

   
   ' Neu MW 20.04.2005
   ' check Vorschub 
   If Feedrate>0 Then
	   checked_feedrate = MT_CheckFeedrate(actt,x,Y,Z,LastPos.X,LastPos.Y,LastPos.Z,Feedrate)
	End If
   
   
   If (MovePara.TRC<>TRC)  Then
     chars= chars + GetTRCStr(TRC)
   End If
   If Not equal(x,LastPos.X) Then
      chars= chars + XToS(x)
   End If
   If Not equal(Y,LastPos.Y) Then
      chars= chars +  YToS(Y)
   End If
   If Not equal(Z,LastPos.Z) Then
      'chars= chars + ZToS(Z)
   End If

   If (MovePara.Feedrate<>checked_feedrate) And (checked_feedrate>0) Then
     chars= chars + GetFeedrateStr(checked_feedrate)
   End If
   Z=-9999
   Call PosSet(LastPosAbs,x,Y,Z)
   Call MoveParaSet(checked_feedrate,TRC)
   MoveUs=chars
End Function
Function Get_Hops_INI_CalcDistanceOutline As Boolean

'Dim iiSet As Object
'Dim Language As Object
  
	'Set iiSet = CreateObject("Hops_DLLInterface.HopsSettings")
	'	If iiSet.ReadInteger("EINST","CalcOffsetDefault",False)=1 Then
	'		Get_Hops_INI_CalcDistanceOutline = True
	'	Else
	'		Get_Hops_INI_CalcDistanceOutline = False
	'	End If
		
   	'Set iiSet = Nothing
	
End Function
Sub WCNC_VORWECHSEL()
	Dim Anlauf As Integer 
	Dim Dr As Integer 
	Dim Dz As Integer 
	
	'	Info_TCBT.BoxNo=BoxNo
	'	Info_TCBT.AggNo=AggNo
	'	Info_TCBT.HeadID=HeadID
	'	Info_TCBT.TC_PLACE=TCB_T.t.GetPlaceID_OnTC
	'	Info_TCBT.T_Speed=T_Speed
	'	Info_TCBT.P_Speed=P_Speed
	'	Info_TCBT.AddMx=AddMx
	'	Info_TCBT.AddMy=AddMy
	'	Info_TCBT.AddMz=AddMz
	'	Info_TCBT.SPVX=SPVX
	'	Info_TCBT.SPVY=SPVY
	'	Info_TCBT.SPVZ=SPVZ
	'	Info_TCBT.DoIt=1
	If (Not(ActT.t)Is Nothing) Then
		If MT_Is_TC_T(Actt)Then
			If Actt.t.GetPlaceID_OnTC<>Info_TCBT.TC_PLACE And Actt.Hid<>StrToFloat(Info_TCBT.HeadID) Then
				If (Info_TCBT.HeadID=info_h1.HeadID)Then
					If Info_TCBT.TC_PLACE=info_h1.TC_PLACE Then
						Info_TCBT.DoIt=1
					Else
						Info_TCBT.DoIt=1
					End If	
				ElseIf Info_TCBT.HeadID=info_h2.HeadID Then
					If Info_TCBT.TC_PLACE=info_h2.TC_PLACE Then
						Info_TCBT.DoIt=1
					Else
						Info_TCBT.DoIt=1
					End If	
				Else
					Info_TCBT.DoIt=1
				End If	
			Else
				Info_TCBT.DoIt=0
			End If
		End If	
	End If
	
	
	If Info_TCBT.DoIt>0 Then
		If Info_TCBT.BoxNo=2500 Then
			Anlauf=0
			Dz=0
			Dr=0
		Else
			'Anlauf=1
			'Dr = Info_TCBT.Dr
			'Dz = Info_TCBT.DZ
			Anlauf=0
			Dr = 0
			Dz = 0
		End If
		'wcnc("C_TSL("+")")
		wcncAddCom("C_TSL("+IntToS(Info_TCBT.TC_PLACE)+","+IntToS(Abs(Info_TCBT.MaxRotSpeed))+")","Set Speed limits for PreChange Tool!")
		wcnc("C_VORWECHSEL("+FToS(Info_TCBT.TC_PLACE)+","+FToS(Anlauf)+","+FToS(Dr)+","+FToS(Dz)+","+FToS(Info_TCBT.SPVY+Info_TCBT.AddMy)+")")
		Info_TCBT.DoIt=0
		If Info_TCBT.HeadID="1" Then
			info_h1=Info_TCBT	
		End If
		If Info_TCBT.HeadID="2" Then
			info_h2=Info_TCBT	
		End If
	End If
	
End Sub

Function Read_MPara_ADD
Dim BList(5) As Long    ' ueber Array definierbare Blacklist - nicht mehr unterstuetzte ID's
Dim I As Integer 
	BList(0) = 1006
	BList(1) = 1010
	BList(2) = 1050
	BList(3) = 1060
	BList(4) = 1015
	BList(5) = 1016
	
	For I = 0 To UBound(BList)
		If MT_Get_MachPara_Add(BList(I))<>"" Then
			pp_err(7,BList(I))
		End If
	Next I
	
	'mPara_Add.Laser_HeadID = IIf(MT_Get_MachPara_Add(1200)="",110,MT_Get_MachPara_Add(1200))
	' -
	'mPara_Add.ShowTravLPointer = IIf(MT_Get_MachPara_Add(1070)="",0,MT_Get_MachPara_Add(1070))
	'mPara_Add.ShowPadsLPointer = IIf(MT_Get_MachPara_Add(1071)="",1,MT_Get_MachPara_Add(1071))
	'mPara_Add.ShowWorkPieceContour = IIf(MT_Get_MachPara_Add(1072)="",1,MT_Get_MachPara_Add(1072))
	' -
	mPara_Add.PARK_DIST_X_Field1 = IIf(MT_Get_MachPara_Add(1130)="",500,MT_Get_MachPara_Add(1130))
	mPara_Add.PARK_DIST_X_Field2 = IIf(MT_Get_MachPara_Add(1131)="",800,MT_Get_MachPara_Add(1131))
	' - 
	'mPara_Add.sc_minfeed = 30
    'If Not MT_Get_MachPara_Add(1015)="" Then
	'	mPara_Add.sc_minfeed = StrToFloat(MT_Get_MachPara_Add(1015))
	'End If
	'mPara_Add.sc_contprec = 0.05
	'If Not MT_Get_MachPara_Add(1016)="" Then
	'	mPara_Add.sc_contprec = StrToFloat(MT_Get_MachPara_Add(1016))
	'End If
		
	' -
	'mPara_Add.KEEP_ZSIC_AFTER_TC = IIf(MT_Get_MachPara_Add(1020)="",False,MT_Get_MachPara_Add(1020))
	mPara_Add.WRITE_COMMENTS = IIf(MT_Get_MachPara_Add(1100)="",False,MT_Get_MachPara_Add(1100))
	mPara_Add.Script_Info = IIf(MT_Get_MachPara_Add(1101)="",False,MT_Get_MachPara_Add(1101))
	
	
End Function



Function wcnc_NCIExt_Strs(iNC As Object,Optional pointoftime=-1)  ' Alle Strings ueber ParaCount wegschreiben
Dim I As Long 
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
Dim I As Long 
Dim iNC As Object ' INCNCInfo
' MW 17.02.2016 
' Vorwirksame NCIExt absetzen
	For I =  0 To UBound(PPara.NCIExtB) 
		Set iNC = PPara.NCIExtB(I) 
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
	Next I

End Function

Function wcnc_NCIExt_After()
Dim I As Long 
Dim iNC As Object ' INCNCInfo
' MW 17.02.2016 
' Nachwirksame NCIExt absetzen
	For I =  0 To UBound(PPara.NCIExtA) 
		Set iNC = PPara.NCIExtA(I) 
		If Not iNC Is Nothing Then
			Select Case iNC.Kind
				Case 80000
					wcnc_NCIExt_Strs(iNC)   ' Alle Strings ueber ParaCount wegschreiben
			End Select
		End If
	Next I
	
End Function

Function wcnc_TCP_Offset_On(Kind)

	If MT_Is_Vertical_StandardTool5Axis(ActT) Then
		If (equal(Kind,-1) Or equal(Kind,1)) Then
			If Not equal(actt.h.RotPointOffZ,0) Then
				' Bezugspunkt Schnittpunkt Achsen
				' MW 21.01.2016 die folgenden Koordinaten beziehen sich immer auf die Plananlage der Spindel - Werkzeugbezugspunkt
				' MW 28.01.2016 hier muss eigentlich die ID -20001 verrechnet werden
				'wcnc("ATRANS Z="+FToS(actt.h.RotPointOffZ))
				'wcnc("ATRANS Z="+FToS(-actt.h.RotPointOffZ))
			Else
				'wcnc("ATRANZ Z="+FToS(-actt.h.RotPointOffZ),True)
			End If
		End If
	End If
	
End Function

Function wcnc_TCP_Offset_Off(Kind)
	If (MT_Is_Vertical_StandardTool5Axis(ActT)) Then
		If equal(Kind,-1) Or equal(Kind,1) Then
			If Not equal(actt.h.RotPointOffZ,0) Then
				'wcnc("ATRANS Z="+FToS(-actt.h.RotPointOffZ))
				'wcnc("ATRANS Z="+FToS(actt.h.RotPointOffZ))
			Else
				'wcnc("ATRANS Z="+FToS(actt.h.RotPointOffZ),True)
			End If
		End If
	End If
End Function


Function ClearMTData
Dim I As Integer
  MT_ClearTHopsBasicToolExt(ActT)
  MT_ClearTHopsBasicToolExt(LastT)
  MT_ClearTHopsBasicToolExt(FirstT) ' MW 24.02.2016
  MT_ClearTHopsBasicToolExt(TCB_T) ' MW 24.02.2016
  
  If CountOfTool>0 Then
	  For I = LBound(ToolArray) To UBound(ToolArray) Step 1
    	MT_ClearTHopsBasicToolExt(ToolArray(I))
	  Next I
  End If
End Function
Function Get_AktHK(Typ As Integer,SubTyp As Integer,OnOff As Boolean)As String
Dim I,j As Integer
Dim erg As String 
	erg=""
	I=Typ
	j=SubTyp
	If OnOff=True Then
		erg=HK_ON(I).P(j)
		'If Not(Actt.H_Add)Is Nothing Then
			If (Actt.H_Add.HK_ON(I).P(j)<>"") Then
				erg=Actt.H_Add.HK_ON(I).P(j)
			End If
		'End If
		If ActHK_ON<>"" Then
			erg=ActHK_ON
		End If		
	Else
		erg=HK_OFF(I).P(j)
		'If Not Actt.H_Add Is Nothing Then
			If Actt.H_Add.HK_OFF(I).P(j)<>"" Then
				erg=Actt.H_Add.HK_OFF(I).P(j)
			End If
		'End If
		If ActHK_OFF<>"" Then
			erg=ActHK_OFF
		End If
	End If	
	
	Get_AktHK=erg
End Function
Function WCNC_AcktHK(MaxPerLine As Long,OnOff As Boolean)
Dim TmpStr, TmpStr2 As String 
Dim I As Long
Const Sep="|"
'Max Perline=0 dann alle auf einmal sonst
'mehrzeilige Ausgabe OS 31.03.2016
	If OnOff Then
		TmpStr=ActHK_ON
	Else
		TmpStr=ActHK_OFF
	End If
	
	If MaxPerLine=0 Then
		wcnc(Replace(TmpStr,Sep," "))
	Else
		TmpStr2=""
		For I=1 To ParamCount_Sep(TmpStr,Sep)
			TmpStr2=TmpStr2+GetParam_Sep(I,TmpStr,Sep)+" "
			If (I Mod MaxPerLine)=0 Then
				wcnc(TmpStr2)
				TmpStr2=""
			End If
		Next I
		If TmpStr2<>"" Then
			wcnc(TmpStr2)
			TmpStr2=""
		End If
	End If
	
End Function
Function WCNC_AktSprueher(MaxPerLine As Long,OnOff As Boolean)
Dim TmpStr, TmpStr2 As String 
Dim I As Long
Const Sep="|"
'Max Perline=0 dann alle auf einmal sonst
'mehrzeilige Ausgabe OS 31.03.2016
	If OnOff Then
		TmpStr=SpruehEinr.MittelOn
	Else
		TmpStr=SpruehEinr.MittelOff
		SpruehEinr.Spruehen=False
		SpruehEinr.MittelOn=""
		SpruehEinr.MittelOFF=""
	End If

	If MaxPerLine=0 Then
		wcnc(Replace(TmpStr,Sep," "))
	Else
		TmpStr2=""
		For I=1 To ParamCount_Sep(TmpStr,Sep)
			TmpStr2=TmpStr2+GetParam_Sep(I,TmpStr,Sep)+" "
			If (I Mod MaxPerLine)=0 Then
				wcnc(TmpStr2)
				TmpStr2=""
			End If
		Next I
		If TmpStr2<>"" Then
			wcnc(TmpStr2)
			TmpStr2=""
		End If
	End If
	
End Function
Function WCNC_DLL_OnLeadInOut(Para As String,Mode As Integer, MaxPerLine As Long,Leadout As Boolean)
Dim TmpStr, TmpStr2 As String 
Dim I As Long
Const Sep="|"
'Max Perline=0 dann alle auf einmal sonst
'mehrzeilige Ausgabe OS 31.03.2016
	TmpStr=Para
	If MaxPerLine=0 Then
		TmpStr=Replace(TmpStr,Sep," ")
		If Leadout Then
			Marker.AStris.Add(TmpStr)
		Else
			Marker.BStris.Add(TmpStr)
		End If
		
	Else
		TmpStr2=""
		For I=1 To ParamCount_Sep(TmpStr,Sep)
			TmpStr2=TmpStr2+GetParam_Sep(I,TmpStr,Sep)+" "
			If (I Mod MaxPerLine)=0 Then
				If Len(Trim(TmpStr2))>0 Then
					If Leadout Then
						Marker.AStris.Add(TmpStr2)
					Else
						Marker.BStris.Add(TmpStr2)
					End If	
					TmpStr2=""
				End If
			End If
		Next I
		If TmpStr2<>"" Then
			If Len(Trim(TmpStr2))>0 Then
				If Leadout Then
					Marker.AStris.Add(TmpStr2)
				Else
					Marker.BStris.Add(TmpStr2)
				End If
				TmpStr2=""
			End If
		End If
	End If
	
End Function
Function Inc_Process
	Marker.actprocess = Marker.actprocess + 1
	If Not equal(Marker.actprocess,PPara.plno) Then
		pp_err(126)
	End If
End Function
