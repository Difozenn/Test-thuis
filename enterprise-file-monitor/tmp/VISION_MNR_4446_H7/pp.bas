' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \%postdir%\pp.bas
' -- 
' -----------------------------------------
'#uses "pp_global.bas"
'#uses "pp_7.bas"
'#uses "pp_mt.bas"
'#uses "pp_mtf.bas"
'#uses "pp_bohrdh.bas"
'#uses "pp_ncinfo.bas"
'#uses "pp_clamps.bas"
'#uses "pp_math.bas"

Option Explicit

Sub Processindex(PListNo)
	ProcessInfo_Set(PListNo)
	
	wcnccom(JobPara.P_Info,True)

End Sub

Sub InitZero
	JobPara.TimerFullSecs = Timer

	' PP-Engine min.Version
	Version_Check("7.0.0.212")

	ReDim Preserve LogArr(1) 
	ReDim WPI(1)	 ' MW 11.02.2016 - damit im Fehlerfall beim Init (vor dem WorkpieceInfo) nicht auf leeres Array laeuft!


	' --
	' 1. Funktion im Script -> auch vor allen NCINFO's
	' --
	INITZero_7  

	' MW 31.07.2013 Evolution - setzen so frueh wie moeglich
	' MW 05.03.2014 jetzt ganz am Anfang
	
    Read_MPara_ADD   ' Parkpos lesen etc. 
    
    
	
  	AddLog("INIT_ZERO TIME: "+ftos(Timer-JobPara.TimerFullSecs)+" sec")

	JobPara.lstp = 10
	MT_GetMachineKinematiks(1)
End Sub


Sub ToolListInit(Count)
Dim Secs_Plausi As Double
	ReDim Preserve LogArr(1) 

	CountOfTool	= Count   ' MW 04.07.2005 auch wenn keine Werkzeuge muss Programm erzeugbar sein z.B. Laserbahnen
	
'    If DEF_Plausi_Check Then
'   		Secs_Plausi = Timer
'	    plausibility_check
'	    AddLog("PLAUSI - DURCHLAUF : "+ftos(Timer-Secs_Plausi)+" sec")
'
'	End If
	If Count>0 Then 
     	ReDim ToolArray(Count)
    End If
    ToolPos=0
	Secs_ToolList = Timer

End Sub

'Sub Tool(BoxNo,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15,d16,d17,d18,d19,d20,d21,d22,d23,d24,d25,d26,d27,d28,d29,d30,d31,d32) 'H6
Sub Tool(BoxNo,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15,d16,d17,d18,d19,d20,d21,d22)
	'26000,"2600_HW_WP_GERADE_D18_NL50_AL80_GL150_Z1+1_RE_S25","",10001,13,1,-1,8000.000000000,2000.000000000,30000.000000000,22000.000000000,22000.000000000,0.000000000,50.000000000,50.000000000,9.010000000,174.850000000,1.500000000,0.000000000,0.000000000,0.000000000,0.000000000,0.000000000

	MT_SetTHopsBasicToolExt(ToolArray(ToolPos),BoxNo,HeadID)
	
	ToolPos=ToolPos+1
	
End Sub

Sub ProcessListInit(Count)
	'ProcessNumber = 0
	'If Count>0 Then 
    ' 	ReDim AllProcessListArray(Count-1)
    'End If
	
End Sub

