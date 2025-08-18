' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \%postdir%\pp_mt.bas
' -- 
' -----------------------------------------
'#uses "pp_global.bas"
'#uses "pp_math.bas"
Option Explicit

' -------------------------------------------------------
' -- erweiterte Funktion um die Laufzeitinfo über aktuelle
' -- arbeitende Aggregat zu implementieren
' --
' -------------------------------------------------------
Global Type THopsBasicToolExt
	MachineData As IToolMachineData            ' Maschinendaten wie z.B. die Referenzspindel für Verfahrbereich
	T As IIHopsBasicTool
	H As IIProcessHead
	DH As IIDrillingHead
	HA As IIHead
	gb As IIGearBox  ' neu mw 15.3.2005
    T_S As IIHopsStandardTool                  ' ObjectType = 1   Hauptspindel Werkzeugwechsler
    T_DH As IIHopsDrillingHeadTool             ' ObjectType = 2   Bohrkopf
    T_PH As IIHopsProcessHeadTool              ' ObjectType = 3   Nebenaggregat
    T_GB As IIHopsGearBoxTool                  ' ObjectType = 4   Winkelgetriebe
    T_SGB As IIHopsSpecialGearBoxTool          ' ObjectType = 5   Special Gearbox like 3,5 Drillers in Row ' 
    T_TCA_GB As IIHopsTC_AccessGearBoxTool ' ObjectType = 6   Toolchanger access Gearbox ' 
    T_DHSaw As IIHopsDH_SawTool                ' ObjectType = 7   Groove Saw on DrillingHead ' 
	HId As Integer                             ' Head ID / Agg No
    AggName As String                          ' Bezeichnet das Aggregat näher
    TC As IIToolChangerHead
    T_CEdge As IICuttingEdge
    ' Neu MW 12.04.2005
    ' eingeführt für Plausibiltätsprüfung Bohrkopf
    T_Driller As tDriller                       ' wird von vertical-drillinghead stroke gesetzt
    'T_Dh_TP As IIDH_ToolPlace
    'TTool As IITool                            ' neu MW 13.04.2005 für Flex5 um dessen Subtoolchanger zu ermitteln
    PH_Add As t_PH_Additions                   	' Zusatzinformationen von Bearbeitungskopf
    H_Add As t_H_Additions                   	' Zusatzinformationen von Bearbeitungskopf
    DH_ADD As t_DH_Additions 
    TC_Place As Long                            ' Werkzeugwechselplatz 
End Type
' --
' -------------------------------------------------------

' -- Datatypes for tool handling
'actual tool
Global ActT As THopsBasicToolExt

Global FirstT As THopsBasicToolExt

'last tool
Global LastT As THopsBasicToolExt

'toolchange before
Global TCB_T As THopsBasicToolExt  ' vorwechsel - tool

'array of all tools
Global ToolArray() As THopsBasicToolExt

'Actual Tool Position
Global ToolPos As Long




' ------------------------------------------------------------------------------------
' --
' -- Name - Definitions for the subs on the cnc - controller

Global Const SPF_TCheck = "; "    '"CP_TCheck"  ' check tools
Global Const SPF_TC = ";CP_TC"  ' sub name on cnc-controller for the toolchange
Global Const SPF_TCarr = ";CP_TCPara"   ' sub name for setting the TCarr - parameters
Global Const SPF_StartProg = ";CP_START"   ' Start Programm
Global Const SPF_EndProg = ";CP_END"   ' ende Programm
Global Const SPF_Panel = ";CP_PANEL"   ' Werkstückinformationen
Global Const SPF_DHCode = ";CP_DHCode"  ' code for drillers
Global Const SPF_TSpeed = ";CP_TSpeed"  ' setting for tool speed
Global Const SPF_TCLift = ";CP_Lift"  ' Vorlegehub steuern
Global Const SPF_TCCHKRPM = ";CP_CHKRPM"  ' Drehzahlüberwachung
Global Const SPF_AGGCheck = ";CP_RELEASE"  ' Agg ok vorgelegt läuft etc.
Global Const SPF_REQUEST_FLEX = ";CP_SETAPTANGLE"  ' Anforderung die Achsen vom Flex 5 zu stellen


