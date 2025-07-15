' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \RB_OH_V7\pp_isg.bas
' -- 
' -----------------------------------------
' -- 
' -- Reichenbacher - ISG / BECKHOFF Postprocessors V7 (mw) --
' -- 
' -----------------------------------------
'#uses "pp_math.bas"
'#uses "pp_global.bas"
'#uses "pp_7.bas"
'#uses "pp_mt.bas"
'#uses "pp_mtf.bas"

Option Explicit

Global Const Fix_Zero = 1   ' G54 written Zeropoint 

Global Const WKS_X = "V.P.LAENGE"
Global Const WKS_Y = "V.P.BREITE"
Global Const WKS_Z = "V.P.DICKE"
Global Const ISG_OffPX = "V.P.OOX"
Global Const ISG_OffPY = "V.P.OOY"
Global Const ISG_OffPZ = "V.P.OOZ"


Global Const ISG_MAX_LIMIT_ZPLUS="V.P.MAXZ"
Global Const ISG_MAX_LIMIT_Z2PLUS="V.P.MAXZ2"
Global Const ISG_MAX_LIMIT_Z3PLUS="V.P.MAXZ3"       ' -- MW 03.05.2007 07:50:35
Global Const ISG_MAX_LIMIT_XPLUS="V.P.MAXX"
Global Const ISG_MAX_LIMIT_XMINUS="V.P.MINX"
Global Const ISG_MAX_LIMIT_YPLUS="V.P.MAXY"
Global Const ISG_MAX_LIMIT_YMINUS="V.P.MINY"



Global Const ISG_MAX_LIMIT_ZPLUS_MACHINE="V.A.+SWE_MDS.Z-1"

Global Const ISG_DCORRECTIONMARKER="V.P.DCMARKER"


Global Const ISG_EXT_CYCLE = ".NC"
Global Const ISG_EXT_MAIN = ".NC"


Global is_CSon As Boolean 

' ------------------------------------------------------------------------------------
' --
' -- Name - Definitions for the subs on the cnc - controller

Global Const SUB_SPF_TCheck = "CH_CHECK_TOOL"  ' check tools

Global Const SUB_CARR_POS = "CH_CARRIER_POS"      ' (VP_CARRIER_NR,VP_X_POS,VP_CARRIAGE_1,VP_CARRIAGE_2,VP_CARRIAGE_3,VP_CARRIAGE_4)
Global Const SUB_CARR_START = "CH_CARRIER_START"  ' () START DER POSITIONIERUNG TRAEGER

Global Const SUB_PRG_START = "CH_PRG_START"       ' ()  SPRUNGVERTEILER NACH DEM VARIABLEN BESCHREIBEN
Global Const SUB_STOPP = "CH_PRG_WAIT"        ' (VP_SETTING,VP_MANUAL_X,VP_MANUAL_Y,VP_MESSAGE,VP_FUNKTION,VP_PLATZNUMMER)

Global Const SUB_CH_START_PROCESSING = "CH_START_PROCESSING" ' ()


Global Const SUB_VAC_ON = "CH_CHECK_CLAMP"  ' (INT VP_STOP, INT VP_SETTING, INT VP_FIELD)
'Global Const SUB_VAC_OFF = "OH_VACOFF"  ' sub name on cnc-controller

Global Const SUB_TCC = "CH_TOOLCHANGE"  ' (VP_HEADID,VP_TCID,VP_TC_PLACE,VP_TNO,VP_DNO,VP_ROTATION,VP_SPEED,VP_BREAK)
Global Const SUB_SPINDEL_ONOFF = "CH_SPINDEL"  ' (VP_HEADID, VP_SWITCH,VP_SPEED,VP_TRANSFORMATION)

Global Const SUB_BLOWING = "CH_SPINDELFUNCTION"  ' (VP_HEADID, VP_SWITCH,VP_SPEED,VP_TRANSFORMATION)
Global Const SUB_BLOWINGOFF = "BLOWING_OFF" '

Global Const SUB_TCP_ON = "CH_TCP_ON"  
Global Const SUB_TCP_OFF = "CH_TCP_OFF"
'Global Const SUB_TCarr = "OH_TCPara"   ' sub name for setting the TCarr - parameters

' HS - Mainspindle oder Bohrkopf 
'Global Const SUB_OFFUP = "OH_OFF"  ' 
'Global Const SUB_MM_UP = "MM_UP"  ' 

' Bohrkopf
Global Const SUB_DHCode = "CH_DRILLHEAD"  ' (VP_SETTING,VP_SPEED,VP_TNO,VP_DNO, VP_GROUP,VP_CODE1, VP_CODE2, VP_CODE3)
'Global Const SUB_DH_OFFUP = "HF_DH_OFF"  ' 
'Global Const SUB_DH_UP = "HF_DH_UP"  ' 

Global Const SUB_HOOD ="CH_SUCTION"    ' Absaughaube 

Global Const SUB_CONTOUR_START = "CH_CONTOUR_START"    ' VC_EINGRIFF_WKZ=1 ; WERKZEUG ALS IM FREI SETZEN
Global Const SUB_CONTOUR_END = "CH_CONTOUR_END"        ' VC_EINGRIFF_WKZ=0 ; WERKZEUG ALS IM FREI SETZEN
Global Const SUB_DYNAMIC = "CH_DYNAMIC"     


Global Const SUB_ATRANSON = "OH_ATRANSON" 
Global Const SUB_TRANSOFF = "OH_TRANSOFF"

Global Const SUB_PARK = "CH_PARKPOS"
Global Const SUB_EndProg = "CH_PRG_END"   ' ende Programm


Function WCNC_START_DEFVARS
Dim i As Integer
Dim SStri As String
	
	wcncwo("#VAR")
	wcncwo("V.P.LAENGE= "+FToS(FinishedPart.X))
	wcncwo("V.P.BREITE= "+FToS(FinishedPart.Y))
	wcncwo("V.P.DICKE= "+FToS(FinishedPart.Z))
	wcncwo(ISG_OffPX+"=0")
	wcncwo(ISG_OffPY+"=0")
	wcncwo(ISG_OffPZ+"=0")
	
	wcncwo(ISG_MAX_LIMIT_ZPLUS+"=0")
	
	
'	If FiveAxis.Yes And Not FiveAxis.isg Then
'		wcncwo(ISG_MAX_LIMIT_Z3PLUS+"=0")
'	End If

	wcncwo(ISG_MAX_LIMIT_XPLUS+"=0")
	wcncwo(ISG_MAX_LIMIT_XMINUS+"=0")
	wcncwo(ISG_MAX_LIMIT_YPLUS+"=0")
	wcncwo(ISG_MAX_LIMIT_YMINUS+"=0")
	
'	wcncwo(ISG_PARKXVAR+"=0")
'	wcncwo(ISG_PARKYVAR+"=0")

'	wcncwo(ISG_DCORRECTIONMARKER+"=0")

'	wcncwo(ISG_LIFTOFFSETX+"=0")
'	wcncwo(ISG_LIFTOFFSETY+"=0")
'	wcncwo(ISG_LIFTOFFSETZ+"=0")
	
'	wcncwo(ISG_MGUD_LASERA+"=0")
'	wcncwo(ISG_MGUD_LASERB+"=0")
	
'	wcncwo("V.P.NPOFFSETX= " + FtoS(JobPara.NPX))
'	wcncwo("V.P.NPOFFSETY= " + FtoS(JobPara.NPY))
'	wcncwo("V.P.NPOFFSETZ= " + FtoS(JobPara.NPZ))
	
	'Neu AK 24.11.2016 Ausgabe HLaserdaten
''	WCNC_HLASER

	wcncwo("#ENDVAR")
	
	wcnc(ISG_MAX_LIMIT_ZPLUS+"="+ISG_MAX_LIMIT_ZPLUS_MACHINE)
