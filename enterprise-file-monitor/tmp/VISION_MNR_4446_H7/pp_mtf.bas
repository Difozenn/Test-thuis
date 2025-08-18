' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \%postdir%\pp_mtf.bas
' -- 
' -----------------------------------------
'#uses "pp_math.bas"
'#uses "pp_mt.bas"
'#uses "pp_global.bas"

Option Explicit



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


' ------------------------------------------------------
' -- writes actual offsets to NC-Vars AOX, AOY, AOZ
' ------------------------------------------------------
Function MT_Write_Offset_NC_Vars As Boolean
Dim AggOX,AggOY, AggOZ, AggOX_SOLL  As Double
Dim LOX,LOY,LOZ As Double 
Dim TPO_x,TPO_y,TPO_z As Double   ' toolplace offsets 
Dim LenO As Double   ' length output
Dim dX,dY,dZ As Double   ' wird für die lenght output - Verrechnung verwendet!
Dim total_ox,total_oy,total_oz As Double
Dim tx,ty,tz As Double
Dim Raster_Angle As Double
Dim r As Integer
	
	AggOX = 0
	AggOY = 0
	AggOZ = 0
	LOX = 0
	LOY = 0
	LOZ = 0
	TPO_x=0
	TPO_y=0
	TPO_z=0
	dX=0
	dY=0
	dZ=0
	AggOX_SOLL=0
	' ----------------------------------------------------------	
	' 1. Aggregate - Offset und Liftoffset ermitteln
	' ----------------------------------------------------------	
	
	If Not (MT_IsDH(ActT)) And Not (MT_isDHSaw(ActT)) Then 
		' kein "Bohrkopf" und keine "Säge auf dem Bohrkopf"
	
		' Offset vom Aggregat sebst - Abstand zum 1. Bohrer
		AggOX = ActT.h.CenterX
		AggOY = ActT.h.CenterY
		AggOZ = ActT.h.CenterZ
	
		' hier offset Ausgang vom Aggregat ( Hauptspindel )
		MT_Write_Offset_NC_Vars = MT_Get_H_Offset_XYZ(ActT,TPO_x,TPO_y,TPO_z)
		
	ElseIf (MT_isDHSaw(ActT)) Then
		' DH- Saw
		' Offset vom Aggregat selbst
		AggOX = ActT.T_DHSaw.MoveX
		AggOY = ActT.T_DHSaw.MoveY
		AggOZ = ActT.T_DHSaw.MoveZ
	End If
	' ----------------------------------------------------------	
	' ----------------------------------------------------------	
	
	
	' ----------------------------------------------------------	
	' 2. ToolPlace Offsets ermitteln
	' ----------------------------------------------------------	
	If ActT.t.ObjectType=4 Then
		' Winkelgetriebe 
		' ------------------------------------------------------------
		' calculate offsets of toolplace for gearbox
		' ------------------------------------------------------------
		ActT.H.ToolPlaces.GetToolPlace_Index(0).GetOffsetToolPlace(ActV.RotA+ActT.t.RotAngle, ActV.TipA, TPO_x, TPO_y, TPO_z)
		' ------------------------------------------------------------
	End If
	
	If MT_Is_TC_T(ActT) Then '(ActT.t.ObjectType=1) Or (ActT.t.ObjectType=4) Then
		' Toolchange Aggregat
		LenO = ActT.H.ToolPlaces.GetToolPlace_Index(0).Length	
		GetDX_DY_DZMitKippW_Laenge( ActT.t.TipAngle,ActT.t.RotAngle,LenO , dX,dY,dZ)
	ElseIf ActT.t.ObjectType=3 Then
		' horizontales Nebenaggregat z.B. schlosskasten
		' auch pneumatic sawing
		' fix Aggregat without toolchange 
		If MT_isPneumaticSaw(ActT) Then
			' aggno muss= 90 sein
			' nur so kann die schwenkbare Säge erkannt werden
			' Raster-Stellung ermitteln
			MT_GetPneumaticSawAngle(ActT,ActV.RotA, Raster_Angle) 
			
			ActT.H.ToolPlaces.GetToolPlace_Index(0).GetOffsetToolPlace(Raster_Angle, ActV.TipA, TPO_x, TPO_y, TPO_z)
		Else
			LenO = ActT.t_PH.PH_ToolPlace.Length
			GetDX_DY_DZMitKippW_Laenge( ActT.t.TipAngle,ActT.t.RotAngle,LenO , dX,dY,dZ)
		End If
	End If
	
	AddHint("")
	AddHint("")
	AddHint("===============================================================")
	If Not (ActT.t.ObjectType = 2) And Not (ActT.t.ObjectType = 7) Then 
		AddHint("Aggregatsverrechnung fuer "+ActT.h.Description+" ")
	Else
		AddHint("Aggregatsverrechnung fuer "+ActT.T_DHSaw.Description+" ")
	End If
	AddHint("===============================================================")
	AddHint("Aggregat X:"+FToS(AggOX)+" Y:"+FToS(AggOY)+" Z:"+FToS(AggOZ))
	AddHint("Lift Offset X:"+FToS(LOX)+" Y:"+FToS(LOY)+" Z:"+FToS(LOZ))
	AddHint("Ausgang Offset X:"+FToS(TPO_x)+" Y:"+FToS(TPO_y)+" Z:"+FToS(TPO_z))
	AddHint("Längen Offsett X:"+FToS(dX)+" Y:"+FToS(dY)+" Z:"+FToS(dZ))


	
	
	total_ox = -AggOX-TPO_x-LOX-dX+AggOX_SOLL
	total_oy = -AggOY-TPO_y-LOY-dY
	total_oz = -AggOZ-TPO_z-LOZ-dZ
	
	If Marker.Messbezug Then
		r= Marker.WP_ActIndex * 100
		'Ftos(WPI(Marker.WP_ActIndex).xMessPunkte(MessPunkt.Mess_Nr-3).Ym
		wcnc(OffPX+"=("+FToS(total_ox)+")+("+FTOS(Marker.FaktorX)+")*(R"+Inttos(r+Marker.MessbezugX)+")")
		wcnc(OffPY+"=("+FToS(total_oy)+")+("+FTOS(Marker.FaktorY)+")*(R"+Inttos(r+Marker.MessbezugY)+")")
		wcnc(OffPZ+"=("+FToS(total_oz)+")+("+FTOS(Marker.FaktorZ)+")*(R"+Inttos(r+Marker.MessbezugZ)+")")
		'wcnc(OffPX+"="+FToS(total_ox)+ "+("+FTOS(Marker.FaktorX)+")*Marker.X) "+OffPY+"="+FToS(total_oy)+ " "+OffPZ+"="+FToS(total_oz))
	Else
		If MT_Is_Vertical_StandardTool5Axis(Actt) Then
			If Actt.t.Tool.ToolType=tSaw And PPara.PreObjectTyp=otSawing And Actt.H_add.MCorrNo>0 Then
				WCNC("DDL=$TC_DP6["+inttos(ActT.h_add.ToolNo)+","+inttos(ActT.h_add.CorrNo)+"]")
				'WCNC("DOOX=(COS("+FTOS(Actv.TipA)+"*PIH/180)*SIN("+FTOS(Actv.RotA)+"*DL))")
				'WCNC("DOOY=(COS("+FTOS(Actv.TipA)+"*PIH/180)*COS("+FTOS(Actv.RotA)+"*DL))")
				'WCNC("DOOZ=(SIN("+FTOS(Actv.TipA)+"*PIH/180)*DL))")
				WCNC("DOOX=(COS("+FTOS(Actv.TipA)+")*SIN("+FTOS(Actv.RotA)+")*DDL)")
				WCNC("DOOY=(COS("+FTOS(Actv.TipA)+")*COS("+FTOS(Actv.RotA)+")*DDL)")
				'WCNC("IF (DL>0)")
				WCNC("DOOZ=(SIN("+FTOS(Actv.TipA)+")*(DDL*(-1)))")
				'WCNC("ELSE")	
				
				'Wcnc("ENDIF")
				
				wcnc(OffPX+"=("+FToS(total_ox)+ "+DOOX) "+OffPY+"=("+FToS(total_oy)+ "+DOOY) "+OffPZ+"=("+FToS(total_oz)+"+DOOZ)")
			Else
				wcnc(OffPX+"="+FToS(total_ox)+ " "+OffPY+"="+FToS(total_oy)+ " "+OffPZ+"="+FToS(total_oz))
			End If
		Else
			wcnc(OffPX+"="+FToS(total_ox)+ " "+OffPY+"="+FToS(total_oy)+ " "+OffPZ+"="+FToS(total_oz))
		End If
		
	End If
End Function



' *****************************************************************************************
' ** Werkzeugliste zur Info ausgeben
' *****************************************************************************************
Function MT_Write_TCheck
Dim i,j As Long
Dim T As THopsBasicToolExt
'Dim LastBoxId As Long
Dim BoxNoArray() As Long
Dim idh As IIDrillingHead
Dim DH_CEdge As IICuttingEdge
Dim dummy As Variant

Dim dh_tool As IITool
Dim toolno,maxrot,rad,length,Len1,Len2,Len3 As Double


	wcnccom("used tools")
	wcnccom("")
	For i = 0 To UBound(ToolArray)-1
	    ReDim Preserve BoxNoArray(i) 
	
		T = ToolArray(i)
		
		If Not MT_CheckisIdInList(T.t.ID,BoxNoArray) Then
			If MT_IsDH(T) Then
				' Drilling Head - no check ???!?!?!?!?
				wcnccom("Box:"+strsize(inttos(T.t.ID),5,2)+" HId:"+StrSize(Inttos(T.HId),5,1)+" "+StrSize(T.T.Description,30,1)) 
				' alle Bohrer-Daten checken
				For j= 0 To T.T_DH.DrillingHead.ToolPlaces.Count-1
					Set dummy = T.T_DH.DrillingHead.ToolPlaces.GetToolPlace_Index(j).ActiveTool
					Set dh_tool = dummy    ' ist ein iiTool
					If (Not dh_tool Is Nothing) Then 
					    If (dh_tool.ToolType=tDriller) Then
							' nur Bohrer
						    toolno = T.T_DH.DrillingHead.ToolPlaces.GetToolPlace_Index(j).ToolNo
						    maxrot = dh_tool.GetFirstCuttingEdge.MaxRotSpeed
						    length=dh_tool.GetFirstCuttingEdge.Length
						    rad= dh_tool.GetFirstCuttingEdge.Radius   
						    Len1=0
						    Len2=0
						    Len3=0
						    If T.T_DH.DrillingHead.ToolPlaces.GetToolPlace_Index(j).Orientation=orVertical Then 
						    	' vertikaler Ausgang Bohrerlänge auf Länge 1 schreiben
						       Len1= length
						    ElseIf T.T_DH.DrillingHead.ToolPlaces.GetToolPlace_Index(j).Orientation=orYPlus Then 
						    	' hor. Ausgang Y+
						    	Len2 = - length
						    ElseIf T.T_DH.DrillingHead.ToolPlaces.GetToolPlace_Index(j).Orientation=orYMinus Then 
						    	' hor. Ausgang Y-
						    	Len2 = length
						    ElseIf T.T_DH.DrillingHead.ToolPlaces.GetToolPlace_Index(j).Orientation=orXPlus Then 
						    	' hor. Ausgang X+
						    	Len3 = -length
						    ElseIf T.T_DH.DrillingHead.ToolPlaces.GetToolPlace_Index(j).Orientation=orXMinus Then 
						    	' hor. Ausgang X-
						    	Len3 = length
						    Else
						    	' Fehler
						    	AddMistake("Fehler bei Bohrdaten unerlaubte Orientation vom BohrkopfAusgang")
						    End If
  							wcnc(SPF_TCheck+"("+inttos(T.t.ID)+","+inttos(toolno)+ _
  							  ","+inttos(1)+","+inttos(maxrot)+","+ftos(rad)+","+ftos(Len1)+","+ftos(Len2)+","+ftos(Len3)+")" )
					    End If
					End If
				Next
			ElseIf MT_isDHSaw(T) Then
				' NutSäge auf Bohrkopf - 
				' Referenzpunkt ist Sägeblatt- Mitte deshalb muss die Länge über
				' Länge-SD/2 berrechnet werden und entsprechend auf Länge2 bzw. Länge 3 zu schreiben
				length=T.t.Length - T.t.SawThickness/2
				Len1=0    ' t.t.Radius  - Radius wird von Postprozessor verrechnet
				Len2=0
				Len3=0
			    If T.T_DHSaw.DH_ToolPlace.Orientation=orYPlus Then 
			    	' hor. Ausgang Y+
			    	Len2 = - length
			    ElseIf T.T_DHSaw.DH_ToolPlace.Orientation=orYMinus Then 
			    	' hor. Ausgang Y-
			    	Len2 = length
			    ElseIf T.T_DHSaw.DH_ToolPlace.Orientation=orXPlus Then 
			    	' hor. Ausgang X+
			    	Len3 = -length
			    ElseIf T.T_DHSaw.DH_ToolPlace.Orientation=orXMinus Then 
			    	' hor. Ausgang X-
			    	Len3 = length
			    Else
			    	' Fehler
			    	AddMistake("Fehler bei Nutsäge Bohrkopf - unerlaubte Orientation vom Bohrkopf/Sägeausgang")
			    End If

				wcnc(SPF_TCheck+"("+inttos(T.t.ID)+","+inttos(T.t.ToolNo)+","+inttos(T.h_add.CorrNo)+","+inttos(T.t.MaxRotSpeed)+","+ftos(T.t.Radius)+","+ftos(Len1)+","+ftos(Len2)+","+ftos(Len3)+")")
			ElseIf MT_IsGearBoxTool(T) Then
				
				If T.t_gb.Tool.ToolType=tSaw Then
					' Sonderfall Säge Länge 1 mit Sägeblattbreite verrechnet
					wcncaddcom(SPF_TCheck+"("+inttos(T.t.ID)+","+inttos(T.t.ToolNo)+","+inttos(T.h_add.CorrNo)+","+inttos(T.t.MaxRotSpeed)+","+ftos(T.t.Radius)+","+ftos(T.t.Length-T.t.SawThickness/2)+","+ftos(0)+","+ftos(0)+")","S"+ftos(T.t.MaxRotSpeed)+" R"+ftos(T.t.Radius)+" L1:"+ftos(T.t.Length-T.t.SawThickness/2)+" L2:"+ftos(0)+" L3:"+ftos(0))
				Else
					wcncaddcom(SPF_TCheck+"("+inttos(T.t.ID)+","+inttos(T.t.ToolNo)+","+inttos(T.h_add.CorrNo)+","+inttos(T.t.MaxRotSpeed)+","+ftos(T.t.Radius)+","+ftos(T.t.Length)+","+ftos(0)+","+ftos(0)+")","S"+ftos(T.t.MaxRotSpeed)+" R"+ftos(T.t.Radius)+" L1:"+ftos(T.t.Length)+" L2:"+ftos(0)+" L3:"+ftos(0))
				End If
			Else
				' alle übrigen Werkzeuge
				wcnccom("Box:"+strsize(inttos(T.t.ID),5,2)+" HId:"+StrSize(Inttos(T.HId),5,1)+" "+StrSize(T.T.Description,30,1)  + " Platz:"+ strsize(inttos(T.t.GetPlaceID_OnTC),3,0)+" T:"+strsize(inttos(T.H_add.ToolNo),3,0)+" D"+strsize(inttos(T.H_ADD.CorrNo),3,0))
				wcncaddcom(SPF_TCheck+"("+inttos(T.t.ID)+","+inttos(T.t.ToolNo)+","+inttos(T.h_add.CorrNo)+","+inttos(T.t.MaxRotSpeed)+","+ftos(T.t.Radius)+","+ftos(T.t.Length)+","+ftos(0)+","+ftos(0)+")","S"+ftos(T.t.MaxRotSpeed)+" R"+ftos(T.t.Radius)+" L1:"+ftos(T.t.Length)+" L2:"+ftos(0)+" L3:"+ftos(0))
			End If
		End If
		BoxNoArray(i)=T.t.ID
		'LastBoxId=t.t.ID
	Next i
	wcnccom("")
	
