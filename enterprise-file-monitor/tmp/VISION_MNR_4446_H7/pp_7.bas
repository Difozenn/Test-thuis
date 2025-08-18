' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \hh7\pp_7.bas
' -- 
' -----------------------------------------
'#uses "pp_math.bas"
'#uses "pp_global.bas"
'#uses "pp_ncinfo.bas"
'#uses "pp_mt.bas"
'#uses "pp_mtf.bas"


Option Explicit

Global tTimer As Double 

Type TNCIExt
	e7251 As Boolean     ' NCIExt 7251 Wenn true "G451" ansonsten "G450" beim Fraesen - absetzen bei Start_Milling
	e7211 As Boolean     ' NCIExt 7211 Blasduese
End Type
Global NCiE As TNCIExt


Type THood
	Typ1 As Integer 
	Value1 As Double
	Mode1 As Integer
	Typ2 As Integer 
	Value2 As Double
	Mode2 As Integer
End Type

Global NCI_Ext_SH As THood

'Process Parameter
Type TProcessPara
	PLNo As Long        ' MW 30.03.2016 wird ueber ProcessIndex uebergeben
	ToolId As Long 
	Tool As Object 
	HeadInfo As Variant 
	HId As Long 
	ProcInfoStr As String  ' MW 30.03.2016
	Feedrate As Double
	I_Feedrate As Double
	S_Feedrate As Double
	Speed As Double
	'RotA As Double
	'TipA As Double
	mMode As Integer          ' MillingMode MW 11.01.2016 Parameter von AdditionalSPInfoMPs 
	ObjectTyp As Integer
	PreObjectTyp As Integer
	MinRotA As Double
	MaxRotA As Double
	MinTipA As Double
	MaxTipA As Double
	SuctionPos As Integer   ' MW 18.04.2016 Haubenpos - init setzt pos auf Einstellung der Schneide welche ueber SUB SuctionHood (NCIExt) ueberschrieben wird (-1 = Haube inaktiv)
	NCiExtB() As Object            ' Objectliste aller vorwegwirksamen NCIExt 
	NCiExtA() As Object            ' Objectliste aller nachwegwirksamen NCIExt 
	'   OSZ As sTOSZ
	NTool As Object     ' folgendes Werkzeug
	NHeadInfo As Variant  ' Head folgendes Werkzeug
	RotA As Double    ' Head Ausrichtung auf Ebene oder StartAusrichtung 
	TipA As Double
	HeadRotA As Double    ' Head Ausrichtung auf Ebene oder StartAusrichtung 
	HeadTipA As Double
	HeadSPAX As Double    ' 1. Anfahrposition in X fuer Werkzeugwechsel
	HeadSPAY As Double    ' 1. Anfahrposition in Y fuer Werkzeugwechsel
	HeadSPAZ As Double    ' 
	ProcessGroup As Long  ' MW 22.04.2016 Ermittlng der ProcessGruppe -> Neu ueber eine Engine - Funktion 
	MinX As Double        ' MW 22.04.2016 Ermittlng Min-Max der Bearbeitung -> Neu ueber eine Engine - Funktion 
	MaxX As Double 
	MinY As Double 
	MaxY As Double
	DustPosNCIExt As Boolean   ' MW 09.02.2016 NCIExt fuer Haube wurde programmiert
End Type

Global PPara As TProcessPara    ' MW 16.02.2016 hier werden unter anderem Vorschuebe, NCInfos (Haubenpos) etc. zugeordnet


Function GetStrObjectTyp(Obj) As String
Dim resu As String 
Dim objt,mode As Integer 
	resu = ""
	If (Obj.ObjectTyp = otMillingMPs) Then
		objt = Obj.PreObjectTyp
		mode = Obj.Mode
	ElseIf (Obj.ObjectTyp = otMillingPoints) Then
		objt = Obj.PreObjectTyp
		mode = Obj.MMode
	Else
		objt = Obj.ObjectTyp
	End If
	
	Select Case objt
			Case otNotdefinied
				resu= "not definied"
		    Case otNCInfo
				resu = "NCInfo"
		    Case otMilling
				resu = "Milling" + IIf(mode=1," with C-Axis",IIf(mode=2," 5Axis",""))
			Case otVertDrilling 		    
				resu = "VertDrilling"
			Case otHorzDrilling 		   
				resu = "HorzDrilling"
			Case otSawing 		    
				resu = "Sawing"
			Case otNCProcess 		    
				pp_Err(1569)  ' darf nicht vorkommen
				resu = "NCProcess"
			Case otNCInfoProcess 		    
				resu = "NCInfoProcess"
			Case otNCContourProcess 		    
				pp_Err(1569)  ' darf nicht vorkommen
				resu = "NCContourProcess"
			Case otDHProcess 		    
				resu = "DHProcess"
			Case otMillingPoints 		    
				resu = "MillingPoints"
			Case otMillingMPs		    
				resu = "MillingMPs"
			Case otNCInfoProcessMPs 
				' NCinfoProcess - ProcessKind = 1/2 = Drilling/Milling
				resu = "NCInfoProcessMPs"
	End Select 
	GetStrObjectTyp = resu
End Function

Sub INITZero_7
Dim i As Integer 
	Write_PPVersion
	Read_PPVersion
'	If GetV_Check3(Script_Version)<>GetV_Check3(Setup_Version) Then     ' auf uebereinstimmung mit dem Setup pruefen
		' Ueberpruefung, ob in der PP.INI
		' [VERSION]
		' PPSCRIPT=7.0.1.1   -> wird vom Script geschrieben
		' PPSETUP=7.0.1.0    -> wird vom PP-Setup geschrieben

		'pp_Err(1,Script_Version,Setup_Version)
'	End If

	Get_Language_info
	get_Hops_path

	INI_Check   ' Plausibilisierung auf korrekte Einstellungen der Engine
	
	For i = 1 To TDATA.MachineData.ProcessHeadsCount
		If TDATA.GetProcessHead_ID(i).RotType=atFree And TDATA.GetProcessHead_ID(i).TipType=atFree Then
		    ' Maschine mit 1. Head als 5-Achs
			JobPara.is_5Axis_Machine=True
			Exit For
		End If
	Next i
	
End Sub

' MW 01.04.2016 -> hier werden eigentlich nur noch die MinMax TipRot - Werte gesetzt
Function Add_SPInfoMPs_7(Mode,PreObjectTyp, MinRot,MaxRot,MinTipA,MaxTipA, R1, R2, R3,  R4)

	' Mode 0 : Standard
	' Mode 1 : C-Achsfraesen
	' Mode 2 : Vektorfraesen/5Achsfraesen
	If Mode=1 Then
		If equal(MinTipA,MaxTipA) Then
			' das ist der Kippwinkel fuer das C-Achsfraesen - notwendig z.B. fuer das Stellen funkgest. Stellachse (Stellung ueber aufruf eines Zyklus')
		Else
			pp_Err(1,"Angle C-Axis milling not constant")
		End If
		'mill_c.activ = True
		'MillC_INIT(True,DirectionMode,ExcessLength,Mode,AxisRotA,KW,TRC,DISTANCE,dw)			
	End If
	
	If Mode=2 Then	
'		If  equal(MinRot,MaxRot) And equal(MinTipA,MaxTipA) And equal(MinTipA,0) Then
			' dann senkrecht fraesen
			' MW 04.02.2016 - Da fuer 4-Achs kein TCP zur Verfuegung steht, muessen die Koordinaten im Bezug auf die Plananlage ausgegeben werden
'			Marker.WorkMode= 0

			'Surface_Mill.Mode=0
			'SurfaceMilling_Init(False,SurfaceMode,DirectionMode,ExcessLength,AxisRotA,KW,TRC,DISTANCE,MinRot,MaxRot,MinTipA,MaxTipA)
'		Else
'			Marker.WorkMode= Mode
			'Surface_Mill.Mode=2
			' Leitkurven - Fraesen mit kontinuierlicher Kippachse identisch Ablauf "nur" Kippachse mitschwenken..
			'SurfaceMilling_Init(True,SurfaceMode,DirectionMode,ExcessLength,AxisRotA,KW,TRC,DISTANCE,MinRot,MaxRot,MinTipA,MaxTipA)
'		End If
	End If
	If Not equal(PPara.MMode, Mode) Then
		pp_Err(126)
		PPara.MMode = Mode
	End If
	If Not equal(PPara.PreObjectTyp, PreObjectTyp) Then
		pp_Err(126)
		PPara.PreObjectTyp = PreObjectTyp
	End If
	PPara.MinRotA = MinRot 
	PPara.MaxRotA = MaxRot
	PPara.MinTipA = MinTipA
	PPara.MaxTipA = MaxTipA


	
End Function


' --------------------------------------------------------------------------------------------------------------------------------------
' DLL-Milling - zugehoerige Functions/Subs
' --------------------------------------------------------------------------------------------------------------------------------------

Function DLLMPs_Init

Const NCLineDef = "N%d"
Const G0 = "G0"
Const G1 = "G1", G2 = "G2", G3 = "G3"
Const G40 = "G40" , G41 = "G41", G42 = "G42"
Const X = "%s%s", Y = "%s%s", Z = "%s%s"
Const radG2 = "CR=%s", radG3 = "CR=%s"
Const i = "I%s", J="J%s"
Const F = "F%s"
Const TipA = "%s%s"
Const RotA ="%s%s"    ' "%s360+[%s]" so, wenn Achse negativ ausgegeben wird -> als Notloesung
'Const TipA_rel = "G91 A=%s", RotA_rel = "G91 C=%s G90"
Const TipA_rel = "B=IC(%s)", RotA_rel = "C=IC(%s)"										'relative verfahrung B/C Achse
Const ExtStr = ""
Const AbsStr = "" '
Const IncStr = "" '
'Const EB1_3_I = "I%s", EB1_3_J="J%s"
'Const EB2_4_I = "I%s", EB2_4_J="J%s"
' ------------------------------------------------------------------------------
Const SEP = "."
Const DECIMALS = 4         ' Anzahl Nachkommstellen
Const PRECISION = 0.0001   ' Genauigkeit - Pruefung letzter X/Y/Z/A/B/C = aktueller X/Y/Z/A/B/C
Const UseRadius = True
Const NCLineStep = 10
Const UseAbsIncStrForRelTipARotA = False      'false 4. und 5. Achse absolut ausgeben, true relativ dann wird incstr verwendet
Const RotInvert = True
Const TipInvert = True    ' MW 11.02.2016  False
Const XYZ_WritingMode = 0
Const FeedrateFactor = 1
Dim WriteOnlyLastPointMPsBefore As Boolean
Dim WriteNCMillingPointsHeadData As Boolean  ' bei True fuer Maschinen ohne TCP werden die Koordinaten fuer kontinuierliche Bearbeitungen (C-Axis/5-Axismilling etc.) auf den RefPoint (Drehpunkt) ausgegeben
										     ' fuer 4-Achsmaschinen muss dieser Parameter = true sein
Const WriteNCMillingPointsHeadDataTipARotA = True  ' auf den Kopf bezogen also kardanische verrechnete Achsausgabe der Dreh/KippAchse (WriteNCMillingPointsHeadData muss false sein)

	If JobPara.is_5Axis_Machine Then
		' Maschine hat TCP -> Werkzeugbezugspunkt = Werkzeugspitze
		WriteNCMillingPointsHeadData = False
	Else
		' fuer 4-Achsmaschinen muss dieser Parameter = true sein		
		WriteNCMillingPointsHeadData = True
	End If
  ' toCheck OS/MW - Diese Einstellung kann in einer kommenden Version situationsbedingt ueberschrieben werden
		
'	If JobPara.is_Evo Then
		' fuer diese Maschine muss durch die Nullpunktaenderung eigentlich nach dem Umspannen die letzte Position mit dem "Traversen"- Offset
		' verrechnet werden - dies konnte in der Engine nicht geloest werden
		' ueber diesen Parameter kann die Ausgabe des "falschen" letzten Punktes unterdrueckt werden
		' N770 ; ---  ##################### DLLMPs vor ViewChange - AGGOX:-67.79  AGGOY:-215.47  AGGOZ:-25.9 ---
		' N780 D0 G0 X=1047.79+(-778.997)-(-1789.027) Y715.47 Z=177.9
		' N790 D0 G0 X1087.79
	
'		WriteOnlyLastPointMPsBefore = True
		' MW 28.01.2016 Anmerkung ==> bei Maschinen mit Liftoffsets wird der letzte Punkt generell von der Engine unterdrueckt.
'	Else
		WriteOnlyLastPointMPsBefore = False
'	End If

'Const Drehung360 = True

	PPDLLInit("",NCData,PostSettings)
'	PPDLLInitStrings(NCLine,NCLineStep,G0,G1,G2,G3,G40,G41,G42,X,Y,Z,radG2,radG3,I,J,F,TipA,RotA,TipA_rel,RotA_rel,Absolut,RotInvert,TipInvert,ForceXY_ZChange,ExtStr,AbsStr,IncStr)
'	PPDLLInitParameter(SEP,DECIMALS,PRECISION,UseRadius)
	
	PPDLLInitStrings(NCLineDef,G0,G1,G2,G3,G40,G41,G42,X,Y,Z,radG2,radG3,i,J,i,J,i,J,F,TipA,RotA,TipA_rel,RotA_rel,AbsStr,IncStr)
	PPDLLInitParameter(SEP,DECIMALS,PRECISION,UseRadius,NCLineStep,UseAbsIncStrForRelTipARotA,RotInvert,TipInvert,XYZ_WritingMode,WriteNCMillingPointsHeadData,WriteNCMillingPointsHeadDataTipARotA,FeedrateFactor,WriteOnlyLastPointMPsBefore)
	

	' INIT Dyn. Haube 
	PPDLLInitDynamicSuction()

End Function

Function DLLMPs_Start(pno)

	' toCheck OS/MW   - generelle Logik fuer alle Maschinen 
'	If MT_NoTurningWithSpindelRot(actt) Then
	 	' -- MW 06.03.2014
		' Big Tool erst unmittelbar vor der Bearbeitung Spindel starten
'		MT_Write_Speed(ActT,pspeed)
'	Else
		If Not equal(Marker.LastSpeed,PPara.Speed) Then
			MT_Write_Speed(ActT,PPara.Speed)
		End If
'	End If

	
	wcnccom("Mode:" + inttos(PPara.MMode))
	wcnccom("PreObjectType :" + inttos(PPara.PreObjectTyp))
	'wcnc("; WorkMode:" + inttos(PPara.PreObjectType),True)

	'MW 20.01.2016?
	MT_Write_Check_Spindle
	
