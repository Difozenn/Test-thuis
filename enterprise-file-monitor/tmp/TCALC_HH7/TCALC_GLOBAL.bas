' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \TCALC_HH7\TCALC_GLOBAL.BAS
' -- 
' -----------------------------------------

Option Explicit

'***********************************************************************************
'*************************************  Types  *************************************
'***********************************************************************************

Global Const SCRIPTVERSION="V7.0.0.0"   ' -- Zeitkalkulation for Hops7


Type TFinishedPart
   x As Double
   y As Double
   z As Double
End Type
Global FinishedPart As TFinishedPart

' Workpiece - Info
Type TWPI
    SName As String       ' AnschlagName
    Sox As Double         ' Anschlag Offset X  
    Soy As Double         ' Anschlag Offset Y
    Soz As Double         ' Anschlag Offset Z
    WPName As String      ' Werkstück -Name
    WPox As Double        ' Werkstück Offset X
    WPoy As Double        ' Werkstück Offset Y
    WPoz As Double        ' Werkstück Offset Z 
    WPx As Double         ' Werkstück Breite
    WPy As Double         ' Werkstück Länge   
    WPz As Double         ' Werkstück Dicke
End Type
Global WPI() As TWPI


' -------------------------------------------------------------
' -- Hier Type für Bohrkopfdaten 
Global Type tDH
	TName As String         ' Name
	V As Double        ' Vorschub
	VE As Double       ' Eintauchvorschub
	VA As Double       ' Austauchvorschub
	centerx As Double           ' Offset zum Referenzbohrer X 
	centery As Double           ' offset zum Referenzbohrer Y
	centerz As Double           ' offset zum Referenzbohrer Z
End Type


' --
' -------------------------------------------------------

' -------------------------------------------------------------
' -- Hier Type für einen Bohrer vom Bohrkopf
Global Type tDriller
	TName As String         ' Name
	TNo As Long              ' TNummer des Bohrers auf der Steuerung
	V As Double        ' Vorschub
	VE As Double       ' Eintauchvorschub
	VA As Double       ' Austauchvorschub
	Length As Double         ' Bohrer Länge
	E_Len As Double          ' Bohrer Überstand 
	offx As Double           ' Offset zum Referenzbohrer X 
	offy As Double           ' offset zum Referenzbohrer Y
	offz As Double           ' offset zum Referenzbohrer Z
	Edge As IICuttingEdge    ' Schneidendaten des Bohrers
	TP As IIDH_ToolPlace     ' Toolplace Daten des bohrers
	Speed As Double          ' SollDrehzahl Neu MW 09.08.2005
End Type
' -------------------------------------------------------------

Type TBMuster
    BM1 As Double
    BM2 As Double
    BM3 As Double   ' neu 18.3.2005 Spindelcodierung nur noch 16Bit
    GroupCode As Long
End Type


'Process Parameter
Type TProcessPara
   Feedrate As Double
   I_Feedrate As Double
   S_Feedrate As Double
   Speed As Double
   RotA As Double
   TipA As Double
End Type



Type TPos
   x As Double
   y As Double   
   z As Double
End Type
'Last x,y,z position
Global LastPos As TPos


Type TMovePara
  TRC As Long
  Feedrate As Long
End Type
Global MovePara As TMovePara


'View adjustments
Type TView
   View As Long
   LastView As Long
   IPX As Double
   IPY As Double
   IPZ As Double
   RotA As Double
   TipA As Double
   SPVX As Double
   SPVY As Double
   SPVZ As Double
   Vxx As Double
   Vxy As Double
   Vxz As Double
   Vyx As Double
   Vyy As Double
   Vyz As Double
   vzx As Double
   vzy As Double
   vzz As Double
End Type