' ------------------------------------------------------------------------------------
Function MT_SetTHopsBasicToolExt(T As THopsBasicToolExt,BoxNo,HeadID)
Dim dummy As Object
	
	Set T.T = TDATA.GetTool_ID(BoxNo)	
	' Neu MW 30.3.2004
	Set dummy = TDATA.MachineData
	Set T.MachineData = dummy
	
	Set dummy = T.T
	' overwrite the HeadId with the programmed Headid
	T.Hid = HeadID
	Set T.H = TDATA.GetProcessHead_ID(HeadID)
	Set T.DH = TDATA.GetDrillingHead_ID(HeadID)
	Set T.HA = TDATA.GetHead_ID(HeadID)	
    Set T.T_S = Nothing' ObjectType = 1  Hauptspindel Werkzeugwechsler
    Set T.T_DH = Nothing' ObjectType = 2   Bohrkopf
    Set T.T_PH = Nothing' ObjectType = 3   Nebenaggregat
    Set T.T_GB = Nothing' ObjectType = 4   Winkelgetriebe
    Set T.T_SGB = Nothing' Special Gearbox like 3,5 Drillers in Row ' ObjectType = 5 
    Set T.T_TCA_GB = Nothing' Toolchanger access Gearbox ' ObjectType = 6 
    Set T.T_DHSaw = Nothing' Groove Saw on DrillingHead ' ObjectType = 7

	' Neu Test MW 9.2.2005
	Set T.tc = dummy.GetOn_TC
	
	
	If Not T.T.ObjectType=htokDrillingHeadTool Then	
		' alle Werkzeuge ausser Bohrkopf haben Cuttingedge
		' Neu MW 7.4.2005
		' Schneide
		Set T.T_CEdge = dummy.CuttingEdge
	End If
	
	If T.T.ObjectType=htokStandardTool Then	
		' Es handelt sich um ein IHopsStandardTool (1)
		Set T.T_S = dummy
		
		
		If T.h Is Nothing Then
			AddMistake(GetErrMsg(150,"_ungültige Aggregatnummer ?!",1))
			Exit All
		End If
		If T.T_S Is Nothing Then
			AddMistake(GetErrMsg(10,"_Schwerwiegender Fehler - Werkzeug ",1)+T.T.Description +" - "+GetErrMsg(11,"_ist derzeit nicht gerüstet! Agg:",0)+T.aggname)
			Exit All
		End If
		
		If T.T_S.GetOn_TC Is Nothing Then
			AddMistake(GetErrMsg(10,"_Schwerwiegender Fehler - Werkzeug ",1)+T.T_S.Description +" - "+GetErrMsg(11,"_ist derzeit nicht gerüstet! Agg:",0)+T.aggname)
			Exit All
		End If
		
		T.AggName = T.T_S.Description+" ; "+ T.T_S.GetOn_TC.Description + " #"+inttos(T.T_S.GetOn_TC.HeadID)		
		
		' Zusatzinfos aus Hauptspindel setzen
		Set_PH_Additions(T,T.h.Additions)
		Set_H_Additions(T,T.ha.Additions)

	ElseIf T.T.ObjectType=htokDrillingHeadTool Then	
		' Es handelt sich um ein IHopsDrillingHeadTool (2)
		Set T.T_DH = dummy
		T.AggName = T.T_DH.Description + " #"+inttos(T.T_DH.DrillingHead.HeadID)
		'Set T.T_S = dummy
		Set_DH_Additions(T,T.Dh.Additions)
		Set_H_Additions(T,T.ha.Additions)
	ElseIf T.T.ObjectType=htokProcessHeadTool Then	
		' Es handelt sich um ein IHopsProcessHeadTool (3)
		Set T.T_PH = dummy
		
		
		T.AggName = T.T_PH.Description
		' --
		' -- Modified  MW 24.06.2008 08:28:05
		' --
		' Zusatzinfos aus Hauptspindel setzen
		Set_PH_Additions(T,T.h.Additions)
		Set_H_Additions(T,T.ha.Additions)
	ElseIf T.T.ObjectType=htokGearBoxTool Then	
		' Es handelt sich um ein IHopsGearBoxTool (4)
		Set T.T_GB = dummy
		Set T.gb = dummy.GearBox
		
		
		T.AggName = T.T_GB.Description
		' Zusatzinfos aus Hauptspindel setzen
		Set_PH_Additions(T,T.h.Additions)
		Set_H_Additions(T,T.ha.Additions)
	ElseIf T.T.ObjectType=htokSpecialGearBoxTool Then	
		' Es handelt sich um ein IHopsSpecialGearBoxTool (5)
		Set T.T_SGB = dummy
		Set T.gb = dummy.GearBox  ' Neu MW 16.11.2005
		
		T.AggName = T.T_SGB.Description
		
	ElseIf T.T.ObjectType=htokTC_AccessGearBoxTool Then	
		' Es handelt sich um ein Special IHopsTC_AccessGearBoxTool (6)
		Set T.T_TCA_GB = dummy
		Set T.T_GB = dummy
		Set T.gb = dummy.GearBox
		
		T.AggName = T.T_TCA_GB.Description
	ElseIf T.T.ObjectType=htokDH_SawTool Then	
		' Es handelt sich um ein Groove Saw on DrillingHead ' ObjectType = (7)
		Set T.H = Nothing
		Set T.T_DHSaw = dummy
		T.AggName = T.T_DHSaw.Description
		T.hid = T.t_dhsaw.AggNo
	End If