Sub ProcessInfo(Processtype,View,IPX,IPY,IPZ,RotA#,TipA#,SPVX,SPVY,SPVZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)

'Dim Process As TAllProcessPara
'
'	Call PParaSetALL(Process,Processtype,View,IPX,IPY,IPZ,RotA#,TipA#,SPVX,SPVY,SPVZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
'	
'    AllProcessListArray(ProcessNumber)=Process
'	ProcessNumber = ProcessNumber + 1
	
	
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

Sub ClampChange(situa1,situa2,Para1,Para2,Para3,Para4,Para5,Para6,Para7,Para8,Para9,ParaStr)
Dim tt As THopsBasicToolExt
	'MM 16.11.2006   Abfahrt erzwingen vor umspannen
	'wenn gleiches tool !!!!
	If (Retreat_ClampChange = 0) Or (situa2=1) Then
		Z_Is_Safety=False
		
		' -- MW 22.10.2009
		If MT_Is_Vertical_StandardTool5Axis(ActT) Then
			' Traori muss aus
			If (ActT.h_add.traori) Then
				' 5-Axis mit Traori -
				wcncAddCom(ActT.H_Add.TraoriOff, " 5-Achs - Transformation abschalten")  ' "TRAFOOF"
			End If
			
		End If
		
		' --  MW 12.11.2007 14:18:07
		wSafetyAbs(False)
		'wcnc("G53 "+ G0 + " X="+MAX_LIMIT_XPLUS )
		Firsttime_Viewchange=True

		' -- MW 22.10.2009
		If MT_Is_Vertical_StandardTool5Axis(ActT) Then
			' Traori wieder an
			If (ActT.h_add.traori) Then
				' 5-Axis mit Traori -
				wcnc(ActT.H_Add.TraoriOn)  '  "TRAORI"	
			End If
			
		End If


		
		' --  MW 08.11.2007 09:30:12
		' --  Ebenenwechsel erzwingen
		ActV.View=-1  
	End If
	
	If situa2=1 Then
		' Nur bei 1. Szenenwechsel möglicher Werkzeugwechsel
'		ClampChangeParkXY	  ' Parken X / Y 
	End If
	
	Handle_Clamp_Situation(situa1,situa2)
	
	' --
	'Call wcncMachineComponentData(situa2)

End Sub
Sub Init(NCPath)
Dim NCITrenner As Integer

  AddLog("ToolList-Data aufsammeln: "+ftos(Timer-Secs_ToolList)+" sec")


  'Initializing global variables
  ncpathGlobal=NCPath
  NCLine=10
  Firsttime_Viewchange=True
  
  Set ActT.t = Nothing
  Set LastT.t = Nothing
  Set FirstT.t = Nothing
  
  
  MarkerSawingReset
  Z_Is_Safety=False
  Z_Is_SafetyPart=False
  FloatFormat="0.000"
  
  Init_MachineData  
  Init_JobData
  Init_Marker
  
	'Prüfen, ob Trenner für An- Abfahrbewegung eingeschaltet ist
	'NCITrenner=ReadIntPP_ini("NCInfo","NCILeadInOut",-1)
	'If NCITrenner<>500 Then
	'	AddMistake(GetErrMsg(100,"_Fehler bei Einstellungen NCInfo 500",1)) 
	'End If
	
	SetDrillingZMax -5,-10,-15,-20,-25,-30,-35,-40,-45
	Haube.P3AchsAktiv=False
	Haube.P3AchsLastPos=-9999
	Haube.P5AchsAktiv=False
	Haube.P5AchsLastPos=-9999
	Haube.PLeitblechAktiv=False
	Haube.PLeitblechPos=-9999
	Haube.PleitblechDist=-9999
	Haube.LastTipAng=-9999
End Sub

'Sub FirstTool(BoxNo,ToolName,ToolTypStr,ToolType,ToolNo,CorrNo,AggNo,Feedrate,I_Feedrate,S_Feedrate,T_Speed,P_Speed,SawThickness,Safety_Horiz,Safety_Z,Radius,Length,StartFactor,AddMx,AddMy,AddMz,RotA,TipA,S1,S2,S3,S4,S5,S6,S7,S8,S9,S10,SPVX,SPVY,SPVZ,Vzx,Vzy,Vzz) 'OLD H6
Sub FirstTool(BoxNo,ToolName,ToolTypStr,ToolType,ToolNo,CorrNo,AggNo,Feedrate,I_Feedrate,S_Feedrate,T_Speed,P_Speed,SawThickness,Safety_Horiz,Safety_Z,Radius,Length,StartFactor,AddMx,AddMy,AddMz,RotA,TipA,SPVX,SPVY,SPVZ,Vzx,Vzy,Vzz)

  	Dim t As IIHopsBasicTool   ' Die Mutter der O-Typen 1-4 hierüber  können alle Standard - Eigenschaften abgerufen werden
	Dim PTC As Boolean
	Dim Next_TCB_T As THopsBasicToolExt



	MT_SetTHopsBasicToolExt(FirstT,BoxNo,HeadID)
	MT_SetTHopsBasicToolExt(Next_TCB_T,BoxNo,HeadID)
	Set Next_TCB_T.t = TDATA.GetTool_ID(BoxNo)
	Set t= TDATA.GetTool_ID(BoxNo)
	Set TCB_T.t = TDATA.GetTool_ID(BoxNo)	
	
	'Set Basic infos of FirstTool
	If MT_Is_TC_T(FirstT) Then
		Info_FT.BoxNo=BoxNo
		Info_FT.AggNo=AggNo
		Info_FT.HeadID=HeadID
		Info_FT.TC_PLACE=FirstT.t.GetPlaceID_OnTC
		Info_FT.T_Speed=T_Speed
		Info_FT.P_Speed=P_Speed
		If P_Speed<>0 Then
			Info_FT.Dr = IntToS(MT_Get_SpindleDirection(Next_TCB_T,P_Speed))
			Info_FT.Dz = IntToS(Abs(MT_Get_SpindleSpeed(Next_TCB_T,P_Speed)))
		Else
			Info_FT.Dr=0
			Info_FT.Dz=0
		End If
		Info_FT.MaxRotSpeed=TCB_T.t.MaxRotSpeed
		Info_FT.AddMx=AddMx
		Info_FT.AddMy=AddMy
		Info_FT.AddMz=AddMz
		Info_FT.SPVX=SPVX
		Info_FT.SPVY=SPVY
		Info_FT.SPVZ=SPVZ
		Info_FT.DoIt=1
	Else
		Info_FT.BoxNo=BoxNo
		Info_FT.AggNo=AggNo
		Info_FT.HeadID=HeadID
		Info_FT.TC_PLACE=-9999
		Info_FT.T_Speed=T_Speed
		Info_FT.P_Speed=P_Speed
		Info_FT.Dr = 0
		Info_FT.Dz = 0
		Info_FT.MaxRotSpeed=0
		Info_FT.AddMx=AddMx
		Info_FT.AddMy=AddMy
		Info_FT.AddMz=AddMz
		Info_FT.SPVX=SPVX
		Info_FT.SPVY=SPVY
		Info_FT.SPVZ=SPVZ
		Info_FT.DoIt=0
	End If
	Info_TCBT=Info_FT
End Sub


Sub NC_Start(NCName,NCExt,TDB,FX,FY,FZ,Comment,Add_X,Add_Y,Add_Z)
    'open file and write NC-start
	If is_WorkC_OptionBit(6,JobPara.WorkC_OptionBit) Then
		' 6. Bit M50 wenn mit A-Achse gearbeitet wird		
		MsgBox("Used Pins Up at End")
	End If
    
    If UCase(NCName) = "FIELD12" Then
    	NCName = "FIELD1"
    End If
    Marker.FirstT=True
    NCNameGlobal=NCName
   	JobPara.NPX=Add_X   ' G54 Nullpunkt X
   	JobPara.NPY=Add_Y   ' G54 Nullpunkt Y
   	JobPara.NPZ=Add_Z   ' G54 Nullpunkt Z
    
    If Add_Z <=0 Then
	    'MsgBox("Achtung - keine Saugerhoehe definiert")
	End If
    
    'PPSettings
    PostSettings.NCFileNames=ncpathGlobal+NCName+NCExt
    'WriteStrPP_ini("NC","REALNCNAME",ncpathGlobal+NCName+NCExt)
    FileOpen(NCName+NCExt)
    
    Call SaveFinishedPart(FX,FY,FZ)
   	Call wcncHeader(NCName+NCExt,TDB,FX,FY,FZ,Comment,Add_X,Add_Y,Add_Z)
End Sub


'Sub ToolChange(BoxNo,d1,d2,d3,d4,d5,d6,d7,d8,d9,tspeed,pspeed,d12,d13,d14,d15,d16,d17,d18,d19,d20,d21,d22,d23,d24,d25,d26,d27,d28,d29,d30,d31,d32,d33)
Sub ToolChange(BoxNo,d1,d2,d3,d4,d5,d6,d7,d8,d9,tspeed,pspeed,d12,d13,d14,d15,d16,d17,d18,d19,d20,d21,d22,d23)',d24,d25,d26,d27,d28,d29,d30,d31,d32,d33)
Dim Dummy As Object
Dim bmcode As TBMuster
Dim	GB_TC_Output As Boolean   ' Wechsel von Ausgang zu Ausgang
Dim ZentrumZ As Double
Dim DrillHeadMotorOn,DrillHeadDown As Variant
Dim isok As Boolean

	PPara.Speed = pspeed
	Marker.LastSpeed = -99999   

	'WCNC("**************TOOLCHANGE************START")
	'Abschalten Haube wenn Haube Aktiv
	If Haube.pos > 0 Then 'Or Haube_NCI244=True Then
		'If Haube.P5AchsUseit And Haube.P5AchsTc=True Then
		'	Haube.P5AchsTc=True
		'ElseIf Haube.P5AchsUseit Then
		'	Haube.P5AchsTc=False
		'End If
		'If Haube.P3AchsUseit And Haube.P3AchsTc=True Then
		'	Haube.P3AchsTc=True
		'ElseIf Haube.P3AchsUseit Then
		'	Haube.P3AchsTc=False
		'End If
		Haube.pos=-1
		'Prüfen ob die Haube zurück gestezt werden muss
		Haube.P3AchsTc=True
		Haube.P5AchsTc=True
		Haube.PDHTc=True
		Haube.PLeitblechTc=True
		Call CheckHaube
		 		
 		If Haube.NewHaubePosBeforeTC<2 Then
 			'Haube.pos
			'Haube.IsEbene0
			Haube.P3AchsUseIt=False
			Haube.P5AchsUseIt=False
			Haube.PDHUseIt=False
			Haube.P3AchsAktiv=False
			Haube.P5AchsAktiv=False
			Haube.PDHAktiv=False
			Haube.P3AchsPos=0
			Haube.P5AchsPos=0
			Haube.PDHPos=0
			Haube.P3AchsLastPos=0
			Haube.P5AchsLastPos=0
			Haube.PDHLastPos=0
			Haube.P3AchsAuto=0
			Haube.P5AchsAuto=False
			Haube.PDHAuto=False
			Haube.P3AchsTc=False
			Haube.P5AchsTc=False
			Haube.PDHTc=False
			Haube.P3AchsRetreat=False
			Haube.PLeitBlechUseIT=False 
			Haube.PLeitblechAktiv=False
			Haube.PLeitblechPos=0
			Haube.PleitblechDist=0
			Haube.PLeitblechLastPos=0
			Haube.PleitblechLastDist=0
			Haube.PLeitblechTc=False
 			Haube.NewHaubePosBeforeTC=-1
 		End If
 		
 	
		'Haube.P3AchsTc=False
		'Haube.P5AchsTc=False
	Else
		'Haube.NewHaubePosBeforeTC=-1
		If Haube.NewHaubePosBeforeTC<2 Then
 			'Haube.pos
			'Haube.IsEbene0
			Haube.P3AchsUseIt=False
			Haube.P5AchsUseIt=False
			Haube.PDHUseIt=False
			Haube.P3AchsAktiv=False
			Haube.P5AchsAktiv=False
			Haube.PDHAktiv=False
			Haube.P3AchsPos=0
			Haube.P5AchsPos=0
			Haube.PDHPos=0
			Haube.P3AchsLastPos=0
			Haube.P5AchsLastPos=0
			Haube.PDHLastPos=0
			Haube.P3AchsAuto=0
			Haube.P5AchsAuto=False
			Haube.PDHAuto=False
			Haube.P3AchsTc=False
			Haube.P5AchsTc=False
			Haube.PDHTc=False
			Haube.P3AchsRetreat=False
			Haube.PLeitBlechUseIT=False 
			Haube.PLeitblechAktiv=False
			Haube.PLeitblechPos=0
			Haube.PleitblechDist=0
			Haube.PLeitblechLastPos=0
			Haube.PleitblechLastDist=0
			Haube.PLeitblechTc=False
 			Haube.NewHaubePosBeforeTC=-1
 		End If
	End If

	' Neu MW 12.06.2006
	' Sägen-Merker zurücksetzen..
	MarkerSawingReset

	GB_TC_Output = False   ' Wechsel von Ausgang zu Ausgang
	
	If MT_GB_Output_Changed(ActT,LastT) Then
		AddHint("letztes Werkzeug: "+LastT.aggname+" GB Tool:"+ftos(LastT.gb.ToolNo))
		AddHint("Gleiches Aggregat - kein zurückziehen notwendig")
		AddHint("jetzt Werkzeug: "+ActT.aggname+" GB Tool:"+ftos(ActT.gb.ToolNo))
	End If

	' letztes benutztes Werkzeug auf Lastt schreiben
	If Not ActT.t Is Nothing Then
		Set LastT.t = TDATA.GetTool_ID(ActT.T.ID)
		Set Dummy = LastT.T
		
		Set LastT.t_dh = Dummy
		Set LastT.t_dhsaw = Dummy
		' Neu MW 22.10.2007 
		' Gearboxtool - daten
		Set lastt.T_GB = Dummy
		' Neu MW 22.10.2007 
		' Schneiden Daten
		Set lastt.T_Cedge = actt.t_cedge
		'NEU MW 2.6.2005
		
	Set LASTT.H = TDATA.GetProcessHead_ID(ACTT.HId)
	If LASTT.T.ObjectType=htokStandardTool Then	
		' Zusatzinfos aus Hauptspindel setzen
		Set_H_Additions(LASTT,LASTT.h.Additions)
	Else
		'Set_H_Additions(LASTT,LASTT.h.Additions)
	End If
        'Set LASTT.H =dummy
		' Neu MW 22.03.2005
		' Gearbox und 
		' --------------------------------
		If MT_IsGearBoxTool(LastT) Or MT_IsGearBoxTool_Special(LastT) Then
			Set LastT.gb = Dummy.GearBox
		End If
		Set LastT.t_gb = Dummy
		' --------------------------------
		
		LastT.HId = ActT.HId
		LastT.aggname = ActT.aggname
	Else
		If Not LastT.t Is Nothing Then
			Set LastT.t = Nothing
		End If
	End If

	' Muss vor der Werkzeugabwahl stehen, damit Werkzeugabwahl weiss, dass z.B. Spindel ausgeschaltet werden
	' muss
	If BoxNo > 0 Then
		MT_SetTHopsBasicToolExt(ActT,BoxNo,HeadID)
	End If
	
	
	' Werkzeugabwahl 
	MT_Tool_Re_Change(LastT,BoxNo)
	
	If BoxNo<0 Then
		' nur abwahl am Schluss
		Exit Sub
	End If
	

	
	
	
	If Not ActT.T.IsInActConf Then
		AddMistake("Schwerwiegender Fehler - Werkzeug "+ActT.T.Description +".. ist nicht gerüstet! Agg:"+ActT.aggname)
	End If
	
	If MT_isSpecialToolKind_Printer(ActT.t) Then 
		' Printer ÜBERLESEN
		'Exit Sub
	End If
	
	If MT_isSpecialToolKind_Laser(ActT.t) Then 
		' LASER ÜBERLESEN
		'Exit Sub
	End If
	
	' Auf sicherheit, da nach bohren und anschliessender Bearbeitung
	' mit HS sonst nicht hochgefahren wird
	If Not Firsttime_Viewchange Then
		Z_Is_Safety=False
	End If
	
	If MT_isDH_wasDH(ActT,LastT) Then
		' war ist Bohrkopf nicht hochfahren
		' und keine WEchsel von Bohrkopf Sägen auf Bohrkopf bohren 
	Else
		If Not MT_GB_Output_Changed(ActT,LastT) And Not MT_TEdgeChange(ActT,LastT) Or (Actt.HId<>LasTt.HId) Then
			Z_Is_Safety=False
			wSafetyAbs(Z_Is_Safety)
			If Not LastT.t Is Nothing Then
				
				If MT_Is_Vertical_StandardTool5Axis(LAStT) Then
					' 5-Achs 
					'wcnc("G153 G0 "+LASTT.PH_Add.TipAxisName+"=0 "+ LAStT.PH_Add.RotAxisName+"="+FToS(ACtT.PH_Add.Haube3AchsCPos))
					wcnc("G153 G0 B=0 C="+FToS(ACtT.H_Add.Haube3AchsCPos))
					'AddMistake("Check Function")
				ElseIf MT_Is_Vertical_Rot_Axis(LAStT) Then
					'wcnc("G153 G0 "+LAStT.PH_Add.RotAxisName+"="+FToS(ACtT.PH_Add.Haube3AchsCPos))
					wcnc("G153 G0 C="+FToS(ACtT.H_Add.Haube3AchsCPos))
					'AddMistake("Check Function")
				End If
			End If
			'If MT_Is_Vertical_StandardTool5Axis(ACTT) Then
			If MT_Is_Vertical_StandardTool5Axis(ACTT) Then
				' 5-Achs 
				'wcnc("G153 G0 "+ACTT.PH_Add.TipAxisName+"=0 "+ ACtT.PH_Add.RotAxisName+"="+FToS(ACtT.PH_Add.Haube3AchsCPos))
			End If
			' Neu MW 07.07.2005 - dann ist auch Sicherheit übers 
			' Werkstück gewährleistet, -> Problem durch Toolchange wird auch 
			' der ToolCarr zurückgesetzt
			Z_Is_SafetyPart=True
			
		Else
			wSafetyPart
		End If
		ResetActV	
	End If
	
	
	Marker.Last_Liftpos = -9999
	Marker.LiftPos_Startup = -1
	Marker.Last_Bm.BM1 =0
	Marker.Last_Bm.BM2 =0
	Marker.Last_Bm.BM3 =0
	Marker.last_bm.GroupCode=0
	
	' OS 02.05.2013 Neue Schwenklogik Marker Setezen ----------------------------- * Start
	' 0=AUS/ALT 1=DYNAMISCH 2=ZMAX
	
	' OS 02.05.2013 Neue Schwenklogik Marker Setezen ----------------------------- * End
	
	' prepare all Aggregats with it's first tool except the Aggregat which is used now
	If Firsttime_Viewchange Then
		If TDATA.GetProcessHeadList_TC.Count > 0 Then   			' count of Processheads with toolchange access
			' only necessary if less 1 TC- Head
			'MT_Fill_All_TC_Tools(ActT)
		End If
	End If


	If Not MT_isDH(ActT) And (MT_Is_TC_T(ActT)) Then
		' Toolchange call except drilling head
		'wcncCom("ToolChange :"+ActT.tc.Description)
		'wcnccom(ActT.aggname)
		
		wcncCom(ActT.T.Description+" "+ " ID:"+inttos(ActT.T.ID)+" Platz:"+ inttos(ActT.t.GetPlaceID_OnTC)+" T:"+inttos(ActT.T.ToolNo))
		
		If Not lastt.t Is Nothing Then
			If MT_IsGearBoxTool(actt) And MT_IsGearBoxTool(lastt) Then
				' 24.10.2007 MW Unterdruecken Werkzeugaufruf wenn sich 
				' Spindeldrehzahl bzw. Rot-Richtung nicht aendert
				If (actt.t.GetPlaceID_OnTC=lastt.t.GetPlaceID_OnTC) And _
					(actt.T_CEdge.RotSpeed = lastt.T_CEdge.RotSpeed) And _
					(actt.T_CEdge.RotDirection = lastt.T_CEdge.RotDirection)And(aCTT.HId=lASTT.HId) Then
					' Werkzeugwechsel - Aufruf nicht notwendig
				Else
					MT_WZW(pspeed)
				End If
			Else
			   MT_WZW(pspeed)
			End If
		Else
			MT_WZW(pspeed)
		End If
		wcnc("STOPRE")	
		wcncaddcom("$TC_DP1["+inttos(ActT.h_add.ToolNo)+","+inttos(ActT.h_add.CorrNo)+"]=120"," Typ")
		wcncaddcom("$TC_DP6["+inttos(ActT.h_add.ToolNo)+","+inttos(ActT.h_add.CorrNo)+"]="+ftos(ActT.t.Radius)," Radius")
		wcncaddcom("$TC_DP7["+inttos(ActT.h_add.ToolNo)+","+inttos(ActT.h_add.CorrNo)+"]="+ftos(ActT.t.MaxLength)," cOLLIsIONSLAENGE")
		wcncaddcom("$TC_DP8["+inttos(ActT.h_add.ToolNo)+","+inttos(ActT.h_add.CorrNo)+"]="+ftos(ActT.t.CollRadius)," COLLISIONSRADIUS")
		' Neu MW 3.6.2005
		' Verschleiss und Basismass Nullen
		If (ActT.H_Add.traori) Then
			Verschleiss_BasismassNullen(IntToS(ActT.h_add.ToolNo),IntToS(actt.h_add.CorrNo))
		End If
		
		If (actt.H_Add.Traori) Or Not (MT_Is_Vertical_StandardTool5Axis(actt)) Then
			' Länge auf Korrekturdaten schreiben
			' für 5- Achs verrechnet TRAORI korrekt
			wcncAddCom("$TC_DP5["+IntToS(ActT.h_add.ToolNo)+","+IntToS(actt.h_add.CorrNo)+"]=0","LÄNGE 3")  
			wcncAddCom("$TC_DP4["+IntToS(ActT.h_add.ToolNo)+","+IntToS(actt.h_add.CorrNo)+"]=0","LÄNGE 2")  
			'If tm_bg.activ And MT_IsGearBoxTool(actt) Then
			'	ZentrumZ = actt.gb.CenterZ
			'Else
				ZentrumZ = 0
			'End If
			wcncaddcom("$TC_DP3["+inttos(ActT.h_add.ToolNo)+","+inttos(actt.h_add.CorrNo)+"]="+ftos(actt.t.Length-ZentrumZ)," Länge")
			wcnc("STOPRE")	

            ' toCheck OS/MW - jetzt erst im ViewChange
		Else
			' kein Traori
			' spezielle Längenverrechnung
			' Pivot-Point - Mass wird im Viewchange verrechnet und auf Länge 1, Länge 2, Länge 3 geschrieben
		End If
		If ActT.h_add.MCorrNo>0 Then
			If Not MT_IsAnyGearboxTool(Actt) Then
			'If PPara.PreObjectTyp = otMilling Or PPara.PreObjectTyp=otMillingMPs Or PPara.PreObjectTyp=otMillingMPs Or PPara.PreObjectTyp=otMillingPoints Or PPara.PreObjectTyp=otVertDrilling Or PPara.PreObjectTyp=otHorzDrilling Then
				WCNC("C_CHECKTOOL("+FTOS(ActT.h_add.MLTolCorr)+","+FTOS(ActT.h_add.MRTolCorr)+")")
				wcncaddcom("$TC_DP3["+inttos(ActT.h_add.ToolNo)+","+inttos(ActT.h_add.CorrNo)+"]=$TC_DP3["+inttos(ActT.h_add.ToolNo)+","+inttos(ActT.h_add.MCorrNo)+"]" ,"Laenge")
				wcncaddcom("$TC_DP6["+inttos(ActT.h_add.ToolNo)+","+inttos(ActT.h_add.CorrNo)+"]=$TC_DP6["+inttos(ActT.h_add.ToolNo)+","+inttos(ActT.h_add.MCorrNo)+"]" ,"Radius")
				WCNC("STOPRE")
			End If
		End If
		If (actt.PH_Add.Traori) Then
		    wcnc(actt.PH_Add.TraoriOff)  '  "TRAORI"
		End If
	ElseIf MT_isDHSaw(ActT) Then
		' Säge auf Bohrkopf
		If MT_isDH_wasDH(ActT,LastT) Then
			' war ist Bohrkopf kein Wechsel aufrufen
			' und keine WEchsel von Bohrkopf Sägen auf Bohrkopf bohren 
		Else
			MT_WZW(pspeed)
		End If
		'MT_Write_Speed(actt,pspeed)
		' NutSäge auf Bohrkopf 
		
		
	ElseIf MT_isDH(ActT) Then
	
		' Neu MW 08.03.2006
		' 5-Achs - Kopf auf horizontale Stellung, um den Arbeitsbereich des 
		' Bohrkopfes zu erhöhen geht aber auch nur bis zu einem gewissen Werkzeugdurchmesser bzw.
		' Werkstückdicke
		' OS wERKZEUG VOR BOHREN ABLEGEN
		wcncaddcom("G153 "+G0+" "+Tip_Axis_ToS(0)+" "+Rot_Axis_ToS(0),"safety pos For Drilling")
		If Trim(Actt.H_Add.ToolCheckForDrillhead)="" Then
			WCNC(GToolChangeCycleName+"(0,0,0)")
		Else
			WCNC(Actt.H_Add.ToolCheckForDrillhead)
		End If
		
	
		' Bohrkopf
		' MT_WZW(pspeed)
		'MT_Write_Speed(actt,pspeed)
		' Einschalten
		If MT_get_Add_ID(actt,10049,isok)=1 Then 
			DrillHeadMotorOn = MT_get_Add_ID(actt,10050,isok)
		ElseIf MT_get_Add_ID(actt,10049,isok)=2 Then 
			DrillHeadMotorOn = MT_get_Add_ID(actt,10050,isok)+"="+inttos(Abs(MT_Get_SpindleSpeed(actt,pspeed)))
		Else
			AddMistake("Drilhead on not defined in para: 10049!")
		End If
		
		If isok Then
			wcncaddcom(DrillHeadMotorOn,"DrillHeadMotorOn")
		Else
			AddMistake("234992383")
		End If

		
		WCNC("STOPRE")
		WCNC("G4 F.1")
		DrillHeadDown = MT_get_Add_ID(actt,10054,isok)
		If isok Then
			wcncaddcom(DrillHeadDown,"DrillHeadDown")
		Else
			AddMistake("234992382343")
		End If
		
	ElseIf MT_isPneumaticSaw(ActT) Then
		' Säge pneumatisch schwenkbar
		If MT_isDH_wasPneumaticSaw(actt,lastt) Then
			' war vorher bereits pneumatische Säge - keine Werkzeugwechsel
		Else
			MT_WZW(pspeed)
		End If
		'MT_Write_Speed(actt,pspeed)
	ElseIf MT_IsSpecialToolKind_Printer(ActT.t) Then
	
	
		MT_WZW(pspeed)
		
		MT_Write_Act_D_Correction
		
	Else
		AddMistake("Toolchange - Werkzeug Typ noch nicht berücksichtigt")
		' kein Bohr
		MT_WZW(pspeed)
		' necessary ?
		MT_Write_Act_D_Correction
		'MT_Write_Speed(actt,pspeed)
	
	End If
	'WEGEN TRAFOFF
	SET_Zero(False,"",0,0,0,0,0,0,False,False)
	'wcnc("G54")
	
	'Setzen des Haubenflags
	Haube.pos = MT_Get_HaubenPos
	
	If MT_IsGearBoxTool(ActT) Or MT_IsGearBoxTool_Special(ActT) Or MT_IsGearBoxTool_5thAxis(ActT) Then	
		wcnccom("Werkzeugträgerkorrektur - Verrechnung! ")
	End If
	
	
	Marker.FirstT=False
	'WCNC("**************TOOLCHANGE************END")
End Sub


'Sub ToolChangeBefore(BoxNo,d1,d2,d3,d4,d5,AggNo,d7,d8,d9,d10,d11,d12,d13,d14,d15,d16,d17,d18,d19,d20,d21,d22,d23,d24,d25,d26,d27,d28,d29,d30,d31,d32,d33,d34,d35,d36,d37,d38)
Sub ToolChangeBefore(BoxNo,ToolName,ToolTypStr,ToolType,ToolNo,CorrNo,AggNo,Feedrate,I_Feedrate,S_Feedrate,T_Speed,P_Speed,SawThickness,Safety_Horiz,Safety_Z,Radius,Length,StartFactor,AddMx,AddMy,AddMz,RotA,TipA,SPVX,SPVY,SPVZ,Vzx,Vzy,Vzz)

Dim t As IIHopsBasicTool   ' Die Mutter der O-Typen 1-4 hierüber  können alle Standard - Eigenschaften abgerufen werden
Dim PTC As Boolean
Dim Next_TCB_T As THopsBasicToolExt



	MT_SetTHopsBasicToolExt(Next_TCB_T,BoxNo,HeadID)
	Set Next_TCB_T.t = TDATA.GetTool_ID(BoxNo)
	Set t= TDATA.GetTool_ID(BoxNo)
	Set TCB_T.t = TDATA.GetTool_ID(BoxNo)
	
	If MT_Is_TC_T(Next_TCB_T) Then
		Info_TCBT.BoxNo=BoxNo
		Info_TCBT.AggNo=AggNo
		Info_TCBT.HeadID=HeadID
		Info_TCBT.TC_PLACE=TCB_T.t.GetPlaceID_OnTC
		Info_TCBT.T_Speed=T_Speed
		Info_TCBT.P_Speed=P_Speed
		If P_Speed<>0 Then
			Info_TCBT.Dr = IntToS(MT_Get_SpindleDirection(Next_TCB_T,P_Speed))
			Info_TCBT.Dz = IntToS(Abs(MT_Get_SpindleSpeed(Next_TCB_T,P_Speed)))
		Else
			Info_TCBT.Dr=0
			Info_TCBT.Dz=0
		End If
		Info_TCBT.MaxRotSpeed=TCB_T.t.MaxRotSpeed
		Info_TCBT.AddMx=AddMx
		Info_TCBT.AddMy=AddMy
		Info_TCBT.AddMz=AddMz
		Info_TCBT.SPVX=SPVX
		Info_TCBT.SPVY=SPVY
		Info_TCBT.SPVZ=SPVZ
		Info_TCBT.DoIt=1
	Else
		Info_TCBT.BoxNo=BoxNo
		Info_TCBT.AggNo=AggNo
		Info_TCBT.HeadID=HeadID
		Info_TCBT.TC_PLACE=-9999
		Info_TCBT.T_Speed=T_Speed
		Info_TCBT.P_Speed=P_Speed
		Info_TCBT.Dr = 0
		Info_TCBT.Dz = 0
		Info_TCBT.MaxRotSpeed=0
		Info_TCBT.AddMx=AddMx
		Info_TCBT.AddMy=AddMy
		Info_TCBT.AddMz=AddMz
		Info_TCBT.SPVX=SPVX
		Info_TCBT.SPVY=SPVY
		Info_TCBT.SPVZ=SPVZ
		Info_TCBT.DoIt=0
	End If
	
		If Info_TCBT.DoIt=1 Then
		 'TH1.BoxNo
		 'TH
		
		End If
		

	
	
	If MT_isSpecialToolKind_Laser(t) Then 
		' LASER ÜBERLESEN
		Exit Sub
	End If
	
	'If (Not(TCB_T.t)Is Nothing) Then
	'	
	'	If Not(MT_Is_TC_T(TCB_T)) And (MT_Is_TC_T(Next_TCB_T)) Then 
	'		PTC=False
	'		If Not(Actt.t)Is Nothing Then
	'			If Actt.t.ToolNo<>Next_TCB_T.t.ToolNo Then 
	'				PTC=True
	'			End If
	'		End If
	'	Else
	'		PTC=False
	'	End If
		
	'Else
	'	If Not(MT_Is_TC_T(Firstt)) And MT_Is_TC_T(Next_TCB_T) Then
	'		PTC=True
	'	Else
	'		PTC=False
	'	End If
		
	'End If
	
	
	' Object merken für Vorwechsel
	
	
	'If PTC=True Then
	'	WCNC("C_VORWECHSEL("+Inttos(TCB_T.t.GetPlaceID_OnTC)+")")
	'End If
	
	
	Marker.NextHid=HeadID	
End Sub

Sub ViewChange(View,LastView,IPX,IPY,IPZ,RotA#,TipA#,SPAX,SPAY,SPAZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)

	
	'WCNC("**************View CHANGE************Start")
	wcnc_Workpiece_Info
	
	If ActT.T.ToolType=1000 Then 
		' LASER ÜBERLESEN
		Exit Sub
	End If
	LastV=ActV
	
	Call ViewSave(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPAX,SPAY,SPAZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
	
	PosReset
	
   	If MT_isDH(ActT) Then
	   Marker.Last_DH_Process=""
   	   DH_View0= ActV
   	   Exit Sub     ' !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   		' Ebenenwechsel - Abhandlung erst beim bohren selber
     	'wcncCom("Viewchange Bohrkopf View "+View)
     	'If Not ViewEqual Then
       		'set view: if last view isn't equal (actual view) 
       		' nicht notwendig
       	'	Call wcncViewChange_DH(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPaX,SPaY,SPaZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
    	'End If
     	'wcncCom("ViewchangeEnd Bohrkopf ")		
	End If
   	
	wcncCom("Viewchange View "+View)
	
		'Hauben status schreiben
	Haube.pos = MT_Get_HaubenPos
	
	If Haube.pos > 0 Then
    	If ActV.View = 0 And (Not PPara.MMode=1) And (Not PPara.MMode=2) And (Not(MT_IsGearBoxTool(Actt) Or MT_IsGearBoxTool_Special(Actt)))Then 
    		Haube.IsEbene0 = True
    		Haube.pos = MT_Get_HaubenPos
    	ElseIf ActV.View>0 And (Not PPara.MMode=1) And (Not PPara.MMode=2) And (Not(MT_IsGearBoxTool(Actt) Or MT_IsGearBoxTool_Special(Actt))) Then
    		Haube.IsEbene0 = True
    		Haube.pos = MT_Get_HaubenPos
    	ElseIf ((PPara.MMode=1) Or (PPara.MMode=2)) And (Not(MT_IsGearBoxTool(Actt) Or MT_IsGearBoxTool_Special(Actt))) Then
    		If Actt.H_Add.HaubeTyp5Achs=4 Then
    			Haube.IsEbene0 = True
    			Haube.pos = MT_Get_HaubenPos
    		ElseIf Actt.H_Add.HaubeTyp5Achs=5 And (PPara.MMode=1)Then
    			Haube.IsEbene0 = True
    			Haube.pos = MT_Get_HaubenPos
    		Else
    			Haube.IsEbene0 = False
    			Haube.pos=-1
    		End If
    	Else
    		Haube.IsEbene0 = False
    		Haube.pos=-1
    	End If
    End If
	
	'Haube ggf. vor oder zurücklegen
	Call CheckHaube

	If ((PPara.MMode=1) Or MT_IsSpecialToolKind_Printer(ActT.t)) And (ActV.View<>0) Then
	   ' // Check für Mehrspindiger Bohrgetriebe In Hauptspindel
	   ' darf nur vertikal bearbeiten
	   AddMistake("Bearbeitung mit "+ActT.T.ToolName +" auf Ebene"+inttos(ActV.View) + " nicht möglich")
	
	End If
	
	' Tx Dx
	' toCheck OS/MW  erst im DLL-Milling
	If (actt.H_Add.Traori) Or Not (MT_Is_Vertical_StandardTool5Axis(actt)) Then
		MT_Write_Call_Correction
		If (actt.H_Add.Traori) Then
	        wcnc(actt.H_Add.TraoriOn)  '  "TRAORI"
		End If
		'WEGEN TRAFOFF
		SET_Zero(False,"",0,0,0,0,0,0,False,False)
	End If
		
	Call wcncViewChange(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPAX,SPAY,SPAZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
	
		If MT_Is_Vertical_StandardTool(ActT) Then
			' 4-Achs
			' vertical aggs with or without rotation axis "C"
'			Call wcncViewChange(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPAX,SPAY,SPAZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
			
		ElseIf MT_Is_Vertical_StandardTool5Axis(ActT) Then

			
		
		ElseIf MT_Is_Vertical_Rot_Axis(ActT) And MT_IsGearBoxTool(ActT) Then
		
'			Call wcncViewChange_GB(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPAX,SPAY,SPAZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
			
		ElseIf MT_IsGearBoxTool_5thAxis(ActT) Then
		
			' ----------------------------------------------		
			' GB with 5th axis
			
	   	ElseIf MT_isDHSaw(ActT) Or MT_isPneumaticSaw(ActT) Then
'			wcncCom("Viewchange View "+View)
	   	
'			Call wcncViewChange_SawFix(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPAX,SPAY,SPAZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
		ElseIf MT_IsGearBoxTool(ActT) Then
		
'			Call wcncViewChange_GB(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPAX,SPAY,SPAZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
		ElseIf MT_IsSpecialToolKind_Printer(ActT.t) Then	
			Call wcncViewChangePrinter(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPAX,SPAY,SPAZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
		ElseIf MT_Is_Vertical_Rot_Axis(ActT) And MT_IsGearBoxTool_Special(ActT) Then
'			Call wcncViewChange_GB(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPAX,SPAY,SPAZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
		Else 
		
'			AddMistake("bad error in Viewchange ") 
'			Call wcncViewChange(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPAX,SPAY,SPAZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
		End If
'	End If
	wcncCom("ViewchangeEnd")
	'If ActV.View<>0 Then
	Z_Is_Safety=False
	'End If
	' important sonst wird keine Sicherheit zwischen Ebenenwechsel gefahren
	Z_Is_SafetyPart=False

    Firsttime_Viewchange = False
    Marker.CPREC=0
	'WCNC("**************View CHANGE************END")
End Sub

Sub DistanceToOutLine(Value)
	If Not equal(Value,0) Then
		pp_err(0,"Distance to outline <>0")
	End If
End Sub

Sub Start_Milling(PNo,TRC,StartMove,StartFactor,I_Feedrate,Feedrate,S_Feedrate,speed,PPVX,PPVY,PPVZ,PPAX,PPAY,PPAZ,RotA,TipA,TAngle,Start_End_MoveReady)
'	Dim fraestiefe As Double
Dim test As Double
Dim isok As Boolean 
Dim d As IIHopsBasicTool

	Marker.PNo = PNo
	Call PosSet(LastPosAbs, PPAX,PPAY,PPAZ)  ' MW 26.02.2013  -> Merker für Max Z
	Get_AktHK(2,0,True)
	'Call CheckHaube
		
	
	If Not equal(PPara.Speed,speed) Then
		MT_Write_Speed(ActT,speed)
		PPara.Speed = speed
	End If

	PosReset
	MoveParaReset
	MT_Write_Check_Spindle
	
	'wcnc("FGROUP(X,Y,Z,C)")
	' **************************************************************
	' **************************************************************
    If MT_isDHSaw(actt) Then
		wcncCom("--  Groove saw - sawing/milling ")
		' ----------------------------------------------------
		' -- hier Bohrspindeln/Säge vorlegen
		' -- Bohrkopf - Säge
		' ----------------------------------------------------
		'Aufruf fehlt MM
		MT_WRITE_DHCode(ActT,ActT.t_dhsaw.DH_ToolPlace.ToolNo)
	ElseIf MT_Is_UndersideTool(ActT) Then
		wcncCom("****** Unterflurfräsen ****")
	
		' --
		' -- Unterflur-Getriebe
		' Berechnung der Ebenenausrichtung anhand von Tangle und der aktuell eingestellten Ebene
		' --
		MT_Underside_Set_Param_Angle(ActT,TAngle)
		' --
		' --
	
		' Korrektur aufrufen, und offsets setzen
		'MT_Write_Call_Correction
		' mit C-Achse
		'wcnc(G0+MoveUs(PPVX,PPVY,PPVZ,MovePara.Feedrate,TRC)+GetHeadAngles_GB(UndersideTool.dw))
		'wcnc(G0+Move(PPVX,PPVY,PPVZ,MovePara.Feedrate,TRC)+GetHeadAngles_GB(UndersideTool.dw)+MT_Write_DustCover(PPAZ))
	ElseIf MT_IsGearBoxTool(actt) Then
		If actt.t_gb.Tool.ToolType = tSaw Then
			wcncCom("--")
			wcncCom("--  sawing / milling ")
			wcncCom("--")
		Else
			wcncCom("--")
			wcncCom("--  milling ")
			wcncCom("--")
		End If	
	Else
		wcncCom("--")
		wcncCom("--  Milling ")
		wcncCom("--")
	End If
	' Standard
	
'	wcnc(G0+Move(PPVX,PPVY,PPVZ,MovePara.Feedrate,TRC))
	
	
	If SpindleBlowNozzle.Blow Then
		Call SetBlasen()
	End If
	
	If SawBlowNozzle.Blow Then
		Call SetBlasenSaw()
	End If
	
	If (MT_Is_Vertical_StandardTool5Axis(Actt)Or MT_Is_Vertical_StandardTool(Actt) Or MT_IsGearboxTool(Actt)) Then
		If MT_get_Add_ID(actt,10201,isok)=1 Then
			Marker.CPREC=1
			'wcnc("")
		ElseIf MT_get_Add_ID(actt,10201,isok)=2 Then
			Marker.CPREC=11
		Else
			Marker.CPREC=0
		End If
	End If
	
End Sub

Sub G00(PPVX,PPVY,PPVZ,PPAX,PPAY,PPAZ,Feedrate,speed,RotA,TipA,TRC,TAngle)
Dim ZKorr_ As Long
	Call PosSet(LastPosAbs, PPAX,PPAY,PPAZ)  ' MW 26.02.2013  -> Merker für Max Z
    'ZKorr_=Marker.Zkorr
    'Marker.Zkorr=0
'    If EndMoveActive And Marker.CPREC=2 Then
'    	Marker.CPREC=3
'    ElseIf EndMoveActive And Marker.CPREC=12 Then
'    	Marker.CPREC=13
'    End If
    
    wcnc(G0+Move5(PPVX,PPVY,PPVZ,RotA,TipA,MovePara.Feedrate,TRC))
    'Marker.Zkorr=ZKorr_
End Sub

Sub G01(PPVX,PPVY,PPVZ,PPAX,PPAY,PPAZ,Feedrate,speed,RotA,TipA,TRC,TAngle)

	Call PosSet(LastPosAbs, PPAX,PPAY,PPAZ)  ' MW 26.02.2013  -> Merker für Max Z
    wcnc(G1+Move5(PPVX,PPVY,PPVZ,RotA,TipA,Feedrate,TRC))
End Sub

Sub G02(PPVX,PPVY,PPVZ,CVI,CVJ,RCVI,RCVJ,PPAX,PPAY,PPAZ,CAI,CAJ,CAK,RCAI,RCAJ,RCAK,radius,Feedrate,speed,RotA,TipA,TRC,TAngleB,TAngleE)

	Call PosSet(LastPosAbs, PPAX,PPAY,PPAZ)  ' MW 26.02.2013  -> Merker für Max Z
	' Neu MW 12.05.2004
	If (MovePara.TRC<>TRC) Then
		AddMistake(GetErrMsg(106,"_Werkzeugradiuskompensation wird von Maschine nicht unterstützt!",0)+ " G2")
	End If
	
	wcnc(G2+Move5(PPVX,PPVY,PPVZ,RotA,TipA,Feedrate,TRC)+IJToS(RCVI,RCVJ,radius))

	
End Sub

Sub G03(PPVX,PPVY,PPVZ,CVI,CVJ,RCVI,RCVJ,PPAX,PPAY,PPAZ,CAI,CAJ,CAK,RCAI,RCAJ,RCAK,radius,Feedrate,speed,RotA,TipA,TRC,TAngleB,TAngleE)
	
	Call PosSet(LastPosAbs, PPAX,PPAY,PPAZ)  ' MW 26.02.2013  -> Merker für Max Z
	' Neu MW 12.05.2004
	If (MovePara.TRC<>TRC) Then
		AddMistake(GetErrMsg(106,"_Werkzeugradiuskompensation wird von Maschine nicht unterstützt!",0)+ " G3")
	End If
	
	wcnc(G3+Move5(PPVX,PPVY,PPVZ,RotA,TipA,Feedrate,TRC)+IJToS(RCVI,RCVJ,radius))
End Sub

Sub End_Milling(DMove,DFactor,Retreat,d1,d2,d3)

	If Marker.C_Poly Then
		AddMistake("Drehzahlreglung für Säge ausschalten!")
	End If
	If Marker.CPREC=2 Then
		WCNC("CPRECOF")
		Marker.CPREC=0
	ElseIf Marker.CPREC=12 Then
		WCNC("FFWOF")
		Marker.CPREC=0
	End If
	
	
	End_Continuous_Path_Mode(Retreat)
	
	If ((Retreat=1) And (ActV.View<>0)) Or (MT_Is_undersidetool(actt)) Then
		'Go savety next view isn't equal
		If DMove = 6 Then
			' MW 26.02.13 ohne Z-Sicherheit auch bei "normalen" Fräsbahnen
			'wsafetypart (DMove)
		Else
			'wsafetypart
		End If
	End If
	MarkerSawingReset
	Marker.Viewchangechecked=False
	Marker.LAst_ExhaustPos = 9999
	Retreat_ClampChange=Retreat
	'Measureinfos
	Call RESET_MESSBEZUG
	'Zurücksetzen der Bahnsteuerparameter Os 31.03.2016
	ActHK_ON=""
	ActHK_OFF=""
	Inc_Process   ' ActProcess=ActProcess+1
End Sub

Sub Start_Drilling(PNo,I_Feedrate,Feedrate,S_Feedrate,speed)

	Marker.PNo = PNo
	' Neu MW 20.04.2005
	If Not equal(PPara.Speed,speed) Then
		MT_Write_Speed(ActT,speed)
		PPara.Speed = speed
	End If
	
	I_Feedrate = MT_CheckFeedrate(actt,0,0,0,0,0,0,I_Feedrate)
	Feedrate = MT_CheckFeedrate(actt,0,0,0,0,0,0,Feedrate)
	S_Feedrate = MT_CheckFeedrate(actt,0,0,0,0,0,0,S_Feedrate)
	
	PosReset
	MoveParaReset
	wcncCom("--")
	wcncCom("--      Drilling")
	wcncCom("--")
	MT_Write_Check_Spindle
	
	
End Sub

Sub Drilling(DNo,PPVX,PPVY,PPVZ,PPAX,PPAY,PPAZ,D,Depth,DFlag,Free,ZMax)
Dim Count As Integer
Dim i As Integer
Dim ActDepth As Double
Dim dx As Double
Const DFI=-3
Const DFS=-3
pp_err(0)
'toCheck OS/MW
	If ActT.T.ToolType=-9999999 Then  
		'Ausstechen   
		wcnc(G0+Move(PPVX,PPVY,PPVZ,MovePara.Feedrate,MovePara.TRC))
		wcnc(G1+Move(PPVX,PPVY,0,PPara.Feedrate,MovePara.TRC))
		wcnc("TRANS"+XEqualToS(ActV.IPX)+"+R10"+YEqualToS(ActV.IPY)+"+R11"+ZEqualToS(ActV.IPZ)+"+R12")
		wcnc("AROT "+ZToS(0)+" "+XToS(0))
		wcnc(G1+ZToS(Depth))
		wcnc(G0+ZToS(FinishedPart.Z+PPVZ))
	Else
		' Standardbohren 
'		Call Drilling0(PPVX,PPVY,PPVZ,PPAX,PPAY,PPAZ,D,Depth,DFlag,Free,ZMax)
	End If
End Sub


Sub End_Drilling(Retreat)
	If (Retreat=1) And (ActV.View<>0) Then
		'Go savety next view isn't equal
		wsafetyPart
	End If
	MarkerSawingReset
	Marker.Viewchangechecked=False
	Marker.Last_ExhaustPos = 9999
	Retreat_ClampChange=Retreat
	'Zurücksetzen der Bahnsteuerparameter Os 31.03.2016
	ActHK_ON=""
	ActHK_OFF=""
	Inc_Process   ' ActProcess=ActProcess+1
End Sub

Sub Sawing(PNo,I_Feedrate,Feedrate,S_Feedrate,speed,SPX,SPY,SPZ,EPX,EPY,EPZ,ZRef,TC,Flag,CPSawUnit_PosSX,CPSawUnit_PosSY,CPSawUnit_PosSZ,CPSawUnit_PosRX,CPSawUnit_PosRY,CPSawUnit_PosRZ,CPSawUnit_SPX,CPSawUnit_SPY,CPSawUnit_SPZ,CPSawUnit_EPX,CPSawUnit_EPY,CPSawUnit_EPZ,ViewCPSawUnit_PosSX,ViewCPSawUnit_PosSY,ViewCPSawUnit_PosSZ,ViewCPSawUnit_PosRX,ViewCPSawUnit_PosRY,ViewCPSawUnit_PosRZ,ViewCPSawUnit_SPX,ViewCPSawUnit_SPY,ViewCPSawUnit_SPZ,ViewCPSawUnit_EPX,ViewCPSawUnit_EPY,ViewCPSawUnit_EPZ,Retreat)
	' Neu MW 20.04.2005
	I_Feedrate = MT_CheckFeedrate(actt,0,0,0,0,0,0,I_Feedrate)
	Feedrate = MT_CheckFeedrate(actt,0,0,0,0,0,0,Feedrate)
	S_Feedrate = MT_CheckFeedrate(actt,0,0,0,0,0,0,S_Feedrate)
	Marker.PNo = PNo	
	PosReset
	MoveParaReset

	MT_Write_Check_Spindle
	If MT_isdhsaw(ActT) Then
		' ----------------------------------------------------
		' -- hier Bohrspindeln/Säge vorlegen
		' -- Bohrkopf - Säge
		' ----------------------------------------------------
		
		MT_WRITE_DHCode(ActT,ActT.t_dhsaw.DH_ToolPlace.ToolNo)
	End If
	
	wcncCom("*****************************************")
	wcncCom("*************  Sägen  *******************")
	wcncCom("*****************************************")

	
	'If MT_FixSawingOk(ActT) Then
	'	Call SawingXY_Direction(I_Feedrate,Feedrate,S_Feedrate,speed,SPX,SPY,SPZ,EPX,EPY,EPZ,ZRef,TC,Flag,CPSawUnit_PosSX,CPSawUnit_PosSY,CPSawUnit_PosSZ,CPSawUnit_PosRX,CPSawUnit_PosRY,CPSawUnit_PosRZ,CPSawUnit_SPX,CPSawUnit_SPY,CPSawUnit_SPZ,CPSawUnit_EPX,CPSawUnit_EPY,CPSawUnit_EPZ,ViewCPSawUnit_PosSX,ViewCPSawUnit_PosSY,ViewCPSawUnit_PosSZ,ViewCPSawUnit_PosRX,ViewCPSawUnit_PosRY,ViewCPSawUnit_PosRZ,ViewCPSawUnit_SPX,ViewCPSawUnit_SPY,ViewCPSawUnit_SPZ,ViewCPSawUnit_EPX,ViewCPSawUnit_EPY,ViewCPSawUnit_EPZ,Retreat)
	'Else
		wcnc(G1+Move(ViewCPSawUnit_SPX,ViewCPSawUnit_SPY,ViewCPSawUnit_SPZ,I_Feedrate,MovePara.TRC))
		wcnc(G1+Move(ViewCPSawUnit_EPX,ViewCPSawUnit_EPY,ViewCPSawUnit_EPZ,Feedrate,MovePara.TRC))
		wcnc(G1+Move(ViewCPSawUnit_PosRX,ViewCPSawUnit_PosRY,ViewCPSawUnit_PosRZ,S_Feedrate,MovePara.TRC))
	'End If
	
	MarkerSawing.LastIsSawing=True
	MarkerSawing.LastKW=True
	
	' Neu MW 07.03.2006
	If ((Retreat=1)) Then
		' lastissawing wird gecheckt
		wsafetyPart
	End If
	
	
	Marker.Viewchangechecked=False
	Marker.Last_ExhaustPos = 9999
	Retreat_ClampChange=Retreat
	
End Sub


Sub Start_Vertical_DrillingHead_Stroke(PNo,I_Feedrate,Feedrate,S_Feedrate,speed)

	' Neu MW 20.04.2005
	I_Feedrate = MT_CheckFeedrate(actt,0,0,0,0,0,0,I_Feedrate)
	Feedrate = MT_CheckFeedrate(actt,0,0,0,0,0,0,Feedrate)
	S_Feedrate = MT_CheckFeedrate(actt,0,0,0,0,0,0,S_Feedrate)
	
	Marker.PNo = PNo	

	'If (speed <> ProcessPara.Speed) Then
	
	' --
	' -- Neu MW 09.08.2005 wenn Speed = 0 -> dann Drehzahl von Bohrer übernehmen
	' --
	If (speed <> PPara.Speed) And (speed <> 0) Then
		MT_Write_Speed(actt,speed)

	End If
	PosReset
	MoveParaReset
	Marker.FirstTime_DH_Drilling = True
	Marker.Programmed_DH_Speed = speed

	LastV.IPX=-99999
	LastV.IPY=-99999
	LastV.IPZ=-99999
	Marker.LAstRotAngle_DrillingHead_Stroke=-99999


    'wcnc("BRISK")
	
End Sub

Sub Vertical_DrillingHead_Stroke(SNo,SPosX,SPosY,PosFirstX,PosFirstY,Depth,DZ,DType,DFlag_Type,Dummy,tools,DFlag_TypeString)
Dim	DH_VE,DH_V,DH_VA As Double   ' Bohrkopf selbst

Dim FirstTNr As Long
Dim Dh_TP As IIDH_ToolPlace

Dim itp As Variant
Dim Code As TBMuster

Dim dh As tDH
Dim Driller As tDriller
Dim DFlag As Integer
Dim ZMax As Double
Dim VDrillSicMode As Boolean   ' auch bei unterschiedlichen vertikalen Bohrhüben explizites zurücklegen
Dim isok As Boolean

	Driller.ActRot = Marker.RotAngle_DrillingHead_Stroke

	VDrillSicMode = MT_get_Add_ID(actt,10063,isok)
	If Not isok Then
		AddMistake("23423423423422")
	End If

	' Tool-No des 1. Bohrers aus dem Hub
	FirstTNr = Val(Get_First_Token(tools))   

	Set itp= ActT.t_dh.DrillingHead.ToolPlaces.GetToolPlace_PlaceID(FirstTNr) ' liefert BasicToolplace zurück
	' deshalb instanz so erzeugen
	Set Dh_TP=itp

	' ------------------------------------------------
	' Bohrdaten Bohrkopf
	' Vorschübe vom Bohrkopf
	' es wird davon ausgegangen, dass eine Vorschubsänderung über Werkzeugaufruf
	' eine gewollte Vorschubsdefinition ist
	' ------------------------------------------------
	
	' Neu MW 27.04.2005
	' setzt die dh und driller  - Daten 
	' MT_SetDrillingHeadData(tools, dh,Driller)
	
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
	' Vorschübe des einzelnen Bohrer
	Driller.V = Driller.Edge.Feedrate        ' Vorschub
	Driller.VE = Driller.Edge.MoveInFeedrate        ' EintauchVorschub
	Driller.VA = Driller.Edge.MoveOutFeedrate        ' AustauchVorschub
	Driller.Speed = Driller.Edge.RotSpeed        		' Solldrehzahl Neu MW 09.08.2005
	' Programmierten Vorschub berücksichtigten
	If PPara.I_Feedrate <> actt.t_dh.MoveInFeedrate Then
		' vorschub wurde geändert ist nicht ursprünglicher Wert des Bohrkopfs
		Driller.VE=PPara.I_Feedrate
	End If
	If PPara.Feedrate <> actt.t_dh.Feedrate Then
		' vorschub wurde geändert ist nicht ursprünglicher Wert des Bohrkopfs
		Driller.V=PPara.Feedrate
	End If
	If PPara.S_Feedrate <> actt.t_dh.MoveOutFeedrate Then
		' vorschub wurde geändert ist nicht ursprünglicher Wert des Bohrkopfs
		Driller.VA=PPara.S_Feedrate
	End If
	Driller.TNo = Driller.tp.ToolNo               ' TNummer des Bohrers auf der Steuerung
												  '  ' referiert auf die T-Korrketur auf der Steuerung fortlaufend vom 1. Bohrer beginnend		
	
	' --
	' -- Neu MW 09.08.2005 wenn Speed = 0 -> dann Drehzahl von Bohrer übernehmen
	' --
	If (Driller.Speed <> PPara.Speed) And (Marker.Programmed_DH_Speed=0) Then
		MT_Write_Speed(actt,Driller.Speed)
		
		PPara.Speed = Driller.Speed
		Marker.LastSpeed = Driller.Speed

	End If
	
	' liefert Bitmuster 1 und Bitmuster 2 in Code zurück	
	MT_Get_SpindleCode_Dez(tools,Code)

	wcnccom("vertical drilling: ->"+tools+"<-"+ " "+Driller.TName+" Typ:"+DType)
	
	Haube.pos = MT_Get_HaubenPos
	If Driller.edge.PosDustExhaust>0 Then
		Haube.pos=CLng(Driller.edge.PosDustExhaust)
		Haube.IsEbene0 = True
	End If
	
	Call CheckHaube
	'MT_Get_SpindleCode_Artis(tools,Code)
	If Driller.edge Is Nothing Then
	    ' kann nicht vorkommen
		AddMistake(GetErrMsg(99,"_unerwarteter Fehler",1))
	End If
	
	If MT_IsDHType(Actt)=1 Then		'DH Fix
		If (Marker.Last_DH_ToNo<>Driller.Tno) Then
		' Längenkorrektur aktivieren für 1. Bohrer des Hubs
			MT_Write_Correction_DH_Drill(Driller)
		
			'wcnc("T"+inttos(Driller.TNo)+ " D1")
			' ermittelt die maximale Anzahl von Wechselplätzen		
			'wcnc("T"+inttos(MT_Get_TNum_DrillingHead(actt))+ " D"+MT_Get_DNum_DrillingHead(actt))
			wcnc("T"+inttos(MT_Get_TNum_DrillingHead(actt)))
			wcnc("D"+MT_Get_DNum_DrillingHead(actt))
		End If
	ElseIf MT_IsDHType(Actt)=2 Then   'DH Raster
		If (Marker.Last_DH_ToNo<>Driller.Tno) Then
		' Längenkorrektur aktivieren für 1. Bohrer des Hubs
			'MT_Write_Correction_DH_Drill(Driller)
		
			'wcnc("T"+inttos(Driller.TNo)+ " D1")
			' ermittelt die maximale Anzahl von Wechselplätzen		
			'wcnc("T"+inttos(MT_Get_TNum_DrillingHead(actt))+ " D"+MT_Get_DNum_DrillingHead(actt))
			AddMistake("BohrkopfTyp Schwenkbar im Raster: Noch nicht Eingefahren!")
			Exit All
		End If
	ElseIf MT_IsDHType(Actt)=3 Then   'DH Free
		If (Marker.Last_DH_ToNo<>Driller.Tno) Then
		' Längenkorrektur aktivieren für 1. Bohrer des Hubs
			MT_Write_Correction_DH_Crot_Drill(Driller)
		
			'wcnc("T"+inttos(Driller.TNo)+ " D1")
			' ermittelt die maximale Anzahl von Wechselplätzen		
			'wcnc("T"+inttos(MT_Get_TNum_DrillingHead(actt))+ " D"+MT_Get_DNum_DrillingHead(actt))
			wcnc("T"+inttos(MT_Get_TNum_DrillingHead(actt)))
			wcnc("D"+MT_Get_DNum_DrillingHead(actt))
		End If
	End If
	
	
	If Marker.Last_DH_Process = DRILL_DHH Then
		' letzte Bearbeitung fand mit horizontal Spindeln statt
		' hor. Bohr Spindeln zurücklegen
		wcnccom("hor. Bohrspindeln zurücklegen")
		MT_WRITE_DHCode(actt,"")
	Else
		
		'If (Marker.Last_DH_ToNo<>Driller.Tno) And (VDrillSicMode) Then
		If MT_IsDHType(Actt)=1 Then
			If ((Marker.Last_DH_ToNo<>Driller.Tno)Or(Marker.DH_String<> tools)) And (VDrillSicMode)Then
		        ' --
                        ' -- Modified  MW 23.06.2008 13:19:05
                        ' -- bei jeder Änderung des Bohrmusters muss explizit zurückgelegt werden.

				' Neu MW 17.03.2006
				' auch Vertikale Bohrspindeln müssen zuerst zurück - da Rückzug zu langsam erfolgt
				wcnccom("vert. Bohrspindeln zurücklegen")
				MT_WRITE_DHCode(actt,"")
			End If
		ElseIf MT_IsDHType(Actt)=3 Then
			If ((Marker.Last_DH_ToNo<>Driller.Tno) Or (Marker.RotAngle_DrillingHead_Stroke <> Marker.LastRotAngle_DrillingHead_Stroke)) And (VDrillSicMode) Then
				wcnccom("vert. Bohrspindeln zurücklegen")
				MT_WRITE_DHCode(actt,"")
			End If
		End If
		
		'wcnc("M84")   ' Neu MW 17.03.2006 - da Spindeln zu langsam zurückgelegt werden
		' G04F1.5
		'wcnc(StrG04F)  ' Neu 17.03.2006
		'wcnc("STOPRE")  ' Neu
		
	End If
	
    If Not Marker.Last_DH_Process = DRILL_DHV Then
    	' letzter Hub war kein Vertikal drilling head hub
    	' also Ebene setzen
        Call wcncViewChange_DH(dh,DH_View0.View,DH_View0.LastView,DH_View0.IPX,DH_View0.IPY,DH_View0.IPZ,DH_View0.RotA,DH_View0.TipA,PosFirstX,PosFirstY,DH_View0.SPVZ,DH_View0.Vxx,DH_View0.Vxy,DH_View0.Vxz,DH_View0.Vyx,DH_View0.Vyy,DH_View0.Vyz,DH_View0.Vzx,DH_View0.Vzy,DH_View0.Vzz)
    End If
    
    
	'If Firsttime_Viewchange Then 
	' neu mw 28.04.2005
	If Firsttime_Viewchange Or Is_WP_Change Then 
	    ' 1. Anfahrt auf Werkstück
		' bei ersten mal wird immer ohne Z angefahren
		
		wcnc(G0+XEqualToS(PosFirstX)+YEqualToS(PosFirstY))
		Firsttime_Viewchange =False	
	Else
	
		If (Marker.Last_DH_ToNo<>Driller.Tno) Then
		    ' In Sicherheit auf Z im Bezug auf aktuellen Vorlegecode
		    ' wenn siche bohrmuster ändert und die folgenden Bohrer Länger sind
		    If (Driller.Length > Marker.last_DH_TLength) And (Marker.Last_DH_Process=DRILL_DHV) Then
		    	' jetziger HUB findet mit längerem Werkzeug statt 
		    	' daher muss jetzt erst mal im Bezug auf längeres Werkzeug hochgefahren werden
		    	' für aktives Werkzeug ist Längenkorrektur bereits aktiv
		    	wcnccom("Hochfahren, da längeres Werkzeug vorgelegt wird:")
		    	wcnccom("bisher:"+ftos(Marker.last_DH_TLength)+" jetzt:"+ftos(Driller.Length))
			    'wcnc(G0+ZEqualToS(actt.t_dh.GetSecurityZ(ActV.TipA)))
				' Neu MW 15.09.2005 * zusätzlichen Sicherheitsabstand einrechnen
			    wcnccom("Additives ZMass:"+ftos(GetAddZSic))
		    	
			    wcnc(G0+ZEqualToS(actt.t_dh.GetSecurityZ(ActV.TipA)+GetAddZSic))
			    
			    LastPos.Z = actt.t_dh.GetSecurityZ(ActV.TipA)
			End If
		    If (Marker.Last_DH_Process=DRILL_DHH) Then
		    	' letzter Hub fand horizontal statt
		    	' für aktives Werkzeug ist Längenkorrektur bereits aktiv
		    	wcnccom("Z-Positionieren, da vorher Hor. Bohren")
				' Neu MW 15.09.2005 * zusätzlichen Sicherheitsabstand einrechnen
			    wcnccom("Additives ZMass:"+ftos(GetAddZSic))
		    	
			    wcnc(G0+ZEqualToS(actt.t_dh.GetSecurityZ(ActV.TipA)+GetAddZSic))
		    	
			    'wcnc(G0+ZEqualToS(actt.t_dh.GetSecurityZ(ActV.TipA)))
			    LastPos.Z = actt.t_dh.GetSecurityZ(ActV.TipA)
			End If

		End If
	    
	End If
	' ----------------------------------------------------
	' -- hier Bohrspindeln vorlegen
	' -- Nicht mehr hier vorlegen, -> Zeitgewinn erst anfahren dann check und vorlegen
	' MT_WRITE_DHCode(actt,tools)
	' ----------------------------------------------------
    
	DFlag = Val(Get_First_Token(DFlag_TypeString))
	
	' Neu MW 25. Juli 2005
	ZMax=GetZMax(DFlag Mod 10,Depth)
'	wcncCom("ZMax:"+FToS(ZMax))


	If (DFlag >19) And (DFlag<30) Then
		' Bohrzyklus Durchgangsloch bohren
		Drilling_DH_Cylce_20(PosFirstX,PosFirstY,Depth,ActT.t_dh.GetSecurityZ(0),Driller,dh,tools,ZMax)
	ElseIf (DFlag >29) And (DFlag<40) Then
		' Bohrzyklus Topfband mit Verweilzeit bohren
		Drilling_DH_Cylce_30(PosFirstX,PosFirstY,Depth,ActT.t_dh.GetSecurityZ(0),Driller,dh,tools,ZMax)
	Else
		'If (DFlag >9) And (DFlag<20) Then
		' Bohrzyklus Sackloch bohren
		Drilling_DH_Cylce_10(PosFirstX,PosFirstY,Depth,ActT.t_dh.GetSecurityZ(0),Driller,dh,tools,ZMax)
	
	End If

	Marker.Last_DH_Process = DRILL_DHV
	Marker.last_DH_TLength = Driller.Length
	Marker.Last_DH_ToNo = Driller.tno
	Marker.DH_String = tools
	Marker.LastRotAngle_DrillingHead_Stroke = Marker.RotAngle_DrillingHead_Stroke	
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

'Drilling with Drilling Head 
Sub DrillingHorzDrillingHead(PPAX,PPAY,PPAZ,Depth,ToolNo,View)
  'wcnc(QXQYQZToS(PPAX,PPAY,PPAZ+FinishedPart.z)+" PRF="+FToS(Abs(Depth))+GetToolNoStrHorz(ToolNo)+GetCycleTypeStrHorz(View))
End Sub

Sub Horizontal_DrillingHead_Stroke(SNo,View,IPX,IPY,IPZ,RotA,TipA,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz,SPosX,SPosY,PosFirstX,PosFirstY,PosZ,SPosX_V,SPosY_V,PosFirstX_V,PosFirstY_V,SPosZ_V,PosFirstZ_V,Depth,DZ,DType,DFlag_Type,Dummy,tools,DFlag_TypeString)

Dim ox,oy,oz As Double
Dim Dh_TP As IIDH_ToolPlace
Dim itp As Variant
Dim FirstTNr As Long
Dim Code As TBMuster

Dim dh As tDH
Dim Driller As tDriller

'Dim Add_C As Double
Dim isok As Boolean
Dim Offsetwinkel_DH As Double
Dim Reset_Hori As Boolean   ' erzwingt Neuberrechnung offset und Rückzug
Dim Bohrer_Rot_0Grad As Double 


AddHint("Hori X:"+inttos(PosFirstX)+"-  Y:"+inttos(PosFirstY))

	
	
	If MT_IsDHType(Actt)=3 Then 
		Reset_Hori = Marker.RotAngle_DrillingHead_Stroke <> Marker.LastRotAngle_DrillingHead_Stroke

		' -- 
		' --  MW 10.08.2009 10:19:52
		' --
		Driller.ActRot = Marker.RotAngle_DrillingHead_Stroke
	End If
	
	FirstTNr = Val(Get_First_Token(tools))
	
	Set itp= ActT.t_dh.DrillingHead.ToolPlaces.GetToolPlace_PlaceID(FirstTNr)
	Set Dh_TP=itp

	' Bohrdaten Bohrkopf
	' Vorschübe vom Bohrkopf
	
	' Neu MW 27.04.2005
	' setzt die dh und driller  - Daten 
	' MT_SetDrillingHeadData(tools, dh,Driller)
	' 
	
	
	dh.tname = ActT.t.Description
	dh.CenterX = ActT.t.MoveX	
	dh.CenterY = ActT.t.MoveY
	dh.CenterZ = ActT.t.MoveZ	
	dh.VE=ActT.t.MoveInFeedrate
	dh.V=ActT.t.Feedrate
	dh.VA=ActT.t.MoveOutFeedrate
	
	
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
	Driller.Speed = Driller.Edge.RotSpeed        		' Solldrehzahl Neu MW 09.08.2005
	
	Driller.TNo = Driller.tp.ToolNo               ' TNummer des Bohrers auf der Steuerung
												  '  ' referiert auf die T-Korrketur auf der Steuerung fortlaufend vom 1. Bohrer beginnend		
	
	
	If MT_IsDHType(Actt)=3 Then 
		' -- 
		' --  START MW 17.09.2009 14:10:16
		' --
		' -- 
		' --  Prüfung ob Bohrer in die richtige Richtung bohrt.
		' --  
	
		Bohrer_Rot_0Grad = Driller.tp.RotAngle   '-> Bohrrichtung des Hor. Bohrers unter 0°
	
		' Driller.ActRot    ->  Sollstellung C-Achse für Bohrkopf unter welchem die hor. Bohrung gebohrt werden soll!
	
		' ROTA -> Soll - Bohrrichtung 
	
		If RotA <> (Norm0_360(Driller.ActRot+Bohrer_Rot_0Grad-90)) Then
			AddMistake("Bohrrichtung nicht moeglich - C-Achse:"+ftos(Driller.ActRot)+" Bohrwinkel:"+ftos(RotA))
		Else
			AddHint("Hor. Bohren - Bohrrichtung OK! - C:"+ftos(Driller.ActRot)+" Bohrwinkel:"+ftos(RotA)+" Soll:"+ftos(Norm0_360(Driller.ActRot+Bohrer_Rot_0Grad-90)))
		End If

	
		If TipA<>90 Then
		AddMistake("Bohrrichtung nicht moeglich ")
		End If
	
		' -- 
		' --  ENDE MW 17.09.2009 14:10:16
		' --
	End If
	
	
	Haube.pos = MT_Get_HaubenPos
	If Driller.edge.PosDustExhaust>0 Then
		Haube.IsEbene0 = True
		Haube.pos=CLng(Driller.edge.PosDustExhaust)
	End If
	
	Call CheckHaube
	' liefert Bitmuster 1 und Bitmuster 2 in Code zurück	
	MT_Get_SpindleCode_Dez(tools,Code)
		

	wcnccom("horizontal drilling: ->"+tools+"<-"+ " "+Driller.TName+" Typ:"+DType)
	If (Marker.Last_DH_ToNo<>Driller.Tno) Or (Reset_Hori) Then
		' Längenkorrektur aktivieren für 1. Bohrer des Hubs
		If MT_IsDHType(Actt)=1 Then
			MT_Write_Correction_DH_Drill(Driller)
		ElseIf MT_IsDHType(Actt)=3 Then
			MT_Write_Correction_DH_CRot_Drill(Driller)
		Else 
			AddMistake("Bohrkopf Typ Nicht Zugelassen")
		End If
		
		
		'wcnc("T"+inttos(Driller.TNo)+ " D1")
		' ermittelt die maximale Anzahl von Wechselplätzen		
		'wcnc("T"+inttos(Driller.tno)+ " D1")
		wcnc("T"+inttos(MT_Get_TNum_DrillingHead(actt)))
		wcnc("D"+inttos(MT_Get_DNum_DrillingHead(actt)))
	
	End If

	If ((Marker.Last_DH_Process = DRILL_DHH) Or (Marker.Last_DH_Process = DRILL_DHV)) And (Marker.Last_DH_ToNo<>Driller.Tno) Or (Reset_Hori) Then
		' letzte Bearbeitung fand mit horizontal oder Vertikalen Spindeln statt
		' und Vorlegespindeln haben sich geändert 
		' hor. Bohr Spindeln zurücklegen
		wcnccom("hor. Bohren alle Bohrspindeln zurücklegen")
		' Neu MW 13.09.20005 - hat bisher gefehlt, hat aber keine Probleme verursacht, da
		' Spindeln alle im zurückgezogenen Zustand
		If (Marker.Last_DH_Process = DRILL_DHH) And (LastV.View<>View) Then
			' hochfahren, auf Sicherheit in Z
			' Neu MW 15.09.2005 * zusätzlichen Sicherheitsabstand einrechnen
		    wcnccom("Additives ZMass:"+ftos(GetAddZSic))
		    'wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+GetAddZSic))
		    ' Neu MW 15.09.2005 - Bug IPZ ist nicht korrekt, da ja noch letzter View aktiv 
		    
'		    wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-LastV.IPZ+GetAddZSic))
		    
			' SF/MW 06.07.2016
			' Ebene kommt mit Agg-Versatz Z verrechnet
		    wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-LastV.IPZ+Marker.Last_DH_DZ+GetAddZSic))		    
		    
		    'wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ))
		End If
		
		MT_WRITE_DHCode(actt,"")
		
	End If

    If (Not Marker.Last_DH_Process = DRILL_DHH) Or (LastV.View<>View) Or (LastV.IPX<>IPX) Or (LastV.IPY<>IPY) Or (LastV.IPZ<>IPZ) Then
    	' letzte Bearbeitung nicht horizontal oder ebene gewechselt
		Call wcncViewChange_DH(dh,View,0,IPX,IPY,IPZ,RotA,TipA, PosFirstX,PosFirstY,DZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
	    ' mw 21.09.2005
	    '.-------------------------
	    If (Marker.Last_DH_Process = DRILL_DHV) Then
		    wcncCom("hochfahren, da vorher vertikal bohren")
			'wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+GetAddZSic))		
			
			' SF/MW 06.07.2016
			' Ebene kommt mit Agg-Versatz Z verrechnet
			wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+DZ+GetAddZSic))		
			
			
		Else
	       ' Neu MW 02.09.2010 - immer hochfahren auch wenn vorher hor. Bohren evtl. Werkstückwechsel
	       If (Marker.Last_DH_Process = DRILL_DHH) Then
			    wcncCom("hochfahren, da zuvor hor. bohren aber Ebenenaenderung")
				'wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+GetAddZSic))		
				
				' SF/MW 06.07.2016
				' Ebene kommt mit Agg-Versatz Z verrechnet
				wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+DZ+GetAddZSic))		
				
				wcnc(G0+XEqualToS(PosFirstX_V)+ZEqualToS(actt.t_dh.SecurityHorz))
			End If
			
		End If
		'MT_WRITE_DHCode(actt,tools)
	    '.-------------------------
	End If

	'If Firsttime_Viewchange Then 
	' neu mw 28.04.2005
	If MT_IsDHType(Actt)=3 Then 
		Offsetwinkel_DH= StrToFloat(MT_get_Add_ID(actt,10003,isok))
	End If
	If Firsttime_Viewchange Or Is_WP_Change Then 
	    ' 1. Anfahrt auf Werkstück
		' bei ersten mal wird immer ohne Z angefahren
		
		If MT_IsDHType(Actt)=1 Then 		
			wcnc(G0+XEqualToS(PosFirstX_V)+ZEqualToS(actt.t_dh.SecurityHorz))
		ElseIf MT_IsDHType(Actt)=3 Then 
			If isok Then
				wcnc(G0+XEqualToS(PosFirstX_V)+ZEqualToS(actt.t_dh.SecurityHorz) + RotAxisDH(Offsetwinkel_DH+Driller.ActRot))
			
			Else
				AddMistake("ID 10003 - Bohrkopf nicht gefunden")
		
			End If
		End If
		Firsttime_Viewchange =False	
		
	Else

		If (Marker.Last_DH_ToNo<>Driller.Tno) Or (Reset_Hori) Then
		    ' In Sicherheit auf Z im Bezug auf aktuellen Vorlegecode
		    ' wenn siche bohrmuster ändert und die folgenden Bohrer Länger sind
			If MT_IsDHType(Actt)=1 Then    
		    	'wcnccom("**JS1")
		    	
				' Neu MW 15.09.2005 * zusätzlichen Sicherheitsabstand einrechnen
		    	wcnccom("Additives ZMass:"+ftos(GetAddZSic))
		    	'wcnc(G0+XEqualToS(PosFirstX_V)+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+GetAddZSic)+ZEqualToS(actt.t_dh.SecurityHorz))
		    	
		    	' SF/MW 06.07.2016
				' Ebene kommt mit Agg-Versatz Z verrechnet

		    	wcnc(G0+XEqualToS(PosFirstX_V)+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+DZ+GetAddZSic)+ZEqualToS(actt.t_dh.SecurityHorz))


		    	'wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+GetAddZSic)+ZEqualToS(actt.t_dh.SecurityHorz))
		    	'wcnccom("Additives ZMass:"+ftos(GetAddZSic))
		    	' Neu MW 21.09.2005 auch in X bereits angefahren folgende Zeile entfaellt
		    	'wcnc(G0+XEqualToS(PosFirstX_V)+ YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+GetAddZSic)+ZEqualToS(actt.t_dh.SecurityHorz))
			ElseIf MT_IsDHType(Actt)=3 Then
				   ' In Sicherheit auf Z im Bezug auf aktuellen Vorlegecode
		    	' wenn siche bohrmuster ändert und die folgenden Bohrer Länger sind
	    
				' zusätzlichen Sicherheitsabstand einrechnen
		   	 	wcnccom("Additives ZMass:"+ftos(GetAddZSic))
		    	' * auch in X muss positioniert werden..
		    	'wcnc(G0+XEqualToS(PosFirstX_V)+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+GetAddZSic)+ZEqualToS(actt.t_dh.SecurityHorz) + RotAxisDH(Offsetwinkel_DH+Driller.ActRot))
		    	
		    	' SF/MW 06.07.2016
				' Ebene kommt mit Agg-Versatz Z verrechnet
		    	
		    	wcnc(G0+XEqualToS(PosFirstX_V)+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+DZ+GetAddZSic)+ZEqualToS(actt.t_dh.SecurityHorz) + RotAxisDH(Offsetwinkel_DH+Driller.ActRot))
		    	'wcnc(G0+YEqualToS(FinishedPart.Z+actt.t_dh.GetSecurityZ(TipA)-IPZ+GetAddZSic)+ZEqualToS(actt.t_dh.SecurityHorz))
			End If
		
		Else
			' gleicher Bohrer wie zuvor
			' nichts tun
		End If
	    
	End If
	
	
	Drilling_DHorz(PosFirstX_V,PosFirstY_V,0,Depth,DFlag_Type Mod 10,0,GetZMax(DFlag_Type Mod 10,Depth),Driller,dh,tools)
	' über Y- auf der Ebene wieder übers Werkstück fahren
