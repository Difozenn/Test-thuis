' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \%postdir%\pp_bohrdh.bas
' -- 
' -----------------------------------------
'#uses "pp_global.bas"
'#uses "pp_mt.bas"
'#uses "pp_mtf.bas"
'#uses "pp_math.bas"

Option Explicit


' -----------------------------------------------------
' -- Sackloch   - blind hole
' -----------------------------------------------------
' -- ppvx       : Bohrpos in X auf Ebene (Viewchange bezogen)
' -- ppvy       : Bohrpos in Y auf Ebene (Viewchange bezogen)
' -- depth      : Bohrtiefe auf Ebene bezogen (Viewchange bezogen)
' -- driller    : type of TDriller 
' -- dh         : type of TDH
' -----------------------------------------------------

Function Drilling_DH_Cylce_10(PPVX,PPVY,Depth,Sic_Z,Driller As tDriller, dh As tDH ,tools,zmax)

Dim Count As Integer
Dim I As Integer
Dim ActDepth As Double
Dim dx As Double
Dim DFI As Double  ' bohren mit Eintauchvorschub
Dim DFS As Double    ' bohren mit Vorschub bis auf 
Dim SIC_G0 As Double   ' distance above hole 
Const FF = 10000 ' fast feedrate position to Sic above hole
Dim wp As TWPI
Dim Oberk_abs, Unterk_abs, Tiefe_abs As Double
'Dim diff_eb As Double   ' Differenz Oberk_wks bis Ebene der Bohrung
Dim isok As Boolean
Dim Offsetwinkel_DH As Double

	wp = WPI(Marker.wp_actindex)

	Unterk_abs = (wp.WPoz - JobPara.npz)
	Oberk_abs = (wp.WPoz - JobPara.npz) + wp.WPz  ' Oberkante Werkstück
	Tiefe_abs = DH_View0.IPZ + Depth
' MW / SF 06.07.2016 Nicht mehr noetig - Engine macht das schon richtig
'	diff_eb = FinishedPart.Z - DH_View0.IPZ

    SIC_G0 = 2   ' distance above hole auf Ebene bezogen
    DFI = -2.5    ' Eintauchtiefe mit Eintauchvorschub auf Ebene bezogen
    DFS = 5      ' Abstand vor dem Durchtritt durch Werkstück auf Ebene bezogen



	wcnccom("Drill Cycle 10")
	' Überprüfung, ob die Ebene auf Oberkante Werkstück liegt 
'	If DH_View0.IPZ <> FinishedPart.Z Then
		' Einfügepunkt der Ebene weicht von Oberkante Werkstück ab
		' Differenz verrechnen
		
		' Neu MW 15.09.2005 * zusätzlichen Sicherheitsabstand einrechnen
	    'wcnccom("Additives ZMass:"+ftos(GetAddZSic))
		
		Sic_Z = Sic_Z + GetAddZSic
		'SIC_G0 =  - (diff_eb) +SIC_G0
		'Depth = Depth - (diff_eb) 
		'DFI = DFI - (diff_eb) 
		'DFS = DFS - (diff_eb) 
	
'		Sic_Z = Sic_Z + (FinishedPart.Z - DH_View0.IPZ) 
'		SIC_G0 =  - (FinishedPart.Z - DH_View0.IPZ) +SIC_G0
'		Depth = Depth - (FinishedPart.Z - DH_View0.IPZ) 
		
