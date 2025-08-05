' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \hh7\pp_ncinfo.bas
' -- 
' -----------------------------------------
'#uses "pp_math.bas"
'#uses "pp_global.bas"
'#uses "pp_mt.bas"
'#uses "pp_mtf.bas"
'#uses "pp_bohrdh.bas"
'#uses "pp_laser.bas"
'#uses "pp_isg.bas"
'#uses "pp_measure.bas"

Option Explicit         ' -- MW 15.04.2008 11:40:52

	
	
Function Handle_NCInfo(Kind,NCType,Para1,Para2,Para3,Para4,Para5,Para6,Para7,Para8,Para9,characters)

Dim n As Integer
Dim C As Integer
Dim s As Variant   ' -- MW 15.04.2008 11:40:52
Dim BL_NCI(1)
Dim BL_Global(1) As Integer 
Dim i As Integer 	
	BL_NCI(0)=7710    ' DINISO - Mode,Liftpos,WZW,Speed,Viewchange
	BL_NCI(1)=8810    ' DINISO - ENDE, erzwingt Ebenenwechsel
	
	BL_Global(0)=55   ' altes parken
	BL_Global(1)=58   ' Steuert Rueckzugsverhalten beim Bohren/Fraesen -> nicht mehr zugelassen.

  If Kind=0 Then
  	 For i = 0 To UBound(BL_NCI) 
  	 	' Blacklist pruefen
  	 	If equal(NCType,BL_NCI(i)) Then
  	 		pp_err(1553,BL_NCI(i))
  	 	End If
	 Next i 
  
	If NCType=8201 And (PPara.Din_ISO_8201 = False) Then
       ' -- NCZeile direkt absetzen _diniso.hop -> Nachwirksam
       wcnc(characters)
    End If
 
    If NCType=10 Or NCType=11 Then
    	pp_err(1553,NCType)
	    'wcnc_nci_10_or_11(NCType,Para1)
    End If
    
' MW 23.12.2015 bei ISG bis dato nicht mehr verwendet    
'    If NCType=7100 Then
'    	' Pneumatik Channel an HH_Pneu_Channel_On.hop
'    	' Nur merken, da Befehl sonst viel zu frueh abgesetzt
'    	SetPneumatic_Marker(Para1)
'    End If
'    If NCType=8100 Then
'    	' Pneumatik Channel aus
'    	Pneumatic_Off(Para1)
'    End If
    
    ' --------------------------------------------------------
    ' - DIN ISO 
    ' - ueber Systemmakro _DINISO_CALL.HOP kommt
    ' - NCINFO 7710 
    ' - NCINFOProzess 7710
    ' - NCINFO 8711
    
'    If NCType=7710 Then
'    	' Neu MW 19.10.2005
'    	' DINISO - Programm folgt
'    	Set_DINISO_Marker(Para1,Para2,Para3,Para4,Para5)
'    End If
    
	If NCType=8810 Then
		' -- NCZeile DIN-ISO ENDE 
		' Neu MW 10.06.2015
'		ActV.View = -1
'		wsafetyPart(ActT)
	End If
    
    If NCType=7711 Then
    	' Neu MW 9.11.2005
    	' DINISO - LINE
    	' Neu MW 11.11 Line auch mit | - Zeichen als Zeilenumbruch
    	WCNC_LINE_With_Seperator(characters)
    	'WCNC(characters)
    End If
    If NCType=8711 Then
    	' DINISO - LINE aufgerufen von _DINISO_CALL.HOP
    	' "|" - Zeichen als Zeilenumbruch
    	WCNC_LINE_With_Seperator(characters)
    	'WCNC(characters)
    End If
    ' --------------------------------------------------------
    
    If NCType=8200 Then
    	' MW 21.12.2015
    	' den gibt es nicht mehr
    	' Maschinen stop mit Parken und M0
    	'Machine_Stop(Para1,Para2,Para3,characters)
    End If
    
    
  ElseIf Kind=1 Then
	' NCZeile direkt zwischen G-Befehlen	
	If (NCType=200) Then
		wcnc(characters)
	End If
