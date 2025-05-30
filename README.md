# TTPlus_datatool
This repository contains the datatool for analyzing TT+ data. 

The files contained are:
- "clean_manualFiles.py" which is used to pre-process manual txt data retrieved from the devices/gateways. It is recommended to first run manual data in txt format through this python code that will generate a folder containing the cleaned manual files to be available for the main software.

- "TTplus_DT_Ver3.py" which is the main software for analyzing and cleaning TT plus data. The software comes with a GUI of which an example of compiling is given in the files. The output of the software are both .html interactive plots and a csv files for each data type among 4B, 45, 4D, 49. 4B contains informations about the gateway, 4D and 45 contain sapflow data, battery data, environmental data and radial growth data. 49 contains spectrometer data.
  
