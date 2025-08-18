' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \TCALC_HH7\TCALC_MT.BAS
' -- 
' -----------------------------------------
'#uses "TCalc_Global.bas"

Option Explicit

Global Type THopsBasicToolExt
	MachineData As IToolMachineData            ' Maschinendaten wie z.B. die Referenzspindel für Verfahrbereich
	T As IIHopsBasicTool
	H As IIProcessHead
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
    LiftMode As Integer 						' Modus 0 = Spindel ohne Vorlegemechanismus, 
    											' Modus 1 = bevorzugte Arbeitssttellung oben "BAO" 
     											' Modus 2 = bevorzugte Arbeitsstellung unten "BAU"
    T_CEdge As IICuttingEdge
    ' Neu MW 12.04.2005
    ' eingeführt für Plausibiltätsprüfung Bohrkopf
    T_Driller As tDriller                       ' wird von vertical-drillinghead stroke gesetzt
    'T_Dh_TP As IIDH_ToolPlace
    'TTool As IITool                             ' neu MW 13.04.2005 für Flex5 um dessen Subtoolchanger zu ermitteln
'    PH_Add As t_PH_Additions                   ' Zusatzinformationen von Bearbeitungskopf
    TC_Place As Long                            ' Werkzeugwechselplatz 
End Type



' -- Datatypes for tool handling
'actual tool
Global ActT As THopsBasicToolExt

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
    Set T.T_S = Nothing' ObjectType = 1  Hauptspindel Werkzeugwechsler
    Set T.T_DH = Nothing' ObjectType = 2   Bohrkopf
    Set T.T_PH = Nothing' ObjectType = 3   Nebenaggregat
    Set T.T_GB = Nothing' ObjectType = 4   Winkelgetriebe
    Set T.T_SGB = Nothing' Special Gearbox like 3,5 Drillers in Row ' ObjectType = 5 
    Set T.T_TCA_GB = Nothing' Toolchanger access Gearbox ' ObjectType = 6 
    Set T.T_DHSaw = Nothing' Groove Saw on DrillingHead ' ObjectType = 7

	' Neu Test MW 9.2.2005
	Set T.tc = dummy.GetOn_TC
	
	' Neu MW 1.4.2005
	' Lift-Mode ermitteln
	'T.LiftMode = MT_GET_LIFT_MODE(T)
	
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
		'Set_PH_Additions(T,T.h.Additions)
		

	ElseIf T.T.ObjectType=htokDrillingHeadTool Then	
		' Es handelt sich um ein IHopsDrillingHeadTool (2)
		Set T.T_DH = dummy
		T.AggName = T.T_DH.Description + " #"+inttos(T.T_DH.DrillingHead.HeadID)		
	ElseIf T.T.ObjectType=htokProcessHeadTool Then	
		' Es handelt sich um ein IHopsProcessHeadTool (3)
		Set T.T_PH = dummy
		
		
		T.AggName = T.T_PH.Description
	ElseIf T.T.ObjectType=htokGearBoxTool Then	
		' Es handelt sich um ein IHopsGearBoxTool (4)
		Set T.T_GB = dummy
		Set T.gb = dummy.GearBox
		
		
		T.AggName = T.T_GB.Description
		' Zusatzinfos aus Hauptspindel setzen
		'Set_PH_Additions(T,T.h.Additions)
		
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


Function MT_Get_RangeXYZ(ActT As THopsBasicToolExt,MinX,MaxX,MinY,MaxY,MinZ,MaxZ As Double)
Dim Ref_Agg As Double
Dim Ref_PH As Object ' IIHead    ' Referenzhead
Dim dummy As Object
Dim Fehler As Integer
Dim rminx,rmaxx,rminy,rmaxy,rminz,rmaxz As Double