' MW 23.12.2015 bei ISG bis dato nicht mehr verwendet    
'	If NCType=7100 Then
'    	SetPneumatic_Marker(Para1)
'		Pneumatic_On
'	End If
  ElseIf Kind=4 Then
  	 ' Globale Schalter
  	 For i = 0 To UBound(BL_Global) 
  	 	' Blacklist pruefen
  	 	If equal(NCType,BL_Global(i)) Then
  	 		pp_err(1553,BL_Global(i))
  	 	End If
	 Next i 
  	 
  	 If (NCType=57) Then
  	 	Marker.No_G0_Up_DH = True
  	 End If
'  	 If (NCType=NCINFO_HORMILLING_PULLBACK) Then
'  	 	' -- 
'  	 	' --  MW 21.06.2007 14:01:38
'  	 	' --  erzwingt den Rueckzug nach jeder horizontalen Fraesbearbeitung
'  	 	Marker.HorMilling_PullBack = IIf(Para2=1,True,False)
'  	 End If
  	 
'	If Not TDATA.MachineData.MachineParameter.CreateNCDataAdditions.GetAddition_ID(-200029) Is Nothing Then
'		NCI_Senken  = Val(TDATA.MachineData.MachineParameter.CreateNCDataAdditions.GetAddition_ID(-200029).Value)
'	Else
'		NCI_Senken  = 64  
'	End If
 	If NCType = 64 Then   ' NCI_Senken Then
 	    Marker.RollerTrackDown = True
 		'wcnc("M155")
 	End If
 	
	If (NCType = 91) And (JobPara.is_evo) And (UCase(characters)="QUOTE") Then
		' MW 05.03.2014
		JobPara.Mea.QuoteXQD = Para1
		If JobPara.Mea.QuoteXQD > JobPara.Mea.MaxQuoteX Then
			pp_err(580,JobPara.Mea.QuoteXQD,JobPara.Mea.MaxQuoteX)
			'AddMistake(GetErrMsg(475,"_Maximale Qoute fuer Messwertverrechnung zu gross !",1)) 
		End If
	End If

  	 
  	 
  End If

End Function


Function Handle_NCInfoProcess(InfoTyp,x1,y1,z1,x2,y2,z2,w1,w2,w3,w4,w5,w6,w7,w8,w9,w10,w11,w12,w13,w14,w15,w16,w17,w18,w19,w20,w21,str1,str2)
Dim obj
Dim BL_NCI(1)
Dim i As Long
Dim ax1,ay1,az1,ax2,ay2,az2 As Variant
Dim ax,ay,az As Variant
Dim LOX As Double 
Dim LOY As Double
Dim LOZ As Double
Dim NCIP_MPs As Object
Dim NCI As Object 
Dim NCIExt As Object 
Dim CodeLine As String     
Dim Para1 As Double 

