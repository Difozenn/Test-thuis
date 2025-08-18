' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \hh7\pp_7.bas
' -- 
' -----------------------------------------
'#uses "pp_math.bas"
'#uses "pp_global.bas"
'#uses "pp_ncinfo.bas"

Option Explicit

Global tTimer As Double 

' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     pp_7.bas
' -- 
' -----------------------------------------
Type THood
	activ As Boolean
	Typ1 As Integer 
	Value1 As Double
	Mode1 As Integer
	Typ2 As Integer 
	Value2 As Double
	Mode2 As Integer
End Type

'Global NCI_Ext_SH As THood

Type TDynamic  ' NCIExt 70099 Para1 = 100
	activ As Boolean
	no As Integer
End Type

Type TNCIExt
	e7251 As Boolean     ' NCIExt 7251 Wenn true "G451" ansonsten "G450" beim Fraesen - absetzen bei Start_Milling
	e7211 As Boolean     ' NCIExt 7211 Blasduese
	'DustPos As Boolean   ' MW 09.02.2016 NCIExt fuer Haube wurde programmiert
	dynamic As TDynamic 
	sh As THood 
End Type
Global NCiE As TNCIExt




'Process Parameter
Type TProcessPara
	PLNo As Long        ' MW 30.03.2016 wird ueber ProcessIndex uebergeben
	ToolId As Long 
	Tool As Object 
	View As Object      ' MW 24.04.2019 meas
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
	NCiE As TNCIExt       ' SH Haube, Dynamic etc.
	Din_ISO_8201 As Boolean 
	Part As NCPart 
End Type

Global PPara As TProcessPara    ' MW 16.02.2016 hier werden unter anderem Vorschuebe, NCInfos (Haubenpos) etc. zugeordnet


Function SetPPDLL_NCIExt_LeadInLeadOut   ' MW 24.02.2016 - PPDLLAddStrsAfterLeadIn(_Strs, _Mode)  /  PPDLLAddStrsBeforeLeadout(_Strs, _Mode)
Dim i,j As Long 
Dim iNC As Object ' INCNCInfo
Dim ParaString As String
Const POT_B = 30     ' Point of Time 30 = unmittelbar nach der Anfahrbewegung
Const POT_A = 40     ' Point of Time 40 = unmittelbar nach der Abfahrbewegung
Const STR_START = 5   ' ab PARA6 werden alle als abzusetzende Strings interpretiert

   ' Vorwirksame NCIExt nach Anfahrbewegung for Abfahrbewegung absetzen
	Marker.BStris.Clear 	 '  Marker erzeugt in InitMarker
	Marker.AStris.Clear 	 '  Marker erzeugt in InitMarker 	
	For i =  0 To UBound(PPara.NCiExtB) 
		Set iNC = PPara.NCiExtB(i) 
		If Not iNC Is Nothing Then
			Select Case iNC.Kind
				Case 70000
				
					If equal(iNC.Para1,POT_B) Or equal(iNC.Para1,POT_A) Then    ' 
						' PointOfTime = POT_B = (30)
						' PointOfTime = POT_A = (40)
						' Strings sammeln
'						Marker.BStris.Clear 	 '  Marker erzeugt in InitMarker
'						Marker.AStris.Clear 	 '  Marker erzeugt in InitMarker 	
						
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
			End Select
		End If
	Next i
	
End Function

Sub INITZero_7
Dim i As Integer
Dim Setup_Version As String 
	Write_PPVersion
	
	Setup_Version = PostSettings.ReadString("VERSION","PPSETUP","0.0.0.0")
	
	If GetV_Check3(Script_Version)<>GetV_Check3(Setup_Version) Then     ' auf uebereinstimmung mit dem Setup pruefen
		' Ueberpruefung, ob in der PP.INI
		' [VERSION]
		' PPSCRIPT=7.0.1.1   -> wird vom Script geschrieben
		' PPSETUP=7.0.1.0    -> wird vom PP-Setup geschrieben

		pp_Err(1,Script_Version,Setup_Version)
	End If

	Get_Language_info
	get_Hops_path
	
	JobPara.TRC_strategy = -1
	If Val(MT_Get_MachPara_Add(10100))=1 Then
		JobPara.TRC_strategy = 1
	ElseIf Val(MT_Get_MachPara_Add(10100))=2 Then
		JobPara.TRC_strategy = 2
	End If
			

	INI_Check   ' Plausibilisierung auf korrekte Einstellungen der Engine

	JobPara.TimerInitTL = Timer
	Get_ToolList	 ' MW 31.03.2016 ersetzt Sub TOOL 

	
	JobPara.is_5Axis_Machine = False  ' Ermittlung, ob Maschine mit 5-Achs- Kopf ausgestattet

	For i = 0 To TDATA.MachineData.ProcessHeadsCount-1
		' MW 01.03.2016 ueberarbeitet
		If Not TDATA.MachineData.GetProcessHead_Index(i) Is Nothing Then
			' norm. Arbeitskopf
			If TDATA.MachineData.GetProcessHead_Index(i).RotType=atFree And TDATA.MachineData.GetProcessHead_Index(i).TipType=atFree Then
			    ' Maschine mit 1. Head als 5-Achs
				JobPara.is_5Axis_Machine=True
				Exit For
			End If
		End If
	Next i
	
	If TDATA.MachineData.DrillingHeadsCount>0 Then
		If Not TDATA.MachineData.GetDrillingHead_Index(0) Is Nothing Then
			If Not TDATA.MachineData.GetDrillingHead_Index(0).Additions.GetAddition_ID(999) Is Nothing Then
				If Val(TDATA.MachineData.GetDrillingHead_Index(0).Additions.GetAddition_ID(999).Value)>0 Then
					' MW 17.07.2017 Voreinstellung fuer Rueckzug aus Bohrloch -> auch ueber NCINFO 57
					Marker.No_G0_Up_DH = True
				End If
			End If
		End If
	End If
	
'	PPara_Init   ' MW 17.02.2016    jetzt in ProcessIndex MW 30.03.2016

End Sub

' --------------------------------------------------------------------------------------------------------------------------------------
' Berechnungslogik Bezugspunkt Werkzeugspitze oder Ref. Bearbeitungskopf
' --------------------------------------------------------------------------------------------------------------------------------------
' --------------------------------------------------------------------------------------------------------------------------------------
' DLL-Milling - zugehoerige Functions/Subs
' --------------------------------------------------------------------------------------------------------------------------------------

Function DLLMPs_Init

Const NCLineDef = "N%d"
Const G0 = "G0"
Const G1 = "G1", G2 = "G2", G3 = "G3"
Const G40 = "G40" , G41 = "G41", G42 = "G42"
Const X = "%s%s", Y = "%s%s", Z = "%s%s"
Const radG2 = "R=%s", radG3 = "R=%s"
Const i = "I%s", j="J%s"
Const F = "F%s"
Const TipA = "%s%s"
Const RotA ="%s%s"    ' "%s360+[%s]" so, wenn Achse negativ ausgegeben wird -> als Notloesung
'Const TipA_rel = "G91 A=%s", RotA_rel = "G91 C=%s G90"
Const TipA_rel = "A=%s", RotA_rel = "C=%s"
Const ExtStr = ""
Const AbsStr = "G90" '
Const IncStr = "G91" '
'Const EB1_3_I = "I%s", EB1_3_J="J%s"
'Const EB2_4_I = "I%s", EB2_4_J="J%s"
' ------------------------------------------------------------------------------
Const SEP = "."
Const DECIMALS = 4         ' Anzahl Nachkommstellen
Const PRECISION = 0.0001  ' MW 26.09.2018 entfaellt, wird ueber die Anzahl der Nachkommastellen    ' Genauigkeit - Pruefung letzter X/Y/Z/A/B/C = aktueller X/Y/Z/A/B/C
Const UseRadius = True
Const NCLineStep = 10
Const UseAbsIncStrForRelTipARotA = True      'false 4. und 5. Achse absolut ausgeben, true relativ dann wird incstr verwendet
Const RotInvert = True
Const TipInvert = True    ' MW 11.02.2016  False
Const XYZ_WritingMode = 0
Const FeedrateFactor = 1
Dim WriteOnlyLastPointMPsBefore As Boolean
Dim WriteNCMillingPointsHeadData As Boolean  ' bei True fuer Maschinen ohne TCP werden die Koordinaten fuer kontinuierliche Bearbeitungen (C-Axis/5-Axismilling etc.) auf den RefPoint (Drehpunkt) ausgegeben
										     ' fuer 4-Achsmaschinen muss dieser Parameter = true sein
Const WriteNCMillingPointsHeadDataTipARotA = False  ' auf den Kopf bezogen also kardanisch wenn True gesetzt (WriteNCMillingPointsHeadData muss false sein)
Dim ToolDirection As Integer

	If JobPara.is_5Axis_Machine Then
		' Maschine hat TCP -> Werkzeugbezugspunkt = Werkzeugspitze
		WriteNCMillingPointsHeadData = False
	Else
		' fuer 4-Achsmaschinen muss dieser Parameter = true sein		
		' === > Bezugspunkt immer Kopf, d.h. Bearbeitungen C-Achsfraesen und 5-Achsfraesen finden immer mit D0 statt
		WriteNCMillingPointsHeadData = True
	End If
		
	If JobPara.is_Evo Then
		' fuer diese Maschine muss durch die Nullpunktaenderung eigentlich nach dem Umspannen die letzte Position mit dem "Traversen"- Offset
		' verrechnet werden - dies konnte in der Engine nicht geloest werden
		' ueber diesen Parameter kann die Ausgabe des "falschen" letzten Punktes unterdrueckt werden
		' N770 ; ---  ##################### DLLMPs vor ViewChange - AGGOX:-67.79  AGGOY:-215.47  AGGOZ:-25.9 ---
		' N780 D0 G0 X=1047.79+(-778.997)-(-1789.027) Y715.47 Z=177.9
		' N790 D0 G0 X1087.79
	
		WriteOnlyLastPointMPsBefore = True
		' MW 28.01.2016 Anmerkung ==> bei Maschinen mit Liftoffsets wird der letzte Punkt generell von der Engine unterdrueckt.
	Else
		WriteOnlyLastPointMPsBefore = False
	End If

'Const Drehung360 = True

	PPDLLInit("",NCData,PostSettings)
