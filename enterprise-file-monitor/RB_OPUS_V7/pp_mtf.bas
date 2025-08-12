' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \RB_OH_OPUS_V7\pp_mtf.bas
' -- 
' -----------------------------------------
' -- 
' -- Reichenbacher - ISG / BECKHOFF Postprocessors V7 (mw) --
' -- 
' -----------------------------------------
'#uses "pp_global.bas"
'#uses "pp_7.bas"
'#uses "pp_math.bas"
'#uses "pp_mt.bas"


Option Explicit

' -----------------------------------------
' -- Tool - Types : Actt. (T_S/T_DH etc.)
' -- [1] T_S As IIHopsStandardTool                  ' ObjectType = htokStandardTool   Hauptspindel Werkzeugwechsler
' -- [2] T_DH As IIHopsDrillingHeadTool             ' ObjectType = htokDrillingHeadTool   Bohrkopf
' -- [3] T_PH As IIHopsProcessHeadTool              ' ObjectType = htokProcessHeadTool   Nebenaggregat
' -- [4] T_GB As IIHopsGearBoxTool                  ' ObjectType = htokGearBoxTool   Winkelgetriebe
' -- [5] T_SGB As IIHopsSpecialGearBoxTool          ' ObjectType = htokSpecialGearBoxTool   Special Gearbox like 3,5 Drillers in Row ' 
' -- [6] T_TCA_GB As IIHopsTC_AccessGearBoxTool     ' ObjectType = htokTC_AccessGearBoxTool   Toolchanger access Gearbox ' 
' -- [7] T_DHSaw As IIHopsDH_SawTool                ' ObjectType = htokDH_SawTool   Groove Saw on DrillingHead ' 
' -----------------------------------------



Function MT_AddHint(typ,stri)
Dim message As String

	message = "Func. MT..-"
	If typ = 1 Then
		message= message+ "schwerwiegender Fehler "+stri
	ElseIf typ=99 Then
		' Sondertyp 
		message= message+stri
	Else
		message= message+stri
	
	End If
	AddHint(message)

	
End Function




' *****************************************************************************************
' ** Check ob Id in BoxnoArray
' *****************************************************************************************
Function MT_CheckisIdInList(ID,BoxNoArray) As Boolean
Dim sBox As Long
Dim i As Long
Dim result As Boolean
	result = False
	
	For i = 0 To UBound(BoxNoArray)-1
		sBox = BoxNoArray(i)
		If ID = sBox Then
		   result=True
		   Exit For
		End If
	Next i
	MT_CheckisIdInList = result
End Function





' *****************************************************************************************
' ** Werkzeugwechsel - Speed Abhandlung
' *****************************************************************************************

Function MT_Write_Speed(t As THopsBasicToolExt,pspeed,Optional Gear_Ratio )   ' MW 13.01.2015 CP -> POS pneum.schwenk.Saege

Dim HId As Long   ' Aggregate Head id 

Dim dr As Long   ' Spindle - Direction
Dim dz As Long   ' Tool - Speed (programmed speed)

Dim Speed_Trans_complete As Double     ' Getriebeuebersetzungsverhaeltnis
Dim Speed_Trans_MU As Double  ' ueBersetzung Hauptspindel
Dim Speed_Trans_GB As Double  ' uebersetzung Winkelgetriebeausgang
Dim Speed_trans_DH As Double  ' uebersetzung Bohrkopf - wird hierher uebergeben
Dim Speed_trans_PH As Double  ' uebersetzung Bohrkopf - wird hierher uebergeben

	Speed_Trans_complete = 0
	Speed_Trans_MU = 0
	Speed_Trans_GB = 0
	Speed_trans_DH = 0
	Speed_trans_PH = 0

	Marker.LastSpeed = pspeed


    If IsMissing(Gear_Ratio) Then
    	Gear_Ratio = 1
    End If
    
	HId = t.Hid '  
	
	
	dz = inttos(MT_Get_SpindleSpeed(ActT,pspeed))
	dr = IIf(dz<0,4,3)
	
	If Not t.T.GetOn_TC Is Nothing Then
		' Tool - on toolchanger
		If Not t.h Is Nothing Then
			If t.h.ToolPlaces.Count = 1 Then
				' -- mehr wie einen Ausgang gibt derzeit nicht
				Speed_Trans_MU = t.h.ToolPlaces.GetToolPlace_Index(0).GearRate
				Speed_Trans_GB = 1 ' falls nicht Winkelgetriebe
			Else
				pp_err(0,"Gear ratio - more than one main unit output")
			End If
			If Not t.t_gb Is Nothing Then
				' -- dann Werkzeug auf Winkegetriebeausgang
				Speed_Trans_GB = t.t_gb.GB_ToolPlace.GearRate
			End If
		End If
		Speed_Trans_complete = Speed_Trans_MU*Speed_Trans_GB
		
		
	ElseIf MT_IsDH(t) Then
		' Drilling Head
		' Tx Dx ueberschreiben mit korrekter Einstellung	
		dz = inttos(MT_Get_SpindleSpeed(ActT,pspeed))
		
		' --  uebersetzungsverhaeltnis DH
		Speed_trans_DH = Gear_Ratio
		
		Speed_Trans_complete = Speed_trans_DH
		
	ElseIf MT_isDHSaw(t) Then
		' Nutsaege auf Drilling Head
		If t.t_dhsaw.RotDirection = rdLeft Then
		   dr=3
		ElseIf t.t_dhsaw.RotDirection = rdRight Then
			dr=4
		ElseIf t.t_dhsaw.RotDirection = rdLeftRight Then
		End If
		' Neu MW 09.08.2005  auch programmierte Drehzahl nehmen
		dz = inttos(MT_Get_SpindleSpeed(ActT,pspeed))
		' --  uebersetzungsverhaeltnis DH
		If Not t.t_dhsaw Is Nothing Then
			Speed_trans_DH = t.t_dhsaw.DH_ToolPlace.GearRate
		End If
		Speed_Trans_complete = Speed_trans_DH
		
	End If
	
	CC(SUB_SPINDEL_ONOFF,IntToS(Hid),IntToS(dr),IntToS(Abs(dz)))
	

End Function



' *****************************************************************************************
' ** Ermittlung Spindle - Ausgangsdrehzahl ueber uebersetzung etc.
' ** zusaetzlich ueberpruefung Min - Max - Speed findet in Plausi statt
' *****************************************************************************************
Function MT_Get_SpindleSpeed(t As tHopsBasicToolExt,pspeed)
Dim OutPut_Spindle As Double
Dim Max_ToolSpeed, Min_ToolSpeed As Double    ' vom Werkzeug selbst
Dim Max_HeadSpeed, Min_HeadSpeed As Double	  ' vom Bearbeitungskopf
Dim Speed As Double 
	Speed = pspeed

	MT_GetMinMaxToolSpeed(t,Min_ToolSpeed,Max_ToolSpeed)
	' 1. Werkzeugdrehgeschwindigkeit checken im Bezug auf Schneide 
	If Abs(Speed) > Max_ToolSpeed Then
	   Speed = Max_ToolSpeed
	End If
	If Abs(Speed) < Min_ToolSpeed Then
	   Speed = Min_ToolSpeed
	End If
	


	' kommt evtl. auch negativ zurueck 
    OutPut_Spindle=T.t.GetRotSpeed(Speed)    ' 	gets transmission ratio - direction 
    
    

    ' jetzt die eigentliche Drehrichtung vom Werkzeug beruecksichtigen
    ' neu MW 09.6.2005
    ' neu MW 15.07.2005  - Drehrichtung wird von GetRotSpeed bereits beruecksichtigt!
    'If t.t.RotDirection=rdLeft Then
	'	OutPut_Spindle = - OutPut_Spindle
    ' End If
    
	' ----------------------------------------------
	' Fuer alle Werkzeug auf Hauptspindel muss jetzt der Ausgang gecheckt werden,
	' da TMDATA - GetRotSpeed ja nicht weiss auf welcher Spindel das Werkzeug sitzt
	If (Not MT_IsDH(t)) And (Not MT_isDHSaw(t)) Then
	    If Not t.h Is Nothing Then
	    	If Not t.h.ToolPlaces Is Nothing Then
	    		If Not t.h.ToolPlaces.GetToolPlace_Index(0) Is Nothing Then
			    	If t.h.ToolPlaces.GetToolPlace_Index(0).ReverseRotDirection = True Then
						OutPut_Spindle = - OutPut_Spindle
					End If
					If Not equal(t.h.ToolPlaces.GetToolPlace_Index(0).GearRate,0) Then
				    	OutPut_Spindle = OutPut_Spindle / t.h.ToolPlaces.GetToolPlace_Index(0).GearRate 
				    End If
				End If
			End If
	    End If
	
	End If
    'If T.T.ObjectType=htokStandardTool Then	
    If MT_Is_TC_T(t) Then	
    	' -- check Spindeldrehzahl fuer alle Werkzeuge auf einer Wechselspindel
    	
    	' 2. Werkzeugdrehgeschwindigkeit checken im Bezug auf Spindeldefinition!
		MT_GetMinMaxHeadSpeed(t,Min_HeadSpeed,Max_HeadSpeed)
    	If Abs(OutPut_Spindle) > Max_HeadSpeed Then
    	   OutPut_Spindle = IIf(OutPut_Spindle<0,-Max_HeadSpeed,Max_HeadSpeed)
    	End If
    	If Abs(OutPut_Spindle) < Min_HeadSpeed Then
    	   OutPut_Spindle = IIf(OutPut_Spindle<0,-Min_HeadSpeed,Min_HeadSpeed)
    	End If
    End If
    If MT_isDHSaw(t) Then	
    	' -- check Spindeldrehzahl fuer Saege auf Bohrkopf
    	
    	' 2. Werkzeugdrehgeschwindigkeit checken im Bezug auf Spindeldefinition!
		MT_GetMinMaxHeadSpeed(t,Min_HeadSpeed,Max_HeadSpeed)
    	If Abs(OutPut_Spindle) > Max_HeadSpeed Then
    	   OutPut_Spindle = IIf(OutPut_Spindle<0,-Max_HeadSpeed,Max_HeadSpeed)
    	End If
    	If Abs(OutPut_Spindle) < Min_HeadSpeed Then
    	   OutPut_Spindle = IIf(OutPut_Spindle<0,-Min_HeadSpeed,Min_HeadSpeed)
    	End If
    End If

    MT_Get_SpindleSpeed=(OutPut_Spindle)
