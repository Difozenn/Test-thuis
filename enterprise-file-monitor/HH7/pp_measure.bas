' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \hh7\pp_measure.bas
' -- 
' -----------------------------------------
'#uses "pp_math.bas"
'#uses "pp_7.bas"
'#uses "pp_global.bas"
'#uses "pp_mt.bas"
'#uses "pp_isg.bas"

Option Explicit

Enum TMeasureError
	meOK
	meNoProceccNCInfo
	meWrongProcessNo
	meDHProcess
	meNoDHProcess
	meWrongDHSNo
End Enum

Enum TMeasureDirection
	mdXP
	mdXM
	mdYP
	mdYM
	mdZP
	mdZM
	mdNotDef
End Enum

Global Type TUseMeasurePointInfo
	IsActiv As Boolean
	MpNoX As Integer
	MpNoY As Integer
	MpNoZ As Integer
	FactorX As Double
	FactorY As Double
	FactorZ As Double
End Type

Global Type TMeasurePointInfo
	PNCI As NCNCInfoProcess
	Direction As TMeasureDirection
	MPNo As Long
	Tolerance As Double
	Kind As Integer
	SVX As Double
	SVY As Double
	SVZ As Double
	SAX As Variant 
	SAY As Variant 
	SAZ As Variant 
	EVX As Double
	EVY As Double
	EVZ As Double
	EAX As Variant 
	EAY As Variant 
	EAZ As Variant 
End Type

Global Type TMeasurePointsInfos
	MeasureList() As TMeasurePointInfo
	Count As Long
	XMeasurePointExists As Boolean
	YMeasurePointExists As Boolean
	ZMeasurePointExists As Boolean
End Type

Global MeasurePointsInfos As TMeasurePointsInfos 
Global UseMeasurePointInfo As TUseMeasurePointInfo

' Rueckgabe der Messpunktnummer - WKS spezifisch
Function Measure_Get_MPNo(MPNo) As Integer

'	Measure_Get_MPNo = ((MPNo\1000)*100)+(MPNo Mod 1000)
'	Measure_Get_MPNo = MPNo   '(MPNo Mod 1000)

	Measure_Get_MPNo = (MPNo Mod 1000)
	
'	Measure_Get_MPNo = Measure_Get_MPNo - 1  ' MW 18.06.2019 Array beginnt bei 0
End Function


' Rueckgabe der Messpunktnummer - (Array) Maschinen seitig
Function Measure_Get_StrArr_MPNo(MPNo) As String
Dim resu As String
Dim tmp_MPNo 
	resu = ""
	tmp_MPNo = Measure_Get_MPNo(MPNo)
	
	resu = ISG_MEAS_ARR+"_"+inttos(Marker.wp_actindex)+"["+ inttoS(tmp_MPNo) +"]"
	
	Measure_Get_StrArr_MPNo = resu
End Function


Function SetUseMeasurePointInfo(UseMeasurePointInfo As TUseMeasurePointInfo,ByVal MeasuringReference As NCNCInfo)
Dim Value As Double
	
	UseMeasurePointInfo.MpNoX=0
	UseMeasurePointInfo.MpNoY=0
	UseMeasurePointInfo.MpNoZ=0

	UseMeasurePointInfo.IsActiv=(Not MeasuringReference Is Nothing)
	If UseMeasurePointInfo.IsActiv Then
		UseMeasurePointInfo.IsActiv=UseMeasurePointInfo.IsActiv And (Not MeasuringReference.NCIExt Is Nothing)
		If UseMeasurePointInfo.IsActiv Then
			MeasuringReference.NCIExt.GetFloat(1,Value)
			UseMeasurePointInfo.MpNoX=Fix(Value)
			MeasuringReference.NCIExt.GetFloat(2,Value)
			UseMeasurePointInfo.MpNoY=Fix(Value)
			MeasuringReference.NCIExt.GetFloat(3,Value)
			UseMeasurePointInfo.MpNoZ=Fix(Value)
			MeasuringReference.NCIExt.GetFloat(4,Value)
			UseMeasurePointInfo.FactorX=Value
			MeasuringReference.NCIExt.GetFloat(5,Value)
			UseMeasurePointInfo.FactorY=Value
			MeasuringReference.NCIExt.GetFloat(6,Value)
			UseMeasurePointInfo.FactorZ=Value
			UseMeasurePointInfo.IsActiv=(UseMeasurePointInfo.MpNoX>0) Or (UseMeasurePointInfo.MpNoY>0) Or (UseMeasurePointInfo.MpNoZ>0)
		End If
	End If
