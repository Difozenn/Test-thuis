' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     pp_laser.bas
' -- 
' -----------------------------------------
'#uses "pp_math.bas"
'#uses "pp_mt.bas"
'#uses "pp_mtf.bas"
'#uses "pp_global.bas"
'#uses "pp_7.bas"

Option Explicit

' -------------------------------------------------------------
' -- Hier Typen fuer Laserpointer
' Traverse

Global Type TTraverse
	field As Integer  ' Feldzugehoerigkeit
	FieldType As Integer ' Feldtype - neu MW 19.09.2005
	X As Double      ' x - Referenzpos
	Y As Double      ' y - Referenzpos
	z As Double      ' ? noch ohne Funktion
	pad_count As Long    ' Anzahl Pads auf der Traverse
End Type

' Sauger
Global Type TPad
    Traverse As Integer  ' Traversenzugehoerigkeit
    TravPad As Long      ' Nummer Pad auf Traverse
	field As Integer  ' Feldzugehoerigkeit
	X As Double      ' x - Referenzpos
	Y As Double      ' y - Referenzpos
	z As Double      ' ? noch ohne Funktion
	used As Boolean     ' benutzt
	PadType As Integer  ' Sauger Type=0  , Hebelspanner Type=1
	X2 As Double        ' 2. Referenzposition fuer Hebelspanner X
	Y2 As Double 		' 2. Referenzposition fuer Hebelspanner Y
End Type

' ein Konturstuetzpunkt
Global Type TCP
	GTyp As Integer  ' G0/G1 G2 G3 = (0/1/2/3)
	X As Double      ' x 
	Y As Double      ' y 
	i As Double      ' Mittelpunkt i
	j As Double      ' Mittelpunkt j
	'r As Double      ' Radius
End Type

' Eine Kontur
Global Type TContour
	Tool As Long      ' Tool ID
	CP_Count As Long  ' Anzahl Stuetzpunkte
	TCPoint() As TCP  ' Konturstuetzpunkt
End Type

' Werkstuecke
Global Type TWP 
	field As Integer  ' Feldzugehoerigkeit
	C_Count As Long   ' KonturCount
	L_Contour() As TContour
End Type

Global Type TFIELD
	FType As Integer
End Type


Global Type TLaserPointer
	'Activ_Field As Integer     ' 1= links 2= rechts 3 = gekoppelt
	'Laser_Activ As Boolean     ' wird gesetzt, wenn Laserpointer activ gedrueckt
	HeadID As Long              ' HeadId des Lasers kommt aus INI-Datei
	Feedrate As Double          ' Vorschub fuer Konturen abfahren 
    CountPointers As Integer     ' Anzahl Laserpointer
    TPLaser1 As Integer 	 ' Toolplace 1. Laser
    TPLaser2 As Integer 	 ' Toolplace 2. Laser
    off_x1 As Double         ' offset X 1. Laserpointer
    off_y1 As Double         ' offset Y 1. Laserpointer
    off_x2 As Double         ' offset X 2. Laserpointer
    off_y2 As Double         ' offset Y 2. Laserpointer
    ShowTraverses As Boolean ' Traversen auch Darstellen ?
    ShowPads As Boolean	     ' Modified  MW 19.04.2007 10:37:47 fuer automatischen Tisch
	TravCount As Long         ' Anzahl Traversen
	pad_count As Long        ' Anzahl Gesamt
	WP_count As Long        ' Anzahl der aufliegenden Werkstuecke
	PathAndFileN As String          ' Pfad wo die HPGL- Datei welche Jobliste erzeugt zu finden ist +Dateiname 
	XMinField1 As Double     ' Feld 1 XMin
	XMaxField1 As Double     ' Feld 1 XMax   
	XMinField2 As Double     ' Feld 2 XMin
	XMaxField2 As Double     ' Feld 2 XMax
	Trav() As TTraverse
	Pad() As TPad             ' getrennt von Traverse, da auch Glatttisch moeglich
	WP() As TWP				  ' Werkstuecke welche die Konturen beinhalten
	activ_LaserNo As Long    ' merker aktiver Laser
	last_x As Double   ' merker fuer letzte angefahrene Position
	last_y As Double   ' merker fuer letzte angefahrene Position
	is_on As Boolean   ' Merker ob bereits eingeschaltet
	Fields() As TField ' Neu MW 19.09.2005 merker fuer Feldtypen
End Type
Global LasPT As TLaserPointer
'Global isLaserpointer As Boolean