End Function


Function MT_GetMinMaxToolSpeed(t As tHopsBasicToolExt,Min_ToolSpeed,Max_ToolSpeed)

	If t.t.ObjectType=htokDrillingHeadTool Then
		Min_ToolSpeed = t.t.SpindleMinRotSpeed	
		Max_ToolSpeed = t.t.SpindleMaxRotSpeed	
	ElseIf t.T.ObjectType=htokDH_SawTool Then	
		' Es handelt sich um ein Groove Saw on DrillingHead ' ObjectType = 7
		Min_ToolSpeed = t.t.MinRotSpeed	
		Max_ToolSpeed = t.t.MaxRotSpeed	
		
	Else
		Min_ToolSpeed = t.t.MinRotSpeed	
		Max_ToolSpeed = t.t.MaxRotSpeed	
	
	End If
End Function


Function MT_GetMinMaxHeadSpeed(t As tHopsBasicToolExt,Min_HeadSpeed,Max_HeadSpeed)

	If t.t.ObjectType=htokDrillingHeadTool Then
		Min_HeadSpeed = t.t_dh.SpindleMinRotSpeed	
		Max_HeadSpeed = t.t_Dh.SpindleMaxRotSpeed	
	ElseIf t.T.ObjectType=htokDH_SawTool Then	
		' Es handelt sich um ein Groove Saw on DrillingHead ' ObjectType = 7
		Min_HeadSpeed = t.T_DHSaw.SpindleMinRotSpeed	
		Max_HeadSpeed = t.T_DHSaw.SpindleMaxRotSpeed	
		
	Else
		Min_HeadSpeed = t.h.MinRotSpeed	
		Max_HeadSpeed = t.h.MaxRotSpeed	
	
	End If
End Function



' Saege auf Bohrkopf
Function MT_isDHSaw(t As tHopsBasicToolExt)
	MT_isDHSaw = False
	If Not t.T_DHSaw Is Nothing Then
		MT_isDHSaw= ((t.t.ObjectType=7)) 
	End If
End Function


Function MT_Is_TC_T(t As tHopsBasicToolExt)
	MT_Is_TC_T = False
	If Not t.t Is Nothing Then
		If Not t.t.GetOn_TC Is Nothing Then
			MT_Is_TC_T= True
		End If
	End If
End Function



' -------------------------------------------------------------------------
' ueberpruefungsroutine, ob vorheriges Tool und aktuelles Tool vom Bohrkopf
' Saege auf Bohrkopf !!!!
' -------------------------------------------------------------------------

Function MT_isDH_wasDH(act As THopsBasicToolExt ,last As THopsBasicToolExt)
Dim result As Boolean
	result = False
	If (MT_IsDH(last) And MT_isDHSaw(act)) Or (MT_IsDH(act) And MT_isDHSaw(last)) _
 		Or (MT_isDHSaw(act) And MT_isDHSaw(last)) Then
 		result = True
 	End If
	MT_isDH_wasDH = result
	
End Function


' -------------------------------------------------------------------------
' ueberpruefungsroutine, ob Tool ein Saegeblatt ist
' -------------------------------------------------------------------------
Function MT_isSaw(T As tHopsBasicToolExt) As Boolean

	MT_isSaw = False
	If Not T.T_GB Is Nothing Then
		' Winkelgetriebe
		' -- 
		' --  MW 02.08.2007 11:28:09
		' --
		' -- Abfragen auf nothing von .tool !!!!
		If Not T.T_GB.Tool Is Nothing Then
			MT_isSaw= (T.t_gb.Tool.ToolType = tSaw)
		End If
	ElseIf Not T.t_ph Is Nothing Then
		' Nebenaggregat
		' processheadTool
		If Not T.t_ph.Tool Is Nothing Then	
			MT_isSaw= (T.t_ph.Tool.ToolType = tSaw)
		End If
	ElseIf Not T.t_dhsaw Is Nothing Then
		' MW 23.04.2015 - Bohrkopfsaege ist auch Saege
		If Not T.T_DHSaw.Tool Is Nothing Then
			MT_isSaw = (T.T_DHSaw.Tool.ToolType = tSaw) 
		End If

	ElseIf Not T.t Is Nothing Then
		' iihopsbasictool
		' Saege auf 5-Achs ?
		If MT_Is_S_Tool(T) Then
			If Not T.t.Tool Is Nothing Then
				MT_isSaw= (T.t.Tool.ToolType = tSaw)
			End If
		End If
			
	End If
End Function



Function MxxT_IsSpecialToolKind_Laser(Tool As IIHopsBasicTool)

	MxxT_IsSpecialToolKind_Laser=False
	
	If Tool.ObjectType=5 Then
		' IhopsSpecialTool
		MxxT_IsSpecialToolKind_Laser = True
	End If
End Function

' *****************************************************************************************
' ** Befindet sich Werkzeug auf einer Drehachse welche um Z dreht
' *****************************************************************************************
Function MT_Is_Vertical_Rot_Axis(T As THopsBasicToolExt)

Dim rot As Variant
Dim tip As Variant
	
	MT_Is_Vertical_Rot_Axis = False
	
	
	If Not T.H Is Nothing Then
		'test =TH.Description
		rot = T.H.RotType
		tip = T.H.TipType
		
		' If (rot = atFree) And (tip = atFix) Then
		' MW 11.12.2012 auch 5-Achs mit Winkelgetriebe
		If (rot = atFree) And ((tip = atFix) Or (tip = atFree))Then
		    ' Drehachse frei
			MT_Is_Vertical_Rot_Axis = True
		End If
		
	End If
		


End Function

' *****************************************************************************************
' ** Befindet sich Werkzeug auf einer Drehachse welche um Z dreht
' *****************************************************************************************
Function MT_Is_Vertical_Without_Rot_Axis(T As THopsBasicToolExt)

Dim rot As Variant
Dim tip As Variant
Dim dummy As Variant
Dim iitp As IIPH_ToolPlace

	
	MT_Is_Vertical_Without_Rot_Axis = False
	
	
	If Not T.H Is Nothing Then
		rot = T.H.RotType
		tip = T.H.TipType
		
		If (rot = atFix) And (tip = atFix) Then
		    ' keine drehbaren achsen
		    If Not T.h.ToolPlaces.GetToolPlace_PlaceID(1) Is Nothing Then
		    	' 1. Ausgang
		    	Set dummy = t.h.ToolPlaces.GetToolPlace_PlaceID(1)
		    	Set iitp = dummy
		    	If iitp.RotAngle=0 And iitp.TipAngle=0 Then	
		    		' jetzt sollte es doch eine Hauptspindel ohne dreh/kippachse sein
					MT_Is_Vertical_Without_Rot_Axis = True
		    	End If
		    End If
		    
		End If
		
	End If
		


End Function

' *****************************************************************************************
' ** Handelt es sich um Standardwerkzeug aus Wechsler 5-Achs 
' *****************************************************************************************
Function MT_Is_Vertical_StandardTool5Axis(T As THopsBasicToolExt)
Dim erg As Boolean
	erg = False
  If Not T.t Is Nothing Then
	If T.t.ObjectType=1 Then 
		If (T.h.TipType=atFree) And (T.h.RotType=atFree) Then
			erg = True
		End If
	End If
  End If
	MT_Is_Vertical_StandardTool5Axis = erg
End Function


' *****************************************************************************************
' ** Handelt es sich um Standardwerkzeug aus Wechsler 
' *****************************************************************************************
Function MT_Is_Vertical_StandardTool4Axis(T As THopsBasicToolExt)
Dim erg As Boolean
	erg = False
	If T.t.ObjectType=1 Then 
		If (T.h.TipType=atFix) And  ( (T.h.RotType=atFix) Or (T.h.RotType=atFree) ) Then
			erg = True
		End If
	End If
	MT_Is_Vertical_StandardTool4Axis = erg
End Function

' *****************************************************************************************
' ** Handelt es sich um ein Bohrkopf - Tool
' *****************************************************************************************
Function MT_IsDH(T As THopsBasicToolExt)
	MT_IsDH=False
	If Not T.t_dh Is Nothing Then
		MT_IsDH = (T.t.ObjectType=htokDrillingHeadTool)
	End If
End Function


' *****************************************************************************************
' ** jegliche Art von Winkelgetriebe
' *****************************************************************************************
Function MT_IsGB(T As THopsBasicToolExt)
	
	' wenn True dann ist es ein Winkelgetriebe 
	'MT_IsGB = (T.t.ObjectType=htokGearBoxTool) Or (T.t.ObjectType=htokSpecialGearBoxTool) Or (T.t.ObjectType=htokTC_AccessGearBoxTool) 
	' MW 20.01.2016
	MT_IsGB = (T.t.ObjectType=htokGearBoxTool) Or (T.t.ObjectType=htokSpecialGearBoxTool) Or (T.t.ObjectType=htokTC_AccessGearBoxTool) Or (T.t.ObjectType=htokGearboxOnHeadTool) 

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
' *****************************************************************************************
Function MT_IsGearBoxTool_Special(T As THopsBasicToolExt)
	
	MT_IsGearBoxTool_Special = (T.t.ObjectType=htokSpecialGearBoxTool)

End Function

Function MT_IsGearBoxTool_Special_Vertical(T As THopsBasicToolExt)
Dim result As Boolean
	result = False

	If MT_IsGearBoxTool_Special(T) Then
	   If T.T_SGB.GB_ToolPlace.TipAngle=0 Then
	   		result=True
	   End If
	End If
	MT_IsGearBoxTool_Special_Vertical = result
End Function

Function MT_IsGearBoxTool_Special_Horizontal(T As THopsBasicToolExt)
Dim result As Boolean
	result = False

	If MT_IsGearBoxTool_Special(T) Then
	   If T.T_SGB.GB_ToolPlace.TipAngle=90 Then
	   		result=True
	   End If
	End If
	MT_IsGearBoxTool_Special_Horizontal = result
End Function


Function MT_Is_UndersideTool(T As THopsBasicToolExt)
Dim result As Boolean
	result = False

	If MT_IsGearBoxTool(T) Then
		If equal(T.T_GB.GB_ToolPlace.TipAngle,180) Then
			' Unterflurgetriebe
			result = True
		End If
		If T.T_GB.GB_ToolPlace.TipType = aatFix Then
			' 
		End If
	End If
	MT_Is_UndersideTool = result