End Function

Function GetProcessUseMeasurePointInfo(UseMeasurePointInfo As TUseMeasurePointInfo,ByVal PNo As Long) As TMeasureError
Dim P As NCProcess
Dim dummy As Object

	If (PNo>=1) And (PNo<=NCData.ProcessList.Count) Then
		Set dummy = NCData.ProcessList.GetProcess_NCInfoIndex(PNo-1)
		Set P = dummy
		
		If P.ObjectTyp<>otDHProcess Then

			GetProcessUseMeasurePointInfo=meOK
			
			SetUseMeasurePointInfo(UseMeasurePointInfo,NCData.GetExtInfo(ekMeasuringReference,P))
		Else
			GetProcessUseMeasurePointInfo=meDHProcess
		End If
	
	Else
		GetProcessUseMeasurePointInfo=meWrongProcessNo
	End If
End Function

Function GetDHStrokeUseMeasurePointInfo(UseMeasurePointInfo As TUseMeasurePointInfo,ByVal PNo As Long,ByVal DHSNo As Long) As TMeasureError
Dim P As NCProcessExt
Dim dummy As Object
Dim Value As Double
Dim DHP As NCDHProcess
Dim MeasuringReference As NCNCInfo

	If (PNo>=1) And (PNo<=NCData.ProcessList.Count) Then
		Set dummy = NCData.ProcessList.GetProcess_NCInfoIndex(PNo-1)
		Set P = dummy
		
		If P.ObjectTyp=otDHProcess Then
			Set DHP = dummy
			
			If (DHSNo>=1) And (DHSNo<=DHP.DHStrokeList.Count) Then
			
				GetDHStrokeUseMeasurePointInfo=meOK
				
				SetUseMeasurePointInfo(UseMeasurePointInfo,DHP.DHStrokeList.GetDHStroke(DHSNo-1).MeasuringReference)
				
			End If
		Else
			GetDHStrokeUseMeasurePointInfo=meDHProcess
		End If
	
	Else
		GetDHStrokeUseMeasurePointInfo=meWrongProcessNo
	End If
End Function

'Methoden für TMeasurePointsInfos
Function MeasureInfos_Init()
	MeasurePointsInfos.Count=0	
	ReDim MeasurePointsInfos.MeasureList(MeasurePointsInfos.Count)
	MeasurePointsInfos.XMeasurePointExists=False
	MeasurePointsInfos.YMeasurePointExists=False
	MeasurePointsInfos.ZMeasurePointExists=False
End Function

Function MeasureInfos_Final()
Dim i As Long

	For i = 1 To MeasurePointsInfos.Count Step 1
		Set MeasurePointsInfos.MeasureList(i).PNCI=Nothing
	Next i
	MeasurePointsInfos.Count=0	
	ReDim MeasurePointsInfos.MeasureList(MeasurePointsInfos.Count)
End Function

Function MeasurePointsInfos_GetMeasurePointInfo_MpNo(MPNo As Integer,MeasurePointInfo As TMeasurePointInfo) As Boolean
Dim i As Long

	MeasurePointsInfos_GetMeasurePointInfo_MpNo=False
	
	For i = 1 To MeasurePointsInfos.Count Step 1
		If MeasurePointsInfos.MeasureList(i).MpNo=MPNo Then
		
			MeasurePointInfo=MeasurePointsInfos.MeasureList(i)
			
			MeasurePointsInfos_GetMeasurePointInfo_MpNo=True
			Exit For 
			
		End If
	Next i
End Function

Function MeasurePointsInfos_GetMeasurePointInfo_Active() As TMeasurePointInfo

	MeasurePointsInfos_GetMeasurePointInfo_Active=MeasurePointsInfos.MeasureList(MeasurePointsInfos.Count)
End Function

