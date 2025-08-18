' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \hh7\pp_isg.bas
' -- 
' -----------------------------------------
'#uses "pp_math.bas"
'#uses "pp_global.bas"
'#uses "pp_7.bas"

Option Explicit

'***********************************************************************************
'*************************************  Types  *************************************
'***********************************************************************************
Global Const ISG_OffPX = "V.P.OOX"
Global Const ISG_OffPY = "V.P.OOY"
Global Const ISG_OffPZ = "V.P.OOZ"

Global Const ISG_PARKXVAR = "V.P.PX"
Global Const ISG_PARKYVAR = "V.P.PY"

Global Const ISG_TCARR = ""     '"CP_TCARR"       ' ?????????
'Global Const ISG_TCARROFF = "CP_TCARROFF"    ' ?????????
Global Const ISG_TCARROFF = "CP_TCPARAOFF"    ' MW 21.04.2009


Global Const ISG_MAX_LIMIT_ZPLUS="V.P.MAXZ"
Global Const ISG_MAX_LIMIT_Z2PLUS="V.P.MAXZ2"
Global Const ISG_MAX_LIMIT_Z3PLUS="V.P.MAXZ3"       ' -- MW 03.05.2007 07:50:35
Global Const ISG_MAX_LIMIT_XPLUS="V.P.MAXX"
Global Const ISG_MAX_LIMIT_XMINUS="V.P.MINX"
Global Const ISG_MAX_LIMIT_YPLUS="V.P.MAXY"
Global Const ISG_MAX_LIMIT_YMINUS="V.P.MINY"

Global Const ISG_MAX_LIMIT_ZPLUS_MACHINE="V.A.+SWE_MDS.Z-1"


Global Const ISG_DCORRECTIONMARKER="V.P.DCMARKER"

' --  Neu MW 22.03.2006
Global Const ISG_LIFTOFFSETX = "V.P.LIFTOX"
Global Const ISG_LIFTOFFSETY = "V.P.LIFTOY"
Global Const ISG_LIFTOFFSETZ = "V.P.LIFTOZ"


Global Const ISG_EXT_CYCLE = ".NC"
Global Const ISG_EXT_MAIN = ".NC"


Global Const ISG_MGUD_LASERA= "V.P.LP_MODE_A"
Global Const ISG_MGUD_LASERB= "V.P.LP_MODE_D"

Global is_CSon As Boolean 

Global Const ISG_MEACYCLE= "CP_MEA_X"  ' MW 05.03.2014  Cycle - Name
Global Const ISG_MEA_X= "V.P.MEAOFFX"  ' MW 05.03.2014  Messwert - Parameter

Global Const ISG_MEAS_ARR = "V.P.MEASARR"  ' MW 24.04.2019  Messwert - Array Werktstueckbezogen V.P.MEASARR_1;V.P.MEASARR_2 usw.

Function ISG_init_NCVARNames

	g_OffPX=ISG_OffPX
	g_OffPY=ISG_OffPY
	g_OffPZ=ISG_OffPZ
	
	g_PARKXVAR=ISG_PARKXVAR
	g_PARKYVAR=ISG_PARKYVAR
	
	g_TCARR=ISG_TCARR
	g_TCARROFF=ISG_TCARROFF
	
    g_MAX_LIMIT_ZPLUS=ISG_MAX_LIMIT_ZPLUS
	g_MAX_LIMIT_Z2PLUS=ISG_MAX_LIMIT_Z2PLUS
	g_MAX_LIMIT_Z3PLUS=ISG_MAX_LIMIT_Z3PLUS
	g_MAX_LIMIT_XPLUS=ISG_MAX_LIMIT_XPLUS
	g_MAX_LIMIT_XMINUS=ISG_MAX_LIMIT_XMINUS
	g_MAX_LIMIT_YPLUS=ISG_MAX_LIMIT_YPLUS
	g_MAX_LIMIT_YMINUS=ISG_MAX_LIMIT_YMINUS
	g_DCORRECTIONMARKER=ISG_DCORRECTIONMARKER
	g_LIFTOFFSETX = ISG_LIFTOFFSETX
	g_LIFTOFFSETY = ISG_LIFTOFFSETY
	g_LIFTOFFSETZ = ISG_LIFTOFFSETZ
	

	
End Function