'	If FiveAxis.Yes And Not FiveAxis.isg Then
'		wcnc(ISG_MAX_LIMIT_Z3PLUS+"=V.A.+SWE_MDS.Z3-1")
'	End If
	

	wcnc(ISG_MAX_LIMIT_XPLUS+"=V.A.+SWE_MDS.X-1")
	wcnc(ISG_MAX_LIMIT_XMINUS+"=V.A.-SWE_MDS.X+1")
	wcnc(ISG_MAX_LIMIT_YPLUS+"=V.A.+SWE_MDS.Y-1")
	wcnc(ISG_MAX_LIMIT_YMINUS+"=V.A.-SWE_MDS.Y+1")
	
End Function



' schreibt funktion id - Abhaengig ins NCprogramm
' 
Function WCNC_SUB(SubName,Optional v1,Optional v2,Optional v3,Optional v4,Optional v5,Optional v6,Optional v7,Optional v8)

Dim done As Boolean
	done = False
	' -- 
	' -- FueR ISG CONTROLLER
	' --  MW 11.04.2008 12:40:28
	' --
    Select Case UCase(SubName)
		Case SUB_SPF_TCheck
			CC(SUB_SPF_TCheck,v1,v2,v3,v4,v5) 
			done = True		
		Case SUB_CARR_POS
			CC(SUB_CARR_POS,v1,v2,v3,v4,v5,v6) 
			done = True		
		Case SUB_CARR_START
			wcncCom("",True)
			CC(SUB_CARR_START) 
			wcncCom("",True)
			done = True		
		Case SUB_PRG_START
			wcncCom("",True)
			CC(SUB_PRG_START,v1,v2,v3,v4,v5,v6,v7,v8) 
			wcncCom("",True)
			done = True
		Case SUB_BLOWING
			If (PPara.Spindle_Fct > 0) Then
				CC(SUB_BLOWING,PPara.Spindle_Fct)
			ElseIf (ppara.SubProcessNo > 1) Then
				If (pparalast.Spindle_Fct <> ppara.spindle_fct) Then
					CC(SUB_BLOWING,PPara.Spindle_Fct)
				End If
			End If
			done = True
		Case SUB_BLOWINGOFF
			CC(SUB_BLOWING,0)
			done = True
		Case SUB_CH_START_PROCESSING
			wcncCom("",True)
			CC(SUB_CH_START_PROCESSING) 
			wcncCom("",True)
			done = True
		
	    Case SUB_TCP_ON
			WCNC_TCPON()
			done = True
	    Case SUB_TCP_OFF
			WCNC_TCPOFF()
			done = True
		Case SUB_STOPP
			 CC(SUB_STOPP,v1,v2,v3,v4,v5,v6)
			done = True
		Case SUB_PARK
			CC(SUB_PARK,v1,v2,v3,v4,v5)
			done = True
		Case SUB_ENDPROG
			 CC(SUB_ENDPROG,v1)
			done = True
	    Case "STOPRE"
			WCNC_STOPRE
			done = True
	    Case SUB_TRANSOFF
			WCNC_TRANSOFF
			done = True
		Case "ATRANSAROT","ATRANSAROT_P2"
			WCNC_ATRANS_AROT(v1,v2,v3,v4,v5)
			done = True
		Case "ATRANSAROT_DH"
			WCNC_ATRANS_AROT_DH(v1,v2,v3,v4,v5,v6,v7,v8)
			done = True
		Case "SUPAZ"
			WCNC_SUPAZ 
			done = True
		Case "SUPAZ5AXIS"
			WCNC_SUPAZ 
			done = True
		Case "G64G17SOFT"
			WCNC_G64G17SOFT
			done = True
		Case "G90 D0"
			WCNC_G90D0
			done = True
		Case "CUT2DF"
			WCNC_CUT2DF
			done = True
		Case "CFIN"
			WCNC_CFIN
			done = True
		Case "M5"
			wcnc("M5")
'			done = True
		Case "ENDIF"
			' IF LASER CALL
			wcnc("$ENDIF")
			done = True
		Case "EXTCALL"
			' IF LASER CALL
			WCNC_EXTCALL(v1)
			done = True
		Case "G04"
			WCNC_G04(v1)
			done = True
		Case "MSG"
			'			WCNC_MSG(v1,v2) 'Else WCNC_SIEMENS_MSG(v1,v2)
			'done = True
		Case "MSGOFF"
			'	WCNC_MSGOFF 'Else WCNC_SIEMENS_MSGOFF
			'done = True
		Case "ATRANSZ"
			'WCNC_ATRANSZ(v1) 'Else WCNC_SIEMENS_ATRANSZ(v1)
			'done = True
		Case SUB_CONTOUR_START
			WCNC_CONTOUR_START
			done = True
		Case SUB_CONTOUR_END
			WCNC_CONTOUR_END
			done = True
			
		Case SUB_Dynamic
			' Eigenschaft von Schneide
			'var_id1 = -1 
			'If Not ActT.T_CEdge Is Nothing Then
			'	If Not ActT.T_CEdge.Additions.GetAddition_ID(100) Is Nothing Then
			'		If Val(ActT.T_CEdge.Additions.GetAddition_ID(100).Value) > -1 Then
			'			var_id1 = Val(ActT.T_CEdge.Additions.GetAddition_ID(100).Value)
			'		End If
			'	End If
			'End If
			'If PPara.NCiE.dynamic.Activ Then
			'	var_id1 = PPara.NCiE.dynamic.No
			'End If
			
			' ProcessKind
			'var_id2 = GetObjectTypNo(NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1))
			WCNC_CONTOUR_DYNAMIC(SUB_Dynamic,v1)
			done = True		
		Case SUB_VAC_ON
			wcncCom("",True)
			CC(SUB_VAC_ON,v1,v2,v3,v4) 
			wcncCom("",True)
			done = True		
		Case SUB_HOOD
			'CC(SUB_HOOD,v1,v2,v3,v4,v5,v6) 
			'done = True		
	    Case "G153 G0 D0 Z=MAXZ"
		    WCNC_SUPAZ
			'wcnc("G153 G0 D0 Z="+MAX_LIMIT_ZPLUS)	
			done = True
		
	End Select

	If Not done Then 
		pp_err(122)
	End If
	
End Function