'	wcncaddcom(YEqualToS(-IPZ+ActT.T.GetSecurityZ(ActV.TipA)+DZ+FinishedPart.z),"Hochfahren übers Werkstück!")
	
	' Bohrkopf zurücklegen
	Marker.Last_DH_Process = Drill_DHH 
	Marker.Last_DH_ToNo = Driller.tno
	Marker.Last_DH_DZ = DZ

	If MT_IsDHType(Actt)=3 Then
		Marker.LastRotAngle_DrillingHead_Stroke = Marker.RotAngle_DrillingHead_Stroke
	End If
End Sub

Sub End_Vertical_DrillingHead_Stroke(Retreat)
	wcnccom("Bohrspindeln zurücklegen")
	MT_WRITE_DHCode(ActT,"")
	wcnc("TRANS")
	'wcnc("C_FRAME_SAVE")
	' Neu MW 15.09.2005 * zusätzlichen Sicherheitsabstand einrechnen
    wcnccom("Additives ZMass:"+ftos(GetAddZSic))
	
	'wcnc("G0 Z"+Ftos(ActT.t_dh.GetSecurityZ(0)+(FinishedPart.Z+GetAddZSic)))
	'Neu MW 22.02.2006 - wenn Bohrkopf nicht Referenzkopf
	wcnc("G0 Z="+Ftos(ActT.t_dh.GetSecurityZ(0)+(FinishedPart.Z+GetAddZSic))+Get_Val_Signed(-ActT.t.DrillingHead.CenterZ))
	
	MarkerSawingReset
	
	Marker.FirstTime_DH_Drilling=False
	Marker.Last_DH_ToNo	= -9999   ' Sonst wird Korrektur nicht neu angewählt, wenn dazwischen z.B. eine Fräsbearbeitung stattfindet!
	Marker.Viewchangechecked=False
   ' wcnc("SOFT")
	Marker.DH_String = ""
	Retreat_ClampChange=Retreat
	Call Reset_Messbezug
		'Zurücksetzen der Bahnsteuerparameter Os 31.03.2016
	ActHK_ON=""
	ActHK_OFF=""
	Inc_Process   ' ActProcess=ActProcess+1
