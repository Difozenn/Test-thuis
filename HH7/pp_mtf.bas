' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \hh7\pp_mtf.bas
' -- 
' -----------------------------------------
'#uses "pp_global.bas"
'#uses "pp_7.bas"
'#uses "pp_math.bas"
'#uses "pp_mt.bas"
'#uses "pp_isg.bas"
'#uses "pp_siemens.bas"

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
' ** Werkzeugliste zur Info ausgeben
' *****************************************************************************************
Function MT_Write_TCheck
Dim i,j As Long
Dim t As THopsBasicToolExt
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
	
		t = ToolArray(i)
		
		If Not MT_CheckisIdInList(t.t.ID,BoxNoArray) Then
			If MT_IsMEAS(t) Then
				' MW 24.04.2019 - meas
				' nichts tun ?
			ElseIf MT_IsDH(t) Then
				' Drilling Head - no check ???!?!?!?!?
				wcnccom("Box:"+strsize(inttos(t.t.ID),5,2)+" HId:"+StrSize(Inttos(t.HId),5,1)+" "+StrSize(t.T.Description,30,1)) 
				' alle Bohrer-Daten checken
				For j= 0 To t.T_DH.DrillingHead.ToolPlaces.Count-1
					Set dummy = t.T_DH.DrillingHead.ToolPlaces.GetToolPlace_Index(j).ActiveTool
					Set dh_tool = dummy    ' ist ein iiTool
					If (Not dh_tool Is Nothing) Then 
					    If (dh_tool.ToolType=tDriller) Then
							' nur Bohrer
						    toolno = t.T_DH.DrillingHead.ToolPlaces.GetToolPlace_Index(j).ToolNo
						    maxrot = dh_tool.GetFirstCuttingEdge.MaxRotSpeed
						    length=dh_tool.GetFirstCuttingEdge.Length
						    rad= dh_tool.GetFirstCuttingEdge.Radius   
						    Len1=0
						    Len2=0
						    Len3=0
						    If t.T_DH.DrillingHead.ToolPlaces.GetToolPlace_Index(j).Orientation=orVertical Then 
						    	' vertikaler Ausgang Bohrerlaenge auf Laenge 1 schreiben
						       Len1= length
						    ElseIf t.T_DH.DrillingHead.ToolPlaces.GetToolPlace_Index(j).Orientation=orYPlus Then 
						    	' hor. Ausgang Y+
						    	Len2 = - length
						    ElseIf t.T_DH.DrillingHead.ToolPlaces.GetToolPlace_Index(j).Orientation=orYMinus Then 
						    	' hor. Ausgang Y-
						    	Len2 = length
						    ElseIf t.T_DH.DrillingHead.ToolPlaces.GetToolPlace_Index(j).Orientation=orXPlus Then 
						    	' hor. Ausgang X+
						    	Len3 = -length
						    ElseIf t.T_DH.DrillingHead.ToolPlaces.GetToolPlace_Index(j).Orientation=orXMinus Then 
						    	' hor. Ausgang X-
						    	Len3 = length
						    Else
						    	' Fehler
						    	pp_err(350)
						    End If
						    
						    If JobPara.isg Then
						    	' Cylcle call 
	  							ISG_CC(SPF_TCheck,inttos(t.t.ID),inttos(toolno),inttos(1),inttos(maxrot),ftos(rad),ftos(Len1),ftos(Len2),ftos(Len3))
							Else
	  							wcnc(SPF_TCheck+"("+inttos(t.t.ID)+","+inttos(toolno)+ _
	  							  ","+inttos(1)+","+inttos(maxrot)+","+ftos(rad)+","+ftos(Len1)+","+ftos(Len2)+","+ftos(Len3)+")" )
	  						End If
					    End If
					End If
				Next
			ElseIf MT_isDHSaw(t) Then
				' NutSaege auf Bohrkopf - 
				' Referenzpunkt ist Saegeblatt- Mitte deshalb muss die Laenge ueber
				' Laenge-SD/2 berrechnet werden und entsprechend auf Laenge2 bzw. Laenge 3 zu schreiben
				length=t.t.Length - t.t.SawThickness/2
				Len1=0    ' t.t.Radius  - Radius wird von Postprozessor verrechnet
				Len2=0
				Len3=0
			    If t.T_DHSaw.DH_ToolPlace.Orientation=orYPlus Then 
			    	' hor. Ausgang Y+
			    	Len2 = - length
			    ElseIf t.T_DHSaw.DH_ToolPlace.Orientation=orYMinus Then 
			    	' hor. Ausgang Y-
			    	Len2 = length
			    ElseIf t.T_DHSaw.DH_ToolPlace.Orientation=orXPlus Then 
			    	' hor. Ausgang X+
			    	Len3 = -length
			    ElseIf t.T_DHSaw.DH_ToolPlace.Orientation=orXMinus Then 
			    	' hor. Ausgang X-
			    	Len3 = length
			    Else
			    	' Fehler
			    	pp_err(351)
			    End If

				'wcnc(SPF_TCheck+"("+inttos(t.t.ID)+","+inttos(t.t.ToolNo)+","+inttos(t.t.CorrNo)+","+inttos(t.t.MaxRotSpeed)+","+ftos(t.t.Radius)+","+ftos(Len1)+","+ftos(Len2)+","+ftos(Len3)+")")
			    If JobPara.isg Then
			    	' Cylcle call 
					iSG_CC(SPF_TCheck,inttos(t.t.ID),inttos(t.t.ToolNo),inttos(t.t.CorrNo),inttos(t.t.SpindleMaxRotSpeed),ftos(t.t.Radius),ftos(Len1),ftos(Len2),ftos(Len3))
			    Else
					wcnc(SPF_TCheck+"("+inttos(t.t.ID)+","+inttos(t.t.ToolNo)+","+inttos(t.t.CorrNo)+","+inttos(t.t.SpindleMaxRotSpeed)+","+ftos(t.t.Radius)+","+ftos(Len1)+","+ftos(Len2)+","+ftos(Len3)+")")
				End If
			ElseIf MT_IsGearBoxTool(t) Then
				
				If t.t_gb.Tool.ToolType=tSaw Then
					' Sonderfall Saege Laenge 1 mit Saegeblattbreite verrechnet
					'wcncaddcom(SPF_TCheck+"("+inttos(t.t.ID)+","+inttos(t.t.ToolNo)+","+inttos(t.t.CorrNo)+","+inttos(t.t.MaxRotSpeed)+","+ftos(t.t.Radius)+","+ftos(t.t.Length-t.t.SawThickness/2)+","+ftos(0)+","+ftos(0)+")","S"+ftos(t.t.MaxRotSpeed)+" R"+ftos(t.t.Radius)+" L1:"+ftos(t.t.Length-t.t.SawThickness/2)+" L2:"+ftos(0)+" L3:"+ftos(0))
					' Neu MW 08.02.2006 - Max - Drehzahl bezogen auf Hauptspindel (als Integer)
					If JobPara.isg Then
						isg_CC(SPF_TCheck,inttos(t.t.ID),inttos(t.t.ToolNo),inttos(t.t.CorrNo),inttos(Int(t.t_gb.SpindleMaxRotSpeed)),ftos(t.t.Radius),ftos(t.t.Length-t.t.SawThickness/2),ftos(0),ftos(0))
					Else
						wcncaddcom(SPF_TCheck+"("+inttos(t.t.ID)+","+inttos(t.t.ToolNo)+","+inttos(t.t.CorrNo)+","+inttos(Int(t.t_gb.SpindleMaxRotSpeed))+","+ftos(t.t.Radius)+","+ftos(t.t.Length-t.t.SawThickness/2)+","+ftos(0)+","+ftos(0)+")","S"+inttos(Int(t.t.SpindleMaxRotSpeed))+" R"+ftos(t.t.Radius)+" L1:"+ftos(t.t.Length-t.t.SawThickness/2)+" L2:"+ftos(0)+" L3:"+ftos(0))
					End If
					
				Else
					'wcncaddcom(SPF_TCheck+"("+inttos(t.t.ID)+","+inttos(t.t.ToolNo)+","+inttos(t.t.CorrNo)+","+inttos(t.t.MaxRotSpeed)+","+ftos(t.t.Radius)+","+ftos(t.t.Length)+","+ftos(0)+","+ftos(0)+")","S"+ftos(t.t.MaxRotSpeed)+" R"+ftos(t.t.Radius)+" L1:"+ftos(t.t.Length)+" L2:"+ftos(0)+" L3:"+ftos(0))
					' Neu MW 08.02.2006 - Max - Drehzahl bezogen auf Hauptspindel (als Integer)
					If JobPara.isg Then
						isg_CC(SPF_TCheck,inttos(t.t.ID),inttos(t.t.ToolNo),inttos(t.t.CorrNo),inttos(Int(t.t_gb.SpindleMaxRotSpeed)),ftos(t.t.Radius),ftos(t.t.Length),ftos(0),ftos(0))
					Else
						wcncaddcom(SPF_TCheck+"("+inttos(t.t.ID)+","+inttos(t.t.ToolNo)+","+inttos(t.t.CorrNo)+","+inttos(Int(t.t_gb.SpindleMaxRotSpeed))+","+ftos(t.t.Radius)+","+ftos(t.t.Length)+","+ftos(0)+","+ftos(0)+")","S"+inttos(Int(t.t.SpindleMaxRotSpeed))+" R"+ftos(t.t.Radius)+" L1:"+ftos(t.t.Length)+" L2:"+ftos(0)+" L3:"+ftos(0))
					End If
					
				End If

			ElseIf MT_IsGearBoxTool_Special(t) Then

				If JobPara.isg Then
					' -- 
					' --  MW 10.09.2008 09:20:47
					' --
					' --  Anstelle t.t_gb.SpindleMaxRotSpeed jetzt 	t.T_SGB.SpindleMaxRotSpeed
					isg_CC(SPF_TCheck,inttos(t.t.ID),inttos(t.t.ToolNo),inttos(t.t.CorrNo),inttos(Int(t.T_SGB.SpindleMaxRotSpeed)),ftos(t.t.Radius),ftos(t.t.Length),ftos(0),ftos(0))
				Else
					wcncaddcom(SPF_TCheck+"("+inttos(t.t.ID)+","+inttos(t.t.ToolNo)+","+inttos(t.t.CorrNo)+","+inttos(Int(t.T_SGB.SpindleMaxRotSpeed))+","+ftos(t.t.Radius)+","+ftos(t.t.Length)+","+ftos(0)+","+ftos(0)+")","S"+ftos(t.t.SpindleMaxRotSpeed)+" R"+ftos(t.t.Radius)+" L1:"+ftos(t.t.Length)+" L2:"+ftos(0)+" L3:"+ftos(0))
				End If
			ElseIf MT_is_VBM_Stempel(t) Then 
				' Stempel Evolution MW 31.07.2013
				' nix zu tun
				
			ElseIf MT_IsProcessHeadTool(t) Then
				' Neu MW 19.05.2005
				' Werkzeuglaenge wird horizontal - Verrechnet 
				' momentan nur fuer achsparallele Ausrichtung moeglich
				length=t.t.Length
				Len1=0    ' t.t.Radius  - Radius wird von Postprozessor verrechnet
				Len2=0
				Len3=0
				
				If MT_isPneumaticSaw(t) Then
					' pneumatisch schwenkbares Aggregat 
					' Laenge positiv auf Laenge 1 schreiben
					' verrechnen mit TCarr
					Len1 = t.t.Length - t.t.SawThickness/2
				Else
					' je nach Ausrichtung fuer fix ausgerichtete Arbeitsspindel
				    If t.T_PH.PH_ToolPlace.Orientation=orYPlus Then 
				    	' hor. Ausgang Y+
				    	Len2 = - length
				    ElseIf t.T_PH.PH_ToolPlace.Orientation=orYMinus Then 
				    	' hor. Ausgang Y-
				    	Len2 = length
				    ElseIf t.T_PH.PH_ToolPlace.Orientation=orXPlus Then 
				    	' hor. Ausgang X+
				    	Len3 = -length
				    ElseIf t.T_PH.PH_ToolPlace.Orientation=orXMinus Then 
				    	' hor. Ausgang X-
				    	Len3 = length
				    Else
				    	' Fehler
				    	pp_err(352)
				    End If
				End If
				
				wcnccom("Box:"+strsize(inttos(t.t.ID),5,2)+" HId:"+StrSize(Inttos(t.HId),5,1)+" "+StrSize(t.T.Description,30,1)  + " Platz:"+ strsize(inttos(t.t.GetPlaceID_OnTC),3,0)+" T:"+strsize(inttos(t.T.ToolNo),3,0)+" D"+strsize(inttos(t.T.CorrNo),3,0))
				
				If JobPara.isg Then
					isg_cc(SPF_TCheck,inttos(t.t.ID),inttos(t.t.ToolNo),inttos(t.t.CorrNo),inttos(Int(t.t.SpindleMaxRotSpeed)),ftos(t.t.Radius),ftos(Len1),ftos(Len2),ftos(Len3))
				Else
					wcncaddcom(SPF_TCheck+"("+inttos(t.t.ID)+","+inttos(t.t.ToolNo)+","+inttos(t.t.CorrNo)+","+inttos(Int(t.t.SpindleMaxRotSpeed))+","+ftos(t.t.Radius)+","+ftos(Len1)+","+ftos(Len2)+","+ftos(Len3)+")","S"+inttos(Int(t.t.SpindleMaxRotSpeed))+" R"+ftos(t.t.Radius)+" L1:"+ftos(Len1)+" L2:"+ftos(Len2)+" L3:"+ftos(Len3))
				End If
				
				
			ElseIf MT_Is_GearBoxTool_With_FreeTiltAxis(t) Then
				' Getriebe mit Stellachse (5.Achse)
				If t.T_TCA_GB.Tool.ToolType=tSaw Then
					' Saegeblatt 
					Len1 = t.t.Length - t.t.SawThickness/2
				Else
					Len1 = t.t.Length
				End If
				wcnccom("Box:"+strsize(inttos(t.t.ID),5,2)+" HId:"+StrSize(Inttos(t.HId),5,1)+" "+StrSize(t.T.Description,30,1)  + " Platz:"+ strsize(inttos(t.t.GetPlaceID_OnTC),3,0)+" T:"+strsize(inttos(t.T.ToolNo),3,0)+" D"+strsize(inttos(t.T.CorrNo),3,0))
				If JobPara.isg Then
					isg_cc(SPF_TCheck,inttos(t.t.ID),inttos(t.t.ToolNo),inttos(t.t.CorrNo),inttos(Int(t.t_gb.SpindleMaxRotSpeed)),ftos(t.t.Radius),ftos(Len1),ftos(0),ftos(0))
				Else
					wcncaddcom(SPF_TCheck+"("+inttos(t.t.ID)+","+inttos(t.t.ToolNo)+","+inttos(t.t.CorrNo)+","+inttos(Int(t.t_gb.SpindleMaxRotSpeed))+","+ftos(t.t.Radius)+","+ftos(Len1)+","+ftos(0)+","+ftos(0)+")","S"+ftos(t.t.SpindleMaxRotSpeed)+" R"+ftos(t.t.Radius)+" L1:"+ftos(t.t.Length)+" L2:"+ftos(0)+" L3:"+ftos(0))
				End If
				
				' ..
				' --
			Else
				' alle uebrigen Werkzeuge
				wcnccom("Box:"+strsize(inttos(t.t.ID),5,2)+" HId:"+StrSize(Inttos(t.HId),5,1)+" "+StrSize(t.T.Description,30,1)  + " Platz:"+ strsize(inttos(t.t.GetPlaceID_OnTC),3,0)+" T:"+strsize(inttos(t.T.ToolNo),3,0)+" D"+strsize(inttos(t.T.CorrNo),3,0))
				'wcncaddcom(SPF_TCheck+"("+inttos(t.t.ID)+","+inttos(t.t.ToolNo)+","+inttos(t.t.CorrNo)+","+inttos(t.t.MaxRotSpeed)+","+ftos(t.t.Radius)+","+ftos(t.t.Length)+","+ftos(0)+","+ftos(0)+")","S"+ftos(t.t.MaxRotSpeed)+" R"+ftos(t.t.Radius)+" L1:"+ftos(t.t.Length)+" L2:"+ftos(0)+" L3:"+ftos(0))
				
				' -- 
				' --  MW 13.06.2008 11:43:35
				' --  5-Axis Saegeblatt wird bis auf laengsten Punkt eingetragen, verrechnet wird aber auf die Mitte - auch controller - DLL
				' --
				' -- MW 11.05.2016 - nicht wenn SaegeRefPunkt definierbar
	            If (t.t.SawThickness>0.0001) And (t.T.Tool.ToolType=tSaw) And (Not TDATA.MachineData.MachineParameter.SawRefDefinable) Then
	            
					Len1 = t.t.Length - t.t.SawThickness/2
	            Else
					Len1 = t.t.Length
	            End If
				If JobPara.isg Then
					isg_cc(SPF_TCheck,inttos(t.t.ID),inttos(t.t.ToolNo),inttos(t.t.CorrNo),inttos(Int(t.t.SpindleMaxRotSpeed)),ftos(t.t.Radius),ftos(Len1),ftos(0),ftos(0))
				Else
					wcncaddcom(SPF_TCheck+"("+inttos(t.t.ID)+","+inttos(t.t.ToolNo)+","+inttos(t.t.CorrNo)+","+inttos(Int(t.t.SpindleMaxRotSpeed))+","+ftos(t.t.Radius)+","+ftos(Len1)+","+ftos(0)+","+ftos(0)+")","S"+ftos(t.t.SpindleMaxRotSpeed)+" R"+ftos(t.t.Radius)+" L1:"+ftos(t.t.Length)+" L2:"+ftos(0)+" L3:"+ftos(0))
				End If
				
			End If
		End If
		BoxNoArray(i)=t.t.ID
		'LastBoxId=t.t.ID
	Next i
	wcnccom("")
	
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
' ** Werkzeugwechsel - Abhandlung
' *****************************************************************************************
' t= actt
' spindlecode = 00110101 etc.
' ids = 109,110,112, etc.
Function MT_WZW   '

