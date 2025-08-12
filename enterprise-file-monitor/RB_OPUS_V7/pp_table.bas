' -----------------------------------------
' -- 
' -- NCHOPS-7 postprocessor
' -- File     \RB_OH_OPUS_V7\pp_table.bas
' -- 
' -----------------------------------------
' -- 
' -- Reichenbacher - ISG / BECKHOFF Postprocessors V7 (mw) --
' -- 
' -----------------------------------------
'#uses "pp_math.bas"
'#uses "pp_global.bas"
'#uses "pp_isg.bas"

Option Explicit

'***********************************************************************************
'*************************************  Types  *************************************
'***********************************************************************************

Type TClamps
	Y As Double
	PadName As String
End Type

Type TTrav 
	X As Double
	Clamps() As TClamps
End Type

Global All_Trav() As TTrav


'VP_CARRIER_NR TRAEGERNUMMER 1-10
'VP_X_POS TRAEGERPOSITION In X - RICHTUNG [MM] [MKS]
'VP_CARRIAGE_1 POSTION GRUNDTRAEGER 1 In Y - RICHTUNG [MM] [MKS]
'VP_CARRIAGE_2 POSTION GRUNDTRAEGER 2 In Y - RICHTUNG [MM] [MKS]
'VP_CARRIAGE_3 POSTION GRUNDTRAEGER 3 In Y - RICHTUNG [MM] [MKS]
'VP_CARRIAGE_4 POSTION GRUNDTRAEGER 4 In Y - RICHTUNG [MM] [MKS]

Function WCNC_Initial_Table_Positions()
Dim MCD As IMachineComponentsData
Dim refX,refY As Double 
Dim Act_Trav,MTrav  As Integer 
Dim Act_Cup,MCup As Integer 
Dim T As IMachineComponent
Dim P As IMachineComponent
Dim VP_CARRIER_NR As Integer
Dim VP_X_POS As Double
Dim VP_CARRIAGE_1 As Double
Dim VP_CARRIAGE_2 As Double
Dim VP_CARRIAGE_3 As Double
Dim VP_CARRIAGE_4 As Double 
Dim i As Integer 


	Set MCD = NCData.NCClampSituations.ClampSituations.GetItem_Index(0).MachineComponentsData
	
	refX = MCDATA.MachineComponents.RulerPosx
	refY = MCDATA.MachineComponents.RulerPosy
	
	wcncCom("",True)
	wcncCom("TABLE POSITIONS",True)
	wcncCom("LINEALPOS X :"+ftos(refX))
	wcncCom("LINEALPOS Y :"+ftos(refY))
	wcncCom("",True)
	
	
	MTrav = 1
	ReDim All_Trav(0)  ' Init Travs
	For Act_Trav = 0 To (MCD.MachineComponents.ComponentList.TraverseCount-1) Step 1
		Set T = MCD.MachineComponents.ComponentList.GetTraverse_Index(Act_Trav)
		
		T.MCList.SortPosY
		
		If T.MoveX Then
			' verschiebbare/fahrbare Traverse
			ReDim Preserve All_Trav(UBound(All_Trav)+1)
			
			All_Trav(MTrav).X = T.PosX + refX 
			
			ReDim All_Trav(MTrav).Clamps(0) ' init Cups dieser Traverse
			
			MCup = 1
			
			For Act_Cup = 0 To T.MCList.ClampCarrierCount-1 Step 1
				' Wagen um 1 erhoehen
				ReDim Preserve All_Trav(MTrav).Clamps(UBound(All_Trav(MTrav).Clamps)+1)			
				Set P = T.MCList.GetClampCarrier_Index(Act_Cup)
				
				If P.MoveY Then
					
					All_Trav(MTrav).Clamps(MCup).Y = P.PosY + refY
					
				End If
				MCup = MCup + 1
				
			Next Act_Cup
			
			MTrav = MTrav + 1  ' verschiebbare relevante Trav

		End If
	Next Act_Trav
	
	For i = 1 To UBound(All_Trav)
		' Alle Traversen ausgeben
		' CH_CARRIER_POS(VP_CARRIER_NR,VP_X_POS,VP_CARRIAGE_1,VP_CARRIAGE_2,VP_CARRIAGE_3,VP_CARRIAGE_4)
		VP_CARRIER_NR = i
		VP_X_POS = All_Trav(i).X
		VP_CARRIAGE_1 = 0		
		VP_CARRIAGE_2 = 0		
		VP_CARRIAGE_3 = 0		
		VP_CARRIAGE_4 = 0		
		If UBound(All_Trav(i).Clamps) > 0 Then
			VP_CARRIAGE_1 = All_Trav(i).Clamps(1).Y
		End If
		If UBound(All_Trav(i).Clamps) > 1 Then
			VP_CARRIAGE_2 = All_Trav(i).Clamps(2).Y
		End If
		If UBound(All_Trav(i).Clamps) > 2 Then
			VP_CARRIAGE_3 = All_Trav(i).Clamps(3).Y
		End If
		If UBound(All_Trav(i).Clamps) > 3 Then
			VP_CARRIAGE_4 = All_Trav(i).Clamps(4).Y
		End If
		
		WCNC_SUB(SUB_CARR_POS,VP_CARRIER_NR,VP_X_POS,VP_CARRIAGE_1,VP_CARRIAGE_2,VP_CARRIAGE_3,VP_CARRIAGE_4)

	Next i
	
	If UBound(All_Trav)>0 Then
		WCNC_SUB(SUB_CARR_START)
	End If
		
	
	Set MCD = Nothing
	Set T = Nothing
	Set P = Nothing

	
End Function

