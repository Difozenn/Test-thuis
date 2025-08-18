' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \hh7\pp_math.bas
' -- 
' -----------------------------------------


Option Explicit

Const Pi = 4*Atn(1)
Const Eps6= 1e-5
Const SepStr=";"


Function equal(W1,W2)
  equal= Abs(W1-W2)<0.00001
End Function

Function equal_t(W1,W2,t)
  equal_t= Abs(W1-W2)<t
End Function



Function Rot_3D(x,y,z , KWgrad,DWgrad As Double)

	
Dim sinKW,sinDW,cosKW,CosDW,x1,y1,z1 As Double

  sinKW= Sin(KWgrad*Pi/180)
  sinDW= Sin(DWgrad*Pi/180)
  cosKW= Cos(KWgrad*Pi/180)
  CosDW= Cos(DWgrad*Pi/180)
  x1= x*CosDW-y*cosKW*sinDW+z*sinDW*sinKW
  y1= x*sinDW+y*CosDW*cosKW-z*CosDW*sinKW
  z1= y*sinKW+z*cosKW
  x= x1
  y= y1
  z= z1
  If equal(x,0) Then x= 0
  If equal(y,0) Then y= 0
  If equal(z,0) Then z= 0
End Function

 

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



Function exponent2(zahl) As Double
Dim i As Integer
Dim erg As Double
    erg = 1
	If zahl = 1 Then
		exponent2=erg
	   	Exit Function
	End If

	For i = 1 To zahl-1 Step 1
		erg = erg * 2
	Next
	exponent2=erg
End Function





Function BinToDouble(binstri As String) As Variant
Dim i As Long
Dim erg As Variant

	erg = 0
	For i = Len(binstri) To 1 Step -1
		If Mid$(binstri,i,1)="1" Then erg=erg+exponent2(Len(binstri)-i+1)
		'Debug.Print erg	
	Next i
	BinToDouble=erg

	
End Function


Function Str_Replace(test,pos,char)
Dim i As Long
Dim erg As String
Dim ss As String

For i = 1 To Len(test)
	
	ss = Mid(test,i,1)
	If i = pos Then
		erg = erg + char
	Else
		erg = erg + ss
	End If
Next

Str_Replace = erg	
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



Function Max(a,e) As Double
	If a> e Then
		Max = a
	Else
		Max = e
	End If
End Function

Function Min(a,e) As Double
	If e < a Then
		Min = e
	Else
		Min = a
	End If
End Function

Function GetDX_DY_DZMitKippW_Laenge( KippW,DrehW,laenge , dx,dy,dz) As Boolean
Dim dl As Double

  XYUeberWinkelGrad_Laenge(KippW-90,laenge,dl,dz)
  dy = 0
  XYUeberWinkelGrad_Laenge(DrehW+90,dl,dx,dy)
	
End Function

Function XYUeberWinkelGrad_Laenge(  wi,laenge , X,Y ) As Boolean
Dim xoff As Double
Dim yoff As Double

  xoff = Cos(wi*Pi/180)*laenge
  yoff = Sin(wi*Pi/180)*laenge
  X=xoff
  Y=yoff
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
	
	res= (wi/180*PI) * R
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


Function GetWinkelGrad(px,py,pmx,pmy ) As Double
Dim vx,vy As Double
Dim winkel As Double
  vx = pmx - px
  vy = pmy - py
  winkel = angle_xachse(vx,vy)
  GetWinkelGrad = winkel

	
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
	MinSek=	Str(minuten)+" min  "+Str(sekunden)+"."+IntToS(zentel)+" sec"
    
	
End Function


' String formaten auf anzahl zeichen
' 
Function StrSize(s,anz,Typ) As String
' Typ = 1 linksbuendig
' Typ = 2 rechtsbuendig
' Typ = 3 mittig

StrSize = s
If Typ = 1 Then
	' linksbuendig
	StrSize = s + repl(" ",anz-Len(s))
End If

If Typ = 2 Then
	' rechtsbuendig
	StrSize =  repl(" ",anz-Len(s)) + s
End If

StrSize = Left(StrSize,anz)
	
End Function

' *****************************************************************************************
' ** Wert mit vorangestellem Vorzeichen (+/) zurueckgeben
' *****************************************************************************************
Function Get_Val_Signed(v) As String
	Get_Val_Signed = IIf((v>0)Or(equal(v,0)),"+"+FToS(v),FToS(v)) 
End Function

' ch mit anzahl vervielfachen und als string zurueckgeben
Function repl(ch,anz) As String
Dim i As Long
Dim result As String


result = ""
For i = 1 To anz
	result = result + ch
Next i
repl = result
	
End Function

'delete from index to index+count all chars
Function delete(S,index,Count)
Dim	ns As String
Dim n As  Integer
Dim indexpluscount As Integer
  ns=""
  indexpluscount=index+Count-1
  For n= 1 To Len(S) Step 1
     If Not ((n>=index) And  (n<=indexpluscount)) Then
       ns=ns+Mid(S,n,1)
     End If
  Next n
  delete=ns
End Function


Function ParamCount_Sep(S,Separator)
Dim	n As Long
Dim Count As Long
 ParamCount_Sep=0
  Count = 0
  S= Trim(S)
  If Len(S) > 0 Then
     For n= 1 To Len(S) Step 1
        If Mid(S,n,1) = Separator Then
           Count = Count + 1
        End If
     Next n
     ParamCount_Sep = Count + 1
  End If