Dim MeasurePointInfo As TMeasurePointInfo

	LOX = 0 
	LOY = 0 
	LOZ = 0

	BL_NCI(0)=7710    ' DINISO - Process
	BL_NCI(1)=7711    ' DINISO - Process alt
	
	For i = 0 To UBound(BL_NCI) 
		' Blacklist pruefen
		If equal(InfoTyp,BL_NCI(i)) Then
			pp_err(1590,BL_NCI(i))
		End If
	Next i 
		
    If InfoTyp=77710 Then
    	' DINISO - Process
    	
    	' Neu AK 28.09.2015 - Aggregate pruefen, Vorlegestufe erreicht,
    	MT_Write_Check_Spindle
    	
		' Bewegung absetzen - same As simu    
		If PPara.ObjectTyp = otNCInfoProcessMPs Then
			' als Milling definiert - hier die uebergebene Position anfahren
			DINISO_WRITE_CPLIFT(False,LOX,LOY,LOZ)  ' Liftoffsets holen
			x1=x1-LOX
			y1=y1-LOY
			z1=z1-LOZ
			x2=x2-LOX
			y2=y2-LOY
			z2=z2-LOZ
			
			If IsDINISO_No_VC Then
				' ohne Viewchange
				
				If MT_Is_Vertical_StandardTool5Axis(ActT) Then
					' Fuer 5-Axis muss TCP aktiv sein
					WCNC_IDD(JobPara.TCP_ON)
					WCNC_IDD("STOPRE")
					wcnc("G"+IntToS(53+Fix_Zero))
				End If
				
				NCData.ProcessList.GetProcess_NCInfoIndex(ppara.PLNo-1).View.GetAxAyAz(x1,y1,z1,ax1,ay1,az1)
				NCData.ProcessList.GetProcess_NCInfoIndex(ppara.PLNo-1).View.GetAxAyAz(x2,y2,z2,ax2,ay2,az2)
				
				ax1 = ax1 + ActT.h.CenterX
				ay1 = ay1 + ActT.h.CenterY
				az1 = az1 + ActT.h.CenterZ
				ax2 = ax2 + ActT.h.CenterX
				ay2 = ay2 + ActT.h.CenterY
				az2 = az2 + ActT.h.CenterZ

			
				'az1= -WPI(Marker.wp_actindex).WPz - az1	' Is the working depth
				'az2= -WPI(Marker.wp_actindex).WPz - az2
				
				wcnc("G1"+Move(ax1,ay1,az1,PPara.Feedrate,0))
				wcnc("G1"+Move(ax2,ay2,az2,PPara.Feedrate,0))
			Else	
				' mit Viewchange auf die Ebene bezogen
				
				x1 = x1 + ActT.h.CenterX
				y1 = y1 + ActT.h.CenterY
				z1 = z1 + ActT.h.CenterZ
				x2 = x2 + ActT.h.CenterX
				y2 = y2 + ActT.h.CenterY
				z2 = z2 + ActT.h.CenterZ
				
				wcnc("G1"+Move(x1,y1,z1,PPara.Feedrate,0))
				wcnc("G1"+Move(x2,y2,z2,PPara.Feedrate,0))
			End If
		End If
    	
    	'ID = Para1
    	'HeadID = Para2
    	If Len(str1)>0 Then
		    WCNC_LINE_With_Seperator(str1)
    	End If
    	If Len(str2)>0 Then
		    WCNC_LINE_With_Seperator(str2)
	    End If
    	
    	' spez. NCIExt -7710 -> Dieser NCIExt wird für die  Scriptausgabe [PP] unterdrückt 
		Set NCIP_MPs = NCData.ProcessList.GetProcess_NCInfoIndex(ppara.PLNo-1)
		If Not NCIP_MPs Is Nothing Then
'			If Not NCIP_MPs.NCInfoListAfter.GetNCI_Index(i) Is Nothing Then
'				If NCIP_MPs.NCInfoListAfter.GetNCI_Index(i).Kind = -7710 Then
'					wcnccom("DINISO - Lines NCI#-7710 NCAfter Counts - "+inttos(NCIP_MPs.NCInfoListAfter.CountNCI -1),True)
'				End If
'			
'			End If

			For i = 0 To NCIP_MPs.NCInfoListAfter.CountNCI -1 
				Set NCI = NCIP_MPs.NCInfoListAfter.GetNCI_Index(i)
				' ohne diese Logik bei 10000 ISO - Lines 3Sek
				If Not NCI.NCIExt Is Nothing Then
					' alle NCIExt Para2 absetzen
					If (NCI.Kind = -7710) And (NCI.IsAfterProcess=True) And NCI.NCIExt.GetFloat(0,Para1) Then
						Set NCIExt = NCI.NCIExt
						If equal(Para1,1) And NCIExt.GetString(1,CodeLine) Then
				    		wcnc(CodeLine)
						End If
					End If
	'			Else
