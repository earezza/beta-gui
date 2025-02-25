Basic graphical user interface using Tkinter to run the BETA (Binding and Expression Target Analysis) program instead of a command-line interface.  
See http://cistrome.org/BETA/ for documentation and installation of BETA.

Build apptainer image:  
1. Install Apptainer if not already installed  
2. Clone this repository  (git clone ...)  
3. > apptainer build beta.sif beta.def  

Run it:  
1. > apptainer run beta.sif
