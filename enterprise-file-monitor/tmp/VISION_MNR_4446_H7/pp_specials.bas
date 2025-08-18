' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \hh7\pp_specials.bas
' -- 
' -----------------------------------------
'#uses "pp_global.bas"
'#uses "pp_mt.bas"

Option Explicit


' Variablen der Eingabemaske 
' ---------------------------------------

Global Vakuum_Station1_Ein As Boolean
Global Vakuum_Station2_Ein As Boolean
Global Vakuum_Station3_Ein As Boolean
Global Vakuum_Station4_Ein As Boolean

Global Vakuum_Station1_Aus As Boolean
Global Vakuum_Station2_Aus As Boolean
Global Vakuum_Station3_Aus As Boolean
Global Vakuum_Station4_Aus As Boolean


Global Anschlag1_Runter As Boolean
Global Anschlag2_Runter As Boolean
Global Anschlag3_Runter As Boolean
Global Anschlag4_Runter As Boolean

Global Anschlag1_Hoch As Boolean
Global Anschlag2_Hoch As Boolean
Global Anschlag3_Hoch As Boolean
Global Anschlag4_Hoch As Boolean

Global Einlegehilfe1_Runter As Boolean
Global Einlegehilfe2_Runter As Boolean

Global Einlegehilfe1_Hoch As Boolean
Global Einlegehilfe2_Hoch As Boolean

Global ProgM30 As Boolean
Global ProgM17 As Boolean

Global parkposition As Boolean
'Global park_right As Boolean



Function All_Agg_UP_AND_Off
	wcnc(SPF_EndProg)
	
End Function


	
Function  DH_UP(agg As Long)
' H0 M27  einzelne Bohrer und Einheit hoch

	wcncaddcom("H0 M88","Bohrkopfspindeln hoch")
	wcncaddcom("H0 M89","Bohrkopfspindeln hoch")

End Function


Function HFunctionForDH(CodeX,CodeY)
Dim Bohrkopf As Integer
' vorsicht bei der Überprüfung muss aktspindelcode immer auf null gesetzt werden wenn 
' Werkzeugwechsel..., be careful
	If (AktSpindelCodeDH_X <> CodeX) Or (AktSpindelCodeDH_Y <> CodeY)  Then
	   ' nur absetzen wenn sich Bohrmuster ändert !!
		AktSpindelCodeDH_X=CodeX
		AktSpindelCodeDH_Y=CodeY
		
		wcnc("M88 H"+Inttos(CodeX))
		wcnc("M89 H"+Inttos(CodeY))
	   	'wcnc("G4F.1")
	   	'wcnc("STOPRE")
	End If    ' AktSpindelCodeDH <> spindelvorlegecode 

End Function



Rem See DialogFunc help topic for more information.
Private Function DialogFunction(DlgItem$, Action%, SuppValue&) As Boolean
	Select Case Action%
	Case 2 ' Value changing or button pressed
		   Rem DialogFunction = True ' Prevent button press from closing the dialog box
			Select Case DlgItem
				Case "wei"
					DialogFunction= (DlgValue("ProgM30")=1) And (DlgValue("ProgM17")=1)
					If DialogFunction Then
					  MsgBox("doppelte Auswahl des Programmendes")
					End If
					DialogFunction= (DlgValue("ProgM30")=0) And (DlgValue("ProgM17")=0)
					If DialogFunction Then
					  MsgBox("kein Programmende ausgewählt")
					End If
					'DialogFunction= (DlgValue("AG1N1")=1) And (DlgValue("AG2N1")=1)
					'If DialogFunction Then
					'  MsgBox("Doppelte Auswahl des Nullpunkts")
					'End If
					'DialogFunction= (DlgValue("AG1N1")=0) And (DlgValue("AG2N1")=0)
					'If DialogFunction Then
					'  MsgBox("keinen Nullpunkt ausgewählt")
					'End If
					'DialogFunction= ((DlgValue("AG1N1")=1) And (DlgValue("AG2N1")=1)) Or ((DlgValue("PGA1")=1) And (DlgValue("PGA2")=1))Or((DlgValue("PGA1")=0) And (DlgValue("PGA2")=0)) Or ((DlgValue("AG1N1")=0) And (DlgValue("AG2N1")=0))
					DialogFunction= ( ((DlgValue("ProgM30")=1) And (DlgValue("ProgM17")=1))Or((DlgValue("ProgM30")=0) And (DlgValue("ProgM17")=0)) )
			End Select
	End Select