End Sub

Sub NC_End()
Dim SSVariant As Variant
Dim RetreatType As Long

	If MT_Is_Vertical_StandardTool5Axis(Actt) Then
		RetreatType=1
	ElseIf MT_Is_Vertical_Rot_Axis(Actt) Then
		RetreatType=2
	Else
		RetreatType=3
	End If
	
	
	Call ToolChange (-1,"Schrupper D20","",10300,2,1,5,5000.000000,1200.000000,60000.000000,18000.000000,12434.000000,0.000000,50.000000,50.000000,10.000000,88.000000,1.560000,160.000000,-180.000000,0.000000,0.000000,0.000000,1)
	
	'wcnc("==============================")
	If Marker.PrinterIsUp=False Then
		'WCNC("H90")
	End If
	
	wSafetyAbs(False)
	If RetreatType=1 Then
		WCNC("G153 G0 B=0 C=0")
	ElseIf RetreatType=2 Then
		WCNC("G153 G0 C=0")
	ElseIf RetreatType=3 Then
		'DoNothing
	End If
	
	' EndandPark  MW 28.04.2010
	'Haube.P5AchsAktiv=True
	'Haube.Pos=(-9999)
	'Call CheckHaube

	
	WKS_ENTSPANNEN   ' hier erfolgt auch das parken
	'ReadStrPP_ini("NC","ERWEITERUNG","MPF", SSVariant)
	
	If Marker.aaxiss Then
		' auf jeden Fall A-Achse aus
		wcnc("DO MOV[A]=0")
		Marker.aaxiss=False	
	End If
	
	If Marker.blowing Then
		' auf jeden Fall aus
		Blasen_AUS
	End If
	
	

	
	If GTableType=1 Then
		wcnc("C_FRG_ACHSEN")
	End If
	
	
	If InStr(UCase(SSVariant),"SPF")>0 Then
		wcnc("M02")   ' or RET
	Else
		wcnc("M30")
	End If


	FileClose
	If mPara_Add.Script_Info=True Then
		AddLog("BASIC SCRIPT - DURCHLAUF GESAMT: "+ftos(Timer-JobPara.TimerFullSecs)+" sec")
		If MT_Get_MachPara_Add(1102) = "1" Then
			Write_DebuggerLog
		End If
	End If
	
	ClearMTData  
	