Dim H_Id As Variant   ' Aggregate Head id 
Dim TC_Id As Variant    ' Tool - Changer Head id 

Dim TC_PlaceNo As Variant   ' Place - No toolchanger
Dim ID As Variant   ' Campus - No ID

Dim LiftPosC As Variant   ' Lift - pos c-axis
Dim CanLift As Variant   ' lift aggregate possible

Dim Change_Mode As Variant
'Dim Change_Curve As Variant

Dim xp As Variant   ' X-pos

Dim accel As Variant   ' Achsbeschleunigung

Dim flex_id As Variant   ' fuer Flexkopf die Kennung


Dim offx,offy,offz As Double
	
Dim t As THopsBasicToolExt 
Dim Flex_T As IIHopsBasicTool

Dim Sub_TC_Id As Variant   ' Tool - Changer Head id fuer HSK F40 sub tool
Dim Sub_TC_PlaceNo As Variant   ' Place - No toolchanger fuer HSK F40
' Neu MW 07.11.2005
Dim Add_Field1000 As Variant  ' fuer Vario WSG  SubTool
Dim Add_Field1001 As Variant  ' fuer Vario WSG  ID

Dim Z2_Dyn As Double   
Dim LevelSpindleControl1 as integer
Dim LevelSpindleControlValue as string

	t = ActT

	' fix
	H_Id = t.Hid '  Aggregats Head Id
	
	' Vario Flexkopf - Kennung
	If t.T.ObjectType=htokTC_AccessGearBoxTool Then
		' = Werkzeug auf Flexkopf
		ID = t.t.ToolNo   '  Campus - internal ID fuer Flexgetriebe Kennung
		' Neu MW 14.4.2005
		ID = t.t.GearBox.ToolNo
		Set Flex_T = TDATA.GetTool_ID(t.t.ID)
		
		' Neu MW 07.11.2005
		If Not t.t.GearBox.Additions.GetAddition_ID(1000) Is Nothing Then
			Add_Field1000 = t.t.GearBox.Additions.GetAddition_ID(1000).Value
			ID = Add_Field1000 
		Else
			pp_err(0," - ID 1000 SUBTYPE Agg:")
		End If
		

	Else
		ID = t.t.ID   '  Campus - No ID
	End If
	
	TC_Id = ""   ' toolchanger Head ID
	TC_PlaceNo = ""
	LiftPosC = ""
	CanLift = ""
	
	Change_Mode = MT_Get_TCMode
	'AK 21.09.2011 naechste XPosition im ToolChangezyklus mitgeben
	'If Marker.XPosAfterToolChange<>0 Then
	'	xp = Marker.XPosAfterToolChange
	'	Marker.XPosAfterToolChange=0
	'End If 	

	
	If MT_Is_TC_T(t) Then
		' Tool - on toolchanger
		TC_Id = t.T.GetOn_TC.HeadID
		TC_PlaceNo = t.t.GetPlaceID_OnTC 't.T.ToolNo_Place
		
		If PostSettings.GeneralSettings.RelativToRefSpindle Then
			' MW 12.01.2015 -> Offset bereits verrechnet
			xp = (ViewBefore.SPVX) 
		Else
			xp = (-t.h.CenterX+ ViewBefore.SPVX) 
		End If

	ElseIf MT_IsDH(t) Then
		' Drilling Head
		'offx = MT_Get_BasicToolPlace_OffsetX(ActT.t,Ids)  ' gets offset x of the first driller in row
		'offy = MT_Get_BasicToolPlace_OffsetY(ActT.t,Ids)  ' gets offset y of the first driller in row
		'offz = MT_Get_BasicToolPlace_OffsetZ(ActT.t,Ids)  ' gets offset z of the first driller in row
		
		'xp = (ActV.SPVX+offx)
		' MW 12.01.2015 
		xp = ViewBefore.SPVX
	End If
	
	' Achtung Sicherheit nur moeglich, wenn reale Werkzeugdaten bekannt
	' sind. Momentan ist T-Nummer = Platznummer
	'zs = t.T.GetSecurityZ(ViewBefore.TipA)
	
	CanLift = IIf(t.T.CanLift,1,0)
	If CanLift Then
		LiftPosC= t.T.PosCForLift
	End If
	
	' Achsbeschleunigung aus der Schneide holen
	If Not t.t_cedge Is Nothing Then	
		' todo - gilt nicht fuer Bohrkopf
		accel = t.T_Cedge.AxisSpeedUp
		
		' AK 26.04.2019 Spindelauslastungsüberwachung manipulieren anhand Zusatzparameter in Schneide
		LevelSpindleControl1=0
		If not t.t_cedge.Additions.GetAddition_ID(13001) Is Nothing then
			if Val(t.t_cedge.Additions.GetAddition_ID(13001).value)>0 then
				LevelSpindleControl1= Val(t.t_cedge.Additions.GetAddition_ID(13001).value)
				
				If LevelSpindleControl1>100 then
					LevelSpindleControl1=100
				End If
				If LevelSpindleControl1<0 then
					LevelSpindleControl1=0
				End If
			End If			
		End If
		
		If LevelSpindleControl1>0 then
			accel = (LevelSpindleControl1*-1)
		END IF
			
	End If
	
	
	' Flexkopf - Kennung
	If t.T.ObjectType=htokTC_AccessGearBoxTool Then
		' Neu MW 07.11.2005
		If Not t.t.GearBox.Additions.GetAddition_ID(1001) Is Nothing Then
			Add_Field1001 = t.t.GearBox.Additions.GetAddition_ID(1001).Value
			flex_id = Add_Field1001
		Else
			pp_err(0," - ID 1001 FLEXID Agg:")
		End If
		
		'flex_id=1    ' momentan wird nur 1 Flexwerkzeug unterstuetzt
	Else
		flex_id=""
	End If
	
	MT_WRITE_WZW(H_Id,TC_Id,TC_PlaceNo,ID,LiftPosC,CanLift,Change_Mode,xp,accel,flex_id)
	
	' Fuer Flexkopf folgt jetzt der Sub- Wechsel
	If t.T.ObjectType=htokTC_AccessGearBoxTool Then
		' HeadId und anderes bleibt	
		wcnccom("sub change flex-tool")
		ID = t.t.ID   '  Campus - No ID
		Sub_TC_Id= t.T_TCA_GB.Tool.GetOn_TC.HeadID
		
		Sub_TC_PlaceNo = t.T_TCA_GB.Tool.GetPlaceID_OnTC 't.T.ToolNo_Place
		MT_WRITE_WZW(H_Id,Sub_TC_Id,Sub_TC_PlaceNo,ID,LiftPosC,CanLift,Change_Mode,xp,accel,flex_id)
	End If


