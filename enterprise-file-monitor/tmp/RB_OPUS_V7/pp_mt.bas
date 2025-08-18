' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \RB_OH_OPUS_V7\pp_mt.bas
' -- 
' -----------------------------------------
' -- 
' -- Reichenbacher - ISG / BECKHOFF Postprocessors V7 (mw) --
' -- 
' -----------------------------------------
'#uses "pp_global.bas"
'#uses "pp_math.bas"

Option Explicit

Global Type THopsBasicToolExt
	MachineData As IToolMachineData            ' Maschinendaten wie z.B. die Referenzspindel fuer Verfahrbereich
	T As IIHopsBasicTool
	H As IIProcessHead
	DH As IIDrillingHead                       ' MW 18.03.2015
	gb As IIGearBox  ' neu mw 15.3.2005
    T_S As IIHopsStandardTool                  ' ObjectType = 1   Hauptspindel Werkzeugwechsler
    T_DH As IIHopsDrillingHeadTool             ' ObjectType = 2   Bohrkopf
    T_PH As IIHopsProcessHeadTool              ' ObjectType = 3   Nebenaggregat
    T_GB As IIHopsGearBoxTool                  ' ObjectType = 4   Winkelgetriebe
    T_SGB As IIHopsSpecialGearBoxTool          ' ObjectType = 5   Special Gearbox like 3,5 Drillers in Row ' 
    T_TCA_GB As IIHopsTC_AccessGearBoxTool ' ObjectType = 6   Toolchanger access Gearbox ' 
    T_DHSaw As IIHopsDH_SawTool                ' ObjectType = 7   Groove Saw on DrillingHead ' 
	HId As Integer                             ' Head ID / Agg No
    AggName As String                          ' Bezeichnet das Aggregat naeher
    TC As IIToolChangerHead
    T_CEdge As IICuttingEdge
    T_Driller As tDriller                       ' wird von vertical-drillinghead stroke gesetzt
    PreChanged As Boolean                        ' Merker, ob bereits vorgewechselt
    PH_Add As t_PH_Additions                   ' Zusatzinformationen von Bearbeitungskopf 
    											' Neu MW 03.04.2007 5Axis
    toolname As String                          ' eigentlicher Werkzeugname  MW 12.04.2007
'    SetOf_DustPositions As HeadCalc_SetOfDouble
'	SetOf_DustPositionsMFunc As NCData_SetOfString
End Type
' --
' -------------------------------------------------------

' -- Datatypes for tool handling
' MW 09.06.2015 1st of all tools
Global FirstT As THopsBasicToolExt

'actual tool
Global ActT As THopsBasicToolExt

'last tool
Global LastT As THopsBasicToolExt

'array of all tools
Global ToolArray() As THopsBasicToolExt