'	If (MT_Get_PosDustExhaust(actt) = 1) And (JobPara.DynamicSuctionNC=True) Then
'		' dyn. Haubenposition - >
'		WCNC_IDD("CP_HOODDYN_ON",1)
'	End If
	
End Function

Function DLLMPs(Kind,pno)
Dim LiftPosChange As Boolean 
Dim DustSuction As Integer 
'Dim Obj 
'Dim MMPs As NCMillingMPs
'Dim MP As NCMillingPoints
'Dim PNMPs As NCNCInfoProcessMPs

'Dim ax As Variant
'Dim ay As Variant
'Dim az As Variant

' moegliche Infos aus Object
'	Set Obj = NCData.ProcessList.GetProcess_NCInfoIndex(pno-1).View			
'	Set OBJ = NCData.ProcessList.GetProcess_NCInfoIndex(pno-1).Tool

'	wcnc("; WorkMode:" + inttos(Marker.workmode))

'	MP.NCMillingPoints.GetXYZ
'	MP.NCMillingHeadPoints.GetXYZ
'	
'	PNMPs.Para1x|y|z
'	PNMPs.HeadOffX|y|z

'	Set Obj = NCData.ProcessList.GetProcess_NCInfoIndex(pno-1)
'	If Obj.ObjectTyp = otMillingMPs Then
'		Set MMPs = Obj
'		MMPs.MillingList.GetMillingElement_Index(0).GetAxAyAz(ax,ay,az)
'		' MMPs.HeadOffX|y|z
'	End If

	' Spindel mit Vorgelege steuern
	'MT_Set_LiftPos(Kind,pno)
	'MT_Set_HaubeObj(Kind,pno)

	' MW 10.02.2016 - Ermittlung Haubenpos
	'DustSuction = MT_Get_Suction(Kind,PPara)

	
	Select Case Kind
		Case -1 
			wcnc_NCIExt_Before(10)  ' Bei PointOfTime=1 (Para6) hier und jetzt absetzen

			'WCNC_IDD("CONTOUR_START")   ' MW 02.02.2016 - erst im Start_Milling		
			 ' Anfahrt absolut im WKS-Koordinatensystem 
			 ' Alles was vor dem Viewchange kommt - anfahren auf Bearbeitungsposition
			 ' -> Die folgenden X/Y/Z Koordinaten beziehen sich immer auf der Plananlage der Spindel
			 '     ==> d.h. es darf z.B. keine Laengenkorrektur aktiv sein!
			 ' -> Je nach Einstellung "Koordinaten relativ zur Referenzspindel" werden die Offsets mit eingerechnet
			 
			' Dim ZOffGes As Double
			' MT_Write_Offset_NC_Vars(ZOffGes) 
			
			'PPDLLInitStartEndString("3","4")				
			'WCNC_IDD("ATRANSAROT",0,0,0,0,0)
			
			' --> eventuell Drehzahl - Aenderung 
			'MT_Write_Speed(ActT,PPara.Speed,,MT_GetPneumaticSawAngle(ActT,NCData.ProcessList.GetProcess_NCInfoIndex(pno-1).View.TipA,NCData.ProcessList.GetProcess_NCInfoIndex(pno-1).View.RotA))
			
'			PPDLLSupressAxis(True,False,False,True,True)  ' Achsausgabe X, C, A unterdruecken
			
'			wcnccom(" ##################### DLLMPs vor ViewChange - AGGOX:"+ftos(actt.h.CenterX)+"  AGGOY:"+ftos(actt.h.CenterY)+"  AGGOZ:"+ftos(actt.h.CenterZ),True)
			wcnccom(" ##################### DLLMPs vor ViewChange - AGGOX:"+ftos(ActT.t.MoveX)+"  AGGOY:"+ftos(ActT.t.MoveY)+"  AGGOZ:"+ftos(ActT.t.MoveZ),True)
'			wcnc("; TCP:"+ftos(actt.h.TCPOffset_Z)+"  - OffDPx "+ftos(actt.h.RotPointOffX)+"  - OffDPy "+ftos(actt.h.RotPointOffY)+"  - OffDPz "+ftos(actt_mt.h.RotPointOffZ))



			PPDLLInitStartEndLineString("D0","")  ' Schreibt D0 x y z D2

		Case 0
			wcnccom(" ##################### DLLMPs",True)
			wcnc_NCIExt_Before(20)  ' Bei PointOfTime=2 (Para6) hier und jetzt absetzen
			
			'  DLL_ROUT WORKING
			' Eigentliche Bearbeitung
			
			' Bahnverhalten ?
			ActHK_ON=Get_AktHK(PPara.PreObjectTyp,PPara.MMode,True)
			WCNC_AcktHK(0,True)
			'WCNC_AcktHK()
			'WCNC_AktSprueher(2,True)
			SetPPDLL_NCIExt_LeadInLeadOut   ' MW 24.02.2016 - PPDLLAddStrsAfterLeadIn(_Strs, _Mode)  /  PPDLLAddStrsBeforeLeadout(_Strs, _Mode)
			
		Case 1 
			' Rueckzug absolut im WKS-Koordinatensystem 
			ActHK_OFF=Get_AktHK(PPara.PreObjectTyp,PPara.MMode,False)
			WCNC_AcktHK(0,False)
			'WCNC_AktSprueher(2,False)
			wcnc_NCIExt_Before(50)  ' Bei PointOfTime=3 (Para6) hier und jetzt absetzen
			wcnc("TRANS")   '  			WCNC_IDD("TRANSOFF")
			
			' MW 19.01.2015 - Bezugspunkt Werkzeugspitze aus
			'WCNC_IDD("TCARROFF")
			If ((MT_Is_Vertical_StandardTool5Axis(actT)) And (actT.h_add.traori)) Or (MT_IsAnyGearboxTool(Actt) And (actT.h_add.traori))Then
				' 5-Axis mit Traori -
				wcncaddcom(ActT.H_Add.TraoriOff, " 5-Achs - Transformation abschalten")  ' "TRAFOOF"
			End If

			If (PPara.PreObjectTyp=otVertDrilling) Or (PPara.PreObjectTyp=otHorzDrilling) Or (PPara.PreObjectTyp=11) Then
				PPDLLSetMaxDepthDrilling("G1 G9",1)
			End If

			
			'WCNC_IDD("CONTOUR_END_EXCLUSIV")   ' MW 15.02.2016 - ehemals StartLeadOut

			'  DLL_ROUT PULL BACK
			wcnccom(" ##################### DLLMPs SIC",True)
			PPDLLInitStartEndLineString("D0","")  ' Schreibt D0 x y z D2
	End Select

	wcnc_TCP_Offset_On(Kind)    ' hier G92 Offset rechnen (5Axis)
	
'	If DustSuction = 1 Then   
'		' dyn. Haube
'		If equal(Kind,0) Then
'			' MW 11.02.2016 beim Hochfahren kann letzte Position immer beibehalten werden
'			' -> nur fuer die eigentliche Bearbeitung Haubenposition ausgeben - also von Sicherheit ueber Werkstueck und zurueck
'			PPDLLActivateDynamicSuction(ActT.SetOf_DustPositions,ActT.SetOf_DustPositionsMFunc,0)
'		End If
'	Else
'		' Dann Haube auf Pos. von Schneide oder program. ueber NCIExt oder ganz HOCH
'		wcnc_DustSuction(DustSuction)
'	End If

	PPDLLWriteProcess(NCFileNo,Kind,pno-1,NCLine)

	wcnc_TCP_Offset_Off(Kind)    ' hier G92 Offset rechnen (5Axis)
	

End Function


Function DLLMPs_End
	' kommt beim C-Achsfraesen, Oberflaechenfraesen 5-Achsfraesen
	
	wcnc_NCIExt_After
	
	'WCNC_IDD("CONTOUR_END")

	' MW 06.03.2014
	'MT_NoTurningWithSpindelRot_OFF(actt)
	' -> Drehzahlreduzierung bei BigTools
	' toCheck OS/MW

'	If (MT_Get_PosDustExhaust(actt) = 1) And (JobPara.DynamicSuctionNC=True) Then
'		WCNC_IDD("CP_HOODDYN_OFF",0)
'	End If


Inc_Process   ' ActProcess=ActProcess+1
	
	'Marker.EndMoveActiv=False

	PPara.DustPosNCIExt = False

	'PParaReset  ' PNo,Feedrate,I_Feedrate,S_Feedrate,Mode,PreObjectType,MinRotA,MaxRotA,MinTipA,MaxTipA,DustPosNCIExt,NCIExtB,NCIExtA
	            ' außer  ---- >  Speed	< ------

End Function

Function DLLMPs_Final
	' kommt nur einmalig zum Schluss
	PPDLLFinalize
End Function



Sub EndLeadIn_7
	'WCNC_IDD("CONTOUR_START_EXCLUSIV")
End Sub

Sub StartLeadOut_7
	'WCNC_IDD("CONTOUR_END_EXCLUSIV")
End Sub

Sub Park_7 (Index)
	JobPara.park=NCData.NCInfo_Global.GetNCI_Index(Index).Para1
	JobPara.parkx=NCData.NCInfo_Global.GetNCI_Index(Index).Para2
	JobPara.parky=NCData.NCInfo_Global.GetNCI_Index(Index).Para3
End Sub

Sub SuctionHood_7 (Index)
	NCI_Ext_SH.Value1 = NCData.NCIExtList.GetNCI_Index(Index).Para1
	NCI_Ext_SH.Typ1 = NCData.NCIExtList.GetNCI_Index(Index).Para2			    
	NCI_Ext_SH.Mode1 = NCData.NCIExtList.GetNCI_Index(Index).Para3			    
	NCI_Ext_SH.Value2 = NCData.NCIExtList.GetNCI_Index(Index).Para4
	NCI_Ext_SH.Typ2 = NCData.NCIExtList.GetNCI_Index(Index).Para6			    
	NCI_Ext_SH.Mode2 = NCData.NCIExtList.GetNCI_Index(Index).Para6			    
	'MT_CheckProgValue_Suction(NCI_Ext_SH.Value1)  ' MW 10.02.2016 -> Plausibilierung des Wertes, gesetzt werden dürfen nur die Werte, welche unter Eigenschaften definiert
End Sub


Sub	Handle_NCI_Ext_7 (Kind,NCType,Index)   ' 
' ------------------------------------------------------------------------------------------------------------------------
' Kinds
' 0:Process 
' 1:innerhalb Fraesen  
' 2:Bohren 
' 3:horz.Bohren 
' 4:global 
' 6:NCINFO vor dem Vorwechsel fuer Ermittlung fuer welches Aggregat vorgewechselt werden muss - Motornummer setzen
' 7:NCINFO vor dem Vorwechsel fuer Ermittlung fuer welches Aggregat vorgewechselt werden muss - Motornummer setzen
' ------------------------------------------------------------------------------------------------------------------------
Dim resStr As String
Dim Mode As Integer
Dim i As Integer 
Dim flo As Double 
Dim Found As Boolean 
	Found = True
	Select Case Kind
		Case 0
			Select Case NCType
				Case -100200 
					' ehemals NCINFO 200
				    Mode = NCData.NCIExtList.GetNCI_Index(Index).Para1			    
					If NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetString(1,resStr) Then
						' True wenn String
						wcnc(resStr)
					End If
				Case 70000 
					' Diverse Makros welche bisher NCI 200 benutzt haben
					' -> zusaetzliche Parameter fuer Bestimmung Zeitpunkt absetzen
					' -> und jetzt natuerlich die Moeglichkeit Hold..
					'If NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetString(1,resStr) Then
					'	' True wenn String
					'	wcnc(resStr)
					'End If
					If NCData.NCIExtList.GetNCI_Index(Index).IsBeforeProcess Then 
						' Vorwirksam
						Set PPara.NCIExtB(UBound(PPara.NCIExtB)) = NCData.NCIExtList.GetNCI_Index(Index)
						ReDim Preserve PPara.NCIExtB(UBound(PPara.NCIExtB)+1)
						'For i = 0 To NCData.NCIExtList.GetNCI_Index(Index).NCIExt.ParaCount-1 
						'	NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetFloat(i,flo)
						'	NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetString(i,resStr)
						'Next i
					End If
					
					If equal(NCData.NCIExtList.GetNCI_Index(Index).Para1,0) Then    ' 
						' PointOfTime = 0 -> also hier direkt absetzen
						wcnc_NCIExt_Strs(NCData.NCIExtList.GetNCI_Index(Index),0)   ' Alle Strings ueber ParaCount wegschreiben
					End If					
					
				Case 80000 
					' Diverse Makros welche bisher NCI 200 benutzt haben
					' -> zusaetzliche Parameter fuer Bestimmung Zeitpunkt absetzen
					' -> und jetzt natuerlich die Moeglichkeit Hold..
					If NCData.NCIExtList.GetNCI_Index(Index).IsAfterProcess Then 
						' Nachwirksam
						Set PPara.NCIExtA(UBound(PPara.NCIExtA)) = NCData.NCIExtList.GetNCI_Index(Index)
						ReDim Preserve PPara.NCIExtA(UBound(PPara.NCIExtA)+1)
					End If
					' ----------> immer direkt hier absetzen
					wcnc_NCIExt_Strs(NCData.NCIExtList.GetNCI_Index(Index),0)   ' Alle Strings ueber ParaCount wegschreiben


				Case 7451 
					' Bahnverhalten Ecken eckig fahren
					'NCiE.e7251 = True  ' NCIExt 7251 Wenn true "G451" ansonsten "G450" beim Fraesen 
				Case 7211
					' Blasduese ein
					'NCiE.e7211 = True  ' NCIExt 7211
					'SpindleBlowNozzle.Blow=True
				Case 30000
					If NCData.NCIExtList.GetNCI_Index(Index).IsBeforeProcess Then  
						' Nachwirksam
						'Set PPara.NCIExtA(UBound(PPara.NCIExtA)) = NCData.NCIExtList.GetNCI_Index(Index)
						'ReDim Preserve PPara.NCIExtA(UBound(PPara.NCIExtA)+1)
						If NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetString(0,resStr) Then
							ActHK_ON=resStr
						Else
							ActHK_ON=""
						End If
						
						If NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetString(1,resStr) Then
							ActHK_OFF=resStr
						Else
							ActHK_OFF=""
						End If
					' ----------> immer direkt hier absetzen
					'wcnc_NCIExt_Strs(NCData.NCIExtList.GetNCI_Index(Index),0)   ' Alle Strings ueber ParaCount wegschreiben
					End If
					
				Case 100246 'handlig für Sprühmittel und Minmalmengenschmierung
					If NCData.NCIExtList.GetNCI_Index(Index).IsBeforeProcess Then 
						Set PPara.NCIExtB(UBound(PPara.NCIExtB)) = NCData.NCIExtList.GetNCI_Index(Index)
						ReDim Preserve PPara.NCIExtB(UBound(PPara.NCIExtB)+1)
						If NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetString(0,resStr) Then
							NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetString(0,resStr)
							SpruehEinr.MittelOn=resStr
						Else
							SpruehEinr.MittelOn=""
						End If
						If NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetString(1,resStr) Then
							NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetString(1,resStr)
							SpruehEinr.MittelOFF=resStr
						Else
							SpruehEinr.MittelOFF=""						
						End If
						If NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetFloat(2,flo)Then
							NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetFloat(2,flo)
							If flo<>1 Then
								SpruehEinr.Spruehen=False
								SpruehEinr.MittelOn=""
								SpruehEinr.MittelOff=""
							ElseIf flo=1 Then
								SpruehEinr.Spruehen=True
							End If
						Else
							SpruehEinr.Spruehen=False
							SpruehEinr.MittelOn=""
							SpruehEinr.MittelOff=""	
						End If
						
					End If
			Case Else
				Found = False
			End Select
		Case 1
			' NCI innerhalb Fraesbahn
			Select Case NCType
				Case -100200 
					' ehemals NCINFO 200
				    Mode = NCData.NCIExtList.GetNCI_Index(Index).Para1			    
					If NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetString(1,resStr) Then
						' True wenn String
						If Mode=0 Then
							wcnc(resStr)
						Else
							wcnc(resStr,True)
						End If
					End If
			Case 30000

				Found = False
			End Select
		Case 4 
			' Globale NCIExt
			
			Select Case NCType
			Case 100001
				
				Mode = NCData.NCIExtList.GetNCI_Index(Index).Para1
				'PinTischPins.BitStr=Para1
				For i=1 To 22 Step 1
					If NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetString(i,resStr) Then
						If Mode=0 Then
							PinTischPins.Pins(i)=resStr
						Else
							PinTischPins.Pins(i)=""
						End If
					End If
				Next i
				If NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetString(23,resStr) Then
					If Mode=0 Then
						PinTischPins.VerweilZeit=resStr
					Else
							PinTischPins.VerweilZeit=""
					End If
				End If
				If NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetString(24,resStr) Then
					If Mode=0 Then
						PinTischPins.PinsUp=resStr
					Else
							PinTischPins.PinsUp=""
					End If
				End If
				If NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetString(25,resStr) Then
					If Mode=0 Then
						PinTischPins.Unterstuetzer=resStr
					Else
							PinTischPins.Unterstuetzer=""
					End If
				End If
			Case 30000
			
			Case Else
				Found = False
			End Select
		Case Else
			Found = False
	End Select
	If Not Found Then AddHint("NCIExt Kind #"+inttos(Kind)+ " not interpreted")