End Function



Function MT_WRITE_WZW(Head_Id,TC_Id,TC_PlaceNo,ID,LiftPosC,CanLift,Change_Mode,xp,accel,flex_id)
Dim NCStr As String ' String for NC-Prog
Dim RangeXMin,RangeXMax As Double
Dim RangeYMin,RangeYMax As Double
Dim RangeZMin,RangeZMax As Double
' MW 30.05.2017 Drehzahl, Drehrichtung und Uebersetzungsverhaeltnis mit uebergeben
Dim dr As Long   ' Spindle - Direction
Dim dz As Long   ' Tool - Speed (programmed speed)
Dim gr As Double ' GearRatio - Uebersetzungsverhaeltnis

	dr=0 
	dz=0 
	gr=0

	If Not actt.t Is Nothing Then
		If MT_Is_TC_T(actt) Then
			' MW 16.12.2013 Nur WZW - Tools
		   MT_Get_RangeXYZ(ActT,RangeXMin,RangeXMax,RangeYMin,RangeYMax,RangeZMin,RangeZMax)
		   
			If (JobPara.npx + xp + TDATA.GetProcessHead_ID(Head_Id).CenterX) < RangeXMin Then
				' X-Minus Endlage bei Vorpositionierung X
				xp = RangeXMin + 1 - TDATA.GetProcessHead_ID(Head_Id).CenterX
				xp = xp - JobPara.npx  ' MW 13.05.2014 Vorpos. im Bezug auf Werkstueck Nullpunkt
			End If
			
		   
			If (JobPara.npx + xp + TDATA.GetProcessHead_ID(Head_Id).CenterX) > RangeXMax Then
				' X-Minus Endlage bei Vorpositionierung X
				xp = RangeXMax +(-1) +(-TDATA.GetProcessHead_ID(Head_Id).CenterX)
				xp = xp - JobPara.npx  ' MW 13.05.2014 Vorpos. im Bezug auf Werkstueck Nullpunkt
			End If
		End If
	End If
	
   
'	xp=""
'	wcnccom("Hid:"+inttos(Head_Id)+" TCID:"+inttos(TC_Id))
'	wcnccom("PlaceNo:"+inttos(TC_PlaceNo))            '+ " ID:"+inttos(ID))
'	wcnccom("Liftpos C:"+inttos(LiftPosC)+" CanLift:"+IIf(CanLift,"JA","Nein"))
'	wcnccom("TC-Mode :"+inttos(Change_Mode))
'	wcnccom("XPOS :"+inttos(xp))
'	wcnccom("LIFTMODE: "+inttos(ActT.liftmode))
	
	'NCStr = SPF_TC+"("+IntToS(Head_Id)+","+IntToS(H_Typ)+","+IntToS(TC_Id)+","+IntToS(TC_Typ)+","+IntToS(TC_PlaceNo)+","+IntToS(ID)+","+IntToS(LiftPosC)+","+IntToS(CanLift)+","+IntToS(Change_Mode)+","+IntToS(Change_Curve)+","+IntToS(xp)+")"
	     
	'NCStr = SPF_TC+"("+IntToS(Head_Id)+","+IntToS(TC_Id)+","+IntToS(TC_PlaceNo)+","+IntToS(ID)+","+IntToS(LiftPosC)+","+IntToS(CanLift)+","+IntToS(Change_Mode)+","+IntToS(xp)+")"
	
	
	
	NCStr = SPF_TC+"("+IntToS(Head_Id)+","+IntToS(TC_Id)+","+IntToS(TC_PlaceNo)+","+IntToS(ID)+","+IntToS(LiftPosC)+","+IntToS(CanLift)+","+IntToS(Change_Mode)+","+IntToS(xp)+","+IntToS(accel)+","+inttos(flex_id)+")"
	
	If NCStr <> Last_TC_Call_NCStr Then
	
		If JobPara.isg Then

			If MT_Is_TC_T(actt) Then
				' MW 30.05.2017 - WZW-Aufruf mit zusätzlichem Drehzahlinformation - Wrike id#155399984
				If MT_NoTurningWithSpindelRot(actT) Then
					' Big Tool erst unmittelbar vor der Bearbeitung Spindel starten
				Else
					MT_Get_Speed_Data(actT,PPara.Speed,dr,dz,gr) ' rueckgabe dr,dz,gr	
				End If
			End If
			If JobPara.TC_SpeedInfo Then
				' mit Drehrichtung, Drehzahl und GearRatio
				isg_cc(SPF_TC,IntToS(Head_Id),IntToS(TC_Id),IntToS(TC_PlaceNo),IntToS(ID),IntToS(LiftPosC),IntToS(CanLift),IntToS(Change_Mode),intToS(xp),intToS(accel),inttos(flex_id),IntToS(dr),IntToS(Abs(dz)),Ftos(gr))
			Else
				isg_cc(SPF_TC,IntToS(Head_Id),IntToS(TC_Id),IntToS(TC_PlaceNo),IntToS(ID),IntToS(LiftPosC),IntToS(CanLift),IntToS(Change_Mode),intToS(xp),intToS(accel),inttos(flex_id))
			End If
			
		Else
			' old Siemens
			wcnc(NCStr)
		End If
		
	End If
	Last_TC_Call_NCStr = NCStr

	
End Function


' *****************************************************************************************
' ** Werkzeugwechsel - Speed Abhandlung
' *****************************************************************************************

Function MT_Write_Speed(T As THopsBasicToolExt,pspeed,Optional Gear_Ratio,Optional CP As Variant )   ' MW 13.01.2015 CP -> POS pneum.schwenk.Saege

Dim H_Id As Long   ' Aggregate Head id 
Dim H_Typ As String  ' Aggregate Typ
Dim TNo As Variant   ' Tool - T-No
Dim DNo As Variant   ' Tool - D-No

Dim dr As Long   ' Spindle - Direction
Dim dz As Long   ' Tool - Speed (programmed speed)

Dim xp As Variant   ' X-pos waehrend Spindel - Anlauf
Dim yp As Variant   ' Y-pos waehrend Spindel - Anlauf
Dim zp As Variant   ' Z-pos waehrend Spindel - Anlauf

Dim offx,offy,offz As Double   ' actual Tool - offset for axis prepositioning
Dim Raster_Angle As Double

' -- 
' --  MW 27.11.2008 08:11:39
' --
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
    	' -- 
    	' --  MW 13.02.2009 11:53:09
    	' --
    	Gear_Ratio = 1
    End If
    
	H_Id = T.Hid '  
	H_Typ = "" 
	
	TNo = inttos(T.t.ToolNo)
	DNo = inttos(T.T.CorrNo)
	
	dz = inttos(MT_Get_SpindleSpeed(ActT,pspeed))
	dr = IIf(dz<0,4,3)
	xp = ""
	yp = ""
	zp = ""
	
	If Not T.T.GetOn_TC Is Nothing Then
		' Tool - on toolchanger
		If Not T.h Is Nothing Then
			If T.h.ToolPlaces.Count = 1 Then
				' -- mehr wie einen Ausgang gibt derzeit nicht
				Speed_Trans_MU = T.h.ToolPlaces.GetToolPlace_Index(0).GearRate
				Speed_Trans_GB = 1 ' falls nicht Winkelgetriebe
			Else
				pp_err(0,"Gear ratio - more than one main unit output")
			End If
			If Not T.t_gb Is Nothing Then
				' -- dann Werkzeug auf Winkegetriebeausgang
				Speed_Trans_GB = T.t_gb.GB_ToolPlace.GearRate
			End If
		End If
		Speed_Trans_complete = Speed_Trans_MU*Speed_Trans_GB
		
		
	ElseIf MT_IsDH(T) Then
		' Drilling Head
		' Tx Dx ueberschreiben mit korrekter Einstellung	
		TNo = ""
		DNo = ""
		dz = inttos(MT_Get_SpindleSpeed(ActT,pspeed))
		
		' --  uebersetzungsverhaeltnis DH
		Speed_trans_DH = Gear_Ratio
		
		Speed_Trans_complete = Speed_trans_DH
		
	ElseIf MT_isDHSaw(T) Then
		' Nutsaege auf Drilling Head
		If T.t_dhsaw.RotDirection = rdLeft Then
		   dr=3
		ElseIf T.t_dhsaw.RotDirection = rdRight Then
			dr=4
		ElseIf T.t_dhsaw.RotDirection = rdLeftRight Then
		End If
		' Neu MW 09.08.2005  auch programmierte Drehzahl nehmen
		dz = inttos(MT_Get_SpindleSpeed(ActT,pspeed))
		' --  uebersetzungsverhaeltnis DH
		If Not T.t_dhsaw Is Nothing Then
			Speed_trans_DH = T.t_dhsaw.DH_ToolPlace.GearRate
		End If
		Speed_Trans_complete = Speed_trans_DH
		
	ElseIf MT_isPneumaticSaw(T) Then
		' pneumatische Saege
		' wird immer erst im Viewchange aufgerufen - dadurch actv.rota moeglihc
		' MW 13.01.2015 CP wird jetzt uebergeben
		If IsEmpty (CP) Or Not IsNumeric(CP) Then
			pp_err(0,"pneum.saw?")
		End If
		'MT_GetPneumaticSawAngle(T,ActV.RotA,Raster_Angle)
		'CP = Raster_Angle 
		' --  uebersetzungsverhaeltnis DH
		If Not T.t.PH_ToolPlace Is Nothing Then
			Speed_trans_PH = T.t.PH_ToolPlace.GearRate
		End If
		Speed_Trans_complete = Speed_trans_PH
		
		
	Else
		If MT_IsProcessHeadTool(T) Then
			' -- 
			' --  MW 27.11.2008 08:46:55
			' --
			' --  uebersetzungsverhaeltnis z.B. SchloKa
			If Not T.t.PH_ToolPlace Is Nothing Then
				Speed_trans_PH = T.t.PH_ToolPlace.GearRate
			End If
			Speed_Trans_complete = Speed_trans_PH

		End If
	
	End If
	
	' Achtung Sicherheit nur moeglich, wenn reale Werkzeugdaten bekannt
	' sind. Momentan ist T-Nummer = Platznummer
	'zs = t.T.GetSecurityZ(ViewBefore.TipA)

	MT_Speed_Call(H_Id,H_Typ,dr,dz,xp,yp,zp,IIf(IsNumeric(CP),CP,""),Speed_Trans_complete)
	

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
						 ' 4 = Saege in X-Richtung 1-32
						 ' 5 = Saege in Y-Richtung 1-32