'pick the parameter at position 'nr' of the string 'S'
Function GetParamHPGL(s, GTyp,X,Y)
Dim	Count As Integer
Dim n As Integer
Dim p As Integer
Dim SSave As String
	' Version 1 Punkte
	' PA 731.800,0.00;
	SSave=UCase(s)	
	If InStr(SSave,"PA")>0 Then
		GTyp = "1"
		 ' PA entfernen
		 SSave = delete(SSave,1,InStr(s,"PA")+2)
	     p= InStr(SSave,",")
		
		X=RTrim(LTrim(Mid(SSave,1,p-1)))
		Y=RTrim(LTrim(Mid(SSave,p+1,Len(SSave)-p-1)))
	Else
		GTyp = "???"
	End If
End Function


Function LaserInit As Boolean
	
	'LasPT.Laser_Activ = PostSettings.LaserActive
	LasPT.activ_laserno=-1
	LasPT.HeadID = mPara_Add.Laser_HeadID
	If ((TDATA.GetProcessHead_ID(LasPT.HeadID) Is Nothing)) Then
		Exit Function
	Else
		LasPT.Feedrate = 5000   ' vordefinition 5m/min
		If Not TDATA.GetProcessHead_ID(LasPT.HeadID).ToolPlaces Is Nothing Then
		    If Not TDATA.GetProcessHead_ID(LasPT.HeadID).ToolPlaces.GetFirstCuttingEdge Is Nothing Then
				LasPT.Feedrate = TDATA.GetProcessHead_ID(LasPT.HeadID).ToolPlaces.GetFirstCuttingEdge.Feedrate
			End If
		End If
	End If
	LasPT.CountPointers = TDATA.GetProcessHead_ID(LasPT.HeadID).ToolPlaces.Count
	Get_LaserOffset(LasPT.off_x1,LasPT.off_y1,LasPT.off_x2,LasPT.off_y2)  ' result = Anzahl Laser
	
	If LasPT.CountPointers<1 Then
		LaserInit=False
	Else
		LaserInit=True
	End If
	
	If LasPT.CountPointers>1 Then
		LasPT.TPLaser1=TDATA.GetProcessHead_ID(LasPT.HeadID).ToolPlaces.GetToolPlace_Index(0).PlaceID
		LasPT.TPLaser2=TDATA.GetProcessHead_ID(LasPT.HeadID).ToolPlaces.GetToolPlace_Index(1).PlaceID
	ElseIf LasPT.CountPointers>0 Then
		LasPT.TPLaser1=TDATA.GetProcessHead_ID(LasPT.HeadID).ToolPlaces.GetToolPlace_Index(0).PlaceID
	End If
	
	' x1 ist immer der kleinere Wert
	LasPT.ShowTraverses= mPara_Add.ShowTravLPointer
	LasPT.ShowPads= mPara_Add.ShowPadsLPointer
	'LasPT.Activ_Field = MCDATA.ActiveFields

	LasPT.PathAndFileN = PostSettings.LaserFilename   '"\LaserFile.hpgl"
	
	If MCDATA.FieldsCount>1 Then
		LasPT.XMinField1 = MCDATA.GetField_Index(0).Minx
		LasPT.XMaxField1 = MCDATA.GetField_Index(0).Maxx
		LasPT.XMinField2 = MCDATA.GetField_Index(1).Minx
		LasPT.XMaxField2 = MCDATA.GetField_Index(1).Maxx
	ElseIf MCDATA.FieldsCount=1 Then
		LasPT.XMinField1 = MCDATA.GetField_Index(0).Minx
		LasPT.XMaxField1 = MCDATA.GetField_Index(0).Maxx
	Else
		pp_err(300)
	End If
	
	If Not Read_TravAndPadData Then
		LaserInit = False
	End If
	
	

End Function