'	PPDLLInitStrings(NCLine,NCLineStep,G0,G1,G2,G3,G40,G41,G42,X,Y,Z,radG2,radG3,I,J,F,TipA,RotA,TipA_rel,RotA_rel,Absolut,RotInvert,TipInvert,ForceXY_ZChange,ExtStr,AbsStr,IncStr)
'	PPDLLInitParameter(SEP,DECIMALS,PRECISION,UseRadius)
	
	PPDLLInitStrings(NCLineDef,G0,G1,G2,G3,G40,G41,G42,X,Y,Z,radG2,radG3,i,j,i,j,i,j,F,TipA,RotA,TipA_rel,RotA_rel,AbsStr,IncStr)
	PPDLLInitParameter(SEP,DECIMALS,PRECISION,UseRadius,NCLineStep,UseAbsIncStrForRelTipARotA,RotInvert,TipInvert,XYZ_WritingMode,WriteNCMillingPointsHeadData,WriteNCMillingPointsHeadDataTipARotA,FeedrateFactor,WriteOnlyLastPointMPsBefore)
	
  	'AddLog("INIT TEST DELPHI ROUTINE TIME: "+ftos(Timer-JobPara.TimerFullSecs)+" sec")


	' INIT Dyn. Haube 
	PPDLLInitDynamicSuction()

	If JobPara.is_Evo Then
	Dim tmp_t As thopsbasictoolext
	Dim CID, TCount, ii
	Dim var_XToolID As String
	
	
		ToolDirection=0
		If Not ActT.t Is Nothing Then
			ToolDirection=ActT.t.RotDirection
		End If
			
		'CID=MT_Get_MachPara_Add(60050)
		'	If CID<>"" Then
		TCount=TDATA.ToolsCount
		For ii= 0 To TCount-1
			Set tmp_t.t = TDATA.GetTool_Index(ii)
	   		If Not tmp_t.t Is Nothing Then
	   			If tmp_t.t.ObjectType = htokStandardTool Then
					If Not tmp_t.t.CuttingEdge.Additions.GetAddition_ID(60050) Is Nothing Then
						var_XToolID = tmp_t.t.CuttingEdge.Additions.GetAddition_ID(60050).Value
						'MsgBox(var_XToolID)
						If var_XToolID = "1" Then
							wcncaddcom("L CYCLE [NAME=CP_STRIPTOOL.NC @P1=" +FToS(tmp_t.t.ID)+" @P2="+FToS(tmp_t.t.ToolNo)+" @P3="+FToS(tmp_t.t.CorrNo)+" @P4="+ftos(tmp_t.t.CuttingEdge.RotDirection)+" @P5="+ftos(tmp_t.t.CuttingEdge.RotSpeed)+" @P6="+ftos(tmp_t.t.CuttingEdge.MaxRotSpeed)+" @P7="+ftos(tmp_t.t.CuttingEdge.Length)+" @P8=" + ftos(tmp_t.t.CuttingEdge.Radius) + "]", "Stripcut / Tooldata ")
							Exit For
						End If
					End If
				End If
		  	End If
		Next 
		'	End If			

	';	If MT_Get_MachPara_Add(60050)="-1" Then
	'		Set tmp_t.t = TDATA.GetTool_ID(136)
	'		If tmp_t.t.RotDirection=rdLeft Then
	'			MsgBox("links")
	'				
'		End If
'		If tmp_t.t.RotDirection=rdRight Then
'			MsgBox("rechts")
'				
'		End If
				
	'	End If
		'Stripcut Aufruf vor allen Bearbeitungen - Vermessung Y
		If (Marker.RollerTrackDown=False) Then
			'Keine Formatierung
			wcncaddcom("L CYCLE [NAME=CP_STRIPCUT.NC @P1=" +FToS(FinishedPart.X)+" @P2="+FToS(FinishedPart.Y)+" @P3="+FToS(FinishedPart.Z)+" @P4=0 @P5="+ftos(TDATA.MachineData.GetProcessHead_Index(0).CenterX)+" @P6="+ftos(TDATA.MachineData.GetProcessHead_Index(0).CenterY)+" @P7="+ftos(TDATA.MachineData.GetProcessHead_Index(0).CenterZ)+" @P8=1 @P9=0 @P10=" + ftos(ToolDirection) + "]", "Stripcut / no RollerTrack Mode Bit 1 ")
		Else	
			'Mit Formatierung
			wcncaddcom("L CYCLE [NAME=CP_STRIPCUT.NC @P1=" +FToS(FinishedPart.X)+" @P2="+FToS(FinishedPart.Y)+" @P3="+FToS(FinishedPart.Z)+" @P4=0 @P5="+ftos(TDATA.MachineData.GetProcessHead_Index(0).CenterX)+" @P6="+ftos(TDATA.MachineData.GetProcessHead_Index(0).CenterY)+" @P7="+ftos(TDATA.MachineData.GetProcessHead_Index(0).CenterZ)+" @P8=1 @P9=1 @P10=" + ftos(ToolDirection) + "]", "Stripcut / with RollerTrack Mode Bit 1  ")
		End If
	End If			


End Function

Function DLLMPs_Start(pno)
	
	wcnc("; WorkMode:" + inttos(PPara.MMode),True)
	'wcnc("; WorkMode:" + inttos(PPara.PreObjectType),True)

	MT_Write_Check_Spindle
' MW 11.11.2016	WCNC_IDD("CONTOUR_START")
	
'	If (MT_Get_PosDustExhaust(actt) = 1) And (JobPara.DynamicSuctionNC=True) Then
'		' dyn. Haubenposition - >
'		WCNC_IDD("CP_HOODDYN_ON",1)
'	End If
	
End Function

Function DLLMPs(Kind,pno)
Dim LiftPosChange As Boolean 
Dim DustSuction As Integer 
Dim mFunctionHoodThreshold As String ' statisch autom. berechnete Haubenposition
Dim ToolDirection As Integer


	' Spindel mit Vorgelege steuern
	MT_Set_LiftPos(Kind,pno)
	'MT_Set_HaubeObj(Kind,pno)

	' MW 10.02.2016 - Ermittlung Haubenpos
	DustSuction = MT_Get_Suction(Kind,PPara.NCiE.sh.Activ,PPara.MinTipA,PPara.MaxTipA)

		
'	PPDLLSetWriteNCMillingPointsHeadData(True)   Bezugsposition dyn. festlegen - notwendig bei Verwendung von mehreren Arbeitskoepfen
	
	Select Case Kind
		Case -1 
			wcnc_NCIExt_Before(10)  ' Bei PointOfTime=10 (Para6) hier und jetzt absetzen

'			WCNC_IDD("CONTOUR_START")   ' MW 02.02.2016 - erst im Start_Milling		
			 ' Anfahrt absolut im WKS-Koordinatensystem 
			 ' Alles was vor dem Viewchange kommt - anfahren auf Bearbeitungsposition
			 ' -> Die folgenden X/Y/Z Koordinaten beziehen sich immer auf der Plananlage der Spindel
			 '     ==> d.h. es darf z.B. keine Laengenkorrektur aktiv sein!
			 ' -> Je nach Einstellung "Koordinaten relativ zur Referenzspindel" werden die Offsets mit eingerechnet
			 
			' Dim ZOffGes As Double
			' MT_Write_Offset_NC_Vars(ZOffGes) 
			
			'PPDLLInitStartEndString("3","4")				
			'WCNC_IDD("ATRANSAROT",0,0,0,0,0)
			
			If MT_isPneumaticSaw(ActT) Then
				' Drehung pneumatisch Saege hier - zeitgewinn schwenken waehrend der Anfahrt !
				MT_Write_Speed(ActT,PPara.Speed,,MT_GetPneumaticSawAngle(ActT,NCData.ProcessList.GetProcess_NCInfoIndex(pno-1).View.TipA,NCData.ProcessList.GetProcess_NCInfoIndex(pno-1).View.RotA))
			End If
'			PPDLLSupressAxis(True,False,False,True,True)  ' Achsausgabe X, C, A unterdruecken
			
'			wcnccom(" ##################### DLLMPs vor ViewChange - AGGOX:"+ftos(actt.h.CenterX)+"  AGGOY:"+ftos(actt.h.CenterY)+"  AGGOZ:"+ftos(actt.h.CenterZ),True)
			wcnccom(" ##################### DLLMPs vor ViewChange - AGGOX:"+ftos(ActT.t.MoveX)+"  AGGOY:"+ftos(ActT.t.MoveY)+"  AGGOZ:"+ftos(ActT.t.MoveZ),True)