Dim NCStr As String ' String for NC-Prog
Dim Orientation As Variant
Dim one_spindle As Long
Dim FirstTNr As Long

	FirstTNr = Val(Get_First_Token(tools))   
	
	' fix
	H_Id = T.Hid '  Aggregats Head Id
	
	H_Typ = ""   '  Aggregate Head Typ
	
	If FirstTNr <= 0 Then
		' Werkzeugabwahl
		Code.GroupCode = 0     ' 0=alles zuruecksetzen  marker.last_bm.GroupCode
		Code.BM1=0
		Code.BM2=0
		Code.BM3=0
	Else
		' Spindelcodierung anhand angegebener Spindelnummer ermitteln
		' und zurueckgeben in Bm1 und BM2, BM3
		MT_Get_SpindleCode_Dez(tools,Code)
		If ActT.t.ObjectType = 7 Then
			' Saege auf Bohrkopf
			Orientation = ActT.t_dhsaw.DH_ToolPlace.Orientation
			If (Orientation=orYPlus) Or (Orientation=orYMinus) Then	
				Code.GroupCode=4
			ElseIf (Orientation=orXPlus) Or (Orientation=orXMinus) Then	
				Code.GroupCode=5
			Else
				pp_err(351)
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
				pp_err(351)
			End If
		
		End If
	End If
	
	NCStr = SPF_DHCode+"("+IntToS(H_Id)+","+IntToS(Code.GroupCode)+","+IntToS(Code.BM1)+","+IntToS(Code.BM2)+","+IntToS(Code.BM3)+")"
	
	
	If (Code.BM1 <> Marker.last_bm.BM1) Or (Code.BM2 <> Marker.last_bm.BM2) Or (Code.BM3 <> Marker.last_bm.BM3) Then
		If JobPara.isg Then
			isg_CC(SPF_DHCode,IntToS(H_Id),IntToS(Code.GroupCode),IntToS(Code.BM1),IntToS(Code.BM2),IntToS(Code.BM3))
		Else
			wcnc(NCStr)
		End If
    	wcnccom("BM1:"+ftos(Code.BM1))
	    If Code.BM2>0 Then
	    	wcnccom(" * BM2:"+ftos(Code.BM2))
	    End If
	    If Code.BM3>0 Then
	    	wcnccom(" * BM3:"+ftos(Code.BM3))
	    End If
		' evtl. ueberpruefung, ob Bohrkopf -bohrer vorgelegt etc.
		'MT_Write_Check_Spindle
		' 
	    
	End If
	Marker.Last_Bm.BM1 = Code.BM1
	Marker.Last_Bm.BM2 = Code.BM2
	Marker.Last_Bm.BM3 = Code.BM3
	Marker.Last_Bm.GroupCode = Code.GroupCode
	
	PosReset
End Function


Function MT_Speed_Call(Hid,HTyp,dr,dz,xp,yp,zp,CP,Optional Gear_Ratio)
Dim NCStr As String ' String for NC-Prog

  'A.K. 29.01.2008
  'Vor TSpeed immer T/D Ausgabe
  If mill_c_activ() Then
  	wcnccom("AKNEU")
  	' --  for ISG Controller
  	WCNC_IDD("TCARROFF",ActT.T.ToolNo,ActT.T.CorrNo)
  	
   	'wcnc(g_TCARROFF+"T"+IntToS(ActT.T.ToolNo)+" D"+IntToS(ActT.T.CorrNo))
  Else
  End If
  	' MW 20.09.2011 - immer vor SPEED - CALL Werkzeug bekanntgeben
	If ((ActT.T.ToolNo>0) And (ActT.T.CorrNo>0)) Then
		wcnccom("AKNEU")
		wcncaddcom("T"+IntToS(ActT.T.ToolNo)+" D"+IntToS(ActT.T.CorrNo),"SpeedCall",True)
	End If

	'wcnccom("Hid:"+inttos(Hid)+" HTyp:"+inttos(wn)+" TNo:"+inttos(tn)+" DNo:"+inttos(dn)+" DrehRicht:"+inttos(dr)+" Drehzahl:"+inttos(dz)+")")
	If JobPara.isg Then
		If Not IsMissing(Gear_Ratio) And Not IsEmpty(Gear_Ratio) Then 
			isg_cc(SPF_TSpeed,IntToS(Hid),IntToS(dr),IntToS(Abs(dz)),IntToS(xp),IntToS(yp),IntToS(zp),IntToS(CP),Ftos(Gear_Ratio))
		Else
			isg_cc(SPF_TSpeed,IntToS(Hid),IntToS(dr),IntToS(Abs(dz)),IntToS(xp),IntToS(yp),IntToS(zp),IntToS(CP))
		End If
	Else
		NCStr = SPF_TSpeed+"("+IntToS(Hid)+","+IntToS(dr)+","+IntToS(Abs(dz))+","+IntToS(xp)+","+IntToS(yp)+","+IntToS(zp)+","+IntToS(CP)+")"
		wcnc(NCStr)
	End If
	

	
End Function


' *****************************************************************************************
' ** Ermittlung Spindle - Ausgangsdrehzahl ueber uebersetzung etc.
' ** zusaetzlich ueberpruefung Min - Max - Speed findet in Plausi statt
' *****************************************************************************************
Function MT_Get_SpindleSpeed(T As tHopsBasicToolExt,pspeed)
Dim OutPut_Spindle As Double
Dim Max_ToolSpeed, Min_ToolSpeed As Double    ' vom Werkzeug selbst
Dim Max_HeadSpeed, Min_HeadSpeed As Double	  ' vom Bearbeitungskopf
Dim Speed As Double 
	Speed = pspeed

	MT_GetMinMaxToolSpeed(T,Min_ToolSpeed,Max_ToolSpeed)
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
	If (Not MT_IsProcessHeadTool(T)) And (Not MT_IsDH(T)) And (Not MT_isDHSaw(T)) Then
	    If Not T.h Is Nothing Then
	    	If Not T.h.ToolPlaces Is Nothing Then
	    		If Not T.h.ToolPlaces.GetToolPlace_Index(0) Is Nothing Then
			    	If T.h.ToolPlaces.GetToolPlace_Index(0).ReverseRotDirection = True Then
						OutPut_Spindle = - OutPut_Spindle
					End If
					If Not equal(T.h.ToolPlaces.GetToolPlace_Index(0).GearRate,0) Then
				    	OutPut_Spindle = OutPut_Spindle / T.h.ToolPlaces.GetToolPlace_Index(0).GearRate 
				    End If
				End If
			End If
	    End If
	
	End If
    'If T.T.ObjectType=htokStandardTool Then	
    If MT_Is_TC_T(T) Then	
    	' -- check Spindeldrehzahl fuer alle Werkzeuge auf einer Wechselspindel
    	
    	' 2. Werkzeugdrehgeschwindigkeit checken im Bezug auf Spindeldefinition!
		MT_GetMinMaxHeadSpeed(T,Min_HeadSpeed,Max_HeadSpeed)
    	If Abs(OutPut_Spindle) > Max_HeadSpeed Then
    	   OutPut_Spindle = IIf(OutPut_Spindle<0,-Max_HeadSpeed,Max_HeadSpeed)
    	End If
    	If Abs(OutPut_Spindle) < Min_HeadSpeed Then
    	   OutPut_Spindle = IIf(OutPut_Spindle<0,-Min_HeadSpeed,Min_HeadSpeed)
    	End If
    End If
    If MT_isDHSaw(T) Then	
    	' -- check Spindeldrehzahl fuer Saege auf Bohrkopf
    	
    	' 2. Werkzeugdrehgeschwindigkeit checken im Bezug auf Spindeldefinition!
		MT_GetMinMaxHeadSpeed(T,Min_HeadSpeed,Max_HeadSpeed)
    	If Abs(OutPut_Spindle) > Max_HeadSpeed Then
    	   OutPut_Spindle = IIf(OutPut_Spindle<0,-Max_HeadSpeed,Max_HeadSpeed)
    	End If
    	If Abs(OutPut_Spindle) < Min_HeadSpeed Then
    	   OutPut_Spindle = IIf(OutPut_Spindle<0,-Min_HeadSpeed,Min_HeadSpeed)
    	End If
    End If

    MT_Get_SpindleSpeed=(OutPut_Spindle)
End Function


Function MT_GetMinMaxToolSpeed(T As tHopsBasicToolExt,Min_ToolSpeed,Max_ToolSpeed)

	If T.t.ObjectType=htokDrillingHeadTool Then
		Min_ToolSpeed = T.t.SpindleMinRotSpeed	
		Max_ToolSpeed = T.t.SpindleMaxRotSpeed	
	ElseIf T.T.ObjectType=htokDH_SawTool Then	
		' Es handelt sich um ein Groove Saw on DrillingHead ' ObjectType = 7
		Min_ToolSpeed = T.t.MinRotSpeed	
		Max_ToolSpeed = T.t.MaxRotSpeed	
		
	Else
		Min_ToolSpeed = T.t.MinRotSpeed	
		Max_ToolSpeed = T.t.MaxRotSpeed	
		If MT_IsGearBoxTool_TC_Access(T) Then
			' Neu MW 23.11.2005 
			' fuer Werkzeug auf TC-Access-Tool
			If T.gb.MinRotSpeed < Min_ToolSpeed Then
				Min_ToolSpeed = T.gb.MinRotSpeed	
			End If
			If T.gb.MaxRotSpeed < Max_ToolSpeed Then
				Max_ToolSpeed = T.gb.MaxRotSpeed	
			End If
		End If
	
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
	If ActT.t.CorrNo < 8 Then
		wcnc("D"+IntToS(ActT.T.CorrNo))
	Else
		pp_err(353)
	End If
End Function

Function MT_Write_Act_T_Correction
	wcnc("T"+IntToS(ActT.T.ToolNo))
End Function

Function MT_Write_Call_Correction
Dim X,Y,Z As Double
Dim dx,dy,dz As Variant
Dim length As Double
Dim Rota As Double
Dim Tipa As Double
Dim center_z As Double
Dim l1x,l1y,l1z,l2x,l2y,l2z,l3x,l3y,l3z,v1x,v1y,v1z,v2x,v2y,v2z,a1,a2 As Variant

	If ActT.T.CorrNo < 10 Then