'	End If

	If Not Marker.FirstTime_DH_Drilling Then
		' jetzt bereits gebohrt jetzt erst die Spindeln vorlegen
		' dann die nächste Bohrposition anfahren
		' ----------------------------------------------------
		' -- hier Bohrspindeln vorlegen
		' --  -> Zeitgewinn erst anfahren dann check und vorlegen
		MT_WRITE_DHCode(actt,tools)
		' ----------------------------------------------------
	End If

	
	' Move to Drill - Position with the Security DH
    If MT_IsDHType(Actt)=1 Then
    	wcnc(G0+Move(PPVX,PPVY,Sic_Z,0,0))
    ElseIf MT_IsDHType(Actt)=3 Then
		Offsetwinkel_DH= StrToFloat(MT_get_Add_ID(actt,10003,isok))
		If isok Then
			wcnccom("Anfahrt "+actt.t.Description+ " mit C-Achse")
		    wcnc(G0+Move(PPVX,PPVY,Sic_Z,0,0) + RotAxisDH(Offsetwinkel_DH+Driller.ActRot))
		Else
			AddMistake("ID 10003 - Bohrkopf nicht gefunden")
		End If
	Else
    	AddMistake("BohrkopfTyp nicht berücksichtigt")
    	Exit All
	End If
	If Marker.FirstTime_DH_Drilling Then
		' beim 1. Mal vor dem 1. Vorlgen checken ob alles ok
		' Bohrkopf läuft etc.
		MT_Write_Check_Spindle
		Marker.FirstTime_DH_Drilling=False
		' ----------------------------------------------------
		' -- hier Bohrspindeln vorlegen
		' --  -> Zeitgewinn erst anfahren dann check und vorlegen
		MT_WRITE_DHCode(actt,tools)
		' ----------------------------------------------------
		
	End If
	' evtl. Überprüfung, ob Bohrkopf -bohrer vorgelegt etc.
	If (Marker.Last_DH_ToNo<>Driller.Tno) Then
		MT_Write_Check_Spindle
	End If
	' 



	'Go to safety position on the view
    wcnc(G1+Move(PPVX,PPVY,SIC_G0,FF,0))
    
    
    If (DFI>Depth) And Not (equal(Driller.ve,Driller.v)) Then
    	' Eintauchvorschub weicht vom Vorschub ab
       'Drilling with the surface feed
       wcnc(G1+Move(PPVX,PPVY,DFI,Driller.ve,0)) 
    End If
   	If Depth>=zmax Then 
	    'Drilling all depth
	    wcnc(G9+Move(PPVX,PPVY,Depth,Driller.v,0))
	Else
		' Bohren mit maximaler Zustellung
		Count=Depth\zmax
		For I = 1 To Count Step 1
			ActDepth=I*zmax
			If Equal(ActDepth,Depth) Then
			    wcnc(G9+Move(PPVX,PPVY,ActDepth,Driller.v,0))		
			Else
		    wcnc(G1+Move(PPVX,PPVY,ActDepth,Driller.v,0))
		    End If
		    ' jetzt zurück zum ausräumen
			wcnc(G1+Move(PPVX,PPVY,0,FF,0))
		Next I
		If ActDepth>Depth Then
			wcnc(G9+Move(PPVX,PPVY,Depth,Driller.v,0))
		End If
	End If

    
    'Go to safety position on the view
    'wcnc(G1+Move(PPVX,PPVY,SIC_G0,FF,0))
    
    wcnc(G1+Move(PPVX,PPVY,Sic_Z,FF,0))
    
End Function

' -----------------------------------------------------
' -- Durchgangsloch   - through boring
' -----------------------------------------------------
' -- ppvx       : Bohrpos in X auf Ebene (Viewchange bezogen)
' -- ppvy       : Bohrpos in Y auf Ebene (Viewchange bezogen)
' -- depth      : Bohrtiefe auf Ebene bezogen (Viewchange bezogen)
' -- driller    : type of TDriller 
' -- dh         : type of TDH
' -----------------------------------------------------

Function Drilling_DH_Cylce_20(PPVX,PPVY,Depth,Sic_Z,Driller As tDriller, dh As tDH ,tools,zmax)

Dim Count As Integer
Dim I As Integer
Dim ActDepth As Double
Dim dx As Double
Dim DFI As Double  ' bohren mit Eintauchvorschub
Dim DFS As Double    ' bohren mit Vorschub bis auf 
Dim SIC_G0 As Double   ' distance above hole 
Const FF = 10000 ' fast feedrate position to Sic above hole
Dim breakthrough As Boolean
Dim wp As TWPI
Dim Oberk_abs, Unterk_abs, Tiefe_abs As Double
'Dim diff_eb As Double   ' Differenz Oberk_wks bis Ebene der Bohrung
Dim isok As Boolean
Dim Offsetwinkel_DH As Double

	wp = WPI(Marker.wp_actindex)

	Unterk_abs = (wp.WPoz - JobPara.npz)
	Oberk_abs = (wp.WPoz - JobPara.npz) + wp.WPz  ' Oberkante Werkstück
	Tiefe_abs = DH_View0.IPZ + Depth
' MW / SF 06.07.2016 Nicht mehr noetig - Engine macht das schon richtig
'	diff_eb = FinishedPart.Z - DH_View0.IPZ

    SIC_G0 = 2   ' distance above hole auf Ebene bezogen
    DFI = -5    ' Eintauchtiefe mit Eintauchvorschub auf Ebene bezogen
    DFS = 5      ' Abstand vor dem Durchtritt durch Werkstück auf Ebene bezogen

	wcnccom("Drill Cycle 20")
	' Überprüfung, ob die Ebene auf Oberkante Werkstück liegt 
	' Differenz verrechnen