End Sub

Sub NCInfo(Kind,NCType,Para1,Para2,Para3,Para4,Para5,Para6,Para7,Para8,Para9,characters)
	Handle_NCInfo(Kind,NCType,Para1,Para2,Para3,Para4,Para5,Para6,Para7,Para8,Para9,characters)
End Sub


' Neu MW 09.11.2004
Sub ViewInfoToolChange(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPVX,SPVY,SPVZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz,dummy1,dummy2,dummy3,dummy4,dummy5,dummy6,dummy7,dummy8,dummy9,dummy10)
	ViewBefore.View=View
	ViewBefore.LastView=LastView
	ViewBefore.IPX=IPX
	ViewBefore.IPY=IPY
	ViewBefore.IPZ=IPZ
	ViewBefore.RotA=RotA
	ViewBefore.TipA=TipA
	ViewBefore.SPVX=SPVX
	ViewBefore.SPVY=SPVY
	ViewBefore.SPVZ=SPVZ
	ViewBefore.Vxx=Vxx
	ViewBefore.Vxy=Vxy
	ViewBefore.Vxz=Vxz
	ViewBefore.Vyx=Vyx
	ViewBefore.Vyy=Vyy
	ViewBefore.Vyz=Vyz
	ViewBefore.Vzx=Vzx
	ViewBefore.Vzy=Vzy
	ViewBefore.Vzz=Vzz

	Haube.NewHaubePosBeforeTC=1