' -------------------------------------------------------------
' -- Hier Type für Merker
Global Type TMarker
    Last_Liftpos As Integer
    LiftPos_Startup As Integer
    LiftPos_Processing As Integer
    Last_BM As TBMuster
    Last_DH_Process As String       ' marker lastproces DrillingV->DH Vertikal DrillingH->DH horizontal
    last_DH_TLength As Double    ' marker last length of drilling 
    Last_DH_ToNo As Long            ' letzte Bohrspindel T-Nummer
    FirstTime_DH_Drilling As Boolean   ' Merker für Bohrkopf Bohren aktiv
    Viewchangechecked As Boolean    ' spezialmerker zum check ob viewchange bereits durchlaufen
    WP_ActIndex As Long      '  Workpiece - Index - Zähler
    WP_LastIndex As Long      '  Workpiece - Index - Zähler
    Pneumatic_Channel() As Long   ' pneumatik channel - merker, da NCInfo viel zu früh kommt - wird dann erst bei StartMilling aufgerufen
    Programmed_DH_Speed As Double   ' Merker, programmierte Drehzahl Bohrkopf
    Last_ExhaustPos As Integer   ' Merker für Absaugung
	DINISO_PROCESS As Boolean   
	DINISO_MODE As Integer ' Mode für DINISO-Programm
	DINISO_LIFTPOS	As Integer ' Position für Vorlegehub -1 = bevorzugte Stellung
	LastNC As String            ' Merker zuletzt abgesetzter NCCode - Zeile
End Type
Global Marker As TMarker


Global Const Pi = 4*Atn(1)
Global Const Eps6= 1e-5



Global FloatFormat As String
Global MoveTime_Result As Double

Global DZMax01 As Double
Global DZMax02 As Double
Global DZMax03 As Double
Global DZMax04 As Double
Global DZMax05 As Double
Global DZMax06 As Double
Global DZMax07 As Double
Global DZMax08 As Double
Global DZMax09 As Double

'actual view
Global ActV As TView
'last view
Global LastV As TView

Global DH_View0 As TView

Global ProcessPara As TProcessPara

Type TLanguage
	id As Long
	display As Variant	
	Ext As Variant	
	id_default As Long 
	display_default As Variant 
	Ext_Default As Variant
End Type


' Variables from interface "work-center"
Global Type ThopsJobPara
	Activ_Fields As Integer         ' Aktive Felder 1=links 2=rechts 3=gekoppelt
	Laser_Activ As Boolean          ' wird 1 gesetzt wenn Punktlaser aktiviert 
    Position As Integer				' Anschlagposition
    FLAG As Variant					' Flag
    NPX As Double					' Nullpunkt X
    NPY As Double					' Nullpunkt Y
    NPZ As Double					' Nullpunkt Z
    AUFMASSX As Double				' Aufmass X
    AUFMASSY As Double				' Aufmass Y
    Pad_Z As Double					' Saugerhöhe
    Jig_Z As Double					' Schablonenhöhe
    'Sic_Z As Double					' muss von Engine bereits verrechnet worden sein
    									' zusätzlicher Sicherheitsabstand z.B. Spannmittel Überstand übers Werkstück
    MirrorX As Boolean
    MirrorY As Boolean
    Park As Integer					' Parkpos 1 = Links hinten 2=rechts hinten 3=mitte hinten
    ParkX As Double
    Parky As Double
    Language As TLanguage           ' wird aus iiSettings ermittelt
    HopsPath As String 				' wird aus iiSettings ermittelt
    HPGL_TimeStamp As String        ' Neu MW 2.8.2005 für check ob korrekte HPGL-Datei
    Add_ZSic As Double              ' Neu MW 14.09.2005 zusätzliche Z-Sicherheit
End Type
Global JobPara As THopsJobPara



' -------------------------------------------------------------
' -------------------------------------------------------------
' -------------------------------------------------------------
' -------------------------------------------------------------
' -------------------------------------------------------------
' -------------------------------------------------------------


' ch mit anzahl vervielfachen und als string zurückgeben
Function repl(ch,anz) As String
Dim i As Long
Dim result As String