'			wcnc("; TCP:"+ftos(actt.h.TCPOffset_Z)+"  - OffDPx "+ftos(actt.h.RotPointOffX)+"  - OffDPy "+ftos(actt.h.RotPointOffY)+"  - OffDPz "+ftos(actt_mt.h.RotPointOffZ))
			
			
			PPDLLInitStartEndLineString("D0","")  ' Schreibt D0 x y z D2

						' AK 08.03.2019 / Anpassungen Stripcut erste Bearbeitung

			
			

			'In letzter Szene Stripcut X aufrufen
			If JobPara.is_Evo And Marker.XCUT_Done=False Then
				If JobPara.actscene=Marker.MaxSceneNo Then
					Marker.XCUT_Done=True
					ToolDirection=0
					if Not ActT.t is nothing then
						ToolDirection=ActT.t.RotDirection
					end if

					
					If (Marker.RollerTrackDown=False) Then
						'Keine Formatierung
						wcncaddcom("L CYCLE [NAME=CP_STRIPCUT.NC @P1=" +FToS(FinishedPart.X)+" @P2="+FToS(FinishedPart.Y)+" @P3="+FToS(FinishedPart.Z)+" @P4=0 @P5="+ftos(TDATA.MachineData.GetProcessHead_Index(0).CenterX)+" @P6="+ftos(TDATA.MachineData.GetProcessHead_Index(0).CenterY)+" @P7="+ftos(TDATA.MachineData.GetProcessHead_Index(0).CenterZ)+" @P8=2 @P9=0 @P10=" + ftos(ToolDirection)  + "]", "Stripcut / no RollerTrack Mode Bit 1 ")
					End If
				End If
			End If
	
	
			If JobPara.is_Evo And Marker.XCUT_Done=False Then
				If JobPara.actscene>1 Then
					If Marker.AktProzessIsXMove=True Then
						ToolDirection=0
						if Not ActT.t is nothing then
							ToolDirection=ActT.t.RotDirection
						end if
						Marker.XCUT_Done=True
						wcncaddcom("L CYCLE [NAME=CP_STRIPCUT.NC @P1=" +FToS(FinishedPart.X)+" @P2="+FToS(FinishedPart.Y)+" @P3="+FToS(FinishedPart.Z)+" @P4=0 @P5="+ftos(TDATA.MachineData.GetProcessHead_Index(0).CenterX)+" @P6="+ftos(TDATA.MachineData.GetProcessHead_Index(0).CenterY)+" @P7="+ftos(TDATA.MachineData.GetProcessHead_Index(0).CenterZ)+" @P8=2 @P9=1 @P10=" + ftos(ToolDirection)  + "]", "Stripcut / no RollerTrack Mode Bit 1 ")
					End If
				End If
			End If

	
	
		Case 0
			' Eigentliche Bearbeitung
			wcnccom(" ##################### DLLMPs",True)
			wcnc_NCIExt_Before(20)  ' Bei PointOfTime=20 (Para6) hier und jetzt absetzen

			' MW 15.11.2017 - Einstellung wird nicht zurueckgesetzt - z.B. nach Verwendung von Winkelgetriebe
			PPDLLSetWriteNCMillingMPsHeadData(False)  ' Bezugspunkt=Werkzeugspitze ==> es ist ja Traori aktiv

			If (PPara.MMode>0) And Not MT_H_Is_5_Axis(actt) Then
			    ' C-Achsfraesen oder 5-Achsfraesen mit 3-Achs oder 4-Achs
				PPDLLSetWriteNCMillingPointsHeadData(True)   ' Bezugsposition = Head Verwendung Winkelgetriebe mit veraenderlicher Ausrichtung
				wcncaddcom("D0","########### Alle Offs bereits verrechnet auch Werkzeugradius",True)
			ElseIf MT_IsGearBoxTool(actt) And MT_H_Is_5_Axis(actt) Then
				' ===> MW 21.03.2016 Winkelgetriebe durch die aus der Mitte schwenkenden 5-AchsHeads immer verrechnen auf Kopf			
				If equal(PPara.MMode,0) Then
					' statische Ausrichtung, Bearbeitung auf einer Ebene mit Winkelgetriebe
					PPDLLSetWriteNCMillingMPsHeadData(True)   ' Bezugspunkt=Plananlage

					wcncaddcom("V.G.WZ_AKT.L=0.0","Werkzeuglaenge von Winkelgetriebewerkzeug bereits von Engine verrechnet")
					' ===> D0 nicht moeglich, da Radius fuer G41/G42 benoetigt wird
					' Werkzeuuglaenge auf 0 setzen
				ElseIf (PPara.MMode>0) Then
					' C-Achsfraesen oder 5-Achsfraesen mit Winkelgetriebe auf 5-Achs
					PPDLLSetWriteNCMillingPointsHeadData(True)
					wcncaddcom("D0","########### Alle Offs bereits verrechnet",True)
				End If
			Else
				' MW 19.01.2015 - Offset auf Werkzeugspitze muss aktiv sein
				' Korrektur aufrufen, und offsets setzen
				MT_Write_Call_Correction
			End If

			WCNC_IDD("CONTOUR_START")

			If ppara.PreObjectTyp=2 Then
				' oszillieren ueber Maschinenseitige option
				WCNC_IDD("CONTOUR_START_EXCLUSIV")   ' MW 15.02.2016 - ehemals EndLeadIn
			End If
			
			SetPPDLL_NCIExt_LeadInLeadOut   ' MW 24.02.2016 - PPDLLAddStrsAfterLeadIn(_Strs, _Mode)  /  PPDLLAddStrsBeforeLeadout(_Strs, _Mode)
			
			If ppara.PreObjectTyp=2 Then
				' oszillierendes fraesen ende
				WCNC_IDD("CONTOUR_END_EXCLUSIV")   ' MW 15.02.2016 - ehemals StartLeadOut
			End If

		Case 1 
			' Rueckzug absolut im WKS-Koordinatensystem 

			WCNC_IDD("CONTOUR_END")
			
			wcnc_NCIExt_Before(50)  ' Bei PointOfTime=3 (Para6) hier und jetzt absetzen
			WCNC_IDD("TRANSOFF")
			
			' MW 19.01.2015 - Bezugspunkt Werkzeugspitze aus
			WCNC_IDD("TCARROFF")

			If (MT_Is_Vertical_StandardTool5Axis(ActT)) Then
				' 5-Axis mit Traori
				wcnc_IDD(JobPara.TCP_OFF)

				'wcncaddcom(T.ph_add.traorioff," 5-Achs Transformation abschalten") ' TRAFOOF 
				wcnc("G"+IntToS(53+Fix_Zero))
			End If

			If (PPara.MMode>0) And ((MT_IsGearBoxTool(actt) And MT_H_Is_5_Axis(actt)) Or (Not MT_H_Is_5_Axis(actt)) ) Then
				' 04.02.2019 - Verrechnung Winkelgetriebe auf 5Achs oder auch 4-Achs
				PPDLLSetWriteNCMillingPointsHeadData(False)
			End If

			wcnccom(" ##################### DLLMPs SIC",True)
			PPDLLInitStartEndLineString("D0","")  ' Schreibt D0 x y z D2
			
			
			
			If (isDINISO_Process) Then
				' MW 09.05.2016 
				PPDLLSupressAxis(True,True,False,True,True)  ' Achsausgabe X,Y, C, A unterdruecken
			End If
	End Select

	wcnc_TCP_Offset_On(Kind)    ' hier G92 Offset rechnen (5Axis)
	
	If DustSuction = 1 Then   
		' dyn. Haube
		If ActT.ph_add.HoodThreshold_DynMode = 0 Then
			' MW 11.01.2017 - Tiefste Zustellung maﬂgebend fuer die Haubenposition
			If equal(Kind,-1) Then
				mFunctionHoodThreshold = PPDLLGetProcessSuctionStr(ppara.PLNo-1,0,ActT.SetOf_DustPositions,ActT.SetOf_DustPositionsMFunc) 
				wcnc(mFunctionHoodThreshold)   ' +"   ;HoodThresDynMode = 1")
			End If
		Else
			' alte dyn. Steuerung nicht praktikabel
			If equal(Kind,0) Then
				' MW 11.02.2016 beim Hochfahren kann letzte Position immer beibehalten werden
				' -> nur fuer die eigentliche Bearbeitung Haubenposition ausgeben - also von Sicherheit ueber Werkstueck und zurueck
				PPDLLActivateDynamicSuction(ActT.SetOf_DustPositions,ActT.SetOf_DustPositionsMFunc,0)
			End If
		End If
	Else
		' Dann Haube auf Pos. von Schneide oder program. ueber NCIExt oder ganz HOCH
		wcnc_DustSuction(DustSuction)
	End If

	PPDLLWriteProcess(NCFileNo,Kind,pno-1,NCLine)

	wcnc_TCP_Offset_Off(Kind)    ' hier G92 Offset rechnen (5Axis)
	
	If equal(Kind,-1) Or equal(Kind,1) Then
		' Anfahrt und Rueckzug findet mit D0 statt -> hier muss wieder aktiviert werden
		If ((ActT.T.ToolNo>0) And (ActT.T.CorrNo>0)) Then
			wcnc("T"+IntToS(ActT.T.ToolNo)+" D"+IntToS(ActT.T.CorrNo))
		End If
	End If

End Function


Function DLLMPs_End
	' kommt beim C-Achsfraesen, Oberflaechenfraesen 5-Achsfraesen
	
	wcnc_NCIExt_After
	
	' MW 02.02.2018 - bereits In Function DLLMPs kind = 1 erfolgt -> siehe auch end_milling
	'WCNC_IDD("CONTOUR_END")

	' MW 06.03.2014
	MT_NoTurningWithSpindelRot_OFF(ActT)

'	If (MT_Get_PosDustExhaust(actt) = 1) And (JobPara.DynamicSuctionNC=True) Then
'		WCNC_IDD("CP_HOODDYN_OFF",0)
'	End If

	Marker.Last_SuctionPos = -1
	Inc_Process   ' ActProcess=ActProcess+1
	
'	PPara.DustPosNCIExt = False

End Function

Function DLLMPs_Final
	' kommt nur einmalig zum Schluss
	PPDLLFinalize
End Function



Sub EndLeadIn_7
	WCNC_IDD("CONTOUR_START_EXCLUSIV")
End Sub

Sub StartLeadOut_7
	WCNC_IDD("CONTOUR_END_EXCLUSIV")
End Sub

Sub Park_7 (Index)
	JobPara.park=NCData.NCInfo_Global.GetNCI_Index(Index).Para1
	JobPara.parkx=NCData.NCInfo_Global.GetNCI_Index(Index).Para2
	JobPara.parky=NCData.NCInfo_Global.GetNCI_Index(Index).Para3
End Sub

Sub SuctionHood_7 (Index)
	PPara.NCiE.sh.Value1= NCData.NCIExtList.GetNCI_Index(Index).Para1
	PPara.NCiE.sh.Typ1 = NCData.NCIExtList.GetNCI_Index(Index).Para2			    
	PPara.NCiE.sh.Mode1 = NCData.NCIExtList.GetNCI_Index(Index).Para3			    
	PPara.NCiE.sh.Value2 = NCData.NCIExtList.GetNCI_Index(Index).Para4
	PPara.NCiE.sh.Typ2 = NCData.NCIExtList.GetNCI_Index(Index).Para6			    
	PPara.NCiE.sh.Mode2 = NCData.NCIExtList.GetNCI_Index(Index).Para6			    
