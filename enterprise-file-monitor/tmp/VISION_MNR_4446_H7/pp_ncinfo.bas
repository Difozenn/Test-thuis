' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \%postdir%\pp_ncinfo.bas
' -- 
' -----------------------------------------
'#uses "pp_global.bas"
'#uses "pp_messen.bas"
'#uses "pp_mt.bas"
'#uses "pp_mtf.bas"
'#uses "pp_bohrdh.bas"
'#uses "PP_Clamps.bas"
'#uses "pp_math.bas"

Option Explicit

	
	
Function Handle_NCInfo(Kind,NCType,Para1,Para2,Para3,Para4,Para5,Para6,Para7,Para8,Para9,characters)

Dim n As Integer
Dim C As Integer
Dim s As Variant
Dim I As Integer


'Dim S As Variant
 ' S="" 
  If Kind=0 Then
  
  	If NCType=7148 Or NCType=222 Then
  		Marker.Messbezug=True
  	  	Marker.MessbezugX=Para1
		Marker.FaktorX=Para2
  		Marker.MessbezugY=Para3
		Marker.FaktorY=Para4
		Marker.MessbezugZ=Para5
		Marker.FaktorZ=Para6
		If Not MessBezChanged Then
			If Marker.MessbezugX<>0 Or Marker.Messbezug<>0 Or Marker.MessbezugZ<>0 Then
				Marker.Messbezug=True
			Else
				Marker.Messbezug=False
			End If
		End If
		
		'AddMistake("No Messurig in Z")
	End If
  
  	If NCType=7404 Then
  		Call PrintEtikett(Para1,Para2,Para7)
  	End If
  
  
    If NCType=7411 Or NCType=8411 Then
		A_Axis_COMMANDS(Para1,Para2,Para3)
	End If
	
  
    If NCType=200 Then
       '// Bohren mit Mehrspindler über Para1 kommt der Drehwinkel
       wcnc(characters)

    End If
  
  
    If NCType=205 Then
       '// Bohren mit Mehrspindler über Para1 kommt der Drehwinkel
       C_AchsPos_Mehrspindler=Para1
    End If
    

   	If (NCType=7211) Then
		'Blase EIN puffern...
		SpindleBlowNozzle.Blow=True
		SpindleBlowNozzle.Nozzle=1
	End If

   	If (NCType=8211) Then
		'Blasen AUS...
		If SpindleBlowNozzle.Blow=True Then
			Call Blasen_AUS
		End If
	End If
 
 	If (NCType=7212) Then
		'Blase EIN puffern...
		SawBlowNozzle.Blow=True
		SawBlowNozzle.Nozzle=1
	End If

   	If (NCType=8212) Then
		'Blasen AUS...
		If SawBlowNozzle.Blow=True Then
			Call BlasenSaw_AUS
		End If
	End If
 
 
   	If (NCType=8450) Then
		wcnccom("Gerundetes Fahrverhalten... ab jetzt.")
		wcnc("G450")
	End If

  	If (NCType=7451) Then
		wcnccom("Scharfes Fahrverhalten... ab jetzt.")
		wcnc("G451")
	End If

 	If NCType=7701 Then
 		If Haube.NewHaubePosBeforeTC=1 Then
 			Haube.NewHaubePosBeforeTC=2
 		End If
 		
 		If Para4=1 Then
			Haube.P3AchsUseIt=True			'Haube vorgelegen ja/nein
		Else
			Haube.P3AchsUseIt=False
		End If
		If Para1=1 Then
			Haube.P5AchsUseIt=True			'Haube vorgelegen ja/nein
		Else
			Haube.P5AchsUseIt=False		
		End If
		
		If characters="HaubenPos LeitBlechPos" Then
			If Para7=1 Then
				Haube.PLeitBlechUseIT=True
			Else
				Haube.PLeitBlechUseIT=False
			End If
			Haube.PDHUseIt=False
		Else
			If Para7=1 Then
				Haube.PDHUseIt=True				'Haube vorgelegen ja/nein
			Else
				Haube.PDHUseIt=False		
			End If
			Haube.PLeitBlechUseIT=False
		End If
		
		If characters="HaubenPos LeitBlechPos" Then
			Haube.PLeitblechPos=CDbl(Para8)
			Haube.PLeitblechDist=CDbl(Para9)
			Haube.PDHPos=0
		Else
			Haube.PDHPos=CDbl(Para8)		'Neue Pos
		End If
		
		Haube.P3AchsPos=CDbl(Para5)		'Neue Pos
		Haube.P5AchsPos=CDbl(Para2)		'Neue Pos
			
		If Para3=1 Then
			Haube.P5AchsAuto=True		'Automatisch Vorlegen wenn Ebene0
		Else
			Haube.P5AchsAuto=False		'Automatisch Vorlegen wenn Ebene0
		End If
		
		If Para6=1 Then
			Haube.P3AchsAuto=True		'Automatisch Vorlegen wenn Ebene0
		Else
			Haube.P3AchsAuto=False
		End If
		If characters="HaubenPos LeitBlechPos" Then
			
			'PLeitblechAktiv As Boolean 
			'PLeitblechPos As Double 
			'PleitblechDist As Double 
			Haube.PDHAuto=False
		Else
			If Para9=1 Then
				Haube.PDHAuto=True			'Automatisch Vorlegen wenn Ebene0
			Else
				Haube.PDHAuto=False
			End If
		End If
		
	End If
	
    If NCType=10 Then
      
      wcncCom("*************NCInfo Before Begin*******************")
      'C=ReadSectionCountPP_ini("NC_Before"+IntToS(Round(Para1)))
      For n=0 To C-1 Step 1
        'Call ReadSectionNoPP_ini("NC_Before"+IntToS(Round(Para1)),n,s)
        If s<>Chr(0) Then
          	wcnc(s) 
        End If
      Next n
      wcncCom("*************NCInfo Before End    *******************")
    End If
    
    If NCType=11 Then
        wcncCom("*************NCInfo after Begin*******************")
        'C=ReadSectionCountPP_ini("NC_After"+IntToS(Round(Para1)))
        For n=0 To C-1 Step 1
          'Call ReadSectionNoPP_ini("NC_After"+IntToS(Round(Para1)),n,s)
          s=Trim(s)
          If s<>Chr(0) Then
            	wcnc(s) 
          End If
        Next n
        wcncCom("*************NCInfo after End    *******************")
    End If
    If NCType=7100 Then
    	' Pneumatik Channel an
    	' Nur merken, da Befehl sonst viel zu früh abgesetzt
    	SetPneumatic_Marker(Para1)
    End If
    
    If NCType=7710 Then
    	' Neu MW 19.10.2005
    	' DINISO - Programm folgt
    	Set_DINISO_Marker(Para1,Para2)
    End If
    If NCType=7711 Then
    	' Neu MW 9.11.2005
    	' DINISO - LINE
    	' Neu MW 11.11 Line auch mit | - Zeichen als Zeilenumbruch
    	WCNC_LINE_With_Seperator(characters)
    	'WCNC(characters)
    End If

     
    If NCType=8100 Then
    	' Pneumatik Channel aus
    	Pneumatic_Off(Para1)
    End If
    If NCType=8200 Then
    	' Maschinen stop mit Parken und M0
    	pp_err(1535,NCType)
    	''Machine_Stop(Para1,Para2,Para3,characters)
    End If
  ElseIf Kind=1 Then
	
	If (NCType=8212) Then
		'Blasen AUS...
		If SawBlowNozzle.Blow=True Then
			Call BlasenSaw_AUS
		End If
	End If
  
	If (NCType=7212) Then
		'Blase EIN puffern...
		SawBlowNozzle.Blow=True
		SawBlowNozzle.Nozzle=1
	End If
  
	If (NCType=7211) Then
		'Blase EIN puffern...
		SpindleBlowNozzle.Blow=True
		SpindleBlowNozzle.Nozzle=1
	End If
  
  
    If NCType=7411 Or NCType=8411 Then
    	A_Axis_COMMANDS(Para1,Para2,Para3)
    End If
  
	
	If (NCType=200) Then
		If Para1=1 Then
			Marker.C_Poly=True
		End If
		If Para1=-1 Then
			Marker.C_Poly=False
		End If
		
		wcnc(characters)
	End If
	

   	If (NCType=8211) Then
		'Blasen AUS...
		Blasen_AUS
	End If

	If NCType=7100 Then
    	SetPneumatic_Marker(Para1)
		Pneumatic_On
	End If
	
	
	If NCType=7148 Then
		Marker.MessbezugZ=-999
		'AddMistake("No Messurig in Z")
	End If
	
  ElseIf Kind=4 Then
  	 ' Globale Schalter
     If (NCType=NCINFOPARKINFO) Then
	  	 JobPara.park=Para1
	  	 JobPara.parkx=Para2
	  	 JobPara.parky=Para3
     End If
     
    If NCType=150 Then
    	If Para7=0 Or Para7=1 Or Para7=2 Then
    		Lage.V_MESS=Para7
    	Else
    		AddMistake("Measure type is not allowed on this machine!")
    		Lage.V_MESS=0
    	End If
		Lage.V_WKZ_NR=Para9
		If Para8=20 Then
			Lage.V_ANSCHLAGART=2
			If Para1>Para2 Then
				Lage.V_MESSPOS_X1=Para2
				Lage.V_MESSPOS_X2=Para1
			Else
				Lage.V_MESSPOS_X1=Para1
				Lage.V_MESSPOS_X2=Para2	
			End If
		ElseIf Para8=10 Then
			Lage.V_ANSCHLAGART=1
			If Para1>Para2 Then
				Lage.V_MESSPOS_X1=Para2
				Lage.V_MESSPOS_X2=Para1
			Else
				Lage.V_MESSPOS_X1=Para1
				Lage.V_MESSPOS_X2=Para2		
			End If
			
		End If
		
		Lage.V_MESSPOS_Y1=Para3

		Lage.V_MESSPOS_Z1=Para4
		If Para7=2 Then
			Lage.V_MESSPOS_ZX=Para5
			Lage.V_MESSPOS_ZY=Para6
		Else
			Lage.V_MESSPOS_ZX=0
			Lage.V_MESSPOS_ZY=0		
		End If
		
    End If
     
    If NCType=151 Then
     	'Nestingtisch Feldvorwahl
     	For I=0 To 3
     		FieldMask.M(I)=False
     	Next	
     	FieldMask.BitMask=0
     	If Para1=1 Then
     		FieldMask.M(0)=True
     	End If
     	If Para2=1 Then
     		FieldMask.M(1)=True
     	End If
     	If Para3=1 Then
     		FieldMask.M(2)=True
     	End If
     	If Para4=1 Then
     		FieldMask.M(3)=True
     	End If
     	If Para5>=0 Then
     		FieldMask.BitMask=CLng(Para5)
     		For I=0 To 7
     			If (I Mod 4)=0 Then
     				FieldMask.Asstr=FieldMask.Asstr+" "
     			End If
     			If Para5 And 2^I Then
     				FieldMask.Asstr=FieldMask.Asstr+"1"
     			Else
     				FieldMask.Asstr=FieldMask.Asstr+"0"
     			End If
     		Next
     	End If
     	If Para6>=0 Then
     		FieldMask.BitMaskR=CLng(Para6)
     		For I=0 To 7
     			If (I Mod 4)=0 Then
     				FieldMask.AsstrR=FieldMask.Asstr+" "
     			End If
     			If Para6 And 2^I Then
     				FieldMask.AsstrR=FieldMask.Asstr+"1"
     			Else
     				FieldMask.AsstrR=FieldMask.Asstr+"0"
     			End If
     		Next
     	End If
     	
     End If
  	 	
  End If