Const C_RMINX=-5000, C_RMAXX=8000, C_RMINY=-5000, C_RMAXY=8000, C_RMINZ=-200, C_RMAXZ=800


	Fehler = 0

	Ref_Agg = ActT.MachineData.ReferenceHead
	
	If Not ActT.h Is Nothing Then
		' Standard - processhead
		Set dummy = ActT.h  'TDATA.GetHead_ID(Ref_Agg)
		rminx= dummy.RangeMinX
		rmaxx= dummy.RangeMaxX
		rminy= dummy.RangeMinY
		rmaxy= dummy.RangeMaxY
		rminz= dummy.RangeMinZ
		rmaxz= dummy.RangeMaxZ
		
	ElseIf MT_IsDH(ActT) Then
		' drillinghead 
		Set dummy = ActT.t_dh.DrillingHead  'TDATA.GetDrillingHead_ID(Ref_Agg)
		rminx= dummy.RangeMinX
		rmaxx= dummy.RangeMaxX
		rminy= dummy.RangeMinY
		rmaxy= dummy.RangeMaxY
		rminz= dummy.RangeMinZ
		rmaxz= dummy.RangeMaxZ
	ElseIf MT_isDHSaw(ActT) Then
		' DrillingHeadSaw
		Set dummy = ActT.T_DHSaw.DrillingHead  'TDATA.GetDrillingHead_ID(Ref_Agg)
		rminx= dummy.RangeMinX
		rmaxx= dummy.RangeMaxX
		rminy= dummy.RangeMinY
		rmaxy= dummy.RangeMaxY
		rminz= dummy.RangeMinZ
		rmaxz= dummy.RangeMaxZ
	Else 	
		Set dummy = Nothing
	End If
	If Not dummy Is Nothing Then
		' -- 1. X - Bereich
		If equal(rminx-rmaxx,0) Then
			' Bereich über Ref-Spindel ermitteln
			'If Not ActT.h Is Nothing Then
			'	' Standard - processhead
				Set Ref_PH = TDATA.GetHead_ID(Ref_Agg)
			'Else
			'	Set Ref_PH = TDATA.GetDrillingHead_ID(Ref_Agg)
			'End If
			
			If Not Ref_PH Is Nothing Then 
				' Range X von Referenzkopf
				
				'Set Ref_PH = dummy
				MinX = Ref_PH.RangeMinX
				MaxX = Ref_PH.RangeMaxX
				
				' Versatz der Spindel mit einrechnen
				MinX = MinX + dummy.CenterX
				MaxX = MaxX + dummy.CenterX
			Else
				Fehler=1
			End If
			
		Else
			' X- Range- Werte vom Head selbst übernehmen
			MinX = rminx
			MaxX = rmaxx
		
		End If
		' -- 2. Y - Bereich
		If equal(rminy-rmaxy,0) Then
			' Bereich über Ref-Spindel ermitteln
			'If Not ActT.h Is Nothing Then
			'	' Standard - processhead
				Set Ref_PH = TDATA.GetHead_ID(Ref_Agg)
			'Else
			'	Set Ref_PH = TDATA.GetDrillingHead_ID(Ref_Agg)
			'End If
			
			If Not Ref_PH Is Nothing Then 
				' Range Y von Referenzkopf
				MinY = Ref_PH.RangeMinY
				MaxY = Ref_PH.RangeMaxY
				
				' Versatz der Spindel mit einrechnen
				MinY = MinY + dummy.CenterY
				MaxY = MaxY + dummy.CenterY
				
			Else
				Fehler=1
			End If
			
		Else
			' Y- Range- Werte vom Head selbst übernehmen
			MinY = rminy
			MaxY = rmaxy
		
		End If
		' -- 3. Z - Bereich
		If equal(rminz-rmaxz,0) Then
			' Bereich über Ref-Spindel ermitteln
			'If Not ActT.h Is Nothing Then
			'	' Standard - processhead
				Set Ref_PH = TDATA.GetHead_ID(Ref_Agg)
			'Else
			'	Set Ref_PH = TDATA.GetDrillingHead_ID(Ref_Agg)
			'End If
			
			If Not Ref_PH Is Nothing Then 
				' Range Z von Referenzkopf
				MinZ = Ref_PH.RangeMinZ
				MaxZ = Ref_PH.RangeMaxZ
				
				' Versatz der Spindel mit einrechnen
				MinZ = MinZ + dummy.CenterZ
				MaxZ = MaxZ + dummy.CenterZ

			Else
				Fehler=1
			End If
			
		Else
			' Z- Range- Werte vom Head selbst übernehmen
			MinZ = rminz
			MaxZ = rmaxz
		
		End If
	Else
		Fehler=1
	End If
	
	If Fehler=1 Then	
		AddMistake(GetErrMsg(160,"_Fehler bei Ermittlung Min MaxRange X/Y/Z !",1))
		AddMistake(GetErrMsg(161,"_Parameter Ref-Spindel ",1)+ftos(Ref_Agg)+" ?")
	Else
		AddHint("Range-Ermittlung für Aggregat" + dummy.Description)
		AddHint("Minx: "+ftos(MinX)+" Maxx: "+ftos(MaxX)+" MinY: "+ftos(MinY)+" MaxY: "+ftos(MaxY)+" Minz: "+ftos(MinZ)+" MaxZ: "+ftos(MaxZ))
	End If
	
	If MinX<C_RMINX Then   '=-5000
		MinX=C_RMINX
	End If
	If MaxX>C_RMAXX Then   '=8000
		MaxX=C_RMAXX
	End If
	If MinY<C_RMINY Then   '=-5000
		MinY=C_RMINY
	End If
	If MaxY>C_RMAXY Then   '=8000
		MaxY=C_RMAXY
	End If
	If MinZ<C_RMINZ  Then   '=-200
		MinZ=C_RMINZ
	End If
	If MaxZ>C_RMAXZ Then   '=800
		MaxZ=C_RMAXZ
	End If
	
	