End Function

Sub ShowDialog
Dim Listarray(10) As String
Dim wertstr,wertneu As Variant
Dim wert As Double
Dim res As Variant


    Listarray(0)="G54"
    Listarray(1)="G55"
    Listarray(2)="G56"
    Listarray(3)="G57"
    Listarray(4)="G58"
    Listarray(5)="G506"
    Listarray(6)="G507"
    Listarray(7)="G508"
    Listarray(8)="G509"

	Begin Dialog UserDialog 490,413,"(c) direkt cnc-systeme gmbh",.DialogFunction ' %GRID:2,2,1,1
		GroupBox 0,0,230,182,"Programmanfang",.GroupBox2
		CheckBox 20,161,200,14,"Einlegehilfe Gruppe 2 Einf",.Einlegehilfe2_Runter,1
		CheckBox 20,14,200,14,"Vakuum Station 1 gespannt",.Vakuum_Station1_Ein,1
		CheckBox 20,28,200,14,"Vakuum Station 2 gespannt",.Vakuum_Station2_Ein,1
		CheckBox 20,42,200,14,"Vakuum Station 3 gespannt",.Vakuum_Station3_Ein,1
		CheckBox 20,56,200,14,"Vakuum Station 4 gespannt",.Vakuum_Station4_Ein,1
	'	CheckBox 20,98,170,14,"Einlegehilfe1 einfahren",.CBEinlege1ein
		CheckBox 20,77,170,14,"Anschlaggruppe1 Einf",.Anschlag1_Runter,1
		CheckBox 20,91,170,14,"Anschlaggruppe2 Einf",.Anschlag2_Runter,1
		CheckBox 20,105,170,14,"Anschlaggruppe3 Einf",.Anschlag3_Runter,1
		CheckBox 20,119,170,14,"Anschlaggruppe4 Einf",.Anschlag4_Runter,1
		
		CheckBox 20,147,200,14,"Einlegehilfe Gruppe 1 Einf",.Einlegehilfe1_Runter,1
		GroupBox 0,182,230,98,"Nullpunktauswahl",.GroupBox4
		'CheckBox 10,224,200,14,"Nullpunkt G505 Anopti",.AG1N1,1
		'CheckBox 10,203,200,14,"Nullpunkt G57 ",.AG2N1,1
		
		OKButton 200,378,80,21,.wei
		GroupBox 230,0,250,182,"Programmende",.GroupBox1
	'	CheckBox 20,112,170,14,"Einlegehilfe2 einfahren",.CBEinlege2ein
	'	CheckBox 220,98,170,14,"Einlegehilfe1 ausfahren",.CBEinlege1aus
		
		
		CheckBox 250,14,220,14,"Vakuum Station 1 entspannen",.Vakuum_Station1_Aus,1
		CheckBox 250,28,220,14,"Vakuum Station 2 entspannen",.Vakuum_Station2_Aus,1
		CheckBox 250,42,220,14,"Vakuum Station 3 entspannen",.Vakuum_Station3_Aus,1
		CheckBox 250,56,220,14,"Vakuum Station 4 entspannen",.Vakuum_Station4_Aus,1
		
		CheckBox 250,77,170,14,"Anschlaggruppe1 Ausf",.Anschlag1_Hoch,1
		CheckBox 250,91,170,14,"Anschlaggruppe2 Ausf",.Anschlag2_Hoch,1
		CheckBox 250,105,170,14,"Anschlaggruppe3 Ausf",.Anschlag3_Hoch,1
		CheckBox 250,120,170,14,"Anschlaggruppe4 Ausf",.Anschlag4_Hoch,1
		
		CheckBox 250,147,200,14,"Einlegehilfe Gruppe 1 Ausf",.Einlegehilfe1_Hoch,1
		CheckBox 250,161,200,14,"Einlegehilfe Gruppe 2 Ausf",.Einlegehilfe2_Hoch,1
		GroupBox 230,182,250,98,"Programmart",.GroupBox5
		CheckBox 240,200,190,14,"Einzelprogramm (M30)",.ProgM30,1
		CheckBox 240,218,190,14,"Wechsel Programm (M17)",.ProgM17,1
		DropListBox 10,196,120,77,Listarray(),.DropListBox1
		GroupBox 0,280,480,91,"Bahnverhalten",.GroupBox3
		OptionGroup .Group1
			OptionButton 200,301,160,14,"Ecken eckig (G451)",.Bahnverhalten2
			OptionButton 20,301,140,14,"CPRECON (G64)",.Bahnverhalten
		Text 20,326,120,14,"$SC_MINFEED",.Text1
		Text 20,348,120,14,"$SC_CONTPREC",.Text2
		TextBox 150,322,90,21,.sc_minfeed
		TextBox 150,346,90,20,.sc_contprec
		Text 250,238,218,28,"Achtung bei M17 keine Nullpunkts anwahl im NC-Programm",.Text3
		OptionGroup .parkposition
			OptionButton 16,226,138,14,"parken links",.OptionButton1
			OptionButton 16,250,138,14,"parken rechts",.OptionButton2
	'	CheckBox 20,126,170,14,"Einlegehilfe3 einfahren",.CBEinlege3ein
	'	CheckBox 220,126,170,14,"Einlegehilfe3 ausfahren",.CBEinlege3aus
	'	CheckBox 220,112,170,14,"Einlegehilfe2 ausfahren",.CBEinlege2aus
	    '	DropListBox 198,-2,0,0,ListArray(),.DropListBox1
	End Dialog
	
	
	Dim dlg As UserDialog
	
	Read_UserDlg_Adjusts
	
	
    'Vakuum Station 1-4 gespannt
    dlg.Vakuum_Station1_Ein=IIf(Vakuum_Station1_Ein,1,0)
    dlg.Vakuum_Station2_Ein=IIf(Vakuum_Station2_Ein,1,0)
	dlg.Vakuum_Station3_Ein=IIf(Vakuum_Station3_Ein,1,0)
  	dlg.Vakuum_Station4_Ein=IIf(Vakuum_Station4_Ein,1,0)
  	'Anschlag Gruppe 1-4 Einf
  	dlg.Anschlag1_Runter=IIf(Anschlag1_Runter,1,0)
    dlg.Anschlag2_Runter=IIf(Anschlag2_Runter,1,0)
    dlg.Anschlag3_Runter=IIf(Anschlag3_Runter,1,0)
    dlg.Anschlag4_Runter=IIf(Anschlag4_Runter,1,0)
    'Einlegehilfe Gruppe 1-2
    dlg.Einlegehilfe1_Runter=IIf(Einlegehilfe1_Runter,1,0)
    dlg.Einlegehilfe2_Runter=IIf(Einlegehilfe2_Runter,1,0)
    'Vakuum Station 1-4 entspannen
    dlg.Vakuum_Station1_Aus=IIf(Vakuum_Station1_Aus,1,0)
    dlg.Vakuum_Station2_Aus=IIf(Vakuum_Station2_Aus,1,0)
    dlg.Vakuum_Station3_Aus=IIf(Vakuum_Station3_Aus,1,0)
    dlg.Vakuum_Station4_Aus=IIf(Vakuum_Station4_Aus,1,0)
    'Anschlag Gruppe 1-4 Ausf
    dlg.Anschlag1_Hoch=IIf(Anschlag1_Hoch,1,0)
    dlg.Anschlag2_Hoch=IIf(Anschlag2_Hoch,1,0)
    dlg.Anschlag3_Hoch=IIf(Anschlag3_Hoch,1,0)
    dlg.Anschlag4_Hoch=IIf(Anschlag4_Hoch,1,0)
    'Einlegehilfe Gruppe 1-2
    dlg.Einlegehilfe1_Hoch=IIf(Einlegehilfe1_Hoch,1,0)
    dlg.Einlegehilfe1_Hoch=IIf(Einlegehilfe1_Hoch,1,0)
    'Nullpunkte
    'dlg.DropListBox1= NullpunktNummer
    'Programmart
	dlg.ProgM30=IIf(ProgM30,1,0)
	dlg.ProgM17=IIf(ProgM17,1,0)
	
	dlg.sc_minfeed=IntToS(sc_minfeed)
	dlg.sc_contprec=IntToS(sc_contprec)

	dlg.DropListBox1=NullpunktNummer
	dlg.group1=Bahnverhalten
	
	dlg.parkposition=IIf(parkposition=0,1,0)
