' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \%postdir%\pp_messen.bas
' -- 
' -----------------------------------------
'#uses "pp_7.bas"
'#uses "pp_math.bas"
'#uses "pp_global.bas"
'#uses "pp_mt.bas"
'#uses "pp_mtf.bas"


Option Explicit

Global Const Max_Anz_Messpunkte=10

' --------------------------------------------------
' Initialisierung
' --------------------------------------------------



Function Init_Messen(wp)
Dim i As Integer 

	' maximal 10 Messpunkte
	ReDim WPI(wp).xMessPunkte(Max_Anz_Messpunkte)
'	' alle Messwert - Parameter nullen 
'	wcnccom("Messwerte auf 0")
'	For i = 1 To 10 
'	
'		wcnc(GetMessPParam(i,0)+"=0")
'	Next i
'	wcnc("MESSPOSZ=0")
	
End Function


' --------------------------------------------------
' gibt True zurück, wenn angegebene Messnummer noch
' nicht existiert
' --------------------------------------------------
Function neuer_Messpunkt(Para1,wp) As Boolean
Dim i As Integer
Dim result As Boolean

	result = True
	For i = 1 To UBound(WPI(wp).xMessPunkte) 
	    If WPI(wp).xMessPunkte(i).Mess_Nr=Para1 Then
			result=False   ' Messpunkt bereits vorhanden
	    End If
	Next
	
	neuer_Messpunkt = result	
	
End Function



' --------------------------------------------------
' gibt True zurück, wenn angegebene Messnummer noch
' nicht existiert
' --------------------------------------------------

Function Get_Messpunkt_AusArray(SuchMessNr,wp) As Integer
Dim i As Integer
Dim result As Integer

	result = -1
	For i = 1 To UBound(WPI(Marker.WP_ActIndex).xMessPunkte) 
	    If WPI(Marker.WP_ActIndex).xMessPunkte(i).Mess_Nr=SuchMessNr Then
			result=i
	    End If
	Next
	
	If result<=0 Then
		AddMistake(GetErrMsg(234100,"_Fehler bei Messpunkt - Suche",1)) 

	End If
	
	Get_Messpunkt_AusArray = result
	
End Function


' --------------------------------------------------
' array um 1 erhöhen und daten wegschreiben
' --------------------------------------------------
Function MesspunktDaten_Schreiben(mess_nr,Para2,Para3,Para4,Para5,Para6,Para7,Para8   ,Para9   ,para10, str1)
		'MesspunktDaten_Schreiben(mess_nr,xm   ,ym   ,zm   ,xs   ,ys   ,zs,  ,richtung,messtyp ,MessrichtungStr)   

Dim akt_anz,NP As Integer
Dim r As Long
Dim dw_richtung As Double 
Dim Richtung_Str As String

	If mess_nr > Max_Anz_Messpunkte Then
		'AddMistake("Messpunkt-Anzahl überschritten: Max:"+inttos(Max_Anz_Messpunkte))
	End If

	' R100+x für Werkstück 1
	' R200+x für Werkstück 2
	' R300+x für Werkstück 3
	r= Marker.WP_ActIndex * 100'+900 ' 1. R-Param - Wert dann aufsteigend - Werkstückabhängig!

	If mess_nr=1 Then
		akt_anz=1
	Else
		akt_anz = UBound(WPI(Marker.WP_ActIndex).xMessPunkte)
	End If
	