'		If mill_c_activ And ( MT_IsGearBoxTool(ActT) Or MT_IsGearBoxTool_TC_Access(ActT) )  Then
'			' Fraesen mit mitgefuehrter C-Achse
'			' Offset auf Werkzeugspitze errechnen 
'			
'			' MW 11.01.2016  ????????????????????????
'			' MW 19.01.2016  Engine rechnet offset X/Y aber kein Z ???????????????
'			actt.t_gb.Get_OffsetToolRefPoint(0,ProcessPara.MinTipA,dx,dy,dz)
'			
'			' Offset Z auf Werkzeugspitze verrechnen - X/Y uebernimmt Engine
'			wcnc_IDD("ATRANSZ",-dz-actt.t.Length)
'			
'			wcnc("T"+IntToS(ActT.T.ToolNo)+" D"+IntToS(ActT.T.CorrNo))
' ===> MW 20.01.2016 Bei 4-Achs Maschinen wird ueber WriteNCMillingPointsHeadData=true gefraest
		
		'If ( MT_IsGearBoxTool(ActT) ) Or ( MT_IsGearBoxTool_TC_Access(ActT)) Or ( MT_IsGearBoxTool_Special(actt) ) Or (MT_isPneumaticSaw(actt)) Then
		If MT_IsGB(actt) Then
			' TCarr set the parameters with Cycle
			If ( MT_Get_TP_Offset_XYZ(actt,X,Y,Z)) And ( MT_Get_TP_Len(actt,length) ) And ( MT_Get_TP_TipAngle(Tipa) ) And ( MT_Get_TP_RotAngle(Rota) ) Then
		    	' Neu MW 16.11.2005
		    	If MT_IsGearBoxTool_Special_Vertical(actt) Then
		    		' Getriebe Special Mehrfachbohrgetriebe
			    	a1=360' MW 26.04.2019 wurde nie mit wert belegt  -MultiDrilling_GBHeadVert.dw
			    ElseIf MT_Is_UndersideTool(actt) Then
			    	a1=360-UndersideTool.view_w
			    	' MW 12.04.2010  - auch negative OffsetX/OffsetY - Werte koennen die Ausgangsrichtung bestimmen!
			    	' die Parameter, welche aber auf den TCARR gehen muessen absolut sein!
			    	X = Abs(X)
			    	Y = Abs(Y)
			    	a1=Norm0_360(360-UndersideTool.view_w     +   90)
			    
			    ElseIf (MT_H_Is_3_Axis(actt)) Then
			    	' MW 30.08.2019 - Winkelgetriebe (CLAMEX) nicht drehbar d.h. hor. Laengen - Verrechnung ist von der Ausgangsrichtung abhaengig
			    	' Lösung suchen für das Erkennen von gedrehten CLAMEX-Teilen (Betternest) "komplementäre Schneide" 
			    	' https://www.wrike.com/open.htm?id=120675377
			    	' [Case ID#: 102636]
			    	' Ausrichtung anhand Winkelgetriebe Ausgangsrichtung
			    	a1 = actT.T_GB.GearBox.OffsetC + (-actT.T_GB.GB_ToolPlace.RotAngle) +90    ' winkelgetriebe Gesamtoffset + Ausgangsoffset
		    	Else
			    	a1=360-ActV.RotA
			    	' Ausrichtung anhand Ebene
		    	End If
		    	While a1>=360.0
		    		a1 = a1 - 360
		    	Wend
		    	a2=ActV.TipA
		    	
			    If MT_isPneumaticSaw(actt) Then
			    	center_z=0
			    	' Achtung pneumatische Saege ist nicht immer gleich der Ebene
					a1 = Norm0_360(MT_GetPneumaticSawAngle(actt,ActV.TipA,ActV.RotA) -90)
					a1 = Norm0_360(360 - a1)
			    Else
		    		center_z=ActT.gb.CenterZ
		    	End If
			    l1x="" 
			    l1y=""
			    l1z=-Z-center_z
			    l2x=X 
			    l2y=Y
			    l3z=length
			    v1z=-1
			    v2x=1
				
		    	' Neu MW 16.11.2005
		    	If MT_IsGearBoxTool_Special_Vertical(actt) Or MT_IsGearBoxTool_Special_Horizontal(actt) Then
		    		' evtl. Offset wird von Engine verrechnet 
				    l1x=0
				    l1y=0
				    l1z=-Z-center_z
				    l2x=0 
				    l2y=0
				    l3z=0
				    v1z=-1
				    v2x=1
		    	End If
			    
			    If JobPara.isg Then
	 			    ' --  AK 21.09.2009
  			    ' --  T+D vor TCarr, da im Tcar Referenz auf Wkzlaenge
  			    	If MT_Is_UndersideTool(actt) Then
	  			        ' MW 03.04.2014  bei Unterflur Offset X/Y/Z selbst gerechnet
						l1z = 0
						l2x = 0
						l2y = 0
						l2z = 0
						
					ElseIf MT_H_Is_5_Axis(actt) And MT_IsGB(actt) Then
						' MW 25.07.2013 Sonderfall 5-Achs mit Winkelgetriebe wird ohne Kinematik betrieben !
						' Annahme 5-Achs Transformation (Kinematik) bezieht sich auf den imaginaeren Punkt (60.182)
						' ID 20022 addieren auf L1
						'l1z = l1z + actT.PH_Add.TraoriOffset_Z
  			    	End If
  			    	If Not MT_Is_UndersideTool(actt) Then
  			    		' MW 27.07.2018 - es ist bereits alles verechnet
						WCNC_IDD("TCARRACTIVATE",ActT.T.ToolNo,ActT.T.CorrNo)
						ISG_CC(SPF_TCarr,l1x,l1y,l1z,l2x,l2y,l2z,l3x,l3y,l3z,v1x,v1y,v1z,v2y,v2z,a1,a2)
						Marker.TCarr_Activ = True  ' MW 20.01.2015 - nur abschalten wenn auch aktiv
					End If
			    Else
					wcnc(SPF_TCarr+"("+ftos(l1x)+","+ftos(l1y)+","+ftos(l1z)+","+ _
				   ftos(l2x)+","+ftos(l2y)+","+ftos(l2z)+","+ _
				   ftos(l3x)+","+ftos(l3y)+","+ftos(l3z)+","+ _
				   ftos(v1x)+","+ftos(v1y)+","+ftos(v1z)+","+ _
				   ftos(v2x)+","+ftos(v2y)+","+ftos(v2z)+","+ _
				   ftos(a1)+","+ftos(a2)+")")
 '                 ftos(Rota)+","+ftos(Tipa)+","+ftos(length)+ _
 '                 ","+ftos(ActV.RotA)+","+ftos(ActV.TipA)+")")
	 			    ' --  AK 21.09.2009
  			    ' --  T+D vor TCarr, da im Tcar Referenz auf Wkzlaenge
  	  		  WCNC_IDD("TCARRACTIVATE",ActT.T.ToolNo,ActT.T.CorrNo)
			    
			    End If
			    
	
			    
			    
			Else
				' Fehlerfall
				pp_err(354)
			End If
			' 
			' working with TCarr   - orientierbare Werkzeugtraeger
			' --  for ISG Controller
	    ' --  AK 21.09.2009
	    ' --  Aktivierungsaufruf je nach Variante im oberen Bereich
      '			WCNC_IDD("TCARRACTIVATE",ActT.T.ToolNo,ActT.T.CorrNo)
			
			'wcnc(g_TCARR + " T"+IntToS(ActT.T.ToolNo)+" D"+IntToS(ActT.T.CorrNo))
		Else
			' every other kind of tools  -  calls standard Tx Dx
			wcnc("T"+IntToS(ActT.T.ToolNo)+" D"+IntToS(ActT.T.CorrNo))
		End If
	Else
		pp_err(353)
	End If
End Function



' Saege auf Bohrkopf
Function MT_isDHSaw(T As tHopsBasicToolExt)
	MT_isDHSaw = False
	If Not T.T_DHSaw Is Nothing Then
		MT_isDHSaw= ((T.t.ObjectType=7)) 
	End If
End Function


Function MT_Is_TC_T(T As tHopsBasicToolExt)
	MT_Is_TC_T = False
	If Not T.t Is Nothing Then
		If Not T.t.GetOn_TC Is Nothing Then
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


' -- pneumatische Saege
Function MT_isPneumaticSaw(T As tHopsBasicToolExt)
Dim raster As Boolean
Dim TpCount As Integer
Dim Resu As Boolean

	Resu = False
	
	If Not T.T_PH Is Nothing Then
		If (T.t_ph.ProcessHead.RotType = atRaster) And MT_IsProcessHeadTool(T) And MT_isSaw(T) Then
			Resu = True
		End If
	End If
		
	MT_isPneumaticSaw = Resu   ' (raster) And  ((T.t.AggNo>=DEF_PSaeg1)Or (T.t.AggNo<=DEF_PSaeg1+4))
		
	
End Function

' -------------------------------------------------------------------------
' ueberpruefungsroutine, ob vorheriges Tool und aktuelles Tool pneumatisch Saege
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
		If equal(t.T_GB.GB_ToolPlace.TipAngle,180) Then
			' Unterflurgetriebe
			result = True
		End If
		If t.T_GB.GB_ToolPlace.TipType = aatFix Then
			' 
		End If
	End If
	MT_Is_UndersideTool = result
End Function

' *****************************************************************************************
' ** Winkelgetriebe mit Wechslerzugriff
' *****************************************************************************************
Function MT_IsGearBoxTool_TC_Access(t As THopsBasicToolExt)
	
	MT_IsGearBoxTool_TC_Access=False
	' wenn True dann ist es ein Winkelgetriebe mit Werkzeugwechsel - Moeglichkeit
	' und gleichzeitig auch Schwenkbar 
	If Not t.t Is Nothing Then
		MT_IsGearBoxTool_TC_Access = (t.t.ObjectType=htokTC_AccessGearBoxTool)
	End If

End Function


' Winkelgetriebe ohne Wechslerzugriff aber stellbarer Kippachse
' also das ist eigentlich Winkelgetriebe mit (4. bzw. 5. Achse)
Function MT_Is_GearBoxTool_With_FreeTiltAxis(t As THopsBasicToolExt)
Dim result As Boolean
	result = False

	If MT_IsGearBoxTool(t) Then
		If Not t.T_GB.GB_ToolPlace Is Nothing Then
			If t.T_GB.GB_ToolPlace.TipType=TAggAxisKind.aatAxis Then
				' ok
				result = True
			End If
		End If
	Else
	  If MT_IsGearBoxTool_TC_Access(T) Then
			result = True  
	  End If
	End If
	MT_Is_GearBoxTool_With_FreeTiltAxis = result
End Function



' *****************************************************************************************
' ** Nebenaggregat
' *****************************************************************************************
Function MT_IsProcessHeadTool(t As THopsBasicToolExt)
	
	MT_IsProcessHeadTool = (t.t.ObjectType=htokProcessHeadTool)

End Function


' *****************************************************************************************
' ** Alle Werkzeugwechselspindeln mit dem 1. Werkzeug ruesten
' ** !!! -> ausser actt welches anschliessend benutzt wird
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
Dim FirstUsedTool As THopsBasicToolExt   ' fuer 1. benutztes Werkzeug auf der Spindel

Dim ID As Variant
Dim t_array() As Integer



Exit Function
' ein paar Feinheiten fehlen noch
' es muss noch ueberprueft werden, ob z.B. das 1. Werkzeug fuer beide Spindeln
' dasselbe ist. 
' Im Falle eines Winkelgetriebes, muss ueber die Gearbox-ID gecheckt werden, ob
' das Werkzeug bereits auf der anderen Spindel vorgewechselt wurde!

	' ------------------------------------------------------
	' -- alle vorhandenen Werkzeugwechselspindeln durchgehen 
	' -- (die welche auf einen Wechsler zugreifen koennen)
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
			' -- Spindel mit 1. benutzten Werkzeug fuellen, falls an einer Bearbeitun beteiligt 
			' -- 1. benutztes Werkzeug ermitteln ueber Function MT_Get_FirstUsedTool
			If MT_Get_FirstUsedToolBoxNo(Hid)>0 Then
				MT_SetTHopsBasicToolExt(FirstUsedTool,MT_Get_FirstUsedToolBoxNo(Hid),Hid)
			End If
			'Set FirstUsedTool.T = TDATA.GetTool_ID(MT_Get_FirstUsedTool(Hid))
			'firstUsedTool.Hid = Hid
			If (Not FirstUsedTool.T Is Nothing) Then
				If Not (MT_Is_Tool_Used_Before_From_Another_Head(FirstUsedTool)) Then
					' -- found Spindel mit gefundenem Werkzeug fuellen
					'bm = ""  ' drilling Head 
					'dn = inttos(FirstUsedTool.T.CorrNo)
					
					If Not FirstUsedTool.T.GetOn_TC Is Nothing Then
						' Tool - on toolchanger
						tn = FirstUsedTool.T.ToolNo
						pn = FirstUsedTool.T.ToolNo_Place
						wn = FirstUsedTool.T.GetOn_TC.HeadID
					Else
						'AddMistake(GetErrMsg("falscher Spindeltyp bei Ermittlung Spindel fuellen..")
					End If
					
					cs= FirstUsedTool.T.PosCForLift
					hz = IIf(FirstUsedTool.T.CanLift,1,0)

					If equal(hz,0) Then
						' -- Werkzeug kann nicht gehoben werden,
						' -- daher entfaellt Werkzeugaufruf
						' tn=-1
						wcnccom("")
						wcnccom("")
						wcnccom("Spindel "+inttos(Hid)+ " "+FirstUsedTool.aggname+ " nicht vorwechseln, da heben nicht zulaessig")
						wcnccom("")
						wcnccom("")
					Else
						' -- 1. Werzeug fuer Spindel einwechseln
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