result = ""
For i = 1 To anz
	result = result + ch
Next i
repl = result
	
End Function


Function FToS(W)
  Dim n As Integer
  Dim FToSSave As String
  Dim erg As String
  Dim anz As Long
  
  anz=0
  erg=""
  'FToSSave = Format$(W,FloatFormat)
  erg = Replace$(Format$(W,FloatFormat),",",".")
'  For n=1 To Len(FToSSave) Step 1
'	If Mid(FToSSave,n,1)="," Then
'  	    erg=erg+"."
'  	Else
'       erg=erg+Mid(FToSSave,n,1) 	
'  	End If
'  Next n
	
  ' -- 
  ' Neu 08.11.2004 MW 
  ' -- nachfolgende Nullen z.B. bei 34.100 werden gelöscht = 34.1
  ' -- dadurch bei Dokus etc. kurzere Zeilenlängen und weniger NC-Code
  ' -- 
  ' -- 
  For n=Len(erg) To 1 Step -1
	If (Mid(erg,n,1)=".") Or (Mid(erg,n,1)<>"0") Then
		Exit For
  	Else
       If Mid(erg,n,1)="0" Then
       		anz = anz + 1   ' diese können gelöscht werden
       End If
  	End If
  Next n
  If anz > 0 Then
	  erg = Mid(erg,1,Len(erg)-anz)
  End If
  If erg="" Then
  	'AddHint("schwerwiegender Fehler")
Else
  If Mid(erg,Len(erg),1)="." Then
  	 ' punkt löschen
  	 erg=Mid(erg,1,Len(erg)-1)
  End If

  End If
  FToS=erg
End Function

Function IntToS(W)
  IntToS= Trim(Str(W))
End Function

Function LZWIPU(x1, y1, x2, Y2)  As Double

     LZWIPU = Sqr(((x1-x2)*(x1-x2))+((y1-Y2)*(y1-Y2)))
	
End Function

Function LZWIPU3d(x1, y1, z1, x2, Y2, z2)  As Double

     LZWIPU3d = Sqr(((x1-x2)*(x1-x2))+((y1-Y2)*(y1-Y2))+((z1-z2)*(z1-z2)))
	
End Function

Function MinSek(sek) As String
Dim minuten As Double
Dim sekunden As Double
Dim zentel As Double
    'sek = Round(sek)
    minuten= sek \ 60
'    If minuten>0 Then
	    sekunden = Int(sek) Mod 60
'	Else	
	    'sekunden = Str(sek)
'	End If
    If equal(sekunden,0) Then
        zentel =  ((sek-(minuten*60))*10) 'Mod 1 
    Else
        zentel =  (sek*10) Mod sekunden*10 
    End If
    zentel=Int(zentel)
	'MinSek=	Str(sek \ 60)+" Min."+IntToS(sek Mod 60)+" Sek."
	MinSek=	Str(minuten)+" Min  "+Str(sekunden)+"."+IntToS(zentel)+" Sek"
    
	
End Function

Function MMinM(mm) As String
Dim meter As Double
Dim milimeter As Double
    'sek = Round(sek)
    meter= mm \ 1000

	milimeter = Int(mm) Mod 1000

 
	MMinM=	Str(meter)+" m  "+Str(milimeter)+" mm"
    
	
End Function

Function equal(W1,W2)
  equal= Abs(W1-W2)<0.00001
End Function

Function Get_First_Token(stri As String) As String      ' stri = "109;110;117"  result = "109"
Dim i As Long
Dim erg As String

	erg = ""
	For i = 1 To Len(stri) 
		If (Mid(stri,i,1)=";") Then
			Exit For
		Else
			erg = erg + Mid(stri,i,1)
		End If
	Next i
	Get_First_Token = erg
	
	
End Function