End Function




' *****************************************************************************************
' ** Gibt 1. benutztes Werkzeug auf dem Aggregat ("HID") als BoxNummer zurueck
' *****************************************************************************************

Function MT_Get_FirstUsedToolBoxNo(Hid)
Dim BoxNo As Long
Dim i As Long

	For i = 0 To UBound(ToolArray)  
		If Hid = ToolArray(i).HId Then
			' -- Werkzeug fuer Hid gefunden
			BoxNo = ToolArray(i).t.ID
			Exit For
		End If
	Next i
	
	MT_Get_FirstUsedToolBoxNo = BoxNo
	
End Function

Function MT_Is_Tool_Used_Before_From_Another_Head(FirstTool As THopsBasicToolExt)
Dim result As Boolean
Dim i As Long

	result = False
	
	For i = 0 To UBound(ToolArray)  
		If (FirstTool.HID = ToolArray(i).HId) And (FirstTool.t.ID = ToolArray(i).t.ID) Then
			' -- Werkzeug fuer Head gefunden
			Exit For
		Else
			' -- 
			' -- check ob das Werkzeug erst noch von einem anderen Head benutzt wird
			' -- 
			If (FirstTool.HID <> ToolArray(i).HId) And (FirstTool.T.ID = ToolArray(i).T.ID) Then
				' -- Werkzeug fuer anderen Head gefunden - also wird werkzeug
				' -- vorher von einem anderen Bearbeitungskopf benuetzt
				result = True
				Exit For
			End If
		End If
	Next i
	
	MT_Is_Tool_Used_Before_From_Another_Head = result
	
End Function


' -- gibt ID von 1. Wechselspindel zurueck
Function MT_GetFirst_TC_Hid
Dim IProHL As IIProcessHead

	If TDATA.GetProcessHeadList_TC.Count > 0 Then
		Set IProHL = TDATA.GetProcessHeadList_TC.GetProcessHead_Index(0)
		MT_GetFirst_TC_Hid=IProHL.HeadID
	Else
		pp_err(355)
	End If
	
End Function

' aufgerufen von Process_END
Function MT_Tool_Re_Change()
Dim isok As Boolean
Dim NT As THopsBasicToolExt
	If Not PPara.NTool Is Nothing Then
		MT_SetTHopsBasicToolExt(NT,PPara.NTool.ID,PPara.NHeadInfo)
			
	End If
	
	If Not (PPara.ActT.t Is Nothing) Then
	
		If MT_isDH_wasDH(PPara.ActT,NT) Then
			' kein Motor aus bei wechhsel von Bohrkopf Bohren auf Bohrkopf Sägen
			' und keine Motor aus bei wechsel von Bohrkopf Sägen auf Bohrkopf bohren 
			' und keine Motor aus bei wechsel von Bohrkopf Sägen auf Bohrkopf Sägen
		
		ElseIf MT_IsDH(PPara.ActT) Then 
				'DrillHeadMotorOff 
				wcnccom("",True)
				wcnccom("DH Off/up",True)
				CC(SUB_SPINDEL_ONOFF,IntToS(ppara.Hid),0,0)
				wcnccom("",True)
				'WCNC_IDD(SUB_OFFUP,PPara.ActT.HId)
		ElseIf MT_isDHSaw(PPara.ActT) Then
				' MW 02.05.2018
				wcnccom("",True)
				wcnccom("DHSAW Off/up",True)
				CC(SUB_SPINDEL_ONOFF,IntToS(ppara.Hid),0,0)
				wcnccom("",True)
				wcnccom("pins up",True)
				WCNC_WRITE_DHCode("",True)
		
				'DrillHeadMotorOff 
				wcnccom("DH Off/up",True)
				'WCNC_IDD(SUB_OFFUP,PPara.ActT.HId)
		
		ElseIf (MT_Is_TC_T(PPara.ActT)) Then
				' stoppt alle laufenden Spindeln
				wcnccom("",True)
				wcnccom("Motor #Off#Up",True)
				CC(SUB_SPINDEL_ONOFF,IntToS(ppara.Hid),0,0)
				wcnccom("",True)
				
				' MainMotorOff 
				'CC(SUB_OFFUP,PPara.ActT.HId)
		'ElseIf (MT_Is_MFE_Vertical(PPara.ActT)) Then
				' MW 04.09.2018 - Nebenaggregat Saege auch AUS
		'		wcnccom("Saw Motor #Off#Up",True)
		'		CC(SUB_OFFUP,PPara.ActT.HId)
		Else
			pp_err(3)
			'If Not MT_GB_Output_Changed(actt,T) Then
			'	' bei einem Aggregatsausgang - Wechsel wird Motor nicht abgeschaltet
			'
			'End If
		
			
		End If
	End If
End Function


' ----------------------------------------------------------------------------------------------------------------
' -- Aggregat -  OFFSETS 
' ----------------------------------------------------------------------------------------------------------------


' ----------------------------------------------------------------------------------------------------------------
' -- TOOLPLACE OFFSETS 
' ----------------------------------------------------------------------------------------------------------------


' --------------------------------------------------------
' -- ret = Toolplace offset in X,Y,Z depends on Objecttype
' --------------------------------------------------------
Function MT_Get_TP_Offset_XYZ(T As THopsBasicToolExt,X,Y,Z As Double) As Boolean
Dim ret As Boolean
	ret = True
	If T.t.ObjectType=1 Then
		' IProcessHead Toolchange  - spindle
		' - Attention - only 1 output possible
		If Not T.H.ToolPlaces.GetToolPlace_Index(0) Is Nothing Then
			
			If (equal(T.H.TipAngle,0)) And (equal(T.H.RotAngle,0)) And (T.H.TipType=atFix) And (T.H.RotType=atFix) Then
				' fix vertical Aggregat 
				
				ret = MT_Get_H_Offset_XYZ(T,X,Y,Z)
				
			ElseIf (equal(T.H.TipAngle,0)) And (equal(T.H.RotAngle,0)) And (T.H.TipType=atFix) And (T.H.RotType=atFree) Then
				' vertical Aggregat with free rotating Axis
				ret = MT_Get_H_Offset_XYZ(T,X,Y,Z)
				' ------------------------------------------------------------
				' calculate offsets of toolplace for gearbox
				' ------------------------------------------------------------
				T.H.ToolPlaces.GetToolPlace_Index(0).GetOffsetToolPlace(ActV.RotA, ActV.TipA, X, Y, Z)
				' ------------------------------------------------------------
			Else
				pp_err(356)
			End If
		Else 
			pp_err(356)
		End If
	
	ElseIf T.t.ObjectType=3 Then
		' IHopsProcessHeadTool
		If Not T.t_ph.PH_ToolPlace Is Nothing Then
			X = T.t_PH.PH_ToolPlace.OffsetX
			Y = T.t_PH.PH_ToolPlace.OffsetY
			Z = T.t_PH.PH_ToolPlace.OffsetZ
			
		Else 
			ret = False
		End If
		
	ElseIf T.t.ObjectType=4 Then
		' IHopsGearBoxTool
		ret = MT_Get_GB_Offset_XYZ(X,Y,Z)
	ElseIf T.t.ObjectType=5 Then
		' IHopsSpecialGearBoxTool
		ret = MT_Get_SGB_Offset_XYZ(X,Y,Z)
	ElseIf T.t.ObjectType=htokTC_AccessGearBoxTool Then
		' IHopsGearBoxTool
		ret = MT_Get_TCA_GB_Offset_XYZ(X,Y,Z)
		
	Else
		ret = False
	End If
	MT_Get_TP_Offset_XYZ = ret
	
End Function


' --------------------------------------------------------
' -- ret = Gesamtoffset Ausgang + offset Winkelgetriebe selbst
' --------------------------------------------------------
Function MT_Get_RotAxisOffset(T As THopsBasicToolExt) As Double
Dim OffC,GbOffC,PIN_OFFC As Double

  ' Neu MW 02.11.2005
  ' definierten PIN-Offset verwenden
  PIN_OFFC= T.h.PinOffset
   If MT_IsGearBoxTool_Special(T) Then
   		'OffC = T.T_TCA_GB.GearBox.OffsetC     ' winkelgetriebe Gesamtoffset
   		'GbOffC = T.T_TCA_GB.GB_ToolPlace.RotAngle   ' Ausgangsoffset
   		' geaendert MW 16.11.2005 
   		OffC = T.T_SGB.GearBox.OffsetC     ' winkelgetriebe Gesamtoffset
   		GbOffC = T.T_SGB.GB_ToolPlace.RotAngle   ' Ausgangsoffset
   		
   
   ElseIf MT_IsGearBoxTool(T) Then
   		OffC = T.T_GB.GearBox.OffsetC     ' winkelgetriebe Gesamtoffset
   		GbOffC = T.T_GB.GB_ToolPlace.RotAngle   ' Ausgangsoffset
   	ElseIf (MT_Is_Vertical_StandardTool5Axis(T)) Then
   		OffC = 0 ' winkelgetriebe Gesamtoffset
   		GbOffC = 0   ' Ausgangsoffset
		PIN_OFFC= 0
   		
   	Else 
   		pp_err(3)
   	End If
  'MT_Get_RotAxisOffset = -OffC + GbOffC+ 180  ' Anpassung an Nullstellung der Maschine
	
  'MT_Get_RotAxisOffset = -OffC - GbOffC+90 ' Anpassung an Nullstellung der Maschine (Nockenposition)
  ' Neu MW 02.11.2005
  ' definierten PIN-Offset verwenden
  MT_Get_RotAxisOffset = -OffC - GbOffC+PIN_OFFC ' Anpassung an Nullstellung der Maschine (Nockenposition)
End Function