Function MT_Tool_Re_Change(T As THopsBasicToolExt,ID)
' T = Lastt
' Actt = aktives Tool
	If Not T.t Is Nothing Then
		If MT_IsDH(T) Or MT_isDHSaw(T) Then
			' bohrkopf war im Einsatz mit Bohren oder mit Saegen
			MT_WRITE_DHCode(T,"")
		End If
		If MT_isDH_wasDH(ActT,T) Then
			' kein Motor aus bei wechhsel von Bohrkopf Bohren auf Bohrkopf Saegen
			' und keine Motor aus bei wechsel von Bohrkopf Saegen auf Bohrkopf bohren 
			' und keine Motor aus bei wechsel von Bohrkopf Saegen auf Bohrkopf Saegen
		Else

			' MW 04.01.2011 - Kombi-Tools
			
			If Not MT_GB_Output_Changed(ActT,T) And Not MT_TEdgeChange(ActT,T) Or (ID<0)Then
				' MW 21.02.2012 ID<0 immer aus!
				' bei einem Aggregatsausgang - Wechsel wird Motor nicht abgeschaltet
				WCNC_IDD("M5")
				If (MT_Is_Vertical_StandardTool5Axis(T)) And (PPara.PreObjectTyp = otNCInfoProcess) Then
					If NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Kind=7710 Then
						' Fuer NCINFOPROZESS DINISO Traori wieder abschalten
						wcnc_IDD(JobPara.TCP_OFF)
						wcnc("G"+IntToS(53+Fix_Zero))
					End If
				End If
' MW 21.01.2016 zu spaet
'				If (MT_Is_Vertical_StandardTool5Axis(T)) Then
'					' 5-Axis mit Traori
'					wcnc_IDD(T.ph_add.traorioff)'
'
'					'wcncaddcom(T.ph_add.traorioff," 5-Achs Transformation abschalten") ' TRAFOOF 
'					wcnc("G"+IntToS(53+Fix_Zero))
'				End If
			End If

			If MT_IsDH(T) Or MT_isDHSaw(T) Then
				' MW 10.01.2011 Vorlegbaren Bohrkopf zuruecklegen!
				If JobPara.isg Then
					wcnc("L CYCLE [NAME=CP_CLEARDH.NC @P1=1]")
				End If 	
			End If

		End If
		
		If JobPara.isg Then
			
   	        If ( MT_IsGearBoxTool(T) ) Or ( MT_IsGearBoxTool_TC_Access(T)) Or ( MT_IsGearBoxTool_Special(T) ) Or (MT_isPneumaticSaw(T)) Then
				
				' ToolCarrier abschalten
   	        
			  	WCNC_IDD("TCARROFF")
				
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
   		
   
   ElseIf (MT_IsGearBoxTool(T)) Or (MT_IsGearBoxTool_TC_Access(T)) Then

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
			' Saege auf Bohrkopf
			Set itp= actt.t_dhsaw.DH_ToolPlace
		Else
			' Bohrer
			Set itp= actt.t_dh.DrillingHead.ToolPlaces.GetToolPlace_PlaceID(TNr)
		End If
		Set Dh_TP=itp
		
		If Dh_TP.SpindleNo<=16 Then  'If Dh_TP.SpindleNo<=32 Then
		 	' Bitmuster 1 fuellen
			bm.BM1 = bm.BM1 + exponent2(Dh_TP.SpindleNo)
		ElseIf Dh_TP.SpindleNo<=32 Then   'ElseIf Dh_TP.SpindleNo<=64 Then
		 	' Bitmuster 2 fuellen
			bm.BM2 = bm.BM2 + exponent2(Dh_TP.SpindleNo-16)
		ElseIf Dh_TP.SpindleNo<=48 Then
		 	' Bitmuster 3 fuellen
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




Function MT_Write_Check_Spindle
	wcnc_IDD(SPF_AGGCheck)
End Function

Function MT_GB_Output_Changed(ActT As THopsBasicToolExt,LastT As THopsBasicToolExt) As Boolean
	MT_GB_Output_Changed = False
	If (Not LastT.t Is Nothing) And (Not ActT.t Is Nothing) Then
		' check ob Ausgangswechsel auf Aggregat
		If MT_IsGearBoxTool(ActT) Then
			If MT_IsGearBoxTool(LastT) And MT_IsGearBoxTool(ActT) Then
				' jetzt Wechsel von Aggregatausgang zu Aggregatausgang
		        If LastT.gb.ToolNo = ActT.gb.ToolNo Then
					MT_GB_Output_Changed = True   ' Wechsel von Ausgang zu Ausgang
		        End If
			End If
		ElseIf MT_IsGearBoxTool_Special(ActT) Then
			' Neu MW 16.11.2005 
			' auch fuer Specialwinkelgetriebe
			If MT_IsGearBoxTool_Special(LastT) And MT_IsGearBoxTool_Special(ActT) Then
				' jetzt Wechsel von Aggregatausgang zu Aggregatausgang
		        If LastT.gb.ToolNo = ActT.gb.ToolNo Then
					MT_GB_Output_Changed = True   ' Wechsel von Ausgang zu Ausgang
		        End If
			End If
		End If
	End If
	
End Function

Function MT_Request_Flexible_Axis(ByVal TipAngle,RotAngle)
Dim HeadID As Long
Dim ID As Long   ' Flex Kennung
Dim Rota,TipA As Variant
Dim MAX_Z2_Dyn As Double 
	' Neu MW 14.12.2005
	' hier kann der Rotangel auch durchaus mal noch negativ sein
    'If RotAngle>-1 Then
    If RotAngle>-360.01 Then

'    	Rota=GetHeadAnglesMath_GB(RotAngle)    ?????????????

    Else
        Rota=""
    End If

	HeadID = ActT.HId
	ID = 1
	
	' --  for ISG Controller
	WCNC_IDD(SPF_REQUEST_FLEX,HeadID,ID,TipAngle,Rota)
	
	'wcnc(SPF_REQUEST_FLEX+"("+Inttos(HeadID)+","+inttos(ID)+","+ftos(TipAngle)+","+ftos(Rota)+")")
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
	If (MT_IsGearBoxTool(t)) Or (MT_IsGearBoxTool_Special(t)) Or (MT_IsGearBoxTool_TC_Access(t)) Then
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


Function MT_GetOffsets_Pneumatic_Saw(t As THopsBasicToolExt,Raster_Angle,X,Y,Z)
Dim id As Integer
Dim dx,dy,dz As String

	id = ((Raster_Angle/90)+1)*10
	' ID 10/11/12 20/21/22 30/31/32 40/41/42
		
	dx=""
	dy=""
	dz=""
	X=0
	Y=0
	Z=0
	
	If Not t.t_PH.PH_ToolPlace Is Nothing Then
		If Not t.T_ph.PH_ToolPlace.Additions.GetAddition_ID(id) Is Nothing Then
			dx= t.T_ph.PH_ToolPlace.Additions.GetAddition_ID(id).Value 
			X= StrToFloat(dx)
		End If
		If Not t.T_ph.PH_ToolPlace.Additions.GetAddition_ID(id+1) Is Nothing Then
			dy= t.T_ph.PH_ToolPlace.Additions.GetAddition_ID(id+1).Value 
			Y= StrToFloat(dy)
		End If
		If Not t.T_ph.PH_ToolPlace.Additions.GetAddition_ID(id+2) Is Nothing Then
			dz= t.T_ph.PH_ToolPlace.Additions.GetAddition_ID(id+2).Value
			Z= StrToFloat(dz)
		End If
	End If
	
	
End Function

' -- 
' MW 24.09.2012
' AggOffX = Werkzeug - Aggregatverschiebung X
' SPVX = Anfahrposition auf die Ebene
' --
Function MT_PreChange(AggOffX,SPVX)

Dim H_Id As Variant   ' Aggregate Head id 
Dim TC_Id As Variant    ' Tool - Changer Head id 

Dim TC_PlaceNo As Variant   ' Place - No toolchanger
Dim id As Variant   ' Campus - No ID

Dim LiftPosC As Variant   ' Lift - pos c-axis
Dim CanLift As Variant   ' lift aggregate possible

Dim Change_Mode As Variant
'Dim Change_Curve As Variant

Dim activ As Boolean
Dim i,j As Integer
Dim activ_agg As Long
Dim  t As THopsBasicToolExt
Dim Stop_Prechange As Boolean 
Dim Same_GB As Boolean       ' MW 07.07.2015  Toolchanges von Winkelgetriebeausgaege ignorieren

	If Not JobPara.TC_PreInfo_Activ Then
		Exit Function
	End If
	
	activ_agg = ActT.HID
	
	' schauen, ob fuer aktives Aggregat naechstes Werkzeug auf selbigem Aggregat noch folgt 
	' dann vorwechsel aufrufen

	Stop_Prechange = False
	For i = marker.ActProcess To Marker.CountOfTool-1
		t= ToolArray(i)
		
		' MW 12.04.2012
		If (i+1) <= (Marker.CountOfTool-1) Then
			For j = (i+1) To (Marker.CountOfTool-1) 
				If ToolArray(j).PreChanged Then
					' Vorwechsel laeuft bereits -> Achtung nur korrekt fuer "einspindlige" Maschinen
					Stop_Prechange = True
					Exit For
				End If
			Next
		End If
		If Stop_Prechange Then
			Exit For
		End If
	
		
		' MW 07.07.2015  Toolchanges von Winkelgetriebeausgaege ignorieren
		Same_GB = False
	    If MT_IsGB(actt) And MT_IsGB(t) Then 
	    	' Winkelgetriebe 
	    	If t.gb.ToolNo = actt.gb.ToolNo Then
	    		Same_GB = True
	    	End If
	    End If
			
		
		'If (t.hid = activ_agg)   Then
			If t.t.ID <> ActT.t.ID Then
				If (t.t.ToolNo <> ActT.t.ToolNo) And (Not Same_GB) Then
					If (Not ToolArray(i).PreChanged) And (Not t.t.GetOn_TC Is Nothing) Then
						H_Id=t.HID
						id = t.t.ID   '  Campus - No ID
						TC_Id = t.T.GetOn_TC.HeadID
						TC_PlaceNo = t.t.GetPlaceID_OnTC
		
						wcnccom("-- Vorwechsel:"+t.t.Description)
						wcnccom("Headid:"+inttos(H_Id)+"  TC_Id:"+inttos(TC_Id)+"  TC_Platz:"+inttos(TC_PlaceNo)+"  Id:"+inttos(id))
						
						' MW 24.09.2012 - Naechste Sollpositioin in X mit Aggregat Offset
						AggOffX = t.h.CenterX '

						WCNC_IDD(SPF_PREINFO,H_Id,TC_Id,TC_PlaceNo,id,-1*AggOffX+SPVX)
						
						'wcnc(SPF_PREINFO+"("+IntToS(H_Id)+","+IntToS(TC_Id)+","+IntToS(TC_PlaceNo)+","+IntToS(id)+")")				
						
						ToolArray(i).PreChanged=True
						Exit For
					End If
				End If
			End If
		'End If
	Next i

	