End Function

Function Set_PH_Additions(T As THopsBasicToolExt, addi As IIAdditions)

Dim idummy As Long
Dim ddummy As Double
Dim sdummy As String
Dim vdummy As Variant
Dim isok As Boolean
Dim IDNotFound As String


        ' Fuer Hauptspindel - Werkzeuge
		IDNotFound=""

		If Not addi.GetAddition_ID(10000) Is Nothing Then
			T.PH_Add.ToolChangeMode = StrToFloat(addi.GetAddition_ID(10000).Value)
		Else
			IDNotFound=IDNotFound+"10000;"
		End If
		If Not T.h.Additions.GetAddition_ID(10001) Is Nothing Then
			If LTrim(RTrim((T.h.Additions.GetAddition_ID(10001).Value)))="1" Then
				T.PH_Add.Traori = True
			Else
				T.PH_Add.Traori = False
			End If
		Else
			IDNotFound=IDNotFound+"10001;"
		End If

		If Not addi.GetAddition_ID(10004) Is Nothing Then
			If LTrim(RTrim((addi.GetAddition_ID(10004).Value)))<>"" Then
					T.PH_Add.TraoriOn = LTrim(RTrim((addi.GetAddition_ID(10004).Value)))
			Else
				T.PH_Add.TraoriOn = "TRAORI"
			End If
		Else
			T.PH_Add.TraoriOn = "TRAORI"
		End If
		If Not addi.GetAddition_ID(10005) Is Nothing Then
			If LTrim(RTrim((addi.GetAddition_ID(10005).Value)))="" Then
				T.PH_Add.TraoriOff = "TRAFOOF"
			Else
				T.PH_Add.TraoriOff = LTrim(RTrim((addi.GetAddition_ID(10005).Value)))
			End If
		Else
			T.PH_Add.TraoriOff = "TRAFOOF"
		End If
		
		' Neu MW 06.03.2006
		idummy = MT_get_Add_ID(T,10070,isok) 
		If isok Then
			If equal(idummy,0) Then
				' von Wechselplatz übernehmen
				If Not T.T.GetOn_TC Is Nothing Then
					' Tool - on toolchanger
					T.PH_Add.ToolNo= T.t.GetPlaceID_OnTC
				Else
					' Tool - on ?????
					T.PH_Add.ToolNo = T.t.ToolNo
				End If
				
			Else
				T.PH_Add.ToolNo = idummy
			End If
		Else
			AddMistake(GetErrMsg(324597816,"_error missing ID:10070 MTManager",1))
		End If
		' Neu MW 06.03.2006
		idummy = MT_get_Add_ID(T,10071,isok) 
		If isok Then
			T.PH_Add.CorrNo = idummy
		Else
			AddMistake(GetErrMsg(32457660,"_error missing ID:10071 MTManager",1))
		End If

		' Typ 3-Achshaube 
		' 0=Keine oder statische Haube
		' 1=Stellbar Statisch Vorlegbar
		' 2=Auf wert vorlegbar
		' 3=Dynamisch auf Wert vorlegbar
		If Not addi.GetAddition_ID(10500) Is Nothing Then
			T.PH_Add.HaubeTyp3Achs = LTrim(RTrim((addi.GetAddition_ID(10500).Value)))         ' HaubeTyp3Achs  #10500
		Else
			IDNotFound=IDNotFound+"10500;"
		End If
		
		'Typ 5-Achshaube 
		' 0=Keine oder statische Haube
		' 1=Stellbar Statisch Vorlegbar
		' 2=Auf wert vorlegbar
		' 3=Dynamisch auf Wert vorlegbar
		If Not addi.GetAddition_ID(10501) Is Nothing Then
			T.PH_Add.HaubeTyp5Achs = LTrim(RTrim((addi.GetAddition_ID(10501).Value)))         ' HaubeTyp5Achs  #10501
		Else
			IDNotFound=IDNotFound+"10501;"
		End If
	
		'Maximal erlaubter Werkzeugradius 3-Achshaube
		If Not addi.GetAddition_ID(10502) Is Nothing Then
			T.PH_Add.HaubeMaxToolRad3Achs = LTrim(RTrim((addi.GetAddition_ID(10502).Value)))         ' HaubeMaxToolRad5Achs  #10502
		Else
			IDNotFound=IDNotFound+"10502;"
		End If
		
		'Maximal erlaubter Werkzeugradius 5-Achshaube
		If Not addi.GetAddition_ID(10503) Is Nothing Then
			T.PH_Add.HaubeMaxToolRad5Achs = LTrim(RTrim((addi.GetAddition_ID(10503).Value)))         ' HaubeMaxToolRad5Achs  #10503
		Else
			IDNotFound=IDNotFound+"10503;"
		End If
		
		'C_AchsPos für das vorlegen der 3A-Achs_Haube
		If Not addi.GetAddition_ID(10504) Is Nothing Then
			T.PH_Add.Haube3AchsCPos = LTrim(RTrim((addi.GetAddition_ID(10504).Value)))         ' HaubeMaxToolRad5Achs  #10503
		Else
			IDNotFound=IDNotFound+"10504;"
		End If
	
		If Not addi.GetAddition_ID(10505) Is Nothing Then
			T.PH_Add.HaubeTypDH = LTrim(RTrim((addi.GetAddition_ID(10505).Value)))         			' HaubeMaxToolRad5Achs  #10503
		Else
			IDNotFound=IDNotFound+"10505;"
		End If	
	
		If Trim(IDNotFound)<>"" Then
			AddMistake("Missing ProzessDeadID's: "+IDNotFound)
		End If
		
		If Not addi.GetAddition_ID(10600) Is Nothing Then
			T.PH_Add.ToolChangeType = LTrim(RTrim((addi.GetAddition_ID(10600).Value)))         			' HaubeMaxToolRad5Achs  #10503
		Else
			IDNotFound=IDNotFound+"10600;"
		End If	

		If Trim(IDNotFound)<>"" Then
			AddMistake("Missing ProzessDeadID's: "+IDNotFound)
		End If
		
		If Not addi.GetAddition_ID(10601) Is Nothing Then
			T.PH_Add.ToolCheckForDrillhead = LTrim(RTrim((addi.GetAddition_ID(10601).Value)))         			' HaubeMaxToolRad5Achs  #10503
		Else
			IDNotFound=IDNotFound+"10601;"
		End If	
	
		If Not addi.GetAddition_ID(10602) Is Nothing Then
			T.PH_Add.SpindleOff= LTrim(RTrim((addi.GetAddition_ID(10602).Value)))         						' Spindel Aus
		Else
			IDNotFound=IDNotFound+"10602;"
		End If
	
		If Trim(IDNotFound)<>"" Then
			AddMistake("Missing ProzessDeadID's: "+IDNotFound)
		End If