'	dlg.park_right=IIf(parkposition=1,1,0)


	'Dialog dlg
	res=Dialog(dlg,-1)
	Select Case res
	    Case -1
	       'OK-Button     
			Bahnverhalten=dlg.group1

		    'Nullpunkte
			NullpunktNummer=dlg.DropListBox1
		    Nullpunkt= Listarray(NullpunktNummer)

			
		    'Vakuum Station 1-4 gespannt
		    Vakuum_Station1_Ein=(dlg.Vakuum_Station1_Ein=1)
		    Vakuum_Station2_Ein=(dlg.Vakuum_Station2_Ein=1)
			Vakuum_Station3_Ein=(dlg.Vakuum_Station3_Ein=1)
		  	Vakuum_Station4_Ein=(dlg.Vakuum_Station4_Ein=1)
		  	'Anschlag Gruppe 1-4 Einf
		  	Anschlag1_Runter=(dlg.Anschlag1_Runter=1)
		    Anschlag2_Runter=(dlg.Anschlag2_Runter=1)
		    Anschlag3_Runter=(dlg.Anschlag3_Runter=1)
		    Anschlag4_Runter=(dlg.Anschlag4_Runter=1)
		    'Einlegehilfe Gruppe 1-2
		    Einlegehilfe1_Runter=(dlg.Einlegehilfe1_Runter=1)
		    Einlegehilfe2_Runter=(dlg.Einlegehilfe2_Runter=1)
		    'Vakuum Station 1-4 entspannen
		    Vakuum_Station1_Aus=(dlg.Vakuum_Station1_Aus=1)
		    Vakuum_Station2_Aus=(dlg.Vakuum_Station2_Aus=1)
		    Vakuum_Station3_Aus=(dlg.Vakuum_Station3_Aus=1)
		    Vakuum_Station4_Aus=(dlg.Vakuum_Station4_Aus=1)
		    'Anschlag Gruppe 1-4 Ausf
		    Anschlag1_Hoch=(dlg.Anschlag1_Hoch=1)
		    Anschlag2_Hoch=(dlg.Anschlag2_Hoch=1)
		    Anschlag3_Hoch=(dlg.Anschlag3_Hoch=1)
		    Anschlag4_Hoch=(dlg.Anschlag4_Hoch=1)
		    'Einlegehilfe Gruppe 1-2
		    Einlegehilfe1_Hoch=(dlg.Einlegehilfe1_Hoch=1)
		    Einlegehilfe1_Hoch=(dlg.Einlegehilfe1_Hoch=1)  
		    'Programmart
			ProgM30=(dlg.ProgM30=1)
			ProgM17=(dlg.ProgM17=1)
		    ' Einlegehilfen
		    
		    sc_minfeed=StrToFloat(dlg.sc_minfeed)
			sc_contprec=StrToFloat(dlg.sc_contprec)

		    'Programmart
			parkposition=(dlg.parkposition=0)
			'parkposition=(dlg.park_right=1)

	       
	       	Write_UserDlg_Adjusts


    End Select