Function WCNC_START_DEF_ISG
Dim i,HaubenMode As Integer
Dim HP() As Double   ' Haubenstellungen
Dim SStri As String
	
	wcncwo("#VAR")
	wcncwo("V.P.LAENGE= "+FToS(FinishedPart.X))
	wcncwo("V.P.BREITE= "+FToS(FinishedPart.Y))
	wcncwo("V.P.DICKE= "+FToS(FinishedPart.Z))
	wcncwo(ISG_OffPX+"=0")
	wcncwo(ISG_OffPY+"=0")
	wcncwo(ISG_OffPZ+"=0")
	
	wcncwo(ISG_MAX_LIMIT_ZPLUS+"=0")
	
	
	If FiveAxis.Yes And Not FiveAxis.isg Then
		' --
		' -- Modified  MW 09.05.2011
		' --
		wcncwo(ISG_MAX_LIMIT_Z3PLUS+"=0")
	End If

	wcncwo(ISG_MAX_LIMIT_XPLUS+"=0")
	wcncwo(ISG_MAX_LIMIT_XMINUS+"=0")
	wcncwo(ISG_MAX_LIMIT_YPLUS+"=0")
	wcncwo(ISG_MAX_LIMIT_YMINUS+"=0")
	
	wcncwo(ISG_PARKXVAR+"=0")
	wcncwo(ISG_PARKYVAR+"=0")

	wcncwo(ISG_DCORRECTIONMARKER+"=0")

	' Neu MW 22.03.2006
	wcncwo(ISG_LIFTOFFSETX+"=0")
	wcncwo(ISG_LIFTOFFSETY+"=0")
	wcncwo(ISG_LIFTOFFSETZ+"=0")
	
	' --
	' -- Modified  MW 29.04.2008 09:16:18
	' --
	wcncwo(ISG_MGUD_LASERA+"=0")
	wcncwo(ISG_MGUD_LASERB+"=0")
	
	' --
	' -- Modified  AK 08.07.2009
	' --
	wcncwo("V.P.NPOFFSETX= " + FtoS(JobPara.NPX))
	wcncwo("V.P.NPOFFSETY= " + FtoS(JobPara.NPY))
	wcncwo("V.P.NPOFFSETZ= " + FtoS(JobPara.NPZ))
	' --
	' -- Modified  AK 21.02.2012
	' --
	wcncwo("V.P.AUTOXSTRATEGIE= 0")
	
	If JobPara.is_Evo Then
		' geaendert von DS (HH) 02.09.2013 
		wcncwo("V.P.UMSPANNHUB= 0")
		' MW 05.03.2014
		wcncwo(ISG_MEA_X+"= 0")
	End If
	
	If (Jumps_ok) Then
	
		' --
		' -- Modified  MW 12.12.2012
		' --
		wcncwo("V.P.JMPTIMESTAMP= "+JobPara.JumpStamp)
	End If


	' --
	' -- Modified  MW 02.12.2013
	' --
	HP = MT_Get_Head_SchwellwerteHaube(1,HaubenMode) 
	If HaubenMode=1 Then
		' MW 17.01.2014 Nur bei HaubenMode=1 gibt es Array HP
		 
		If (UBound(HP)>0) Then
			' Mode=1 dann dynamisch
			For i = 1 To UBound(HP) 
				SStri = SStri + ftos(HP(i))
				If i< UBound(HP) Then
					SStri = SStri + ","
					
				End If
			Next i
			wcncwo("V.P.HOODPOS["+inttos(UBound(HP) )+"]=["+SStri+"]")
		End If
	End If
	
	'Neu AK 24.11.2016 Ausgabe HLaserdaten
	WCNC_HLASER
	
	WCNC_MEASURING_ARR()  ' MW 24.04.2019 VARDEF Werkstueckbezogenes Array fuer Messpunkte

	wcncwo("#ENDVAR")
	
	wcnc(ISG_MAX_LIMIT_ZPLUS+"="+ISG_MAX_LIMIT_ZPLUS_MACHINE)
	If FiveAxis.Yes And Not FiveAxis.isg Then
		' --
		' -- Modified  MW 09.05.2011
		' --
		wcnc(ISG_MAX_LIMIT_Z3PLUS+"=V.A.+SWE_MDS.Z3-1")
	End If
	

	wcnc(ISG_MAX_LIMIT_XPLUS+"=V.A.+SWE_MDS.X-1")
	wcnc(ISG_MAX_LIMIT_XMINUS+"=V.A.-SWE_MDS.X+1")
	wcnc(ISG_MAX_LIMIT_YPLUS+"=V.A.+SWE_MDS.Y-1")
	wcnc(ISG_MAX_LIMIT_YMINUS+"=V.A.-SWE_MDS.Y+1")
	

End Function



Function WCNC_START_DEF_ISG_EXT2
Dim ZP_Name As String	
Dim CS As ClampSituation
Dim MCD As IMachineComponentsData
Dim ClampCount As Integer
Dim TMC As IMachineComponent


	If Not JobPara.is_Evo Then
		SET_Zero_ISG(WPI(0).WPName,JobPara.NPX,JobPara.NPY,JobPara.NPZ)
	Else
		' geaendert von DS (HH) 02.09.2013 
		'ISG_CC("Check SCI")
		' Warum hier kein aktives Werkstueck. haengt Verschiebung nicht von Werkstueck / Nullpunkt ab?
		'MsgBox(FToS(Marker.wp_actindex))
		'MsgBox(FToS(WPI(Marker.wp_actindex).SType))
		'	MsgBox(FToS(WPI(1).Sox))
		' SCI check Type of Zeropoint for G74 
		Set CS = NCData.NCClampSituations.ClampSituations.GetItem_Index(0)
		Set MCD = CS.MachineComponentsData
		Set TMC = MCD.MachineComponents.ComponentList.GetTraverse_Index(0)
	
		'msgbox(FToS(JobPara.NPX-TMC.PosX))
		ZP_Name= WPI(1).SName
		
		If Not MCDATA.ZeroPoints.GetZeroPointName(ZP_Name) Is Nothing Then
			' --
			' MW 03.09.2013
			' --
			' -- Nullpunktsfestlegung EVO
			' --  
			If 	Val(MCDATA.ZeroPoints.GetZeroPointName(ZP_Name).Additions.GetAddition_ID(-200000).Value) = 1 Then
				' -200000 = 1 Teil liegt auf absenkbarer Rollenbahn
			    'If WPI(1).SType=1 Then
				'SET_Zero_ISG(WPI(1).WPName,JobPara.NPX-WPI(1).Sox,JobPara.NPY-WPI(1).Soy,JobPara.NPZ-WPI(1).Soz)
				JobPara.NPX= JobPara.NPX-TMC.PosX
				
				SET_Zero_ISG(WPI(1).WPName,JobPara.NPX,JobPara.NPY,JobPara.NPZ)
			ElseIf Val(MCDATA.ZeroPoints.GetZeroPointName(ZP_Name).Additions.GetAddition_ID(-200000).Value) = 2 Then 
				' -200000 = 2 Teil liegt auf Kleinteil - Anschlag
				
				JobPara.NPX= JobPara.NPX-TMC.PosX

				SET_Zero_ISG(WPI(1).WPName,JobPara.NPX,JobPara.NPY,JobPara.NPZ)
			Else
				pp_err(0,"Sonstiger - Nullpunkt ? ")
				SET_Zero_ISG(WPI(1).WPName,JobPara.NPX,JobPara.NPY,JobPara.NPZ)
			End If
		Else
			pp_err(0,"Zeropoint " + ZP_Name + " not found.")
		End If
		
		'If JobPara.is_evo And Marker.RollerTrackDown Then
			'wcncaddcom("M155","RollerTrack down")
		'End If
	End If
	