End Function


'count of parameters in the string Trenner SepStr=";" bzw. frei definierbar im Post
Function ParamCount(S)
Dim	n As Integer
Dim Count As Integer
 ParamCount=0
  Count = 0
  S= Trim(S)
  If Len(S) > 0 Then
     For n= 1 To Len(S) Step 1
        If Mid(S,n,1) = SepStr Then
           Count = Count + 1
        End If
     Next n
     ParamCount = Count + 1
  End If
End Function

'pick the parameter at position 'nr' of the string 'S'
Function Param(nr,S)
Dim	Count As Integer
Dim n As Integer
Dim p As Integer
Dim SSave As String
  Count = ParamCount(S)

  If (nr > Count) Or (nr < 1)Then
     Param = ""
     Exit Function
  End If

If Count = 1 Then
     Param = Trim(S)
     Exit Function
  End If

  If nr = 1 Then
     p= InStr(S,SepStr)

     Param = Trim (Mid(S, 1, p-1))

  ElseIf nr < Count Then
     SSave=S 
     For n = 1 To nr-1 Step 1
        SSave=delete(SSave,1,InStr(SSave,SepStr))
     Next n

     p= InStr(SSave,SepStr)
     Param = Trim(Mid (SSave,1, p-1))

  ElseIf nr = Count Then 
     p = InStrRev(S,SepStr)
     Param = Trim(Mid (S, p+1, Len(S)-p))

  End If
End Function

'xyz;zzz;iii -> Result is the Parameter at the Position 'nr'  -> mit uebergabe des Seperators
Function GetParam_Sep(nr,S,Separator) 
Dim	Count As Long
Dim n As Long
Dim p As Long
Dim SSave As String
  Count = ParamCount_Sep(S,Separator)

  If (nr > Count) Or (nr < 1)Then
     GetParam_Sep = ""
     Exit Function
  End If

If Count = 1 Then
     GetParam_Sep = Trim(S)
     Exit Function
  End If

  If nr = 1 Then
     p= InStr(S,Separator)

     GetParam_Sep = Trim (Mid(S, 1, p-1))

  ElseIf nr < Count Then
     SSave=S 
     For n = 1 To nr-1 Step 1
        SSave=delete(SSave,1,InStr(SSave,Separator))
     Next n

     p= InStr(SSave,Separator)
     GetParam_Sep = Trim(Mid (SSave,1, p-1))

  ElseIf nr = Count Then 
     p = InStrRev(S,Separator)
     GetParam_Sep = Trim(Mid (S, p+1, Len(S)-p))

  End If
End Function





Function Dist2P(p1x,p1y,p2x,p2y) As Double

	Dist2P = Sqr(((p2x-p1x)*(p2x-p1x))+((p2y-p1y)*(p2y-p1y)))
	
End Function


Function ExtractFilePath(DatPfad)
Dim i,korrektpos As Integer
Dim ss As String

    For i = Len(DatPfad) To 1 Step-1 
        If Mid(DatPfad,i,1) = "\" Then 
           korrektpos = i
           Exit For
        End If
    Next
    DatPfad = Mid(DatPfad,1,korrektpos)
    ' mit Backslash am Ende
	
End Function

Function ExtractFileName(PfadundDateiName)
Dim i As Integer
Dim ss As String
    ss=""
    For i = Len(PfadundDateiName) To 1 Step-1 
        If Mid(PfadundDateiName,i,1) = "\" Then 
           Exit For
        End If
        ss=ss+Mid(PfadundDateiName,i,1)
    Next
    ' backwards
    PfadundDateiName=""
    For i = Len(ss) To 1 Step-1 
        PfadundDateiName=PfadundDateiName+Mid(ss,i,1)
    Next
	ExtractFileName=PfadundDateiName
End Function


Function WithoutExtension(NCName)
Dim erg As String
	erg= Mid(NCName,1,(InStr(NCName,"."))-1)
    WithoutExtension=erg
End Function


Function Check_Term(term)

Dim ss As String
    term=Replace(term,"(","[")
    term=Replace(term,")","]")
	Check_Term=term
End Function


Function Is_Null(Wert ) As  Boolean

  Is_Null= Abs(Wert)<0.000001

	
End Function

Function Norm0_360(w) As Double
	While w<0 
		w=w+360
	Wend
	While w>=360 
		w=w-360
	Wend
	Norm0_360 = w
End Function

' Schnittpunkt von 2 Geraden im Raum
Function Get_SP2Lines(sx1,sy1,ex1,ey1,sx2,sy2,ex2,ey2,ByRef spx,spy) As Boolean

Dim VX1, VY1, VX2, VY2 As Double
Dim Det As Double
Dim Det1 As Double
Dim Det2 As Double
Dim Detx As Double
Dim Dety As Double
Dim result As Boolean

	VX1 = ex1-sx1
	VY1 = ey1-sy1
	VX2 = ex2-sx2
	VY2 = ey2-sy2
	Det = VX1 * VY2 - VX2 * VY1
	If Abs(Det)<0.0001 Then
		result=False
	Else
		result=False
		Det1 = VX1 * sy1 - VY1 * sx1
		Det2 = VX2 * sy2 - VY2 * sx2
		Detx = -VX1 * Det2 + VX2 * Det1
		Dety = VY2 * Det1 - VY1 * Det2
		spx = Detx/Det
		spy = Dety/Det
	End If
	Get_SP2Lines=result
End Function