End Sub

'write Vacuumcircle turn on
Sub Vakuum_Ueberwachung_Ein
	
    If Vakuum_Station1_Ein Then
	  wcnc("M56   ; Station 1 gespannt")
	  wcnc("R60=1")
  	End If 
    If Vakuum_Station2_Ein Then
	  wcnc("M58   ; Station 2 gespannt")
	  wcnc("R61=1")
  	End If 
    If Vakuum_Station3_Ein Then
	  'wcnc("M53   ; Station 3 gespannt")
	  'wcnc("R62=1")
  	End If 
    If Vakuum_Station4_Ein Then
	  'wcnc("M54   ; Station 4 gespannt")
	  'wcnc("R63=1")
  	End If 
End Sub


'write Vacuumcircle turn off
Sub Vakuum_Ueberwachung_Aus
    If Vakuum_Station1_Aus Then
	  wcnc("M57   ; Station 1 entspannt")
  	End If 
    If Vakuum_Station2_Aus Then
	  wcnc("M59   ; Station 2 entspannt")
  	End If 
    If Vakuum_Station3_Aus Then
	  'wcnc("M43   ; Station 3 entspannt")
  	End If 
    If Vakuum_Station4_Aus Then
	  'wcnc("M44   ; Station 4 entspannt")
  	End If 
