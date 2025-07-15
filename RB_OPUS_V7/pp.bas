' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \RB_OH_OPUS_V7\pp.bas
' -- 
' -----------------------------------------
' -- 
' -- Reichenbacher - ISG / BECKHOFF Postprocessors V7 (mw) --
' -- 
' -----------------------------------------
'#uses "pp_7.bas"
'#uses "pp_mt.bas"
'#uses "pp_mtf.bas"
'#uses "pp_global.bas"
'#uses "pp_bohrdh.bas"
'#uses "pp_ncinfo.bas"
'#uses "pp_math.bas"
'#uses "pp_table.bas"
'#uses "pp_version.bas"
'#uses "pp_isg.bas"



Option Explicit


Sub InitZero
Dim path As Variant
Dim f_source As Integer

Dim Controller As String 

Dim i As Integer
Dim PH As IIProcessHead 
Dim SA

	JobPara.TimerFullSecs = Timer

	ReDim Preserve LogArr(1) 
	ReDim WPI(1)	 ' MW 11.02.2016 - damit im Fehlerfall beim Init (vor dem WorkpieceInfo) nicht auf leeres Array laeuft!


	INITZero_7  

	' -- Bitschalter aus Workcenter auswerten
	 If Not MCDATA.Additions.GetAddition_ID(80000) Is Nothing Then
	 	JobPara.WorkC_OptionBit = Val(MCDATA.Additions.GetAddition_ID(80000).Value)
	 Else 
	 	AddMistake("Options Bits in pp.ini not set !")
	 End If
	
    
    JobPara.ActScene=1
	
	' Pruefung 5-Achs, ob Anfahren ohne direkt in Z ID -20002
	For i = 0 To TDATA.MachineData.ProcessHeadsCount - 1 
	
		Set PH = TDATA.MachineData.GetProcessHead_Index(i)
		
		
		If Not PH Is Nothing Then
			If (PH.RotType = atFree) And (PH.TipType = atFree) Then
		    	' -5Achs Drehachse frei + Kippachse frei
		    	' PP;SIMU Additions
				Set SA = NCData.GetExtInfo(ekHead_SimuAdditions,PH)
				If Not SA.GetAddition_ID(-20002) Is Nothing Then
					If Val(SA.GetAddition_ID(-20002).Value) > 0 Then
						pp_err(17,PH.Description,-20002)
					End If
				End If
		    End If
		End If
		Set PH=Nothing
		Set SA=Nothing
	Next i
	  	

	JobPara.lstp = 10
End Sub


Sub StartLeadOut
	Call StartLeadOut_7
End Sub

Sub EndLeadIn
	Call EndLeadIn_7
End Sub


Sub Park (Index)
	Call Park_7 (Index)
End Sub


Sub NCIExt (Kind,NCType,Index)
Dim Group As Variant
Dim PostName As Variant 
	Group = NCData.NCIExtList.GetNCI_Index(Index).NCIExt.Group
	PostName = PostSettings.PPName
	
	'  4 Zeichen gleich ? "RB_OH" = "RB_OH   _V7" = TRUE
	If (Left(UCase(Group),4) = Left(UCase(PostName),4)) Or (Left(UCase(Group),5) = ("RH_QT")) Or (Left(UCase(Group),5) = ("RB_QT")) Or (Left(UCase(Group),5) = ("RB_OH")) Or (Left(UCase(Group),5) = ("RH_OH")) Then
		' Fuer diesen Post festgelegter NCINFO
'		If equal(NCType,91200) Then
'			' Alle NCIExt PP [OEM] zur freien Verwendung seitens Reichenbacher
'			Call Handle_NCI_Ext_7_OEM (Kind,NCType,Index)
'		Else
			Call Handle_NCI_Ext_7 (Kind,NCType,Index)
'		End If
		
	' System - NCI
	ElseIf equal(NCType,-100200) Then
		' NCZeile direkt
		Call Handle_NCI_Ext_7 (Kind,NCType,Index)
	ElseIf equal(NCType,-100058) Then
		' hor.Bohren mit Rueckzug ueber Platte
		If equal(NCData.NCInfo_Global.GetNCI_Index(Index).Para1,1) Then
			Marker.HorDH_PullBack = True
		Else
			Marker.HorDH_PullBack = False
		End If
	Else
		AddHint("NCIExt Group ["+(Group)+ "] NCType #"+inttos(NCType)+" not interpreted from this Post ["+UCase(PostName)+"] TDATA ["+TDATA.ActMachineName+"]" )
	End If
End Sub

Sub MachineStop(Index, NextBoxNoWorking, HeadID)
	Call Machine_Stopp_7 (Index, NextBoxNoWorking, HeadID)
End Sub

Sub SuctionHood(Index)
	Call SuctionHood_7 (Index)
End Sub


Sub ClampChangeExt(Situa1,Situa2,Index)
Dim par1,par2,par3,par4,par5,par6,par7,par8,par9,par10,par11,par12 As Variant 
	
	par1 = Situa1
	par2 = Situa2
	
	Call Handle_ClampChangeExt_7 (Index,par3,par4,par5,par6,par7,par8,par9,par10,par11,par12)
	
	
	' Aufruf alte ClampChange Sub
	Call ClampChange(par1,par2,par3,par4,par5,par6,par7,par8,par9,par10,par11,par12)
	
End Sub
	
Sub AdditionalSPInfo(d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,s1,s2,s3,s4,s5)

End Sub


Sub SetDrillingZMax(DZMax1,DZMax2,DZMax3,DZMax4,DZMax5,DZMax6,DZMax7,DZMax8,DZMax9)
  DZMax01=DZMax1
  DZMax02=DZMax2
  DZMax03=DZMax3
  DZMax04=DZMax4
  DZMax05=DZMax5
  DZMax06=DZMax6
  DZMax07=DZMax7
  DZMax08=DZMax8
  DZMax09=DZMax9	
	
End Sub

Sub Init(NCPath)

	If Not PostSettings.GeneralSettings.WriteInitZero Then
		pp_err(5,"WriteInitZero")
	End If
	
	WritingNCData = True	
	
	AddLog("needed Time for collection Tool and HeadInfos: "+ftos(Timer-JobPara.TimerInitTL)+" sec")
	
	
	
	'Initializing global variables
	ncpathGlobal=NCPath
	NCLine=10
	Firsttime_Viewchange=True
	
	Set ActT.t = Nothing
	Set LastT.t = Nothing
	
	
	Z_Is_Safety=False
	Z_Is_SafetyPart=False
	'  DistanceToOutLineValue=0
	FloatFormat="0.000"
	
'	Init_Marker  ' MW 27.02.2020
	
'	init_NCVARNames
	
	SetDrillingZMax -5,-10,-15,-20,-25,-30,-35,-40,-45
	
		
End Sub

Sub FirstTool(BoxNo,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15,d16,d17,d18,d19,d20,d21,d22,d23,d24,d25,d26,d27,d28)
Dim Obj
Dim HeadInfo As Variant
Dim Head As Long 


	'AK 21.09.2011 naechste XPosition im ToolChangezyklus mitgeben
	' d18 = AddMx = Werkzeug - Aggregatverschiebung X
	' d33 = SPVX = Anfahrposition auf die Ebene
	'Marker.XPosAfterToolChange=(-1*d18)+d33

	Marker.FirstTool_PosX = d25   ' MW 21.12.2015
	
	Set Obj = NCData.ProcessList.GetProcess_NCInfoIndex(0)
	If Not Obj Is Nothing Then
		HeadInfo = Obj.HeadInfo
		If IsNumeric(HeadInfo) Then
			Head = Val(HeadInfo) 
		Else
			pp_err(126,"HeadInfo")
		End If
		MT_SetTHopsBasicToolExt(FirstT,BoxNo,Head)
	End If
	Set Obj = Nothing
	
	