'	If DH_View0.IPZ <> Oberk_abs Then
		' Einfügepunkt der Ebene weicht von Oberkante Werkstück ab
		' Differenz verrechnen
		' Neu MW 15.09.2005 * zusätzlichen Sicherheitsabstand einrechnen
	    'wcnccom("Additives ZMass:"+ftos(GetAddZSic))
	    
		Sic_Z = Sic_Z + GetAddZSic
		'SIC_G0 =  - (diff_eb) +SIC_G0
		'Depth = Depth - (diff_eb) 
		'DFI = DFI - (diff_eb) 
		'DFS = DFS - (diff_eb) 
'	End If

	' --------------------------------------
	' -- Ermittlung, ob Loch auch tatsächlich durchs Teil geht ?
	' --------------------------------------
	If (Tiefe_abs) <=Unterk_abs Then
		' through - Tiefe um Überstand erhöhen
		breakthrough = True
		Depth = Depth-Driller.E_Len
		wcnccom("Durch = TRUE Ueberstand:"+ftos(Driller.e_len))
	Else
		wcnccom("Durch = FALSE")
	 	breakthrough = False
	End If

	If Not Marker.FirstTime_DH_Drilling Then
		' jetzt bereits gebohrt jetzt erst die Spindeln vorlegen
		' dann die nächste Bohrposition anfahren
		' ----------------------------------------------------
		' -- hier Bohrspindeln vorlegen
		' --  -> Zeitgewinn erst anfahren dann check und vorlegen
		MT_WRITE_DHCode(actt,tools)
		' ----------------------------------------------------
	End If
	
	' Move to Drill - Position with the Security DH
	If MT_IsDHType(Actt)=1 Then
    	wcnc(G0+Move(PPVX,PPVY,Sic_Z,0,0))
    ElseIf MT_IsDHType(Actt)=3 Then
		Offsetwinkel_DH= StrToFloat(MT_get_Add_ID(actt,10003,isok))
		If isok Then
			'Move to Drill - Position with the Security DH
			'wcnc("G0 C11="+ ftos(MT_get_Add_ID(actt,10003,isok)))
			wcnccom("Anfahrt "+actt.t.Description+ " mit C-Achse")
		    wcnc(G0+Move(PPVX,PPVY,Sic_Z,0,0) + RotAxisDH(Offsetwinkel_DH+Driller.ActRot))
		Else
			AddMistake("ID 10003 - Bohrkopf nicht gefunden")
		End If
    Else
    	AddMistake("BohrkopfTyp nicht berücksichtigt")
    	Exit All
	End If

	If Marker.FirstTime_DH_Drilling Then
		' beim 1. Mal vor dem 1. Vorlgen checken ob alles ok
		' Bohrkopf läuft etc.
		MT_Write_Check_Spindle
		Marker.FirstTime_DH_Drilling = False
		' ----------------------------------------------------
		' -- hier Bohrspindeln vorlegen
		' --  -> Zeitgewinn erst anfahren dann check und vorlegen
		MT_WRITE_DHCode(actt,tools)
		' ----------------------------------------------------
		
	End If
	' evtl. Überprüfung, ob Bohrkopf -bohrer vorgelegt etc.
	If (Marker.Last_DH_ToNo<>Driller.Tno) Then
		MT_Write_Check_Spindle
	End If
	' 
    
    
    

	'Go to safety position on the view (SIC)
    wcnc(G1+Move(PPVX,PPVY,SIC_G0,FF,0))
    
    If (DFI>Depth) And Not (equal(Driller.ve,Driller.v)) Then
    	' Eintauchvorschub weicht vom Vorschub ab und Anbohrtiefe weniger tief als Bohrtiefe
       'Drilling with the surface feed
       wcnc(G1+Move(PPVX,PPVY,DFI,Driller.ve,0)) 
    End If
   	If Depth>=zmax Then 
	    'Drilling all depth
	    If breakthrough Then
		    ' --- Bohrung geht durch ---
		    'Drilling bis vor dem Austrittsmass DFS
	        wcnc(G1+Move(PPVX,PPVY,-(DH_View0.IPZ-Unterk_abs)+DFS,Driller.v,0)) 
	    	'jetzt durchbohren mit Austauchvorschub
		    wcnc(G9+Move(PPVX,PPVY,Depth,Driller.va,0))
		Else
		    wcnc(G9+Move(PPVX,PPVY,Depth,Driller.v,0))
		End If
	    
	Else
		' mit Rückzug
		' Bohren mit maximaler Zustellung
	    If breakthrough Then
		    ' --- Bohrung geht durch ---
		    Count=(-(DH_View0.IPZ-Unterk_abs)+DFS)\zmax
			For I = 1 To Count Step 1
				ActDepth=I*zmax
				If EQUAL(ActDepth,Depth) Then
			    	wcnc(G9+Move(PPVX,PPVY,ActDepth,Driller.v,0))
			    Else
				   	wcnc(G1+Move(PPVX,PPVY,ActDepth,Driller.v,0))		    
			    End If
				wcnc(G0+Move(PPVX,PPVY,0,Driller.v,0))
			Next I
			If ActDepth>Depth Then
			    'Drilling bis vor dem Austrittsmass DFS
		        wcnc(G1+Move(PPVX,PPVY,-(DH_View0.IPZ-Unterk_abs)+DFS,Driller.v,0)) 
		    	'jetzt durchbohren mit Austauchvorschub
				wcnc(G9+Move(PPVX,PPVY,Depth,Driller.va,0))
			End If
		Else
		    ' --- Bohrung geht nicht durch ---
			Count=Depth\zmax  
			For I = 1 To Count Step 1
				ActDepth=I*zmax
				If EQUAL(ActDepth,Depth) Then
			    	wcnc(G9+Move(PPVX,PPVY,ActDepth,Driller.v,0))
			    Else
			    	wcnc(G1+Move(PPVX,PPVY,ActDepth,Driller.v,0))
			    End If
				wcnc(G0+Move(PPVX,PPVY,0,Driller.v,0))
			Next I
			If ActDepth>Depth Then
				wcnc(G9+Move(PPVX,PPVY,Depth,Driller.v,0))
			End If
		End If
	End If
	
    	
    'Go to safety position on the view with Moveout Feedrate Drillinghead
   
    'wcnc(G1+Move(PPVX,PPVY,SIC_G0,FF,0))
    
    wcnc(G1+Move(PPVX,PPVY,Sic_Z,FF,0))
    