Function Read_TravAndPadData As Boolean
Dim s As String
Dim Trav_No,Pad_No As Long
Dim act_wp As Long
Dim act_contour_point,act_contour , act_tool As Long
Dim GTyp,X,Y As String
   Pad_No = 0
   Read_TravAndPadData = True
   If Not FileExist(LasPT.PathAndFileN) Then
   		AddHint("File:" + LasPT.PathAndFileN+ ".. does not exist")
      Read_TravAndPadData = False
      Exit Function
   End If
   Open LasPT.PathAndFileN For Input As #1
    While Not EOF(1)
        Line Input #1,s$
        If UCase(Mid(s,1,2)) = "CO" Then
        	If InStr(s,"CO TRAVERSECOUNT[")>0 Then
        		' Traversencount gefunden
				LasPT.TravCount = Val(GetValB(s,"TRAVERSECOUNT"))
				ReDim LasPT.trav(LasPT.travcount)
		    End If
        	If InStr(s,"CO TRAVERSE[")>0 Then
        		' Traverse gefunden
        		Trav_No = Val(GetValB(s,"TRAVERSE"))
				LasPT.Trav(Trav_No).Field=Val(GetValB(s,"FIELD"))
				LasPT.Trav(Trav_No).Pad_Count=Val(GetValB(s,"PADCOUNT"))
				
				' Neu MW 19.09.2005 - Feldtype
				LasPT.Trav(Trav_No).FieldType = LasPT.Fields(LasPT.trav(Trav_No).Field).Ftype
				
				If LasPT.trav(Trav_No).FieldType=0 Then
					' Neu MW 19.09.2005 - ueberpruefung, ob es sich um einen
					' Traversentisch - handelt - nur dann koennen in den Plot X/Y- Werten vernuenftige
					' Werte stehen
					LasPT.Trav(Trav_No).X=StrToFloat(GetValB(s,"PLOTX"))
					LasPT.Trav(Trav_No).Y=StrToFloat(GetValB(s,"PLOTY"))
				End If
		    End If
        	If InStr(s,"CO PAD[")>0 Then
        		' Sauger gefunden
        		Pad_No= Pad_No + 1
        		LasPT.pad_count=Pad_No
        		ReDim Preserve LasPT.pad(Pad_No) 
        		
        		LasPT.pad(Pad_No).Traverse = Val(GetValB(s,"TRAVERSE"))
        		LasPT.pad(Pad_No).TravPad = Val(GetValB(s,"PAD"))   ' PadNo auf Trav
        		' Keine Feldinformation beim Sauger
        		LasPT.pad(Pad_No).Field = LasPT.Trav(Trav_No).Field  'Val(GetValB(s,"FIELD"))
        		LasPT.pad(Pad_No).X = StrToFloat(GetValB(s,"X"))
        		LasPT.pad(Pad_No).Y = StrToFloat(GetValB(s,"Y"))
        		LasPT.pad(Pad_No).Z = StrToFloat(GetValB(s,"Z"))
        		
        		LasPT.pad(Pad_No).Used = IIf(GetValB(s,"USED")="YES",True,False)
        		
        		' Neu MW 13.09.2005
        		' Saugertyp
        		' 2. Referenzposition fuer drehbare Spanner
        		LasPT.pad(Pad_No).PadType = StrToFloat(GetValB(s,"TYPE"))
        		LasPT.pad(Pad_No).x2 = StrToFloat(GetValB(s,"PLOTX2"))
        		LasPT.pad(Pad_No).y2 = StrToFloat(GetValB(s,"PLOTY2"))
        		
        		
		    End If
        	If InStr(s,"CO WORKPIECECOUNT[")>0 Then
        		' Info fuer Anzahl Werkstuecke gefunden
        		LasPT.wp_count = Val(GetValB(s,"WORKPIECECOUNT"))
        		ReDim LasPT.wp(LasPT.wp_count)
		    End If
        	If InStr(s,"CO WORKPIECE[")>0 Then
        		' Info fuer Anzahl Werkstuecke gefunden
        		act_wp = Val(GetValB(s,"WORKPIECE"))
        		LasPT.wp(act_wp).Field = Val(GetValB(s,"FIELD"))
        		LasPT.wp(act_wp).c_count = Val(GetValB(s,"CONTOURCOUNT")) +1' +1 da Werkstueck auch Kontur
        		ReDim LasPT.wp(act_wp).L_Contour(LasPT.wp(act_wp).c_count) ' Array fuer Anzahl Konturen bereitstellen
				act_contour_point=0
        		act_contour = 1
		    End If
        	If InStr(s,"CO CONTOUR[")>0 Then
        		' Kontur
				act_contour_point=0
        		act_contour = Val(GetValB(s,"CONTOUR")) + 1  ' +1, da Werkstueck auch Kontur
        		act_tool = Val(GetValB(s,"TOOLID"))
        		LasPT.wp(act_wp).L_Contour(act_contour).Tool = act_tool
        	End If
        	'If (InStr(s,"CO (ARC")>0) Then
        	' Neu MW 16.09.2005
        	If (InStr(s,"CO (ARC")>0) And (act_wp>0) Then
        		' Kontur - Bogen
			    act_contour_point=act_contour_point+1
		        LasPT.wp(act_wp).L_Contour(act_contour).CP_Count=act_contour_point
	       		ReDim Preserve LasPT.wp(act_wp).L_Contour(act_contour).TCPoint(act_contour_point)
	       		If (Val(GetValB(s,"DR")))<0 Then 
	       			LasPT.wp(act_wp).L_Contour(act_contour).TCPoint(act_contour_point).gtyp=2
	       		Else
	       			LasPT.wp(act_wp).L_Contour(act_contour).TCPoint(act_contour_point).gtyp=3
	       		End If
	       		LasPT.wp(act_wp).L_Contour(act_contour).TCPoint(act_contour_point).X=StrToFloat(GetValB(s,"EPX"))
	       		LasPT.wp(act_wp).L_Contour(act_contour).TCPoint(act_contour_point).Y=StrToFloat(GetValB(s,"EPY"))
	       		LasPT.wp(act_wp).L_Contour(act_contour).TCPoint(act_contour_point).I=(StrToFloat(GetValB(s,"MPX"))) -(StrToFloat ( GetValB(s,"SPX") ) )
	       		LasPT.wp(act_wp).L_Contour(act_contour).TCPoint(act_contour_point).J=(StrToFloat(GetValB(s,"MPY"))) -(StrToFloat ( GetValB(s,"SPY") ) )
        		
        	End If
        	If InStr(s,"CO FIELDCOUNT[")>0 Then
        		' Feldtypen
        		ReDim LasPT.Fields(Val(GetValB(s,"FIELDCOUNT")))
        		
        	End If
        	If InStr(s,"CO FIELD[")>0 Then
        		' Feldtypen
	        	 LasPT.Fields(Val(GetValB(s,"FIELD"))).Ftype=Val(GetValB(s,"FIELDTYPE"))
	        End If
        Else
        	' sonstige Konturen in diesem Fall geraden
		    If (InStr(s,"PA")>0) And (act_wp>0) Then
		    	' wenn dies zutrifft werden alle Konturen aufgesammelt
			    GetParamHPGL(s,GTyp,X,Y)
			    act_contour_point=act_contour_point+1
		        LasPT.wp(act_wp).L_Contour(act_contour).CP_Count=act_contour_point
	       		ReDim Preserve LasPT.wp(act_wp).L_Contour(act_contour).TCPoint(act_contour_point)
	       		LasPT.wp(act_wp).L_Contour(act_contour).TCPoint(act_contour_point).gtyp=GTyp
	       		LasPT.wp(act_wp).L_Contour(act_contour).TCPoint(act_contour_point).X=StrToFloat(X)
	       		LasPT.wp(act_wp).L_Contour(act_contour).TCPoint(act_contour_point).Y=StrToFloat(Y)
		    End If
		    
        End If
    Wend
     Close #1
	