Function MeasurePointsInfos_AddPoint() As TMeasureError
Dim MeasurePointInfo As TMeasurePointInfo
Dim P As NCProcess
Dim dummy As Object
Dim dx As Double
Dim dy As Double
Dim dz As Double
Dim PNo As Long

	PNo=ppara.PLNo  ' ActProcess
	
	If (PNo>=1) And (PNo<=NCData.ProcessList.Count) Then
		Set dummy = NCData.ProcessList.GetProcess_NCInfoIndex(PNo-1)
		Set P = dummy
		
		' 
		If (P.ObjectTyp=otNCInfoProcess) Or (P.ObjectTyp=otNCInfoProcessMPs) Then

			MeasurePointsInfos_AddPoint=meOK

			MeasurePointsInfos.Count=MeasurePointsInfos.Count+1
			ReDim Preserve MeasurePointsInfos.MeasureList(MeasurePointsInfos.Count)
	   		Set MeasurePointInfo.PNCI = dummy
	   		MeasurePointInfo.SVX=MeasurePointInfo.PNCI.Para1x
	   		MeasurePointInfo.SVY=MeasurePointInfo.PNCI.Para1y
	   		MeasurePointInfo.SVZ=MeasurePointInfo.PNCI.Para1z
			P.View.GetAxAyAz(MeasurePointInfo.SVX,MeasurePointInfo.SVY,MeasurePointInfo.SVZ,MeasurePointInfo.SAX,MeasurePointInfo.SAY,MeasurePointInfo.SAZ)
	   		MeasurePointInfo.EVX=MeasurePointInfo.PNCI.Para2x
	   		MeasurePointInfo.EVY=MeasurePointInfo.PNCI.Para2y
	   		MeasurePointInfo.EVZ=MeasurePointInfo.PNCI.Para2z
			P.View.GetAxAyAz(MeasurePointInfo.EVX,MeasurePointInfo.EVY,MeasurePointInfo.EVZ,MeasurePointInfo.EAX,MeasurePointInfo.EAY,MeasurePointInfo.EAZ)
			MeasurePointInfo.MpNo=Fix(MeasurePointInfo.PNCI.Para7)
			MeasurePointInfo.Tolerance=MeasurePointInfo.PNCI.Para8
			MeasurePointInfo.Kind=Fix(MeasurePointInfo.PNCI.Para9)
			dx=MeasurePointInfo.EAX-MeasurePointInfo.SAX 
			dy=MeasurePointInfo.EAY-MeasurePointInfo.SAY 
			dz=MeasurePointInfo.EAZ-MeasurePointInfo.SAZ
			If equal(dx,0) And equal(dy,0) And Not equal(dz,0) Then
				If dz>0 Then
					MeasurePointInfo.Direction=mdZP
				Else
					MeasurePointInfo.Direction=mdZM
				End If
				MeasurePointsInfos.ZMeasurePointExists=True
			ElseIf equal(dx,0) And Not equal(dy,0) And equal(dz,0) Then
				If dy>0 Then
					MeasurePointInfo.Direction=mdYP
				Else
					MeasurePointInfo.Direction=mdYM
				End If
				MeasurePointsInfos.YMeasurePointExists=True
			ElseIf Not equal(dx,0) And equal(dy,0) And equal(dz,0) Then
				If dx>0 Then
					MeasurePointInfo.Direction=mdXP
				Else
					MeasurePointInfo.Direction=mdXM
				End If
				MeasurePointsInfos.XMeasurePointExists=True
			Else
				MeasurePointInfo.Direction=mdNotDef
			End If
			MeasurePointsInfos.MeasureList(MeasurePointsInfos.Count)=MeasurePointInfo
		Else
			MeasurePointsInfos_AddPoint=meNoProceccNCInfo
		End If
	
	Else
		MeasurePointsInfos_AddPoint=meWrongProcessNo
	End If

End Function


Function wcnc_measuring(MeasurePointInfo As TMeasurePointInfo,T As THopsBasicToolExt)  ' 
Dim kind As Integer 
Dim sx,sy,sz As Double 
Dim ex,ey,ez As Double 
Dim Direction As Integer ' wie Ebene (1=Y+) (2=X+) (3=Y-) (4=X-)
Dim Dist As Double 
Dim VT As Double 
Dim VET As Double 
Dim mess_i As String
Dim RefVal As Double 
Dim mResVar As String  ' ID #6001 
Dim BaseParams As String 
Dim Tol,MaxTol As Double 
Dim ArrName As String
Dim Sic_Z As Double  ' MW 09.05.2019 Werkzeug SIC + zusaetzliche Ueberfahrhoehe
Dim Head_X As Double
Dim Head_Y As Double
Dim Head_Z As Double

	
	
'	realMPNo = Measure_GetRealMPNo(MeasurePointInfo.MpNo)   ' (MeasurePointInfo.MpNo Mod 1000)