'	NCI_Ext_SH.Value1 = NCData.NCIExtList.GetNCI_Index(Index).Para1
'	NCI_Ext_SH.Typ1 = NCData.NCIExtList.GetNCI_Index(Index).Para2			    
'	NCI_Ext_SH.Mode1 = NCData.NCIExtList.GetNCI_Index(Index).Para3			    
'	NCI_Ext_SH.Value2 = NCData.NCIExtList.GetNCI_Index(Index).Para4
'	NCI_Ext_SH.Typ2 = NCData.NCIExtList.GetNCI_Index(Index).Para6			    
'	NCI_Ext_SH.Mode2 = NCData.NCIExtList.GetNCI_Index(Index).Para6			    
	MT_CheckProgValue_Suction(PPara.NCiE.sh.Value1)  ' MW 10.02.2016 -> Plausibilierung des Wertes, gesetzt werden d¸rfen nur die Werte, welche unter Eigenschaften definiert
	
	PPara.NCiE.sh.activ = True
	
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
Dim Mode As Double
Dim i As Integer 
Dim flo As Double 
Dim Found As Boolean 
Dim Para1 As Double
Dim Para2 As Double 
Dim Para3 As Double 
Dim Para4 As Double
Dim Para5 As Double
Dim Para6 As Double
Dim Para7 As Double
Dim Para8 As Double
Dim Para9 As Double
Dim Para10 As Double
Dim Para11 As Double
Dim Para12 As Double
Dim Para13 As Double
Dim Para14 As Double
Dim s1,s2 As String
Dim Mode_Ok As Boolean 
	Mode_Ok = True

	Found = True
	Select Case Kind
		Case 0
			If NCData.NCIExtList.GetNCI_Index(Index).IsBeforeProcess Then 
			
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
							' Vorwirksam
						Set PPara.NCiExtB(UBound(PPara.NCiExtB)) = NCData.NCIExtList.GetNCI_Index(Index)
						ReDim Preserve PPara.NCiExtB(UBound(PPara.NCiExtB)+1)
							'For i = 0 To NCData.NCIExtList.GetNCI_Index(Index).NCIExt.ParaCount-1 
							'	NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetFloat(i,flo)
							'	NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetString(i,resStr)
							'Next i
						
						If equal(NCData.NCIExtList.GetNCI_Index(Index).Para1,0) Then    ' 
							' PointOfTime = 0 -> also hier direkt absetzen
							wcnc_NCIExt_Strs(NCData.NCIExtList.GetNCI_Index(Index),0)   ' Alle Strings ueber ParaCount wegschreiben
						End If					
					Case 70099
						' Alle vorwirksamen NCIExt des HH7 - Posts
						Mode_Ok = False
						If NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetFloat(0,Mode) Then
							' bei Allen vorwirksamen NCIext wird ueber den 1. Parameter die Funktionalitaet unterschieden
							Select Case Mode
								Case 100
									' Dynamic - Parameter der Bearbeitung
									If NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetFloat(1,Para1) Then
										PPara.NCiE.dynamic.activ = True
										PPara.NCiE.dynamic.No = Para1   ' dynamic - Logik
										Mode_Ok=True
									End If
								Case Else
									If Mode <= 50 Then
										If jobpara.is_Evo Then
											' MW 26.09.2018 - Messversatz fuer EVO
											' Unterschied ist, dass fuer die Szene ermittelt werden muss, ob der Messvorgang stattfinden muss									
											' hier jetzt 1:1 wie CASE 70000
											Set PPara.NCiExtB(UBound(PPara.NCiExtB)) = NCData.NCIExtList.GetNCI_Index(Index)
											ReDim Preserve PPara.NCiExtB(UBound(PPara.NCiExtB)+1)
												'For i = 0 To NCData.NCIExtList.GetNCI_Index(Index).NCIExt.ParaCount-1 
												'	NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetFloat(i,flo)
												'	NCData.NCIExtList.GetNCI_Index(Index).NCIExt.GetString(i,resStr)
												'Next i
											
											If equal(NCData.NCIExtList.GetNCI_Index(Index).Para1,0) Then    ' 
												' PointOfTime = 0 -> also hier direkt absetzen
												wcnc_NCIExt_Strs(NCData.NCIExtList.GetNCI_Index(Index),0)   ' Alle Strings ueber ParaCount wegschreiben
											End If					
										End If
									Else
										' weitere 
									End If
							End Select
						End If
						
					Case Else
						'Found = False
					End Select
			ElseIf NCData.NCIExtList.GetNCI_Index(Index).IsAfterProcess Then
				' Nachwirksam
				Select Case NCType
					Case 80000 
						' Diverse Makros welche bisher NCI 200 benutzt haben
						' -> zusaetzliche Parameter fuer Bestimmung Zeitpunkt absetzen
						' -> und jetzt natuerlich die Moeglichkeit Hold..
						Set PPara.NCiExtA(UBound(PPara.NCiExtA)) = NCData.NCIExtList.GetNCI_Index(Index)
						ReDim Preserve PPara.NCiExtA(UBound(PPara.NCiExtA)+1)
						' ----------> immer direkt hier absetzen
						wcnc_NCIExt_Strs(NCData.NCIExtList.GetNCI_Index(Index),0)   ' Alle Strings ueber ParaCount wegschreiben
	
					Case -108040
				  	 	' Rollenbahn senken und heben NCINFO 64 bzw. 8040 bei Standard
	  		  	 		'wcncaddcom("M154","RollerTrack up")
						If (Marker.RollerTrackDown) Then
							wcncaddcom("L CYCLE [NAME=CP_STRIPCUT.NC @P1=" +FToS(FinishedPart.X)+" @P2="+FToS(FinishedPart.Y)+" @P3="+FToS(FinishedPart.Z)+" @P4=0 @P5="+ftos(TDATA.MachineData.GetProcessHead_Index(0).CenterX)+" @P6="+ftos(TDATA.MachineData.GetProcessHead_Index(0).CenterY)+" @P7="+ftos(TDATA.MachineData.GetProcessHead_Index(0).CenterZ)+" @P8=2 @P9=1 @P10=0]", "Stripcut / RollerTrack down")
                            Marker.XCUT_Done=True
							' Formatierung unten aktiv 
							' Verzoegerter Aufruf Messzyklus nach Rollerbahn hoch 
				  	 		Marker.RollerTrackDown = False
							wcnc_Evo_Mea    
						End If
			  	 		Marker.RollerTrackDown = False
	
					Case 7451 
						' Bahnverhalten Ecken eckig fahren
						'NCiE.e7251 = True  ' NCIExt 7251 Wenn true "G451" ansonsten "G450" beim Fraesen 
					Case 7211
						' Blasduese ein
						'NCiE.e7211 = True  ' NCIExt 7211
						'SpindleBlowNozzle.Blow=True
				Case Else
					Found = False
				End Select
			End If
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
			Case Else
				Found = False
			End Select
		Case 4 
			' Globale NCIExt
			
			Select Case NCType
				Case -100064
					' Rollertracker
			 	    Marker.RollerTrackDown = True
			Case Else
				Found = False
			End Select
		Case Else
			Found = False
	End Select
	If Not Found Then AddHint("NCIExt Kind #"+inttos(Kind)+ " not interpreted")
End Sub

'Neu AK 24.11.2016
Sub	Handle_NCI_Ext_7_OEM (Kind,NCType,Index)   ' 
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
Dim Mode As Double
Dim i As Integer 
Dim flo As Double 
Dim Found As Boolean 
Dim Para1 As Double
Dim Para2 As Double 
Dim Para3 As Double 
Dim Para4 As Double
Dim Para5 As Double
Dim Para6 As Double
Dim Para7 As Double
Dim Para8 As Double
Dim Para9 As Double
Dim Para10 As Double
Dim Para11 As Double
Dim Para12 As Double
Dim Para13 As Double
Dim Para14 As Double
Dim s1,s2 As String
Dim Mode_Ok As Boolean 
	Mode_Ok = True

	Found = True
	Select Case Kind
		Case 0
			If NCData.NCIExtList.GetNCI_Index(Index).IsBeforeProcess Then 
			
				'Select Case NCType
				'	Case 70100 
					
				'	Case Else
						'Found = False
				'	End Select
			ElseIf NCData.NCIExtList.GetNCI_Index(Index).IsAfterProcess Then
				' Nachwirksam
				'Select Case NCType
					'Case 80100 

				'Case Else
				'	Found = False
				'End Select
			End If
		Case 1
			' NCI innerhalb Fraesbahn
			'Select Case NCType
			'	Case -100200 
			'Case Else
			'	Found = False
			'End Select
		Case 4 
			' Globale NCIExt
			
			Select Case NCType
				Case 90100
					Select Case NCData.NCInfo_Global.GetNCI_Index(Index).Para1
						Case 9001
							' Neu AK 24.11.2016
							' H-Laserpositionen

							If HLaserInfo.HLaserListTyp <= 0 Then
								HLaserInfo.HLaserListTyp = StringListCreate
							End If
							If HLaserInfo.HLaserListX <= 0 Then
								HLaserInfo.HLaserListX = StringListCreate
							End If
							If HLaserInfo.HLaserListY <= 0 Then
								HLaserInfo.HLaserListY = StringListCreate
							End If
						
							HLaserInfo.HLaserX_Active=True
							HLaserInfo.HLaserY_Active=True
																				
							If HLaserInfo.HLaserX_Active Then
								HLaserInfo.ActPosX=NCData.NCInfo_Global.GetNCI_Index(Index).Para3
							Else
								HLaserInfo.ActPosX=-9999
							End If		
							If HLaserInfo.HLaserY_Active Then
								HLaserInfo.ActPosY=NCData.NCInfo_Global.GetNCI_Index(Index).Para4
							Else
								HLaserInfo.ActPosY=-9999
							End If		
							
							StringListAdd(HLaserInfo.HLaserListTyp,inttos(NCData.NCInfo_Global.GetNCI_Index(Index).Para2))
							StringListAdd(HLaserInfo.HLaserListX,inttos(HLaserInfo.ActPosX))
							StringListAdd(HLaserInfo.HLaserListY,inttos(HLaserInfo.ActPosY))
	
					End Select	
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
	Mode = NCData.NCIExtList.GetNCI_Index(Index).Para1
	Park = NCData.NCIExtList.GetNCI_Index(Index).Para2
	X = NCData.NCIExtList.GetNCI_Index(Index).Para3
	Y = NCData.NCIExtList.GetNCI_Index(Index).Para4
	stri = NCData.NCIExtList.GetNCI_Index(Index).Text
	Typ = NCData.NCIExtList.GetNCI_Index(Index).Para5
	Para1 = NCData.NCIExtList.GetNCI_Index(Index).Para6
	Para2 = NCData.NCIExtList.GetNCI_Index(Index).Para7
	Machine_Stop(Park,X,Y,stri,NextBoxWorking,HeadID)
End Sub


' Achtung ProcessID ist nicht der eigentliche ProzessNo aus der ProzessListe
Sub Process_Start_7(ProcessId,BoxId,HeadID,d1,d2,ProcC,XMin,YMin,ZMin,XMax,YMax,ZMax)
'Dim TN As String    ' aus ToolListe holen
'Dim H_Name As String
'
'	If Not TDATA.GetProcessHead_ID(HeadID) Is Nothing Then
'		H_Name = TDATA.GetProcessHead_ID(HeadID).Description 
'	ElseIf Not TDATA.GetDrillingHead_ID(HeadID) Is Nothing Then
'		'H_Name = TDATA.GetDrillingHead_ID(HeadID).Description 
'		' unnoetig, kommt auch ueber TN
'	End If
'
'	TN = Get_TN_Info(BoxId)

	' MW 13.04.2015 -> Info ueber die momentane Bearbeitung fuer die Ausgabe von Fehlermeldungen
