' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \hh7\pp.bas
' -- 
' -----------------------------------------

'#uses "pp_7.bas"
'#uses "pp_global.bas"
'#uses "pp_mt.bas"
'#uses "pp_mtf.bas"
'#uses "pp_bohrdh.bas"
'#uses "pp_laser.bas"
'#uses "pp_ncinfo.bas"
'#uses "pp_isg.bas"
'#uses "pp_siemens.bas"
'#uses "pp_math.bas"
'#uses "pp_measure.bas"


Option Explicit



Sub InitZero
Dim i As Integer
Dim PH As IIProcessHead 
Dim SA

	JobPara.TimerFullSecs = Timer

	ReDim Preserve LogArr(1) 
	ReDim WPI(1)	 ' MW 11.02.2016 - damit im Fehlerfall beim Init (vor dem WorkpieceInfo) nicht auf leeres Array laeuft!

	Version_Check("7.0.0.340")  	' Pruefung auf PPEngine.dll min.Version

	' --
	' 1. Funktion im Script -> auch vor allen NCINFO's
	' --
	INITZero_7  

	' MW 31.07.2013 Evolution - setzen so frueh wie moeglich
	' MW 05.03.2014 jetzt ganz am Anfang
	JobPara.is_Evo = IIf(TDATA.MachineData.MachineParameter.MachineNo=200002,True,False)
	
    Read_MPara_ADD   ' Parkpos lesen etc. 
    
    
	If JobPara.is_evo Then
	
		JobPara.Mea.QuoteXQD = -99999
		JobPara.Mea.QuoteXQM = -99999   
	
		JobPara.Mea.MaxQuoteX = 25
		
	    If Not MT_Get_MachPara_Add(3000)="" Then
	    	' Quote einstellbar ueber Maschine -> Parameter -> ID3000
	    	JobPara.Mea.MaxQuoteX = StrToFloat(MT_Get_MachPara_Add(3000))
	    End If
	
		JobPara.Mea.MaxMessDiffX = 3
		
	    If Not MT_Get_MachPara_Add(3001)="" Then
	    	JobPara.Mea.MaxMessDiffX = StrToFloat(MT_Get_MachPara_Add(3001))
	    End If
	    
		EvoPreCheck_Obj	  'Vorlauf ueber NCDATA MW 14.01.2015
		' --
		' MW 05.03.2014 
		' -- Vorlauf Ermittlung In welchen Szenen gemessen werden muss
	   ' pp_vorlauf       ' Function implementiert in PP_Plausi.bas
	ElseIf Val(MT_Get_MachPara_Add(1005)) Then
	
		EvoPreCheck_Obj	  'Vorlauf ueber NCDATA MW 14.01.2015
		' Sprungmarken in welchen Szenen ?
	    'pp_vorlauf       ' Function implementiert in PP_Plausi.bas
	    
	    
	End If
    JobPara.ActScene=1
	JobPara.mea.Bea_Mea_activ = False
	
  	AddLog("INIT_ZERO TIME: "+ftos(Timer-JobPara.TimerFullSecs)+" sec")
  	
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
	
	' 1. 2Zeichen gleich ? "HH_sdfa" = "HH7" = TRUE
	If Left(UCase(Group),2) = Left(UCase(PostName),2) Then
		' Fuer diesen Post festgelegter NCINFO
		If equal(NCType,90100) Then
			' Alle NCIExt von HH7 PP [OEM] zur freien Verwendung seitens Holz-Her
			'Neu AK 24.11.2016
			Call Handle_NCI_Ext_7_OEM (Kind,NCType,Index)
		Else
			Call Handle_NCI_Ext_7 (Kind,NCType,Index)
		End If
		If equal(NCType,90200) Then
			Marker.RollerTrackDown=True
			'wcncAddCom(";PreInfo M154")
		End If
		
	' System - NCI
	ElseIf equal(NCType,-100200) Then
		' NCZeile direkt
		Call Handle_NCI_Ext_7 (Kind,NCType,Index)
	ElseIf (JobPara.is_Evo) Then
		If equal(NCType,-108040) Or equal(NCType,-100064) Then
			' Rollertracker EVO
			Call Handle_NCI_Ext_7 (Kind,NCType,Index)
		End If
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

Sub SuctionHood (Index)
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


'	Sub ToolListInit(Count)
'	Dim Secs_Plausi As Double
'	
'		CountOfTool	= Count   ' MW 04.07.2005 auch wenn keine Werkzeuge muss Programm erzeugbar sein z.B. Laserbahnen
'		
'	'    If (DEF_Plausi_Check) And (Not JobPara.is_Evo) Then
'	'   		Secs_Plausi = Timer
'	'	    plausibility_check
'	'	    AddLog("PLAUSI - DURCHLAUF : "+ftos(Timer-Secs_Plausi)+" sec")
'	'
'	'	End If
'		If Count>0 Then 
'	     	ReDim ToolArray(Count)
'	    End If
'	    ToolPos=0
'		JobPara.TimerInitTL = Timer
'	
'	
'	End Sub