End Function


' Get Value between the brackets
Function GetValB(Stri,idstr) As String
Dim pos1 As Integer
Dim i As Long
Dim resstri As String
	idstr=idstr+"["
	resstri=""
	pos1 = InStr(1,Stri,idstr) 
	If pos1>0 Then
		' found = true
		For i= pos1+Len(idstr) To Len(Stri)  
			If Mid(Stri,i,1)="]" Then 
				Exit For
			End If
			resstri= resstri + Mid(Stri,i,1) 
			
		Next

	Else
		pp_err(301)
	End If
	GetValB = resstri
End Function


Function do_LaserPointer
Dim i,j,k As Long
Dim Trav As ttraverse
Dim Pad As tpad
Dim Las_C As TContour    ' eine komplette Laser-Kontur
Dim msg As String
Dim toolno As Long
Dim tooldescription As String
	' Neu MW 27.09.2005
Dim	Laser_WP_or_ToolPath As Boolean
Dim LaserInitOk As Boolean
	LaserInitOk = LaserInit
	Laser_WP_or_ToolPath =False
    If (Not LaserInitOk) And (JobPara.Laser_Activ) Then
    	pp_err(302)
	ElseIf Not LaserInitOk Then
		' Neu MW 07.07.2005
		' dann z.B. hpgl-File nicht vorhanden
		Exit Function
	End If
	
	If JobPara.Activ_Fields=1 Then
		' links Pointern
		WCNC_IDD("IFLASERA")
	ElseIf JobPara.Activ_Fields=2 Then
		' rechts Pointern		
		WCNC_IDD("IFLASERB")
		
	Else
		' links und rechts Pointern
		WCNC_IDD("IFLASERA")
		
	End If
		wcnc_IDD("G500")
	
		wSafetyAbs(False)
		wcncCom(" ------------   LASERPOINTER    -------------")
	
		MT_WRITE_WZW(LasPT.HeadID,"","","",0,-1,"","","","")
		Last_TC_Call_NCStr = ""    ' sonst wird aufruf laser bei Konturen unterdrueckt
		wcncCom("traverses")
		For i = 1 To LasPT.TravCount 
			' 1. Traversen anfahren
			Trav = LasPT.trav(i)			
			If (Trav.Field = (JobPara.Activ_Fields-1)) Or (JobPara.Activ_Fields=3) Then
				' Traverse vom aktiven Feld, oder Felder gekoppelt
			    If LasPT.ShowTraverses Then
			    	
			    	' Neu MW 19.09.2005 - nur fuer Traversentisch Traversen Lasern
			    	If Trav.fieldtype=0 Then
						wcnc_laserpos(0,Trav.X,Trav.Y,Trav.Field,"Traverse "+FToS(i))	
					End If
				End If
				
			    If LasPT.ShowPAds Then
			    	' --
			    	' -- Modified  MW 19.04.2007 10:38:51
			    	' --
					For j = 1 To LasPT.PAd_Count 
						' 1. Sauger anfahren
						Pad = LasPT.pad(j)			
						If ((i)=Pad.Traverse) And ((Pad.Field = (jobpara.Activ_Fields-1) Or (jobpara.Activ_Fields=3))) And (Pad.Used) Then
							' neu MW 13.09.2005
							' -- 2. Referenzposition fuer drehbare Spanner
							If Pad.padtype=1 Then
								' das ist ein Spanner
								wcncCom("clamp center")
								wcnc_laserpos(0,Pad.X,Pad.Y,Pad.Field,"Traverse "+FToS(Pad.Traverse)+" Pad "+FToS(Pad.TravPad)+ " Clamp center")
								If Not equal(Pad.x2,0) Or Not equal(Pad.y2,0) Then
									' 2. Position fuer Drehung einstellen
									wcncCom("clamp refpos")
									wcnc_laserpos(0,Pad.x2,Pad.y2,Pad.Field,"Traverse "+FToS(Pad.Traverse)+" Pad "+FToS(Pad.TravPad)+ " Clamp rotation Pos")
								End If
							Else
								' das muss ein "normaler" Sauger sein
								wcncCom("pads standard")
								' MW 13.09.2005 - Type mit als Meldung anzeigen
								wcnc_laserpos(0,Pad.X,Pad.Y,Pad.Field,"Traverse "+FToS(Pad.Traverse)+" Pad "+FToS(Pad.TravPad)+ " Type:" + ftos(Pad.PadType))
								'wcnc_laserpos(0,Pad.X,Pad.Y,Pad.Field,"Traverse "+FToS(Pad.Traverse)+" Pad "+FToS(Pad.TravPad))
							End If
						End If
					Next
				End If
				
			End If
		Next

		WCNC_IDD("TRANSOFF")

	  
	EndandPark

	wcnc("M30")   ' Ruestvorgang beendet
	
	wcnc_IDD("ENDLASER")

		
	' Werkstueck bzw. Fraes/LaserKonturen darstellen
	If (UBound(LasPT.wp)>0) Then
	If (UBound(LasPT.wp(1).L_Contour)>0) Then		
		' Hier folgen jetzt die Konturen - diese werden wie eine Fraesbahn
		' abgefahren
		For i = 1 To UBound(LasPT.wp) 
			' alle Werkstuecke durchgehen, und auf Aktiv-Field ueberpruefen
			If (LasPT.wp(i).Field = (jobpara.Activ_Fields-1)) Or (jobpara.Activ_Fields=3) Then
				' Nur Werkstuecke vom aktivem Feld werden beruecksichtigt
				For k= 1 To UBound(LasPT.wp(i).L_Contour) 
					' alle Konturen durchgehen
					Las_C = LasPT.wp(i).L_Contour(k)
					If (k=1) And (Las_C.cp_Count>0) Then
						' Werkstueck abfahren
						' Die 1. Kontur ist immer das Werkstueck
						'wcncCom("LASERPOINTER WORKPIECE CONTOUR")
						wcnc_IDD("G500")
						wSafetyAbs(False)
						MT_WRITE_WZW(LasPT.HeadID,"","","",0,-1,"","","","")
						For j = 1 To Las_C.CP_Count 
							If j = 1 Then
								' anfahrt
								' Neu MW 27.09.2005
								Laser_WP_or_ToolPath = True
								msg="LASERPOINTER WORKPIECE -"+inttos(i)+"-"
								'wcnc_laserposContour(Las_C.TCPoint(j).X,Las_C.TCPoint(j).Y,Las_C.TCPoint(j).i,Las_C.TCPoint(j).j,Las_C.TCPoint(j).GTyp,LasPT.wp(i).Field,msg,0)
								wcnc_laserposContour(Las_C.TCPoint(j).X,Las_C.TCPoint(j).Y,Las_C.TCPoint(j).i,Las_C.TCPoint(j).j,0,LasPT.wp(i).Field,msg,0)
							Else
								wcnc_laserposContour(Las_C.TCPoint(j).X,Las_C.TCPoint(j).Y,Las_C.TCPoint(j).i,Las_C.TCPoint(j).j,Las_C.TCPoint(j).Gtyp,LasPT.wp(i).Field,"",1)
							End If
						Next
					ElseIf (k>1) And (Las_C.cp_count>0) Then
						' alle weiteren Konturen
						'wcncCom("LASERPOINTER CONTOUR TOOL #"+ftos(LasPT.wp(i).L_Contour(k).Tool))
						wcnc_IDD("G500")
						wSafetyAbs(False)
						MT_WRITE_WZW(LasPT.HeadID,"","","",0,-1,"","","","")
						For j = 1 To Las_C.CP_Count 
							If j = 1 Then
								' anfahrt
								' Neu MW 27.09.2005
								Laser_WP_or_ToolPath = True
								toolno = LasPT.wp(i).L_Contour(k).Tool
								tooldescription=TDATA.GetTool_ID(toolno).Description
								
								msg="LASERPOINTER WORKPIECE -"+inttos(i)+"- TOOL #"+ftos(toolno)+" "+tooldescription
								'wcnc_laserposContour(Las_C.TCPoint(j).X,Las_C.TCPoint(j).Y,Las_C.TCPoint(j).i,Las_C.TCPoint(j).j,Las_C.TCPoint(j).Gtyp,LasPT.wp(i).Field,msg,0)
								' GTYp = 0
								wcnc_laserposContour(Las_C.TCPoint(j).X,Las_C.TCPoint(j).Y,Las_C.TCPoint(j).i,Las_C.TCPoint(j).j,0,LasPT.wp(i).Field,msg,0)
							Else
								wcnc_laserposContour(Las_C.TCPoint(j).X,Las_C.TCPoint(j).Y,Las_C.TCPoint(j).i,Las_C.TCPoint(j).j,Las_C.TCPoint(j).Gtyp,LasPT.wp(i).Field,"",1)
							End If
						Next
					Else 
						' nothing
					End If
					If LasPT.is_on=True Then
						Laser_OFF
						'If (i = UBound(LasPT.wp)) And (k= UBound(LasPT.wp(i).L_Contour)) Then
						'	' Neu MW 22.09.2005
						'	'
						'	' Stop, wenn Laserkontur (Werkstueck oder Werkzeug) abgefahren worden ist
						'	wcncaddcom("M0","MW 22.09.05")
						'End If
						'wcnc_msgOff
					End If
				Next
			End If   ' in aktivem Feld
		Next
		
		If (Laser_WP_or_ToolPath) Then
			' Stop, wenn Laserkontur (Werkstueck oder Werkzeug) abgefahren worden ist
			wcncaddcom("M0","MW 27.09.05")
			Laser_WP_or_ToolPath = False
			wcnc_msgOff
			WCNC_IDD("TRANSOFF")
			
		End If
		
		
	End If
	End If