'old MW 31.03.2016	MT_SetTHopsBasicToolExt(FirstT,BoxNo,Hid)
	


End Sub

Sub NC_Start(NCName,NCExt,TDB,FX,FY,FZ,Comment,Add_X,Add_Y,Add_Z)

    NCNameGlobal=NCName
   	JobPara.NPX=Add_X   ' G54 Nullpunkt X
   	JobPara.NPY=Add_Y   ' G54 Nullpunkt Y
   	JobPara.NPZ=Add_Z   ' G54 Nullpunkt Z
    
	SetNCName(NCName,NCExt,ncpathGlobal)
    NCFileNo = File_Open(NCName+NCExt)
    Call SaveFinishedPart(FX,FY,FZ)
    
	wcncCom("FinishedPart: X: "+FToS(FX)+" Y: "+FToS(FY)+" Z: "+FToS(FZ))
	wcncCom("TData:"+TDB)
	

	wcncCom("created:"+Str$(Date)+" - "+Str$(Time)+" - DiREKT CNC-Systeme GmbH",True)

	wcncCom("MT:"+TDATA.ActMachineName,True)
	wcncCom("Post:"+TDATA.MachineData.MachineParameter.PostProzessor+" V"+DLLVersion+" Script"+SCRIPT_VERSION,True)
	wcncCom("",True)
	wcncCom("Total Processes[#"+IntToS(NCData.ProcessList.Count)+"]",True)
	wcncCom("",True)
	
	
	WCNC_START_DEFVARS
	

	If (Marker.CountOfTool > 0) Then    ' MW 28.02.2020 DINISO - bringt kein Werkzeug mit
		WCNC_Write_TCheck()    ' MW 14.02.2020
	End If
	

	WCNC_Initial_Table_Positions() ' wcncMachineComponentData(0)   ' Traversen-/Saugerdaten absetzen 
	
	'// Byte 1 fuer PRG_START
	WCNC_PRGSTART()

'MW 12.02.2020	WCNC_SUB(SUB_PRG_WAIT,0,0,0,0,0)

	WCNC_SUB(SUB_CH_START_PROCESSING) 
	
'	WCNC_SUB("G500 G90 D0")
	WCNC_SUB("CUT2DF")
	WCNC_SUB("CFIN")

	wSafetyAbs(False)
	
'	WCNC_IDD("G153 G0 D0 Z="+MAX_LIMIT_ZPLUS)
'	WCNC_IDD("STOPRE")
	

	WCNC_SUB("G64G17SOFT")
	
	
	WCNC_SET_Zero(TDATA.MachineData.OffsetX+JobPara.NPX,TDATA.MachineData.OffsetY+JobPara.NPY,TDATA.MachineData.OffsetZ+JobPara.NPZ)
	
	
	WCNC_VAC_ON
	
	WCNC_EXTCALL_DINISO()

	PPara.SubProcessNo = 0


End Sub


Sub ToolChange(BoxNo,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,pspeed,d12,d13,d14,d15,d16,d17,d18,d19,d20,d21,d22,d23)

	If (BoxNo > 0) And (Not equal(PPara.Speed,pspeed)) Then
		pp_err(126,"PSpeed")
	End If
	If (BoxNo > 0) And (Not equal(PPara.ToolID,BoxNo)) Then
		' Processpara check auf Boxno
		pp_err(126)
	End If

	Reset_FirstTime_Viewchange
	

	' letztes benutztes Werkzeug auf Lastt schreiben
	If Not ActT.t Is Nothing Then
	
		Set_LastTool_ActTool
	
	Else
		If Not LastT.t Is Nothing Then
			Set LastT.t = Nothing
		End If
	End If

	' Muss vor der Werkzeugabwahl stehen, damit Werkzeugabwahl weiss, dass z.B. Spindel ausgeschaltet werden muss
	If BoxNo > 0 Then
		MT_SetTHopsBasicToolExt(ActT,BoxNo,PPara.HId)
	End If
	
	If BoxNo<0 Then
		' nur abwahl am Schluss
		pp_err(0,CallersLine)
		Exit Sub
	End If
	
	If MT_isDH_wasDH(ActT,LastT) Then
		' war ist Bohrkopf nicht hochfahren
		' und keine WEchsel von Bohrkopf Saegen auf Bohrkopf bohren 
	Else
	
		If Not MT_GB_Output_Changed(ActT,lastT) And Not MT_TEdgeChange(ActT,lastT) Then
	
			Z_Is_Safety=False
			wSafetyAbs(Z_Is_Safety)
			' Neu MW 07.07.2005 - dann ist auch Sicherheit uebers 
			' Werkstueck gewaehrleistet, -> Problem durch Toolchange wird auch 
			' der ToolCarr zurueckgesetzt
			Z_Is_SafetyPart=True
		Else
				
			' -- Wechsel von einem Winkelgetriebeausgang auf den naechsten Winkelgetriebeausgang
			' -- Achtung wenn Maschinenstop zwischen dem Ausgangswechsel wird TCARR abgewaehlt, dann 
			' -- geht hier Sicherheitsfahrt uebers Werkstueck schief.. MW 3.12.2008
			If Marker.MachineStopActive=False Then
				'wSafetyPart(actt)
			Else
				Marker.MachineStopActive=False
			End If
		End If
		ResetActV	
	End If
	
	Marker.Last_Bm.BM1 =0
	Marker.Last_Bm.BM2 =0
	Marker.Last_Bm.BM3 =0
	Marker.last_bm.GroupCode=0
	
	If isDINISO_Process	Then
		'If (Marker.DINISO_Process) And (equal(Marker.DINISO_TC,0) ) Then
		If IsDINISO_No_TC Then  ' MW 30.03.2016
			' ---------------------------------------------------------
			' -- DINISO-Programm ohne Werkzeugaufruf
		 	Exit Sub
		End If
	End If

	WCNC_Write_Speed()
	
	If BoxNo<0 Then
		' nur abwahl am Schluss
		pp_err(1,CallersLine)
		Exit Sub
	End If


End Sub    ' ToolChange


Sub ToolChangeBefore(BoxNo,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15,d16,d17,d18,d19,d20,d21,d22,d23,d24,d25,d26,d27,d28)
End Sub

Sub ViewInfoToolChange(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPVX,SPVY,SPVZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz,dummy1,dummy2,dummy3,dummy4,dummy5,dummy6,dummy7,dummy8,dummy9,dummy10)
End Sub

Sub ViewChange(View,LastView,IPX,IPY,IPZ,RotA#,TipA#,SPAX,SPAY,SPAZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)

Dim ox As Double
Dim oy As Double
Dim oz As Double   ' Spezial -> fuer pneum. schwenkbare Saege kann Feinjustierung ueber Offsets (Id's im Ausgang) getaetigt werden
Dim oxv As Variant 
Dim oyv As Variant 
Dim ozv As Variant 


	wcnccom("ViewChange - AGGOX:"+ftos(ActT.t.MoveX)+"  AGGOY:"+ftos(ActT.t.MoveY)+"  AGGOZ:"+ftos(ActT.t.MoveZ),True)
	
	MT_Write_Activate_Tool(PPara.ActT,True)
	
'	If mPara_Add.WriteWorkTypeInfo Then
		WCNC_SUB(SUB_Dynamic,GetObjectTypNo(NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1)))