End Function


Function MT_get_Add_ID(ActT As THopsBasicToolExt,id,isok As Boolean)
Dim Addi As IIAddition
	isok = False
	If ActT.t.ObjectType=htokStandardTool Then
		Set Addi = ActT.h.Additions.GetAddition_ID(id)
	ElseIf ActT.t.ObjectType=htokDrillingHeadTool Then
		Set Addi = ActT.t_dh.DrillingHead.Additions.GetAddition_ID(id)
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
Function MT_H_Is_5_Axis(t As THopsBasicToolExt)

Dim rot As Variant
Dim tip As Variant
	
	MT_H_Is_5_Axis = False
	
	
	If Not t.H Is Nothing Then
		'test =TH.Description
		rot = t.H.RotType
		tip = t.H.TipType
		
		If (rot = atFree) And (tip = atFree) Then
		    ' Drehachse frei + Kippachse frei
			If t.h.ToolPlaces.GetToolPlace_PlaceID(1).TipAngle=0 Then
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
' -- 
' -- 
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
'	If result="" Then
'		AddHint("MT_Get_MachPara_Add not found ID - " +ftos(search_id))
'	End If
	Set Addi=Nothing
End Function


Function MT_IS_ISG
Const id = 1000
Dim result As Boolean 
Dim rs As Variant 
	result=False
	If Not TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(id) Is Nothing Then
		rs = TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(id).Value 
		If Val(rs)=1 Then
			result=True
		End If
	End If
	MT_IS_ISG = result
	
	
End Function

Function MT_Get_Sic_Diff_Saw_Router(t As THopsBasicToolExt,TipAngle) As Double
' -- 
' --  MW 21.04.2009 14:50:43
' --
Dim ZSicSaw, ZSicRouter As Double
Dim l_ttyp As THopsToolType
Dim tmp_t As thopsbasictoolext


   	If MT_IS_MainAgg(t) Then
   		l_ttyp = t.t.Tool.ToolType
   	
		Set tmp_t.t = TDATA.GetTool_ID(t.T.ID)
   	
		Set tmp_t.t.Tool.ToolType=tSaw
		
		' MW 03.03.2010
		ZSicSaw = tmp_t.t.GetSecurityZ(TipAngle)
		'ZSicSaw = T.t.GetSecurityZ(TipAngle)
		'wcncCom("ZSic:als Saege"+FToS(ZSicSaw))
		
		Set tmp_t.t.Tool.ToolType=tCutter
		
		' MW 03.03.2010
		ZSicRouter = tmp_t.t.GetSecurityZ(TipAngle)
		'ZSicRouter = T.t.GetSecurityZ(TipAngle)
		'wcncCom("ZSic:als Fraeser"+FToS(ZSicRouter))

		If MT_Is_Vertical_StandardTool5Axis(t) Then
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
		
		' MW 03.03.2010 urspruenglichen Typ wieder setzen
   		t.t.Tool.ToolType = l_ttyp
		
	ElseIf MT_isDHSaw(t) Or MT_isPneumaticSaw(t) Then
		' -- 
 		' -- 1. Saege auf Bohrkopf oder Saege pneumatisch
		' --  
		MT_Get_Sic_Diff_Saw_Router = t.t.CollRadius
	ElseIf MT_isPneumaticSaw(t) Then
		' -- 
 		' -- 1. Saege pneumatisch
		' --  
		MT_Get_Sic_Diff_Saw_Router = t.t.CollRadius

	
	End If
	
End Function

' MW 04.01.2011
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

' Stempel/Halt mal kurz Vorrichtung 
Function MT_is_VBM_Stempel(ActT As THopsBasicToolExt)
Dim result As Boolean
Dim Spec_type As Integer 

	If Not TDATA.MachineData.MachineParameter.CreateNCDataAdditions.GetAddition_ID(-200003) Is Nothing Then
		Spec_type  = Val(TDATA.MachineData.MachineParameter.CreateNCDataAdditions.GetAddition_ID(-200003).Value)
	Else
		Spec_type  = 500  
	End If
	
	result = False
	If (MT_IsProcessHeadTool(ActT)) And equal(ActT.t.ToolType,Spec_type) Then
		result = True
	End If
	MT_is_VBM_Stempel = result
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
	
	
	If T.h.ToolPlaces.GetToolPlace_Index(0).PosDustExhaust= 1 Then
		' Im Bearbeitungskopf dynamisch also Werkzeug / Winkelgetriebe heranziehen
		If MT_IsGearBoxTool(T) Or  MT_IsGearBoxTool_Special(T) Or MT_IsGearBoxTool_TC_Access(T) Then
			' Winkelgetriebe oder aehnliches
			DustPos = Actt.GB.PosDustExhaust
		ElseIf MT_IsProcessHeadTool(T) Then
			DustPos = Actt.T_CEdge.PosDustExhaust
		Else
			DustPos = Actt.T_CEdge.PosDustExhaust
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


' Big Tool -> keine drehende Spindel waehrend dem Anfahren / schwenken
Function MT_NoTurningWithSpindelRot(T As THopsBasicToolExt) As Boolean
Dim erg As Boolean

	erg = False
	'  -> nur gueltig fuer 5-Achs - Werkzeuge
	If (MT_H_Is_5_Axis(T) And MT_Is_S_Tool(T)) Then
		If (T.t.Radius*2) >= T.PH_Add.MaxDiamM5Turn5Axis Then
			erg = True		
		End If
	End If
	MT_NoTurningWithSpindelRot = erg
End Function

' MW 06.03.2014 Big Tool -> Handling Spindel aus bzw. Drosselung
Function MT_NoTurningWithSpindelRot_OFF(T As THopsBasicToolExt)
Dim r_speed As Double   ' reduzierte Spindel Drehgeschwindigkeit

	r_speed = T.PH_Add.MaxDiamM5Turn5Axis_RedSpeed
	
	If MT_NoTurningWithSpindelRot(T) Then
		' MW 06.03.2014
		' Big Tool erst unmittelbar vor der Bearbeitung Spindel starten
		If r_speed = 0 Then
			wcnc("M5")  ' Spindle OFF
			WCNC_ISG_CHK_SPEED  ' MW 10.03.2014
		Else
			MT_Write_Speed(T,r_speed)
			WCNC_ISG_CHK_SPEEDINTOLERANCE ' AK 11.03.2014
		End If
		
		PPara.Speed = r_speed
	End If

End Function


' assymetrische Winkelgetriebe vertikal -> Olivenbohrer Roto
' oder Reihenbohrgetriebe mit Programmierung C-Achse
Function MT_IsGearBoxTool_Special_Vertical_sym_or_asym(T As THopsBasicToolExt)
Dim result As Boolean
Dim CountA ,i As Integer 
Dim offx,offy As Double 
	result = False
	If Not T.t_gb Is Nothing Then
		If T.gb.ToolPlaces.Count > 1 Then
		   If T.T_GB.GB_ToolPlace.TipAngle=0 Then
		   		' Werkzeug sitzt auf senkrechtem Ausgang
		   		CountA = T.gb.ToolPlaces.Count
		   		If CountA > 1 Then
		   			' mehr als 1 Ausgang
		   				
		   			For i = 0 To CountA -1
		   				If T.gb.ToolPlaces.GetToolPlace_Index(i).TipAngle=T.T_GB.GB_ToolPlace.TipAngle Then
		   					' auch senkrecht
		   					offx= T.gb.ToolPlaces.GetToolPlace_Index(i).OffsetX
		   					offy= T.gb.ToolPlaces.GetToolPlace_Index(i).OffsetY
		   					
		   					If (Dist2P(0,0,offx,offy)>5)  Then
		   						' Ausgangsdifferenz > 5mm
		   						result =True
		   						Exit For
		   					End If
		   				End If
		   			Next i
		   		End If
		   End If
		End If
	End If
	MT_IsGearBoxTool_Special_Vertical_sym_or_asym = result
End Function



' MW 26.10.2105
' Werkzeug ist eigentlich ein Aggregat oder Spaenleitblech
' Dadurch kommt die Ausgangsstellung beim C-Achsenfraesen nicht auf die Loesung +-180 neg. TIPA
Function MT_is_Tool_Agg (T As THopsBasicToolExt)
Dim resu As Boolean
 	resu = False
	If Not T.t Is Nothing Then
		If Not T.t.Tool.Additions.GetAddition_ID(10001) Is Nothing Then
			If T.t.Tool.Additions.GetAddition_ID(10001).Value="1" Then
				resu = True
			End If
		End If
	End If
	MT_is_Tool_Agg = resu	
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
  Set T.SetOf_DustPositions = Nothing       ' MW 24.02.2016
  Set T.SetOf_DustPositionsMFunc = Nothing  ' MW 24.02.2016

End Function


' *****************************************************************************************
' ** Ermittlung des bevorzugten Liftpos
' *****************************************************************************************
Function MT_GET_PREFLIFT As Double

	If Not ActT.h Is Nothing Then
		MT_GET_PREFLIFT = ActT.H.LiftOffsets.Preferred_LiftID
	Else	
		pp_err(0,"ActT.h Is Nothing")
		MT_GET_PREFLIFT=-1
	End If
	
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
		MT_GET_T_POSDUST = ActT.GB.PosDustExhaust
	ElseIf Not T.t_cedge Is Nothing Then
		MT_GET_T_POSDUST = T.T_CEdge.PosDustExhaust 
	End If
	
End Function



' *****************************************************************************************
' ** Function um die die gewuenschte Liftpos ueber den Cycle abzusetzen
' ** Markers
' ** LastLiftpos       => zuletzt gesetzte Position wenn < 0 dann war TC aktiv
' ** LiftPosStartup    => von Engine (oder DINISO-Process) gelieferte Liftposition der Liftstellung zum anfahren
' ** LiftPosProcessing => von Engine (oder DINISO-Process) gelieferte Liftposition der Liftstellung zum bearbeiten


' es wird davon ausgegangen, dass die 
' Pos = 1 immer die untere Stellung ist, 
' Pos = 2 immer die obere Stellung ist !

' *****************************************************************************************
Function MT_Set_LiftPos(Kind,PNo) As Boolean    ' Kind -1:Anfahren 0:Process 1:Abfahren
Dim lo 
Dim lox,loy,loz As Double 
Dim r_Lift As Integer
Dim p_Lift As Integer 
Dim actLift As Integer 
Dim result As Boolean 

'Dim Obj 
'Dim MMPs As NCMillingMPs
'Dim MP As NCMillingPoints
'Dim PNMPs As NCNCInfoProcessMPs

'Dim ax As Variant
'Dim ay As Variant
'Dim az As Variant

	If isDINISO_Process Then
		' MW 30.03.2016 - nicht bei DINISO_Process
		Exit Function
	End If

	actLift = Marker.LastLiftpos
	result = False

 	If Not ActT.h Is Nothing Then
		If ActT.h.UseLiftOffsets Then
		
			If Not JobPara.isg Then pp_err(1,"Lifting Siemens Controller ?")

			r_Lift = NCData.ProcessList.GetProcess_NCInfoIndex(PNo-1).RLiftOffsetInfos.ID
			p_Lift = NCData.ProcessList.GetProcess_NCInfoIndex(PNo-1).PLiftOffsetInfos.ID
			
			Select Case Kind
			Case -1   ' Anfahren


'	MP.NCMillingPoints.GetXYZ
'	MP.NCMillingHeadPoints.GetXYZ
'	
'	PNMPs.Para1x|y|z
'	PNMPs.HeadOffX|y|z