Function ISG_CC_Get_S_(Cycle As String, Optional p1v,Optional p2v,Optional p3v,Optional p4v,Optional p5v As Variant ,Optional p6v,Optional p7v,Optional p8v,Optional p9v,Optional p10v,Optional p11v,Optional p12v,Optional p13v,Optional p14v,Optional p15v,Optional p16v) As String
Dim s As String
Dim hlnum As Double 

	s = "L CYCLE [NAME=" + UCase(Cycle) + ISG_EXT_CYCLE 
	
	If Not IsMissing(p1v) And Not IsEmpty(p1v) Then 
		If IsNumeric(p1v) Then
			If UCase(TypeName(p1v)) = "BOOLEAN" Then
				hlnum = IIf(p1v,1,0)
			Else
				hlnum = StrToFloat(p1v)
			End If
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
			If UCase(TypeName(p2v)) = "BOOLEAN" Then
				hlnum = IIf(p2v,1,0)
			Else
				hlnum = StrToFloat(p2v)
			End If
			s = s + " @P2=" + ftos(hlnum)
		Else
			If Len(p2v)>0 Then
				s = s + " @P2=" + p2v
			End If
		End If
	End If
	If Not IsMissing(p3v) And Not IsEmpty(p3v) Then 
		If IsNumeric(p3v) Then
			If UCase(TypeName(p3v)) = "BOOLEAN" Then
				hlnum = IIf(p3v,1,0)
			Else
				hlnum = StrToFloat(p3v)
			End If
			s = s + " @P3=" + ftos(hlnum)
		Else
			If Len(p3v)>0 Then
				s = s + " @P3=" + p3v
			End If
		End If
	End If
	
	
	If Not IsMissing(p4v) And Not IsEmpty(p4v) Then 
		If IsNumeric(p4v) Then
			If UCase(TypeName(p4v)) = "BOOLEAN" Then
				hlnum = IIf(p4v,1,0)
			Else
				hlnum = StrToFloat(p4v)
			End If
			s = s + " @P4=" + ftos(hlnum)
		Else
			If Len(p4v)>0 Then
				s = s + " @P4=" + p4v
			End If
			
		End If
	End If
	
	If Not IsMissing(p5v) And Not IsEmpty(p5v) Then 
		If IsNumeric(p5v) Then
			If UCase(TypeName(p5v)) = "BOOLEAN" Then
				hlnum = IIf(p5v,1,0)
			Else
				hlnum = StrToFloat(p5v)
			End If
			s = s + " @P5=" + ftos(hlnum)
		Else
			If Len(p5v)>0 Then
				s = s + " @P5=" + """"+p5v+""""
			End If
		End If
	End If
	If Not IsMissing(p6v) And Not IsEmpty(p6v) Then 
		If IsNumeric(p6v) Then
			If UCase(TypeName(p6v)) = "BOOLEAN" Then
				hlnum = IIf(p6v,1,0)
			Else
				hlnum = StrToFloat(p6v)
			End If
			s = s + " @P6=" + ftos(hlnum)
		Else
			If Len(p6v)>0 Then
				s = s + " @P6=" + """"+p6v+""""
			End If
		End If
	End If
	If Not IsMissing(p7v) And Not IsEmpty(p7v) Then 
		If IsNumeric(p7v) Then
			If UCase(TypeName(p7v)) = "BOOLEAN" Then
				hlnum = IIf(p7v,1,0)
			Else
				hlnum = StrToFloat(p7v)
			End If
			s = s + " @P7=" + ftos(hlnum)
		Else
			If Len(p7v)>0 Then
				s = s + " @P7=" + """"+p7v+""""
			End If
		End If
	End If
	If Not IsMissing(p8v) And Not IsEmpty(p8v) Then 
		If IsNumeric(p8v) Then
			If UCase(TypeName(p8v)) = "BOOLEAN" Then
				hlnum = IIf(p8v,1,0)
			Else
				hlnum = StrToFloat(p8v)
			End If
			s = s + " @P8=" + ftos(hlnum)
		Else
			If Len(p8v)>0 Then
				s = s + " @P8=" + """"+p8v+""""
			End If
		End If
	End If
	If Not IsMissing(p9v) And Not IsEmpty(p9v) Then 
		If IsNumeric(p9v) Then
			If UCase(TypeName(p9v)) = "BOOLEAN" Then
				hlnum = IIf(p9v,1,0)
			Else
				hlnum = StrToFloat(p9v)
			End If
			s = s + " @P9=" + ftos(hlnum)
		Else
			If Len(p9v)>0 Then
				s = s + " @P9=" + """"+p9v+""""
			End If
		End If
	End If
	If Not IsMissing(p10v) And Not IsEmpty(p10v) Then 
		If IsNumeric(p10v) Then
			If UCase(TypeName(p10v)) = "BOOLEAN" Then
				hlnum = IIf(p10v,1,0)
			Else
				hlnum = StrToFloat(p10v)
			End If
			s = s + " @P10=" + ftos(hlnum)
		Else
			If Len(p10v)>0 Then
				s = s + " @P10=" + """"+p10v+""""
			End If
		End If
	End If
	If Not IsMissing(p11v) And Not IsEmpty(p11v) Then 
		If IsNumeric(p11v) Then
			If UCase(TypeName(p11v)) = "BOOLEAN" Then
				hlnum = IIf(p11v,1,0)
			Else
				hlnum = StrToFloat(p11v)
			End If
			s = s + " @P11=" + ftos(hlnum)
		Else
			If Len(p11v)>0 Then
				s = s + " @P11=" + """"+p11v+""""
			End If
		End If
	End If
	If Not IsMissing(p12v) And Not IsEmpty(p12v) Then 
		If IsNumeric(p12v) Then
			If UCase(TypeName(p12v)) = "BOOLEAN" Then
				hlnum = IIf(p12v,1,0)
			Else
				hlnum = StrToFloat(p12v)
			End If
			s = s + " @P12=" + ftos(hlnum)
		Else
			If Len(p12v)>0 Then
				s = s + " @P12=" + """"+p12v+""""
			End If
		End If
	End If
	If Not IsMissing(p13v) And Not IsEmpty(p13v) Then 
		If IsNumeric(p13v) Then
			If UCase(TypeName(p13v)) = "BOOLEAN" Then
				hlnum = IIf(p13v,1,0)
			Else
				hlnum = StrToFloat(p13v)
			End If
			s = s + " @P13=" + ftos(hlnum)
		Else
			If Len(p13v)>0 Then
				s = s + " @P13=" + """"+p13v+""""
			End If
		End If
	End If
	If Not IsMissing(p14v) And Not IsEmpty(p14v) Then 
		If IsNumeric(p14v) Then
			If UCase(TypeName(p14v)) = "BOOLEAN" Then
				hlnum = IIf(p14v,1,0)
			Else
				hlnum = StrToFloat(p14v)
			End If
			s = s + " @P14=" + ftos(hlnum)
		Else
			If Len(p14v)>0 Then
				s = s + " @P14=" + """"+p14v+""""
			End If
		End If
	End If
	If Not IsMissing(p15v) And Not IsEmpty(p15v) Then 
		If IsNumeric(p15v) Then
			If UCase(TypeName(p15v)) = "BOOLEAN" Then
				hlnum = IIf(p15v,1,0)
			Else
				hlnum = StrToFloat(p15v)
			End If
			s = s + " @P15=" + ftos(hlnum)
		Else
			If Len(p15v)>0 Then
				s = s + " @P15=" + """"+p15v+""""
			End If
		End If
	End If
	If Not IsMissing(p16v) And Not IsEmpty(p16v) Then 
		If IsNumeric(p16v) Then
			If UCase(TypeName(p16v)) = "BOOLEAN" Then
				hlnum = IIf(p16v,1,0)
			Else
				hlnum = StrToFloat(p16v)
			End If
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