End Sub

Sub Machine_Stopp_7 (Index, NextBoxWorking,HeadID)
Dim Mode,Park,X,Y,stri,Typ,Para1,Para2
Dim park_merker As Integer
Dim msg,xstr,ystr As String
Dim parkx,parky As Double
Dim characters As String 

	Mode = NCData.NCIExtList.GetNCI_Index(Index).Para1
	Park = NCData.NCIExtList.GetNCI_Index(Index).Para2
	X = NCData.NCIExtList.GetNCI_Index(Index).Para3
	Y = NCData.NCIExtList.GetNCI_Index(Index).Para4
	stri = NCData.NCIExtList.GetNCI_Index(Index).Text
	Typ = NCData.NCIExtList.GetNCI_Index(Index).Para5
	Para1 = NCData.NCIExtList.GetNCI_Index(Index).Para6
	Para2 = NCData.NCIExtList.GetNCI_Index(Index).Para7
	'Machine_Stop(Park,X,Y,stri,NextBoxWorking,HeadID)
	
	msg=stri

	If Len(msg)<=0 Then
		msg = "programmed machine stop - go on with start"
	End If
	xstr=""
	ystr=""
	
	wcnccom("*")
	wcnccom(" Machine STOP Park:"+inttos(Park))
	wcnccom("*")
	
	' MW 11.08.2005 
	' geht nicht, da WerkzeugVorwechsel auch schon einige Bearbeitungen
	' eher kommen kann!
	If Not TCB_T.t Is Nothing Then
		' Toolchangebefore wurde aufgerufen
		If tcb_t.t.ID <> actt.t.ID Then
			' nächstes Werkzeug ein anderes 
			If Not MT_GB_Output_Changed(ActT,TCB_T) Then
				' nächstes Werkzeug nicht auf gleichm Winkelgetriebe
				' dann kann bereits abgeschaltet werden
				'wcncaddcom("M05","toolchange follows")
			End If
		End If
	End If
	park_merker	= JobPara.park
	JobPara.park=Park
	
	Get_ParkStrXY(xstr,ystr)  ' holt sich parkstring
	JobPara.park = park_merker
	
	If Park=10 Then
		xstr=FToS(parkx)
		ystr=FToS(parky)
	End If
	
	
	wcnc(DCORRECTIONMARKER+"=$P_TOOL")   ' aktuelle D-Korrektur merken
	
	If (actt.H_Add.Traori) Then
        wcnc(actt.H_Add.TraoriOff)  '  "TRAORI AUS"

	End If
	
	
	wcnc("TCARR=0")   ' Werkzeugträgerkorrektur abwählen
	
	wSafetyAbs(False)    ' Z-Hochfahren
	
	If (Len(xstr)>0) And (Len(ystr)>0) Then
		wcnc("G53 G0 X="+xstr+" Y="+ystr)  ' X-Y Positionierung
	ElseIf (Len(xstr)>0) Then
		wcnc("G53 G0 X="+xstr)  ' X Positionierung
	ElseIf (Len(ystr)>0) Then
		wcnc("G53 G0 Y="+ystr)  ' X Positionierung
	End If
	
   If MT_Is_Vertical_StandardTool5Axis(actt) Then
		' 5-Achs 
		wcnc("G53 G0 B=0 C=0")
   End If
	
	wcnc_msg(msg)
	wcnc("M0")
	If (actt.H_Add.Traori) Then 'And aCTT.T.HID=HeadID Then 'And actt.T=NextT.T Then
        wcnc(actt.H_Add.TraoriOn)  '  "TRAORI"
	End If
	SET_Zero(False,"",0,0,0,0,0,0,False,False)

	Anschlaege_runterAll(0)

	'Vacuumkontrolle An
	If is_WorkC_OptionBit(UsePfosten,JobPara.WorkC_OptionBit) Then
		Pfosten_spannen(0)
	Else
		vacuum_on(0)
	End If
	wcnc_msgOff
	
	wcnc("D="+DCORRECTIONMARKER)   ' aktuelle D-Korrektur zurückholen
	
End Sub


Sub Process_Start_7(ProcId,BoxId,HeadID,d1,d2,ProcC,XMin,YMin,ZMin,XMax,YMax,ZMax)

	wcnccom("------------------------------- ",True)
	wcnccom(" process group start ",True)
	wcnccom("------------------------------- ",True)
	
	
End Sub

Sub Process_End_7(ProcId,d1,d2)
	
	wcnccom("------------------------------- ",True)
	wcnccom(" process group end ",True)
	wcnccom("------------------------------- ",True)
End Sub



Function SetPPDLL_NCIExt_LeadInLeadOut   ' MW 24.02.2016 - PPDLLAddStrsAfterLeadIn(_Strs, _Mode)  /  PPDLLAddStrsBeforeLeadout(_Strs, _Mode)
Dim i,j As Long 
Dim iNC As Object ' INCNCInfo
Dim ParaString As String
Const POT_B = 30
Const POT_A = 40
Const STR_START = 5   ' ab PARA6 werden alle als abzusetzende Strings interpretiert

	Marker.BStris.Clear 	 '  Marker erzeugt in InitMarker
	Marker.AStris.Clear 	 '  Marker erzeugt in InitMarker 	

   ' Vorwirksame NCIExt nach Anfahrbewegung for Abfahrbewegung absetzen
	For i =  0 To UBound(PPara.NCIExtB) 
		Set iNC = PPara.NCIExtB(i) 
		If Not iNC Is Nothing Then
			Select Case iNC.Kind
				Case 70000
				
					If equal(iNC.Para1,POT_B) Or equal(iNC.Para1,POT_A) Then    ' 
						' PointOfTime = POT_B = (30)
						' PointOfTime = POT_A = (40)
						' Strings sammeln
						
						For j = STR_START To iNC.NCIExt.ParaCount-1 
							If iNC.NCIExt.GetString(j,ParaString) Then
								' String - Wert gefunden
								If Len(ParaString)>0 Then
									' inc.para2=1 -> Zeilennummerierung unterdrucken
									If equal(iNC.Para1,POT_B) Then Marker.BStris.Add(ParaString)
									If equal(iNC.Para1,POT_A) Then Marker.AStris.Add(ParaString)

									'wcncAddCom(ParaString,"NCIExt "+IntToS(iNC.Kind)+" PoT="+IntToS(pointoftime)+" sL="+IntToS(iNC.Para2),True,equal(iNC.Para2,1))
								End If
							End If
							
						Next j
						If Marker.BStris.Count>0 Then
							PPDLLAddStrsAfterLeadIn(Marker.BStris,iNC.Para2)	
						End If
						If Marker.AStris.Count>0 Then
							PPDLLAddStrsBeforeLeadout(Marker.AStris,iNC.Para2)	
						End If
						'BStris.Clear 
						'AStris.Clear 

					End If
		'	Case 100246
		'		For j = 0 To 1 
		'			If iNC.NCIExt.GetString(j,ParaString) Then
		'				If Len(ParaString)>0 Then
		'					If j=0 Then WCNC_DLL_OnLeadInOut(ParaString,0,2,False)
		'					If j=1 Then WCNC_DLL_OnLeadInOut(ParaString,0,2,True)
		'				End If	
		'			End If
		'			
		'		Next j
		'		If Marker.BStris.Count>0 Then
		'			PPDLLAddStrsAfterLeadIn(Marker.BStris,iNC.Para2)	
		'		End If
		'		If Marker.AStris.Count>0 Then
		'			PPDLLAddStrsBeforeLeadout(Marker.AStris,iNC.Para2)	
		'		End If
			End Select
		End If
	Next i
	
End Function

Sub Handle_ClampChangeExt_7 (Index,par1,par2,par3,par4,par5,par6,par7,par8,par9,stri)
Dim resStr As String 
Dim para12 As Double
	par1 = NCData.NCIExtList.GetNCI_Index(Index).Para1			    
	par2 = NCData.NCIExtList.GetNCI_Index(Index).Para2
	par3 = NCData.NCIExtList.GetNCI_Index(Index).Para3
	par4 = NCData.NCIExtList.GetNCI_Index(Index).Para4
	par5 = NCData.NCIExtList.GetNCI_Index(Index).Para5
	par6 = NCData.NCIExtList.GetNCI_Index(Index).Para6
	par7 = NCData.NCIExtList.GetNCI_Index(Index).Para7
	par8 = NCData.NCIExtList.GetNCI_Index(Index).Para8
	par9 = NCData.NCIExtList.GetNCI_Index(Index).Para9
	stri = NCData.NCIExtList.GetNCI_Index(Index).Text
'	If NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetString(Index,resStr) Then
'		stri = resStr
'	Else
'		stri = ""
'	End If
	Dim i As Integer 
	For i = 0 To 20 
		If NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetFloat(i,para12) Then
		
		End If
	Next
End Sub


Function Get_TN_Info(BoxId, Optional HeadID) As String
Dim TN As String
	TN = ""
	If Not TDATA.GetTool_ID (BoxId) Is Nothing Then
		If (TDATA.GetTool_ID(BoxId).ObjectType = htokDrillingHeadTool) Or (TDATA.GetTool_ID(BoxId).ObjectType = htokDH_SawTool) Then
			' Bohrkopf - Werkzeug
			TN =TDATA.GetTool_ID(BoxId).Description
			
			TN = TN+" Head:" + TDATA.GetDrillingHead_ID(TDATA.GetTool_ID(BoxId).AggNo).Description
			
			
		ElseIf (TDATA.GetTool_ID(BoxId).ObjectType = htokStandardTool) Or (TDATA.GetTool_ID(BoxId).ObjectType = htokGearboxOnHeadTool) Then
			TN =TDATA.GetTool_ID(BoxId).Tool.Description
			
			If Not IsMissing(HeadID)  Then
				TN = TN+" HEAD:" + TDATA.GetProcessHead_ID(HeadID).Description
			End If
			
			
		ElseIf Not TDATA.GetTool_ID(BoxId).Tool Is Nothing Then
			TN =TDATA.GetTool_ID(BoxId).Tool.Description
			
			If Not IsMissing(HeadID)  Then
				TN = TN+" HEAD:" + TDATA.GetProcessHead_ID(HeadID).Description
			End If
			
		End If
	End If
	Get_TN_Info = TN
	
End Function

Function GetV_Check3(V) As String
Dim i,pos As Integer 
' macht aus 1.2.3.4 -> 1.2.3
'       aus 20.34.3567.3554 -> 20.34.3567
	For i = Len(V) To 0 Step -1
		If Mid$(V,i,1)="." Then
			pos=i
			Exit For
		End If
	Next i
	If pos > 0 Then 
		GetV_Check3=Mid(V,1,pos-1)
	Else
		pp_Err(1549)
	End If
End Function


Function SetNCName(NCName,NCExt,NCPath As String)
	If FolderExists(NCPath) Then
		JobPara.RealNCFileName = NCPath+NCName+NCExt
	    PostSettings.NCFileNames = NCPath+NCName+NCExt
	Else
		pp_Err(1543,NCPath)
	End If
    
End Function
    


Function Read_PPVersion As String 
Dim vari As Variant

	' MW 21.01.2015 Die Versionsnummer wird uebers das Setup geschrieben/Revision gepflegt
	vari = PostSettings.ReadString("VERSION","PPSETUP","0.0.0.0")
	Read_PPVersion = vari
End Function


Function Write_PPVersion
	PostSettings.WriteString("VERSION", "PPSCRIPT",SCRIPT_VERSION)
End Function

' ------------------------------------------------------------------------------------------
' --  
' -- PP.INI -> EINSTELLUNGEN
' -- 
' -- Hier wird festgelegt, mit welchen Einstellungen die Engine zu arbeiten hat

Function INI_Check   ' 
Dim Err As String