'	End If

	ox=0 
	oy=0
	oz=0
	
	If (isDINISO_Process) Then
		If (IsDINISO_No_VC) Then
			'If (Marker.DINISO_Process) And (Marker.DINISO_VC<>1) Then
			' ---------------------------------------------------------
			' -- DINISO-Programm ohne Ebenenwechsel dann hier Liftinfo absetzen
			If Not (IsDINISO_No_TC) Then
				'If Not equal(Marker.DINISO_TC,0) Then
				' NEu MW 27.03.2006 - wenn kein Werkzeugaufruf dann auch kein 
				' T- Nummern - aufruf
		    	'MT_Write_Act_T_Correction
		    	'MT_Write_Act_D_Correction
		    End If
			Exit Sub
		Else
			' MW 04.05.2017 - Aggregatsversatz wie bisher verrechnen
			If MT_Is_Vertical_StandardTool5Axis(ActT) Then
				ox = -ActT.h.CenterX
				oy = -ActT.h.CenterY
				oz = -ActT.h.CenterZ
			Else
				pp_err(0,"wrong Tool DINISO-CALL")
			End If
			
		End If
		
	End If

	wcnc_Workpiece_Info

	LastV=ActV
	
	Call ViewSave(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPAX,SPAY,SPAZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
	
	PosReset
	
   	If MT_isDH(ActT) Then
	   Marker.Last_DH_Process=""
   	   DH_View0= ActV
   	   Exit Sub
	End If
   	
	wcncCom("Viewchange View "+View)
	
	If PostSettings.GeneralSettings.RelativToRefSpindle Then
		If mt_isdhsaw(PPara.ActT) Then
			' Bohrkopfsäge
			MT_GetOffsets_DHSaw(PPara.ActT,ox,oy,oz)
		ElseIf MT_Is_MFE_Vertical(PPara.ActT) Then
			' MW 28.06.2018 360Grad MFE
			' hor. Offset Aggregatsausgang verrechnen
			PPara.ActT.t_gb.Get_OffsetToolRefPoint(PPara.View.RotA,PPara.View.TipA,oxv,oyv,ozv)			
			ox=oxv
			oy=oyv
			oz=ozv
			If ActT.t_gb.Tool.ToolType=tSaw Then
				' Get_OffsetToolRefPoint verrechnet auch SBB 
	    		If Equal(PPara.View.TipA,90) Then
	    			GetDX_DY_DZMitKippW_Laenge(PPara.View.TipA,PPara.View.RotA,(PPara.ActT.T.SawThickness/2) , oxv,oyv,ozv)
	    			ox = ox + oxv
	    			oy = oy + oyv
	    		Else
	    			pp_err(0,"MFE wronggTipAngle")
	    		End If
	    	End If
		End If
		
		wcnc(ISG_OffPX+"="+FToS(ox)+ " "+ISG_OffPY+"="+FToS(oy)+ " "+ISG_OffPZ+"="+FToS(oz))
	Else
		pp_err(0,"wrong settings")
		' ??????????? eigentlich Quatsch
		'MT_Write_Offset_NC_Vars(ZOffGes)' Offsets auf OOX, OOY, OOZ schreiben OOX=-207.39 OOY=-112.35 OOZ=-50
									' without rotating output - offset
	End If

	WCNC_SUB(SUB_TRANSOFF)
	' ???	MT_Write_CPLift(Marker.LiftPos_StartUp)
	
	'wcncCom("INFO - IM IPZ wird beim vertikalen Fraesen der Offset Z vom Aggregat eingerechnet",True)
	
	' MW 21.01.2016 - TCP vor CS Ebene
	If MT_Is_Vertical_StandardTool5Axis(ActT) Then
		' 5-Axis 
		WCNC_SUB(SUB_TCP_ON)   ' (actt.ph_add.traorion)
		WCNC_SUB("STOPRE")
		wcnc("G"+IntToS(53+Fix_Zero))
	End If

	wcnc_Haube5A(PPara.sHood.pos)

	WCNC_SUB("ATRANSAROT",IPX,IPY,IPZ,RotA,TipA)
		   	

	wcncCom("ViewchangeEnd")
	'If ActV.View<>0 Then
		Z_Is_Safety=False
	'End If
	Firsttime_Viewchange = False
	Z_Is_SafetyPart=False

	If (ppara.SubProcessNo > 1) Then
		If (pparalast.actt.t.ID = ppara.actt.t.ID) Then 
			WCNC_Write_Speed()  
		End If
	End If
	
	
	WCNC_SUB(SUB_BLOWING)
End Sub   ' ViewChange

Sub DistanceToOutLine(Value)
	If Not equal(Value,0) Then
		pp_err(0,"Distance to outline <>0")
	End If
'    If (Mill_C.activ) And  (MT_Is_Vertical_StandardTool5Axis(actt)) Then
'    	Mill_C.offn=Value
'	  	DistanceToOutLineValue=0
'    Else
'	  	DistanceToOutLineValue=Value
'  	End If
End Sub



Sub Start_Milling(PNo,TRC,StartMove,StartFactor,I_F,F,S_F,S,PPVX,PPVY,PPVZ,PPAX,PPAY,PPAZ,RotA,TipA,TAngle,Start_End_MoveReady)


	If MT_isdhsaw(ActT) Then
		' ----------------------------------------------------
		' -- hier Bohrspindeln/Saege vorlegen
		' -- Bohrkopf - Saege
		' ----------------------------------------------------
		WCNC_WRITE_DHCode(ActT.t_dhsaw.DH_ToolPlace.ToolNo,false)
	End If

	PosReset
	MoveParaReset
	
	' Neu MW 21.11.2005
	If MT_Is_UndersideTool(ActT) Then
		wcncCom("****** Unterflurfraesen ****")
		pp_err(3)
		' --
		' -- Unterflur-Getriebe
		' Berechnung der Ebenenausrichtung anhand von Tangle und der aktuell eingestellten Ebene
		' --
		MT_Underside_Set_Param_Angle(ActT,TAngle)
		' --
		' --
        ' MW 03.04.2014 erst hier ist bekannt von welcher Richtung das Aggregat kommt, und somit kann auch der Offset gerechnet werden
'		Call wcncViewChange_GB(ActV.View,ActV.LastView,ActV.IPX,ActV.IPY,ActV.IPZ,ActV.RotA,ActV.TipA,ActV.SPVX,ActV.SPVY,ActV.SPVZ,ActV.Vxx,ActV.Vxy,ActV.Vxz,ActV.Vyx,ActV.Vyy,ActV.Vyz,ActV.Vzx,ActV.Vzy,ActV.Vzz)
		
		' Korrektur aufrufen, und offsets setzen
		'MT_Write_Call_Correction
		' mit C-Achse
'		wcnc(G0+Move(PPVX,PPVY,PPVZ,MovePara.Feedrate,TRC)+GetHeadAngles_GB(UndersideTool.dw)+MT_Write_DustCover(PPAZ))
	Else
		' Standard
		wcncCom("--")
		wcncCom("--      Milling ")
		wcncCom("--")
		
		' MW 14.01.2015 -> kommt von pp-engine
		'wcncaddcom(G0+Move(PPVX,PPVY,PPVZ,MovePara.Feedrate,TRC)+MT_Write_DustCover(PPAZ),"Startmilling",True)
		
	End If
	'Marker.StartMoveActiv = True
End Sub

Sub G00(PPVX,PPVY,PPVZ,PPAX,PPAY,PPAZ,Feedrate,Speed,RotA,TipA,TRC,TAngle)
	If PostSettings.GeneralSettings.CalcHeadMoves Then
		pp_err(0,"G00")
	End If

End Sub

Sub G01(PPVX,PPVY,PPVZ,PPAX,PPAY,PPAZ,Feedrate,speed,RotA,TipA,TRC,TAngle)
	If PostSettings.GeneralSettings.CalcHeadMoves Then
		pp_err(0,"G01")
	End If

End Sub

Sub G02(PPVX,PPVY,PPVZ,CVI,CVJ,RCVI,RCVJ,PPAX,PPAY,PPAZ,CAI,CAJ,CAK,RCAI,RCAJ,RCAK,radius,Feedrate,speed,RotA,TipA,TRC,TAngleB,TAngleE)
	If PostSettings.GeneralSettings.CalcHeadMoves Then
		pp_err(0,"G02")
	End If
        
End Sub

Sub G03(PPVX,PPVY,PPVZ,CVI,CVJ,RCVI,RCVJ,PPAX,PPAY,PPAZ,CAI,CAJ,CAK,RCAI,RCAJ,RCAK,radius,Feedrate,speed,RotA,TipA,TRC,TAngleB,TAngleE)
	If PostSettings.GeneralSettings.CalcHeadMoves Then
		pp_err(0,"G03")
	End If

End Sub

Sub End_Milling(DMove,DFactor,Retreat,EPAX,EPAY,EPAZ)
	wcnc_NCIExt_After
	
	Marker.Last_SuctionPos = -1
	
End Sub

Sub Start_Drilling(PNo,I_F,F,S_F,S)

	PosReset
	MoveParaReset
	wcncCom("--")
	wcncCom("--      Drilling ")
	wcncCom("--")
	
	
End Sub

Sub Drilling(DNo,PPVX,PPVY,PPVZ,PPAX,PPAY,PPAZ,D,Depth,DFlag,Free,ZMax)
Dim Count As Integer
Dim I As Integer
Dim ActDepth As Double
Dim dx As Double
Const DFI=-3
Const DFS=-3
	' Standardbohren 
'	Call Drilling0(PPVX,PPVY,PPVZ,PPAX,PPAY,PPAZ,D,Depth,DFlag,Free,ZMax)
End Sub


Sub End_Drilling(Retreat)
	Marker.Last_SuctionPos = -1

	'PPara_Reset  ' PNo,Feedrate,I_Feedrate,S_Feedrate,Mode,PreObjectType,MinRotA,MaxRotA,MinTipA,MaxTipA,DustPosNCIExt,NCIExtB,NCIExtA
	            ' außer  ---- >  Speed	< ------

End Sub


Sub Start_Vertical_DrillingHead_Stroke(pno,I_Feedrate,Feedrate,S_Feedrate,Speed)
	PosReset
	MoveParaReset
	Marker.FirstTime_DH_Drilling = True
	Marker.Programmed_DH_Speed = Speed

	LastV.IPX=-99999
	LastV.IPY=-99999
	LastV.IPZ=-99999

End Sub

Sub Vertical_DrillingHead_Stroke(SNo,SPosX,SPosY,PosX,PosY,Depth,DZ,DType,DFlag_Type,Dummy,tools,DFlag_TypeString)
Dim	DH_VE,DH_V,DH_VA As Double   ' Bohrkopf selbst

Dim FirstTNr As Long
Dim Dh_TP As IIDH_ToolPlace

Dim itp As Variant
Dim Code As TBMuster

Dim dh As tDH
Dim Driller As tDriller
Dim DFlag As Integer
Dim zmax As Double

	' Tool-No des 1. Bohrers aus dem Hub
	FirstTNr = Val(Get_First_Token(tools))   

	Set itp= ActT.t_dh.DrillingHead.ToolPlaces.GetToolPlace_PlaceID(FirstTNr) ' liefert BasicToolplace zurueck
	' deshalb instanz so erzeugen
	Set Dh_TP=itp

	' ------------------------------------------------
	' Bohrdaten Bohrkopf
	' Vorschuebe vom Bohrkopf
	' es wird davon ausgegangen, dass eine Vorschubsaenderung ueber Werkzeugaufruf
	' eine gewollte Vorschubsdefinition ist
	' ------------------------------------------------

	dh.tname = actt.t.Description
	dh.CenterX = ActT.t.MoveX	
	dh.CenterY = ActT.t.MoveY
	dh.CenterZ = ActT.t.MoveZ	
	If PPara.I_Feedrate = actt.t_dh.MoveInFeedrate Then
		' vorschub des Bohrkopfs
		dh.VE=actt.t.MoveInFeedrate
	Else
		' programmierter Vorschub
	    dh.ve=PPara.I_Feedrate
	End If
	If PPara.Feedrate = actt.t_dh.Feedrate Then
		' vorschub des Bohrkopfs
		dh.V=actt.t.Feedrate
	Else
		' programmierter Vorschub
	    dh.v=PPara.Feedrate
	End If
	If PPara.S_Feedrate = actt.t_dh.MoveOutFeedrate Then
		' vorschub des Bohrkopfs
		dh.VA=actt.t.MoveOutFeedrate
	Else
		' programmierter Vorschub
	    dh.va=PPara.S_Feedrate
	End If

	Set Driller.Edge = actt.t_dh.DrillingHead.ToolPlaces.GetCuttingEdgeActiveTool_PlaceID(FirstTNr, 0)
	Set Driller.TP = Dh_TP

	
	Driller.TName = Driller.TP.ActiveTool.Name
	Driller.E_Len = Driller.Edge.ExcessLength
	Driller.Length = Driller.Edge.Length          ' ?????????????????
	'Driller.Length = Driller.TP.ActiveTool.MaxLength

	Driller.OffX = Driller.tp.OffsetX           ' MT_Get_BasicToolPlace_OffsetX(actt.t,tools)  ' gets offset x of the first driller in row
	Driller.OffY = Driller.tp.OffsetY           ' MT_Get_BasicToolPlace_OffsetY(actt.t,tools)  ' gets offset y of the first driller in row
	Driller.OffZ = Driller.tp.OffsetZ           ' MT_Get_BasicToolPlace_OffsetZ(actt.t,tools)  ' gets offset z of the first driller in row
	' Vorschuebe des einzelnen Bohrer
	Driller.V = Driller.Edge.Feedrate        ' Vorschub
	Driller.VE = Driller.Edge.MoveInFeedrate        ' EintauchVorschub
	Driller.VA = Driller.Edge.MoveOutFeedrate        ' AustauchVorschub
	Driller.Speed = Driller.Edge.RotSpeed        		' Solldrehzahl Neu MW 09.08.2005
	
	' -- 
	' --  MW 05.12.2008 15:16:23
	' --
	' --  sonst nicht korrekt
	Driller.Speed = Driller.Edge.RotSpeed/itp.GearRate   ' Drehzahl auf Motor bezogen - 
	
	
	' Programmierten Vorschub beruecksichtigten
	If PPara.I_Feedrate <> actt.t_dh.MoveInFeedrate Then
		' vorschub wurde geaendert ist nicht urspruenglicher Wert des Bohrkopfs
		Driller.VE=PPara.I_Feedrate
	End If
	If PPara.Feedrate <> actt.t_dh.Feedrate Then
		' vorschub wurde geaendert ist nicht urspruenglicher Wert des Bohrkopfs
		Driller.V=PPara.Feedrate
	End If
	If PPara.S_Feedrate <> actt.t_dh.MoveOutFeedrate Then
		' vorschub wurde geaendert ist nicht urspruenglicher Wert des Bohrkopfs
		Driller.VA=PPara.S_Feedrate
	End If
	Driller.TNo = Driller.tp.ToolNo               ' TNummer des Bohrers auf der Steuerung
												  '  ' referiert auf die T-Korrketur auf der Steuerung fortlaufend vom 1. Bohrer beginnend		


	' --
	' -- Neu MW 09.08.2005 wenn Speed = 0 -> dann Drehzahl von Bohrer uebernehmen
	' --
	'If (Driller.Speed <> PPara.Speed) And (Marker.Programmed_DH_Speed=0) Then
	If (Driller.Speed <> Marker.LastSpeed) And (Marker.Programmed_DH_Speed=0) Then
		MT_Write_Speed(actt,Driller.Speed,itp.GearRate)
		'AK 22.04.2015 Prozssspeed setzen sonnst kommt bei Lochreihe immer Speedausgabe
		'PPara.Speed = Driller.Speed
		'Marker.LastSpeed = Driller.Speed
	End If
	
	
	' liefert Bitmuster 1 und Bitmuster 2 in Code zurueck	
	MT_Get_SpindleCode_Dez(tools,Code)

	If Driller.edge Is Nothing Then
	    ' kann nicht vorkommen
	    pp_err(0,"driller.edge = nothing")
	End If

	
	wcnccom("vertical drilling: ->"+tools+"<-"+ " "+Driller.TName+" Typ:"+DType)
'	If (Marker.Last_DH_ToNo<>Driller.Tno) Then
'		' Laengenkorrektur aktivieren fuer 1. Bohrer des Hubs
'		wcnc("T"+inttos(Driller.TNo)+ " D1")
'	End If
	
	If Marker.Last_DH_Process = DRILL_DHH Then
		' letzte Bearbeitung fand mit horizontal Spindeln statt
		' hor. Bohr Spindeln zuruecklegen
		wcnccom("pins up",True)
		WCNC_WRITE_DHCode("",false)
	End If
	
    If (Not Marker.Last_DH_Process = DRILL_DHV) Or (Marker.Last_DH_Tools<>tools) Then
    	' MW 14.03.2018 - bei Bohrmuster - Aenderung auch, aufgrund Offsetverrechnung
    	' letzter Hub war kein Vertikal drilling head hub
    	' also Ebene setzen
        Call wcncViewChange_DH(dh,DH_View0.View,DH_View0.LastView,DH_View0.IPX,DH_View0.IPY,DH_View0.IPZ,DH_View0.RotA,DH_View0.TipA,Driller)
    End If
    
    
	'If Firsttime_Viewchange Then 
	' neu mw 28.04.2005
	'If Firsttime_Viewchange Or Is_WP_Change Then 
	' Neu MW 28.06.2006
	' Beim Bohren mit Bohrkopf kommt zwischen den Bohrungen kein workpieceindex
	If Firsttime_Viewchange Then 
	    ' 1. Anfahrt auf Werkstueck
		' bei ersten mal wird immer ohne Z angefahren
		
		wcnc(G0+XEqualToS(PosX)+YEqualToS(PosY))
		Firsttime_Viewchange =False	
	End If
'	Else
	
		If (Marker.Last_DH_ToNo<>Driller.Tno) Then
		    ' In Sicherheit auf Z im Bezug auf aktuellen Vorlegecode
		    ' wenn siche bohrmuster aendert und die folgenden Bohrer Laenger sind
		    If (Driller.Length > Marker.last_DH_TLength) And (Marker.Last_DH_Process=DRILL_DHV) Then
		    	' jetziger HUB findet mit laengerem Werkzeug statt 
		    	' daher muss jetzt erst mal im Bezug auf laengeres Werkzeug hochgefahren werden
		    	' fuer aktives Werkzeug ist Laengenkorrektur bereits aktiv
		    	wcnccom("Hochfahren, da laengeres Werkzeug vorgelegt wird:")
		    	wcnccom("bisher:"+ftos(Marker.last_DH_TLength)+" jetzt:"+ftos(Driller.Length))
				' Neu MW 15.09.2005 * zusaetzlichen Sicherheitsabstand einrechnen
			    wcnccom("Additives ZMass:"+ftos(GetAddZSic))
		    	
			    wcnc(G0+ZEqualToS(actt.t_dh.GetSecurityZ(ActV.TipA)+GetAddZSic))
			    LastPos.Z = actt.t_dh.GetSecurityZ(ActV.TipA)
			End If
		    If (Marker.Last_DH_Process=DRILL_DHH) Then
		    	' letzter Hub fand horizontal statt
		    	' fuer aktives Werkzeug ist Laengenkorrektur bereits aktiv
		    	wcnccom("Z-Positionieren, da vorher Hor. Bohren")
				' Neu MW 15.09.2005 * zusaetzlichen Sicherheitsabstand einrechnen
			    wcnccom("Additives ZMass:"+ftos(GetAddZSic))
		    	
			    wcnc(G0+ZEqualToS(actt.t_dh.GetSecurityZ(ActV.TipA)+GetAddZSic))
			    LastPos.Z = actt.t_dh.GetSecurityZ(ActV.TipA)
			End If

		End If
	    
'	End If
	' ----------------------------------------------------
	' -- hier Bohrspindeln vorlegen
	' -- Nicht mehr hier vorlegen, -> Zeitgewinn erst anfahren dann check und vorlegen
	' MT_WRITE_DHCode(actt,tools)
	' ----------------------------------------------------
	DFlag = Val(Get_First_Token(DFlag_TypeString))
	
	' Neu MW 25. Juli 2005
	zmax=GetZMax(DFlag Mod 10,Depth)
	wcncCom("ZMax:"+FToS(zmax))


	If (DFlag >19) And (DFlag<30) Then
		' Bohrzyklus Durchgangsloch bohren
		Drilling_DH_Cylce_20(PosX,PosY,Depth,actt.t_dh.GetSecurityZ(0),Driller,dh,tools,zmax)
	ElseIf (DFlag >29) And (DFlag<40) Then
		' Bohrzyklus Topfband mit Verweilzeit bohren
		Drilling_DH_Cylce_30(PosX,PosY,Depth,actt.t_dh.GetSecurityZ(0),Driller,dh,tools,zmax)
	Else
		'If (DFlag >9) And (DFlag<20) Then
		' Bohrzyklus Sackloch bohren
		Drilling_DH_Cylce_10(PosX,PosY,Depth,actt.t_dh.GetSecurityZ(0),Driller,dh,tools,zmax)
	
	End If

	Marker.Last_DH_Process = DRILL_DHV
	Marker.last_DH_TLength = Driller.Length
	Marker.Last_DH_ToNo = Driller.tno
	
	Marker.Last_DH_Tools = tools
	
End Sub

' -----------------------------------------------------
' -- Sackloch   - blind hole
' -----------------------------------------------------
' -- ppvx       : Bohrpos in X auf Ebene (Viewchange bezogen)
' -- ppvy       : Bohrpos in Y auf Ebene (Viewchange bezogen)
' -- depth      : Bohrtiefe auf Ebene bezogen (Viewchange bezogen)
' -- ve         : Eintauchvorschub
' -- v          : Bohrvorschub im Material
' -- va         : Austauchvorschub aus dem Teil raus
' -----------------------------------------------------


Sub Horizontal_DrillingHead_Stroke(SNo,View,IPX,IPY,IPZ,RotA,TipA,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz,S_PosX,S_PosY,PosFirst_X,PosFirst_Y,PosZ,SPosX_V,SPosY_V,PosFirstX_V,PosFirstY_V,SPosZ_V,PosFirstZ_V,Depth,DZ,DType,DFlag_Type,Dummy,tools,DFlag_TypeString)

Dim ox,oy,oz As Double
Dim Dh_TP As IIDH_ToolPlace
Dim itp As Variant
Dim FirstTNr As Long
Dim Code As TBMuster

Dim dh As tDH
Dim Driller As tDriller

	FirstTNr = Val(Get_First_Token(tools))
	

	
	Set itp= actt.t_dh.DrillingHead.ToolPlaces.GetToolPlace_PlaceID(FirstTNr)
	Set Dh_TP=itp

	' Bohrdaten Bohrkopf
	' Vorschuebe vom Bohrkopf
	
	' Neu MW 27.04.2005
	' setzt die dh und driller  - Daten 
	' MT_SetDrillingHeadData(tools, dh,Driller)
	' 
	
	dh.tname = actt.t.Description
	dh.CenterX = ActT.t.MoveX	
	dh.CenterY = ActT.t.MoveY
	dh.CenterZ = ActT.t.MoveZ	
	dh.VE=actt.t.MoveInFeedrate
	dh.V=actt.t.Feedrate
	dh.VA=actt.t.MoveOutFeedrate
	
	
	' Bohrdaten fuellen in Type TBohrer
	Set Driller.Edge = actt.t_dh.DrillingHead.ToolPlaces.GetCuttingEdgeActiveTool_PlaceID(FirstTNr, 0)
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
	Driller.Speed = Driller.Edge.RotSpeed        		' Solldrehzahl Neu MW 09.08.2005
	
	
	' -- 
	' --  MW 05.12.2008 15:16:23
	' --
	' --  sonst nicht korrekt
	Driller.Speed = Driller.Edge.RotSpeed/itp.GearRate   ' Drehzahl auf Motor bezogen - 
	
	Driller.TNo = Driller.tp.ToolNo               ' TNummer des Bohrers auf der Steuerung
												  '  ' referiert auf die T-Korrketur auf der Steuerung fortlaufend vom 1. Bohrer beginnend		
	
	' --
	' -- Neu MW 09.08.2005 wenn Speed = 0 -> dann Drehzahl von Bohrer uebernehmen
	' --
	If Not equal(Driller.Speed,Marker.LastSpeed) And (Marker.Programmed_DH_Speed=0)Then
		MT_Write_Speed(actt,Driller.Speed,itp.GearRate)
	End If
	
	' liefert Bitmuster 1 und Bitmuster 2 in Code zurueck	
	MT_Get_SpindleCode_Dez(tools,Code)
		

	wcnccom("horizontal drilling: ->"+tools+"<-"+ " "+Driller.TName+" Typ:"+DType)
'	If (Marker.Last_DH_ToNo<>Driller.Tno) Then
'		wcnc("T"+inttos(Driller.tno)+ " D1")
'	End If



	If ((Marker.Last_DH_Process = DRILL_DHH) Or (Marker.Last_DH_Process = DRILL_DHV)) And (Marker.Last_DH_ToNo<>Driller.Tno) Then
		' letzte Bearbeitung fand mit horizontal oder Vertikalen Spindeln statt
		' und Vorlegespindeln haben sich geaendert 
		' hor. Bohr Spindeln zuruecklegen
		wcnccom("hor. Bohren alle Bohrspindeln zuruecklegen")
		
		
		' Neu MW 13.09.2005 - hat bisher gefehlt, hat aber keine Probleme verursacht, da
		' Spindeln alle im zurueckgezogenen Zustand
		If (Marker.Last_DH_Process = DRILL_DHH) And (LastV.View<>View) Then
			' hochfahren, auf Sicherheit in Z
			' Neu MW 15.09.2005 * zusaetzlichen Sicherheitsabstand einrechnen
		    wcnccom("Additives ZMass:"+ftos(GetAddZSic))
		    'wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+GetAddZSic))
		    ' Neu MW 15.09.2005 - Bug IPZ ist nicht korrekt, da ja noch letzter View aktiv 
		    
'	    wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-LastV.IPZ+GetAddZSic))
		    'wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ))
		    
			' SF/MW 06.07.2016
			' Ebene kommt mit Agg-Versatz Z verrechnet
		    wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-LastV.IPZ+Marker.Last_DH_DZ+GetAddZSic))		    
		End If
		
		wcnccom("pins up",True)
		WCNC_WRITE_DHCode("",false)
	End If

    If (Not Marker.Last_DH_Process = DRILL_DHH) Or (LastV.View<>View) Or (LastV.IPX<>IPX) Or (LastV.IPY<>IPY) Or (LastV.IPZ<>IPZ) Then
    	' letzte Bearbeitung nicht horizontal oder ebene gewechselt
    	
		Call wcncViewChange_DH(dh,View,0,IPX,IPY,IPZ,RotA,TipA,Driller)
		
	    If (Marker.Last_DH_Process = DRILL_DHV) Then
		    wcncCom("hochfahren, da vorher vertikal bohren")
			'wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+GetAddZSic))		
			
			' SF/MW 06.07.2016
			' Ebene kommt mit Agg-Versatz Z verrechnet
			wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+DZ+GetAddZSic))		
			
		Else
	       ' Neu MW 28.06.2006 - immer hochfahren auch wenn vorher hor. Bohren
	       If (Marker.Last_DH_Process = DRILL_DHH) Then
			    wcncCom("hochfahren, da zuvor hor. bohren aber Ebenenaenderung")
				' wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+GetAddZSic))		
				
				
				' SF/MW 06.07.2016
				' Ebene kommt mit Agg-Versatz Z verrechnet
				wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+DZ+GetAddZSic))		
				
				
				wcnc(G0+XEqualToS(PosFirstX_V)+ZEqualToS(actt.t_dh.SecurityHorz))
			End If
		End If
		'MT_WRITE_DHCode(actt,tools)
	    '.-------------------------
	ElseIf (Marker.Last_DH_Tools<>tools) Then
		' andere Bohrspindel - Versatz rechnen
		Call wcncViewChange_DH(dh,View,0,IPX,IPY,IPZ,RotA,TipA,Driller)
	
	End If

	'If Firsttime_Viewchange Then 
	' neu mw 28.04.2005
	'If Firsttime_Viewchange Or Is_WP_Change Then 
	' Neu MW 28.06.2006 
	' Beim Bohren mit Bohrkopf kommt zwischen den Bohrungen kein workpieceindex
	If Firsttime_Viewchange Then 
	    ' 1. Anfahrt auf Werkstueck
		' bei ersten mal wird immer ohne Z angefahren
		wcnccom("WP-CHANGE DH HOR")
		wcnc(G0+XEqualToS(PosFirstX_V)+ZEqualToS(actt.t_dh.SecurityHorz))
		
		Firsttime_Viewchange =False	
	Else

		If (Marker.Last_DH_ToNo<>Driller.Tno) Or (Marker.HorDH_PullBack) Then 
			If (Marker.HorDH_PullBack) Then
				' Neu MW 20.02.2007
			    ' wcnccom("**MW20022007")