Function CC(Cycle As String, Optional p1v,Optional p2v,Optional p3v,Optional p4v,Optional p5v As Variant ,Optional p6v,Optional p7v,Optional p8v,Optional p9v,Optional p10v,Optional p11v,Optional p12v,Optional p13v,Optional p14v,Optional p15v,Optional p16v)
Dim s As String
Dim ss As String
Dim hlnum As Double 
	
	s = ISG_CC_Get_S_(Cycle,p1v,p2v,p3v,p4v,p5v,p6v,p7v,p8v,p9v,p10v,p11v,p12v,p13v,p14v,p15v,p16v)
	
	Select Case Cycle
		Case "CH_CARRIER_POS"
			wcncaddcom(s,"TREAGER,X,Y1,Y2,Y3,Y4")
		Case "CH_CARRIER_START"
			wcnc(s)
		Case "CH_CHECK_CLAMP"
			wcncaddcom(s,"VP_STOP, VP_SETTING, VP_FIELD, VP_SECTLINK")
		Case "CH_CHECK_TOOL"
			wcncaddcom(s,"")
		Case "CH_DRILLHEAD"
			wcncaddcom(s,"ON/OFF,VP_SPEED,VP_TNO,VP_DNO, VP_GROUP,VP_CODE1, VP_CODE2, VP_CODE3")
		Case "CH_DYNAMIC"
			wcncaddcom(s,PPara.ProcInfoStr)
		Case "CH_PARKPOS"
			wcncaddcom(s,"VP_SETTING,VP_MANUAL_X,VP_MANUAL_Y,VP_FUNKTION,VP_PLATZNUMMER")
		Case "CH_PRG_END"
			wcncaddcom(s,"VP_SETTING - BITSUMME [1]Vak [2]Pneu [4]ANS [8]UTRAE [16]STOP")
		Case "SUB_PRG_WAIT"
			'VP_SETTING,VP_FUNKTION,VP_MANUAL_X,VP_MANUAL_Y,VP_PLATZNUMMER
			wcncaddcom(s,"VP_SETTING,VP_MANUAL_X,VP_MANUAL_Y,VP_MESSAGE,VP_FUNKTION,VP_PLATZNUMMER")
		Case "CH_SPINDEL"
			wcncaddcom(s,"VP_HEADID, VP_SWITCH,VP_SPEED,VP_ROTATION,VP_TRANSFORMATION")
		Case "CH_SPINDELFUNCTION"
			wcncaddcom(s,"VP_SETTING - BLASDUESE,..")
		Case "CH_SUCTION"
			'VP_HEADID, VP_SETTING , VP_POS, VP_VORPOS_X,VP_VORPOS_X, VP_VORPOS_Z
			wcncaddcom(s,"VP_HEADID, VP_SETTING , VP_POS, VP_VORPOS_X,VP_VORPOS_X, VP_VORPOS_Z")
		Case "CH_TOOLCHANGE"
			wcncaddcom(s,"VP_HEADID,VP_TCID,VP_TC_PLACE,VP_TNO,VP_DNO,VP_ROTATION,VP_SPEED,VP_BREAK")
		Case "CH_PARK" 
			wcncaddcom(s,"VP_SETTING,VP_MANUAL_X,VP_MANUAL_Y,VP_FUNKTION,VP_PLATZNUMMER")
		Case "CH_PRG_START"
			wcnc(s)
		
		Case Else
			wcnc(s)
	End Select
	

	
End Function

Function WCNC_SET_Zero(oxg,oyg,ozg)

' axis definition
Const X = "X"
Const Y = "Y"
Const Z = "Z"
Const Z1 = "Z1"

Const ZP = 1


	wcnc("V.G.NP["+inttos(ZP)+"].V.X="+ftos(oxg))
	wcnc("V.G.NP["+inttos(ZP)+"].V.Y="+ftos(oyg))

	
	wcnc("V.G.NP["+inttos(ZP)+"].V.Z="+ftos(ozg))
	
	
	wcncCom("")
	WCNC_SUB("STOPRE")
	WCNC_ZEROPOINT()
	wcncCom("")

End Function

' *****************************************************************************************
' ** Werkzeugliste zur Info ausgeben
' *****************************************************************************************
Function WCNC_Write_TCheck
Dim i,j As Long
Dim T As THopsBasicToolExt
Dim BoxNoArray() As Long
Dim idh As IIDrillingHead
Dim DH_CEdge As IICuttingEdge
Dim dummy As Variant

Dim dh_tool As IITool
Dim toolno,MaxRot,rad,length,Len1,Len2,Len3 As Double
Dim TN As String       ' ToolName
Dim DNo As Integer     ' Schneidennummer
Dim TCID As Integer ' Toolchanger IC
Dim TCPlace As Integer ' Toolchanger Place
Dim TNo As Integer ' Tool Number
	wcnccom("",True)
	wcnccom("used tools",True)
	wcnccom("",True)
	wcnccom("",True)
	For i = 1 To UBound(ToolArray)
	    ReDim Preserve BoxNoArray(i) 
	
		T = ToolArray(i)
		If Not MT_CheckisIdInList(T.t.ID,BoxNoArray) Then
		
			If Not T.tc Is Nothing Then
				' Tool is on Changer
				TCID = T.tc.HeadID
				TCPlace = T.t.GetPlaceID_OnTC
				TNo = T.t.ID
				DNo = T.T_CEdge.EdgeID
				If Not equal(DNo,1) Then
					' MW 14.02.2020 - momentan werden die Werkzeugdaten nur auf D1/D5 geschrieben
					' ==> mehrere Schneiden nicht moeglich
' MW 14.07.2021   - lt. m.t. geht das inzwischen					pp_err(353,DNo,T.t.Description)
				End If
			End If
			If Not T.t Is Nothing Then
				TN = T.t.Description
				MaxRot = T.t.MaxRotSpeed
				length = T.t.Length '-> 150.18#
				rad  = T.t.Radius '-> 8#
			End If

		
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
						    MaxRot = dh_tool.GetFirstCuttingEdge.MaxRotSpeed
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
  							'wcnccom(dh_tool.Description + " T"+inttos(toolno) +" R"+ftos(rad)+" L1:"+ftos(Len1)+" L2:"+ftos(Len2)+" L3:"+ftos(Len3) )
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

				wcnccom(T.t.Description+" S"+inttos(T.t.MaxRotSpeed)+" R"+ftos(T.t.Radius))
			ElseIf MT_IsGearBoxTool(T) Then
				
				wcnccom("BOX:"+strsize(inttos(T.t.ID),5,2)+" TCID:"+ strsize(inttos(TCID),3,1)+" TCPlace:"+ strsize(inttos(TCPlace),3,1)+" HId:"+StrSize(Inttos(T.HId),5,1)+" "+StrSize(TN,30,1)  + " MaxRotSpeed S"+ftos(MaxRot),True)
			Else
				' alle übrigen Werkzeuge
				wcnccom("BOX:"+strsize(inttos(T.t.ID),5,2)+" TCID:"+ strsize(inttos(TCID),3,1)+" TCPlace:"+ strsize(inttos(TCPlace),3,1)+" HId:"+StrSize(Inttos(T.HId),5,1)+" "+StrSize(TN,30,1)  + " MaxRotSpeed S"+ftos(MaxRot),True)
				'wcnccom("BOX:"+strsize(inttos(T.t.ID),5,2)+" HId:"+StrSize(Inttos(T.HId),5,1)+" "+StrSize(T.T.Description,30,1)  + " Platz:"+ strsize(inttos(T.t.GetPlaceID_OnTC),3,0)+" T:"+strsize(inttos(T.PH_add.ToolNo),3,0)+" D"+strsize(inttos(T.PH_ADD.CorrNo),3,0))
				'WCNC_SUB(SUB_SPF_TCheck,TCPlace,DNo,length,rad,MaxRot)
				WCNC_SUB(SUB_SPF_TCheck,TNo,DNo,length,rad,MaxRot)
				'wcncaddcom(SPF_TCheck+"("+inttos(T.t.ID)+","+inttos(T.t.ToolNo)+","+inttos(T.ph_add.CorrNo)+","+inttos(T.t.MaxRotSpeed)+","+ftos(T.t.Radius)+","+ftos(T.t.Length)+","+ftos(0)+","+ftos(0)+")","S"+ftos(T.t.MaxRotSpeed)+" R"+ftos(T.t.Radius)+" L1:"+ftos(T.t.Length)+" L2:"+ftos(0)+" L3:"+ftos(0))
			End If
		End If
		BoxNoArray(i)=T.t.ID
		'LastBoxId=t.t.ID
	Next i
	wcnccom("",True)
	wcnccom("",True)
	
End Function



Function WCNC_STOPRE
	WCNC("#FLUSH WAIT")
End Function

Function WCNC_ZEROPOINT()
	WCNC("G"+IntToS(53+Fix_Zero))
End Function


Function WCNC_TRANSOFF
	If is_CSon Then
		WCNC("#CS OFF")   
	End If
	is_CSon = False
End Function


Function WCNC_ATRANS_AROT(IPX,IPY,IPZ,RotA,TipA)
Dim rotx,roty,rotz As Double 

	rotx=TipA
	roty=0
	rotz=RotA
	
	WCNC("P1="+ftos(IPX)+"+"+ISG_OffPX)
	WCNC("P2="+ftos(IPY)+"+"+ISG_OffPY)
	WCNC("P3="+ftos(IPZ)+"+"+ISG_OffPZ)
	WCNC("#CS ON[P1,P2,P3,"+ftos(rotx)+","+ftos(roty)+","+ftos(rotz)+"]")
	
	is_CSon = True
		