' ------------------------------------------------------------------------------------
Function MT_SetTHopsBasicToolExt(T As THopsBasicToolExt,BoxNo,HeadID)
Dim dummy As Object
	
	Set T.T = TDATA.GetTool_ID(BoxNo)	
	' Neu MW 30.3.2004
	Set dummy = TDATA.MachineData
	Set T.MachineData = dummy
	
	Set dummy = T.T
	' overwrite the HeadId with the programmed Headid
	T.HId = HeadID
	Set T.H = TDATA.GetProcessHead_ID(HeadID)
	
    Set T.T_S = Nothing' ObjectType = 1  Hauptspindel Werkzeugwechsler
    Set T.T_DH = Nothing' ObjectType = 2   Bohrkopf
    Set T.T_PH = Nothing' ObjectType = 3   Nebenaggregat
    Set T.T_GB = Nothing' ObjectType = 4   Winkelgetriebe
    Set T.T_SGB = Nothing' Special Gearbox like 3,5 Drillers in Row ' ObjectType = 5 
    Set T.T_TCA_GB = Nothing' Toolchanger access Gearbox ' ObjectType = 6 
    Set T.T_DHSaw = Nothing' Groove Saw on DrillingHead ' ObjectType = 7
    
    Set T.dh = Nothing  '	IIDrillingHead             
	Set T.gb = Nothing  '   IIGearBox  
    Set T.TC = Nothing ' IIToolChangerHead
    Set T.T_CEdge = Nothing  ' IICuttingEdge
    
    
	Set T.tc = dummy.GetOn_TC
	
	If Not T.T.ObjectType=htokDrillingHeadTool Then	
		' alle Werkzeuge ausser Bohrkopf haben Cuttingedge
		' Schneide
		Set T.T_CEdge = dummy.CuttingEdge

	End If
	
	If T.T.ObjectType=htokStandardTool Then	
		' Es handelt sich um ein IHopsStandardTool (1)
		Set T.T_S = dummy
		
		
		If T.h Is Nothing Then
			pp_err(320)
		End If
		If T.T_S Is Nothing Then
			pp_err(0,"t.t_s = nothing")
		End If
		
		If T.T_S.GetOn_TC Is Nothing Then
			pp_err(0,"tool not on toolchanger")
		End If
		
		T.AggName = T.T_S.Description+" ; "+ T.T_S.GetOn_TC.Description + " #"+inttos(T.T_S.GetOn_TC.HeadID)		
		T.ToolName = T.t_s.Tool.Name   
		
		' Zusatzinfos aus Hauptspindel setzen
		Set_PH_Additions(T,T.h.Additions)
		
		
	ElseIf T.T.ObjectType=htokDrillingHeadTool Then	
		' Es handelt sich um ein IHopsDrillingHeadTool (2)
		Set T.T_DH = dummy
		Set T.dH = TDATA.GetDrillingHead_ID(HeadID)
		
		T.AggName = T.T_DH.Description + " #"+inttos(T.T_DH.DrillingHead.HeadID)		
	ElseIf T.T.ObjectType=htokProcessHeadTool Then	
		' Es handelt sich um ein IHopsProcessHeadTool (3)
		Set T.T_PH = dummy
		Set T.T_S = dummy
		T.ToolName = T.t_s.Tool.Name   
		
		T.AggName = T.T_PH.Description
		' Zusatzinfos aus Hauptspindel setzen
		Set_PH_Additions(T,T.h.Additions)
		
	ElseIf (T.T.ObjectType=htokGearBoxTool) Or (T.t.ObjectType=htokGearboxOnHeadTool) Then
		' Es handelt sich um ein IHopsGearBoxTool (4) 
		Set T.T_GB = dummy
		Set T.gb = dummy.GearBox
		
		T.AggName = T.T_GB.Description
		
		' Zusatzinfos aus Hauptspindel setzen
		Set_PH_Additions(T,T.h.Additions)
		
		
	ElseIf (T.T.ObjectType=htokSpecialGearBoxTool) Then	
		' Es handelt sich um ein IHopsSpecialGearBoxTool (5)
		Set T.T_SGB = dummy
		Set T.gb = dummy.GearBox  ' Neu MW 16.11.2005
		T.AggName = T.T_SGB.Description
		
		' Zusatzinfos aus Hauptspindel setzen
		Set_PH_Additions(T,T.h.Additions)
		

	ElseIf T.T.ObjectType=htokTC_AccessGearBoxTool Then	
		' Es handelt sich um ein Special IHopsTC_AccessGearBoxTool (6)
		Set T.T_TCA_GB = dummy
		Set T.T_GB = dummy
		Set T.gb = dummy.GearBox
		
		T.AggName = T.T_TCA_GB.Description
		' Zusatzinfos aus Hauptspindel setzen
		Set_PH_Additions(T,T.h.Additions)
	ElseIf T.T.ObjectType=htokDH_SawTool Then	
		' Es handelt sich um ein Groove Saw on DrillingHead ' ObjectType = (7)
		Set T.H = Nothing
		Set T.T_DHSaw = dummy
		T.AggName = T.T_DHSaw.Description
		T.HId = T.t_dhsaw.AggNo
	End If
End Function

Function MT_get_Add_ID_Head(ActT As THopsBasicToolExt,id,isok As Boolean)
Dim addi As IIAddition
'Dim hid As Integer 
	isok = False
	If ActT.t.ObjectType=htokStandardTool Then
		Set addi = ActT.h.Additions.GetAddition_ID(id)
		'hid = ActT.h.HeadID
	ElseIf ActT.t.ObjectType=htokDrillingHeadTool Then
		Set addi = ActT.t_dh.DrillingHead.Additions.GetAddition_ID(id)
		'hid = ActT.dh.HeadID
		
	ElseIf ActT.t.ObjectType=htokGearBoxTool Then
		' -- 
		' --  MW 19.03.2009 13:48:32
		' --  V1.0.5.76x
		' --
		Set addi = ActT.h.Additions.GetAddition_ID(id)
		'hid = ActT.h.HeadID
		
	ElseIf ActT.t.ObjectType=htokSpecialGearBoxTool Then
		' -- 
		' --  Reihenbohrgetriebe auf asymmetrischer 5-Achs - Spindel
		' --
		Set addi = ActT.h.Additions.GetAddition_ID(id)
		'hid = ActT.h.HeadID
		
	ElseIf ActT.t.ObjectType=htokProcessHeadTool Then
		Set addi = ActT.h.Additions.GetAddition_ID(id)
		'hid = ActT.h.HeadID
		
	ElseIf ActT.t.ObjectType=htokGearboxOnHeadTool Then
		' -- 
		' --  TP - PosMode
		If (id = 102002) Or (id=102000) Then
			' Multifunktionseinheit 
			Set addi = ActT.h.Additions.GetAddition_ID(id)
			
		End If
		'hid = ActT.h.HeadID
	Else
		' momentan nur fuer Hauptspindel und Bohrkopf, Winkegetriebe und Processhead(fixe nutsaege)
		'AddMistake("93847432456")
	End If
	
	If Not addi Is Nothing Then
		isok = True
		'AddHintList("MTManager PH["+inttos(hid)+"] Addition ID["+inttos(id)+"] ="+addi.Value)   ' MW 19.11.2012

		MT_get_Add_ID_Head=addi.Value
	Else
		'AddMistake("ZusatzInfo ID+"+inttos(id)+" - fuer Werkzeug "+ActT.t.Description+ ".. nicht gefunden")
	End If