End Function



Function ISG_CC_Get_S_(Cycle As String, Optional p1v,Optional p2v,Optional p3v,Optional p4v,Optional p5v As Variant ,Optional p6v,Optional p7v,Optional p8v,Optional p9v,Optional p10v,Optional p11v,Optional p12v,Optional p13v,Optional p14v,Optional p15v,Optional p16v) As String
Dim s As String
Dim hlnum As Double 

	s = "L CYCLE [NAME=" + UCase(Cycle) + ISG_EXT_CYCLE 
	
	If Not IsMissing(p1v) And Not IsEmpty(p1v) Then 
		If IsNumeric(p1v) Then
			hlnum = StrToFloat(p1v)
			s = s + " @P1=" + ftos(hlnum)
		Else
			If Len(p1v)>0 Then
				' z.B. Parameternamen @P1=V.P.PX
				s = s + " @P1=" + p1v
			End If
		End If
	End If
	If Not IsMissing(p2v) And Not IsEmpty(p2v) Then 
		If IsNumeric(p2v) Then
			hlnum = StrToFloat(p2v)
			s = s + " @P2=" + ftos(hlnum)
		Else
			If Len(p2v)>0 Then
				s = s + " @P2=" + p2v
			End If
		End If
	End If
	If Not IsMissing(p3v) And Not IsEmpty(p3v) Then 
		If IsNumeric(p3v) Then
			hlnum = StrToFloat(p3v)
			s = s + " @P3=" + ftos(hlnum)
		Else
			If Len(p3v)>0 Then
				s = s + " @P3=" + p3v
			End If
		End If
	End If
	
	
	If Not IsMissing(p4v) And Not IsEmpty(p4v) Then 
		If IsNumeric(p4v) Then
			hlnum = StrToFloat(p4v)
			s = s + " @P4=" + ftos(hlnum)
		Else
			If Len(p4v)>0 Then
				s = s + " @P4=" + p4v
			End If
			
		End If
	End If
	
	If Not IsMissing(p5v) And Not IsEmpty(p5v) Then 
		If IsNumeric(p5v) Then
			hlnum = StrToFloat(p5v)
			s = s + " @P5=" + ftos(hlnum)
		Else
			If Len(p5v)>0 Then
				s = s + " @P5=" + """"+p5v+""""
			End If
		End If
	End If
	If Not IsMissing(p6v) And Not IsEmpty(p6v) Then 
		If IsNumeric(p6v) Then
			hlnum = StrToFloat(p6v)
			s = s + " @P6=" + ftos(hlnum)
		Else
			If Len(p6v)>0 Then
				s = s + " @P6=" + """"+p6v+""""
			End If
		End If
	End If
	If Not IsMissing(p7v) And Not IsEmpty(p7v) Then 
		If IsNumeric(p7v) Then
			hlnum = StrToFloat(p7v)
			s = s + " @P7=" + ftos(hlnum)
		Else
			If Len(p7v)>0 Then
				s = s + " @P7=" + """"+p7v+""""
			End If
		End If
	End If
	If Not IsMissing(p8v) And Not IsEmpty(p8v) Then 
		If IsNumeric(p8v) Then
			hlnum = StrToFloat(p8v)
			s = s + " @P8=" + ftos(hlnum)
		Else
			If Len(p8v)>0 Then
				s = s + " @P8=" + """"+p8v+""""
			End If
		End If
	End If
	If Not IsMissing(p9v) And Not IsEmpty(p9v) Then 
		If IsNumeric(p9v) Then
			hlnum = StrToFloat(p9v)
			s = s + " @P9=" + ftos(hlnum)
		Else
			If Len(p9v)>0 Then
				s = s + " @P9=" + """"+p9v+""""
			End If
		End If
	End If
	If Not IsMissing(p10v) And Not IsEmpty(p10v) Then 
		If IsNumeric(p10v) Then
			hlnum = StrToFloat(p10v)
			s = s + " @P10=" + ftos(hlnum)
		Else
			If Len(p10v)>0 Then
				s = s + " @P10=" + """"+p10v+""""
			End If
		End If
	End If
	If Not IsMissing(p11v) And Not IsEmpty(p11v) Then 
		If IsNumeric(p11v) Then
			hlnum = StrToFloat(p11v)
			s = s + " @P11=" + ftos(hlnum)
		Else
			If Len(p11v)>0 Then
				s = s + " @P11=" + """"+p11v+""""
			End If
		End If
	End If
	If Not IsMissing(p12v) And Not IsEmpty(p12v) Then 
		If IsNumeric(p12v) Then
			hlnum = StrToFloat(p12v)
			s = s + " @P12=" + ftos(hlnum)
		Else
			If Len(p12v)>0 Then
				s = s + " @P12=" + """"+p12v+""""
			End If
		End If
	End If
	If Not IsMissing(p13v) And Not IsEmpty(p13v) Then 
		If IsNumeric(p13v) Then
			hlnum = StrToFloat(p13v)
			s = s + " @P13=" + ftos(hlnum)
		Else
			If Len(p13v)>0 Then
				s = s + " @P13=" + """"+p13v+""""
			End If
		End If
	End If
	If Not IsMissing(p14v) And Not IsEmpty(p14v) Then 
		If IsNumeric(p14v) Then
			hlnum = StrToFloat(p14v)
			s = s + " @P14=" + ftos(hlnum)
		Else
			If Len(p14v)>0 Then
				s = s + " @P14=" + """"+p14v+""""
			End If
		End If
	End If
	If Not IsMissing(p15v) And Not IsEmpty(p15v) Then 
		If IsNumeric(p15v) Then
			hlnum = StrToFloat(p15v)
			s = s + " @P15=" + ftos(hlnum)
		Else
			If Len(p15v)>0 Then
				s = s + " @P15=" + """"+p15v+""""
			End If
		End If
	End If
	If Not IsMissing(p16v) And Not IsEmpty(p16v) Then 
		If IsNumeric(p16v) Then
			hlnum = StrToFloat(p16v)
			s = s + " @P16=" + ftos(hlnum)
		Else
			If Len(p16v)>0 Then
				s = s + " @P16=" + """"+p16v+""""
			End If
		End If
	End If
	

	s=s+ "]" 	

	ISG_CC_Get_S_ = s