'						' alle "normalen" NCInfo
'					    If (NCIP_MPs.NCInfoListAfter.GetNCI_Index(i).Kind = -7710) And (NCIP_MPs.NCInfoListAfter.GetNCI_Index(i).Para1 = 1) Then
'					    	wcnc(NCIP_MPs.NCInfoListAfter.GetNCI_Index(i).Text)
'					    End If
				End If
			Next i 
			Set NCIP_MPs = Nothing
			Set NCI = Nothing
			Set NCIExt = Nothing
		End If
		

		' MW 12.04.2018
		' ==> kompatibiltaet NCINFO 8201 
		' hier ueber Object absetzen, da der NCINFO erst nach  Script-Aufruf "DLLMPs_Milling 1,1" kommt

    	' spez. NCInfo 8201 -
		Set NCIP_MPs = NCData.ProcessList.GetProcess_NCInfoIndex(ppara.PLNo-1)
		If Not NCIP_MPs Is Nothing Then
			For i = 0 To NCIP_MPs.NCInfoListAfter.CountNCI -1 
				Set NCI = NCIP_MPs.NCInfoListAfter.GetNCI_Index(i)
				If NCI.NCIExt Is Nothing Then
					' wenn nothing dann muss es ein "alter" NCINFO sein
					' alle NCIExt Para2 absetzen
					If (NCI.Kind = 8201) And (NCI.IsAfterProcess=True) Then
						'Set NCIExt = NCI.NCIExt
						'If equal(para1,1) And NCIExt.GetString(1,CodeLine) Then
				    		wcnc(NCI.Text)
							ppara.Din_ISO_8201 = True   ' kein erneutes absetzen notwendig
						'End If
					End If
	'			Else
'						' alle "normalen" NCInfo
'					    If (NCIP_MPs.NCInfoListAfter.GetNCI_Index(i).Kind = -7710) And (NCIP_MPs.NCInfoListAfter.GetNCI_Index(i).Para1 = 1) Then
'					    	wcnc(NCIP_MPs.NCInfoListAfter.GetNCI_Index(i).Text)
'					    End If
				End If
			Next i 
			Set NCIP_MPs = Nothing
			Set NCI = Nothing
			Set NCIExt = Nothing
		End If

		
		
    	' Fertig - jetzt Ruecksetzen
    	'Reset_DINISO_Marker
		'Marker.DINISO_LIFTPOS = -1
		Last_TC_Call_NCStr = ""   ' sonst danach kein neuer Toolchange aufruf 
		
'		If ppara.PreObjectType = otNCInfoProcess Then
'			' als undef definiert
'			Set obj = NCData.ProcessList.GetProcess_NCInfoIndex(ppara.pno-1)
'			
'		End If
		
'		If ppara.PreObjectType = otNCInfoProcessMPs Then
'			' ProcessNCInfo als Drilling oder Milling
'			Set obj = NCData.ProcessList.GetProcess_NCInfoIndex(ppara.pno-1)
'			wcnc("G1"+Move(obj.Para1x,obj.Para1y,obj.Para1z,ppara.Feedrate,0))
'			wcnc("G1"+Move(obj.Para2x,obj.Para2y,obj.Para2z,ppara.Feedrate,0))
'		End If
    End If
    
'    If InfoTyp=7711 Then
'    	wcnc(str1)
'    End If
    
    If equal(InfoTyp,-200000) And (mt_is_vbm_stempel(actt)) Then
'??????????????		MT_Write_Offset_NC_Vars(0)      ' Head - Offsets
		wcncCom("Werkstueck auf Stempel/Greiferposition fahren!",True)
		wcnc("X"+ftos(x1)+"+"+ ISG_OffPX)
		wcncCom("",True)
	End If
	
	If equal(InfoTyp,-210001) And MT_IsMEAS(actt) Then
		' MW 24.04.2019 - meas
		' Prozess Messen 
		MeasurePointsInfos_AddPoint
		MeasurePointInfo=MeasurePointsInfos_GetMeasurePointInfo_Active
		
		wcnc_measuring(MeasurePointInfo,actt)  ' ((MeasurePointInfo.MpNo\1000)*100)+(MeasurePointInfo.MpNo mod 1000)
	End If
	
	
End Function


Function Machine_Stop(Para1,Para2,Para3,characters,NextBoxWorking,HeadID)