' --------------------------------------------------------
' -- ret = Toolplace Rot Angle depends on Objecttype
' --------------------------------------------------------
Function MT_Get_TP_RotAngle(rot As Double) As Boolean
Dim ret As Boolean
	ret = True
	If ActT.t.ObjectType=1 Then
		' IProcessHead Toolchange  - spindle
		If Not ActT.h.GetToolPlace_Index(1) Is Nothing Then
			rot = ActT.H.ToolPlaces.GetToolPlace_Index(1).RotAngle
		Else 
			ret = False
		End If
		
	ElseIf ActT.t.ObjectType=3 Then
		' IHopsProcessHeadTool
		If Not ActT.t_PH.PH_ToolPlace Is Nothing Then
			rot = ActT.t_PH.PH_ToolPlace.RotAngle
		Else 
			ret = False
		End If
	ElseIf ActT.t.ObjectType=4 Then
		' IHopsGearBoxTool
		If Not ActT.t_gb.GB_ToolPlace Is Nothing Then
			rot = ActT.t_gb.GB_ToolPlace.RotAngle
		Else 
			ret = False
		End If
	ElseIf ActT.t.ObjectType=5 Then
		' IHopsSpecial GearBoxTool
		' MW 16.11.2005
		If Not ActT.t_sgb.GB_ToolPlace Is Nothing Then
			rot = ActT.t_sgb.GB_ToolPlace.RotAngle
		Else 
			ret = False
		End If
	ElseIf ActT.t.ObjectType=6 Then
		' IHopsTCAccess GearBoxTool
		If Not ActT.T_TCA_GB.GB_ToolPlace Is Nothing Then
			rot = ActT.T_TCA_GB.GB_ToolPlace.RotAngle
		Else 
			ret = False
		End If
		
	Else
		ret = False
	End If
	MT_Get_TP_RotAngle = ret
	
End Function

' --------------------------------------------------------
' -- ret = Toolplace Tip Angle depends on Objecttype
' --------------------------------------------------------
Function MT_Get_TP_TipAngle(Tip As Double) As Boolean
Dim ret As Boolean
	ret = True
	If ActT.t.ObjectType=1 Then
		' IProcessHead Toolchange  - spindle
		If Not ActT.h.GetToolPlace_Index(1) Is Nothing Then
			Tip = ActT.H.ToolPlaces.GetToolPlace_Index(1).TipAngle
		Else 
			ret = False
		End If
		
	ElseIf ActT.t.ObjectType=3 Then
		' IHopsProcessHeadTool
		If Not ActT.t_PH.PH_ToolPlace Is Nothing Then
			Tip = ActT.t_PH.PH_ToolPlace.TipAngle
		Else 
			ret = False
		End If
		
	ElseIf ActT.t.ObjectType=4 Then
		' IHopsGearBoxTool
		If Not ActT.t_gb.GB_ToolPlace Is Nothing Then
			Tip = ActT.t_gb.GB_ToolPlace.TipAngle
		Else 
			ret = False
		End If
	ElseIf ActT.t.ObjectType=5 Then
		' IHopsSpecialGearBoxTool
		' MW 16.11.2005
		If Not ActT.t_sgb.GB_ToolPlace Is Nothing Then
			Tip = ActT.t_sgb.GB_ToolPlace.TipAngle
		Else 
			ret = False
		End If
	ElseIf ActT.t.ObjectType=6 Then
		' IHopsTCAccess GearBoxTool
		If Not ActT.T_TCA_GB.GB_ToolPlace Is Nothing Then
			Tip = ActT.T_TCA_GB.GB_ToolPlace.TipAngle
		Else 
			ret = False
		End If
	Else
		ret = False
	End If
	MT_Get_TP_TipAngle = ret
	
End Function

' --------------------------------------------------------
' -- ret = Toolplace length depends on Objecttype
' --------------------------------------------------------
Function MT_Get_TP_Len(T As THopsBasicToolExt,length As Double) As Boolean
Dim ret As Boolean
	ret = True
	If T.t.ObjectType=1 Then
		' IProcessHead Toolchange  - spindle
		If Not T.h.ToolPlaces.GetToolPlace_Index(0) Is Nothing Then
			length = T.H.ToolPlaces.GetToolPlace_Index(0).Length
		Else 
			ret = False
		End If
		
	ElseIf T.t.ObjectType=3 Then
		' IHopsProcessHeadTool
		If Not T.t_PH.PH_ToolPlace Is Nothing Then
			length = T.t_PH.PH_ToolPlace.Length
		Else 
			ret = False
		End If
	ElseIf T.t.ObjectType=4 Then
		' IHopsGearBoxTool
		If Not T.t_gb.GB_ToolPlace Is Nothing Then
			length = T.t_gb.GB_ToolPlace.Length
		Else 
			ret = False
		End If
	ElseIf T.t.ObjectType=5 Then
		' Neu MW 16.11.2005
		' IHopsSpecial GearBoxTool
		If Not T.t_sgb.GB_ToolPlace Is Nothing Then
			length = T.t_sgb.GB_ToolPlace.Length
		Else 
			ret = False
		End If
	ElseIf T.t.ObjectType=6 Then
		' IHopsTCAccess_GearBoxTool
		If Not T.T_TCA_GB.GB_ToolPlace Is Nothing Then
			length = T.T_TCA_GB.GB_ToolPlace.Length
		Else 
			ret = False
		End If
		
	Else
		ret = False
	End If
	MT_Get_TP_Len = ret
	
End Function


' --------------------------------------------------------
' -- ret = Toolplace length depends on Objecttype
' --------------------------------------------------------
Function MT_Get_TCMode As Integer
Dim ret As Integer
	ret = -1
	If ActT.t.ObjectType=1 Then
		' IProcessHead Toolchange  - spindle
		ret = ActT.T_S.Tool.TC_Mode    ' + 1 ?, da Mode bei Index 0 beginnt!

	ElseIf ActT.t.ObjectType=4 Then
		' IHopsGearBoxTool
		ret = ActT.t_gb.GearBox.TC_Mode 
	ElseIf ActT.t.ObjectType=htokTC_AccessGearBoxTool Then
		ret = ActT.T_TCA_GB.GearBox.TC_Mode

	Else
		If Not ActT.T_S Is Nothing Then
			If Not ActT.T_S Is Nothing Then
				 'ret= ActT.t_gb.GearBox.TC_Mode 
				 ' Neu MW 16.04.2007
				 
				 ret = ActT.T_S.Tool.TC_Mode    ' + 1 ?, da Mode bei Index 0 beginnt!
			End If
		End If
	End If
	MT_Get_TCMode = ret
	
End Function

' ----------------------------------------------------------------------------------------------------------------
' -- Gearbox -  TOOLPLACE OFFSETS 
' ----------------------------------------------------------------------------------------------------------------


' --------------------------------------------------------
' -- ret = Gearbox Toolplace offset in X,Y,Z
' --------------------------------------------------------
Function MT_Get_GB_Offset_XYZ(X,Y,Z As Double) As Boolean
Dim ret As Boolean

	ret= True
	If Not ActT.t_gb.GB_ToolPlace Is Nothing Then
		X = ActT.t_gb.GB_ToolPlace.OffsetX
		Y = ActT.t_gb.GB_ToolPlace.OffsetY
		Z = ActT.t_gb.GB_ToolPlace.OffsetZ
		
	Else 
		ret = False
	End If
	MT_Get_GB_Offset_XYZ = ret
	
End Function

' --------------------------------------------------------
' -- ret = Special Gearbox Toolplace offset in X,Y,Z
' -- MW 16.11.2005
' --------------------------------------------------------
Function MT_Get_SGB_Offset_XYZ(X,Y,Z As Double) As Boolean
Dim ret As Boolean

	ret= True
	If Not ActT.t_sgb.GB_ToolPlace Is Nothing Then
		X = ActT.t_sgb.GB_ToolPlace.OffsetX
		Y = ActT.t_sgb.GB_ToolPlace.OffsetY
		Z = ActT.t_sgb.GB_ToolPlace.OffsetZ
		
	Else 
		ret = False
	End If
	MT_Get_SGB_Offset_XYZ = ret
	
End Function


' --------------------------------------------------------
' -- ret = Gearbox Flex 5 Toolplace offset in X,Y,Z
' --------------------------------------------------------
Function MT_Get_TCA_GB_Offset_XYZ(X,Y,Z As Double) As Boolean
Dim ret As Boolean

	ret= True
	If Not ActT.T_TCA_GB.GB_ToolPlace Is Nothing Then
		X = ActT.T_TCA_GB.GB_ToolPlace.OffsetX
		Y = ActT.T_TCA_GB.GB_ToolPlace.OffsetY
		Z = ActT.T_TCA_GB.GB_ToolPlace.OffsetZ
		
	Else 
		ret = False
	End If
	MT_Get_TCA_GB_Offset_XYZ = ret
	
End Function


' ----------------------------------------------------------------------------------------------------------------
' -- ProcessHead  -  TOOLPLACE OFFSETS 
' ----------------------------------------------------------------------------------------------------------------

' --------------------------------------------------------
' -- ret = Head Toolplace offset in X,Y,Z  
' --------------------------------------------------------
Function MT_Get_H_Offset_XYZ(T As THopsBasicToolExt,X,Y,Z As Double) As Boolean
Dim ret As Boolean


	ret= True
	If Not T.h.ToolPlaces.GetToolPlace_Index(0) Is Nothing Then
		
		X = T.H.ToolPlaces.GetToolPlace_Index(0).OffsetX
		Y = T.H.ToolPlaces.GetToolPlace_Index(0).OffsetY
		Z = T.H.ToolPlaces.GetToolPlace_Index(0).OffsetZ
		
	Else 
		ret = False
	End If
	MT_Get_H_Offset_XYZ = ret
	
End Function


' --------------------------------------------------------
' -- ret = Drilling Head Toolplace offset in X,Y,Z  
' --------------------------------------------------------
Function MT_Get_DH_Offset_XYZ(T As THopsBasicToolExt,Place As Long,X,Y,Z As Double) As Boolean
Dim ret As Boolean


	ret= True
	If Not T.T_Dh.ToolPlaces.GetToolPlace_Index(Place) Is Nothing Then
		
		X = T.T_Dh.ToolPlaces.GetToolPlace_Index(Place).OffsetX
		Y = T.T_Dh.ToolPlaces.GetToolPlace_Index(Place).OffsetY
		Z = T.T_Dh.ToolPlaces.GetToolPlace_Index(Place).OffsetZ
		
	Else 
		ret = False
	End If
	MT_Get_DH_Offset_XYZ = ret
	
End Function





' -----------------------------------------------
' -- Spindelcodierung ermitteln -> als DEZIMAL WERT
' -----------------------------------------------