'				wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+GetAddZSic))
				
				' SF/MW 06.07.2016
				' Ebene kommt mit Agg-Versatz Z verrechnet
				wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+DZ+GetAddZSic))		
				
			End If
		    ' In Sicherheit auf Z im Bezug auf aktuellen Vorlegecode
		    ' wenn siche bohrmuster aendert und die folgenden Bohrer Laenger sind
		    'wcnccom("**JS1")
		    
			' Neu MW 15.09.2005 * zusaetzlichen Sicherheitsabstand einrechnen
		    wcnccom("Additives ZMass:"+ftos(GetAddZSic))
		    ' Neu Nuertingen, MW 21.09.2005 * auch in X muss positioniert werden..
		    'wcnc(G0+XEqualToS(PosFirstX_V)+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+GetAddZSic)+ZEqualToS(actt.t_dh.SecurityHorz))
		    
				' SF/MW 06.07.2016
				' Ebene kommt mit Agg-Versatz Z verrechnet
		    
		    wcnc(G0+XEqualToS(PosFirstX_V)+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+DZ+GetAddZSic)+ZEqualToS(actt.t_dh.SecurityHorz))
		    
		    'wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+GetAddZSic)+ZEqualToS(actt.t_dh.SecurityHorz))
		    'wcnccom("Additives ZMass:"+ftos(GetAddZSic))
		    ' Neu MW 21.09.2005 auch in X bereits angefahren folgende Zeile entfaellt
		    'wcnc(G0+XEqualToS(PosFirstX_V)+ YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+GetAddZSic)+ZEqualToS(actt.t_dh.SecurityHorz))
		Else
			' gleicher Bohrer wie zuvor
			' nichts tun
		End If
	    
	End If
	
	
	Drilling_DHorz(PosFirstX_V,PosFirstY_V,0,Depth,DFlag_Type Mod 10,0,GetZMax(DFlag_Type Mod 10,Depth),Driller,dh,tools)
	
	' Bohrkopf zuruecklegen
	Marker.Last_DH_Process = Drill_DHH 
	Marker.Last_DH_ToNo = Driller.tno
	Marker.Last_DH_Tools = tools
	Marker.Last_DH_DZ = DZ
	