Dim park_merker As Integer
Dim msg,xstr,ystr As String
Dim park As Integer
Dim parkx,parky As Double
	
	park = Para1
	parkx=Para2
	parky=Para3
	msg = characters
	If Len(msg)<=0 Then
		msg = "programmed machine stop - go on with start"
	End If
	xstr=""
	ystr=""
	
	wcnccom("*")
	wcnccom(" Machine STOPP SysNCIEXT -108200 Park:"+inttos(park))
	wcnccom("*")
	
	' MW 11.08.2005 
	' geht nicht, da WerkzeugVorwechsel auch schon einige Bearbeitungen
	' eher kommen kann!
	If Not TCB_T.t Is Nothing Then
		' Toolchangebefore wurde aufgerufen
		If tcb_t.t.ID <> actt.t.ID Then
			' naechstes Werkzeug ein anderes 
			If Not MT_GB_Output_Changed(ActT,TCB_T) Then
				' naechstes Werkzeug nicht auf gleichm Winkelgetriebe
				' dann kann bereits abgeschaltet werden
				'wcncaddcom("M05","toolchange follows")
			End If
		End If
	End If
	park_merker	= JobPara.park
	JobPara.park=park
	
	Get_ParkStrXY(xstr,ystr)  ' holt sich parkstring
	JobPara.park = park_merker
	
	If park=10 Then
		xstr=FToS(parkx)
		ystr=FToS(parky)
	End If
	
	If JobPara.isg Then
		' -- nicht noetig fuer ISG		
	Else
		wcnc(g_DCORRECTIONMARKER+"=$P_TOOL")   ' aktuelle D-Korrektur merken
		
		wcnc("TCARR=0")   ' Werkzeugtraegerkorrektur abwaehlen
	
	End If
	
	' G53 / unterdrueckt keine TRAORI
	If MT_Is_Vertical_StandardTool5Axis(actt) Then
		wcnc_IDD(JobPara.tcp_off)
	End If
	
	wSafetyAbs(False)    ' Z-Hochfahren
	
	If JobPara.isg Then
		If (Len(xstr)>0) And (Len(ystr)>0) Then
			WCNC_ISG_SUPAXY(xstr,ystr)
		ElseIf (Len(xstr)>0) Then
			WCNC_ISG_SUPAX(xstr)
		ElseIf (Len(ystr)>0) Then
			WCNC_ISG_SUPAY(ystr)
		End If
	Else
		If (Len(xstr)>0) And (Len(ystr)>0) Then
			wcnc("G53 G0 X="+xstr+" Y="+ystr)  ' X-Y Positionierung
		ElseIf (Len(xstr)>0) Then
			wcnc("G53 G0 X="+xstr)  ' X Positionierung
		ElseIf (Len(ystr)>0) Then
			wcnc("G53 G0 Y="+ystr)  ' X Positionierung
		End If
	End If
	


    If UCase(characters)="$NOSTOP" Then
    	wcnccom("STOP OHNE STOP")
    Else
 	' --
    	' -- Modified  AK 13.05.2014
    	' --
		If InStr(msg,"%CMD_VACUUMOFF%")>0 Then
			msg=Replace$(msg,"%CMD_VACUUMOFF%", "")
			wcnc("M98")
		End If

		wcnc_msg(msg)
		wcnc("M0")
		wcnc_msgOff
	End If

	
	If JobPara.isg Then
		' -- nicht noetig fuer ISG		
	Else
		wcnc("D="+g_DCORRECTIONMARKER)   ' aktuelle D-Korrektur zurueckholen
	End If
	ActV.View = -1   ' erzwingt einen erneuten Ebenenwechsel	

'	If MT_Is_Vertical_StandardTool5Axis(actt) Then
		' --
		' --
		'  - TROARI darf nicht eingeschaltet werden, - fuehrt zu SoftwareEndlage
		' --
		' --
		' --
		' --
'		wcnc_IDD(JobPara.tcp_on)
'		' --  5-Axis milling
'		' --  Nach Traori muss G54 aktiviert werden
'		wcnc_IDD("STOPRE")
'		wcnc("G"+IntToS(53+Fix_Zero))
'	End If
	
	Marker.MachineStopActive=True
	
	
End Function



Function WCNC_LINE_With_Seperator(stri)
Dim substri As String

	While InStr(stri,"|") > 0
		substri = Mid(stri,1,InStr(stri,"|")-1)
		stri=Mid(stri,InStr(stri,"|")+1,Len(stri))
		wcnc(substri)
	Wend
	If Len(stri)>0 Then
		wcnc(stri)
	End If
	