End Sub

Sub Anschlaege_Runter
    If Anschlag1_Runter Then
	  wcnc("M74   ; Anschlag  1 einfahren")
  	End If 
    If Anschlag2_Runter Then
	  wcnc("M76   ; Anschlag  2 einfahren")
	  End If
	If Anschlag3_Runter Then
	  'wcnc("H39   ; Anschlag  3 einfahren")
  	End If
  	If Anschlag4_Runter Then
	  'wcnc("H41   ; Anschlag  4 einfahren")
  	End If
End Sub


Sub Anschlaege_Hoch
    If Anschlag1_Hoch Then
	  wcnc("M73   ; Anschlag  1 ausfahren")
  	End If 
    If Anschlag2_Hoch Then
	  wcnc("M75   ; Anschlag  2 ausfahren")
  	End If
  	If Anschlag3_Hoch Then
	  'wcnc("H38   ; Anschlag  3 ausfahren")
  	End If
  	If Anschlag4_Hoch Then
	  'wcnc("H40   ; Anschlag  4 ausfahren")
  	End If
End Sub

Sub wcnc_EinlegeHilfen_Runter

    If Einlegehilfe1_Runter Then
	  wcnc("M72  ; Einlegehilfen 1 einfahren")
  	End If 
    If Einlegehilfe2_Runter Then
	  'wcnc("H63  ; Einlegehilfen 2 einfahren")
  	End If 
    
End Sub

Sub wcnc_EinlegeHilfen_Hoch
    If Einlegehilfe1_Hoch Then
	  wcnc("M71  ; Einlegehilfen 1 ausfahren")
  	End If
  	If Einlegehilfe1_Hoch Then
	  'wcnc("H62  ; Einlegehilfen 2 ausfahren")
  	End If
     
End Sub


Function Read_UserDlg_Adjusts
Dim wertstr As Variant
Dim wertneu As Variant


NullpunktNummer=ReadIntPP_ini("USERDLG","Nullpunkt",0)
Bahnverhalten=ReadIntPP_ini("USERDLG","Bahnverhalten",1)

Vakuum_Station1_Ein=ReadIntPP_ini("USERDLG","Vacuum1_ON",0)
Vakuum_Station2_Ein=ReadIntPP_ini("USERDLG","Vacuum2_ON",0)
Vakuum_Station3_Ein=ReadIntPP_ini("USERDLG","Vacuum3_ON",0)
Vakuum_Station4_Ein=ReadIntPP_ini("USERDLG","Vacuum4_ON",0)

Vakuum_Station1_Aus=ReadIntPP_ini("USERDLG","Vacuum1_OFF",0)
Vakuum_Station2_Aus=ReadIntPP_ini("USERDLG","Vacuum2_OFF",0)
Vakuum_Station3_Aus=ReadIntPP_ini("USERDLG","Vacuum3_OFF",0)
Vakuum_Station4_Aus=ReadIntPP_ini("USERDLG","Vacuum4_OFF",0)


Anschlag1_Runter=ReadIntPP_ini("USERDLG","Ans1_Down",0)
Anschlag2_Runter=ReadIntPP_ini("USERDLG","Ans2_Down",0)
Anschlag3_Runter=ReadIntPP_ini("USERDLG","Ans3_Down",0)
Anschlag4_Runter=ReadIntPP_ini("USERDLG","Ans4_Down",0)

Anschlag1_Hoch=ReadIntPP_ini("USERDLG","Ans1_Up",0)
Anschlag2_Hoch=ReadIntPP_ini("USERDLG","Ans2_Up",0)
Anschlag3_Hoch=ReadIntPP_ini("USERDLG","Ans3_Up",0)
Anschlag4_Hoch=ReadIntPP_ini("USERDLG","Ans4_Up",0)
  