End Function

' -------------------------------------------------------------------
' wird fuer das Anfahren einer Traversen oder Sauger - Position 
' benutzt. Anhand der MaxFeld - Info wird automatisch zwischen
' den 2 Lasern umgeschaltet!
' -------------------------------------------------------------------
Function wcnc_laserpos(GTyp,X,Y,field,msg)   ' 

	
	If (X<=LasPT.xmaxfield1) Or (LasPT.CountPointers=1) Then
		' X - Position liegt im Feld 1 also mit Laser 1 abfahren
		' oder nur 1 Laser vorhanden
	    LasPT.activ_LaserNo=1		
		wcnc_LaserOffset
	Else
	    LasPT.activ_LaserNo=2
		wcnc_LaserOffset
	End If
	If equal(GTyp,0) Then
		wcnc(G0+XToS(X)+YToS(Y))
	Else
		wcnc(G1+XToS(X)+YToS(Y)+ " F"+Ftos(LasPT.Feedrate))
	End If
	Laser_ON
	wcnc_msg(msg)
	wcnc("M0")
	wcnc_msgOff
	
	Laser_OFF
	
End Function


' -------------------------------------------------------------------
' Diese Funktion wird fuers Konturen abfahren mit dem 
' Punktlaser benutzt 
' hierbei wird ueberprueft, ob das MaxFeld vom Feld 1 ueberschritten wird
' wenn ja erfolgt automatisch ein Laserwechsel
' -------------------------------------------------------------------
' Mode = 0 -> Anfahrt 1. Punkt
' Mode = 1 -> nur naechsten Punkt anfahren und checken, ob 
'             Pointer gewechselt werden muss
Function wcnc_laserposContour(X,Y,i,j,GTyp,field,msg,mode)   ' 
Dim MidField As Double
Const Tol_Limit = 50
	MidField = (Max(LasPT.xminfield1, LasPT.xminfield2) + Min(LasPT.xmaxfield1, LasPT.xmaxfield2))/2

	' Neu MW 11.08.2005 - Logik wenn 1 Laser!!!!
	If LasPT.CountPointers=2 Then
		' diese Logik gilt nur wenn 2 Laserpointer vorhanden	
		If (mode=1) And ( ((X<=(MidField-Tol_Limit)) And (LasPT.activ_laserno=2)) Or ((X>(MidField+Tol_Limit)) And (LasPT.activ_laserno=1)) ) Then
			' Laserpointer wechsel
			' von (2 auf 1) oder (1 auf 2) 
			' Laserpointer 1 oder 2 muss jetzt auf der Mitte stehen, da hpgl-File auf 
			' Feldgrenze schneidet 
			' also Laser Aus
			Laser_OFF
			' dann Endpunkt mit Laser 1 anfahren
			If (X<=LasPT.xmaxfield1) Then
		    	LasPT.activ_LaserNo=1	
			Else
		    	LasPT.activ_LaserNo=2
			End If
	    	wcnc_LaserOffset
	    	' hinfahren 
			wcnc(G0+XToS(LasPT.last_X)+YToS(LasPT.last_Y))
			' laser einschalten
			Laser_ON
		End If
			
			
		If (X<=LasPT.xmaxfield1) Or (LasPT.CountPointers=1) Then
			' X - Position liegt im Feld 1 also mit Laser 1 abfahren
			' oder nur 1 Laser vorhanden
		    If (mode=0) Then
		    	' Anfahrt 
		    	LasPT.activ_LaserNo=1	
		    	wcnc_LaserOffset
		    End If
		ElseIf (X>LasPT.xmaxfield1) And (LasPT.CountPointers>1) Then
		    If (mode=0) Then
		    	' Anfahrt 
			    LasPT.activ_LaserNo=2
				wcnc_LaserOffset
			End If
		Else 
			pp_err(303)
		End If
    Else
		If (mode=0) Then
	    	' Logik fuer 1 LASERPOINTER
	    	LasPT.activ_LaserNo=1	
		    wcnc_LaserOffset
		End If
	End If
		
	If (GTyp=0) Then
		wcnc(G0+XToS(X)+YToS(Y)+ " F"+Ftos(LasPT.Feedrate))
	ElseIf GTyp=1 Then
		wcnc(G1+XToS(X)+YToS(Y)+ " F"+Ftos(LasPT.Feedrate))
	ElseIf (GTyp=2) Or (GTyp=3) Then
		wcnc("G"+GTyp+XToS(X)+YToS(Y)+itos(i)+jtos(j)+ " F"+Ftos(LasPT.Feedrate))
	End If
	
    If (mode=0) Then
    	' Anfahrt 
    	Laser_ON
    End If
	
	If Len(msg)>1 Then
		wcnc_msg(msg)
	End If