'	If neuer_Messpunkt(mess_nr,Marker.act_wp) Then
	
	    NP=akt_anz+1
	    NP = mess_nr
	    
	    ReDim Preserve WPI(Marker.WP_ActIndex).xMessPunkte(NP)   	

		WPI(Marker.WP_ActIndex).xMessPunkte(NP).Mess_Nr=mess_nr
		WPI(Marker.WP_ActIndex).xMessPunkte(NP).X_S=Para2
		WPI(Marker.WP_ActIndex).xMessPunkte(NP).Y_S=Para3
		WPI(Marker.WP_ActIndex).xMessPunkte(NP).Z_S=Para4
		WPI(Marker.WP_ActIndex).xMessPunkte(NP).Xm=Para5
		WPI(Marker.WP_ActIndex).xMessPunkte(NP).Ym=Para6
		WPI(Marker.WP_ActIndex).xMessPunkte(NP).Zm=Para7
		
		' da teil auf Workcenter beliebig gedreht werden kann, muss Richtung dynamisch über die Messpunkte bestimmt werden
		dw_richtung=GetWinkelGrad(WPI(Marker.WP_ActIndex).xMessPunkte(NP).X_S,WPI(Marker.WP_ActIndex).xMessPunkte(NP).Y_S,WPI(Marker.WP_ActIndex).xMessPunkte(NP).Xm,WPI(Marker.WP_ActIndex).xMessPunkte(NP).Ym)
		
		' Ermittlung Messrichtung bezogen auf Maschinenkoordinatensystem 
		If (dw_richtung=0) And equal(WPI(Marker.WP_ActIndex).xMessPunkte(NP).Xm,WPI(Marker.WP_ActIndex).xMessPunkte(NP).X_S) And equal(WPI(Marker.WP_ActIndex).xMessPunkte(NP).Ym,WPI(Marker.WP_ActIndex).xMessPunkte(NP).Y_S) Then
			Richtung_Str=" Z-"
			WPI(Marker.WP_ActIndex).xMessPunkte(NP).Richtung=0
			
		ElseIf (dw_richtung=90) Or (dw_richtung=-270) Then
			Richtung_Str=" Y+"
			WPI(Marker.WP_ActIndex).xMessPunkte(NP).Richtung=1
		ElseIf (dw_richtung=0) Or (dw_richtung=360) Then
			Richtung_Str=" X+"
			WPI(Marker.WP_ActIndex).xMessPunkte(NP).Richtung=2
		ElseIf (dw_richtung=-90) Or (dw_richtung=270) Then
			Richtung_Str=" Y-"
			WPI(Marker.WP_ActIndex).xMessPunkte(NP).Richtung=3
		ElseIf (dw_richtung=180) Or (dw_richtung=-180) Then
			Richtung_Str=" X-"
			WPI(Marker.WP_ActIndex).xMessPunkte(NP).Richtung=4
		End If
		WPI(Marker.WP_ActIndex).xMessPunkte(NP).Str2=Richtung_Str
		
			
			
		WPI(Marker.WP_ActIndex).xMessPunkte(NP).Messtyp=Para9
		WPI(Marker.WP_ActIndex).xMessPunkte(NP).str1=str1
		WPI(Marker.WP_ActIndex).xMessPunkte(NP).RPara=inttos(r+NP)
		
		
		WPI(Marker.WP_ActIndex).xMessPunkte(NP).gemessen=False
		
		WPI(Marker.WP_ActIndex).Activ_Messpoint=NP
		
'		If Not equal(Channel,1) Then
'			' --
'			' -- Für Channel=1 wird Parameter erst in Messen_Abhandeln gesetzt
'			' -- sonst sind die Verschiebeparameter beim Messen selbst bereits aktiv (P20020)
'			If equal(MessPunkte(NP).Mess_Nr,11) And _
'			   equal(MessPunkte(NP).Messtyp,3) And _
'			   equal(MessPunkte(NP).Para6,1) Then
'				' --
'				' -- Modified  MW 03.03.2009 13:55:14
'				' --
'				' -- Zargenyp RT-SD-PF58 Seitenteil - 58er Drehflügeltüre
'				' -- Zeichnung 168.615
'				' -- 
'				' -- dann wurde beim Messen Z Parameter P20020 beschrieben
'				' --
'				MessZ_Komplett_Move = True
'			End If
'		End If
		
		
		
'	Else
'		' ansonsten vorhandenen Messpunkt wieder aktiv setzen
'		
'		WPI(Marker.act_wp).Activ_Messpoint=Get_Messpunkt_AusArray(mess_nr,Marker.act_wp)
'	End If
	
	
End Function




' --------------------------------------------------
' Messen, sofern noch nicht gemessen, und Aktive_mess_nummer >0
' --------------------------------------------------