'	JobPara.Proc_Info = JobPara.Proc_Info + _
'	       IIf(Not equal(XMin,-99999)," Xmin:"+ftos(XMin),"") + IIf(Not equal(XMax,99999)," Xmax:"+ftos(XMax),"") + _
'	       IIf(Not equal(YMin,-99999)," Ymin:"+ftos(YMin),"") + IIf(Not equal(YMax,99999)," Ymax:"+ftos(YMax),"") + _
'	       IIf(Not equal(ZMin,-99999)," Zmin:"+ftos(ZMin),"") + IIf(Not equal(ZMax,99999)," Zmax:"+ftos(ZMax),"") 
'	       " IPX:"+ftos(JobPara.Proc_L_Array(ProcId-1).ipx) + _
'	       " IPY:"+ftos(JobPara.Proc_L_Array(ProcId-1).ipy) + _
'	       P_Ptr.Act_P.Kind + _
'	       " View:"+inttos(P_Ptr.Act_P.Ebene) + _

	wcnccom("---",True)
	wcnccom("--- process group start --- ",True)
	wcnccom("---",True)
	
	If XMin=XMax and HeadID="1" and ((YMax-YMin)>FinishedPart.Y) then
		Marker.AktProzessIsXMove=true
	else
		Marker.AktProzessIsXMove=false	
	end if
	
End Sub


Sub Process_End_7(ProcId,d1,d2)
	
	wcnccom("---",True)
	wcnccom("--- process group end ---",True)
'	wcnccom(" process group end - "+ JobPara.Proc_ErrInfo,True)
	wcnccom("------------------------------- ",True)'process End  -------------------------------",True)
	wcnccom("---",True)
End Sub


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
	Const EnableCreateNew = True   ' NC-Programm aus Oberflaeche neu erzeugen ermoeglichen

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
	Const VorWechselVorWerkzeugWechsel  = False         ' WZG-Vorwechsel vor WZG-Wechsel
	Const AlleWerkzeugeWegschreiben = False   ' MW 31.03.2016 True             ' Werkzeugliste schreiben
	Const AlleBearbeitungenWegschreiben = False         ' Bearbeitungsliste schreiben
	Const RohteilInfoWegschreiben=False                ' Fertigteilinformation schreiben
	Const ViewInfoBeforeToolchangeWegschreiben=True    ' Ebeneninfo vor Werkzeugwechsel schreiben
	Const AlleTeileWegschreiben=True                   ' Werstueck - Info schreiben
	Const WriteHid=False  ' MW 31.03.2016 True                                ' Aggregate Info schreiben
	Const ProcessMinMaxInfo=False   ' MW 09.02.2016 True                       ' Min/Max Info schreiben
	Const WriteStartNCInfoProcess=False ' MW 01.04.2016 nicht mehr notwendig, da PPara schon Info hat True ' MW 17.02.2016 False                ' Start NCInfoProcess schreiben
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
	Const GTypRadiusKorrekturAufbau = 1            ' G-Typ fuer Werkzeugradiuskorrekturaufbau
	Const AnfahrFaktor_Seitlich = 1.1              ' Faktor fuer seitliches Anfahren
' Milling / Definition der Strecke fuer Korrekturaufbau
	Dim TRCAngle As Double '  = 0                  ' Winkel 0(Hops6): in Verlaengerung der Anfahrbewegung
	Dim TRCFactor As Double ' = 0                  ' Faktor 0(Hops6) 
	Dim TRCLength As Double ' = 1                  ' Strecke (1mm) fuer Korrekturaufbau
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
	
'	Const NewDHOpti=True
'	Const ModeOldDrilOpti=0
	Const BohroptiBoxNRWegschreiben=True
	Const BohroptiAnzahlHuebeWegschreiben=False
	Const LaengeVerrechnenBohrkopf=False
'	Const CheckAllHoles=True
	Const BohrungenAufBohrkopfGruppieren=True
	Const InsertAllDrillBits=False   ' EINST
	Const MinMaxHorzLaengeSicherheitVerrechnen=True   ' EINST
	
	Const DHTimeOpti = True
	Const DHPinChangeTime = 1
' Bohrkopf generelle Logik DLL JA/NEIN ? MW 18.03.2016
	Const CalcDHMoves = False
	Const CalcDHFirstActiveSpindleIsRefPoint = False
	Const CalcDHRelativToRefSpindle = False


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
	Const GBOn5AxisFreeTipA = True  ' PP unterstuetzt Winkelgetriebe auf 5-Achskopf 

' -----------------------------------------------------------------------------------
' -----------------------------------------------------------------------------------
' -----------------------------------------------------------------------------------
' -----------------------------------------------------------------------------------
' -----------------------------------------------------------------------------------
' -----------------------------------------------------------------------------------
' -----------------------------------------------------------------------------------
' -----------------------------------------------------------------------------------

	' MW 12.06.2016 Definierbar ueber Machpara 10100
	If equal(JobPara.TRC_Strategy,1) Then
		' optimalst wenn Steuerung es realisiert
		' MW 12.05.2016 getestet - funzt gut
		TRCAngle  = 90                     ' Winkel 0(Hops6): in Verlaengerung der Anfahrbewegung
		TRCFactor = 1                      ' Faktor 0(Hops6) 
		TRCLength = 0.1                    ' Strecke (1mm) fuer Korrekturaufbau (bei 0 steht NC teilweise hin)
	ElseIf equal(JobPara.TRC_Strategy,2) Then
		' BSW - Mode
		TRCAngle  = 45                     ' Winkel 0(Hops6): in Verlaengerung der Anfahrbewegung
		TRCFactor = 1                      ' Faktor 0(Hops6) 
		TRCLength = 0.1                    ' Strecke (1mm) fuer Korrekturaufbau
'	ElseIf equal(JobPara.ID.TRC_Strategy,11) Then
'		TRCAngle  = 60                     ' Winkel 0(Hops6): in Verlaengerung der Anfahrbewegung
'		TRCFactor = 1.01                   ' Faktor 0(Hops6) 
'		TRCLength = 1                      ' Strecke (1mm) fuer Korrekturaufbau
	Else
		' Classic
		TRCAngle=0                               ' Winkel 0(Hops6): in Verlaengerung der Anfahrbewegung
		TRCFactor=0                              ' Faktor 0(Hops6) 
		TRCLength = 1                            ' Strecke (1mm) fuer Korrekturaufbau
	End If

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
	' MW 24.02.2016
	If PostSettings.GeneralSettings.EnableCreateNew <> EnableCreateNew Then
		PostSettings.WriteBool("NC","EnableCreateNew",EnableCreateNew)
		Err = Err + "EnableCreateNew;"
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
	
' MW 21.07.2017 why not	
'	If PostSettings.DrillingsSettings.NewDHOpti <> NewDHOpti Then
'		PostSettings.WriteBool("EINST","NeueBohrOpti",NewDHOpti)
'		Err = Err + "NewDHOpti"
'	End If

' MW 21.07.2017 why not	
'	If PostSettings.DrillingsSettings.DHModeOldDrillOpti <>ModeOldDrilOpti Then
'		PostSettings.WriteInteger("EINST","ModeOldDrilOpti",ModeOldDrilOpti)
'		Err = Err + "ModeOldDrilOpti;"
'	End If

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
	
' MW 21.07.2017 why not	
'	If PostSettings.DrillingsSettings.DHCheckAllHoles <>CheckAllHoles Then
'		PostSettings.WriteBool("NC","CheckAllHoles",CheckAllHoles)
'		Err = Err + "CheckAllHoles;"
'	End If
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

	
' Bohrkopf generelle Logik DLL JA/NEIN ?
	If PostSettings.DrillingsSettings.CalcDHMoves <> CalcDHMoves Then
		PostSettings.WriteBool("EINST","CalcDHMoves",CalcDHMoves)
		Err = Err + "CalcDHMoves;"
	End If
	If PostSettings.DrillingsSettings.CalcDHFirstActiveSpindleIsRefPoint <> CalcDHFirstActiveSpindleIsRefPoint Then
		PostSettings.WriteBool("EINST","CalcDHFirstActiveSpindleIsRefPoint",CalcDHFirstActiveSpindleIsRefPoint)
		Err = Err + "CalcDHFirstActiveSpindleIsRefPoint;"
	End If
	If PostSettings.DrillingsSettings.CalcDHRelativToRefSpindle <> CalcDHRelativToRefSpindle Then
		PostSettings.WriteBool("EINST","CalcDHRelativToRefSpindle",CalcDHRelativToRefSpindle)
		Err = Err + "CalcDHRelativToRefSpindle;"
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


' EVO: Ermittlung ueber Vorlauf in welcher Szene Bearbeitungen vorhanden sind, welche sich auf die Teilelaenge beziehen (Messwertverrechnung)
' HH generell: Ermittlung der Szenen fuer moegliche Einspruenge "Jumps zu einer Bearbeitung"