End Function


' ISG Call Cycle
' INFO:
' * Nicht uebergebene Parameter werden NC-seitig mit 0 vorinitialisiert
' * es koennen auch parameter uebergeben werden, welche gar nicht benutzt werden

Function ISG_CC(Cycle As String, Optional p1v,Optional p2v,Optional p3v,Optional p4v,Optional p5v As Variant ,Optional p6v,Optional p7v,Optional p8v,Optional p9v,Optional p10v,Optional p11v,Optional p12v,Optional p13v,Optional p14v,Optional p15v,Optional p16v)
Dim s As String
Dim ss As String
Dim hlnum As Double 
	
	s = ISG_CC_Get_S_(Cycle,p1v,p2v,p3v,p4v,p5v,p6v,p7v,p8v,p9v,p10v,p11v,p12v,p13v,p14v,p15v,p16v)
	
	wcnc(s)
	
	If UCase(Cycle)=UCase(SPF_TCheck) Then
		wcnccom("1:CAMPUS ID, 2:ToolNo, 3:DNo, 4:DZ, 5:Radius, 6:Laenge1, 7:Laenge2, 8:Laenge3")
	End If
	If UCase(Cycle)=UCase(SPF_TC) Then
		wcnccom("1:CAMPUS ID, 2:HEAD ID, 3:PLACE ID WZW, 4:ToolNo, 5:C-Achse-Heben, 6:Heben erlaubt, 7:Wechselmode, 8:XPos, 9:Achsbeschl")
	End If
	If UCase(Cycle)=UCase(SPF_TSpeed) Then
		wcnccom("1:HEAD ID, 2:DR, 3:DZ, 4:XPos, 5:YPos, 6:ZPos, 7:CRaster")
	End If
	If UCase(Cycle)=UCase(SPF_TCLift) Then
		wcnccom("1:HEAD ID, 2:STUFE")
	End If
	If UCase(Cycle)=UCase(SPF_DHCode) Then
		wcnccom("1:HEAD ID, 2:GROUPCODE 3:bm1 4:bm2 5:bm3")
	End If
	If UCase(Cycle)=UCase(SPF_TCarr) Then
		
		'ISG_CC(SPF_TCarr,l1x,l1y,l1z,l2x,l2y,l2z,l3x,l3y,l3z,v1x,v1y,v1z,v2y,v2z,a1,a2)

		wcnccom("[P1/P2/P3]:Vektorlaenge 1 bis DP")
		wcnccom("[P4/P5/P6]:Vektorlaenge 2 (ausser mittig liegender DP)")
		wcnccom("[P7/P8/P9]:Offset In Richtung Werkzeug")
		wcnccom("[P10/P11/P12]:RichtungVektor 1")
		wcnccom("[P13/P14]:RichtungVektor 2 v2y v2z")
		wcnccom("[P15]:DW [P16]:KW")
	End If
	
	
