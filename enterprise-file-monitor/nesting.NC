%field2
N10 ; --- FinishedPart: X: 320 Y: 250 Z: 19 ---
N20 ; --- TData:7532DR_106 ---
N30 ; --- created:06.08.2025 - 15:08:42 - DiREKT CNC-Systeme GmbH ---
N40 ; --- machine parameters id1000=1 ---
#VAR
V.P.LAENGE= 320
V.P.BREITE= 250
V.P.DICKE= 19
V.P.OOX=0
V.P.OOY=0
V.P.OOZ=0
V.P.MAXZ=0
V.P.MAXX=0
V.P.MINX=0
V.P.MAXY=0
V.P.MINY=0
V.P.PX=0
V.P.PY=0
V.P.DCMARKER=0
V.P.LIFTOX=0
V.P.LIFTOY=0 
V.P.LIFTOZ=0 
V.P.LP_MODE_A=0 
V.P.LP_MODE_D=0
V.P.NPOFFSETX= 188.5
V.P.NPOFFSETY= 132.7
V.P.NPOFFSETZ= 18.4 
V.P.AUTOXSTRATEGIE= 0 
V.P.HLASERCOUNT=0
V.P.HLASERPOSTYP
V.P.HLASERPOSX
V.P.HLASERPOSY
#ENDVAR
N50 V.P.MAXZ=V.A.+SWE_MDS.Z-1
N60 V.P.MAXX=V.A.+SWE_MDS.X-1
N70 V.P.MINX=V.A.-SWE_MDS.X+1
N80 V.P.MAXY=V.A.+SWE_MDS.Y-1
N90 V.P.MINY=V.A.-SWE_MDS.Y+1
N100 ; --- WZ:7532DR_106 --- 
N110 ; --- Post:HH7 V7.5.5.93 Script7.0.9.0 ---
N120 ; --- total processes[#2] ---
N130 ; --- used tools ---
N140 ; ---  ---
N150 ; --- Box:  601 HId:1     VF 12 R P/N                    Platz:1 T:50 D1 ---
N160 L CYCLE [NAME=CP_TCHECK.NC @P1=601 @P2=50 @P3=1 @P4=24000 @P5=5.4 @P6=111.55 @P7=0 @P8=0]
N170 ; --- 1:CAMPUS ID, 2:ToolNo, 3:DNo, 4:DZ, 5:Radius, 6:Laenge1, 7:Laenge2, 8:Laenge3 ---
N180 ; --- Box:  181 HId:1     SF 12 R P                      Platz:8 T:44 D1 ---
N190 L CYCLE [NAME=CP_TCHECK.NC @P1=181 @P2=44 @P3=1 @P4=24000 @P5=5.775 @P6=114.9 @P7=0 @P8=0]
N200 ; --- 1:CAMPUS ID, 2:ToolNo, 3:DNo, 4:DZ, 5:Radius, 6:Laenge1, 7:Laenge2, 8:Laenge3 ---
N210 ; ---  ---
N220 G90 D0 ;G500
N230 ;CUT2DF
N240 ;CFIN
N250 V.P.AutoXStrategie = 2
N260 L CYCLE [NAME=CP_START.NC]
N270 ;G64 G17 SOFT
N280 V.G.NP[1].V.X=188.5
N290 V.G.NP[1].V.Y=132.7
N300 V.G.NP[1].V.Z=18.4
N310 ; ---  ---
N320 #FLUSH WAIT
N330 G54
N340 ; ---  ---
N350 ; --- Process #1 Kind:<Milling(2)> - BOXID:<601> T:<601 VF 12 R P/N>  HId:<1> Xmin:182.8 Xmax:514.2 Ymin:126.9 Ymax:387.7 ---
N360 ; --- --- ---
N370 ; --- --- process group start ---  ---
N380 ; --- --- ---
N390 L CYCLE [NAME=CP_CLEARDH.NC @P1=1]
N400 ; --- Go Safety ---
N410 G90 D0
N420 #MCS ON
N430 G0 Z=V.P.MAXZ
N440 #MCS OFF
N450 ; --- 601 VF 12 R P/N ---
N460 ; --- HEAD:1 Spindle 1 (P01 V01) ---
N470 ; --- VF 12 R P/N  ID:601 Platz:1 T:50 ---
N480 L CYCLE [NAME=CP_TC.NC @P1=1 @P2=2001 @P3=1 @P4=601 @P5=-1 @P6=1 @P7=0 @P8=-6 @P9=100]
N490 ; --- 1:CAMPUS ID, 2:HEAD ID, 3:PLACE ID WZW, 4:ToolNo, 5:C-Achse-Heben, 6:Heben erlaubt, 7:Wechselmode, 8:XPos, 9:Achsbeschl ---
N500 ; --- AKNEU ---
N510 T50 D1    ; --- SpeedCall ---
N520 L CYCLE [NAME=CP_TSPEED.NC @P1=1 @P2=3 @P3=22000 @P8=1]
N530 ; --- 1:HEAD ID, 2:DR, 3:DZ, 4:XPos, 5:YPos, 6:ZPos, 7:CRaster ---
N540 ; ---  ##################### DLLMPs vor ViewChange - AGGOX:-0.15  AGGOY:0.2  AGGOZ:0 ---
N550 M160    ; --- DustSuction ---
N560 D0 G0 X-5.85 Y125.3 Z275.59
N570 T50 D1
N580 L CYCLE [NAME=CP_DYNAMIC.NC @P1=-1 @P2=2]
N590 ; --- WP:1 Stop:CM X:188.5 Y:132.7 Z:0 ---
N600 ; --- Y:\testpp.hop ---
N610 ; --- FX:320 FY:250 Z:19 ---
N620 ; --- Viewchange View 0 ---
N630 V.P.OOX=0 V.P.OOY=0 V.P.OOZ=0
N640 ; --- INFO - IM IPZ wird beim vertikalen Fraesen der Offset Z vom Aggregat eingerechnet ---
N650 ; --- -- ---
N660 ; --- VERSCHIEBUNG AKTIVIEREN ---
N670 ; --- -- ---
N680 P1=0+V.P.OOX
N690 P2=0+V.P.OOY
N700 P3=19+V.P.OOZ
N710 L CYCLE [NAME=CP_CS.NC @P1=1 @P2=P1 @P3=P2 @P4=P3 @P5=0 @P6=0 @P7=0]
N720 ; --- ViewchangeEnd ---
N730 L CYCLE [NAME=CP_RELEASE.NC]
N740 ; --- -- ---
N750 ; --- --      Milling  ---
N760 ; --- -- ---
N770 ; ---  ##################### DLLMPs ---
N780 T50 D1
N790 L CP_CONTOUR_START.NC
N800 G0 G40 X-5.85 Y125.3 Z25
N810 G1 G42 Y130.8 F16000
N820 G1 X-5.85 Y130.8 Z-21 F4000
N830 G2 X0.15 Y124.8 R=6 F16000
N840 G1 Y-0.2
N850 G1 X320.15
N860 G1 Y249.8
N870 G1 X0.15
N880 G1 Y119.4
N890 G2 X-5.85 Y113.4 R=6
N900 G1 X-5.85 Y113.4 Z25 F10000
N910 G1 G40 Y118.9 F16000
N920 L CP_CONTOUR_END.NC
N930 ; --- -- ---
N940 ; --- VERSCHIEBUNG DEAKTIVIEREN ---
N950 ; --- -- ---
N960 L CYCLE [NAME=CP_CS.NC @P1=0]
N970 ; ---  ##################### DLLMPs SIC ---
N980 D0 G0 X-5.85 Y118.9 Z275.59
N990 T50 D1
N1000 ; --- --- ---
N1010 ; --- --- process group end --- ---
N1020 ; --- -------------------------------  ---
N1030 ; --- --- ---
N1040 ; --- Process #2 Kind:<Milling(2)> - BOXID:<181> T:<181 SF 12 R P>  HId:<1> Xmin:304.575 Xmax:393.025 Ymin:233.075 Ymax:281.525 ---
N1050 ; --- --- ---
N1060 ; --- --- process group start ---  ---
N1070 ; --- --- ---
N1080 L CYCLE [NAME=CP_CLEARDH.NC @P1=1]
N1090 M5
N1100 ; --- Go Safety ---
N1110 G90 D0
N1120 #MCS ON
N1130 G0 Z=V.P.MAXZ
N1140 #MCS OFF
N1150 ; --- 181 SF 12 R P ---
N1160 ; --- HEAD:1 Spindle 1 (P01 V01) ---
N1170 ; --- SF 12 R P  ID:181 Platz:8 T:44 ---
N1180 L CYCLE [NAME=CP_TC.NC @P1=1 @P2=2001 @P3=8 @P4=181 @P5=-1 @P6=1 @P7=0 @P8=160 @P9=100]
N1190 ; --- 1:CAMPUS ID, 2:HEAD ID, 3:PLACE ID WZW, 4:ToolNo, 5:C-Achse-Heben, 6:Heben erlaubt, 7:Wechselmode, 8:XPos, 9:Achsbeschl ---
N1200 ; --- AKNEU ---
N1210 T44 D1    ; --- SpeedCall ---
N1220 L CYCLE [NAME=CP_TSPEED.NC @P1=1 @P2=3 @P3=22000 @P8=1]
N1230 ; --- 1:HEAD ID, 2:DR, 3:DZ, 4:XPos, 5:YPos, 6:ZPos, 7:CRaster ---
N1240 ; ---  ##################### DLLMPs vor ViewChange - AGGOX:-0.15  AGGOY:0.2  AGGOZ:0 ---
N1250 M160    ; --- DustSuction ---
N1260 D0 G0 X160.275 Y100.8 Z275.59
N1270 T44 D1
N1280 L CYCLE [NAME=CP_DYNAMIC.NC @P1=-1 @P2=2]
N1290 ; --- WP:1 Stop:CM X:188.5 Y:132.7 Z:0 ---
N1300 ; --- Y:\testpp.hop ---
N1310 ; --- FX:320 FY:250 Z:19 ---
N1320 ; --- Viewchange View 0 ---
N1330 V.P.OOX=0 V.P.OOY=0 V.P.OOZ=0
N1340 ; --- INFO - IM IPZ wird beim vertikalen Fraesen der Offset Z vom Aggregat eingerechnet ---
N1350 ; --- -- ---
N1360 ; --- VERSCHIEBUNG AKTIVIEREN ---
N1370 ; --- -- ---
N1380 P1=0+V.P.OOX
N1390 P2=0+V.P.OOY
N1400 P3=19+V.P.OOZ
N1410 L CYCLE [NAME=CP_CS.NC @P1=1 @P2=P1 @P3=P2 @P4=P3 @P5=0 @P6=0 @P7=0]
N1420 ; --- ViewchangeEnd ---
N1430 L CYCLE [NAME=CP_RELEASE.NC]
N1440 ; --- -- ---
N1450 ; --- --      Milling  ---
N1460 ; --- -- ---
N1470 ; ---  ##################### DLLMPs ---
N1480 T44 D1
N1490 L CP_CONTOUR_START.NC
N1500 G0 G40 X160.275 Y100.8 Z25
N1510 G1 G42 X166.15 F10000
N1520 G1 X166.15 Y100.8 Z-0.0001 F4000
N1530 G2 X160.15 Y94.8 R=6 F10000
N1540 G1 X110.15
N1550 G1 Y154.8
N1560 G1 X210.15
N1570 G1 Y94.8
N1580 G1 X160.15
N1590 G2 X154.15 Y100.8 R=6
N1600 G1 X154.15 Y100.8 Z25
N1610 G1 G40 X160.025
N1620 L CP_CONTOUR_END.NC
N1630 ; --- -- ---
N1640 ; --- VERSCHIEBUNG DEAKTIVIEREN ---
N1650 ; --- -- ---
N1660 L CYCLE [NAME=CP_CS.NC @P1=0]
N1670 ; ---  ##################### DLLMPs SIC ---
N1680 D0 G0 X160.025 Y100.8 Z275.59
N1690 T44 D1
N1700 ; --- --- ---
N1710 ; --- --- process group end --- ---
N1720 ; --- -------------------------------  ---
N1730 ; --- --- ---
N1740 L CYCLE [NAME=CP_CLEARDH.NC @P1=1]
N1750 M5
N1760 L CYCLE [NAME=CP_CLEARDH.NC @P1=1]
N1770 ; --- Go Safety ---
N1780 G90 D0
N1790 #MCS ON
N1800 G0 Z=V.P.MAXZ
N1810 #MCS OFF
N1820 ; --- ohne parken - Achsen stehen lassen! ---
N1830 #MCS ON
N1840 V.P.PX=V.A.ACT_POS.X
N1850 V.P.PY=V.A.ACT_POS.Y
N1860 #MCS OFF
N1870 L CYCLE [NAME=CP_END.NC @P1=V.P.PX @P2=V.P.PY]
N1880 M30