End Sub

Sub End_Vertical_DrillingHead_Stroke(Retreat)


	If (Marker.Last_DH_Process = DRILL_DHH) Then
		' letzter Hub horizontal
	    wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(90)-LastV.IPZ+Marker.Last_DH_DZ+GetAddZSic))		    
	Else
		' letzter Hub vertical
		'wcnc("G0 Z="+Ftos(ActT.t_dh.GetSecurityZ(0)+(FinishedPart.Z+GetAddZSic-lastv.ipz+Marker.Last_DH_DZ)))
		wcnc("G0 Z="+Ftos(ActT.t_dh.GetSecurityZ(0)+GetAddZSic))
		'wcnc("G0 Z="+Ftos(ActT.t_dh.GetSecurityZ(0)+(FinishedPart.Z+GetAddZSic))+Get_Val_Signed(-ActT.t.DrillingHead.CenterZ))
	End If

	WCNC_SUB(SUB_TRANSOFF)
	
	wcnccom("pins up",True)

	WCNC_WRITE_DHCode("",true)
	
	
' zu spaet MW 08.03.2018  - 2 vor TRANSOFF
'	wcnc("G0 Z"+Ftos(actt.t_dh.GetSecurityZ(0)+(FinishedPart.Z+GetAddZSic)))
	
	Marker.FirstTime_DH_Drilling=False
	Marker.Last_DH_ToNo	= -9999   ' Sonst wird Korrektur nicht neu angewaehlt, wenn dazwischen z.B. eine Fraesbearbeitung stattfindet!
	
	Marker.Last_DH_Tools = ""
	
	'PPara_Reset  ' PNo,Feedrate,I_Feedrate,S_Feedrate,Mode,PreObjectType,MinRotA,MaxRotA,MinTipA,MaxTipA,DustPosNCIExt,NCIExtB,NCIExtA
	            ' außer  ---- >  Speed	< ------
	

