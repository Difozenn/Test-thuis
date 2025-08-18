' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \%postdir%\pp_clamps.bas
' -- 
' -----------------------------------------
'#uses "pp_global.bas"
'#uses "pp_math.bas"

Option Explicit

'***********************************************************************************
'*************************************  Types  *************************************
'***********************************************************************************

Type TClamps
	Name As String
	No As Long 
	DiffY As Double  ' Differenz Spannsituation in Y
End Type

Type TTrav 
	No As Long
	Clamps() As TClamps
End Type

Type TClampings
   Act_Situation As Long
End Type

Global Clamps As TClampings

Type TUmspannStep
	Trav As Integer
	Saug As Integer
	DiffY As Double
End Type

Type TUmspann
	UmSpannStep() As TUmspannStep
End Type

Global TLSPath As String
Global ScaleY As Double

Function TravInActiveField(trfldid, fldid) As Boolean
	If fldid = 1 Then
	  TravInActiveField = trfldid = 0
	ElseIf fldid = 2 Then
	  TravInActiveField = trfldid = 1
	Else
	  TravInActiveField = True
	End If 
End Function
' --
' -- Umspannen Szenenabhandlung
' -- 
' -- in diesem Modus werden die Spanner in der Abfolgen von Vorne nach Hinten 
' -- Reihenweise durchgegangen
' -- 
Function Handle_Clamp_Situation(situa1,situa2)

Dim CS_Old, CS_New As ClampSituation
Dim MCD_Old, MCD_NEW As IMachineComponentsData
Dim i As Integer
Dim j As Integer
Dim k As Integer
Dim TMC_Old,TMC_New As IMachineComponent
Dim CCMC_OLD,CCMC_NEW As IMachineComponent
Dim NCP As NCPart


Dim t As IMachineComponent
Dim Start As Integer
Dim Ende As Integer

Dim SArrayNewYSauger(3) As Double   ' 4 Sauger 0-3 
Dim SPosChanged As Boolean   ' Merker ob sich eine Saugerposition auf der Traverse geändert hat
Dim TravChanged As Boolean   ' Travpos geändert

Dim	RowChange(4) As Boolean 
Dim	ClampChange(20,4) As Boolean


	 
	Set CS_Old = NCData.NCClampSituations.ClampSituations.GetItem_Index(situa1)
	Set CS_New = NCData.NCClampSituations.ClampSituations.GetItem_Index(situa2)
	
	Set MCD_Old = CS_Old.MachineComponentsData
	Set MCD_NEW = CS_New.MachineComponentsData
	
	' Daten aufbereiten wegen fixer Traversen
	' MCD_Old
	For i = (MCD_Old.MachineComponents.ComponentList.Count-1) To 0 Step -1
		Set t = MCD_Old.MachineComponents.ComponentList.GetItem_Index(i)
		If (t.MCList.ClampCarrierCount=0) Then

			MCD_Old.MachineComponents.ComponentList.Delete_Index(i)
		End If
	Next i
	' Daten aufbereiten wegen fixer Traversen
	' MCD_NEW
	For i = (MCD_NEW.MachineComponents.ComponentList.Count-1) To 0 Step -1
		Set t = MCD_NEW.MachineComponents.ComponentList.GetItem_Index(i)
		If (t.MCList.ClampCarrierCount=0) Then

			MCD_NEW.MachineComponents.ComponentList.Delete_Index(i)
		End If
	Next i
	
	GetTraversen_Bereich(MCD_NEW,Start,Ende)
	
	
	
	'Ermitteln ob Klemmen oder Öffnen beim umsetzen der Sauger
	Dim ClampMode As String		'0=Öffnen/lösen beim Verfahren   1=Geschlossen Verfahren
	
	If JobPara.activ_fields = 1 Then
		ClampMode = CS_New.AdditionalInfo.GetAddition_ID(3).Value    'ForLeft
    
    ElseIf JobPara.activ_fields = 2 Then
		ClampMode = CS_New.AdditionalInfo.GetAddition_ID(4).Value    'ForRight
    
    ElseIf JobPara.activ_fields = 3 Then
		'gekoppelt
		If CS_New.AdditionalInfo.GetAddition_ID(1).Value = "1" Then
			'NP auf Feld Links
			ClampMode = CS_New.AdditionalInfo.GetAddition_ID(3).Value    'ForLeft
		Else
			'NP auf Feld Rechts
			ClampMode = CS_New.AdditionalInfo.GetAddition_ID(4).Value    'ForRight
		End If
    End If
    
	
	'For j = 0 To MCD_Old.MachineComponents.ComponentList.TraverseCount-1 Step 1
	' -- 
	wcnccom("")
	wcnccom("")
	wcnccom("")
	If ClampMode = "1" Then
		wcnccom("|||||||||||| CLAMP CHANGE CLOSED ||||||||||||||||")
	Else
		wcnccom("|||||||||||| CLAMP CHANGE OPENED ||||||||||||||||")
	End If
	wcnccom("")
	wcnccom("--> SZENE:"+inttos(situa2+1))
	
	Get_Sauger_ReihenChanged(ClampChange,RowChange,situa1,situa2)   ' RowChange Array of Boolean 0..3
	
	'Sich bewegende Spanner lösen
	If ClampMode = "0" Then

		M_Loesen(ClampChange,RowChange)  
	End If


	For j = Start To Ende Step 1
		' alle beteiligten Traversen für die Ausgangssituation (bisherige Spannsituation) durchgehen
		SPosChanged=False   ' geänderte Y- Position gefunden
		TravChanged=False
		
		Set TMC_Old = MCD_Old.MachineComponents.ComponentList.GetTraverse_Index(j)
		TMC_Old.MCList.SortPosY
		Set TMC_New = MCD_NEW.MachineComponents.ComponentList.GetTraverse_Index(j)
		TMC_New.MCList.SortPosY
		
		If TMC_Old.PosX<>TMC_New.PosX Then
			' Traversen dürfen sich nicht bewegen, - wenn gewollt über NCINFO freischalten
			'AddMistake("unterschiedliche Traversenposition beim Umspannen nicht erlaubt")
			
			' MW 31.03.2010 - logisch dürfen sie
			TravChanged=True
		End If
		
		If (TMC_Old.MCList.ClampCarrierCount>0) And (TMC_New.MCList.ClampCarrierCount>0) And _
			(TMC_Old.MCList.ClampCarrierCount=TMC_New.MCList.ClampCarrierCount) Then
				' es handelt sich um eine Traverse mit Saugern drauf
			
				For k= 0 To TMC_Old.MCList.ClampCarrierCount-1  
					Set CCMC_OLD = TMC_Old.MCList.GetClampCarrier_Index(k)
					Set CCMC_NEW = TMC_New.MCList.GetClampCarrier_Index(k)
					
					SArrayNewYSauger(k) = (CCMC_NEW.PosY + TDATA.MachineData.OffsetY + TMC_New.NCOffsetY)
					
					If Not equal(CCMC_OLD.PosY,CCMC_NEW.PosY) Then
						' es hat sich ein Saugerpos geändert
						'wcnccom("Trav:"+inttos(j+1)+"  /  S:"+inttos(k+1)+" "+Int(CCMC_OLD.PosY)+" --> "+Int(CCMC_NEW.PosY))
						'Gleitkomma !   MM 20.01.09
						wcnccom("Trav:"+inttos(j+1)+"  /  S:"+inttos(k+1)+" "+ftos(CCMC_OLD.PosY)+" --> "+ftos(CCMC_NEW.PosY))
						SPosChanged=True   ' geänderte Y- Position gefunden
						
						'AddHint("Sauger alt:"+FtoS(CCMC_OLD.PosX)+"  "+FToS(CCMC_OLD.PosY))
						'AddHint("Sauger neu:"+FtoS(CCMC_NEW.PosX)+"  "+FToS(CCMC_NEW.PosY))
					End If
				Next   'k
				If SPosChanged Or TravChanged Then
					' jetzt neue Saugerpositionen absetzen TRAEGERPOS setzen
					'wcncNewPadPositions(situa2,j+1,TMC_Old.PosX+TDATA.MachineData.OffsetX + TMC_Old.NCOffsetX,SArrayNewYSauger)
					wcncNewPadPositions(situa2,j+1,TMC_New.PosX+TDATA.MachineData.OffsetX + TMC_Old.NCOffsetX,SArrayNewYSauger)
				End If
		End If
	Next j

	If situa2=1 Then
		' -- Werkzeugwechsel während Spannerpositionierung
		' Nur bei 1. Szenenwechsel möglicher Werkzeugwechsel
		
		wcnccom("Werkzeugwechsel während Umspannvorgang ? ")
		TC_SPez
	End If

	wcnc("STOPRE")
	wcnc("C_TRAEGERPOS_START")
	wcnccom("")
	wcnccom("|||||||||||||||| CLAMP CHANGE END ||||||||||||||||||")
	wcnccom("")
	wcnccom("")
	wcnccom("")

	
	wcnc("STOPRE")
	
	

	
	If ClampMode = "0" Then
		M_Spannen(ClampChange,RowChange)  ' Sich bewegende Spanner wieder spannen




	End If
	
	'Hochfahren...
	'Reset_All_Axis
	'Marker.M_Reset=True
	
	'wcnc("Z=PRK TP0")
	
	'Marker.NCSTOP_Active = True
	'Marker.ActHead=inttos(ActT.AggNo)
	' sonst wird beim erzwungenen toolchange über viewchange falsches aggregat aufgerufen
	
	If ClampMode = "1" Then
		'Nur anhalten bei Saugen...
		'M_Spannen(ClampChange,RowChange)
		'wcnc("M00")
		WCNC("M51")
		'wcncaddcom("C_HOLE_ACHSEN","Stop bis Spanner positioniert")
		'wcncaddcom("H102","Stop bis Spanner positioniert")
		wcnc("STOPRE")
	End If
	