End Function

' *****************************************************************************************
' ** Handelt es sich um ein Bohrkopf - Tool
' *****************************************************************************************
Function MT_IsDH(T As THopsBasicToolExt)
	If Not T.t_dh Is Nothing Then
		MT_IsDH = (T.t.ObjectType=2)
	End If

End Function

Function MT_Is_TC_T(T As tHopsBasicToolExt)
	MT_Is_TC_T = False
	If Not T.t.GetOn_TC Is Nothing Then
		MT_Is_TC_T= True
	End If
End Function

	' Neu MW 27.04.2005
Function MT_SetDrillingHeadData(tools,dh As tDH,Driller As tDriller)
Dim Dh_TP As IIDH_ToolPlace
Dim itp As Variant
Dim FirstTNr As Long

	
	FirstTNr = Val(Get_First_Token(tools))
	
	Set itp= ActT.t_dh.DrillingHead.ToolPlaces.GetToolPlace_PlaceID(FirstTNr)
	Set Dh_TP=itp

	dh.tname = ActT.t.Description
	dh.CenterX = ActT.t.MoveX	
	dh.CenterY = ActT.t.MoveY
	dh.CenterZ = ActT.t.MoveZ	
	If ProcessPara.I_Feedrate = ActT.t_dh.MoveInFeedrate Then
		' vorschub des Bohrkopfs
		dh.VE=ActT.t.MoveInFeedrate
	Else
		' programmierter Vorschub
	    dh.ve=ProcessPara.I_Feedrate
	End If
	If ProcessPara.Feedrate = ActT.t_dh.Feedrate Then
		' vorschub des Bohrkopfs
		dh.V=ActT.t.Feedrate
	Else
		' programmierter Vorschub
	    dh.v=ProcessPara.Feedrate
	End If
	If ProcessPara.S_Feedrate = ActT.t_dh.MoveOutFeedrate Then
		' vorschub des Bohrkopfs
		dh.VA=ActT.t.MoveOutFeedrate
	Else
		' programmierter Vorschub
	    dh.va=ProcessPara.S_Feedrate
	End If
	
	
	
	' Bohrdaten füllen in Type TBohrer
	Set Driller.Edge = ActT.t_dh.DrillingHead.ToolPlaces.GetCuttingEdgeActiveTool_PlaceID(FirstTNr, 0)
	Set Driller.TP = Dh_TP
	Driller.TName = Driller.TP.ActiveTool.Name
	Driller.E_Len = Driller.Edge.ExcessLength
	Driller.Length = Driller.Edge.Length
	Driller.Length = Driller.TP.ActiveTool.MaxLength

	Driller.OffX = Driller.tp.OffsetX           ' MT_Get_BasicToolPlace_OffsetX(actt.t,tools)  ' gets offset x of the first driller in row
	Driller.OffY = Driller.tp.OffsetY           ' MT_Get_BasicToolPlace_OffsetY(actt.t,tools)  ' gets offset y of the first driller in row
	Driller.OffZ = Driller.tp.OffsetZ           ' MT_Get_BasicToolPlace_OffsetZ(actt.t,tools)  ' gets offset z of the first driller in row
	Driller.V = Driller.Edge.Feedrate        ' Vorschub
	Driller.VE = Driller.Edge.MoveInFeedrate        ' EintauchVorschub
	Driller.VA = Driller.Edge.MoveOutFeedrate        ' AustauchVorschub
	Driller.TNo = Driller.tp.ToolNo               ' TNummer des Bohrers auf der Steuerung
												  '  ' referiert auf die T-Korrketur auf der Steuerung fortlaufend vom 1. Bohrer beginnend