End Sub

Sub NC_End()

	wSafetyAbs(False)
	WCNC_PARK()
	WCNC_PRGEND()
	wcnc("M17")
	FileClose
	
	ClearMTData  
	ClearObjects

End Sub

Sub NCInfo(Kind,NCType,Para1,Para2,Para3,Para4,Para5,Para6,Para7,Para8,Para9,characters)

	Handle_NCInfo(Kind,NCType,Para1,Para2,Para3,Para4,Para5,Para6,Para7,Para8,Para9,characters)
End Sub



'	Sub HeadInfo(id)
'	Dim H As Object
'		
'		Set H= TDATA.GetProcessHead_ID(id)
'		If id >= 0 Then
'			HeadID= id
'		Else
'			pp_err(126)  ' MW 31.03.2016 - darf nicht sein
'			HeadID = MT_GetFirst_TC_Hid
'		End If
'		
'	'	' -- AK 04.05.2011
'	'	'Wenn naechstes Werkzeug nicht Bohrkopf, dann Aufraeumzyklus aufrufen
'	'	If ViewInfoToolChangeFlag And id <> 51 Then
'	'		If JobPara.isg Then
'	'			wcnc("L CYCLE [NAME=CP_CLEARDH.NC @P1=1]")
'	'		End If 	
'	'	End If 
'	'	ViewInfoToolChangeFlag=False
'	End Sub