End Function


' *****************************************************************************************
' ** Check ob Id in BoxnoArray
' *****************************************************************************************
Function MT_CheckisIdInList(id,BoxNoArray) As Boolean
Dim sBox As Long
Dim i As Long
Dim result As Boolean
	result = False
	
	For i = 0 To UBound(BoxNoArray)-1
		sBox = BoxNoArray(i)
		If id = sBox Then
		   result=True
		   Exit For
		End If
	Next i
	MT_CheckisIdInList = result
End Function


' *****************************************************************************************
' ** Werkzeugwechsel - Abhandlung
' *****************************************************************************************
' t= actt
' spindlecode = 00110101 etc.
' ids = 109,110,112, etc.
Function MT_WZW(pspeed)   '

Dim H_Id As Variant   ' Aggregate Head id 
Dim TC_Id As Variant    ' Tool - Changer Head id 

Dim TC_PlaceNo As Variant   ' Place - No toolchanger
Dim id As Variant   ' Campus - No ID

Dim LiftPosC As Variant   ' Lift - pos c-axis
Dim CanLift As Variant   ' lift aggregate possible

Dim Change_Mode As Variant
'Dim Change_Curve As Variant

Dim xp As Variant   ' X-pos

Dim accel As Variant   ' Achsbeschleunigung

Dim flex_id As Variant   ' fuer Flexkopf die Kennung


Dim offx,offy,offz As Double
	
Dim T As THopsBasicToolExt 
Dim Flex_T As IIHopsBasicTool

Dim Sub_TC_Id As Variant   ' Tool - Changer Head id für HSK F40 sub tool
Dim Sub_TC_PlaceNo As Variant   ' Place - No toolchanger für HSK F40
Dim dr As Long   ' Spindle - Direction
Dim dZ As Long   ' Tool - Speed (programmed speed)
Dim S_Max As Long
Dim Max_ToolSpeed, Min_ToolSpeed As Double    ' vom Werkzeug selbst
Dim Max_HeadSpeed, Min_HeadSpeed As Double	 

	T= ActT
	
	dr = inttos(MT_Get_SpindleDirection(T,pspeed))
	dZ = inttos(Abs(MT_Get_SpindleSpeed(T,pspeed)))
	If Not T.T.GetOn_TC Is Nothing Then
		' Tool - on toolchanger
	ElseIf MT_IsDH(T) Then
		' Drilling Head
		' Tx Dx überschreiben mit korrekter Einstellung	
		'TNo = ""
		'DNo = ""
		dZ = inttos(Abs(MT_Get_SpindleSpeed(T,pspeed)))
	ElseIf MT_isDHSaw(T) Then
		' Nutsäge auf Drilling Head
		If T.t_dhsaw.RotDirection = rdLeft Then
		   dr=3
		ElseIf T.t_dhsaw.RotDirection = rdRight Then
			dr=4
		ElseIf T.t_dhsaw.RotDirection = rdLeftRight Then
		End If
		
		dZ = inttos(Abs(MT_Get_SpindleSpeed(T,ActT.t.RotSpeed)))
		
	ElseIf MT_isPneumaticSaw(T) Then
		' pneumatische Säge
		'MT_GetPneumaticSawAngle(ViewBefore.RotA, raster_angle) 
		'cp =raster_angle		
		
	Else
	End If

	' fix
	H_Id = T.Hid '  Aggregats Head Id
	
	' Flexkopf - Kennung
	If T.T.ObjectType=htokTC_AccessGearBoxTool Then
		' = Werkzeug auf Flexkopf
		id = T.t.ToolNo   '  Campus - internal ID für Flexgetriebe Kennung
		' Neu MW 14.4.2005
		id = T.t.GearBox.ToolNo
		Set Flex_T = TDATA.GetTool_ID(T.t.ID)

	Else
		id = T.t.ID   '  Campus - No ID
	End If
	
	TC_Id = ""   ' toolchanger Head ID
	TC_PlaceNo = ""
	LiftPosC = ""
	CanLift = ""
	
	Change_Mode = MT_Get_TCMode
	xp = ""
	
	If Not T.T.GetOn_TC Is Nothing Then
		' Tool - on toolchanger
		TC_Id = T.T.GetOn_TC.HeadID
		TC_PlaceNo = T.t.GetPlaceID_OnTC 't.T.ToolNo_Place
	ElseIf T.T.ObjectType=2 Then
		' Drilling Head
		
		'offx = MT_Get_BasicToolPlace_OffsetX(ActT.t,Ids)  ' gets offset x of the first driller in row
		'offy = MT_Get_BasicToolPlace_OffsetY(ActT.t,Ids)  ' gets offset y of the first driller in row
		'offz = MT_Get_BasicToolPlace_OffsetZ(ActT.t,Ids)  ' gets offset z of the first driller in row
		
		xp = FTos(ActV.SPVX+offx)
	End If
	
	' Achtung Sicherheit nur möglich, wenn reale Werkzeugdaten bekannt
	' sind. Momentan ist T-Nummer = Platznummer
	'zs = t.T.GetSecurityZ(ViewBefore.TipA)
	
	CanLift = IIf(T.T.CanLift,1,0)
	If CanLift Then
		LiftPosC= T.T.PosCForLift
	End If
	
	' Achsbeschleunigung aus der Schneide holen
	If Not T.t_cedge Is Nothing Then	
		' todo - gilt nicht für Bohrkopf
		accel = T.T_Cedge.AxisSpeedUp
	End If
	
	
	' Flexkopf - Kennung
	If T.T.ObjectType=htokTC_AccessGearBoxTool Then
		flex_id=1    ' momentan wird nur 1 Flexwerkzeug unterstützt
	Else
		flex_id=""
	End If
	If MT_IsProcessHeadTool(ActT) Then
		' Fixe Fräs/Bohrmotoren
		If GSiemens840DType=1 Then
			WcncAddCom("C_TSL("+IntToS(T.H_Add.ToolNo)+","+IntToS(Abs(T.t.MaxRotSpeed))+")","Set Speed limits for next Tool!")
		End If
		If ActT.H_Add.ToolChangeType=0 Then
			wcnc(GToolChangeCycleName+"("+inttos(T.H_Add.ToolNo)+","+Inttos(dr)+","+inttos(dZ)+")")
		ElseIf ActT.H_Add.ToolChangeType=1 Then
			wcnc(GToolChangeCycleName+"("+inttos(T.H_Add.ToolNo)+","+Inttos(dr)+","+inttos(dZ)+",,)")
		ElseIf ActT.H_Add.ToolChangeType=2 Then
			AddMistake("ToolChangeMode 2 nicht zulässig!")
			wcnc(GToolChangeCycleName+"("+inttos(T.H_Add.ToolNo)+","+Inttos(dr)+","+inttos(dZ)+","+Ftos(TDATA.MachineData.OffsetX+JobPara.NPX+ViewBefore.SPVX)+","+FTOS(TDATA.MachineData.OffsetY+JobPara.NPY+ViewBefore.SPVY)+")")
		Else 
			AddMistake("ToolChangeMode nicht zulässig!")
		End If 
		'wcnc("Wechsel("+inttos(199+ActT.hid)+","+Inttos(dr)+","+inttos(dZ)+")")
	ElseIf (ActT.H_Add.ToolChangeMode=1) Or (MT_IsGearBoxTool_Special_Vertical(ActT)) Or (MT_Is_UndersideTool(ActT)) Then
		' Werkzeugwechsel - Programm Version #1 
		If GSiemens840DType=1 Then
			WcncAddCom("C_TSL("+IntToS(TC_PlaceNo)+","+IntToS(Abs(T.t.MaxRotSpeed))+")","Set Speed limits for next Tool!")
		End If
		'If ViewBefore.SPVX ViewBefore.SPVY
		If ActT.H_Add.ToolChangeType=0 Then
			wcnc(GToolChangeCycleName+"("+inttos(TC_PlaceNo)+","+Inttos(dr)+","+inttos(dZ)+")")
		ElseIf ActT.H_Add.ToolChangeType=1 Then
			
			wcnc(GToolChangeCycleName+"("+inttos(TC_PlaceNo)+","+Inttos(dr)+","+inttos(dZ)+",,)")
		ElseIf ActT.H_Add.ToolChangeType=2 Then
			wcnc(GToolChangeCycleName+"("+inttos(TC_PlaceNo)+","+Inttos(dr)+","+inttos(dZ)+","+Ftos(TDATA.MachineData.OffsetX+JobPara.NPX+ViewBefore.SPVX)+","+FTOS(TDATA.MachineData.OffsetY+JobPara.NPY+ViewBefore.SPVY)+")")
		ElseIf ActT.H_Add.ToolChangeType=3 Then
			If Not(TCB_T.T)Is Nothing Then
				If MT_Is_TC_T(TCB_T) And (Lastt.t)Is Nothing Then
					wcnc(GToolChangeCycleName+"("+inttos(TC_PlaceNo)+","+Inttos(dr)+","+inttos(dZ)+","+Inttos(TCB_T.t.GetPlaceID_OnTC)+")")
				ElseIf MT_Is_TC_T(TCB_T) Then
					'If (Lastt.t.GetPlaceID_OnTC<>TCB_T.t.GetPlaceID_OnTC)And (Actt.t.GetPlaceID_OnTC<>TCB_T.t.GetPlaceID_OnTC) Then
					If(Actt.t.GetPlaceID_OnTC<>TCB_T.t.GetPlaceID_OnTC) Then
						wcnc(GToolChangeCycleName+"("+inttos(TC_PlaceNo)+","+Inttos(dr)+","+inttos(dZ)+","+Inttos(TCB_T.t.GetPlaceID_OnTC)+")")
					Else
						wcnc(GToolChangeCycleName+"("+inttos(TC_PlaceNo)+","+Inttos(dr)+","+inttos(dZ)+")")
					End If	
				Else
					wcnc(GToolChangeCycleName+"("+inttos(TC_PlaceNo)+","+Inttos(dr)+","+inttos(dZ)+")")
				End If
			Else
				wcnc(GToolChangeCycleName+"("+inttos(TC_PlaceNo)+","+Inttos(dr)+","+inttos(dZ)+")")
			End If
		ElseIf ActT.H_Add.ToolChangeType=4 Then
			wcnc(GToolChangeCycleName+"("+inttos(TC_PlaceNo)+","+Inttos(dr)+","+inttos(dZ)+","+FTOS(TDATA.MachineData.OffsetX+JobPara.NPX+ViewBefore.SPVX)+","+FTOS(TDATA.MachineData.OffsetY+JobPara.NPY+ViewBefore.SPVY)+","+FTOS(ActT.HId)+")")
			
			Call WCNC_VORWECHSEL()
		ElseIf ActT.H_Add.ToolChangeType=5 Then
			If is_WorkC_OptionBit(CheckToolOnChange,JobPara.WorkC_OptionBit) Then
				wcnc(GToolChangeCycleName+"("+inttos(TC_PlaceNo)+","+Inttos(dr)+","+inttos(dZ)+",1)")
			Else
				wcnc(GToolChangeCycleName+"("+inttos(TC_PlaceNo)+","+Inttos(dr)+","+inttos(dZ)+",0)")
			End If
		Else 
			AddMistake("ToolChangeMode nicht zulässig!")
		End If 
	ElseIf (ActT.H_Add.ToolChangeMode=0) And MT_IsSpecialToolKind_Printer(ActT.t) Then
		'Drucker
		MT_IsSpecialToolKind_Printer(ActT.t)
	Else
		AddMistake("Error toolchangemode " + ActT.t.Description + ".. Not Found")
	End If
	
	'MT_WRITE_WZW(H_Id,TC_Id,TC_PlaceNo,ID,LiftPosC,CanLift,Change_Mode,xp,accel,flex_id)
	