End Function


Function WCNC_ATRANS_AROT_DH(IPX,IPY,IPZ,RotA,TipA,ox,oy,oz)
Dim rotx,roty,rotz As Double 

	rotx=TipA
	roty=0
	rotz=RotA

	WCNC("P1="+ftos(IPX)+Get_Val_Signed(ox))
	WCNC("P2="+ftos(IPY)+Get_Val_Signed(oy))
	WCNC("P3="+ftos(IPZ)+Get_Val_Signed(oz))
	
	WCNC("#CS ON[P1,P2,P3,"+ftos(rotx)+","+ftos(roty)+","+ftos(rotz)+"]")

	is_CSon = True

End Function


Function WCNC_SUPAX(x)
	WCNC("#MCS ON")
	WCNC("G0 "+XEqualToS(x))
	WCNC("#MCS OFF")
End Function

Function WCNC_SUPAY(y)
	wcnc("#MCS ON")
	wcnc("G0 "+yEqualToS(y))
	wcnc("#MCS OFF")
End Function


Function WCNC_SUPAXY(x,y)
	wcnc("#MCS ON")
	wcnc("G0"+XEqualToS(x)+YEqualToS(y))
	wcnc("#MCS OFF")
End Function

Function WCNC_SUPAZ
	wcnc("#MCS ON")
	wcnc("G0 Z="+ISG_MAX_LIMIT_ZPLUS)
	wcnc("#MCS OFF")
End Function


Function WCNC_G64G17SOFT

	'WCNC("G64 G17 SOFT")
	
End Function

'Function WCNC_G500
'	wcnc(";G500")
'End Function

Function WCNC_G90D0
	WCNC("G90 D0")
End Function

'Function WCNC_G500G90D0
'	WCNC("G500 G90 D0")
'End Function


Function WCNC_CUT2DF
'	WCNC("CUT2DF")
End Function

Function WCNC_CFIN
'	WCNC("CFIN")
End Function

