' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \hh7\pp_bohrdh.bas
' -- 
' -----------------------------------------
'#uses "pp_math.bas"
'#uses "pp_global.bas"
'#uses "pp_mt.bas"
'#uses "pp_mtf.bas"

Option Explicit

Dim tmp_dfi,tmp_dfs As Double 


'get move string with x,y,z,feedrate,trc parameter
Function Move(ByVal X,ByVal Y,ByVal Z,Feedrate,TRC)

   Dim chars As String
   Dim checked_feedrate As Double
   
   
   chars=""

   
   ' Neu MW 20.04.2005
   ' check Vorschub - Move wird momentan noch ueber das Bohren mit definierbaren Vorschueben aufgerufen, deshalb hier Pruefung
   If Feedrate>0 Then
	   checked_feedrate = MT_CheckFeedrate(actt,Feedrate)
	   'If Not equal(checked_feedrate,Feedrate) Then
	   '	  pp_err(126)
	   'End If
	End If
   
   
   If (MovePara.TRC<>TRC)  Then
     chars= chars + GetTRCStr(TRC)
   End If
   
   ' --
   ' -- Neu MW 13.02.2007 - 
   ' -- wenn Kreisinterpolation in Z ohne Ausgabe einer X oder Y - Koordinate
   ' -- ist auf Siemens nicht moeglich - faehrt ?????
   ' --
   
   If (Not equal(X,LastPos.X)) Or (Not equal(Z,LastPos.Z)) Then
      chars= chars + XToS(X)
   End If
   If (Not equal(Y,LastPos.Y)) Or (Not equal(Z,LastPos.Z)) Then
      chars= chars +  YToS(Y)
   End If
   If Not equal(Z,LastPos.Z) Then
      chars= chars + ZToS(Z)
   End If

   If (Not equal(MovePara.Feedrate,checked_feedrate)) And (checked_feedrate>0) Then
      chars= chars + GetFeedrateStr(checked_feedrate)
   End If
   Call PosSet(X,Y,Z)
   Call MoveParaSet(checked_feedrate,TRC)
   Move=chars
End Function


Function Drilling_DH_Cylce_10(PPVX,PPVY,Depth,Sic_Z,Driller As tDriller, dh As tDH ,tools,zmax)