'MeasurePointsInfos.MeasureList(MeasurePointsInfos.Count).svx -> -200#
'MeasurePointsInfos.MeasureList(MeasurePointsInfos.Count).svy -> 22.5#
'MeasurePointsInfos.MeasureList(MeasurePointsInfos.Count).svz -> 20#
'MeasurePointsInfos.MeasureList(MeasurePointsInfos.Count).eax -> 15.5#
'MeasurePointsInfos.MeasureList(MeasurePointsInfos.Count).eay -> 200#
'MeasurePointsInfos.MeasureList(MeasurePointsInfos.Count).eaz -> 22.5#
'MeasurePointsInfos.MeasureList(MeasurePointsInfos.Count).mpno -> 1001&
'MeasurePointsInfos.MeasureList(MeasurePointsInfos.Count).Tolerance -> 5#

	Tol = MeasurePointInfo.Tolerance
	Head_X = ActT.h.CenterX
	Head_Y = ActT.h.CenterY
	Head_Z = ActT.h.CenterZ

	sx = MeasurePointInfo.Sax + Head_X  ' MeasurePointInfo.Svx
	sy = MeasurePointInfo.Say + Head_Y  ' MeasurePointInfo.Svy 
	sz = MeasurePointInfo.Saz + Head_Z  ' MeasurePointInfo.Svz
	ex = MeasurePointInfo.eax + Head_X  ' MeasurePointInfo.evx
	ey = MeasurePointInfo.eay + Head_Y  ' MeasurePointInfo.EvY
	ez = MeasurePointInfo.eaz + Head_Z  ' MeasurePointInfo.evz
	
'	VT = ActT.T_CEdge.Feedrate      ' Vorschub aus der Schneide 
'	VET = ActT.T_CEdge.MoveInFeedrate      ' EintauchVorschub aus der Schneide 
	
	' Pruefung auf Maximale Toleranz
	If Not ActT.t.Tool.Additions.GetAddition_ID(6002) Is Nothing Then	
		MaxTol = StrToFloat(ActT.t.Tool.Additions.GetAddition_ID(6002).Value)
	Else
		MaxTol = 15
	End If

	If Tol > MaxTol Then
		pp_err(129,Tol,MaxTol)
	End If
	
	kind = MeasurePointInfo.Kind
	
	Sic_Z = actt.t.GetSecurityZ(0)
	Sic_Z = Sic_Z + NCData.ProgInfo.SupplementZOffset 

    Select Case MeasurePointInfo.direction
    	Case mdXP
    		' Messen in X+ Richtung
    		mess_i = "X+"
    		Direction = 2  ' Ebene 2
    		Dist = Abs(MeasurePointInfo.eax-MeasurePointInfo.sax)
    		RefVal = MeasurePointInfo.eax
    	Case mdXM
    		' Messen in X- Richtung
    		mess_i = "X-"
    		Direction = 4  ' Ebene 4
    		Dist = Abs(MeasurePointInfo.eax-MeasurePointInfo.sax)
    		RefVal = MeasurePointInfo.eax
    	Case mdYP	
    		' Messen in Y+ Richtung
    		mess_i = "Y+"
    		Direction = 1  ' Ebene 1
    		Dist = Abs(MeasurePointInfo.eay-MeasurePointInfo.say)
    		RefVal = MeasurePointInfo.eaY
    	Case mdYM
    		' Messen in Y- Richtung
    		mess_i = "Y-"
    		Direction = 3  ' Ebene 3
    		Dist = Abs(MeasurePointInfo.eay-MeasurePointInfo.say)
    		RefVal = MeasurePointInfo.eax
    	Case mdZM
    		' Dicke tasten Messen in z- Richtung 
    		mess_i = "Z"
    		Direction = 0  ' Ebene 0
    		Dist = Abs(MeasurePointInfo.eaz-MeasurePointInfo.saz)
    		RefVal = MeasurePointInfo.eaZ
    	Case Else
    		pp_err(0,"wrong measure direction")
	End Select 
	
	wcnccom("; Measure START -------------------------------------------------------------")
	
	' Offset Spindel Laser
	'nc_offx = MeasGetLOffX(True)
	'nc_offy = MeasGetLOffY(True)
	