End Function

Function MT_GetMinMaxFeedrate(ActT As THopsBasicToolExt,ByRef Minf,ByRef MaxF)
	Minf = ActT.t.MinFeedrate
	MaxF = ActT.t.MaxFeedrate
End Function


Function MT_CheckFeedrate(ActT As THopsBasicToolExt, x,y,z,lastx,lasty,lastz,Feedrate) As Double
Dim inf,outf As Boolean  ' eintauch/Austauchvorgang
Dim MaxFeedrate,MinFeedrate As Double  ' min-max Vorschub
Dim result As Double     ' Rückgabewert

	result=Feedrate
	inf=False
	outf = False
	MT_GetMinMaxFeedrate(ActT,MinFeedrate,MaxFeedrate)
	
	If (z<lastz) Then
		' eintauchvorgang
	   inf = True
	End If
	If (z>lastz) Then
		' austauchvorgang
	   outf = True
	End If
	
	If (inf Or outf) And (Not equal(x,lastx) Or Not equal(y,lasty)) Then
		' fliegendes Ein bzw. Austauchen
		' dann beschränken auf Min bzw. Max Vorsch
	Else
		' auf der Stelle runter 
		' oder auf der Stelle hoch
	
	End If
	' 20.4.2005
	' erstmal generell beschränken
	If (Feedrate > MaxFeedrate) And (MaxFeedrate>0.01) Then
		result=MaxFeedrate
	Else
		If (Feedrate< MinFeedrate) And (MinFeedrate>0.01) Then
			result=MinFeedrate
		End If
	End If
	MT_CheckFeedrate = result
	
End Function


' *****************************************************************************************
' ** Winkelgetriebe
' *****************************************************************************************
Function MT_IsGearBoxTool(T As THopsBasicToolExt)
	
	' wenn True dann ist es ein Winkelgetriebe
	MT_IsGearBoxTool = (T.t.ObjectType=htokGearBoxTool)

End Function

' *****************************************************************************************
' ** Winkelgetriebe Spezial Typ 5 Reihenbohrgetriebe
' ** MW 16.11.2005
' *****************************************************************************************
Function MT_IsGearBoxTool_Special(T As THopsBasicToolExt)
	
	MT_IsGearBoxTool_Special = (T.t.ObjectType=htokSpecialGearBoxTool)

End Function


' Säge auf Bohrkopf
Function MT_isDHSaw(T As tHopsBasicToolExt)
	MT_isDHSaw = False
	If Not T.T_DHSaw Is Nothing Then
		MT_isDHSaw= ((T.t.ObjectType=7)) 
	End If
End Function