'	wcnc("M0")
'	wcnc_msgOff
	
'	Laser_OFF(LasPT.HeadID,LaserTP)

	LasPT.last_x = X 
	LasPT.last_y = Y
	
End Function

Function Laser_ON
Dim HeadId,Place As Long
	HeadId= LasPT.HeadID
	If LasPT.activ_LaserNo=1 Then
		Place = 1
	ElseIf LasPT.activ_LaserNo=2 Then
		Place = 2
	End If

	Laser_Call(HeadId,Place,1)
	LasPT.is_on=True
End Function

Function Laser_OFF
Dim HeadId,Place As Long
	HeadId = LasPT.HeadID
	If LasPT.activ_LaserNo=1 Then
		Place = 1
	ElseIf LasPT.activ_LaserNo=2 Then
		Place = 2
	End If
	
	If LasPT.is_on=True Then
		' nur aus wenn an ist
		Laser_Call(HeadId,Place,0)
	End If
	LasPT.is_on=False
	
End Function

Function Get_LaserOffset(off_x1,off_y1,off_x2,off_y2) 
Dim x_h,y_h As Double
	
	If TDATA.GetProcessHead_ID(LasPT.HeadID) Is Nothing Then
		AddHint("Laser ? - wrong HeadID ?")
		Exit Function
	End If
	
	If TDATA.GetProcessHead_ID(LasPT.HeadID).ToolPlaces.Count>1 Then
		' 2 Ausgaenge/Laser vorhanden
		' 2 Laser pointer vorhanden
		off_x1 = TDATA.GetProcessHead_ID(LasPT.HeadID).CenterX
		off_y1 = TDATA.GetProcessHead_ID(LasPT.HeadID).CenterY
		off_x1 = off_x1 + TDATA.GetProcessHead_ID(LasPT.HeadID).ToolPlaces.GetToolPlace_Index(0).OffsetX
		off_y1 = off_y1 + TDATA.GetProcessHead_ID(LasPT.HeadID).ToolPlaces.GetToolPlace_Index(0).OffsetY
		
		off_x2 = TDATA.GetProcessHead_ID(LasPT.HeadID).CenterX
		off_y2 = TDATA.GetProcessHead_ID(LasPT.HeadID).CenterY
		off_x2 = off_x2 + TDATA.GetProcessHead_ID(LasPT.HeadID).ToolPlaces.GetToolPlace_Index(1).OffsetX
		off_y2 = off_y2 + TDATA.GetProcessHead_ID(LasPT.HeadID).ToolPlaces.GetToolPlace_Index(1).OffsetY
	ElseIf TDATA.GetProcessHead_ID(LasPT.HeadID).ToolPlaces.Count>0 Then
		' mindestens 1 Ausgang muss angelegt sein
		off_x1 = off_x1 + TDATA.GetProcessHead_ID(LasPT.HeadID).ToolPlaces.GetToolPlace_Index(0).OffsetX
		off_y1 = off_y1 + TDATA.GetProcessHead_ID(LasPT.HeadID).ToolPlaces.GetToolPlace_Index(0).OffsetY
	Else
		' Ausgang nicht vorhanden - falsche Definition 
		'
		pp_err(304)
	End If

	If TDATA.GetProcessHead_ID(LasPT.HeadID).ToolPlaces.Count>1 Then
	End If
	
	If (off_x1 > off_x2) And (LasPT.countpointers=2) Then
		' tausch der Offsets 
		x_h= off_x1
		y_h= off_y1
		off_x1 = off_x2
		off_y1 = off_y2
		off_x2 = x_h
		off_y2 = y_h
		
	End If
	off_x1=-off_x1
	off_y1=-off_y1
	off_x2=-off_x2
	off_y2=-off_y2
	