End Function


' --
' -- Ermittlung welche Saugerreihen sich zur vorherigen Szene geändert haben
' -- 
' -- 
Function Get_Sauger_ReihenChanged(ClampChange,RowChange,situa1,situa2)   ' RowChange Array of Boolean 0..3

Dim CS_Old, CS_New As ClampSituation
Dim MCD_Old, MCD_NEW As IMachineComponentsData
Dim i As Integer
Dim j As Integer
Dim k As Integer
Dim TMC_Old,TMC_New As IMachineComponent
Dim CCMC_OLD,CCMC_NEW As IMachineComponent
Dim NCP As NCPart

Dim t As IMachineComponent
Dim Start As Integer
Dim Ende As Integer
	
	RowChange(0)=False
	RowChange(1)=False
	RowChange(2)=False
	RowChange(3)=False
	
	 
	Set CS_Old = NCData.NCClampSituations.ClampSituations.GetItem_Index(situa1)
	Set CS_New = NCData.NCClampSituations.ClampSituations.GetItem_Index(situa2)
	
	Set MCD_Old = CS_Old.MachineComponentsData
	Set MCD_NEW = CS_New.MachineComponentsData
	
	' Daten aufbereiten wegen fixer Traversen
	' MCD_Old
	For i = (MCD_Old.MachineComponents.ComponentList.Count-1) To 0 Step -1
		Set t = MCD_Old.MachineComponents.ComponentList.GetItem_Index(i)
		If (t.MCList.ClampCarrierCount=0) Then

			MCD_Old.MachineComponents.ComponentList.Delete_Index(i)
		End If
	Next i
	' Daten aufbereiten wegen fixer Traversen
	' MCD_NEW
	For i = (MCD_NEW.MachineComponents.ComponentList.Count-1) To 0 Step -1
		Set t = MCD_NEW.MachineComponents.ComponentList.GetItem_Index(i)
		If (t.MCList.ClampCarrierCount=0) Then
			MCD_NEW.MachineComponents.ComponentList.Delete_Index(i)
		End If
	Next i
	
	GetTraversen_Bereich(MCD_NEW,Start,Ende)
	
	For j = Start To Ende Step 1
		' alle beteiligten Traversen für die Ausgangssituation (bisherige Spannsituation) durchgehen
		
		Set TMC_Old = MCD_Old.MachineComponents.ComponentList.GetTraverse_Index(j)
		TMC_Old.MCList.SortPosY

		Set TMC_New = MCD_NEW.MachineComponents.ComponentList.GetTraverse_Index(j)
		TMC_New.MCList.SortPosY
		
		If (TMC_Old.MCList.ClampCarrierCount>0) And (TMC_New.MCList.ClampCarrierCount>0) And _
			(TMC_Old.MCList.ClampCarrierCount=TMC_New.MCList.ClampCarrierCount) Then
				' es handelt sich um eine Traverse mit Saugern drauf
			
				For k= 0 To TMC_Old.MCList.ClampCarrierCount-1  
					Set CCMC_OLD = TMC_Old.MCList.GetClampCarrier_Index(k)
					Set CCMC_NEW = TMC_New.MCList.GetClampCarrier_Index(k)
					
					ClampChange(j,k)=False
					If Not equal(CCMC_OLD.PosY,CCMC_NEW.PosY) Then
						' es hat sich ein Saugerpos geändert
						ClampChange(j,k)=True
						RowChange(k)=True					
					End If
				Next   'k
		End If
	Next j
	