Dim Count As Integer
Dim I As Integer
Dim ActDepth As Double
Dim dx As Double
Dim DFI As Double  ' bohren mit Eintauchvorschub
Dim DFS As Double    ' bohren mit Vorschub bis auf 
Dim SIC_G0 As Double   ' distance above hole 
Dim FF As Double    ' fast feedrate position to Sic above hole
Dim MUF As Double    ' MW 06.07.2015
Dim DWELL_TIME As Double  'Verweilzeit bei Topfband         AK 09.02.2011
Dim wp As TWPI
Dim Oberk_abs, Unterk_abs, Tiefe_abs As Double

	wp = WPI(Marker.wp_actindex)

	Unterk_abs = (wp.WPoz - JobPara.npz)
	Oberk_abs = (wp.WPoz - JobPara.npz) + wp.WPz  ' Oberkante Werkstueck
	Tiefe_abs = DH_View0.IPZ + Depth
	FF = 10000 ' fast feedrate position to Sic above hole
	MUF = FF
    SIC_G0 = 2   ' distance above hole auf Ebene bezogen
    DFI = -2.5    ' Eintauchtiefe mit Eintauchvorschub auf Ebene bezogen
    DFS = 5      ' Abstand vor dem Durchtritt durch Werkstueck auf Ebene bezogen
    DWELL_TIME = 0.1  'Verweilzeit bei Topfband         AK 09.02.2011
	GetParams_Drills_Edge(MUF,FF,SIC_G0,DFI,DFS,DWELL_TIME,dh,Driller)          ' Neuer uebergabeparameter AK 09.02.2011

	wcnccom("Drill Cycle 10")
    wcnccom("Additives ZMass:"+ftos(GetAddZSic))
		
	Sic_Z = Sic_Z  + GetAddZSic

	If Not Marker.FirstTime_DH_Drilling Then
		' jetzt bereits gebohrt jetzt erst die Spindeln vorlegen
		' dann die naechste Bohrposition anfahren
		' ----------------------------------------------------
		' -- hier Bohrspindeln vorlegen
		' --  -> Zeitgewinn erst anfahren dann check und vorlegen
		MT_WRITE_DHCode(actt,tools)
		' ----------------------------------------------------
	End If

	
	' Move to Drill - Position with the Security DH
    wcnc(G0+Move(PPVX,PPVY,Sic_Z,0,0))
	If Marker.FirstTime_DH_Drilling Then
		' beim 1. Mal vor dem 1. Vorlgen checken ob alles ok
		' Bohrkopf laeuft etc.
		MT_Write_Check_Spindle
		Marker.FirstTime_DH_Drilling=False
		' ----------------------------------------------------
		' -- hier Bohrspindeln vorlegen
		' --  -> Zeitgewinn erst anfahren dann check und vorlegen
		MT_WRITE_DHCode(actt,tools)
		' ----------------------------------------------------
		
	End If
	
	
	If (Marker.Last_DH_Tools<>tools) Then
		MT_Write_Check_Spindle
	End If
	
	'Go to safety position on the view
    wcnc(G1+Move(PPVX,PPVY,SIC_G0,FF,0))
    
    If (DFI>Depth) And Not (equal(Driller.ve,Driller.v)) Then
    	' Eintauchvorschub weicht vom Vorschub ab
       'Drilling with the surface feed
       wcnc(G1+Move(PPVX,PPVY,DFI,Driller.ve,0)) 
    End If
   	If Depth>=zmax Then 
	    'Drilling all depth
	    wcnc(G1+Move(PPVX,PPVY,Depth,Driller.v,0))
	Else
		' Bohren mit maximaler Zustellung
		Count=Depth\zmax
		For I = 1 To Count Step 1
			ActDepth=I*zmax
		    wcnc(G1+Move(PPVX,PPVY,ActDepth,Driller.v,0))
		    ' jetzt zurueck zum ausraeumen
	        If dh.G0_up Then
		        wcnc_IDD("BRISK")
				wcnc(G0+Move(PPVX,PPVY,0,Driller.v,0))
		    	wcnc_IDD("SOFT")
		    Else
				wcnc(G1+Move(PPVX,PPVY,0,MUF,0))
			End If
		Next I
		If ActDepth>Depth Then
			wcnc(G1+Move(PPVX,PPVY,Depth,Driller.v,0))
		End If
	End If
    
    'Go to safety position on the view
    If dh.G0_up Then
        wcnc_IDD("BRISK")
	    wcnc(G0+Move(PPVX,PPVY,Sic_Z,FF,0))
    	wcnc_IDD("SOFT")
    Else
	    wcnc(G1+Move(PPVX,PPVY,SIC_G0,MUF,0))
	    wcnc(G1+Move(PPVX,PPVY,Sic_Z,FF,0))
	End If
    
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
Dim FF As Double ' fast feedrate position to Sic above hole
Dim MUF As Double
Dim DWELL_TIME As Double  'Verweilzeit bei Topfband         AK 09.02.2011
Dim breakthrough As Boolean
Dim wp As TWPI
Dim Oberk_abs, Unterk_abs, Tiefe_abs As Double

	wp = WPI(Marker.wp_actindex)

	' Nullpunkt - Offset Z aus Nullpunkt beruecksichtigen
	wp.WPoz = wp.WPoz + wp.Soz
	' Hoehendifferenz zu anderen Werkstuecken
	' Werkstueck - Lage Z - Gesamt Nullpunktsverschiebung
	' wenn alle Werkstuecke gleich liegen UnterK_ABS = 0
	Unterk_abs = (wp.WPoz - JobPara.npz)
	Oberk_abs = (wp.WPoz - JobPara.npz) + wp.WPz  ' Oberkante Werkstueck
	' 
	Tiefe_abs = DH_View0.IPZ + Depth

	FF = 10000 ' fast feedrate position to Sic above hole
	MUF = FF
    SIC_G0 = 2   ' distance above hole auf Ebene bezogen
    DFI = -5    ' Eintauchtiefe mit Eintauchvorschub auf Ebene bezogen
    DFS = 5      ' Abstand vor dem Durchtritt durch Werkstueck auf Ebene bezogen
    DWELL_TIME = 0.1  'Verweilzeit bei Topfband         AK 09.02.2011
    
	GetParams_Drills_Edge(MUF,FF,SIC_G0,DFI,DFS,DWELL_TIME,dh,Driller) ' Neuer uebergabeparameter AK 09.02.2011

	wcnccom("Drill Cycle 20")
    wcnccom("Additives ZMass:"+ftos(GetAddZSic))
	    
	Sic_Z = Sic_Z + GetAddZSic

	' --------------------------------------
	' -- Ermittlung, ob Loch auch tatsaechlich durchs Teil geht ?
	' --------------------------------------
	If (Tiefe_abs) <=Unterk_abs Then
		' through - Tiefe um ueberstand erhoehen
		breakthrough = True
		Depth = Depth-Driller.E_Len
		wcnccom("Durch = TRUE Ueberstand:"+ftos(Driller.e_len))
	Else
		wcnccom("Durch = FALSE")
	 	breakthrough = False
	End If

	If Not Marker.FirstTime_DH_Drilling Then
		' jetzt bereits gebohrt jetzt erst die Spindeln vorlegen
		' dann die naechste Bohrposition anfahren
		' ----------------------------------------------------
		' -- hier Bohrspindeln vorlegen
		' --  -> Zeitgewinn erst anfahren dann check und vorlegen
		MT_WRITE_DHCode(actt,tools)
		' ----------------------------------------------------
	End If
	
	' Move to Drill - Position with the Security DH
    wcnc(G0+Move(PPVX,PPVY,Sic_Z,0,0))
    
	If Marker.FirstTime_DH_Drilling Then
		' beim 1. Mal vor dem 1. Vorlgen checken ob alles ok
		' Bohrkopf laeuft etc.
		MT_Write_Check_Spindle
		Marker.FirstTime_DH_Drilling = False
		' ----------------------------------------------------
		' -- hier Bohrspindeln vorlegen
		' --  -> Zeitgewinn erst anfahren dann check und vorlegen
		MT_WRITE_DHCode(actt,tools)
		' ----------------------------------------------------
		
	End If
	' evtl. ueberpruefung, ob Bohrkopf -bohrer vorgelegt etc.
	If (Marker.Last_DH_Tools<>tools) Then
		MT_Write_Check_Spindle
	End If

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
		    wcnc(G1+Move(PPVX,PPVY,Depth,Driller.va,0))
		Else
		    wcnc(G1+Move(PPVX,PPVY,Depth,Driller.v,0))
		End If
	    
	Else
		' mit Rueckzug
		' Bohren mit maximaler Zustellung
	    If breakthrough Then
		    ' --- Bohrung geht durch ---
		    Count=(-(DH_View0.IPZ-Unterk_abs)+DFS)\zmax
			For I = 1 To Count Step 1
				ActDepth=I*zmax
			    wcnc(G1+Move(PPVX,PPVY,ActDepth,Driller.v,0))
		        If dh.G0_up Then
			        wcnc_IDD("BRISK")
					wcnc(G0+Move(PPVX,PPVY,0,Driller.v,0))
			    	wcnc_IDD("SOFT")
			    Else
					wcnc(G1+Move(PPVX,PPVY,0,MUF,0))
				End If
			Next I
			If ActDepth>Depth Then
			    'Drilling bis vor dem Austrittsmass DFS
		        wcnc(G1+Move(PPVX,PPVY,-(DH_View0.IPZ-Unterk_abs)+DFS,Driller.v,0)) 
		    	'jetzt durchbohren mit Austauchvorschub
				wcnc(G1+Move(PPVX,PPVY,Depth,Driller.va,0))
			End If
		Else
		    ' --- Bohrung geht nicht durch ---
			Count=Depth\zmax  
			For I = 1 To Count Step 1
				ActDepth=I*zmax
			    wcnc(G1+Move(PPVX,PPVY,ActDepth,Driller.v,0))
			    
		        If dh.G0_up Then
			        wcnc_IDD("BRISK")
					wcnc(G0+Move(PPVX,PPVY,0,Driller.v,0))
			    	wcnc_IDD("SOFT")
			    Else
					wcnc(G1+Move(PPVX,PPVY,0,MUF,0))
			    End If
			Next I
			If ActDepth>Depth Then
				wcnc(G1+Move(PPVX,PPVY,Depth,Driller.v,0))
			End If
		End If
	End If
	
    	
    'Go to safety position on the view with Moveout Feedrate Drillinghead
    
    If dh.G0_up Then
        wcnc_IDD("BRISK")
	    wcnc(G0+Move(PPVX,PPVY,Sic_Z,FF,0))
    	wcnc_IDD("SOFT")
    Else
	    wcnc(G1+Move(PPVX,PPVY,SIC_G0,MUF,0))
	    wcnc(G1+Move(PPVX,PPVY,Sic_Z,FF,0))
	End If
    
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

