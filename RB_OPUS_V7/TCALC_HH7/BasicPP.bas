'#uses "D:\Campus\System\Posts\TCALC_HH7\TCALC_HH7.bas"

'PPEngine: 08.07.2025 11:32:56
Sub Main
    INITZero
    Park 0
    WorkPieceListInit 1
    WorkPieceInfo "CM",188.5,132.7,0,"Y:\OPUS\PROGRAMMAS\PROJECTWERK\BULO\STKN_Typetekeningen\STKN 1_K_ZPX_L.HOP",0,0,12.7,633,425,18
    ToolListInit 1
    HeadInfo "51"
    Tool 501,"DH 7845_R (_sx_0_0)","",399,-1,-1,51,4000,2000,5000,0,0,0,5,7,0,0,0,-144.57,-459.65,0,0,0
    Init "D:\Programs\BZManual\NcPrg\"
    SetDrillingZMax -5,-10,-15,-20,-25,-30,-35,-40,-45
    HeadInfo "51"
    FirstTool 501,"DH 7845_R (_sx_0_0)","",399,-1,-1,51,4000,2000,5000,0,0,0,5,7,0,0,0,-144.57,-459.65,0,0,0,142.5,64,25,0,0,1
    NC_Start "field2","","7532DR_106",633,425,18,"",188.5,132.7,12.7
    WorkPieceIndex 0
    ViewInfoToolChange 0,0,0,0,18,0,0,142.5,64,25,1,0,0,0,1,0,0,0,1,"","","","","","","","","",""
    HeadInfo "51"
    ToolChange 501,"DH 7845_R (_sx_0_0)","",399,-1,-1,51,4000,2000,5000,0,0,0,5,7,0,0,0,-144.57,-459.65,0,0,0,1
    ViewChange 0,0,0,0,18,0,0,142.5,64,25,1,0,0,0,1,0,0,0,1
    Start_Vertical_DrillingHead_Stroke 1,2000,2500,5000,0
    Vertical_DrillingHead_Stroke 1,142.5,64,142.5,96,-13,0,1,10,"0000000000000000000010000000","115","10"
    Vertical_DrillingHead_Stroke 2,142.5,304,142.5,336,-13,0,1,10,"0000000000000000000010000000","115","10"
    Vertical_DrillingHead_Stroke 3,490.5,304,490.5,336,-13,0,1,10,"0000000000000000000010000000","115","10"
    Vertical_DrillingHead_Stroke 4,490.5,64,490.5,96,-13,0,1,10,"0000000000000000000010000000","115","10"
    End_Vertical_DrillingHead_Stroke 1
    NC_End
End Sub