End Function




' liefert alle Traversen inkl. Sauger/Spannmittel des Werkstückes zurück
Function Get_WP_Clamps(WorkPiece As Variant) As TTrav()

Dim i As Integer
Dim NCP As NCPart

Dim info_str As Variant
Dim token,token2 As String
Dim aTrav() As TTrav
'Dim aSAUG() As TClamps
Dim TravNo, SaugNo As Integer 
Dim Akt_Trav As Long 

	ReDim aTrav(0)
	'ReDim aSAUG(0)
 	Set NCP = NCData.NCParts.GetNCPart_Index(WorkPiece-1)
 	
 	If NCP Is Nothing Then
 		Exit Function
 	End If
 	
	info_str = NCP.ClampInfo
	
	For i = 1 To ParamCount(info_str)
		' holen von Traversen + Saugerinfo
		token = Param(i,info_str)
		' Token2=Traverse		
		TravNo = Val(Param2x(1,token))
		SaugNo = Val(Param2x(2,token))
		Akt_Trav = TravDa(aTrav,TravNo)
		If Akt_Trav<0 Then
			'If UBound(aTrav)<TravNo Then
		    ReDim Preserve aTrav(UBound(aTrav)+1) 
		    Akt_Trav = UBound(aTrav)
		    ReDim aTrav(Akt_Trav).Clamps(0)
		End If
		' jetzt Traversen - Nummer auf TraversenArray schreiben
		aTrav(Akt_Trav).No=TravNo
		
		ReDim Preserve aTrav(Akt_Trav).Clamps(UBound(aTrav(Akt_Trav).Clamps)+1) 
		
		' jetzt Sauger - Nummer auf SaugerArray der Traverse schreiben
		aTrav(Akt_Trav).Clamps(UBound(aTrav(Akt_Trav).Clamps)).No=SaugNo
		
	Next i
	Get_WP_Clamps=aTrav
	
End Function


' liefert den Spanntype von WORKPIECE zurück
Function Get_WP_ClampType(WorkPiece As Variant) As Long

Dim NCP As NCPart

	Set NCP = NCData.NCParts.GetNCPart_Index(WorkPiece-1)
	If Not NCP Is Nothing Then
		Get_WP_ClampType = NCP.ClampType
	Else
		Get_WP_ClampType = -1
	End If

End Function


' liefert den Spanntype von WORKPIECE zurück
Function Get_WP_Origin(WorkPiece As Variant) As Integer

Dim NCP As NCPart

	Set NCP = NCData.NCParts.GetNCPart_Index(WorkPiece-1)
	If Not NCP Is Nothing Then
		Get_WP_Origin = NCP.ZP
	End If
	
End Function


Function TravDa(Trav, TravNo  ) As Long 
Dim i As Long
Dim result As Long 
 	result = -1
	For i = 1 To UBound(Trav) 
		If Trav(i).No=TravNo Then
			result=i
		End If
	Next i
	TravDa = result
End Function


Function Write_CustomSEZ

Dim akt_wp As Integer 
Dim i,j,k As Integer 

Dim origin,frontstops,sidestops As Integer
Dim Akt_Trav,akt_saug As Integer 


If NCData.NCParts.Count=0 Then
	Exit Function
End If

	For i = 1 To UBound(WPI) 
		' Group = i
		If i=1 Then
			wcnccom("")
			wcnccom("Traverse " + IntTos(i))
		End If
		
		akt_wp = i    ' 1. Werkstück Ubound(0) gibt es nicht
		
		'If WPI(akt_wp).ClampType=0 Then
			' Uniclamp
		'	origin = WPI(akt_wp).Origin
		'	Select Case origin
		'	Case 1,5
		'		sidestops=1
		'	Case 2,6
		'		sidestops=2
		'	Case 3,7
		'		sidestops=3
		'	Case 4,8
		'		sidestops=4
		'	End Select
		'	sidestops=0
		'	frontstops=0
			'origin=24		'Dieser Anschlag hat nur Seitenanschläge !
		'Else
			' Sauger
		'	origin = WPI(akt_wp).Origin
		'	Select Case origin
		'	Case 1,5
		'		sidestops=1
		'	Case 2,6
		'		sidestops=2
		'	Case 3,7
		'		sidestops=3
		'	Case 4,8
		'		sidestops=4
		'	End Select
			
		'	frontstops=0
		'	sidestops=0
		'End If
		
		
		'wcncWON("GROUP="+inttos(akt_wp))
		'wcncWON("ORIGIN="+inttos(origin))
		
		'If frontstops>0 Then
		'	wcncWON("FRONTSTOPS="+inttos(frontstops)) 'Y-Anschlgreihe von hinten beginnend
		'End If
		'If sidestops>0 Then
	'		wcncWON("SIDESTOPS="+inttos(sidestops))	'X-Anschlgreihe von hinten beginnend
		'End If
		
		
		For j = 1 To UBound(WPI(akt_wp).Trav)
		'For j = 1 To UBound(WPI(1).Trav)
			Akt_Trav= WPI(akt_wp).Trav(j).No
			'wcnc(R_Parameter+inttos(i)+"1="+Ftos(WPI(akt_wp).Trav(j)))		'Traverse-Nr. von links
			
			For k = 1 To UBound( WPI(akt_wp).Trav(j).Clamps) 
				akt_saug= WPI(akt_wp).Trav(j).Clamps(k).No
				wcncWO("CARRIAGE="+inttos(akt_saug+1))	'Sauger-Nr. von hinten beginnend
			Next k
		Next j
		
		If i=UBound(WPI) Then
			wcncWO("")
			wcncWO("TRAEGERPOSSTART")
			wcncWO("")
		End If

	Next i

