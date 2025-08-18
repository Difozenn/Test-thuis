'#uses "D:\HOPS7\System\Posts\VISION_MNR_4446_H7\pp.bas"

'PPEngine: 13.10.2022 7:29:21
Sub Main
    INITZero
    Park 0
    WorkPieceListInit 1
    WorkPieceInfo "LV",-0.1,0.34,0,"Y:\Reichenbacher2\Korpus\0627_BB0275_DCM\BK_1DL_LZ_Tr1_02OCX_L.HOP",0,0,130.5,595,800,31
    ToolListInit 2
    HeadInfo "51"
    Tool 501,"Bohrkopf","",399,-1,-1,51,1000,500,2666,4450,4450,0,10,30.8,0,0,0,-360.5,19.73,-167,0,0
    HeadInfo "1"
    Tool 10,"Groeffrees 6mm","",10001,-1,2,1,4000,3000,20000,16000,16000,0,50,50,3,103.33,1.5,0,0,0,0,0
    Init "D:\CAD_CAM_DATEN\"
    SetDrillingZMax -5,-10,-15,-20,-25,-30,-35,-40,-45
    HeadInfo "51"
    FirstTool 501,"Bohrkopf","",399,-1,-1,51,1000,500,2666,4450,4450,0,10,30.8,0,0,0,-360.5,19.73,-167,0,0,374,176.27,228.8,0,0,1
    NC_Start "Field1",".spf","VISION_MNR_4446_H7",595,800,31,"",-0.1,0.34,130.5
    InitDLLMPs_Milling 
    ProcessIndex 1
    Process_Start 1,501,"51","","",1,374,176.27,149,942,465.27,197.8
    WorkPieceIndex 0
    ViewInfoToolChange 0,0,0,0,198,0,0,374,176.27,228.8,1,0,0,0,1,0,0,0,1,"","","","","","","","","",""
    HeadInfo "1"
    ToolChangeBefore 10,"Groeffrees 6mm","",10001,-1,2,1,4000,3000,20000,16000,16000,0,50,50,3,103.33,1.5,0,0,0,0,0,557.813,383,81,0,0,1
    HeadInfo "51"
    ToolChange 501,"Bohrkopf","",399,-1,-1,51,1000,500,2666,4450,4450,0,10,30.8,0,0,0,-360.5,19.73,-167,0,0,1
    ViewChange 0,0,0,0,198,0,0,374,176.27,228.8,1,0,0,0,1,0,0,0,1
    Start_Vertical_DrillingHead_Stroke 1,500,2500,2666,4450
    Vertical_DrillingHead_Stroke 1,374,176.27,374,16.27,-18,167,1,10,"0000000000010000000","210","10"
    Vertical_DrillingHead_Stroke 2,374,465.27,374,305.27,-18,167,1,10,"0000000000010000000","210","10"
    Vertical_DrillingHead_Stroke 3,942,465.27,942,305.27,-18,167,1,10,"0000000000010000000","210","10"
    Vertical_DrillingHead_Stroke 4,942,176.27,942,16.27,-18,167,1,10,"0000000000010000000","210","10"
    End_Vertical_DrillingHead_Stroke 1
    Process_End 1,"",""
    ProcessIndex 2
    Process_Start 2,10,"1","","",1,-3,379,23,598.09,385,81
    AdditionalSPInfoMPs 0,2,0,0,0,0,"","","",""
    WorkPieceIndex 0
    ViewInfoToolChange 0,0,0,0,31,0,0,557.813,383,81,1,0,0,0,1,0,0,0,1,"","","","","","","","","",""
    HeadInfo "1"
    ToolChange 10,"Groeffrees 6mm","",10001,-1,2,1,4000,3000,20000,16000,16000,0,50,50,3,103.33,1.5,0,0,0,0,0,1
    DLLMPs_Milling -1,2
    ViewChange 0,0,0,0,31,0,0,557.813,383,81,1,0,0,0,1,0,0,0,1
    Start_milling 2,0,999999999,0,3000,2500,4000,16000,557.813,383,50,557.813,383,81,0,0,270,1
    DLLMPs_Milling 0,2
    DLLMPs_Milling 1,2
    End_Milling 999999999,0,1,598.09,383,81
    Process_End 2,"",""
    FinalDLLMPs_Milling 
    NC_End
End Sub