End Function

' *****************************************************************************************
' ** Vorlegehub - Steuerung
' *****************************************************************************************
Function DINISO_WRITE_CPLIFT(WriteWNC As Boolean, Optional X As Double , Optional Y As Double, Optional Z As Double )

Dim H_Id As Variant   ' Aggregate Head id 
Dim H_Typ As Variant  ' Aggregate Typ
Dim LP As Integer  ' Vorlegestufe

	X = 0
	Y = 0 
	Z = 0  ' werden zurueckgegeben

	LP = DINISO_Get_Liftpos
	If LP <= 0 Then
		LP = MT_GET_PREFLIFT
	End If
	If (equal(LP,1) Or equal(LP,2)) Then
		' ** 
		' ** Vorlegestufe fuer ext. DINISO-Programm
		' ** 
    	' liftpos absetzen fuer DINISO - Funktionalitaet
    	X = actT.H.LiftOffsets.GetLiftOffset_ID(LP).OffsetX
    	Y = actT.H.LiftOffsets.GetLiftOffset_ID(LP).OffsetY
    	Z = actT.H.LiftOffsets.GetLiftOffset_ID(LP).OffsetZ
    	
    	If WriteWNC Then
			wcnccom("Vorlegestufe:"+inttos(LP)+" - verrechnet: x:"+ftos(X)+" y:"+ftos(Y)+" z:"+ftos(Z),True)
			If JobPara.isg Then
			
				ISG_CC(SPF_TCLift,inttos(ActT.Hid),inttos(LP))
			Else
				wcncaddcom(SPF_TCLift+"("+inttos(ActT.Hid)+","+inttos(LP)+")",IIf(LP=1," untere Stellung"," obere Stellung"))
			End If
			' -- Lift- Offsets bekanntgeben
			wcnc(g_LIFTOFFSETX+"="+ftos(X))
			wcnc(g_LIFTOFFSETY+"="+ftos(Y))
			wcnc(g_LIFTOFFSETZ+"="+ftos(Z))
		End If
	End If

End Function

Function isDINISO_Process
Dim resu As Boolean
	resu = False
	If (PPara.PreObjectTyp = otNCInfoProcessMPs) Or (PPara.PreObjectTyp = otNCInfoProcess) Then
		If NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Kind=77710 Then
			resu = True
		End If
	End If

	isDINISO_Process = resu
End Function

Function IsDINISO_No_Speed
Dim resu As Boolean
	resu = False
	If (PPara.PreObjectTyp = otNCInfoProcessMPs) Or (PPara.PreObjectTyp = otNCInfoProcess) Then
		' NCINFOProcess als Bohren oder Fraesen
		If NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Kind=77710 Then
			resu = NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Para10=0
		End If
	End If
	IsDINISO_No_Speed = resu
End Function

Function IsDINISO_No_TC
Dim resu As Boolean
	resu = False
	If (PPara.PreObjectTyp = otNCInfoProcessMPs) Or (PPara.PreObjectTyp = otNCInfoProcess) Then
		' NCINFOProcess als Bohren oder Fraesen
		If NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Kind=77710 Then
			resu = NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Para8=0
		End If
	End If
	IsDINISO_No_TC = resu
End Function

Function IsDINISO_No_VC
Dim resu As Boolean
	resu = False
	If (PPara.PreObjectTyp = otNCInfoProcessMPs) Or (PPara.PreObjectTyp = otNCInfoProcess) Then
		' NCINFOProcess als Bohren oder Fraesen
		If NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Kind=77710 Then
			resu = NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Para9=0
		End If
	End If
	IsDINISO_No_VC = resu
End Function



Function DINISO_Get_Liftpos
Dim resu As Integer
	resu = -1
	If (PPara.PreObjectTyp = otNCInfoProcessMPs) Or (PPara.PreObjectTyp = otNCInfoProcess) Then
		' NCINFOProcess als Bohren oder Fraesen
		If NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Kind=77710 Then
			resu = NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Para11
		End If
	End If
	DINISO_Get_Liftpos = resu
End Function