Function EvoPreCheck_Obj   ' Vorlauf ueber NCDATA
Dim p,NCI,dhs As Long 
Dim ClampChange As Boolean 
Dim NCIGl
Dim Obj 
Dim ObjNCI
Dim DHStroke
Dim SceneCount As Long 
Dim MinX As Double
Dim MaxX As Double 
	
	' Fuer Jumps Einsprunginfo
	' ---------------------------
	SceneCount = 1
	ReDim JobPara.mea.MessSzene(1)
	JobPara.mea.MessSzene(UBound(JobPara.mea.MessSzene))=False
	ReDim JobPara.TC_SC(NCData.ProcessList.Count)
	' ---------------------------
	

	ReDim JobPara.mea.MessSzene(1) 	                                  ' bisher in InitZero_Plausi
	JobPara.mea.MessSzene(UBound(JobPara.mea.MessSzene))=False

	'NCI_Global_Check
	For NCI = 0 To NCData.NCInfo_Global.CountNCI - 1
		Set NCIGl = NCData.NCInfo_Global.GetNCI_Index(NCI)
		If NCIGl.IsGlobal And equal(NCIGl.Kind,91) And (UCase(NCIGl.Text)="QUOTE") Then
			' NINFO 91 gefunden --> Wert fuer Messquote gefunden
			JobPara.Mea.QuoteXQD = NCIGl.Para1
			If JobPara.Mea.QuoteXQD > JobPara.Mea.MaxQuoteX Then
				pp_Err(580,JobPara.Mea.QuoteXQD,JobPara.Mea.MaxQuoteX)
			End If
			' MW 17.12.2018 Qoute fuer Fraes-/Saegebearbeitungen
			JobPara.Mea.QuoteXQM = NCIGl.Para2
			If JobPara.Mea.QuoteXQM > JobPara.Mea.MaxQuoteX Then
				pp_Err(580,JobPara.Mea.QuoteXQM,JobPara.Mea.MaxQuoteX)
			End If
		End If
	Next NCI
	
	
	For p = 0 To NCData.ProcessList.Count -1
	
		Set Obj = NCData.ProcessList.GetProcess_NCInfoIndex(p)
		
		JobPara.TC_SC(p) = SceneCount
		
		' Clampchange vorwirksam suchen
		For NCI = 0 To Obj.NCInfoListBefore.CountNCI-1
			' Alle vorwirksamen NCINFOS durchgehen
			If Obj.NCInfoListBefore.GetNCI_Index(NCI).IsClampChange Then
				SceneCount = SceneCount + 1    ' eine Szene weiter
				' Clampchange ohne dass zuvor Bearbeitung gekommen ist
				ReDim Preserve JobPara.mea.MessSzene(UBound(JobPara.mea.MessSzene)+1) 	
				JobPara.mea.MessSzene(UBound(JobPara.mea.MessSzene))=False
			End If
			
			' Ermittlung ob Fraesbearbeitung mit Massbezug, dann muss auch in dieser Szene gemessen werden
			If (Obj.NCInfoListBefore.GetNCI_Index(NCI).Kind = 70099) And (Obj.NCInfoListBefore.GetNCI_Index(NCI).Para1<=30) Then
				JobPara.mea.MessSzene(UBound(JobPara.mea.MessSzene))=True    ' in dieser Szene muss gemessen werden
				If MT_Get_MachPara_Add(30000003)="1" Then
					If (Obj.PreObjectTyp=otVertDrilling) Then
						AddHint("Szene #"+inttos(UBound(JobPara.mea.MessSzene))+ " vertikales Bohren #"+inttos(p+1)+" mit Messwert- Verrechnung " )
					ElseIf (Obj.PreObjectTyp=otHorzDrilling) Then
						AddHint("Szene #"+inttos(UBound(JobPara.mea.MessSzene))+ " horizontales Bohren #"+inttos(p+1)+" mit Messwert- Verrechnung " )
					ElseIf (Obj.PreObjectTyp=otSawing) Then
						AddHint("Szene #"+inttos(UBound(JobPara.mea.MessSzene))+ " Saegebearbeitung #"+inttos(p+1)+" mit Messwert- Verrechnung " )
					ElseIf (Obj.ObjectTyp = otMilling) Or (Obj.ObjectTyp = otMillingMPs) Then
						AddHint("Szene #"+inttos(UBound(JobPara.mea.MessSzene))+ " Fraesbearbeitung #"+inttos(p+1)+" mit Messwert- Verrechnung " )
					Else
						AddHint("Szene #"+inttos(UBound(JobPara.mea.MessSzene))+ " Bearbeitung #"+inttos(p+1)+" mit Messwert- Verrechnung " )
					End If
				End If
				
			End If

		Next NCI
		
		' nach Bohrungen im DH - Process suchen und pruefen ob diese im Messquoten- Bereich liegen
		If Obj.ObjectTyp=otDHProcess Then
			' Bohrkopfbearbeitung gefunden
			For dhs = 0 To Obj.DHStrokeList.Count-1
				Set DHStroke = Obj.DHStrokeList.GetDHStroke(dhs)

				Evo_Check_MeaDrill(DHStroke.FirstPosX)   ' setzt [JobPara.mea.Bea_Mea_activ = True] wenn Bearbeitungspos X im Messqouten - Bereich

				If JobPara.mea.Bea_Mea_activ Then
					' Bohrung mit Messwert - Verrechnung
					JobPara.mea.MessSzene(UBound(JobPara.mea.MessSzene))=True    ' in dieser Szene muss gemessen werden
					If MT_Get_MachPara_Add(30000003)="1" Then
						AddHint("Szene #"+inttos(UBound(JobPara.mea.MessSzene))+ IIf(DHStroke.IsVertical," - BK verticalDrill #" +inttos(dhs)," - BK horiz.Drill #" +inttos(dhs)) + " X:"+ftos(DHStroke.FirstPosX) +" Y:"+ftos(DHStroke.FirstPosY) + " mit Messwert- Verrechnung " )
					End If
					AddLog("Szene #"+inttos(UBound(JobPara.mea.MessSzene))+ IIf(DHStroke.IsVertical," - BK verticalDrill #" +inttos(dhs)," - BK horiz.Drill #" +inttos(dhs)) + " X:"+ftos(DHStroke.FirstPosX) +" Y:"+ftos(DHStroke.FirstPosY) + " mit Messwert- Verrechnung " )
			
				End If
				JobPara.mea.Bea_Mea_activ = False
				
			Next
		End If
		
		' nach Bearbeitungen Fraesen suchen und pruefen ob diese im Messquoten- Bereich liegen
		If Obj.ObjectTyp=otMillingMPs Then
			' Fraesbearbeitung gefunden

				Evo_Check_MeaMill(Obj,MinX,MaxX)   ' setzt [JobPara.mea.Bea_Mea_activ = True] wenn Bearbeitungspos X im Messqouten - Bereich

				If JobPara.mea.Bea_Mea_activ Then
					' Bearbeitung mit Messwert - Verrechnung
					JobPara.mea.MessSzene(UBound(JobPara.mea.MessSzene))=True    ' in dieser Szene muss gemessen werden
					If MT_Get_MachPara_Add(30000003)="1" Then
						AddHint("Szene #"+inttos(UBound(JobPara.mea.MessSzene))+ " - Prozess ["+inttos(p+1) + "] - Tool [" + Obj.Tool.Description + " MinX ["+ftos(MinX)+"]" + " MaxX ["+ftos(MaxX)+"]  mit Messwert- Verrechnung " )
					End If
					AddLog("Szene #"+inttos(UBound(JobPara.mea.MessSzene))+ " - Prozess ["+inttos(p+1) + "] - Tool [" + Obj.Tool.Description + " MinX ["+ftos(MinX)+"]" + " MaxX ["+ftos(MaxX)+"]  mit Messwert- Verrechnung " )
			
				End If
				JobPara.mea.Bea_Mea_activ = False
				
		End If
		
		
		' Clampchange nachwirksam suchen
		For NCI = 0 To Obj.NCInfoListAfter.CountNCI-1
			' Alle nachwirksamen NCINFOS durchgehen
			If Obj.NCInfoListAfter.GetNCI_Index(NCI).IsClampChange Then
				SceneCount = SceneCount + 1    ' eine Szene weiter
				' Clampchange nach Bearbeitung
				ReDim Preserve JobPara.mea.MessSzene(UBound(JobPara.mea.MessSzene)+1) 	
				JobPara.mea.MessSzene(UBound(JobPara.mea.MessSzene))=False
			End If
		Next NCI
		
	Next p
	Set NCIGl = Nothing
	Set Obj = Nothing
	Set ObjNCI = Nothing
	Set DHStroke = Nothing
	'AK 20.03.2019
	Marker.MaxSceneNo=SceneCount
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
	PP.SuctionPos = -1
	ReDim PP.NCiExtB(0)
	ReDim PP.NCiExtA(0)
	Set PP.NTool = Nothing
	PP.NHeadInfo = ""
	PP.TipA = 0
	PP.RotA = 0
	PP.HeadTipA = 0
	PP.HeadRotA = 0
	PP.HeadSPAX = 0    ' 1. Anfahrposition in X fuer Werkzeugwechsel
	PP.HeadSPAY = 0    ' 1. Anfahrposition in Y fuer Werkzeugwechsel
	PP.HeadSPAZ = 0    ' 1. Anfahrposition in Z fuer Werkzeugwechsel
	
	' Programmierbare NCIExt's
	PP.NCiE.sh.activ = False
	PP.NCiE.dynamic.activ = False  ' MW 27.06.2016 - PP.dynamic.no = unnuetze
	PP.Din_ISO_8201 = False    ' Dieser wird wenn NCInfoProzess kommt direkt mit dem NCINFOProzess abgesetzt somit muss dieser nicht beim NCINFO - Aufruf selbst abgesetzt werden
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
	Set p.View = Obj.View
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
			'p.ProcessGroup = NCData.GetExtInfo(ekNCProcess_ProcessGroup,MMPs)
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
			'p.ProcessGroup = NCData.GetExtInfo(ekNCProcess_ProcessGroup,MP)
			

		Case otNCInfoProcess
			' 7: NCINFOProcess
		Case otDHProcess
			' 9: Bohrkopf
			
		Case otNCInfoProcessMPs			
			' 12: NCInfoProcess als Milling
		
		Case Else
			pp_Err(0,"wrong ObjectTyp")

	End Select 
	
	
	Set P_MinMax = NCData.GetExtInfo(ekNCProcess_HeadMinMax,Obj) ' -> [INCProcessMinMaxInfo@0x0B7D77F0]
	If Not P_MinMax Is Nothing Then
		p.Minx = P_MinMax.Minx
		p.Maxx = P_MinMax.Maxx
		p.Miny = P_MinMax.Miny
		p.Maxy = P_MinMax.Maxy
		If Not T.h Is Nothing Then
			p.Minx = p.Minx - T.h.CenterX
			p.Maxx = p.Maxx - T.h.CenterX
			p.Miny = p.Miny - T.h.CenterY
			p.Maxy = p.Maxy - T.h.CenterY
		End If
		
	End If
	
	' Info
	p.ProcessGroup = NCData.GetExtInfo(ekNCProcess_ProcessGroup,Obj)
	
	p.ProcInfoStr  = GetStrObjectTyp(Obj) + "("+inttos(GetObjectTypNo(Obj))+")"  
	
	
	' Vorschuebe bereits plausibilisiert auf MIN/MAX !!!
	p.Feedrate = Obj.Feedrate
	p.I_Feedrate = Obj.MoveInFeedrate
	p.S_Feedrate = Obj.MoveOutFeedrate
	p.Speed = Obj.RotSpeed
	
	
	' MW 11.04.2016 Plausibilisierung PP - Zwischenstand
	If MT_H_Is_5_Axis(T) And mt_isgb(T) Then
'		pp_Err(6,"")
	End If