End Function

Function ISG_SUB(Cycle As String)
Dim s As String 

	s = "L " + UCase(Cycle) + ISG_EXT_CYCLE 
	wcnc(s)
End Function


Function SET_Zero_ISG(pos,oxg,oyg,ozg)

' axis definition
Const X = "X"
Const Y = "Y"
Const Z = "Z"
Const Z1 = "Z1"

Const ZP = 1


	wcnc("V.G.NP["+inttos(ZP)+"].V.X="+ftos(oxg))
	wcnc("V.G.NP["+inttos(ZP)+"].V.Y="+ftos(oyg))

	
	wcnc("V.G.NP["+inttos(ZP)+"].V.Z="+ftos(ozg))
	
	If FiveAxis.Yes And Not FiveAxis.isg Then
		' --
		' -- Modified  MW 09.05.2011
		' -- fuer 5-Achs
		' --
		wcnc(";V.G.NP["+inttos(ZP)+"].V.Z3="+ftos(ozg))
	End If
	
	wcncCom("")
	WCNC_IDD("STOPRE")
	wcnc("G"+IntToS(53+Fix_Zero))
	wcncCom("")

End Function

Function WCNC_ISG_STOPRE
	wcnc("#FLUSH WAIT")
End Function

Function WCNC_ISG_TRANSOFF
	If is_CSon Then
		wcnccom("--")
		wcnccom("VERSCHIEBUNG DEAKTIVIEREN")
		wcnccom("--")

		'wcnc("#CS OFF")
  	'2009.03.04 A.K. - Aufruf ueber Zyklus, da CS + Polynomueberschleifen Fehler macht (z.B. Rotationskontur, Fraesmode 2+3)
		wcnc("L CYCLE [NAME=CP_CS.NC @P1=0]")
	End If
	is_CSon = False
End Function

Function WCNC_ISG_TRANSON(ipx,ipy,ipz,ox,oy,oz)
	' nur Verschiebung
	
WCNC_ISG_TRANSOFF  
' --
' -- Modified  MW 28.04.2008 16:59:47
' --
		wcnccom("--")
	wcnccom("VERSCHIEBUNG AKTIVIEREN")
		wcnccom("--")
	wcnc("P1="+ftos(ipx)+"+"+ox)
	wcnc("P2="+ftos(ipy)+"+"+oy)
	wcnc("P3="+ftos(ipz)+"+"+oz)
	'2009.03.04 A.K. - Aufruf ueber Zyklus, da CS + Polynomueberschleifen Fehler macht (z.B. Rotationskontur, Fraesmode 2+3)
	wcnc("L CYCLE [NAME=CP_CS.NC @P1=1 @P2=P1 @P3=P2 @P4=P3 @P5=0 @P6="+ftos(0)+" @P7="+ftos(0)+"]")
'
'	wcnc("#CS ON[P1,P2,P3,0,"+ftos(0)+","+ftos(0)+"]")
	is_CSon = True
End Function


Function WCNC_ISG_ATRANS_AROT(ipx,ipy,ipz,rota,tipa)
Dim rotx,roty,rotz As Double 
Dim MinX,MaxX As Double 
rotx=tipa
roty=0
rotz=rota

		wcnccom("--")
	wcnccom("VERSCHIEBUNG AKTIVIEREN")
		wcnccom("--")

	Evo_Check_MeaMill(NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1),MinX,MaxX)   
	If JobPara.mea.Bea_Mea_activ = True Then
		wcnc("P1="+ftos(ipx)+"+"+g_OffPX+"+"+ISG_MEA_X )
		wcnc("P2="+ftos(ipy)+"+"+g_OffPY)
		wcnc("P3="+ftos(ipz)+"+"+g_OffPZ)
		JobPara.mea.Bea_Mea_activ = False
	Else		
		wcnc("P1="+ftos(ipx)+"+"+g_OffPX)
		wcnc("P2="+ftos(ipy)+"+"+g_OffPY)
		wcnc("P3="+ftos(ipz)+"+"+g_OffPZ)
	End If

	
	
	'wcnc("#CS ON[P1,P2,P3,"+ftos(rotx)+","+ftos(roty)+","+ftos(rotz)+"]")
	'2009.03.04 A.K. - Aufruf ueber Zyklus, da CS + Polynomueberschleifen Fehler macht (z.B. Rotationskontur, Fraesmode 2+3)
	wcnc("L CYCLE [NAME=CP_CS.NC @P1=1 @P2=P1 @P3=P2 @P4=P3 @P5="+ftos(rotx)+" @P6="+ftos(roty)+" @P7="+ftos(rotz)+"]")
	
	'wcnc("#CS ON["+ftos(ipx)+"+"+g_OffPX+","+ftos(ipy)+"+"+g_OffPY+","+ftos(ipz)+"+"+g_OffPZ+","+ftos(rota)+","+ftos(tipa)+"]")
	
	is_CSon = True
		

End Function

Function WCNC_ISG_ATRANS_AROT_DH(ipx,ipy,ipz,rota,tipa,ox,oy,oz)
Dim rotx,roty,rotz As Double 