End Function
	


Function test(situa1,situa2)

 Dim CS As ClampSituation
 Dim MCD As IMachineComponentsData
 Dim i As Integer
 Dim j As Integer
 Dim k As Integer
 Dim TMC As IMachineComponent
 Dim CCMC As IMachineComponent
 Dim NCP As NCPart
	
	' Plausibel - Situationen da ?
 	
	For i = situa1 To NCData.NCClampSituations.ClampSituations.Count-1 Step 1
		Set CS = NCData.NCClampSituations.ClampSituations.GetItem_Index(i)
		Set MCD = CS.MachineComponentsData
		'MCD.Save("","c:\",IntToS(i)+".dat")
		For j = 0 To MCD.MachineComponents.ComponentList.TraverseCount-1 Step 1
			Set TMC = MCD.MachineComponents.ComponentList.GetTraverse_Index(j)
			'MsgBox("Trav:"+IntToS(TMC.ID))
			For k = 0 To TMC.MCList.ClampCarrierCount-1 Step 1
				Set CCMC = TMC.MCList.GetClampCarrier_Index(k)
				'MsgBox("Sauger:"+FtoS(CCMC.PosX)+"  "+FToS(CCMC.PosY))
			Next k
		Next j
	Next i
 
	Set NCP = NCData.NCParts.GetNCPart_Index(0)
' NCP.ClampInfo
' NCP.ZP

	Clamps.Act_Situation = Clamps.Act_Situation + 1
	
End Function

Function wcncUmSpannStep_Open(UmSpannStep)
Dim i As Integer
Dim t,s As Integer
Dim d As Double

Dim Stri As String

Const B = "PUNC("

	If UBound(UmSpannStep) > 0 Then
		wcnccom("")
		wcnccom("OPEN clamps...")
		wcnc("L=GWTINIT")
		stri = ""
		For i=1 To UBound(UmSpannStep)
			t=UmSpannStep(i).Trav
			s=UmSpannStep(i).Saug
			d=UmSpannStep(i).DiffY
			stri=stri+B+inttos(t)+","+inttos(s)+")=0 "
		Next i
		wcnc(stri)
		wcnc("L=GWTEXE")
	End If

End Function

Function wcncUmSpannStep_Move(UmSpannStep)
Dim i As Integer
Dim t,s As Integer
Dim d As Double

Dim Stri As String

Const B = "PCR("

	If UBound(UmSpannStep) > 0 Then
		wcnccom("")
		wcnccom("MOVE clamps...")
		wcnc("L=GWTINIT")
		stri = ""
		For i=1 To UBound(UmSpannStep)
			t=UmSpannStep(i).Trav
			s=UmSpannStep(i).Saug
			d=UmSpannStep(i).DiffY
			stri=stri+B+inttos(t)+","+inttos(s)+")="+ftos(d)+" "
		Next i
		wcnc(stri)
		wcnc("L=GWTEXE PINC=1")
	End If

End Function

Function wcncUmSpannStep_Close(UmSpannStep)
Dim i As Integer
Dim t,s As Integer
Dim d As Double

Dim stri As String

Const B = "PUNC("

	If UBound(UmSpannStep) > 0 Then
		wcnccom("")
		wcnccom("CLOSE clamps...")
		wcnc("L=GWTINIT")
		stri = ""
		For i=1 To UBound(UmSpannStep)
			t=UmSpannStep(i).Trav
			s=UmSpannStep(i).Saug
			d=UmSpannStep(i).DiffY
			stri=stri+B+inttos(t)+","+inttos(s)+")=1 "
		Next i
		wcnc(stri)
		wcnc("L=GWTEXE")
	End If

End Function

'****************************************************************************************************
'*******************************************Spannerdaten ausgeben************************************
'****************************************************************************************************
'****************************************************************************************************
'****************************************************************************************************

Function wcncMachineComponentData(Situ)
Dim MCD As IMachineComponentsData									'Falls NCInfo 85 nicht verwendet wurde
	'If (NCData.NCClampSituations.ClampSituations.Count>0) And Not (NCI_Marker.NCINFO_Zero_GLOBAL_SET) Then
	' Neu MW 29.03.2007
	If (NCData.NCClampSituations.ClampSituations.Count>0) And _
	        ((PostSettings.PPStarterType=ppstWorkcenter) Or _
	         (PostSettings.PPStarterType=ppstAnoptiMT)) Then

		Set MCD = NCData.NCClampSituations.ClampSituations.GetItem_Index(Situ).MachineComponentsData.Clone
	    Dim CNISLNR As Long
	    GetTLSPath(MCD)
	    ScaleY = 1
	    If MCD.MirrorY Then
	    	ScaleY = -1
	    End If 
	    CNISLNR=StringListCreate
		'ComponentDataInNC(MCD,NCData.NCClampSituations.ClampSituations.GetItem_Index(Situ).MachineComponentsData.ActiveFields,CNISLNR)
		
		' --  MW 07.11.2007 12:43:57
		
		ComponentDataInNC(MCD,MCDATA.ActiveFields,CNISLNR)
		
		WcncStringList(CNISLNR)
	    'StringListSaveToFile(CNISLNR,"c:\text.dat")
	    StringListDestroy(CNISLNR)
	Else
    	wcncWO("END TABLECONFIG")
    	wcncWO("")
	End If 
End Function

Function GetElementAnzahl(CL As IMachineComponentList)
Dim i As Integer
Dim j As Integer