'--
'--
'--
'--
'--
'--   nicht aktiv
'--
'--
'--
'--
Function Messen_Abhandeln(ArrayNr As Integer)
'--
Dim Mess As TMessPunkt	

	If (ArrayNr > 0) Then
		Mess = WPI(Marker.WP_ActIndex).xMessPunkte(ArrayNr)
	
		' Neu MW 13.05.2004 - alle Aggregate können messen
		'If Not (MessPunkte(ArrayNr).gemessen) And ( (Channel=2) Or (Channel=4) ) Then
		If Not (Mess.gemessen) Then ' And (  (xMessPunkte(ArrayNr).Messtyp=0) Or (xMessPunkte(ArrayNr).Messtyp=3) ) Then
			Messen(Mess,0)
		Else
			wcnccom("Werkstück:"+Inttos(Marker.WP_ActIndex)+" Messwert "+inttos(Mess.Mess_Nr)+" nur verrechnen")
		End If
		

		'If equal(channel,1) Then
			
			' --
			' -- für Kanal 1 darf Merker erst nach dem Messen in Z- gesetzt werden
			' --
			
'			If equal(xMessPunkte(ArrayNr).Mess_Nr,11) And _
'			   equal(xMessPunkte(ArrayNr).Messtyp,3) Then
				' --
				' -- Modified  MW 03.03.2009 13:55:14
				' --
				' -- Zargenyp RT-SD-PF58 Seitenteil - 58er Drehflügeltüre
				' -- Zeichnung 168.615
				' -- 
				' -- dann wurde beim Messen Z Parameter P20020 beschrieben
				' --
'				Marker.MessZ_Komplett_Move = True
'			End If
		'End If

	End If

	
End Function


' --------------------------------------------------
' Messen, eigentlichen Messvorgang absetzen
' --------------------------------------------------
Function Messen(MessPunkt As TMessPunkt, Zon As Integer)
Dim xs,ys,zs,mess_x,mess_y,mess_z As Double
Dim Eb As Integer
Dim P_ParamX,P_ParamY,P_ParamZ As String
Dim Sic As Double		' sicherheitsabstand vertikal oder hor. je nach ebene
Dim DnumMess As Integer    ' MW 24.02.2010 Fixe Korrektur fürs Messen
Dim Richtung As Integer 
Dim RDummy As String
Dim Delta As Double 
Dim TmpStr As String

   Marker.Ueberfahren=0
   RDummy = inttos(Marker.WP_ActIndex*100)   ' achse in der nicht gemessen wurde


	Richtung = MessPunkt.Richtung

	' von hier aus Anfahren
	xs = MessPunkt.X_S
	ys = MessPunkt.Y_S 
	zs = MessPunkt.Z_S     'FinishedPart.Z+actt.t.GetSecurityZ(0)+getaddzsic
	If Richtung<>0 Then
		' Anfahrposition für horizontal tasten
		'zs = FinishedPart.Z+actt.t.GetSecurityZ(0)+getaddzsic
		zs = actt.t.GetSecurityZ(0)+getaddzsic
	End If
	
	' 
	mess_x = MessPunkt.Xm
	mess_y = MessPunkt.Ym 
	mess_z = MessPunkt.Zm 
	
	
	wcnccom(" ---  Werkstück "+inttos(Marker.WP_ActIndex)+"- - -   M E S S E N  - - -"+inttos(MessPunkt.Mess_Nr)+"- ---")

	wcnccom("")
	wcnccom("===========================")
	wcnccom(". MESSFAHRT ("+ MessPunkt.Str2+")" )  ' Messnummer
	
	
	' Anfahrt auf Messposition
	' -----------------------------------
	If Firsttime_Viewchange Then 
		' Without Z- Positioning