' Programm
	Const ShowErr = True        ' Fehleranzeigen
	Const AllowNC_Err = False    ' NC-Erzeugung bei Fehlern ermoeglichen
	Const Delete_NCFile = True  ' NC-Programm loeschen
	'Const KeepOpen = 0       ' geoeffnet lassen
	'Const Modal = 1          ' Modales Fenster
	'Const Maximized = 1      ' Maximiertes Fenster
	'Const Gen_New = 0         ' Neu erzeugen moeglich
	Const WriteLocDat = False     ' Loc.dat schreiben
	Const ProgActivateDLL = False  ' Programmaktivierung steuerungsseitig
	Const ProgActivateAndStart = 0  ' 0: anwaehlen und starten 1:anwaehlen

' Maschine
	Const BlockFlagMode=-1         ' Makroeinstellung verwenden 
	Const MoveX=0                  ' Konstante Verschiebung X
	Const MoveY=0                  ' Konstante Verschiebung Y
	Const MoveZ=0                  ' Konstante Verschiebung Z
	' --> Koordinatensystem
		Const RotateXAxisAngle=0   ' Drehung um die X-Achse 0/180
		Const RotateZAxisAngle=0   ' Drehung um die Z-Achse 90/180/270

' Parameter / Generell Settings
	Const Main_bas_File="PP"                       ' --> PP.BAS
	Const SatzEnde = "13;10"
	Const AdaptEndOfLine = True                    ' Zeilenende anpassen
	Const CalcHeadOffset = False                   ' Aggregatverschiebung verrechnen
	Const LaengeVerrechnen = False                 ' Werkzeuglaenge verrechnen
	Const CheckToolActConf = True                  ' Werkzeug in aktiver Konfiguration pruefen
	Const AddDW = 0                                ' 0/90/180/270 drehen Winkel additiv
	Const Verschiebung = 0                         ' Verschiebung verrechnen Nein/Ja/Stop -> Nullpunkt verrechnen welcher ueber NCSTART kommt
												   ' ===> 1 momentan nicht moeglich !!!!!!!
												   '      -> dadurch verschobene Ebene0 beim vertikalen Bohrungen wird nicht korrekt verrechnet
	Const CalcHeadMoves = True                     ' Bearbeitungskopfdaten verrechnen -> neue Logik 5-Achs und 3-Achs SIMU = NC
		Const RelativToRefSpindle = True           ' Absolut -> also mit Head Offsetverrechnung
	
' Parameter / Script
	Const NKS = 9                                      ' Nachkommastellen
	Const Delete0InNKS = True                          ' .0300 letzte Nullen loeschen
	Const VorWechselVorWerkzeugWechsel  = True         ' WZG-Vorwechsel vor WZG-Wechsel
	Const AlleWerkzeugeWegschreiben = True             ' Werkzeugliste schreiben
	Const AlleBearbeitungenWegschreiben = False         ' Bearbeitungsliste schreiben
	Const RohteilInfoWegschreiben=False                ' Fertigteilinformation schreiben
	Const ViewInfoBeforeToolchangeWegschreiben=True    ' Ebeneninfo vor Werkzeugwechsel schreiben
	Const AlleTeileWegschreiben=True                   ' Werstueck - Info schreiben
	Const WriteHid=True                                ' Aggregate Info schreiben
	Const ProcessMinMaxInfo=False   ' MW 09.02.2016 True                       ' Min/Max Info schreiben
	Const WriteStartNCInfoProcess=True ' MW 17.02.2016 False                ' Start NCInfoProcess schreiben
	Const WriteStartEndProcess=True                    ' Start - Ende der Bearbeitung schreiben MW 20.01.2016 true
	Const WriteStartEndProcessToolOpti=True 'False           ' Werkzeug wechselt optimiert -> MW 02.02.2016 muss True sein, im ProcessStart wird z.B. LAstLiftPos resetet
	Const WriteInitZero=True                           ' Initialisierungsmakro schreiben

' Milling
	Const AnfahrBewegungInBasic = 1                ' 0: nicht ausgeben 1: ausgeben 2:ohne Radiuskorrektur ausgeben 3:ohne Radiuskorrektur und Sicherheit ausgeben
	Const BearLage_G2G3UmschaltenEbene1=False      ' Ebene 1 -> Umschalten G2/G3 und WRK (masch)
	Const BearLage_G2G3UmschaltenEbene2=False      ' Ebene 2 -> Umschalten G2/G3 und WRK (masch)
	Const BearLage_G2G3UmschaltenEbene3=False      ' Ebene 3 -> Umschalten G2/G3 und WRK (masch)
	Const BearLage_G2G3UmschaltenEbene4=False      ' Ebene 4 -> Umschalten G2/G3 und WRK (masch)
	Const ExecuteOnParaViews=False                 ' auf parallel verschobenen Ebenen
	Const SP_EP_No_LeadInOutWegschreiben=False     ' SP/EP ohne An/Abfahrbewegung schreiben
'Const NCILeadInOut = 500                       ' ????????
	Const WriteAddSPInfo=True                      ' Erweiterte Startpunktdaten schreiben
	Const ToleranzNextMillEle=0.00001              ' Toleranz (nexte Elemente)
	Const ToleranzNextMillEle5Axis=0.01  '0.1             ' Toleranz (5-Achsfraesen)
' Milling / WKR
	Const GTypRadiusKorrekturAufbau = 0            ' G-Typ fuer Werkzeugradiuskorrekturaufbau
	Const AnfahrFaktor_Seitlich = 1.1              ' Faktor fuer seitliches Anfahren
' Milling / Definition der Strecke fuer Korrekturaufbau
	Const TRCAngle=90                               ' Winkel 0(Hops6): in Verlaengerung der Anfahrbewegung
	Const TRCFactor=1                             ' Faktor 0(Hops6) 
	Const TRCLength = 1                            ' Strecke (1mm) fuer Korrekturaufbau
' Milling WRK / Aequidistanten - Rechnung
	Const RadiusKorrekturFreieEbeneRechnen=False   ' Fraeserradiuskorrektur auf freier Ebene berechnen
	Const SetofTRConAllViews=False                 ' Fraeserradiuskorrektur auf allen Ebenen berechnen
	Const DeleteStartEndTRCLines=False             ' Radiuskorrekturlinien auf allen Ebenen berechnen
	Const ArcToLines=False                         ' Boegen in Linien
' Milling / Abstand zur Kontur
	Const ToleranzArcInsert=0.1                       ' Toleranz (Bogen ein)
	Const AbstandZurKonturAusgeben=True               ' Abstand zur Kontur schreiben
	Const AbstandzurKonturVerrechnen=False            ' Abstand zur Kontur verrechnen
	Const AbstandzurKonturVerrechnenTRCAbhaengig=True ' Offsetberechnung in Abhaengigkeit von der WRK
	Const CalcOffTRC_CAxis=False  ' MW 20.01.2016 nicht mehr True   ' Offsetberechnung C-Achsfraesen WKG

' Bohren
	Const DrillingAsMilling=True
	Const TieflochflagWegschreiben=True
	
	Const NeueBohrOpti=True
	
	Const ModeOldDrilOpti=0
	Const BohroptiBoxNRWegschreiben=True
	Const BohroptiAnzahlHuebeWegschreiben=False
	Const LaengeVerrechnenBohrkopf=False
	Const CheckAllHoles=True
	Const BohrungenAufBohrkopfGruppieren=True
	Const InsertAllDrillBits=False   ' EINST
	Const MinMaxHorzLaengeSicherheitVerrechnen=True   ' EINST
	
	Const DHTimeOpti = True
	Const DHPinChangeTime = 3

' Sawing
	Const SBBVerrechnen=False                   ' Saegeblattdicke verrechnen
	Const SaegeBlatthalbeVerrechnen=True        ' Halbe Saegeblattdicke verrechnen
	Const SaegeLaengeVerrechnen=False
	Const SaegeRadiusVerrechnen=True
	Const SaegeEinpassenVerrechnen=True
	Const ExtentedSawingCut=True
	Const TwoSawingToOne=True
	Const SawingAsMilling=True

' Winkelgetriebe auf 5-Achskopf  MW 18.03.2016
	Const GBOn5AxisFreeTipA = False  ' PP unterstuetzt Winkelgetriebe auf 5-Achskopf 