'	wcnc("G1" + XEqualToS(svx)+nc_offx + YEqualToS(svy) + nc_offy + ZEqualToS(actt.t.Length)+GetFeedrateStr(VT)) 
'	wcnc("G1" + XEqualToS(evx)+nc_offx + YEqualToS(evy) + nc_offy + ZEqualToS(evz+actt.t.Length+0.1)+GetFeedrateStr(VET)) 
	
	
	wcnccom(" measuring #"+inttos(MeasurePointInfo.MpNo)+" - Direction ["+inttos(Direction)+"] ["+mess_i+"]",True)
	'Stri = mCycleName+"(" +inttoS(Direction) +","+ftos(tol) + ")"
	' MESS(MP[1])  
	'Stri = mCycleName+"(" +mArrayName+"["+ inttoS(realMPNo) +"],"+ftos(tol) + ")"
	
	ArrName = Measure_Get_StrArr_MPNo(MeasurePointInfo.MpNo)
	
	'Stri = mCycleName + "(" 
	'Stri = Stri + inttos(kind)
	'Stri = Stri + "," + inttos(Direction)
	'Stri = Stri + "," + ftos(ex)
	'Stri = Stri + "," + ftos(ey)
	'Stri = Stri + "," + ftos(ez)
	'Stri = Stri + "," + inttos(Dist)
	'Stri = Stri + "," + ArrName
	'Stri = Stri + ")"
	
	'wcnccom(Stri,True)   ' hier Zyklus - Aufruf

	If ((ActT.T.ToolNo>0) And (ActT.T.CorrNo>0)) Then
		wcnc("T"+IntToS(ActT.T.ToolNo)+" D"+IntToS(ActT.T.CorrNo))
	End If

	WCNC_IDD("CP_MEAS",kind,Direction,ex,ey,ez,Dist,Tol,ArrName,Sic_Z,Head_X,Head_Y,Head_Z-Actt.H.RotPointOffZ)
	
	
	wcnccom("; Measure END -------------------------------------------------------------")
	

End Function

Function Get_Comment_Measure(MeasurePointInfo As TMeasurePointInfo) As String
Dim Stri_D As String 
Dim WPName As String 
Dim ZPName As String 
Dim resu As String 
	resu = ""
	Select Case MeasurePointInfo.direction
		Case mdXP
			Stri_D = " [X+] "
		Case mdXM
			Stri_D = " [X-] "
		Case mdYP
			Stri_D = " [Y+] "
		Case mdYM
			Stri_D = " [Y-] "
		Case mdZM
			Stri_D = " [Z-] "
	End Select 
	
	
	WPName = ExtractFileName(ppara.part.MainHopName)
	
	ZPName = ppara.part.StopName

	resu = "MEAS OFFSET #"+inttos(MeasurePointInfo.MpNo)+Stri_D 

	If (PPara.ObjectTyp = otDHProcess) Then
		' Werkstueck - Bezug unter Umstaenden nicht gegeben, da Bohrkopfbohrungen Werkstueckuebergreifend optimiert
		resu = resu +" DRILLINGHEAD "
		If (NCData.NCParts.Count=1)  Then
			resu = resu +" WP["+inttos(Marker.wp_actindex)+"/"+inttos(Measure_Get_MPNo(MeasurePointInfo.MpNo))+"] WP:" + WPName + "   ZP:" + ZPName
		End If
	Else
		resu = resu + " " + actt.t.Description+ " "
		resu = resu +" WP["+inttos(Marker.wp_actindex)+"/"+inttos(Measure_Get_MPNo(MeasurePointInfo.MpNo))+"] WP:" + WPName + "   ZP:" + ZPName
	End If
	Get_Comment_Measure = resu
End Function
			