' ????????????		wcnc(G0+XEqualToS(xs)+YEqualToS(ys)+GetHeadAngles5AxisCAxis(0,0,0))
		' toCheck OS/MW
		pp_err(0)
	End If
	
	If Marker.FirstMeasure Then
		Zon=1
		Marker.FirstMeasure=False
	End If
	
	
	
	If Marker.DoorMeasureCount>4 Then
		'wcnc(G0+Move5(xs,ys,zs,0,0,ProcessPara.Feedrate,0))
		If Marker.DoorMeasureCount=5 Then
			TmpStr="DDX=(R"+inttos(100+MessPunkt.Mess_Nr-1)
			TmpStr=TmpStr+"+(R"+inttos(100+MessPunkt.Mess_Nr-2)
			TmpStr=TmpStr+"-R"+inttos(100+MessPunkt.Mess_Nr-1)+")/2)-"
			TmpStr=TmpStr+Ftos(WPI(Marker.WP_ActIndex).xMessPunkte(MessPunkt.Mess_Nr-1).Xm+((WPI(Marker.WP_ActIndex).xMessPunkte(MessPunkt.Mess_Nr-2).Xm-WPI(Marker.WP_ActIndex).xMessPunkte(MessPunkt.Mess_Nr-1).Xm)/2))
			WCNC(TmpStr)
			TmpStr="DDY=(R"+inttos(100+MessPunkt.Mess_Nr-3)
			TmpStr=TmpStr+"+(R"+inttos(100+MessPunkt.Mess_Nr-4)
			TmpStr=TmpStr+"-R"+inttos(100+MessPunkt.Mess_Nr-3)+")/2)-"
			TmpStr=TmpStr+Ftos(WPI(Marker.WP_ActIndex).xMessPunkte(MessPunkt.Mess_Nr-3).Ym+((WPI(Marker.WP_ActIndex).xMessPunkte(MessPunkt.Mess_Nr-4).Ym-WPI(Marker.WP_ActIndex).xMessPunkte(MessPunkt.Mess_Nr-3).Ym)/2))
			WCNC(TmpStr)
  			'WCNC("DDX=(R"+inttos(100+MessPunkt.Mess_Nr-1)+"+(R"+inttos(100+MessPunkt.Mess_Nr-2)+"-R"+inttos(100+MessPunkt.Mess_Nr-1)+")/2)-"+Ftos(((WPI(Marker.WP_ActIndex).xMessPunkte(MessPunkt.Mess_Nr-1).Xm-WPI(Marker.WP_ActIndex).xMessPunkte(MessPunkt.Mess_Nr-2).Xm)/2)+WPI(Marker.WP_ActIndex).xMessPunkte(MessPunkt.Mess_Nr-1).Xm))
  			'WCNC("DDY=(R"+inttos(100+MessPunkt.Mess_Nr-3)+"+(R"+inttos(100+MessPunkt.Mess_Nr-4)+"-R"+inttos(100+MessPunkt.Mess_Nr-3)+")/2)-"+Ftos(((WPI(Marker.WP_ActIndex).xMessPunkte(MessPunkt.Mess_Nr-3).Ym-WPI(Marker.WP_ActIndex).xMessPunkte(MessPunkt.Mess_Nr-4).Ym)/2)+WPI(Marker.WP_ActIndex).xMessPunkte(MessPunkt.Mess_Nr-3).Ym))
  			'WCNC("DDY=(R"+inttos(100+CLng(Para2)+1)+"+(R"+inttos(100+CLng(Para2))+"-R"+inttos(100+CLng(Para2)+1)+")/2)-"+Ftos(((WPI(Marker.WP_ActIndex).xMessPunkte(CLng(Para2)).Ym-WPI(Marker.WP_ActIndex).xMessPunkte(CLng(Para2)+1).Ym)/2)+WPI(Marker.WP_ActIndex).xMessPunkte(CLng(Para2)+1).Ym))
  		  	Marker.MessbezugX=0
  		  	Marker.MessbezugY=0
  		  	Marker.MeasureActiv=True
  		  	WCNC("STOPRE")
  		End If
  	ElseIf Marker.DrillMeasureXCount=2 Then
  		WCNCCom("2 Drilling X")
		wcnc(G0+Move5(xs,ys,zs,0,0,PPara.Feedrate,0))	
	ElseIf Marker.DrillMeasureYCount=2 Then
  		WCNCCom("2 Drilling Y")
		wcnc(G0+Move5(xs,ys,zs,0,0,PPara.Feedrate,0))	
	Else
		wcnc(G0+Move5(xs,ys,zs,0,0,PPara.Feedrate,0))
	End If
	
	If Richtung = 0 Then
		' Z-Messen
	Else
		' -----------------------------------
		' In Z runter
		' -----------------------------------
		'wcnc(G0+Move5(xs,ys,-mess_z,0,0,ProcessPara.Feedrate,0))
	End If
	
	If Richtung=1 Or Richtung=2 Then
		Delta=Marker.Ueberfahren	
	ElseIf Richtung=3 Or Richtung=4 Then
		Delta=-Marker.Ueberfahren
	End If
	
	
	wcnccom("Jetzt Tastvorgang - Ergebnis der Messung steht auf R"+inttos(MessPunkt.RPara))
	Select Case Richtung
	Case 0 
		' Z-
		'wcnc("C_Z_TAST("+ftos(mess_z)+","+inttos(MessPunkt.RPara)+")")
		wcnc("C_Z_TAST("+ftos(mess_x)+","+ftos(mess_y)+","+ftos(mess_z)+","+inttos(MessPunkt.RPara)+")")
		'AddMistake("z-Tasten auf dieser Maschine nicht erlaubt!")
	Case 1,3
		' Y+ / y-
		'AddMistake("X-Tasten auf dieser Maschine nicht erlaubt!")
		If Marker.MeasureActiv=True Then
			AddMistake("Auf dieser Maschine nicht erlaubt!")
			WCNC("TAST_X=("+ftos(mess_x)+"+DDX)")
			WCNC("TAST_Y=("+ftos(mess_y+Delta)+"+DDY)")
			wcnc(G0+Move5(xs,ys,zs,0,0,PPara.Feedrate,0))
			wcnc("C_Y_TAST(TAST_X,TAST_Y,"+ftos(-mess_z)+","+RDummy+","+inttos(MessPunkt.RPara)+","+Inttos(Zon)+")")	
		Else
			'wcnc("XY_YTAST("+ftos(mess_x)+","+ftos(mess_y+Delta)+","+ftos(-mess_z)+")")',"+RDummy+","+inttos(MessPunkt.RPara)+","+Inttos(ZON)+")")
			wcnc("C_Y_TAST("+ftos(mess_x+Delta)+","+ftos(mess_y)+","+ftos(-mess_z)+","+inttos(MessPunkt.RPara)+","+RDummy+","+Inttos(Zon)+")")
		End If	
	Case 2,4 
		' X+ / X-
		'AddMistake("X-Tasten auf dieser Maschine nicht erlaubt!")
		If Marker.MeasureActiv=True Then
			WCNC("TAST_X=("+ftos(mess_x+Delta)+"+DDX)")
			WCNC("TAST_Y=("+ftos(mess_y)+"+DDY)")
			wcnc(G0+Move5(xs,ys,zs,0,0,PPara.Feedrate,0))
			wcnc("C_X_TAST(TAST_X,TAST_Y,"+ftos(-mess_z)+","+inttos(MessPunkt.RPara)+","+RDummy+","+Inttos(Zon)+")")
		Else
			wcnc("C_Y_TAST("+ftos(mess_x+Delta)+","+ftos(mess_y)+","+ftos(-mess_z)+","+inttos(MessPunkt.RPara)+","+RDummy+","+Inttos(Zon)+")")
		End If
	Case Else
		AddMistake("32498723498723")
	End Select
	If Richtung = 0 Then
		' Z-Messen
	Else
		' XY-Messen
		' -----------------------------------
		' In Z hoch
		' -----------------------------------
		'wcnc(G0+Move5(xs,ys,zs,0,0,ProcessPara.Feedrate,0))
	End If
	
	If Len(Trim(Marker.MeasProtPath))>0 Then
		WCNC("STOPRE")
		Select Case Richtung
		
		Case 0 
		' Z-
			
		Case 1,3 
			' Y+ / y-
			WCNC("DDY=(R"+inttos(MessPunkt.RPara)+"-"+Ftos(mess_y)+")")
			wcnc("C_DD_CHECK(DDY)")
			WCNC("WRITE(ERROR,"+Chr(34)+Marker.MeasProtPath+Chr(34)+","+Chr(34)+"Y-Soll: "+Ftos(mess_y)+"   IST: R"+inttos(MessPunkt.RPara)+"="+Chr$(34)+" <<R"+inttos(MessPunkt.RPara)+"<<"+Chr$(34)+" DY= "+Chr$(34)+"<<DDY"+")")
			
		Case 2,4 
			' X+ / X-
			WCNC("DDX=(R"+inttos(MessPunkt.RPara)+"-"+Ftos(mess_x)+")")
			wcnc("C_DD_CHECK(DDX)")
			WCNC("WRITE(ERROR,"+Chr(34)+Marker.MeasProtPath+Chr(34)+","+Chr(34)+"X-Soll: "+Ftos(mess_x)+"   IST: R"+inttos(MessPunkt.RPara)+"="+Chr$(34)+" <<R"+inttos(MessPunkt.RPara)+"<<"+Chr$(34)+" DX= "+Chr$(34)+"<<DDX"+")")

		Case Else
			AddMistake("32498723498723")
		End Select
	End If
	
	wcnccom(" --- M E S S E N    E N D E ---")
	