Function GetZMax(DFlag,Depth)
    Select Case DFlag
    Case 0
      GetZMax=Depth    
    Case 1
        GetZMax=DZMax01
    Case 2
        GetZMax=DZMax02
    Case 3
        GetZMax=DZMax03
    Case 4
        GetZMax=DZMax04
    Case 5
        GetZMax=DZMax05
    Case 6
        GetZMax=DZMax06
    Case 7
        GetZMax=DZMax07
    Case 8
        GetZMax=DZMax08
    Case 9
        GetZMax=DZMax09
    End Select
End Function

Function DX_DY_Null(ax,ay,ex,ey) As Boolean
Dim dx,dy As Double
  DX_DY_Null= False
  dx= ex-ax
  dy= ey-ay
  If equal(dx,0) And equal(dy,0) Then
    DX_DY_Null= True
  End If
	
End Function



Function LRadian(spX,spY,spZ,epX,epY,epZ,i,j,DR) As Double
Dim res As Double
Dim wi,R As Double
	R=LZWIPU(spX,spY,i,j)
	'wi = GetWinkelDiffGrad(i,j,spX,spY,epX,epY)
	wi = GetDrehwinkelGrad(spX,spY,epX,epY,i,j,DR)
	
	res= (wi/180*Pi) * R
	LRadian=res
End Function


Function GetWinkelDiffGrad(pmx,pmy,pax,pay,pex,pey) As Double
Dim Wa, we, wdiff As Double

	Wa = GetWinkelGrad(pmx,pmy,pax,pay)
	we = GetWinkelGrad(pmx,pmy,pex,pey)
	If Wa > we Then
		we = we + 360
	End If
	wdiff = we - Wa
	If wdiff >= 360 Then 
	   wdiff = wdiff -360
	End If
	GetWinkelDiffGrad= wdiff

	
End Function

Function GetDrehwinkelGrad(ax,ay,ex,ey,mx,my ,DR) As Double
Dim w As Double
	If DR=2 Then
		w= GetWinkelDiffGrad(mx,my,ex,ey,ax,ay)
	Else
		w= GetWinkelDiffGrad(mx,my,ax,ay,ex,ey)
	End If
    If (equal(w,0) And DX_DY_Null(ax,ay,ex,ey)) Then
	    w= 360
    End If
  GetDrehwinkelGrad= w
	
End Function


Function angle_xachse(vx,vy) As Double
Dim w As Double

    If (Abs(vx) <= Eps6) And (Abs(vy) <= Eps6) Then
       w= 0
    ElseIf Abs(vx) <= Eps6 Then
       If vy > 0 Then
          w = 90
       Else
          w = 270
       End If
    ElseIf  Abs(vy) <= Eps6 Then
        If vx > 0 Then
           w = 0
        Else
           w = 180
        End If
    Else
         w=Abs(Atn(vx/vy))

         If vx > 0 Then
             If (vy > 0)  Then  '{1.Quadrant}
                w = 0.5 * Pi - w
             ElseIf (vy < 0)  Then '{4.Quadrant}
					 w = 1.5*Pi +w
			 End If

          Else
              If (vy < 0)  Then   '{3.Quadrant}
                w = 1.5 * Pi-w
              ElseIf vy > 0  Then '{2.Quadrant}
                w = w + 0.5*Pi
              End If
          End If
          w = w/Pi * 180

    End If

    angle_xachse = w
    
End Function


Function GetWinkelGrad(px,py,pmx,pmy ) As Double
Dim vx,vy As Double
Dim winkel As Double
  vx = pmx - px
  vy = pmy - py
  winkel = angle_xachse(vx,vy)
  GetWinkelGrad = winkel

	
End Function