' -----------------------------------------------------------------------------------
' -----------------------------------------------------------------------------------
' -----------------------------------------------------------------------------------
' -----------------------------------------------------------------------------------
' -----------------------------------------------------------------------------------
' -----------------------------------------------------------------------------------
' -----------------------------------------------------------------------------------
' -----------------------------------------------------------------------------------

	Err = ""
	
	' -----------------------------------------------------------------------------------
	' Machine Settings	
	If PostSettings.MachineSettings.BlockFlagMode<>BlockFlagMode Then
		PostSettings.WriteInteger("NC","BLockFlag",BlockFlagMode)
		Err = Err + "BLockFlag;"
	End If
	If PostSettings.MachineSettings.MoveX<>MoveX Then
		PostSettings.WriteInteger("Maschine","Masch_VerschiebungX",MoveX)
		Err = Err + "Masch_VerschiebungX;"
	End If
	If PostSettings.MachineSettings.MoveY<>MoveY Then
		PostSettings.WriteInteger("Maschine","Masch_Verschiebungy",MoveY)
		Err = Err + "Masch_VerschiebungY;"
	End If
	If PostSettings.MachineSettings.MoveZ<>MoveZ Then
		PostSettings.WriteInteger("Maschine","Masch_VerschiebungZ",MoveZ)
		Err = Err + "Masch_VerschiebungZ;"
	End If
	'     Koordinatensystem
	If PostSettings.MachineSettings.RotateXAxisAngle<>RotateXAxisAngle Then
		PostSettings.WriteInteger("Maschine","Masch_DrehW_X_Achse",RotateXAxisAngle)
		Err = Err + "Masch_DrehW_X_Achse;"
	End If
	If PostSettings.MachineSettings.RotateZAxisAngle<>RotateZAxisAngle Then
		PostSettings.WriteInteger("Maschine","Masch_DrehW_Z_Achse",RotateZAxisAngle)
		Err = Err + "Masch_DrehW_Z_Achse;"
	End If
	' -----------------------------------------------------------------------------------
	
	' -----------------------------------------------------------------------------------
	' Programm
	If PostSettings.GeneralSettings.ShowErrors<>ShowErr Then
		PostSettings.WriteInteger("NC","FehlerAnzeigen",ShowErr)
		Err = Err + "ShowErr;"
	End If
	If PostSettings.GeneralSettings.EnableCreateButton<>AllowNC_Err Then
		PostSettings.WriteInteger("NC","EnableCreateButton",AllowNC_Err)
		Err = Err + "AllowNC_Err;"
	End If
	If PostSettings.GeneralSettings.DeleteNCFile<>Delete_NCFile Then
		PostSettings.WriteInteger("NC","DeleteNCFile",Delete_NCFile)
		Err = Err + "DeleteNCFile;"
	End If
	If PostSettings.GeneralSettings.SaveLocFile<>WriteLocDat Then
		PostSettings.WriteInteger("NC","WriteLocDat",WriteLocDat)
		Err = Err + "WriteLocDat;"
	End If
	If PostSettings.GeneralSettings.EnableProgActive<>ProgActivateDLL Then
		PostSettings.WriteInteger("NC","EnableProgActive",ProgActivateDLL)
		Err = Err + "EnableProgActive;"
	End If
	If PostSettings.GeneralSettings.SelectStartProg<>ProgActivateAndStart Then
		PostSettings.WriteInteger("EINST","SelectStartProg",ProgActivateAndStart)
		Err = Err + "ProgActivateAndStart;"
	End If
	' -----------------------------------------------------------------------------------
	
	' -----------------------------------------------------------------------------------
	' Parameter  / General Settings	
	If UCase(PostSettings.DefaultPPBasName) <> Main_bas_File Then
		PostSettings.WriteString("NC","Maschine",Main_bas_File)
		Err = Err + "Main_bas_File;"
	End If
	If UCase(PostSettings.GeneralSettings.EndOfLineStr) <> SatzEnde Then
		PostSettings.WriteString("NC","SatzEnde",SatzEnde)
		Err = Err + "SatzEnde;"
	End If
	If PostSettings.GeneralSettings.AdaptEndOfLine <> AdaptEndOfLine Then
		PostSettings.WriteBool("NC","AdaptEndOfLine",AdaptEndOfLine)
		Err = Err + "AdaptEndOfLine;"
	End If
	If PostSettings.GeneralSettings.CalcHeadOffset <> CalcHeadOffset Then
		PostSettings.WriteBool("NC","AggVerVerrechnen",CalcHeadOffset)
		Err = Err + "AggVerVerrechnen;"
	End If
	
	If PostSettings.GeneralSettings.RelativToRefSpindle <> RelativToRefSpindle Then
		PostSettings.WriteBool("EINST","RelativToRefSpindle",RelativToRefSpindle)
		Err = Err + "RelativToRefSpindle;"
	End If
	
	If PostSettings.GeneralSettings.CalcToolLength <> LaengeVerrechnen Then
		PostSettings.WriteBool("NC","LaengeVerrechnen",LaengeVerrechnen)
		Err = Err + "LaengeVerrechnen;"
	End If
	If PostSettings.GeneralSettings.CheckToolInActConf  <> CheckToolActConf Then
		PostSettings.WriteBool("EINST","CheckToolInActConf",CheckToolActConf)
		Err = Err + "CheckToolActConf;"
	End If
	If PostSettings.GeneralSettings.AddRotAngle  <> AddDW Then
		PostSettings.WriteInteger("NC","DrehenWinkelAdditiv",AddDW)
		Err = Err + "DrehenWinkelAdditiv;"
	End If
	If PostSettings.GeneralSettings.MovingMode	<> Verschiebung Then
		PostSettings.WriteInteger("NC","Verschiebung",Verschiebung)
		Err = Err + "Verschiebung;"
	End If
	
	If PostSettings.GeneralSettings.CalcHeadMoves <> CalcHeadMoves Then
		PostSettings.WriteBool("EINST","CalcHeadMoves",CalcHeadMoves)
		Err = Err + "CalcHeadMoves;"
	End If
	
	' -----------------------------------------
	' Script

	If PostSettings.GeneralSettings.Delete0<>Delete0InNKS Then
		PostSettings.WriteBool("EINST","Delete0InNKS",Delete0InNKS)
		Err = Err + "Delete0InNKS;"
	End If
	' ???
	'If PostSettings.GeneralSettings.<>NKS Then
	If PostSettings.ReadInteger ("NC","NKS",9)<> NKS Then
		PostSettings.WriteInteger("NC","NKS",NKS)
		Err = Err + "NKS;"
	End If
	If PostSettings.GeneralSettings.WriteTCBeforeBeforeTC<>VorWechselVorWerkzeugWechsel Then
		PostSettings.WriteBool("NC","VorWechselVorWerkzeugWechsel",VorWechselVorWerkzeugWechsel)
		Err = Err + "VorWechselVorWerkzeugWechsel;"
	End If
	If PostSettings.GeneralSettings.WriteToolList <> AlleWerkzeugeWegschreiben Then
		PostSettings.WriteBool("NC","AlleWerkzeugeWegschreiben",AlleWerkzeugeWegschreiben)
		Err = Err + "VorWechselVorWerkzeugWechsel;"
	End If
	If PostSettings.GeneralSettings.WriteProcessList <> AlleBearbeitungenWegschreiben Then
		PostSettings.WriteBool("NC","AlleBearbeitungenWegschreiben",AlleBearbeitungenWegschreiben)
		Err = Err + "AlleBearbeitungenWegschreiben;"
	End If
	If PostSettings.GeneralSettings.WriteFinishedPartInfo <> RohteilInfoWegschreiben Then
		PostSettings.WriteBool("NC","RohteilInfoWegschreiben",RohteilInfoWegschreiben)
		Err = Err + "RohteilInfoWegschreiben;"
	End If
	If PostSettings.GeneralSettings.WriteViewInfoBeforeTC <> ViewInfoBeforeToolchangeWegschreiben Then
		PostSettings.WriteBool("NC","ViewInfoBeforeToolchangeWegschreiben",ViewInfoBeforeToolchangeWegschreiben)
		Err = Err + "ViewInfoBeforeToolchangeWegschreiben;"
	End If
	If PostSettings.GeneralSettings.WriteParts <> AlleTeileWegschreiben Then
		PostSettings.WriteBool("NC","AlleTeileWegschreiben",AlleTeileWegschreiben)
		Err = Err + "AlleTeileWegschreiben;"
	End If
	If PostSettings.GeneralSettings.WriteHeadInfo <> WriteHid Then
		PostSettings.WriteBool("EINST","WriteHid",WriteHid)
		Err = Err + "WriteHid;"
	End If
	If PostSettings.GeneralSettings.WriteProcessMinMax <> ProcessMinMaxInfo Then
		PostSettings.WriteBool("EINST","ProcessMinMaxInfo",ProcessMinMaxInfo)
		Err = Err + "ProcessMinMaxInfo;"
	End If
	If PostSettings.GeneralSettings.WriteStartNCInfoProcess <> WriteStartNCInfoProcess Then
		PostSettings.WriteBool("EINST","WriteStartNCInfoProcess",WriteStartNCInfoProcess)
		Err = Err + "WriteStartNCInfoProcess;"
	End If
	If PostSettings.GeneralSettings.WriteStartEndProcess <> WriteStartEndProcess Then
		PostSettings.WriteBool("EINST","WriteStartEndProcess",WriteStartEndProcess)
		Err = Err + "WriteStartEndProcess;"
	End If
	If PostSettings.GeneralSettings.WriteStartEndProcessToolOpti <> WriteStartEndProcessToolOpti Then
		PostSettings.WriteBool("EINST","WriteStartEndProcessToolOpti",WriteStartEndProcessToolOpti)
		Err = Err + "WriteStartEndProcessToolOpti;"
	End If
	If PostSettings.GeneralSettings.WriteInitZero <> WriteInitZero Then
		PostSettings.WriteBool("EINST","WriteInitZero",WriteInitZero)
		Err = Err + "WriteInitZero;"
	End If
	
	' -----------------------------------------------------------------------------------
	' Milling Settings	
	If PostSettings.MillingSettings.WriteLeadInOutMode<>AnfahrBewegungInBasic Then
		PostSettings.WriteInteger("NC","AnfahrBewegungInBasic",AnfahrBewegungInBasic)
		Err = Err + "AnfahrBewegungInBasic;"
	End If
	If PostSettings.MillingSettings.ChangeG2G3TRCView1<>BearLage_G2G3UmschaltenEbene1 Then
		PostSettings.WriteBool("NC","BearLage_G2G3UmschaltenEbene1",BearLage_G2G3UmschaltenEbene1)
		Err = Err + "BearLage_G2G3UmschaltenEbene1;"
	End If
	If PostSettings.MillingSettings.ChangeG2G3TRCView2<>BearLage_G2G3UmschaltenEbene2 Then
		PostSettings.WriteBool("NC","BearLage_G2G3UmschaltenEbene2",BearLage_G2G3UmschaltenEbene2)
		Err = Err + "BearLage_G2G3UmschaltenEbene2;"
	End If
	If PostSettings.MillingSettings.ChangeG2G3TRCView3<>BearLage_G2G3UmschaltenEbene3 Then
		PostSettings.WriteBool("NC","BearLage_G2G3UmschaltenEbene3",BearLage_G2G3UmschaltenEbene3)
		Err = Err + "BearLage_G2G3UmschaltenEbene3;"
	End If
	If PostSettings.MillingSettings.ChangeG2G3TRCView4<>BearLage_G2G3UmschaltenEbene4 Then
		PostSettings.WriteBool("NC","BearLage_G2G3UmschaltenEbene4",BearLage_G2G3UmschaltenEbene4)
		Err = Err + "BearLage_G2G3UmschaltenEbene4;"
	End If
	If PostSettings.MillingSettings.ExecuteOnParaViews<>ExecuteOnParaViews Then
		PostSettings.WriteBool("Einst","ExecuteOnParaViews",ExecuteOnParaViews)
		Err = Err + "ExecuteOnParaViews;"
	End If
	
	If PostSettings.MillingSettings.WriteSPEPNoLeadInOut<>SP_EP_No_LeadInOutWegschreiben Then
		PostSettings.WriteBool("NC","SP_EP_No_LeadInOutWegschreiben",SP_EP_No_LeadInOutWegschreiben)
		Err = Err + "SP_EP_No_LeadInOutWegschreiben;"
	End If
	If PostSettings.MillingSettings.CalcTRCOnAllViews<>SetofTRConAllViews Then
		PostSettings.WriteBool("Einst","SetofTRConAllViews",SetofTRConAllViews)
		Err = Err + "SetofTRConAllViews;"
	End If
	If PostSettings.MillingSettings.WriteAddSPInfo<>WriteAddSPInfo Then
		PostSettings.WriteBool("Einst","WriteAddSPInfo",WriteAddSPInfo)
		Err = Err + "WriteAddSPInfo;"
	End If
	If PostSettings.MillingSettings.ToleranceNextMillEle<>ToleranzNextMillEle Then
		PostSettings.WriteString("Einst","ToleranzNextMillEle",ftos(ToleranzNextMillEle))
		Err = Err + "ToleranzNextMillEle;"
	End If
	If PostSettings.MillingSettings.ToleranceSurface<>ToleranzNextMillEle5Axis Then
		PostSettings.WriteString("Einst","ToleranzNextMillEle5Axis",ftos(ToleranzNextMillEle5Axis))
		Err = Err + "ToleranzNextMillEle5Axis;"
	End If
	If PostSettings.MillingSettings.GTypeTRC<>GTypRadiusKorrekturAufbau Then
		PostSettings.WriteInteger("NC","GTypRadiusKorrekturAufbau",GTypRadiusKorrekturAufbau)
		Err = Err + "GTypRadiusKorrekturAufbau;"
	End If
	If PostSettings.MillingSettings.LeadFactorSide<>AnfahrFaktor_Seitlich Then
		PostSettings.WriteString("NC","AnfahrFaktor_Seitlich",ftos(AnfahrFaktor_Seitlich))
		Err = Err + "AnfahrFaktor_Seitlich;"
	End If
	If PostSettings.MillingSettings.TRCAngle<>TRCAngle Then
		PostSettings.WriteString("NC","TRCAngle",ftos(TRCAngle))
		Err = Err + "TRCAngle;"
	End If
	If PostSettings.MillingSettings.TRCFactor<>TRCFactor Then
		PostSettings.WriteString("NC","TRCFactor",ftos(TRCFactor))
		Err = Err + "TRCFactor;"
	End If
	If PostSettings.MillingSettings.TRCLength<>TRCLength Then
		PostSettings.WriteString("NC","FesteLaengeTRCWert",ftos(TRCLength))
		Err = Err + "TRCLength;"
	End If
'	If PostSettings.MillingSettings.TRCLengthRadius<> Then
'		PostSettings.WriteInteger("Einst","AnfahrBewegungInBasic",AnfahrBewegungInBasic)
'		Err = Err + "AnfahrBewegungInBasic"
'	End If
	If PostSettings.MillingSettings.CalcTRCOnFreeView<>RadiusKorrekturFreieEbeneRechnen Then
		PostSettings.WriteBool("NC","RadiusKorrekturFreieEbeneRechnen",RadiusKorrekturFreieEbeneRechnen)
		Err = Err + "RadiusKorrekturFreieEbeneRechnen;"
	End If
	If PostSettings.MillingSettings.DeleteStartEndTRCLines<>DeleteStartEndTRCLines Then
		PostSettings.WriteBool("Einst","DeleteStartEndTRCLines",DeleteStartEndTRCLines)
		Err = Err + "DeleteStartEndTRCLines;"
	End If
	If PostSettings.MillingSettings.ArcToLines<>ArcToLines Then
		PostSettings.WriteBool("Einst","ArcToLines",ArcToLines)
		Err = Err + "ArcToLines;"
	End If
	If PostSettings.MillingSettings.DistToOutlineToleranceArcIn<>ToleranzArcInsert Then
		PostSettings.WriteString("NC","ToleranzArcInsert",ftos(ToleranzArcInsert))
		Err = Err + "ToleranzArcInsert;"
	End If
	If PostSettings.MillingSettings.WriteDistToContour<>AbstandZurKonturAusgeben Then
		PostSettings.WriteBool("NC","AbstandZurKonturAusgeben",AbstandZurKonturAusgeben)
		Err = Err + "AbstandZurKonturAusgeben;"
	End If
	If PostSettings.MillingSettings.CalcDistToOutline<>AbstandzurKonturVerrechnen Then
		PostSettings.WriteBool("NC","AbstandzurKonturVerrechnen",AbstandzurKonturVerrechnen)
		Err = Err + "AbstandzurKonturVerrechnen;"
	End If
	If PostSettings.MillingSettings.OffsetDependsOnTRC<>AbstandzurKonturVerrechnenTRCAbhaengig Then
		PostSettings.WriteBool("NC","AbstandzurKonturVerrechnenTRCAbhaengig",AbstandzurKonturVerrechnenTRCAbhaengig)
		Err = Err + "AbstandzurKonturVerrechnenTRCAbhaengig;"
	End If
	If PostSettings.MillingSettings.CalcOffsetCAxisMilling<>CalcOffTRC_CAxis Then
		PostSettings.WriteBool("Einst","CalcOffTRC_CAxis",CalcOffTRC_CAxis)
		Err = Err + "CalcOffTRC_CAxis;"
	End If


'	If PostSettings.MillingSettings.FixTRCLength<> Then
'	If PostSettings.MillingSettings.ToleranceSmallArc<> Then
	
	'immer schreiben ueber neue Subs
	'PostSettings.MillingSettings.WriteInfoLeadInOut
	


	' -----------------------------------------------------------------------------------
	' Drilling Settings	
	If PostSettings.DrillingsSettings.DrillingAsMilling<>DrillingAsMilling Then
		PostSettings.WriteBool("EINST","DrillingAsMilling",DrillingAsMilling)
		Err = Err + "DrillingAsMilling;"
	End If
	If PostSettings.DrillingsSettings.WriteMaximumDepths <>TieflochflagWegschreiben Then
		PostSettings.WriteBool("NC","TieflochflagWegschreiben",TieflochflagWegschreiben)
		Err = Err + "TieflochflagWegschreiben;"
	End If
	
	If PostSettings.DrillingsSettings.NewDHOpti <>NeueBohrOpti Then
		PostSettings.WriteBool("EINST","NeueBohrOpti",NeueBohrOpti)
		Err = Err + "NeueBohrOpti;"
	End If

	If PostSettings.DrillingsSettings.DHModeOldDrillOpti <>ModeOldDrilOpti Then
		PostSettings.WriteInteger("EINST","ModeOldDrilOpti",ModeOldDrilOpti)
		Err = Err + "ModeOldDrilOpti;"
	End If

	If PostSettings.DrillingsSettings.WriteDHID<>BohroptiBoxNRWegschreiben Then
		PostSettings.WriteBool("NC","BohroptiBoxNRWegschreiben",BohroptiBoxNRWegschreiben)
		Err = Err + "BohroptiBoxNRWegschreiben;"
	End If
	If PostSettings.DrillingsSettings.WriteDHStrokeCount<>BohroptiAnzahlHuebeWegschreiben Then
		PostSettings.WriteBool("NC","BohroptiAnzahlHuebeWegschreiben",BohroptiAnzahlHuebeWegschreiben)
		Err = Err + "BohroptiAnzahlHuebeWegschreiben;"
	End If
	If PostSettings.DrillingsSettings.DHCalcLength<>LaengeVerrechnenBohrkopf Then
		PostSettings.WriteBool("NC","LaengeVerrechnenBohrkopf",LaengeVerrechnenBohrkopf)
		Err = Err + "LaengeVerrechnenBohrkopf;"
	End If
	If PostSettings.DrillingsSettings.DHCheckAllHoles <>CheckAllHoles Then
		PostSettings.WriteBool("NC","CheckAllHoles",CheckAllHoles)
		Err = Err + "CheckAllHoles;"
	End If
	If PostSettings.DrillingsSettings.GroupDrillingsOnDH <>BohrungenAufBohrkopfGruppieren Then
		PostSettings.WriteBool("NC","BohrungenAufBohrkopfGruppieren",BohrungenAufBohrkopfGruppieren)
		Err = Err + "BohrungenAufBohrkopfGruppieren;"
	End If
	
	If PostSettings.DrillingsSettings.DHInsertAllDrillBits <>InsertAllDrillBits Then
		PostSettings.WriteBool("EINST","InsertAllDrillBits",InsertAllDrillBits)
		Err = Err + "InsertAllDrillBits;"
	End If
	If PostSettings.DrillingsSettings.DHCalcMinMaxHorzLengthSafety <>MinMaxHorzLaengeSicherheitVerrechnen Then
		PostSettings.WriteBool("EINST","MinMaxHorzLaengeSicherheitVerrechnen",MinMaxHorzLaengeSicherheitVerrechnen)
		Err = Err + "MinMaxHorzLaengeSicherheitVerrechnen;"
	End If

	If PostSettings.DrillingsSettings.DHTimeOpti <> DHTimeOpti Then
		PostSettings.WriteBool("EINST","DHTimeOpti",DHTimeOpti)
		Err = Err + "DHTimeOpti;"
	End If
	If PostSettings.DrillingsSettings.DHPinChangeTime <> DHPinChangeTime Then
		PostSettings.WriteString("EINST","DHPinChangeTime",ftos(DHPinChangeTime))
		Err = Err + "DHPinChangeTime;"
	End If


	' -----------------------------------------------------------------------------------
	' Sawing Settings	
	If PostSettings.SawingSettings.CalcFitIn <> SaegeEinpassenVerrechnen Then
		PostSettings.WriteBool("NC","SaegeEinpassenVerrechnen",SaegeEinpassenVerrechnen)
		Err = Err + "SaegeEinpassenVerrechnen;"
	End If
	If PostSettings.SawingSettings.CalcHalfSBB <> SaegeBlatthalbeVerrechnen Then
		PostSettings.WriteBool("NC","SaegeBlatthalbeVerrechnen",SaegeBlatthalbeVerrechnen)
		Err = Err + "SaegeBlatthalbeVerrechnen;"
	End If
	If PostSettings.SawingSettings.CalcSawLength <> SaegeLaengeVerrechnen Then
		PostSettings.WriteBool("NC","SaegeLaengeVerrechnen",SaegeLaengeVerrechnen)
		Err = Err + "SaegeLaengeVerrechnen;"
	End If
	If PostSettings.SawingSettings.CalcSawRadius <> SaegeRadiusVerrechnen Then
		PostSettings.WriteBool("NC","SaegeRadiusVerrechnen",SaegeRadiusVerrechnen)
		Err = Err + "SaegeRadiusVerrechnen;"
	End If
	If PostSettings.SawingSettings.CalcSBB <> SBBVerrechnen Then
		PostSettings.WriteBool("NC","SBBVerrechnen",SBBVerrechnen)
		Err = Err + "SBBVerrechnen;"
	End If
	If PostSettings.SawingSettings.TwoSawingToOne <> TwoSawingToOne Then
		PostSettings.WriteBool("EINST","TwoSawingToOne",TwoSawingToOne)
		Err = Err + "TwoSawingToOne;"
	End If
	If PostSettings.SawingSettings.TwoSawingToOneMaxDist>9 Then
		' Wert plausibilisieren ?
		Err = Err + "wrong value TwoSawingToOneMaxDist"
	End If
	If PostSettings.SawingSettings.TwoSawingToOneSafety<2 Then
		' Wert plausibilisieren
		Err = Err + "wrong value TwoSawingToOneSafety"
	End If

	If PostSettings.SawingSettings.ExtSawCut <> ExtentedSawingCut Then
		PostSettings.WriteBool("EINST","ExtentedSawingCut",ExtentedSawingCut)
		Err = Err + "ExtentedSawingCut;"
	End If
	If PostSettings.SawingSettings.SawingAsMilling <> SawingAsMilling Then
		PostSettings.WriteBool("EINST","SawingAsMilling",SawingAsMilling)
		Err = Err + "SawingAsMilling;"
	End If