'	MT_Write_Call_Correction	
	wcnc("T"+IntToS(ActT.h_add.ToolNo))
	wcnc("D"+IntToS(ActT.h_add.CorrNo))
	' ToCheck OS/MW
	 
	
	MessPunkt.gemessen=True
End Function



Function GetMessPParam(MNr,Typ) 
	If (MNr>11) And Not (Typ=3) Then
		AddMistake(GetErrMsg(32400,"_Zuviele Messpunkt - Max. 11 werden momentan unterstützt",1)) 
	End If
	' Neu MW 05.08.2004
	' Parameter P20020 ist Messwert in Z
'	If equal(MNr,11) Then
'		GetMessPParam = "P" + Inttos(20020)	
'		GetMessPParam = "MESSPOSZ"
'	Else
		GetMessPParam = "R" + Inttos(100+MNr)	
'		GetMessPParam = "MESSPOS[" + Inttos(MNr)+"]"
'	End If
End Function

Function Messen_Plaus_Pruef(MessParam)
	wcnc("P4000<-5."+ IntToS(NCLine+(30)) )
	wcnc("P4000>5."+ IntToS(NCLine+(20)) )
	'wcnc("M23."+ IntToS(NCLine+(20)) )
	wcnc("M23."+ IntToS(NCLine+(30)) )
	' Neu MW 06.08.2004 anstatt :-10 positiv setzen
	wcnc(MessParam+":10 P8503:3204 M0" )  ' Wesswert auf -10 und NC-STOP das heißt das Material ist 10mm näher zum Taster 
										' d.h. Verrechnete Bearbeitung findet 10mm entfernt statt -> Tür wird nicht kaputt gemacht!
	wcnc("M23."+ IntToS(NCLine+(20)) )
	