End Function

Function wcnc_LaserOffset
	If LasPT.activ_Laserno <=1 Then
		wcncaddcom(g_OffPX+"="+FToS(LasPT.off_x1)+ " "+g_OffPY+"="+FToS(LasPT.off_y1),"LASER 1")
	ElseIf LasPT.activ_Laserno=2 Then
		wcncaddcom(g_OffPX+"="+FToS(LasPT.off_x2)+ " "+g_OffPY+"="+FToS(LasPT.off_y2),"LASER 2")
	Else
		pp_err(305)
	End If
	
	WCNC_IDD("TRANSON",0,0,0,g_OffPX,g_OffPY,"0")
	
End Function

Function Laser_Call(Hid,TP,OnOff)
Dim NCStr As String ' String for NC-Prog

	'wcnccom("Hid:"+inttos(Hid)+" HTyp:"+inttos(wn)+" TNo:"+inttos(tn)+" DNo:"+inttos(dn)+" DrehRicht:"+inttos(dr)+" Drehzahl:"+inttos(dz)+")")
	
	WCNC_IDD(SPF_LASERONOFF,Hid,TP,OnOff)
	'NCStr = SPF_LASERONOFF+"("+IntToS(Hid)+","+IntToS(TP)+","+IntToS(OnOff)+")"
	
	If OnOff Then
		wcnccom("LASER ON")
	Else
		wcnccom("LASER OFF")
	End If

	
End Function


Function Laser_HPGL_TimeStampOk As Boolean
Dim result As Boolean
Dim s As String
Dim tstamp As String
Const SStri = "TIMESTAMP" ' Suchwert 
	
	result = False
	If FileExist(PostSettings.LaserFilename) Then
		Open PostSettings.LaserFilename For Input As #1
	    Line Input #1,s$
	    If UCase(Mid(s,1,2)) = "CO" Then
	        If InStr(s,"CO "+ UCase(SStri) +"[")>0 Then
	        	' Timestamp gefunden
				tstamp = GetValB(s,UCase(SStri))
				If tstamp = JobPara.hpgl_timestamp Then
					result = True
				End If
			End If
		End If
		Close #1
	End If
	
	Laser_HPGL_TimeStampOk = result
	
End Function