Einlegehilfe1_Runter=ReadIntPP_ini("USERDLG","Einlege1_Down",0)
Einlegehilfe2_Runter=ReadIntPP_ini("USERDLG","Einlege2_Down",0)
Einlegehilfe1_Hoch=ReadIntPP_ini("USERDLG","Einlege1_Up",0)
Einlegehilfe2_Hoch=ReadIntPP_ini("USERDLG","Einlege2_Up",0)

ProgM30=ReadIntPP_ini("USERDLG","M30",1)
ProgM17=ReadIntPP_ini("USERDLG","M17",0)

wertstr="2000"
ReadStrPP_ini("FAHRVERHALTEN","SC_MINFEED",wertstr,wertneu)
If wertneu<=0 Then
	wertneu=StrToFloat(wertstr)
End If
sc_minfeed=StrToFloat(wertneu)

wertstr="0.05"
ReadStrPP_ini("FAHRVERHALTEN","SC_CONTPREC",wertstr,wertneu)
If wertneu<=0 Then
	wertneu=StrToFloat(wertstr)
End If
sc_contprec = StrToFloat(wertneu)

parkposition=ReadIntPP_ini("USERDLG","ParkPosition",1)


End Function


Function Write_UserDlg_Adjusts
Dim wertstr As Variant
Dim wertneu As Variant

WriteIntPP_ini("USERDLG","Nullpunkt",NullpunktNummer)

WriteIntPP_ini("USERDLG","Bahnverhalten",Bahnverhalten)


WriteBoolPP_ini("USERDLG","Vacuum1_ON",Vakuum_Station1_Ein)
WriteBoolPP_ini("USERDLG","Vacuum2_ON",Vakuum_Station2_Ein)
WriteBoolPP_ini("USERDLG","Vacuum3_ON",Vakuum_Station3_Ein)
WriteBoolPP_ini("USERDLG","Vacuum4_ON",Vakuum_Station4_Ein)

WriteBoolPP_ini("USERDLG","Vacuum1_OFF",Vakuum_Station1_Aus)
WriteBoolPP_ini("USERDLG","Vacuum2_OFF",Vakuum_Station2_Aus)
WriteBoolPP_ini("USERDLG","Vacuum3_OFF",Vakuum_Station3_Aus)
WriteBoolPP_ini("USERDLG","Vacuum4_OFF",Vakuum_Station4_Aus)

WriteBoolPP_ini("USERDLG","Ans1_Down",Anschlag1_Runter)
WriteBoolPP_ini("USERDLG","Ans2_Down",Anschlag2_Runter)
WriteBoolPP_ini("USERDLG","Ans3_Down",Anschlag3_Runter)
WriteBoolPP_ini("USERDLG","Ans4_Down",Anschlag4_Runter)

WriteBoolPP_ini("USERDLG","Ans1_Up",Anschlag1_Hoch)
WriteBoolPP_ini("USERDLG","Ans2_Up",Anschlag2_Hoch)
WriteBoolPP_ini("USERDLG","Ans3_Up",Anschlag3_Hoch)
WriteBoolPP_ini("USERDLG","Ans4_Up",Anschlag4_Hoch)
  

WriteBoolPP_ini("USERDLG","Einlege1_Down",Einlegehilfe1_Runter)
WriteBoolPP_ini("USERDLG","Einlege2_Down",Einlegehilfe2_Runter)
WriteBoolPP_ini("USERDLG","Einlege1_Up",Einlegehilfe1_Hoch)
WriteBoolPP_ini("USERDLG","Einlege2_Up",Einlegehilfe2_Hoch)

WriteBoolPP_ini("USERDLG","M30",ProgM30)
WriteBoolPP_ini("USERDLG","M17",ProgM17)

wertstr=sc_minfeed
WriteStrPP_ini("FAHRVERHALTEN","SC_MINFEED",wertstr)

wertstr=sc_contprec
WriteStrPP_ini("FAHRVERHALTEN","SC_CONTPREC",wertstr)

WriteBoolPP_ini("USERDLG","ParkPosition",parkposition)
	
End Function