Function Drilling_DH_Cylce_30(PPVX,PPVY,Depth,Sic_Z,Driller As tDriller, dh As tDH,tools,zmax)

Dim Count As Integer
Dim I As Integer
Dim ActDepth As Double
Dim dx As Double
Dim DFI,DFS As Double  ' bohren mit Eintauchvorschub
Dim SIC_G0 As Double   ' distance above hole 
Dim FF As Double ' fast feedrate position to Sic above hole
Dim MUF As Double
Dim DWELL_TIME As Double  'Verweilzeit bei Topfband         AK 09.02.2011
Dim wp As TWPI
Dim Oberk_abs, Unterk_abs, Tiefe_abs As Double
	wp = WPI(Marker.wp_actindex)

	Unterk_abs = (wp.WPoz - JobPara.npz)
	Oberk_abs = (wp.WPoz - JobPara.npz) + wp.WPz  ' Oberkante Werkstueck
	Tiefe_abs = DH_View0.IPZ + Depth
	FF = 10000
	MUF = FF
    SIC_G0 = 2   ' distance above hole auf Ebene bezogen
    DFI = -2.5    ' Eintauchtiefe mit Eintauchvorschub auf Ebene bezogen
    DFS = 5    ' nicht benutzt bei Cycle 30
    DWELL_TIME = 0.1  'Verweilzeit bei Topfband         AK 09.02.2011

	GetParams_Drills_Edge(MUF,FF,SIC_G0,DFI,DFS,DWELL_TIME,dh,Driller) ' Neuer uebergabeparameter AK 09.02.2011

	wcnccom("Drill Cycle 30")
	
    wcnccom("Additives ZMass:"+ftos(GetAddZSic))
	Sic_Z = Sic_Z + GetAddZSic

	If Not Marker.FirstTime_DH_Drilling Then
		' jetzt bereits gebohrt jetzt erst die Spindeln vorlegen
		' dann die naechste Bohrposition anfahren
		' ----------------------------------------------------
		' -- hier Bohrspindeln vorlegen
		' --  -> Zeitgewinn erst anfahren dann check und vorlegen
		MT_WRITE_DHCode(actt,tools)
		' ----------------------------------------------------
	End If

	
	' Move to Drill - Position with the Security DH
    wcnc(G0+Move(PPVX,PPVY,Sic_Z,0,0))

	If Marker.FirstTime_DH_Drilling Then
		' beim 1. Mal vor dem 1. Vorlgen checken ob alles ok
		' Bohrkopf laeuft etc.
		MT_Write_Check_Spindle
		Marker.FirstTime_DH_Drilling = False
		
		' ----------------------------------------------------
		' -- hier Bohrspindeln vorlegen
		' --  -> Zeitgewinn erst anfahren dann check und vorlegen
		MT_WRITE_DHCode(actt,tools)
		' ----------------------------------------------------
	End If

    
	' evtl. ueberpruefung, ob Bohrkopf -bohrer vorgelegt etc.
	If (Marker.Last_DH_Tools<>tools) Then
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
    
 	If Depth>=zmax Then 
    	'Drilling all depth
	    wcnc(G1+Move(PPVX,PPVY,Depth,Driller.v,0))
	Else
		' Bohren mit maximaler Zustellung
		Count=Depth\zmax  
		For I = 1 To Count Step 1
			ActDepth=I*zmax
		    wcnc(G1+Move(PPVX,PPVY,ActDepth,Driller.v,0))
	        If dh.G0_up Then
		        wcnc_IDD("BRISK")
				wcnc(G0+Move(PPVX,PPVY,0,Driller.v,0))
		    	wcnc_IDD("SOFT")
		    Else
				wcnc(G1+Move(PPVX,PPVY,0,MUF,0))
			End If
		Next I
		If ActDepth>Depth Then
			wcnc(G1+Move(PPVX,PPVY,Depth,Driller.v,0))
		End If
	
	End If
    	
    WCNC_IDD("G04",DWELL_TIME)        ' Verweilzeit aus ID1004 (Bohrkopf/Schneide) aenderbar   AK 09.02.2011
    
    'Go to safety position on the view with Moveout Feedrate Drillinghead
    wcnc(G1+Move(PPVX,PPVY,SIC_G0,MUF,0))
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


	wcnccom("Drill Cycle horizontal")
	
	MT_WRITE_DHCode(actt,tools)

	' in Z- Runter auf Bohrposition	
    wcnc(G0+Move(PPVX,PPVY,Actt.t_dh.SecurityHorz,0,0))
    
	If Marker.FirstTime_DH_Drilling Then
		' beim 1. Mal vor dem 1. Vorlgen checken ob alles ok
		' Bohrkopf laeuft etc.
		MT_Write_Check_Spindle
		Marker.FirstTime_DH_Drilling = False
		' ----------------------------------------------------
		' -- hier Bohrspindeln vorlegen
		MT_WRITE_DHCode(actt,tools)
		' ----------------------------------------------------
	Else	
		If (Marker.Last_DH_Tools<>tools) Then
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
      wcnc(G1+Move(PPVX,PPVY,PPVZ+Depth,Driller.v,0))
    Else  
       'Drilling with a maximum depth (ZMax)
      Count=Depth\zmax  
      For I = 1 To Count Step 1
        ActDepth=I*zmax
        wcnc(G1+Move(PPVX,PPVY,PPVZ+ActDepth,Driller.v,0))
        
        ' Rueckzug auf 0
        wcnc(G1+Move(PPVX,PPVY,PPVZ,FF,0))

	  Next I
      If ActDepth>Depth Then
        wcnc(G1+Move(PPVX,PPVY,PPVZ+Depth,Driller.v,0))
      End If
    End If
    
    'Go to safety position on the view
    If dh.G0_up Then
    	wcnc(G0+Move(PPVX,PPVY,PPVZ+SIC,FF,0))
	Else    
    	wcnc(G1+Move(PPVX,PPVY,PPVZ+SIC,FF,0))
    End If
    
    wcnc(G0+Move(PPVX,PPVY,Actt.t_dh.SecurityHorz,0,0))
    