'	Sub Tool(BoxNo,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15,d16,d17,d18,d19,d20,d21,d22)
'		If Not equal(Headid,Hid) Then
'			pp_err(126)
'		End If
'		'wegschreiben ins ToolArray
'		MT_SetTHopsBasicToolExt(ToolArray(ToolPos),BoxNo,Hid)
'		
'		ToolPos=ToolPos+1
'		
'	End Sub


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
Dim l_KoppelWert As Double
Dim l_FeldA As Boolean
Dim l_FeldD As Boolean
Dim l_KoppelAD As Boolean
Dim l_KoppelDA As Boolean
Dim c_part As Integer

	If Not PostSettings.GeneralSettings.WriteInitZero Then
		pp_err(5,"WriteInitZero")
	End If
	
	WritingNCData = True	

	AddLog("needed Time for collection Tool and HeadInfos: "+ftos(Timer-Jobpara.TimerInitTL)+" sec")
	
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
	
	Init_MachineData  
	Init_JobData
	Init_Marker

	MeasureInfos_Init()

	If JobPara.isg Then
		ISG_init_NCVARNames
	Else
		SIEMENS_init_NCVARNames
	End If
	
	SetDrillingZMax -5,-10,-15,-20,-25,-30,-35,-40,-45
	
	If (Not PostSettings.PPStarterType = ppstHops) Then
		' --
		' Modified AK 21.02.2012
		' --
		l_KoppelWert = MCDATA.Fields.GetField_FieldIndex(0).GetSection_Index(0).Maxx
		l_FeldA      = False
		l_FeldD      = False
		l_KoppelAD   = False
		l_KoppelDA   = False 
		
		'Nur Feld A activ
		If JobPara.Activ_Fields = 1 Then
			' Werkstueck links - X-Pos rechts
			Marker.AutoXStrategie = 1
		ElseIf JobPara.Activ_Fields= 2 Then
			' Werkstueck rechts - X-Pos links
			Marker.AutoXStrategie = 2
		Else
			'Kopplung aktiv
		
			For c_part = 1 To UBound(WPI)-1
				' Pruefen ob Werkstueck an A oder D anliegt
				If WPI(c_part).Sox < l_KoppelWert Then
					' Teil liegt an Feld A Anschlag
					l_FeldA      = True         
					' Pruefen ob rechte Kante Werkstueck ueber Koppelgrenze geht 
					' Stop offset x + workpiece offset x + workpiece x
					If (WPI(c_part).Sox + WPI(c_part).WPox + WPI(c_part).WPx) > l_KoppelWert Then
						l_KoppelAD = True
					End If 
				Else
					'Teil liegt auf Feld D Anschlag 
					l_FeldD      = True         
					' Pruefen ob rechte Kante Werkstueck ueber Koppelgrenze geht 
					' Stop offset x + workpiece offset x + workpiece x
					If (WPI(c_part).Sox - WPI(c_part).WPox - WPI(c_part).WPx) < l_KoppelWert Then
						l_KoppelDA = True
					End If
				End If 
			Next
	
			If l_FeldA=True And l_FeldD=True Then
				'beide Felder mit Werksuecke belegt
				If l_KoppelAD=True And l_KoppelDA=True Then
					'beide Teile ragen jeweils in andere Feld -> X-Pos rechts dann links
					Marker.AutoXStrategie = 14
				ElseIf l_KoppelAD=True Then
					'nur A Teil ragt in D Bereich, Teil D kurz  --> X-Pos rechts
					Marker.AutoXStrategie = 15
				ElseIf l_KoppelDA=True Then
					'nur D Teil ragt in A Bereich, Teil A kurz  --> X-Pos links
					Marker.AutoXStrategie = 16
				Else
					'kein Teil ragt in anderen Bereich kurze Teile + Handkoppeln --> X-Pos Mitte
					Marker.AutoXStrategie = 13
				End If
			ElseIf l_FeldA=True Then
				'nur Feld A Belegt mit langem Teil --> X-Pos rechts
				Marker.AutoXStrategie = 11
			ElseIf l_FeldD=True Then
				'nur Feld D Belegt mit langem Teil --> X-Pos links
				Marker.AutoXStrategie = 12
			End If
		End If
		'Marker.AutoXStrategie:
		'1	=Teil nur A 
		'2	=Teil nur D
		'11	=Teil nur A lang
		'12	=Teil nur D lang
		'13	=Teil A+D kurz
		'14	=Teil A+D beide lang
		'15	=Teil A+D A lang, D kurz
		'16	=Teil A+D D lang, A kurz
	End If
		
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

	If JobPara.isg Then
		NCExt=ISG_EXT_MAIN
	End If

    'open file and write NC-start
    NCNameGlobal=NCName
   	JobPara.NPX=Add_X   ' G54 Nullpunkt X
   	JobPara.NPY=Add_Y   ' G54 Nullpunkt Y
   	JobPara.NPZ=Add_Z   ' G54 Nullpunkt Z
    
    If Add_Z <=0 Then
    	    ' MW 31.03.2006
	    'MsgBox("Achtung - keine Saugerhoehe definiert")
	End If
    
	SetNCName(NCName,NCExt,ncpathGlobal)
    FileOpen(NCName+NCExt)
    Call SaveFinishedPart(FX,FY,FZ)
   	Call wcncHeader(NCName+NCExt,TDB,FX,FY,FZ,Comment,Add_X,Add_Y,Add_Z)