Dim MCT As IMachineComponent
Dim MCS As IMachineComponent

	GetElementAnzahl = 0
	For i = 0 To CL.TraverseCount-1 Step 1
		Set MCT = CL.GetTraverse_Index(i)
		GetElementAnzahl = GetElementAnzahl+1
		GetElementAnzahl = GetElementAnzahl+MCT.MCList.ClampCarrierCount
		GetElementAnzahl = GetElementAnzahl+MCT.MCList.StopCount 
		For j = 0 To MCT.MCList.ClampCarrierCount-1 Step 1
			Set MCS = MCT.MCList.GetClampCarrier_Index(j)
			GetElementAnzahl = GetElementAnzahl+MCS.MCList.ClampingCount
		Next j
	Next i
End Function

Function GetRigamX(Additions)
Dim Add As IAdditionExt
	Set Add = Additions.GetAddition_ID(0)
	If Add Is Nothing Then
		GetRigamX = "0"
	Else
		GetRigamX = Add.Value
	End If
End Function

Function GetRigamY(Additions)
Dim Add As IAdditionExt
	Set Add = Additions.GetAddition_ID(1)
	If Add Is Nothing Then
		GetRigamY = "0"
	Else
		GetRigamY = Add.Value
	End If
End Function

Function IntToSHex(Value)
  IntToSHex=IntToS(Value)
  If Value>=10 Then
    Select Case Value
    Case 10
      IntToSHex="a"
    Case 11
      IntToSHex="b"
    Case 12
      IntToSHex="c"
    Case 13
      IntToSHex="d"
    Case 14
      IntToSHex="e"
    Case 15
      IntToSHex="f"
    Case Else
      IntToSHex="0"
    End Select
  End If
End Function

Function GetComponentDataMoveStr(Movex,Movey,Movew,Crossable,Overlapable)
Dim Sx As String
Dim Sy As String
Dim Movexy As Integer
	Movexy=0
	If Movex Then
	  Movexy=Movexy+1
	End If
	If Movey Then
	  Movexy=Movexy+2
	End If
	Sx=IntToSHex(Movexy)
	
	Movexy=0
	If Movew Then
	  Movexy=Movexy+1
	End If
	If Crossable Then
	  Movexy=Movexy+8
	End If
	If Overlapable Then
	  Movexy=Movexy+4
	End If
	Sy=IntToSHex(Movexy)
	GetComponentDataMoveStr=Sy+Sx	
End Function

Sub ComponentDataStandardInCNIFormat(NR,CategoriaA,IdObjAtt,IdAssoc)
  StringListAdd(NR,"Angolo=0.000")
  StringListAdd(NR,"CategoriaA="+IntToS(CategoriaA))
  StringListAdd(NR,"IdObjAtt="+IdObjAtt)
  StringListAdd(NR,"IdAssoc="+IdAssoc)
  StringListAdd(NR,"StepAng=15.000")
End Sub

Function ComponentDataInNC(MCD As IMachineComponentsData,ActField,NR)
  StringListAdd(NR,"")
  StringListAdd(NR,"; ******* TABLECONFIG *******")
  StringListAdd(NR,"")
'  StringListAdd(NR,"CountObjects="+IntToS(1+GetElementAnzahl(MCD.MachineComponents.ComponentList)))
'  StringListAdd(NR,"RigamX="+FToS(GetRigamX(MCD.Additions)))
'  StringListAdd(NR,"RigamY="+FToS(GetRigamY(MCD.Additions)))
'  StringListAdd(NR,"")
	'ComponentDataMachineInCNIFormat(MCD,NR)
  ComponentDataTableInCNIFormat(MCD,ActField,NR)
  'ComponentDataPadInCNIFormat(MCD,NR)
  'ComponentDataStopInCNIFormat(MCD,NR)
  'ComponentDataRotPadInCNIFormat(MCD,NR)
  StringListAdd(NR,"; ***** END TABLECONFIG *****")
'  StringListAdd(NR,"%")
End Function

Function ComponentDataMachineInCNIFormat(MCD As IMachineComponentsData,NR)
  If MCD.MachineComponents.Reserved1="" Then
  	StringListAdd(NR,"PosX="+FToS(0))
  Else
  	StringListAdd(NR,"PosX="+MCD.MachineComponents.Reserved1)
  End If 
  If MCD.MachineComponents.Reserved2="" Then
  	StringListAdd(NR,"PosY="+FToS(0))
  Else
  	StringListAdd(NR,"PosY="+MCD.MachineComponents.Reserved2)
  End If 
  'StringListAdd(NR,"DxfName="+GetComponentDXFName(mckMachine,MCD.MachineComponents.MachineDXF))
  'Call ComponentDataStandardInCNIFormat(NR,0,"1","0")
  StringListAdd(NR,"")
End Function

Function ComponentDataTableInCNIFormat(MCD As IMachineComponentsData,ActField,NR)
Dim i As Long
Dim Index100 As Long
Dim Index10 As Long
Dim Index1 As Long
Dim Trav_Zeile,Trav_ZeileBefore As String

Dim T As IMachineComponent
Dim Start As Integer
Dim Ende As Integer
Dim gefunden, L_Done, R_Done As Boolean
Dim ADMax, AdMin As Double 


	If Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(900021)) Is Nothing Then 
		AdMin=CDbl(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(900021).Value)
	Else
		AddMistake("MachinParameter Missing ID: "+CStr(900021))
	End If
	
	If Not(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(900022)) Is Nothing Then 
		AdMax=CDbl(TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(900022).Value)
	Else
		AddMistake("MachinParameter Missing ID: "+CStr(900022))
	End If
'ADMax=
'AdMin=

	Index100=800
	Index10=10
	Index1=1

	'Ori alles
	'For I = 0 To (MCD.MachineComponents.ComponentList.TraverseCount-1) Step 1
	
	'MsgBox (Inttos(MCD.MachineComponents.ComponentList.TraverseCount) )
		
	'For I = (MCD.MachineComponents.ComponentList.TraverseCount-1) To 0 Step -1
	For i = (MCD.MachineComponents.ComponentList.Count-1) To 0 Step -1
	 	'
		' Alle Komponenten durchgehen, da über Traversenindex die Komponenten nicht gelöscht werden können
		'
		'Set t = MCD.MachineComponents.ComponentList.GetTraverse_Index(I)
		Set T = MCD.MachineComponents.ComponentList.GetItem_Index(i)

		If (T.MoveX=False And T.Kind=mckTraverse) Then
			' Alle Traversen welche nicht verschiebbar sind raus!
			MCD.MachineComponents.ComponentList.Delete_Index(i)
		End If
	
	Next i

	'MsgBox (Inttos(MCD.MachineComponents.ComponentList.TraverseCount) )
