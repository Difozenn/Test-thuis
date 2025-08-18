' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \hh7\pp_siemens.bas
' -- 
' -----------------------------------------
'#uses "pp_math.bas"

Option Explicit

Global Const SIEMENS_OffPX = "OOX"
Global Const SIEMENS_OffPY = "OOY"
Global Const SIEMENS_OffPZ = "OOZ"

Global Const SIEMENS_PARKXVAR = "PX"
Global Const SIEMENS_PARKYVAR = "PY"

Global Const SIEMENS_TCARR = "TCARR=1"
Global Const SIEMENS_TCARROFF = "TCARR=0"


Global Const SIEMENS_MAX_LIMIT_ZPLUS="MAXZ"
Global Const SIEMENS_MAX_LIMIT_Z2PLUS="MAXZ2"
Global Const SIEMENS_MAX_LIMIT_Z3PLUS="MAXZ3"
Global Const SIEMENS_MAX_LIMIT_XPLUS="MAXX"
Global Const SIEMENS_MAX_LIMIT_XMINUS="MINX"
Global Const SIEMENS_MAX_LIMIT_YPLUS="MAXY"
Global Const SIEMENS_MAX_LIMIT_YMINUS="MINY"

Global Const SIEMENS_DCORRECTIONMARKER="DCMARKER"

Global Const SIEMENS_LIFTOFFSETX = "LIFTOX"
Global Const SIEMENS_LIFTOFFSETY = "LIFTOY"
Global Const SIEMENS_LIFTOFFSETZ = "LIFTOZ"

Global Const SIEMENS_MGUD_LASERA= "LP_MODE_A"
Global Const SIEMENS_MGUD_LASERB= "LP_MODE_D"


Function SIEMENS_init_NCVARNames

	g_OffPX=SIEMENS_OffPX
	g_OffPY=SIEMENS_OffPY
	g_OffPZ=SIEMENS_OffPZ
	
	g_PARKXVAR=SIEMENS_PARKXVAR
	g_PARKYVAR=SIEMENS_PARKYVAR
	
	g_TCARR=SIEMENS_TCARR
	g_TCARROFF=SIEMENS_TCARROFF
	
    g_MAX_LIMIT_ZPLUS=SIEMENS_MAX_LIMIT_ZPLUS
	g_MAX_LIMIT_Z2PLUS=SIEMENS_MAX_LIMIT_Z2PLUS
	g_MAX_LIMIT_Z3PLUS=SIEMENS_MAX_LIMIT_Z3PLUS
	g_MAX_LIMIT_XPLUS=SIEMENS_MAX_LIMIT_XPLUS
	g_MAX_LIMIT_XMINUS=SIEMENS_MAX_LIMIT_XMINUS
	g_MAX_LIMIT_YPLUS=SIEMENS_MAX_LIMIT_YPLUS
	g_MAX_LIMIT_YMINUS=SIEMENS_MAX_LIMIT_YMINUS
	g_DCORRECTIONMARKER=SIEMENS_DCORRECTIONMARKER
	g_LIFTOFFSETX = SIEMENS_LIFTOFFSETX
	g_LIFTOFFSETY = SIEMENS_LIFTOFFSETY
	g_LIFTOFFSETZ = SIEMENS_LIFTOFFSETZ
	
	
End Function