End Function



' *****************************************************************************************
' ** Werkzeugwechsel - Speed Abhandlung
' *****************************************************************************************

Function MT_Write_Speed(T As THopsBasicToolExt,pspeed)   '

Dim H_Id As Long   ' Aggregate Head id 
Dim H_Typ As String  ' Aggregate Typ
Dim TNo As Variant   ' Tool - T-No
Dim DNo As Variant   ' Tool - D-No

Dim dr As Long   ' Spindle - Direction
Dim dZ As Long   ' Tool - Speed (programmed speed)

Dim xp As Variant   ' X-pos während Spindel - Anlauf
Dim yp As Variant   ' Y-pos während Spindel - Anlauf
Dim zp As Variant   ' Z-pos während Spindel - Anlauf
Dim cp As Variant   ' C-pos während Spindel - Anlauf bzw. Raster - Position der pneum. Säge


Dim offx,offy,offz As Double   ' actual Tool - offset for axis prepositioning
Dim Raster_Angle As Double


	H_Id = T.Hid '  
	H_Typ = "" 
	
	TNo = inttos(T.h_add.ToolNo)
	DNo = inttos(T.h_add.CorrNo)
	
	dr = inttos(MT_Get_SpindleDirection(T,pspeed))
	dZ = inttos(Abs(MT_Get_SpindleSpeed(T,pspeed)))
	xp = ""
	yp = ""
	zp = ""
	cp = ""
	
	If Not T.T.GetOn_TC Is Nothing Then
		' Tool - on toolchanger
	ElseIf MT_IsDH(T) Then
		' Drilling Head
		' Tx Dx überschreiben mit korrekter Einstellung	
		TNo = ""
		DNo = ""

		
		'offx = MT_Get_BasicToolPlace_OffsetX(ActT.t,Ids)  ' gets offset x of the first driller in row
		'offy = MT_Get_BasicToolPlace_OffsetY(ActT.t,Ids)  ' gets offset y of the first driller in row
		'offz = MT_Get_BasicToolPlace_OffsetZ(ActT.t,Ids)  ' gets offset z of the first driller in row
		
		'TNo = inttos(MT_Get_First_ToolNo_DH(t.t,Ids))
		'DNo = MT_Get_ActiveCuttingEdge_EdgeId(t.t,Ids)
		'bm = Inttos(BinToDouble(Spindlecode))
		dZ = inttos(Abs(MT_Get_SpindleSpeed(T,pspeed)))
		
		'xp = FTos(ActV.SPVX+offx)
		'yp = FTos(ActV.SPVY+offy)
		If Not Firsttime_Viewchange Then
			'zp = FTos(ActV.SPVZ+offz)
		End If
	ElseIf MT_isDHSaw(T) Then
		' Nutsäge auf Drilling Head
		If T.t_dhsaw.RotDirection = rdLeft Then
		   dr=3
		ElseIf T.t_dhsaw.RotDirection = rdRight Then
			dr=4
		ElseIf T.t_dhsaw.RotDirection = rdLeftRight Then
		End If
		
		dZ = inttos(Abs(MT_Get_SpindleSpeed(T,T.t.RotSpeed)))
		
	ElseIf MT_isPneumaticSaw(T) Then
		' pneumatische Säge
		MT_GetPneumaticSawAngle(T,ViewBefore.RotA, Raster_Angle) 
		cp =Raster_Angle		
		
	Else
	End If
	
	' Achtung Sicherheit nur möglich, wenn reale Werkzeugdaten bekannt
	' sind. Momentan ist T-Nummer = Platznummer
	'zs = t.T.GetSecurityZ(ViewBefore.TipA)
	wcnc("S"+inttos(dZ)+ " M"+inttos(dr))	

	'MT_Speed_Call(H_Id,H_Typ,dr,DZ,xp,yp,zp,cp)

End Function
	


' *****************************************************************************************
' ** Werkzeugwechsel - Abhandlung
' *****************************************************************************************
' t= actt
' spindlecode = 00110101 etc.
' ids = 109,110,112, etc.
Function MT_WRITE_DHCode(T As THopsBasicToolExt,tools)   '
Dim Code As TBMuster

Dim H_Id As Variant   ' Aggregate Head id 
Dim H_Typ As Variant  ' Aggregate Typ
'Dim Group_Id As Variant  ' Gruppen - ID 
						 ' 1 = vertikalspindeln 1-32
						 ' 2 = horizontalspindeln X-Richtung  1-32
						 ' 3 = horizontalspindeln Y-Richtung  1-32 
						 ' 4 = Säge in X-Richtung 1-32
						 ' 5 = Säge in Y-Richtung 1-32


Dim NCStr As String ' String for NC-Prog
Dim Orientation As Variant
Dim one_spindle As Long
Dim FirstTNr As Long
Dim BitMuster1,DrillsUp,DrillsDown As Variant
Dim isok As Boolean
Dim StrG04FUp As Variant
Dim StrG04FDown As Variant

	FirstTNr = Val(Get_First_Token(tools))   



	' fix
	H_Id = T.Hid '  Aggregats Head Id
	
	H_Typ = ""   '  Aggregate Head Typ
	
	If FirstTNr <= 0 Then
		' Werkzeugabwahl
		Code.GroupCode = 0     ' 0=alles zurücksetzen  marker.last_bm.GroupCode
		Code.BM1=0
		Code.BM2=0
		Code.BM3=0
	Else
		' Spindelcodierung anhand angegebener Spindelnummer ermitteln
		' und zurückgeben in Bm1 und BM2, BM3
		MT_Get_SpindleCode_Dez(tools,Code)
		If ActT.t.ObjectType = 7 Then
			' Säge auf Bohrkopf
			Orientation = ActT.t_dhsaw.DH_ToolPlace.Orientation
			If (Orientation=orYPlus) Or (Orientation=orYMinus) Then	
				Code.GroupCode=4
			ElseIf (Orientation=orXPlus) Or (Orientation=orXMinus) Then	
				Code.GroupCode=5
			Else
				AddMistake("Toolchange - Werkzeug Typ Säge mit dieser Orientierung noch nicht berücksichtigt")
			End If
		Else
			Orientation = ActT.t_dh.DrillingHead.ToolPlaces.GetToolPlace_PlaceID(FirstTNr).Orientation
			If (Orientation=orVertical) Then	
				Code.GroupCode=1
			ElseIf (Orientation=orYPlus) Or (Orientation=orYMinus) Then	
				Code.GroupCode=3
			ElseIf (Orientation=orXPlus) Or (Orientation=orXMinus) Then	
				Code.GroupCode=2
			Else
				AddMistake("Toolchange - Werkzeug Typ Säge mit dieser Orientierung noch nicht berücksichtigt")
			End If
		
		End If
	End If
	
	BitMuster1 = MT_get_Add_ID(ActT,10060,isok)
	If isok Then
		NCStr = BitMuster1+"="+IntToS(Code.BM1) '+","+IntToS(Code.BM2)+","+IntToS(Code.BM3)+")"
	Else
	End If
	If Code.BM2>0 Or Code.BM3>0 Then
		AddMistake("Bohrhub- Codierung overflow")
	End If
	If (Code.BM1 <> Marker.last_bm.BM1) Or (Code.BM2 <> Marker.last_bm.BM2) Or (Code.BM3 <> Marker.last_bm.BM3) Then
		DrillsUp = MT_get_Add_ID(ActT,10053,isok)
		If isok Then
			wcncaddcom(DrillsUp,"Spindeln zurücklegen")
		Else
			AddMistake("23423423422")
		End If
		WCNC("STOPRE")
		StrG04FUp = MT_get_Add_ID(ActT,10061,isok)
		If isok Then
			StrG04FUp="G04F"+StrG04FUp
		Else
			AddMistake("248677325")
		End If
		StrG04FDown = MT_get_Add_ID(ActT,10062,isok)
		If isok Then
			StrG04FDown="G04F"+StrG04FDown
		Else
			AddMistake("248677325")
		End If
		If Code.BM1 <> 0 Then
			wcnccom("Bohrer vorlegen")
		Else
			wcnccom("alle Bohrspindeln zurücklegen")
		End If
		wcnc(NCStr)
    	'wcnccom("BM1:"+ftos(Code.BM1))
	    If Code.BM2>0 Then
	    	'wcnccom(" * BM2:"+ftos(Code.BM2))
	    End If
	    If Code.BM3>0 Then
	    	'wcnccom(" * BM3:"+ftos(Code.BM3))
	    End If
		' evtl. Überprüfung, ob Bohrkopf -bohrer vorgelegt etc.
		'MT_Write_Check_Spindle
		' 
		If Code.BM1<=0 Then
			' dann zurücklegen
			DrillsUp = MT_get_Add_ID(actt,10053,isok)
			If isok Then
			    wcncaddcom(DrillsUp,"Spindeln zurücklegen")
			Else
				AddMistake("23423423422")
			End If
			wcnc(StrG04FUp)  ' Neu 17.03.2006
		    'wcncaddcom("G4F.5","")
		    wcncaddcom("STOPRE","")
		Else
			DrillsDown = MT_get_Add_ID(actt,10052,isok)
			If isok Then
			    wcncaddcom(DrillsDown,"Spindeln vorlegen")
			Else
				AddMistake("2342323423423")
			End If
			wcnc(StrG04FDown)  ' Neu 17.03.2006
		    'wcncaddcom("G4F.5","")
		    wcncaddcom("STOPRE","")
		End If
	End If
	Marker.Last_Bm.BM1 = Code.BM1
	Marker.Last_Bm.BM2 = Code.BM2
	Marker.Last_Bm.BM3 = Code.BM3
	Marker.Last_Bm.GroupCode = Code.GroupCode
	
	PosReset
End Function


Function MT_Speed_Call(Hid,HTyp,dr,dZ,xp,yp,zp,cp)
Dim NCStr As String ' String for NC-Prog

	'wcnccom("Hid:"+inttos(Hid)+" HTyp:"+inttos(wn)+" TNo:"+inttos(tn)+" DNo:"+inttos(dn)+" DrehRicht:"+inttos(dr)+" Drehzahl:"+inttos(dz)+")")
	NCStr = SPF_TSpeed+"("+IntToS(Hid)+","+IntToS(dr)+","+IntToS(dZ)+","+IntToS(xp)+","+IntToS(yp)+","+IntToS(zp)+","+IntToS(cp)+")"
	wcnc(NCStr)

	
End Function


' *****************************************************************************************
' ** Ermittlung Spindle - Ausgangsdrehzahl über Übersetzung etc.
' ** zusätzlich Überprüfung Min - Max - Speed findet in Plausi statt
' *****************************************************************************************
Function MT_Get_SpindleSpeed(T As tHopsBasicToolExt,pspeed)
Dim OutPut_Spindle As Double


Dim Max_ToolSpeed, Min_ToolSpeed As Double    ' vom Werkzeug selbst
Dim Max_HeadSpeed, Min_HeadSpeed As Double	  ' vom Bearbeitungskopf

	MT_GetMinMaxToolSpeed(T,Min_ToolSpeed,Max_ToolSpeed)

	MT_GetMinMaxHeadSpeed(T,Min_HeadSpeed,Max_HeadSpeed)


    OutPut_Spindle=Abs(T.t.GetRotSpeed(pspeed))    ' 	gets transmission ratio 
    
    If T.T.ObjectType=htokStandardTool Then	
    	' -- Neu MW 30.3.2005
    	' -- check Spindeldrehzahl für "normale" Werkzeuge Schaftfräser etc.
    	
    	' 1. Werkzeugdrehgeschwindigkeit checken!
    	If OutPut_Spindle > Max_HeadSpeed Then
    	   OutPut_Spindle = Max_HeadSpeed
    	End If
    	If OutPut_Spindle < Min_HeadSpeed Then
    	   OutPut_Spindle = Min_HeadSpeed
    	End If
    
    End If

	' kommt evtl. auch negativ zurück  - 27.04.2006 kommt wohl immer positiv zurück 
	' -- Neu MW 10.11.2006
    OutPut_Spindle=T.t.GetRotSpeed(pspeed)    ' 	gets transmission ratio - direction 
	'If T.t.RotDirection=rdLeft Then
	'	OutPut_Spindle = - Abs(OutPut_Spindle)
	'Else			
	'	OutPut_Spindle = Abs(OutPut_Spindle)
	'End If
	' --
 

    MT_Get_SpindleSpeed=(OutPut_Spindle)
End Function