'NCData.NCClampSituations.ClampSituations.GetItem_Index(Situ).MachineComponentsData.ActiveFields

	GetTraversen_Bereich(MCD,Start,Ende)
	
	If is_WorkC_OptionBit(EinTransportPos,JobPara.WorkC_OptionBit) Then
		If JobPara.activ_fields=3 Then
			If is_WorkC_OptionBit(SuppsUpAtStart,JobPara.WorkC_OptionBit)Then
				StringListAdd(NR,"M50")
				StringListAdd(NR,"G90 D0 G153 G0 Z=MAXZ")
				StringListAdd(NR,"C_TRANSPORT")
				StringListAdd(NR,"M0")
			Else
				AddMistake("Unterstuetzer Hoch!")
			End If
		Else
			AddMistake("Eintransport nur mit FeldKopplung erlaubt!")
		End If
	End If
	StringListAdd(NR,"M50")
	

	'StringListAdd(NR,"REFPOS")
	'StringListAdd(NR,"T_AUSWAHL(" +Inttos(Ende-Start+1) +")")

	If GTabletype=1 Then
		For i = Start To Ende Step 1

			Set T = MCD.MachineComponents.ComponentList.GetTraverse_Index(i)
		
			T.MCList.SortPosY


			If T.Field=1 Then
				Index100=900
				Index10=10
			End If
		
			Index1=1

			Trav_Zeile=""
		
			'StringListAdd(NR,"; TRAVERSE " + Inttos(I+1))
			'StringListAdd(NR,"R"+IntToS(Index100+Index10+Index1)+"="+FToS(T.PosX))
			If JobPara.activ_fields=1 Or JobPara.activ_fields=3 Then
				Trav_Zeile="C_TRAEGERPOS(" + Inttos(i+1)+","+FToS(Round(TDATA.MachineData.OffsetX + T.NCOffsetX + T.PosX))
			Else

				Trav_Zeile="C_TRAEGERPOS(" + Inttos(i+1)+","+FToS(Round(TDATA.MachineData.OffsetX + T.NCOffsetX + T.PosX))		
			End If
			
			ComponentDataPadInCNIFormat(T,NR,Index100+Index10+Index1,Trav_Zeile)
		
			StringListAdd(NR,Trav_Zeile+")")
			Index10=Index10+10
		Next i
	ElseIf GTableType=2 Then
		'PROC C_TRAEGERPOS(Int _ERSTERTRAEGER, REAL GRENZWERT_UNTEN, REAL GRENZWERT_OBEN, REAL POSWERT1, REAL POSWERT2, REAL POSWERT3, REAL POSWERT4, REAL POSWERT5, REAL POSWERT6, REAL POSWERT7, REAL POSWERT8) 
		For i = Start To Ende Step 1

			Set T = MCD.MachineComponents.ComponentList.GetTraverse_Index(i)
		
			T.MCList.SortPosY


			If T.Field=1 Then
				Index100=900
				Index10=10
			End If
		
			Index1=1
			If i=Start Then
				If JobPara.activ_fields=1 Then
					Trav_ZeileBefore="C_TRAEGERPOS("+Inttos(Start+1)+","+FToS(Round(TDATA.MachineData.OffsetX + T.NCOffsetX + T.PosX))+","
				ElseIf JobPara.activ_fields=2 Then
					If JobPara.NPX>(TDATA.MachineData.OffsetX + T.NCOffsetX + T.PosX) Then
						Trav_ZeileBefore="C_TRAEGERPOS("+Inttos(Start+1)+","+FToS(Round(JobPara.NPX - AdMin))+","	
					Else
						Trav_ZeileBefore="C_TRAEGERPOS("+Inttos(Start+1)+","+FToS(Round(TDATA.MachineData.OffsetX + T.NCOffsetX + T.PosX - AdMin))+","	
					End If
				ElseIf JobPara.activ_fields=3 Then
					Trav_ZeileBefore="C_TRAEGERPOS("+Inttos(Start+1)+","+FToS(Round(TDATA.MachineData.OffsetX + T.NCOffsetX + T.PosX))+","					
				End If
			End If
			
		
			'StringListAdd(NR,"; TRAVERSE " + Inttos(I+1))
			'StringListAdd(NR,"R"+IntToS(Index100+Index10+Index1)+"="+FToS(T.PosX))
			If JobPara.activ_fields=1 Or JobPara.activ_fields=3 Then
				Trav_Zeile=Trav_Zeile+","+FToS(Round(TDATA.MachineData.OffsetX + T.NCOffsetX + T.PosX))
			Else

				Trav_Zeile=Trav_Zeile+","+FToS(Round(TDATA.MachineData.OffsetX + T.NCOffsetX + T.PosX))		
			End If
			
			'ComponentDataPadInCNIFormat(t,NR,Index100+Index10+Index1,Trav_Zeile)
		
			'StringListAdd(NR,Trav_Zeile+")")
			'Index10=Index10+10
			If i=Ende Then
				If JobPara.activ_fields=1 Then 
					Trav_Zeile=Trav_Zeile+",,,,"
					If (JobPara.NPX+FinishedPart.X)>(TDATA.MachineData.OffsetX + T.NCOffsetX + T.PosX) Then
						Trav_ZeileBefore=Trav_ZeileBefore+FToS(Round(JobPara.NPX+FinishedPart.X + ADMax))
					Else
						Trav_ZeileBefore=Trav_ZeileBefore+FToS(Round(TDATA.MachineData.OffsetX + T.NCOffsetX + T.PosX + ADMax))
					End If
				ElseIf JobPara.activ_fields=2 Then 
					Trav_Zeile=",,,,"+Trav_Zeile
					Trav_ZeileBefore=Trav_ZeileBefore+FToS(Round(TDATA.MachineData.OffsetX + T.NCOffsetX + T.PosX))
				ElseIf JobPara.activ_fields=3 Then 
					Trav_ZeileBefore=Trav_ZeileBefore+FToS(Round(TDATA.MachineData.OffsetX + T.NCOffsetX + T.PosX))
				End If
				
			End If
		Next i
		Trav_Zeile=Trav_ZeileBefore+Trav_Zeile+")"
		StringListAdd(NR,Trav_Zeile)
	End If
	

	StringListAdd(NR,"")
	StringListAdd(NR,"STOPRE")
	'StringListAdd(NR,"C_TRAEGERPOS_START")
	StringListAdd(NR,"MSG("+""""+" Traverses in Position ! " + """"+")")
	If is_WorkC_OptionBit(SuppsUpAtStart,JobPara.WorkC_OptionBit) Then
		Unterstuetzer_hoch(NR)
		StringListAdd(NR,"MSG("+""""+" Unterstützer Hoch ! " + """"+")")
	End If
	'StringListAdd(NR,"M00")
	StringListAdd(NR,"MSG("+""""+ """"+")")
	If is_WorkC_OptionBit(PinsUpAtStart,JobPara.WorkC_OptionBit) Then
		Anschlaege_hoch(NR)
		StringListAdd(NR,"MSG("+""""+" PinsUP ! " + """"+")")
	End If
	StringListAdd(NR,"M00")
	StringListAdd(NR,"MSG("+""""+ """"+")")