rotx=tipa
roty=0
rotz=rota

	If (JobPara.mea.Bea_Mea_activ) And ((JobPara.mea.Orientation=orXPlus)) Then
		' Messversatz in der Bohrtiefe verrechnen
		wcnc("P1="+ftos(ipx)+Get_Val_Signed(ox)+"+"+ISG_MEA_X)
	Else
		wcnc("P1="+ftos(ipx)+Get_Val_Signed(ox))
	End If

	wcnc("P2="+ftos(ipy)+Get_Val_Signed(oy))
	wcnc("P3="+ftos(ipz)+Get_Val_Signed(oz))
	'wcnc("#CS ON["+ftos(ipx)+Get_Val_Signed(ox)+","+ftos(ipy)+Get_Val_Signed(oy)+","+ftos(ipz)+Get_Val_Signed(oz)+","+ftos(rota)+","+ftos(tipa)+"]")
	'wcnc("#CS ON[P1,P2,P3,"+ftos(rotx)+","+ftos(roty)+","+ftos(rotz)+"]")
	'2009.03.04 A.K. - Aufruf ueber Zyklus, da CS + Polynomueberschleifen Fehler macht (z.B. Rotationskontur, Fraesmode 2+3)
	wcnc("L CYCLE [NAME=CP_CS.NC @P1=1 @P2=P1 @P3=P2 @P4=P3 @P5="+ftos(rotx)+" @P6="+ftos(roty)+" @P7="+ftos(rotz)+"]")

	is_CSon = True
End Function

Function WCNC_ISG_SUPAX(x)
	wcnc("#MCS ON")
	wcnc("G0 "+XEqualToS(x))
	wcnc("#MCS OFF")
End Function

Function WCNC_ISG_SUPAY(y)
	wcnc("#MCS ON")
	wcnc("G0 "+yEqualToS(y))
	wcnc("#MCS OFF")
End Function


Function WCNC_ISG_SUPAXY(x,y)
	wcnc("#MCS ON")
	wcnc("G0"+XEqualToS(x)+YEqualToS(y))
	wcnc("#MCS OFF")
End Function



Function WCNC_ISG_SUPAZ
	wcnc("#MCS ON")
	wcnc("G0 Z="+g_MAX_LIMIT_ZPLUS)
	wcnc("#MCS OFF")
End Function

Function WCNC_ISG_SUPAZ5AXIS
	wcnc("#MCS ON")
	wcnc("G0 Z="+g_MAX_LIMIT_ZPLUS +" Z3="+g_MAX_LIMIT_Z3PLUS)
	wcnc("#MCS OFF")
End Function

Function WCNC_ISG_G602

	WCNC(";G602")
	
End Function

Function WCNC_ISG_BRISK

	'WCNC(";BRISK")
	
End Function

Function WCNC_ISG_SOFT

	'WCNC(";SOFT")
	
End Function


Function WCNC_ISG_G64G17SOFT

	WCNC(";G64 G17 SOFT")
	
End Function

Function WCNC_ISG_G500
	wcnc(";G500")
End Function

Function WCNC_ISG_G90D0
	WCNC("G90 D0")
End Function

Function WCNC_ISG_G500G90D0
	WCNC("G90 D0 ;G500")
End Function


Function WCNC_ISG_CUT2DF
	WCNC(";CUT2DF")
End Function

Function WCNC_ISG_CFIN
	WCNC(";CFIN")
End Function


Function W_________CNC_ISG_TCarr(v1,v2)
		WCNC(g_TCARR+" T"+inttos(v1)+" D"+inttos(v2))
End Function

'Function WCNC_ISG_OFFN(v1,v2)
'	wcnccom("Toolradius manipulation - offn")
'	wcnc("V.G.WZ_AKT.R=V.G.WZ_AKT.R"+IIf(v1>=0,"+","")+ftos(v1))
'End Function


Function WCNC_ISG_SZENE(v1,v2,v3,v4,v5,v6,v7)
	' MW 11.01.2012 - v5
	ISG_CC(SPF_Szene,v1,v2,v3,v4,v5,v6,v7)
End Function

Function WCNC_ISG_IFLASERA
		   WCNC("$IF "+isg_MGUD_LASERA+"!=1 $GOTO [NOLASERMODE]")
End Function

Function WCNC_ISG_IFLASERB
		   WCNC("$IF "+isg_MGUD_LASERB+"!=1 $GOTO [NOLASERMODE]")
End Function

Function WCNC_ISG_SPF_LASERONOFF(hid,tp,OnOff)
	' --  MW 15.04.2008 08:51:28
	' --  for ISG Controller
	ISG_CC(SPF_LASERONOFF,hid,tp,OnOff)
End Function