' Winkelgetriebe auf 5-Achskopf
	If PostSettings.GeneralSettings.GBOn5AxisFreeTipA <> GBOn5AxisFreeTipA Then
		PostSettings.WriteBool("NC","GBOn5AxisFreeTipA",GBOn5AxisFreeTipA)
		Err = Err + "GBOn5AxisFreeTipA;"
	End If
	

	If Err <> "" Then 
		pp_Err(5,Err+ " wrong entry automatically corrected")
	End If
End Function

Function wcnc_nci_10_or_11(Typ,No)
Dim StrVariant As Variant
Dim Typstr As String
Dim C,i As Long

	If Typ=10 Then
		Typstr="NC_BEFORE"+inttos(No)
	ElseIf Typ=11 Then
		Typstr="NC_AFTER"+inttos(No)
	Else
		pp_Err(0,"NCINFO 10/11")
	End If
	
	C = PostSettings.ReadSectionCount(Typstr)
	
	If C > 0 Then
		wcncCom("*************NCInfo "+Typstr+" Start *******************")
	
		For i = 0 To C-1 
			
			PostSettings.ReadSectionNo(Typstr,i,StrVariant)
			If Len(StrVariant)>0 Then
				wcnc(StrVariant)
			End If
				
		
		Next i
	    wcncCom("*************NCInfo "+Typstr+" End    *******************")
	Else
		pp_Err(1555,Typstr)
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
		AddMistake("Post Engine " + Replace(Target_Version,";",".") +" Or higher necessary")		
	End If
	
End Function


Function ProcessInfo_Init(PP As TProcessPara)
	PP.PLNo = -1
	PP.ToolID = -1
	Set PP.Tool = Nothing
	PP.HeadInfo = ""
	PP.HId = -1
	PP.ProcInfoStr = ""
	PP.Feedrate = -1
	PP.I_Feedrate = -1
	PP.S_Feedrate = -1
	PP.Speed = -1
	PP.MMode = -1
	PP.ObjectTyp = -1
	PP.PreObjectTyp = -1
	PP.MinRotA = -99999
	PP.MaxRotA  = -99999
	PP.MinTipA  = -99999
	PP.MaxTipA  = -99999
	PP.DustPosNCIExt = False
	ReDim PP.NCIExtB(0)
	ReDim PP.NCIExtA(0)
	Set PP.NTool = Nothing
	PP.NHeadInfo = ""
	PP.TipA = 0
	PP.RotA = 0
	PP.HeadTipA = 0
	PP.HeadRotA = 0
	PP.HeadSPAX = 0    ' 1. Anfahrposition in X fuer Werkzeugwechsel
	PP.HeadSPAY = 0    ' 1. Anfahrposition in Y fuer Werkzeugwechsel
	PP.HeadSPAZ = 0    ' 1. Anfahrposition in Z fuer Werkzeugwechsel
End Function


Sub ProcessInfo_Set(PListNo)  ' gibt die ProcessNummer des folgenden Prozesses
Dim p As TProcessPara

Dim Obj
Dim MMPs As NCMillingMPs
Dim MP As NCMillingPoints
Dim min As Variant
Dim max As Variant
Dim mint As Variant
Dim maxt As Variant
Dim T As tHopsBasicToolExt
Dim SicMode As Integer
Dim isOK As Boolean 
'Dim PExt As Object
'Dim PExtE As IIHeadExt

Dim P_MinMax As NCProcessMinMaxInfo

'NCData.GetExtInfo(ekHead_SimuAdditions,T.h) -> [IIAdditions@0x05DC2630]

	' ALLES AUSGANGSZUSTAND
	ProcessInfo_Init(p)
	
	p.PLNo = PListNo
	
	Set Obj = NCData.ProcessList.GetProcess_NCInfoIndex(PListNo-1)
	
	p.ObjectTyp = Obj.ObjectTyp
	p.PreObjectTyp = Obj.ObjectTyp
	
	p.ToolID = Obj.ToolID
	Set p.Tool = Obj.Tool
	If equal(p.Tool.ToolType,1000) Then
		' Laserwerkzeug darf hier nie ankommen
		pp_Err(126,"Lasertool ?")
	End If
	
	' naechsten Werkzeug
	If Not NCData.ProcessList.GetProcess_NCInfoIndex(PListNo) Is Nothing Then
		Set p.NTool = NCData.ProcessList.GetProcess_NCInfoIndex(PListNo).Tool
		p.NHeadInfo = NCData.ProcessList.GetProcess_NCInfoIndex(PListNo).HeadInfo
	'Else
		'Set P.NTool = Nothing   erfolgt im init
	End If
	
	p.HeadInfo = Obj.HeadInfo
	If IsNumeric(p.HeadInfo) Then
		p.HId = Val(p.HeadInfo)   ' 
	Else
		pp_Err(126,"HeadInfo")
	End If
	
'	Set PExt = TDATA.GetHead_ID(1)
'	PExtE = HeadExt(PExt)
	
	'PExt.CheckFeedrate
	
	
	MT_SetTHopsBasicToolExt(T,p.ToolID,p.HId)
	
	
	Select Case p.ObjectTyp
		Case otNotdefinied
			' 0: nicht definiert
		Case otNCInfo
			' 1: Ncinfo
		Case otMillingMPs  
			' 11: statische Ausrichtung, Bearbeitung auf einer Ebene
			Set MMPs = Obj
			'		'		MMPs.MillingList.GetMillingElement_Index(0).GetAxAyAz(ax,ay,az)
			'		'		' MMPs.HeadOffX|y|z
			'		MMPs.CalcMinMaxRotAngleCAchs(min,max)
			'		MMPs.CalcMinMaxRotAngleCAchs
			'		MMPs.CalcMinMaxRotAngle5Achs
			'		MMPs.
			'		P.minrota=min
			'		P.MaxRotA=max
			p.MMode = MMPs.Mode '   Obj.Mode
			p.PreObjectTyp = MMPs.PreObjectTyp
			
			
			p.HeadRotA = MMPs.HeadRotA ' -> 20.3385402129464#
			p.HeadTipA = MMPs.HeadTipA ' -> 59.9414895296074#
			
			p.RotA = MMPs.View.RotA
			p.TipA = MMPs.View.TipA
			
			' zurueckrechnen auf Hops Ebene
			p.RotA = (- p.RotA)
			p.TipA = (p.TipA - 180)
			
			' TCP - Stellung vom Head berechnen (mathematisch)
			p.RotA = Norm0_360(( - p.RotA ) + 180)
			p.TipA = p.TipA 
			MMPs.HeadMPsBefore.GetXYZ(MMPs.HeadMPsBefore.NCMillingPointsCount-1,p.HeadSPAX,p.HeadSPAY,p.HeadSPAZ)
			
			'Set P_MinMax = NCData.GetExtInfo(ekNCProcess_HeadMinMax,MMPs) ' -> [INCProcessMinMaxInfo@0x0B7D77F0]
			'p.Minx = P_MinMax.Minx
			'p.Maxx = P_MinMax.Maxx
			'p.Miny = P_MinMax.Miny
			'p.Maxy = P_MinMax.Maxy
			
			
			'NCData.GetExtInfo(ekHead_SimuAdditions,T.h) -> [IIAdditions@0x05DC2630]
			p.ProcessGroup = NCData.GetExtInfo(ekNCProcess_ProcessGroup,MMPs)
			'p.HeadSPAX = p.HeadSPAX - T.h.CenterX
			'p.HeadSPAY = p.HeadSPAY + T.h.CenterY
			'p.HeadSPAZ = p.HeadSPAZ - T.h.CenterZ
			
		Case otMillingPoints
			' 10: C-Achsfraesen oder Vektorfraesen/5-Achsfraesen
			Set MP = Obj
			'		MP.GetMinMaxRotTipAngle(min,max,mint,maxt)
			'		P.MinRotA=min
			'		P.MaxRotA=max
			'		P.MinTipA=mint
			'		P.MaxTipA=maxt
			p.MMode = MP.MMode '   Obj.Mode
			p.PreObjectTyp = MP.PreObjectTyp
					
			MP.NCMillingHeadPoints.GetRotATipA(0,p.HeadRotA, p.HeadTipA) ' -> 20.3385402129464#    -> 59.9414895296074#
			MP.NCMillingPoints.GetRotATipA(0,p.RotA, p.TipA)
			
			MP.HeadMPsBefore.GetXYZ(MP.HeadMPsBefore.NCMillingPointsCount-1,p.HeadSPAX,p.HeadSPAY,p.HeadSPAZ)
			'.NCMillingHeadPoints.GetXYZ(0,p.HeadSPAX,p.HeadSPAY,p.HeadSPAZ)
			'p.HeadSPAX = p.HeadSPAX - T.h.CenterX
			'p.HeadSPAY = p.HeadSPAY + T.h.CenterY
			'p.HeadSPAZ = p.HeadSPAZ - T.h.CenterZ
			
			'Set P_MinMax = NCData.GetExtInfo(ekNCProcess_HeadMinMax,MP) ' -> [INCProcessMinMaxInfo@0x0B7D77F0]
			'p.Minx = P_MinMax.Minx
			'p.Maxx = P_MinMax.Maxx
			'p.Miny = P_MinMax.Miny
			'p.Maxy = P_MinMax.Maxy
			
			'NCData.GetExtInfo(ekHead_SimuAdditions,T.h) -> [IIAdditions@0x05DC2630]
			p.ProcessGroup = NCData.GetExtInfo(ekNCProcess_ProcessGroup,MP)
			

		Case otNCInfoProcess
			' 7: NCINFOProcess
		Case otDHProcess
			' 9: Bohrkopf
			
		Case otNCInfoProcessMPs			
			' 12: NCInfoProcess als Milling
		
		Case Else
			pp_Err(0)

	End Select 
	
	
	Set P_MinMax = NCData.GetExtInfo(ekNCProcess_HeadMinMax,Obj) ' -> [INCProcessMinMaxInfo@0x0B7D77F0]
	If Not P_MinMax Is Nothing Then
		p.Minx = P_MinMax.Minx
		p.Maxx = P_MinMax.Maxx
		p.Maxy = P_MinMax.Maxy
		p.Miny = P_MinMax.Miny
		If Not T.h Is Nothing Then
			p.Minx = p.Minx - T.h.CenterX
			p.Maxx = p.Maxx - T.h.CenterX
			p.Miny = p.Miny + T.h.CenterY
			p.Maxy = p.Maxy + T.h.CenterY
		End If
		
	End If
	p.ProcessGroup = NCData.GetExtInfo(ekNCProcess_ProcessGroup,Obj)
	
	p.ProcInfoStr  = GetStrObjectTyp(Obj)  ' MW 04.05.2016
	
	Select Case p.PreObjectTyp
			Case otNotdefinied
				p.ProcInfoStr = "not definied"
		    Case otNCInfo
				p.ProcInfoStr = "NCInfo"
		    Case otMilling
				p.ProcInfoStr = "Milling" + IIf(p.MMode=1," with C-Axis",IIf(p.MMode=2," 5Axis",""))
			Case otVertDrilling 		    
				p.ProcInfoStr = "VertDrilling"
			Case otHorzDrilling 		   
				p.ProcInfoStr = "HorzDrilling"
			Case otSawing 		    
				p.ProcInfoStr = "Sawing"
			Case otNCProcess 		    
				pp_Err(1569)  ' darf nicht vorkommen
				p.ProcInfoStr = "NCProcess"
			Case otNCInfoProcess 		    
				p.ProcInfoStr = "NCInfoProcess"
			Case otNCContourProcess 		    
				pp_Err(1569)  ' darf nicht vorkommen
				p.ProcInfoStr = "NCContourProcess"
			Case otDHProcess 		    
				p.ProcInfoStr = "DHProcess"
			Case otMillingPoints 		    
				p.ProcInfoStr = "MillingPoints"
			Case otMillingMPs		    
				p.ProcInfoStr = "MillingMPs"
			Case otNCInfoProcessMPs 
				' NCinfoProcess - ProcessKind = 1/2 = Drilling/Milling
				p.ProcInfoStr = "NCInfoProcessMPs"
	End Select 
	
	' Vorschuebe bereits plausibilisiert auf MIN/MAX !!!
	p.Feedrate = Obj.Feedrate
	p.I_Feedrate = Obj.MoveInFeedrate
	p.S_Feedrate = Obj.MoveOutFeedrate
	p.Speed = Obj.RotSpeed
	
	
	' MW 18.04.2016
	' Haubenpos / Haubensteuerung