End Function



Function messen_get_mess_para(nrxy,nrz,xmessp,ymessp,zmessp)
Dim mess_xy,mess_z As TMessPunkt


	If nrxy>0 Then
		mess_xy=WPI(Marker.WP_ActIndex).xMessPunkte(nrxy)
		
		Select Case mess_xy.Richtung
			Case 0 
				' Z-
				'wcnc("Z_TAST("+ftos(x)+","+ftos(y)+","+inttos(MessPunkt.RPara))
				AddMistake("Falsche Messrichtung - Z-Messpunkt für XY definiert!")
				'zmessp=mess_xy.rpara
			Case 1,3 
				' Y+ / y-
				ymessp=mess_xy.RPara
				'wcnc("XY_TAST("+ftos(x)+","+ftos(y)+","+RDummy+","+inttos(MessPunkt.RPara)+")")
			Case 2,4 
				' X+ / X-
				'wcnc("XY_TAST("+ftos(x)+","+ftos(y)+","+inttos(MessPunkt.RPara)+","+RDummy+")")
				xmessp=mess_xy.RPara
			Case Else
				AddMistake("32498723498723")
		End Select
	End If
	
	If nrz > 0 Then
		mess_z=WPI(Marker.WP_ActIndex).xMessPunkte(nrz)
		Select Case mess_z.Richtung
			Case 0 
				' Z-
				'wcnc("Z_TAST("+ftos(x)+","+ftos(y)+","+inttos(MessPunkt.RPara))
				
				zmessp=mess_z.RPara
			Case Else
				AddMistake("Messwert Z - verrechnen - falscher Messpunkt Nr."+inttos(nrz))
			
		End Select
	End If

	
End Function

Function wcnc_init_MessParameter
Dim i As Integer
Dim stri As String
	stri =""
	For i = 0 To Max_Anz_Messpunkte
		stri = stri + "R"+inttos(700+i)+"=0 "
	Next
	'wcnc(stri)
End Function