Function WCNC_EXTCALL(v1)
	pp_err(0,"ISG EXTCALL noch nicht implementiert")
	wcnc("EXTCALL """+v1+"""")
End Function

Function WCNC_G04(v1)

	wcnc("G04 "+ftos(v1))
	
End Function



Function WCNC_CONTOUR_START
Dim cycl As String
	wcnccom("",True)
	'wcncaddcom("VC_EINGRIFF_WKZ=1","WERKZEUG ALS IM FREI SETZEN",True)
	cycl = SUB_CONTOUR_START
	'wcncaddcom("L CYCLE [NAME="+cycl+".NC]","TCP On")
	CC(cycl)
	wcnccom("",True)	
	
End Function


Function WCNC_CONTOUR_END
Dim cycl As String
	wcnccom("",True)	
	'wcncaddcom("VC_EINGRIFF_WKZ=0","WERKZEUG ALS FREI SETZEN",True)
	cycl = SUB_CONTOUR_END
	'wcncaddcom("L CYCLE [NAME="+cycl+".NC]","TCP On")
	CC(cycl)
	wcnccom("",True)	
	
End Function


Function WCNC_CONTOUR_DYNAMIC(s,v1)  ',v2)
'	CC(s,v1,v2)
	CC(s,v1)
End Function


Function WCNC_TCPON()
Dim cycl As String
	cycl = SUB_TCP_ON
	'wcncaddcom("L CYCLE [NAME="+cycl+".NC]","TCP On")
	CC(cycl)
End Function

Function WCNC_TCPOFF()
Dim cycl As String
	cycl = SUB_TCP_OFF
	CC(cycl)
	'wcncaddcom("L CYCLE [NAME="+cycl+".NC]","TCP Off")
End Function


' call	WCNC_Machine_Stop(Park,X,Y,stri,NextBoxWorking,HeadID)

Function WCNC_Machine_Stop(Mode,Para1,Para2,Para3,characters,NextBoxWorking,HeadID,MessageNo)

Dim Park As Integer
'Dim ParkX,ParkY As Double
Dim FBit1 As Integer   ' Werkzeug wird ausgewechselt
Dim FBit2 As Integer   ' Werkzeug wird eingewechselt 
Dim FBit3 As Integer   ' Spindel bleibt eingeschaltet
Dim FBit4 As Integer   ' Programm STOPP M0
Dim FBit5 As Integer   ' Keine Grundstellung Rundachsen

Dim VP_SETTING As Integer 
Dim VP_MANUAL_X As Double
Dim VP_MANUAL_Y As Double 
Dim VP_MESSAGE As Integer
Dim VP_FUNKTION As Integer 
Dim VP_PLATZNUMMER As Long

	Park = Para1
	If Park=10 Then
		VP_MANUAL_X = Para2
		VP_MANUAL_Y = Para3
	Else
		VP_MANUAL_X = 0
		VP_MANUAL_Y = 0
	End If
	
	VP_SETTING = Trans2Cycle(Park)  ' Nummerierung ist nicht 1:1 uebernommen worden
	VP_MESSAGE = MessageNo   ' ISG bietet keine Möglichkeit einen Text zu uebergeben       ===>   ' Chr(34)+ characters+ Chr(34)
	VP_FUNKTION = 0
	VP_PLATZNUMMER = 0
	
'	If Len(VP_MESSAGE)<=0 Then
'		If (JobPara.language.ID=1031) Then
'			VP_MESSAGE = "programmierter Maschinen-STOPP - weiter mit NC-Start"
'		Else
'			VP_MESSAGE = "programmed machine stop - go on with start"
'		End If
'	End If
	
	wcnccom("*")
	wcnccom(" Machine STOPP - Parkmode:"+inttos(Park))
	wcnccom("*")
	
	FBit1 = 0
	FBit2 = 0
	FBit3 = 0
	FBit4 = 1  ' M0
	FBit5 = 0  ' Keine Grundstellung Rundachsen
	If Not equal(PPara.ActT.t.ID,NextBoxWorking) Then
		' -->  es folgt andere Werkzeug
		
		If Not MT_GB_Output_Changed(PPara.ActT,pParaNext.ActT) And Not MT_TEdgeChange(PPara.ActT,pParaNext.ActT) Then
			' --> anderes Werkzeug nicht auf gleichem Winkelgetriebe und kein Schneidenwechsel
			
			If MT_Is_TC_T(pParaNext.ActT) Then
				' aktuelles Werkzeug auf/von Wechsler
			
				FBit1 = 1   ' Werkzeug wird ausgewechselt
				FBit2 = 1   ' Werkzeug wird eingewechselt
				VP_PLATZNUMMER = pParaNext.TNo_Tmp
			End If
		End If
	Else
		FBit3 = 1
		If equal(Mode,1) Then
			' MW 07.06.2022 ueber Mode Spindel AUS steuerbar
			FBit3 = 0
		End If
		
	End If
	VP_FUNKTION = IIf(FBit1=1,exponent2(1),0) + IIf(FBit2=1,exponent2(2),0) + IIf(FBit3=1,exponent2(3),0) + IIf(FBit4=1,exponent2(4),0) + IIf(FBit5=1,exponent2(5),0) 
	
	WCNC_SUB(SUB_STOPP,VP_SETTING,VP_MANUAL_X,VP_MANUAL_Y,VP_MESSAGE,VP_FUNKTION,VP_PLATZNUMMER)
	
	
	' G53 / unterdrueckt keine TRAORI
'	If MT_Is_Vertical_StandardTool5Axis(actt) Then
'		wcnc_IDD(SUB_TCP_OFF)  ' actt.ph_add.TraoriOff)
'	End If

	ActV.View = -1   ' erzwingt einen erneuten Ebenenwechsel	
	
	Marker.MachineStopActive=True
	
	
End Function


Function WCNC_SET_WZ_DATA_STANDARD(T As THopsBasicToolExt)
Dim TNo As Long
Dim DNo As Long 
	TNo = PPara.TNo_Tmp   ' T.PH_Add.Tool_No
	DNo = PPara.DNo_Tmp   ' T.PH_Add.Corr_No

	wcncaddcom("$TC_DP1["+inttos(TNo)+","+inttos(DNo)+"]=120"," Typ")
	wcncaddcom("$TC_DP6["+inttos(TNo)+","+inttos(DNo)+"]="+ftos(T.t.Radius)," Radius")
	wcncAddCom("$TC_DP5["+IntToS(TNo)+","+IntToS(DNo)+"]=0","Length X")  
	wcncaddcom("$TC_DP4["+inttos(TNo)+","+inttos(DNo)+"]=0","Length Y")
	wcncAddCom("$TC_DP3["+IntToS(TNo)+","+IntToS(DNo)+"]="+ftos(T.t.Length),"Length Z")  
	WCNC_STOPRE
	
End Function

Function WCNC_SET_WZ_DATA_GB(T As THopsBasicToolExt)
Dim TNo As Long
Dim DNo As Long 
	TNo = ppara.tno_tmp   ' T.PH_Add.Tool_No
	DNo = ppara.dno_tmp   ' T.PH_Add.Corr_No
	' MW 15.11.2018 nur Radius 

	wcncaddcom("$TC_DP1["+inttos(TNo)+","+inttos(DNo)+"]=120"," Typ")
	wcncaddcom("$TC_DP6["+inttos(TNo)+","+inttos(DNo)+"]="+ftos(T.t.Radius)," Radius")
	wcncAddCom("$TC_DP5["+IntToS(TNo)+","+IntToS(DNo)+"]=0","Length X")  
	wcncaddcom("$TC_DP4["+inttos(TNo)+","+inttos(DNo)+"]=0","Length Y")
	wcncAddCom("$TC_DP3["+IntToS(TNo)+","+IntToS(DNo)+"]=0","Length Z")  
	WCNC_STOPRE
	
End Function





' *****************************************************************************************
' ** Werkzeugwechsel - Abhandlung
' *****************************************************************************************
' t= actt
' spindlecode = 00110101 etc.
' ids = 109,110,112, etc.
Function WCNC_WRITE_DHCode(tools,UpAndOff)   '
Dim Code As TBMuster
Dim Orientation As Variant
Dim one_spindle As Long
Dim FirstTNr As Long
Dim TP_GroupCode As Integer 
Dim T As THopsBasicToolExt
Dim DH_TP As IIDH_ToolPlace
Dim itp As Variant
Dim VP_SETTING As Integer 
Dim VP_SPEED As Double
Dim VP_TNO As Integer 
Dim VP_DNO As Integer 
Dim VP_GROUP As Integer 
Dim VP_CODE1, VP_CODE2, VP_CODE3 As Double 

	VP_GROUP = 0
	VP_SETTING = 0
	VP_SPEED = ppara.Spindle_SPEED
	VP_CODE1 = 0
	VP_CODE2 = 0
	VP_CODE3 = 0
	T = ppara.actt
	FirstTNr = Val(Get_First_Token(tools))   
	TP_GroupCode = 0
	If FirstTNr>0 Then
		
		If MT_IsDH(T) Then
			Set itp = T.t_dh.DrillingHead.ToolPlaces.GetToolPlace_PlaceID(FirstTNr)
			Set DH_TP=itp
			If DH_TP.Orientation=orVertical Then
				VP_GROUP = 1
			ElseIf (DH_TP.Orientation=orXPlus) Or (DH_TP.Orientation=orXMinus)  Then
				VP_GROUP = 2
			ElseIf (DH_TP.Orientation=orYPlus) Or (DH_TP.Orientation=orYMinus)  Then
				VP_GROUP = 3
			Else
				pp_err(351)
			End If
		ElseIf MT_isDHSaw(T) Then
			Set itp = T.t_dhsaw.DrillingHead.ToolPlaces.GetToolPlace_PlaceID(FirstTNr)
			Set DH_TP=itp
			If (DH_TP.Orientation=orYPlus) Or (DH_TP.Orientation=orYMinus)  Then
				' Saege X
				VP_GROUP = 4
			ElseIf (DH_TP.Orientation=orXPlus) Or (DH_TP.Orientation=orXMinus)  Then
				' Saege Y
				VP_GROUP = 5
			Else
				pp_err(351)
			End If
		Else
			pp_err(0,"wrong tool")
		End If
		TP_GroupCode = DH_TP.GroupID
		
	End If
	
	If Not UpAndOff	Then
		VP_SETTING = 1
	Else
		VP_SETTING = 0
	End If
	
	If FirstTNr <= 0 Then
		' Werkzeugabwahl
		Code.GroupCode = 0     ' 0=alles zuruecksetzen  marker.last_bm.GroupCode
	Else
		' Spindelcodierung anhand angegebener Spindelnummer ermitteln
		' und zurueckgeben in Bm1 und BM2, BM3
		MT_Get_SpindleCode_Dez(tools,Code)
		VP_CODE1 = Code.BM1
		VP_CODE2 = Code.BM2
		VP_CODE3 = Code.BM3

		
	End If
	
	
	If (Code.BM1 <> Marker.last_bm.BM1) Or (Code.BM2 <> Marker.last_bm.BM2) Or (Code.BM3 <> Marker.last_bm.BM3) Then
		If Code.BM1<=0 And Code.BM2<=0 And Code.BM3<=0 Then
			wcnccom("dh pins up",True)
		Else
			wcnccom("dh pins downs #"+tools,True)
		End If

	
		CC(SUB_DHCode,VP_SETTING,VP_SPEED,VP_TNO,VP_DNO, VP_GROUP,VP_CODE1, VP_CODE2, VP_CODE3)
		
    	wcnccom(" * BM1:"+ftos(Code.BM1)+" * BM2:"+ftos(Code.BM2)+" * BM3:"+ftos(Code.BM3))
	    
	End If
	Marker.Last_Bm.BM1 = Code.BM1
	Marker.Last_Bm.BM2 = Code.BM2
	Marker.Last_Bm.BM3 = Code.BM3
	Marker.Last_Bm.GroupCode = Code.GroupCode
	
	PosReset
End Function


' --
' Aufruf von Process_Start
' --
Function WCNC_WRITE_WZW()
Dim VP_HEADID As Integer
Dim VP_TCID As Integer
Dim VP_TC_PLACE As Integer
Dim VP_TNO As Integer
Dim VP_DNO As Integer
Dim VP_ROTATION As Integer
Dim VP_SPEED As Integer
Dim VP_BREAK As Integer

	VP_HEADID = PPara.HId  ' gibt es immer
	If MT_Is_TC_T(PPara.ActT) Then
		VP_TCID = PPara.ActT.T.GetOn_TC.HeadID 
		VP_TC_PLACE = PPara.ActT.t.GetPlaceID_OnTC
	Else
		VP_TCID = -1
		VP_TC_PLACE = -1
	End If
	
	VP_TNO = PPara.ActT.T.ID
	VP_DNO = 0
	
	VP_BREAK = 0
	MT_Get_ID_Tool(PPara.ActT,100,0,VP_BREAK) 

	' Drehrichtung / Drehzahl
	VP_ROTATION = PPara.Spindle_DIR
	VP_SPEED = Abs(PPara.Spindle_SPEED)
	
	If MT_IsDH(PPara.ActT) Then
		wcnccom("DRILLING HEAD #"+IntToS(VP_HEADID),True)
	ElseIf MT_isDHSaw(PPara.ActT) Then
		wcnccom("DH SAWING HEAD #"+IntToS(VP_HEADID),True)
	ElseIf MT_Is_TC_T(PPara.ActT) Then
		' Wechselspindel
		
		wcnccom("HEADID [#"+IntToS(VP_HEADID) + "] TCID [#"+inttos(VP_TCID)+ "]  TCPLACE [#"+IntToS(VP_TC_PLACE)+"]",True)
	Else
		pp_err(3)
	End If
	wcnccom("",True)
	CC(SUB_TCC,VP_HEADID,VP_TCID,VP_TC_PLACE,VP_TNO,VP_DNO,VP_ROTATION,VP_SPEED,VP_BREAK)
	wcnccom("",True)
	
End Function

' --
' Aufruf von ToolChange WCNC_Write_Speed()
' Aufruf von ViewChange WCNC_Write_Speed()  fuer moegliche Drehzahlaenderung
' --
'VP_HEADID BEARBEITUNGSKOPF ID
'VP_SWITCH EINSCHALTEN / AUSSCHALTEN
'      ==> + PNEUMATISCH VORLEGEN / ZURUECKLEGEN ETC.
'          0== AUSCHALTEN
'          1== EINSCHALTEN
'VP_SPEED DREHZAHL (AENDERUNG)

Function WCNC_Write_Speed() 
Dim VP_HEADID As Integer
Dim VP_SWITCH As Integer
Dim VP_ROTATION As Integer
Dim VP_SPEED As Double
Dim VP_TRANSFORMATION As Boolean 
	VP_HEADID = PPara.HId 
	VP_SWITCH = 1   ' hier einschalten 
	VP_ROTATION = PPara.Spindle_DIR
	VP_SPEED = Abs(PPara.Spindle_SPEED)
	
	If MT_IsGB(ppara.actT) Then
		' MW 28.06.2022 nicht bei Winkelgetriebe
		VP_TRANSFORMATION = False
	Else
		VP_TRANSFORMATION = True
	End If

	Select Case PPara.PreObjectTyp
'		Case otNCInfoProcess,otNCInfoProcessMPs
'			' DINISO - PROZESS - nur wenn Drehzahl gewuenscht absetzen
'			If Not (IsDINISO_No_Speed) And (isDINISO_Process) Then
'				CC(SUB_SPINDEL_ONOFF,VP_HEADID,VP_SWITCH,VP_SPEED)				
'			End If
		
		Case otDHProcess 		    
			' --
			' -- wenn Speed = 0 -> dann Drehzahl von Bohrer uebernehmen
			' --
'		Case otVertDrilling, otHorzDrilling
'			If ((Not equal(Marker.LastSpeed,PPara.Speed)) Or TC) Then
'				CC(SUB_SPINDEL_ONOFF,VP_HEADID,VP_SWITCH,VP_SPEED)				
'			End If
		Case Else
			If (ppara.SubProcessNo = 1) Then
				' 1. Sub Prozess immer Drehzahl absetzen
				CC(SUB_SPINDEL_ONOFF,VP_HEADID,VP_SWITCH,VP_ROTATION,VP_SPEED,VP_TRANSFORMATION)				
			ElseIf Not equal(ppara.speed,pparalast.speed) Then
				CC(SUB_SPINDEL_ONOFF,VP_HEADID,VP_SWITCH,VP_ROTATION,VP_SPEED,VP_TRANSFORMATION)
			ElseIf (ppara.SubProcessNo > 1) Then
				' MW 07.06.2022
				' --> 2. oder weiterer Prozess 
				If (aPPara(ppara.plNo-1).M_Stopp_Activ) Then
					' --> dazwischen Maschinenstopp mit etwaigem Spindel anhalten
					'
					CC(SUB_SPINDEL_ONOFF,VP_HEADID,VP_SWITCH,VP_ROTATION,VP_SPEED,VP_TRANSFORMATION)
				End If
			End If

	End Select 

	
End Function


Function WCNC_TCP_Offset_On(Kind)
Dim offz As Double 

	offz = ActT.ph_add.RotPointOffZ
	If Not equal(offz,0) Then

	    If (MT_Is_Vertical_StandardTool5Axis(ActT)) Or (MT_IsGearBoxTool(ActT) And MT_H_Is_5_Axis(ActT)) Then	
			If (MT_IsGearBoxTool(ActT) And MT_H_Is_5_Axis(ActT)) Then
				' MW 22.03.2016 Bei Winkelgetrieben auf 5Achs Bezug immer Kopf
				' d.h. nur bei Kind = -1 setzen
				If equal(Kind,-1) Then
					' Bezugspunkt Schnittpunkt Achsen
					' MW 21.01.2016 die folgenden Koordinaten beziehen sich immer auf die Plananlage der Spindel - Werkzeugbezugspunkt
					PPDLLSetAxisNames("","","Z=","","")
					PPDLLAxisOffsetsStr("","",IIf(offz>0,"+"+FToS(offz),ftos(offz)))
					'wcnc("G90 G92 X=0 Y=0 Z="+FToS(ActT.h.RotPointOffZ))
				End If
			Else
				If (equal(Kind,-1) Or equal(Kind,1)) Then
					' Bezugspunkt Schnittpunkt Achsen
					' MW 21.01.2016 die folgenden Koordinaten beziehen sich immer auf die Plananlage der Spindel - Werkzeugbezugspunkt
					PPDLLSetAxisNames("","","Z=","","")
					PPDLLAxisOffsetsStr("","",IIf(offz>0,"+"+FToS(offz),ftos(offz)))
					'wcnc("G90 G92 X=0 Y=0 Z="+FToS(ActT.h.RotPointOffZ))
				End If
			End If
		End If
	End If
	
End Function

Function WCNC_TCP_Offset_Off(Kind)
Dim offz As Double 

	offz = ActT.ph_add.RotPointOffZ
	If Not equal(offz,0) Then
	    If (MT_Is_Vertical_StandardTool5Axis(ActT)) Or (MT_IsGearBoxTool(ActT) And MT_H_Is_5_Axis(ActT)) Then	
			If (MT_IsGearBoxTool(ActT) And MT_H_Is_5_Axis(ActT)) Then
				' MW 22.03.2016 Bei Winkelgetrieben auf 5Achs Bezug immer Kopf
				' d.h. erst bei Kind =1 wieder abloeschen
				If equal(Kind,1) Then
					PPDLLSetAxisNames("","","","","")
					'wcnc("G90 G92 X=0 Y=0 Z=0")
				End If
			Else
				If equal(Kind,-1) Or equal(Kind,1) Then
					PPDLLSetAxisNames("","","","","")
					'wcnc("G90 G92 X=0 Y=0 Z=0")
				End If
			End If
		End If
	End If
End Function




Function WCNC_MSG(msg As String)
	
'	CC(SUB_MSG,msg)
'	WCNC_IDD(SUB_MSG,msg)
	WCNC("MSG ("+Chr(34)+msg+Chr(34)+ ")" )
	
End Function


Function WCNC_MSGOFF()
	' --  for ISG Controller
'	WCNC_IDD(SUB_MSGOFF)
	WCNC("MSG ("+Chr(34)+Chr(34)+ ")" )
End Function


Function WCNC_VAC_ON()
Dim VP_STOP As Integer
Dim VP_SETTING As Integer
Dim VP_FIELD As Integer
Dim VP_SEC_LINK_F1 As Integer
Dim VP_SEC_LINK_F2 As Integer
'Dim iic As ClampSituation

	VP_STOP = 0
	VP_SETTING = 1
	
	VP_SEC_LINK_F1 = 0
	VP_SEC_LINK_F2 = 0
	
'	NCData.NCClampSituations.ClampSituations.Add(iic)
'	Set iic = NCData.NCClampSituations.ClampSituations.GetItem_Index(0)
'	VP_SLink = iic.AdditionalInfo.GetAddition_ID(101).Value
	
	If equal(JobPara.Activ_Fields,1) Then
		VP_FIELD = 1
		If equal(Val(NCData.NCClampSituations.ClampSituations.GetItem_Index(0).AdditionalInfo.GetAddition_ID(100).Value),3) Then 
			VP_SEC_LINK_F1 = 1
		End If
	ElseIf equal(JobPara.Activ_Fields,2) Then
		VP_FIELD = 2
		If equal(Val(NCData.NCClampSituations.ClampSituations.GetItem_Index(0).AdditionalInfo.GetAddition_ID(101).Value),3) Then 
			VP_SEC_LINK_F2 = 2
		End If
	ElseIf equal(JobPara.Activ_Fields,3) Then
		VP_FIELD = 3
		If equal(Val(NCData.NCClampSituations.ClampSituations.GetItem_Index(0).AdditionalInfo.GetAddition_ID(100).Value),3) Then 
			VP_SEC_LINK_F1 = 1
		End If
		If equal(Val(NCData.NCClampSituations.ClampSituations.GetItem_Index(0).AdditionalInfo.GetAddition_ID(101).Value),3) Then 
			VP_SEC_LINK_F2 = 2
		End If
	Else 
		pp_err(50,JobPara.Activ_Fields)
	End If
	
	WCNC_SUB(SUB_VAC_ON,VP_STOP,VP_SETTING,VP_FIELD,VP_SEC_LINK_F1+VP_SEC_LINK_F2)
	
End Function
	

'Function wcnc_DustSuction(Pos)
'Dim VP_HEADID As Integer
'Dim VP_SETTING As Integer 
'Dim VP_POS As Double 
'Dim VP_VORPOS_X As Double
'Dim VP_VORPOS_Y As Double
'Dim VP_VORPOS_Z As Double

'mw todo
'VP_HEADID = ppara.hid
'	
'VP_SETTING = 0    ' zuruecklegen
'VP_POS = 0
'VP_VORPOS_X = 0
'VP_VORPOS_Y = 0
'VP_VORPOS_Z = 0
'
'	If Pos > 0 Then
'		VP_SETTING = 1
'		VP_POS = Pos
'	End If

'	If Not ActT.SetOf_DustPositions Is Nothing Then
'		If Not equal(Pos,Marker.Last_SuctionPos) Then
'			' Pos
'			' 0: Keine
'			' 1: dynamisch
'			' >1 : definierte Position -> dann muss Pos -1 gerechnet werden
'			'wcncAddCom(actt.SetOf_DustPositionsMFunc.GetString(IIf(Pos>1,Pos-1,Pos)),"DustSuction",True)
'			'WCNC_SUB(SUB_HOOD,VP_HEADID, VP_SETTING , VP_POS, VP_VORPOS_X,VP_VORPOS_Y, VP_VORPOS_Z)
'			' MW 12.02.2020
'			WCNC_SUB(SUB_HOOD, VP_SETTING , VP_POS)
'			Marker.Last_SuctionPos = Pos			
'		End If
'	End If
'	
'End Function



Function WCNC_PARK()
Dim VP_SETTING As Integer 
Dim VP_MANUAL_X As Double
Dim VP_MANUAL_Y As Double 
Dim VP_FUNKTION As Integer 
Dim VP_PLATZNUMMER As Integer

	VP_MANUAL_X = 0
	VP_MANUAL_Y = 0
	If (JobPara.park = 10) Then
		VP_MANUAL_X = JobPara.parkx 
		VP_MANUAL_Y = JobPara.parky
	End If
	VP_SETTING = Trans2Cycle(JobPara.park)  ' Nummerierung ist nicht 1:1 uebernommen worden
	VP_FUNKTION = 0
	VP_PLATZNUMMER = 0
	'JobPara.park,,JobPara.parky
	
	WCNC_SUB(SUB_PARK,VP_SETTING,VP_MANUAL_X,VP_MANUAL_Y,VP_FUNKTION,VP_PLATZNUMMER)
	
	
	' -- Bitschalter aus Workcenter auswerten
	 If Not MCDATA.Additions.GetAddition_ID(80000) Is Nothing Then
	 	JobPara.WorkC_OptionBit = Val(MCDATA.Additions.GetAddition_ID(80000).Value)
	 Else 
	 	AddMistake("Options Bits in pp.ini not set !")
	 End If
	 
	 wcncCom("Bitmode: "+FToS(JobPara.WorkC_OptionBit),True)
	 
End Function
	

Function WCNC_PRGSTART()
Dim BIT1 As Boolean
Dim BIT2 As Boolean
Dim BIT3 As Boolean 
Dim BIT4 As Boolean 
Dim BIT5 As Boolean 
Dim BIT6 As Boolean 
Dim BIT7 As Boolean 
Dim BIT8 As Boolean 

	'// Byte 1 fuer PRG_START

	BIT1 = IIf(is_WorkC_OptionBit(1,JobPara.WorkC_OptionBit),True,False)
	BIT2 = IIf(is_WorkC_OptionBit(2,JobPara.WorkC_OptionBit),True,False)
	BIT3 = IIf(is_WorkC_OptionBit(3,JobPara.WorkC_OptionBit),True,False)
	BIT4 = IIf(is_WorkC_OptionBit(4,JobPara.WorkC_OptionBit),True,False)
	BIT5 = IIf(is_WorkC_OptionBit(5,JobPara.WorkC_OptionBit),True,False)
	BIT6 = IIf(is_WorkC_OptionBit(6,JobPara.WorkC_OptionBit),True,False)
	BIT7 = IIf(is_WorkC_OptionBit(7,JobPara.WorkC_OptionBit),True,False)
	BIT8 = IIf(is_WorkC_OptionBit(8,JobPara.WorkC_OptionBit),True,False)
	If (BIT8) Then
		WCNC_SUB(SUB_PRG_START,BIT1,BIT2,BIT3,BIT4,BIT5,BIT6,BIT7,BIT8)
	ElseIf (BIT7) Then
		WCNC_SUB(SUB_PRG_START,BIT1,BIT2,BIT3,BIT4,BIT5,BIT6,BIT7)
	ElseIf (BIT6) Then
		WCNC_SUB(SUB_PRG_START,BIT1,BIT2,BIT3,BIT4,BIT5,BIT6)
	ElseIf (BIT5) Then
		WCNC_SUB(SUB_PRG_START,BIT1,BIT2,BIT3,BIT4,BIT5)
	ElseIf (BIT4) Then
		WCNC_SUB(SUB_PRG_START,BIT1,BIT2,BIT3,BIT4)
	ElseIf (BIT3) Then
		WCNC_SUB(SUB_PRG_START,BIT1,BIT2,BIT3)
	Else
		WCNC_SUB(SUB_PRG_START,BIT1,BIT2)
	End If
	
End Function

Function WCNC_PRGEND()
Dim VP_SETTING As Integer 
Dim i As Integer 
Dim erg As Long
	erg = 0 
	For i = 9 To 17 Step 1
		If is_WorkC_OptionBit(i,JobPara.WorkC_OptionBit) Then
			erg = erg + exponent2(i-8)
		End If


	Next i
'	If (erg = JobPara.WorkC_OptionBit) Then
		WCNC_SUB(SUB_EndProg,erg)
'	Else
'		pp_err(0,"workcenter optionsbits")
'	End If
	
		
	

End Function


Function Trans2Cycle(OrgPark) As Integer ' Nummerierung ist nicht 1:1 uebernommen worden
Dim NewPark As Integer
	NewPark = OrgPark
    Select Case (OrgPark)
		Case 0
			NewPark = 0
		Case 1
			NewPark = 2
		Case 2
			NewPark = 5
		Case 3
			NewPark = 8
		Case 4
			NewPark = 1
		Case 5
			NewPark = 4
		Case 6
			NewPark = 7
		Case 7
			NewPark = 3
		Case 8
			NewPark = 6
		Case 9
			NewPark = 9
		Case 10
			NewPark = 10
		Case 11
			NewPark = 11
		Case 12
			NewPark = 12
		
	End Select
	Trans2Cycle	= NewPark
	
End Function