Function WCNC_START_DEF_SIEMENS

	wcnc("DEF REAL LAENGE= "+FToS(FinishedPart.X))
	wcnc("DEF REAL BREITE= "+FToS(FinishedPart.Y))
	wcnc("DEF REAL DICKE= "+FToS(FinishedPart.Z))
	wcncAddCom("DEF REAL "+g_OffPX+"=0","Output offset X")
	wcncAddCom("DEF REAL "+g_OffPY+"=0","Output offset Y")
	wcncAddCom("DEF REAL "+g_OffPZ+"=0","Output offset Z")
	
	wcnc("DEF REAL "+g_MAX_LIMIT_ZPLUS+"=0")
	
	If FiveAxis.Yes And Not FiveAxis.isg Then
		wcnc("DEF REAL "+g_MAX_LIMIT_Z3PLUS+"=0")
	End If

	wcnc("DEF REAL "+g_MAX_LIMIT_XPLUS+"=0")
	wcnc("DEF REAL "+g_MAX_LIMIT_XMINUS+"=0")
	wcnc("DEF REAL "+g_MAX_LIMIT_YPLUS+"=0")
	wcnc("DEF REAL "+g_MAX_LIMIT_YMINUS+"=0")
	
	wcnc("DEF REAL "+g_PARKXVAR+"=0")
	wcnc("DEF REAL "+g_PARKYVAR+"=0")

	wcnc("DEF INT "+g_DCORRECTIONMARKER+"=0")

	wcnc("DEF REAL "+g_LIFTOFFSETX+"=0")
	wcnc("DEF REAL "+g_LIFTOFFSETY+"=0")
	wcnc("DEF REAL "+g_LIFTOFFSETZ+"=0")
	
	
	wcnc(g_MAX_LIMIT_ZPLUS+"=$MA_POS_LIMIT_PLUS[Z1]-1")
	If FiveAxis.Yes And Not FiveAxis.isg Then
		wcnc(g_MAX_LIMIT_Z3PLUS+"=$MA_POS_LIMIT_PLUS[Z3]-20")
	End If

	wcnc(g_MAX_LIMIT_XPLUS+"=$MA_POS_LIMIT_PLUS[X]-1")
	wcnc(g_MAX_LIMIT_XMINUS+"=$MA_POS_LIMIT_MINUS[X]+1")
	wcnc(g_MAX_LIMIT_YPLUS+"=$MA_POS_LIMIT_PLUS[Y]-1")
	wcnc(g_MAX_LIMIT_YMINUS+"=$MA_POS_LIMIT_MINUS[Y]+1")


End Function


Function WCNC_START_DEF_SIEMENS_EXT2
	
		
	SET_Zero(WPI(0).WPName,JobPara.NPX,JobPara.NPY,JobPara.NPZ,0,0,0)
	
	' --------------------------------------
	' Konturgenauigkeit einstellen
	wcnc("$SC_MINFEED="+FToS(mPara_Add.sc_minfeed))
	wcnc("$SC_CONTPREC="+FToS(mPara_Add.sc_contprec))
	' --------------------------------------

End Function


Function WCNC_SIEMENS_STOPRE
	wcnc("STOPRE")
End Function


Function WCNC_SIEMENS_TRANSOFF
	wcnc("TRANS")
End Function

Function WCNC_SIEMENS_TRANSON(x,y,z,ox,oy,oz)
	wcnc("TRANS"+XEqualToS(x)+"+"+ox+ _
	              YEqualToS(y)+"+"+oy+ _
                  ZEqualToS(z)+"+"+oz)
End Function


Function WCNC_SIEMENS_ATRANS_AROT(ipx,ipy,ipz,rota,tipa)
	wcnc("ATRANS"+XEqualToS(ipx)+"+"+g_OffPX+ _
	              YEqualToS(ipy)+"+"+g_OffPY+ _
	              ZEqualToS(ipz)+"+"+g_OffPZ)
	              
	wcnc("AROT"+ZToS(rota)+XToS(tipa))
End Function

Function WCNC_SIEMENS_ATRANS_AROT_DH(ipx,ipy,ipz,rota,tipa,ox,oy,oz)

	wcnc("ATRANS"+XEqualToS(ipx)+Get_Val_Signed(ox)+YEqualToS(ipy)+Get_Val_Signed(oy)+ _
	              ZEqualToS(ipz)+Get_Val_Signed(oz))
	wcnc("AROT"+ZToS(rota)+XToS(tipa))

End Function

Function WCNC_SIEMENS_SUPAZ
	wcnc("SUPA G0 Z="+g_MAX_LIMIT_ZPLUS)
End Function

Function WCNC_SIEMENS_SUPAZ5AXIS
	wcnc("SUPA G0 Z="+g_MAX_LIMIT_ZPLUS +" Z3="+g_MAX_LIMIT_Z3PLUS)
End Function

Function WCNC_SIEMENS_G602

	wcnc("G602")
	
End Function

Function WCNC_SIEMENS_BRISK

	wcnc("BRISK")
	