End Sub


' Neu MW 30.11.2004
Sub HeadInfo(id)
Dim H As Object

	Set H= TDATA.GetProcessHead_ID(id)
	If id >= 0 Then
		HeadID= id
	Else
		HeadID = MT_GetFirst_TC_Hid
	End If

	
End Sub


Sub WorkPieceListInit(count)

	ReDim WPI(1)	
	If Not PostSettings.GeneralSettings.WriteInitZero Then
		pp_err(5,"WriteInitZero")
	End If

	WritePPVersion   ' MW 14.04.2007
	Get_Language_info
	get_Hops_path
	SecMidnight = Timer


	
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
	JobPara.Flag=Anschlag
	'drehflag=Dreh
End Sub

Sub SP_EP_No_LeadInOut(SP_x,SP_y,SP_z,SP_ax,SP_ay,SP_az,SP_Feedrate,SP_Speed,SP_RotA,SP_TipA,SP_TRC,SP_TA,SP_Distance, _
                       EP_x,EP_y,EP_z,EP_ax,EP_ay,EP_az,EP_Feedrate,EP_Speed,EP_RotA,EP_TipA,EP_TRC,EP_TA,EP_DMove,EP_DFactor,EP_Retreat, _
                       Dummy1,Dummy2,Dummy3,Dummy4,Dummy5,Dummy6,Dummy7,Dummy8,Dummy9,Dummy10,Dummy11,Dummy12,Dummy13,Dummy14,Dummy15,Dummy16,Dummy17,Dummy18,Dummy19,Dummy20)
  Call SP_EP_No_LeadInOutSave(SP_EP,SP_x,SP_y,SP_z,SP_ax,SP_ay,SP_az,SP_Feedrate,SP_Speed,SP_RotA,SP_TipA,SP_TRC,SP_TA,SP_Distance, _
                       EP_x,EP_y,EP_z,EP_ax,EP_ay,EP_az,EP_Feedrate,EP_Speed,EP_RotA,EP_TipA,EP_TRC,EP_TA,EP_DMove,EP_DFactor,EP_Retreat, _
                       Dummy1,Dummy2,Dummy3,Dummy4,Dummy5,Dummy6,Dummy7,Dummy8,Dummy9,Dummy10,Dummy11,Dummy12,Dummy13,Dummy14,Dummy15,Dummy16,Dummy17,Dummy18,Dummy19,Dummy20)