'	StringListAdd(NR,"ANFANG")
	'Call WKS_SPANNEN

	StringListAdd(NR,"C_HOLE_ACHSEN")
'	StringListAdd(NR,"H102")
	StringListAdd(NR,"")


End Function

Function ComponentDataPadInCNIFormat(T As IMachineComponent,NR,Index,Trav_Zeile)
Dim i,j As Long
Dim P As IMachineComponent
Dim R_Parameter As String
	
		For j = 0 To T.MCList.ClampCarrierCount-1 Step 1
			Set P = T.MCList.GetClampCarrier_Index(j)
			
			'MM 22.01.09  ab jetzt Sauger in Y nicht mehr runden, da mit Klemmspanner
			'Trav_Zeile=Trav_Zeile+","+FToS(Round(TDATA.MachineData.OffsetY + t.NCOffsetY + P.PosY))
			Trav_Zeile=Trav_Zeile+","+FToS(TDATA.MachineData.OffsetY + T.NCOffsetY + P.PosY)
			'Index=Index+1
			'StringListAdd(NR,"R"+IntToS(Index)+"="+FToS(P.PosY))
			
			'StringListAdd(NR,"; SAUGERPOS in Y auf Traverse " + inttos(I+1))
		Next j

End Function

Function ComponentDataRotPadInCNIFormat(MCD As IMachineComponentsData,NR)
Dim i,j,AktIndex As Long
Dim CC As IMachineComponent
Dim P As IMachineComponent
Dim Index As Integer
Dim t As IMachineComponent
	AktIndex = 0
	For i = 0 To (MCD.MachineComponents.ComponentList.TraverseCount-1) Step 1
		Set t = MCD.MachineComponents.ComponentList.GetTraverse_Index(i)
		For j = 0 To t.MCList.ClampCarrierCount-1 Step 1
			Set CC = t.MCList.GetClampCarrier_Index(j)
			If CC.MCList.Count>0 Then
				Set P = CC.MCList.GetClamping_Index(0)
				
				'StringListAdd(NR,"Categoria=5")
				'StringListAdd(NR,"Ordine="+IntToS(P.Reserved1))
				 
				StringListAdd(NR,"PosX="+FToS(P.PosX))
				StringListAdd(NR,"PosY="+FToS(ScaleY*P.PosY))
				'StringListAdd(NR,"Associato="+IntToS(P.Reserved2))
				'StringListAdd(NR,"DxfName="+GetComponentDXFName(P.Kind,P.DXF))
				'StringListAdd(NR,"Side="+P.Side)
				'StringListAdd(NR,"Movimento="+GetComponentDataMoveStr(P.MoveX,P.MoveY,P.MoveAngle,P.Transitable,P.Overlayable))
				'StringListAdd(NR,"DxfAuxR=")
				'StringListAdd(NR,"DxfAuxL=")
				
				'StringListAdd(NR,"OrigAss="+P.Reserved0)
				
				'StringListAdd(NR,"Angolo="+FToS(P.Angle))
				'StringListAdd(NR,"CategoriaA=3")
				'StringListAdd(NR,"IdObjAtt="+P.Reserved3)
				'StringListAdd(NR,"IdAssoc="+P.Reserved3)
				'StringListAdd(NR,"StepAng="+FToS(P.DAngle))
				StringListAdd(NR,"")
				AktIndex = AktIndex+1
			End If
		Next j
	Next i
End Function

Function ComponentDataStopInCNIFormat(MCD As IMachineComponentsData,NR)
Dim i,j,AktIndex As Long
Dim S As IMachineComponent
Dim t As IMachineComponent
	AktIndex = 0
	For i = 0 To (MCD.MachineComponents.ComponentList.TraverseCount-1) Step 1
		Set t = MCD.MachineComponents.ComponentList.GetTraverse_Index(i)
		For j = 0 To t.MCList.StopCount-1 Step 1
			Set S = t.MCList.GetStop_Index(j)
			StringListAdd(NR,"Categoria=4")
			'StringListAdd(NR,"Ordine="+IntToS(S.Reserved1))
			StringListAdd(NR,"PosX="+FToS(S.PosX))
			StringListAdd(NR,"PosY="+FToS(ScaleY*S.PosY))
			'StringListAdd(NR,"Associato="+IntToS(S.Reserved2))
			'StringListAdd(NR,"DxfName="+GetComponentDXFName(S.Kind,S.DXF))
			'StringListAdd(NR,"Side="+S.Side)
			'StringListAdd(NR,"Movimento="+GetComponentDataMoveStr(S.MoveX,S.MoveY,False,S.Transitable,S.Overlayable))
			'StringListAdd(NR,"DxfAuxR=")
			'StringListAdd(NR,"DxfAuxL=")
			'StringListAdd(NR,"OrigAss="+S.Reserved0)
			'Call ComponentDataStandardInCNIFormat(NR,2,S.Reserved4,S.Reserved3)
			StringListAdd(NR,"")
		Next j
  Next i