Function Get_Measure_Offset_Vars(Optional SNo = 0)   ' StriOffX,StriOffY,StriOffZ) 
Dim MeasureError As TMeasureError
Dim MeasurePointInfo As TMeasurePointInfo
Dim realMPNo As Integer  
Dim StriOffX As String
Dim StriOffY As String
Dim StriOffZ As String
	StriOffX = "0"
	StriOffY = "0"
	StriOffZ = "0"

	If PPara.ObjectTyp = otDHProcess Then
		' Bohrkopfbearbeitung
		MeasureError=GetDHStrokeUseMeasurePointInfo(UseMeasurePointInfo,PPara.PLNo,SNo)
	Else	
		MeasureError=GetProcessUseMeasurePointInfo(UseMeasurePointInfo,PPara.PLNo)
	End If
	If Not MeasureError Then
		If (MeasurePointsInfos.Count > 0) Then ' And (UseMeasurePointInfo.isactiv) Then
			If MeasurePointsInfos_GetMeasurePointInfo_MpNo(UseMeasurePointInfo.mpnox,MeasurePointInfo) Then
				' --
				' Messwert X verrechnen
				' --
				If MeasurePointInfo.direction=mdXP Or MeasurePointInfo.direction=mdXM Then
					' [X+] oder [X-] Messpunkt
					
					StriOffX = Measure_Get_StrArr_MPNo(MeasurePointInfo.MpNo)+"*"+ftos(UseMeasurePointInfo.factorx)
					
				 	wcnccom(Get_Comment_Measure(MeasurePointInfo),True) ' 
					If MeasurePointInfo.direction=mdXP Then
						' bei [X+] kein   'StriOffX = "+"+StriOffX 
					ElseIf MeasurePointInfo.direction=mdXM Then
						' bei [X-]
						StriOffX = "-"+StriOffX 
					Else
						pp_err(127,UseMeasurePointInfo.MpNox)
					End If
				ElseIf UseMeasurePointInfo.mpnox>0 Then
					If (MeasurePointInfo.direction = mdYP) Or (MeasurePointInfo.direction = mdYM) Or (MeasurePointInfo.direction = mdZM) Then
						' falsche Messrichtung
						pp_err(127,UseMeasurePointInfo.MpNoy)
					Else
						pp_err(128,UseMeasurePointInfo.MpNox)
					End If
				End If
			End If
			If MeasurePointsInfos_GetMeasurePointInfo_MpNo(UseMeasurePointInfo.mpnoy,MeasurePointInfo) Then
				' --
				' Messwert Y verrechnen
				' --
				If MeasurePointInfo.direction=mdYP Or MeasurePointInfo.direction=mdYM Then
					' [Y+] oder [Y-] Messpunkt
					
					StriOffY = Measure_Get_StrArr_MPNo(MeasurePointInfo.MpNo)+"*"+ftos(UseMeasurePointInfo.Factory)
					
				 	wcnccom(Get_Comment_Measure(MeasurePointInfo),True) ' 
					If MeasurePointInfo.direction=mdYP Then
						' bei [Y+] kein 'StriOffY = "+"+StriOffY 
					ElseIf MeasurePointInfo.direction=mdYM Then
						' bei [Y-]
						StriOffY = "-"+StriOffY 
					Else
						pp_err(127,UseMeasurePointInfo.MpNoy)
					End If
				ElseIf UseMeasurePointInfo.mpnoy>0 Then
					If (MeasurePointInfo.direction = mdXP) Or (MeasurePointInfo.direction = mdXM) Or (MeasurePointInfo.direction = mdZM) Then
						' falsche Messrichtung
						pp_err(127,UseMeasurePointInfo.MpNoy)
					Else
						pp_err(128,UseMeasurePointInfo.MpNoy)
					End If
				End If
			End If
			If MeasurePointsInfos_GetMeasurePointInfo_MpNo(UseMeasurePointInfo.mpnoz,MeasurePointInfo) Then
				' --
				' Messwert Z verrechnen
				' --
				If MeasurePointInfo.direction=mdZM Then
					' [Z-] Werkstueckdicke messen
					
				 	wcnccom(Get_Comment_Measure(MeasurePointInfo),True) ' 
				 	
					StriOffZ = Measure_Get_StrArr_MPNo(MeasurePointInfo.MpNo)+"*"+ftos(UseMeasurePointInfo.Factorz)
					'StriOffZ = "+"+StriOffZ
				Else
					If (MeasurePointInfo.direction = mdXP) Or (MeasurePointInfo.direction = mdXM) Or (MeasurePointInfo.direction = mdYP) Or (MeasurePointInfo.direction = mdYM) Then
						' falsche Messrichtung
						pp_err(127,UseMeasurePointInfo.MpNoy)
					Else
						pp_err(128,UseMeasurePointInfo.MpNoz)
					End If
				End If
			ElseIf UseMeasurePointInfo.mpnoz>0 Then
				pp_err(128,UseMeasurePointInfo.MpNoz)
			End If
			If equal(MeasurePointInfo.MpNo,0) Then
				' Messwert Aufhebung z.B. Bohren
				wcnccom("NO MEAS OFFSET",True)
			End If
			WCNC_IDD("CP_MEAS_OFFSET",StriOffX,StriOffY,StriOffZ)
			
		
		End If
	End If
	

End Function