End Function

' -----------------------------------------------------
' -- Hinge hole   - dwell Topfband
' -----------------------------------------------------
' -- ppvx       : Bohrpos in X auf Ebene (Viewchange bezogen)
' -- ppvy       : Bohrpos in Y auf Ebene (Viewchange bezogen)
' -- depth      : Bohrtiefe auf Ebene bezogen (Viewchange bezogen)
' -- driller    : type of TDriller 
' -- dh         : type of TDH
' -----------------------------------------------------

Function Drilling_DH_Cylce_30(PPVX,PPVY,Depth,Sic_Z,Driller As tDriller, dh As tDH,tools,ZMax)

Dim Count As Integer
Dim I As Integer
Dim ActDepth As Double
Dim dx As Double
Dim DFI As Double  ' bohren mit Eintauchvorschub
Dim SIC_G0 As Double   ' distance above hole 
Const FF = 10000 ' fast feedrate position to Sic above hole
Dim wp As TWPI
Dim Oberk_abs, Unterk_abs, Tiefe_abs As Double
'Dim diff_eb As Double   ' Differenz Oberk_wks bis Ebene der Bohrung
Dim isok As Boolean
'Dim FirstTNr As Long
'Dim Add_C As Double
Dim Offsetwinkel_DH As Double

	
	wp = WPI(Marker.wp_actindex)

	Unterk_abs = (wp.WPoz - JobPara.npz)
	Oberk_abs = (wp.WPoz - JobPara.npz) + wp.WPz  ' Oberkante Werkstück
	Tiefe_abs = DH_View0.IPZ + Depth


' MW / SF 06.07.2016 Nicht mehr noetig - Engine macht das schon richtig
	
'	diff_eb = FinishedPart.Z - DH_View0.IPZ

    SIC_G0 = 2   ' distance above hole auf Ebene bezogen
    DFI = -2.5    ' Eintauchtiefe mit Eintauchvorschub auf Ebene bezogen


	wcnccom("Drill Cycle 30")
	
	' Überprüfung, ob die Ebene auf Oberkante Werkstück liegt 