'	If MT_H_Is_5_Axis(T) Then
'		SicMode = MT_get_Add_ID_HeadExt(T,-20002,isOK)
'		If isOK Then	
'		
'		End If
'	End If

	Set p.Part = NCData.NCParts.GetNCPart_Index(Obj.PartIndex)

	PPara = p   ' -> Zuweisung auf global Para
	MT_ClearTHopsBasicToolExt(T)
	Set Obj = Nothing
	Set MMPs = Nothing
	Set MP = Nothing
	Set P_MinMax = Nothing

	' MW 01.04.2016
	'JobPara.P_Info = "Process #"+inttos(PPara.PLNo)+ " - ID:<"+inttos(PPara.ToolID)+"> T:<"+Get_TN_Info(PPara.ToolID)+"> " + " Kind:<" + PPara.ProcInfoStr +"> HId:<"+inttos(PPara.HId)+ ">" 
	JobPara.P_Info = "Process #"+inttos(PPara.PLNo)+ " Kind:<" + PPara.ProcInfoStr +">"+ " - BOXID:<"+inttos(PPara.ToolID)+"> T:<"+Get_TN_Info(PPara.ToolID)+"> "+ " HId:<"+inttos(PPara.HId)+ ">" + _
	       " Xmin:"+ftos(PPara.Minx) + " Xmax:"+ftos(PPara.Maxx) + _
	       " Ymin:"+ftos(PPara.Miny) + " Ymax:"+ftos(PPara.Maxy) 

End Sub

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
				' -> kann nicht vorkommen da zuvor ProObjectTyp gesetzt wird
				resu = "MillingPoints"
			Case otMillingMPs		    
				' -> kann nicht vorkommen da zuvor ProObjectTyp gesetzt wird
				resu = "MillingMPs"
			Case otNCInfoProcessMPs 
				' NCinfoProcess - ProcessKind = 1/2 = Drilling/Milling
				resu = "NCInfoProcessMPs"
	End Select 
	GetStrObjectTyp = resu
End Function


Function GetObjectTypNo(Obj) As Integer
Dim resu As Integer
Dim objt,mode As Integer 
	If (Obj.ObjectTyp = otMillingMPs) Then
		objt = Obj.PreObjectTyp
		mode = Obj.Mode
	ElseIf (Obj.ObjectTyp = otMillingPoints) Then
		objt = Obj.PreObjectTyp
		mode = Obj.MMode
	Else
		objt = Obj.ObjectTyp
	End If
	
	resu = objt
	Select Case objt
			Case otNotdefinied
				'resu= "not definied"
		    Case otNCInfo
				'resu = "NCInfo"
		    Case otMilling
			    resu = resu + IIf(mode=1,19,IIf(mode=2,20,0))
				'resu = "Milling" + IIf(mode=1," with C-Axis",IIf(mode=2," 5Axis",""))
			Case otVertDrilling 		    
				'resu = "VertDrilling"
			Case otHorzDrilling 		   
				'resu = "HorzDrilling"
			Case otSawing 		    
				'resu = "Sawing"
			Case otNCProcess 		    
				pp_Err(1569)  ' darf nicht vorkommen
				'resu = "NCProcess"
			Case otNCInfoProcess 		    
				'resu = "NCInfoProcess"
			Case otNCContourProcess 		    
				pp_Err(1569)  ' darf nicht vorkommen
				'resu = "NCContourProcess"
			Case otDHProcess 		    
				'resu = "DHProcess"
			Case otMillingPoints 	
				' -> kann nicht vorkommen da zuvor ProObjectTyp gesetzt wird
				'resu = "MillingPoints"
			Case otMillingMPs		    
				' -> kann nicht vorkommen da zuvor ProObjectTyp gesetzt wird
				'resu = "MillingMPs"
			Case otNCInfoProcessMPs 
				' NCinfoProcess - ProcessKind = 1/2 = Drilling/Milling
				'resu = "NCInfoProcessMPs"
	End Select 
	GetObjectTypNo = resu
End Function



Sub ProcessInfoClear(p As TProcessPara)
	' ALLES ABLOESCHEN
	ProcessInfo_Init(p)
	
	Set p.Tool = Nothing
	Set p.NTool = Nothing
	ReDim p.NCiExtB(0) ' Objectliste aller vorwegwirksamen NCIExt 
	ReDim p.NCiExtA(0) ' Objectliste aller nachwegwirksamen NCIExt 
	

	
End Sub


' MW 01.04.2016 -> hier werden eigentlich nur noch die MinMax TipRot - Werte gesetzt
Function Add_SPInfoMPs_7(mode,PreObjectTyp, MinRot,MaxRot,MinTipA,MaxTipA, R1, R2, R3,  R4)

	' Mode 0 : Standard
	' Mode 1 : C-Achsfraesen
	' Mode 2 : Vektorfraesen/5Achsfraesen
	If mode=1 Then
		If equal(MinTipA,MaxTipA) Then
			' das ist der Kippwinkel fuer das C-Achsfraesen - notwendig z.B. fuer das Stellen funkgest. Stellachse (Stellung ueber aufruf eines Zyklus')
		Else
			pp_Err(1,"Angle C-Axis milling not constant")
		End If
		'mill_c.activ = True
		'MillC_INIT(True,DirectionMode,ExcessLength,Mode,AxisRotA,KW,TRC,DISTANCE,dw)			
	End If
	
	If mode=2 Then	
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
	If Not equal(PPara.MMode, mode) Then
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


Function Get_ToolList
Dim i As Long
Dim Obj
Dim TID As Long
Dim HeadInfo As Variant
Dim Head As Long 
Dim PInd As Integer 
	Marker.CountOfTool = NCData.ProcessList.Count
	
	' -- 
	' -- ToolArray init
	' -- 
	If Marker.CountOfTool>0 Then 
     	ReDim ToolArray(Marker.CountOfTool)
    End If
    
	' -- 
	' -- Messteile  init
	' -- 
	JobPara.Measuring.Activ = False
	
	ReDim JobPara.Measuring.NCParts(NCData.NCParts.Count) 
	For i = 0 To NCData.NCParts.Count-1
		If Not NCData.NCParts.GetNCPart_Index(i) Is Nothing Then
			JobPara.Measuring.NCParts(i).Amount=0
		End If
			
	Next i
    

	For i = 0 To NCData.ProcessList.Count-1
		Set Obj = NCData.ProcessList.GetProcess_NCInfoIndex(i)
		If Not Obj Is Nothing Then
			' -- 
			' -- ToolArray fuellen
			' -- 
			TID = Obj.ToolID
			HeadInfo = Obj.HeadInfo
			Head = Val(HeadInfo) 
			MT_SetTHopsBasicToolExt(ToolArray(i),TID,Head)
				
				
				
			' -- 
			' -- NCInfoProzesse MessVorgang aufsammeln
			' -- 
				
			If (Obj.ObjectTyp = otNCInfoProcessMPs) Then  ' -> 12&
				If (Obj.Kind = -210001) And (MT_IsMEAS(ToolArray(i))) Then
					' Messen - hier die Ermittlung der benoetigen Arraygroessen
					' Obj.PartIndex
					' obj.para7 = Werkstueckuebergreifende Messnummer #1001,#1002 / #2001,#2002


					JobPara.Measuring.Activ = True    ' -- messen gefunden

					PInd = Obj.PartIndex
					
					JobPara.Measuring.NCParts(PInd).PartNo = PInd  ' -- Teilenummer ueber diese kann Teilename, Nullpunkt ect. geholt werden
					JobPara.Measuring.NCParts(PInd).Amount = JobPara.Measuring.NCParts(PInd).Amount + 1
				End If
				
			End If
		End If
		Set Obj = Nothing
	Next i
End Function


' MW 31.03.2016 Drehzahl Zentral absetzen
Function Speed_Call_7(Optional TC As Boolean )   ' TC = True wenn Aufruf ueber Werkzeugwechsel

    If IsMissing(TC) Then
    	TC  = False
    ElseIf TC = True Then
		Marker.LastSpeed = -99999   ' damit Drehzahl immer abgesetzt wird
    End If

	' Ausschluss
	If MT_is_VBM_Stempel(ActT) Then
		Exit Function
	End If
	If MT_isPneumaticSaw(ActT) And TC Then
		' Ausrichtung und Spindel einschalten erst im Ebenenwechsel, da
		' Ausrichtung vorher nicht bekannt.
		
		'MT_Write_Speed(ActT,pspeed)

		Exit Function
	End If

	Select Case PPara.PreObjectTyp
		Case otNCInfoProcess,otNCInfoProcessMPs
			' DINISO - PROZESS - nur wenn Drehzahl gewuenscht absetzen
			If Not (IsDINISO_No_Speed) And (isDINISO_Process) Then
				MT_Write_Speed(ActT,PPara.Speed)
			End If
		
		Case otDHProcess 		    
			' --
			' -- wenn Speed = 0 -> dann Drehzahl von Bohrer uebernehmen
			' --
			If ((Not equal(Marker.LastSpeed,PPara.Speed)) Or TC) And (PPara.Speed <> 0) Then
				MT_Write_Speed(actt,PPara.Speed)
				'AK 22.04.2015 Prozssspeed setzen sonnst kommt bei Lochreihe immer Speedausgabe
				' ProcessPara.Speed = speed
		                ' -> MW 07.05.2015 Hier nicht notwendig, da Function PParaSet dies uebernimmt
		
			End If
		Case otVertDrilling, otHorzDrilling
			If ((Not equal(Marker.LastSpeed,PPara.Speed)) Or TC) Then
				MT_Write_Speed(ActT,PPara.Speed)
			End If
		Case Else
			If TC Then
				' Aufruf von Werkzeugwechsel
				If MT_NoTurningWithSpindelRot(actT) Then
					' MW 06.03.2014
					' Big Tool erst unmittelbar vor der Bearbeitung Spindel starten
				Else
					MT_Write_Speed(ActT,PPara.Speed)
				End If
			Else
				If MT_NoTurningWithSpindelRot(actt) Then
				 	' -- MW 06.03.2014
					' Big Tool erst unmittelbar vor der Bearbeitung Spindel starten
					MT_Write_Speed(ActT,PPara.Speed)
				Else
					If Not equal(Marker.LastSpeed,PPara.Speed) Then
						MT_Write_Speed(ActT,PPara.Speed)
					End If
				End If
			End If

	End Select 

	
End Function

'Function PPara_Set(PNo,I_Feedrate,Feedrate,S_Feedrate,speed)
'
'                                TEST die Objectdaten muesen mit den uebergebenen uebereinstimmen
'Dim F As Double
'Dim I As Double
'Dim S As Double
'Dim Sp As Double 
'Dim pot As Integer 
'Dim Obj 
	' kommt beim C-Achsfraesen, Oberflaechenfraesen 5-Achsfraesen

' 	Set Obj = 