'Dim tip,rot As Integer 
'Const kangle=55
'	For rot = 0 To 360 Step 45
'		For tip = -115 To 115 Step 1
'			wcncwo(";Rot:  "+inttos(rot)+ " ; Tip:  "+inttos(tip)+" ; BAchse "+ Ftos((GetKartanAngleTipAxisWBAxis_D(rot, tip, kangle)))+" ; CAchse "+ Ftos((GetKartanAngleRotAxisWBAxis_D(rot, tip, kangle))))
'		Next tip
'	Next rot


End Sub


Sub ToolChange(BoxNo,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,pspeed,d12,d13,d14,d15,d16,d17,d18,d19,d20,d21,d22,d23)
Dim bmcode As TBMuster
Dim	GB_TC_Output As Boolean   ' Wechsel von Ausgang zu Ausgang

	If (BoxNo > 0) And (Not equal(PPara.Speed,pspeed)) Then
		pp_err(126,"PSpeed")
	End If
	If (BoxNo > 0) And (Not equal(PPara.ToolID,BoxNo)) Then
		' Processpara check auf Boxno
		pp_err(126)
	End If

	' Neu MW 15.09.2005
	' FirstTime - Viewchange True setzen, je nach Einstellung
	Reset_FirstTime_Viewchange
	
	GB_TC_Output = False   ' Wechsel von Ausgang zu Ausgang
	

	' letztes benutztes Werkzeug auf Lastt schreiben
	If Not ActT.t Is Nothing Then
	
		Set_LastTool_ActTool
	
		' -- end Neu MW 11.04.2007 -- 5 Axis
	Else
		If Not LastT.t Is Nothing Then
			Set LastT.t = Nothing
		End If
	End If

	' Muss vor der Werkzeugabwahl stehen, damit Werkzeugabwahl weiss, dass z.B. Spindel ausgeschaltet werden
	' muss
	If BoxNo > 0 Then
		MT_SetTHopsBasicToolExt(ActT,BoxNo,PPara.HId)
	End If
	
	If Not MT_IsDH(actT) And Not MT_isDHSaw(actT) Then
		' MW 31.03.2016 HeadInfo eleminiert!
		If JobPara.isg Then
			wcnc("L CYCLE [NAME=CP_CLEARDH.NC @P1=1]")
		End If 	
	End If

	
	
	' Werkzeugabwahl 
	If Not Lastt.t Is Nothing Then
		MT_Tool_Re_Change(LastT,IIf(BoxNo<0,-1,lastt.t.ID))
	End If
	If BoxNo<0 Then
		' nur abwahl am Schluss
		Exit Sub
	End If
	
	' Auf sicherheit, da nach bohren und anschliessender Bearbeitung
	' mit HS sonst nicht hochgefahren wird
	If Not Firsttime_Viewchange Then
		Z_Is_Safety=False
	End If
	
	If MT_isDH_wasDH(ActT,LastT) Then
		' war ist Bohrkopf nicht hochfahren
		' und keine WEchsel von Bohrkopf Saegen auf Bohrkopf bohren 
	Else
	
		' MW 04.01.2011 - Kombi-Tools
		'If Not MT_GB_Output_Changed(ActT,LastT) Then
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
			' -- 
			' --  MW 03.12.2008 17:25:22
			' --
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

	' -------------------------------------------------------------
	' MW 12.12.2012  Jumps 
	' -- Einsprungmoeglichkeit zu einem bestimmten Werkzeugwechsel
	Jumps_Goto_and_In
	' -------------------------------------------------------------

	' -------------------------------------------------------------
	' -- MW 06.03.2013 Wenn Messwert in 1. Szene benoetigt wird! 
	wcnc_Evo_Mea    
	' -------------------------------------------------------------
	
	If MT_isPneumaticSaw(ActT) Then
		' neu MW 30.06.2005 - schwenkbare Saege
		wcncCom(ActT.T.Description+" "+ " ID:"+IntToS(ActT.T.ID)+" Platz:"+ IntToS(ActT.t.GetPlaceID_OnTC)+" T:"+IntToS(ActT.T.ToolNo))
		
		MT_WZW
		
	ElseIf MT_is_VBM_Stempel(ActT) Then
		' Stempel/Halt mal kurz Vorrichtung 
		' nix tun
		wcncCom("Tooltype :"+IntToS(actt.t.ToolType)+"  -"+ actt.t.Description)

	ElseIf Not MT_isDH(ActT) And ((MT_Is_TC_T(ActT) Or (MT_IsProcessHeadTool(ActT)))) Then
		' neu MW 19.05.2005 - Processhead - Tool
		' Toolchange call except drilling head
		'wcncCom("ToolChange :"+ActT.tc.Description)
		wcncCom(ActT.toolname)
		wcncCom("HEAD:"+IntToS(ActT.hid)+" "+ActT.h.Description)
		wcncCom(ActT.T.Description+" "+ " ID:"+IntToS(ActT.T.ID)+" Platz:"+ IntToS(ActT.t.GetPlaceID_OnTC)+" T:"+IntToS(ActT.T.ToolNo))
		
		MT_WZW
		
	ElseIf MT_isDHSaw(ActT) Then
		' Saege auf Bohrkopf
		If MT_isDH_wasDH(ActT,LastT) Then
			' war ist Bohrkopf kein Wechsel aufrufen
			' und keine WEchsel von Bohrkopf Saegen auf Bohrkopf bohren 
		Else
			MT_WZW
		End If
		
		
	ElseIf MT_isDH(ActT) Then
		' Bohrkopf
		MT_WZW
		
	Else
		pp_err(3)
		' kein Bohr
		MT_WZW
		' necessary ?
		MT_Write_Act_D_Correction
	
	End If
	
	Speed_Call_7 (True)
	
	If MT_IsGearBoxTool(ActT) Or MT_IsGearBoxTool_Special(ActT) Or MT_IsGearBoxTool_TC_Access(ActT) Then	
		wcncCom("Werkzeugtraegerkorrektur - Verrechnung! ")
	End If