End Function

Function WcncStringList(NR)
        Dim strolevariant As Variant
Dim i As Integer
	For i = 0 To StringListCount(NR)
    	strolevariant = StringListStrings(NR, i)
		wcncWO (strolevariant)
	Next i
End Function


Function GetTLSPath(MCD As IMachineComponentsData)
	If MCD.MachineComponents.Reserved0="" Then
		TLSPath = "C:\HOME\D_XNC\tls\"
	Else
		TLSPath = MCD.MachineComponents.Reserved0
	End If 
End Function

'****************************************************************************************************
'****************************************************************************************************
'****************************************************************************************************

Function GetTraversen_Bereich(MCD_NEW,Start,Ende)
	
Dim i As Integer

	Start = -1
	Ende = 0




	For i=0 To MCD_NEW.MachineComponents.ComponentList.TraverseCount-1 
		If TravInActiveField(MCD_NEW.MachineComponents.ComponentList.GetTraverse_Index(i).Field, MCDATA.ActiveFields) Then
			If Start = -1 Then






				Start = i
			End If
			Ende = i
		End If
	Next i
	
End Function


'****************************************************************************************************
'****************************************************************************************************
'****************************************************************************************************

Function wcncNewPadPositions(scene,Traeger,TravPos,Saugers)
Dim i As Integer 
Dim Stri As String
	
	'Gleitkomma !   MM 20.01.09
	
	'Stri="TRAEGERPOS("+inttos(Traeger)+","+ftos(Round(TravPos))
' MW - Blödsinn - Gleitkomma - Startsituation gibt auch kein Gleitkomma aus - Was soll das ?
	Stri="C_TRAEGERPOS("+inttos(Traeger)+","+ftos(TravPos)
	
	For i = 0 To UBound(Saugers)
		'Stri=Stri+ ","+ftos(Round(Saugers(i)))
		Stri=Stri+ ","+ftos(Saugers(i))
	Next i
	Stri=Stri+")"
	wcncaddcom(Stri,"UMSPANNEN TRAEGER:"+inttos(Traeger))
End Function

Function M_Loesen(ClampChange,RowChange)  ' Sich bewegende Spanner lösen
Dim i,k As Integer
Dim Pad_No As Integer


If JobPara.activ_fields=1 Then
	Pad_No=0

	For i=0 To 9 Step 1
		For k=0 To 2 Step 1
			Pad_No=Pad_No+1
			If ClampChange(i,k) Then
				Pad_No=210+i*10+k+1
				WCNC("M"+FtoS(Pad_No))	
					

			End If
		Next k
	
	Next i









ElseIf JobPara.activ_fields=2 Then

	Pad_No=0

	For i=0 To 9 Step 1
		For k=0 To 2 Step 1
			Pad_No=Pad_No+1
			If ClampChange(i,k) Then
				Pad_No=250+i*10+k+1
				WCNC("M"+FtoS(Pad_No-40))	
					







			End If
		Next k
	
	Next i









ElseIf JobPara.activ_fields=3 Then
	'AddMistake("Clampchange on 2 desks in Hops not avaliable!")
	
	Pad_No=0

	For i=0 To 9 Step 1
		For k=0 To 2 Step 1
			Pad_No=Pad_No+1
			If ClampChange(i,k) Then
				Pad_No=210+i*10+k+1
				WCNC("M"+FtoS(Pad_No))	


			End If
		Next k
	
	Next i

End If

End Function

Function M_Spannen(ClampChange,RowChange)  ' Sich bewegte Spanner wieder spannen
Dim i,k As Integer
Dim Pad_No As Integer


If JobPara.activ_fields=1 Then

	'wcnc("H102")
	Pad_No=0

	For i=0 To 9 Step 1
		For k=0 To 2 Step 1
			Pad_No=Pad_No+1
			If ClampChange(i,k) Then
				Pad_No=110+i*10+k+1
				WCNC("M"+FtoS(Pad_No))	
					
			End If
		Next k
	
	Next i



ElseIf JobPara.activ_fields=2 Then
	'wcnc("H102")
	Pad_No=0

	For i=0 To 9 Step 1
		For k=0 To 2 Step 1
			Pad_No=Pad_No+1
			If ClampChange(i,k) Then
				Pad_No=110+i*10+k+1
				WCNC("M"+FtoS(Pad_No))	


					

			End If
		Next k
	
	Next i

ElseIf JobPara.activ_fields=3 Then
	'AddMistake("Clampchange on 2 desks in Hops not avaliable!")
	'wcnc("H102")
	Pad_No=0


	For i=0 To 9 Step 1
		For k=0 To 2 Step 1
			Pad_No=Pad_No+1
			If ClampChange(i,k) Then
				Pad_No=110+i*10+k+1
				WCNC("M"+FtoS(Pad_No))	

					










			End If
		Next k








	
	Next i





















End If
















End Function

Function ClampChangeParkXY
Dim xstr,ystr As String
	xstr=""
	ystr=""
	'Get_ParkStrXY(11,xstr,ystr)
	Get_ParkStrXY(xstr,ystr)
	
	If Len(xstr)>0 Then
		wcnc(PARKXVAR+"="+xstr)
	End If
	If Len(ystr)>0 Then
		wcnc(PARKYVAR+"="+ystr)
	End If
	If (Len(xstr)>0) And (Len(ystr)>0) Then
		wcnc("G53 "+ G0 + " X="+FToS(PARKXVAR)+" Y="+ FToS(PARKYVAR) )
	ElseIf Len(xstr)>0 Then
		' nur x
		wcnc("G53 "+ G0 + " X="+FToS(PARKXVAR) )
	ElseIf Len(ystr)>0 Then
		' nur Y
		wcnc("G53 "+ G0 + " Y="+ FToS(PARKYVAR) )
 	End If
End Function
Function Anschlaege_hoch_Anf


End Function