End Sub

Sub Start_NCInfoProcess (PNo,I_Feedrate,Feedrate,S_Feedrate,speed)

End Sub


Sub NCInfoProcess(InfoTyp,x1,y1,z1,x2,y2,z2,w1,w2,w3,w4,w5,w6,w7,w8,w9,w10,w11,w12,w13,w14,w15,w16,w17,w18,w19,w20,w21,str1,str2)
Dim count As Long

	Marker.PNo = Marker.PNo + 1
	Handle_NCInfoProcess(InfoTyp,x1,y1,z1,x2,y2,z2,w1,w2,w3,w4,w5,w6,w7,w8,w9,w10,w11,w12,w13,w14,w15,w16,w17,w18,w19,w20,w21,str1,str2)
	Inc_Process   ' ActProcess=ActProcess+1
End Sub



Sub old_AdditionalSPInfo(DirectionMode,ExcessLength,Mode,Laser,AxisRotA,Res1,SurfaceMode,Res3,Res4,Res5,KW,TRC,DISTANCE,DW,MinRot,MaxRot,s3,s4,s5)
	' -- 
	' Neu MW 25.09.2006
	' Leitkurven - Fräsen mit kontinuierlicher Kippachse
	If SurfaceMode=3 Then
		SurfaceMode=2
	End If
	If equal(Mode,1) Then
	