'				Set Obj = NCData.ProcessList.GetProcess_NCInfoIndex(PNo-1)
'				If Obj.ObjectTyp = otMillingMPs Then
'					Set MMPs = Obj
'					MMPs.MillingList.GetMillingElement_Index(0).GetAxAyAz(ax,ay,az)
'					ax = ax + MMPs.HeadOffX
'					ay = ay + MMPs.HeadOffY
'					az = az + MMPs.HeadOffZ
'				End If
'				Set Obj = Nothing
'					wcnccom("MMPS X:"+ftos(ax)+ " Y:"+ftos(ay) + " Z:"+ftos(az),True)
			
				Set lo = ActT.h.LiftOffsets.GetLiftOffset_Index(r_Lift-1)		
				wcnccom("Lift- Startup:"+inttos(r_Lift)+" - verrechnet von Engine: x:"+ftos(lo.OffsetX)+" y:"+ftos(lo.OffsetY)+" z:"+ftos(lo.OffsetZ),True)
				Set lo = ActT.h.LiftOffsets.GetLiftOffset_Index(p_Lift-1)		
				wcnccom("Lift- Processing:"+inttos(p_Lift)+" - verrechnet von Engine: x:"+ftos(lo.OffsetX)+" y:"+ftos(lo.OffsetY)+" z:"+ftos(lo.OffsetZ),True)
			
			
				' hier muss geprueft werden, ob der letzte Prozess mit der oberen Stellung beendet wurde,
				' dann muss erst die naechste Bearbeitungsposition angefahren werden (Z hoch im Prinzip) und dann kann auf die untere Stellung vorgelegt werden
				If (Marker.LastLiftpos = 2) And (r_Lift=1) Then
					' letzte Bearbeitung wurde mit der oberen Stellung beendet
					' jetzt folgt Anfahrt mit unterer Stellung - Z-Ausgleichsbewegung

					result = False   ' keine Liftpos aendern
				Else
					If Not equal(actLift,r_Lift) Then
						actLift = r_Lift
						result = True  ' dann wird Liftpos abgesetzt
					End If
				End If
			Case 0   ' Process
				If Not equal(actLift,p_Lift) Then
					actLift = p_Lift
					result = True  ' dann wird Liftpos abgesetzt
				End If
			Case 1   ' Abfahren
				If Not equal(actLift,r_Lift) Then
					actLift = r_Lift
					result = True  ' dann wird Liftpos abgesetzt
				Else
					result = False
				End If
			End Select
			
			If result = True Then 
				wcnccom("Lifting Spindle PLift:"+inttos(p_Lift)+" RLift:"+inttos(r_Lift),True)
				ISG_CC(SPF_TCLift,inttos(ActT.Hid),inttos(actLift))
			End If
			
'			If Not equal(r_Lift,p_Lift) And (Kind=0) Then
'				MsgBox("Lifting difference Process:"+inttos(pno))
'			End If

			Marker.LastLiftpos = actLift
		End If
	End If

	Set lo = Nothing	
	
	MT_Set_LiftPos = result
End Function

' *****************************************************************************************

'Declare Sub ProcessLaserFile Lib "c:\CAMPUS7\System\Posts\HH7\NCDataPPChanger.dll" (ByVal sInput As String, ByVal sOutput As String)
'
'Declare Function ScanNCData Lib "c:\CAMPUS7\System\Posts\HH7\NCDataPPChanger.dll" (ByVal ncd As Variant )

' *****************************************************************************************
Function MT___Set_HaubeObj_Tst(Kind,PNo) As Boolean    ' Kind -1:Anfahren 0:Process 1:Abfahren

Dim Obj 

'Dim ObjPL  ' As Variant ' Object    ' NCProcessList

Dim MMPs As NCMillingMPs
Dim MP As NCMillingPoints
'Dim PNMPs As NCNCInfoProcessMPs
Dim i As Long 
Dim x As Double 
Dim y As Double
Dim z As Double 

'Exit Function
	'ProcessLaserFile PostSettings.LaserFilename, ncpathGlobal + "NC_Laser.1st"

	'Set ObjPL = NCData.ProcessList
	
	'ScanNCData( NCData.ProcessList)    'NCData.ProcessList)  ' ??????????????????????
	'FScanNCData( ObjPL)    'NCData.ProcessList)  ' ??????????????????????
	
	
	Set Obj = NCData.ProcessList.GetProcess_NCInfoIndex(pno-1)
	If Obj.ObjectTyp = otMillingMPs Then
		Set MMPs = Obj
		For i = 0 To MMPs.MillingList.Count
			' alle durchgehen
			Debug.Print MMPs.MillingList.GetMillingElement_Index(0).XEnd & MMPs.MillingList.GetMillingElement_Index(0).YEnd
		Next i
		Set Obj = Nothing
'		wcnccom("MMPS X:"+ftos(ax)+ " Y:"+ftos(ay) + " Z:"+ftos(az),True)
	End If

	If Obj.ObjectTyp = otMillingPoints Then
		Set MP = Obj
		AddLog(inttos(MP.NCMillingHeadPoints.NCMillingPointsCount) )
		For i = 0 To MP.NCMillingHeadPoints.NCMillingPointsCount -1
			' alle durchgehen
			'MP.NCMillingHeadPoints.GetXYZ(i,x,y,z)
			'If i = 500 Then
				MP.NCMillingHeadPoints.SetXYZ(i,i,0,0)
			'End If
			
			
			'Debug.Print "X:"+ftos(x) & "Y:"+ftos(y) & "Z:"+ftos(z)
		Next i
		Set Obj = Nothing
'		wcnccom("MMPS X:"+ftos(ax)+ " Y:"+ftos(ay) + " Z:"+ftos(az),True)
	End If

End Function

' MW 09.02.2016 - Neue Logik Haube ueber Engine 
Function MT_Get_Suction (Kind,DP_NCIE,DP_MinT,DP_MaxT)

Dim CE_DustPos As Integer 
Dim DustPos As Integer 
Dim DustPos_PH As Integer 	
Dim DustPos_CE As Integer 	

	DustPos = 0 ' "-" Keine 
	
	DustPos_PH = MT_GET_HEAD_POSDUST(actt)   ' Dem Bearbeitungskopf/Processhead hinterlegte Haubenpos
	DustPos_CE = MT_GET_T_POSDUST(actt)      ' MT-Manager eingetragene Position im Winkelgetriebe oder der Werkzeug-Schneide

	If DustPos_PH = 0 Then    	 ' In der Spindel ist keine "-" hinterlegt
		' wenn auf ProcessHead keine Haube gewaehlt gibt es auch keine
		'MF = actt.SetOf_DustPositionsMFunc.GetString(0)
		' Haubenpos DEFAULT = OBEN
		DustPos = 0 ' "-" Keine 
	ElseIf DustPos_PH = 1 Then   ' dynamische Position
		' Pos aus der Schneide holen
		DustPos = DustPos_CE   ' MT-Manager eingetragene Position im Winkelgetriebe oder der Werkzeug-Schneide
		
		If PPara.NCiE.sh.Activ Then
			' Program. Haubenposition ueber NCIExt -100244 gefunden
			DustPos = PPara.NCiE.sh.Value1  ' Wert ist bereits plausibilisiert
		End If
		If (DustPos = 1) Then
			' Dyn. von Schneide oder programmiert
			If (equal(PPara.MinTipA,0) And equal(PPara.MaxTipA,0)) Then  ' And Not isgb(actt) Then
				' senkrechte Ausrichtung - auch bei Winkelgetriebe moeglich
				' dyn. Position ueber DLL fahren
			Else
				' undefiniert
				DustPos=0   ' keine
			End If
		End If
	Else                        
		' Dem PH wurde eine fixe Position hinterlegt 
		DustPos = DustPos_PH  
	End If
	MT_Get_Suction = DustPos
End Function

' *****************************************************************************************
' ** MW 10.02.2016 
' ** -> Plausibilierung des programmierten Wertes Haube, gesetzt werden dürfen nur die Werte, welche unter Eigenschaften MTManager definiert sind
' ** -> also auch nur die welche im Werkzeug - Schneide definiert werden koennen
' *****************************************************************************************
Function MT_CheckProgValue_Suction(Suction_Pos) As String
Dim i As Integer 
	If (Suction_Pos < 0) Or (Suction_Pos > TDATA.MachineData.MachineParameter.PosDustExhaustTypes.Count-1) Then
		pp_err(1589,Suction_Pos) 
	Else
		MT_CheckProgValue_Suction = TDATA.MachineData.MachineParameter.PosDustExhaustTypes.GetString_Index(Suction_Pos)	
	End If
End Function


' *****************************************************************************************
' ** Werkzeug - Funktion ermittelt anhand der Drehzahl, die Drehrichtung und gibt zudem das Uebersetzungsverhaeltnis zurueck
' *****************************************************************************************
' ** MW 30.05.2017
Function MT_Get_Speed_Data(T As THopsBasicToolExt,pspeed,dr,dz,gr,Optional Gear_Ratio) ' rueckgabe dr,dz,gr

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


    If IsMissing(Gear_Ratio) Then
    	' parameter nicht uebergeben
    	Gear_Ratio = 1
    End If
    
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
		dz = inttos(MT_Get_SpindleSpeed(ActT,pspeed))
		
		' --  uebersetzungsverhaeltnis DH
		Speed_trans_DH = Gear_Ratio
		
		Speed_Trans_complete = Speed_trans_DH
		
	ElseIf MT_isDHSaw(T) Then
		' Nutsaege auf Drilling Head
		If T.t_dhsaw.RotDirection = rdLeft Then
		   dr=3
		ElseIf T.t_dhsaw.RotDirection = rdRight Then
			dr=4
		ElseIf T.t_dhsaw.RotDirection = rdLeftRight Then
		
		End If
		dz = inttos(MT_Get_SpindleSpeed(ActT,pspeed))
		' --  uebersetzungsverhaeltnis DH
		If Not T.t_dhsaw Is Nothing Then
			Speed_trans_DH = T.t_dhsaw.DH_ToolPlace.GearRate
		End If
		Speed_Trans_complete = Speed_trans_DH
		
	ElseIf MT_isPneumaticSaw(T) Then
		' pneumatische Saege
		' wird immer erst im Viewchange aufgerufen - dadurch actv.rota moeglihc
		' MW 13.01.2015 CP wird jetzt uebergeben
		pp_err(0,"pneum.saw?")
'		If IsEmpty (CP) Or Not IsNumeric(CP) Then
'			pp_err(0,"pneum.saw?")
'		End If
		'MT_GetPneumaticSawAngle(T,ActV.RotA,Raster_Angle)
		'CP = Raster_Angle 
		' --  uebersetzungsverhaeltnis DH
		If Not T.t.PH_ToolPlace Is Nothing Then
			Speed_trans_PH = T.t.PH_ToolPlace.GearRate
		End If
		Speed_Trans_complete = Speed_trans_PH
		
		
	Else
		If MT_IsProcessHeadTool(T) Then
			' -- 
			' --  MW 27.11.2008 08:46:55
			' --
			' --  uebersetzungsverhaeltnis z.B. SchloKa
			If Not T.t.PH_ToolPlace Is Nothing Then
				Speed_trans_PH = T.t.PH_ToolPlace.GearRate
			End If
			Speed_Trans_complete = Speed_trans_PH

		End If
	
	End If
	
	gr = Speed_Trans_complete

	

End Function

Function MT_IsMEAS(T As THopsBasicToolExt)

	MT_IsMEAS = False
	
	If Not T.t Is Nothing Then
		If (MT_IsProcessHeadTool(T) Or MT_Is_TC_T(T)) And (T.T.ToolType=6000) Then
			' Werkzeug (Messwerkzeug) auf Processhead und Spezieller Typ = 6000
			MT_IsMEAS = True
		End If
	End If
End Function
