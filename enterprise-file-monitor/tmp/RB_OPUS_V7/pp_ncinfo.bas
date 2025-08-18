' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \RB_OH_OPUS_V7\pp_ncinfo.bas
' -- 
' -----------------------------------------
' -- 
' -- Reichenbacher - ISG / BECKHOFF Postprocessors V7 (mw) --
' -- 
' -----------------------------------------
'#uses "pp_math.bas"
'#uses "pp_global.bas"
'#uses "pp_mt.bas"
'#uses "pp_mtf.bas"
'#uses "pp_bohrdh.bas"
'#uses "pp_7.bas"


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
  ElseIf Kind=4 Then
  	 ' Globale Schalter
  	 For i = 0 To UBound(BL_Global) 
  	 	' Blacklist pruefen
  	 	If equal(NCType,BL_Global(i)) Then
  	 		pp_err(1553,BL_Global(i))
  	 	End If
	 Next i 
  	 
'  	 If (NCType=57) Then
'  	 	Marker.No_G0_Up_DH = True
'  	 End If
  	 
  	 
  End If

End Function


Function Handle_NCInfoProcess(InfoTyp,x1,y1,z1,x2,y2,z2,w1,w2,w3,w4,w5,w6,w7,w8,w9,w10,w11,w12,w13,w14,w15,w16,w17,w18,w19,w20,w21,str1,str2)
Dim obj
Dim BL_NCI(1)
Dim i As Integer 	
Dim ax1,ay1,az1,ax2,ay2,az2 As Variant
Dim ax,ay,az As Variant
'Dim LOX As Double 
'Dim LOY As Double
'Dim LOZ As Double
Dim NCIExt As Object 
Dim NCIP_MPs As Object
Dim NCI As Object 
Dim CodeLine As String     
Dim Para1 As Double 

	'LOX = 0 
	'LOY = 0 
	'LOZ = 0

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
    	
		' Bewegung absetzen - same As simu    
		If PPara.ObjectTyp = otNCInfoProcessMPs Then
			' als Milling definiert - hier die uebergebene Position anfahren
			'DINISO_WRITE_CPLIFT(False,LOX,LOY,LOZ)  ' Liftoffsets holen
			'x1=x1-LOX
			'y1=y1-LOY
			'z1=z1-LOZ
			'x2=x2-LOX
			'y2=y2-LOY
			'z2=z2-LOZ
			
			If IsDINISO_No_VC Then
				' ohne Viewchange
				
				If MT_Is_Vertical_StandardTool5Axis(ActT) Then
					' Fuer 5-Axis muss TCP aktiv sein
					
' mw 15.07.2022 notwendig ?					
'					WCNC_IDD(JobPara.TCP_ON)
'					WCNC_IDD("STOPRE")
'					wcnc("G"+IntToS(53+Fix_Zero))
				End If

				If (Not IsDINISO_No_SP) Then
					' MW 10.03.2020				
					NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).View.GetAxAyAz(x1,y1,z1,ax1,ay1,az1)
					NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).View.GetAxAyAz(x2,y2,z2,ax2,ay2,az2)
					
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
				End If
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
		Set NCIP_MPs = NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1)
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
		Set NCIP_MPs = NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1)
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
							PPara.Din_ISO_8201 = True   ' kein erneutes absetzen notwendig
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
'		Last_TC_Call_NCStr = ""   ' sonst danach kein neuer Toolchange aufruf 
		
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

	
End Function


'Function SetPneumatic_Marker(Para1)
'	If Marker.pneumatic_channel(1)<0 Then
'		Marker.pneumatic_channel(1)=Para1
'	ElseIf Marker.pneumatic_channel(2)<0 Then
'		Marker.pneumatic_channel(2)=Para1
'	ElseIf Marker.pneumatic_channel(3)<0 Then
'		Marker.pneumatic_channel(3)=Para1
'	End If
'End Function


'Function Pneumatic_On
'Dim i As Integer        '-- MW 15.04.2008 11:40:52
'	If (MT_isToolUsingPneumatic(actt)) Then
'		For i = 1 To 3 
'			If Marker.pneumatic_channel(i)>0 Then
'				' -- 
'				' -- ISG CONTROLLER
'				' --  MW 15.04.2008 08:56:09
'				' --
'				If JobPara.isg Then
'					' -- 
'					' -- ISG CONTROLLER PFUEFEN MW
'					' --
'					
'					AddMistake("ISG Pneumatic_On noch nicht implementiert")
'
'				Else
'					wcncAddCom("SetChannel"+IntToS(Marker.pneumatic_channel(i))+"On","pneum. Channel #"+IntToS(Marker.pneumatic_channel(i))+" on")
'				End If
'				
'				Marker.pneumatic_channel(i)=-1
'			End If
'		Next
'	End If
'End Function

'Function Pneumatic_Off(Para1)
'	If (MT_isToolUsingPneumatic(actt)) Then
'		' -- 
'		' -- ISG CONTROLLER
'		' --  MW 15.04.2008 08:56:09
'		' --
'		If JobPara.isg Then
'			' -- 
'			' -- ISG CONTROLLER PFUEFEN MW
'			' --
'			
'			AddMistake("ISG Pneumatic_On noch nicht implementiert")
'			If equal(Para1,-1)  Then
'				
'				wcncAddCom("SetChannelAllOff","pneum. Channel all off")
'			ElseIf (Para1<4) And (Para1>0) Then
'				wcncAddCom("SetChannel"+IntToS(Para1)+"Off","pneum. Channel #"+IntToS(Para1)+" off")
'			End If
'			
'		Else	
'			If equal(Para1,-1)  Then
'				
'				wcncAddCom("SetChannelAllOff","pneum. Channel all off")
'			ElseIf (Para1<4) And (Para1>0) Then
'				wcncAddCom("SetChannel"+IntToS(Para1)+"Off","pneum. Channel #"+IntToS(Para1)+" off")
'			End If
'		End If
'	End If
'End Function



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



Function IsDINISO_No_SP
Dim resu As Boolean
	resu = False
	' setzt no Viewchange voraus
	If IsDINISO_No_VC() Then
		If (PPara.PreObjectTyp = otNCInfoProcessMPs) Or (PPara.PreObjectTyp = otNCInfoProcess) Then
			' NCINFOProcess als Bohren oder Fraesen
			If NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Kind=77710 Then
				resu = NCData.ProcessList.GetProcess_NCInfoIndex(PPara.PLNo-1).Para25=1
			End If
		End If
	End If
	IsDINISO_No_SP = resu
End Function