' *****************************************************************************************
' ** Ermittlung Spindle - Ausgangsdrehzahl über Übersetzung etc.
' ** zusätzlich Überprüfung Min - Max - Speed
' *****************************************************************************************
Function MT_Get_SpindleDirection(T As tHopsBasicToolExt,pspeed)
Dim direction As Integer

	If MT_Get_SpindleSpeed(T,pspeed) < 0 Then
		direction = 4
	Else
		direction = 3
	End If
	
	MT_Get_SpindleDirection = direction
End Function


Function MT_GetMinMaxToolSpeed(T As tHopsBasicToolExt,Min_ToolSpeed,Max_ToolSpeed)

	If T.t.ObjectType=htokDrillingHeadTool Then
		Min_ToolSpeed = T.t.MinRotSpeed	
		Max_ToolSpeed = T.t.MaxRotSpeed	
	ElseIf T.T.ObjectType=htokDH_SawTool Then	
		' Es handelt sich um ein Groove Saw on DrillingHead ' ObjectType = 7
		Min_ToolSpeed = T.t.MinRotSpeed	
		Max_ToolSpeed = T.t.MaxRotSpeed	
		
	Else
		Min_ToolSpeed = T.t.MinRotSpeed	
		Max_ToolSpeed = T.t.MaxRotSpeed	
	
	End If
End Function


Function MT_GetMinMaxHeadSpeed(T As tHopsBasicToolExt,Min_HeadSpeed,Max_HeadSpeed)

	If T.t.ObjectType=htokDrillingHeadTool Then
		Min_HeadSpeed = T.t_dh.SpindleMinRotSpeed	
		Max_HeadSpeed = T.t_Dh.SpindleMaxRotSpeed	
	ElseIf T.T.ObjectType=htokDH_SawTool Then	
		' Es handelt sich um ein Groove Saw on DrillingHead ' ObjectType = 7
		Min_HeadSpeed = T.T_DHSaw.SpindleMinRotSpeed	
		Max_HeadSpeed = T.T_DHSaw.SpindleMaxRotSpeed	
		
	Else
		Min_HeadSpeed = T.h.MinRotSpeed	
		Max_HeadSpeed = T.h.MaxRotSpeed	
	
	End If
End Function


Function MT_Write_Act_D_Correction
	If ActT.h_add.CorrNo < 8 Then
		wcnc("D"+IntToS(ActT.h_add.CorrNo))
	Else
		AddMistake("unerlaubte D-Nummer bitte Werkzeugverwaltung überprüfen")
	End If
End Function

Function MT_Write_Act_T_Correction
	'wcnc("T"+IntToS(ActT.T.ToolNo))
	'wcnc("T"+IntToS(ActT.T.GetPlaceID_OnTC))
	wcnc("T"+IntToS(ActT.H_Add.ToolNo))

End Function



Function MssssT_Get_ActiveCuttingEdge_EdgeId(T As IIHopsBasicTool,id) 
Dim BTP As IIBasicToolPlace
Dim DHT As IIHopsDrillingHeadTool
Dim ICE As IICuttingEdge
Dim tdummy As Object


Dim Tx As Variant

	Set tx = T
	If Tx.ObjectType=2 Then	
		Set DHT = Tx
		If Not DHT Is Nothing Then
		
			Set BTP = DHT.DrillingHead.ToolPlaces.GetToolPlace_PlaceID(Val(Get_First_Token(id)))
			Set tdummy = BTP.ActiveTool
			
			
			Set ICE = tdummy.GetCuttingEdge_Index(0)
			
			
			
			MssssT_Get_ActiveCuttingEdge_EdgeId = ICE.EdgeID
		End If
	Else
		AddMistake("Cutting edge DH not found")
	End If
	
	
End Function


'Function MT_Get_DrillingHeadToolPlace(T As IIHopsBasicTool,ID) As IIBasicToolPlace

'Dim DHT As IIHopsDrillingHeadTool
'Dim Tx As Variant
'	Set Tx = T

'	If Tx.ObjectType=2 Then	
'		Set DHT = Tx   'TDATA.GetTool_ID(T.ID)
'		If Not DHT Is Nothing Then
		
'			Set MT_Get_DrillingHeadToolPlace = DHT.DrillingHead.ToolPlaces.GetToolPlace_PlaceID(ID)
'		End If
'	Else
'		Set MT_Get_DrillingHeadToolPlace = Nothing 
'	End If
	
	
'End Function



' -- gibt die 1. ToolNummern  zurück
'Function MT_Get_First_ToolNo_DH(T As IIHopsBasicTool,ID) As String  
'Dim IBTP As IIBasicToolPlace
'Dim i As Long
'Dim result As String
'Dim Stri As String
	
'	Stri = ""
'	result = ""
'	For i = 1 To Len(ID) 	
'		If (Mid(ID,i,1) = ";") Then
'			' ; found
'			'
'			Set IBTP=MT_Get_DrillingHeadToolPlace(T,Stri)
'			result=result + inttos(IBTP.ToolNo)
'			Stri=""
'			Exit For
'		Else
'			Stri = Stri + Mid(ID,i,1)
'		End If
'	Next i
'	If Stri <> "" Then
'			' ; found
'			'
'			Set IBTP=MT_Get_DrillingHeadToolPlace(T,Stri)
'			result=result + inttos(IBTP.ToolNo)
'	End If
'	MT_Get_First_ToolNo_DH = result
'End Function


'Function MT_Get_BasicToolPlace_OffsetX(T As IIHopsBasicTool,Ids) As Double
'Dim IBTP As IIBasicToolPlace
'Dim result As Double
'
'	Set IBTP=MT_Get_DrillingHeadToolPlace(T,Get_First_Token(Ids))
'	result= IBTP.OffsetX
'	MT_Get_BasicToolPlace_OffsetX = result

	
'End Function

'Function MT_Get_BasicToolPlace_OffsetY(T As IIHopsBasicTool,Ids) As Double
'Dim IBTP As IIBasicToolPlace
'Dim result As Double
'
'	Set IBTP=MT_Get_DrillingHeadToolPlace(T,Get_First_Token(Ids))
'	result= IBTP.OffsetY
'	MT_Get_BasicToolPlace_OffsetY = result

	
'End Function


'Function MT_Get_BasicToolPlace_OffsetZ(T As IIHopsBasicTool,Ids) As Double
'Dim IBTP As IIBasicToolPlace
'Dim result As Double
'
'	Set IBTP=MT_Get_DrillingHeadToolPlace(T,Get_First_Token(Ids))
'	result= IBTP.OffsetZ
'	MT_Get_BasicToolPlace_OffsetZ = result

	
'End Function

' ------------------------------------------------------------------------------------------
' -- Function/Definitions  Tooltypes
' ------------------------------------------------------------------------------------------

' Bohrkopf
'Function MT_isDH_OK(T As tHopsBasicToolExt)
'	MT_isDH_OK = False
'	If Not T.t_dh Is Nothing Then
'		MT_isDH_OK= ((T.t.ObjectType=2)) 
'	End If
'End Function


' Säge auf Bohrkopf
Function MT_isDHSaw(T As tHopsBasicToolExt)
	MT_isDHSaw = False
	If Not T.T_DHSaw Is Nothing Then
		MT_isDHSaw= ((T.t.ObjectType=7)) 
	End If
End Function


Function MT_Is_TC_T(T As tHopsBasicToolExt)
	MT_Is_TC_T = False
	If Not T.t.GetOn_TC Is Nothing Then
		MT_Is_TC_T= True
	End If
End Function



' -------------------------------------------------------------------------
' Überprüfungsroutine, ob vorheriges Tool und aktuelles Tool vom Bohrkopf
' Säge auf Bohrkopf !!!!
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
Function MT_isPrinter_wasPrinter(act As THopsBasicToolExt ,last As THopsBasicToolExt)
Dim result As Boolean
	result = False
	If (MT_IsSpecialToolKind_Printer(last.t) And MT_IsSpecialToolKind_Printer(act.t)) Then
 		result = True
 	End If
	 MT_isPrinter_wasPrinter = result
	
End Function
' -- pneumatische Säge
Function MT_isPneumaticSaw(T As tHopsBasicToolExt)
	MT_isPneumaticSaw = False
	If Not T.T_PH Is Nothing Then
		MT_isPneumaticSaw= (T.t.ObjectType=3) And (T.t.AggNo=90)
	End If
End Function

' -------------------------------------------------------------------------
' Überprüfungsroutine, ob vorheriges Tool und aktuelles Tool pneumatisch Säge
' -------------------------------------------------------------------------

Function MT_isDH_wasPneumaticSaw(act As THopsBasicToolExt ,last As THopsBasicToolExt)
Dim result As Boolean
	result = False
	If (MT_isPneumaticSaw(last) And MT_isPneumaticSaw(act)) Then 
 		result = True
 	End If
	MT_isDH_wasPneumaticSaw = result
	
End Function

' -------------------------------------------------------------------------
' Überprüfungsroutine, ob Tool ein Sägeblatt ist
' -------------------------------------------------------------------------
Function MT_isSaw(T As tHopsBasicToolExt) As Boolean

	MT_isSaw = False
	If Not T.T_GB Is Nothing Then
		MT_isSaw= (T.t_gb.Tool.ToolType = tSaw)
	End If
End Function



Function MT_IsSpecialToolKind_Laser(Tool As IIHopsBasicTool)

	MT_IsSpecialToolKind_Laser=False
	
	If Tool.ObjectType=5 Then
		' IhopsSpecialTool
		MT_IsSpecialToolKind_Laser = True
	End If
End Function
Function MT_IsSpecialToolKind_Printer(Tool As IIHopsBasicTool)
	MT_IsSpecialToolKind_Printer=False
	
	If Tool.ObjectType=3 And Tool.ID=11111 And Tool.AggNo=2 Then
		' IhopsSpecialTool
		MT_IsSpecialToolKind_Printer = True
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
		' 26.10.2007 - Winkelgetriebe auf 5-Achs
		If (rot = atFree) And ((tip = atFix) Or (tip=atFree) )Then
		    ' Drehachse frei
			MT_Is_Vertical_Rot_Axis = True
		End If
		
	End If
		


End Function

' *****************************************************************************************
' ** Handelt es sich um Standardwerkzeug aus Wechsler 5-Achs 
' *****************************************************************************************
Function MT_Is_Vertical_StandardTool5Axis(T As THopsBasicToolExt)
Dim erg As Boolean
	erg = False
	If (Not T.t Is Nothing)  Then
	If T.t.ObjectType=1 Then 
		If (T.h.TipType=atFree) And (T.h.RotType=atFree) Then
			erg = True
		End If
	End If
	MT_Is_Vertical_StandardTool5Axis = erg
	End If
	
End Function


' *****************************************************************************************
' ** Handelt es sich um Standardwerkzeug aus Wechsler 3-Achs oder 4-Achs
' *****************************************************************************************
Function MT_Is_Vertical_StandardTool(T As THopsBasicToolExt)
Dim erg As Boolean
	erg = False
	If T.t.ObjectType=1 Then 
		If (T.h.TipType=atFix) And  ( (T.h.RotType=atFix) Or (T.h.RotType=atFree) ) Then
			erg = True
		End If
	End If
	MT_Is_Vertical_StandardTool = erg
End Function

' *****************************************************************************************
' ** Handelt es sich um ein Bohrkopf - Tool
' *****************************************************************************************
Function MT_IsDH(T As THopsBasicToolExt)
	If Not T.t_dh Is Nothing Then
		MT_IsDH = (T.t.ObjectType=2)
	End If

End Function
Function MT_IsDHType(T As THopsBasicToolExt)
	MT_IsDHType=0
	If Not T.t_dh Is Nothing Then
		'RotA Fix
	    If T.dh.RotType=0 Then
			MT_IsDHType = 1
		ElseIf T.dh.RotType=1 Then
			'RotA Raster
			MT_IsDHType = 2
		ElseIf T.dh.RotType=2 Then
			'RotA Frei
			MT_IsDHType = 3
		Else
			AddMistake("Unknowen DrillingHeadType")
		End If
		
	End If

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
' ** Winkelgetriebe mit 5. Achse
' *****************************************************************************************
Function MT_IsGearBoxTool_5thAxis(T As THopsBasicToolExt)
	
	' wenn True dann ist es ein Winkelgetriebe
	MT_IsGearBoxTool_5thAxis = (T.t.ObjectType=htokTC_AccessGearBoxTool)

End Function
Function MT_IsAnyGearboxTool (T As THopsBasicToolExt)
	Dim result As Boolean 
	result=False
	If MT_IsGearBoxTool_5thAxis(T) Then
		result=True
	ElseIf MT_IsGearBoxTool(T) Then
		result=True
	ElseIf MT_IsGearBoxTool_Special_Horizontal(T) Then
		result=True
	ElseIf MT_IsGearBoxTool_Special_Vertical(T) Then
		result=True
	ElseIf MT_IsGearBoxTool_Special(T) Then
		result=True
	ElseIf MT_Is_UndersideTool(T) Then	
		result=True
	End If
	
	
	
	MT_IsAnyGearboxTool=result
End Function
' *****************************************************************************************
' ** Nebenaggregat
' *****************************************************************************************
Function MT_IsProcessHeadTool(T As THopsBasicToolExt)
	
	MT_IsProcessHeadTool = (T.t.ObjectType=3)

End Function


' *****************************************************************************************
' ** Alle Werkzeugwechselspindeln mit dem 1. Werkzeug rüsten
' ** !!! -> außer actt welches anschließend benutzt wird
' ** oder, wenn 1. Werkzeug ein Werkzeug ist welches Lift = 0 hat
' *****************************************************************************************

Function MT_Fill_All_TC_Tools(ToolIH As THopsBasicToolExt)