End Function
Function Set_H_Additions(T As THopsBasicToolExt, addi As IIAdditions)
	
Dim idummy As Long
Dim ddummy As Double
Dim sdummy As String
Dim vdummy As Variant
Dim isok As Boolean
Dim IDNotFound As String
Dim i,j As Integer 
        ' Fuer Hauptspindel - Werkzeuge
		IDNotFound=""

		If Not addi.GetAddition_ID(10000) Is Nothing Then
			T.H_Add.ToolChangeMode = StrToFloat(addi.GetAddition_ID(10000).Value)
		Else
			IDNotFound=IDNotFound+"10000;"
		End If
		If Not addi.GetAddition_ID(10001) Is Nothing Then
			If LTrim(RTrim((addi.GetAddition_ID(10001).Value)))="1" Then
				T.H_Add.Traori = True
			Else
				T.H_Add.Traori = False
			End If
		Else
			IDNotFound=IDNotFound+"10001;"
		End If

		If Not addi.GetAddition_ID(10004) Is Nothing Then
			If LTrim(RTrim((addi.GetAddition_ID(10004).Value)))<>"" Then
				T.H_Add.TraoriOn = LTrim(RTrim((addi.GetAddition_ID(10004).Value)))
			Else
				T.H_Add.TraoriOn = "TRAORI"
			End If
		Else
			T.H_Add.TraoriOn = "TRAORI"
		End If
		If Not addi.GetAddition_ID(10005) Is Nothing Then
			If LTrim(RTrim((addi.GetAddition_ID(10005).Value)))="" Then
				T.H_Add.TraoriOff = "TRAFOOF"
			Else
				T.H_Add.TraoriOff = LTrim(RTrim((addi.GetAddition_ID(10005).Value)))
			End If
		Else
			T.H_Add.TraoriOff = "TRAFOOF"
		End If
		
		' Neu MW 06.03.2006
		idummy = MT_get_Add_ID(T,10070,isok) 
		If isok Then
			If equal(idummy,0) Then
				' von Wechselplatz übernehmen
				If Not T.T.GetOn_TC Is Nothing Then
					' Tool - on toolchanger
					T.H_Add.ToolNo= T.t.GetPlaceID_OnTC
				Else
					' Tool - on ?????
					T.H_Add.ToolNo = T.t.ToolNo
				End If
				
			Else
				T.H_Add.ToolNo = idummy
			End If
		Else
			AddMistake(GetErrMsg(324597816,"_error missing ID:10070 MTManager",1))
		End If
		' Neu MW 06.03.2006
		idummy = MT_get_Add_ID(T,10071,isok) 
		If isok Then
			T.H_Add.CorrNo = idummy
		Else
			AddMistake(GetErrMsg(32457660,"_error missing ID:10071 MTManager",1))
		End If
		
		idummy = MT_get_Add_ID(T,10301,isok) 'D1 bis D4 erlaubt
		If isok Then
			If idummy<5 And idummy>0 Then
				T.H_Add.MCorrNo = idummy
			Else
				T.H_Add.MCorrNo=-99999
			End If
		Else
			T.H_Add.MCorrNo=-99999
			'AddMistake(GetErrMsg(32457660,"_error missing ID:10301 MTManager",1))
		End If

		If Not addi.GetAddition_ID(10302) Is Nothing Then
			ddummy=StrToFloat(addi.GetAddition_ID(10302).Value)
			T.H_Add.MLTolCorr = CDbl(ddummy)
		Else
			T.H_Add.MLTolCorr=0
			'AddMistake(GetErrMsg(32457660,"_error missing ID:10301 MTManager",1))
		End If
		
		If Not addi.GetAddition_ID(10303) Is Nothing Then
			ddummy=StrToFloat(addi.GetAddition_ID(10303).Value)
			T.H_Add.MRTolCorr = CDbl(ddummy)
		Else
			T.H_Add.MRTolCorr=0
			'AddMistake(GetErrMsg(32457660,"_error missing ID:10301 MTManager",1))
		End If
		
		' Typ 3-Achshaube 
		' 0=Keine oder statische Haube
		' 1=Stellbar Statisch Vorlegbar
		' 2=Auf wert vorlegbar
		' 3=Dynamisch auf Wert vorlegbar
		If Not addi.GetAddition_ID(10500) Is Nothing Then
			T.H_Add.HaubeTyp3Achs = LTrim(RTrim((addi.GetAddition_ID(10500).Value)))         ' HaubeTyp3Achs  #10500
		Else
			IDNotFound=IDNotFound+"10500;"
		End If
		
		'Typ 5-Achshaube 
		' 0=Keine oder statische Haube
		' 1=Stellbar Statisch Vorlegbar
		' 2=Auf wert vorlegbar
		' 3=Dynamisch auf Wert vorlegbar
		If Not addi.GetAddition_ID(10501) Is Nothing Then
			T.H_Add.HaubeTyp5Achs = LTrim(RTrim((addi.GetAddition_ID(10501).Value)))         ' HaubeTyp5Achs  #10501
		Else
			IDNotFound=IDNotFound+"10501;"
		End If
	
		'Maximal erlaubter Werkzeugradius 3-Achshaube
		If Not addi.GetAddition_ID(10502) Is Nothing Then
			T.H_Add.HaubeMaxToolRad3Achs = LTrim(RTrim((addi.GetAddition_ID(10502).Value)))         ' HaubeMaxToolRad5Achs  #10502
		Else
			IDNotFound=IDNotFound+"10502;"
		End If
		
		'Maximal erlaubter Werkzeugradius 5-Achshaube
		If Not addi.GetAddition_ID(10503) Is Nothing Then
			T.H_Add.HaubeMaxToolRad5Achs = LTrim(RTrim((addi.GetAddition_ID(10503).Value)))         ' HaubeMaxToolRad5Achs  #10503
		Else
			IDNotFound=IDNotFound+"10503;"
		End If
		
		'C_AchsPos für das vorlegen der 3A-Achs_Haube
		If Not addi.GetAddition_ID(10504) Is Nothing Then
			T.H_Add.Haube3AchsCPos = LTrim(RTrim((addi.GetAddition_ID(10504).Value)))         ' HaubeMaxToolRad5Achs  #10503
		Else
			IDNotFound=IDNotFound+"10504;"
		End If
	
		If Not addi.GetAddition_ID(10505) Is Nothing Then
			T.H_Add.HaubeTypDH = LTrim(RTrim((addi.GetAddition_ID(10505).Value)))         			' HaubeMaxToolRad5Achs  #10503
		Else
			IDNotFound=IDNotFound+"10505;"
		End If	
	
		If Trim(IDNotFound)<>"" Then
			AddMistake("Missing ProzessDeadID's: "+IDNotFound)
		End If
		
		If Not addi.GetAddition_ID(10600) Is Nothing Then
			T.H_Add.ToolChangeType = LTrim(RTrim((addi.GetAddition_ID(10600).Value)))         			' HaubeMaxToolRad5Achs  #10503
		Else
			IDNotFound=IDNotFound+"10600;"
		End If	
	
		If Trim(IDNotFound)<>"" Then
			AddMistake("Missing ProzessDeadID's: "+IDNotFound)
		End If
		
		
		If Not addi.GetAddition_ID(10601) Is Nothing Then
			T.H_Add.ToolCheckForDrillhead = LTrim(RTrim((addi.GetAddition_ID(10601).Value)))         			' HaubeMaxToolRad5Achs  #10503
		Else
			IDNotFound=IDNotFound+"10601;"
		End If	
	
		If Not addi.GetAddition_ID(10602) Is Nothing Then
			T.H_Add.SpindleOff= LTrim(RTrim((addi.GetAddition_ID(10602).Value)))         			' Spindel Aus
		Else
			IDNotFound=IDNotFound+"10602;"
		End If	
		
		If Trim(IDNotFound)<>"" Then
			AddMistake("Missing ProzessDeadID's: "+IDNotFound)
		End If
		
		'T.H_Add.	HK_ON(13) As TMachineKinematiks
		'HK_OFF(13) As TMachineKinematiks=
		MT_GetMachineKinematiks(2,addi)
		For i=0 To 12
			For j=0 To 2
				If Trim(HK_ON(i).P(j))<>"" Then 
					T.H_Add.HK_ON(i).P(j)=HK_ON(i).P(j)
				ElseIf Trim(MKG_ON(i).P(j))<>"" Then 
					T.H_Add.HK_ON(i).P(j)=MKG_ON(i).P(j)
				Else
					T.H_Add.HK_ON(i).P(j)=""
				End If
				If Trim(HK_OFF(i).P(j))<>"" Then 
					T.H_Add.HK_OFF(i).P(j)=HK_OFF(i).P(j)
				ElseIf Trim(MKG_OFF(i).P(j))<>"" Then 
					T.H_Add.HK_OFF(i).P(j)=MKG_OFF(i).P(j)
				Else
					T.H_Add.HK_OFF(i).P(j)=""
				End If
			Next j
		Next i
		'Set T.H_Add.HK_OFF=HK_OFF
		isok=isok