'	p.SuctionPos = MT_Get_HaubenPos(T)
	


	PPara = p   ' -> Zuweisung auf global Para
	MT_ClearTHopsBasicToolExt(T)
	Set Obj = Nothing
	Set MMPs = Nothing
	Set MP = Nothing
	Set P_MinMax = Nothing

	JobPara.P_Info = "Process [#"+inttos(PPara.PLNo)+ "] Kind:<" + PPara.ProcInfoStr +">"+ " - BOXID:<"+inttos(PPara.ToolID)+"> T:<"+Get_TN_Info(PPara.ToolID)+"> "+ " HId:<"+inttos(PPara.HId)+ ">" + _
	       " Xmin:"+ftos(PPara.Minx) + " Xmax:"+ftos(PPara.Maxx) + _
	       " Ymin:"+ftos(PPara.Miny) + " Ymax:"+ftos(PPara.Maxy) 

End Sub



Function pp_Err(Err,Optional var1,Optional var2,Optional var3, Optional var4)
Dim Err_de,Err_en As String 

	GetErrorCode(Err,Err_de,Err_en,var1,var2,var3,var4)

	If (JobPara.language.ID=1031) Or (Err_en="") Then
		' Deutsch
		AddMistake(Get_ErrMsg(Err,Err_de,1) )
	Else
		' International
		AddMistake(Get_ErrMsg(Err,Err_en,1) )
	End If
	
	Stop
	Exit All
	
	
End Function


Function Get_ErrMsg(Err,stri,Mode) As String

'Dim iiSet As Object
'Dim Language As Object
Dim errstri As Variant
'Dim path As String
'Dim path_Default As String

'	path  = JobPara.hopspath+"language\moduls\ppscript\ppscript"+JobPara.language.Ext+".ini"
'	path_Default  = JobPara.hopspath+"language\moduls\ppscript\ppscript"+JobPara.language.Ext_Default+".ini"
  
'	Set iiSet = CreateObject("BasicExt5.BasicExtension5")	
'	errstri = iiSet.IniFileReadstr(path,"errmsg",IntToS(Err),"")
'	If errstri="" Then
'  		errstri = iiSet.IniFileReadstr(path_Default,"errmsg",IntToS(Err),stri)
'	End If

	If Mode=1 Then
		errstri = errstri + "PP.Error #"+IntToS(Err)+" / " + stri
	End If
	If Len(JobPara.P_Info)>0 Then
		errstri = errstri + Chr(13)+Chr(10)+JobPara.P_Info
	End If
	If Marker.wp_actindex>=0 Then
		If Len(WPI(Marker.wp_actindex).WPName)>0 Then
			errstri = errstri + Chr(13)+Chr(10)+WPI(Marker.wp_actindex).WPName
		End If
	End If
	Get_ErrMsg = errstri
'   	Set iiSet = Nothing
	
End Function