End Function


Function Set_PH_Additions(T As THopsBasicToolExt, addi As IIAdditions)

Dim idummy As Long
Dim ddummy As Double
Dim sdummy As String
Dim vdummy As Variant
Dim isok As Boolean
Dim id As Integer
Dim SStr As String
'Dim	HoodThreshold_Base As Double       ' MW 29.05.2017 * Basismass der Haube ID '10095


		
		If MT_Is_S_Tool(T) Or mt_isgb(T) Then
			' Offset Werkzeugbezugspunkt zu Nullpunktsbezug Z
			ddummy = MT_get_Add_ID_HeadExt(T,-20001,isok)
			If isok Then
				T.PH_Add.RotPointOffZ = MT_get_Add_ID_HeadExt(T,-20001,isok)
			Else
				T.PH_Add.RotPointOffZ = 0
			End If
			
			If Not addi.GetAddition_ID(20001) Is Nothing Then
				T.PH_Add.HaubeDown(1)= LTrim(RTrim((addi.GetAddition_ID(20001).Value))) 
			End If
			
			If Not addi.GetAddition_ID(20002) Is Nothing Then
				T.PH_Add.HaubeDown(2)= LTrim(RTrim((addi.GetAddition_ID(20002).Value)))
			End If
			
			If Not addi.GetAddition_ID(20003) Is Nothing Then
				T.PH_Add.HaubeDown(3)= LTrim(RTrim((addi.GetAddition_ID(20003).Value)))
			End If
			
			
		End If


'		If Not T.h Is Nothing Then
'			' * Basismass der Haube ID '10095
'			If Not T.H.ToolPlaces.GetToolPlace_Index(0).Additions.GetAddition_ID(10095) Is Nothing Then
'				HoodThreshold_Base = Val(T.H.ToolPlaces.GetToolPlace_Index(0).Additions.GetAddition_ID(10095).Value)
'			Else
'				HoodThreshold_Base = 0
'			End If
'			
'			
'			' Frei definierbare Haubenpositionen einlesen fuer dyn. Haubensteuerung
'				
'			Set T.SetOf_DustPositions = CreateObject("NC_Data.HeadCalc_SetOfDouble")	
'			Set T.SetOf_DustPositionsMFunc = CreateObject("NC_Data.NCData_SetOfString")	
'			
'			T.SetOf_DustPositions.Clear
'			T.SetOf_DustPositionsMFunc.Clear
'			
'			If Not T.H.ToolPlaces.GetToolPlace_Index(0) Is Nothing Then
'				' immer von Ausgang 1 
'				For id = 10100 To 10119 
'					' immer von Ausgang 1 
'					'If MT_GET_HEAD_POSDUST(T)=0 Then
'					'	'wcnccom("exhaust disabled - aggregat ")
'					'	Exit Function
'					'End If
'					If Not T.H.ToolPlaces.GetToolPlace_Index(0).Additions.GetAddition_ID(id) Is Nothing Then
'						SStr = T.H.ToolPlaces.GetToolPlace_Index(0).Additions.GetAddition_ID(id).Value
'						If (Len(SStr)>0) And IsNumeric(SStr) Then
'							T.SetOf_DustPositions.Add(StrToFloat(SStr)+HoodThreshold_Base)
'							T.SetOf_DustPositionsMFunc.Add(SUB_HOOD+" @P1="+inttos(SStr))   '  160+id-10100))
'						End If
'					End If
'					
'				Next id 
'			Else
'				pp_err(1,"Processhead - no ToolPlace found")
'			End If
'			
'		End If

End Function


Function MT_get_Add_ID_HeadExt(ActT As THopsBasicToolExt,id,isok As Boolean)
Dim addi As IIAddition
Dim SimuAdditions As IIAdditions

	isok = False

	If ActT.t.ObjectType=htokDrillingHeadTool Then
		
	Else
		Set SimuAdditions  = NCData.GetExtInfo(ekHead_SimuAdditions,ActT.h)
		Set addi = SimuAdditions.GetAddition_ID(id)
		If Not addi Is Nothing Then
			isok = True
			MT_get_Add_ID_HeadExt=addi.Value
		End If
	End If
	
	Set addi = Nothing
	Set SimuAdditions = Nothing
	
End Function