End Function
Function Set_DH_Additions(T As THopsBasicToolExt, addi As IIAdditions)
	
Dim idummy As Long
Dim ddummy As Double
Dim sdummy As String
Dim vdummy As Variant
Dim isok As Boolean
Dim IDNotFound As String
			' Typ 3-Achshaube 
		' 0=Keine oder statische Haube
		' 1=Stellbar Statisch Vorlegbar
		' 2=Auf wert vorlegbar
		' 3=Dynamisch auf Wert vorlegbar
		If Not addi.GetAddition_ID(10500) Is Nothing Then
			T.DH_Add.HaubeTyp3Achs = LTrim(RTrim((addi.GetAddition_ID(10500).Value)))         ' HaubeTyp3Achs  #10500
		Else
			IDNotFound=IDNotFound+"10500;"
		End If
		
		'Typ 5-Achshaube 
		' 0=Keine oder statische Haube
		' 1=Stellbar Statisch Vorlegbar
		' 2=Auf wert vorlegbar
		' 3=Dynamisch auf Wert vorlegbar
		If Not addi.GetAddition_ID(10501) Is Nothing Then
			T.DH_Add.HaubeTyp5Achs = LTrim(RTrim((addi.GetAddition_ID(10501).Value)))         ' HaubeTyp5Achs  #10501
		Else
			IDNotFound=IDNotFound+"10501;"
		End If
	
		'Maximal erlaubter Werkzeugradius 3-Achshaube
		If Not addi.GetAddition_ID(10502) Is Nothing Then
			T.DH_Add.HaubeMaxToolRad3Achs = LTrim(RTrim((addi.GetAddition_ID(10502).Value)))         ' HaubeMaxToolRad5Achs  #10502
		Else
			IDNotFound=IDNotFound+"10502;"
		End If
		
		'Maximal erlaubter Werkzeugradius 5-Achshaube
		If Not addi.GetAddition_ID(10503) Is Nothing Then
			T.DH_Add.HaubeMaxToolRad5Achs = LTrim(RTrim((addi.GetAddition_ID(10503).Value)))         ' HaubeMaxToolRad5Achs  #10503
		Else
			IDNotFound=IDNotFound+"10503;"
		End If
		
		'C_AchsPos für das vorlegen der 3A-Achs_Haube
		If Not addi.GetAddition_ID(10504) Is Nothing Then
			T.DH_Add.Haube3AchsCPos = LTrim(RTrim((addi.GetAddition_ID(10504).Value)))         ' HaubeMaxToolRad5Achs  #10503
		Else
			IDNotFound=IDNotFound+"10504;"
		End If
	
		If Not addi.GetAddition_ID(10601) Is Nothing Then
			T.DH_Add.ToolCheckForDrillhead = LTrim(RTrim((addi.GetAddition_ID(10601).Value)))         			' HaubeMaxToolRad5Achs  #10503
		Else
			IDNotFound=IDNotFound+"10601;"
		End If	
	
		If Trim(IDNotFound)<>"" Then
			AddMistake("Missing ProzessDeadID's: "+IDNotFound)
		End If
End Function