Sub WorkPieceListInit(count)
	ReDim WPI(1)  ' MW 03.03.2016 muss frueher aufgerufen werden
	If Not PostSettings.GeneralSettings.WriteInitZero Then
		pp_err(5,"WriteInitZero")
	End If
	
	WritingNCData = False

	
	
End Sub


'WorkPieceInfo "AH",100.000000000,1000.000000000,0.000000000,"D:\CAMPUS\HOP\HH\NUT1.HOP",0.000000000,0.000000000,0.000000000,800.000000000,1000.000000000,20.000000000
Sub WorkPieceInfo(SName,Sox,Soy,Soz,WPName,WPox,WPoy,WPoz,WPx,WPy,WPz)
    WPI(UBound(WPI)).SName = SName     ' Stop name
    WPI(UBound(WPI)).Sox = Sox         ' Stop offset x   
    WPI(UBound(WPI)).Soy = Soy         ' stop offset y
    WPI(UBound(WPI)).Soz = Soz         ' stop offset z
    WPI(UBound(WPI)).WPName = WPName   ' workpiece name
    WPI(UBound(WPI)).WPox = WPox       ' workpiece offset x
    WPI(UBound(WPI)).WPoy = WPoy       ' workpiece offset y
    WPI(UBound(WPI)).WPoz = WPoz       ' workpiece offset z
    WPI(UBound(WPI)).WPx = WPx         ' workpiece x
    WPI(UBound(WPI)).WPy = WPy         ' workpiece y
    WPI(UBound(WPI)).WPz = WPz         ' workpiece z
    ReDim Preserve WPI(UBound(WPI)+1) 
	
End Sub

Sub WorkPieceIndex(idx)
	Marker.wp_lastindex = Marker.wp_actindex
	Marker.wp_actindex = idx+1
End Sub

Sub FinishedpartInfo(Anschlag,Dreh)
'	JobPara.Flag=Anschlag
	'drehflag=Dreh
End Sub


'Sub Start_NCInfoProcess (PNo,I_F,F,S_F,S)
' MW 01.04.2016 nicht mehr notwendig
'End Sub

Sub NCInfoProcess(InfoTyp,x1,y1,z1,x2,y2,z2,w1,w2,w3,w4,w5,w6,w7,w8,w9,w10,w11,w12,w13,w14,w15,w16,w17,w18,w19,w20,w21,str1,str2)

	wcnccom("NCInfoProcess : "+inttos(InfoTyp),True)
	Handle_NCInfoProcess(InfoTyp,x1,y1,z1,x2,y2,z2,w1,w2,w3,w4,w5,w6,w7,w8,w9,w10,w11,w12,w13,w14,w15,w16,w17,w18,w19,w20,w21,str1,str2)

End Sub


Sub Old_AdditionalSPInfo(DirectionMode,ExcessLength,Mode,Laser,AxisRotA,Res1,SurfaceMode,dw_agg,Res4,Res5,KW,TRC,DISTANCE,DW,MinRot,MaxRot,MinTipA,MaxTipA,s5)
	'MsgBox("SPInfo: MinRot:"+Ftos(MinRot)+" MaxRot:"+ftos(MaxRot)+" MinTip:"+Ftos(MinTipA)+" MaxTip:"+ftos(MaxTipA),vbInformation )
	wcnccom("Surfacemode:"+inttos(SurfaceMode))  ' 
	
	If SurfaceMode=3 Then
		SurfaceMode=2
	End If
	If equal(Mode,1) Then
		pp_err(1)
		'MillC_INIT(True,DirectionMode,ExcessLength,Mode,AxisRotA,KW,TRC,DISTANCE,MinRot,MaxRot,DW)			
	ElseIf equal(SurfaceMode,1) Then
		pp_err(1)
		'SurfaceMilling_Init(True,SurfaceMode,DirectionMode,ExcessLength,AxisRotA,KW,TRC,DISTANCE,MinRot,MaxRot,MinTipA,MaxTipA)
	ElseIf equal(SurfaceMode,2) Then
		pp_err(1)
		'SurfaceMilling_Init(True,SurfaceMode,DirectionMode,ExcessLength,AxisRotA,KW,TRC,DISTANCE,MinRot,MaxRot,MinTipA,MaxTipA)
	End If
	If equal(Mode,0) Then
		' -- 
		' --  MW 03.04.2014
		' --  Implementation asymetrisches Topfbandaggregat / Oder Reihenbohrgetriebe
		' --  
		' -- +90, da unserer Ebene 1 (Y+) die Nullebene die Reihe In X stehend O O X O O hier als 0° kommt
		MultiDrilling_GBHeadVert.dw = dw_agg  + 90  ' ???
    End If