End Sub


Sub ToolChangeBefore(BoxNo,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15,d16,d17,d18,d19,d20,d21,d22,d23,d24,d25,d26,d27,d28)
Dim t As IIHopsBasicTool   ' Die Mutter der O-Typen 1-4 hierueber  koennen alle Standard - Eigenschaften abgerufen werden
Dim Dummy As Object
Dim AggOffX, SPVX As Double

'	If Not equal(Headid,HID) Then
'		pp_err(126)
'	End If
	
	Set t= TDATA.GetTool_ID(BoxNo)
	
	' Object merken fuer Vorwechsel
	Set TCB_T.t = TDATA.GetTool_ID(BoxNo)	
	' neu MW 04.08.2004
	If TCB_T.T.ObjectType=htokGearBoxTool Then	
		' Es handelt sich um ein IHopsGearBoxTool (4)
		Set Dummy = TDATA.MachineData
		'Set t.MachineData = dummy

		Set Dummy = TCB_T.T
		'Set t.T_GB = dummy
		Set TCB_T.gb = Dummy.GearBox
		'TCB_T.AggName = t.T_GB.Description
	End If
	
  'AK 21.09.2011 naechste XPosition im ToolChangezyklus mitgeben
	' d18 = AddMx = Werkzeug - Aggregatverschiebung X
	' d33 = SPVX = Anfahrposition auf die Ebene
	'Marker.XPosAfterToolChange=(-1*d18)+d33
	
	' MW 24.09.2012
	AggOffX = d18    ' Werkzeug - Aggregatverschiebung X
	SPVX = d25  ' d33       ' Anfahrposition auf die Ebene
	
	MT_PRECHANGE(AggOffX,SPVX)
	
End Sub