Dim Hid As Variant   ' Head id 
Dim wn As Variant   ' Tool - Changer Head id 
Dim pn As Variant   ' Place - No 
Dim tn As Variant   ' Tool - No 
'Dim dn As Variant   ' Edge - No
'Dim dr As Variant   ' Spindle - Direction
'Dim dz As Variant   ' Tool - Speed
'Dim xp As Variant   ' X-pos
'Dim yp As Variant   ' Y-pos
'Dim zp As Variant   ' Z-pos
'Dim cp As Variant   ' C-pos
'Dim zs As Variant   ' safety z 
Dim cs As Variant   ' Lift - pos c-axis
Dim hz As Variant   ' lift aggregate possible
'Dim bm As Variant   ' bits for drilling head


Dim i As Long
Dim IProHL As IIProcessHead
Dim FirstUsedTool As THopsBasicToolExt   ' für 1. benutztes Werkzeug auf der Spindel

Dim id As Variant
Dim t_array() As Integer



Exit Function
' ein paar Feinheiten fehlen noch
' es muss noch überprüft werden, ob z.B. das 1. Werkzeug für beide Spindeln
' dasselbe ist. 
' Im Falle eines Winkelgetriebes, muss über die Gearbox-ID gecheckt werden, ob
' das Werkzeug bereits auf der anderen Spindel vorgewechselt wurde!

	' ------------------------------------------------------
	' -- alle vorhandenen Werkzeugwechselspindeln durchgehen 
	' -- (die welche auf einen Wechsler zugreifen können)
	' ------------------------------------------------------
	For i = 0 To TDATA.GetProcessHeadList_TC.Count -1
		' -- i = 1.,2.,3. HauptSpindel
		Set IProHL = TDATA.GetProcessHeadList_TC.GetProcessHead_Index(i)
		
		Hid = IProHL.HeadID		' Kopf Id der jetzigen Hauptspindel
		If Hid <> ToolIH.hid Then
			' -- 
			' -- Gefunden Hauptspindel ist nicht an der 1. Bearbeitung
			' -- im Programm beteiligt
			' --
			' -- Spindel mit 1. benutzten Werkzeug füllen, falls an einer Bearbeitun beteiligt 
			' -- 1. benutztes Werkzeug ermitteln über Function MT_Get_FirstUsedTool
			If MT_Get_FirstUsedToolBoxNo(Hid)>0 Then
				MT_SetTHopsBasicToolExt(FirstUsedTool,MT_Get_FirstUsedToolBoxNo(Hid),Hid)
			End If
			'Set FirstUsedTool.T = TDATA.GetTool_ID(MT_Get_FirstUsedTool(Hid))
			'firstUsedTool.Hid = Hid
			If (Not FirstUsedTool.T Is Nothing) Then
				If Not (MT_Is_Tool_Used_Before_From_Another_Head(FirstUsedTool)) Then
					' -- found Spindel mit gefundenem Werkzeug füllen
					'bm = ""  ' drilling Head 
					
					If Not FirstUsedTool.T.GetOn_TC Is Nothing Then
						' Tool - on toolchanger
						tn = FirstUsedTool.T.ToolNo
						pn = FirstUsedTool.T.ToolNo_Place
						wn = FirstUsedTool.T.GetOn_TC.HeadID
					Else
						'MT_AddMistake(1,"falscher Spindeltyp bei Ermittlung Spindel füllen..")
					End If
					
					cs= FirstUsedTool.T.PosCForLift
					hz = IIf(FirstUsedTool.T.CanLift,1,0)

					If equal(hz,0) Then
						' -- Werkzeug kann nicht gehoben werden,
						' -- daher entfällt Werkzeugaufruf
						' tn=-1
						wcnccom("")
						wcnccom("")
						wcnccom("Spindel "+inttos(Hid)+ " "+FirstUsedTool.aggname+ " nicht vorwechseln, da heben nicht zulässig")
						wcnccom("")
						wcnccom("")
					Else
						' -- 1. Werzeug für Spindel einwechseln
						wcnccom("")
						wcnccom("")
						wcnccom("Hid:"+inttos(Hid))
						wcnccom("WNo:"+inttos(wn))
						wcnccom("PNo:"+inttos(pn))
						wcnccom("TNo:"+inttos(tn))
						
						wcnccom("Spindel "+inttos(Hid)+ " "+FirstUsedTool.aggname+" vorwechseln..")
						'MT_WZW_Call(Hid,wn,pn,tn,"","","","","","","","","","","")
						wcnccom("")
						wcnccom("")
						' merker welches Tool bereits benutzt wird, kann in anderer Spindeln nicht auch noch
						' genommen werden
						ReDim tarray(1)
						tarray(0)= tn 
					End If
				End If
			
				
			End If
		End If
	Next i
	

	
End Function



' *****************************************************************************************
' ** Gibt 1. benutztes Werkzeug auf dem Aggregat ("HID") als BoxNummer zurück
' *****************************************************************************************

Function MT_Get_FirstUsedToolBoxNo(Hid)
Dim BoxNo As Long
Dim i As Long

	For i = 0 To UBound(ToolArray)  
		If Hid = ToolArray(i).HId Then
			' -- Werkzeug für Hid gefunden
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
			' -- Werkzeug für Head gefunden
			Exit For
		Else
			' -- 
			' -- check ob das Werkzeug erst noch von einem anderen Head benutzt wird
			' -- 
			If (FirstTool.HID <> ToolArray(i).HId) And (FirstTool.T.ID = ToolArray(i).T.ID) Then
				' -- Werkzeug für anderen Head gefunden - also wird werkzeug
				' -- vorher von einem anderen Bearbeitungskopf benützt
				result = True
				Exit For
			End If
		End If
	Next i
	
	MT_Is_Tool_Used_Before_From_Another_Head = result
	
End Function


' -- gibt ID von 1. Wechselspindel zurück
Function MT_GetFirst_TC_Hid
Dim IProHL As IIProcessHead

	If TDATA.GetProcessHeadList_TC.Count > 0 Then
		Set IProHL = TDATA.GetProcessHeadList_TC.GetProcessHead_Index(0)
		MT_GetFirst_TC_Hid=IProHL.HeadID
	Else
		AddMistake(GetErrMsg(157,"_keine Wechslerspindel gefunden",1))
	End If
	
End Function


Function MT_Tool_Re_Change(T As THopsBasicToolExt,BoxNo)
Dim DrillHeadUp,DrillHeadMotorOff,PrintHeadUp As Variant
Dim isok As Boolean

' T = Lastt
' Actt = aktives Tool
	If Not T.t Is Nothing Then
		If MT_IsDH(T) Or MT_isDHSaw(T) Then
			' bohrkopf war im Einsatz mit Bohren oder mit Sägen
			MT_WRITE_DHCode(T,"")
			DrillHeadUp = MT_get_Add_ID(T,10055,isok)
			If isok Then
				wcncaddcom(DrillHeadUp,"Bohrmotor zurück")
			Else
				AddMistake("69987239204")
			End If
			
			DrillHeadMotorOff = MT_get_Add_ID(T,10051,isok)
			If isok Then
				wcncaddcom(DrillHeadMotorOff,"Bohrmotor aus")
			Else
				AddMistake("699872392204")
			End If
		End If

		If MT_isDH_wasDH(actt,T) Then
			' kein Motor aus bei wechhsel von Bohrkopf Bohren auf Bohrkopf Sägen
			' und keine Motor aus bei wechsel von Bohrkopf Sägen auf Bohrkopf bohren 
			' und keine Motor aus bei wechsel von Bohrkopf Sägen auf Bohrkopf Sägen
		ElseIf MT_isPrinter_wasPrinter(ActT,T) Then
			' Drucker nicht hoch wenn noch zu drucken
			
		Else
			If MT_IsSpecialToolKind_Printer(T.t) Then
				PrintHeadUp=MT_get_Add_ID(T,10155,isok)
				If isok Then
					wcncaddcom(PrintHeadUp,"Drucker zurück")
					Marker.PrinterIsUp=True
				Else
					AddMistake("Unbekannte Add_ID: 10155")
				End If
			End If
			If Not MT_GB_Output_Changed(ActT,T) And Not MT_TEdgeChange(ActT,T) Then
				' bei einem Aggregatsausgang - Wechsel wird Motor nicht abgeschaltet
				'wcnc("M5")
				If (T.h_add.traori) Then
				' 5-Axis mit Traori -
					wcncaddcom(ActT.H_Add.TraoriOff, " 5-Achs - Transformation abschalten")  ' "TRAFOOF"
				End If
				wcnc(Lastt.H_Add.SpindleOff)
				'wcnc("S0")
				If (MT_Is_Vertical_StandardTool5Axis(T)) And (T.h_add.traori) Then
					' 5-Axis mit Traori -
					wcncaddcom(ActT.H_Add.TraoriOff, " 5-Achs - Transformation abschalten")  ' "TRAFOOF"
				End If
			ElseIf ActT.Hid<>T.Hid Then
				If (T.h_add.traori) Then

				' 5-Axis mit Traori -
					wcncaddcom(ActT.H_Add.TraoriOff, " 5-Achs - Transformation abschalten")  ' "TRAFOOF"
				End If
				wcnc(Lastt.H_Add.SpindleOff)
			ElseIf BoxNo<0 Then
				' am Programmende immer S0 erzwingen
				'wcnc(Actt.H_Add.SpindleOff)
				wcnc(aCTT.H_Add.SpindleOff)
				'If (MT_Is_Vertical_StandardTool5Axis(T)) And (T.ph_add.traori) Then
				If (T.h_add.traori) Then

				' 5-Axis mit Traori -
					wcncaddcom(ActT.H_Add.TraoriOff, " 5-Achs - Transformation abschalten")  ' "TRAFOOF"
				End If
			
			End If
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
				AddMistake(GetErrMsg(158,"_Ausgang der Spindel konnte nicht ermittelt werden",1))
			End If
		Else 
			AddMistake(GetErrMsg(158,"_Ausgang der Spindel konnte nicht ermittelt werden",1)+"-2")
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
   		' geändert MW 16.11.2005 
   		OffC = T.T_SGB.GearBox.OffsetC     ' winkelgetriebe Gesamtoffset
   		GbOffC = T.T_SGB.GB_ToolPlace.RotAngle   ' Ausgangsoffset
   		
   
   ElseIf (MT_IsGearBoxTool(T)) Or (MT_IsGearBoxTool_5thAxis(T)) Then

   		OffC = T.T_GB.GearBox.OffsetC     ' winkelgetriebe Gesamtoffset
   		GbOffC = T.T_GB.GB_ToolPlace.RotAngle   ' Ausgangsoffset
   	ElseIf MT_Is_Vertical_StandardTool5Axis(T) Then
   		' 5- Achs
   		MT_Get_RotAxisOffset=0
   		Exit Function
   	ElseIf MT_Is_Vertical_StandardTool(T) Then
   		MT_Get_RotAxisOffset=0
   	Else 
   		AddMistake(GetErrMsg(101,"_falscher Werkzeugtyp",1))
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
				 ret= ActT.t_gb.GearBox.TC_Mode 
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

' 32Bit = 4294967295 = 11111111111111111111111111111111
' 32Bit = 2147483648 = 10000000000000000000000000000000 
' 32Bit = 3221225472 = 11000000000000000000000000000000 
' 32Bit = 2147483647 = 1111111111111111111111111111111   funktioniert
' 32Bit = 2147483648 = 10000000000000000000000000000000
' der 64Bit double kann auf jeden fall mindestens 32Bit

	dummy = tools
	erg = True

	TNr = Val(Get_First_Token(dummy))
	While TNr >0 
		If actt.t.ObjectType = 7 Then
			' Säge auf Bohrkopf
			Set itp= ActT.t_dhsaw.DH_ToolPlace
		Else
			' Bohrer
			Set itp= ActT.t_dh.DrillingHead.ToolPlaces.GetToolPlace_PlaceID(TNr)
		End If
		Set Dh_TP=itp
		
		'If Dh_TP.SpindleNo<=16 Then  'If Dh_TP.SpindleNo<=32 Then
		If Dh_TP.SpindleNo<=16000 Then  'If Dh_TP.SpindleNo<=32 Then
			' MW 31.05.2005 - nur 1 Bitmuster
		 	' Bitmuster 1 füllen
			bm.BM1 = bm.BM1 + exponent2(Dh_TP.SpindleNo)
		ElseIf Dh_TP.SpindleNo<=32 Then   'ElseIf Dh_TP.SpindleNo<=64 Then
		 	' Bitmuster 2 füllen
			bm.BM2 = bm.BM2 + exponent2(Dh_TP.SpindleNo-16)
		ElseIf Dh_TP.SpindleNo<=48 Then
		 	' Bitmuster 3 füllen
			bm.BM3 = bm.BM3 + exponent2(Dh_TP.SpindleNo-32)
		Else
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

Function MT_Get_SpindleCode_Artis(ByVal tools,bm) As Boolean
Dim Dh_TP As IIDH_ToolPlace
Dim itp As Variant
Dim TNr As Long
Dim dummy As String
Dim erg As Boolean
Dim s As Variant


	dummy = tools
	erg = True
    s = " $A_DBD[4]="
	TNr = Val(Get_First_Token(dummy))
	While TNr >0 
		If ActT.t.ObjectType = 7 Then
			' Säge auf Bohrkopf
			Set itp= ActT.t_dhsaw.DH_ToolPlace
		Else
			' Bohrer
			Set itp= ActT.t_dh.DrillingHead.ToolPlaces.GetToolPlace_PlaceID(TNr)
		End If
		Set Dh_TP=itp
		
		s = s + "BS"+Dh_TP.SpindleNo+"+"
		
		
		
		
		If InStr(dummy,";")<=0 Then
		   Exit While
		End If
		
		dummy = Mid(dummy,InStr(dummy,";")+1,Len(dummy)-InStr(dummy,";"))
		TNr = Val(Get_First_Token(dummy))

	Wend
	'MT_Get_SpindleCode_Dez = erg
	
	
	