End Function

Function GetParams_Drills_Edge(MUF,FF,SIC_G0,DFI,DFS,DWELL_TIME,dh As tdh, Drill As tDriller)
Dim tmp As Variant

Const ID_FF = 1000
Const ID_SIC_G0 = 1001
Const ID_DFI_Edge = 1002
Const ID_DFS_Edge = 1003
Dim ID_DWELL_TIME As Integer    ' bisher Const ID_DWELL_TIME = 1004
Dim ID_MUF As Integer           ' neu = ID 1004

	If Not actt.t_DH.DrillingHead.Additions.GetAddition_ID(1005) Is Nothing Then
		' ID 1005 -> Verweilzeit neu gefunden 
		ID_MUF = 1004           ' Rueckzugsvorschub
		ID_DWELL_TIME = 1005    ' Verweilzeit
	Else
		' Kompatibilitaetsmodus
		ID_MUF = ID_FF          ' Anfahrvorschub = Rueckzugsvorschub
		ID_DWELL_TIME = 1004    ' Verweilzeit aus ID1004 wie bisher
	End If


	' 1. Aus Bohrkopf versuchen die Werte zu holen
	If Not actt.t_DH.DrillingHead.Additions.GetAddition_ID(ID_FF) Is Nothing Then
		tmp = actt.t_DH.DrillingHead.Additions.GetAddition_ID(ID_FF).Value
		If Val(tmp)>=0 Then
			FF = Val(tmp)
		End If
	End If
	If Not actt.t_DH.DrillingHead.Additions.GetAddition_ID(ID_SIC_G0) Is Nothing Then
		tmp = actt.t_DH.DrillingHead.Additions.GetAddition_ID(ID_SIC_G0).Value
		If Val(tmp)>=0 Then
			SIC_G0 = Val(tmp)
		End If
	End If
	
	If Not actt.t_DH.DrillingHead.Additions.GetAddition_ID(ID_DFI_Edge) Is Nothing Then
		tmp = actt.t_DH.DrillingHead.Additions.GetAddition_ID(ID_DFI_Edge).Value
		If Val(tmp)>=0 Then
			' dieser immer negativ
			DFI = -Abs(Val(tmp))
		End If
	End If
	
	If Not actt.t_DH.DrillingHead.Additions.GetAddition_ID(ID_DFS_Edge) Is Nothing Then
		tmp = actt.t_DH.DrillingHead.Additions.GetAddition_ID(ID_DFS_Edge).Value
		If Val(tmp)>=0 Then
			DFS = Val(tmp)
		End If
	End If

	If Not actt.t_DH.DrillingHead.Additions.GetAddition_ID(ID_DWELL_TIME) Is Nothing Then
		tmp = actt.t_DH.DrillingHead.Additions.GetAddition_ID(ID_DWELL_TIME).Value
		If Val(tmp)>=0 Then
			DWELL_TIME = Abs(Val(tmp)) / 1000
			If DWELL_TIME < 0.01 Then
			  DWELL_TIME = 0.01
	 	  End If			 
		End If
	End If
	
	' Rueckzugsvorschub	
	If Not actt.t_DH.DrillingHead.Additions.GetAddition_ID(ID_MUF) Is Nothing Then
		tmp = actt.t_DH.DrillingHead.Additions.GetAddition_ID(ID_MUF).Value
		If Val(tmp)>=0 Then
			MUF = Val(tmp)
		End If
	End If



	If Not Drill.Edge.Additions.GetAddition_ID(1005) Is Nothing Then
		' ID 1005 -> Verweilzeit neu gefunden 
		ID_MUF = 1004           ' Rueckzugsvorschub
		ID_DWELL_TIME = 1005    ' Verweilzeit
	Else
		' Kompatibilitaetsmodus
		ID_MUF = ID_FF          ' Anfahrvorschub = Rueckzugsvorschub
		ID_DWELL_TIME = 1004    ' Verweilzeit aus ID1004 wie bisher
	End If

	' 2. Fuer jede Schneide kann zusaetzlich eine differierende Einstellung vorgenommen werden

	If Not Drill.Edge.Additions.GetAddition_ID(ID_FF) Is Nothing Then
		tmp = Drill.Edge.Additions.GetAddition_ID(ID_FF).Value
		If Val(tmp)>=0 Then
			FF = Val(tmp)
		End If
	End If
	If Not Drill.Edge.Additions.GetAddition_ID(ID_SIC_G0) Is Nothing Then
		tmp = Drill.Edge.Additions.GetAddition_ID(ID_SIC_G0).Value
		If Val(tmp)>=0 Then
			SIC_G0 = Val(tmp)
		End If
	End If
	If Not Drill.Edge.Additions.GetAddition_ID(ID_DFI_Edge) Is Nothing Then
		tmp = Drill.Edge.Additions.GetAddition_ID(ID_DFI_Edge).Value
		If Val(tmp)>=0 Then
			DFI = -Abs(Val(tmp))
		End If
	End If
	If Not Drill.Edge.Additions.GetAddition_ID(ID_DFS_Edge) Is Nothing Then
		tmp = Drill.Edge.Additions.GetAddition_ID(ID_DFS_Edge).Value
		If Val(tmp)>=0 Then
			DFS = Val(tmp)
		End If
	End If
	If Not Drill.Edge.Additions.GetAddition_ID(ID_DWELL_TIME) Is Nothing Then
		tmp = Drill.Edge.Additions.GetAddition_ID(ID_DWELL_TIME).Value
		If tmp>=0 Then
			DWELL_TIME = Abs(Val(tmp)) / 1000
			If DWELL_TIME < 0.01 Then
			  DWELL_TIME = 0.01
	 	  End If			 
		End If
	End If
	
	If Not Drill.Edge.Additions.GetAddition_ID(ID_MUF) Is Nothing Then
		tmp = Drill.Edge.Additions.GetAddition_ID(ID_MUF).Value
		If Val(tmp)>=0 Then
			MUF = Val(tmp)
		End If
	End If
	
End Function
  
    