Function MT_Get_SpindleCode_Dez(ByVal tools,bm) As Boolean
Dim Dh_TP As IIDH_ToolPlace
Dim itp As Variant
Dim TNr As Long
Dim dummy As String
Dim erg As Boolean

	dummy = tools
	erg = True

	TNr = Val(Get_First_Token(dummy))
	While TNr >0 
		If actt.t.ObjectType = 7 Then
			' Saege auf Bohrkopf
			Set itp= actt.t_dhsaw.DH_ToolPlace
		Else
			' Bohrer
			Set itp= actt.t_dh.DrillingHead.ToolPlaces.GetToolPlace_PlaceID(TNr)
		End If
		Set Dh_TP=itp
		
		If Dh_TP.SpindleNo<=(16+16) Then  'If Dh_TP.SpindleNo<=32 Then
		 	' Bitmuster 1 fuellen
			bm.BM1 = bm.BM1 + exponent2(Dh_TP.SpindleNo)
		ElseIf Dh_TP.SpindleNo<=(32+32) Then   'ElseIf Dh_TP.SpindleNo<=64 Then
		 	' Bitmuster 2 fuellen
			bm.BM2 = bm.BM2 + exponent2(Dh_TP.SpindleNo-16)
		ElseIf Dh_TP.SpindleNo<=(48+48) Then
		 	' Bitmuster 3 fuellen
			bm.BM3 = bm.BM3 + exponent2(Dh_TP.SpindleNo-32)
		Else
			pp_err(0,"wrong BitCode DH SpindleNo"+inttos(Dh_TP.SpindleNo))		
			erg = False
		End If
		
		If InStr(dummy,";")<=0 Then
		   Exit While
		End If
		
		dummy = Mid(dummy,InStr(dummy,";")+1,Len(dummy)-InStr(dummy,";"))
		TNr = Val(Get_First_Token(dummy))

	Wend
	MT_Get_SpindleCode_Dez = erg
	
	
	
End Function


' gibt die Winkelstellung zurueck, unter der die Saege die Stellung saw_angle erreichen kann
' Saege schwenkbar oder fix
Function MT_GetPneumaticSawAngle(T As THopsBasicToolExt,TipA,saw_angle) As Double
Dim raster_count As Long
Dim i As Long
Dim an As Double
Dim erg As Double
Dim Raster_Angle As Double 
	' Saegewinkel normieren 0-360
	While saw_angle >= 360 
		saw_angle = saw_angle-360 
	Wend
	While saw_angle < 0 
		saw_angle= saw_angle+360
	Wend
	erg = False
	If T.h.RotType=atRaster Then
		' Raster fuer Saegeschnitt ermitteln
		raster_count = T.h.RotPositions.Count
		For i = 0 To raster_count-1
			an = T.h.RotPositions.GetDouble(i)
			an = an - 90   ' anpassen an Nullstellung 
			an = Norm0_360(an)
			
			If equal(TipA,90) Then
				If (an = saw_angle) Or ( (an-180)=saw_angle ) Or ( (an+180)=saw_angle ) Then
					' -- MW 17.10.2007 09:38:30 - 
					' -- beruecksichtigt keinen Kippstellung
					' Stellung gefunden
					
					erg = True
					Raster_Angle = Norm0_360(an + 90)
					Exit For
				End If
			Else
				' --
				' -- Modified  MW 17.10.2007 09:40:02
				' --
				' -- gekippte (45°) Saege beruecksichtigen 
				' -- es gibt nur eine Stellung
				If (an = saw_angle) Then
					' -- MW 17.10.2007 09:38:30 - 
					' -- beruecksichtigt keinen Kippstellung
					' Stellung gefunden
					
					erg = True
					Raster_Angle = Norm0_360(an + 90)
					Exit For
				End If
				 
			End If
		Next
	ElseIf T.h.RotType=atFix Then
		' Fixe Saege nicht schwenkbar - Stellung ermitteln
		an = T.h.RotAngle
		If (saw_angle=an) Then
			' Stellung gefunden ok
			erg = True
			Raster_Angle = an
		End If
		
	End If
	If erg=False Then
		pp_err(159)
	Else
		MT_GetPneumaticSawAngle = Raster_Angle
	End If
End Function


Function MT_GB_Output_Changed(ActT As THopsBasicToolExt,LastT As THopsBasicToolExt) As Boolean
	MT_GB_Output_Changed = False
	If (Not LastT.t Is Nothing) And (Not ActT.t Is Nothing) Then
		' check ob Ausgangswechsel auf Aggregat
		If MT_IsGearBoxTool(ActT) Then
			If MT_IsGearBoxTool(LastT) And MT_IsGearBoxTool(ActT) Then
				' jetzt Wechsel von Aggregatausgang zu Aggregatausgang
		        If (LastT.gb.ToolNo = ActT.gb.ToolNo) And (LastT.hid = ActT.hid) Then
					MT_GB_Output_Changed = True   ' Wechsel von Ausgang zu Ausgang
		        End If
			End If
		ElseIf MT_IsGearBoxTool_Special(ActT) Then
			' Neu MW 16.11.2005 
			' auch fuer Specialwinkelgetriebe
			If MT_IsGearBoxTool_Special(LastT) And MT_IsGearBoxTool_Special(ActT) Then
				' jetzt Wechsel von Aggregatausgang zu Aggregatausgang
		        If (LastT.gb.ToolNo = ActT.gb.ToolNo) And (LastT.hid = ActT.hid) Then
					MT_GB_Output_Changed = True   ' Wechsel von Ausgang zu Ausgang
		        End If
			End If
		End If
	End If
	
End Function


Function MT_Get_RangeXYZ(ActT As THopsBasicToolExt,MinX,MaxX,MinY,MaxY,MinZ,MaxZ As Double)
Dim Ref_Agg As Double
Dim Ref_PH As Object ' IIHead    ' Referenzhead
Dim dummy As Object
Dim Fehler As Integer
Dim rminx,rmaxx,rminy,rmaxy,rminz,rmaxz As Double


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
		Set dummy = ActT.t_dh  'TDATA.GetDrillingHead_ID(Ref_Agg)
		rminx= dummy.DrillingHead.RangeMinX
		rmaxx= dummy.DrillingHead.RangeMaxX
		rminy= dummy.DrillingHead.RangeMinY
		rmaxy= dummy.DrillingHead.RangeMaxY
		rminz= dummy.DrillingHead.RangeMinZ
		rmaxz= dummy.DrillingHead.RangeMaxZ
	ElseIf MT_isDHSaw(ActT) Then
		' DrillingHeadSaw
		Set dummy = ActT.T_DHSaw  'TDATA.GetDrillingHead_ID(Ref_Agg)
		rminx= dummy.DrillingHead.RangeMinX
		rmaxx= dummy.DrillingHead.RangeMaxX
		rminy= dummy.DrillingHead.RangeMinY
		rmaxy= dummy.DrillingHead.RangeMaxY
		rminz= dummy.DrillingHead.RangeMinZ
		rmaxz= dummy.DrillingHead.RangeMaxZ
	Else 	
		Set dummy = Nothing
	End If
	If Not dummy Is Nothing Then
		' -- 1. X - Bereich
		If equal(rminx-rmaxx,0) Then
			' Bereich ueber Ref-Spindel ermitteln
			If Not ActT.h Is Nothing Then
				' Standard - processhead
				Set Ref_PH = TDATA.GetHead_ID(Ref_Agg)
			Else
				Set Ref_PH = TDATA.GetDrillingHead_ID(Ref_Agg)
			End If
			
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
			' X- Range- Werte vom Head selbst uebernehmen
			MinX = rminx
			MaxX = rmaxx
		
		End If
		' -- 2. Y - Bereich
		'If equal(rminy-rmaxx,0) Then   MW 02.09.2013
		If equal(rminy-rmaxy,0) Then
			' Bereich ueber Ref-Spindel ermitteln
			If Not ActT.h Is Nothing Then
				' Standard - processhead
				Set Ref_PH = TDATA.GetHead_ID(Ref_Agg)
			Else
				Set Ref_PH = TDATA.GetDrillingHead_ID(Ref_Agg)
			End If
			
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
			' Y- Range- Werte vom Head selbst uebernehmen
			MinY = rminy
			MaxY = rmaxy
		
		End If
		' -- 3. Z - Bereich
		If equal(rminz-rmaxz,0) Then
			' Bereich ueber Ref-Spindel ermitteln
			If Not ActT.h Is Nothing Then
				' Standard - processhead
				Set Ref_PH = TDATA.GetHead_ID(Ref_Agg)
			Else
				Set Ref_PH = TDATA.GetDrillingHead_ID(Ref_Agg)
			End If
			
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
			' Z- Range- Werte vom Head selbst uebernehmen
			MinZ = rminz
			MaxZ = rmaxz
		
		End If
	Else
		Fehler=1
	End If
	
'	If Fehler=1 Then	
'		AddMistake(GetErrMsg(160,"_Fehler bei Ermittlung Min MaxRange X/Y/Z !",1))
'		AddMistake(GetErrMsg(161,"_Parameter Ref-Spindel ",1)+ftos(Ref_Agg)+" ?")
'	Else
'		'AddHint("Range-Ermittlung fuer Aggregat" + dummy.Description)
'		'AddHint("Minx: "+ftos(MinX)+" Maxx: "+ftos(MaxX)+" MinY: "+ftos(MinY)+" MaxY: "+ftos(MaxY)+" Minz: "+ftos(MinZ)+" MaxZ: "+ftos(MaxZ))
'	End If

	
End Function

Function MT_CheckFeedrate(ActT As THopsBasicToolExt,Feedrate) As Double
Dim MaxFeedrate,MinFeedrate As Double  ' min-max Vorschub
Dim result As Double     ' Rueckgabewert

	result=Feedrate
	MT_GetMinMaxFeedrate(ActT,MinFeedrate,MaxFeedrate)
	
	' erstmal generell beschraenken
	If Feedrate > MaxFeedrate Then
		result=MaxFeedrate
	Else
		If Feedrate< MinFeedrate Then
			result=MinFeedrate
		End If
	End If
	'MT_CheckFeedrate = result
	' MW 04.01.2011 Vorschub 11335.234 mach keinen Sinn eh immer als integer ausgegeben
	MT_CheckFeedrate = Round(result)
	
End Function


Function MT_GetMinMaxFeedrate(ActT As THopsBasicToolExt,ByRef Minf,ByRef MaxF)
	Minf = ActT.t.MinFeedrate
	MaxF = ActT.t.MaxFeedrate
End Function


	' Neu MW 27.04.2005