'Save the View adjustments
Sub ViewSave(View,LastView,IPX,IPY,IPZ,RotA,TipA,SPVX,SPVY,SPVZ,Vxx,Vxy,Vxz,Vyx,Vyy,Vyz,Vzx,Vzy,Vzz)
   ActV.View=View
   ActV.LastView=LastView
   ActV.IPX=IPX
   ActV.IPY=IPY
   ActV.IPZ=IPZ
   ActV.RotA =RotA
   ActV.TipA =TipA
   ActV.SPVX=SPVX
   ActV.SPVY =SPVY
   ActV.SPVZ =SPVZ
   ActV.Vxx=Vxx
   ActV.Vxy=Vxy
   ActV.Vxz=Vxz
   ActV.Vyx=Vyx
   ActV.Vyy=Vyy
   ActV.Vyz=Vyz
   ActV.Vzx=Vzx
   ActV.Vzy=Vzy
   ActV.Vzz=Vzz
   
'   Marker.viewchangechecked = True
   
End Sub


'Set Processparameter
Sub PParaSet(I_Feedrate,Feedrate,S_Feedrate,speed,RotA,TipA)
  ProcessPara.Feedrate=Feedrate
  ProcessPara.I_Feedrate=I_Feedrate
  ProcessPara.S_Feedrate=S_Feedrate
  ProcessPara.Speed=speed
  ProcessPara.RotA=RotA
  ProcessPara.TipA=TipA
End Sub

Sub PosReset
  LastPos.X=-99999
  LastPos.Y=-99999
  LastPos.Z=-99999
End Sub

'Reset the moveparameter to an impossible value
Sub MoveParaReset
  MovePara.TRC=-99999
  MovePara.Feedrate=-99999
End Sub

Function Cosinus (w)
Dim erg As Double
   
   erg=Cos(w*Pi/180)
   Cosinus=erg
	
End Function

Function sinus (w)
Dim erg As Double
   
   erg=Sin(w*Pi/180)
   sinus=erg
	
End Function

Function tangens (w)
Dim erg As Double
   
   erg=Tan(w*Pi/180)
   tangens=erg
	
End Function


' holt Fehlermeldung aus der Datei ppscript_de.ini in Abhängigkeit der gewählten Sprache
Function GetErrMsg(no As Long,stri,mode) As String

Dim iiSet As Object
Dim Language As Object
Dim errstri As Variant
Dim path As String
Dim path_Default As String

	path  = JobPara.hopspath+"language\moduls\ppscript\ppscript"+JobPara.language.Ext+".ini"
	path_Default  = JobPara.hopspath+"language\moduls\ppscript\ppscript"+JobPara.language.Ext_Default+".ini"
  
	Set iiSet = CreateObject("BasicExt5.BasicExtension5")	
	errstri = iiSet.IniFileReadstr(path,"errmsg",IntToS(no),"")
	If errstri="" Then
  		errstri = iiSet.IniFileReadstr(path_Default,"errmsg",IntToS(no),Stri)
	End If 
	If mode=1 Then
		errstri = "PPScript("+IntToS(no)+") - " + errstri
	End If
	GetErrMsg = errstri
   	Set iiSet = Nothing
	
End Function


Function GetAddZSic As Double
	GetAddZSic = JobPara.add_zsic
End Function


'get move string with x,y,z,feedrate,trc parameter
Function Move(ByVal x,ByVal Y,ByVal Z,Feedrate,TRC)
   
   		' dann Zeitberechnung für Bohren
   		If Feedrate<=0 Then
   			Feedrate=TPVars.MAXFEEDRATE_XY
   		End If
   		MoveTime_Result= MoveTime_Result+GetTimePath(LZWIPU3d(TimeC_lpos.X,TimeC_lpos.Y,TimeC_lpos.Z,x,Y,Z),Feedrate)	
   		TimeC_lpos.X=x
   		TimeC_lpos.Y=Y
   		TimeC_lpos.Z=Z
   		Move=""
End Function

Function ReadStrPP_ini(Sec,key,default,resu) As String 
	resu = PostSettings.ReadString(Sec,key,default)
End Function

Function WriteStrPP_ini(Sec,key,striVari)
	PostSettings.WriteString(Sec,key,striVari)	
End Function
