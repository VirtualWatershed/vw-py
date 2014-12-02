#!/bin/bash
# temperature_experiment.bash
#
# This script runs every step required for running the an experiment. The 
# experiment's hypothesis is that snow melting in the ISNOBAL model will be 
# accelerated so that snow melts sooner when the temperature is increased 
# throughout the water year.
#
# We'll do that by first downloading the required files and re-scaling them 
# with our quantization routine, then modifying every hour's worth of data's 
# temperature measurements by adding increasing multiples of 0.5 deg C up to
# 4.0. Then we run the ISNOBAL model on the re-scaled observed data as well as
# all our modified data. To visualize the melt, we finally read all the output
# data, sum the melt over all grid elements, save that to a csv for later use,
# and plot the 3-day summed, resampled melt data.
#
# Dependencies: GNU Paralell. On OS X with Homebrew installed 
# (http://brew.sh/): 
# $ brew install parallel 
#
# On Ubuntu/Debian (second command for proper compatability): 
# $ sudo apt-get install parallel && sudo rm /etc/parallel/config
# 
# To do this, we first have to download and re-scale the original input data 
# obtained from the icewater FTP site at Boise State University:


# Download data from ftp site (faster and more reliable than getting whole .zip)
function make_full_addr {
    filenum=$1

    root_ftp="ftp://icewater.boisestate.edu/boisefront-products/other/projects/Kormos_iSNOBAL/input.dp/"

    if [ $filenum -lt 10 ]; then
        filenum="000$filenum"
    elif [ $filenum -lt 100 ]; then
        filenum="00$filenum"
    elif [ $filenum -lt 1000 ]; then
        filenum="0$filenum"
    fi

    echo "${root_ftp}in.$filenum"
}

export -f make_full_addr

files=(`/usr/bin/seq 0 10 | parallel make_full_addr {}`)

save_dir=data/original_inputs

mkdir -p $save_dir

parallel curl {} -o $save_dir/{/} ::: ${files[@]} 


# Now that we've downloaded all the files, we re-quantize the data
# Data gets saved to 'data/inputs', defined in the python script
parallel ./recalc_input_headers.py ::: $(find data/original_inputs -type f)

# Increase the temperatures by multiples of .5 degrees
for mod_val in 0.5 1.0 1.5 2.0 2.5 3.0 3.5 4.0; do
    parallel ./modify_ipw_temps.py $mod_val {} ::: parallel $(find data/inputs -type f)
done

# Now we're ready to run ISNOBAL on each of our nine input scenarios: observed
# and each of the eight increasing temperature scenarios. modify_ipw_temps.py
# saved our modified data in folders like data/inputsP1.0 for the data that had
# it's temperature increased by 1.0. Run these like so:

parallel ./run_isnobal.py data/inputsP{} data/outputsP{} ::: 0.5 1.0 1.5 2.0 2.5 3.0 3.5 4.0

./run_isnobal.py data/inputs data/outputs

# Let's do one more time-intensive procedure, then it's time to have some fun 
# and see if melting really was different for different temperature scenarios.
# First, let's make a CSV file of the sum of the snow melt for each hour over
# all grid points in the image using the nice properties of pandas resample
# function.

./create_summary_csv.py