End Function


Function Handle_NCInfoProcess(InfoTyp,x1,y1,z1,x2,y2,z2,w1,w2,w3,w4,w5,w6,w7,w8,w9,w10,w11,w12,w13,w14,w15,w16,w17,w18,w19,w20,w21,str1,str2)
Dim ProgPara As String
Dim Progname As String
Dim isok As Boolean 
Dim PrintHeadDown, PrintHeadPrintLabel, PrintHeadStickLabel,PrintHeadWaitPrint,PrintHeadWaitStick, PrintHeadLabelStatus As String
'Gewnide Bohren/Schneiden
Dim dr As Integer
Dim steigung As Double
Dim art As Integer		'0=Bohren  1=fraesen
Dim Richt As Integer	'Gewinderichtung 2 oder 3
Dim PPVZ As Double
	
	If InfoTyp=444000 Then 
		Call SetStrings(str1)
		'Wcnc("H92") Printheaddown
		PrintHeadDown=MT_get_Add_ID(actT,10154,isok)
		If isok Then
			wcncaddcom(PrintHeadDown,"Drucker voerlegen")
			Marker.PrinterIsUp=False
		Else
			AddMistake("Unbekannte Add_ID: 10154")
		End If
		'Wcnc("M91")
		'PrintHeadPrintLabel=MT_get_Add_ID(actT,10156,isok)
		'If isok Then
		'	wcncaddcom(PrintHeadPrintLabel,"Label Drucken")
		'Else
		'	AddMistake("Unbekannte Add_ID: 10156")
		'End If
		
		'PrintHeadWaitPrint=MT_get_Add_ID(actT,10159,isok)
		'If isok Then
		'	wcncaddcom("G04 F"+PrintHeadWaitPrint,"Drucken abwarten")
		'Else
		'	AddMistake("Unbekannte Add_ID: 10159")
		'End If
		
		'Wcnc("G0 "+" X"+Ftos(x1)+" Y"+Ftos(y1))
		'wcnc(G1+Move(ViewCPSawUnit_SPX,ViewCPSawUnit_SPY,ViewCPSawUnit_SPZ,I_Feedrate,MovePara.TRC))
		wcnc(G0+MoveOhneZ(x1,y1,z1,1111,0))
		Wcnc("STOPRE")
		WCNC("REPEAT")
		WCNC("MSG("+Chr$(&h22)+"Drucke Etikett"+Chr$(&h22)+")")
		WCNC("G04 F0.1")
		WCNC("UNTIL R999==0")
		'WCNC("M92")
		PrintHeadStickLabel=MT_get_Add_ID(actT,10157,isok)
		If isok Then
			wcncaddcom(PrintHeadStickLabel,"Label aufkleben")
		Else
			AddMistake("Unbekannte Add_ID: 10157")
		End If
		'Wcnc("G04 F0.5") Wait for Stick
		PrintHeadWaitStick=MT_get_Add_ID(actT,10160,isok)
		If isok Then
			wcncaddcom("G04 F"+PrintHeadWaitStick,"Kleben abwarten")
		Else
			AddMistake("Unbekannte Add_ID: 10160")
		End If
		'Wcnc("H90") Printhead up done in Rechange
		PrintHeadLabelStatus=MT_get_Add_ID(actT,10158,isok)
		If isok Then
			wcncAddCom(PrintHeadLabelStatus+"=0","Label leer")
		Else
			AddMistake("Unbekannte Add_ID: 10158")
		End If
		wcnc("STOPRE")
		'Wcnc("G0"+ztos(ActT.t.GetSecurityZ(0)))
	End If
	
	If InfoTyp=102001 Then
		steigung = StrToFloat(actt.T_CEdge.Additions.GetAddition_ID(444).Value)
		art = StrToFloat(actt.T_CEdge.Additions.GetAddition_ID(333).Value)
		Richt = StrToFloat(actt.T_CEdge.Additions.GetAddition_ID(555).Value)
		dr = IntToS(MT_Get_SpindleDirection(ActT,PPara.Speed))
		If ActV.TipA < 45 Then
	  		PPVZ = ActT.T.GetSecurityZ(0)  
  		Else
	  	'Sonst wird y Sicherheitsabstand berechnet
	  		PPVZ = ActT.T.SecurityHorz
  		End If
  		wcnc(G0+Move(x1,y1,PPVZ,MovePara.Feedrate,MovePara.TRC))
	
		If SpindleBlowNozzle.Blow Then
			Call SetBlasen()
		End If
	
		If SawBlowNozzle.Blow Then
			Call SetBlasenSaw()
		End If
		WcncCom("Gewinde Bohren")
		wcnc("CYCLE84(" +FToS(PPVZ) + ",0," +FToS(PPVZ) + "," +FToS(w1) + ",,1," + IntToS(dr) + ",," +FToS(steigung) +",0," +FToS(PPara.Speed) +"," +FToS(PPara.Speed) + ",3,1,0,0,,)")
	End If
	
	If InfoTyp=102002 Then
		WcncCom("Gewinde Schneiden")
		'wcnc("CYCLE90(" +FToS(PPVZ) + ",0," +FToS(5) + "," +FToS(Depth) + ",,"+FToS(actt.T_CEdge.Radius*2)+","+FToS(actt.T_CEdge.Radius*2 - steigung*2)+"," +FToS(steigung) +"," +FToS(ProcessPara.Feedrate) + "," +IntToS(Richt) + ",0," + FToS(PPVX)+","+ FToS(PPVY) + ")")
	
	
	End If
	
	If InfoTyp=101001 Then
   		
   
		'MesspunktDaten_Schreiben(mess_nr,xm,ym,zm,xx,ys,zs,richtung,modus,nr,MessrichtungStr)   
		Dim Ax1,Ay1,Az1 As Variant
		Dim Ax2,Ay2,Az2 As Variant
		Dim Zon As Integer 
		
		If Marker.GetDoorMeasure=True Then
			Marker.DoorMeasureCount=Marker.DoorMeasureCount+1
		End If
		
		If Marker.GetDrillMeasureX=True Then
			Marker.DrillMeasureXCount=Marker.DrillMeasureXCount+1
		End If
		
		If Marker.GetDrillMeasureY=True Then
			Marker.DrillMeasureYCount=Marker.DrillMeasureYCount+1
		End If
		
		If Marker.DoorMeasureCount>4 Then
				
		End If
		
		'If Marker.LageMessenY=True Then
		'
		'End If
		
		
		' Anfahrpunkt		
		VxyzToAxyz(ActV.IPX, ActV.IPY, ActV.IPZ, ActV.RotA, ActV.TipA, x1,y1,z1, Ax1, Ay1, Az1)
		
		' Messpunkt
		VxyzToAxyz(ActV.IPX, ActV.IPY, ActV.IPZ, ActV.RotA, ActV.TipA, x2,y2,z2, Ax2, Ay2, Az2)
		
		' Achtung  Z1 anstelle Az1
		Call MesspunktDaten_Schreiben(w3,Ax1,Ay1,Az1,Ax2,Ay2,Az2,w1,w2,w3,str2)
		'If w19=1 Then
		'	Zon=1
		'Else
			Zon=0
		'End If
		
		messen(WPI(Marker.WP_ActIndex).xMessPunkte(w3), Zon)
	End If
	
	If InfoTyp=101002 Then
		'C_MESSEN_NULL( V_MESS,  V_WKZ_NR,  V_ANSCHLAGART,  V_MESSPOS_Y1,V_MESSPOS_X1, V_MESSPOS_X2, V_BAUTEILLAENGE, V_BAUTEILBREITE,  V_BAUTEILDICKE) 
		Call RESET_MESSBEZUG
		WCNC("C_MESSEN_NULL( V_MESS_LOK,  V_WKZ_NR_LOK,  V_ANSCHLAGART_LOK,  V_MESSPOS_X1_LOK, V_MESSPOS_X2_LOK, V_MESSPOS_Y1_LOK, V_MESSPOS_Z1_LOK, V_MESSPOS_ZX_LOK, V_MESSPOS_ZY_LOK, H_LAENGE, H_BREITE, H_DICKE)")
		Marker.LastMessbezugX=-999
		Marker.LastMessbezugY=-999
		Marker.LastMessbezugZ=-999
		WCNC("STOPRE")
		If Fix_Zero<=5 Then
			wcnc("G"+IntToS(53+Fix_Zero))
		ElseIf Fix_Zero>5 And Fix_Zero<100 Then
			wcnc("G"+IntToS(499+Fix_Zero))
		Else 
			AddMistake("Check ZereoPoint Number!")
		End If
	End If
	
    If InfoTyp=7710 Then
    	' Neu MW 18.10.2005
    	'ToolChange DINISO - MODE
    	'ID = Para1
    	'HeadID = Para2
    	Progname = str1
    	ProgPara = str2
    	If Marker.diniso_mode<=2 Then
	    	If Len(ProgPara)>0 Then
	    	  	wcnc(ProgPara)
	    	End If
	    	If Len(Progname)>0 Then
		    	wcnc("EXTCALL """+Progname+"""")
		    End If
		End If
    	
    	' Fertig - jetzt Rücksetzen
    	Reset_DINISO_Marker
		Marker.DINISO_Mode = -1
		Marker.DINISO_LIFTPOS = -1
		Last_TC_Call_NCStr = ""   ' sonst danach kein neuer Toolchange aufruf 
    End If
    If InfoTyp=7711 Then
    	wcnc(str1)
    End If

	Marker.Viewchangechecked=False

	
End Function


Function SetPneumatic_Marker(Para1)
	If Marker.pneumatic_channel(1)<0 Then
		Marker.pneumatic_channel(1)=Para1
	ElseIf Marker.pneumatic_channel(2)<0 Then
		Marker.pneumatic_channel(2)=Para1
	ElseIf Marker.pneumatic_channel(3)<0 Then
		Marker.pneumatic_channel(3)=Para1
	End If
End Function


Function Pneumatic_On
Dim i As Integer

	If (MT_isToolUsingPneumatic(actt)) Then
		For i = 1 To 3 
			If Marker.pneumatic_channel(i)>0 Then
				wcncAddCom("SetChannel"+IntToS(Marker.pneumatic_channel(i))+"On","pneum. Channel #"+IntToS(Marker.pneumatic_channel(i))+" on")
				Marker.pneumatic_channel(i)=-1
			End If
		Next
	End If
End Function

Function Pneumatic_Off(Para1)
	If (MT_isToolUsingPneumatic(actt)) Then
		If equal(Para1,-1)  Then
			wcncAddCom("SetChannelAllOff","pneum. Channel all off")
		ElseIf (Para1<4) And (Para1>0) Then
			wcncAddCom("SetChannel"+IntToS(Para1)+"Off","pneum. Channel #"+IntToS(Para1)+" off")
		End If
	End If
End Function


' ToCheck OS/MW 
' zusaetzliche Parameter NextBoxWorking,HeadID
Function Machine_Stop(Para1,Para2,Para3,characters,NextBoxWorking,HeadID)
Dim park_merker As Integer
Dim msg,xstr,ystr As String
Dim park As Integer
Dim parkx,parky As Double
Dim ROTDIR As Long
	
	If Firsttime_Viewchange Then
		' Stop vor 1. Bearbeitung nicht moeglich!
		Exit Function
		GetErrMsg(74224107,"Stop vor 1. Bearbeitung nicht moeglich!",1)
	End If
	
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
	wcnccom(" Machine STOP NCINFO 8200 Park:"+inttos(park))
	wcnccom("*")
	
	' MW 11.08.2005 
	' geht nicht, da WerkzeugVorwechsel auch schon einige Bearbeitungen
	' eher kommen kann!
	If Not TCB_T.t Is Nothing Then
		' Toolchangebefore wurde aufgerufen
		If tcb_t.t.ID <> actt.t.ID Then
			' nächstes Werkzeug ein anderes 
			If Not MT_GB_Output_Changed(ActT,TCB_T) Then
				' nächstes Werkzeug nicht auf gleichm Winkelgetriebe
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
	
	
	wcnc(DCORRECTIONMARKER+"=$P_TOOL")   ' aktuelle D-Korrektur merken
	
	'wcnc("TCARR=0")   ' Werkzeugträgerkorrektur abwählen
	
	If (actt.H_Add.Traori) Then
        wcnc(actt.H_Add.TraoriOff)  '  "TRAORI AUS"

	End If

	wSafetyAbs(False)    ' Z-Hochfahren

	If (Len(xstr)>0) And (Len(ystr)>0) Then
		wcnc("G153 G0 X="+xstr+" Y="+ystr)  ' X-Y Positionierung
	ElseIf (Len(xstr)>0) Then
		wcnc("G153 G0 X="+xstr)  ' X Positionierung
	ElseIf (Len(ystr)>0) Then
		wcnc("G153 G0 Y="+ystr)  ' X Positionierung
	End If
	
   If MT_Is_Vertical_StandardTool5Axis(actt) Then
		' 5-Achs 
		'wcnc("G153 G0 "+ActT.PH_Add.TipAxisName+"=0 "+ ActT.PH_Add.RotAxisName+"=0")
   End If
	
	
	wcnc_msg(msg)
	wcnc("M0")
	If (actt.H_Add.Traori) Then
        wcnc(actt.H_Add.TraoriOn)  '  "TRAORI"
        SET_Zero(False,"",0,0,0,0,0,0,False,False)

	End If
	'Marker.Stopp=True
	VACUUM_ON(0)
	'WCNC("C_VORHANG(1)")
	WCNC("STOPRE")
	If Actt.t.RotDirection=1 Then
		ROTDIR=4
	Else
		ROTDIR=3
	End If
	'WCNC("C_VORHANG(1)")
	'WCNC("STOPRE")
	'Marker.Vorhang=False
	'Alt OS 13.03.2014
	'If GSiemens840DType=1 Then
	'	WcncAddCom("C_TSL("+IntToS(Actt.t.GetPlaceID_OnTC)+","+IntToS(Abs(Actt.t.MaxRotSpeed))+")","Set Speed limits for next Tool!")
	'End If
	
	
	'If Actt.T_H.Addtions.ToolChangeType=0 Then
	'	WCNC(GToolChangeCycleName+"("+Inttos(Actt.t.GetPlaceID_OnTC)+","+Inttos(ROTDIR)+","+FTOS(Actt.t.RotSpeed)+")")
	'ElseIf
	'Neu OS 13.03.2014
	If Not(MT_IsDH(Actt)) Then
		MT_WZW(Actt.t.RotSpeed)
	End If
	
	
	
	'WCNC("M"+Inttos(ROTDIR)+" S="+FTOS(Actt.t.RotSpeed))
	'WCNC("")
	wcnc_msgOff
	
	wcnc("D="+DCORRECTIONMARKER)   ' aktuelle D-Korrektur zurückholen
	ActV.View = -1   ' erzwingt einen erneuten Ebenenwechsel	
	Firsttime_Viewchange=True	
End Function

Function Set_DINISO_Marker(Para1,Para2)

	Marker.DINISO_PROCESS = True
	Marker.DINISO_Mode = Para1
	Marker.DINISO_LIFTPOS = Para2
End Function
	

Function Reset_DINISO_Marker

	Marker.DINISO_PROCESS = False
	
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

Function A_Axis_COMMANDS(Para1,Para2,Para3)

	If (Para3 = 2) And (Marker.aaxiss=False) Then
		' Stellen der A-Achse
		wcncCom("*************  Stellen der A-Achse  *******************")
		wcnc("G1 A"+FTOS(Para1) + " F"+FTOS(Para2)) 
		
	ElseIf (Para3 = -1) Or (Para3 = 1) Then
		'Permanente Rotation der A-Achse mit Richtung Para3 und Geschw. Para2	
		wcncCom("*************  Fortlaufende A-Achsenrotation  *******************")
		wcnc("DO MOV[A]=" + Format(Para3,"0") + " FA[A]="+FTOS(Para2)) 
		Marker.aaxiss=True

	ElseIf (Para3 = 0) Then
			'Stoppen der permanenten Rotation
		wcncCom("*************  Fortlaufende A-Achsenrotation Stop  *******************")

		wcnc(DCORRECTIONMARKER+"=$P_TOOL")   ' aktuelle D-Korrektur merken
		If (actt.H_Add.Traori) Then
    		wcnc(actt.H_Add.TraoriOff)  '  "TRAORI AUS"
		End If

		wSafetyAbs(False)    ' Z-Hochfahren
		
		
	   If MT_Is_Vertical_StandardTool5Axis(actt) Then
			' 5-Achs 
			'wcnc("G153 G0 "+ActT.PH_Add.TipAxisName+"=0")
			'AddMistake("Check Function")
	   End If
				
		wcnc("D="+DCORRECTIONMARKER)   ' aktuelle D-Korrektur zurückholen
		ActV.View = -1   ' erzwingt einen erneuten Ebenenwechsel	
		WCNC("DO MOV[A]=0")
		WCNC("A_ZERO")

		If (actt.H_Add.Traori) Then
	        wcnc(actt.H_Add.TraoriOn)  '  "TRAORI"
	        SET_Zero(False,"",0,0,0,0,0,0,False,False)
		End If

		Marker.aaxiss=False
	'Andere Parameter = Fehler	
	Else
		AddMistake("Order for A-Axiss is not Allowed!")
	End If
	
End Function