End Function

Function WCNC_SIEMENS_SOFT

	wcnc("SOFT")
	
End Function

Function WCNC_SIEMENS_G64G17SOFT

	WCNC("G64 G17 SOFT")
	
End Function

Function WCNC_SIEMENS_G500
	wcnc("G500")
End Function

Function WCNC_SIEMENS_G500G90D0
	wcnc("G500 G90 D0")
End Function

Function WCNC_SIEMENS_G90D0
	wcnc("G90 D0")
End Function

Function WCNC_SIEMENS_CUT2DF
	wcnc("CUT2DF")
End Function

Function WCNC_SIEMENS_CFIN
	wcnc("CFIN")
End Function


Function W______CNC_SIEMENS_TCarr(v1,v2)
		wcnc(g_TCARR+" T"+inttos(v1)+" D"+inttos(v2))
End Function


Function WCNC_SIEMENS_OFFN(v1,v2)
	wcnc("OFFN="+FToS(v1-v2))
End Function
	

Function WCNC_SIEMENS_SZENE(v1,v2,v3,v4)
	
	wcnc(SPF_Szene+"("+ftos(v1)+",-1,,"+ftos(v4)+")")
	
End Function

Function WCNC_SIEMENS_IFLASERA
	wcnc("IF "+SIEMENS_MGUD_LASERA+"==1")
End Function

Function WCNC_SIEMENS_IFLASERB
	wcnc("IF "+SIEMENS_MGUD_LASERB+"==1")
End Function

Function WCNC_SIEMENS_SPF_LASERONOFF(HID,TP,OnOff)
	   wcnc(SPF_LASERONOFF+"("+IntToS(HID)+","+IntToS(TP)+","+IntToS(OnOff)+")")
End Function


Function WCNC_SIEMENS_EXTCALL(v1)
	wcnc("EXTCALL """+v1+"""")
End Function

Function WCNC_SIEMENS_G04(v1)

	WCNC("G04 F"+ftos(v1))
	
End Function

Function WCNC_SIEMENS_MSG(v1,v2)

	WCNC("MSG ("+Chr(34)+v1+Chr(34)+v2 + ")" )
	
End Function


Function WCNC_SIEMENS_MSGOFF

	WCNC("MSG ("+Chr(34)+Chr(34)+ ")" )
	
End Function

Function WCNC_SIEMENS_TCARROFF(v1,v2)
	WCNC(g_TCARROFF+" T"+IntToS(v1)+" D"+IntToS(v2))
End Function

Function WCNC_SIEMENS_REQUEST_FLEX(HeadID,ID,TipAngle,Rota)

	WCNC(SPF_REQUEST_FLEX+"("+Inttos(HeadID)+","+inttos(ID)+","+ftos(TipAngle)+","+ftos(Rota)+")")
	
End Function
	
Function WCNC_SIEMENS_PREINFO(H_Id,TC_Id,TC_PlaceNo,ID,XPos)

	WCNC(SPF_PREINFO+"("+IntToS(H_Id)+","+IntToS(TC_Id)+","+IntToS(TC_PlaceNo)+","+IntToS(ID)+","+fToS(XPos)+")")
	
End Function
						
		
Function WCNC_SIEMENS_ATRANSZ(v1)
		
	WCNC("ATRANS Z="+ftos(v1))
	
End Function
		
Function WCNC_SIEMENS_TCARR_ACTIVATE(T,D)

	wcnc(g_TCARR + " T"+IntToS(T)+" D"+IntToS(D))
	
End Function

' -- Neu AK 06.10.2009  
' -- Konturstart/ end auch bei Siemens

Function WCNC_SIEMENS_CONTOUR_START(Optional para1,Optional para2,Optional para3)

	wcnc(SPF_CONTOUR_START + "(" + para1 +"," + para2 +","  + para3    +")")
	
End Function


Function WCNC_SIEMENS_CONTOUR_END(Optional para1)
		wcnc(SPF_CONTOUR_END + "(" + para1 + ")")
	End Function
	
Function WCNC_SIEMENS_KINEMATIK(s)
	wcnc(s)
End Function