Function MT_SetDrillingHeadData(tools,dh As tdh,Driller As tDriller)
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
	If PPara.I_Feedrate = ActT.t_dh.MoveInFeedrate Then
		' vorschub des Bohrkopfs
		dh.VE=ActT.t.MoveInFeedrate
	Else
		' programmierter Vorschub
	    dh.ve=PPara.I_Feedrate
	End If
	If PPara.Feedrate = ActT.t_dh.Feedrate Then
		' vorschub des Bohrkopfs
		dh.V=ActT.t.Feedrate
	Else
		' programmierter Vorschub
	    dh.v=PPara.Feedrate
	End If
	If PPara.S_Feedrate = actt.t_dh.MoveOutFeedrate Then
		' vorschub des Bohrkopfs
		dh.VA=ActT.t.MoveOutFeedrate
	Else
		' programmierter Vorschub
	    dh.va=PPara.S_Feedrate
	End If
	
	
	
	' Bohrdaten fuellen in Type TBohrer
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


' Ermittlung, ob Aggregat in der Lage pneumatic zu benutzen
Function MT_isToolUsingPneumatic(t As THopsBasicToolExt)
Dim result As Boolean

	result = False
	If (MT_IsGearBoxTool(t)) Or (MT_IsGearBoxTool_Special(t)) Then
		If t.gb.UsePneumaticChannels Then
		 	result = True
		End If
	End If
	MT_isToolUsingPneumatic = result
End Function



Function MT_Underside_Set_Param_Angle(t As THopsBasicToolExt,TAngle)
Dim WiUndersideGear As Double
			
			WiUndersideGear = GetWinkelGrad(0,0,t.t_gb.GB_ToolPlace.OffsetX,t.t_gb.GB_ToolPlace.OffsetY)
			' 360-Tangle da Tangentenwinkel auf der um 180° gekippten Ebene betrachtet wird
			UndersideTool.dw = Norm0_360(ActV.RotA + (360-TAngle) + WiUndersideGear -90)
			
			' Ebenenwinkel
			UndersideTool.view_w = Norm0_360(ActV.RotA + (360-TAngle) - 90)
	
End Function


'Function MT_GetOffsets_Pneumatic_Saw(t As THopsBasicToolExt,Raster_Angle,X,Y,Z)
'Dim id As Integer
'Dim dx,dy,dz As String
'
'	id = ((Raster_Angle/90)+1)*10
'		
'	dx=""
'	dy=""
'	dz=""
'	X=0
'	Y=0
'	Z=0
'	
'	If Not t.t_PH.PH_ToolPlace Is Nothing Then
'		If Not t.T_ph.PH_ToolPlace.Additions.GetAddition_ID(id) Is Nothing Then
'			dx= t.T_ph.PH_ToolPlace.Additions.GetAddition_ID(id).Value 
'			X= StrToFloat(dx)
'		End If
'		If Not t.T_ph.PH_ToolPlace.Additions.GetAddition_ID(id+1) Is Nothing Then
'			dy= t.T_ph.PH_ToolPlace.Additions.GetAddition_ID(id+1).Value 
'			Y= StrToFloat(dy)
'		End If
'		If Not t.T_ph.PH_ToolPlace.Additions.GetAddition_ID(id+2) Is Nothing Then
'			dz= t.T_ph.PH_ToolPlace.Additions.GetAddition_ID(id+2).Value
'			Z= StrToFloat(dz)
'		End If
'	End If
'	
'	
'End Function



Function MT_get_Add_ID(ActT As THopsBasicToolExt,id,isok As Boolean)
Dim Addi As IIAddition
	isok = False
	If ActT.t.ObjectType=htokStandardTool Then
		Set Addi = ActT.h.Additions.GetAddition_ID(id)
	ElseIf ActT.t.ObjectType=htokDrillingHeadTool Then
		Set Addi = ActT.t_dh.DrillingHead.Additions.GetAddition_ID(id)
	ElseIf MT_IsGB(ActT) Then
		' MW 15.11.2018
		Set Addi = ActT.h.Additions.GetAddition_ID(id)
	Else
		' momentan nur fuer Hauptspindel und Bohrkopf
		'AddMistake("93847432456")
	End If
	
	If Not Addi Is Nothing Then
		isok = True
		MT_get_Add_ID=Addi.Value
	Else
		'AddMistake("ZusatzInfo ID+"+inttos(id)+" - fuer Werkzeug "+ActT.t.Description+ ".. nicht gefunden")
	End If
End Function



Function MT_IS_MainAgg(t As THopsBasicToolExt) 
	MT_IS_MainAgg=(MT_H_Is_3_Axis(t) Or MT_H_Is_4_Axis(t) Or MT_H_Is_5_Axis(t))
End Function


' *****************************************************************************************
' ** MT_H -> Aggregat ohne Drehachse und ohne Kippachse in Z- ausgerichtet
' *****************************************************************************************
Function MT_H_Is_3_Axis(t As THopsBasicToolExt)

Dim rot As Variant
Dim tip As Variant
	
	MT_H_Is_3_Axis = False
	
	
	If Not t.H Is Nothing Then
		'test =TH.Description
		rot = t.H.RotType
		tip = t.H.TipType
		
		If (rot = atFix) And (tip = atFix) Then
		    
		    ' Drehachse fix kippachse fix
		    
			If t.h.ToolPlaces.GetToolPlace_PlaceID(1).TipAngle=0 Then
				' nur in Z- Richtung liegende Spindeln 1!!
				MT_H_Is_3_Axis = True
			End If
		End If
		
	End If

End Function

' *****************************************************************************************
' ** MT_H -> Aggregat mit Drehachse welche um Z dreht
' *****************************************************************************************
Function MT_H_Is_4_Axis(t As THopsBasicToolExt)

Dim rot As Variant
Dim tip As Variant
	
	MT_H_Is_4_Axis = False
	
	
	If Not t.H Is Nothing Then
		'test =TH.Description
		rot = t.H.RotType
		tip = t.H.TipType
		
		If (rot = atFree) And (tip = atFix) Then
		    ' Drehachse frei
			If t.h.ToolPlaces.GetToolPlace_PlaceID(1).TipAngle=0 Then
				' nur in Z- Richtung liegende Spindeln 1!!
				MT_H_Is_4_Axis = True
			End If
		End If
		
	End If
		


End Function

' *****************************************************************************************
' ** MT_H -> Aggregat mit Dreh- und Kippachse welche um Z dreht
' *****************************************************************************************
Function MT_H_Is_5_Axis(T As THopsBasicToolExt)

Dim rot As Variant
Dim tip As Variant
	
	MT_H_Is_5_Axis = False
	
	
	If Not T.H Is Nothing Then
		'test =TH.Description
		rot = T.H.RotType
		tip = T.H.TipType
		
		If (rot = atFree) And (tip = atFree) Then
		    ' Drehachse frei + Kippachse frei
			If T.h.ToolPlaces.GetToolPlace_PlaceID(1).TipAngle=0 Then
				' nur in Z- Richtung liegende Spindeln 1!!
				MT_H_Is_5_Axis = True
			Else
	 			AddMistake(GetErrMsg(154,"_unerlaubte Ausgangsrichtung bei Aggregat",1))
			End If
		End If
		
	End If
		


End Function





' *****************************************************************************************
' ** Handelt es sich um Standardwerkzeug aus Wechsler 
' *****************************************************************************************
Function MT_Is_S_Tool(t As THopsBasicToolExt)
Dim erg As Boolean
	erg = False
	If t.t.ObjectType=htokStandardTool Then 
		erg = True
	End If
	MT_Is_S_Tool = erg
End Function

Function MT_GetHeadName(t As THopsBasicToolExt)
Dim TP_Name As String
	If Not t.h Is Nothing Then
		MT_GetHeadName = t.h.Description
	End If

	
End Function

' --
' -- MW 19.04.2007 10:56:14
' --
Function MT_Find5AxisHead
Dim i,cHeads As Integer
Dim result As Boolean 
	result = False
	cHeads=TDATA.MachineData.ProcessHeadsCount
	For i = 0 To cHeads-1
		If (TDATA.MachineData.GetProcessHead_Index(i).RotType=atFree) And (TDATA.MachineData.GetProcessHead_Index(i).TipType=atFree) Then
			result = True
			Exit For
		End If
	Next
	MT_Find5AxisHead=result
End Function

Function MT_Get_MachPara_Add(search_id) As Variant
' -- 
' --  MW 25.07.2007 08:52:18
' --  fuer Tresholds
' --
Dim i As Long
Dim Addi As IIAddition
Dim iDName As Variant 
Dim result As String
	result=""
	Set Addi = TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(search_id)
	If Not Addi Is Nothing Then
		result=Addi.Value 
	End If
	MT_Get_MachPara_Add=result
	If result="" Then
		AddHint("MT_Get_MachPara_Add not found ID - " +ftos(search_id))
	End If
	Set Addi=Nothing
End Function

Function MT_TEdgeChange(ActT As THopsBasicToolExt,LastT As THopsBasicToolExt) As Boolean
	MT_TEdgeChange=False
	If (Not LastT.t Is Nothing) And (Not ActT.t Is Nothing) Then
        If (LastT.t.ToolNo = ActT.t.ToolNo) And (LastT.hid=ActT.hid) And MT_IS_MainAgg(ActT) And MT_IS_MainAgg(LastT) Then
			MT_TEdgeChange=True
        End If
	End If
End Function


' --
' -- MW 24.09.2012
' -- Ermittlung der Anzahl von Werkzeugwechselspindeln
' -- Massgebend Hauptspindel mit zugelassenen Wechselspindeln
' --
Function MT_Count_TC_Heads
Dim i,cHeads As Integer
Dim found As Integer
	found = 0
	cHeads=TDATA.MachineData.ProcessHeadsCount
	For i = 0 To cHeads-1
		If TDATA.MachineData.GetProcessHead_Index(i).ToolChangersEnabled.Count>=1 Then
			' Wechselspindel gefunden
			' TDATA.MachineData.GetProcessHead_Index(i).Description -> "Spindle 5X (P01 V01)"
			found = found + 1
		End If
	Next
	MT_Count_TC_Heads=found 
End Function