End Function



' gibt die Winkelstellung zurück, unter der die Säge die Stellung saw_angle erreichen kann
' Säge schwenkbar oder fix
Function MT_GetPneumaticSawAngle(T As THopsBasicToolExt,saw_angle, Raster_Angle As Double) As Boolean
Dim raster_count As Long
Dim i As Long
Dim an As Double
Dim erg As Double
	' Sägewinkel normieren 0-360
	While saw_angle >= 360 
		saw_angle = saw_angle-360 
	Wend
	While saw_angle < 0 
		saw_angle= saw_angle+360
	Wend
	erg = False
	If T.h.RotType=atRaster Then
		' Raster für Sägeschnitt ermitteln
		raster_count = T.h.RotPositions.Count
		For i = 0 To raster_count-1
			an = T.h.RotPositions.GetDouble(i)
			an = an - 90   ' anpassen an Nullstellung 
			an = Norm0_360(an)
			
			If (an = saw_angle) Or ( (an-180)=saw_angle ) Or ( (an+180)=saw_angle ) Then
				' Stellung gefunden
				erg = True
				Raster_Angle = Norm0_360(an + 90)
				Exit For
			End If
		Next
	ElseIf T.h.RotType=atFix Then
		' Fixe Säge nicht schwenkbar - Stellung ermitteln
		an = T.h.RotAngle
		If (saw_angle=an) Then
			' Stellung gefunden ok
			erg = True
			Raster_Angle = an
		End If
		
	End If
	If erg=False Then
		AddMistake(GetErrMsg(159,"_Fehler bei Ermittlung der Sägestellung pneum. Säge",1))
	End If
End Function


Function MT_Write_Check_Spindle
	'wcnc(SPF_AGGCheck)
End Function

Function MT_GB_Output_Changed(ActT As THopsBasicToolExt,LastT As THopsBasicToolExt) As Boolean
	MT_GB_Output_Changed = False
	If (Not LastT.t Is Nothing) And (Not ActT.t Is Nothing) Then
		' check ob Ausgangswechsel auf Aggregat
		If MT_IsGearBoxTool(LastT) And MT_IsGearBoxTool(ActT) Then
			' jetzt Wechsel von Aggregatausgang zu Aggregatausgang
	        If LastT.gb.ToolNo = ActT.gb.ToolNo Then
				MT_GB_Output_Changed = True   ' Wechsel von Ausgang zu Ausgang
	        End If
		End If
	End If
	
End Function

Function MT_Request_Flexible_Axis(ByVal angle)
Dim HeadID As Long
Dim id As Long   ' Flex Kennung momentan nur 1 unterstützt
	HeadID = ActT.hID
	id = 1
	
	wcnc(SPF_REQUEST_FLEX+"("+Inttos(HeadID)+","+inttos(id)+","+ftos(angle)+")")
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
	

	
End Function

Function MT_CheckFeedrate(ActT As THopsBasicToolExt, X,Y,Z,lastx,lasty,lastz,Feedrate) As Double
Dim inf,outf As Boolean  ' eintauch/Austauchvorgang
Dim MaxFeedrate,MinFeedrate As Double  ' min-max Vorschub
Dim result As Double     ' Rückgabewert

	result=Feedrate
	inf=False
	outf = False
	MT_GetMinMaxFeedrate(ActT,MinFeedrate,MaxFeedrate)
	
	If (Z<lastz) Then
		' eintauchvorgang
	   inf = True
	End If
	If (Z>lastz) Then
		' austauchvorgang
	   outf = True
	End If
	
	If (inf Or outf) And (Not equal(X,lastx) Or Not equal(Y,lasty)) Then
		' fliegendes Ein bzw. Austauchen
		' dann beschränken auf Min bzw. Max Vorsch
	Else
		' auf der Stelle runter 
		' oder auf der Stelle hoch
	
	End If
	' 20.4.2005
	' erstmal generell beschränken
	If Feedrate > MaxFeedrate Then
		result=MaxFeedrate
	Else
		If Feedrate< MinFeedrate Then
			result=MinFeedrate
		End If
	End If
	MT_CheckFeedrate = result
	
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
	If PPara.S_Feedrate = ActT.t_dh.MoveOutFeedrate Then
		' vorschub des Bohrkopfs
		dh.VA=ActT.t.MoveOutFeedrate
	Else
		' programmierter Vorschub
	    dh.va=PPara.S_Feedrate
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


Function MT_get_Add_ID(ActT As THopsBasicToolExt,id,isok As Boolean)
Dim Addi As IIAddition
	isok = False
	If ActT.t.ObjectType=htokStandardTool Then
		Set Addi = ActT.h.Additions.GetAddition_ID(id)
	ElseIf ActT.t.ObjectType=htokDrillingHeadTool Then
		Set Addi = ActT.t_dh.DrillingHead.Additions.GetAddition_ID(id)
	ElseIf ActT.t.ObjectType=htokGearBoxTool Then
		Set Addi = ActT.h.Additions.GetAddition_ID(id)
	ElseIf ActT.t.ObjectType=3 Then 'Spezial Kopf
		Set Addi = ActT.h.Additions.GetAddition_ID(id)
	ElseIf ActT.t.ObjectType=5 Then 'Spezial Kopf
		Set Addi = ActT.h.Additions.GetAddition_ID(id)
	Else
		' momentan nur für Hauptspindel und Bohrkopf
		'AddMistake("93847432456")
	End If
	
	If Not Addi Is Nothing Then
		isok = True
		MT_get_Add_ID=Addi.Value
	Else
		'AddMistake("ZusatzInfo ID+"+inttos(id)+" - für Werkzeug "+ActT.t.Description+ ".. nicht gefunden")
	End If
End Function



Function MT_Write_Correction_DH_Drill(Driller As tDriller)
Dim Tnum,DNum As Double
Dim lenz,leny,lenx As Double

	' Tnum = letzter Werkzeugwechselplatz +1
	Tnum = MT_Get_TNum_DrillingHead(ActT)     ' ermittelt die T-Nummer für die Korrektur Bohrkopf
	DNum = MT_Get_DNum_DrillingHead(ActT)     ' ermittelt die D-Nummer für die Korrektur Bohrkopf
	lenx=0
	leny=0
	lenz=0
    If Driller.TP.Orientation=orVertical Then 
    	' vertikaler Ausgang Bohrerlänge auf Länge 1 schreiben
       lenz= Driller.Length
    ElseIf Driller.TP.Orientation=orYPlus Then 
    	' hor. Ausgang Y+
    	leny = - Driller.Length
    ElseIf Driller.TP.Orientation=orYMinus Then 
    	' hor. Ausgang Y-
    	leny = Driller.Length
    ElseIf Driller.TP.Orientation=orXPlus Then 
    	' hor. Ausgang X+
    	lenx = -Driller.Length
    ElseIf Driller.TP.Orientation=orXMinus Then 
    	' hor. Ausgang X-
    	lenx = Driller.Length
    Else
    	' Fehler
    	AddMistake("Fehler bei Bohrdaten unerlaubte Orientation vom BohrkopfAusgang")
    End If
    wcnc("STOPRE")
	wcncaddcom("$TC_DP1["+inttos(Tnum)+","+inttos(DNum)+"]=120"," Typ")
	Verschleiss_BasismassNullen(Tnum,DNum)
	' Länge X/Y/Z beschreiben - Versatz vom Aktuellen BOHRER
	Call wcncAddCom("$TC_DP5["+IntToS(Tnum)+","+IntToS(DNum)+"]=("+FToS(LenX)+")"+Get_Val_Signed(-Driller.OffX),"distance x")  
	Call wcncAddCom("$TC_DP4["+IntToS(Tnum)+","+IntToS(DNum)+"]=("+FToS(LenY)+")"+Get_Val_Signed(-Driller.OffY),"distance y")  
	Call wcncAddCom("$TC_DP3["+IntToS(Tnum)+","+IntToS(DNum)+"]=("+FToS(LenZ)+")"+Get_Val_Signed(-Driller.OffZ),"distance z")  
  
End Function
Function MT_Write_Correction_DH_CRot_Drill(Driller As tDriller)',dh As tdh)
Dim Tnum,DNum As Double
Dim LenZ,LenX,LenY As Double
Dim adx,ady,adz As Double
Dim dx,dy As Double
Dim MyAng As Double


	' Tnum = letzter Werkzeugwechselplatz +1
	'Tnum = actt.ph_add.ToolNo   'MT_Get_TNum_DrillingHead(ActT)     ' ermittelt die T-Nummer für die Korrektur Bohrkopf
	'DNum = actt.ph_add.CorrNo   'MT_Get_DNum_DrillingHead(ActT)     ' ermittelt die D-Nummer für die Korrektur Bohrkopf
	Tnum = MT_Get_TNum_DrillingHead(ActT)     ' ermittelt die T-Nummer für die Korrektur Bohrkopf
	DNum = MT_Get_DNum_DrillingHead(ActT)     ' ermittelt die D-Nummer für die Korrektur Bohrkopf
	LenX=0
	LenY=0
	LenZ=0
    If Driller.TP.Orientation=orVertical Then 
    	' vertikaler Ausgang Bohrerlänge auf Länge 1 schreiben
       LenZ= Driller.Length
       
    ElseIf (Driller.TP.Orientation=orYPlus) Or (Driller.TP.Orientation=orYMinus) Or (Driller.TP.Orientation=orXPlus) Or (Driller.TP.Orientation=orXMinus) Then
    	LenX = cosinus(Driller.tp.RotAngle)*Driller.Length
    	LenY = sinus(Driller.tp.RotAngle)*Driller.Length
    
'    ElseIf Driller.TP.Orientation=orYPlus Then 
'    	' hor. Ausgang Y+
'    	LenY = - Driller.Length
'    ElseIf Driller.TP.Orientation=orYMinus Then 
'    	' hor. Ausgang Y-
'    	LenY = Driller.Length
'    ElseIf Driller.TP.Orientation=orXPlus Then 
'    	' hor. Ausgang X+
'    	LenX = -Driller.Length
'    ElseIf Driller.TP.Orientation=orXMinus Then 
'    	' hor. Ausgang X-
'    	LenX = Driller.Length
    Else
    	' Fehler
    	AddMistake("Fehler bei Bohrdaten unerlaubte Orientation vom BohrkopfAusgang")
    End If
    wcnc("STOPRE")
	wcncaddcom("$TC_DP1["+inttos(Tnum)+","+inttos(DNum)+"]=120"," Typ")
	Verschleiss_BasismassNullen(Tnum,DNum)
	' Länge X/Y/Z beschreiben - Versatz vom Aktuellen BOHRER
	Call wcncAddCom("$TC_DP5["+IntToS(Tnum)+","+IntToS(DNum)+"]=("+FToS(LenX)+")"+Get_Val_Signed(-Driller.OffX),"distance x")  
	Call wcncAddCom("$TC_DP4["+IntToS(Tnum)+","+IntToS(DNum)+"]=("+FToS(LenY)+")"+Get_Val_Signed(-Driller.OffY),"distance y")  
	Call wcncAddCom("$TC_DP3["+IntToS(Tnum)+","+IntToS(DNum)+"]=("+FToS(LenZ)+")"+Get_Val_Signed(-Driller.OffZ),"distance z")  
  
	
	
	' -- 
	' --  MW 10.08.2009 16:23:31
	' --
	' --  Drehbarer Bohrkopf / Drehung der Werkzeugspitze um 0,0
	
	dx=Driller.OffX + LenX +ActT.t.MoveX '+ dh.CenterX
	
	dy=Driller.OffY + LenY +ActT.t.MoveY '+ dh.CenterY
	
            
    ' + 90 da Verrechnung in abhängigkeit der Ebenenausrichtung erfolgt
    
    ' Rotation dx,dy um x=0 y=0
    MyAng=Driller.ActRot
    RotPoint00(MyAng,dx,dy)

    
    
    'actT.T_PH.Get_OffsetToolRefPoint(Driller.ActRot,0, adx, ady, adz)
    'actt.t_ph.PH_ToolPlace.GetOffsetToolPlace(Driller.ActRot,0, adx,ady,adz)

    
	wcnccom("OFFSET BOHRER"+Driller.tname+" ID:"+inttos(Driller.tp.PlaceID))
	wcnccom("--------------------------------------------------------------------------------")
	wcnccom("BOHRKOPF OFFSETBERRECHNUNG FÜR STELLUNG DW:"+ftos(Driller.ActRot))
	wcnccom("--------------------------------------------------------------------------------")
	wcnccom("DX:"+ftos(dx)+"  DY:"+ftos(dy))
	
	'MsgBox("X:"+FToS(adx)+"  Y:"+FToS(ady)+"  WINKEL:"+ftos(90-MultiDrilling_GBHeadVert.dw))
	
	Call wcncAddCom("$TC_DP5["+IntToS(Tnum)+","+IntToS(DNum)+"]=("+FToS(-dx)+")","distance x")  
	Call wcncAddCom("$TC_DP4["+IntToS(Tnum)+","+IntToS(DNum)+"]=("+FToS(-dy)+")","distance y")  	
  
    wcnc("STOPRE")