'	If DH_View0.IPZ <> FinishedPart.Z Then
		' Neu MW 15.09.2005 * zusätzlichen Sicherheitsabstand einrechnen
	    'wcnccom("Additives ZMass:"+ftos(GetAddZSic))

		Sic_Z = Sic_Z + GetAddZSic
		'SIC_G0 =  - (diff_eb) +SIC_G0
		'Depth = Depth - (diff_eb) 
		'DFI = DFI - (diff_eb) 
	
'		Sic_Z = Sic_Z + (FinishedPart.Z - DH_View0.IPZ) 
'		SIC_G0 =  - (FinishedPart.Z - DH_View0.IPZ) +SIC_G0
'		Depth = Depth - (FinishedPart.Z - DH_View0.IPZ) 
'	End If

	If Not Marker.FirstTime_DH_Drilling Then
		' jetzt bereits gebohrt jetzt erst die Spindeln vorlegen
		' dann die nächste Bohrposition anfahren
		' ----------------------------------------------------
		' -- hier Bohrspindeln vorlegen
		' --  -> Zeitgewinn erst anfahren dann check und vorlegen
		MT_WRITE_DHCode(actt,tools)
		' ----------------------------------------------------
	End If

	
	' Move to Drill - Position with the Security DH
	If MT_IsDHType(Actt)=1 Then
    	wcnc(G0+Move(PPVX,PPVY,Sic_Z,0,0))
    ElseIf MT_IsDHType(Actt)=3 Then
		Offsetwinkel_DH= StrToFloat(MT_get_Add_ID(actt,10003,isok))
		If isok Then
			'Move to Drill - Position with the Security DH
			'wcnc("G0 C11="+ ftos(MT_get_Add_ID(actt,10003,isok)))
			wcnccom("Anfahrt "+actt.t.Description+ " mit C-Achse")
		    wcnc(G0+Move(PPVX,PPVY,Sic_Z,0,0) + RotAxisDH(Offsetwinkel_DH+Driller.ActRot))
		Else
			AddMistake("ID 10003 - Bohrkopf nicht gefunden")
		End If
    Else
    	AddMistake("BohrkopfTyp nicht berücksichtigt")
    	Exit All
	End If

	If Marker.FirstTime_DH_Drilling Then
		' beim 1. Mal vor dem 1. Vorlgen checken ob alles ok
		' Bohrkopf läuft etc.
		MT_Write_Check_Spindle
		Marker.FirstTime_DH_Drilling = False
		
		' ----------------------------------------------------
		' -- hier Bohrspindeln vorlegen
		' --  -> Zeitgewinn erst anfahren dann check und vorlegen
		MT_WRITE_DHCode(actt,tools)
		' ----------------------------------------------------
	End If

    
	' evtl. Überprüfung, ob Bohrkopf -bohrer vorgelegt etc.
	If (Marker.Last_DH_ToNo<>Driller.Tno) Then
		MT_Write_Check_Spindle
	End If
	' 

	'Go to safety position on the view (SIC)
    wcnc(G1+Move(PPVX,PPVY,SIC_G0,FF,0))
    
    If (DFI>Depth) And Not (equal(Driller.ve,Driller.v)) Then
    	' Eintauchvorschub weicht vom Vorschub ab
       'Drilling with the surface feed
       wcnc(G1+Move(PPVX,PPVY,DFI,Driller.ve,0)) 
    End If
    
 	If Depth>=ZMax Then 
    	'Drilling all depth
	    wcnc(G1+Move(PPVX,PPVY,Depth,Driller.v,0))
	Else
		' Bohren mit maximaler Zustellung
		Count=Depth\ZMax  
		For I = 1 To Count Step 1
			ActDepth=I*ZMax
		    wcnc(G1+Move(PPVX,PPVY,ActDepth,Driller.v,0))
			wcnc(G0+Move(PPVX,PPVY,0,Driller.v,0))
		Next I
		If ActDepth>Depth Then
			wcnc(G1+Move(PPVX,PPVY,Depth,Driller.v,0))
		End If
	
	End If
    	
    wcnc("G04 F0.1")
    'Go to safety position on the view with Moveout Feedrate Drillinghead
   
    'wcnc(G1+Move(PPVX,PPVY,SIC_G0,FF,0))
    
    wcnc(G1+Move(PPVX,PPVY,Sic_Z,FF,0))
    
End Function


' -----------------------------------------------------
' -- horizontal drilling
' -----------------------------------------------------
' -- ppvx       : Bohrpos in X auf Ebene (Viewchange bezogen)
' -- ppvy       : Bohrpos in Y auf Ebene (Viewchange bezogen)
' -- ppvz       : Bohrpos in Y auf Ebene (Viewchange bezogen)
' -- depth      : Bohrtiefe auf Ebene bezogen (Viewchange bezogen)
' -- driller    : type of TDriller 
' -- dh         : type of TDH
' -----------------------------------------------------