' MW 12.12.2012
Function MT_SameTools(ActT As THopsBasicToolExt,LastT As THopsBasicToolExt) As Boolean
	MT_SameTools=False
	If (Not LastT.t Is Nothing) And (Not ActT.t Is Nothing) Then
        If (LastT.t.ToolNo = ActT.t.ToolNo) And (LastT.hid=ActT.hid) And (ActT.t.ID = LastT.t.ID) Then
			MT_SameTools=True
        End If
	End If
End Function

		

' -- Neu MW 02.12.2013 - Schwellwerte Haube holen ueber ID's 10100 - 10119 im Ausgang des Heads
Function MT_Get_Head_SchwellwerteHaube(Head,HaubenMode) As Double()
Dim Schwellwert() As Double   ' Schwellwerte
Dim i,id As Long 
Dim THead As IIProcessHead
Dim SCount As Integer   ' Anzahl Schwellwerte

	ReDim Preserve Schwellwert(0)
	Set THead = TDATA.GetProcessHead_ID(Head)

	If Not THead Is Nothing Then
	' -- Schwell- Werte von Ausgang holen
	For i = 0 To 19
		id = 10100+i
			If Not THead.ToolPlaces.GetToolPlace_Index(0) Is Nothing Then
				HaubenMode= THead.ToolPlaces.GetToolPlace_Index(0).PosDustExhaust
				If Not HaubenMode=1 Then
					' Nur wenn Dyn. gewaehlt     
					Exit Function
				End If
				If Not THead.ToolPlaces.GetToolPlace_Index(0).Additions.GetAddition_ID(id) Is Nothing Then
					If (THead.ToolPlaces.GetToolPlace_Index(0).Additions.GetAddition_ID(id).Value<>"") And IsNumeric(THead.ToolPlaces.GetToolPlace_Index(0).Additions.GetAddition_ID(id).Value) Then
					ReDim Preserve Schwellwert(UBound(Schwellwert)+1)
					Schwellwert(i+1)=StrToFloat(THead.ToolPlaces.GetToolPlace_Index(0).Additions.GetAddition_ID(id).Value)
					SCount=SCount + 1
				Else
						AddHint("Schwellwert "+inttos(i+1)+" leer!")
					End If
				Else
					AddHint("Schwellwert "+inttos(i+1)+" ueberlesen!")
				End If
				
			Else
				pp_err(0,"toolplaces = nothing")
			End If
		Next i 
	End If
	MT_Get_Head_SchwellwerteHaube = Schwellwert
End Function



Function MT_Get_PosDustExhaust(T As THopsBasicToolExt) As Integer
Dim DustPos As Integer      ' das ist die Ermittelte Position

	DustPos = 0  ' ohne !?
	If T.h Is Nothing Then
		' Head nicht gefunden oder nicht bekannt
		MT_Get_PosDustExhaust = 0
		Exit Function
	End If
	
	
	If (T.h.ToolPlaces.GetToolPlace_Index(0).PosDustExhaust > 0) Then
		' Im Bearbeitungskopf dynamisch also Werkzeug / Winkelgetriebe heranziehen
		If MT_IsGearBoxTool(T) Or  MT_IsGearBoxTool_Special(T) Then
			' Winkelgetriebe oder aehnliches
			DustPos = T.GB.PosDustExhaust
		ElseIf Not T.T_CEdge Is Nothing Then
			DustPos = T.T_CEdge.PosDustExhaust
		End If
	Else
		DustPos = T.h.ToolPlaces.GetToolPlace_Index(0).PosDustExhaust
	End If
	
	If (isDINISO_Process) Then
		' keine Absaugung 
		'MT_Write_DustCover=""
		DustPos = 0
	End If
	MT_Get_PosDustExhaust=DustPos

End Function

Function MT_Get_HaubenMode(T As THopsBasicToolExt) As Long
Dim Mode As Long
	
	Mode =-1
	If Not T.T.CuttingEdge.Additions.GetAddition_ID(1) Is Nothing Then
		Mode=CLng(T.T.CuttingEdge.Additions.GetAddition_ID(1).Value)
	End If
	
	If Mode > 0 Then
		MT_Get_HaubenMode = Mode
	Else
		MT_Get_HaubenMode = -1
	End If
End Function



Function MT_ClearTHopsBasicToolExt(T As THopsBasicToolExt)
  Set T.T = Nothing
  Set T.MachineData = Nothing
  Set T.H = Nothing
  Set T.T_S = Nothing
  Set T.T_DH = Nothing
  Set T.T_PH = Nothing
  Set T.T_GB = Nothing
  Set T.T_SGB = Nothing
  Set T.T_TCA_GB = Nothing
  Set T.T_DHSaw = Nothing
  Set T.tc = Nothing
  Set T.gb = Nothing
  Set T.TC = Nothing
  Set T.T_CEdge = Nothing
'  Set T.SetOf_DustPositions = Nothing       ' MW 24.02.2016
'  Set T.SetOf_DustPositionsMFunc = Nothing  ' MW 24.02.2016

End Function



' *****************************************************************************************
' ** Ermittlung der Haubenposition des Bearbeitungskopfes
' *****************************************************************************************
Function MT_GET_HEAD_POSDUST(T As THopsBasicToolExt) As Integer

	If Not T.h Is Nothing Then
		MT_GET_HEAD_POSDUST = T.H.ToolPlaces.GetToolPlace_Index(0).PosDustExhaust
	Else
		MT_GET_HEAD_POSDUST = 0   ' ohne Haube
	End If
	
End Function

' *****************************************************************************************
' ** Ermittlung der Haubenposition der Schneide
' *****************************************************************************************
Function MT_GET_T_POSDUST(T As THopsBasicToolExt) As Integer

	MT_GET_T_POSDUST = 0   ' ohne Haube

	If MT_IsGB(T) Then
		' Winkelgetriebe oder aehnliches
		MT_GET_T_POSDUST = T.GB.PosDustExhaust
	ElseIf Not T.t_cedge Is Nothing Then
		MT_GET_T_POSDUST = T.T_CEdge.PosDustExhaust 
	End If
	
End Function



' MW 09.02.2016 - Neue Logik Haube ueber Engine 
' Function MT_Get_Suction (Kind,DP_NCIE,DP_MinT,DP_MaxT)
' 
' Dim CE_DustPos As Integer 
' Dim DustPos As Integer 
' Dim DustPos_PH As Integer 	
' Dim DustPos_CE As Integer 	

' 	DustPos = 0 ' "-" Keine 
	
' 	DustPos_PH = MT_GET_HEAD_POSDUST(ActT)   ' Dem Bearbeitungskopf/Processhead hinterlegte Haubenpos
' 	DustPos_CE = MT_GET_T_POSDUST(ActT)      ' MT-Manager eingetragene Position im Winkelgetriebe oder der Werkzeug-Schneide

' 	If DustPos_PH = 0 Then    	 ' In der Spindel ist keine "-" hinterlegt
' 		' wenn auf ProcessHead keine Haube gewaehlt gibt es auch keine
' 		'MF = actt.SetOf_DustPositionsMFunc.GetString(0)
' 		' Haubenpos DEFAULT = OBEN
' 		DustPos = 0 ' "-" Keine 
' 	ElseIf DustPos_PH = 1 Then   ' dynamische Position
' 		' Pos aus der Schneide holen
' 		DustPos = DustPos_CE   ' MT-Manager eingetragene Position im Winkelgetriebe oder der Werkzeug-Schneide
		
' 		If PPara.NCiE.sh.activ Then
' 			' Program. Haubenposition ueber NCIExt -100244 gefunden
' 			DustPos = PPara.NCiE.sh.Value1  ' Wert ist bereits plausibilisiert
' 		End If
' 		If (DustPos = 1) Then
' 			' Dyn. von Schneide oder programmiert
' 			If (equal(PPara.MinTipA,0) And equal(PPara.MaxTipA,0)) Then  ' And Not isgb(actt) Then
' 				' senkrechte Ausrichtung - auch bei Winkelgetriebe moeglich
' 				' dyn. Position ueber DLL fahren
' 			Else
' 				' undefiniert
' 				DustPos=0   ' keine
' 			End If
' 		End If
' 	Else                        
' 		' Dem PH wurde eine fixe Position hinterlegt 
' 		DustPos = DustPos_PH  
' 	End If
' 	MT_Get_Suction = DustPos
' End Function

' *****************************************************************************************
' ** MW 10.02.2016 
' ** -> Plausibilierung des programmierten Wertes Haube, gesetzt werden dürfen nur die Werte, welche unter Eigenschaften MTManager definiert sind
' ** -> also auch nur die welche im Werkzeug - Schneide definiert werden koennen
' *****************************************************************************************
Function MT_CheckProgValue_Suction(Suction_Pos) As String
Dim i As Integer 
	If (Suction_Pos < 0) Or (Suction_Pos > TDATA.MachineData.MachineParameter.PosDustExhaustTypes.Count-1) Then
'		pp_err(1589,Suction_Pos) 
	Else
		MT_CheckProgValue_Suction = TDATA.MachineData.MachineParameter.PosDustExhaustTypes.GetString_Index(Suction_Pos)	
	End If
End Function


' *****************************************************************************************
' ** Werkzeug - Funktion ermittelt anhand der Drehzahl, die Drehrichtung und gibt zudem das Uebersetzungsverhaeltnis zurueck
' *****************************************************************************************
' ** MW 30.05.2017
Function MT_Get_Speed_Data(T As THopsBasicToolExt,pspeed,dr,dz) ' rueckgabe dr,dz,gr

Dim Speed_Trans_complete As Double     ' Getriebeuebersetzungsverhaeltnis
Dim Speed_Trans_MU As Double  ' ueBersetzung Hauptspindel
Dim Speed_Trans_GB As Double  ' uebersetzung Winkelgetriebeausgang
Dim Speed_trans_DH As Double  ' uebersetzung Bohrkopf - wird hierher uebergeben
Dim Speed_trans_PH As Double  ' uebersetzung Bohrkopf - wird hierher uebergeben

	Speed_Trans_complete = 0
	Speed_Trans_MU = 0
	Speed_Trans_GB = 0
	Speed_trans_DH = 0
	Speed_trans_PH = 0