End Function
Function MT_Get_Last_TC_Place(id)    ' ermittelt die T-Nummer für die Korrektur des Bohrkopfes
Dim itc As IIToolChangerHead

Set itc= TDATA.GetToolChangerHead_ID(id)
	
	If Not itc Is Nothing Then
		MT_Get_Last_TC_Place = itc.ToolPlaces.Count
	Else
		AddMistake("2342343")
	End If
End Function


Function MT_Get_TNum_DrillingHead(T As THopsBasicToolExt)    ' ermittelt die T-Nummer für die Korrektur des Bohrkopfes
Dim itc As IIToolChangerHead
Dim isok As Boolean

' hier aus MT_-manager aus Spezial 10070 die T.-Nummer holen
	MT_Get_TNum_DrillingHead = MT_get_Add_ID(T,10070,isok)
	If Not isok Then
		AddMistake("23409d68923")
	End If

End Function

Function MT_Get_DNum_DrillingHead(T As THopsBasicToolExt)    ' ermittelt die T-Nummer für die Korrektur des Bohrkopfes
Dim itc As IIToolChangerHead
Dim isok As Boolean

' hier aus MT_-manager aus Spezial 10071 die D-Nummer holen
	MT_Get_DNum_DrillingHead = MT_get_Add_ID(T,10071,isok)
	If Not isok Then
		AddMistake("23403968923")
	End If

End Function


' Ermittlung, ob Aggregat in der Lage pneumatic zu benutzen
Function MT_isToolUsingPneumatic(T As THopsBasicToolExt)
Dim result As Boolean

	result = False
	If (MT_IsGearBoxTool(T)) Or (MT_IsGearBoxTool_Special(T)) Or (MT_IsGearBoxTool_5thAxis(T)) Then
		If T.gb.UsePneumaticChannels Then
		 	result = True
		End If
	End If
	MT_isToolUsingPneumatic = result
End Function



Function MT_Underside_Set_Param_Angle(T As THopsBasicToolExt,TAngle)
Dim WiUndersideGear As Double
			
			WiUndersideGear = GetWinkelGrad(0,0,T.t_gb.GB_ToolPlace.OffsetX,T.t_gb.GB_ToolPlace.OffsetY)
			' 360-Tangle da Tangentenwinkel auf der um 180° gekippten Ebene betrachtet wird
			UndersideTool.dw = Norm0_360(ActV.RotA + (360-TAngle) + WiUndersideGear +90)
			
			' Ebenenwinkel
			UndersideTool.view_w = Norm0_360(ActV.RotA + (360-TAngle) - 90)
	
End Function


' Normierung anhand Maschinendaten der Achsen
Function MT_Rot_Norm_MINMAX(w) As Double
Dim minrot,maxrot As Double
Dim result As Double
	result =w
	If Not ActT.h Is Nothing Then
		' Processhead ja
		minrot = ActT.h.RotMin
		maxrot = ActT.h.RotMax
		While result<minrot
			result=result+360
		Wend
		While result>maxrot
			result=result-360
		Wend
	End If
	MT_Rot_Norm_MINMAX=result
End Function

Function MT_AllDrillHeadsUp
Dim i As Integer 
Const M_id = 10055
Dim iProcessHead As IIDrillingHead

	For i = 0 To TDATA.MachineData.DrillingHeadsCount-1
		
		Set iProcessHead = TDATA.MachineData.GetDrillingHead_Index(i)
		
		If Not iProcessHead Is Nothing Then
			If Not iProcessHead.Additions Is Nothing Then
				If Not iProcessHead.Additions.GetAddition_ID(M_id) Is Nothing Then
					wcnc(iProcessHead.Additions.GetAddition_ID(M_id).Value)
				End If
			End If
		End If
		
		
	Next i
End Function

Function MT_TEdgeChange(ActT As THopsBasicToolExt,LastT As THopsBasicToolExt) As Boolean
	MT_TEdgeChange=False
	If (Not LastT.t Is Nothing) And (Not ActT.t Is Nothing) Then
	        If LastT.t.ToolNo = ActT.t.ToolNo Then
				MT_TEdgeChange=True
	        	
	        End If
	End If
End Function

Function HeadHasChanged(AT As THopsBasicToolExt,LT As THopsBasicToolExt)
	HeadHasChanged=False
	If (Not LT.t Is Nothing) And (Not AT.t Is Nothing) Then 
		If AT.Hid<>LastT.hid Then
			HeadHasChanged=True
		End If
		
	End If
	
End Function

Function MT_Get_HaubenPos As Long
Dim dustEx As Long
	
	dustEx =-1
	'If MT_IsGB(ActT) Then
	If Not ActT.GB Is Nothing Then
		dustEx = (ActT.GB.PosDustExhaust)
	End If
	'Else
	If Not ActT.T_CEdge Is Nothing Then
		dustEx = (ActT.T_CEdge.PosDustExhaust)
	End If
	
	If dustEx > 0 Then
	' 0 = automatik nix machen
		MT_Get_HaubenPos = dustEx
	Else
		MT_Get_HaubenPos = -1
	End If
	
End Function
Function MT_GetDHDustEX(T As THopsBasicToolExt)	
Dim i As Integer
	MT_GetDHDustEX=-1
End Function
Function MT_Get_Sic_Diff_Saw_Router(T As THopsBasicToolExt,TipAngle) As Double
' -- 
' --  MW 21.04.2009 14:50:43
' --
Dim ZSicSaw, ZSicRouter As Double
Dim l_ttyp As THopsToolType
Dim tmp_t As thopsbasictoolext
 

  'If MT_IS_MainAgg(t) Then
     l_ttyp = T.t.Tool.ToolType
    
  Set tmp_t.t = TDATA.GetTool_ID(T.T.ID)
    
  Set tmp_t.t.Tool.ToolType=tSaw
  
  ' MW 03.03.2010
  ZSicSaw = tmp_t.t.GetSecurityZ(TipAngle)
  'ZSicSaw = T.t.GetSecurityZ(TipAngle)
  'wcncCom("ZSic:als Säge"+FToS(ZSicSaw))
  
  Set tmp_t.t.Tool.ToolType=tCutter
  
  ' MW 03.03.2010
  ZSicRouter = tmp_t.t.GetSecurityZ(TipAngle)
  'ZSicRouter = T.t.GetSecurityZ(TipAngle)
  'wcncCom("ZSic:als Fräser"+FToS(ZSicRouter))
 
  If MT_Is_Vertical_StandardTool5Axis(T) Then
   ' --
   ' -- Modified  MW 08.06.2009 16:45:03
   ' --
   ZSicRouter= ZSicRouter + (sinus(TipAngle)*t.t.Radius)
  End If
  
 
  If ZSicRouter > ZSicSaw Then
   MT_Get_Sic_Diff_Saw_Router =  (ZSicRouter - ZSicSaw)
  Else
   MT_Get_Sic_Diff_Saw_Router = 0
  End If
  
  Set tmp_t.t = Nothing
  
  ' MW 03.03.2010 ursprünglichen Typ wieder setzen
	T.t.Tool.ToolType = l_ttyp
  
 'ElseIf MT_isDHSaw(t) Or MT_isPneumaticSaw(t) Then
  ' -- 
   ' -- 1. Säge auf Bohrkopf oder Säge pneumatisch
  ' --  
 ' MT_Get_Sic_Diff_Saw_Router = t.t.CollRadius
 'ElseIf MT_isPneumaticSaw(t) Then
  ' -- 
   ' -- 1. Säge pneumatisch
  ' --  
  'MT_Get_Sic_Diff_Saw_Router = t.t.CollRadius
 
 
 'End If
 
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


' *****************************************************************************************
' ** MT_H -> Aggregat ohne Drehachse und ohne Kippachse in Z- ausgerichtet
' *****************************************************************************************
Function MT_H_Is_3_Axis(T As THopsBasicToolExt)

Dim rot As Variant
Dim tip As Variant
	
	MT_H_Is_3_Axis = False
	
	
	If Not T.H Is Nothing Then
		'test =TH.Description
		rot = T.H.RotType
		tip = T.H.TipType
		
		If (rot = atFix) And (tip = atFix) Then
		    
		    ' Drehachse fix kippachse fix
		    
			If T.h.ToolPlaces.GetToolPlace_PlaceID(1).TipAngle=0 Then
				' nur in Z- Richtung liegende Spindeln 1!!
				MT_H_Is_3_Axis = True
			End If
		End If
		
	End If

End Function

' *****************************************************************************************
' ** MT_H -> Aggregat mit Drehachse welche um Z dreht
' *****************************************************************************************
Function MT_H_Is_4_Axis(T As THopsBasicToolExt)

Dim rot As Variant
Dim tip As Variant
	
	MT_H_Is_4_Axis = False
	
	
	If Not T.H Is Nothing Then
		'test =TH.Description
		rot = T.H.RotType
		tip = T.H.TipType
		
		If (rot = atFree) And (tip = atFix) Then
		    ' Drehachse frei
			If T.h.ToolPlaces.GetToolPlace_PlaceID(1).TipAngle=0 Then
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

' Statische Verrechnung Werkzeugspitze ueber TCarr oder Laenge2/Laenge3
Function Call_Correction_Gb
Dim X,Y,Z As Double
Dim dX,dy,dZ As Double
'Dim length As Double
Dim Rota As Double
Dim Tipa As Double
Dim center_z As Double
Dim adx As Variant
Dim ady As Variant
Dim adz As Variant
Dim Lenx As Double
Dim Leny As Double
Dim Lenz As Double
Dim ds_x As Variant 
Dim ds_y As Variant 
Dim ds_Z As Variant 
Dim c_Z As Variant
Dim tEMP As Double 
Dim l1x,l1y,l1z,l2x,l2y,l2z,l3x,l3y,l3z,v1x,v1y,v1z,v2x,v2y,v2z,a1,a2 As Variant
Dim Raster_Angle As Double