'		MillC_INIT(True,DirectionMode,ExcessLength,Mode,AxisRotA,KW,TRC,DISTANCE,MinRot,MaxRot,DW)			
	ElseIf equal(SurfaceMode,1) Then
		' -- 
		' -- Neu MW 26.07.2006
		' -- 
		' -- Oberflächenfräsen 3-Achsen
'		SurfaceMilling_Init(True,SurfaceMode,DirectionMode,ExcessLength,AxisRotA,KW,DW,TRC,DISTANCE,MinRot,MaxRot)
		' -- 
	ElseIf equal(SurfaceMode,2)  Then
		' -- 
		' -- Neu MW 26.07.2006
		' -- 
		' -- Mit schwenken der Kippachse !
'		SurfaceMilling_Init(True,SurfaceMode,DirectionMode,ExcessLength,AxisRotA,KW,DW,TRC,DISTANCE,MinRot,MaxRot)
	End If

End Sub


Sub AdditionalVertDrillingInfo(DW,Res1,Res2,Res3,Res4)

	
	' +90, da unserer Ebene 1 (Y+) die Nullebene die Reihe in X stehend O O X O O hier als 0° kommt
	MultiDrilling_GBHeadVert.dw = DW + 90
	' -- 
	' --  MW 02.07.2008 14:10:37
	' --
	' -- da Änderung PP-Engine diese Funktion wird vor Toolchange aufgerufen
	
	'MultiDrilling_GBHeadVert.Angle = actt.T_SGB.Angle
 
End Sub


Sub SawingExt(PNo,I_Feedrate,Feedrate,S_Feedrate,speed,SPX,SPY,SPZ,EPX,EPY,EPZ,ZRef,TC,Flag, _
              CPSawUnit_PosSX,CPSawUnit_PosSY,CPSawUnit_PosSZ,CPSawUnit_PosRX,CPSawUnit_PosRY,CPSawUnit_PosRZ, _
              CPSawUnit_SPX,CPSawUnit_SPY,CPSawUnit_SPZ,CPSawUnit_EPX,CPSawUnit_EPY,CPSawUnit_EPZ, _
              ViewCPSawUnit_PosSX,ViewCPSawUnit_PosSY,ViewCPSawUnit_PosSZ,ViewCPSawUnit_PosRX,ViewCPSawUnit_PosRY,ViewCPSawUnit_PosRZ, _
              ViewCPSawUnit_SPX,ViewCPSawUnit_SPY,ViewCPSawUnit_SPZ,ViewCPSawUnit_EPX,ViewCPSawUnit_EPY,ViewCPSawUnit_EPZ,Retreat, _
              CPSawUnit_PosSX2,CPSawUnit_PosSY2,CPSawUnit_PosSZ2,CPSawUnit_PosRX2,CPSawUnit_PosRY2,CPSawUnit_PosRZ2, _
              ViewCPSawUnit_PosSX2,ViewCPSawUnit_PosSY2,ViewCPSawUnit_PosSZ2,ViewCPSawUnit_PosRX2,ViewCPSawUnit_PosRY2,ViewCPSawUnit_PosRZ2, _
              RViewx,RViewy,RViewz, _
              Res1,Res2,Res3,Res4,Res5)

	' Neu MW 20.04.2005
	I_Feedrate = MT_CheckFeedrate(actt,0,0,0,0,0,0,I_Feedrate)
	Feedrate = MT_CheckFeedrate(actt,0,0,0,0,0,0,Feedrate)
	S_Feedrate = MT_CheckFeedrate(actt,0,0,0,0,0,0,S_Feedrate)

	Marker.PNo = PNo	

	PosReset
	MoveParaReset

	MT_Write_Check_Spindle
	If MT_isdhsaw(ActT) Then
		' ----------------------------------------------------
		' -- hier Bohrspindeln/Säge vorlegen
		' -- Bohrkopf - Säge
		' ----------------------------------------------------
		
		MT_WRITE_DHCode(ActT,ActT.t_dhsaw.DH_ToolPlace.ToolNo)
	End If
	
	wcncCom("*****************************************")
	wcncCom("*************  Sägen  *******************")
	wcncCom("*****************************************")
	'If MT_FixSawingOk(ActT) Then
	'	Call SawingXY_Direction(I_Feedrate,Feedrate,S_Feedrate,speed,SPX,SPY,SPZ,EPX,EPY,EPZ,ZRef,TC,Flag,CPSawUnit_PosSX,CPSawUnit_PosSY,CPSawUnit_PosSZ,CPSawUnit_PosRX,CPSawUnit_PosRY,CPSawUnit_PosRZ,CPSawUnit_SPX,CPSawUnit_SPY,CPSawUnit_SPZ,CPSawUnit_EPX,CPSawUnit_EPY,CPSawUnit_EPZ,ViewCPSawUnit_PosSX,ViewCPSawUnit_PosSY,ViewCPSawUnit_PosSZ,ViewCPSawUnit_PosRX,ViewCPSawUnit_PosRY,ViewCPSawUnit_PosRZ,ViewCPSawUnit_SPX,ViewCPSawUnit_SPY,ViewCPSawUnit_SPZ,ViewCPSawUnit_EPX,ViewCPSawUnit_EPY,ViewCPSawUnit_EPZ,Retreat)
	'Else
	
		' Anfahrt abwärts - he
		wcnc(G1+Move(ViewCPSawUnit_PosSX,ViewCPSawUnit_PosSY,ViewCPSawUnit_PosSZ,S_Feedrate,MovePara.TRC))
	
		wcnc(G1+Move(ViewCPSawUnit_SPX,ViewCPSawUnit_SPY,ViewCPSawUnit_SPZ,I_Feedrate,MovePara.TRC))
		wcnc(G1+Move(ViewCPSawUnit_EPX,ViewCPSawUnit_EPY,ViewCPSawUnit_EPZ,Feedrate,MovePara.TRC))
		wcnc(G1+Move(ViewCPSawUnit_PosRX,ViewCPSawUnit_PosRY,ViewCPSawUnit_PosRZ,S_Feedrate,MovePara.TRC))
		
		' jetzt wieder in Z- hochfahren
		wcnc(G1+Move(RViewx,RViewy,RViewz,S_Feedrate,MovePara.TRC))
		
	'End If
	
	MarkerSawing.LastIsSawing=True
	MarkerSawing.LastKW=True
	
	' Neu MW 07.03.2006
	If ((Retreat=1)) Then
		' lastissawing wird gecheckt
		wsafetyPart
	End If
	
	
	Marker.Viewchangechecked=False
	Marker.Last_ExhaustPos = 9999
	Retreat_ClampChange=Retreat

End Sub

Sub LeadInOutWithoutSafety (an,ab)
	
End Sub
Sub RotAngle_DrillingHead_Stroke(Angle)
	Marker.RotAngle_DrillingHead_Stroke = Angle
	
End Sub

Sub AdditionalSPInfoMPs(Mode,PreObjectTyp, MinRot,MaxRot,MinTipA,MaxTipA, R1, R2, R3,  R4)
	Add_SPInfoMPs_7(Mode,PreObjectTyp, MinRot,MaxRot,MinTipA,MaxTipA, R1, R2, R3,  R4)
End Sub


' --------------------------------------------------------------------------------------------------------------------------------------
' Postprozessor - Generation 7 - Funktionen
' --------------------------------------------------------------------------------------------------------------------------------------

Sub SuctionHood (Index)
	Call SuctionHood_7 (Index)
	PPara.DustPosNCIExt = True
End Sub

Sub Process_Start(ProcId,BoxId,HeadID,d1,d2,ProcC,XMin,YMin,ZMin,XMax,YMax,ZMax)
	Call Process_Start_7(ProcId,BoxId,HeadID,d1,d2,ProcC,XMin,YMin,ZMin,XMax,YMax,ZMax)
End Sub


Sub Process_End(ProcId,d1,d2)
	Call Process_End_7(ProcId,d1,d2)
End Sub

Sub ClampChangeExt(Situa1,Situa2,Index)
Dim par1,par2,par3,par4,par5,par6,par7,par8,par9,par10,par11,par12 As Variant 
	
	par1 = Situa1
	par2 = Situa2
	
	Call Handle_ClampChangeExt_7 (Index,par3,par4,par5,par6,par7,par8,par9,par10,par11,par12)
	
	
	' Aufruf alte ClampChange Sub
	Call ClampChange(par1,par2,par3,par4,par5,par6,par7,par8,par9,par10,par11,par12)
	
End Sub

' --------------------------------------------------------------------------------------------------------------------------------------
' DLL-Milling - zugehoerige Functions/Subs
' --------------------------------------------------------------------------------------------------------------------------------------


Sub InitDLLMPs_Milling
	' kommt nur einmalig zu Beginn
	DLLMPs_Init()
End Sub


Sub DLLMPs_Start_Milling(pno)
	' kommt nur einmalig zu Beginn
	DLLMPs_Start(pno)
End Sub


Sub DLLMPs_Milling(Kind,pno)
	' Kind -1: Anfahrt auf Bearbeitung 
	' Kind  0: eigentliche Bearbeitung
	' Kind  1: Abfahrt nach Bearbeitung
	DLLMPs(Kind,pno)
End Sub


Sub DLLMPs_End_Milling
	' Ende der Bearbeitung
	DLLMPs_End()
End Sub

Sub FinalDLLMPs_Milling
	' kommt nur einmalig zum Schluss
	DLLMPs_Final()
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
Sub MachineStop (Index, NextBoxWorking,HeadID)
	Call Machine_Stopp_7(Index, NextBoxWorking,HeadID)
End Sub


Sub NCIExt (Kind,NCType,Index)
Dim Group As Variant
Dim PostName As Variant 
	Group = NCData.NCIExtList.GetNCI_Index(Index).NCIExt.Group
	PostName = PostSettings.PPName
	
	' 1. 2Zeichen gleich ? "VISION" = "VISION" = TRUE
	If Left(UCase(Group),6) = Left(UCase(PostName),6) Then
		' Fuer diesen Post festgelegter NCINFO
		Call Handle_NCI_Ext_7 (Kind,NCType,Index)
	ElseIf UCase(Group) = UCase(PPGRP) Then	
		Call Handle_NCI_Ext_7 (Kind,NCType,Index)
	' System - NCI
	ElseIf equal(NCType,-100200) Then
		' NCZeile direkt
		Call Handle_NCI_Ext_7 (Kind,NCType,Index)
	ElseIf equal(NCType,-100058) Then
		' hor.Bohren mit Rueckzug ueber Platte
		pp_err(0)
		'If equal(NCData.NCInfo_Global.GetNCI_Index(Index).Para1,1) Then
		'	Marker.HorDH_PullBack = True
		'Else
		'	Marker.HorDH_PullBack = False
		'End If
	Else
		AddHint("NCIExt Group ["+(Group)+ "] NCType #"+inttos(NCType)+" not interpreted from this Post ["+UCase(PostName)+"] TDATA ["+TDATA.ActMachineName+"]" )
	End If
End Sub