End Sub


Sub Old_AdditionalVertDrillingInfo(DW,Res1,Res2,Res3,Res4)

	
	' +90, da unserer Ebene 1 (Y+) die Nullebene die Reihe in X stehend O O X O O hier als 0° kommt
	MultiDrilling_GBHeadVert.dw = DW + 90
	' -- 
	' --  MW 02.07.2008 14:10:37
	' --
	' -- da aenderung PP-Engine diese Funktion wird vor Toolchange aufgerufen
	'MultiDrilling_GBHeadVert.Angle = actt.T_SGB.Angle
 
End Sub




Sub ClampChange(par1,par2,par3,par4,par5,par6,par7,par8,par9,par10,par11,par12)
Dim pcount, i,No As Integer
Dim para,pstri, p3,p4,p5,p6 As String 
Dim Next_Working_Box,Next_Working_Head As Long 
Dim Same_Tool_Next, MultiSzene As Boolean 
Dim d As Variant 
Dim tmp_Speed As Double 

	pp_err(6,CallersLine)
    JobPara.ActScene=JobPara.ActScene+1


	Same_Tool_Next = False
	tmp_Speed = -1

	No=1
	' Annahme par12 = "@P:2;@P:3;@S:HALLO"
	p3="" 
	p4="" 
	p5="" 
	p6="" 

	' MultiSzene --> es kommen noch weitere Szenen z.B. keine Drehzahl anfordern
	' AK 22.01.2018
	MultiSzene=False

	pcount = paramcount(par12)
	If InStr(par12,"@P")>0 Then
		' es wurden Parameter uebern String uebergeben!
		For i = 1 To pcount
			para = Param(i,par12)
  		    ' Debug.Print InStr("Hello","l") ' 3
			If InStr(para,"@P3")>0 Then
				p3= Replace(para,"@P3:","")
			ElseIf InStr(para,"@P4")>0 Then
				p4= Replace(para,"@P4:","")
			ElseIf InStr(para,"@P5")>0 Then
				p5= Replace(para,"@P5:","")
			ElseIf InStr(para,"@P6")>0 Then
				p6= Replace(para,"@P6:","")
			ElseIf InStr(para,"@S")>0 Then
				pstri= Replace(para,"@S:","")
			End If
		Next i
		' -- AK 22.01.2018 
		' – Bei Bit 7 in Parameter p3 à Kennung für Multiszene setzen 
		If (p3 And 128)>0 Then
			MultiSzene=True
		End If
	End If

	MT_GetToolId_Next_Process(Next_Working_Box,Next_Working_Head)

	
	If (Next_Working_Box > 0) And (Not actt.t Is Nothing) Then
		' -- MW 20.02.2012 
		' -- nach umspannen muss eigentlich immer noch eine Bearbeitung kommen! 
		If equal(Next_Working_Box,actt.t.ID) Then
			wcnccom("Naechstes Werkzeug:"+inttos(Next_Working_Box)+" ist auch aktuelles Werkzeug")
			Same_Tool_Next = True
		End If
		
		MT_Tool_Re_Change() ' M5 AUS !! 
		
	End If
	'AK 22.04.2015 Antriebe vor letzen Szenenaufruf
	If (Next_Working_Box < 0) And (Not actt.t Is Nothing) Then
		MT_Tool_Re_Change() ' M5 AUS !! 	
	End If
	
	
	If Same_Tool_Next = True Then
		' es geht mit gleichem Werkzeug weiter 
		' Spindel wieder einschalten
		If Not MT_IsDH(actt) Then
			tmp_Speed = Marker.LastSpeed   'ProcessPara.Speed
		End If
		
		' -- AK 22.01.2018 
		' – Bei Multiszene wird kein Toolspeed ausgegeben 
		If (tmp_Speed > 0) And (MultiSzene=False) Then
			MT_Write_Speed(ActT,tmp_Speed)
		End If

	End If


End Sub

Sub LeadInOutWithoutSafety(an,ab)
		
End Sub



' ------------------------------------------------------------------------------
' ------------------------------------------------------------------------------
' ------------------------------------------------------------------------------
' ------------------------------------------------------------------------------
' ------------------------------------------------------------------------------
' ------------------------------------------------------------------------------
' ------------------------------------------------------------------------------
' ------------------------------------------------------------------------------
' ------------------------------------------------------------------------------
' ------------------------------------------------------------------------------
' ------------------------------------------------------------------------------
' ------------------------------------------------------------------------------
' ------------------------------------------------------------------------------
' ------------------------------------------------------------------------------
' ------------------------------------------------------------------------------
' ------------------------------------------------------------------------------
' ------------------------------------------------------------------------------
' ------------------------------------------------------------------------------
' ------------------------------------------------------------------------------
' ------------------------------------------------------------------------------
Sub ProcessIndex(PListNo)  ' gibt die ProcessNummer des folgenden Prozesses bekannt
	ProcessInfo_Set(PListNo) 
	
	If PListNo > 1 Then
		pParaLast = PPara
	End If


	If PListNo<NCData.ProcessList.Count Then 
		pParaNext = ProcessInfo_Set(PListNo+1)
	Else
		ProcessInfo_Init(pParaNext)  ' MW 18.07.2018 sonst liefert Process_IS_DS(PParaNext) falsches Ergebnis
		Set pParaNext.actT.T=Nothing
	End If
	' immer nach dem setzen von pparanext, da der info_str immer auf ppara geschrieben wird
	PPara = ProcessInfo_Set(PListNo)  

	
	wcnccom(JobPara.P_Info)
	
End Sub

Sub Process_Start(ProcId,BoxId,HeadID,d1,d2,ProcC,XMin,YMin,ZMin,XMax,YMax,ZMax)
	Call Process_Start_7(ProcId,BoxId,HeadID,d1,d2,ProcC,XMin,YMin,ZMin,XMax,YMax,ZMax)
End Sub


Sub Process_End(ProcId,d1,d2)
	Call Process_End_7(ProcId,d1,d2)
End Sub


'  MMode,PreObjectTyp: Integer; MinAS, MaxAS, MinTAs, MaxTAS: Double; R1, R2, R3, R4
Sub AdditionalSPInfoMPs(Mode,PreObjectTyp, MinRot,MaxRot,MinTipA,MaxTipA, R1, R2, R3,  R4)
	Add_SPInfoMPs_7(Mode,PreObjectTyp, MinRot,MaxRot,MinTipA,MaxTipA, R1, R2, R3,  R4)
End Sub


' --------------------------------------------------------------------------------------------------------------------------------------
' DLL-Milling - zugehoerige Functions/Subs
' --------------------------------------------------------------------------------------------------------------------------------------


Sub InitDLLMPs_Milling
	DLLMPs_Init()
End Sub


Sub DLLMPs_Start_Milling(pno)
	DLLMPs_Start(pno)
End Sub


Sub DLLMPs_Milling(Kind,pno)
	DLLMPs(Kind,pno)
End Sub


Sub DLLMPs_End_Milling
	DLLMPs_End()
End Sub

Sub FinalDLLMPs_Milling
	' kommt nur einmalig zum Schluss
	DLLMPs_Final()
End Sub


Sub processlistinit(c)
	
End Sub

Sub ProcessInfo(s,d,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15,d16,d17)

	
End Sub