Function WCNC_ISG_EXTCALL(v1)
	pp_err(0,"ISG EXTCALL noch nicht implementiert")
	wcnc("EXTCALL """+v1+"""")
End Function

Function WCNC_ISG_G04(v1)

	wcnc("G04 "+ftos(v1))
	
End Function

Function WCNC_ISG_MSG(v1,v2)

	'wcnc("MSG HMI["+Chr(34)+v1+Chr(34)+v2 + "]" )
' -- 
' --  MW 11.12.2008 11:38:28
' --
	'wcnc("#MSG PLC["+Chr(34)+v1+Chr(34) + "]" )
  wcnc("#MSG SYN PLC["+Chr(34)+"SID:1152 MID:30 TEXT:"+v1+Chr(34) + "]" )
	
End Function


Function WCNC_ISG_MSGOFF()

	 wcnc("#MSG SYN PLC["+Chr(34)+"SID:1152 MID:30 CLEAR"+ Chr(34) + "]" )
	
End Function

Function WCNC_ISG_TCARROFF
	If Marker.TCarr_Activ Then
		ISG_CC(g_TCARROFF)
	End If
	'wcnc("T"+IntToS(v1)+" D"+IntToS(v2))
	
End Function

Function WCNC_ISG_REQUEST_FLEX(HeadID,ID,TipAngle,rota)

	ISG_CC(SPF_REQUEST_FLEX,HeadID,ID,TipAngle,rota)

	
End Function


Function WCNC_ISG_PREINFO(H_Id,TC_Id,TC_PlaceNo,ID,XPos)

ISG_CC(SPF_PREINFO,H_Id,TC_Id,TC_PlaceNo,ID,XPos)
	
End Function

Function WCNC_ISG_ATRANSZ(v1)
	' wird bis jetzt nur beim Z-Achsfraesen fuer den Z-Offset benutzt
	
	If ((Marker.OffzCAxisMill_Activ = True) And equal(v1,0)) Or ((Marker.OffzCAxisMill_Activ = False) And Not equal(v1,0)) Then
		'wcnc("ATRANS Z="+ftos(v1))
		wcncaddcom("G90 G92 X=0 Y=0 Z="+ftos(v1),"OFF Z CAxismilling"+IIf(equal(v1,0)," off",""),True)
	End If
	
	If equal(v1,0) Then
		Marker.OffzCAxisMill_Activ = False
	Else
		Marker.OffzCAxisMill_Activ = True
	End If
End Function

Function WCNC_ISG_TCARR_ACTIVATE(T,D)

	' -- kein Aufruf notwendig, - wird bereits im Zyklus verrechnet 
	
	' --
	' -- Modified  MW 30.04.2008 15:03:35
	' -- ISG Controller
	' --
	' -- Tx Dx muss aufgerufen werden 30.04.2008
	wcnc("T"+IntToS(T)+" D"+IntToS(D))
	
End Function



Function WCNC_ISG_CONTOUR_START
	
	
	ISG_SUB(SPF_CONTOUR_START)
	
End Function


Function WCNC_ISG_CONTOUR_END

	ISG_SUB(SPF_CONTOUR_END)
	
End Function

Function WCNC_ISG_KINEMATIK(s,v1)
	If v1=1 Then
		wcnccom("TRAORI ON")
		Marker.traorion = True
	Else
		wcnccom("TRAORI OFF")
		Marker.traorion = False
	End If

	ISG_CC(s,v1)
End Function

Function WCNC_ISG_HAUBE(s,v1,v2)
	ISG_CC(s,v1,v2)
End Function


' MW 24.10.2012
Function WCNC_ISG_SUPA_TIP(TipAxisValue)
	wcnc("#MCS ON")
	wcnc("G0 A="+ftos(TipAxisValue))
	wcnc("#MCS OFF")
End Function

Function WCNC_ISG_CHK_SPEED

	
	ISG_SUB(SPF_CHK_SPEED)
	
End Function

' AK 11.03.2014
Function WCNC_ISG_CHK_SPEEDINTOLERANCE
	
	wcnc("V.P.SPEEDCHECK=2")
	wcnc("L F_MOTSPEED.NC")
	
End Function

' Neu AK 03.11.2015 Oszillierendes Fraesen 
Function WCNC_ISG_CONTOUR_START_EXT(s,v1,v2,v3,v4)
'Dim fCommand As Variant
	If v1=1 Then 'Pendelmode aktivieren
		'Set fCommand = CreateObject("NC_Data.NCData_SetOfString")	
		wcnccom("1 - OSC ON")
		Marker.fCommand1.Clear
		Marker.fCommand1.Add(ISG_CC_Get_S_(s,v1,v2,v3,v4))
		PPDLLAddStrsAfterLeadIn(marker.fCommand1,0)

		'ISG_CC(s,v1,v2,v3,v4)
		Marker.OscilationOn = True
	End If
End Function

' Neu AK 03.11.2015 Oszillierendes Fraesen 
Function WCNC_ISG_CONTOUR_END_EXT(s,v1,v2,v3,v4)
'Dim fCommand As NCData_SetOfString    ' MW 24.02.2016   Liste der Strings fuer wegschreiben NCIExt nach der Anfahrbewegung ueber DLL-Milling
	If v1=1 Or Marker.OscilationOn=True Then 
		'Pendelmode deaktivieren
		'Set fCommand = CreateObject("NC_Data.NCData_SetOfString")	
		wcnccom("1 - OSC OFF")
		Marker.fCommand2.Clear
		Marker.fCommand2.Add(ISG_CC_Get_S_(s,v1,v2,v3,v4))
		PPDLLAddStrsBeforeLeadout(Marker.fCommand2,0)  
		'ISG_CC(s,v1,v2,v3,v4)
		Marker.OscilationOn = False
	End If
End Function

Function WCNC_ISG_CONTOUR_DYNAMIC(s,v1,v2)
		ISG_CC(s,v1,v2)
End Function

' Neu AK 24.11.2016 HLaserpositionen ausgeben 
Function WCNC_HLASER
	Dim stri_line As String
	Dim i, listcount As Integer
	Dim rs As Variant

	listcount=StringListCount(HLaserInfo.HLaserListX)
	stri_line="V.P.HLASERCOUNT=" + inttos(listcount)
	wcncwo(stri_line)
	
'	stri_line="V.P.HLASERPOS"
'	if listcount>0 then 
'		stri_line = stri_line + "[3][" + inttos(listcount) + "]=["
'		For i = 0 To listcount-1
'			stri_line = stri_line + " " + StringListStrings(HLaserInfo.HLaserListTyp, i) + "," + StringListStrings(HLaserInfo.HLaserListX, i) + "," + StringListStrings(HLaserInfo.HLaserListY, i)
'			if i<listcount-1 then
'				stri_line = stri_line + ","
'			end if
'		Next i
'		stri_line = stri_line + "]"	
'	end if
'	wcncwo(stri_line)
	If listcount>0 Then 
		If Not TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(199991) Is Nothing Then
			stri_line="V.P.HLASEROFFX= " + TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(199991).Value
			wcncwo(stri_line)
		End If
		If Not TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(199992) Is Nothing Then
			stri_line="V.P.HLASEROFFY= " + TDATA.MachineData.MachineParameter.Additions.GetAddition_ID(199992).Value
			wcncwo(stri_line)
		End If
	End If			
	stri_line="V.P.HLASERPOSTYP"
	If listcount>0 Then 
		stri_line = stri_line + "[" + inttos(listcount) + "]=["
		For i = 0 To listcount-1
			stri_line = stri_line + " " + StringListStrings(HLaserInfo.HLaserListTyp, i)
			If i<listcount-1 Then
				stri_line = stri_line + ","
			End If
		Next i
		stri_line = stri_line + "]"	
	End If
	wcncwo(stri_line)
	stri_line="V.P.HLASERPOSX"
	If listcount>0 Then 
		stri_line = stri_line + "[" + inttos(listcount) + "]=["
		For i = 0 To listcount-1
			stri_line = stri_line + " " + StringListStrings(HLaserInfo.HLaserListX, i)
			If i<listcount-1 Then
				stri_line = stri_line + ","
			End If
		Next i
		stri_line = stri_line + "]"	
	End If
	wcncwo(stri_line)
	stri_line="V.P.HLASERPOSY"
	If listcount>0 Then 
		stri_line = stri_line + "[" + inttos(listcount) + "]=["
		For i = 0 To listcount-1
			stri_line = stri_line + " " + StringListStrings(HLaserInfo.HLaserListY, i)
			If i<listcount-1 Then
				stri_line = stri_line + ","
			End If
		Next i
		stri_line = stri_line + "]"	
	End If
	wcncwo(stri_line)

	
End Function


' --
' Werkstueckbezogenes Array fuer Messpunkte vordefinieren
' --
Function WCNC_MEASURING_ARR()
Dim AnzM As Integer 
Dim AnzP As Integer 
Dim i,j As Integer 
Dim stri As String
Dim WPName As String
Dim ZPName As String

	If JobPara.measuring.Activ Then
		AnzP = NCData.NCParts.Count
		For i = 0 To (AnzP - 1)
		
			AnzM = JobPara.measuring.NCParts(i).Amount
			WPName = ExtractFileName(NCData.NCParts.GetNCPart_Index(JobPara.measuring.NCParts(i).Partno).MainHopName)
			
			ZPName = NCData.NCParts.GetNCPart_Index(JobPara.measuring.NCParts(i).Partno).StopName
			
			stri = ""
			
			For j = 1 To AnzM
				If Len(stri)> 0 Then
					stri = stri + ",0"
				Else
					stri = stri + "0"
				End If
			Next j
			wcncwo(ISG_MEAS_ARR+"_"+inttos(i+1)+"["+inttos(AnzM+1)+"] = ["+stri+"]  ; WP:" +WPName + "   ZP:"+ZPName)
			
		Next i
		
	End If
	
End Function


Function WCNC_ISG_MEAS(Messtyp,Direction,x,y,z,Dist,MessTol,Param,Sic_Z,Head_X,Head_Y,Head_Z)
	
	' --
	' -- Messzyklus
	' --
	wcnccom("--")
	
	wcnc("P99=0")
	wcnc("L CYCLE [NAME=CP_MEAS.NC @P1="+inttos(Messtyp)+" @P2="+inttos(Direction)+ " @P3="+ftos(x)+" @P4="+ftos(y)+" @P5="+ftos(z)+" @P6="+ftos(Dist)+" @P7="+ftos(MessTol)+" @P8="+ftos(Sic_Z)+" @P9="+ftos(Head_X)+" @P10="+ftos(Head_Y)+" @P11="+ftos(Head_Z)+"]")
	wcnc(Param+"=P99")

End Function


Function WCNC_ISG_MEAS_OFFSET(Str_Off_X,Str_OFF_Y,Str_OFF_Z)
	' --
	' -- Messwert verrechnen
	' --
	wcnccom("--")
	wcnc("L CYCLE [NAME=CP_MEAS_OFFSET.NC @P1="+(Str_Off_X)+" @P2="+(Str_OFF_Y)+ " @P3="+(Str_OFF_Z)+"]")


	
End Function