Function GetErrorCode(ErrNo,Err_de,Err_en,Optional var1,Optional var2,Optional var3, Optional var4)
	Err_de = ""
	Err_en = ""

	Select Case ErrNo
	Case 0 
		Err_de = "es ist ein unerwarteter Fehler aufgetreten ["+var1+"]"
		Err_en = "it encountered an unexpected error ["+var1+"]"
	Case 1
		Err_de = "Diskrepanz zwischen Setup und Script Versionen! - Script Version["+var1+"] Setup Version:["+var2+"]"
		Err_en = "Version between Setup and Script not equal! - Script Version["+var1+"] Setup Version:["+var2+"]"
	Case 2 
		Err_de = " - bitte Postprozessorlauf erneut starten"
		Err_en = " - please restart Post"
	Case 3 
		Err_de = "falsches Werkzeug, oder ungueltiger Werkzeugtyp"
		Err_en = "wrong Tool or wrongg Tooltype"
	Case 4 		
		Err_de = "es ist ein unerwarteter Fehler ist aufgetreten - die Prozessanzahl der Kanaele ist unterschiedlich"
		Err_en = "it encountered an unexpected error - the number of processes in the channels is different"
	Case 5
		Err_de = "falsche Einstellung in der Datei PP.ini [" + var1 + "]"
		Err_en = "wrong settings found in file PP.ini [" + var1 + "]"
	Case 6
		Err_de = "Dieses Funktionalitaet ist noch nicht implementiert [" + var1+"]"
		Err_en = "This functionallity is not yet implemented [" + var1+"]"
	Case 7
		Err_de = "Die Funktionalitaet dieser ID wird nicht unterstuetzt - Maschine - Parameter - ID[" + var1+"]"
		Err_en = "The functionallity of the used ID - Machine - Parameter - ID[" + var1+"] is not supported anymore"
	Case 10
		Err_de = "Werkzeug "+ var1 +" - ist derzeit nicht geruestet! Agg:"+var2
		Err_en = "Tool "+ var1 +" - Not found On Toolchanger! Agg:+var2
	Case 11	
		Err_de = "Werkzeug "+var1 + " - ID 100001=1 - Korrekturtyp 1 steuerungsseitig nicht moeglich"
		Err_en = "Tool "+var1 + " - ID 100001=1 - Saw 5Axis Correction-Type =1 not possible"
	Case 12 
		Err_de = "ungueltiger Werkzeugtyp beim Saegen "
		Err_en = "not allowed kind of Tool for sawing"
	Case 13
		Err_de = "Spindel nicht definiert"
		Err_en = "spindle not defined"
	Case 15
		Err_de = "Erweitertes Saegen - bei dieser Option muss die Einstellung [Saegeradius verrechnen] aktiv sein"
		Err_de = "Sawing extended - impossible without calculating the saw radius - check adjustments in postprocessor"
	Case 20 
		Err_de = "Softwareende [X-] erreicht ["+var1+"]"
		Err_en = "Softwarelimit [X-] reached ["+var1+"]"
	Case 21
		Err_de = "Softwareende [X+] erreicht ["+var1+"]"
		Err_en = "Softwarelimit [X+] reached ["+var1+"]"
	Case 30 
		Err_de = "Softwareende [Y-] erreicht ["+var1+"]"
		Err_en = "Softwarelimit [Y-] reached ["+var1+"]"
	Case 31
		Err_de = "Softwareende [Y+] erreicht ["+var1+"]"
		Err_en = "Softwarelimit [Y+] reached ["+var1+"]"
	Case 40 
		Err_de = "Softwareende [Z-] erreicht ["+var1+"]"
		Err_en = "Softwarelimit [Z-] reached ["+var1+"]"
	Case 41
		Err_de = "Softwareende [Z+] erreicht ["+var1+"]"
		Err_en = "Softwarelimit [Z+] reached ["+var1+"]"
	Case 100
		Err_de = "Kanal fuer Werkzeug "+var1 + " nicht gefunden - oder konnte nicht ermittelt werden"
		Err_en = "Channel for tool "+var1 + " not found"
	Case 101
		Err_de = "Unterflurbearbeitung mit Bohren - Technologie nicht moeglich"
		Err_en = "Underside working with drilling - technologie not possible"
	Case 102
		Err_de = "Ebenenueberpruefungg - Bearbeitung mit diesem Werkzeug auf dieser Ebene nicht moeglich - Ebene ["+var1+"]"
		Err_en = "Check View - Working with this Tool on this Side not possible ["+var1+"]"
	Case 103 
		Err_de = "Werkzeug kann pneumatische Arbeitsstellung nicht erreichen"
		Err_en = "Tool can not find pneumatic working position"
	Case 104
		Err_de = "Werkzeug kann erforderliche Arbeitsposition nicht erreichen"
		Err_en = "Tool can't reach working position"
	Case 105
		Err_de = "C-Achsenfraesen - Werkzeug kann erforderliche Arbeitsposition nicht erreichen"
		Err_en = "Milling with Rotation Axis - Tool can't reach working position"
	Case 106 
		Err_de = "Werkzeugradiuskompensation zusammen mit G2/G3 wird von Maschine nicht unterstuetzt"
		Err_en = "Tool radius compensation together with G2/G3 not supported from machine controller"
	Case 110 
		Err_de = "Unterflurbearbeitung auf der Ebene " +var1 +" nicht moeglich"
		Err_en = "underside working on view " +var1 +" not possible"
	Case 126
		Err_de = "Inkonsistenz im Postprozessor Script gefunden - "
		Err_en = "inconsistency found in Postprocessor Script - "	
	Case 140 
		Err_de = "Ungueltiger Wert bei Maschinenparameter ID:"+var1
		Err_en = "wrong value - Machine parameter ID:"+var1
	Case 150 
		Err_de = "Fehler bei Ermittlung des Werkzeugwechsler Typs - Werkzeug:"+var1
		Err_en = "Error while checking Toolchanger of Tool:"+var1
	Case 154
		Err_de = "Ausgangsrichtung/Kippstellung Min:"+var1+" Max:"+var2+" des Winkelgetriebes kann nicht erreicht werden - Limit ueberschritten"
		Err_en = "Orientationi Gearbox Min:"+var1+" Max:"+var2+" can not be reached - limit exceeded"
	Case 157
		Err_de = "Keine Werkzeugwechsel - Spindel gefunden"
		Err_en = "No Toolchanger Spindle found"
	Case 159 
		Err_de = "Fehler bei Ermittlung der Saegestellung pneum. Saege"
		Err_en = "error while checking sawing position of pneumatic saw"
	Case 160 
		Err_de = "Falsche Definition des Arbeitskopfes"
		Err_en = "wrong definition of Processhead"
	Case 162 
		Err_de = "Fraesen mit C-Achse - unerlaubter KippWinkel - [" +var1+"]
		Err_en = "C-Axis milling - wrong tilting angle - [" +var1+"]
	Case 163
		Err_de = "Fraesen mit C-Achse - unerlaubtes Werkzeug - [" +var1+"]
		Err_en = "C-Axis milling - wrong tool - [" +var1+"]
	Case 164
		Err_de = "Kippwinkel des Aggregats <"+var2+"> - ungleich dem Winkel der Arbeitseben <"+var1+">"
		Err_en = "Tilting angle of Tool <"+var2+"> - not equal to working surface <"+var1+">"
	Case 165
		Err_de = "Spindeldrehrichtung nicht korrekt ["+var1+"] - Werkzeugdaten ueberpruefen"
		Err_en = "Spindle rotation direction no correct ["+var1+"] - please check Tools"
	Case 166
		Err_de = "undefinierte Spindeldrehrichtung"
		Err_en = "not defined spindle rotation direction"
	Case 170
		Err_de = "Gleiches Werkzeug wird auf 2 unterschiedlichen Spindeln benutzt " + var1 
		Err_en = "same Tool on different Heads used not possible "+ var1
	Case 180
		Err_de = "Fehler bei Ermittlung Min MaxRange X/Y/Z"
		Err_en = "error while calculate min/max Range"
	Case 181
		Err_de = "Parameter Ref-Spindel " +var1
		Err_en = "Parameter Ref-Spindel " +var1
	Case 185
		Err_de = "Fehler beim Lesen der ID #"+var1 + " "+ var2 + " - Bearbeitungskopf"
		Err_en = "error reading ID #"+var1 + " "+ var2 + " - Processhead"
	Case 186
		Err_de = "Kanal nicht gefunden"
		Err_en = "Channel not found"
	Case 187 
		Err_de = "Parkposition fuer C-Achse nicht gefunden"
		Err_en = "liftpos/parkpos C-Axis not found for"
	Case 188
		Err_de = "angegebene Tiefe ist zu gross"
		Err_en = "wrong depth or depth to much"
	Case 189
		Err_de = "Falscher Saegewinkel fuer Saegen mit Zyklus (G7/G9)"
		Err_en = "wrong sawing angle while using (G7/G9)"
	Case 190
		Err_de = "zugehoeriger Achsname nicht gefunden - "+var1
		Err_en = "Axis name not found - "+var1
	Case 191
		Err_de = "Etikettieren aktiv - hierzu muss der Plausibilisierungsvorlauf aktiviert werden"
		Err_en = "Labeling activ - please activate the option Plausicheck"
	Case 192
		Err_de = "Ordner der Labeldatei nicht gefunden - ["+var1+"]"
		Err_en = "Label Filepath not found - ["+var1+"]"
	Case 193 
		Err_de = "PP.INI - Einstellung WriteInitZero auf 1 geaendert - Postprozessor bitte erneut starten"
		Err_en = "Setting WriteInitZero Set To 1 - Please Start once again"
	Case 194
		Err_de = "PP.INI - Einstellung (Saegen als Fraesen) wird noch nicht unterstuetzt - Bitte Einstellung pruefen"
		Err_en = "Option sawing as milling not yet possible - please check post adjustments"
	Case 195
		Err_de = "Diese Version (alte Engine) des Postprozcessors wird nicht mehr unterstuetzt [" + var1+"]"
		Err_en = "postprocessor - old engine not longer supported " + var1
	Case 196
		Err_de = "Achtung ! Evtl. nicht lesbares Zeichen im NC-Programmnamen"
		Err_en = "Attention! Possibly unreadable characters in the NC program name"
	Case 197 
		Err_de = "Diese Funktionalitaet wurde noch nicht freigegeben - unterschiedliche Werkstueckdicken"
		Err_en = "this functionality was not testet yet - different z levels"
	Case 198
		Err_de = "Falsche Werkzeugart beim C-Achsenfraesen "
		Err_en = "wrong Tooltype for Milling with C-Axis "
	Case 199 
		Err_de = "Falsche Einstellung im Posptrozessor - Einstellung Bohren - als Fraesbahn pruefen"
		Err_en = "wrong option set in Adjustments - drilling as milling"
	Case 200
		Err_de = "PP.INI - Einstellung beim Saegen nicht korrekt - muss auf den Modus (SAWINGEXT) gesetzt werden"
		Err_en = "wrong setting in post - please set sawingext activ"
	Case 201
		Err_de = "DLL_Milling mit Spaeneleitblech wird nicht unterstuetzt"
		Err_en = "DLL_Milling with Deflector not supported in this Version"
	Case 202
		Err_de = "DLL_Milling wird in dieser Version nicht unterstuetzt"
		Err_en = "DLL_Milling not supported in this Version"
	Case 203
		Err_de = "Dieser Modus des An-/Abfahren ist in Kombination mit Spaeneleitblech nicht moeglich"
		Err_en = "This kind of move in / move out in Combination with the deflector not possible"
	Case 204
		Err_de = "Leitblechradius in NCI 7999 nicht definiert"
		Err_en = "Radius of the Deflector not set correct - NCINFO 7999"
	Case 205
		Err_de = "Radiuskorrektur darf nicht mittig sein (Spaeneleitblech)"
		Err_en = "Tool radius correction (Toolcenter) not possible with Deflector"
	Case 206
		Err_de = "Bearbeitungskopf/ProcessHead [" + inttos(var1) + "] ID "+inttos(var2) +" fehlt oder nicht gefunden - Spaeneleitblech Boxnummer"
		Err_en = "Processhead [" + inttos(var1) + "] ID "+inttos(var2) +" not found - Deflector ID - Number"
	Case 207
		Err_de = "Werkzeug Zusatzinformation ID :"+inttos(var1)+ " nur zulaessig fuer Saegewerkzeuge auf 5-Achs Arbeitskopf"
		Err_en = "Tool Addition ID :"+inttos(var1)+ " only possible for 5-Axis Head!"
	Case 220
		Err_de = "Keine korrekte Szene gefunden "
		Err_en = "unexpected error - no clamp situations found "
	Case 224
		Err_de = "5-Achs falsches Werkzeug fuer diesen Vorgang"
		Err_en = "5-Axis wrong tool "
	Case 400 
		Err_de = "nicht erlaubtes Werkzeug beim Oberflaechenfraesen ["+var1+"] - ["+var2+"]"
		Err_en = "wrong Tool surface milling ["+var1+"] - ["+var2+"]"
	Case 401
		Err_de = "nicht geeignetes Werkzeug beim Fraesvorgang gefunden ["+var1+"] - ["+var2+"]"
		Err_en = "wrong Tool found for milling ["+var1+"] - ["+var2+"]"
	Case 459
		Err_de = "Fehler bei Ermittlung der Rasterstellung - geeignete Richtung nicht gefunden"
		Err_en = "error while checking pneumatic working position - position not found"
	Case 508
		Err_de = "Falsche Einstellung in der PP-Engine - Einstellung beim Fraesen (An/Abfahrbewegung berechnen) auf ja setzen"
		Err_en = "wrong entry for PP-Engine - please set calculate leadin/leadout to yes"
	Case 517
		Err_de = "Achtung ! Evtl. nicht lesbares Zeichen im NC-Programmnamen"
		Err_en = "Possibly unreadable characters in the NC program name"
	Case 530
		Err_de = "In Einstellungen muss fuer Trenner An/Abfahrbewegung 500 gewaehlt sein"
		Err_en = "NCINFO - Setting for start_type/end_type must be selected with Type=500"
	Case 535
		Err_de = "Makro SPKW (NCINFO 7005) wird in NCHOPS V6.x nicht unterstuetzt"
		Err_en = "Macro SPKW (NCINFO 7005) is not supported anymore in NCHOPS V6.x"
	Case 538
		Err_de = "Spannsituation nicht gefunden"
		Err_en = "clampsituation not found"
	Case 541
		Err_de = "Bearbeitung auf gespiegeltem Nullpunkt #"+var1 + " nicht moeglich"
		Err_en = "Working on machine side mirrored zeropoint #"+var1 + " not possible"
	Case 543
		Err_de = "Die Definition einer zusaetzlichen Ueberfahrhoehe ist nicht erlaubt "+FToS(var1)+")"
		Err_en = "Definition of additional above Height not possible "+FToS(var1)+")"
	Case 544 
		Err_de = "Der definierte Stop (M200, M201, M203) ist in Kombination mit Multizone nicht moeglich"
		Err_en = "programmed Stop (M200, M201, M203) in combination with multizone not possible"
	Case 545 
		Err_de = "Der programmierte Maschinenstopp wurde programmiert, ohne dass ein Werkzeug zuvor aktiv ist"
		Err_en = "the  Machine stop was programmed without having a activ Tool"
	Case 546
		Err_de = "Nullpunkt nicht gefunden - Evtl. Grundpositionsdatei neu speichern ? #"+ var1
		Err_en = "Zeropoint not found #"+var1
	Case 580
		Err_de = "Die definierte Messquote ueberschreitet den maximal zulaessigen Wert ["+ var1+ ">"+var2  +"]"
		Err_en = "Defined measure quote exceeds the maximum allowed value ["+ var1+ ">"+var2 + "]"
	Case 550
		Err_de = "Werkzeug ID10001=1 -Werkzeug steuerungsseitig mit mehreren Schneiden gefunden - Aber Schneidenanzahl ungueltig"
		Err_en = "Tool with ID10001=1 found - but only 1 cuttting edge found. This is not possible!"
	Case 554 
		Err_de = "Die Einstellung [G0 zwischen Bohrungen] ist nicht moeglich - bitte Engine - Einstellung korrigieren"
		Err_en = "Engine Setting [G0 between drilling] impossible"
	Case 602 
		Err_de = "Die Einstellung - [immer gleicher NCName] ist beim Arbeiten mit Workcenter nicht moeglich (ID:1050)" 
		Err_en = "_name of program ? - The setting equal NC Name not possible! (ID:1050)"
	Case 1500
		Err_de = "Werkzeug nicht gefunden - BoxID:" + Str(var1)
		Err_en = "Tool not found - BoxID:" + Str(var1)
	Case 1501
		Err_de = "Die Einstellung fuer WriteInitZero wurde auf 1 gesetzt - bitte erneut Starten"
		Err_en = "Setting WriteInitZero set to 1 - Please Start Post once again"
	Case 1502
		Err_de = "Tooling Group wurde nicht gefunden"
		Err_en = "WT - Group end not found"
	Case 1503
		Err_de = "G-Bewegung G0 ist nicht vorgesehen - Bitte Einstellungen pruefen"
		Err_en = "Moving with G0 is not foreseen in the Post"
	Case 1504
		Err_de = "Eine Aenderung der Radiuskorrektur im Konturverlauf ist nicht moeglich"
		Err_en = "A change of the radius compensation in the contour is not possible"
	Case 1505
		Err_de = "Falsche Kontur fuer LRout_X - es darf nur ein Konturelement definiert sein"
	Case 1506
		Err_de = "wrong sawing direction"
	Case 1509
		Err_de = "Keine Kantenbearbeitung fuer dieses Kontur gefunden!"
	Case 1510
		Err_de = "Nur eine Kantenbearbeitung pro Kontur zugelassen!"
	Case 1511
		Err_de = "Downloading PIECE not possible with this working mode!"
	Case 1512 
		Err_de = "Maschinentyp ungueltig oder nicht definiert"
	Case 1513
		Err_de = "Post Engine " + Replace(var1,";",".") +" Or higher necessary"		
	Case 1514 
		Err_de = "Ungueltiger Wert bei Maschinenparameter ID:"+IntToS(var1)
	Case 1515
		Err_de = "String to long <<"+var1+">> Max:"+IntToS(var2)
	Case 1516
		Err_de = "Function ISO_Write - wrong parameter found"
	Case 1517
		Err_de = "Bogenfehler G" + IntToS(var1)+ " X"+FToS(var2)+ " Y"+FToS(var3)
	Case 1518
		Err_de = "Radiales Anfahren - minimaler Faktor "+FToS(var1)
	Case 1519
		Err_de = "lateral lead in not possible - minimum faktor "+FToS(var1)
	Case 1520
		Err_de = "wrong tooltype"
	Case 1521
		Err_de = "BiesseWorks cannot handle this type of movement"
	Case 1522
		Err_de = "LRout_X es ist nur eine Kontur moeglich"
	Case 1523
		Err_de = "wrong view found"
	Case 1524
		Err_de = "view not found - unexcepted error"
	Case 1525
		Err_de = "Falsche Sauger/Trav Move"
	Case 1526
		Err_de = "wrong Macro CALL " + var1 +" Params:"+var2
	Case 1528
		Err_de = "View 0 with Offset found - not possible"
	Case 1529
		Err_de = "Programmed Deflector not found"
	Case 1530
		Err_de = "Deflector not found"
	Case 1531
		Err_de = "unknown ObjectType"
	Case 1532
		Err_de = "Processhead ID:" + IntToS(var3)+" special ID "+var1+ " not found Tool ID:" + var2 
	Case 1533 
		Err_de = "Processhead ID:" + IntToS(var1) + "missing or wrong ID:103000"
	Case 1534
		Err_de = "Processhead ID:" + IntToS(var1) + "missing or wrong ID:103001"
	Case 1535
		Err_de = "NCINFO <<"+IntToS(var1) +">> WIRD NICHT UNTERSTUETZT!"
		Err_en = "NCINFO <<"+IntToS(var1) +">> NOT SUPPORTED!"
	Case 1536
		Err_de = "error with NCI 7050/8050 "
	Case 1537
		Err_de = "Falscher Mode NCINFO 7005 Para1"
	Case 1538
		Err_de = "Bitte im PP unter Einstellungen Fraesen ->Fraeserradiuskorrektur auf freier Ebene berechnen <- deaktivieren !"
	Case 1539
		Err_de = "Bitte im PP unter Einstellungen Fraesen ->Radiuskorrekturlinien am Start und Ende loeschen <- deaktivieren !"
	Case 1540
		Err_de = "Bitte unter Einstellungen Fraesen An/Abfahrbewegung ->ohne Radiuskorrekturaufbau und Sicherheit ausgeben<- setzen!"
	Case 1541
		Err_de = "PP.INI - Einstellung neu gesetzt ->bitte nochmals starten<- !"
	Case 1542
		Err_de = "Parameter ["+(var1)+"] kann nicht ueberschrieben werden " 
	Case 1543
		Err_de = "Ordner nicht gefunden <"+var1+">"
		Err_en = "Folder not found <"+var1+">"
	Case 1545
		Err_de = "Werkzeug nicht geruestet"
		Err_en = "Tool not fitted on Head or Toolchanger"
	Case 1546
		Err_de = "Bitte unter Einstellungen Fraesen An/Abfahrbewegung ->ohne Radiuskorrekturaufbau und Sicherheit ausgeben<- setzen!"
	Case 1547
		Err_de = "Bitte unter Einstellungen Fraesen An/Abfahrbewegung auf ->nicht ausgeben<- !"
	Case 1548
		Err_de = "Werkzeug nicht geeignet fuer diese Art der Bearbeitung"
	Case 1549
		Err_de = "PP.INI Eintrag [VERSION] - "+var1+" ungueltig"
		Err_en = "PP.INI entry [VERSION] - "+var1+" invalid"
	Case 1550
		Err_de = "Parameter [" +var1 + "] im Makro " +var2  + " nicht gefunden..  " 
	Case 1551
		Err_de = "Kippwinkel des Aggregats <" +FToS(var1)+"> ungleich der Arbeitsebene"
	Case 1552
		Err_de = "Falscher Funktionsaufruf "+ FToS(var1) + " kein " + var2 + " gefunden"
	Case 1553
		Err_de = "NCINFO #"+inttos(var1)+" wird in dieser Version nicht mehr unterstuetzt"
		Err_en = "NCINFO #"+inttos(var1)+" not supported in this version of Post"
	Case 1554
		Err_de = "Verschobene Ebene "+IntToS(var1)+ " nicht zulaessig - bitte PP Einstellungen kontrollieren"
	Case 1555
		Err_de = "PP.INI Eintrag "+var1+" nicht gefunden"
		Err_en = "PP.INI entry  "+var1+" not found"
	Case 1558
		Err_de = "Die Ebene der Bearbeitung wird derzeit nicht unterstuetzt ! - "+var1
		Err_en = "This view for working is not supported at the moment - "+var1
	Case 1559
		Err_de = "Falsche Ebene fuer Bearbeitung mit diesem Werkzeug"
		Err_en = "wrong view for this kind of work with this specified Tool"
	Case 1561
		Err_de = "Saege kann Bearbeitungsstellung nicht erreichen"
		Err_en = "saw can not reach the needed working position"
	Case 1563
		Err_de = "Ausgangsrichtung des Winkelgetriebes stimmt nicht mit der Arbeitsebene ueberein"
		Err_en = "This direction of the angular head does not correspond to the defined working view"
	Case 1564
		Err_de = "Die Arbeitsebene kann nicht mit dem Winkelgetriebe erreicht werden"
		Err_en = "The Working position (View) can not be reached with the angular head"
	Case 1568
		Err_de = "Dieser Art der Bearbeitung wird nicht unterstuetzt: (SurfaceMode:"+IntToS(var1)+")"+ "  (Mode:"+IntToS(var2)+")"
		Err_en = "This kind of working is not supported at the moment: (SurfaceMode:"+IntToS(var1)+")"+ "  (Mode:"+IntToS(var2)+")"
	Case 1569
		Err_de = "Dieser Art der Bearbeitung wird derzeit leider noch nicht unterstuetzt: "
		Err_en = "This kind of working is not supported at the moment"
	Case 1571
		Err_de = "Falsche Einstellung in der Postprozessor [INI-Datei] gefunden"
		Err_en = "Wrong setting found in Postprocessor - INI File PP.INI"
	Case 1572
		Err_de = "Die falsche Einstellungen in der Postprozessor [INI-Datei] wurde korrigiert! - Bitte erneut starten" 
		Err_en = "Wrong setting found in File PP.INI - values now fixed/correct - please start the Post once again"
	Case 1575
		Err_de = "Ohne Wahl der Korrekturseite ist diese Art der Anfahrbewegung nicht moeglich"
	Case 1585
		Err_de = var1+" falsche Wert - Uebergabe GlobalVars"
	Case 1585
		Err_de = var1+" falsche Wert - Uebergabe GlobalVars"
	Case 1586
		Err_de = " verschobene Ebene0 wird nicht unterstuetzt"
		Err_en = " shifted View 0 not supported"
	Case 1588 
		Err_de = "Werkzeug bereits im anderen Kanal benutzt - Box:"+inttos(var1)+" Head:"+inttos(var2)
		Err_en = "Tool already used in other Channel - Box:"+inttos(var1)+" Head:"+inttos(var2)
	Case 1589 
		Err_de = "Programmierte Haubenposition außerhalb des zulaessigen Bereichs Pos:"+inttos(var1)
		Err_en = "not allowed programmed Suction position found Pos:"+inttos(var1)
	
	Case Else
		AddMistake("Err"+inttos(ErrNo)+" not found")
		Exit All
		Stop
	End Select
	
End Function