Function Drilling_DHorz(PPVX,PPVY,PPVZ,Depth,DFlag,Free,zmax,Driller As tDriller, dh As tDH,tools)

Dim Count As Integer
Dim I As Integer
Dim ActDepth As Double
Dim dx As Double
Const DFI=-3
Const SIC = 2   ' distance above hole 
Const FF = 10000 ' fast feedrate position to Sic above hole
Dim isok As Boolean
'Dim FirstTNr As Long
'Dim Add_C As Double
Dim Offsetwinkel_DH As Double

	wcnccom("Drill Cycle horizontal")
	
	If Not Marker.FirstTime_DH_Drilling Then
		' jetzt bereits gebohrt jetzt erst die Spindeln vorlegen
		' dann die nächste Bohrposition anfahren
		' ----------------------------------------------------
		' -- hier Bohrspindeln vorlegen
		' --  -> Zeitgewinn erst anfahren dann check und vorlegen
		MT_WRITE_DHCode(actt,tools)
		' ----------------------------------------------------
	Else
		' mw 21.09.2005 immer vorlegen
	    '.-------------------------
		MT_WRITE_DHCode(actt,tools)
	    '.-------------------------

	End If

	' in Z- Runter auf Bohrposition	
    If MT_IsDHType(Actt)=1 Then
    	wcnc(G0+Move(PPVX,PPVY,Actt.t_dh.SecurityHorz,0,0))
    ElseIf MT_IsDHType(Actt)=3 Then
		Offsetwinkel_DH= StrToFloat(MT_get_Add_ID(actt,10003,isok))
		If isok Then
			wcnccom("Anfahrt "+actt.t.Description+ " mit C-Achse")
	    	wcnc(G0+Move(PPVX,PPVY,Actt.t_dh.SecurityHorz,0,0) + RotAxisDH(Offsetwinkel_DH+Driller.ActRot))
		Else
			AddMistake("ID 10003 - Bohrkopf nicht gefunden")
		End If
    Else
    	AddMistake("BohrkopfTyp nicht berücksichtigt")
    	Exit All
	End If

    
	If Marker.FirstTime_DH_Drilling Then
		' beim 1. Mal vor dem 1. Vorlgen checken ob alles ok
		' Bohrkopf läuft etc.
		MT_Write_Check_Spindle
		Marker.FirstTime_DH_Drilling = False
		' ----------------------------------------------------
		' -- hier Bohrspindeln vorlegen
		MT_WRITE_DHCode(actt,tools)
		' ----------------------------------------------------
	Else	
		If (Marker.Last_DH_ToNo<>Driller.Tno) Then
			MT_Write_Check_Spindle
		End If
	End If

	'Go to safety position on the view
    wcnc(G0+Move(PPVX,PPVY,PPVZ+SIC,FF,0))


    
    If (DFI>Depth) And ((DFI>zmax) Or (DFlag=0)) And Not equal(Driller.v,Driller.ve) Then
       'Drilling with the surface feed
       wcnc(G1+Move(PPVX,PPVY,PPVZ+DFI,Driller.ve,0)) 
    End If
    
    If DFlag=0 Then
      'Drilling all depth
      wcnc(G9+Move(PPVX,PPVY,PPVZ+Depth,Driller.v,0))
    Else  
       'Drilling with a maximum depth (ZMax)
      Count=Depth\zmax  
      For I = 1 To Count Step 1
        ActDepth=I*zmax
        If Equal(ActDepth,Depth) Then
        	wcnc(G9+Move(PPVX,PPVY,PPVZ+ActDepth,Driller.v,0))        
        Else
        	wcnc(G1+Move(PPVX,PPVY,PPVZ+ActDepth,Driller.v,0))
        End If
        
        ' Rückzug auf 0
        wcnc(G1+Move(PPVX,PPVY,PPVZ,FF,0))

	  Next I
      If ActDepth>Depth Then
        wcnc(G9+Move(PPVX,PPVY,PPVZ+Depth,Driller.v,0))
      End If
    End If
    
    'Go to safety position on the view
    wcnc(G1+Move(PPVX,PPVY,PPVZ+SIC,FF,0))
    
    wcnc(G0+Move(PPVX,PPVY,Actt.t_dh.SecurityHorz,0,0))
    
End Function