'    If IsMissing(Gear_Ratio) Then
'    	' parameter nicht uebergeben
'    	Gear_Ratio = 1
'    End If
    
	dz = inttos(MT_Get_SpindleSpeed(T,pspeed))
	dr = IIf(dz<0,4,3)
	
	If Not T.T.GetOn_TC Is Nothing Then
		' Werkzeug auf Wechsler
		If Not T.h Is Nothing Then
			If T.h.ToolPlaces.Count = 1 Then
				' -- mehr wie einen Ausgang gibt derzeit nicht
				Speed_Trans_MU = T.h.ToolPlaces.GetToolPlace_Index(0).GearRate
				Speed_Trans_GB = 1 ' falls nicht Winkelgetriebe
			Else
				pp_err(0,"Gear ratio - more than one main unit output")
			End If
			If Not T.t_gb Is Nothing Then
				' Werkzeug auf Winkelgetriebe
				Speed_Trans_GB = T.t_gb.GB_ToolPlace.GearRate
			End If
		Else
			pp_err(1592,T.HId)
		End If
		Speed_Trans_complete = Speed_Trans_MU*Speed_Trans_GB
	ElseIf MT_IsDH(T) Then
		' Drilling Head
		' Tx Dx ueberschreiben mit korrekter Einstellung	
		dz = inttos(MT_Get_SpindleSpeed(T,pspeed))
		
		' --  uebersetzungsverhaeltnis DH
'		Speed_trans_DH = Gear_Ratio
		
		Speed_Trans_complete = Speed_trans_DH
		
	ElseIf MT_isDHSaw(T) Then
		' Nutsaege auf Drilling Head
		If T.t_dhsaw.RotDirection = rdLeft Then
		   dr=3
		ElseIf T.t_dhsaw.RotDirection = rdRight Then
			dr=4
		ElseIf T.t_dhsaw.RotDirection = rdLeftRight Then
		
		End If
		dz = inttos(MT_Get_SpindleSpeed(T,pspeed))
		' --  uebersetzungsverhaeltnis DH
		If Not T.t_dhsaw Is Nothing Then
			Speed_trans_DH = T.t_dhsaw.DH_ToolPlace.GearRate
		End If
		Speed_Trans_complete = Speed_trans_DH
		
	End If
	
'	gr = Speed_Trans_complete

	

End Function



Function MT_Write_Activate_Tool(T As THopsBasicToolExt,SetWZData)
Dim TNo As Long
Dim DNo As Long 
'	TNo = T.T.ToolNo ' T von Werkzeug - ToolNo - Mode
'	DNo = T.T.CorrNo
	
'	TNo=T.t.GetPlaceID_OnTC
	
'	TNo = ppara.tno_tmp   ' T.PH_Add.Tool_No
	TNo = T.T.ID
	DNo = ppara.dno_tmp   ' T.PH_Add.Corr_No
	
	If MT_IsDH(T) Then
		wcnc("D0")
	ElseIf MT_isDHSaw(T) Then
		'D0 von Haus aus aktiv lassen
		'wcnc("D0") 
	ElseIf MT_IsGB(T) Then
		' MW 15.11.2018 - 4-Achs
		'D0 von Haus aus aktiv lassen
		'wcnc("D0") 
		If (PPara.MMode<=0) Then 
		    ' beim C-Achsfraesen oder 5-Achsfraesen keine Korrektur notwendig
			If ((TNo>0) And (DNo>0)) Then
				' wcnc("T"+IntToS(TNo)+" D"+IntToS(DNo))
				wcnc("D"+IntToS(TNo))
				
' MW 28.06.2022				
'				If SetWZData Then
'					' notwendig fuer statische Bearbeitungen auf Ebene - hier Verwendung G41/G42
'					WCNC_SET_WZ_DATA_GB(T)
'				End If
			Else
				pp_err(0,"ToolNo<=0 or CorrNo<=0")
			End If
		End If
	ElseIf MT_H_Is_3_Axis(T) Or MT_H_Is_4_Axis(T) Or MT_H_Is_5_Axis(T) Then
		'  MW 15.11.2018 - 4-Achs
		If ((TNo>0) And (DNo>0)) Then
			'wcnc("T"+IntToS(TNo)+" D"+IntToS(DNo))
			wcnc("D"+IntToS(TNo))
'			If SetWZData Then
'				WCNC_SET_WZ_DATA_STANDARD(T)
'			End If

		Else
			pp_err(0,"ToolNo<=0 or CorrNo<=0")
		End If
		
	ElseIf MT_Is_MFE_Vertical(T) Then
		' MW 27.06.2018 MFE Saege
'		If ((TNo>0) And (DNo>0)) Then
'			wcnc("T"+IntToS(TNo)+" D"+IntToS(DNo))
'			If SetWZData Then
'				' Radius bereits von der Engine verrechnet.
'				' Wenn der Aggregatsoffset auf SägeblattMitte / Aggregatzentrum eingetragen bleibt lediglich die horizontale Länge zu verrechnen
'				wcncaddcom("V.G.WZ_AKT.L="+ftos(0*T.t.Length),"set Tool length",True)
'				wcncaddcom("V.G.WZ_AKT.R="+ftos(T.t.Radius),"set Tool length",True)
'			End If
'		End If
	Else
		pp_err(8)
	End If
	
End Function

Function MT_get_DH_Drill_Offsets(driller As tDriller,X,Y,Z)
Dim LenZ,LenY,LenX As Double

	LenX=0
	LenY=0
	LenZ=0
	
	X = 0
	Y = 0
	Z = 0
    If driller.TP.Orientation=orVertical Then 
    	' vertikaler Ausgang Bohrerlänge auf Länge 1 schreiben
       LenZ= driller.Length
    ElseIf driller.TP.Orientation=orYPlus Then 
    	' hor. Ausgang Y+
    	LenY = - driller.Length
    ElseIf driller.TP.Orientation=orYMinus Then 
    	' hor. Ausgang Y-
    	LenY = driller.Length
    ElseIf driller.TP.Orientation=orXPlus Then 
    	' hor. Ausgang X+
    	LenX = -driller.Length
    ElseIf driller.TP.Orientation=orXMinus Then 
    	' hor. Ausgang X-
    	LenX = driller.Length
    Else
    	' Fehler
    	pp_err(0,"Fehler bei Bohrdaten unerlaubte Orientation vom BohrkopfAusgang")
    End If
    
	X = LenX + (-driller.OffX) ' distance X
	Y = LenY + (-driller.OffY) ' distance y
	Z = LenZ + (-driller.OffZ) ' distance Z
	
End Function

Function MT_GetOffsets_DHSaw(T As THopsBasicToolExt,ox,oy,oz)
Dim laenge2,laenge3 As Double 

			'  ppara.actt.t.Get_OffsetToolRefPoint(RotA, TipA, ox, oy, oz)		tut nicht
			laenge2 = 0
			laenge3 = 0
			ox = 0 
			oy = 0
			oz = 0
            If (T.t.DH_ToolPlace.Orientation=orYPlus) Then 
            	laenge2 = -(T.t.Length-T.t.SawThickness/2)
            End If
            If (T.t.DH_ToolPlace.Orientation=orYMinus) Then 
                laenge2 = (T.t.Length-T.t.SawThickness/2)
            End If
            If (T.t.DH_ToolPlace.Orientation=orXPlus) Then
            	laenge3 = -(T.t.Length-T.t.SawThickness/2)
            End If
            If (T.t.DH_ToolPlace.Orientation=orXMinus) Then
            	laenge3 = (T.t.Length-T.t.SawThickness/2)
            End If

            'TPOffX := -(DH_Saw.DH_ToolPlace.OffsetX);
            'TPOffy := -(DH_Saw.DH_ToolPlace.OffsetY);
            'TPOffz := -(DH_Saw.DH_ToolPlace.OffsetZ);
			
			ox = -T.t.DH_ToolPlace.OffsetX+laenge3
			oy = -T.t.DH_ToolPlace.OffsetY+laenge2
			oz = -T.t.DH_ToolPlace.OffsetZ

	
End Function


' *****************************************************************************************
' ** Winkelgetriebe auf Multifunktionseinheit mit vertikaler Ausrichtung
' ** entspricht "normaler" 4-Achs - Spindel ohne Wechselzugriff mit fix gerüstetem Winkelgetriebe
' *****************************************************************************************
Function MT_Is_MFE_Vertical(T As THopsBasicToolExt)
	
	MT_Is_MFE_Vertical=False
	' wenn True dann ist es ein Werkzeug (Winkelgetriebe auf Nebenaggregat)
	If Not T.t Is Nothing Then
		If (T.t.ObjectType=htokGearboxOnHeadTool) Then
			If (T.h.ToolPlaces.GetToolPlace_PlaceID(1).TipAngle=0) Then
				MT_Is_MFE_Vertical = True
			End If
		End If
		
	End If

End Function

		

Function MT_Get_ID_MachinePara(ID As Long ,default As Variant,result As Variant) As Boolean
Dim found As Boolean 
Dim Nome As String 
Dim value As Variant 
	result = default
	found = False
	If Not TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(ID) Is Nothing Then
		
		value = TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(ID).Value
		If Not Get_ID_RESULT(value, default, result) Then
			pp_err(140,inttos(ID))
		Else
			found=True	
		End If
		
	End If
	
	MT_Get_ID_MachinePara = found
	
End Function

Function MT_Get_ID_Tool(T As THopsBasicToolExt,ID As Long ,default As Variant,result As Variant) As Boolean
Dim found As Boolean 
Dim Nome As String 
Dim value As Variant 
	result = default
	found = False
	If MT_IsDH(T) Then
		' ?
	Else
		If Not T.t.Tool Is Nothing Then
			If Not T.t.Tool.Additions.GetAddition_ID(ID) Is Nothing Then
				
				value = T.t.Tool.Additions.GetAddition_ID(ID).Value
				If Not Get_ID_RESULT(value, default, result) Then
					pp_err(140,inttos(ID))
				Else
					found=True	
				End If
				
			End If
		End If
	End If
	
	MT_Get_ID_Tool = found
	
End Function


Function MT_get_SimuAdditions_Head(HeadID,ID,isok As Boolean)
Dim addi As IIAdditions
'Dim hid As Integer 
Dim Temp
Dim ActT As THopsBasicToolExt

	isok = False
	Set Temp = TDATA.GetProcessHead_ID(HeadID)

	Set addi = NCData.GetExtInfo(ekHead_SimuAdditions,Temp)
	If Not addi.GetAddition_ID(ID) Is Nothing Then
		isok = True
		MT_get_SimuAdditions_Head=addi.GetAddition_ID(ID).Value
	End If
	Set Temp = Nothing
	Set addi = Nothing
	
End Function