Dim Use_TCarr,isok As Boolean
Dim calc_wi_traori As Double

	' Gearbox or Gearbox with 5th axis
	' toCheck OS/MW
	' 
	Use_TCarr = MT_get_Add_ID(ActT,10030,isok)
	If Not isok Then
		Use_TCarr=False
	End If
	
	If Use_TCarr Then   ' Einstellbar über HS ob mit oder ohne TCarr gearbeitet werden soll
		' TCarr set the parameters with Cycle
		pp_err(7,10030)
	Else
	    ' TCARR - 810D ohne Option TCarr ?!?!??!!?
	    ' 1. Offset Z Aggregat
	    If MT_IsGearBoxTool_Special(ActT) Then
	    	c_Z = ActT.t_sgb.GearBox.CenterZ
	    	' offset Ausgang + Werkzeug selbst
	    	actT.T_SGB.Get_OffsetToolRefPoint(ActV.RotA,ActV.TipA, adx, ady, adz)
	    Else
	    	c_Z = ActT.t_gb.GearBox.CenterZ
	
	    	' offset Ausgang + Werkzeug selbst
	    	
	    	ActT.T_GB.Get_OffsetToolRefPoint((ActT.t_gb.GB_ToolPlace.RotAngle + ActT.T_GB.GearBox.OffsetC + ActT.h.PinOffset),ActV.TipA, adx, ady, adz)
	    	If ActT.t_gb.Tool.ToolType=tSaw Then
	    		If Equal(ActV.TipA,90) Then
	    			GetDX_DY_DZMitKippW_Laenge(ActV.TipA,ActV.RotA,(ActT.t.GB_ToolPlace.Length) , dX,dy,dZ)
	    			adz=c_Z+dZ
	    			GetDX_DY_DZMitKippW_Laenge(ActV.TipA,ActV.RotA,(ActT.t.SawThickness/2) , dX,dy,dZ)
					ds_x = dX		
					ds_y = dy
					ds_Z = dZ
	    		Else
	    		
	    			GetDX_DY_DZMitKippW_Laenge(ActV.TipA,ActV.RotA,(ActT.t.GB_ToolPlace.Length+ActT.t.SawThickness/2) , dX,dy,dZ)
	    			adz=c_Z+dZ
	    			adx=-dX
	    			ady=-dy
	    			'GetDX_DY_DZMitKippW_Laenge(ActV.TipA,Actv.RotA,(actT.t.SawThickness/2) , dX,dY,dZ)
					'ds_x = dX		
					'ds_y = dY
					'ds_Z = dZ
					ds_x = 0		
					ds_y = 0
					ds_Z = 0
	    		End If
	    		
	    		'adx=adx+
				' dann Säge !!!
				'ds_x = (actT.t.SawThickness/2)*SINUS(ActV.RotA)				
				'ds_y = (actT.t.SawThickness/2)*COSINUS(ActV.RotA)
				'GetDX_DY_DZMitKippW_Laenge( 0,30,(100) , dX,dY,dZ)
				'GetDX_DY_DZMitKippW_Laenge( 90,30,(100) , dX,dY,dZ)
				'GetDX_DY_DZMitKippW_Laenge( 180,30,(100) , dX,dY,dZ)
				'GetDX_DY_DZMitKippW_Laenge(270,30,(100) , dX,dY,dZ)
	
				'ds_x=0
				'ds_y=0  ' nicht nötig Sägeblattbreite von Engine verrechnet
			End If
	    End If
	    
	    
	
	    
	    Lenx=adx+ds_x
	    Leny=ady+ds_y
	    Lenz=-adz+ds_Z
	    'WCNCCOM("Lenx: "+Ftos(lenx)+" ADX: "+Ftos(adx)+" DS_X: "+Ftos(ds_x))
	    'WCNCCOM("Leny: "+Ftos(leny)+" ADY: "+Ftos(ady)+" DS_Y: "+Ftos(ds_y))
	    'WCNCCOM("LenZ: "+Ftos(lenz)+" ADZ: "+Ftos(adz)+" DS_Z: "+Ftos(ds_Z))
	    'wcnc("STOPRE")
		'wcncaddcom("$TC_DP1["+inttos(Tnum)+","+inttos(DNum)+"]=120"," Typ")
		'Verschleiss_BasismassNullen(Tnum,DNum)
		' Länge X/Y/Z beschreiben - Versatz vom Aktuellen BOHRER
		
	    wcnc("STOPRE")
		If (ActT.H_Add.traori) Then
			' -- 
			' --  MW 22.10.2007 09:46:45
			' --
			' -- Winkelgetriebe über Traori-verrechnen
			' -- ausgangsoffset mit Drehwinkel = 0 errmitteln
			If Equal(ActV.TipA,90) Or Equal(ActV.TipA,0) Or (Equal(ActV.TipA,180) And MT_Is_UndersideTool(ActT)) Then
				'If Equal(actv.TipA,180) And MT_Is_UndersideTool(actt) Then	
				
				'Else
				'	AddMistake("nicht erlaubte Richtung fuer Winkelgetriebe")
				'End If
				
			Else
				AddMistake("nicht erlaubte Richtung fuer Winkelgetriebe")
			End If
			'actt.t_gb.GB_ToolPlace.GetOffsetToolPlace(0,actv.TipA, lenx,leny,lenz)
			
			'actt.t_gb.GB_ToolPlace.GetOffsetToolPlace(actt.t_gb.GB_ToolPlace.RotAngle+90,actv.TipA, lenx,leny,lenz)
			
			' +90, kommen vom pinoffset - das ist im Prinzip der Offset von Winkelgetriebe 0-Stellung zu 
			' Ebenen-Nullstellung
			' Winkel vom Ausgang  + Winkelgetriebe Gesamtoffset + Head - Nockenoffset
			If aCTT.hID=1 Then
				If MT_IsGearBoxTool_Special(ActT) Then
					calc_wi_traori = ActT.t_sgb.GB_ToolPlace.RotAngle + ActT.T_sGB.GearBox.OffsetC + ActT.h.PinOffset
			
					ActT.t_sgb.Get_OffsetToolRefPoint(calc_wi_traori,ActV.TipA, Lenx,Leny,Lenz)
				Else
					'calc_wi_traori = ActT.t_gb.GB_ToolPlace.RotAngle + ActT.T_GB.GearBox.OffsetC + ActT.h.PinOffset
					'ActT.t_gb.Get_OffsetToolRefPoint(calc_wi_traori,ActV.TipA, Lenx,Leny,Lenz)
	
					'neu MW 04.11.2015
					' Winkelgetriebe Ausgangswinkel negiert
					'calc_wi_traori = -ActT.t_gb.GB_ToolPlace.RotAngle + ActT.T_GB.GearBox.OffsetC + ActT.h.PinOffset
					'calc_wi_traori = ActT.T_GB.GearBox.OffsetC + ActT.h.PinOffset
					'neu MW 04.11.2015
					' 360 - calc_wi_traori 
					'bisher hat nur ausgang 1 und ausgang 3 funktioniert
					'ActT.t_gb.Get_OffsetToolRefPoint(calc_wi_traori,ActV.TipA, Lenx,Leny,Lenz)
					'wcnc(";Lenx: "+ftos(Lenx)+" Leny: "+ftos(Leny)+" Lenz "+ftos(Lenz))
					'ActT.t_gb.Get_OffsetToolRefPoint(360-calc_wi_traori,ActV.TipA, Lenx,Leny,Lenz)
					'ausgang 4 x und y offsets muessen beide positiv sein
					'ausgang 2 x und z offsets muessen beide negativ sein 
					'ausgang 1 x positiv und y negativ
					'ausgang 3 x negativ und z positiv
				End If
			End If
			
			If ActT.hID=1 Then
				'MW 04.11.2015 x/y Tausch nicht mehr notwendig
				'tEMP=lenx
				'lenx=leny
				'leny=tEMP
				If MT_Is_UndersideTool(ActT) Then
					tEMP=Lenx
					LenX=LenY
					'Lenx=Lenx
					Leny=tEMP
					
				Else
	
				End If
			Else
				If MT_Is_UndersideTool(ActT) Then
					Leny=Leny
				Else
				
				End If
				'"tEMP=lenx
				''lenx=0
				''leny=-leny	
			End If
			
			'lenx=-lenx
			'leny=-leny
			'leny=leny+actt.t_cedge.Length* SINUS(actt.t_gb.GB_ToolPlace.RotAngle)
			'lenx=-lenx-actt.t_cedge.Length* COSINUS(actt.t_gb.GB_ToolPlace.RotAngle)
			'lenz= ok
			Call wcncAddCom("$TC_DP5["+IntToS(ActT.h_add.ToolNo)+","+IntToS(ActT.h_add.CorrNo)+"]=("+FToS(Lenx)+")","distance x")  
			Call wcncAddCom("$TC_DP4["+IntToS(ActT.h_add.ToolNo)+","+IntToS(ActT.h_add.CorrNo)+"]=("+FToS(Leny)+")","distance y")  
			Call wcncAddCom("$TC_DP3["+IntToS(ActT.h_add.ToolNo)+","+IntToS(ActT.h_add.CorrNo)+"]=("+FToS(Lenz)+")","distance z")  
		Else
		
			Call wcncAddCom("$TC_DP5["+IntToS(ActT.h_add.ToolNo)+","+IntToS(ActT.h_add.CorrNo)+"]=("+FToS(Lenx)+")","distance x")  
			Call wcncAddCom("$TC_DP4["+IntToS(ActT.h_add.ToolNo)+","+IntToS(ActT.h_add.CorrNo)+"]=("+FToS(Leny)+")","distance y")  
			Call wcncAddCom("$TC_DP3["+IntToS(ActT.h_add.ToolNo)+","+IntToS(ActT.h_add.CorrNo)+"]=("+FToS(Lenz)+")","distance z")  
		End If
	    wcnc("STOPRE")
	
		'wcnc("T"+IntToS(ActT.ph_add.ToolNo)+" D"+IntToS(ActT.ph_add.CorrNo))
	    wcnc("T"+IntToS(ActT.h_add.ToolNo))
	    wcnc("D"+IntToS(ActT.h_add.CorrNo))
	    
	
	End If
End Function



Function MT_Write_Call_Correction
Dim X,Y,Z As Double
Dim dX,dy,dZ As Double
Dim length As Double
Dim Rota As Double
Dim Tipa As Double
Dim center_z As Double
Dim adx,ady,adz As Variant
Dim Lenx,Leny,Lenz As Double
Dim ds_x,ds_y,ds_Z,c_Z As Variant
Dim tEMP As Double 
Dim l1x,l1y,l1z,l2x,l2y,l2z,l3x,l3y,l3z,v1x,v1y,v1z,v2x,v2y,v2z,a1,a2 As Variant
Dim Raster_Angle As Double

Dim Use_TCarr,isok As Boolean
Dim calc_wi_traori As Double

	If ActT.h_add.CorrNo < 10 Then
    	' toCheck OS/MW
    	' hier muessen die einzelnen Konstellationen noch getestet werden, wann ist was Bezugspunkt des Werkzeugs
		If (PPara.MMode=0) Then
			' Normale Bearbeitung mit "statischer" Ausrichtung des Werkzeugs
			' toCheck
			If MT_IsAnyGearboxTool(ActT) Then
				' Winkelgetriebe (auch Unterflur)
				Call_Correction_Gb
			Else
				If ActT.h_add.MCorrNo>0 Then
					If Actt.t.Tool.ToolType=tSaw Then
						If PPara.PreObjectTyp =otSawing Then
							'WCNC("C_CHECKTOOL("+FTOS(ActT.h_add.MLTolCorr)+","+FTOS(ActT.h_add.MRTolCorr)+")")
							'wcncaddcom("$TC_DP3["+inttos(ActT.h_add.ToolNo)+","+inttos(ActT.h_add.CorrNo)+"]=("+ftos(Actt.t.Length-ZentrumZ)+"-$TC_DP3["+inttos(ActT.h_add.ToolNo)+","+inttos(ActT.h_add.MCorrNo)+"])" ,"Laenge")
							wcncaddcom("$TC_DP6["+inttos(ActT.h_add.ToolNo)+","+inttos(ActT.h_add.CorrNo)+"]=("+ftos(ActT.t.Radius)+")-$TC_DP6["+inttos(ActT.h_add.ToolNo)+","+inttos(ActT.h_add.MCorrNo)+"]","Radius")
							WCNC("STOPRE")
						Else
							'WCNC("C_CHECKTOOL("+FTOS(ActT.h_add.MLTolCorr)+","+FTOS(ActT.h_add.MRTolCorr)+")")
							'wcncaddcom("$TC_DP3["+inttos(ActT.h_add.ToolNo)+","+inttos(ActT.h_add.CorrNo)+"]=$TC_DP3["+inttos(ActT.h_add.ToolNo)+","+inttos(ActT.h_add.MCorrNo)+"]" ,"Laenge")
							wcncaddcom("$TC_DP6["+inttos(ActT.h_add.ToolNo)+","+inttos(ActT.h_add.CorrNo)+"]=$TC_DP6["+inttos(ActT.h_add.ToolNo)+","+inttos(ActT.h_add.MCorrNo)+"]" ,"Radius")
							WCNC("STOPRE")					
						End If	
					
					End If
				End If
				wcnc("T"+IntToS(ActT.h_add.ToolNo))
				wcnc("D"+IntToS(ActT.h_add.CorrNo))
			End If
	    ElseIf (PPara.MMode=1) Then
	    	' C-Achsenfraesen
	    	' toCheck OS/MW
			If MT_IsAnyGearboxTool(ActT) Then
				' alles Verrechnet
				wcnc("D0")
			Else
				wcnc("T"+IntToS(ActT.h_add.ToolNo))
				wcnc("D"+IntToS(ActT.h_add.CorrNo))
			End If
		ElseIf (PPara.MMode=2) Then
			' 5Achsfraesen / Oberflaechenfraesen
	    	' toCheck OS/MW
	    	' hier passiert nichts
		    If (MT_Is_Vertical_StandardTool5Axis(ActT)) Then
				' 5-Axis 
				wcnc("T"+IntToS(ActT.h_add.ToolNo))
				wcnc("D"+IntToS(ActT.h_add.CorrNo))
			ElseIf MT_IsAnyGearboxTool(ActT) Then
				' alles Verrechnet
				wcnc("D0")
			Else 
				' 3-Achs ????
				pp_err(0,"8234243")
			End If
		Else
			' every other kind of tools  -  calls standard Tx Dx
			'wcnc("T"+IntToS(ActT.T.ToolNo)+" D"+IntToS(ActT.T.CorrNo))
			'wcnc("T"+IntToS(ActT.T.GetPlaceID_OnTC)+" D"+IntToS(ActT.T.CorrNo))
			'wcnc("T"+IntToS(ActT.ph_add.ToolNo)+" D"+IntToS(ActT.ph_add.CorrNo))
			wcnc("T"+IntToS(ActT.h_add.ToolNo))
			wcnc("D"+IntToS(ActT.h_add.CorrNo))
		End If
	Else
		AddMistake("unerlaubte D-Nummer bitte Werkzeugverwaltung überprüfen")
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

End Function
Function MT_GetMachineKinematiks(Kind As Integer,Optional addi As IIAdditions)

'kind=1 Global BY Workingtype
'Kind=2 By Head

'0	otNotdefinied
'1	otNCInfo
'2	otMilling
'3	otVertDrilling
'4	otHorzDrilling
'5	otSawing
'6	otNCProcess
'7	otNCInfoProcess
'8	otNCContourProcess
'9	otDHProcess
'10	otMillingPoints
'11	otMillingMPs
'12	otNCInfoProcessMPs

Dim I,J As Integer 
Dim Add As Long
For I=0 To 12
	
	For J=0 To 2
		
		If Kind=1 Then
			Add=30000+I*10+J
			If Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(Add)) Is Nothing Then 
				MKG_ON(I).P(J)=(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(Add).Value)
			Else
				MKG_ON(I).P(J)=""
				AddHint("MachinParameter Missing ID: "+CStr(Add))
			End If
			Add=40000+I*10+J
			If Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(Add)) Is Nothing Then 
				MKG_OFF(I).P(J)=(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(Add).Value)
			Else
				MKG_OFF(I).P(J)=""
				AddHint("MachinParameter Missing ID: "+CStr(40000+I+J))
			End If
		ElseIf Kind=2 Then
			Add=30000+I*10+J
			If Not(addi.GetAddition_ID(Add)) Is Nothing Then 
				HK_ON(I).P(J)=(addi.GetAddition_ID(Add).Value)
				
			Else
				HK_ON(I).P(J)=""
				AddHint("MachinParameter Missing ID: "+CStr(Add))
			End If
			Add=40000+I*10+J
			If Not(addi.GetAddition_ID(Add)) Is Nothing Then 
				HK_OFF(I).P(J)=(addi.GetAddition_ID(Add).Value)
			Else
				HK_OFF(I).P(J)=""
				AddHint("MachinParameter Missing ID: "+CStr(Add))
			End If
		End If
		
	Next J
	
Next I

End Function