' TEST !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
'	F = NCData.ProcessList.GetProcess_NCInfoIndex(PNo-1).Feedrate
'	I = NCData.ProcessList.GetProcess_NCInfoIndex(PNo-1).MoveInFeedrate
'	S = NCData.ProcessList.GetProcess_NCInfoIndex(PNo-1).MoveOutFeedrate
'	Sp = NCData.ProcessList.GetProcess_NCInfoIndex(PNo-1).RotSpeed
'	
'	If PNo <> PPara.PLNo Then
'		pp_Err(126)
'		PPara.PLNo = PNo
'	End If

	
'	If Not equal(F,PPara.Feedrate) Or Not equal(I,PPara.I_Feedrate) Or Not equal(S,PPara.S_Feedrate) Or Not equal(Sp,PPara.Speed) Then 'Or Not equal(pot,PPara.PreObjectType) Then 
'		pp_Err(126)
'	End If
'End Function



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
	ElseIf Err = 5 Then
		If (JobPara.language.ID=1031) Then
			errstri = errstri + Chr(13)+Chr(10)+"Postprozessor bitte nochmals starten"
		Else
			errstri = errstri + Chr(13)+Chr(10)+"please start postprocessing once again"
		End If
	Else 
		errstri = errstri + Chr(13)+Chr(10)+"general error"
	End If
			errstri = errstri + Chr(13)+Chr(10)+"1"
			errstri = errstri + Chr(13)+Chr(10)+"2"
			errstri = errstri + Chr(13)+Chr(10)+"3"
			errstri = errstri + Chr(13)+Chr(10)+"4"
	Get_ErrMsg = errstri
	
'  	Set iiSet = Nothing
	
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
		Err_en = " - please restart Postprocessor"
	Case 3 
		Err_de = "falsches Werkzeug, oder ungueltiger Werkzeugtyp"
		Err_en = "wrong Tool or wrong Tooltype"
	Case 4 		
		Err_de = "es ist ein unerwarteter Fehler ist aufgetreten - die Prozessanzahl der Kanaele ist unterschiedlich"
		Err_en = "it encountered an unexpected error - the number of processes in the channels is different"
	Case 5
		Err_de = "falsche Einstellung in der Datei PP.ini [" + var1 + "]"
		Err_en = "wrong settings found in file PP.ini [" + var1 + "]"
	Case 6
		Err_de = "Dieses Funktionalitaet ist noch nicht implementiert [" + var1+"]"
		Err_en = "This functionality is not yet implemented [" + var1+"]"
	Case 7
		Err_de = "Die Funktionalitaet dieser ID wird nicht unterstuetzt - Maschine - Parameter - ID[" + var1+"]"
		Err_en = "The functionality of the used ID - Machine - Parameter - ID[" + var1+"] is not supported anymore"
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
	Case 17
		Err_de = "Unerlaubte Einstellung im MTManager bei Bearbeitungskopf "+var1+" Zusatzinformationen [PP;SIMU] ID #"+inttos(var2)
		Err_en = "Defined Option in Head "+var1+" additional information [PP;SIMU] ID #"+inttos(var2)+ " not allowed"
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
	Case 120	
		Err_de = "Einsprungmarken konnten nicht korrekt gesetzt werden"
		Err_en = "Jump to - Positions error - wrong tool!"
	Case 121 
		Err_de = "Werkzeugvorwechsel - Information (Parameter ID=2000) nur bei Maschinen mit einer Wechselspindel zulaessig"
		Err_en = "CP_PreChange - possible only if one Toolchange - Spindle is available"
	Case 122
		Err_de = "interner Postprozssor - Fehler, Anweisung nicht gefunden"
		Err_en = "unexpected error 1424-3247 - internal error - syntax not found"
	Case 125 
		Err_de = "Einsprungmarken - falsche Anzahl"
		Err_en = "Jump - Positions Count Error !"
	Case 126
		Err_de = "Inkonsistenz im Postprozessor Script gefunden - " + var1
		Err_en = "inconsistency found in Postprocessor Script - " + var1
	Case 127
		Err_de = "Die angegebenen Messnummer #"+inttos(var1)+" bezieht sich auf einen Messpunkt mit einer anderen Messrichtung"
		Err_en = "specified measuring number#"+inttos(var1)+" refers to a measuring point in different direction"
	Case 128
		Err_de = "Die angegebenen Messnummer #"+inttos(var1)+" bezieht sich auf einen nicht vorhandenen Messpunkt"
		Err_en = "the specified measuring number #"+inttos(var1)+" refers to a non existing measuring number"
	Case 129
		Err_de = "Die angegebenen Messtoleranz ["+ftos(var1)+"] ueberschreitet die maximal zugelassene Toleranz ["+ftos(var2)+"]"
		Err_en = "specified measure tolerance ["+ftos(var1)+"] higher than the maximum tolerance [" +ftos(var2)+"]"
	Case 140 
		Err_de = "Ungueltiger Wert bei Maschinenparameter ID:"+var1
		Err_en = "wrong value - Machine parameter ID:"+var1
	Case 150 
		Err_de = "Fehler bei Ermittlung des Werkzeugwechsler Typs - Werkzeug:"+var1
		Err_en = "Error while checking Toolchanger of Tool:"+var1
	Case 154
		Err_de = "Ausgangsrichtung/Kippstellung Min:"+var1+" Max:"+var2+" des Winkelgetriebes kann nicht erreicht werden - Limit ueberschritten"
		Err_en = "Orientation Gearbox Min:"+var1+" Max:"+var2+" can not be reached - limit exceeded"
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
	Case 221
		Err_de = "Fehler bei Clampchange - keine unterschiedlichen Spannpositionen gefunden"
		Err_en = "error in function Clampchange - no different clamp situations found"
	Case 224
		Err_de = "5-Achs falsches Werkzeug fuer diesen Vorgang"
		Err_en = "5-Axis wrong tool "
	Case 300
		Err_de = "Laserausgabe - Fehler bei Ermittlung Anzahl Felder"
		Err_en = "error calculating fields"
	Case 301
		Err_de = "nicht interpretierbarer Wert"
		Err_en = "wrong value"
	Case 302
		Err_de = "Laserdaten nicht gefunden"
		Err_en = "required laser data was not found"
	Case 303
		Err_de = "Laserbereich ueberschritten"
		Err_en = "laser area limit exceeded"
	Case 304
		Err_de = "Laser - Werkzeug nicht gefunden"
		Err_en = "laser - Tool not found"
	Case 305
		Err_de = "fuer Laser wurde falsche Nummer zugwiesen"
		Err_en = "wrong number definition for laser"
	Case 306
		Err_de = ""
		Err_en = ""
	Case 320
		Err_de = "ungueltiger Bearbeitungskopf"
		Err_en = "invalid Head ID"
	Case 350
		Err_de = "unerlaubte Richtung bei BohrkopfAusgang"
		Err_en = "unexpected direction drilling head"
	Case 351
		Err_de = "Fehler bei Nutsaege Bohrkopf - unerlaubte Richtung bei Bohrkopf/Saegeausgang"
		Err_en = "unexpected direction drilling head/saw"
	Case 352
		Err_de = "Fehler bei Aggregat - unerlaubte Richtung vom Ausgang"
		Err_en = "unexpected direction head"
	Case 353
		Err_de = "unerlaubte Schneidennummer"
		Err_en = "invalid cutting edge"
	Case 354
		Err_de = "Winkelgetriebe - falsche Werkzeugdaten"
		Err_en = "wrong tool data angular head"
	Case 355
		Err_de = "keine Wechslerspindel gefunden"
		Err_en = "no toolchanger Head found"
	Case 356
		Err_de = "Ausgang der Spindel konnte nicht ermittelt werden"
		Err_en = "invalid direction of Head"
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
	Case 1506
	Case 1509
	Case 1510
	Case 1511
	Case 1512 
	Case 1513
		Err_en = "Postprozessor Engine " + Replace(var1,";",".") +" oder hoeher erwartet"		
		Err_de = "Post Engine " + Replace(var1,";",".") +" Or higher necessary"		
	Case 1514 
	Case 1515
	Case 1516
	Case 1517
	Case 1518
	Case 1519
	Case 1520
	Case 1521
	Case 1522
	Case 1523
	Case 1524
	Case 1525
	Case 1526
	Case 1528
	Case 1529
	Case 1530
	Case 1531
	Case 1532
	Case 1533 
	Case 1534
	Case 1535
	Case 1536
	Case 1537
	Case 1538
	Case 1539
	Case 1540
	Case 1541
	Case 1542
	Case 1543
		Err_de = "Ordner nicht gefunden <"+var1+">"
		Err_en = "Folder not found <"+var1+">"
	Case 1545
		Err_de = "Werkzeug nicht geruestet"
		Err_en = "Tool not fitted on Head or Toolchanger"
	Case 1546
	Case 1547
	Case 1548
	Case 1549
		Err_de = "PP.INI Eintrag [VERSION] - "+var1+" ungueltig"
		Err_en = "PP.INI entry [VERSION] - "+var1+" invalid"
	Case 1550
	Case 1551
	Case 1552
	Case 1553
		Err_de = "NCINFO #"+inttos(var1)+" wird in dieser Version nicht mehr unterstuetzt"
		Err_en = "NCINFO #"+inttos(var1)+" not supported in this version of Post"
	Case 1554
	Case 1555
		Err_de = "PP.INI Eintrag "+var1+" nicht gefunden"
		Err_en = "PP.INI entry  "+var1+" not found"
	Case 1558
		Err_de = "Oszillierende Bearbeitung mit Kippwinkel bzw. Ebene <> 0 nicht moeglich"
		Err_en = "oscilating working with angle or on view <> 0 impossible"
	Case 1559
	Case 1561
	Case 1563
	Case 1564
	Case 1568
	Case 1569
		Err_de = "Dieser Art der Bearbeitung wird derzeit leider noch nicht unterstuetzt: "
		Err_en = "This kind of working is not supported at the moment"
	Case 1571
	Case 1572
	Case 1575
	Case 1585
	Case 1585
	Case 1586
	Case 1588 
	Case 1589 
		Err_de = "Programmierte Haubenposition auﬂerhalb des zulaessigen Bereichs Pos:"+inttos(var1)
		Err_en = "not allowed programmed Suction position found Pos:"+inttos(var1)
	Case 1590
		Err_de = "PROZESSNCINFO #"+inttos(var1)+" wird In dieser Version nicht mehr unterstuetzt"
		Err_en = "PROCESSNCINFO #"+inttos(var1)+" not supported in this version of Post"
	Case 1591
	Case 1592
		Err_de = "Bearbeitungskopf [" +var1 + "] nicht gefunden" 
		Err_en = "Processhead [" +var1 + "] not found" 
	Case Else
		AddMistake("Err"+inttos(ErrNo)+" not found")
		Exit All
		Stop
	End Select
	
End Function