Sub ViewChange(View,LastView,IPX,IPY,IPZ,RotA#,TipA#,SPAX,SPAY,SPAZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
Dim ox As Double
Dim oy As Double
Dim oz As Double   ' Spezial -> fuer pneum. schwenkbare Saege kann Feinjustierung ueber Offsets (Id's im Ausgang) getaetigt werden

	If Not MT_IsMEAS(actt) Then
		WCNC_IDD("CP_DYNAMIC")   ' MW 27.06.2016
	End If

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
		    	MT_Write_Act_T_Correction
		    	MT_Write_Act_D_Correction
		    End If
		    If (ActT.h.UseLiftOffsets) Then
			    DINISO_WRITE_CPLIFT(True)
			End If
			Exit Sub
		Else
			' MW 04.05.2017 - Aggregatsversatz wie bisher verrechnen
			If MT_IS_MainAgg(actt) Then     '  MW 19.12.2018 Aenderung von HH uebernommen - gab wohl eine 3-Achs - Maschine mit DINISO - Betriebe MT_Is_Vertical_StandardTool5Axis(ActT) Then
				ox = -ActT.h.CenterX
				oy = -ActT.h.CenterY
				oz = -ActT.h.CenterZ
			Else
				pp_err(0,"wrong Tool DINISO-CALL")
			End If
			
		End If
		
	End If
	If MT_IsProcessHeadTool(ActT) And Not MT_isPneumaticSaw(ActT) And equal(TipA,90) Then
		' SuperSonderSpecial 
		' Steuerung macht Gleitkommarechenfehler, wenn 
		' AROT Z180 X90 und keine TCARR - Funktion aktiv
		If Not JobPara.isg Then
			' -- 
			' --  MW 11.12.2008 11:48:59
			' --
			' -- gilt natuerlich nicht fuer ISG
			TipA = TipA + 0.001
		End If
		
	End If

	wcnc_Workpiece_Info
	
	If MT_is_VBM_Stempel(ActT) Then
		' -> Evolution
		Exit Sub
	ElseIf MT_IsMEAS(actt) Then
		' MW 24.04.2019 meas
		Exit Sub
	End If
	
	LastV=ActV
	
	Call ViewSave(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPAX,SPAY,SPAZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
	
	PosReset
	
   	If MT_isDH(ActT) Then
	   Marker.Last_DH_Process=""
   	   DH_View0= ActV
   	   Exit Sub
	End If
   	
	wcncCom("Viewchange View "+View, True)
	
	If MT_Is_GearBoxTool_With_FreeTiltAxis(actt) Or MT_IsGearBoxTool_TC_Access(actt) Then
		' --
		' --  Winkelgetriebe mit frei schwenkbarer Kippachse (GB with 5th-Axis) / Winkelgetriebe mit Wechslerzugriff
		' ----------------------------------------------		
		wcncCom("Stellachse (5.Achse) auf "+FToS(ActV.TipA))
		If Mill_c_Activ() Then
			' - CAchs fraesen
			MT_Request_Flexible_Axis(Abs(Get_mill_c_kw),-99999)
		Else			
			MT_Request_Flexible_Axis(ActV.TipA,ActV.RotA)	

			WCNC_IDD("TCARRACTIVATE",actt.t.ToolNo,actt.t.CorrNo)
		End If
	End If
	
	If PostSettings.GeneralSettings.RelativToRefSpindle Then
		If MT_isPneumaticSaw(ActT) Then
			' -- 04.03.2006
			' -- Offset pneumatische S�ge �ber Zusatzinfo vom Ausgang verrechnen
			' --
			MT_GetOffsets_Pneumatic_Saw(actt,MT_GetPneumaticSawAngle(actt,TipA,RotA),ox,oy,oz)
		End If
' MW 23.03.2016  ???????????????????? war wohl mal ein test !!!!			
'			If MT_Is_Vertical_StandardTool5Axis(ActT) Then
'				' Bezugspunkt Plananlage Spindel - hier Offset runter rechnter - oder TCP anders definieren
'				wcnc(g_OffPX+"="+FToS(ox)+ " "+g_OffPY+"="+FToS(oy)+ " "+g_OffPZ+"="+FToS(oz)+"+("+FToS(-actt.h.RotPointOffZ)+")")
'			Else
			wcnc(g_OffPX+"="+FToS(ox)+ " "+g_OffPY+"="+FToS(oy)+ " "+g_OffPZ+"="+FToS(oz))
'			End If
	Else
		pp_err(0,"wrong settings")
		' ??????????? eigentlich Quatsch
		'MT_Write_Offset_NC_Vars(ZOffGes)' Offsets auf OOX, OOY, OOZ schreiben OOX=-207.39 OOY=-112.35 OOZ=-50
									' without rotating output - offset
	End If

	WCNC_IDD("TRANSOFF")
	' ???	MT_Write_CPLift(Marker.LiftPos_StartUp)
	
	wcncCom("INFO - IM IPZ wird beim vertikalen Fraesen der Offset Z vom Aggregat eingerechnet",True)
	
	' MW 21.01.2016 - TCP vor CS Ebene
	If MT_Is_Vertical_StandardTool5Axis(ActT) Then
		' 5-Axis 
		WCNC_IDD(JobPara.TCP_ON)
		WCNC_IDD("STOPRE")
		wcnc("G"+IntToS(53+Fix_Zero))
	End If

	Get_Measure_Offset_Vars()  ' strix,striy,striz)  ' MW 24.04.2019 meas

	WCNC_IDD("ATRANSAROT",IPX,IPY,IPZ,RotA,TipA)
	'???	MT_Write_CPLift(Marker.LiftPos_Processing)
		   	

	wcncCom("ViewchangeEnd", True)
	'If ActV.View<>0 Then
		Z_Is_Safety=False
	'End If
	Firsttime_Viewchange = False
	Z_Is_SafetyPart=False
	
' MW 23.12.2015 bei ISG bis dato nicht mehr verwendet    
'	Pneumatic_On
	


	Speed_Call_7()  ' MW 31.03.2016
End Sub

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
		MT_WRITE_DHCode(ActT,ActT.t_dhsaw.DH_ToolPlace.ToolNo)
	End If

	PosReset
	MoveParaReset
	MT_Write_Check_Spindle
	
	If MT_Is_UndersideTool(ActT) Then
		wcncCom("****** Unterflurfraesen ****")
		
		' --
		' -- Unterflur-Getriebe
		' Berechnung der Ebenenausrichtung anhand von Tangle und der aktuell eingestellten Ebene
		' --
		MT_Underside_Set_Param_Angle(ActT,TAngle)
		' --
		' --
		' Korrektur aufrufen, und offsets setzen
		MT_Write_Call_Correction
	Else
		' Standard
		wcncCom("--")
		wcncCom("--      Milling ")
		wcncCom("--")
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

'	WCNC_IDD("CONTOUR_END")

	MT_NoTurningWithSpindelRot_OFF(actt)

'	If ((Retreat=1) And (ActV.View<>0)) Or (mt_is_undersidetool(ActT) Or (Marker.HorMilling_PullBack) Or (FiveAxis.Yes And FiveAxis.ISG)) Then
'		' MW 16.09.2011 bei FiveAxis ISG auch bei Ebene 0 Rueckzug wenn Retreat kommt
'		'Go savety next view isn't equal
'		wsafetyPart(ActT)
'		'If (Marker.HorMilling_PullBack) Then
'		' MW 20.09.2011 
'		' sonst wird kein erneuter Ebenenaufruf gemacht.. es fehlt CS, welcher immer abgeschaltet wird!
'		If (Marker.HorMilling_PullBack) Or (FiveAxis.Yes And FiveAxis.ISG) Then
'			ActV.View=-1
'		End If
'	End If
	
	Marker.Last_SuctionPos = -1
	
	Inc_Process
	
End Sub

Sub Start_Drilling(pno,I_F,F,S_F,S)

	PosReset
	MoveParaReset
	wcncCom("--")
	wcncCom("--      Drilling ")
	wcncCom("--")
	MT_Write_Check_Spindle
	
	
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
	Inc_Process
End Sub


Sub Start_Vertical_DrillingHead_Stroke(pno,I_Feedrate,Feedrate,S_Feedrate,Speed)
	PosReset
	MoveParaReset
	Marker.FirstTime_DH_Drilling = True
	Marker.Programmed_DH_Speed = Speed

	LastV.IPX=-99999
	LastV.IPY=-99999
	LastV.IPZ=-99999

	wcnc_IDD("G602")
	
	' Dynamik Bohrkopf aktivierbar ueber BK ID 1100
	If Not actt.t_DH.DrillingHead.Additions.GetAddition_ID(1100) Is Nothing Then
		If Val(actt.t_DH.DrillingHead.Additions.GetAddition_ID(1100).Value) > 0 Then
			wcnc_IDD("CP_DRILLSTART",Val(actt.t_DH.DrillingHead.Additions.GetAddition_ID(1100).Value))
		End If
	End If
	
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
Dim zmax As Double

	Get_Measure_Offset_Vars(SNo)    ' MW 24.04.2019
	
	Evo_Check_MeaDrill(PosFirstX)   ' Pruefung ob Bohrung im Bereich zum Verrechen mit Messwert


	' Tool-No des 1. Bohrers aus dem Hub
	FirstTNr = Val(Get_First_Token(tools))   

	Set itp= actt.t_dh.DrillingHead.ToolPlaces.GetToolPlace_PlaceID(FirstTNr) ' liefert BasicToolplace zurueck
	' deshalb instanz so erzeugen
	Set Dh_TP=itp

	' ------------------------------------------------
	' Bohrdaten Bohrkopf
	' Vorschuebe vom Bohrkopf
	' es wird davon ausgegangen, dass eine Vorschubsaenderung ueber Werkzeugaufruf
	' eine gewollte Vorschubsdefinition ist
	' ------------------------------------------------


	' NEU MW 08.07.2006
	dh.G0_up = Not Marker.No_G0_Up_DH
	
	' Neu MW 27.04.2005
	' setzt die dh und driller  - Daten 
	' MT_SetDrillingHeadData(tools, dh,Driller)
	
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

	' 06.03.2014 fuer die Richtung der Verrechnung
	JobPara.mea.Orientation = Driller.tp.Orientation
	
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
	If (Marker.Last_DH_ToNo<>Driller.Tno) Then
		' Laengenkorrektur aktivieren fuer 1. Bohrer des Hubs
		wcnc("T"+inttos(Driller.TNo)+ " D1")
	End If
	
	If Marker.Last_DH_Process = DRILL_DHH Then
		' letzte Bearbeitung fand mit horizontal Spindeln statt
		' hor. Bohr Spindeln zuruecklegen
		wcnccom("hor. Bohrspindeln zuruecklegen")
		MT_WRITE_DHCode(actt,"")
	End If
	
    If Not Marker.Last_DH_Process = DRILL_DHV Then
    	' letzter Hub war kein Vertikal drilling head hub
    	' also Ebene setzen
        Call wcncViewChange_DH(dh,DH_View0.View,DH_View0.LastView,DH_View0.IPX,DH_View0.IPY,DH_View0.IPZ,DH_View0.RotA,DH_View0.TipA,PosFirstX,PosFirstY,DH_View0.SPVZ,DH_View0.Vxx,DH_View0.Vxy,DH_View0.Vxz,DH_View0.Vyx,DH_View0.Vyy,DH_View0.Vyz,DH_View0.Vzx,DH_View0.Vzy,DH_View0.Vzz)
    End If
    
    
	'If Firsttime_Viewchange Then 
	' neu mw 28.04.2005
	'If Firsttime_Viewchange Or Is_WP_Change Then 
	' Neu MW 28.06.2006
	' Beim Bohren mit Bohrkopf kommt zwischen den Bohrungen kein workpieceindex
	If Firsttime_Viewchange Then 
	    ' 1. Anfahrt auf Werkstueck
		' bei ersten mal wird immer ohne Z angefahren
		
		wcnc(G0+XEqualToS(PosFirstX)+YEqualToS(PosFirstY))
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
		Drilling_DH_Cylce_20(PosFirstX,PosFirstY,Depth,actt.t_dh.GetSecurityZ(0),Driller,dh,tools,zmax)
	ElseIf (DFlag >29) And (DFlag<40) Then
		' Bohrzyklus Topfband mit Verweilzeit bohren
		Drilling_DH_Cylce_30(PosFirstX,PosFirstY,Depth,actt.t_dh.GetSecurityZ(0),Driller,dh,tools,zmax)
	Else
		'If (DFlag >9) And (DFlag<20) Then
		' Bohrzyklus Sackloch bohren
		Drilling_DH_Cylce_10(PosFirstX,PosFirstY,Depth,actt.t_dh.GetSecurityZ(0),Driller,dh,tools,zmax)
	
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


Sub Horizontal_DrillingHead_Stroke(SNo,View,IPX,IPY,IPZ,RotA,TipA,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz,SPosX,SPosY,PosFirstX,PosFirstY,PosZ,SPosX_V,SPosY_V,PosFirstX_V,PosFirstY_V,SPosZ_V,PosFirstZ_V,Depth,DZ,DType,DFlag_Type,Dummy,tools,DFlag_TypeString)

Dim ox,oy,oz As Double
Dim Dh_TP As IIDH_ToolPlace
Dim itp As Variant
Dim FirstTNr As Long
Dim Code As TBMuster

Dim dh As tDH
Dim Driller As tDriller

	Get_Measure_Offset_Vars(SNo)    ' MW 24.04.2019

	Evo_Check_MeaDrill(PosFirstX)   ' Pruefung ob Bohrung im Bereich zum Verrechen mit Messwert


	FirstTNr = Val(Get_First_Token(tools))
	

	
	Set itp= actt.t_dh.DrillingHead.ToolPlaces.GetToolPlace_PlaceID(FirstTNr)
	Set Dh_TP=itp

	' Bohrdaten Bohrkopf
	' Vorschuebe vom Bohrkopf
	
	' Neu MW 27.04.2005
	' setzt die dh und driller  - Daten 
	' MT_SetDrillingHeadData(tools, dh,Driller)
	' 
	
	' NEU MW 08.07.2006
	dh.G0_up = Not Marker.No_G0_Up_DH
	
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
	
	' 06.03.2014 fuer die Richtung der Verrechnung
	JobPara.mea.Orientation = Driller.tp.Orientation
	
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
	If (Marker.Last_DH_ToNo<>Driller.Tno) Then
		wcnc("T"+inttos(Driller.tno)+ " D1")
	End If



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

	JobPara.mea.Bea_Mea_activ = False
	
	' Dynamik Bohrkopf aktivierbar ueber BK ID 1100
	If Not actt.t_DH.DrillingHead.Additions.GetAddition_ID(1100) Is Nothing Then
		If Val(actt.t_DH.DrillingHead.Additions.GetAddition_ID(1100).Value) > 0 Then
			wcnc_IDD("CP_DRILLEND")
		End If
	End If

	wcnccom("Bohrspindeln zuruecklegen")
	MT_WRITE_DHCode(actt,"")
	
	wcnc_IDD("TRANSOFF")
	' zusaetzlichen Sicherheitsabstand einrechnen
    wcnccom("Additives ZMass:"+ftos(GetAddZSic))
	
	wcnc("G0 Z"+Ftos(actt.t_dh.GetSecurityZ(0)+(FinishedPart.Z+GetAddZSic)))
	Marker.FirstTime_DH_Drilling=False
	Marker.Last_DH_ToNo	= -9999   ' Sonst wird Korrektur nicht neu angewaehlt, wenn dazwischen z.B. eine Fraesbearbeitung stattfindet!
	Inc_Process
	wcnc_IDD("G601")

	Marker.Last_DH_Tools = ""
	
End Sub

Sub NC_End()

	Call ToolChange (-1,"Schrupper D20","",10300,2,1,5,5000.000000,1200.000000,60000.000000,18000.000000,12434.000000,0.000000,50.000000,50.000000,10.000000,88.000000,1.560000,160.000000,-180.000000,0.000000,0.000000,0.000000,1)
	
	If JobPara.isg Then
		wcnc("L CYCLE [NAME=CP_CLEARDH.NC @P1=1]")
	End If 	
  
  	Check_Jumps  ' MW 12.12.2012 Pruefung auf gleiche Anzahl, und wegschreiben der Jumplist

	wSafetyAbs(False)
	EndandPark
	wcnc("M30")
	FileClose
	
	If mPara_Add.Script_Info=True Then
		AddLog("BASIC SCRIPT - DURCHLAUF GESAMT: "+ftos(Timer-JobPara.TimerFullSecs)+" sec")
		If MT_Get_MachPara_Add(1102) = "1" Then
			Write_DebuggerLog
		End If
	End If
	
	ClearMTData  
	
	ClearObjects
	
	MeasureInfos_Final()  ' MW 24.04.2019

End Sub

Sub NCInfo(Kind,NCType,Para1,Para2,Para3,Para4,Para5,Para6,Para7,Para8,Para9,characters)

	Handle_NCInfo(Kind,NCType,Para1,Para2,Para3,Para4,Para5,Para6,Para7,Para8,Para9,characters)
End Sub


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
	
'	' -- AK 04.05.2011
'	' -- Kennung setzten fuer letztes Werkzeug vor WZW
'	ViewInfoToolChangeFlag=True
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

Sub SP_EP_No_LeadInOut(SP_x,SP_y,SP_z,SP_ax,SP_ay,SP_az,SP_Feedrate,SP_Speed,SP_RotA,SP_TipA,SP_TRC,SP_TA,SP_Distance, _
                       EP_x,EP_y,EP_z,EP_ax,EP_ay,EP_az,EP_Feedrate,EP_Speed,EP_RotA,EP_TipA,EP_TRC,EP_TA,EP_DMove,EP_DFactor,EP_Retreat, _
                       Dummy1,Dummy2,Dummy3,Dummy4,Dummy5,Dummy6,Dummy7,Dummy8,Dummy9,Dummy10,Dummy11,Dummy12,Dummy13,Dummy14,Dummy15,Dummy16,Dummy17,Dummy18,Dummy19,Dummy20)
  Call SP_EP_No_LeadInOutSave(SP_EP,SP_x,SP_y,SP_z,SP_ax,SP_ay,SP_az,SP_Feedrate,SP_Speed,SP_RotA,SP_TipA,SP_TRC,SP_TA,SP_Distance, _
                       EP_x,EP_y,EP_z,EP_ax,EP_ay,EP_az,EP_Feedrate,EP_Speed,EP_RotA,EP_TipA,EP_TRC,EP_TA,EP_DMove,EP_DFactor,EP_Retreat, _
                       Dummy1,Dummy2,Dummy3,Dummy4,Dummy5,Dummy6,Dummy7,Dummy8,Dummy9,Dummy10,Dummy11,Dummy12,Dummy13,Dummy14,Dummy15,Dummy16,Dummy17,Dummy18,Dummy19,Dummy20)
End Sub

'Sub Start_NCInfoProcess (PNo,I_F,F,S_F,S)
' MW 01.04.2016 nicht mehr notwendig
'End Sub

Sub NCInfoProcess(InfoTyp,x1,y1,z1,x2,y2,z2,w1,w2,w3,w4,w5,w6,w7,w8,w9,w10,w11,w12,w13,w14,w15,w16,w17,w18,w19,w20,w21,str1,str2)
	
	If Not MT_IsMEAS(actt) Then 
		wcnccom("NCInfoProcess : "+inttos(InfoTyp),True)
	End If
	Handle_NCInfoProcess(InfoTyp,x1,y1,z1,x2,y2,z2,w1,w2,w3,w4,w5,w6,w7,w8,w9,w10,w11,w12,w13,w14,w15,w16,w17,w18,w19,w20,w21,str1,str2)

	Inc_Process

End Sub


Sub ClampChange(par1,par2,par3,par4,par5,par6,par7,par8,par9,par10,par11,par12)
Dim pcount, i,No As Integer
Dim para,pstri, p3,p4,p5,p6 As String 
Dim Next_Working_Box,Next_Working_Head As Long 
Dim Same_Tool_Next, MultiSzene As Boolean 
Dim d As Variant 
Dim tmp_Speed As Double 


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
		' � Bei Bit 7 in Parameter p3 � Kennung f�r Multiszene setzen 
		If (p3 And 128)>0 Then
			MultiSzene=True
		End If
	End If

	MT_GetToolId_Next_Process(Next_Working_Box,Next_Working_Head)

	
	If (Next_Working_Box > 0) And (Not actt.t Is Nothing) Then
		' -- nach umspannen muss eigentlich immer noch eine Bearbeitung kommen! 
		If equal(Next_Working_Box,actt.t.ID) Then
			wcnccom("Naechstes Werkzeug:"+inttos(Next_Working_Box)+" ist auch aktuelles Werkzeug")
			Same_Tool_Next = True
		End If
		
		MT_Tool_Re_Change(actT,-1) ' M5 AUS !! 
		
	End If
	'AK 22.04.2015 Antriebe vor letzen Szenenaufruf
	If (Next_Working_Box < 0) And (Not actt.t Is Nothing) Then
		MT_Tool_Re_Change(actT,-1) ' M5 AUS !! 	
	End If
	
	If JobPara.isg Then
		'MsgBox("CP_Szene  " + ftos(par1)+ " "  + ftos(par2)+ " " + ftos(par3)+ " " + ftos(par4)+ " "+ par12)
		wcnc("""SZENEMESSAGE"" = """ + pstri + """")
		wcnc_Idd(SPF_Szene,ftos(par1),ftos(par2),-1,p3)
		'wcnc_Idd("CP_Szene",ftos(par1),ftos(par2+1),-1,p3,p4,p5,pstri)
		
	Else
		wcnc("CP_Szene("+ftos(par2+1)+",-1,,"+ftos(par3)+")")
	End If

	
	If JobPara.is_evo Then
	
		wcnc(ISG_MEA_X+"= 0")
	
		wcnc_Move_Zangen(par1,par2)
		
		wcnc_Evo_Mea

	End If

	If Same_Tool_Next = True Then
		' es geht mit gleichem Werkzeug weiter 
		' Spindel wieder einschalten
		If Not MT_IsDH(actt) Then
			tmp_Speed = Marker.LastSpeed   'ProcessPara.Speed
		End If
		
		' -- AK 22.01.2018 
		' � Bei Multiszene wird kein Toolspeed ausgegeben 
		If (tmp_Speed > 0) And (MultiSzene=False) Then
			MT_Write_Speed(ActT,tmp_Speed)
		End If

		'Call ToolChange(actt.t.ID,d,d,d,d,d,d,d,d,d,d,ProcessPara.Speed,d,d,d,d,d,d,d,d,d,d,d,d,d,d,d,d,d,d,d,d,d,d)	
	End If


End Sub

Sub LeadInOutWithoutSafety (an,ab)
		
End Sub

Sub ProcessIndex (PListNo)  ' gibt die ProcessNummer des folgenden Prozesses bekannt
	ProcessInfo_Set(PListNo) 
	If Not MT_IsMEAS(actt) Then 
		wcnccom(JobPara.P_Info,True)
	End If
	
End Sub

Sub Process_Start(ProcId,BoxId,HeadID,d1,d2,ProcC,XMin,YMin,ZMin,XMax,YMax,ZMax)
    Marker.LastLiftpos = -1
'    Marker.LiftPosStartup = -1
'    Marker.LiftPosProcessing = -1
	
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
	If Not MT_IsMEAS(actt) Then
		' MW 24.04.2019 - nicht fuer Messtaster
		DLLMPs(Kind,pno)
	End If
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

Sub ProcessInfo (s,d,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15,d16,d17)

	
End Sub
